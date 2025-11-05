import osmnx as ox
from pyrosm import OSM
from shapely.geometry import Point
import networkx as nx
import os


def load_graph(center_point, radius_km, network_type='walk', pbf_path='glos.osm.pbf'):
    ox.settings.use_cache = True

    G = ox.graph_from_point(
        center_point,
        dist=radius_km * 1000,
        network_type=network_type,
        dist_type='network',
        simplify=False
    )
    print(f"Graph loaded: {len(G.nodes)} nodes, {len(G.edges)} edges")

    return G


def preprocess_pbf_to_graphml(pbf_path: str, output_path: str, network_type: str = "walk"):
    """
    Load a .pbf file using Pyrosm, build a network, simplify it, and save to GraphML.

    Parameters
    ----------
    pbf_path : str
        Path to .pbf file (e.g., 'data/great-britain-latest.osm.pbf')
    output_path : str
        Path to save simplified GraphML (e.g., 'data/glos_walk_simplified.graphml')
    network_type : str
        One of {'walk', 'bike', 'drive'}

    Returns
    -------
    G_simplified : networkx.MultiDiGraph
        Simplified OSMnx graph
    """
    print(f"[INFO] Loading OSM data from {pbf_path} for network type: {network_type}")
    osm = OSM(pbf_path)

    # Extract the network based on the mode
    if network_type == "walk":
        nodes, edges = osm.get_network(network_type="walking", nodes=True)
    elif network_type == "bike":
        nodes, edges = osm.get_network(network_type="cycling", nodes=True)
    elif network_type == "drive":
        nodes, edges = osm.get_network(network_type="driving", nodes=True)
    else:
        raise ValueError("network_type must be one of {'walk', 'bike', 'drive'}")

    print(f"[INFO] Network extracted: {len(nodes)} nodes, {len(edges)} edges")

    # Convert to OSMnx-compatible graph
    G = ox.graph_from_gdfs(nodes, edges, graph_attrs={"network_type": network_type})
    print(f"[INFO] Created graph with {len(G.nodes)} nodes and {len(G.edges)} edges")

    # Simplify
    print("[INFO] Simplifying graph...")
    G_simplified = ox.simplify_graph(G)
    print(f"[INFO] Simplified: {len(G_simplified.nodes)} nodes, {len(G_simplified.edges)} edges")

    # Save
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    ox.save_graphml(G_simplified, output_path)
    print(f"[INFO] Saved simplified graph to {output_path}")

    return G_simplified


def load_subgraph_from_simplified_graph(
    graphml_path: str,
    center_point: tuple,
    radius_km: float = 5.0
):
    """
    Load a preprocessed simplified graph and extract a subgraph around a point.

    Parameters
    ----------
    graphml_path : str
        Path to saved simplified GraphML file
    center_point : tuple
        (lat, lon)
    radius_km : float
        Extraction radius (in kilometers)

    Returns
    -------
    subgraph : networkx.MultiDiGraph
        Extracted subgraph for routing
    """
    lat, lon = center_point
    print(f"[INFO] Loading graph from {graphml_path}")
    G_full = ox.load_graphml(graphml_path)

    print(f"[INFO] Extracting subgraph around ({lat}, {lon}) ± {radius_km} km")
    subgraph = ox.truncate.truncate_graph_dist(G_full, Point(lon, lat), max_dist=radius_km * 1000)

    print(f"[INFO] Subgraph extracted: {len(subgraph.nodes)} nodes, {len(subgraph.edges)} edges")
    return subgraph
