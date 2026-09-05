import sys
import os
import uuid
import datetime
import random

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.db.session import SessionLocal
from backend.db.models import Asset, MaintenanceHistory, Section

def generate_synthetic_history():
    # Set fixed seed for reproducibility
    random.seed(42)

    db = SessionLocal()

    # Clean existing data to prevent accumulation
    db.query(MaintenanceHistory).delete()
    db.commit()

    # Join Asset and Section to get corridor_id
    assets_info = db.query(Asset, Section.corridor_id).join(Section).all()

    if not assets_info:
        print("No assets found.")
        return

    records = []
    now = datetime.datetime.now(datetime.timezone.utc)

    for asset, corridor_id in assets_info:
        age_days = (asset.age_years or 5.0) * 365
        crit = asset.criticality or 3

        # Corridor multipliers
        corridor_multiplier = 1.0
        if corridor_id == "NDLS-CNB":
            corridor_multiplier = 1.2
        elif corridor_id == "CSTM-PUNE":
            corridor_multiplier = 1.1

        current_offset = age_days
        had_failure = False
        consecutive_failures = 0

        while current_offset > 5:
            # Asset degradation: failure hazard generally increases as the asset becomes older
            age_factor = ((age_days - current_offset) / age_days) * 0.10
            fail_prob = 0.05 + (crit * 0.02) + age_factor
            fail_prob *= corridor_multiplier

            if had_failure:
                fail_prob += 0.15 + (consecutive_failures * 0.05)
                # Next event happens sooner if there was a failure (clustering)
                time_step = random.uniform(5, 30)
            else:
                # Normal preventive intervals
                time_step = random.uniform(60, 180)

            current_offset -= time_step
            if current_offset <= 0:
                break

            event_start = now - datetime.timedelta(days=current_offset)
            duration = random.choice([60, 90, 120, 180, 240, 360])
            event_end = event_start + datetime.timedelta(minutes=duration)

            is_failure = random.random() < fail_prob
            is_recurrence = False

            if is_failure:
                if had_failure:
                    # Meaningfully higher recurrence probability if it's a repeated recent failure
                    is_recurrence = random.random() < min(0.4 + (consecutive_failures * 0.15), 0.9)
                ev_type = random.choices(["CORRECTIVE", "EMERGENCY"], [70, 30])[0]
                had_failure = True
                consecutive_failures += 1
            else:
                ev_type = random.choices(["PREVENTIVE", "INSPECTION"], [60, 40])[0]
                # Slowly decay failure state
                if random.random() < 0.4:
                    had_failure = False
                    consecutive_failures = 0

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
                created_at=event_start,
                updated_at=event_end
            )
            records.append(record)

    print(f"Generated {len(records)} synthetic historical records.")
    db.add_all(records)
    db.commit()
    print("Committed successfully.")

if __name__ == "__main__":
    generate_synthetic_history()
