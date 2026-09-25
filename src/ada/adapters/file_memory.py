from __future__ import annotations

import json
from pathlib import Path
import re
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
        self.root = Path(root).expanduser().resolve()
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
            schema_version = int(metadata["schema_version"])
            if schema_version != 1:
                raise ValueError("unsupported personality Memory schema")
            return PersonalityProfile(
                schema_version=schema_version,
                profile_id=str(metadata["profile_id"]),
                display_name=str(metadata["display_name"]),
                inspiration=str(metadata["inspiration"]).strip(),
                background_story=str(metadata["background_story"]).strip(),
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
            "change_reason": reason,
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
        """Establish one explicit user statement directly as confirmed Memory."""

        self._validate_entry_id(entry_id)
        entry = MemoryEntry(
            entry_id=entry_id,
            kind=kind,
            evidence_origin=EvidenceOrigin.EXPLICIT_STATEMENT,
            lifecycle=MemoryLifecycle.CONFIRMED,
            content=self._validate_content(content),
            confirmation_basis=ConfirmationBasis.EXPLICIT_USER,
        )
        self._write_entry(self.memory_dir / f"{entry_id}.md", entry)
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
        if (self.memory_dir / f"{entry_id}.md").exists():
            raise FileMemoryError(
                f"entry id {entry_id!r} already exists in established Memory"
            )

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
        self._write_entry(self.learning_dir / f"{entry_id}.md", entry)
        return entry

    def promote_learning(
        self,
        entry_id: str,
        *,
        confirmation_basis: ConfirmationBasis,
    ) -> MemoryEntry:
        """Promote evidence through the first conservative Ada-owned rule.

        The baseline permits explicit-user confirmation only. Automatic
        observation-pattern promotion remains a later validation-policy slice.
        """

        self._validate_entry_id(entry_id)
        if confirmation_basis is not ConfirmationBasis.EXPLICIT_USER:
            raise ValueError(
                "the baseline only permits explicit-user-confirmed promotion"
            )

        evidence = self.load_learning_entry(entry_id, include_inactive=True)
        if evidence is None:
            raise FileMemoryError(f"learning entry {entry_id!r} does not exist")
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
            lifecycle=MemoryLifecycle.CONFIRMED,
            content=evidence.content,
            confirmation_basis=confirmation_basis,
            supports_memory_id=established.entry_id,
        )
        self._write_entry(self.memory_dir / f"{entry_id}.md", established)
        self._write_entry(self.learning_dir / f"{entry_id}.md", retained_evidence)
        return established

    def forget(self, entry_id: str) -> bool:
        """Remove current established Memory and neutralize retained evidence."""

        self._validate_entry_id(entry_id)
        changed = False
        memory_path = self.memory_dir / f"{entry_id}.md"
        evidence = self.load_learning_entry(entry_id, include_inactive=True)

        if memory_path.exists():
            self._reject_symlink(memory_path)
            memory_path.unlink()
            changed = True
        if evidence is not None and evidence.lifecycle is not MemoryLifecycle.FORGOTTEN:
            forgotten = MemoryEntry(
                entry_id=evidence.entry_id,
                kind=evidence.kind,
                evidence_origin=evidence.evidence_origin,
                lifecycle=MemoryLifecycle.FORGOTTEN,
                content=evidence.content,
                confirmation_basis=evidence.confirmation_basis,
                supports_memory_id=evidence.supports_memory_id,
            )
            self._write_entry(self.learning_dir / f"{entry_id}.md", forgotten)
            changed = True

        return changed

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
        if not include_inactive and entry.lifecycle in {
            MemoryLifecycle.FORGOTTEN,
            MemoryLifecycle.SUPERSEDED,
        }:
            return None
        return entry

    def _write_entry(self, path: Path, entry: MemoryEntry) -> None:
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
        self._write_markdown(path, metadata, f"{entry.content}\n")

    def _read_entry(self, path: Path) -> MemoryEntry:
        metadata, body = self._read_markdown(path)
        try:
            if int(metadata["schema_version"]) != 1:
                raise ValueError("unsupported Memory entry schema")
            entry = MemoryEntry(
                entry_id=str(metadata["entry_id"]),
                kind=MemoryKind(str(metadata["kind"])),
                evidence_origin=EvidenceOrigin(str(metadata["evidence_origin"])),
                lifecycle=MemoryLifecycle(str(metadata["lifecycle"])),
                content=self._validate_content(body),
                confirmation_basis=(
                    ConfirmationBasis(str(metadata["confirmation_basis"]))
                    if "confirmation_basis" in metadata
                    else None
                ),
                supports_memory_id=(
                    str(metadata["supports_memory_id"])
                    if "supports_memory_id" in metadata
                    else None
                ),
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
    ) -> None:
        self._reject_symlink(path)
        header = "\n".join(
            f"{key} = {self._toml_value(value)}"
            for key, value in metadata.items()
        )
        text = f"+++\n{header}\n+++\n\n{body.rstrip()}\n"
        self._atomic_write(path, text)

    def _atomic_write(self, path: Path, text: str) -> None:
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
                handle.write(text)
                handle.flush()
                temp_name = handle.name
            Path(temp_name).replace(path)
        except OSError as exc:
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
    def _string_tuple(
        metadata: dict[str, Any],
        key: str,
    ) -> tuple[str, ...]:
        value = metadata[key]
        if not isinstance(value, list) or not all(
            isinstance(item, str) for item in value
        ):
            raise TypeError(f"{key} must be an array of strings")
        return tuple(value)

    @staticmethod
    def _validate_entry_id(entry_id: str) -> None:
        if _ENTRY_ID.fullmatch(entry_id) is None:
            raise ValueError(
                "Memory entry id must be a lowercase safe slug of at most 64 characters"
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
            path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise FileMemoryError(f"cannot create Memory directory {path}") from exc
        if not path.is_dir():
            raise FileMemoryError(f"Memory path is not a directory: {path}")

    @staticmethod
    def _reject_symlink(path: Path) -> None:
        if path.is_symlink():
            raise FileMemoryError(f"Memory file must not be a symlink: {path}")
