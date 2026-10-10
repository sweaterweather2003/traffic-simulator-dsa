import csv
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


class SimulationCsvLogger:
    COLUMNS = (
        "run_id",
        "timestamp_utc",
        "step",
        "controller",
        "signal_phase",
        "signal_steps_remaining",
        "arrivals_per_step",
        "vehicles_created",
        "vehicles_served",
        "queue_north",
        "queue_east",
        "queue_south",
        "queue_west",
        "queue_ns",
        "queue_ew",
        "average_wait_steps",
        "maximum_queue",
        "stops",
        "forecast_ns",
        "forecast_ew",
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
                    f"Cannot append simulation data to {self.path}: "
                    "the existing CSV header does not match the simulation log format."
                )

    def start_new_run(self):
        self.run_id = str(uuid4())

    def log_step(self, simulator):
        queues = {
            direction: len(simulator.intersection.lanes[direction])
            for direction in ("N", "E", "S", "W")
        }
        result = simulator.result()
        self.writer.writerow(
            {
                "run_id": self.run_id,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "step": simulator.tick,
                "controller": simulator.controller_name,
                "signal_phase": simulator.phase,
                "signal_steps_remaining": simulator.remaining,
                "arrivals_per_step": simulator.cfg.arrivals_per_step,
                "vehicles_created": simulator.vehicles_created,
                "vehicles_served": simulator.throughput,
                "queue_north": queues["N"],
                "queue_east": queues["E"],
                "queue_south": queues["S"],
                "queue_west": queues["W"],
                "queue_ns": queues["N"] + queues["S"],
                "queue_ew": queues["E"] + queues["W"],
                "average_wait_steps": round(result.average_wait, 4),
                "maximum_queue": simulator.max_queue,
                "stops": simulator.stops,
                "forecast_ns": round(simulator.forecast_values["NS"], 4),
                "forecast_ew": round(simulator.forecast_values["EW"], 4),
            }
        )
        self.file.flush()

    def close(self):
        if not self.file.closed:
            self.file.close()
