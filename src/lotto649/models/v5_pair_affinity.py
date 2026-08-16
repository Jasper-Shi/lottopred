from __future__ import annotations

from datetime import date

import numpy as np

from .base import ProbabilityModel
from ..domain import Draw
from ..research_protocol import assert_history_precedes_target


MINIMUM_HISTORY_DRAWS = 300
PAIR_PRIOR_STRENGTH = 250.0
MARGINAL_PRIOR = 6.0 / 49.0
CONDITIONAL_PAIR_PRIOR = 5.0 / 48.0
ZSCORE_EPSILON = 1.0e-9
SIGNAL_TEMPERATURE = 0.10


class V5PairAffinityModel(ProbabilityModel):
    """Frozen v5.0.0 previous-draw-anchored pair-affinity candidate."""

    name = "v5_pair_affinity"

    def __init__(self) -> None:
        self._cached_history: tuple[Draw, ...] = ()
        self._marginal_counts = np.zeros(49, dtype=np.int64)
        self._pair_counts = np.zeros((49, 49), dtype=np.int64)

    def _add_draw(self, draw: Draw) -> None:
        indices = np.fromiter((number - 1 for number in draw.numbers), dtype=np.int64)
        self._marginal_counts[indices] += 1
        self._pair_counts[np.ix_(indices, indices)] += 1

    def _counts_for(self, history: list[Draw]) -> tuple[np.ndarray, np.ndarray]:
        frozen_history = tuple(history)
        cached_length = len(self._cached_history)
        extends_cache = (
            len(frozen_history) >= cached_length
            and frozen_history[:cached_length] == self._cached_history
        )
        if not extends_cache:
            self._cached_history = ()
            self._marginal_counts.fill(0)
            self._pair_counts.fill(0)
            cached_length = 0

        for draw in frozen_history[cached_length:]:
            self._add_draw(draw)
        self._cached_history = frozen_history
        return self._marginal_counts, self._pair_counts

    def predict(self, history: list[Draw], target_date: date) -> dict[int, float]:
        if len(history) < MINIMUM_HISTORY_DRAWS:
            raise ValueError(
                f"v5_pair_affinity requires at least {MINIMUM_HISTORY_DRAWS} prior draws"
            )
        assert_history_precedes_target(history, target_date)

        marginal_counts, pair_counts = self._counts_for(history)
        draw_count = len(history)
        marginal_probabilities = (
            marginal_counts + PAIR_PRIOR_STRENGTH * MARGINAL_PRIOR
        ) / (draw_count + PAIR_PRIOR_STRENGTH)
        marginal_logits = np.log(marginal_probabilities / (1.0 - marginal_probabilities))

        anchors = tuple(number - 1 for number in history[-1].numbers)
        scores = np.empty(49, dtype=float)
        for candidate in range(49):
            residuals = []
            for anchor in anchors:
                if anchor == candidate:
                    continue
                conditional_probability = (
                    pair_counts[candidate, anchor]
                    + PAIR_PRIOR_STRENGTH * CONDITIONAL_PAIR_PRIOR
                ) / (marginal_counts[anchor] + PAIR_PRIOR_STRENGTH)
                conditional_logit = np.log(
                    conditional_probability / (1.0 - conditional_probability)
                )
                residuals.append(conditional_logit - marginal_logits[candidate])
            scores[candidate] = float(np.mean(residuals))

        mean = float(np.mean(scores))
        population_std = float(np.std(scores, ddof=0))
        z_scores = (scores - mean) / (population_std + ZSCORE_EPSILON)
        raw = np.exp(SIGNAL_TEMPERATURE * z_scores)
        probabilities = 6.0 * raw / float(np.sum(raw))

        if not np.isfinite(probabilities).all():
            raise RuntimeError("v5_pair_affinity produced non-finite probabilities")
        if np.any(probabilities <= 0.0) or np.any(probabilities >= 1.0):
            raise RuntimeError("v5_pair_affinity violated the probability contract")
        if not np.isclose(float(np.sum(probabilities)), 6.0, rtol=0.0, atol=1e-12):
            raise RuntimeError("v5_pair_affinity probabilities do not sum to six")
        return {number: float(probabilities[number - 1]) for number in range(1, 50)}
