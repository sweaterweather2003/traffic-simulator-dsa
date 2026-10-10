from collections import deque


class Lane:
    def __init__(self, direction, capacity=80):
        self.direction = direction
        self.capacity = capacity
        self.queue = deque()

    def enqueue(self, vehicle):
        if len(self.queue) >= self.capacity:
            return False
        self.queue.append(vehicle)
        return True

    def dequeue(self, count=1):
        vehicles = []
        for _ in range(min(count, len(self.queue))):
            vehicles.append(self.queue.popleft())
        return vehicles

    def __len__(self):
        return len(self.queue)

    @property
    def emergency_count(self):
        return sum(vehicle.emergency for vehicle in self.queue)
