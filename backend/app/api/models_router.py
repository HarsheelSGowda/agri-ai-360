from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.model import ModelMetrics, ModelPerformanceResponse
from app.services.ml_service import load_metrics

router = APIRouter(tags=["models"])

ALGORITHMS = ["random_forest", "gradient_boosting", "xgboost", "svm"]
DISPLAY_NAMES = {
    "random_forest": "Random Forest",
    "gradient_boosting": "Gradient Boosting",
    "xgboost": "XGBoost",
    "svm": "SVM",
}


@router.get("/models")
def list_models(_: User = Depends(get_current_user)):
    metrics = load_metrics()
    if not metrics:
        return {"models": [], "active_model": None}
    return {
        "models": list(metrics.get("models", {}).keys()),
        "active_model": metrics.get("active_model"),
        "trained_at": metrics.get("trained_at"),
    }


@router.get("/models/performance", response_model=ModelPerformanceResponse)
def model_performance(_: User = Depends(get_current_user)):
    metrics = load_metrics()

    model_rows: list[ModelMetrics] = []
    for algo in ALGORITHMS:
        entry = (metrics or {}).get("models", {}).get(algo)
        if entry:
            model_rows.append(
                ModelMetrics(
                    algorithm=DISPLAY_NAMES[algo],
                    status="trained",
                    accuracy=entry["accuracy"],
                    precision=entry["precision"],
                    recall=entry["recall"],
                    f1_score=entry["f1_score"],
                    trained_at=metrics.get("trained_at"),
                )
            )
        else:
            model_rows.append(
                ModelMetrics(
                    algorithm=DISPLAY_NAMES[algo],
                    status="not_evaluated",
                    accuracy=None,
                    precision=None,
                    recall=None,
                    f1_score=None,
                    trained_at=None,
                )
            )

    active = (metrics or {}).get("active_model", "")
    active_entry = (metrics or {}).get("models", {}).get(active, {})
    feature_importance = None
    if active_entry.get("feature_importance"):
        feature_importance = [
            {"feature": k, "importance": v} for k, v in sorted(active_entry["feature_importance"].items(), key=lambda kv: -kv[1])
        ]

    confusion_matrix = None
    if active_entry.get("confusion_matrix"):
        confusion_matrix = {"labels": active_entry["labels"], "matrix": active_entry["confusion_matrix"]}

    return ModelPerformanceResponse(
        models=model_rows,
        active_model=DISPLAY_NAMES.get(active, active or "Not trained"),
        dataset_records=(metrics or {}).get("dataset_records", 0),
        dataset_source=(metrics or {}).get("dataset_source", "Not documented"),
        feature_importance=feature_importance,
        confusion_matrix=confusion_matrix,
    )
