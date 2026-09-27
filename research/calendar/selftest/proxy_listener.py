"""Count connection attempts to a fake proxy (probe self-test, localhost only).

Usage: python3 proxy_listener.py PROXY_PORT STATUS_PORT
A connection to STATUS_PORT returns the number of proxy connections so far.
"""

from __future__ import annotations

import socket
import sys
import threading

COUNT = {"n": 0}


def _listen(port: int) -> socket.socket:
    sock = socket.socket()
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", port))
    sock.listen(16)
    return sock


def _status(port: int) -> None:
    sock = _listen(port)
    while True:
        conn, _ = sock.accept()
        conn.sendall(str(COUNT["n"]).encode())
        conn.close()


def main() -> None:
    proxy_port, status_port = int(sys.argv[1]), int(sys.argv[2])
    threading.Thread(target=_status, args=(status_port,), daemon=True).start()
    sock = _listen(proxy_port)
    while True:
        conn, _ = sock.accept()
        COUNT["n"] += 1
        conn.close()


if __name__ == "__main__":
    main()
