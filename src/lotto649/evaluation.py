from __future__ import annotations

import math
import numpy as np

from .domain import Draw, Prediction, hit_count


def brier_score(probabilities: dict[int, float], actual: tuple[int, ...]) -> float:
    y = np.array([1.0 if n in actual else 0.0 for n in range(1, 50)])
    p = np.array([probabilities[n] for n in range(1, 50)])
    return float(np.mean((p - y) ** 2))


def binary_log_loss(probabilities: dict[int, float], actual: tuple[int, ...]) -> float:
    eps = 1e-12
    total = 0.0
    actual_set = set(actual)
    for n in range(1, 50):
        p = min(max(probabilities[n], eps), 1 - eps)
        total -= math.log(p if n in actual_set else 1 - p)
    return total / 49


def mean_actual_rank(probabilities: dict[int, float], actual: tuple[int, ...]) -> float:
    ranked = sorted(probabilities, key=lambda n: (-probabilities[n], n))
    rank = {n: i + 1 for i, n in enumerate(ranked)}
    return float(np.mean([rank[n] for n in actual]))


def evaluate_prediction(pred: Prediction, actual: Draw) -> dict:
    return {
        "target_draw_date": actual.draw_date.isoformat(),
        "model_name": pred.model_name,
        "model_version": pred.model_version,
        "actual": list(actual.numbers),
        "bonus": actual.bonus,
        "final_6_hits": hit_count(pred.final_combination, actual.numbers),
        "top_6_hits": hit_count(pred.top6, actual.numbers),
        "top_12_hits": hit_count(pred.top12, actual.numbers),
        "top_18_hits": hit_count(pred.top18, actual.numbers),
        "matched_final": sorted(set(pred.final_combination) & set(actual.numbers)),
        "brier_score": brier_score(pred.probabilities, actual.numbers),
        "log_loss": binary_log_loss(pred.probabilities, actual.numbers),
        "mean_actual_rank": mean_actual_rank(pred.probabilities, actual.numbers),
    }
