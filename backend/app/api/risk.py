from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_farmer
from app.database.session import get_db
from app.models.farm import Farm
from app.models.soil import SoilRecord
from app.models.user import Farmer
from app.services.risk_service import compute_risk
from app.services.soil_health import compute_soil_health
from app.services.weather_provider import get_weather_provider

router = APIRouter(tags=["risk"])


@router.get("/risk")
def get_risk(farm_id: int, db: Session = Depends(get_db), farmer: Farmer = Depends(get_current_farmer)):
    farm = db.query(Farm).filter(Farm.id == farm_id, Farm.farmer_id == farmer.id).first()
    if not farm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found")

    soil = db.query(SoilRecord).filter(SoilRecord.farm_id == farm_id).order_by(SoilRecord.created_at.desc()).first()
    soil_score = None
    if soil:
        soil_score = compute_soil_health(soil.nitrogen, soil.phosphorus, soil.potassium, soil.ph)["score"]

    weather = get_weather_provider().get_current(farm.location)

    return compute_risk(
        temperature_c=weather["temperature_c"],
        rainfall_mm=weather["rainfall_mm"],
        humidity_pct=weather["humidity_pct"],
        soil_score=soil_score,
        irrigation_available=farm.irrigation_available,
    )
