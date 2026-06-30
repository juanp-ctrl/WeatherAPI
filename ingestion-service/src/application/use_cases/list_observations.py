from __future__ import annotations

from datetime import datetime
from uuid import UUID

from ...domain.repositories.raw_observation_repository import RawObservationRepository
from ..dtos.observation_dto import ObservationListResponseDTO, ObservationResponseDTO


class ListObservationsUseCase:
    def __init__(self, repository: RawObservationRepository) -> None:
        self._repository = repository

    async def execute(
        self,
        location_id: UUID | None = None,
        since: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> ObservationListResponseDTO:
        items, total = await _fetch(self._repository, location_id, since, limit, offset)
        return ObservationListResponseDTO(
            items=[ObservationResponseDTO.model_validate(obs) for obs in items],
            total=total,
            limit=limit,
            offset=offset,
        )


async def _fetch(repository, location_id, since, limit, offset):
    items = await repository.list(
        location_id=location_id, since=since, limit=limit, offset=offset
    )
    total = await repository.count(location_id=location_id, since=since)
    return items, total
