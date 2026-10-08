from collections import deque
<<<<<<< HEAD
class Lane:
    def __init__(self,direction,capacity=80): self.direction=direction; self.capacity=capacity; self.queue=deque()
    def enqueue(self,v):
        if len(self.queue)>=self.capacity:return False
        self.queue.append(v); return True
    def dequeue(self,count=1):
        out=[]
        for _ in range(min(count,len(self.queue))):out.append(self.queue.popleft())
        return out
    def __len__(self):return len(self.queue)
    @property
    def emergency_count(self):return sum(v.emergency for v in self.queue)
=======

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
>>>>>>> origin/main
