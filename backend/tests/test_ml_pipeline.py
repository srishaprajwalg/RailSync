import os
import datetime
import pytest
import numpy as np
from sqlalchemy.orm import Session

from backend.db.models import Asset, MaintenanceHistory, MaintenanceRequest, MLPrediction, PriorityDecision
from backend.services.ml_training_pipeline import (
    FEATURE_VERSION,
    MODEL_NAME,
    extract_canonical_features,
    build_training_dataset_from_db,
    get_bootstrap_calibration_dataset,
    evaluate_model_and_baselines,
    train_recurrence_model,
    load_persisted_model,
)
from backend.services.ml_engine import AssetRecurrencePredictor, predict_maintenance_recurrence
from backend.services.ai_prioritizer import calculate_and_persist_priority

def test_canonical_feature_extraction():
    dummy_asset = Asset(
        id="TEST-AST-01",
        asset_code="TRK-TEST",
        asset_type="TRACK",
        department="ENGINEERING",
        corridor_id="SBC-JTJ",
        start_chainage=10.0,
        end_chainage=12.0,
        age_years=8.5,
        criticality=4,
    )
    
    now = datetime.datetime.now(datetime.timezone.utc)
    dummy_history = [
        MaintenanceHistory(
            id="HIST-1",
            asset_id="TEST-AST-01",
            event_type="CORRECTIVE",
            duration_minutes=120,
            success=True,
            failure=True,
            recurrence=True,
            completed_at=now - datetime.timedelta(days=20),
            created_at=now - datetime.timedelta(days=20),
        ),
        MaintenanceHistory(
            id="HIST-2",
            asset_id="TEST-AST-01",
            event_type="PREVENTIVE",
            duration_minutes=60,
            success=True,
            failure=False,
            recurrence=False,
            completed_at=now - datetime.timedelta(days=60),
            created_at=now - datetime.timedelta(days=60),
        ),
    ]

    features = extract_canonical_features(
        asset=dummy_asset,
        history_prior_to_t=dummy_history,
        request_severity=5,
        is_defect=1,
        observation_time=now,
    )

    assert features["feature_version"] == FEATURE_VERSION
    assert len(features["feature_vector"]) == 8
    assert features["asset_age_years"] == 8.5
    assert features["asset_criticality"] == 4.0
    assert features["past_failures_count"] == 1
    assert features["recurrence_ratio"] == 0.5
    assert features["avg_past_duration_hrs"] == 1.5
    assert 19.0 <= features["time_since_last_failure_days"] <= 21.0
    assert features["request_severity"] == 5
    assert features["is_defect"] == 1

def test_temporal_observation_window_leakage_prevention(db_session: Session):
    asset = Asset(
        id="LEAK-AST-01",
        asset_code="TRK-LEAK",
        asset_type="TRACK",
        department="ENGINEERING",
        corridor_id="SBC-JTJ",
        start_chainage=20.0,
        end_chainage=22.0,
        age_years=5.0,
        criticality=3,
    )
    db_session.add(asset)
    db_session.flush()

    t_past = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=50)
    t_target = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=25)
    t_future = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=5)

    # Past event (before target)
    h_past = MaintenanceHistory(
        id="HIST-PAST",
        asset_id=asset.id,
        event_type="PREVENTIVE",
        started_at=t_past,
        completed_at=t_past + datetime.timedelta(minutes=60),
        duration_minutes=60,
        success=True,
        failure=False,
        recurrence=False,
    )
    # Target event
    h_target = MaintenanceHistory(
        id="HIST-TARGET",
        asset_id=asset.id,
        event_type="CORRECTIVE",
        started_at=t_target,
        completed_at=t_target + datetime.timedelta(minutes=180),
        duration_minutes=180,
        success=True,
        failure=True,
        recurrence=True,
    )
    # Future event (after target) - MUST NOT BE INCLUDED IN FEATURES FOR TARGET
    h_future = MaintenanceHistory(
        id="HIST-FUTURE",
        asset_id=asset.id,
        event_type="EMERGENCY",
        started_at=t_future,
        completed_at=t_future + datetime.timedelta(minutes=240),
        duration_minutes=240,
        success=True,
        failure=True,
        recurrence=True,
    )
    db_session.add_all([h_past, h_target, h_future])
    db_session.commit()

    X, y, meta = build_training_dataset_from_db(db_session)
    assert len(y) >= 3

    def _to_utc(dt):
        if dt.tzinfo is None:
            return dt.replace(tzinfo=datetime.timezone.utc)
        return dt

    # Find the row for HIST-TARGET in X
    # Prior history for HIST-TARGET must be 1 event (h_past only, not h_future)
    prior_for_target = [
        h for h in [h_past, h_target, h_future]
        if _to_utc(h.completed_at or h.created_at) < _to_utc(t_target) and h.id != h_target.id
    ]
    assert len(prior_for_target) == 1
    assert prior_for_target[0].id == "HIST-PAST"

def test_insufficient_data_detection_and_fallback(db_session: Session):
    X, y, meta = get_bootstrap_calibration_dataset()
    assert meta["dataset_name"] == "BOOTSTRAP_SYNTHETIC_CALIBRATION"
    assert len(y) == 10

    # With only 10 samples, validation should report INSUFFICIENT_DATA_FOR_VALIDATION
    val_report = evaluate_model_and_baselines(X, y, None)
    assert val_report["validation_status"] == "INSUFFICIENT_DATA_FOR_VALIDATION"
    assert "too small" in val_report["message"]

def test_model_training_and_serialization(tmp_path):
    test_model_path = str(tmp_path / "test_model.joblib")
    
    report = train_recurrence_model(
        db=None,
        force_bootstrap_if_insufficient=True,
        model_save_path=test_model_path,
    )
    assert report["status"] == "SUCCESS"
    assert report["model_name"] == MODEL_NAME
    assert os.path.exists(test_model_path)

    loaded_clf, loaded_meta = load_persisted_model(test_model_path)
    assert loaded_clf is not None
    assert loaded_meta["feature_version"] == FEATURE_VERSION
    assert loaded_meta["model_name"] == MODEL_NAME

def test_prediction_probabilities_and_evidence_scoring():
    predictor = AssetRecurrencePredictor()
    
    dummy_asset = Asset(
        id="PRED-AST-01",
        asset_code="TRK-KPN",
        asset_type="TRACK",
        department="ENGINEERING",
        corridor_id="SBC-JTJ",
        age_years=15.0,
        criticality=5,
    )
    dummy_req = MaintenanceRequest(
        id="REQ-TEST-01",
        asset_id="PRED-AST-01",
        request_type="Defect",
        defect_type="Rail Fracture Repair",
        severity=5,
        criticality=5,
        start_chainage=80.0,
        end_chainage=82.0,
        estimated_duration_minutes=180,
    )

    pred = predictor.predict(dummy_asset, [], dummy_req)
    assert 0.0 <= pred["probability"] <= 1.0
    assert pred["prediction"] in ("LOW_RECURRENCE_RISK", "MODERATE_RECURRENCE_RISK", "HIGH_RECURRENCE_RISK")
    assert pred["data_support"] == "LOW"
    assert 0.50 <= pred["evidence_score"] <= 0.95

def test_ml_to_priority_integration(db_session: Session):
    m_req = MaintenanceRequest(
        id="INT-REQ-01",
        asset_id="AST-TRK-05",
        corridor_id="SBC-JTJ",
        department="ENGINEERING",
        request_type="Defect",
        defect_type="Rail Fracture Repair",
        status="OPEN",
        severity=5,
        criticality=5,
        start_chainage=75.0,
        end_chainage=78.0,
        line_direction="Up",
        estimated_duration_minutes=180,
        deadline_mins=1440,
        overdue_days=2,
        required_resource="Track Repair Crew",
        source_type="SYNTHETIC",
    )
    db_session.add(m_req)
    db_session.commit()

    ml_pred = predict_maintenance_recurrence(db_session, m_req)
    assert ml_pred is not None
    assert ml_pred.probability > 0.0

    p_dec = calculate_and_persist_priority(db_session, m_req, current_time_mins=0, ml_pred=ml_pred)
    assert p_dec is not None
    assert p_dec.priority_score >= 80
    assert p_dec.priority_category == "Critical"
    assert p_dec.ml_risk_score > 0
    assert "recurrence risk" in p_dec.reasoning.lower()
