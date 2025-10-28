import osmnx as ox
import random
from utils.plotting import plot_isodistance_points
import numpy as np
from network.snapping import snap_to_road
from utils.geo import nodes_around_waypoint


def cluster_based_sample(G, node_set, center=None, n_bins=30, alpha=1.0, random_state=None):
    rng = np.random.default_rng(random_state)

    # --- Get coordinates of all nodes in G ---
    all_nodes = np.array(list(G.nodes))
    xs = np.array([G.nodes[n]['x'] for n in all_nodes])
    ys = np.array([G.nodes[n]['y'] for n in all_nodes])

    # --- Compute center if not provided ---
    if center is None:
        cx, cy = np.mean(xs), np.mean(ys)
    else:
        cy, cx = center  # user provides (lat, lon)

    # --- Compute radial distances for all nodes ---
    all_r = np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2)

    # --- Estimate 1D density using histogram ---
    hist, bin_edges = np.histogram(all_r, bins=n_bins, density=True)

    # --- Compute radial distances for candidate nodes ---
    node_list = list(node_set)
    x_nodes = np.array([G.nodes[n]['x'] for n in node_list])
    y_nodes = np.array([G.nodes[n]['y'] for n in node_list])
    r_nodes = np.sqrt((x_nodes - cx) ** 2 + (y_nodes - cy) ** 2)

    # --- Assign densities to each node based on histogram bin ---
    bin_idx = np.digitize(r_nodes, bin_edges) - 1
    bin_idx = np.clip(bin_idx, 0, len(hist) - 1)
    dens_nodes = hist[bin_idx]

    # --- Compute inverse-density sampling weights ---
    eps = 1e-12
    weights = (dens_nodes + eps) ** (-alpha)
    probs = weights / np.sum(weights)

    # --- Sample one node according to inverse-density probabilities ---
    sampled_node = rng.choice(node_list, p=probs)
    return sampled_node


def generate_route(G, start_latlon, target_distance_km, plot=False):
    waypoints = []
    current_waypoint, snapped_point = snap_to_road(G, start_latlon)
    waypoints.append(current_waypoint)

    leg_distance_m = (target_distance_km * 1000) / 3  # convert to meters

    print("Sampling points and routing...")

    # --- Sample second point ---
    nodes_around_1 = nodes_around_waypoint(G, snapped_point, leg_distance_m)
    print(f"Found {len(nodes_around_1)} nodes around point 1.")
    if not nodes_around_1:
        raise ValueError("No nodes found around start point for the given leg distance.")

    second_waypoint = cluster_based_sample(G, nodes_around_1, center=snapped_point)
    lat2, lon2 = G.nodes[second_waypoint]['y'], G.nodes[second_waypoint]['x']
    second_waypoint_coord = (lat2, lon2)
    second_waypoint, second_snapped = snap_to_road(G, second_waypoint_coord)
    waypoints.append(second_waypoint)

    # --- Sample third point ---
    nodes_around_2 = nodes_around_waypoint(G, second_snapped, leg_distance_m)
    print(f"Found {len(nodes_around_2)} nodes around point 2.")
    intersection_nodes = nodes_around_1.intersection(nodes_around_2)
    if not intersection_nodes:
        raise ValueError("No intersection nodes found between isodistance rings.")

    third_waypoint = random.choice(list(intersection_nodes))
    waypoints.append(third_waypoint)

    print(f"Found {len(intersection_nodes)} intersecting nodes.")

    # use ox.shortest_path to compute full list of nodes for route from first -> second -> third -> first
    path1 = ox.shortest_path(G, current_waypoint, second_waypoint, weight="length")
    path2 = ox.shortest_path(G, second_waypoint, third_waypoint, weight="length")
    path3 = ox.shortest_path(G, third_waypoint, current_waypoint, weight="length")

    # Combine paths, avoiding duplicate nodes at the joins
    full_route_nodes = path1 + path2[1:] + path3[1:]

    # --- Compute total length ---
    total_length_m = 0
    for u, v in zip(full_route_nodes[:-1], full_route_nodes[1:]):
        if G.has_edge(u, v):
            edge_data = G.get_edge_data(u, v)
            # For MultiDiGraphs, choose first edge if multiple
            if isinstance(edge_data, dict):
                first_edge = edge_data[list(edge_data.keys())[0]]
                total_length_m += first_edge.get('length', 0)
        else:
            # If route includes a reversed edge, try the other direction
            if G.has_edge(v, u):
                edge_data = G.get_edge_data(v, u)
                first_edge = edge_data[list(edge_data.keys())[0]]
                total_length_m += first_edge.get('length', 0)

    total_length_km = total_length_m / 1000
    print(f"Generated route with {len(full_route_nodes)} total nodes.")
    print(f"Total route length: {total_length_km:.2f} km")

    # --- Plotting ---
    if plot:
        plot_isodistance_points(G, nodes_around_1, nodes_around_2, intersection_nodes, full_route_nodes, waypoints)

    return full_route_nodes, waypoints, total_length_km
