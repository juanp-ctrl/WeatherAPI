from datetime import datetime, timezone
from uuid import uuid4

import pytest

from src.application.use_cases.process_observations import ProcessObservationsUseCase
from src.domain.entities.processing_rule import ProcessingRule
from src.domain.ports.ingestion_client import RawObservationData
from .fakes import (
    FakeAlertRepository,
    FakeIngestionClient,
    FakeProcessedObservationRepository,
    FakeProcessingRuleRepository,
    FakeWatermarkRepository,
)


def _raw_obs(ingested_at=None, temperature_c=20.0) -> RawObservationData:
    return RawObservationData(
        id=uuid4(),
        location_id=uuid4(),
        observed_at=datetime(2026, 6, 30, 12, 0, tzinfo=timezone.utc),
        ingested_at=ingested_at or datetime(2026, 6, 30, 12, 5, tzinfo=timezone.utc),
        temperature_c=temperature_c,
        humidity_pct=50.0,
        wind_speed_kmh=5.0,
        precipitation_mm=0.0,
        weather_code=1,
    )


def _high_temp_rule() -> ProcessingRule:
    return ProcessingRule(
        id=uuid4(),
        metric="temperature_c",
        operator=">",
        threshold=35.0,
        severity="HIGH",
        alert_type="HIGH_TEMPERATURE",
        message_template="Temperature {value}°C exceeds {threshold}°C",
    )


async def test_process_creates_processed_observation():
    obs_repo = FakeProcessedObservationRepository()
    alert_repo = FakeAlertRepository()
    rule_repo = FakeProcessingRuleRepository()
    watermark_repo = FakeWatermarkRepository()
    ingestion_client = FakeIngestionClient([_raw_obs()])

    uc = ProcessObservationsUseCase(
        ingestion_client, obs_repo, alert_repo, rule_repo, watermark_repo
    )
    result = await uc.execute()

    assert result.observations_processed == 1
    assert await obs_repo.count() == 1


async def test_process_generates_alert_when_rule_fires():
    obs_repo = FakeProcessedObservationRepository()
    alert_repo = FakeAlertRepository()
    rule_repo = FakeProcessingRuleRepository([_high_temp_rule()])
    watermark_repo = FakeWatermarkRepository()
    ingestion_client = FakeIngestionClient([_raw_obs(temperature_c=40.0)])

    uc = ProcessObservationsUseCase(
        ingestion_client, obs_repo, alert_repo, rule_repo, watermark_repo
    )
    result = await uc.execute()

    assert result.alerts_generated == 1
    alerts = await alert_repo.list()
    assert len(alerts) == 1
    assert alerts[0].alert_type == "HIGH_TEMPERATURE"
    assert alerts[0].severity == "HIGH"


async def test_process_no_alert_when_rule_not_fired():
    obs_repo = FakeProcessedObservationRepository()
    alert_repo = FakeAlertRepository()
    rule_repo = FakeProcessingRuleRepository([_high_temp_rule()])
    watermark_repo = FakeWatermarkRepository()
    ingestion_client = FakeIngestionClient([_raw_obs(temperature_c=20.0)])

    uc = ProcessObservationsUseCase(
        ingestion_client, obs_repo, alert_repo, rule_repo, watermark_repo
    )
    result = await uc.execute()

    assert result.alerts_generated == 0
    assert await alert_repo.count() == 0


async def test_process_updates_watermark():
    obs_repo = FakeProcessedObservationRepository()
    alert_repo = FakeAlertRepository()
    rule_repo = FakeProcessingRuleRepository()
    watermark_repo = FakeWatermarkRepository()
    ingested_ts = datetime(2026, 6, 30, 13, 0, tzinfo=timezone.utc)
    ingestion_client = FakeIngestionClient([_raw_obs(ingested_at=ingested_ts)])

    uc = ProcessObservationsUseCase(
        ingestion_client, obs_repo, alert_repo, rule_repo, watermark_repo
    )
    await uc.execute()

    wm = await watermark_repo.get("ingestion")
    assert wm is not None
    assert wm.last_ingested_at == ingested_ts


async def test_process_uses_watermark_on_second_run():
    obs_repo = FakeProcessedObservationRepository()
    alert_repo = FakeAlertRepository()
    rule_repo = FakeProcessingRuleRepository()
    watermark_repo = FakeWatermarkRepository()

    early_ts = datetime(2026, 6, 30, 10, 0, tzinfo=timezone.utc)
    late_ts = datetime(2026, 6, 30, 14, 0, tzinfo=timezone.utc)
    obs_old = _raw_obs(ingested_at=early_ts)
    obs_new = _raw_obs(ingested_at=late_ts)

    ingestion_client = FakeIngestionClient([obs_old, obs_new])

    uc = ProcessObservationsUseCase(
        ingestion_client, obs_repo, alert_repo, rule_repo, watermark_repo
    )

    await uc.execute()
    first_count = await obs_repo.count()

    ingestion_client._observations = [obs_new]
    result2 = await uc.execute()

    assert result2.observations_processed == 0


async def test_process_no_observations_returns_zero():
    obs_repo = FakeProcessedObservationRepository()
    alert_repo = FakeAlertRepository()
    rule_repo = FakeProcessingRuleRepository()
    watermark_repo = FakeWatermarkRepository()
    ingestion_client = FakeIngestionClient([])

    uc = ProcessObservationsUseCase(
        ingestion_client, obs_repo, alert_repo, rule_repo, watermark_repo
    )
    result = await uc.execute()

    assert result.observations_processed == 0
    assert result.alerts_generated == 0
