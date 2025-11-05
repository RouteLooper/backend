import random
from routingpy import Valhalla
from shapely.geometry import Polygon, MultiPoint, Point
import folium

# Initialize Valhalla client
client = Valhalla(base_url="http://localhost:8002")

# Coordinates
coord_a = [-2.105674, 51.915820]
coord_b = [-2.056077, 51.907495]

profile = "auto"


def get_isochrone(center):
    iso = client.isochrones(
        locations=center,
        profile=profile,
        intervals=[4000],
        interval_type="distance",
        polygons=True,
    )
    return Polygon(iso[0].geometry[0])


# --- Fetch isochrones ---
poly_a = get_isochrone(coord_a)
poly_b = get_isochrone(coord_b)

# --- Compute boundary intersection ---
boundary_a = poly_a.boundary
boundary_b = poly_b.boundary
raw_intersection = boundary_a.intersection(boundary_b)

# --- Convert intersection to points ---
points = []
if not raw_intersection.is_empty:
    for geom in getattr(raw_intersection, 'geoms', [raw_intersection]):
        if geom.geom_type == "Point":
            points.append(geom)
        elif geom.geom_type == "LineString":
            start_point = Point(geom.coords[0])
            end_point = Point(geom.coords[-1])
            points.extend([start_point, end_point])

boundary_intersection = MultiPoint(points)
print(f"Number of intersection points: {len(boundary_intersection.geoms)}")

# --- Randomly pick one intersection point ---
intersection_point = random.choice(boundary_intersection.geoms)
intersection_coord = [intersection_point.x, intersection_point.y]
print(f"Selected intersection point: {intersection_coord}")

# --- Compute route: A → Intersection → B ---
route = client.directions(
    locations=[coord_a, intersection_coord, coord_b],
    profile=profile,
    units="km",
    preference="shortest",
)

# --- Plot everything using folium ---
center_lat = (coord_a[1] + coord_b[1]) / 2
center_lon = (coord_a[0] + coord_b[0]) / 2
m = folium.Map(location=[center_lat, center_lon], zoom_start=12, tiles="cartodb positron")

# Add isochrones
folium.Polygon(
    locations=[(lat, lon) for lon, lat in poly_a.exterior.coords],
    color="blue", weight=2, fill=False, popup="Isochrone A"
).add_to(m)

folium.Polygon(
    locations=[(lat, lon) for lon, lat in poly_b.exterior.coords],
    color="green", weight=2, fill=False, popup="Isochrone B"
).add_to(m)

# Add boundary intersection points
for pt in boundary_intersection.geoms:
    folium.CircleMarker(
        location=[pt.y, pt.x],
        radius=3,
        color="red",
        fill=True,
        fill_opacity=1
    ).add_to(m)

# Highlight the chosen intersection
folium.CircleMarker(
    location=[intersection_point.y, intersection_point.x],
    radius=5,
    color="orange",
    fill=True,
    fill_opacity=1,
    popup="Selected Intersection"
).add_to(m)

# Add the route line
route_coords = [(lat, lon) for lon, lat in route.geometry]
folium.PolyLine(route_coords, color="purple", weight=4, popup="Route A→Intersection→B").add_to(m)

# Save map
m.save("route_with_isodistances.html")
print("Map saved as route_with_isodistances.html")
