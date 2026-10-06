class Vehicle:
    vehicle_counter = 0

    def __init__(self, arrival_time, origin, destination, emergency=False):
        Vehicle.vehicle_counter += 1
        self.vehicle_id = Vehicle.vehicle_counter
        self.arrival_time = arrival_time
        self.origin = origin
        self.destination = destination
        self.emergency = emergency
        self.waiting_time = 0
        self.passed = False

    def increment_waiting_time(self):
        self.waiting_time += 1

    def __repr__(self):
        vehicle_type = "EMERGENCY" if self.emergency else "NORMAL"
        return f"Vehicle(id={self.vehicle_id}, type={vehicle_type}, wait={self.waiting_time})"
