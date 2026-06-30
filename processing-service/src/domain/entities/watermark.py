from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4


@dataclass
class Watermark:
    source: str
    last_ingested_at: datetime
    id: UUID = field(default_factory=uuid4)
    updated_at: datetime | None = None
