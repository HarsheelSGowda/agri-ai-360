"""
Personalized farmer notifications (Phase 5, new priority feature).

generate_for_farm() derives notifications from the same real data every other
module already computes (soil health, weather, risk, latest disease diagnosis,
market price trend) - it does not invent facts or randomize content. Each
notification's message is built from the actual current values for that farm.

Deduplication: before inserting, skip a notification whose exact title+message
was already created for this farmer within the lookback window, so re-running
generation (e.g. on every dashboard load) doesn't spam duplicates.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.disease import DiseaseDetection
from app.models.farm import Farm
from app.models.notification import Notification
from app.models.prediction import CropPrediction
from app.models.soil import SoilRecord
from app.models.user import Farmer
from app.services import market_price_service
from app.services.risk_service import compute_risk
from app.services.soil_health import compute_soil_health
from app.services.weather_provider import get_weather_provider

DEDUP_WINDOW = timedelta(hours=12)


def _guess_state(location: str, states: list[str]) -> str | None:
    lower = location.lower()
    for state in states:
        if state.lower() in lower:
            return state
    return None


def _already_notified(db: Session, farmer_id: int, title: str, message: str) -> bool:
    cutoff = datetime.now(timezone.utc) - DEDUP_WINDOW
    return (
        db.query(Notification)
        .filter(
            Notification.farmer_id == farmer_id,
            Notification.title == title,
            Notification.message == message,
            Notification.created_at >= cutoff,
        )
        .first()
        is not None
    )


def _add(db: Session, farmer_id: int, farm_id: int | None, category: str, priority: str, title: str, message: str, created: list) -> None:
    if _already_notified(db, farmer_id, title, message):
        return
    note = Notification(farmer_id=farmer_id, farm_id=farm_id, category=category, priority=priority, title=title, message=message)
    db.add(note)
    created.append(note)


def generate_for_farm(db: Session, farm: Farm, farmer: Farmer) -> list[Notification]:
    created: list[Notification] = []
    name = farmer.name.split()[0] if farmer.name else "Farmer"

    soil = db.query(SoilRecord).filter(SoilRecord.farm_id == farm.id).order_by(SoilRecord.created_at.desc()).first()
    soil_health = compute_soil_health(soil.nitrogen, soil.phosphorus, soil.potassium, soil.ph) if soil else None

    weather = get_weather_provider().get_current(farm.location)

    if soil_health and soil_health["score"] < 65:
        worst_insight = soil_health["insights"][0]
        _add(
            db,
            farmer.id,
            farm.id,
            "FERTILIZER",
            "MEDIUM" if soil_health["score"] >= 45 else "HIGH",
            f"Soil health needs attention on {farm.name}",
            f"Good day {name}. {worst_insight} Check the Fertilizer Advisor for guidance.",
            created,
        )

    if any("rain" in f["condition"].lower() for f in weather["forecast"][:2]):
        _add(
            db,
            farmer.id,
            farm.id,
            "WEATHER",
            "MEDIUM",
            f"Rain expected near {farm.location}",
            f"Rainfall is expected soon near {farm.location}. Consider checking irrigation requirements before it arrives.",
            created,
        )

    risk = compute_risk(
        temperature_c=weather["temperature_c"],
        rainfall_mm=weather["rainfall_mm"],
        humidity_pct=weather["humidity_pct"],
        soil_score=soil_health["score"] if soil_health else None,
        irrigation_available=farm.irrigation_available,
    )
    if risk["overall"] in ("MEDIUM", "HIGH"):
        _add(
            db,
            farmer.id,
            farm.id,
            "RISK",
            risk["overall"],
            f"{risk['overall'].title()} risk flagged on {farm.name}",
            f"{name}, current conditions put {farm.name} at {risk['overall']} overall risk. {risk['notes'][0]}",
            created,
        )

    latest_disease = (
        db.query(DiseaseDetection)
        .filter(DiseaseDetection.farm_id == farm.id, DiseaseDetection.is_healthy.is_(False))
        .order_by(DiseaseDetection.created_at.desc())
        .first()
    )
    if latest_disease and latest_disease.created_at >= datetime.now(timezone.utc) - timedelta(days=7):
        _add(
            db,
            farmer.id,
            farm.id,
            "DISEASE",
            "HIGH",
            f"Possible disease detected on {farm.name}",
            f"Your uploaded leaf image for {latest_disease.crop} indicates possible {latest_disease.condition} "
            f"({latest_disease.probability * 100:.0f}% confidence). Please inspect affected plants.",
            created,
        )

    latest_prediction = (
        db.query(CropPrediction).filter(CropPrediction.farm_id == farm.id).order_by(CropPrediction.created_at.desc()).first()
    )
    if latest_prediction:
        crop = latest_prediction.top_crop
        states = market_price_service.list_states(db, crop)
        state = _guess_state(farm.location, states)
        if state:
            trend = market_price_service.get_trend(db, crop, state, days=10)
            if trend["found"] and trend["change_pct"] is not None and abs(trend["change_pct"]) >= 5:
                direction = "increased" if trend["change_pct"] > 0 else "decreased"
                _add(
                    db,
                    farmer.id,
                    farm.id,
                    "MARKET",
                    "MEDIUM",
                    f"{crop.title()} prices {direction} in {state}",
                    f"{crop.title()} market prices have {direction} by {abs(trend['change_pct'])}% recently in {state} "
                    f"(historical Agmarknet data). Check Market Prices for details.",
                    created,
                )

    if created:
        db.commit()
        for note in created:
            db.refresh(note)
    return created
