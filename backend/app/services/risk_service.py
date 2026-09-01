"""
Rule-based, transparent risk summary — explicitly a prototype, not a trained
risk model. Combines the soil health score with weather signals using fixed
thresholds documented inline.
"""

from __future__ import annotations

Risk = str  # "LOW" | "MEDIUM" | "HIGH"


def _weather_risk(temperature_c: float, rainfall_mm: float, humidity_pct: float) -> Risk:
    flags = 0
    if temperature_c > 38 or temperature_c < 8:
        flags += 1
    if rainfall_mm > 8 or rainfall_mm == 0:
        flags += 1
    if humidity_pct > 90 or humidity_pct < 25:
        flags += 1
    if flags == 0:
        return "LOW"
    if flags == 1:
        return "MEDIUM"
    return "HIGH"


def _soil_risk(soil_score: int | None) -> Risk:
    if soil_score is None:
        return "MEDIUM"
    if soil_score >= 70:
        return "LOW"
    if soil_score >= 45:
        return "MEDIUM"
    return "HIGH"


def _water_risk(irrigation_available: bool, rainfall_mm: float) -> Risk:
    if irrigation_available:
        return "LOW"
    return "LOW" if rainfall_mm >= 2 else "HIGH"


def _disease_risk(humidity_pct: float) -> Risk:
    # High humidity is a well-known general driver of fungal disease pressure.
    if humidity_pct >= 85:
        return "HIGH"
    if humidity_pct >= 65:
        return "MEDIUM"
    return "LOW"


_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}


def compute_risk(
    *,
    temperature_c: float,
    rainfall_mm: float,
    humidity_pct: float,
    soil_score: int | None,
    irrigation_available: bool,
) -> dict:
    weather = _weather_risk(temperature_c, rainfall_mm, humidity_pct)
    soil = _soil_risk(soil_score)
    water = _water_risk(irrigation_available, rainfall_mm)
    disease = _disease_risk(humidity_pct)

    overall_score = max(_ORDER[weather], _ORDER[soil], _ORDER[water], _ORDER[disease])
    overall = {v: k for k, v in _ORDER.items()}[overall_score]

    notes = []
    if weather != "LOW":
        notes.append("Weather conditions are outside the typical comfortable range.")
    if soil != "LOW":
        notes.append("Soil health score suggests nutrient management may be needed.")
    if water != "LOW":
        notes.append("No irrigation available and rainfall is low — water stress risk.")
    if disease != "LOW":
        notes.append("High humidity increases general fungal disease pressure.")
    if not notes:
        notes.append("No elevated risk signals detected from current soil and weather data.")

    return {
        "overall": overall,
        "weather_risk": weather,
        "soil_risk": soil,
        "water_risk": water,
        "disease_risk": disease,
        "notes": notes,
        "is_prototype": True,
    }
