from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from hashlib import sha256
import math

from .base import ProbabilityModel
from ..domain import Draw
from ..research_protocol import assert_history_precedes_target


RNG_START_DATE = date(2019, 5, 15)
ACTIVE_MINIMUM_POST_RNG_DRAWS = 104
FAIR_PROBABILITY = 6.0 / 49.0
FIXED_PERIOD_DRAWS = 49.0 / 6.0
FIXED_ANGULAR_FREQUENCY = 12.0 * math.pi / 49.0
BISECTION_ITERATIONS = 256
BISECTION_BASE_BOUND = 64.0
PROBABILITY_SUM_ABSOLUTE_TOLERANCE = 1.0e-12
CONTROL_SEED = 649
ROW_CONTROL_DOMAIN = "lotto649-v8-prefix-control-v1"
PHASE_CONTROL_DOMAIN = "lotto649-v8-phase-control-v1"
UINT64_DENOMINATOR = 1 << 64


@dataclass(frozen=True)
class SpectralPhaseAnalysis:
    post_rng_draw_count: int
    cosine_coefficients: tuple[float, ...]
    sine_coefficients: tuple[float, ...]
    forecast_phase: float | None
    scores: tuple[float, ...]
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
        raise RuntimeError("v8_spectral_phase must produce exactly 49 probabilities")
    if not all(math.isfinite(value) for value in probabilities):
        raise RuntimeError("v8_spectral_phase produced non-finite probabilities")
    if not all(0.0 < value < 1.0 for value in probabilities):
        raise RuntimeError("v8_spectral_phase violated the probability contract")
    if not math.isclose(
        sum(probabilities),
        6.0,
        rel_tol=0.0,
        abs_tol=PROBABILITY_SUM_ABSOLUTE_TOLERANCE,
    ):
        raise RuntimeError("v8_spectral_phase probabilities do not sum to six")


def _map_scores_to_probabilities(
    scores: tuple[float, ...],
) -> tuple[float | None, tuple[float, ...]]:
    if len(scores) != 49 or not all(math.isfinite(score) for score in scores):
        raise RuntimeError("v8_spectral_phase produced invalid forecast scores")
    if all(score == 0.0 for score in scores):
        probabilities = _exact_fair_probabilities()
        _validate_probabilities(probabilities)
        return None, probabilities

    maximum_absolute_score = max(abs(score) for score in scores)
    lower = -BISECTION_BASE_BOUND - maximum_absolute_score
    upper = BISECTION_BASE_BOUND + maximum_absolute_score
    original_lower = lower
    original_upper = upper

    lower_sum = sum(_stable_sigmoid(lower + score) for score in scores)
    upper_sum = sum(_stable_sigmoid(upper + score) for score in scores)
    if not lower_sum < 6.0 < upper_sum:
        raise RuntimeError("v8_spectral_phase failed to strictly bracket its intercept")

    for _ in range(BISECTION_ITERATIONS):
        midpoint = (lower + upper) / 2.0
        midpoint_sum = sum(_stable_sigmoid(midpoint + score) for score in scores)
        if midpoint_sum > 6.0:
            upper = midpoint
        else:
            lower = midpoint

    intercept = (lower + upper) / 2.0
    if not original_lower < intercept < original_upper:
        raise RuntimeError("v8_spectral_phase intercept is not strictly interior")
    probabilities = tuple(
        _stable_sigmoid(intercept + score) for score in scores
    )
    _validate_probabilities(probabilities)
    return intercept, probabilities


def _analysis_after_chronology_check(
    history: list[Draw],
    target_date: date,
    *,
    rotate_phase: bool = False,
) -> SpectralPhaseAnalysis:
    post_rng_history = [
        draw for draw in history if RNG_START_DATE <= draw.draw_date < target_date
    ]
    draw_count = len(post_rng_history)
    zeroes = (0.0,) * 49
    if draw_count < ACTIVE_MINIMUM_POST_RNG_DRAWS:
        probabilities = _exact_fair_probabilities()
        _validate_probabilities(probabilities)
        return SpectralPhaseAnalysis(
            post_rng_draw_count=draw_count,
            cosine_coefficients=zeroes,
            sine_coefficients=zeroes,
            forecast_phase=None,
            scores=zeroes,
            active=False,
            intercept=None,
            probabilities=probabilities,
        )
    if post_rng_history[0].draw_date != RNG_START_DATE:
        raise ValueError(
            "active v8_spectral_phase history must begin on 2019-05-15"
        )

    cosine_basis = tuple(
        math.cos(FIXED_ANGULAR_FREQUENCY * index)
        for index in range(draw_count)
    )
    sine_basis = tuple(
        math.sin(FIXED_ANGULAR_FREQUENCY * index)
        for index in range(draw_count)
    )
    scale = 2.0 / float(draw_count)
    cosine_coefficients = []
    sine_coefficients = []
    for number in range(1, 50):
        centered = tuple(
            (1.0 if number in draw.numbers else 0.0) - FAIR_PROBABILITY
            for draw in post_rng_history
        )
        cosine_coefficients.append(
            scale
            * math.fsum(
                value * cosine_basis[index]
                for index, value in enumerate(centered)
            )
        )
        sine_coefficients.append(
            scale
            * math.fsum(
                value * sine_basis[index]
                for index, value in enumerate(centered)
            )
        )
    coefficients_a = tuple(cosine_coefficients)
    coefficients_b = tuple(sine_coefficients)
    if not all(
        math.isfinite(value) for value in (*coefficients_a, *coefficients_b)
    ):
        raise RuntimeError("v8_spectral_phase produced non-finite coefficients")

    forecast_phase = FIXED_ANGULAR_FREQUENCY * draw_count
    if rotate_phase:
        rotated_scores = []
        for number, (coefficient_a, coefficient_b) in enumerate(
            zip(coefficients_a, coefficients_b),
            start=1,
        ):
            rotated_phase = (
                forecast_phase + spectral_phase_rotation_angle(number)
            )
            rotated_scores.append(
                coefficient_a * math.cos(rotated_phase)
                + coefficient_b * math.sin(rotated_phase)
            )
        scores = tuple(rotated_scores)
    else:
        cosine_target = math.cos(forecast_phase)
        sine_target = math.sin(forecast_phase)
        scores = tuple(
            coefficient_a * cosine_target + coefficient_b * sine_target
            for coefficient_a, coefficient_b in zip(
                coefficients_a,
                coefficients_b,
            )
        )
    intercept, probabilities = _map_scores_to_probabilities(scores)
    return SpectralPhaseAnalysis(
        post_rng_draw_count=draw_count,
        cosine_coefficients=coefficients_a,
        sine_coefficients=coefficients_b,
        forecast_phase=forecast_phase,
        scores=scores,
        active=True,
        intercept=intercept,
        probabilities=probabilities,
    )


def analyze_spectral_phase(
    history: list[Draw],
    target_date: date,
) -> SpectralPhaseAnalysis:
    assert_history_precedes_target(history, target_date)
    return _analysis_after_chronology_check(history, target_date)


def _row_control_digest(draw_count: int, index: int) -> bytes:
    payload = f"{ROW_CONTROL_DOMAIN}:{CONTROL_SEED}:{draw_count}:{index}".encode()
    return sha256(payload).digest()


def strict_prefix_row_permutation_indices(draw_count: int) -> tuple[int, ...]:
    if draw_count < 1:
        raise ValueError("row-control draw count must be positive")
    order = tuple(
        sorted(
            range(draw_count),
            key=lambda index: (_row_control_digest(draw_count, index), index),
        )
    )
    identity = tuple(range(draw_count))
    if order == identity:
        return (*identity[1:], identity[0])
    return order


def spectral_phase_rotation_angle(number: int) -> float:
    if number not in range(1, 50):
        raise ValueError("phase-control number must be in 1..49")
    payload = f"{PHASE_CONTROL_DOMAIN}:{CONTROL_SEED}:{number}".encode()
    raw = int.from_bytes(sha256(payload).digest()[:8], byteorder="big")
    return 2.0 * math.pi * (raw / UINT64_DENOMINATOR)


def permute_v8_post_rng_prefix(
    history: list[Draw],
    target_date: date,
) -> list[Draw]:
    assert_history_precedes_target(history, target_date)
    post_rng_positions = [
        index
        for index, draw in enumerate(history)
        if RNG_START_DATE <= draw.draw_date < target_date
    ]
    draw_count = len(post_rng_positions)
    if draw_count < ACTIVE_MINIMUM_POST_RNG_DRAWS:
        return list(history)
    if history[post_rng_positions[0]].draw_date != RNG_START_DATE:
        raise ValueError(
            "active v8_spectral_phase history must begin on 2019-05-15"
        )
    if any(history[position].bonus is None for position in post_rng_positions):
        raise ValueError("V8 row control requires complete main-plus-bonus rows")

    source_order = strict_prefix_row_permutation_indices(draw_count)
    transformed = list(history)
    for destination_offset, source_offset in enumerate(source_order):
        destination_position = post_rng_positions[destination_offset]
        source = history[post_rng_positions[source_offset]]
        transformed[destination_position] = Draw(
            history[destination_position].draw_date,
            source.numbers,
            source.bonus,
        )
    return transformed


def analyze_spectral_phase_rotation_control(
    history: list[Draw],
    target_date: date,
) -> SpectralPhaseAnalysis:
    assert_history_precedes_target(history, target_date)
    return _analysis_after_chronology_check(
        history,
        target_date,
        rotate_phase=True,
    )


class V8SpectralPhaseModel(ProbabilityModel):
    """Frozen v8.0.0 fixed-recurrence spectral-phase candidate."""

    name = "v8_spectral_phase"

    def predict(self, history: list[Draw], target_date: date) -> dict[int, float]:
        analysis = analyze_spectral_phase(history, target_date)
        return {
            number: analysis.probabilities[number - 1]
            for number in range(1, 50)
        }


class V8SpectralPhaseRowControlModel(ProbabilityModel):
    """Frozen strict-prefix complete-row temporal permutation control."""

    name = "v8_spectral_phase_row_control"

    def predict(self, history: list[Draw], target_date: date) -> dict[int, float]:
        transformed = permute_v8_post_rng_prefix(history, target_date)
        return V8SpectralPhaseModel().predict(transformed, target_date)


class V8SpectralPhaseRotationControlModel(ProbabilityModel):
    """Frozen per-label coefficient-phase stress control."""

    name = "v8_spectral_phase_rotation_control"

    def predict(self, history: list[Draw], target_date: date) -> dict[int, float]:
        analysis = analyze_spectral_phase_rotation_control(history, target_date)
        return {
            number: analysis.probabilities[number - 1]
            for number in range(1, 50)
        }
