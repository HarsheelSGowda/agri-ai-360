from pydantic import BaseModel


class ModelMetrics(BaseModel):
    algorithm: str
    status: str
    accuracy: float | None
    precision: float | None
    recall: float | None
    f1_score: float | None
    trained_at: str | None


class ConfusionMatrixOut(BaseModel):
    labels: list[str]
    matrix: list[list[int]]


class ModelPerformanceResponse(BaseModel):
    models: list[ModelMetrics]
    active_model: str
    dataset_records: int
    dataset_source: str
    feature_importance: list[dict] | None
    confusion_matrix: ConfusionMatrixOut | None
