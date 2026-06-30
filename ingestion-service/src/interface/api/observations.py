from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from ...application.dtos.observation_dto import (
    IngestResultDTO,
    ObservationListResponseDTO,
    ObservationResponseDTO,
)
from ...application.use_cases.get_observation import GetObservationUseCase
from ...application.use_cases.ingest_observations import IngestObservationsUseCase
from ...application.use_cases.list_observations import ListObservationsUseCase
from ..dependencies import (
    get_get_observation_uc,
    get_ingest_uc,
    get_list_observations_uc,
    require_api_key,
)

router = APIRouter(prefix="/api/v1/observations", tags=["observations"])


@router.get("", response_model=ObservationListResponseDTO)
async def list_observations(
    location_id: UUID | None = Query(None),
    since: datetime | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    uc: ListObservationsUseCase = Depends(get_list_observations_uc),
) -> ObservationListResponseDTO:
    return await uc.execute(
        location_id=location_id, since=since, limit=limit, offset=offset
    )


@router.get("/{observation_id}", response_model=ObservationResponseDTO)
async def get_observation(
    observation_id: UUID,
    uc: GetObservationUseCase = Depends(get_get_observation_uc),
) -> ObservationResponseDTO:
    return await uc.execute(observation_id)


@router.post(
    "/ingest",
    response_model=IngestResultDTO,
    dependencies=[Depends(require_api_key)],
)
async def trigger_ingestion(
    uc: IngestObservationsUseCase = Depends(get_ingest_uc),
) -> IngestResultDTO:
    return await uc.execute()
