from copy import deepcopy
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pytest

from lotto649.backtest import run_backtest
from lotto649.config import load_config
from lotto649.domain import Draw
from lotto649.models.v5_pair_affinity import (
    CONDITIONAL_PAIR_PRIOR,
    MARGINAL_PRIOR,
    MINIMUM_HISTORY_DRAWS,
    PAIR_PRIOR_STRENGTH,
    SIGNAL_TEMPERATURE,
    ZSCORE_EPSILON,
    V5PairAffinityModel,
)
from lotto649.research_protocol import load_experiment_registry, permute_draw_outcomes


ROOT = Path(__file__).resolve().parents[1]


def synthetic_history(count: int = 330) -> list[Draw]:
    draws = []
    draw_date = date(2010, 1, 2)
    for index in range(count):
        values = []
        cursor = (index * 13 + 5) % 49
        while len(values) < 6:
            number = ((cursor + len(values) * 17) % 49) + 1
            if number not in values:
                values.append(number)
        bonus = next(number for number in range(1, 50) if number not in values)
        draws.append(Draw(draw_date, tuple(values), bonus))
        draw_date += timedelta(days=3)
    return draws


def reference_probabilities(history: list[Draw]) -> dict[int, float]:
    marginal_counts = np.zeros(49, dtype=np.int64)
    pair_counts = np.zeros((49, 49), dtype=np.int64)
    for draw in history:
        indices = np.array([number - 1 for number in draw.numbers], dtype=np.int64)
        marginal_counts[indices] += 1
        pair_counts[np.ix_(indices, indices)] += 1

    marginal = (marginal_counts + PAIR_PRIOR_STRENGTH * MARGINAL_PRIOR) / (
        len(history) + PAIR_PRIOR_STRENGTH
    )
    marginal_logits = np.log(marginal / (1.0 - marginal))
    anchors = [number - 1 for number in history[-1].numbers]
    scores = []
    for candidate in range(49):
        residuals = []
        for anchor in anchors:
            if candidate == anchor:
                continue
            conditional = (
                pair_counts[candidate, anchor]
                + PAIR_PRIOR_STRENGTH * CONDITIONAL_PAIR_PRIOR
            ) / (marginal_counts[anchor] + PAIR_PRIOR_STRENGTH)
            residuals.append(
                np.log(conditional / (1.0 - conditional)) - marginal_logits[candidate]
            )
        scores.append(float(np.mean(residuals)))

    scores_array = np.asarray(scores)
    z_scores = (scores_array - np.mean(scores_array)) / (
        np.std(scores_array, ddof=0) + ZSCORE_EPSILON
    )
    raw = np.exp(SIGNAL_TEMPERATURE * z_scores)
    probabilities = 6.0 * raw / np.sum(raw)
    return {number: float(probabilities[number - 1]) for number in range(1, 50)}


def assert_probability_contract(probabilities: dict[int, float]) -> None:
    assert set(probabilities) == set(range(1, 50))
    assert all(0.0 < value < 1.0 for value in probabilities.values())
    assert sum(probabilities.values()) == pytest.approx(6.0, abs=1e-12)


def test_v5_constants_match_the_registered_candidate():
    registration = load_experiment_registry(
        ROOT / "docs" / "experiments" / "registry.yaml"
    ).get("V5_pair_affinity")

    assert registration.experiment_id == "V5_pair_affinity"
    assert registration.model_name == "v5_pair_affinity"
    assert registration.model_version == "v5.0.0"
    assert registration.seed == 649
    assert registration.family == "pair_cooccurrence"
    assert registration.multiplicity_family == "v5_pair_cooccurrence"
    assert registration.variant_index == 1
    assert MINIMUM_HISTORY_DRAWS == registration.parameters["minimum_history_draws"]
    assert PAIR_PRIOR_STRENGTH == registration.parameters["pair_prior_strength_draws"]
    assert MARGINAL_PRIOR == registration.parameters["marginal_prior_probability"]
    assert CONDITIONAL_PAIR_PRIOR == registration.parameters[
        "conditional_pair_prior_probability"
    ]
    assert SIGNAL_TEMPERATURE == registration.parameters["signal_temperature"]
    assert ZSCORE_EPSILON == registration.parameters["zscore_population_epsilon"]
    assert registration.parameters["history_window"] == "expanding"
    assert registration.parameters["anchor_draw_lag"] == 1
    assert registration.parameters["combination_constraints"] == "none"
    assert registration.parameters["calibration"] == "none"
    assert registration.parameters["ensemble_members"] == "none"


def test_v5_refuses_to_predict_below_the_registered_minimum():
    history = synthetic_history(MINIMUM_HISTORY_DRAWS - 1)
    with pytest.raises(ValueError, match="at least 300"):
        V5PairAffinityModel().predict(
            history, history[-1].draw_date + timedelta(days=3)
        )


def test_v5_exact_formula_and_probability_contract():
    history = synthetic_history(320)
    target_date = history[-1].draw_date + timedelta(days=3)
    probabilities = V5PairAffinityModel().predict(history, target_date)

    assert_probability_contract(probabilities)
    np.testing.assert_allclose(
        list(probabilities.values()),
        list(reference_probabilities(history).values()),
        rtol=0.0,
        atol=1e-15,
    )


def test_v5_accepts_exactly_300_prior_draws():
    history = synthetic_history(MINIMUM_HISTORY_DRAWS)
    probabilities = V5PairAffinityModel().predict(
        history, history[-1].draw_date + timedelta(days=3)
    )
    assert_probability_contract(probabilities)


def test_v5_rejects_target_draw_in_its_history():
    history = synthetic_history(320)
    with pytest.raises(ValueError, match="strictly before"):
        V5PairAffinityModel().predict(history, history[-1].draw_date)


def test_v5_rejects_unordered_or_duplicate_history():
    history = synthetic_history(320)
    target_date = history[-1].draw_date + timedelta(days=3)

    with pytest.raises(ValueError, match="chronological"):
        V5PairAffinityModel().predict(history[:-2] + [history[-1], history[-2]], target_date)
    with pytest.raises(ValueError, match="unique"):
        V5PairAffinityModel().predict(history[:-1] + [history[-2]], target_date)


def test_v5_prediction_is_deterministic_and_prefix_invariant():
    history = synthetic_history(330)
    prefix = history[:310]
    prefix_target = prefix[-1].draw_date + timedelta(days=3)
    model = V5PairAffinityModel()

    first = model.predict(prefix, prefix_target)
    assert first == model.predict(prefix, prefix_target)
    model.predict(history, history[-1].draw_date + timedelta(days=3))
    assert first == model.predict(prefix, prefix_target)
    assert first == V5PairAffinityModel().predict(prefix, prefix_target)


def test_v5_ignores_bonus_numbers():
    history = synthetic_history(320)
    changed_bonus = [
        Draw(
            draw.draw_date,
            draw.numbers,
            next(
                number
                for number in range(49, 0, -1)
                if number not in draw.numbers and number != draw.bonus
            ),
        )
        for draw in history
    ]
    target_date = history[-1].draw_date + timedelta(days=3)

    assert V5PairAffinityModel().predict(
        history, target_date
    ) == V5PairAffinityModel().predict(changed_bonus, target_date)


def test_v5_runs_through_the_registered_negative_control_path():
    history = synthetic_history(320)
    control = permute_draw_outcomes(history, seed=649)
    probabilities = V5PairAffinityModel().predict(
        control, control[-1].draw_date + timedelta(days=3)
    )

    assert_probability_contract(probabilities)
    assert probabilities == V5PairAffinityModel().predict(
        control, control[-1].draw_date + timedelta(days=3)
    )


def test_negative_control_uses_the_same_walk_forward_scoring_pipeline():
    draws = synthetic_history(304)
    control = permute_draw_outcomes(draws, seed=649)
    cfg = deepcopy(load_config(ROOT / "config" / "research-v5-pair-affinity.yaml"))
    cfg["backtest"]["models"] = ["v5_pair_affinity"]
    start = draws[300].draw_date
    end = draws[-1].draw_date

    candidate_frame = run_backtest(draws, cfg, start, end)
    control_frame = run_backtest(control, cfg, start, end)

    assert list(candidate_frame.columns) == list(control_frame.columns)
    assert candidate_frame["target_draw_date"].tolist() == control_frame[
        "target_draw_date"
    ].tolist()
    assert len(candidate_frame) == len(control_frame) == 4


def test_backtest_records_per_model_version_without_changing_default_behavior():
    draws = synthetic_history(301)
    cfg = deepcopy(load_config(ROOT / "config" / "research-v5-pair-affinity.yaml"))
    cfg["backtest"]["models"] = ["v5_pair_affinity"]
    target_date = draws[-1].draw_date

    frame = run_backtest(draws, cfg, target_date, target_date)

    assert len(frame) == 1
    assert frame.iloc[0]["model_name"] == "v5_pair_affinity"
    assert frame.iloc[0]["model_version"] == "v5.0.0"
