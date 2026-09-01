from pydantic import BaseModel, Field


class YieldPredictionInput(BaseModel):
    crop: str = Field(min_length=1, max_length=100)
    state: str = Field(min_length=1, max_length=100)
    season: str = Field(min_length=1, max_length=50)
    farm_id: int | None = None


class YieldPredictionResponse(BaseModel):
    supported: bool
    crop: str
    mapped_crop: str | None = None
    state: str | None = None
    season: str | None = None
    predicted_yield_tonnes_per_ha: float | None = None
    predicted_yield_quintal_per_acre: float | None = None
    model_used: str | None = None
    r2_score: float | None = None
    mae: float | None = None
    reason: str | None = None


class YieldOptionsResponse(BaseModel):
    states: list[str]
    seasons: list[str]
    supported_crops: list[str]
    dataset_records: int
    active_model: str | None
    active_model_r2: float | None
