import os
import sys
import json

# Add backend and project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from backend.db.session import SessionLocal
from backend.services.ml_training_pipeline import train_recurrence_model
from sqlalchemy import text

def run_training_cli():
    print("=" * 70)
    print(" RAILVYUHA MACHINE LEARNING TRAINING PIPELINE")
    print("=" * 70)
    
    db = None
    try:
        db = SessionLocal()
        # Test if DB is reachable
        db.execute(text("SELECT 1"))
    except Exception:
        db = None

    print(f"PostgreSQL Session   : {'CONNECTED' if db else 'UNAVAILABLE (Using Bootstrap Calibration)'}")
    
    report = train_recurrence_model(db=db, force_bootstrap_if_insufficient=True)

    print(f"Model Name           : {report['model_name']}")
    print(f"Model Version        : {report['model_version']}")
    print(f"Feature Version      : {report['feature_version']}")
    print(f"Sample Count         : {report['sample_count']}")
    print(f"Bootstrap Fallback   : {report['is_bootstrap_fallback']}")
    print(f"Data Source Type     : {report['dataset'].get('source_type', 'SYNTHETIC')}")
    print(f"Artifact Location    : {report['model_save_path']}")
    
    val = report["validation"]
    print("-" * 70)
    print(f"VALIDATION STATUS    : {val['validation_status']}")
    if val.get("message"):
        print(f"Notice               : {val['message']}")
    
    if val.get("metrics"):
        print("METRICS:")
        for k, v in val["metrics"].items():
            print(f"  - {k:<20}: {v}")
    
    if val.get("baseline_comparison"):
        print("BASELINE COMPARISONS:")
        for model_k, metrics in val["baseline_comparison"].items():
            print(f"  - {model_k:<30}: F1={metrics['f1_score']}, Acc={metrics['accuracy']}")

    print("=" * 70)
    if db:
        db.close()

if __name__ == "__main__":
    run_training_cli()
