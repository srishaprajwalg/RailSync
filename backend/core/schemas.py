from pydantic import BaseModel, Field
from typing import List, Optional

class Station(BaseModel):
    id: str
    code: str
    name: str
    chainage_km: float

class TrainStop(BaseModel):
    station_id: str
    arrival_mins: int  # Absolute minutes from the start of the planning horizon
    departure_mins: int # Absolute minutes from the start of the planning horizon

class TrainSchedule(BaseModel):
    train_id: str
    type: str  # Express, Passenger
    direction: str  # Up, Down
    stops: List[TrainStop]

class GoodsTrainForecast(BaseModel):
    """
    Represents a forecast window for a goods train movement.
    Unlike passenger trains with exact minute-by-minute schedules, goods trains
    are forecast to pass through a corridor section within a time window.
    """
    forecast_id: str
    direction: str  # Up, Down
    start_km: float # Entry point of the forecast section
    end_km: float   # Exit point of the forecast section
    earliest_entry_mins: int # Absolute minutes from horizon start
    latest_exit_mins: int    # Absolute minutes from horizon start

class PriorityDetails(BaseModel):
    score: int
    category: str
    explanation: str

class MaintenanceTask(BaseModel):
    id: str
    department: str  # TMS, SMMS, TDMS
    task_type: str
    
    # Origins and Urgency factors
    origin: str             # e.g., "Defect", "Routine Maintenance"
    severity: int           # 1 (Low) to 5 (Critical safety hazard)
    overdue_days: int       # Number of days this task is overdue
    asset_criticality: int  # 1 (Low) to 5 (High-density/critical section)
    
    # Spatial and Temporal constraints
    start_km: float
    end_km: float
    duration_mins: int
    deadline_mins: int      # Absolute minutes from horizon start
    line_direction: str
    
    priority_details: Optional[PriorityDetails] = None

class MaintenanceTaskCreate(BaseModel):
    department: str
    start_km: float
    end_km: float
    duration_mins: int
    severity: int

class PlannedBlock(BaseModel):
    id: str
    start_time_mins: int
    end_time_mins: int
    start_km: float
    end_km: float
    line_direction: str
    assigned_tasks: List[str]  # Task IDs

class OptimizeRequest(BaseModel):
    horizon_days: int = Field(7, ge=1, le=30, description="Planning horizon in days (1 to 30)")

class OptimizationMetrics(BaseModel):
    total_tasks: int
    planned_tasks: int
    deferred_tasks: int
    infeasible_tasks: int
    blocks_created: int
    total_block_minutes: int
    total_requested_maintenance_minutes: int
    downtime_reduction_pct: float
    high_priority_planned: int
    high_priority_deferred: int

class OptimizationResult(BaseModel):
    status: str
    blocks: List[PlannedBlock]
    metrics: OptimizationMetrics

