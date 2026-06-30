from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status

from ...domain.repositories.raw_observation_repository import RawObservationRepository
from ..dtos.observation_dto import ObservationResponseDTO


class GetObservationUseCase:
    def __init__(self, repository: RawObservationRepository) -> None:
        self._repository = repository

    async def execute(self, observation_id: UUID) -> ObservationResponseDTO:
        observation = await self._repository.get_by_id(observation_id)
        if observation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Observation {observation_id} not found",
            )
        return ObservationResponseDTO.model_validate(observation)
