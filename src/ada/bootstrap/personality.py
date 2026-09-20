from __future__ import annotations

from importlib.resources import files
import tomllib

from ada.core.personality import PersonalityProfile
from ada.ports.personality_memory import PersonalityMemoryPort


def load_bootstrap_personality() -> PersonalityProfile:
    """Load the distribution's default personality seed."""

    raw = (
        files("ada.bootstrap")
        .joinpath("default_personality.toml")
        .read_bytes()
    )
    data = tomllib.loads(raw.decode("utf-8"))
    return PersonalityProfile(
        schema_version=int(data["schema_version"]),
        profile_id=str(data["profile_id"]),
        display_name=str(data["display_name"]),
        inspiration=str(data["inspiration"]).strip(),
        background_story=str(data["background_story"]).strip(),
        traits=tuple(str(item) for item in data["traits"]),
        interaction_style=tuple(
            str(item) for item in data["interaction_style"]
        ),
        boundaries=tuple(str(item) for item in data["boundaries"]),
    )


def bootstrap_personality_memory(
    memory: PersonalityMemoryPort,
) -> PersonalityProfile:
    """Seed empty Memory exactly once, then use Memory as the active source."""

    existing = memory.load_personality()
    if existing is not None:
        return existing

    seed = load_bootstrap_personality()
    memory.save_personality(
        seed,
        reason="initial personality bootstrap from distribution seed",
    )

    stored = memory.load_personality()
    if stored is None:
        raise RuntimeError(
            "personality Memory did not return the profile after bootstrap"
        )
    return stored
