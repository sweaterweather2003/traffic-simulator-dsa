from collections import deque

class Lane:
    def __init__(self, lane_id, source, destination):
        self.lane_id = lane_id
        self.source = source
        self.destination = destination
        self.vehicles = deque()

    def add_vehicle(self, vehicle):
        self.vehicles.append(vehicle)

    def remove_vehicle(self):
        return self.vehicles.popleft() if self.vehicles else None

    def peek(self):
        return self.vehicles[0] if self.vehicles else None

    def size(self):
        return len(self.vehicles)

    def is_empty(self):
        return not self.vehicles

    def increment_waiting_times(self):
        for vehicle in self.vehicles:
            vehicle.increment_waiting_time()

    def __repr__(self):
        return f"Lane({self.source}->{self.destination}, vehicles={self.size()})"
