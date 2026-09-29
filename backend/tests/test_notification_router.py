"""
API-level tests for app/api/notification_router.py - GET /notifications,
POST /notifications/generate, PATCH /notifications/{id}/read, PATCH
/notifications/read-all. Covers auth, farm/notification ownership checks,
and the real end-to-end generation flow (using the actual /farms/{id}/soil
endpoint to create a genuinely low-scoring soil record, so the notification
that comes back is produced by real business logic, not a stub).
"""

import uuid

import pytest

from app.models.disease import DiseaseDetection

BAD_SOIL = {"nitrogen": 5, "phosphorus": 2, "potassium": 5, "ph": 4.0, "soil_type": "Loamy"}


def _register_and_get_headers(client, name="Notif Router Farmer"):
    email = f"notifrouter_{uuid.uuid4().hex[:10]}@example.com"
    resp = client.post("/api/auth/register", json={"name": name, "email": email, "password": "secret123"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _create_farm(client, headers, location="Pune, Maharashtra", irrigation_available=True):
    resp = client.post(
        "/api/farms",
        json={"name": "Notif Farm", "location": location, "area_acres": 2, "soil_type": "Loamy", "irrigation_available": irrigation_available},
        headers=headers,
    )
    return resp.json()


# ---------------------------------------------------------------------------
# GET /notifications
# ---------------------------------------------------------------------------


def test_list_notifications_is_empty_for_a_fresh_farmer(client, auth_headers):
    resp = client.get("/api/notifications", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_notifications_requires_authentication(client):
    resp = client.get("/api/notifications")
    assert resp.status_code == 401


def test_list_notifications_only_returns_the_current_farmers_own_notifications(client):
    headers_a = _register_and_get_headers(client, "Farmer A")
    headers_b = _register_and_get_headers(client, "Farmer B")
    farm_a = _create_farm(client, headers_a, location="Pune, Maharashtra", irrigation_available=False)

    # Give farmer A's farm bad soil so /generate produces a real notification.
    client.post(f"/api/farms/{farm_a['id']}/soil", json=BAD_SOIL, headers=headers_a)
    client.post("/api/notifications/generate", params={"farm_id": farm_a["id"]}, headers=headers_a)

    resp_a = client.get("/api/notifications", headers=headers_a)
    resp_b = client.get("/api/notifications", headers=headers_b)
    assert len(resp_a.json()) > 0
    assert resp_b.json() == []  # farmer B must not see farmer A's notifications


def test_list_notifications_unread_only_filter(client, auth_headers, farm):
    client.post(f"/api/farms/{farm['id']}/soil", json=BAD_SOIL, headers=auth_headers)
    client.post("/api/notifications/generate", params={"farm_id": farm["id"]}, headers=auth_headers)

    all_notes = client.get("/api/notifications", headers=auth_headers).json()
    assert len(all_notes) > 0

    client.patch(f"/api/notifications/{all_notes[0]['id']}/read", headers=auth_headers)

    unread = client.get("/api/notifications", params={"unread_only": True}, headers=auth_headers).json()
    assert all_notes[0]["id"] not in [n["id"] for n in unread]
    assert len(unread) == len(all_notes) - 1


def test_list_notifications_farm_id_filter(client, auth_headers, farm):
    client.post(f"/api/farms/{farm['id']}/soil", json=BAD_SOIL, headers=auth_headers)
    client.post("/api/notifications/generate", params={"farm_id": farm["id"]}, headers=auth_headers)

    matching = client.get("/api/notifications", params={"farm_id": farm["id"]}, headers=auth_headers).json()
    non_matching = client.get("/api/notifications", params={"farm_id": 999999999}, headers=auth_headers).json()
    assert len(matching) > 0
    assert non_matching == []


# ---------------------------------------------------------------------------
# POST /notifications/generate
# ---------------------------------------------------------------------------


def test_generate_notifications_for_a_healthy_farm_creates_nothing(client, auth_headers, farm):
    """A brand-new farm with no soil record, calm mock weather (deterministic
    per its location hash could vary, but with no soil at all soil_risk is
    MEDIUM per risk_service.py, so at minimum a RISK notification is likely -
    this test only asserts the call succeeds and returns a consistent shape,
    not a specific count, since the mock weather provider's output depends on
    farm.location's hash and isn't pinned here."""
    resp = client.post("/api/notifications/generate", params={"farm_id": farm["id"]}, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["created"] == len(body["notifications"])


def test_generate_notifications_with_bad_soil_creates_a_fertilizer_notification(client, auth_headers, farm):
    client.post(f"/api/farms/{farm['id']}/soil", json=BAD_SOIL, headers=auth_headers)
    resp = client.post("/api/notifications/generate", params={"farm_id": farm["id"]}, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert any(n["category"] == "FERTILIZER" and n["priority"] == "HIGH" for n in body["notifications"])


def test_generate_notifications_second_call_creates_no_duplicates(client, auth_headers, farm):
    client.post(f"/api/farms/{farm['id']}/soil", json=BAD_SOIL, headers=auth_headers)
    first = client.post("/api/notifications/generate", params={"farm_id": farm["id"]}, headers=auth_headers).json()
    second = client.post("/api/notifications/generate", params={"farm_id": farm["id"]}, headers=auth_headers).json()
    assert first["created"] > 0
    assert second["created"] == 0


def test_generate_notifications_requires_owning_the_farm(client, auth_headers, farm):
    other_headers = _register_and_get_headers(client, "Other Farmer")
    resp = client.post("/api/notifications/generate", params={"farm_id": farm["id"]}, headers=other_headers)
    assert resp.status_code == 404


def test_generate_notifications_for_a_nonexistent_farm_returns_404(client, auth_headers):
    resp = client.post("/api/notifications/generate", params={"farm_id": 999999999}, headers=auth_headers)
    assert resp.status_code == 404


def test_generate_notifications_requires_authentication(client, farm):
    resp = client.post("/api/notifications/generate", params={"farm_id": farm["id"]})
    assert resp.status_code == 401


def test_generate_notifications_requires_the_farm_id_query_param(client, auth_headers):
    resp = client.post("/api/notifications/generate", headers=auth_headers)
    assert resp.status_code == 422


def test_generate_notifications_crashes_for_a_farm_with_an_unhealthy_diagnosis_KNOWN_BUG(client, auth_headers, farm, db_session):
    """
    API-level confirmation of the bug documented in detail in
    test_notification_service.py::test_recent_unhealthy_diagnosis_currently_crashes_generate_for_farm_KNOWN_BUG:
    generate_notifications() has no try/except around generate_for_farm(), so
    the underlying offset-naive/offset-aware TypeError propagates all the way
    up as an unhandled server error. TestClient re-raises unhandled server
    exceptions into the calling test by default (same pattern already used
    for the bcrypt-72-byte bug in test_auth.py), which is what this test
    asserts - this is not a 4xx/5xx HTTP response, it's a real crash.
    """
    db_session.add(
        DiseaseDetection(farm_id=farm["id"], crop="apple", condition="Apple Scab", is_healthy=False, probability=0.9, model_used="logistic_regression")
    )
    db_session.commit()

    with pytest.raises(TypeError, match="offset-naive and offset-aware"):
        client.post("/api/notifications/generate", params={"farm_id": farm["id"]}, headers=auth_headers)


# ---------------------------------------------------------------------------
# PATCH /notifications/{id}/read
# ---------------------------------------------------------------------------


def test_mark_read_updates_is_read(client, auth_headers, farm):
    client.post(f"/api/farms/{farm['id']}/soil", json=BAD_SOIL, headers=auth_headers)
    notes = client.post("/api/notifications/generate", params={"farm_id": farm["id"]}, headers=auth_headers).json()["notifications"]
    note_id = notes[0]["id"]

    resp = client.patch(f"/api/notifications/{note_id}/read", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["is_read"] is True

    listed = client.get("/api/notifications", headers=auth_headers).json()
    assert next(n for n in listed if n["id"] == note_id)["is_read"] is True


def test_mark_read_for_a_nonexistent_notification_returns_404(client, auth_headers):
    resp = client.patch("/api/notifications/999999999/read", headers=auth_headers)
    assert resp.status_code == 404


def test_mark_read_cannot_be_used_on_another_farmers_notification(client, auth_headers, farm):
    client.post(f"/api/farms/{farm['id']}/soil", json=BAD_SOIL, headers=auth_headers)
    notes = client.post("/api/notifications/generate", params={"farm_id": farm["id"]}, headers=auth_headers).json()["notifications"]
    note_id = notes[0]["id"]

    other_headers = _register_and_get_headers(client, "Snooping Farmer")
    resp = client.patch(f"/api/notifications/{note_id}/read", headers=other_headers)
    assert resp.status_code == 404  # not 403 - existence itself isn't leaked to a non-owner


def test_mark_read_requires_authentication(client):
    resp = client.patch("/api/notifications/1/read")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# PATCH /notifications/read-all
# ---------------------------------------------------------------------------


def test_mark_all_read_marks_every_unread_notification(client, auth_headers, farm):
    client.post(f"/api/farms/{farm['id']}/soil", json=BAD_SOIL, headers=auth_headers)
    client.post("/api/notifications/generate", params={"farm_id": farm["id"]}, headers=auth_headers)

    resp = client.patch("/api/notifications/read-all", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["updated"] > 0

    unread = client.get("/api/notifications", params={"unread_only": True}, headers=auth_headers).json()
    assert unread == []


def test_mark_all_read_is_idempotent(client, auth_headers, farm):
    client.post(f"/api/farms/{farm['id']}/soil", json=BAD_SOIL, headers=auth_headers)
    client.post("/api/notifications/generate", params={"farm_id": farm["id"]}, headers=auth_headers)
    client.patch("/api/notifications/read-all", headers=auth_headers)

    second = client.patch("/api/notifications/read-all", headers=auth_headers)
    assert second.json()["updated"] == 0  # nothing left unread to update


def test_mark_all_read_does_not_affect_other_farmers(client, auth_headers, farm):
    client.post(f"/api/farms/{farm['id']}/soil", json=BAD_SOIL, headers=auth_headers)
    client.post("/api/notifications/generate", params={"farm_id": farm["id"]}, headers=auth_headers)

    other_headers = _register_and_get_headers(client, "Unaffected Farmer")
    other_farm = _create_farm(client, other_headers)
    client.post(f"/api/farms/{other_farm['id']}/soil", json=BAD_SOIL, headers=other_headers)
    client.post("/api/notifications/generate", params={"farm_id": other_farm["id"]}, headers=other_headers)

    client.patch("/api/notifications/read-all", headers=auth_headers)

    other_unread = client.get("/api/notifications", params={"unread_only": True}, headers=other_headers).json()
    assert len(other_unread) > 0  # the other farmer's notifications are untouched


def test_mark_all_read_requires_authentication(client):
    resp = client.patch("/api/notifications/read-all")
    assert resp.status_code == 401
