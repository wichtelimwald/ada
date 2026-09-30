#!/usr/bin/env python3
"""Prepare/clean up a manual restricted-runtime identity probe for MVP-30 S2.

Research-only. This script NEVER invokes sudo.

"prepare" creates only synthetic state:
- a temporary encrypted APFS sparse bundle mounted for the current user;
- a synthetic Keychain item whose random value is sent to macOS security(1) only
  over stdin (security -i), never argv/environment/files/output;
- a tiny shell check for an explicitly chosen existing restricted account.

It prints the ONE identity-switch command for the maintainer to execute manually.
"cleanup" removes the synthetic Keychain item, detaches the vault, and deletes the
temporary workspace without sudo.
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


WORKSPACE_PREFIX = "ada-mvp30-s2-identity-"
STATE_NAME = "probe-state.json"
SECURITY = Path("/usr/bin/security")


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


def require_security_tool() -> None:
    if not SECURITY.exists():
        raise ProbeError("/usr/bin/security is unavailable")


def keychain_add(service: str, account: str, password: str) -> None:
    # security(1) interactive mode reads commands from stdin. service/account are
    # generated fixed-safe tokens and password is random hex, so no shell quoting
    # or command interpolation is involved.
    command = (
        f"add-generic-password -a {account} -s {service} -w {password}\n"
    ).encode("ascii")
    result = vault.run(
        [str(SECURITY), "-q", "-i"],
        input_bytes=command,
        check=False,
        timeout=20,
    )
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise ProbeError(
            "current-user synthetic Keychain add failed"
            + (f": {stderr}" if stderr else "")
        )


def keychain_read(service: str, account: str) -> bool:
    # -w emits the secret to stdout. Capture it and discard it; never print it.
    result = vault.run(
        [
            str(SECURITY),
            "find-generic-password",
            "-a",
            account,
            "-s",
            service,
            "-w",
        ],
        check=False,
        timeout=20,
    )
    return result.returncode == 0


def keychain_delete(service: str, account: str) -> bool:
    result = vault.run(
        [
            str(SECURITY),
            "delete-generic-password",
            "-a",
            account,
            "-s",
            service,
        ],
        check=False,
        timeout=20,
    )
    return result.returncode == 0


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
    service: str,
    account: str,
) -> None:
    script = f"""#!/bin/sh
set +e

/bin/cat {shlex.quote(str(private_file))} >/dev/null 2>&1
vault_rc=$?

{shlex.quote(str(SECURITY))} find-generic-password \
  -a {shlex.quote(account)} \
  -s {shlex.quote(service)} \
  -w >/dev/null 2>&1
keychain_rc=$?

printf '%s\\n' \
  'probe=mvp-30-s2-restricted-runtime-manual' \
  'runtime_user={runtime_user}' \
  "vault_read_exit=$vault_rc" \
  "keychain_read_exit=$keychain_rc"

# Evidence only: expected denials remain visible as their individual exit codes.
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
        report["keychain_cleanup"] = keychain_delete(service, account)
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


def prepare(runtime_user_requested: str | None) -> dict[str, Any]:
    if sys.platform != "darwin":
        raise ProbeError("this probe must run on macOS")
    require_security_tool()

    runtime_user = choose_runtime_user(runtime_user_requested)
    # Use /tmp explicitly instead of macOS's per-user TMPDIR under /var/folders.
    # The latter is intentionally not traversable by unrelated OS identities and
    # would make the manual restricted-user check fail before it reaches the
    # synthetic vault/Keychain targets.
    root = Path(tempfile.mkdtemp(prefix=WORKSPACE_PREFIX, dir="/tmp"))
    # The stand-in runtime must reach the mounted file/checker by exact path.
    # It cannot list the workspace or read the 0600 state file.
    root.chmod(0o711)

    image = root / "identity-vault.sparsebundle"
    mountpoint = root / "mount"
    checker = root / "restricted-check.sh"
    state_path = root / STATE_NAME

    vault_password = secrets.token_hex(32)
    keychain_password = secrets.token_hex(32)
    marker = b"synthetic-ada-s2-identity-marker\n"
    service = f"org.ada.mvp30.s2.{secrets.token_hex(8)}"
    account = "synthetic-probe"

    device: str | None = None
    keychain_item_added = False
    try:
        create_vault(image, vault_password)
        mountpoint.mkdir(mode=0o700, exist_ok=True)
        device = vault.attach(image, mountpoint, vault_password)

        private_file = mountpoint / "synthetic-private.txt"
        private_file.write_bytes(marker)
        private_file.chmod(0o600)

        if private_file.read_bytes() != marker:
            raise ProbeError("current user could not read the synthetic vault marker")

        keychain_add(service, account, keychain_password)
        keychain_item_added = True

        if not keychain_read(service, account):
            raise ProbeError("current-user synthetic Keychain read failed")

        write_restricted_check(
            checker,
            runtime_user=runtime_user,
            private_file=private_file,
            service=service,
            account=account,
        )

        state = {
            "account": account,
            "device": device,
            "runtime_user": runtime_user,
            "service": service,
        }
        write_state(state_path, state)

        return {
            "probe": "mvp-30-s2-restricted-runtime-prepare",
            "status": "ready",
            "runtime_user": runtime_user,
            "broker_user_vault_read": True,
            "broker_user_keychain_read": True,
            "keychain_transport": "security -i via stdin",
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

    except Exception:
        if keychain_item_added:
            try:
                keychain_delete(service, account)
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
            report = prepare(args.runtime_user)
        else:
            report = cleanup_workspace(args.state_file)
    except (ProbeError, vault.ProbeError, OSError, ValueError, KeyError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, indent=2))
        return 2

    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] in {"ready", "ok"} else 3


if __name__ == "__main__":
    raise SystemExit(main())
