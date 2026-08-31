import pytest
from fastapi.testclient import TestClient
from main import app, tasks, TASK_DEFAULTS

client = TestClient(app)

def test_get_task_defaults():
    response = client.get("/api/tasks/defaults")
    assert response.status_code == 200
    data = response.json()
    assert "Track Tamping" in data
    assert data["Track Tamping"]["duration_mins"] == 120

def test_preview_priority_valid():
    payload = {
        "department": "TMS",
        "task_type": "Track Tamping",
        "origin": "Defect",
        "severity": 5,
        "overdue_days": 10,
        "asset_criticality": 5,
        "start_km": 10.0,
        "end_km": 12.0,
        "duration_mins": 120,
        "deadline_mins": 1440,
        "line_direction": "Up"
    }
    response = client.post("/api/tasks/preview-priority", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "score" in data
    assert "category" in data
    assert "explanation" in data
    assert data["score"] > 80  # Defect + Sev 5 + Crit 5 + Overdue 10 + Deadline 24h = High score

def test_preview_priority_missing_fields():
    payload = {
        "department": "TMS"
        # Missing other required fields
    }
    response = client.post("/api/tasks/preview-priority", json=payload)
    assert response.status_code == 422  # Unprocessable Entity (FastAPI validation)

def test_preview_matches_actual_processing():
    payload = {
        "department": "TMS",
        "task_type": "Routine Inspection",
        "origin": "Routine Maintenance",
        "severity": 1,
        "overdue_days": 0,
        "asset_criticality": 1,
        "start_km": 10.0,
        "end_km": 12.0,
        "duration_mins": 90,
        "deadline_mins": 10080, # 7 days
        "line_direction": "Up"
    }
    
    # 1. Preview Priority
    preview_res = client.post("/api/tasks/preview-priority", json=payload)
    assert preview_res.status_code == 200
    preview_score = preview_res.json()["score"]
    
    # 2. Add Task Actually
    add_res = client.post("/api/tasks", json=payload)
    assert add_res.status_code == 200
    tasks_list = add_res.json()
    added_task = tasks_list[-1]  # The newly added task is appended to the end
    
    # 3. Assert scores match
    assert added_task["priority_details"]["score"] == preview_score
    assert added_task["priority_details"]["score"] == 0 # Routine, Sev1, Crit1, 0 overdue, >72h deadline -> 0

def test_priority_changes_with_severity():
    payload = {
        "department": "TMS",
        "task_type": "Routine Inspection",
        "origin": "Routine Maintenance",
        "severity": 1,
        "overdue_days": 0,
        "asset_criticality": 1,
        "start_km": 10.0,
        "end_km": 12.0,
        "duration_mins": 90,
        "deadline_mins": 10080,
        "line_direction": "Up"
    }
    
    # Sev 1
    res1 = client.post("/api/tasks/preview-priority", json=payload)
    score1 = res1.json()["score"]
    
    # Sev 5
    payload["severity"] = 5
    res5 = client.post("/api/tasks/preview-priority", json=payload)
    score5 = res5.json()["score"]
    
    assert score5 > score1

def test_newly_created_task_lifecycle_status():
    payload = {
        "task_type": "Track Tamping",
        "origin": "Routine Maintenance",
        "severity": 1,
        "overdue_days": 0,
        "asset_criticality": 1,
        "start_km": 10.0,
        "end_km": 12.0,
        "duration_mins": 90,
        "deadline_mins": 10080,
        "line_direction": "Up"
    }
    res = client.post("/api/tasks", json=payload)
    assert res.status_code == 200
    added_task = res.json()[-1]
    assert added_task["lifecycle_status"] == "Prioritized"

def test_department_inferred_from_activity():
    payload = {
        "task_type": "Signal Failure",
        "origin": "Defect",
        "severity": 5,
        "overdue_days": 0,
        "asset_criticality": 5,
        "start_km": 10.0,
        "end_km": 12.0,
        "duration_mins": 60,
        "deadline_mins": 1440,
        "line_direction": "Up"
    }
    res = client.post("/api/tasks", json=payload)
    added_task = res.json()[-1]
    assert added_task["department"] == "Signalling"

def test_unknown_activity_safe():
    payload = {
        "task_type": "Laser Alignment",
        "origin": "Routine Maintenance",
        "severity": 1,
        "overdue_days": 0,
        "asset_criticality": 1,
        "start_km": 10.0,
        "end_km": 12.0,
        "duration_mins": 60,
        "deadline_mins": 1440,
        "line_direction": "Up"
    }
    res = client.post("/api/tasks", json=payload)
    added_task = res.json()[-1]
    assert added_task["department"] == "Unknown"
    assert added_task["lifecycle_status"] == "Prioritized"

def test_update_lifecycle_status():
    # First add a task
    payload = {
        "task_type": "Track Tamping",
        "origin": "Routine Maintenance",
        "severity": 1,
        "overdue_days": 0,
        "asset_criticality": 1,
        "start_km": 10.0,
        "end_km": 12.0,
        "duration_mins": 90,
        "deadline_mins": 10080,
        "line_direction": "Up"
    }
    res = client.post("/api/tasks", json=payload)
    added_task = res.json()[-1]
    task_id = added_task["id"]
    
    # Now update it
    update_res = client.put(f"/api/tasks/{task_id}/status", json={"lifecycle_status": "Completed"})
    assert update_res.status_code == 200
    
    # Verify it updated
    tasks_list = update_res.json()
    updated_task = next(t for t in tasks_list if t["id"] == task_id)
    assert updated_task["lifecycle_status"] == "Completed"
