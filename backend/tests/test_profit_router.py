"""
API-level tests for app/api/profit_router.py (GET /predict/profit/options,
POST /predict/profit) - request validation, auth enforcement, and the 503
error path. Calculation correctness itself is covered in
test_profit_service.py.
"""

import app.api.profit_router as profit_router_module
from app.services.profit_service import ProfitDataUnavailableError

BASE_PAYLOAD = {"crop": "rice", "state": "Maharashtra", "season": "Kharif", "cost_per_acre": 15000}


def test_profit_options_returns_crops_and_price_year(client, auth_headers):
    resp = client.get("/api/predict/profit/options", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "rice" in body["supported_crops"]
    assert body["price_year"] == "2016"


def test_profit_options_requires_authentication(client):
    resp = client.get("/api/predict/profit/options")
    assert resp.status_code == 401


def test_predict_profit_success_shape(client, auth_headers):
    resp = client.post("/api/predict/profit", json=BASE_PAYLOAD, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["supported"] is True
    assert body["mapped_crop"] == "Rice"
    assert body["price_source"] == "state"
    assert body["profit_per_acre"] > 0


def test_predict_profit_unsupported_crop_returns_200_with_supported_false(client, auth_headers):
    resp = client.post("/api/predict/profit", json={**BASE_PAYLOAD, "crop": "wheat"}, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["supported"] is False
    assert "wheat" in body["reason"]


def test_predict_profit_unsupported_state_returns_200_with_supported_false(client, auth_headers):
    resp = client.post("/api/predict/profit", json={**BASE_PAYLOAD, "state": "Atlantis"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["supported"] is False


def test_predict_profit_with_area_acres_includes_total_farm_profit(client, auth_headers):
    resp = client.post("/api/predict/profit", json={**BASE_PAYLOAD, "area_acres": 4.0}, headers=auth_headers)
    body = resp.json()
    assert body["total_farm_profit"] is not None


def test_predict_profit_farm_id_is_accepted_but_has_no_effect_on_the_response_KNOWN_BEHAVIOR(client, auth_headers, farm):
    """
    Documents actual current behavior, same pattern already found in
    water_router.py: ProfitPredictionInput.farm_id exists in the schema, but
    predict_profit_endpoint() never reads payload.farm_id - nothing is
    persisted anywhere (there is no profit-estimate table), and the response
    is identical whether farm_id is supplied or not.
    """
    without_farm_id = client.post("/api/predict/profit", json=BASE_PAYLOAD, headers=auth_headers).json()
    with_farm_id = client.post("/api/predict/profit", json={**BASE_PAYLOAD, "farm_id": farm["id"]}, headers=auth_headers).json()
    assert without_farm_id == with_farm_id


def test_predict_profit_rejects_negative_cost(client, auth_headers):
    resp = client.post("/api/predict/profit", json={**BASE_PAYLOAD, "cost_per_acre": -1}, headers=auth_headers)
    assert resp.status_code == 422


def test_predict_profit_rejects_cost_above_1_million(client, auth_headers):
    resp = client.post("/api/predict/profit", json={**BASE_PAYLOAD, "cost_per_acre": 1_000_001}, headers=auth_headers)
    assert resp.status_code == 422


def test_predict_profit_accepts_cost_of_exactly_zero(client, auth_headers):
    resp = client.post("/api/predict/profit", json={**BASE_PAYLOAD, "cost_per_acre": 0}, headers=auth_headers)
    assert resp.status_code == 200


def test_predict_profit_rejects_zero_area_acres_at_the_schema_level(client, auth_headers):
    resp = client.post("/api/predict/profit", json={**BASE_PAYLOAD, "area_acres": 0}, headers=auth_headers)
    assert resp.status_code == 422


def test_predict_profit_rejects_missing_required_field(client, auth_headers):
    incomplete = {k: v for k, v in BASE_PAYLOAD.items() if k != "season"}
    resp = client.post("/api/predict/profit", json=incomplete, headers=auth_headers)
    assert resp.status_code == 422


def test_predict_profit_requires_authentication(client):
    resp = client.post("/api/predict/profit", json=BASE_PAYLOAD)
    assert resp.status_code == 401


def test_predict_profit_returns_503_when_reference_data_unavailable(client, auth_headers, monkeypatch):
    def boom(*_args, **_kwargs):
        raise ProfitDataUnavailableError("Price reference has not been built yet.")

    monkeypatch.setattr(profit_router_module, "predict_profit", boom)
    resp = client.post("/api/predict/profit", json=BASE_PAYLOAD, headers=auth_headers)
    assert resp.status_code == 503
    assert "price reference" in resp.json()["detail"].lower()
