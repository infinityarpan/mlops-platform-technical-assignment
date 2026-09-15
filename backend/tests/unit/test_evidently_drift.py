import uuid
from pathlib import Path

import pandas as pd

from app.services.evidently_drift import compute_drift_score


def _test_dir() -> Path:
    path = Path(__file__).resolve().parent / ".evidently_test" / uuid.uuid4().hex
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_compute_drift_score_with_generated_data(monkeypatch):
    test_dir = _test_dir()
    monkeypatch.setattr("app.services.evidently_drift.settings.drift_data_dir", test_dir)
    score = compute_drift_score("pump-failure-predictor")
    assert 0.0 <= score <= 1.0


def test_compute_drift_score_uses_reference_and_current(monkeypatch):
    test_dir = _test_dir()
    monkeypatch.setattr("app.services.evidently_drift.settings.drift_data_dir", test_dir)
    reference = pd.DataFrame({"sensor_a": [0.1, 0.2, 0.3] * 20, "sensor_b": [1.0, 1.1, 1.2] * 20})
    current = pd.DataFrame({"sensor_a": [5.0, 5.1, 5.2] * 20, "sensor_b": [9.0, 9.1, 9.2] * 20})
    reference.to_csv(test_dir / "shift-model_reference.csv", index=False)
    current.to_csv(test_dir / "shift-model_current.csv", index=False)
    score = compute_drift_score("shift-model")
    assert score > 0.0
