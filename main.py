from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import List, Tuple, Literal
import os
from route_generator import generate_custom_route

GRAPHHOPPER_HOST = "http://localhost:8989"

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
gpx_dir = os.path.join(os.getcwd(), "gpx")
os.makedirs(gpx_dir, exist_ok=True)
app.mount("/gpx", StaticFiles(directory=gpx_dir), name="gpx")

# --- Data Models ---
LatLon = Tuple[float, float]
LatLonEle = Tuple[float, float, float]


class RouteRequest(BaseModel):
    waypoints: List[LatLon] = Field(..., description="List of waypoints as [latitude, longitude]")
    profile: Literal["car", "bike", "foot"] = Field(..., description="Routing profile")
    target_distance_m: float = Field(..., description="Target distance in meters")
    loop: bool = Field(True, description="Whether the route should be a loop returning to start")


class RouteResponse(BaseModel):
    route: List[LatLonEle] = Field(..., description="List of route coordinates as (lat, lon, ele)")
    distance_m: float = Field(..., description="Total distance of the route in meters")
    duration_s: float = Field(..., description="Total duration of the route in seconds")
    elevation_gain_m: float = Field(..., description="Total elevation gain in meters")
    elevation_loss_m: float = Field(..., description="Total elevation loss in meters")
    gpx_file_url: str = Field(..., description="URL to download the GPX file")
    gmaps_url: str = Field(..., description="Google Maps URL of the route")
    network_type: str = Field(..., description="Routing profile used")


# --- API Endpoints ---
@app.post("/generate-route", response_model=RouteResponse)
def generate_route_endpoint(req: RouteRequest):
    """
    Generate a looped route starting/ending at start_end_lon_lat, optionally passing waypoints,
    aiming for target_distance_m and using network_type graph.
    """

    # Run the route generator
    try:
        result = generate_custom_route(
            waypoints=req.waypoints,
            profile=req.profile,
            target_distance_m=req.target_distance_m,
            loop=req.loop,
            host=GRAPHHOPPER_HOST
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Route generation failed: {e}")

    # Validate result
    if not isinstance(result, dict) or "route" not in result:
        raise HTTPException(status_code=500, detail="Route generator returned invalid result format")

    # Prepare final response
    response = {
        "route": [(lat, lon, ele) for lat, lon, ele in result["route"]],
        "distance_m": result["distance_m"],
        "duration_s": result["duration_s"],
        "elevation_gain_m": result["elevation_gain_m"],
        "elevation_loss_m": result["elevation_loss_m"],
        "gpx_file_url": result["gpx_file_url"],
        "gmaps_url": result["gmaps_url"],
        "network_type": result["network_type"]
    }

    return response


@app.get("/health")
def health():
    return {"status": "ok"}
