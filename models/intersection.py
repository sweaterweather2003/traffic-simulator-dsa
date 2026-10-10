from models.lane import Lane


class Intersection:
    def __init__(self, intersection_id="I0", directions=("N", "E", "S", "W"), capacity=80):
        self.intersection_id = intersection_id
        self.lanes = {direction: Lane(direction, capacity) for direction in directions}
        self.current_phase = "NS"

    def total_queue(self, phase):
        directions = ("N", "S") if phase == "NS" else ("E", "W")
        return sum(len(self.lanes[direction]) for direction in directions)

    def total_emergency(self, phase):
        directions = ("N", "S") if phase == "NS" else ("E", "W")
        return sum(self.lanes[direction].emergency_count for direction in directions)
