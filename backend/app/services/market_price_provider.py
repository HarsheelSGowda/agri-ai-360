"""
Market price provider abstraction (Phase 2, Crop Market Price Intelligence).

MarketPriceProvider defines the interface the rest of the app depends on.
HistoricalDBMarketPriceProvider reads real Agmarknet mandi price records
(seeded via ml/market_price/seed_market_prices.py) from the `market_prices`
table - real government data, but a fixed historical year (2016), not a live
feed. When a real live Agmarknet/eNAM API integration is available, a
LiveMarketPriceProvider implementing the same interface can be swapped in via
get_market_price_provider() without touching the service, routes, or frontend.

Mirrors the WeatherProvider pattern (app/services/weather_provider.py).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.market_price import MarketPrice

SOURCE_LABEL = "Agmarknet (Government of India mandi price records), calendar year 2016"


class MarketPriceProvider(ABC):
    @abstractmethod
    def list_crops(self, db: Session) -> list[str]: ...

    @abstractmethod
    def list_states(self, db: Session, crop: str) -> list[str]: ...

    @abstractmethod
    def list_districts(self, db: Session, crop: str, state: str) -> list[str]: ...

    @abstractmethod
    def list_markets(self, db: Session, crop: str, state: str, district: str | None = None) -> list[str]: ...

    @abstractmethod
    def latest_snapshot(
        self, db: Session, crop: str, state: str, district: str | None, market: str | None, variety: str | None
    ) -> list[MarketPrice]: ...

    @abstractmethod
    def trend(
        self, db: Session, crop: str, state: str, district: str | None, market: str | None, variety: str | None, limit_days: int
    ) -> list[MarketPrice]: ...

    @abstractmethod
    def market_comparison(self, db: Session, crop: str, state: str, district: str | None, as_of: date) -> list[MarketPrice]: ...

    @property
    @abstractmethod
    def source_label(self) -> str: ...

    @property
    @abstractmethod
    def is_live(self) -> bool: ...


class HistoricalDBMarketPriceProvider(MarketPriceProvider):
    """Queries the real, DB-backed Agmarknet 2016 historical dataset."""

    def list_crops(self, db: Session) -> list[str]:
        rows = db.query(MarketPrice.crop).distinct().order_by(MarketPrice.crop).all()
        return [r[0] for r in rows]

    def list_states(self, db: Session, crop: str) -> list[str]:
        rows = db.query(MarketPrice.state).filter(MarketPrice.crop == crop).distinct().order_by(MarketPrice.state).all()
        return [r[0] for r in rows]

    def list_districts(self, db: Session, crop: str, state: str) -> list[str]:
        rows = (
            db.query(MarketPrice.district)
            .filter(MarketPrice.crop == crop, MarketPrice.state == state)
            .distinct()
            .order_by(MarketPrice.district)
            .all()
        )
        return [r[0] for r in rows]

    def list_markets(self, db: Session, crop: str, state: str, district: str | None = None) -> list[str]:
        query = db.query(MarketPrice.market).filter(MarketPrice.crop == crop, MarketPrice.state == state)
        if district:
            query = query.filter(MarketPrice.district == district)
        rows = query.distinct().order_by(MarketPrice.market).all()
        return [r[0] for r in rows]

    def _base_query(self, db: Session, crop: str, state: str, district: str | None, market: str | None, variety: str | None):
        query = db.query(MarketPrice).filter(MarketPrice.crop == crop, MarketPrice.state == state)
        if district:
            query = query.filter(MarketPrice.district == district)
        if market:
            query = query.filter(MarketPrice.market == market)
        if variety:
            query = query.filter(MarketPrice.variety == variety)
        return query

    def latest_snapshot(
        self, db: Session, crop: str, state: str, district: str | None, market: str | None, variety: str | None
    ) -> list[MarketPrice]:
        query = self._base_query(db, crop, state, district, market, variety)
        latest_date = query.with_entities(func.max(MarketPrice.price_date)).scalar()
        if latest_date is None:
            return []
        return query.filter(MarketPrice.price_date == latest_date).order_by(MarketPrice.market).all()

    def trend(
        self,
        db: Session,
        crop: str,
        state: str,
        district: str | None,
        market: str | None,
        variety: str | None,
        limit_days: int = 30,
    ) -> list[MarketPrice]:
        query = self._base_query(db, crop, state, district, market, variety)
        distinct_dates = [
            r[0] for r in query.with_entities(MarketPrice.price_date).distinct().order_by(MarketPrice.price_date.desc()).limit(limit_days)
        ]
        if not distinct_dates:
            return []
        return query.filter(MarketPrice.price_date.in_(distinct_dates)).order_by(MarketPrice.price_date).all()

    def market_comparison(self, db: Session, crop: str, state: str, district: str | None, as_of: date) -> list[MarketPrice]:
        query = db.query(MarketPrice).filter(MarketPrice.crop == crop, MarketPrice.state == state, MarketPrice.price_date == as_of)
        if district:
            query = query.filter(MarketPrice.district == district)
        return query.order_by(MarketPrice.modal_price.desc()).all()

    @property
    def source_label(self) -> str:
        return SOURCE_LABEL

    @property
    def is_live(self) -> bool:
        return False


def get_market_price_provider() -> MarketPriceProvider:
    return HistoricalDBMarketPriceProvider()
