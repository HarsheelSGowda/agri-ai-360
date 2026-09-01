from datetime import datetime

from pydantic import BaseModel, Field


class SoilCreate(BaseModel):
    nitrogen: float = Field(ge=0, le=300)
    phosphorus: float = Field(ge=0, le=300)
    potassium: float = Field(ge=0, le=300)
    ph: float = Field(ge=0, le=14)
    soil_type: str = Field(min_length=1, max_length=100)
    organic_carbon: float | None = Field(default=None, ge=0, le=100)
    moisture: float | None = Field(default=None, ge=0, le=100)
    electrical_conductivity: float | None = Field(default=None, ge=0, le=50)


class SoilHealthResult(BaseModel):
    score: int
    breakdown: dict[str, int]
    insights: list[str]


class SoilOut(BaseModel):
    id: int
    farm_id: int
    nitrogen: float
    phosphorus: float
    potassium: float
    ph: float
    soil_type: str
    organic_carbon: float | None
    moisture: float | None
    electrical_conductivity: float | None
    created_at: datetime
    health: SoilHealthResult

    model_config = {"from_attributes": True}
