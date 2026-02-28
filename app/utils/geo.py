"""
Geographic utilities for GigRoute.
Provides distance calculations and travel time estimations.
"""
import math
from typing import Optional, Tuple


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points on Earth.

    Uses the Haversine formula to calculate the shortest distance
    over the earth's surface.

    Args:
        lat1: Latitude of first point in degrees
        lon1: Longitude of first point in degrees
        lat2: Latitude of second point in degrees
        lon2: Longitude of second point in degrees

    Returns:
        Distance in kilometers, rounded to 1 decimal place
    """
    # Earth's radius in kilometers
    R = 6371.0

    # Convert degrees to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    # Differences
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    # Haversine formula
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))

    distance = R * c
    return round(distance, 1)


def estimate_travel_time(distance_km: float, mode: str = 'car') -> int:
    """
    Estimate travel time based on distance and transport mode.

    Uses average speeds for different transport modes to estimate
    travel duration. These are rough estimates - actual times may vary
    based on traffic, route, and other factors.

    Args:
        distance_km: Distance in kilometers
        mode: Transport mode - 'car', 'train', 'bus', 'flight', 'walk'

    Returns:
        Estimated travel time in minutes
    """
    # Average speeds in km/h for different modes
    speeds = {
        'car': 80,      # Highway average
        'train': 200,   # High-speed train
        'bus': 60,      # Coach/tour bus
        'flight': 800,  # Commercial aircraft (excluding airport time)
        'walk': 5,      # Walking pace
        'bike': 20,     # Cycling
    }

    speed = speeds.get(mode.lower(), 80)  # Default to car speed

    # Calculate time in hours, convert to minutes
    time_hours = distance_km / speed
    time_minutes = time_hours * 60

    # Add buffer time for different modes
    if mode.lower() == 'flight':
        # Add 2 hours for airport procedures
        time_minutes += 120
    elif mode.lower() == 'train':
        # Add 15 minutes for station access
        time_minutes += 15

    return round(time_minutes)


def format_travel_time(minutes: int) -> str:
    """
    Format travel time in a human-readable string.

    Args:
        minutes: Travel time in minutes

    Returns:
        Formatted string like "2h30" or "45min"
    """
    if minutes < 60:
        return f"{minutes}min"

    hours = minutes // 60
    remaining_minutes = minutes % 60

    if remaining_minutes == 0:
        return f"{hours}h"

    return f"{hours}h{remaining_minutes:02d}"


def calculate_stops_distances(tour_stops: list) -> list:
    """
    Calculate distances between consecutive tour stops.

    Args:
        tour_stops: List of TourStop objects with coordinates (from venue OR direct location)

    Returns:
        List of dicts with distance info between consecutive stops:
        [
            {
                'from_stop': TourStop,
                'to_stop': TourStop,
                'distance_km': float,
                'estimated_time_car': int,  # minutes
                'estimated_time_formatted': str
            },
            ...
        ]
    """
    distances = []

    # Sort stops by date
    sorted_stops = sorted(tour_stops, key=lambda s: s.date)

    for i in range(len(sorted_stops) - 1):
        current_stop = sorted_stops[i]
        next_stop = sorted_stops[i + 1]

        # Check if both stops have coordinates (via venue OR direct location)
        if current_stop.has_coordinates and next_stop.has_coordinates:
            current_coords = current_stop.get_coordinates
            next_coords = next_stop.get_coordinates

            distance = haversine_distance(
                current_coords[0], current_coords[1],
                next_coords[0], next_coords[1]
            )

            travel_time = estimate_travel_time(distance, 'car')

            distances.append({
                'from_stop': current_stop,
                'to_stop': next_stop,
                'distance_km': distance,
                'estimated_time_car': travel_time,
                'estimated_time_formatted': format_travel_time(travel_time)
            })
        else:
            # No coordinates available
            distances.append({
                'from_stop': current_stop,
                'to_stop': next_stop,
                'distance_km': None,
                'estimated_time_car': None,
                'estimated_time_formatted': None
            })

    return distances


def get_tour_total_distance(tour_stops: list) -> Tuple[Optional[float], int]:
    """
    Calculate total distance for a tour.

    Args:
        tour_stops: List of TourStop objects

    Returns:
        Tuple of (total_distance_km, stops_with_coordinates_count)
    """
    distances = calculate_stops_distances(tour_stops)

    total_km = 0.0
    valid_count = 0

    for d in distances:
        if d['distance_km'] is not None:
            total_km += d['distance_km']
            valid_count += 1

    if valid_count == 0:
        return None, 0

    return round(total_km, 1), valid_count


def get_google_maps_directions_url(
    origin_lat: float, origin_lon: float,
    dest_lat: float, dest_lon: float,
    mode: str = 'driving'
) -> str:
    """
    Generate a Google Maps directions URL.

    Args:
        origin_lat: Origin latitude
        origin_lon: Origin longitude
        dest_lat: Destination latitude
        dest_lon: Destination longitude
        mode: Travel mode - 'driving', 'transit', 'walking', 'bicycling'

    Returns:
        Google Maps directions URL
    """
    return (
        f"https://www.google.com/maps/dir/?api=1"
        f"&origin={origin_lat},{origin_lon}"
        f"&destination={dest_lat},{dest_lon}"
        f"&travelmode={mode}"
    )
