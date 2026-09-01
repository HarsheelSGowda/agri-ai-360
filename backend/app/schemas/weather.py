from typing import Literal

from pydantic import BaseModel


class ForecastDay(BaseModel):
    day: str
    temp_c: float
    condition: str


class WeatherOut(BaseModel):
    temperature_c: float
    humidity_pct: float
    rainfall_mm: float
    wind_kmh: float
    condition: str
    forecast: list[ForecastDay]
    source: Literal["mock", "live"]
