from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import List, Tuple, Optional, Literal
import os
from route_generator import generate_route_api

# --- FastAPI setup ---
app = FastAPI(title="Route Generator API", version="1.0")

# Allow requests from mobile app or frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # change to your app domain(s) in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve GPX files as static files
gpx_dir = os.path.join(os.getcwd(), "generated_gpx")
os.makedirs(gpx_dir, exist_ok=True)
app.mount("/gpx", StaticFiles(directory=gpx_dir), name="gpx")

# --- Data Models ---
LonLat = Tuple[float, float]
LonLatEle = Tuple[float, float, float]


class RouteRequest(BaseModel):
    start_end_lon_lat: LonLat = Field(..., description="Start and end coordinate of looped route (lon, lat)")
    waypoints: Optional[List[LonLat]] = Field(default_factory=list, description="List of waypoints (lon, lat)")
    target_distance_m: float = Field(..., gt=0, description="Target distance in meters")
    target_elevation_m: float = Field(..., ge=0, description="Target total uphill elevation in meters")
    profile: Literal[
        "auto", "bicycle", "bus", "bikeshare", "truck", "taxi", "motor_scooter", "motorcycle", "multimodal", "pedestrian"] = Field(
        "pedestrian", description="Network type: walk, bike, or drive...")


class RouteResponse(BaseModel):
    route: List[LonLatEle]
    distance_km: float
    elevation_m: float
    google_maps_url: str
    gpx_file_url: str
    metadata: Optional[dict]


# --- API Endpoints ---
@app.post("/generate-route", response_model=RouteResponse)
def generate_route_endpoint(req: RouteRequest):
    """
    Generate a looped route starting/ending at start_end_lon_lat, optionally passing waypoints,
    aiming for target_distance_km and target_elevation_m, using network_type graph.
    """

    # Run the route generator
    try:
        result = generate_route_api(
            start_end_lon_lat=req.start_end_lon_lat,
            waypoints=req.waypoints,
            target_distance_m=req.target_distance_m,
            target_elevation_m=req.target_elevation_m,
            profile=req.profile,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Route generation failed: {e}")

    # Validate result
    if not isinstance(result, dict) or "route" not in result:
        raise HTTPException(status_code=500, detail="Route generator returned invalid result format")

    # Prepare final response
    response = {
        "route": result["route"],
        "distance_km": round(result.get("distance_km", 0.0), 3),
        "elevation_m": round(result.get("elevation_m", 0.0), 1),
        "google_maps_url": result.get("google_maps_url", ""),
        "gpx_file_url": result.get("gpx_file_url", ""),
        "metadata": result.get("metadata", {}),
    }

    return response


@app.get("/health")
def health():
    return {"status": "ok"}
