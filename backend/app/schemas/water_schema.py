from datetime import date as date_type

from pydantic import BaseModel, Field


class WaterRequirementInput(BaseModel):
    crop: str = Field(min_length=1, max_length=100)
    state: str = Field(min_length=1, max_length=100)
    temperature_c: float = Field(ge=-10, le=55)
    rainfall_mm: float = Field(ge=0, le=1000)
    date: date_type | None = None
    area_acres: float | None = Field(default=None, gt=0, le=100_000)
    farm_id: int | None = None


class WaterRequirementResponse(BaseModel):
    supported: bool
    crop: str
    kc_mid: float | None = None
    kc_category: str | None = None
    kc_source_row: str | None = None
    kc_note: str | None = None
    state: str | None = None
    latitude_deg: float | None = None
    month: str | None = None
    p_value: float | None = None
    reference_et0_mm_per_day: float | None = None
    crop_water_use_mm_per_day: float | None = None
    effective_rainfall_mm_per_day: float | None = None
    net_irrigation_mm_per_day: float | None = None
    net_irrigation_liters_per_acre_per_day: float | None = None
    net_irrigation_liters_total_per_day: float | None = None
    reason: str | None = None


class WaterOptionsResponse(BaseModel):
    supported_crops: list[str]
    states: list[str]
