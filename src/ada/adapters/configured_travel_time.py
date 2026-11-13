from __future__ import annotations

from datetime import timedelta
from typing import Mapping

from ada.ports.travel_time import TravelEstimate, TravelTimePort


class ConfiguredTravelTime(TravelTimePort):
    """Local, directional approximate travel times for registered place keys.

    No routing service or network access. A missing pair is explicitly unknown;
    the reverse route is not assumed equal unless it is configured separately.
    """

    def __init__(
        self,
        durations: Mapping[tuple[str, str], timedelta],
    ) -> None:
        checked: dict[tuple[str, str], timedelta] = {}
        for (origin, destination), duration in durations.items():
            if (
                not isinstance(origin, str)
                or not origin.strip()
                or not isinstance(destination, str)
                or not destination.strip()
                or not isinstance(duration, timedelta)
                or duration < timedelta(0)
            ):
                raise ValueError("registered routes need place keys and nonnegative durations")
            checked[(origin, destination)] = duration
        self._durations = checked

    def estimate(self, *, origin: str, destination: str) -> TravelEstimate:
        duration = self._durations.get((origin, destination))
        if duration is None:
            return TravelEstimate(duration=None, source="unconfigured")
        return TravelEstimate(duration=duration, source="configured")
