from copy import deepcopy
from datetime import date, timedelta
from hashlib import sha256
import math
from pathlib import Path

import pytest

from lotto649.backtest import run_backtest
from lotto649.config import load_config
from lotto649.domain import Draw
from lotto649.models.factory import build_models
import lotto649.models.v8_spectral_phase as v8_module
from lotto649.models.v8_spectral_phase import (
    ACTIVE_MINIMUM_POST_RNG_DRAWS,
    BISECTION_BASE_BOUND,
    BISECTION_ITERATIONS,
    CONTROL_SEED,
    FAIR_PROBABILITY,
    FIXED_ANGULAR_FREQUENCY,
    FIXED_PERIOD_DRAWS,
    PHASE_CONTROL_DOMAIN,
    PROBABILITY_SUM_ABSOLUTE_TOLERANCE,
    RNG_START_DATE,
    ROW_CONTROL_DOMAIN,
    V8SpectralPhaseModel,
    V8SpectralPhaseRotationControlModel,
    V8SpectralPhaseRowControlModel,
    analyze_spectral_phase,
    analyze_spectral_phase_rotation_control,
    permute_v8_post_rng_prefix,
    spectral_phase_rotation_angle,
    strict_prefix_row_permutation_indices,
)
from lotto649.optimizer import rank_numbers
from lotto649.research_protocol import load_experiment_registry


ROOT = Path(__file__).resolve().parents[1]


def _spectral_history(count: int = 104) -> list[Draw]:
    return [
        Draw(
            RNG_START_DATE + timedelta(days=3 * index),
            (1, 2, 3, 4, 5, 6),
            7 + (index % 43),
        )
        for index in range(count)
    ]


def _assert_probability_contract(probabilities: dict[int, float]) -> None:
    assert list(probabilities) == list(range(1, 50))
    assert all(math.isfinite(value) for value in probabilities.values())
    assert all(0.0 < value < 1.0 for value in probabilities.values())
    assert sum(probabilities.values()) == pytest.approx(6.0, rel=0.0, abs=1e-12)


def _distinct_row_history(count: int = 105) -> list[Draw]:
    draws = []
    for index in range(count):
        numbers = tuple(
            sorted((((index * 5) + offset * 8) % 49) + 1 for offset in range(6))
        )
        bonus = next(number for number in range(1, 50) if number not in numbers)
        draws.append(
            Draw(
                RNG_START_DATE + timedelta(days=3 * index),
                numbers,
                bonus,
            )
        )
    return draws


def test_v8_activates_at_exactly_104_post_rng_draws_after_exact_fair_fallback():
    history = _spectral_history()
    target_date = history[-1].draw_date + timedelta(days=3)
    model = V8SpectralPhaseModel()

    inactive_analysis = analyze_spectral_phase(history[:103], target_date)
    inactive = model.predict(history[:103], target_date)
    active_analysis = analyze_spectral_phase(history, target_date)
    active = model.predict(history, target_date)

    assert ACTIVE_MINIMUM_POST_RNG_DRAWS == 104
    assert inactive_analysis.post_rng_draw_count == 103
    assert inactive_analysis.active is False
    assert inactive_analysis.intercept is None
    assert inactive == {number: FAIR_PROBABILITY for number in range(1, 50)}
    assert active_analysis.post_rng_draw_count == 104
    assert active_analysis.active is True
    assert active != inactive
    _assert_probability_contract(active)


def test_v8_candidate_matches_the_frozen_literal_projection_and_probability_oracle():
    history = _spectral_history()
    target_date = history[-1].draw_date + timedelta(days=3)

    analysis = analyze_spectral_phase(history, target_date)
    probabilities = V8SpectralPhaseModel().predict(history, target_date)

    assert FIXED_ANGULAR_FREQUENCY == pytest.approx(
        0.7693696294505615, rel=0.0, abs=1e-16
    )
    assert analysis.forecast_phase == pytest.approx(
        80.0144414628584, rel=0.0, abs=1e-13
    )
    assert analysis.cosine_coefficients[0] == pytest.approx(
        -0.011497459375820284, rel=0.0, abs=1e-16
    )
    assert analysis.sine_coefficients[0] == pytest.approx(
        0.03124231134527243, rel=0.0, abs=1e-16
    )
    assert analysis.scores[0] == pytest.approx(
        -0.02999392331382293, rel=0.0, abs=1e-16
    )
    assert analysis.cosine_coefficients[6] == pytest.approx(
        0.0016042966570912023, rel=0.0, abs=1e-17
    )
    assert analysis.sine_coefficients[6] == pytest.approx(
        -0.004359392280735688, rel=0.0, abs=1e-17
    )
    assert analysis.scores[6] == pytest.approx(
        0.004185198601928781, rel=0.0, abs=1e-17
    )
    assert analysis.intercept == pytest.approx(
        -1.969487847710298, rel=0.0, abs=1e-15
    )
    assert probabilities[1] == pytest.approx(
        0.11925734347867172, rel=0.0, abs=1e-16
    )
    assert probabilities[7] == pytest.approx(
        0.12289432416576675, rel=0.0, abs=1e-16
    )
    assert rank_numbers(probabilities)[:12] == list(range(7, 19))
    assert analysis.probabilities == tuple(probabilities.values())


def test_v8_four_draw_projection_oracle_locks_index_phase_and_sine_sign(monkeypatch):
    history = [
        Draw(RNG_START_DATE, (1, 2, 3, 4, 5, 6), 7),
        Draw(RNG_START_DATE + timedelta(days=3), (2, 3, 4, 5, 6, 7), 8),
        Draw(RNG_START_DATE + timedelta(days=6), (1, 2, 3, 4, 5, 6), 7),
        Draw(RNG_START_DATE + timedelta(days=9), (2, 3, 4, 5, 6, 7), 8),
    ]
    target_date = RNG_START_DATE + timedelta(days=12)
    monkeypatch.setattr(v8_module, "ACTIVE_MINIMUM_POST_RNG_DRAWS", 4)

    candidate = analyze_spectral_phase(history, target_date)
    phase_control = analyze_spectral_phase_rotation_control(history, target_date)

    assert candidate.cosine_coefficients[0] == pytest.approx(
        0.4500196640465583, rel=0.0, abs=1e-16
    )
    assert candidate.sine_coefficients[0] == pytest.approx(
        0.3506341225567017, rel=0.0, abs=1e-16
    )
    assert candidate.forecast_phase == pytest.approx(
        3.077478517802246, rel=0.0, abs=1e-16
    )
    assert candidate.scores[0] == pytest.approx(
        -0.4266298450173648, rel=0.0, abs=1e-16
    )
    assert phase_control.scores[0] == pytest.approx(
        0.5702233418877444, rel=0.0, abs=1e-16
    )


def test_v8_row_control_sha_order_is_literal_prefix_bound_and_row_preserving():
    assert strict_prefix_row_permutation_indices(4) == (2, 0, 3, 1)
    order = strict_prefix_row_permutation_indices(104)

    assert order[:12] == (21, 64, 12, 83, 58, 46, 55, 3, 68, 57, 67, 23)
    assert order[-6:] == (92, 77, 24, 18, 80, 34)
    assert sha256(",".join(str(index) for index in order).encode()).hexdigest() == (
        "4969fc573dd313e0675654af8caaef9e4d7dcf205d19a048354cfbb4759ab341"
    )
    assert strict_prefix_row_permutation_indices(105) != order
    assert sorted(order) == list(range(104))


def test_v8_phase_control_angles_match_frozen_sha256_big_endian_oracles():
    assert spectral_phase_rotation_angle(1) == pytest.approx(
        3.8368722591110487, rel=0.0, abs=1e-15
    )
    assert spectral_phase_rotation_angle(2) == pytest.approx(
        5.788172110580001, rel=0.0, abs=1e-15
    )
    assert spectral_phase_rotation_angle(49) == pytest.approx(
        5.244672103318183, rel=0.0, abs=1e-15
    )


def test_v8_candidate_and_both_controls_are_fixed_factory_models():
    cfg = load_config(ROOT / "config" / "research-v8-fixed-spectral-phase.yaml")

    models = build_models(
        cfg,
        requested=[
            "v8_spectral_phase",
            "v8_spectral_phase_row_control",
            "v8_spectral_phase_rotation_control",
        ],
    )

    assert isinstance(models["v8_spectral_phase"], V8SpectralPhaseModel)
    assert isinstance(
        models["v8_spectral_phase_row_control"],
        V8SpectralPhaseRowControlModel,
    )
    assert isinstance(
        models["v8_spectral_phase_rotation_control"],
        V8SpectralPhaseRotationControlModel,
    )


@pytest.mark.parametrize(
    ("path", "invalid_value"),
    [
        (("research", "fixed_angular_frequency"), "10*pi/49"),
        (("research", "coefficient_estimator"), "least_squares"),
        (("research", "active_minimum_post_rng_prior_draws"), 105),
        (("research", "signal_temperature"), 0.1),
        (("research", "variant_index"), True),
        (("live", "enabled"), True),
        (("live", "enabled"), 0),
    ],
)
def test_v8_factory_rejects_any_non_frozen_research_configuration(
    path,
    invalid_value,
):
    cfg = load_config(ROOT / "config" / "research-v8-fixed-spectral-phase.yaml")
    altered = deepcopy(cfg)
    altered[path[0]][path[1]] = invalid_value

    with pytest.raises(ValueError, match="frozen V8 research configuration"):
        build_models(altered, requested=["v8_spectral_phase"])


def test_v8_factory_requires_the_dedicated_research_configuration():
    with pytest.raises(ValueError, match="frozen V8 research configuration"):
        build_models(
            {"features": {}, "backtest": {"models": ["v8_spectral_phase"]}},
        )


def test_v8_factory_rejects_mixed_or_selectable_alternative_models():
    cfg = load_config(ROOT / "config" / "research-v8-fixed-spectral-phase.yaml")
    cfg["backtest"]["models"] = ["v8_spectral_phase", "random"]

    with pytest.raises(ValueError, match="cannot mix selectable models"):
        build_models(cfg)


def test_v8_factory_default_all_models_path_does_not_select_v8():
    models = build_models({"features": {}, "backtest": {}})

    assert not (set(models) & {
        "v8_spectral_phase",
        "v8_spectral_phase_row_control",
        "v8_spectral_phase_rotation_control",
    })


def test_v8_phase_control_matches_frozen_probability_and_rank_oracle():
    history = _spectral_history()
    target_date = history[-1].draw_date + timedelta(days=3)

    analysis = analyze_spectral_phase_rotation_control(history, target_date)
    probabilities = V8SpectralPhaseRotationControlModel().predict(
        history,
        target_date,
    )

    assert analysis.intercept == pytest.approx(
        -1.971615667618047, rel=0.0, abs=1e-15
    )
    assert probabilities[1] == pytest.approx(
        0.12572136427453826, rel=0.0, abs=1e-16
    )
    assert probabilities[2] == pytest.approx(
        0.12013551326972251, rel=0.0, abs=1e-16
    )
    assert probabilities[7] == pytest.approx(
        0.12257785932325442, rel=0.0, abs=1e-16
    )
    assert probabilities[49] == pytest.approx(
        0.12225701481587639, rel=0.0, abs=1e-16
    )
    assert rank_numbers(probabilities)[:12] == [
        4,
        1,
        5,
        6,
        3,
        33,
        46,
        36,
        41,
        40,
        16,
        47,
    ]
    _assert_probability_contract(probabilities)


def test_v8_row_control_moves_complete_rows_but_preserves_dates_and_marginals():
    history = _distinct_row_history(104)
    target_date = history[-1].draw_date + timedelta(days=3)
    order = strict_prefix_row_permutation_indices(len(history))

    transformed = permute_v8_post_rng_prefix(history, target_date)

    assert [draw.draw_date for draw in transformed] == [
        draw.draw_date for draw in history
    ]
    assert [
        (draw.numbers, draw.bonus) for draw in transformed
    ] == [
        (history[source].numbers, history[source].bonus) for source in order
    ]
    assert sorted((draw.numbers, draw.bonus) for draw in transformed) == sorted(
        (draw.numbers, draw.bonus) for draw in history
    )
    for number in range(1, 50):
        assert sum(number in draw.numbers for draw in transformed) == sum(
            number in draw.numbers for draw in history
        )
        assert sum(draw.bonus == number for draw in transformed) == sum(
            draw.bonus == number for draw in history
        )

    row_control = V8SpectralPhaseRowControlModel().predict(history, target_date)
    transformed_candidate = V8SpectralPhaseModel().predict(
        transformed,
        target_date,
    )
    original_candidate = V8SpectralPhaseModel().predict(history, target_date)
    assert row_control == transformed_candidate
    assert row_control != original_candidate


def test_v8_row_control_hash_binds_draw_count_ties_and_identity_fallback(monkeypatch):
    assert v8_module._row_control_digest(104, 0).hex() == (
        "a2b805b7177baa822cc5df48c2cb07d778684e3e879c2cfd4bf2bcd06e051bff"
    )
    assert v8_module._row_control_digest(104, 103).hex() == (
        "73790566bb2d9a6613dd725b6396e5692b3f2155355f2dbc28b26e6966ef6324"
    )
    assert v8_module._row_control_digest(105, 0).hex() == (
        "c364ad82862a13cbe4039b0c33c1b5ecac5fe9a7901d9ff16b49b2ce55312c5a"
    )

    monkeypatch.setattr(v8_module, "_row_control_digest", lambda _count, _index: b"x")

    assert strict_prefix_row_permutation_indices(4) == (1, 2, 3, 0)


def test_v8_candidate_and_controls_exclude_bonus_from_probabilities():
    history = _distinct_row_history(104)
    altered = [
        Draw(
            draw.draw_date,
            draw.numbers,
            next(
                number
                for number in range(49, 0, -1)
                if number not in draw.numbers
            ),
        )
        for draw in history
    ]
    target_date = history[-1].draw_date + timedelta(days=3)

    for model in (
        V8SpectralPhaseModel(),
        V8SpectralPhaseRowControlModel(),
        V8SpectralPhaseRotationControlModel(),
    ):
        assert model.predict(history, target_date) == model.predict(
            altered,
            target_date,
        )


def test_v8_models_ignore_pre_rng_rows_and_repeat_deterministically():
    history = _distinct_row_history(104)
    target_date = history[-1].draw_date + timedelta(days=3)
    pre_rng = Draw(RNG_START_DATE - timedelta(days=3), (1, 8, 16, 24, 32, 40), 49)
    altered_pre_rng = Draw(
        RNG_START_DATE - timedelta(days=3),
        (2, 9, 17, 25, 33, 41),
        48,
    )

    for model in (
        V8SpectralPhaseModel(),
        V8SpectralPhaseRowControlModel(),
        V8SpectralPhaseRotationControlModel(),
    ):
        baseline = model.predict(history, target_date)
        assert model.predict([pre_rng, *history], target_date) == baseline
        assert model.predict([altered_pre_rng, *history], target_date) == baseline
        assert model.predict(history, target_date) == baseline

    transformed = permute_v8_post_rng_prefix([pre_rng, *history], target_date)
    assert transformed[0] == pre_rng


def test_v8_inactive_controls_bypass_hash_phase_and_solver(monkeypatch):
    history = _spectral_history(103)
    target_date = history[-1].draw_date + timedelta(days=3)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("inactive controls must return fair before control math")

    monkeypatch.setattr(v8_module, "_row_control_digest", forbidden)
    monkeypatch.setattr(v8_module, "spectral_phase_rotation_angle", forbidden)
    monkeypatch.setattr(v8_module, "_stable_sigmoid", forbidden)

    expected = {number: FAIR_PROBABILITY for number in range(1, 50)}
    assert V8SpectralPhaseRowControlModel().predict(history, target_date) == expected
    assert (
        V8SpectralPhaseRotationControlModel().predict(history, target_date)
        == expected
    )


def test_v8_solver_trace_locks_bracket_and_all_256_iterations(monkeypatch):
    history = _spectral_history()
    target_date = history[-1].draw_date + timedelta(days=3)
    original_sigmoid = v8_module._stable_sigmoid
    calls: list[float] = []

    def traced_sigmoid(value: float) -> float:
        calls.append(value)
        return original_sigmoid(value)

    monkeypatch.setattr(v8_module, "_stable_sigmoid", traced_sigmoid)
    analysis = analyze_spectral_phase(history, target_date)

    groups = [calls[index : index + 49] for index in range(0, len(calls), 49)]
    assert BISECTION_BASE_BOUND == 64.0
    assert BISECTION_ITERATIONS == 256
    assert len(groups) == 2 + 256 + 1
    maximum_absolute_score = max(abs(score) for score in analysis.scores)
    lower = -64.0 - maximum_absolute_score
    upper = 64.0 + maximum_absolute_score
    assert groups[0] == pytest.approx(
        [lower + score for score in analysis.scores], rel=0.0, abs=1e-15
    )
    assert groups[1] == pytest.approx(
        [upper + score for score in analysis.scores], rel=0.0, abs=1e-15
    )
    for step in range(256):
        midpoint = (lower + upper) / 2.0
        expected_inputs = [midpoint + score for score in analysis.scores]
        assert groups[step + 2] == pytest.approx(
            expected_inputs,
            rel=0.0,
            abs=1e-15,
        )
        if sum(original_sigmoid(value) for value in expected_inputs) > 6.0:
            upper = midpoint
        else:
            lower = midpoint
    intercept = (lower + upper) / 2.0
    assert analysis.intercept == intercept
    assert groups[-1] == pytest.approx(
        [intercept + score for score in analysis.scores],
        rel=0.0,
        abs=1e-15,
    )


def test_v8_solver_equality_updates_the_lower_bracket(monkeypatch):
    scores = (1.0, -1.0, *((0.0,) * 47))

    def equality_sigmoid(value: float) -> float:
        if value <= -64.0:
            return 0.0
        if value >= 64.0:
            return 1.0
        return FAIR_PROBABILITY

    monkeypatch.setattr(v8_module, "BISECTION_ITERATIONS", 1)
    monkeypatch.setattr(v8_module, "_stable_sigmoid", equality_sigmoid)

    intercept, probabilities = v8_module._map_scores_to_probabilities(scores)

    assert intercept == 32.5
    assert probabilities == (FAIR_PROBABILITY,) * 49


def test_v8_zero_scores_bypass_solver_and_invalid_math_fails_closed(monkeypatch):
    def forbidden(_value: float) -> float:
        raise AssertionError("the exact-zero branch must bypass the solver")

    monkeypatch.setattr(v8_module, "_stable_sigmoid", forbidden)
    intercept, probabilities = v8_module._map_scores_to_probabilities((0.0,) * 49)

    assert intercept is None
    assert probabilities == (FAIR_PROBABILITY,) * 49

    with pytest.raises(RuntimeError, match="invalid forecast scores"):
        v8_module._map_scores_to_probabilities((math.nan, *((0.0,) * 48)))


def test_v8_solver_rejects_a_non_strict_intercept_bracket(monkeypatch):
    monkeypatch.setattr(
        v8_module,
        "_stable_sigmoid",
        lambda _value: FAIR_PROBABILITY,
    )

    with pytest.raises(RuntimeError, match="strictly bracket"):
        v8_module._map_scores_to_probabilities((1.0, *((0.0,) * 48)))


def test_v8_stable_sigmoid_and_probability_contract_have_literal_boundaries():
    assert v8_module._stable_sigmoid(2.0) == pytest.approx(
        0.8807970779778823, rel=0.0, abs=1e-16
    )
    assert v8_module._stable_sigmoid(-2.0) == pytest.approx(
        0.11920292202211755, rel=0.0, abs=1e-16
    )
    assert v8_module._stable_sigmoid(0.0) == 0.5
    assert v8_module._stable_sigmoid(1000.0) == 1.0
    assert v8_module._stable_sigmoid(-1000.0) == 0.0

    with pytest.raises(RuntimeError, match="do not sum to six"):
        v8_module._validate_probabilities(
            (FAIR_PROBABILITY + 2.0e-12, *((FAIR_PROBABILITY,) * 48))
        )
    with pytest.raises(RuntimeError, match="probability contract"):
        v8_module._validate_probabilities((0.0, *((FAIR_PROBABILITY,) * 48)))


def test_v8_active_history_requires_origin_and_strict_chronology():
    history = _spectral_history()
    target_date = history[-1].draw_date + timedelta(days=3)
    shifted = [
        Draw(draw.draw_date + timedelta(days=3), draw.numbers, draw.bonus)
        for draw in history
    ]
    duplicate = [*history[:-1], Draw(history[-2].draw_date, history[-1].numbers, 7)]

    assert V8SpectralPhaseModel().predict(shifted[:103], target_date) == {
        number: FAIR_PROBABILITY for number in range(1, 50)
    }
    with pytest.raises(ValueError, match="begin on 2019-05-15"):
        V8SpectralPhaseModel().predict(
            shifted,
            shifted[-1].draw_date + timedelta(days=3),
        )
    with pytest.raises(ValueError, match="must not be empty"):
        V8SpectralPhaseModel().predict([], target_date)
    with pytest.raises(ValueError, match="chronological"):
        V8SpectralPhaseModel().predict(
            [*history[:-2], history[-1], history[-2]],
            target_date,
        )
    with pytest.raises(ValueError, match="unique"):
        V8SpectralPhaseModel().predict(duplicate, target_date)
    with pytest.raises(ValueError, match="strictly before"):
        V8SpectralPhaseModel().predict(history, history[-1].draw_date)


def test_v8_controls_are_prefix_stable_after_a_future_append():
    history = _distinct_row_history(105)
    old_history = history[:104]
    old_target_date = history[104].draw_date

    models = (
        V8SpectralPhaseModel(),
        V8SpectralPhaseRowControlModel(),
        V8SpectralPhaseRotationControlModel(),
    )
    before = [model.predict(old_history, old_target_date) for model in models]

    for model in models:
        model.predict(history, history[-1].draw_date + timedelta(days=3))
    after = [model.predict(history[:104], old_target_date) for model in models]

    assert after == before


def test_v8_phase_control_preserves_candidate_coefficients_and_amplitudes():
    history = _distinct_row_history(104)
    target_date = history[-1].draw_date + timedelta(days=3)

    candidate = analyze_spectral_phase(history, target_date)
    control = analyze_spectral_phase_rotation_control(history, target_date)

    assert control.cosine_coefficients == candidate.cosine_coefficients
    assert control.sine_coefficients == candidate.sine_coefficients
    assert [
        math.hypot(cosine, sine)
        for cosine, sine in zip(
            control.cosine_coefficients,
            control.sine_coefficients,
        )
    ] == pytest.approx(
        [
            math.hypot(cosine, sine)
            for cosine, sine in zip(
                candidate.cosine_coefficients,
                candidate.sine_coefficients,
            )
        ],
        rel=0.0,
        abs=0.0,
    )


def test_v8_row_control_requires_a_complete_bonus_for_every_active_row():
    history = _distinct_row_history(104)
    incomplete = [*history[:-1], Draw(history[-1].draw_date, history[-1].numbers)]

    with pytest.raises(ValueError, match="complete main-plus-bonus"):
        V8SpectralPhaseRowControlModel().predict(
            incomplete,
            history[-1].draw_date + timedelta(days=3),
        )


def test_v8_constants_config_and_registry_are_locked_to_implementation():
    cfg = load_config(ROOT / "config" / "research-v8-fixed-spectral-phase.yaml")
    registration = load_experiment_registry(
        ROOT / "docs" / "experiments" / "registry.yaml"
    ).get("V8_fixed_recurrence_harmonic")
    parameters = registration.parameters

    assert registration.model_name == V8SpectralPhaseModel.name
    assert registration.model_version == "v8.0.0"
    assert registration.seed == CONTROL_SEED == 649
    assert RNG_START_DATE.isoformat() == parameters["post_rng_start_date"]
    assert ACTIVE_MINIMUM_POST_RNG_DRAWS == parameters[
        "active_minimum_post_rng_prior_draws"
    ]
    assert FAIR_PROBABILITY == parameters["fair_inclusion_probability"]
    assert FIXED_PERIOD_DRAWS == parameters["fixed_period_draws"]
    assert parameters["fixed_angular_frequency"] == "12*pi/49"
    assert BISECTION_ITERATIONS == parameters["bisection_iterations"]
    assert PROBABILITY_SUM_ABSOLUTE_TOLERANCE == parameters[
        "probability_sum_absolute_tolerance"
    ]
    assert PROBABILITY_SUM_ABSOLUTE_TOLERANCE == cfg["research"][
        "probability_sum_absolute_tolerance"
    ]
    assert ROW_CONTROL_DOMAIN in parameters["row_control_domain"]
    assert PHASE_CONTROL_DOMAIN in parameters["phase_control_domain"]
    assert cfg["backtest"]["models"] == [V8SpectralPhaseModel.name]
    assert cfg["live"] == {"enabled": False, "models": [], "shadow_models": []}


@pytest.mark.parametrize(
    "model_name",
    [
        "v8_spectral_phase",
        "v8_spectral_phase_row_control",
        "v8_spectral_phase_rotation_control",
    ],
)
def test_v8_candidate_and_controls_use_the_same_real_backtest_scoring_seam(
    model_name,
):
    draws = _distinct_row_history(105)
    target = draws[-1]
    cfg = load_config(ROOT / "config" / "research-v8-fixed-spectral-phase.yaml")
    cfg["backtest"]["models"] = [model_name]
    cfg["backtest"]["model_versions"][model_name] = "v8.0.0"

    frame = run_backtest(
        draws,
        cfg,
        date.fromisoformat(target.draw_date.isoformat()),
        date.fromisoformat(target.draw_date.isoformat()),
    )

    assert list(frame["target_draw_date"]) == [target.draw_date.isoformat()]
    assert list(frame["model_name"]) == [model_name]
    assert list(frame["actual"]) == [list(target.numbers)]
    assert list(frame["bonus"]) == [target.bonus]
