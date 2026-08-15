from __future__ import annotations

from datetime import date
import numpy as np

from .base import ProbabilityModel, normalize_expected_six
from ..domain import Draw
from ..features import number_feature_frame, BASE_P


class RandomBaseline(ProbabilityModel):
    name = "random"

    def predict(self, history: list[Draw], target_date: date) -> dict[int, float]:
        return {n: BASE_P for n in range(1, 50)}


class LongFrequencyModel(ProbabilityModel):
    name = "long_frequency"

    def predict(self, history: list[Draw], target_date: date) -> dict[int, float]:
        f = number_feature_frame(history, target_date.weekday())
        strength = 250.0
        scores = {}
        for _, r in f.iterrows():
            count_equiv = r.long_freq * len(history)
            posterior = (count_equiv + strength * BASE_P) / (len(history) + strength)
            scores[int(r.number)] = posterior
        return normalize_expected_six(scores)


class RecentFrequencyModel(ProbabilityModel):
    name = "recent_frequency"

    def __init__(self, window: int = 100):
        self.window = window

    def predict(self, history: list[Draw], target_date: date) -> dict[int, float]:
        f = number_feature_frame(history, target_date.weekday())
        col = f"freq_{self.window}" if f"freq_{self.window}" in f.columns else "freq_100"
        scores = {int(r.number): 0.6 * float(r[col]) + 0.4 * BASE_P for _, r in f.iterrows()}
        return normalize_expected_six(scores)


class EmaGapModel(ProbabilityModel):
    name = "ema_gap"

    def predict(self, history: list[Draw], target_date: date) -> dict[int, float]:
        f = number_feature_frame(history, target_date.weekday())
        gap_z = (f["gap"] - f["gap"].mean()) / (f["gap"].std() + 1e-9)
        ema_z = (f["ema_freq"] - f["ema_freq"].mean()) / (f["ema_freq"].std() + 1e-9)
        raw = np.exp(0.25 * ema_z - 0.05 * gap_z)
        return normalize_expected_six({int(n): float(s) for n, s in zip(f.number, raw)})
