"""
osmnx_multi_mode_routing.py

Purpose:
- Input: JSON file or JSON string containing an array of lat/lng points.
- For each transport mode ("drive", "bike", "walk") compute a route that visits the points sequentially
  and returns to the start (A -> B -> C -> ... -> A), concatenating segment paths.
- Returns for each mode: resampled high-resolution coordinate list, encoded polyline, distance (km), duration (min).

Notes:
- This script uses OSMnx + NetworkX + Shapely + polyline packages.
- OSMnx downloads OpenStreetMap data at runtime; internet connection is required.
- The script builds a graph that covers the bounding box of the input points (with a safety buffer).
- Edges' geometry is used (when available) to reconstruct smooth road geometry; the final polyline is
  resampled every `resample_m` meters (default 10m) for smooth display in map SDKs.

Usage examples:
  python osmnx_multi_mode_routing.py --input-file points.json --resample 10 --modes drive bike walk
  python osmnx_multi_mode_routing.py --input-json '[{"lat":51.5,"lng":-0.1},{"lat":51.52,"lng":-0.12}]'

Output: printed JSON to stdout with keys per mode.

Dependencies:
  pip install osmnx networkx shapely polyline click

"""

import json
import math
from typing import List, Tuple, Dict, Optional
import click

# geospatial / routing libs
import osmnx as ox
import networkx as nx
from shapely.geometry import LineString, Point
from shapely.ops import linemerge
import polyline


# ---- Utilities ----

def bbox_from_points(points: List[Tuple[float, float]], buffer_m: float = 1000) -> Tuple[float, float, float, float]:
    """
    Return bounding box as (west, south, east, north) expanded by buffer_m meters.
    """
    lats = [p[0] for p in points]
    lngs = [p[1] for p in points]
    min_lat, max_lat = min(lats), max(lats)
    min_lng, max_lng = min(lngs), max(lngs)

    mean_lat = (min_lat + max_lat) / 2.0
    meters_per_deg_lat = 111_320.0
    meters_per_deg_lng = 111_320.0 * math.cos(math.radians(mean_lat))

    lat_buffer = buffer_m / meters_per_deg_lat
    lng_buffer = buffer_m / meters_per_deg_lng if meters_per_deg_lng != 0 else 0.01

    north = max_lat + lat_buffer
    south = min_lat - lat_buffer
    east = max_lng + lng_buffer
    west = min_lng - lng_buffer

    # return (west, south, east, north) to match OSMnx graph_from_bbox order
    return west, south, east, north


def build_graph_for_mode(points: List[Tuple[float, float]], mode: str = "drive",
                         buffer_m: int = 2000) -> nx.MultiDiGraph:
    """Build an OSMnx graph covering all points with a buffer.
    mode: 'drive', 'bike' (or 'bike' -> 'bike' or 'cycle'), 'walk'
    """
    west, south, east, north = bbox_from_points(points, buffer_m=buffer_m)
    bbox = (west, south, east, north)
    # network_type mapping: allow synonyms
    network_type = mode
    if mode == 'bike':
        network_type = 'bike'  # OSMnx supports 'bike'
    if mode in ("walk", "pedestrian"):
        network_type = 'walk'

    print(f"Downloading graph for mode='{mode}' bbox: W={bbox[0]:.6f}, S={bbox[1]:.6f}, E={bbox[2]:.6f}, N={bbox[3]:.6f}")
    G = ox.graph_from_bbox(bbox, network_type=network_type, simplify=True)

    # ensure length attribute exists on edges
    ox.distance.add_edge_lengths(G)

    return G


def route_nodes_and_edges(G: nx.MultiDiGraph, orig_xy: Tuple[float, float], dest_xy: Tuple[float, float]) -> Tuple[
    List[int], List[Tuple[int, int, int]]]:
    """Compute node route (list of node ids) and list of (u,v,key) edges for the path.
    orig_xy and dest_xy are (lat, lng).
    """
    orig_node = ox.distance.nearest_nodes(G, orig_xy[1], orig_xy[0])
    dest_node = ox.distance.nearest_nodes(G, dest_xy[1], dest_xy[0])

    # shortest path by length (meters)
    route_nodes = nx.shortest_path(G, orig_node, dest_node, weight='length')

    # construct list of edges (u,v,key) in order
    edge_list = []
    for u, v in zip(route_nodes[:-1], route_nodes[1:]):
        # for multigraph there may be multiple keys; choose the first (or the one with min length)
        data_dict = G.get_edge_data(u, v)
        if data_dict is None:
            continue
        # choose key with minimum 'length' if available
        best_key = None
        best_len = float('inf')
        for key, attr in data_dict.items():
            length = attr.get('length', float('inf'))
            if length < best_len:
                best_len = length
                best_key = key
        edge_list.append((u, v, best_key))

    return route_nodes, edge_list


def edges_to_coords(G: nx.MultiDiGraph, edge_list: List[Tuple[int, int, int]]) -> List[Tuple[float, float]]:
    """Convert an ordered list of edges into a concatenated list of (lat,lng) coordinates using edge geometry when available.
    Ensures continuity (no duplicated sequential points).
    """
    coords = []
    for (u, v, k) in edge_list:
        edge_data = G.get_edge_data(u, v, k)
        geom = edge_data.get('geometry') if edge_data is not None else None
        if geom is not None and isinstance(geom, LineString):
            pts = [(pt[1], pt[0]) for pt in geom.coords]  # shapely coords are (x,lng),(y,lat) -> convert to (lat,lng)
        else:
            # fallback: use node coordinates
            u_pt = (G.nodes[u]['y'], G.nodes[u]['x'])
            v_pt = (G.nodes[v]['y'], G.nodes[v]['x'])
            pts = [u_pt, v_pt]

        # append while avoiding duplicates
        if not coords:
            coords.extend(pts)
        else:
            # if the last appended point equals first point of this edge, skip it
            if coords[-1] == pts[0]:
                coords.extend(pts[1:])
            else:
                coords.extend(pts)
    return coords


def resample_line_coords(coords: List[Tuple[float, float]], spacing_m: float = 10.0) -> List[Tuple[float, float]]:
    """Resample a polyline given as lat/lng pairs to approximately every spacing_m meters.
    Approach: convert lat/lng to a local Euclidean projection using ox.projection.project_geometry,
    then interpolate along the merged LineString, then project back.
    """
    if len(coords) < 2:
        return coords

    # build LineString in (lng, lat) for shapely
    line = LineString([(lng, lat) for lat, lng in coords])

    # project to UTM / local CRS for metric distances
    proj_line, crs = ox.projection.project_geometry(line)

    length_m = proj_line.length
    if length_m == 0:
        return coords

    # create points every spacing_m
    distances = list(frange(0.0, length_m, spacing_m))
    if distances[-1] < length_m:
        distances.append(length_m)

    resampled = []
    for d in distances:
        p = proj_line.interpolate(d)
        # project back to lat/lng
        unproj = ox.projection.project_geometry(p, crs=crs, to_latlong=True)[0]
        # unproj is a shapely Point with x=lng, y=lat
        resampled.append((unproj.y, unproj.x))

    return resampled


def frange(start: float, stop: float, step: float):
    """Floating point range generator (inclusive of start, exclusive of stop unless exact)."""
    x = start
    while x < stop:
        yield x
        x += step


def compute_loop_route(points: List[Tuple[float, float]], mode: str = 'drive', resample_m: float = 10.0,
                       graph_buffer_m: int = 2000) -> Dict:
    """Compute the full loop A->B->C->...->A for the given mode. Return dict with coords, polyline, distance_km, duration_min."""
    if len(points) < 2:
        raise ValueError("At least two points are required to compute a route.")

    # Build a graph that covers all points
    G = build_graph_for_mode(points, mode=mode, buffer_m=graph_buffer_m)

    # iterate over sequential pairs including final->first
    full_coords = []
    total_m = 0.0
    for i in range(len(points)):
        a = points[i]
        b = points[(i + 1) % len(points)]  # wraps back to 0

        _, edge_list = route_nodes_and_edges(G, a, b)
        seg_coords = edges_to_coords(G, edge_list)

        if not seg_coords:
            # if no geometry returned for the segment, skip
            continue

        # Append segment coords into full_coords with dedupe
        if not full_coords:
            full_coords.extend(seg_coords)
        else:
            # avoid duplicate of connecting point
            if full_coords[-1] == seg_coords[0]:
                full_coords.extend(seg_coords[1:])
            else:
                full_coords.extend(seg_coords)

        # add segment length via edge lengths
        seg_length = 0.0
        for u, v, k in edge_list:
            edge_data = G.get_edge_data(u, v, k)
            seg_length += edge_data.get('length', 0.0)
        total_m += seg_length

    # merge and resample
    if len(full_coords) < 2:
        raise RuntimeError("Failed to build route geometry.")

    resampled = resample_line_coords(full_coords, spacing_m=resample_m)

    # compute estimated duration using simple speeds (user can refine)
    distance_km = total_m / 1000.0
    speed_kmh = {'drive': 30.0, 'bike': 15.0, 'walk': 5.0}.get(mode, 30.0)
    duration_min = (distance_km / speed_kmh) * 60.0 if speed_kmh > 0 else None

    # encode polyline (polyline library expects list of (lat,lng))
    encoded = polyline.encode(resampled, precision=5)

    return {
        'coords': resampled,
        'polyline': encoded,
        'distance_km': distance_km,
        'duration_min': duration_min
    }


# ---- CLI via click ----
@click.command()
@click.option('--input-file', '-f', type=click.Path(exists=True), required=False,
              help='Path to JSON file containing an array of points [{"lat":...,"lng":...}, ...]')
@click.option('--input-json', '-j', type=str, required=False,
              help='JSON string containing an array of points')
@click.option('--resample', '-r', default=10.0, type=float, help='Resample spacing in meters (default 10m)')
@click.option('--modes', '-m', multiple=True, default=['drive', 'bike', 'walk'], help='Transport modes to compute')
@click.option('--buffer', default=2000, type=int, help='Graph buffer in meters around points (default 2000m)')
@click.option('--output-prefix', '-o', default='route', type=str, help='Prefix for output files')
def main(input_file: Optional[str], input_json: Optional[str], resample: float, modes: Tuple[str], buffer: int, output_prefix: str):
    if not input_file and not input_json:
        raise click.UsageError('Either --input-file or --input-json must be provided')

    if input_file:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    else:
        data = json.loads(input_json)

    # data should be array of {lat,lng}
    points = [(float(p['lat']), float(p['lng'])) for p in data]

    out = {}
    for mode in modes:
        try:
            print(f"Computing mode: {mode}")
            result = compute_loop_route(points, mode=mode, resample_m=resample, graph_buffer_m=buffer)
            out[mode] = result

            # ---- Write outputs per mode ----
            # 1. JSON file
            json_path = f"{output_prefix}_{mode}.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2)
            print(f"  ✅ Saved JSON: {json_path}")

            # 2. GeoJSON LineString file for easy use in GIS / Mapbox
            geojson = {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "LineString",
                            "coordinates": [[lng, lat] for lat, lng in result['coords']]
                        },
                        "properties": {
                            "mode": mode,
                            "distance_km": result['distance_km'],
                            "duration_min": result['duration_min']
                        }
                    }
                ]
            }
            geojson_path = f"{output_prefix}_{mode}.geojson"
            with open(geojson_path, "w", encoding="utf-8") as f:
                json.dump(geojson, f, indent=2)
            print(f"  ✅ Saved GeoJSON: {geojson_path}")

        except Exception as e:
            out[mode] = {'error': str(e)}

    # ---- Combined JSON to stdout ----
    print(json.dumps(out, indent=2))


if __name__ == '__main__':
    main()
