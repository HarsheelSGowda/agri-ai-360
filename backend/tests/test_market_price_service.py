"""
Tests for app/services/market_price_service.py - the thin aggregation layer
over MarketPriceProvider (current price, trend, market comparison). Uses the
real default provider (HistoricalDBMarketPriceProvider) against real seeded
MarketPrice rows - no mocking of the provider itself, since it's local DB
data, not an external service.
"""

from datetime import date

import pytest

from app.models.market_price import MarketPrice
from app.services.market_price_service import (
    NoMarketDataError,
    get_current_price,
    get_market_comparison,
    get_trend,
    list_crops,
    list_districts,
    list_markets,
    list_states,
)


@pytest.fixture(autouse=True)
def _clean_market_prices(db_session):
    db_session.query(MarketPrice).delete()
    db_session.commit()
    yield
    db_session.query(MarketPrice).delete()
    db_session.commit()


def _add_price(db_session, *, crop="rice", state="Maharashtra", district="Pune", market="Pune APMC",
                variety="Common", price_date=date(2016, 1, 1), min_price=1900, max_price=2100,
                modal_price=2000, arrivals_tonnes=None):
    row = MarketPrice(
        crop=crop, state=state, district=district, market=market, variety=variety,
        price_date=price_date, min_price=min_price, max_price=max_price, modal_price=modal_price,
        arrivals_tonnes=arrivals_tonnes,
    )
    db_session.add(row)
    db_session.commit()
    return row


def test_no_market_data_error_is_a_real_exception_class():
    """Sanity check that this declared exception type is usable, even though
    (per source inspection) none of the current service functions raise it -
    they all return {"found": False, ...} instead."""
    with pytest.raises(NoMarketDataError):
        raise NoMarketDataError("no data")


def test_list_helpers_delegate_to_the_real_provider(db_session):
    _add_price(db_session, crop="rice", state="Maharashtra", district="Pune", market="Pune APMC")
    _add_price(db_session, crop="maize", state="Karnataka", district="Mysore", market="Mysore APMC")

    assert list_crops(db_session) == ["maize", "rice"]
    assert list_states(db_session, "rice") == ["Maharashtra"]
    assert list_districts(db_session, "rice", "Maharashtra") == ["Pune"]
    assert list_markets(db_session, "rice", "Maharashtra") == ["Pune APMC"]


# ---------------------------------------------------------------------------
# get_current_price
# ---------------------------------------------------------------------------


def test_get_current_price_found_with_a_single_market(db_session):
    _add_price(db_session, price_date=date(2016, 1, 10), min_price=1900, max_price=2100, modal_price=2000, variety="Fine")
    result = get_current_price(db_session, "rice", "Maharashtra")
    assert result == {
        "found": True,
        "crop": "rice",
        "state": "Maharashtra",
        "district": None,
        "market": None,
        "variety": "Fine",
        "as_of_date": "2016-01-10",
        "min_price": 1900.0,
        "max_price": 2100.0,
        "modal_price": 2000.0,
        "markets_reporting": 1,
        "source": "Agmarknet (Government of India mandi price records), calendar year 2016",
        "is_live": False,
    }


def test_get_current_price_aggregates_across_multiple_markets_on_the_latest_date(db_session):
    _add_price(db_session, market="Market A", price_date=date(2016, 1, 10), min_price=1800, max_price=2000, modal_price=1900)
    _add_price(db_session, market="Market B", price_date=date(2016, 1, 10), min_price=2000, max_price=2200, modal_price=2100)
    result = get_current_price(db_session, "rice", "Maharashtra")
    assert result["markets_reporting"] == 2
    assert result["min_price"] == 1800.0  # overall min across both markets
    assert result["max_price"] == 2200.0  # overall max across both markets
    assert result["modal_price"] == 2000.0  # average of 1900 and 2100


def test_get_current_price_only_considers_the_most_recent_date(db_session):
    _add_price(db_session, price_date=date(2016, 1, 1), modal_price=1000)  # older, must be ignored
    _add_price(db_session, price_date=date(2016, 1, 10), modal_price=2000)
    result = get_current_price(db_session, "rice", "Maharashtra")
    assert result["modal_price"] == 2000.0
    assert result["as_of_date"] == "2016-01-10"


def test_get_current_price_not_found_returns_a_reason(db_session):
    result = get_current_price(db_session, "rice", "Nowhere")
    assert result["found"] is False
    assert "rice" in result["reason"]
    assert "Nowhere" in result["reason"]
    assert "found" in result and len(result) == 2  # only found + reason keys, nothing else


def test_get_current_price_not_found_reason_mentions_district_and_market_when_given(db_session):
    result = get_current_price(db_session, "rice", "Nowhere", district="Nodistrict", market="Nomarket")
    assert "Nodistrict" in result["reason"]
    assert "Nomarket" in result["reason"]


def test_get_current_price_district_and_market_filters_narrow_the_result(db_session):
    _add_price(db_session, district="Pune", market="Pune APMC", price_date=date(2016, 1, 10), modal_price=2000)
    _add_price(db_session, district="Nashik", market="Nashik APMC", price_date=date(2016, 1, 10), modal_price=9999)
    result = get_current_price(db_session, "rice", "Maharashtra", district="Pune")
    assert result["modal_price"] == 2000.0


# ---------------------------------------------------------------------------
# get_trend
# ---------------------------------------------------------------------------


def test_get_trend_found_computes_up_direction_and_change_pct(db_session):
    _add_price(db_session, price_date=date(2016, 1, 1), modal_price=2000)
    _add_price(db_session, price_date=date(2016, 1, 10), modal_price=2200)
    result = get_trend(db_session, "rice", "Maharashtra", days=30)
    assert result["found"] is True
    assert len(result["points"]) == 2
    assert result["points"][0]["date"] == "2016-01-01"
    assert result["points"][-1]["date"] == "2016-01-10"
    assert result["trend_direction"] == "UP"
    assert result["change_pct"] == pytest.approx(10.0)  # (2200-2000)/2000*100


def test_get_trend_computes_down_direction(db_session):
    _add_price(db_session, price_date=date(2016, 1, 1), modal_price=2000)
    _add_price(db_session, price_date=date(2016, 1, 10), modal_price=1800)
    result = get_trend(db_session, "rice", "Maharashtra", days=30)
    assert result["trend_direction"] == "DOWN"
    assert result["change_pct"] == pytest.approx(-10.0)


def test_get_trend_computes_flat_direction_when_price_unchanged(db_session):
    _add_price(db_session, price_date=date(2016, 1, 1), modal_price=2000)
    _add_price(db_session, price_date=date(2016, 1, 10), modal_price=2000)
    result = get_trend(db_session, "rice", "Maharashtra", days=30)
    assert result["trend_direction"] == "FLAT"
    assert result["change_pct"] == 0.0


def test_get_trend_change_pct_guards_against_division_by_zero(db_session):
    """If the first point's modal_price is 0 (edge-case bad data), change_pct
    must fall back to 0.0 rather than raising a ZeroDivisionError."""
    _add_price(db_session, price_date=date(2016, 1, 1), modal_price=0, min_price=0, max_price=0)
    _add_price(db_session, price_date=date(2016, 1, 10), modal_price=2000)
    result = get_trend(db_session, "rice", "Maharashtra", days=30)
    assert result["change_pct"] == 0.0


def test_get_trend_averages_multiple_markets_per_date(db_session):
    _add_price(db_session, market="A", price_date=date(2016, 1, 1), modal_price=1900)
    _add_price(db_session, market="B", price_date=date(2016, 1, 1), modal_price=2100)
    result = get_trend(db_session, "rice", "Maharashtra", days=30)
    assert result["points"][0]["modal_price"] == 2000.0  # average of 1900 and 2100
    assert result["points"][0]["min_price"] == 1900.0
    assert result["points"][0]["max_price"] == 2100.0


def test_get_trend_not_found_returns_empty_points(db_session):
    result = get_trend(db_session, "rice", "Nowhere")
    assert result == {"found": False, "reason": "No historical trend data found for rice in Nowhere.", "points": []}


def test_get_trend_days_parameter_limits_the_window(db_session):
    for day in range(1, 6):
        _add_price(db_session, price_date=date(2016, 1, day), modal_price=2000 + day)
    result = get_trend(db_session, "rice", "Maharashtra", days=2)
    assert len(result["points"]) == 2
    assert result["points"][0]["date"] == "2016-01-04"
    assert result["points"][-1]["date"] == "2016-01-05"


# ---------------------------------------------------------------------------
# get_market_comparison
# ---------------------------------------------------------------------------


def test_get_market_comparison_found_sorted_by_modal_price_descending(db_session):
    _add_price(db_session, market="Low Market", district="Pune", price_date=date(2016, 1, 10), modal_price=1800, min_price=1700, max_price=1900, arrivals_tonnes=50.0)
    _add_price(db_session, market="High Market", district="Nashik", price_date=date(2016, 1, 10), modal_price=2200, min_price=2100, max_price=2300, arrivals_tonnes=30.0)

    result = get_market_comparison(db_session, "rice", "Maharashtra")
    assert result["found"] is True
    assert result["as_of_date"] == "2016-01-10"
    assert [m["market"] for m in result["markets"]] == ["High Market", "Low Market"]
    assert result["best_market"]["market"] == "High Market"
    assert result["markets"][0]["arrivals_tonnes"] == 30.0


def test_get_market_comparison_not_found_returns_empty_markets_and_none_best_market(db_session):
    result = get_market_comparison(db_session, "rice", "Nowhere")
    assert result == {"found": False, "reason": "No market comparison data found for rice in Nowhere.", "markets": []}


def test_get_market_comparison_district_filter_narrows_results(db_session):
    _add_price(db_session, district="Pune", market="Pune Market", price_date=date(2016, 1, 10))
    _add_price(db_session, district="Nashik", market="Nashik Market", price_date=date(2016, 1, 10))
    result = get_market_comparison(db_session, "rice", "Maharashtra", district="Pune")
    assert len(result["markets"]) == 1
    assert result["markets"][0]["market"] == "Pune Market"


def test_get_market_comparison_only_uses_the_latest_date_not_older_ones(db_session):
    """
    Documents actual behavior: get_market_comparison() calls
    provider.latest_snapshot() internally (not provider.market_comparison(),
    which takes an explicit as_of date) - so it always reflects only the most
    recent reporting date, with no way to compare an arbitrary historical
    date through this service function.
    """
    _add_price(db_session, market="Old Market", price_date=date(2016, 1, 1), modal_price=9999)
    _add_price(db_session, market="New Market", price_date=date(2016, 1, 10), modal_price=2000)
    result = get_market_comparison(db_session, "rice", "Maharashtra")
    assert [m["market"] for m in result["markets"]] == ["New Market"]
