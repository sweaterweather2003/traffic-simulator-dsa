import heapq
class MaxHeap:
    def __init__(self):self.h=[]
    def push(self,key,value):heapq.heappush(self.h,(-key,value))
    def pop(self):return heapq.heappop(self.h)[1] if self.h else None
    def peek(self):return self.h[0][1] if self.h else None
