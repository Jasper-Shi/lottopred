from __future__ import annotations

from datetime import date
import numpy as np

from .base import ProbabilityModel, normalize_expected_six
from ..domain import Draw
from ..research_features import rich_number_feature_frame, standardized_signal_scores


class V2StatisticalModel(ProbabilityModel):
    """Conservative multi-factor statistical model.

    V2 combines only weak, shrunk signals. It deliberately avoids optimizing
    coefficients against the 2020-2025 blind period.
    """
    name = "v2_statistical"

    def predict(self, history: list[Draw], target_date: date) -> dict[int, float]:
        if len(history) < 250:
            return {n: 6 / 49 for n in range(1, 50)}
        frame = rich_number_feature_frame(history, target_date)
        score = standardized_signal_scores(frame)
        raw = np.exp(np.clip(score, -1.2, 1.2))
        return normalize_expected_six({int(n): float(v) for n, v in zip(frame.number, raw)})
