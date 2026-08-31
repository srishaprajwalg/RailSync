
from core.schemas import MaintenanceTask, PriorityDetails
from services.optimizer import optimize_blocks, group_tasks_into_blocks

def create_task(id, department, task_type, start_km, end_km, duration, direction="Up", deadline=1440):
    return MaintenanceTask(
        id=id,
        department=department,
        task_type=task_type,
        origin="Routine Maintenance",
        severity=1,
        overdue_days=0,
        asset_criticality=3,
        start_km=start_km,
        end_km=end_km,
        duration_mins=duration,
        deadline_mins=deadline,
        line_direction=direction,
        priority_details=PriorityDetails(score=50, category="Medium", explanation="Test")
    )

def test_grouping_same_time_same_area_diff_direction():
    # TEST 1: Same time + same spatial area + Up/Down -> MUST produce separate PlannedBlocks.
    task1 = create_task("T1", "TMS", "Track Tamping", 10.0, 12.0, 60, direction="Up")
    task2 = create_task("T2", "TMS", "Track Tamping", 10.0, 12.0, 60, direction="Down")
    
    # Manually grouping them simulating they were handed to the grouper at the same time
    # Though optimize_blocks inherently isolates them, this tests the grouper's resilience.
    scheduled_intervals = [
        (0, 60, task1),
        (0, 60, task2)
    ]
    
    blocks = group_tasks_into_blocks(scheduled_intervals, "Mixed")
    assert len(blocks) == 2, "Different line directions MUST produce separate PlannedBlocks even if time and space overlap."
    
def test_grouping_same_time_same_area_up_up():
    # TEST 2: Same time + same spatial area + Up/Up -> MAY produce one PlannedBlock.
    task1 = create_task("T1", "TMS", "Track Tamping", 10.0, 12.0, 60, direction="Up")
    task2 = create_task("T2", "S&T", "Signal Failure", 10.0, 12.0, 60, direction="Up")
    
    scheduled_intervals = [
        (0, 60, task1),
        (0, 60, task2)
    ]
    
    blocks = group_tasks_into_blocks(scheduled_intervals, "Up")
    assert len(blocks) == 1, "Up/Up tasks overlapping in time and space should produce ONE PlannedBlock."
    assert set(blocks[0].assigned_tasks) == {"T1", "T2"}
    
def test_grouping_same_time_same_area_down_down():
    # TEST 3: Same time + same spatial area + Down/Down -> MAY produce one PlannedBlock.
    task1 = create_task("T1", "TMS", "Track Tamping", 10.0, 12.0, 60, direction="Down")
    task2 = create_task("T2", "S&T", "Signal Failure", 10.0, 12.0, 60, direction="Down")
    
    scheduled_intervals = [
        (0, 60, task1),
        (0, 60, task2)
    ]
    
    blocks = group_tasks_into_blocks(scheduled_intervals, "Down")
    assert len(blocks) == 1, "Down/Down tasks overlapping in time and space should produce ONE PlannedBlock."

def test_grouping_same_time_distant_areas():
    # TEST 4: Same time + distant spatial areas -> MUST produce separate PlannedBlocks.
    task1 = create_task("T1", "TMS", "Track Tamping", 10.0, 12.0, 60, direction="Up")
    task2 = create_task("T2", "TDMS", "OHE Maintenance", 130.0, 132.0, 60, direction="Up")
    
    scheduled_intervals = [
        (0, 60, task1),
        (0, 60, task2)
    ]
    
    blocks = group_tasks_into_blocks(scheduled_intervals, "Up")
    assert len(blocks) == 2, "Distant tasks MUST produce separate PlannedBlocks."
    
def test_grouping_spatially_continuous_compatible_tasks():
    # TEST 5: Spatially continuous compatible tasks -> MAY produce one PlannedBlock with correct min/max extent.
    task1 = create_task("T1", "TMS", "Track Tamping", 10.0, 12.0, 60, direction="Up")
    task2 = create_task("T2", "S&T", "Signal Failure", 12.0, 15.0, 60, direction="Up")
    
    scheduled_intervals = [
        (0, 60, task1),
        (0, 60, task2)
    ]
    
    blocks = group_tasks_into_blocks(scheduled_intervals, "Up")
    assert len(blocks) == 1
    assert blocks[0].start_km == 10.0
    assert blocks[0].end_km == 15.0

def test_existing_valid_block_behavior_deadline():
    # TEST 6: Existing optimizer safety/deadline behavior -> MUST remain unchanged.
    task1 = create_task("T1", "TMS", "Track Tamping", 10.0, 12.0, 120, deadline=60)
    
    blocks, statuses = optimize_blocks([task1], [], [], horizon_days=1)
    
    assert statuses["T1"] == "Infeasible"
    assert len(blocks) == 0

def test_completed_tasks_are_excluded():
    task1 = create_task("T1", "TMS", "Track Tamping", 10.0, 12.0, 120)
    task1.lifecycle_status = "Completed"
    
    blocks, statuses = optimize_blocks([task1], [], [], horizon_days=1)
    
    assert "T1" not in statuses  # Should not even be in the status map
    assert len(blocks) == 0

def test_non_completed_task_remains_eligible():
    task1 = create_task("T1", "TMS", "Track Tamping", 10.0, 12.0, 120)
    task1.lifecycle_status = "Prioritized"
    
    blocks, statuses = optimize_blocks([task1], [], [], horizon_days=1)
    
    assert statuses["T1"] == "Planned"
    assert len(blocks) == 1
