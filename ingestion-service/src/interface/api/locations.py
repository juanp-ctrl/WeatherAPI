from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status

from ...application.dtos.location_dto import (
    LocationCreateDTO,
    LocationResponseDTO,
    LocationUpdateDTO,
)
from ...application.use_cases.delete_location import DeleteLocationUseCase
from ...application.use_cases.get_location import GetLocationUseCase
from ...application.use_cases.list_locations import ListLocationsUseCase
from ...application.use_cases.register_location import RegisterLocationUseCase
from ...application.use_cases.update_location import UpdateLocationUseCase
from ..dependencies import (
    get_delete_location_uc,
    get_get_location_uc,
    get_list_locations_uc,
    get_register_location_uc,
    get_update_location_uc,
    require_api_key,
)

router = APIRouter(prefix="/api/v1/locations", tags=["locations"])


@router.get("", response_model=list[LocationResponseDTO])
async def list_locations(
    active_only: bool = False,
    uc: ListLocationsUseCase = Depends(get_list_locations_uc),
) -> list[LocationResponseDTO]:
    return await uc.execute(active_only=active_only)


@router.post(
    "",
    response_model=LocationResponseDTO,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_api_key)],
)
async def create_location(
    dto: LocationCreateDTO,
    uc: RegisterLocationUseCase = Depends(get_register_location_uc),
) -> LocationResponseDTO:
    return await uc.execute(dto)


@router.get("/{location_id}", response_model=LocationResponseDTO)
async def get_location(
    location_id: UUID,
    uc: GetLocationUseCase = Depends(get_get_location_uc),
) -> LocationResponseDTO:
    return await uc.execute(location_id)


@router.put(
    "/{location_id}",
    response_model=LocationResponseDTO,
    dependencies=[Depends(require_api_key)],
)
async def update_location(
    location_id: UUID,
    dto: LocationUpdateDTO,
    uc: UpdateLocationUseCase = Depends(get_update_location_uc),
) -> LocationResponseDTO:
    return await uc.execute(location_id, dto)


@router.delete(
    "/{location_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_api_key)],
)
async def delete_location(
    location_id: UUID,
    uc: DeleteLocationUseCase = Depends(get_delete_location_uc),
) -> None:
    await uc.execute(location_id)
