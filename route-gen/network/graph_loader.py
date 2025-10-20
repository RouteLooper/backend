import osmnx as ox


def load_graph(center_point, radius_km, network_type='walk'):
    G = ox.graph_from_point(
        center_point,
        dist=radius_km * 1000,
        network_type=network_type,
        dist_type='network',
        simplify=True
    )
    print(f"Graph loaded: {len(G.nodes)} nodes, {len(G.edges)} edges")
    return G
