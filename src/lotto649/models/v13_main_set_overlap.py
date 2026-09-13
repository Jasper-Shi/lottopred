"""Frozen V13 adjacent-main-set law; source-only, deterministic pure arithmetic.

The forecast factories require the complete strict post-RNG prefix. The separate
count-level solver/score/objective functions support closed mathematical oracles;
they do not authorize a historical forecast from an incomplete source sequence.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import date, timedelta
from itertools import pairwise
from typing import Self

MODEL_VERSION = "v13.0.0"
CANDIDATE_NAME = "v13_post_rng_main_set_overlap"
CONTROL_NAME = "v13_cyclic_anchor_overlap_control"
CANDIDATE_FEATURE_SET = "post_rng_adjacent_main_set_overlap_one_scalar_normal_prior"
CONTROL_FEATURE_SET = (
    "post_rng_adjacent_main_set_overlap_one_scalar_fixed_cyclic_source_anchor"
)
REGIME_START = date(2019, 5, 15)
N = (6096454, 5775588, 1851150, 246820, 13545, 258, 1)
LOG_N = float.fromhex("0x1.07412c1f4cc68p+4")
FAIR = 6.0 / 49.0
MAX_PAIRS = 4443
MAX_BETA = 26722.0
CYCLIC_MAP = tuple(1 + (label % 49) for label in range(1, 50))
CYCLIC_MAP_SHA256 = "6db8d037c252c737f8e3091d4961e677345cb5eee0a6cf11709b06600d557ad6"
_LABELS = tuple(range(1, 50))


class OverlapValidationError(ValueError):
    """A source, numerical, or frozen-forecast contract failed terminally."""


def _canonical(value: object) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _six(numbers: object) -> bool:
    return (
        type(numbers) is tuple
        and len(numbers) == 6
        and all(type(n) is int and 1 <= n <= 49 for n in numbers)
        and tuple(sorted(set(numbers))) == numbers
    )


@dataclass(frozen=True, slots=True)
class MainDraw:
    """An explicit date/main-only input; bonus and result metadata are absent."""

    draw_date: date
    numbers: tuple[int, ...]

    def __post_init__(self) -> None:
        if type(self.draw_date) is not date or not _six(self.numbers):
            raise OverlapValidationError("invalid main-only draw")


def _counts(counts: object) -> tuple[int, ...]:
    if (
        type(counts) not in (tuple, list)
        or len(counts) > MAX_PAIRS
        or any(type(k) is not int or not 0 <= k <= 6 for k in counts)
    ):
        raise OverlapValidationError("invalid chronological overlap counts")
    return tuple(counts)


def _beta(beta: object) -> None:
    if type(beta) is not float or not math.isfinite(beta) or abs(beta) > MAX_BETA:
        raise OverlapValidationError("invalid binary64 beta")


def moments(beta: float) -> tuple[float, float, float]:
    """Return registered mean, direct complementary moment, and log partition."""
    _beta(beta)
    if beta == 0.0:
        return 36.0 / 49.0, 258.0 / 49.0, LOG_N
    a = tuple(beta * float(k) for k in range(7))
    maximum = max(a)
    weights = tuple(float(N[k]) * math.exp(a[k] - maximum) for k in range(7))
    denominator = math.fsum(weights)
    if not math.isfinite(denominator) or denominator <= 0.0:
        raise OverlapValidationError("invalid shifted partition denominator")
    mean = math.fsum(float(k) * weights[k] for k in range(7)) / denominator
    complement = math.fsum(float(6 - k) * weights[k] for k in range(7)) / denominator
    log_z = maximum + math.log(denominator)
    if not all(math.isfinite(v) for v in (mean, complement, log_z)):
        raise OverlapValidationError("nonfinite overlap moments")
    return mean, complement, log_z


def _score(beta: float, counts: tuple[int, ...]) -> float:
    mean, _, _ = moments(beta)
    result = math.fsum([-beta, *(float(k) - mean for k in counts)])
    if not math.isfinite(result):
        raise OverlapValidationError("nonfinite overlap score")
    return result


def map_score(beta: float, counts: tuple[int, ...] | list[int]) -> float:
    """Count-level oracle API, not a source-prefix forecast factory."""
    return _score(beta, _counts(counts))


def map_objective(beta: float, counts: tuple[int, ...] | list[int]) -> float:
    """Evaluate the exact chronological binary64 objective on validated counts."""
    values = _counts(counts)
    _, _, log_z = moments(beta)
    result = math.fsum(
        [-0.5 * (beta * beta), *(beta * float(k) - log_z for k in values)]
    )
    if not math.isfinite(result):
        raise OverlapValidationError("nonfinite overlap objective")
    return result


def solve_map_beta(counts: tuple[int, ...] | list[int]) -> float:
    """Exactly 256 bisections, except the registered integer-zero bypass."""
    values = _counts(counts)
    residual = 49 * sum(values) - 36 * len(values)
    if not values or residual == 0:
        return 0.0
    bound = float(6 * len(values) + 64)
    at_zero = _score(0.0, values)
    if (
        not math.isfinite(at_zero)
        or at_zero == 0.0
        or (at_zero > 0.0) != (residual > 0)
    ):
        raise OverlapValidationError("integer and binary64 score signs disagree")
    lo, hi = (0.0, bound) if residual > 0 else (-bound, 0.0)
    lower_score, upper_score = _score(lo, values), _score(hi, values)
    if not (
        math.isfinite(lower_score)
        and math.isfinite(upper_score)
        and lower_score > 0.0
        and upper_score < 0.0
    ):
        raise OverlapValidationError("overlap root lacks strict finite endpoints")
    for _ in range(256):
        midpoint = lo + (hi - lo) / 2.0
        midpoint_score = _score(midpoint, values)
        if not math.isfinite(midpoint_score):
            raise OverlapValidationError("nonfinite midpoint score")
        if midpoint_score > 0.0:
            lo = midpoint
        else:
            hi = midpoint
    result = lo + (hi - lo) / 2.0
    if not math.isfinite(result) or result == 0.0 or (result > 0.0) != (residual > 0):
        raise OverlapValidationError("invalid terminal overlap root")
    return result


def _next_draw(value: date) -> date:
    return value + timedelta(days=3 if value.weekday() == 2 else 4)


def _prefix(history_prefix: object, target_date: date) -> tuple[MainDraw, ...]:
    if (
        type(target_date) is not date
        or target_date <= REGIME_START
        or target_date.weekday() not in (2, 5)
        or type(history_prefix) not in (tuple, list)
        or not history_prefix
        or len(history_prefix) > MAX_PAIRS + 1
    ):
        raise OverlapValidationError("invalid complete strict prefix")
    previous = None
    post_rng = []
    for row in history_prefix:
        if type(row) is not MainDraw:
            raise OverlapValidationError("prefix requires main-only draws")
        row.__post_init__()
        if row.draw_date >= target_date or (
            previous is not None and row.draw_date <= previous
        ):
            raise OverlapValidationError(
                "target, future, duplicate or unordered prefix date"
            )
        previous = row.draw_date
        if row.draw_date >= REGIME_START:
            post_rng.append(row)
    if not post_rng:
        raise OverlapValidationError("post-RNG source anchor absent")
    expected = REGIME_START
    for row in post_rng:
        if row.draw_date != expected:
            raise OverlapValidationError("missing or noncanonical post-RNG draw date")
        expected = _next_draw(expected)
    if expected != target_date:
        raise OverlapValidationError("missing trailing post-RNG draw date")
    return tuple(post_rng)


def _transformed(anchor: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(sorted(1 + (number % 49) for number in anchor))


def _distribution(
    beta: float, anchor: tuple[int, ...]
) -> tuple[float, float, float, tuple[tuple[int, float], ...]]:
    mean, complement, log_z = moments(beta)
    p_in, p_out = (FAIR, FAIR) if beta == 0.0 else (mean / 6.0, complement / 43.0)
    probabilities = tuple((n, p_in if n in anchor else p_out) for n in _LABELS)
    if (
        not all(
            type(p) is float and math.isfinite(p) and 0.0 < p < 1.0
            for _, p in probabilities
        )
        or abs(math.fsum(p for _, p in probabilities) - 6.0) > 1e-12
    ):
        raise OverlapValidationError("invalid final overlap probabilities")
    return mean, complement, log_z, probabilities


@dataclass(frozen=True, slots=True, init=False)
class OverlapForecast:
    """An immutable result issued only by the registered forecast factories."""

    model_name: str
    model_version: str
    feature_set: str
    target_date: date
    history_through: date
    source_draw_date: date
    source_anchor: tuple[int, ...]
    transformed_anchor: tuple[int, ...] | None
    training_pair_count: int
    training_overlap_sum: int
    scientific_projection_sha256: str
    counts_sha256: str
    beta: float
    beta_hex: str
    mean: float
    mean_hex: str
    complement_mean: float
    complement_mean_hex: str
    log_z: float
    log_z_hex: str
    probabilities: tuple[tuple[int, float], ...]
    probability_hex: tuple[tuple[int, str], ...]
    ranking: tuple[int, ...]
    top6: tuple[int, ...]
    top12: tuple[int, ...]
    top18: tuple[int, ...]
    final6: tuple[int, ...]

    def __new__(cls, *_args: object, **_kwargs: object) -> Self:
        raise TypeError("OverlapForecast may only be issued by registered factories")

    def __init_subclass__(cls, **kwargs: object) -> None:
        raise TypeError("OverlapForecast cannot be subclassed")


def _sha(value: object) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and all(c in "0123456789abcdef" for c in value)
    )


def validate_forecast(forecast: OverlapForecast) -> None:
    """Validate frozen state and distribution without re-reading inputs/refitting."""
    if type(forecast) is not OverlapForecast:
        raise OverlapValidationError("not an overlap forecast")
    try:
        _validate_forecast_fields(forecast)
    except AttributeError as exc:
        raise OverlapValidationError("incomplete overlap forecast") from exc


def _validate_forecast_fields(f: OverlapForecast) -> None:
    if (
        type(f.model_name) is not str
        or f.model_name not in (CANDIDATE_NAME, CONTROL_NAME)
        or type(f.model_version) is not str
        or f.model_version != MODEL_VERSION
        or type(f.feature_set) is not str
        or f.feature_set
        != (
            CANDIDATE_FEATURE_SET
            if f.model_name == CANDIDATE_NAME
            else CONTROL_FEATURE_SET
        )
        or type(f.target_date) is not date
        or f.target_date <= REGIME_START
        or f.target_date.weekday() not in (2, 5)
        or type(f.history_through) is not date
        or type(f.source_draw_date) is not date
        or f.history_through != f.source_draw_date
        or f.source_draw_date < REGIME_START
        or f.source_draw_date.weekday() not in (2, 5)
        or _next_draw(f.source_draw_date) != f.target_date
        or not _six(f.source_anchor)
        or (f.model_name == CANDIDATE_NAME and f.transformed_anchor is not None)
        or (
            f.model_name == CONTROL_NAME
            and (
                not _six(f.transformed_anchor)
                or f.transformed_anchor != _transformed(f.source_anchor)
            )
        )
        or type(f.training_pair_count) is not int
        or not 0 <= f.training_pair_count <= MAX_PAIRS
        or type(f.training_overlap_sum) is not int
        or not 0 <= f.training_overlap_sum <= 6 * f.training_pair_count
        or not _sha(f.scientific_projection_sha256)
        or not _sha(f.counts_sha256)
    ):
        raise OverlapValidationError("invalid frozen source state")
    expected_source_date = REGIME_START
    for _ in range(f.training_pair_count):
        expected_source_date = _next_draw(expected_source_date)
    if f.source_draw_date != expected_source_date:
        raise OverlapValidationError("source date and pair count disagree")
    _beta(f.beta)
    residual = 49 * f.training_overlap_sum - 36 * f.training_pair_count
    if (residual == 0 and f.beta.hex() != "0x0.0p+0") or (
        residual != 0 and (f.beta == 0.0 or (f.beta > 0.0) != (residual > 0))
    ):
        raise OverlapValidationError("stored beta violates exact integer sign rule")
    for value, hex_value in (
        (f.beta, f.beta_hex),
        (f.mean, f.mean_hex),
        (f.complement_mean, f.complement_mean_hex),
        (f.log_z, f.log_z_hex),
    ):
        if (
            type(value) is not float
            or not math.isfinite(value)
            or type(hex_value) is not str
            or hex_value != value.hex()
        ):
            raise OverlapValidationError("frozen scalar numeric/hex mismatch")
    anchor = f.source_anchor if f.transformed_anchor is None else f.transformed_anchor
    mean, complement, log_z, probabilities = _distribution(f.beta, anchor)
    if f.mean != mean or f.complement_mean != complement or f.log_z != log_z:
        raise OverlapValidationError("frozen moments disagree with law")
    if (
        type(f.probabilities) is not tuple
        or len(f.probabilities) != 49
        or any(
            type(pair) is not tuple
            or len(pair) != 2
            or type(pair[0]) is not int
            or type(pair[1]) is not float
            or not math.isfinite(pair[1])
            for pair in f.probabilities
        )
        or f.probabilities != probabilities
        or type(f.probability_hex) is not tuple
        or any(
            type(pair) is not tuple
            or len(pair) != 2
            or type(pair[0]) is not int
            or type(pair[1]) is not str
            for pair in f.probability_hex
        )
        or f.probability_hex != tuple((n, p.hex()) for n, p in probabilities)
    ):
        raise OverlapValidationError("frozen probability numeric/hex mismatch")
    probability_map = dict(probabilities)
    ranking = tuple(sorted(_LABELS, key=lambda n: (-probability_map[n], n)))
    for actual, expected in (
        (f.ranking, ranking),
        (f.top6, ranking[:6]),
        (f.top12, ranking[:12]),
        (f.top18, ranking[:18]),
        (f.final6, tuple(sorted(ranking[:6]))),
    ):
        if (
            type(actual) is not tuple
            or any(type(n) is not int for n in actual)
            or actual != expected
        ):
            raise OverlapValidationError("frozen ranking violates categorical tie rule")


def _forecast(
    history_prefix: object, target_date: date, *, control: bool
) -> OverlapForecast:
    rows = _prefix(history_prefix, target_date)
    counts = tuple(
        len(
            set(_transformed(source.numbers) if control else source.numbers)
            & set(destination.numbers)
        )
        for source, destination in pairwise(rows)
    )
    beta = solve_map_beta(counts)
    source = rows[-1]
    transformed_anchor = _transformed(source.numbers) if control else None
    anchor = source.numbers if transformed_anchor is None else transformed_anchor
    mean, complement, log_z, probabilities = _distribution(beta, anchor)
    probability_map = dict(probabilities)
    ranking = tuple(sorted(_LABELS, key=lambda n: (-probability_map[n], n)))
    forecast = object.__new__(OverlapForecast)
    for field_name, value in (
        ("model_name", CONTROL_NAME if control else CANDIDATE_NAME),
        ("model_version", MODEL_VERSION),
        ("feature_set", CONTROL_FEATURE_SET if control else CANDIDATE_FEATURE_SET),
        ("target_date", target_date),
        ("history_through", source.draw_date),
        ("source_draw_date", source.draw_date),
        ("source_anchor", source.numbers),
        ("transformed_anchor", transformed_anchor),
        ("training_pair_count", len(counts)),
        ("training_overlap_sum", sum(counts)),
        (
            "scientific_projection_sha256",
            _digest(
                [
                    {
                        "draw_date": row.draw_date.isoformat(),
                        "numbers": list(row.numbers),
                    }
                    for row in rows
                ]
            ),
        ),
        ("counts_sha256", _digest(list(counts))),
        ("beta", beta),
        ("beta_hex", beta.hex()),
        ("mean", mean),
        ("mean_hex", mean.hex()),
        ("complement_mean", complement),
        ("complement_mean_hex", complement.hex()),
        ("log_z", log_z),
        ("log_z_hex", log_z.hex()),
        ("probabilities", probabilities),
        ("probability_hex", tuple((n, p.hex()) for n, p in probabilities)),
        ("ranking", ranking),
        ("top6", ranking[:6]),
        ("top12", ranking[:12]),
        ("top18", ranking[:18]),
        ("final6", tuple(sorted(ranking[:6]))),
    ):
        object.__setattr__(forecast, field_name, value)
    validate_forecast(forecast)
    return forecast


def forecast_candidate(
    history_prefix: list[MainDraw] | tuple[MainDraw, ...], target_date: date
) -> OverlapForecast:
    """Fit the one registered law on a complete strictly previous main-only prefix."""
    return _forecast(history_prefix, target_date, control=False)


def forecast_control(
    history_prefix: list[MainDraw] | tuple[MainDraw, ...], target_date: date
) -> OverlapForecast:
    """Fit source-only cyclic-anchor control with its own chronological counts."""
    return _forecast(history_prefix, target_date, control=True)
