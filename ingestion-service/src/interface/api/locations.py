from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status

from ...application.dtos.location_dto import (
    LocationCreateDTO,
    LocationResponseDTO,
    LocationUpdateDTO,
)
from ..dependencies import (
    DeleteLocationUCDep,
    GetLocationUCDep,
    ListLocationsUCDep,
    RegisterLocationUCDep,
    UpdateLocationUCDep,
    require_api_key,
)

router = APIRouter(prefix="/api/v1/locations", tags=["locations"])


@router.get("")
async def list_locations(
    uc: ListLocationsUCDep,
    active_only: bool = False,
) -> list[LocationResponseDTO]:
    return await uc.execute(active_only=active_only)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_api_key)],
)
async def create_location(
    dto: LocationCreateDTO,
    uc: RegisterLocationUCDep,
) -> LocationResponseDTO:
    return await uc.execute(dto)


@router.get("/{location_id}")
async def get_location(
    location_id: UUID,
    uc: GetLocationUCDep,
) -> LocationResponseDTO:
    return await uc.execute(location_id)


@router.put(
    "/{location_id}",
    dependencies=[Depends(require_api_key)],
)
async def update_location(
    location_id: UUID,
    dto: LocationUpdateDTO,
    uc: UpdateLocationUCDep,
) -> LocationResponseDTO:
    return await uc.execute(location_id, dto)


@router.delete(
    "/{location_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_api_key)],
)
async def delete_location(
    location_id: UUID,
    uc: DeleteLocationUCDep,
) -> None:
    await uc.execute(location_id)
