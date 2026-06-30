from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID


class RawObservationData:
    """Plain data object carrying a raw observation from the ingestion service."""

    __slots__ = (
        "id",
        "location_id",
        "temperature_c",
        "humidity_pct",
        "wind_speed_kmh",
        "precipitation_mm",
        "weather_code",
        "observed_at",
        "ingested_at",
    )

    def __init__(
        self,
        id: UUID,
        location_id: UUID,
        observed_at: datetime,
        ingested_at: datetime,
        temperature_c: float | None = None,
        humidity_pct: float | None = None,
        wind_speed_kmh: float | None = None,
        precipitation_mm: float | None = None,
        weather_code: int | None = None,
    ) -> None:
        self.id = id
        self.location_id = location_id
        self.temperature_c = temperature_c
        self.humidity_pct = humidity_pct
        self.wind_speed_kmh = wind_speed_kmh
        self.precipitation_mm = precipitation_mm
        self.weather_code = weather_code
        self.observed_at = observed_at
        self.ingested_at = ingested_at


class IngestionClient(Protocol):
    async def get_observations(
        self,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[RawObservationData]: ...
