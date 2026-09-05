import datetime
from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict

class Station(BaseModel):
    id: str
    code: str
    name: str
    chainage_km: float
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class TrainStop(BaseModel):
    station_id: str
    arrival_mins: int  # Absolute minutes from the start of the planning horizon
    departure_mins: int # Absolute minutes from the start of the planning horizon

class TrainSchedule(BaseModel):
    train_id: str
    type: str  # Express, Passenger, Shatabdi, etc.
    direction: str  # Up, Down
    stops: List[TrainStop]

class GoodsTrainForecast(BaseModel):
    """
    Represents a forecast window for a goods train movement.
    """
    forecast_id: str
    direction: str  # Up, Down
    start_km: float # Entry point of the forecast section
    end_km: float   # Exit point of the forecast section
    earliest_entry_mins: int # Absolute minutes from horizon start
    latest_exit_mins: int    # Absolute minutes from horizon start
    confidence: Optional[float] = 0.85
    source_type: Optional[str] = "SYNTHETIC"

class PriorityDetails(BaseModel):
    score: int
    category: str
    explanation: str

class MaintenanceTask(BaseModel):
    id: str
    department: str  # ENGINEERING, S&T, TRACTION (or legacy TMS, SMMS, TDMS)
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
    required_resource: Optional[str] = None
    asset_id: Optional[str] = None
    source_type: Optional[str] = "SYNTHETIC"
    
    priority_details: Optional[PriorityDetails] = None
    lifecycle_status: str = "Reported"
    rejection_reason: Optional[str] = None

class MaintenanceTaskCreate(BaseModel):
    department: Optional[str] = None
    task_type: str
    origin: str
    severity: int
    overdue_days: int
    asset_criticality: int
    start_km: float
    end_km: float
    duration_mins: int
    deadline_mins: int
    line_direction: str
    asset_id: Optional[str] = None
    corridor_id: Optional[str] = "SBC-JTJ"

class PlannedBlock(BaseModel):
    id: str
    start_time_mins: int
    end_time_mins: int
    start_km: float
    end_km: float
    line_direction: str
    assigned_tasks: List[str]  # Task IDs
    reasoning: Optional[str] = None

class OptimizeRequest(BaseModel):
    horizon_days: int = Field(30, ge=1, le=30, description="Planning horizon in days (1 to 30)")
    corridor_id: Optional[str] = "SBC-JTJ"
    department: Optional[str] = "ALL"

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
    task_statuses: Optional[Dict[str, str]] = None

class TaskStatusUpdate(BaseModel):
    lifecycle_status: str

# ---------------------------------------------------------------------------
# Extended Database-Backed Entities & Lifecycle Schemas
# ---------------------------------------------------------------------------

class CorridorOut(BaseModel):
    id: str
    code: str
    name: str
    description: Optional[str]
    total_length_km: float
    active: bool

class SectionOut(BaseModel):
    id: str
    corridor_id: str
    code: str
    name: str
    start_chainage: float
    end_chainage: float
    direction: str

class AssetOut(BaseModel):
    id: str
    asset_code: str
    asset_type: str
    department: str
    corridor_id: str
    section_id: Optional[str]
    station_id: Optional[str]
    start_chainage: float
    end_chainage: float
    age_years: float
    criticality: int
    status: str
    metadata_json: Optional[Dict[str, Any]]

class MaintenanceHistoryOut(BaseModel):
    id: str
    asset_id: str
    maintenance_request_id: Optional[str]
    event_type: str
    failure_type: Optional[str]
    started_at: Optional[datetime.datetime]
    completed_at: Optional[datetime.datetime]
    duration_minutes: int
    success: bool
    failure: bool
    recurrence: bool
    team: Optional[str]
    notes: Optional[str]
    created_at: datetime.datetime

class MLPredictionOut(BaseModel):
    id: str
    maintenance_request_id: str
    asset_id: Optional[str]
    model_name: str
    model_version: str
    prediction_type: str
    prediction: str
    probability: float
    confidence: float
    features_snapshot: Optional[Dict[str, Any]]
    created_at: datetime.datetime

class PriorityDecisionOut(BaseModel):
    id: str
    maintenance_request_id: str
    priority_score: int
    priority_category: str
    ml_risk_score: int
    severity_score: int
    criticality_score: int
    urgency_score: int
    overdue_score: int
    operational_impact_score: int
    reasoning: str
    engine_version: str
    created_at: datetime.datetime

class ScheduleDecisionOut(BaseModel):
    id: str
    block_id: str
    maintenance_request_id: str
    selected_start_mins: int
    selected_end_mins: int
    why_selected: str
    train_constraints: Optional[str]
    spatial_constraints: Optional[str]
    department_coordination: Optional[str]
    priority_reason: Optional[str]
    solver_reason: Optional[str]

class MaintenanceOutcomeCreate(BaseModel):
    maintenance_request_id: str
    planned_block_id: Optional[str] = None
    actual_duration_minutes: int
    completion_status: str = "COMPLETED" # COMPLETED, PARTIAL, ABORTED, FAILED
    success: bool = True
    recurrence: bool = False
    train_delay_minutes: int = 0
    trains_impacted: int = 0
    deviation_reason: Optional[str] = None

class MaintenanceOutcomeOut(BaseModel):
    id: str
    maintenance_request_id: str
    planned_block_id: Optional[str]
    actual_duration_minutes: int
    completion_status: str
    success: bool
    failure: bool
    recurrence: bool
    train_delay_minutes: int
    trains_impacted: int
    deviation_reason: Optional[str]
    created_at: datetime.datetime

class LocationQueryActivity(BaseModel):
    id: str
    task_type: str
    department: str
    origin: str
    severity: int
    start_km: float
    end_km: float
    status: str
    priority_score: int
    priority_category: str
    scheduled_start_mins: Optional[int] = None
    scheduled_end_mins: Optional[int] = None
    block_id: Optional[str] = None
    explanation: Optional[str] = None

class LocationQueryResponse(BaseModel):
    corridor_id: str
    target_chainage_km: float
    radius_km: float
    chainage_min_km: float
    chainage_max_km: float
    assets_in_range: List[AssetOut]
    maintenance_activities: List[LocationQueryActivity]
    passing_trains_count: int
    total_activities_count: int

class PriorityOverrideRequest(BaseModel):
    override_score: int = Field(..., ge=0, le=100, description="Manual priority score from dispatcher (0-100)")
    override_reason: str = Field(..., min_length=5, description="Operational justification for override")
    overridden_by: str = Field(..., description="Identity of dispatcher/controller executing override")

class PriorityOverrideResponse(BaseModel):
    task_id: str
    original_score: int
    new_score: int
    new_category: str
    overridden_by: str
    override_reason: str
    updated_at: datetime.datetime

