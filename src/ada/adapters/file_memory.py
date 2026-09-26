from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import errno
import fcntl
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import stat
import sys
import tomllib
from typing import Any, Iterator
from uuid import uuid4

from ada.adapters.git_memory_history import (
    GitMemoryHistory,
    GitMemoryHistoryError,
)
from ada.core.memory import (
    ConfirmationBasis,
    EvidenceOrigin,
    ForgetResult,
    MemoryEntry,
    MemoryKind,
    MemoryLifecycle,
)
from ada.core.personality import PersonalityProfile


_ENTRY_ID = re.compile(r"m-[0-9a-f]{32}")
_FORGOTTEN_BODY = "[forgotten]"
_STALE_TEMP = re.compile(r"\.ada-memory-tmp-[0-9a-f]{32}")


class FileMemoryError(RuntimeError):
    """The file-native Memory store could not be read or written safely."""


class MemoryAlreadyExistsError(FileMemoryError):
    """A create-only Memory publication lost a race to an existing file."""


class MemoryConflictError(FileMemoryError):
    """The caller's revision is stale and current Memory must win."""


class MemoryHistoryCommitError(FileMemoryError):
    """Current files changed, but the matching history commit did not complete."""

    def __init__(self, message: str, *, paths: tuple[str, ...]) -> None:
        super().__init__(message)
        self.paths = paths
        self.current_state_applied = True


@dataclass(frozen=True, slots=True)
class MemorySnapshot:
    entry: MemoryEntry
    revision: str


@dataclass(frozen=True, slots=True)
class PersonalitySnapshot:
    profile: PersonalityProfile
    revision: str


class FileMemoryStore:
    """Current-file Memory adapter with safe local writes and Git history.

    Current Markdown files are authoritative. Git is recovery/versioning only and
    is never consulted by normal Memory reads.
    """

    def __init__(self, root: str | Path) -> None:
        if isinstance(root, str) and not root.strip():
            raise FileMemoryError("Memory root must not be blank")
        if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
            raise FileMemoryError(
                "file-native Memory requires POSIX O_NOFOLLOW/O_DIRECTORY support"
            )

        expanded = Path(root).expanduser()
        if expanded.is_symlink():
            raise FileMemoryError(
                f"Memory root must not be a symlink: {expanded}"
            )

        self.root = expanded.resolve()
        self._ensure_directory(self.root)
        self._history = GitMemoryHistory(self.root)
        self._history_call(self._history.validate_existing_repository)

        self.memory_dir = self.root / "memory"
        self.learning_dir = self.root / "learning"
        self._ensure_directory(self.memory_dir)
        self._ensure_directory(self.learning_dir)

        with self._write_lock():
            self._history_call(self._history.ensure_initialized)
            self._cleanup_stale_temp_files()
            self._capture_external_changes(
                message="Capture pre-existing Memory state",
            )

    def load_personality(self) -> PersonalityProfile | None:
        snapshot = self.load_personality_snapshot()
        return snapshot.profile if snapshot is not None else None

    def load_personality_snapshot(self) -> PersonalitySnapshot | None:
        path = self.memory_dir / "personality.md"
        if not self._path_exists(path):
            return None
        metadata, _body, revision = self._read_markdown(path)
        try:
            schema_version = self._require_int(metadata, "schema_version")
            if schema_version != 1:
                raise ValueError("unsupported personality Memory schema")
            profile = PersonalityProfile(
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
        return PersonalitySnapshot(profile=profile, revision=revision)

    def create_personality_if_absent(
        self,
        profile: PersonalityProfile,
        *,
        reason: str,
    ) -> bool:
        path = self.memory_dir / "personality.md"
        metadata, body = self._personality_document(profile, reason=reason)

        with self._write_lock():
            self._capture_external_changes()
            try:
                revision = self._write_markdown(
                    path,
                    metadata,
                    body,
                    create_only=True,
                )
            except MemoryAlreadyExistsError:
                return False
            self._verify_revision(path, revision)
            self._capture_ada_write(
                (self._history_path(path),),
                reason=reason,
            )
        return True

    def update_personality(
        self,
        profile: PersonalityProfile,
        *,
        reason: str,
        expected_revision: str,
    ) -> PersonalitySnapshot:
        path = self.memory_dir / "personality.md"
        metadata, body = self._personality_document(profile, reason=reason)

        with self._write_lock():
            self._capture_external_changes()
            current = self.load_personality_snapshot()
            if current is None:
                raise FileMemoryError("personality Memory does not exist")
            self._require_expected_revision(
                current.revision,
                expected_revision,
                path,
            )
            revision = self._write_markdown(
                path,
                metadata,
                body,
                expected_revision=expected_revision,
            )
            self._verify_revision(path, revision)
            self._capture_ada_write(
                (self._history_path(path),),
                reason=reason,
            )

        return PersonalitySnapshot(profile=profile, revision=revision)

    def remember_explicit(
        self,
        *,
        kind: MemoryKind,
        content: str,
    ) -> MemoryEntry:
        """Create new trusted application-confirmed explicit Memory."""

        entry = MemoryEntry(
            entry_id="",
            kind=kind,
            evidence_origin=EvidenceOrigin.EXPLICIT_STATEMENT,
            lifecycle=MemoryLifecycle.CONFIRMED,
            content=self._validate_content(content),
            confirmation_basis=ConfirmationBasis.EXPLICIT_USER,
        )

        with self._write_lock():
            self._capture_external_changes()
            entry = MemoryEntry(
                entry_id=self._new_entry_id(),
                kind=entry.kind,
                evidence_origin=entry.evidence_origin,
                lifecycle=entry.lifecycle,
                content=entry.content,
                confirmation_basis=entry.confirmation_basis,
            )
            path = self.memory_dir / f"{entry.entry_id}.md"
            revision = self._write_entry(path, entry, create_only=True)
            self._verify_revision(path, revision)
            self._capture_ada_write(
                (self._history_path(path),),
                reason="create explicit Memory",
            )
        return entry

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
        lifecycle = (
            MemoryLifecycle.PROVISIONAL
            if evidence_origin is EvidenceOrigin.HYPOTHESIS
            else MemoryLifecycle.OBSERVED
        )

        with self._write_lock():
            self._capture_external_changes()
            entry = MemoryEntry(
                entry_id=self._new_entry_id(),
                kind=kind,
                evidence_origin=evidence_origin,
                lifecycle=lifecycle,
                content=self._validate_content(content),
            )
            path = self.learning_dir / f"{entry.entry_id}.md"
            revision = self._write_entry(path, entry, create_only=True)
            self._verify_revision(path, revision)
            self._capture_ada_write(
                (self._history_path(path),),
                reason="record learning evidence",
            )
        return entry

    def promote_learning(
        self,
        entry_id: str,
        *,
        confirmation_basis: ConfirmationBasis,
    ) -> MemoryEntry:
        """Promote evidence through a trusted Ada application confirmation."""

        self._validate_entry_id(entry_id)
        if confirmation_basis is not ConfirmationBasis.EXPLICIT_USER:
            raise ValueError(
                "the baseline only permits explicit-user-confirmed promotion"
            )

        memory_path = self.memory_dir / f"{entry_id}.md"
        learning_path = self.learning_dir / f"{entry_id}.md"

        with self._write_lock():
            self._capture_external_changes()
            if (
                self._path_exists(learning_path)
                and self._is_forgotten_tombstone(learning_path)
            ):
                raise FileMemoryError(
                    f"learning entry {entry_id!r} is not promotable in its current state"
                )
            if self._path_exists(memory_path):
                raise FileMemoryError(
                    f"established Memory {entry_id!r} already exists; promotion will not overwrite it"
                )

            evidence_snapshot = self._load_learning_snapshot(
                entry_id,
                include_inactive=True,
            )
            if evidence_snapshot is None:
                raise FileMemoryError(
                    f"learning entry {entry_id!r} does not exist"
                )
            evidence = evidence_snapshot.entry
            if evidence.supports_memory_id is not None:
                raise FileMemoryError(
                    f"learning entry {entry_id!r} already supports established Memory"
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
            retained_evidence = MemoryEntry(
                entry_id=evidence.entry_id,
                kind=evidence.kind,
                evidence_origin=evidence.evidence_origin,
                lifecycle=evidence.lifecycle,
                content=evidence.content,
                supports_memory_id=established.entry_id,
            )

            memory_revision = self._write_entry(
                memory_path,
                established,
                create_only=True,
            )
            self._verify_revision(memory_path, memory_revision)
            try:
                learning_revision = self._write_entry(
                    learning_path,
                    retained_evidence,
                    expected_revision=evidence_snapshot.revision,
                )
                self._verify_revision(learning_path, learning_revision)
            except FileMemoryError as exc:
                raise FileMemoryError(
                    "promotion established current Memory but could not update "
                    "retained learning evidence; current Memory wins and the "
                    "operation requires reconciliation"
                ) from exc

            self._capture_ada_write(
                (
                    self._history_path(memory_path),
                    self._history_path(learning_path),
                ),
                reason="promote learning evidence",
            )
        return established

    def correct_explicit(
        self,
        entry_id: str,
        *,
        content: str,
        expected_revision: str,
    ) -> MemoryEntry:
        """Correct established Memory without last-write-wins behavior."""

        self._validate_entry_id(entry_id)
        path = self.memory_dir / f"{entry_id}.md"

        with self._write_lock():
            self._capture_external_changes()
            snapshot = self.load_memory_snapshot(
                entry_id,
                include_inactive=True,
            )
            if snapshot is None:
                raise FileMemoryError(
                    f"established Memory {entry_id!r} does not exist"
                )
            self._require_expected_revision(
                snapshot.revision,
                expected_revision,
                path,
            )
            if snapshot.entry.lifecycle is not MemoryLifecycle.CONFIRMED:
                raise FileMemoryError(
                    f"Memory {entry_id!r} is not current confirmed Memory"
                )

            corrected = MemoryEntry(
                entry_id=entry_id,
                kind=snapshot.entry.kind,
                evidence_origin=EvidenceOrigin.EXPLICIT_STATEMENT,
                lifecycle=MemoryLifecycle.CONFIRMED,
                content=self._validate_content(content),
                confirmation_basis=ConfirmationBasis.EXPLICIT_USER,
            )
            revision = self._write_entry(
                path,
                corrected,
                expected_revision=expected_revision,
            )
            self._verify_revision(path, revision)
            self._capture_ada_write(
                (self._history_path(path),),
                reason="correct explicit Memory",
            )
        return corrected

    def forget(self, entry_id: str) -> ForgetResult:
        """Remove current semantic Memory while retaining an opaque tombstone."""

        self._validate_entry_id(entry_id)
        memory_path = self.memory_dir / f"{entry_id}.md"
        learning_path = self.learning_dir / f"{entry_id}.md"

        with self._write_lock():
            self._capture_external_changes()
            memory_snapshot = (
                self._read_entry(memory_path, area="memory")
                if self._path_exists(memory_path)
                else None
            )
            learning_exists = self._path_exists(learning_path)
            learning_revision: str | None = None
            learning_is_tombstone = False
            if learning_exists:
                _learning_text, learning_revision = self._read_text_file(
                    learning_path
                )
                try:
                    learning_is_tombstone = self._is_forgotten_tombstone(
                        learning_path
                    )
                except FileMemoryError:
                    # Forget is allowed to neutralize malformed non-authoritative
                    # learning evidence. Established Memory above remains strict.
                    learning_is_tombstone = False

            memory_entry = (
                memory_snapshot[0] if memory_snapshot is not None else None
            )
            memory_revision = (
                memory_snapshot[1] if memory_snapshot is not None else None
            )

            if learning_is_tombstone:
                if memory_entry is None:
                    return ForgetResult.ALREADY_FORGOTTEN
                self._unlink_durable(
                    memory_path,
                    expected_revision=memory_revision,
                )
                self._capture_ada_write(
                    (
                        self._history_path(memory_path),
                        self._history_path(learning_path),
                    ),
                    reason="complete interrupted Memory forget",
                )
                return ForgetResult.FORGOTTEN

            if memory_entry is None and not learning_exists:
                return ForgetResult.NOT_FOUND

            tombstone_revision = self._write_forget_tombstone(
                learning_path,
                entry_id,
                create_only=not learning_exists,
                expected_revision=learning_revision,
            )
            self._verify_revision(learning_path, tombstone_revision)

            if memory_entry is not None:
                self._unlink_durable(
                    memory_path,
                    expected_revision=memory_revision,
                )

            self._capture_ada_write(
                (
                    self._history_path(memory_path),
                    self._history_path(learning_path),
                ),
                reason="forget current Memory",
            )
        return ForgetResult.FORGOTTEN

    def load_memory_entry(
        self,
        entry_id: str,
        *,
        include_inactive: bool = False,
    ) -> MemoryEntry | None:
        snapshot = self.load_memory_snapshot(
            entry_id,
            include_inactive=include_inactive,
        )
        return snapshot.entry if snapshot is not None else None

    def load_memory_snapshot(
        self,
        entry_id: str,
        *,
        include_inactive: bool = False,
    ) -> MemorySnapshot | None:
        self._validate_entry_id(entry_id)

        learning_path = self.learning_dir / f"{entry_id}.md"
        if (
            self._path_exists(learning_path)
            and self._is_forgotten_tombstone(learning_path)
        ):
            return None

        path = self.memory_dir / f"{entry_id}.md"
        if not self._path_exists(path):
            return None
        entry, revision = self._read_entry(path, area="memory")
        if not include_inactive and entry.lifecycle is not MemoryLifecycle.CONFIRMED:
            return None
        return MemorySnapshot(entry=entry, revision=revision)

    def load_learning_entry(
        self,
        entry_id: str,
        *,
        include_inactive: bool = False,
    ) -> MemoryEntry | None:
        snapshot = self._load_learning_snapshot(
            entry_id,
            include_inactive=include_inactive,
        )
        return snapshot.entry if snapshot is not None else None

    def history_head(self) -> str:
        try:
            return self._history.head()
        except GitMemoryHistoryError as exc:
            raise FileMemoryError(str(exc)) from exc

    def _load_learning_snapshot(
        self,
        entry_id: str,
        *,
        include_inactive: bool,
    ) -> MemorySnapshot | None:
        self._validate_entry_id(entry_id)
        path = self.learning_dir / f"{entry_id}.md"
        if not self._path_exists(path):
            return None
        if self._is_forgotten_tombstone(path):
            return None
        entry, revision = self._read_entry(path, area="learning")
        if not include_inactive:
            if self._path_exists(self.memory_dir / f"{entry_id}.md"):
                return None
            if (
                entry.lifecycle
                in {
                    MemoryLifecycle.FORGOTTEN,
                    MemoryLifecycle.SUPERSEDED,
                    MemoryLifecycle.CONTRADICTED,
                }
                or entry.supports_memory_id is not None
            ):
                return None
        return MemorySnapshot(entry=entry, revision=revision)

    @staticmethod
    def _personality_document(
        profile: PersonalityProfile,
        *,
        reason: str,
    ) -> tuple[dict[str, Any], str]:
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
        return metadata, body

    def _new_entry_id(self) -> str:
        for _attempt in range(32):
            entry_id = f"m-{uuid4().hex}"
            if not self._entry_id_seen(entry_id):
                return entry_id
        raise FileMemoryError("could not allocate a fresh opaque Memory entry id")

    def _entry_id_seen(self, entry_id: str) -> bool:
        for directory, prefix in (
            (self.memory_dir, "memory"),
            (self.learning_dir, "learning"),
        ):
            path = directory / f"{entry_id}.md"
            if self._path_exists(path):
                return True
            try:
                if self._history.has_path_history(
                    f"{prefix}/{entry_id}.md"
                ):
                    return True
            except GitMemoryHistoryError as exc:
                raise FileMemoryError(str(exc)) from exc
        return False

    def _write_forget_tombstone(
        self,
        path: Path,
        entry_id: str,
        *,
        create_only: bool,
        expected_revision: str | None,
    ) -> str:
        self._validate_entry_id(entry_id)
        metadata: dict[str, Any] = {
            "schema_version": 1,
            "entry_id": entry_id,
            "lifecycle": MemoryLifecycle.FORGOTTEN.value,
        }
        return self._write_markdown(
            path,
            metadata,
            f"{_FORGOTTEN_BODY}\n",
            create_only=create_only,
            expected_revision=expected_revision,
        )

    def _write_entry(
        self,
        path: Path,
        entry: MemoryEntry,
        *,
        create_only: bool = False,
        expected_revision: str | None = None,
    ) -> str:
        area = self._area_for_path(path)
        self._validate_area_entry(entry, area=area)
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
        return self._write_markdown(
            path,
            metadata,
            f"{entry.content}\n",
            create_only=create_only,
            expected_revision=expected_revision,
        )

    def _read_entry(
        self,
        path: Path,
        *,
        area: str,
    ) -> tuple[MemoryEntry, str]:
        metadata, body, revision = self._read_markdown(path)
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
                        "learning evidence may only support the same logical entry id"
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
            self._validate_area_entry(entry, area=area)
        except (KeyError, TypeError, ValueError) as exc:
            raise FileMemoryError(
                f"invalid Memory entry metadata in {path}"
            ) from exc

        if entry.entry_id != path.stem:
            raise FileMemoryError(
                f"Memory entry id {entry.entry_id!r} does not match file {path.name!r}"
            )
        return entry, revision

    @staticmethod
    def _validate_area_entry(entry: MemoryEntry, *, area: str) -> None:
        if area == "memory":
            if entry.lifecycle not in {
                MemoryLifecycle.CONFIRMED,
                MemoryLifecycle.STALE,
                MemoryLifecycle.CONTRADICTED,
            }:
                raise ValueError(
                    f"lifecycle {entry.lifecycle.value!r} is invalid in established Memory"
                )
            if entry.confirmation_basis is None:
                raise ValueError(
                    "established Memory requires a confirmation basis"
                )
            if entry.supports_memory_id is not None:
                raise ValueError(
                    "established Memory cannot support another Memory id"
                )
            return

        if area != "learning":
            raise ValueError(f"unknown Memory area: {area!r}")
        if entry.lifecycle not in {
            MemoryLifecycle.OBSERVED,
            MemoryLifecycle.PROVISIONAL,
            MemoryLifecycle.CONTRADICTED,
            MemoryLifecycle.SUPERSEDED,
        }:
            raise ValueError(
                f"lifecycle {entry.lifecycle.value!r} is invalid in learning"
            )
        if entry.confirmation_basis is not None:
            raise ValueError("learning evidence cannot carry confirmation basis")

    def _is_forgotten_tombstone(self, path: Path) -> bool:
        metadata, body, _revision = self._read_markdown(path)
        lifecycle = metadata.get("lifecycle")
        if lifecycle != MemoryLifecycle.FORGOTTEN.value:
            return False

        try:
            if self._require_int(metadata, "schema_version") != 1:
                raise ValueError("unsupported Memory tombstone schema")
            entry_id = self._require_str(metadata, "entry_id")
            self._validate_entry_id(entry_id)
            if entry_id != path.stem:
                raise ValueError("tombstone id does not match file")
            if set(metadata) != {"schema_version", "entry_id", "lifecycle"}:
                raise ValueError("tombstone contains unexpected metadata")
            if body.strip() != _FORGOTTEN_BODY:
                raise ValueError("tombstone contains unexpected content")
        except (KeyError, TypeError, ValueError) as exc:
            raise FileMemoryError(
                f"invalid forgotten Memory tombstone in {path}"
            ) from exc
        return True

    def _area_for_path(self, path: Path) -> str:
        if path.parent == self.memory_dir:
            return "memory"
        if path.parent == self.learning_dir:
            return "learning"
        raise ValueError(f"path is outside Memory areas: {path}")

    def _read_markdown(
        self,
        path: Path,
    ) -> tuple[dict[str, Any], str, str]:
        text, revision = self._read_text_file(path)
        normalized = text.replace("\r\n", "\n")
        if not normalized.startswith("+++\n"):
            raise FileMemoryError(f"missing TOML front matter in {path}")
        delimiter = "\n+++\n"
        end = normalized.find(delimiter, 4)
        if end < 0:
            raise FileMemoryError(f"unterminated TOML front matter in {path}")

        metadata_text = normalized[4:end]
        body = normalized[end + len(delimiter):]
        try:
            metadata = tomllib.loads(metadata_text)
        except tomllib.TOMLDecodeError as exc:
            raise FileMemoryError(
                f"invalid TOML front matter in {path}"
            ) from exc
        return metadata, body, revision

    def _write_markdown(
        self,
        path: Path,
        metadata: dict[str, Any],
        body: str,
        *,
        create_only: bool = False,
        expected_revision: str | None = None,
    ) -> str:
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
        return self._atomic_write(
            path,
            text.encode("utf-8"),
            create_only=create_only,
            expected_revision=expected_revision,
        )

    def _atomic_write(
        self,
        path: Path,
        data: bytes,
        *,
        create_only: bool,
        expected_revision: str | None,
    ) -> str:
        self._ensure_directory(path.parent)
        directory_fd = self._open_directory_fd(path.parent)
        temp_name = f".ada-memory-tmp-{uuid4().hex}"
        temp_exists = False
        try:
            temp_fd = os.open(
                temp_name,
                os.O_WRONLY
                | os.O_CREAT
                | os.O_EXCL
                | os.O_CLOEXEC
                | os.O_NOFOLLOW,
                0o600,
                dir_fd=directory_fd,
            )
            temp_exists = True
            try:
                self._write_all(temp_fd, data)
                self._sync_file_fd(temp_fd)
            finally:
                os.close(temp_fd)

            if expected_revision is not None:
                current_revision = self._revision_in_directory(
                    directory_fd,
                    path,
                )
                if current_revision != expected_revision:
                    self._capture_external_changes()
                    raise MemoryConflictError(
                        "Memory file changed immediately before publication "
                        f"and will not be overwritten: {path}"
                    )

            if create_only:
                try:
                    os.link(
                        temp_name,
                        path.name,
                        src_dir_fd=directory_fd,
                        dst_dir_fd=directory_fd,
                        follow_symlinks=False,
                    )
                except FileExistsError as exc:
                    raise MemoryAlreadyExistsError(
                        f"Memory file already exists and will not be overwritten: {path}"
                    ) from exc
                except OSError as exc:
                    if exc.errno not in {
                        errno.EPERM,
                        errno.EOPNOTSUPP,
                        errno.ENOTSUP,
                        errno.EXDEV,
                    }:
                        raise
                    self._create_only_fallback(
                        directory_fd,
                        path,
                        data,
                    )
                os.unlink(temp_name, dir_fd=directory_fd)
                temp_exists = False
                self._sync_directory_fd(directory_fd)
            else:
                os.replace(
                    temp_name,
                    path.name,
                    src_dir_fd=directory_fd,
                    dst_dir_fd=directory_fd,
                )
                temp_exists = False
                self._sync_directory_fd(directory_fd)
        except MemoryAlreadyExistsError:
            raise
        except (OSError, UnicodeError) as exc:
            raise FileMemoryError(
                f"cannot write Memory file {path}"
            ) from exc
        finally:
            if temp_exists:
                try:
                    os.unlink(temp_name, dir_fd=directory_fd)
                except FileNotFoundError:
                    pass
            os.close(directory_fd)

        return sha256(data).hexdigest()

    def _create_only_fallback(
        self,
        directory_fd: int,
        path: Path,
        data: bytes,
    ) -> None:
        try:
            target_fd = os.open(
                path.name,
                os.O_WRONLY
                | os.O_CREAT
                | os.O_EXCL
                | os.O_CLOEXEC
                | os.O_NOFOLLOW,
                0o600,
                dir_fd=directory_fd,
            )
        except FileExistsError as exc:
            raise MemoryAlreadyExistsError(
                f"Memory file already exists and will not be overwritten: {path}"
            ) from exc

        remove_partial = True
        try:
            self._write_all(target_fd, data)
            self._sync_file_fd(target_fd)
            remove_partial = False
        finally:
            os.close(target_fd)
            if remove_partial:
                try:
                    os.unlink(path.name, dir_fd=directory_fd)
                    self._sync_directory_fd(directory_fd)
                except FileNotFoundError:
                    pass

    def _read_text_file(self, path: Path) -> tuple[str, str]:
        directory_fd = self._open_directory_fd(path.parent)
        try:
            try:
                fd = os.open(
                    path.name,
                    os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW,
                    dir_fd=directory_fd,
                )
            except FileNotFoundError as exc:
                raise FileMemoryError(
                    f"Memory file disappeared while reading: {path}"
                ) from exc
            except OSError as exc:
                if exc.errno == errno.ELOOP:
                    raise FileMemoryError(
                        f"Memory file must not be a symlink: {path}"
                    ) from exc
                raise
            try:
                mode = os.fstat(fd).st_mode
                if not stat.S_ISREG(mode):
                    raise FileMemoryError(
                        f"Memory file must be a regular file: {path}"
                    )
                with os.fdopen(fd, "rb", closefd=False) as handle:
                    raw = handle.read()
            finally:
                os.close(fd)
        except FileMemoryError:
            raise
        except OSError as exc:
            raise FileMemoryError(
                f"cannot read Memory file {path}"
            ) from exc
        finally:
            os.close(directory_fd)

        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise FileMemoryError(
                f"Memory file is not valid UTF-8: {path}"
            ) from exc
        return text, sha256(raw).hexdigest()

    def _unlink_durable(
        self,
        path: Path,
        *,
        expected_revision: str | None = None,
    ) -> None:
        directory_fd = self._open_directory_fd(path.parent)
        try:
            self._assert_regular_entry(directory_fd, path)
            if expected_revision is not None:
                current_revision = self._revision_in_directory(
                    directory_fd,
                    path,
                )
                if current_revision != expected_revision:
                    self._capture_external_changes()
                    raise MemoryConflictError(
                        "Memory file changed immediately before deletion "
                        f"and will not be removed: {path}"
                    )
            os.unlink(path.name, dir_fd=directory_fd)
            self._sync_directory_fd(directory_fd)
        except FileMemoryError:
            raise
        except OSError as exc:
            raise FileMemoryError(
                f"cannot remove Memory file {path}"
            ) from exc
        finally:
            os.close(directory_fd)

    def _revision_in_directory(
        self,
        directory_fd: int,
        path: Path,
    ) -> str:
        try:
            fd = os.open(
                path.name,
                os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW,
                dir_fd=directory_fd,
            )
        except FileNotFoundError as exc:
            raise MemoryConflictError(
                f"Memory file disappeared before publication: {path}"
            ) from exc
        except OSError as exc:
            if exc.errno == errno.ELOOP:
                raise FileMemoryError(
                    f"Memory file must not be a symlink: {path}"
                ) from exc
            raise FileMemoryError(
                f"cannot reopen Memory file for revision check: {path}"
            ) from exc

        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                raise FileMemoryError(
                    f"Memory file must be a regular file: {path}"
                )
            digest = sha256()
            while True:
                chunk = os.read(fd, 1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
            return digest.hexdigest()
        finally:
            os.close(fd)

    def _path_exists(self, path: Path) -> bool:
        directory_fd = self._open_directory_fd(path.parent)
        try:
            try:
                info = os.stat(
                    path.name,
                    dir_fd=directory_fd,
                    follow_symlinks=False,
                )
            except FileNotFoundError:
                return False
            if stat.S_ISLNK(info.st_mode):
                raise FileMemoryError(
                    f"Memory file must not be a symlink: {path}"
                )
            if not stat.S_ISREG(info.st_mode):
                raise FileMemoryError(
                    f"Memory file must be a regular file: {path}"
                )
            return True
        finally:
            os.close(directory_fd)

    @staticmethod
    def _assert_regular_entry(directory_fd: int, path: Path) -> None:
        try:
            info = os.stat(
                path.name,
                dir_fd=directory_fd,
                follow_symlinks=False,
            )
        except FileNotFoundError as exc:
            raise FileMemoryError(
                f"Memory file does not exist: {path}"
            ) from exc
        if stat.S_ISLNK(info.st_mode):
            raise FileMemoryError(
                f"Memory file must not be a symlink: {path}"
            )
        if not stat.S_ISREG(info.st_mode):
            raise FileMemoryError(
                f"Memory file must be a regular file: {path}"
            )

    @contextmanager
    def _write_lock(self) -> Iterator[None]:
        root_fd = self._open_directory_fd(self.root)
        try:
            try:
                lock_fd = os.open(
                    ".ada-memory.lock",
                    os.O_RDWR
                    | os.O_CREAT
                    | os.O_CLOEXEC
                    | os.O_NOFOLLOW,
                    0o600,
                    dir_fd=root_fd,
                )
            except OSError as exc:
                raise FileMemoryError(
                    "cannot open Ada Memory write lock"
                ) from exc
            try:
                if not stat.S_ISREG(os.fstat(lock_fd).st_mode):
                    raise FileMemoryError(
                        "Ada Memory write lock is not a regular file"
                    )
                fcntl.flock(lock_fd, fcntl.LOCK_EX)
                yield
            finally:
                try:
                    fcntl.flock(lock_fd, fcntl.LOCK_UN)
                finally:
                    os.close(lock_fd)
        finally:
            os.close(root_fd)

    def _cleanup_stale_temp_files(self) -> None:
        for directory in (self.memory_dir, self.learning_dir):
            try:
                children = tuple(directory.iterdir())
            except OSError as exc:
                raise FileMemoryError(
                    f"cannot scan Memory directory for stale temp files: {directory}"
                ) from exc
            for child in children:
                if _STALE_TEMP.fullmatch(child.name):
                    self._unlink_durable(child)

    def _capture_external_changes(
        self,
        *,
        message: str = "Capture external Memory edit",
    ) -> None:
        try:
            self._history.capture_external_changes(message=message)
        except GitMemoryHistoryError as exc:
            raise FileMemoryError(str(exc)) from exc

    def _capture_ada_write(
        self,
        paths: tuple[str, ...],
        *,
        reason: str,
    ) -> None:
        try:
            self._history.capture_ada_write(paths, reason=reason)
        except GitMemoryHistoryError as exc:
            raise MemoryHistoryCommitError(
                "current Memory state changed but Git history capture failed; "
                "do not blindly retry the write, reconcile the current files first: "
                f"{exc}",
                paths=paths,
            ) from exc

    @staticmethod
    def _history_call(operation: Any) -> Any:
        try:
            return operation()
        except GitMemoryHistoryError as exc:
            raise FileMemoryError(str(exc)) from exc

    def _verify_revision(self, path: Path, expected_revision: str) -> None:
        _text, current_revision = self._read_text_file(path)
        if current_revision != expected_revision:
            self._capture_external_changes()
            raise MemoryConflictError(
                f"Memory file changed concurrently and Ada will not overwrite it: {path}"
            )

    @staticmethod
    def _require_expected_revision(
        current_revision: str,
        expected_revision: str,
        path: Path,
    ) -> None:
        if not expected_revision or current_revision != expected_revision:
            raise MemoryConflictError(
                f"Memory file changed since it was read and will not be overwritten: {path}"
            )

    def _history_path(self, path: Path) -> str:
        try:
            return path.relative_to(self.root).as_posix()
        except ValueError as exc:
            raise FileMemoryError(
                f"Memory path escaped configured root: {path}"
            ) from exc

    @staticmethod
    def _open_directory_fd(path: Path) -> int:
        try:
            fd = os.open(
                path,
                os.O_RDONLY
                | os.O_CLOEXEC
                | os.O_DIRECTORY
                | os.O_NOFOLLOW,
            )
        except OSError as exc:
            raise FileMemoryError(
                f"cannot open Memory directory safely: {path}"
            ) from exc
        if not stat.S_ISDIR(os.fstat(fd).st_mode):
            os.close(fd)
            raise FileMemoryError(
                f"Memory path is not a directory: {path}"
            )
        return fd

    @staticmethod
    def _write_all(fd: int, data: bytes) -> None:
        view = memoryview(data)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise OSError("short write while persisting Memory")
            view = view[written:]

    @staticmethod
    def _sync_file_fd(fd: int) -> None:
        os.fsync(fd)
        if sys.platform == "darwin" and hasattr(fcntl, "F_FULLFSYNC"):
            fcntl.fcntl(fd, fcntl.F_FULLFSYNC)

    @staticmethod
    def _sync_directory_fd(fd: int) -> None:
        os.fsync(fd)

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
            raise TypeError(
                f"{key} must be a non-empty array of non-empty strings"
            )
        return tuple(item.strip() for item in value)

    @staticmethod
    def _validate_entry_id(entry_id: str) -> None:
        if _ENTRY_ID.fullmatch(entry_id) is None:
            raise ValueError(
                "Memory entry id must be an opaque m-<uuid4-hex> identifier"
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
