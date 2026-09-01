from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.profit_schema import ProfitOptionsResponse, ProfitPredictionInput, ProfitPredictionResponse
from app.services.profit_service import ProfitDataUnavailableError, predict_profit, supported_profit_crops

router = APIRouter(tags=["profit"])


@router.get("/predict/profit/options", response_model=ProfitOptionsResponse)
def profit_options(_: User = Depends(get_current_user)):
    return ProfitOptionsResponse(supported_crops=supported_profit_crops(), price_year="2016")


@router.post("/predict/profit", response_model=ProfitPredictionResponse)
def predict_profit_endpoint(payload: ProfitPredictionInput, _: User = Depends(get_current_user)):
    try:
        result = predict_profit(
            payload.crop,
            payload.state,
            payload.season,
            payload.cost_per_acre,
            payload.area_acres,
        )
    except ProfitDataUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    return ProfitPredictionResponse(**result)
