import osmnx as ox


def load_graph(center_point, radius_km, network_type='walk', pbf_path='glos.osm.pbf'):
    ox.settings.use_cache = True

    G = ox.graph_from_point(
        center_point,
        dist=radius_km * 1000,
        network_type=network_type,
        dist_type='network',
        simplify=True
    )
    print(f"Graph loaded: {len(G.nodes)} nodes, {len(G.edges)} edges")

    return G

   # ox.settings.use_cache = True
    # Load the full PBF region (simplify=True ensures a clean graph)
   # G = ox.graph_from_file(pbf_path, network_type=network_type, simplify=True)
   # print(f"Full graph loaded: {len(G.nodes)} nodes, {len(G.edges)} edges")

    # Trim graph to desired radius around the center point
  #  G_sub = ox.truncate.truncate_graph_dist(G, center_point, max_dist=radius_km * 1000)
  #  print(f"Subgraph loaded: {len(G_sub.nodes)} nodes, {len(G_sub.edges)} edges")

   # return G_sub


