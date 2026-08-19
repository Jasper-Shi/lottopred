from __future__ import annotations

from datetime import date, timedelta
from hashlib import sha256
from itertools import combinations
import json
import math
import os
from pathlib import Path
import subprocess
import sys

import pytest

from lotto649.domain import Draw
from lotto649.models.base import ProbabilityModel
import lotto649.models.v10_adjacent_pair_structure as v10
from lotto649.models.v10_adjacent_pair_structure import (
    V10AdjacencyLabelBijectionControlModel,
    V10AdjacentPairStructureModel,
    V10Forecast,
    forecast_v10,
    joint_log_gain,
    preflight_v10_model,
)


CANDIDATE = "v10_adjacent_pair_structure"
CONTROL = "v10_adjacency_label_bijection_control"
TARGET = date(2020, 1, 11)
ROOT = Path(__file__).resolve().parents[1]


def _history() -> list[Draw]:
    return [
        Draw(date(2020, 1, 1), (1, 2, 10, 20, 30, 40), 49),
        Draw(date(2020, 1, 4), (3, 9, 15, 21, 27, 33), 49),
        Draw(date(2020, 1, 8), (5, 6, 7, 20, 35, 49), 48),
    ]


def _map_draw(draw: Draw) -> Draw:
    return Draw(
        draw.draw_date,
        tuple(v10.CONTROL_DESTINATIONS[number - 1] for number in draw.numbers),
    )


def _brute_force_forced_table(n: int, k: int) -> tuple[tuple[int, ...], ...]:
    rows: list[tuple[int, ...]] = []
    for forced_label in range(1, n + 1):
        counts = [0] * k
        for selected in combinations(range(1, n + 1), k):
            if forced_label not in selected:
                continue
            adjacency = sum(
                right - left == 1
                for left, right in zip(selected, selected[1:])
            )
            counts[adjacency] += 1
        rows.append(tuple(counts))
    return tuple(rows)


def _assert_probability_contract(forecast: V10Forecast) -> None:
    assert len(forecast.probabilities) == 49
    assert all(math.isfinite(value) for value in forecast.probabilities)
    assert all(0.0 < value < 1.0 for value in forecast.probabilities)
    assert math.fsum(forecast.probabilities) == pytest.approx(
        6.0,
        rel=0.0,
        abs=1.0e-12,
    )
    assert forecast.ranking == tuple(
        sorted(
            range(1, 50),
            key=lambda number: (-forecast.probabilities[number - 1], number),
        )
    )
    assert forecast.top6 == forecast.ranking[:6]
    assert forecast.top12 == forecast.ranking[:12]
    assert forecast.top18 == forecast.ranking[:18]
    assert forecast.final6 == tuple(sorted(forecast.top6))


def test_v10_preflight_locks_registered_counts_dp_map_and_numeric_oracles():
    assert preflight_v10_model() is None
    assert preflight_v10_model() is None

    assert v10.FAIR_CATEGORY_COUNTS == (
        7_059_052,
        5_430_040,
        1_357_510,
        132_440,
        4_730,
        44,
    )
    assert sum(v10.FAIR_CATEGORY_COUNTS) == 13_983_816
    assert math.fsum(
        category * count
        for category, count in enumerate(v10.FAIR_CATEGORY_COUNTS)
    ) / 13_983_816 == 30.0 / 49.0

    table = v10._marginal_count_table()
    assert table[0] == (962_598, 617_050, 123_410, 9_030, 215, 1)
    assert table[24] == (860_586, 666_310, 168_146, 16_646, 610, 6)
    assert table[48] == table[0]
    canonical_table = json.dumps(table, separators=(",", ":")).encode()
    assert sha256(canonical_table).hexdigest() == (
        "7d14a90bc388cb0e02dda77ff315a1662492c2cb44f6d5497e297354804d781b"
    )
    for category, count in enumerate(v10.FAIR_CATEGORY_COUNTS):
        assert sum(row[category] for row in table) == 6 * count

    assert v10.CONTROL_DESTINATIONS == (
        3, 11, 2, 14, 41, 45, 22, 39, 1, 40, 31, 37, 29, 12, 30, 6, 7,
        19, 46, 15, 27, 26, 42, 28, 13, 21, 20, 36, 18, 4, 5, 32, 17,
        8, 9, 10, 35, 43, 47, 16, 48, 34, 23, 24, 44, 25, 33, 38, 49,
    )
    assert sorted(v10.CONTROL_DESTINATIONS) == list(range(1, 50))
    assert sha256(v10.CONTROL_MAP_CANONICAL.encode()).hexdigest() == (
        "c533509f258e0bb8bdd9fabac8a017ee689e07af0f1d6daf4d36ee63873c0562"
    )
    assert v10._probabilities_for_theta(-1.3)[0].hex() == (
        "0x1.0e2c39c67edaep-3"
    )


def test_v10_pure_model_preflight_needs_only_the_standard_library():
    command = (
        "from lotto649.models.v10_adjacent_pair_structure "
        "import preflight_v10_model; preflight_v10_model()"
    )
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT / "src")

    completed = subprocess.run(
        [sys.executable, "-S", "-c", command],
        cwd=ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr


def test_v10_dp_recurrence_matches_a_complete_small_space_oracle():
    assert v10._build_marginal_count_table(6, 2) == (
        (4, 1),
        (3, 2),
        (3, 2),
        (3, 2),
        (3, 2),
        (4, 1),
    )
    assert v10._build_marginal_count_table(8, 3) == (
        _brute_force_forced_table(8, 3)
    )


@pytest.mark.parametrize(
    ("numbers", "expected"),
    [
        ((1, 3, 5, 7, 9, 11), 0),
        ((1, 2, 4, 8, 16, 32), 1),
        ((1, 2, 3, 8, 9, 20), 3),
        ((1, 2, 3, 4, 5, 6), 5),
        ((1, 10, 20, 30, 40, 49), 0),
    ],
)
def test_v10_adjacency_is_sorted_gap_one_without_wrap(numbers, expected):
    assert v10._adjacency_count(numbers) == expected


def test_v10_binary64_moment_solver_and_probability_contract_are_literal():
    history = [
        Draw(date(2020, 1, 1), (1, 2, 10, 20, 30, 40), 49),
        Draw(date(2020, 1, 4), (3, 4, 9, 15, 21, 27), 49),
    ]

    forecast = forecast_v10(history, date(2020, 1, 8), CANDIDATE)

    assert forecast.model_version == "v10.0.0"
    assert forecast.history_draws == 2
    assert forecast.history_through == date(2020, 1, 4)
    assert forecast.sum_a == 2
    assert forecast.moment_numerator == 128
    assert forecast.moment_denominator == 147
    assert forecast.moment_binary64.hex() == "0x1.bdd2b899406f7p-1"
    assert forecast.theta.hex() == "0x1.d4c61abbdd33cp-2"
    assert math.isfinite(forecast.log_z)
    _assert_probability_contract(forecast)
    for number in range(1, 50):
        assert (
            forecast.probabilities[number - 1]
            == forecast.probabilities[49 - number]
        )


def test_v10_solver_rejects_a_moment_on_either_frozen_bracket_boundary():
    boundary_moments = (
        v10._partition(v10.BISECTION_LOWER).moment,
        v10._partition(v10.BISECTION_UPPER).moment,
    )

    for boundary_moment in boundary_moments:
        with pytest.raises(RuntimeError, match="not strictly bracketed"):
            v10._solve_theta(boundary_moment)


def test_v10_solver_locks_iterations_equality_branch_and_final_midpoint(
    monkeypatch: pytest.MonkeyPatch,
):
    partition_calls: list[float] = []

    def identity_partition(theta: float) -> v10._Partition:
        partition_calls.append(theta)
        return v10._Partition(
            log_z=theta,
            moment=theta,
            ell_max=theta,
            scaled_sum=1.0,
        )

    monkeypatch.setattr(v10, "_partition", identity_partition)

    theta, final_partition = v10._solve_theta(0.0)

    assert len(partition_calls) == 2 + 256 + 1
    assert partition_calls[:4] == [-64.0, 64.0, 0.0, -32.0]
    assert partition_calls[-2].hex() == "-0x1.0000000000000p-249"
    assert theta.hex() == "-0x1.0000000000000p-250"
    assert partition_calls[-1] == theta
    assert final_partition.moment == theta


def test_v10_empty_prefix_is_the_registered_exact_fair_bypass():
    forecast = forecast_v10([], TARGET, CANDIDATE)

    assert forecast.history_draws == 0
    assert forecast.history_through is None
    assert forecast.sum_a == 0
    assert forecast.moment_numerator == 30
    assert forecast.moment_denominator == 49
    assert forecast.moment_binary64 == 30.0 / 49.0
    assert forecast.theta.hex() == "0x0.0p+0"
    assert forecast.log_z.hex() == "0x1.07412c1f4cc68p+4"
    assert forecast.probabilities == (6.0 / 49.0,) * 49
    assert forecast.ranking == tuple(range(1, 50))
    assert forecast.final6 == (1, 2, 3, 4, 5, 6)
    assert joint_log_gain(forecast, (1, 2, 3, 4, 5, 6)).hex() == (
        "0x0.0p+0"
    )
    _assert_probability_contract(forecast)


def test_v10_targeted_control_is_exactly_the_same_engine_in_permuted_space():
    history = _history()
    transformed = [_map_draw(draw) for draw in history]

    candidate_in_permuted_space = forecast_v10(transformed, TARGET, CANDIDATE)
    control = forecast_v10(history, TARGET, CONTROL)

    assert control.sum_a == candidate_in_permuted_space.sum_a
    assert control.moment_numerator == candidate_in_permuted_space.moment_numerator
    assert control.moment_denominator == candidate_in_permuted_space.moment_denominator
    assert control.moment_binary64 == candidate_in_permuted_space.moment_binary64
    assert control.theta == candidate_in_permuted_space.theta
    assert control.log_z == candidate_in_permuted_space.log_z
    for source_label, destination_label in enumerate(
        v10.CONTROL_DESTINATIONS,
        start=1,
    ):
        assert control.probabilities[source_label - 1] == (
            candidate_in_permuted_space.probabilities[destination_label - 1]
        )
    _assert_probability_contract(control)


def test_v10_joint_gain_uses_candidate_or_permuted_control_adjacency_exactly():
    history = _history()
    actual = (1, 2, 10, 20, 30, 40)
    candidate = forecast_v10(history, TARGET, CANDIDATE)
    control = forecast_v10(history, TARGET, CONTROL)

    candidate_expected = candidate.theta * 1
    candidate_expected -= candidate.log_z
    candidate_expected += math.log(13_983_816)
    mapped_actual = tuple(
        sorted(v10.CONTROL_DESTINATIONS[number - 1] for number in actual)
    )
    control_expected = control.theta * v10._adjacency_count(mapped_actual)
    control_expected -= control.log_z
    control_expected += math.log(13_983_816)

    assert joint_log_gain(candidate, actual) == candidate_expected
    assert joint_log_gain(control, actual) == control_expected


def test_v10_forecast_is_bonus_blind_deterministic_and_payload_has_no_reveal_data():
    history = _history()
    bonus_changed = [
        Draw(
            draw.draw_date,
            draw.numbers,
            next(number for number in range(1, 50) if number not in draw.numbers),
        )
        for draw in history
    ]

    for model_name in (CANDIDATE, CONTROL):
        first = forecast_v10(history, TARGET, model_name)
        repeated = forecast_v10(history, TARGET, model_name)
        altered_bonus = forecast_v10(bonus_changed, TARGET, model_name)

        assert first == repeated == altered_bonus
        assert first.canonical_payload_bytes() == repeated.canonical_payload_bytes()
        assert first.canonical_payload_bytes() == (
            altered_bonus.canonical_payload_bytes()
        )
        payload = first.canonical_payload()
        assert payload["target_date"] == TARGET.isoformat()
        assert payload["history_through"] == history[-1].draw_date.isoformat()
        assert set(payload["probabilities"]) == {
            str(number) for number in range(1, 50)
        }
        assert "timestamp" not in first.canonical_payload_bytes().decode().lower()
        assert "actual" not in payload
        assert "bonus" not in payload
        assert json.loads(first.canonical_payload_bytes()) == payload


def test_v10_earlier_prefix_replays_identically_after_a_later_forecast():
    history = _history()
    old_history = history[:2]
    old_target = history[2].draw_date

    for model_name in (CANDIDATE, CONTROL):
        before = forecast_v10(old_history, old_target, model_name)
        forecast_v10(history, TARGET, model_name)
        after = forecast_v10(old_history, old_target, model_name)

        assert after == before
        assert after.canonical_payload_bytes() == before.canonical_payload_bytes()


def test_v10_candidate_and_control_adapters_are_thin_probability_models():
    history = _history()
    adapters = (
        (V10AdjacentPairStructureModel(), CANDIDATE),
        (V10AdjacencyLabelBijectionControlModel(), CONTROL),
    )

    for model, model_name in adapters:
        assert isinstance(model, ProbabilityModel)
        assert model.name == model_name
        forecast = forecast_v10(history, TARGET, model_name)
        assert model.predict(history, TARGET) == {
            number: forecast.probabilities[number - 1]
            for number in range(1, 50)
        }


def test_v10_rejects_chronology_model_and_revealed_set_contract_violations():
    history = _history()
    duplicate_date = [history[0], Draw(history[0].draw_date, history[1].numbers)]

    with pytest.raises(ValueError, match="chronological"):
        forecast_v10([history[1], history[0]], TARGET, CANDIDATE)
    with pytest.raises(ValueError, match="unique"):
        forecast_v10(duplicate_date, TARGET, CANDIDATE)
    with pytest.raises(ValueError, match="strictly before"):
        forecast_v10(history, history[-1].draw_date, CANDIDATE)
    with pytest.raises(ValueError, match="model_name"):
        forecast_v10(history, TARGET, "v10_rescue_variant")

    forecast = forecast_v10(history, TARGET, CANDIDATE)
    with pytest.raises(ValueError, match="six distinct"):
        joint_log_gain(forecast, (1, 1, 2, 3, 4, 5))
    with pytest.raises(ValueError, match="1..49"):
        joint_log_gain(forecast, (0, 1, 2, 3, 4, 5))


def test_v10_changing_a_strictly_prior_main_set_changes_both_forecasts():
    history = _history()
    altered = [
        history[0],
        Draw(history[1].draw_date, (3, 4, 5, 6, 7, 8), history[1].bonus),
        history[2],
    ]

    for model_name in (CANDIDATE, CONTROL):
        assert forecast_v10(history, TARGET, model_name) != forecast_v10(
            altered,
            TARGET,
            model_name,
        )


def test_v10_model_does_not_depend_on_target_date_spacing_or_wall_clock():
    history = _history()
    later_target = TARGET + timedelta(days=100)

    first = forecast_v10(history, TARGET, CANDIDATE)
    later = forecast_v10(history, later_target, CANDIDATE)

    assert first.probabilities == later.probabilities
    assert first.ranking == later.ranking
    assert first.target_date != later.target_date
