import datetime
from typing import List, Optional, Any, Dict
from sqlalchemy import String, Float, Integer, Date, ForeignKey, Index, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base, TimestampMixin

class Asset(Base, TimestampMixin):
    """
    Physical railway infrastructure asset.
    Asset types: TRACK, SIGNAL, POINT, OHE, BRIDGE, CROSSING, OTHER
    Departments: ENGINEERING, S&T, TRACTION
    """
    __tablename__ = "assets"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    asset_code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    asset_type: Mapped[str] = mapped_column(String(32), index=True, nullable=False) # TRACK, SIGNAL, POINT, OHE, BRIDGE, CROSSING, OTHER
    department: Mapped[str] = mapped_column(String(32), index=True, nullable=False) # ENGINEERING, S&T, TRACTION
    
    corridor_id: Mapped[str] = mapped_column(String(64), ForeignKey("corridors.id", ondelete="CASCADE"), nullable=False, index=True)
    section_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("sections.id", ondelete="SET NULL"), nullable=True, index=True)
    station_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("stations.id", ondelete="SET NULL"), nullable=True, index=True)

    start_chainage: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    end_chainage: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    
    installation_date: Mapped[Optional[datetime.date]] = mapped_column(Date, nullable=True)
    age_years: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    criticality: Mapped[int] = mapped_column(Integer, default=3, nullable=False) # 1 (Low) to 5 (Critical)
    status: Mapped[str] = mapped_column(String(32), default="OPERATIONAL", nullable=False) # OPERATIONAL, DEGRADED, MAINTENANCE_REQUIRED, OUT_OF_SERVICE
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Relationships
    corridor: Mapped["Corridor"] = relationship("Corridor", back_populates="assets")
    section: Mapped[Optional["Section"]] = relationship("Section", back_populates="assets")
    station: Mapped[Optional["Station"]] = relationship("Station", back_populates="assets")
    
    maintenance_requests: Mapped[List["MaintenanceRequest"]] = relationship("MaintenanceRequest", back_populates="asset")
    maintenance_history: Mapped[List["MaintenanceHistory"]] = relationship("MaintenanceHistory", back_populates="asset")
    ml_predictions: Mapped[List["MLPrediction"]] = relationship("MLPrediction", back_populates="asset")

    __table_args__ = (
        Index("ix_assets_corridor_chainage", "corridor_id", "start_chainage", "end_chainage"),
        Index("ix_assets_dept_type", "department", "asset_type"),
    )
