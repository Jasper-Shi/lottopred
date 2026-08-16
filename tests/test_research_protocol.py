from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
import json
import math
import os
import subprocess

import pytest
import yaml

from lotto649.data import load_draws
from lotto649.domain import Draw
from lotto649.research_protocol import (
    GitEvidenceError,
    GitFileEvidence,
    CohortAssessment,
    FormalLookRecord,
    OutcomeBoundary,
    ProspectiveCohortSpec,
    VerifiedOutcomeBoundary,
    assert_history_precedes_target,
    assess_prospective_snapshot,
    aggregate_prospective_cohort,
    draw_digest,
    draws_fingerprint,
    file_sha256,
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


def test_v6_registry_preserves_frozen_variant_and_rejected_result():
    registry = load_experiment_registry(REGISTRY_PATH)
    registration = registry.get(
        "V6_fixed_boundary_js_regime"
    )

    assert registry.schema_version == 2
    assert registration.status == "closed_rejected"
    assert registration.family == "entropy_regime"
    assert registration.model_name == "v6_entropy_regime"
    assert registration.model_version == "v6.0.0"
    assert registration.primary_metric == "top12_hits_lift_vs_theory"
    assert registration.multiplicity_family == "entropy_regime"
    assert registration.variant_index == 1
    assert registration.result is not None
    assert registration.result.decision == "reject"
    assert registration.result.implementation_commit == (
        "591b6173aa3a2e711d2c5e5e7f9cc3f8c7801bf6"
    )
    assert registration.result.historical_primary_signal_supported is False
    assert registration.result.shadow_activation == "not_activated"
    for result_path in (
        registration.result.report_json,
        registration.result.report_markdown,
        registration.result.result_file,
    ):
        assert (ROOT / result_path).is_file()
    assert file_sha256(ROOT / registration.result.report_json) == (
        "12400a4b5164b030225827d47a8024a1ec7aeaeb32fa64cd2fab0b46ff8d4c2a"
    )
    assert file_sha256(ROOT / registration.result.report_markdown) == (
        "cd842403041a166a3996ab982a987a3871a7039aaf4d600f73b9c6e4dc4aec80"
    )
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
        "reference_report_sha256": (
            "b86391ada265d96f94e789f4962812d32771385702e2efa2285cb9ef96d5d6bb"
        ),
    }
    assert registration.negative_controls[0].kind == "whole_draw_date_permutation"
    assert registration.negative_controls[0].seed == 649
    assert registration.prospective.status == "not_activated"
    assert registration.prospective.minimum_eligible_draws == 208
    assert (ROOT / registration.registration_file).is_file()
    assert file_sha256(ROOT / registration.parameters["reference_report"]) == (
        registration.parameters["reference_report_sha256"]
    )


def _unsealed_v6_candidate():
    closed = load_experiment_registry(REGISTRY_PATH).get(
        "V6_fixed_boundary_js_regime"
    )
    return replace(
        closed,
        experiment_id="V6_protocol_fixture",
        status="registered",
        result=None,
        _terminal_result_lock=None,
        _cohort_activation_lock=None,
    )


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
            activation_commit=None,
            outcomes_known_at_activation=None,
            cohort_start=None,
        )


def test_prospective_activation_requires_a_complete_new_outcome_boundary():
    registration = load_experiment_registry(REGISTRY_PATH).get(
        "V6_fixed_boundary_js_regime"
    )
    cohort = registration.prospective

    assert cohort.activation_commit is None
    assert cohort.outcomes_known_at_activation is None

    with pytest.raises(ValueError, match="requires a freeze commit"):
        replace(cohort, status="active", cohort_start=date(2026, 8, 19))

    activation_boundary = OutcomeBoundary(
        source_commit="b" * 40,
        sha256="c" * 64,
        draw_count=4432,
        history_through=date(2026, 8, 15),
    )
    active = replace(
        cohort,
        status="active",
        freeze_commit="a" * 40,
        activation_commit="d" * 40,
        outcomes_known_at_activation=activation_boundary,
        cohort_start=date(2026, 8, 19),
    )

    assert active.outcomes_known_at_activation == activation_boundary


def test_activation_boundary_cannot_precede_registration_known_outcomes():
    registration = load_experiment_registry(REGISTRY_PATH).get(
        "V6_fixed_boundary_js_regime"
    )
    earlier_boundary = OutcomeBoundary(
        source_commit="b" * 40,
        sha256="c" * 64,
        draw_count=registration.outcomes_known_draw_count - 1,
        history_through=registration.outcomes_known_through - timedelta(days=1),
    )
    active = replace(
        registration.prospective,
        status="active",
        freeze_commit="a" * 40,
        activation_commit="d" * 40,
        outcomes_known_at_activation=earlier_boundary,
        cohort_start=date(2026, 8, 19),
    )

    with pytest.raises(ValueError, match="activation boundary cannot precede"):
        replace(
            registration,
            status="prospective_shadow",
            prospective=active,
        )


def test_cohort_start_must_be_after_activation_known_outcomes():
    registration = load_experiment_registry(REGISTRY_PATH).get(
        "V6_fixed_boundary_js_regime"
    )
    activation_boundary = OutcomeBoundary(
        source_commit="b" * 40,
        sha256="c" * 64,
        draw_count=registration.outcomes_known_draw_count,
        history_through=date(2026, 8, 19),
    )
    active = replace(
        registration.prospective,
        status="active",
        freeze_commit="a" * 40,
        activation_commit="d" * 40,
        outcomes_known_at_activation=activation_boundary,
        cohort_start=activation_boundary.history_through,
    )

    with pytest.raises(ValueError, match="strictly after activation-known"):
        replace(
            registration,
            status="prospective_shadow",
            prospective=active,
        )


def test_prospective_shadow_accepts_only_continue_result_and_active_cohort():
    registry = load_experiment_registry(REGISTRY_PATH)
    candidate = _unsealed_v6_candidate()
    rejected = registry.get("V5_pair_affinity").result
    assert rejected is not None
    activation_boundary = OutcomeBoundary(
        source_commit="b" * 40,
        sha256="c" * 64,
        draw_count=candidate.outcomes_known_draw_count,
        history_through=candidate.outcomes_known_through,
    )
    active = replace(
        candidate.prospective,
        status="active",
        freeze_commit="a" * 40,
        activation_commit="d" * 40,
        outcomes_known_at_activation=activation_boundary,
        cohort_start=date(2026, 8, 19),
    )
    continued = replace(
        rejected,
        decision="continue_shadow",
        shadow_activation="active",
        historical_primary_signal_supported=True,
    )

    registration = replace(
        candidate,
        status="prospective_shadow",
        prospective=active,
        result=continued,
    )
    assert registration.result == continued

    with pytest.raises(ValueError, match="prospective_shadow requires"):
        replace(
            candidate,
            status="prospective_shadow",
            prospective=active,
            result=None,
        )
    with pytest.raises(ValueError, match="prospective_shadow requires"):
        replace(
            candidate,
            status="prospective_shadow",
            prospective=active,
            result=replace(rejected, shadow_activation="active"),
        )


def test_terminal_rejection_cannot_be_removed_with_dataclass_replace():
    rejected = load_experiment_registry(REGISTRY_PATH).get("V5_pair_affinity")

    with pytest.raises(ValueError, match="terminal result cannot be removed"):
        replace(rejected, status="registered", result=None)


def test_activated_cohort_cannot_be_reset_with_dataclass_replace():
    boundary = OutcomeBoundary(
        source_commit="b" * 40,
        sha256="c" * 64,
        draw_count=4432,
        history_through=date(2026, 8, 15),
    )
    registration = _active_registration("a" * 40, "d" * 40, boundary)
    inactive = load_experiment_registry(REGISTRY_PATH).get(
        "V6_fixed_boundary_js_regime"
    ).prospective

    with pytest.raises(ValueError, match="activated cohort cannot be reset"):
        replace(
            registration,
            status="registered",
            prospective=inactive,
            result=None,
        )


def test_sealed_terminal_result_cannot_be_removed_from_reloaded_registry(tmp_path):
    payload = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
    rejected = next(
        item for item in payload["experiments"] if item["id"] == "V5_pair_affinity"
    )
    rejected["status"] = "registered"
    rejected.pop("result")
    path = tmp_path / "registry.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match="sealed terminal result"):
        load_experiment_registry(path)


def test_sealed_terminal_experiment_cannot_be_deleted_from_registry(tmp_path):
    payload = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
    payload["experiments"] = [
        item
        for item in payload["experiments"]
        if item["id"] != "V5_pair_affinity"
    ]
    path = tmp_path / "registry.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match="missing sealed terminal"):
        load_experiment_registry(path)


def test_prospective_cohort_must_start_after_all_known_outcomes():
    registration = load_experiment_registry(REGISTRY_PATH).get(
        "V6_fixed_boundary_js_regime"
    )
    boundary = OutcomeBoundary(
        source_commit="b" * 40,
        sha256="c" * 64,
        draw_count=registration.outcomes_known_draw_count,
        history_through=registration.outcomes_known_through,
    )
    active = replace(
        registration.prospective,
        status="active",
        freeze_commit="a" * 40,
        activation_commit="d" * 40,
        outcomes_known_at_activation=boundary,
        cohort_start=registration.outcomes_known_through,
    )

    with pytest.raises(ValueError, match="after all outcomes known"):
        replace(
            registration,
            status="prospective_shadow",
            prospective=active,
            result=None,
        )


def _active_registration(
    freeze_commit: str,
    activation_commit: str,
    activation_boundary: OutcomeBoundary,
):
    registry = load_experiment_registry(REGISTRY_PATH)
    registration = _unsealed_v6_candidate()
    rejected = registry.get("V5_pair_affinity").result
    assert rejected is not None
    registration = replace(
        registration,
        outcomes_known_source_commit=activation_boundary.source_commit,
        outcomes_known_sha256=activation_boundary.sha256,
        outcomes_known_draw_count=activation_boundary.draw_count,
        outcomes_known_through=activation_boundary.history_through,
    )
    active = replace(
        registration.prospective,
        status="active",
        freeze_commit=freeze_commit,
        activation_commit=activation_commit,
        outcomes_known_at_activation=activation_boundary,
        cohort_start=date(2027, 1, 6),
    )
    continued = replace(
        rejected,
        decision="continue_shadow",
        shadow_activation="active",
        historical_primary_signal_supported=True,
    )
    return replace(
        registration,
        status="prospective_shadow",
        prospective=active,
        result=continued,
    )


def _snapshot() -> dict:
    return {
        "target_draw_date": "2027-01-06",
        "generated_at": "2027-01-03T12:00:00-05:00",
        "model_name": "v6_entropy_regime",
        "model_version": "v6.0.0",
        "probabilities": {str(number): 6 / 49 for number in range(1, 50)},
        "top6": [1, 2, 3, 4, 5, 6],
        "top12": list(range(1, 13)),
        "top18": list(range(1, 19)),
        "final_combination": [1, 2, 3, 4, 5, 6],
        "metadata": {
            "role": "shadow",
            "history_draws": 4431,
            "history_through": "2026-08-12",
        },
    }


def _git(repo: Path, *args: str, env: dict[str, str] | None = None) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    return completed.stdout.strip()


def _commit(repo: Path, message: str, timestamp: str) -> str:
    env = {
        **os.environ,
        "GIT_AUTHOR_DATE": timestamp,
        "GIT_COMMITTER_DATE": timestamp,
    }
    _git(repo, "add", ".", env=env)
    _git(repo, "commit", "-m", message, env=env)
    return _git(repo, "rev-parse", "HEAD")


def _git_repo_with_immutable_snapshot(
    tmp_path: Path,
    *,
    snapshot_timestamp: str = "2027-01-03T12:00:00-05:00",
    snapshot_payload: dict | None = None,
):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.name", "Protocol Test")
    _git(repo, "config", "user.email", "protocol@example.invalid")

    (repo / "freeze.txt").write_text("frozen\n", encoding="utf-8")
    data_path = repo / "data" / "processed" / "draws.csv"
    data_path.parent.mkdir(parents=True)
    data_path.write_bytes((ROOT / "data" / "processed" / "draws.csv").read_bytes())
    freeze = _commit(repo, "freeze", "2027-01-01T12:00:00-05:00")
    (repo / "activation.txt").write_text("active\n", encoding="utf-8")
    activation = _commit(repo, "activate", "2027-01-02T12:00:00-05:00")
    snapshot = snapshot_payload if snapshot_payload is not None else _snapshot()
    path = repo / "predictions" / (
        "2027-01-06__v6_entropy_regime__v6.0.0.json"
    )
    path.parent.mkdir()
    path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    first_commit = _commit(repo, "snapshot", snapshot_timestamp)
    return repo, path, snapshot, freeze, activation, first_commit


def _snapshot_outcome_evidence(repo: Path, freeze_commit: str):
    draws_path = repo / "data" / "processed" / "draws.csv"
    draws = load_draws(draws_path)
    boundary = OutcomeBoundary(
        source_commit=freeze_commit,
        sha256=sha256(draws_path.read_bytes()).hexdigest(),
        draw_count=len(draws),
        history_through=draws[-1].draw_date,
    )
    evidence = VerifiedOutcomeBoundary.from_repository(
        repo,
        boundary,
        registration_boundary=boundary,
    )
    return boundary, evidence


def _source_evidence_for_current_data(
    repo: Path,
    source_commit: str,
    base_boundary: OutcomeBoundary,
):
    draws_path = repo / "data" / "processed" / "draws.csv"
    rows = draws_path.read_text(encoding="utf-8").splitlines()
    boundary = OutcomeBoundary(
        source_commit=source_commit,
        sha256=sha256(draws_path.read_bytes()).hexdigest(),
        draw_count=len(rows) - 1,
        history_through=date.fromisoformat(rows[-1].split(",", 1)[0]),
    )
    return VerifiedOutcomeBoundary.from_repository(
        repo,
        boundary,
        registration_boundary=base_boundary,
    )


def test_git_file_evidence_is_derived_from_one_immutable_commit(tmp_path):
    repo, path, snapshot, freeze, activation, first_commit = (
        _git_repo_with_immutable_snapshot(tmp_path)
    )

    evidence = GitFileEvidence.from_repository(
        repo,
        path,
        freeze_commit=freeze,
        activation_commit=activation,
    )

    assert evidence.path == (
        "predictions/2027-01-06__v6_entropy_regime__v6.0.0.json"
    )
    assert evidence.first_commit_sha == first_commit
    assert evidence.first_commit_at.tzinfo is not None
    assert evidence.canonical_digest == snapshot_digest(snapshot)
    assert evidence.raw_sha256 == sha256(path.read_bytes()).hexdigest()
    assert evidence.commit_count == 1


def test_git_file_evidence_rejects_modified_or_non_ancestor_history(tmp_path):
    repo, path, snapshot, freeze, activation, _ = _git_repo_with_immutable_snapshot(
        tmp_path
    )
    (repo / "later.txt").write_text("later\n", encoding="utf-8")
    later = _commit(repo, "later", "2027-01-04T12:00:00-05:00")

    with pytest.raises(GitEvidenceError, match="activation commit is not a strict ancestor"):
        GitFileEvidence.from_repository(
            repo,
            path,
            freeze_commit=freeze,
            activation_commit=later,
        )

    snapshot["top6"] = [2, 3, 4, 5, 6, 7]
    path.write_text(json.dumps(snapshot), encoding="utf-8")
    _commit(repo, "rewrite snapshot", "2027-01-05T12:00:00-05:00")
    with pytest.raises(GitEvidenceError, match="exactly one commit"):
        GitFileEvidence.from_repository(
            repo,
            path,
            freeze_commit=freeze,
            activation_commit=activation,
        )


def _git_repo_with_outcome_boundaries(tmp_path: Path, *, rewrite_prefix: bool = False):
    repo = tmp_path / "outcome-repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.name", "Protocol Test")
    _git(repo, "config", "user.email", "protocol@example.invalid")
    draws = synthetic_draws(4)
    data_path = repo / "data" / "processed" / "draws.csv"
    data_path.parent.mkdir(parents=True)
    registration_bytes = _csv_bytes(draws[:3])
    data_path.write_bytes(registration_bytes)
    registration_commit = _commit(
        repo,
        "registration outcomes",
        "2027-01-01T12:00:00-05:00",
    )
    registration_boundary = OutcomeBoundary(
        source_commit=registration_commit,
        sha256=sha256(registration_bytes).hexdigest(),
        draw_count=3,
        history_through=draws[2].draw_date,
    )

    if rewrite_prefix:
        replacement = Draw(draws[0].draw_date, (2, 10, 18, 26, 34, 42), 1)
        activation_draws = [replacement, *draws[1:]]
        activation_bytes = _csv_bytes(activation_draws)
    else:
        activation_bytes = _csv_bytes(draws)
    data_path.write_bytes(activation_bytes)
    activation_commit = _commit(
        repo,
        "activation outcomes",
        "2027-01-02T12:00:00-05:00",
    )
    activation_boundary = OutcomeBoundary(
        source_commit=activation_commit,
        sha256=sha256(activation_bytes).hexdigest(),
        draw_count=4,
        history_through=draws[3].draw_date,
    )
    return repo, registration_boundary, activation_boundary


def test_verified_outcome_boundary_reads_and_checks_git_data_blobs(tmp_path):
    repo, registration_boundary, activation_boundary = (
        _git_repo_with_outcome_boundaries(tmp_path)
    )

    evidence = VerifiedOutcomeBoundary.from_repository(
        repo,
        activation_boundary,
        registration_boundary=registration_boundary,
    )

    assert evidence.boundary == activation_boundary
    assert evidence.registration_boundary == registration_boundary
    assert evidence.raw_sha256 == activation_boundary.sha256
    assert evidence.registration_prefix_preserved


def test_verified_outcome_boundary_rejects_rewritten_registration_prefix(tmp_path):
    repo, registration_boundary, activation_boundary = (
        _git_repo_with_outcome_boundaries(tmp_path, rewrite_prefix=True)
    )

    with pytest.raises(GitEvidenceError, match="registration-known data prefix"):
        VerifiedOutcomeBoundary.from_repository(
            repo,
            activation_boundary,
            registration_boundary=registration_boundary,
        )

def _evaluation(snapshot: dict, actual: Draw, snapshot_path: str) -> dict:
    probability = 6 / 49
    return {
        "target_draw_date": actual.draw_date.isoformat(),
        "model_name": snapshot["model_name"],
        "model_version": snapshot["model_version"],
        "actual": list(actual.numbers),
        "bonus": actual.bonus,
        "final_6_hits": 6,
        "top_6_hits": 6,
        "top_12_hits": 6,
        "top_18_hits": 6,
        "brier_score": probability * (1 - probability),
        "log_loss": -(
            6 * math.log(probability) + 43 * math.log(1 - probability)
        )
        / 49,
        "mean_actual_rank": 3.5,
        "matched_final": [1, 2, 3, 4, 5, 6],
        "prediction_snapshot_digest": snapshot_digest(snapshot),
        "prediction_snapshot_path": snapshot_path,
        "actual_draw_digest": draw_digest(actual),
        "verified_data_draw_count": 4432,
        "verified_data_history_through": actual.draw_date.isoformat(),
    }


def _commit_evaluation(
    repo: Path,
    evaluation: dict,
    actual: Draw,
    timestamp: str = "2027-01-07T12:00:00-05:00",
) -> tuple[Path, str]:
    path = repo / "evaluations" / (
        "2027-01-06__v6_entropy_regime__v6.0.0.json"
    )
    path.parent.mkdir()
    path.write_text(json.dumps(evaluation, indent=2), encoding="utf-8")
    data_path = repo / "data" / "processed" / "draws.csv"
    values = ",".join(str(number) for number in actual.numbers)
    row = f"{actual.draw_date.isoformat()},{values},{actual.bonus}\n".encode()
    data_path.write_bytes(data_path.read_bytes() + row)
    commit = _commit(repo, "evaluation", timestamp)
    return path, commit


def test_unactivated_cohort_cannot_accept_a_snapshot(tmp_path):
    registration = load_experiment_registry(REGISTRY_PATH).get(
        "V6_fixed_boundary_js_regime"
    )
    repo, path, snapshot, freeze, activation, _ = _git_repo_with_immutable_snapshot(
        tmp_path
    )
    evidence = GitFileEvidence.from_repository(
        repo,
        path,
        freeze_commit=freeze,
        activation_commit=activation,
    )
    assessment = assess_prospective_snapshot(
        registration,
        snapshot,
        snapshot_evidence=evidence,
    )

    assert not assessment.eligible
    assert "cohort_not_active" in assessment.reasons


def test_active_cohort_accounts_for_pending_and_verified_evaluation(tmp_path):
    repo, path, snapshot, freeze, activation, snapshot_commit = _git_repo_with_immutable_snapshot(
        tmp_path
    )
    boundary, boundary_evidence = _snapshot_outcome_evidence(repo, freeze)
    registration = _active_registration(freeze, activation, boundary)
    snapshot_source_evidence = _source_evidence_for_current_data(
        repo,
        snapshot_commit,
        boundary,
    )
    snapshot_evidence = GitFileEvidence.from_repository(
        repo,
        path,
        freeze_commit=freeze,
        activation_commit=activation,
    )

    pending = assess_prospective_snapshot(
        registration,
        snapshot,
        snapshot_evidence=snapshot_evidence,
        activation_boundary_evidence=boundary_evidence,
        snapshot_source_evidence=snapshot_source_evidence,
    )
    actual = Draw(date(2027, 1, 6), (1, 2, 3, 4, 5, 6), 7)
    evaluation = _evaluation(snapshot, actual, snapshot_evidence.path)
    evaluation_path, evaluation_commit = _commit_evaluation(repo, evaluation, actual)
    evaluation_evidence = GitFileEvidence.from_repository(
        repo,
        evaluation_path,
        freeze_commit=freeze,
        activation_commit=activation,
    )
    evaluation_source_evidence = _source_evidence_for_current_data(
        repo,
        evaluation_commit,
        snapshot_source_evidence.boundary,
    )
    evaluated = assess_prospective_snapshot(
        registration,
        snapshot,
        snapshot_evidence=snapshot_evidence,
        activation_boundary_evidence=boundary_evidence,
        snapshot_source_evidence=snapshot_source_evidence,
        evaluation=evaluation,
        evaluation_evidence=evaluation_evidence,
        evaluation_source_evidence=evaluation_source_evidence,
    )

    assert pending.status == "eligible_pending"
    assert pending.snapshot_eligible
    assert not pending.eligible
    assert not pending.evaluated_eligible
    assert evaluated.status == "eligible_evaluated"
    assert evaluated.evaluated_eligible


@pytest.mark.parametrize(
    ("failure", "expected_reason"),
    [
        ("missing_metric", "missing_registered_metric:top_12_hits"),
        ("snapshot_digest", "evaluation_snapshot_digest_mismatch"),
        ("snapshot_path", "evaluation_snapshot_path_mismatch"),
        ("actual", "evaluation_actual_mismatch"),
        ("actual_digest", "actual_draw_digest_mismatch"),
    ],
)
def test_evaluation_must_bind_snapshot_actual_and_all_registered_metrics(
    tmp_path,
    failure,
    expected_reason,
):
    repo, path, snapshot, freeze, activation, snapshot_commit = _git_repo_with_immutable_snapshot(
        tmp_path
    )
    boundary, boundary_evidence = _snapshot_outcome_evidence(repo, freeze)
    registration = _active_registration(freeze, activation, boundary)
    snapshot_source_evidence = _source_evidence_for_current_data(
        repo,
        snapshot_commit,
        boundary,
    )
    snapshot_evidence = GitFileEvidence.from_repository(
        repo,
        path,
        freeze_commit=freeze,
        activation_commit=activation,
    )
    actual = Draw(date(2027, 1, 6), (1, 2, 3, 4, 5, 6), 7)
    evaluation = _evaluation(snapshot, actual, snapshot_evidence.path)
    if failure == "missing_metric":
        evaluation.pop("top_12_hits")
    elif failure == "snapshot_digest":
        evaluation["prediction_snapshot_digest"] = "0" * 64
    elif failure == "snapshot_path":
        evaluation["prediction_snapshot_path"] = "predictions/wrong.json"
    elif failure == "actual":
        evaluation["actual"] = [1, 2, 3, 4, 5]
    else:
        evaluation["actual_draw_digest"] = "0" * 64
    evaluation_path, evaluation_commit = _commit_evaluation(repo, evaluation, actual)
    evaluation_evidence = GitFileEvidence.from_repository(
        repo,
        evaluation_path,
        freeze_commit=freeze,
        activation_commit=activation,
    )
    evaluation_source_evidence = _source_evidence_for_current_data(
        repo,
        evaluation_commit,
        snapshot_source_evidence.boundary,
    )

    assessment = assess_prospective_snapshot(
        registration,
        snapshot,
        snapshot_evidence=snapshot_evidence,
        activation_boundary_evidence=boundary_evidence,
        snapshot_source_evidence=snapshot_source_evidence,
        evaluation=evaluation,
        evaluation_evidence=evaluation_evidence,
        evaluation_source_evidence=evaluation_source_evidence,
    )

    assert assessment.status == "excluded"
    assert expected_reason in assessment.reasons


def test_active_cohort_excludes_late_or_digest_changed_snapshots(tmp_path):
    repo, path, snapshot, freeze, activation, snapshot_commit = _git_repo_with_immutable_snapshot(
        tmp_path,
        snapshot_timestamp="2027-01-06T00:00:00-05:00",
    )
    boundary, boundary_evidence = _snapshot_outcome_evidence(repo, freeze)
    registration = _active_registration(freeze, activation, boundary)
    snapshot_source_evidence = _source_evidence_for_current_data(
        repo,
        snapshot_commit,
        boundary,
    )
    evidence = GitFileEvidence.from_repository(
        repo,
        path,
        freeze_commit=freeze,
        activation_commit=activation,
    )
    changed = {**snapshot, "top6": [2, 3, 4, 5, 6, 7]}
    assessment = assess_prospective_snapshot(
        registration,
        changed,
        snapshot_evidence=evidence,
        activation_boundary_evidence=boundary_evidence,
        snapshot_source_evidence=snapshot_source_evidence,
    )

    assert assessment.status == "excluded"
    assert "late_snapshot_commit" in assessment.reasons
    assert "snapshot_digest_mismatch" in assessment.reasons


def test_pending_snapshot_requires_the_complete_probability_and_ranking_contract(
    tmp_path,
):
    snapshot = _snapshot()
    probability = snapshot["probabilities"]["1"]
    snapshot["probabilities"]["01"] = 0.0
    snapshot["probabilities"]["1"] = 0.0
    snapshot["probabilities"]["2"] += probability
    snapshot["top6"] = [2, 3, 4, 5, 6, 13]
    snapshot["top18"][-1] = snapshot["top18"][-2]
    snapshot["final_combination"] = [1, 1, 2, 3, 4, 5]
    repo, path, snapshot, freeze, activation, snapshot_commit = (
        _git_repo_with_immutable_snapshot(
            tmp_path,
            snapshot_payload=snapshot,
        )
    )
    boundary, activation_evidence = _snapshot_outcome_evidence(repo, freeze)
    registration = _active_registration(freeze, activation, boundary)
    snapshot_evidence = GitFileEvidence.from_repository(
        repo,
        path,
        freeze_commit=freeze,
        activation_commit=activation,
    )
    source_evidence = _source_evidence_for_current_data(
        repo,
        snapshot_commit,
        boundary,
    )

    assessment = assess_prospective_snapshot(
        registration,
        snapshot,
        snapshot_evidence=snapshot_evidence,
        activation_boundary_evidence=activation_evidence,
        snapshot_source_evidence=source_evidence,
    )

    assert assessment.status == "excluded"
    assert "probability_keys_must_be_canonical_1_to_49" in assessment.reasons
    assert "probabilities_must_be_finite_open_interval" in assessment.reasons
    assert "top6_does_not_match_probability_rank" in assessment.reasons
    assert "top6_not_nested_in_top12" in assessment.reasons
    assert "invalid_top18" in assessment.reasons
    assert "invalid_final_combination" in assessment.reasons


def _scheduled_targets(count: int, *, start: date = date(2027, 1, 6)) -> list[date]:
    targets = [start]
    while len(targets) < count:
        delta = 3 if targets[-1].weekday() == 2 else 4
        targets.append(targets[-1] + timedelta(days=delta))
    return targets


def _cohort_assessment(
    target: date,
    status: str = "eligible_evaluated",
    evaluation_git_evidence: GitFileEvidence | None = None,
):
    key = target.strftime("%Y%m%d")
    snapshot_hash = sha256(f"snapshot:{key}".encode()).hexdigest()
    evaluation_hash = (
        sha256(f"evaluation:{key}".encode()).hexdigest()
        if status == "eligible_evaluated"
        else None
    )
    snapshot_path = (
        f"predictions/{target.isoformat()}__v6_entropy_regime__v6.0.0.json"
    )
    evaluation_path = snapshot_path.replace("predictions/", "evaluations/", 1)
    template = evaluation_git_evidence
    repository = template.repository if template is not None else ROOT
    commit_time = (
        template.first_commit_at
        if template is not None
        else datetime(2027, 1, 7, tzinfo=timezone.utc)
    )
    evaluation_commit = (
        template.first_commit_sha
        if template is not None
        else sha256(f"commit:{key}".encode()).hexdigest()[:40]
    )
    freeze_commit = template.freeze_commit if template is not None else "a" * 40
    activation_commit = (
        template.activation_commit if template is not None else "d" * 40
    )
    snapshot_git = GitFileEvidence._create(
        repository=repository,
        path=snapshot_path,
        first_commit_sha=sha256(f"snapshot-commit:{key}".encode()).hexdigest()[:40],
        first_commit_at=commit_time - timedelta(days=1),
        canonical_digest=snapshot_hash,
        raw_sha256=snapshot_hash,
        commit_count=1,
        freeze_commit=freeze_commit,
        activation_commit=activation_commit,
    )
    evaluation_git = None
    if evaluation_hash is not None:
        evaluation_git = GitFileEvidence._create(
            repository=repository,
            path=evaluation_path,
            first_commit_sha=evaluation_commit,
            first_commit_at=commit_time,
            canonical_digest=evaluation_hash,
            raw_sha256=evaluation_hash,
            commit_count=1,
            freeze_commit=freeze_commit,
            activation_commit=activation_commit,
        )
    return CohortAssessment._create(
        status=status,
        reasons=(),
        snapshot_digest=snapshot_hash,
        target_draw_date=target,
        evaluation_digest=evaluation_hash,
        snapshot_path=snapshot_path,
        evaluation_path=(evaluation_path if evaluation_hash else None),
        snapshot_git_evidence=snapshot_git,
        evaluation_git_evidence=evaluation_git,
    )


def _aggregate_registration():
    boundary = OutcomeBoundary(
        source_commit="b" * 40,
        sha256="c" * 64,
        draw_count=4431,
        history_through=date(2026, 8, 12),
    )
    return _active_registration("a" * 40, "d" * 40, boundary)


def test_cohort_aggregator_freezes_exact_208_draw_checkpoint_and_halves():
    registration = _aggregate_registration()
    observations = tuple(
        _cohort_assessment(target) for target in _scheduled_targets(208)
    )

    aggregate = aggregate_prospective_cohort(registration, observations)

    assert aggregate.status == "ready"
    assert len(aggregate.eligible_evaluated) == 208
    assert len(aggregate.checkpoint) == 208
    assert len(aggregate.first_half) == 104
    assert len(aggregate.second_half) == 104
    assert aggregate.first_half + aggregate.second_half == aggregate.checkpoint
    assert aggregate.pending == ()
    assert aggregate.formal_look_count == 0


def test_cohort_aggregator_does_not_count_pending_and_marks_unlooked_overrun():
    registration = _aggregate_registration()
    targets = _scheduled_targets(210)
    collecting = aggregate_prospective_cohort(
        registration,
        tuple(_cohort_assessment(target) for target in targets[:207])
        + (_cohort_assessment(targets[209], "eligible_pending"),),
    )
    assert collecting.status == "collecting"
    assert len(collecting.eligible_evaluated) == 207
    assert len(collecting.pending) == 1

    overdue = aggregate_prospective_cohort(
        registration,
        tuple(_cohort_assessment(target) for target in targets[:209]),
    )
    assert overdue.status == "overdue"
    assert len(overdue.checkpoint) == 208
    assert len(overdue.extra_evaluated) == 1


def test_cohort_aggregator_blocks_earlier_pending_duplicates_and_second_look():
    registration = _aggregate_registration()
    targets = _scheduled_targets(210)
    observations = tuple(
        _cohort_assessment(target)
        for index, target in enumerate(targets[:209])
        if index != 100
    )
    earlier_pending = _cohort_assessment(targets[100], "eligible_pending")

    blocked = aggregate_prospective_cohort(
        registration,
        observations + (earlier_pending,),
    )
    assert blocked.status == "waiting_for_earlier_pending"
    assert blocked.checkpoint == ()

    duplicate = observations + (_cohort_assessment(targets[0]),)
    with pytest.raises(ValueError, match="duplicate prospective target"):
        aggregate_prospective_cohort(registration, duplicate)

    ready_observations = tuple(
        _cohort_assessment(target) for target in targets[:208]
    )
    with pytest.raises(ValueError, match="at most one formal look"):
        aggregate_prospective_cohort(
            registration,
            ready_observations,
            formal_looks=(object(), object()),
        )


def test_formal_look_requires_exact_ready_checkpoint_and_git_evidence(tmp_path):
    repo, _, _, freeze, activation, _ = _git_repo_with_immutable_snapshot(tmp_path)
    boundary, _ = _snapshot_outcome_evidence(repo, freeze)
    registration = _active_registration(freeze, activation, boundary)
    evaluation_path = repo / "audit" / "checkpoint-evaluation.json"
    evaluation_path.parent.mkdir()
    evaluation_path.write_text(json.dumps({"kind": "checkpoint"}), encoding="utf-8")
    _commit(repo, "checkpoint evaluation", "2027-01-07T12:00:00-05:00")
    evaluation_git = GitFileEvidence.from_repository(
        repo,
        evaluation_path,
        freeze_commit=freeze,
        activation_commit=activation,
    )
    observations = tuple(
        _cohort_assessment(target, evaluation_git_evidence=evaluation_git)
        for target in _scheduled_targets(208)
    )
    ready = aggregate_prospective_cohort(registration, observations)
    report_path = repo / "reports" / "prospective" / (
        f"{registration.experiment_id}__{registration.model_version}__formal_look.json"
    )
    report_path.parent.mkdir(parents=True)
    report_path.write_text(
        json.dumps(
            {
                "experiment_id": registration.experiment_id,
                "model_name": registration.model_name,
                "model_version": registration.model_version,
                "checkpoint_digest": ready.checkpoint_digest,
                "eligible_evaluated_count": 208,
                "decision": "reject",
            }
        ),
        encoding="utf-8",
    )
    _commit(repo, "formal look", "2027-01-08T12:00:00-05:00")
    formal_look = FormalLookRecord.from_repository(
        registration,
        ready,
        repo,
        report_path,
    )

    looked = aggregate_prospective_cohort(
        registration,
        observations,
        formal_looks=(formal_look,),
    )
    assert looked.status == "formal_look_recorded"
    assert formal_look.report_sha256 == sha256(report_path.read_bytes()).hexdigest()
    assert formal_look.record_commit == formal_look.git_evidence.first_commit_sha

    overdue = aggregate_prospective_cohort(
        registration,
        observations + (
            _cohort_assessment(
                _scheduled_targets(209)[-1],
                evaluation_git_evidence=evaluation_git,
            ),
        ),
    )
    with pytest.raises(GitEvidenceError, match="exact ready checkpoint"):
        FormalLookRecord.from_repository(
            registration,
            overdue,
            repo,
            report_path,
        )
    with pytest.raises(ValueError, match="cannot retroactively"):
        aggregate_prospective_cohort(
            registration,
            overdue.eligible_evaluated,
            formal_looks=(formal_look,),
        )


def test_verified_assessment_and_formal_look_cannot_be_publicly_constructed():
    with pytest.raises(TypeError):
        CohortAssessment()
    with pytest.raises(TypeError):
        FormalLookRecord()


def test_fixed_formal_look_cannot_choose_continue_shadow(tmp_path, monkeypatch):
    registration = _aggregate_registration()
    ready = aggregate_prospective_cohort(
        registration,
        tuple(_cohort_assessment(target) for target in _scheduled_targets(208)),
    )
    relative_path = (
        "reports/prospective/"
        f"{registration.experiment_id}__{registration.model_version}__formal_look.json"
    )
    report_path = tmp_path / relative_path
    report_path.parent.mkdir(parents=True)
    payload = {
        "experiment_id": registration.experiment_id,
        "model_name": registration.model_name,
        "model_version": registration.model_version,
        "checkpoint_digest": ready.checkpoint_digest,
        "eligible_evaluated_count": 208,
        "decision": "continue_shadow",
    }
    report_path.write_text(json.dumps(payload), encoding="utf-8")
    evidence = GitFileEvidence._create(
        repository=tmp_path.resolve(),
        path=relative_path,
        first_commit_sha="e" * 40,
        first_commit_at=datetime(2030, 1, 1, tzinfo=timezone.utc),
        canonical_digest=snapshot_digest(payload),
        raw_sha256=sha256(report_path.read_bytes()).hexdigest(),
        commit_count=1,
        freeze_commit=registration.prospective.freeze_commit,
        activation_commit=registration.prospective.activation_commit,
    )
    monkeypatch.setattr(
        GitFileEvidence,
        "from_repository",
        classmethod(lambda cls, *args, **kwargs: evidence),
    )

    with pytest.raises(GitEvidenceError, match="decision is invalid"):
        FormalLookRecord.from_repository(
            registration,
            ready,
            tmp_path,
            report_path,
        )
