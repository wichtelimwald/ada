#!/usr/bin/env python3
"""Target-Mac probe for MVP-30 S2 encrypted-vault mechanics.

Uses synthetic data only. The vault passphrase exists only in this process memory
and is passed to hdiutil over stdin; it is never written to argv, environment,
files, logs, or output.

This is research/probe code, not the production EncryptedVaultProvider.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import plistlib
import platform
import pwd
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
from typing import Any


class ProbeError(RuntimeError):
    pass


def run(
    argv: list[str],
    *,
    input_bytes: bytes | None = None,
    check: bool = True,
    timeout: int = 120,
) -> subprocess.CompletedProcess[bytes]:
    try:
        result = subprocess.run(
            argv,
            input=input_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise ProbeError(
            f"{argv[0]} timed out after {timeout}s"
        ) from exc
    if check and result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise ProbeError(f"{argv[0]} failed with exit {result.returncode}: {stderr}")
    return result


def hdi_password(password: str) -> bytes:
    # hdiutil accepts stdin password data; EOF termination works in current
    # documented examples and avoids argv/environment exposure.
    return password.encode("utf-8")


def parse_attached_device(plist_bytes: bytes, mountpoint: Path) -> tuple[str, str]:
    data = plistlib.loads(plist_bytes)
    expected = str(mountpoint.resolve())
    mounted_device: str | None = None
    whole_device: str | None = None

    for entity in data.get("system-entities", []):
        candidate_mount = entity.get("mount-point")
        dev_entry = entity.get("dev-entry")
        if not dev_entry:
            continue
        dev_entry = str(dev_entry)

        # The whole image device is the /dev/diskN entry; mounted filesystems are
        # typically slices such as /dev/diskNs1.
        name = Path(dev_entry).name
        if re.fullmatch(r"disk\d+", name):
            whole_device = dev_entry

        if (
            candidate_mount
            and str(Path(candidate_mount).resolve()) == expected
        ):
            mounted_device = dev_entry

    if mounted_device is None:
        raise ProbeError(
            "hdiutil attach output did not contain the expected mounted device"
        )
    if whole_device is None:
        # Conservative fallback from /dev/diskNsM -> /dev/diskN.
        name = Path(mounted_device).name
        match = re.fullmatch(r"(disk\d+)(?:s\d+)+", name)
        whole_device = (
            f"/dev/{match.group(1)}" if match else mounted_device
        )

    return mounted_device, whole_device


def python_can_read(path: Path) -> bool:
    code = (
        "from pathlib import Path; import sys; "
        "Path(sys.argv[1]).read_bytes(); "
        "raise SystemExit(0)"
    )
    result = run([sys.executable, "-c", code, str(path)], check=False)
    return result.returncode == 0


def distinct_user_can_read(path: Path, runtime_user: str) -> tuple[str, bool | None]:
    try:
        account = pwd.getpwnam(runtime_user)
    except KeyError:
        return ("skipped:runtime-user-not-found", None)
    if account.pw_uid == os.getuid():
        return ("skipped:runtime-user-is-current-user", None)

    sudo = shutil.which("sudo")
    if sudo is None:
        return ("skipped:sudo-unavailable", None)

    preflight = run([sudo, "-n", "-u", runtime_user, "/usr/bin/true"], check=False)
    if preflight.returncode != 0:
        return ("skipped:sudo-not-preauthorized-or-user-invalid", None)

    reader = "/usr/bin/python3"
    if not Path(reader).exists():
        return ("skipped:/usr/bin/python3-unavailable", None)

    code = (
        "from pathlib import Path; import sys; "
        "Path(sys.argv[1]).read_bytes(); "
        "raise SystemExit(0)"
    )
    result = run(
        [sudo, "-n", "-u", runtime_user, reader, "-c", code, str(path)],
        check=False,
    )
    return ("executed", result.returncode == 0)


def attach(image: Path, mountpoint: Path, password: str) -> tuple[str, str]:
    mountpoint.mkdir(mode=0o700, exist_ok=True)
    result = run(
        [
            "/usr/bin/hdiutil",
            "attach",
            str(image),
            "-stdinpass",
            "-mountpoint",
            str(mountpoint),
            "-owners",
            "on",
            "-nobrowse",
            "-plist",
        ],
        input_bytes=hdi_password(password),
    )
    return parse_attached_device(result.stdout, mountpoint)


def detach(device: str) -> None:
    run(["/usr/bin/hdiutil", "detach", device], timeout=20)


def probe(runtime_user: str | None) -> dict[str, Any]:
    if sys.platform != "darwin":
        raise ProbeError("this probe must run on macOS")
    if not Path("/usr/bin/hdiutil").exists():
        raise ProbeError("/usr/bin/hdiutil is unavailable")

    report: dict[str, Any] = {
        "probe": "mvp-30-s2-encrypted-vault",
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "same_user_unlocked_read": None,
        "distinct_runtime_user_requested": runtime_user is not None,
        "distinct_user_probe": "not-requested",
        "distinct_user_unlocked_read": None,
        "detach_reattach_persistence": False,
        "cleanup": False,
    }

    password = secrets.token_hex(32)
    marker = b"synthetic-ada-s2-marker\n"

    with tempfile.TemporaryDirectory(prefix="ada-mvp30-s2-") as temp_dir:
        root = Path(temp_dir)
        # TemporaryDirectory is normally 0700. Make only the parent traversable so
        # an optional distinct-user read reaches the mounted volume and tests the
        # volume's ownership/mode rather than failing early on the temp parent.
        root.chmod(0o711)
        image = root / "synthetic-vault.sparsebundle"
        mountpoint = root / "mount"
        mountpoint.mkdir(mode=0o700)

        run(
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
                "AdaMVP30S2Probe",
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
            input_bytes=hdi_password(password),
        )

        device: str | None = None
        try:
            mounted_device, device = attach(image, mountpoint, password)
            secret_file = mountpoint / "synthetic-private.txt"
            secret_file.write_bytes(marker)
            secret_file.chmod(0o600)
            vault_stat = mountpoint.stat()
            report["vault_root_uid"] = vault_stat.st_uid
            report["vault_root_gid"] = vault_stat.st_gid
            report["vault_root_mode"] = oct(vault_stat.st_mode & 0o777)

            # Expected to be True: same-user process separation alone is not a
            # filesystem protection boundary once the vault is unlocked.
            report["same_user_unlocked_read"] = python_can_read(secret_file)

            if runtime_user:
                status, readable = distinct_user_can_read(secret_file, runtime_user)
                report["distinct_user_probe"] = status
                report["distinct_user_unlocked_read"] = readable

            detach(device)
            device = None

            mounted_device, device = attach(image, mountpoint, password)
            persisted = (mountpoint / "synthetic-private.txt").read_bytes()
            report["detach_reattach_persistence"] = persisted == marker
        finally:
            if device is not None:
                try:
                    detach(device)
                except Exception:
                    report["cleanup"] = False
                    raise
            report["cleanup"] = True

    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Probe macOS encrypted-vault mechanics and direct-read isolation "
            "using synthetic data only."
        )
    )
    parser.add_argument(
        "--runtime-user",
        help=(
            "Optional existing macOS account to use for the distinct-identity "
            "negative read probe. The script never prompts for sudo; run sudo -v "
            "yourself first if you intentionally want this probe."
        ),
    )
    args = parser.parse_args()

    try:
        report = probe(args.runtime_user)
    except ProbeError as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, indent=2))
        return 2

    report["status"] = "ok"
    print(json.dumps(report, indent=2, sort_keys=True))

    if report["same_user_unlocked_read"] is not True:
        print(
            "error: expected same-user baseline read to succeed; "
            "the platform behavior needs investigation",
            file=sys.stderr,
        )
        return 3
    if report["detach_reattach_persistence"] is not True:
        print("error: detach/reattach persistence check failed", file=sys.stderr)
        return 4

    if (
        args.runtime_user
        and report["distinct_user_probe"] == "executed"
        and report["distinct_user_unlocked_read"] is True
    ):
        print(
            "error: distinct runtime identity could still read the synthetic vault",
            file=sys.stderr,
        )
        return 5

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
