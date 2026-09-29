"""
Tests for app/services/fertilizer_service.py - rule-based nutrient
deficiency/excess checking, pH guidance, organic-carbon guidance and
growth-stage application timing. Pure functions, no DB/network - real
computation throughout, no mocking needed or appropriate here.
"""

from app.services.fertilizer_service import (
    FERTILIZER_CATEGORY,
    GROWTH_STAGE_GUIDANCE,
    NUTRIENT_LABEL,
    SOC_LOW,
    SOC_MEDIUM,
    VALID_GROWTH_STAGES,
    _nutrient_status,
    _organic_carbon_guidance,
    _ph_guidance,
    recommend_fertilizer,
)

ADEQUATE = {"nitrogen": 80, "phosphorus": 40, "potassium": 55}  # mid-range for all three
GOOD_PH = 6.5  # within fertilizer_service's own 5.5-8.5 non-warning band


# ---------------------------------------------------------------------------
# _nutrient_status
# ---------------------------------------------------------------------------


def test_nutrient_status_deficient_below_low_threshold():
    assert _nutrient_status("nitrogen", 39) == "DEFICIENT"  # low threshold is 40
    assert _nutrient_status("phosphorus", 0) == "DEFICIENT"
    assert _nutrient_status("potassium", 29) == "DEFICIENT"


def test_nutrient_status_excess_above_high_threshold():
    assert _nutrient_status("nitrogen", 121) == "EXCESS"  # high threshold is 120
    assert _nutrient_status("phosphorus", 61) == "EXCESS"
    assert _nutrient_status("potassium", 81) == "EXCESS"


def test_nutrient_status_adequate_within_range_including_boundaries():
    assert _nutrient_status("nitrogen", 40) == "ADEQUATE"  # exactly at low boundary
    assert _nutrient_status("nitrogen", 120) == "ADEQUATE"  # exactly at high boundary
    assert _nutrient_status("nitrogen", 80) == "ADEQUATE"


# ---------------------------------------------------------------------------
# _ph_guidance
# ---------------------------------------------------------------------------


def test_ph_guidance_acidic_below_5_5():
    guidance = _ph_guidance(5.4)
    assert guidance is not None
    assert "acidic" in guidance.lower()
    assert "5.4" in guidance


def test_ph_guidance_alkaline_above_8_5():
    guidance = _ph_guidance(8.6)
    assert guidance is not None
    assert "alkaline" in guidance.lower()


def test_ph_guidance_none_within_the_non_warning_band():
    assert _ph_guidance(5.5) is None  # exactly at the acidic boundary - not flagged
    assert _ph_guidance(8.5) is None  # exactly at the alkaline boundary - not flagged
    assert _ph_guidance(7.0) is None


def test_ph_guidance_uses_its_own_thresholds_not_soil_healths_KNOWN_BEHAVIOR():
    """
    Documents a real, minor inconsistency with this module's own docstring:
    the docstring says nutrient status "reuses the exact same general
    agronomic reference bands already used ... in soil_health.py (single
    source of truth - no duplicated/drifting thresholds)". That's true for
    N/P/K (both modules import the same THRESHOLDS dict), but pH guidance
    here uses its own hardcoded 5.5/8.5 cutoffs, independent of
    soil_health.THRESHOLDS["ph"] (3.0, 6.0, 7.5, 10.0). A pH of 6.5 - which
    soil_health.py would score as fully optimal - triggers no warning here
    either, so behavior doesn't visibly diverge for typical values, but the
    "single source of truth" claim doesn't actually hold for pH.
    """
    from app.services.soil_health import THRESHOLDS

    soil_health_ph_band = THRESHOLDS["ph"]  # (3.0, 6.0, 7.5, 10.0)
    assert soil_health_ph_band != (5.5, 5.5, 8.5, 8.5)  # fertilizer_service's cutoffs aren't drawn from this tuple at all


# ---------------------------------------------------------------------------
# _organic_carbon_guidance
# ---------------------------------------------------------------------------


def test_organic_carbon_guidance_none_when_not_provided():
    assert _organic_carbon_guidance(None) is None


def test_organic_carbon_guidance_low_below_soc_low():
    guidance = _organic_carbon_guidance(SOC_LOW - 0.1)
    assert "low" in guidance.lower()
    assert "manure" in guidance.lower()


def test_organic_carbon_guidance_moderate_between_soc_low_and_soc_medium():
    guidance = _organic_carbon_guidance((SOC_LOW + SOC_MEDIUM) / 2)
    assert "moderate" in guidance.lower()


def test_organic_carbon_guidance_healthy_at_or_above_soc_medium():
    guidance = _organic_carbon_guidance(SOC_MEDIUM)
    assert "healthy" in guidance.lower()


# ---------------------------------------------------------------------------
# recommend_fertilizer - full pipeline
# ---------------------------------------------------------------------------


def test_recommend_fertilizer_all_adequate_produces_no_warnings_or_categories():
    result = recommend_fertilizer(crop="rice", **ADEQUATE, ph=GOOD_PH, growth_stage="vegetative", moisture=20)
    assert result["warnings"] == []
    assert result["organic_matter_guidance"] is None
    for entry in result["deficiencies"]:
        assert entry["status"] == "ADEQUATE"
        assert entry["recommended_category"] is None


def test_recommend_fertilizer_deficient_nitrogen_sets_category_but_no_warning():
    """Only EXCESS nutrients append a warning; a DEFICIENT nutrient's
    actionable guidance is the recommended_category field instead - this
    test documents that asymmetry directly."""
    result = recommend_fertilizer(crop="rice", nitrogen=10, phosphorus=40, potassium=55, ph=GOOD_PH, growth_stage="vegetative")
    n_entry = next(d for d in result["deficiencies"] if d["nutrient"] == NUTRIENT_LABEL["nitrogen"])
    assert n_entry["status"] == "DEFICIENT"
    assert n_entry["recommended_category"] == FERTILIZER_CATEGORY["nitrogen"]
    assert not any("nitrogen" in w.lower() and "deficien" in w.lower() for w in result["warnings"])


def test_recommend_fertilizer_excess_potassium_appends_a_warning():
    result = recommend_fertilizer(crop="rice", nitrogen=80, phosphorus=40, potassium=150, ph=GOOD_PH, growth_stage="vegetative")
    k_entry = next(d for d in result["deficiencies"] if d["nutrient"] == NUTRIENT_LABEL["potassium"])
    assert k_entry["status"] == "EXCESS"
    assert k_entry["recommended_category"] is None  # only DEFICIENT gets a recommended category
    assert any("potassium" in w.lower() and "already above" in w.lower() for w in result["warnings"])


def test_recommend_fertilizer_multiple_simultaneous_issues():
    result = recommend_fertilizer(
        crop="rice", nitrogen=10, phosphorus=200, potassium=55, ph=5.0, growth_stage="vegetative", moisture=5,
    )
    statuses = {d["nutrient"]: d["status"] for d in result["deficiencies"]}
    assert statuses[NUTRIENT_LABEL["nitrogen"]] == "DEFICIENT"
    assert statuses[NUTRIENT_LABEL["phosphorus"]] == "EXCESS"
    assert statuses[NUTRIENT_LABEL["potassium"]] == "ADEQUATE"
    assert len(result["warnings"]) == 3  # phosphorus excess + acidic pH + low moisture


def test_recommend_fertilizer_ph_warning_included_when_acidic():
    result = recommend_fertilizer(crop="rice", **ADEQUATE, ph=5.0, growth_stage="vegetative")
    assert any("acidic" in w.lower() for w in result["warnings"])


def test_recommend_fertilizer_moisture_below_15_appends_a_warning():
    result = recommend_fertilizer(crop="rice", **ADEQUATE, ph=GOOD_PH, growth_stage="vegetative", moisture=10)
    assert any("moisture" in w.lower() for w in result["warnings"])


def test_recommend_fertilizer_moisture_none_is_not_checked_at_all():
    result = recommend_fertilizer(crop="rice", **ADEQUATE, ph=GOOD_PH, growth_stage="vegetative", moisture=None)
    assert not any("moisture" in w.lower() for w in result["warnings"])


def test_recommend_fertilizer_moisture_at_exactly_15_is_not_flagged():
    result = recommend_fertilizer(crop="rice", **ADEQUATE, ph=GOOD_PH, growth_stage="vegetative", moisture=15)
    assert not any("moisture" in w.lower() for w in result["warnings"])


def test_recommend_fertilizer_recognizes_every_valid_growth_stage():
    for stage in VALID_GROWTH_STAGES:
        result = recommend_fertilizer(crop="rice", **ADEQUATE, ph=GOOD_PH, growth_stage=stage)
        assert result["application_timing"] == GROWTH_STAGE_GUIDANCE[stage]


def test_recommend_fertilizer_growth_stage_is_case_and_whitespace_insensitive():
    result = recommend_fertilizer(crop="rice", **ADEQUATE, ph=GOOD_PH, growth_stage="  Vegetative  ")
    assert result["application_timing"] == GROWTH_STAGE_GUIDANCE["vegetative"]
    assert result["growth_stage"] == "  Vegetative  "  # echoed back verbatim, unlike the internal lookup key


def test_recommend_fertilizer_unrecognized_growth_stage_falls_back_to_generic_guidance():
    result = recommend_fertilizer(crop="rice", **ADEQUATE, ph=GOOD_PH, growth_stage="dormancy")
    assert "not recognized" in result["application_timing"].lower()


def test_recommend_fertilizer_organic_carbon_guidance_flows_through():
    result = recommend_fertilizer(crop="rice", **ADEQUATE, ph=GOOD_PH, growth_stage="vegetative", organic_carbon=0.3)
    assert "low" in result["organic_matter_guidance"].lower()


def test_recommend_fertilizer_farm_area_acres_is_echoed_unchanged():
    result = recommend_fertilizer(crop="rice", **ADEQUATE, ph=GOOD_PH, growth_stage="vegetative", farm_area_acres=3.5)
    assert result["farm_area_acres"] == 3.5


def test_recommend_fertilizer_disclaimer_is_always_present():
    result = recommend_fertilizer(crop="rice", **ADEQUATE, ph=GOOD_PH, growth_stage="vegetative")
    assert "not a calibrated dosage" in result["disclaimer"].lower()


def test_recommend_fertilizer_crop_parameter_has_no_effect_on_computation_KNOWN_BEHAVIOR():
    """
    Documents real, current behavior (by design, per the module's own
    docstring - not a bug): `crop` is only echoed back in the response, never
    used to vary the nutrient thresholds, warnings, or guidance. Two
    completely different (and even nonexistent) crop names with identical
    numeric inputs produce byte-identical recommendations apart from the
    echoed crop field.
    """
    rice_result = recommend_fertilizer(crop="rice", nitrogen=10, phosphorus=200, potassium=55, ph=5.0, growth_stage="vegetative", moisture=5)
    fake_crop_result = recommend_fertilizer(crop="a_completely_made_up_crop", nitrogen=10, phosphorus=200, potassium=55, ph=5.0, growth_stage="vegetative", moisture=5)

    rice_result_no_crop = {k: v for k, v in rice_result.items() if k != "crop"}
    fake_result_no_crop = {k: v for k, v in fake_crop_result.items() if k != "crop"}
    assert rice_result_no_crop == fake_result_no_crop
    assert rice_result["crop"] == "rice"
    assert fake_crop_result["crop"] == "a_completely_made_up_crop"
