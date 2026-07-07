from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security.api_key import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession

from ..application.use_cases.acknowledge_alert import AcknowledgeAlertUseCase
from ..application.use_cases.crud_rules import (
    CreateRuleUseCase,
    DeleteRuleUseCase,
    GetRuleUseCase,
    ListRulesUseCase,
    UpdateRuleUseCase,
)
from ..application.use_cases.list_alerts import GetAlertUseCase, ListAlertsUseCase
from ..application.use_cases.list_processed_observations import (
    GetProcessedObservationUseCase,
    ListProcessedObservationsUseCase,
)
from ..application.use_cases.process_observations import ProcessObservationsUseCase
from ..infrastructure.config.settings import get_settings
from ..infrastructure.external.http_ingestion_client import HttpIngestionClient
from ..infrastructure.persistence.alert_repository import SQLAlchemyAlertRepository
from ..infrastructure.persistence.database import get_db_session
from ..infrastructure.persistence.processed_observation_repository import (
    SQLAlchemyProcessedObservationRepository,
)
from ..infrastructure.persistence.processing_rule_repository import (
    SQLAlchemyProcessingRuleRepository,
)
from ..infrastructure.persistence.watermark_repository import (
    SQLAlchemyWatermarkRepository,
)

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(
    api_key: Annotated[str | None, Security(_api_key_header)],
) -> None:
    settings = get_settings()
    if not api_key or api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_db_session():
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_obs_repo(session: SessionDep) -> SQLAlchemyProcessedObservationRepository:
    return SQLAlchemyProcessedObservationRepository(session)


def get_alert_repo(session: SessionDep) -> SQLAlchemyAlertRepository:
    return SQLAlchemyAlertRepository(session)


def get_rule_repo(session: SessionDep) -> SQLAlchemyProcessingRuleRepository:
    return SQLAlchemyProcessingRuleRepository(session)


def get_watermark_repo(session: SessionDep) -> SQLAlchemyWatermarkRepository:
    return SQLAlchemyWatermarkRepository(session)


ObsRepoDep = Annotated[SQLAlchemyProcessedObservationRepository, Depends(get_obs_repo)]
AlertRepoDep = Annotated[SQLAlchemyAlertRepository, Depends(get_alert_repo)]
RuleRepoDep = Annotated[SQLAlchemyProcessingRuleRepository, Depends(get_rule_repo)]
WatermarkRepoDep = Annotated[SQLAlchemyWatermarkRepository, Depends(get_watermark_repo)]


def get_ingestion_client(request: Request) -> HttpIngestionClient:
    settings = get_settings()
    return HttpIngestionClient(
        client=request.app.state.http_client,
        base_url=settings.ingestion_service_url,
    )


IngestionClientDep = Annotated[HttpIngestionClient, Depends(get_ingestion_client)]


def get_process_uc(
    ingestion_client: IngestionClientDep,
    obs_repo: ObsRepoDep,
    alert_repo: AlertRepoDep,
    rule_repo: RuleRepoDep,
    watermark_repo: WatermarkRepoDep,
) -> ProcessObservationsUseCase:
    return ProcessObservationsUseCase(
        ingestion_client, obs_repo, alert_repo, rule_repo, watermark_repo
    )


def get_list_obs_uc(repo: ObsRepoDep) -> ListProcessedObservationsUseCase:
    return ListProcessedObservationsUseCase(repo)


def get_get_obs_uc(repo: ObsRepoDep) -> GetProcessedObservationUseCase:
    return GetProcessedObservationUseCase(repo)


def get_list_alerts_uc(repo: AlertRepoDep) -> ListAlertsUseCase:
    return ListAlertsUseCase(repo)


def get_get_alert_uc(repo: AlertRepoDep) -> GetAlertUseCase:
    return GetAlertUseCase(repo)


def get_ack_alert_uc(repo: AlertRepoDep) -> AcknowledgeAlertUseCase:
    return AcknowledgeAlertUseCase(repo)


def get_create_rule_uc(repo: RuleRepoDep) -> CreateRuleUseCase:
    return CreateRuleUseCase(repo)


def get_get_rule_uc(repo: RuleRepoDep) -> GetRuleUseCase:
    return GetRuleUseCase(repo)


def get_list_rules_uc(repo: RuleRepoDep) -> ListRulesUseCase:
    return ListRulesUseCase(repo)


def get_update_rule_uc(repo: RuleRepoDep) -> UpdateRuleUseCase:
    return UpdateRuleUseCase(repo)


def get_delete_rule_uc(repo: RuleRepoDep) -> DeleteRuleUseCase:
    return DeleteRuleUseCase(repo)


ProcessUseCaseDep = Annotated[ProcessObservationsUseCase, Depends(get_process_uc)]
ListObsUseCaseDep = Annotated[
    ListProcessedObservationsUseCase, Depends(get_list_obs_uc)
]
GetObsUseCaseDep = Annotated[
    GetProcessedObservationUseCase, Depends(get_get_obs_uc)
]
ListAlertsUseCaseDep = Annotated[ListAlertsUseCase, Depends(get_list_alerts_uc)]
GetAlertUseCaseDep = Annotated[GetAlertUseCase, Depends(get_get_alert_uc)]
AckAlertUseCaseDep = Annotated[AcknowledgeAlertUseCase, Depends(get_ack_alert_uc)]
CreateRuleUseCaseDep = Annotated[CreateRuleUseCase, Depends(get_create_rule_uc)]
GetRuleUseCaseDep = Annotated[GetRuleUseCase, Depends(get_get_rule_uc)]
ListRulesUseCaseDep = Annotated[ListRulesUseCase, Depends(get_list_rules_uc)]
UpdateRuleUseCaseDep = Annotated[UpdateRuleUseCase, Depends(get_update_rule_uc)]
DeleteRuleUseCaseDep = Annotated[DeleteRuleUseCase, Depends(get_delete_rule_uc)]
