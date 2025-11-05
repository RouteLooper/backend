# Valhalla self-host instructions

## Generate config file
docker run --rm -v C:\Users\james\Documents\Python\route-generator\data:/data ghcr.io/valhalla/valhalla:latest valhalla_build_config > C:\Users\james\Documents\Python\route-generator\data\valhalla.json

## Build tiles
docker run -it --rm -v C:\Users\james\Documents\Python\route-generator\data:/data ghcr.io/valhalla/valhalla:latest valhalla_build_tiles -c /data/valhalla.json /data/gloucestershire-251104.osm.pbf

## Start the service
docker run -d -v C:\Users\james\Documents\Python\route-generator\data:/data -p 8002:8002 ghcr.io/valhalla/valhalla:latest valhalla_service /data/valhalla.json 1

# Running server

## Start the server
uvicorn main:app --reload

## /generate-route example input
{
  "start_end_lat_lon": [51.908571, -2.086392],
  "waypoints": [[51.931178, -2.069347], [51.913158, -2.040591]],
  "target_distance_m": 5000,
  "target_elevation_m": 200,
  "profile": "bicycle" # Any of: auto, bicycle, bus, bikeshare, truck, taxi, motor_scooter, motorcycle, multimodal, pedestrian
}