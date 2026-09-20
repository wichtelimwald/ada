from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Protocol


@dataclass(frozen=True, slots=True)
class TravelEstimate:
    duration: timedelta
    source: str


class TravelTimePort(Protocol):
    """Approximate travel-time boundary without implying location tracking."""

    def estimate(self, *, origin: str, destination: str) -> TravelEstimate:
        """Return an approximate travel duration and its source."""
