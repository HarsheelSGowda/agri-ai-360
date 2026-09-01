from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class SoilRecord(Base):
    __tablename__ = "soil_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    farm_id: Mapped[int] = mapped_column(ForeignKey("farms.id"), nullable=False)
    nitrogen: Mapped[float] = mapped_column(Float, nullable=False)
    phosphorus: Mapped[float] = mapped_column(Float, nullable=False)
    potassium: Mapped[float] = mapped_column(Float, nullable=False)
    ph: Mapped[float] = mapped_column(Float, nullable=False)
    soil_type: Mapped[str] = mapped_column(String(100), nullable=False)
    organic_carbon: Mapped[float | None] = mapped_column(Float, nullable=True)
    moisture: Mapped[float | None] = mapped_column(Float, nullable=True)
    electrical_conductivity: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    farm: Mapped["Farm"] = relationship(back_populates="soil_records")


class WeatherRecord(Base):
    __tablename__ = "weather_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    temperature_c: Mapped[float] = mapped_column(Float, nullable=False)
    humidity_pct: Mapped[float] = mapped_column(Float, nullable=False)
    rainfall_mm: Mapped[float] = mapped_column(Float, nullable=False)
    wind_kmh: Mapped[float] = mapped_column(Float, nullable=False)
    condition: Mapped[str] = mapped_column(String(100), nullable=False)
    source: Mapped[str] = mapped_column(String(20), default="mock")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
