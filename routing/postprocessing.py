def remove_short_out_and_backs(graph, route_nodes, min_fraction=0.03):
    """
    Remove short out-and-back spurs from route.
    min_fraction: proportion of total route length to treat as 'short'.
    """
    total_len_km = route_length_km(graph, route_nodes)
    min_spur_km = total_len_km * min_fraction

    cleaned = []
    i = 0
    while i < len(route_nodes):
        node = route_nodes[i]
        # Look ahead for same node appearing again
        try:
            j = route_nodes.index(node, i + 1)
        except ValueError:
            cleaned.append(node)
            i += 1
            continue

        # Compute subpath length manually
        sub_len_m = sum(
            graph[u][v][0]['length'] if 0 in graph[u][v] else graph[u][v]['length']
            for u, v in zip(route_nodes[i:j + 1][:-1], route_nodes[i:j + 1][1:])
        )
        sub_len_km = sub_len_m / 1000

        # If subpath is a short out-and-back, skip it
        if sub_len_km < min_spur_km:
            # Jump ahead past the repeated node, effectively removing spur
            i = j
        else:
            cleaned.append(node)
            i += 1

    # Always ensure last node kept
    if cleaned[-1] != route_nodes[-1]:
        cleaned.append(route_nodes[-1])

    print(f"Removed short spurs under {min_spur_km:.2f} km")
    return cleaned


def route_length_km(graph, nodes):
    total_len_m = sum(
        graph[u][v][0]['length'] if 0 in graph[u][v] else graph[u][v]['length']
        for u, v in zip(nodes[:-1], nodes[1:])
    )
    return total_len_m / 1000


def iteratively_clean(G, full_route_nodes, min_out_and_back_frac, target_distance_km, max_iterations):
    prev_len = route_length_km(G, full_route_nodes)
    print(f"Initial route length: {prev_len:.2f} km")

    for i in range(1, max_iterations + 1):
        cleaned = remove_short_out_and_backs(G, full_route_nodes, min_fraction=min_out_and_back_frac)
        new_len = route_length_km(G, cleaned)
        print(f"Iteration {i}: {new_len:.2f} km")

        # Stop if no improvement or below target
        if new_len >= prev_len:
            print("No further reduction — stopping cleanup.")
            break

        full_route_nodes, prev_len = cleaned, new_len

        if new_len <= target_distance_km:
            print("Reached target distance — stopping cleanup.")
            break

    print(f"Final cleaned length: {prev_len:.2f} km (target: {target_distance_km:.2f} km)")

    return full_route_nodes, prev_len
