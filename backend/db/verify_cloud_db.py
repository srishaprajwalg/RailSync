import os
import sys
import re
import time
from typing import Dict, Any, List
from sqlalchemy import text, inspect

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from backend.db.session import engine, DATABASE_URL, SessionLocal, mask_connection_url, get_sanitized_connection_info
    from backend.db.models import Base
except ImportError:
    from db.session import engine, DATABASE_URL, SessionLocal, mask_connection_url, get_sanitized_connection_info
    from db.models import Base

def verify_database_connection() -> Dict[str, Any]:
    """
    Comprehensive verification for Cloud PostgreSQL + PostGIS database.
    Checks connectivity, PostgreSQL version, PostGIS extension, 17 tables,
    foreign keys, indexes, table row counts, and Alembic migration state.
    """
    report = {
        "status": "FAILED",
        "url_masked": mask_connection_url(DATABASE_URL),
        "db_type": "Unknown",
        "pg_version": "N/A",
        "postgis_available": False,
        "postgis_version": "N/A",
        "tables_expected": 17,
        "tables_found": 0,
        "existing_tables": [],
        "missing_tables": [],
        "foreign_keys_count": 0,
        "foreign_keys_summary": {},
        "indexes_count": 0,
        "table_row_counts": {},
        "alembic_version": "NOT_APPLIED",
        "latency_ms": 0.0,
        "error": None,
    }

    start_time = time.time()
    try:
        with engine.connect() as conn:
            report["latency_ms"] = round((time.time() - start_time) * 1000, 2)
            
            # 1. Determine dialect and version
            dialect_name = conn.dialect.name
            report["db_type"] = dialect_name
            
            if dialect_name == "postgresql":
                ver_res = conn.execute(text("SELECT version()")).scalar()
                report["pg_version"] = ver_res or "PostgreSQL (Unknown version)"
                
                # Check PostGIS extension
                postgis_res = conn.execute(
                    text("SELECT extname, extversion FROM pg_extension WHERE extname = 'postgis'")
                ).fetchone()
                if postgis_res:
                    report["postgis_available"] = True
                    report["postgis_version"] = postgis_res[1]
                else:
                    # Attempt to check if postgis extension is available to install
                    try:
                        avail_res = conn.execute(
                            text("SELECT name, default_version FROM pg_available_extensions WHERE name = 'postgis'")
                        ).fetchone()
                        if avail_res:
                            report["postgis_version"] = f"Available to install (version {avail_res[1]})"
                        else:
                            report["postgis_version"] = "Not installed"
                    except Exception:
                        report["postgis_version"] = "Not installed"
            elif dialect_name == "sqlite":
                report["pg_version"] = "SQLite (Isolated Test Mode)"

            # 2. Inspect tables
            inspector = inspect(conn)
            all_db_tables = set(inspector.get_table_names())
            expected_tables = set(Base.metadata.tables.keys())

            matched_tables = sorted(list(all_db_tables.intersection(expected_tables)))
            report["existing_tables"] = matched_tables
            report["tables_found"] = len(matched_tables)
            report["missing_tables"] = sorted(list(expected_tables - all_db_tables))

            # 3. Inspect Foreign Keys & Indexes
            fk_total = 0
            idx_total = 0
            for tbl in matched_tables:
                fks = inspector.get_foreign_keys(tbl)
                indexes = inspector.get_indexes(tbl)
                fk_total += len(fks)
                idx_total += len(indexes)
                if fks:
                    report["foreign_keys_summary"][tbl] = [
                        f"{fk['constrained_columns']} -> {fk['referred_table']}.{fk['referred_columns']}"
                        for fk in fks
                    ]
            report["foreign_keys_count"] = fk_total
            report["indexes_count"] = idx_total

            # 4. Query table row counts
            for tbl in expected_tables:
                if tbl in all_db_tables:
                    try:
                        count = conn.execute(text(f"SELECT count(*) FROM {tbl}")).scalar()
                        report["table_row_counts"][tbl] = count
                    except Exception:
                        report["table_row_counts"][tbl] = -1

            # 5. Inspect Alembic migration version
            if "alembic_version" in all_db_tables:
                try:
                    ver = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
                    report["alembic_version"] = ver or "EMPTY"
                except Exception:
                    report["alembic_version"] = "ERROR_READING_ALEMBIC_VERSION"
            else:
                report["alembic_version"] = "TABLE_NOT_FOUND (Migrations not yet applied)"

            if len(report["missing_tables"]) == 0:
                report["status"] = "SUCCESS"
            elif len(matched_tables) > 0:
                report["status"] = "PARTIAL"
            else:
                report["status"] = "EMPTY_DATABASE"

    except Exception as e:
        report["status"] = "FAILED"
        report["error"] = mask_connection_url(str(e))

    return report

def print_verification_report(report: Dict[str, Any]):
    """Pretty prints the verification audit report."""
    print("=" * 70)
    print(" RAILVYUHA CLOUD DATABASE VERIFICATION REPORT")
    print("=" * 70)
    print(f"Target Database URL  : {report['url_masked']}")
    print(f"Dialect Type         : {report['db_type'].upper()}")
    print(f"Connection Status    : {report['status']}")
    print(f"Connection Latency   : {report['latency_ms']} ms")
    print(f"Database Engine Ver  : {report['pg_version']}")
    print(f"PostGIS Extension    : {'INSTALLED (v' + str(report['postgis_version']) + ')' if report['postgis_available'] else str(report['postgis_version'])}")
    print(f"Tables Found         : {report['tables_found']} / {report['tables_expected']}")
    print(f"Foreign Keys Count   : {report['foreign_keys_count']}")
    print(f"Indexes Count        : {report['indexes_count']}")
    print(f"Alembic Version      : {report['alembic_version']}")
    
    if report["missing_tables"]:
        print(f"Missing Tables       : {', '.join(report['missing_tables'])}")
        print("  -> Run 'alembic upgrade head' to apply schema migrations.")
    
    print("-" * 70)
    print(" TABLE ROW COUNTS:")
    if report["table_row_counts"]:
        for tbl, count in sorted(report["table_row_counts"].items()):
            print(f"  - {tbl:<25}: {count:>6} rows")
    else:
        print("  (No tables found in target database)")
    
    if report["error"]:
        print("-" * 70)
        print(f" ERROR DETAILS       : {report['error']}")
    print("=" * 70)

if __name__ == "__main__":
    rep = verify_database_connection()
    print_verification_report(rep)
    if rep["status"] == "FAILED":
        sys.exit(1)
