from __future__ import annotations

from dataclasses import replace
import errno
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from uuid import UUID

from ada.adapters.file_memory import (
    FileMemoryError,
    FileMemoryStore,
    MemoryConflictError,
    MemoryHistoryCommitError,
)
from ada.adapters.git_memory_history import GitMemoryHistoryError
from ada.bootstrap.personality import (
    bootstrap_personality_memory,
    load_bootstrap_personality,
)
from ada.core.memory import (
    ConfirmationBasis,
    EvidenceOrigin,
    ForgetResult,
    MemoryKind,
    MemoryLifecycle,
)


_ID = re.compile(r"m-[0-9a-f]{32}")


def _git(root: str | Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
        env={
            "PATH": __import__("os").environ.get("PATH", ""),
            "HOME": __import__("os").environ.get("HOME", ""),
            "GIT_CONFIG_GLOBAL": __import__("os").devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
        },
    )
    return result.stdout.strip()


class FileMemoryTests(unittest.TestCase):
    def test_empty_personality_seeds_once_and_manual_edit_wins(self) -> None:
        with TemporaryDirectory() as temp:
            store = FileMemoryStore(temp)

            first = bootstrap_personality_memory(store)
            personality_path = Path(temp) / "memory" / "personality.md"
            initial_text = personality_path.read_text(encoding="utf-8")

            self.assertEqual(first.display_name, "Ada")
            self.assertIn('display_name = "Ada"', initial_text)

            edited = initial_text.replace(
                'display_name = "Ada"',
                'display_name = "Mira"',
            )
            personality_path.write_text(edited, encoding="utf-8")

            second = bootstrap_personality_memory(store)

            self.assertEqual(second.display_name, "Mira")
            self.assertEqual(
                personality_path.read_text(encoding="utf-8"),
                edited,
            )

    def test_personality_initialization_is_create_only(self) -> None:
        with TemporaryDirectory() as temp:
            store = FileMemoryStore(temp)
            seed = load_bootstrap_personality()
            winner = replace(seed, display_name="Human winner")
            loser = replace(seed, display_name="Ada loser")

            self.assertTrue(
                store.create_personality_if_absent(
                    winner,
                    reason="synthetic concurrent winner",
                )
            )
            self.assertFalse(
                store.create_personality_if_absent(
                    loser,
                    reason="synthetic losing bootstrap",
                )
            )

            current = store.load_personality()
            self.assertIsNotNone(current)
            assert current is not None
            self.assertEqual(current.display_name, "Human winner")

    def test_malformed_manual_personality_edit_fails_closed(self) -> None:
        with TemporaryDirectory() as temp:
            store = FileMemoryStore(temp)
            bootstrap_personality_memory(store)
            path = Path(temp) / "memory" / "personality.md"
            lines = path.read_text(encoding="utf-8").splitlines()
            text = "\n".join(
                'traits = "broken"' if line.startswith("traits = [") else line
                for line in lines
            )
            path.write_text(text + "\n", encoding="utf-8")

            with self.assertRaisesRegex(
                RuntimeError,
                "invalid personality Memory metadata",
            ):
                store.load_personality()

    def test_generic_memory_ids_are_opaque_and_generated_by_ada(self) -> None:
        with TemporaryDirectory() as temp:
            store = FileMemoryStore(temp)

            stored = store.remember_explicit(
                kind=MemoryKind.PREFERENCE,
                content="Prefer concise answers.",
            )

            self.assertRegex(stored.entry_id, _ID)
            self.assertNotIn("concise", stored.entry_id)
            self.assertEqual(
                stored.evidence_origin,
                EvidenceOrigin.EXPLICIT_STATEMENT,
            )
            self.assertEqual(stored.lifecycle, MemoryLifecycle.CONFIRMED)
            self.assertEqual(
                stored.confirmation_basis,
                ConfirmationBasis.EXPLICIT_USER,
            )
            self.assertTrue(
                (Path(temp) / "memory" / f"{stored.entry_id}.md").exists()
            )

    def test_observation_stays_in_learning_until_explicit_promotion(self) -> None:
        with TemporaryDirectory() as temp:
            store = FileMemoryStore(temp)

            observed = store.record_learning(
                kind=MemoryKind.PREFERENCE,
                evidence_origin=EvidenceOrigin.BEHAVIORAL_OBSERVATION,
                content="The user repeatedly asks for implementation details.",
            )

            self.assertEqual(observed.lifecycle, MemoryLifecycle.OBSERVED)
            self.assertIsNone(store.load_memory_entry(observed.entry_id))

            with self.assertRaisesRegex(
                ValueError,
                "explicit-user-confirmed",
            ):
                store.promote_learning(
                    observed.entry_id,
                    confirmation_basis=ConfirmationBasis.OBSERVED_PATTERN,
                )

            promoted = store.promote_learning(
                observed.entry_id,
                confirmation_basis=ConfirmationBasis.EXPLICIT_USER,
            )

            self.assertEqual(promoted.entry_id, observed.entry_id)
            self.assertEqual(promoted.lifecycle, MemoryLifecycle.CONFIRMED)
            retained = store.load_learning_entry(
                observed.entry_id,
                include_inactive=True,
            )
            self.assertIsNotNone(retained)
            assert retained is not None
            self.assertEqual(
                retained.supports_memory_id,
                observed.entry_id,
            )
            self.assertIsNone(store.load_learning_entry(observed.entry_id))

    def test_hypothesis_is_provisional(self) -> None:
        with TemporaryDirectory() as temp:
            store = FileMemoryStore(temp)
            hypothesis = store.record_learning(
                kind=MemoryKind.ROUTINE,
                evidence_origin=EvidenceOrigin.HYPOTHESIS,
                content="School pickup may usually happen around 15:00.",
            )
            self.assertEqual(
                hypothesis.lifecycle,
                MemoryLifecycle.PROVISIONAL,
            )

    def test_stale_correction_cannot_overwrite_manual_edit(self) -> None:
        with TemporaryDirectory() as temp:
            store = FileMemoryStore(temp)
            original = store.remember_explicit(
                kind=MemoryKind.PREFERENCE,
                content="Prefer concise answers.",
            )
            snapshot = store.load_memory_snapshot(original.entry_id)
            self.assertIsNotNone(snapshot)
            assert snapshot is not None

            path = Path(temp) / "memory" / f"{original.entry_id}.md"
            path.write_text(
                path.read_text(encoding="utf-8").replace(
                    "Prefer concise answers.",
                    "Manual correction wins.",
                ),
                encoding="utf-8",
            )

            with self.assertRaises(MemoryConflictError):
                store.correct_explicit(
                    original.entry_id,
                    content="Stale Ada correction.",
                    expected_revision=snapshot.revision,
                )

            current = store.load_memory_entry(original.entry_id)
            self.assertIsNotNone(current)
            assert current is not None
            self.assertEqual(current.content, "Manual correction wins.")

            log = _git(
                temp,
                "log",
                "--format=%s",
                "--",
                f"memory/{original.entry_id}.md",
            )
            self.assertIn("Capture external Memory edit", log)

    def test_late_manual_edit_is_detected_at_publication(self) -> None:
        with TemporaryDirectory() as temp:
            store = FileMemoryStore(temp)
            original = store.remember_explicit(
                kind=MemoryKind.PREFERENCE,
                content="Before late edit.",
            )
            snapshot = store.load_memory_snapshot(original.entry_id)
            self.assertIsNotNone(snapshot)
            assert snapshot is not None
            path = Path(temp) / "memory" / f"{original.entry_id}.md"
            original_write_entry = store._write_entry
            injected = False

            def write_with_late_human_edit(*args, **kwargs):
                nonlocal injected
                if not injected:
                    injected = True
                    path.write_text(
                        path.read_text(encoding="utf-8").replace(
                            "Before late edit.",
                            "Late human edit wins.",
                        ),
                        encoding="utf-8",
                    )
                return original_write_entry(*args, **kwargs)

            with patch.object(
                store,
                "_write_entry",
                side_effect=write_with_late_human_edit,
            ):
                with self.assertRaises(MemoryConflictError):
                    store.correct_explicit(
                        original.entry_id,
                        content="Ada must not overwrite.",
                        expected_revision=snapshot.revision,
                    )

            current = store.load_memory_entry(original.entry_id)
            self.assertIsNotNone(current)
            assert current is not None
            self.assertEqual(current.content, "Late human edit wins.")
            log = _git(
                temp,
                "log",
                "--format=%s",
                "--",
                f"memory/{original.entry_id}.md",
            )
            self.assertEqual(
                log.splitlines()[0],
                "Capture external Memory edit",
            )

    def test_explicit_correction_keeps_identity_and_records_history(self) -> None:
        with TemporaryDirectory() as temp:
            store = FileMemoryStore(temp)
            original = store.remember_explicit(
                kind=MemoryKind.PREFERENCE,
                content="Prefer concise answers.",
            )
            snapshot = store.load_memory_snapshot(original.entry_id)
            self.assertIsNotNone(snapshot)
            assert snapshot is not None

            corrected = store.correct_explicit(
                original.entry_id,
                content="Prefer detailed answers.",
                expected_revision=snapshot.revision,
            )

            self.assertEqual(corrected.entry_id, original.entry_id)
            self.assertEqual(corrected.content, "Prefer detailed answers.")
            log = _git(
                temp,
                "log",
                "--format=%s",
                "--",
                f"memory/{original.entry_id}.md",
            )
            self.assertIn("Ada Memory: correct explicit Memory", log)
            self.assertIn("Ada Memory: create explicit Memory", log)

    def test_forget_is_idempotent_and_never_rehydrates_from_history(self) -> None:
        with TemporaryDirectory() as temp:
            store = FileMemoryStore(temp)
            original_text = "Sensitive synthetic observation."
            observed = store.record_learning(
                kind=MemoryKind.FACT,
                evidence_origin=EvidenceOrigin.OBSERVED_FACT,
                content=original_text,
            )
            store.promote_learning(
                observed.entry_id,
                confirmation_basis=ConfirmationBasis.EXPLICIT_USER,
            )

            self.assertEqual(
                store.forget(observed.entry_id),
                ForgetResult.FORGOTTEN,
            )
            self.assertEqual(
                store.forget(observed.entry_id),
                ForgetResult.ALREADY_FORGOTTEN,
            )
            self.assertIsNone(store.load_memory_entry(observed.entry_id))
            self.assertIsNone(store.load_learning_entry(observed.entry_id))

            tombstone_path = (
                Path(temp) / "learning" / f"{observed.entry_id}.md"
            )
            tombstone = tombstone_path.read_text(encoding="utf-8")
            self.assertNotIn(original_text, tombstone)
            self.assertNotIn("kind =", tombstone)
            self.assertNotIn("evidence_origin =", tombstone)
            self.assertIn('lifecycle = "forgotten"', tombstone)
            self.assertIn("[forgotten]", tombstone)

            history = _git(
                temp,
                "log",
                "--format=%H",
                "--all",
                "--",
                f"memory/{observed.entry_id}.md",
            )
            self.assertTrue(history)
            self.assertIsNone(store.load_memory_entry(observed.entry_id))

            with self.assertRaisesRegex(RuntimeError, "not promotable"):
                store.promote_learning(
                    observed.entry_id,
                    confirmation_basis=ConfirmationBasis.EXPLICIT_USER,
                )

    def test_forgotten_id_is_never_reused(self) -> None:
        old_uuid = UUID("11111111-1111-4111-8111-111111111111")
        new_uuid = UUID("22222222-2222-4222-8222-222222222222")
        temp_uuid = UUID("33333333-3333-4333-8333-333333333333")

        with TemporaryDirectory() as temp:
            store = FileMemoryStore(temp)
            with patch(
                "ada.adapters.file_memory.uuid4",
                return_value=old_uuid,
            ):
                first = store.remember_explicit(
                    kind=MemoryKind.FACT,
                    content="First synthetic fact.",
                )
            self.assertEqual(
                store.forget(first.entry_id),
                ForgetResult.FORGOTTEN,
            )

            with patch(
                "ada.adapters.file_memory.uuid4",
                side_effect=[old_uuid, new_uuid, temp_uuid],
            ):
                second = store.remember_explicit(
                    kind=MemoryKind.FACT,
                    content="Second synthetic fact.",
                )

            self.assertNotEqual(second.entry_id, first.entry_id)
            self.assertEqual(second.entry_id, f"m-{new_uuid.hex}")

    def test_forget_preserves_malformed_established_memory(self) -> None:
        with TemporaryDirectory() as temp:
            store = FileMemoryStore(temp)
            entry = store.remember_explicit(
                kind=MemoryKind.FACT,
                content="Do not silently erase this.",
            )
            path = Path(temp) / "memory" / f"{entry.entry_id}.md"
            malformed = "not TOML front matter\n"
            path.write_text(malformed, encoding="utf-8")

            with self.assertRaisesRegex(
                FileMemoryError,
                "missing TOML front matter",
            ):
                store.forget(entry.entry_id)

            self.assertEqual(path.read_text(encoding="utf-8"), malformed)
            self.assertFalse(
                (Path(temp) / "learning" / f"{entry.entry_id}.md").exists()
            )

    def test_forget_neutralizes_malformed_learning_evidence(self) -> None:
        with TemporaryDirectory() as temp:
            store = FileMemoryStore(temp)
            observed = store.record_learning(
                kind=MemoryKind.PREFERENCE,
                evidence_origin=EvidenceOrigin.BEHAVIORAL_OBSERVATION,
                content="Observed wording.",
            )
            learning = Path(temp) / "learning" / f"{observed.entry_id}.md"
            learning.write_text("not front matter\n", encoding="utf-8")

            self.assertEqual(
                store.forget(observed.entry_id),
                ForgetResult.FORGOTTEN,
            )

            tombstone = learning.read_text(encoding="utf-8")
            self.assertNotIn("Observed wording.", tombstone)
            self.assertNotIn("kind =", tombstone)
            self.assertNotIn("evidence_origin =", tombstone)
            self.assertIn('lifecycle = "forgotten"', tombstone)
            self.assertEqual(
                store.forget(observed.entry_id),
                ForgetResult.ALREADY_FORGOTTEN,
            )

    def test_area_lifecycle_invariants_fail_closed(self) -> None:
        with TemporaryDirectory() as temp:
            store = FileMemoryStore(temp)
            entry = store.remember_explicit(
                kind=MemoryKind.FACT,
                content="Current fact.",
            )
            path = Path(temp) / "memory" / f"{entry.entry_id}.md"
            text = path.read_text(encoding="utf-8")
            path.write_text(
                text.replace(
                    'lifecycle = "confirmed"',
                    'lifecycle = "observed"',
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                FileMemoryError,
                "invalid Memory entry metadata",
            ):
                store.load_memory_entry(entry.entry_id)

    def test_promotion_never_clobbers_existing_memory_or_reuses_evidence(self) -> None:
        with TemporaryDirectory() as temp:
            store = FileMemoryStore(temp)
            observed = store.record_learning(
                kind=MemoryKind.PREFERENCE,
                evidence_origin=EvidenceOrigin.BEHAVIORAL_OBSERVATION,
                content="Observed wording.",
            )
            store.promote_learning(
                observed.entry_id,
                confirmation_basis=ConfirmationBasis.EXPLICIT_USER,
            )

            path = Path(temp) / "memory" / f"{observed.entry_id}.md"
            path.write_text(
                path.read_text(encoding="utf-8").replace(
                    "Observed wording.",
                    "Manual correction.",
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(RuntimeError, "already exists"):
                store.promote_learning(
                    observed.entry_id,
                    confirmation_basis=ConfirmationBasis.EXPLICIT_USER,
                )

            current = store.load_memory_entry(observed.entry_id)
            self.assertIsNotNone(current)
            assert current is not None
            self.assertEqual(current.content, "Manual correction.")

    def test_symlinked_memory_paths_are_rejected_at_open(self) -> None:
        with TemporaryDirectory() as temp, TemporaryDirectory() as outside:
            root = Path(temp)
            store = FileMemoryStore(root)
            target = Path(outside) / "outside.md"
            target.write_text("outside", encoding="utf-8")
            link_id = "m-" + ("a" * 32)
            link = root / "memory" / f"{link_id}.md"
            link.symlink_to(target)

            with self.assertRaisesRegex(RuntimeError, "symlink"):
                store.load_memory_entry(link_id)

        with TemporaryDirectory() as temp, TemporaryDirectory() as outside:
            root = Path(temp)
            memory_dir = root / "memory"
            memory_dir.symlink_to(Path(outside), target_is_directory=True)

            with self.assertRaisesRegex(RuntimeError, "symlink"):
                FileMemoryStore(root)

    def test_create_only_falls_back_when_hard_links_are_unavailable(self) -> None:
        with TemporaryDirectory() as temp:
            store = FileMemoryStore(temp)
            with patch(
                "ada.adapters.file_memory.os.link",
                side_effect=OSError(
                    errno.EOPNOTSUPP,
                    "synthetic no-hardlink filesystem",
                ),
            ):
                entry = store.remember_explicit(
                    kind=MemoryKind.FACT,
                    content="Fallback publication works.",
                )

            current = store.load_memory_entry(entry.entry_id)
            self.assertIsNotNone(current)
            assert current is not None
            self.assertEqual(current.content, "Fallback publication works.")

    def test_non_markdown_editor_artifacts_are_not_recorded_in_history(self) -> None:
        with TemporaryDirectory() as temp:
            store = FileMemoryStore(temp)
            artifact = Path(temp) / "memory" / ".editor.swp"
            artifact.write_text(
                "synthetic editor artifact with private-looking text",
                encoding="utf-8",
            )

            store.remember_explicit(
                kind=MemoryKind.FACT,
                content="Legitimate Memory write.",
            )

            self.assertTrue(artifact.exists())
            tracked = _git(temp, "ls-files", "--", "memory/.editor.swp")
            self.assertEqual(tracked, "")
            history = _git(
                temp,
                "log",
                "--format=%H",
                "--all",
                "--",
                "memory/.editor.swp",
            )
            self.assertEqual(history, "")

    def test_stale_ada_temp_is_removed_before_history_capture(self) -> None:
        with TemporaryDirectory() as temp:
            FileMemoryStore(temp)
            stale = (
                Path(temp)
                / "memory"
                / ".ada-memory-tmp-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
            )
            stale.write_text(
                "synthetic interrupted write content",
                encoding="utf-8",
            )

            FileMemoryStore(temp)

            self.assertFalse(stale.exists())
            tracked = _git(
                temp,
                "ls-files",
                "--",
                "memory/.ada-memory-tmp-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            )
            self.assertEqual(tracked, "")

    def test_external_edit_is_captured_before_next_ada_write(self) -> None:
        with TemporaryDirectory() as temp:
            store = FileMemoryStore(temp)
            first = store.remember_explicit(
                kind=MemoryKind.FACT,
                content="Before human edit.",
            )
            first_path = Path(temp) / "memory" / f"{first.entry_id}.md"
            first_path.write_text(
                first_path.read_text(encoding="utf-8").replace(
                    "Before human edit.",
                    "After human edit.",
                ),
                encoding="utf-8",
            )

            store.remember_explicit(
                kind=MemoryKind.FACT,
                content="Second Ada write.",
            )

            log = _git(
                temp,
                "log",
                "--format=%s",
                "--",
                f"memory/{first.entry_id}.md",
            )
            subjects = log.splitlines()
            self.assertEqual(subjects[0], "Capture external Memory edit")
            self.assertIn("Ada Memory: create explicit Memory", subjects)

    def test_ada_commit_does_not_consume_unrelated_staged_content(self) -> None:
        with TemporaryDirectory() as temp:
            store = FileMemoryStore(temp)
            unrelated = Path(temp) / "unrelated.txt"
            unrelated.write_text("keep staged", encoding="utf-8")
            _git(temp, "add", "--", "unrelated.txt")

            store.remember_explicit(
                kind=MemoryKind.FACT,
                content="Path-restricted commit.",
            )

            staged = _git(temp, "diff", "--cached", "--name-only")
            self.assertEqual(staged, "unrelated.txt")

    def test_existing_foreign_git_repository_is_refused(self) -> None:
        with TemporaryDirectory() as temp:
            subprocess.run(
                ["git", "-C", temp, "init", "--quiet"],
                check=True,
                capture_output=True,
                text=True,
            )

            with self.assertRaisesRegex(
                FileMemoryError,
                "pre-existing Git repository",
            ):
                FileMemoryStore(temp)

            self.assertFalse((Path(temp) / "memory").exists())
            self.assertFalse((Path(temp) / "learning").exists())
            self.assertFalse((Path(temp) / ".ada-memory.lock").exists())

    def test_ada_owned_history_can_be_reopened(self) -> None:
        with TemporaryDirectory() as temp:
            first_store = FileMemoryStore(temp)
            entry = first_store.remember_explicit(
                kind=MemoryKind.FACT,
                content="Persist across adapter restart.",
            )

            second_store = FileMemoryStore(temp)
            current = second_store.load_memory_entry(entry.entry_id)

            self.assertIsNotNone(current)
            assert current is not None
            self.assertEqual(current.content, "Persist across adapter restart.")
            marker = Path(temp) / ".git" / "ada-memory-history-v1"
            self.assertTrue(marker.is_file())

    def test_git_lock_failure_stops_before_current_memory_write(self) -> None:
        with TemporaryDirectory() as temp:
            store = FileMemoryStore(temp)
            lock = Path(temp) / ".git" / "index.lock"
            lock.write_text("synthetic lock", encoding="utf-8")
            try:
                with self.assertRaisesRegex(
                    FileMemoryError,
                    "Git command failed",
                ):
                    store.remember_explicit(
                        kind=MemoryKind.FACT,
                        content="Must not be written.",
                    )
            finally:
                lock.unlink()

            generic_files = list((Path(temp) / "memory").glob("m-*.md"))
            self.assertEqual(generic_files, [])

    def test_history_failure_after_write_has_explicit_ambiguous_outcome(self) -> None:
        with TemporaryDirectory() as temp:
            store = FileMemoryStore(temp)
            with patch.object(
                store._history,
                "capture_ada_write",
                side_effect=GitMemoryHistoryError("synthetic history failure"),
            ):
                with self.assertRaises(MemoryHistoryCommitError) as caught:
                    store.remember_explicit(
                        kind=MemoryKind.FACT,
                        content="Current state was published.",
                    )

            self.assertTrue(caught.exception.current_state_applied)
            generic_files = list((Path(temp) / "memory").glob("m-*.md"))
            self.assertEqual(len(generic_files), 1)
            self.assertIn(
                "Current state was published.",
                generic_files[0].read_text(encoding="utf-8"),
            )

    def test_scalar_front_matter_types_fail_closed(self) -> None:
        with TemporaryDirectory() as temp:
            store = FileMemoryStore(temp)
            bootstrap_personality_memory(store)
            path = Path(temp) / "memory" / "personality.md"
            original = path.read_text(encoding="utf-8")

            for old, new in (
                ('display_name = "Ada"', 'display_name = ["Mira"]'),
                ("schema_version = 1", "schema_version = true"),
                ("schema_version = 1", "schema_version = 1.9"),
            ):
                with self.subTest(new=new):
                    path.write_text(
                        original.replace(old, new),
                        encoding="utf-8",
                    )
                    with self.assertRaisesRegex(
                        RuntimeError,
                        "invalid personality Memory metadata",
                    ):
                        store.load_personality()

    def test_entry_header_identity_and_malformed_entries_fail_closed(self) -> None:
        with TemporaryDirectory() as temp:
            store = FileMemoryStore(temp)
            entry = store.remember_explicit(
                kind=MemoryKind.PREFERENCE,
                content="Prefer concise answers.",
            )
            path = Path(temp) / "memory" / f"{entry.entry_id}.md"
            original = path.read_text(encoding="utf-8")
            other_id = "m-" + ("b" * 32)

            path.write_text(
                original.replace(
                    f'entry_id = "{entry.entry_id}"',
                    f'entry_id = "{other_id}"',
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "does not match file"):
                store.load_memory_entry(entry.entry_id)

            path.write_text(
                original.replace(
                    'kind = "preference"',
                    'kind = "not-a-kind"',
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                RuntimeError,
                "invalid Memory entry metadata",
            ):
                store.load_memory_entry(entry.entry_id)

            path.write_text("not TOML front matter", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "missing TOML front matter"):
                store.load_memory_entry(entry.entry_id)

    def test_reserved_root_and_invalid_requested_ids_fail_closed(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "must not be blank"):
            FileMemoryStore("")

        with TemporaryDirectory() as temp:
            store = FileMemoryStore(temp)
            for unsafe in (
                "../outside",
                "reply-style",
                "m-too-short",
            ):
                with self.subTest(unsafe=unsafe):
                    with self.assertRaises(ValueError):
                        store.load_memory_entry(unsafe)

    def test_forget_not_found_is_explicit(self) -> None:
        with TemporaryDirectory() as temp:
            store = FileMemoryStore(temp)
            missing = "m-" + ("c" * 32)
            self.assertEqual(
                store.forget(missing),
                ForgetResult.NOT_FOUND,
            )


if __name__ == "__main__":
    unittest.main()
