from __future__ import annotations

import json
import os
from pathlib import Path
import re
import stat
from tempfile import NamedTemporaryFile
import tomllib
from typing import Any

from ada.core.memory import (
    ConfirmationBasis,
    EvidenceOrigin,
    MemoryEntry,
    MemoryKind,
    MemoryLifecycle,
)
from ada.core.personality import PersonalityProfile


_ENTRY_ID = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}")
_RESERVED_ENTRY_IDS = frozenset({"personality"})
_FORGOTTEN_BODY = "[forgotten]"


class FileMemoryError(RuntimeError):
    """The file-native Memory baseline could not be read or written safely."""


class FileMemoryStore:
    """Current-file Memory adapter for the first ADR-0008 implementation slice.

    This baseline intentionally does not implement protection domains, encryption,
    Git history, retrieval indexes, or concurrent-edit reconciliation. Callers
    provide an explicit root. Reads use current files only and never consult Git
    history, snapshots, or backups.
    """

    def __init__(self, root: str | Path) -> None:
        if isinstance(root, str) and not root.strip():
            raise FileMemoryError("Memory root must not be blank")

        expanded = Path(root).expanduser()
        if expanded.is_symlink():
            raise FileMemoryError(
                f"Memory root must not be a symlink: {expanded}"
            )

        self.root = expanded.resolve()
        self.memory_dir = self.root / "memory"
        self.learning_dir = self.root / "learning"
        self._ensure_directory(self.root)
        self._ensure_directory(self.memory_dir)
        self._ensure_directory(self.learning_dir)

    def load_personality(self) -> PersonalityProfile | None:
        path = self.memory_dir / "personality.md"
        if not path.exists():
            return None
        metadata, _body = self._read_markdown(path)
        try:
            schema_version = self._require_int(metadata, "schema_version")
            if schema_version != 1:
                raise ValueError("unsupported personality Memory schema")
            return PersonalityProfile(
                schema_version=schema_version,
                profile_id=self._require_str(metadata, "profile_id"),
                display_name=self._require_str(metadata, "display_name"),
                inspiration=self._require_str(metadata, "inspiration"),
                background_story=self._require_str(
                    metadata,
                    "background_story",
                ),
                traits=self._string_tuple(metadata, "traits"),
                interaction_style=self._string_tuple(
                    metadata,
                    "interaction_style",
                ),
                boundaries=self._string_tuple(metadata, "boundaries"),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise FileMemoryError(
                f"invalid personality Memory metadata in {path}"
            ) from exc

    def save_personality(
        self,
        profile: PersonalityProfile,
        *,
        reason: str,
    ) -> None:
        path = self.memory_dir / "personality.md"
        metadata = {
            "schema_version": profile.schema_version,
            "profile_id": profile.profile_id,
            "display_name": profile.display_name,
            "inspiration": profile.inspiration,
            "background_story": profile.background_story,
            "traits": profile.traits,
            "interaction_style": profile.interaction_style,
            "boundaries": profile.boundaries,
            "last_ada_write_reason": reason,
        }
        body = (
            "# Personality\n\n"
            "The TOML front matter above is the current authoritative personality "
            "profile for this development Memory root. Manual edits are read on "
            "the next load.\n"
        )
        self._write_markdown(path, metadata, body)

    def remember_explicit(
        self,
        *,
        entry_id: str,
        kind: MemoryKind,
        content: str,
    ) -> MemoryEntry:
        """Establish one trusted application-confirmed explicit user statement.

        This is not a model tool. Callers must already have established that the
        user explicitly supplied the statement in trusted application context.
        """

        self._validate_entry_id(entry_id)
        self._require_unused_entry_id(entry_id)
        entry = MemoryEntry(
            entry_id=entry_id,
            kind=kind,
            evidence_origin=EvidenceOrigin.EXPLICIT_STATEMENT,
            lifecycle=MemoryLifecycle.CONFIRMED,
            content=self._validate_content(content),
            confirmation_basis=ConfirmationBasis.EXPLICIT_USER,
        )
        self._write_entry(
            self.memory_dir / f"{entry_id}.md",
            entry,
            create_only=True,
        )
        return entry

    def record_learning(
        self,
        *,
        entry_id: str,
        kind: MemoryKind,
        evidence_origin: EvidenceOrigin,
        content: str,
    ) -> MemoryEntry:
        """Record non-authoritative evidence without silently establishing Memory."""

        self._validate_entry_id(entry_id)
        if evidence_origin is EvidenceOrigin.EXPLICIT_STATEMENT:
            raise ValueError(
                "explicit statements belong in established Memory, not learning"
            )
        self._require_unused_entry_id(entry_id)

        lifecycle = (
            MemoryLifecycle.PROVISIONAL
            if evidence_origin is EvidenceOrigin.HYPOTHESIS
            else MemoryLifecycle.OBSERVED
        )
        entry = MemoryEntry(
            entry_id=entry_id,
            kind=kind,
            evidence_origin=evidence_origin,
            lifecycle=lifecycle,
            content=self._validate_content(content),
        )
        self._write_entry(
            self.learning_dir / f"{entry_id}.md",
            entry,
            create_only=True,
        )
        return entry

    def promote_learning(
        self,
        entry_id: str,
        *,
        confirmation_basis: ConfirmationBasis,
    ) -> MemoryEntry:
        """Promote evidence through a trusted Ada application confirmation.

        This is not a model tool. The baseline accepts only an Ada-owned
        explicit-user confirmation path; sensitivity/class-C/D validation is
        still a later gate before any user/model-facing write path is exposed.
        """

        self._validate_entry_id(entry_id)
        if confirmation_basis is not ConfirmationBasis.EXPLICIT_USER:
            raise ValueError(
                "the baseline only permits explicit-user-confirmed promotion"
            )

        memory_path = self.memory_dir / f"{entry_id}.md"
        if memory_path.exists():
            raise FileMemoryError(
                f"established Memory {entry_id!r} already exists; promotion will not overwrite it"
            )

        evidence = self.load_learning_entry(entry_id, include_inactive=True)
        if evidence is None:
            raise FileMemoryError(f"learning entry {entry_id!r} does not exist")
        if evidence.supports_memory_id is not None:
            raise FileMemoryError(
                f"learning entry {entry_id!r} already supports established Memory"
            )
        if evidence.lifecycle in {
            MemoryLifecycle.FORGOTTEN,
            MemoryLifecycle.SUPERSEDED,
        }:
            raise FileMemoryError(
                f"learning entry {entry_id!r} is not promotable in its current state"
            )

        established = MemoryEntry(
            entry_id=evidence.entry_id,
            kind=evidence.kind,
            evidence_origin=evidence.evidence_origin,
            lifecycle=MemoryLifecycle.CONFIRMED,
            content=evidence.content,
            confirmation_basis=confirmation_basis,
        )
        retained_evidence = MemoryEntry(
            entry_id=evidence.entry_id,
            kind=evidence.kind,
            evidence_origin=evidence.evidence_origin,
            lifecycle=evidence.lifecycle,
            content=evidence.content,
            confirmation_basis=None,
            supports_memory_id=established.entry_id,
        )
        self._write_entry(
            memory_path,
            established,
            create_only=True,
        )
        self._write_entry(
            self.learning_dir / f"{entry_id}.md",
            retained_evidence,
        )
        return established

    def forget(self, entry_id: str) -> bool:
        """Forget current Memory before any later retrieval/re-learning can use it.

        The current learning file becomes a content-free tombstone before the
        established Memory file is removed. A malformed learning file therefore
        does not block forgetting an otherwise valid established entry.
        """

        self._validate_entry_id(entry_id)
        memory_path = self.memory_dir / f"{entry_id}.md"
        learning_path = self.learning_dir / f"{entry_id}.md"

        memory_entry = (
            self._read_entry(memory_path)
            if memory_path.exists()
            else None
        )
        if memory_entry is None and not learning_path.exists():
            return False

        tombstone_kind = (
            memory_entry.kind
            if memory_entry is not None
            else MemoryKind.FACT
        )
        tombstone_origin = (
            memory_entry.evidence_origin
            if memory_entry is not None
            else EvidenceOrigin.HYPOTHESIS
        )

        if memory_entry is None and learning_path.exists():
            try:
                evidence = self._read_entry(learning_path)
            except FileMemoryError:
                evidence = None
            if evidence is not None:
                tombstone_kind = evidence.kind
                tombstone_origin = evidence.evidence_origin

        forgotten = MemoryEntry(
            entry_id=entry_id,
            kind=tombstone_kind,
            evidence_origin=tombstone_origin,
            lifecycle=MemoryLifecycle.FORGOTTEN,
            content=_FORGOTTEN_BODY,
        )
        self._write_entry(learning_path, forgotten)

        if memory_path.exists():
            self._reject_symlink(memory_path)
            try:
                memory_path.unlink()
            except OSError as exc:
                raise FileMemoryError(
                    f"cannot remove established Memory file {memory_path}"
                ) from exc

        return True

    def load_memory_entry(self, entry_id: str) -> MemoryEntry | None:
        self._validate_entry_id(entry_id)
        path = self.memory_dir / f"{entry_id}.md"
        if not path.exists():
            return None
        entry = self._read_entry(path)
        if entry.lifecycle is MemoryLifecycle.FORGOTTEN:
            return None
        return entry

    def load_learning_entry(
        self,
        entry_id: str,
        *,
        include_inactive: bool = False,
    ) -> MemoryEntry | None:
        self._validate_entry_id(entry_id)
        path = self.learning_dir / f"{entry_id}.md"
        if not path.exists():
            return None
        entry = self._read_entry(path)
        if not include_inactive and (
            entry.lifecycle in {
                MemoryLifecycle.FORGOTTEN,
                MemoryLifecycle.SUPERSEDED,
            }
            or entry.supports_memory_id is not None
        ):
            return None
        return entry

    def _write_entry(
        self,
        path: Path,
        entry: MemoryEntry,
        *,
        create_only: bool = False,
    ) -> None:
        metadata: dict[str, Any] = {
            "schema_version": 1,
            "entry_id": entry.entry_id,
            "kind": entry.kind.value,
            "evidence_origin": entry.evidence_origin.value,
            "lifecycle": entry.lifecycle.value,
        }
        if entry.confirmation_basis is not None:
            metadata["confirmation_basis"] = entry.confirmation_basis.value
        if entry.supports_memory_id is not None:
            metadata["supports_memory_id"] = entry.supports_memory_id
        self._write_markdown(
            path,
            metadata,
            f"{entry.content}\n",
            create_only=create_only,
        )

    def _read_entry(self, path: Path) -> MemoryEntry:
        metadata, body = self._read_markdown(path)
        try:
            if self._require_int(metadata, "schema_version") != 1:
                raise ValueError("unsupported Memory entry schema")
            entry_id = self._require_str(metadata, "entry_id")
            self._validate_entry_id(entry_id)
            supports_memory_id = (
                self._require_str(metadata, "supports_memory_id")
                if "supports_memory_id" in metadata
                else None
            )
            if supports_memory_id is not None:
                self._validate_entry_id(supports_memory_id)
                if supports_memory_id != entry_id:
                    raise ValueError(
                        "baseline learning evidence may only support the same entry id"
                    )
            lifecycle = MemoryLifecycle(
                self._require_str(metadata, "lifecycle")
            )
            content = (
                body.strip()
                if lifecycle is MemoryLifecycle.FORGOTTEN
                else self._validate_content(body)
            )
            entry = MemoryEntry(
                entry_id=entry_id,
                kind=MemoryKind(self._require_str(metadata, "kind")),
                evidence_origin=EvidenceOrigin(
                    self._require_str(metadata, "evidence_origin")
                ),
                lifecycle=lifecycle,
                content=content,
                confirmation_basis=(
                    ConfirmationBasis(
                        self._require_str(metadata, "confirmation_basis")
                    )
                    if "confirmation_basis" in metadata
                    else None
                ),
                supports_memory_id=supports_memory_id,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise FileMemoryError(f"invalid Memory entry metadata in {path}") from exc

        if entry.entry_id != path.stem:
            raise FileMemoryError(
                f"Memory entry id {entry.entry_id!r} does not match file {path.name!r}"
            )
        return entry

    def _read_markdown(self, path: Path) -> tuple[dict[str, Any], str]:
        self._reject_symlink(path)
        try:
            mode = path.stat(follow_symlinks=False).st_mode
        except OSError as exc:
            raise FileMemoryError(f"cannot stat Memory file {path}") from exc
        if not stat.S_ISREG(mode):
            raise FileMemoryError(f"Memory file must be a regular file: {path}")

        try:
            text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
        except OSError as exc:
            raise FileMemoryError(f"cannot read Memory file {path}") from exc

        if not text.startswith("+++\n"):
            raise FileMemoryError(f"missing TOML front matter in {path}")
        delimiter = "\n+++\n"
        end = text.find(delimiter, 4)
        if end < 0:
            raise FileMemoryError(f"unterminated TOML front matter in {path}")

        metadata_text = text[4:end]
        body = text[end + len(delimiter):]
        try:
            metadata = tomllib.loads(metadata_text)
        except tomllib.TOMLDecodeError as exc:
            raise FileMemoryError(f"invalid TOML front matter in {path}") from exc
        return metadata, body

    def _write_markdown(
        self,
        path: Path,
        metadata: dict[str, Any],
        body: str,
        *,
        create_only: bool = False,
    ) -> None:
        self._reject_symlink(path)
        header = "\n".join(
            f"{key} = {self._toml_value(value)}"
            for key, value in metadata.items()
        )
        try:
            tomllib.loads(header)
        except tomllib.TOMLDecodeError as exc:
            raise FileMemoryError(
                f"refusing to write invalid TOML front matter for {path}"
            ) from exc
        text = f"+++\n{header}\n+++\n\n{body.rstrip()}\n"
        self._atomic_write(path, text, create_only=create_only)

    def _atomic_write(
        self,
        path: Path,
        text: str,
        *,
        create_only: bool = False,
    ) -> None:
        self._ensure_directory(path.parent)
        temp_name: str | None = None
        try:
            with NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=path.parent,
                prefix=f".{path.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temp_name = handle.name
                handle.write(text)
                handle.flush()
                os.fsync(handle.fileno())

            if create_only:
                try:
                    os.link(temp_name, path)
                except FileExistsError as exc:
                    raise FileMemoryError(
                        f"Memory file already exists and will not be overwritten: {path}"
                    ) from exc
            else:
                Path(temp_name).replace(path)
        except (OSError, UnicodeError) as exc:
            if isinstance(exc, FileMemoryError):
                raise
            raise FileMemoryError(f"cannot write Memory file {path}") from exc
        finally:
            if temp_name is not None:
                temp = Path(temp_name)
                if temp.exists():
                    temp.unlink()

    @staticmethod
    def _toml_value(value: Any) -> str:
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, int):
            return str(value)
        if isinstance(value, str):
            return json.dumps(value, ensure_ascii=False)
        if isinstance(value, (tuple, list)):
            return "[" + ", ".join(
                FileMemoryStore._toml_value(item) for item in value
            ) + "]"
        raise TypeError(f"unsupported TOML metadata value: {type(value).__name__}")

    @staticmethod
    def _require_int(metadata: dict[str, Any], key: str) -> int:
        value = metadata[key]
        if type(value) is not int:
            raise TypeError(f"{key} must be an integer")
        return value

    @staticmethod
    def _require_str(
        metadata: dict[str, Any],
        key: str,
    ) -> str:
        value = metadata[key]
        if not isinstance(value, str):
            raise TypeError(f"{key} must be a string")
        value = value.strip()
        if not value:
            raise ValueError(f"{key} must not be empty")
        return value

    @staticmethod
    def _string_tuple(
        metadata: dict[str, Any],
        key: str,
    ) -> tuple[str, ...]:
        value = metadata[key]
        if not isinstance(value, list) or not value or not all(
            isinstance(item, str) and item.strip() for item in value
        ):
            raise TypeError(f"{key} must be a non-empty array of non-empty strings")
        return tuple(item.strip() for item in value)

    def _require_unused_entry_id(self, entry_id: str) -> None:
        if (
            (self.memory_dir / f"{entry_id}.md").exists()
            or (self.learning_dir / f"{entry_id}.md").exists()
        ):
            raise FileMemoryError(
                f"entry id {entry_id!r} already exists and will not be overwritten"
            )

    @staticmethod
    def _validate_entry_id(entry_id: str) -> None:
        if _ENTRY_ID.fullmatch(entry_id) is None:
            raise ValueError(
                "Memory entry id must be a lowercase safe slug of at most 64 characters"
            )
        if entry_id in _RESERVED_ENTRY_IDS:
            raise ValueError(
                f"Memory entry id {entry_id!r} is reserved for Ada-owned state"
            )

    @staticmethod
    def _validate_content(content: str) -> str:
        content = content.strip()
        if not content:
            raise ValueError("Memory content must not be empty")
        return content

    @staticmethod
    def _ensure_directory(path: Path) -> None:
        if path.is_symlink():
            raise FileMemoryError(f"Memory directory must not be a symlink: {path}")
        try:
            path.mkdir(mode=0o700, parents=True, exist_ok=True)
        except OSError as exc:
            raise FileMemoryError(f"cannot create Memory directory {path}") from exc
        if not path.is_dir():
            raise FileMemoryError(f"Memory path is not a directory: {path}")

    @staticmethod
    def _reject_symlink(path: Path) -> None:
        if path.is_symlink():
            raise FileMemoryError(f"Memory file must not be a symlink: {path}")
