from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4


@dataclass
class ProcessedObservation:
    raw_observation_id: UUID
    location_id: UUID
    observed_at: datetime
    severity_score: int = 0
    temperature_c: float | None = None
    humidity_pct: float | None = None
    wind_speed_kmh: float | None = None
    precipitation_mm: float | None = None
    weather_code: int | None = None
    heat_index_c: float | None = None
    wind_chill_c: float | None = None
    feels_like_c: float | None = None
    id: UUID = field(default_factory=uuid4)
    processed_at: datetime | None = None
