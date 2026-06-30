from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ProcessedObservationResponseDTO(BaseModel):
    id: UUID
    raw_observation_id: UUID
    location_id: UUID
    temperature_c: float | None = None
    humidity_pct: float | None = None
    wind_speed_kmh: float | None = None
    precipitation_mm: float | None = None
    weather_code: int | None = None
    heat_index_c: float | None = None
    wind_chill_c: float | None = None
    feels_like_c: float | None = None
    severity_score: int
    observed_at: datetime
    processed_at: datetime | None = None

    model_config = {"from_attributes": True}


class ProcessedObservationListDTO(BaseModel):
    items: list[ProcessedObservationResponseDTO]
    total: int
    limit: int
    offset: int


class ProcessResultDTO(BaseModel):
    observations_processed: int
    alerts_generated: int
    errors: list[str] = []
