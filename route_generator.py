import os
from typing import List, Tuple, Dict, Any
from network.graph_loader import load_graph
from routing.router import generate_route
from routing.postprocessing import iteratively_clean
from utils.gmaps_link import generate_gmaps_route_url
from utils.gpx_utils import create_gpx_file
from utils.plotting import plot_route
from utils.elevation import add_elevations_to_coords
from shapely.geometry import LineString
import networkx as nx


def generate_route_api(
        start_end_lat_lon: Tuple[float, float],
        waypoints: List[Tuple[float, float]],
        target_distance_km: float,
        target_elevation_m: float,
        min_out_and_back_frac: float,
        network_type: str,
        radius_km: float = 10.0,
        max_iterations: int = 10
) -> Dict[str, Any]:
    """
    Generates a looped route based on inputs. Returns coordinates, distance, elevation, and Google Maps URL.

    Parameters
    ----------
    start_end_lat_lon : tuple
        Start and end coordinate (lat, lon)
    waypoints : list of tuples
        Optional waypoints (lat, lon) the route must pass through
    target_distance_km : float
        Target distance of the route in km
    target_elevation_m : float
        Target total uphill elevation (if used by your internal routing)
    min_out_and_back_frac : float
        Minimum fraction of route considered valid for out-and-back removal
    network_type : str
        One of {"walk", "bike", "drive"}
    radius_km : float
        Radius of graph to load (default: 10 km)
    max_iterations : int, optional
        Maximum cleaning iterations (default: 10)

    Returns
    -------
    dict with keys:
        route: list of (lat, lon)
        distance_km: float
        elevation_m: float (currently placeholder if not computed)
        google_maps_url: str
        metadata: dict (extra details)
    """

    # --- Step 1: Load OSM graph based on inputs ---
    G = load_graph(start_end_lat_lon, radius_km, network_type=network_type)

    # --- Step 2: Generate initial route ---
    full_route_nodes, generated_waypoints, total_length_km = generate_route(G, start_end_lat_lon, target_distance_km)

    # --- Step 3: Post-process (remove out-and-back segments) ---
    full_route_nodes, total_length_km = iteratively_clean(
        G,
        full_route_nodes,
        min_out_and_back_frac,
        target_distance_km,
        max_iterations
    )

    # --- Step 4: Optionally plot (for debug only) ---
    # plot_route(G, full_route_nodes)

    # --- Step 5: Google Maps link ---
    route_url = generate_gmaps_route_url(G, generated_waypoints, mode=network_type)

    # --- Step 6: Add Route Coordinates and Elevation ---
    route_coords = get_detailed_route_coords(G, full_route_nodes)
    print("[INFO] Adding elevation data to route points (batched)...")
    route_with_elev = add_elevations_to_coords(route_coords)

    gpx_path = create_gpx_file(route_with_elev)
    gpx_file_url = f"/gpx/{os.path.basename(gpx_path)}"

    # --- Step 7: Prepare return payload ---
    result = {
        "route": route_with_elev,
        "distance_km": total_length_km,
        "elevation_m": target_elevation_m,  # If your algorithm supports elevation, replace this
        "google_maps_url": route_url,
        "gpx_file_url": gpx_file_url,
        "metadata": {
            "num_waypoints": len(generated_waypoints),
            "network_type": network_type,
            "radius_km": radius_km,
        }
    }

    return result


def get_detailed_route_coords(G: nx.MultiDiGraph, route_nodes: List[int]) -> List[Tuple[float, float]]:
    """
    Expand a list of route nodes into high-resolution (lat, lon) coordinates
    following the exact road geometries in the graph.

    Parameters:
        G (nx.MultiDiGraph): OSMnx graph.
        route_nodes (List[int]): List of node IDs from ox.shortest_path().

    Returns:
        List[Tuple[float, float]]: High-resolution list of (lat, lon) coordinates.
    """
    detailed_coords = []

    for u, v in zip(route_nodes[:-1], route_nodes[1:]):
        # Find edge data between u and v
        edge_data = G.get_edge_data(u, v)

        if not edge_data:
            print(f"[WARNING] No edge data found between {u} and {v}. Skipping.")
            continue

        # Some edges have multiple parallel edges; pick the first one
        edge = list(edge_data.values())[0]

        # If geometry exists, use it
        if 'geometry' in edge and isinstance(edge['geometry'], LineString):
            coords = list(edge['geometry'].coords)
            # Convert (lon, lat) → (lat, lon)
            detailed_coords.extend([(lat, lon) for lon, lat in coords])
        else:
            # If no geometry, just use start and end nodes
            y1, x1 = G.nodes[u]['y'], G.nodes[u]['x']
            y2, x2 = G.nodes[v]['y'], G.nodes[v]['x']
            detailed_coords.extend([(y1, x1), (y2, x2)])

    print(f"[DEBUG] Generated {len(detailed_coords)} detailed route coordinates.")
    return detailed_coords
