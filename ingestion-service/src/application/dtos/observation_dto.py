from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ObservationResponseDTO(BaseModel):
    id: UUID
    location_id: UUID
    temperature_c: float | None = None
    humidity_pct: float | None = None
    wind_speed_kmh: float | None = None
    precipitation_mm: float | None = None
    weather_code: int | None = None
    observed_at: datetime
    ingested_at: datetime | None = None

    model_config = {"from_attributes": True}


class ObservationListResponseDTO(BaseModel):
    items: list[ObservationResponseDTO]
    total: int
    limit: int
    offset: int


class IngestResultDTO(BaseModel):
    locations_processed: int
    observations_stored: int
    errors: list[str] = []
