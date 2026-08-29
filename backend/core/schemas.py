from pydantic import BaseModel
from typing import List, Optional

class Station(BaseModel):
    id: str
    code: str
    name: str
    chainage_km: float

class TrainStop(BaseModel):
    station_id: str
    arrival_mins: int  # minutes from midnight
    departure_mins: int

class TrainSchedule(BaseModel):
    train_id: str
    type: str  # Express, Goods, Passenger
    direction: str  # Up, Down
    stops: List[TrainStop]

class MaintenanceTask(BaseModel):
    id: str
    department: str  # TMS, SMMS, TDMS
    task_type: str
    start_km: float
    end_km: float
    duration_mins: int
    base_priority: int
    deadline_mins: int
    line_direction: str

class PlannedBlock(BaseModel):
    id: str
    start_time_mins: int
    end_time_mins: int
    start_km: float
    end_km: float
    line_direction: str
    assigned_tasks: List[str]  # Task IDs
