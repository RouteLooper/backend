import osmnx as ox
import networkx as nx
import math
import random
from geopy.distance import geodesic


def distance_km(p1, p2):
    return geodesic(p1, p2).km


def bearing_deg(lat1, lon1, lat2, lon2):
    # Compute bearing from p1 to p2
    lat1_rad, lon1_rad = math.radians(lat1), math.radians(lon1)
    lat2_rad, lon2_rad = math.radians(lat2), math.radians(lon2)
    dlon = lon2_rad - lon1_rad
    y = math.sin(dlon) * math.cos(lat2_rad)
    x = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon)
    brng = math.atan2(y, x)
    return (math.degrees(brng) + 360) % 360


def nodes_around_point(graph, coord, x, tolerance=None):
    """
    Returns a set of nodes in graph G approximately x meters from a coordinate.

    Parameters:
        graph: networkx graph
        coord: tuple (lat, lon)
        x: target distance in meters
        tolerance: allowed distance tolerance in meters
    """
    if tolerance is None:
        tolerance = 0.1 * x

    # Find nearest graph node
    node = ox.distance.nearest_nodes(graph, X=coord[1], Y=coord[0])

    # Compute shortest path distances
    distances = nx.single_source_dijkstra_path_length(graph, node, weight='length')

    # Find nodes within tolerance
    nodes_near = {n for n, d in distances.items() if abs(d - x) <= tolerance}

    return nodes_near, node


def sample_point(graph, center_latlon, mean_dist_km, std_fraction=0.3, mean_angle_deg=None, angle_std_deg=45):
    """Sample a random point around center using polar coordinates."""
    r = abs(random.gauss(mean_dist_km, mean_dist_km * std_fraction))
    isodistance_nodes, _ = nodes_around_point(graph, center_latlon, r * 1000)

    if mean_angle_deg is None:
        chosen_node = random.choice(list(isodistance_nodes))
    else:
        theta = random.gauss(mean_angle_deg, angle_std_deg)
        # Pick node whose bearing is closest to theta
        center_lat, center_lon = center_latlon
        best_node = None
        min_diff = 360
        for n in isodistance_nodes:
            node_lat, node_lon = graph.nodes[n]['y'], graph.nodes[n]['x']
            diff = abs(bearing_deg(center_lat, center_lon, node_lat, node_lon) - theta) % 360
            if diff > 180:
                diff = 360 - diff
            if diff < min_diff:
                min_diff = diff
                best_node = n
        chosen_node = best_node

    # Return coordinates
    lat, lon = graph.nodes[chosen_node]['y'], graph.nodes[chosen_node]['x']
    return lat, lon
