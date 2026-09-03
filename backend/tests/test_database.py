import pytest
from backend.db.models import (
    Corridor,
    Section,
    Station,
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
    PlannedBlock,
    BlockTask,
    ScheduleDecision,
)
from backend.db.session import normalize_database_url, DatabaseConfigurationError
from backend.db.verify_cloud_db import verify_database_connection, mask_connection_url

def test_corridor_and_infrastructure(db_session):
    corridor = db_session.query(Corridor).filter_by(id="SBC-JTJ").first()
    assert corridor is not None
    assert corridor.code == "SBC-JTJ"
    assert corridor.total_length_km == 145.0
    assert corridor.active is True

    # 4 sections
    sections = db_session.query(Section).filter_by(corridor_id=corridor.id).all()
    assert len(sections) == 4

    # 7 stations
    stations = db_session.query(Station).order_by(Station.chainage_km).all()
    assert len(stations) == 7
    assert stations[0].code == "SBC"
    assert stations[-1].code == "JTJ"
    assert stations[-1].chainage_km == 145.0

def test_assets_by_department(db_session):
    assets = db_session.query(Asset).filter_by(corridor_id="SBC-JTJ").all()
    assert len(assets) >= 20

    eng_assets = [a for a in assets if a.department == "ENGINEERING"]
    st_assets = [a for a in assets if a.department == "S&T"]
    trac_assets = [a for a in assets if a.department == "TRACTION"]

    assert len(eng_assets) >= 8
    assert len(st_assets) >= 6
    assert len(trac_assets) >= 4

    # Verify foreign key / relationship
    for a in assets:
        assert a.corridor_id == "SBC-JTJ"
        assert a.age_years >= 0.0
        assert 1 <= a.criticality <= 5

def test_maintenance_history_and_failures(db_session):
    history = db_session.query(MaintenanceHistory).all()
    assert len(history) >= 8

    recurrent_failures = [h for h in history if h.recurrence]
    assert len(recurrent_failures) > 0

    # Ensure linked assets exist
    for h in history:
        assert h.asset_id is not None
        assert h.asset is not None

def test_trains_and_movements(db_session):
    trains = db_session.query(Train).all()
    assert len(trains) > 0

    runs = db_session.query(TrainRun).all()
    assert len(runs) > 0

    movements = db_session.query(TrainMovement).all()
    assert len(movements) > 0

    # Verify source type
    for t in trains:
        assert t.source_type == "REAL"

def test_freight_forecasts(db_session):
    forecasts = db_session.query(FreightForecast).all()
    assert len(forecasts) > 0
    for f in forecasts:
        assert f.source_type == "SYNTHETIC"
        assert f.earliest_entry_mins < f.latest_exit_mins

def test_maintenance_requests_and_lifecycle(db_session):
    requests = db_session.query(MaintenanceRequest).all()
    assert len(requests) == 420

    for r in requests:
        assert r.source_type == "SYNTHETIC"
        assert r.department in ["ENGINEERING", "S&T", "TRACTION"]
        assert 0 <= r.priority_score <= 100
        assert r.priority_category in ["Critical", "High", "Medium", "Low"]
        assert r.status in ["OPEN", "PRIORITIZED", "SCHEDULED", "IN_PROGRESS", "COMPLETED", "DEFERRED", "CANCELLED", "FAILED"]

def test_ml_predictions_and_explainable_priority(db_session):
    preds = db_session.query(MLPrediction).all()
    assert len(preds) == 420
    for p in preds:
        assert "recurrence" in p.model_name or p.model_name == "asset_recurrence_risk_v1"
        assert 0.0 <= p.probability <= 1.0
        assert p.features_snapshot is not None

    p_decs = db_session.query(PriorityDecision).all()
    assert len(p_decs) == 420
    for pd in p_decs:
        assert 0 <= pd.priority_score <= 100
        assert pd.reasoning is not None
        assert len(pd.reasoning) > 0

def test_database_url_normalization():
    # 1. Plain postgresql://
    url1 = "postgresql://user:pass@ep-cool-db.aws.neon.tech/railvyuha"
    norm1 = normalize_database_url(url1)
    assert norm1.startswith("postgresql+psycopg://")

    # 2. Heroku/legacy postgres://
    url2 = "postgres://user:pass@ec2-54.compute-1.amazonaws.com:5432/dbrand"
    norm2 = normalize_database_url(url2)
    assert norm2.startswith("postgresql+psycopg://")

    # 3. Already valid psycopg format
    url3 = "postgresql+psycopg://admin:secret@localhost:5432/railvyuha"
    norm3 = normalize_database_url(url3)
    assert norm3 == url3

    # 4. Masking for logs
    masked = mask_connection_url("postgresql+psycopg://admin:super_secret_pw@db.cloud.net:5432/prod")
    assert "super_secret_pw" not in masked
    assert "admin:****@db.cloud.net" in masked

    # 5. Sanitized connection info
    from backend.db.session import get_sanitized_connection_info
    info = get_sanitized_connection_info("postgresql+psycopg://admin:super_secret_pw@db.cloud.net:5432/prod")
    assert info["host"] == "db.cloud.net"
    assert info["port"] == 5432
    assert info["database"] == "prod"
    assert info["username"] == "admin"
    assert "super_secret_pw" not in str(info.values())

def test_verify_database_connection_structure():
    rep = verify_database_connection()
    assert "status" in rep
    assert "url_masked" in rep
    assert "tables_expected" in rep
    assert rep["tables_expected"] == 17

def test_batched_persistence_unit_of_work_and_rollback(db_session):
    import uuid
    # Pick 2 existing requests for foreign keys
    reqs = db_session.query(MaintenanceRequest).limit(2).all()
    assert len(reqs) == 2

    run_id = f"TEST-OPT-{uuid.uuid4().hex[:8].upper()}"
    opt_run = OptimizationRun(
        id=run_id,
        corridor_id="SBC-JTJ",
        horizon_days=30,
        solver="Google OR-Tools CP-SAT",
        status="COMPLETED",
        solve_time_ms=1200,
        metrics_json={"test": True}
    )

    blocks = []
    block_tasks = []
    decisions = []

    for i in range(3):
        b_id = f"TEST-BLK-{uuid.uuid4().hex[:8].upper()}"
        blk = PlannedBlock(
            id=b_id,
            optimization_run_id=run_id,
            corridor_id="SBC-JTJ",
            start_time_mins=i * 120,
            end_time_mins=(i + 1) * 120,
            start_chainage=10.0,
            end_chainage=20.0,
            direction="Up",
            status="PLANNED",
            reasoning="Test batched persistence"
        )
        blocks.append(blk)

        for r in reqs:
            bt = BlockTask(
                id=f"TEST-BT-{uuid.uuid4().hex[:8].upper()}",
                block_id=b_id,
                maintenance_request_id=r.id,
            )
            block_tasks.append(bt)

            sd = ScheduleDecision(
                id=f"TEST-SCD-{uuid.uuid4().hex[:8].upper()}",
                block_id=b_id,
                maintenance_request_id=r.id,
                selected_start_mins=i * 120,
                selected_end_mins=(i + 1) * 120,
                why_selected="Batched persistence test",
            )
            decisions.append(sd)

    # Unit-of-work batch registration
    db_session.add(opt_run)
    db_session.add_all(blocks)
    db_session.add_all(block_tasks)
    db_session.add_all(decisions)

    # Flush Unit of Work
    db_session.flush()

    # Verify counts and referential integrity inside transaction
    persisted_run = db_session.query(OptimizationRun).filter_by(id=run_id).first()
    assert persisted_run is not None
    assert len(persisted_run.planned_blocks) == 3

    persisted_blocks = db_session.query(PlannedBlock).filter_by(optimization_run_id=run_id).all()
    assert len(persisted_blocks) == 3
    for b in persisted_blocks:
        assert b.optimization_run_id == run_id
        assert len(b.block_tasks) == 2
        assert len(b.schedule_decisions) == 2

    # Verify no orphan records
    for bt in block_tasks:
        assert db_session.query(BlockTask).filter_by(id=bt.id).first() is not None
    for sd in decisions:
        assert db_session.query(ScheduleDecision).filter_by(id=sd.id).first() is not None

    # Rollback transaction
    db_session.rollback()

    # Verify complete rollback leaves zero records
    assert db_session.query(OptimizationRun).filter_by(id=run_id).first() is None
    assert db_session.query(PlannedBlock).filter_by(optimization_run_id=run_id).count() == 0
