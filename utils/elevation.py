import os
import math
import requests
import rasterio
from typing import List, Tuple, Dict
from functools import lru_cache


def _tile_name(lat: float, lon: float) -> str:
    """Return Copernicus tile name like N51E001."""
    ns = "N" if lat >= 0 else "S"
    ew = "E" if lon >= 0 else "W"
    lat_base = math.floor(lat) if lat >= 0 else math.ceil(lat) - 1
    lon_base = math.floor(lon) if lon >= 0 else math.ceil(lon) - 1
    return f"{ns}{abs(int(lat_base)):02d}{ew}{abs(int(lon_base)):03d}"


def _tile_url(lat: float, lon: float) -> str:
    """Return AWS Copernicus DEM tile URL for a given lat/lon."""
    ns = "N" if lat >= 0 else "S"
    ew = "E" if lon >= 0 else "W"
    lat_base = math.floor(lat) if lat >= 0 else math.ceil(lat) - 1
    lon_base = math.floor(lon) if lon >= 0 else math.ceil(lon) - 1
    return (
        f"https://copernicus-dem-30m.s3.amazonaws.com/"
        f"Copernicus_DSM_COG_10_{ns}{abs(lat_base):02d}_00_{ew}{abs(lon_base):03d}_00_DEM/"
        f"Copernicus_DSM_COG_10_{ns}{abs(lat_base):02d}_00_{ew}{abs(lon_base):03d}_00_DEM.tif"
    )


@lru_cache(maxsize=64)
def _open_tile(lat: int, lon: int):
    url = _tile_url(lat, lon)
    try:
        # Tell Rasterio to use HTTP range requests
        return rasterio.open(url)
    except Exception as e:
        print(f"[ERROR] Could not open remote DEM tile: {url} -> {e}")
        return None


def _get_elevation_from_tile(src, lat: float, lon: float) -> float:
    """Return elevation for (lat, lon) if within the tile; else None."""
    if not src:
        return None
    x, y = lon, lat
    # Check bounds
    if not (src.bounds.left <= x <= src.bounds.right and src.bounds.bottom <= y <= src.bounds.top):
        return None
    try:
        val = list(src.sample([(x, y)]))[0][0]
        if val is None or (src.nodata is not None and val == src.nodata):
            return None
        return float(val)
    except Exception:
        return None


def add_elevations_to_coords(coords: List[Tuple[float, float]]) -> List[Tuple[float, float, float]]:
    """Add elevation osm to a list of (lat, lon) coordinates using Copernicus GLO-30."""
    results = []
    for lat, lon in coords:
        lat_base = math.floor(lat) if lat >= 0 else math.ceil(lat) - 1
        lon_base = math.floor(lon) if lon >= 0 else math.ceil(lon) - 1

        src = _open_tile(lat_base, lon_base)
        elev = _get_elevation_from_tile(src, lat, lon)

        # if outside tile or None -> try neighbours
        if elev is None:
            for dlat in [0, 1, -1]:
                for dlon in [0, 1, -1]:
                    if dlat == 0 and dlon == 0:
                        continue
                    neighbour = _open_tile(lat_base + dlat, lon_base + dlon)
                    elev = _get_elevation_from_tile(neighbour, lat, lon)
                    if elev is not None:
                        break
                if elev is not None:
                    break

        if elev is None:
            elev = 0.0  # fallback
        results.append((lat, lon, elev))

    print(f"[DEBUG] Added elevation for {len(results)} points (from cached Copernicus tiles).")
    return results
