from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import numpy as np

from .base import ProbabilityModel
from ..domain import Draw
from ..research_protocol import assert_history_precedes_target


MINIMUM_HISTORY_DRAWS = 300
BLOCK_DRAWS = 104
FEATURE_WINDOW_DRAWS = 2 * BLOCK_DRAWS
FINITE_POPULATION_CORRECTION = 48.0 / 43.0
REGIME_THRESHOLD = 73.68263852010577
ZSCORE_EPSILON = 1.0e-12
SIGNAL_TEMPERATURE = 0.10
JITTER_SEED_BASE = 649_000_000
JITTER_LOW = -1.0e-9
JITTER_HIGH = 1.0e-9


def _main_number_counts(draws: list[Draw]) -> np.ndarray:
    counts = np.zeros(49, dtype=np.int64)
    for draw in draws:
        indices = np.fromiter((number - 1 for number in draw.numbers), dtype=np.int64)
        counts[indices] += 1
    return counts


@dataclass(frozen=True)
class EntropyRegimeAnalysis:
    older_counts: tuple[int, ...]
    recent_counts: tuple[int, ...]
    adjusted_contributions: tuple[float, ...]
    statistic: float
    directional_scores: tuple[float, ...]
    active: bool


def analyze_entropy_regime(
    history: list[Draw], target_date: date
) -> EntropyRegimeAnalysis:
    if len(history) < MINIMUM_HISTORY_DRAWS:
        raise ValueError(
            f"v6_entropy_regime requires at least {MINIMUM_HISTORY_DRAWS} prior draws"
        )
    assert_history_precedes_target(history, target_date)

    feature_draws = history[-FEATURE_WINDOW_DRAWS:]
    older_counts = _main_number_counts(feature_draws[:BLOCK_DRAWS])
    recent_counts = _main_number_counts(feature_draws[BLOCK_DRAWS:])
    expected = (older_counts + recent_counts) / 2.0

    contributions = np.zeros(49, dtype=float)
    older_mask = older_counts > 0
    recent_mask = recent_counts > 0
    contributions[older_mask] += older_counts[older_mask] * np.log(
        older_counts[older_mask] / expected[older_mask]
    )
    contributions[recent_mask] += recent_counts[recent_mask] * np.log(
        recent_counts[recent_mask] / expected[recent_mask]
    )
    adjusted = FINITE_POPULATION_CORRECTION * 2.0 * contributions
    statistic = float(np.sum(adjusted))
    directional = np.sign(recent_counts - older_counts) * adjusted
    return EntropyRegimeAnalysis(
        older_counts=tuple(int(value) for value in older_counts),
        recent_counts=tuple(int(value) for value in recent_counts),
        adjusted_contributions=tuple(float(value) for value in adjusted),
        statistic=statistic,
        directional_scores=tuple(float(value) for value in directional),
        active=statistic > REGIME_THRESHOLD,
    )


class V6EntropyRegimeModel(ProbabilityModel):
    """Frozen v6.0.0 fixed-boundary entropy-regime candidate."""

    name = "v6_entropy_regime"

    def predict(self, history: list[Draw], target_date: date) -> dict[int, float]:
        analysis = analyze_entropy_regime(history, target_date)
        scores = np.asarray(analysis.directional_scores, dtype=float)
        rng = np.random.default_rng(JITTER_SEED_BASE + target_date.toordinal())
        jitter = rng.uniform(JITTER_LOW, JITTER_HIGH, size=49)
        if analysis.active:
            mean = float(np.mean(scores))
            population_std = float(np.std(scores, ddof=0))
            z_scores = (scores - mean) / (population_std + ZSCORE_EPSILON)
            logits = SIGNAL_TEMPERATURE * z_scores + jitter
        else:
            logits = jitter

        raw = np.exp(logits)
        probabilities = 6.0 * raw / float(np.sum(raw))
        if not np.isfinite(probabilities).all():
            raise RuntimeError("v6_entropy_regime produced non-finite probabilities")
        if np.any(probabilities <= 0.0) or np.any(probabilities >= 1.0):
            raise RuntimeError("v6_entropy_regime violated the probability contract")
        if not np.isclose(float(np.sum(probabilities)), 6.0, rtol=0.0, atol=1e-12):
            raise RuntimeError("v6_entropy_regime probabilities do not sum to six")
        return {number: float(probabilities[number - 1]) for number in range(1, 50)}
