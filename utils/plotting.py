import osmnx as ox
import matplotlib.pyplot as plt


def plot_route(graph, route_nodes):
    fig, ax = ox.plot_graph_route(graph, route_nodes, route_linewidth=3, node_size=0, bgcolor='white')
    return fig, ax


def plot_isodistance_points(G, nodes_around_1, nodes_around_2, intersection_nodes, full_route_nodes, route_nodes):
    fig, ax = ox.plot_graph(G, show=False, close=False, bgcolor='white', node_size=0)

    # Plot nodes around first point
    x1 = [G.nodes[n]['x'] for n in nodes_around_1]
    y1 = [G.nodes[n]['y'] for n in nodes_around_1]
    ax.scatter(x1, y1, c='blue', s=10, label='Isodistance ring 1', alpha=0.6)

    # Plot nodes around second point
    x2 = [G.nodes[n]['x'] for n in nodes_around_2]
    y2 = [G.nodes[n]['y'] for n in nodes_around_2]
    ax.scatter(x2, y2, c='green', s=10, label='Isodistance ring 2', alpha=0.6)

    # Plot intersection nodes
    xi = [G.nodes[n]['x'] for n in intersection_nodes]
    yi = [G.nodes[n]['y'] for n in intersection_nodes]
    ax.scatter(xi, yi, c='red', s=25, label='Intersection nodes', zorder=5)

    # Plot route itself
    route_x = [G.nodes[n]['x'] for n in full_route_nodes]
    route_y = [G.nodes[n]['y'] for n in full_route_nodes]
    ax.plot(route_x, route_y, c='black', linewidth=2.5, label='Route path', zorder=6)

    # Plot start/second/third points
    for node, color, label in zip(route_nodes, ['purple', 'orange', 'brown'], ['Start', 'Second', 'Third']):
        ax.scatter(G.nodes[node]['x'], G.nodes[node]['y'], c=color, s=50, label=label, edgecolor='k', zorder=7)

    ax.legend(loc='best')
    plt.show()
