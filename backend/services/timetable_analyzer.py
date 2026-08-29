from core.schemas import TrainSchedule, Station
from typing import List, Tuple, Dict

def get_train_occupancy(schedules: List[TrainSchedule], line_direction: str, start_km: float, end_km: float) -> List[Tuple[int, int]]:
    """
    Returns a list of (arrival_mins, departure_mins) tuples representing when trains
    occupy the track segment between start_km and end_km.
    """
    occupancies = []
    
    for schedule in schedules:
        if schedule.direction != line_direction:
            continue
            
        # We need to find when the train enters and exits the segment
        # A simple approximation for the MVP: find the stations that bracket the segment
        # and get the train's time at those stations.
        segment_entry_time = None
        segment_exit_time = None
        
        # Sort stops by arrival time just in case
        stops = sorted(schedule.stops, key=lambda x: x.arrival_mins)
        if not stops:
            continue
            
        # This is a simplification. A real implementation would interpolate exact times 
        # based on chainage and speed.
        if schedule.direction == "Up":
            # Train goes from lower chainage to higher chainage
            entry_stop = next((s for s in stops if next((st for st in MOCK_STATIONS if st.id == s.station_id), None).chainage_km >= start_km - 5), stops[0])
            exit_stop = next((s for s in reversed(stops) if next((st for st in MOCK_STATIONS if st.id == s.station_id), None).chainage_km <= end_km + 5), stops[-1])
            if entry_stop and exit_stop and entry_stop.arrival_mins <= exit_stop.departure_mins:
                occupancies.append((entry_stop.arrival_mins, exit_stop.departure_mins))
        else:
            # Down train (higher to lower chainage)
            entry_stop = next((s for s in stops if next((st for st in MOCK_STATIONS if st.id == s.station_id), None).chainage_km <= end_km + 5), stops[0])
            exit_stop = next((s for s in reversed(stops) if next((st for st in MOCK_STATIONS if st.id == s.station_id), None).chainage_km >= start_km - 5), stops[-1])
            if entry_stop and exit_stop and entry_stop.arrival_mins <= exit_stop.departure_mins:
                occupancies.append((entry_stop.arrival_mins, exit_stop.departure_mins))

    return merge_intervals(occupancies)

def merge_intervals(intervals: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    """Merges overlapping occupancy intervals."""
    if not intervals:
        return []
    sorted_intervals = sorted(intervals, key=lambda x: x[0])
    merged = [sorted_intervals[0]]
    
    for current in sorted_intervals[1:]:
        previous = merged[-1]
        if current[0] <= previous[1]:
            # Overlap, merge
            merged[-1] = (previous[0], max(previous[1], current[1]))
        else:
            merged.append(current)
            
    return merged

def find_white_spaces(occupancies: List[Tuple[int, int]], day_start: int = 0, day_end: int = 1440, safety_margin: int = 15) -> List[Tuple[int, int]]:
    """
    Finds available time windows given train occupancies.
    Applies safety margins before and after trains.
    """
    white_spaces = []
    current_time = day_start
    
    for occ in occupancies:
        window_start = current_time
        window_end = occ[0] - safety_margin
        
        if window_end - window_start > 0:
            white_spaces.append((window_start, window_end))
            
        current_time = occ[1] + safety_margin
        
    # Check space after the last train
    if day_end - current_time > 0:
        white_spaces.append((current_time, day_end))
        
    return white_spaces

# Needed for chainage reference
from services.mock_data import MOCK_STATIONS
