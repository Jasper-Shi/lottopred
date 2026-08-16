from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
import csv
from dataclasses import dataclass, field
from datetime import date, datetime, time
from hashlib import sha256
import io
import json
import math
from pathlib import Path
import subprocess
from typing import Any
from zoneinfo import ZoneInfo

import yaml

from .domain import Draw, Prediction


TORONTO = ZoneInfo("America/Toronto")
EXPECTED_HISTORICAL_PARTITIONS = {
    "development": (date(1982, 1, 1), date(2014, 12, 31)),
    "legacy_validation": (date(2015, 1, 1), date(2019, 12, 31)),
    "consumed_diagnostic": (date(2020, 1, 1), date(2025, 12, 31)),
}
VALID_EXPERIMENT_STATUSES = {
    "registered",
    "historical_diagnostic_complete",
    "prospective_shadow",
    "closed_rejected",
    "closed_archived",
    "promoted",
}


def _as_date(value: object, field: str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"{field} must be an ISO date") from exc
    raise ValueError(f"{field} must be an ISO date")


def _as_mapping(value: object, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be a mapping")
    return value


@dataclass(frozen=True)
class DateRange:
    start: date
    end: date

    def __post_init__(self) -> None:
        if self.start > self.end:
            raise ValueError("partition start must not be after its end")


@dataclass(frozen=True)
class NegativeControlSpec:
    kind: str
    seed: int

    def __post_init__(self) -> None:
        if self.kind != "whole_draw_date_permutation":
            raise ValueError(f"unsupported negative control: {self.kind}")
        if self.seed < 0:
            raise ValueError("negative-control seed must be non-negative")


@dataclass(frozen=True)
class OutcomeBoundary:
    source_commit: str
    sha256: str
    draw_count: int
    history_through: date

    def __post_init__(self) -> None:
        if len(self.source_commit) != 40 or any(
            character not in "0123456789abcdef" for character in self.source_commit
        ):
            raise ValueError("outcome-boundary source commit must be a full lowercase Git SHA")
        if len(self.sha256) != 64 or any(
            character not in "0123456789abcdef" for character in self.sha256
        ):
            raise ValueError("outcome-boundary fingerprint must be a lowercase SHA-256 digest")
        if self.draw_count < 1:
            raise ValueError("outcome-boundary draw count must be positive")


@dataclass(frozen=True)
class ProspectiveCohortSpec:
    status: str
    role: str
    minimum_eligible_draws: int
    commit_deadline: str
    freeze_commit: str | None
    activation_commit: str | None
    outcomes_known_at_activation: OutcomeBoundary | None
    cohort_start: date | None

    def __post_init__(self) -> None:
        if self.status not in {"not_activated", "active", "closed"}:
            raise ValueError(f"unsupported cohort status: {self.status}")
        if self.role != "shadow":
            raise ValueError("new research cohorts must begin with role=shadow")
        if self.minimum_eligible_draws < 104:
            raise ValueError("prospective cohorts require at least 104 eligible draws")
        if self.minimum_eligible_draws % 2:
            raise ValueError("prospective cohort minimum must split into two equal halves")
        if self.commit_deadline != "before_target_local_date":
            raise ValueError("cohort commit deadline must be before_target_local_date")
        activation_fields = (
            self.freeze_commit,
            self.activation_commit,
            self.outcomes_known_at_activation,
            self.cohort_start,
        )
        if self.status == "not_activated" and any(
            value is not None for value in activation_fields
        ):
            raise ValueError("an unactivated cohort requires all activation fields to be null")
        if self.status in {"active", "closed"} and any(
            value is None for value in activation_fields
        ):
            raise ValueError(
                "an activated cohort requires a freeze commit, activation commit, "
                "outcome boundary, and start date"
            )
        for field_name, commit in (
            ("freeze", self.freeze_commit),
            ("activation", self.activation_commit),
        ):
            if commit is not None and (
                len(commit) != 40
                or any(character not in "0123456789abcdef" for character in commit)
            ):
                raise ValueError(f"{field_name} commit must be a full lowercase Git SHA")


@dataclass(frozen=True)
class ExperimentResult:
    decision: str
    decided_on: date
    implementation_commit: str
    report_json: str
    report_markdown: str
    result_file: str
    historical_primary_signal_supported: bool
    shadow_activation: str

    def __post_init__(self) -> None:
        if self.decision not in {"reject", "archive", "continue_shadow", "promote"}:
            raise ValueError(f"unsupported experiment decision: {self.decision}")
        if len(self.implementation_commit) != 40 or any(
            character not in "0123456789abcdef"
            for character in self.implementation_commit
        ):
            raise ValueError("implementation commit must be a full lowercase Git SHA")
        if not self.report_json or not self.report_markdown or not self.result_file:
            raise ValueError("experiment result paths must be recorded")
        if self.shadow_activation not in {"not_activated", "active", "closed"}:
            raise ValueError(
                f"unsupported result shadow activation: {self.shadow_activation}"
            )


def _terminal_result_digest(result: ExperimentResult) -> str:
    encoded = "\x00".join(
        (
            result.decision,
            result.decided_on.isoformat(),
            result.implementation_commit,
            result.report_json,
            result.report_markdown,
            result.result_file,
            str(result.historical_primary_signal_supported),
            result.shadow_activation,
        )
    ).encode()
    return sha256(encoded).hexdigest()


def _cohort_activation_digest(
    model_name: str,
    model_version: str,
    cohort: ProspectiveCohortSpec,
) -> str:
    boundary = cohort.outcomes_known_at_activation
    if (
        cohort.status not in {"active", "closed"}
        or cohort.freeze_commit is None
        or cohort.activation_commit is None
        or boundary is None
        or cohort.cohort_start is None
    ):
        raise ValueError("activated cohort lock requires complete activation fields")
    encoded = "\x00".join(
        (
            model_name,
            model_version,
            cohort.role,
            str(cohort.minimum_eligible_draws),
            cohort.commit_deadline,
            cohort.freeze_commit,
            cohort.activation_commit,
            boundary.source_commit,
            boundary.sha256,
            str(boundary.draw_count),
            boundary.history_through.isoformat(),
            cohort.cohort_start.isoformat(),
        )
    ).encode()
    return sha256(encoded).hexdigest()


# Terminal seals are append-only code anchors. They prevent a terminal registry
# decision from being erased and reloaded as a fresh experiment without an
# explicit, reviewable protocol-code change.
KNOWN_TERMINAL_RESULT_SEALS = {
    "V5_pair_affinity": (
        "1b1e73bf090770d7ad9fff2d30cc0b93b2f51afa4308eb3294b5f15657592add"
    ),
    "V6_fixed_boundary_js_regime": (
        "74bda907c42243890ef74f59f3e626ca37204a2863bf18d5aadde738e4c7cc57"
    ),
}


@dataclass(frozen=True)
class ExperimentRegistration:
    experiment_id: str
    family: str
    model_name: str
    model_version: str
    status: str
    registration_file: str
    registered_on: date
    seed: int
    primary_metric: str
    multiplicity_family: str
    variant_index: int
    dataset_path: str
    dataset_source_commit: str
    dataset_sha256: str
    dataset_draw_count: int
    registration_history_through: date
    outcomes_known_through: date
    outcomes_known_source_commit: str
    outcomes_known_sha256: str
    outcomes_known_draw_count: int
    partitions: Mapping[str, DateRange]
    negative_controls: tuple[NegativeControlSpec, ...]
    parameters: Mapping[str, Any]
    prospective: ProspectiveCohortSpec
    result: ExperimentResult | None
    _terminal_result_lock: str | None = field(
        default=None,
        repr=False,
        compare=False,
    )
    _cohort_activation_lock: str | None = field(
        default=None,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        if not self.experiment_id or not self.family:
            raise ValueError("experiment id and family are required")
        if not self.model_name or not self.model_version:
            raise ValueError("model name and version are required")
        if self.status not in VALID_EXPERIMENT_STATUSES:
            raise ValueError(f"unsupported experiment status: {self.status}")
        if self.seed < 0 or self.variant_index < 1:
            raise ValueError("seed must be non-negative and variant_index must be positive")
        if len(self.dataset_sha256) != 64 or any(c not in "0123456789abcdef" for c in self.dataset_sha256):
            raise ValueError("dataset_sha256 must be a lowercase SHA-256 digest")
        if len(self.dataset_source_commit) != 40 or any(
            c not in "0123456789abcdef" for c in self.dataset_source_commit
        ):
            raise ValueError("dataset source commit must be a full lowercase Git SHA")
        if self.dataset_draw_count < 1:
            raise ValueError("registration dataset draw count must be positive")
        if len(self.outcomes_known_source_commit) != 40 or any(
            c not in "0123456789abcdef"
            for c in self.outcomes_known_source_commit
        ):
            raise ValueError(
                "known-outcomes source commit must be a full lowercase Git SHA"
            )
        if len(self.outcomes_known_sha256) != 64 or any(
            c not in "0123456789abcdef" for c in self.outcomes_known_sha256
        ):
            raise ValueError(
                "known-outcomes dataset fingerprint must be a lowercase SHA-256 digest"
            )
        if self.outcomes_known_draw_count < self.dataset_draw_count:
            raise ValueError(
                "known-outcomes draw count cannot precede the diagnostic prefix"
            )
        if self.outcomes_known_through < self.registration_history_through:
            raise ValueError(
                "known outcomes cannot end before the registered diagnostic prefix"
            )
        if self.outcomes_known_through > self.registered_on:
            raise ValueError("known outcomes cannot extend beyond registration date")
        if (
            self.prospective.cohort_start is not None
            and self.prospective.cohort_start <= self.outcomes_known_through
        ):
            raise ValueError(
                "prospective cohort must start after all outcomes known at registration"
            )
        activation_boundary = self.prospective.outcomes_known_at_activation
        if activation_boundary is not None and (
            activation_boundary.history_through < self.outcomes_known_through
            or activation_boundary.draw_count < self.outcomes_known_draw_count
        ):
            raise ValueError(
                "activation boundary cannot precede outcomes known at registration"
            )
        if (
            activation_boundary is not None
            and self.prospective.cohort_start is not None
            and self.prospective.cohort_start
            <= activation_boundary.history_through
        ):
            raise ValueError(
                "prospective cohort must start strictly after activation-known outcomes"
            )
        if self.prospective.status in {"active", "closed"}:
            activation_lock = _cohort_activation_digest(
                self.model_name,
                self.model_version,
                self.prospective,
            )
            if self._cohort_activation_lock is None:
                object.__setattr__(
                    self,
                    "_cohort_activation_lock",
                    activation_lock,
                )
            elif self._cohort_activation_lock != activation_lock:
                raise ValueError("activated cohort identity cannot be changed")
        elif self._cohort_activation_lock is not None:
            raise ValueError("activated cohort cannot be reset or reopened")
        if self.primary_metric != "top12_hits_lift_vs_theory":
            raise ValueError(
                "registered primary metric must remain top12_hits_lift_vs_theory"
            )
        if not self.negative_controls:
            raise ValueError("at least one negative control is required")
        if set(self.partitions) != set(EXPECTED_HISTORICAL_PARTITIONS):
            raise ValueError("historical partitions must use the three registered evidence lanes")
        for name, expected in EXPECTED_HISTORICAL_PARTITIONS.items():
            actual = self.partitions[name]
            if (actual.start, actual.end) != expected:
                raise ValueError(f"{name} must remain fixed at {expected[0]} through {expected[1]}")
        terminal_decisions = {"reject", "archive", "promote"}
        if self.result is not None and self.result.decision in terminal_decisions:
            result_lock = _terminal_result_digest(self.result)
            if self._terminal_result_lock is None:
                object.__setattr__(self, "_terminal_result_lock", result_lock)
            elif self._terminal_result_lock != result_lock:
                raise ValueError("terminal result cannot be replaced")
        elif self._terminal_result_lock is not None:
            raise ValueError("terminal result cannot be removed or reopened")

        sealed_result = KNOWN_TERMINAL_RESULT_SEALS.get(self.experiment_id)
        if sealed_result is not None and (
            self.result is None
            or self.result.decision not in terminal_decisions
            or _terminal_result_digest(self.result) != sealed_result
        ):
            raise ValueError(
                f"{self.experiment_id} sealed terminal result cannot be removed or changed"
            )

        if self.result is not None and (
            self.result.shadow_activation != self.prospective.status
        ):
            raise ValueError("result and prospective cohort statuses must agree")
        decision = self.result.decision if self.result is not None else None
        allowed_states = {
            "registered": {(None, "not_activated")},
            "historical_diagnostic_complete": {(None, "not_activated")},
            "prospective_shadow": {("continue_shadow", "active")},
            "closed_rejected": {
                ("reject", "not_activated"),
                ("reject", "closed"),
            },
            "closed_archived": {
                ("archive", "not_activated"),
                ("archive", "closed"),
            },
            "promoted": {("promote", "closed")},
        }
        if (decision, self.prospective.status) not in allowed_states[self.status]:
            if self.status == "prospective_shadow":
                raise ValueError(
                    "prospective_shadow requires a continue_shadow result and active cohort"
                )
            raise ValueError(
                "experiment status, result decision, and prospective status are inconsistent"
            )


@dataclass(frozen=True)
class ExperimentRegistry:
    schema_version: int
    experiments: tuple[ExperimentRegistration, ...]

    def get(self, experiment_id: str) -> ExperimentRegistration:
        matches = [item for item in self.experiments if item.experiment_id == experiment_id]
        if not matches:
            raise KeyError(experiment_id)
        return matches[0]


def _parse_registration(raw: Mapping[str, Any]) -> ExperimentRegistration:
    partition_raw = _as_mapping(raw.get("historical_partitions"), "historical_partitions")
    partitions = {
        name: DateRange(
            _as_date(_as_mapping(value, name).get("start"), f"{name}.start"),
            _as_date(_as_mapping(value, name).get("end"), f"{name}.end"),
        )
        for name, value in partition_raw.items()
    }

    controls_raw = raw.get("negative_controls")
    if not isinstance(controls_raw, list):
        raise ValueError("negative_controls must be a list")
    controls = tuple(
        NegativeControlSpec(
            kind=str(_as_mapping(value, "negative_control").get("kind", "")),
            seed=int(_as_mapping(value, "negative_control").get("seed", -1)),
        )
        for value in controls_raw
    )

    dataset = _as_mapping(raw.get("registration_dataset"), "registration_dataset")
    known_outcomes = _as_mapping(
        raw.get("outcomes_known_at_registration"),
        "outcomes_known_at_registration",
    )
    prospective_raw = _as_mapping(raw.get("prospective"), "prospective")
    cohort_start_raw = prospective_raw.get("cohort_start")
    activation_boundary_raw = prospective_raw.get("outcomes_known_at_activation")
    activation_boundary = None
    if activation_boundary_raw is not None:
        boundary = _as_mapping(
            activation_boundary_raw,
            "prospective.outcomes_known_at_activation",
        )
        activation_boundary = OutcomeBoundary(
            source_commit=str(boundary.get("source_commit", "")),
            sha256=str(boundary.get("sha256", "")),
            draw_count=int(boundary.get("draw_count", 0)),
            history_through=_as_date(
                boundary.get("history_through"),
                "prospective.outcomes_known_at_activation.history_through",
            ),
        )
    prospective = ProspectiveCohortSpec(
        status=str(prospective_raw.get("status", "")),
        role=str(prospective_raw.get("role", "")),
        minimum_eligible_draws=int(prospective_raw.get("minimum_eligible_draws", 0)),
        commit_deadline=str(prospective_raw.get("commit_deadline", "")),
        freeze_commit=prospective_raw.get("freeze_commit"),
        activation_commit=prospective_raw.get("activation_commit"),
        outcomes_known_at_activation=activation_boundary,
        cohort_start=(
            _as_date(cohort_start_raw, "prospective.cohort_start")
            if cohort_start_raw is not None
            else None
        ),
    )

    result_raw = raw.get("result")
    result = None
    if result_raw is not None:
        result_mapping = _as_mapping(result_raw, "result")
        historical_primary_signal_supported = result_mapping.get(
            "historical_primary_signal_supported"
        )
        if not isinstance(historical_primary_signal_supported, bool):
            raise ValueError(
                "result.historical_primary_signal_supported must be a boolean"
            )
        result = ExperimentResult(
            decision=str(result_mapping.get("decision", "")),
            decided_on=_as_date(result_mapping.get("decided_on"), "result.decided_on"),
            implementation_commit=str(result_mapping.get("implementation_commit", "")),
            report_json=str(result_mapping.get("report_json", "")),
            report_markdown=str(result_mapping.get("report_markdown", "")),
            result_file=str(result_mapping.get("result_file", "")),
            historical_primary_signal_supported=historical_primary_signal_supported,
            shadow_activation=str(result_mapping.get("shadow_activation", "")),
        )

    return ExperimentRegistration(
        experiment_id=str(raw.get("id", "")),
        family=str(raw.get("family", "")),
        model_name=str(raw.get("model_name", "")),
        model_version=str(raw.get("model_version", "")),
        status=str(raw.get("status", "")),
        registration_file=str(raw.get("registration_file", "")),
        registered_on=_as_date(raw.get("registered_on"), "registered_on"),
        seed=int(raw.get("seed", -1)),
        primary_metric=str(raw.get("primary_metric", "")),
        multiplicity_family=str(raw.get("multiplicity_family", "")),
        variant_index=int(raw.get("variant_index", 0)),
        dataset_path=str(dataset.get("path", "")),
        dataset_source_commit=str(dataset.get("source_commit", "")),
        dataset_sha256=str(dataset.get("sha256", "")),
        dataset_draw_count=int(dataset.get("draw_count", 0)),
        registration_history_through=_as_date(dataset.get("history_through"), "history_through"),
        outcomes_known_through=_as_date(
            known_outcomes.get("history_through"),
            "outcomes_known_at_registration.history_through",
        ),
        outcomes_known_source_commit=str(known_outcomes.get("source_commit", "")),
        outcomes_known_sha256=str(known_outcomes.get("sha256", "")),
        outcomes_known_draw_count=int(known_outcomes.get("draw_count", 0)),
        partitions=partitions,
        negative_controls=controls,
        parameters=_as_mapping(raw.get("parameters"), "parameters"),
        prospective=prospective,
        result=result,
    )


def load_experiment_registry(path: str | Path) -> ExperimentRegistry:
    registry_path = Path(path)
    payload = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    root = _as_mapping(payload, "registry")
    schema_version = int(root.get("schema_version", 0))
    if schema_version != 2:
        raise ValueError(f"unsupported registry schema version: {schema_version}")
    raw_experiments = root.get("experiments")
    if not isinstance(raw_experiments, list) or not raw_experiments:
        raise ValueError("registry must contain at least one experiment")
    experiments = tuple(
        _parse_registration(_as_mapping(raw, "experiment")) for raw in raw_experiments
    )
    ids = [item.experiment_id for item in experiments]
    identities = [(item.model_name, item.model_version) for item in experiments]
    family_variants = [(item.multiplicity_family, item.variant_index) for item in experiments]
    if len(ids) != len(set(ids)):
        raise ValueError("experiment ids must be unique")
    missing_sealed = set(KNOWN_TERMINAL_RESULT_SEALS) - set(ids)
    if missing_sealed:
        raise ValueError(
            "registry is missing sealed terminal experiment(s): "
            + ", ".join(sorted(missing_sealed))
        )
    if len(identities) != len(set(identities)):
        raise ValueError("model name/version identities must be unique")
    if len(family_variants) != len(set(family_variants)):
        raise ValueError("multiplicity-family variant indices must be unique")
    return ExperimentRegistry(schema_version=schema_version, experiments=experiments)


def validate_draw_chronology(draws: Sequence[Draw]) -> None:
    dates = [draw.draw_date for draw in draws]
    if dates != sorted(dates):
        raise ValueError("draws must be in chronological order")
    if len(dates) != len(set(dates)):
        raise ValueError("draw dates must be unique")


def assert_history_precedes_target(history: Sequence[Draw], target_date: date) -> None:
    if not history:
        raise ValueError("history must not be empty")
    validate_draw_chronology(history)
    if history[-1].draw_date >= target_date:
        raise ValueError(
            f"history through {history[-1].draw_date} is not strictly before target {target_date}"
        )


@dataclass(frozen=True)
class WalkForwardFold:
    history: tuple[Draw, ...]
    target: Draw

    def __post_init__(self) -> None:
        assert_history_precedes_target(self.history, self.target.draw_date)


def walk_forward_folds(
    draws: Sequence[Draw],
    start: date,
    end: date,
    minimum_history_draws: int,
) -> Iterator[WalkForwardFold]:
    if minimum_history_draws < 1:
        raise ValueError("minimum_history_draws must be positive")
    validate_draw_chronology(draws)
    for index, target in enumerate(draws):
        if index < minimum_history_draws or not (start <= target.draw_date <= end):
            continue
        yield WalkForwardFold(history=tuple(draws[:index]), target=target)


def _permutation_order(length: int, seed: int) -> list[int]:
    order = sorted(
        range(length),
        key=lambda index: sha256(f"lotto649-control-v1:{seed}:{index}".encode()).digest(),
    )
    if length > 1 and order == list(range(length)):
        order = order[1:] + order[:1]
    return order


def permute_draw_outcomes(draws: Sequence[Draw], seed: int = 649) -> list[Draw]:
    """Assign intact outcomes to different fixed dates for a deterministic null.

    The permutation is created before walk-forward evaluation. Models then run on
    the permuted chronology through the same history/target pipeline as the
    candidate. The transformed series is a negative control, never evidence.
    """
    if seed < 0:
        raise ValueError("seed must be non-negative")
    validate_draw_chronology(draws)
    order = _permutation_order(len(draws), seed)
    return [
        Draw(target.draw_date, draws[source_index].numbers, draws[source_index].bonus)
        for target, source_index in zip(draws, order)
    ]


def draws_fingerprint(draws: Sequence[Draw]) -> str:
    validate_draw_chronology(draws)
    canonical = [
        {
            "draw_date": draw.draw_date.isoformat(),
            "numbers": list(draw.numbers),
            "bonus": draw.bonus,
        }
        for draw in draws
    ]
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
    return sha256(encoded).hexdigest()


def file_sha256(path: str | Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _csv_prefix_sha256(path: str | Path, data_row_count: int) -> str:
    """Hash the CSV header and exactly ``data_row_count`` physical data rows."""
    if data_row_count < 1:
        raise ValueError("registered CSV row count must be positive")

    digest = sha256()
    with Path(path).open("rb") as stream:
        header = stream.readline()
        if not header:
            raise RuntimeError("registration dataset CSV is missing its header")
        digest.update(header)
        for _ in range(data_row_count):
            row = stream.readline()
            if not row:
                raise RuntimeError("registration dataset prefix is truncated")
            digest.update(row)
    return digest.hexdigest()


def validated_registered_draw_prefix(
    path: str | Path,
    draws: Sequence[Draw],
    *,
    expected_sha256: str,
    draw_count: int,
    history_through: date,
) -> tuple[Draw, ...]:
    """Return the immutable registered prefix after strict append-only checks.

    The registered digest covers the raw CSV header and registered physical
    rows, including their original line endings. Later rows may be appended,
    but the registered bytes, chronology, and history boundary may not change.
    """
    if draw_count < 1:
        raise ValueError("registered CSV row count must be positive")
    try:
        validate_draw_chronology(draws)
    except ValueError as exc:
        raise RuntimeError("current dataset is not a strict chronological append") from exc
    if len(draws) < draw_count:
        raise RuntimeError("registration dataset prefix is truncated")

    prefix = tuple(draws[:draw_count])
    if prefix[-1].draw_date != history_through:
        raise RuntimeError("registration dataset history boundary mismatch")
    actual_sha256 = _csv_prefix_sha256(path, draw_count)
    if actual_sha256 != expected_sha256:
        raise RuntimeError("registration dataset prefix fingerprint mismatch")
    return prefix


def snapshot_digest(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return sha256(encoded).hexdigest()


def draw_digest(draw: Draw) -> str:
    return snapshot_digest(
        {
            "target_draw_date": draw.draw_date.isoformat(),
            "actual": list(draw.numbers),
            "bonus": draw.bonus,
        }
    )


class GitEvidenceError(RuntimeError):
    """Raised when immutable Git evidence cannot be proved from repository state."""


_GIT_EVIDENCE_FACTORY_TOKEN = object()


def _git_output(repo: Path, *arguments: str) -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo), *arguments],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = ""
        if isinstance(exc, subprocess.CalledProcessError):
            detail = (exc.stderr or "").strip()
        suffix = f": {detail}" if detail else ""
        raise GitEvidenceError(f"Git evidence command failed{suffix}") from exc
    return completed.stdout


def _git_bytes(repo: Path, *arguments: str) -> bytes:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo), *arguments],
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = ""
        if isinstance(exc, subprocess.CalledProcessError):
            detail = exc.stderr.decode(errors="replace").strip()
        suffix = f": {detail}" if detail else ""
        raise GitEvidenceError(f"Git evidence command failed{suffix}") from exc
    return completed.stdout


def _require_complete_repository(repo: Path) -> None:
    shallow = _git_output(repo, "rev-parse", "--is-shallow-repository").strip()
    if shallow != "false":
        raise GitEvidenceError("Git evidence requires a complete, non-shallow repository")


def _is_ancestor(repo: Path, ancestor: str, descendant: str) -> bool:
    completed = subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "merge-base",
            "--is-ancestor",
            ancestor,
            descendant,
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode == 0:
        return True
    if completed.returncode == 1:
        return False
    raise GitEvidenceError("Git ancestry check failed")


def _full_commit(repo: Path, value: str, field_name: str) -> str:
    if len(value) != 40 or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise GitEvidenceError(f"{field_name} must be a full lowercase Git SHA")
    resolved = _git_output(repo, "rev-parse", f"{value}^{{commit}}").strip()
    if resolved != value:
        raise GitEvidenceError(f"{field_name} does not resolve to the exact commit")
    return resolved


@dataclass(frozen=True, init=False)
class GitFileEvidence:
    repository: Path
    path: str
    first_commit_sha: str
    first_commit_at: datetime
    canonical_digest: str
    raw_sha256: str
    commit_count: int
    freeze_commit: str
    activation_commit: str
    _factory_token: object = field(repr=False, compare=False)

    def __init__(self) -> None:
        raise TypeError("GitFileEvidence must be derived from a repository")

    @classmethod
    def _create(cls, **values: Any) -> GitFileEvidence:
        instance = object.__new__(cls)
        values["_factory_token"] = _GIT_EVIDENCE_FACTORY_TOKEN
        for name, value in values.items():
            object.__setattr__(instance, name, value)
        if instance.first_commit_at.tzinfo is None:
            raise GitEvidenceError("Git first-commit time must be timezone-aware")
        if instance.commit_count != 1:
            raise GitEvidenceError("audited file must have exactly one commit")
        return instance

    @classmethod
    def from_repository(
        cls,
        repository: str | Path,
        file_path: str | Path,
        *,
        freeze_commit: str,
        activation_commit: str,
    ) -> GitFileEvidence:
        """Derive fail-closed immutable-file evidence using read-only Git commands.

        Git's aware committer timestamp is auditable repository metadata, but it
        is not an externally witnessed publication receipt. Remote attestation
        is deliberately outside this local verifier's claim.
        """
        repo = Path(repository).resolve(strict=True)
        top_level = Path(
            _git_output(repo, "rev-parse", "--show-toplevel").strip()
        ).resolve(strict=True)
        if top_level != repo:
            raise GitEvidenceError("repository must be the Git worktree top level")
        _require_complete_repository(repo)

        candidate = Path(file_path)
        absolute_path = (
            candidate.resolve(strict=True)
            if candidate.is_absolute()
            else (repo / candidate).resolve(strict=True)
        )
        try:
            relative_path = absolute_path.relative_to(repo).as_posix()
        except ValueError as exc:
            raise GitEvidenceError("audited file must be inside the repository") from exc
        if relative_path == ".git" or relative_path.startswith(".git/"):
            raise GitEvidenceError("Git metadata cannot be used as file evidence")

        freeze_sha = _full_commit(repo, freeze_commit, "freeze commit")
        activation_sha = _full_commit(repo, activation_commit, "activation commit")
        if freeze_sha == activation_sha or not _is_ancestor(
            repo, freeze_sha, activation_sha
        ):
            raise GitEvidenceError(
                "freeze commit must be a strict ancestor of activation commit"
            )

        dirty = _git_output(
            repo,
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
            "--",
            relative_path,
        ).strip()
        if dirty:
            raise GitEvidenceError("audited file differs from committed Git state")

        commits = tuple(
            line
            for line in _git_output(
                repo,
                "log",
                "--follow",
                "--format=%H",
                "--",
                relative_path,
            ).splitlines()
            if line
        )
        if len(commits) != 1:
            raise GitEvidenceError("audited file must have exactly one commit")
        first_commit = commits[0]
        additions = tuple(
            line
            for line in _git_output(
                repo,
                "log",
                "--follow",
                "--diff-filter=A",
                "--format=%H",
                "--",
                relative_path,
            ).splitlines()
            if line
        )
        if additions != (first_commit,):
            raise GitEvidenceError("audited file lacks one unambiguous first-add commit")

        for field_name, ancestor in (
            ("freeze", freeze_sha),
            ("activation", activation_sha),
        ):
            if ancestor == first_commit or not _is_ancestor(
                repo, ancestor, first_commit
            ):
                raise GitEvidenceError(
                    f"{field_name} commit is not a strict ancestor of the file's first commit"
                )

        original_bytes = _git_bytes(repo, "show", f"{first_commit}:{relative_path}")
        try:
            original_payload = json.loads(original_bytes.decode("utf-8"))
            current_payload = json.loads(absolute_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise GitEvidenceError("audited file must contain valid UTF-8 JSON") from exc
        if not isinstance(original_payload, Mapping) or not isinstance(
            current_payload, Mapping
        ):
            raise GitEvidenceError("audited JSON root must be a mapping")
        original_digest = snapshot_digest(original_payload)
        if snapshot_digest(current_payload) != original_digest:
            raise GitEvidenceError("current canonical JSON differs from its first commit")

        committed_at_raw = _git_output(
            repo,
            "show",
            "-s",
            "--format=%cI",
            first_commit,
        ).strip()
        try:
            committed_at = datetime.fromisoformat(committed_at_raw)
        except ValueError as exc:
            raise GitEvidenceError("Git first-commit time is invalid") from exc
        if committed_at.tzinfo is None:
            raise GitEvidenceError("Git first-commit time must be timezone-aware")

        return cls._create(
            repository=repo,
            path=relative_path,
            first_commit_sha=first_commit,
            first_commit_at=committed_at,
            canonical_digest=original_digest,
            raw_sha256=sha256(original_bytes).hexdigest(),
            commit_count=len(commits),
            freeze_commit=freeze_sha,
            activation_commit=activation_sha,
        )


_OUTCOME_EVIDENCE_FACTORY_TOKEN = object()
OUTCOME_DATA_PATH = "data/processed/draws.csv"


def _draws_from_csv_blob(raw: bytes) -> tuple[Draw, ...]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise GitEvidenceError("outcome data blob must be valid UTF-8") from exc
    rows = csv.reader(io.StringIO(text, newline=""))
    try:
        header = next(rows)
    except StopIteration as exc:
        raise GitEvidenceError("outcome data blob is empty") from exc
    expected_header = ["draw_date", "n1", "n2", "n3", "n4", "n5", "n6", "bonus"]
    if header != expected_header:
        raise GitEvidenceError("outcome data blob has an unexpected CSV header")

    draws: list[Draw] = []
    try:
        for row in rows:
            if not row:
                continue
            if len(row) != 8:
                raise GitEvidenceError("outcome data blob has a malformed CSV row")
            draws.append(
                Draw(
                    date.fromisoformat(row[0]),
                    tuple(int(value) for value in row[1:7]),
                    int(row[7]),
                )
            )
    except (TypeError, ValueError) as exc:
        raise GitEvidenceError("outcome data blob contains an invalid draw") from exc
    if not draws:
        raise GitEvidenceError("outcome data blob contains no draws")
    try:
        validate_draw_chronology(draws)
    except ValueError as exc:
        raise GitEvidenceError("outcome data blob is not strictly chronological") from exc
    return tuple(draws)


def _verified_boundary_blob(
    repo: Path,
    boundary: OutcomeBoundary,
) -> tuple[bytes, tuple[Draw, ...]]:
    source_commit = _full_commit(repo, boundary.source_commit, "outcome source commit")
    raw = _git_bytes(repo, "show", f"{source_commit}:{OUTCOME_DATA_PATH}")
    if sha256(raw).hexdigest() != boundary.sha256:
        raise GitEvidenceError("outcome data raw SHA-256 does not match its boundary")
    draws = _draws_from_csv_blob(raw)
    if len(draws) != boundary.draw_count:
        raise GitEvidenceError("outcome data draw count does not match its boundary")
    if draws[-1].draw_date != boundary.history_through:
        raise GitEvidenceError("outcome data last date does not match its boundary")
    return raw, draws


@dataclass(frozen=True, init=False)
class VerifiedOutcomeBoundary:
    repository: Path
    path: str
    boundary: OutcomeBoundary
    registration_boundary: OutcomeBoundary
    raw_sha256: str
    draws_fingerprint: str
    registration_raw_sha256: str
    draws: tuple[Draw, ...] = field(repr=False)
    _factory_token: object = field(repr=False, compare=False)

    def __init__(self) -> None:
        raise TypeError("VerifiedOutcomeBoundary must be derived from Git blobs")

    @classmethod
    def _create(cls, **values: Any) -> VerifiedOutcomeBoundary:
        instance = object.__new__(cls)
        values["_factory_token"] = _OUTCOME_EVIDENCE_FACTORY_TOKEN
        for name, value in values.items():
            object.__setattr__(instance, name, value)
        return instance

    @property
    def registration_prefix_preserved(self) -> bool:
        return True

    @classmethod
    def from_repository(
        cls,
        repository: str | Path,
        boundary: OutcomeBoundary,
        *,
        registration_boundary: OutcomeBoundary,
    ) -> VerifiedOutcomeBoundary:
        """Verify activation and registration-known data directly from Git blobs."""
        repo = Path(repository).resolve(strict=True)
        top_level = Path(
            _git_output(repo, "rev-parse", "--show-toplevel").strip()
        ).resolve(strict=True)
        if repo != top_level:
            raise GitEvidenceError("repository must be the Git worktree top level")
        _require_complete_repository(repo)

        activation_commit = _full_commit(
            repo,
            boundary.source_commit,
            "activation outcome source commit",
        )
        registration_commit = _full_commit(
            repo,
            registration_boundary.source_commit,
            "registration outcome source commit",
        )
        if activation_commit != registration_commit and not _is_ancestor(
            repo,
            registration_commit,
            activation_commit,
        ):
            raise GitEvidenceError(
                "registration outcome source is not an ancestor of activation data"
            )

        registration_raw, registration_draws = _verified_boundary_blob(
            repo,
            registration_boundary,
        )
        activation_raw, activation_draws = _verified_boundary_blob(repo, boundary)
        if (
            boundary.draw_count < registration_boundary.draw_count
            or boundary.history_through < registration_boundary.history_through
        ):
            raise GitEvidenceError(
                "activation outcome boundary precedes registration-known data"
            )
        if not activation_raw.startswith(registration_raw) or (
            activation_draws[: len(registration_draws)] != registration_draws
        ):
            raise GitEvidenceError(
                "activation data does not preserve the registration-known data prefix"
            )

        return cls._create(
            repository=repo,
            path=OUTCOME_DATA_PATH,
            boundary=boundary,
            registration_boundary=registration_boundary,
            raw_sha256=sha256(activation_raw).hexdigest(),
            draws_fingerprint=draws_fingerprint(activation_draws),
            registration_raw_sha256=sha256(registration_raw).hexdigest(),
            draws=activation_draws,
        )


_COHORT_ASSESSMENT_FACTORY_TOKEN = object()


@dataclass(frozen=True, init=False)
class CohortAssessment:
    status: str
    reasons: tuple[str, ...]
    snapshot_digest: str
    target_draw_date: date | None = None
    evaluation_digest: str | None = None
    snapshot_path: str | None = None
    evaluation_path: str | None = None
    snapshot_git_evidence: GitFileEvidence | None = field(default=None, repr=False)
    evaluation_git_evidence: GitFileEvidence | None = field(default=None, repr=False)
    _factory_token: object = field(repr=False, compare=False)

    def __init__(self) -> None:
        raise TypeError("CohortAssessment is created only by prospective assessment")

    @classmethod
    def _create(
        cls,
        *,
        status: str,
        reasons: tuple[str, ...],
        snapshot_digest: str,
        target_draw_date: date | None = None,
        evaluation_digest: str | None = None,
        snapshot_path: str | None = None,
        evaluation_path: str | None = None,
        snapshot_git_evidence: GitFileEvidence | None = None,
        evaluation_git_evidence: GitFileEvidence | None = None,
    ) -> CohortAssessment:
        instance = object.__new__(cls)
        values = {
            "status": status,
            "reasons": reasons,
            "snapshot_digest": snapshot_digest,
            "target_draw_date": target_draw_date,
            "evaluation_digest": evaluation_digest,
            "snapshot_path": snapshot_path,
            "evaluation_path": evaluation_path,
            "snapshot_git_evidence": snapshot_git_evidence,
            "evaluation_git_evidence": evaluation_git_evidence,
            "_factory_token": _COHORT_ASSESSMENT_FACTORY_TOKEN,
        }
        for name, value in values.items():
            object.__setattr__(instance, name, value)
        return instance

    @property
    def eligible(self) -> bool:
        return self.status == "eligible_evaluated"

    @property
    def snapshot_eligible(self) -> bool:
        return self.status in {"eligible_pending", "eligible_evaluated"}

    @property
    def evaluated_eligible(self) -> bool:
        return self.status == "eligible_evaluated"


_FORMAL_LOOK_FACTORY_TOKEN = object()


@dataclass(frozen=True, init=False)
class FormalLookRecord:
    checkpoint_digest: str
    eligible_evaluated_count: int
    experiment_id: str
    model_version: str
    report_path: str
    report_sha256: str
    decision: str
    record_commit: str
    git_evidence: GitFileEvidence = field(repr=False)
    _factory_token: object = field(repr=False, compare=False)

    def __init__(self) -> None:
        raise TypeError("FormalLookRecord must be derived from immutable Git evidence")

    @classmethod
    def from_repository(
        cls,
        registration: ExperimentRegistration,
        ready_aggregate: CohortAggregate,
        repository: str | Path,
        file_path: str | Path,
    ) -> FormalLookRecord:
        cohort = registration.prospective
        if (
            ready_aggregate._factory_token is not _COHORT_AGGREGATE_FACTORY_TOKEN
            or ready_aggregate.status != "ready"
            or len(ready_aggregate.checkpoint) != cohort.minimum_eligible_draws
            or ready_aggregate.checkpoint_digest is None
        ):
            raise GitEvidenceError(
                "formal look can be recorded only from the exact ready checkpoint"
            )
        if cohort.freeze_commit is None or cohort.activation_commit is None:
            raise GitEvidenceError("formal look requires an activated cohort")
        evidence = GitFileEvidence.from_repository(
            repository,
            file_path,
            freeze_commit=cohort.freeze_commit,
            activation_commit=cohort.activation_commit,
        )
        expected_path = (
            f"reports/prospective/{registration.experiment_id}__"
            f"{registration.model_version}__formal_look.json"
        )
        if evidence.path != expected_path:
            raise GitEvidenceError("formal-look record path does not match the experiment")
        try:
            payload = json.loads(
                (evidence.repository / evidence.path).read_text(encoding="utf-8")
            )
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise GitEvidenceError("formal-look record must be valid JSON") from exc
        if not isinstance(payload, Mapping):
            raise GitEvidenceError("formal-look record root must be a mapping")
        if payload.get("experiment_id") != registration.experiment_id:
            raise GitEvidenceError("formal-look experiment identity mismatch")
        if payload.get("model_name") != registration.model_name:
            raise GitEvidenceError("formal-look model identity mismatch")
        if payload.get("model_version") != registration.model_version:
            raise GitEvidenceError("formal-look model version mismatch")
        checkpoint_digest = payload.get("checkpoint_digest")
        if not isinstance(checkpoint_digest, str) or len(checkpoint_digest) != 64 or any(
            character not in "0123456789abcdef"
            for character in checkpoint_digest
        ):
            raise GitEvidenceError("formal-look checkpoint digest must be SHA-256")
        eligible_count = payload.get("eligible_evaluated_count")
        if eligible_count != cohort.minimum_eligible_draws:
            raise GitEvidenceError(
                "formal look must record exactly the frozen minimum eligible count"
            )
        if checkpoint_digest != ready_aggregate.checkpoint_digest:
            raise GitEvidenceError("formal-look checkpoint does not match ready aggregate")
        decision = payload.get("decision")
        if decision not in {"reject", "archive", "promote"}:
            raise GitEvidenceError("formal-look decision is invalid")
        for observation in ready_aggregate.checkpoint:
            evaluation_git = observation.evaluation_git_evidence
            if evaluation_git is None:
                raise GitEvidenceError(
                    "formal look requires Git evidence for every checkpoint evaluation"
                )
            if (
                evaluation_git.repository != evidence.repository
                or evaluation_git.first_commit_sha == evidence.first_commit_sha
                or not _is_ancestor(
                    evidence.repository,
                    evaluation_git.first_commit_sha,
                    evidence.first_commit_sha,
                )
            ):
                raise GitEvidenceError(
                    "formal-look report must strictly follow every checkpoint evaluation"
                )

        instance = object.__new__(cls)
        values = {
            "checkpoint_digest": checkpoint_digest,
            "eligible_evaluated_count": eligible_count,
            "experiment_id": registration.experiment_id,
            "model_version": registration.model_version,
            "report_path": evidence.path,
            "report_sha256": evidence.raw_sha256,
            "decision": decision,
            "record_commit": evidence.first_commit_sha,
            "git_evidence": evidence,
            "_factory_token": _FORMAL_LOOK_FACTORY_TOKEN,
        }
        for name, value in values.items():
            object.__setattr__(instance, name, value)
        return instance


_COHORT_AGGREGATE_FACTORY_TOKEN = object()


@dataclass(frozen=True, init=False)
class CohortAggregate:
    status: str
    eligible_evaluated: tuple[CohortAssessment, ...]
    pending: tuple[CohortAssessment, ...]
    excluded: tuple[CohortAssessment, ...]
    checkpoint: tuple[CohortAssessment, ...]
    first_half: tuple[CohortAssessment, ...]
    second_half: tuple[CohortAssessment, ...]
    extra_evaluated: tuple[CohortAssessment, ...]
    checkpoint_digest: str | None
    formal_look_count: int
    _factory_token: object = field(repr=False, compare=False)

    def __init__(self) -> None:
        raise TypeError("CohortAggregate is created only by verified aggregation")

    @classmethod
    def _create(cls, **values: Any) -> CohortAggregate:
        instance = object.__new__(cls)
        values["_factory_token"] = _COHORT_AGGREGATE_FACTORY_TOKEN
        for name, value in values.items():
            object.__setattr__(instance, name, value)
        return instance


REGISTERED_EVALUATION_METRICS = (
    "final_6_hits",
    "top_6_hits",
    "top_12_hits",
    "top_18_hits",
    "brier_score",
    "log_loss",
    "mean_actual_rank",
    "matched_final",
)


def _prediction_from_snapshot(snapshot: Mapping[str, Any]) -> Prediction:
    generated_at = datetime.fromisoformat(str(snapshot["generated_at"]))
    probabilities_raw = _as_mapping(snapshot["probabilities"], "probabilities")
    if set(probabilities_raw) != {str(number) for number in range(1, 50)}:
        raise ValueError("snapshot probability keys must be canonical strings 1..49")
    probabilities = {int(key): float(value) for key, value in probabilities_raw.items()}
    if set(probabilities) != set(range(1, 50)):
        raise ValueError("snapshot probabilities must cover exactly 1..49")
    return Prediction(
        target_draw_date=_as_date(snapshot["target_draw_date"], "target_draw_date"),
        generated_at=generated_at,
        model_name=str(snapshot["model_name"]),
        model_version=str(snapshot["model_version"]),
        probabilities=probabilities,
        top6=[int(value) for value in snapshot["top6"]],
        top12=[int(value) for value in snapshot["top12"]],
        top18=[int(value) for value in snapshot["top18"]],
        final_combination=[int(value) for value in snapshot["final_combination"]],
        metadata=dict(_as_mapping(snapshot["metadata"], "metadata")),
    )


def _snapshot_contract_reasons(snapshot: Mapping[str, Any]) -> tuple[str, ...]:
    reasons: list[str] = []
    probabilities: dict[int, float] = {}
    try:
        raw_probabilities = _as_mapping(snapshot.get("probabilities"), "probabilities")
        if set(raw_probabilities) != {str(number) for number in range(1, 50)}:
            reasons.append("probability_keys_must_be_canonical_1_to_49")
        probabilities = {
            int(key): float(value) for key, value in raw_probabilities.items()
        }
    except (TypeError, ValueError):
        reasons.append("invalid_probabilities")
    else:
        if set(probabilities) != set(range(1, 50)):
            reasons.append("probabilities_must_cover_1_to_49")
        if any(
            not math.isfinite(value) or not (0.0 < value < 1.0)
            for value in probabilities.values()
        ):
            reasons.append("probabilities_must_be_finite_open_interval")
        if not math.isclose(
            sum(probabilities.values()),
            6.0,
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            reasons.append("probabilities_must_sum_to_six")

    ranked = (
        sorted(probabilities, key=lambda number: (-probabilities[number], number))
        if set(probabilities) == set(range(1, 50))
        and all(math.isfinite(value) for value in probabilities.values())
        else []
    )
    top_sets: dict[int, list[int]] = {}
    for size, field_name in ((6, "top6"), (12, "top12"), (18, "top18")):
        raw_values = snapshot.get(field_name)
        valid = (
            isinstance(raw_values, list)
            and len(raw_values) == size
            and all(type(value) is int and 1 <= value <= 49 for value in raw_values)
            and len(set(raw_values)) == size
        )
        if not valid:
            reasons.append(f"invalid_{field_name}")
            continue
        values = list(raw_values)
        top_sets[size] = values
        if ranked and values != ranked[:size]:
            reasons.append(f"{field_name}_does_not_match_probability_rank")
    if 6 in top_sets and 12 in top_sets and not set(top_sets[6]).issubset(
        top_sets[12]
    ):
        reasons.append("top6_not_nested_in_top12")
    if 12 in top_sets and 18 in top_sets and not set(top_sets[12]).issubset(
        top_sets[18]
    ):
        reasons.append("top12_not_nested_in_top18")

    final = snapshot.get("final_combination")
    if not (
        isinstance(final, list)
        and len(final) == 6
        and all(type(value) is int and 1 <= value <= 49 for value in final)
        and len(set(final)) == 6
    ):
        reasons.append("invalid_final_combination")
    return tuple(reasons)


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


def assess_prospective_snapshot(
    registration: ExperimentRegistration,
    snapshot: Mapping[str, Any],
    *,
    snapshot_evidence: GitFileEvidence | None,
    activation_boundary_evidence: VerifiedOutcomeBoundary | None = None,
    snapshot_source_evidence: VerifiedOutcomeBoundary | None = None,
    evaluation: Mapping[str, Any] | None = None,
    evaluation_evidence: GitFileEvidence | None = None,
    evaluation_source_evidence: VerifiedOutcomeBoundary | None = None,
) -> CohortAssessment:
    reasons: list[str] = []
    digest = snapshot_digest(snapshot)
    cohort = registration.prospective

    if cohort.status != "active":
        reasons.append("cohort_not_active")
    else:
        registration_boundary = OutcomeBoundary(
            source_commit=registration.outcomes_known_source_commit,
            sha256=registration.outcomes_known_sha256,
            draw_count=registration.outcomes_known_draw_count,
            history_through=registration.outcomes_known_through,
        )
        if activation_boundary_evidence is None:
            reasons.append("missing_activation_boundary_evidence")
        else:
            if (
                activation_boundary_evidence.boundary
                != cohort.outcomes_known_at_activation
            ):
                reasons.append("activation_boundary_evidence_mismatch")
            if (
                activation_boundary_evidence.registration_boundary
                != registration_boundary
            ):
                reasons.append("activation_registration_boundary_mismatch")
            if cohort.activation_commit is not None and (
                activation_boundary_evidence.boundary.source_commit
                != cohort.activation_commit
                and not _is_ancestor(
                    activation_boundary_evidence.repository,
                    activation_boundary_evidence.boundary.source_commit,
                    cohort.activation_commit,
                )
            ):
                reasons.append("activation_data_not_available_at_activation")
    if snapshot.get("model_name") != registration.model_name:
        reasons.append("wrong_model_name")
    if snapshot.get("model_version") != registration.model_version:
        reasons.append("wrong_model_version")
    metadata = snapshot.get("metadata")
    if not isinstance(metadata, Mapping) or metadata.get("role") != cohort.role:
        reasons.append("wrong_model_role")
    reasons.extend(_snapshot_contract_reasons(snapshot))

    target_date: date | None = None
    try:
        target_date = _as_date(snapshot.get("target_draw_date"), "target_draw_date")
    except ValueError:
        reasons.append("invalid_target_date")

    if target_date is not None:
        if cohort.cohort_start is not None and target_date < cohort.cohort_start:
            reasons.append("before_cohort_start")
        history_through = metadata.get("history_through") if isinstance(metadata, Mapping) else None
        try:
            if _as_date(history_through, "history_through") >= target_date:
                reasons.append("history_not_strictly_prior")
        except ValueError:
            reasons.append("invalid_history_through")

    expected_snapshot_path = None
    if target_date is not None:
        expected_snapshot_path = (
            f"predictions/{target_date.isoformat()}__{registration.model_name}__"
            f"{registration.model_version}.json"
        )
    if snapshot_evidence is None:
        reasons.append("missing_snapshot_git_evidence")
    else:
        if snapshot_evidence.canonical_digest != digest:
            reasons.append("snapshot_digest_mismatch")
        if (
            expected_snapshot_path is not None
            and snapshot_evidence.path != expected_snapshot_path
        ):
            reasons.append("snapshot_path_mismatch")
        if snapshot_evidence.freeze_commit != cohort.freeze_commit:
            reasons.append("snapshot_freeze_commit_mismatch")
        if snapshot_evidence.activation_commit != cohort.activation_commit:
            reasons.append("snapshot_activation_commit_mismatch")
        if target_date is not None:
            deadline = datetime.combine(target_date, time.min, tzinfo=TORONTO)
            if snapshot_evidence.first_commit_at.astimezone(TORONTO) >= deadline:
                reasons.append("late_snapshot_commit")

    if cohort.status == "active":
        if snapshot_source_evidence is None:
            reasons.append("missing_snapshot_source_evidence")
        else:
            if activation_boundary_evidence is not None and (
                snapshot_source_evidence.registration_boundary
                != activation_boundary_evidence.boundary
            ):
                reasons.append("snapshot_source_base_boundary_mismatch")
            if snapshot_evidence is None or (
                snapshot_source_evidence.boundary.source_commit
                != snapshot_evidence.first_commit_sha
            ):
                reasons.append("snapshot_source_commit_mismatch")
            if snapshot_evidence is not None and (
                snapshot_source_evidence.repository != snapshot_evidence.repository
            ):
                reasons.append("snapshot_source_repository_mismatch")
            if activation_boundary_evidence is not None and (
                snapshot_source_evidence.repository
                != activation_boundary_evidence.repository
            ):
                reasons.append("snapshot_activation_source_repository_mismatch")
            if isinstance(metadata, Mapping):
                if (
                    metadata.get("history_draws")
                    != snapshot_source_evidence.boundary.draw_count
                ):
                    reasons.append("snapshot_source_draw_count_mismatch")
                try:
                    snapshot_history_through = _as_date(
                        metadata.get("history_through"),
                        "history_through",
                    )
                except ValueError:
                    pass
                else:
                    if (
                        snapshot_history_through
                        != snapshot_source_evidence.boundary.history_through
                    ):
                        reasons.append("snapshot_source_history_through_mismatch")

    generated_at: datetime | None = None
    try:
        generated_raw = snapshot.get("generated_at")
        generated_at = datetime.fromisoformat(generated_raw) if isinstance(generated_raw, str) else None
        if generated_at is None or generated_at.tzinfo is None:
            raise ValueError
    except ValueError:
        reasons.append("invalid_generated_at")
    if generated_at is not None and generated_at.tzinfo is not None:
        if snapshot_evidence is not None:
            if generated_at > snapshot_evidence.first_commit_at:
                reasons.append("generated_after_first_commit")
        if target_date is not None:
            deadline = datetime.combine(target_date, time.min, tzinfo=TORONTO)
            if generated_at.astimezone(TORONTO) >= deadline:
                reasons.append("late_snapshot_generation")

    evaluation_digest = None
    if evaluation is not None:
        evaluation_digest = snapshot_digest(evaluation)
        for field in ("target_draw_date", "model_name", "model_version"):
            if evaluation.get(field) != snapshot.get(field):
                reasons.append(f"evaluation_{field}_mismatch")
        if evaluation_evidence is None:
            reasons.append("missing_evaluation_git_evidence")
        else:
            if evaluation_evidence.canonical_digest != evaluation_digest:
                reasons.append("evaluation_digest_mismatch")
            expected_evaluation_path = (
                expected_snapshot_path.replace("predictions/", "evaluations/", 1)
                if expected_snapshot_path is not None
                else None
            )
            if (
                expected_evaluation_path is not None
                and evaluation_evidence.path != expected_evaluation_path
            ):
                reasons.append("evaluation_path_mismatch")
            if snapshot_evidence is not None and (
                evaluation_evidence.repository != snapshot_evidence.repository
            ):
                reasons.append("evaluation_repository_mismatch")
            if evaluation_evidence.freeze_commit != cohort.freeze_commit:
                reasons.append("evaluation_freeze_commit_mismatch")
            if evaluation_evidence.activation_commit != cohort.activation_commit:
                reasons.append("evaluation_activation_commit_mismatch")
            if (
                target_date is not None
                and evaluation_evidence.first_commit_at.astimezone(TORONTO).date()
                < target_date
            ):
                reasons.append("evaluation_committed_before_draw")

        if snapshot_evidence is None or (
            evaluation.get("prediction_snapshot_digest")
            != snapshot_evidence.canonical_digest
        ):
            reasons.append("evaluation_snapshot_digest_mismatch")
        if snapshot_evidence is None or (
            evaluation.get("prediction_snapshot_path") != snapshot_evidence.path
        ):
            reasons.append("evaluation_snapshot_path_mismatch")

        verified_draw = None
        if evaluation_source_evidence is None:
            reasons.append("missing_evaluation_source_evidence")
        else:
            if snapshot_source_evidence is not None and (
                evaluation_source_evidence.registration_boundary
                != snapshot_source_evidence.boundary
            ):
                reasons.append("evaluation_source_base_boundary_mismatch")
            if evaluation_evidence is None or (
                evaluation_source_evidence.boundary.source_commit
                != evaluation_evidence.first_commit_sha
            ):
                reasons.append("evaluation_source_commit_mismatch")
            if evaluation_evidence is not None and (
                evaluation_source_evidence.repository
                != evaluation_evidence.repository
            ):
                reasons.append("evaluation_source_repository_mismatch")
            if target_date is not None:
                verified_matches = tuple(
                    draw
                    for draw in evaluation_source_evidence.draws
                    if draw.draw_date == target_date
                )
                if len(verified_matches) != 1:
                    reasons.append("verified_source_missing_unique_target_draw")
                else:
                    verified_draw = verified_matches[0]

        if snapshot_evidence is not None and evaluation_evidence is not None:
            if (
                snapshot_evidence.repository != evaluation_evidence.repository
                or snapshot_evidence.first_commit_sha
                == evaluation_evidence.first_commit_sha
                or not _is_ancestor(
                    snapshot_evidence.repository,
                    snapshot_evidence.first_commit_sha,
                    evaluation_evidence.first_commit_sha,
                )
            ):
                reasons.append("snapshot_not_strict_ancestor_of_evaluation")

        if verified_draw is not None:
            if target_date is None or verified_draw.draw_date != target_date:
                reasons.append("verified_draw_target_mismatch")
            if evaluation.get("actual") != list(verified_draw.numbers):
                reasons.append("evaluation_actual_mismatch")
            if evaluation.get("bonus") != verified_draw.bonus:
                reasons.append("evaluation_bonus_mismatch")
            if evaluation.get("actual_draw_digest") != draw_digest(verified_draw):
                reasons.append("actual_draw_digest_mismatch")

            try:
                prediction = _prediction_from_snapshot(snapshot)
                from .evaluation import evaluate_prediction

                expected_evaluation = evaluate_prediction(prediction, verified_draw)
            except (KeyError, TypeError, ValueError) as exc:
                reasons.append(f"evaluation_recompute_failure:{type(exc).__name__}")
            else:
                for metric in REGISTERED_EVALUATION_METRICS:
                    if metric not in evaluation:
                        reasons.append(f"missing_registered_metric:{metric}")
                    elif not _metric_matches(
                        evaluation.get(metric), expected_evaluation[metric]
                    ):
                        reasons.append(f"registered_metric_mismatch:{metric}")

        verified_count = evaluation.get("verified_data_draw_count")
        if type(verified_count) is not int or verified_count < 1:
            reasons.append("invalid_verified_data_draw_count")
        elif evaluation_source_evidence is not None and (
            verified_count != evaluation_source_evidence.boundary.draw_count
        ):
            reasons.append("verified_data_draw_count_mismatch")
        elif isinstance(metadata, Mapping):
            history_draws = metadata.get("history_draws")
            if type(history_draws) is int and verified_count <= history_draws:
                reasons.append("verified_data_count_not_after_snapshot_history")
        try:
            verified_history_through = _as_date(
                evaluation.get("verified_data_history_through"),
                "verified_data_history_through",
            )
            if evaluation_source_evidence is not None and (
                verified_history_through
                != evaluation_source_evidence.boundary.history_through
            ):
                reasons.append("verified_data_history_through_mismatch")
            elif verified_draw is not None and (
                verified_history_through < verified_draw.draw_date
            ):
                reasons.append("verified_data_history_missing_actual")
        except ValueError:
            reasons.append("invalid_verified_data_history_through")
    else:
        if evaluation_evidence is not None:
            reasons.append("evaluation_evidence_without_evaluation")
        if evaluation_source_evidence is not None:
            reasons.append("evaluation_source_evidence_without_evaluation")

    if reasons:
        return CohortAssessment._create(
            status="excluded",
            reasons=tuple(dict.fromkeys(reasons)),
            snapshot_digest=digest,
            target_draw_date=target_date,
            evaluation_digest=evaluation_digest,
            snapshot_path=(snapshot_evidence.path if snapshot_evidence else None),
            evaluation_path=(evaluation_evidence.path if evaluation_evidence else None),
            snapshot_git_evidence=snapshot_evidence,
            evaluation_git_evidence=evaluation_evidence,
        )
    status = "eligible_evaluated" if evaluation is not None else "eligible_pending"
    return CohortAssessment._create(
        status=status,
        reasons=(),
        snapshot_digest=digest,
        target_draw_date=target_date,
        evaluation_digest=evaluation_digest,
        snapshot_path=(snapshot_evidence.path if snapshot_evidence else None),
        evaluation_path=(evaluation_evidence.path if evaluation_evidence else None),
        snapshot_git_evidence=snapshot_evidence,
        evaluation_git_evidence=evaluation_evidence,
    )


def _assessment_sort_key(assessment: CohortAssessment) -> tuple[date, str, str]:
    return (
        assessment.target_draw_date or date.max,
        assessment.status,
        assessment.snapshot_digest,
    )


def _checkpoint_digest(
    registration: ExperimentRegistration,
    observations: Sequence[CohortAssessment],
) -> str:
    return snapshot_digest(
        {
            "experiment_id": registration.experiment_id,
            "model_name": registration.model_name,
            "model_version": registration.model_version,
            "minimum_eligible_draws": registration.prospective.minimum_eligible_draws,
            "observations": [
                {
                    "target_draw_date": observation.target_draw_date.isoformat(),
                    "snapshot_digest": observation.snapshot_digest,
                    "evaluation_digest": observation.evaluation_digest,
                    "snapshot_path": observation.snapshot_path,
                    "evaluation_path": observation.evaluation_path,
                }
                for observation in observations
                if observation.target_draw_date is not None
            ],
        }
    )


def aggregate_prospective_cohort(
    registration: ExperimentRegistration,
    assessments: Sequence[CohortAssessment],
    *,
    formal_looks: Sequence[FormalLookRecord] = (),
) -> CohortAggregate:
    """Build the one fixed prospective checkpoint without skipping pending targets."""
    if registration.prospective.status not in {"active", "closed"}:
        raise ValueError("prospective cohort must be active or closed before aggregation")
    if len(formal_looks) > 1:
        raise ValueError("at most one formal look is permitted")
    if formal_looks and (
        formal_looks[0]._factory_token is not _FORMAL_LOOK_FACTORY_TOKEN
    ):
        raise ValueError("formal look must come from immutable Git evidence")
    if any(
        assessment._factory_token is not _COHORT_ASSESSMENT_FACTORY_TOKEN
        for assessment in assessments
    ):
        raise ValueError("cohort aggregation requires verified assessments")

    targets = [
        assessment.target_draw_date
        for assessment in assessments
        if assessment.target_draw_date is not None
    ]
    if len(targets) != len(set(targets)):
        raise ValueError("duplicate prospective target is prohibited")

    known_statuses = {"eligible_evaluated", "eligible_pending", "excluded"}
    unknown = [item.status for item in assessments if item.status not in known_statuses]
    if unknown:
        raise ValueError(f"unsupported cohort assessment status: {unknown[0]}")

    cohort_start = registration.prospective.cohort_start
    for assessment in assessments:
        if assessment.status.startswith("eligible_"):
            if assessment.target_draw_date is None:
                raise ValueError("eligible observation requires a target date")
            if cohort_start is not None and assessment.target_draw_date < cohort_start:
                raise ValueError("prospective backfill before cohort start is prohibited")
            if len(assessment.snapshot_digest) != 64:
                raise ValueError("eligible observation requires a snapshot digest")
            if assessment.evaluated_eligible and (
                assessment.evaluation_digest is None
                or len(assessment.evaluation_digest) != 64
            ):
                raise ValueError("evaluated observation requires an evaluation digest")
            if assessment.reasons:
                raise ValueError("eligible observation cannot retain exclusion reasons")
            expected_snapshot_path = (
                f"predictions/{assessment.target_draw_date.isoformat()}__"
                f"{registration.model_name}__{registration.model_version}.json"
            )
            snapshot_git = assessment.snapshot_git_evidence
            if (
                snapshot_git is None
                or snapshot_git._factory_token is not _GIT_EVIDENCE_FACTORY_TOKEN
                or snapshot_git.canonical_digest != assessment.snapshot_digest
                or snapshot_git.path != assessment.snapshot_path
                or snapshot_git.path != expected_snapshot_path
                or snapshot_git.freeze_commit
                != registration.prospective.freeze_commit
                or snapshot_git.activation_commit
                != registration.prospective.activation_commit
            ):
                raise ValueError("eligible observation has invalid snapshot Git evidence")
            if assessment.evaluated_eligible:
                expected_evaluation_path = expected_snapshot_path.replace(
                    "predictions/",
                    "evaluations/",
                    1,
                )
                evaluation_git = assessment.evaluation_git_evidence
                if (
                    evaluation_git is None
                    or evaluation_git._factory_token is not _GIT_EVIDENCE_FACTORY_TOKEN
                    or evaluation_git.canonical_digest
                    != assessment.evaluation_digest
                    or evaluation_git.path != assessment.evaluation_path
                    or evaluation_git.path != expected_evaluation_path
                    or evaluation_git.repository != snapshot_git.repository
                    or evaluation_git.freeze_commit
                    != registration.prospective.freeze_commit
                    or evaluation_git.activation_commit
                    != registration.prospective.activation_commit
                ):
                    raise ValueError(
                        "evaluated observation has invalid evaluation Git evidence"
                    )
            elif (
                assessment.evaluation_digest is not None
                or assessment.evaluation_path is not None
                or assessment.evaluation_git_evidence is not None
            ):
                raise ValueError("pending observation cannot contain evaluation evidence")

    evaluated = tuple(
        sorted(
            (item for item in assessments if item.evaluated_eligible),
            key=_assessment_sort_key,
        )
    )
    pending = tuple(
        sorted(
            (item for item in assessments if item.status == "eligible_pending"),
            key=_assessment_sort_key,
        )
    )
    excluded = tuple(
        sorted(
            (item for item in assessments if item.status == "excluded"),
            key=_assessment_sort_key,
        )
    )
    minimum = registration.prospective.minimum_eligible_draws

    checkpoint: tuple[CohortAssessment, ...] = ()
    first_half: tuple[CohortAssessment, ...] = ()
    second_half: tuple[CohortAssessment, ...] = ()
    extra: tuple[CohortAssessment, ...] = ()
    digest = None
    if len(evaluated) >= minimum:
        candidate = evaluated[:minimum]
        cutoff = candidate[-1].target_draw_date
        earlier_pending = (
            cutoff is not None
            and any(
                item.target_draw_date is not None
                and item.target_draw_date <= cutoff
                for item in pending
            )
        )
        if earlier_pending:
            if formal_looks:
                raise ValueError("formal look cannot skip an earlier pending target")
            status = "waiting_for_earlier_pending"
        else:
            checkpoint = candidate
            half = minimum // 2
            first_half = checkpoint[:half]
            second_half = checkpoint[half:]
            extra = evaluated[minimum:]
            digest = _checkpoint_digest(registration, checkpoint)
            if formal_looks:
                formal_look = formal_looks[0]
                if (
                    formal_look.experiment_id != registration.experiment_id
                    or formal_look.model_version != registration.model_version
                    or formal_look.eligible_evaluated_count != minimum
                    or formal_look.checkpoint_digest != digest
                ):
                    raise ValueError(
                        "formal-look digest does not match the fixed earliest checkpoint"
                    )
                formal_evidence = formal_look.git_evidence
                for observation in checkpoint:
                    evaluation_git = observation.evaluation_git_evidence
                    if evaluation_git is None:
                        raise ValueError(
                            "formal look requires Git evidence for every checkpoint evaluation"
                        )
                    if (
                        evaluation_git.repository != formal_evidence.repository
                        or evaluation_git.first_commit_sha
                        == formal_evidence.first_commit_sha
                        or not _is_ancestor(
                            formal_evidence.repository,
                            evaluation_git.first_commit_sha,
                            formal_evidence.first_commit_sha,
                        )
                    ):
                        raise ValueError(
                            "formal-look commit must strictly follow all checkpoint evaluations"
                        )
                for observation in extra:
                    evaluation_git = observation.evaluation_git_evidence
                    if evaluation_git is None:
                        raise ValueError(
                            "post-look evaluation requires immutable Git evidence"
                        )
                    if (
                        evaluation_git.repository != formal_evidence.repository
                        or formal_evidence.first_commit_sha
                        == evaluation_git.first_commit_sha
                        or not _is_ancestor(
                            formal_evidence.repository,
                            formal_evidence.first_commit_sha,
                            evaluation_git.first_commit_sha,
                        )
                    ):
                        raise ValueError(
                            "an overdue cohort cannot retroactively record a formal look"
                        )
                status = "formal_look_recorded"
            elif len(evaluated) == minimum:
                status = "ready"
            else:
                status = "overdue"
    else:
        if formal_looks:
            raise ValueError("formal look cannot occur before the minimum checkpoint")
        status = "collecting"

    return CohortAggregate._create(
        status=status,
        eligible_evaluated=evaluated,
        pending=pending,
        excluded=excluded,
        checkpoint=checkpoint,
        first_half=first_half,
        second_half=second_half,
        extra_evaluated=extra,
        checkpoint_digest=digest,
        formal_look_count=len(formal_looks),
    )
