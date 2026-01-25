from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import List, Tuple, Literal
import os
import secrets
import time
import asyncio
import httpx
from route_generator import generate_custom_route

GRAPHHOPPER_HOST = os.environ.get("GRAPHHOPPER_HOST", "http://localhost:8989")
API_KEYS = [k for k in os.environ.get("APP_API_KEYS", "").split(",") if k]

RATE_LIMIT_PER_MIN = int(os.environ.get("RATE_LIMIT_PER_MIN", "60"))
RATE_LIMIT_WINDOW = 60
MAX_REQUEST_SIZE = int(os.environ.get("MAX_REQUEST_SIZE", str(1024 * 1024)))

PRIVACY_POLICY_PATH = os.path.join(os.getcwd(), "privacy_policy.html")

app = FastAPI(title="Route Generator API", version="1.0", docs_url=None, redoc_url=None)

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Serve GPX files ---
gpx_dir = os.path.join(os.getcwd(), "gpx")
os.makedirs(gpx_dir, exist_ok=True)
app.mount("/gpx", StaticFiles(directory=gpx_dir), name="gpx")


# --- Security / request size ---
@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    cl = request.headers.get("content-length")
    if cl:
        try:
            if int(cl) > MAX_REQUEST_SIZE:
                return PlainTextResponse("Request too large", status_code=413)
        except ValueError:
            pass
    return await call_next(request)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("Strict-Transport-Security", "max-age=63072000; includeSubDomains; preload")
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Content-Security-Policy",
                                "default-src 'none'; img-src 'self' data:; connect-src 'self'; style-src 'self';")
    return response


# --- Rate limiting ---
_rate_lock = asyncio.Lock()
_rate_state = {}


async def _check_rate_limit(api_key: str):
    now = int(time.time())
    window_start = now - RATE_LIMIT_WINDOW
    async with _rate_lock:
        timestamps = _rate_state.get(api_key, [])
        timestamps = [t for t in timestamps if t > window_start]
        if len(timestamps) >= RATE_LIMIT_PER_MIN:
            _rate_state[api_key] = timestamps
            return False
        timestamps.append(now)
        _rate_state[api_key] = timestamps
        return True


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


# --- Authentication ---
async def verify_api_key(x_api_key: str = Header(None)):
    if not API_KEYS:
        raise HTTPException(status_code=401, detail="No API keys configured on server")
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header")
    ok = any(secrets.compare_digest(x_api_key, k) for k in API_KEYS)
    if not ok:
        raise HTTPException(status_code=403, detail="Invalid API key")
    allowed = await _check_rate_limit(x_api_key)
    if not allowed:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    return x_api_key


# --- Endpoints ---
@app.post("/generate-route", response_model=RouteResponse)
async def generate_route_endpoint(req: RouteRequest, api_key: str = Depends(verify_api_key)):
    print("TEST")
    try:
        result = generate_custom_route(
            waypoints=req.waypoints,
            profile=req.profile,
            target_distance_m=req.target_distance_m,
            loop=req.loop,
            host=GRAPHHOPPER_HOST,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Route generation failed: {e}")
    if not isinstance(result, dict) or "route" not in result:
        raise HTTPException(status_code=500, detail="Route generator returned invalid result format")
    return {
        "route": [(lat, lon, ele) for lat, lon, ele in result["route"]],
        "distance_m": result["distance_m"],
        "duration_s": result["duration_s"],
        "elevation_gain_m": result["elevation_gain_m"],
        "elevation_loss_m": result["elevation_loss_m"],
        "gpx_file_url": result["gpx_file_url"],
        "gmaps_url": result["gmaps_url"],
        "network_type": result["network_type"],
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/probe")
async def probe():
    async def wake_graphhopper():
        url = f"{GRAPHHOPPER_HOST}/health"
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                await client.get(url)
        except Exception:
            pass

    asyncio.create_task(wake_graphhopper())
    return {"status": "ok"}


@app.get("/privacy-policy", response_class=HTMLResponse)
async def privacy_policy():
    with open(PRIVACY_POLICY_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    return HTMLResponse(content=content)


# --- Redirect everything else to privacy policy ---
@app.middleware("http")
async def redirect_to_privacy_policy(request: Request, call_next):
    allowed_paths = ["/probe", "/health", "/generate-route", "/privacy-policy"]

    if not (request.url.path.startswith("/gpx/") or request.url.path in allowed_paths):
        return RedirectResponse(url="/privacy-policy")

    return await call_next(request)
