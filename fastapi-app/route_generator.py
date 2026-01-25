import random
import pandas as pd
from typing import Tuple, Optional, Dict, Any, List

from utils.graphhopper_api import fetch_graphhopper_spt, fetch_graphhopper_route
from utils.gmaps_link import generate_gmaps_route_url
from utils.gpx_utils import create_gpx_file


def generate_loop_route_from_single_waypoint(
    waypoint: Tuple[float, float],
    profile: str,
    target_distance_m: float,
    host: str = "http://localhost:8989",
    threshold: float = 500
) -> Optional[Dict[str, Any]]:
    """(Same as before – unchanged)"""
    start_lat, start_lon = waypoint
    stage_distance = target_distance_m / 3

    print(f"\n[Loop Route] Generating looped route for '{profile}' | "
          f"Target={target_distance_m:.0f} m | Stage={stage_distance:.0f} m")

    df1 = fetch_graphhopper_spt(profile, start_lat, start_lon,
                                distance_limit=int(stage_distance + threshold),
                                host=host)
    if df1.empty:
        print("No SPT data from start point.")
        return None

    df1_ring = df1[(df1["distance"] >= stage_distance - threshold) &
                   (df1["distance"] <= stage_distance + threshold)]
    if df1_ring.empty:
        print("No ring points found at target distance from start.")
        return None

    first_random_point = df1_ring.sample(1).iloc[0]
    p1_lat, p1_lon = first_random_point["latitude"], first_random_point["longitude"]
    print(f"Selected first intermediate point near ({p1_lat:.5f}, {p1_lon:.5f})")

    df2 = fetch_graphhopper_spt(profile, p1_lat, p1_lon,
                                distance_limit=int(stage_distance + threshold),
                                host=host)
    if df2.empty:
        print("No SPT data from intermediate point.")
        return None

    df2_ring = df2[(df2["distance"] >= stage_distance - threshold) &
                   (df2["distance"] <= stage_distance + threshold)]
    if df2_ring.empty:
        print("No ring points found at target distance from intermediate point.")
        return None

    print("Finding intersection of SPT rings (exact coordinate match)...")
    common_points = pd.merge(df1_ring, df2_ring, on=["longitude", "latitude"])
    if common_points.empty:
        print("No common coordinates found between SPT rings.")
        return None

    chosen_match = common_points.sample(1).iloc[0]
    p2_lat, p2_lon = chosen_match["latitude"], chosen_match["longitude"]
    print(f"Selected intersection point at ({p2_lat:.5f}, {p2_lon:.5f})")

    points = [
        (start_lat, start_lon),
        (p1_lat, p1_lon),
        (p2_lat, p2_lon),
        (start_lat, start_lon)
    ]

    route_data = fetch_graphhopper_route(profile, points=points, host=host)
    if not route_data:
        print("Failed to generate route from selected points.")
        return None

    distance_m = route_data["distance"]
    duration_s = route_data["time"] / 1000
    elevation_gain = route_data["ascend"]
    elevation_loss = route_data["descend"]
    coordinates = route_data["coordinates"]

    route_coords_latlon = [(lat, lon, ele) for lon, lat, ele in coordinates]
    gpx_file_url = create_gpx_file(route_coords_latlon)
    gmaps_url = generate_gmaps_route_url(points, profile=profile)

    return {
        "route": coordinates,
        "distance_m": distance_m,
        "duration_s": duration_s,
        "elevation_gain_m": elevation_gain,
        "elevation_loss_m": elevation_loss,
        "gpx_file_url": gpx_file_url,
        "gmaps_url": gmaps_url,
        "network_type": profile,
    }


def generate_GH_loop_route_from_single_waypoint(
    waypoint: Tuple[float, float],
    profile: str,
    target_distance_m: float,
    host: str = "http://localhost:8989",
) -> Optional[Dict[str, Any]]:
    """(Same as before – unchanged)"""

    route_data = fetch_graphhopper_route(profile,
                                         points=[waypoint],
                                         host=host, round_trip=True,
                                         round_trip_dist=target_distance_m)
    if not route_data:
        print("Failed to generate route from selected points.")
        return None

    distance_m = route_data["distance"]
    duration_s = route_data["time"] / 1000
    elevation_gain = route_data["ascend"]
    elevation_loss = route_data["descend"]
    coordinates = route_data["coordinates"]

    route_coords_latlon = [(lat, lon, ele) for lon, lat, ele in coordinates]

    # Sample up to 8 points evenly
    num_samples = min(8, len(route_coords_latlon))
    if num_samples == len(route_coords_latlon):
        sampled_points = [(lat, lon) for lat, lon, _ in route_coords_latlon]
    else:
        # Compute evenly spaced indices
        indices = [round(i * (len(route_coords_latlon) - 1) / (num_samples - 1)) for i in range(num_samples)]
        sampled_points = [(route_coords_latlon[i][0], route_coords_latlon[i][1]) for i in indices]

    # Insert into points array
    points = [
        waypoint,  # start
        *sampled_points,  # sampled intermediate points
        waypoint  # end (same as start for loop)
    ]

    gpx_file_url = create_gpx_file(route_coords_latlon)
    gmaps_url = generate_gmaps_route_url(points, profile=profile)

    return {
        "route": coordinates,
        "distance_m": distance_m,
        "duration_s": duration_s,
        "elevation_gain_m": elevation_gain,
        "elevation_loss_m": elevation_loss,
        "gpx_file_url": gpx_file_url,
        "gmaps_url": gmaps_url,
        "network_type": profile,
    }


def generate_multi_waypoint_route(
    waypoints: List[Tuple[float, float]],
    profile: str,
    target_distance_m: float,
    loop: bool,
    host: str,
    threshold: float = 500
) -> Optional[Dict[str, Any]]:
    """
    Generates a route passing through multiple waypoints in order.
    Scales total distance to approximate target using SPT rings for intermediate adjustments.
    """

    if loop and waypoints[0] != waypoints[-1]:
        waypoints = waypoints + [waypoints[0]]

    # --- Compute base stage routes between consecutive waypoints ---
    stage_results = []
    total_distance = 0.0

    for i in range(len(waypoints) - 1):
        w1, w2 = waypoints[i], waypoints[i + 1]

        route = fetch_graphhopper_route(profile, points=[w1, w2], host=host)
        if not route:
            print(f"Failed to compute base route between {w1} and {w2}")
            return None

        dist = route["distance"]
        total_distance += dist
        stage_results.append({
            "start": w1, "end": w2,
            "distance": dist,
            "route": route
        })

    # --- Compare with target distance ---
    if total_distance >= target_distance_m:
        full_coords = [coord for s in stage_results for coord in s["route"]["coordinates"]]
        route_coords_latlon = [(lat, lon, ele) for lon, lat, ele in full_coords]
        gpx_file_url = create_gpx_file(route_coords_latlon)
        gmaps_url = generate_gmaps_route_url(waypoints, profile=profile)

        return {
            "route": full_coords,
            "distance_m": total_distance,
            "duration_s": sum(s["route"]["time"] for s in stage_results) / 1000,
            "elevation_gain_m": sum(s["route"]["ascend"] for s in stage_results),
            "elevation_loss_m": sum(s["route"]["descend"] for s in stage_results),
            "gpx_file_url": gpx_file_url,
            "gmaps_url": gmaps_url,
            "network_type": profile,
        }

    # --- Scale distances ---
    multiplier = target_distance_m / total_distance

    # --- For each stage, find SPT-based intermediate point ---
    new_points = [waypoints[0]]

    for i in range(len(waypoints) - 1):
        w1_lat, w1_lon = waypoints[i]
        w2_lat, w2_lon = waypoints[i + 1]
        stage_target = stage_results[i]["distance"] * multiplier
        half_stage = stage_target / 2

        df1 = fetch_graphhopper_spt(profile, w1_lat, w1_lon,
                                    distance_limit=int(half_stage + threshold),
                                    host=host)
        df2 = fetch_graphhopper_spt(profile, w2_lat, w2_lon,
                                    distance_limit=int(half_stage + threshold),
                                    host=host)
        if df1.empty or df2.empty:
            print("One of the SPTs is empty, skipping stage.")
            continue

        df1_ring = df1[(df1["distance"] >= half_stage - threshold) &
                       (df1["distance"] <= half_stage + threshold)]
        df2_ring = df2[(df2["distance"] >= half_stage - threshold) &
                       (df2["distance"] <= half_stage + threshold)]

        common = pd.merge(df1_ring, df2_ring, on=["longitude", "latitude"])
        if common.empty:
            print("No intersection found, skipping intermediate point.")
            continue

        chosen = common.sample(1).iloc[0]
        lat_i, lon_i = chosen["latitude"], chosen["longitude"]
        new_points.append((lat_i, lon_i))

        new_points.append(waypoints[i + 1])

    # --- Generate final route through all points ---
    route_data = fetch_graphhopper_route(profile, points=new_points, host=host)
    if not route_data:
        print("Failed to generate final multi-waypoint route.")
        return None

    coords = route_data["coordinates"]
    route_coords_latlon = [(lat, lon, ele) for lon, lat, ele in coords]
    gpx_file_url = create_gpx_file(route_coords_latlon)
    gmaps_url = generate_gmaps_route_url(new_points, profile=profile)

    return {
        "route": coords,
        "distance_m": route_data["distance"],
        "duration_s": route_data["time"] / 1000,
        "elevation_gain_m": route_data["ascend"],
        "elevation_loss_m": route_data["descend"],
        "gpx_file_url": gpx_file_url,
        "gmaps_url": gmaps_url,
        "network_type": profile,
    }


def generate_custom_route(
    waypoints: List[Tuple[float, float]],
    profile: str,
    target_distance_m: float,
    loop: bool = True,
    host: str = "http://localhost:8989"
) -> Optional[Dict[str, Any]]:
    """Master entry point for route generation."""
    if not waypoints:
        raise ValueError("At least one waypoint is required.")

    if len(waypoints) == 1:
        return generate_GH_loop_route_from_single_waypoint(waypoint=waypoints[0], profile=profile,
                                                           target_distance_m=target_distance_m, host=host)
    else:
        return generate_multi_waypoint_route(
            waypoints=waypoints,
            profile=profile,
            target_distance_m=target_distance_m,
            loop=loop,
            host=host
        )