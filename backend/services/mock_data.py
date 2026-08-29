import random
from typing import List, Dict
from core.schemas import Station, TrainSchedule, TrainStop, MaintenanceTask

# Approximate stations and chainages for SBC-JTJ corridor
MOCK_STATIONS = [
    Station(id="SBC", code="SBC", name="KSR Bengaluru", chainage_km=0.0),
    Station(id="BNC", code="BNC", name="Bengaluru Cantt", chainage_km=4.3),
    Station(id="KJM", code="KJM", name="Krishnarajapuram", chainage_km=13.7),
    Station(id="WFD", code="WFD", name="Whitefield", chainage_km=23.3),
    Station(id="BWT", code="BWT", name="Bangarapet", chainage_km=70.4),
    Station(id="KPN", code="KPN", name="Kuppam", chainage_km=104.6),
    Station(id="JTJ", code="JTJ", name="Jolarpettai", chainage_km=145.2)
]

def generate_mock_timetables() -> List[TrainSchedule]:
    """Generates a simplified, approximate timetable for a 24-hour period."""
    schedules = []
    
    # Generate some Up trains (SBC -> JTJ)
    # Average speed ~60 km/h -> ~1 km/min for simplicity
    for i in range(1, 15): # 14 Express trains
        start_time = i * 90 + random.randint(0, 30) # roughly every 1.5 hours
        stops = []
        current_time = start_time
        prev_km = MOCK_STATIONS[0].chainage_km
        
        for station in MOCK_STATIONS:
            travel_time = int(station.chainage_km - prev_km) # 1 km = 1 min approx
            current_time += travel_time
            arrival = current_time
            # 2 min stop at intermediate, 0 at start/end
            departure = current_time + (2 if station.id not in ["SBC", "JTJ"] else 0)
            stops.append(TrainStop(station_id=station.id, arrival_mins=arrival, departure_mins=departure))
            current_time = departure
            prev_km = station.chainage_km
            
        schedules.append(TrainSchedule(
            train_id=f"EXP_UP_{i}",
            type="Express",
            direction="Up",
            stops=stops
        ))

    # Generate some Down trains (JTJ -> SBC)
    for i in range(1, 15):
        start_time = i * 90 + random.randint(30, 60)
        stops = []
        current_time = start_time
        prev_km = MOCK_STATIONS[-1].chainage_km
        
        for station in reversed(MOCK_STATIONS):
            travel_time = int(abs(station.chainage_km - prev_km))
            current_time += travel_time
            arrival = current_time
            departure = current_time + (2 if station.id not in ["SBC", "JTJ"] else 0)
            stops.append(TrainStop(station_id=station.id, arrival_mins=arrival, departure_mins=departure))
            current_time = departure
            prev_km = station.chainage_km
            
        schedules.append(TrainSchedule(
            train_id=f"EXP_DN_{i}",
            type="Express",
            direction="Down",
            stops=stops
        ))
        
    return schedules

def generate_mock_tasks() -> List[MaintenanceTask]:
    """Generates synthetic maintenance tasks."""
    tasks = []
    directions = ["Up", "Down"]
    
    # TMS (Engineering)
    for i in range(5):
        start_km = random.randint(10, 130)
        tasks.append(MaintenanceTask(
            id=f"TMS_{i}",
            department="TMS",
            task_type="Track Tamping",
            start_km=float(start_km),
            end_km=float(start_km + 2),
            duration_mins=120,
            base_priority=random.randint(2, 4),
            deadline_mins=1440, # within the day
            line_direction=random.choice(directions)
        ))
        
    # TDMS (Traction)
    for i in range(4):
        start_km = random.randint(10, 130)
        tasks.append(MaintenanceTask(
            id=f"TDMS_{i}",
            department="TDMS",
            task_type="OHE Maintenance",
            start_km=float(start_km),
            end_km=float(start_km + 5),
            duration_mins=90,
            base_priority=random.randint(1, 3),
            deadline_mins=1440,
            line_direction=random.choice(directions)
        ))
        
    # SMMS (Signalling)
    for i in range(6):
        # Signalling usually at stations, pick a random station chainage approx
        station = random.choice(MOCK_STATIONS[1:-1])
        tasks.append(MaintenanceTask(
            id=f"SMMS_{i}",
            department="SMMS",
            task_type="Point Overhaul",
            start_km=station.chainage_km - 0.5,
            end_km=station.chainage_km + 0.5,
            duration_mins=60,
            base_priority=random.randint(2, 5),
            deadline_mins=1440,
            line_direction=random.choice(directions)
        ))
        
    return tasks
