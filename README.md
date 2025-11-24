# Start API Command 
uvicorn main:app --host 0.0.0.0 --port 8000 --reload   

# Graphhopper self-host instructions

## Start the container
docker run -it --rm `
  -v "${PWD}/config.yml:/data/config.yml" `
  -v "${PWD}/osm:/data/osm" `
  -v "${PWD}/graph-cache:/data/graph-cache" `
  -v "${PWD}/custom_models:/data/custom_models" `
  -e JAVA_OPTS="-Xmx8g -Xms8g" `
  -p 8989:8989 `
  israelhikingmap/graphhopper:latest `
  -c /data/config.yml -i /data/osm/gloucestershire-251104.osm.pbf -o /data/graph-cache


config.yml has to be perfect for it to work
check hosting: 
  0.0.0.0 - local network
 localhost - within container

spt : http://localhost:8989/spt?profile=car&point=51.8940,-2.0786&distance_limit=30000
routing : http://localhost:8989/route?point=51.8940,-2.0786&point=51.9040,-2.0796&profile=car