from __future__ import annotations

from datetime import date
import math
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier

from .base import ProbabilityModel, normalize_expected_six
from ..domain import Draw
from ..features import BASE_P
from ..research_protocol import assert_history_precedes_target
from ..research_features import rich_number_feature_frame

FEATURES = [
    "number_scaled", "long_freq", "freq_10", "freq_25", "freq_50", "freq_100", "freq_250",
    "ema_12", "ema_35", "ema_90", "gap", "gap_ratio", "in_prev", "in_prev2",
    "weekday_freq", "month_freq", "transition_freq", "sum_prev_centered",
    "sum_ma5_centered", "sum_ma20_centered", "sum_slope5", "target_weekday",
    "target_month_sin", "target_month_cos",
]


def _require_probability_contract(probabilities: dict[int, float]) -> None:
    if (
        set(probabilities) != set(range(1, 50))
        or any(
            not math.isfinite(probability) or not 0.0 < probability < 1.0
            for probability in probabilities.values()
        )
        or not math.isclose(
            math.fsum(probabilities.values()),
            6.0,
            rel_tol=0.0,
            abs_tol=1.0e-12,
        )
    ):
        raise RuntimeError("V3 probability contract is violated")


class V3BoostingModel(ProbabilityModel):
    name = "v3_boosting"

    def __init__(self, training_draws: int = 420, stride: int = 8, min_history: int = 350):
        self.training_draws = training_draws
        self.stride = stride
        self.min_history = min_history
        self._cache_key = None
        self._cache_value = None

    def _training_frame(self, history: list[Draw]) -> tuple[pd.DataFrame, np.ndarray]:
        start = max(120, len(history) - self.training_draws)
        frames = []
        for idx in range(start, len(history), self.stride):
            prior = history[:idx]
            target = history[idx]
            f = rich_number_feature_frame(prior, target.draw_date)
            f["y"] = f["number"].isin(target.numbers).astype(int)
            frames.append(f)
        if not frames:
            return pd.DataFrame(), np.array([])
        allf = pd.concat(frames, ignore_index=True)
        return allf[FEATURES], allf["y"].to_numpy()

    def predict(self, history: list[Draw], target_date: date) -> dict[int, float]:
        assert_history_precedes_target(history, target_date)
        key = (tuple(history), target_date)
        if self._cache_key == key and self._cache_value is not None:
            return dict(self._cache_value)
        if len(history) < self.min_history:
            result = {n: BASE_P for n in range(1, 50)}
        else:
            X, y = self._training_frame(history)
            if len(X) == 0 or len(np.unique(y)) < 2:
                result = {n: BASE_P for n in range(1, 50)}
            else:
                model = HistGradientBoostingClassifier(
                    learning_rate=0.06,
                    max_iter=45,
                    max_leaf_nodes=15,
                    min_samples_leaf=35,
                    l2_regularization=2.0,
                    random_state=649,
                )
                model.fit(X, y)
                current = rich_number_feature_frame(history, target_date)
                learned = model.predict_proba(current[FEATURES])[:, 1]
                probs = 0.72 * learned + 0.28 * BASE_P
                result = normalize_expected_six({int(n): float(p) for n, p in zip(current.number, probs)})
        _require_probability_contract(result)
        self._cache_key, self._cache_value = key, dict(result)
        return result
