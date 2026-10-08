import heapq
<<<<<<< HEAD
class EmergencyPriorityQueue:
    def __init__(self):self.h=[];self.i=0
    def push(self,vehicle,priority):heapq.heappush(self.h,(-priority,self.i,vehicle));self.i+=1
    def pop(self):return heapq.heappop(self.h)[2] if self.h else None
    def __len__(self):return len(self.h)
=======

class EmergencyPriorityQueue:
    def __init__(self):
        self.heap = []

    def push(self, vehicle):
        priority = 1 if vehicle.emergency else 2
        heapq.heappush(self.heap, (priority, vehicle.arrival_time, vehicle.vehicle_id, vehicle))

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
>>>>>>> origin/main
