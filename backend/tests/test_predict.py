"""
API-level tests for app/api/predict.py (POST /predict/crop, alias
POST /predict/top-crops, and POST /explain/crop) - request validation,
auth enforcement, real inference end-to-end through the HTTP layer, and
farm-scoped database persistence (crop_predictions/crop_scores).
"""

import app.api.predict as predict_module
from app.models.prediction import CropPrediction, CropScore
from app.services.ml_service import ModelUnavailableError

RICE_PAYLOAD = {"nitrogen": 90, "phosphorus": 42, "potassium": 43, "temperature": 20.8, "humidity": 82, "ph": 6.5, "rainfall": 202.9}


# ---------------------------------------------------------------------------
# POST /predict/crop (and alias /predict/top-crops)
# ---------------------------------------------------------------------------


def test_predict_crop_success_shape(client, auth_headers):
    resp = client.post("/api/predict/crop", json=RICE_PAYLOAD, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["top_crops"]) == 5
    assert body["top_crops"][0]["crop"] == "rice"
    assert body["model_used"] == "random_forest"
    assert body["input"]["nitrogen"] == 90
    assert "farm_id" not in body["input"]  # farm_id is excluded from the echoed input


def test_predict_top_crops_alias_returns_identical_result(client, auth_headers):
    a = client.post("/api/predict/crop", json=RICE_PAYLOAD, headers=auth_headers).json()
    b = client.post("/api/predict/top-crops", json=RICE_PAYLOAD, headers=auth_headers).json()
    assert a["top_crops"] == b["top_crops"]


def test_predict_crop_requires_authentication(client):
    resp = client.post("/api/predict/crop", json=RICE_PAYLOAD)
    assert resp.status_code == 401


def test_predict_crop_rejects_nitrogen_above_max(client, auth_headers):
    resp = client.post("/api/predict/crop", json={**RICE_PAYLOAD, "nitrogen": 301}, headers=auth_headers)
    assert resp.status_code == 422


def test_predict_crop_rejects_negative_nitrogen(client, auth_headers):
    resp = client.post("/api/predict/crop", json={**RICE_PAYLOAD, "nitrogen": -1}, headers=auth_headers)
    assert resp.status_code == 422


def test_predict_crop_rejects_ph_above_14(client, auth_headers):
    resp = client.post("/api/predict/crop", json={**RICE_PAYLOAD, "ph": 14.1}, headers=auth_headers)
    assert resp.status_code == 422


def test_predict_crop_rejects_temperature_below_min(client, auth_headers):
    resp = client.post("/api/predict/crop", json={**RICE_PAYLOAD, "temperature": -10.1}, headers=auth_headers)
    assert resp.status_code == 422


def test_predict_crop_rejects_missing_required_field(client, auth_headers):
    incomplete = {k: v for k, v in RICE_PAYLOAD.items() if k != "rainfall"}
    resp = client.post("/api/predict/crop", json=incomplete, headers=auth_headers)
    assert resp.status_code == 422


def test_predict_crop_returns_503_when_model_unavailable(client, auth_headers, monkeypatch):
    def boom(_payload):
        raise ModelUnavailableError("model artifacts not found")

    monkeypatch.setattr(predict_module, "predict_top_k", boom)
    resp = client.post("/api/predict/crop", json=RICE_PAYLOAD, headers=auth_headers)
    assert resp.status_code == 503
    assert "model artifacts not found" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# farm_id-triggered persistence to crop_predictions / crop_scores
# ---------------------------------------------------------------------------


def test_predict_crop_without_farm_id_does_not_persist_anything(client, auth_headers, db_session):
    before = db_session.query(CropPrediction).count()
    resp = client.post("/api/predict/crop", json=RICE_PAYLOAD, headers=auth_headers)
    assert resp.status_code == 200
    after = db_session.query(CropPrediction).count()
    assert after == before


def test_predict_crop_with_owned_farm_id_persists_prediction_and_scores(client, auth_headers, farm, db_session):
    resp = client.post("/api/predict/crop", json={**RICE_PAYLOAD, "farm_id": farm["id"]}, headers=auth_headers)
    assert resp.status_code == 200

    saved = db_session.query(CropPrediction).filter(CropPrediction.farm_id == farm["id"]).one()
    assert saved.top_crop == "rice"
    assert saved.top_score > 0.9
    assert saved.input_json["nitrogen"] == 90
    assert "farm_id" not in saved.input_json

    scores = db_session.query(CropScore).filter(CropScore.prediction_id == saved.id).order_by(CropScore.rank).all()
    assert len(scores) == 5
    assert scores[0].crop == "rice"
    assert scores[0].rank == 1
    assert [s.rank for s in scores] == [1, 2, 3, 4, 5]


def test_predict_crop_with_unowned_farm_id_silently_skips_persistence(client, auth_headers, db_session):
    """
    Documents actual current behavior: predict.py looks up the farm scoped to
    the current farmer (Farm.id == payload.farm_id, Farm.farmer_id ==
    farmer.id) and, if not found (wrong owner, or a nonexistent id), just
    skips the `if farm:` persistence block silently - the prediction still
    succeeds and returns 200 with no error or warning that nothing was saved.
    """
    resp = client.post("/api/predict/crop", json={**RICE_PAYLOAD, "farm_id": 999999999}, headers=auth_headers)
    assert resp.status_code == 200
    assert db_session.query(CropPrediction).filter(CropPrediction.farm_id == 999999999).count() == 0


def test_predict_crop_does_not_persist_to_a_farm_owned_by_a_different_farmer(client, auth_headers, farm, db_session):
    """A second farmer must not be able to attach a prediction to the first
    farmer's farm just by guessing its id."""
    email_resp = client.post(
        "/api/auth/register",
        json={"name": "Other Farmer", "email": "other_farmer_predict_test@example.com", "password": "secret123"},
    )
    other_headers = {"Authorization": f"Bearer {email_resp.json()['access_token']}"}

    resp = client.post("/api/predict/crop", json={**RICE_PAYLOAD, "farm_id": farm["id"]}, headers=other_headers)
    assert resp.status_code == 200  # prediction itself still succeeds
    assert db_session.query(CropPrediction).filter(CropPrediction.farm_id == farm["id"]).count() == 0


# ---------------------------------------------------------------------------
# POST /explain/crop
# ---------------------------------------------------------------------------


def test_explain_crop_success_shape(client, auth_headers):
    resp = client.post("/api/explain/crop", json={**RICE_PAYLOAD, "crop": "rice"}, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["crop"] == "rice"
    assert len(body["contributions"]) == 7
    assert body["method"] == "shap"
    assert "Rice" in body["narrative"]


def test_explain_crop_requires_authentication(client):
    resp = client.post("/api/explain/crop", json={**RICE_PAYLOAD, "crop": "rice"})
    assert resp.status_code == 401


def test_explain_crop_unknown_crop_returns_400(client, auth_headers):
    resp = client.post("/api/explain/crop", json={**RICE_PAYLOAD, "crop": "unicorn_fruit"}, headers=auth_headers)
    assert resp.status_code == 400
    assert "unknown crop" in resp.json()["detail"].lower()


def test_explain_crop_missing_crop_field_returns_422(client, auth_headers):
    resp = client.post("/api/explain/crop", json=RICE_PAYLOAD, headers=auth_headers)
    assert resp.status_code == 422


def test_explain_crop_returns_503_when_model_unavailable(client, auth_headers, monkeypatch):
    def boom(_payload, _crop):
        raise ModelUnavailableError("SHAP explanation not supported for model 'svm' in this MVP.")

    monkeypatch.setattr(predict_module, "explain_prediction", boom)
    resp = client.post("/api/explain/crop", json={**RICE_PAYLOAD, "crop": "rice"}, headers=auth_headers)
    assert resp.status_code == 503
