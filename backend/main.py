from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.schemas import Station, TrainSchedule, MaintenanceTask, PlannedBlock
from services.mock_data import MOCK_STATIONS, generate_mock_timetables, generate_mock_tasks
from services.optimizer import optimize_blocks
from typing import List, Dict

app = FastAPI(title="AI-Powered Automatic Block Planning API")

# Allow CORS for local frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for MVP
timetables = generate_mock_timetables()
tasks = generate_mock_tasks()
planned_blocks = []

@app.get("/api/corridor", response_model=List[Station])
def get_corridor():
    """Returns the simulated stations and chainages."""
    return MOCK_STATIONS

@app.get("/api/timetables", response_model=List[TrainSchedule])
def get_timetables():
    """Returns the simulated train schedules."""
    return timetables

@app.get("/api/tasks", response_model=List[MaintenanceTask])
def get_tasks():
    """Returns the synthetic multi-department maintenance tasks."""
    return tasks

@app.post("/api/optimize", response_model=Dict)
def run_optimization():
    """Runs the CP-SAT optimizer to generate planned blocks."""
    global planned_blocks
    planned_blocks = optimize_blocks(tasks, timetables, safety_margin=15)
    
    # Calculate some metrics
    total_requested_mins = sum(t.duration_mins for t in tasks)
    total_granted_blocks = len(planned_blocks)
    total_granted_tasks = sum(len(b.assigned_tasks) for b in planned_blocks)
    total_block_time = sum(b.end_time_mins - b.start_time_mins for b in planned_blocks)
    
    return {
        "status": "success",
        "blocks": [b.model_dump() for b in planned_blocks],
        "metrics": {
            "total_tasks": len(tasks),
            "granted_tasks": total_granted_tasks,
            "total_requested_mins": total_requested_mins,
            "optimized_block_mins": total_block_time,
            "blocks_created": total_granted_blocks
        }
    }

@app.get("/api/blocks", response_model=List[PlannedBlock])
def get_blocks():
    """Returns the currently planned blocks."""
    return planned_blocks
