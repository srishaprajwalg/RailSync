"""
test_corridor_isolation.py — Multi-corridor isolation test suite.
Validates:
- Test A: Maintenance Isolation (requests, assets, sections)
- Test B: Timetable Isolation (trains, runs, stops per corridor)
- Test C: Optimizer Isolation (independent CP-SAT scheduling with corridor train occupancy)
- Test D: Block Isolation (planned blocks strictly within corridor chainage boundaries)
- Test E: Chainage Isolation (monotonically increasing chainages matching target lengths)
- Test F: Location Query Isolation (geospatial/radius queries partitioned by corridor)
"""

import pytest
from sqlalchemy.orm import Session

from backend.db.models import (
    Corridor,
    Section,
    Station as StationModel,
    Asset,
    TrainRun,
    TrainMovement,
    MaintenanceRequest,
    FreightForecast,
    OptimizationRun,
    PlannedBlock as PlannedBlockModel,
)
from backend.services.seeder import seed_corridor, seed_all_corridors
from backend.services.real_corridor import (
    get_corridor_stations,
    get_real_timetables,
    CORRIDOR_CONFIGS,
)
from backend.services.timetable_analyzer import (
    get_station_chainage,
    get_passenger_train_occupancy,
)
from backend.services.optimizer import optimize_blocks
from backend.core.schemas import MaintenanceTask, OptimizeRequest
from backend.main import (
    get_corridor_stations as api_get_corridor_stations,
    get_timetables as api_get_timetables,
    get_goods_forecasts as api_get_goods_forecasts,
    get_tasks as api_get_tasks,
    get_assets as api_get_assets,
    get_blocks as api_get_blocks,
    location_query as api_location_query,
)

@pytest.fixture(scope="function")
def multi_corridor_db(db_session: Session):
    """Seed all three corridors into the isolated test database."""
    seed_all_corridors(db_session, force_clean=False)
    return db_session

# ===========================================================================
# Test E: Chainage and Station Geometry Isolation
# ===========================================================================

def test_chainage_and_geometry_isolation(multi_corridor_db: Session):
    """Verifies that each corridor has correct monotonic station chainages matching ground truth lengths."""
    for corridor_id, cfg in CORRIDOR_CONFIGS.items():
        stations = get_corridor_stations(corridor_id)
        codes = [s.code for s in stations]
        chainages = [s.chainage_km for s in stations]

        # Expected codes
        assert codes == cfg["codes"], f"Station codes mismatch for {corridor_id}"
        
        # Origin is 0.0 km
        assert chainages[0] == 0.0, f"Origin station {codes[0]} must be at 0.0 km"
        
        # Terminal matches target length
        assert chainages[-1] == cfg["total_km"], f"Terminal station {codes[-1]} must match {cfg['total_km']} km"
        
        # Strictly monotonic
        for i in range(len(chainages) - 1):
            assert chainages[i] < chainages[i + 1], f"Chainage not strictly increasing on {corridor_id}"

    # Verify global lookup in timetable analyzer returns expected chainages
    assert get_station_chainage("SBC") == 0.0
    assert get_station_chainage("JTJ") == 145.0
    assert get_station_chainage("NDLS") == 0.0
    assert get_station_chainage("CNB") == 440.0
    assert get_station_chainage("CSTM") == 0.0
    assert get_station_chainage("PUNE") == 192.0

# ===========================================================================
# Test A: Maintenance and Asset Isolation
# ===========================================================================

def test_maintenance_and_asset_isolation(multi_corridor_db: Session):
    """Verifies that assets and maintenance requests are strictly partitioned by corridor."""
    for corridor_id in ["SBC-JTJ", "NDLS-CNB", "CSTM-PUNE"]:
        corridor = multi_corridor_db.query(Corridor).filter_by(id=corridor_id).first()
        assert corridor is not None

        # Verify sections belong strictly to this corridor
        sections = multi_corridor_db.query(Section).filter_by(corridor_id=corridor_id).all()
        assert len(sections) >= 4
        for sec in sections:
            assert sec.corridor_id == corridor_id
            assert sec.start_chainage >= 0.0
            assert sec.end_chainage <= corridor.total_length_km

        # Verify assets belong strictly to this corridor
        assets = multi_corridor_db.query(Asset).filter_by(corridor_id=corridor_id).all()
        assert len(assets) >= 15
        for a in assets:
            assert a.corridor_id == corridor_id
            assert a.start_chainage >= 0.0
            assert a.end_chainage <= corridor.total_length_km

        # Verify maintenance requests
        requests = multi_corridor_db.query(MaintenanceRequest).filter_by(corridor_id=corridor_id).all()
        assert len(requests) == 420
        for r in requests:
            assert r.corridor_id == corridor_id
            assert r.start_chainage >= 0.0
            assert r.end_chainage <= corridor.total_length_km

    # Verify API query returns isolated results
    sbc_tasks = api_get_tasks(corridor_id="SBC-JTJ", db=multi_corridor_db)
    ndls_tasks = api_get_tasks(corridor_id="NDLS-CNB", db=multi_corridor_db)
    cstm_tasks = api_get_tasks(corridor_id="CSTM-PUNE", db=multi_corridor_db)

    assert len(sbc_tasks) == 420
    assert len(ndls_tasks) == 420
    assert len(cstm_tasks) == 420

    # Ensure no task ID overlap
    sbc_ids = {t.id for t in sbc_tasks}
    ndls_ids = {t.id for t in ndls_tasks}
    cstm_ids = {t.id for t in cstm_tasks}

    assert sbc_ids.isdisjoint(ndls_ids)
    assert sbc_ids.isdisjoint(cstm_ids)
    assert ndls_ids.isdisjoint(cstm_ids)

# ===========================================================================
# Test B: Timetable Isolation
# ===========================================================================

def test_timetable_isolation(multi_corridor_db: Session):
    """Verifies that train schedules and movements are isolated to their corridors."""
    sbc_schedules = api_get_timetables(corridor_id="SBC-JTJ", db=multi_corridor_db)
    ndls_schedules = api_get_timetables(corridor_id="NDLS-CNB", db=multi_corridor_db)
    cstm_schedules = api_get_timetables(corridor_id="CSTM-PUNE", db=multi_corridor_db)

    assert len(sbc_schedules) > 0
    assert len(ndls_schedules) > 0
    assert len(cstm_schedules) > 0

    sbc_stations = set(CORRIDOR_CONFIGS["SBC-JTJ"]["codes"])
    ndls_stations = set(CORRIDOR_CONFIGS["NDLS-CNB"]["codes"])
    cstm_stations = set(CORRIDOR_CONFIGS["CSTM-PUNE"]["codes"])

    # SBC schedules must only touch SBC corridor stations
    for s in sbc_schedules:
        for stop in s.stops:
            assert stop.station_id in sbc_stations, f"Foreign station {stop.station_id} in SBC-JTJ timetable"

    # NDLS schedules must only touch NDLS corridor stations
    for s in ndls_schedules:
        for stop in s.stops:
            assert stop.station_id in ndls_stations, f"Foreign station {stop.station_id} in NDLS-CNB timetable"

    # CSTM schedules must only touch CSTM corridor stations
    for s in cstm_schedules:
        for stop in s.stops:
            assert stop.station_id in cstm_stations, f"Foreign station {stop.station_id} in CSTM-PUNE timetable"

# ===========================================================================
# Test C & D: Optimizer & Block Isolation
# ===========================================================================

def test_optimizer_and_block_isolation(multi_corridor_db: Session):
    """
    Verifies that CP-SAT can optimize a subset of tasks for NDLS-CNB independently,
    using only NDLS-CNB timetables and producing blocks within 0-440 km.
    """
    ndls_tasks_raw = api_get_tasks(corridor_id="NDLS-CNB", db=multi_corridor_db)[:15]
    ndls_timetables = api_get_timetables(corridor_id="NDLS-CNB", db=multi_corridor_db)
    ndls_forecasts = api_get_goods_forecasts(corridor_id="NDLS-CNB", db=multi_corridor_db)

    blocks, status_map = optimize_blocks(
        ndls_tasks_raw,
        ndls_timetables,
        ndls_forecasts,
        horizon_days=7,
        safety_margin=15,
    )

    assert len(status_map) == len(ndls_tasks_raw)
    for b in blocks:
        # Blocks must be strictly within NDLS-CNB chainage (0.0 to 440.0 km)
        assert 0.0 <= b.start_km <= 440.0
        assert 0.0 <= b.end_km <= 440.0
        assert b.end_km >= b.start_km
        # Block span must not exceed maximum 20.0 km
        assert (b.end_km - b.start_km) <= 20.001

# ===========================================================================
# Test F: Location Query Isolation
# ===========================================================================

def test_location_query_isolation(multi_corridor_db: Session):
    """
    Verifies that location queries for KM 20.0 ± 5km return assets and trains
    specific only to the queried corridor.
    """
    res_sbc = api_location_query(chainage=20.0, radius_km=5.0, corridor_id="SBC-JTJ", db=multi_corridor_db)
    res_ndls = api_location_query(chainage=20.0, radius_km=5.0, corridor_id="NDLS-CNB", db=multi_corridor_db)

    assert res_sbc.corridor_id == "SBC-JTJ"
    assert res_ndls.corridor_id == "NDLS-CNB"

    # SBC assets must have corridor_id="SBC-JTJ"
    for a in res_sbc.assets_in_range:
        assert a.corridor_id == "SBC-JTJ"

    # NDLS assets must have corridor_id="NDLS-CNB"
    for a in res_ndls.assets_in_range:
        assert a.corridor_id == "NDLS-CNB"
