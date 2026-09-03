import datetime
from typing import List, Optional, Any, Dict
from sqlalchemy import String, Float, Integer, Boolean, DateTime, ForeignKey, Index, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base, TimestampMixin

class OptimizationRun(Base, TimestampMixin):
    """
    Audit log and metadata for CP-SAT solver executions.
    """
    __tablename__ = "optimization_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    corridor_id: Mapped[str] = mapped_column(String(64), ForeignKey("corridors.id", ondelete="CASCADE"), nullable=False, index=True)
    
    horizon_start: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    horizon_end: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    horizon_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    
    solver: Mapped[str] = mapped_column(String(64), default="Google OR-Tools CP-SAT", nullable=False)
    solver_version: Mapped[str] = mapped_column(String(32), default="9.15", nullable=False)
    objective_version: Mapped[str] = mapped_column(String(32), default="v2.0-hierarchical", nullable=False)
    
    status: Mapped[str] = mapped_column(String(32), default="COMPLETED", nullable=False) # RUNNING, COMPLETED, FAILED
    solve_time_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    metrics_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Relationships
    corridor: Mapped["Corridor"] = relationship("Corridor", back_populates="optimization_runs")
    planned_blocks: Mapped[List["PlannedBlock"]] = relationship("PlannedBlock", back_populates="optimization_run", cascade="all, delete-orphan")


class PlannedBlock(Base, TimestampMixin):
    """
    Consolidated physical maintenance block created by CP-SAT solver and post-processing grouping.
    """
    __tablename__ = "planned_blocks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    optimization_run_id: Mapped[str] = mapped_column(String(64), ForeignKey("optimization_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    corridor_id: Mapped[str] = mapped_column(String(64), ForeignKey("corridors.id", ondelete="CASCADE"), nullable=False, index=True)

    start_time: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    end_time: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    start_time_mins: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    end_time_mins: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    start_chainage: Mapped[float] = mapped_column(Float, nullable=False)
    end_chainage: Mapped[float] = mapped_column(Float, nullable=False)
    direction: Mapped[str] = mapped_column(String(16), nullable=False) # Up, Down
    status: Mapped[str] = mapped_column(String(32), default="PLANNED", nullable=False) # PLANNED, EXECUTING, COMPLETED, CANCELLED
    reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    optimization_run: Mapped["OptimizationRun"] = relationship("OptimizationRun", back_populates="planned_blocks")
    block_tasks: Mapped[List["BlockTask"]] = relationship("BlockTask", back_populates="block", cascade="all, delete-orphan")
    schedule_decisions: Mapped[List["ScheduleDecision"]] = relationship("ScheduleDecision", back_populates="block", cascade="all, delete-orphan")
    outcomes: Mapped[List["MaintenanceOutcome"]] = relationship("MaintenanceOutcome", back_populates="planned_block")

    __table_args__ = (
        Index("ix_planned_blocks_corridor_time", "corridor_id", "start_time_mins", "end_time_mins"),
    )


class BlockTask(Base, TimestampMixin):
    """
    Many-to-many relationship linking PlannedBlocks to assigned MaintenanceRequests.
    """
    __tablename__ = "block_tasks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    block_id: Mapped[str] = mapped_column(String(64), ForeignKey("planned_blocks.id", ondelete="CASCADE"), nullable=False, index=True)
    maintenance_request_id: Mapped[str] = mapped_column(String(64), ForeignKey("maintenance_requests.id", ondelete="CASCADE"), nullable=False, index=True)

    # Relationships
    block: Mapped["PlannedBlock"] = relationship("PlannedBlock", back_populates="block_tasks")
    maintenance_request: Mapped["MaintenanceRequest"] = relationship("MaintenanceRequest", back_populates="block_assignments")


class ScheduleDecision(Base, TimestampMixin):
    """
    Traceable reasoning answering: 'Why was this task scheduled in this exact window?'
    """
    __tablename__ = "schedule_decisions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    block_id: Mapped[str] = mapped_column(String(64), ForeignKey("planned_blocks.id", ondelete="CASCADE"), nullable=False, index=True)
    maintenance_request_id: Mapped[str] = mapped_column(String(64), ForeignKey("maintenance_requests.id", ondelete="CASCADE"), nullable=False, index=True)

    selected_start_mins: Mapped[int] = mapped_column(Integer, nullable=False)
    selected_end_mins: Mapped[int] = mapped_column(Integer, nullable=False)
    
    why_selected: Mapped[str] = mapped_column(Text, nullable=False)
    train_constraints: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    spatial_constraints: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    department_coordination: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    priority_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    solver_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relationships
    block: Mapped["PlannedBlock"] = relationship("PlannedBlock", back_populates="schedule_decisions")
    maintenance_request: Mapped["MaintenanceRequest"] = relationship("MaintenanceRequest", back_populates="schedule_decisions")


class MaintenanceOutcome(Base, TimestampMixin):
    """
    Actual maintenance execution outcomes supporting Planned vs Actual comparison and ML feedback loops.
    """
    __tablename__ = "maintenance_outcomes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    maintenance_request_id: Mapped[str] = mapped_column(String(64), ForeignKey("maintenance_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    planned_block_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("planned_blocks.id", ondelete="SET NULL"), nullable=True, index=True)

    actual_start: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_end: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_start_mins: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    actual_end_mins: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    actual_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)

    completion_status: Mapped[str] = mapped_column(String(32), default="COMPLETED", nullable=False) # COMPLETED, PARTIAL, ABORTED, FAILED
    success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    failure: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    recurrence: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    train_delay_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    trains_impacted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    deviation_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    maintenance_request: Mapped["MaintenanceRequest"] = relationship("MaintenanceRequest", back_populates="outcomes")
    planned_block: Mapped[Optional["PlannedBlock"]] = relationship("PlannedBlock", back_populates="outcomes")
