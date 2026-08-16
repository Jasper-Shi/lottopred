from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

import pytest

from lotto649.domain import Draw
from lotto649.research_protocol import (
    ProspectiveCohortSpec,
    assert_history_precedes_target,
    assess_prospective_snapshot,
    draws_fingerprint,
    file_sha256,
    load_experiment_registry,
    permute_draw_outcomes,
    snapshot_digest,
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

    assert registration.status == "registered"
    assert registration.model_name == "v5_pair_affinity"
    assert registration.model_version == "v5.0.0"
    assert registration.primary_metric == "top12_hits_lift_vs_theory"
    assert registration.prospective.status == "not_activated"
    assert registration.prospective.minimum_eligible_draws == 104

    dataset_path = ROOT / registration.dataset_path
    current = pd.read_csv(dataset_path)
    current_through = date.fromisoformat(str(current.iloc[-1]["draw_date"]))
    if current_through == registration.registration_history_through:
        assert file_sha256(dataset_path) == registration.dataset_sha256
        assert len(current) == registration.dataset_draw_count
    else:
        assert current_through > registration.registration_history_through


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


def _active_registration():
    registration = load_experiment_registry(REGISTRY_PATH).get("V5_pair_affinity")
    active = replace(
        registration.prospective,
        status="active",
        freeze_commit="a" * 40,
        cohort_start=date(2027, 1, 6),
    )
    return replace(registration, status="prospective_shadow", prospective=active)


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
