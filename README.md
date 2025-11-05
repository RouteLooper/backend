# Valhalla self-host instructions

## Generate config file
docker run --rm -v C:\Users\james\Documents\Python\route-generator\data:/data ghcr.io/valhalla/valhalla:latest valhalla_build_config > C:\Users\james\Documents\Python\route-generator\data\valhalla.json

## Build tiles
docker run -it --rm -v C:\Users\james\Documents\Python\route-generator\data:/data ghcr.io/valhalla/valhalla:latest valhalla_build_tiles -c /data/valhalla.json /data/gloucestershire-251104.osm.pbf

## Start the service
docker run -d -v C:\Users\james\Documents\Python\route-generator\data:/data -p 8002:8002 ghcr.io/valhalla/valhalla:latest valhalla_service /data/valhalla.json 1