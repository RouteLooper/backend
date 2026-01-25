from typing import List, Tuple

graphhopper_to_gmaps = {
    "car": "driving",
    "bike": "bicycling",
    "foot": "walking",
}


def generate_gmaps_route_url(
        user_waypoints: List[Tuple[float, float]],
        profile: str,
) -> str:
    if profile not in graphhopper_to_gmaps:
        raise ValueError(f"Unsupported profile '{profile}'")

    gmaps_mode = graphhopper_to_gmaps[profile]

    o_lat, o_lon = user_waypoints.pop(0)
    d_lat, d_lon = user_waypoints.pop(-1)

    # Format for Google Maps
    url = f"https://www.google.com/maps/dir/?api=1&origin={o_lat},{o_lon}&destination={d_lat},{d_lon}"

    waypoints_param = "|".join(f"{lat},{lon}" for lat, lon in user_waypoints)

    if waypoints_param:
        url += f"&waypoints={waypoints_param}"
    url += f"&travelmode={gmaps_mode}&dir_action=navigate"
    if gmaps_mode != "driving":
        url += "&avoid=highways"

    return url
