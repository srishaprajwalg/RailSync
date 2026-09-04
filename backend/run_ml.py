import sys
import os
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.services.ml_training_pipeline import train_recurrence_model
from backend.db.session import SessionLocal

db = SessionLocal()
res = train_recurrence_model(db=db)
print(json.dumps(res, indent=2))
