"""Source-only synthetic and literal mathematical checks for frozen V13 core."""

import ast
import dataclasses
import hashlib
import inspect
import json
import math
from datetime import UTC, date, datetime, timedelta
from fractions import Fraction

import pytest

from lotto649.models import v13_main_set_overlap as core

# Copied literal fixtures from R13 scientific fingerprint 7d86364d43907a64...
# They contain only closed combinatorics and synthetic integer-count sequences.
MOMENT_ORACLES = [
    {
        "name": "positive_one",
        "outputs": {
            "beta": {"decimal": 1.0, "hex": "0x1.0000000000000p+0"},
            "complement_mean": {
                "decimal": 4.517822385994081,
                "hex": "0x1.212400813ecd1p+2",
            },
            "expected_six": {"decimal": 6.0, "hex": "0x1.8000000000000p+2"},
            "log_z": {"decimal": 17.534194398142738, "hex": "0x1.188c0f6cdbabep+4"},
            "mean": {"decimal": 1.482177614005919, "hex": "0x1.7b6ffdfb04cbcp+0"},
            "p_in": {"decimal": 0.24702960233431984, "hex": "0x1.f9eaa7f95bba5p-3"},
            "p_out": {"decimal": 0.10506563688358328, "hex": "0x1.ae594e25930d8p-4"},
        },
    },
    {
        "name": "negative_one",
        "outputs": {
            "beta": {"decimal": -1.0, "hex": "-0x1.0000000000000p+0"},
            "complement_mean": {
                "decimal": 5.686048623067681,
                "hex": "0x1.6be8387be2a85p+2",
            },
            "expected_six": {
                "decimal": 5.999999999999999,
                "hex": "0x1.7ffffffffffffp+2",
            },
            "log_z": {"decimal": 15.953720678413367, "hex": "0x1.fe84e13a69bd3p+3"},
            "mean": {"decimal": 0.31395137693231817, "hex": "0x1.417c7841d57a9p-2"},
            "p_in": {"decimal": 0.0523252294887197, "hex": "0x1.aca5f5ad1ca37p-5"},
            "p_out": {"decimal": 0.13223368890855072, "hex": "0x1.0ed0894a55539p-3"},
        },
    },
    {
        "name": "real_log2_binary64_input",
        "outputs": {
            "beta": {"decimal": 0.6931471805599453, "hex": "0x1.62e42fefa39efp-1"},
            "complement_mean": {
                "decimal": 4.782004731425376,
                "hex": "0x1.320c5d92b2832p+2",
            },
            "expected_six": {"decimal": 6.0, "hex": "0x1.8000000000000p+2"},
            "log_z": {"decimal": 17.12063123278197, "hex": "0x1.11ee1b03facbbp+4"},
            "mean": {"decimal": 1.2179952685746243, "hex": "0x1.37ce89b535f39p+0"},
            "p_in": {"decimal": 0.20299921142910404, "hex": "0x1.9fbe0cf19d44cp-3"},
            "p_out": {"decimal": 0.11120941235872968, "hex": "0x1.c783855168f2dp-4"},
        },
    },
    {
        "name": "positive_zero",
        "outputs": {
            "beta": {"decimal": 0.0, "hex": "0x0.0p+0"},
            "complement_mean": {
                "decimal": 5.26530612244898,
                "hex": "0x1.50fac687d6344p+2",
            },
            "expected_six": {"decimal": 6.0, "hex": "0x1.8000000000000p+2"},
            "log_z": {"decimal": 16.45341121889615, "hex": "0x1.07412c1f4cc68p+4"},
            "mean": {"decimal": 0.7346938775510204, "hex": "0x1.7829cbc14e5e1p-1"},
            "p_in": {"decimal": 0.12244897959183673, "hex": "0x1.f58d0fac687d6p-4"},
            "p_out": {"decimal": 0.12244897959183673, "hex": "0x1.f58d0fac687d6p-4"},
        },
    },
]

ROOT_ORACLES = [
    {
        "D": 0,
        "Ksum": 0,
        "counts_run_length": [],
        "name": "empty",
        "outputs": {
            "beta": {"decimal": 0.0, "hex": "0x0.0p+0"},
            "complement_mean": {
                "decimal": 5.26530612244898,
                "hex": "0x1.50fac687d6344p+2",
            },
            "expected_six": {"decimal": 6.0, "hex": "0x1.8000000000000p+2"},
            "log_z": {"decimal": 16.45341121889615, "hex": "0x1.07412c1f4cc68p+4"},
            "mean": {"decimal": 0.7346938775510204, "hex": "0x1.7829cbc14e5e1p-1"},
            "objective_at_root": {"decimal": 0.0, "hex": "0x0.0p+0"},
            "p_in": {"decimal": 0.12244897959183673, "hex": "0x1.f58d0fac687d6p-4"},
            "p_out": {"decimal": 0.12244897959183673, "hex": "0x1.f58d0fac687d6p-4"},
            "score_at_root": {"decimal": 0.0, "hex": "0x0.0p+0"},
        },
    },
    {
        "D": 1,
        "Ksum": 0,
        "counts_run_length": [{"count": 1, "value": 0}],
        "name": "single_zero",
        "outputs": {
            "beta": {"decimal": -0.49105746377637116, "hex": "-0x1.f6d7c48d813f8p-2"},
            "complement_mean": {
                "decimal": 5.508942536223628,
                "hex": "0x1.609283b727ec0p+2",
            },
            "expected_six": {
                "decimal": 5.999999999999999,
                "hex": "0x1.7ffffffffffffp+2",
            },
            "log_z": {"decimal": 16.155658634378824, "hex": "0x1.027d93e87ff40p+4"},
            "mean": {"decimal": 0.4910574637763711, "hex": "0x1.f6d7c48d813f7p-2"},
            "objective_at_root": {
                "decimal": -16.276227350744065,
                "hex": "-0x1.046b6d5edb4dcp+4",
            },
            "p_in": {"decimal": 0.08184291062939518, "hex": "0x1.4f3a830900d4fp-4"},
            "p_out": {"decimal": 0.12811494270287507, "hex": "0x1.066120884d565p-3"},
            "score_at_root": {
                "decimal": 5.551115123125783e-17,
                "hex": "0x1.0000000000000p-54",
            },
        },
    },
    {
        "D": 1,
        "Ksum": 1,
        "counts_run_length": [{"count": 1, "value": 1}],
        "name": "single_one",
        "outputs": {
            "beta": {"decimal": 0.1651855408776437, "hex": "0x1.524ccbfebb7f0p-3"},
            "complement_mean": {
                "decimal": 5.165185540877643,
                "hex": "0x1.4a92665ff5dbfp+2",
            },
            "expected_six": {"decimal": 6.0, "hex": "0x1.8000000000000p+2"},
            "log_z": {"decimal": 16.5829111221342, "hex": "0x1.09539a9ce0a82p+4"},
            "mean": {"decimal": 0.8348144591223562, "hex": "0x1.ab6ccd0051203p-1"},
            "objective_at_root": {
                "decimal": -16.431368712714075,
                "hex": "-0x1.06e6e2e119fe4p+4",
            },
            "p_in": {"decimal": 0.13913574318705937, "hex": "0x1.1cf333558b6adp-3"},
            "p_out": {"decimal": 0.12012059397389868, "hex": "0x1.ec03926b1a94cp-4"},
            "score_at_root": {
                "decimal": 1.1102230246251565e-16,
                "hex": "0x1.0000000000000p-53",
            },
        },
    },
    {
        "D": 1,
        "Ksum": 6,
        "counts_run_length": [{"count": 1, "value": 6}],
        "name": "single_six",
        "outputs": {
            "beta": {"decimal": 2.741094831823059, "hex": "0x1.5edc3208f5138p+1"},
            "complement_mean": {
                "decimal": 2.7410948318230597,
                "hex": "0x1.5edc3208f513ap+1",
            },
            "expected_six": {"decimal": 6.0, "hex": "0x1.8000000000000p+2"},
            "log_z": {"decimal": 21.634767855000426, "hex": "0x1.5a2802569c766p+4"},
            "mean": {"decimal": 3.2589051681769408, "hex": "0x1.a123cdf70aec7p+1"},
            "objective_at_root": {
                "decimal": -8.944999302585614,
                "hex": "-0x1.1e3d6f2d6b230p+3",
            },
            "p_in": {"decimal": 0.5431508613628234, "hex": "0x1.1617dea4b1f2fp-1"},
            "p_out": {"decimal": 0.06374639143774558, "hex": "0x1.051aefa768fccp-4"},
            "score_at_root": {
                "decimal": 4.440892098500626e-16,
                "hex": "0x1.0000000000000p-51",
            },
        },
    },
    {
        "D": 49,
        "Ksum": 36,
        "counts_run_length": [{"count": 13, "value": 0}, {"count": 36, "value": 1}],
        "name": "fair_49",
        "outputs": {
            "beta": {"decimal": 0.0, "hex": "0x0.0p+0"},
            "complement_mean": {
                "decimal": 5.26530612244898,
                "hex": "0x1.50fac687d6344p+2",
            },
            "expected_six": {"decimal": 6.0, "hex": "0x1.8000000000000p+2"},
            "log_z": {"decimal": 16.45341121889615, "hex": "0x1.07412c1f4cc68p+4"},
            "mean": {"decimal": 0.7346938775510204, "hex": "0x1.7829cbc14e5e1p-1"},
            "objective_at_root": {
                "decimal": -806.2171497259113,
                "hex": "-0x1.931bcb8fed8ffp+9",
            },
            "p_in": {"decimal": 0.12244897959183673, "hex": "0x1.f58d0fac687d6p-4"},
            "p_out": {"decimal": 0.12244897959183673, "hex": "0x1.f58d0fac687d6p-4"},
            "score_at_root": {
                "decimal": -1.887379141862766e-15,
                "hex": "-0x1.1000000000000p-49",
            },
        },
    },
    {
        "D": 49,
        "Ksum": 35,
        "counts_run_length": [{"count": 14, "value": 0}, {"count": 35, "value": 1}],
        "name": "below_fair_49",
        "outputs": {
            "beta": {"decimal": -0.034469008436897625, "hex": "-0x1.1a5ebffec8e54p-5"},
            "complement_mean": {
                "decimal": 5.285010836562512,
                "hex": "0x1.523d9e1782a97p+2",
            },
            "expected_six": {"decimal": 6.0, "hex": "0x1.8000000000000p+2"},
            "log_z": {"decimal": 16.428427819133415, "hex": "0x1.06dad720fdfe7p+4"},
            "mean": {"decimal": 0.7149891634374875, "hex": "0x1.6e130f43eab47p-1"},
            "objective_at_root": {
                "decimal": -806.1999724891,
                "hex": "-0x1.931998b2d2646p+9",
            },
            "p_in": {"decimal": 0.11916486057291459, "hex": "0x1.e81969afe39b4p-4"},
            "p_out": {"decimal": 0.12290722875726773, "hex": "0x1.f76d91ff45734p-4"},
            "score_at_root": {
                "decimal": 8.68749516769185e-15,
                "hex": "0x1.3900000000000p-47",
            },
        },
    },
    {
        "D": 49,
        "Ksum": 37,
        "counts_run_length": [{"count": 12, "value": 0}, {"count": 37, "value": 1}],
        "name": "above_fair_49",
        "outputs": {
            "beta": {"decimal": 0.03380003012654931, "hex": "0x1.14e3ccffea3e0p-5"},
            "complement_mean": {
                "decimal": 5.245587755716868,
                "hex": "0x1.4fb7b5b4c686fp+2",
            },
            "expected_six": {"decimal": 6.0, "hex": "0x1.8000000000000p+2"},
            "log_z": {"decimal": 16.47857602744898, "hex": "0x1.07a83f5628b00p+4"},
            "mean": {"decimal": 0.7544122442831317, "hex": "0x1.82425259cbc87p-1"},
            "objective_at_root": {
                "decimal": -806.200195451336,
                "hex": "-0x1.9319a0012a25ep+9",
            },
            "p_in": {"decimal": 0.12573537404718862, "hex": "0x1.01818c3bdd305p-3"},
            "p_out": {"decimal": 0.1219904129236481, "hex": "0x1.f3ac381eebf28p-4"},
            "score_at_root": {
                "decimal": -2.3314683517128287e-15,
                "hex": "-0x1.5000000000000p-49",
            },
        },
    },
    {
        "D": 4443,
        "Ksum": 0,
        "counts_run_length": [{"count": 4443, "value": 0}],
        "name": "extreme_zero_4443",
        "outputs": {
            "beta": {"decimal": -6.476384120031792, "hex": "-0x1.9e7d13d1f7b2cp+2"},
            "complement_mean": {
                "decimal": 5.998542339833439,
                "hex": "0x1.7fe81e2150615p+2",
            },
            "expected_six": {"decimal": 6.0, "hex": "0x1.8000000000000p+2"},
            "log_z": {"decimal": 15.624675852402724, "hex": "0x1.f3fd58369575cp+3"},
            "mean": {"decimal": 0.0014576601665612868, "hex": "0x1.7e1deaf9eb8e8p-10"},
            "objective_at_root": {
                "decimal": -69441.4065878604,
                "hex": "-0x1.0f416816245b6p+16",
            },
            "p_in": {"decimal": 0.0002429433610935478, "hex": "0x1.fd7d394d3a135p-13"},
            "p_out": {"decimal": 0.13950098464728927, "hex": "0x1.1db2b1368f2aap-3"},
            "score_at_root": {
                "decimal": -5.466113672802919e-15,
                "hex": "-0x1.89e0000000000p-48",
            },
        },
    },
    {
        "D": 4443,
        "Ksum": 26658,
        "counts_run_length": [{"count": 4443, "value": 6}],
        "name": "extreme_six_4443",
        "outputs": {
            "beta": {"decimal": 11.507508378130638, "hex": "0x1.703d8235d08c0p+3"},
            "complement_mean": {
                "decimal": 0.0025900311452014086,
                "hex": "0x1.537b0620e6e16p-9",
            },
            "expected_six": {
                "decimal": 6.000000000000001,
                "hex": "0x1.8000000000001p+2",
            },
            "log_z": {"decimal": 69.0476422901051, "hex": "0x1.1430c923f7a1cp+6"},
            "mean": {"decimal": 5.997409968854799, "hex": "0x1.7fd5909f3be33p+2"},
            "objective_at_root": {
                "decimal": -77.72772526680764,
                "hex": "-0x1.36e930cff5a59p+6",
            },
            "p_in": {"decimal": 0.9995683281424665, "hex": "0x1.ffc76b7efa844p-1"},
            "p_out": {"decimal": 6.023328244654439e-05, "hex": "0x1.f945fd36ec792p-15"},
            "score_at_root": {
                "decimal": -3.780975532663433e-12,
                "hex": "-0x1.0a10000000000p-38",
            },
        },
    },
]

ANCHOR = (4, 11, 19, 27, 38, 49)
OTHER = (1, 2, 3, 5, 6, 7)


def _canonical(value):
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode()


def _rows(*numbers):
    result = []
    day = date(2019, 5, 15)
    for values in numbers:
        result.append(core.MainDraw(day, values))
        day += timedelta(days=3 if day.weekday() == 2 else 4)
    return result, day


def _scalar_result(beta):
    mean, complement, log_z = core.moments(beta)
    p_in, p_out = (
        (6.0 / 49.0, 6.0 / 49.0) if beta == 0.0 else (mean / 6.0, complement / 43.0)
    )
    return {
        "beta": beta,
        "mean": mean,
        "complement_mean": complement,
        "log_z": log_z,
        "p_in": p_in,
        "p_out": p_out,
        "expected_six": math.fsum([p_in] * 6 + [p_out] * 43),
    }


def _literal_outputs(actual, expected):
    assert set(actual) == set(expected)
    for name, value in actual.items():
        assert type(value) is float
        assert value == expected[name]["decimal"], name
        assert value.hex() == expected[name]["hex"], name


@pytest.mark.parametrize("oracle", MOMENT_ORACLES, ids=lambda item: item["name"])
def test_all_four_literal_moment_oracles(oracle):
    beta = float.fromhex(oracle["outputs"]["beta"]["hex"])
    _literal_outputs(_scalar_result(beta), oracle["outputs"])


@pytest.mark.parametrize("oracle", ROOT_ORACLES, ids=lambda item: item["name"])
def test_all_nine_literal_root_score_objective_oracles(oracle):
    counts = tuple(
        k["value"] for k in oracle["counts_run_length"] for _ in range(k["count"])
    )
    assert len(counts) == oracle["D"]
    assert sum(counts) == oracle["Ksum"]
    beta = core.solve_map_beta(counts)
    values = _scalar_result(beta)
    values["score_at_root"] = core.map_score(beta, counts)
    values["objective_at_root"] = core.map_objective(beta, counts)
    _literal_outputs(values, oracle["outputs"])


def test_closed_combinatorial_fair_and_real_log2_oracles():
    mass = tuple(math.comb(6, k) * math.comb(43, 6 - k) for k in range(7))
    assert mass == (6096454, 5775588, 1851150, 246820, 13545, 258, 1) == core.N
    assert sum(mass) == math.comb(49, 6) == 13983816
    mean = sum(Fraction(k * mass[k], sum(mass)) for k in range(7))
    second = sum(Fraction(k * k * mass[k], sum(mass)) for k in range(7))
    assert mean == Fraction(36, 49)
    assert second - mean * mean == Fraction(5547, 9604)
    tilted = tuple(mass[k] * (2**k) for k in range(7))
    z = sum(tilted)
    mu = sum(Fraction(k * tilted[k], z) for k in range(7))
    assert z == 27251830
    assert mu == Fraction(3319260, 2725183)
    assert mu / 6 == Fraction(553210, 2725183)
    assert (6 - mu) / 43 == Fraction(303066, 2725183)


def test_integer_fair_bypass_precedes_all_floating_score_calls(monkeypatch):
    counts = (0,) * 13 + (1,) * 36
    assert core.map_score(0.0, counts).hex() == "-0x1.1000000000000p-49"

    def forbidden(*args):
        raise AssertionError("floating score cannot run on exact integer bypass")

    monkeypatch.setattr(core, "_score", forbidden)
    assert core.solve_map_beta(counts).hex() == "0x0.0p+0"
    assert core.solve_map_beta(()).hex() == "0x0.0p+0"


def test_all_256_bisections_equality_moves_upper_and_final_midpoint(monkeypatch):
    calls = []

    def score(beta, counts):
        calls.append(beta)
        return 1.0 - beta

    monkeypatch.setattr(core, "_score", score)
    answer = core.solve_map_beta((1,))
    lo, hi = 0.0, 70.0
    expected = [0.0, lo, hi]
    for _ in range(256):
        midpoint = lo + (hi - lo) / 2.0
        expected.append(midpoint)
        if midpoint < 1.0:
            lo = midpoint
        else:
            hi = midpoint
    assert calls == expected
    assert len(calls) == 259
    assert calls.count(1.0) > 150  # Stagnation and exact zero must not stop iterations.
    assert answer == lo + (hi - lo) / 2.0 == 1.0


@pytest.mark.parametrize(
    "stage,replacement",
    [
        (0, 0.0),
        (0, -1.0),
        (0, float("nan")),
        (1, 0.0),
        (1, float("inf")),
        (2, 0.0),
        (2, 1.0),
        (3, float("nan")),
        (17, float("inf")),
    ],
)
def test_sign_endpoint_and_midpoint_failures_are_terminal(
    monkeypatch, stage, replacement
):
    calls = []
    real = core._score

    def broken(beta, counts):
        position = len(calls)
        calls.append(beta)
        return replacement if position == stage else real(beta, counts)

    monkeypatch.setattr(core, "_score", broken)
    with pytest.raises(core.OverlapValidationError):
        core.solve_map_beta((1,))
    assert len(calls) <= max(stage + 1, 3)  # Both endpoints are evaluated once.


def test_numerical_exception_propagates_without_rescue_or_retry(monkeypatch):
    calls = []

    def broken(value):
        calls.append(value)
        raise ArithmeticError("synthetic numerical failure")

    monkeypatch.setattr(core.math, "exp", broken)
    with pytest.raises(ArithmeticError, match="synthetic numerical failure"):
        core.solve_map_beta((1,))
    assert len(calls) == 1


@pytest.mark.parametrize(
    "beta",
    [
        None,
        True,
        1,
        "1",
        float("nan"),
        float("inf"),
        -float("inf"),
        26722.0001,
        -26722.0001,
    ],
)
def test_moment_domains_are_closed(beta):
    with pytest.raises(core.OverlapValidationError):
        core.moments(beta)


@pytest.mark.parametrize(
    "counts", [None, {0}, iter([0]), [True], [1.0], ["1"], [-1], [7], [0] * 4444]
)
@pytest.mark.parametrize(
    "function", [core.solve_map_beta, core.map_score, core.map_objective]
)
def test_count_domains_are_closed(counts, function):
    with pytest.raises(core.OverlapValidationError):
        if function is core.solve_map_beta:
            function(counts)
        else:
            function(0.0, counts)


@pytest.mark.parametrize("beta", [-26722.0, 26722.0])
def test_bracket_underflow_is_permitted_but_final_probabilities_cannot_be_repaired(
    beta,
):
    mean, complement, log_z = core.moments(beta)
    assert all(math.isfinite(value) for value in (mean, complement, log_z))
    assert (mean, complement) == ((0.0, 6.0) if beta < 0.0 else (6.0, 0.0))
    with pytest.raises(core.OverlapValidationError):
        core._distribution(beta, ANCHOR)


@pytest.mark.parametrize(
    "values",
    [
        (),
        (1, 2, 3, 4, 5),
        (1, 2, 3, 4, 5, 5),
        (2, 1, 3, 4, 5, 6),
        (0, 2, 3, 4, 5, 6),
        (1, 2, 3, 4, 5, 50),
        (True, 2, 3, 4, 5, 6),
        (1.0, 2, 3, 4, 5, 6),
        [1, 2, 3, 4, 5, 6],
    ],
)
def test_main_projection_rejects_invalid_numbers_without_sorting_or_coercion(values):
    with pytest.raises(core.OverlapValidationError):
        core.MainDraw(date(2019, 5, 15), values)


@pytest.mark.parametrize("day", ["2019-05-15", datetime(2019, 5, 15, tzinfo=UTC), None])
def test_main_projection_rejects_date_coercion(day):
    with pytest.raises(core.OverlapValidationError):
        core.MainDraw(day, ANCHOR)


def test_bonus_is_not_an_accepted_core_input():
    with pytest.raises(TypeError):
        core.MainDraw(date(2019, 5, 15), ANCHOR, bonus=8)


@pytest.mark.parametrize("factory", [core.forecast_candidate, core.forecast_control])
def test_one_valid_anchor_has_no_pairs_and_exact_fair_forecast(factory):
    rows, target = _rows(ANCHOR)
    f = factory(rows, target)
    assert f.source_draw_date == f.history_through == date(2019, 5, 15)
    assert f.target_date == date(2019, 5, 18)
    assert f.training_pair_count == f.training_overlap_sum == 0
    assert f.beta_hex == "0x0.0p+0"
    assert f.probabilities == tuple((n, 6.0 / 49.0) for n in range(1, 50))
    assert f.probability_hex == tuple((n, "0x1.f58d0fac687d6p-4") for n in range(1, 50))
    assert f.ranking == tuple(range(1, 50))
    assert f.final6 == (1, 2, 3, 4, 5, 6)
    assert f.counts_sha256 == hashlib.sha256(b"[]\n").hexdigest()
    core.validate_forecast(f)


@pytest.mark.parametrize("factory", [core.forecast_candidate, core.forecast_control])
@pytest.mark.parametrize(
    "mutation",
    [
        "none",
        "missing_first",
        "missing_interior",
        "missing_last",
        "duplicate",
        "out_of_order",
        "same_target",
        "future",
        "off_calendar",
    ],
)
def test_prefix_does_not_adopt_target_future_or_missing_rows(factory, mutation):
    rows, target = _rows(ANCHOR, OTHER, ANCHOR)
    if mutation == "none":
        rows = [core.MainDraw(date(2019, 5, 11), ANCHOR)]
    elif mutation == "missing_first":
        rows = rows[1:]
    elif mutation == "missing_interior":
        rows.pop(1)
    elif mutation == "missing_last":
        rows.pop()
    elif mutation == "duplicate":
        rows.insert(1, rows[0])
    elif mutation == "out_of_order":
        rows = rows[::-1]
    elif mutation == "same_target":
        rows.append(core.MainDraw(target, ANCHOR))
    elif mutation == "future":
        rows.append(core.MainDraw(target + timedelta(days=3), ANCHOR))
    else:
        rows[1] = core.MainDraw(date(2019, 5, 17), OTHER)
    with pytest.raises(core.OverlapValidationError):
        factory(rows, target)


@pytest.mark.parametrize("factory", [core.forecast_candidate, core.forecast_control])
@pytest.mark.parametrize(
    "prefix,target",
    [
        ([], date(2019, 5, 18)),
        ((), date(2019, 5, 18)),
        (None, date(2019, 5, 18)),
        ([core.MainDraw(date(2019, 5, 15), ANCHOR)], "2019-05-18"),
        ([core.MainDraw(date(2019, 5, 15), ANCHOR)], date(2019, 5, 19)),
        ([core.MainDraw(date(2019, 5, 15), ANCHOR)], date(2019, 5, 15)),
        ([object()], date(2019, 5, 18)),
    ],
)
def test_forecast_prefix_type_and_target_domains(factory, prefix, target):
    with pytest.raises(core.OverlapValidationError):
        factory(prefix, target)


@pytest.mark.parametrize("factory", [core.forecast_candidate, core.forecast_control])
def test_boundary_and_pre_rng_mutation_are_scientifically_inert(factory):
    rows, target = _rows(ANCHOR, OTHER)
    baseline = factory(rows, target)
    pre_a = [
        core.MainDraw(date(1982, 6, 12), ANCHOR),
        core.MainDraw(date(2019, 5, 11), ANCHOR),
    ]
    pre_b = [
        core.MainDraw(date(1982, 6, 12), OTHER),
        core.MainDraw(date(2019, 5, 11), OTHER),
    ]
    assert factory(pre_a + rows, target) == baseline == factory(pre_b + rows, target)
    assert baseline.training_pair_count == 1
    assert baseline.source_draw_date == date(2019, 5, 18)


def test_source_and_count_hashes_are_date_main_only_canonical_with_lf():
    rows, target = _rows(ANCHOR, OTHER)
    f = core.forecast_candidate(rows, target)
    projection = [
        {"draw_date": "2019-05-15", "numbers": list(ANCHOR)},
        {"draw_date": "2019-05-18", "numbers": list(OTHER)},
    ]
    assert (
        f.scientific_projection_sha256
        == hashlib.sha256(_canonical(projection)).hexdigest()
    )
    assert (
        f.scientific_projection_sha256
        != hashlib.sha256(_canonical(projection)[:-1]).hexdigest()
    )
    assert f.counts_sha256 == hashlib.sha256(b"[0]\n").hexdigest()
    assert f.training_pair_count == 1 and f.training_overlap_sum == 0


def test_fixed_cyclic_map_transforms_only_source_and_uses_own_counts():
    source = (1, 2, 3, 4, 5, 49)
    destination = (1, 6, 7, 8, 9, 10)
    rows, target = _rows(source, destination)
    candidate = core.forecast_candidate(rows, target)
    control = core.forecast_control(rows, target)
    assert core.CYCLIC_MAP == (*range(2, 50), 1)
    assert (
        hashlib.sha256(_canonical(list(core.CYCLIC_MAP))).hexdigest()
        == core.CYCLIC_MAP_SHA256
    )
    assert (
        core.CYCLIC_MAP_SHA256
        == "6db8d037c252c737f8e3091d4961e677345cb5eee0a6cf11709b06600d557ad6"
    )
    assert candidate.source_anchor == control.source_anchor == destination
    assert candidate.transformed_anchor is None
    assert control.transformed_anchor == (2, 7, 8, 9, 10, 11)
    assert candidate.training_overlap_sum == 1
    assert control.training_overlap_sum == 2
    assert candidate.counts_sha256 == hashlib.sha256(b"[1]\n").hexdigest()
    assert control.counts_sha256 == hashlib.sha256(b"[2]\n").hexdigest()
    assert (
        candidate.scientific_projection_sha256 == control.scientific_projection_sha256
    )
    assert candidate.beta != control.beta


@pytest.mark.parametrize(
    "source,sign,final6", [(ANCHOR, 1, ANCHOR), (OTHER, -1, OTHER)]
)
def test_literal_positive_and_negative_candidate_final6(source, sign, final6):
    rows, target = _rows(source, ANCHOR)
    f = core.forecast_candidate(rows, target)
    assert (f.beta > 0.0) == (sign > 0)
    assert f.final6 == final6
    probabilities = dict(f.probabilities)
    assert len({probabilities[n] for n in ANCHOR}) == 1
    assert len({probabilities[n] for n in range(1, 50) if n not in ANCHOR}) == 1
    assert len(set(probabilities.values())) == 2
    assert f.ranking == tuple(
        sorted(range(1, 50), key=lambda n: (-probabilities[n], n))
    )
    assert f.top6 == f.ranking[:6]
    assert f.top12 == f.ranking[:12]
    assert f.top18 == f.ranking[:18]
    assert f.final6 == tuple(sorted(f.top6))


def test_eligible_prior_main_mutation_changes_fit_and_each_call_refits(monkeypatch):
    rows, target = _rows(ANCHOR, ANCHOR)
    calls = []
    real = core.solve_map_beta

    def tracked(counts):
        calls.append(counts)
        return real(counts)

    monkeypatch.setattr(core, "solve_map_beta", tracked)
    original = core.forecast_candidate(rows, target)
    rows[0] = core.MainDraw(rows[0].draw_date, OTHER)
    changed = core.forecast_candidate(rows, target)
    again = core.forecast_candidate(rows, target)
    assert calls == [(6,), (0,), (0,)]
    assert original.beta > 0 > changed.beta
    assert changed == again
    assert original.source_anchor == changed.source_anchor
    assert original.scientific_projection_sha256 != changed.scientific_projection_sha256


def test_future_mutation_is_inert_at_strict_prefix_caller_boundary():
    rows, target = _rows(ANCHOR, ANCHOR)
    target_row = core.MainDraw(target, OTHER)
    future = core.MainDraw(target + timedelta(days=3), OTHER)
    all_rows = [*rows, target_row, future]

    def caller_projection(records):
        return tuple(row for row in records if row.draw_date < target)

    first = core.forecast_candidate(caller_projection(all_rows), target)
    changed = [
        *rows,
        core.MainDraw(target, ANCHOR),
        core.MainDraw(future.draw_date, ANCHOR),
    ]
    second = core.forecast_candidate(caller_projection(changed), target)
    assert first == second
    with pytest.raises(core.OverlapValidationError):
        core.forecast_candidate(all_rows, target)


def test_relabeling_equivariance_is_for_probabilities_not_tie_order():
    rows, target = _rows(ANCHOR, OTHER, OTHER)
    relabel = lambda n: 1 + ((n + 6) % 49)
    mapped = [
        core.MainDraw(row.draw_date, tuple(sorted(relabel(n) for n in row.numbers)))
        for row in rows
    ]
    original = core.forecast_candidate(rows, target)
    changed = core.forecast_candidate(mapped, target)
    assert original.beta_hex == changed.beta_hex
    assert original.counts_sha256 == changed.counts_sha256
    p, q = dict(original.probabilities), dict(changed.probabilities)
    assert all(p[n] == q[relabel(n)] for n in range(1, 50))
    assert tuple(relabel(n) for n in original.ranking) != changed.ranking


def test_issued_forecast_ordinary_mutation_reconstruction_and_subclass_are_rejected():
    rows, target = _rows(ANCHOR)
    f = core.forecast_candidate(rows, target)
    with pytest.raises(dataclasses.FrozenInstanceError):
        f.beta = 1.0
    with pytest.raises(TypeError):
        core.OverlapForecast()
    with pytest.raises(TypeError):
        dataclasses.replace(f, beta=1.0)
    with pytest.raises(TypeError):
        type("Forged", (core.OverlapForecast,), {})
    with pytest.raises(core.OverlapValidationError):
        core.validate_forecast(object.__new__(core.OverlapForecast))


@pytest.mark.parametrize(
    "field,value",
    [
        ("model_name", "unregistered"),
        ("model_version", "v13.0.1"),
        ("feature_set", "changed"),
        ("target_date", date(2019, 5, 25)),
        ("history_through", date(2019, 5, 11)),
        ("source_draw_date", date(2019, 5, 18)),
        ("source_anchor", OTHER),
        ("transformed_anchor", ANCHOR),
        ("training_pair_count", True),
        ("training_pair_count", 1),
        ("training_overlap_sum", 1),
        ("scientific_projection_sha256", "g" * 64),
        ("counts_sha256", "0" * 63),
        ("beta", -0.0),
        ("beta", 0),
        ("beta", True),
        ("beta", float("nan")),
        ("beta_hex", "0x0p+0"),
        ("mean", 0),
        ("mean_hex", "wrong"),
        ("complement_mean", 6.0),
        ("complement_mean_hex", "wrong"),
        ("log_z", 0.0),
        ("log_z_hex", "wrong"),
        ("probabilities", ()),
        ("probability_hex", ()),
        ("ranking", tuple(range(49, 0, -1))),
        ("top6", (True, 2, 3, 4, 5, 6)),
        ("top12", ()),
        ("top18", ()),
        ("final6", OTHER),
    ],
)
def test_forecast_validation_rejects_tampered_fields(field, value):
    # A nonfair forecast binds the anchor through its marginal groups; fair law
    # cannot reconstruct the source anchor from probabilities alone.
    rows, target = _rows(ANCHOR, ANCHOR) if field == "source_anchor" else _rows(ANCHOR)
    f = core.forecast_candidate(rows, target)
    object.__setattr__(f, field, value)
    with pytest.raises(core.OverlapValidationError):
        core.validate_forecast(f)


@pytest.mark.parametrize("field", ["probabilities", "probability_hex"])
def test_probability_labels_cannot_use_bool_aliases(field):
    rows, target = _rows(ANCHOR)
    f = core.forecast_candidate(rows, target)
    values = list(getattr(f, field))
    values[0] = (True, values[0][1])
    object.__setattr__(f, field, tuple(values))
    with pytest.raises(core.OverlapValidationError):
        core.validate_forecast(f)


def test_frozen_validation_never_refits(monkeypatch):
    rows, target = _rows(OTHER, ANCHOR)
    f = core.forecast_candidate(rows, target)

    def forbidden(*args):
        raise AssertionError("frozen validation cannot refit")

    monkeypatch.setattr(core, "solve_map_beta", forbidden)
    monkeypatch.setattr(core, "_prefix", forbidden)
    core.validate_forecast(f)


def test_core_is_static_stdlib_only_with_hard_terminal_checks():
    tree = ast.parse(inspect.getsource(core))
    assert not any(isinstance(node, ast.Assert) for node in ast.walk(tree))
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(item.name for item in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in {
                "eval",
                "exec",
                "compile",
                "__import__",
                "getattr",
                "setattr",
            }
    assert set(imports) == {
        "__future__",
        "hashlib",
        "json",
        "math",
        "dataclasses",
        "datetime",
        "itertools",
        "typing",
    }


@pytest.mark.parametrize(
    "source,destination,sign",
    [
        ((3, 10, 18, 26, 37, 48), ANCHOR, 1),
        ((1, 2, 4, 5, 7, 8), ANCHOR, -1),
    ],
)
def test_control_ranking_uses_transformed_current_anchor_and_exact_ties(
    source, destination, sign
):
    rows, target = _rows(source, destination)
    f = core.forecast_control(rows, target)
    transformed = (1, 5, 12, 20, 28, 39)
    assert f.transformed_anchor == transformed
    assert (f.beta > 0.0) == (sign > 0)
    assert f.final6 == (transformed if sign > 0 else (2, 3, 4, 6, 7, 8))
    p = dict(f.probabilities)
    assert f.ranking == tuple(sorted(range(1, 50), key=lambda n: (-p[n], n)))
    assert (
        f.top6 == f.ranking[:6]
        and f.top12 == f.ranking[:12]
        and f.top18 == f.ranking[:18]
    )
    assert f.final6 == tuple(sorted(f.top6))
    assert {p[n] for n in transformed} == {f.mean / 6.0}
    assert {p[n] for n in range(1, 50) if n not in transformed} == {
        f.complement_mean / 43.0
    }


def test_count_digest_preserves_pair_order_not_only_sufficient_statistics():
    first_rows, target = _rows(OTHER, ANCHOR, ANCHOR)
    second_rows, second_target = _rows(OTHER, OTHER, ANCHOR)
    first = core.forecast_candidate(first_rows, target)
    second = core.forecast_candidate(second_rows, second_target)
    assert first.training_pair_count == second.training_pair_count == 2
    assert first.training_overlap_sum == second.training_overlap_sum == 6
    assert first.beta_hex == second.beta_hex
    assert first.source_anchor == second.source_anchor
    assert first.counts_sha256 == hashlib.sha256(b"[0,6]\n").hexdigest()
    assert second.counts_sha256 == hashlib.sha256(b"[6,0]\n").hexdigest()
    assert first.counts_sha256 != second.counts_sha256


@pytest.mark.parametrize("value", [None, ANCHOR, (True, 5, 12, 20, 28, 39)])
def test_control_forecast_rejects_invalid_transformed_anchor(value):
    rows, target = _rows(ANCHOR)
    f = core.forecast_control(rows, target)
    object.__setattr__(f, "transformed_anchor", value)
    with pytest.raises(core.OverlapValidationError):
        core.validate_forecast(f)


@pytest.mark.parametrize("value", [True, 1, 0.0, 1.0, float("nan"), float("inf")])
def test_final_marginal_values_are_strict_float_finite_open_interval(value):
    rows, target = _rows(ANCHOR)
    f = core.forecast_candidate(rows, target)
    probabilities = list(f.probabilities)
    probabilities[0] = (1, value)
    object.__setattr__(f, "probabilities", tuple(probabilities))
    with pytest.raises(core.OverlapValidationError):
        core.validate_forecast(f)


def test_validator_cannot_treat_algebraically_recomputed_complement_as_identical():
    rows, target = _rows(ANCHOR, ANCHOR)
    f = core.forecast_candidate(rows, target)
    assert f.complement_mean.hex() == "0x1.5edc3208f513ap+1"
    substituted = 6.0 - f.mean
    assert substituted.hex() != f.complement_mean_hex
    object.__setattr__(f, "complement_mean", substituted)
    object.__setattr__(f, "complement_mean_hex", substituted.hex())
    with pytest.raises(core.OverlapValidationError):
        core.validate_forecast(f)
