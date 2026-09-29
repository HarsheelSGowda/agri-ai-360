"""
API-level tests for app/api/disease_router.py (GET /predict/disease/options,
POST /predict/disease) - multipart image upload handling, validation, auth,
farm-ownership-scoped persistence, and error paths. Uses the same real
committed training images as test_disease_service.py for genuine end-to-end
inference through the HTTP layer (no mocking of the ML model).
"""

from pathlib import Path

import app.api.disease_router as disease_router_module
from app.models.disease import DiseaseDetection
from app.services.disease_service import DiseaseModelUnavailableError, InvalidImageError

DATASET_DIR = Path(__file__).resolve().parents[2] / "ml" / "datasets" / "plant_disease"
APPLE_HEALTHY = DATASET_DIR / "apple__healthy" / "0055dd26-23a7-4415-ac61-e0b44ebfaf80___RS_HL 5672.JPG"
MAIZE_RUST = DATASET_DIR / "maize__common_rust" / "RS_Rust 1569.JPG"


def _image_file(path: Path = APPLE_HEALTHY, content_type: str = "image/jpeg"):
    return {"image": (path.name, path.read_bytes(), content_type)}


# ---------------------------------------------------------------------------
# GET /predict/disease/options
# ---------------------------------------------------------------------------


def test_disease_options_returns_real_reference_data(client, auth_headers):
    resp = client.get("/api/predict/disease/options", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["supported_crops"] == ["apple", "grapes", "maize", "orange"]
    assert len(body["classes"]) == 13
    assert body["active_model"] == "disease_logistic_regression"
    assert body["dataset_records"] == 3875


def test_disease_options_requires_authentication(client):
    resp = client.get("/api/predict/disease/options")
    assert resp.status_code == 401


def test_disease_options_returns_empty_shape_when_metrics_missing(client, auth_headers, monkeypatch):
    monkeypatch.setattr(disease_router_module, "load_disease_metrics", lambda: None)
    resp = client.get("/api/predict/disease/options", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == {"supported_crops": [], "classes": [], "active_model": None, "active_model_accuracy": None, "dataset_records": 0}


# ---------------------------------------------------------------------------
# POST /predict/disease - success paths
# ---------------------------------------------------------------------------


def test_predict_disease_success_with_a_real_healthy_leaf(client, auth_headers):
    resp = client.post("/api/predict/disease", files=_image_file(APPLE_HEALTHY), headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["top_prediction"]["crop"] == "apple"
    assert body["top_prediction"]["is_healthy"] is True
    assert body["saved_to_history"] is False  # no farm_id supplied
    assert "care_guidance" in body
    assert len(body["alternatives"]) == 2


def test_predict_disease_success_with_a_real_diseased_leaf(client, auth_headers):
    resp = client.post("/api/predict/disease", files=_image_file(MAIZE_RUST), headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["top_prediction"]["crop"] == "maize"
    assert body["top_prediction"]["condition"] == "Common Rust"
    assert body["top_prediction"]["is_healthy"] is False


def test_predict_disease_accepts_png_content_type(client, auth_headers):
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (32, 32), color=(50, 120, 50)).save(buf, format="PNG")
    resp = client.post("/api/predict/disease", files={"image": ("leaf.png", buf.getvalue(), "image/png")}, headers=auth_headers)
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# POST /predict/disease - validation / error paths
# ---------------------------------------------------------------------------


def test_predict_disease_rejects_a_non_image_content_type(client, auth_headers):
    resp = client.post("/api/predict/disease", files={"image": ("notes.txt", b"hello world", "text/plain")}, headers=auth_headers)
    assert resp.status_code == 400
    assert "jpeg, png or webp" in resp.json()["detail"].lower()


def test_predict_disease_rejects_an_empty_file(client, auth_headers):
    resp = client.post("/api/predict/disease", files={"image": ("empty.jpg", b"", "image/jpeg")}, headers=auth_headers)
    assert resp.status_code == 400
    assert "empty" in resp.json()["detail"].lower()


def test_predict_disease_rejects_an_oversized_file(client, auth_headers):
    oversized = b"\xff" * (8 * 1024 * 1024 + 1)  # just over the 8 MB limit; content stays a declared image/jpeg
    resp = client.post("/api/predict/disease", files={"image": ("huge.jpg", oversized, "image/jpeg")}, headers=auth_headers)
    assert resp.status_code == 400
    assert "too large" in resp.json()["detail"].lower()


def test_predict_disease_rejects_corrupt_image_bytes_with_a_valid_content_type(client, auth_headers):
    """Declared content-type passes the router's own check, but the bytes
    themselves aren't a real image at all - InvalidImageError -> 400."""
    resp = client.post("/api/predict/disease", files={"image": ("fake.jpg", b"not actually a jpeg", "image/jpeg")}, headers=auth_headers)
    assert resp.status_code == 400
    assert "readable image" in resp.json()["detail"].lower()


def test_predict_disease_missing_image_field_returns_422(client, auth_headers):
    resp = client.post("/api/predict/disease", headers=auth_headers)
    assert resp.status_code == 422


def test_predict_disease_requires_authentication(client):
    resp = client.post("/api/predict/disease", files=_image_file())
    assert resp.status_code == 401


def test_predict_disease_returns_503_when_model_unavailable(client, auth_headers, monkeypatch):
    def boom(_bytes):
        raise DiseaseModelUnavailableError("Disease model has not been trained yet.")

    monkeypatch.setattr(disease_router_module, "diagnose", boom)
    resp = client.post("/api/predict/disease", files=_image_file(), headers=auth_headers)
    assert resp.status_code == 503
    assert "disease model" in resp.json()["detail"].lower()


def test_predict_disease_returns_400_when_diagnose_raises_invalid_image_error(client, auth_headers, monkeypatch):
    """Confirms the router's own except-clause wiring for InvalidImageError,
    independent of whatever bytes actually trigger it inside diagnose()."""

    def boom(_bytes):
        raise InvalidImageError("The uploaded file isn't a readable image.")

    monkeypatch.setattr(disease_router_module, "diagnose", boom)
    resp = client.post("/api/predict/disease", files=_image_file(), headers=auth_headers)
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# POST /predict/disease - farm-scoped history persistence
# ---------------------------------------------------------------------------


def test_predict_disease_with_owned_farm_id_persists_to_history(client, auth_headers, farm, db_session):
    resp = client.post("/api/predict/disease", files=_image_file(MAIZE_RUST), data={"farm_id": str(farm["id"])}, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["saved_to_history"] is True

    saved = db_session.query(DiseaseDetection).filter(DiseaseDetection.farm_id == farm["id"]).one()
    assert saved.crop == "maize"
    assert saved.condition == "Common Rust"
    assert saved.is_healthy is False
    assert saved.model_used == "disease_logistic_regression"
    assert saved.probability == body["top_prediction"]["probability"]


def test_predict_disease_without_farm_id_does_not_persist_anything(client, auth_headers, db_session):
    before = db_session.query(DiseaseDetection).count()
    resp = client.post("/api/predict/disease", files=_image_file(), headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["saved_to_history"] is False
    after = db_session.query(DiseaseDetection).count()
    assert after == before


def test_predict_disease_with_unowned_farm_id_silently_skips_persistence(client, auth_headers, db_session):
    """Same 'silent skip, still succeeds' pattern already found in predict.py
    (crop recommendation): an id belonging to nobody just means the
    diagnosis isn't saved - no error, no warning in the response."""
    resp = client.post("/api/predict/disease", files=_image_file(), data={"farm_id": "999999999"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["saved_to_history"] is False
    assert db_session.query(DiseaseDetection).filter(DiseaseDetection.farm_id == 999999999).count() == 0


def test_predict_disease_does_not_persist_to_a_farm_owned_by_a_different_farmer(client, auth_headers, farm, db_session):
    other_resp = client.post(
        "/api/auth/register", json={"name": "Other Disease Farmer", "email": "other_disease_test@example.com", "password": "secret123"}
    )
    other_headers = {"Authorization": f"Bearer {other_resp.json()['access_token']}"}

    resp = client.post("/api/predict/disease", files=_image_file(), data={"farm_id": str(farm["id"])}, headers=other_headers)
    assert resp.status_code == 200
    assert resp.json()["saved_to_history"] is False
    assert db_session.query(DiseaseDetection).filter(DiseaseDetection.farm_id == farm["id"]).count() == 0


def test_predict_disease_requires_a_farmer_profile_not_just_a_user(client, db_session):
    """predict_disease uses get_current_farmer (not get_current_user) - a
    valid token for a User with no Farmer profile must be rejected with 404,
    same as every other get_current_farmer-protected endpoint."""
    from app.core.security import create_access_token, hash_password
    from app.models.user import User

    email = "disease_orphan_user@example.com"
    user = User(email=email, password_hash=hash_password("secret123"))
    db_session.add(user)
    db_session.commit()
    token = create_access_token(subject=email)

    resp = client.post("/api/predict/disease", files=_image_file(), headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404
    assert "farmer profile" in resp.json()["detail"].lower()
