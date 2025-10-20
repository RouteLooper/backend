import networkx as nx
import math
from network.snapping import snap_to_road
from utils.geo import sample_point, distance_km
from config import *


def generate_route(G, start_latlon, target_distance_km, N):
    route_nodes = []
    current_point = start_latlon
    current_node, current_point = snap_to_road(G, current_point)
    route_nodes.append(current_node)

    total_distance = 0
    remaining_distance = target_distance_km
    print(f"Remaining: {remaining_distance:.2f}")
    avg_leg = target_distance_km / (N + 1)  # leg to each consecutive intermediate point plus leg back to start
    bearing = None

    print("Sampling points and routing...")

    for i in range(N):

        # --- Sample new point ---
        new_point = sample_point(G, current_point, avg_leg, mean_angle_deg=bearing)

        # Resample until within initial search area
        while distance_km(start_latlon, new_point) > radius_km:
            new_point = sample_point(G, current_point, avg_leg, mean_angle_deg=bearing)

        # Snap to road network
        new_node, snapped_point = snap_to_road(G, new_point)

        # --- Compute route ---
        path = nx.shortest_path(G, current_node, new_node, weight="length")
        segment_length_m = sum(
            G[u][v][0]["length"] if 0 in G[u][v] else G[u][v]["length"]
            for u, v in zip(path[:-1], path[1:])
        )
        segment_length_km = segment_length_m / 1000
        total_distance += segment_length_km

        remaining_distance -= segment_length_km
        avg_leg = max(remaining_distance / max((N - i - 1), 1), 0.1)

        route_nodes.extend(path[1:])
        current_node = new_node
        current_point = snapped_point

        # --- Update bearing for directional bias ---
        if len(path) > 1:
            y0, x0 = G.nodes[path[0]]["y"], G.nodes[path[0]]["x"]
            y1, x1 = G.nodes[path[-1]]["y"], G.nodes[path[-1]]["x"]
            bearing = math.degrees(math.atan2(x1 - x0, y1 - y0))

    # Finally, route back to start
    try:
        back_path = nx.shortest_path(G, current_node, route_nodes[0], weight='length')
        route_nodes.extend(back_path[1:])
    except Exception as e:
        print("Failed to close loop:", e)

    return route_nodes
