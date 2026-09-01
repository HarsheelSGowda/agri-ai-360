from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.yield_schema import YieldOptionsResponse, YieldPredictionInput, YieldPredictionResponse
from app.services.yield_service import (
    YieldModelUnavailableError,
    load_yield_metrics,
    predict_yield,
    supported_recommendation_crops,
)

router = APIRouter(tags=["yield"])


@router.get("/predict/yield/options", response_model=YieldOptionsResponse)
def yield_options(_: User = Depends(get_current_user)):
    metrics = load_yield_metrics()
    if not metrics:
        return YieldOptionsResponse(states=[], seasons=[], supported_crops=[], dataset_records=0, active_model=None, active_model_r2=None)

    return YieldOptionsResponse(
        states=metrics.get("supported_states", []),
        seasons=metrics.get("supported_seasons", []),
        supported_crops=supported_recommendation_crops(),
        dataset_records=metrics.get("dataset_records", 0),
        active_model=metrics.get("active_model"),
        active_model_r2=metrics.get("active_model_r2"),
    )


@router.post("/predict/yield", response_model=YieldPredictionResponse)
def predict_yield_endpoint(payload: YieldPredictionInput, _: User = Depends(get_current_user)):
    try:
        result = predict_yield(payload.crop, payload.state, payload.season)
    except YieldModelUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    return YieldPredictionResponse(**result)
