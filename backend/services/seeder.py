import datetime
import uuid
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session

from backend.db.models import (
    Corridor,
    Section,
    Station as StationModel,
    Asset,
    Train,
    TrainRun,
    TrainMovement,
    FreightForecast,
    MaintenanceRequest,
    MaintenanceHistory,
    MLPrediction,
    PriorityDecision,
)
from backend.services.real_corridor import (
    CORRIDOR_CONFIGS,
    get_corridor_stations,
    get_real_timetables,
    CORRIDOR_STATIONS,
)
from backend.services.mock_data import generate_mock_tasks, generate_mock_goods_forecasts
from backend.services.ai_prioritizer import calculate_and_persist_priority
from backend.services.ml_engine import predict_maintenance_recurrence

# Department mapping
ACTIVITY_TO_DEPT_NORM = {
    "Track Tamping": "ENGINEERING",
    "Rail Fracture Repair": "ENGINEERING",
    "Routine Inspection": "ENGINEERING",
    "Point Overhaul": "S&T",
    "Signal Failure": "S&T",
    "OHE Maintenance": "TRACTION",
    "Insulator Flashover": "TRACTION",
}

# ---------------------------------------------------------------------------
# Corridor Section & Asset Metadata Definitions
# ---------------------------------------------------------------------------

CORRIDOR_METADATA = {
    "SBC-JTJ": {
        "name": "Bengaluru City (SBC) to Jolarpettai (JTJ)",
        "description": "Double-line electrified trunk corridor connecting SWR and SR zones (145.0 km)",
        "total_length_km": 145.0,
        "sections": [
            {"id": "SEC-SBC-WFD", "code": "SBC-WFD", "name": "Bengaluru City - Whitefield", "start": 0.0, "end": 23.3, "dir": "BOTH"},
            {"id": "SEC-WFD-BWT", "code": "WFD-BWT", "name": "Whitefield - Bangarapet", "start": 23.3, "end": 70.4, "dir": "BOTH"},
            {"id": "SEC-BWT-KPN", "code": "BWT-KPN", "name": "Bangarapet - Kuppam", "start": 70.4, "end": 104.6, "dir": "BOTH"},
            {"id": "SEC-KPN-JTJ", "code": "KPN-JTJ", "name": "Kuppam - Jolarpettai", "start": 104.6, "end": 145.0, "dir": "BOTH"},
        ],
        "assets": [
            {"id": "AST-TRK-01", "code": "TRK-UP-SBC-KJM", "type": "TRACK", "dept": "ENGINEERING", "sec": "SEC-SBC-WFD", "stn": None, "start": 0.0, "end": 13.5, "age": 4.5, "crit": 4},
            {"id": "AST-TRK-02", "code": "TRK-DN-SBC-KJM", "type": "TRACK", "dept": "ENGINEERING", "sec": "SEC-SBC-WFD", "stn": None, "start": 0.0, "end": 13.5, "age": 4.5, "crit": 4},
            {"id": "AST-TRK-03", "code": "TRK-UP-WFD-MLUR", "type": "TRACK", "dept": "ENGINEERING", "sec": "SEC-WFD-BWT", "stn": None, "start": 23.3, "end": 43.5, "age": 8.0, "crit": 3},
            {"id": "AST-TRK-04", "code": "TRK-DN-WFD-MLUR", "type": "TRACK", "dept": "ENGINEERING", "sec": "SEC-WFD-BWT", "stn": None, "start": 23.3, "end": 43.5, "age": 9.0, "crit": 3},
            {"id": "AST-TRK-05", "code": "TRK-UP-BWT-KPN", "type": "TRACK", "dept": "ENGINEERING", "sec": "SEC-BWT-KPN", "stn": None, "start": 70.4, "end": 104.6, "age": 16.0, "crit": 5},
            {"id": "AST-TRK-06", "code": "TRK-DN-BWT-KPN", "type": "TRACK", "dept": "ENGINEERING", "sec": "SEC-BWT-KPN", "stn": None, "start": 70.4, "end": 104.6, "age": 15.5, "crit": 5},
            {"id": "AST-TRK-07", "code": "TRK-UP-KPN-JTJ", "type": "TRACK", "dept": "ENGINEERING", "sec": "SEC-KPN-JTJ", "stn": None, "start": 104.6, "end": 145.0, "age": 7.0, "crit": 4},
            {"id": "AST-TRK-08", "code": "TRK-DN-KPN-JTJ", "type": "TRACK", "dept": "ENGINEERING", "sec": "SEC-KPN-JTJ", "stn": None, "start": 104.6, "end": 145.0, "age": 7.5, "crit": 4},
            {"id": "AST-BRG-01", "code": "BRG-PALAR-KM52", "type": "BRIDGE", "dept": "ENGINEERING", "sec": "SEC-WFD-BWT", "stn": None, "start": 52.0, "end": 52.8, "age": 22.0, "crit": 5},
            {"id": "AST-PNT-SBC", "code": "PNT-SBC-101", "type": "POINT", "dept": "S&T", "sec": "SEC-SBC-WFD", "stn": "SBC", "start": 0.0, "end": 0.5, "age": 5.0, "crit": 5},
            {"id": "AST-PNT-KJM", "code": "PNT-KJM-204", "type": "POINT", "dept": "S&T", "sec": "SEC-SBC-WFD", "stn": "KJM", "start": 13.5, "end": 14.0, "age": 6.5, "crit": 4},
            {"id": "AST-PNT-WFD", "code": "PNT-WFD-302", "type": "POINT", "dept": "S&T", "sec": "SEC-SBC-WFD", "stn": "WFD", "start": 23.0, "end": 23.6, "age": 4.0, "crit": 4},
            {"id": "AST-PNT-BWT", "code": "PNT-BWT-401", "type": "POINT", "dept": "S&T", "sec": "SEC-WFD-BWT", "stn": "BWT", "start": 70.0, "end": 70.8, "age": 10.0, "crit": 5},
            {"id": "AST-PNT-KPN", "code": "PNT-KPN-503", "type": "POINT", "dept": "S&T", "sec": "SEC-BWT-KPN", "stn": "KPN", "start": 104.2, "end": 105.0, "age": 8.0, "crit": 4},
            {"id": "AST-PNT-JTJ", "code": "PNT-JTJ-601", "type": "POINT", "dept": "S&T", "sec": "SEC-KPN-JTJ", "stn": "JTJ", "start": 144.5, "end": 145.0, "age": 12.0, "crit": 5},
            {"id": "AST-SIG-KJM", "code": "SIG-KJM-AUTO-12", "type": "SIGNAL", "dept": "S&T", "sec": "SEC-SBC-WFD", "stn": "KJM", "start": 13.2, "end": 13.7, "age": 3.0, "crit": 4},
            {"id": "AST-SIG-BWT", "code": "SIG-BWT-HOME-04", "type": "SIGNAL", "dept": "S&T", "sec": "SEC-WFD-BWT", "stn": "BWT", "start": 69.8, "end": 70.4, "age": 7.0, "crit": 5},
            {"id": "AST-OHE-01", "code": "OHE-SBC-WFD", "type": "OHE", "dept": "TRACTION", "sec": "SEC-SBC-WFD", "stn": None, "start": 0.0, "end": 23.3, "age": 14.0, "crit": 4},
            {"id": "AST-OHE-02", "code": "OHE-WFD-BWT", "type": "OHE", "dept": "TRACTION", "sec": "SEC-WFD-BWT", "stn": None, "start": 23.3, "end": 70.4, "age": 16.0, "crit": 4},
            {"id": "AST-OHE-03", "code": "OHE-BWT-KPN", "type": "OHE", "dept": "TRACTION", "sec": "SEC-BWT-KPN", "stn": None, "start": 70.4, "end": 104.6, "age": 18.0, "crit": 5},
            {"id": "AST-OHE-04", "code": "OHE-KPN-JTJ", "type": "OHE", "dept": "TRACTION", "sec": "SEC-KPN-JTJ", "stn": None, "start": 104.6, "end": 145.0, "age": 11.0, "crit": 4},
        ],
        "histories": [
            {"asset_id": "AST-TRK-03", "event": "CORRECTIVE", "failure": "Rail Surface Fatigue", "dur": 180, "success": True, "rec": False, "days_ago": 120, "team": "BWT Track Gang"},
            {"asset_id": "AST-TRK-05", "event": "EMERGENCY", "failure": "Weld Fracture", "dur": 240, "success": True, "rec": True, "days_ago": 45, "team": "KPN Flying Squad"},
            {"asset_id": "AST-TRK-05", "event": "CORRECTIVE", "failure": "Rail Fracture Repair", "dur": 210, "success": True, "rec": True, "days_ago": 15, "team": "KPN Flying Squad"},
            {"asset_id": "AST-PNT-BWT", "event": "CORRECTIVE", "failure": "Point Machine Motor Jam", "dur": 90, "success": True, "rec": True, "days_ago": 60, "team": "BWT Signal Unit"},
            {"asset_id": "AST-PNT-BWT", "event": "PREVENTIVE", "failure": "Routine Overhaul", "dur": 120, "success": True, "rec": False, "days_ago": 180, "team": "S&T Division"},
            {"asset_id": "AST-OHE-03", "event": "EMERGENCY", "failure": "Insulator Flashover", "dur": 150, "success": True, "rec": True, "days_ago": 30, "team": "Traction Emergency"},
            {"asset_id": "AST-OHE-03", "event": "PREVENTIVE", "failure": "OHE Periodic Inspection", "dur": 90, "success": True, "rec": False, "days_ago": 90, "team": "OHE Gang 4"},
            {"asset_id": "AST-PNT-SBC", "event": "PREVENTIVE", "failure": "Point Testing", "dur": 60, "success": True, "rec": False, "days_ago": 40, "team": "SBC Signal Staff"},
            {"asset_id": "AST-TRK-01", "event": "PREVENTIVE", "failure": "Tamping Cycle", "dur": 180, "success": True, "rec": False, "days_ago": 150, "team": "CSMT Tamper 09"},
        ],
    },
    "NDLS-CNB": {
        "name": "New Delhi (NDLS) to Kanpur Central (CNB)",
        "description": "Electrified quadruple/double-line trunk corridor of Northern & North Central Railway (440.0 km)",
        "total_length_km": 440.0,
        "sections": [
            {"id": "SEC-NDLS-GZB", "code": "NDLS-GZB", "name": "New Delhi - Ghaziabad", "start": 0.0, "end": 21.0, "dir": "BOTH"},
            {"id": "SEC-GZB-ALJN", "code": "GZB-ALJN", "name": "Ghaziabad - Aligarh", "start": 21.0, "end": 128.4, "dir": "BOTH"},
            {"id": "SEC-ALJN-TDL", "code": "ALJN-TDL", "name": "Aligarh - Tundla", "start": 128.4, "end": 207.3, "dir": "BOTH"},
            {"id": "SEC-TDL-ETW", "code": "TDL-ETW", "name": "Tundla - Etawah", "start": 207.3, "end": 300.2, "dir": "BOTH"},
            {"id": "SEC-ETW-CNB", "code": "ETW-CNB", "name": "Etawah - Kanpur Central", "start": 300.2, "end": 440.0, "dir": "BOTH"},
        ],
        "assets": [
            {"id": "AST-NDLS-TRK-01", "code": "TRK-UP-NDLS-GZB", "type": "TRACK", "dept": "ENGINEERING", "sec": "SEC-NDLS-GZB", "stn": None, "start": 0.0, "end": 21.0, "age": 3.5, "crit": 5},
            {"id": "AST-NDLS-TRK-02", "code": "TRK-DN-NDLS-GZB", "type": "TRACK", "dept": "ENGINEERING", "sec": "SEC-NDLS-GZB", "stn": None, "start": 0.0, "end": 21.0, "age": 4.0, "crit": 5},
            {"id": "AST-NDLS-TRK-03", "code": "TRK-UP-GZB-ALJN", "type": "TRACK", "dept": "ENGINEERING", "sec": "SEC-GZB-ALJN", "stn": None, "start": 21.0, "end": 128.4, "age": 6.0, "crit": 4},
            {"id": "AST-NDLS-TRK-04", "code": "TRK-DN-GZB-ALJN", "type": "TRACK", "dept": "ENGINEERING", "sec": "SEC-GZB-ALJN", "stn": None, "start": 21.0, "end": 128.4, "age": 6.5, "crit": 4},
            {"id": "AST-NDLS-TRK-05", "code": "TRK-UP-ALJN-TDL", "type": "TRACK", "dept": "ENGINEERING", "sec": "SEC-ALJN-TDL", "stn": None, "start": 128.4, "end": 207.3, "age": 12.0, "crit": 5},
            {"id": "AST-NDLS-TRK-06", "code": "TRK-DN-ALJN-TDL", "type": "TRACK", "dept": "ENGINEERING", "sec": "SEC-ALJN-TDL", "stn": None, "start": 128.4, "end": 207.3, "age": 11.5, "crit": 5},
            {"id": "AST-NDLS-TRK-07", "code": "TRK-UP-TDL-CNB", "type": "TRACK", "dept": "ENGINEERING", "sec": "SEC-TDL-ETW", "stn": None, "start": 207.3, "end": 300.2, "age": 8.0, "crit": 4},
            {"id": "AST-NDLS-TRK-08", "code": "TRK-DN-TDL-CNB", "type": "TRACK", "dept": "ENGINEERING", "sec": "SEC-ETW-CNB", "stn": None, "start": 300.2, "end": 440.0, "age": 8.5, "crit": 4},
            {"id": "AST-NDLS-BRG-01", "code": "BRG-YAMUNA-KM18", "type": "BRIDGE", "dept": "ENGINEERING", "sec": "SEC-NDLS-GZB", "stn": None, "start": 18.0, "end": 19.2, "age": 28.0, "crit": 5},
            {"id": "AST-NDLS-PNT-NDLS", "code": "PNT-NDLS-101", "type": "POINT", "dept": "S&T", "sec": "SEC-NDLS-GZB", "stn": "NDLS", "start": 0.0, "end": 0.5, "age": 4.0, "crit": 5},
            {"id": "AST-NDLS-PNT-GZB", "code": "PNT-GZB-202", "type": "POINT", "dept": "S&T", "sec": "SEC-NDLS-GZB", "stn": "GZB", "start": 20.5, "end": 21.0, "age": 5.0, "crit": 5},
            {"id": "AST-NDLS-PNT-ALJN", "code": "PNT-ALJN-301", "type": "POINT", "dept": "S&T", "sec": "SEC-GZB-ALJN", "stn": "ALJN", "start": 127.8, "end": 128.4, "age": 9.0, "crit": 4},
            {"id": "AST-NDLS-PNT-TDL", "code": "PNT-TDL-401", "type": "POINT", "dept": "S&T", "sec": "SEC-ALJN-TDL", "stn": "TDL", "start": 206.8, "end": 207.3, "age": 14.0, "crit": 5},
            {"id": "AST-NDLS-PNT-ETW", "code": "PNT-ETW-501", "type": "POINT", "dept": "S&T", "sec": "SEC-TDL-ETW", "stn": "ETW", "start": 299.7, "end": 300.2, "age": 7.0, "crit": 4},
            {"id": "AST-NDLS-PNT-CNB", "code": "PNT-CNB-601", "type": "POINT", "dept": "S&T", "sec": "SEC-ETW-CNB", "stn": "CNB", "start": 439.5, "end": 440.0, "age": 10.0, "crit": 5},
            {"id": "AST-NDLS-SIG-GZB", "code": "SIG-GZB-AUTO-01", "type": "SIGNAL", "dept": "S&T", "sec": "SEC-NDLS-GZB", "stn": "GZB", "start": 20.8, "end": 21.2, "age": 3.0, "crit": 5},
            {"id": "AST-NDLS-SIG-TDL", "code": "SIG-TDL-HOME-02", "type": "SIGNAL", "dept": "S&T", "sec": "SEC-ALJN-TDL", "stn": "TDL", "start": 206.9, "end": 207.3, "age": 6.0, "crit": 4},
            {"id": "AST-NDLS-OHE-01", "code": "OHE-NDLS-GZB", "type": "OHE", "dept": "TRACTION", "sec": "SEC-NDLS-GZB", "stn": None, "start": 0.0, "end": 21.0, "age": 12.0, "crit": 5},
            {"id": "AST-NDLS-OHE-02", "code": "OHE-GZB-ALJN", "type": "OHE", "dept": "TRACTION", "sec": "SEC-GZB-ALJN", "stn": None, "start": 21.0, "end": 128.4, "age": 15.0, "crit": 4},
            {"id": "AST-NDLS-OHE-03", "code": "OHE-ALJN-TDL", "type": "OHE", "dept": "TRACTION", "sec": "SEC-ALJN-TDL", "stn": None, "start": 128.4, "end": 207.3, "age": 18.0, "crit": 5},
            {"id": "AST-NDLS-OHE-04", "code": "OHE-TDL-ETW", "type": "OHE", "dept": "TRACTION", "sec": "SEC-TDL-ETW", "stn": None, "start": 207.3, "end": 300.2, "age": 9.0, "crit": 4},
            {"id": "AST-NDLS-OHE-05", "code": "OHE-ETW-CNB", "type": "OHE", "dept": "TRACTION", "sec": "SEC-ETW-CNB", "stn": None, "start": 300.2, "end": 440.0, "age": 11.0, "crit": 4},
        ],
        "histories": [
            {"asset_id": "AST-NDLS-TRK-05", "event": "CORRECTIVE", "failure": "Rail Surface Fatigue", "dur": 180, "success": True, "rec": False, "days_ago": 110, "team": "ALJN Track Gang"},
            {"asset_id": "AST-NDLS-TRK-06", "event": "EMERGENCY", "failure": "Weld Fracture", "dur": 240, "success": True, "rec": True, "days_ago": 35, "team": "TDL Flying Squad"},
            {"asset_id": "AST-NDLS-PNT-TDL", "event": "CORRECTIVE", "failure": "Point Machine Motor Jam", "dur": 90, "success": True, "rec": True, "days_ago": 50, "team": "TDL Signal Unit"},
            {"asset_id": "AST-NDLS-PNT-CNB", "event": "PREVENTIVE", "failure": "Routine Overhaul", "dur": 120, "success": True, "rec": False, "days_ago": 140, "team": "CNB S&T Division"},
            {"asset_id": "AST-NDLS-OHE-03", "event": "EMERGENCY", "failure": "Insulator Flashover", "dur": 150, "success": True, "rec": True, "days_ago": 25, "team": "NCR Traction Emergency"},
            {"asset_id": "AST-NDLS-OHE-01", "event": "PREVENTIVE", "failure": "OHE Periodic Inspection", "dur": 90, "success": True, "rec": False, "days_ago": 80, "team": "GZB OHE Gang 2"},
            {"asset_id": "AST-NDLS-PNT-NDLS", "event": "PREVENTIVE", "failure": "Point Testing", "dur": 60, "success": True, "rec": False, "days_ago": 30, "team": "NDLS Signal Staff"},
            {"asset_id": "AST-NDLS-TRK-01", "event": "PREVENTIVE", "failure": "Tamping Cycle", "dur": 180, "success": True, "rec": False, "days_ago": 120, "team": "GZB Tamper 04"},
        ],
    },
    "CSTM-PUNE": {
        "name": "Mumbai CST (CSTM) to Pune Jn (PUNE)",
        "description": "Central Railway electrified main trunk corridor via Bhor Ghat (192.0 km)",
        "total_length_km": 192.0,
        "sections": [
            {"id": "SEC-CSTM-KYN", "code": "CSTM-KYN", "name": "Mumbai CST - Kalyan", "start": 0.0, "end": 53.2, "dir": "BOTH"},
            {"id": "SEC-KYN-KJT", "code": "KYN-KJT", "name": "Kalyan - Karjat", "start": 53.2, "end": 102.4, "dir": "BOTH"},
            {"id": "SEC-KJT-LNL", "code": "KJT-LNL", "name": "Karjat - Lonavala (Bhor Ghat)", "start": 102.4, "end": 126.6, "dir": "BOTH"},
            {"id": "SEC-LNL-PUNE", "code": "LNL-PUNE", "name": "Lonavala - Pune Jn", "start": 126.6, "end": 192.0, "dir": "BOTH"},
        ],
        "assets": [
            {"id": "AST-CSTM-TRK-01", "code": "TRK-UP-CSTM-KYN", "type": "TRACK", "dept": "ENGINEERING", "sec": "SEC-CSTM-KYN", "stn": None, "start": 0.0, "end": 53.2, "age": 5.0, "crit": 5},
            {"id": "AST-CSTM-TRK-02", "code": "TRK-DN-CSTM-KYN", "type": "TRACK", "dept": "ENGINEERING", "sec": "SEC-CSTM-KYN", "stn": None, "start": 0.0, "end": 53.2, "age": 5.5, "crit": 5},
            {"id": "AST-CSTM-TRK-03", "code": "TRK-UP-KYN-KJT", "type": "TRACK", "dept": "ENGINEERING", "sec": "SEC-KYN-KJT", "stn": None, "start": 53.2, "end": 102.4, "age": 7.0, "crit": 4},
            {"id": "AST-CSTM-TRK-04", "code": "TRK-DN-KYN-KJT", "type": "TRACK", "dept": "ENGINEERING", "sec": "SEC-KYN-KJT", "stn": None, "start": 53.2, "end": 102.4, "age": 7.5, "crit": 4},
            {"id": "AST-CSTM-TRK-05", "code": "TRK-UP-KJT-LNL", "type": "TRACK", "dept": "ENGINEERING", "sec": "SEC-KJT-LNL", "stn": None, "start": 102.4, "end": 126.6, "age": 14.0, "crit": 5},
            {"id": "AST-CSTM-TRK-06", "code": "TRK-DN-KJT-LNL", "type": "TRACK", "dept": "ENGINEERING", "sec": "SEC-KJT-LNL", "stn": None, "start": 102.4, "end": 126.6, "age": 15.0, "crit": 5},
            {"id": "AST-CSTM-TRK-07", "code": "TRK-UP-LNL-PUNE", "type": "TRACK", "dept": "ENGINEERING", "sec": "SEC-LNL-PUNE", "stn": None, "start": 126.6, "end": 192.0, "age": 6.0, "crit": 4},
            {"id": "AST-CSTM-TRK-08", "code": "TRK-DN-LNL-PUNE", "type": "TRACK", "dept": "ENGINEERING", "sec": "SEC-LNL-PUNE", "stn": None, "start": 126.6, "end": 192.0, "age": 6.5, "crit": 4},
            {"id": "AST-CSTM-BRG-01", "code": "BRG-ULHAS-KM62", "type": "BRIDGE", "dept": "ENGINEERING", "sec": "SEC-KYN-KJT", "stn": None, "start": 62.0, "end": 62.6, "age": 30.0, "crit": 5},
            {"id": "AST-CSTM-PNT-CSTM", "code": "PNT-CSTM-101", "type": "POINT", "dept": "S&T", "sec": "SEC-CSTM-KYN", "stn": "CSTM", "start": 0.0, "end": 0.5, "age": 4.5, "crit": 5},
            {"id": "AST-CSTM-PNT-KYN", "code": "PNT-KYN-201", "type": "POINT", "dept": "S&T", "sec": "SEC-CSTM-KYN", "stn": "KYN", "start": 52.8, "end": 53.2, "age": 6.0, "crit": 5},
            {"id": "AST-CSTM-PNT-KJT", "code": "PNT-KJT-301", "type": "POINT", "dept": "S&T", "sec": "SEC-KYN-KJT", "stn": "KJT", "start": 101.9, "end": 102.4, "age": 8.0, "crit": 5},
            {"id": "AST-CSTM-PNT-LNL", "code": "PNT-LNL-401", "type": "POINT", "dept": "S&T", "sec": "SEC-KJT-LNL", "stn": "LNL", "start": 126.1, "end": 126.6, "age": 11.0, "crit": 4},
            {"id": "AST-CSTM-PNT-PUNE", "code": "PNT-PUNE-501", "type": "POINT", "dept": "S&T", "sec": "SEC-LNL-PUNE", "stn": "PUNE", "start": 191.5, "end": 192.0, "age": 9.0, "crit": 5},
            {"id": "AST-CSTM-SIG-KYN", "code": "SIG-KYN-AUTO-01", "type": "SIGNAL", "dept": "S&T", "sec": "SEC-CSTM-KYN", "stn": "KYN", "start": 53.0, "end": 53.4, "age": 3.5, "crit": 5},
            {"id": "AST-CSTM-SIG-LNL", "code": "SIG-LNL-HOME-02", "type": "SIGNAL", "dept": "S&T", "sec": "SEC-KJT-LNL", "stn": "LNL", "start": 126.2, "end": 126.6, "age": 5.5, "crit": 4},
            {"id": "AST-CSTM-OHE-01", "code": "OHE-CSTM-KYN", "type": "OHE", "dept": "TRACTION", "sec": "SEC-CSTM-KYN", "stn": None, "start": 0.0, "end": 53.2, "age": 16.0, "crit": 5},
            {"id": "AST-CSTM-OHE-02", "code": "OHE-KYN-KJT", "type": "OHE", "dept": "TRACTION", "sec": "SEC-KYN-KJT", "stn": None, "start": 53.2, "end": 102.4, "age": 18.0, "crit": 4},
            {"id": "AST-CSTM-OHE-03", "code": "OHE-KJT-LNL", "type": "OHE", "dept": "TRACTION", "sec": "SEC-KJT-LNL", "stn": None, "start": 102.4, "end": 126.6, "age": 22.0, "crit": 5},
            {"id": "AST-CSTM-OHE-04", "code": "OHE-LNL-PUNE", "type": "OHE", "dept": "TRACTION", "sec": "SEC-LNL-PUNE", "stn": None, "start": 126.6, "end": 192.0, "age": 12.0, "crit": 4},
        ],
        "histories": [
            {"asset_id": "AST-CSTM-TRK-05", "event": "EMERGENCY", "failure": "Bhor Ghat Track Slip", "dur": 300, "success": True, "rec": True, "days_ago": 40, "team": "KJT Ghat Gang"},
            {"asset_id": "AST-CSTM-TRK-06", "event": "CORRECTIVE", "failure": "Rail Surface Wear", "dur": 180, "success": True, "rec": False, "days_ago": 100, "team": "LNL Track Unit"},
            {"asset_id": "AST-CSTM-PNT-KJT", "event": "CORRECTIVE", "failure": "Catch Siding Point Jam", "dur": 90, "success": True, "rec": True, "days_ago": 55, "team": "KJT Signal Team"},
            {"asset_id": "AST-CSTM-PNT-KYN", "event": "PREVENTIVE", "failure": "Routine Overhaul", "dur": 120, "success": True, "rec": False, "days_ago": 160, "team": "KYN S&T Crew"},
            {"asset_id": "AST-CSTM-OHE-03", "event": "EMERGENCY", "failure": "Ghat OHE Wire Snap", "dur": 180, "success": True, "rec": True, "days_ago": 20, "team": "Ghat Traction Flying Squad"},
            {"asset_id": "AST-CSTM-OHE-01", "event": "PREVENTIVE", "failure": "Suburban OHE Check", "dur": 90, "success": True, "rec": False, "days_ago": 70, "team": "CSTM Traction Gang"},
            {"asset_id": "AST-CSTM-PNT-CSTM", "event": "PREVENTIVE", "failure": "Terminal Point Testing", "dur": 60, "success": True, "rec": False, "days_ago": 30, "team": "CSTM S&T"},
            {"asset_id": "AST-CSTM-TRK-01", "event": "PREVENTIVE", "failure": "Tamping Cycle", "dur": 180, "success": True, "rec": False, "days_ago": 130, "team": "KYN Tamper 02"},
        ],
    },
}

def seed_corridor(db: Session, corridor_id: str, force_clean: bool = False) -> Dict[str, Any]:
    """
    Seeds a specific corridor's infrastructure, trains, forecasts, assets, and tasks.
    If the corridor already exists and not force_clean, leaves it untouched.
    """
    if corridor_id not in CORRIDOR_METADATA:
        raise ValueError(f"Unknown corridor_id: {corridor_id}")

    meta = CORRIDOR_METADATA[corridor_id]
    cfg = CORRIDOR_CONFIGS.get(corridor_id, CORRIDOR_CONFIGS["SBC-JTJ"])
    stats = {}

    existing = db.query(Corridor).filter_by(id=corridor_id).first()
    if existing and not force_clean:
        return {"status": "already_seeded", "corridor_id": corridor_id}

    if existing and force_clean:
        # Delete only this corridor's records in cascade order
        # Assets & history
        asset_ids = [a.id for a in db.query(Asset).filter_by(corridor_id=corridor_id).all()]
        db.query(MaintenanceHistory).filter(MaintenanceHistory.asset_id.in_(asset_ids)).delete(synchronize_session=False)
        
        # Requests, predictions, decisions
        req_ids = [r.id for r in db.query(MaintenanceRequest).filter_by(corridor_id=corridor_id).all()]
        db.query(PriorityDecision).filter(PriorityDecision.maintenance_request_id.in_(req_ids)).delete(synchronize_session=False)
        db.query(MLPrediction).filter(MLPrediction.maintenance_request_id.in_(req_ids)).delete(synchronize_session=False)
        db.query(MaintenanceRequest).filter_by(corridor_id=corridor_id).delete(synchronize_session=False)

        # Forecasts
        db.query(FreightForecast).filter_by(corridor_id=corridor_id).delete(synchronize_session=False)

        # Train runs & movements
        run_ids = [r.id for r in db.query(TrainRun).filter_by(corridor_id=corridor_id).all()]
        db.query(TrainMovement).filter(TrainMovement.train_run_id.in_(run_ids)).delete(synchronize_session=False)
        db.query(TrainRun).filter_by(corridor_id=corridor_id).delete(synchronize_session=False)

        # Assets, Stations, Sections, Corridor
        db.query(Asset).filter_by(corridor_id=corridor_id).delete(synchronize_session=False)
        sec_ids = [s.id for s in db.query(Section).filter_by(corridor_id=corridor_id).all()]
        db.query(StationModel).filter(StationModel.section_id.in_(sec_ids)).delete(synchronize_session=False)
        db.query(Section).filter_by(corridor_id=corridor_id).delete(synchronize_session=False)
        db.query(Corridor).filter_by(id=corridor_id).delete(synchronize_session=False)
        db.flush()

    # 1. Corridor
    corridor = Corridor(
        id=corridor_id,
        code=corridor_id,
        name=meta["name"],
        description=meta["description"],
        total_length_km=meta["total_length_km"],
        active=True,
    )
    db.add(corridor)
    db.flush()
    stats["corridor"] = 1

    # 2. Sections
    sections_data = meta["sections"]
    section_objects = {}
    for s in sections_data:
        sec_obj = Section(
            id=s["id"],
            corridor_id=corridor.id,
            code=s["code"],
            name=s["name"],
            start_chainage=s["start"],
            end_chainage=s["end"],
            direction=s["dir"],
        )
        db.add(sec_obj)
        section_objects[s["id"]] = sec_obj
    db.flush()
    stats["sections"] = len(sections_data)

    def get_section_for_chainage(km: float) -> str:
        for s in sections_data:
            if s["start"] <= km <= s["end"]:
                return s["id"]
        return sections_data[-1]["id"]

    # 3. Stations (from Datameet)
    stations = get_corridor_stations(corridor_id)
    station_objects = {}
    for stn in stations:
        sec_id = get_section_for_chainage(stn.chainage_km)
        stn_obj = StationModel(
            id=stn.code,
            section_id=sec_id,
            code=stn.code,
            name=stn.name,
            chainage_km=stn.chainage_km,
            latitude=stn.latitude,
            longitude=stn.longitude,
        )
        db.add(stn_obj)
        station_objects[stn.code] = stn_obj
    db.flush()
    stats["stations"] = len(stations)

    # 4. Assets
    assets_data = meta["assets"]
    asset_objects = {}
    for a in assets_data:
        asset_obj = Asset(
            id=a["id"],
            asset_code=a["code"],
            asset_type=a["type"],
            department=a["dept"],
            corridor_id=corridor.id,
            section_id=a["sec"],
            station_id=a["stn"],
            start_chainage=a["start"],
            end_chainage=a["end"],
            installation_date=datetime.date.today() - datetime.timedelta(days=int(a["age"] * 365)),
            age_years=a["age"],
            criticality=a["crit"],
            status="OPERATIONAL",
            metadata_json={"source": "SYNTHETIC_ASSET_REGISTRY", "corridor": corridor_id},
        )
        db.add(asset_obj)
        asset_objects[a["id"]] = asset_obj
    db.flush()
    stats["assets"] = len(assets_data)

    # 5. Maintenance History
    histories_data = meta["histories"]
    for h in histories_data:
        started = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=h["days_ago"], hours=4)
        completed = started + datetime.timedelta(minutes=h["dur"])
        hist_obj = MaintenanceHistory(
            id=f"HIST-{uuid.uuid4().hex[:8].upper()}",
            asset_id=h["asset_id"],
            event_type=h["event"],
            failure_type=h["failure"],
            started_at=started,
            completed_at=completed,
            duration_minutes=h["dur"],
            success=h["success"],
            failure=not h["success"],
            recurrence=h["rec"],
            team=h["team"],
            notes=f"Historical record logged {h['days_ago']} days ago on {corridor_id}.",
        )
        db.add(hist_obj)
    db.flush()
    stats["maintenance_history"] = len(histories_data)

    # 6. Trains & Timetables
    raw_schedules = get_real_timetables(corridor_id)
    train_catalog = {}
    train_movements_count = 0

    for sched in raw_schedules:
        base_train_number = sched.train_id.split("_")[0]
        if base_train_number not in train_catalog:
            existing_train = db.query(Train).filter_by(id=base_train_number).first()
            if not existing_train:
                train_obj = Train(
                    id=base_train_number,
                    train_number=base_train_number,
                    name=f"{sched.type} {base_train_number}",
                    category=sched.type.upper().replace(" ", "_"),
                    operator=cfg.get("operator", "Indian Railways"),
                    source_type="REAL",
                )
                db.add(train_obj)
                train_catalog[base_train_number] = train_obj
            else:
                train_catalog[base_train_number] = existing_train
    db.flush()
    stats["trains"] = len(train_catalog)

    for sched in raw_schedules:
        base_train_number = sched.train_id.split("_")[0]
        day_str = sched.train_id.split("_D")[-1] if "_D" in sched.train_id else "0"
        try:
            day_offset = int(day_str)
        except ValueError:
            day_offset = 0

        # Unique run_id per corridor
        run_id = f"{corridor_id}_{sched.train_id}" if corridor_id != "SBC-JTJ" else sched.train_id
        train_run = TrainRun(
            id=run_id,
            train_id=base_train_number,
            corridor_id=corridor.id,
            direction=sched.direction,
            service_date=datetime.date.today() + datetime.timedelta(days=day_offset),
            day_offset=day_offset,
        )
        db.add(train_run)
        db.flush()

        for stop in sched.stops:
            stn_code = stop.station_id
            stn_info = next((s for s in stations if s.code == stn_code), None)
            chainage = stn_info.chainage_km if stn_info else 0.0

            mv = TrainMovement(
                id=f"TM-{uuid.uuid4().hex[:8].upper()}",
                train_run_id=train_run.id,
                station_code=stn_code,
                chainage_km=chainage,
                arrival_mins=stop.arrival_mins,
                departure_mins=stop.departure_mins,
            )
            db.add(mv)
            train_movements_count += 1

    db.flush()
    stats["train_runs"] = len(raw_schedules)
    stats["train_movements"] = train_movements_count

    # 7. Freight Forecasts
    mock_forecasts = generate_mock_goods_forecasts(corridor_id, meta["total_length_km"])
    for f in mock_forecasts:
        ff_obj = FreightForecast(
            id=f.forecast_id,
            corridor_id=corridor.id,
            direction=f.direction,
            start_chainage=f.start_km,
            end_chainage=f.end_km,
            earliest_entry_mins=f.earliest_entry_mins,
            latest_exit_mins=f.latest_exit_mins,
            confidence=f.confidence,
            source_type="SYNTHETIC",
        )
        db.add(ff_obj)
    db.flush()
    stats["freight_forecasts"] = len(mock_forecasts)

    # 8. Maintenance Requests + ML Predictions + Explainable Priorities
    mock_tasks = generate_mock_tasks(corridor_id, stations=stations, total_km=meta["total_length_km"])

    def find_matching_asset(task_type: str, start_km: float, end_km: float) -> str:
        dept = ACTIVITY_TO_DEPT_NORM.get(task_type, "ENGINEERING")
        for a in assets_data:
            if a["dept"] == dept and not (a["end"] < start_km or a["start"] > end_km):
                return a["id"]
        return assets_data[0]["id"]

    for t in mock_tasks:
        dept_norm = ACTIVITY_TO_DEPT_NORM.get(t.task_type, "ENGINEERING")
        sec_id = get_section_for_chainage(t.start_km)
        asset_id = find_matching_asset(t.task_type, t.start_km, t.end_km)

        m_req = MaintenanceRequest(
            id=t.id,
            asset_id=asset_id,
            corridor_id=corridor.id,
            section_id=sec_id,
            department=dept_norm,
            request_type=t.origin,
            defect_type=t.task_type,
            description=f"{t.origin} for {t.task_type} between Km {t.start_km:.1f} and {t.end_km:.1f} ({corridor_id})",
            status="PRIORITIZED",
            severity=t.severity,
            criticality=t.asset_criticality,
            start_chainage=t.start_km,
            end_chainage=t.end_km,
            line_direction=t.line_direction,
            estimated_duration_minutes=t.duration_mins,
            deadline_mins=t.deadline_mins,
            overdue_days=t.overdue_days,
            required_resource=t.required_resource,
            source_type="SYNTHETIC",
        )
        db.add(m_req)
        db.flush()

        ml_pred = predict_maintenance_recurrence(db, m_req)
        calculate_and_persist_priority(db, m_req, current_time_mins=0, ml_pred=ml_pred)

    db.commit()
    stats["maintenance_requests"] = len(mock_tasks)
    stats["ml_predictions"] = len(mock_tasks)
    stats["priority_decisions"] = len(mock_tasks)
    stats["status"] = "success"
    return stats

def seed_database(db: Session, corridor_id: Optional[str] = "SBC-JTJ", force_clean: bool = False) -> Dict[str, Any]:
    """
    Seeds the database.
    - If corridor_id is specified (default: 'SBC-JTJ'), seeds only that corridor.
    - If corridor_id is None, seeds all three corridors (SBC-JTJ, NDLS-CNB, CSTM-PUNE).
    Existing corridors are preserved untouched unless force_clean=True.
    """
    if corridor_id:
        return seed_corridor(db, corridor_id, force_clean=force_clean)

    overall_stats = {}
    for c_id in ["SBC-JTJ", "NDLS-CNB", "CSTM-PUNE"]:
        overall_stats[c_id] = seed_corridor(db, c_id, force_clean=force_clean)
    return overall_stats

def seed_all_corridors(db: Session, force_clean: bool = False) -> Dict[str, Any]:
    """Ensures all three corridors are seeded in the database."""
    return seed_database(db, corridor_id=None, force_clean=force_clean)
