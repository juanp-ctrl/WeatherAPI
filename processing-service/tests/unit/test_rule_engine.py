import pytest
from uuid import uuid4

from src.domain.entities.processing_rule import ProcessingRule
from src.domain.services.rule_engine import RuleMatch, evaluate_rules


def _rule(metric, operator, threshold, severity="HIGH", active=True) -> ProcessingRule:
    return ProcessingRule(
        id=uuid4(),
        metric=metric,
        operator=operator,
        threshold=threshold,
        severity=severity,
        alert_type="TEST_ALERT",
        message_template="Value {value} exceeded {threshold}",
        is_active=active,
    )


def test_rule_fires_on_greater_than():
    rules = [_rule("temperature_c", ">", 35.0)]
    obs = {"temperature_c": 36.0}
    matches = evaluate_rules(obs, rules)
    assert len(matches) == 1
    assert matches[0].alert_type == "TEST_ALERT"


def test_rule_does_not_fire_when_below_threshold():
    rules = [_rule("temperature_c", ">", 35.0)]
    obs = {"temperature_c": 30.0}
    matches = evaluate_rules(obs, rules)
    assert len(matches) == 0


def test_inactive_rule_ignored():
    rules = [_rule("temperature_c", ">", 35.0, active=False)]
    obs = {"temperature_c": 40.0}
    matches = evaluate_rules(obs, rules)
    assert len(matches) == 0


def test_rule_fires_on_less_than():
    rules = [_rule("temperature_c", "<", 0.0, severity="CRITICAL")]
    obs = {"temperature_c": -5.0}
    matches = evaluate_rules(obs, rules)
    assert len(matches) == 1
    assert matches[0].severity == "CRITICAL"


def test_rule_fires_on_greater_or_equal():
    rules = [_rule("humidity_pct", ">=", 90.0)]
    obs = {"humidity_pct": 90.0}
    matches = evaluate_rules(obs, rules)
    assert len(matches) == 1


def test_missing_metric_skipped():
    rules = [_rule("temperature_c", ">", 35.0)]
    obs = {"humidity_pct": 80.0}
    matches = evaluate_rules(obs, rules)
    assert len(matches) == 0


def test_none_metric_value_skipped():
    rules = [_rule("temperature_c", ">", 35.0)]
    obs = {"temperature_c": None}
    matches = evaluate_rules(obs, rules)
    assert len(matches) == 0


def test_message_template_substitution():
    rules = [_rule("temperature_c", ">", 35.0)]
    obs = {"temperature_c": 38.5}
    matches = evaluate_rules(obs, rules)
    assert "38.5" in matches[0].message
    assert "35.0" in matches[0].message


def test_multiple_rules_multiple_matches():
    rules = [
        _rule("temperature_c", ">", 35.0),
        _rule("humidity_pct", ">", 80.0),
    ]
    obs = {"temperature_c": 40.0, "humidity_pct": 85.0}
    matches = evaluate_rules(obs, rules)
    assert len(matches) == 2


def test_equals_operator():
    rules = [_rule("weather_code", "==", 95.0)]
    obs = {"weather_code": 95}
    matches = evaluate_rules(obs, rules)
    assert len(matches) == 1
