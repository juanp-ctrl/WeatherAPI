from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from ..infrastructure.config.settings import get_settings
from ..infrastructure.external.open_meteo_adapter import OpenMeteoAdapter
from ..infrastructure.persistence.database import dispose_engine, get_session_maker, init_engine
from ..infrastructure.persistence.location_repository import SQLAlchemyLocationRepository
from ..infrastructure.persistence.raw_observation_repository import (
    SQLAlchemyRawObservationRepository,
)
from ..application.use_cases.ingest_observations import IngestObservationsUseCase
from .api.health import router as health_router
from .api.locations import router as locations_router
from .api.observations import router as observations_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def _ingestion_loop(interval_seconds: int) -> None:
    settings = get_settings()
    weather_source = OpenMeteoAdapter(base_url=settings.open_meteo_base_url)
    maker = get_session_maker()

    while True:
        try:
            async with maker() as session:
                async with session.begin():
                    loc_repo = SQLAlchemyLocationRepository(session)
                    obs_repo = SQLAlchemyRawObservationRepository(session)
                    uc = IngestObservationsUseCase(loc_repo, obs_repo, weather_source)
                    result = await uc.execute()
                    logger.info(
                        "Scheduler: ingested %d observation(s) across %d location(s)",
                        result.observations_stored,
                        result.locations_processed,
                    )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error("Ingestion scheduler error: %s", exc)

        await asyncio.sleep(interval_seconds)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    logging.getLogger().setLevel(settings.log_level.upper())

    init_engine(settings)
    logger.info("Database engine initialised")

    scheduler_task = asyncio.create_task(
        _ingestion_loop(settings.ingestion_interval_seconds)
    )
    logger.info(
        "Ingestion scheduler started (interval=%ds)", settings.ingestion_interval_seconds
    )

    yield

    scheduler_task.cancel()
    try:
        await scheduler_task
    except asyncio.CancelledError:
        pass

    await dispose_engine()
    logger.info("Shutdown complete")


app = FastAPI(title="ingestion-service", lifespan=lifespan)

app.include_router(health_router)
app.include_router(locations_router)
app.include_router(observations_router)
