import math
import random

from algorithms.signal_controller import AdaptiveSignalOptimizer
from models.intersection import Intersection
from models.vehicle import Vehicle
from simulation.statistics import SimulationResult


class TrafficSimulator:
    def __init__(self, cfg, forecaster=None):
        self.cfg = cfg
        self.forecaster = forecaster
        self.opt = AdaptiveSignalOptimizer(cfg)
        self.reset()

    def reset(self):
        self.r = random.Random(self.cfg.seed)
        self.intersection = Intersection(capacity=self.cfg.lane_capacity)
        self.phase = "NS"
        self.remaining = self.cfg.fixed_green_steps
        self.tick = 0
        self.vehicle_id = 0
        self.total_wait = 0
        self.emergency_wait = 0
        self.max_queue = 0
        self.throughput = 0
        self.stops = 0
        self.vehicles_created = 0
        self.flow_history = []
        self.forecast_values = {"NS": 0.0, "EW": 0.0}
        self.controller_name = "longest_queue"

    def forecast(self, intersection):
        if self.forecaster is not None:
            model = getattr(self.forecaster, "m", self.forecaster)
            feature_count = int(getattr(model, "n_features_in_", 12))
            flow = (intersection.total_queue("NS") + intersection.total_queue("EW")) / 2
            self.flow_history.append(float(flow))
            history = self.flow_history[-feature_count:]
            features = [0.0] * (feature_count - len(history)) + history
            prediction = float(self.forecaster.predict_online(features))
            ns_queue = intersection.total_queue("NS")
            ew_queue = intersection.total_queue("EW")
            total_queue = ns_queue + ew_queue
            ns_share = ns_queue / total_queue if total_queue else 0.5
            return {"NS": prediction * ns_share, "EW": prediction * (1 - ns_share)}

        return {
            "NS": intersection.total_queue("NS") * 1.1 + self.cfg.arrivals_per_step * 0.5,
            "EW": intersection.total_queue("EW") * 1.1 + self.cfg.arrivals_per_step * 0.5,
        }

    def _sample_arrivals(self):
        expected = max(0.0, float(self.cfg.arrivals_per_step))
        if expected == 0:
            return 0

        threshold = math.exp(-expected)
        product = 1.0
        arrivals = 0
        while product > threshold:
            product *= self.r.random()
            arrivals += 1
        return arrivals - 1

    def step(self, controller_name=None):
        if controller_name is not None:
            self.controller_name = controller_name

        intersection = self.intersection
        for _ in range(self._sample_arrivals()):
            direction = self.r.choice(self.cfg.directions)
            vehicle = Vehicle(
                self.vehicle_id,
                direction,
                self.r.random() < 0.04,
                self.tick,
            )
            if intersection.lanes[direction].enqueue(vehicle):
                self.vehicles_created += 1
            self.vehicle_id += 1

        forecast = self.forecast(intersection)
        self.forecast_values = forecast
        if self.remaining <= 0:
            if self.controller_name == "fixed":
                self.phase = self.opt.opposite(self.phase)
                self.remaining = self.cfg.fixed_green_steps
            elif self.controller_name == "longest_queue":
                self.phase = self.opt.choose_longest_queue(intersection)
                self.remaining = self.opt.green_time(intersection, self.phase, {})
            elif self.controller_name == "max_pressure":
                self.phase = self.opt.choose_max_pressure(intersection)
                self.remaining = self.opt.green_time(intersection, self.phase, {})
            elif self.controller_name == "fpac":
                self.phase = self.opt.choose_fpac(intersection, forecast)
                self.remaining = self.opt.green_time(intersection, self.phase, forecast)
            else:
                raise ValueError(f"Unknown controller: {self.controller_name}")

        for direction in self.opt.dirs(self.phase):
            completed = intersection.lanes[direction].dequeue(1)
            self.throughput += len(completed)

        queue_size = sum(len(intersection.lanes[direction]) for direction in self.cfg.directions)
        self.max_queue = max(self.max_queue, queue_size)
        self.stops += queue_size
        for direction in self.cfg.directions:
            for vehicle in intersection.lanes[direction].queue:
                vehicle.wait_time += 1
                self.total_wait += 1
                self.emergency_wait += int(vehicle.emergency)

        self.remaining -= 1
        self.tick += 1

    def result(self):
        queued = sum(len(lane) for lane in self.intersection.lanes.values())
        return SimulationResult(
            self.controller_name,
            self.total_wait / max(1, self.throughput + queued),
            self.max_queue,
            self.throughput,
            self.stops,
            self.emergency_wait / max(1, self.vehicles_created),
        )

    def run(self, controller_name="fpac"):
        self.reset()
        self.controller_name = controller_name
        for _ in range(self.cfg.steps):
            self.step()
        return self.result()
