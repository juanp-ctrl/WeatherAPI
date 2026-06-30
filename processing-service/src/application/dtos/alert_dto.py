from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AlertResponseDTO(BaseModel):
    id: UUID
    processed_observation_id: UUID
    rule_id: UUID
    alert_type: str
    severity: str
    message: str
    acknowledged: bool
    created_at: datetime | None = None
    acknowledged_at: datetime | None = None

    model_config = {"from_attributes": True}


class AlertListDTO(BaseModel):
    items: list[AlertResponseDTO]
    total: int
    limit: int
    offset: int
