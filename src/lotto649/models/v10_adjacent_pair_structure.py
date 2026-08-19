from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from hashlib import sha256
import json
import math

from .base import ProbabilityModel
from ..domain import Draw


MODEL_VERSION = "v10.0.0"
CANDIDATE_MODEL_NAME = "v10_adjacent_pair_structure"
CONTROL_MODEL_NAME = "v10_adjacency_label_bijection_control"
MODEL_NAMES = frozenset({CANDIDATE_MODEL_NAME, CONTROL_MODEL_NAME})

FAIR_CATEGORY_COUNTS = (
    7_059_052,
    5_430_040,
    1_357_510,
    132_440,
    4_730,
    44,
)
FAIR_TOTAL_SIX_SETS = 13_983_816
FAIR_PROBABILITY = 6.0 / 49.0
PROBABILITY_SUM_ABSOLUTE_TOLERANCE = 1.0e-12
BISECTION_ITERATIONS = 256
BISECTION_LOWER = -64.0
BISECTION_UPPER = 64.0

MARGINAL_COUNT_TABLE_SHA256 = (
    "7d14a90bc388cb0e02dda77ff315a1662492c2cb44f6d5497e297354804d781b"
)
CONTROL_DOMAIN = "lotto649-v10-adjacency-control-v1"
CONTROL_SEED = 649
CONTROL_DESTINATIONS = (
    3,
    11,
    2,
    14,
    41,
    45,
    22,
    39,
    1,
    40,
    31,
    37,
    29,
    12,
    30,
    6,
    7,
    19,
    46,
    15,
    27,
    26,
    42,
    28,
    13,
    21,
    20,
    36,
    18,
    4,
    5,
    32,
    17,
    8,
    9,
    10,
    35,
    43,
    47,
    16,
    48,
    34,
    23,
    24,
    44,
    25,
    33,
    38,
    49,
)
CONTROL_MAP_CANONICAL = ",".join(
    f"{source}:{destination}"
    for source, destination in enumerate(CONTROL_DESTINATIONS, start=1)
)
CONTROL_MAP_SHA256 = (
    "c533509f258e0bb8bdd9fabac8a017ee689e07af0f1d6daf4d36ee63873c0562"
)


@dataclass(frozen=True)
class V10Forecast:
    """Deterministic, pre-reveal output from the frozen V10 engine."""

    model_name: str
    model_version: str
    target_date: date
    history_draws: int
    history_through: date | None
    sum_a: int
    moment_numerator: int
    moment_denominator: int
    moment_binary64: float
    theta: float
    log_z: float
    probabilities: tuple[float, ...]
    ranking: tuple[int, ...]
    top6: tuple[int, ...]
    top12: tuple[int, ...]
    top18: tuple[int, ...]
    final6: tuple[int, ...]

    def canonical_payload(self) -> dict[str, object]:
        """Return the timestamp-free and outcome-free JSON payload."""

        return {
            "feature_identity": "sorted_main_gap_exactly_one",
            "final6": list(self.final6),
            "history_draws": self.history_draws,
            "history_through": (
                self.history_through.isoformat()
                if self.history_through is not None
                else None
            ),
            "log_z": self.log_z,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "moment_binary64": self.moment_binary64,
            "moment_denominator": self.moment_denominator,
            "moment_numerator": self.moment_numerator,
            "probabilities": {
                str(number): self.probabilities[number - 1]
                for number in range(1, 50)
            },
            "ranking": list(self.ranking),
            "seed": CONTROL_SEED,
            "sum_a": self.sum_a,
            "target_date": self.target_date.isoformat(),
            "theta": self.theta,
            "top6": list(self.top6),
            "top12": list(self.top12),
            "top18": list(self.top18),
        }

    def canonical_payload_bytes(self) -> bytes:
        """Serialize the deterministic payload with one canonical encoding."""

        return json.dumps(
            self.canonical_payload(),
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")


@dataclass(frozen=True)
class _Partition:
    log_z: float
    moment: float
    ell_max: float
    scaled_sum: float


def _adjacency_count(numbers: Iterable[int]) -> int:
    ordered = tuple(sorted(numbers))
    return sum(
        right - left == 1 for left, right in zip(ordered, ordered[1:])
    )


@lru_cache(maxsize=None)
def _build_marginal_count_table(
    n: int,
    k: int,
) -> tuple[tuple[int, ...], ...]:
    if type(n) is not int or type(k) is not int or not 1 <= k <= n:
        raise ValueError("marginal DP requires integers satisfying 1 <= k <= n")

    rows: list[tuple[int, ...]] = []
    for forced_label in range(1, n + 1):
        state: dict[tuple[int, int, int], int] = {(0, 0, 0): 1}
        for position in range(1, n + 1):
            next_state: dict[tuple[int, int, int], int] = {}
            choices = (1,) if position == forced_label else (0, 1)
            for (used, adjacency, previous), count in state.items():
                for selected in choices:
                    next_used = used + selected
                    next_adjacency = adjacency + previous * selected
                    if next_used > k or next_adjacency >= k:
                        continue
                    key = (next_used, next_adjacency, selected)
                    next_state[key] = next_state.get(key, 0) + count
            state = next_state
        rows.append(
            tuple(
                state.get((k, adjacency, 0), 0)
                + state.get((k, adjacency, 1), 0)
                for adjacency in range(k)
            )
        )
    return tuple(rows)


@lru_cache(maxsize=1)
def _marginal_count_table() -> tuple[tuple[int, ...], ...]:
    return _build_marginal_count_table(49, 6)


def _control_digest(source_label: int) -> bytes:
    payload = f"{CONTROL_DOMAIN}:{CONTROL_SEED}:{source_label}".encode("utf-8")
    return sha256(payload).digest()


def _generated_control_destinations() -> tuple[int, ...]:
    digest_order = sorted(
        range(1, 50),
        key=lambda source_label: (
            _control_digest(source_label),
            source_label,
        ),
    )
    destinations = [0] * 49
    for destination, source_label in enumerate(digest_order, start=1):
        destinations[source_label - 1] = destination
    return tuple(destinations)


def _partition(theta: float) -> _Partition:
    if not math.isfinite(theta):
        raise RuntimeError("v10 theta must be finite")
    log_weights = tuple(
        math.log(count) + theta * adjacency
        for adjacency, count in enumerate(FAIR_CATEGORY_COUNTS)
    )
    ell_max = max(log_weights)
    scaled_weights = tuple(
        math.exp(log_weight - ell_max) for log_weight in log_weights
    )
    scaled_sum = math.fsum(scaled_weights)
    log_z = ell_max + math.log(scaled_sum)
    moment = math.fsum(
        adjacency * weight
        for adjacency, weight in enumerate(scaled_weights)
    ) / scaled_sum
    if not all(
        math.isfinite(value)
        for value in (ell_max, scaled_sum, log_z, moment)
    ):
        raise RuntimeError("v10 partition calculation produced a non-finite value")
    return _Partition(
        log_z=log_z,
        moment=moment,
        ell_max=ell_max,
        scaled_sum=scaled_sum,
    )


def _solve_theta(moment_binary64: float) -> tuple[float, _Partition]:
    lower = BISECTION_LOWER
    upper = BISECTION_UPPER
    lower_partition = _partition(lower)
    upper_partition = _partition(upper)
    if not lower_partition.moment < moment_binary64 < upper_partition.moment:
        raise RuntimeError("v10 moment root is not strictly bracketed")

    for _ in range(BISECTION_ITERATIONS):
        midpoint = lower + (upper - lower) / 2.0
        if _partition(midpoint).moment < moment_binary64:
            lower = midpoint
        else:
            upper = midpoint
    theta = lower + (upper - lower) / 2.0
    return theta, _partition(theta)


def _probabilities_for_theta(theta: float) -> tuple[float, ...]:
    partition = _partition(theta)
    probabilities = []
    for row in _marginal_count_table():
        scaled_terms = tuple(
            math.exp(
                math.log(count)
                + theta * adjacency
                - partition.ell_max
            )
            for adjacency, count in enumerate(row)
        )
        probabilities.append(math.fsum(scaled_terms) / partition.scaled_sum)
    result = tuple(probabilities)
    _validate_probabilities(result, require_reflection=True)
    return result


def _validate_probabilities(
    probabilities: tuple[float, ...],
    *,
    require_reflection: bool,
) -> None:
    if len(probabilities) != 49:
        raise RuntimeError("v10 must produce exactly 49 probabilities")
    if not all(math.isfinite(probability) for probability in probabilities):
        raise RuntimeError("v10 produced a non-finite probability")
    if not all(0.0 < probability < 1.0 for probability in probabilities):
        raise RuntimeError("v10 violated the open-interval probability contract")
    if abs(math.fsum(probabilities) - 6.0) > PROBABILITY_SUM_ABSOLUTE_TOLERANCE:
        raise RuntimeError("v10 probabilities do not sum to six")
    if require_reflection and any(
        probabilities[number - 1] != probabilities[49 - number]
        for number in range(1, 50)
    ):
        raise RuntimeError("v10 candidate probabilities violate reflection symmetry")


def _fit_parameters(
    history_draws: int,
    sum_a: int,
) -> tuple[int, int, float, float, float, tuple[float, ...]]:
    moment_numerator = 49 * sum_a + 30
    moment_denominator = 49 * (history_draws + 1)
    moment_binary64 = moment_numerator / moment_denominator
    if not math.isfinite(moment_binary64):
        raise RuntimeError("v10 moment conversion produced a non-finite value")

    if 49 * sum_a == 30 * history_draws:
        return (
            moment_numerator,
            moment_denominator,
            moment_binary64,
            0.0,
            math.log(FAIR_TOTAL_SIX_SETS),
            (FAIR_PROBABILITY,) * 49,
        )

    theta, partition = _solve_theta(moment_binary64)
    probabilities = _probabilities_for_theta(theta)
    return (
        moment_numerator,
        moment_denominator,
        moment_binary64,
        theta,
        partition.log_z,
        probabilities,
    )


@lru_cache(maxsize=1)
def preflight_v10_model() -> None:
    """Verify every registered mathematical and mapping identity."""

    formula_counts = tuple(
        math.comb(5, adjacency) * math.comb(44, 6 - adjacency)
        for adjacency in range(6)
    )
    if formula_counts != FAIR_CATEGORY_COUNTS:
        raise RuntimeError("v10 fair adjacency counts do not match the oracle")
    if sum(FAIR_CATEGORY_COUNTS) != FAIR_TOTAL_SIX_SETS:
        raise RuntimeError("v10 fair adjacency counts do not sum to C(49,6)")
    weighted_sum = sum(
        adjacency * count
        for adjacency, count in enumerate(FAIR_CATEGORY_COUNTS)
    )
    if 49 * weighted_sum != 30 * FAIR_TOTAL_SIX_SETS:
        raise RuntimeError("v10 fair adjacency mean does not equal 30/49")
    weighted_square_sum = sum(
        adjacency * adjacency * count
        for adjacency, count in enumerate(FAIR_CATEGORY_COUNTS)
    )
    variance_numerator = (
        weighted_square_sum * FAIR_TOTAL_SIX_SETS - weighted_sum * weighted_sum
    )
    variance_denominator = FAIR_TOTAL_SIX_SETS * FAIR_TOTAL_SIX_SETS
    if variance_numerator * 4_802 != variance_denominator * 2_365:
        raise RuntimeError("v10 fair adjacency variance does not equal 2365/4802")

    table = _marginal_count_table()
    canonical_table = json.dumps(table, separators=(",", ":")).encode("utf-8")
    if sha256(canonical_table).hexdigest() != MARGINAL_COUNT_TABLE_SHA256:
        raise RuntimeError("v10 marginal DP table does not match its frozen digest")
    if table[0] != (962_598, 617_050, 123_410, 9_030, 215, 1):
        raise RuntimeError("v10 marginal DP label-1 row does not match its oracle")
    if table[24] != (860_586, 666_310, 168_146, 16_646, 610, 6):
        raise RuntimeError("v10 marginal DP label-25 row does not match its oracle")
    if table[48] != table[0]:
        raise RuntimeError("v10 marginal DP label-49 row does not match its oracle")
    if any(
        sum(row[adjacency] for row in table) != 6 * count
        for adjacency, count in enumerate(FAIR_CATEGORY_COUNTS)
    ):
        raise RuntimeError("v10 marginal DP category identities failed")

    generated_map = _generated_control_destinations()
    if generated_map != CONTROL_DESTINATIONS:
        raise RuntimeError("v10 generated control map differs from its literal map")
    if sorted(CONTROL_DESTINATIONS) != list(range(1, 50)):
        raise RuntimeError("v10 control map is not a label bijection")
    if CONTROL_DESTINATIONS in (
        tuple(range(1, 50)),
        tuple(range(49, 0, -1)),
    ):
        raise RuntimeError("v10 control map preserves the registered numeric path")
    if sha256(CONTROL_MAP_CANONICAL.encode("utf-8")).hexdigest() != (
        CONTROL_MAP_SHA256
    ):
        raise RuntimeError("v10 control map canonical digest differs from its oracle")

    if math.log(FAIR_TOTAL_SIX_SETS).hex() != "0x1.07412c1f4cc68p+4":
        raise RuntimeError("v10 exact-fair log-Z differs from its binary64 oracle")
    (
        numerator,
        denominator,
        moment,
        theta,
        _log_z,
        _probabilities,
    ) = _fit_parameters(2, 2)
    if (numerator, denominator) != (128, 147):
        raise RuntimeError("v10 synthetic moment integer ratio differs from its oracle")
    if moment.hex() != "0x1.bdd2b899406f7p-1":
        raise RuntimeError("v10 synthetic moment differs from its binary64 oracle")
    if theta.hex() != "0x1.d4c61abbdd33cp-2":
        raise RuntimeError("v10 bisection root differs from its binary64 oracle")
    if _probabilities_for_theta(-1.3)[0].hex() != "0x1.0e2c39c67edaep-3":
        raise RuntimeError("v10 marginal probability differs from its binary64 oracle")


def _validated_history(
    history: Sequence[Draw],
    target_date: date,
) -> tuple[Draw, ...]:
    if not isinstance(target_date, date):
        raise TypeError("v10 target_date must be a date")
    frozen_history = tuple(history)
    if not all(isinstance(draw, Draw) for draw in frozen_history):
        raise TypeError("v10 history must contain Draw instances")
    history_dates = tuple(draw.draw_date for draw in frozen_history)
    if history_dates != tuple(sorted(history_dates)):
        raise ValueError("draws must be in chronological order")
    if len(history_dates) != len(set(history_dates)):
        raise ValueError("draw dates must be unique")
    if frozen_history and frozen_history[-1].draw_date >= target_date:
        raise ValueError(
            f"history through {frozen_history[-1].draw_date} is not "
            f"strictly before target {target_date}"
        )
    return frozen_history


def forecast_v10(
    history: Sequence[Draw],
    target_date: date,
    model_name: str,
) -> V10Forecast:
    """Build one frozen candidate or label-bijection-control forecast."""

    if model_name not in MODEL_NAMES:
        raise ValueError(
            "v10 model_name must be v10_adjacent_pair_structure or "
            "v10_adjacency_label_bijection_control"
        )
    preflight_v10_model()
    frozen_history = _validated_history(history, target_date)
    control = model_name == CONTROL_MODEL_NAME

    transformed_main_sets = (
        tuple(
            sorted(CONTROL_DESTINATIONS[number - 1] for number in draw.numbers)
        )
        if control
        else draw.numbers
        for draw in frozen_history
    )
    sum_a = sum(_adjacency_count(numbers) for numbers in transformed_main_sets)
    (
        moment_numerator,
        moment_denominator,
        moment_binary64,
        theta,
        log_z,
        permuted_probabilities,
    ) = _fit_parameters(len(frozen_history), sum_a)

    if control:
        probabilities = tuple(
            permuted_probabilities[destination - 1]
            for destination in CONTROL_DESTINATIONS
        )
        _validate_probabilities(probabilities, require_reflection=False)
    else:
        probabilities = permuted_probabilities
        _validate_probabilities(probabilities, require_reflection=True)

    ranking = tuple(
        sorted(
            range(1, 50),
            key=lambda number: (-probabilities[number - 1], number),
        )
    )
    top6 = ranking[:6]
    return V10Forecast(
        model_name=model_name,
        model_version=MODEL_VERSION,
        target_date=target_date,
        history_draws=len(frozen_history),
        history_through=(
            frozen_history[-1].draw_date if frozen_history else None
        ),
        sum_a=sum_a,
        moment_numerator=moment_numerator,
        moment_denominator=moment_denominator,
        moment_binary64=moment_binary64,
        theta=theta,
        log_z=log_z,
        probabilities=probabilities,
        ranking=ranking,
        top6=top6,
        top12=ranking[:12],
        top18=ranking[:18],
        final6=tuple(sorted(top6)),
    )


def _validated_actual_main(actual_main: Iterable[int]) -> tuple[int, ...]:
    actual = tuple(actual_main)
    if len(actual) != 6 or len(set(actual)) != 6:
        raise ValueError("v10 actual main set must contain six distinct labels")
    if any(type(number) is not int or not 1 <= number <= 49 for number in actual):
        raise ValueError("v10 actual main labels must be integers in 1..49")
    return tuple(sorted(actual))


def joint_log_gain(
    forecast: V10Forecast,
    actual_main: Iterable[int],
) -> float:
    """Score the frozen complete-set law after the main set is revealed."""

    if not isinstance(forecast, V10Forecast) or forecast.model_name not in MODEL_NAMES:
        raise ValueError("joint_log_gain requires a candidate or control V10Forecast")
    actual = _validated_actual_main(actual_main)
    if 49 * forecast.sum_a == 30 * forecast.history_draws:
        return 0.0
    if forecast.model_name == CONTROL_MODEL_NAME:
        actual = tuple(
            sorted(CONTROL_DESTINATIONS[number - 1] for number in actual)
        )
    adjacency = _adjacency_count(actual)
    gain = forecast.theta * adjacency
    gain -= forecast.log_z
    gain += math.log(FAIR_TOTAL_SIX_SETS)
    if not math.isfinite(gain):
        raise RuntimeError("v10 joint log gain is non-finite")
    return gain


class V10AdjacentPairStructureModel(ProbabilityModel):
    """Thin ProbabilityModel adapter for the frozen V10 candidate."""

    name = CANDIDATE_MODEL_NAME

    def predict(self, history: list[Draw], target_date: date) -> dict[int, float]:
        forecast = forecast_v10(history, target_date, self.name)
        return {
            number: forecast.probabilities[number - 1]
            for number in range(1, 50)
        }


class V10AdjacencyLabelBijectionControlModel(ProbabilityModel):
    """Thin ProbabilityModel adapter for the frozen label-bijection control."""

    name = CONTROL_MODEL_NAME

    def predict(self, history: list[Draw], target_date: date) -> dict[int, float]:
        forecast = forecast_v10(history, target_date, self.name)
        return {
            number: forecast.probabilities[number - 1]
            for number in range(1, 50)
        }
