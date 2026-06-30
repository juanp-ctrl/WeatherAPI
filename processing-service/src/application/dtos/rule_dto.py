from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class RuleCreateDTO(BaseModel):
    metric: str = Field(..., max_length=64)
    operator: str = Field(..., pattern=r"^(>|>=|<|<=|==)$")
    threshold: float
    severity: str = Field(..., pattern=r"^(LOW|MEDIUM|HIGH|CRITICAL)$")
    alert_type: str = Field(..., max_length=64)
    message_template: str = Field(
        ...,
        description="Template with {value} and {threshold} placeholders",
    )
    is_active: bool = True


class RuleUpdateDTO(BaseModel):
    metric: str | None = Field(None, max_length=64)
    operator: str | None = Field(None, pattern=r"^(>|>=|<|<=|==)$")
    threshold: float | None = None
    severity: str | None = Field(None, pattern=r"^(LOW|MEDIUM|HIGH|CRITICAL)$")
    alert_type: str | None = Field(None, max_length=64)
    message_template: str | None = None
    is_active: bool | None = None


class RuleResponseDTO(BaseModel):
    id: UUID
    metric: str
    operator: str
    threshold: float
    severity: str
    alert_type: str
    message_template: str
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}
