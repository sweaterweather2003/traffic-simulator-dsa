import unittest
from dataclasses import replace

from data_structures.graph import Graph
from models.vehicle import Vehicle
from simulation.network_simulator import NetworkSimulationConfig, NetworkTrafficSimulator
from simulation.robustness import SCENARIOS, run_robustness_suite, summarize_robustness
from simulation.route_advisor import recommend_routes, steps_to_minutes


class NetworkSimulatorTests(unittest.TestCase):
    def test_graph_supports_both_existing_route_api_shapes(self):
        graph = Graph()
        graph.add_edge("A", "B", 1)
        graph.add_edge("B", "C", 2)

        self.assertEqual(graph.dijkstra("A", "C"), (3, ["A", "B", "C"]))
        self.assertEqual(graph.shortest_path("A", "C"), (["A", "B", "C"], 3))

    def test_route_advisor_avoids_a_congested_alternative(self):
        simulator = NetworkTrafficSimulator(
            NetworkSimulationConfig(arrivals_per_step=0, road_capacity=8)
        )
        for vehicle_id in range(8):
            simulator.queues[("A", "B")].enqueue(
                Vehicle(
                    vehicle_id,
                    "E",
                    destination="D",
                    route=("A", "B", "D"),
                )
            )

        routes = recommend_routes(simulator, "A", "D")

        self.assertEqual(routes[0][0], ("A", "C", "D"))
        self.assertGreater(routes[1][1], routes[0][1])
        self.assertAlmostEqual(steps_to_minutes(60), 1.0)

    def test_vehicles_travel_on_road_before_reaching_signal(self):
        simulator = NetworkTrafficSimulator(
            NetworkSimulationConfig(
                arrivals_per_step=0,
                min_green_steps=8,
                max_green_steps=8,
                clearance_steps=0,
                edge_travel_steps=3,
                approach_travel_steps=3,
            )
        )
        self.assertTrue(simulator.add_vehicle("A", "C"))
        source_lane = simulator.queues[("EXT-N", "A")]
        destination_lane = simulator.queues[("A", "C")]

        simulator.step("fixed", spawn_traffic=False)
        simulator.step("fixed", spawn_traffic=False)
        simulator.step("fixed", spawn_traffic=False)
        self.assertEqual(len(source_lane), 1)
        self.assertEqual(len(destination_lane), 0)

        simulator.step("fixed", spawn_traffic=False)
        self.assertEqual(len(source_lane), 0)
        self.assertEqual(len(destination_lane), 1)

    def test_road_incident_blocks_a_vehicle_and_expires(self):
        simulator = NetworkTrafficSimulator(
            NetworkSimulationConfig(
                arrivals_per_step=0,
                min_green_steps=1,
                max_green_steps=1,
                clearance_steps=0,
                edge_travel_steps=1,
                approach_travel_steps=1,
            )
        )
        self.assertTrue(simulator.add_vehicle("A", "D"))
        simulator.set_incident(("B", "D"), duration_steps=8)

        for _ in range(6):
            simulator.step("fixed", spawn_traffic=False)

        self.assertGreater(simulator.incident_blocked, 0)
        self.assertIn(("B", "D"), simulator.incidents)
        for _ in range(3):
            simulator.step("fixed", spawn_traffic=False)
        self.assertNotIn(("B", "D"), simulator.incidents)

    def test_run_is_deterministic_for_a_fixed_seed(self):
        config = NetworkSimulationConfig(seed=21, steps=40, arrivals_per_step=2)
        first = NetworkTrafficSimulator(config).run("forecast")
        second = NetworkTrafficSimulator(config).run("forecast")

        self.assertEqual(first, second)

    def test_incident_capacity_and_spillback_are_respected(self):
        config = NetworkSimulationConfig(
            seed=123,
            steps=80,
            arrivals_per_step=12,
            lane_capacity=20,
            road_capacity=1,
            incident_edge="A-B",
        )
        simulator = NetworkTrafficSimulator(config)
        result = simulator.run("spillback")

        self.assertGreater(result.spillback_blocked, 0)
        self.assertEqual(simulator.edge_capacity[("A", "B")], 1)
        self.assertEqual(simulator.edge_capacity[("B", "A")], 1)
        for lane in simulator.queues.values():
            self.assertLessEqual(len(lane), lane.capacity)

    def test_signal_changes_include_an_all_red_clearance_step(self):
        config = NetworkSimulationConfig(
            seed=9,
            steps=5,
            arrivals_per_step=0,
            min_green_steps=1,
            max_green_steps=2,
            clearance_steps=1,
        )
        simulator = NetworkTrafficSimulator(config)

        simulator.step("fixed")
        served_before_clearance = simulator.throughput
        simulator.step("fixed")

        self.assertTrue(all(phase == "CLEAR" for phase in simulator.signals.values()))
        self.assertEqual(simulator.throughput, served_before_clearance)
        simulator.step("fixed")
        self.assertTrue(all(phase == "EW" for phase in simulator.signals.values()))

    def test_robustness_suite_covers_each_scenario_and_baseline(self):
        config = NetworkSimulationConfig(steps=8, arrivals_per_step=1)
        rows = run_robustness_suite(config, seeds=1)

        self.assertEqual(len(rows), len(SCENARIOS) * 4)
        self.assertEqual({row["scenario"] for row in rows}, set(SCENARIOS))
        self.assertIn("average_queue", rows[0])
        self.assertIn("average_travel_time_steps", rows[0])
        self.assertEqual(
            {row["controller"] for row in rows},
            {"fixed", "longest_queue", "forecast", "spillback"},
        )

    def test_forecast_features_can_be_disabled_for_controlled_ablation(self):
        full_config = NetworkSimulationConfig(seed=3, arrivals_per_step=5)
        no_forecast_config = replace(full_config, forecast_observation=False)
        full_simulator = NetworkTrafficSimulator(full_config)
        no_forecast_simulator = NetworkTrafficSimulator(no_forecast_config)
        full_observation, _ = full_simulator.step("fixed")
        no_forecast_observation, _ = no_forecast_simulator.step("fixed")

        forecast_feature_positions = [
            node_index * 19 + direction_index * 4 + 3
            for node_index in range(4)
            for direction_index in range(4)
        ]
        self.assertTrue(all(no_forecast_observation[index] == 0 for index in forecast_feature_positions))
        self.assertTrue(any(full_observation[index] != 0 for index in forecast_feature_positions))

    def test_sensor_noise_does_not_change_seeded_arrival_randomness(self):
        base = NetworkSimulationConfig(seed=71, steps=40, arrivals_per_step=2)
        noisy = replace(base, sensor_noise=0.2, missing_sensor_probability=0.25)

        baseline = NetworkTrafficSimulator(base)
        noisy_simulator = NetworkTrafficSimulator(noisy)
        baseline._spawn_arrivals()
        noisy_simulator._spawn_arrivals()
        baseline_arrivals = {
            key: [vehicle.vehicle_id for vehicle in lane.queue]
            for key, lane in baseline.queues.items()
        }
        noisy_arrivals = {
            key: [vehicle.vehicle_id for vehicle in lane.queue]
            for key, lane in noisy_simulator.queues.items()
        }

        self.assertEqual(baseline_arrivals, noisy_arrivals)

    def test_robustness_summary_reports_variation_and_confidence_interval(self):
        rows = [
            {
                "scenario": "nominal",
                "controller": "forecast",
                "average_wait_steps": wait,
                "average_queue": 3.0,
                "average_travel_time_steps": 12.0,
                "throughput": 10,
                "spillback_blocked": 2,
            }
            for wait in (2.0, 4.0, 6.0)
        ]

        summary = summarize_robustness(rows)[0]
        self.assertEqual(summary["average_wait_steps_mean"], 4.0)
        self.assertEqual(summary["average_wait_steps_std"], 2.0)
        self.assertEqual(summary["average_queue_mean"], 3.0)
        self.assertEqual(summary["average_travel_time_steps_mean"], 12.0)
        self.assertIsNotNone(summary["average_wait_steps_ci95"])


if __name__ == "__main__":
    unittest.main()
