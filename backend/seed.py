import sys
import os
import argparse
from pathlib import Path

# Add project root and backend to python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from backend.db.session import SessionLocal, init_db, get_sanitized_connection_info
from backend.services.seeder import seed_database

def main():
    parser = argparse.ArgumentParser(description="Seed the RailVyuha database with infrastructure, timetables, and maintenance data.")
    parser.add_argument("--force", action="store_true", help="Force clean existing corridor data and re-seed.")
    args = parser.parse_args()

    db_info = get_sanitized_connection_info()
    print(f"Connecting to database: type={db_info['dialect']}, host={db_info['host']}, port={db_info['port']}, db={db_info['database']}, user={db_info['username']}")
    print("Initializing tables if not present...")
    init_db()

    db = SessionLocal()
    try:
        print("Starting seed pipeline...")
        result = seed_database(db, force_clean=args.force)
        print("Seed result:")
        for k, v in result.items():
            print(f"  - {k}: {v}")
        print("Database seed completed successfully.")
    except Exception as e:
        print(f"Error during database seed: {e}", file=sys.stderr)
        db.rollback()
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    main()
