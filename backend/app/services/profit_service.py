"""
Profit Prediction (Phase 2).

Deliberately NOT a single "trained profit model" — profit is computed as
Revenue - Cost, where:

  Revenue = predicted yield (real trained regressor, see yield_service.py)
            x real historical mandi price (see build_price_reference.py)
  Cost    = supplied by the farmer

Cost of cultivation varies hugely by farm, region and practice, and no
public dataset we found offered honest per-farm cost figures (see
docs/dataset.md) — inventing a "cost model" would mean presenting made-up
numbers as if they were data-driven, which the project's own rules forbid.
Asking the farmer for their own cost estimate is the honest alternative.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.core.config import settings
from app.services.yield_service import HECTARES_PER_ACRE, YieldModelUnavailableError, predict_yield

QUINTALS_PER_TONNE = 10


class ProfitDataUnavailableError(RuntimeError):
    pass


def _models_dir() -> Path:
    return settings.resolved_models_dir


@lru_cache
def load_price_reference() -> dict | None:
    path = _models_dir() / "price_reference.json"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def supported_profit_crops() -> list[str]:
    ref = load_price_reference()
    return sorted(ref.keys()) if ref else []


def _lookup_price(crop: str, state: str) -> tuple[float, str] | None:
    ref = load_price_reference()
    if not ref or crop not in ref:
        return None
    crop_ref = ref[crop]
    if state in crop_ref["by_state"]:
        return crop_ref["by_state"][state], "state"
    return crop_ref["national_median"], "national_fallback"


def predict_profit(
    crop: str,
    state: str,
    season: str,
    cost_per_acre: float,
    area_acres: float | None = None,
) -> dict:
    if not load_price_reference():
        raise ProfitDataUnavailableError(
            "Price reference has not been built yet. Run ml/profit_prediction/build_price_reference.py."
        )

    if crop.lower() not in supported_profit_crops():
        return {
            "supported": False,
            "reason": f"No market price data is available for '{crop}' yet — profit prediction "
            f"currently covers: {', '.join(supported_profit_crops())}.",
            "crop": crop,
        }

    try:
        yield_result = predict_yield(crop, state, season)
    except YieldModelUnavailableError as exc:
        raise ProfitDataUnavailableError(str(exc)) from exc

    if not yield_result["supported"]:
        return {
            "supported": False,
            "reason": f"Yield estimate unavailable, so profit can't be calculated: {yield_result['reason']}",
            "crop": crop,
        }

    price_lookup = _lookup_price(crop.lower(), state)
    if price_lookup is None:
        return {
            "supported": False,
            "reason": f"No price data found for '{crop}' at all (unexpected — crop passed the supported check).",
            "crop": crop,
        }
    price_per_quintal, price_source = price_lookup

    yield_tonnes_per_ha = yield_result["predicted_yield_tonnes_per_ha"]
    revenue_per_ha = yield_tonnes_per_ha * QUINTALS_PER_TONNE * price_per_quintal
    revenue_per_acre = revenue_per_ha / HECTARES_PER_ACRE
    cost_per_ha = cost_per_acre * HECTARES_PER_ACRE

    profit_per_acre = revenue_per_acre - cost_per_acre
    profit_per_ha = revenue_per_ha - cost_per_ha
    margin_pct = (profit_per_acre / revenue_per_acre * 100) if revenue_per_acre > 0 else None

    result = {
        "supported": True,
        "crop": crop,
        "mapped_crop": yield_result["mapped_crop"],
        "state": state,
        "season": season,
        "yield_tonnes_per_ha": yield_tonnes_per_ha,
        "price_rs_per_quintal": price_per_quintal,
        "price_source": price_source,
        "cost_per_acre": round(cost_per_acre, 2),
        "revenue_per_acre": round(revenue_per_acre, 2),
        "profit_per_acre": round(profit_per_acre, 2),
        "revenue_per_ha": round(revenue_per_ha, 2),
        "profit_per_ha": round(profit_per_ha, 2),
        "margin_pct": round(margin_pct, 1) if margin_pct is not None else None,
        "total_farm_profit": None,
    }

    if area_acres is not None and area_acres > 0:
        result["total_farm_profit"] = round(profit_per_acre * area_acres, 2)

    return result
