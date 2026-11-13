"""Experimental Ada-only KDBX reader; never exposed as a model tool."""

from __future__ import annotations

import stat
from pathlib import Path
from typing import Any


_MAX_VAULT_SIZE = 16 * 1024 * 1024


class SecretVaultError(RuntimeError):
    """Credential vault unavailable or request denied (never includes secrets)."""


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

    def unlock(self, passphrase: str) -> None:
        if self.unlocked:
            raise SecretVaultError("Ada vault is already unlocked")
        if not passphrase:
            raise SecretVaultError("Ada vault passphrase is required")
        try:
            root = self.path.parent.parent
            if root.is_symlink() or self.path.parent.is_symlink() or self.path.is_symlink():
                raise SecretVaultError("Ada vault path must not contain symlinks")
            info = self.path.stat()
            if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= _MAX_VAULT_SIZE:
                raise SecretVaultError("Ada vault must be a bounded regular file")
            if info.st_mode & 0o077:
                raise SecretVaultError("Ada vault must be owner-only (mode 0600)")
        except OSError:
            raise SecretVaultError("Ada vault is not accessible") from None

        try:
            # Optional pinned PoC-only reader. Never required for ordinary Ada.
            from kdbxtool import Database
        except ImportError:
            raise SecretVaultError("KDBX reader not installed (experimental extra)") from None

        try:
            self._db = Database.open(self.path, password=passphrase)
        except Exception:
            raise SecretVaultError("Ada vault could not be unlocked") from None

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
