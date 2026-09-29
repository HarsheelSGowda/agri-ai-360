from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Float, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class MarketPrice(Base):
    """
    Real historical Agmarknet (Indian government mandi) price records, seeded via
    ml/market_price/seed_market_prices.py from ml/datasets/agmarknet_prices/*.csv.

    Source data covers calendar year 2016 for 6 crops — see
    docs/dataset.md / DATASETS.md. This is historical reference data, not a live
    feed; MarketPriceProvider is the abstraction that would be swapped for a live
    Agmarknet API integration without touching the service/routes/frontend.
    """

    __tablename__ = "market_prices"
    __table_args__ = (Index("ix_market_prices_lookup", "crop", "state", "district", "market", "price_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    crop: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    district: Mapped[str] = mapped_column(String(100), nullable=False)
    market: Mapped[str] = mapped_column(String(150), nullable=False)
    variety: Mapped[str] = mapped_column(String(100), nullable=False)
    group_name: Mapped[str] = mapped_column(String(100), nullable=True)
    arrivals_tonnes: Mapped[float | None] = mapped_column(Float, nullable=True)
    min_price: Mapped[float] = mapped_column(Float, nullable=False)
    max_price: Mapped[float] = mapped_column(Float, nullable=False)
    modal_price: Mapped[float] = mapped_column(Float, nullable=False)
    price_date: Mapped[date] = mapped_column(Date, nullable=False)
    source: Mapped[str] = mapped_column(String(50), default="agmarknet_2016_historical")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
