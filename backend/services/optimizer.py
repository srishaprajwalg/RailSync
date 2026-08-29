from ortools.sat.python import cp_model
from typing import List
from core.schemas import MaintenanceTask, PlannedBlock, TrainSchedule, GoodsTrainForecast
from services.timetable_analyzer import get_passenger_train_occupancy, get_goods_train_occupancy
from services.compatibility import are_tasks_compatible
import uuid

def is_task_feasible_alone(
    task: MaintenanceTask,
    schedules: List[TrainSchedule],
    forecasts: List[GoodsTrainForecast],
    horizon_mins: int,
    safety_margin: int
) -> bool:
    """Checks if a single task is geometrically and physically feasible within its deadline."""
    effective_deadline = min(task.deadline_mins, horizon_mins)
    if effective_deadline < task.duration_mins:
        return False
        
    model = cp_model.CpModel()
    start = model.NewIntVar(0, effective_deadline - task.duration_mins, 'start')
    end = model.NewIntVar(task.duration_mins, effective_deadline, 'end')
    interval = model.NewIntervalVar(start, task.duration_mins, end, 'interval')
    
    p_occs = get_passenger_train_occupancy(schedules, task.line_direction, task.start_km, task.end_km)
    for (enter, exit_time) in p_occs:
        safe_start = max(0, enter - safety_margin)
        safe_end = exit_time + safety_margin
        t_int = model.NewIntervalVar(safe_start, safe_end - safe_start, safe_end, 'train')
        model.AddNoOverlap([interval, t_int])
        
    g_occs = get_goods_train_occupancy(forecasts, task.line_direction, task.start_km, task.end_km)
    for (enter, exit_time) in g_occs:
        safe_start = max(0, enter - safety_margin)
        safe_end = exit_time + safety_margin
        t_int = model.NewIntervalVar(safe_start, safe_end - safe_start, safe_end, 'goods')
        model.AddNoOverlap([interval, t_int])
        
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    return status in [cp_model.OPTIMAL, cp_model.FEASIBLE]

def optimize_blocks(
    tasks: List[MaintenanceTask], 
    schedules: List[TrainSchedule], 
    forecasts: List[GoodsTrainForecast] = None,
    horizon_days: int = 7,
    safety_margin: int = 15
) -> tuple[List[PlannedBlock], dict]:
    """
    Core Optimization Engine using Google OR-Tools CP-SAT.
    """
    if forecasts is None:
        forecasts = []
        
    planned_blocks = []
    task_status_map = {}
    
    # We will plan per line direction separately
    for direction in ["Up", "Down"]:
        dir_tasks = [t for t in tasks if t.line_direction == direction]
        if not dir_tasks:
            continue
            
        model = cp_model.CpModel()
            
        # 1. Create variables for each task
        task_starts = {}
        task_ends = {}
        task_intervals = {}
        task_is_scheduled = {}
        
        # Max horizon is bounded by the selected horizon_days
        horizon_mins = horizon_days * 1440
        
        for task in dir_tasks:
            task_is_scheduled[task.id] = model.NewBoolVar(f'scheduled_{task.id}')
            
            # Start can be anywhere from 0 to absolute deadline or horizon, whichever is earlier
            effective_deadline = min(task.deadline_mins, horizon_mins)
            
            if effective_deadline < task.duration_mins:
                # Task cannot possibly fit in the available time
                model.Add(task_is_scheduled[task.id] == 0)
                # Still need to create dummy variables to avoid KeyError later
                task_starts[task.id] = model.NewIntVar(0, 0, f'start_{task.id}')
                task_ends[task.id] = model.NewIntVar(0, 0, f'end_{task.id}')
                task_intervals[task.id] = model.NewOptionalIntervalVar(
                    task_starts[task.id], task.duration_mins, task_ends[task.id], 
                    task_is_scheduled[task.id], f'interval_{task.id}'
                )
                continue

            task_starts[task.id] = model.NewIntVar(0, effective_deadline - task.duration_mins, f'start_{task.id}')
            task_ends[task.id] = model.NewIntVar(task.duration_mins, effective_deadline, f'end_{task.id}')
            
            task_intervals[task.id] = model.NewOptionalIntervalVar(
                task_starts[task.id], 
                task.duration_mins, 
                task_ends[task.id], 
                task_is_scheduled[task.id], 
                f'interval_{task.id}'
            )

        # 2. Timetable safety constraints (No overlap with specific train movements)
        # Instead of global white spaces, we create interval variables for every train 
        # crossing the specific chainage segment of the task, and force NoOverlap.
        
        train_conflict_intervals = {}
        
        for task in dir_tasks:
            train_conflict_intervals[task.id] = []
            
            # Passenger Trains
            p_occupancies = get_passenger_train_occupancy(schedules, direction, task.start_km, task.end_km)
            # Goods Trains
            g_occupancies = get_goods_train_occupancy(forecasts, direction, task.start_km, task.end_km)
            
            all_occupancies = p_occupancies + g_occupancies
            
            for i, (enter_time, exit_time) in enumerate(all_occupancies):
                # Apply safety margin around the train occupancy
                safe_start = max(0, enter_time - safety_margin)
                safe_end = exit_time + safety_margin
                duration = safe_end - safe_start
                if duration <= 0:
                    continue
                    
                # Create a fixed interval representing the train
                # Since it's fixed, we can just use NewIntervalVar with constant values
                train_interval = model.NewIntervalVar(
                    safe_start, duration, safe_end, f'train_{task.id}_occ_{i}'
                )
                
                # The task interval cannot overlap with this train interval
                model.AddNoOverlap([task_intervals[task.id], train_interval])

        # 3. Task compatibility constraint (No overlap if incompatible and physically overlapping)
        for i in range(len(dir_tasks)):
            for j in range(i + 1, len(dir_tasks)):
                t1 = dir_tasks[i]
                t2 = dir_tasks[j]
                
                # Check spatial overlap
                spatial_overlap = not (t1.end_km < t2.start_km or t2.end_km < t1.start_km)
                
                if spatial_overlap:
                    if not are_tasks_compatible(t1, t2):
                        # They cannot overlap in time
                        model.AddNoOverlap([task_intervals[t1.id], task_intervals[t2.id]])

        # 4. Objective function: Lexicographic Hierarchy
        # 1. Complete as many feasible/required tasks as possible (W_SCHEDULE = 1 Billion)
        # 2. Prioritize high-urgency/high-priority tasks (W_PRIORITY = 1 Million)
        # 3. Minimize start times to encourage early execution and natural consolidation (W_EARLY = 10)
        
        W_SCHEDULE = 1_000_000_000
        W_PRIORITY = 1_000_000
        W_EARLY = 10
        
        objective_terms = []
        for task in dir_tasks:
            score = task.priority_details.score if hasattr(task, 'priority_details') and task.priority_details else 10
            
            reward_schedule = task_is_scheduled[task.id] * W_SCHEDULE
            reward_priority = task_is_scheduled[task.id] * (score * W_PRIORITY)
            penalty_early = task_starts[task.id] * W_EARLY
            
            objective_terms.append(reward_schedule + reward_priority - penalty_early)
            
        model.Maximize(sum(objective_terms))

        # Solve
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 10.0 # Time limit for CP
        status = solver.Solve(model)
        
        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            # Extract the actual scheduled tasks
            scheduled_intervals = []
            for task in dir_tasks:
                if solver.Value(task_is_scheduled[task.id]):
                    s = solver.Value(task_starts[task.id])
                    e = solver.Value(task_ends[task.id])
                    scheduled_intervals.append((s, e, task))
            
            # Simple grouping heuristic to create blocks from overlapping tasks
            scheduled_intervals.sort(key=lambda x: x[0])
            
            if scheduled_intervals:
                current_block = [scheduled_intervals[0]]
                for interval in scheduled_intervals[1:]:
                    prev = current_block[-1]
                    # If time overlaps, add to block
                    if interval[0] <= prev[1]:
                        current_block.append(interval)
                    else:
                        # Output current block
                        planned_blocks.append(create_block_from_group(current_block, direction))
                        current_block = [interval]
                        
                planned_blocks.append(create_block_from_group(current_block, direction))

        # Identify deferred vs infeasible tasks using the standalone feasibility check
        for task in dir_tasks:
            if not solver.Value(task_is_scheduled[task.id]):
                # Test if the task was genuinely impossible on its own
                if not is_task_feasible_alone(task, schedules, forecasts, horizon_mins, safety_margin):
                    task_status_map[task.id] = "Infeasible"
                else:
                    # It was feasible, but the optimizer didn't pick it (due to conflicts or capacity limits)
                    task_status_map[task.id] = "Deferred"
            else:
                task_status_map[task.id] = "Planned"

    return planned_blocks, task_status_map

def create_block_from_group(group, direction):
    # A block's protected time window covers all consolidated tasks
    start_time = min(g[0] for g in group)
    end_time = max(g[1] for g in group)
    
    # A block's physical extent is the union of all task chainages inside it
    start_km = min(g[2].start_km for g in group)
    end_km = max(g[2].end_km for g in group)
    tasks = [g[2].id for g in group]
    
    return PlannedBlock(
        id=str(uuid.uuid4())[:8],
        start_time_mins=start_time,
        end_time_mins=end_time,
        start_km=start_km,
        end_km=end_km,
        line_direction=direction,
        assigned_tasks=tasks
    )
