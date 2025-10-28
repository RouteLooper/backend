from urllib.parse import quote


def generate_gmaps_route_url(graph, node_ids, mode="drive"):
    """
    Generate a properly formatted Google Maps Directions URL from OSMnx nodes.
    Route will start and end at the same node (circular route).

    Parameters
    ----------
    graph : networkx.MultiDiGraph
        The OSMnx graph containing the nodes.
    node_ids : list[int]
        List of OSMnx node IDs (2–10).
    mode : str
        One of {'walk', 'drive', 'bike'}.

    Returns
    -------
    str
        A valid Google Maps Directions URL following API spec.
    """

    if len(node_ids) < 2:
        raise ValueError("At least two nodes (start + one waypoint) are required.")
    if len(node_ids) > 10:
        raise ValueError("Google Maps supports at most 10 total locations (origin + waypoints + destination).")

    # Convert OSMnx modes → Google Maps travelmode
    mode_map = {
        "walk": "walking",
        "drive": "driving",
        "bike": "bicycling"
    }
    if mode not in mode_map:
        raise ValueError("Mode must be one of: 'walk', 'drive', 'bike'.")
    gmaps_mode = mode_map[mode]

    # Ensure circular route: append start to end
    if node_ids[0] != node_ids[-1]:
        node_ids = node_ids + [node_ids[0]]

    # Extract lat/lon for each node
    coords = [(graph.nodes[n]['y'], graph.nodes[n]['x']) for n in node_ids]

    # Define origin, destination, and waypoints
    origin = f"{coords[0][0]},{coords[0][1]}"
    destination = f"{coords[-1][0]},{coords[-1][1]}"
    waypoints = coords[1:-1]

    # Build waypoints string separated by '|'
    if waypoints:
        waypoints_param = "|".join([f"{lat},{lon}" for lat, lon in waypoints])
        waypoints_param = quote(waypoints_param, safe='|,')
    else:
        waypoints_param = ""

    # Construct URL according to spec
    url = f"https://www.google.com/maps/dir/?api=1&origin={origin}&destination={destination}"
    if waypoints_param:
        url += f"&waypoints={waypoints_param}"
    url += f"&travelmode={gmaps_mode}"
    url += "&dir_action=navigate"
    if gmaps_mode != "driving":
        url += "&avoid=highways"

    return url
