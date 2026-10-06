class AdaptiveSignalOptimizer:
    def __init__(self, min_green=3, max_green=8):
        self.min_green = min_green
        self.max_green = max_green

    def choose_lane(self, intersection):
        for lane in intersection.lanes.values():
            if any(vehicle.emergency for vehicle in lane.vehicles):
                return lane.lane_id

        lane = intersection.get_lane_with_longest_queue()
        return lane.lane_id if lane else None

    def calculate_green_duration(self, lane):
        return min(self.min_green + lane.size(), self.max_green)

    def optimize(self, intersection):
        lane_id = self.choose_lane(intersection)
        if lane_id is None:
            return None, 0
        return lane_id, self.calculate_green_duration(intersection.get_lane(lane_id))
