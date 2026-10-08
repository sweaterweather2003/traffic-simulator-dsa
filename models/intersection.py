from models.lane import Lane
class Intersection:
    def __init__(self,intersection_id="I0",directions=("N","E","S","W"),capacity=80):
        self.intersection_id=intersection_id; self.lanes={d:Lane(d,capacity) for d in directions}; self.current_phase="NS"
    def total_queue(self,phase):return sum(len(self.lanes[d]) for d in (("N","S") if phase=="NS" else ("E","W")))
    def total_emergency(self,phase):return sum(self.lanes[d].emergency_count for d in (("N","S") if phase=="NS" else ("E","W")))
