from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Protocol


@dataclass(frozen=True, slots=True)
class TravelEstimate:
    # None means the registered route has no configured duration. Never infer 0.
    duration: timedelta | None
    source: str


class TravelTimePort(Protocol):
    """Approximate travel-time boundary without implying location tracking."""

    def estimate(self, *, origin: str, destination: str) -> TravelEstimate:
        """Return a configured approximate duration, or an explicit unknown."""
