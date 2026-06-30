from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Depends, HTTPException, Security, status
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


async def require_api_key(api_key: str | None = Security(_api_key_header)) -> None:
    settings = get_settings()
    if not api_key or api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_db_session():
        yield session


def get_obs_repo(session: AsyncSession = Depends(get_session)):
    return SQLAlchemyProcessedObservationRepository(session)


def get_alert_repo(session: AsyncSession = Depends(get_session)):
    return SQLAlchemyAlertRepository(session)


def get_rule_repo(session: AsyncSession = Depends(get_session)):
    return SQLAlchemyProcessingRuleRepository(session)


def get_watermark_repo(session: AsyncSession = Depends(get_session)):
    return SQLAlchemyWatermarkRepository(session)


def get_ingestion_client():
    settings = get_settings()
    return HttpIngestionClient(base_url=settings.ingestion_service_url)


def get_process_uc(
    ingestion_client=Depends(get_ingestion_client),
    obs_repo=Depends(get_obs_repo),
    alert_repo=Depends(get_alert_repo),
    rule_repo=Depends(get_rule_repo),
    watermark_repo=Depends(get_watermark_repo),
) -> ProcessObservationsUseCase:
    return ProcessObservationsUseCase(
        ingestion_client, obs_repo, alert_repo, rule_repo, watermark_repo
    )


def get_list_obs_uc(repo=Depends(get_obs_repo)) -> ListProcessedObservationsUseCase:
    return ListProcessedObservationsUseCase(repo)


def get_get_obs_uc(repo=Depends(get_obs_repo)) -> GetProcessedObservationUseCase:
    return GetProcessedObservationUseCase(repo)


def get_list_alerts_uc(repo=Depends(get_alert_repo)) -> ListAlertsUseCase:
    return ListAlertsUseCase(repo)


def get_get_alert_uc(repo=Depends(get_alert_repo)) -> GetAlertUseCase:
    return GetAlertUseCase(repo)


def get_ack_alert_uc(repo=Depends(get_alert_repo)) -> AcknowledgeAlertUseCase:
    return AcknowledgeAlertUseCase(repo)


def get_create_rule_uc(repo=Depends(get_rule_repo)) -> CreateRuleUseCase:
    return CreateRuleUseCase(repo)


def get_get_rule_uc(repo=Depends(get_rule_repo)) -> GetRuleUseCase:
    return GetRuleUseCase(repo)


def get_list_rules_uc(repo=Depends(get_rule_repo)) -> ListRulesUseCase:
    return ListRulesUseCase(repo)


def get_update_rule_uc(repo=Depends(get_rule_repo)) -> UpdateRuleUseCase:
    return UpdateRuleUseCase(repo)


def get_delete_rule_uc(repo=Depends(get_rule_repo)) -> DeleteRuleUseCase:
    return DeleteRuleUseCase(repo)
