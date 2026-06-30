from __future__ import annotations

"""Pure domain functions for computing derived weather metrics."""


def compute_heat_index(temp_c: float | None, humidity_pct: float | None) -> float | None:
    """Rothfusz regression formula. Applicable when temp > 27°C and humidity > 40%."""
    if temp_c is None or humidity_pct is None:
        return None
    if temp_c <= 27.0 or humidity_pct <= 40.0:
        return None
    t = temp_c * 9.0 / 5.0 + 32.0
    rh = humidity_pct
    hi_f = (
        -42.379
        + 2.04901523 * t
        + 10.14333127 * rh
        - 0.22475541 * t * rh
        - 0.00683783 * t * t
        - 0.05481717 * rh * rh
        + 0.00122874 * t * t * rh
        + 0.00085282 * t * rh * rh
        - 0.00000199 * t * t * rh * rh
    )
    return (hi_f - 32.0) * 5.0 / 9.0


def compute_wind_chill(temp_c: float | None, wind_speed_kmh: float | None) -> float | None:
    """North American Wind Chill Index. Applicable when temp < 10°C and wind > 4.8 km/h."""
    if temp_c is None or wind_speed_kmh is None:
        return None
    if temp_c >= 10.0 or wind_speed_kmh <= 4.8:
        return None
    v016 = wind_speed_kmh ** 0.16
    return 13.12 + 0.6215 * temp_c - 11.37 * v016 + 0.3965 * temp_c * v016


def compute_feels_like(
    temp_c: float | None,
    heat_index_c: float | None,
    wind_chill_c: float | None,
) -> float | None:
    """Return heat index when hot, wind chill when cold, otherwise raw temperature."""
    if heat_index_c is not None:
        return heat_index_c
    if wind_chill_c is not None:
        return wind_chill_c
    return temp_c


_SEVERITY_SCORE: dict[str, int] = {
    "CRITICAL": 10,
    "HIGH": 7,
    "MEDIUM": 5,
    "LOW": 2,
}


def compute_severity_score(severities: list[str]) -> int:
    """Return the highest severity score across a list of alert severities."""
    if not severities:
        return 0
    return max(_SEVERITY_SCORE.get(s.upper(), 0) for s in severities)
