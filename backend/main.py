import os
import uuid
import datetime
import logging
import time
from typing import List, Dict, Any, Optional

logger = logging.getLogger("railvyuha.main")
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import or_, and_

from backend.db.session import get_db, init_db, SessionLocal
from backend.db.models import (
    Corridor,
    Section,
    Station as StationModel,
    Asset,
    Train,
    TrainRun,
    TrainMovement,
    FreightForecast,
    MaintenanceRequest,
    MaintenanceHistory,
    MLPrediction,
    PriorityDecision,
    OptimizationRun,
    PlannedBlock as PlannedBlockModel,
    BlockTask,
    ScheduleDecision,
    MaintenanceOutcome,
)
from backend.core.schemas import (
    Station,
    TrainSchedule,
    TrainStop,
    GoodsTrainForecast,
    PriorityDetails,
    MaintenanceTask,
    MaintenanceTaskCreate,
    PlannedBlock,
    OptimizeRequest,
    OptimizationMetrics,
    OptimizationResult,
    TaskStatusUpdate,
    CorridorOut,
    SectionOut,
    AssetOut,
    MaintenanceHistoryOut,
    MLPredictionOut,
    PriorityDecisionOut,
    ScheduleDecisionOut,
    MaintenanceOutcomeCreate,
    MaintenanceOutcomeOut,
    LocationQueryResponse,
    LocationQueryActivity,
    PriorityOverrideRequest,
    PriorityOverrideResponse,
)
from backend.services.seeder import seed_database
from backend.services.optimizer import optimize_blocks, explain_task_infeasibility
from backend.services.ai_prioritizer import (
    calculate_task_priority,
    calculate_and_persist_priority,
)
from backend.services.ml_engine import predict_maintenance_recurrence

logger = logging.getLogger(__name__)

app = FastAPI(title="RailVyuha — Automatic Block Planning System API")

# Allow CORS for local frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup event: Initialize database and seed if empty
@app.on_event("startup")
def on_startup():
    try:
        init_db()
        db = SessionLocal()
        try:
            seed_database(db)
        finally:
            db.close()
    except Exception as e:
        logger.warning("Startup database check/seed encountered: %s", e)

# ---------------------------------------------------------------------------
# Department & Resource Mappings
# ---------------------------------------------------------------------------
ACTIVITY_TO_DEPT = {
    "Track Tamping": "ENGINEERING",
    "Rail Fracture Repair": "ENGINEERING",
    "Routine Inspection": "ENGINEERING",
    "Point Overhaul": "S&T",
    "Signal Failure": "S&T",
    "OHE Maintenance": "TRACTION",
    "Insulator Flashover": "TRACTION",
}

# UI display mapping for backwards compatibility
DEPT_DISPLAY_MAP = {
    "ENGINEERING": "Engineering / Track",
    "S&T": "Signalling",
    "TRACTION": "Electrical / Traction",
    "TMS": "Engineering / Track",
    "SMMS": "Signalling",
    "TDMS": "Electrical / Traction",
}

ACTIVITY_TO_RESOURCE = {
    "Track Tamping": "Tamping Machine",
    "Rail Fracture Repair": "Track Repair Crew",
    "Routine Inspection": "Track Inspection Crew",
    "Point Overhaul": "Signalling Maintenance Crew",
    "Signal Failure": "Signalling Maintenance Crew",
    "OHE Maintenance": "OHE Maintenance Crew",
    "Insulator Flashover": "Electrical Response Crew",
}

RESOURCE_CAPACITY = {
    "Tamping Machine": 1,
    "Track Repair Crew": 1,
    "Track Inspection Crew": 1,
    "Signalling Maintenance Crew": 1,
    "OHE Maintenance Crew": 1,
    "Electrical Response Crew": 1,
}

TASK_DEFAULTS = {
    "Track Tamping": {"department": "Engineering / Track", "duration_mins": 120, "required_resource": "Tamping Machine"},
    "Rail Fracture Repair": {"department": "Engineering / Track", "duration_mins": 180, "required_resource": "Track Repair Crew"},
    "Point Overhaul": {"department": "Signalling", "duration_mins": 240, "required_resource": "Signalling Maintenance Crew"},
    "Signal Failure": {"department": "Signalling", "duration_mins": 60, "required_resource": "Signalling Maintenance Crew"},
    "OHE Maintenance": {"department": "Electrical / Traction", "duration_mins": 120, "required_resource": "OHE Maintenance Crew"},
    "Insulator Flashover": {"department": "Electrical / Traction", "duration_mins": 120, "required_resource": "Electrical Response Crew"},
    "Routine Inspection": {"department": "Engineering / Track", "duration_mins": 90, "required_resource": "Track Inspection Crew"},
}

def _db_request_to_schema(r: MaintenanceRequest) -> MaintenanceTask:
    dept_disp = DEPT_DISPLAY_MAP.get(r.department, r.department)
    explanation = f"Priority {r.priority_category} (Score: {r.priority_score})"
    if getattr(r, "priority_decisions", None) and len(r.priority_decisions) > 0:
        latest_dec = r.priority_decisions[-1]
        if latest_dec.reasoning:
            explanation = latest_dec.reasoning

    return MaintenanceTask(
        id=r.id,
        department=dept_disp,
        task_type=r.defect_type,
        origin=r.request_type,
        severity=r.severity,
        overdue_days=r.overdue_days,
        asset_criticality=r.criticality,
        start_km=r.start_chainage,
        end_km=r.end_chainage,
        duration_mins=r.estimated_duration_minutes,
        deadline_mins=r.deadline_mins,
        line_direction=r.line_direction,
        required_resource=r.required_resource,
        asset_id=r.asset_id,
        source_type=r.source_type,
        priority_details=PriorityDetails(
            score=r.priority_score,
            category=r.priority_category,
            explanation=explanation,
        ),
        lifecycle_status=r.status,
        rejection_reason=r.description if (r.status in ("Infeasible", "Deferred") and r.description) else None,
    )

# ---------------------------------------------------------------------------
# Infrastructure Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/corridor", response_model=List[Station])
@app.get("/api/corridors/stations", response_model=List[Station])
def get_corridor_stations(corridor_id: Optional[str] = Query("SBC-JTJ", description="Corridor ID"), db: Session = Depends(get_db)):
    """Returns corridor stations from database for the specified corridor."""
    cid = corridor_id if isinstance(corridor_id, str) else "SBC-JTJ"
    query = db.query(StationModel)
    if cid:
        sections = db.query(Section).filter_by(corridor_id=cid).all()
        sec_ids = [s.id for s in sections]
        query = query.filter(StationModel.section_id.in_(sec_ids))
    stations = query.order_by(StationModel.chainage_km).all()
    return [
        Station(
            id=s.id,
            code=s.code,
            name=s.name,
            chainage_km=s.chainage_km,
            latitude=s.latitude,
            longitude=s.longitude,
        )
        for s in stations
    ]

@app.get("/api/corridors", response_model=List[CorridorOut])
def get_corridors(db: Session = Depends(get_db)):
    """Returns all active corridors."""
    corridors = db.query(Corridor).filter_by(active=True).all()
    return [
        CorridorOut(
            id=c.id,
            code=c.code,
            name=c.name,
            description=c.description,
            total_length_km=c.total_length_km,
            active=c.active,
        )
        for c in corridors
    ]

@app.get("/api/sections", response_model=List[SectionOut])
def get_sections(corridor_id: str = "SBC-JTJ", db: Session = Depends(get_db)):
    """Returns corridor subdivisions."""
    sections = db.query(Section).filter_by(corridor_id=corridor_id).order_by(Section.start_chainage).all()
    return [
        SectionOut(
            id=s.id,
            corridor_id=s.corridor_id,
            code=s.code,
            name=s.name,
            start_chainage=s.start_chainage,
            end_chainage=s.end_chainage,
            direction=s.direction,
        )
        for s in sections
    ]

# ---------------------------------------------------------------------------
# Asset Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/assets", response_model=List[AssetOut])
def get_assets(
    corridor_id: Optional[str] = Query(None, description="Corridor ID (e.g. SBC-JTJ, NDLS-CNB, CSTM-PUNE)"),
    department: Optional[str] = Query(None, description="ALL, ENGINEERING, S&T, TRACTION"),
    section_id: Optional[str] = None,
    asset_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Returns physical railway assets backed by database."""
    cid = corridor_id if isinstance(corridor_id, str) else None
    dept_str = department if isinstance(department, str) else None
    query = db.query(Asset)
    if cid:
        query = query.filter(Asset.corridor_id == cid)
    if dept_str and dept_str.upper() != "ALL":
        dept_val = "ENGINEERING" if "ENG" in dept_str.upper() else ("S&T" if "S&T" in dept_str.upper() or "SIG" in dept_str.upper() else "TRACTION")
        query = query.filter(Asset.department == dept_val)
    if section_id:
        query = query.filter(Asset.section_id == section_id)
    if asset_type:
        query = query.filter(Asset.asset_type == asset_type.upper())

    assets = query.order_by(Asset.start_chainage).all()
    return [
        AssetOut(
            id=a.id,
            asset_code=a.asset_code,
            asset_type=a.asset_type,
            department=a.department,
            corridor_id=a.corridor_id,
            section_id=a.section_id,
            station_id=a.station_id,
            start_chainage=a.start_chainage,
            end_chainage=a.end_chainage,
            age_years=a.age_years,
            criticality=a.criticality,
            status=a.status,
            metadata_json=a.metadata_json,
        )
        for a in assets
    ]

@app.get("/api/assets/{asset_id}", response_model=AssetOut)
def get_asset(asset_id: str, db: Session = Depends(get_db)):
    """Returns a specific asset by ID."""
    asset = db.query(Asset).filter_by(id=asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return AssetOut(
        id=asset.id,
        asset_code=asset.asset_code,
        asset_type=asset.asset_type,
        department=asset.department,
        corridor_id=asset.corridor_id,
        section_id=asset.section_id,
        station_id=asset.station_id,
        start_chainage=asset.start_chainage,
        end_chainage=asset.end_chainage,
        age_years=asset.age_years,
        criticality=asset.criticality,
        status=asset.status,
        metadata_json=asset.metadata_json,
    )

# ---------------------------------------------------------------------------
# Timetables and Goods Forecasts
# ---------------------------------------------------------------------------

@app.get("/api/timetables", response_model=List[TrainSchedule])
def get_timetables(corridor_id: Optional[str] = Query(None, description="Corridor ID"), db: Session = Depends(get_db)):
    """Returns train schedules from database."""
    cid = corridor_id if isinstance(corridor_id, str) else None
    query = db.query(TrainRun).options(
        selectinload(TrainRun.movements),
        selectinload(TrainRun.train),
    )
    if cid:
        query = query.filter(TrainRun.corridor_id == cid)
    runs = query.all()
    schedules = []
    for run in runs:
        stops = [
            TrainStop(
                station_id=mv.station_code,
                arrival_mins=mv.arrival_mins,
                departure_mins=mv.departure_mins,
            )
            for mv in sorted(run.movements, key=lambda m: m.arrival_mins)
        ]
        schedules.append(
            TrainSchedule(
                train_id=run.id,
                type=run.train.category.replace("_", " ").title() if run.train else "Express",
                direction=run.direction,
                stops=stops,
            )
        )
    return schedules

@app.get("/api/goods_forecasts", response_model=List[GoodsTrainForecast])
def get_goods_forecasts(corridor_id: Optional[str] = Query(None, description="Corridor ID"), db: Session = Depends(get_db)):
    """Returns simulated goods train forecasts from database."""
    cid = corridor_id if isinstance(corridor_id, str) else None
    query = db.query(FreightForecast)
    if cid:
        query = query.filter(FreightForecast.corridor_id == cid)
    forecasts = query.all()
    return [
        GoodsTrainForecast(
            forecast_id=f.id,
            direction=f.direction,
            start_km=f.start_chainage,
            end_km=f.end_chainage,
            earliest_entry_mins=f.earliest_entry_mins,
            latest_exit_mins=f.latest_exit_mins,
            confidence=f.confidence,
            source_type=f.source_type,
        )
        for f in forecasts
    ]

# ---------------------------------------------------------------------------
# Maintenance Tasks & Requests
# ---------------------------------------------------------------------------

@app.get("/api/tasks", response_model=List[MaintenanceTask])
@app.get("/api/maintenance", response_model=List[MaintenanceTask])
def get_tasks(
    corridor_id: Optional[str] = Query(None, description="Corridor ID"),
    department: Optional[str] = Query(None, description="ALL, ENGINEERING, S&T, TRACTION"),
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Returns persistent maintenance requests."""
    cid = corridor_id if isinstance(corridor_id, str) else None
    dept_str = department if isinstance(department, str) else None
    query = db.query(MaintenanceRequest)
    if cid:
        query = query.filter(MaintenanceRequest.corridor_id == cid)
    if dept_str and dept_str.upper() != "ALL":
        dept_norm = "ENGINEERING" if "ENG" in dept_str.upper() else ("S&T" if "S&T" in dept_str.upper() or "SIG" in dept_str.upper() else "TRACTION")
        query = query.filter(MaintenanceRequest.department == dept_norm)
    if status:
        query = query.filter(MaintenanceRequest.status == status)

    from sqlalchemy.orm import selectinload
    requests = query.options(selectinload(MaintenanceRequest.priority_decisions)).order_by(MaintenanceRequest.priority_score.desc()).all()
    return [_db_request_to_schema(r) for r in requests]

@app.get("/api/tasks/defaults")
def get_task_defaults():
    """Returns baseline duration and department defaults for standard tasks."""
    return TASK_DEFAULTS

@app.post("/api/tasks/preview-priority", response_model=PriorityDetails)
def preview_priority(task_in: MaintenanceTaskCreate):
    """Preview the AI priority score without creating the task."""
    dept = ACTIVITY_TO_DEPT.get(task_in.task_type, "ENGINEERING")
    dummy_task = MaintenanceTask(
        id="PREVIEW",
        department=DEPT_DISPLAY_MAP.get(dept, dept),
        task_type=task_in.task_type,
        origin=task_in.origin,
        severity=task_in.severity,
        overdue_days=task_in.overdue_days,
        asset_criticality=task_in.asset_criticality,
        start_km=task_in.start_km,
        end_km=task_in.end_km,
        duration_mins=task_in.duration_mins,
        deadline_mins=task_in.deadline_mins,
        line_direction=task_in.line_direction,
        required_resource=ACTIVITY_TO_RESOURCE.get(task_in.task_type, "General Crew"),
        lifecycle_status="Reported",
    )
    return calculate_task_priority(dummy_task, current_time_mins=0)

@app.post("/api/tasks", response_model=List[MaintenanceTask])
@app.post("/api/maintenance", response_model=List[MaintenanceTask])
def add_task(task_in: MaintenanceTaskCreate, db: Session = Depends(get_db)):
    """Add a new task, run ML prediction + priority scoring, persist to DB, and return updated task list."""
    target_corridor_id = getattr(task_in, "corridor_id", None)
    if not target_corridor_id:
        raise HTTPException(status_code=400, detail="corridor_id is required")
    dept_norm = ACTIVITY_TO_DEPT.get(task_in.task_type, "ENGINEERING")
    task_id = f"MANUAL-{uuid.uuid4().hex[:6].upper()}"

    # Auto-match asset if not provided
    asset_id = task_in.asset_id
    if not asset_id:
        matching_asset = (
            db.query(Asset)
            .filter(
                Asset.corridor_id == target_corridor_id,
                Asset.department == dept_norm,
                Asset.start_chainage <= task_in.end_km,
                Asset.end_chainage >= task_in.start_km,
            )
            .first()
        )
        asset_id = matching_asset.id if matching_asset else None

    # Find section
    section = (
        db.query(Section)
        .filter(
            Section.corridor_id == target_corridor_id,
            Section.start_chainage <= task_in.start_km,
            Section.end_chainage >= task_in.start_km,
        )
        .first()
    )

    m_req = MaintenanceRequest(
        id=task_id,
        asset_id=asset_id,
        corridor_id=target_corridor_id,
        section_id=section.id if section else None,
        department=dept_norm,
        request_type=task_in.origin,
        defect_type=task_in.task_type,
        description=f"{task_in.origin} for {task_in.task_type} (Km {task_in.start_km:.1f} - {task_in.end_km:.1f})",
        status="Prioritized",
        severity=task_in.severity,
        criticality=task_in.asset_criticality,
        start_chainage=task_in.start_km,
        end_chainage=task_in.end_km,
        line_direction=task_in.line_direction,
        estimated_duration_minutes=task_in.duration_mins,
        deadline_mins=task_in.deadline_mins,
        overdue_days=task_in.overdue_days,
        required_resource=ACTIVITY_TO_RESOURCE.get(task_in.task_type, "General Crew"),
        source_type="SYNTHETIC",
    )
    db.add(m_req)
    db.flush()

    # Run ML prediction
    ml_pred = predict_maintenance_recurrence(db, m_req)

    # Compute and persist explainable priority decision
    calculate_and_persist_priority(db, m_req, current_time_mins=0, ml_pred=ml_pred)

    db.commit()

    # Return full updated task list for this corridor
    requests = db.query(MaintenanceRequest).filter(MaintenanceRequest.corridor_id == target_corridor_id).order_by(MaintenanceRequest.priority_score.desc()).all()
    return [_db_request_to_schema(r) for r in requests]

@app.put("/api/tasks/{task_id}/status", response_model=List[MaintenanceTask])
@app.patch("/api/maintenance/{task_id}")
def update_task_status(task_id: str, status_update: TaskStatusUpdate, db: Session = Depends(get_db)):
    """Update a task's lifecycle status in the database."""
    req = db.query(MaintenanceRequest).filter_by(id=task_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Maintenance task not found")

    req.status = status_update.lifecycle_status
    db.commit()

    requests = db.query(MaintenanceRequest).order_by(MaintenanceRequest.priority_score.desc()).all()
    return [_db_request_to_schema(r) for r in requests]

@app.get("/api/maintenance/{task_id}/history", response_model=List[MaintenanceHistoryOut])
def get_task_history(task_id: str, db: Session = Depends(get_db)):
    """Returns historical maintenance records for the asset associated with a task."""
    req = db.query(MaintenanceRequest).filter_by(id=task_id).first()
    if not req or not req.asset_id:
        return []
    history = db.query(MaintenanceHistory).filter_by(asset_id=req.asset_id).order_by(MaintenanceHistory.created_at.desc()).all()
    return [
        MaintenanceHistoryOut(
            id=h.id,
            asset_id=h.asset_id,
            maintenance_request_id=h.maintenance_request_id,
            event_type=h.event_type,
            failure_type=h.failure_type,
            started_at=h.started_at,
            completed_at=h.completed_at,
            duration_minutes=h.duration_minutes,
            success=h.success,
            failure=h.failure,
            recurrence=h.recurrence,
            team=h.team,
            notes=h.notes,
            created_at=h.created_at,
        )
        for h in history
    ]

@app.get("/api/analytics/lifecycle")
def get_lifecycle_counts(
    corridor_id: Optional[str] = Query(None, description="Corridor ID"),
    department: Optional[str] = Query(None, description="Department Scope"),
    db: Session = Depends(get_db)
):
    req_query = db.query(MaintenanceRequest)
    if corridor_id:
        req_query = req_query.filter(MaintenanceRequest.corridor_id == corridor_id)
    if department and department.upper() != "ALL":
        dept_norm = "ENGINEERING" if "ENG" in department.upper() else ("S&T" if "S&T" in department.upper() or "SIG" in department.upper() else "TRACTION")
        req_query = req_query.filter(MaintenanceRequest.department == dept_norm)

    requests = req_query.all()
    counts = {"Pending": 0, "Scheduled": 0, "In Progress": 0, "Completed": 0, "Deferred": 0, "Infeasible": 0}

    for r in requests:
        st = r.status.capitalize() if r.status else "Pending"
        if st in ["Open", "Prioritized"]:
            counts["Pending"] += 1
        elif st == "Scheduled":
            counts["Scheduled"] += 1
        elif st == "In progress" or st == "In Progress":
            counts["In Progress"] += 1
        elif st == "Completed":
            counts["Completed"] += 1
        elif st == "Deferred":
            counts["Deferred"] += 1
        elif st == "Infeasible":
            counts["Infeasible"] += 1
        else:
            counts["Pending"] += 1

    hist_query = db.query(MaintenanceHistory)
    if corridor_id or (department and department.upper() != "ALL"):
        hist_query = hist_query.join(Asset, MaintenanceHistory.asset_id == Asset.id)
        if corridor_id:
            hist_query = hist_query.filter(Asset.corridor_id == corridor_id)
        if department and department.upper() != "ALL":
            dept_norm = "ENGINEERING" if "ENG" in department.upper() else ("S&T" if "S&T" in department.upper() or "SIG" in department.upper() else "TRACTION")
            hist_query = hist_query.filter(Asset.department == dept_norm)

    counts["Completed"] += hist_query.count()
    return [{"name": k, "value": v} for k, v in counts.items() if v > 0]

@app.get("/api/predictions/{maintenance_id}", response_model=List[MLPredictionOut])
def get_task_predictions(maintenance_id: str, db: Session = Depends(get_db)):
    """Returns ML recurrence risk predictions for a maintenance request."""
    preds = db.query(MLPrediction).filter_by(maintenance_request_id=maintenance_id).order_by(MLPrediction.created_at.desc()).all()
    return [
        MLPredictionOut(
            id=p.id,
            maintenance_request_id=p.maintenance_request_id,
            asset_id=p.asset_id,
            model_name=p.model_name,
            model_version=p.model_version,
            prediction_type=p.prediction_type,
            prediction=p.prediction,
            probability=p.probability,
            confidence=p.confidence,
            features_snapshot=p.features_snapshot,
            created_at=p.created_at,
        )
        for p in preds
    ]

@app.get("/api/priority/{maintenance_id}", response_model=PriorityDecisionOut)
def get_priority_decision(maintenance_id: str, db: Session = Depends(get_db)):
    """Returns the latest explainable priority scoring decision for a task."""
    dec = db.query(PriorityDecision).filter_by(maintenance_request_id=maintenance_id).order_by(PriorityDecision.created_at.desc()).first()
    if not dec:
        raise HTTPException(status_code=404, detail="Priority decision not found")
    return PriorityDecisionOut(
        id=dec.id,
        maintenance_request_id=dec.maintenance_request_id,
        priority_score=dec.priority_score,
        priority_category=dec.priority_category,
        ml_risk_score=dec.ml_risk_score,
        severity_score=dec.severity_score,
        criticality_score=dec.criticality_score,
        urgency_score=dec.urgency_score,
        overdue_score=dec.overdue_score,
        operational_impact_score=dec.operational_impact_score,
        reasoning=dec.reasoning,
        engine_version=dec.engine_version,
        created_at=dec.created_at,
    )

# ---------------------------------------------------------------------------
# CP-SAT Optimization Runs & Planned Blocks
# ---------------------------------------------------------------------------

@app.post("/api/optimize", response_model=Dict[str, Any])
def run_optimization(request: OptimizeRequest = OptimizeRequest(), db: Session = Depends(get_db)):
    """
    Executes Google OR-Tools CP-SAT scheduler against persistent database entities,
    stores optimization runs, planned blocks, and schedule decisions into PostgreSQL.
    """
    start_time = datetime.datetime.now()
    t0_wall = time.time()

    # 1. Fetch active tasks, schedules, and forecasts from DB
    t_fetch_start = time.time()
    from sqlalchemy.orm import selectinload
    query = db.query(MaintenanceRequest).options(selectinload(MaintenanceRequest.priority_decisions)).filter(
        MaintenanceRequest.corridor_id == request.corridor_id,
        MaintenanceRequest.status.notin_(["Completed", "COMPLETED", "CANCELLED"])
    )
    if request.department and request.department != "ALL":
        query = query.filter(MaintenanceRequest.department == request.department)
    db_requests = query.all()
    tasks = [_db_request_to_schema(r) for r in db_requests]

    timetables = get_timetables(corridor_id=request.corridor_id, db=db)
    goods_forecasts = get_goods_forecasts(corridor_id=request.corridor_id, db=db)
    t_fetch_ms = int((time.time() - t_fetch_start) * 1000)

    # 2. Run CP-SAT solver
    t_opt_start = time.time()
    planned_blocks, status_map = optimize_blocks(
        tasks, timetables, goods_forecasts,
        horizon_days=request.horizon_days,
        safety_margin=15,
        resource_capacities=RESOURCE_CAPACITY,
    )
    t_opt_ms = int((time.time() - t_opt_start) * 1000)

    solve_time_ms = int((datetime.datetime.now() - start_time).total_seconds() * 1000)

    # 3. Calculate metrics
    total_requested_mins = sum(t.duration_mins for t in tasks)
    total_block_time = sum(b.end_time_mins - b.start_time_mins for b in planned_blocks)

    planned_tasks = sum(1 for status in status_map.values() if status == "Planned")
    deferred_tasks = sum(1 for status in status_map.values() if status == "Deferred")
    infeasible_tasks = sum(1 for status in status_map.values() if status == "Infeasible")

    high_priority_planned = sum(
        1 for t in tasks if status_map.get(t.id) == "Planned" and (t.priority_details.score >= 60 if t.priority_details else False)
    )
    high_priority_deferred = sum(
        1 for t in tasks if status_map.get(t.id) == "Deferred" and (t.priority_details.score >= 60 if t.priority_details else False)
    )

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
        high_priority_deferred=high_priority_deferred,
    )

    # 4. Persist OptimizationRun, PlannedBlocks, BlockTasks, and ScheduleDecisions to DB
    t_persist_start = time.time()
    run_id = f"OPT-{uuid.uuid4().hex[:8].upper()}"

    blocks_to_add: List[PlannedBlockModel] = []
    block_tasks_to_add: List[BlockTask] = []
    decisions_to_add: List[ScheduleDecision] = []

    for blk in planned_blocks:
        blk_db = PlannedBlockModel(
            id=blk.id,
            optimization_run_id=run_id,
            corridor_id=request.corridor_id,
            start_time_mins=blk.start_time_mins,
            end_time_mins=blk.end_time_mins,
            start_chainage=blk.start_km,
            end_chainage=blk.end_km,
            direction=blk.line_direction,
            status="PLANNED",
            reasoning=blk.reasoning or f"Optimized {blk.line_direction} window between train paths spanning Km {blk.start_km:.1f} to {blk.end_km:.1f}",
        )
        blocks_to_add.append(blk_db)

        for t_id in blk.assigned_tasks:
            bt = BlockTask(
                id=f"BT-{uuid.uuid4().hex[:8].upper()}",
                block_id=blk.id,
                maintenance_request_id=t_id,
            )
            block_tasks_to_add.append(bt)

            # Look up actual task priority details
            t_req = next((req for req in db_requests if req.id == t_id), None)
            priority_str = f"Score {t_req.priority_score} ({t_req.priority_category})" if t_req else "Score N/A"
            ml_risk = "N/A"
            if t_req and getattr(t_req, 'priority_decisions', None) and len(t_req.priority_decisions) > 0:
                ml_risk = f"{t_req.priority_decisions[-1].ml_risk_score} pts"

            sched_dec = ScheduleDecision(
                id=f"SCD-{uuid.uuid4().hex[:8].upper()}",
                block_id=blk.id,
                maintenance_request_id=t_id,
                selected_start_mins=blk.start_time_mins,
                selected_end_mins=blk.end_time_mins,
                why_selected=f"Task {t_id} (Priority: {priority_str}, ML Risk: {ml_risk}) assigned to gap (Mins {blk.start_time_mins}–{blk.end_time_mins}, Day {blk.start_time_mins//1440})",
                train_constraints=f"Zero conflicting trains for Km {blk.start_km:.1f}–{blk.end_km:.1f} (±15m safety margin)",
                spatial_constraints=f"Spans corridor Km {blk.start_km:.1f} to {blk.end_km:.1f} ({blk.end_km - blk.start_km:.1f} km span)",
                department_coordination="Multi-department consolidated block" if len(blk.assigned_tasks) > 1 else "Standalone single activity block",
                solver_reason="CP-SAT Optimal Interval Assignment",
            )
            decisions_to_add.append(sched_dec)

    # 5. Update request status and explain rejections in DB
    task_rejection_reasons = {}
    for r in db_requests:
        s = status_map.get(r.id)
        if s == "Planned":
            r.status = "Scheduled"
        elif s == "Deferred":
            r.status = "Deferred"
            reason = "Feasible alone, but deferred by CP-SAT solver to avoid conflict with higher-priority maintenance tasks or corridor capacity limits."
            r.description = reason
            task_rejection_reasons[r.id] = reason
        elif s == "Infeasible":
            r.status = "Infeasible"
            t_schema = _db_request_to_schema(r)
            reason = explain_task_infeasibility(t_schema, timetables, goods_forecasts, request.horizon_days * 1440, safety_margin=15)
            r.description = reason
            task_rejection_reasons[r.id] = reason

    # Pre-populate timing_breakdown on metrics_json before insert to avoid subsequent UPDATE
    t_persist_prep_ms = int((time.time() - t_persist_start) * 1000)
    t_prep_total_ms = int((time.time() - t0_wall) * 1000)

    metrics_data = metrics.model_dump()
    metrics_data["timing_breakdown"] = {
        "db_fetch_ms": t_fetch_ms,
        "optimization_ms": t_opt_ms,
        "db_persist_ms": t_persist_prep_ms,
        "total_ms": t_prep_total_ms,
    }

    opt_run = OptimizationRun(
        id=run_id,
        corridor_id=request.corridor_id,
        horizon_days=request.horizon_days,
        solver="Google OR-Tools CP-SAT",
        solver_version="9.15",
        objective_version="v2.0-hierarchical",
        status="COMPLETED",
        solve_time_ms=solve_time_ms,
        metrics_json=metrics_data,
    )

    # Batch session registration using Unit-of-Work
    db.add(opt_run)
    db.add_all(blocks_to_add)
    db.add_all(block_tasks_to_add)
    db.add_all(decisions_to_add)

    # Single commit
    db.commit()

    t_final_persist_ms = int((time.time() - t_persist_start) * 1000)
    t_final_total_ms = int((time.time() - t0_wall) * 1000)

    logger.info(
        "Optimization run %s completed in %dms (DB fetch: %dms | Optimization: %dms | DB persist: %dms)",
        run_id, t_final_total_ms, t_fetch_ms, t_opt_ms, t_final_persist_ms
    )

    return {
        "status": "success",
        "blocks": [b.model_dump() for b in planned_blocks],
        "metrics": metrics.model_dump(),
        "task_statuses": status_map,
        "task_rejection_reasons": task_rejection_reasons,
    }

@app.get("/api/blocks", response_model=List[PlannedBlock])
def get_blocks(
    corridor_id: Optional[str] = Query(None, description="Corridor ID"),
    department: Optional[str] = Query(None, description="Department Scope"),
    db: Session = Depends(get_db)
):
    """Returns the latest planned blocks from database for the specified corridor."""
    cid = corridor_id if isinstance(corridor_id, str) else None
    query = db.query(OptimizationRun)
    if cid:
        query = query.filter(OptimizationRun.corridor_id == cid)
    latest_run = query.order_by(OptimizationRun.created_at.desc()).first()
    if not latest_run:
        return []

    db_blocks = (
        db.query(PlannedBlockModel)
        .options(selectinload(PlannedBlockModel.block_tasks).joinedload(BlockTask.maintenance_request))
        .filter_by(optimization_run_id=latest_run.id)
        .all()
    )

    filtered_blocks = []
    for b in db_blocks:
        if department and department != "ALL":
            has_dept = any(bt.maintenance_request.department == department for bt in b.block_tasks if bt.maintenance_request)
            if not has_dept:
                continue
        filtered_blocks.append(b)

    return [
        PlannedBlock(
            id=b.id,
            start_time_mins=b.start_time_mins,
            end_time_mins=b.end_time_mins,
            start_km=b.start_chainage,
            end_km=b.end_chainage,
            line_direction=b.direction,
            assigned_tasks=[bt.maintenance_request_id for bt in b.block_tasks],
            reasoning=b.reasoning,
        )
        for b in filtered_blocks
    ]

@app.get("/api/blocks/{block_id}/decisions", response_model=List[ScheduleDecisionOut])
def get_block_decisions(block_id: str, db: Session = Depends(get_db)):
    """Returns all schedule decisions for tasks assigned to a planned block."""
    decisions = db.query(ScheduleDecision).filter_by(block_id=block_id).all()
    return [
        ScheduleDecisionOut(
            id=d.id,
            block_id=d.block_id,
            maintenance_request_id=d.maintenance_request_id,
            selected_start_mins=d.selected_start_mins,
            selected_end_mins=d.selected_end_mins,
            why_selected=d.why_selected,
            train_constraints=d.train_constraints,
            spatial_constraints=d.spatial_constraints,
            department_coordination=d.department_coordination,
            priority_reason=d.priority_reason,
            solver_reason=d.solver_reason,
        )
        for d in decisions
    ]

@app.get("/api/optimization/runs/latest")
def get_latest_optimization_run(corridor_id: Optional[str] = Query(None, description="Corridor ID"), db: Session = Depends(get_db)):
    """Returns the most recent CP-SAT optimization run and its metrics."""
    cid = corridor_id if isinstance(corridor_id, str) else None
    query = db.query(OptimizationRun)
    if cid:
        query = query.filter(OptimizationRun.corridor_id == cid)
    latest_run = query.order_by(OptimizationRun.created_at.desc()).first()
    if not latest_run:
        raise HTTPException(status_code=404, detail="No optimization run found")
    return {
        "id": latest_run.id,
        "corridor_id": latest_run.corridor_id,
        "horizon_days": latest_run.horizon_days,
        "solver": latest_run.solver,
        "solver_version": latest_run.solver_version,
        "objective_version": latest_run.objective_version,
        "status": latest_run.status,
        "solve_time_ms": latest_run.solve_time_ms,
        "metrics": latest_run.metrics_json,
        "created_at": latest_run.created_at,
    }

@app.post("/api/tasks/{task_id}/override-priority", response_model=PriorityOverrideResponse)
def override_task_priority(
    task_id: str,
    override_req: PriorityOverrideRequest,
    db: Session = Depends(get_db),
):
    """
    Enables Section Engineers / Chief Controllers to manually override AI priority scores
    with full audit trail and reason documentation.
    """
    req = db.query(MaintenanceRequest).filter_by(id=task_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Maintenance task not found")

    original_score = req.priority_score
    new_score = override_req.override_score

    if new_score >= 80:
        new_category = "Critical"
    elif new_score >= 60:
        new_category = "High"
    elif new_score >= 40:
        new_category = "Medium"
    else:
        new_category = "Low"

    req.priority_score = new_score
    req.priority_category = new_category

    p_dec = db.query(PriorityDecision).filter_by(maintenance_request_id=task_id).first()
    now = datetime.datetime.now(datetime.timezone.utc)
    if p_dec:
        p_dec.priority_score = new_score
        p_dec.priority_category = new_category
        p_dec.engine_version = "v2.1-dispatcher-override"
        p_dec.reasoning = (
            f"Manual priority override by {override_req.overridden_by} (Score: {original_score} -> {new_score}). "
            f"Justification: {override_req.override_reason}"
        )
    else:
        p_dec = PriorityDecision(
            id=f"PRD-{uuid.uuid4().hex[:8].upper()}",
            maintenance_request_id=task_id,
            priority_score=new_score,
            priority_category=new_category,
            severity_score=req.severity * 6,
            criticality_score=req.criticality * 4,
            urgency_score=20 if req.deadline_mins <= 1440 else 10,
            overdue_score=min(20, req.overdue_days * 2),
            ml_risk_score=0,
            operational_impact_score=5,
            engine_version="v2.1-dispatcher-override",
            reasoning=f"Manual priority override by {override_req.overridden_by}: {override_req.override_reason}",
        )
        db.add(p_dec)

    db.commit()

    return PriorityOverrideResponse(
        task_id=task_id,
        original_score=original_score,
        new_score=new_score,
        new_category=new_category,
        overridden_by=override_req.overridden_by,
        override_reason=override_req.override_reason,
        updated_at=now,
    )


# ---------------------------------------------------------------------------
# Planned vs Actual Outcomes & ML Feedback Loop
# ---------------------------------------------------------------------------

@app.post("/api/outcomes", response_model=MaintenanceOutcomeOut)
def record_maintenance_outcome(outcome_in: MaintenanceOutcomeCreate, db: Session = Depends(get_db)):
    """
    Records actual maintenance execution outcome, transitions request to COMPLETED,
    and appends a new record to MaintenanceHistory to enable ML model retraining feedback loop.
    """
    req = db.query(MaintenanceRequest).filter_by(id=outcome_in.maintenance_request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Maintenance request not found")

    outcome_id = f"OUT-{uuid.uuid4().hex[:8].upper()}"
    outcome = MaintenanceOutcome(
        id=outcome_id,
        maintenance_request_id=req.id,
        planned_block_id=outcome_in.planned_block_id,
        actual_duration_minutes=outcome_in.actual_duration_minutes,
        completion_status=outcome_in.completion_status,
        success=outcome_in.success,
        failure=not outcome_in.success,
        recurrence=outcome_in.recurrence,
        train_delay_minutes=outcome_in.train_delay_minutes,
        trains_impacted=outcome_in.trains_impacted,
        deviation_reason=outcome_in.deviation_reason,
    )
    db.add(outcome)

    # Update request state
    req.status = "Completed" if outcome_in.success else "Failed"
    req.actual_duration_minutes = outcome_in.actual_duration_minutes

    # Append to MaintenanceHistory for future ML training
    if req.asset_id:
        now = datetime.datetime.now(datetime.timezone.utc)
        hist = MaintenanceHistory(
            id=f"HIST-{uuid.uuid4().hex[:8].upper()}",
            asset_id=req.asset_id,
            maintenance_request_id=req.id,
            event_type="CORRECTIVE" if req.request_type.lower() == "defect" else "PREVENTIVE",
            failure_type=req.defect_type,
            started_at=now - datetime.timedelta(minutes=outcome_in.actual_duration_minutes),
            completed_at=now,
            duration_minutes=outcome_in.actual_duration_minutes,
            success=outcome_in.success,
            failure=not outcome_in.success,
            recurrence=outcome_in.recurrence,
            team="Field Execution Crew",
            notes=f"Outcome recorded: {outcome_in.completion_status}. Delays: {outcome_in.train_delay_minutes} mins. Deviation: {outcome_in.deviation_reason or 'None'}",
        )
        db.add(hist)

    db.commit()

    return MaintenanceOutcomeOut(
        id=outcome.id,
        maintenance_request_id=outcome.maintenance_request_id,
        planned_block_id=outcome.planned_block_id,
        actual_duration_minutes=outcome.actual_duration_minutes,
        completion_status=outcome.completion_status,
        success=outcome.success,
        failure=outcome.failure,
        recurrence=outcome.recurrence,
        train_delay_minutes=outcome.train_delay_minutes,
        trains_impacted=outcome.trains_impacted,
        deviation_reason=outcome.deviation_reason,
        created_at=outcome.created_at or datetime.datetime.now(datetime.timezone.utc),
    )

@app.get("/api/outcomes", response_model=List[MaintenanceOutcomeOut])
def get_outcomes(db: Session = Depends(get_db)):
    """Returns recorded maintenance execution outcomes."""
    outcomes = db.query(MaintenanceOutcome).order_by(MaintenanceOutcome.created_at.desc()).all()
    return [
        MaintenanceOutcomeOut(
            id=o.id,
            maintenance_request_id=o.maintenance_request_id,
            planned_block_id=o.planned_block_id,
            actual_duration_minutes=o.actual_duration_minutes,
            completion_status=o.completion_status,
            success=o.success,
            failure=o.failure,
            recurrence=o.recurrence,
            train_delay_minutes=o.train_delay_minutes,
            trains_impacted=o.trains_impacted,
            deviation_reason=o.deviation_reason,
            created_at=o.created_at,
        )
        for o in outcomes
    ]

# ---------------------------------------------------------------------------
# Location Query (e.g. KM 76.5 ± 5 km)
# ---------------------------------------------------------------------------

@app.get("/api/location-query", response_model=LocationQueryResponse)
def location_query(
    chainage: float = Query(76.5, description="Target chainage in KM (e.g. 76.5)"),
    radius_km: float = Query(5.0, ge=0.5, le=50.0, description="Search radius in KM (e.g. 5.0)"),
    corridor_id: str = Query("SBC-JTJ", description="Corridor ID"),
    db: Session = Depends(get_db),
):
    """
    Geospatial & chainage radius search querying assets, maintenance tasks,
    scheduled blocks, and passing train density in [chainage - radius, chainage + radius].
    """
    km_min = max(0.0, chainage - radius_km)
    km_max = chainage + radius_km

    # 1. Assets in range
    assets = (
        db.query(Asset)
        .filter(
            Asset.corridor_id == corridor_id,
            Asset.start_chainage <= km_max,
            Asset.end_chainage >= km_min,
        )
        .all()
    )

    # 2. Maintenance requests in range
    m_requests = (
        db.query(MaintenanceRequest)
        .filter(
            MaintenanceRequest.corridor_id == corridor_id,
            MaintenanceRequest.start_chainage <= km_max,
            MaintenanceRequest.end_chainage >= km_min,
        )
        .all()
    )

    activities = []
    for r in m_requests:
        activities.append(
            LocationQueryActivity(
                id=r.id,
                task_type=r.defect_type,
                department=DEPT_DISPLAY_MAP.get(r.department, r.department),
                origin=r.request_type,
                severity=r.severity,
                start_km=r.start_chainage,
                end_km=r.end_chainage,
                status=r.status,
                priority_score=r.priority_score,
                priority_category=r.priority_category,
                explanation=f"At Km {r.start_chainage:.1f}–{r.end_chainage:.1f} ({r.department})",
            )
        )

    # 3. Passing trains in section
    trains_count = (
        db.query(TrainMovement)
        .join(TrainRun, TrainMovement.train_run_id == TrainRun.id)
        .filter(
            TrainRun.corridor_id == corridor_id,
            TrainMovement.chainage_km >= km_min,
            TrainMovement.chainage_km <= km_max,
        )
        .count()
    )

    return LocationQueryResponse(
        corridor_id=corridor_id,
        target_chainage_km=chainage,
        radius_km=radius_km,
        chainage_min_km=km_min,
        chainage_max_km=km_max,
        assets_in_range=[
            AssetOut(
                id=a.id,
                asset_code=a.asset_code,
                asset_type=a.asset_type,
                department=a.department,
                corridor_id=a.corridor_id,
                section_id=a.section_id,
                station_id=a.station_id,
                start_chainage=a.start_chainage,
                end_chainage=a.end_chainage,
                age_years=a.age_years,
                criticality=a.criticality,
                status=a.status,
                metadata_json=a.metadata_json,
            )
            for a in assets
        ],
        maintenance_activities=activities,
        passing_trains_count=trains_count,
        total_activities_count=len(activities),
    )
