from simulation.network_simulator import NODE_COORDINATES, PHASE_DIRECTIONS


SECONDS_PER_SIMULATION_STEP = 1


def _signal_delay(simulator, node, next_node):
    x0, y0 = NODE_COORDINATES[node]
    x1, y1 = NODE_COORDINATES[next_node]
    direction = "EW" if x0 != x1 else "NS"
    phase = simulator.signals[node]
    if phase == "CLEAR":
        return simulator.clearance_remaining[node] + simulator.cfg.min_green_steps / 2
    if direction in PHASE_DIRECTIONS[phase]:
        return simulator.remaining_green[node] / 2
    return (
        simulator.remaining_green[node]
        + simulator.cfg.clearance_steps
        + simulator.cfg.min_green_steps / 2
    )


def _estimate_route_steps(simulator, path):
    estimated_steps = 0.0
    for source, destination in zip(path, path[1:]):
        lane = simulator.queues[(source, destination)]
        occupancy = len(lane) / max(1, lane.capacity)
        estimated_steps += simulator.cfg.edge_travel_steps
        estimated_steps += len(lane) * 0.65
        estimated_steps += occupancy * simulator.cfg.max_green_steps
        estimated_steps += _signal_delay(simulator, source, destination)

    if len(path) > 1:
        estimated_steps += _signal_delay(simulator, path[-1], path[-2])
    return estimated_steps


def recommend_routes(simulator, origin, destination):
    if origin == destination:
        return []

    routes = []

    def visit(node, path):
        if node == destination:
            routes.append((tuple(path), _estimate_route_steps(simulator, path)))
            return
        for neighbor, _ in simulator.graph.get_neighbors(node):
            if neighbor not in path and simulator.incidents.get((node, neighbor), 0) <= 0:
                visit(neighbor, path + [neighbor])

    visit(origin, [origin])
    return sorted(routes, key=lambda route: (route[1], route[0]))


def steps_to_minutes(steps):
    return steps * SECONDS_PER_SIMULATION_STEP / 60