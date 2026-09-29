"""
API-level tests for app/api/yield_router.py (GET /predict/yield/options,
POST /predict/yield) - request validation, auth enforcement, and the 503
error path. yield_service.py's own calculation correctness is already
covered incidentally (90%) via test_profit_service.py, since predict_profit
calls predict_yield internally with real data; these tests focus on the
HTTP layer's own behavior, using real reference data throughout.
"""

import app.api.yield_router as yield_router_module
from app.services.yield_service import YieldModelUnavailableError

BASE_PAYLOAD = {"crop": "rice", "state": "Maharashtra", "season": "Kharif"}


def test_yield_options_returns_real_reference_data(client, auth_headers):
    resp = client.get("/api/predict/yield/options", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "rice" in body["supported_crops"]
    assert len(body["states"]) == 37
    assert body["seasons"] == ["Autumn", "Kharif", "Rabi", "Summer", "Whole Year", "Winter"]
    assert body["dataset_records"] == 325280
    assert body["active_model"] == "yield_xgboost"
    assert body["active_model_r2"] == 0.9193696169130281


def test_yield_options_requires_authentication(client):
    resp = client.get("/api/predict/yield/options")
    assert resp.status_code == 401


def test_yield_options_returns_empty_shape_when_metrics_missing(client, auth_headers, monkeypatch):
    monkeypatch.setattr(yield_router_module, "load_yield_metrics", lambda: None)
    resp = client.get("/api/predict/yield/options", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == {
        "states": [], "seasons": [], "supported_crops": [], "dataset_records": 0, "active_model": None, "active_model_r2": None,
    }


def test_predict_yield_success_shape_matches_real_model_output(client, auth_headers):
    resp = client.post("/api/predict/yield", json=BASE_PAYLOAD, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body == {
        "supported": True,
        "crop": "rice",
        "mapped_crop": "Rice",
        "state": "Maharashtra",
        "season": "Kharif",
        "predicted_yield_tonnes_per_ha": 1.327,
        "predicted_yield_quintal_per_acre": 5.37,
        "model_used": "yield_xgboost",
        "r2_score": 0.9193696169130281,
        "mae": 1.0326488870594115,
        "reason": None,
    }


def test_predict_yield_unsupported_crop_returns_200_with_supported_false(client, auth_headers):
    resp = client.post("/api/predict/yield", json={**BASE_PAYLOAD, "crop": "wheat"}, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["supported"] is False
    assert "wheat" in body["reason"]


def test_predict_yield_unsupported_state_returns_200_with_supported_false(client, auth_headers):
    resp = client.post("/api/predict/yield", json={**BASE_PAYLOAD, "state": "Atlantis"}, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["supported"] is False
    assert "atlantis" in body["reason"].lower()


def test_predict_yield_unsupported_season_returns_200_with_supported_false(client, auth_headers):
    resp = client.post("/api/predict/yield", json={**BASE_PAYLOAD, "season": "Monsoon"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["supported"] is False


def test_predict_yield_farm_id_is_accepted_but_has_no_effect_on_the_response_KNOWN_BEHAVIOR(client, auth_headers, farm):
    """Same no-op pattern already found in water_router.py, profit_router.py
    and risk_ml_router.py: YieldPredictionInput.farm_id exists in the schema
    but predict_yield_endpoint() never reads it - nothing is persisted, and
    the response is identical with or without it."""
    without_farm_id = client.post("/api/predict/yield", json=BASE_PAYLOAD, headers=auth_headers).json()
    with_farm_id = client.post("/api/predict/yield", json={**BASE_PAYLOAD, "farm_id": farm["id"]}, headers=auth_headers).json()
    assert without_farm_id == with_farm_id


def test_predict_yield_rejects_missing_required_field(client, auth_headers):
    incomplete = {k: v for k, v in BASE_PAYLOAD.items() if k != "season"}
    resp = client.post("/api/predict/yield", json=incomplete, headers=auth_headers)
    assert resp.status_code == 422


def test_predict_yield_rejects_empty_crop_string(client, auth_headers):
    resp = client.post("/api/predict/yield", json={**BASE_PAYLOAD, "crop": ""}, headers=auth_headers)
    assert resp.status_code == 422


def test_predict_yield_requires_authentication(client):
    resp = client.post("/api/predict/yield", json=BASE_PAYLOAD)
    assert resp.status_code == 401


def test_predict_yield_returns_503_when_model_unavailable(client, auth_headers, monkeypatch):
    def boom(*_args, **_kwargs):
        raise YieldModelUnavailableError("Yield model has not been trained yet.")

    monkeypatch.setattr(yield_router_module, "predict_yield", boom)
    resp = client.post("/api/predict/yield", json=BASE_PAYLOAD, headers=auth_headers)
    assert resp.status_code == 503
    assert "yield model" in resp.json()["detail"].lower()
