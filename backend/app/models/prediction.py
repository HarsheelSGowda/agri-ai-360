from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class CropPrediction(Base):
    __tablename__ = "crop_predictions"

    id: Mapped[int] = mapped_column(primary_key=True)
    farm_id: Mapped[int] = mapped_column(ForeignKey("farms.id"), nullable=False)
    model_version_id: Mapped[int | None] = mapped_column(ForeignKey("model_versions.id"), nullable=True)
    input_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    top_crop: Mapped[str] = mapped_column(String(100), nullable=False)
    top_score: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    farm: Mapped["Farm"] = relationship(back_populates="predictions")
    scores: Mapped[list["CropScore"]] = relationship(back_populates="prediction", cascade="all, delete-orphan")
    explanation: Mapped["RecommendationExplanation"] = relationship(
        back_populates="prediction", uselist=False, cascade="all, delete-orphan"
    )


class CropScore(Base):
    __tablename__ = "crop_scores"

    id: Mapped[int] = mapped_column(primary_key=True)
    prediction_id: Mapped[int] = mapped_column(ForeignKey("crop_predictions.id"), nullable=False)
    crop: Mapped[str] = mapped_column(String(100), nullable=False)
    probability: Mapped[float] = mapped_column(Float, nullable=False)
    rank: Mapped[int] = mapped_column(nullable=False)

    prediction: Mapped["CropPrediction"] = relationship(back_populates="scores")


class RecommendationExplanation(Base):
    __tablename__ = "recommendation_explanations"

    id: Mapped[int] = mapped_column(primary_key=True)
    prediction_id: Mapped[int] = mapped_column(ForeignKey("crop_predictions.id"), unique=True, nullable=False)
    method: Mapped[str] = mapped_column(String(50), default="shap")
    contributions_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    narrative: Mapped[str] = mapped_column(String(1000), nullable=False)

    prediction: Mapped["CropPrediction"] = relationship(back_populates="explanation")


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    farm_id: Mapped[int] = mapped_column(ForeignKey("farms.id"), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    algorithm: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=False)
    trained_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    farmer_id: Mapped[int] = mapped_column(ForeignKey("farmers.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    messages: Mapped[list["ChatMessage"]] = relationship(back_populates="session", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("chat_sessions.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(String(4000), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    session: Mapped["ChatSession"] = relationship(back_populates="messages")
