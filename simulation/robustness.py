import csv
from dataclasses import replace
from pathlib import Path
from statistics import fmean, stdev

from simulation.network_simulator import NetworkSimulationConfig, NetworkTrafficSimulator


SCENARIOS = {
    "nominal": {},
    "low_demand": {"demand_multiplier": 0.5},
    "peak_demand": {"demand_multiplier": 1.75},
    "noisy_sensors": {"sensor_noise": 0.15},
    "missing_sensors": {"missing_sensor_probability": 0.3},
    "incident_A_B": {"incident_edge": "A-B", "incident_capacity_factor": 0.25},
    "combined_stress": {
        "demand_multiplier": 1.5,
        "sensor_noise": 0.15,
        "missing_sensor_probability": 0.2,
        "incident_edge": "A-B",
        "incident_capacity_factor": 0.25,
    },
}
BASELINE_CONTROLLERS = ("fixed", "longest_queue", "forecast", "spillback")


def run_robustness_suite(
    config=None,
    seeds=3,
    output_path=None,
    ppo_policy=None,
    forecaster=None,
    sensor_profile=None,
):
    base = config or NetworkSimulationConfig()
    controllers = BASELINE_CONTROLLERS + (("ppo",) if ppo_policy is not None else ())
    rows = []
    for scenario, overrides in SCENARIOS.items():
        for seed in range(seeds):
            for controller in controllers:
                scenario_config = replace(base, seed=base.seed + seed, **overrides)
                result = NetworkTrafficSimulator(
                    scenario_config,
                    forecaster=forecaster,
                    sensor_profile=sensor_profile,
                ).run(
                    controller,
                    policy=ppo_policy if controller == "ppo" else None,
                )
                rows.append(
                    {
                        "scenario": scenario,
                        "seed": scenario_config.seed,
                        "controller": controller,
                        "throughput": result.throughput,
                        "average_wait_steps": round(result.average_wait, 4),
                        "final_queue": result.total_queue,
                        "maximum_queue": result.maximum_queue,
                        "average_queue": round(result.average_queue, 4),
                        "average_travel_time_steps": round(result.average_travel_time, 4),
                        "spillback_blocked": result.spillback_blocked,
                        "incident_blocked": result.incident_blocked,
                        "stopped_vehicle_steps": result.stopped_vehicle_steps,
                        "vehicles_generated": result.demand_generated,
                    }
                )

    if output_path is not None:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        columns = tuple(rows[0])
        with path.open("w", newline="", encoding="utf-8") as output:
            writer = csv.DictWriter(output, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)

    return rows


def summarize_robustness(rows):
    grouped = {}
    for row in rows:
        key = (row["scenario"], row["controller"])
        grouped.setdefault(key, []).append(row)

    summaries = []
    for (scenario, controller), samples in sorted(grouped.items()):
        summary = {
            "scenario": scenario,
            "controller": controller,
            "seeds": len(samples),
        }
        for metric in (
            "average_wait_steps",
            "average_queue",
            "average_travel_time_steps",
            "throughput",
            "spillback_blocked",
        ):
            values = [float(sample[metric]) for sample in samples]
            mean = fmean(values)
            deviation = stdev(values) if len(values) > 1 else None
            margin = 1.96 * deviation / (len(values) ** 0.5) if deviation is not None else None
            summary[f"{metric}_mean"] = mean
            summary[f"{metric}_std"] = deviation
            summary[f"{metric}_ci95"] = (
                (mean - margin, mean + margin) if margin is not None else None
            )
        summaries.append(summary)
    return summaries
