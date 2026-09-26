from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from dulwich.repo import Repo

from ada.adapters.dulwich_memory_history import MemoryHistoryError
from ada.adapters.file_memory import (
    FileMemoryConflictError,
    FileMemoryError,
    FileMemoryHistoryPendingError,
    FileMemoryRecoveryRequiredError,
    FileMemoryStore,
)
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
from ada.core.personality import PersonalityProfile


def _ids(*values: str):
    iterator = iter(values)
    return lambda: next(iterator)


class _FakeHistory:
    def __init__(self, *, fail_on_capture: int | None = None) -> None:
        self.capture_count = 0
        self.fail_on_capture = fail_on_capture
        self.snapshots: list[dict[str, bytes]] = []
        self.reasons: list[str] = []
        self.seen: set[str] = set()

    def capture_snapshot(
        self,
        snapshot: dict[str, bytes],
        *,
        reason: str,
    ) -> bool:
        self.capture_count += 1
        if self.capture_count == self.fail_on_capture:
            raise MemoryHistoryError("synthetic history failure")
        current = dict(snapshot)
        self.snapshots.append(current)
        self.reasons.append(reason)
        for path in current:
            if path.startswith(("memory/m_", "learning/m_")):
                self.seen.add(Path(path).stem)
        return True

    def has_seen_entry_id(self, entry_id: str) -> bool:
        return entry_id in self.seen


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
            first_store = FileMemoryStore(temp)
            first_store.save_personality(
                load_bootstrap_personality(),
                reason="first",
            )
            original = (Path(temp) / "memory" / "personality.md").read_text(
                encoding="utf-8"
            )

            second_store = FileMemoryStore(temp)
            second_store.save_personality(
                PersonalityProfile(
                    schema_version=1,
                    profile_id="other",
                    display_name="Other",
                    inspiration="Synthetic",
                    background_story="Synthetic",
                    traits=("quiet",),
                    interaction_style=("brief",),
                    boundaries=("test",),
                ),
                reason="must not clobber",
            )

            self.assertEqual(
                (Path(temp) / "memory" / "personality.md").read_text(
                    encoding="utf-8"
                ),
                original,
            )

    def test_malformed_manual_personality_edit_is_captured_then_fails_closed(
        self,
    ) -> None:
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
            before = self._history_count(temp)

            with self.assertRaisesRegex(
                RuntimeError,
                "invalid personality Memory metadata",
            ):
                store.load_personality()

            self.assertGreater(self._history_count(temp), before)

    def test_explicit_memory_gets_opaque_id_and_correction_keeps_identity(
        self,
    ) -> None:
        with TemporaryDirectory() as temp:
            store = FileMemoryStore(
                temp,
                id_factory=_ids("1" * 32),
            )
            stored = store.remember_explicit(
                kind=MemoryKind.PREFERENCE,
                content="Prefer concise answers.",
            )

            self.assertEqual(stored.entry_id, "m_" + "1" * 32)
            versioned = store.load_memory_entry_versioned(stored.entry_id)
            self.assertIsNotNone(versioned)
            assert versioned is not None

            corrected = store.correct_memory(
                stored.entry_id,
                content="Prefer detailed answers.",
                expected_revision=versioned.revision,
            )

            self.assertEqual(corrected.entry.entry_id, stored.entry_id)
            self.assertEqual(
                corrected.entry.evidence_origin,
                EvidenceOrigin.EXPLICIT_STATEMENT,
            )
            self.assertEqual(
                corrected.entry.confirmation_basis,
                ConfirmationBasis.EXPLICIT_USER,
            )
            self.assertEqual(
                store.load_memory_entry(stored.entry_id).content,
                "Prefer detailed answers.",
            )

    def test_stale_correction_never_overwrites_manual_edit(self) -> None:
        with TemporaryDirectory() as temp:
            store = FileMemoryStore(
                temp,
                id_factory=_ids("2" * 32),
            )
            entry = store.remember_explicit(
                kind=MemoryKind.PREFERENCE,
                content="Prefer concise answers.",
            )
            versioned = store.load_memory_entry_versioned(entry.entry_id)
            assert versioned is not None
            path = Path(temp) / "memory" / f"{entry.entry_id}.md"
            manual = path.read_text(encoding="utf-8").replace(
                "Prefer concise answers.",
                "Manual correction wins.",
            )
            path.write_text(manual, encoding="utf-8")

            with self.assertRaisesRegex(
                FileMemoryConflictError,
                "changed since it was read",
            ):
                store.correct_memory(
                    entry.entry_id,
                    content="Stale Ada correction.",
                    expected_revision=versioned.revision,
                )

            current = store.load_memory_entry(entry.entry_id)
            self.assertIsNotNone(current)
            assert current is not None
            self.assertEqual(current.content, "Manual correction wins.")

    def test_observation_stays_learning_until_explicit_promotion(self) -> None:
        with TemporaryDirectory() as temp:
            store = FileMemoryStore(
                temp,
                id_factory=_ids("3" * 32),
            )
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
            self.assertIsNone(store.load_learning_entry(observed.entry_id))
            retained = store.load_learning_entry(
                observed.entry_id,
                include_inactive=True,
            )
            self.assertIsNotNone(retained)
            assert retained is not None
            self.assertEqual(retained.content, observed.content)

    def test_hypothesis_is_provisional(self) -> None:
        with TemporaryDirectory() as temp:
            store = FileMemoryStore(
                temp,
                id_factory=_ids("4" * 32),
            )
            hypothesis = store.record_learning(
                kind=MemoryKind.ROUTINE,
                evidence_origin=EvidenceOrigin.HYPOTHESIS,
                content="Synthetic pickup may usually happen around 15:00.",
            )
            self.assertEqual(
                hypothesis.lifecycle,
                MemoryLifecycle.PROVISIONAL,
            )

    def test_forget_is_idempotent_and_blocks_repromotion(self) -> None:
        with TemporaryDirectory() as temp:
            store = FileMemoryStore(
                temp,
                id_factory=_ids("5" * 32),
            )
            observed = store.record_learning(
                kind=MemoryKind.PREFERENCE,
                evidence_origin=EvidenceOrigin.BEHAVIORAL_OBSERVATION,
                content="Synthetic observed wording.",
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
            self.assertIn("[forgotten]", tombstone)
            self.assertNotIn("Synthetic observed wording.", tombstone)

            with self.assertRaisesRegex(RuntimeError, "not promotable"):
                store.promote_learning(
                    observed.entry_id,
                    confirmation_basis=ConfirmationBasis.EXPLICIT_USER,
                )

    def test_forget_missing_id_is_explicit_not_found(self) -> None:
        with TemporaryDirectory() as temp:
            store = FileMemoryStore(temp)
            self.assertEqual(
                store.forget("m_" + "6" * 32),
                ForgetResult.NOT_FOUND,
            )

    def test_forget_cleanup_failure_reports_active_forget_state(self) -> None:
        with TemporaryDirectory() as temp:
            history = _FakeHistory()
            store = FileMemoryStore(
                temp,
                history=history,
                id_factory=_ids("6" * 32),
            )
            entry = store.remember_explicit(
                kind=MemoryKind.FACT,
                content="Synthetic fact requiring cleanup.",
            )
            original_unlink = store._unlink_regular

            def fail_unlink(path: Path) -> None:
                raise FileMemoryError("synthetic unlink failure")

            store._unlink_regular = fail_unlink  # type: ignore[method-assign]
            try:
                with self.assertRaisesRegex(
                    FileMemoryRecoveryRequiredError,
                    "forgotten in current semantics",
                ):
                    store.forget(entry.entry_id)
            finally:
                store._unlink_regular = original_unlink  # type: ignore[method-assign]

            self.assertIsNone(store.load_memory_entry(entry.entry_id))
            self.assertTrue(
                (Path(temp) / "memory" / f"{entry.entry_id}.md").exists()
            )
            tombstone = (
                Path(temp) / "learning" / f"{entry.entry_id}.md"
            ).read_text(encoding="utf-8")
            self.assertIn("[forgotten]", tombstone)
            self.assertTrue(
                any(
                    "Capture partial forget requiring cleanup" in reason
                    for reason in self._history_reasons(history)
                )
            )

    def test_malformed_established_memory_is_never_destroyed_by_forget(
        self,
    ) -> None:
        with TemporaryDirectory() as temp:
            store = FileMemoryStore(
                temp,
                id_factory=_ids("7" * 32),
            )
            entry = store.remember_explicit(
                kind=MemoryKind.FACT,
                content="Synthetic established fact.",
            )
            path = Path(temp) / "memory" / f"{entry.entry_id}.md"
            malformed = "not TOML front matter\n"
            path.write_text(malformed, encoding="utf-8")

            with self.assertRaisesRegex(
                RuntimeError,
                "missing TOML front matter",
            ):
                store.forget(entry.entry_id)

            self.assertEqual(path.read_text(encoding="utf-8"), malformed)
            self.assertFalse(
                (Path(temp) / "learning" / f"{entry.entry_id}.md").exists()
            )

    def test_forgotten_identity_is_not_reused_even_if_tombstone_is_deleted(
        self,
    ) -> None:
        first_id = "m_" + "8" * 32
        second_id = "m_" + "9" * 32
        with TemporaryDirectory() as temp:
            first = FileMemoryStore(
                temp,
                id_factory=_ids("8" * 32),
            )
            entry = first.remember_explicit(
                kind=MemoryKind.FACT,
                content="Synthetic fact.",
            )
            self.assertEqual(entry.entry_id, first_id)
            first.forget(entry.entry_id)
            (
                Path(temp) / "learning" / f"{entry.entry_id}.md"
            ).unlink()

            reopened = FileMemoryStore(
                temp,
                id_factory=_ids("8" * 32, "9" * 32),
            )
            replacement = reopened.remember_explicit(
                kind=MemoryKind.FACT,
                content="Different synthetic fact.",
            )

            self.assertEqual(replacement.entry_id, second_id)

    def test_inactive_established_lifecycle_is_not_current_context(self) -> None:
        with TemporaryDirectory() as temp:
            store = FileMemoryStore(
                temp,
                id_factory=_ids("a" * 32),
            )
            entry = store.remember_explicit(
                kind=MemoryKind.FACT,
                content="Synthetic fact.",
            )
            path = Path(temp) / "memory" / f"{entry.entry_id}.md"
            path.write_text(
                path.read_text(encoding="utf-8").replace(
                    'lifecycle = "confirmed"',
                    'lifecycle = "stale"',
                ),
                encoding="utf-8",
            )

            self.assertIsNone(store.load_memory_entry(entry.entry_id))
            inactive = store.load_memory_entry(
                entry.entry_id,
                include_inactive=True,
            )
            self.assertIsNotNone(inactive)
            assert inactive is not None
            self.assertEqual(inactive.lifecycle, MemoryLifecycle.STALE)

    def test_wrong_area_lifecycle_is_integrity_error(self) -> None:
        with TemporaryDirectory() as temp:
            store = FileMemoryStore(
                temp,
                id_factory=_ids("b" * 32),
            )
            entry = store.remember_explicit(
                kind=MemoryKind.FACT,
                content="Synthetic fact.",
            )
            path = Path(temp) / "memory" / f"{entry.entry_id}.md"
            path.write_text(
                path.read_text(encoding="utf-8").replace(
                    'lifecycle = "confirmed"',
                    'lifecycle = "observed"',
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                RuntimeError,
                "invalid Memory entry metadata",
            ):
                store.load_memory_entry(entry.entry_id)

    def test_symlinked_memory_paths_are_rejected_without_following_target(
        self,
    ) -> None:
        with TemporaryDirectory() as temp, TemporaryDirectory() as outside:
            root = Path(temp)
            store = FileMemoryStore(root)
            entry_id = "m_" + "c" * 32
            target = Path(outside) / "outside.md"
            target.write_text("outside", encoding="utf-8")
            link = root / "memory" / f"{entry_id}.md"
            link.symlink_to(target)

            with self.assertRaisesRegex(RuntimeError, "symlink"):
                store.load_memory_entry(entry_id)

            self.assertEqual(target.read_text(encoding="utf-8"), "outside")

        with TemporaryDirectory() as temp, TemporaryDirectory() as outside:
            root = Path(temp)
            memory_dir = root / "memory"
            memory_dir.symlink_to(Path(outside), target_is_directory=True)

            with self.assertRaisesRegex(RuntimeError, "symlink"):
                FileMemoryStore(root)

    def test_manual_edit_is_captured_before_use(self) -> None:
        with TemporaryDirectory() as temp:
            store = FileMemoryStore(
                temp,
                id_factory=_ids("d" * 32),
            )
            entry = store.remember_explicit(
                kind=MemoryKind.PREFERENCE,
                content="Before manual edit.",
            )
            path = Path(temp) / "memory" / f"{entry.entry_id}.md"
            before = self._history_count(temp)
            path.write_text(
                path.read_text(encoding="utf-8").replace(
                    "Before manual edit.",
                    "After manual edit.",
                ),
                encoding="utf-8",
            )

            loaded = store.load_memory_entry(entry.entry_id)

            self.assertIsNotNone(loaded)
            assert loaded is not None
            self.assertEqual(loaded.content, "After manual edit.")
            self.assertGreater(self._history_count(temp), before)
            self.assertEqual(
                self._latest_history_message(temp),
                "Capture external Memory edits",
            )

    def test_history_is_never_used_to_rehydrate_current_memory(self) -> None:
        with TemporaryDirectory() as temp:
            store = FileMemoryStore(
                temp,
                id_factory=_ids("e" * 32),
            )
            entry = store.remember_explicit(
                kind=MemoryKind.FACT,
                content="History-only canary.",
            )
            path = Path(temp) / "memory" / f"{entry.entry_id}.md"
            self.assertTrue(path.exists())
            path.unlink()

            self.assertIsNone(store.load_memory_entry(entry.entry_id))
            self.assertFalse(path.exists())

    def test_history_failure_after_current_write_reports_committed_state(
        self,
    ) -> None:
        with TemporaryDirectory() as temp:
            history = _FakeHistory(fail_on_capture=3)
            store = FileMemoryStore(
                temp,
                history=history,
                id_factory=_ids("f" * 32),
            )

            with self.assertRaisesRegex(
                FileMemoryHistoryPendingError,
                "write is current",
            ):
                store.remember_explicit(
                    kind=MemoryKind.FACT,
                    content="Synthetic write with failed history.",
                )

            path = Path(temp) / "memory" / f"m_{'f' * 32}.md"
            self.assertTrue(path.exists())
            self.assertIn(
                "Synthetic write with failed history.",
                path.read_text(encoding="utf-8"),
            )

    def test_history_captures_manual_change_separately_before_ada_correction(
        self,
    ) -> None:
        with TemporaryDirectory() as temp:
            store = FileMemoryStore(
                temp,
                id_factory=_ids("0" * 32),
            )
            entry = store.remember_explicit(
                kind=MemoryKind.PREFERENCE,
                content="Initial.",
            )
            path = Path(temp) / "memory" / f"{entry.entry_id}.md"
            path.write_text(
                path.read_text(encoding="utf-8").replace(
                    "Initial.",
                    "Manual.",
                ),
                encoding="utf-8",
            )
            versioned = store.load_memory_entry_versioned(entry.entry_id)
            assert versioned is not None

            store.correct_memory(
                entry.entry_id,
                content="Ada correction.",
                expected_revision=versioned.revision,
            )

            messages = self._history_messages(temp)
            self.assertIn("Capture external Memory edits", messages)
            self.assertIn(
                f"Correct established Memory {entry.entry_id}",
                messages,
            )

    def test_opaque_ids_cannot_escape_root_or_use_semantic_slugs(self) -> None:
        with TemporaryDirectory() as temp:
            store = FileMemoryStore(temp)
            for bad in (
                "../outside",
                "reply-style",
                "m_not-hex",
                "m_" + "a" * 31,
            ):
                with self.subTest(bad=bad):
                    with self.assertRaises(ValueError):
                        store.load_memory_entry(bad)

    @staticmethod
    def _history_count(root: str) -> int:
        with Repo(str(Path(root) / ".ada-history.git")) as repo:
            try:
                head = repo.head()
            except KeyError:
                return 0
            return sum(1 for _ in repo.get_walker(include=[head]))

    @staticmethod
    def _history_messages(root: str) -> list[str]:
        with Repo(str(Path(root) / ".ada-history.git")) as repo:
            try:
                head = repo.head()
            except KeyError:
                return []
            return [
                item.commit.message.decode("utf-8").strip()
                for item in repo.get_walker(include=[head])
            ]

    @staticmethod
    def _history_reasons(history: _FakeHistory) -> list[str]:
        return list(history.reasons)

    @classmethod
    def _latest_history_message(cls, root: str) -> str:
        messages = cls._history_messages(root)
        if not messages:
            raise AssertionError("expected at least one history revision")
        return messages[0]


if __name__ == "__main__":
    unittest.main()
