"""
Unit-level tests for app/services/assistant_service.py's internal helpers -
_guess_state, _extract_crop, _classify, _explanation_narrative, and the
"hi"/"hello" farm-guard bypass in answer_question(). Complements
test_assistant.py, which tests the same module through the real
/api/assistant/ask endpoint with real farm/soil/prediction data.
"""

from unittest.mock import MagicMock

from app.services import assistant_service as asvc
from app.services.assistant_service import (
    _classify,
    _explanation_narrative,
    _extract_crop,
    _guess_state,
    _handle_market,
    answer_question,
)


# ---------------------------------------------------------------------------
# _guess_state
# ---------------------------------------------------------------------------


def test_guess_state_finds_a_matching_state_case_insensitively():
    assert _guess_state("Nashik, Maharashtra", ["Maharashtra", "Kerala"]) == "Maharashtra"
    assert _guess_state("nashik, MAHARASHTRA", ["Maharashtra"]) == "Maharashtra"


def test_guess_state_returns_none_when_no_state_matches():
    assert _guess_state("Somewhere Unknown", ["Maharashtra", "Kerala"]) is None


def test_guess_state_returns_none_for_an_empty_states_list():
    assert _guess_state("Nashik, Maharashtra", []) is None


# ---------------------------------------------------------------------------
# _extract_crop
# ---------------------------------------------------------------------------


def test_extract_crop_finds_a_crop_named_in_the_message():
    assert _extract_crop("how much fertilizer does rice need", ["rice", "maize"]) == "rice"


def test_extract_crop_returns_none_when_no_known_crop_is_mentioned():
    assert _extract_crop("how much fertilizer do I need", ["rice", "maize"]) is None


def test_extract_crop_prefers_the_longest_match():
    """'mungbean' contains no shorter crop name as a substring here, but this
    documents the longest-match tie-breaking rule directly: if the message
    mentions both a short and a longer crop name, the longer one wins."""
    assert _extract_crop("is this good for mungbean or bean", ["bean", "mungbean"]) == "mungbean"


# ---------------------------------------------------------------------------
# _classify
# ---------------------------------------------------------------------------


def test_classify_weather_intent():
    assert _classify("what's the weather like today") == "weather"


def test_classify_greeting_intent():
    assert _classify("hello") == "greeting"


def test_classify_why_recommended_requires_crop_or_recommend_keyword():
    assert _classify("why was this crop recommended") == "why_recommended"
    assert _classify("why is it raining") != "why_recommended"  # "why" alone isn't enough


def test_classify_falls_back_when_nothing_matches():
    assert _classify("asdkjaskdj random gibberish") == "fallback"


# ---------------------------------------------------------------------------
# _explanation_narrative - the "no prediction" branch is dead code today
# ---------------------------------------------------------------------------


def test_explanation_narrative_returns_none_without_a_prediction():
    """
    _explanation_narrative()'s own `if not prediction: return None` guard is
    currently unreachable through the real call graph: its only caller,
    _handle_why_recommended(), already checks `if not prediction` and returns
    early *before* ever calling _explanation_narrative() - so in practice
    this function is never invoked with a missing prediction. Tested
    directly here so the function's own contract is verified regardless of
    how its (sole) current caller happens to use it.
    """
    assert _explanation_narrative({"latest_prediction": None}) is None
    assert _explanation_narrative({}) is None


def test_explanation_narrative_returns_none_when_explain_prediction_fails(monkeypatch):
    prediction = MagicMock()
    prediction.input_json = {"nitrogen": 90}
    prediction.top_crop = "rice"

    from app.services.ml_service import ModelUnavailableError

    def boom(_payload, _crop):
        raise ModelUnavailableError("model unavailable")

    monkeypatch.setattr(asvc, "explain_prediction", boom)
    assert _explanation_narrative({"latest_prediction": prediction}) is None


# ---------------------------------------------------------------------------
# _handle_market - the "price not found" branch is dead code today
# ---------------------------------------------------------------------------


def test_handle_market_price_not_found_branch(monkeypatch):
    """
    Documents that market_price_service.get_current_price(crop, state) can
    only realistically return found=False here if `state` came from
    list_states(crop) but the exact crop+state combo has no snapshot row -
    which can't happen, since list_states() only returns states that DO have
    at least one row for that crop (the same query get_current_price then
    re-runs with no extra filters). This branch is therefore effectively
    unreachable through the real call graph too - tested directly by forcing
    get_current_price() to disagree with list_states(), purely to verify the
    handler's own defensive correctness.
    """
    farm = MagicMock()
    farm.location = "Nashik, Maharashtra"
    context = {"farm": farm, "top_crops": [], "latest_prediction": None}

    monkeypatch.setattr(asvc.market_price_service, "list_states", lambda _db, _crop: ["Maharashtra"])
    monkeypatch.setattr(asvc.market_price_service, "get_current_price", lambda _db, _crop, _state: {"found": False, "reason": "no data after all"})

    answer, used_data = _handle_market(MagicMock(), "what's the price of rice", context, ["rice"])
    assert answer == "no data after all"
    assert used_data == []


# ---------------------------------------------------------------------------
# The "hi"/"hello" farm-guard bypass - a fixed bug, regression-tested below
# ---------------------------------------------------------------------------


def _no_farm_context():
    farmer = MagicMock()
    farmer.name = "Test Farmer"
    return {"farm": None, "farmer": farmer}


def test_farm_guard_correctly_blocks_a_message_with_no_hi_substring():
    context = _no_farm_context()
    answer, used_data = answer_question(MagicMock(), "is my farm at risk", context, [])
    assert "please select a farm above first" in answer.lower()
    assert used_data == []


def test_farm_guard_uses_whole_word_matching_not_bypassed_by_hi_substring():
    """
    Regression test for a fixed bug: answer_question()'s "no farm selected"
    guard is meant to let real greetings ("hi", "hello", "hey") through even
    without a farm. It used to do this with a plain substring check
    (`"hi" not in message.lower()`), so any message containing "hi" ANYWHERE
    - "high", "this", "which", "history", "think", "shirt" - silently
    bypassed the intended block. The guard now matches "hi"/"hello"/"hey" as
    whole words only (`\\b(hi|hello|hey)\\b`), so these non-greeting messages
    correctly hit the guard, while real greetings still pass through.
    """
    context = _no_farm_context()

    # None of these are greetings, but each contains "hi" as a substring -
    # the guard must not be fooled by that anymore.
    non_greeting_messages = [
        "why is my risk high",
        "what should I check before irrigation this week",
        "what's the weather this week",
    ]
    for message in non_greeting_messages:
        answer, used_data = answer_question(MagicMock(), message, context, [])
        assert "please select a farm above first" in answer.lower(), (
            f"expected the global guard to fire for {message!r}, but it was bypassed"
        )
        assert used_data == []

    # Real greetings (whole-word "hi"/"hello"/"hey") still bypass the guard.
    for greeting in ["hi", "hello", "hey", "hi there, why is the sky blue"]:
        answer, _used_data = answer_question(MagicMock(), greeting, context, [])
        assert "please select a farm above first" not in answer.lower(), (
            f"expected the guard to be bypassed for real greeting {greeting!r}"
        )
