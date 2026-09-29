"""
Weather provider abstraction.

WeatherProvider defines the interface the rest of the app depends on.
MockWeatherProvider is a clearly-labeled deterministic dev/demo provider — no
external API key required.

OpenMeteoWeatherProvider is a real, live implementation using open-meteo.com
(free, no API key required for this project's usage level). It is opt-in via
WEATHER_PROVIDER=open-meteo in .env — the default stays "mock" so existing
behavior is unchanged unless a developer explicitly switches it on.
get_weather_provider() wraps it in _FallbackWeatherProvider so a network
failure never breaks a caller — it transparently falls back to mock data
(clearly tagged source="mock") rather than raising.
"""

from __future__ import annotations

import hashlib
import logging
from abc import ABC, abstractmethod

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

FORECAST_DAYS = ["Tomorrow", "Day 2", "Day 3", "Day 4", "Day 5"]
CONDITIONS = ["Clear Sky", "Partly Cloudy", "Cloudy", "Light Rain", "Sunny"]

# Real WMO "weather code" (WW) interpretation table, as documented by Open-Meteo
# (https://open-meteo.com/en/docs) — not invented. Individual codes within a
# documented range are given distinct, more specific text.
WMO_CONDITIONS: dict[int, str] = {
    0: "Clear Sky",
    1: "Mainly Clear",
    2: "Partly Cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing Rime Fog",
    51: "Light Drizzle",
    53: "Moderate Drizzle",
    55: "Dense Drizzle",
    56: "Light Freezing Drizzle",
    57: "Dense Freezing Drizzle",
    61: "Slight Rain",
    63: "Moderate Rain",
    65: "Heavy Rain",
    66: "Light Freezing Rain",
    67: "Heavy Freezing Rain",
    71: "Slight Snow Fall",
    73: "Moderate Snow Fall",
    75: "Heavy Snow Fall",
    77: "Snow Grains",
    80: "Slight Rain Showers",
    81: "Moderate Rain Showers",
    82: "Violent Rain Showers",
    85: "Slight Snow Showers",
    86: "Heavy Snow Showers",
    95: "Thunderstorm",
    96: "Thunderstorm With Slight Hail",
    99: "Thunderstorm With Heavy Hail",
}


def wmo_condition(code: int) -> str:
    return WMO_CONDITIONS.get(code, "Unknown")


class WeatherProvider(ABC):
    @abstractmethod
    def get_current(self, location: str) -> dict:
        raise NotImplementedError


class MockWeatherProvider(WeatherProvider):
    """Deterministic, seeded-by-location mock data — clearly not a live API."""

    def get_current(self, location: str) -> dict:
        seed = int(hashlib.sha256(location.lower().strip().encode()).hexdigest(), 16)

        temperature_c = 20 + (seed % 150) / 10  # 20.0 - 34.9
        humidity_pct = 45 + (seed // 150) % 45  # 45 - 89
        rainfall_mm = round(((seed // 10000) % 120) / 10, 1)  # 0 - 11.9
        wind_kmh = 4 + (seed // 100000) % 22  # 4 - 25
        condition = CONDITIONS[seed % len(CONDITIONS)]

        forecast = []
        for i, day in enumerate(FORECAST_DAYS):
            day_seed = seed + i * 97
            forecast.append(
                {
                    "day": day,
                    "temp_c": round(18 + (day_seed % 160) / 10, 1),
                    "condition": CONDITIONS[day_seed % len(CONDITIONS)],
                }
            )

        return {
            "temperature_c": round(temperature_c, 1),
            "humidity_pct": humidity_pct,
            "rainfall_mm": rainfall_mm,
            "wind_kmh": wind_kmh,
            "condition": condition,
            "forecast": forecast,
            "source": "mock",
        }


class LiveWeatherFetchError(RuntimeError):
    """Raised when a live provider can't produce real data (network, geocoding, bad response)."""


class OpenMeteoWeatherProvider(WeatherProvider):
    """
    Real, live weather via open-meteo.com — free, no API key required for this
    project's usage level. Two real HTTP calls per request: geocode the location
    string to lat/lon, then fetch current conditions + a 5-day daily forecast.

    Never returns invented data: any failure (network, timeout, location not
    found, unexpected response shape) raises LiveWeatherFetchError instead of
    guessing — callers should use get_weather_provider(), which wraps this in a
    safe fallback to the mock provider rather than letting a request fail.
    """

    GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
    FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
    TIMEOUT_SECONDS = 6.0

    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client

    def _get_client(self) -> httpx.Client:
        return self._client or httpx.Client(timeout=self.TIMEOUT_SECONDS)

    def _geocode(self, client: httpx.Client, location: str) -> tuple[float, float]:
        # The location string is typically "City, State" (e.g. "Nashik, Maharashtra") —
        # geocoding works best on just the city/place name, so use the first segment.
        place = location.split(",")[0].strip() or location
        try:
            resp = client.get(self.GEOCODE_URL, params={"name": place, "count": 1, "language": "en", "format": "json"})
            resp.raise_for_status()
            data = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise LiveWeatherFetchError(f"Geocoding request failed for '{place}': {exc}") from exc

        results = data.get("results") or []
        if not results:
            raise LiveWeatherFetchError(f"No geocoding match found for location '{place}'.")
        return float(results[0]["latitude"]), float(results[0]["longitude"])

    def get_current(self, location: str) -> dict:
        client = self._get_client()
        owns_client = self._client is None
        try:
            lat, lon = self._geocode(client, location)
            try:
                resp = client.get(
                    self.FORECAST_URL,
                    params={
                        "latitude": lat,
                        "longitude": lon,
                        "current": "temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m",
                        "daily": "temperature_2m_max,weather_code",
                        "timezone": "auto",
                        "forecast_days": 6,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                current = data["current"]
                daily = data["daily"]
            except (httpx.HTTPError, ValueError, KeyError) as exc:
                raise LiveWeatherFetchError(f"Forecast request failed for '{location}': {exc}") from exc

            forecast = []
            # daily[0] is today; the next 5 entries are the forecast days.
            for i, day in enumerate(FORECAST_DAYS):
                idx = i + 1
                forecast.append(
                    {
                        "day": day,
                        "temp_c": round(float(daily["temperature_2m_max"][idx]), 1),
                        "condition": wmo_condition(int(daily["weather_code"][idx])),
                    }
                )

            return {
                "temperature_c": round(float(current["temperature_2m"]), 1),
                "humidity_pct": round(float(current["relative_humidity_2m"])),
                "rainfall_mm": round(float(current["precipitation"]), 1),
                "wind_kmh": round(float(current["wind_speed_10m"])),
                "condition": wmo_condition(int(current["weather_code"])),
                "forecast": forecast,
                "source": "live",
            }
        except (IndexError, TypeError) as exc:
            raise LiveWeatherFetchError(f"Unexpected response shape from Open-Meteo for '{location}': {exc}") from exc
        finally:
            if owns_client:
                client.close()


class _FallbackWeatherProvider(WeatherProvider):
    """Tries a primary provider first; falls back to a secondary on any failure
    rather than letting a network hiccup break the /weather endpoint (or the
    dashboard/notifications/assistant modules that depend on it)."""

    def __init__(self, primary: WeatherProvider, fallback: WeatherProvider) -> None:
        self._primary = primary
        self._fallback = fallback

    def get_current(self, location: str) -> dict:
        try:
            return self._primary.get_current(location)
        except Exception as exc:  # noqa: BLE001 - any live-provider failure should fall back, not 500
            logger.warning("Live weather provider failed for '%s', falling back to mock: %s", location, exc)
            return self._fallback.get_current(location)


def get_weather_provider() -> WeatherProvider:
    if settings.weather_provider == "open-meteo":
        return _FallbackWeatherProvider(OpenMeteoWeatherProvider(), MockWeatherProvider())
    # Default "mock" (or any unrecognized value) — unchanged existing behavior.
    return MockWeatherProvider()
