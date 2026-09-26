from __future__ import annotations

from typing import Protocol

from ada.core.personality import PersonalityProfile


class PersonalityMemoryPort(Protocol):
    """Narrow Memory capability required to bootstrap and load Ada's personality."""

    def load_personality(self) -> PersonalityProfile | None:
        """Return the active personality, or None when Memory is empty."""

    def save_personality(
        self,
        profile: PersonalityProfile,
        *,
        reason: str,
    ) -> None:
        """Initialize personality without clobbering an already existing profile."""
