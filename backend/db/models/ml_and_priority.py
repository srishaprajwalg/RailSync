from typing import Optional, Any, Dict
from sqlalchemy import String, Float, Integer, ForeignKey, Index, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base, TimestampMixin

class MLPrediction(Base, TimestampMixin):
    """
    Immutable historical record of ML model predictions for maintenance requests and assets.
    Prediction types: RECURRENCE_RISK, FAILURE_RISK, REPAIR_DURATION, OPERATIONAL_IMPACT
    """
    __tablename__ = "ml_predictions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    maintenance_request_id: Mapped[str] = mapped_column(String(64), ForeignKey("maintenance_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("assets.id", ondelete="SET NULL"), nullable=True, index=True)

    model_name: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    model_version: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    prediction_type: Mapped[str] = mapped_column(String(32), nullable=False)
    
    prediction: Mapped[str] = mapped_column(String(64), nullable=False)
    probability: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    features_snapshot: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Relationships
    maintenance_request: Mapped["MaintenanceRequest"] = relationship("MaintenanceRequest", back_populates="ml_predictions")
    asset: Mapped[Optional["Asset"]] = relationship("Asset", back_populates="ml_predictions")

    __table_args__ = (
        Index("ix_ml_predictions_request_model", "maintenance_request_id", "model_name", "model_version"),
    )


class PriorityDecision(Base, TimestampMixin):
    """
    Explainable, traceable priority scoring decision for a maintenance request.
    """
    __tablename__ = "priority_decisions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    maintenance_request_id: Mapped[str] = mapped_column(String(64), ForeignKey("maintenance_requests.id", ondelete="CASCADE"), nullable=False, index=True)

    priority_score: Mapped[int] = mapped_column(Integer, nullable=False)
    priority_category: Mapped[str] = mapped_column(String(32), nullable=False)
    
    ml_risk_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    severity_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    criticality_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    urgency_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    overdue_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    operational_impact_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    engine_version: Mapped[str] = mapped_column(String(32), default="v1.0-explainable", nullable=False)

    # Relationships
    maintenance_request: Mapped["MaintenanceRequest"] = relationship("MaintenanceRequest", back_populates="priority_decisions")
