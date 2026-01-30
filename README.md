# RouteLooper Backend

## Overview

RouteLooper Backend powers a mobile application that generates looped routes for running, cycling, or driving.

Given a start location and optional intermediate waypoints, the service generates routes that:

- Start and end at the same point (looped), or pass through defined waypoints
- Match a target distance
- Follow roads and paths appropriate for the selected transport mode
- Include elevation data and estimated travel time

Each generated route is returned as:
- A list of latitude/longitude/elevation points
- A downloadable GPX file
- A shareable Google Maps navigation link

The backend is built using FastAPI, with GraphHopper used as the routing engine. The service is currently deployed on Microsoft Azure.

## Architecture

The backend consists of two main components:

### FastAPI Service

- Exposes a REST API for route generation
- Handles authentication, rate limiting, and request validation
- Orchestrates route generation via GraphHopper
- Serves generated GPX files as static assets

### GraphHopper

- Provides routing, distance calculation, and elevation data
- Uses OpenStreetMap data
- Runs as a separate Docker container
- The FastAPI service communicates with GraphHopper over HTTP.


## API Endpoints

### `POST /generate-route`
Generates a custom route based on waypoints, distance, and transport mode.

#### Authentication
Requires an X-API-Key header. Requests are rate-limited per API key.

#### Request Body
```json
{ 
  "waypoints": [[51.5074, -0.1278]],
  "profile": "foot",
  "target_distance_m": 5000,
  "loop": true
}
```
#### Parameters
- waypoints – List of [latitude, longitude] pairs
- profile – Routing mode: car, bike, or foot
- target_distance_m – Target route length in metres
- loop – Whether the route should return to the starting point

### Response
```json
{
  "route": [[51.5074, -0.1278, 35.2],...],
  "distance_m": 5023.4,
  "duration_s": 1830,
  "elevation_gain_m": 72.5,
  "elevation_loss_m": 70.1,
  "gpx_file_url": "/gpx/route_abc123.gpx",
  "gmaps_url": "https://maps.google.com/…",
  "network_type": "foot"
}
```

## Security & Limits

- API key authentication using the X-API-Key header
- Per-key rate limiting (configurable via environment variables)
- Maximum request size enforcement
- Security headers applied to all responses
- CORS enabled (currently permissive)


## Local Development

### Start FastAPI Locally
```commandline
1. cd fastapi-app
2. uvicorn main:app --host 0.0.0.0 --port 8000 --reload 
```  

### Build & Push FastAPI Image (Azure)
```commandline
1. az acr login --name \<registry name>
2. cd fastapi-app
3. docker build -t fastapi:latest . 
4. docker tag fastapi:latest \<registry name>.azurecr.io/\<azure repository name>:latest
5. docker push \<registry name>.azurecr.io/\<azure repository name>:latest
```

### Run GraphHopper Locally
```commandline
docker run -it --rm `
  -v ./graphhopperdata:/data `
  -e JAVA_OPTS="-Xmx10g -Xms10g"  `
  -p 8989:8989  `
  israelhikingmap/graphhopper:latest  `
  -c /data/config.yml `
  -i /data/osm/britain-and-ireland-251126.osm.pbf `
  -o /data/graph-cache `
```


