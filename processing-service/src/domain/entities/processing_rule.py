from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

VALID_OPERATORS = frozenset({">", ">=", "<", "<=", "=="})


@dataclass
class ProcessingRule:
    metric: str
    operator: str
    threshold: float
    severity: str
    alert_type: str
    message_template: str
    is_active: bool = True
    id: UUID = field(default_factory=uuid4)
    created_at: datetime | None = None
    updated_at: datetime | None = None
