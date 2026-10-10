import random
from collections import defaultdict, deque
import heapq
from dataclasses import dataclass

from data_structures.graph import Graph
from models.lane import Lane
from models.vehicle import Vehicle


NODE_COORDINATES = {
    "A": (0, 0),
    "B": (1, 0),
    "C": (0, 1),
    "D": (1, 1),
}
DIRECTIONS = ("N", "E", "S", "W")
PHASE_DIRECTIONS = {"NS": ("N", "S"), "EW": ("E", "W")}


@dataclass
class NetworkSimulationConfig:
    seed: int = 42
    steps: int = 300
    arrivals_per_step: float = 3.0
    lane_capacity: int = 12
    road_capacity: int = 8
    min_green_steps: int = 2
    max_green_steps: int = 8
    clearance_steps: int = 1
    emergency_probability: float = 0.02
    demand_multiplier: float = 1.0
    sensor_noise: float = 0.0
    missing_sensor_probability: float = 0.0
    forecast_observation: bool = True
    incident_edge: str | None = None
    incident_capacity_factor: float = 0.25
    nodes: tuple = ("A", "B", "C", "D")
    edges: tuple = (("A", "B"), ("A", "C"), ("B", "D"), ("C", "D"))
    history_window: int = 5
    edge_travel_steps: int = 8
    approach_travel_steps: int = 3


@dataclass
class NetworkResult:
    controller: str
    average_wait: float
    throughput: int
    total_queue: int
    maximum_queue: int
    spillback_blocked: int
    stopped_vehicle_steps: int
    demand_generated: int
    average_travel_time: float
    completed_trips: int
    incident_blocked: int
    average_queue: float

    def summary(self):
        return (
            f"Controller: {self.controller}\n"
            f"Vehicles served: {self.throughput}\n"
            f"Average wait: {self.average_wait:.2f} steps\n"
            f"Final network queue: {self.total_queue}\n"
            f"Average network queue: {self.average_queue:.2f}\n"
            f"Maximum network queue: {self.maximum_queue}\n"
            f"Spillback-blocked movements: {self.spillback_blocked}\n"
            f"Incident-blocked movements: {self.incident_blocked}\n"
            f"Average completed travel time: {self.average_travel_time:.2f} steps\n"
            f"Stopped vehicle-steps: {self.stopped_vehicle_steps}\n"
            f"Vehicles generated: {self.demand_generated}"
        )


class NetworkTrafficSimulator:
    """Four-intersection grid with finite-capacity links and safe two-phase signals."""

    def __init__(self, cfg=None, forecaster=None, sensor_profile=None):
        self.cfg = cfg or NetworkSimulationConfig()
        self.forecaster = forecaster
        self.sensor_profile = [float(value) for value in sensor_profile] if sensor_profile is not None else []
        if not self.cfg.nodes or any(node not in NODE_COORDINATES for node in self.cfg.nodes):
            raise ValueError("Network nodes must be selected from A, B, C, and D.")
        self._validate_config()
        self.graph = Graph()
        self.coordinates = {node: NODE_COORDINATES[node] for node in self.cfg.nodes}
        for source, destination in self.cfg.edges:
            if source not in self.coordinates or destination not in self.coordinates:
                raise ValueError(f"Road edge {source}-{destination} uses an unknown node.")
            self.graph.add_edge(source, destination, 1)
        self._validate_connected_network()
        self.neighbors = {node: [v for v, _ in self.graph.get_neighbors(node)] for node in self.cfg.nodes}
        self.routes = {
            (source, destination): self.graph.shortest_path(source, destination)[0]
            for source in self.cfg.nodes
            for destination in self.cfg.nodes
            if source != destination
        }
        self.edge_capacity = {}
        for source in self.cfg.nodes:
            for destination in self.neighbors[source]:
                capacity = self.cfg.road_capacity
                if self.cfg.incident_edge in (f"{source}-{destination}", f"{destination}-{source}"):
                    capacity = max(1, int(capacity * self.cfg.incident_capacity_factor))
                self.edge_capacity[(source, destination)] = capacity
        self.reset()

    def _validate_config(self):
        if self.cfg.arrivals_per_step < 0:
            raise ValueError("arrivals_per_step must not be negative.")
        if self.cfg.lane_capacity < 1 or self.cfg.road_capacity < 1:
            raise ValueError("Lane and road capacities must be positive.")
        if self.cfg.min_green_steps < 1 or self.cfg.max_green_steps < self.cfg.min_green_steps:
            raise ValueError("Green-time limits are invalid.")
        if self.cfg.clearance_steps < 0:
            raise ValueError("clearance_steps must not be negative.")
        if not 0 <= self.cfg.emergency_probability <= 1:
            raise ValueError("emergency_probability must be between 0 and 1.")
        if not 0 <= self.cfg.missing_sensor_probability <= 1 or self.cfg.sensor_noise < 0:
            raise ValueError("Sensor error settings are invalid.")
        if not 0 < self.cfg.incident_capacity_factor <= 1:
            raise ValueError("incident_capacity_factor must be in (0, 1].")

    def _validate_connected_network(self):
        if len(self.cfg.nodes) < 2:
            raise ValueError("The network must contain at least two intersections.")
        for source in self.cfg.nodes:
            if any(self.graph.dijkstra(source, target)[0] == float("inf") for target in self.cfg.nodes):
                raise ValueError("All configured intersections must be connected by roads.")

    def _direction(self, source, destination):
        x0, y0 = self.coordinates[source]
        x1, y1 = self.coordinates[destination]
        if x0 < x1:
            return "W"
        if x0 > x1:
            return "E"
        if y0 < y1:
            return "N"
        return "S"

    def reset(self):
        self.random = random.Random(self.cfg.seed)
        self.sensor_random = random.Random(self.cfg.seed + 104729)
        self.queues = {}
        self.queue_directions = {}
        self.signals = {node: "NS" for node in self.cfg.nodes}
        self.remaining_green = {node: self.cfg.min_green_steps for node in self.cfg.nodes}
        self.clearance_remaining = {node: 0 for node in self.cfg.nodes}
        self.pending_phase = {node: None for node in self.cfg.nodes}
        self.pending_green = {node: self.cfg.min_green_steps for node in self.cfg.nodes}
        self.arrival_history = defaultdict(lambda: deque(maxlen=self.cfg.history_window))
        self.observation_cache = {}
        self.sensor_history = list(self.sensor_profile[-12:])
        self.tick = 0
        self.next_vehicle_id = 0
        self.vehicles_generated = 0
        self.throughput = 0
        self.total_completed_wait = 0
        self.maximum_queue = 0
        self.spillback_blocked = 0
        self.incident_blocked = 0
        self.incidents = {}
        self.total_completed_travel_time = 0
        self.completed_trips = 0
        self.stopped_vehicle_steps = 0
        self.last_blocked_this_step = 0
        self.last_incident_blocked = 0
        for node in self.cfg.nodes:
            for direction in DIRECTIONS:
                key = (f"EXT-{direction}", node)
                self.queues[key] = Lane(direction, self.cfg.lane_capacity)
                self.queue_directions[key] = direction
            for neighbor in self.neighbors[node]:
                key = (neighbor, node)
                self.queues[key] = Lane(
                    self._direction(neighbor, node),
                    self.edge_capacity[(neighbor, node)],
                )
                self.queue_directions[key] = self._direction(neighbor, node)
        self.lanes_by_node_direction = {
            (node, direction): tuple(
                lane for key, lane in self.queues.items()
                if key[1] == node and self.queue_directions[key] == direction
            )
            for node in self.cfg.nodes
            for direction in DIRECTIONS
        }
        self.incoming_lanes_by_node = {
            node: tuple(
                (key, lane) for key, lane in self.queues.items() if key[1] == node
            )
            for node in self.cfg.nodes
        }
        self.current_forecast = self._forecast_by_lane()
        return self.get_observation()

    def _sample_arrivals(self):
        expected = self.cfg.arrivals_per_step * self.cfg.demand_multiplier
        count = int(expected)
        if self.random.random() < expected - count:
            count += 1
        return count

    def _spawn_arrivals(self):
        arrivals = defaultdict(int)
        for _ in range(self._sample_arrivals()):
            origin = self.random.choice(self.cfg.nodes)
            destination = self.random.choice([node for node in self.cfg.nodes if node != origin])
            route = self.routes[(origin, destination)]
            direction = self._direction(origin, route[1])
            key = (f"EXT-{direction}", origin)
            vehicle = Vehicle(
                self.next_vehicle_id,
                direction,
                self.random.random() < self.cfg.emergency_probability,
                self.tick,
                destination=destination,
                route=tuple(route),
                edge_entry_step=self.tick,
            )
            self.next_vehicle_id += 1
            if self.queues[key].enqueue(vehicle):
                self.vehicles_generated += 1
                arrivals[(origin, direction)] += 1

        for node in self.cfg.nodes:
            for direction in DIRECTIONS:
                self.arrival_history[(node, direction)].append(arrivals[(node, direction)])

    def add_vehicle(self, origin, destination, emergency=False):
        if origin not in self.coordinates or destination not in self.coordinates or origin == destination:
            return False

        distances = {node: float("inf") for node in self.coordinates}
        previous = {}
        distances[origin] = 0
        pending = [(0, origin)]
        while pending:
            distance, node = heapq.heappop(pending)
            if distance != distances[node]:
                continue
            if node == destination:
                break
            for neighbor, weight in self.graph.get_neighbors(node):
                if self.incidents.get((node, neighbor), 0) > 0:
                    continue
                candidate = distance + weight
                if candidate < distances[neighbor]:
                    distances[neighbor] = candidate
                    previous[neighbor] = node
                    heapq.heappush(pending, (candidate, neighbor))

        if distances[destination] == float("inf"):
            return False
        path = [destination]
        while path[-1] != origin:
            path.append(previous[path[-1]])
        path.reverse()

        direction = self._direction(origin, path[1])
        lane = self.queues[(f"EXT-{direction}", origin)]
        if len(lane) >= lane.capacity:
            return False
        vehicle = Vehicle(
            self.next_vehicle_id,
            direction,
            emergency,
            self.tick,
            destination=destination,
            route=tuple(path),
            edge_entry_step=self.tick,
        )
        lane.enqueue(vehicle)
        self.next_vehicle_id += 1
        self.vehicles_generated += 1
        return True

    def set_incident(self, edge, duration_steps=60):
        if not any(neighbor == edge[1] for neighbor, _ in self.graph.get_neighbors(edge[0])):
            raise ValueError("Incident must target a connected road.")
        if duration_steps < 1:
            raise ValueError("Incident duration must be at least one step.")
        self.incidents[edge] = duration_steps
        if any(neighbor == edge[0] for neighbor, _ in self.graph.get_neighbors(edge[1])):
            self.incidents[(edge[1], edge[0])] = duration_steps

    def clear_incident(self, edge):
        self.incidents.pop(edge, None)
        self.incidents.pop((edge[1], edge[0]), None)

    def _sensor_trend_multiplier(self):
        if self.forecaster is None or not self.sensor_history:
            return 1.0
        model = getattr(self.forecaster, "m", self.forecaster)
        feature_count = int(getattr(model, "n_features_in_", 12))
        history = self.sensor_history[-feature_count:]
        features = [0.0] * (feature_count - len(history)) + history
        predicted = float(self.forecaster.predict_online(features))
        last_value = max(abs(self.sensor_history[-1]), 1e-6)
        multiplier = max(0.5, min(1.5, predicted / last_value))
        self.sensor_history.append(predicted)
        return multiplier

    def _forecast_by_lane(self):
        trend = self._sensor_trend_multiplier()
        return {
            (node, direction): (
                sum(history) / len(history) * trend if history else 0.0
            )
            for node in self.cfg.nodes
            for direction in DIRECTIONS
            for history in (self.arrival_history[(node, direction)],)
        }

    def _route_next_hop(self, vehicle, node):
        position = vehicle.route_index
        if position >= len(vehicle.route) or vehicle.route[position] != node:
            raise RuntimeError(
                f"Vehicle {vehicle.vehicle_id} route does not include intersection {node}."
            )
        if position + 1 >= len(vehicle.route):
            return None
        return vehicle.route[position + 1]

    def _lane_free_ratio(self, node, lane):
        if not lane.queue:
            return 1.0
        available = 0
        for vehicle in lane.queue:
            next_hop = self._route_next_hop(vehicle, node)
            if next_hop is None:
                available += 1
                continue
            target_lane = self.queues[(node, next_hop)]
            if len(target_lane) < target_lane.capacity:
                available += 1
        return available / len(lane.queue)

    def _observe(self):
        observations = {}
        values = []
        for node in self.cfg.nodes:
            node_features = {}
            for direction in DIRECTIONS:
                lanes = self.lanes_by_node_direction[(node, direction)]
                queue = sum(len(lane) for lane in lanes)
                waiting = sum(vehicle.wait_time for lane in lanes for vehicle in lane.queue)
                count = sum(len(lane) for lane in lanes)
                capacity = sum(lane.capacity for lane in lanes) or self.cfg.lane_capacity
                free = min((self._lane_free_ratio(node, lane) for lane in lanes if lane.queue), default=1.0)
                expected = (
                    self.current_forecast[(node, direction)]
                    if self.cfg.forecast_observation
                    else 0.0
                )
                raw = {
                    "queue": queue / capacity,
                    "wait": waiting / max(1, count * self.cfg.max_green_steps),
                    "free": free,
                    "forecast": expected / max(1.0, self.cfg.arrivals_per_step),
                }
                observed = {}
                for feature, value in raw.items():
                    cache_key = (node, direction, feature)
                    if self.sensor_random.random() < self.cfg.missing_sensor_probability:
                        value = self.observation_cache.get(cache_key, value)
                    elif self.cfg.sensor_noise:
                        value += self.sensor_random.gauss(0.0, self.cfg.sensor_noise)
                    value = max(0.0, min(1.0, value))
                    self.observation_cache[cache_key] = value
                    observed[feature] = value
                    values.append(value)
                node_features[direction] = observed
            observations[node] = node_features
            values.extend((
                1.0 if self.signals[node] == "NS" else 0.0,
                1.0 if self.signals[node] == "EW" else 0.0,
                self.remaining_green[node] / max(1, self.cfg.max_green_steps),
            ))
        return observations, values

    def get_observation(self):
        return self._observe()[1]

    def _choose_phase(self, node, controller, observed):
        current = self.signals[node]
        if controller == "fixed":
            return ("EW" if current == "NS" else "NS"), self.cfg.min_green_steps

        phase_scores = {}
        for phase, directions in PHASE_DIRECTIONS.items():
            score = 0.0
            for direction in directions:
                lane_observation = observed[node][direction]
                queue = lane_observation["queue"]
                wait = lane_observation["wait"]
                free = lane_observation["free"]
                forecast = lane_observation["forecast"]
                if controller == "longest_queue":
                    score += queue
                elif controller == "max_pressure":
                    score += queue * free
                elif controller == "forecast":
                    score += queue + 0.75 * forecast + 0.15 * wait
                elif controller == "spillback":
                    score += (queue + 0.75 * forecast + 0.5 * wait) * free
                else:
                    raise ValueError(f"Unknown network controller: {controller}")
            phase_scores[phase] = score

        selected = max(phase_scores, key=phase_scores.get)
        green = min(
            self.cfg.max_green_steps,
            max(self.cfg.min_green_steps, self.cfg.min_green_steps + int(phase_scores[selected] * 4)),
        )
        return selected, green

    def step(self, controller="forecast", actions=None, spawn_traffic=True):
        if controller == "ppo" and actions is None:
            raise ValueError("The PPO controller requires one phase action per intersection.")
        if controller not in {"ppo", "fixed", "longest_queue", "max_pressure", "forecast", "spillback"}:
            raise ValueError(f"Unknown network controller: {controller}")

        self.last_blocked_this_step = 0
        self.last_incident_blocked = 0
        if spawn_traffic:
            self._spawn_arrivals()
        self.current_forecast = self._forecast_by_lane()
        observed = None if controller == "ppo" else self._observe()[0]
        if actions is not None and len(actions) != len(self.cfg.nodes):
            raise ValueError("PPO action count must match the number of intersections.")

        for index, node in enumerate(self.cfg.nodes):
            if self.clearance_remaining[node] > 0:
                self.clearance_remaining[node] -= 1
                if self.clearance_remaining[node] == 0:
                    self.signals[node] = self.pending_phase[node]
                    self.remaining_green[node] = self.pending_green[node]
                    self.pending_phase[node] = None
                continue
            if self.remaining_green[node] > 0:
                continue
            if controller == "ppo":
                action_phase = "EW" if int(actions[index]) == 1 else "NS"
                phase = action_phase
                green = self.cfg.min_green_steps
            else:
                phase, green = self._choose_phase(node, controller, observed)
            if phase != self.signals[node] and self.cfg.clearance_steps:
                self.signals[node] = "CLEAR"
                self.clearance_remaining[node] = self.cfg.clearance_steps
                self.pending_phase[node] = phase
                self.pending_green[node] = green
            else:
                self.signals[node] = phase
                self.remaining_green[node] = green

        queue_lengths_before = {key: len(lane) for key, lane in self.queues.items()}
        for node in self.cfg.nodes:
            if self.signals[node] == "CLEAR":
                continue
            allowed = PHASE_DIRECTIONS[self.signals[node]]
            for key, lane in self.incoming_lanes_by_node[node]:
                if self.queue_directions[key] not in allowed:
                    continue
                if queue_lengths_before[key] <= 0:
                    continue
                vehicle = lane.queue[0]
                travel_steps = (
                    self.cfg.approach_travel_steps
                    if key[0].startswith("EXT-")
                    else self.cfg.edge_travel_steps
                )
                if self.tick - vehicle.edge_entry_step < travel_steps:
                    continue
                next_hop = self._route_next_hop(vehicle, node)
                if next_hop is None:
                    lane.dequeue(1)
                    vehicle.completed = True
                    self.throughput += 1
                    self.total_completed_wait += vehicle.wait_time
                    self.total_completed_travel_time += self.tick - vehicle.arrival_step + 1
                    self.completed_trips += 1
                    continue
                if self.incidents.get((node, next_hop), 0) > 0:
                    self.incident_blocked += 1
                    self.last_incident_blocked += 1
                    continue
                downstream = self.queues[(node, next_hop)]
                if len(downstream) >= downstream.capacity:
                    self.spillback_blocked += 1
                    self.last_blocked_this_step += 1
                    continue
                moved_vehicle = lane.dequeue(1)[0]
                moved_vehicle.route_index += 1
                moved_vehicle.edge_entry_step = self.tick
                downstream.enqueue(moved_vehicle)

        queue_size = sum(len(lane) for lane in self.queues.values())
        self.maximum_queue = max(self.maximum_queue, queue_size)
        self.stopped_vehicle_steps += queue_size
        for lane in self.queues.values():
            for vehicle in lane.queue:
                vehicle.wait_time += 1
        for node in self.cfg.nodes:
            if self.signals[node] != "CLEAR":
                self.remaining_green[node] = max(0, self.remaining_green[node] - 1)
        self.incidents = {
            edge: remaining - 1
            for edge, remaining in self.incidents.items()
            if remaining > 1
        }
        self.tick += 1
        return self.get_observation(), self.result()

    def result(self, controller="forecast"):
        queue_size = sum(len(lane) for lane in self.queues.values())
        return NetworkResult(
            controller,
            self.total_completed_wait / max(1, self.throughput),
            self.throughput,
            queue_size,
            self.maximum_queue,
            self.spillback_blocked,
            self.stopped_vehicle_steps,
            self.vehicles_generated,
            self.total_completed_travel_time / max(1, self.completed_trips),
            self.completed_trips,
            self.incident_blocked,
            self.stopped_vehicle_steps / max(1, self.tick),
        )

    def run(self, controller="forecast", policy=None):
        self.reset()
        for _ in range(self.cfg.steps):
            if controller == "ppo":
                if policy is None:
                    raise ValueError("A trained PPO policy is required.")
                action, _ = policy.predict(self.get_observation(), deterministic=True)
                self.step(controller, actions=action)
            else:
                self.step(controller)
        return self.result(controller)
