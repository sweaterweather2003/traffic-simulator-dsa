import heapq

class EmergencyPriorityQueue:
    def __init__(self):
        self.heap = []
        self.sequence = 0

    def push(self, vehicle):
        priority = 0 if vehicle.emergency else 1
        heapq.heappush(
            self.heap,
            (priority, vehicle.arrival_step, self.sequence, vehicle),
        )
        self.sequence += 1

    def pop(self):
        return heapq.heappop(self.heap)[3] if self.heap else None

    def peek(self):
        return self.heap[0][3] if self.heap else None

    def is_empty(self):
        return not self.heap

    def size(self):
        return len(self.heap)

    def clear(self):
        self.heap.clear()
