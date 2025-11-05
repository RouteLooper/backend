import random
from routingpy import Valhalla
from shapely.geometry import Polygon, MultiPoint, Point
from shapely.ops import nearest_points
import math
import os
from typing import List, Tuple, Dict, Any
from utils.gmaps_link import generate_gmaps_route_url
from utils.gpx_utils import create_gpx_file
from utils.elevation import add_elevations_to_coords


def haversine_distance(coord1, coord2):
    """Return distance in meters between two (lat, lon) coordinates."""
    R = 6371000
    lat1, lon1 = map(math.radians, coord1)
    lat2, lon2 = map(math.radians, coord2)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def generate_route_api(
        start_end_lon_lat: Tuple[float, float],
        waypoints: List[Tuple[float, float]],
        target_distance_m: float,
        target_elevation_m: float,
        profile: str,
) -> Dict[str, Any]:
    """
    Generates a looped route based on inputs. Returns coordinates, distance, elevation, and Google Maps URL.
    """

    # -------------------------------
    # Configuration
    # -------------------------------
    VALHALLA_URL = "http://localhost:8002"
    client = Valhalla(base_url=VALHALLA_URL)

    # -------------------------------
    # Helper: fetch iso-distance polygon
    # -------------------------------
    def get_isodistance(center, distance_m):
        iso = client.isochrones(
            locations=center,
            profile=profile,
            intervals=[distance_m],
            interval_type="distance",
            polygons=True,
        )
        return Polygon(iso[0].geometry[0])

    # ==================================================================
    # CASE 1: No waypoints → simple circular route
    # ==================================================================
    if not waypoints or len(waypoints) == 0:
        iso_distance = target_distance_m / 3  # meters

        # Iso-distance from start
        poly_start = get_isodistance(start_end_lon_lat, iso_distance)
        boundary_start = poly_start.boundary

        # Randomly pick a point on boundary
        coords = list(boundary_start.coords)
        rand_coord = random.choice(coords)
        rand_point = Point(rand_coord)

        # Iso-distance from that random point
        poly_second = get_isodistance([rand_point.x, rand_point.y], iso_distance)
        boundary_second = poly_second.boundary

        # Intersection
        raw_intersection = boundary_start.intersection(boundary_second)
        points = []
        if not raw_intersection.is_empty:
            for geom in getattr(raw_intersection, 'geoms', [raw_intersection]):
                if geom.geom_type == "Point":
                    points.append(geom)
                elif geom.geom_type == "LineString":
                    points.extend([Point(geom.coords[0]), Point(geom.coords[-1])])
        intersection_points = MultiPoint(points)
        if len(intersection_points.geoms) == 0:
            raise ValueError("No intersection found — try different parameters.")
        intersection_point = random.choice(intersection_points.geoms)

        # Route through: start → rand → intersection → start
        valhalla_route = client.directions(
            locations=[
                start_end_lon_lat,
                [rand_point.x, rand_point.y],
                [intersection_point.x, intersection_point.y],
                start_end_lon_lat,
            ],
            profile=profile,
            units="km",
        )

        # Valhalla gives (lon, lat) → convert to (lat, lon)
        route_coords = [(lat, lon) for lon, lat in valhalla_route.geometry]

        route_url = generate_gmaps_route_url(route_coords, mode=profile)

        # Elevations + GPX
        route_with_elev = add_elevations_to_coords(route_coords)
        gpx_path = create_gpx_file(route_with_elev)
        gpx_file_url = f"/gpx/{os.path.basename(gpx_path)}"

        return {
            "route": route_with_elev,
            "distance_m": valhalla_route.distance,
            "duration_s": valhalla_route.duration,
            "elevation_m": target_elevation_m,
            "google_maps_url": route_url,
            "gpx_file_url": gpx_file_url,
            "metadata": {
                "num_waypoints": 0,
                "network_type": profile,
            },
        }

    # ==================================================================
    # CASE 2: Waypoints provided → staged intersection logic
    # ==================================================================
    else:
        # Build full sequence including start and return
        all_points = [start_end_lon_lat] + waypoints + [start_end_lon_lat]

        # Compute leg distances and proportions
        leg_distances = [
            haversine_distance(all_points[i], all_points[i + 1])
            for i in range(len(all_points) - 1)
        ]
        total_leg_distance = sum(leg_distances)
        proportions = [d / total_leg_distance for d in leg_distances]
        target_leg_distances = [target_distance_m * p for p in proportions]

        intersection_coords = []

        # For each leg between waypoints, find intersection or midpoint fallback
        for i in range(len(leg_distances)):
            pt1 = all_points[i]
            pt2 = all_points[i + 1]
            stage_iso = target_leg_distances[i] / 2

            poly1 = get_isodistance(pt1, stage_iso)
            poly2 = get_isodistance(pt2, stage_iso)

            raw_intersection = poly1.boundary.intersection(poly2.boundary)
            points = []
            if not raw_intersection.is_empty:
                for geom in getattr(raw_intersection, 'geoms', [raw_intersection]):
                    if geom.geom_type == "Point":
                        points.append(geom)
                    elif geom.geom_type == "LineString":
                        points.extend([Point(geom.coords[0]), Point(geom.coords[-1])])
            intersection_points = MultiPoint(points)
            if len(intersection_points.geoms) == 0:
                # fallback: use midpoint
                print(f"No intersection for leg {i}, using midpoint.")
                midpoint = Point(
                    (pt1[0] + pt2[0]) / 2,
                    (pt1[1] + pt2[1]) / 2,
                )
                intersection_coords.append(midpoint)
            else:
                intersection_coords.append(random.choice(intersection_points.geoms))

        # Build ordered coordinate list for route
        route_sequence = [start_end_lon_lat]
        for i, wp in enumerate(waypoints):
            inter = intersection_coords[i]
            route_sequence.append([inter.x, inter.y])
            route_sequence.append(wp)
        # Final intersection before returning
        route_sequence.append([intersection_coords[-1].x, intersection_coords[-1].y])
        route_sequence.append(start_end_lon_lat)

        # Fetch route
        valhalla_route = client.directions(
            locations=route_sequence,
            profile=profile,
            units="km",
            preference="shortest",
        )

        # Convert Valhalla output from (lon, lat) to (lat, lon)
        route_coords = [(lat, lon) for lon, lat in valhalla_route.geometry]
        route_url = generate_gmaps_route_url(route_coords, waypoints, mode=profile)

        route_with_elev = add_elevations_to_coords(route_coords)
        gpx_path = create_gpx_file(route_with_elev)
        gpx_file_url = f"/gpx/{os.path.basename(gpx_path)}"

        return {
            "route": route_with_elev,
            "distance_m": valhalla_route.distance,
            "duration_s": valhalla_route.duration,
            "elevation_m": target_elevation_m,
            "google_maps_url": route_url,
            "gpx_file_url": gpx_file_url,
            "metadata": {
                "num_waypoints": len(waypoints),
                "network_type": profile,
            },
        }
