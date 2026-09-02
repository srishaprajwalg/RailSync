import random
from typing import List, Dict
from core.schemas import Station, TrainSchedule, TrainStop, MaintenanceTask, GoodsTrainForecast

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

HORIZON_DAYS = 30
MINS_PER_DAY = 1440

def generate_mock_timetables() -> List[TrainSchedule]:
    """Generates a simplified passenger timetable across the entire planning horizon."""
    random.seed(42)
    schedules = []
    
    train_types = [
        {"type": "Vande Bharat", "speed": 1.2, "stop_time": 2},
        {"type": "Shatabdi", "speed": 1.4, "stop_time": 2},
        {"type": "Superfast", "speed": 1.6, "stop_time": 3},
        {"type": "Express", "speed": 2.0, "stop_time": 5},
        {"type": "Passenger", "speed": 3.0, "stop_time": 10},
    ]
    
    for day in range(HORIZON_DAYS):
        day_offset = day * MINS_PER_DAY
        
        # Generate Up passenger trains (SBC -> JTJ)
        for i in range(1, 20):
            t_config = random.choices(train_types, weights=[5, 10, 30, 40, 15])[0]
            start_time = day_offset + (i * 70) + random.randint(0, 45)
            stops = []
            current_time = start_time
            prev_km = MOCK_STATIONS[0].chainage_km
            
            for station in MOCK_STATIONS:
                travel_time = int((station.chainage_km - prev_km) * t_config["speed"])
                current_time += travel_time
                arrival = current_time
                departure = current_time + (t_config["stop_time"] if station.id not in ["SBC", "JTJ"] else 0)
                stops.append(TrainStop(station_id=station.id, arrival_mins=arrival, departure_mins=departure))
                current_time = departure
                prev_km = station.chainage_km
                
            schedules.append(TrainSchedule(
                train_id=f"{t_config['type'][:3].upper().replace(' ', '')}_UP_D{day}_{i}",
                type=t_config["type"],
                direction="Up",
                stops=stops
            ))

        # Generate Down passenger trains (JTJ -> SBC)
        for i in range(1, 20):
            t_config = random.choices(train_types, weights=[5, 10, 30, 40, 15])[0]
            start_time = day_offset + (i * 70) + random.randint(30, 90)
            stops = []
            current_time = start_time
            prev_km = MOCK_STATIONS[-1].chainage_km
            
            for station in reversed(MOCK_STATIONS):
                travel_time = int(abs(station.chainage_km - prev_km) * t_config["speed"])
                current_time += travel_time
                arrival = current_time
                departure = current_time + (t_config["stop_time"] if station.id not in ["SBC", "JTJ"] else 0)
                stops.append(TrainStop(station_id=station.id, arrival_mins=arrival, departure_mins=departure))
                current_time = departure
                prev_km = station.chainage_km
                
            schedules.append(TrainSchedule(
                train_id=f"{t_config['type'][:3].upper().replace(' ', '')}_DN_D{day}_{i}",
                type=t_config["type"],
                direction="Down",
                stops=stops
            ))
            
    return schedules

def generate_mock_goods_forecasts() -> List[GoodsTrainForecast]:
    """Generates wide-window forecasts for goods trains."""
    random.seed(42)
    forecasts = []
    
    for day in range(HORIZON_DAYS):
        day_offset = day * MINS_PER_DAY
        
        # Up line goods trains
        for i in range(6): 
            start_km = 0.0
            end_km = 145.2
            earliest_entry = day_offset + random.randint(0, MINS_PER_DAY - 300)
            latest_exit = earliest_entry + 250 + 120 
            
            forecasts.append(GoodsTrainForecast(
                forecast_id=f"FREIGHT_UP_D{day}_{i}",
                direction="Up",
                start_km=start_km,
                end_km=end_km,
                earliest_entry_mins=earliest_entry,
                latest_exit_mins=latest_exit
            ))
            
        # Down line goods trains
        for i in range(6):
            start_km = 145.2
            end_km = 0.0
            earliest_entry = day_offset + random.randint(0, MINS_PER_DAY - 300)
            latest_exit = earliest_entry + 250 + 120 
            
            forecasts.append(GoodsTrainForecast(
                forecast_id=f"FREIGHT_DN_D{day}_{i}",
                direction="Down",
                start_km=start_km,
                end_km=end_km,
                earliest_entry_mins=earliest_entry,
                latest_exit_mins=latest_exit
            ))
            
    return forecasts

def generate_mock_tasks() -> List[MaintenanceTask]:
    """Generates synthetic maintenance tasks with defects, severity, and overdue status."""
    random.seed(42)
    tasks = []
    directions = ["Up", "Down"]
    origins = ["Defect", "Routine Maintenance"]
    
    def get_deadline():
        # Mix of extremely tight (infeasible), same-day, weekly, and monthly deadlines
        return random.choices(
            [random.randint(60, 300), random.randint(720, 1440), random.randint(1440, 7*1440), random.randint(7*1440, 30*1440)],
            weights=[5, 20, 35, 40]
        )[0]
    
    # TMS (Engineering)
    for i in range(150):
        start_km = random.randint(10, 130)
        origin = random.choices(origins, weights=[30, 70])[0]
        severity = random.randint(3, 5) if origin == "Defect" else random.randint(1, 3)
        overdue = random.randint(0, 30) if origin == "Routine Maintenance" else random.randint(0, 5)
        
        tasks.append(MaintenanceTask(
            id=f"TMS_{i}",
            department="TMS",
            task_type="Track Tamping" if origin == "Routine Maintenance" else "Rail Fracture Repair",
            origin=origin,
            severity=severity,
            overdue_days=overdue,
            asset_criticality=random.randint(1, 5),
            start_km=float(start_km),
            end_km=float(start_km + random.randint(1, 5)),
            duration_mins=random.choice([120, 180, 240]),
            deadline_mins=get_deadline(),
            line_direction=random.choice(directions)
        ))
        
    # TDMS (Traction)
    for i in range(120):
        start_km = random.randint(10, 130)
        origin = random.choices(origins, weights=[20, 80])[0]
        severity = random.randint(3, 5) if origin == "Defect" else random.randint(1, 3)
        overdue = random.randint(0, 15) if origin == "Routine Maintenance" else random.randint(0, 2)
        
        tasks.append(MaintenanceTask(
            id=f"TDMS_{i}",
            department="TDMS",
            task_type="OHE Maintenance" if origin == "Routine Maintenance" else "Insulator Flashover",
            origin=origin,
            severity=severity,
            overdue_days=overdue,
            asset_criticality=random.randint(1, 5),
            start_km=float(start_km),
            end_km=float(start_km + random.randint(2, 8)),
            duration_mins=90,
            deadline_mins=get_deadline(),
            line_direction=random.choice(directions)
        ))
        
    # SMMS (Signalling)
    for i in range(150):
        station = random.choice(MOCK_STATIONS[1:-1])
        origin = random.choices(origins, weights=[40, 60])[0]
        severity = random.randint(4, 5) if origin == "Defect" else random.randint(1, 4)
        overdue = random.randint(0, 20) if origin == "Routine Maintenance" else 0
        
        tasks.append(MaintenanceTask(
            id=f"SMMS_{i}",
            department="SMMS",
            task_type="Point Overhaul" if origin == "Routine Maintenance" else "Signal Failure",
            origin=origin,
            severity=severity,
            overdue_days=overdue,
            asset_criticality=random.randint(3, 5), # Station areas are more critical
            start_km=station.chainage_km - 0.5,
            end_km=station.chainage_km + 0.5,
            duration_mins=60,
            deadline_mins=get_deadline(),
            line_direction=random.choice(directions)
        ))
        
    return tasks
