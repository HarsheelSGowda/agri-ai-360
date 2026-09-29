"""
Tests for app/services/market_price_provider.py - HistoricalDBMarketPriceProvider,
the real DB-backed query layer over the market_prices table (real Agmarknet
2016 data model, seeded here with representative rows rather than mocked -
these are genuine SQLAlchemy queries against genuine rows).
"""

from datetime import date

import pytest

from app.models.market_price import MarketPrice
from app.services.market_price_provider import HistoricalDBMarketPriceProvider, get_market_price_provider

PROVIDER = HistoricalDBMarketPriceProvider()


@pytest.fixture(autouse=True)
def _clean_market_prices(db_session):
    """
    market_prices is unscoped, session-wide reference data (not per-farmer),
    and the test database is shared across the whole pytest session with no
    per-test rollback - without this, rows left behind by other tests (in
    this file or test_notification_service.py) would silently leak into
    list_crops()/list_states()-style assertions that expect an exact set.
    """
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


def test_get_market_price_provider_returns_the_historical_provider():
    provider = get_market_price_provider()
    assert isinstance(provider, HistoricalDBMarketPriceProvider)


def test_source_label_and_is_live():
    assert PROVIDER.is_live is False
    assert "2016" in PROVIDER.source_label
    assert "Agmarknet" in PROVIDER.source_label


def test_list_crops_returns_distinct_sorted_crops(db_session):
    _add_price(db_session, crop="rice")
    _add_price(db_session, crop="maize")
    _add_price(db_session, crop="rice", market="Different Market")  # duplicate crop, must not repeat
    assert PROVIDER.list_crops(db_session) == ["maize", "rice"]


def test_list_states_filters_by_crop(db_session):
    _add_price(db_session, crop="rice", state="Maharashtra")
    _add_price(db_session, crop="rice", state="Punjab")
    _add_price(db_session, crop="maize", state="Karnataka")
    assert PROVIDER.list_states(db_session, "rice") == ["Maharashtra", "Punjab"]
    assert PROVIDER.list_states(db_session, "maize") == ["Karnataka"]


def test_list_districts_filters_by_crop_and_state(db_session):
    _add_price(db_session, crop="rice", state="Maharashtra", district="Pune")
    _add_price(db_session, crop="rice", state="Maharashtra", district="Nashik")
    _add_price(db_session, crop="rice", state="Punjab", district="Amritsar")
    assert PROVIDER.list_districts(db_session, "rice", "Maharashtra") == ["Nashik", "Pune"]


def test_list_markets_filters_by_crop_state_and_optional_district(db_session):
    _add_price(db_session, crop="rice", state="Maharashtra", district="Pune", market="Pune APMC")
    _add_price(db_session, crop="rice", state="Maharashtra", district="Nashik", market="Nashik APMC")
    assert PROVIDER.list_markets(db_session, "rice", "Maharashtra") == ["Nashik APMC", "Pune APMC"]
    assert PROVIDER.list_markets(db_session, "rice", "Maharashtra", district="Pune") == ["Pune APMC"]


def test_latest_snapshot_returns_only_the_most_recent_date(db_session):
    _add_price(db_session, price_date=date(2016, 1, 1), modal_price=1900, market="A")
    _add_price(db_session, price_date=date(2016, 1, 10), modal_price=2100, market="B")
    rows = PROVIDER.latest_snapshot(db_session, "rice", "Maharashtra", None, None, None)
    assert len(rows) == 1
    assert rows[0].price_date == date(2016, 1, 10)
    assert rows[0].modal_price == 2100


def test_latest_snapshot_includes_all_markets_reporting_on_the_latest_date(db_session):
    _add_price(db_session, price_date=date(2016, 1, 10), market="Market A", modal_price=2000)
    _add_price(db_session, price_date=date(2016, 1, 10), market="Market B", modal_price=2200)
    rows = PROVIDER.latest_snapshot(db_session, "rice", "Maharashtra", None, None, None)
    assert len(rows) == 2
    assert {r.market for r in rows} == {"Market A", "Market B"}


def test_latest_snapshot_returns_empty_list_when_no_data(db_session):
    assert PROVIDER.latest_snapshot(db_session, "rice", "Nowhere", None, None, None) == []


def test_latest_snapshot_respects_the_district_filter(db_session):
    _add_price(db_session, district="Pune", market="Pune APMC", variety="Common", price_date=date(2016, 1, 5))
    _add_price(db_session, district="Nashik", market="Nashik APMC", variety="Fine", price_date=date(2016, 1, 5))
    rows = PROVIDER.latest_snapshot(db_session, "rice", "Maharashtra", "Pune", None, None)
    assert len(rows) == 1
    assert rows[0].district == "Pune"


def test_latest_snapshot_respects_the_market_filter(db_session):
    _add_price(db_session, market="Pune APMC", price_date=date(2016, 1, 5))
    _add_price(db_session, market="Nashik APMC", price_date=date(2016, 1, 5))
    rows = PROVIDER.latest_snapshot(db_session, "rice", "Maharashtra", None, "Pune APMC", None)
    assert len(rows) == 1
    assert rows[0].market == "Pune APMC"


def test_latest_snapshot_respects_the_variety_filter(db_session):
    _add_price(db_session, variety="Common", price_date=date(2016, 1, 5))
    _add_price(db_session, variety="Fine", price_date=date(2016, 1, 5))
    rows = PROVIDER.latest_snapshot(db_session, "rice", "Maharashtra", None, None, "Fine")
    assert len(rows) == 1
    assert rows[0].variety == "Fine"


def test_trend_orders_points_by_date_ascending(db_session):
    _add_price(db_session, price_date=date(2016, 1, 5), modal_price=2100)
    _add_price(db_session, price_date=date(2016, 1, 1), modal_price=2000)
    _add_price(db_session, price_date=date(2016, 1, 3), modal_price=2050)
    rows = PROVIDER.trend(db_session, "rice", "Maharashtra", None, None, None, limit_days=30)
    dates = [r.price_date for r in rows]
    assert dates == sorted(dates)


def test_trend_limit_days_caps_to_the_most_recent_distinct_dates(db_session):
    for day in range(1, 6):  # 5 distinct dates: Jan 1-5
        _add_price(db_session, price_date=date(2016, 1, day), modal_price=2000 + day)
    rows = PROVIDER.trend(db_session, "rice", "Maharashtra", None, None, None, limit_days=2)
    dates = {r.price_date for r in rows}
    assert dates == {date(2016, 1, 4), date(2016, 1, 5)}  # only the 2 most recent dates


def test_trend_returns_empty_list_when_no_data(db_session):
    assert PROVIDER.trend(db_session, "rice", "Nowhere", None, None, None, limit_days=30) == []


def test_market_comparison_returns_rows_for_the_exact_date_sorted_by_modal_price_desc(db_session):
    """
    market_comparison() is a real, correctly-implemented method on the
    provider interface - but market_price_service.get_market_comparison()
    actually calls latest_snapshot() instead of this method (confirmed by
    reading the source). This method is therefore currently unused by the
    rest of the app; tested directly here for its own correctness so that
    fact is documented rather than left as an untested dead path.
    """
    _add_price(db_session, market="Low Market", modal_price=1800, price_date=date(2016, 1, 10))
    _add_price(db_session, market="High Market", modal_price=2200, price_date=date(2016, 1, 10))
    _add_price(db_session, market="Wrong Date Market", modal_price=9999, price_date=date(2016, 1, 9))

    rows = PROVIDER.market_comparison(db_session, "rice", "Maharashtra", None, as_of=date(2016, 1, 10))
    assert [r.market for r in rows] == ["High Market", "Low Market"]  # sorted descending, wrong-date row excluded


def test_market_comparison_respects_district_filter(db_session):
    _add_price(db_session, district="Pune", market="Pune Market", price_date=date(2016, 1, 10))
    _add_price(db_session, district="Nashik", market="Nashik Market", price_date=date(2016, 1, 10))
    rows = PROVIDER.market_comparison(db_session, "rice", "Maharashtra", "Pune", as_of=date(2016, 1, 10))
    assert len(rows) == 1
    assert rows[0].district == "Pune"


def test_market_comparison_returns_empty_list_for_a_date_with_no_data(db_session):
    _add_price(db_session, price_date=date(2016, 1, 10))
    assert PROVIDER.market_comparison(db_session, "rice", "Maharashtra", None, as_of=date(2016, 6, 1)) == []
