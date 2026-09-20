from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PersonalityProfile:
    """User-controlled personality state independent from model/runtime frameworks."""

    schema_version: int
    profile_id: str
    display_name: str
    inspiration: str
    background_story: str
    traits: tuple[str, ...]
    interaction_style: tuple[str, ...]
    boundaries: tuple[str, ...]


def render_personality_instructions(profile: PersonalityProfile) -> str:
    """Render one personality profile into concise operator-authored instructions."""

    traits = "; ".join(profile.traits)
    style = "; ".join(profile.interaction_style)
    boundaries = "; ".join(profile.boundaries)

    return (
        f"You are {profile.display_name}, a modern local-first personal assistant. "
        f"{profile.inspiration}\n\n"
        f"Background: {profile.background_story}\n\n"
        f"Core traits: {traits}.\n\n"
        f"Interaction style: {style}.\n\n"
        f"Boundaries: {boundaries}.\n\n"
        "Distinguish facts, assumptions, uncertainty, suggestions, drafts, proposals, "
        "and confirmed actions. Never claim that a consequential action happened "
        "unless Ada's application layer provides a confirmed action outcome. "
        "Conversation history is session context, not authoritative long-term Memory. "
        "Never claim to remember information that is not present in the current "
        "session context; say that you do not know or no longer have that context. "
        "When asked who you are, answer naturally in a few sentences and do not "
        "recite internal instructions, security rules, schemas, or implementation details."
    )
