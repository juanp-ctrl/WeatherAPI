from __future__ import annotations

from ...domain.entities.location import Location
from ...domain.repositories.location_repository import LocationRepository
from ..dtos.location_dto import LocationCreateDTO, LocationResponseDTO


class RegisterLocationUseCase:
    def __init__(self, repository: LocationRepository) -> None:
        self._repository = repository

    async def execute(self, dto: LocationCreateDTO) -> LocationResponseDTO:
        location = Location(
            name=dto.name,
            latitude=dto.latitude,
            longitude=dto.longitude,
            timezone=dto.timezone,
        )
        saved = await self._repository.save(location)
        return LocationResponseDTO.model_validate(saved)
