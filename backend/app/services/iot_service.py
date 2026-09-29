"""
IoT sensor integration architecture (Phase 2E, Feature 10C).

Intended pipeline: Sensor -> API/MQTT gateway -> Backend (this service, via
POST /api/iot/readings) -> Database (SensorReading table) -> Dashboard.

Two things here are real, not simulated:
  1. record_reading() - a genuine ingestion path any real gateway/device could
     call today to persist a real reading (source="device").
  2. list_readings() - a genuine read path over whatever rows actually exist.

generate_demo_batch() is the ONLY simulated part, used because no physical
sensor is connected to this deployment yet. Every row it creates is tagged
source="demo_simulation" so the API/UI can label it clearly and it's never
confused with a real device feed.
"""

from __future__ import annotations

import hashlib
import time

from sqlalchemy.orm import Session

from app.models.sensor_reading import SensorReading

SENSOR_SPECS: dict[str, dict] = {
    "soil_moisture": {"unit": "%", "range": (15.0, 45.0)},
    "temperature": {"unit": "°C", "range": (18.0, 36.0)},
    "humidity": {"unit": "%", "range": (40.0, 90.0)},
    "ec": {"unit": "dS/m", "range": (0.2, 2.5)},
}


def record_reading(
    db: Session,
    farm_id: int,
    sensor_type: str,
    value: float,
    unit: str | None = None,
    source: str = "device",
) -> SensorReading:
    if sensor_type not in SENSOR_SPECS:
        raise ValueError(f"Unknown sensor_type '{sensor_type}'. Supported: {list(SENSOR_SPECS)}")
    reading = SensorReading(
        farm_id=farm_id,
        sensor_type=sensor_type,
        value=value,
        unit=unit or SENSOR_SPECS[sensor_type]["unit"],
        source=source,
    )
    db.add(reading)
    db.commit()
    db.refresh(reading)
    return reading


def list_readings(db: Session, farm_id: int, limit: int = 50) -> list[SensorReading]:
    return (
        db.query(SensorReading)
        .filter(SensorReading.farm_id == farm_id)
        .order_by(SensorReading.recorded_at.desc())
        .limit(limit)
        .all()
    )


def generate_demo_batch(db: Session, farm_id: int) -> list[SensorReading]:
    """One reading per sensor type, seeded from farm_id + current time so repeated
    clicks produce different (but always clearly-labeled) demo values."""
    seed = int(hashlib.sha256(f"{farm_id}-{time.time_ns()}".encode()).hexdigest(), 16)
    created: list[SensorReading] = []
    for i, (sensor_type, spec) in enumerate(SENSOR_SPECS.items()):
        low, high = spec["range"]
        frac = ((seed >> (i * 11)) % 1000) / 1000
        value = round(low + frac * (high - low), 1)
        reading = SensorReading(farm_id=farm_id, sensor_type=sensor_type, value=value, unit=spec["unit"], source="demo_simulation")
        db.add(reading)
        created.append(reading)
    db.commit()
    for r in created:
        db.refresh(r)
    return created
