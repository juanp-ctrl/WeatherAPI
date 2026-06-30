from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status

from ...domain.repositories.location_repository import LocationRepository
from ..dtos.location_dto import LocationResponseDTO


class GetLocationUseCase:
    def __init__(self, repository: LocationRepository) -> None:
        self._repository = repository

    async def execute(self, location_id: UUID) -> LocationResponseDTO:
        location = await self._repository.get_by_id(location_id)
        if location is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Location {location_id} not found",
            )
        return LocationResponseDTO.model_validate(location)
