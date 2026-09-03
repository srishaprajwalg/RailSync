import uuid
import time
import logging
from ortools.sat.python import cp_model
from typing import List
from backend.core.schemas import MaintenanceTask, PlannedBlock, TrainSchedule, GoodsTrainForecast
from backend.services.timetable_analyzer import get_passenger_train_occupancy, get_goods_train_occupancy
from backend.services.compatibility import are_tasks_compatible

logger = logging.getLogger("railvyuha.optimizer")

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
    safety_margin: int = 15,
    resource_capacities: dict = None
) -> tuple[List[PlannedBlock], dict]:
    """
    Core Optimization Engine using Google OR-Tools CP-SAT.
    """
    t_opt_start = time.time()
    if forecasts is None:
        forecasts = []
    if resource_capacities is None:
        resource_capacities = {}
        
    planned_blocks = []
    task_status_map = {}
    
    # 0. Filter out completed tasks from active planning
    active_tasks = [t for t in tasks if getattr(t, 'lifecycle_status', '') != "Completed"]
    if not active_tasks:
        return planned_blocks, task_status_map
        
    model = cp_model.CpModel()
    
    # 1. Create variables for each task
    task_starts = {}
    task_ends = {}
    task_intervals = {}
    task_is_scheduled = {}
    
    # Max horizon is bounded by the selected horizon_days
    horizon_mins = horizon_days * 1440
    
    for task in active_tasks:
        task_is_scheduled[task.id] = model.NewBoolVar(f'scheduled_{task.id}')
        effective_deadline = min(task.deadline_mins, horizon_mins)
        
        if effective_deadline < task.duration_mins:
            # Task cannot possibly fit in the available time
            model.Add(task_is_scheduled[task.id] == 0)
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
            task_starts[task.id], task.duration_mins, task_ends[task.id], 
            task_is_scheduled[task.id], f'interval_{task.id}'
        )
        
    # 2. Timetable safety & 3. Compatibility constraints (Directionally isolated)
    for direction in ["Up", "Down"]:
        dir_tasks = [t for t in active_tasks if t.line_direction == direction]
        
        for task in dir_tasks:
            # Train Conflict Intervals
            p_occupancies = get_passenger_train_occupancy(schedules, direction, task.start_km, task.end_km)
            g_occupancies = get_goods_train_occupancy(forecasts, direction, task.start_km, task.end_km)
            all_occupancies = p_occupancies + g_occupancies
            
            for i, (enter_time, exit_time) in enumerate(all_occupancies):
                safe_start = max(0, enter_time - safety_margin)
                safe_end = exit_time + safety_margin
                duration = safe_end - safe_start
                if duration <= 0:
                    continue
                train_interval = model.NewIntervalVar(
                    safe_start, duration, safe_end, f'train_{task.id}_occ_{i}'
                )
                model.AddNoOverlap([task_intervals[task.id], train_interval])
                
        # Task compatibility constraints
        for i in range(len(dir_tasks)):
            for j in range(i + 1, len(dir_tasks)):
                t1 = dir_tasks[i]
                t2 = dir_tasks[j]
                spatial_overlap = not (t1.end_km < t2.start_km or t2.end_km < t1.start_km)
                if spatial_overlap and not are_tasks_compatible(t1, t2):
                    model.AddNoOverlap([task_intervals[t1.id], task_intervals[t2.id]])
                    
    # 4. Resource Constraints (Cross-Direction)
    for resource, capacity in resource_capacities.items():
        res_tasks = [t for t in active_tasks if getattr(t, 'required_resource', None) == resource]
        if not res_tasks:
            continue
            
        res_intervals = [task_intervals[t.id] for t in res_tasks]
        if capacity == 1:
            model.AddNoOverlap(res_intervals)
        else:
            demands = [1 for _ in res_tasks]
            model.AddCumulative(res_intervals, demands, capacity)

    # 5. Objective function: Strict global hierarchy (Priority > Coverage > Earliness)
    # Conservative verified bound for current prototype: N_MAX <= 1,000 tasks, MAX_START <= 43,200 (30 days)
    W_PRIORITY = 1_000_000_000_000  # 1 Trillion
    W_BASE = 100_000_000            # 100 Million
    W_EARLY = 1                     # 1
    
    objective_terms = []
    for task in active_tasks:
        score = task.priority_details.score if hasattr(task, 'priority_details') and task.priority_details else 10
        reward_schedule = task_is_scheduled[task.id] * W_BASE
        reward_priority = task_is_scheduled[task.id] * (score * W_PRIORITY)
        penalty_early = task_starts[task.id] * W_EARLY
        objective_terms.append(reward_schedule + reward_priority - penalty_early)
        
    model.Maximize(sum(objective_terms))

    t_model_ms = int((time.time() - t_opt_start) * 1000)

    # Solve
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10.0 # Time limit for CP
    t_solve_start = time.time()
    status = solver.Solve(model)
    t_solve_ms = int((time.time() - t_solve_start) * 1000)
    
    t_group_start = time.time()
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        # Build blocks per direction so they don't combine Up and Down tasks
        for direction in ["Up", "Down"]:
            dir_tasks = [t for t in active_tasks if t.line_direction == direction]
            scheduled_intervals = []
            for task in dir_tasks:
                if solver.Value(task_is_scheduled[task.id]):
                    s = solver.Value(task_starts[task.id])
                    e = solver.Value(task_ends[task.id])
                    scheduled_intervals.append((s, e, task))
            planned_blocks.extend(group_tasks_into_blocks(scheduled_intervals, direction, schedules, forecasts, safety_margin))
    t_group_ms = int((time.time() - t_group_start) * 1000)

    # Identify deferred vs infeasible tasks
    t_infeas_start = time.time()
    for task in active_tasks:
        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE) and solver.Value(task_is_scheduled[task.id]):
            task_status_map[task.id] = "Planned"
        else:
            # Test if the task was genuinely impossible on its own due to constraints
            if not is_task_feasible_alone(task, schedules, forecasts, horizon_mins, safety_margin):
                task_status_map[task.id] = "Infeasible"
            else:
                # Feasible, but optimizer deferred it due to conflicts/resources
                task_status_map[task.id] = "Deferred"
    t_infeas_ms = int((time.time() - t_infeas_start) * 1000)

    logger.info(
        "optimize_blocks: Model build: %dms | CP-SAT solve: %dms | Grouping: %dms | Feasibility: %dms",
        t_model_ms, t_solve_ms, t_group_ms, t_infeas_ms
    )

    return planned_blocks, task_status_map

def is_block_envelope_safe(
    schedules: List[TrainSchedule] = None,
    forecasts: List[GoodsTrainForecast] = None,
    direction: str = "Up",
    start_km: float = 0.0,
    end_km: float = 0.0,
    start_time: int = 0,
    end_time: int = 0,
    safety_margin: int = 15,
) -> bool:
    """
    Verifies that the consolidated block envelope [start_km, end_km] during [start_time, end_time]
    does not intersect any passenger or freight train occupancies (with safety_margin).
    """
    if not schedules and not forecasts:
        return True

    min_k = min(start_km, end_km)
    max_k = max(start_km, end_km)

    p_occs = get_passenger_train_occupancy(schedules or [], direction, min_k, max_k)
    g_occs = get_goods_train_occupancy(forecasts or [], direction, min_k, max_k)

    for (enter_t, exit_t) in (p_occs + g_occs):
        train_start = max(0, enter_t - safety_margin)
        train_end = exit_t + safety_margin
        if max(start_time, train_start) < min(end_time, train_end):
            return False
    return True

def explain_task_infeasibility(
    task: MaintenanceTask,
    schedules: List[TrainSchedule],
    forecasts: List[GoodsTrainForecast],
    horizon_mins: int = 43200,
    safety_margin: int = 15,
) -> str:
    """
    Computes mathematical root cause explanation for why a task could not be scheduled.
    """
    effective_deadline = min(task.deadline_mins, horizon_mins)
    if effective_deadline < task.duration_mins:
        return (
            f"Requested duration ({task.duration_mins}m) strictly exceeds deadline ({effective_deadline}m). "
            f"Mathematically impossible to schedule within deadline."
        )

    p_occs = get_passenger_train_occupancy(schedules or [], task.line_direction, task.start_km, task.end_km)
    g_occs = get_goods_train_occupancy(forecasts or [], task.line_direction, task.start_km, task.end_km)

    # Calculate blocked intervals before deadline
    blocked = []
    for (enter, exit_t) in (p_occs + g_occs):
        b_s = max(0, enter - safety_margin)
        b_e = min(effective_deadline, exit_t + safety_margin)
        if b_s < effective_deadline and b_e > 0 and b_s < b_e:
            blocked.append((b_s, b_e))

    blocked.sort()
    merged = []
    for b in blocked:
        if not merged or merged[-1][1] < b[0]:
            merged.append(b)
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b[1]))

    gaps = []
    curr = 0
    for b_s, b_e in merged:
        if b_s > curr:
            gaps.append(b_s - curr)
        curr = max(curr, b_e)
    if curr < effective_deadline:
        gaps.append(effective_deadline - curr)

    max_gap = max(gaps) if gaps else 0
    return (
        f"Requires {task.duration_mins}m clear window (with ±{safety_margin}m safety margin), "
        f"but maximum continuous headway before deadline ({effective_deadline}m / Day {effective_deadline/1440:.1f}) "
        f"is only {max_gap}m across {len(blocked)} train movements."
    )

def group_tasks_into_blocks(
    scheduled_intervals,
    direction: str = "Up",
    schedules: List[TrainSchedule] = None,
    forecasts: List[GoodsTrainForecast] = None,
    safety_margin: int = 15,
) -> List[PlannedBlock]:
    planned_blocks = []
    if not scheduled_intervals:
        return planned_blocks

    # Group by line direction first so Up and Down never combine
    by_dir = {}
    for item in scheduled_intervals:
        d = item[2].line_direction
        by_dir.setdefault(d, []).append(item)

    for dir_key, dir_intervals in by_dir.items():
        n = len(dir_intervals)
        adj = {i: [] for i in range(n)}

        for i in range(n):
            s1, e1, t1 = dir_intervals[i]
            min_k1, max_k1 = min(t1.start_km, t1.end_km), max(t1.start_km, t1.end_km)
            for j in range(i + 1, n):
                s2, e2, t2 = dir_intervals[j]
                min_k2, max_k2 = min(t2.start_km, t2.end_km), max(t2.start_km, t2.end_km)

                t_overlap = (s1 <= e2) and (s2 <= e1)
                s_overlap = (min_k1 <= max_k2) and (min_k2 <= max_k1)
                is_compatible = are_tasks_compatible(t1, t2)

                # Proposed pair envelope
                pair_min_k = min(min_k1, min_k2)
                pair_max_k = max(max_k1, max_k2)
                pair_start = min(s1, s2)
                pair_end = max(e1, e2)
                span_km = pair_max_k - pair_min_k

                # Enforce max 20 km span per block and train clearance
                span_ok = span_km <= 20.0

                if t_overlap and s_overlap and is_compatible and span_ok:
                    if is_block_envelope_safe(
                        schedules, forecasts, dir_key, pair_min_k, pair_max_k, pair_start, pair_end, safety_margin
                    ):
                        adj[i].append(j)
                        adj[j].append(i)

        visited = set()
        for i in range(n):
            if i not in visited:
                component = []
                queue = [i]
                visited.add(i)

                while queue:
                    curr = queue.pop(0)
                    component.append(dir_intervals[curr])
                    for neighbor in adj[curr]:
                        if neighbor not in visited:
                            visited.add(neighbor)
                            queue.append(neighbor)

                # Verify final component envelope safety against trains and enforce maximum 20 km span
                comp_min_k = min(min(t.start_km, t.end_km) for _, _, t in component)
                comp_max_k = max(max(t.start_km, t.end_km) for _, _, t in component)
                comp_start = min(s for s, _, _ in component)
                comp_end = max(e for _, e, _ in component)

                comp_span_km = comp_max_k - comp_min_k
                comp_span_ok = comp_span_km <= 20.0

                if comp_span_ok and is_block_envelope_safe(schedules, forecasts, dir_key, comp_min_k, comp_max_k, comp_start, comp_end, safety_margin):
                    planned_blocks.append(create_block_from_group(component, dir_key))
                else:
                    # If component envelope exceeds 20 km or intersects a train, partition into safe sub-clusters
                    sub_clusters = []
                    for item in component:
                        s, e, t = item
                        t_min = min(t.start_km, t.end_km)
                        t_max = max(t.start_km, t.end_km)
                        placed = False
                        for sc in sub_clusters:
                            test_c = sc + [item]
                            sc_min_k = min(min(it[2].start_km, it[2].end_km) for it in test_c)
                            sc_max_k = max(max(it[2].start_km, it[2].end_km) for it in test_c)
                            sc_start = min(it[0] for it in test_c)
                            sc_end = max(it[1] for it in test_c)
                            if (sc_max_k - sc_min_k <= 20.0) and is_block_envelope_safe(
                                schedules, forecasts, dir_key, sc_min_k, sc_max_k, sc_start, sc_end, safety_margin
                            ):
                                sc.append(item)
                                placed = True
                                break
                        if not placed:
                            sub_clusters.append([item])

                    for sc in sub_clusters:
                        planned_blocks.append(create_block_from_group(sc, dir_key))

    return planned_blocks

def create_block_from_group(group, direction):
    # A block's protected time window covers all consolidated tasks
    start_time = min(g[0] for g in group)
    end_time = max(g[1] for g in group)

    # A block's physical extent is the union of all task chainages inside it
    start_km = min(min(g[2].start_km, g[2].end_km) for g in group)
    end_km = max(max(g[2].start_km, g[2].end_km) for g in group)

    # Defensive invariant: hard maximum block span cannot exceed 20.0 km for consolidated blocks
    span = max(start_km, end_km) - min(start_km, end_km)
    if len(group) > 1 and span > 20.0001:
        raise ValueError(f"Block physical envelope ({span:.2f} km) exceeds maximum allowed span of 20.0 km")

    tasks = [g[2].id for g in group]

    depts = sorted(set(g[2].department for g in group))
    dept_str = ", ".join(depts)
    if len(tasks) > 1:
        reasoning = (
            f"Coordinated {direction} maintenance window ({len(tasks)} tasks across {dept_str}) "
            f"spanning Km {start_km:.1f} to {end_km:.1f} ({end_km - start_km:.1f} km). "
            f"Verified zero passenger or freight train path conflicts."
        )
    else:
        reasoning = (
            f"Optimized {direction} window between train paths spanning Km {start_km:.1f} to {end_km:.1f} "
            f"for {group[0][2].task_type} ({dept_str})."
        )

    return PlannedBlock(
        id=str(uuid.uuid4())[:8],
        start_time_mins=start_time,
        end_time_mins=end_time,
        start_km=start_km,
        end_km=end_km,
        line_direction=direction,
        assigned_tasks=tasks,
        reasoning=reasoning,
    )

