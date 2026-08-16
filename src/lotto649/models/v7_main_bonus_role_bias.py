from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import math

from .base import ProbabilityModel
from ..domain import Draw
from ..research_protocol import assert_history_precedes_target


RNG_START_DATE = date(2019, 5, 15)
ACTIVE_MINIMUM_POST_RNG_DRAWS = 104
MAIN_ROLE_PSEUDOCOUNT = 3.0
BONUS_ROLE_PSEUDOCOUNT = 0.5
FAIR_MAIN_TO_BONUS_ODDS = 6.0
FAIR_PROBABILITY = 6.0 / 49.0
BISECTION_ITERATIONS = 256
BISECTION_BASE_BOUND = 64.0
PROBABILITY_SUM_ABSOLUTE_TOLERANCE = 1.0e-12
CONTROL_SEED = 649


@dataclass(frozen=True)
class MainBonusRoleAnalysis:
    post_rng_draw_count: int
    main_counts: tuple[int, ...]
    bonus_counts: tuple[int, ...]
    signals: tuple[float, ...]
    active: bool
    intercept: float | None
    probabilities: tuple[float, ...]


def _stable_sigmoid(value: float) -> float:
    if value >= 0.0:
        return 1.0 / (1.0 + math.exp(-value))
    exponential = math.exp(value)
    return exponential / (1.0 + exponential)


def _exact_fair_probabilities() -> tuple[float, ...]:
    return (FAIR_PROBABILITY,) * 49


def _validate_probabilities(probabilities: tuple[float, ...]) -> None:
    if len(probabilities) != 49:
        raise RuntimeError("v7_main_bonus_role_bias must produce exactly 49 probabilities")
    if not all(math.isfinite(value) for value in probabilities):
        raise RuntimeError("v7_main_bonus_role_bias produced non-finite probabilities")
    if not all(0.0 < value < 1.0 for value in probabilities):
        raise RuntimeError("v7_main_bonus_role_bias violated the probability contract")
    if not math.isclose(
        sum(probabilities),
        6.0,
        rel_tol=0.0,
        abs_tol=PROBABILITY_SUM_ABSOLUTE_TOLERANCE,
    ):
        raise RuntimeError("v7_main_bonus_role_bias probabilities do not sum to six")


def _analysis_after_chronology_check(
    history: list[Draw], target_date: date
) -> MainBonusRoleAnalysis:
    post_rng_history = [
        draw
        for draw in history
        if RNG_START_DATE <= draw.draw_date < target_date
    ]
    main_counts = [0] * 49
    bonus_counts = [0] * 49
    for draw in post_rng_history:
        if draw.bonus is None:
            raise ValueError(
                "v7_main_bonus_role_bias requires a bonus role for every post-RNG draw"
            )
        for number in draw.numbers:
            main_counts[number - 1] += 1
        bonus_counts[draw.bonus - 1] += 1

    active = len(post_rng_history) >= ACTIVE_MINIMUM_POST_RNG_DRAWS
    if not active:
        signals = (0.0,) * 49
        probabilities = _exact_fair_probabilities()
        _validate_probabilities(probabilities)
        return MainBonusRoleAnalysis(
            post_rng_draw_count=len(post_rng_history),
            main_counts=tuple(main_counts),
            bonus_counts=tuple(bonus_counts),
            signals=signals,
            active=False,
            intercept=None,
            probabilities=probabilities,
        )

    signals = tuple(
        math.log(
            (main_count + MAIN_ROLE_PSEUDOCOUNT)
            / (bonus_count + BONUS_ROLE_PSEUDOCOUNT)
        )
        - math.log(FAIR_MAIN_TO_BONUS_ODDS)
        for main_count, bonus_count in zip(main_counts, bonus_counts)
    )
    if all(signal == 0.0 for signal in signals):
        probabilities = _exact_fair_probabilities()
        _validate_probabilities(probabilities)
        return MainBonusRoleAnalysis(
            post_rng_draw_count=len(post_rng_history),
            main_counts=tuple(main_counts),
            bonus_counts=tuple(bonus_counts),
            signals=signals,
            active=True,
            intercept=None,
            probabilities=probabilities,
        )

    maximum_absolute_signal = max(abs(signal) for signal in signals)
    lower = -BISECTION_BASE_BOUND - maximum_absolute_signal
    upper = BISECTION_BASE_BOUND + maximum_absolute_signal
    original_lower = lower
    original_upper = upper

    lower_sum = sum(_stable_sigmoid(lower + signal) for signal in signals)
    upper_sum = sum(_stable_sigmoid(upper + signal) for signal in signals)
    if not lower_sum < 6.0 < upper_sum:
        raise RuntimeError("v7_main_bonus_role_bias failed to strictly bracket its intercept")

    for _ in range(BISECTION_ITERATIONS):
        midpoint = (lower + upper) / 2.0
        midpoint_sum = sum(
            _stable_sigmoid(midpoint + signal) for signal in signals
        )
        if midpoint_sum > 6.0:
            upper = midpoint
        else:
            lower = midpoint

    intercept = (lower + upper) / 2.0
    if not original_lower < intercept < original_upper:
        raise RuntimeError("v7_main_bonus_role_bias intercept is not strictly interior")
    probabilities = tuple(
        _stable_sigmoid(intercept + signal) for signal in signals
    )
    _validate_probabilities(probabilities)
    return MainBonusRoleAnalysis(
        post_rng_draw_count=len(post_rng_history),
        main_counts=tuple(main_counts),
        bonus_counts=tuple(bonus_counts),
        signals=signals,
        active=True,
        intercept=intercept,
        probabilities=probabilities,
    )


def analyze_main_bonus_role_bias(
    history: list[Draw], target_date: date
) -> MainBonusRoleAnalysis:
    assert_history_precedes_target(history, target_date)
    return _analysis_after_chronology_check(history, target_date)


class V7MainBonusRoleBiasModel(ProbabilityModel):
    """Frozen v7.0.0 post-RNG main/bonus role-bias candidate."""

    name = "v7_main_bonus_role_bias"

    def predict(self, history: list[Draw], target_date: date) -> dict[int, float]:
        assert_history_precedes_target(history, target_date)
        analysis = _analysis_after_chronology_check(history, target_date)
        return {
            number: analysis.probabilities[number - 1]
            for number in range(1, 50)
        }


class V7MainBonusRoleControlModel(ProbabilityModel):
    """Registered seed-649 within-draw historical role negative control."""

    name = "v7_main_bonus_role_control"

    def predict(self, history: list[Draw], target_date: date) -> dict[int, float]:
        assert_history_precedes_target(history, target_date)
        from ..research_protocol import reassign_bonus_roles_within_draws

        transformed_history = reassign_bonus_roles_within_draws(
            history,
            seed=CONTROL_SEED,
            start_date=RNG_START_DATE,
        )
        return V7MainBonusRoleBiasModel().predict(transformed_history, target_date)
