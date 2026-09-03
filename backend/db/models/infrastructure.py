from typing import List, Optional
from sqlalchemy import String, Float, Boolean, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base, TimestampMixin

class Corridor(Base, TimestampMixin):
    """
    Top-level railway corridor supporting multi-corridor operation.
    Example: SBC-JTJ (Bengaluru to Jolarpettai, 145.0 km)
    """
    __tablename__ = "corridors"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    total_length_km: Mapped[float] = mapped_column(Float, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    sections: Mapped[List["Section"]] = relationship("Section", back_populates="corridor", cascade="all, delete-orphan")
    assets: Mapped[List["Asset"]] = relationship("Asset", back_populates="corridor")
    train_runs: Mapped[List["TrainRun"]] = relationship("TrainRun", back_populates="corridor")
    freight_forecasts: Mapped[List["FreightForecast"]] = relationship("FreightForecast", back_populates="corridor")
    maintenance_requests: Mapped[List["MaintenanceRequest"]] = relationship("MaintenanceRequest", back_populates="corridor")
    optimization_runs: Mapped[List["OptimizationRun"]] = relationship("OptimizationRun", back_populates="corridor")


class Section(Base, TimestampMixin):
    """
    Corridor subdivision with designated chainage boundaries.
    """
    __tablename__ = "sections"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    corridor_id: Mapped[str] = mapped_column(String(64), ForeignKey("corridors.id", ondelete="CASCADE"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    start_chainage: Mapped[float] = mapped_column(Float, nullable=False)
    end_chainage: Mapped[float] = mapped_column(Float, nullable=False)
    direction: Mapped[str] = mapped_column(String(16), default="BOTH", nullable=False) # UP, DOWN, BOTH

    # Relationships
    corridor: Mapped["Corridor"] = relationship("Corridor", back_populates="sections")
    stations: Mapped[List["Station"]] = relationship("Station", back_populates="section")
    assets: Mapped[List["Asset"]] = relationship("Asset", back_populates="section")

    __table_args__ = (
        Index("ix_sections_corridor_chainage", "corridor_id", "start_chainage", "end_chainage"),
    )


class Station(Base, TimestampMixin):
    """
    Station along the corridor with calibrated chainage and geographic coordinates.
    """
    __tablename__ = "stations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    section_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("sections.id", ondelete="SET NULL"), nullable=True, index=True)
    code: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    chainage_km: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Relationships
    section: Mapped[Optional["Section"]] = relationship("Section", back_populates="stations")
    assets: Mapped[List["Asset"]] = relationship("Asset", back_populates="station")
    train_movements: Mapped[List["TrainMovement"]] = relationship("TrainMovement", back_populates="station")
