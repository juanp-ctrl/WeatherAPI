from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status

from ...domain.repositories.processed_observation_repository import (
    ProcessedObservationRepository,
)
from ..dtos.processed_observation_dto import (
    ProcessedObservationListDTO,
    ProcessedObservationResponseDTO,
)


class ListProcessedObservationsUseCase:
    def __init__(self, repository: ProcessedObservationRepository) -> None:
        self._repository = repository

    async def execute(
        self,
        location_id: UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> ProcessedObservationListDTO:
        items = await self._repository.list(
            location_id=location_id, limit=limit, offset=offset
        )
        total = await self._repository.count(location_id=location_id)
        return ProcessedObservationListDTO(
            items=[ProcessedObservationResponseDTO.model_validate(o) for o in items],
            total=total,
            limit=limit,
            offset=offset,
        )


class GetProcessedObservationUseCase:
    def __init__(self, repository: ProcessedObservationRepository) -> None:
        self._repository = repository

    async def execute(self, observation_id: UUID) -> ProcessedObservationResponseDTO:
        obs = await self._repository.get_by_id(observation_id)
        if obs is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Processed observation {observation_id} not found",
            )
        return ProcessedObservationResponseDTO.model_validate(obs)
