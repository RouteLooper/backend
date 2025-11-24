import os
import uuid
from typing import List, Tuple
import gpxpy
import gpxpy.gpx


def create_gpx_file(route_coords: List[Tuple[float, float, float]], output_dir: str = "gpx") -> str:
    """
    Create a GPX file from a list of (lat, lon) tuples and return its file path.
    """

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Create GPX structure
    gpx = gpxpy.gpx.GPX()
    gpx_track = gpxpy.gpx.GPXTrack()
    gpx.tracks.append(gpx_track)
    gpx_segment = gpxpy.gpx.GPXTrackSegment()
    gpx_track.segments.append(gpx_segment)

    # Add route and elevation points
    for i, (lat, lon, ele) in enumerate(route_coords):
        gpx_segment.points.append(gpxpy.gpx.GPXTrackPoint(lat, lon, elevation=ele))

    # Generate unique filename
    filename = f"route_{uuid.uuid4().hex[:8]}.gpx"
    filepath = os.path.join(output_dir, filename)

    # Write GPX file
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            xml_data = gpx.to_xml()
            f.write(xml_data)
    except Exception as e:
        raise

    return filepath
