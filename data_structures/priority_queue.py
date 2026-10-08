import heapq
class EmergencyPriorityQueue:
    def __init__(self):self.h=[];self.i=0
    def push(self,vehicle,priority):heapq.heappush(self.h,(-priority,self.i,vehicle));self.i+=1
    def pop(self):return heapq.heappop(self.h)[2] if self.h else None
    def __len__(self):return len(self.h)
