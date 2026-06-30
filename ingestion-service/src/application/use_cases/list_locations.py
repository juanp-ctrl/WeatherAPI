from __future__ import annotations

from ...domain.repositories.location_repository import LocationRepository
from ..dtos.location_dto import LocationResponseDTO


class ListLocationsUseCase:
    def __init__(self, repository: LocationRepository) -> None:
        self._repository = repository

    async def execute(self, active_only: bool = False) -> list[LocationResponseDTO]:
        locations = await self._repository.list_all(active_only=active_only)
        return [LocationResponseDTO.model_validate(loc) for loc in locations]
