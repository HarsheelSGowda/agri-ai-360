from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_farmer, get_current_user
from app.database.session import get_db
from app.models.disease import DiseaseDetection
from app.models.farm import Farm
from app.models.user import Farmer, User
from app.schemas.disease_schema import DiseaseDiagnosisResponse, DiseaseOptionsResponse
from app.services.disease_service import (
    DiseaseModelUnavailableError,
    InvalidImageError,
    diagnose,
    load_disease_metrics,
    supported_crops,
)

router = APIRouter(tags=["disease"])

MAX_UPLOAD_BYTES = 8 * 1024 * 1024  # 8 MB


@router.get("/predict/disease/options", response_model=DiseaseOptionsResponse)
def disease_options(_: User = Depends(get_current_user)):
    metrics = load_disease_metrics()
    if not metrics:
        return DiseaseOptionsResponse(supported_crops=[], classes=[], active_model=None, active_model_accuracy=None, dataset_records=0)

    return DiseaseOptionsResponse(
        supported_crops=supported_crops(),
        classes=metrics.get("classes", []),
        active_model=metrics.get("active_model"),
        active_model_accuracy=metrics.get("active_model_accuracy"),
        dataset_records=metrics.get("dataset_records", 0),
    )


@router.post("/predict/disease", response_model=DiseaseDiagnosisResponse)
async def predict_disease(
    image: UploadFile = File(...),
    farm_id: int | None = Form(default=None),
    db: Session = Depends(get_db),
    farmer: Farmer = Depends(get_current_farmer),
):
    if image.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Upload a JPEG, PNG or WebP image.")

    contents = await image.read()
    if not contents:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image is too large (max 8 MB).")

    try:
        result = diagnose(contents)
    except InvalidImageError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except DiseaseModelUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    saved = False
    if farm_id is not None:
        farm = db.query(Farm).filter(Farm.id == farm_id, Farm.farmer_id == farmer.id).first()
        if farm:
            top = result["top_prediction"]
            db.add(
                DiseaseDetection(
                    farm_id=farm.id,
                    crop=top["crop"],
                    condition=top["condition"],
                    is_healthy=top["is_healthy"],
                    probability=top["probability"],
                    model_used=result["model_used"],
                )
            )
            db.commit()
            saved = True

    return DiseaseDiagnosisResponse(**result, saved_to_history=saved)
