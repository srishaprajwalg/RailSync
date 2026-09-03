import os
import sys
import datetime
import joblib
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    average_precision_score,
    confusion_matrix,
    accuracy_score,
)
from sklearn.model_selection import StratifiedKFold

from backend.db.models import Asset, MaintenanceHistory, MaintenanceRequest

MODEL_NAME = "recurrence_logistic_v2"
FEATURE_VERSION = "recurrence_features_v2"
MODEL_VERSION_BOOTSTRAP = "v2.0.0-bootstrap-calibration"
MODEL_VERSION_DB = "v2.0.0-db-trained"

ARTIFACT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "artifacts", "models"))
DEFAULT_MODEL_PATH = os.path.join(ARTIFACT_DIR, f"{MODEL_NAME}.joblib")

FEATURE_NAMES = [
    "asset_age_years",
    "asset_criticality",
    "past_failures_count",
    "recurrence_ratio",
    "avg_past_duration_hrs",
    "time_since_last_failure_days",
    "request_severity",
    "is_defect",
]

# ---------------------------------------------------------------------------
# Canonical Feature Extraction (Used Identically for Training & Inference)
# ---------------------------------------------------------------------------

def extract_canonical_features(
    asset: Optional[Asset],
    history_prior_to_t: List[MaintenanceHistory],
    request_severity: int = 3,
    is_defect: int = 1,
    observation_time: Optional[datetime.datetime] = None,
) -> Dict[str, Any]:
    """
    Extracts the canonical 8-dimensional feature vector.
    Strictly uses historical records prior to observation time T to prevent target leakage.
    """
    age_years = float(asset.age_years) if asset and asset.age_years else 5.0
    criticality = float(asset.criticality) if asset and asset.criticality else 3.0

    total_prior_events = len(history_prior_to_t)
    failures = [h for h in history_prior_to_t if h.failure or h.recurrence]
    failure_count = len(failures)
    recurrence_count = sum(1 for h in history_prior_to_t if h.recurrence)
    
    rec_ratio = (recurrence_count / total_prior_events) if total_prior_events > 0 else 0.0
    avg_duration_hrs = (
        sum(h.duration_minutes for h in history_prior_to_t) / (total_prior_events * 60.0)
        if total_prior_events > 0 else 2.0
    )

    # Calculate days since last failure before observation time T
    if failures and observation_time:
        # Sort by completed_at descending
        sorted_fails = sorted(failures, key=lambda f: f.completed_at or f.created_at, reverse=True)
        last_fail_time = sorted_fails[0].completed_at or sorted_fails[0].created_at
        if last_fail_time.tzinfo is None:
            last_fail_time = last_fail_time.replace(tzinfo=datetime.timezone.utc)
        if observation_time.tzinfo is None:
            observation_time = observation_time.replace(tzinfo=datetime.timezone.utc)
        days_since = max(0.0, (observation_time - last_fail_time).total_seconds() / 86400.0)
    elif failures:
        days_since = 30.0
    else:
        # Default to asset age in days if no previous failures
        days_since = age_years * 365.0

    feature_vector = [
        float(age_years),
        float(criticality),
        float(failure_count),
        float(rec_ratio),
        float(avg_duration_hrs),
        float(days_since),
        float(request_severity),
        float(is_defect),
    ]

    return {
        "feature_version": FEATURE_VERSION,
        "feature_names": FEATURE_NAMES,
        "feature_vector": feature_vector,
        "asset_id": asset.id if asset else None,
        "asset_age_years": age_years,
        "asset_criticality": criticality,
        "total_prior_events": total_prior_events,
        "past_failures_count": failure_count,
        "recurrence_ratio": round(rec_ratio, 3),
        "avg_past_duration_hrs": round(avg_duration_hrs, 2),
        "time_since_last_failure_days": round(days_since, 1),
        "request_severity": request_severity,
        "is_defect": is_defect,
    }

# ---------------------------------------------------------------------------
# Bootstrap Synthetic Calibration Dataset
# ---------------------------------------------------------------------------

def get_bootstrap_calibration_dataset() -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
    """
    Returns the explicitly labeled bootstrap calibration dataset.
    Derived from Indian Railways asset degradation and failure recurrence curves.
    """
    X_train = np.array([
        # [age, crit, past_fails, rec_ratio, avg_dur, time_since_fail, sev, is_defect]
        [2.0, 1.0, 0.0, 0.00, 1.0, 730.0, 1.0, 0.0],   # Young asset, routine, 0 failures -> No recurrence (0)
        [4.0, 2.0, 0.0, 0.00, 1.5, 1460.0, 2.0, 0.0],  # Normal wear -> No recurrence (0)
        [8.0, 3.0, 1.0, 0.00, 2.0, 180.0, 3.0, 1.0],   # Moderate age, 1 failure -> Low-medium (0)
        [12.0, 4.0, 2.0, 0.50, 3.0, 45.0, 4.0, 1.0],   # Old asset, 2 failures, 50% recurrent -> High (1)
        [15.0, 5.0, 3.0, 0.67, 3.5, 15.0, 5.0, 1.0],   # Critical old section, multiple fractures -> Critical recurrence (1)
        [18.0, 5.0, 4.0, 0.75, 4.0, 10.0, 5.0, 1.0],   # Extreme wear -> Critical recurrence (1)
        [6.0, 3.0, 0.0, 0.00, 1.5, 2190.0, 2.0, 0.0],  # Mid age, preventive -> No recurrence (0)
        [10.0, 4.0, 2.0, 0.50, 2.5, 60.0, 3.0, 1.0],   # Elevated risk (1)
        [1.0, 2.0, 0.0, 0.00, 1.0, 365.0, 1.0, 0.0],   # Low risk (0)
        [14.0, 4.0, 3.0, 0.67, 3.0, 30.0, 4.0, 1.0],   # High risk (1)
    ])
    y_train = np.array([0, 0, 0, 1, 1, 1, 0, 1, 0, 1])
    
    meta = {
        "dataset_name": "BOOTSTRAP_SYNTHETIC_CALIBRATION",
        "sample_count": len(y_train),
        "positive_count": int(np.sum(y_train == 1)),
        "negative_count": int(np.sum(y_train == 0)),
        "source_type": "SYNTHETIC",
        "provenance": "Calibrated baseline degradation curves for railway assets",
    }
    return X_train, y_train, meta

# ---------------------------------------------------------------------------
# Training Dataset Construction from PostgreSQL Historical Records
# ---------------------------------------------------------------------------

def build_training_dataset_from_db(db: Session) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
    """
    Constructs training dataset from PostgreSQL MaintenanceHistory records.
    Uses temporal observation windows at time T for each historical event
    to strictly prevent target leakage.
    """
    history_records = db.query(MaintenanceHistory).order_by(MaintenanceHistory.created_at.asc()).all()
    
    if not history_records:
        return np.empty((0, 8)), np.empty(0), {"sample_count": 0, "status": "NO_HISTORICAL_DATA"}

    X_list = []
    y_list = []

    def _to_utc(dt: Optional[datetime.datetime]) -> Optional[datetime.datetime]:
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=datetime.timezone.utc)
        return dt

    for event in history_records:
        asset = db.query(Asset).filter_by(id=event.asset_id).first() if event.asset_id else None
        obs_time = _to_utc(event.started_at or event.created_at)
        
        # Query prior history on the same asset strictly before obs_time (No Leakage)
        prior_history = [
            h for h in history_records
            if h.asset_id == event.asset_id and _to_utc(h.completed_at or h.created_at) < obs_time and h.id != event.id
        ]
        
        # Severity and defect classification derived from event
        is_def = 1 if event.event_type.upper() in ("CORRECTIVE", "EMERGENCY") else 0
        sev = 5 if event.event_type.upper() == "EMERGENCY" else (3 if is_def else 1)

        feat_dict = extract_canonical_features(
            asset=asset,
            history_prior_to_t=prior_history,
            request_severity=sev,
            is_defect=is_def,
            observation_time=obs_time,
        )
        
        # Target label: 1 if recurrent/failure event, 0 otherwise
        target = 1 if (event.recurrence or event.failure) else 0

        X_list.append(feat_dict["feature_vector"])
        y_list.append(target)

    X = np.array(X_list, dtype=np.float64)
    y = np.array(y_list, dtype=np.int64)

    pos_count = int(np.sum(y == 1))
    neg_count = int(np.sum(y == 0))

    meta = {
        "dataset_name": "POSTGRESQL_MAINTENANCE_HISTORY",
        "sample_count": len(y),
        "positive_count": pos_count,
        "negative_count": neg_count,
        "source_type": "SYNTHETIC",
        "provenance": "Constructed from relational maintenance_history records without target leakage",
    }
    return X, y, meta

# ---------------------------------------------------------------------------
# Model Evaluation & Baseline Comparison
# ---------------------------------------------------------------------------

def evaluate_model_and_baselines(
    X: np.ndarray,
    y: np.ndarray,
    model: LogisticRegression,
) -> Dict[str, Any]:
    """
    Evaluates Logistic Regression against:
    1. Majority-Class Baseline
    2. Deterministic Rule Heuristic (Defect + Severity >= 4 + Past Failures >= 1)
    """
    n_samples = len(y)
    n_pos = int(np.sum(y == 1))
    n_neg = int(np.sum(y == 0))

    if n_samples < 15 or n_pos < 2 or n_neg < 2:
        return {
            "validation_status": "INSUFFICIENT_DATA_FOR_VALIDATION",
            "sample_count": n_samples,
            "class_distribution": {"positive": n_pos, "negative": n_neg},
            "message": "Dataset too small (<15 samples or single-class) for statistically valid cross-validation.",
            "metrics": None,
            "baseline_comparison": None,
        }

    # Stratified K-Fold validation
    k_folds = min(5, min(n_pos, n_neg))
    skf = StratifiedKFold(n_splits=k_folds, shuffle=True, random_state=42)

    y_true_all = []
    y_pred_all = []
    y_prob_all = []
    y_majority_all = []
    y_heuristic_all = []

    # Majority class on full dataset
    majority_class = 1 if n_pos >= n_neg else 0

    for train_idx, val_idx in skf.split(X, y):
        X_tr, X_val = X[train_idx], X[val_idx]
        y_tr, y_val = y[train_idx], y[val_idx]

        fold_clf = LogisticRegression(random_state=42)
        fold_clf.fit(X_tr, y_tr)

        probs = fold_clf.predict_proba(X_val)[:, 1]
        preds = fold_clf.predict(X_val)

        y_true_all.extend(y_val)
        y_pred_all.extend(preds)
        y_prob_all.extend(probs)
        y_majority_all.extend([majority_class] * len(y_val))

        # Heuristic: is_defect (col 7) == 1 and sev (col 6) >= 4 and past_fails (col 2) >= 1
        heur_preds = [
            1 if (row[7] == 1.0 and row[6] >= 4.0 and row[2] >= 1.0) else 0
            for row in X_val
        ]
        y_heuristic_all.extend(heur_preds)

    y_true_np = np.array(y_true_all)
    y_pred_np = np.array(y_pred_all)
    y_prob_np = np.array(y_prob_all)

    # Compute Metrics
    acc = float(accuracy_score(y_true_np, y_pred_np))
    prec = float(precision_score(y_true_np, y_pred_np, zero_division=0))
    rec = float(recall_score(y_true_np, y_pred_np, zero_division=0))
    f1 = float(f1_score(y_true_np, y_pred_np, zero_division=0))
    
    try:
        roc_auc = float(roc_auc_score(y_true_np, y_prob_np))
    except Exception:
        roc_auc = None
    try:
        pr_auc = float(average_precision_score(y_true_np, y_prob_np))
    except Exception:
        pr_auc = None

    cm = confusion_matrix(y_true_np, y_pred_np).tolist()

    # Baseline metrics
    maj_f1 = float(f1_score(y_true_np, y_majority_all, zero_division=0))
    maj_acc = float(accuracy_score(y_true_np, y_majority_all))
    heur_f1 = float(f1_score(y_true_np, y_heuristic_all, zero_division=0))
    heur_acc = float(accuracy_score(y_true_np, y_heuristic_all))

    return {
        "validation_status": "VALIDATED_STRATIFIED_KFOLD",
        "k_folds": k_folds,
        "sample_count": n_samples,
        "class_distribution": {"positive": n_pos, "negative": n_neg},
        "metrics": {
            "accuracy": round(acc, 4),
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1_score": round(f1, 4),
            "roc_auc": round(roc_auc, 4) if roc_auc is not None else "N/A",
            "pr_auc": round(pr_auc, 4) if pr_auc is not None else "N/A",
            "confusion_matrix": cm,
        },
        "baseline_comparison": {
            "logistic_regression": {"f1_score": round(f1, 4), "accuracy": round(acc, 4)},
            "majority_class_baseline": {"f1_score": round(maj_f1, 4), "accuracy": round(maj_acc, 4)},
            "deterministic_rule_heuristic": {"f1_score": round(heur_f1, 4), "accuracy": round(heur_acc, 4)},
        }
    }

# ---------------------------------------------------------------------------
# Model Training & Persistence Service
# ---------------------------------------------------------------------------

def train_recurrence_model(
    db: Optional[Session] = None,
    force_bootstrap_if_insufficient: bool = True,
    model_save_path: str = DEFAULT_MODEL_PATH,
) -> Dict[str, Any]:
    """
    Executes the complete ML training pipeline:
    1. Extracts training examples from PostgreSQL historical maintenance data.
    2. Checks data sufficiency; falls back to bootstrap calibration dataset if insufficient.
    3. Fits Logistic Regression model.
    4. Evaluates model with cross-validation and baseline comparison.
    5. Persists model artifact and comprehensive metadata with joblib.
    6. Returns structured training audit report.
    """
    used_bootstrap = False
    if db is not None:
        X_train, y_train, data_meta = build_training_dataset_from_db(db)
        if len(y_train) < 15 and force_bootstrap_if_insufficient:
            X_train, y_train, data_meta = get_bootstrap_calibration_dataset()
            used_bootstrap = True
    else:
        X_train, y_train, data_meta = get_bootstrap_calibration_dataset()
        used_bootstrap = True

    model_version = MODEL_VERSION_BOOTSTRAP if used_bootstrap else MODEL_VERSION_DB

    # Train final classifier
    clf = LogisticRegression(random_state=42)
    clf.fit(X_train, y_train)

    # Evaluate
    val_report = evaluate_model_and_baselines(X_train, y_train, clf)

    # Ensure output directory exists
    os.makedirs(os.path.dirname(model_save_path), exist_ok=True)

    metadata = {
        "model_name": MODEL_NAME,
        "model_version": model_version,
        "feature_version": FEATURE_VERSION,
        "feature_names": FEATURE_NAMES,
        "trained_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "sample_count": len(y_train),
        "class_distribution": {
            "positive": int(np.sum(y_train == 1)),
            "negative": int(np.sum(y_train == 0)),
        },
        "dataset_metadata": data_meta,
        "validation": val_report,
        "is_bootstrap_fallback": used_bootstrap,
    }

    # Persist model payload
    payload = {
        "model": clf,
        "metadata": metadata,
    }
    joblib.dump(payload, model_save_path)

    return {
        "status": "SUCCESS",
        "model_name": MODEL_NAME,
        "model_version": model_version,
        "feature_version": FEATURE_VERSION,
        "model_save_path": model_save_path,
        "sample_count": len(y_train),
        "is_bootstrap_fallback": used_bootstrap,
        "dataset": data_meta,
        "validation": val_report,
    }

def load_persisted_model(model_path: str = DEFAULT_MODEL_PATH) -> Tuple[LogisticRegression, Dict[str, Any]]:
    """
    Loads persisted model and metadata from joblib artifact.
    If no artifact exists, trains and saves the baseline model first.
    """
    if not os.path.exists(model_path):
        train_recurrence_model(model_save_path=model_path)
    
    payload = joblib.load(model_path)
    return payload["model"], payload["metadata"]
