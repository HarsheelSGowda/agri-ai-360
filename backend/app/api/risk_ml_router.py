from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.risk_ml_schema import YieldRiskInput, YieldRiskOptionsResponse, YieldRiskResponse
from app.services.risk_ml_service import (
    RiskModelUnavailableError,
    load_risk_metrics,
    predict_yield_risk,
    supported_risk_crops,
)

router = APIRouter(tags=["risk-ml"])


@router.get("/predict/yield-risk/options", response_model=YieldRiskOptionsResponse)
def yield_risk_options(_: User = Depends(get_current_user)):
    metrics = load_risk_metrics()
    if not metrics:
        return YieldRiskOptionsResponse(supported_crops=[], active_model=None, active_model_accuracy=None, dataset_records=0)

    return YieldRiskOptionsResponse(
        supported_crops=supported_risk_crops(),
        active_model=metrics.get("active_model"),
        active_model_accuracy=metrics.get("active_model_accuracy"),
        dataset_records=metrics.get("dataset_records", 0),
    )


@router.post("/predict/yield-risk", response_model=YieldRiskResponse)
def predict_yield_risk_endpoint(payload: YieldRiskInput, _: User = Depends(get_current_user)):
    try:
        result = predict_yield_risk(payload.crop, payload.state, payload.season)
    except RiskModelUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    return YieldRiskResponse(**result)
