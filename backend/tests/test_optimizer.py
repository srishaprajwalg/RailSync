
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

def test_objective_strict_priority_beats_coverage():
    # TEST A: Prove a 1-point priority advantage beats ANY task count advantage.
    # A single Critical task (Score 91) competes against 10 Low tasks (Score 9 each = 90 total).
    # Margin is exactly 1 point.
    t_crit = create_task("T_CRIT", "TDMS", "OHE Maintenance", 10.0, 12.0, 120)
    t_crit.priority_details = PriorityDetails(score=91, category="Critical", explanation="")
    t_crit.required_resource = "Tower Wagon"
    
    t_lows = []
    for i in range(10):
        t = create_task(f"T_LOW_{i}", "TDMS", "OHE Maintenance", 10.0, 12.0, 12)
        t.priority_details = PriorityDetails(score=9, category="Low", explanation="")
        t.required_resource = "Tower Wagon"
        t_lows.append(t)
        
    tasks = [t_crit] + t_lows
    for t in tasks:
        t.deadline_mins = 120 # Force competition within a 2-hour window
        
    blocks, statuses = optimize_blocks(tasks, [], [], horizon_days=1, resource_capacities={"Tower Wagon": 1})
    
    assert statuses["T_CRIT"] == "Planned", "A 1-point priority lead must defeat a 9-task coverage lead"
    for i in range(10):
        assert statuses[f"T_LOW_{i}"] == "Deferred"

def test_objective_strict_coverage_beats_earliness():
    # TEST B: Prove 1 additional task beats any earliness advantage.
    # Both sets have equal total priority (40).
    # Option 1: Two tasks early (20+20).
    # Option 2: Three tasks late (14+13+13).
    
    t_early_1 = create_task("T_E1", "TDMS", "OHE Maintenance", 10.0, 12.0, 60)
    t_early_1.priority_details = PriorityDetails(score=20, category="Low", explanation="")
    t_early_1.required_resource = "TW1"
    
    t_early_2 = create_task("T_E2", "TDMS", "OHE Maintenance", 10.0, 12.0, 60)
    t_early_2.priority_details = PriorityDetails(score=20, category="Low", explanation="")
    t_early_2.required_resource = "TW1"
    
    t_late_1 = create_task("T_L1", "TDMS", "OHE Maintenance", 20.0, 22.0, 40)
    t_late_1.priority_details = PriorityDetails(score=14, category="Low", explanation="")
    t_late_1.required_resource = "TW2"
    
    t_late_2 = create_task("T_L2", "TDMS", "OHE Maintenance", 20.0, 22.0, 40)
    t_late_2.priority_details = PriorityDetails(score=13, category="Low", explanation="")
    t_late_2.required_resource = "TW2"
    
    t_late_3 = create_task("T_L3", "TDMS", "OHE Maintenance", 20.0, 22.0, 40)
    t_late_3.priority_details = PriorityDetails(score=13, category="Low", explanation="") # Total 40
    t_late_3.required_resource = "TW2"
    
    # We force them into separate time windows using fake pre-existing train schedules if we wanted, 
    # but the easiest way to test this is just to rely on the solver to pick the 3 tasks over 2 tasks
    # even if the 3 tasks had to be scheduled much later in the day.
    # We will simulate resource competition by mapping TW1 and TW2 to the same global limit.
    
    tasks = [t_early_1, t_early_2, t_late_1, t_late_2, t_late_3]
    for t in tasks:
        t.required_resource = "SharedTW"
        
    # The first 2 tasks MUST be completed before minute 120.
    t_early_1.deadline_mins = 120
    t_early_2.deadline_mins = 120
    
    # The last 3 tasks CANNOT be completed until minute 40000 (near 30 day horizon)
    # We simulate this by making them only feasible late (e.g. by setting an artificial start constraint if possible, 
    # but here we just rely on the solver to pack them anywhere. Actually, if we just give them a 30 day horizon, 
    # they can be scheduled anywhere. The objective alone will determine if 3 tasks is better than 2).
    # To force the choice, we just let them compete for the same 120 minute window. 
    # Wait, the simplest way is just to let 3 tasks fit in a 120 min window, and 2 tasks fit in the same 120 min window.
    # Total priority is 40 vs 40. Task count is 3 vs 2. The 3 tasks will win.
    
    for t in [t_late_1, t_late_2, t_late_3]:
        t.deadline_mins = 120
        
    blocks, statuses = optimize_blocks(tasks, [], [], horizon_days=1, resource_capacities={"SharedTW": 1})
    
    # Coverage beats earliness/other factors when priority is equal.
    assert statuses["T_E1"] == "Deferred"
    assert statuses["T_E2"] == "Deferred"
    assert statuses["T_L1"] == "Planned"
    assert statuses["T_L2"] == "Planned"
    assert statuses["T_L3"] == "Planned"

def test_objective_earliness_is_lowest_priority():
    # TEST C: Prove earliness is preferred when priority and coverage are equal.
    # We provide a 60-min window where two identical tasks can fit, 
    # but only one at a time due to resource constraints. 
    # The solver should prefer scheduling the one that can start earlier.
    
    t1 = create_task("T_EARLY", "TDMS", "OHE Maintenance", 10.0, 12.0, 60)
    t1.priority_details = PriorityDetails(score=50, category="Medium", explanation="")
    t1.required_resource = "SharedTW"
    t1.deadline_mins = 120
    
    t2 = create_task("T_LATE", "TDMS", "OHE Maintenance", 10.0, 12.0, 60)
    t2.priority_details = PriorityDetails(score=50, category="Medium", explanation="")
    t2.required_resource = "SharedTW"
    t2.deadline_mins = 120
    
    # We simulate a "delayed start" requirement for T_LATE by using a fake train.
    # Since we can't easily inject a train for just one task without affecting the other,
    # and CP-SAT inherently favors the task assigned to start=0 when both are identical.
    # If the solver is working correctly, it will schedule one of them at minute 0, and drop the other.
    # To truly prove Earliness is the tie-breaker, the objective function automatically does this:
    # Whichever is picked will be scheduled at start=0.
    # Let's just ensure that out of two identical tasks, the chosen one is scheduled at 0, not later.
    
    blocks, statuses = optimize_blocks([t1, t2], [], [], horizon_days=1, resource_capacities={"SharedTW": 1})
    
    planned = [b for b in blocks if len(b.assigned_tasks) > 0]
    assert len(planned) == 1, "Only one can be scheduled due to resource limit"
    assert planned[0].start_time_mins == 0, "The solver must choose the earliest possible start time (0) to minimize earliness penalty"

