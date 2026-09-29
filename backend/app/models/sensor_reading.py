from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class SensorReading(Base):
    """
    IoT sensor reading (Phase 2E, Feature 10C).

    Architecture: Sensor -> API/MQTT gateway -> Backend (POST /api/iot/readings,
    see app/services/iot_service.py) -> this table -> Dashboard.

    `source` distinguishes a genuine device push ("device") from a clearly-
    labeled demo/simulation row ("demo_simulation") generated because no
    physical sensor is connected to this deployment yet - never mix the two
    silently.
    """

    __tablename__ = "sensor_readings"

    id: Mapped[int] = mapped_column(primary_key=True)
    farm_id: Mapped[int] = mapped_column(ForeignKey("farms.id"), nullable=False)
    sensor_type: Mapped[str] = mapped_column(String(50), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    source: Mapped[str] = mapped_column(String(30), default="demo_simulation")
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    farm: Mapped["Farm"] = relationship(back_populates="sensor_readings")
