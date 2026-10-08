import random
from models.vehicle import Vehicle
from data_structures.priority_queue import EmergencyPriorityQueue
from algorithms.signal_optimizer import AdaptiveSignalOptimizer
from simulation.statistics import Statistics
from config import VEHICLE_ARRIVAL_PROBABILITY, EMERGENCY_PROBABILITY, NORMAL_VEHICLES_PER_STEP, FIXED_SIGNAL_DURATION, MIN_GREEN_TIME, MAX_GREEN_TIME

class TrafficSimulator:
    def __init__(self, intersections, graph, adaptive=True):
        self.intersections = intersections
        self.graph = graph
        self.adaptive = adaptive
        self.current_time = 0
        self.statistics = Statistics()
        self.emergency_queue = EmergencyPriorityQueue()
        self.optimizer = AdaptiveSignalOptimizer(MIN_GREEN_TIME, MAX_GREEN_TIME)
        self.total_vehicles_in_system = []

    def generate_vehicle(self, intersection):
        lanes = list(intersection.lanes.values())
        if not lanes:
            return
        lane = random.choice(lanes)
        emergency = random.random() < EMERGENCY_PROBABILITY
        vehicle = Vehicle(self.current_time, lane.source, lane.destination, emergency)
        lane.add_vehicle(vehicle)
        self.statistics.vehicle_created(vehicle)
        if emergency:
            self.emergency_queue.push(vehicle)

    def generate_vehicles(self):
        for intersection in self.intersections.values():
            if random.random() < VEHICLE_ARRIVAL_PROBABILITY:
                self.generate_vehicle(intersection)

    def update_waiting_times(self):
        for intersection in self.intersections.values():
            for lane in intersection.lanes.values():
                lane.increment_waiting_times()

    def select_signal(self, intersection):
        if self.adaptive:
            lane_id, _ = self.optimizer.optimize(intersection)
            if lane_id is not None:
                intersection.set_green_lane(lane_id)
        else:
            lane_ids = list(intersection.lanes)
            if not lane_ids:
                return
            if intersection.current_green_lane in lane_ids:
                current_index = lane_ids.index(intersection.current_green_lane)
            else:
                current_index = -1
            intersection.set_green_lane(lane_ids[(current_index + 1) % len(lane_ids)])

    def process_intersection(self, intersection):
        if intersection.current_green_lane is None or intersection.signal_timer >= FIXED_SIGNAL_DURATION:
            self.select_signal(intersection)

        lane = intersection.get_lane(intersection.current_green_lane)
        if lane is None:
            return

        emergency_vehicle = next((v for v in lane.vehicles if v.emergency), None)
        if emergency_vehicle:
            lane.vehicles.remove(emergency_vehicle)
            emergency_vehicle.passed = True
            self.statistics.vehicle_completed(emergency_vehicle)
            return

        for _ in range(NORMAL_VEHICLES_PER_STEP):
            vehicle = lane.remove_vehicle()
            if vehicle is None:
                break
            vehicle.passed = True
            self.statistics.vehicle_completed(vehicle)

    def count_vehicles(self):
        return sum(lane.size() for i in self.intersections.values() for lane in i.lanes.values())

    def run(self, steps):
        print("\n" + "=" * 60)
        print("          TRAFFIC SIMULATION STARTED")
        print("=" * 60)

        for step in range(steps):
            self.current_time = step
            print(f"\n--- Simulation Step {step + 1} ---")
            self.generate_vehicles()
            self.update_waiting_times()

            for intersection in self.intersections.values():
                self.process_intersection(intersection)
                intersection.increment_signal_timer()

            self.total_vehicles_in_system.append(self.count_vehicles())
            self.display_status()

        print("\n" + "=" * 60)
        print("          TRAFFIC SIMULATION FINISHED")
        print("=" * 60)
        self.statistics.display()

    def display_status(self):
        for intersection in self.intersections.values():
            print(f"Intersection {intersection.intersection_id} | Green lane: {intersection.current_green_lane}")
            for lane in intersection.lanes.values():
                print(f"  Lane {lane.lane_id}: {lane.size()} vehicles")
