from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from ada.adapters.file_memory import FileMemoryStore
from ada.bootstrap.personality import bootstrap_personality_memory
from ada.core.memory import (
    ConfirmationBasis,
    EvidenceOrigin,
    MemoryKind,
    MemoryLifecycle,
)


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

    def test_explicit_preference_is_established_memory(self) -> None:
        with TemporaryDirectory() as temp:
            store = FileMemoryStore(temp)

            stored = store.remember_explicit(
                entry_id="reply-style",
                kind=MemoryKind.PREFERENCE,
                content="Prefer concise answers.",
            )

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
                (Path(temp) / "memory" / "reply-style.md").exists()
            )
            self.assertFalse(
                (Path(temp) / "learning" / "reply-style.md").exists()
            )

            path = Path(temp) / "memory" / "reply-style.md"
            path.write_text(
                path.read_text(encoding="utf-8").replace(
                    "Prefer concise answers.",
                    "Prefer detailed answers.",
                ),
                encoding="utf-8",
            )
            edited = store.load_memory_entry("reply-style")
            self.assertIsNotNone(edited)
            assert edited is not None
            self.assertEqual(edited.content, "Prefer detailed answers.")

    def test_observation_stays_in_learning_until_explicit_promotion(self) -> None:
        with TemporaryDirectory() as temp:
            store = FileMemoryStore(temp)

            observed = store.record_learning(
                entry_id="detail-pattern",
                kind=MemoryKind.PREFERENCE,
                evidence_origin=EvidenceOrigin.BEHAVIORAL_OBSERVATION,
                content="The user repeatedly asks for implementation details.",
            )

            self.assertEqual(observed.lifecycle, MemoryLifecycle.OBSERVED)
            self.assertIsNone(store.load_memory_entry("detail-pattern"))

            with self.assertRaisesRegex(
                ValueError,
                "explicit-user-confirmed",
            ):
                store.promote_learning(
                    "detail-pattern",
                    confirmation_basis=ConfirmationBasis.OBSERVED_PATTERN,
                )

            promoted = store.promote_learning(
                "detail-pattern",
                confirmation_basis=ConfirmationBasis.EXPLICIT_USER,
            )

            self.assertEqual(promoted.lifecycle, MemoryLifecycle.CONFIRMED)
            self.assertEqual(
                promoted.confirmation_basis,
                ConfirmationBasis.EXPLICIT_USER,
            )
            retained = store.load_learning_entry(
                "detail-pattern",
                include_inactive=True,
            )
            self.assertIsNotNone(retained)
            assert retained is not None
            self.assertEqual(
                retained.supports_memory_id,
                "detail-pattern",
            )

    def test_observed_fact_stays_in_learning(self) -> None:
        with TemporaryDirectory() as temp:
            store = FileMemoryStore(temp)

            observed = store.record_learning(
                entry_id="practice-address",
                kind=MemoryKind.FACT,
                evidence_origin=EvidenceOrigin.OBSERVED_FACT,
                content="A synthetic practice address was seen in a test source.",
            )

            self.assertEqual(observed.lifecycle, MemoryLifecycle.OBSERVED)
            self.assertIsNone(store.load_memory_entry("practice-address"))
            self.assertTrue(
                (Path(temp) / "learning" / "practice-address.md").exists()
            )

    def test_hypothesis_is_provisional(self) -> None:
        with TemporaryDirectory() as temp:
            store = FileMemoryStore(temp)

            hypothesis = store.record_learning(
                entry_id="possible-routine",
                kind=MemoryKind.ROUTINE,
                evidence_origin=EvidenceOrigin.HYPOTHESIS,
                content="School pickup may usually happen around 15:00.",
            )

            self.assertEqual(
                hypothesis.lifecycle,
                MemoryLifecycle.PROVISIONAL,
            )

    def test_forget_removes_memory_and_neutralizes_learning_evidence(self) -> None:
        with TemporaryDirectory() as temp:
            store = FileMemoryStore(temp)
            store.record_learning(
                entry_id="detail-pattern",
                kind=MemoryKind.PREFERENCE,
                evidence_origin=EvidenceOrigin.BEHAVIORAL_OBSERVATION,
                content="The user repeatedly asks for implementation details.",
            )
            store.promote_learning(
                "detail-pattern",
                confirmation_basis=ConfirmationBasis.EXPLICIT_USER,
            )

            self.assertTrue(store.forget("detail-pattern"))

            self.assertIsNone(store.load_memory_entry("detail-pattern"))
            self.assertFalse(
                (Path(temp) / "memory" / "detail-pattern.md").exists()
            )
            self.assertIsNone(store.load_learning_entry("detail-pattern"))

            inactive = store.load_learning_entry(
                "detail-pattern",
                include_inactive=True,
            )
            self.assertIsNotNone(inactive)
            assert inactive is not None
            self.assertEqual(
                inactive.lifecycle,
                MemoryLifecycle.FORGOTTEN,
            )

    def test_existing_entries_are_never_silently_overwritten(self) -> None:
        with TemporaryDirectory() as temp:
            store = FileMemoryStore(temp)
            store.remember_explicit(
                entry_id="reply-style",
                kind=MemoryKind.PREFERENCE,
                content="Prefer concise answers.",
            )
            path = Path(temp) / "memory" / "reply-style.md"
            path.write_text(
                path.read_text(encoding="utf-8").replace(
                    "Prefer concise answers.",
                    "Manual correction wins.",
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(RuntimeError, "will not be overwritten"):
                store.remember_explicit(
                    entry_id="reply-style",
                    kind=MemoryKind.PREFERENCE,
                    content="Second write.",
                )

            current = store.load_memory_entry("reply-style")
            self.assertIsNotNone(current)
            assert current is not None
            self.assertEqual(current.content, "Manual correction wins.")

    def test_promotion_never_clobbers_existing_memory_or_reuses_evidence(self) -> None:
        with TemporaryDirectory() as temp:
            store = FileMemoryStore(temp)
            store.record_learning(
                entry_id="detail-pattern",
                kind=MemoryKind.PREFERENCE,
                evidence_origin=EvidenceOrigin.BEHAVIORAL_OBSERVATION,
                content="Observed wording.",
            )
            store.promote_learning(
                "detail-pattern",
                confirmation_basis=ConfirmationBasis.EXPLICIT_USER,
            )

            memory_path = Path(temp) / "memory" / "detail-pattern.md"
            memory_path.write_text(
                memory_path.read_text(encoding="utf-8").replace(
                    "Observed wording.",
                    "Manual correction.",
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(RuntimeError, "already exists"):
                store.promote_learning(
                    "detail-pattern",
                    confirmation_basis=ConfirmationBasis.EXPLICIT_USER,
                )

            current = store.load_memory_entry("detail-pattern")
            self.assertIsNotNone(current)
            assert current is not None
            self.assertEqual(current.content, "Manual correction.")

            retained = store.load_learning_entry(
                "detail-pattern",
                include_inactive=True,
            )
            self.assertIsNotNone(retained)
            assert retained is not None
            self.assertEqual(retained.lifecycle, MemoryLifecycle.OBSERVED)
            self.assertEqual(retained.supports_memory_id, "detail-pattern")
            self.assertIsNone(store.load_learning_entry("detail-pattern"))

    def test_personality_name_is_reserved_from_generic_entry_api(self) -> None:
        with TemporaryDirectory() as temp:
            store = FileMemoryStore(temp)
            bootstrap_personality_memory(store)

            for operation in (
                lambda: store.remember_explicit(
                    entry_id="personality",
                    kind=MemoryKind.FACT,
                    content="unsafe",
                ),
                lambda: store.load_memory_entry("personality"),
                lambda: store.forget("personality"),
            ):
                with self.subTest(operation=operation):
                    with self.assertRaisesRegex(ValueError, "reserved"):
                        operation()

            self.assertIsNotNone(store.load_personality())

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
                    path.write_text(original.replace(old, new), encoding="utf-8")
                    with self.assertRaisesRegex(
                        RuntimeError,
                        "invalid personality Memory metadata",
                    ):
                        store.load_personality()

    def test_forget_creates_content_free_tombstone_and_blocks_repromotion(self) -> None:
        with TemporaryDirectory() as temp:
            store = FileMemoryStore(temp)
            original_text = "Sensitive synthetic observation."
            store.record_learning(
                entry_id="sensitive-note",
                kind=MemoryKind.FACT,
                evidence_origin=EvidenceOrigin.OBSERVED_FACT,
                content=original_text,
            )
            store.promote_learning(
                "sensitive-note",
                confirmation_basis=ConfirmationBasis.EXPLICIT_USER,
            )

            self.assertTrue(store.forget("sensitive-note"))

            tombstone_path = Path(temp) / "learning" / "sensitive-note.md"
            tombstone_text = tombstone_path.read_text(encoding="utf-8")
            self.assertNotIn(original_text, tombstone_text)
            self.assertIn("[forgotten]", tombstone_text)
            self.assertIsNone(store.load_learning_entry("sensitive-note"))

            with self.assertRaisesRegex(RuntimeError, "not promotable"):
                store.promote_learning(
                    "sensitive-note",
                    confirmation_basis=ConfirmationBasis.EXPLICIT_USER,
                )

    def test_malformed_learning_evidence_does_not_block_forget(self) -> None:
        with TemporaryDirectory() as temp:
            store = FileMemoryStore(temp)
            store.record_learning(
                entry_id="detail-pattern",
                kind=MemoryKind.PREFERENCE,
                evidence_origin=EvidenceOrigin.BEHAVIORAL_OBSERVATION,
                content="Observed wording.",
            )
            store.promote_learning(
                "detail-pattern",
                confirmation_basis=ConfirmationBasis.EXPLICIT_USER,
            )
            learning_path = Path(temp) / "learning" / "detail-pattern.md"
            learning_path.write_text("not front matter", encoding="utf-8")

            self.assertTrue(store.forget("detail-pattern"))
            self.assertIsNone(store.load_memory_entry("detail-pattern"))
            tombstone = learning_path.read_text(encoding="utf-8")
            self.assertIn('lifecycle = "forgotten"', tombstone)
            self.assertNotIn("Observed wording.", tombstone)

    def test_symlinked_memory_paths_are_rejected(self) -> None:
        with TemporaryDirectory() as temp, TemporaryDirectory() as outside:
            root = Path(temp)
            store = FileMemoryStore(root)
            target = Path(outside) / "outside.md"
            target.write_text("outside", encoding="utf-8")
            link = root / "memory" / "linked.md"
            link.symlink_to(target)

            with self.assertRaisesRegex(RuntimeError, "symlink"):
                store.load_memory_entry("linked")

        with TemporaryDirectory() as temp, TemporaryDirectory() as outside:
            root = Path(temp)
            memory_dir = root / "memory"
            memory_dir.symlink_to(Path(outside), target_is_directory=True)

            with self.assertRaisesRegex(RuntimeError, "symlink"):
                FileMemoryStore(root)

    def test_entry_header_identity_and_malformed_entries_fail_closed(self) -> None:
        with TemporaryDirectory() as temp:
            store = FileMemoryStore(temp)
            store.remember_explicit(
                entry_id="reply-style",
                kind=MemoryKind.PREFERENCE,
                content="Prefer concise answers.",
            )
            path = Path(temp) / "memory" / "reply-style.md"
            original = path.read_text(encoding="utf-8")

            path.write_text(
                original.replace(
                    'entry_id = "reply-style"',
                    'entry_id = "other-id"',
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "does not match file"):
                store.load_memory_entry("reply-style")

            path.write_text(
                original.replace(
                    'kind = "preference"',
                    'kind = "not-a-kind"',
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "invalid Memory entry metadata"):
                store.load_memory_entry("reply-style")

            path.write_text("not TOML front matter", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "missing TOML front matter"):
                store.load_memory_entry("reply-style")

    def test_reserved_and_blank_roots_fail_closed(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "must not be blank"):
            FileMemoryStore("")

    def test_current_file_state_does_not_rehydrate_from_history_like_data(self) -> None:
        with TemporaryDirectory() as temp:
            store = FileMemoryStore(temp)
            store.remember_explicit(
                entry_id="reply-style",
                kind=MemoryKind.PREFERENCE,
                content="Prefer concise answers.",
            )
            current = Path(temp) / "memory" / "reply-style.md"
            old_content = current.read_text(encoding="utf-8")
            current.unlink()

            history = Path(temp) / ".git" / "synthetic-history"
            history.parent.mkdir(parents=True)
            history.write_text(old_content, encoding="utf-8")

            self.assertIsNone(store.load_memory_entry("reply-style"))

    def test_entry_ids_cannot_escape_the_configured_root(self) -> None:
        with TemporaryDirectory() as temp:
            store = FileMemoryStore(temp)

            with self.assertRaises(ValueError):
                store.remember_explicit(
                    entry_id="../outside",
                    kind=MemoryKind.FACT,
                    content="unsafe",
                )


if __name__ == "__main__":
    unittest.main()
