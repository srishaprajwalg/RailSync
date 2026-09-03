import pytest
from backend.db.models import (
    MaintenanceRequest,
    MLPrediction,
    PriorityDecision,
    OptimizationRun,
    PlannedBlock,
    BlockTask,
    ScheduleDecision,
    MaintenanceOutcome,
    MaintenanceHistory,
)
from backend.services.ml_engine import predict_maintenance_recurrence
from backend.services.ai_prioritizer import calculate_and_persist_priority
from backend.services.optimizer import optimize_blocks
from backend.core.schemas import TrainSchedule, GoodsTrainForecast, MaintenanceTask, PriorityDetails

def test_complete_maintenance_lifecycle(db_session):
    # Step 1: Create a new Maintenance Request
    m_req = MaintenanceRequest(
        id="TEST-LIFECYCLE-01",
        asset_id="AST-TRK-05",
        corridor_id="SBC-JTJ",
        section_id="SEC-BWT-KPN",
        department="ENGINEERING",
        request_type="Defect",
        defect_type="Rail Fracture Repair",
        description="Emergency fracture repair on Bangarapet-Kuppam uphill track",
        status="OPEN",
        severity=5,
        criticality=5,
        start_chainage=75.0,
        end_chainage=78.0,
        line_direction="Up",
        estimated_duration_minutes=180,
        deadline_mins=1440,
        overdue_days=2,
        required_resource="Track Repair Crew",
        source_type="SYNTHETIC",
    )
    db_session.add(m_req)
    db_session.commit()

    # Step 2: Run ML Prediction
    ml_pred = predict_maintenance_recurrence(db_session, m_req)
    assert ml_pred is not None
    assert "recurrence" in ml_pred.model_name
    assert ml_pred.prediction_type == "RECURRENCE_RISK"
    assert 0.0 <= ml_pred.probability <= 1.0
    assert ml_pred.features_snapshot is not None
    assert ml_pred.features_snapshot["asset_id"] == "AST-TRK-05"

    # Step 3: Compute & Persist Explainable Priority Decision
    p_dec = calculate_and_persist_priority(db_session, m_req, current_time_mins=0, ml_pred=ml_pred)
    assert p_dec is not None
    assert p_dec.priority_score >= 80  # Critical defect with severity 5, overdue, urgency, and ML risk
    assert p_dec.priority_category == "Critical"
    assert "Defect" in p_dec.reasoning
    assert p_dec.severity_score == 30

    # Step 4: Run CP-SAT Optimization
    schema_task = MaintenanceTask(
        id=m_req.id,
        department="Engineering / Track",
        task_type=m_req.defect_type,
        origin=m_req.request_type,
        severity=m_req.severity,
        overdue_days=m_req.overdue_days,
        asset_criticality=m_req.criticality,
        start_km=m_req.start_chainage,
        end_km=m_req.end_chainage,
        duration_mins=m_req.estimated_duration_minutes,
        deadline_mins=m_req.deadline_mins,
        line_direction=m_req.line_direction,
        required_resource=m_req.required_resource,
        priority_details=PriorityDetails(score=p_dec.priority_score, category=p_dec.priority_category, explanation=p_dec.reasoning),
    )

    planned_blocks, status_map = optimize_blocks(
        tasks=[schema_task],
        schedules=[],
        forecasts=[],
        horizon_days=7,
        safety_margin=15,
        resource_capacities={"Track Repair Crew": 1},
    )

    assert len(planned_blocks) >= 1
    assert status_map[m_req.id] == "Planned"

    # Persist PlannedBlock and ScheduleDecision
    blk = planned_blocks[0]
    opt_run = OptimizationRun(
        id="OPT-TEST-01",
        corridor_id="SBC-JTJ",
        horizon_days=7,
        solver="Google OR-Tools CP-SAT",
        solver_version="9.15",
        status="COMPLETED",
        solve_time_ms=50,
    )
    db_session.add(opt_run)
    db_session.flush()

    db_blk = PlannedBlock(
        id=blk.id,
        optimization_run_id=opt_run.id,
        corridor_id="SBC-JTJ",
        start_time_mins=blk.start_time_mins,
        end_time_mins=blk.end_time_mins,
        start_chainage=blk.start_km,
        end_chainage=blk.end_km,
        direction=blk.line_direction,
        status="PLANNED",
    )
    db_session.add(db_blk)
    db_session.flush()

    bt = BlockTask(id="BT-TEST-01", block_id=db_blk.id, maintenance_request_id=m_req.id)
    db_session.add(bt)

    sched_dec = ScheduleDecision(
        id="SCD-TEST-01",
        block_id=db_blk.id,
        maintenance_request_id=m_req.id,
        selected_start_mins=blk.start_time_mins,
        selected_end_mins=blk.end_time_mins,
        why_selected="Optimal window selected within safety limits and before deadline.",
    )
    db_session.add(sched_dec)
    m_req.status = "SCHEDULED"
    db_session.commit()

    # Step 5: Record Actual Execution Outcome (Planned vs Actual)
    outcome = MaintenanceOutcome(
        id="OUT-TEST-01",
        maintenance_request_id=m_req.id,
        planned_block_id=db_blk.id,
        actual_duration_minutes=175,
        completion_status="COMPLETED",
        success=True,
        failure=False,
        recurrence=False,
        train_delay_minutes=0,
        trains_impacted=0,
        deviation_reason="Completed 5 minutes ahead of schedule.",
    )
    db_session.add(outcome)
    m_req.status = "COMPLETED"
    m_req.actual_duration_minutes = 175

    # Log to MaintenanceHistory for future ML training
    hist = MaintenanceHistory(
        id="HIST-TEST-01",
        asset_id=m_req.asset_id,
        maintenance_request_id=m_req.id,
        event_type="CORRECTIVE",
        failure_type=m_req.defect_type,
        duration_minutes=175,
        success=True,
        failure=False,
        recurrence=False,
        team="Track Maintenance Unit 4",
        notes="Repair verified with ultrasonic testing.",
    )
    db_session.add(hist)
    db_session.commit()

    # Step 6: Verify Persistence & Feedback Loop
    persisted_outcome = db_session.query(MaintenanceOutcome).filter_by(id="OUT-TEST-01").first()
    assert persisted_outcome is not None
    assert persisted_outcome.actual_duration_minutes == 175
    assert persisted_outcome.success is True

    persisted_history = db_session.query(MaintenanceHistory).filter_by(id="HIST-TEST-01").first()
    assert persisted_history is not None
    assert persisted_history.asset_id == "AST-TRK-05"
    assert persisted_history.duration_minutes == 175

    persisted_req = db_session.query(MaintenanceRequest).filter_by(id="TEST-LIFECYCLE-01").first()
    assert persisted_req.status == "COMPLETED"
    assert persisted_req.actual_duration_minutes == 175
