from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime
from hashlib import sha256
import json
import math
import os
from pathlib import Path
from types import SimpleNamespace
import subprocess
import sys

import pytest
import yaml

import lotto649.prospective as prospective_module
from lotto649.domain import Draw, Prediction
from lotto649.evaluation import evaluate_prediction
from lotto649.models.factory import build_models
from lotto649.optimizer import rank_numbers, select_combination
from lotto649.predictor import make_prediction
from lotto649.prospective import audit_registered_cohort, verify_live_release
from lotto649.research_protocol import GitEvidenceError, draw_digest, snapshot_digest


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _synthetic_python_312(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        prospective_module,
        "_runtime_python_identity",
        lambda: ("CPython", "3.12"),
    )


def _git(repository: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repository), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _commit(repository: Path, message: str, committed_at: str) -> str:
    environment = os.environ.copy()
    environment["GIT_AUTHOR_DATE"] = committed_at
    environment["GIT_COMMITTER_DATE"] = committed_at
    completed = subprocess.run(
        ["git", "-C", str(repository), "commit", "-m", message],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )
    assert completed.stdout
    return _git(repository, "rev-parse", "HEAD")


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _draw_csv(draws: list[Draw]) -> str:
    rows = ["draw_date,n1,n2,n3,n4,n5,n6,bonus"]
    for draw in draws:
        rows.append(
            ",".join(
                (
                    draw.draw_date.isoformat(),
                    *(str(number) for number in draw.numbers),
                    str(draw.bonus),
                )
            )
        )
    return "\n".join(rows) + "\n"


def _prediction_payload(
    target: date,
    *,
    model_name: str = "v3_boosting",
    model_version: str = "v3.0.0",
    role: str = "shadow",
    generated_at: str = "2026-01-05T12:00:00-05:00",
    history_draws: int = 1,
    history_through: str = "2026-01-03",
) -> dict:
    probability = 6.0 / 49.0
    return {
        "target_draw_date": target.isoformat(),
        "generated_at": generated_at,
        "model_name": model_name,
        "model_version": model_version,
        "probabilities": {
            str(number): probability for number in range(1, 50)
        },
        "top6": list(range(1, 7)),
        "top12": list(range(1, 13)),
        "top18": list(range(1, 19)),
        "final_combination": list(range(1, 7)),
        "metadata": {
            "role": role,
            "history_draws": history_draws,
            "history_through": history_through,
        },
    }


def _model_prediction_payload(
    models: dict,
    cfg: dict,
    history: list[Draw],
    target: date,
    *,
    model_name: str,
    model_version: str,
    role: str,
    generated_at: str,
) -> dict:
    prediction = make_prediction(
        models[model_name],
        history,
        target,
        cfg,
        model_version,
    )
    payload = prediction.to_json_dict()
    payload["generated_at"] = generated_at
    payload["metadata"]["role"] = role
    return payload


def _add_release_metadata(snapshot: dict, evidence, repository: Path) -> None:
    snapshot["metadata"]["prospective_release"] = {
            "experiment_id": evidence.experiment_id,
            "freeze_commit": evidence.freeze_commit,
            "activation_commit": evidence.activation_commit,
            "release_commit": evidence.release_commit,
            "generation_source_commit": evidence.evidence_commit,
            "immutable_registration_digest": (
                evidence.immutable_registration_digest
            ),
            "activation_anchor_sha256": evidence.activation_anchor_sha256,
            "frozen_manifest_sha256": evidence.frozen_manifest_sha256,
            "requirements_live_lock_sha256": sha256(
                (repository / "requirements-live.lock").read_bytes()
            ).hexdigest(),
    }


def _mutate_prediction_but_keep_contract(snapshot: dict) -> None:
    probabilities = {
        int(number): float(value)
        for number, value in snapshot["probabilities"].items()
    }
    probabilities[1] += 1.0e-6
    probabilities[49] -= 1.0e-6
    ranking = rank_numbers(probabilities)
    snapshot["probabilities"] = {
        str(number): probabilities[number] for number in range(1, 50)
    }
    snapshot["top6"] = ranking[:6]
    snapshot["top12"] = ranking[:12]
    snapshot["top18"] = ranking[:18]
    snapshot["final_combination"] = select_combination(probabilities, 12)


def _evaluation_payload(snapshot: dict, actual: Draw, verified_draws: list[Draw]) -> dict:
    prediction = Prediction(
        target_draw_date=date.fromisoformat(snapshot["target_draw_date"]),
        generated_at=datetime.fromisoformat(snapshot["generated_at"]),
        model_name=snapshot["model_name"],
        model_version=snapshot["model_version"],
        probabilities={
            int(number): float(value)
            for number, value in snapshot["probabilities"].items()
        },
        top6=snapshot["top6"],
        top12=snapshot["top12"],
        top18=snapshot["top18"],
        final_combination=snapshot["final_combination"],
        metadata=snapshot["metadata"],
    )
    evaluation = evaluate_prediction(prediction, actual)
    evaluation.update(
        {
            "prediction_snapshot_digest": snapshot_digest(snapshot),
            "prediction_snapshot_path": (
                f"predictions/{actual.draw_date.isoformat()}__"
                f"{snapshot['model_name']}__{snapshot['model_version']}.json"
            ),
            "actual_draw_digest": draw_digest(actual),
            "verified_data_draw_count": len(verified_draws),
            "verified_data_history_through": verified_draws[-1].draw_date.isoformat(),
        }
    )
    return evaluation


def _write_registry(repository: Path, *, active: bool) -> None:
    payload = yaml.safe_load(
        (ROOT / "docs" / "experiments" / "registry.yaml").read_text(
            encoding="utf-8"
        )
    )
    registration = next(
        item
        for item in payload["experiments"]
        if item["id"] == "V3_frozen_shadow_cohort"
    )
    registration["status"] = "prospective_shadow" if active else "registered"
    registration["result"] = None
    registration["prospective"] = {
        "status": "not_activated",
        "role": "shadow",
        "minimum_eligible_draws": 208,
        "commit_deadline": "before_target_local_date",
        "freeze_commit": None,
        "activation_commit": None,
        "outcomes_known_at_activation": None,
        "cohort_start": None,
    }
    path = repository / "docs" / "experiments" / "registry.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _write_dormant_registry(
    repository: Path,
    *,
    outcome_commit: str,
    initial_csv_sha256: str,
    minimum_history_draws: int = 1,
    minimum_eligible_draws: int = 208,
) -> None:
    payload = yaml.safe_load(
        (ROOT / "docs" / "experiments" / "registry.yaml").read_text(
            encoding="utf-8"
        )
    )
    registration = next(
        item
        for item in payload["experiments"]
        if item["id"] == "V3_frozen_shadow_cohort"
    )
    registration.update(
        {
            "status": "registered",
            "registered_on": date(2026, 1, 3),
            "registration_dataset": {
                "path": "data/processed/draws.csv",
                "source_commit": outcome_commit,
                "sha256": initial_csv_sha256,
                "draw_count": 1,
                "history_through": date(2026, 1, 3),
            },
            "outcomes_known_at_registration": {
                "source_commit": outcome_commit,
                "sha256": initial_csv_sha256,
                "draw_count": 1,
                "history_through": date(2026, 1, 3),
            },
            "result": None,
        }
    )
    registration["parameters"]["frozen_implementation_paths"] = [
        "config.yaml",
        "frozen/model.py",
        "requirements-live.lock",
    ]
    registration["parameters"]["minimum_history_draws"] = minimum_history_draws
    registration["parameters"]["live_python_implementation"] = "CPython"
    registration["parameters"]["live_python_major_minor"] = "3.12"
    registration["prospective"] = {
        "status": "not_activated",
        "role": "shadow",
        "minimum_eligible_draws": minimum_eligible_draws,
        "commit_deadline": "before_target_local_date",
        "freeze_commit": None,
        "activation_commit": None,
        "outcomes_known_at_activation": None,
        "cohort_start": None,
    }
    path = repository / "docs" / "experiments" / "registry.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _activate_registry(
    repository: Path,
    *,
    freeze_commit: str,
    activation_commit: str,
    initial_csv_sha256: str,
    result_overrides: dict | None = None,
) -> None:
    path = repository / "docs" / "experiments" / "registry.yaml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    registration = next(
        item
        for item in payload["experiments"]
        if item["id"] == "V3_frozen_shadow_cohort"
    )
    registration["status"] = "prospective_shadow"
    registration["result"] = {
        "decision": "continue_shadow",
        "decided_on": date(2026, 1, 4),
        "implementation_commit": freeze_commit,
        "report_json": (
            "reports/prospective/"
            "V3_frozen_shadow_cohort__v3.0.0__activation.json"
        ),
        "report_markdown": (
            "reports/prospective/"
            "V3_frozen_shadow_cohort__v3.0.0__activation.md"
        ),
        "result_file": (
            "reports/prospective/"
            "V3_frozen_shadow_cohort__v3.0.0__activation.claim"
        ),
        "historical_primary_signal_supported": False,
        "shadow_activation": "active",
    }
    if result_overrides:
        registration["result"].update(result_overrides)
    registration["prospective"].update(
        {
            "status": "active",
            "freeze_commit": freeze_commit,
            "activation_commit": activation_commit,
            "outcomes_known_at_activation": {
                "source_commit": activation_commit,
                "sha256": initial_csv_sha256,
                "draw_count": 1,
                "history_through": date(2026, 1, 3),
            },
            "cohort_start": date(2026, 1, 7),
        }
    )
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _active_repository_with_mixed_observations(
    tmp_path: Path,
    *,
    pending_model_version: str = "v3.0.0",
    release_after_snapshots: bool = False,
    immutable_registry_drift: bool = False,
    frozen_path_drift: bool = False,
    omit_comparisons: bool = False,
    comparison_role: str = "primary",
    invalid_comparison_probability: bool = False,
    invalid_comparison_metric: bool = False,
    omit_comparison_evaluation: bool = False,
    valid_candidate_replay_mutation: bool = False,
    valid_comparison_replay_mutation: bool = False,
    minimum_history_draws: int = 1,
    minimum_eligible_draws: int = 208,
    include_third_evaluated: bool = False,
    activation_result_overrides: dict | None = None,
    pre_release_terminal_restore: bool = False,
) -> Path:
    repository = tmp_path / "repository"
    repository.mkdir(parents=True)
    _git(repository, "init")
    _git(repository, "config", "user.name", "Prospective Test")
    _git(repository, "config", "user.email", "prospective@example.test")

    activation_draw = Draw(date(2026, 1, 3), (8, 9, 10, 11, 12, 13), 14)
    initial_csv = _draw_csv([activation_draw])
    data_path = repository / "data" / "processed" / "draws.csv"
    data_path.parent.mkdir(parents=True)
    data_path.write_text(initial_csv, encoding="utf-8")
    _git(repository, "add", "data/processed/draws.csv")
    outcome_commit = _commit(
        repository,
        "Commit registration-known outcomes",
        "2026-01-03T10:00:00-05:00",
    )

    _write_dormant_registry(
        repository,
        outcome_commit=outcome_commit,
        initial_csv_sha256=sha256(initial_csv.encode()).hexdigest(),
        minimum_history_draws=minimum_history_draws,
        minimum_eligible_draws=minimum_eligible_draws,
    )
    frozen_path = repository / "frozen" / "model.py"
    frozen_path.parent.mkdir()
    frozen_path.write_text("MODEL_SPEC = 'v3.0.0'\n", encoding="utf-8")
    config_payload = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    config_path = repository / "config.yaml"
    config_path.write_text(
        yaml.safe_dump(config_payload, sort_keys=False),
        encoding="utf-8",
    )
    requirements_path = repository / "requirements-live.lock"
    requirements_path.write_bytes((ROOT / "requirements-live.lock").read_bytes())
    _git(
        repository,
        "add",
        "config.yaml",
        "docs/experiments/registry.yaml",
        "frozen/model.py",
        "requirements-live.lock",
    )
    freeze_commit = _commit(
        repository,
        "Freeze dormant cohort specification",
        "2026-01-03T11:00:00-05:00",
    )

    activation_base = (
        repository
        / "reports"
        / "prospective"
        / "V3_frozen_shadow_cohort__v3.0.0__activation"
    )
    activation_json = Path(f"{activation_base}.json")
    _write_json(
        activation_json,
        {
            "schema_version": 1,
            "experiment_id": "V3_frozen_shadow_cohort",
            "model_name": "v3_boosting",
            "model_version": "v3.0.0",
            "freeze_commit": freeze_commit,
            "decision": "continue_shadow",
            "role": "shadow",
            "outcome_path": "data/processed/draws.csv",
            "outcome_sha256": sha256(initial_csv.encode()).hexdigest(),
            "outcome_draw_count": 1,
            "outcome_history_through": "2026-01-03",
            "cohort_start": "2026-01-07",
        },
    )
    Path(f"{activation_base}.md").write_text(
        "# Synthetic activation anchor\n",
        encoding="utf-8",
    )
    Path(f"{activation_base}.claim").write_text(
        "V3_frozen_shadow_cohort v3.0.0 activation\n",
        encoding="utf-8",
    )
    _git(repository, "add", "reports/prospective")
    activation_commit = _commit(
        repository,
        "Record activation anchor",
        "2026-01-04T12:00:00-05:00",
    )

    cfg = dict(config_payload)
    cfg["_root"] = repository
    models = build_models(
        cfg,
        requested=["v3_boosting", "ensemble", "random"],
    )
    evaluated_snapshot = _model_prediction_payload(
        models,
        cfg,
        [activation_draw],
        date(2026, 1, 7),
        model_name="v3_boosting",
        model_version="v3.0.0",
        role="shadow",
        generated_at="2026-01-05T12:00:00-05:00",
    )
    pending_snapshot = _model_prediction_payload(
        models,
        cfg,
        [activation_draw],
        date(2026, 1, 10),
        model_name="v3_boosting",
        model_version="v3.0.0",
        role="shadow",
        generated_at="2026-01-05T12:00:00-05:00",
    )
    if valid_candidate_replay_mutation:
        _mutate_prediction_but_keep_contract(evaluated_snapshot)
    third_snapshot = None
    if include_third_evaluated:
        third_snapshot = _model_prediction_payload(
            models,
            cfg,
            [activation_draw],
            date(2026, 1, 14),
            model_name="v3_boosting",
            model_version="v3.0.0",
            role="shadow",
            generated_at="2026-01-05T12:00:00-05:00",
        )
    pending_snapshot["model_version"] = pending_model_version
    evaluated_path = (
        repository
        / "predictions"
        / "2026-01-07__v3_boosting__v3.0.0.json"
    )
    pending_path = (
        repository
        / "predictions"
        / "2026-01-10__v3_boosting__v3.0.0.json"
    )
    _write_json(evaluated_path, evaluated_snapshot)
    _write_json(pending_path, pending_snapshot)
    if third_snapshot is not None:
        _write_json(
            repository
            / "predictions"
            / "2026-01-14__v3_boosting__v3.0.0.json",
            third_snapshot,
        )
    comparison_snapshots: dict[tuple[date, str], dict] = {}
    if not omit_comparisons:
        comparison_targets = [date(2026, 1, 7), date(2026, 1, 10)]
        if include_third_evaluated:
            comparison_targets.append(date(2026, 1, 14))
        for target in comparison_targets:
            for model_name in ("ensemble", "random"):
                comparison = _model_prediction_payload(
                    models,
                    cfg,
                    [activation_draw],
                    target,
                    model_name=model_name,
                    model_version="v1.0.0",
                    role=comparison_role if model_name == "ensemble" else "primary",
                    generated_at="2026-01-05T12:00:00-05:00",
                )
                if invalid_comparison_probability and model_name == "ensemble":
                    comparison["probabilities"]["1"] = 0.5
                if valid_comparison_replay_mutation and model_name == "ensemble":
                    _mutate_prediction_but_keep_contract(comparison)
                comparison_snapshots[(target, model_name)] = comparison
                _write_json(
                    repository
                    / "predictions"
                    / f"{target.isoformat()}__{model_name}__v1.0.0.json",
                    comparison,
                )
    if release_after_snapshots:
        _git(repository, "add", "predictions")
        _commit(
            repository,
            "Commit snapshots before registry release",
            "2026-01-04T12:30:00-05:00",
        )

    if pre_release_terminal_restore:
        registry_path = repository / "docs" / "experiments" / "registry.yaml"
        dormant_raw = registry_path.read_text(encoding="utf-8")
        registry = yaml.safe_load(dormant_raw)
        registration = next(
            item
            for item in registry["experiments"]
            if item["id"] == "V3_frozen_shadow_cohort"
        )
        registration["status"] = "closed_rejected"
        registration["result"] = {
            "decision": "reject",
            "decided_on": date(2026, 1, 4),
            "implementation_commit": freeze_commit,
            "report_json": "reports/prospective/transient.json",
            "report_markdown": "reports/prospective/transient.md",
            "result_file": "reports/prospective/transient.md",
            "historical_primary_signal_supported": False,
            "shadow_activation": "not_activated",
        }
        registry_path.write_text(
            yaml.safe_dump(registry, sort_keys=False),
            encoding="utf-8",
        )
        _git(repository, "add", registry_path.relative_to(repository).as_posix())
        _commit(
            repository,
            "Illegally terminate dormant cohort",
            "2026-01-04T12:35:00-05:00",
        )
        registry_path.write_text(dormant_raw, encoding="utf-8")
        _git(repository, "add", registry_path.relative_to(repository).as_posix())
        _commit(
            repository,
            "Illegally restore dormant cohort",
            "2026-01-04T12:40:00-05:00",
        )

    _activate_registry(
        repository,
        freeze_commit=freeze_commit,
        activation_commit=activation_commit,
        initial_csv_sha256=sha256(initial_csv.encode()).hexdigest(),
        result_overrides=activation_result_overrides,
    )
    _git(repository, "add", "docs/experiments/registry.yaml")
    release_commit = _commit(
        repository,
        "Release active cohort",
        "2026-01-04T13:00:00-05:00",
    )
    if not release_after_snapshots:
        release_evidence = verify_live_release(
            repository,
            "V3_frozen_shadow_cohort",
        )
        assert release_evidence.evidence_commit == release_commit
        candidate_snapshots = [evaluated_snapshot, pending_snapshot]
        if third_snapshot is not None:
            candidate_snapshots.append(third_snapshot)
        for snapshot in candidate_snapshots:
            _add_release_metadata(snapshot, release_evidence, repository)
        _write_json(evaluated_path, evaluated_snapshot)
        _write_json(pending_path, pending_snapshot)
        if third_snapshot is not None:
            _write_json(
                repository
                / "predictions"
                / "2026-01-14__v3_boosting__v3.0.0.json",
                third_snapshot,
            )

    if immutable_registry_drift:
        registry_path = repository / "docs" / "experiments" / "registry.yaml"
        registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
        registration = next(
            item
            for item in registry["experiments"]
            if item["id"] == "V3_frozen_shadow_cohort"
        )
        registration["parameters"]["primary_alpha"] = 0.04
        registry_path.write_text(
            yaml.safe_dump(registry, sort_keys=False),
            encoding="utf-8",
        )
        _git(repository, "add", "docs/experiments/registry.yaml")
        _commit(
            repository,
            "Illegally change frozen primary alpha",
            "2026-01-04T14:00:00-05:00",
        )

    if frozen_path_drift:
        frozen_path.write_text("MODEL_SPEC = 'changed'\n", encoding="utf-8")
        _git(repository, "add", "frozen/model.py")
        _commit(
            repository,
            "Illegally change frozen model",
            "2026-01-04T15:00:00-05:00",
        )

    if not release_after_snapshots:
        _git(repository, "add", "predictions")
        _commit(
            repository,
            "Commit two pre-draw snapshots",
            "2026-01-05T13:00:00-05:00",
        )

    evaluated_draw = Draw(date(2026, 1, 7), (1, 2, 3, 4, 5, 6), 7)
    pending_draw = Draw(date(2026, 1, 10), (2, 8, 14, 20, 26, 32), 38)
    missing_draw = Draw(date(2026, 1, 14), (3, 9, 15, 21, 27, 33), 39)
    verified_draws = [activation_draw, evaluated_draw, pending_draw, missing_draw]
    data_path.write_text(_draw_csv(verified_draws), encoding="utf-8")
    evaluation = _evaluation_payload(
        evaluated_snapshot,
        evaluated_draw,
        verified_draws,
    )
    _write_json(
        repository
        / "evaluations"
        / "2026-01-07__v3_boosting__v3.0.0.json",
        evaluation,
    )
    if third_snapshot is not None:
        _write_json(
            repository
            / "evaluations"
            / "2026-01-10__v3_boosting__v3.0.0.json",
            _evaluation_payload(pending_snapshot, pending_draw, verified_draws),
        )
        _write_json(
            repository
            / "evaluations"
            / "2026-01-14__v3_boosting__v3.0.0.json",
            _evaluation_payload(third_snapshot, missing_draw, verified_draws),
        )
    actual_by_target = {
        evaluated_draw.draw_date: evaluated_draw,
        pending_draw.draw_date: pending_draw,
        missing_draw.draw_date: missing_draw,
    }
    for (target, model_name), comparison in comparison_snapshots.items():
        if omit_comparison_evaluation and model_name == "ensemble":
            continue
        actual = actual_by_target[target]
        comparison_evaluation = _evaluation_payload(
            comparison,
            actual,
            verified_draws,
        )
        if (
            invalid_comparison_metric
            and target == evaluated_draw.draw_date
            and model_name == "ensemble"
        ):
            comparison_evaluation["top_12_hits"] += 1
        _write_json(
            repository
            / "evaluations"
            / f"{target.isoformat()}__{model_name}__v1.0.0.json",
            comparison_evaluation,
        )
    _git(repository, "add", "data/processed/draws.csv", "evaluations")
    _commit(
        repository,
        "Commit verified outcomes and due evaluation",
        "2026-01-15T12:00:00-05:00",
    )
    return repository


def _commit_formal_terminal_transition(
    repository: Path,
    *,
    formal_decision: str,
) -> tuple[str, str]:
    registry_path = repository / "docs" / "experiments" / "registry.yaml"
    registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    registration = next(
        item
        for item in registry["experiments"]
        if item["id"] == "V3_frozen_shadow_cohort"
    )
    parameters = registration["parameters"]
    claim_path = repository / parameters["formal_look_claim"]
    claim_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(
        claim_path,
        {
            "schema_version": 1,
            "experiment_id": registration["id"],
            "kind": "formal_claim",
        },
    )
    _git(repository, "add", claim_path.relative_to(repository).as_posix())
    _commit(
        repository,
        "Commit formal claim",
        "2026-01-16T12:00:00-05:00",
    )

    attempt_path = repository / parameters["formal_look_attempt"]
    formal_path = repository / parameters["formal_look_json"]
    markdown_path = repository / parameters["formal_look_markdown"]
    _write_json(
        attempt_path,
        {
            "schema_version": 1,
            "experiment_id": registration["id"],
            "kind": "formal_attempt",
        },
    )
    markdown_path.write_text("# Immutable formal report\n", encoding="utf-8")
    _write_json(
        formal_path,
        {
            "schema_version": 1,
            "experiment_id": registration["id"],
            "model_name": registration["model_name"],
            "model_version": registration["model_version"],
            "decision": formal_decision,
            "gate_outcome": formal_decision,
            "formal_markdown_path": parameters["formal_look_markdown"],
        },
    )
    _git(
        repository,
        "add",
        attempt_path.relative_to(repository).as_posix(),
        formal_path.relative_to(repository).as_posix(),
        markdown_path.relative_to(repository).as_posix(),
    )
    report_commit = _commit(
        repository,
        "Commit formal report",
        "2026-01-17T12:00:00-05:00",
    )

    terminal_status, registry_decision = {
        "reject": ("closed_rejected", "reject"),
        "archive": ("closed_archived", "archive"),
        "eligible_for_reviewed_promotion": ("promoted", "promote"),
    }[formal_decision]
    registration["status"] = terminal_status
    registration["result"] = {
        "decision": registry_decision,
        "decided_on": date(2026, 1, 18),
        "implementation_commit": report_commit,
        "report_json": parameters["formal_look_json"],
        "report_markdown": parameters["formal_look_markdown"],
        "result_file": parameters["formal_look_markdown"],
        "historical_primary_signal_supported": False,
        "shadow_activation": "closed",
    }
    registration["prospective"]["status"] = "closed"
    registry_path.write_text(
        yaml.safe_dump(registry, sort_keys=False),
        encoding="utf-8",
    )
    _git(repository, "add", registry_path.relative_to(repository).as_posix())
    transition_commit = _commit(
        repository,
        "Review and close prospective cohort",
        "2026-01-18T12:00:00-05:00",
    )
    return report_commit, transition_commit


def _unactivated_repository(tmp_path: Path) -> Path:
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init")
    _git(repository, "config", "user.name", "Prospective Test")
    _git(repository, "config", "user.email", "prospective@example.test")
    _write_registry(repository, active=False)
    _git(repository, "add", "docs/experiments/registry.yaml")
    _git(repository, "commit", "-m", "Register inactive cohort")
    return repository


def test_audit_rejects_an_unactivated_registered_cohort(tmp_path: Path) -> None:
    repository = _unactivated_repository(tmp_path)

    with pytest.raises(ValueError, match="cohort must be active"):
        audit_registered_cohort(repository, "V3_frozen_shadow_cohort")


def test_audit_reports_evaluated_pending_and_missing_scheduled_targets(
    tmp_path: Path,
) -> None:
    repository = _active_repository_with_mixed_observations(tmp_path)

    aggregate = audit_registered_cohort(repository, "V3_frozen_shadow_cohort")

    assert [item.target_draw_date for item in aggregate.eligible_evaluated] == [
        date(2026, 1, 7)
    ]
    assert [item.target_draw_date for item in aggregate.pending] == [
        date(2026, 1, 10)
    ]
    assert [item.target_draw_date for item in aggregate.excluded] == [
        date(2026, 1, 14)
    ]


def test_audit_requires_frozen_v1_comparison_evidence_for_each_v3_snapshot(
    tmp_path: Path,
) -> None:
    repository = _active_repository_with_mixed_observations(
        tmp_path,
        omit_comparisons=True,
    )

    aggregate = audit_registered_cohort(repository, "V3_frozen_shadow_cohort")

    candidate_targets = {date(2026, 1, 7), date(2026, 1, 10)}
    excluded = {
        item.target_draw_date: item.reasons
        for item in aggregate.excluded
        if item.target_draw_date in candidate_targets
    }
    assert excluded.keys() == candidate_targets
    assert all(
        "missing_comparison_snapshot:ensemble:v1.0.0" in reasons
        and "missing_comparison_snapshot:random:v1.0.0" in reasons
        for reasons in excluded.values()
    )


def test_audit_keeps_revealed_candidate_pending_when_comparison_eval_is_missing(
    tmp_path: Path,
) -> None:
    repository = _active_repository_with_mixed_observations(
        tmp_path,
        omit_comparison_evaluation=True,
    )

    aggregate = audit_registered_cohort(repository, "V3_frozen_shadow_cohort")

    assert date(2026, 1, 7) in {
        item.target_draw_date for item in aggregate.pending
    }
    assert not aggregate.eligible_evaluated


def test_audit_rejects_comparison_role_probability_and_metric_mutations(
    tmp_path: Path,
) -> None:
    role_repository = _active_repository_with_mixed_observations(
        tmp_path / "role",
        comparison_role="shadow",
    )
    with pytest.raises(GitEvidenceError, match="snapshot role must be primary"):
        audit_registered_cohort(role_repository, "V3_frozen_shadow_cohort")

    probability_repository = _active_repository_with_mixed_observations(
        tmp_path / "probability",
        invalid_comparison_probability=True,
    )
    with pytest.raises(GitEvidenceError, match="probability contract is invalid"):
        audit_registered_cohort(probability_repository, "V3_frozen_shadow_cohort")

    metric_repository = _active_repository_with_mixed_observations(
        tmp_path / "metric",
        invalid_comparison_metric=True,
    )
    with pytest.raises(
        GitEvidenceError,
        match="comparison registered metric mismatch: top_12_hits",
    ):
        audit_registered_cohort(metric_repository, "V3_frozen_shadow_cohort")


def test_audit_replays_candidate_and_comparison_probabilities_from_frozen_history(
    tmp_path: Path,
) -> None:
    candidate_repository = _active_repository_with_mixed_observations(
        tmp_path / "candidate",
        valid_candidate_replay_mutation=True,
    )
    with pytest.raises(
        GitEvidenceError,
        match="probabilities do not match frozen replay: v3_boosting",
    ):
        audit_registered_cohort(candidate_repository, "V3_frozen_shadow_cohort")

    comparison_repository = _active_repository_with_mixed_observations(
        tmp_path / "comparison",
        valid_comparison_replay_mutation=True,
    )
    with pytest.raises(
        GitEvidenceError,
        match="probabilities do not match frozen replay: ensemble",
    ):
        audit_registered_cohort(comparison_repository, "V3_frozen_shadow_cohort")


def test_verify_live_release_returns_committed_release_and_manifest_evidence(
    tmp_path: Path,
) -> None:
    repository = _active_repository_with_mixed_observations(tmp_path)

    evidence = verify_live_release(repository, "V3_frozen_shadow_cohort")

    assert evidence.experiment_id == "V3_frozen_shadow_cohort"
    assert evidence.model_name == "v3_boosting"
    assert evidence.model_version == "v3.0.0"
    assert evidence.evidence_commit == _git(repository, "rev-parse", "HEAD")
    assert _git(
        repository,
        "show",
        "-s",
        "--format=%s",
        evidence.release_commit,
    ) == "Release active cohort"
    assert evidence.frozen_path_sha256.keys() == {
        "config.yaml",
        "frozen/model.py",
        "requirements-live.lock",
    }
    assert len(evidence.frozen_manifest_sha256) == 64


@pytest.mark.parametrize(
    "formal_decision",
    ["reject", "archive", "eligible_for_reviewed_promotion"],
)
def test_terminal_transition_preserves_release_identity_and_binds_formal_evidence(
    tmp_path: Path,
    formal_decision: str,
) -> None:
    repository = _active_repository_with_mixed_observations(tmp_path)
    active = verify_live_release(repository, "V3_frozen_shadow_cohort")
    report_commit, transition_commit = _commit_formal_terminal_transition(
        repository,
        formal_decision=formal_decision,
    )

    evidence = prospective_module._derive_registry_release(
        repository,
        "V3_frozen_shadow_cohort",
        freeze_commit=active.freeze_commit,
        activation_commit=active.activation_commit,
    )

    assert evidence.release_commit == active.release_commit
    assert evidence.active_registration_digest == (
        prospective_module._mapping_digest(
            prospective_module._active_registration_view(
                prospective_module._registry_row_at(
                    repository,
                    active.release_commit,
                    "V3_frozen_shadow_cohort",
                )
            )
        )
    )
    assert evidence.formal_result_commit == report_commit
    assert evidence.terminal_transition_commit == transition_commit
    with pytest.raises(ValueError, match="active cohort"):
        verify_live_release(repository, "V3_frozen_shadow_cohort")


def test_terminal_registry_result_cannot_be_changed_or_reopened(tmp_path: Path) -> None:
    changed = _active_repository_with_mixed_observations(tmp_path / "changed")
    active = verify_live_release(changed, "V3_frozen_shadow_cohort")
    _commit_formal_terminal_transition(changed, formal_decision="reject")
    registry_path = changed / "docs" / "experiments" / "registry.yaml"
    registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    registration = next(
        item
        for item in registry["experiments"]
        if item["id"] == "V3_frozen_shadow_cohort"
    )
    registration["result"]["result_file"] = "reports/prospective/replacement.md"
    registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
    _git(changed, "add", registry_path.relative_to(changed).as_posix())
    _commit(changed, "Illegally replace terminal result", "2026-01-19T12:00:00-05:00")
    with pytest.raises(GitEvidenceError, match="terminal registry identity changed"):
        prospective_module._derive_registry_release(
            changed,
            "V3_frozen_shadow_cohort",
            freeze_commit=active.freeze_commit,
            activation_commit=active.activation_commit,
        )

    reopened = _active_repository_with_mixed_observations(tmp_path / "reopened")
    active = verify_live_release(reopened, "V3_frozen_shadow_cohort")
    _commit_formal_terminal_transition(reopened, formal_decision="archive")
    registry_path = reopened / "docs" / "experiments" / "registry.yaml"
    registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    registration = next(
        item
        for item in registry["experiments"]
        if item["id"] == "V3_frozen_shadow_cohort"
    )
    registration["status"] = "prospective_shadow"
    registration["prospective"]["status"] = "active"
    registration["result"] = {
        "decision": "continue_shadow",
        "decided_on": date(2026, 1, 4),
        "implementation_commit": active.freeze_commit,
        "report_json": registration["parameters"]["activation_anchor_json"],
        "report_markdown": registration["parameters"]["activation_anchor_markdown"],
        "result_file": registration["parameters"]["activation_anchor_claim"],
        "historical_primary_signal_supported": False,
        "shadow_activation": "active",
    }
    registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
    _git(reopened, "add", registry_path.relative_to(reopened).as_posix())
    _commit(reopened, "Illegally reopen terminal cohort", "2026-01-19T12:00:00-05:00")
    with pytest.raises(GitEvidenceError, match="terminal registry identity changed"):
        prospective_module._derive_registry_release(
            reopened,
            "V3_frozen_shadow_cohort",
            freeze_commit=active.freeze_commit,
            activation_commit=active.activation_commit,
        )


def test_release_rejects_transient_terminal_state_before_activation(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        GitEvidenceError,
        match="dormant registry identity changed before release",
    ):
        _active_repository_with_mixed_observations(
            tmp_path,
            pre_release_terminal_restore=True,
        )


def test_closed_cohort_audit_replays_snapshots_from_original_active_release(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _active_repository_with_mixed_observations(tmp_path)
    _commit_formal_terminal_transition(repository, formal_decision="reject")
    monkeypatch.setattr(
        prospective_module,
        "_aggregate_with_committed_formal_look",
        lambda _repository, registration, assessments, **_kwargs: (
            prospective_module.aggregate_prospective_cohort(
                registration,
                assessments,
            )
        ),
    )

    aggregate = audit_registered_cohort(repository, "V3_frozen_shadow_cohort")

    assert aggregate.status == "collecting"
    assert [item.target_draw_date for item in aggregate.eligible_evaluated] == [
        date(2026, 1, 7)
    ]


def test_closed_audit_uses_terminal_data_boundary_not_later_draws(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _active_repository_with_mixed_observations(tmp_path)
    _commit_formal_terminal_transition(repository, formal_decision="reject")
    data_path = repository / "data" / "processed" / "draws.csv"
    future = Draw(date(2026, 1, 17), (4, 10, 16, 22, 28, 34), 40)
    values = ",".join(str(number) for number in future.numbers)
    data_path.write_text(
        data_path.read_text(encoding="utf-8")
        + f"{future.draw_date.isoformat()},{values},{future.bonus}\n",
        encoding="utf-8",
    )
    _git(repository, "add", data_path.relative_to(repository).as_posix())
    _commit(repository, "Append post-terminal draw", "2026-01-18T20:00:00-05:00")
    monkeypatch.setattr(
        prospective_module,
        "_aggregate_with_committed_formal_look",
        lambda _repository, registration, assessments, **_kwargs: (
            prospective_module.aggregate_prospective_cohort(
                registration,
                assessments,
            )
        ),
    )

    aggregate = audit_registered_cohort(repository, "V3_frozen_shadow_cohort")

    audited_targets = {
        item.target_draw_date
        for lane in (
            aggregate.eligible_evaluated,
            aggregate.pending,
            aggregate.excluded,
        )
        for item in lane
    }
    assert date(2026, 1, 17) not in audited_targets


def test_closed_audit_requires_terminal_checkout_after_frozen_code_evolution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _active_repository_with_mixed_observations(tmp_path)
    _, terminal_commit = _commit_formal_terminal_transition(
        repository,
        formal_decision="archive",
    )
    frozen_path = repository / "frozen" / "model.py"
    frozen_path.write_text("MODEL_SPEC = 'next-version'\n", encoding="utf-8")
    _git(repository, "add", frozen_path.relative_to(repository).as_posix())
    _commit(repository, "Develop a later model version", "2026-01-19T12:00:00-05:00")
    monkeypatch.setattr(
        prospective_module,
        "_aggregate_with_committed_formal_look",
        lambda _repository, registration, assessments, **_kwargs: (
            prospective_module.aggregate_prospective_cohort(
                registration,
                assessments,
            )
        ),
    )

    with pytest.raises(
        GitEvidenceError,
        match="requires checkout of the terminal transition commit",
    ):
        audit_registered_cohort(repository, "V3_frozen_shadow_cohort")

    _git(repository, "switch", "--detach", terminal_commit)
    aggregate = audit_registered_cohort(repository, "V3_frozen_shadow_cohort")

    assert aggregate.status == "collecting"


def test_closed_audit_rejects_contract_valid_forged_candidate_probabilities(
    tmp_path: Path,
) -> None:
    repository = _active_repository_with_mixed_observations(
        tmp_path,
        valid_candidate_replay_mutation=True,
    )
    _commit_formal_terminal_transition(repository, formal_decision="reject")

    with pytest.raises(
        GitEvidenceError,
        match="probabilities do not match frozen replay: v3_boosting",
    ):
        audit_registered_cohort(repository, "V3_frozen_shadow_cohort")


@pytest.mark.parametrize("directory", ["predictions", "evaluations"])
def test_closed_audit_rejects_post_terminal_candidate_evidence(
    tmp_path: Path,
    directory: str,
) -> None:
    repository = _active_repository_with_mixed_observations(tmp_path)
    _commit_formal_terminal_transition(repository, formal_decision="reject")
    path = repository / directory / (
        "2026-01-17__v3_boosting__v3.0.0.json"
    )
    _write_json(path, _prediction_payload(date(2026, 1, 17)))
    _git(repository, "add", path.relative_to(repository).as_posix())
    _commit(
        repository,
        "Illegally add post-terminal cohort evidence",
        "2026-01-19T12:00:00-05:00",
    )

    with pytest.raises(GitEvidenceError, match="post-terminal candidate evidence"):
        audit_registered_cohort(repository, "V3_frozen_shadow_cohort")


def test_closed_formal_record_must_match_terminal_result_and_report_commit() -> None:
    registration = SimpleNamespace(
        prospective=SimpleNamespace(status="closed"),
        result=SimpleNamespace(decision="reject"),
    )
    release = prospective_module._RegistryReleaseEvidence(
        release_commit="a" * 40,
        immutable_registration_digest="b" * 64,
        active_registration_digest="c" * 64,
        activation_anchor_sha256="d" * 64,
        formal_result_commit="e" * 40,
        terminal_transition_commit="f" * 40,
    )
    matching = SimpleNamespace(record_commit="e" * 40, decision="reject")

    prospective_module._verify_terminal_formal_record(
        registration,
        release,
        matching,
    )

    with pytest.raises(GitEvidenceError, match="verified formal look"):
        prospective_module._verify_terminal_formal_record(
            registration,
            release,
            SimpleNamespace(
                record_commit="e" * 40,
                decision="eligible_for_reviewed_promotion",
            ),
        )
    with pytest.raises(GitEvidenceError, match="verified formal look"):
        prospective_module._verify_terminal_formal_record(
            registration,
            replace(release, formal_result_commit="0" * 40),
            matching,
        )


def test_verify_live_release_rejects_python_and_dependency_runtime_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _active_repository_with_mixed_observations(tmp_path)

    monkeypatch.setattr(
        prospective_module,
        "_runtime_python_identity",
        lambda: ("CPython", "3.13"),
    )
    with pytest.raises(GitEvidenceError, match="Python runtime"):
        verify_live_release(repository, "V3_frozen_shadow_cohort")

    monkeypatch.setattr(
        prospective_module,
        "_runtime_python_identity",
        lambda: ("CPython", "3.12"),
    )
    installed = prospective_module._installed_distribution_version
    monkeypatch.setattr(
        prospective_module,
        "_installed_distribution_version",
        lambda name: "0.0.0" if name == "numpy" else installed(name),
    )
    with pytest.raises(GitEvidenceError, match="dependency version mismatch: numpy"):
        verify_live_release(repository, "V3_frozen_shadow_cohort")


@pytest.mark.parametrize(
    "result_overrides",
    [
        {"implementation_commit": "f" * 40},
        {"historical_primary_signal_supported": True},
    ],
)
def test_activation_result_binds_freeze_and_disclaims_historical_signal(
    tmp_path: Path,
    result_overrides: dict,
) -> None:
    with pytest.raises(
        GitEvidenceError,
        match="release result does not cite the activation artifacts",
    ):
        _active_repository_with_mixed_observations(
            tmp_path,
            activation_result_overrides=result_overrides,
        )


def test_audit_excludes_a_snapshot_with_the_wrong_registered_version(
    tmp_path: Path,
) -> None:
    repository = _active_repository_with_mixed_observations(
        tmp_path,
        pending_model_version="v3.0.1",
    )

    aggregate = audit_registered_cohort(repository, "V3_frozen_shadow_cohort")

    wrong_version = next(
        item
        for item in aggregate.excluded
        if item.target_draw_date == date(2026, 1, 10)
    )
    assert "wrong_model_version" in wrong_version.reasons


def test_audit_fails_closed_when_a_committed_snapshot_is_tampered(
    tmp_path: Path,
) -> None:
    repository = _active_repository_with_mixed_observations(tmp_path)
    snapshot_path = (
        repository
        / "predictions"
        / "2026-01-07__v3_boosting__v3.0.0.json"
    )
    snapshot_path.write_text("{}\n", encoding="utf-8")

    with pytest.raises(GitEvidenceError, match="differs from committed Git state"):
        audit_registered_cohort(repository, "V3_frozen_shadow_cohort")


def test_audit_rejects_snapshots_committed_before_the_registry_release(
    tmp_path: Path,
) -> None:
    repository = _active_repository_with_mixed_observations(
        tmp_path,
        release_after_snapshots=True,
    )

    with pytest.raises(GitEvidenceError, match="release commit.*strict ancestor"):
        audit_registered_cohort(repository, "V3_frozen_shadow_cohort")


def test_audit_fails_closed_when_the_frozen_registry_specification_drifts(
    tmp_path: Path,
) -> None:
    repository = _active_repository_with_mixed_observations(
        tmp_path,
        immutable_registry_drift=True,
    )

    with pytest.raises(
        GitEvidenceError,
        match="immutable registry specification changed after freeze",
    ):
        audit_registered_cohort(repository, "V3_frozen_shadow_cohort")


def test_audit_fails_closed_when_a_frozen_implementation_path_drifts(
    tmp_path: Path,
) -> None:
    repository = _active_repository_with_mixed_observations(
        tmp_path,
        frozen_path_drift=True,
    )

    with pytest.raises(GitEvidenceError, match="frozen path frozen/model.py changed"):
        audit_registered_cohort(repository, "V3_frozen_shadow_cohort")


def test_audit_rejects_dirty_frozen_worktree_and_precohort_trace(
    tmp_path: Path,
) -> None:
    dirty_repository = _active_repository_with_mixed_observations(tmp_path / "dirty")
    (dirty_repository / "frozen" / "model.py").write_text(
        "MODEL_SPEC = 'dirty'\n",
        encoding="utf-8",
    )
    with pytest.raises(GitEvidenceError, match="dirty frozen runtime path"):
        audit_registered_cohort(dirty_repository, "V3_frozen_shadow_cohort")

    trace_repository = _active_repository_with_mixed_observations(tmp_path / "trace")
    trace = trace_repository / "predictions" / (
        "2025-12-31__v3_boosting__v3.0.0.json"
    )
    _write_json(trace, _prediction_payload(date(2025, 12, 31)))
    _git(trace_repository, "add", trace.relative_to(trace_repository).as_posix())
    _commit(
        trace_repository,
        "Commit prohibited precohort trace",
        "2026-01-16T12:00:00-05:00",
    )
    with pytest.raises(GitEvidenceError, match="predates the prospective cohort"):
        audit_registered_cohort(trace_repository, "V3_frozen_shadow_cohort")


def test_audit_excludes_snapshot_below_registered_minimum_history(
    tmp_path: Path,
) -> None:
    repository = _active_repository_with_mixed_observations(
        tmp_path,
        minimum_history_draws=2,
    )

    aggregate = audit_registered_cohort(repository, "V3_frozen_shadow_cohort")

    item = next(
        assessment
        for assessment in aggregate.excluded
        if assessment.target_draw_date == date(2026, 1, 7)
    )
    assert item.reasons == ("insufficient_registered_history",)


def test_cli_reports_only_cohort_progress_not_interim_performance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import lotto649.cli as cli

    calls: list[tuple[Path, str]] = []

    def fake_audit(repository: Path, experiment_id: str) -> SimpleNamespace:
        calls.append((repository, experiment_id))
        return SimpleNamespace(
            status="collecting",
            eligible_evaluated=(object(),),
            pending=(object(), object()),
            excluded=(object(),),
            checkpoint=(),
            formal_look_count=0,
        )

    monkeypatch.setattr(cli, "audit_registered_cohort", fake_audit, raising=False)
    monkeypatch.setattr(cli, "load_config", lambda _path: {"_root": str(tmp_path)})
    monkeypatch.setattr(
        cli,
        "load_experiment_registry",
        lambda _path: SimpleNamespace(
            get=lambda _experiment_id: SimpleNamespace(
                prospective=SimpleNamespace(minimum_eligible_draws=208)
            )
        ),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "lotto649",
            "prospective-audit",
            "--experiment",
            "V3_frozen_shadow_cohort",
        ],
    )

    cli.main()

    assert calls == [(tmp_path, "V3_frozen_shadow_cohort")]
    assert json.loads(capsys.readouterr().out) == {
        "checkpoint_count": 0,
        "eligible_evaluated_count": 1,
        "excluded_count": 1,
        "experiment_id": "V3_frozen_shadow_cohort",
        "formal_look_count": 0,
        "pending_count": 2,
        "remaining_to_checkpoint": 207,
        "status": "collecting",
    }


def _fake_ready_aggregate(item=None, *, status: str = "ready"):
    checkpoint = tuple([item or SimpleNamespace(target_draw_date=date(2026, 1, 7))] * 208)
    extra = (
        SimpleNamespace(target_draw_date=date(2028, 1, 1)),
    ) if status == "overdue" else ()
    return prospective_module.CohortAggregate._create(
        status=status,
        eligible_evaluated=(
            checkpoint + extra if status != "collecting" else ()
        ),
        pending=(),
        excluded=(),
        checkpoint=checkpoint if status in {"ready", "overdue"} else (),
        first_half=checkpoint[:104] if status in {"ready", "overdue"} else (),
        second_half=checkpoint[104:] if status in {"ready", "overdue"} else (),
        extra_evaluated=extra,
        checkpoint_digest="a" * 64 if status in {"ready", "overdue"} else None,
        formal_look_count=0,
    )


def test_formal_exact_tail_bootstrap_and_gate_decision_are_deterministic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    denominator = math.comb(49, 6)
    one_draw = [
        math.comb(12, hits) * math.comb(37, 6 - hits) / denominator
        for hits in range(7)
    ]
    independent_two_draw_tail = sum(
        one_draw[left] * one_draw[right]
        for left in range(7)
        for right in range(7)
        if left + right >= 5
    )
    assert prospective_module._exact_top12_upper_tail(0, 2) == 1.0
    assert prospective_module._exact_top12_upper_tail(12, 2) == pytest.approx(
        one_draw[6] ** 2
    )
    assert prospective_module._exact_top12_upper_tail(5, 2) == pytest.approx(
        independent_two_draw_tail
    )
    hits = [index % 4 for index in range(208)]
    assert prospective_module._bootstrap_top12_lift(
        hits,
        resamples=10_000,
        seed=649,
    ) == prospective_module._bootstrap_top12_lift(
        hits,
        resamples=10_000,
        seed=649,
    )

    fair_brier, fair_log_loss = prospective_module._fair_constant_scores()

    def rows(top12: int) -> tuple[dict, ...]:
        return tuple(
            {
                "final_6_hits": 0,
                "top_6_hits": 1,
                "top_12_hits": top12,
                "top_18_hits": 2,
                "brier_score": fair_brier,
                "log_loss": fair_log_loss,
                "mean_actual_rank": 25.0,
            }
            for _ in range(208)
        )

    registration = prospective_module.load_experiment_registry(
        ROOT / "docs" / "experiments" / "registry.yaml"
    ).get("V3_frozen_shadow_cohort")
    aggregate = _fake_ready_aggregate()
    claim = SimpleNamespace(
        path=registration.parameters["formal_look_claim"],
        raw_sha256="b" * 64,
        first_commit_sha="c" * 40,
    )
    monkeypatch.setattr(
        prospective_module,
        "_formal_rows",
        lambda *_args, **_kwargs: {
            "v3_boosting": rows(2),
            "ensemble": rows(1),
            "random": rows(1),
        },
    )
    positive = prospective_module._compute_formal_look_from_ready(
        ROOT,
        registration,
        aggregate,
        claim_evidence=claim,
        attempt_path=registration.parameters["formal_look_attempt"],
        attempt_sha256="d" * 64,
        markdown_path=registration.parameters["formal_look_markdown"],
        markdown_sha256="",
    )
    assert tuple(positive.gates) == tuple(
        registration.parameters["formal_gate_keys"]
    )
    assert all(positive.gates.values())
    assert positive.decision == positive.gate_outcome == (
        "eligible_for_reviewed_promotion"
    )
    assert positive.schema_version == 1

    monkeypatch.setattr(
        prospective_module,
        "_formal_rows",
        lambda *_args, **_kwargs: {
            "v3_boosting": rows(1),
            "ensemble": rows(2),
            "random": rows(1),
        },
    )
    negative = prospective_module._compute_formal_look_from_ready(
        ROOT,
        registration,
        aggregate,
        claim_evidence=claim,
        attempt_path=registration.parameters["formal_look_attempt"],
        attempt_sha256="d" * 64,
        markdown_path=registration.parameters["formal_look_markdown"],
        markdown_sha256="",
    )
    assert not negative.all_gates_passed
    assert negative.decision == negative.gate_outcome == "reject"

    monkeypatch.setattr(
        prospective_module,
        "_formal_rows",
        lambda *_args, **_kwargs: {
            "v3_boosting": rows(2),
            "ensemble": rows(1),
            "random": rows(2),
        },
    )
    invalid = prospective_module._compute_formal_look_from_ready(
        ROOT,
        registration,
        aggregate,
        claim_evidence=claim,
        attempt_path=registration.parameters["formal_look_attempt"],
        attempt_sha256="d" * 64,
        markdown_path=registration.parameters["formal_look_markdown"],
        markdown_sha256="",
    )
    assert not invalid.gates["random_control_null_aggregate_and_halves"]
    assert invalid.decision == invalid.gate_outcome == "archive"


def test_formal_claim_commit_attempt_and_single_publication_flow(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _active_repository_with_mixed_observations(tmp_path)
    real = audit_registered_cohort(repository, "V3_frozen_shadow_cohort")
    item = real.eligible_evaluated[0]
    ready = _fake_ready_aggregate(item)
    monkeypatch.setattr(
        prospective_module,
        "audit_registered_cohort",
        lambda *_args, **_kwargs: ready,
    )

    claim_path = prospective_module.claim_registered_formal_look(
        repository,
        "V3_frozen_shadow_cohort",
    )
    _git(repository, "add", claim_path.relative_to(repository).as_posix())
    _commit(
        repository,
        "Commit performance-blind formal claim",
        "2026-01-16T12:00:00-05:00",
    )

    def fake_compute(
        _root,
        registration,
        aggregate,
        *,
        claim_evidence,
        attempt_path,
        attempt_sha256,
        markdown_path,
        markdown_sha256,
    ):
        gates = {key: False for key in registration.parameters["formal_gate_keys"]}
        return prospective_module.FormalLookComputation(
            schema_version=1,
            experiment_id=registration.experiment_id,
            model_name=registration.model_name,
            model_version=registration.model_version,
            checkpoint_digest=aggregate.checkpoint_digest,
            eligible_evaluated_count=208,
            scopes={"synthetic": {}},
            candidate_minus_v1_top12={"aggregate_208": 0.0},
            gates=gates,
            all_gates_passed=False,
            decision="reject",
            gate_outcome="reject",
            formal_claim_path=claim_evidence.path,
            formal_claim_sha256=claim_evidence.raw_sha256,
            formal_claim_commit=claim_evidence.first_commit_sha,
            formal_attempt_path=attempt_path,
            formal_attempt_sha256=attempt_sha256,
            formal_markdown_path=markdown_path,
            formal_markdown_sha256=markdown_sha256,
            procedures={"formal_look_count": 1},
        )

    monkeypatch.setattr(
        prospective_module,
        "_compute_formal_look_from_ready",
        fake_compute,
    )
    result = prospective_module.run_registered_formal_look(
        repository,
        "V3_frozen_shadow_cohort",
    )
    registration = prospective_module.load_experiment_registry(
        repository / "docs" / "experiments" / "registry.yaml"
    ).get("V3_frozen_shadow_cohort")
    for key in ("formal_look_attempt", "formal_look_json", "formal_look_markdown"):
        assert (repository / registration.parameters[key]).is_file()
    assert result.decision == result.gate_outcome == "reject"
    assert result.formal_markdown_sha256 == sha256(
        (repository / registration.parameters["formal_look_markdown"]).read_bytes()
    ).hexdigest()
    with pytest.raises(RuntimeError, match="already used"):
        prospective_module.run_registered_formal_look(
            repository,
            "V3_frozen_shadow_cohort",
        )


def test_formal_rows_lock_all_three_identity_payloads_after_audit(
    tmp_path: Path,
) -> None:
    repository = _active_repository_with_mixed_observations(tmp_path)
    registration = prospective_module.load_experiment_registry(
        repository / prospective_module.REGISTRY_PATH
    ).get("V3_frozen_shadow_cohort")
    audited = audit_registered_cohort(repository, registration.experiment_id)
    item = audited.eligible_evaluated[0]

    claim_path = repository / registration.parameters["formal_look_claim"]
    _write_json(claim_path, {"kind": "synthetic immutable claim"})
    _git(repository, "add", claim_path.relative_to(repository).as_posix())
    claim_commit = _commit(
        repository,
        "Commit performance-blind formal claim",
        "2026-01-16T12:00:00-05:00",
    )
    claim_evidence = prospective_module.GitFileEvidence.from_repository(
        repository,
        claim_path,
        freeze_commit=registration.prospective.freeze_commit,
        activation_commit=registration.prospective.activation_commit,
    )
    comparison_evidence = tuple(
        replace(evidence, verified_at_commit=claim_commit)
        for evidence in item.comparison_evidence
    )
    locked_item = prospective_module.CohortAssessment._create(
        status=item.status,
        reasons=item.reasons,
        snapshot_digest=item.snapshot_digest,
        target_draw_date=item.target_draw_date,
        evaluation_digest=item.evaluation_digest,
        snapshot_path=item.snapshot_path,
        evaluation_path=item.evaluation_path,
        snapshot_git_evidence=item.snapshot_git_evidence,
        evaluation_git_evidence=item.evaluation_git_evidence,
        snapshot_frozen_path_evidence=item.snapshot_frozen_path_evidence,
        comparison_evidence=comparison_evidence,
    )
    aggregate = prospective_module.CohortAggregate._create(
        status="ready",
        eligible_evaluated=(locked_item,),
        pending=(),
        excluded=(),
        checkpoint=(locked_item,),
        first_half=(locked_item,),
        second_half=(),
        extra_evaluated=(),
        checkpoint_digest="a" * 64,
        formal_look_count=0,
    )

    target = locked_item.target_draw_date
    assert target is not None
    for model_name, model_version in (
        (registration.model_name, registration.model_version),
        ("ensemble", "v1.0.0"),
        ("random", "v1.0.0"),
    ):
        filename = f"{target.isoformat()}__{model_name}__{model_version}.json"
        snapshot_path = repository / "predictions" / filename
        evaluation_path = repository / "evaluations" / filename
        original_snapshot = snapshot_path.read_bytes()
        original_evaluation = evaluation_path.read_bytes()
        snapshot = json.loads(original_snapshot)
        evaluation = json.loads(original_evaluation)
        _mutate_prediction_but_keep_contract(snapshot)
        actual = Draw(
            target,
            tuple(evaluation["actual"]),
            evaluation["bonus"],
        )
        replacement = _evaluation_payload(snapshot, actual, [actual])
        replacement["verified_data_draw_count"] = evaluation[
            "verified_data_draw_count"
        ]
        replacement["verified_data_history_through"] = evaluation[
            "verified_data_history_through"
        ]
        _write_json(snapshot_path, snapshot)
        _write_json(evaluation_path, replacement)

        with pytest.raises(
            GitEvidenceError,
            match="changed after the immutable audit",
        ):
            prospective_module._formal_rows(
                repository,
                registration,
                aggregate,
                claim_evidence=claim_evidence,
            )

        snapshot_path.write_bytes(original_snapshot)
        evaluation_path.write_bytes(original_evaluation)


def test_formal_runner_rejects_claim_commit_that_includes_another_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _active_repository_with_mixed_observations(tmp_path)
    real = audit_registered_cohort(repository, "V3_frozen_shadow_cohort")
    ready = _fake_ready_aggregate(real.eligible_evaluated[0])
    monkeypatch.setattr(
        prospective_module,
        "audit_registered_cohort",
        lambda *_args, **_kwargs: ready,
    )
    claim = prospective_module.claim_registered_formal_look(
        repository,
        "V3_frozen_shadow_cohort",
    )
    extra = repository / "reports" / "prospective" / "unrelated.txt"
    extra.write_text("must not share the claim commit\n", encoding="utf-8")
    _git(
        repository,
        "add",
        claim.relative_to(repository).as_posix(),
        extra.relative_to(repository).as_posix(),
    )
    _commit(
        repository,
        "Illegally combine formal claim and unrelated change",
        "2026-01-16T12:00:00-05:00",
    )
    with pytest.raises(GitEvidenceError, match="claim commit must change only"):
        prospective_module.run_registered_formal_look(
            repository,
            "V3_frozen_shadow_cohort",
        )


def test_formal_report_pair_rolls_back_and_cleans_stages_on_fsync_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "reports" / "prospective"
    output.mkdir(parents=True)
    calls = 0
    original = prospective_module._fsync_directory

    def fail_publication_fsync(directory: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 3:
            raise OSError("synthetic directory fsync failure")
        original(directory)

    monkeypatch.setattr(
        prospective_module,
        "_fsync_directory",
        fail_publication_fsync,
    )
    with pytest.raises(OSError, match="synthetic directory fsync failure"):
        prospective_module._publish_formal_report_pair(
            tmp_path,
            json_path="reports/prospective/formal.json",
            json_raw=b"{}\n",
            markdown_path="reports/prospective/formal.md",
            markdown_raw=b"# Formal\n",
        )
    assert not (output / "formal.json").exists()
    assert not (output / "formal.md").exists()
    assert not (output / "formal.json.stage").exists()
    assert not (output / "formal.md.stage").exists()


def test_formal_report_commit_point_survives_cleanup_fsync_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "reports" / "prospective"
    output.mkdir(parents=True)
    calls = 0
    original = prospective_module._fsync_directory

    def fail_cleanup_fsync(directory: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 4:
            raise OSError("synthetic post-commit cleanup fsync failure")
        original(directory)

    monkeypatch.setattr(
        prospective_module,
        "_fsync_directory",
        fail_cleanup_fsync,
    )
    with pytest.warns(RuntimeWarning, match="published; cleanup fsync failed"):
        prospective_module._publish_formal_report_pair(
            tmp_path,
            json_path="reports/prospective/formal.json",
            json_raw=b"{}\n",
            markdown_path="reports/prospective/formal.md",
            markdown_raw=b"# Formal\n",
        )
    assert (output / "formal.json").read_bytes() == b"{}\n"
    assert (output / "formal.md").read_bytes() == b"# Formal\n"


def test_audit_fails_closed_for_incomplete_or_deleted_formal_artifacts(
    tmp_path: Path,
) -> None:
    incomplete = _active_repository_with_mixed_observations(tmp_path / "incomplete")
    registration = prospective_module.load_experiment_registry(
        incomplete / "docs" / "experiments" / "registry.yaml"
    ).get("V3_frozen_shadow_cohort")
    _write_json(
        incomplete / registration.parameters["formal_look_attempt"],
        {"kind": "consumed_attempt"},
    )
    with pytest.raises(GitEvidenceError, match="artifact set is incomplete"):
        audit_registered_cohort(incomplete, "V3_frozen_shadow_cohort")

    deleted = _active_repository_with_mixed_observations(tmp_path / "deleted")
    registration = prospective_module.load_experiment_registry(
        deleted / "docs" / "experiments" / "registry.yaml"
    ).get("V3_frozen_shadow_cohort")
    claim = deleted / registration.parameters["formal_look_claim"]
    _write_json(claim, {"kind": "historical_claim"})
    _git(deleted, "add", claim.relative_to(deleted).as_posix())
    _commit(
        deleted,
        "Commit historical formal claim",
        "2026-01-16T12:00:00-05:00",
    )
    claim.unlink()
    _git(deleted, "add", claim.relative_to(deleted).as_posix())
    _commit(
        deleted,
        "Delete prohibited formal claim",
        "2026-01-16T13:00:00-05:00",
    )
    with pytest.raises(GitEvidenceError, match="formal-look evidence was deleted"):
        audit_registered_cohort(deleted, "V3_frozen_shadow_cohort")


def test_committed_formal_report_must_match_frozen_numeric_recomputation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registration = prospective_module.load_experiment_registry(
        ROOT / "docs" / "experiments" / "registry.yaml"
    ).get("V3_frozen_shadow_cohort")
    claim_path, attempt_path, json_path, markdown_path = (
        registration.parameters[key]
        for key in (
            "formal_look_claim",
            "formal_look_attempt",
            "formal_look_json",
            "formal_look_markdown",
        )
    )
    claim_raw = b'{"kind":"claim"}\n'
    attempt_raw = b'{"kind":"attempt"}\n'
    (tmp_path / claim_path).parent.mkdir(parents=True)
    (tmp_path / claim_path).write_bytes(claim_raw)
    (tmp_path / attempt_path).write_bytes(attempt_raw)
    ready = _fake_ready_aggregate()
    claim_evidence = SimpleNamespace(
        path=claim_path,
        raw_sha256=sha256(claim_raw).hexdigest(),
        first_commit_sha="c" * 40,
    )
    gates = {key: False for key in registration.parameters["formal_gate_keys"]}
    expected = prospective_module.FormalLookComputation(
        schema_version=1,
        experiment_id=registration.experiment_id,
        model_name=registration.model_name,
        model_version=registration.model_version,
        checkpoint_digest=ready.checkpoint_digest,
        eligible_evaluated_count=208,
        scopes={"aggregate_208": {"v3_boosting": {"avg_top12_hits": 1.0}}},
        candidate_minus_v1_top12={"aggregate_208": 0.0},
        gates=gates,
        all_gates_passed=False,
        decision="reject",
        gate_outcome="reject",
        formal_claim_path=claim_path,
        formal_claim_sha256=claim_evidence.raw_sha256,
        formal_claim_commit=claim_evidence.first_commit_sha,
        formal_attempt_path=attempt_path,
        formal_attempt_sha256=sha256(attempt_raw).hexdigest(),
        formal_markdown_path=markdown_path,
        formal_markdown_sha256="",
        procedures={"formal_look_count": 1},
    )
    markdown = prospective_module._formal_markdown(expected)
    expected = replace(
        expected,
        formal_markdown_sha256=sha256(markdown).hexdigest(),
    )
    forged = expected.to_json_dict()
    forged["scopes"] = {"forged": {}}
    _write_json(tmp_path / json_path, forged)
    (tmp_path / markdown_path).write_bytes(markdown)

    monkeypatch.setattr(
        prospective_module,
        "aggregate_prospective_cohort",
        lambda *_args, **_kwargs: ready,
    )
    monkeypatch.setattr(
        prospective_module,
        "_path_has_git_history",
        lambda *_args: True,
    )
    monkeypatch.setattr(
        prospective_module,
        "FormalLookRecord",
        SimpleNamespace(
            from_repository=lambda *_args: SimpleNamespace(record_commit="e" * 40)
        ),
    )
    monkeypatch.setattr(
        prospective_module,
        "_commit_changed_paths",
        lambda *_args: tuple(sorted((attempt_path, json_path, markdown_path))),
    )
    monkeypatch.setattr(
        prospective_module,
        "GitFileEvidence",
        SimpleNamespace(from_repository=lambda *_args, **_kwargs: claim_evidence),
    )
    monkeypatch.setattr(
        prospective_module,
        "_compute_formal_look_from_ready",
        lambda *_args, **_kwargs: replace(expected, formal_markdown_sha256=""),
    )
    with pytest.raises(GitEvidenceError, match="frozen recomputation"):
        prospective_module._aggregate_with_committed_formal_look(
            tmp_path,
            registration,
            (),
        )


@pytest.mark.parametrize("status", ["collecting", "overdue"])
def test_formal_claim_rejects_early_and_209th_states(status: str) -> None:
    aggregate = _fake_ready_aggregate(status=status)
    if status == "overdue":
        assert len(aggregate.eligible_evaluated) == 209
    with pytest.raises(RuntimeError, match="exact ready 208-draw checkpoint"):
        prospective_module._require_exact_ready_checkpoint(aggregate)


def test_audit_marks_the_first_post_checkpoint_evaluation_overdue(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _active_repository_with_mixed_observations(
        tmp_path,
        include_third_evaluated=True,
    )
    registration = prospective_module.load_experiment_registry(
        repository / "docs" / "experiments" / "registry.yaml"
    ).get("V3_frozen_shadow_cohort")
    small_cohort = object.__new__(type(registration.prospective))
    for field_name in registration.prospective.__dataclass_fields__:
        object.__setattr__(
            small_cohort,
            field_name,
            2
            if field_name == "minimum_eligible_draws"
            else getattr(registration.prospective, field_name),
        )
    small_registration = object.__new__(type(registration))
    for field_name in registration.__dataclass_fields__:
        object.__setattr__(
            small_registration,
            field_name,
            small_cohort
            if field_name == "prospective"
            else getattr(registration, field_name),
        )
    monkeypatch.setattr(
        prospective_module,
        "load_experiment_registry",
        lambda _path: SimpleNamespace(get=lambda _experiment_id: small_registration),
    )

    aggregate = audit_registered_cohort(repository, "V3_frozen_shadow_cohort")

    assert aggregate.status == "overdue"
    assert len(aggregate.eligible_evaluated) == 3
    assert len(aggregate.checkpoint) == 2
    assert len(aggregate.extra_evaluated) == 1
