from __future__ import annotations

import itertools
import math


def rank_numbers(probabilities: dict[int, float]) -> list[int]:
    return sorted(probabilities, key=lambda n: (-probabilities[n], n))


def select_combination(probabilities: dict[int, float], candidate_pool_size: int = 12) -> list[int]:
    """Select the maximum independent log-score combination inside the candidate pool.

    V1 intentionally does not force sum, odd/even, or other structural folklore.
    Those constraints are research hypotheses and must first prove out-of-sample value.
    """
    ranked = rank_numbers(probabilities)
    pool = ranked[:candidate_pool_size]
    best, best_score = None, -float("inf")
    for combo in itertools.combinations(pool, 6):
        score = sum(math.log(max(probabilities[n], 1e-12)) for n in combo)
        if score > best_score:
            best, best_score = combo, score
    return sorted(best) if best else sorted(ranked[:6])
