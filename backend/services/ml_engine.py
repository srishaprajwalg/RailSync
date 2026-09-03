import os
import datetime
import uuid
import numpy as np
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from backend.db.models import Asset, MaintenanceHistory, MaintenanceRequest, MLPrediction
from backend.services.ml_training_pipeline import (
    MODEL_NAME,
    FEATURE_VERSION,
    extract_canonical_features,
    load_persisted_model,
    train_recurrence_model,
)

class AssetRecurrencePredictor:
    """
    Data-driven Machine Learning inference engine for predicting defect recurrence and failure risk.
    Loads and runs the persisted Logistic Regression model artifact.
    """
    def __init__(self):
        self.model, self.metadata = load_persisted_model()
        self.model_name = self.metadata.get("model_name", MODEL_NAME)
        self.model_version = self.metadata.get("model_version", "v2.0.0")
        self.feature_version = self.metadata.get("feature_version", FEATURE_VERSION)

    def reload(self):
        """Reloads persisted model from disk."""
        self.model, self.metadata = load_persisted_model()
        self.model_name = self.metadata.get("model_name", MODEL_NAME)
        self.model_version = self.metadata.get("model_version", "v2.0.0")
        self.feature_version = self.metadata.get("feature_version", FEATURE_VERSION)

    def predict(
        self,
        asset: Optional[Asset],
        history: List[MaintenanceHistory],
        request: MaintenanceRequest,
    ) -> Dict[str, Any]:
        """
        Extracts canonical features and performs probabilistic inference.
        Separates prediction probability from historical data evidence/support score.
        """
        is_def = 1 if request.request_type.lower() == "defect" else 0
        sev = request.severity

        feat_dict = extract_canonical_features(
            asset=asset,
            history_prior_to_t=history,
            request_severity=sev,
            is_defect=is_def,
            observation_time=datetime.datetime.now(datetime.timezone.utc),
        )

        X = np.array([feat_dict["feature_vector"]], dtype=np.float64)
        probs = self.model.predict_proba(X)[0]
        prob_recurrence = float(probs[1])

        # Categorical classification label
        if prob_recurrence >= 0.70:
            prediction_label = "HIGH_RECURRENCE_RISK"
        elif prob_recurrence >= 0.45:
            prediction_label = "MODERATE_RECURRENCE_RISK"
        else:
            prediction_label = "LOW_RECURRENCE_RISK"

        # Evidence / Historical Data Support (NOT statistical model confidence)
        n_history = len(history)
        if n_history >= 4:
            data_support = "HIGH"
        elif n_history >= 2:
            data_support = "MODERATE"
        else:
            data_support = "LOW"
            
        evidence_score = min(0.50 + (n_history * 0.10), 0.95)

        return {
            "model_name": self.model_name,
            "model_version": self.model_version,
            "feature_version": self.feature_version,
            "prediction_type": "RECURRENCE_RISK",
            "prediction": prediction_label,
            "probability": round(prob_recurrence, 4),
            "evidence_score": round(evidence_score, 3),
            "data_support": data_support,
            "confidence": round(evidence_score, 3), # Preserved for schema compatibility
            "features_snapshot": feat_dict,
        }

# Global singleton predictor instance
_predictor_instance = AssetRecurrencePredictor()

def predict_maintenance_recurrence(db: Session, request: MaintenanceRequest) -> MLPrediction:
    """
    Runs ML prediction for a maintenance request against its asset's history in the DB.
    Persists and returns the MLPrediction entity.
    """
    asset = db.query(Asset).filter_by(id=request.asset_id).first() if request.asset_id else None
    history = db.query(MaintenanceHistory).filter_by(asset_id=request.asset_id).all() if request.asset_id else []

    pred_res = _predictor_instance.predict(asset, history, request)

    ml_pred = MLPrediction(
        id=f"MLP-{uuid.uuid4().hex[:8].upper()}",
        maintenance_request_id=request.id,
        asset_id=asset.id if asset else None,
        model_name=pred_res["model_name"],
        model_version=pred_res["model_version"],
        prediction_type=pred_res["prediction_type"],
        prediction=pred_res["prediction"],
        probability=pred_res["probability"],
        confidence=pred_res["confidence"],
        features_snapshot=pred_res["features_snapshot"],
    )
    db.add(ml_pred)
    db.flush()
    return ml_pred
