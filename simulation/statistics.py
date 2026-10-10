from dataclasses import dataclass


@dataclass
class SimulationResult:
    controller: str
    average_wait: float
    max_queue: int
    throughput: int
    stops: int
    emergency_wait: float

    def summary(self):
        return (
            f"Controller: {self.controller}\n"
            f"Average wait: {self.average_wait:.2f}\n"
            f"Maximum queue: {self.max_queue}\n"
            f"Throughput: {self.throughput}\n"
            f"Stops: {self.stops}\n"
            f"Emergency wait: {self.emergency_wait:.2f}"
        )
