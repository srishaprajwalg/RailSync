from core.schemas import MaintenanceTask
from typing import List

# Explicit compatibility matrix based on task types
# Returns True if task1 and task2 can be executed in parallel at the same location/time
def are_tasks_compatible(task1: MaintenanceTask, task2: MaintenanceTask) -> bool:
    # Basic logic: 
    # If they are on different lines (Up vs Down), they are completely independent blocks, 
    # but they don't constrain each other for consolidation on the SAME block.
    # Actually, consolidation only happens for tasks on the same line.
    if task1.line_direction != task2.line_direction:
        return False
        
    t1, t2 = task1.task_type, task2.task_type
    
    # If tasks are exactly the same type, they might conflict over the same physical asset, 
    # but let's assume they are different tasks.
    if task1.id == task2.id:
        return True
        
    # Example constraints:
    # 1. Track Tamping (TMS) requires heavy machinery on track. It is compatible with OHE Maintenance (TDMS) 
    #    ONLY IF OHE maintenance doesn't require power block that disables the tamping machine (assume diesel, so it's fine).
    # 2. Point Overhaul (SMMS) requires track access and testing. It might NOT be compatible with Track Tamping at the exact same location.
    
    incompatible_pairs = [
        {"Track Tamping", "Point Overhaul"}, # Cannot tamp track while overhauling the same points
        # Add more real-world constraints here
    ]
    
    pair = {t1, t2}
    if pair in incompatible_pairs:
        return False
        
    return True
