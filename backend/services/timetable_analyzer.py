from core.schemas import TrainSchedule, GoodsTrainForecast
from services.mock_data import MOCK_STATIONS
from typing import List, Tuple, Optional

def get_station_chainage(station_id: str) -> float:
    for st in MOCK_STATIONS:
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
    Returns time intervals when goods trains MIGHT occupy the task segment based on their forecast window.
    """
    occupancies = []
    start_km = min(task_start_km, task_end_km)
    end_km = max(task_start_km, task_end_km)
    
    for forecast in forecasts:
        if forecast.direction != line_direction:
            continue
            
        # Simplified interpolation for the uncertainty window
        # The goods train travels from forecast.start_km to forecast.end_km
        total_dist = abs(forecast.end_km - forecast.start_km)
        if total_dist == 0:
            continue
            
        if forecast.direction == "Up":
            # Up: lower to higher chainage
            frac_enter = (start_km - forecast.start_km) / total_dist
            frac_exit = (end_km - forecast.start_km) / total_dist
        else:
            # Down: higher to lower chainage
            frac_enter = (forecast.start_km - end_km) / total_dist
            frac_exit = (forecast.start_km - start_km) / total_dist

        # Clamp fractions
        frac_enter = max(0.0, min(1.0, frac_enter))
        frac_exit = max(0.0, min(1.0, frac_exit))
        
        total_time_window = forecast.latest_exit_mins - forecast.earliest_entry_mins
        
        # We calculate the earliest possible entry and latest possible exit for this segment
        # Goods trains can be anywhere in this expanding window.
        earliest_segment_entry = forecast.earliest_entry_mins + int(frac_enter * (total_time_window * 0.5))
        latest_segment_exit = forecast.latest_exit_mins - int((1 - frac_exit) * (total_time_window * 0.5))
        
        if earliest_segment_entry < latest_segment_exit:
            occupancies.append((earliest_segment_entry, latest_segment_exit))
            
    return occupancies
