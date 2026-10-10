import csv
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


class NetworkCsvLogger:
    COLUMNS = (
        "run_id",
        "timestamp_utc",
        "step",
        "controller",
        "intersection",
        "signal_phase",
        "green_steps_remaining",
        "clearance_steps_remaining",
        "queue_north",
        "queue_east",
        "queue_south",
        "queue_west",
        "forecast_north",
        "forecast_east",
        "forecast_south",
        "forecast_west",
        "network_queue",
        "average_queue",
        "vehicles_generated",
        "vehicles_served",
        "average_wait_steps",
        "average_travel_time_steps",
        "completed_trips",
        "spillback_blocked",
        "incident_blocked",
    )

    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        needs_header = not self.path.exists() or self.path.stat().st_size == 0
        self.file = self.path.open("a", newline="", encoding="utf-8")
        self.writer = csv.DictWriter(self.file, fieldnames=self.COLUMNS)
        self.start_new_run()
        if needs_header:
            self.writer.writeheader()
            self.file.flush()
        else:
            with self.path.open("r", newline="", encoding="utf-8") as existing:
                header = next(csv.reader(existing), [])
            if tuple(header) != self.COLUMNS:
                self.file.close()
                raise ValueError(
                    f"Cannot append network data to {self.path}: "
                    "the existing CSV header does not match the network log format."
                )

    def start_new_run(self):
        self.run_id = str(uuid4())

    def log_step(self, simulator, controller):
        network_queue = sum(len(lane) for lane in simulator.queues.values())
        result = simulator.result(controller)
        timestamp = datetime.now(timezone.utc).isoformat()
        for node in simulator.cfg.nodes:
            queues = {
                direction: sum(
                    len(lane)
                    for key, lane in simulator.queues.items()
                    if key[1] == node and simulator.queue_directions[key] == direction
                )
                for direction in ("N", "E", "S", "W")
            }
            forecasts = {
                direction: simulator.current_forecast[(node, direction)]
                for direction in ("N", "E", "S", "W")
            }
            self.writer.writerow(
                {
                    "run_id": self.run_id,
                    "timestamp_utc": timestamp,
                    "step": simulator.tick,
                    "controller": controller,
                    "intersection": node,
                    "signal_phase": simulator.signals[node],
                    "green_steps_remaining": simulator.remaining_green[node],
                    "clearance_steps_remaining": simulator.clearance_remaining[node],
                    "queue_north": queues["N"],
                    "queue_east": queues["E"],
                    "queue_south": queues["S"],
                    "queue_west": queues["W"],
                    "forecast_north": round(forecasts["N"], 4),
                    "forecast_east": round(forecasts["E"], 4),
                    "forecast_south": round(forecasts["S"], 4),
                    "forecast_west": round(forecasts["W"], 4),
                    "network_queue": network_queue,
                    "average_queue": round(result.average_queue, 4),
                    "vehicles_generated": simulator.vehicles_generated,
                    "vehicles_served": simulator.throughput,
                    "average_wait_steps": round(result.average_wait, 4),
                    "average_travel_time_steps": round(result.average_travel_time, 4),
                    "completed_trips": result.completed_trips,
                    "spillback_blocked": simulator.spillback_blocked,
                    "incident_blocked": simulator.incident_blocked,
                }
            )
        self.file.flush()

    def close(self):
        if not self.file.closed:
            self.file.close()
