from typing import List, Tuple

graphhopper_to_gmaps = {
    "car": "driving",
    "bike": "bicycling",
    "foot": "walking",
}


def generate_gmaps_route_url(
        user_waypoints: List[Tuple[float, float]],
        route_coords: List[Tuple[float, float, float]],
        profile: str,
) -> str:
    if profile not in graphhopper_to_gmaps:
        raise ValueError(f"Unsupported profile '{profile}'")

    gmaps_mode = graphhopper_to_gmaps[profile]
    max_waypoints = 10
    max_intermediate = max_waypoints - 2  # exclude origin & destination

    route_latlon = [(lat, lon) for lat, lon, _ in route_coords]

    origin = f"{user_waypoints[0][0]},{user_waypoints[0][1]}"
    destination = f"{user_waypoints[-1][0]},{user_waypoints[-1][1]}"

    # List of segments between user waypoints
    segments: List[List[Tuple[float, float]]] = []

    for i in range(len(user_waypoints) - 1):
        start_wp = user_waypoints[i]
        end_wp = user_waypoints[i + 1]

        start_idx = min(range(len(route_latlon)),
                        key=lambda j: (route_latlon[j][0] - start_wp[0]) ** 2 + (route_latlon[j][1] - start_wp[1]) ** 2)
        end_idx = min(range(start_idx, len(route_latlon)),
                      key=lambda j: (route_latlon[j][0] - end_wp[0]) ** 2 + (route_latlon[j][1] - end_wp[1]) ** 2)

        # Exclude endpoints
        segment_points = route_latlon[start_idx + 1:end_idx]
        segments.append(segment_points)

    # How many intermediate user waypoints exist?
    user_intermediates = user_waypoints[1:-1]
    remaining_slots = max_intermediate - len(user_intermediates)

    # Sample points proportionally from each segment
    sampled_points: List[Tuple[float, float]] = []
    total_points_available = sum(len(seg) for seg in segments)
    if remaining_slots > 0 and total_points_available > 0:
        for seg in segments:
            if not seg:
                continue
            n_points = max(1, round(len(seg) / total_points_available * remaining_slots))
            n_points = min(n_points, len(seg))
            # Evenly spaced indices
            indices = [int(i * len(seg) / n_points) for i in range(n_points)]
            sampled_points.append([seg[idx] for idx in indices])

    # Build intermediate waypoints in correct order
    intermediate_waypoints: List[Tuple[float, float]] = []
    for i in range(len(user_waypoints) - 1):
        # Add user-defined intermediate waypoint if it exists
        if 0 < i < len(user_waypoints) - 1:
            intermediate_waypoints.append(user_waypoints[i])
        # Add sampled points for this segment
        if sampled_points and i < len(sampled_points):
            intermediate_waypoints.extend(sampled_points[i])

    # Format for Google Maps
    waypoints_param = "|".join(f"{lat},{lon}" for lat, lon in intermediate_waypoints)

    url = f"https://www.google.com/maps/dir/?api=1&origin={origin}&destination={destination}"
    if waypoints_param:
        url += f"&waypoints={waypoints_param}"
    url += f"&travelmode={gmaps_mode}&dir_action=navigate"
    if gmaps_mode != "driving":
        url += "&avoid=highways"

    return url
