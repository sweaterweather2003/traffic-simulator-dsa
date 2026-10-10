import argparse

from config import SimulationConfig
from simulation.traffic_simulator import TrafficSimulator
from utils.display import comparison


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--train-ml", action="store_true")
    parser.add_argument("--compare", action="store_true")
    parser.add_argument("--run-fpac", action="store_true")
    parser.add_argument("--animate", action="store_true", help="Open the interactive Pygame simulation")
    parser.add_argument("--network", action="store_true", help="Run the multi-intersection network simulator")
    parser.add_argument("--train-ppo", action="store_true", help="Train shared-policy PPO for the network")
    parser.add_argument(
        "--train-ppo-current-only",
        action="store_true",
        help="Train a matched PPO ablation without forecast features",
    )
    parser.add_argument("--robustness", action="store_true", help="Evaluate network controllers under changed conditions")
    parser.add_argument(
        "--current-only",
        action="store_true",
        help="Hide forecasts from network controller observations",
    )
    parser.add_argument(
        "--controller",
        choices=["fixed", "longest_queue", "max_pressure", "forecast", "spillback", "ppo"],
        default="spillback",
    )
    parser.add_argument("--timesteps", type=int, default=5_000)
    parser.add_argument("--seeds", type=int, default=3)
    parser.add_argument("--output", help="Optional CSV path for robustness results")
    parser.add_argument("--data")
    parser.add_argument(
        "--model",
        default="random_forest",
        choices=["historical_average", "random_forest", "xgboost"],
    )
    parser.add_argument("--steps", type=int, default=100)
    parser.add_argument("--lookback", type=int, default=12)
    args = parser.parse_args()
    cfg = SimulationConfig(steps=args.steps)

    if args.train_ml:
        from ml.forecasting import train

        _, metrics, path = train(args.data, args.model, args.lookback)
        print("ML metrics:", metrics)
        print("Saved:", path)
        return

    if args.train_ppo and args.train_ppo_current_only:
        parser.error("Choose only one PPO training mode.")
    if (args.train_ppo or args.train_ppo_current_only) and not args.network:
        parser.error("PPO training requires --network")
    if args.train_ppo and args.current_only:
        parser.error("Use --train-ppo-current-only to train without forecast features.")

    if args.network:
        from simulation.network_simulator import NetworkSimulationConfig, NetworkTrafficSimulator

        network_cfg = NetworkSimulationConfig(
            seed=cfg.seed,
            steps=args.steps,
            arrivals_per_step=cfg.arrivals_per_step / 2,
            lane_capacity=cfg.lane_capacity,
            road_capacity=12,
            min_green_steps=cfg.min_green_steps,
            max_green_steps=cfg.max_green_steps,
            forecast_observation=not args.current_only,
        )

        if args.train_ppo or args.train_ppo_current_only:
            from simulation.ppo_controller import (
                CURRENT_ONLY_MODEL_PATH,
                MODEL_PATH,
                train_ppo,
            )

            train_forecast_model = args.train_ppo
            training_config = network_cfg
            model_path = MODEL_PATH
            if args.train_ppo_current_only:
                from dataclasses import replace

                training_config = replace(network_cfg, forecast_observation=False)
                model_path = CURRENT_ONLY_MODEL_PATH
                train_forecast_model = False
            try:
                model_path = train_ppo(training_config, args.timesteps, model_path)
            except KeyboardInterrupt:
                print(
                    "\nPPO training interrupted. A partial checkpoint was saved to "
                    f"{model_path}. It can be evaluated, but train longer before "
                    "drawing research conclusions."
                )
                return
            if train_forecast_model:
                print("Trained PPO with forecast features enabled.")
            else:
                print("Trained current-state-only PPO ablation.")
            print(f"Saved shared-policy PPO model: {model_path}")
            return

        forecaster = None
        sensor_profile = None
        if args.data and not (args.train_ppo or args.train_ppo_current_only):
            from ml.dataset import aggregate_flow, load_flow_csv
            from ml.forecasting import load_or_train

            forecaster = load_or_train(args.data, args.model, args.lookback)
            sensor_profile = aggregate_flow(load_flow_csv(args.data))

        if args.robustness:
            from simulation.robustness import run_robustness_suite, summarize_robustness

            ppo_policy = None
            if args.controller == "ppo":
                from simulation.ppo_controller import (
                    CURRENT_ONLY_MODEL_PATH,
                    MODEL_PATH,
                    load_ppo,
                )

                ppo_policy = load_ppo(
                    CURRENT_ONLY_MODEL_PATH if args.current_only else MODEL_PATH
                )
            output_path = args.output or (
                "results/network_robustness_current_only.csv"
                if args.current_only
                else "results/network_robustness.csv"
            )
            rows = run_robustness_suite(
                network_cfg,
                args.seeds,
                output_path,
                ppo_policy,
                forecaster,
                sensor_profile,
            )
            print(f"Completed {len(rows)} matched scenario runs.")
            print(f"Detailed results saved to: {output_path}")
            print("scenario             controller       wait mean    std   95% CI   avg queue   trip sec   throughput   blocked")
            for row in summarize_robustness(rows):
                wait_ci = row["average_wait_steps_ci95"]
                ci_margin = (wait_ci[1] - wait_ci[0]) / 2 if wait_ci is not None else None
                deviation = row["average_wait_steps_std"]
                deviation_text = f"{deviation:.2f}" if deviation is not None else "n/a"
                ci_text = f"{ci_margin:.2f}" if ci_margin is not None else "n/a"
                print(
                    f"{row['scenario']:<21}{row['controller']:<17}"
                    f"{row['average_wait_steps_mean']:>9.2f}"
                    f"{deviation_text:>8}{ci_text:>9}"
                    f"{row['average_queue_mean']:>12.2f}"
                    f"{row['average_travel_time_steps_mean']:>11.2f}"
                    f"{row['throughput_mean']:>13.1f}"
                    f"{row['spillback_blocked_mean']:>10.1f}"
                )
            return

        simulator = NetworkTrafficSimulator(network_cfg, forecaster, sensor_profile)
        policy = None
        if args.controller == "ppo":
            from simulation.ppo_controller import (
                CURRENT_ONLY_MODEL_PATH,
                MODEL_PATH,
                load_ppo,
            )

            policy = load_ppo(CURRENT_ONLY_MODEL_PATH if args.current_only else MODEL_PATH)
        if args.animate:
            from simulation.network_pygame_viewer import run_network_viewer

            run_network_viewer(simulator, args.controller, policy)
            return
        result = simulator.run(args.controller, policy)
        print(result.summary())
        return

    forecaster = None
    if args.data:
        from ml.forecasting import load_or_train

        forecaster = load_or_train(args.data, args.model, args.lookback)
    if args.animate:
        from simulation.pygame_viewer import run_viewer

        run_viewer(TrafficSimulator(cfg, forecaster))
        return

    if args.compare:
        results = [
            TrafficSimulator(cfg, forecaster).run(controller)
            for controller in ("fixed", "longest_queue", "max_pressure", "fpac")
        ]
        comparison(results)
        return

    result = TrafficSimulator(cfg, forecaster).run(
        "fpac" if args.run_fpac else "longest_queue"
    )
    print(result.summary())


if __name__ == "__main__":
    main()
