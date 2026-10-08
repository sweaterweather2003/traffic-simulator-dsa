from dataclasses import dataclass
@dataclass
class SimulationResult:
    controller:str; average_wait:float; max_queue:int; throughput:int; stops:int; emergency_wait:float
    def summary(self):return f"Controller: {self.controller}\nAverage wait: {self.average_wait:.2f}\nMaximum queue: {self.max_queue}\nThroughput: {self.throughput}\nStops: {self.stops}\nEmergency wait: {self.emergency_wait:.2f}"
