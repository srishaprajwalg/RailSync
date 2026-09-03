import datetime
from typing import List, Optional
from sqlalchemy import String, Float, Integer, Date, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base, TimestampMixin

class Train(Base, TimestampMixin):
    """
    Train catalog identity.
    Categories: EXPRESS, SUPERFAST, PASSENGER, VANDE_BHARAT, SHATABDI, RAJDHANI, FREIGHT, OTHER
    """
    __tablename__ = "trains"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    train_number: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    operator: Mapped[Optional[str]] = mapped_column(String(64), default="Indian Railways", nullable=True)
    source_type: Mapped[str] = mapped_column(String(32), default="REAL", nullable=False) # REAL, IMPORTED, SYNTHETIC

    # Relationships
    runs: Mapped[List["TrainRun"]] = relationship("TrainRun", back_populates="train", cascade="all, delete-orphan")


class TrainRun(Base, TimestampMixin):
    """
    Daily service run of a train through a corridor.
    """
    __tablename__ = "train_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    train_id: Mapped[str] = mapped_column(String(64), ForeignKey("trains.id", ondelete="CASCADE"), nullable=False, index=True)
    corridor_id: Mapped[str] = mapped_column(String(64), ForeignKey("corridors.id", ondelete="CASCADE"), nullable=False, index=True)
    service_date: Mapped[Optional[datetime.date]] = mapped_column(Date, nullable=True)
    direction: Mapped[str] = mapped_column(String(16), nullable=False) # Up, Down
    day_offset: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    train: Mapped["Train"] = relationship("Train", back_populates="runs")
    corridor: Mapped["Corridor"] = relationship("Corridor", back_populates="train_runs")
    movements: Mapped[List["TrainMovement"]] = relationship("TrainMovement", back_populates="train_run", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_train_runs_corridor_direction", "corridor_id", "direction"),
    )


class TrainMovement(Base, TimestampMixin):
    """
    Specific station arrival and departure times for a train run.
    """
    __tablename__ = "train_movements"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    train_run_id: Mapped[str] = mapped_column(String(64), ForeignKey("train_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    station_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("stations.id", ondelete="SET NULL"), nullable=True, index=True)
    station_code: Mapped[str] = mapped_column(String(16), nullable=False)
    
    arrival_time: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    departure_time: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    arrival_mins: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    departure_mins: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    chainage_km: Mapped[float] = mapped_column(Float, nullable=False)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Relationships
    train_run: Mapped["TrainRun"] = relationship("TrainRun", back_populates="movements")
    station: Mapped[Optional["Station"]] = relationship("Station", back_populates="train_movements")

    __table_args__ = (
        Index("ix_train_movements_window", "train_run_id", "arrival_mins", "departure_mins"),
    )


class FreightForecast(Base, TimestampMixin):
    """
    Forecast window for freight train movements across a corridor section.
    """
    __tablename__ = "freight_forecasts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    corridor_id: Mapped[str] = mapped_column(String(64), ForeignKey("corridors.id", ondelete="CASCADE"), nullable=False, index=True)
    direction: Mapped[str] = mapped_column(String(16), nullable=False) # Up, Down
    
    start_chainage: Mapped[float] = mapped_column(Float, nullable=False)
    end_chainage: Mapped[float] = mapped_column(Float, nullable=False)
    earliest_entry_mins: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    latest_exit_mins: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.85, nullable=False)
    forecast_source: Mapped[str] = mapped_column(String(64), default="SYNTHETIC_SIMULATION", nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), default="SYNTHETIC", nullable=False) # REAL, SYNTHETIC, INFERRED

    # Relationships
    corridor: Mapped["Corridor"] = relationship("Corridor", back_populates="freight_forecasts")

    __table_args__ = (
        Index("ix_freight_corridor_time", "corridor_id", "earliest_entry_mins", "latest_exit_mins"),
    )
