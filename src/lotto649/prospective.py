from __future__ import annotations

from collections.abc import Mapping, Sequence
import csv
from dataclasses import dataclass, replace
from datetime import date, datetime, time, timedelta
from hashlib import sha256
from importlib.metadata import PackageNotFoundError, version as distribution_version
import io
import json
import math
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
from typing import Any
import warnings

import numpy as np
import yaml

from .domain import Draw, Prediction
from .evaluation import evaluate_prediction
from .models.factory import build_models
from .optimizer import rank_numbers, select_combination
from .research_protocol import (
    CohortAggregate,
    CohortAssessment,
    ComparisonEvidence,
    FormalLookRecord,
    GitEvidenceError,
    GitFileEvidence,
    OutcomeBoundary,
    REGISTERED_EVALUATION_METRICS,
    VerifiedOutcomeBoundary,
    TORONTO,
    aggregate_prospective_cohort,
    assess_prospective_snapshot,
    draw_digest,
    load_experiment_registry,
    snapshot_digest,
    validate_formal_attempt_payload,
    verify_frozen_paths,
)


REGISTRY_PATH = Path("docs/experiments/registry.yaml")
OUTCOME_PATH = "data/processed/draws.csv"


@dataclass(frozen=True)
class _RegistryReleaseEvidence:
    release_commit: str
    immutable_registration_digest: str
    active_registration_digest: str
    activation_anchor_sha256: str
    formal_result_commit: str | None = None
    terminal_transition_commit: str | None = None


@dataclass(frozen=True)
class LiveReleaseEvidence:
    experiment_id: str
    model_name: str
    model_version: str
    freeze_commit: str
    activation_commit: str
    release_commit: str
    evidence_commit: str
    immutable_registration_digest: str
    activation_anchor_sha256: str
    frozen_manifest_sha256: str
    frozen_path_sha256: Mapping[str, str]


@dataclass(frozen=True)
class FormalLookComputation:
    schema_version: int
    experiment_id: str
    model_name: str
    model_version: str
    checkpoint_digest: str
    eligible_evaluated_count: int
    scopes: Mapping[str, Mapping[str, Mapping[str, Any]]]
    candidate_minus_v1_top12: Mapping[str, float]
    gates: Mapping[str, bool]
    all_gates_passed: bool
    decision: str
    gate_outcome: str
    formal_claim_path: str
    formal_claim_sha256: str
    formal_claim_commit: str
    formal_attempt_path: str
    formal_attempt_sha256: str
    formal_markdown_path: str
    formal_markdown_sha256: str
    procedures: Mapping[str, Any]

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "experiment_id": self.experiment_id,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "checkpoint_digest": self.checkpoint_digest,
            "eligible_evaluated_count": self.eligible_evaluated_count,
            "scopes": self.scopes,
            "candidate_minus_v1_top12": self.candidate_minus_v1_top12,
            "gates": self.gates,
            "all_gates_passed": self.all_gates_passed,
            "decision": self.decision,
            "gate_outcome": self.gate_outcome,
            "formal_claim_path": self.formal_claim_path,
            "formal_claim_sha256": self.formal_claim_sha256,
            "formal_claim_commit": self.formal_claim_commit,
            "formal_attempt_path": self.formal_attempt_path,
            "formal_attempt_sha256": self.formal_attempt_sha256,
            "formal_markdown_path": self.formal_markdown_path,
            "formal_markdown_sha256": self.formal_markdown_sha256,
            "procedures": self.procedures,
        }


def _git_bytes(repository: Path, *args: str) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(repository), *args],
        check=True,
        capture_output=True,
    )
    return completed.stdout


def _head_commit(repository: Path) -> str:
    return _git_bytes(repository, "rev-parse", "HEAD^{commit}").decode().strip()


def _runtime_python_identity() -> tuple[str, str]:
    return platform.python_implementation(), f"{sys.version_info.major}.{sys.version_info.minor}"


def _installed_distribution_version(name: str) -> str:
    return distribution_version(name)


def _verify_frozen_runtime(
    repository: Path,
    registration: Any,
    *,
    evidence_commit: str,
    frozen_paths: Sequence[str],
) -> None:
    expected_implementation = registration.parameters.get(
        "live_python_implementation"
    )
    expected_version = registration.parameters.get("live_python_major_minor")
    implementation, version = _runtime_python_identity()
    if (
        expected_implementation != "CPython"
        or expected_version != "3.12"
        or implementation != expected_implementation
        or version != expected_version
    ):
        raise GitEvidenceError("live Python runtime does not match registration")
    lock_path = "requirements-live.lock"
    if lock_path not in frozen_paths:
        raise GitEvidenceError("live requirements lock is not in the frozen closure")
    try:
        raw = _git_bytes(repository, "show", f"{evidence_commit}:{lock_path}")
        text = raw.decode("utf-8")
    except (subprocess.CalledProcessError, UnicodeError) as exc:
        raise GitEvidenceError("frozen live requirements lock is unavailable") from exc
    requirements: dict[str, tuple[str, str]] = {}
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.count("==") != 1:
            raise GitEvidenceError(
                f"live requirement must be an exact name==version pin: line {line_number}"
            )
        name, expected = line.split("==", 1)
        if (
            line != f"{name}=={expected}"
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", name)
            or not expected
            or any(character.isspace() for character in expected)
        ):
            raise GitEvidenceError(
                f"live requirement pin is malformed: line {line_number}"
            )
        normalized = re.sub(r"[-_.]+", "-", name).lower()
        if normalized in requirements:
            raise GitEvidenceError(f"duplicate live requirement pin: {name}")
        requirements[normalized] = (name, expected)
    if not requirements:
        raise GitEvidenceError("frozen live requirements lock is empty")
    for name, expected in requirements.values():
        try:
            installed = _installed_distribution_version(name)
        except PackageNotFoundError as exc:
            raise GitEvidenceError(f"frozen live dependency is not installed: {name}") from exc
        if installed != expected:
            raise GitEvidenceError(
                f"frozen live dependency version mismatch: {name}=={installed}"
            )


def _is_strict_ancestor(repository: Path, ancestor: str, descendant: str) -> bool:
    if ancestor == descendant:
        return False
    completed = subprocess.run(
        [
            "git",
            "-C",
            str(repository),
            "merge-base",
            "--is-ancestor",
            ancestor,
            descendant,
        ],
        check=False,
        capture_output=True,
    )
    if completed.returncode == 0:
        return True
    if completed.returncode == 1:
        return False
    raise GitEvidenceError("Git ancestry check failed")


def _registry_row_at(
    repository: Path,
    commit: str,
    experiment_id: str,
) -> Mapping[str, Any]:
    try:
        raw = _git_bytes(repository, "show", f"{commit}:{REGISTRY_PATH.as_posix()}")
        payload = yaml.safe_load(raw.decode("utf-8"))
    except (subprocess.CalledProcessError, UnicodeError, yaml.YAMLError) as exc:
        raise GitEvidenceError(
            f"registry evidence is unavailable at commit {commit}"
        ) from exc
    if not isinstance(payload, Mapping):
        raise GitEvidenceError("committed registry root must be a mapping")
    experiments = payload.get("experiments")
    if not isinstance(experiments, list):
        raise GitEvidenceError("committed registry experiments must be a list")
    matches = [
        item
        for item in experiments
        if isinstance(item, Mapping) and item.get("id") == experiment_id
    ]
    if len(matches) != 1:
        raise GitEvidenceError(
            f"registry must contain exactly one {experiment_id} entry at {commit}"
        )
    return matches[0]


def _jsonable(value: object) -> object:
    if isinstance(value, Mapping):
        return {
            str(key): _jsonable(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _mapping_digest(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        _jsonable(value),
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return sha256(encoded).hexdigest()


_ACTIVATION_MUTABLE_FIELDS = {
    "status",
    "freeze_commit",
    "activation_commit",
    "outcomes_known_at_activation",
    "cohort_start",
}


def _immutable_registration_view(row: Mapping[str, Any]) -> Mapping[str, Any]:
    view = dict(row)
    view.pop("status", None)
    view.pop("result", None)
    prospective = view.get("prospective")
    if not isinstance(prospective, Mapping):
        raise GitEvidenceError("registry prospective specification must be a mapping")
    immutable_prospective = dict(prospective)
    for field in _ACTIVATION_MUTABLE_FIELDS:
        immutable_prospective.pop(field, None)
    view["prospective"] = immutable_prospective
    return view


def _active_registration_view(row: Mapping[str, Any]) -> Mapping[str, Any]:
    prospective = row.get("prospective")
    result = row.get("result")
    if not isinstance(prospective, Mapping) or not isinstance(result, Mapping):
        raise GitEvidenceError("active registry entry requires prospective and result mappings")
    return {
        "status": row.get("status"),
        "model_name": row.get("model_name"),
        "model_version": row.get("model_version"),
        "result": dict(result),
        "prospective": dict(prospective),
    }


def _prospective_status(row: Mapping[str, Any]) -> object:
    prospective = row.get("prospective")
    return prospective.get("status") if isinstance(prospective, Mapping) else None


def _commit_changed_paths(repository: Path, commit: str) -> tuple[str, ...]:
    parents = _git_bytes(
        repository,
        "rev-list",
        "--parents",
        "-n",
        "1",
        commit,
    ).decode().split()
    if len(parents) != 2:
        raise GitEvidenceError("protocol transition must use a non-merge commit")
    return tuple(
        sorted(
            path
            for path in _git_bytes(
                repository,
                "diff-tree",
                "--no-commit-id",
                "--name-only",
                "-r",
                commit,
            )
            .decode()
            .splitlines()
            if path
        )
    )


def _verify_single_add_artifact(
    repository: Path,
    path: str,
    activation_commit: str,
) -> bytes:
    dirty = _git_bytes(
        repository,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
        "--",
        path,
    ).decode().strip()
    if dirty:
        raise GitEvidenceError(f"activation artifact differs from Git state: {path}")
    commits = tuple(
        value
        for value in _git_bytes(
            repository,
            "log",
            "--format=%H",
            "--",
            path,
        )
        .decode()
        .splitlines()
        if value
    )
    additions = tuple(
        value
        for value in _git_bytes(
            repository,
            "log",
            "--diff-filter=A",
            "--format=%H",
            "--",
            path,
        )
        .decode()
        .splitlines()
        if value
    )
    if commits != (activation_commit,) or additions != (activation_commit,):
        raise GitEvidenceError(
            f"activation artifact must be added exactly once at A: {path}"
        )
    original = _git_bytes(repository, "show", f"{activation_commit}:{path}")
    current = _git_bytes(repository, "show", f"HEAD:{path}")
    if current != original:
        raise GitEvidenceError(f"activation artifact changed after A: {path}")
    return original


def _commit_toronto_date(repository: Path, commit: str) -> date:
    raw = _git_bytes(
        repository,
        "show",
        "-s",
        "--format=%cI",
        commit,
    ).decode().strip()
    try:
        committed_at = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise GitEvidenceError("protocol commit timestamp is invalid") from exc
    if committed_at.tzinfo is None:
        raise GitEvidenceError("protocol commit timestamp must be timezone-aware")
    return committed_at.astimezone(TORONTO).date()


def _terminal_decision_state(formal_decision: object) -> tuple[str, str]:
    mapping = {
        "reject": ("closed_rejected", "reject"),
        "archive": ("closed_archived", "archive"),
        "eligible_for_reviewed_promotion": ("promoted", "promote"),
    }
    try:
        return mapping[formal_decision]  # type: ignore[index]
    except (KeyError, TypeError) as exc:
        raise GitEvidenceError(
            "terminal transition cites an invalid formal outcome"
        ) from exc


def _verify_terminal_transition(
    repository: Path,
    row: Mapping[str, Any],
    *,
    freeze_commit: str,
    activation_commit: str,
    transition_commit: str,
) -> str:
    claim_path, attempt_path, formal_path, markdown_path = _registered_formal_paths(
        row
    )
    formal_evidence = GitFileEvidence.from_repository(
        repository,
        formal_path,
        freeze_commit=freeze_commit,
        activation_commit=activation_commit,
    )
    claim_evidence = GitFileEvidence.from_repository(
        repository,
        claim_path,
        freeze_commit=freeze_commit,
        activation_commit=activation_commit,
    )
    attempt_evidence = GitFileEvidence.from_repository(
        repository,
        attempt_path,
        freeze_commit=freeze_commit,
        activation_commit=activation_commit,
    )
    report_commit = formal_evidence.first_commit_sha
    if (
        attempt_evidence.first_commit_sha != report_commit
        or not _is_strict_ancestor(
            repository,
            claim_evidence.first_commit_sha,
            report_commit,
        )
        or not _is_strict_ancestor(repository, report_commit, transition_commit)
    ):
        raise GitEvidenceError(
            "terminal transition must strictly follow one claimed formal report"
        )
    if _commit_changed_paths(repository, claim_evidence.first_commit_sha) != (
        claim_path,
    ):
        raise GitEvidenceError("formal-look claim commit must change only the claim")
    if _commit_changed_paths(repository, report_commit) != tuple(
        sorted((attempt_path, formal_path, markdown_path))
    ):
        raise GitEvidenceError(
            "formal-look result commit must change exactly attempt, JSON, and Markdown"
        )
    if _commit_changed_paths(repository, transition_commit) != (
        REGISTRY_PATH.as_posix(),
    ):
        raise GitEvidenceError(
            "terminal transition commit must change only the registry"
        )
    try:
        formal_payload = json.loads(
            _git_bytes(
                repository,
                "show",
                f"{report_commit}:{formal_path}",
            ).decode("utf-8")
        )
        markdown_at_report = _git_bytes(
            repository,
            "show",
            f"{report_commit}:{markdown_path}",
        )
        markdown_at_head = _git_bytes(
            repository,
            "show",
            f"HEAD:{markdown_path}",
        )
    except (subprocess.CalledProcessError, UnicodeError, json.JSONDecodeError) as exc:
        raise GitEvidenceError("terminal formal report evidence is unavailable") from exc
    markdown_history = tuple(
        value
        for value in _git_bytes(
            repository,
            "log",
            "--format=%H",
            "--",
            markdown_path,
        )
        .decode()
        .splitlines()
        if value
    )
    if (
        not isinstance(formal_payload, Mapping)
        or formal_payload.get("schema_version") != 1
        or formal_payload.get("experiment_id") != row.get("id")
        or formal_payload.get("model_name") != row.get("model_name")
        or formal_payload.get("model_version") != row.get("model_version")
        or formal_payload.get("formal_markdown_path") != markdown_path
        or markdown_history != (report_commit,)
        or markdown_at_head != markdown_at_report
    ):
        raise GitEvidenceError("terminal formal report identity is invalid")

    expected_status, expected_result_decision = _terminal_decision_state(
        formal_payload.get("decision")
    )
    prospective = row.get("prospective")
    result = row.get("result")
    if (
        row.get("status") != expected_status
        or not isinstance(prospective, Mapping)
        or prospective.get("status") != "closed"
        or not isinstance(result, Mapping)
        or result.get("decision") != expected_result_decision
        or result.get("implementation_commit") != report_commit
        or result.get("report_json") != formal_path
        or result.get("report_markdown") != markdown_path
        or result.get("result_file") != markdown_path
        or result.get("historical_primary_signal_supported") is not False
        or result.get("shadow_activation") != "closed"
    ):
        raise GitEvidenceError(
            "terminal registry result does not bind the formal outcome"
        )
    decided_on = result.get("decided_on")
    if isinstance(decided_on, str):
        try:
            decided_on = date.fromisoformat(decided_on)
        except ValueError as exc:
            raise GitEvidenceError("terminal decision date is invalid") from exc
    if (
        not isinstance(decided_on, date)
        or decided_on < _commit_toronto_date(repository, report_commit)
        or decided_on > _commit_toronto_date(repository, transition_commit)
    ):
        raise GitEvidenceError(
            "terminal decision date is outside its Git evidence boundary"
        )
    return report_commit


def _verify_activation_anchor(
    repository: Path,
    row: Mapping[str, Any],
    *,
    freeze_commit: str,
    activation_commit: str,
) -> str:
    parameters = row.get("parameters")
    prospective = row.get("prospective")
    if not isinstance(parameters, Mapping) or not isinstance(prospective, Mapping):
        raise GitEvidenceError("activation registry fields must be mappings")
    artifact_paths = (
        parameters.get("activation_anchor_json"),
        parameters.get("activation_anchor_markdown"),
        parameters.get("activation_anchor_claim"),
    )
    if (
        parameters.get("activation_anchor_schema_version") != 1
        or parameters.get("activation_anchor_commit_changes")
        != "exact_three_activation_artifacts_only"
        or any(not isinstance(path, str) or not path for path in artifact_paths)
        or len(set(artifact_paths)) != 3
    ):
        raise GitEvidenceError("activation anchor registry specification is invalid")
    expected_paths = tuple(sorted(artifact_paths))
    if _commit_changed_paths(repository, activation_commit) != expected_paths:
        raise GitEvidenceError("activation commit must add exactly three anchor artifacts")
    raw_artifacts = {
        path: _verify_single_add_artifact(repository, path, activation_commit)
        for path in artifact_paths
    }
    json_path = artifact_paths[0]
    try:
        payload = json.loads(raw_artifacts[json_path].decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise GitEvidenceError("activation anchor JSON is invalid") from exc
    required_fields = parameters.get("activation_anchor_required_fields")
    if not isinstance(required_fields, list) or any(
        not isinstance(field, str) for field in required_fields
    ):
        raise GitEvidenceError("activation anchor required-fields registry is invalid")
    if not isinstance(payload, Mapping) or set(payload) != set(required_fields):
        raise GitEvidenceError("activation anchor JSON fields do not match registration")
    boundary = prospective.get("outcomes_known_at_activation")
    if not isinstance(boundary, Mapping):
        raise GitEvidenceError("active registry has no activation outcome boundary")
    expected = {
        "schema_version": 1,
        "experiment_id": row.get("id"),
        "model_name": row.get("model_name"),
        "model_version": row.get("model_version"),
        "freeze_commit": freeze_commit,
        "decision": "continue_shadow",
        "role": "shadow",
        "outcome_path": OUTCOME_PATH,
        "outcome_sha256": boundary.get("sha256"),
        "outcome_draw_count": boundary.get("draw_count"),
        "outcome_history_through": _jsonable(boundary.get("history_through")),
        "cohort_start": _jsonable(prospective.get("cohort_start")),
    }
    if _jsonable(payload) != expected:
        raise GitEvidenceError("activation anchor JSON does not bind the active cohort")
    if boundary.get("source_commit") != activation_commit:
        raise GitEvidenceError("activation outcome source commit must equal A")
    result = row.get("result")
    if not isinstance(result, Mapping) or (
        result.get("decision") != "continue_shadow"
        or result.get("shadow_activation") != "active"
        or result.get("implementation_commit") != freeze_commit
        or result.get("report_json") != artifact_paths[0]
        or result.get("report_markdown") != artifact_paths[1]
        or result.get("result_file") != artifact_paths[2]
        or result.get("historical_primary_signal_supported") is not False
    ):
        raise GitEvidenceError("release result does not cite the activation artifacts")
    return sha256(raw_artifacts[json_path]).hexdigest()


def _derive_registry_release(
    repository: Path,
    experiment_id: str,
    *,
    freeze_commit: str,
    activation_commit: str,
) -> _RegistryReleaseEvidence:
    dirty = _git_bytes(
        repository,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
        "--",
        REGISTRY_PATH.as_posix(),
    ).decode().strip()
    if dirty:
        raise GitEvidenceError("registry differs from committed Git state")
    if not _is_strict_ancestor(repository, freeze_commit, activation_commit):
        raise GitEvidenceError(
            "freeze commit must be a strict ancestor of activation commit"
        )

    frozen_row = _registry_row_at(repository, freeze_commit, experiment_id)
    frozen_prospective = frozen_row.get("prospective")
    dormant_fields = (
        "freeze_commit",
        "activation_commit",
        "outcomes_known_at_activation",
        "cohort_start",
    )
    if (
        frozen_row.get("status") != "registered"
        or frozen_row.get("result") is not None
        or not isinstance(frozen_prospective, Mapping)
        or frozen_prospective.get("status") != "not_activated"
        or any(
            field not in frozen_prospective
            or frozen_prospective.get(field) is not None
            for field in dormant_fields
        )
    ):
        raise GitEvidenceError("freeze registry entry must be fully dormant")
    dormant_digest = _mapping_digest(frozen_row)
    immutable_digest = _mapping_digest(_immutable_registration_view(frozen_row))

    current_row = _registry_row_at(repository, _head_commit(repository), experiment_id)
    if _prospective_status(current_row) not in {"active", "closed"}:
        raise GitEvidenceError("current registry entry is neither active nor closed")
    if _mapping_digest(_immutable_registration_view(current_row)) != immutable_digest:
        raise GitEvidenceError("immutable registry specification changed after freeze")

    history = (freeze_commit,) + tuple(
        commit
        for commit in _git_bytes(
            repository,
            "log",
            "--full-history",
            "--reverse",
            "--format=%H",
            f"{freeze_commit}..HEAD",
            "--",
            REGISTRY_PATH.as_posix(),
        )
        .decode()
        .splitlines()
        if commit
    )
    changed_at_freeze = _git_bytes(
        repository,
        "diff-tree",
        "--no-commit-id",
        "--name-only",
        "-r",
        freeze_commit,
        "--",
        REGISTRY_PATH.as_posix(),
    ).decode().splitlines()
    if REGISTRY_PATH.as_posix() not in changed_at_freeze:
        raise GitEvidenceError("freeze commit did not commit the frozen registry entry")

    release_commit = None
    active_digest = None
    activation_anchor_sha256 = None
    terminal_digest = None
    terminal_transition_commit = None
    formal_result_commit = None
    for commit in history:
        row = _registry_row_at(repository, commit, experiment_id)
        if _mapping_digest(_immutable_registration_view(row)) != immutable_digest:
            raise GitEvidenceError(
                "immutable registry specification changed after freeze"
            )
        status = _prospective_status(row)
        if release_commit is None:
            if status != "active":
                if _mapping_digest(row) != dormant_digest:
                    raise GitEvidenceError(
                        "dormant registry identity changed before release"
                    )
                continue
            if row.get("status") != "prospective_shadow":
                raise GitEvidenceError(
                    "registry must enter one active release before any terminal state"
                )
            release_commit = commit
            active_digest = _mapping_digest(_active_registration_view(row))
            activation_anchor_sha256 = _verify_activation_anchor(
                repository,
                row,
                freeze_commit=freeze_commit,
                activation_commit=activation_commit,
            )
            continue
        if terminal_transition_commit is None:
            if status == "active":
                if _mapping_digest(_active_registration_view(row)) != active_digest:
                    raise GitEvidenceError(
                        "active registry identity changed after release"
                    )
                continue
            if status != "closed":
                raise GitEvidenceError("active registry identity changed after release")
            terminal_transition_commit = commit
            terminal_digest = _mapping_digest(_active_registration_view(row))
            formal_result_commit = _verify_terminal_transition(
                repository,
                row,
                freeze_commit=freeze_commit,
                activation_commit=activation_commit,
                transition_commit=commit,
            )
            continue
        if (
            status != "closed"
            or _mapping_digest(_active_registration_view(row)) != terminal_digest
        ):
            raise GitEvidenceError("terminal registry identity changed after transition")

    if release_commit is None:
        raise GitEvidenceError("registry has no unambiguous active release commit")
    if not _is_strict_ancestor(repository, activation_commit, release_commit):
        raise GitEvidenceError(
            "activation commit must be a strict ancestor of registry release commit"
        )
    if _commit_changed_paths(repository, release_commit) != (
        REGISTRY_PATH.as_posix(),
    ):
        raise GitEvidenceError("registry release commit must change only the registry")
    assert active_digest is not None
    assert activation_anchor_sha256 is not None
    return _RegistryReleaseEvidence(
        release_commit=release_commit,
        immutable_registration_digest=immutable_digest,
        active_registration_digest=active_digest,
        activation_anchor_sha256=activation_anchor_sha256,
        formal_result_commit=formal_result_commit,
        terminal_transition_commit=terminal_transition_commit,
    )


def _verify_registry_at_snapshot(
    repository: Path,
    experiment_id: str,
    evidence: _RegistryReleaseEvidence,
    snapshot_commit: str,
) -> None:
    if not _is_strict_ancestor(
        repository,
        evidence.release_commit,
        snapshot_commit,
    ):
        raise GitEvidenceError(
            "registry release commit must be a strict ancestor of snapshot commit"
        )
    row = _registry_row_at(repository, snapshot_commit, experiment_id)
    if (
        _mapping_digest(_immutable_registration_view(row))
        != evidence.immutable_registration_digest
    ):
        raise GitEvidenceError("snapshot commit contains registry specification drift")
    if _mapping_digest(_active_registration_view(row)) != evidence.active_registration_digest:
        raise GitEvidenceError("snapshot commit does not contain the active registry release")


def verify_live_release(
    repository: str | Path,
    experiment_id: str,
) -> LiveReleaseEvidence:
    """Verify the active release and frozen runtime at the committed Git HEAD.

    This is a performance-blind precondition for opening a dormant live model
    version. It does not discover, read, or score any prospective outcome.
    """
    root = Path(repository).resolve(strict=True)
    registration = load_experiment_registry(root / REGISTRY_PATH).get(experiment_id)
    cohort = registration.prospective
    if (
        registration.status != "prospective_shadow"
        or cohort.status != "active"
        or cohort.freeze_commit is None
        or cohort.activation_commit is None
    ):
        raise ValueError("live release requires a prospective_shadow active cohort")
    frozen_paths = registration.parameters.get("frozen_implementation_paths")
    if (
        not isinstance(frozen_paths, Sequence)
        or isinstance(frozen_paths, (str, bytes))
        or not frozen_paths
        or not all(isinstance(path, str) and path for path in frozen_paths)
    ):
        raise ValueError("active cohort requires frozen_implementation_paths")

    release = _derive_registry_release(
        root,
        experiment_id,
        freeze_commit=cohort.freeze_commit,
        activation_commit=cohort.activation_commit,
    )
    head = _head_commit(root)
    if head != release.release_commit and not _is_strict_ancestor(
        root,
        release.release_commit,
        head,
    ):
        raise GitEvidenceError("registry release commit is not an ancestor of HEAD")
    frozen = verify_frozen_paths(
        root,
        freeze_commit=cohort.freeze_commit,
        evidence_commit=head,
        paths=frozen_paths,
    )
    _verify_frozen_runtime(
        root,
        registration,
        evidence_commit=head,
        frozen_paths=frozen_paths,
    )
    return LiveReleaseEvidence(
        experiment_id=experiment_id,
        model_name=registration.model_name,
        model_version=registration.model_version,
        freeze_commit=cohort.freeze_commit,
        activation_commit=cohort.activation_commit,
        release_commit=release.release_commit,
        evidence_commit=head,
        immutable_registration_digest=release.immutable_registration_digest,
        activation_anchor_sha256=release.activation_anchor_sha256,
        frozen_manifest_sha256=frozen.manifest_sha256,
        frozen_path_sha256=frozen.path_sha256,
    )


def _draws_from_csv(raw: bytes) -> tuple[Draw, ...]:
    try:
        rows = csv.DictReader(io.StringIO(raw.decode("utf-8"), newline=""))
    except UnicodeDecodeError as exc:
        raise ValueError("committed outcome data must be valid UTF-8") from exc
    expected = ["draw_date", "n1", "n2", "n3", "n4", "n5", "n6", "bonus"]
    if rows.fieldnames != expected:
        raise ValueError("committed outcome data has an unexpected CSV header")
    try:
        draws = tuple(
            Draw(
                date.fromisoformat(row["draw_date"]),
                tuple(int(row[f"n{index}"]) for index in range(1, 7)),
                int(row["bonus"]),
            )
            for row in rows
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("committed outcome data contains an invalid draw") from exc
    if not draws:
        raise ValueError("committed outcome data contains no draws")
    dates = tuple(draw.draw_date for draw in draws)
    if dates != tuple(sorted(dates)) or len(dates) != len(set(dates)):
        raise ValueError("committed outcome data is not strictly chronological")
    return draws


def _boundary_at_commit(
    repository: Path,
    commit: str,
    *,
    draw_count: int,
    history_through: date,
) -> OutcomeBoundary:
    raw = _git_bytes(repository, "show", f"{commit}:{OUTCOME_PATH}")
    return OutcomeBoundary(
        source_commit=commit,
        sha256=sha256(raw).hexdigest(),
        draw_count=draw_count,
        history_through=history_through,
    )


def _current_boundary(
    repository: Path,
    *,
    evidence_commit: str | None = None,
) -> tuple[OutcomeBoundary, tuple[Draw, ...]]:
    commit = evidence_commit or _head_commit(repository)
    raw = _git_bytes(repository, "show", f"{commit}:{OUTCOME_PATH}")
    draws = _draws_from_csv(raw)
    return (
        OutcomeBoundary(
            source_commit=commit,
            sha256=sha256(raw).hexdigest(),
            draw_count=len(draws),
            history_through=draws[-1].draw_date,
        ),
        draws,
    )


def _registration_boundary(registration: Any) -> OutcomeBoundary:
    return OutcomeBoundary(
        source_commit=registration.outcomes_known_source_commit,
        sha256=registration.outcomes_known_sha256,
        draw_count=registration.outcomes_known_draw_count,
        history_through=registration.outcomes_known_through,
    )


def _scheduled_targets(start: date, end: date) -> tuple[date, ...]:
    if start > end:
        return ()
    targets: list[date] = []
    current = start
    while current <= end:
        if current.weekday() in (2, 5):
            targets.append(current)
        current += timedelta(days=1)
    return tuple(targets)


def _read_json_mapping(path: Path) -> Mapping[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"audited evidence is not valid UTF-8 JSON: {path}") from exc
    if not isinstance(payload, Mapping):
        raise ValueError(f"audited JSON root must be a mapping: {path}")
    return payload


def _source_boundary_from_snapshot(
    repository: Path,
    evidence: GitFileEvidence,
    snapshot: Mapping[str, Any],
) -> OutcomeBoundary:
    metadata = snapshot.get("metadata")
    if not isinstance(metadata, Mapping):
        raise ValueError("snapshot metadata must be a mapping")
    draw_count = metadata.get("history_draws")
    history_through = metadata.get("history_through")
    if type(draw_count) is not int or draw_count < 1:
        raise ValueError("snapshot history_draws must be a positive integer")
    if not isinstance(history_through, str):
        raise ValueError("snapshot history_through must be an ISO date")
    return _boundary_at_commit(
        repository,
        evidence.first_commit_sha,
        draw_count=draw_count,
        history_through=date.fromisoformat(history_through),
    )


def _source_boundary_from_evaluation(
    repository: Path,
    evidence: GitFileEvidence,
    evaluation: Mapping[str, Any],
) -> OutcomeBoundary:
    draw_count = evaluation.get("verified_data_draw_count")
    history_through = evaluation.get("verified_data_history_through")
    if type(draw_count) is not int or draw_count < 1:
        raise ValueError("evaluation verified_data_draw_count must be positive")
    if not isinstance(history_through, str):
        raise ValueError("evaluation verified_data_history_through must be an ISO date")
    return _boundary_at_commit(
        repository,
        evidence.first_commit_sha,
        draw_count=draw_count,
        history_through=date.fromisoformat(history_through),
    )


def _missing_snapshot(target: date, registration: Any) -> Mapping[str, Any]:
    boundary = registration.prospective.outcomes_known_at_activation
    if boundary is None:
        raise ValueError("active cohort is missing its activation outcome boundary")
    probability = 6.0 / 49.0
    return {
        "target_draw_date": target.isoformat(),
        "generated_at": datetime.combine(
            boundary.history_through,
            datetime.min.time(),
            tzinfo=TORONTO,
        ).isoformat(),
        "model_name": registration.model_name,
        "model_version": registration.model_version,
        "probabilities": {
            str(number): probability for number in range(1, 50)
        },
        "top6": list(range(1, 7)),
        "top12": list(range(1, 13)),
        "top18": list(range(1, 19)),
        "final_combination": list(range(1, 7)),
        "metadata": {
            "role": registration.prospective.role,
            "history_draws": boundary.draw_count,
            "history_through": boundary.history_through.isoformat(),
        },
    }


def _scan_candidate_path_history(
    repository: Path,
    registration: Any,
    *,
    activation_history_through: date,
    cohort_start: date,
    evidence_commit: str | None = None,
) -> tuple[date, ...]:
    """Return every exact candidate target visible by an evidence boundary.

    This deliberately scans prediction *and* evaluation history.  A deleted or
    pre-cohort trace is evidence, not an observation that may be silently
    omitted from the prospective counter.
    """
    boundary_commit = evidence_commit or _head_commit(repository)
    suffix = f"__{registration.model_name}__{registration.model_version}.json"
    historical = {
        value
        for value in _git_bytes(
            repository,
            "log",
            boundary_commit,
            "--format=",
            "--name-only",
            "--",
            "predictions",
            "evaluations",
        )
        .decode()
        .splitlines()
        if value
        and value.split("/", 1)[0] in {"predictions", "evaluations"}
        and Path(value).name.endswith(suffix)
    }
    tree_paths = {
        value
        for value in _git_bytes(
            repository,
            "ls-tree",
            "-r",
            "--name-only",
            boundary_commit,
            "--",
            "predictions",
            "evaluations",
        )
        .decode()
        .splitlines()
        if value and Path(value).name.endswith(suffix)
    }
    worktree_paths = (
        {
            path.relative_to(repository).as_posix()
            for directory in ("predictions", "evaluations")
            for path in (repository / directory).glob(f"*{suffix}")
        }
        if evidence_commit is None
        else set()
    )
    paths = historical | tree_paths | worktree_paths
    targets: set[date] = set()
    for path in sorted(paths):
        target_text = Path(path).name[: -len(suffix)]
        try:
            target = date.fromisoformat(target_text)
        except ValueError as exc:
            raise GitEvidenceError(f"invalid candidate evidence path: {path}") from exc
        if target.weekday() not in (2, 5):
            raise GitEvidenceError(
                f"candidate evidence target is not Wednesday/Saturday: {target}"
            )
        if target < cohort_start or target <= activation_history_through:
            raise GitEvidenceError(
                f"candidate evidence predates the prospective cohort: {path}"
            )
        if path in historical and path not in tree_paths:
            raise GitEvidenceError(f"candidate evidence was deleted: {path}")
        targets.add(target)
    return tuple(sorted(targets))


def _reject_post_terminal_candidate_evidence(
    repository: Path,
    registration: Any,
    terminal_commit: str,
) -> None:
    suffix = f"__{registration.model_name}__{registration.model_version}.json"
    changed = {
        value
        for value in _git_bytes(
            repository,
            "log",
            "--format=",
            "--name-only",
            f"{terminal_commit}..HEAD",
            "--",
            "predictions",
            "evaluations",
        )
        .decode()
        .splitlines()
        if value and Path(value).name.endswith(suffix)
    }
    terminal_tree = {
        value
        for value in _git_bytes(
            repository,
            "ls-tree",
            "-r",
            "--name-only",
            terminal_commit,
            "--",
            "predictions",
            "evaluations",
        )
        .decode()
        .splitlines()
        if value and Path(value).name.endswith(suffix)
    }
    current_worktree = {
        path.relative_to(repository).as_posix()
        for directory in ("predictions", "evaluations")
        for path in (repository / directory).glob(f"*{suffix}")
    }
    dirty = _git_bytes(
        repository,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
        "--",
        "predictions",
        "evaluations",
    ).decode()
    if (
        changed
        or current_worktree - terminal_tree
        or any(
            Path(line[3:]).name.endswith(suffix)
            for line in dirty.splitlines()
            if len(line) > 3
        )
    ):
        raise GitEvidenceError(
            "post-terminal candidate evidence is prohibited for the closed version"
        )


def _frozen_model_context(
    repository: Path,
    *,
    freeze_commit: str,
    candidate_name: str,
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    try:
        raw = _git_bytes(repository, "show", f"{freeze_commit}:config.yaml")
        cfg = yaml.safe_load(raw.decode("utf-8"))
    except (subprocess.CalledProcessError, UnicodeError, yaml.YAMLError) as exc:
        raise GitEvidenceError("frozen model configuration is unavailable") from exc
    if not isinstance(cfg, dict):
        raise GitEvidenceError("frozen model configuration must be a mapping")
    cfg["_root"] = repository
    cfg["_config_path"] = repository / "config.yaml"
    identities = [candidate_name, *[name for name, _ in _COMPARISON_IDENTITIES]]
    try:
        models = build_models(cfg, requested=identities)
    except (KeyError, TypeError, ValueError) as exc:
        raise GitEvidenceError("frozen model factory configuration is invalid") from exc
    return cfg, models


def _verify_replayed_prediction(
    snapshot: Mapping[str, Any],
    *,
    model: Any,
    history: Sequence[Draw],
    target: date,
    cfg: Mapping[str, Any],
) -> None:
    try:
        probabilities = model.predict(list(history), target)
        ranking = rank_numbers(probabilities)
        final = select_combination(
            probabilities,
            int(cfg["prediction"].get("candidate_pool_size", 12)),
        )
    except Exception as exc:
        raise GitEvidenceError(
            f"frozen prediction replay failed for {model.name}"
        ) from exc
    observed_raw = snapshot.get("probabilities")
    if not isinstance(observed_raw, Mapping):
        raise GitEvidenceError("snapshot probabilities are unavailable for replay")
    try:
        observed = {int(key): float(value) for key, value in observed_raw.items()}
    except (TypeError, ValueError) as exc:
        raise GitEvidenceError("snapshot probabilities are invalid for replay") from exc
    if set(observed) != set(probabilities) or any(
        not math.isclose(
            observed[number],
            float(probabilities[number]),
            rel_tol=0.0,
            abs_tol=1.0e-15,
        )
        for number in probabilities
    ):
        raise GitEvidenceError(
            f"snapshot probabilities do not match frozen replay: {model.name}"
        )
    if (
        snapshot.get("top6") != ranking[:6]
        or snapshot.get("top12") != ranking[:12]
        or snapshot.get("top18") != ranking[:18]
        or snapshot.get("final_combination") != final
    ):
        raise GitEvidenceError(
            f"snapshot ranking/final selection does not match frozen replay: {model.name}"
        )


def _verify_replayed_target(
    repository: Path,
    *,
    registration: Any,
    target: date,
    history: Sequence[Draw],
    cfg: Mapping[str, Any],
    models: Mapping[str, Any],
) -> None:
    identities = (
        (registration.model_name, registration.model_version),
        *_COMPARISON_IDENTITIES,
    )
    for model_name, model_version in identities:
        path = repository / "predictions" / (
            f"{target.isoformat()}__{model_name}__{model_version}.json"
        )
        if not path.is_file():
            continue
        snapshot = _read_json_mapping(path)
        _verify_replayed_prediction(
            snapshot,
            model=models[model_name],
            history=history,
            target=target,
            cfg=cfg,
        )


_COMPARISON_IDENTITIES = (
    ("ensemble", "v1.0.0"),
    ("random", "v1.0.0"),
)

_CANDIDATE_RELEASE_METADATA_FIELDS = (
    "experiment_id",
    "freeze_commit",
    "activation_commit",
    "release_commit",
    "generation_source_commit",
    "immutable_registration_digest",
    "activation_anchor_sha256",
    "frozen_manifest_sha256",
    "requirements_live_lock_sha256",
)


def _verify_candidate_release_metadata(
    repository: Path,
    snapshot: Mapping[str, Any],
    *,
    registration: Any,
    release: _RegistryReleaseEvidence,
    snapshot_evidence: GitFileEvidence,
    snapshot_frozen_manifest_sha256: str,
    frozen_paths: Sequence[str],
) -> None:
    metadata = snapshot.get("metadata")
    if not isinstance(metadata, Mapping):
        raise GitEvidenceError("candidate snapshot metadata must be a mapping")
    release_metadata = metadata.get("prospective_release")
    if not isinstance(release_metadata, Mapping) or set(release_metadata) != set(
        _CANDIDATE_RELEASE_METADATA_FIELDS
    ):
        raise GitEvidenceError(
            "candidate snapshot prospective_release metadata fields are invalid"
        )
    cohort = registration.prospective
    generation_commit = release_metadata.get("generation_source_commit")
    if not isinstance(generation_commit, str):
        raise GitEvidenceError("candidate generation_source_commit is invalid")
    if not _is_strict_ancestor(
        repository,
        generation_commit,
        snapshot_evidence.first_commit_sha,
    ):
        raise GitEvidenceError(
            "candidate generation source must strictly precede snapshot commit"
        )
    if generation_commit != release.release_commit and not _is_strict_ancestor(
        repository,
        release.release_commit,
        generation_commit,
    ):
        raise GitEvidenceError(
            "candidate generation source does not descend from registry release"
        )
    generation_row = _registry_row_at(
        repository,
        generation_commit,
        registration.experiment_id,
    )
    if (
        _mapping_digest(_immutable_registration_view(generation_row))
        != release.immutable_registration_digest
        or _mapping_digest(_active_registration_view(generation_row))
        != release.active_registration_digest
    ):
        raise GitEvidenceError(
            "candidate generation source does not contain the active release"
        )
    generation_frozen = verify_frozen_paths(
        repository,
        freeze_commit=cohort.freeze_commit,
        evidence_commit=generation_commit,
        paths=frozen_paths,
    )
    try:
        lock_raw = _git_bytes(
            repository,
            "show",
            f"{generation_commit}:requirements-live.lock",
        )
    except subprocess.CalledProcessError as exc:
        raise GitEvidenceError("frozen live requirements lock is unavailable") from exc
    expected = {
        "experiment_id": registration.experiment_id,
        "freeze_commit": cohort.freeze_commit,
        "activation_commit": cohort.activation_commit,
        "release_commit": release.release_commit,
        "generation_source_commit": generation_commit,
        "immutable_registration_digest": release.immutable_registration_digest,
        "activation_anchor_sha256": release.activation_anchor_sha256,
        "frozen_manifest_sha256": generation_frozen.manifest_sha256,
        "requirements_live_lock_sha256": sha256(lock_raw).hexdigest(),
    }
    if any(release_metadata.get(field) != value for field, value in expected.items()):
        raise GitEvidenceError("candidate snapshot release metadata does not match Git")
    if generation_frozen.manifest_sha256 != snapshot_frozen_manifest_sha256:
        raise GitEvidenceError("candidate frozen manifest changed before snapshot commit")


def _prediction_from_payload(
    snapshot: Mapping[str, Any],
    *,
    expected_role: str,
) -> Prediction:
    metadata = snapshot.get("metadata")
    if not isinstance(metadata, Mapping) or metadata.get("role") != expected_role:
        raise GitEvidenceError(f"snapshot role must be {expected_role}")
    probabilities_raw = snapshot.get("probabilities")
    if not isinstance(probabilities_raw, Mapping) or set(probabilities_raw) != {
        str(number) for number in range(1, 50)
    }:
        raise GitEvidenceError("snapshot probability keys must be canonical 1..49")
    try:
        probabilities = {
            int(number): float(value)
            for number, value in probabilities_raw.items()
        }
    except (TypeError, ValueError) as exc:
        raise GitEvidenceError("snapshot probabilities must be numeric") from exc
    if any(
        not math.isfinite(value) or not 0.0 < value < 1.0
        for value in probabilities.values()
    ) or not math.isclose(
        math.fsum(probabilities.values()),
        6.0,
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise GitEvidenceError("snapshot probability contract is invalid")
    ranked = sorted(probabilities, key=lambda number: (-probabilities[number], number))
    top_values: dict[int, list[int]] = {}
    for size, field in ((6, "top6"), (12, "top12"), (18, "top18")):
        value = snapshot.get(field)
        if (
            not isinstance(value, list)
            or value != ranked[:size]
            or len(set(value)) != size
        ):
            raise GitEvidenceError(f"snapshot {field} ranking contract is invalid")
        top_values[size] = value
    final = snapshot.get("final_combination")
    if (
        not isinstance(final, list)
        or len(final) != 6
        or len(set(final)) != 6
        or any(type(number) is not int or not 1 <= number <= 49 for number in final)
        or not set(final).issubset(top_values[12])
    ):
        raise GitEvidenceError("snapshot final combination contract is invalid")
    try:
        target = date.fromisoformat(str(snapshot.get("target_draw_date")))
        generated_at = datetime.fromisoformat(str(snapshot.get("generated_at")))
    except ValueError as exc:
        raise GitEvidenceError("snapshot date identity is invalid") from exc
    if generated_at.tzinfo is None:
        raise GitEvidenceError("snapshot generated_at must be timezone-aware")
    return Prediction(
        target_draw_date=target,
        generated_at=generated_at,
        model_name=str(snapshot.get("model_name")),
        model_version=str(snapshot.get("model_version")),
        probabilities=probabilities,
        top6=top_values[6],
        top12=top_values[12],
        top18=top_values[18],
        final_combination=final,
        metadata=dict(metadata),
    )


def _metric_matches(actual: object, expected: object) -> bool:
    if isinstance(expected, int):
        return type(actual) is int and actual == expected
    if isinstance(expected, float):
        return (
            isinstance(actual, (int, float))
            and not isinstance(actual, bool)
            and math.isfinite(float(actual))
            and math.isclose(float(actual), expected, rel_tol=1e-12, abs_tol=1e-12)
        )
    return actual == expected


def _audit_comparison_evidence(
    repository: Path,
    target: date,
    *,
    model_name: str,
    model_version: str,
    cohort: Any,
    experiment_id: str,
    release_evidence: _RegistryReleaseEvidence,
    activation_boundary: OutcomeBoundary,
    candidate_snapshot_boundary: OutcomeBoundary,
    verified_draw: Draw | None,
) -> tuple[str, ComparisonEvidence | None]:
    relative_snapshot = Path("predictions") / (
        f"{target.isoformat()}__{model_name}__{model_version}.json"
    )
    snapshot_path = repository / relative_snapshot
    if not snapshot_path.is_file():
        return "missing_snapshot", None
    snapshot = _read_json_mapping(snapshot_path)
    snapshot_evidence = GitFileEvidence.from_repository(
        repository,
        relative_snapshot,
        freeze_commit=cohort.freeze_commit,
        activation_commit=cohort.activation_commit,
    )
    _verify_registry_at_snapshot(
        repository,
        experiment_id,
        release_evidence,
        snapshot_evidence.first_commit_sha,
    )
    if (
        snapshot.get("target_draw_date") != target.isoformat()
        or snapshot.get("model_name") != model_name
        or snapshot.get("model_version") != model_version
    ):
        raise GitEvidenceError(
            f"comparison snapshot identity mismatch: {relative_snapshot.as_posix()}"
        )
    prediction = _prediction_from_payload(snapshot, expected_role="primary")
    deadline = datetime.combine(target, time.min, tzinfo=TORONTO)
    if snapshot_evidence.first_commit_at.astimezone(TORONTO) >= deadline:
        raise GitEvidenceError("comparison snapshot was committed after its deadline")
    generated_at_raw = snapshot.get("generated_at")
    try:
        generated_at = datetime.fromisoformat(generated_at_raw)
    except (TypeError, ValueError) as exc:
        raise GitEvidenceError("comparison snapshot generated_at is invalid") from exc
    if (
        generated_at.tzinfo is None
        or generated_at > snapshot_evidence.first_commit_at
        or generated_at.astimezone(TORONTO) >= deadline
    ):
        raise GitEvidenceError("comparison snapshot generation time is invalid")
    snapshot_boundary = _source_boundary_from_snapshot(
        repository,
        snapshot_evidence,
        snapshot,
    )
    if (
        snapshot_boundary.sha256 != candidate_snapshot_boundary.sha256
        or snapshot_boundary.draw_count != candidate_snapshot_boundary.draw_count
        or snapshot_boundary.history_through
        != candidate_snapshot_boundary.history_through
    ):
        raise GitEvidenceError(
            "comparison snapshot source history differs from candidate"
        )
    if snapshot_boundary.history_through >= target:
        raise GitEvidenceError("comparison snapshot history is not strictly prior")
    VerifiedOutcomeBoundary.from_repository(
        repository,
        snapshot_boundary,
        registration_boundary=activation_boundary,
    )

    def comparison_evidence(
        evaluation_evidence: GitFileEvidence | None = None,
        evaluation: Mapping[str, Any] | None = None,
    ) -> ComparisonEvidence:
        return ComparisonEvidence(
            model_name=model_name,
            model_version=model_version,
            verified_at_commit=_head_commit(repository),
            snapshot_path=snapshot_evidence.path,
            snapshot_digest=snapshot_evidence.canonical_digest,
            snapshot_raw_sha256=snapshot_evidence.raw_sha256,
            snapshot_commit=snapshot_evidence.first_commit_sha,
            evaluation_path=(
                evaluation_evidence.path
                if evaluation_evidence is not None
                else None
            ),
            evaluation_digest=(
                snapshot_digest(evaluation) if evaluation is not None else None
            ),
            evaluation_raw_sha256=(
                evaluation_evidence.raw_sha256
                if evaluation_evidence is not None
                else None
            ),
            evaluation_commit=(
                evaluation_evidence.first_commit_sha
                if evaluation_evidence is not None
                else None
            ),
        )

    relative_evaluation = Path("evaluations") / relative_snapshot.name
    evaluation_path = repository / relative_evaluation
    if verified_draw is None:
        if evaluation_path.exists():
            raise GitEvidenceError(
                "comparison evaluation exists before a verified target outcome"
            )
        return "complete", comparison_evidence()
    if not evaluation_path.is_file():
        return "pending_evaluation", comparison_evidence()

    evaluation = _read_json_mapping(evaluation_path)
    evaluation_evidence = GitFileEvidence.from_repository(
        repository,
        relative_evaluation,
        freeze_commit=cohort.freeze_commit,
        activation_commit=cohort.activation_commit,
    )
    if not _is_strict_ancestor(
        repository,
        snapshot_evidence.first_commit_sha,
        evaluation_evidence.first_commit_sha,
    ):
        raise GitEvidenceError(
            "comparison snapshot commit must strictly precede its evaluation"
        )
    if evaluation_evidence.first_commit_at.astimezone(TORONTO).date() < target:
        raise GitEvidenceError("comparison evaluation was committed before the draw")
    if (
        evaluation.get("target_draw_date") != target.isoformat()
        or evaluation.get("model_name") != model_name
        or evaluation.get("model_version") != model_version
        or evaluation.get("prediction_snapshot_path")
        != relative_snapshot.as_posix()
        or evaluation.get("prediction_snapshot_digest")
        != snapshot_evidence.canonical_digest
    ):
        raise GitEvidenceError(
            f"comparison evaluation identity mismatch: {relative_evaluation.as_posix()}"
        )
    evaluation_boundary = _source_boundary_from_evaluation(
        repository,
        evaluation_evidence,
        evaluation,
    )
    evaluation_source = VerifiedOutcomeBoundary.from_repository(
        repository,
        evaluation_boundary,
        registration_boundary=snapshot_boundary,
    )
    matches = tuple(
        draw for draw in evaluation_source.draws if draw.draw_date == target
    )
    if matches != (verified_draw,):
        raise GitEvidenceError("comparison evaluation source does not bind the target draw")
    if (
        evaluation.get("actual") != list(verified_draw.numbers)
        or evaluation.get("bonus") != verified_draw.bonus
        or evaluation.get("actual_draw_digest") != draw_digest(verified_draw)
    ):
        raise GitEvidenceError("comparison evaluation actual outcome identity mismatch")
    expected_evaluation = evaluate_prediction(prediction, verified_draw)
    for metric in REGISTERED_EVALUATION_METRICS:
        if metric not in evaluation or not _metric_matches(
            evaluation.get(metric),
            expected_evaluation[metric],
        ):
            raise GitEvidenceError(
                f"comparison registered metric mismatch: {metric}"
            )
    return "complete", comparison_evidence(evaluation_evidence, evaluation)


def _apply_comparison_states(
    assessment: CohortAssessment,
    states: Sequence[
        tuple[str, str, str, ComparisonEvidence | None]
    ],
) -> CohortAssessment:
    evidence = tuple(
        item for _, _, _, item in states if item is not None
    )
    missing_snapshots = [
        f"missing_comparison_snapshot:{name}:{version}"
        for name, version, state, _ in states
        if state == "missing_snapshot"
    ]
    if missing_snapshots:
        return CohortAssessment._create(
            status="excluded",
            reasons=tuple(dict.fromkeys((*assessment.reasons, *missing_snapshots))),
            snapshot_digest=assessment.snapshot_digest,
            target_draw_date=assessment.target_draw_date,
            evaluation_digest=assessment.evaluation_digest,
            snapshot_path=assessment.snapshot_path,
            evaluation_path=assessment.evaluation_path,
            snapshot_git_evidence=assessment.snapshot_git_evidence,
            evaluation_git_evidence=assessment.evaluation_git_evidence,
            snapshot_frozen_path_evidence=(
                assessment.snapshot_frozen_path_evidence
            ),
            comparison_evidence=evidence,
        )
    if (
        assessment.status in {"eligible_pending", "eligible_evaluated"}
        and any(state == "pending_evaluation" for _, _, state, _ in states)
    ):
        return CohortAssessment._create(
            status="eligible_pending",
            reasons=(),
            snapshot_digest=assessment.snapshot_digest,
            target_draw_date=assessment.target_draw_date,
            snapshot_path=assessment.snapshot_path,
            snapshot_git_evidence=assessment.snapshot_git_evidence,
            snapshot_frozen_path_evidence=(
                assessment.snapshot_frozen_path_evidence
            ),
            comparison_evidence=evidence,
        )
    return CohortAssessment._create(
        status=assessment.status,
        reasons=assessment.reasons,
        snapshot_digest=assessment.snapshot_digest,
        target_draw_date=assessment.target_draw_date,
        evaluation_digest=assessment.evaluation_digest,
        snapshot_path=assessment.snapshot_path,
        evaluation_path=assessment.evaluation_path,
        snapshot_git_evidence=assessment.snapshot_git_evidence,
        evaluation_git_evidence=assessment.evaluation_git_evidence,
        snapshot_frozen_path_evidence=assessment.snapshot_frozen_path_evidence,
        comparison_evidence=evidence,
    )


def _apply_minimum_history(
    assessment: CohortAssessment,
    *,
    observed: int,
    required: int,
) -> CohortAssessment:
    if observed >= required or not assessment.snapshot_eligible:
        return assessment
    return CohortAssessment._create(
        status="excluded",
        reasons=("insufficient_registered_history",),
        snapshot_digest=assessment.snapshot_digest,
        target_draw_date=assessment.target_draw_date,
        evaluation_digest=assessment.evaluation_digest,
        snapshot_path=assessment.snapshot_path,
        evaluation_path=assessment.evaluation_path,
        snapshot_git_evidence=assessment.snapshot_git_evidence,
        evaluation_git_evidence=assessment.evaluation_git_evidence,
        snapshot_frozen_path_evidence=assessment.snapshot_frozen_path_evidence,
        comparison_evidence=assessment.comparison_evidence,
    )


def _verify_terminal_formal_record(
    registration: Any,
    release_evidence: _RegistryReleaseEvidence | None,
    record: Any,
) -> None:
    if registration.prospective.status != "closed":
        return
    result = registration.result
    expected_formal_decision = {
        "reject": "reject",
        "archive": "archive",
        "promote": "eligible_for_reviewed_promotion",
    }.get(result.decision if result is not None else None)
    if (
        release_evidence is None
        or release_evidence.terminal_transition_commit is None
        or release_evidence.formal_result_commit != record.record_commit
        or record.decision != expected_formal_decision
    ):
        raise GitEvidenceError(
            "terminal registry transition does not match the verified formal look"
        )


def _aggregate_with_committed_formal_look(
    repository: Path,
    registration: Any,
    assessments: Sequence[CohortAssessment],
    *,
    release_evidence: _RegistryReleaseEvidence | None = None,
) -> CohortAggregate:
    aggregate = aggregate_prospective_cohort(registration, assessments)
    claim_path, attempt_path, formal_path, markdown_path = _registered_formal_paths(
        registration
    )
    paths = (claim_path, attempt_path, formal_path, markdown_path)
    present = {path: (repository / path).is_file() for path in paths}
    history = {path: _path_has_git_history(repository, path) for path in paths}
    deleted = [path for path in paths if history[path] and not present[path]]
    if deleted:
        raise GitEvidenceError(
            "formal-look evidence was deleted: " + ", ".join(deleted)
        )
    if not any(present.values()):
        return aggregate
    if present[claim_path] and not any(
        present[path] for path in (attempt_path, formal_path, markdown_path)
    ):
        _require_exact_ready_checkpoint(aggregate)
        _verified_formal_claim(repository, registration, aggregate, claim_path)
        return aggregate
    if not all(present.values()):
        raise GitEvidenceError(
            "formal-look attempt/report artifact set is incomplete; cohort is consumed"
        )
    if len(aggregate.checkpoint) != registration.prospective.minimum_eligible_draws:
        raise GitEvidenceError("formal-look report exists without a fixed checkpoint")
    extra_ids = {id(item) for item in aggregate.extra_evaluated}
    ready_assessments = [item for item in assessments if id(item) not in extra_ids]
    ready = aggregate_prospective_cohort(registration, ready_assessments)
    if ready.status != "ready":
        raise GitEvidenceError("formal-look report cannot bind a non-ready checkpoint")
    record = FormalLookRecord.from_repository(
        registration,
        ready,
        repository,
        formal_path,
    )
    _verify_terminal_formal_record(registration, release_evidence, record)
    expected_report_paths = tuple(sorted((attempt_path, formal_path, markdown_path)))
    if _commit_changed_paths(repository, record.record_commit) != expected_report_paths:
        raise GitEvidenceError(
            "formal-look result commit must change exactly attempt, JSON, and Markdown"
        )
    claim_evidence = GitFileEvidence.from_repository(
        repository,
        claim_path,
        freeze_commit=registration.prospective.freeze_commit,
        activation_commit=registration.prospective.activation_commit,
    )
    attempt_raw = (repository / attempt_path).read_bytes()
    computed = _compute_formal_look_from_ready(
        repository,
        registration,
        ready,
        claim_evidence=claim_evidence,
        attempt_path=attempt_path,
        attempt_sha256=sha256(attempt_raw).hexdigest(),
        markdown_path=markdown_path,
        markdown_sha256="",
    )
    expected_markdown = _formal_markdown(computed)
    computed = replace(
        computed,
        formal_markdown_sha256=sha256(expected_markdown).hexdigest(),
    )
    report = _read_json_mapping(repository / formal_path)
    if _jsonable(report) != _jsonable(computed.to_json_dict()):
        raise GitEvidenceError("formal-look report does not match frozen recomputation")
    try:
        actual_markdown = (repository / markdown_path).read_bytes()
    except OSError as exc:
        raise GitEvidenceError("formal-look Markdown is unavailable") from exc
    if actual_markdown != expected_markdown:
        raise GitEvidenceError("formal-look Markdown does not match frozen computation")
    return aggregate_prospective_cohort(
        registration,
        assessments,
        formal_looks=(record,),
    )


def audit_registered_cohort(
    repository: str | Path,
    experiment_id: str,
) -> CohortAggregate:
    """Audit one activated prospective cohort from immutable repository evidence."""
    root = Path(repository).resolve(strict=True)
    registration = load_experiment_registry(root / REGISTRY_PATH).get(experiment_id)
    if registration.prospective.status not in {"active", "closed"}:
        raise ValueError("prospective cohort must be active or closed")
    cohort = registration.prospective
    if (
        cohort.freeze_commit is None
        or cohort.activation_commit is None
        or cohort.outcomes_known_at_activation is None
        or cohort.cohort_start is None
    ):
        raise ValueError("activated cohort evidence is incomplete")

    frozen_paths = registration.parameters.get("frozen_implementation_paths")
    if (
        not isinstance(frozen_paths, Sequence)
        or isinstance(frozen_paths, (str, bytes))
        or not frozen_paths
        or not all(isinstance(path, str) and path for path in frozen_paths)
    ):
        raise ValueError("activated cohort requires frozen_implementation_paths")
    minimum_history_draws = registration.parameters.get("minimum_history_draws")
    if type(minimum_history_draws) is not int or minimum_history_draws < 1:
        raise ValueError("activated cohort requires a positive minimum_history_draws")

    release_evidence = _derive_registry_release(
        root,
        experiment_id,
        freeze_commit=cohort.freeze_commit,
        activation_commit=cohort.activation_commit,
    )
    head = _head_commit(root)
    closed = cohort.status == "closed"
    if closed:
        terminal_commit = release_evidence.terminal_transition_commit
        if terminal_commit is None:
            raise GitEvidenceError("closed cohort has no terminal transition commit")
        _reject_post_terminal_candidate_evidence(
            root,
            registration,
            terminal_commit,
        )
        evidence_commit = terminal_commit
    else:
        evidence_commit = head
    verify_frozen_paths(
        root,
        freeze_commit=cohort.freeze_commit,
        evidence_commit=evidence_commit,
        paths=frozen_paths,
    )
    if closed and head != evidence_commit:
        try:
            verify_frozen_paths(
                root,
                freeze_commit=cohort.freeze_commit,
                evidence_commit=head,
                paths=frozen_paths,
            )
        except GitEvidenceError as exc:
            raise GitEvidenceError(
                "closed cohort replay requires checkout of the terminal transition "
                "commit after frozen runtime evolution"
            ) from exc
    _verify_frozen_runtime(
        root,
        registration,
        evidence_commit=evidence_commit,
        frozen_paths=frozen_paths,
    )

    activation_evidence = VerifiedOutcomeBoundary.from_repository(
        root,
        cohort.outcomes_known_at_activation,
        registration_boundary=_registration_boundary(registration),
    )
    current_boundary, current_draws = _current_boundary(
        root,
        evidence_commit=evidence_commit if closed else None,
    )
    VerifiedOutcomeBoundary.from_repository(
        root,
        current_boundary,
        registration_boundary=cohort.outcomes_known_at_activation,
    )
    latest_verified_draw = current_draws[-1].draw_date
    verified_draw_by_date = {draw.draw_date: draw for draw in current_draws}
    discovered_targets = _scan_candidate_path_history(
        root,
        registration,
        activation_history_through=(
            cohort.outcomes_known_at_activation.history_through
        ),
        cohort_start=cohort.cohort_start,
        evidence_commit=evidence_commit if closed else None,
    )
    targets = set(
        _scheduled_targets(cohort.cohort_start, latest_verified_draw)
    )
    targets.update(discovered_targets)
    frozen_cfg, frozen_models = _frozen_model_context(
        root,
        freeze_commit=cohort.freeze_commit,
        candidate_name=registration.model_name,
    )

    assessments = []
    for target in sorted(targets):
        relative_snapshot = Path(
            "predictions"
        ) / f"{target.isoformat()}__{registration.model_name}__{registration.model_version}.json"
        snapshot_path = root / relative_snapshot
        relative_evaluation = Path(
            "evaluations"
        ) / f"{target.isoformat()}__{registration.model_name}__{registration.model_version}.json"
        evaluation_path = root / relative_evaluation

        if not snapshot_path.is_file():
            if evaluation_path.exists():
                raise GitEvidenceError(
                    f"evaluation exists without snapshot: {relative_evaluation.as_posix()}"
                )
            assessment = assess_prospective_snapshot(
                registration,
                _missing_snapshot(target, registration),
                snapshot_evidence=None,
                activation_boundary_evidence=activation_evidence,
            )
            assessments.append(assessment)
            continue

        snapshot = _read_json_mapping(snapshot_path)
        snapshot_evidence = GitFileEvidence.from_repository(
            root,
            relative_snapshot,
            freeze_commit=cohort.freeze_commit,
            activation_commit=cohort.activation_commit,
        )
        _verify_registry_at_snapshot(
            root,
            experiment_id,
            release_evidence,
            snapshot_evidence.first_commit_sha,
        )
        frozen_evidence = verify_frozen_paths(
            root,
            freeze_commit=cohort.freeze_commit,
            evidence_commit=snapshot_evidence.first_commit_sha,
            paths=frozen_paths,
        )
        snapshot_boundary = _source_boundary_from_snapshot(
            root,
            snapshot_evidence,
            snapshot,
        )
        snapshot_source_evidence = VerifiedOutcomeBoundary.from_repository(
            root,
            snapshot_boundary,
            registration_boundary=cohort.outcomes_known_at_activation,
        )
        _verify_candidate_release_metadata(
            root,
            snapshot,
            registration=registration,
            release=release_evidence,
            snapshot_evidence=snapshot_evidence,
            snapshot_frozen_manifest_sha256=frozen_evidence.manifest_sha256,
            frozen_paths=frozen_paths,
        )
        comparison_states = []
        for comparison_name, comparison_version in _COMPARISON_IDENTITIES:
            state, comparison_evidence = _audit_comparison_evidence(
                root,
                target,
                model_name=comparison_name,
                model_version=comparison_version,
                cohort=cohort,
                experiment_id=experiment_id,
                release_evidence=release_evidence,
                activation_boundary=cohort.outcomes_known_at_activation,
                candidate_snapshot_boundary=snapshot_boundary,
                verified_draw=verified_draw_by_date.get(target),
            )
            comparison_states.append(
                (
                    comparison_name,
                    comparison_version,
                    state,
                    comparison_evidence,
                )
            )

        evaluation = None
        evaluation_evidence = None
        evaluation_source_evidence = None
        if evaluation_path.is_file():
            evaluation = _read_json_mapping(evaluation_path)
            evaluation_evidence = GitFileEvidence.from_repository(
                root,
                relative_evaluation,
                freeze_commit=cohort.freeze_commit,
                activation_commit=cohort.activation_commit,
            )
            evaluation_boundary = _source_boundary_from_evaluation(
                root,
                evaluation_evidence,
                evaluation,
            )
            evaluation_source_evidence = VerifiedOutcomeBoundary.from_repository(
                root,
                evaluation_boundary,
                registration_boundary=snapshot_boundary,
            )

        _verify_replayed_target(
            root,
            registration=registration,
            target=target,
            history=snapshot_source_evidence.draws,
            cfg=frozen_cfg,
            models=frozen_models,
        )
        assessment = _apply_comparison_states(
            assess_prospective_snapshot(
                    registration,
                    snapshot,
                    snapshot_evidence=snapshot_evidence,
                    activation_boundary_evidence=activation_evidence,
                    snapshot_source_evidence=snapshot_source_evidence,
                    snapshot_frozen_path_evidence=frozen_evidence,
                    evaluation=evaluation,
                    evaluation_evidence=evaluation_evidence,
                    evaluation_source_evidence=evaluation_source_evidence,
            ),
            comparison_states,
        )
        assessments.append(
            _apply_minimum_history(
                assessment,
                observed=snapshot_boundary.draw_count,
                required=minimum_history_draws,
            )
        )

    return _aggregate_with_committed_formal_look(
        root,
        registration,
        assessments,
        release_evidence=release_evidence,
    )


_FAIR_PROBABILITY = 6.0 / 49.0
_FAIR_TOP12_EXPECTATION = 72.0 / 49.0
_FORMAL_SCOPE_SLICES = {
    "aggregate_208": slice(0, 208),
    "first_104": slice(0, 104),
    "second_104": slice(104, 208),
}
_FORMAL_GATE_KEYS = (
    "positive_aggregate_primary_lift",
    "aggregate_adjusted_p_at_most_0_05",
    "aggregate_bootstrap_lower_above_zero",
    "positive_primary_lift_in_both_fixed_halves",
    "proper_scores_within_fair_tolerance_aggregate_and_halves",
    "candidate_top12_mean_strictly_above_v1_ensemble",
    "random_control_null_aggregate_and_halves",
    "audit_clear",
)
_FORMAL_INVALIDITY_GATE_KEYS = (
    "random_control_null_aggregate_and_halves",
    "audit_clear",
)


def _exact_top12_upper_tail(total_hits: int, draw_count: int) -> float:
    if draw_count < 1 or not 0 <= total_hits <= 6 * draw_count:
        raise ValueError("formal Top-12 hit total is outside its support")
    if total_hits == 0:
        return 1.0
    denominator = math.comb(49, 6)
    one_draw = np.zeros(7, dtype=float)
    for hits in range(7):
        if hits <= 12 and 6 - hits <= 37:
            one_draw[hits] = (
                math.comb(12, hits) * math.comb(37, 6 - hits) / denominator
            )
    distribution = np.array([1.0])
    for _ in range(draw_count):
        active = len(distribution)
        updated = np.zeros(active + 6, dtype=float)
        for hits, probability in enumerate(one_draw):
            if probability:
                updated[hits : hits + active] += probability * distribution
        distribution = updated
    return float(np.clip(np.sum(distribution[total_hits:]), 0.0, 1.0))


def _bootstrap_top12_lift(
    hits: Sequence[int],
    *,
    resamples: int,
    seed: int,
) -> tuple[float, float]:
    values = np.asarray(hits, dtype=float)
    if values.ndim != 1 or len(values) == 0:
        raise ValueError("formal bootstrap requires a non-empty hit vector")
    rng = np.random.default_rng(seed)
    lifts = np.empty(resamples, dtype=float)
    chunk_size = 256
    for start in range(0, resamples, chunk_size):
        stop = min(start + chunk_size, resamples)
        indices = rng.integers(
            0,
            len(values),
            size=(stop - start, len(values)),
        )
        lifts[start:stop] = (
            values[indices].mean(axis=1) - _FAIR_TOP12_EXPECTATION
        )
    lower, upper = np.quantile(lifts, [0.025, 0.975], method="linear")
    return float(lower), float(upper)


def _fair_constant_scores() -> tuple[float, float]:
    brier = (
        6 * (1.0 - _FAIR_PROBABILITY) ** 2
        + 43 * _FAIR_PROBABILITY**2
    ) / 49
    log_loss = -(
        6 * math.log(_FAIR_PROBABILITY)
        + 43 * math.log(1.0 - _FAIR_PROBABILITY)
    ) / 49
    return brier, log_loss


def _score_snapshot(
    snapshot: Mapping[str, Any],
    evaluation: Mapping[str, Any],
    *,
    expected_role: str,
) -> Mapping[str, float | int]:
    prediction = _prediction_from_payload(snapshot, expected_role=expected_role)
    actual_raw = evaluation.get("actual")
    bonus = evaluation.get("bonus")
    if (
        not isinstance(actual_raw, list)
        or len(actual_raw) != 6
        or any(type(number) is not int for number in actual_raw)
        or type(bonus) is not int
    ):
        raise GitEvidenceError("formal look evaluation outcome is invalid")
    try:
        draw = Draw(prediction.target_draw_date, tuple(actual_raw), bonus)
    except ValueError as exc:
        raise GitEvidenceError("formal look evaluation outcome is invalid") from exc
    expected = evaluate_prediction(prediction, draw)
    for metric in REGISTERED_EVALUATION_METRICS:
        if metric not in evaluation or not _metric_matches(
            evaluation.get(metric), expected[metric]
        ):
            raise GitEvidenceError(f"formal look registered metric mismatch: {metric}")
    return {
        "final_6_hits": int(expected["final_6_hits"]),
        "top_6_hits": int(expected["top_6_hits"]),
        "top_12_hits": int(expected["top_12_hits"]),
        "top_18_hits": int(expected["top_18_hits"]),
        "brier_score": float(expected["brier_score"]),
        "log_loss": float(expected["log_loss"]),
        "mean_actual_rank": float(expected["mean_actual_rank"]),
    }


def _formal_rows(
    repository: Path,
    registration: Any,
    aggregate: CohortAggregate,
    *,
    claim_evidence: GitFileEvidence,
) -> Mapping[str, tuple[Mapping[str, float | int], ...]]:
    candidate_name = registration.model_name
    candidate_version = registration.model_version
    rows: dict[str, list[Mapping[str, float | int]]] = {
        candidate_name: [],
        "ensemble": [],
        "random": [],
    }
    audit_heads = {
        evidence.verified_at_commit
        for assessment in aggregate.checkpoint
        for evidence in assessment.comparison_evidence
    }
    if audit_heads != {_head_commit(repository)}:
        raise GitEvidenceError(
            "formal comparison evidence is not locked to the audited Git HEAD"
        )

    def locked_payload(
        *,
        path: str,
        canonical_digest: str,
        raw_sha256: str,
    ) -> Mapping[str, Any]:
        try:
            raw = (repository / path).read_bytes()
            payload = json.loads(raw.decode("utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise GitEvidenceError("formal checkpoint evidence is unavailable") from exc
        if (
            not isinstance(payload, Mapping)
            or sha256(raw).hexdigest() != raw_sha256
            or snapshot_digest(payload) != canonical_digest
        ):
            raise GitEvidenceError(
                "formal checkpoint evidence changed after the immutable audit"
            )
        return payload

    for assessment in aggregate.checkpoint:
        target = assessment.target_draw_date
        if target is None:
            raise GitEvidenceError("formal checkpoint observation has no target date")
        candidate_snapshot_evidence = assessment.snapshot_git_evidence
        candidate_evaluation_evidence = assessment.evaluation_git_evidence
        if (
            candidate_snapshot_evidence is None
            or candidate_evaluation_evidence is None
            or assessment.evaluation_digest is None
        ):
            raise GitEvidenceError(
                "formal checkpoint is missing candidate Git evidence"
            )
        comparison_by_identity = {
            (item.model_name, item.model_version): item
            for item in assessment.comparison_evidence
        }
        if set(comparison_by_identity) != set(_COMPARISON_IDENTITIES):
            raise GitEvidenceError(
                "formal checkpoint is missing registered comparison Git evidence"
            )
        identities = [
            (
                candidate_name,
                candidate_version,
                "shadow",
                candidate_snapshot_evidence.path,
                candidate_snapshot_evidence.canonical_digest,
                candidate_snapshot_evidence.raw_sha256,
                candidate_snapshot_evidence.first_commit_sha,
                candidate_evaluation_evidence.path,
                candidate_evaluation_evidence.canonical_digest,
                candidate_evaluation_evidence.raw_sha256,
                candidate_evaluation_evidence.first_commit_sha,
            )
        ]
        for model_name, version in _COMPARISON_IDENTITIES:
            evidence = comparison_by_identity[(model_name, version)]
            if (
                evidence.evaluation_path is None
                or evidence.evaluation_digest is None
                or evidence.evaluation_raw_sha256 is None
                or evidence.evaluation_commit is None
            ):
                raise GitEvidenceError(
                    "formal checkpoint comparison evaluation evidence is incomplete"
                )
            identities.append(
                (
                    model_name,
                    version,
                    "primary",
                    evidence.snapshot_path,
                    evidence.snapshot_digest,
                    evidence.snapshot_raw_sha256,
                    evidence.snapshot_commit,
                    evidence.evaluation_path,
                    evidence.evaluation_digest,
                    evidence.evaluation_raw_sha256,
                    evidence.evaluation_commit,
                )
            )
        actual_identity = None
        for (
            model_name,
            version,
            role,
            snapshot_path,
            locked_snapshot_digest,
            snapshot_raw_sha256,
            snapshot_commit,
            evaluation_path,
            locked_evaluation_digest,
            evaluation_raw_sha256,
            evaluation_commit,
        ) in identities:
            stem = f"{target.isoformat()}__{model_name}__{version}.json"
            if (
                snapshot_path != f"predictions/{stem}"
                or evaluation_path != f"evaluations/{stem}"
                or not _is_strict_ancestor(
                    repository,
                    snapshot_commit,
                    evaluation_commit,
                )
                or not _is_strict_ancestor(
                    repository,
                    evaluation_commit,
                    claim_evidence.first_commit_sha,
                )
            ):
                raise GitEvidenceError(
                    "formal checkpoint Git chronology/identity is invalid"
                )
            snapshot = locked_payload(
                path=snapshot_path,
                canonical_digest=locked_snapshot_digest,
                raw_sha256=snapshot_raw_sha256,
            )
            evaluation = locked_payload(
                path=evaluation_path,
                canonical_digest=locked_evaluation_digest,
                raw_sha256=evaluation_raw_sha256,
            )
            if (
                snapshot.get("target_draw_date") != target.isoformat()
                or snapshot.get("model_name") != model_name
                or snapshot.get("model_version") != version
                or evaluation.get("target_draw_date") != target.isoformat()
                or evaluation.get("model_name") != model_name
                or evaluation.get("model_version") != version
            ):
                raise GitEvidenceError("formal look model/target identity mismatch")
            if model_name == candidate_name and (
                snapshot_digest(snapshot) != assessment.snapshot_digest
                or snapshot_digest(evaluation) != assessment.evaluation_digest
            ):
                raise GitEvidenceError("formal checkpoint digest changed after audit")
            observed_actual = (
                evaluation.get("actual"),
                evaluation.get("bonus"),
                evaluation.get("actual_draw_digest"),
            )
            if actual_identity is None:
                actual_identity = observed_actual
            elif observed_actual != actual_identity:
                raise GitEvidenceError(
                    "formal comparison outcome differs from the candidate outcome"
                )
            rows[model_name].append(
                _score_snapshot(snapshot, evaluation, expected_role=role)
            )
    return {name: tuple(values) for name, values in rows.items()}


def _formal_scope_summary(
    rows: Sequence[Mapping[str, float | int]],
    *,
    resamples: int,
    seed: int,
) -> Mapping[str, Any]:
    if not rows:
        raise ValueError("formal scope cannot be empty")

    def average(field: str) -> float:
        return math.fsum(float(row[field]) for row in rows) / len(rows)

    top12_hits = [int(row["top_12_hits"]) for row in rows]
    if any(not 0 <= value <= 6 for value in top12_hits):
        raise GitEvidenceError("formal Top-12 hits are outside 0..6")
    total = sum(top12_hits)
    lower, upper = _bootstrap_top12_lift(
        top12_hits,
        resamples=resamples,
        seed=seed,
    )
    fair_brier, fair_log_loss = _fair_constant_scores()
    avg_brier = average("brier_score")
    avg_log_loss = average("log_loss")
    avg_top12 = average("top_12_hits")
    return {
        "draws": len(rows),
        "avg_final_6_hits": average("final_6_hits"),
        "avg_top6_hits": average("top_6_hits"),
        "avg_top12_hits": avg_top12,
        "avg_top18_hits": average("top_18_hits"),
        "avg_brier": avg_brier,
        "avg_log_loss": avg_log_loss,
        "avg_actual_rank": average("mean_actual_rank"),
        "total_top12_hits": total,
        "primary_top12_lift_vs_theory": avg_top12 - _FAIR_TOP12_EXPECTATION,
        "primary_exact_one_sided_p": _exact_top12_upper_tail(total, len(rows)),
        "primary_adjusted_p": _exact_top12_upper_tail(total, len(rows)),
        "primary_bootstrap_95_ci": [lower, upper],
        "fair_constant_brier": fair_brier,
        "fair_constant_log_loss": fair_log_loss,
        "brier_delta_vs_fair": avg_brier - fair_brier,
        "log_loss_delta_vs_fair": avg_log_loss - fair_log_loss,
    }


def _require_frozen_formal_parameters(registration: Any) -> tuple[int, int, float]:
    parameters = registration.parameters
    expected = {
        "prospective_exact_eligible_evaluated_draws": 208,
        "prospective_half_draws": 104,
        "bootstrap_replicates": 10_000,
        "bootstrap_seed": 649,
        "bootstrap_rng": "numpy.default_rng",
        "bootstrap_unit": "complete_target_draw",
        "bootstrap_interval": "two_sided_95_percentile_linear",
        "primary_exact_test": "hypergeometric_draw_level_convolution_upper_tail",
        "primary_alpha": 0.05,
        "primary_multiplicity_method": (
            "single_registered_variant_no_secondary_claims"
        ),
        "proper_score_max_delta_vs_fair": 1.0e-9,
        "v1_ensemble_top12_gate_scope": "aggregate_208",
        "v1_ensemble_top12_minimum_difference": "strictly_greater_than_zero",
        "random_control_null_rule": (
            "raw_exact_p_gt_0_05_or_bootstrap_ci_includes_zero"
        ),
        "formal_invalidity_gate_keys": list(_FORMAL_INVALIDITY_GATE_KEYS),
        "formal_invalidity_decision": "archive",
        "formal_scientific_gate_failure_decision": "reject",
        "formal_all_gates_pass_decision": "eligible_for_reviewed_promotion",
    }
    mismatches = [key for key, value in expected.items() if parameters.get(key) != value]
    if mismatches:
        raise GitEvidenceError(
            "formal-look registered parameters do not match frozen implementation: "
            + ", ".join(mismatches)
        )
    if registration.prospective.minimum_eligible_draws != 208:
        raise GitEvidenceError("formal look requires exactly 208 eligible draws")
    if registration.parameters.get("formal_gate_keys") != list(_FORMAL_GATE_KEYS):
        raise GitEvidenceError("formal-look gate keys do not match frozen implementation")
    return (
        int(parameters["bootstrap_replicates"]),
        int(parameters["bootstrap_seed"]),
        float(parameters["proper_score_max_delta_vs_fair"]),
    )


def _require_exact_ready_checkpoint(aggregate: CohortAggregate) -> None:
    if (
        aggregate.status != "ready"
        or len(aggregate.checkpoint) != 208
        or aggregate.extra_evaluated
        or aggregate.formal_look_count != 0
        or aggregate.checkpoint_digest is None
    ):
        raise RuntimeError("formal look requires the exact ready 208-draw checkpoint")
    checkpoint_end = aggregate.checkpoint[-1].target_draw_date
    if checkpoint_end is None or any(
        pending.target_draw_date is not None
        and pending.target_draw_date <= checkpoint_end
        for pending in aggregate.pending
    ):
        raise RuntimeError("formal look cannot skip an earlier pending target")


def _compute_formal_look_from_ready(
    root: Path,
    registration: Any,
    aggregate: CohortAggregate,
    *,
    claim_evidence: GitFileEvidence,
    attempt_path: str,
    attempt_sha256: str,
    markdown_path: str,
    markdown_sha256: str,
) -> FormalLookComputation:
    """Private metric-reading seam; callers must first seal an attempt."""
    _require_exact_ready_checkpoint(aggregate)
    resamples, seed, tolerance = _require_frozen_formal_parameters(registration)
    rows = _formal_rows(
        root,
        registration,
        aggregate,
        claim_evidence=claim_evidence,
    )
    scopes: dict[str, dict[str, Mapping[str, Any]]] = {}
    candidate_minus_v1: dict[str, float] = {}
    for scope_name, scope_slice in _FORMAL_SCOPE_SLICES.items():
        scopes[scope_name] = {}
        for model_name, model_rows in rows.items():
            scopes[scope_name][model_name] = _formal_scope_summary(
                model_rows[scope_slice],
                resamples=resamples,
                seed=seed,
            )
        candidate_minus_v1[scope_name] = (
            scopes[scope_name][registration.model_name]["avg_top12_hits"]
            - scopes[scope_name]["ensemble"]["avg_top12_hits"]
        )

    candidate = scopes["aggregate_208"][registration.model_name]
    candidate_halves = [
        scopes["first_104"][registration.model_name],
        scopes["second_104"][registration.model_name],
    ]
    proper_summaries = [candidate, *candidate_halves]
    random_summaries = [
        scopes[scope]["random"]
        for scope in ("aggregate_208", "first_104", "second_104")
    ]

    def random_is_null(summary: Mapping[str, Any]) -> bool:
        lower, upper = summary["primary_bootstrap_95_ci"]
        return summary["primary_exact_one_sided_p"] > 0.05 or (
            lower <= 0.0 <= upper
        )

    gates = {
        "positive_aggregate_primary_lift": (
            candidate["primary_top12_lift_vs_theory"] > 0.0
        ),
        "aggregate_adjusted_p_at_most_0_05": (
            candidate["primary_adjusted_p"] <= 0.05
        ),
        "aggregate_bootstrap_lower_above_zero": (
            candidate["primary_bootstrap_95_ci"][0] > 0.0
        ),
        "positive_primary_lift_in_both_fixed_halves": all(
            summary["primary_top12_lift_vs_theory"] > 0.0
            for summary in candidate_halves
        ),
        "proper_scores_within_fair_tolerance_aggregate_and_halves": all(
            summary["brier_delta_vs_fair"] <= tolerance
            and summary["log_loss_delta_vs_fair"] <= tolerance
            for summary in proper_summaries
        ),
        "candidate_top12_mean_strictly_above_v1_ensemble": (
            candidate_minus_v1["aggregate_208"] > 0.0
        ),
        "random_control_null_aggregate_and_halves": all(
            random_is_null(summary) for summary in random_summaries
        ),
        "audit_clear": True,
    }
    if tuple(gates) != _FORMAL_GATE_KEYS:
        raise AssertionError("formal gate implementation drifted from registration")
    all_passed = all(gates.values())
    if any(not gates[key] for key in _FORMAL_INVALIDITY_GATE_KEYS):
        decision = "archive"
    elif all_passed:
        decision = "eligible_for_reviewed_promotion"
    else:
        decision = "reject"
    return FormalLookComputation(
        schema_version=1,
        experiment_id=registration.experiment_id,
        model_name=registration.model_name,
        model_version=registration.model_version,
        checkpoint_digest=aggregate.checkpoint_digest,
        eligible_evaluated_count=208,
        scopes=scopes,
        candidate_minus_v1_top12=candidate_minus_v1,
        gates=gates,
        all_gates_passed=all_passed,
        decision=decision,
        gate_outcome=decision,
        formal_claim_path=claim_evidence.path,
        formal_claim_sha256=claim_evidence.raw_sha256,
        formal_claim_commit=claim_evidence.first_commit_sha,
        formal_attempt_path=attempt_path,
        formal_attempt_sha256=attempt_sha256,
        formal_markdown_path=markdown_path,
        formal_markdown_sha256=markdown_sha256,
        procedures={
            "primary_exact_test": registration.parameters["primary_exact_test"],
            "primary_alpha": registration.parameters["primary_alpha"],
            "primary_multiplicity_method": registration.parameters[
                "primary_multiplicity_method"
            ],
            "bootstrap_replicates": resamples,
            "bootstrap_seed": seed,
            "bootstrap_rng": "numpy.default_rng",
            "bootstrap_unit": "complete_target_draw",
            "bootstrap_interval": "two_sided_95_percentile_linear",
            "proper_score_max_delta_vs_fair": tolerance,
            "formal_look_count": 1,
            "promotion": "separate_reviewed_pr_only",
        },
    )


def _registered_formal_paths(registration: Any) -> tuple[str, str, str, str]:
    parameters = (
        registration.get("parameters")
        if isinstance(registration, Mapping)
        else registration.parameters
    )
    if not isinstance(parameters, Mapping):
        raise GitEvidenceError("registered formal-look parameters are invalid")
    names = (
        "formal_look_claim",
        "formal_look_attempt",
        "formal_look_json",
        "formal_look_markdown",
    )
    values = tuple(parameters.get(name) for name in names)
    if (
        parameters.get("formal_look_schema_version") != 1
        or parameters.get("formal_look_protocol")
        != "claim_commit_before_checkpoint_aggregate_computation"
        or parameters.get("formal_look_publication")
        != "stage_both_then_publish_without_overwrite"
        or parameters.get("formal_look_prepublication_failure")
        != "archive_and_never_rerun_same_version"
        or parameters.get("formal_look_publication_commit_point")
        != "both_final_hardlinks_and_parent_directory_fsync"
        or parameters.get("formal_look_postpublication_cleanup_failure")
        != "warning_does_not_invalidate_durable_result"
        or any(not isinstance(value, str) or not value for value in values)
        or len(set(values)) != 4
    ):
        raise GitEvidenceError("registered formal-look paths/protocol are invalid")
    return values  # type: ignore[return-value]


def _path_has_git_history(repository: Path, path: str) -> bool:
    return bool(
        _git_bytes(repository, "log", "--format=%H", "--", path).decode().strip()
    )


def _fsync_directory(directory: Path) -> None:
    descriptor = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _exclusive_write(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        _fsync_directory(path.parent)
    except BaseException:
        # The permanent attempt seal must survive a post-seal failure.  Claim and
        # staging writes happen before metric access and may also remain as
        # forensic evidence instead of being silently retried.
        raise


def _canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")


def claim_registered_formal_look(
    repository: str | Path,
    experiment_id: str,
) -> Path:
    """Create the one registered claim without reading checkpoint performance."""
    root = Path(repository).resolve(strict=True)
    aggregate = audit_registered_cohort(root, experiment_id)
    _require_exact_ready_checkpoint(aggregate)
    registration = load_experiment_registry(root / REGISTRY_PATH).get(experiment_id)
    _require_frozen_formal_parameters(registration)
    claim_path, attempt_path, json_path, markdown_path = _registered_formal_paths(
        registration
    )
    for path in (claim_path, attempt_path, json_path, markdown_path):
        if (root / path).exists() or _path_has_git_history(root, path):
            raise RuntimeError(f"formal-look evidence path was already used: {path}")
    payload = {
        "schema_version": 1,
        "kind": "prospective_formal_look_claim",
        "experiment_id": experiment_id,
        "model_name": registration.model_name,
        "model_version": registration.model_version,
        "checkpoint_digest": aggregate.checkpoint_digest,
        "eligible_evaluated_count": registration.prospective.minimum_eligible_draws,
        "evidence_commit": _head_commit(root),
        "protocol": registration.parameters["formal_look_protocol"],
    }
    destination = root / claim_path
    _exclusive_write(destination, _canonical_json_bytes(payload))
    return destination


def _verified_formal_claim(
    repository: Path,
    registration: Any,
    aggregate: CohortAggregate,
    claim_path: str,
) -> GitFileEvidence:
    cohort = registration.prospective
    evidence = GitFileEvidence.from_repository(
        repository,
        claim_path,
        freeze_commit=cohort.freeze_commit,
        activation_commit=cohort.activation_commit,
    )
    if _commit_changed_paths(repository, evidence.first_commit_sha) != (claim_path,):
        raise GitEvidenceError("formal-look claim commit must change only the claim")
    payload = _read_json_mapping(repository / claim_path)
    expected = {
        "schema_version": 1,
        "kind": "prospective_formal_look_claim",
        "experiment_id": registration.experiment_id,
        "model_name": registration.model_name,
        "model_version": registration.model_version,
        "checkpoint_digest": aggregate.checkpoint_digest,
        "eligible_evaluated_count": registration.prospective.minimum_eligible_draws,
        "evidence_commit": payload.get("evidence_commit"),
        "protocol": registration.parameters["formal_look_protocol"],
    }
    if _jsonable(payload) != expected:
        raise GitEvidenceError("formal-look claim payload does not match checkpoint")
    source_commit = payload.get("evidence_commit")
    if not isinstance(source_commit, str) or not _is_strict_ancestor(
        repository,
        source_commit,
        evidence.first_commit_sha,
    ):
        raise GitEvidenceError("formal-look claim source must strictly precede claim")
    for observation in aggregate.checkpoint:
        evaluation = observation.evaluation_git_evidence
        if evaluation is None or not _is_strict_ancestor(
            repository,
            evaluation.first_commit_sha,
            evidence.first_commit_sha,
        ):
            raise GitEvidenceError(
                "formal-look claim must strictly follow every checkpoint evaluation"
            )
    return evidence


def _formal_markdown(computation: FormalLookComputation) -> bytes:
    gate_lines = "\n".join(
        f"- `{key}`: {'pass' if value else 'fail'}"
        for key, value in computation.gates.items()
    )
    text = (
        f"# Formal prospective look: {computation.experiment_id}\n\n"
        f"- Model: `{computation.model_name} {computation.model_version}`\n"
        f"- Eligible evaluations: {computation.eligible_evaluated_count}\n"
        f"- Checkpoint digest: `{computation.checkpoint_digest}`\n"
        f"- Gate outcome: `{computation.gate_outcome}`\n"
        f"- Claim commit: `{computation.formal_claim_commit}`\n\n"
        "## Frozen gates\n\n"
        f"{gate_lines}\n\n"
        "## Registered summaries\n\n"
        "```json\n"
        f"{json.dumps(_jsonable(computation.scopes), indent=2, sort_keys=True)}\n"
        "```\n\n"
        "## Candidate minus V1 ensemble (Top-12 mean)\n\n"
        "```json\n"
        f"{json.dumps(_jsonable(computation.candidate_minus_v1_top12), indent=2, sort_keys=True)}\n"
        "```\n\n"
        "## Frozen procedures\n\n"
        "```json\n"
        f"{json.dumps(_jsonable(computation.procedures), indent=2, sort_keys=True)}\n"
        "```\n"
    )
    return text.encode("utf-8")


def _publish_formal_report_pair(
    repository: Path,
    *,
    json_path: str,
    json_raw: bytes,
    markdown_path: str,
    markdown_raw: bytes,
) -> None:
    json_stage = repository / f"{json_path}.stage"
    markdown_stage = repository / f"{markdown_path}.stage"
    _exclusive_write(json_stage, json_raw)
    _exclusive_write(markdown_stage, markdown_raw)
    published: list[Path] = []
    committed = False
    try:
        for stage, destination in (
            (json_stage, repository / json_path),
            (markdown_stage, repository / markdown_path),
        ):
            os.link(stage, destination)
            published.append(destination)
        _fsync_directory((repository / json_path).parent)
        committed = True
    except BaseException:
        for destination in reversed(published):
            try:
                destination.unlink()
            except FileNotFoundError:
                pass
        _fsync_directory((repository / json_path).parent)
        raise
    finally:
        for stage in (json_stage, markdown_stage):
            try:
                stage.unlink()
            except OSError as exc:
                if committed:
                    warnings.warn(
                        f"formal report published but stage cleanup failed: {exc}",
                        RuntimeWarning,
                        stacklevel=2,
                    )
        if committed:
            try:
                _fsync_directory((repository / json_path).parent)
            except OSError as exc:
                warnings.warn(
                    f"formal report published; cleanup fsync failed: {exc}",
                    RuntimeWarning,
                    stacklevel=2,
                )


def run_registered_formal_look(
    repository: str | Path,
    experiment_id: str,
) -> FormalLookComputation:
    """Seal and publish the sole registered look after a committed claim."""
    root = Path(repository).resolve(strict=True)
    aggregate = audit_registered_cohort(root, experiment_id)
    _require_exact_ready_checkpoint(aggregate)
    registration = load_experiment_registry(root / REGISTRY_PATH).get(experiment_id)
    claim_path, attempt_path, json_path, markdown_path = _registered_formal_paths(
        registration
    )
    if any(
        (root / path).exists() or _path_has_git_history(root, path)
        for path in (attempt_path, json_path, markdown_path)
    ):
        raise RuntimeError("formal-look attempt/report path was already used")
    claim_evidence = _verified_formal_claim(
        root,
        registration,
        aggregate,
        claim_path,
    )

    attempt_payload = {
        "schema_version": 1,
        "kind": "prospective_formal_look_attempt",
        "experiment_id": experiment_id,
        "model_name": registration.model_name,
        "model_version": registration.model_version,
        "checkpoint_digest": aggregate.checkpoint_digest,
        "eligible_evaluated_count": registration.prospective.minimum_eligible_draws,
        "formal_claim_path": claim_path,
        "formal_claim_sha256": claim_evidence.raw_sha256,
        "formal_claim_commit": claim_evidence.first_commit_sha,
    }
    attempt_raw = _canonical_json_bytes(attempt_payload)
    _exclusive_write(root / attempt_path, attempt_raw)
    try:
        attempt_raw = (root / attempt_path).read_bytes()
    except OSError as exc:
        raise GitEvidenceError("formal-look attempt evidence is unavailable") from exc
    validate_formal_attempt_payload(
        attempt_raw,
        registration=registration,
        ready_aggregate=aggregate,
        claim_evidence=claim_evidence,
    )
    attempt_sha256 = sha256(attempt_raw).hexdigest()

    computation = _compute_formal_look_from_ready(
        root,
        registration,
        aggregate,
        claim_evidence=claim_evidence,
        attempt_path=attempt_path,
        attempt_sha256=attempt_sha256,
        markdown_path=markdown_path,
        markdown_sha256="",
    )
    markdown_raw = _formal_markdown(computation)
    computation = replace(
        computation,
        formal_markdown_sha256=sha256(markdown_raw).hexdigest(),
    )
    json_raw = _canonical_json_bytes(computation.to_json_dict())
    try:
        current_attempt_raw = (root / attempt_path).read_bytes()
    except OSError as exc:
        raise GitEvidenceError("formal-look attempt evidence is unavailable") from exc
    validate_formal_attempt_payload(
        current_attempt_raw,
        registration=registration,
        ready_aggregate=aggregate,
        claim_evidence=claim_evidence,
    )
    if current_attempt_raw != attempt_raw:
        raise GitEvidenceError("formal-look attempt changed during computation")
    _publish_formal_report_pair(
        root,
        json_path=json_path,
        json_raw=json_raw,
        markdown_path=markdown_path,
        markdown_raw=markdown_raw,
    )
    return computation
