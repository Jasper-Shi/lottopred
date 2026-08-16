from datetime import date

import numpy as np
import pandas as pd
import pytest

from lotto649.domain import Draw
from lotto649.evaluation import binary_log_loss, brier_score
from lotto649.research_diagnostics import (
    FAIR_EXPECTATIONS,
    FAIR_P,
    bootstrap_mean_lift_interval,
    exact_topk_upper_tail,
    fair_constant_scores,
    registered_primary_summary,
    single_draw_topk_pmf,
)


def test_top12_hypergeometric_pmf_is_normalized_with_registered_mean():
    probabilities = single_draw_topk_pmf(12)

    assert probabilities.sum() == pytest.approx(1.0, abs=1e-15)
    assert np.dot(np.arange(7), probabilities) == pytest.approx(
        FAIR_EXPECTATIONS[12], abs=1e-15
    )


def test_exact_upper_tail_matches_one_draw_hypergeometric_probability():
    probabilities = single_draw_topk_pmf(12)

    assert exact_topk_upper_tail(0, 1) == 1.0
    assert exact_topk_upper_tail(6, 1) == pytest.approx(probabilities[6])
    assert exact_topk_upper_tail(7, 1) == 0.0
    assert exact_topk_upper_tail(3, 1) == pytest.approx(probabilities[3:].sum())


def test_exact_upper_tail_matches_small_brute_force_convolution():
    probabilities = single_draw_topk_pmf(12)
    brute_force = np.convolve(probabilities, probabilities)

    assert exact_topk_upper_tail(5, 2) == pytest.approx(brute_force[5:].sum())


def test_registered_bootstrap_is_deterministic_across_chunk_sizes():
    hits = np.array([0, 1, 2, 3, 1, 2, 0, 4], dtype=int)

    first = bootstrap_mean_lift_interval(
        hits, FAIR_EXPECTATIONS[12], resamples=500, chunk_size=17
    )
    second = bootstrap_mean_lift_interval(
        hits, FAIR_EXPECTATIONS[12], resamples=500, chunk_size=128
    )

    assert first == second


def test_fair_constant_scores_match_the_shared_evaluation_functions():
    probabilities = {number: FAIR_P for number in range(1, 50)}
    actual = Draw(date(2020, 1, 1), (1, 8, 17, 24, 35, 49), 2)
    expected_brier, expected_log_loss = fair_constant_scores()

    assert expected_brier == pytest.approx(
        brier_score(probabilities, actual.numbers), abs=1e-15
    )
    assert expected_log_loss == pytest.approx(
        binary_log_loss(probabilities, actual.numbers), abs=1e-15
    )


def test_primary_summary_keeps_registered_exact_test_and_all_secondary_metrics():
    frame = pd.DataFrame(
        {
            "model_name": ["v5_pair_affinity"] * 8,
            "model_version": ["v5.0.0"] * 8,
            "top_6_hits": [0, 1, 1, 2, 0, 1, 0, 1],
            "top_12_hits": [1, 2, 2, 3, 1, 2, 1, 2],
            "top_18_hits": [2, 3, 2, 4, 1, 3, 2, 3],
            "brier_score": [0.108] * 8,
            "log_loss": [0.377] * 8,
            "mean_actual_rank": [24.0] * 8,
        }
    )

    summary = registered_primary_summary(frame, multiplicity_family_size=2)

    assert summary["total_top12_hits"] == 14
    assert summary["primary_top12_lift_vs_theory"] == pytest.approx(
        14 / 8 - FAIR_EXPECTATIONS[12]
    )
    assert summary["primary_holm_adjusted_p"] == pytest.approx(
        min(1.0, 2 * summary["primary_exact_one_sided_p"])
    )
    assert len(summary["primary_bootstrap_95_ci"]) == 2
    assert "top6_lift_vs_theory" in summary
    assert "top18_lift_vs_theory" in summary
    assert "brier_delta_vs_fair" in summary
    assert "log_loss_delta_vs_fair" in summary
