from copy import deepcopy
from datetime import datetime, timedelta
import math
from pathlib import Path

import pytest

from lotto649.config import load_config
from lotto649.backtest import run_backtest
from lotto649.domain import Draw, Prediction
from lotto649.evaluation import evaluate_prediction
from lotto649.models.factory import build_models
import lotto649.models.v7_main_bonus_role_bias as v7_module
from lotto649.models.v7_main_bonus_role_bias import (
    ACTIVE_MINIMUM_POST_RNG_DRAWS,
    BONUS_ROLE_PSEUDOCOUNT,
    MAIN_ROLE_PSEUDOCOUNT,
    RNG_START_DATE,
    V7MainBonusRoleBiasModel,
    V7MainBonusRoleControlModel,
    analyze_main_bonus_role_bias,
)
from lotto649.optimizer import rank_numbers
from lotto649.research_protocol import load_experiment_registry


ROOT = Path(__file__).resolve().parents[1]
FAIR_PROBABILITY = 6.0 / 49.0


def _role_history(count: int = 104) -> list[Draw]:
    """A hand-auditable series over the same seven labels.

    Draws 1..103 assign label 7 to bonus.  Draw 104 instead assigns label 6
    to bonus, so the exact role counts are independent of production code.
    """
    draws = []
    for index in range(count):
        draw_date = RNG_START_DATE + timedelta(days=3 * index)
        if index == 103:
            draws.append(Draw(draw_date, (1, 2, 3, 4, 5, 7), 6))
        else:
            draws.append(Draw(draw_date, (1, 2, 3, 4, 5, 6), 7))
    return draws


def _assert_probability_contract(probabilities: dict[int, float]) -> None:
    assert list(probabilities) == list(range(1, 50))
    assert all(math.isfinite(value) for value in probabilities.values())
    assert all(0.0 < value < 1.0 for value in probabilities.values())
    assert sum(probabilities.values()) == pytest.approx(6.0, rel=0.0, abs=1e-12)


def _all_zero_signal_history() -> list[Draw]:
    draws = []
    selected = tuple(range(1, 8))
    for index in range(105):
        bonus = selected[index % 7]
        main = tuple(number for number in selected if number != bonus)
        draws.append(Draw(RNG_START_DATE + timedelta(days=3 * index), main, bonus))
    return draws


def _relabel_history(history: list[Draw], mapping: dict[int, int]) -> list[Draw]:
    return [
        Draw(
            draw.draw_date,
            tuple(mapping[number] for number in draw.numbers),
            mapping[draw.bonus] if draw.bonus is not None else None,
        )
        for draw in history
    ]


def test_v7_activates_at_exactly_104_post_rng_draws_after_exact_fair_fallback():
    history = _role_history()
    target_date = history[-1].draw_date + timedelta(days=3)
    model = V7MainBonusRoleBiasModel()

    inactive_analysis = analyze_main_bonus_role_bias(history[:103], target_date)
    inactive = model.predict(history[:103], target_date)
    active_analysis = analyze_main_bonus_role_bias(history, target_date)
    active = model.predict(history, target_date)

    assert ACTIVE_MINIMUM_POST_RNG_DRAWS == 104
    assert inactive_analysis.post_rng_draw_count == 103
    assert not inactive_analysis.active
    assert inactive_analysis.signals == (0.0,) * 49
    assert inactive_analysis.intercept is None
    assert inactive == {number: FAIR_PROBABILITY for number in range(1, 50)}
    assert active_analysis.post_rng_draw_count == 104
    assert active_analysis.active
    assert active != inactive
    _assert_probability_contract(active)


def test_v7_ignores_pre_cutoff_roles_and_includes_the_cutoff_draw():
    history = _role_history()
    before_cutoff = Draw(RNG_START_DATE - timedelta(days=3), (40, 41, 42, 43, 44, 45), 49)
    altered_before_cutoff = Draw(
        RNG_START_DATE - timedelta(days=3), (8, 9, 10, 11, 12, 13), 14
    )
    target_date = history[-1].draw_date + timedelta(days=3)

    baseline = analyze_main_bonus_role_bias(history, target_date)
    with_pre_cutoff = analyze_main_bonus_role_bias(
        [before_cutoff, *history], target_date
    )
    with_altered_pre_cutoff = analyze_main_bonus_role_bias(
        [altered_before_cutoff, *history], target_date
    )

    assert with_pre_cutoff == baseline == with_altered_pre_cutoff
    assert baseline.main_counts[:7] == (104, 104, 104, 104, 104, 103, 1)
    assert baseline.bonus_counts[:7] == (0, 0, 0, 0, 0, 1, 103)
    assert baseline.post_rng_draw_count == len(history)


def test_v7_matches_independent_hand_counted_signal_root_and_probability_oracle():
    history = _role_history()
    target_date = history[-1].draw_date + timedelta(days=3)

    analysis = analyze_main_bonus_role_bias(history, target_date)
    probabilities = V7MainBonusRoleBiasModel().predict(history, target_date)

    # These literals were worked independently from the registered equations:
    # five labels have m/b=104/0, one 103/1, one 1/103, and 42 have 0/0.
    assert analysis.signals[:8] == pytest.approx(
        (
            3.574216545793796,
            3.574216545793796,
            3.574216545793796,
            3.574216545793796,
            3.574216545793796,
            2.4662145167758482,
            -5.045036720813588,
            0.0,
        ),
        rel=0.0,
        abs=1e-15,
    )
    assert analysis.signals[8:] == (0.0,) * 41
    maximum_absolute_signal = max(abs(signal) for signal in analysis.signals)
    lower = -64.0 - maximum_absolute_signal
    upper = 64.0 + maximum_absolute_signal

    def oracle_sigmoid(value: float) -> float:
        if value >= 0.0:
            return 1.0 / (1.0 + math.exp(-value))
        exponential = math.exp(value)
        return exponential / (1.0 + exponential)

    assert sum(oracle_sigmoid(lower + signal) for signal in analysis.signals) < 6.0
    assert 6.0 < sum(
        oracle_sigmoid(upper + signal) for signal in analysis.signals
    )
    original_lower, original_upper = lower, upper
    for _ in range(256):
        midpoint = (lower + upper) / 2.0
        if (
            sum(
                oracle_sigmoid(midpoint + signal)
                for signal in analysis.signals
            )
            > 6.0
        ):
            upper = midpoint
        else:
            lower = midpoint
    oracle_intercept = (lower + upper) / 2.0

    assert analysis.intercept == pytest.approx(
        -2.8699877856647102, rel=0.0, abs=1e-15
    )
    assert analysis.intercept == oracle_intercept
    assert original_lower < analysis.intercept < original_upper
    assert probabilities[1] == pytest.approx(
        0.6691246749812786, rel=0.0, abs=1e-15
    )
    assert probabilities[6] == pytest.approx(
        0.40040611002305093, rel=0.0, abs=1e-15
    )
    assert probabilities[7] == pytest.approx(
        0.0003650816047396997, rel=0.0, abs=1e-18
    )
    assert probabilities[8] == pytest.approx(
        0.05365727222537657, rel=0.0, abs=1e-16
    )
    assert rank_numbers(probabilities)[:8] == [1, 2, 3, 4, 5, 6, 8, 9]
    assert rank_numbers(probabilities)[-1] == 7
    assert analysis.probabilities == tuple(probabilities.values())


def test_v7_solver_trace_locks_registered_bracket_and_all_256_steps(monkeypatch):
    history = _role_history()
    target_date = history[-1].draw_date + timedelta(days=3)
    original_sigmoid = v7_module._stable_sigmoid
    calls: list[float] = []

    def traced_sigmoid(value: float) -> float:
        calls.append(value)
        return original_sigmoid(value)

    monkeypatch.setattr(v7_module, "_stable_sigmoid", traced_sigmoid)
    analysis = analyze_main_bonus_role_bias(history, target_date)

    assert v7_module.BISECTION_BASE_BOUND == 64.0
    assert v7_module.BISECTION_ITERATIONS == 256
    groups = [calls[index : index + 49] for index in range(0, len(calls), 49)]
    assert len(groups) == 2 + 256 + 1
    maximum_absolute_signal = max(abs(signal) for signal in analysis.signals)
    lower = -64.0 - maximum_absolute_signal
    upper = 64.0 + maximum_absolute_signal
    assert groups[0] == pytest.approx(
        [lower + signal for signal in analysis.signals], rel=0.0, abs=1e-15
    )
    assert groups[1] == pytest.approx(
        [upper + signal for signal in analysis.signals], rel=0.0, abs=1e-15
    )
    for step in range(256):
        midpoint = (lower + upper) / 2.0
        expected_inputs = [midpoint + signal for signal in analysis.signals]
        assert groups[step + 2] == pytest.approx(
            expected_inputs, rel=0.0, abs=1e-15
        )
        midpoint_sum = sum(original_sigmoid(value) for value in expected_inputs)
        if midpoint_sum > 6.0:
            upper = midpoint
        else:
            lower = midpoint
    expected_intercept = (lower + upper) / 2.0
    assert analysis.intercept == expected_intercept
    assert groups[-1] == pytest.approx(
        [expected_intercept + signal for signal in analysis.signals],
        rel=0.0,
        abs=1e-15,
    )


def test_v7_solver_equality_follows_the_registered_lower_branch(monkeypatch):
    history = _role_history()
    target_date = history[-1].draw_date + timedelta(days=3)

    def equality_sigmoid(value: float) -> float:
        if value <= -64.0:
            return 0.0
        if value >= 64.0:
            return 1.0
        return FAIR_PROBABILITY

    monkeypatch.setattr(v7_module, "BISECTION_ITERATIONS", 1)
    monkeypatch.setattr(v7_module, "_stable_sigmoid", equality_sigmoid)

    analysis = analyze_main_bonus_role_bias(history, target_date)

    assert analysis.intercept is not None
    assert analysis.intercept > 0.0
    assert analysis.probabilities == (FAIR_PROBABILITY,) * 49


@pytest.mark.parametrize("history", [_role_history(103), _all_zero_signal_history()])
def test_v7_fair_fallbacks_bypass_the_solver(monkeypatch, history):
    target_date = history[-1].draw_date + timedelta(days=3)

    def fail_if_called(_value: float) -> float:
        raise AssertionError("fair fallback must bypass the registered solver")

    monkeypatch.setattr(v7_module, "_stable_sigmoid", fail_if_called)

    analysis = analyze_main_bonus_role_bias(history, target_date)

    assert analysis.intercept is None
    assert analysis.probabilities == (FAIR_PROBABILITY,) * 49


def test_v7_solver_fails_closed_when_the_registered_bracket_is_not_strict(
    monkeypatch,
):
    history = _role_history()
    target_date = history[-1].draw_date + timedelta(days=3)
    monkeypatch.setattr(
        v7_module,
        "_stable_sigmoid",
        lambda _value: FAIR_PROBABILITY,
    )

    with pytest.raises(RuntimeError, match="failed to strictly bracket"):
        analyze_main_bonus_role_bias(history, target_date)


def test_model_factory_builds_registered_v7_candidate_and_control_only():
    cfg = {"features": {}, "backtest": {"models": []}}

    candidate = build_models(cfg, requested=["v7_main_bonus_role_bias"])
    control = build_models(cfg, requested=["v7_main_bonus_role_control"])

    assert list(candidate) == ["v7_main_bonus_role_bias"]
    assert isinstance(candidate["v7_main_bonus_role_bias"], V7MainBonusRoleBiasModel)
    assert list(control) == ["v7_main_bonus_role_control"]
    assert isinstance(control["v7_main_bonus_role_control"], V7MainBonusRoleControlModel)


def test_v7_constants_research_config_and_registry_are_exactly_locked():
    cfg = load_config(ROOT / "config" / "research-v7-main-bonus-role-bias.yaml")
    registration = load_experiment_registry(
        ROOT / "docs" / "experiments" / "registry.yaml"
    ).get("V7_post_rng_main_bonus_role_bias")
    parameters = registration.parameters

    assert registration.model_name == "v7_main_bonus_role_bias"
    assert registration.model_version == "v7.0.0"
    assert registration.family == "draw_role_exchangeability"
    assert registration.multiplicity_family == "draw_role_exchangeability"
    assert registration.variant_index == 1
    assert registration.seed == v7_module.CONTROL_SEED == 649
    assert RNG_START_DATE.isoformat() == parameters["post_rng_start_date"]
    assert ACTIVE_MINIMUM_POST_RNG_DRAWS == parameters[
        "active_minimum_post_rng_prior_draws"
    ]
    assert MAIN_ROLE_PSEUDOCOUNT == parameters["main_role_pseudocount"]
    assert BONUS_ROLE_PSEUDOCOUNT == parameters["bonus_role_pseudocount"]
    assert v7_module.FAIR_MAIN_TO_BONUS_ODDS == parameters[
        "fair_conditional_main_bonus_odds"
    ]
    assert v7_module.BISECTION_ITERATIONS == parameters["bisection_iterations"]
    assert v7_module.PROBABILITY_SUM_ABSOLUTE_TOLERANCE == parameters[
        "probability_sum_absolute_tolerance"
    ]
    assert cfg["research"]["post_rng_start_date"] == RNG_START_DATE.isoformat()
    assert cfg["research"]["active_minimum_post_rng_prior_draws"] == (
        ACTIVE_MINIMUM_POST_RNG_DRAWS
    )
    assert cfg["research"]["main_role_pseudocount"] == MAIN_ROLE_PSEUDOCOUNT
    assert cfg["research"]["bonus_role_pseudocount"] == BONUS_ROLE_PSEUDOCOUNT
    assert cfg["research"]["bisection_iterations"] == v7_module.BISECTION_ITERATIONS
    assert cfg["backtest"]["models"] == [registration.model_name]
    assert cfg["backtest"]["model_versions"] == {
        registration.model_name: registration.model_version
    }
    assert "v7_main_bonus_role_control" not in cfg["backtest"]["models"]
    assert cfg["live"] == {"enabled": False, "models": [], "shadow_models": []}


def test_v7_rejects_empty_unordered_duplicate_same_date_and_future_history():
    history = _role_history()
    target_date = history[-1].draw_date + timedelta(days=3)
    duplicate = [
        *history[:-1],
        Draw(history[-2].draw_date, history[-1].numbers, history[-1].bonus),
    ]

    with pytest.raises(ValueError, match="must not be empty"):
        V7MainBonusRoleBiasModel().predict([], target_date)
    with pytest.raises(ValueError, match="chronological"):
        V7MainBonusRoleBiasModel().predict(
            [*history[:-2], history[-1], history[-2]], target_date
        )
    with pytest.raises(ValueError, match="unique"):
        V7MainBonusRoleBiasModel().predict(duplicate, target_date)
    with pytest.raises(ValueError, match="strictly before"):
        V7MainBonusRoleBiasModel().predict(history, history[-1].draw_date)
    future = Draw(target_date + timedelta(days=3), (8, 9, 10, 11, 12, 13), 14)
    with pytest.raises(ValueError, match="strictly before"):
        V7MainBonusRoleBiasModel().predict([*history, future], target_date)


def test_v7_prediction_depends_only_on_strict_prefix_not_target_or_future_outcome():
    history = _role_history()
    target_date = history[-1].draw_date + timedelta(days=3)
    first_target = Draw(target_date, (8, 9, 10, 11, 12, 13), 14)
    second_target = Draw(target_date, (20, 21, 22, 23, 24, 25), 26)
    first_future = Draw(target_date + timedelta(days=3), (27, 28, 29, 30, 31, 32), 33)
    second_future = Draw(target_date + timedelta(days=3), (34, 35, 36, 37, 38, 39), 40)

    first_series = [*history, first_target, first_future]
    second_series = [*history, second_target, second_future]
    first_prefix = [draw for draw in first_series if draw.draw_date < target_date]
    second_prefix = [draw for draw in second_series if draw.draw_date < target_date]

    assert first_prefix == second_prefix == history
    assert V7MainBonusRoleBiasModel().predict(
        first_prefix, target_date
    ) == V7MainBonusRoleBiasModel().predict(second_prefix, target_date)


def test_v7_strictly_prior_historical_bonus_role_changes_signal_direction():
    history = _role_history()
    target_date = history[-1].draw_date + timedelta(days=3)
    reassigned_last_role = [
        *history[:-1],
        Draw(history[-1].draw_date, (1, 2, 3, 4, 5, 6), 7),
    ]

    original = V7MainBonusRoleBiasModel().predict(history, target_date)
    changed = V7MainBonusRoleBiasModel().predict(reassigned_last_role, target_date)
    original_analysis = analyze_main_bonus_role_bias(history, target_date)
    changed_analysis = analyze_main_bonus_role_bias(reassigned_last_role, target_date)

    assert original_analysis.main_counts[5:7] == (103, 1)
    assert original_analysis.bonus_counts[5:7] == (1, 103)
    assert changed_analysis.main_counts[5:7] == (104, 0)
    assert changed_analysis.bonus_counts[5:7] == (0, 104)
    assert changed_analysis.signals[5] > original_analysis.signals[5]
    assert changed_analysis.signals[6] < original_analysis.signals[6]
    assert changed[6] > original[6]
    assert changed[7] < original[7]


def test_v7_active_all_zero_signals_bypass_root_with_exact_fair_vector():
    history = _all_zero_signal_history()
    target_date = history[-1].draw_date + timedelta(days=3)

    analysis = analyze_main_bonus_role_bias(history, target_date)
    probabilities = V7MainBonusRoleBiasModel().predict(history, target_date)

    assert analysis.active
    assert analysis.post_rng_draw_count == 105
    assert analysis.main_counts[:7] == (90,) * 7
    assert analysis.bonus_counts[:7] == (15,) * 7
    assert analysis.signals == (0.0,) * 49
    assert analysis.intercept is None
    assert probabilities == {number: FAIR_PROBABILITY for number in range(1, 50)}
    assert rank_numbers(probabilities) == list(range(1, 50))


def test_v7_extreme_counts_remain_open_finite_sum_six_and_deterministic():
    history = [
        Draw(
            RNG_START_DATE + timedelta(days=index),
            (1, 2, 3, 4, 5, 6),
            49,
        )
        for index in range(2_000)
    ]
    target_date = history[-1].draw_date + timedelta(days=1)
    model = V7MainBonusRoleBiasModel()

    first = model.predict(history, target_date)
    second = model.predict(history, target_date)
    new_instance = V7MainBonusRoleBiasModel().predict(history, target_date)
    later_target = model.predict(history, target_date + timedelta(days=100))

    _assert_probability_contract(first)
    assert first == second == new_instance == later_target
    assert first[1] > FAIR_PROBABILITY > first[49]
    assert model.name == "v7_main_bonus_role_bias"


def test_v7_global_label_permutation_is_equivariant_with_numeric_tie_rule():
    history = _role_history()
    target_date = history[-1].draw_date + timedelta(days=3)
    mapping = {number: ((number * 17) % 49) + 1 for number in range(1, 50)}
    inverse = {mapped: original for original, mapped in mapping.items()}
    relabelled = _relabel_history(history, mapping)

    original_analysis = analyze_main_bonus_role_bias(history, target_date)
    mapped_analysis = analyze_main_bonus_role_bias(relabelled, target_date)
    original = V7MainBonusRoleBiasModel().predict(history, target_date)
    mapped = V7MainBonusRoleBiasModel().predict(relabelled, target_date)

    for mapped_label in range(1, 50):
        original_label = inverse[mapped_label]
        assert mapped_analysis.main_counts[mapped_label - 1] == (
            original_analysis.main_counts[original_label - 1]
        )
        assert mapped_analysis.bonus_counts[mapped_label - 1] == (
            original_analysis.bonus_counts[original_label - 1]
        )
        assert mapped_analysis.signals[mapped_label - 1] == (
            original_analysis.signals[original_label - 1]
        )
        assert mapped[mapped_label] == pytest.approx(
            original[original_label], rel=0.0, abs=1e-15
        )

    expected_ranking = sorted(
        range(1, 50),
        key=lambda mapped_label: (-original[inverse[mapped_label]], mapped_label),
    )
    assert rank_numbers(mapped) == expected_ranking


def test_target_bonus_is_excluded_from_hits_ranks_and_proper_scores():
    history = _role_history()
    target_date = history[-1].draw_date + timedelta(days=3)
    probabilities = V7MainBonusRoleBiasModel().predict(history, target_date)
    ranked = rank_numbers(probabilities)
    prediction = Prediction(
        target_draw_date=target_date,
        generated_at=datetime(2026, 8, 16, 12, 0),
        model_name="v7_main_bonus_role_bias",
        model_version="v7.0.0",
        probabilities=probabilities,
        top6=ranked[:6],
        top12=ranked[:12],
        top18=ranked[:18],
        final_combination=ranked[:6],
        metadata={},
    )
    first = evaluate_prediction(
        prediction, Draw(target_date, (1, 2, 8, 9, 10, 11), 12)
    )
    second = evaluate_prediction(
        prediction, Draw(target_date, (1, 2, 8, 9, 10, 11), 13)
    )

    assert first["bonus"] == 12
    assert second["bonus"] == 13
    assert {key: value for key, value in first.items() if key != "bonus"} == {
        key: value for key, value in second.items() if key != "bonus"
    }
    assert list(prediction.to_json_dict()["probabilities"]) == [
        str(number) for number in range(1, 50)
    ]


def test_v7_fails_closed_when_post_rng_role_label_is_missing():
    history = _role_history()
    missing_bonus = [*history[:-1], Draw(history[-1].draw_date, history[-1].numbers)]

    with pytest.raises(ValueError, match="requires a bonus role"):
        V7MainBonusRoleBiasModel().predict(
            missing_bonus, history[-1].draw_date + timedelta(days=3)
        )


def test_v7_control_public_predict_matches_frozen_seed_649_literal_oracle():
    history = _role_history()
    target_date = history[-1].draw_date + timedelta(days=3)

    probabilities = V7MainBonusRoleControlModel().predict(history, target_date)

    _assert_probability_contract(probabilities)
    assert V7MainBonusRoleControlModel.name == "v7_main_bonus_role_control"
    # Independent default_rng(649) replay assigns pseudo-bonus counts
    # [14, 15, 14, 12, 15, 19, 15] to sorted labels 1..7.
    assert probabilities[1] == pytest.approx(
        0.12955110370852665, rel=0.0, abs=1e-15
    )
    assert probabilities[2] == pytest.approx(
        0.1210594073391932, rel=0.0, abs=1e-15
    )
    assert probabilities[4] == pytest.approx(
        0.149919034356489, rel=0.0, abs=1e-15
    )
    assert probabilities[6] == pytest.approx(
        0.09479351144146174, rel=0.0, abs=1e-15
    )
    assert probabilities[8] == pytest.approx(
        0.1222144529706528, rel=0.0, abs=1e-15
    )
    assert probabilities == V7MainBonusRoleControlModel().predict(
        history, target_date
    )


def test_v7_candidate_and_control_share_the_real_walk_forward_scoring_seam():
    post_rng_history = _role_history()
    target_date = post_rng_history[-1].draw_date + timedelta(days=3)
    pre_rng_history = [
        Draw(
            RNG_START_DATE - timedelta(days=301 - index),
            (8, 9, 10, 11, 12, 13),
            14,
        )
        for index in range(300)
    ]
    target = Draw(target_date, (15, 16, 17, 18, 19, 20), 21)
    draws = [*pre_rng_history, *post_rng_history, target]
    candidate_cfg = load_config(
        ROOT / "config" / "research-v7-main-bonus-role-bias.yaml"
    )
    control_cfg = deepcopy(candidate_cfg)
    control_cfg["backtest"]["models"] = ["v7_main_bonus_role_control"]
    control_cfg["backtest"]["model_versions"] = {
        "v7_main_bonus_role_control": "v7.0.0"
    }

    candidate = run_backtest(draws, candidate_cfg, target_date, target_date)
    control = run_backtest(draws, control_cfg, target_date, target_date)

    assert len(candidate) == len(control) == 1
    assert candidate.loc[0, "model_name"] == "v7_main_bonus_role_bias"
    assert control.loc[0, "model_name"] == "v7_main_bonus_role_control"
    assert candidate.loc[0, "model_version"] == control.loc[0, "model_version"] == (
        "v7.0.0"
    )
    identity_columns = ["target_draw_date", "actual", "bonus"]
    assert candidate.loc[0, identity_columns].to_dict() == control.loc[
        0, identity_columns
    ].to_dict()
    assert candidate.loc[0, "target_draw_date"] == target_date.isoformat()
    assert candidate.loc[0, "actual"] == list(target.numbers)
    assert candidate.loc[0, "bonus"] == target.bonus
