from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_farmer
from app.database.session import get_db
from app.models.farm import Farm
from app.models.soil import SoilRecord
from app.models.user import Farmer
from app.schemas.farm import FarmCreate, FarmOut
from app.schemas.soil import SoilCreate, SoilOut
from app.services.soil_health import compute_soil_health

router = APIRouter(tags=["farms"])


def _get_owned_farm(db: Session, farm_id: int, farmer: Farmer) -> Farm:
    farm = db.query(Farm).filter(Farm.id == farm_id, Farm.farmer_id == farmer.id).first()
    if not farm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found")
    return farm


@router.post("/farms", response_model=FarmOut, status_code=status.HTTP_201_CREATED)
def create_farm(payload: FarmCreate, db: Session = Depends(get_db), farmer: Farmer = Depends(get_current_farmer)):
    farm = Farm(farmer_id=farmer.id, **payload.model_dump())
    db.add(farm)
    db.commit()
    db.refresh(farm)
    return farm


@router.get("/farms", response_model=list[FarmOut])
def list_farms(db: Session = Depends(get_db), farmer: Farmer = Depends(get_current_farmer)):
    return db.query(Farm).filter(Farm.farmer_id == farmer.id).order_by(Farm.created_at.desc()).all()


@router.get("/farms/{farm_id}", response_model=FarmOut)
def get_farm(farm_id: int, db: Session = Depends(get_db), farmer: Farmer = Depends(get_current_farmer)):
    return _get_owned_farm(db, farm_id, farmer)


@router.post("/farms/{farm_id}/soil", response_model=SoilOut, status_code=status.HTTP_201_CREATED)
def submit_soil(
    farm_id: int,
    payload: SoilCreate,
    db: Session = Depends(get_db),
    farmer: Farmer = Depends(get_current_farmer),
):
    _get_owned_farm(db, farm_id, farmer)

    record = SoilRecord(farm_id=farm_id, **payload.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)

    health = compute_soil_health(record.nitrogen, record.phosphorus, record.potassium, record.ph)
    return SoilOut.model_validate({**record.__dict__, "health": health})


@router.get("/farms/{farm_id}/soil", response_model=SoilOut | None)
def get_latest_soil(farm_id: int, db: Session = Depends(get_db), farmer: Farmer = Depends(get_current_farmer)):
    _get_owned_farm(db, farm_id, farmer)

    record = (
        db.query(SoilRecord).filter(SoilRecord.farm_id == farm_id).order_by(SoilRecord.created_at.desc()).first()
    )
    if not record:
        return None

    health = compute_soil_health(record.nitrogen, record.phosphorus, record.potassium, record.ph)
    return SoilOut.model_validate({**record.__dict__, "health": health})
