from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.schemas import Station, TrainSchedule, MaintenanceTask, MaintenanceTaskCreate, PlannedBlock, GoodsTrainForecast, OptimizeRequest, OptimizationResult, OptimizationMetrics
from services.real_corridor import CORRIDOR_STATIONS, get_real_timetables
from services.mock_data import generate_mock_tasks, generate_mock_goods_forecasts
from services.optimizer import optimize_blocks
from services.ai_prioritizer import prioritize_tasks
from typing import List, Dict, Any
import uuid

app = FastAPI(title="RailVyuha — AI-Powered Automatic Block Planning API")

# Allow CORS for local frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for MVP
# Stations and timetables: derived from real Indian Railways data (datameet/railways)
# Goods forecasts and maintenance tasks: synthetic (no public source exists)
timetables = get_real_timetables()
goods_forecasts = generate_mock_goods_forecasts()
tasks = prioritize_tasks(generate_mock_tasks(), current_time_mins=0)
planned_blocks = []

@app.get("/api/corridor", response_model=List[Station])
def get_corridor():
    """Returns corridor stations derived from real Indian Railways data (chainage is approximate)."""
    return CORRIDOR_STATIONS

@app.get("/api/timetables", response_model=List[TrainSchedule])
def get_timetables():
    """Returns train schedules derived from real Indian Railways data."""
    return timetables

@app.get("/api/goods_forecasts", response_model=List[GoodsTrainForecast])
def get_goods_forecasts():
    """Returns the simulated goods train forecasts."""
    return goods_forecasts

@app.get("/api/tasks", response_model=List[MaintenanceTask])
def get_tasks():
    """Returns the synthetic multi-department maintenance tasks."""
    return tasks

@app.post("/api/tasks", response_model=List[MaintenanceTask])
def add_task(task_in: MaintenanceTaskCreate):
    """Add a new manual task and return the updated task list."""
    global tasks
    new_task = MaintenanceTask(
        id=f"MANUAL-{uuid.uuid4().hex[:6].upper()}",
        department=task_in.department,
        task_type="Manual Block",
        origin="User Input",
        severity=task_in.severity,
        overdue_days=0,
        asset_criticality=3,
        start_km=task_in.start_km,
        end_km=task_in.end_km,
        duration_mins=task_in.duration_mins,
        deadline_mins=1440,
        line_direction="Both"
    )
    new_task = prioritize_tasks([new_task], current_time_mins=0)[0]
    tasks.append(new_task)
    return tasks

@app.post("/api/optimize", response_model=Dict[str, Any])
def run_optimization(request: OptimizeRequest = OptimizeRequest()):
    """Runs the CP-SAT optimizer to generate planned blocks."""
    global planned_blocks
    planned_blocks, status_map = optimize_blocks(
        tasks, timetables, goods_forecasts, 
        horizon_days=request.horizon_days, 
        safety_margin=15
    )
    
    # Calculate detailed horizon-aware metrics
    total_requested_mins = sum(t.duration_mins for t in tasks)
    total_block_time = sum(b.end_time_mins - b.start_time_mins for b in planned_blocks)
    
    planned_tasks = sum(1 for status in status_map.values() if status == "Planned")
    deferred_tasks = sum(1 for status in status_map.values() if status == "Deferred")
    infeasible_tasks = sum(1 for status in status_map.values() if status == "Infeasible")
    
    # High priority is score >= 60 (Critical and High)
    high_priority_planned = sum(1 for t in tasks if status_map.get(t.id) == "Planned" and (t.priority_details.score >= 60 if t.priority_details else False))
    high_priority_deferred = sum(1 for t in tasks if status_map.get(t.id) == "Deferred" and (t.priority_details.score >= 60 if t.priority_details else False))
    
    downtime_reduction_pct = 0.0
    if total_requested_mins > 0:
        downtime_reduction_pct = ((total_requested_mins - total_block_time) / total_requested_mins) * 100
        
    metrics = OptimizationMetrics(
        total_tasks=len(tasks),
        planned_tasks=planned_tasks,
        deferred_tasks=deferred_tasks,
        infeasible_tasks=infeasible_tasks,
        blocks_created=len(planned_blocks),
        total_block_minutes=total_block_time,
        total_requested_maintenance_minutes=total_requested_mins,
        downtime_reduction_pct=downtime_reduction_pct,
        high_priority_planned=high_priority_planned,
        high_priority_deferred=high_priority_deferred
    )
    
    # Still returning Dict so frontend block mapping does not break immediately, 
    # but we include the new metrics object.
    return {
        "status": "success",
        "blocks": [b.model_dump() for b in planned_blocks],
        "metrics": metrics.model_dump(),
        "task_statuses": status_map
    }

@app.get("/api/blocks", response_model=List[PlannedBlock])
def get_blocks():
    """Returns the currently planned blocks."""
    return planned_blocks
