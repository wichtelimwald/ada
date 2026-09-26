from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
import errno
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import stat
import sys
import tomllib
from typing import Any

from ada.adapters.dulwich_memory_history import (
    DulwichMemoryHistory,
    MemoryHistoryError,
)
from ada.core.memory import (
    ConfirmationBasis,
    EvidenceOrigin,
    ForgetResult,
    MemoryEntry,
    MemoryKind,
    MemoryLifecycle,
    VersionedMemoryEntry,
)
from ada.core.personality import PersonalityProfile
from ada.ports.memory_history import MemoryHistoryPort


_ENTRY_ID = re.compile(r"m_[0-9a-f]{32}")
_RESERVED_ENTRY_IDS = frozenset({"personality"})
_FORGOTTEN_BODY = "[forgotten]"
_CURRENT_MEMORY_LIFECYCLES = frozenset({MemoryLifecycle.CONFIRMED})
_ESTABLISHED_LIFECYCLES = frozenset(
    {
        MemoryLifecycle.CONFIRMED,
        MemoryLifecycle.STALE,
        MemoryLifecycle.CONTRADICTED,
        MemoryLifecycle.SUPERSEDED,
    }
)
_LEARNING_LIFECYCLES = frozenset(
    {
        MemoryLifecycle.OBSERVED,
        MemoryLifecycle.PROVISIONAL,
        MemoryLifecycle.CONTRADICTED,
        MemoryLifecycle.SUPERSEDED,
        MemoryLifecycle.FORGOTTEN,
    }
)


class FileMemoryError(RuntimeError):
    """The file-native Memory store could not be read or written safely."""


class FileMemoryConflictError(FileMemoryError):
    """A concurrent or stale Memory write was rejected without overwriting it."""


class FileMemoryHistoryPendingError(FileMemoryError):
    """Current Memory changed, but its history revision could not be captured."""


class FileMemoryRecoveryRequiredError(FileMemoryError):
    """A Memory state change is active, but deterministic cleanup is incomplete."""


class FileMemoryStore:
    """Human-readable current Memory with Git-style recovery history.

    Current Markdown files remain the only semantic Memory authority. History is
    recovery/versioning state only and is never consulted for normal retrieval.
    This store is still development-only until MVP-30 adds protection domains,
    broker-mediated access and encryption.
    """

    def __init__(
        self,
        root: str | Path,
        *,
        history: MemoryHistoryPort | None = None,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        if isinstance(root, str) and not root.strip():
            raise FileMemoryError("Memory root must not be blank")
        if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
            raise FileMemoryError(
                "Memory storage requires POSIX O_NOFOLLOW and O_DIRECTORY support"
            )

        expanded = Path(root).expanduser()
        if expanded.is_symlink():
            raise FileMemoryError(
                f"Memory root must not be a symlink: {expanded}"
            )

        self.root = expanded.resolve()
        self.memory_dir = self.root / "memory"
        self.learning_dir = self.root / "learning"
        self.history_dir = self.root / ".ada-history.git"
        self._id_factory = id_factory or (lambda: secrets.token_hex(16))

        self._ensure_directory(self.root)
        self._ensure_directory(self.memory_dir)
        self._ensure_directory(self.learning_dir)

        with self._exclusive_lock():
            self._history = history or DulwichMemoryHistory(self.history_dir)
            self._capture_external_changes(
                reason="Capture current Memory state"
            )

    def load_personality(self) -> PersonalityProfile | None:
        with self._exclusive_lock():
            self._capture_external_changes(reason="Capture external Memory edits")
            path = self.memory_dir / "personality.md"
            if not self._path_exists(path):
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
        """Initialize personality without ever clobbering an existing profile."""

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
        rendered = self._render_markdown(metadata, body)

        with self._exclusive_lock():
            self._capture_external_changes(reason="Capture external Memory edits")
            if self._path_exists(path):
                return

            before = self._snapshot_current_files()
            try:
                self._write_bytes(path, rendered, create_only=True)
            except FileMemoryConflictError:
                self._capture_external_changes(
                    reason="Capture concurrent personality initialization"
                )
                return

            desired = dict(before)
            desired["memory/personality.md"] = rendered
            self._finalize_mutation(
                desired,
                reason=reason,
            )

    def remember_explicit(
        self,
        *,
        kind: MemoryKind,
        content: str,
    ) -> MemoryEntry:
        """Create one trusted application-confirmed explicit statement.

        This remains an application-internal primitive, not a model tool.
        Model/user-facing trust and sensitivity validation is an MVP-40 gate.
        """

        with self._exclusive_lock():
            self._capture_external_changes(reason="Capture external Memory edits")
            entry_id = self._new_entry_id()
            entry = MemoryEntry(
                entry_id=entry_id,
                kind=kind,
                evidence_origin=EvidenceOrigin.EXPLICIT_STATEMENT,
                lifecycle=MemoryLifecycle.CONFIRMED,
                content=self._validate_content(content),
                confirmation_basis=ConfirmationBasis.EXPLICIT_USER,
            )
            before = self._snapshot_current_files()
            path = self.memory_dir / f"{entry_id}.md"
            rendered = self._render_entry(entry)
            self._write_bytes(path, rendered, create_only=True)
            desired = dict(before)
            desired[f"memory/{entry_id}.md"] = rendered
            self._finalize_mutation(
                desired,
                reason=f"Create established Memory {entry_id}",
            )
            return entry

    def correct_memory(
        self,
        entry_id: str,
        *,
        content: str,
        expected_revision: str,
    ) -> VersionedMemoryEntry:
        """Correct one current entry using optimistic same-file concurrency."""

        self._validate_entry_id(entry_id)
        if not expected_revision.strip():
            raise ValueError("expected Memory revision must not be blank")

        with self._exclusive_lock():
            self._capture_external_changes(reason="Capture external Memory edits")
            if self._is_forgotten(entry_id):
                raise FileMemoryConflictError(
                    f"Memory entry {entry_id!r} is already forgotten"
                )

            path = self.memory_dir / f"{entry_id}.md"
            if not self._path_exists(path):
                raise FileMemoryError(
                    f"established Memory {entry_id!r} does not exist"
                )
            raw = self._read_bytes(path)
            current_revision = self._revision(raw)
            if current_revision != expected_revision:
                raise FileMemoryConflictError(
                    f"established Memory {entry_id!r} changed since it was read"
                )

            current = self._parse_entry(path, raw, area="memory")
            if current.lifecycle not in _CURRENT_MEMORY_LIFECYCLES:
                raise FileMemoryConflictError(
                    f"established Memory {entry_id!r} is not current"
                )

            corrected = MemoryEntry(
                entry_id=entry_id,
                kind=current.kind,
                evidence_origin=EvidenceOrigin.EXPLICIT_STATEMENT,
                lifecycle=MemoryLifecycle.CONFIRMED,
                content=self._validate_content(content),
                confirmation_basis=ConfirmationBasis.EXPLICIT_USER,
            )
            rendered = self._render_entry(corrected)
            before = self._snapshot_current_files()

            # Recheck immediately before publication. This narrows the
            # non-cooperating-editor race without pretending advisory locks bind
            # arbitrary editors.
            if self._revision(self._read_bytes(path)) != expected_revision:
                self._capture_external_changes(
                    reason="Capture concurrent external Memory edit"
                )
                raise FileMemoryConflictError(
                    f"established Memory {entry_id!r} changed during correction"
                )

            self._write_bytes(path, rendered)
            desired = dict(before)
            desired[f"memory/{entry_id}.md"] = rendered
            self._finalize_mutation(
                desired,
                reason=f"Correct established Memory {entry_id}",
            )
            return VersionedMemoryEntry(
                entry=corrected,
                revision=self._revision(rendered),
            )

    def record_learning(
        self,
        *,
        kind: MemoryKind,
        evidence_origin: EvidenceOrigin,
        content: str,
    ) -> MemoryEntry:
        """Record non-authoritative evidence without establishing Memory."""

        if evidence_origin is EvidenceOrigin.EXPLICIT_STATEMENT:
            raise ValueError(
                "explicit statements belong in established Memory, not learning"
            )

        with self._exclusive_lock():
            self._capture_external_changes(reason="Capture external Memory edits")
            entry_id = self._new_entry_id()
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
            before = self._snapshot_current_files()
            path = self.learning_dir / f"{entry_id}.md"
            rendered = self._render_entry(entry)
            self._write_bytes(path, rendered, create_only=True)
            desired = dict(before)
            desired[f"learning/{entry_id}.md"] = rendered
            self._finalize_mutation(
                desired,
                reason=f"Record learning evidence {entry_id}",
            )
            return entry

    def promote_learning(
        self,
        entry_id: str,
        *,
        confirmation_basis: ConfirmationBasis,
    ) -> MemoryEntry:
        """Promote evidence only through explicit trusted-user confirmation."""

        self._validate_entry_id(entry_id)
        if confirmation_basis is not ConfirmationBasis.EXPLICIT_USER:
            raise ValueError(
                "the baseline only permits explicit-user-confirmed promotion"
            )

        with self._exclusive_lock():
            self._capture_external_changes(reason="Capture external Memory edits")
            memory_path = self.memory_dir / f"{entry_id}.md"
            if self._path_exists(memory_path):
                raise FileMemoryError(
                    f"established Memory {entry_id!r} already exists; "
                    "promotion will not overwrite it"
                )

            evidence = self._load_learning_entry_unlocked(
                entry_id,
                include_inactive=True,
            )
            if evidence is None:
                raise FileMemoryError(
                    f"learning entry {entry_id!r} does not exist"
                )
            if evidence.lifecycle in {
                MemoryLifecycle.FORGOTTEN,
                MemoryLifecycle.SUPERSEDED,
                MemoryLifecycle.CONTRADICTED,
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
            before = self._snapshot_current_files()
            rendered = self._render_entry(established)
            self._write_bytes(memory_path, rendered, create_only=True)
            desired = dict(before)
            desired[f"memory/{entry_id}.md"] = rendered
            self._finalize_mutation(
                desired,
                reason=f"Promote learning evidence {entry_id}",
            )
            return established

    def forget(self, entry_id: str) -> ForgetResult:
        """Remove one identity from current Memory with an idempotent tombstone."""

        self._validate_entry_id(entry_id)
        with self._exclusive_lock():
            self._capture_external_changes(reason="Capture external Memory edits")
            memory_path = self.memory_dir / f"{entry_id}.md"
            learning_path = self.learning_dir / f"{entry_id}.md"

            memory_entry: MemoryEntry | None = None
            learning_entry: MemoryEntry | None = None

            if self._path_exists(memory_path):
                # Integrity errors intentionally propagate before any mutation.
                raw = self._read_bytes(memory_path)
                memory_entry = self._parse_entry(memory_path, raw, area="memory")

            if self._path_exists(learning_path):
                raw = self._read_bytes(learning_path)
                learning_entry = self._parse_entry(
                    learning_path,
                    raw,
                    area="learning",
                )
                if learning_entry.lifecycle is MemoryLifecycle.FORGOTTEN:
                    return ForgetResult.ALREADY_FORGOTTEN

            if memory_entry is None and learning_entry is None:
                return ForgetResult.NOT_FOUND

            source = memory_entry or learning_entry
            assert source is not None
            forgotten = MemoryEntry(
                entry_id=entry_id,
                kind=source.kind,
                evidence_origin=source.evidence_origin,
                lifecycle=MemoryLifecycle.FORGOTTEN,
                content=_FORGOTTEN_BODY,
            )
            tombstone = self._render_entry(forgotten)
            before = self._snapshot_current_files()

            # Tombstone first: if deletion later fails/crashes, normal reads
            # already treat this identity as forgotten and cannot re-promote its
            # learning evidence.
            self._write_bytes(
                learning_path,
                tombstone,
                create_only=not self._path_exists(learning_path),
            )
            if self._path_exists(memory_path):
                try:
                    self._unlink_regular(memory_path)
                except FileMemoryError as exc:
                    # The tombstone already makes the identity forgotten in
                    # current semantics. Preserve/capture that exact partial
                    # state and report it explicitly instead of returning an
                    # ambiguous generic failure.
                    partial = self._snapshot_current_files()
                    try:
                        self._history.capture_snapshot(
                            partial,
                            reason=(
                                f"Capture partial forget requiring cleanup "
                                f"{entry_id}"
                            ),
                        )
                    except MemoryHistoryError as history_exc:
                        raise FileMemoryRecoveryRequiredError(
                            f"Memory {entry_id!r} is forgotten in current "
                            "semantics, established-file cleanup failed, and "
                            "the partial state could not be captured in history"
                        ) from history_exc
                    raise FileMemoryRecoveryRequiredError(
                        f"Memory {entry_id!r} is forgotten in current semantics, "
                        "but established-file cleanup failed; recovery is required"
                    ) from exc

            desired = dict(before)
            desired[f"learning/{entry_id}.md"] = tombstone
            desired.pop(f"memory/{entry_id}.md", None)
            self._finalize_mutation(
                desired,
                reason=f"Forget Memory {entry_id}",
            )
            return ForgetResult.FORGOTTEN

    def load_memory_entry(
        self,
        entry_id: str,
        *,
        include_inactive: bool = False,
    ) -> MemoryEntry | None:
        versioned = self.load_memory_entry_versioned(
            entry_id,
            include_inactive=include_inactive,
        )
        return None if versioned is None else versioned.entry

    def load_memory_entry_versioned(
        self,
        entry_id: str,
        *,
        include_inactive: bool = False,
    ) -> VersionedMemoryEntry | None:
        self._validate_entry_id(entry_id)
        with self._exclusive_lock():
            self._capture_external_changes(reason="Capture external Memory edits")
            if self._is_forgotten(entry_id):
                return None

            path = self.memory_dir / f"{entry_id}.md"
            if not self._path_exists(path):
                return None
            raw = self._read_bytes(path)
            entry = self._parse_entry(path, raw, area="memory")
            if not include_inactive and entry.lifecycle not in _CURRENT_MEMORY_LIFECYCLES:
                return None
            return VersionedMemoryEntry(
                entry=entry,
                revision=self._revision(raw),
            )

    def load_learning_entry(
        self,
        entry_id: str,
        *,
        include_inactive: bool = False,
    ) -> MemoryEntry | None:
        self._validate_entry_id(entry_id)
        with self._exclusive_lock():
            self._capture_external_changes(reason="Capture external Memory edits")
            return self._load_learning_entry_unlocked(
                entry_id,
                include_inactive=include_inactive,
            )

    def _load_learning_entry_unlocked(
        self,
        entry_id: str,
        *,
        include_inactive: bool,
    ) -> MemoryEntry | None:
        path = self.learning_dir / f"{entry_id}.md"
        if not self._path_exists(path):
            return None
        raw = self._read_bytes(path)
        entry = self._parse_entry(path, raw, area="learning")

        if include_inactive:
            return entry

        if entry.lifecycle in {
            MemoryLifecycle.FORGOTTEN,
            MemoryLifecycle.SUPERSEDED,
            MemoryLifecycle.CONTRADICTED,
        }:
            return None

        # Promotion uses the same immutable identity. Once an established file
        # exists, the learning evidence is inspectable but no longer an active
        # promotion candidate, even after a crash before metadata cleanup.
        memory_path = self.memory_dir / f"{entry_id}.md"
        if self._path_exists(memory_path):
            self._parse_entry(
                memory_path,
                self._read_bytes(memory_path),
                area="memory",
            )
            return None
        return entry

    def _is_forgotten(self, entry_id: str) -> bool:
        path = self.learning_dir / f"{entry_id}.md"
        if not self._path_exists(path):
            return False
        entry = self._parse_entry(
            path,
            self._read_bytes(path),
            area="learning",
        )
        return entry.lifecycle is MemoryLifecycle.FORGOTTEN

    def _new_entry_id(self) -> str:
        for _ in range(64):
            raw = self._id_factory()
            candidate = raw if raw.startswith("m_") else f"m_{raw}"
            self._validate_entry_id(candidate)
            if self._entry_exists_now(candidate):
                continue
            try:
                if self._history.has_seen_entry_id(candidate):
                    continue
            except MemoryHistoryError as exc:
                raise FileMemoryError(
                    "cannot verify Memory identity uniqueness in history"
                ) from exc
            return candidate
        raise FileMemoryError("could not allocate a unique opaque Memory entry id")

    def _entry_exists_now(self, entry_id: str) -> bool:
        return (
            self._path_exists(self.memory_dir / f"{entry_id}.md")
            or self._path_exists(self.learning_dir / f"{entry_id}.md")
        )

    def _render_entry(self, entry: MemoryEntry) -> bytes:
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
        return self._render_markdown(
            metadata,
            f"{entry.content}\n",
        )

    def _parse_entry(
        self,
        path: Path,
        raw: bytes,
        *,
        area: str,
    ) -> MemoryEntry:
        metadata, body = self._parse_markdown(path, raw)
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
                        "learning evidence may only support the same immutable entry id"
                    )
            lifecycle = MemoryLifecycle(
                self._require_str(metadata, "lifecycle")
            )
            if area == "memory" and lifecycle not in _ESTABLISHED_LIFECYCLES:
                raise ValueError(
                    f"lifecycle {lifecycle.value!r} is invalid in established Memory"
                )
            if area == "learning" and lifecycle not in _LEARNING_LIFECYCLES:
                raise ValueError(
                    f"lifecycle {lifecycle.value!r} is invalid in learning"
                )

            if lifecycle is MemoryLifecycle.FORGOTTEN:
                if body.strip() != _FORGOTTEN_BODY:
                    raise ValueError("forgotten Memory tombstone must be content-free")
                content = _FORGOTTEN_BODY
            else:
                content = self._validate_content(body)

            evidence_origin = EvidenceOrigin(
                self._require_str(metadata, "evidence_origin")
            )
            if (
                area == "learning"
                and evidence_origin is EvidenceOrigin.EXPLICIT_STATEMENT
            ):
                raise ValueError(
                    "explicit statements are invalid in the learning area"
                )

            entry = MemoryEntry(
                entry_id=entry_id,
                kind=MemoryKind(self._require_str(metadata, "kind")),
                evidence_origin=evidence_origin,
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
            raise FileMemoryError(
                f"invalid Memory entry metadata in {path}"
            ) from exc

        if entry.entry_id != path.stem:
            raise FileMemoryError(
                f"Memory entry id {entry.entry_id!r} does not match file {path.name!r}"
            )
        return entry

    def _read_markdown(self, path: Path) -> tuple[dict[str, Any], str]:
        return self._parse_markdown(path, self._read_bytes(path))

    def _parse_markdown(
        self,
        path: Path,
        raw: bytes,
    ) -> tuple[dict[str, Any], str]:
        try:
            text = raw.decode("utf-8").replace("\r\n", "\n")
        except UnicodeDecodeError as exc:
            raise FileMemoryError(
                f"Memory file is not valid UTF-8: {path}"
            ) from exc

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
            raise FileMemoryError(
                f"invalid TOML front matter in {path}"
            ) from exc
        return metadata, body

    def _render_markdown(
        self,
        metadata: Mapping[str, Any],
        body: str,
    ) -> bytes:
        header = "\n".join(
            f"{key} = {self._toml_value(value)}"
            for key, value in metadata.items()
        )
        try:
            tomllib.loads(header)
        except tomllib.TOMLDecodeError as exc:
            raise FileMemoryError(
                "refusing to write invalid TOML front matter"
            ) from exc
        text = f"+++\n{header}\n+++\n\n{body.rstrip()}\n"
        return text.encode("utf-8")

    def _capture_external_changes(self, *, reason: str) -> None:
        snapshot = self._snapshot_current_files()
        try:
            self._history.capture_snapshot(snapshot, reason=reason)
        except MemoryHistoryError as exc:
            raise FileMemoryError(
                "cannot capture current Memory state in recovery history"
            ) from exc

    def _finalize_mutation(
        self,
        desired_snapshot: Mapping[str, bytes],
        *,
        reason: str,
    ) -> None:
        try:
            self._history.capture_snapshot(
                desired_snapshot,
                reason=reason,
            )
        except MemoryHistoryError as exc:
            current = self._snapshot_current_files()
            if current == dict(desired_snapshot):
                raise FileMemoryHistoryPendingError(
                    "Memory write is current, but recovery history capture failed"
                ) from exc
            raise FileMemoryConflictError(
                "Memory changed during a write and recovery history capture failed"
            ) from exc

        current = self._snapshot_current_files()
        desired = dict(desired_snapshot)
        if current == desired:
            return

        try:
            self._history.capture_snapshot(
                current,
                reason="Capture concurrent external Memory edit",
            )
        except MemoryHistoryError as exc:
            raise FileMemoryConflictError(
                "concurrent external Memory edit detected; "
                "current files were preserved but history capture failed"
            ) from exc
        raise FileMemoryConflictError(
            "concurrent external Memory edit detected; current file state wins"
        )

    def _snapshot_current_files(self) -> dict[str, bytes]:
        snapshot: dict[str, bytes] = {}
        for area, directory in (
            ("memory", self.memory_dir),
            ("learning", self.learning_dir),
        ):
            dir_fd = self._open_directory(directory)
            try:
                try:
                    names = os.listdir(dir_fd)
                except OSError as exc:
                    raise FileMemoryError(
                        f"cannot scan Memory directory {directory}"
                    ) from exc
                for name in names:
                    if not name.endswith(".md"):
                        continue
                    path = directory / name
                    snapshot[f"{area}/{name}"] = self._read_bytes_from_dir_fd(
                        dir_fd,
                        name,
                        display_path=path,
                    )
            finally:
                os.close(dir_fd)
        return snapshot

    @contextmanager
    def _exclusive_lock(self) -> Iterator[None]:
        dir_fd = self._open_directory(self.root)
        lock_fd: int | None = None
        try:
            flags = os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW
            try:
                lock_fd = os.open(
                    ".ada-memory.lock",
                    flags,
                    0o600,
                    dir_fd=dir_fd,
                )
            except OSError as exc:
                raise FileMemoryError(
                    f"cannot open Memory lock under {self.root}"
                ) from exc
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_EX)
            except OSError as exc:
                raise FileMemoryError("cannot acquire Memory lock") from exc
            yield
        finally:
            if lock_fd is not None:
                try:
                    fcntl.flock(lock_fd, fcntl.LOCK_UN)
                finally:
                    os.close(lock_fd)
            os.close(dir_fd)

    def _read_bytes(self, path: Path) -> bytes:
        dir_fd = self._open_directory(path.parent)
        try:
            return self._read_bytes_from_dir_fd(
                dir_fd,
                path.name,
                display_path=path,
            )
        finally:
            os.close(dir_fd)

    @staticmethod
    def _read_bytes_from_dir_fd(
        dir_fd: int,
        name: str,
        *,
        display_path: Path,
    ) -> bytes:
        fd: int | None = None
        try:
            try:
                fd = os.open(
                    name,
                    os.O_RDONLY | os.O_NOFOLLOW,
                    dir_fd=dir_fd,
                )
            except FileNotFoundError:
                raise
            except OSError as exc:
                if exc.errno == errno.ELOOP:
                    raise FileMemoryError(
                        f"Memory file must not be a symlink: {display_path}"
                    ) from exc
                raise FileMemoryError(
                    f"cannot open Memory file {display_path}"
                ) from exc

            try:
                mode = os.fstat(fd).st_mode
            except OSError as exc:
                raise FileMemoryError(
                    f"cannot stat Memory file {display_path}"
                ) from exc
            if not stat.S_ISREG(mode):
                raise FileMemoryError(
                    f"Memory file must be a regular file: {display_path}"
                )

            with os.fdopen(fd, "rb", closefd=True) as handle:
                fd = None
                return handle.read()
        except FileNotFoundError as exc:
            raise FileMemoryConflictError(
                f"Memory file changed while being read: {display_path}"
            ) from exc
        except OSError as exc:
            raise FileMemoryError(
                f"cannot read Memory file {display_path}"
            ) from exc
        finally:
            if fd is not None:
                os.close(fd)

    def _write_bytes(
        self,
        path: Path,
        content: bytes,
        *,
        create_only: bool = False,
    ) -> None:
        dir_fd = self._open_directory(path.parent)
        try:
            if create_only:
                self._create_bytes(dir_fd, path, content)
            else:
                self._replace_bytes(dir_fd, path, content)
        finally:
            os.close(dir_fd)

    def _create_bytes(
        self,
        dir_fd: int,
        path: Path,
        content: bytes,
    ) -> None:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
        try:
            fd = os.open(
                path.name,
                flags,
                0o600,
                dir_fd=dir_fd,
            )
        except FileExistsError as exc:
            raise FileMemoryConflictError(
                f"Memory file already exists and will not be overwritten: {path}"
            ) from exc
        except OSError as exc:
            raise FileMemoryError(
                f"cannot create Memory file {path}"
            ) from exc

        try:
            self._write_and_sync(fd, content)
        finally:
            os.close(fd)
        self._sync_directory(dir_fd, path.parent)

    def _replace_bytes(
        self,
        dir_fd: int,
        path: Path,
        content: bytes,
    ) -> None:
        temp_name = f".{path.name}.{secrets.token_hex(8)}.tmp"
        temp_fd: int | None = None
        try:
            temp_fd = os.open(
                temp_name,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600,
                dir_fd=dir_fd,
            )
            self._write_and_sync(temp_fd, content)
            os.close(temp_fd)
            temp_fd = None
            os.replace(
                temp_name,
                path.name,
                src_dir_fd=dir_fd,
                dst_dir_fd=dir_fd,
            )
            self._sync_directory(dir_fd, path.parent)
        except OSError as exc:
            raise FileMemoryError(
                f"cannot replace Memory file {path}"
            ) from exc
        finally:
            if temp_fd is not None:
                os.close(temp_fd)
            try:
                os.unlink(temp_name, dir_fd=dir_fd)
            except FileNotFoundError:
                pass

    def _unlink_regular(self, path: Path) -> None:
        dir_fd = self._open_directory(path.parent)
        try:
            try:
                mode = os.stat(
                    path.name,
                    dir_fd=dir_fd,
                    follow_symlinks=False,
                ).st_mode
            except FileNotFoundError:
                return
            except OSError as exc:
                raise FileMemoryError(
                    f"cannot stat Memory file {path}"
                ) from exc
            if not stat.S_ISREG(mode):
                raise FileMemoryError(
                    f"Memory file must be regular before deletion: {path}"
                )
            try:
                os.unlink(path.name, dir_fd=dir_fd)
            except OSError as exc:
                raise FileMemoryError(
                    f"cannot remove established Memory file {path}"
                ) from exc
            self._sync_directory(dir_fd, path.parent)
        finally:
            os.close(dir_fd)

    @staticmethod
    def _write_and_sync(fd: int, content: bytes) -> None:
        view = memoryview(content)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise FileMemoryError("short write while persisting Memory")
            view = view[written:]

        if sys.platform == "darwin":
            full_sync = getattr(fcntl, "F_FULLFSYNC", None)
            if full_sync is not None:
                try:
                    fcntl.fcntl(fd, full_sync)
                    return
                except OSError:
                    # Fall back to POSIX fsync; failure there still fails closed.
                    pass
        try:
            os.fsync(fd)
        except OSError as exc:
            raise FileMemoryError("cannot fsync Memory file") from exc

    @staticmethod
    def _sync_directory(dir_fd: int, path: Path) -> None:
        try:
            os.fsync(dir_fd)
        except OSError as exc:
            raise FileMemoryError(
                f"cannot fsync Memory directory {path}"
            ) from exc

    @staticmethod
    def _open_directory(path: Path) -> int:
        try:
            return os.open(
                path,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
            )
        except OSError as exc:
            if exc.errno == errno.ELOOP:
                raise FileMemoryError(
                    f"Memory directory must not be a symlink: {path}"
                ) from exc
            raise FileMemoryError(
                f"cannot open Memory directory {path}"
            ) from exc

    @staticmethod
    def _path_exists(path: Path) -> bool:
        dir_fd = FileMemoryStore._open_directory(path.parent)
        try:
            try:
                mode = os.stat(
                    path.name,
                    dir_fd=dir_fd,
                    follow_symlinks=False,
                ).st_mode
            except FileNotFoundError:
                return False
            except OSError as exc:
                raise FileMemoryError(
                    f"cannot stat Memory path {path}"
                ) from exc
            if stat.S_ISLNK(mode):
                raise FileMemoryError(
                    f"Memory file must not be a symlink: {path}"
                )
            if not stat.S_ISREG(mode):
                raise FileMemoryError(
                    f"Memory path is not a regular file: {path}"
                )
            return True
        finally:
            os.close(dir_fd)

    @staticmethod
    def _revision(content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

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
        raise TypeError(
            f"unsupported TOML metadata value: {type(value).__name__}"
        )

    @staticmethod
    def _require_int(metadata: Mapping[str, Any], key: str) -> int:
        value = metadata[key]
        if type(value) is not int:
            raise TypeError(f"{key} must be an integer")
        return value

    @staticmethod
    def _require_str(
        metadata: Mapping[str, Any],
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
        metadata: Mapping[str, Any],
        key: str,
    ) -> tuple[str, ...]:
        value = metadata[key]
        if not isinstance(value, list) or not value or not all(
            isinstance(item, str) and item.strip() for item in value
        ):
            raise TypeError(
                f"{key} must be a non-empty array of non-empty strings"
            )
        return tuple(item.strip() for item in value)

    @staticmethod
    def _validate_entry_id(entry_id: str) -> None:
        if entry_id in _RESERVED_ENTRY_IDS:
            raise ValueError(
                f"Memory entry id {entry_id!r} is reserved for Ada-owned state"
            )
        if _ENTRY_ID.fullmatch(entry_id) is None:
            raise ValueError(
                "Memory entry id must be an opaque m_<32 lowercase hex> identifier"
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
            raise FileMemoryError(
                f"Memory directory must not be a symlink: {path}"
            )
        try:
            path.mkdir(mode=0o700, parents=True, exist_ok=True)
        except OSError as exc:
            raise FileMemoryError(
                f"cannot create Memory directory {path}"
            ) from exc
        if not path.is_dir():
            raise FileMemoryError(
                f"Memory path is not a directory: {path}"
            )
        fd = FileMemoryStore._open_directory(path)
        os.close(fd)
