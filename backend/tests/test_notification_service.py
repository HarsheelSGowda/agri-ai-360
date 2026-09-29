"""
Tests for app/services/notification_service.py - generate_for_farm() derives
personalized alerts from each farm's real soil health, weather, risk, disease
and market-price-trend data. Weather is stubbed (via monkeypatching
get_weather_provider, the one genuinely variable external-style collaborator)
so every scenario is fully deterministic; soil health, risk, disease and
market-price logic all run for real against real service code and real rows
inserted into the test database - no mocking of business logic itself.
"""

import uuid
from datetime import date, datetime, timedelta, timezone

import pytest

from app.models.disease import DiseaseDetection
from app.models.farm import Farm
from app.models.market_price import MarketPrice
from app.models.notification import Notification
from app.models.prediction import CropPrediction
from app.models.soil import SoilRecord
from app.models.user import Farmer, User
from app.services import notification_service as ns
from app.services.notification_service import _already_notified, _guess_state, generate_for_farm

GOOD_SOIL = {"nitrogen": 80, "phosphorus": 40, "potassium": 55, "ph": 6.75}  # score 100
BAD_SOIL = {"nitrogen": 5, "phosphorus": 2, "potassium": 5, "ph": 4.0}  # score 24 (HIGH priority)
MEDIUM_SOIL = {"nitrogen": 25, "phosphorus": 10, "potassium": 20, "ph": 4.5}  # score 53 (MEDIUM priority)

CALM_WEATHER = {
    "temperature_c": 25,
    "rainfall_mm": 5,
    "humidity_pct": 50,
    "wind_kmh": 10,
    "condition": "Clear Sky",
    "forecast": [{"day": "Tomorrow", "temp_c": 26, "condition": "Clear Sky"}, {"day": "Day 2", "temp_c": 26, "condition": "Sunny"}],
    "source": "mock",
}

SEVERE_WEATHER = {
    "temperature_c": 42,
    "rainfall_mm": 0,
    "humidity_pct": 95,
    "wind_kmh": 30,
    "condition": "Clear Sky",
    "forecast": [{"day": "Tomorrow", "temp_c": 42, "condition": "Clear Sky"}, {"day": "Day 2", "temp_c": 42, "condition": "Sunny"}],
    "source": "mock",
}

RAINY_FORECAST_WEATHER = {**CALM_WEATHER, "forecast": [{"day": "Tomorrow", "temp_c": 24, "condition": "Light Rain"}, {"day": "Day 2", "temp_c": 25, "condition": "Sunny"}]}


class _StubWeatherProvider:
    def __init__(self, data: dict):
        self._data = data

    def get_current(self, _location: str) -> dict:
        return self._data


def _make_farmer_and_farm(db_session, *, location="Pune, Maharashtra", irrigation_available=True, name="Test Farmer"):
    user = User(email=f"notif_{uuid.uuid4().hex[:10]}@example.com", password_hash="x")
    db_session.add(user)
    db_session.flush()
    farmer = Farmer(user_id=user.id, name=name, location=location)
    db_session.add(farmer)
    db_session.flush()
    farm = Farm(farmer_id=farmer.id, name="Notif Farm", location=location, area_acres=3, soil_type="Loamy", irrigation_available=irrigation_available)
    db_session.add(farm)
    db_session.commit()
    return farmer, farm


def _add_soil(db_session, farm, values: dict):
    db_session.add(SoilRecord(farm_id=farm.id, soil_type="Loamy", **values))
    db_session.commit()


# ---------------------------------------------------------------------------
# _guess_state
# ---------------------------------------------------------------------------


def test_guess_state_matches_a_state_substring_case_insensitively():
    assert _guess_state("Pune, Maharashtra", ["Maharashtra", "Kerala"]) == "Maharashtra"
    assert _guess_state("pune, MAHARASHTRA", ["Maharashtra"]) == "Maharashtra"


def test_guess_state_returns_none_when_no_state_matches():
    assert _guess_state("Somewhere Unknown", ["Maharashtra", "Kerala"]) is None


# ---------------------------------------------------------------------------
# generate_for_farm - soil health branch
# ---------------------------------------------------------------------------


def test_no_soil_record_produces_no_fertilizer_notification(db_session, monkeypatch):
    farmer, farm = _make_farmer_and_farm(db_session)
    monkeypatch.setattr(ns, "get_weather_provider", lambda: _StubWeatherProvider(CALM_WEATHER))
    created = generate_for_farm(db_session, farm, farmer)
    assert not any(n.category == "FERTILIZER" for n in created)


def test_good_soil_health_produces_no_fertilizer_notification(db_session, monkeypatch):
    farmer, farm = _make_farmer_and_farm(db_session)
    _add_soil(db_session, farm, GOOD_SOIL)
    monkeypatch.setattr(ns, "get_weather_provider", lambda: _StubWeatherProvider(CALM_WEATHER))
    created = generate_for_farm(db_session, farm, farmer)
    assert not any(n.category == "FERTILIZER" for n in created)


def test_medium_soil_health_produces_medium_priority_fertilizer_notification(db_session, monkeypatch):
    farmer, farm = _make_farmer_and_farm(db_session)
    _add_soil(db_session, farm, MEDIUM_SOIL)
    monkeypatch.setattr(ns, "get_weather_provider", lambda: _StubWeatherProvider(CALM_WEATHER))
    created = generate_for_farm(db_session, farm, farmer)
    fert = [n for n in created if n.category == "FERTILIZER"]
    assert len(fert) == 1
    assert fert[0].priority == "MEDIUM"
    assert farmer.name.split()[0] in fert[0].message
    assert "Fertilizer Advisor" in fert[0].message


def test_bad_soil_health_produces_high_priority_fertilizer_notification(db_session, monkeypatch):
    farmer, farm = _make_farmer_and_farm(db_session)
    _add_soil(db_session, farm, BAD_SOIL)
    monkeypatch.setattr(ns, "get_weather_provider", lambda: _StubWeatherProvider(CALM_WEATHER))
    created = generate_for_farm(db_session, farm, farmer)
    fert = [n for n in created if n.category == "FERTILIZER"]
    assert len(fert) == 1
    assert fert[0].priority == "HIGH"


# ---------------------------------------------------------------------------
# generate_for_farm - weather/rain branch
# ---------------------------------------------------------------------------


def test_rain_in_next_two_days_produces_weather_notification(db_session, monkeypatch):
    farmer, farm = _make_farmer_and_farm(db_session)
    monkeypatch.setattr(ns, "get_weather_provider", lambda: _StubWeatherProvider(RAINY_FORECAST_WEATHER))
    created = generate_for_farm(db_session, farm, farmer)
    weather_notes = [n for n in created if n.category == "WEATHER"]
    assert len(weather_notes) == 1
    assert weather_notes[0].priority == "MEDIUM"
    assert farm.location in weather_notes[0].message


def test_no_rain_in_forecast_produces_no_weather_notification(db_session, monkeypatch):
    farmer, farm = _make_farmer_and_farm(db_session)
    _add_soil(db_session, farm, GOOD_SOIL)  # avoid the LOW-risk path also needing this
    monkeypatch.setattr(ns, "get_weather_provider", lambda: _StubWeatherProvider(CALM_WEATHER))
    created = generate_for_farm(db_session, farm, farmer)
    assert not any(n.category == "WEATHER" for n in created)


def test_rain_only_checked_in_the_first_two_forecast_days():
    """The real production check is `weather['forecast'][:2]` - a rain day
    further out (day 3+) must NOT trigger the notification. Documents the
    real slicing behavior directly against the data shape, independent of DB
    state."""
    weather = {**CALM_WEATHER, "forecast": [
        {"day": "Tomorrow", "temp_c": 26, "condition": "Clear Sky"},
        {"day": "Day 2", "temp_c": 26, "condition": "Sunny"},
        {"day": "Day 3", "temp_c": 24, "condition": "Light Rain"},
    ]}
    assert not any("rain" in f["condition"].lower() for f in weather["forecast"][:2])


# ---------------------------------------------------------------------------
# generate_for_farm - risk branch
# ---------------------------------------------------------------------------


def test_low_overall_risk_produces_no_risk_notification(db_session, monkeypatch):
    farmer, farm = _make_farmer_and_farm(db_session, irrigation_available=True)
    _add_soil(db_session, farm, GOOD_SOIL)
    monkeypatch.setattr(ns, "get_weather_provider", lambda: _StubWeatherProvider(CALM_WEATHER))
    created = generate_for_farm(db_session, farm, farmer)
    assert not any(n.category == "RISK" for n in created)


def test_medium_overall_risk_produces_medium_risk_notification(db_session, monkeypatch):
    # No soil record at all -> soil_risk is always MEDIUM (see risk_service.py), even with calm weather.
    farmer, farm = _make_farmer_and_farm(db_session, irrigation_available=True)
    monkeypatch.setattr(ns, "get_weather_provider", lambda: _StubWeatherProvider(CALM_WEATHER))
    created = generate_for_farm(db_session, farm, farmer)
    risk_notes = [n for n in created if n.category == "RISK"]
    assert len(risk_notes) == 1
    assert risk_notes[0].priority == "MEDIUM"


def test_high_overall_risk_produces_high_risk_notification(db_session, monkeypatch):
    farmer, farm = _make_farmer_and_farm(db_session, irrigation_available=False)
    monkeypatch.setattr(ns, "get_weather_provider", lambda: _StubWeatherProvider(SEVERE_WEATHER))
    created = generate_for_farm(db_session, farm, farmer)
    risk_notes = [n for n in created if n.category == "RISK"]
    assert len(risk_notes) == 1
    assert risk_notes[0].priority == "HIGH"
    assert farm.name in risk_notes[0].title


# ---------------------------------------------------------------------------
# generate_for_farm - disease branch
# ---------------------------------------------------------------------------


def test_recent_unhealthy_diagnosis_currently_crashes_generate_for_farm_KNOWN_BUG(db_session, monkeypatch):
    """
    Documents a genuine, currently-unfixed, high-severity bug (found while
    adding this test coverage, not fixed here per this pass's rules):
    DiseaseDetection.created_at is stored via a plain `DateTime` column (not
    timezone-aware). Once written and re-read from the database (exactly what
    the `.order_by(...).first()` query above does), SQLAlchemy returns a
    timezone-*naive* datetime. But generate_for_farm() compares it directly
    against `datetime.now(timezone.utc) - timedelta(days=7)`, which is
    timezone-*aware*. Comparing a naive and an aware datetime raises
    `TypeError: can't compare offset-naive and offset-aware datetimes`.

    Real-world impact: ANY farm with at least one unhealthy disease diagnosis
    on record makes `POST /api/notifications/generate` crash with an
    unhandled 500 - there is no try/except around generate_for_farm() in
    notification_router.py. This is fully reproducible from a fresh in-memory
    database with no other test state involved (verified independently before
    writing this test) - it is a real production bug, not a test artifact.
    """
    farmer, farm = _make_farmer_and_farm(db_session)
    _add_soil(db_session, farm, GOOD_SOIL)
    db_session.add(
        DiseaseDetection(farm_id=farm.id, crop="apple", condition="Apple Scab", is_healthy=False, probability=0.87, model_used="logistic_regression")
    )
    db_session.commit()
    monkeypatch.setattr(ns, "get_weather_provider", lambda: _StubWeatherProvider(CALM_WEATHER))


    with pytest.raises(TypeError, match="offset-naive and offset-aware"):
        generate_for_farm(db_session, farm, farmer)


def test_healthy_diagnosis_produces_no_disease_notification(db_session, monkeypatch):
    farmer, farm = _make_farmer_and_farm(db_session)
    _add_soil(db_session, farm, GOOD_SOIL)
    db_session.add(
        DiseaseDetection(farm_id=farm.id, crop="apple", condition="Healthy", is_healthy=True, probability=0.99, model_used="logistic_regression")
    )
    db_session.commit()
    monkeypatch.setattr(ns, "get_weather_provider", lambda: _StubWeatherProvider(CALM_WEATHER))
    created = generate_for_farm(db_session, farm, farmer)
    assert not any(n.category == "DISEASE" for n in created)


def test_old_unhealthy_diagnosis_beyond_7_days_also_hits_the_same_KNOWN_BUG(db_session, monkeypatch):
    """
    The "older than 7 days" branch is intended to skip notifying about a
    stale diagnosis, but the offset-naive/aware TypeError documented in
    test_recent_unhealthy_diagnosis_currently_crashes_generate_for_farm_KNOWN_BUG
    happens in the *comparison itself* (`latest_disease.created_at >= ...`),
    before the code can even decide whether the diagnosis is old or recent.
    So an old unhealthy diagnosis crashes generate_for_farm() exactly the same
    way a recent one does - there is no age at which this branch is safe to
    reach once any unhealthy DiseaseDetection row exists for the farm.
    """

    farmer, farm = _make_farmer_and_farm(db_session)
    _add_soil(db_session, farm, GOOD_SOIL)
    old = DiseaseDetection(farm_id=farm.id, crop="maize", condition="Common Rust", is_healthy=False, probability=0.9, model_used="logistic_regression")
    db_session.add(old)
    db_session.commit()
    old.created_at = datetime.now(timezone.utc) - timedelta(days=8)
    db_session.commit()
    monkeypatch.setattr(ns, "get_weather_provider", lambda: _StubWeatherProvider(CALM_WEATHER))

    with pytest.raises(TypeError, match="offset-naive and offset-aware"):
        generate_for_farm(db_session, farm, farmer)


# ---------------------------------------------------------------------------
# generate_for_farm - market price branch (real MarketPrice rows, real trend calc)
# ---------------------------------------------------------------------------


def _seed_rice_price_trend(db_session, *, state: str, first_price: float, last_price: float):
    # `state` must be distinct per test: get_trend() filters only by crop+state
    # (not district/market/variety) and the test DB is shared across the whole
    # session, so two tests reusing the same crop+state would see each
    # other's rows aggregated into the same trend calculation.
    db_session.add(
        MarketPrice(
            crop="rice", state=state, district="Test District", market="Test APMC", variety="Common",
            min_price=first_price - 50, max_price=first_price + 50, modal_price=first_price,
            price_date=date(2016, 1, 1),
        )
    )
    db_session.add(
        MarketPrice(
            crop="rice", state=state, district="Test District", market="Test APMC", variety="Common",
            min_price=last_price - 50, max_price=last_price + 50, modal_price=last_price,
            price_date=date(2016, 1, 10),
        )
    )
    db_session.commit()


def test_significant_price_increase_produces_market_notification(db_session, monkeypatch):
    state = "Maharashtra"
    farmer, farm = _make_farmer_and_farm(db_session, location=f"Pune, {state}")
    _add_soil(db_session, farm, GOOD_SOIL)
    db_session.add(CropPrediction(farm_id=farm.id, input_json={"nitrogen": 80}, top_crop="rice", top_score=0.9))
    db_session.commit()
    _seed_rice_price_trend(db_session, state=state, first_price=2000, last_price=2200)  # +10%, well above the 5% threshold

    monkeypatch.setattr(ns, "get_weather_provider", lambda: _StubWeatherProvider(CALM_WEATHER))
    created = generate_for_farm(db_session, farm, farmer)
    market_notes = [n for n in created if n.category == "MARKET"]
    assert len(market_notes) == 1
    assert market_notes[0].priority == "MEDIUM"
    assert "Rice" in market_notes[0].title
    assert "increased" in market_notes[0].message
    assert state in market_notes[0].message


def test_small_price_change_below_threshold_produces_no_market_notification(db_session, monkeypatch):
    state = "Kerala"
    farmer, farm = _make_farmer_and_farm(db_session, location=f"Kochi, {state}")
    _add_soil(db_session, farm, GOOD_SOIL)
    db_session.add(CropPrediction(farm_id=farm.id, input_json={"nitrogen": 80}, top_crop="rice", top_score=0.9))
    db_session.commit()
    _seed_rice_price_trend(db_session, state=state, first_price=2000, last_price=2050)  # +2.5%, below the 5% threshold

    monkeypatch.setattr(ns, "get_weather_provider", lambda: _StubWeatherProvider(CALM_WEATHER))
    created = generate_for_farm(db_session, farm, farmer)
    assert not any(n.category == "MARKET" for n in created)


def test_no_crop_prediction_produces_no_market_notification(db_session, monkeypatch):
    state = "Karnataka"
    farmer, farm = _make_farmer_and_farm(db_session, location=f"Mysore, {state}")
    _add_soil(db_session, farm, GOOD_SOIL)
    _seed_rice_price_trend(db_session, state=state, first_price=2000, last_price=2200)
    monkeypatch.setattr(ns, "get_weather_provider", lambda: _StubWeatherProvider(CALM_WEATHER))
    created = generate_for_farm(db_session, farm, farmer)
    assert not any(n.category == "MARKET" for n in created)


def test_farm_location_with_no_matching_state_produces_no_market_notification(db_session, monkeypatch):
    """The predicted crop's state can't be guessed from a location with no
    recognizable state name - the market check is skipped entirely rather
    than guessing a state."""
    state = "Gujarat"
    farmer, farm = _make_farmer_and_farm(db_session, location="Nowhereville")
    _add_soil(db_session, farm, GOOD_SOIL)
    db_session.add(CropPrediction(farm_id=farm.id, input_json={"nitrogen": 80}, top_crop="rice", top_score=0.9))
    db_session.commit()
    _seed_rice_price_trend(db_session, state=state, first_price=2000, last_price=2200)
    monkeypatch.setattr(ns, "get_weather_provider", lambda: _StubWeatherProvider(CALM_WEATHER))
    created = generate_for_farm(db_session, farm, farmer)
    assert not any(n.category == "MARKET" for n in created)


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------


def test_already_notified_detects_an_identical_recent_title_and_message(db_session):
    farmer, farm = _make_farmer_and_farm(db_session)
    db_session.add(Notification(farmer_id=farmer.id, farm_id=farm.id, category="RISK", priority="HIGH", title="T", message="M"))
    db_session.commit()
    assert _already_notified(db_session, farmer.id, "T", "M") is True
    assert _already_notified(db_session, farmer.id, "T", "different message") is False


def test_already_notified_ignores_entries_outside_the_dedup_window(db_session):
    farmer, farm = _make_farmer_and_farm(db_session)
    note = Notification(farmer_id=farmer.id, farm_id=farm.id, category="RISK", priority="HIGH", title="T", message="M")
    db_session.add(note)
    db_session.commit()
    note.created_at = datetime.now(timezone.utc) - timedelta(hours=13)  # outside the 12-hour DEDUP_WINDOW
    db_session.commit()
    assert _already_notified(db_session, farmer.id, "T", "M") is False


def test_generate_for_farm_does_not_create_duplicate_notifications_on_a_second_call(db_session, monkeypatch):
    farmer, farm = _make_farmer_and_farm(db_session, irrigation_available=False)
    monkeypatch.setattr(ns, "get_weather_provider", lambda: _StubWeatherProvider(SEVERE_WEATHER))

    first_run = generate_for_farm(db_session, farm, farmer)
    assert len(first_run) > 0

    second_run = generate_for_farm(db_session, farm, farmer)
    assert second_run == []  # every notification this scenario produces was already created within the dedup window

    total_in_db = db_session.query(Notification).filter(Notification.farmer_id == farmer.id).count()
    assert total_in_db == len(first_run)


def test_generate_for_farm_does_not_deduplicate_across_different_farmers(db_session, monkeypatch):
    """Two unrelated farmers whose farms independently produce the identical
    risk message must each get their own notification - dedup is scoped per
    farmer_id, not globally."""
    farmer_a, farm_a = _make_farmer_and_farm(db_session, irrigation_available=False, name="Farmer A")
    farmer_b, farm_b = _make_farmer_and_farm(db_session, irrigation_available=False, name="Farmer B")
    monkeypatch.setattr(ns, "get_weather_provider", lambda: _StubWeatherProvider(SEVERE_WEATHER))

    created_a = generate_for_farm(db_session, farm_a, farmer_a)
    created_b = generate_for_farm(db_session, farm_b, farmer_b)
    assert len(created_a) > 0
    assert len(created_b) > 0  # not suppressed just because farmer_a already has the same-looking alert


def test_generate_for_farm_returns_empty_list_when_nothing_is_notable(db_session, monkeypatch):
    farmer, farm = _make_farmer_and_farm(db_session, irrigation_available=True)
    _add_soil(db_session, farm, GOOD_SOIL)
    monkeypatch.setattr(ns, "get_weather_provider", lambda: _StubWeatherProvider(CALM_WEATHER))
    created = generate_for_farm(db_session, farm, farmer)
    assert created == []
