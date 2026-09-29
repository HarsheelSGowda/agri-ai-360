"""
Tests for the AI Agriculture Assistant (Feature 9 / Phase 2D).

The assistant is a rule-based Q&A engine grounded in real per-farm data, not
an LLM. These tests verify: (1) it never fabricates an answer when the
underlying data doesn't exist yet, (2) it correctly reuses real data once it
does exist, and (3) chat history persists and can be reset.

See also test_assistant_service.py for unit-level tests of the internal
helpers (_guess_state, _extract_crop, _classify) and a documented bug in the
"no farm selected" guard.
"""

from datetime import date

SOIL_PAYLOAD = {
    "nitrogen": 90,
    "phosphorus": 42,
    "potassium": 43,
    "ph": 6.5,
    "soil_type": "Loamy",
    "organic_carbon": 0.6,
    "moisture": 20,
}

CROP_INPUT = {
    "nitrogen": 90,
    "phosphorus": 42,
    "potassium": 43,
    "temperature": 25,
    "humidity": 80,
    "ph": 6.5,
    "rainfall": 200,
}


def ask(client, headers, message, farm_id=None):
    payload = {"message": message}
    if farm_id is not None:
        payload["farm_id"] = farm_id
    resp = client.post("/api/assistant/ask", json=payload, headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_ask_without_farm_asks_to_select_one(client, auth_headers):
    body = ask(client, auth_headers, "why is my risk high")
    assert "select a farm" in body["reply"]["content"].lower()
    assert body["used_data"] == []


def test_greeting_without_farm_is_still_friendly(client, auth_headers):
    body = ask(client, auth_headers, "hello")
    assert "hello" in body["reply"]["content"].lower()


def test_which_crop_before_any_prediction_says_so_honestly(client, auth_headers, farm):
    body = ask(client, auth_headers, "which crop is suitable for my soil?", farm["id"])
    assert "haven't run a crop recommendation" in body["reply"]["content"].lower()
    assert body["used_data"] == []


def test_soil_meaning_before_any_soil_record_says_so_honestly(client, auth_headers, farm):
    body = ask(client, auth_headers, "what does my soil condition mean?", farm["id"])
    assert "haven't submitted a soil record" in body["reply"]["content"].lower()


def test_disease_before_any_scan_says_so_honestly(client, auth_headers, farm):
    body = ask(client, auth_headers, "is there any disease on my leaves?", farm["id"])
    assert "no leaf image has been analyzed" in body["reply"]["content"].lower()


def test_full_flow_uses_real_soil_and_prediction_data(client, auth_headers, farm):
    resp = client.post(f"/api/farms/{farm['id']}/soil", json=SOIL_PAYLOAD, headers=auth_headers)
    assert resp.status_code == 201, resp.text

    resp = client.post("/api/predict/crop", json={**CROP_INPUT, "farm_id": farm["id"]}, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    top_crop = resp.json()["top_crops"][0]["crop"]

    body = ask(client, auth_headers, "which crop is suitable for my soil?", farm["id"])
    assert top_crop.lower() in body["reply"]["content"].lower()
    assert "Latest crop recommendation" in body["used_data"]

    body = ask(client, auth_headers, "why was this crop recommended?", farm["id"])
    content = body["reply"]["content"].lower()
    assert top_crop.lower() in content

    body = ask(client, auth_headers, "what does my soil condition mean?", farm["id"])
    assert "soil health score" in body["reply"]["content"].lower()

    body = ask(client, auth_headers, "how can i improve my soil?", farm["id"])
    assert "score" in body["reply"]["content"].lower()

    body = ask(client, auth_headers, "what should i check before irrigation?", farm["id"])
    assert "irrigation" in body["reply"]["content"].lower()

    # Fertilizer/market questions must not error even when reference data may not cover this crop/state.
    body = ask(client, auth_headers, "any fertilizer advice for my crop?", farm["id"])
    assert body["reply"]["content"]

    body = ask(client, auth_headers, "what's the market price for my crop?", farm["id"])
    assert body["reply"]["content"]


def test_unmatched_question_gives_honest_fallback(client, auth_headers, farm):
    body = ask(client, auth_headers, "asdkjaskdj random gibberish query", farm["id"])
    assert "rule-based assistant" in body["reply"]["content"].lower()


def test_history_persists_across_requests(client, auth_headers, farm):
    ask(client, auth_headers, "hello", farm["id"])
    resp = client.get("/api/assistant/messages", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["session_id"] is not None
    assert len(body["messages"]) == 2
    assert body["messages"][0]["role"] == "farmer"
    assert body["messages"][1]["role"] == "ai"


def test_reset_starts_a_new_empty_session(client, auth_headers, farm):
    ask(client, auth_headers, "hello", farm["id"])
    resp = client.post("/api/assistant/reset", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["messages"] == []

    resp = client.get("/api/assistant/messages", headers=auth_headers)
    assert resp.json()["session_id"] == body["session_id"]
    assert resp.json()["messages"] == []


# ---------------------------------------------------------------------------
# Additional real-data branches not exercised above
# ---------------------------------------------------------------------------


def test_why_recommended_before_any_prediction_says_so_honestly(client, auth_headers, farm):
    body = ask(client, auth_headers, "why was this crop recommended?", farm["id"])
    assert "no crop recommendation has been run" in body["reply"]["content"].lower()


def test_soil_improve_before_any_soil_record_says_so_honestly(client, auth_headers, farm):
    body = ask(client, auth_headers, "how can i improve my soil?", farm["id"])
    assert "haven't submitted a soil record" in body["reply"]["content"].lower()


def test_risk_question_with_a_farm_selected_returns_the_real_breakdown(client, auth_headers, farm):
    body = ask(client, auth_headers, "is my farm at risk", farm["id"])  # no "hi" substring - hits the real risk handler cleanly
    content = body["reply"]["content"].lower()
    assert "overall risk for this farm is" in content
    assert "prototype risk signal" in content
    assert "Risk assessment" in body["used_data"]


def test_weather_question_with_a_farm_selected(client, auth_headers, farm):
    body = ask(client, auth_headers, "what's the weather like today", farm["id"])
    content = body["reply"]["content"].lower()
    assert "current conditions near" in content
    assert "no live weather api key configured" in content
    assert "Weather (mock provider)" in body["used_data"]


def test_irrigation_question_without_any_soil_moisture_reading(client, auth_headers, farm):
    """No soil record at all -> the irrigation handler's own 'no moisture
    reading on file' branch, distinct from the SOIL_PAYLOAD-with-moisture
    case already covered in test_full_flow_uses_real_soil_and_prediction_data."""
    body = ask(client, auth_headers, "is my farm at risk of water stress, should I irrigate", farm["id"])
    assert "no soil moisture reading is on file" in body["reply"]["content"].lower()


def test_disease_question_after_a_real_diagnosis_reports_it(client, auth_headers, farm, db_session):
    from app.models.disease import DiseaseDetection

    db_session.add(
        DiseaseDetection(farm_id=farm["id"], crop="apple", condition="Apple Scab", is_healthy=False, probability=0.9, model_used="disease_logistic_regression")
    )
    db_session.commit()

    body = ask(client, auth_headers, "any disease detected on my leaves", farm["id"])
    content = body["reply"]["content"].lower()
    assert "apple" in content
    assert "apple scab" in content
    assert "90%" in content
    assert "Latest disease detection" in body["used_data"]


def test_fertilizer_question_without_any_soil_record_says_so_honestly(client, auth_headers, farm):
    body = ask(client, auth_headers, "any fertilizer advice for my crop?", farm["id"])
    assert "haven't submitted a soil record" in body["reply"]["content"].lower()


def test_fertilizer_question_with_soil_but_no_crop_mentioned_or_predicted(client, auth_headers, farm):
    client.post(f"/api/farms/{farm['id']}/soil", json=SOIL_PAYLOAD, headers=auth_headers)
    body = ask(client, auth_headers, "any fertilizer advice for my crop?", farm["id"])
    assert "tell me which crop" in body["reply"]["content"].lower()


def test_fertilizer_crop_name_extraction_requires_market_price_data_KNOWN_BEHAVIOR(client, auth_headers, farm):
    """
    Documents a real, non-obvious coupling (not a crash, not fixed here):
    the assistant router builds `known_crops` from
    market_price_service.list_crops(db) - the ~6 crops that happen to have
    seeded Agmarknet price data - NOT the full 22-crop recommendation-engine
    vocabulary. So _extract_crop() can only recognize a crop name typed into
    a fertilizer question if that crop also happens to have market price
    data loaded. With an empty market_prices table (a plausible real state
    if the seed script hasn't been run), asking about "rice" here fails to
    extract "rice" at all and falls through to the "tell me which crop"
    fallback, even though rice is a perfectly normal recommendation-engine
    crop with its own fertilizer thresholds.
    """
    client.post(f"/api/farms/{farm['id']}/soil", json=SOIL_PAYLOAD, headers=auth_headers)
    body = ask(client, auth_headers, "any fertilizer advice for rice?", farm["id"])
    assert "tell me which crop" in body["reply"]["content"].lower()


def test_fertilizer_question_with_deficient_soil_names_the_deficiency(client, auth_headers, farm, db_session):
    """Same scenario as the KNOWN_BEHAVIOR test above, but with rice's market
    price data seeded first (as market_question_with_real_price_data_reports_it
    does) so crop extraction succeeds and the actual deficiency-naming branch
    can be exercised."""
    from app.models.market_price import MarketPrice

    db_session.query(MarketPrice).delete()
    db_session.add(
        MarketPrice(
            crop="rice", state="Maharashtra", district="Nashik", market="Nashik APMC", variety="Common",
            min_price=1900, max_price=2100, modal_price=2000, price_date=date(2016, 1, 10),
        )
    )
    db_session.commit()

    deficient_soil = {**SOIL_PAYLOAD, "nitrogen": 10}  # below the 40 optimal-low threshold
    client.post(f"/api/farms/{farm['id']}/soil", json=deficient_soil, headers=auth_headers)
    body = ask(client, auth_headers, "any fertilizer advice for rice?", farm["id"])
    content = body["reply"]["content"].lower()
    assert "deficient in" in content
    assert "nitrogen" in content

    db_session.query(MarketPrice).delete()
    db_session.commit()


def test_market_question_without_soil_prediction_or_named_crop(client, auth_headers, farm):
    body = ask(client, auth_headers, "what's the market price for my crop?", farm["id"])
    assert "tell me which crop" in body["reply"]["content"].lower()


def test_market_question_with_real_price_data_reports_it(client, auth_headers, farm, db_session):
    """
    Seeds a real MarketPrice row for rice in Maharashtra (matching the real
    `farm` fixture's location) so _guess_state() actually finds a match and
    the full price-lookup success path runs end to end - not just the "no
    market data" fallback the other market tests exercise.
    """
    from app.models.market_price import MarketPrice

    db_session.query(MarketPrice).delete()
    db_session.commit()
    db_session.add(
        MarketPrice(
            crop="rice", state="Maharashtra", district="Nashik", market="Nashik APMC", variety="Common",
            min_price=1900, max_price=2100, modal_price=2000, price_date=date(2016, 1, 10),
        )
    )
    db_session.commit()

    body = ask(client, auth_headers, "what's the market price for rice?", farm["id"])
    content = body["reply"]["content"].lower()
    assert "2000" in content or "2000.0" in content
    assert "maharashtra" in content
    assert "historical reference data" in content
    assert "Market price data" in body["used_data"]

    db_session.query(MarketPrice).delete()
    db_session.commit()


def test_why_recommended_falls_back_honestly_when_shap_explanation_is_unavailable(client, auth_headers, farm, monkeypatch):
    """Covers the branch where a prediction exists but explain_prediction()
    fails - the assistant must say so rather than fabricate a narrative."""
    from app.services import assistant_service as asvc
    from app.services.ml_service import ModelUnavailableError

    client.post(f"/api/farms/{farm['id']}/soil", json=SOIL_PAYLOAD, headers=auth_headers)
    client.post("/api/predict/crop", json={**CROP_INPUT, "farm_id": farm["id"]}, headers=auth_headers)

    def boom(_payload, _crop):
        raise ModelUnavailableError("explanation unavailable")

    monkeypatch.setattr(asvc, "explain_prediction", boom)
    body = ask(client, auth_headers, "why was this crop recommended?", farm["id"])
    assert "couldn't regenerate the" in body["reply"]["content"].lower()


def test_get_messages_before_ever_asking_anything_returns_no_session(client, auth_headers):
    resp = client.get("/api/assistant/messages", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == {"session_id": None, "messages": []}


def test_ask_with_a_farm_id_not_owned_by_the_farmer_returns_404(client, auth_headers):
    resp = client.post("/api/assistant/ask", json={"message": "hello", "farm_id": 999999999}, headers=auth_headers)
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Farm not found"
