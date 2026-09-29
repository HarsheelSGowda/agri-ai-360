"""
Tests for the live weather integration (Open-Meteo).

Covers: the existing mock provider (regression — must stay unchanged), the
WMO weather-code mapping, OpenMeteoWeatherProvider's parsing/error-handling
logic against a mocked HTTP transport (deterministic, no network dependency),
the safe fallback-to-mock wrapper, provider selection, and one real
live-network call that proves the integration actually works end-to-end
(skipped, not failed, if this environment has no network access).
"""

import httpx
import pytest

from app.core.config import settings
from app.services.weather_provider import (
    LiveWeatherFetchError,
    MockWeatherProvider,
    OpenMeteoWeatherProvider,
    WeatherProvider,
    _FallbackWeatherProvider,
    get_weather_provider,
    wmo_condition,
)


def test_wmo_condition_mapping_uses_documented_codes():
    assert wmo_condition(0) == "Clear Sky"
    assert "Rain" in wmo_condition(61)
    assert "Drizzle" in wmo_condition(51)
    assert "Snow" in wmo_condition(71)
    assert "Thunderstorm" in wmo_condition(95)
    assert wmo_condition(12345) == "Unknown"  # never invents a description for an unmapped code


def test_mock_provider_shape_unchanged():
    data = MockWeatherProvider().get_current("Nashik, Maharashtra")
    assert data["source"] == "mock"
    assert len(data["forecast"]) == 5
    assert set(data) == {"temperature_c", "humidity_pct", "rainfall_mm", "wind_kmh", "condition", "forecast", "source"}


GEOCODE_OK = {"results": [{"latitude": 19.99, "longitude": 73.79}]}
FORECAST_OK = {
    "current": {"temperature_2m": 28.8, "relative_humidity_2m": 62, "precipitation": 0.2, "weather_code": 53, "wind_speed_10m": 12.7},
    "daily": {
        "temperature_2m_max": [29.8, 29.8, 28.5, 28.1, 28.5, 29.2],
        "weather_code": [55, 51, 3, 3, 1, 3],
    },
}


def _mock_transport(geocode_json=None, forecast_json=None, geocode_status=200, forecast_status=200):
    def handler(request: httpx.Request) -> httpx.Response:
        if "geocoding-api" in str(request.url):
            return httpx.Response(geocode_status, json=geocode_json if geocode_json is not None else {"results": []})
        return httpx.Response(forecast_status, json=forecast_json if forecast_json is not None else {})

    return httpx.MockTransport(handler)


def test_open_meteo_provider_parses_a_real_shaped_response():
    client = httpx.Client(transport=_mock_transport(GEOCODE_OK, FORECAST_OK))
    provider = OpenMeteoWeatherProvider(client=client)
    data = provider.get_current("Nashik, Maharashtra")
    assert data["source"] == "live"
    assert data["temperature_c"] == 28.8
    assert data["humidity_pct"] == 62
    assert data["rainfall_mm"] == 0.2
    assert data["wind_kmh"] == 13
    assert data["condition"] == "Moderate Drizzle"
    assert len(data["forecast"]) == 5
    assert data["forecast"][0] == {"day": "Tomorrow", "temp_c": 29.8, "condition": "Light Drizzle"}


def test_open_meteo_provider_raises_when_location_not_found():
    client = httpx.Client(transport=_mock_transport(geocode_json={"results": []}))
    provider = OpenMeteoWeatherProvider(client=client)
    with pytest.raises(LiveWeatherFetchError):
        provider.get_current("Nowhereville")


def test_open_meteo_provider_raises_on_geocoding_http_error():
    client = httpx.Client(transport=_mock_transport(geocode_status=500))
    provider = OpenMeteoWeatherProvider(client=client)
    with pytest.raises(LiveWeatherFetchError):
        provider.get_current("Nashik")


def test_open_meteo_provider_raises_on_forecast_http_error():
    client = httpx.Client(transport=_mock_transport(GEOCODE_OK, forecast_status=503))
    provider = OpenMeteoWeatherProvider(client=client)
    with pytest.raises(LiveWeatherFetchError):
        provider.get_current("Nashik")


def test_open_meteo_provider_raises_on_malformed_response():
    client = httpx.Client(transport=_mock_transport(GEOCODE_OK, forecast_json={"unexpected": "shape"}))
    provider = OpenMeteoWeatherProvider(client=client)
    with pytest.raises(LiveWeatherFetchError):
        provider.get_current("Nashik")


class _AlwaysFailsProvider(WeatherProvider):
    def get_current(self, location: str) -> dict:
        raise LiveWeatherFetchError("simulated failure")


def test_fallback_provider_falls_back_to_mock_on_failure():
    wrapper = _FallbackWeatherProvider(_AlwaysFailsProvider(), MockWeatherProvider())
    data = wrapper.get_current("Nashik, Maharashtra")
    assert data["source"] == "mock"  # never claims to be live data when the live call failed


def test_fallback_provider_passes_through_live_data_on_success():
    client = httpx.Client(transport=_mock_transport(GEOCODE_OK, FORECAST_OK))
    wrapper = _FallbackWeatherProvider(OpenMeteoWeatherProvider(client=client), MockWeatherProvider())
    data = wrapper.get_current("Nashik, Maharashtra")
    assert data["source"] == "live"


def test_get_weather_provider_defaults_to_mock(monkeypatch):
    monkeypatch.setattr(settings, "weather_provider", "mock")
    assert isinstance(get_weather_provider(), MockWeatherProvider)


def test_get_weather_provider_unrecognized_value_falls_back_to_mock(monkeypatch):
    monkeypatch.setattr(settings, "weather_provider", "something-unrecognized")
    assert isinstance(get_weather_provider(), MockWeatherProvider)


def test_get_weather_provider_selects_open_meteo_when_configured(monkeypatch):
    monkeypatch.setattr(settings, "weather_provider", "open-meteo")
    assert isinstance(get_weather_provider(), _FallbackWeatherProvider)


def test_weather_endpoint_default_returns_mock(client, auth_headers):
    resp = client.get("/api/weather", params={"location": "Nashik, Maharashtra"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["source"] == "mock"


def test_weather_endpoint_with_open_meteo_configured_never_errors(client, auth_headers, monkeypatch):
    """With WEATHER_PROVIDER=open-meteo, the endpoint must return 200 with either
    real live data or a safe mock fallback - never a 500, regardless of this
    environment's network access."""
    monkeypatch.setattr(settings, "weather_provider", "open-meteo")
    resp = client.get("/api/weather", params={"location": "Nashik, Maharashtra"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["source"] in ("live", "mock")


def test_open_meteo_provider_live_network_smoke():
    """One real call to the live Open-Meteo API - proves the integration
    actually works end-to-end, not just against a mocked response. Skips
    (does not fail the suite) if this environment has no network access."""
    provider = OpenMeteoWeatherProvider()
    try:
        data = provider.get_current("Nashik, Maharashtra")
    except LiveWeatherFetchError as exc:
        pytest.skip(f"Live Open-Meteo API unreachable in this environment: {exc}")

    assert data["source"] == "live"
    assert -50 <= data["temperature_c"] <= 60
    assert 0 <= data["humidity_pct"] <= 100
    assert data["condition"] != "Unknown"
    assert len(data["forecast"]) == 5
