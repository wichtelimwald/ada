#!/usr/bin/env python3
"""Prepare/clean up a manual restricted-runtime identity probe for MVP-30 S2.

Research-only. This script NEVER invokes sudo.

"prepare" creates only synthetic state:
- a temporary encrypted APFS sparse bundle mounted for the current user;
- a synthetic Keychain item whose random value never leaves process memory;
- a tiny shell check that an explicitly chosen existing restricted account can run.

It prints the ONE identity-switch command for the maintainer to execute manually.
"cleanup" then removes the synthetic Keychain item, detaches the vault, and deletes
the temporary workspace without sudo.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import pwd
import secrets
import shlex
import shutil
import stat
import sys
import tempfile
from typing import Any

import probe_encrypted_vault as vault


class ProbeError(RuntimeError):
    pass


HERE = Path(__file__).resolve().parent
KEYCHAIN_SWIFT = HERE / "keychain_probe.swift"
WORKSPACE_PREFIX = "ada-mvp30-s2-identity-"
STATE_NAME = "probe-state.json"


def choose_runtime_user(requested: str | None) -> str:
    candidates = [requested] if requested else ["nobody", "_nobody"]
    for candidate in candidates:
        if not candidate:
            continue
        try:
            account = pwd.getpwnam(candidate)
        except KeyError:
            continue
        if account.pw_uid == os.getuid():
            continue
        return candidate
    raise ProbeError("no suitable existing distinct runtime account found")


def compile_keychain_helper(output: Path) -> None:
    xcrun = shutil.which("xcrun")
    if xcrun is None:
        raise ProbeError("xcrun is unavailable; Xcode Command Line Tools are required")
    result = vault.run([xcrun, "--find", "swiftc"], check=False)
    if result.returncode != 0:
        raise ProbeError("swiftc is unavailable via xcrun")
    swiftc = result.stdout.decode().strip()
    if not swiftc:
        raise ProbeError("xcrun returned an empty swiftc path")

    vault.run([swiftc, str(KEYCHAIN_SWIFT), "-o", str(output)])
    output.chmod(0o755)


def helper(
    executable: Path,
    operation: str,
    service: str,
    account: str,
) -> int:
    result = vault.run(
        [str(executable), operation, service, account],
        check=False,
        timeout=20,
    )
    return result.returncode


def create_vault(image: Path, password: str) -> None:
    vault.run(
        [
            "/usr/bin/hdiutil",
            "create",
            "-type",
            "SPARSEBUNDLE",
            "-size",
            "32m",
            "-fs",
            "APFS",
            "-volname",
            "AdaMVP30S2IdentityProbe",
            "-uid",
            str(os.getuid()),
            "-gid",
            str(os.getgid()),
            "-mode",
            "0700",
            "-encryption",
            "AES-256",
            "-stdinpass",
            str(image),
        ],
        input_bytes=vault.hdi_password(password),
    )


def write_restricted_check(
    path: Path,
    *,
    runtime_user: str,
    private_file: Path,
    helper_bin: Path,
    service: str,
    account: str,
) -> None:
    script = f"""#!/bin/sh
set +e

/bin/cat {shlex.quote(str(private_file))} >/dev/null 2>&1
vault_rc=$?

{shlex.quote(str(helper_bin))} read {shlex.quote(service)} {shlex.quote(account)} >/dev/null 2>&1
keychain_rc=$?

printf '%s\\n' \
  'probe=mvp-30-s2-restricted-runtime-manual' \
  'runtime_user={runtime_user}' \
  "vault_read_exit=$vault_rc" \
  "keychain_read_exit=$keychain_rc"

# This checker reports evidence only; it deliberately does not turn an expected
# denial into a shell failure that could obscure the two individual exit codes.
exit 0
"""
    path.write_text(script, encoding="utf-8")
    path.chmod(0o755)


def write_state(path: Path, state: dict[str, Any]) -> None:
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    path.chmod(stat.S_IRUSR | stat.S_IWUSR)


def validate_state_path(state_path: Path) -> Path:
    resolved = state_path.expanduser().resolve()
    if resolved.name != STATE_NAME:
        raise ProbeError(f"state file must be named {STATE_NAME}")
    if not resolved.parent.name.startswith(WORKSPACE_PREFIX):
        raise ProbeError("state file is not inside an Ada MVP-30 S2 probe workspace")
    return resolved


def cleanup_workspace(state_path: Path) -> dict[str, Any]:
    state_path = validate_state_path(state_path)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    root = state_path.parent

    helper_bin = Path(state["helper_bin"])
    service = str(state["service"])
    account = str(state["account"])
    device = str(state["device"])

    report: dict[str, Any] = {
        "probe": "mvp-30-s2-restricted-runtime-cleanup",
        "keychain_cleanup": False,
        "vault_cleanup": False,
        "workspace_cleanup": False,
        "status": "running",
    }

    try:
        report["keychain_cleanup"] = helper(
            helper_bin,
            "delete",
            service,
            account,
        ) == 0
    except Exception as exc:
        report["keychain_cleanup_error"] = str(exc)

    try:
        vault.detach(device)
        report["vault_cleanup"] = True
    except Exception as exc:
        report["vault_cleanup_error"] = str(exc)

    if report["vault_cleanup"]:
        try:
            shutil.rmtree(root)
            report["workspace_cleanup"] = True
        except Exception as exc:
            report["workspace_cleanup_error"] = str(exc)

    report["status"] = (
        "ok"
        if report["keychain_cleanup"]
        and report["vault_cleanup"]
        and report["workspace_cleanup"]
        else "error"
    )
    return report


def prepare(runtime_user_requested: str | None) -> tuple[dict[str, Any], Path]:
    if sys.platform != "darwin":
        raise ProbeError("this probe must run on macOS")

    runtime_user = choose_runtime_user(runtime_user_requested)
    root = Path(tempfile.mkdtemp(prefix=WORKSPACE_PREFIX))
    # The stand-in runtime must reach the mounted file/checker by exact path.
    # It cannot list the workspace or read the 0600 state file.
    root.chmod(0o711)

    helper_bin = root / "keychain-probe"
    image = root / "identity-vault.sparsebundle"
    mountpoint = root / "mount"
    checker = root / "restricted-check.sh"
    state_path = root / STATE_NAME

    password = secrets.token_hex(32)
    marker = b"synthetic-ada-s2-identity-marker\n"
    service = f"org.ada.mvp30.s2.{secrets.token_hex(8)}"
    account = "synthetic-probe"

    device: str | None = None
    keychain_item_added = False
    try:
        compile_keychain_helper(helper_bin)
        create_vault(image, password)
        mountpoint.mkdir(mode=0o700, exist_ok=True)
        device = vault.attach(image, mountpoint, password)

        private_file = mountpoint / "synthetic-private.txt"
        private_file.write_bytes(marker)
        private_file.chmod(0o600)

        if private_file.read_bytes() != marker:
            raise ProbeError("current user could not read the synthetic vault marker")

        if helper(helper_bin, "add", service, account) != 0:
            raise ProbeError("current-user synthetic Keychain add failed")
        keychain_item_added = True

        if helper(helper_bin, "read", service, account) != 0:
            raise ProbeError("current-user synthetic Keychain read failed")

        write_restricted_check(
            checker,
            runtime_user=runtime_user,
            private_file=private_file,
            helper_bin=helper_bin,
            service=service,
            account=account,
        )

        state = {
            "account": account,
            "device": device,
            "helper_bin": str(helper_bin),
            "runtime_user": runtime_user,
            "service": service,
        }
        write_state(state_path, state)

        report = {
            "probe": "mvp-30-s2-restricted-runtime-prepare",
            "status": "ready",
            "runtime_user": runtime_user,
            "broker_user_vault_read": True,
            "broker_user_keychain_read": True,
            "workspace": str(root),
            "state_file": str(state_path),
            "manual_identity_switch_command": (
                f"sudo -u {shlex.quote(runtime_user)} -- /bin/sh "
                f"{shlex.quote(str(checker))}"
            ),
            "cleanup_command": (
                "python3 research/memory/mvp-30-s2/"
                f"probe_restricted_runtime.py cleanup {shlex.quote(str(state_path))}"
            ),
        }
        return report, state_path

    except Exception:
        if keychain_item_added:
            try:
                helper(helper_bin, "delete", service, account)
            except Exception:
                pass
        if device is not None:
            try:
                vault.detach(device)
            except Exception:
                pass
        shutil.rmtree(root, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument(
        "--runtime-user",
        help="Existing restricted account to test; defaults to nobody/_nobody.",
    )

    cleanup_parser = subparsers.add_parser("cleanup")
    cleanup_parser.add_argument("state_file", type=Path)

    args = parser.parse_args()

    try:
        if args.command == "prepare":
            report, _ = prepare(args.runtime_user)
        else:
            report = cleanup_workspace(args.state_file)
    except (ProbeError, vault.ProbeError, OSError, ValueError, KeyError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, indent=2))
        return 2

    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] in {"ready", "ok"} else 3


if __name__ == "__main__":
    raise SystemExit(main())
