from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_farmer
from app.database.session import get_db
from app.models.farm import Farm
from app.models.prediction import CropPrediction, CropScore
from app.models.user import Farmer
from app.schemas.prediction import CropPredictionInput, ExplainRequest, ExplanationResponse, TopCropsResponse
from app.services.ml_service import ModelUnavailableError, explain_prediction, predict_top_k

router = APIRouter(tags=["prediction"])


@router.post("/predict/top-crops", response_model=TopCropsResponse)
@router.post("/predict/crop", response_model=TopCropsResponse)
def predict_top_crops(
    payload: CropPredictionInput,
    db: Session = Depends(get_db),
    farmer: Farmer = Depends(get_current_farmer),
):
    try:
        result = predict_top_k(payload.model_dump(exclude={"farm_id"}))
    except ModelUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    if payload.farm_id is not None:
        farm = db.query(Farm).filter(Farm.id == payload.farm_id, Farm.farmer_id == farmer.id).first()
        if farm:
            prediction = CropPrediction(
                farm_id=farm.id,
                input_json=payload.model_dump(exclude={"farm_id"}),
                top_crop=result["top_crops"][0]["crop"],
                top_score=result["top_crops"][0]["probability"],
            )
            db.add(prediction)
            db.flush()
            for rank, item in enumerate(result["top_crops"], start=1):
                db.add(CropScore(prediction_id=prediction.id, crop=item["crop"], probability=item["probability"], rank=rank))
            db.commit()

    return TopCropsResponse(**result, input=payload.model_dump(exclude={"farm_id"}))


@router.post("/explain/crop", response_model=ExplanationResponse)
def explain_crop(payload: ExplainRequest, farmer: Farmer = Depends(get_current_farmer)):
    try:
        result = explain_prediction(payload.model_dump(exclude={"farm_id", "crop"}), payload.crop)
    except ModelUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return ExplanationResponse(**result)
