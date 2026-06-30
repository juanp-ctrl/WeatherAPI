from __future__ import annotations

from typing import Protocol
from datetime import datetime
from uuid import UUID

from ..entities.raw_observation import RawObservation


class RawObservationRepository(Protocol):
    async def get_by_id(self, observation_id: UUID) -> RawObservation | None: ...
    async def list(
        self,
        location_id: UUID | None = None,
        since: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[RawObservation]: ...
    async def count(
        self,
        location_id: UUID | None = None,
        since: datetime | None = None,
    ) -> int: ...
    async def save_many(self, observations: list[RawObservation]) -> int: ...
