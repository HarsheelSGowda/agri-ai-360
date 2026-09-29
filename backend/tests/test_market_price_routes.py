"""
API-level tests for app/api/market_price_routes.py - the 6 /market-prices
endpoints. Calculation correctness itself is covered in
test_market_price_service.py / test_market_price_provider.py; these tests
focus on the HTTP layer's routing, query params, auth, and response shapes,
using real seeded MarketPrice rows.
"""

from datetime import date

import pytest

from app.models.market_price import MarketPrice


@pytest.fixture(autouse=True)
def _clean_market_prices(db_session):
    db_session.query(MarketPrice).delete()
    db_session.commit()
    yield
    db_session.query(MarketPrice).delete()
    db_session.commit()


def _add_price(db_session, *, crop="rice", state="Maharashtra", district="Pune", market="Pune APMC",
                variety="Common", price_date=date(2016, 1, 10), min_price=1900, max_price=2100, modal_price=2000):
    row = MarketPrice(
        crop=crop, state=state, district=district, market=market, variety=variety,
        price_date=price_date, min_price=min_price, max_price=max_price, modal_price=modal_price,
    )
    db_session.add(row)
    db_session.commit()
    return row


# ---------------------------------------------------------------------------
# GET /market-prices/crops
# ---------------------------------------------------------------------------


def test_get_crops_returns_real_data(client, auth_headers, db_session):
    _add_price(db_session, crop="rice")
    _add_price(db_session, crop="maize")
    resp = client.get("/api/market-prices/crops", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == {"crops": ["maize", "rice"]}


def test_get_crops_requires_authentication(client):
    resp = client.get("/api/market-prices/crops")
    assert resp.status_code == 401


def test_get_crops_empty_when_no_data(client, auth_headers):
    resp = client.get("/api/market-prices/crops", headers=auth_headers)
    assert resp.json() == {"crops": []}


# ---------------------------------------------------------------------------
# GET /market-prices/states, /districts, /markets
# ---------------------------------------------------------------------------


def test_get_states_requires_crop_query_param(client, auth_headers):
    resp = client.get("/api/market-prices/states", headers=auth_headers)
    assert resp.status_code == 422


def test_get_states_returns_real_data(client, auth_headers, db_session):
    _add_price(db_session, crop="rice", state="Maharashtra")
    resp = client.get("/api/market-prices/states", params={"crop": "rice"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == {"states": ["Maharashtra"]}


def test_get_districts_requires_crop_and_state(client, auth_headers):
    resp = client.get("/api/market-prices/districts", params={"crop": "rice"}, headers=auth_headers)
    assert resp.status_code == 422


def test_get_districts_returns_real_data(client, auth_headers, db_session):
    _add_price(db_session, district="Pune")
    resp = client.get("/api/market-prices/districts", params={"crop": "rice", "state": "Maharashtra"}, headers=auth_headers)
    assert resp.json() == {"districts": ["Pune"]}


def test_get_markets_returns_real_data_and_respects_district_filter(client, auth_headers, db_session):
    _add_price(db_session, district="Pune", market="Pune APMC")
    _add_price(db_session, district="Nashik", market="Nashik APMC")
    resp_all = client.get("/api/market-prices/markets", params={"crop": "rice", "state": "Maharashtra"}, headers=auth_headers)
    resp_pune = client.get(
        "/api/market-prices/markets", params={"crop": "rice", "state": "Maharashtra", "district": "Pune"}, headers=auth_headers
    )
    assert resp_all.json() == {"markets": ["Nashik APMC", "Pune APMC"]}
    assert resp_pune.json() == {"markets": ["Pune APMC"]}


# ---------------------------------------------------------------------------
# GET /market-prices (current price)
# ---------------------------------------------------------------------------


def test_get_current_price_found(client, auth_headers, db_session):
    _add_price(db_session, modal_price=2000)
    resp = client.get("/api/market-prices", params={"crop": "rice", "state": "Maharashtra"}, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["found"] is True
    assert body["modal_price"] == 2000.0
    assert body["is_live"] is False
    assert "2016" in body["source"]


def test_get_current_price_not_found_still_returns_200(client, auth_headers):
    """found: false is a normal 200 response, not a 404 - same convention
    already established for water/profit/yield 'unsupported' responses."""
    resp = client.get("/api/market-prices", params={"crop": "rice", "state": "Nowhere"}, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["found"] is False
    assert body["reason"] is not None
    assert body["modal_price"] is None


def test_get_current_price_requires_crop_and_state(client, auth_headers):
    resp = client.get("/api/market-prices", params={"crop": "rice"}, headers=auth_headers)
    assert resp.status_code == 422


def test_get_current_price_requires_authentication(client):
    resp = client.get("/api/market-prices", params={"crop": "rice", "state": "Maharashtra"})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /market-prices/trend
# ---------------------------------------------------------------------------


def test_get_trend_found(client, auth_headers, db_session):
    _add_price(db_session, price_date=date(2016, 1, 1), modal_price=2000)
    _add_price(db_session, price_date=date(2016, 1, 10), modal_price=2200)
    resp = client.get("/api/market-prices/trend", params={"crop": "rice", "state": "Maharashtra"}, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["found"] is True
    assert len(body["points"]) == 2
    assert body["trend_direction"] == "UP"


def test_get_trend_respects_days_query_param(client, auth_headers, db_session):
    for day in range(1, 6):
        _add_price(db_session, price_date=date(2016, 1, day), modal_price=2000 + day)
    resp = client.get("/api/market-prices/trend", params={"crop": "rice", "state": "Maharashtra", "days": 2}, headers=auth_headers)
    assert len(resp.json()["points"]) == 2


def test_get_trend_not_found(client, auth_headers):
    resp = client.get("/api/market-prices/trend", params={"crop": "rice", "state": "Nowhere"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["found"] is False
    assert resp.json()["points"] == []


def test_get_trend_requires_authentication(client):
    resp = client.get("/api/market-prices/trend", params={"crop": "rice", "state": "Maharashtra"})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /market-prices/comparison
# ---------------------------------------------------------------------------


def test_get_comparison_found(client, auth_headers, db_session):
    _add_price(db_session, market="Market A", modal_price=1800)
    _add_price(db_session, market="Market B", modal_price=2200)
    resp = client.get("/api/market-prices/comparison", params={"crop": "rice", "state": "Maharashtra"}, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["found"] is True
    assert body["best_market"]["market"] == "Market B"
    assert len(body["markets"]) == 2


def test_get_comparison_not_found(client, auth_headers):
    resp = client.get("/api/market-prices/comparison", params={"crop": "rice", "state": "Nowhere"}, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["found"] is False
    assert body["best_market"] is None
    assert body["markets"] == []


def test_get_comparison_requires_authentication(client):
    resp = client.get("/api/market-prices/comparison", params={"crop": "rice", "state": "Maharashtra"})
    assert resp.status_code == 401


def test_get_comparison_requires_crop_and_state(client, auth_headers):
    resp = client.get("/api/market-prices/comparison", params={"crop": "rice"}, headers=auth_headers)
    assert resp.status_code == 422
