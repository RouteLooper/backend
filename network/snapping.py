import osmnx as ox


def snap_to_road(G, point):
    node = ox.distance.nearest_nodes(G, point[1], point[0])
    return node, (G.nodes[node]['y'], G.nodes[node]['x'])
