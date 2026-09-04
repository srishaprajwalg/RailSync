import sys
import os
import uuid
import datetime
import random

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.db.session import SessionLocal
from backend.db.models import Asset, MaintenanceHistory

def generate_synthetic_history():
    db = SessionLocal()
    assets = db.query(Asset).all()
    
    if not assets:
        print("No assets found.")
        return
        
    records = []
    now = datetime.datetime.now(datetime.timezone.utc)
    
    # We want approx 2000 total records. 63 assets * ~32 events = 2016 records.
    for asset in assets:
        age_days = (asset.age_years or 5.0) * 365
        crit = asset.criticality or 3
        
        # Determine number of events based on age and criticality
        num_events = int((age_days / 365) * 4 + crit * 2 + random.randint(-5, 10))
        num_events = max(10, min(80, num_events)) # Keep bounded
        
        # Generate random time offsets for these events (sorted)
        event_offsets = sorted([random.uniform(10, age_days) for _ in range(num_events)], reverse=True)
        
        had_failure = False
        
        for offset_days in event_offsets:
            event_start = now - datetime.timedelta(days=offset_days)
            duration = random.choice([60, 90, 120, 180, 240, 360])
            event_end = event_start + datetime.timedelta(minutes=duration)
            
            # Determine type
            if had_failure:
                # Higher chance of CORRECTIVE if recent failure
                ev_type = random.choices(["PREVENTIVE", "CORRECTIVE", "EMERGENCY", "INSPECTION"], [20, 40, 10, 30])[0]
            else:
                ev_type = random.choices(["PREVENTIVE", "CORRECTIVE", "EMERGENCY", "INSPECTION"], [50, 20, 5, 25])[0]
            
            # Calculate failure probability based on age, criticality, and previous failures
            fail_prob = 0.05 + (crit * 0.02) + (offset_days / (age_days + 1) * 0.05)
            if had_failure:
                fail_prob += 0.15
                
            is_failure = random.random() < fail_prob
            is_recurrence = False
            
            if is_failure:
                if had_failure:
                    is_recurrence = random.random() < 0.6  # 60% chance to be classified as recurrence if it failed before
                had_failure = True
            else:
                # Slowly decay the failure state
                if random.random() < 0.3:
                    had_failure = False
                    
            if ev_type == "EMERGENCY":
                is_failure = True
                
            record = MaintenanceHistory(
                id=f"SYN-MH-{uuid.uuid4().hex[:8].upper()}",
                asset_id=asset.id,
                maintenance_request_id=None,
                event_type=ev_type,
                failure_type="Component Degradation" if is_failure else None,
                started_at=event_start,
                completed_at=event_end,
                duration_minutes=duration,
                success=not is_failure,
                failure=is_failure,
                recurrence=is_recurrence,
                team="Maintenance Crew " + str(random.randint(1, 5)),
                notes="Synthetic historical record for ML calibration.",
                created_at=event_start,  # Explicitly override the TimestampMixin default
                updated_at=event_end
            )
            records.append(record)
            
    print(f"Generated {len(records)} synthetic historical records.")
    db.add_all(records)
    db.commit()
    print("Committed successfully.")

if __name__ == "__main__":
    generate_synthetic_history()
