from config import *
from network.graph_loader import load_graph
from routing.route_generation import generate_route
from routing.postprocessing import remove_short_out_and_backs, route_length_km
from utils.plotting import plot_route

G = load_graph(start_latlon, radius_km)
route_nodes = generate_route(G, start_latlon, target_distance_km, N)
route_nodes_cleaned = remove_short_out_and_backs(G, route_nodes, min_out_and_back_frac)
plot_route(G, route_nodes_cleaned)
