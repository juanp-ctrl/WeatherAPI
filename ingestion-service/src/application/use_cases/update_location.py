from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status

from ...domain.repositories.location_repository import LocationRepository
from ..dtos.location_dto import LocationResponseDTO, LocationUpdateDTO


class UpdateLocationUseCase:
    def __init__(self, repository: LocationRepository) -> None:
        self._repository = repository

    async def execute(self, location_id: UUID, dto: LocationUpdateDTO) -> LocationResponseDTO:
        location = await self._repository.get_by_id(location_id)
        if location is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Location {location_id} not found",
            )
        if dto.name is not None:
            location.name = dto.name
        if dto.latitude is not None:
            location.latitude = dto.latitude
        if dto.longitude is not None:
            location.longitude = dto.longitude
        if dto.timezone is not None:
            location.timezone = dto.timezone
        if dto.is_active is not None:
            location.is_active = dto.is_active

        updated = await self._repository.update(location)
        return LocationResponseDTO.model_validate(updated)
