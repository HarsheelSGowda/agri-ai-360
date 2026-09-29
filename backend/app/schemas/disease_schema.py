from pydantic import BaseModel


class DiseasePrediction(BaseModel):
    crop: str
    condition: str
    is_healthy: bool
    probability: float


class CareGuidance(BaseModel):
    pathogen_type: str | None
    pathogen: str | None
    severity: str
    recommended_actions: list[str]
    prevention: list[str]


class DiseaseDiagnosisResponse(BaseModel):
    top_prediction: DiseasePrediction
    alternatives: list[DiseasePrediction]
    care_guidance: CareGuidance
    model_used: str
    model_accuracy: float
    supported_crops: list[str]
    saved_to_history: bool = False


class DiseaseOptionsResponse(BaseModel):
    supported_crops: list[str]
    classes: list[str]
    active_model: str | None
    active_model_accuracy: float | None
    dataset_records: int


class DiseaseHistoryItem(BaseModel):
    id: int
    farm_id: int
    farm_name: str
    crop: str
    condition: str
    is_healthy: bool
    probability: float
    model_used: str
    created_at: str
