from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class LocationCreateDTO(BaseModel):
    name: str = Field(max_length=255)
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    timezone: str = Field(default="UTC", max_length=64)


class LocationUpdateDTO(BaseModel):
    name: str | None = Field(None, max_length=255)
    latitude: float | None = Field(None, ge=-90.0, le=90.0)
    longitude: float | None = Field(None, ge=-180.0, le=180.0)
    timezone: str | None = Field(None, max_length=64)
    is_active: bool | None = None


class LocationResponseDTO(BaseModel):
    id: UUID
    name: str
    latitude: float
    longitude: float
    timezone: str
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}
