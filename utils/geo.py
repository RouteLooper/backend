import osmnx as ox
import networkx as nx


def nodes_around_waypoint(graph, coord, x, tolerance=None):
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

    return nodes_near
