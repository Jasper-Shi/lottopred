from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, time
from hashlib import sha256
import json
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import yaml

from .domain import Draw


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
class ProspectiveCohortSpec:
    status: str
    role: str
    minimum_eligible_draws: int
    commit_deadline: str
    freeze_commit: str | None
    cohort_start: date | None

    def __post_init__(self) -> None:
        if self.status not in {"not_activated", "active", "closed"}:
            raise ValueError(f"unsupported cohort status: {self.status}")
        if self.role != "shadow":
            raise ValueError("new research cohorts must begin with role=shadow")
        if self.minimum_eligible_draws < 104:
            raise ValueError("prospective cohorts require at least 104 eligible draws")
        if self.commit_deadline != "before_target_local_date":
            raise ValueError("cohort commit deadline must be before_target_local_date")
        if self.status == "not_activated" and (self.freeze_commit or self.cohort_start):
            raise ValueError("an unactivated cohort cannot have a freeze commit or start date")
        if self.status in {"active", "closed"} and not (self.freeze_commit and self.cohort_start):
            raise ValueError("an activated cohort requires a freeze commit and start date")


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
    partitions: Mapping[str, DateRange]
    negative_controls: tuple[NegativeControlSpec, ...]
    parameters: Mapping[str, Any]
    prospective: ProspectiveCohortSpec
    result: ExperimentResult | None

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
        if self.primary_metric != "top12_hits_lift_vs_theory":
            raise ValueError("V5 primary metric must remain top12_hits_lift_vs_theory")
        if not self.negative_controls:
            raise ValueError("at least one negative control is required")
        if set(self.partitions) != set(EXPECTED_HISTORICAL_PARTITIONS):
            raise ValueError("historical partitions must use the three registered evidence lanes")
        for name, expected in EXPECTED_HISTORICAL_PARTITIONS.items():
            actual = self.partitions[name]
            if (actual.start, actual.end) != expected:
                raise ValueError(f"{name} must remain fixed at {expected[0]} through {expected[1]}")
        if self.status == "registered" and self.result is not None:
            raise ValueError("a registered experiment cannot already have a result")
        if self.status == "closed_rejected" and (
            self.result is None or self.result.decision != "reject"
        ):
            raise ValueError("a closed_rejected experiment requires a reject result")
        if self.result is not None and (
            self.result.shadow_activation != self.prospective.status
        ):
            raise ValueError("result and prospective cohort statuses must agree")


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
    prospective_raw = _as_mapping(raw.get("prospective"), "prospective")
    cohort_start_raw = prospective_raw.get("cohort_start")
    prospective = ProspectiveCohortSpec(
        status=str(prospective_raw.get("status", "")),
        role=str(prospective_raw.get("role", "")),
        minimum_eligible_draws=int(prospective_raw.get("minimum_eligible_draws", 0)),
        commit_deadline=str(prospective_raw.get("commit_deadline", "")),
        freeze_commit=prospective_raw.get("freeze_commit"),
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
    if schema_version != 1:
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


@dataclass(frozen=True)
class CohortAssessment:
    status: str
    reasons: tuple[str, ...]
    snapshot_digest: str

    @property
    def eligible(self) -> bool:
        return self.status in {"eligible_pending", "eligible_evaluated"}


def assess_prospective_snapshot(
    registration: ExperimentRegistration,
    snapshot: Mapping[str, Any],
    *,
    first_commit_at: datetime | None,
    first_commit_sha: str | None,
    recorded_digest: str | None,
    evaluation: Mapping[str, Any] | None = None,
    source_integrity_ok: bool = True,
    regenerated: bool = False,
) -> CohortAssessment:
    reasons: list[str] = []
    digest = snapshot_digest(snapshot)
    cohort = registration.prospective

    if cohort.status != "active":
        reasons.append("cohort_not_active")
    if snapshot.get("model_name") != registration.model_name:
        reasons.append("wrong_model_name")
    if snapshot.get("model_version") != registration.model_version:
        reasons.append("wrong_model_version")
    metadata = snapshot.get("metadata")
    if not isinstance(metadata, Mapping) or metadata.get("role") != cohort.role:
        reasons.append("wrong_model_role")

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

    if first_commit_at is None or first_commit_at.tzinfo is None:
        reasons.append("missing_aware_first_commit_time")
    elif target_date is not None:
        deadline = datetime.combine(target_date, time.min, tzinfo=TORONTO)
        if first_commit_at.astimezone(TORONTO) >= deadline:
            reasons.append("late_snapshot_commit")

    if (
        not first_commit_sha
        or not (7 <= len(first_commit_sha) <= 64)
        or any(c not in "0123456789abcdef" for c in first_commit_sha)
    ):
        reasons.append("missing_first_commit_sha")

    generated_at: datetime | None = None
    try:
        generated_raw = snapshot.get("generated_at")
        generated_at = datetime.fromisoformat(generated_raw) if isinstance(generated_raw, str) else None
        if generated_at is None or generated_at.tzinfo is None:
            raise ValueError
    except ValueError:
        reasons.append("invalid_generated_at")
    if generated_at is not None and generated_at.tzinfo is not None:
        if first_commit_at is not None and first_commit_at.tzinfo is not None:
            if generated_at > first_commit_at:
                reasons.append("generated_after_first_commit")
        if target_date is not None:
            deadline = datetime.combine(target_date, time.min, tzinfo=TORONTO)
            if generated_at.astimezone(TORONTO) >= deadline:
                reasons.append("late_snapshot_generation")

    if recorded_digest is None:
        reasons.append("missing_recorded_digest")
    elif recorded_digest != digest:
        reasons.append("snapshot_digest_mismatch")
    if not source_integrity_ok:
        reasons.append("source_integrity_failure")
    if regenerated:
        reasons.append("regenerated_snapshot")

    if evaluation is not None:
        for field in ("target_draw_date", "model_name", "model_version"):
            if evaluation.get(field) != snapshot.get(field):
                reasons.append(f"evaluation_{field}_mismatch")

    if reasons:
        return CohortAssessment("excluded", tuple(reasons), digest)
    status = "eligible_evaluated" if evaluation is not None else "eligible_pending"
    return CohortAssessment(status, (), digest)
