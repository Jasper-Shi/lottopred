"""Fresh synthetic and closed-form acceptance tests for the frozen V12 core.

No fixture reads lottery history or instantiates a canonical historical attempt.
"""

from __future__ import annotations

import hashlib
import json
import math
from copy import deepcopy
from dataclasses import FrozenInstanceError, fields, replace
from datetime import UTC, date, datetime, timedelta
from fractions import Fraction
from itertools import product
from pathlib import Path

import numpy as np
import pytest

from lotto649 import v12_0_1_evidence as evidence
from lotto649.domain import Draw
from lotto649.models import v12_parity_transition as core

ROOT = Path(__file__).resolve().parents[1]
CORE_SHA256 = "fae93e0a6f76c6604eabe24f6b93676e22e87d7e567365b382484433fba2eb77"
SYNTHETIC_START = date(2032, 1, 1)
SYNTHETIC_TARGET = date(2032, 1, 5)


def _draw(bucket: int, offset: int, *, bonus: int | None = None) -> Draw:
    numbers = tuple(range(1, 2 * bucket, 2)) + tuple(range(2, 2 * (7 - bucket), 2))
    return Draw(SYNTHETIC_START + timedelta(days=offset), numbers, bonus)


def _bucket_weights(selected_size: int = 25) -> tuple[int, ...]:
    return tuple(
        math.comb(selected_size, bucket) * math.comb(49 - selected_size, 6 - bucket)
        for bucket in range(7)
    )


def _reference_tilt(eta: float, selected_size: int = 25) -> tuple[float, float]:
    # Closed-form complete-set counts, independent of core constants/functions.
    terms = tuple(
        count * math.exp(eta * bucket)
        for bucket, count in enumerate(_bucket_weights(selected_size))
    )
    normalizer = math.fsum(terms)
    mean = math.fsum(bucket * value for bucket, value in enumerate(terms)) / normalizer
    return mean, math.log(normalizer)


def test_core_source_is_the_exact_registered_byte_identity():
    source = ROOT / "src/lotto649/models/v12_parity_transition.py"
    assert hashlib.sha256(source.read_bytes()).hexdigest() == CORE_SHA256


def test_closed_form_bucket_enumeration_moments_and_registered_binary64_oracles():
    counts = _bucket_weights()
    total = math.comb(49, 6)
    assert counts == core.BUCKET_COUNTS
    assert sum(counts) == total == core.FAIR_SET_COUNT == 13_983_816
    mean = sum(Fraction(bucket * count, total) for bucket, count in enumerate(counts))
    variance = sum(
        Fraction(count, total) * (bucket - mean) ** 2
        for bucket, count in enumerate(counts)
    )
    assert mean == Fraction(150, 49)
    assert variance == Fraction(3225, 2401)
    assert core.FAIR_MEAN.hex() == "0x1.87d6343eb1a1fp+1"
    assert core.FAIR_VARIANCE.hex() == "0x1.57db526b4310cp+0"
    assert core.FAIR_STANDARD_DEVIATION.hex() == "0x1.28b1a92291f40p+0"
    assert tuple(value.hex() for value in core.STANDARDIZED_BUCKET_STATES) == (
        "-0x1.5217d88c9a696p+1",
        "-0x1.c74c7c5dc5b37p+0",
        "-0x1.d4d28f44ad284p-1",
        "-0x1.b0c25cdcee9a3p-5",
        "0x1.9eba43a90f550p-1",
        "0x1.ac40568ff6c9dp+0",
        "0x1.4491c5a5b2f49p+1",
    )
    assert core.STANDARDIZED_BUCKET_STATES == tuple(
        (bucket - float(mean)) / math.sqrt(float(variance)) for bucket in range(7)
    )


@pytest.mark.parametrize("eta", [-10.0, -1.0, -0.1, 0.0, 0.1, 1.0, 10.0])
def test_complete_set_law_normalizes_and_label_marginals_match_combinatorics(eta):
    actual = core.tilted_moment_log_z(eta)
    mean, log_z = _reference_tilt(eta)
    assert actual.expected_bucket == pytest.approx(mean, rel=2e-15, abs=1e-15)
    assert actual.log_z == pytest.approx(log_z, rel=2e-15, abs=1e-15)
    weights = _bucket_weights()
    set_mass = math.fsum(
        count * math.exp(eta * bucket - actual.log_z)
        for bucket, count in enumerate(weights)
    )
    assert set_mass == pytest.approx(1.0, abs=2e-14)
    selected_mass = math.fsum(
        math.comb(24, bucket - 1)
        * math.comb(24, 6 - bucket)
        * math.exp(eta * bucket - actual.log_z)
        for bucket in range(1, 7)
    )
    complement_mass = math.fsum(
        math.comb(25, bucket)
        * math.comb(23, 5 - bucket)
        * math.exp(eta * bucket - actual.log_z)
        for bucket in range(6)
    )
    assert selected_mass == pytest.approx(mean / 25, abs=2e-14)
    assert complement_mass == pytest.approx((6 - mean) / 24, abs=2e-14)
    reflected_mean, reflected_log_z = _reference_tilt(-eta, selected_size=24)
    assert mean == pytest.approx(6 - reflected_mean, abs=2e-14)
    assert log_z == pytest.approx(6 * eta + reflected_log_z, abs=2e-14)


def test_registered_stable_tilt_one_row_and_log_set_count_hex_oracles():
    moment = core.tilted_moment_log_z(1.0)
    assert moment.expected_bucket.hex() == "0x1.146be0cc6d96bp+2"
    assert moment.log_z.hex() == "0x1.429e138359d0bp+4"
    assert math.log(core.FAIR_SET_COUNT).hex() == "0x1.07412c1f4cc68p+4"
    row = core.TransitionRow(SYNTHETIC_START, core.STANDARDIZED_BUCKET_STATES[6], 6)
    fitted = core.solve_map_beta((row,))
    assert fitted.bracket_radius.hex() == "0x1.036d543c46377p+4"
    assert fitted.beta.hex() == "0x1.1356f8128a684p+0"


@pytest.mark.parametrize("eta", [-1000.0, 1000.0])
def test_stable_tilt_keeps_extreme_finite_inputs_finite(eta):
    moment = core.tilted_moment_log_z(eta)
    assert math.isfinite(moment.log_z)
    assert 0 <= moment.expected_bucket <= 6


@pytest.mark.parametrize("eta", [True, None, "1", math.inf, -math.inf, math.nan])
def test_tilt_rejects_nonfinite_or_non_numeric_eta(eta):
    with pytest.raises(ValueError, match="finite"):
        core.tilted_moment_log_z(eta)


def test_solver_performs_256_steps_and_equality_takes_upper_endpoint():
    visited = []

    def score(value):
        visited.append(value)
        return -value

    result = core._bisect_strict_root(score, 1.0)
    assert len(visited) == 256
    assert visited[:4] == [0.0, -0.5, -0.25, -0.125]
    assert result == -(2.0**-256)


def test_real_map_solver_enters_exact_256_step_bisection(monkeypatch):
    original = core._bisect_strict_root
    calls = []

    def counted(score, radius):
        assert score(-radius) > 0 > score(radius)

        def observe(value):
            calls.append(value)
            return score(value)

        return original(observe, radius)

    monkeypatch.setattr(core, "_bisect_strict_root", counted)
    row = core.TransitionRow(SYNTHETIC_START, core.STANDARDIZED_BUCKET_STATES[6], 6)
    assert core.solve_map_beta((row,)).beta > 0
    assert len(calls) == 256


def test_empty_and_exact_zero_score_bypass_solver_with_positive_zero(monkeypatch):
    def forbidden(*args):
        raise AssertionError("fair bypass must not invoke bisection")

    monkeypatch.setattr(core, "_bisect_strict_root", forbidden)
    empty = core.solve_map_beta(())
    assert empty.beta.hex() == empty.bracket_radius.hex() == "0x0.0p+0"
    monkeypatch.setattr(
        core, "tilted_moment_log_z", lambda eta: core.TiltedMoment(3.0, 1.0)
    )
    row = core.TransitionRow(SYNTHETIC_START, core.STANDARDIZED_BUCKET_STATES[3], 3)
    zero = core.solve_map_beta((row,))
    assert zero.beta.hex() == zero.bracket_radius.hex() == "0x0.0p+0"


def test_non_strict_score_bracket_fails_closed(monkeypatch):
    monkeypatch.setattr(
        core, "tilted_moment_log_z", lambda eta: core.TiltedMoment(math.nan, 1.0)
    )
    row = core.TransitionRow(SYNTHETIC_START, core.STANDARDIZED_BUCKET_STATES[6], 6)
    with pytest.raises(ArithmeticError, match="bracket is not strict"):
        core.solve_map_beta((row,))


def test_prefix_uses_exact_adjacent_eligible_transitions_and_last_state():
    draws = (_draw(0, 0), _draw(6, 1), _draw(2, 2))
    prefix = core.build_transition_prefix(
        draws, SYNTHETIC_TARGET, core.TRUE_PARITY_PARTITION
    )
    assert prefix.history_through == draws[-1].draw_date
    assert prefix.previous_bucket == 2
    assert prefix.x_prev == core.STANDARDIZED_BUCKET_STATES[2]
    assert prefix.transitions == (
        core.TransitionRow(draws[1].draw_date, core.STANDARDIZED_BUCKET_STATES[0], 6),
        core.TransitionRow(draws[2].draw_date, core.STANDARDIZED_BUCKET_STATES[6], 2),
    )


def test_rng_boundary_is_inclusive_but_its_incoming_transition_is_excluded():
    old = Draw(date(2019, 5, 14), (2, 4, 6, 8, 10, 12))
    first = Draw(date(2019, 5, 15), (1, 3, 5, 7, 9, 11))
    second = Draw(date(2019, 5, 16), (1, 2, 3, 4, 5, 6))
    prefix = core.build_transition_prefix(
        (old, first, second), SYNTHETIC_TARGET, core.TRUE_PARITY_PARTITION
    )
    assert prefix.transitions == (
        core.TransitionRow(second.draw_date, core.STANDARDIZED_BUCKET_STATES[6], 3),
    )


@pytest.mark.parametrize("forecast", [core.forecast_candidate, core.forecast_control])
def test_bonus_and_pre_rng_mutations_cannot_change_a_forecast(forecast):
    old_one = Draw(date(2019, 5, 14), (1, 2, 3, 4, 5, 6), 7)
    old_two = Draw(date(2019, 5, 14), (40, 41, 42, 43, 44, 45), 46)
    plain = (_draw(6, 0), _draw(2, 1))
    bonuses = tuple(replace(draw, bonus=49) for draw in plain)
    assert forecast((old_one, *plain), SYNTHETIC_TARGET) == forecast(
        (old_two, *bonuses), SYNTHETIC_TARGET
    )


def test_eligible_prior_main_mutation_changes_the_earlier_forecast():
    first = core.forecast_candidate((_draw(6, 0), _draw(6, 1)), SYNTHETIC_TARGET)
    mutated = core.forecast_candidate((_draw(0, 0), _draw(6, 1)), SYNTHETIC_TARGET)
    assert first.beta > 0 > mutated.beta
    assert first.probabilities != mutated.probabilities
    assert first.final6 == (1, 3, 5, 7, 9, 11)
    assert mutated.final6 == (2, 4, 6, 8, 10, 12)


@pytest.mark.parametrize("offset", [4, 5, 50])
@pytest.mark.parametrize("bucket", [0, 3, 6])
def test_target_same_date_or_future_rows_fail_before_forecast(offset, bucket):
    prefix = (_draw(6, 0), _draw(2, 1))
    before = core.forecast_candidate(prefix, SYNTHETIC_TARGET)
    with pytest.raises(ValueError, match="strictly before target"):
        core.forecast_candidate((*prefix, _draw(bucket, offset)), SYNTHETIC_TARGET)
    assert core.forecast_candidate(prefix, SYNTHETIC_TARGET) == before


@pytest.mark.parametrize(
    "draws", [(_draw(0, 0), _draw(1, 0)), (_draw(0, 1), _draw(1, 0))]
)
def test_duplicate_or_reversed_draw_dates_are_rejected(draws):
    with pytest.raises(ValueError, match="unique and strictly increasing"):
        core.forecast_candidate(draws, SYNTHETIC_TARGET)


def test_prefix_requires_real_date_draw_objects_and_post_rng_history():
    for target in (datetime(2032, 1, 5, tzinfo=UTC), "2032-01-05"):
        with pytest.raises(ValueError, match="target date"):
            core.forecast_candidate((_draw(0, 0),), target)
    with pytest.raises(ValueError, match="draw sequence"):
        core.forecast_candidate((object(),), SYNTHETIC_TARGET)
    with pytest.raises(ValueError, match="no eligible"):
        core.forecast_candidate((), SYNTHETIC_TARGET)
    with pytest.raises(ValueError, match="no eligible"):
        core.forecast_candidate(
            (Draw(date(2019, 5, 14), (1, 2, 3, 4, 5, 6)),), SYNTHETIC_TARGET
        )


@pytest.mark.parametrize("forecast", [core.forecast_candidate, core.forecast_control])
@pytest.mark.parametrize("buckets", [(6,), (6, 6), (0, 6), (6, 0), (0, 0)])
def test_complete_probability_ranking_and_final6_contract(forecast, buckets):
    result = forecast(
        tuple(_draw(k, i) for i, k in enumerate(buckets)), SYNTHETIC_TARGET
    )
    probabilities = dict(result.probabilities)
    assert tuple(probabilities) == tuple(range(1, 50))
    assert all(type(label) is int for label in probabilities)
    assert all(math.isfinite(p) and 0 < p < 1 for p in probabilities.values())
    assert math.fsum(probabilities.values()) == pytest.approx(6.0, abs=1e-12)
    expected_ranking = tuple(
        sorted(probabilities, key=lambda n: (-probabilities[n], n))
    )
    assert result.ranking == expected_ranking
    assert result.top6 == expected_ranking[:6]
    assert result.top12 == expected_ranking[:12]
    assert result.top18 == expected_ranking[:18]
    assert result.final6 == tuple(sorted(expected_ranking[:6]))


def test_exact_fair_forecast_never_evaluates_the_tilt(monkeypatch):
    def forbidden(eta):
        raise AssertionError("exact fair distribution cannot evaluate a tilt")

    monkeypatch.setattr(core, "tilted_moment_log_z", forbidden)
    for forecast in (core.forecast_candidate, core.forecast_control):
        result = forecast((_draw(6, 0),), SYNTHETIC_TARGET)
        assert result.beta.hex() == result.eta.hex() == "0x0.0p+0"
        assert all(p.hex() == (6.0 / 49.0).hex() for _, p in result.probabilities)
        assert result.ranking == tuple(range(1, 50))
        assert result.final6 == (1, 2, 3, 4, 5, 6)


def test_out_of_contract_extreme_forecast_fails_instead_of_clipping(monkeypatch):
    monkeypatch.setattr(
        core, "solve_map_beta", lambda rows: core.MapFit(1000.0, 1001.0)
    )
    with pytest.raises(ValueError, match="forecast is invalid"):
        core.forecast_candidate((_draw(6, 0), _draw(6, 1)), SYNTHETIC_TARGET)


def test_pseudo_partition_literal_digest_contingency_and_exact_correlation():
    literal = b"1,2,5,6,7,8,9,10,12,16,17,18,20,24,28,29,32,33,40,41,42,43,44,48,49"
    assert core.PSEUDO_PARTITION_BYTES == literal
    assert hashlib.sha256(literal).hexdigest() == core.PSEUDO_PARTITION_SHA256
    assert core.PSEUDO_PARTITION_SHA256 == (
        "bfbb8cb711e0734aea8a29f6c02aee41a0f39a36643b3155245dc3550bbf14dd"
    )
    pseudo = {int(value) for value in literal.split(b",")}
    odds = set(range(1, 50, 2))
    assert len(pseudo) == 25 and len(set(range(1, 50)) - pseudo) == 24
    contingency = (
        (len(odds & pseudo), len(odds - pseudo)),
        (len(pseudo - odds), len(set(range(1, 50)) - odds - pseudo)),
    )
    assert contingency == core.TRUE_PSEUDO_CONTINGENCY == ((10, 15), (15, 9))
    p = Fraction(25, 49)
    correlation = (Fraction(len(odds & pseudo), 49) - p * p) / (p * (1 - p))
    assert correlation == core.TRUE_PSEUDO_LABEL_CORRELATION == Fraction(-9, 40)


def test_candidate_and_control_call_one_shared_partition_path(monkeypatch):
    calls = []
    original = core.forecast_partition

    def observe(history_prefix, target_date, *, partition, model_name):
        calls.append((partition, model_name))
        return original(
            history_prefix, target_date, partition=partition, model_name=model_name
        )

    monkeypatch.setattr(core, "forecast_partition", observe)
    core.forecast_candidate((_draw(3, 0),), SYNTHETIC_TARGET)
    core.forecast_control((_draw(3, 0),), SYNTHETIC_TARGET)
    assert calls == [
        (core.TRUE_PARITY_PARTITION, core.CANDIDATE_MODEL_NAME),
        (core.PSEUDO_PARITY_PARTITION, core.CONTROL_MODEL_NAME),
    ]


def test_unregistered_partition_and_mismatched_model_are_rejected():
    arbitrary = core.LabelPartition("arbitrary", frozenset(range(1, 26)))
    with pytest.raises(ValueError, match="not registered"):
        core.build_transition_prefix((_draw(3, 0),), SYNTHETIC_TARGET, arbitrary)
    with pytest.raises(ValueError, match="do not agree"):
        core.forecast_partition(
            (_draw(3, 0),),
            SYNTHETIC_TARGET,
            partition=core.TRUE_PARITY_PARTITION,
            model_name=core.CONTROL_MODEL_NAME,
        )


@pytest.mark.parametrize(
    "labels", [set(range(1, 26)), frozenset(range(1, 25)), frozenset(range(26, 51))]
)
def test_invalid_partition_construction_is_rejected(labels):
    with pytest.raises(ValueError, match="partition is invalid"):
        core.LabelPartition("invalid", labels)


def test_forecasts_have_no_public_constructor_or_dataclass_replace_path():
    with pytest.raises(TypeError, match="only be issued"):
        core.ParityForecast()
    result = core.forecast_candidate((_draw(6, 0), _draw(6, 1)), SYNTHETIC_TARGET)
    with pytest.raises(TypeError, match="only be issued"):
        replace(result, beta=0.0)
    with pytest.raises(FrozenInstanceError):
        result.beta = 0.0


def test_core_and_serialized_fair_state_reject_negative_zero():
    issued = core.forecast_candidate((_draw(6, 0),), SYNTHETIC_TARGET)
    forged = object.__new__(core.ParityForecast)
    for item in fields(issued):
        object.__setattr__(forged, item.name, getattr(issued, item.name))
    object.__setattr__(forged, "beta", -0.0)
    object.__setattr__(forged, "eta", -0.0)
    with pytest.raises(ValueError, match="forecast"):
        forged.__post_init__()
    payload = _synthetic_payload()
    payload["forecasts"][0]["scientific_state"].update(beta=-0.0, eta=-0.0)
    with pytest.raises(ValueError, match="positive zero"):
        evidence.score_target(
            evidence.canonical_json_bytes(payload),
            Draw(SYNTHETIC_TARGET, (1, 2, 3, 4, 5, 6)),
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("model_name", "unregistered"),
        ("target_date", SYNTHETIC_START),
        ("history_through", SYNTHETIC_TARGET),
        ("transition_count", -1),
        ("previous_bucket", 7),
        ("x_prev", 0.0),
        ("beta", math.nan),
        ("eta", 0.0),
        ("expected_bucket", 0.0),
        ("log_z", math.inf),
        ("probabilities", tuple((n, 0.5) for n in range(1, 50))),
        ("ranking", tuple(range(49, 0, -1))),
        ("top6", (1, 2, 3, 4, 5, 6)),
        ("top12", ()),
        ("top18", ()),
        ("final6", (2, 4, 6, 8, 10, 12)),
    ],
)
def test_forecast_validator_rejects_field_forgery(field, value):
    issued = core.forecast_candidate((_draw(6, 0), _draw(6, 1)), SYNTHETIC_TARGET)
    forged = object.__new__(core.ParityForecast)
    for item in fields(issued):
        object.__setattr__(forged, item.name, getattr(issued, item.name))
    object.__setattr__(forged, field, value)
    with pytest.raises(ValueError, match="forecast"):
        forged.__post_init__()


@pytest.mark.parametrize(
    "row",
    [
        core.TransitionRow(SYNTHETIC_START, 0.0, 3),
        core.TransitionRow(SYNTHETIC_START, core.STANDARDIZED_BUCKET_STATES[3], 7),
        core.TransitionRow(SYNTHETIC_START, core.STANDARDIZED_BUCKET_STATES[3], True),
        core.TransitionRow(
            datetime(2032, 1, 1, tzinfo=UTC), core.STANDARDIZED_BUCKET_STATES[3], 3
        ),
    ],
)
def test_invalid_transition_rows_are_rejected(row):
    with pytest.raises(ValueError, match="transition rows are invalid"):
        core.solve_map_beta((row,))


def test_transition_solver_rejects_duplicate_or_reversed_destination_dates():
    first = core.TransitionRow(SYNTHETIC_START, core.STANDARDIZED_BUCKET_STATES[6], 6)
    later = replace(first, destination_date=SYNTHETIC_START + timedelta(days=1))
    for rows in ((first, first), (later, first)):
        with pytest.raises(ValueError, match="strictly increasing"):
            core.solve_map_beta(rows)


@pytest.mark.parametrize("count", [1, 2, 3])
def test_exact_top12_tail_matches_independent_integer_cartesian_enumeration(count):
    weights = tuple(math.comb(12, k) * math.comb(37, 6 - k) for k in range(7))
    distribution = [0] * (6 * count + 1)
    for outcomes in product(range(7), repeat=count):
        distribution[sum(outcomes)] += math.prod(weights[k] for k in outcomes)
    denominator = math.comb(49, 6) ** count
    assert sum(distribution) == denominator
    for threshold in range(6 * count + 1):
        exact = evidence.exact_top12_tail(count, threshold)
        expected = sum(distribution[threshold:])
        assert int(exact["numerator_hex"], 16) == expected
        assert int(exact["denominator_hex"], 16) == denominator
        assert exact["value"] == float(Fraction(expected, denominator))


def test_exact_tail_supports_the_registered_sample_size_without_decimal_int_limits():
    # The zero threshold has probability one under any law; no outcomes are read.
    result = evidence.exact_top12_tail(627, 0)
    expected = math.comb(49, 6) ** 627
    assert int(result["numerator_hex"], 16) == expected
    assert int(result["denominator_hex"], 16) == expected
    assert result["value"] == 1.0


@pytest.mark.parametrize("values", [(0.0,), (0.0, 1.0, 2.0, 4.0), (-1.0, 0.0, 1.0)])
def test_bootstrap_is_fresh_seed_649_aligned_row_resampling_with_linear_quantiles(
    values,
):
    rng = np.random.default_rng(649)
    indices = rng.integers(0, len(values), size=(10_000, len(values)))
    means = np.array(
        [math.fsum(values[index] for index in row) / len(values) for row in indices]
    )
    lower, upper = np.quantile(means, [0.025, 0.975], method="linear")
    expected = {
        "lower": float(lower),
        "upper": float(upper),
        "seed": 649,
        "resamples": 10_000,
        "method": "linear",
    }
    assert evidence.bootstrap_interval(values) == expected
    evidence.bootstrap_interval((100.0, 200.0))
    assert evidence.bootstrap_interval(values) == expected


@pytest.mark.parametrize(
    "values,expected",
    [
        ((0.01, 0.04, 0.03), (0.03, 0.06, 0.06)),
        ((0.01, 0.01, 0.8), (0.03, 0.03, 0.8)),
        ((1.0, 1.0, 0.9783404732169021, 0.0125), (1.0, 1.0, 1.0, 0.05)),
        ((1.0, 1.0, 0.9783404732169021, 0.0), (1.0, 1.0, 1.0, 0.0)),
        ((0.9, 0.4, 0.4), (1.0, 1.0, 1.0)),
    ],
)
def test_general_holm_restores_original_order_and_cumulative_step_down(
    values, expected
):
    assert evidence.holm_adjusted(values) == expected


def test_opportunity_chance_uses_unique_sets_per_target_and_stable_fair_product():
    counts = (1, 4, 2, 3)
    result = evidence.opportunity_summary(counts)
    exact_complement = math.prod(
        1 - Fraction(count, math.comb(49, 6)) for count in counts
    )
    expected = -math.expm1(
        math.fsum(math.log1p(-count / math.comb(49, 6)) for count in counts)
    )
    assert result["cumulative_unique_opportunity_count"] == 10
    assert result["cumulative_fair_probability"] == expected
    assert result["cumulative_fair_probability"] == pytest.approx(
        float(1 - exact_complement), rel=2e-15
    )


def _synthetic_payload(*, tilted: bool = False) -> dict:
    prefix = (_draw(6, 0), _draw(6, 1)) if tilted else (_draw(6, 0),)
    fair = {label: 6.0 / 49.0 for label in range(1, 50)}
    return {
        "target_draw_date": SYNTHETIC_TARGET.isoformat(),
        "history_through": prefix[-1].draw_date.isoformat(),
        "forecasts": [
            evidence.serialize_parity_forecast(
                core.forecast_candidate(prefix, SYNTHETIC_TARGET)
            ),
            evidence.serialize_parity_forecast(
                core.forecast_control(prefix, SYNTHETIC_TARGET)
            ),
            evidence.serialize_comparator_forecast("ensemble_v1.0.0", fair),
            evidence.serialize_comparator_forecast("random_v1.0.0", fair),
        ],
    }


def test_synthetic_scores_match_independent_proper_score_rank_and_joint_law_oracles():
    payload = _synthetic_payload(tilted=True)
    frozen = evidence.canonical_json_bytes(payload)
    actual = Draw(SYNTHETIC_TARGET, (1, 3, 5, 7, 9, 11), 49)
    scored = evidence.score_target(frozen, actual)
    assert scored["forecast_payload_sha256"] == hashlib.sha256(frozen).hexdigest()
    assert len(scored["scores"]) == 4
    for prediction, score in zip(payload["forecasts"], scored["scores"], strict=True):
        assert score["model_name"] == prediction["model_name"]
        probabilities = prediction["probabilities"]
        brier = (
            math.fsum(
                (probabilities[str(n)] - (n in actual.numbers)) ** 2
                for n in range(1, 50)
            )
            / 49
        )
        log_loss = (
            -math.fsum(
                math.log(probabilities[str(n)])
                if n in actual.numbers
                else math.log1p(-probabilities[str(n)])
                for n in range(1, 50)
            )
            / 49
        )
        assert score["brier_score"] == brier
        assert score["log_loss"] == log_loss
        assert (
            score["mean_actual_rank"]
            == math.fsum(prediction["ranking"].index(n) + 1 for n in actual.numbers) / 6
        )
        for top_k in (6, 12, 18):
            assert score[f"top{top_k}_hits"] == len(
                set(prediction[f"top{top_k}"]) & set(actual.numbers)
            )
        assert score["final6_hits"] == len(
            set(prediction["final6"]) & set(actual.numbers)
        )
        state = prediction["scientific_state"]
        if state is not None:
            partition = (
                core.TRUE_ODD_LABELS
                if score["model_name"] == core.CANDIDATE_MODEL_NAME
                else core.PSEUDO_PARTITION_LABELS
            )
            bucket = len(set(actual.numbers) & partition)
            expected = (
                0.0
                if state["beta"] == 0.0
                else (
                    math.log(math.comb(49, 6))
                    + state["beta"] * state["x_prev"] * bucket
                    - state["log_z"]
                )
            )
            assert score["joint_log_gain"] == expected


def test_scoring_uses_all_four_frozen_forecasts_and_deduplicates_identical_final6():
    payload = _synthetic_payload()
    actual = Draw(SYNTHETIC_TARGET, (1, 2, 3, 4, 5, 6), 49)
    scored = evidence.score_target(evidence.canonical_json_bytes(payload), actual)
    frozen_sets = {tuple(item["final6"]) for item in payload["forecasts"]}
    assert scored["unique_opportunity_count"] == len(frozen_sets)
    assert all(item["joint_log_gain"] == 0.0 for item in scored["scores"][:2])
    for item in scored["scores"]:
        fair = 6 / 49
        assert item["brier_score"] == pytest.approx(fair * (1 - fair), abs=1e-16)
        assert item["log_loss"] == pytest.approx(
            -fair * math.log(fair) - (1 - fair) * math.log1p(-fair), abs=1e-16
        )
    assert len(scored["exact_final6_opportunities"]) == 1


def _synthetic_scored_rows() -> list[dict]:
    outcomes = (
        (13, 15, 17, 19, 21, 23),
        (2, 4, 6, 8, 10, 12),
        (1, 14, 15, 28, 29, 42),
    )
    rows = []
    for offset, numbers in enumerate(outcomes):
        target = SYNTHETIC_TARGET + timedelta(days=offset)
        payload = _synthetic_payload(tilted=True)
        payload["target_draw_date"] = target.isoformat()
        rows.append(
            evidence.score_target(
                evidence.canonical_json_bytes(payload), Draw(target, numbers)
            )
        )
    return rows


def test_scope_preserves_every_model_metrics_histogram_and_fixed_calibration_bins():
    rows = _synthetic_scored_rows()
    summary = evidence.summarize_scope(rows)
    assert summary["n"] == 3
    assert summary["first_target"] == rows[0]["target_draw_date"]
    assert summary["last_target"] == rows[-1]["target_draw_date"]
    assert (
        summary["target_dates_sha256"]
        == hashlib.sha256(
            ("\n".join(row["target_draw_date"] for row in rows) + "\n").encode("utf-8")
        ).hexdigest()
    )
    for index, name in enumerate(evidence.MODEL_ORDER):
        model = summary["models"][name]
        assert set(model["final6_histogram"]) == set(map(str, range(7)))
        assert model["final6_histogram"] == {
            str(hits): sum(row["scores"][index]["final6_hits"] == hits for row in rows)
            for hits in range(7)
        }
        for k in (6, 12, 18):
            mean = math.fsum(row["scores"][index][f"top{k}_hits"] for row in rows) / 3
            assert model[f"mean_top{k}_hits"] == mean
            assert model[f"top{k}_lift"] == mean - Fraction(6 * k, 49)
        for metric in ("brier_score", "log_loss", "mean_actual_rank"):
            assert (
                model[metric]
                == math.fsum(row["scores"][index][metric] for row in rows) / 3
            )
        bins = model["calibration_bins"]
        assert len(bins) == 10 and sum(item["count"] for item in bins) == 49 * 3
        for bin_index, actual_bin in enumerate(bins):
            lower, upper = bin_index / 10, (bin_index + 1) / 10
            observations = [
                (
                    row["forecast_payload"]["forecasts"][index]["probabilities"][
                        str(label)
                    ],
                    int(label in row["actual"]),
                )
                for row in rows
                for label in range(1, 50)
                if lower
                <= row["forecast_payload"]["forecasts"][index]["probabilities"][
                    str(label)
                ]
                < upper
            ]
            assert actual_bin == {
                "lower": lower,
                "upper": upper,
                "count": len(observations),
                "mean_probability": math.fsum(p for p, _ in observations)
                / len(observations)
                if observations
                else None,
                "observed_frequency": math.fsum(y for _, y in observations)
                / len(observations)
                if observations
                else None,
            }
        if index == 2:
            assert bins[1]["count"] == 147
            assert all(item["count"] == 0 for i, item in enumerate(bins) if i != 1)


def test_scope_resamples_paired_differences_before_bootstrap_and_joint_gain_sum():
    rows = _synthetic_scored_rows()
    summary = evidence.summarize_scope(rows)
    for contrast, other in (("candidate_minus_v1", 2), ("candidate_minus_pseudo", 1)):
        differences = [
            row["scores"][0]["top12_hits"] - row["scores"][other]["top12_hits"]
            for row in rows
        ]
        rng = np.random.default_rng(649)
        indices = rng.integers(0, 3, size=(10_000, 3))
        bootstrap = [
            math.fsum(differences[i] for i in sample) / 3 for sample in indices
        ]
        endpoints = np.quantile(bootstrap, [0.025, 0.975], method="linear")
        interval = summary["contrasts"][contrast]["top12_paired_ci95"]
        assert (interval["lower"], interval["upper"]) == tuple(endpoints)
        for metric, delta in (
            ("brier_score", "brier_delta"),
            ("log_loss", "log_loss_delta"),
        ):
            assert (
                summary["contrasts"][contrast][delta]
                == math.fsum(
                    row["scores"][0][metric] - row["scores"][other][metric]
                    for row in rows
                )
                / 3
            )
    assert summary["contrasts"]["candidate_minus_pseudo"][
        "joint_log_gain_sum"
    ] == math.fsum(
        row["scores"][0]["joint_log_gain"] - row["scores"][1]["joint_log_gain"]
        for row in rows
    )


def test_scope_rejects_out_of_order_duplicate_or_tampered_scoring():
    rows = _synthetic_scored_rows()
    for invalid in ([rows[0], rows[0]], list(reversed(rows))):
        with pytest.raises(ValueError, match="chronological"):
            evidence.summarize_scope(invalid)
    tampered = deepcopy(rows)
    tampered[0]["scores"][0]["top12_hits"] -= 1
    with pytest.raises(ValueError, match="disagrees"):
        evidence.summarize_scope(tampered)


def _synthetic_passing_scopes() -> dict:
    # Artificial metric fixtures test gate predicates, not an observed model result.
    result = {}
    for scope_name in ("aggregate", "first_half", "second_half"):
        candidate = {
            "top12_lift": 0.1,
            "top6_lift": 0.1,
            "top12_exact_p": {"value": 0.0125},
            "top12_lift_ci95": {"lower": 0.01, "upper": 0.2},
            "joint_log_gain_sum": math.log(20.0) if scope_name == "aggregate" else 1.0,
        }
        control = {
            "top12_exact_p": {"value": math.nextafter(0.05, math.inf)},
            "top12_lift_ci95": {"lower": 0.0, "upper": 0.0},
            "joint_log_gain_sum": 0.0,
        }
        result[scope_name] = {
            "models": {
                core.CANDIDATE_MODEL_NAME: candidate,
                core.CONTROL_MODEL_NAME: deepcopy(control),
                "ensemble_v1.0.0": {},
                "random_v1.0.0": deepcopy(control),
            },
            "contrasts": {
                "candidate_minus_v1": {
                    "top12_paired_ci95": {"lower": 0.01, "upper": 0.2},
                    "brier_delta": 1e-9,
                    "log_loss_delta": 1e-9,
                },
                "candidate_minus_pseudo": {
                    "top12_paired_ci95": {"lower": 0.01, "upper": 0.2},
                    "joint_log_gain_sum": 1.0,
                },
                "candidate_minus_fair": {"brier_delta": 1e-9, "log_loss_delta": 1e-9},
            },
        }
    return result


def test_all_ten_gate_names_and_inclusive_boundaries_match_registration():
    gates = evidence.evaluate_ten_gates(
        _synthetic_passing_scopes(), audit_complete=True, audit_warnings=()
    )
    registration = json.loads(
        (
            ROOT
            / "evidence/research_registrations/v12-post-rng-parity-composition-transition-v1.json"
        ).read_bytes()
    )
    assert [item["number"] for item in gates] == list(range(1, 11))
    assert [item["name"] for item in gates] == registration["gates"]["ordered"]
    assert all(item["passed"] is True for item in gates)


def _gate_failures() -> list[tuple[int, tuple[str, ...], float]]:
    candidate = ("models", core.CANDIDATE_MODEL_NAME)
    result = [
        (1, ("aggregate", *candidate, "top12_lift"), 0.0),
        (
            2,
            ("aggregate", *candidate, "top12_exact_p", "value"),
            math.nextafter(0.0125, math.inf),
        ),
        (3, ("aggregate", *candidate, "top12_lift_ci95", "lower"), 0.0),
        (
            9,
            ("aggregate", *candidate, "joint_log_gain_sum"),
            math.nextafter(math.log(20.0), -math.inf),
        ),
        (
            9,
            ("aggregate", "models", core.CONTROL_MODEL_NAME, "joint_log_gain_sum"),
            math.log(20.0),
        ),
    ]
    for scope in ("aggregate", "first_half", "second_half"):
        if scope != "aggregate":
            result.extend(
                [
                    (4, (scope, *candidate, "top12_lift"), 0.0),
                    (9, (scope, *candidate, "joint_log_gain_sum"), 0.0),
                ]
            )
        result.extend(
            [
                (
                    5,
                    (
                        scope,
                        "contrasts",
                        "candidate_minus_v1",
                        "top12_paired_ci95",
                        "lower",
                    ),
                    0.0,
                ),
                (
                    6,
                    (
                        scope,
                        "contrasts",
                        "candidate_minus_pseudo",
                        "top12_paired_ci95",
                        "lower",
                    ),
                    0.0,
                ),
                (7, (scope, *candidate, "top6_lift"), 0.0),
                (
                    9,
                    (
                        scope,
                        "contrasts",
                        "candidate_minus_pseudo",
                        "joint_log_gain_sum",
                    ),
                    0.0,
                ),
            ]
        )
        for control in (core.CONTROL_MODEL_NAME, "random_v1.0.0"):
            result.extend(
                [
                    (6, (scope, "models", control, "top12_exact_p", "value"), 0.05),
                    (6, (scope, "models", control, "top12_lift_ci95", "lower"), 0.01),
                    (6, (scope, "models", control, "top12_lift_ci95", "upper"), -0.01),
                ]
            )
        for reference in ("candidate_minus_fair", "candidate_minus_v1"):
            for metric in ("brier_delta", "log_loss_delta"):
                result.append(
                    (
                        8,
                        (scope, "contrasts", reference, metric),
                        math.nextafter(1e-9, math.inf),
                    )
                )
    return result


@pytest.mark.parametrize("gate_number,path,value", _gate_failures())
def test_each_gate_control_scope_and_metric_conjunction_is_mandatory(
    gate_number, path, value
):
    scopes = _synthetic_passing_scopes()
    node = scopes
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value
    gates = evidence.evaluate_ten_gates(scopes, audit_complete=True, audit_warnings=())
    assert [item["number"] for item in gates if not item["passed"]] == [gate_number]


@pytest.mark.parametrize(
    "complete,warnings", [(False, ()), (True, ("synthetic_audit_warning",))]
)
def test_gate_ten_requires_completed_audit_and_no_warning(complete, warnings):
    gates = evidence.evaluate_ten_gates(
        _synthetic_passing_scopes(), audit_complete=complete, audit_warnings=warnings
    )
    assert [item["number"] for item in gates if not item["passed"]] == [10]


@pytest.mark.parametrize("omitted", ["aggregate", "first_half", "second_half"])
def test_gates_refuse_missing_scope(omitted):
    scopes = _synthetic_passing_scopes()
    del scopes[omitted]
    with pytest.raises(ValueError, match="all three registered scopes"):
        evidence.evaluate_ten_gates(scopes, audit_complete=True, audit_warnings=())


@pytest.mark.parametrize("count,total", [(0, 0), (True, 1), (1, True), (1, -1), (1, 7)])
def test_exact_tail_refuses_invalid_counts_and_impossible_hit_totals(count, total):
    with pytest.raises(ValueError, match="invalid exact-tail"):
        evidence.exact_top12_tail(count, total)


@pytest.mark.parametrize("values", [(), (True,), (math.nan,), (math.inf,)])
def test_statistical_functions_reject_empty_or_nonfinite_or_boolean_rows(values):
    with pytest.raises(ValueError):
        evidence.bootstrap_interval(values)
    with pytest.raises(ValueError):
        evidence.holm_adjusted(values)


@pytest.mark.parametrize("counts", [(0,), (5,), (True,), (1.0,)])
def test_opportunity_counts_cannot_invent_or_omit_a_target_set(counts):
    with pytest.raises(ValueError, match="one to four"):
        evidence.opportunity_summary(counts)


def test_canonical_encoding_is_finite_sorted_utf8_with_exactly_one_lf():
    raw = evidence.canonical_json_bytes({"z": "合成", "a": [1, False, None]})
    assert raw == '{"a":[1,false,null],"z":"合成"}\n'.encode()
    assert evidence.decode_canonical_json(raw) == {"z": "合成", "a": [1, False, None]}


@pytest.mark.parametrize("value", [math.nan, math.inf, (1, 2), {1: "label"}, {1, 2}])
def test_canonical_encoder_rejects_nonfinite_or_ambiguous_types(value):
    with pytest.raises(ValueError, match="finite, plain JSON"):
        evidence.canonical_json_bytes(value)


@pytest.mark.parametrize(
    "raw",
    [b'{"a":1,"a":2}\n', b'{ "a":1}\n', b'{"a":1}', b'{"a":1}\n\n', b'{"a":NaN}\n'],
)
def test_canonical_decoder_rejects_duplicate_keys_and_alternative_encodings(raw):
    with pytest.raises(ValueError):
        evidence.decode_canonical_json(raw)


def test_deduplicated_opportunity_preserves_primary_order_all_producers_and_digests():
    payload = _synthetic_payload()
    scored = evidence.score_target(
        evidence.canonical_json_bytes(payload),
        Draw(SYNTHETIC_TARGET, (1, 2, 3, 4, 5, 6)),
    )
    opportunity = scored["exact_final6_opportunities"][0]
    assert opportunity["primary_producer"] == core.CANDIDATE_MODEL_NAME
    assert opportunity["producer_model_names"][:2] == [
        core.CANDIDATE_MODEL_NAME,
        core.CONTROL_MODEL_NAME,
    ]
    assert set(opportunity["forecast_sha256_by_producer"]) == set(
        opportunity["producer_model_names"]
    )
    by_name = {forecast["model_name"]: forecast for forecast in payload["forecasts"]}
    for name, digest in opportunity["forecast_sha256_by_producer"].items():
        assert (
            digest
            == hashlib.sha256(evidence.canonical_json_bytes(by_name[name])).hexdigest()
        )


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_model",
        "reordered_models",
        "cutoff",
        "version",
        "probability",
        "ranking",
    ],
)
def test_scoring_rejects_incomplete_identity_chronology_or_forecast_mutations(mutation):
    payload = _synthetic_payload()
    if mutation == "missing_model":
        payload["forecasts"].pop()
    elif mutation == "reordered_models":
        payload["forecasts"][0], payload["forecasts"][1] = (
            payload["forecasts"][1],
            payload["forecasts"][0],
        )
    elif mutation == "cutoff":
        payload["history_through"] = SYNTHETIC_TARGET.isoformat()
    elif mutation == "version":
        payload["forecasts"][0]["model_version"] = "v12.0.0"
    elif mutation == "probability":
        payload["forecasts"][0]["probabilities"]["1"] = 0.5
    else:
        payload["forecasts"][0]["ranking"].reverse()
    with pytest.raises(ValueError):
        evidence.score_target(
            evidence.canonical_json_bytes(payload),
            Draw(SYNTHETIC_TARGET, (1, 2, 3, 4, 5, 6)),
        )


def _report_bindings() -> dict:
    return {
        "synthetic_fixture_only": True,
        "registration_R2": "89c7b2857e2fffa83a9e62ab402cf4b88f9b16be",
        "implementation_base": "f76b6f4e6813447992c1da54641a91313703ec2b",
        "execution_authority_M_A_H2": "1" * 40,
        "authorization_source_A_H_s2": "2" * 40,
        "authorization_sha256": "3" * 64,
        "historical_runtime_dependency_closure_sha256": "4" * 64,
        "runtime": {
            "implementation": "CPython",
            "version": "3.12.12",
            "platform": "synthetic",
        },
        "requirements_sha256": "a0dfeac17ad7e1c41dffe4b41b4810156fb028f879d312430bfc517672a570c6",
        "claim_sha256": "5" * 64,
        "ledger": {"last_event_sha256": "6" * 64, "event_count": 1254},
        "lease_ref": "synthetic-only-not-a-git-ref",
        "lease_commit_L_H2": "7" * 40,
        "nonce_hex": "8" * 64,
    }


def _calendar_only_targets() -> tuple[date, ...]:
    first, last = date(2020, 1, 1), date(2025, 12, 31)
    return tuple(
        first + timedelta(days=offset)
        for offset in range((last - first).days + 1)
        if (first + timedelta(days=offset)).weekday() in (2, 5)
    )


def _report_rows(count: int, *, exact_first: bool = False) -> list[dict]:
    # Calendar identities are registered; every main set here is invented.
    # These in-memory report fixtures do not execute a worker or write evidence.
    targets = _calendar_only_targets()[:count]
    training = (Draw(date(2019, 12, 28), (1, 3, 5, 7, 9, 11)),)
    probabilities = {label: 6.0 / 49.0 for label in range(1, 50)}
    forecasts = [
        evidence.serialize_parity_forecast(
            core.forecast_candidate(training, targets[0])
        ),
        evidence.serialize_parity_forecast(core.forecast_control(training, targets[0])),
        evidence.serialize_comparator_forecast("ensemble_v1.0.0", probabilities),
        evidence.serialize_comparator_forecast("random_v1.0.0", probabilities),
    ]
    rows = []
    for index, target in enumerate(targets):
        payload = {
            "schema_version": "synthetic-report-fixture-v1",
            "classification": "synthetic_fixture_only",
            "target_draw_date": target.isoformat(),
            "history_through": training[-1].draw_date.isoformat(),
            "training_cutoff_date": training[-1].draw_date.isoformat(),
            "visible_prefix_sha256": "9" * 64,
            "visible_prefix_draw_count": 1,
            "bindings": _report_bindings(),
            "forecasts": deepcopy(forecasts),
        }
        main = (
            (1, 2, 3, 4, 5, 6)
            if exact_first and index == 0
            else (40, 42, 44, 46, 48, 49)
        )
        row = evidence.score_target(
            evidence.canonical_json_bytes(payload), Draw(target, main, 39)
        )
        row.update(
            prediction_generated_at="2032-01-01T00:00:00Z",
            prediction_frozen_event_sequence=2 * index,
            prediction_frozen_event_sha256=f"{2 * index + 1:064x}",
            scored_event_sequence=2 * index + 1,
            scored_event_sha256=f"{2 * index + 2:064x}",
        )
        rows.append(row)
    return rows


@pytest.fixture(scope="module")
def complete_synthetic_report():
    rows = _report_rows(627)
    return rows, evidence.build_report(rows, _report_bindings(), audit_complete=True)


def test_complete_report_preserves_all_targets_forecasts_snapshots_and_bindings(
    complete_synthetic_report,
):
    rows, report = complete_synthetic_report
    assert report["targets"] == rows
    assert report["bindings"] == _report_bindings()
    assert report["complete_registered_scope"] is True
    assert report["processed_target_count"] == report["expected_target_count"] == 627
    assert report["exclusions"]["unprocessed_target_count"] == 0
    assert (
        report["exclusions"]["known_2026_scored"]
        == report["exclusions"]["burn_in_scored"]
        == 0
    )
    assert report["model_version"] == "v12.0.1" and report["seed"] == 649
    for row in report["targets"]:
        payload = row["forecast_payload"]
        assert date.fromisoformat(payload["training_cutoff_date"]) < date.fromisoformat(
            row["target_draw_date"]
        )
        assert payload["target_draw_date"] == row["target_draw_date"]
        assert payload["history_through"] == payload["training_cutoff_date"]
        assert payload["bindings"] == report["bindings"]
        assert (
            row["forecast_payload_sha256"]
            == hashlib.sha256(evidence.canonical_json_bytes(payload)).hexdigest()
        )
        assert row["prediction_frozen_event_sequence"] < row["scored_event_sequence"]
        assert (
            len(row["prediction_frozen_event_sha256"])
            == len(row["scored_event_sha256"])
            == 64
        )
        assert row["prediction_generated_at"] == "2032-01-01T00:00:00Z"
        assert len(payload["forecasts"]) == len(row["scores"]) == 4
        for forecast, score in zip(payload["forecasts"], row["scores"], strict=True):
            assert set(forecast["probabilities"]) == set(map(str, range(1, 50)))
            assert set(forecast["ranking"]) == set(range(1, 50))
            assert all(
                forecast[key]
                for key in (
                    "model_name",
                    "model_version",
                    "feature_set",
                    "top6",
                    "top12",
                    "top18",
                    "final6",
                )
            )
            assert (
                score["forecast_sha256"]
                == hashlib.sha256(evidence.canonical_json_bytes(forecast)).hexdigest()
            )
    canonical = evidence.canonical_json_bytes(report)
    assert evidence.decode_canonical_json(canonical) == report


def test_complete_report_has_fixed_halves_all_gates_and_honest_negative_disposition(
    complete_synthetic_report,
):
    _, report = complete_synthetic_report
    assert report["scope_order"] == ["aggregate", "first_half", "second_half"]
    assert [report["scopes"][name]["n"] for name in report["scope_order"]] == [
        627,
        314,
        313,
    ]
    assert report["scopes"]["first_half"]["last_target"] == "2022-12-31"
    assert report["scopes"]["second_half"]["first_target"] == "2023-01-04"
    assert report["scopes"]["second_half"]["last_target"] == "2025-12-31"
    assert set(report["annual_descriptive_only"]) == {
        str(year) for year in range(2020, 2026)
    }
    assert [gate["number"] for gate in report["gates"]] == list(range(1, 11))
    assert report["audit"] == {"complete": True, "warnings": []}
    assert report["disposition"] == "Reject"
    assert report["classification"] == "consumed_historical_diagnostic_only"
    assert report["classification_zh"] == "历史诊断/审计候选、不可晋升"
    assert report["eligible_evidence"] is report["promotion_authority"] is False
    assert report["multiplicity"]["input_vector"] == [1.0, 1.0, 0.9783404732169021, 1.0]
    for best in report["best_final6_by_model"].values():
        assert best["final6_hits"] == 0 and len(best["target_dates"]) == 627


def test_markdown_lists_every_target_model_and_points_to_complete_json(
    complete_synthetic_report,
):
    _, report = complete_synthetic_report
    markdown = evidence.render_markdown(report)
    assert "已消耗的历史诊断数据" in markdown
    assert "不可晋升" in markdown and "不具备晋升或未来购票建议的效力" in markdown
    assert "完整 1–49 概率、排名" in markdown and "JSON 报告的 targets" in markdown
    assert "calibration" in markdown and "0–6 分布" in markdown
    assert "627/627" in markdown and "Reject" in markdown
    assert "没有完整的 627" not in markdown
    assert all(
        term not in markdown.lower() for term in ("untouched", "blind", "confirmed")
    )
    assert (
        report["bindings"]["historical_runtime_dependency_closure_sha256"] in markdown
    )
    assert report["bindings"]["execution_authority_M_A_H2"] in markdown
    assert report["bindings"]["claim_sha256"] in markdown
    for row in report["targets"]:
        for forecast in row["forecast_payload"]["forecasts"]:
            prefix = f"| {row['target_draw_date']} | {row['forecast_payload']['history_through']} | {forecast['model_name']} |"
            assert markdown.count(prefix) == 1
    assert (
        len([line for line in markdown.splitlines() if line.startswith("| 20")])
        == 627 * 4
    )


@pytest.mark.parametrize("exact", [False, True])
def test_partial_report_preserves_only_processed_rows_and_never_fabricates_gates(exact):
    rows = _report_rows(1, exact_first=exact)
    reason = (
        "exact_final6_pending_independent_audit" if exact else "synthetic_interruption"
    )
    report = evidence.build_report(
        rows, _report_bindings(), audit_complete=False, stop_reason=reason
    )
    assert report["targets"] == rows and report["processed_target_count"] == 1
    assert report["complete_registered_scope"] is False
    assert report["gates"] is report["multiplicity"] is None
    assert report["scopes"] == {}
    assert report["exclusions"]["unprocessed_target_count"] == 626
    assert report["audit"]["complete"] is False
    assert report["stop_reason"] == reason
    assert report["disposition"] == ("pending_audit" if exact else "Archive")
    assert report["eligible_evidence"] is report["promotion_authority"] is False
    markdown = evidence.render_markdown(report)
    assert "1/627" in markdown and '"complete":false' in markdown
    assert "没有完整的 627 期十项 gates 报告" in markdown
    assert "未运行的目标没有预测或评分" in markdown
    assert "2020-01-04" not in markdown


def test_empty_and_nonregistered_or_after_exact6_reports_fail_closed():
    empty = evidence.build_report(
        [],
        _report_bindings(),
        audit_complete=False,
        stop_reason="synthetic_before_first_freeze",
    )
    assert empty["targets"] == [] and empty["gates"] is None
    assert empty["disposition"] == "Archive" and empty["processed_target_count"] == 0
    with pytest.raises(ValueError, match="continued after an exact Final-6"):
        evidence.build_report(
            _report_rows(2, exact_first=True), _report_bindings(), audit_complete=True
        )
    rows = _report_rows(2)
    with pytest.raises(ValueError, match="registered chronological prefix"):
        evidence.build_report(rows[1:], _report_bindings(), audit_complete=True)


@pytest.mark.parametrize(
    "complete,warnings", [(False, ()), (True, ("synthetic_integrity_warning",))]
)
def test_complete_scope_with_missing_audit_or_warning_remains_archive(
    complete_synthetic_report, monkeypatch, complete, warnings
):
    rows, previously_computed = complete_synthetic_report
    summaries = {scope["n"]: scope for scope in previously_computed["scopes"].values()}
    # Reuse this fixture's independently computed inference to isolate disposition.
    monkeypatch.setattr(
        evidence, "_scope_summary", lambda values: deepcopy(summaries[len(values)])
    )
    report = evidence.build_report(
        rows, _report_bindings(), audit_complete=complete, audit_warnings=warnings
    )
    assert report["complete_registered_scope"] is True
    assert report["disposition"] == "Archive" and report["gates"][9]["passed"] is False
    assert report["eligible_evidence"] is report["promotion_authority"] is False
    assert report["audit"] == {"complete": complete, "warnings": list(warnings)}
    markdown = evidence.render_markdown(report)
    assert "Archive" in markdown
    if not complete:
        assert '"complete":false' in markdown
    for warning in warnings:
        assert warning in markdown


def test_even_hypothetical_all_gate_pass_cannot_become_confirmation_or_promotion(
    complete_synthetic_report, monkeypatch
):
    rows, computed = complete_synthetic_report
    synthetic_predicates = _synthetic_passing_scopes()
    summaries = {}
    for name, original in computed["scopes"].items():
        summary = deepcopy(original)
        for model, values in synthetic_predicates[name]["models"].items():
            summary["models"][model].update(values)
        for contrast, values in synthetic_predicates[name]["contrasts"].items():
            summary["contrasts"][contrast].update(values)
        summaries[summary["n"]] = summary
    # Artificial predicate input proves language/governance even if every gate passes.
    monkeypatch.setattr(
        evidence, "_scope_summary", lambda values: deepcopy(summaries[len(values)])
    )
    report = evidence.build_report(rows, _report_bindings(), audit_complete=True)
    assert all(gate["passed"] for gate in report["gates"])
    assert report["disposition"] == "consumed_diagnostic_all_gates_pass"
    assert report["classification"] == "consumed_historical_diagnostic_only"
    assert report["eligible_evidence"] is report["promotion_authority"] is False
    markdown = evidence.render_markdown(report)
    assert "不可晋升" in markdown and "已消耗的历史诊断数据" in markdown
    assert all(
        term not in markdown.lower() for term in ("untouched", "blind", "confirmed")
    )


def test_stop_marker_cannot_be_hidden_by_a_full_row_count(complete_synthetic_report):
    rows, _ = complete_synthetic_report
    report = evidence.build_report(
        rows,
        _report_bindings(),
        audit_complete=True,
        stop_reason="synthetic_terminal_error",
    )
    assert report["processed_target_count"] == 627
    assert report["complete_registered_scope"] is False
    assert report["disposition"] == "Archive" and report["gates"] is None
    assert report["stop_reason"] == "synthetic_terminal_error"
    assert "没有完整的 627 期十项 gates 报告" in evidence.render_markdown(report)


@pytest.mark.parametrize(
    "mutation", ["empty", "missing", "order", "ranking", "probability"]
)
def test_frozen_payload_can_be_fully_validated_without_any_reveal(mutation):
    payload = _synthetic_payload()
    assert (
        evidence.validate_frozen_payload(evidence.canonical_json_bytes(payload)) is None
    )
    if mutation == "empty":
        payload["forecasts"] = []
    elif mutation == "missing":
        payload["forecasts"].pop()
    elif mutation == "order":
        payload["forecasts"].reverse()
    elif mutation == "ranking":
        payload["forecasts"][0]["ranking"].reverse()
    else:
        payload["forecasts"][0]["probabilities"]["1"] = 0.5
    with pytest.raises(ValueError):
        evidence.validate_frozen_payload(evidence.canonical_json_bytes(payload))
