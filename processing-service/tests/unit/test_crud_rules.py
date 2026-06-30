from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.application.dtos.rule_dto import RuleCreateDTO, RuleUpdateDTO
from src.application.use_cases.crud_rules import (
    CreateRuleUseCase,
    DeleteRuleUseCase,
    GetRuleUseCase,
    ListRulesUseCase,
    UpdateRuleUseCase,
)
from .fakes import FakeProcessingRuleRepository


def _create_dto(**kwargs) -> RuleCreateDTO:
    defaults = {
        "metric": "temperature_c",
        "operator": ">",
        "threshold": 35.0,
        "severity": "HIGH",
        "alert_type": "HIGH_TEMP",
        "message_template": "Temp {value} > {threshold}",
    }
    defaults.update(kwargs)
    return RuleCreateDTO(**defaults)


async def test_create_rule():
    repo = FakeProcessingRuleRepository()
    uc = CreateRuleUseCase(repo)
    result = await uc.execute(_create_dto())
    assert result.metric == "temperature_c"
    assert result.id is not None


async def test_get_rule_found():
    repo = FakeProcessingRuleRepository()
    uc_create = CreateRuleUseCase(repo)
    created = await uc_create.execute(_create_dto())

    uc_get = GetRuleUseCase(repo)
    result = await uc_get.execute(created.id)
    assert result.id == created.id


async def test_get_rule_not_found():
    repo = FakeProcessingRuleRepository()
    uc = GetRuleUseCase(repo)
    with pytest.raises(HTTPException) as exc_info:
        await uc.execute(uuid4())
    assert exc_info.value.status_code == 404


async def test_list_rules():
    repo = FakeProcessingRuleRepository()
    uc_create = CreateRuleUseCase(repo)
    await uc_create.execute(_create_dto())
    await uc_create.execute(_create_dto(metric="humidity_pct"))

    uc_list = ListRulesUseCase(repo)
    rules = await uc_list.execute()
    assert len(rules) == 2


async def test_update_rule():
    repo = FakeProcessingRuleRepository()
    uc_create = CreateRuleUseCase(repo)
    created = await uc_create.execute(_create_dto(threshold=35.0))

    uc_update = UpdateRuleUseCase(repo)
    updated = await uc_update.execute(created.id, RuleUpdateDTO(threshold=40.0))
    assert updated.threshold == 40.0


async def test_delete_rule():
    repo = FakeProcessingRuleRepository()
    uc_create = CreateRuleUseCase(repo)
    created = await uc_create.execute(_create_dto())

    uc_delete = DeleteRuleUseCase(repo)
    await uc_delete.execute(created.id)

    uc_list = ListRulesUseCase(repo)
    rules = await uc_list.execute()
    assert len(rules) == 0


async def test_delete_rule_not_found():
    repo = FakeProcessingRuleRepository()
    uc = DeleteRuleUseCase(repo)
    with pytest.raises(HTTPException) as exc_info:
        await uc.execute(uuid4())
    assert exc_info.value.status_code == 404
