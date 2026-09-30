#!/usr/bin/env python3
"""Target-Mac S2C1 probe for Unix-socket peer-identity enforcement.

Research-only. This script never invokes sudo and makes no persistent system
changes. It proves that the broker can authenticate a local client from
kernel-supplied Unix-domain peer credentials before reading request payload.

Flow:
1. prepare: starts a short-lived broker probe in the background, proves the current
   user is rejected, and prints one explicit restricted-user client command.
2. maintainer runs that exact sudo -u command.
3. collect: reads the server evidence and removes the synthetic workspace.
"""

from __future__ import annotations

import argparse
import ctypes
import errno
import json
import os
from pathlib import Path
import pwd
import secrets
import shutil
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import time
from typing import Any


WORKSPACE_PREFIX = "ada-mvp30-s2-ipc-"
STATE_NAME = "probe-state.json"
RESULT_NAME = "server-result.json"
READY_NAME = "server-ready"
CLIENT_NAME = "restricted-client.py"
SERVER_TIMEOUT_SECONDS = 90


class ProbeError(RuntimeError):
    pass


def choose_runtime_user(requested: str | None) -> pwd.struct_passwd:
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
        return account
    raise ProbeError("no suitable existing distinct runtime account found")


def get_peer_credentials(fd: int) -> tuple[int, int]:
    """Return kernel-supplied effective UID/GID for a connected AF_UNIX peer."""
    libc = ctypes.CDLL(None, use_errno=True)
    try:
        getpeereid = libc.getpeereid
    except AttributeError as exc:
        raise ProbeError("getpeereid(3) is unavailable on this platform") from exc

    uid = ctypes.c_uint()
    gid = ctypes.c_uint()
    getpeereid.argtypes = [
        ctypes.c_int,
        ctypes.POINTER(ctypes.c_uint),
        ctypes.POINTER(ctypes.c_uint),
    ]
    getpeereid.restype = ctypes.c_int

    if getpeereid(fd, ctypes.byref(uid), ctypes.byref(gid)) != 0:
        error = ctypes.get_errno()
        raise ProbeError(f"getpeereid failed: {os.strerror(error)}")
    return int(uid.value), int(gid.value)


def write_json(path: Path, value: dict[str, Any], mode: int = 0o600) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    path.chmod(mode)


def write_client(path: Path) -> None:
    source = """#!/usr/bin/env python3
import json
import socket
import sys

sock_path = sys.argv[1]
with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
    client.settimeout(10)
    client.connect(sock_path)
    greeting = client.recv(64)
    if greeting != b"AUTH_OK\\n":
        print(json.dumps({
            "status": "rejected",
            "greeting": greeting.decode("utf-8", errors="replace").strip(),
        }, sort_keys=True))
        raise SystemExit(2)
    client.sendall(b"PING\\n")
    response = client.recv(64)

print(json.dumps({
    "status": "ok" if response == b"OK\\n" else "error",
    "auth": "accepted",
    "response": response.decode("utf-8", errors="replace").strip(),
}, sort_keys=True))
raise SystemExit(0 if response == b"OK\\n" else 3)
"""
    path.write_text(source, encoding="utf-8")
    path.chmod(0o755)


def reject_current_user(socket_path: Path) -> bool:
    """Connect as the broker user without sending any request payload."""
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(5)
        client.connect(str(socket_path))
        return client.recv(64) == b"REJECTED\n"


def serve(workspace: Path, expected_uid: int, expected_gid: int) -> int:
    socket_path = workspace / "broker.sock"
    ready_path = workspace / READY_NAME
    result_path = workspace / RESULT_NAME

    report: dict[str, Any] = {
        "probe": "mvp-30-s2c-ipc-peer-identity",
        "status": "running",
        "expected_runtime_uid": expected_uid,
        "expected_runtime_gid": expected_gid,
        "rejected_peer_count": 0,
        "rejected_before_payload_read": True,
        "accepted_peer_uid": None,
        "accepted_peer_gid": None,
        "accepted_payload": None,
    }

    try:
        socket_path.unlink(missing_ok=True)
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
            server.bind(str(socket_path))
            socket_path.chmod(0o666)
            server.listen(4)
            server.settimeout(1)
            ready_path.write_text("ready\n", encoding="utf-8")
            ready_path.chmod(0o644)

            deadline = time.monotonic() + SERVER_TIMEOUT_SECONDS
            while time.monotonic() < deadline:
                try:
                    conn, _ = server.accept()
                except socket.timeout:
                    continue

                with conn:
                    peer_uid, peer_gid = get_peer_credentials(conn.fileno())

                    # Authentication is deliberately complete before recv().
                    if peer_uid != expected_uid:
                        report["rejected_peer_count"] += 1
                        conn.sendall(b"REJECTED\n")
                        continue

                    report["accepted_peer_uid"] = peer_uid
                    report["accepted_peer_gid"] = peer_gid
                    conn.sendall(b"AUTH_OK\n")
                    payload = conn.recv(64)
                    report["accepted_payload"] = payload.decode(
                        "utf-8", errors="replace"
                    ).strip()
                    if payload == b"PING\n":
                        conn.sendall(b"OK\n")
                        report["status"] = "ok"
                        break
                    conn.sendall(b"BAD_REQUEST\n")
                    report["status"] = "bad-request"
                    break
            else:
                report["status"] = "timeout"
    except Exception as exc:
        report["status"] = "error"
        report["error"] = str(exc)
    finally:
        socket_path.unlink(missing_ok=True)
        write_json(result_path, report)

    return 0 if report["status"] == "ok" else 3


def validate_state_path(state_path: Path) -> Path:
    resolved = state_path.expanduser().resolve()
    if resolved.name != STATE_NAME:
        raise ProbeError(f"state file must be named {STATE_NAME}")
    if not resolved.parent.name.startswith(WORKSPACE_PREFIX):
        raise ProbeError("state file is not inside an Ada S2C IPC probe workspace")
    return resolved


def prepare(runtime_user_requested: str | None) -> dict[str, Any]:
    if sys.platform != "darwin":
        raise ProbeError("this probe must run on macOS")

    runtime = choose_runtime_user(runtime_user_requested)
    workspace = Path(tempfile.mkdtemp(prefix=WORKSPACE_PREFIX, dir="/tmp"))
    workspace.chmod(0o711)

    client_path = workspace / CLIENT_NAME
    state_path = workspace / STATE_NAME
    ready_path = workspace / READY_NAME
    socket_path = workspace / "broker.sock"
    result_path = workspace / RESULT_NAME
    write_client(client_path)

    process = subprocess.Popen(
        [
            sys.executable,
            str(Path(__file__).resolve()),
            "server",
            str(workspace),
            str(runtime.pw_uid),
            str(runtime.pw_gid),
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        start_new_session=True,
    )

    try:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and not ready_path.exists():
            if process.poll() is not None:
                raise ProbeError("IPC probe server exited before becoming ready")
            time.sleep(0.05)
        if not ready_path.exists():
            raise ProbeError("IPC probe server did not become ready")

        wrong_user_rejected = reject_current_user(socket_path)
        if not wrong_user_rejected:
            raise ProbeError("current-user client was not rejected")

        state = {
            "server_pid": process.pid,
            "runtime_user": runtime.pw_name,
            "runtime_uid": runtime.pw_uid,
            "runtime_gid": runtime.pw_gid,
            "workspace": str(workspace),
            "result_file": str(result_path),
        }
        write_json(state_path, state)

        return {
            "probe": "mvp-30-s2c-ipc-peer-identity-prepare",
            "status": "ready",
            "current_user_uid": os.getuid(),
            "runtime_user": runtime.pw_name,
            "runtime_uid": runtime.pw_uid,
            "wrong_user_rejected": True,
            "wrong_user_sent_payload": False,
            "workspace": str(workspace),
            "manual_identity_switch_command": (
                f"sudo -u {runtime.pw_name} -- /usr/bin/python3 "
                f"{client_path} {socket_path}"
            ),
            "collect_command": (
                "python3 research/memory/mvp-30-s2/"
                f"probe_ipc_peer_identity.py collect {state_path}"
            ),
        }
    except Exception:
        try:
            os.kill(process.pid, signal.SIGTERM)
        except OSError:
            pass
        shutil.rmtree(workspace, ignore_errors=True)
        raise


def collect(state_path: Path) -> dict[str, Any]:
    state_path = validate_state_path(state_path)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    workspace = state_path.parent
    result_path = Path(state["result_file"])
    pid = int(state["server_pid"])

    deadline = time.monotonic() + 10
    while time.monotonic() < deadline and not result_path.exists():
        time.sleep(0.05)

    if not result_path.exists():
        try:
            os.kill(pid, 0)
        except OSError as exc:
            if exc.errno != errno.ESRCH:
                raise
            raise ProbeError("IPC probe server exited without a result") from exc
        raise ProbeError("IPC probe server is still waiting for the restricted client")

    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["workspace_cleanup"] = False

    try:
        shutil.rmtree(workspace)
        result["workspace_cleanup"] = True
    except OSError as exc:
        result["workspace_cleanup_error"] = str(exc)

    if (
        result.get("status") == "ok"
        and result.get("accepted_peer_uid") == int(state["runtime_uid"])
        and result.get("accepted_payload") == "PING"
        and int(result.get("rejected_peer_count", 0)) >= 1
        and result.get("rejected_before_payload_read") is True
        and result["workspace_cleanup"] is True
    ):
        result["status"] = "ok"
    else:
        result["status"] = "error"

    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    prepare_parser = sub.add_parser("prepare")
    prepare_parser.add_argument("--runtime-user")

    server_parser = sub.add_parser("server")
    server_parser.add_argument("workspace", type=Path)
    server_parser.add_argument("expected_uid", type=int)
    server_parser.add_argument("expected_gid", type=int)

    collect_parser = sub.add_parser("collect")
    collect_parser.add_argument("state_file", type=Path)

    args = parser.parse_args()

    try:
        if args.command == "prepare":
            report = prepare(args.runtime_user)
        elif args.command == "server":
            return serve(args.workspace, args.expected_uid, args.expected_gid)
        else:
            report = collect(args.state_file)
    except (ProbeError, OSError, ValueError, KeyError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, indent=2))
        return 2

    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] in {"ready", "ok"} else 3


if __name__ == "__main__":
    raise SystemExit(main())
