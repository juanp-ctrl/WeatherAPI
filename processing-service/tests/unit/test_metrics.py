import pytest

from src.domain.services.metrics import (
    compute_feels_like,
    compute_heat_index,
    compute_severity_score,
    compute_wind_chill,
)


class TestHeatIndex:
    def test_returns_none_when_temp_too_low(self):
        assert compute_heat_index(25.0, 80.0) is None

    def test_returns_none_when_humidity_too_low(self):
        assert compute_heat_index(35.0, 30.0) is None

    def test_returns_none_for_none_inputs(self):
        assert compute_heat_index(None, 80.0) is None
        assert compute_heat_index(35.0, None) is None

    def test_returns_value_for_hot_humid_conditions(self):
        result = compute_heat_index(35.0, 70.0)
        assert result is not None
        assert result > 35.0

    def test_heat_index_higher_than_temp(self):
        result = compute_heat_index(32.0, 80.0)
        assert result is not None
        assert result > 32.0


class TestWindChill:
    def test_returns_none_when_temp_too_high(self):
        assert compute_wind_chill(15.0, 30.0) is None

    def test_returns_none_when_wind_too_low(self):
        assert compute_wind_chill(0.0, 2.0) is None

    def test_returns_none_for_none_inputs(self):
        assert compute_wind_chill(None, 20.0) is None
        assert compute_wind_chill(-5.0, None) is None

    def test_returns_value_for_cold_windy(self):
        result = compute_wind_chill(-10.0, 30.0)
        assert result is not None
        assert result < -10.0

    def test_wind_chill_lower_than_temp(self):
        result = compute_wind_chill(5.0, 20.0)
        assert result is not None
        assert result < 5.0


class TestFeelsLike:
    def test_uses_heat_index_when_available(self):
        result = compute_feels_like(30.0, heat_index_c=38.0, wind_chill_c=None)
        assert result == 38.0

    def test_uses_wind_chill_when_available(self):
        result = compute_feels_like(-5.0, heat_index_c=None, wind_chill_c=-12.0)
        assert result == -12.0

    def test_falls_back_to_temperature(self):
        result = compute_feels_like(20.0, heat_index_c=None, wind_chill_c=None)
        assert result == 20.0

    def test_prefers_heat_index_over_wind_chill(self):
        result = compute_feels_like(5.0, heat_index_c=38.0, wind_chill_c=-2.0)
        assert result == 38.0


class TestSeverityScore:
    def test_no_alerts_returns_zero(self):
        assert compute_severity_score([]) == 0

    def test_critical_returns_ten(self):
        assert compute_severity_score(["CRITICAL"]) == 10

    def test_high_returns_seven(self):
        assert compute_severity_score(["HIGH"]) == 7

    def test_returns_max_of_multiple(self):
        assert compute_severity_score(["LOW", "HIGH", "MEDIUM"]) == 7

    def test_mixed_case_handled(self):
        assert compute_severity_score(["critical"]) == 10
