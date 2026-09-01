from pydantic import BaseModel, Field


class ProfitPredictionInput(BaseModel):
    crop: str = Field(min_length=1, max_length=100)
    state: str = Field(min_length=1, max_length=100)
    season: str = Field(min_length=1, max_length=50)
    cost_per_acre: float = Field(ge=0, le=1_000_000, description="Farmer-supplied estimated input cost, Rs. per acre")
    area_acres: float | None = Field(default=None, gt=0, le=100_000)
    farm_id: int | None = None


class ProfitPredictionResponse(BaseModel):
    supported: bool
    crop: str
    mapped_crop: str | None = None
    state: str | None = None
    season: str | None = None
    yield_tonnes_per_ha: float | None = None
    price_rs_per_quintal: float | None = None
    price_source: str | None = None
    cost_per_acre: float | None = None
    revenue_per_acre: float | None = None
    profit_per_acre: float | None = None
    revenue_per_ha: float | None = None
    profit_per_ha: float | None = None
    margin_pct: float | None = None
    total_farm_profit: float | None = None
    reason: str | None = None


class ProfitOptionsResponse(BaseModel):
    supported_crops: list[str]
    price_year: str
