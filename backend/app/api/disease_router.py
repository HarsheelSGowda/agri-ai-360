from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.api.deps import get_current_user
from app.models.user import User
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
async def predict_disease(image: UploadFile = File(...), _: User = Depends(get_current_user)):
    if image.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Upload a JPEG, PNG or WebP image.")

    contents = await image.read()
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image is too large (max 8 MB).")

    try:
        result = diagnose(contents)
    except InvalidImageError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except DiseaseModelUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    return DiseaseDiagnosisResponse(**result)
