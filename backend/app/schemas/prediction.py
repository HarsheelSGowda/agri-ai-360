from pydantic import BaseModel, Field


class CropPredictionInput(BaseModel):
    nitrogen: float = Field(ge=0, le=300)
    phosphorus: float = Field(ge=0, le=300)
    potassium: float = Field(ge=0, le=300)
    temperature: float = Field(ge=-10, le=55)
    humidity: float = Field(ge=0, le=100)
    ph: float = Field(ge=0, le=14)
    rainfall: float = Field(ge=0, le=5000)
    farm_id: int | None = None


class CropRankingItem(BaseModel):
    crop: str
    probability: float
    confidence: str


class TopCropsResponse(BaseModel):
    top_crops: list[CropRankingItem]
    model_used: str
    model_version: str
    input: dict


class ExplainRequest(CropPredictionInput):
    crop: str


class ShapContribution(BaseModel):
    feature: str
    value: float
    contribution: float


class ExplanationResponse(BaseModel):
    crop: str
    contributions: list[ShapContribution]
    base_value: float
    predicted_value: float
    narrative: str
    method: str = "shap"


class PredictionHistoryItem(BaseModel):
    id: int
    farm_id: int
    farm_name: str
    crop: str
    score: float
    created_at: str
    soil_summary: str
    weather_summary: str
