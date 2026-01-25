import requests
import random
import pandas as pd
import io


def fetch_graphhopper_spt(profile: str, lat: float, lon: float, distance_limit: int = 30000,
                          host: str = "http://localhost:8989") -> pd.DataFrame:
    """
    Fetches Shortest Path Tree (SPT) data from a local GraphHopper server and returns it as a pandas DataFrame.

    Returns:
        pd.DataFrame with columns: ['longitude', 'latitude', 'time', 'distance']
    """
    url = f"{host}/spt"
    params = {
        "profile": profile,
        "point": f"{lat},{lon}",
        "distance_limit": distance_limit
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        text = response.text.strip()
        if not text or not text.startswith("longitude,latitude"):
            print("Unexpected response format or empty result.")
            return pd.DataFrame(columns=["longitude", "latitude", "time", "distance"])

        # Parse CSV directly into DataFrame
        df = pd.read_csv(io.StringIO(text))
        df = df.dropna(subset=["longitude", "latitude"])  # Clean up partial rows if any
        df[["longitude", "latitude"]] = df[["longitude", "latitude"]].astype(float)
        return df.reset_index(drop=True)

    except requests.RequestException as e:
        print(f"Error connecting to GraphHopper server: {e}")
        return pd.DataFrame(columns=["longitude", "latitude", "time", "distance"])


def fetch_graphhopper_route(profile: str,
                            points: list,
                            round_trip: bool = False,
                            round_trip_dist: float | None = None,
                            host: str = "http://localhost:8989") -> dict:
    """
    Fetches a route between multiple points from a local GraphHopper server for a specific transport mode.

    Args:
        round_trip_dist: Target distance for GH round trip algorithm
        round_trip: Enable GH round trip algorithm
        profile (str): The routing profile (e.g., 'car', 'bike', 'foot')
        points (list of tuple): List of (lat, lon) tuples, must contain at least two points
        host (str): Base URL of the GraphHopper instance

    Returns:
        dict containing:
            - 'distance' (m)
            - 'time' (ms)
            - 'ascend' (m)
            - 'descend' (m)
            - 'bbox'
            - 'coordinates' (list of [lon, lat, elevation])
            - 'df' (pandas.DataFrame with columns: ['longitude', 'latitude', 'elevation'])
    """
    if len(points) < 2 and not round_trip:
        raise ValueError("At least two points are required to fetch a route.")

    url = f"{host}/route"

    # Build params dynamically for multiple waypoints
    params = [("profile", profile),
              ("points_encoded", "false"),
              ("elevation", "true"),
              ("instructions", "false")]

    if round_trip:
        rt_params = {
            "algorithm": "round_trip",
            "round_trip.distance": round_trip_dist,
            "round_trip.seed": random.randint(-(2 ** 63), 2 ** 63 - 1),  # random int64 seed each time for round trip
        }

        params.extend(rt_params.items())


    # Add each waypoint as a 'point' parameter
    for lat, lon in points:
        params.append(("point", f"{lat},{lon}"))

    try:
        response = requests.get(url, params=params, timeout=20)
        response.raise_for_status()

        data = response.json()

        if "paths" not in data or not data["paths"]:
            print(f"[{profile}] No route found for given points.")
            return {}

        path = data["paths"][0]
        coords = path["points"]["coordinates"]

        # Convert to DataFrame
        df = pd.DataFrame(coords, columns=["longitude", "latitude", "elevation"])

        print(
            f"[{profile}] Route fetched | Distance: {path['distance']:.1f} m | "
            f"Time: {path['time']/1000:.1f} s | "
            f"Ascend: {path['ascend']:.1f} m | Descend: {path['descend']:.1f} m | "
            f"Waypoints: {len(points)}"
        )

        return {
            "distance": path["distance"],
            "time": path["time"],
            "ascend": path["ascend"],
            "descend": path["descend"],
            "bbox": path.get("bbox"),
            "coordinates": coords,
            "df": df
        }

    except requests.RequestException as e:
        print(f"[{profile}] Error connecting to GraphHopper server: {e}")
        return {}


if __name__ == "__main__":
    # Example usage
    print("Fetching SPT...")
    df_spt = fetch_graphhopper_spt("car", 51.8940, -2.0786, distance_limit=5000)
    print(f"SPT received {len(df_spt)} rows.\n")

    print("Fetching route with waypoints...")
    route = fetch_graphhopper_route("car", points=[
        (51.882172, -1.999488),  # Start
        (51.907393, -2.087897),  # Midpoint / waypoint
        (51.896907, -2.115882)  # End
    ])

    if route:
        print(f"\nFirst 5 route points:\n{route['df'].head()}")