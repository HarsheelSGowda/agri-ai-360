from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_farmer
from app.database.session import get_db
from app.models.disease import DiseaseDetection
from app.models.farm import Farm
from app.models.prediction import CropPrediction
from app.models.user import Farmer
from app.schemas.disease_schema import DiseaseHistoryItem
from app.schemas.prediction import PredictionHistoryItem

router = APIRouter(tags=["history"])


@router.get("/history", response_model=list[PredictionHistoryItem])
def get_history(farm_id: int | None = None, db: Session = Depends(get_db), farmer: Farmer = Depends(get_current_farmer)):
    query = (
        db.query(CropPrediction)
        .join(Farm, Farm.id == CropPrediction.farm_id)
        .filter(Farm.farmer_id == farmer.id)
        .options(joinedload(CropPrediction.farm))
        .order_by(CropPrediction.created_at.desc())
    )
    if farm_id is not None:
        query = query.filter(CropPrediction.farm_id == farm_id)

    items = query.limit(100).all()
    out = []
    for item in items:
        inp = item.input_json
        out.append(
            PredictionHistoryItem(
                id=item.id,
                farm_id=item.farm_id,
                farm_name=item.farm.name,
                crop=item.top_crop,
                score=item.top_score,
                created_at=item.created_at.isoformat(),
                soil_summary=f"N:{inp.get('nitrogen')} P:{inp.get('phosphorus')} K:{inp.get('potassium')} pH:{inp.get('ph')}",
                weather_summary=f"{inp.get('temperature')}°C, {inp.get('humidity')}% humidity, {inp.get('rainfall')}mm rainfall",
            )
        )
    return out


@router.get("/history/disease", response_model=list[DiseaseHistoryItem])
def get_disease_history(farm_id: int | None = None, db: Session = Depends(get_db), farmer: Farmer = Depends(get_current_farmer)):
    query = (
        db.query(DiseaseDetection)
        .join(Farm, Farm.id == DiseaseDetection.farm_id)
        .filter(Farm.farmer_id == farmer.id)
        .options(joinedload(DiseaseDetection.farm))
        .order_by(DiseaseDetection.created_at.desc())
    )
    if farm_id is not None:
        query = query.filter(DiseaseDetection.farm_id == farm_id)

    items = query.limit(100).all()
    return [
        DiseaseHistoryItem(
            id=item.id,
            farm_id=item.farm_id,
            farm_name=item.farm.name,
            crop=item.crop,
            condition=item.condition,
            is_healthy=item.is_healthy,
            probability=item.probability,
            model_used=item.model_used,
            created_at=item.created_at.isoformat(),
        )
        for item in items
    ]
