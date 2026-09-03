import pytest
from fastapi.testclient import TestClient

from backend.main import app, TASK_DEFAULTS

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
    # Find the newly added task by origin and task_type
    matching = [t for t in tasks_list if t["task_type"] == "Routine Inspection" and t["start_km"] == 10.0]
    assert len(matching) > 0
    added_task = matching[0]
    
    # 3. Assert scores match
    assert added_task["priority_details"]["score"] == preview_score
    assert added_task["priority_details"]["score"] == 0

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
    matching = [t for t in res.json() if t["id"].startswith("MANUAL-")]
    assert len(matching) > 0
    added_task = matching[0]
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
    matching = [t for t in res.json() if t["id"].startswith("MANUAL-") and t["task_type"] == "Signal Failure"]
    assert len(matching) > 0
    added_task = matching[0]
    assert added_task["department"] == "Signalling"

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
    matching = [t for t in res.json() if t["id"].startswith("MANUAL-")]
    assert len(matching) > 0
    task_id = matching[0]["id"]
    
    # Now update it
    update_res = client.put(f"/api/tasks/{task_id}/status", json={"lifecycle_status": "Completed"})
    assert update_res.status_code == 200
    
    # Verify it updated
    tasks_list = update_res.json()
    updated_task = next(t for t in tasks_list if t["id"] == task_id)
    assert updated_task["lifecycle_status"] == "Completed"

def test_override_priority():
    # 1. Add a test task
    payload = {
        "task_type": "Insulator Flashover",
        "origin": "Defect",
        "severity": 3,
        "overdue_days": 2,
        "asset_criticality": 3,
        "start_km": 25.0,
        "end_km": 28.0,
        "duration_mins": 90,
        "deadline_mins": 1440,
        "line_direction": "Up"
    }
    res = client.post("/api/tasks", json=payload)
    matching = [t for t in res.json() if t["id"].startswith("MANUAL-") and t["task_type"] == "Insulator Flashover"]
    assert len(matching) > 0
    task_id = matching[0]["id"]
    
    # 2. Execute manual dispatcher override
    override_payload = {
        "override_score": 95,
        "override_reason": "Severe arcing reported by oncoming loco pilot; requires emergency track possession",
        "overridden_by": "Chief Controller SBC"
    }
    override_res = client.post(f"/api/tasks/{task_id}/override-priority", json=override_payload)
    assert override_res.status_code == 200
    data = override_res.json()
    assert data["task_id"] == task_id
    assert data["new_score"] == 95
    assert data["new_category"] == "Critical"
    assert data["overridden_by"] == "Chief Controller SBC"

def test_get_latest_optimization_run_and_decisions():
    # Test getting latest run
    run_res = client.get("/api/optimization/runs/latest")
    if run_res.status_code == 200:
        run_data = run_res.json()
        assert "solver" in run_data
        assert "metrics" in run_data

    # Test getting blocks and decisions
    blocks_res = client.get("/api/blocks")
    assert blocks_res.status_code == 200
    blocks = blocks_res.json()
    if len(blocks) > 0:
        block_id = blocks[0]["id"]
        dec_res = client.get(f"/api/blocks/{block_id}/decisions")
        assert dec_res.status_code == 200
        assert isinstance(dec_res.json(), list)

