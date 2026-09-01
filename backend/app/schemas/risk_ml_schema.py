from pydantic import BaseModel, Field


class YieldRiskInput(BaseModel):
    crop: str = Field(min_length=1, max_length=100)
    state: str = Field(min_length=1, max_length=100)
    season: str = Field(min_length=1, max_length=50)
    farm_id: int | None = None


class YieldRiskResponse(BaseModel):
    supported: bool
    crop: str
    mapped_crop: str | None = None
    state: str | None = None
    season: str | None = None
    risk_level: str | None = None
    probabilities: dict[str, float] | None = None
    model_used: str | None = None
    model_accuracy: float | None = None
    reason: str | None = None


class YieldRiskOptionsResponse(BaseModel):
    supported_crops: list[str]
    active_model: str | None
    active_model_accuracy: float | None
    dataset_records: int
