"""Experimental Ada-only KDBX reader; never exposed as a model tool.

Security checks are applied before any untrusted KDF work. Real credentials
remain prohibited until the runtime and dependency release gates in #58 pass.
"""

from __future__ import annotations

import ctypes
import os
import stat
import sys
from pathlib import Path
from typing import Any


_MAX_VAULT_SIZE = 16 * 1024 * 1024

# Fixed memory and total-work ceilings prevent excessive Argon2 requests
# before key derivation. Unlike the earlier t<=10 policy, this admits the
# ~51 rounds observed for a KeePassXC 2.8.0 auto-calibrated 64 MiB vault.
# This is a resource *upper bound*, not a password-strength guarantee.
_MIN_KDF_MEMORY_KIB = 64 * 1024
_MAX_KDF_MEMORY_KIB = 256 * 1024
_MIN_KDF_ITERATIONS = 3
_MAX_KDF_ITERATIONS = 128
_MIN_KDF_PARALLELISM = 1
_MAX_KDF_PARALLELISM = 8
_MAX_KDF_MEMORY_ITERATIONS_KIB = 8 * 1024 * 1024


class SecretVaultError(RuntimeError):
    """Credential vault unavailable or request denied (never includes secrets)."""


_PR_GET_DUMPABLE = 3
_PR_SET_DUMPABLE = 4


def _prctl(option: int, value: int = 0) -> int:
    """Small Linux-only standard-library bridge; no extra runtime dependency."""
    if sys.platform != "linux":
        raise SecretVaultError("Ada credential process isolation unavailable")
    try:
        libc = ctypes.CDLL(None, use_errno=True)
        call = libc.prctl
        call.restype = ctypes.c_int
        call.argtypes = (
            ctypes.c_int,
            ctypes.c_ulong,
            ctypes.c_ulong,
            ctypes.c_ulong,
            ctypes.c_ulong,
        )
        result = call(option, value, 0, 0, 0)
        if result < 0:
            raise SecretVaultError("Ada credential process isolation unavailable")
        return result
    except (AttributeError, OSError, ValueError):
        raise SecretVaultError("Ada credential process isolation unavailable") from None


def protect_credential_process() -> None:
    """Deny *new* same-UID ptrace/proc opens; prior open fds remain usable.

    This is defense in depth, NOT same-UID process isolation. A sibling that
    opened /proc/<pid>/mem before prctl can still read it after protection.
    Real credentials require an isolated credential process from startup.
    """
    _prctl(_PR_SET_DUMPABLE, 0)
    _require_protected_credential_process()


def _require_protected_credential_process() -> None:
    """Fail closed even if an adapter is called outside the protected CLI."""
    if _prctl(_PR_GET_DUMPABLE) != 0:
        raise SecretVaultError("Ada credential process isolation unavailable")


def _validate_kdf_header(data: bytes) -> None:
    """Reject weak or resource-exhausting KDFs before deriving a key.

    This is an *unauthenticated header* read for policy enforcement only.
    The actual reader must verify KDBX cryptographic authentication afterwards.
    """
    from kdbxtool.parsing import KdbxHeader, KdbxVersion
    from kdbxtool.security import KdfType

    try:
        header, _ = KdbxHeader.parse(data)
        if header.version != KdbxVersion.KDBX4 or header.kdf_type not in (
            KdfType.ARGON2ID,
            KdfType.ARGON2D,
        ):
            raise SecretVaultError("Ada vault KDF policy rejected this file")

        memory = header.argon2_memory_kib
        iterations = header.argon2_iterations
        parallelism = header.argon2_parallelism
        if not (
            isinstance(memory, int)
            and isinstance(iterations, int)
            and isinstance(parallelism, int)
            and _MIN_KDF_MEMORY_KIB <= memory <= _MAX_KDF_MEMORY_KIB
            and _MIN_KDF_ITERATIONS <= iterations <= _MAX_KDF_ITERATIONS
            and _MIN_KDF_PARALLELISM <= parallelism <= _MAX_KDF_PARALLELISM
            and memory * iterations <= _MAX_KDF_MEMORY_ITERATIONS_KIB
        ):
            raise SecretVaultError("Ada vault KDF policy rejected this file")
    except SecretVaultError:
        raise
    except Exception:
        raise SecretVaultError("Ada vault KDF header is invalid") from None


class KdbxSecrets:
    """Read explicitly allowed entries from Ada's private encrypted file.

    The caller supplies the master passphrase through a trusted startup path.
    It must never come from Memory, environment variables, model text or argv.
    """

    def __init__(
        self,
        memory_root: str | Path,
        *,
        allowed_entries: frozenset[str] = frozenset(),
    ) -> None:
        self.path = Path(memory_root) / "secrets" / "ada.kdbx"
        self._allowed = allowed_entries
        self._db: Any = None

    @property
    def unlocked(self) -> bool:
        return self._db is not None

    def _read_vault(self) -> bytes:
        """Read one bounded file descriptor; never re-open between check and decrypt."""
        try:
            root = self.path.parent.parent
            if root.is_symlink() or self.path.parent.is_symlink() or self.path.is_symlink():
                raise SecretVaultError("Ada vault path must not contain symlinks")

            # O_NOFOLLOW protects the final component from a symlink swap
            # between the explicit check above and open(). The parent path
            # still requires an operator-controlled directory.
            flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK
            with os.fdopen(os.open(self.path, flags), "rb") as stream:
                info = os.fstat(stream.fileno())
                if not stat.S_ISREG(info.st_mode):
                    raise SecretVaultError("Ada vault must be a bounded regular file")
                if not 0 < info.st_size <= _MAX_VAULT_SIZE:
                    raise SecretVaultError("Ada vault must be a bounded regular file")
                if info.st_mode & 0o077:
                    raise SecretVaultError("Ada vault must be owner-only (mode 0600)")
                data = stream.read(_MAX_VAULT_SIZE + 1)
                if not 0 < len(data) <= _MAX_VAULT_SIZE:
                    raise SecretVaultError("Ada vault must be a bounded regular file")
                return data
        except SecretVaultError:
            raise
        except OSError:
            raise SecretVaultError("Ada vault is not accessible") from None

    def unlock(self, passphrase: str) -> None:
        _require_protected_credential_process()
        if self.unlocked:
            raise SecretVaultError("Ada vault is already unlocked")
        if not passphrase:
            raise SecretVaultError("Ada vault passphrase is required")

        try:
            # Optional pinned PoC-only reader. Never required for ordinary Ada.
            from kdbxtool import Database
        except ImportError:
            raise SecretVaultError("KDBX reader not installed (experimental extra)") from None

        data = self._read_vault()
        _validate_kdf_header(data)
        try:
            db = Database.open_bytes(data, password=passphrase)
        except Exception:
            raise SecretVaultError("Ada vault could not be unlocked") from None
        # We never save a vault. Do not keep the library's ordinary Python
        # _password/_transformed_key references after decrypting.
        # This is reference release, NOT guaranteed string/byte memory wiping.
        try:
            db.zeroize_credentials()
        except Exception:
            raise SecretVaultError("Ada vault credential cleanup failed") from None
        self._db = db

    def password(self, reference: str) -> str:
        if reference not in self._allowed:
            raise SecretVaultError("Secret reference is not authorized")
        if self._db is None:
            raise SecretVaultError("Ada vault is locked")
        try:
            matches = [
                entry
                for entry in self._db.find_entries(title=reference)
                if entry.title == reference
            ]
            if (
                len(matches) != 1
                or not isinstance(matches[0].password, str)
                or not matches[0].password
            ):
                raise SecretVaultError("Secret reference is missing or ambiguous")
            return matches[0].password
        except SecretVaultError:
            raise
        except Exception:
            raise SecretVaultError("Secret lookup failed") from None

    def lock(self) -> None:
        db = self._db
        self._db = None
        if db is not None:
            try:
                db.zeroize_credentials()
            except Exception:
                pass  # The instance is detached even if cleanup fails.

    def __enter__(self) -> KdbxSecrets:
        return self

    def __exit__(self, *_: object) -> None:
        self.lock()
