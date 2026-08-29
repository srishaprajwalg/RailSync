from ortools.sat.python import cp_model
from typing import List
from core.schemas import MaintenanceTask, PlannedBlock, TrainSchedule
from services.timetable_analyzer import get_train_occupancy, find_white_spaces
from services.compatibility import are_tasks_compatible
import uuid

def optimize_blocks(tasks: List[MaintenanceTask], schedules: List[TrainSchedule], safety_margin: int = 15) -> List[PlannedBlock]:
    """
    Core Optimization Engine using Google OR-Tools CP-SAT.
    """
    model = cp_model.CpModel()
    
    # We will plan per line direction separately to keep the model simpler for MVP
    planned_blocks = []
    
    for direction in ["Up", "Down"]:
        dir_tasks = [t for t in tasks if t.line_direction == direction]
        if not dir_tasks:
            continue
            
        # 1. Create variables for each task
        task_starts = {}
        task_ends = {}
        task_intervals = {}
        task_is_scheduled = {}
        
        for task in dir_tasks:
            task_is_scheduled[task.id] = model.NewBoolVar(f'scheduled_{task.id}')
            # Start can be anywhere from 0 to 1440 (24h in mins)
            task_starts[task.id] = model.NewIntVar(0, 1440, f'start_{task.id}')
            task_ends[task.id] = model.NewIntVar(0, 1440, f'end_{task.id}')
            task_intervals[task.id] = model.NewOptionalIntervalVar(
                task_starts[task.id], 
                task.duration_mins, 
                task_ends[task.id], 
                task_is_scheduled[task.id], 
                f'interval_{task.id}'
            )
            
            # Deadline constraint
            model.Add(task_ends[task.id] <= task.deadline_mins)

        # 2. Timetable safety constraints (No overlap with trains)
        # For MVP, we extract global white spaces for the whole line segment max extent of tasks, 
        # or we check per task. Checking per task is more accurate.
        for task in dir_tasks:
            occupancies = get_train_occupancy(schedules, direction, task.start_km, task.end_km)
            white_spaces = find_white_spaces(occupancies, safety_margin=safety_margin)
            
            # The task must fall completely within ONE of the white spaces if it is scheduled
            # We use a boolean variable for each white space option
            space_bools = []
            for i, (ws_start, ws_end) in enumerate(white_spaces):
                if ws_end - ws_start >= task.duration_mins:
                    in_space = model.NewBoolVar(f'task_{task.id}_in_space_{i}')
                    space_bools.append(in_space)
                    
                    # If in_space is true, task_start >= ws_start and task_end <= ws_end
                    model.Add(task_starts[task.id] >= ws_start).OnlyEnforceIf(in_space)
                    model.Add(task_ends[task.id] <= ws_end).OnlyEnforceIf(in_space)
            
            if space_bools:
                # If scheduled, it must be in exactly one space
                model.AddExactlyOne(space_bools).OnlyEnforceIf(task_is_scheduled[task.id])
            else:
                # No space can fit this task
                model.Add(task_is_scheduled[task.id] == 0)

        # 3. Task compatibility constraint (No overlap if incompatible)
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

        # 4. Objective function: Maximize priority of scheduled tasks
        objective_terms = []
        for task in dir_tasks:
            objective_terms.append(task_is_scheduled[task.id] * task.base_priority)
        model.Maximize(sum(objective_terms))

        # Solve
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 10.0 # Time limit for CP
        status = solver.Solve(model)
        
        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            # Consolidate overlapping scheduled tasks into PlannedBlocks
            scheduled_intervals = []
            for task in dir_tasks:
                if solver.Value(task_is_scheduled[task.id]):
                    s = solver.Value(task_starts[task.id])
                    e = solver.Value(task_ends[task.id])
                    scheduled_intervals.append((s, e, task))
            
            # Simple temporal-spatial grouping for block generation
            # Group if time overlaps and spatial is adjacent/overlapping
            # For MVP, we will just output individual blocks or simple consolidations
            scheduled_intervals.sort(key=lambda x: x[0])
            
            # Simple grouping heuristic post-optimization
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

    return planned_blocks

def create_block_from_group(group, direction):
    start_time = min(g[0] for g in group)
    end_time = max(g[1] for g in group)
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
