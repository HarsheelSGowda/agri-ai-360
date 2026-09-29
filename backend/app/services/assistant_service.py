"""
AI Agriculture Assistant (Phase 2D) - rule-based fallback, not an LLM.

No language-model API key is configured for this project (see
backend/.env.example - there is no ANTHROPIC_API_KEY/OPENAI_API_KEY etc.).
Per the project's no-fabrication rule, this assistant does NOT pretend to be
an LLM: it is a transparent, deterministic keyword-classified Q&A engine that
answers using the exact same real data every other module already computes
(soil health, weather, risk, disease diagnosis, fertilizer guidance, market
price, crop-recommendation SHAP explanation). It never invents an answer it
doesn't have grounded data for - if the underlying data is missing, it says
so and points the farmer to the page that would generate it.

If a real LLM/RAG API is wired up in the future, `answer_question()` is the
single call site the router depends on - swap its body for an LLM call
grounded on the same `gather_context()` payload without touching the router.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.disease import DiseaseDetection
from app.models.farm import Farm
from app.models.prediction import CropPrediction, CropScore
from app.models.soil import SoilRecord
from app.models.user import Farmer
from app.services import market_price_service
from app.services.fertilizer_service import GROWTH_STAGE_GUIDANCE, recommend_fertilizer
from app.services.ml_service import ModelUnavailableError, explain_prediction
from app.services.risk_service import compute_risk
from app.services.soil_health import compute_soil_health
from app.services.weather_provider import get_weather_provider

DEFAULT_GROWTH_STAGE = "vegetative"

SUGGESTED_QUESTIONS = [
    "Which crop is suitable for my soil?",
    "Why was this crop recommended?",
    "What does my soil condition mean?",
    "Why is my risk medium?",
    "How can I improve my soil?",
    "What should I check before irrigation?",
    "What's the market price for my crop?",
    "Any disease detected on my farm?",
]


def _guess_state(location: str, states: list[str]) -> str | None:
    lower = location.lower()
    for state in states:
        if state.lower() in lower:
            return state
    return None


def _extract_crop(message: str, known_crops: list[str]) -> str | None:
    """Longest-match, case-insensitive substring match against known crop names."""
    lower = message.lower()
    matches = [c for c in known_crops if c.lower() in lower]
    if not matches:
        return None
    return max(matches, key=len)


def gather_context(db: Session, farm: Farm | None, farmer: Farmer) -> dict:
    """
    Collect the real, currently-available data for a farm. Any piece can be
    None/missing - handlers below must check before using it, never assume.
    """
    context: dict = {"farm": farm, "farmer": farmer}
    if farm is None:
        return context

    soil = db.query(SoilRecord).filter(SoilRecord.farm_id == farm.id).order_by(SoilRecord.created_at.desc()).first()
    context["soil"] = soil
    context["soil_health"] = compute_soil_health(soil.nitrogen, soil.phosphorus, soil.potassium, soil.ph) if soil else None

    weather = get_weather_provider().get_current(farm.location)
    context["weather"] = weather

    context["risk"] = compute_risk(
        temperature_c=weather["temperature_c"],
        rainfall_mm=weather["rainfall_mm"],
        humidity_pct=weather["humidity_pct"],
        soil_score=context["soil_health"]["score"] if context["soil_health"] else None,
        irrigation_available=farm.irrigation_available,
    )

    latest_prediction = (
        db.query(CropPrediction).filter(CropPrediction.farm_id == farm.id).order_by(CropPrediction.created_at.desc()).first()
    )
    context["latest_prediction"] = latest_prediction
    context["top_crops"] = []
    if latest_prediction:
        scores = (
            db.query(CropScore)
            .filter(CropScore.prediction_id == latest_prediction.id)
            .order_by(CropScore.rank.asc())
            .limit(3)
            .all()
        )
        context["top_crops"] = [{"crop": s.crop, "probability": s.probability} for s in scores]

    context["latest_disease"] = (
        db.query(DiseaseDetection).filter(DiseaseDetection.farm_id == farm.id).order_by(DiseaseDetection.created_at.desc()).first()
    )

    return context


def _explanation_narrative(context: dict) -> str | None:
    prediction: CropPrediction | None = context.get("latest_prediction")
    if not prediction:
        return None
    try:
        result = explain_prediction(prediction.input_json, prediction.top_crop)
    except (ModelUnavailableError, ValueError):
        return None
    return result["narrative"]


def _handle_greeting(_message: str, context: dict) -> tuple[str, list[str]]:
    name = context["farmer"].name.split()[0] if context["farmer"].name else "there"
    farm = context.get("farm")
    if not farm:
        return (
            f"Hello {name}! Select a farm above so I can answer using its real soil, weather and prediction data. "
            "I'm a rule-based assistant, not a general chatbot — I can only answer questions your farm's data supports.",
            [],
        )
    return (
        f"Hello {name}! I can answer questions about {farm.name} using its actual soil, weather, risk, disease, "
        "fertilizer and market data. Try: \"Why was this crop recommended?\" or \"How can I improve my soil?\"",
        [],
    )


def _handle_which_crop(_message: str, context: dict) -> tuple[str, list[str]]:
    top_crops = context.get("top_crops") or []
    if not top_crops:
        return (
            "You haven't run a crop recommendation for this farm yet. Go to Crop Recommendation, enter your soil "
            "and weather values, and I'll be able to tell you which crops the model ranked highest.",
            [],
        )
    lines = ", ".join(f"{c['crop'].title()} ({c['probability'] * 100:.0f}%)" for c in top_crops)
    return (
        f"Based on your most recent crop recommendation run, the top-ranked crops were: {lines}. "
        "These probabilities come from the trained Random Forest/Gradient Boosting model on your submitted soil and weather values.",
        ["Latest crop recommendation"],
    )


def _handle_why_recommended(_message: str, context: dict) -> tuple[str, list[str]]:
    prediction: CropPrediction | None = context.get("latest_prediction")
    if not prediction:
        return (
            "No crop recommendation has been run for this farm yet, so there's nothing to explain. "
            "Run one from the Crop Recommendation page first.",
            [],
        )
    narrative = _explanation_narrative(context)
    if not narrative:
        return (
            f"Your most recent recommendation was {prediction.top_crop.title()}, but I couldn't regenerate the "
            "SHAP explanation right now (the explainability model may be unavailable). Open the recommendation's "
            "detail page to see the full breakdown.",
            ["Latest crop recommendation"],
        )
    return (f"For {prediction.top_crop.title()}: {narrative}", ["Latest crop recommendation", "SHAP explanation"])


def _handle_soil_improve(_message: str, context: dict) -> tuple[str, list[str]]:
    soil_health = context.get("soil_health")
    if not soil_health:
        return (
            "You haven't submitted a soil record for this farm yet. Add one on the Soil Intelligence page and "
            "I'll be able to point out which nutrients need attention.",
            [],
        )
    breakdown = soil_health["breakdown"]
    worst_key = min(breakdown, key=breakdown.get)
    tips = {
        "nitrogen": "Consider a nitrogenous fertilizer (e.g. Urea) and check the Fertilizer Advisor for timing guidance.",
        "phosphorus": "Consider a phosphatic fertilizer (e.g. DAP) as a basal dose, and check soil pH — phosphorus becomes less available in strongly acidic or alkaline soil.",
        "potassium": "Consider a potassic fertilizer (e.g. Muriate of Potash), especially important during flowering/fruiting.",
        "ph": "Soil pH is outside the general optimal band — this affects how well plants can absorb other nutrients regardless of how much fertilizer is applied.",
    }
    return (
        f"Your lowest-scoring soil parameter is {worst_key} (score {breakdown[worst_key]}/100). "
        f"{tips.get(worst_key, '')} For a full nutrient-by-nutrient breakdown with application timing, open the Fertilizer Advisor.",
        ["Soil health score"],
    )


def _handle_soil_meaning(_message: str, context: dict) -> tuple[str, list[str]]:
    soil_health = context.get("soil_health")
    if not soil_health:
        return (
            "You haven't submitted a soil record for this farm yet. Add one on the Soil Intelligence page to get a "
            "soil health score and explanation.",
            [],
        )
    insights = " ".join(soil_health["insights"])
    return (
        f"Your overall soil health score is {soil_health['score']}/100. {insights}",
        ["Soil health score"],
    )


def _handle_risk(_message: str, context: dict) -> tuple[str, list[str]]:
    risk = context.get("risk")
    if not risk:
        return ("Select a farm first — risk is computed from that farm's soil and weather data.", [])
    notes = " ".join(risk["notes"])
    return (
        f"Overall risk for this farm is {risk['overall']}. Breakdown — weather: {risk['weather_risk']}, "
        f"soil: {risk['soil_risk']}, water: {risk['water_risk']}, disease pressure: {risk['disease_risk']}. {notes} "
        "(This is a rule-based prototype risk signal, not a calibrated probability.)",
        ["Risk assessment", "Weather (mock provider)"],
    )


def _handle_irrigation(_message: str, context: dict) -> tuple[str, list[str]]:
    farm: Farm | None = context.get("farm")
    risk = context.get("risk")
    weather = context.get("weather")
    soil = context.get("soil")
    if not farm or not risk or not weather:
        return ("Select a farm first so I can check its irrigation availability, rainfall and water-stress risk.", [])
    parts = [
        f"Irrigation is {'available' if farm.irrigation_available else 'not marked as available'} for {farm.name}.",
        f"Current (mock) weather shows {weather['rainfall_mm']}mm rainfall and {weather['humidity_pct']}% humidity.",
        f"Water-stress risk is currently {risk['water_risk']}.",
    ]
    if soil and soil.moisture is not None:
        parts.append(f"Your last recorded soil moisture reading was {soil.moisture}%.")
    else:
        parts.append("No soil moisture reading is on file — record one for a more precise irrigation check.")
    parts.append("For a numeric estimate, use the Water Requirement page with your crop and growth stage.")
    return (" ".join(parts), ["Risk assessment", "Weather (mock provider)", "Latest soil record"])


def _handle_disease(_message: str, context: dict) -> tuple[str, list[str]]:
    latest = context.get("latest_disease")
    if not latest:
        return (
            "No leaf image has been analyzed for this farm yet. Upload one on the Crop Doctor / Leaf Disease "
            "Detection page and I'll be able to report the result here.",
            [],
        )
    status = "healthy" if latest.is_healthy else f"showing signs of {latest.condition}"
    return (
        f"Your most recent leaf scan ({latest.crop}) was {status}, with {latest.probability * 100:.0f}% model "
        f"confidence ({latest.model_used}). This is an AI prediction and does not replace expert agricultural advice.",
        ["Latest disease detection"],
    )


def _handle_fertilizer(_message: str, context: dict, known_crops: list[str]) -> tuple[str, list[str]]:
    soil = context.get("soil")
    if not soil:
        return (
            "You haven't submitted a soil record for this farm yet. Add one on the Soil Intelligence page — "
            "fertilizer guidance needs your N, P, K and pH values.",
            [],
        )
    crop = _extract_crop(_message, known_crops)
    prediction: CropPrediction | None = context.get("latest_prediction")
    if not crop and prediction:
        crop = prediction.top_crop
    if not crop:
        return (
            "Tell me which crop, or run a crop recommendation first, and I'll check your soil against its nutrient needs.",
            [],
        )
    result = recommend_fertilizer(
        crop=crop,
        nitrogen=soil.nitrogen,
        phosphorus=soil.phosphorus,
        potassium=soil.potassium,
        ph=soil.ph,
        growth_stage=DEFAULT_GROWTH_STAGE,
        organic_carbon=soil.organic_carbon,
        moisture=soil.moisture,
    )
    deficient = [d["nutrient"] for d in result["deficiencies"] if d["status"] == "DEFICIENT"]
    if deficient:
        summary = f"Your soil is deficient in {', '.join(deficient)} for {crop.title()}."
    else:
        summary = f"No nutrient deficiencies detected for {crop.title()} based on your latest soil record."
    return (
        f"{summary} (Assuming {DEFAULT_GROWTH_STAGE} growth stage since none was specified — {GROWTH_STAGE_GUIDANCE[DEFAULT_GROWTH_STAGE].lower()}) "
        f"Open the Fertilizer Advisor for the full breakdown and disclaimer.",
        ["Latest soil record", "Fertilizer recommendation rules"],
    )


def _handle_market(db: Session, _message: str, context: dict, known_crops: list[str]) -> tuple[str, list[str]]:
    farm: Farm | None = context.get("farm")
    crop = _extract_crop(_message, known_crops)
    prediction: CropPrediction | None = context.get("latest_prediction")
    if not crop and prediction:
        crop = prediction.top_crop
    if not crop or not farm:
        return ("Tell me which crop you're asking about, or run a crop recommendation first so I know which crop to check.", [])

    states = market_price_service.list_states(db, crop)
    state = _guess_state(farm.location, states)
    if not state:
        return (
            f"I don't have market price data for {crop.title()} near {farm.location}. Try the Market Prices page "
            "and pick a state directly — coverage is historical Agmarknet data for a limited set of crops/states.",
            [],
        )
    price = market_price_service.get_current_price(db, crop, state)
    if not price["found"]:
        return (price["reason"], [])
    return (
        f"Latest recorded price for {crop.title()} in {state} (as of {price['as_of_date']}, {price['markets_reporting']} "
        f"market(s) reporting): ₹{price['modal_price']}/quintal modal, range ₹{price['min_price']}–₹{price['max_price']}. "
        f"Source: {price['source']} — this is historical reference data, not a live feed.",
        ["Market price data"],
    )


def _handle_fallback(_message: str, _context: dict) -> tuple[str, list[str]]:
    return (
        "I couldn't match that to something your farm's data can answer. I'm a rule-based assistant (not a general "
        "chatbot), so I can only help with: crop recommendation reasoning, soil health, risk levels, irrigation, "
        "fertilizer, disease diagnosis, market prices, and weather. Try one of the suggested questions below.",
        [],
    )


_KEYWORD_INTENTS: list[tuple[str, tuple[str, ...]]] = [
    ("greeting", ("hi", "hello", "hey")),
    ("why_recommended", ("why",)),
    ("which_crop", ("which crop", "what crop", "suitable crop", "best crop", "crop suitable")),
    ("soil_improve", ("improve",)),
    ("soil_meaning", ("soil",)),
    ("irrigation", ("irrigat", "water")),
    ("disease", ("disease", "leaf", "pest", "infect")),
    ("fertilizer", ("fertilizer", "nutrient", "deficien")),
    ("market", ("price", "market", "sell", "mandi")),
    ("risk", ("risk",)),
    ("weather", ("weather", "rain", "temperature", "humid")),
]


def _classify(message: str) -> str:
    lower = message.lower()
    # Order matters: more specific phrases (e.g. "which crop") are checked before
    # generic single-word ones (e.g. "soil") within the same pass below.
    if any(k in lower for k in ("hi", "hello", "hey")) and len(lower.split()) <= 3:
        return "greeting"
    if "why" in lower and ("crop" in lower or "recommend" in lower):
        return "why_recommended"
    if any(p in lower for p in ("which crop", "what crop", "suitable crop", "best crop", "crop suitable")):
        return "which_crop"
    if "improve" in lower and "soil" in lower:
        return "soil_improve"
    if any(k in lower for k in ("irrigat",)) or (
        "water" in lower and "requirement" not in lower
    ):
        return "irrigation"
    if any(k in lower for k in ("disease", "leaf", "pest", "infect")):
        return "disease"
    if any(k in lower for k in ("fertilizer", "nutrient", "deficien")):
        return "fertilizer"
    if any(k in lower for k in ("price", "market", "sell", "mandi")):
        return "market"
    if "risk" in lower:
        return "risk"
    if "soil" in lower:
        return "soil_meaning"
    if any(k in lower for k in ("weather", "rain", "temperature", "humid")):
        return "weather"
    return "fallback"


def _handle_weather(_message: str, context: dict) -> tuple[str, list[str]]:
    weather = context.get("weather")
    farm = context.get("farm")
    if not weather or not farm:
        return ("Select a farm first so I can look up conditions for its location.", [])
    return (
        f"Current conditions near {farm.location}: {weather['temperature_c']}°C, {weather['humidity_pct']}% humidity, "
        f"{weather['rainfall_mm']}mm rainfall, {weather['condition']}. Source: {weather['source']} weather provider — "
        "this project has no live weather API key configured, so this is deterministic demo data, not a real forecast.",
        ["Weather (mock provider)"],
    )


def answer_question(db: Session, message: str, context: dict, known_crops: list[str]) -> tuple[str, list[str]]:
    if context.get("farm") is None and "hi" not in message.lower() and "hello" not in message.lower():
        return (
            "Please select a farm above first — I answer using that farm's real soil, weather and prediction data, "
            "not general knowledge.",
            [],
        )

    intent = _classify(message)
    handlers = {
        "greeting": lambda: _handle_greeting(message, context),
        "why_recommended": lambda: _handle_why_recommended(message, context),
        "which_crop": lambda: _handle_which_crop(message, context),
        "soil_improve": lambda: _handle_soil_improve(message, context),
        "soil_meaning": lambda: _handle_soil_meaning(message, context),
        "irrigation": lambda: _handle_irrigation(message, context),
        "disease": lambda: _handle_disease(message, context),
        "fertilizer": lambda: _handle_fertilizer(message, context, known_crops),
        "market": lambda: _handle_market(db, message, context, known_crops),
        "risk": lambda: _handle_risk(message, context),
        "weather": lambda: _handle_weather(message, context),
        "fallback": lambda: _handle_fallback(message, context),
    }
    return handlers[intent]()
