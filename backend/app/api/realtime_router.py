from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_farmer
from app.database.session import get_db
from app.models.farm import Farm
from app.models.sensor_reading import SensorReading
from app.models.user import Farmer
from app.schemas.realtime_schema import (
    IoTIngestRequest,
    IoTReadingsResponse,
    SatelliteStatusResponse,
    SensorReadingOut,
)
from app.services import iot_service, satellite_service

router = APIRouter(tags=["realtime"])


def _owned_farm(db: Session, farm_id: int, farmer: Farmer) -> Farm:
    farm = db.query(Farm).filter(Farm.id == farm_id, Farm.farmer_id == farmer.id).first()
    if not farm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found")
    return farm


def _to_out(r: SensorReading) -> SensorReadingOut:
    return SensorReadingOut(
        id=r.id, farm_id=r.farm_id, sensor_type=r.sensor_type, value=r.value, unit=r.unit, source=r.source,
        recorded_at=r.recorded_at.isoformat(),
    )


@router.get("/satellite/status", response_model=SatelliteStatusResponse)
def satellite_status(farm_id: int, db: Session = Depends(get_db), farmer: Farmer = Depends(get_current_farmer)):
    farm = _owned_farm(db, farm_id, farmer)
    return SatelliteStatusResponse(**satellite_service.get_satellite_status(farm.location))


@router.get("/iot/readings", response_model=IoTReadingsResponse)
def iot_readings(farm_id: int, db: Session = Depends(get_db), farmer: Farmer = Depends(get_current_farmer)):
    farm = _owned_farm(db, farm_id, farmer)
    readings = iot_service.list_readings(db, farm.id)
    has_real = any(r.source != "demo_simulation" for r in readings)
    return IoTReadingsResponse(farm_id=farm.id, readings=[_to_out(r) for r in readings], has_real_device_data=has_real)


@router.post("/iot/demo/seed", response_model=IoTReadingsResponse)
def iot_seed_demo(farm_id: int, db: Session = Depends(get_db), farmer: Farmer = Depends(get_current_farmer)):
    farm = _owned_farm(db, farm_id, farmer)
    iot_service.generate_demo_batch(db, farm.id)
    readings = iot_service.list_readings(db, farm.id)
    return IoTReadingsResponse(farm_id=farm.id, readings=[_to_out(r) for r in readings], has_real_device_data=False)


@router.post("/iot/readings", response_model=SensorReadingOut, status_code=status.HTTP_201_CREATED)
def ingest_reading(payload: IoTIngestRequest, db: Session = Depends(get_db), farmer: Farmer = Depends(get_current_farmer)):
    """
    Real ingestion endpoint any physical sensor gateway (e.g. an MQTT bridge)
    could call today. Rows created here are tagged source="device", distinct
    from the source="demo_simulation" rows /iot/demo/seed creates.
    """
    _owned_farm(db, payload.farm_id, farmer)
    try:
        reading = iot_service.record_reading(db, payload.farm_id, payload.sensor_type, payload.value, payload.unit, source="device")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _to_out(reading)
