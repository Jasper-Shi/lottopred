"""Outcome-blind deterministic core for the registered V12 parity transition.

This module owns no history loader, artifact writer, or execution authority.
Callers may provide only already-available draws to its pure scientific seam.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import date
from fractions import Fraction
from itertools import pairwise
from typing import Self

from ..domain import Draw

BUCKET_COUNTS = (
    134_596,
    1_062_600,
    3_187_800,
    4_655_200,
    3_491_400,
    1_275_120,
    177_100,
)
FAIR_SET_COUNT = 13_983_816
FAIR_MEAN = float.fromhex("0x1.87d6343eb1a1fp+1")
FAIR_VARIANCE = float.fromhex("0x1.57db526b4310cp+0")
FAIR_STANDARD_DEVIATION = float.fromhex("0x1.28b1a92291f40p+0")
STANDARDIZED_BUCKET_STATES = tuple(
    float.fromhex(encoded)
    for encoded in (
        "-0x1.5217d88c9a696p+1",
        "-0x1.c74c7c5dc5b37p+0",
        "-0x1.d4d28f44ad284p-1",
        "-0x1.b0c25cdcee9a3p-5",
        "0x1.9eba43a90f550p-1",
        "0x1.ac40568ff6c9dp+0",
        "0x1.4491c5a5b2f49p+1",
    )
)

_THEORETICAL_FAIR_MEAN = 150.0 / 49.0
_THEORETICAL_FAIR_VARIANCE = 3225.0 / 2401.0
_THEORETICAL_FAIR_STANDARD_DEVIATION = math.sqrt(_THEORETICAL_FAIR_VARIANCE)
_THEORETICAL_BUCKET_STATES = tuple(
    (float(bucket) - _THEORETICAL_FAIR_MEAN) / _THEORETICAL_FAIR_STANDARD_DEVIATION
    for bucket in range(7)
)
if (
    FAIR_MEAN != _THEORETICAL_FAIR_MEAN
    or FAIR_VARIANCE != _THEORETICAL_FAIR_VARIANCE
    or FAIR_STANDARD_DEVIATION != _THEORETICAL_FAIR_STANDARD_DEVIATION
    or STANDARDIZED_BUCKET_STATES != _THEORETICAL_BUCKET_STATES
):
    raise RuntimeError("registered V12 binary64 constants disagree with theory")

TRUE_ODD_LABELS = frozenset(range(1, 50, 2))
PSEUDO_PARTITION_BYTES = (
    b"1,2,5,6,7,8,9,10,12,16,17,18,20,24,28,29,32,33,40,41,42,43,44,48,49"
)
PSEUDO_PARTITION_SHA256 = (
    "bfbb8cb711e0734aea8a29f6c02aee41a0f39a36643b3155245dc3550bbf14dd"
)
PSEUDO_PARTITION_LABELS = frozenset(
    int(raw_label) for raw_label in PSEUDO_PARTITION_BYTES.decode("ascii").split(",")
)
_ALL_LABELS = frozenset(range(1, 50))
TRUE_PSEUDO_CONTINGENCY = (
    (
        len(TRUE_ODD_LABELS & PSEUDO_PARTITION_LABELS),
        len(TRUE_ODD_LABELS - PSEUDO_PARTITION_LABELS),
    ),
    (
        len(PSEUDO_PARTITION_LABELS - TRUE_ODD_LABELS),
        len(_ALL_LABELS - TRUE_ODD_LABELS - PSEUDO_PARTITION_LABELS),
    ),
)
_TRUE_PSEUDO_JOINT = Fraction(TRUE_PSEUDO_CONTINGENCY[0][0], 49)
_LABEL_PARTITION_MARGINAL = Fraction(25, 49)
TRUE_PSEUDO_LABEL_CORRELATION = (_TRUE_PSEUDO_JOINT - _LABEL_PARTITION_MARGINAL**2) / (
    _LABEL_PARTITION_MARGINAL * Fraction(24, 49)
)

if (
    len(TRUE_ODD_LABELS) != 25
    or len(PSEUDO_PARTITION_LABELS) != 25
    or hashlib.sha256(PSEUDO_PARTITION_BYTES).hexdigest() != PSEUDO_PARTITION_SHA256
    or TRUE_PSEUDO_CONTINGENCY != ((10, 15), (15, 9))
    or TRUE_PSEUDO_LABEL_CORRELATION != Fraction(-9, 40)
):
    raise RuntimeError("registered V12 label partitions are inconsistent")

RNG_REGIME_START = date(2019, 5, 15)
CANDIDATE_MODEL_NAME = "v12_post_rng_parity_composition_transition"
CONTROL_MODEL_NAME = "v12_pseudo_parity_composition_transition_control"


@dataclass(frozen=True)
class LabelPartition:
    name: str
    selected_labels: frozenset[int]

    def __post_init__(self) -> None:
        if (
            type(self.name) is not str
            or not self.name
            or type(self.selected_labels) is not frozenset
            or len(self.selected_labels) != 25
            or any(
                type(label) is not int or not 1 <= label <= 49
                for label in self.selected_labels
            )
        ):
            raise ValueError("V12 label partition is invalid")


TRUE_PARITY_PARTITION = LabelPartition("true_odd", TRUE_ODD_LABELS)
PSEUDO_PARITY_PARTITION = LabelPartition(
    "pseudo_odd",
    PSEUDO_PARTITION_LABELS,
)


@dataclass(frozen=True)
class TransitionRow:
    destination_date: date
    x_source: float
    destination_bucket: int


@dataclass(frozen=True)
class TransitionPrefix:
    history_through: date
    transitions: tuple[TransitionRow, ...]
    previous_bucket: int
    x_prev: float


def build_transition_prefix(
    draws: Iterable[Draw],
    target_date: date,
    partition: LabelPartition,
) -> TransitionPrefix:
    """Build the registered adjacent transition prefix strictly before target."""

    if type(target_date) is not date:
        raise ValueError("target date must be a date")
    if partition not in {TRUE_PARITY_PARTITION, PSEUDO_PARITY_PARTITION}:
        raise ValueError("partition is not registered for V12")
    observed = tuple(draws)
    if any(
        type(draw) is not Draw or type(draw.draw_date) is not date for draw in observed
    ):
        raise ValueError("draw sequence is invalid")
    dates = tuple(draw.draw_date for draw in observed)
    if any(later <= earlier for earlier, later in pairwise(dates)):
        raise ValueError("draw dates must be unique and strictly increasing")
    if any(draw_date >= target_date for draw_date in dates):
        raise ValueError("every supplied draw must be strictly before target")
    prefix = tuple(draw for draw in observed if draw.draw_date >= RNG_REGIME_START)
    if not prefix:
        raise ValueError("target has no eligible post-RNG prefix")

    selected = partition.selected_labels
    buckets = tuple(
        sum(number in selected for number in draw.numbers) for draw in prefix
    )
    transitions = tuple(
        TransitionRow(
            destination_date=destination.draw_date,
            x_source=STANDARDIZED_BUCKET_STATES[buckets[index - 1]],
            destination_bucket=buckets[index],
        )
        for index, destination in enumerate(prefix)
        if index > 0
    )
    previous_bucket = buckets[-1]
    return TransitionPrefix(
        history_through=prefix[-1].draw_date,
        transitions=transitions,
        previous_bucket=previous_bucket,
        x_prev=STANDARDIZED_BUCKET_STATES[previous_bucket],
    )


@dataclass(frozen=True)
class TiltedMoment:
    expected_bucket: float
    log_z: float


@dataclass(frozen=True)
class MapFit:
    beta: float
    bracket_radius: float


@dataclass(frozen=True, init=False)
class ParityForecast:
    model_name: str
    target_date: date
    history_through: date
    transition_count: int
    previous_bucket: int
    x_prev: float
    beta: float
    eta: float
    expected_bucket: float
    log_z: float
    probabilities: tuple[tuple[int, float], ...]
    ranking: tuple[int, ...]
    top6: tuple[int, ...]
    top12: tuple[int, ...]
    top18: tuple[int, ...]
    final6: tuple[int, ...]

    def __new__(cls, *_args: object, **_kwargs: object) -> Self:
        raise TypeError("ParityForecast may only be issued by forecast_partition")

    def __post_init__(self) -> None:
        if (
            type(self.model_name) is not str
            or self.model_name not in {CANDIDATE_MODEL_NAME, CONTROL_MODEL_NAME}
            or type(self.target_date) is not date
            or type(self.history_through) is not date
            or self.history_through >= self.target_date
            or type(self.transition_count) is not int
            or self.transition_count < 0
            or type(self.previous_bucket) is not int
            or not 0 <= self.previous_bucket <= 6
            or type(self.x_prev) is not float
            or self.x_prev != STANDARDIZED_BUCKET_STATES[self.previous_bucket]
            or any(
                type(value) is not float or not math.isfinite(value)
                for value in (
                    self.beta,
                    self.eta,
                    self.expected_bucket,
                    self.log_z,
                )
            )
            or self.eta != self.beta * self.x_prev
            or not 0.0 < self.expected_bucket < 6.0
            or type(self.probabilities) is not tuple
            or len(self.probabilities) != 49
            or any(
                type(item) is not tuple or len(item) != 2 for item in self.probabilities
            )
            or tuple(item[0] for item in self.probabilities) != tuple(range(1, 50))
            or any(
                type(label) is not int
                or type(probability) is not float
                or not math.isfinite(probability)
                or not 0.0 < probability < 1.0
                for label, probability in self.probabilities
            )
            or abs(math.fsum(value for _, value in self.probabilities) - 6.0) > 1e-12
            or type(self.ranking) is not tuple
            or len(self.ranking) != 49
            or any(type(label) is not int for label in self.ranking)
            or set(self.ranking) != set(range(1, 50))
            or type(self.top6) is not tuple
            or type(self.top12) is not tuple
            or type(self.top18) is not tuple
            or type(self.final6) is not tuple
            or self.top6 != self.ranking[:6]
            or self.top12 != self.ranking[:12]
            or self.top18 != self.ranking[:18]
            or self.final6 != tuple(sorted(self.top6))
        ):
            raise ValueError("V12 parity forecast is invalid")
        if self.transition_count == 0 and self.beta != 0.0:
            raise ValueError("V12 parity forecast is invalid")
        if self.beta == 0.0 and (
            self.beta.hex() != "0x0.0p+0" or self.eta.hex() != "0x0.0p+0"
        ):
            raise ValueError("V12 parity forecast is invalid")
        selected_labels = (
            TRUE_ODD_LABELS
            if self.model_name == CANDIDATE_MODEL_NAME
            else PSEUDO_PARTITION_LABELS
        )
        expected_bucket, log_z, expected_probabilities = _forecast_distribution(
            self.beta,
            self.eta,
            selected_labels,
        )
        if (
            self.expected_bucket != expected_bucket
            or self.log_z != log_z
            or self.probabilities != expected_probabilities
        ):
            raise ValueError("V12 parity forecast is invalid")
        probabilities = dict(self.probabilities)
        expected_ranking = tuple(
            sorted(probabilities, key=lambda label: (-probabilities[label], label))
        )
        if self.ranking != expected_ranking:
            raise ValueError("V12 parity forecast ranking is invalid")


def tilted_moment_log_z(eta: float) -> TiltedMoment:
    """Evaluate the registered seven-bucket exponential tilt in binary64."""

    if type(eta) not in {int, float} or not math.isfinite(eta):
        raise ValueError("eta must be finite")
    eta = float(eta)
    exponents = tuple(eta * float(bucket) for bucket in range(7))
    maximum = max(exponents)
    weights = tuple(
        float(count) * math.exp(exponent - maximum)
        for count, exponent in zip(BUCKET_COUNTS, exponents, strict=True)
    )
    denominator = math.fsum(weights)
    expected_bucket = (
        math.fsum(float(bucket) * weight for bucket, weight in enumerate(weights))
        / denominator
    )
    return TiltedMoment(
        expected_bucket=expected_bucket,
        log_z=maximum + math.log(denominator),
    )


def _forecast_distribution(
    beta: float,
    eta: float,
    selected_labels: frozenset[int],
) -> tuple[float, float, tuple[tuple[int, float], ...]]:
    if beta == 0.0:
        return (
            FAIR_MEAN,
            math.log(float(FAIR_SET_COUNT)),
            tuple((label, 6.0 / 49.0) for label in range(1, 50)),
        )
    tilted = tilted_moment_log_z(eta)
    selected_probability = tilted.expected_bucket / 25.0
    complement_probability = (6.0 - tilted.expected_bucket) / 24.0
    return (
        tilted.expected_bucket,
        tilted.log_z,
        tuple(
            (
                label,
                selected_probability
                if label in selected_labels
                else complement_probability,
            )
            for label in range(1, 50)
        ),
    )


def _bisect_strict_root(
    score: Callable[[float], float],
    bracket_radius: float,
) -> float:
    low = -bracket_radius
    high = bracket_radius
    for _ in range(256):
        midpoint = low + (high - low) / 2.0
        if score(midpoint) > 0.0:
            low = midpoint
        else:
            high = midpoint
    return low + (high - low) / 2.0


def solve_map_beta(transitions: Iterable[TransitionRow]) -> MapFit:
    """Solve the registered one-coefficient MAP equation by 256 bisections."""

    rows = tuple(transitions)
    if any(
        type(row) is not TransitionRow
        or type(row.destination_date) is not date
        or type(row.x_source) is not float
        or row.x_source not in STANDARDIZED_BUCKET_STATES
        or type(row.destination_bucket) is not int
        or not 0 <= row.destination_bucket <= 6
        for row in rows
    ):
        raise ValueError("transition rows are invalid")
    if any(
        later.destination_date <= earlier.destination_date
        for earlier, later in pairwise(rows)
    ):
        raise ValueError("transition destinations must be strictly increasing")
    if not rows:
        return MapFit(beta=0.0, bracket_radius=0.0)

    def score(beta: float) -> float:
        return math.fsum(
            [
                -beta,
                *(
                    row.x_source
                    * (
                        float(row.destination_bucket)
                        - tilted_moment_log_z(beta * row.x_source).expected_bucket
                    )
                    for row in rows
                ),
            ]
        )

    if score(0.0) == 0.0:
        return MapFit(beta=0.0, bracket_radius=0.0)
    bracket = 1.0 + 6.0 * math.fsum(abs(row.x_source) for row in rows)
    low = -bracket
    high = bracket
    if not score(low) > 0.0 or not score(high) < 0.0:
        raise ArithmeticError("registered MAP bracket is not strict")
    return MapFit(
        beta=_bisect_strict_root(score, bracket),
        bracket_radius=bracket,
    )


def forecast_partition(
    history_prefix: Iterable[Draw],
    target_date: date,
    *,
    partition: LabelPartition,
    model_name: str,
) -> ParityForecast:
    """Forecast from one already-released strict prefix and registered partition."""

    expected_model_name = {
        TRUE_PARITY_PARTITION: CANDIDATE_MODEL_NAME,
        PSEUDO_PARITY_PARTITION: CONTROL_MODEL_NAME,
    }.get(partition)
    if model_name != expected_model_name:
        raise ValueError("model name and registered partition do not agree")
    prefix = build_transition_prefix(history_prefix, target_date, partition)
    fit = solve_map_beta(prefix.transitions)
    beta = fit.beta
    eta = beta * prefix.x_prev
    if beta == 0.0:
        eta = 0.0
    expected_bucket, log_z, probabilities = _forecast_distribution(
        beta,
        eta,
        partition.selected_labels,
    )
    probability_map = dict(probabilities)
    ranking = tuple(
        sorted(
            probability_map,
            key=lambda label: (-probability_map[label], label),
        )
    )
    forecast = object.__new__(ParityForecast)
    for field_name, value in (
        ("model_name", model_name),
        ("target_date", target_date),
        ("history_through", prefix.history_through),
        ("transition_count", len(prefix.transitions)),
        ("previous_bucket", prefix.previous_bucket),
        ("x_prev", prefix.x_prev),
        ("beta", beta),
        ("eta", eta),
        ("expected_bucket", expected_bucket),
        ("log_z", log_z),
        ("probabilities", probabilities),
        ("ranking", ranking),
        ("top6", ranking[:6]),
        ("top12", ranking[:12]),
        ("top18", ranking[:18]),
        ("final6", tuple(sorted(ranking[:6]))),
    ):
        object.__setattr__(forecast, field_name, value)
    forecast.__post_init__()
    return forecast


def forecast_candidate(
    history_prefix: Iterable[Draw],
    target_date: date,
) -> ParityForecast:
    return forecast_partition(
        history_prefix,
        target_date,
        partition=TRUE_PARITY_PARTITION,
        model_name=CANDIDATE_MODEL_NAME,
    )


def forecast_control(
    history_prefix: Iterable[Draw],
    target_date: date,
) -> ParityForecast:
    return forecast_partition(
        history_prefix,
        target_date,
        partition=PSEUDO_PARITY_PARTITION,
        model_name=CONTROL_MODEL_NAME,
    )
