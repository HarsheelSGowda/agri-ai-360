"""
API-level tests for app/api/risk_ml_router.py (GET /predict/yield-risk/options,
POST /predict/yield-risk) - request validation, auth enforcement, and the 503
error path. Calculation/model correctness itself is covered in
test_risk_ml_service.py.
"""

import app.api.risk_ml_router as risk_ml_router_module
from app.services.risk_ml_service import RiskModelUnavailableError

BASE_PAYLOAD = {"crop": "rice", "state": "Maharashtra", "season": "Kharif"}


def test_yield_risk_options_returns_real_reference_data(client, auth_headers):
    resp = client.get("/api/predict/yield-risk/options", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "rice" in body["supported_crops"]
    assert body["active_model"] == "risk_random_forest"
    assert 0.0 <= body["active_model_accuracy"] <= 1.0
    assert body["dataset_records"] == 325280


def test_yield_risk_options_requires_authentication(client):
    resp = client.get("/api/predict/yield-risk/options")
    assert resp.status_code == 401


def test_yield_risk_options_returns_empty_shape_when_metrics_missing(client, auth_headers, monkeypatch):
    monkeypatch.setattr(risk_ml_router_module, "load_risk_metrics", lambda: None)
    resp = client.get("/api/predict/yield-risk/options", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"supported_crops": [], "active_model": None, "active_model_accuracy": None, "dataset_records": 0}


def test_predict_yield_risk_success_shape(client, auth_headers):
    resp = client.post("/api/predict/yield-risk", json=BASE_PAYLOAD, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["supported"] is True
    assert body["mapped_crop"] == "Rice"
    assert body["risk_level"] == "HIGH"
    assert set(body["probabilities"].keys()) == {"LOW", "MEDIUM", "HIGH"}
    assert body["model_used"] == "risk_random_forest"


def test_predict_yield_risk_unsupported_crop_returns_200_with_supported_false(client, auth_headers):
    resp = client.post("/api/predict/yield-risk", json={**BASE_PAYLOAD, "crop": "wheat"}, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["supported"] is False
    assert "wheat" in body["reason"]


def test_predict_yield_risk_farm_id_is_accepted_but_has_no_effect_on_the_response_KNOWN_BEHAVIOR(client, auth_headers, farm):
    """
    Same pattern already found in water_router.py and profit_router.py:
    YieldRiskInput.farm_id exists in the schema, but
    predict_yield_risk_endpoint() never reads payload.farm_id - nothing is
    persisted anywhere, and the response is identical with or without it.
    """
    without_farm_id = client.post("/api/predict/yield-risk", json=BASE_PAYLOAD, headers=auth_headers).json()
    with_farm_id = client.post("/api/predict/yield-risk", json={**BASE_PAYLOAD, "farm_id": farm["id"]}, headers=auth_headers).json()
    assert without_farm_id == with_farm_id


def test_predict_yield_risk_with_a_nonexistent_state_returns_200_with_supported_true_KNOWN_BUG(client, auth_headers):
    """
    API-level confirmation of the bug documented in detail in
    test_risk_ml_service.py::test_predict_yield_risk_does_not_validate_state_KNOWN_BUG:
    a completely fictional state produces a normal 200 response with
    `supported: true` and a full, confident-looking risk prediction, rather
    than `supported: false` (the pattern every sibling endpoint - yield,
    water, profit - correctly uses for an unrecognized state).
    """
    resp = client.post("/api/predict/yield-risk", json={**BASE_PAYLOAD, "state": "Atlantis"}, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["supported"] is True
    assert body["risk_level"] in ("LOW", "MEDIUM", "HIGH")


def test_predict_yield_risk_rejects_missing_required_field(client, auth_headers):
    incomplete = {k: v for k, v in BASE_PAYLOAD.items() if k != "season"}
    resp = client.post("/api/predict/yield-risk", json=incomplete, headers=auth_headers)
    assert resp.status_code == 422


def test_predict_yield_risk_rejects_empty_crop_string(client, auth_headers):
    resp = client.post("/api/predict/yield-risk", json={**BASE_PAYLOAD, "crop": ""}, headers=auth_headers)
    assert resp.status_code == 422


def test_predict_yield_risk_requires_authentication(client):
    resp = client.post("/api/predict/yield-risk", json=BASE_PAYLOAD)
    assert resp.status_code == 401


def test_predict_yield_risk_returns_503_when_model_unavailable(client, auth_headers, monkeypatch):
    def boom(*_args, **_kwargs):
        raise RiskModelUnavailableError("Risk model has not been trained yet.")

    monkeypatch.setattr(risk_ml_router_module, "predict_yield_risk", boom)
    resp = client.post("/api/predict/yield-risk", json=BASE_PAYLOAD, headers=auth_headers)
    assert resp.status_code == 503
    assert "risk model" in resp.json()["detail"].lower()
