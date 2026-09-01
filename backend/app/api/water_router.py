from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.water_schema import WaterOptionsResponse, WaterRequirementInput, WaterRequirementResponse
from app.services.water_service import STATE_LATITUDE, WaterDataUnavailableError, predict_water_requirement, supported_water_crops

router = APIRouter(tags=["water"])


@router.get("/predict/water/options", response_model=WaterOptionsResponse)
def water_options(_: User = Depends(get_current_user)):
    return WaterOptionsResponse(supported_crops=supported_water_crops(), states=sorted(STATE_LATITUDE.keys()))


@router.post("/predict/water", response_model=WaterRequirementResponse)
def predict_water_endpoint(payload: WaterRequirementInput, _: User = Depends(get_current_user)):
    day = payload.date or date_type.today()
    month_index = day.month - 1  # 0=Jan..11=Dec, matches FAO Table 4 columns

    try:
        result = predict_water_requirement(
            payload.crop,
            payload.state,
            month_index,
            payload.temperature_c,
            payload.rainfall_mm,
            payload.area_acres,
        )
    except WaterDataUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    return WaterRequirementResponse(**result)
