from __future__ import annotations

from typing import Protocol

from ..entities.location import Location
from ..entities.raw_observation import RawObservation


class WeatherDataSource(Protocol):
    async def fetch_current(self, location: Location) -> list[RawObservation]: ...
