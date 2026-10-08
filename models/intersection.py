from models.lane import Lane
<<<<<<< HEAD
class Intersection:
    def __init__(self,intersection_id="I0",directions=("N","E","S","W"),capacity=80):
        self.intersection_id=intersection_id; self.lanes={d:Lane(d,capacity) for d in directions}; self.current_phase="NS"
    def total_queue(self,phase):return sum(len(self.lanes[d]) for d in (("N","S") if phase=="NS" else ("E","W")))
    def total_emergency(self,phase):return sum(self.lanes[d].emergency_count for d in (("N","S") if phase=="NS" else ("E","W")))
=======

class Intersection:
    def __init__(self, intersection_id):
        self.intersection_id = intersection_id
        self.lanes = {}
        self.current_green_lane = None
        self.signal_timer = 0

    def add_lane(self, lane_id, source, destination):
        self.lanes[lane_id] = Lane(lane_id, source, destination)

    def get_lane(self, lane_id):
        return self.lanes.get(lane_id)

    def get_total_vehicles(self):
        return sum(lane.size() for lane in self.lanes.values())

    def get_lane_with_longest_queue(self):
        return max(self.lanes.values(), key=lambda lane: lane.size(), default=None)

    def set_green_lane(self, lane_id):
        if lane_id in self.lanes:
            self.current_green_lane = lane_id
            self.signal_timer = 0

    def increment_signal_timer(self):
        self.signal_timer += 1

    def __repr__(self):
        return f"Intersection(id={self.intersection_id}, vehicles={self.get_total_vehicles()})"
>>>>>>> origin/main
