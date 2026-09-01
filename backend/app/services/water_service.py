"""
Water Requirement (Phase 2).

Estimates crop water requirement (mm/day) and net irrigation need, combining:

  1. The FAO Blaney-Criddle reference evapotranspiration formula, exactly as
     published: ETo = p x (0.46 x Tmean + 8) [mm/day], where p = "mean daily
     percentage of annual daytime hours" for the given latitude and month
     (FAO "Crop Water Needs" Training Manual No. 3, Table 4). p is looked up
     from ml/water_requirement/build_p_reference.py's output (extracted
     directly from the primary source, not retyped from memory), with
     linear interpolation between the table's 5-degree latitude bands.

     NOTE: an earlier version of this module tried to derive p from solar
     astronomy (day length / 12) instead of using FAO's table. That produced
     ETo ~23 mm/day for a real July/Nagpur input, ~3-4x too high against the
     ~5-6 mm/day the real table gives for the same input - a good example of
     why a self-derived "should be equivalent" substitute isn't a safe stand-
     in for the actual cited source. It was replaced with the verified table.

  2. Real FAO-56 Table 12 crop coefficients (Kc_mid), extracted directly
     from the primary source by ml/water_requirement/build_kc_reference.py.

  3. The USDA Soil Conservation Service effective-rainfall formula (real,
     citable), applied to whatever rainfall figure the caller supplies.

This is a planning-level estimate (FAO's own documentation describes
Blaney-Criddle as "not very accurate; it provides a rough estimate... only"),
not a substitute for local agronomic advice - it has no soil-moisture,
irrigation-efficiency, or growth-stage model behind it (only the mid-season/
peak-demand Kc is used).
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.core.config import settings
from app.services.yield_service import HECTARES_PER_ACRE

# Approximate state-capital latitudes (degrees N) - used as a representative
# point per state since the app only collects free-text farm location, not
# GPS coordinates. Real geographic coordinates, not estimated.
STATE_LATITUDE: dict[str, float] = {
    "Andaman and Nicobar Island": 11.67,
    "Andhra Pradesh": 16.51,
    "Arunachal Pradesh": 27.10,
    "Assam": 26.14,
    "Bihar": 25.61,
    "Chandigarh": 30.73,
    "Chhattisgarh": 21.25,
    "Dadra and Nagar Haveli": 20.27,
    "Daman and Diu": 20.42,
    "Delhi": 28.61,
    "Goa": 15.49,
    "Gujarat": 23.22,
    "Haryana": 30.73,
    "Himachal Pradesh": 31.10,
    "Jammu and Kashmir": 34.08,
    "Jharkhand": 23.34,
    "Karnataka": 12.97,
    "Kerala": 8.52,
    "Ladakh": 34.15,
    "Madhya Pradesh": 23.26,
    "Maharashtra": 19.08,
    "Manipur": 24.82,
    "Meghalaya": 25.57,
    "Mizoram": 23.73,
    "Nagaland": 25.67,
    "Odisha": 20.30,
    "Puducherry": 11.94,
    "Punjab": 30.73,
    "Rajasthan": 26.91,
    "Sikkim": 27.34,
    "Tamil Nadu": 13.08,
    "Telangana": 17.39,
    "The Dadra And Nagar Haveli": 20.27,
    "Tripura": 23.84,
    "Uttar Pradesh": 26.85,
    "Uttarakhand": 30.32,
    "West Bengal": 22.57,
}

MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


class WaterDataUnavailableError(RuntimeError):
    pass


def _models_dir() -> Path:
    return settings.resolved_models_dir


@lru_cache
def load_kc_reference() -> dict | None:
    path = _models_dir() / "water_kc_reference.json"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


@lru_cache
def load_p_reference() -> dict | None:
    path = _models_dir() / "water_p_reference.json"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def supported_water_crops() -> list[str]:
    ref = load_kc_reference()
    return sorted(ref.keys()) if ref else []


def _lookup_p(latitude_deg: float, month_index: int) -> float:
    """Linearly interpolate FAO Table 4's p-value between its 5-degree
    latitude bands for the given month (0=Jan..11=Dec)."""
    p_table = load_p_reference()
    if not p_table:
        raise WaterDataUnavailableError("water_p_reference.json missing. Run ml/water_requirement/build_p_reference.py.")

    month = MONTH_NAMES[month_index]
    lat = max(0.0, min(60.0, abs(latitude_deg)))  # table covers 0-60N; India is fully within this range

    lower_band = int(lat // 5) * 5
    upper_band = min(60, lower_band + 5)
    if lower_band == upper_band:
        return p_table[str(lower_band)][month]

    p_lower = p_table[str(lower_band)][month]
    p_upper = p_table[str(upper_band)][month]
    fraction = (lat - lower_band) / (upper_band - lower_band)
    return p_lower + fraction * (p_upper - p_lower)


def reference_et0(temperature_c: float, latitude_deg: float, month_index: int) -> float:
    """FAO Blaney-Criddle ETo (mm/day): ETo = p x (0.46 x Tmean + 8)."""
    p = _lookup_p(latitude_deg, month_index)
    return p * (0.46 * temperature_c + 8)


def effective_rainfall(rainfall_mm: float) -> float:
    """USDA Soil Conservation Service effective rainfall formula."""
    if rainfall_mm <= 0:
        return 0.0
    if rainfall_mm <= 250:
        return rainfall_mm * (125 - 0.2 * rainfall_mm) / 125
    return 125 + 0.1 * rainfall_mm


def predict_water_requirement(
    crop: str,
    state: str,
    month_index: int,
    temperature_c: float,
    rainfall_mm: float,
    area_acres: float | None = None,
) -> dict:
    kc_ref = load_kc_reference()
    if not kc_ref:
        raise WaterDataUnavailableError(
            "Water Kc reference has not been built yet. Run ml/water_requirement/build_kc_reference.py."
        )

    crop_key = crop.lower()
    if crop_key not in kc_ref:
        return {
            "supported": False,
            "reason": f"No FAO-56 crop-coefficient data is available for '{crop}' — water requirement "
            f"currently covers: {', '.join(sorted(kc_ref.keys()))}.",
            "crop": crop,
        }

    if state not in STATE_LATITUDE:
        return {
            "supported": False,
            "reason": f"'{state}' is not a recognized state for this calculation.",
            "crop": crop,
        }

    kc_entry = kc_ref[crop_key]
    latitude = STATE_LATITUDE[state]
    p_value = _lookup_p(latitude, month_index)

    et0 = reference_et0(temperature_c, latitude, month_index)
    etc_mm_per_day = et0 * kc_entry["kc_mid"]

    eff_rainfall_mm_per_day = effective_rainfall(rainfall_mm)
    net_requirement_mm_per_day = max(0.0, etc_mm_per_day - eff_rainfall_mm_per_day)

    liters_per_acre_per_day = net_requirement_mm_per_day * 10 * 1000 / HECTARES_PER_ACRE

    result = {
        "supported": True,
        "crop": crop,
        "kc_mid": kc_entry["kc_mid"],
        "kc_category": kc_entry["category"],
        "kc_source_row": kc_entry["fao56_row"],
        "kc_note": kc_entry["note"],
        "state": state,
        "latitude_deg": latitude,
        "month": MONTH_NAMES[month_index],
        "p_value": round(p_value, 3),
        "reference_et0_mm_per_day": round(et0, 2),
        "crop_water_use_mm_per_day": round(etc_mm_per_day, 2),
        "effective_rainfall_mm_per_day": round(eff_rainfall_mm_per_day, 2),
        "net_irrigation_mm_per_day": round(net_requirement_mm_per_day, 2),
        "net_irrigation_liters_per_acre_per_day": round(liters_per_acre_per_day, 0),
        "net_irrigation_liters_total_per_day": None,
    }

    if area_acres is not None and area_acres > 0:
        result["net_irrigation_liters_total_per_day"] = round(liters_per_acre_per_day * area_acres, 0)

    return result
