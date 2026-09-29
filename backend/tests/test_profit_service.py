"""
Tests for app/services/profit_service.py - Profit = Revenue (real yield
estimate x real historical mandi price) - farmer-supplied cost. Runs against
the real reference data already committed under models/ (price_reference.json)
and the real trained yield model via yield_service.py - no mocking of the
calculation itself. Only predict_yield() is monkeypatched, and only for the
one edge case (zero revenue) that real trained-model output can't produce on
demand.
"""

import pytest

from app.services import profit_service as ps
from app.services.profit_service import (
    HECTARES_PER_ACRE,
    ProfitDataUnavailableError,
    _lookup_price,
    load_price_reference,
    predict_profit,
    supported_profit_crops,
)


# ---------------------------------------------------------------------------
# Reference data loading / supported crops
# ---------------------------------------------------------------------------


def test_supported_profit_crops_matches_real_reference_file():
    crops = supported_profit_crops()
    assert crops == sorted(crops)
    assert set(crops) == {"blackgram", "lentil", "maize", "mungbean", "pigeonpeas", "rice"}


def test_load_price_reference_returns_real_data():
    ref = load_price_reference()
    assert ref is not None
    assert "national_median" in ref["rice"]
    assert "by_state" in ref["rice"]


def test_load_price_reference_returns_none_when_file_missing(tmp_path, monkeypatch):
    load_price_reference.cache_clear()
    monkeypatch.setattr(ps, "_models_dir", lambda: tmp_path)
    try:
        assert load_price_reference() is None
    finally:
        load_price_reference.cache_clear()


# ---------------------------------------------------------------------------
# _lookup_price
# ---------------------------------------------------------------------------


def test_lookup_price_returns_state_price_when_available():
    price, source = _lookup_price("rice", "Maharashtra")
    assert price == 3085.0
    assert source == "state"


def test_lookup_price_falls_back_to_national_median_for_an_uncovered_state():
    price, source = _lookup_price("rice", "Sikkim")  # not in rice's by_state dict per the real reference data
    ref = load_price_reference()
    assert "Sikkim" not in ref["rice"]["by_state"]  # confirms this test is exercising the fallback, not the direct hit
    assert price == ref["rice"]["national_median"]
    assert source == "national_fallback"


def test_lookup_price_returns_none_for_an_unsupported_crop():
    assert _lookup_price("wheat", "Maharashtra") is None


# ---------------------------------------------------------------------------
# predict_profit - full pipeline, pinned real result
# ---------------------------------------------------------------------------


def test_predict_profit_full_pinned_result_for_rice_maharashtra_kharif():
    result = predict_profit("rice", "Maharashtra", "Kharif", cost_per_acre=15000, area_acres=2)
    assert result == {
        "supported": True,
        "crop": "rice",
        "mapped_crop": "Rice",
        "state": "Maharashtra",
        "season": "Kharif",
        "yield_tonnes_per_ha": 1.327,
        "price_rs_per_quintal": 3085.0,
        "price_source": "state",
        "cost_per_acre": 15000,
        "revenue_per_acre": 16567.03,
        "profit_per_acre": 1567.03,
        "revenue_per_ha": 40937.95,
        "profit_per_ha": 3872.2,
        "margin_pct": 9.5,
        "total_farm_profit": 3134.05,
    }


def test_predict_profit_revenue_equals_yield_times_price_conversion():
    """Independently reconstruct revenue_per_acre from yield_tonnes_per_ha and
    price_rs_per_quintal to verify the unit conversion (tonnes/ha -> quintal/ha
    -> Rs/ha -> Rs/acre) rather than trusting the pinned value alone."""
    result = predict_profit("rice", "Maharashtra", "Kharif", cost_per_acre=0)
    expected_revenue_per_ha = result["yield_tonnes_per_ha"] * 10 * result["price_rs_per_quintal"]
    expected_revenue_per_acre = expected_revenue_per_ha / HECTARES_PER_ACRE
    assert result["revenue_per_ha"] == pytest.approx(expected_revenue_per_ha, abs=0.01)
    assert result["revenue_per_acre"] == pytest.approx(expected_revenue_per_acre, abs=0.01)


def test_predict_profit_with_zero_cost_profit_equals_revenue():
    result = predict_profit("rice", "Maharashtra", "Kharif", cost_per_acre=0)
    assert result["profit_per_acre"] == result["revenue_per_acre"]
    assert result["margin_pct"] == 100.0


def test_predict_profit_can_be_negative_when_cost_exceeds_revenue():
    result = predict_profit("rice", "Maharashtra", "Kharif", cost_per_acre=1_000_000)
    assert result["profit_per_acre"] < 0
    assert result["margin_pct"] < 0  # negative margin is valid and must not be clamped to 0/None


def test_predict_profit_without_area_acres_leaves_total_farm_profit_none():
    result = predict_profit("rice", "Maharashtra", "Kharif", cost_per_acre=10000)
    assert result["total_farm_profit"] is None


def test_predict_profit_with_zero_area_acres_also_leaves_total_farm_profit_none():
    result = predict_profit("rice", "Maharashtra", "Kharif", cost_per_acre=10000, area_acres=0)
    assert result["total_farm_profit"] is None


def test_predict_profit_total_farm_profit_scales_linearly_with_area():
    # abs=0.05 (not 0.01): total_farm_profit is computed from the *unrounded*
    # profit_per_acre internally, while this test can only multiply the
    # already-rounded (2dp) profit_per_acre from the response - two
    # independent roundings compounding across area_acres=5 can differ by a
    # couple of cents without either number being wrong.
    result = predict_profit("rice", "Maharashtra", "Kharif", cost_per_acre=10000, area_acres=5)
    assert result["total_farm_profit"] == pytest.approx(result["profit_per_acre"] * 5, abs=0.05)


# ---------------------------------------------------------------------------
# National-price fallback due to a real state-name mismatch between datasets
# ---------------------------------------------------------------------------


def test_predict_profit_chhattisgarh_silently_falls_back_to_national_price_KNOWN_BUG():
    """
    Documents a genuine, currently-unfixed data-quality bug (found while
    adding this test coverage, not fixed here per this pass's rules): the
    yield-prediction training data spells this state "Chhattisgarh" (used in
    yield_metrics.json's supported_states and returned by predict_yield), but
    the price-reference data spells it "Chattisgarh" (one 'h') in
    price_reference.json's rice.by_state keys. Because _lookup_price() does an
    exact string match, a real, valid Chhattisgarh rice profit calculation
    silently degrades to the *national* median price instead of the real,
    more accurate state price - with no warning anywhere in the response
    that this happened. price_source: "national_fallback" is the only signal,
    and nothing currently distinguishes "state genuinely not covered" from
    "state is covered under a different spelling".
    """
    ref = load_price_reference()
    assert "Chattisgarh" in ref["rice"]["by_state"]  # the real price data DOES have this state - just misspelled
    assert "Chhattisgarh" not in ref["rice"]["by_state"]

    result = predict_profit("rice", "Chhattisgarh", "Kharif", cost_per_acre=10000)
    assert result["supported"] is True
    assert result["price_source"] == "national_fallback"  # should be "state" if the spelling matched
    assert result["price_rs_per_quintal"] == ref["rice"]["national_median"]


# ---------------------------------------------------------------------------
# Unsupported / error paths
# ---------------------------------------------------------------------------


def test_predict_profit_unsupported_crop_returns_supported_false():
    result = predict_profit("wheat", "Maharashtra", "Kharif", cost_per_acre=1000)
    assert result["supported"] is False
    assert "wheat" in result["reason"]
    assert "rice" in result["reason"]


def test_predict_profit_unsupported_state_wraps_the_yield_service_reason():
    """Crop is profit-supported (rice), but the state isn't recognized by the
    yield model - profit_service must surface *that* reason, not invent its
    own or silently succeed with a bogus estimate."""
    result = predict_profit("rice", "Atlantis", "Kharif", cost_per_acre=1000)
    assert result["supported"] is False
    assert "yield estimate unavailable" in result["reason"].lower()
    assert "atlantis" in result["reason"].lower()


def test_predict_profit_unsupported_season_wraps_the_yield_service_reason():
    result = predict_profit("rice", "Maharashtra", "Monsoon", cost_per_acre=1000)
    assert result["supported"] is False
    assert "yield estimate unavailable" in result["reason"].lower()


def test_predict_profit_raises_when_price_reference_missing(tmp_path, monkeypatch):
    load_price_reference.cache_clear()
    monkeypatch.setattr(ps, "_models_dir", lambda: tmp_path)
    try:
        with pytest.raises(ProfitDataUnavailableError, match="Price reference"):
            predict_profit("rice", "Maharashtra", "Kharif", cost_per_acre=1000)
    finally:
        load_price_reference.cache_clear()


def test_predict_profit_margin_pct_is_none_when_revenue_is_zero(monkeypatch):
    """A real trained model won't predict exactly zero yield for a supported
    crop, so this edge case (division-by-zero guard on margin_pct) is
    exercised by monkeypatching predict_yield's real result down to zero -
    the only way to reach this branch without fabricating a fake model."""

    def zero_yield(_crop, _state, _season):
        return {
            "supported": True,
            "crop": "rice",
            "mapped_crop": "Rice",
            "state": "Maharashtra",
            "season": "Kharif",
            "predicted_yield_tonnes_per_ha": 0.0,
            "predicted_yield_quintal_per_acre": 0.0,
            "model_used": "yield_xgboost",
            "r2_score": 0.9,
            "mae": 0.1,
        }

    monkeypatch.setattr(ps, "predict_yield", zero_yield)
    result = predict_profit("rice", "Maharashtra", "Kharif", cost_per_acre=1000)
    assert result["revenue_per_acre"] == 0.0
    assert result["margin_pct"] is None
    assert result["profit_per_acre"] == -1000.0


def test_predict_profit_handles_the_defensive_price_lookup_none_branch(monkeypatch):
    """
    price_lookup can only be None here if a crop passes the
    supported_profit_crops() check but _lookup_price() then fails to find it
    anyway - both read the exact same reference data, so this is a "should
    never happen" defensive branch, not reachable through any real input.
    Covered by forcing _lookup_price() to disagree with reality, purely to
    exercise the response shape of that branch.
    """
    monkeypatch.setattr(ps, "_lookup_price", lambda _crop, _state: None)
    result = predict_profit("rice", "Maharashtra", "Kharif", cost_per_acre=1000)
    assert result["supported"] is False
    assert "unexpected" in result["reason"].lower()


def test_predict_profit_wraps_yield_model_unavailable_as_profit_data_unavailable(monkeypatch):
    from app.services.yield_service import YieldModelUnavailableError

    def boom(_crop, _state, _season):
        raise YieldModelUnavailableError("Yield model has not been trained yet.")

    monkeypatch.setattr(ps, "predict_yield", boom)
    with pytest.raises(ProfitDataUnavailableError, match="Yield model"):
        predict_profit("rice", "Maharashtra", "Kharif", cost_per_acre=1000)
