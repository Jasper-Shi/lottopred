from datetime import date, timedelta
import math
from pathlib import Path

import pytest

from lotto649.domain import Draw
from lotto649.config import load_config
import lotto649.models.v6_entropy_regime as v6_module
from lotto649.models.v6_entropy_regime import (
    V6EntropyRegimeModel,
    analyze_entropy_regime,
)
from lotto649.models.factory import build_models
from lotto649.optimizer import rank_numbers
from lotto649.research_protocol import walk_forward_folds
from lotto649.research_protocol import load_experiment_registry


ROOT = Path(__file__).resolve().parents[1]


def _numbers(index: int) -> tuple[int, ...]:
    return tuple(sorted((((index * 7) + offset * 8) % 49) + 1 for offset in range(6)))


def _draws_with_equal_feature_blocks(count: int = 300) -> list[Draw]:
    first = date(2010, 1, 2)
    feature_start = count - 208
    draws = []
    for index in range(count):
        outcome_index = (
            (index - feature_start) % 104 if index >= feature_start else index
        )
        numbers = _numbers(outcome_index)
        bonus = next(number for number in range(1, 50) if number not in numbers)
        draws.append(Draw(first + timedelta(days=3 * index), numbers, bonus))
    return draws


def _draws_with_active_regime() -> list[Draw]:
    first = date(2010, 1, 2)
    draws = []
    for index in range(300):
        if index < 92:
            numbers = _numbers(index)
        elif index < 196:
            numbers = (7, 8, 9, 10, 11, 12)
        else:
            numbers = (1, 2, 3, 4, 5, 6)
        bonus = next(number for number in range(1, 50) if number not in numbers)
        draws.append(Draw(first + timedelta(days=3 * index), numbers, bonus))
    return draws


def test_v6_requires_300_prior_draws_then_returns_expected_six_contract():
    history = _draws_with_equal_feature_blocks()
    target_date = history[-1].draw_date + timedelta(days=3)
    model = V6EntropyRegimeModel()

    with pytest.raises(ValueError, match="at least 300"):
        model.predict(history[:299], target_date)

    probabilities = model.predict(history, target_date)

    assert set(probabilities) == set(range(1, 50))
    assert all(math.isfinite(value) for value in probabilities.values())
    assert all(0.0 < value < 1.0 for value in probabilities.values())
    assert sum(probabilities.values()) == pytest.approx(6.0, abs=1e-12)


def test_model_factory_builds_only_the_requested_v6_candidate():
    models = build_models(
        {"features": {}, "backtest": {"models": ["v6_entropy_regime"]}}
    )

    assert list(models) == ["v6_entropy_regime"]
    assert isinstance(models["v6_entropy_regime"], V6EntropyRegimeModel)


def test_v6_research_config_runs_only_the_registered_exact_version():
    cfg = load_config(ROOT / "config" / "research-v6-entropy-regime.yaml")
    registration = load_experiment_registry(
        ROOT / "docs" / "experiments" / "registry.yaml"
    ).get("V6_fixed_boundary_js_regime")

    assert cfg["backtest"]["models"] == [registration.model_name]
    assert cfg["backtest"]["model_versions"] == {
        registration.model_name: registration.model_version
    }
    assert cfg["backtest"]["min_history_draws"] == registration.parameters[
        "minimum_history_draws"
    ]
    assert cfg["project"]["model_version"] == "v6.0.0"
    assert cfg["live"] == {
        "enabled": False,
        "models": [],
        "shadow_models": [],
    }
    assert cfg["notifications"]["enabled"] is False


def test_v6_implementation_constants_match_the_committed_registration():
    parameters = load_experiment_registry(
        ROOT / "docs" / "experiments" / "registry.yaml"
    ).get("V6_fixed_boundary_js_regime").parameters

    assert v6_module.MINIMUM_HISTORY_DRAWS == parameters["minimum_history_draws"]
    assert v6_module.FEATURE_WINDOW_DRAWS == parameters["feature_window_draws"]
    assert v6_module.BLOCK_DRAWS == parameters["older_block_draws"]
    assert v6_module.BLOCK_DRAWS == parameters["recent_block_draws"]
    assert v6_module.FINITE_POPULATION_CORRECTION == (
        parameters["finite_population_numerator"]
        / parameters["finite_population_denominator"]
    )
    assert v6_module.REGIME_THRESHOLD == parameters["regime_threshold"]
    assert v6_module.ZSCORE_EPSILON == parameters["zscore_population_epsilon"]
    assert v6_module.SIGNAL_TEMPERATURE == parameters["signal_temperature"]
    assert v6_module.JITTER_SEED_BASE == parameters["jitter_seed_base"]
    assert v6_module.JITTER_LOW == parameters["jitter_low"]
    assert v6_module.JITTER_HIGH == parameters["jitter_high"]


def test_active_regime_matches_independent_count_and_statistic_oracle():
    history = _draws_with_active_regime()
    target_date = history[-1].draw_date + timedelta(days=3)

    analysis = analyze_entropy_regime(history, target_date)
    probabilities = V6EntropyRegimeModel().predict(history, target_date)

    assert analysis.older_counts[:12] == (0,) * 6 + (104,) * 6
    assert analysis.recent_counts[:12] == (104,) * 6 + (0,) * 6
    assert analysis.adjusted_contributions[0] == pytest.approx(
        160.9391035048952, abs=1e-10
    )
    assert analysis.statistic == pytest.approx(1931.2692420587423, abs=1e-10)
    assert analysis.directional_scores[:12] == pytest.approx(
        (160.9391035048952,) * 6 + (-160.9391035048952,) * 6,
        abs=1e-10,
    )
    assert analysis.adjusted_contributions[12:] == (0.0,) * 37
    assert analysis.active
    assert rank_numbers(probabilities)[:6] == [2, 1, 3, 6, 4, 5]
    assert set(rank_numbers(probabilities)[-6:]) == set(range(7, 13))
    assert probabilities[1] == pytest.approx(0.14912167012476293, abs=1e-14)
    assert probabilities[7] == pytest.approx(0.09954575244825135, abs=1e-14)
    assert probabilities[13] == pytest.approx(0.12183771528411932, abs=1e-14)


def test_inactive_equal_blocks_use_the_frozen_date_jitter_exactly():
    history = _draws_with_equal_feature_blocks()
    target_date = history[-1].draw_date + timedelta(days=3)
    model = V6EntropyRegimeModel()

    analysis = analyze_entropy_regime(history, target_date)
    first = model.predict(history, target_date)
    second = model.predict(history, target_date)
    next_date = model.predict(history, target_date + timedelta(days=1))

    assert analysis.older_counts == analysis.recent_counts
    assert analysis.statistic == 0.0
    assert not analysis.active
    assert first == second
    assert next_date != first
    assert rank_numbers(first)[:12] == [30, 27, 34, 14, 32, 31, 23, 15, 48, 36, 19, 44]
    assert first[1] == pytest.approx(0.12244897960415183, abs=1e-15)
    assert first[17] == pytest.approx(0.12244897950117073, abs=1e-15)
    assert first[49] == pytest.approx(0.12244897959311558, abs=1e-15)


def test_v6_rejects_unordered_duplicate_or_nonprior_history():
    history = _draws_with_equal_feature_blocks()
    target_date = history[-1].draw_date + timedelta(days=3)
    unordered = [*history[:-2], history[-1], history[-2]]
    duplicate_date = [
        *history[:-1],
        Draw(history[-2].draw_date, history[-1].numbers, history[-1].bonus),
    ]

    with pytest.raises(ValueError, match="chronological"):
        V6EntropyRegimeModel().predict(unordered, target_date)
    with pytest.raises(ValueError, match="unique"):
        V6EntropyRegimeModel().predict(duplicate_date, target_date)
    with pytest.raises(ValueError, match="strictly before"):
        V6EntropyRegimeModel().predict(history, history[-1].draw_date)


def test_v6_feature_window_boundary_is_exactly_208_draws():
    history = _draws_with_active_regime()
    target_date = history[-1].draw_date + timedelta(days=3)
    baseline_analysis = analyze_entropy_regime(history, target_date)
    baseline_probabilities = V6EntropyRegimeModel().predict(history, target_date)

    outside = list(history)
    outside[-209] = Draw(
        outside[-209].draw_date,
        (44, 45, 46, 47, 48, 49),
        1,
    )
    inside = list(history)
    inside[-208] = Draw(
        inside[-208].draw_date,
        (44, 45, 46, 47, 48, 49),
        1,
    )

    assert analyze_entropy_regime(outside, target_date) == baseline_analysis
    assert V6EntropyRegimeModel().predict(outside, target_date) == baseline_probabilities
    assert analyze_entropy_regime(inside, target_date).older_counts != (
        baseline_analysis.older_counts
    )
    assert V6EntropyRegimeModel().predict(inside, target_date) != baseline_probabilities


def test_v6_ignores_bonus_numbers():
    history = _draws_with_active_regime()
    target_date = history[-1].draw_date + timedelta(days=3)
    changed_bonus = []
    for draw in history:
        alternatives = [
            number
            for number in range(49, 0, -1)
            if number not in draw.numbers and number != draw.bonus
        ]
        changed_bonus.append(Draw(draw.draw_date, draw.numbers, alternatives[0]))

    assert analyze_entropy_regime(changed_bonus, target_date) == analyze_entropy_regime(
        history, target_date
    )
    assert V6EntropyRegimeModel().predict(
        changed_bonus, target_date
    ) == V6EntropyRegimeModel().predict(history, target_date)


def test_target_and_future_outcomes_cannot_change_the_prior_fold_prediction():
    history = _draws_with_active_regime()
    target_date = history[-1].draw_date + timedelta(days=3)
    future_date = target_date + timedelta(days=3)
    datasets = (
        [
            *history,
            Draw(target_date, (1, 2, 3, 4, 5, 6), 7),
            Draw(future_date, (7, 8, 9, 10, 11, 12), 13),
        ],
        [
            *history,
            Draw(target_date, (44, 45, 46, 47, 48, 49), 1),
            Draw(future_date, (37, 38, 39, 40, 41, 42), 1),
        ],
    )
    folds = [
        next(
            walk_forward_folds(
                draws,
                start=target_date,
                end=target_date,
                minimum_history_draws=300,
            )
        )
        for draws in datasets
    ]

    assert folds[0].history == folds[1].history == tuple(history)
    first = V6EntropyRegimeModel().predict(list(folds[0].history), target_date)
    second = V6EntropyRegimeModel().predict(list(folds[1].history), target_date)
    assert first == second


def test_active_directional_scores_are_equivariant_to_label_permutation():
    history = _draws_with_active_regime()
    target_date = history[-1].draw_date + timedelta(days=3)
    mapping = {number: ((number + 12) % 49) + 1 for number in range(1, 50)}
    permuted = []
    for draw in history:
        numbers = tuple(sorted(mapping[number] for number in draw.numbers))
        bonus = mapping[draw.bonus]
        permuted.append(Draw(draw.draw_date, numbers, bonus))

    original = analyze_entropy_regime(history, target_date)
    transformed = analyze_entropy_regime(permuted, target_date)

    assert transformed.statistic == pytest.approx(original.statistic, abs=1e-12)
    for source, target in mapping.items():
        assert transformed.directional_scores[target - 1] == pytest.approx(
            original.directional_scores[source - 1], abs=1e-12
        )


def test_regime_gate_is_strictly_greater_than(monkeypatch):
    history = _draws_with_active_regime()
    target_date = history[-1].draw_date + timedelta(days=3)
    statistic = analyze_entropy_regime(history, target_date).statistic

    monkeypatch.setattr(v6_module, "REGIME_THRESHOLD", statistic)
    assert not analyze_entropy_regime(history, target_date).active

    monkeypatch.setattr(v6_module, "REGIME_THRESHOLD", math.nextafter(statistic, -math.inf))
    assert analyze_entropy_regime(history, target_date).active
