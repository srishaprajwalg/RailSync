import uuid
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session

from backend.core.schemas import MaintenanceTask, PriorityDetails
from backend.db.models import MaintenanceRequest, PriorityDecision, MLPrediction

ENGINE_VERSION = "v2.0-explainable-ml-hybrid"

def calculate_task_priority(
    task: MaintenanceTask,
    current_time_mins: int = 0,
    ml_risk_probability: Optional[float] = None
) -> PriorityDetails:
    """
    Explainable task-priority scoring engine.
    Calculates a normalized score (0-100) based on operational factors:
    - Origin (Defect vs Routine)
    - Severity (1-5)
    - Asset Criticality (1-5)
    - Overdue Status
    - Deadline Urgency
    - ML Recurrence Risk Signal (optional enhancement)
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

    # 6. ML Recurrence Signal (if available, adds risk weight)
    if ml_risk_probability is not None and ml_risk_probability > 0.5:
        ml_points = int(round(ml_risk_probability * 10))
        score += ml_points
        factors.append(f"ML recurrence risk ({int(ml_risk_probability * 100)}%)")
        
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

def calculate_and_persist_priority(
    db: Session,
    request: MaintenanceRequest,
    current_time_mins: int = 0,
    ml_pred: Optional[MLPrediction] = None
) -> PriorityDecision:
    """
    Computes priority score and stores the full explainable mathematical breakdown into priority_decisions table.
    """
    # Create temporary schema representation to reuse calculation
    schema_task = MaintenanceTask(
        id=request.id,
        department=request.department,
        task_type=request.defect_type,
        origin=request.request_type,
        severity=request.severity,
        overdue_days=request.overdue_days,
        asset_criticality=request.criticality,
        start_km=request.start_chainage,
        end_km=request.end_chainage,
        duration_mins=request.estimated_duration_minutes,
        deadline_mins=request.deadline_mins,
        line_direction=request.line_direction,
        required_resource=request.required_resource,
    )

    ml_prob = ml_pred.probability if ml_pred else None
    p_details = calculate_task_priority(schema_task, current_time_mins, ml_prob)

    severity_map = {1: 0, 2: 5, 3: 10, 4: 20, 5: 30}
    crit_map = {1: 0, 2: 2, 3: 5, 4: 7, 5: 10}
    
    sev_score = severity_map.get(request.severity, 0)
    crit_score = crit_map.get(request.criticality, 0)
    overdue_score = min(request.overdue_days * 2, 20) if request.overdue_days > 0 else 0
    time_to_deadline = request.deadline_mins - current_time_mins
    urgency_score = 20 if time_to_deadline <= 1440 else (10 if time_to_deadline <= 2880 else (5 if time_to_deadline <= 4320 else 0))
    ml_score = int(round(ml_prob * 10)) if (ml_prob and ml_prob > 0.5) else 0
    operational_impact_score = 10 if request.line_direction == "Up" else 5

    # Update request priority fields
    request.priority_score = p_details.score
    request.priority_category = p_details.category

    p_dec = PriorityDecision(
        id=f"PRD-{uuid.uuid4().hex[:8].upper()}",
        maintenance_request_id=request.id,
        priority_score=p_details.score,
        priority_category=p_details.category,
        ml_risk_score=ml_score,
        severity_score=sev_score,
        criticality_score=crit_score,
        urgency_score=urgency_score,
        overdue_score=overdue_score,
        operational_impact_score=operational_impact_score,
        reasoning=p_details.explanation,
        engine_version=ENGINE_VERSION,
    )
    db.add(p_dec)
    db.flush()
    return p_dec
