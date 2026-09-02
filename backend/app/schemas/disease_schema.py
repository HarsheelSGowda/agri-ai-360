from pydantic import BaseModel


class DiseasePrediction(BaseModel):
    crop: str
    condition: str
    is_healthy: bool
    probability: float


class DiseaseDiagnosisResponse(BaseModel):
    top_prediction: DiseasePrediction
    alternatives: list[DiseasePrediction]
    model_used: str
    model_accuracy: float
    supported_crops: list[str]


class DiseaseOptionsResponse(BaseModel):
    supported_crops: list[str]
    classes: list[str]
    active_model: str | None
    active_model_accuracy: float | None
    dataset_records: int
