from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.fertilizer_schema import FertilizerOptionsResponse, FertilizerRecommendationInput, FertilizerRecommendationResponse
from app.services.fertilizer_service import VALID_GROWTH_STAGES, recommend_fertilizer

router = APIRouter(tags=["fertilizer"])


@router.get("/fertilizer/options", response_model=FertilizerOptionsResponse)
def fertilizer_options(_: User = Depends(get_current_user)):
    return FertilizerOptionsResponse(growth_stages=VALID_GROWTH_STAGES)


@router.post("/fertilizer/recommend", response_model=FertilizerRecommendationResponse)
def recommend(payload: FertilizerRecommendationInput, _: User = Depends(get_current_user)):
    result = recommend_fertilizer(
        crop=payload.crop,
        nitrogen=payload.nitrogen,
        phosphorus=payload.phosphorus,
        potassium=payload.potassium,
        ph=payload.ph,
        growth_stage=payload.growth_stage,
        organic_carbon=payload.organic_carbon,
        moisture=payload.moisture,
        farm_area_acres=payload.farm_area_acres,
    )
    return FertilizerRecommendationResponse(**result)
