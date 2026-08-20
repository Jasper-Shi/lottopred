"""Pure, frozen mathematics for the V11 previous-bonus diagnostic."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from hashlib import sha256
import math

from ..domain import Draw


MODEL_VERSION = "v11.0.0"
CANDIDATE_MODEL_NAME = "v11_previous_bonus_carryover"
CONTROL_MODEL_NAME = "v11_previous_bonus_carryover_pseudo_bonus_control"
PROBABILITY_SUM_ABSOLUTE_TOLERANCE = 1.0e-12
RNG_START_DATE = date(2019, 5, 15)
BISECTION_ITERATIONS = 256
CONTROL_SEED = 649
CONTROL_DOMAIN = "lotto649-v11-bonus-anchor-control-v1"
FAIR_PROBABILITY = 6.0 / 49.0


def _validate_probabilities(probabilities: tuple[float, ...]) -> None:
    if len(probabilities) != 49:
        raise ValueError("V11 requires exactly 49 probabilities")
    if not all(math.isfinite(value) for value in probabilities):
        raise ValueError("V11 probabilities must be finite")
    if not all(0.0 < value < 1.0 for value in probabilities):
        raise ValueError("V11 probabilities must be in the open interval (0, 1)")
    if abs(math.fsum(probabilities) - 6.0) > PROBABILITY_SUM_ABSOLUTE_TOLERANCE:
        raise ValueError("V11 probabilities must sum to six")


@dataclass(frozen=True)
class V1BaseSnapshot:
    """One immutable strict-prefix V1 forecast consumed by both V11 arms."""

    target_date: date
    history_draws: int
    history_through: date | None
    strict_prefix_sha256: str
    probabilities: tuple[float, ...]
    ranking: tuple[int, ...]
    top6: tuple[int, ...]
    top12: tuple[int, ...]
    top18: tuple[int, ...]
    final6: tuple[int, ...]

    def __post_init__(self) -> None:
        if type(self.history_draws) is not int or self.history_draws < 1:
            raise ValueError("V1 base history_draws must be a positive integer")
        if self.history_through is None:
            raise ValueError("V1 base history_through is required")
        if self.history_through >= self.target_date:
            raise ValueError("V1 history_through must be strictly before target_date")
        if not (
            isinstance(self.strict_prefix_sha256, str)
            and len(self.strict_prefix_sha256) == 64
            and all(
                character in "0123456789abcdef"
                for character in self.strict_prefix_sha256
            )
        ):
            raise ValueError("V1 base requires a lowercase SHA-256 prefix digest")
        if type(self.probabilities) is not tuple:
            raise ValueError("V1 base probabilities must be an immutable tuple")
        _validate_probabilities(self.probabilities)
        expected_ranking = tuple(
            sorted(
                range(1, 50),
                key=lambda number: (-self.probabilities[number - 1], number),
            )
        )
        if self.ranking != expected_ranking:
            raise ValueError("V1 ranking does not match its probabilities")
        if not (
            self.top6 == self.ranking[:6]
            and self.top12 == self.ranking[:12]
            and self.top18 == self.ranking[:18]
        ):
            raise ValueError("V1 Top-K fields must be exact ranking prefixes")
        if self.final6 != tuple(sorted(self.top6)):
            raise ValueError("V1 final6 must be the sorted marginal Top-6")


@dataclass(frozen=True)
class V11Transition:
    """One eligible source/destination row with both frozen anchor roles."""

    source_date: date
    destination_date: date
    base_prefix_sha256: str
    candidate_anchor: int
    control_anchor: int
    candidate_q: float
    control_q: float
    candidate_y: int
    control_y: int

    def __post_init__(self) -> None:
        if self.source_date < RNG_START_DATE:
            raise ValueError("V11 transition source is before the RNG boundary")
        if self.destination_date <= self.source_date:
            raise ValueError("V11 transition destination must follow its source")
        if not (
            isinstance(self.base_prefix_sha256, str)
            and len(self.base_prefix_sha256) == 64
            and all(
                character in "0123456789abcdef" for character in self.base_prefix_sha256
            )
        ):
            raise ValueError("V11 transition requires a lowercase SHA-256 digest")
        for anchor in (self.candidate_anchor, self.control_anchor):
            if type(anchor) is not int or not 1 <= anchor <= 49:
                raise ValueError("V11 transition anchors must be integers in 1..49")
        for probability in (self.candidate_q, self.control_q):
            if not math.isfinite(probability) or not 0.0 < probability < 1.0:
                raise ValueError("V11 transition probabilities must be in (0, 1)")
        for response in (self.candidate_y, self.control_y):
            if type(response) is not int or response not in (0, 1):
                raise ValueError("V11 transition responses must be integer zero or one")


@dataclass(frozen=True)
class V11BetaFit:
    """The one-parameter MAP fit and its strict-prefix sample size."""

    transition_count: int
    beta: float


@dataclass(frozen=True)
class V11Forecast:
    """One deterministic candidate or pseudo-control pre-reveal forecast."""

    model_name: str
    model_version: str
    target_date: date
    history_draws: int
    history_through: date | None
    anchor_source_date: date
    anchor_kind: str
    anchor: int
    transition_count: int
    beta: float
    q_b: float
    r_b: float
    probabilities: tuple[float, ...]
    ranking: tuple[int, ...]
    top6: tuple[int, ...]
    top12: tuple[int, ...]
    top18: tuple[int, ...]
    final6: tuple[int, ...]


@dataclass(frozen=True)
class V11ForecastBundle:
    """Candidate and control forecasts bound to the same V1 base object."""

    base: V1BaseSnapshot
    candidate: V11Forecast
    control: V11Forecast


def _stable_logit(probability: float) -> float:
    return math.log(probability) - math.log1p(-probability)


def _stable_sigmoid(value: float) -> float:
    if value >= 0.0:
        return 1.0 / (1.0 + math.exp(-value))
    exponential = math.exp(value)
    return exponential / (1.0 + exponential)


def _score_beta(
    transitions: tuple[V11Transition, ...],
    role: str,
    beta: float,
) -> float:
    if role == "candidate":
        q_and_y = (
            (transition.candidate_q, transition.candidate_y)
            for transition in transitions
        )
    elif role == "control":
        q_and_y = (
            (transition.control_q, transition.control_y) for transition in transitions
        )
    else:
        raise ValueError("V11 role must be 'candidate' or 'control'")
    residuals = [
        response - _stable_sigmoid(_stable_logit(q_anchor) + beta)
        for q_anchor, response in q_and_y
    ]
    return math.fsum([-beta, *residuals])


def fit_beta(
    transitions: tuple[V11Transition, ...],
    role: str,
) -> V11BetaFit:
    """Fit the frozen N(0,1) single-offset MAP by literal bisection."""

    if role not in ("candidate", "control"):
        raise ValueError("V11 role must be 'candidate' or 'control'")
    if type(transitions) is not tuple or not all(
        isinstance(transition, V11Transition) for transition in transitions
    ):
        raise ValueError("V11 transitions must be an immutable tuple of rows")
    if any(
        left.destination_date >= right.destination_date
        for left, right in zip(transitions, transitions[1:])
    ):
        raise ValueError("V11 transitions must be in strict destination-date order")

    transition_count = len(transitions)
    if transition_count == 0:
        return V11BetaFit(transition_count=0, beta=0.0)

    score_at_zero = _score_beta(transitions, role, 0.0)
    if score_at_zero == 0.0:
        return V11BetaFit(transition_count=transition_count, beta=0.0)

    bound = float(transition_count + 64)
    if score_at_zero > 0.0:
        lower = 0.0
        upper = bound
    else:
        lower = -bound
        upper = 0.0
    if not (
        _score_beta(transitions, role, lower) > 0.0
        and _score_beta(transitions, role, upper) < 0.0
    ):
        raise RuntimeError("V11 beta root is not strictly bracketed")

    for _ in range(BISECTION_ITERATIONS):
        midpoint = lower + (upper - lower) / 2.0
        if _score_beta(transitions, role, midpoint) > 0.0:
            lower = midpoint
        else:
            upper = midpoint
    beta = lower + (upper - lower) / 2.0
    return V11BetaFit(transition_count=transition_count, beta=beta)


def select_pseudo_bonus(source_draw: Draw) -> tuple[int, str]:
    """Select the frozen deterministic pseudo-bonus and its full digest."""

    if source_draw.bonus is None:
        raise ValueError("V11 pseudo-bonus selection requires a source bonus")
    seven_labels = tuple(sorted((*source_draw.numbers, source_draw.bonus)))
    digest_and_label = tuple(
        (
            sha256(
                (
                    f"{CONTROL_DOMAIN}:{CONTROL_SEED}:"
                    f"{source_draw.draw_date.isoformat()}:{label}"
                ).encode("utf-8")
            ).digest(),
            label,
        )
        for label in seven_labels
    )
    winning_digest, winning_label = min(digest_and_label)
    return winning_label, winning_digest.hex()


def make_transition(
    base: V1BaseSnapshot,
    source_draw: Draw,
    destination_draw: Draw,
) -> V11Transition:
    """Build both registered anchor roles from one immutable V1 snapshot."""

    if source_draw.draw_date < RNG_START_DATE:
        raise ValueError("V11 transition source is before the RNG boundary")
    if destination_draw.draw_date < RNG_START_DATE:
        raise ValueError("V11 transition destination is before the RNG boundary")
    if source_draw.draw_date >= destination_draw.draw_date:
        raise ValueError("V11 transition source must be before its destination")
    if base.target_date != destination_draw.draw_date:
        raise ValueError("V11 transition base target must equal destination date")
    if base.history_through != source_draw.draw_date:
        raise ValueError("V11 transition base must end at the source date")
    if source_draw.bonus is None:
        raise ValueError("V11 transition requires the published source bonus")

    candidate_anchor = source_draw.bonus
    control_anchor, _ = select_pseudo_bonus(source_draw)
    return V11Transition(
        source_date=source_draw.draw_date,
        destination_date=destination_draw.draw_date,
        base_prefix_sha256=base.strict_prefix_sha256,
        candidate_anchor=candidate_anchor,
        control_anchor=control_anchor,
        candidate_q=base.probabilities[candidate_anchor - 1],
        control_q=base.probabilities[control_anchor - 1],
        candidate_y=int(candidate_anchor in destination_draw.numbers),
        control_y=int(control_anchor in destination_draw.numbers),
    )


def tilt_probabilities(
    base_probabilities: tuple[float, ...],
    anchor: int,
    beta: float,
) -> tuple[float, ...]:
    """Apply the frozen direct marginal capacity transfer."""

    _validate_probabilities(base_probabilities)
    if type(anchor) is not int or not 1 <= anchor <= 49:
        raise ValueError("V11 anchor must be an integer in 1..49")
    if not math.isfinite(beta):
        raise ValueError("V11 beta must be finite")

    q_anchor = base_probabilities[anchor - 1]
    if beta.hex() == "0x0.0p+0":
        return base_probabilities
    r_anchor = _stable_sigmoid(_stable_logit(q_anchor) + beta)
    if r_anchor == q_anchor:
        return base_probabilities

    if r_anchor > q_anchor:
        tilted = tuple(
            r_anchor
            if number == anchor
            else q_value * (6.0 - r_anchor) / (6.0 - q_anchor)
            for number, q_value in enumerate(base_probabilities, start=1)
        )
    else:
        delta = q_anchor - r_anchor
        denominator = 42.0 + q_anchor
        tilted = tuple(
            r_anchor
            if number == anchor
            else q_value + delta * (1.0 - q_value) / denominator
            for number, q_value in enumerate(base_probabilities, start=1)
        )
    _validate_probabilities(tilted)
    base_ranking = tuple(
        sorted(
            range(1, 50),
            key=lambda number: (-base_probabilities[number - 1], number),
        )
    )
    tilted_ranking = tuple(
        sorted(
            range(1, 50),
            key=lambda number: (-tilted[number - 1], number),
        )
    )
    base_nonanchor_ranking = tuple(
        number for number in base_ranking if number != anchor
    )
    tilted_nonanchor_ranking = tuple(
        number for number in tilted_ranking if number != anchor
    )
    if tilted_nonanchor_ranking != base_nonanchor_ranking:
        raise RuntimeError(
            "V11 capacity transfer changed non-anchor ranking after binary64 rounding"
        )
    return tilted


def _forecast_for_role(
    base: V1BaseSnapshot,
    transitions: tuple[V11Transition, ...],
    source_draw: Draw,
    role: str,
) -> V11Forecast:
    fit = fit_beta(transitions, role)
    if role == "candidate":
        if source_draw.bonus is None:
            raise ValueError("V11 candidate forecast requires a source bonus")
        model_name = CANDIDATE_MODEL_NAME
        anchor_kind = "published_bonus"
        anchor = source_draw.bonus
    else:
        model_name = CONTROL_MODEL_NAME
        anchor_kind = "deterministic_pseudo_bonus"
        anchor, _ = select_pseudo_bonus(source_draw)

    q_anchor = base.probabilities[anchor - 1]
    if fit.beta.hex() == "0x0.0p+0":
        r_anchor = q_anchor
    else:
        r_anchor = _stable_sigmoid(_stable_logit(q_anchor) + fit.beta)
    probabilities = tilt_probabilities(base.probabilities, anchor, fit.beta)
    if probabilities is base.probabilities:
        ranking = base.ranking
        top6 = base.top6
        top12 = base.top12
        top18 = base.top18
        final6 = base.final6
    else:
        ranking = tuple(
            sorted(
                range(1, 50),
                key=lambda number: (-probabilities[number - 1], number),
            )
        )
        top6 = ranking[:6]
        top12 = ranking[:12]
        top18 = ranking[:18]
        final6 = tuple(sorted(top6))
    return V11Forecast(
        model_name=model_name,
        model_version=MODEL_VERSION,
        target_date=base.target_date,
        history_draws=base.history_draws,
        history_through=base.history_through,
        anchor_source_date=source_draw.draw_date,
        anchor_kind=anchor_kind,
        anchor=anchor,
        transition_count=fit.transition_count,
        beta=fit.beta,
        q_b=q_anchor,
        r_b=r_anchor,
        probabilities=probabilities,
        ranking=ranking,
        top6=top6,
        top12=top12,
        top18=top18,
        final6=final6,
    )


def forecast_v11_bundle(
    base: V1BaseSnapshot,
    transitions: tuple[V11Transition, ...],
    source_draw: Draw,
) -> V11ForecastBundle:
    """Forecast both registered arms from exactly one immutable V1 base."""

    if base.history_through != source_draw.draw_date:
        raise ValueError("V11 target base must end at the anchor source date")
    if source_draw.draw_date >= base.target_date:
        raise ValueError("V11 anchor source must be strictly before target")
    if source_draw.draw_date < RNG_START_DATE:
        raise ValueError("V11 anchor source is before the RNG boundary")
    if source_draw.bonus is None:
        raise ValueError("V11 bundle requires the published source bonus")
    if any(
        transition.destination_date > source_draw.draw_date
        for transition in transitions
    ):
        raise ValueError("V11 transitions must end within the visible strict prefix")

    candidate = _forecast_for_role(base, transitions, source_draw, "candidate")
    control = _forecast_for_role(base, transitions, source_draw, "control")
    return V11ForecastBundle(base=base, candidate=candidate, control=control)


def anchor_log_gains(
    q_anchor: float,
    r_anchor: float,
    response: int,
) -> tuple[float, float]:
    """Return the observed anchor log gain versus fair and versus V1."""

    if not (
        math.isfinite(q_anchor)
        and math.isfinite(r_anchor)
        and 0.0 < q_anchor < 1.0
        and 0.0 < r_anchor < 1.0
    ):
        raise ValueError("V11 anchor probabilities must be finite and in (0, 1)")
    if type(response) is not int or response not in (0, 1):
        raise ValueError("V11 anchor response must be integer zero or one")
    if response == 1:
        return (
            math.log(r_anchor / FAIR_PROBABILITY),
            math.log(r_anchor / q_anchor),
        )
    return (
        math.log((1.0 - r_anchor) / (1.0 - FAIR_PROBABILITY)),
        math.log((1.0 - r_anchor) / (1.0 - q_anchor)),
    )


@lru_cache(maxsize=1)
def preflight_v11_model() -> None:
    """Fail closed unless every frozen synthetic numeric oracle matches."""

    dates = (
        (date(2019, 5, 15), date(2019, 5, 18)),
        (date(2019, 5, 18), date(2019, 5, 22)),
        (date(2019, 5, 22), date(2019, 5, 25)),
        (date(2019, 5, 25), date(2019, 5, 29)),
    )
    responses = (1, 0, 0, 1)
    transitions = tuple(
        V11Transition(
            source_date=source_date,
            destination_date=destination_date,
            base_prefix_sha256=f"{index:x}" * 64,
            candidate_anchor=index,
            control_anchor=index + 10,
            candidate_q=FAIR_PROBABILITY,
            control_q=FAIR_PROBABILITY,
            candidate_y=response,
            control_y=response,
        )
        for index, ((source_date, destination_date), response) in enumerate(
            zip(dates, responses),
            start=1,
        )
    )
    beta = fit_beta(transitions, "candidate").beta
    r_anchor = _stable_sigmoid(_stable_logit(FAIR_PROBABILITY) + beta)
    if beta.hex() != "0x1.e35d1e3820caep-1":
        raise RuntimeError("V11 preflight beta oracle mismatch")
    if r_anchor.hex() != "0x1.0e5170e3ef9a9p-2":
        raise RuntimeError("V11 preflight tilted-probability oracle mismatch")

    balanced = (
        V11Transition(
            source_date=date(2019, 5, 15),
            destination_date=date(2019, 5, 18),
            base_prefix_sha256="a" * 64,
            candidate_anchor=1,
            control_anchor=2,
            candidate_q=0.5,
            control_q=0.5,
            candidate_y=1,
            control_y=1,
        ),
        V11Transition(
            source_date=date(2019, 5, 18),
            destination_date=date(2019, 5, 22),
            base_prefix_sha256="b" * 64,
            candidate_anchor=1,
            control_anchor=2,
            candidate_q=0.5,
            control_q=0.5,
            candidate_y=0,
            control_y=0,
        ),
    )
    if fit_beta(balanced, "candidate").beta.hex() != "0x0.0p+0":
        raise RuntimeError("V11 preflight balanced-zero oracle mismatch")

    base = (0.2, *((29.0 / 240.0,) * 48))
    positive = tilt_probabilities(base, 1, math.log(2.0))
    negative = tilt_probabilities(base, 1, -math.log(2.0))
    if not (
        positive[0].hex() == "0x1.5555555555555p-2"
        and positive[1].hex() == "0x1.e38e38e38e38fp-4"
        and math.fsum(positive) == 6.000000000000001
        and negative[0].hex() == "0x1.c71c71c71c71ep-4"
        and negative[1].hex() == "0x1.f684bda12f685p-4"
        and math.fsum(negative) == 6.0
    ):
        raise RuntimeError("V11 preflight capacity-transfer oracle mismatch")

    pseudo_label, pseudo_digest = select_pseudo_bonus(
        Draw(date(2020, 1, 1), (1, 2, 3, 5, 6, 7), 4)
    )
    if not (
        pseudo_label == 4
        and pseudo_digest
        == "1052da1f3ebf9c1bfe2f06998f13ebc812c01dd08fd9b0b21cc20fd35d0840c8"
    ):
        raise RuntimeError("V11 preflight pseudo-bonus oracle mismatch")

    gain_oracles = (
        (positive[0], 0, "-0x1.1970f2bd42617p-2", "-0x1.7565011e49675p-3"),
        (positive[0], 1, "0x1.005eee78d91a2p+0", "0x1.058aefa811451p-1"),
        (negative[0], 0, "0x1.a4a5cac16aef2p-7", "0x1.af8e8210a4152p-4"),
        (negative[0], 1, "-0x1.8dfb931f71680p-4", "-0x1.2cf25fad8f1c3p-1"),
    )
    for r_value, response, expected_log_g, expected_d in gain_oracles:
        log_g, d_value = anchor_log_gains(0.2, r_value, response)
        if log_g.hex() != expected_log_g or d_value.hex() != expected_d:
            raise RuntimeError("V11 preflight anchor-gain oracle mismatch")
