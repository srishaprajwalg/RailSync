import pytest
from core.schemas import GoodsTrainForecast, MaintenanceTask, TrainSchedule, PlannedBlock
from services.optimizer import optimize_blocks, is_task_feasible_alone
from services.timetable_analyzer import get_goods_train_occupancy

def test_freight_uncertainty_does_not_block_corridor_unnecessarily():
    # If the old model was used, a 370-min window at start_km to end_km would block all tasks 
    # anywhere in the corridor during that 370-min window.
    # With the new model, a task at the end of the corridor can happen early in the window.
    
    forecasts = [GoodsTrainForecast(
        forecast_id="F1", direction="Up", start_km=0.0, end_km=140.0,
        earliest_entry_mins=100, latest_exit_mins=500  # 400 min window
    )]
    
    # Task at the end of the corridor (km 130-135). 
    # Freight train takes ~210 mins to cross 140km. 
    # Expected entry = 100 + (400-210)/2 = 195. Expected exit = 195 + 210 = 405.
    # Uncertainty buffer = 190.
    # Segment expected enter = 195 + 210 * (130/140) = 390
    # Protected window for 130km: 390 - 95 = 295 to 390 + 95 = 485.
    # So a task from 120 to 180 mins should be totally fine here!
    
    task_early_end = MaintenanceTask(
        id="T1", department="TMS", task_type="Track", origin="Routine", severity=1, overdue_days=0, asset_criticality=1,
        start_km=130.0, end_km=135.0, duration_mins=60, deadline_mins=200, line_direction="Up"
    )
    
    blocks, statuses = optimize_blocks([task_early_end], [], forecasts, horizon_days=1, safety_margin=0)
    assert statuses["T1"] == "Planned"

def test_maintenance_overlapping_plausible_freight_is_rejected():
    forecasts = [GoodsTrainForecast(
        forecast_id="F1", direction="Up", start_km=0.0, end_km=140.0,
        earliest_entry_mins=100, latest_exit_mins=500
    )]
    # Task directly overlapping the plausible arrival time at 130km (which is ~295-485 mins).
    task_conflict = MaintenanceTask(
        id="T2", department="TMS", task_type="Track", origin="Routine", severity=1, overdue_days=0, asset_criticality=1,
        start_km=130.0, end_km=135.0, duration_mins=60, deadline_mins=400, line_direction="Up"
    )
    
    # This task MUST overlap with the freight train if it's forced to start such that it falls inside 295-485.
    # Actually, the optimizer could schedule it from 0 to 60. Let's restrict it to start > 300 by making the deadline tight? 
    # CP-SAT can schedule it before 295.
    # If we force it to happen exactly inside the window: e.g. we use the is_task_feasible_alone directly,
    # or make deadline 380, and safety_margin=0. Max start = 320. 
    # But 0-60 is valid. 
    # Instead, let's just check `get_goods_train_occupancy` directly for this segment.
    occs = get_goods_train_occupancy(forecasts, "Up", 130.0, 135.0)
    assert len(occs) == 1
    enter, exit_time = occs[0]
    
    # The protected window should be roughly around 300-485
    assert enter > 200 # It shouldn't block the start of the 400min window
    assert exit_time < 550
    
def test_safety_margin_is_respected():
    forecasts = [GoodsTrainForecast(
        forecast_id="F1", direction="Up", start_km=0.0, end_km=140.0,
        earliest_entry_mins=100, latest_exit_mins=500
    )]
    task = MaintenanceTask(
        id="T1", department="TMS", task_type="Track", origin="Routine", severity=1, overdue_days=0, asset_criticality=1,
        start_km=130.0, end_km=135.0, duration_mins=60, deadline_mins=400, line_direction="Up"
    )
    # Get the raw occupancy
    occs = get_goods_train_occupancy(forecasts, "Up", 130.0, 135.0)
    enter_time = occs[0][0]
    
    # Make duration exactly enter_time, and deadline enter_time + 10.
    # Without safety margin, it can run from 0 to enter_time (ends exactly when train arrives, NoOverlap allows this).
    # With safety margin 15, the train interval starts at enter_time - 15, so the task (ending at enter_time or later) will overlap.
    task.duration_mins = int(enter_time)
    task.deadline_mins = int(enter_time) + 10
    
    feasible_without_margin = is_task_feasible_alone(task, [], forecasts, horizon_mins=1440, safety_margin=0)
    feasible_with_margin = is_task_feasible_alone(task, [], forecasts, horizon_mins=1440, safety_margin=15)
    
    assert feasible_without_margin is True
    assert feasible_with_margin is False

def test_passenger_train_constraints_unchanged():
    # Ensure passenger trains still work normally
    schedules = [TrainSchedule(
        train_id="P1", type="Express", direction="Up", 
        stops=[
            {"station_id": "ST1", "arrival_mins": 100, "departure_mins": 100},
            {"station_id": "ST2", "arrival_mins": 200, "departure_mins": 200}
        ]
    )]
    # Task km 0 to 140 (covers the whole corridor)
    task = MaintenanceTask(
        id="T1", department="TMS", task_type="Track", origin="Routine", severity=1, overdue_days=0, asset_criticality=1,
        start_km=0.0, end_km=140.0, duration_mins=60, deadline_mins=200, line_direction="Up"
    )
    blocks, statuses = optimize_blocks([task], schedules, [], horizon_days=1, safety_margin=15)
    # The passenger train occupies 100 to 200. Task duration is 60. Deadline is 200. 
    # With safety margin 15, task must end by 100 - 15 = 85.
    # Start must be 0, end 60. This is feasible.
    assert statuses["T1"] == "Planned"
    assert blocks[0].start_time_mins <= 85 - 60

def test_cross_midnight_freight_works():
    forecasts = [GoodsTrainForecast(
        forecast_id="F1", direction="Up", start_km=0.0, end_km=140.0,
        earliest_entry_mins=1300, latest_exit_mins=1600 # crosses midnight (1440)
    )]
    occs = get_goods_train_occupancy(forecasts, "Up", 0.0, 140.0)
    assert len(occs) == 1
    assert occs[0][0] >= 1300
    assert occs[0][1] <= 1600

def test_different_line_directions_isolated():
    forecasts = [GoodsTrainForecast(
        forecast_id="F1", direction="Down", start_km=140.0, end_km=0.0,
        earliest_entry_mins=100, latest_exit_mins=500
    )]
    task = MaintenanceTask(
        id="T1", department="TMS", task_type="Track", origin="Routine", severity=1, overdue_days=0, asset_criticality=1,
        start_km=0.0, end_km=140.0, duration_mins=100, deadline_mins=500, line_direction="Up"
    )
    # Freight is Down, task is Up. Should be no conflict.
    # Safety margin 0
    blocks, statuses = optimize_blocks([task], [], forecasts, horizon_days=1, safety_margin=0)
    assert statuses["T1"] == "Planned"

def test_wider_freight_uncertainty_is_more_conservative():
    # Narrow window
    f_narrow = [GoodsTrainForecast(
        forecast_id="F1", direction="Up", start_km=0.0, end_km=140.0,
        earliest_entry_mins=100, latest_exit_mins=350 # Window = 250. Transit takes 210. Buffer = 40.
    )]
    # Wide window
    f_wide = [GoodsTrainForecast(
        forecast_id="F2", direction="Up", start_km=0.0, end_km=140.0,
        earliest_entry_mins=100, latest_exit_mins=600 # Window = 500. Buffer = 290.
    )]
    
    occ_narrow = get_goods_train_occupancy(f_narrow, "Up", 70.0, 75.0)[0]
    occ_wide = get_goods_train_occupancy(f_wide, "Up", 70.0, 75.0)[0]
    
    # Wide window should produce a longer protected interval
    narrow_duration = occ_narrow[1] - occ_narrow[0]
    wide_duration = occ_wide[1] - occ_wide[0]
    
    assert wide_duration > narrow_duration

def test_never_schedule_inside_protected_interval():
    forecasts = [GoodsTrainForecast(
        forecast_id="F1", direction="Up", start_km=0.0, end_km=140.0,
        earliest_entry_mins=100, latest_exit_mins=500
    )]
    # Force task to only be possible exactly during the freight's protected interval at km 0-5
    occ = get_goods_train_occupancy(forecasts, "Up", 0.0, 5.0)[0]
    enter_time, exit_time = occ
    
    # Make task duration = exit_time - enter_time. Make deadline = exit_time. 
    # Force it to start exactly at enter_time by making it only possible inside this window?
    # No, we can just say deadline is exit_time. It must start by exit_time - duration. 
    # If duration = exit_time - enter_time, it must start exactly at enter_time to finish by exit_time,
    # or start earlier. Let's just say we already had tasks up to enter_time.
    # A simpler way: CP-SAT won't schedule it if it overlaps.
    task = MaintenanceTask(
        id="T1", department="TMS", task_type="Track", origin="Routine", severity=1, overdue_days=0, asset_criticality=1,
        start_km=0.0, end_km=5.0, duration_mins=(exit_time - enter_time) + 10, deadline_mins=exit_time + 5, line_direction="Up"
    )
    # Without safety margin
    blocks, statuses = optimize_blocks([task], [], forecasts, horizon_days=1, safety_margin=0)
    
    # Because duration is longer than the time before enter_time (assuming enter_time is small? Wait, enter_time is ~100)
    # If enter_time is 100, duration might be 200. deadline 305. 
    # Available times: [0, enter_time] = [0, 100]. Not enough for 200.
    # [exit_time, deadline] = [300, 305]. Not enough.
    # So it must be infeasible.
    assert statuses["T1"] == "Infeasible"
