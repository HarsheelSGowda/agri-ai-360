"""
Weather provider abstraction.

WeatherProvider defines the interface the rest of the app depends on.
MockWeatherProvider is a clearly-labeled deterministic dev/demo provider — no
external API key required. When a real key is configured (WEATHER_API_KEY +
WEATHER_PROVIDER=openweathermap, for example), a LiveWeatherProvider implementing
the same interface can be swapped in via get_weather_provider() without touching
any caller.
"""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod

from app.core.config import settings

FORECAST_DAYS = ["Tomorrow", "Day 2", "Day 3", "Day 4", "Day 5"]
CONDITIONS = ["Clear Sky", "Partly Cloudy", "Cloudy", "Light Rain", "Sunny"]


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


def get_weather_provider() -> WeatherProvider:
    if settings.weather_provider == "mock" or not settings.weather_api_key:
        return MockWeatherProvider()
    # Placeholder for a future real-API implementation (e.g. OpenWeatherMap),
    # kept out of the MVP per the "don't fabricate a live integration" rule.
    return MockWeatherProvider()
