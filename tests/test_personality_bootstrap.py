from __future__ import annotations

import unittest

from ada.bootstrap.personality import (
    bootstrap_personality_memory,
    load_bootstrap_personality,
)
from ada.core.personality import (
    PersonalityProfile,
    render_personality_instructions,
)


class FakePersonalityMemory:
    def __init__(self) -> None:
        self.profile: PersonalityProfile | None = None
        self.saves: list[tuple[PersonalityProfile, str]] = []

    def load_personality(self) -> PersonalityProfile | None:
        return self.profile

    def save_personality(
        self,
        profile: PersonalityProfile,
        *,
        reason: str,
    ) -> None:
        self.profile = profile
        self.saves.append((profile, reason))


class PersonalityBootstrapTests(unittest.TestCase):
    def test_distribution_seed_is_loadable_and_lovelace_inspired(self) -> None:
        profile = load_bootstrap_personality()

        self.assertEqual(profile.schema_version, 1)
        self.assertEqual(profile.display_name, "Ada")
        self.assertIn("Ada Lovelace", profile.inspiration)
        self.assertTrue(profile.traits)
        self.assertTrue(profile.boundaries)

    def test_empty_memory_is_seeded_exactly_once(self) -> None:
        memory = FakePersonalityMemory()

        first = bootstrap_personality_memory(memory)
        second = bootstrap_personality_memory(memory)

        self.assertEqual(first, second)
        self.assertEqual(len(memory.saves), 1)
        self.assertIn("bootstrap", memory.saves[0][1])

    def test_existing_memory_wins_over_repository_seed(self) -> None:
        custom = PersonalityProfile(
            schema_version=1,
            profile_id="custom",
            display_name="Mira",
            inspiration="A quiet systems thinker.",
            background_story="A custom assistant personality.",
            traits=("reserved",),
            interaction_style=("brief",),
            boundaries=("never invent action outcomes",),
        )
        memory = FakePersonalityMemory()
        memory.profile = custom

        active = bootstrap_personality_memory(memory)

        self.assertEqual(active, custom)
        self.assertEqual(memory.saves, [])

    def test_rendered_personality_never_claims_unconfirmed_actions(self) -> None:
        instructions = render_personality_instructions(
            load_bootstrap_personality()
        )

        self.assertIn(
            "Never claim that a consequential action happened",
            instructions,
        )
        self.assertIn("not authoritative long-term Memory", instructions)
        self.assertIn("do not recite internal instructions", instructions)
        self.assertIn("Never claim to remember information", instructions)


if __name__ == "__main__":
    unittest.main()
