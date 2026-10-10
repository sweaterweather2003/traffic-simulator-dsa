from pathlib import Path

import joblib
import numpy as np
from sklearn.linear_model import SGDRegressor


class OnlineQueueLearner:
    WARMUP_SAMPLES = 8
    SAVE_INTERVAL = 10

    def __init__(self, model_path=None):
        self.model_path = Path(model_path) if model_path else (
            Path(__file__).resolve().parents[1]
            / "models_saved"
            / "interactive_queue_sgd.joblib"
        )
        self.model = SGDRegressor(
            loss="squared_error",
            penalty="l2",
            alpha=0.0005,
            learning_rate="constant",
            eta0=0.01,
            random_state=42,
        )
        self.samples_seen = 0
        self.evaluated_samples = 0
        self.absolute_error_sum = 0.0
        self.trained = False
        self._warmup_features = []
        self._warmup_targets = []

        if self.model_path.exists():
            saved = joblib.load(self.model_path)
            self.model = saved["model"]
            self.samples_seen = saved["samples_seen"]
            self.evaluated_samples = saved["evaluated_samples"]
            self.absolute_error_sum = saved["absolute_error_sum"]
            self.trained = saved["trained"]
            self._warmup_features = saved["warmup_features"]
            self._warmup_targets = saved["warmup_targets"]

    @property
    def mean_absolute_error(self):
        if not self.evaluated_samples:
            return None
        return self.absolute_error_sum / self.evaluated_samples

    def observe(self, features, next_queue, queue_capacity):
        features = np.asarray(features, dtype=float).reshape(1, -1)
        target = float(next_queue) / max(1, queue_capacity)
        self.samples_seen += 1

        if self.trained:
            prediction = float(self.model.predict(features)[0]) * queue_capacity
            self.absolute_error_sum += abs(prediction - next_queue)
            self.evaluated_samples += 1
            self.model.partial_fit(features, np.asarray([target]))
        else:
            self._warmup_features.append(features[0].tolist())
            self._warmup_targets.append(target)
            if len(self._warmup_targets) >= self.WARMUP_SAMPLES:
                self.model.partial_fit(
                    np.asarray(self._warmup_features),
                    np.asarray(self._warmup_targets),
                )
                self._warmup_features.clear()
                self._warmup_targets.clear()
                self.trained = True

        if self.samples_seen % self.SAVE_INTERVAL == 0:
            self.save()

    def predict(self, features, queue_capacity):
        if not self.trained:
            return None
        features = np.asarray(features, dtype=float).reshape(1, -1)
        prediction = float(self.model.predict(features)[0]) * queue_capacity
        return max(0.0, min(float(queue_capacity), prediction))

    def save(self):
        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self.model_path.with_name(self.model_path.name + ".tmp")
        joblib.dump(
            {
                "model": self.model,
                "samples_seen": self.samples_seen,
                "evaluated_samples": self.evaluated_samples,
                "absolute_error_sum": self.absolute_error_sum,
                "trained": self.trained,
                "warmup_features": self._warmup_features,
                "warmup_targets": self._warmup_targets,
            },
            temporary_path,
            compress=3,
        )
        temporary_path.replace(self.model_path)