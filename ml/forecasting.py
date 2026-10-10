from pathlib import Path

import joblib
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from ml.dataset import aggregate_flow, load_flow_csv, make_supervised
from ml.models import make_model


MODEL_DIR = Path("models_saved")
MODEL_DIR.mkdir(exist_ok=True)


def model_cache_path(path, model_name="random_forest", lookback=12, horizon=1):
    source = Path(path)
    dataset = f"_{source.stem}" if source.suffix.lower() == ".npz" else ""
    return MODEL_DIR / f"{model_name}{dataset}_h{horizon}_lb{lookback}.joblib"


def train(path, model_name="random_forest", lookback=12, horizon=1):
    series = aggregate_flow(load_flow_csv(path))
    features, targets = make_supervised(series, lookback, horizon)
    if len(features) < 10:
        raise ValueError("Not enough traffic history for a chronological train/test split.")

    test_start = max(1, int(0.85 * len(features)))
    if test_start >= len(features):
        test_start = len(features) - 1

    model = make_model(model_name, lookback)
    model.fit(features[:test_start], targets[:test_start])
    test_predictions = model.predict(features[test_start:])
    metrics = {
        "MAE": float(mean_absolute_error(targets[test_start:], test_predictions)),
        "RMSE": float(np.sqrt(mean_squared_error(targets[test_start:], test_predictions))),
        "R2": float(r2_score(targets[test_start:], test_predictions)),
        "train_samples": int(test_start),
        "test_samples": int(len(features) - test_start),
    }

    model.fit(features, targets)
    model_path = model_cache_path(path, model_name, lookback, horizon)
    joblib.dump(model, model_path)
    return model, metrics, model_path


def load_or_train(path,model_name="random_forest",lookback=12,horizon=1):
    p=model_cache_path(path,model_name,lookback,horizon)
    if p.exists():
        model=joblib.load(p)
        estimator=getattr(model,"m",None)
        if hasattr(estimator,"n_jobs"):
            estimator.n_jobs=1
        return model
    return train(path,model_name,lookback,horizon)[0]
