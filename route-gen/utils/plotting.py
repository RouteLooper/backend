import osmnx as ox


def plot_route(graph, route_nodes):
    fig, ax = ox.plot_graph_route(graph, route_nodes, route_linewidth=3, node_size=0, bgcolor='white')
    return fig, ax
