"""
Fertilizer recommendation (Phase 4, new priority feature).

Rule-based decision support, NOT a calibrated dosage prescription. Nutrient
status reuses the exact same general agronomic reference bands already used
and documented in app/services/soil_health.py (single source of truth - no
duplicated/drifting thresholds), plus a general organic-carbon reference band
and general, well-established growth-stage application-timing guidance.

This intentionally never outputs a kg/acre dosage number: exact application
rates depend on a certified local soil-test report, crop variety, target
yield and regional agricultural-university guidelines this system doesn't
have access to. Every response carries an explicit disclaimer to that effect.
"""

from __future__ import annotations

from app.services.soil_health import THRESHOLDS

# Soil organic carbon (%) reference bands - standard Indian soil-testing
# convention (Low / Medium / High), same style of reference-range documentation
# as THRESHOLDS in soil_health.py.
SOC_LOW = 0.5
SOC_MEDIUM = 0.75

FERTILIZER_CATEGORY = {
    "nitrogen": "Nitrogenous fertilizer (e.g. Urea, Ammonium Sulphate)",
    "phosphorus": "Phosphatic fertilizer (e.g. DAP, Single Super Phosphate)",
    "potassium": "Potassic fertilizer (e.g. Muriate of Potash, Sulphate of Potash)",
}

NUTRIENT_LABEL = {"nitrogen": "Nitrogen (N)", "phosphorus": "Phosphorus (P)", "potassium": "Potassium (K)"}

GROWTH_STAGE_GUIDANCE = {
    "seedling": "Apply phosphorus and potassium as a basal dose at planting/transplanting. Avoid heavy nitrogen at this stage - young roots can be damaged by high salt concentration.",
    "vegetative": "This is generally the main window for split nitrogen top-dressing to support leaf and stem growth.",
    "flowering": "Avoid excess nitrogen now - it can delay maturity and increase lodging risk in cereals. Potassium supports flowering and fruit-set if it's deficient.",
    "fruiting": "Potassium demand is typically highest during fruit/grain filling. Avoid further nitrogen unless a visible deficiency is confirmed.",
    "maturity": "Avoid further fertilizer application close to harvest - it rarely helps yield at this point and can affect produce quality.",
}

VALID_GROWTH_STAGES = list(GROWTH_STAGE_GUIDANCE.keys())


def _nutrient_status(nutrient: str, value: float) -> str:
    _, low, high, _ = THRESHOLDS[nutrient]
    if value < low:
        return "DEFICIENT"
    if value > high:
        return "EXCESS"
    return "ADEQUATE"


def _ph_guidance(ph: float) -> str | None:
    if ph < 5.5:
        return (
            f"Soil pH ({ph}) is strongly acidic. Phosphorus and some micronutrients become less available to "
            "plants at low pH; consider agricultural lime after a certified soil test confirms the need."
        )
    if ph > 8.5:
        return (
            f"Soil pH ({ph}) is strongly alkaline. Iron, zinc and manganese availability typically drops at high pH; "
            "consider gypsum or organic matter addition per local agricultural extension guidance."
        )
    return None


def _organic_carbon_guidance(organic_carbon: float | None) -> str | None:
    if organic_carbon is None:
        return None
    if organic_carbon < SOC_LOW:
        return (
            f"Organic carbon ({organic_carbon}%) is low. Consider adding farmyard manure, compost, or crop residue "
            "to improve soil structure and long-term nutrient retention - this doesn't replace mineral fertilizer "
            "but reduces how much of it is needed over time."
        )
    if organic_carbon < SOC_MEDIUM:
        return f"Organic carbon ({organic_carbon}%) is moderate. Maintaining residue incorporation will help sustain it."
    return f"Organic carbon ({organic_carbon}%) is in a healthy range - maintain current organic matter practices."


def recommend_fertilizer(
    crop: str,
    nitrogen: float,
    phosphorus: float,
    potassium: float,
    ph: float,
    growth_stage: str,
    organic_carbon: float | None = None,
    moisture: float | None = None,
    farm_area_acres: float | None = None,
) -> dict:
    nutrients = {"nitrogen": nitrogen, "phosphorus": phosphorus, "potassium": potassium}
    deficiencies = []
    warnings: list[str] = []

    for key, value in nutrients.items():
        status = _nutrient_status(key, value)
        _, low, high, _ = THRESHOLDS[key]
        entry = {
            "nutrient": NUTRIENT_LABEL[key],
            "current_value": value,
            "optimal_range": f"{low}-{high}",
            "status": status,
            "recommended_category": FERTILIZER_CATEGORY[key] if status == "DEFICIENT" else None,
        }
        deficiencies.append(entry)
        if status == "EXCESS":
            warnings.append(
                f"{NUTRIENT_LABEL[key]} is already above the general optimal range ({value} vs {low}-{high}) - "
                "adding more risks nutrient imbalance, crop lodging/burn, or unnecessary runoff. Skip this nutrient "
                "unless a recent soil test says otherwise."
            )

    ph_warning = _ph_guidance(ph)
    if ph_warning:
        warnings.append(ph_warning)

    if moisture is not None and moisture < 15:
        warnings.append(
            f"Soil moisture ({moisture}%) is low - fertilizer (especially nitrogen) is poorly absorbed in dry soil "
            "and can scorch roots. Consider irrigating before or shortly after application."
        )

    stage_key = growth_stage.lower().strip()
    application_timing = GROWTH_STAGE_GUIDANCE.get(
        stage_key, "Growth stage not recognized - general guidance: apply phosphorus/potassium as basal dose, split nitrogen across vegetative growth."
    )

    return {
        "crop": crop,
        "growth_stage": growth_stage,
        "farm_area_acres": farm_area_acres,
        "deficiencies": deficiencies,
        "organic_matter_guidance": _organic_carbon_guidance(organic_carbon),
        "application_timing": application_timing,
        "warnings": warnings,
        "disclaimer": (
            "This is decision support based on general agronomic reference ranges, not a calibrated dosage "
            "prescription. Exact fertilizer quantities depend on a certified local soil-test report, crop variety, "
            "target yield and your state agricultural university's package of practices - validate before applying."
        ),
    }
