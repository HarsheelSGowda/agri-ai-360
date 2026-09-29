"""
Tests for app/api/history.py (GET /history, GET /history/disease) - reads
back the crop_predictions/disease_predictions rows that predict.py and
disease_router.py were already verified to write correctly. Covers auth,
farm/farmer ownership scoping, the farm_id filter, ordering, the 100-row
cap, and the summary-string formatting - using real rows inserted directly
via the test database session (fast, deterministic, no HTTP/ML overhead
needed since the persistence logic itself is already covered elsewhere).
"""

from datetime import datetime, timedelta, timezone

from app.models.disease import DiseaseDetection
from app.models.farm import Farm
from app.models.prediction import CropPrediction


def _add_farm(client, headers, name="History Farm", location="Pune, Maharashtra"):
    resp = client.post(
        "/api/farms",
        json={"name": name, "location": location, "area_acres": 2, "soil_type": "Loamy", "irrigation_available": True},
        headers=headers,
    )
    return resp.json()


def _add_prediction(db_session, farm_id, *, top_crop="rice", top_score=0.9, input_json=None, created_at=None):
    record = CropPrediction(
        farm_id=farm_id,
        input_json=input_json if input_json is not None else {"nitrogen": 90, "phosphorus": 42, "potassium": 43, "ph": 6.5, "temperature": 25, "humidity": 80, "rainfall": 200},
        top_crop=top_crop,
        top_score=top_score,
    )
    db_session.add(record)
    db_session.commit()
    if created_at is not None:
        record.created_at = created_at
        db_session.commit()
    return record


def _add_disease(db_session, farm_id, *, crop="apple", condition="Apple Scab", is_healthy=False, probability=0.9, created_at=None):
    record = DiseaseDetection(farm_id=farm_id, crop=crop, condition=condition, is_healthy=is_healthy, probability=probability, model_used="disease_logistic_regression")
    db_session.add(record)
    db_session.commit()
    if created_at is not None:
        record.created_at = created_at
        db_session.commit()
    return record


def _register_and_get_headers(client, name="History Other Farmer"):
    import uuid

    email = f"history_{uuid.uuid4().hex[:10]}@example.com"
    resp = client.post("/api/auth/register", json={"name": name, "email": email, "password": "secret123"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


# ---------------------------------------------------------------------------
# GET /history - crop recommendation history
# ---------------------------------------------------------------------------


def test_history_requires_authentication(client):
    resp = client.get("/api/history")
    assert resp.status_code == 401


def test_history_is_empty_for_a_fresh_farmer(client, auth_headers):
    resp = client.get("/api/history", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_history_returns_a_real_prediction_with_correct_shape(client, auth_headers, farm, db_session):
    _add_prediction(db_session, farm["id"])
    resp = client.get("/api/history", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    item = body[0]
    assert item["farm_id"] == farm["id"]
    assert item["farm_name"] == farm["name"]
    assert item["crop"] == "rice"
    assert item["score"] == 0.9
    assert item["soil_summary"] == "N:90 P:42 K:43 pH:6.5"
    assert item["weather_summary"] == "25°C, 80% humidity, 200mm rainfall"


def test_history_soil_and_weather_summary_show_none_for_missing_input_fields_KNOWN_BEHAVIOR(client, auth_headers, farm, db_session):
    """
    Documents actual current behavior: soil_summary/weather_summary are built
    with plain dict.get() calls and no fallback, so a prediction whose
    input_json is missing an expected key (e.g. malformed/older data) renders
    the literal string "None" in that slot rather than omitting it or using
    a placeholder like "N/A". Not a crash, just an unpolished display detail.
    """
    _add_prediction(db_session, farm["id"], input_json={"nitrogen": 90})  # missing phosphorus/potassium/ph/temperature/humidity/rainfall
    resp = client.get("/api/history", headers=auth_headers)
    item = resp.json()[0]
    assert item["soil_summary"] == "N:90 P:None K:None pH:None"
    assert item["weather_summary"] == "None°C, None% humidity, Nonemm rainfall"


def test_history_only_returns_the_current_farmers_own_predictions(client, auth_headers, farm, db_session):
    _add_prediction(db_session, farm["id"])
    other_headers = _register_and_get_headers(client)
    resp = client.get("/api/history", headers=other_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_history_farm_id_filter_narrows_to_one_farm(client, auth_headers, db_session):
    farm_a = _add_farm(client, auth_headers, name="Farm A")
    farm_b = _add_farm(client, auth_headers, name="Farm B")
    _add_prediction(db_session, farm_a["id"], top_crop="rice")
    _add_prediction(db_session, farm_b["id"], top_crop="maize")

    resp_all = client.get("/api/history", headers=auth_headers)
    resp_a = client.get("/api/history", params={"farm_id": farm_a["id"]}, headers=auth_headers)

    assert len(resp_all.json()) == 2
    assert len(resp_a.json()) == 1
    assert resp_a.json()[0]["crop"] == "rice"


def test_history_farm_id_for_a_farm_owned_by_another_farmer_returns_empty_not_an_error(client, auth_headers, farm, db_session):
    """
    Unlike dashboard.py (which 404s on an unowned/nonexistent farm_id),
    history.py's farm_id filter is applied on top of the already
    farmer-scoped base query - a farm_id belonging to someone else (or that
    doesn't exist) simply matches zero rows and returns [], not a 404. Real,
    working, but a different error-handling convention than dashboard.py's -
    worth knowing both patterns exist in the API.
    """
    _add_prediction(db_session, farm["id"])
    other_headers = _register_and_get_headers(client)
    other_farm = _add_farm(client, other_headers, name="Someone Else's Farm")

    resp = client.get("/api/history", params={"farm_id": other_farm["id"]}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_history_farm_id_for_a_nonexistent_farm_returns_empty(client, auth_headers, farm, db_session):
    _add_prediction(db_session, farm["id"])
    resp = client.get("/api/history", params={"farm_id": 999999999}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_history_is_ordered_newest_first(client, auth_headers, farm, db_session):
    now = datetime.now(timezone.utc)
    _add_prediction(db_session, farm["id"], top_crop="oldest", created_at=now - timedelta(days=2))
    _add_prediction(db_session, farm["id"], top_crop="middle", created_at=now - timedelta(days=1))
    _add_prediction(db_session, farm["id"], top_crop="newest", created_at=now)

    resp = client.get("/api/history", headers=auth_headers)
    crops = [item["crop"] for item in resp.json()]
    assert crops == ["newest", "middle", "oldest"]


def test_history_caps_results_at_100(client, auth_headers, farm, db_session):
    for _ in range(105):
        _add_prediction(db_session, farm["id"])
    resp = client.get("/api/history", headers=auth_headers)
    assert len(resp.json()) == 100


def test_history_rejects_a_non_integer_farm_id(client, auth_headers):
    resp = client.get("/api/history", params={"farm_id": "not-a-number"}, headers=auth_headers)
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /history/disease - disease diagnosis history
# ---------------------------------------------------------------------------


def test_disease_history_requires_authentication(client):
    resp = client.get("/api/history/disease")
    assert resp.status_code == 401


def test_disease_history_is_empty_for_a_fresh_farmer(client, auth_headers):
    resp = client.get("/api/history/disease", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_disease_history_returns_a_real_diagnosis_with_correct_shape(client, auth_headers, farm, db_session):
    _add_disease(db_session, farm["id"])
    resp = client.get("/api/history/disease", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    item = body[0]
    assert item["farm_id"] == farm["id"]
    assert item["farm_name"] == farm["name"]
    assert item["crop"] == "apple"
    assert item["condition"] == "Apple Scab"
    assert item["is_healthy"] is False
    assert item["model_used"] == "disease_logistic_regression"


def test_disease_history_includes_healthy_diagnoses_unlike_notifications(client, auth_headers, farm, db_session):
    """Contrast with notification_service.py, which only cares about
    unhealthy diagnoses - history.py's query has no is_healthy filter at all,
    so a healthy diagnosis must still show up here."""
    _add_disease(db_session, farm["id"], condition="Healthy", is_healthy=True)
    resp = client.get("/api/history/disease", headers=auth_headers)
    body = resp.json()
    assert len(body) == 1
    assert body[0]["is_healthy"] is True


def test_disease_history_only_returns_the_current_farmers_own_diagnoses(client, auth_headers, farm, db_session):
    _add_disease(db_session, farm["id"])
    other_headers = _register_and_get_headers(client)
    resp = client.get("/api/history/disease", headers=other_headers)
    assert resp.json() == []


def test_disease_history_farm_id_filter_narrows_to_one_farm(client, auth_headers, db_session):
    farm_a = _add_farm(client, auth_headers, name="Disease Farm A")
    farm_b = _add_farm(client, auth_headers, name="Disease Farm B")
    _add_disease(db_session, farm_a["id"], crop="apple")
    _add_disease(db_session, farm_b["id"], crop="maize")

    resp_a = client.get("/api/history/disease", params={"farm_id": farm_a["id"]}, headers=auth_headers)
    assert len(resp_a.json()) == 1
    assert resp_a.json()[0]["crop"] == "apple"


def test_disease_history_farm_id_for_a_farm_owned_by_another_farmer_returns_empty(client, auth_headers, farm, db_session):
    _add_disease(db_session, farm["id"])
    other_headers = _register_and_get_headers(client)
    other_farm = _add_farm(client, other_headers, name="Someone Else's Disease Farm")

    resp = client.get("/api/history/disease", params={"farm_id": other_farm["id"]}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_disease_history_is_ordered_newest_first(client, auth_headers, farm, db_session):
    now = datetime.now(timezone.utc)
    _add_disease(db_session, farm["id"], crop="oldest", created_at=now - timedelta(days=2))
    _add_disease(db_session, farm["id"], crop="middle", created_at=now - timedelta(days=1))
    _add_disease(db_session, farm["id"], crop="newest", created_at=now)

    resp = client.get("/api/history/disease", headers=auth_headers)
    crops = [item["crop"] for item in resp.json()]
    assert crops == ["newest", "middle", "oldest"]


def test_disease_history_caps_results_at_100(client, auth_headers, farm, db_session):
    for _ in range(105):
        _add_disease(db_session, farm["id"])
    resp = client.get("/api/history/disease", headers=auth_headers)
    assert len(resp.json()) == 100


def test_disease_history_rejects_a_non_integer_farm_id(client, auth_headers):
    resp = client.get("/api/history/disease", params={"farm_id": "not-a-number"}, headers=auth_headers)
    assert resp.status_code == 422
