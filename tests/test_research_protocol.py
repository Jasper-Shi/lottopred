from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path

import pytest

from lotto649.data import load_draws
from lotto649.domain import Draw
from lotto649.research_protocol import (
    ProspectiveCohortSpec,
    assert_history_precedes_target,
    assess_prospective_snapshot,
    draws_fingerprint,
    load_experiment_registry,
    permute_draw_outcomes,
    snapshot_digest,
    validated_registered_draw_prefix,
    walk_forward_folds,
)


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "docs" / "experiments" / "registry.yaml"


def synthetic_draws(count: int = 12) -> list[Draw]:
    draws = []
    first = date(2014, 1, 1)
    for index in range(count):
        values = tuple(sorted((((index * 7) + offset * 8) % 49) + 1 for offset in range(6)))
        bonus = next(number for number in range(1, 50) if number not in values)
        draws.append(Draw(first + timedelta(days=index * 3), values, bonus))
    return draws


def test_committed_registry_is_fixed_and_matches_registration_dataset():
    registry = load_experiment_registry(REGISTRY_PATH)
    registration = registry.get("V5_pair_affinity")

    assert registration.status == "closed_rejected"
    assert registration.model_name == "v5_pair_affinity"
    assert registration.model_version == "v5.0.0"
    assert registration.primary_metric == "top12_hits_lift_vs_theory"
    assert registration.outcomes_known_through == date(2026, 8, 15)
    assert registration.outcomes_known_source_commit == (
        "90177c80cfb070038d79508fb2e73305a297f516"
    )
    assert registration.outcomes_known_draw_count == 4432
    assert registration.outcomes_known_sha256 == (
        "edfb7f8a4a7711a630957d6f86b567e6b254caf7b1d1aaea0edf1d16a34155b3"
    )
    assert registration.prospective.status == "not_activated"
    assert registration.prospective.minimum_eligible_draws == 104
    assert registration.result is not None
    assert registration.result.decision == "reject"
    assert registration.result.implementation_commit == (
        "f51a3b59e857f6c3a5d9c0502a0c30e71d15d3b4"
    )
    assert registration.result.historical_primary_signal_supported is False
    assert registration.result.shadow_activation == "not_activated"
    for result_path in (
        registration.result.report_json,
        registration.result.report_markdown,
        registration.result.result_file,
    ):
        assert (ROOT / result_path).is_file()

    dataset_path = ROOT / registration.dataset_path
    draws = load_draws(dataset_path)
    prefix = validated_registered_draw_prefix(
        dataset_path,
        draws,
        expected_sha256=registration.dataset_sha256,
        draw_count=registration.dataset_draw_count,
        history_through=registration.registration_history_through,
    )

    assert len(prefix) == registration.dataset_draw_count
    assert prefix[-1].draw_date == registration.registration_history_through
    assert draws[-1].draw_date >= registration.registration_history_through


def test_v6_registration_freezes_one_entropy_regime_variant_before_scoring():
    registration = load_experiment_registry(REGISTRY_PATH).get(
        "V6_fixed_boundary_js_regime"
    )

    assert registration.status == "registered"
    assert registration.family == "entropy_regime"
    assert registration.model_name == "v6_entropy_regime"
    assert registration.model_version == "v6.0.0"
    assert registration.primary_metric == "top12_hits_lift_vs_theory"
    assert registration.multiplicity_family == "entropy_regime"
    assert registration.variant_index == 1
    assert registration.result is None
    assert registration.registration_history_through == date(2026, 8, 12)
    assert registration.outcomes_known_through == date(2026, 8, 15)
    assert registration.parameters == {
        "minimum_history_draws": 300,
        "feature_window_draws": 208,
        "older_block_draws": 104,
        "recent_block_draws": 104,
        "main_numbers_per_draw": 6,
        "finite_population_numerator": 48,
        "finite_population_denominator": 43,
        "chi_square_degrees_of_freedom": 48,
        "gate_quantile": 0.99,
        "regime_threshold": 73.68263852010577,
        "threshold_operator": "strictly_greater_than",
        "zscore_population_epsilon": 1.0e-12,
        "signal_temperature": 0.10,
        "jitter_rng": "numpy.default_rng",
        "jitter_seed_base": 649000000,
        "jitter_low": -1.0e-9,
        "jitter_high": 1.0e-9,
        "bonus_numbers": "excluded",
        "calibration": "none",
        "combination_constraints": "none",
        "historical_primary_gate_lane": "consumed_diagnostic",
        "proper_score_max_delta_vs_fair": 1.0e-9,
        "reference_report": "reports/v5_pair_affinity_v5.0.0_historical.json",
    }
    assert registration.negative_controls[0].kind == "whole_draw_date_permutation"
    assert registration.negative_controls[0].seed == 649
    assert registration.prospective.status == "not_activated"
    assert registration.prospective.minimum_eligible_draws == 208
    assert (ROOT / registration.registration_file).is_file()


def test_known_outcome_boundary_cannot_hide_consumed_or_future_draws():
    registration = load_experiment_registry(REGISTRY_PATH).get(
        "V6_fixed_boundary_js_regime"
    )

    with pytest.raises(ValueError, match="cannot end before"):
        replace(
            registration,
            outcomes_known_through=date(2026, 8, 11),
        )
    with pytest.raises(ValueError, match="cannot precede"):
        replace(
            registration,
            outcomes_known_draw_count=4430,
        )
    with pytest.raises(ValueError, match="beyond registration"):
        replace(
            registration,
            outcomes_known_through=date(2026, 8, 17),
        )


def _csv_bytes(draws: list[Draw]) -> bytes:
    lines = ["draw_date,n1,n2,n3,n4,n5,n6,bonus\n"]
    for draw in draws:
        values = ",".join(str(number) for number in draw.numbers)
        lines.append(f"{draw.draw_date.isoformat()},{values},{draw.bonus}\n")
    return "".join(lines).encode()


def test_registered_draw_prefix_allows_only_strict_appends(tmp_path):
    draws = synthetic_draws(6)
    registered_bytes = _csv_bytes(draws[:4])
    dataset_path = tmp_path / "draws.csv"
    dataset_path.write_bytes(registered_bytes + _csv_bytes(draws[4:]).split(b"\n", 1)[1])

    prefix = validated_registered_draw_prefix(
        dataset_path,
        draws,
        expected_sha256=sha256(registered_bytes).hexdigest(),
        draw_count=4,
        history_through=draws[3].draw_date,
    )

    assert prefix == tuple(draws[:4])


@pytest.mark.parametrize("failure", ["truncated", "rewritten", "unordered"])
def test_registered_draw_prefix_rejects_non_append_changes(tmp_path, failure):
    draws = synthetic_draws(6)
    registered_bytes = _csv_bytes(draws[:4])
    expected_sha256 = sha256(registered_bytes).hexdigest()
    dataset_path = tmp_path / "draws.csv"
    candidate_draws = draws

    if failure == "truncated":
        dataset_path.write_bytes(_csv_bytes(draws[:3]))
        candidate_draws = draws[:3]
    elif failure == "rewritten":
        rewritten = registered_bytes.replace(b",1,9,17,25,33,41,2\n", b",1,9,17,25,33,40,2\n")
        dataset_path.write_bytes(rewritten + _csv_bytes(draws[4:]).split(b"\n", 1)[1])
    else:
        dataset_path.write_bytes(registered_bytes + _csv_bytes(draws[4:]).split(b"\n", 1)[1])
        candidate_draws = [*draws[:4], draws[5], draws[4]]

    with pytest.raises((RuntimeError, ValueError)):
        validated_registered_draw_prefix(
            dataset_path,
            candidate_draws,
            expected_sha256=expected_sha256,
            draw_count=4,
            history_through=draws[3].draw_date,
        )


def test_registered_draw_prefix_rejects_wrong_history_boundary(tmp_path):
    draws = synthetic_draws(5)
    registered_bytes = _csv_bytes(draws[:4])
    dataset_path = tmp_path / "draws.csv"
    dataset_path.write_bytes(registered_bytes)

    with pytest.raises(RuntimeError, match="history boundary mismatch"):
        validated_registered_draw_prefix(
            dataset_path,
            draws[:4],
            expected_sha256=sha256(registered_bytes).hexdigest(),
            draw_count=4,
            history_through=draws[2].draw_date,
        )


def test_leakage_guard_rejects_target_or_future_draws():
    draws = synthetic_draws()
    target_date = draws[5].draw_date

    assert_history_precedes_target(draws[:5], target_date)
    with pytest.raises(ValueError, match="strictly before"):
        assert_history_precedes_target(draws[:6], target_date)


def test_walk_forward_folds_expose_only_strictly_prior_history():
    draws = synthetic_draws()
    folds = list(
        walk_forward_folds(
            draws,
            start=draws[4].draw_date,
            end=draws[7].draw_date,
            minimum_history_draws=3,
        )
    )

    assert [fold.target for fold in folds] == draws[4:8]
    assert all(fold.history[-1].draw_date < fold.target.draw_date for fold in folds)
    assert all(fold.target not in fold.history for fold in folds)


def test_whole_draw_negative_control_is_deterministic_and_preserves_outcomes():
    draws = synthetic_draws()
    first = permute_draw_outcomes(draws, seed=649)
    second = permute_draw_outcomes(draws, seed=649)

    assert first == second
    assert [draw.draw_date for draw in first] == [draw.draw_date for draw in draws]
    assert sorted((draw.numbers, draw.bonus) for draw in first) == sorted(
        (draw.numbers, draw.bonus) for draw in draws
    )
    assert draws_fingerprint(first) == draws_fingerprint(second)
    assert draws_fingerprint(first) != draws_fingerprint(draws)


def test_promotion_minimum_cannot_be_weakened():
    with pytest.raises(ValueError, match="at least 104"):
        ProspectiveCohortSpec(
            status="not_activated",
            role="shadow",
            minimum_eligible_draws=103,
            commit_deadline="before_target_local_date",
            freeze_commit=None,
            cohort_start=None,
        )


def test_prospective_cohort_must_start_after_all_known_outcomes():
    registration = load_experiment_registry(REGISTRY_PATH).get("V5_pair_affinity")
    active = replace(
        registration.prospective,
        status="active",
        freeze_commit="a" * 40,
        cohort_start=registration.outcomes_known_through,
    )

    with pytest.raises(ValueError, match="after all outcomes known"):
        replace(
            registration,
            status="prospective_shadow",
            prospective=active,
            result=None,
        )


def _active_registration():
    registration = load_experiment_registry(REGISTRY_PATH).get("V5_pair_affinity")
    active = replace(
        registration.prospective,
        status="active",
        freeze_commit="a" * 40,
        cohort_start=date(2027, 1, 6),
    )
    return replace(
        registration,
        status="prospective_shadow",
        prospective=active,
        result=None,
    )


def _snapshot() -> dict:
    return {
        "target_draw_date": "2027-01-06",
        "generated_at": "2027-01-03T12:00:00-05:00",
        "model_name": "v5_pair_affinity",
        "model_version": "v5.0.0",
        "probabilities": {str(number): 6 / 49 for number in range(1, 50)},
        "top6": [1, 2, 3, 4, 5, 6],
        "top12": list(range(1, 13)),
        "top18": list(range(1, 19)),
        "final_combination": [1, 2, 3, 4, 5, 6],
        "metadata": {
            "role": "shadow",
            "history_draws": 4470,
            "history_through": "2027-01-02",
        },
    }


def test_unactivated_cohort_cannot_accept_a_snapshot():
    registration = load_experiment_registry(REGISTRY_PATH).get("V5_pair_affinity")
    snapshot = _snapshot()
    assessment = assess_prospective_snapshot(
        registration,
        snapshot,
        first_commit_at=datetime(2027, 1, 4, tzinfo=timezone.utc),
        first_commit_sha="b" * 40,
        recorded_digest=snapshot_digest(snapshot),
    )

    assert not assessment.eligible
    assert "cohort_not_active" in assessment.reasons


def test_active_cohort_accounts_for_pending_and_evaluated_snapshots():
    registration = _active_registration()
    snapshot = _snapshot()
    commit_time = datetime(2027, 1, 4, 17, tzinfo=timezone.utc)
    digest = snapshot_digest(snapshot)

    pending = assess_prospective_snapshot(
        registration,
        snapshot,
        first_commit_at=commit_time,
        first_commit_sha="b" * 40,
        recorded_digest=digest,
    )
    evaluation = {
        "target_draw_date": "2027-01-06",
        "model_name": "v5_pair_affinity",
        "model_version": "v5.0.0",
    }
    evaluated = assess_prospective_snapshot(
        registration,
        snapshot,
        first_commit_at=commit_time,
        first_commit_sha="b" * 40,
        recorded_digest=digest,
        evaluation=evaluation,
    )

    assert pending.status == "eligible_pending"
    assert evaluated.status == "eligible_evaluated"


def test_active_cohort_excludes_late_regenerated_or_changed_snapshots():
    registration = _active_registration()
    snapshot = _snapshot()
    assessment = assess_prospective_snapshot(
        registration,
        snapshot,
        first_commit_at=datetime(2027, 1, 6, 5, tzinfo=timezone.utc),
        first_commit_sha="b" * 40,
        recorded_digest="0" * 64,
        regenerated=True,
    )

    assert assessment.status == "excluded"
    assert "late_snapshot_commit" in assessment.reasons
    assert "snapshot_digest_mismatch" in assessment.reasons
    assert "regenerated_snapshot" in assessment.reasons
