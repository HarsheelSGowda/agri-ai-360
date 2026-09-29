from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

CATEGORIES = ("WEATHER", "CROP", "DISEASE", "MARKET", "FERTILIZER", "WATER", "RISK")
PRIORITIES = ("LOW", "MEDIUM", "HIGH")


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    farmer_id: Mapped[int] = mapped_column(ForeignKey("farmers.id"), nullable=False)
    farm_id: Mapped[int | None] = mapped_column(ForeignKey("farms.id"), nullable=True)
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    priority: Mapped[str] = mapped_column(String(10), default="MEDIUM")
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(String(1000), nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    farmer: Mapped["Farmer"] = relationship()
