#!/usr/bin/env python3
"""Probe a restricted-runtime identity against a user-context broker boundary.

Research-only. Uses synthetic data, an existing unprivileged account (default:
'nobody' or '_nobody'), a temporary encrypted APFS sparse bundle, and a temporary
Swift helper that stores a random synthetic item in the current user's file-based
Keychain.

The script never creates users, installs launchd jobs, or stores real credentials.
It never prompts for sudo: run 'sudo -v' yourself before invoking the probe.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import pwd
import secrets
import shutil
import subprocess
import sys
import tempfile
from typing import Any

import probe_encrypted_vault as vault


class ProbeError(RuntimeError):
    pass


HERE = Path(__file__).resolve().parent
KEYCHAIN_SWIFT = HERE / "keychain_probe.swift"


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


def require_noninteractive_sudo(runtime_user: str) -> str:
    sudo = shutil.which("sudo")
    if sudo is None:
        raise ProbeError("sudo is unavailable")
    result = vault.run(
        [sudo, "-n", "-u", runtime_user, "/usr/bin/true"],
        check=False,
    )
    if result.returncode != 0:
        raise ProbeError(
            "non-interactive sudo is not authorized; run 'sudo -v' in this "
            "terminal and retry"
        )
    return sudo


def compile_keychain_helper(output: Path) -> None:
    xcrun = shutil.which("xcrun")
    if xcrun is None:
        raise ProbeError("xcrun is unavailable; Xcode Command Line Tools are required")
    result = vault.run(
        [xcrun, "--find", "swiftc"],
        check=False,
    )
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
    *,
    sudo: str | None = None,
    runtime_user: str | None = None,
) -> subprocess.CompletedProcess[bytes]:
    argv = [str(executable), operation, service, account]
    if sudo and runtime_user:
        argv = [sudo, "-n", "-u", runtime_user, *argv]
    return vault.run(argv, check=False, timeout=20)


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


def main() -> int:
    requested = sys.argv[1] if len(sys.argv) > 1 else None
    if sys.platform != "darwin":
        print(json.dumps({"status": "error", "error": "macOS required"}, indent=2))
        return 2

    try:
        runtime_user = choose_runtime_user(requested)
        sudo = require_noninteractive_sudo(runtime_user)
    except ProbeError as exc:
        print(json.dumps({"status": "needs-preflight", "error": str(exc)}, indent=2))
        return 2

    report: dict[str, Any] = {
        "probe": "mvp-30-s2-restricted-runtime",
        "runtime_user": runtime_user,
        "runtime_user_vault_read": None,
        "broker_user_vault_read": None,
        "broker_user_keychain_read": None,
        "runtime_user_keychain_read": None,
        "keychain_cleanup": False,
        "vault_cleanup": False,
        "status": "running",
    }

    password = secrets.token_hex(32)
    marker = b"synthetic-ada-s2-identity-marker\n"
    service = f"org.ada.mvp30.s2.{secrets.token_hex(8)}"
    account = "synthetic-probe"

    with tempfile.TemporaryDirectory(prefix="ada-mvp30-s2-identity-") as temp_dir:
        root = Path(temp_dir)
        # Make the temporary parent traversable to the stand-in runtime account so
        # its vault denial is tested at the mounted file itself, not at /tmp parent.
        root.chmod(0o711)

        helper_bin = root / "keychain-probe"
        image = root / "identity-vault.sparsebundle"
        mountpoint = root / "mount"
        mountpoint.mkdir(mode=0o700)

        device: str | None = None
        keychain_item_added = False
        try:
            compile_keychain_helper(helper_bin)

            create_vault(image, password)
            device = vault.attach(image, mountpoint, password)

            private_file = mountpoint / "synthetic-private.txt"
            private_file.write_bytes(marker)
            private_file.chmod(0o600)

            report["broker_user_vault_read"] = (
                private_file.read_bytes() == marker
            )

            denied = vault.run(
                [sudo, "-n", "-u", runtime_user, "/bin/cat", str(private_file)],
                check=False,
            )
            report["runtime_user_vault_read"] = denied.returncode == 0

            add_result = helper(helper_bin, "add", service, account)
            if add_result.returncode != 0:
                stderr = add_result.stderr.decode("utf-8", errors="replace").strip()
                raise ProbeError(f"current-user Keychain add failed: {stderr}")
            keychain_item_added = True

            current_read = helper(helper_bin, "read", service, account)
            report["broker_user_keychain_read"] = current_read.returncode == 0
            if not report["broker_user_keychain_read"]:
                stderr = current_read.stderr.decode("utf-8", errors="replace").strip()
                raise ProbeError(f"current-user Keychain read failed: {stderr}")

            runtime_read = helper(
                helper_bin,
                "read",
                service,
                account,
                sudo=sudo,
                runtime_user=runtime_user,
            )
            report["runtime_user_keychain_read"] = runtime_read.returncode == 0

        except (ProbeError, vault.ProbeError) as exc:
            report["status"] = "error"
            report["error"] = str(exc)
        finally:
            if keychain_item_added:
                try:
                    delete_result = helper(helper_bin, "delete", service, account)
                    report["keychain_cleanup"] = delete_result.returncode == 0
                    if not report["keychain_cleanup"]:
                        report.setdefault(
                            "error",
                            "synthetic Keychain item cleanup failed",
                        )
                        report["status"] = "error"
                except Exception as exc:
                    report["keychain_cleanup"] = False
                    report.setdefault(
                        "error",
                        f"synthetic Keychain cleanup failed: {exc}",
                    )
                    report["status"] = "error"
            else:
                report["keychain_cleanup"] = True

            if device is not None:
                try:
                    vault.detach(device)
                    report["vault_cleanup"] = True
                except Exception as exc:
                    report["vault_cleanup"] = False
                    report.setdefault("error", f"vault cleanup failed: {exc}")
                    report["status"] = "error"
            else:
                report["vault_cleanup"] = True

    if report["status"] != "error":
        report["status"] = "ok"

    print(json.dumps(report, indent=2, sort_keys=True))

    if report["status"] != "ok":
        return 3
    if report["broker_user_vault_read"] is not True:
        return 4
    if report["runtime_user_vault_read"] is not False:
        return 5
    if report["broker_user_keychain_read"] is not True:
        return 6
    if report["runtime_user_keychain_read"] is not False:
        return 7
    if report["keychain_cleanup"] is not True or report["vault_cleanup"] is not True:
        return 8
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
