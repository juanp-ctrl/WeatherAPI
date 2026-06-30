from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4


@dataclass
class Alert:
    processed_observation_id: UUID
    rule_id: UUID
    alert_type: str
    severity: str
    message: str
    acknowledged: bool = False
    id: UUID = field(default_factory=uuid4)
    created_at: datetime | None = None
    acknowledged_at: datetime | None = None
