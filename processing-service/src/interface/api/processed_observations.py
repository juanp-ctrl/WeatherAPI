from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from ...application.dtos.processed_observation_dto import (
    ProcessResultDTO,
    ProcessedObservationListDTO,
    ProcessedObservationResponseDTO,
)
from ...application.use_cases.list_processed_observations import (
    GetProcessedObservationUseCase,
    ListProcessedObservationsUseCase,
)
from ...application.use_cases.process_observations import ProcessObservationsUseCase
from ..dependencies import (
    get_get_obs_uc,
    get_list_obs_uc,
    get_process_uc,
    require_api_key,
)

router = APIRouter(tags=["processed-observations"])


@router.get("/api/v1/processed", response_model=ProcessedObservationListDTO)
async def list_processed(
    location_id: UUID | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    uc: ListProcessedObservationsUseCase = Depends(get_list_obs_uc),
) -> ProcessedObservationListDTO:
    return await uc.execute(location_id=location_id, limit=limit, offset=offset)


@router.get("/api/v1/processed/{observation_id}", response_model=ProcessedObservationResponseDTO)
async def get_processed(
    observation_id: UUID,
    uc: GetProcessedObservationUseCase = Depends(get_get_obs_uc),
) -> ProcessedObservationResponseDTO:
    return await uc.execute(observation_id)


@router.post(
    "/api/v1/process",
    response_model=ProcessResultDTO,
    dependencies=[Depends(require_api_key)],
)
async def trigger_processing(
    uc: ProcessObservationsUseCase = Depends(get_process_uc),
) -> ProcessResultDTO:
    return await uc.execute()
