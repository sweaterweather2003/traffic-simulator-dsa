from collections import deque
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
