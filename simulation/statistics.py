class Statistics:
    def __init__(self):
        self.total_vehicles = 0
        self.completed_vehicles = 0
        self.total_waiting_time = 0
        self.emergency_vehicles = 0
        self.completed_emergency = 0
        self.waiting_times = []

    def vehicle_created(self, vehicle):
        self.total_vehicles += 1
        if vehicle.emergency:
            self.emergency_vehicles += 1

    def vehicle_completed(self, vehicle):
        self.completed_vehicles += 1
        self.total_waiting_time += vehicle.waiting_time
        self.waiting_times.append(vehicle.waiting_time)
        if vehicle.emergency:
            self.completed_emergency += 1

    def average_waiting_time(self):
        return self.total_waiting_time / self.completed_vehicles if self.completed_vehicles else 0

    def maximum_waiting_time(self):
        return max(self.waiting_times, default=0)

    def minimum_waiting_time(self):
        return min(self.waiting_times, default=0)

    def display(self):
        print("\n" + "=" * 50)
        print("             SIMULATION RESULTS")
        print("=" * 50)
        print(f"Total vehicles generated : {self.total_vehicles}")
        print(f"Vehicles completed       : {self.completed_vehicles}")
        print(f"Emergency vehicles       : {self.emergency_vehicles}")
        print(f"Emergency vehicles done  : {self.completed_emergency}")
        print(f"Average waiting time     : {self.average_waiting_time():.2f}")
        print(f"Minimum waiting time     : {self.minimum_waiting_time():.2f}")
        print(f"Maximum waiting time     : {self.maximum_waiting_time():.2f}")
        print("=" * 50)
