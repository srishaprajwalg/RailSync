import datetime
from typing import List, Optional
from sqlalchemy import String, Float, Integer, Boolean, DateTime, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base, TimestampMixin

class MaintenanceRequest(Base, TimestampMixin):
    """
    Persistent maintenance or defect request across railway departments.
    Lifecycle status: OPEN, PRIORITIZED, SCHEDULED, IN_PROGRESS, COMPLETED, DEFERRED, CANCELLED, FAILED
    Source type: REAL, SYNTHETIC, IMPORTED, INFERRED
    """
    __tablename__ = "maintenance_requests"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    asset_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("assets.id", ondelete="SET NULL"), nullable=True, index=True)
    corridor_id: Mapped[str] = mapped_column(String(64), ForeignKey("corridors.id", ondelete="CASCADE"), nullable=False, index=True)
    section_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("sections.id", ondelete="SET NULL"), nullable=True, index=True)

    department: Mapped[str] = mapped_column(String(32), index=True, nullable=False) # ENGINEERING, S&T, TRACTION
    request_type: Mapped[str] = mapped_column(String(64), nullable=False) # Routine Maintenance, Defect, Emergency
    defect_type: Mapped[str] = mapped_column(String(64), nullable=False) # Track Tamping, Rail Fracture Repair, etc.
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    reported_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    required_by: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    status: Mapped[str] = mapped_column(String(32), default="OPEN", index=True, nullable=False) # OPEN, PRIORITIZED, SCHEDULED, IN_PROGRESS, COMPLETED, DEFERRED, CANCELLED, FAILED
    severity: Mapped[int] = mapped_column(Integer, default=1, nullable=False) # 1 to 5
    criticality: Mapped[int] = mapped_column(Integer, default=1, nullable=False) # 1 to 5
    
    start_chainage: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    end_chainage: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    line_direction: Mapped[str] = mapped_column(String(16), default="Up", nullable=False) # Up, Down, Both
    
    estimated_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    actual_duration_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    deadline_mins: Mapped[int] = mapped_column(Integer, default=1440, nullable=False) # Minutes from horizon start
    overdue_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    required_resource: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    priority_score: Mapped[int] = mapped_column(Integer, default=0, index=True, nullable=False)
    priority_category: Mapped[str] = mapped_column(String(32), default="Low", nullable=False) # Critical, High, Medium, Low
    source_type: Mapped[str] = mapped_column(String(32), default="SYNTHETIC", nullable=False) # REAL, SYNTHETIC, IMPORTED, INFERRED

    # Relationships
    asset: Mapped[Optional["Asset"]] = relationship("Asset", back_populates="maintenance_requests")
    corridor: Mapped["Corridor"] = relationship("Corridor", back_populates="maintenance_requests")
    section: Mapped[Optional["Section"]] = relationship("Section")
    
    history_records: Mapped[List["MaintenanceHistory"]] = relationship("MaintenanceHistory", back_populates="maintenance_request")
    ml_predictions: Mapped[List["MLPrediction"]] = relationship("MLPrediction", back_populates="maintenance_request")
    priority_decisions: Mapped[List["PriorityDecision"]] = relationship("PriorityDecision", back_populates="maintenance_request", cascade="all, delete-orphan")
    block_assignments: Mapped[List["BlockTask"]] = relationship("BlockTask", back_populates="maintenance_request", cascade="all, delete-orphan")
    schedule_decisions: Mapped[List["ScheduleDecision"]] = relationship("ScheduleDecision", back_populates="maintenance_request", cascade="all, delete-orphan")
    outcomes: Mapped[List["MaintenanceOutcome"]] = relationship("MaintenanceOutcome", back_populates="maintenance_request", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_maint_corridor_dept_status", "corridor_id", "department", "status"),
        Index("ix_maint_chainage", "corridor_id", "start_chainage", "end_chainage"),
    )


class MaintenanceHistory(Base, TimestampMixin):
    """
    Historical log of past maintenance, inspections, repairs, and defect recurrences.
    Forms the baseline training data for ML recurrence and risk models.
    """
    __tablename__ = "maintenance_history"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    asset_id: Mapped[str] = mapped_column(String(64), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True)
    maintenance_request_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("maintenance_requests.id", ondelete="SET NULL"), nullable=True, index=True)

    event_type: Mapped[str] = mapped_column(String(32), nullable=False) # PREVENTIVE, CORRECTIVE, EMERGENCY, INSPECTION
    failure_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    
    started_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    
    success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    failure: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    recurrence: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    team: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    asset: Mapped["Asset"] = relationship("Asset", back_populates="maintenance_history")
    maintenance_request: Mapped[Optional["MaintenanceRequest"]] = relationship("MaintenanceRequest", back_populates="history_records")

    __table_args__ = (
        Index("ix_history_asset_time", "asset_id", "created_at"),
    )
