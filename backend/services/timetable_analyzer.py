from core.schemas import TrainSchedule, GoodsTrainForecast
from services.real_corridor import CORRIDOR_STATIONS
from typing import List, Tuple, Optional

def get_station_chainage(station_id: str) -> float:
    for st in CORRIDOR_STATIONS:
        if st.id == station_id:
            return st.chainage_km
    return 0.0

def interpolate_train_time(schedule: TrainSchedule, target_km: float) -> Optional[int]:
    """Interpolates the time a passenger train passes a specific chainage."""
    # Find the stops that bracket this chainage
    stops = schedule.stops
    
    # Ensure stops are ordered by chainage
    stops_with_km = [(s, get_station_chainage(s.station_id)) for s in stops]
    stops_with_km.sort(key=lambda x: x[1])
    
    if schedule.direction == "Up":
        # Chainage is increasing
        for i in range(len(stops_with_km) - 1):
            s1, km1 = stops_with_km[i]
            s2, km2 = stops_with_km[i+1]
            if km1 <= target_km <= km2:
                # Interpolate between departure of s1 and arrival of s2
                if km2 == km1:
                    return s1.departure_mins
                fraction = (target_km - km1) / (km2 - km1)
                return s1.departure_mins + int(fraction * (s2.arrival_mins - s1.departure_mins))
                
        # If target is exactly at or beyond the last stop
        if target_km >= stops_with_km[-1][1]:
            return stops_with_km[-1][0].arrival_mins
        # If before first stop
        if target_km <= stops_with_km[0][1]:
            return stops_with_km[0][0].departure_mins

    else:
        # Down direction, train goes from higher to lower chainage
        # stops are ordered by increasing chainage in stops_with_km, but train travels in reverse.
        # So we look at stops from end to start.
        # But wait, stops_with_km is sorted by chainage (0 to 145).
        # Down train starts at 145 and goes to 0. 
        # stops_with_km[i] (lower chainage) is visited AFTER stops_with_km[i+1] (higher chainage).
        for i in range(len(stops_with_km) - 1, 0, -1):
            s1, km1 = stops_with_km[i] # higher chainage (visited first)
            s2, km2 = stops_with_km[i-1] # lower chainage (visited second)
            if km2 <= target_km <= km1:
                # Interpolate between departure of s1 and arrival of s2
                if km1 == km2:
                    return s1.departure_mins
                fraction = (km1 - target_km) / (km1 - km2)
                return s1.departure_mins + int(fraction * (s2.arrival_mins - s1.departure_mins))
                
        if target_km <= stops_with_km[0][1]:
            return stops_with_km[0][0].arrival_mins
        if target_km >= stops_with_km[-1][1]:
            return stops_with_km[-1][0].departure_mins

    return None

def get_passenger_train_occupancy(schedules: List[TrainSchedule], line_direction: str, task_start_km: float, task_end_km: float) -> List[Tuple[int, int]]:
    """
    Returns exact time intervals when passenger trains occupy the specific task segment.
    """
    occupancies = []
    # Ensure start_km <= end_km
    start_km = min(task_start_km, task_end_km)
    end_km = max(task_start_km, task_end_km)
    
    for schedule in schedules:
        if schedule.direction != line_direction:
            continue
            
        t_start = interpolate_train_time(schedule, start_km)
        t_end = interpolate_train_time(schedule, end_km)
        
        if t_start is not None and t_end is not None:
            # Ensure proper ordering regardless of direction
            enter_time = min(t_start, t_end)
            exit_time = max(t_start, t_end)
            occupancies.append((enter_time, exit_time))
            
    return occupancies

def get_goods_train_occupancy(forecasts: List[GoodsTrainForecast], line_direction: str, task_start_km: float, task_end_km: float) -> List[Tuple[int, int]]:
    """
    Returns time intervals when goods trains MIGHT occupy the task segment based on a prototype freight uncertainty model.
    """
    occupancies = []
    start_km = min(task_start_km, task_end_km)
    end_km = max(task_start_km, task_end_km)
    
    for forecast in forecasts:
        if forecast.direction != line_direction:
            continue
            
        total_dist = abs(forecast.end_km - forecast.start_km)
        if total_dist == 0:
            continue
            
        if forecast.direction == "Up":
            frac_enter = (start_km - forecast.start_km) / total_dist
            frac_exit = (end_km - forecast.start_km) / total_dist
        else:
            frac_enter = (forecast.start_km - end_km) / total_dist
            frac_exit = (forecast.start_km - start_km) / total_dist

        frac_enter = max(0.0, min(1.0, frac_enter))
        frac_exit = max(0.0, min(1.0, frac_exit))
        
        # PROTOTYPE FREIGHT UNCERTAINTY MODEL
        # We assume a nominal freight speed of ~40 km/h to determine expected transit time.
        # The remaining time in the forecast window is treated as the safety/uncertainty buffer.
        nominal_speed_kmh = 40.0
        expected_transit_mins = int((total_dist / nominal_speed_kmh) * 60)
        
        total_window_mins = forecast.latest_exit_mins - forecast.earliest_entry_mins
        
        if expected_transit_mins > total_window_mins:
            expected_transit_mins = total_window_mins
            
        uncertainty_buffer_mins = total_window_mins - expected_transit_mins
        
        # Expected times for the whole corridor
        expected_corridor_entry = forecast.earliest_entry_mins + (uncertainty_buffer_mins // 2)
        
        # Expected times for this specific segment
        segment_expected_enter = expected_corridor_entry + int(frac_enter * expected_transit_mins)
        segment_expected_exit = expected_corridor_entry + int(frac_exit * expected_transit_mins)
        
        # The protected uncertainty window for this segment applies half the buffer before and after expected passage
        earliest_segment_entry = segment_expected_enter - (uncertainty_buffer_mins // 2)
        latest_segment_exit = segment_expected_exit + (uncertainty_buffer_mins // 2)
        
        if earliest_segment_entry < latest_segment_exit:
            occupancies.append((earliest_segment_entry, latest_segment_exit))
            
    return occupancies
