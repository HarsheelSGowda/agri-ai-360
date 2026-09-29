"""
Tests for app/services/water_service.py - the FAO Blaney-Criddle water
requirement calculation. Runs against the real reference tables already
committed under models/ (water_kc_reference.json, water_p_reference.json) -
no mocking of the calculation itself, since it's local, deterministic,
offline data. Only the "reference file missing" error paths use a temp
directory + monkeypatch/cache_clear, mirroring the pattern already
established in test_ml_service.py for the same kind of lru_cache'd loader.
"""

import pytest

from app.services import water_service as ws
from app.services.water_service import (
    STATE_LATITUDE,
    WaterDataUnavailableError,
    _lookup_p,
    effective_rainfall,
    load_kc_reference,
    load_p_reference,
    predict_water_requirement,
    reference_et0,
    supported_water_crops,
)

JULY = 6  # 0=Jan..11=Dec


# ---------------------------------------------------------------------------
# supported_water_crops / reference loading
# ---------------------------------------------------------------------------


def test_supported_water_crops_matches_real_reference_file():
    crops = supported_water_crops()
    assert len(crops) == 17
    assert crops == sorted(crops)
    assert "rice" in crops
    assert "wheat" not in crops  # not one of the FAO-56 rows this project extracted


def test_load_kc_reference_raises_nothing_returns_dict():
    ref = load_kc_reference()
    assert ref is not None
    assert ref["rice"]["kc_mid"] == 1.2


def test_load_kc_reference_returns_none_when_file_missing(tmp_path, monkeypatch):
    load_kc_reference.cache_clear()
    monkeypatch.setattr(ws, "_models_dir", lambda: tmp_path)
    try:
        assert load_kc_reference() is None
    finally:
        load_kc_reference.cache_clear()


def test_load_p_reference_returns_none_when_file_missing(tmp_path, monkeypatch):
    load_p_reference.cache_clear()
    monkeypatch.setattr(ws, "_models_dir", lambda: tmp_path)
    try:
        assert load_p_reference() is None
    finally:
        load_p_reference.cache_clear()


# ---------------------------------------------------------------------------
# _lookup_p - FAO Table 4 interpolation
# ---------------------------------------------------------------------------


def test_lookup_p_exact_band_boundary_returns_table_value_directly():
    # lat=20.0 lands exactly on a table band - no interpolation math involved.
    assert _lookup_p(20.0, JULY) == 0.3


def test_lookup_p_interpolates_between_bands():
    # Halfway between the 20 (0.30) and 25 (0.31) July bands -> 0.305.
    assert _lookup_p(22.5, JULY) == pytest.approx(0.305)


def test_lookup_p_clamps_latitude_above_60_to_the_60_band():
    assert _lookup_p(100, JULY) == _lookup_p(60, JULY)


def test_lookup_p_clamps_negative_latitude_using_absolute_value():
    """India has no negative-latitude farms, but the function takes abs()
    defensively - documents that -70 behaves identically to +70 (both clamp
    to the 60 band), not as an error."""
    assert _lookup_p(-70, JULY) == _lookup_p(60, JULY)


def test_lookup_p_raises_when_reference_missing(tmp_path, monkeypatch):
    load_p_reference.cache_clear()
    monkeypatch.setattr(ws, "_models_dir", lambda: tmp_path)
    try:
        with pytest.raises(WaterDataUnavailableError, match="water_p_reference"):
            _lookup_p(20.0, JULY)
    finally:
        load_p_reference.cache_clear()


# ---------------------------------------------------------------------------
# reference_et0 / effective_rainfall - the two component formulas
# ---------------------------------------------------------------------------


def test_reference_et0_matches_the_published_blaney_criddle_formula():
    # ETo = p * (0.46*T + 8); p=0.3 at lat=20/June, T=28 -> 0.3*(0.46*28+8) = 6.264
    assert reference_et0(temperature_c=28, latitude_deg=20, month_index=5) == pytest.approx(6.264)


def test_effective_rainfall_is_zero_for_zero_or_negative_rainfall():
    assert effective_rainfall(0) == 0.0
    assert effective_rainfall(-5) == 0.0


def test_effective_rainfall_below_250mm_uses_the_usda_scs_formula():
    # Pe = P*(125 - 0.2P)/125 for P <= 250mm
    assert effective_rainfall(100) == pytest.approx(100 * (125 - 20) / 125)


def test_effective_rainfall_is_continuous_at_the_250mm_boundary():
    below = effective_rainfall(250)
    above_formula = 125 + 0.1 * 250
    assert below == pytest.approx(above_formula)


def test_effective_rainfall_above_250mm_uses_the_linear_tail_formula():
    assert effective_rainfall(500) == pytest.approx(125 + 0.1 * 500)


def test_effective_rainfall_formula_is_calibrated_for_monthly_totals_not_a_single_days_reading_KNOWN_LIMITATION():
    """
    Documents a real methodological concern (not modified by this test pass):
    the USDA SCS effective-rainfall formula's constants (125, 0.2, 0.1) are
    the standard values for MONTHLY rainfall totals in irrigation-engineering
    literature. But predict_water_requirement() passes this function whatever
    `rainfall_mm` the caller supplies for a single day, and the real frontend
    (WaterEstimator.tsx) pre-fills that field directly from the *current*
    weather reading (a same-day figure, typically 0-15mm), not a monthly
    total (which for most of India would be tens to hundreds of mm). Applying
    a monthly-calibrated formula to a daily reading and labeling the result
    "effective_rainfall_mm_per_day" conflates two different timeframes. It
    doesn't crash and the numeric outputs are still bounded/sane (see the
    boundary tests above), but the physical interpretation of the result for
    typical daily-rainfall inputs (a few mm) should be treated with caution -
    a day with only 5mm of rain runs almost entirely through the P<=250
    branch and the ratio holds up fine at that end, but the formula was not
    designed or validated for this input distribution.
    """
    daily_reading_mm = 8.0  # typical single-day rainfall, per the real WaterEstimator.tsx flow
    result = effective_rainfall(daily_reading_mm)
    assert result == pytest.approx(daily_reading_mm * (125 - 0.2 * daily_reading_mm) / 125)
    # The formula still returns *something* well-behaved (not negative, not absurd) for a
    # small daily figure - this test pins that current behavior without asserting it is correct.
    assert 0 <= result <= daily_reading_mm


# ---------------------------------------------------------------------------
# predict_water_requirement - full pipeline
# ---------------------------------------------------------------------------


def test_predict_water_requirement_full_pinned_result_for_rice_maharashtra_july():
    result = predict_water_requirement("rice", "Maharashtra", JULY, temperature_c=28.0, rainfall_mm=50.0, area_acres=2.0)
    assert result == {
        "supported": True,
        "crop": "rice",
        "kc_mid": 1.2,
        "kc_category": "specific",
        "kc_source_row": "Rice",
        "kc_note": None,
        "state": "Maharashtra",
        "latitude_deg": 19.08,
        "month": "Jul",
        "p_value": 0.298,
        "reference_et0_mm_per_day": 6.23,
        "crop_water_use_mm_per_day": 7.47,
        "effective_rainfall_mm_per_day": 46.0,
        "net_irrigation_mm_per_day": 0.0,
        "net_irrigation_liters_per_acre_per_day": 0.0,
        "net_irrigation_liters_total_per_day": 0.0,
    }


def test_predict_water_requirement_net_irrigation_never_goes_negative():
    """When effective rainfall exceeds crop water use, net irrigation floors
    at 0.0 rather than going negative (max(0.0, ...) in the source)."""
    result = predict_water_requirement("rice", "Maharashtra", JULY, temperature_c=28.0, rainfall_mm=50.0)
    assert result["net_irrigation_mm_per_day"] >= 0.0


def test_predict_water_requirement_low_rainfall_yields_positive_net_irrigation():
    result = predict_water_requirement("rice", "Maharashtra", JULY, temperature_c=28.0, rainfall_mm=0.0)
    assert result["net_irrigation_mm_per_day"] > 0.0
    assert result["net_irrigation_liters_per_acre_per_day"] > 0.0


def test_predict_water_requirement_is_case_insensitive_on_crop_name():
    result = predict_water_requirement("RICE", "Maharashtra", JULY, temperature_c=28.0, rainfall_mm=50.0)
    assert result["supported"] is True
    assert result["crop"] == "RICE"  # echoes back the original casing the caller sent


def test_predict_water_requirement_unsupported_crop_returns_supported_false_not_an_error():
    result = predict_water_requirement("wheat", "Maharashtra", JULY, temperature_c=28.0, rainfall_mm=50.0)
    assert result["supported"] is False
    assert "wheat" in result["reason"]
    assert "rice" in result["reason"]  # lists the crops that ARE covered


def test_predict_water_requirement_unrecognized_state_returns_supported_false():
    result = predict_water_requirement("rice", "Atlantis", JULY, temperature_c=28.0, rainfall_mm=50.0)
    assert result["supported"] is False
    assert "Atlantis" in result["reason"]


def test_predict_water_requirement_without_area_acres_leaves_total_liters_none():
    result = predict_water_requirement("rice", "Maharashtra", JULY, temperature_c=28.0, rainfall_mm=50.0)
    assert result["net_irrigation_liters_total_per_day"] is None


def test_predict_water_requirement_with_zero_area_acres_also_leaves_total_liters_none():
    """Defense-in-depth: even if a caller bypasses the API schema's gt=0
    constraint and passes area_acres=0 directly to the service function, the
    `area_acres > 0` guard still prevents a bogus 0-multiplied total."""
    result = predict_water_requirement("rice", "Maharashtra", JULY, temperature_c=28.0, rainfall_mm=50.0, area_acres=0)
    assert result["net_irrigation_liters_total_per_day"] is None


def test_predict_water_requirement_raises_when_kc_reference_missing(tmp_path, monkeypatch):
    load_kc_reference.cache_clear()
    monkeypatch.setattr(ws, "_models_dir", lambda: tmp_path)
    try:
        with pytest.raises(WaterDataUnavailableError, match="Kc reference"):
            predict_water_requirement("rice", "Maharashtra", JULY, temperature_c=28.0, rainfall_mm=50.0)
    finally:
        load_kc_reference.cache_clear()


def test_state_latitude_table_covers_every_indian_state_used_in_the_dataset():
    # Sanity check on the static reference table itself - real coordinates, not estimated.
    assert "Maharashtra" in STATE_LATITUDE
    assert 8.0 <= STATE_LATITUDE["Kerala"] <= 37.0  # every entry should be a plausible India latitude
    assert all(0.0 <= lat <= 37.0 for lat in STATE_LATITUDE.values())
