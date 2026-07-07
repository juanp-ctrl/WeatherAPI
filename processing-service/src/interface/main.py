from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from ..application.use_cases.process_observations import ProcessObservationsUseCase
from ..infrastructure.config.settings import get_settings
from ..infrastructure.external.http_ingestion_client import HttpIngestionClient
from ..infrastructure.persistence.alert_repository import SQLAlchemyAlertRepository
from ..infrastructure.persistence.database import dispose_engine, get_session_maker, init_engine
from ..infrastructure.persistence.processed_observation_repository import (
    SQLAlchemyProcessedObservationRepository,
)
from ..infrastructure.persistence.processing_rule_repository import (
    SQLAlchemyProcessingRuleRepository,
)
from ..infrastructure.persistence.watermark_repository import SQLAlchemyWatermarkRepository
from .api.alerts import router as alerts_router
from .api.health import router as health_router
from .api.processed_observations import router as processed_router
from .api.rules import router as rules_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def _processing_loop(
    interval_seconds: int,
    ingestion_service_url: str,
    http_client: httpx.AsyncClient,
) -> None:
    ingestion_client = HttpIngestionClient(client=http_client, base_url=ingestion_service_url)
    maker = get_session_maker()

    while True:
        try:
            async with maker() as session:
                async with session.begin():
                    uc = ProcessObservationsUseCase(
                        ingestion_client=ingestion_client,
                        obs_repo=SQLAlchemyProcessedObservationRepository(session),
                        alert_repo=SQLAlchemyAlertRepository(session),
                        rule_repo=SQLAlchemyProcessingRuleRepository(session),
                        watermark_repo=SQLAlchemyWatermarkRepository(session),
                    )
                    result = await uc.execute()
                    logger.info(
                        "Scheduler: processed %d observation(s), %d alert(s) generated",
                        result.observations_processed,
                        result.alerts_generated,
                    )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error("Processing scheduler error: %s", exc)

        await asyncio.sleep(interval_seconds)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    logging.getLogger().setLevel(settings.log_level.upper())

    init_engine(settings)
    logger.info("Database engine initialised")

    http_client = httpx.AsyncClient(timeout=10.0)
    app.state.http_client = http_client

    scheduler_task = asyncio.create_task(
        _processing_loop(
            settings.processing_interval_seconds,
            settings.ingestion_service_url,
            http_client,
        )
    )
    logger.info(
        "Processing scheduler started (interval=%ds)", settings.processing_interval_seconds
    )

    yield

    scheduler_task.cancel()
    try:
        await scheduler_task
    except asyncio.CancelledError:
        pass

    await http_client.aclose()
    await dispose_engine()
    logger.info("Shutdown complete")


app = FastAPI(title="processing-service", lifespan=lifespan)

app.include_router(health_router)
app.include_router(processed_router)
app.include_router(alerts_router)
app.include_router(rules_router)
