# Useful Commands

## FastAPI local start command 
1. cd fastapi-app
2. uvicorn main:app --host 0.0.0.0 --port 8000 --reload   

# FastAPI build and push
1. az acr login --name \<registry name>
2. cd fastapi-app
3. docker build -t fastapi:latest . 
4. docker tag fastapi:latest \<registry name>.azurecr.io/\<azure repository name>:latest
5. docker push \<registry name>.azurecr.io/\<azure repository name>:latest

## Graphhopper local host command
<pre>docker run -it --rm `
  -v ./graphhopperdata:/data `
  -e JAVA_OPTS="-Xmx10g -Xms10g"  `
  -p 8989:8989  `
  israelhikingmap/graphhopper:latest  `
  -c /data/config.yml `
  -i /data/osm/britain-and-ireland-251126.osm.pbf `
  -o /data/graph-cache `
</pre>


### Graphhopper endpoints
spt : http://localhost:8989/spt?profile=car&point=51.8940,-2.0786&distance_limit=30000
routing : http://localhost:8989/route?point=51.8940,-2.0786&point=51.9040,-2.0796&profile=car



