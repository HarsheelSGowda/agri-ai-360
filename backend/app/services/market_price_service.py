"""
Market price service (Phase 2, Crop Market Price Intelligence).

Thin aggregation layer over MarketPriceProvider: turns raw per-mandi rows into
the current-price snapshot, trend series and market-comparison views the API
exposes. Contains no data fetching of its own - all data access goes through
the provider so the source can change without touching this file.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.services.market_price_provider import MarketPriceProvider, get_market_price_provider


class NoMarketDataError(Exception):
    pass


def _round(value: float) -> float:
    return round(value, 2)


def list_crops(db: Session, provider: MarketPriceProvider | None = None) -> list[str]:
    provider = provider or get_market_price_provider()
    return provider.list_crops(db)


def list_states(db: Session, crop: str, provider: MarketPriceProvider | None = None) -> list[str]:
    provider = provider or get_market_price_provider()
    return provider.list_states(db, crop)


def list_districts(db: Session, crop: str, state: str, provider: MarketPriceProvider | None = None) -> list[str]:
    provider = provider or get_market_price_provider()
    return provider.list_districts(db, crop, state)


def list_markets(db: Session, crop: str, state: str, district: str | None = None, provider: MarketPriceProvider | None = None) -> list[str]:
    provider = provider or get_market_price_provider()
    return provider.list_markets(db, crop, state, district)


def get_current_price(
    db: Session,
    crop: str,
    state: str,
    district: str | None = None,
    market: str | None = None,
    variety: str | None = None,
    provider: MarketPriceProvider | None = None,
) -> dict:
    provider = provider or get_market_price_provider()
    rows = provider.latest_snapshot(db, crop, state, district, market, variety)
    if not rows:
        return {
            "found": False,
            "reason": f"No mandi price records found for {crop} in {state}"
            + (f", {district}" if district else "")
            + (f", market '{market}'" if market else "")
            + ". Try a different state/district/market combination.",
        }

    return {
        "found": True,
        "crop": crop,
        "state": state,
        "district": district,
        "market": market,
        "variety": variety or rows[0].variety,
        "as_of_date": rows[0].price_date.isoformat(),
        "min_price": _round(min(r.min_price for r in rows)),
        "max_price": _round(max(r.max_price for r in rows)),
        "modal_price": _round(sum(r.modal_price for r in rows) / len(rows)),
        "markets_reporting": len(rows),
        "source": provider.source_label,
        "is_live": provider.is_live,
    }


def get_trend(
    db: Session,
    crop: str,
    state: str,
    district: str | None = None,
    market: str | None = None,
    variety: str | None = None,
    days: int = 30,
    provider: MarketPriceProvider | None = None,
) -> dict:
    provider = provider or get_market_price_provider()
    rows = provider.trend(db, crop, state, district, market, variety, limit_days=days)
    if not rows:
        return {"found": False, "reason": f"No historical trend data found for {crop} in {state}.", "points": []}

    by_date: dict[date, list] = {}
    for r in rows:
        by_date.setdefault(r.price_date, []).append(r)

    points = [
        {
            "date": d.isoformat(),
            "min_price": _round(min(r.min_price for r in recs)),
            "max_price": _round(max(r.max_price for r in recs)),
            "modal_price": _round(sum(r.modal_price for r in recs) / len(recs)),
        }
        for d, recs in sorted(by_date.items())
    ]

    first, last = points[0]["modal_price"], points[-1]["modal_price"]
    direction = "UP" if last > first else "DOWN" if last < first else "FLAT"
    change_pct = _round((last - first) / first * 100) if first else 0.0

    return {
        "found": True,
        "points": points,
        "trend_direction": direction,
        "change_pct": change_pct,
        "source": provider.source_label,
        "is_live": provider.is_live,
    }


def get_market_comparison(
    db: Session, crop: str, state: str, district: str | None = None, provider: MarketPriceProvider | None = None
) -> dict:
    provider = provider or get_market_price_provider()
    rows = provider.latest_snapshot(db, crop, state, district, None, None)
    if not rows:
        return {"found": False, "reason": f"No market comparison data found for {crop} in {state}.", "markets": []}

    markets = [
        {
            "market": r.market,
            "district": r.district,
            "min_price": _round(r.min_price),
            "max_price": _round(r.max_price),
            "modal_price": _round(r.modal_price),
            "arrivals_tonnes": r.arrivals_tonnes,
        }
        for r in sorted(rows, key=lambda x: x.modal_price, reverse=True)
    ]

    return {
        "found": True,
        "as_of_date": rows[0].price_date.isoformat(),
        "markets": markets,
        "best_market": markets[0] if markets else None,
        "source": provider.source_label,
        "is_live": provider.is_live,
    }
