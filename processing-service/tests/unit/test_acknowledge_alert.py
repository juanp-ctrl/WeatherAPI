from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.application.use_cases.acknowledge_alert import AcknowledgeAlertUseCase
from src.domain.entities.alert import Alert
from .fakes import FakeAlertRepository


async def test_acknowledge_alert_sets_flag():
    repo = FakeAlertRepository()
    alert = Alert(
        processed_observation_id=uuid4(),
        rule_id=uuid4(),
        alert_type="HIGH_TEMPERATURE",
        severity="HIGH",
        message="Temperature exceeded threshold",
        acknowledged=False,
    )
    await repo.save(alert)

    uc = AcknowledgeAlertUseCase(repo)
    result = await uc.execute(alert.id)

    assert result.acknowledged is True


async def test_acknowledge_alert_not_found():
    repo = FakeAlertRepository()
    uc = AcknowledgeAlertUseCase(repo)

    with pytest.raises(HTTPException) as exc_info:
        await uc.execute(uuid4())

    assert exc_info.value.status_code == 404
