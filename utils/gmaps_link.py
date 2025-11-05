from typing import List, Tuple


def generate_gmaps_route_url(
        route_coords: List[Tuple[float, float]],
        waypoints: List[Tuple[float, float]] = None,
        mode: str = "auto"
) -> str:
    """
    Generate a Google Maps Directions URL approximating the Valhalla route.

    Parameters
    ----------
    route_coords : list of (lat, lon)
        Ordered coordinates from Valhalla route.
    waypoints : list of (lat, lon), optional
        User-specified waypoints (used to detect case 2).
    mode : str
        One of Valhalla profiles:
        {'auto', 'bicycle', 'bus', 'bikeshare', 'truck', 'taxi',
         'motor_scooter', 'motorcycle', 'multimodal', 'pedestrian'}

    Returns
    -------
    str : Google Maps Directions URL
    """

    valhalla_to_gmaps = {
        "auto": "driving",
        "truck": "driving",
        "taxi": "driving",
        "bus": "driving",  # Google Maps driving covers road-based modes
        "motor_scooter": "driving",
        "motorcycle": "driving",
        "bicycle": "bicycling",
        "bikeshare": "bicycling",
        "pedestrian": "walking",
        "multimodal": "driving",  # fallback
    }

    # Normalize mode
    mode = mode.lower()
    gmaps_mode = valhalla_to_gmaps.get(mode, "driving")

    # Normalize
    waypoints = waypoints or []

    # Google Maps limits
    MAX_TOTAL_POINTS = 10  # origin + destination + 8 waypoints
    MAX_WAYPOINTS = MAX_TOTAL_POINTS - 2

    # ------------------------------------------------------------
    # CASE 1: No user waypoints (use Valhalla coordinates directly)
    # ------------------------------------------------------------
    if len(waypoints) == 0:
        if len(route_coords) <= MAX_TOTAL_POINTS:
            gmaps_points = route_coords
        else:
            # Downsample evenly
            step = max(1, len(route_coords) // MAX_TOTAL_POINTS)
            gmaps_points = route_coords[::step]
            if gmaps_points[-1] != route_coords[-1]:
                gmaps_points.append(route_coords[-1])

    # ------------------------------------------------------------
    # CASE 2: User-provided waypoints
    # ------------------------------------------------------------
    else:
        user_wps = waypoints
        n_user = len(user_wps)

        # If too many user waypoints, subsample evenly to fit limit
        if n_user > MAX_WAYPOINTS:
            step = max(1, n_user // MAX_WAYPOINTS)
            sampled_user_wps = user_wps[::step]
            # Ensure last one included
            if sampled_user_wps[-1] != user_wps[-1]:
                sampled_user_wps.append(user_wps[-1])
            user_wps = sampled_user_wps

        # Now merge with route geometry (for shape fidelity)
        total_pts = len(route_coords)
        if total_pts <= MAX_TOTAL_POINTS:
            gmaps_points = route_coords
        else:
            n_middle = MAX_WAYPOINTS
            step = max(1, total_pts // (n_middle + 1))
            shape_points = route_coords[step:step * n_middle:step]
            gmaps_points = [route_coords[0]] + shape_points + [route_coords[-1]]

        # Replace some of the middle shape points with user waypoints,
        # evenly distributed across available slots
        if len(user_wps) > 0:
            slots = min(MAX_WAYPOINTS, len(user_wps))
            indices = [round(i * (len(gmaps_points) - 2) / (slots + 1)) + 1 for i in range(slots)]
            for idx, wp in zip(indices, user_wps):
                if 0 < idx < len(gmaps_points) - 1:
                    gmaps_points[idx] = wp

    # ------------------------------------------------------------
    # Compose URL
    # ------------------------------------------------------------
    origin = f"{gmaps_points[0][0]},{gmaps_points[0][1]}"
    destination = f"{gmaps_points[-1][0]},{gmaps_points[-1][1]}"
    middle_points = gmaps_points[1:-1]

    waypoints_param = ""
    if middle_points:
        waypoints_strs = [f"{lat},{lon}" for lat, lon in middle_points]
        waypoints_param = "|".join(waypoints_strs)

    url = f"https://www.google.com/maps/dir/?api=1&origin={origin}&destination={destination}"
    if waypoints_param:
        url += f"&waypoints={waypoints_param}"
    url += f"&travelmode={gmaps_mode}&dir_action=navigate"
    if gmaps_mode != "driving":
        url += "&avoid=highways"

    return url
