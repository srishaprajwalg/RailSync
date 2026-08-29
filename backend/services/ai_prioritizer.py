from core.schemas import MaintenanceTask, PriorityDetails
from typing import List

def calculate_task_priority(task: MaintenanceTask, current_time_mins: int = 0) -> PriorityDetails:
    """
    Explainable task-priority scoring engine.
    Calculates a normalized score (0-100) based on operational factors:
    - Origin (Defect vs Routine)
    - Severity (1-5)
    - Asset Criticality (1-5)
    - Overdue Status
    - Deadline Urgency
    """
    score = 0
    factors = []
    
    # 1. Origin Base Score
    if task.origin.lower() == "defect":
        score += 20
        factors.append("Defect")
    else:
        # Routine maintenance starts at 0, builds score based on overdue/deadlines
        factors.append("Routine maintenance")
        
    # 2. Severity (1-5) -> up to 30 points
    # 1=0, 2=5, 3=10, 4=20, 5=30
    severity_map = {1: 0, 2: 5, 3: 10, 4: 20, 5: 30}
    sev_score = severity_map.get(task.severity, 0)
    score += sev_score
    if task.severity >= 4:
        factors.append(f"critical severity (L{task.severity})")
    elif task.severity == 3:
        factors.append(f"moderate severity (L{task.severity})")
        
    # 3. Asset Criticality (1-5) -> up to 10 points
    # 1=0, 2=2, 3=5, 4=7, 5=10
    crit_map = {1: 0, 2: 2, 3: 5, 4: 7, 5: 10}
    crit_score = crit_map.get(task.asset_criticality, 0)
    score += crit_score
    if task.asset_criticality >= 4:
        factors.append("on highly critical asset section")
        
    # 4. Overdue Status -> up to 20 points
    if task.overdue_days > 0:
        overdue_score = min(task.overdue_days * 2, 20)
        score += overdue_score
        factors.append(f"overdue by {task.overdue_days} days")
        
    # 5. Deadline Urgency -> up to 20 points
    time_to_deadline = task.deadline_mins - current_time_mins
    if time_to_deadline <= 1440: # Within 24 hours
        score += 20
        factors.append("immediate deadline (< 24h)")
    elif time_to_deadline <= 2880: # Within 48 hours
        score += 10
        factors.append("approaching deadline (< 48h)")
    elif time_to_deadline <= 4320: # Within 72 hours
        score += 5
        
    # Cap score at 100
    score = min(score, 100)
    
    # Determine Category
    if score >= 80:
        category = "Critical"
    elif score >= 60:
        category = "High"
    elif score >= 40:
        category = "Medium"
    else:
        category = "Low"
        
    # Construct explanation
    explanation = " + ".join(factors).capitalize() + "."
    
    return PriorityDetails(
        score=score,
        category=category,
        explanation=explanation
    )

def prioritize_tasks(tasks: List[MaintenanceTask], current_time_mins: int = 0) -> List[MaintenanceTask]:
    """Applies priority details to a list of tasks and sorts them."""
    for task in tasks:
        task.priority_details = calculate_task_priority(task, current_time_mins)
        
    # Sort descending by score
    return sorted(tasks, key=lambda t: t.priority_details.score, reverse=True)
