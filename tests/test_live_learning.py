import tempfile
import unittest
from pathlib import Path

import numpy as np

from config import SimulationConfig
from ml.dataset import aggregate_flow, load_flow_csv
from ml.forecasting import model_cache_path
from ml.online_learning import OnlineQueueLearner
from simulation.simulator import TrafficSimulator as LegacyTrafficSimulator
from simulation.traffic_simulator import TrafficSimulator


class OnlineQueueLearnerTests(unittest.TestCase):
    def test_legacy_simulator_import_uses_supported_engine(self):
        self.assertIs(LegacyTrafficSimulator, TrafficSimulator)

    def test_pems_npz_loads_flow_channel_not_edge_costs(self):
        archive = np.load("data/PEMS04.npz")
        expected = archive["data"][:, :, 0].mean(axis=1)

        frame = load_flow_csv("data/PEMS04.npz")
        actual = aggregate_flow(frame)

        self.assertEqual(frame.shape, (16992, 307))
        self.assertAlmostEqual(float(actual[0]), float(expected[0]))

    def test_pems_edge_csv_is_rejected_as_training_history(self):
        with self.assertRaisesRegex(ValueError, "road-edge list"):
            load_flow_csv("data/PEMS04.csv")

    def test_pems_model_cache_is_separate_from_legacy_models(self):
        self.assertEqual(
            model_cache_path("data/PEMS04.npz").name,
            "random_forest_PEMS04_h1_lb12.joblib",
        )

    def test_model_trains_and_reloads_saved_state(self):
        with tempfile.TemporaryDirectory() as directory:
            model_path = Path(directory) / "online_model.joblib"
            learner = OnlineQueueLearner(model_path)

            for index in range(16):
                features = [index / 20, 0.1, 0.2, 0.3, 0.2, 1.0, 0.5]
                learner.observe(features, index % 8, queue_capacity=80)

            self.assertTrue(learner.trained)
            self.assertIsNotNone(learner.predict(features, queue_capacity=80))
            self.assertEqual(learner.samples_seen, 16)
            self.assertIsNotNone(learner.mean_absolute_error)
            learner.save()

            restored = OnlineQueueLearner(model_path)
            self.assertTrue(restored.trained)
            self.assertEqual(restored.samples_seen, 16)
            self.assertAlmostEqual(
                restored.predict(features, queue_capacity=80),
                learner.predict(features, queue_capacity=80),
            )

    def test_arrivals_vary_around_configured_mean(self):
        simulator = TrafficSimulator(SimulationConfig(seed=21, arrivals_per_step=4))
        arrivals = [simulator._sample_arrivals() for _ in range(5000)]

        self.assertAlmostEqual(sum(arrivals) / len(arrivals), 4.0, delta=0.15)


if __name__ == "__main__":
    unittest.main()