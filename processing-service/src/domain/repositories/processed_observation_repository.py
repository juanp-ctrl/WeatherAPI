from __future__ import annotations

from typing import Protocol
from uuid import UUID

from ..entities.processed_observation import ProcessedObservation


class ProcessedObservationRepository(Protocol):
    async def get_by_id(self, observation_id: UUID) -> ProcessedObservation | None: ...
    async def list(
        self,
        location_id: UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ProcessedObservation]: ...
    async def count(self, location_id: UUID | None = None) -> int: ...
    async def save(self, observation: ProcessedObservation) -> ProcessedObservation: ...
