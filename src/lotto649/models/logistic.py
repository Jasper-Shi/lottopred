from __future__ import annotations

from datetime import date
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline

from .base import ProbabilityModel, normalize_expected_six
from ..domain import Draw
from ..features import number_feature_frame

FEATURES = [
    "long_freq", "ema_freq", "gap", "in_prev", "number_scaled",
    "freq_10", "freq_25", "freq_50", "freq_100", "freq_250",
    "seen_last_1", "seen_last_2", "seen_last_3", "seen_last_5",
]


class LogisticNumberModel(ProbabilityModel):
    name = "logistic"

    def __init__(self, training_draws: int = 480, min_samples: int = 300, stride: int = 4):
        self.training_draws = training_draws
        self.min_samples = min_samples
        self.stride = stride
        self._cache_key = None
        self._cache_value = None

    def _training_frame(self, history: list[Draw]) -> tuple[pd.DataFrame, np.ndarray]:
        start = max(80, len(history) - self.training_draws)
        xs = []
        for idx in range(start, len(history), self.stride):
            prior = history[:idx]
            target = history[idx]
            ff = number_feature_frame(prior, target.draw_date.weekday())
            ff["y"] = ff["number"].isin(target.numbers).astype(int)
            xs.append(ff)
        if not xs:
            return pd.DataFrame(), np.array([])
        allf = pd.concat(xs, ignore_index=True)
        return allf[FEATURES], allf["y"].to_numpy()

    def predict(self, history: list[Draw], target_date: date) -> dict[int, float]:
        key = (len(history), history[-1].draw_date if history else None, target_date)
        if self._cache_key == key and self._cache_value is not None:
            return dict(self._cache_value)
        if len(history) < self.min_samples:
            result = {n: 6 / 49 for n in range(1, 50)}
        else:
            X, y = self._training_frame(history)
            if len(X) == 0 or len(np.unique(y)) < 2:
                result = {n: 6 / 49 for n in range(1, 50)}
            else:
                model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=500, C=0.25))
                model.fit(X, y)
                current = number_feature_frame(history, target_date.weekday())
                probs = model.predict_proba(current[FEATURES])[:, 1]
                result = normalize_expected_six({int(n): float(p) for n, p in zip(current.number, probs)})
        self._cache_key, self._cache_value = key, dict(result)
        return result
