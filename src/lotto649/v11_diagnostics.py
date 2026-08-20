"""One-shot, reveal-gated V11 historical diagnostic infrastructure.

The module is deliberately outside the normal backtest, CLI, factory, and live
paths.  A target outcome crosses the injected reveal seam only after the full
four-model deterministic forecast payload has been appended, flushed, and
``fsync``-ed to an exclusive hash-chain ledger.
"""

from __future__ import annotations

import csv
import json
import math
import os
import shlex
import stat
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from functools import cache
from hashlib import sha256
from pathlib import Path
from typing import Any, Self

import numpy as np

from lotto649.domain import Draw
from lotto649.models.v11_previous_bonus_carryover import (
    anchor_log_gains as _model_anchor_log_gains,
)
from lotto649.models.v11_previous_bonus_carryover import (
    select_pseudo_bonus,
    tilt_probabilities,
)

REGISTRATION_COMMIT = "eb12933ab74f3a9c34a3ece3de90d280197c410c"
EXPERIMENT_ID = "V11_previous_bonus_carryover"
MODEL_VERSION = "v11.0.0"
CANDIDATE_MODEL = "v11_previous_bonus_carryover"
CONTROL_MODEL = "v11_previous_bonus_carryover_pseudo_bonus_control"
V1_MODEL = "ensemble"
RANDOM_MODEL = "random"
MODEL_ORDER = (CANDIDATE_MODEL, CONTROL_MODEL, V1_MODEL, RANDOM_MODEL)
FEATURE_SET_BY_MODEL = {
    CANDIDATE_MODEL: "frozen_v1_marginals_plus_previous_published_bonus_logit_tilt",
    CONTROL_MODEL: "frozen_v1_marginals_plus_deterministic_pseudo_bonus_logit_tilt",
    V1_MODEL: "frozen_v1_ensemble_marginals",
    RANDOM_MODEL: "date_seeded_fair_random_baseline",
}
OPPORTUNITY_MODEL_NAMES = {
    CANDIDATE_MODEL: CANDIDATE_MODEL,
    CONTROL_MODEL: CONTROL_MODEL,
    V1_MODEL: "ensemble_v1.0.0",
    RANDOM_MODEL: "random_v1.0.0",
}
FAIR_PROBABILITY = 6.0 / 49.0
FAIR_EXPECTATIONS = {6: 36.0 / 49.0, 12: 72.0 / 49.0, 18: 108.0 / 49.0}
FAIR_TOTAL_SIX_SETS = 13_983_816
MECHANISM_THRESHOLD = 2.995732273553991
PROPER_SCORE_TOLERANCE = 1.0e-9
ZERO_EVENT_HASH = "0" * 64
DEFAULT_REPORT_STEM = "v11_previous_bonus_carryover_v11.0.0_historical"
REQUIRED_IMPLEMENTATION_PATHS = frozenset(
    {
        "src/lotto649/models/v11_previous_bonus_carryover.py",
        "src/lotto649/v11_diagnostics.py",
        "tools/run_v11_historical.py",
        "tests/test_v11_previous_bonus_carryover.py",
        "tests/test_v11_diagnostics.py",
        "docs/CODEX_HANDOFF.md",
        "docs/MODEL_PROTOCOL.md",
        "docs/RESEARCH_ROADMAP.md",
    }
)
REQUIRED_STATUS_DOCUMENTATION_PATHS = frozenset(
    {
        "docs/CODEX_HANDOFF.md",
        "docs/MODEL_PROTOCOL.md",
        "docs/RESEARCH_ROADMAP.md",
    }
)
STATUS_REPLACEMENT_COUNTS = {
    "docs/CODEX_HANDOFF.md": 2,
    "docs/MODEL_PROTOCOL.md": 1,
    "docs/RESEARCH_ROADMAP.md": 1,
}
REQUIRED_CI_CHECKS = ["source-and-model-smoke", "test"]


@dataclass(frozen=True)
class V11RegisteredIdentity:
    """Immutable preregistration identities trusted by semantic replay."""

    research_config_path: str
    research_config_sha256: str
    data_path: str
    data_source_commit: str
    data_sha256: str
    data_draw_count: int
    data_history_through: str
    runtime_lock_path: str
    runtime_lock_sha256: str
    v1_base_source_commit: str
    v1_base_config_path: str
    v1_base_config_sha256: str
    v1_base_file_sha256: tuple[tuple[str, str], ...]
    analysis_target_start: str
    analysis_target_end: str
    analysis_target_count: int
    analysis_scopes: tuple[tuple[str, str, str, int], ...]
    analysis_bootstrap_replicates: int
    analysis_bootstrap_seed: int
    analysis_reference_json: str
    command_python: str
    command_tool_relative_path: str
    command_output_relative_path: str


REGISTERED_V11_IDENTITY = V11RegisteredIdentity(
    research_config_path="config/research-v11-previous-bonus-carryover.yaml",
    research_config_sha256=(
        "514b0d9e234b8e5eb1d64587224289791ce95fad8f8381b28fda2d0954da7dd7"
    ),
    data_path="data/processed/draws.csv",
    data_source_commit="90177c80cfb070038d79508fb2e73305a297f516",
    data_sha256=("edfb7f8a4a7711a630957d6f86b567e6b254caf7b1d1aaea0edf1d16a34155b3"),
    data_draw_count=4_432,
    data_history_through="2026-08-15",
    runtime_lock_path="requirements-live.lock",
    runtime_lock_sha256=(
        "2fea4cf73cc2578b73c21e6600e31ad843bd903e8a2656b7a2543164ab8d801c"
    ),
    v1_base_source_commit="86549d2650fe98cd48375fa77b5b8521ca271df2",
    v1_base_config_path="config.yaml",
    v1_base_config_sha256=(
        "b67b6cd4e1ace10275da6142fbb8739c1de0e91c37a7f636e42d2c0f4d862ff5"
    ),
    v1_base_file_sha256=(
        (
            "src/lotto649/models/baselines.py",
            "76f9050a13bde44d51584397ecd6acb358f320e1617ef329b70bd6a22d23e28a",
        ),
        (
            "src/lotto649/models/logistic.py",
            "886367c16ed0f0d1109aacb943a3393e63807a31e7710bd0e664e06f6f3c4da2",
        ),
        (
            "src/lotto649/models/ensemble.py",
            "9b2a3fb3156efb3ff248fa6debecfd7a92b718e9517d8da0e3a5fc43da7c0047",
        ),
        (
            "src/lotto649/models/factory.py",
            "d0d3043656144a469b1677491c11cde3143a65b026c2a815485cc89ae5d48fcc",
        ),
        (
            "src/lotto649/features.py",
            "b7bc67b9038b2e3d78230c3087c3ac4e3f17751aeab678574f3601af00671979",
        ),
        (
            "src/lotto649/models/base.py",
            "e2f0c90c376ea6063b906bcca042e8903b351a1ed4b76e9d83e17be3bcf166ec",
        ),
        (
            "src/lotto649/domain.py",
            "fbcb22747ae361767df070c6e50af49fda1aa190b72fd39894afa1c879a50b7a",
        ),
        (
            "src/lotto649/config.py",
            "7563042563ec197de01120bf2d4267d9f089875defdfa95da8323d9f5702e862",
        ),
    ),
    analysis_target_start="2020-01-01",
    analysis_target_end="2025-12-31",
    analysis_target_count=621,
    analysis_scopes=(
        ("aggregate_621", "2020-01-01", "2025-12-31", 621),
        ("first_307", "2020-01-01", "2022-12-31", 307),
        ("second_314", "2023-01-01", "2025-12-31", 314),
    ),
    analysis_bootstrap_replicates=10_000,
    analysis_bootstrap_seed=649,
    analysis_reference_json="{}",
    command_python="python3.12",
    command_tool_relative_path="tools/run_v11_historical.py",
    command_output_relative_path="reports",
)

Notifier = Callable[[str, str], bool]
Clock = Callable[[], datetime]
SourceBlobResolver = Callable[[str, str], bytes]

REQUIRED_6OF6_AUDIT_CHECKS = (
    "claim",
    "chronology",
    "target_exclusion",
    "future_exclusion",
    "preprocessing",
    "feature_selection",
    "model_selection",
    "source_integrity",
    "git_runtime_integrity",
    "forecast_replay",
    "prefix_identity",
)

SCIENTIFIC_GATE_NAMES = (
    "aggregate_candidate_top12_lift_strictly_positive",
    "aggregate_candidate_holm_adjusted_exact_p_at_most_0.05",
    "aggregate_candidate_top12_bootstrap_lower_strictly_positive",
    "candidate_top12_lift_strictly_positive_in_both_halves",
    "paired_candidate_minus_v1_top12_bootstrap_lower_strictly_positive_aggregate_and_halves",
    "paired_candidate_minus_control_top12_bootstrap_lower_strictly_positive_and_pseudo_bonus_and_random_controls_null_aggregate_and_halves",
    "candidate_top6_lift_strictly_positive_aggregate_and_halves",
    "candidate_brier_and_log_loss_no_worse_than_fair_or_v1_by_more_than_1e-9_aggregate_and_halves",
    "all_anchor_mechanism_log_g_d_candidate_control_conditions_pass",
    "no_audit_warning",
)


class V11DiagnosticError(RuntimeError):
    """Raised when the frozen V11 diagnostic cannot proceed safely."""


def _canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    try:
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
            ensure_ascii=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise V11DiagnosticError("V11 payload is not canonical finite JSON") from exc


def _pretty_json_bytes(payload: Mapping[str, Any]) -> bytes:
    try:
        return (
            json.dumps(
                payload,
                indent=2,
                sort_keys=True,
                allow_nan=False,
                ensure_ascii=False,
            ).encode("utf-8")
            + b"\n"
        )
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise V11DiagnosticError("V11 payload is not finite report JSON") from exc


def canonical_sha256(payload: Mapping[str, Any]) -> str:
    """Return the registered canonical JSON digest for a payload."""

    return sha256(_canonical_json_bytes(payload)).hexdigest()


def _registered_relative_path(
    value: str, *, field_name: str, allow_current: bool = False
) -> Path:
    path = Path(value)
    if (
        path.is_absolute()
        or (not path.parts and not (allow_current and value == "."))
        or ".." in path.parts
    ):
        raise V11DiagnosticError(f"V11 registered {field_name} path is invalid")
    return path


def registered_v11_command(
    identity: V11RegisteredIdentity = REGISTERED_V11_IDENTITY,
) -> str:
    """Return the machine-independent registered application command."""

    tool = _registered_relative_path(
        identity.command_tool_relative_path, field_name="tool"
    )
    output = _registered_relative_path(
        identity.command_output_relative_path,
        field_name="output",
        allow_current=True,
    )
    if identity.command_python != "python3.12":
        raise V11DiagnosticError("V11 registered logical interpreter changed")
    argv = [
        identity.command_python,
        tool.as_posix(),
        "--consume-v11-once",
        "--output-dir",
        output.as_posix(),
    ]
    return shlex.join(argv)


def _validate_registered_command(
    command: Any,
    *,
    identity: V11RegisteredIdentity,
) -> None:
    if command != registered_v11_command(identity):
        raise V11DiagnosticError("V11 canonical command changed")


def _validate_invocation_evidence(
    invocation: Any,
    *,
    runtime: Mapping[str, Any],
    identity: V11RegisteredIdentity,
) -> None:
    if not isinstance(invocation, Mapping) or set(invocation) != {
        "logical_command",
        "runtime_executable",
        "tool_relative_path",
        "arguments",
        "output_relative_path",
        "working_directory_relative_to_root",
    }:
        raise V11DiagnosticError("V11 invocation preflight evidence changed")
    expected_arguments = [
        "--consume-v11-once",
        "--output-dir",
        identity.command_output_relative_path,
    ]
    if (
        invocation.get("logical_command") != registered_v11_command(identity)
        or invocation.get("runtime_executable") != runtime.get("executable")
        or invocation.get("tool_relative_path") != identity.command_tool_relative_path
        or invocation.get("arguments") != expected_arguments
        or invocation.get("output_relative_path")
        != identity.command_output_relative_path
        or invocation.get("working_directory_relative_to_root") != "."
    ):
        raise V11DiagnosticError("V11 invocation preflight evidence changed")


def _directory_fsync(directory: Path) -> None:
    descriptor = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


class HashChainLedger:
    """Exclusive append-only canonical JSONL ledger with a SHA-256 chain."""

    def __init__(self, path: Path, handle) -> None:
        self.path = path
        self._handle = handle
        stat = os.fstat(handle.fileno())
        self._owned_identity = (stat.st_dev, stat.st_ino)
        self._sequence = 0
        self._previous_hash = ZERO_EVENT_HASH
        self._closed = False
        self._corrupt = False

    @classmethod
    def create(cls, path: Path) -> Self:
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            handle = path.open("x+", encoding="utf-8", newline="\n")
        except FileExistsError as exc:
            raise V11DiagnosticError("V11 attempt ledger already exists") from exc
        try:
            handle.flush()
            os.fsync(handle.fileno())
            _directory_fsync(path.parent)
            return cls(path, handle)
        except BaseException:
            handle.close()
            raise

    @classmethod
    def open_existing(cls, path: Path) -> Self:
        events = verify_hash_chain_ledger(path)
        handle = path.open("a", encoding="utf-8", newline="\n")
        ledger = cls(path, handle)
        ledger._sequence = len(events)
        ledger._previous_hash = events[-1]["event_sha256"]
        return ledger

    def append(self, event_type: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        if self._closed:
            raise V11DiagnosticError("V11 attempt ledger is closed")
        if self._corrupt:
            raise V11DiagnosticError(
                "V11 attempt ledger has retained corrupt append evidence"
            )
        if not event_type:
            raise V11DiagnosticError("V11 ledger event type is empty")
        without_hash = {
            "event_type": event_type,
            "payload": dict(payload),
            "previous_event_sha256": self._previous_hash,
            "sequence": self._sequence,
        }
        event_hash = sha256(
            _canonical_json_bytes(without_hash) + self._previous_hash.encode("ascii")
        ).hexdigest()
        event = {**without_hash, "event_sha256": event_hash}
        raw = _canonical_json_bytes(event) + b"\n"
        self._handle.seek(0, os.SEEK_END)
        preappend_offset = self._handle.tell()
        try:
            text = raw.decode("utf-8")
            written = self._handle.write(text)
            if written != len(text):
                raise OSError("short V11 ledger write")
            self._handle.flush()
            os.fsync(self._handle.fileno())
        except OSError as exc:
            try:
                self._handle.seek(preappend_offset)
                self._handle.truncate(preappend_offset)
                self._handle.flush()
                os.fsync(self._handle.fileno())
            except (OSError, ValueError) as rollback_exc:
                self._corrupt = True
                raise V11DiagnosticError(
                    "unable to durably append V11 ledger event; rollback_failed; "
                    "corrupt tail evidence retained"
                ) from rollback_exc
            raise V11DiagnosticError(
                "unable to durably append V11 ledger event; append rolled back"
            ) from exc
        self._sequence += 1
        self._previous_hash = event_hash
        return event

    @property
    def head_sha256(self) -> str:
        return self._previous_hash

    @property
    def event_count(self) -> int:
        return self._sequence

    @property
    def inode_identity(self) -> tuple[int, int]:
        """Return the inode captured from the still-open owned handle."""

        return self._owned_identity

    def close(self) -> None:
        if not self._closed:
            self._handle.close()
            self._closed = True

    def __enter__(self) -> Self:
        return self

    def __exit__(self, _exc_type, _exc, _traceback) -> None:
        self.close()


def verify_hash_chain_ledger(path: Path) -> list[dict[str, Any]]:
    """Fail closed unless every ledger line is canonical and hash-linked."""

    try:
        lines = path.read_bytes().splitlines(keepends=True)
    except OSError as exc:
        raise V11DiagnosticError("unable to read V11 attempt ledger") from exc
    if not lines:
        raise V11DiagnosticError("V11 attempt ledger is empty")
    previous = ZERO_EVENT_HASH
    events: list[dict[str, Any]] = []
    for expected_sequence, raw in enumerate(lines):
        if not raw.endswith(b"\n"):
            raise V11DiagnosticError("V11 ledger line lacks newline terminator")
        try:
            event = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise V11DiagnosticError("V11 ledger line is invalid JSON") from exc
        if not isinstance(event, dict) or _canonical_json_bytes(event) + b"\n" != raw:
            raise V11DiagnosticError("V11 ledger event is not canonical JSON")
        if event.get("sequence") != expected_sequence:
            raise V11DiagnosticError("V11 ledger sequence is not contiguous")
        if event.get("previous_event_sha256") != previous:
            raise V11DiagnosticError("V11 ledger previous hash mismatch")
        received = event.get("event_sha256")
        without_hash = dict(event)
        without_hash.pop("event_sha256", None)
        expected = sha256(
            _canonical_json_bytes(without_hash) + previous.encode("ascii")
        ).hexdigest()
        if received != expected:
            raise V11DiagnosticError("V11 ledger event hash mismatch")
        previous = expected
        events.append(event)
    return events


@dataclass(frozen=True)
class V11Scope:
    name: str
    start: date
    end: date
    target_count: int

    def contains(self, target_date: date) -> bool:
        return self.start <= target_date <= self.end


@dataclass(frozen=True)
class V11TargetPlan:
    """Forecast and opaque reveal callbacks for one target date."""

    target_date: date
    build_forecasts: Callable[[], Mapping[str, Any]]
    reveal_actual: Callable[[], Sequence[int]]


@dataclass(frozen=True)
class V11ArtifactPaths:
    claim: Path
    ledger: Path
    report_json: Path
    report_markdown: Path
    report_json_staging: Path
    report_markdown_staging: Path
    claim_staging: Path
    ledger_staging: Path
    acquisition_failure: Path

    @classmethod
    def in_directory(cls, output_dir: Path) -> Self:
        stem = DEFAULT_REPORT_STEM
        return cls(
            claim=output_dir / f"{stem}.claim",
            ledger=output_dir / f"{stem}.ledger.jsonl",
            report_json=output_dir / f"{stem}.json",
            report_markdown=output_dir / f"{stem}.md",
            report_json_staging=output_dir / f".{stem}.json.staging",
            report_markdown_staging=output_dir / f".{stem}.md.staging",
            claim_staging=output_dir / f".{stem}.claim.staging",
            ledger_staging=output_dir / f".{stem}.ledger.jsonl.staging",
            acquisition_failure=output_dir / f".{stem}.acquisition-failure.json",
        )

    def all_normal_paths(self) -> tuple[Path, ...]:
        return tuple(Path(value) for value in self.__dict__.values())


def _artifact_relative_identity(path: Path, output_dir: Path) -> str:
    try:
        relative = path.relative_to(output_dir)
    except ValueError as exc:
        raise V11DiagnosticError(
            "V11 artifact escaped registered output directory"
        ) from exc
    if relative.is_absolute() or ".." in relative.parts:
        raise V11DiagnosticError("V11 artifact relative identity is invalid")
    return relative.as_posix() if relative.parts else "."


def _artifact_from_relative_identity(
    output_dir: Path,
    identity: Any,
    *,
    expected: Path | None = None,
) -> Path:
    if not isinstance(identity, str) or not identity or Path(identity).is_absolute():
        raise V11DiagnosticError("V11 persisted artifact path is not relative")
    relative = Path(identity)
    if ".." in relative.parts or identity == ".":
        raise V11DiagnosticError("V11 persisted artifact path is invalid")
    resolved = output_dir / relative
    if expected is not None and resolved != expected:
        raise V11DiagnosticError("V11 persisted artifact identity changed")
    return resolved


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _never_notify(_subject: str, _body: str) -> bool:
    return False


@dataclass(frozen=True)
class V11DiagnosticRequest:
    root: Path
    output_dir: Path
    code_commit: str
    exact_command: str
    targets: Sequence[V11TargetPlan]
    preflight: Callable[[], Mapping[str, Any]]
    reference: Mapping[str, Any]
    expected_target_count: int = 621
    stability_scopes: tuple[V11Scope, V11Scope] = (
        V11Scope("first_307", date(2020, 1, 1), date(2022, 12, 31), 307),
        V11Scope("second_314", date(2023, 1, 1), date(2025, 12, 31), 314),
    )
    bootstrap_replicates: int = 10_000
    bootstrap_seed: int = 649
    notifier: Notifier = field(default=_never_notify, compare=False, repr=False)
    leakage_audit: Callable[
        [date, Mapping[str, Any], Sequence[int]], Mapping[str, Any]
    ] = field(
        default=lambda _target, _forecast, _actual: {
            "clear": False,
            "checks": [],
        },
        compare=False,
        repr=False,
    )
    clock: Clock = field(default=_utc_now, compare=False, repr=False)
    source_blob_resolver: SourceBlobResolver | None = field(
        default=None, compare=False, repr=False
    )
    registered_identity: V11RegisteredIdentity = REGISTERED_V11_IDENTITY


def _timestamp(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise V11DiagnosticError("V11 audit timestamp must be timezone-aware")
    return (
        value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")
    )


def _validated_timestamp(value: Any, *, field_name: str) -> datetime:
    """Parse the one registered RFC3339 UTC representation, fail closed."""

    if not isinstance(value, str):
        raise V11DiagnosticError(f"V11 {field_name} timestamp is invalid")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=UTC)
    except ValueError as exc:
        raise V11DiagnosticError(f"V11 {field_name} timestamp is invalid") from exc
    if _timestamp(parsed) != value:
        raise V11DiagnosticError(f"V11 {field_name} timestamp is not canonical UTC")
    return parsed


def _actual_main(values: Sequence[int]) -> tuple[int, ...]:
    actual = tuple(values)
    if (
        len(actual) != 6
        or len(set(actual)) != 6
        or any(type(value) is not int or not 1 <= value <= 49 for value in actual)
    ):
        raise V11DiagnosticError("actual main set must be six distinct labels in 1..49")
    return tuple(sorted(actual))


def _probabilities(forecast: Mapping[str, Any]) -> tuple[float, ...]:
    raw = forecast.get("probabilities")
    if isinstance(raw, Mapping):
        if set(raw) != {str(label) for label in range(1, 50)}:
            raise V11DiagnosticError("forecast probability keys must be labels 1..49")
        values = tuple(raw[str(label)] for label in range(1, 50))
    elif isinstance(raw, (list, tuple)):
        values = tuple(raw)
    else:
        raise V11DiagnosticError("forecast probabilities are missing")
    if len(values) != 49 or any(type(value) not in (int, float) for value in values):
        raise V11DiagnosticError("forecast must contain 49 numeric probabilities")
    result = tuple(float(value) for value in values)
    if not all(math.isfinite(value) and 0.0 < value < 1.0 for value in result):
        raise V11DiagnosticError("forecast probabilities must be finite and open")
    if abs(math.fsum(result) - 6.0) > 1.0e-12:
        raise V11DiagnosticError("forecast probabilities must sum to six")
    return result


def _ranking(
    forecast: Mapping[str, Any], probabilities: tuple[float, ...]
) -> tuple[int, ...]:
    raw = forecast.get("ranking")
    if not isinstance(raw, (list, tuple)):
        raise V11DiagnosticError("forecast ranking is missing")
    ranking = tuple(raw)
    expected = tuple(
        sorted(range(1, 50), key=lambda label: (-probabilities[label - 1], label))
    )
    if ranking != expected:
        raise V11DiagnosticError("forecast ranking violates probability/tie order")
    for key, size in (("top6", 6), ("top12", 12), ("top18", 18)):
        if tuple(forecast.get(key, ())) != ranking[:size]:
            raise V11DiagnosticError(f"forecast {key} differs from ranking prefix")
    if tuple(forecast.get("final6", ())) != tuple(sorted(ranking[:6])):
        raise V11DiagnosticError("forecast final6 is not sorted marginal Top-6")
    return ranking


def anchor_log_gains(q_b: float, r_b: float, y: int) -> tuple[float, float]:
    """Expose the model's frozen scalar mechanism calculation to scoring."""

    return _model_anchor_log_gains(q_b, r_b, y)


def score_probability_forecast(
    forecast: Mapping[str, Any], actual_main: Sequence[int]
) -> dict[str, Any]:
    """Score one already-frozen probability forecast after reveal."""

    actual = _actual_main(actual_main)
    probabilities = _probabilities(forecast)
    ranking = _ranking(forecast, probabilities)
    actual_set = set(actual)
    ranks = {label: index for index, label in enumerate(ranking, start=1)}
    brier_terms: list[float] = []
    log_terms: list[float] = []
    for label, probability in enumerate(probabilities, start=1):
        observed = label in actual_set
        brier_terms.append((probability - float(observed)) ** 2)
        log_terms.append(
            -math.log(probability) if observed else -math.log1p(-probability)
        )
    score: dict[str, Any] = {
        "target_date": forecast.get("target_date"),
        "model_name": forecast.get("model_name"),
        "model_version": forecast.get("model_version"),
        "actual": list(actual),
        "actual_ranks": [ranks[label] for label in actual],
        "mean_actual_rank": math.fsum(ranks[label] for label in actual) / 6.0,
        "top6_hits": len(set(forecast["top6"]) & actual_set),
        "top12_hits": len(set(forecast["top12"]) & actual_set),
        "top18_hits": len(set(forecast["top18"]) & actual_set),
        "final6_hits": len(set(forecast["final6"]) & actual_set),
        "matched_final": sorted(set(forecast["final6"]) & actual_set),
        "brier_score": math.fsum(brier_terms) / 49.0,
        "log_loss": math.fsum(log_terms) / 49.0,
        "probabilities": list(probabilities),
        "anchor_response": None,
        "log_g": None,
        "d": None,
    }
    if forecast.get("model_name") in {CANDIDATE_MODEL, CONTROL_MODEL}:
        anchor = forecast.get("anchor")
        if type(anchor) is not int or not 1 <= anchor <= 49:
            raise V11DiagnosticError("V11 anchor must be a label in 1..49")
        y = int(anchor in actual_set)
        log_g, d_value = anchor_log_gains(
            float(forecast["q_b"]), float(forecast["r_b"]), y
        )
        score.update({"anchor_response": y, "log_g": log_g, "d": d_value})
    return score


def _single_draw_top12_coefficients() -> tuple[int, ...]:
    return tuple(math.comb(12, hits) * math.comb(37, 6 - hits) for hits in range(7))


@cache
def _exact_top12_integer_distribution(draw_count: int) -> tuple[int, ...]:
    if type(draw_count) is not int or draw_count < 1:
        raise V11DiagnosticError("exact Top-12 test requires positive draw count")
    one = _single_draw_top12_coefficients()
    distribution = (1,)
    for _ in range(draw_count):
        updated = [0] * (len(distribution) + 6)
        for prior_hits, prior_count in enumerate(distribution):
            for hits, coefficient in enumerate(one):
                updated[prior_hits + hits] += prior_count * coefficient
        distribution = tuple(updated)
    return distribution


def exact_top12_upper_tail(total_hits: int, draw_count: int) -> float:
    if type(draw_count) is not int or draw_count < 1:
        raise V11DiagnosticError("exact Top-12 test requires positive draw count")
    if type(total_hits) is not int or not 0 <= total_hits <= 6 * draw_count:
        raise V11DiagnosticError("exact Top-12 hits are outside valid range")
    distribution = _exact_top12_integer_distribution(draw_count)
    return sum(distribution[total_hits:]) / math.comb(49, 6) ** draw_count


def _bootstrap_interval(
    values: Sequence[float], *, expectation: float, replicates: int, seed: int
) -> list[float]:
    vector = np.asarray(values, dtype=float)
    if vector.ndim != 1 or not len(vector) or not np.isfinite(vector).all():
        raise V11DiagnosticError("bootstrap vector must be finite and non-empty")
    if type(replicates) is not int or replicates < 1 or type(seed) is not int:
        raise V11DiagnosticError("bootstrap settings are invalid")
    rng = np.random.default_rng(seed)
    draws = np.empty(replicates, dtype=float)
    for start in range(0, replicates, 256):
        stop = min(replicates, start + 256)
        indices = rng.integers(0, len(vector), size=(stop - start, len(vector)))
        draws[start:stop] = vector[indices].mean(axis=1) - expectation
    lower, upper = np.quantile(draws, [0.025, 0.975], method="linear")
    return [float(lower), float(upper)]


def _fair_scores() -> tuple[float, float]:
    brier = (6 * (1.0 - FAIR_PROBABILITY) ** 2 + 43 * FAIR_PROBABILITY**2) / 49.0
    log_loss = (
        -(6 * math.log(FAIR_PROBABILITY) + 43 * math.log1p(-FAIR_PROBABILITY)) / 49.0
    )
    return brier, log_loss


def _calibration(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    cells: list[list[tuple[float, int]]] = [[] for _ in range(10)]
    for row in rows:
        actual = set(_actual_main(row["actual"]))
        for label, probability in enumerate(row["probabilities"], start=1):
            probability = float(probability)
            cells[min(9, int(probability * 10.0))].append(
                (probability, int(label in actual))
            )
    total = len(rows) * 49
    bins = []
    weighted = []
    for index, values in enumerate(cells):
        mean = math.fsum(value for value, _ in values) / len(values) if values else None
        observed = math.fsum(y for _, y in values) / len(values) if values else None
        if values:
            weighted.append(len(values) * abs(float(mean) - float(observed)))
        bins.append(
            {
                "bin": index,
                "lower": index / 10.0,
                "upper": (index + 1) / 10.0,
                "right_closed": index == 9,
                "cell_count": len(values),
                "mean_forecast": mean,
                "observed_inclusion_rate": observed,
            }
        )
    return {
        "bins": bins,
        "expected_calibration_error": math.fsum(weighted) / total,
    }


def summarize_v11_scope(
    scores: Sequence[Mapping[str, Any]],
    *,
    scope: str,
    bootstrap_replicates: int = 10_000,
    bootstrap_seed: int = 649,
) -> dict[str, Any]:
    rows = list(scores)
    if not rows:
        raise V11DiagnosticError("V11 scope summary requires rows")
    top6 = [int(row["top6_hits"]) for row in rows]
    top12 = [int(row["top12_hits"]) for row in rows]
    top18 = [int(row["top18_hits"]) for row in rows]
    final6 = [int(row["final6_hits"]) for row in rows]
    if any(a > b or b > c for a, b, c in zip(top6, top12, top18)):
        raise V11DiagnosticError("Top-K hits are not nested")
    count = len(rows)
    avg_top6 = math.fsum(top6) / count
    avg_top12 = math.fsum(top12) / count
    avg_top18 = math.fsum(top18) / count
    avg_brier = math.fsum(float(row["brier_score"]) for row in rows) / count
    avg_log = math.fsum(float(row["log_loss"]) for row in rows) / count
    fair_brier, fair_log = _fair_scores()
    by_year: dict[str, list[Mapping[str, Any]]] = {}
    for row in rows:
        target = row.get("target_date")
        if isinstance(target, str):
            by_year.setdefault(str(date.fromisoformat(target).year), []).append(row)
    log_g_values = [float(row["log_g"]) for row in rows if row.get("log_g") is not None]
    d_values = [float(row["d"]) for row in rows if row.get("d") is not None]
    return {
        "scope": scope,
        "model_name": rows[0].get("model_name"),
        "model_version": rows[0].get("model_version"),
        "draws": count,
        "avg_top6_hits": avg_top6,
        "avg_top12_hits": avg_top12,
        "avg_top18_hits": avg_top18,
        "top6_lift_vs_theory": avg_top6 - FAIR_EXPECTATIONS[6],
        "primary_top12_lift_vs_theory": avg_top12 - FAIR_EXPECTATIONS[12],
        "top18_lift_vs_theory": avg_top18 - FAIR_EXPECTATIONS[18],
        "total_top12_hits": sum(top12),
        "primary_exact_one_sided_p": exact_top12_upper_tail(sum(top12), count),
        "primary_bootstrap_95_ci": _bootstrap_interval(
            top12,
            expectation=FAIR_EXPECTATIONS[12],
            replicates=bootstrap_replicates,
            seed=bootstrap_seed,
        ),
        "avg_actual_rank": math.fsum(float(row["mean_actual_rank"]) for row in rows)
        / count,
        "avg_brier": avg_brier,
        "avg_log_loss": avg_log,
        "fair_constant_brier": fair_brier,
        "fair_constant_log_loss": fair_log,
        "brier_delta_vs_fair": avg_brier - fair_brier,
        "log_loss_delta_vs_fair": avg_log - fair_log,
        "log_g_sum": math.fsum(log_g_values) if log_g_values else None,
        "d_sum": math.fsum(d_values) if d_values else None,
        "final6_hit_histogram": {str(hits): final6.count(hits) for hits in range(7)},
        "calibration": _calibration(rows),
        "performance_by_year": {
            year: {
                "draws": len(year_rows),
                "avg_top6_hits": math.fsum(float(row["top6_hits"]) for row in year_rows)
                / len(year_rows),
                "avg_top12_hits": math.fsum(
                    float(row["top12_hits"]) for row in year_rows
                )
                / len(year_rows),
                "avg_top18_hits": math.fsum(
                    float(row["top18_hits"]) for row in year_rows
                )
                / len(year_rows),
            }
            for year, year_rows in sorted(by_year.items())
        },
    }


def paired_top12_bootstrap(
    candidate_scores: Sequence[Mapping[str, Any]],
    comparison_scores: Sequence[Mapping[str, Any]],
    *,
    scope: str,
    bootstrap_replicates: int = 10_000,
    bootstrap_seed: int = 649,
) -> dict[str, Any]:
    left = list(candidate_scores)
    right = list(comparison_scores)
    if not left or len(left) != len(right):
        raise V11DiagnosticError("paired Top-12 inputs must align")
    dates_left = [row.get("target_date") for row in left]
    dates_right = [row.get("target_date") for row in right]
    if dates_left != dates_right or len(set(dates_left)) != len(dates_left):
        raise V11DiagnosticError("paired Top-12 target dates are not aligned")
    differences = [
        int(candidate["top12_hits"]) - int(comparison["top12_hits"])
        for candidate, comparison in zip(left, right)
    ]
    return {
        "scope": scope,
        "draws": len(differences),
        "mean_difference": math.fsum(differences) / len(differences),
        "bootstrap_95_ci": _bootstrap_interval(
            differences,
            expectation=0.0,
            replicates=bootstrap_replicates,
            seed=bootstrap_seed,
        ),
    }


def holm_v11_adjusted_p(raw_primary_p: float) -> float:
    if not math.isfinite(raw_primary_p) or not 0.0 <= raw_primary_p <= 1.0:
        raise V11DiagnosticError("V11 raw p-value is invalid")
    return min(1.0, 3.0 * raw_primary_p)


def _null_control(summary: Mapping[str, Any]) -> bool:
    lower, upper = (float(value) for value in summary["primary_bootstrap_95_ci"])
    return float(summary["primary_exact_one_sided_p"]) > 0.05 or (lower <= 0.0 <= upper)


def v11_historical_decision(
    *,
    candidate: Mapping[str, Any],
    candidate_halves: Sequence[Mapping[str, Any]],
    control: Mapping[str, Any],
    control_halves: Sequence[Mapping[str, Any]],
    random_control: Mapping[str, Any],
    random_control_halves: Sequence[Mapping[str, Any]],
    v1: Mapping[str, Any],
    v1_halves: Sequence[Mapping[str, Any]],
    paired_v1: Mapping[str, Any],
    paired_v1_halves: Sequence[Mapping[str, Any]],
    paired_control: Mapping[str, Any],
    paired_control_halves: Sequence[Mapping[str, Any]],
    mechanism: Mapping[str, Any],
    audit_warnings: Sequence[str],
) -> dict[str, Any]:
    """Apply exactly the ten registered conjunctive V11 gates."""

    scopes_candidate = [candidate, *candidate_halves]
    scopes_control = [control, *control_halves]
    scopes_random = [random_control, *random_control_halves]
    scopes_v1 = [v1, *v1_halves]
    gates = {
        SCIENTIFIC_GATE_NAMES[0]: float(candidate["primary_top12_lift_vs_theory"])
        > 0.0,
        SCIENTIFIC_GATE_NAMES[1]: float(candidate["primary_holm_adjusted_p"]) <= 0.05,
        SCIENTIFIC_GATE_NAMES[2]: float(candidate["primary_bootstrap_95_ci"][0]) > 0.0,
        SCIENTIFIC_GATE_NAMES[3]: all(
            float(item["primary_top12_lift_vs_theory"]) > 0.0
            for item in candidate_halves
        ),
        SCIENTIFIC_GATE_NAMES[4]: all(
            float(item["bootstrap_95_ci"][0]) > 0.0
            for item in [paired_v1, *paired_v1_halves]
        ),
        SCIENTIFIC_GATE_NAMES[5]: (
            all(
                float(item["bootstrap_95_ci"][0]) > 0.0
                for item in [paired_control, *paired_control_halves]
            )
            and all(_null_control(item) for item in scopes_control)
            and all(_null_control(item) for item in scopes_random)
        ),
        SCIENTIFIC_GATE_NAMES[6]: all(
            float(item["top6_lift_vs_theory"]) > 0.0 for item in scopes_candidate
        ),
        SCIENTIFIC_GATE_NAMES[7]: all(
            float(candidate_scope["brier_delta_vs_fair"]) <= PROPER_SCORE_TOLERANCE
            and float(candidate_scope["log_loss_delta_vs_fair"])
            <= PROPER_SCORE_TOLERANCE
            and float(candidate_scope["avg_brier"]) - float(v1_scope["avg_brier"])
            <= PROPER_SCORE_TOLERANCE
            and float(candidate_scope["avg_log_loss"]) - float(v1_scope["avg_log_loss"])
            <= PROPER_SCORE_TOLERANCE
            for candidate_scope, v1_scope in zip(scopes_candidate, scopes_v1)
        ),
        SCIENTIFIC_GATE_NAMES[8]: (
            float(mechanism["candidate_aggregate_log_g"]) >= MECHANISM_THRESHOLD
            and float(mechanism["candidate_aggregate_d"]) > 0.0
            and all(float(value) > 0.0 for value in mechanism["candidate_half_log_g"])
            and all(float(value) > 0.0 for value in mechanism["candidate_half_d"])
            and float(mechanism["control_aggregate_log_g"]) < MECHANISM_THRESHOLD
            and float(mechanism["candidate_minus_control_aggregate_log_g"]) > 0.0
            and float(mechanism["candidate_minus_control_aggregate_d"]) > 0.0
            and all(
                float(value) > 0.0
                for value in mechanism["candidate_minus_control_half_log_g"]
            )
            and all(
                float(value) > 0.0
                for value in mechanism["candidate_minus_control_half_d"]
            )
        ),
        SCIENTIFIC_GATE_NAMES[9]: not audit_warnings,
    }
    passed = all(gates.values())
    return {
        "gates": gates,
        "all_scientific_gates_passed": passed,
        "decision": "eligible_for_separate_reviewed_shadow_decision"
        if passed
        else ("archive" if audit_warnings else "reject"),
        "secondary_rescue": "prohibited",
        "prospective_status": "not_activated",
    }


def _validate_forecast_payload(
    payload: Mapping[str, Any], *, target_date: date
) -> dict[str, Any]:
    normalized = dict(payload)
    if set(normalized) != {"target_date", "prefix", "forecasts"}:
        raise V11DiagnosticError("V11 forecast bundle keys changed")
    if normalized["target_date"] != target_date.isoformat():
        raise V11DiagnosticError("V11 forecast target date mismatch")
    prefix = normalized["prefix"]
    if not isinstance(prefix, Mapping) or set(prefix) != {
        "history_draws",
        "history_through",
        "strict_prefix_sha256",
    }:
        raise V11DiagnosticError("V11 strict prefix payload is invalid")
    history_through = prefix["history_through"]
    if (
        history_through is not None
        and date.fromisoformat(history_through) >= target_date
    ):
        raise V11DiagnosticError("V11 prefix is not strictly before target")
    digest = prefix["strict_prefix_sha256"]
    if (
        type(prefix["history_draws"]) is not int
        or prefix["history_draws"] < 1
        or not _is_lower_hex(digest, 64)
    ):
        raise V11DiagnosticError("V11 strict prefix digest is invalid")
    forecasts = normalized["forecasts"]
    if not isinstance(forecasts, Mapping) or set(forecasts) != set(MODEL_ORDER):
        raise V11DiagnosticError("V11 forecast model set changed")
    for model_name in MODEL_ORDER:
        forecast = forecasts[model_name]
        if not isinstance(forecast, Mapping):
            raise V11DiagnosticError("V11 model forecast is invalid")
        if forecast.get("model_name") != model_name:
            raise V11DiagnosticError("V11 model name mismatch")
        expected_version = (
            MODEL_VERSION
            if model_name in {CANDIDATE_MODEL, CONTROL_MODEL}
            else "v1.0.0"
        )
        if forecast.get("model_version") != expected_version:
            raise V11DiagnosticError("V11 forecast model version changed")
        if forecast.get("feature_set") != FEATURE_SET_BY_MODEL[model_name]:
            raise V11DiagnosticError("V11 forecast feature set changed")
        if forecast.get("target_date") != target_date.isoformat():
            raise V11DiagnosticError("V11 model target date mismatch")
        if forecast.get("history_draws") != prefix["history_draws"]:
            raise V11DiagnosticError("V11 model prefix draw count mismatch")
        if forecast.get("history_through") != history_through:
            raise V11DiagnosticError("V11 model history boundary mismatch")
        probabilities = _probabilities(forecast)
        _ranking(forecast, probabilities)
        if model_name in {CANDIDATE_MODEL, CONTROL_MODEL}:
            required = {
                "anchor_source_date",
                "anchor_kind",
                "anchor",
                "transition_count",
                "beta",
                "q_b",
                "r_b",
            }
            if not required <= set(forecast):
                raise V11DiagnosticError("V11 anchor forecast metadata is incomplete")
            if model_name == CONTROL_MODEL and not _is_lower_hex(
                forecast.get("pseudo_bonus_selection_sha256"), 64
            ):
                raise V11DiagnosticError(
                    "V11 pseudo-control selection digest is incomplete"
                )
            if forecast.get("D") != forecast.get("transition_count"):
                raise V11DiagnosticError("V11 transition-count alias changed")
            if (
                type(forecast.get("transition_count")) is not int
                or forecast["transition_count"] < 0
                or type(forecast.get("beta")) not in (int, float)
                or not math.isfinite(float(forecast["beta"]))
            ):
                raise V11DiagnosticError("V11 anchor fit metadata is invalid")
            expected_kind = (
                "published_bonus"
                if model_name == CANDIDATE_MODEL
                else "deterministic_pseudo_bonus"
            )
            if (
                forecast.get("anchor_kind") != expected_kind
                or forecast.get("anchor_source_date") != history_through
            ):
                raise V11DiagnosticError("V11 anchor identity changed")
            for key in ("q_b", "r_b"):
                value = forecast[key]
                if (
                    type(value) not in (int, float)
                    or not math.isfinite(value)
                    or not 0.0 < value < 1.0
                ):
                    raise V11DiagnosticError(f"V11 {key} is invalid")
        elif model_name == V1_MODEL:
            if forecast.get("strict_prefix_sha256") != digest:
                raise V11DiagnosticError("V11 V1 prefix digest changed")
        elif forecast.get("seed") != 649_000_000 + target_date.toordinal():
            raise V11DiagnosticError("V11 random forecast seed changed")
    _canonical_json_bytes(normalized)
    return normalized


def _validate_forecast_source_contract(
    payload: Mapping[str, Any], source_row: _RegisteredSourceRow
) -> None:
    """Bind both V11 arms to the registered preceding draw and one V1 base."""

    forecasts = payload["forecasts"]
    base_probabilities = _probabilities(forecasts[V1_MODEL])
    try:
        source_draw = Draw(source_row.draw_date, source_row.main, source_row.bonus)
        control_anchor, control_digest = select_pseudo_bonus(source_draw)
    except (TypeError, ValueError) as exc:
        raise V11DiagnosticError("V11 registered source anchor is invalid") from exc
    expected_anchors = {
        CANDIDATE_MODEL: source_row.bonus,
        CONTROL_MODEL: control_anchor,
    }
    if forecasts[CONTROL_MODEL].get("pseudo_bonus_selection_sha256") != control_digest:
        raise V11DiagnosticError("V11 pseudo-control selection digest changed")
    transition_counts: list[int] = []
    for model_name in (CANDIDATE_MODEL, CONTROL_MODEL):
        forecast = forecasts[model_name]
        anchor = expected_anchors[model_name]
        if forecast.get("anchor") != anchor:
            raise V11DiagnosticError("V11 anchor differs from registered source")
        if forecast.get("q_b") != base_probabilities[anchor - 1]:
            raise V11DiagnosticError("V11 anchor probability differs from V1 base")
        try:
            expected_probabilities = tilt_probabilities(
                base_probabilities, anchor, float(forecast["beta"])
            )
        except (TypeError, ValueError, RuntimeError) as exc:
            raise V11DiagnosticError("V11 registered anchor tilt is invalid") from exc
        if _probabilities(forecast) != expected_probabilities:
            raise V11DiagnosticError("V11 tilted probabilities are not reproducible")
        if forecast.get("r_b") != expected_probabilities[anchor - 1]:
            raise V11DiagnosticError("V11 tilted anchor probability changed")
        transition_counts.append(int(forecast["transition_count"]))
    if transition_counts[0] != transition_counts[1]:
        raise V11DiagnosticError("V11 candidate/control transition counts differ")


def _scope_rows(
    rows: Sequence[Mapping[str, Any]], scope: V11Scope
) -> list[Mapping[str, Any]]:
    selected = [
        row
        for row in rows
        if scope.contains(date.fromisoformat(str(row["target_date"])))
    ]
    if len(selected) != scope.target_count:
        raise V11DiagnosticError(f"scope {scope.name} target count changed")
    return selected


def build_opportunity_record(
    forecasts: Mapping[str, Mapping[str, Any]],
    forecast_hashes: Mapping[str, str],
    actual: tuple[int, ...],
    *,
    target_date: date,
    prior_u_values: Sequence[int],
) -> dict[str, Any]:
    grouped: dict[tuple[int, ...], list[str]] = {}
    for model_name in MODEL_ORDER:
        final6 = tuple(forecasts[model_name]["final6"])
        grouped.setdefault(final6, []).append(model_name)
    actual_set = set(actual)
    unique_sets = []
    for final6, producers in grouped.items():
        producer_names = [OPPORTUNITY_MODEL_NAMES[producer] for producer in producers]
        producer_hashes = {
            OPPORTUNITY_MODEL_NAMES[producer]: forecast_hashes[producer]
            for producer in producers
        }
        unique_sets.append(
            {
                "target": target_date.isoformat(),
                "final6": list(final6),
                "primary_producer_model_name": producer_names[0],
                "producer_model_names": producer_names,
                "producer_forecast_sha256_by_model": producer_hashes,
                "actual": list(actual),
                "hits": len(set(final6) & actual_set),
                "exact_6of6": set(final6) == actual_set,
                "chronology_status": "prediction_frozen_fsynced_before_reveal",
            }
        )
    u_t = len(unique_sets)
    u_values = [*prior_u_values, u_t]
    cumulative = sum(u_values)
    fair_probability = -math.expm1(
        math.fsum(math.log1p(-value / FAIR_TOTAL_SIX_SETS) for value in u_values)
    )
    return {
        "target_date": target_date.isoformat(),
        "actual_main": list(actual),
        "chronology_status": "prediction_frozen_fsynced_before_reveal",
        "u_t": u_t,
        "cumulative_unique_opportunities": cumulative,
        "cumulative_familywise_fair_probability": fair_probability,
        "unique_final6_sets": unique_sets,
    }


def _build_progressive_record(
    *,
    target_date: date,
    forecast_sha256: str,
    forecast: Mapping[str, Any],
    score: Mapping[str, Any],
    actual: tuple[int, ...],
    previous_maximum: int,
    implementation_commit: str,
) -> dict[str, Any]:
    current = int(score["final6_hits"])
    return {
        "target_date": target_date.isoformat(),
        "record_scope": "v11_run_local",
        "evidence_lane": "consumed_historical_diagnostic",
        "global_historical_maximum": "unknown",
        "legacy_reported_floor_final6_hits": 4,
        "verified_full_snapshot_maximum_final6_hits": 3,
        "previous_maximum_final6_hits": previous_maximum,
        "current_final6_hits": current,
        "new_maximum_final6_hits": max(previous_maximum, current),
        "new_within_run_record": current > previous_maximum,
        "model_name": forecast["model_name"],
        "model_version": forecast["model_version"],
        "implementation_commit": implementation_commit,
        "training_cutoff": forecast["history_through"],
        "feature_set": forecast["feature_set"],
        "frozen_parameters": {
            key: forecast[key]
            for key in ("anchor", "transition_count", "D", "beta", "q_b", "r_b")
        },
        "evaluation": {
            key: score[key]
            for key in (
                "top6_hits",
                "top12_hits",
                "top18_hits",
                "final6_hits",
                "matched_final",
                "actual_ranks",
                "mean_actual_rank",
                "brier_score",
                "log_loss",
                "log_g",
                "d",
            )
        },
        "forecast_sha256": forecast_sha256,
        "prediction": list(forecast["final6"]),
        "actual": list(actual),
    }


def _mechanism_delta(
    candidate: Sequence[Mapping[str, Any]],
    control: Sequence[Mapping[str, Any]],
    key: str,
) -> float:
    if [row["target_date"] for row in candidate] != [
        row["target_date"] for row in control
    ]:
        raise V11DiagnosticError("mechanism rows are not aligned")
    return math.fsum(
        float(left[key]) - float(right[key]) for left, right in zip(candidate, control)
    )


def _build_report(
    request: V11DiagnosticRequest,
    *,
    preflight: Mapping[str, Any],
    claim_sha256: str,
    results: Mapping[str, Sequence[Mapping[str, Any]]],
    per_target: Sequence[Mapping[str, Any]],
    record_ledger: Sequence[Mapping[str, Any]],
    ledger: HashChainLedger,
    operational_warnings: Sequence[str] = (),
) -> dict[str, Any]:
    scopes = [
        V11Scope(
            "aggregate_621",
            request.targets[0].target_date,
            request.targets[-1].target_date,
            len(request.targets),
        ),
        *request.stability_scopes,
    ]
    summaries: dict[str, dict[str, Any]] = {name: {} for name in MODEL_ORDER}
    scoped_rows: dict[str, dict[str, list[Mapping[str, Any]]]] = {
        name: {} for name in MODEL_ORDER
    }
    for model_name in MODEL_ORDER:
        for scope in scopes:
            rows = _scope_rows(results[model_name], scope)
            scoped_rows[model_name][scope.name] = rows
            summaries[model_name][scope.name] = summarize_v11_scope(
                rows,
                scope=scope.name,
                bootstrap_replicates=request.bootstrap_replicates,
                bootstrap_seed=request.bootstrap_seed,
            )
    candidate_aggregate = summaries[CANDIDATE_MODEL][scopes[0].name]
    candidate_aggregate["primary_holm_adjusted_p"] = holm_v11_adjusted_p(
        candidate_aggregate["primary_exact_one_sided_p"]
    )
    for scope in scopes[1:]:
        summaries[CANDIDATE_MODEL][scope.name]["primary_holm_adjusted_p"] = None
    paired_v1 = {}
    paired_control = {}
    for scope in scopes:
        candidate_rows = scoped_rows[CANDIDATE_MODEL][scope.name]
        paired_v1[scope.name] = paired_top12_bootstrap(
            candidate_rows,
            scoped_rows[V1_MODEL][scope.name],
            scope=scope.name,
            bootstrap_replicates=request.bootstrap_replicates,
            bootstrap_seed=request.bootstrap_seed,
        )
        paired_control[scope.name] = paired_top12_bootstrap(
            candidate_rows,
            scoped_rows[CONTROL_MODEL][scope.name],
            scope=scope.name,
            bootstrap_replicates=request.bootstrap_replicates,
            bootstrap_seed=request.bootstrap_seed,
        )
    candidate_rows = scoped_rows[CANDIDATE_MODEL][scopes[0].name]
    control_rows = scoped_rows[CONTROL_MODEL][scopes[0].name]
    mechanism = {
        "candidate_aggregate_log_g": summaries[CANDIDATE_MODEL][scopes[0].name][
            "log_g_sum"
        ],
        "candidate_aggregate_d": summaries[CANDIDATE_MODEL][scopes[0].name]["d_sum"],
        "candidate_half_log_g": [
            summaries[CANDIDATE_MODEL][scope.name]["log_g_sum"] for scope in scopes[1:]
        ],
        "candidate_half_d": [
            summaries[CANDIDATE_MODEL][scope.name]["d_sum"] for scope in scopes[1:]
        ],
        "control_aggregate_log_g": summaries[CONTROL_MODEL][scopes[0].name][
            "log_g_sum"
        ],
        "candidate_minus_control_aggregate_log_g": _mechanism_delta(
            candidate_rows, control_rows, "log_g"
        ),
        "candidate_minus_control_aggregate_d": _mechanism_delta(
            candidate_rows, control_rows, "d"
        ),
        "candidate_minus_control_half_log_g": [
            _mechanism_delta(
                scoped_rows[CANDIDATE_MODEL][scope.name],
                scoped_rows[CONTROL_MODEL][scope.name],
                "log_g",
            )
            for scope in scopes[1:]
        ],
        "candidate_minus_control_half_d": [
            _mechanism_delta(
                scoped_rows[CANDIDATE_MODEL][scope.name],
                scoped_rows[CONTROL_MODEL][scope.name],
                "d",
            )
            for scope in scopes[1:]
        ],
    }
    warnings = list(preflight.get("audit_warnings", []))
    decision = v11_historical_decision(
        candidate=summaries[CANDIDATE_MODEL][scopes[0].name],
        candidate_halves=[
            summaries[CANDIDATE_MODEL][scope.name] for scope in scopes[1:]
        ],
        control=summaries[CONTROL_MODEL][scopes[0].name],
        control_halves=[summaries[CONTROL_MODEL][scope.name] for scope in scopes[1:]],
        random_control=summaries[RANDOM_MODEL][scopes[0].name],
        random_control_halves=[
            summaries[RANDOM_MODEL][scope.name] for scope in scopes[1:]
        ],
        v1=summaries[V1_MODEL][scopes[0].name],
        v1_halves=[summaries[V1_MODEL][scope.name] for scope in scopes[1:]],
        paired_v1=paired_v1[scopes[0].name],
        paired_v1_halves=[paired_v1[scope.name] for scope in scopes[1:]],
        paired_control=paired_control[scopes[0].name],
        paired_control_halves=[paired_control[scope.name] for scope in scopes[1:]],
        mechanism=mechanism,
        audit_warnings=warnings,
    )
    return {
        "schema_version": 1,
        "experiment_id": EXPERIMENT_ID,
        "model_version": MODEL_VERSION,
        "evidence_lane": "consumed_historical_diagnostic",
        "registration_commit": REGISTRATION_COMMIT,
        "implementation_commit": request.code_commit,
        "claim_sha256": claim_sha256,
        "preflight": dict(preflight),
        "historical_lane": {
            "target_count": len(per_target),
            "target_start": request.targets[0].target_date.isoformat(),
            "target_end": request.targets[-1].target_date.isoformat(),
            "not_blind_or_confirmatory": True,
        },
        "summaries": summaries,
        "paired_candidate_minus_v1": paired_v1,
        "paired_candidate_minus_control": paired_control,
        "mechanism": mechanism,
        "historical_decision": decision,
        "per_target": list(per_target),
        "progressive_record_ledger": list(record_ledger),
        "scientific_audit_warnings": warnings,
        "operational_warnings": list(operational_warnings),
        "notification_status_at_report_publication": (
            "pending_post_publication"
            if decision["all_scientific_gates_passed"]
            else "not_required"
        ),
        "notification_result_authority": "external_workflow_receipt_after_terminal",
        "opportunity_total": sum(int(row["opportunity"]["u_t"]) for row in per_target),
        "ledger_head_before_publication": ledger.head_sha256,
        "prospective_status": "not_activated",
    }


def _exclusive_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        _directory_fsync(path.parent)
    except FileExistsError as exc:
        raise V11DiagnosticError(f"V11 artifact already exists: {path.name}") from exc


@dataclass
class _OwnedArtifactLease:
    """Pin a stage inode until its final link and all cleanup are complete.

    Keeping the descriptor open prevents POSIX inode-number reuse from making
    an unlinked-and-recreated path appear owned.  The surrounding transaction
    still assumes every same-UID writer to the output directory follows this
    exclusive-stage protocol; POSIX has no atomic compare-and-unlink primitive.
    """

    handle: Any
    content_sha256: str

    def close(self) -> None:
        if not self.handle.closed:
            self.handle.close()


class _OwnedStagingWriteError(OSError):
    """A staging write failed after this attempt acquired a specific inode."""

    def __init__(self, path: Path, lease: _OwnedArtifactLease, cause: OSError) -> None:
        super().__init__(str(cause))
        self.path = path
        self.lease = lease


def _write_staging(path: Path, payload: bytes) -> _OwnedArtifactLease:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = None
    lease: _OwnedArtifactLease | None = None
    try:
        handle = path.open("x+b")
        lease = _OwnedArtifactLease(handle, sha256(payload).hexdigest())
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
        _directory_fsync(path.parent)
    except FileExistsError as exc:
        raise V11DiagnosticError(f"V11 artifact already exists: {path.name}") from exc
    except OSError as exc:
        if lease is not None:
            raise _OwnedStagingWriteError(path, lease, exc) from exc
        if handle is not None:
            handle.close()
        raise
    return lease


def _inode_identity(path: Path) -> tuple[int, int]:
    stat = path.stat(follow_symlinks=False)
    return stat.st_dev, stat.st_ino


def _open_fd_sha256(descriptor: int) -> str:
    """Hash a pinned regular-file descriptor without moving its write offset."""

    digest = sha256()
    offset = 0
    while chunk := os.pread(descriptor, 1024 * 1024, offset):
        digest.update(chunk)
        offset += len(chunk)
    return digest.hexdigest()


def _owned_path_matches(path: Path, lease: _OwnedArtifactLease) -> bool:
    try:
        descriptor = lease.handle.fileno()
        owned_stat = os.fstat(descriptor)
        path_stat = path.stat(follow_symlinks=False)
        return (path_stat.st_dev, path_stat.st_ino) == (
            owned_stat.st_dev,
            owned_stat.st_ino,
        ) and _open_fd_sha256(descriptor) == lease.content_sha256
    except (OSError, ValueError):
        return False


def _directory_entry_exists(path: Path) -> bool:
    """Return whether the directory name exists, including dangling symlinks."""

    try:
        path.lstat()
    except FileNotFoundError:
        return False
    return True


def _foreign_entry_binding(path: Path) -> tuple[str, str]:
    metadata = path.lstat()
    file_type = stat.S_IFMT(metadata.st_mode)
    if stat.S_ISREG(metadata.st_mode):
        return "foreign_snapshot_sha256", _file_sha256(path)
    if stat.S_ISLNK(metadata.st_mode):
        target = os.fsencode(os.readlink(path))
        return "foreign_symlink_target_sha256", sha256(target).hexdigest()
    encoded_type = f"mode:{file_type:o}".encode("ascii")
    return "foreign_entry_type_sha256", sha256(encoded_type).hexdigest()


def _unlink_owned_path(path: Path, lease: _OwnedArtifactLease) -> None:
    if not _directory_entry_exists(path):
        return
    if not _owned_path_matches(path, lease):
        raise V11DiagnosticError(f"refusing to unlink foreign artifact: {path.name}")
    path.unlink()


def _require_owned_artifacts(
    artifacts: Sequence[tuple[Path, _OwnedArtifactLease]],
    *,
    phase: str,
) -> None:
    """Revalidate every transaction name after the preceding OS boundary."""

    changed = [
        path.name for path, lease in artifacts if not _owned_path_matches(path, lease)
    ]
    if changed:
        raise V11DiagnosticError(
            f"V11 owned artifact changed during {phase}: {sorted(changed)}"
        )


def _record_acquisition_failure(
    paths: V11ArtifactPaths,
    error: BaseException,
    rollback_errors: Sequence[Mapping[str, Any]],
) -> None:
    evidence = {
        "schema_version": 1,
        "status": "consumed_archive_acquisition_failure",
        "error_type": type(error).__name__,
        "rollback_failures": [dict(item) for item in rollback_errors],
    }
    try:
        _exclusive_write(
            paths.acquisition_failure, _canonical_json_bytes(evidence) + b"\n"
        )
    except Exception:  # noqa: BLE001, S110 - residual artifacts still block rerun
        # Existing acquisition artifacts remain durable evidence and block reruns.
        pass


def _acquisition_operational_warnings(
    receipt: Mapping[str, Any],
) -> list[str]:
    stage_results = receipt.get("stage_results")
    parent_fsync = receipt.get("parent_fsync")
    failed = (
        not isinstance(stage_results, list)
        or any(item.get("outcome") != "removed" for item in stage_results)
        or not isinstance(parent_fsync, Mapping)
        or parent_fsync.get("outcome") != "succeeded"
    )
    return [f"acquisition_cleanup_failed:{canonical_sha256(receipt)}"] if failed else []


def _acquire_attempt(
    paths: V11ArtifactPaths,
    claim_payload: Mapping[str, Any],
) -> tuple[HashChainLedger, str, dict[str, Any]]:
    """Acquire the permanent one-shot claim before any forecast can be built.

    POSIX cannot atomically create two independent final paths.  The durable
    claim hardlink is the one-shot linearization point; every earlier failure is
    rolled back when possible, and every residual artifact permanently blocks a
    retry.
    """

    claim_bytes = _canonical_json_bytes(claim_payload) + b"\n"
    expected_claim_sha256 = sha256(claim_bytes).hexdigest()
    committed = False
    ledger_stage: HashChainLedger | None = None
    cleanup_receipt: dict[str, Any] | None = None
    claim_stage_lease: _OwnedArtifactLease | None = None
    ledger_stage_lease: _OwnedArtifactLease | None = None
    claim_final_created = False
    ledger_final_created = False
    post_commit_verification_failures: list[dict[str, Any]] = []
    try:
        try:
            claim_stage_lease = _write_staging(paths.claim_staging, claim_bytes)
        except _OwnedStagingWriteError as exc:
            claim_stage_lease = exc.lease
            raise
        if _file_sha256(paths.claim_staging) != expected_claim_sha256:
            raise V11DiagnosticError("V11 staged claim digest mismatch")
        ledger_stage = HashChainLedger.create(paths.ledger_staging)
        ledger_stage_lease = _OwnedArtifactLease(
            ledger_stage._handle,
            sha256(b"").hexdigest(),
        )
        claimed_event = ledger_stage.append(
            "claimed",
            {
                "claim_sha256": expected_claim_sha256,
                "implementation_commit": claim_payload["implementation_commit"],
                "started_at_utc": claim_payload["started_at_utc"],
            },
        )
        ledger_stage_lease = _OwnedArtifactLease(
            ledger_stage._handle,
            sha256(_canonical_json_bytes(claimed_event) + b"\n").hexdigest(),
        )
        os.link(paths.ledger_staging, paths.ledger)
        ledger_final_created = True
        if not _owned_path_matches(paths.ledger, ledger_stage_lease):
            raise V11DiagnosticError(
                "V11 linked ledger identity or content differs from owned stage"
            )
        _directory_fsync(paths.ledger.parent)
        _require_owned_artifacts(
            (
                (paths.ledger, ledger_stage_lease),
                (paths.ledger_staging, ledger_stage_lease),
                (paths.claim_staging, claim_stage_lease),
            ),
            phase="before claim link",
        )
        os.link(paths.claim_staging, paths.claim)
        claim_final_created = True
        _require_owned_artifacts(
            (
                (paths.claim, claim_stage_lease),
                (paths.ledger, ledger_stage_lease),
                (paths.claim_staging, claim_stage_lease),
                (paths.ledger_staging, ledger_stage_lease),
            ),
            phase="after claim link",
        )
        _directory_fsync(paths.claim.parent)
        _require_owned_artifacts(
            (
                (paths.claim, claim_stage_lease),
                (paths.ledger, ledger_stage_lease),
                (paths.claim_staging, claim_stage_lease),
                (paths.ledger_staging, ledger_stage_lease),
            ),
            phase="after acquisition commit fsync",
        )
        committed = True
    except Exception as exc:
        rollback_errors: list[dict[str, Any]] = []
        for created, final, lease in (
            (claim_final_created, paths.claim, claim_stage_lease),
            (ledger_final_created, paths.ledger, ledger_stage_lease),
        ):
            if not created or lease is None:
                continue
            try:
                _unlink_owned_path(final, lease)
            except (OSError, V11DiagnosticError) as rollback_exc:
                rollback_errors.append(
                    {
                        "phase": "rollback_final_unlink",
                        "path": _artifact_relative_identity(final, paths.claim.parent),
                        "error_type": type(rollback_exc).__name__,
                    }
                )
        for staging, lease in (
            (paths.claim_staging, claim_stage_lease),
            (paths.ledger_staging, ledger_stage_lease),
        ):
            if lease is None:
                continue
            try:
                _unlink_owned_path(staging, lease)
            except (OSError, V11DiagnosticError) as rollback_exc:
                rollback_errors.append(
                    {
                        "phase": "rollback_stage_unlink",
                        "path": _artifact_relative_identity(
                            staging, paths.claim.parent
                        ),
                        "error_type": type(rollback_exc).__name__,
                    }
                )
        try:
            _directory_fsync(paths.claim.parent)
        except OSError as rollback_exc:
            rollback_errors.append(
                {
                    "phase": "rollback_parent_fsync",
                    "path": ".",
                    "error_type": type(rollback_exc).__name__,
                }
            )
        if rollback_errors:
            _record_acquisition_failure(paths, exc, rollback_errors)
            raise V11DiagnosticError(
                f"V11 acquisition failed and rollback retained evidence: {rollback_errors}"
            ) from exc
        raise
    finally:
        try:
            if committed:
                stage_results = []
                for role, staging, lease in (
                    ("claim", paths.claim_staging, claim_stage_lease),
                    ("ledger", paths.ledger_staging, ledger_stage_lease),
                ):
                    if lease is None:  # pragma: no cover - committed invariant
                        raise V11DiagnosticError(
                            "V11 committed acquisition lacks owned stage lease"
                        )
                    outcome = "removed"
                    error_type = None
                    content_binding = None
                    content_sha256 = None
                    try:
                        _unlink_owned_path(staging, lease)
                    except V11DiagnosticError as exc:
                        outcome = "foreign_inode_refused"
                        error_type = type(exc).__name__
                        content_binding, content_sha256 = _foreign_entry_binding(
                            staging
                        )
                    except OSError:
                        if not _directory_entry_exists(staging):
                            outcome = "removed"
                            error_type = None
                        elif not _owned_path_matches(staging, lease):
                            outcome = "foreign_inode_refused"
                            error_type = "V11DiagnosticError"
                            content_binding, content_sha256 = _foreign_entry_binding(
                                staging
                            )
                        else:
                            outcome = "unlink_failed"
                            error_type = "OSError"
                            content_binding = "mutable_final_bytes"
                    stage_results.append(
                        {
                            "phase": "stage_unlink",
                            "role": role,
                            "path": _artifact_relative_identity(
                                staging, paths.claim.parent
                            ),
                            "outcome": outcome,
                            "error_type": error_type,
                            "content_binding": content_binding,
                            "content_sha256": content_sha256,
                        }
                    )
                parent_outcome = "succeeded"
                parent_error_type = None
                try:
                    _directory_fsync(paths.claim.parent)
                except OSError:
                    parent_outcome = "failed"
                    parent_error_type = "OSError"
                cleanup_receipt = {
                    "schema_version": 1,
                    "phase": "post_claim_commit_cleanup",
                    "stage_results": stage_results,
                    "parent_fsync": {
                        "phase": "parent_directory_fsync",
                        "path": ".",
                        "outcome": parent_outcome,
                        "error_type": parent_error_type,
                    },
                }
                for final, lease in (
                    (paths.claim, claim_stage_lease),
                    (paths.ledger, ledger_stage_lease),
                ):
                    if lease is not None and not _owned_path_matches(final, lease):
                        post_commit_verification_failures.append(
                            {
                                "phase": "post_commit_final_verification",
                                "path": _artifact_relative_identity(
                                    final, paths.claim.parent
                                ),
                                "error_type": "V11DiagnosticError",
                            }
                        )
        finally:
            if ledger_stage is not None and (not committed or cleanup_receipt is None):
                ledger_stage.close()
            if claim_stage_lease is not None:
                claim_stage_lease.close()
    if cleanup_receipt is None:  # pragma: no cover - success return invariant
        raise V11DiagnosticError("V11 acquisition cleanup receipt is missing")
    if ledger_stage is None:  # pragma: no cover - committed invariant
        raise V11DiagnosticError("V11 acquisition ledger handle is missing")
    if post_commit_verification_failures:
        error = V11DiagnosticError(
            "V11 acquisition final identity changed after committed cleanup"
        )
        _record_acquisition_failure(
            paths,
            error,
            post_commit_verification_failures,
        )
        ledger_stage.close()
        raise V11DiagnosticError(
            "V11 acquisition failed; foreign final evidence retained: "
            f"{post_commit_verification_failures}"
        ) from error
    ledger_stage.path = paths.ledger
    return ledger_stage, expected_claim_sha256, cleanup_receipt


def _safe_publish_pair(
    paths: V11ArtifactPaths, json_bytes: bytes, markdown_bytes: bytes
) -> list[str]:
    stages = (
        (paths.report_json_staging, paths.report_json, json_bytes),
        (paths.report_markdown_staging, paths.report_markdown, markdown_bytes),
    )
    stage_leases: dict[Path, _OwnedArtifactLease] = {}
    linked: list[tuple[Path, _OwnedArtifactLease]] = []
    try:
        for staging, _final, payload in stages:
            try:
                stage_leases[staging] = _write_staging(staging, payload)
            except _OwnedStagingWriteError as exc:
                stage_leases[staging] = exc.lease
                raise
        for staging, final, _payload in stages:
            os.link(staging, final)
            linked.append((final, stage_leases[staging]))
            if not _owned_path_matches(final, stage_leases[staging]):
                raise V11DiagnosticError(
                    f"V11 linked final identity or content differs from owned stage: {final.name}"
                )
        _require_owned_artifacts(
            tuple(linked)
            + tuple((staging, stage_leases[staging]) for staging, _, _ in stages),
            phase="after report final links",
        )
        # Stage removal is part of the publication transaction.  The sole
        # commit fsync occurs only after both owned names have been removed,
        # so an immutable final never predates a cleanup outcome it cannot
        # report.
        for staging, _final, _payload in stages:
            _unlink_owned_path(staging, stage_leases[staging])
        _require_owned_artifacts(linked, phase="after report stage cleanup")
        _directory_fsync(paths.report_json.parent)
        _require_owned_artifacts(linked, phase="after report commit fsync")
    except Exception as exc:
        rollback_errors = []
        for final, identity in reversed(linked):
            try:
                _unlink_owned_path(final, identity)
            except (OSError, V11DiagnosticError) as rollback_exc:
                rollback_errors.append(
                    f"{final.name}:{type(rollback_exc).__name__}:{rollback_exc}"
                )
        try:
            _directory_fsync(paths.report_json.parent)
        except OSError as rollback_exc:
            rollback_errors.append(
                f"parent_fsync:{type(rollback_exc).__name__}:{rollback_exc}"
            )
        if rollback_errors:
            raise V11DiagnosticError(
                f"V11 publication rollback_failed; evidence_retained={rollback_errors}"
            ) from exc
        raise V11DiagnosticError("V11 partial publication retained in staging") from exc
    finally:
        for lease in stage_leases.values():
            lease.close()
    return []


def _safe_publish_bundle(path: Path, payload: Mapping[str, Any]) -> list[str]:
    staging = path.with_name(f".{path.name}.staging")
    raw = _pretty_json_bytes(payload)
    stage_lease: _OwnedArtifactLease | None = None
    final_created = False
    try:
        try:
            stage_lease = _write_staging(staging, raw)
        except _OwnedStagingWriteError as exc:
            stage_lease = exc.lease
            raise
        os.link(staging, path)
        final_created = True
        if not _owned_path_matches(path, stage_lease):
            raise V11DiagnosticError(
                f"V11 linked bundle identity or content differs from owned stage: {path.name}"
            )
        _require_owned_artifacts(
            ((path, stage_lease), (staging, stage_lease)),
            phase="before bundle stage cleanup",
        )
        _unlink_owned_path(staging, stage_lease)
        _require_owned_artifacts(
            ((path, stage_lease),), phase="after bundle stage cleanup"
        )
        _directory_fsync(path.parent)
        _require_owned_artifacts(
            ((path, stage_lease),), phase="after bundle commit fsync"
        )
    except Exception as exc:
        rollback_errors = []
        if final_created and stage_lease is not None:
            try:
                _unlink_owned_path(path, stage_lease)
            except (OSError, V11DiagnosticError) as rollback_exc:
                rollback_errors.append(
                    f"{path.name}:{type(rollback_exc).__name__}:{rollback_exc}"
                )
        try:
            _directory_fsync(path.parent)
        except OSError as rollback_exc:
            rollback_errors.append(
                f"parent_fsync:{type(rollback_exc).__name__}:{rollback_exc}"
            )
        if rollback_errors:
            raise V11DiagnosticError(
                f"V11 bundle rollback_failed; evidence_retained={rollback_errors}"
            ) from exc
        raise V11DiagnosticError(
            "V11 partial bundle publication retained in staging"
        ) from exc
    finally:
        if stage_lease is not None:
            stage_lease.close()
    return []


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalized_audit(
    callback: Callable[[date, Mapping[str, Any], Sequence[int]], Mapping[str, Any]],
    target: date,
    forecast: Mapping[str, Any],
    actual: tuple[int, ...],
    *,
    claim_evidence: Mapping[str, Any],
) -> dict[str, Any]:
    callback_error = None
    try:
        raw = callback(target, forecast, actual)
    except Exception as exc:  # noqa: BLE001 - audit callbacks are external
        raw = {}
        callback_error = {"error_type": type(exc).__name__, "error_message": str(exc)}
    checks_by_name = {}
    if isinstance(raw, Mapping) and isinstance(raw.get("checks"), list):
        for check in raw["checks"]:
            if isinstance(check, Mapping) and isinstance(check.get("name"), str):
                checks_by_name[check["name"]] = check
    checks_by_name["claim"] = {
        "name": "claim",
        "passed": all(
            claim_evidence.get(key) is True
            for key in (
                "claim_sha256_matches",
                "claimed_genesis_matches",
                "claim_precedes_first_prediction",
                "ledger_contains_current_prediction",
            )
        ),
        "evidence": dict(claim_evidence),
    }
    checks = []
    errors = []
    for name in REQUIRED_6OF6_AUDIT_CHECKS:
        check = checks_by_name.get(name, {})
        evidence = check.get("evidence") if isinstance(check, Mapping) else None
        passed = (
            isinstance(check, Mapping)
            and check.get("passed") is True
            and evidence not in (None, "", [], {})
        )
        if not passed:
            errors.append(f"missing_or_failed:{name}")
        checks.append({"name": name, "passed": passed, "evidence": evidence})
    clear = (
        callback_error is None
        and not errors
        and all(check["passed"] for check in checks)
    )
    return {
        "clear": clear,
        "declared_clear_ignored": raw.get("clear")
        if isinstance(raw, Mapping)
        else None,
        "required_check_names": list(REQUIRED_6OF6_AUDIT_CHECKS),
        "checks": checks,
        "schema_errors": errors,
        "callback_error": callback_error,
    }


def _notification_payload(
    subject: str, body: str, context: Mapping[str, Any]
) -> dict[str, Any]:
    request = {"subject": subject, "body": body, "context": dict(context)}
    key = canonical_sha256(request)
    return {
        "notification_required": True,
        "notification_status": "pending_external_receipt",
        "notification_subject": subject,
        "notification_body": body,
        "notification_idempotency_key": key,
        "notification_request": request,
        "notification_pending_warning": f"notification_pending:{key}",
    }


def _build_exact6_bundle(
    *,
    clear: bool,
    target_date: str,
    exact: Mapping[str, Any],
    forecast_payload: Mapping[str, Any],
    forecast_sha256: str,
    actual: tuple[int, ...],
    opportunity: Mapping[str, Any],
    evaluation_by_model: Mapping[str, Mapping[str, Any]],
    results: Mapping[str, Sequence[Mapping[str, Any]]],
    bootstrap_replicates: int,
    bootstrap_seed: int,
    audit: Mapping[str, Any],
    preflight: Mapping[str, Any],
    implementation_commit: str,
    exact_command: str,
    claim_path: str,
    claim_sha256: str,
    ledger_head_before_bundle: str,
    scored_targets: int,
) -> dict[str, Any]:
    forecasts = forecast_payload["forecasts"]
    primary_raw_model = next(
        name
        for name in MODEL_ORDER
        if OPPORTUNITY_MODEL_NAMES[name] == exact["primary_producer_model_name"]
    )
    primary_forecast = forecasts[primary_raw_model]
    scored_prefix_benchmark = {
        name: summarize_v11_scope(
            results[name],
            scope=f"scored_prefix_{scored_targets}",
            bootstrap_replicates=bootstrap_replicates,
            bootstrap_seed=bootstrap_seed,
        )
        for name in MODEL_ORDER
    }
    return {
        "schema_version": 1,
        "status": "historical-6of6-candidate" if clear else "Archive",
        "experiment_id": EXPERIMENT_ID,
        "model_version": MODEL_VERSION,
        "primary_producer_model_version": primary_forecast["model_version"],
        "primary_producer_feature_set": primary_forecast["feature_set"],
        "primary_producer_parameters": {
            key: primary_forecast[key]
            for key in (
                "anchor",
                "transition_count",
                "D",
                "beta",
                "q_b",
                "r_b",
                "seed",
            )
            if key in primary_forecast
        },
        "target_date": target_date,
        "primary_producer_model_name": exact["primary_producer_model_name"],
        "producer_model_names": exact["producer_model_names"],
        "producer_forecast_sha256_by_model": exact["producer_forecast_sha256_by_model"],
        "forecast_payload": forecast_payload,
        "forecast_sha256": forecast_sha256,
        "prediction": exact["final6"],
        "actual": list(actual),
        "training_cutoff": forecast_payload["prefix"]["history_through"],
        "opportunity": opportunity,
        "evaluation_by_model": evaluation_by_model,
        "scored_prefix_benchmark": scored_prefix_benchmark,
        "registration_commit": REGISTRATION_COMMIT,
        "implementation_commit": implementation_commit,
        "source_commit": preflight.get("data", {}).get("source_commit"),
        "runtime": preflight.get("runtime"),
        "exact_command": exact_command,
        "claim": {"path": claim_path, "sha256": claim_sha256},
        "ledger_head_before_bundle": ledger_head_before_bundle,
        "leakage_audit": audit,
        "scored_targets_before_stop": scored_targets,
        "normal_621_report": "prohibited_after_early_stop",
        "oos_reason": "strict_prefix_forecast_fsynced_before_opaque_reveal",
        "control_producer_never_supports_v11_mechanism_or_activation": True,
        "historical_6of6_does_not_rescue_scientific_gates": True,
    }


def _exact6_notification(
    bundle: Mapping[str, Any],
    *,
    terminal_type: str,
    bundle_sha256: str,
) -> dict[str, Any]:
    clear = bundle["status"] == "historical-6of6-candidate"
    subject = (
        "🚨 [LOTTO649] 历史严格回测成功预测 6/6"
        if clear
        else "⚠️ [LOTTO649] 历史 6/6 候选泄漏审计失败"
    )
    audit = bundle["leakage_audit"]
    body = (
        f"目标日期: {bundle['target_date']}\n"
        f"预测: {bundle['prediction']}\n实际: {bundle['actual']}\n"
        f"首个生产者: {bundle['primary_producer_model_name']}\n"
        f"生产者模型版本: {bundle['primary_producer_model_version']}\n"
        f"实验版本: {MODEL_VERSION}\n"
        f"全部生产者及哈希: {bundle['producer_forecast_sha256_by_model']}\n"
        f"训练截止: {bundle['training_cutoff']}\n"
        f"泄漏审计通过: {clear}; "
        f"检查: {[(item['name'], item['passed']) for item in audit['checks']]}\n"
        f"实现提交: {bundle['implementation_commit']}\n"
        f"累计机会: {bundle['opportunity']['cumulative_unique_opportunities']}\n"
        f"家族公平概率: "
        f"{bundle['opportunity']['cumulative_familywise_fair_probability']}\n"
        f"截至停止点四模型TopK/proper/Final6评分: "
        f"{bundle['evaluation_by_model']}\n"
        f"截至停止点完整四模型benchmark: "
        f"{bundle['scored_prefix_benchmark']}\n"
        "OOS理由: 预测在不透明揭示前已持久化。"
    )
    return _notification_payload(
        subject,
        body,
        {
            "event_type": terminal_type,
            "target_date": bundle["target_date"],
            "bundle_sha256": bundle_sha256,
        },
    )


def _exact6_terminal_payload(
    bundle: Mapping[str, Any],
    *,
    terminal_type: str,
    bundle_path: str,
    bundle_sha256: str,
    operational_warnings: Sequence[str],
) -> dict[str, Any]:
    notification = _exact6_notification(
        bundle,
        terminal_type=terminal_type,
        bundle_sha256=bundle_sha256,
    )
    return {
        "target_date": bundle["target_date"],
        "bundle_path": bundle_path,
        "bundle_sha256": bundle_sha256,
        "scored_targets": bundle["scored_targets_before_stop"],
        "stop_global_search": bundle["status"] == "historical-6of6-candidate",
        "operational_warnings": [
            *operational_warnings,
            notification["notification_pending_warning"],
        ],
        **notification,
    }


def _normal_terminal_payload(
    report: Mapping[str, Any],
    *,
    json_path: str,
    json_sha256: str,
    markdown_path: str,
    markdown_sha256: str,
    scored_targets: int,
    implementation_commit: str,
    operational_warnings: Sequence[str],
) -> dict[str, Any]:
    decision = report["historical_decision"]
    passed = decision["all_scientific_gates_passed"] is True
    terminal: dict[str, Any] = {
        "decision": decision["decision"],
        "all_scientific_gates_passed": passed,
        "gates": decision["gates"],
        "json_path": json_path,
        "json_sha256": json_sha256,
        "markdown_path": markdown_path,
        "markdown_sha256": markdown_sha256,
        "scored_targets": scored_targets,
        "operational_warnings": list(operational_warnings),
    }
    if not passed:
        terminal.update(_notification_not_required())
        return terminal
    notification = _notification_payload(
        "[LOTTO649] 【历史严格回测】V11全部统计门槛通过",
        "V11 十项冻结门槛全部通过；仍未激活，需另行审核。",
        {
            "event_type": "published",
            "json_sha256": json_sha256,
            "markdown_sha256": markdown_sha256,
            "implementation_commit": implementation_commit,
            "experiment_id": EXPERIMENT_ID,
        },
    )
    terminal.update(notification)
    terminal["operational_warnings"] = [
        *operational_warnings,
        notification["notification_pending_warning"],
    ]
    return terminal


def _notification_not_required() -> dict[str, Any]:
    return {
        "notification_required": False,
        "notification_status": "not_required",
        "notification_subject": None,
        "notification_body": None,
        "notification_idempotency_key": None,
        "notification_request": None,
        "notification_pending_warning": None,
    }


def _dispatch_notification(
    notifier: Notifier, notification: Mapping[str, Any]
) -> dict[str, Any]:
    key = notification["notification_idempotency_key"]
    try:
        sent = notifier(
            str(notification["notification_subject"]),
            str(notification["notification_body"]),
        )
    except Exception as exc:  # noqa: BLE001 - notification adapters are external
        return {
            "notification_idempotency_key": key,
            "outcome": "exception",
            "dispatch_accepted": False,
            "exception_type": type(exc).__name__,
            "operational_warning": f"notification_exception:{type(exc).__name__}:{key}",
        }
    if sent is not True:
        return {
            "notification_idempotency_key": key,
            "outcome": "returned_false",
            "dispatch_accepted": False,
            "exception_type": None,
            "operational_warning": f"notification_returned_false:{key}",
        }
    return {
        "notification_idempotency_key": key,
        "outcome": "dispatch_accepted",
        "dispatch_accepted": True,
        "exception_type": None,
        "operational_warning": None,
    }


def _validate_notification_envelope(payload: Mapping[str, Any]) -> None:
    if payload.get("notification_required") is False:
        for key, value in _notification_not_required().items():
            if payload.get(key) != value:
                raise V11DiagnosticError("V11 not-required notification changed")
        return
    request = payload.get("notification_request")
    if not isinstance(request, Mapping) or set(request) != {
        "subject",
        "body",
        "context",
    }:
        raise V11DiagnosticError("V11 notification request schema changed")
    key = canonical_sha256(request)
    if (
        payload.get("notification_required") is not True
        or payload.get("notification_status") != "pending_external_receipt"
        or payload.get("notification_subject") != request["subject"]
        or payload.get("notification_body") != request["body"]
        or payload.get("notification_idempotency_key") != key
        or payload.get("notification_pending_warning") != f"notification_pending:{key}"
    ):
        raise V11DiagnosticError("V11 notification envelope is not reproducible")


def _validate_notification_receipt(
    receipt: Mapping[str, Any], *, idempotency_key: str
) -> str | None:
    if receipt.get("notification_idempotency_key") != idempotency_key:
        raise V11DiagnosticError("V11 notification receipt key changed")
    outcome = receipt.get("outcome")
    exception_type = receipt.get("exception_type")
    if outcome == "dispatch_accepted":
        expected = {
            "notification_idempotency_key": idempotency_key,
            "outcome": outcome,
            "dispatch_accepted": True,
            "exception_type": None,
            "operational_warning": None,
        }
    elif outcome == "returned_false":
        expected = {
            "notification_idempotency_key": idempotency_key,
            "outcome": outcome,
            "dispatch_accepted": False,
            "exception_type": None,
            "operational_warning": f"notification_returned_false:{idempotency_key}",
        }
    elif outcome == "exception" and isinstance(exception_type, str) and exception_type:
        expected = {
            "notification_idempotency_key": idempotency_key,
            "outcome": outcome,
            "dispatch_accepted": False,
            "exception_type": exception_type,
            "operational_warning": (
                f"notification_exception:{exception_type}:{idempotency_key}"
            ),
        }
    else:
        raise V11DiagnosticError("V11 notification receipt outcome changed")
    _same_payload(receipt, expected, "V11 notification receipt was forged")
    return expected["operational_warning"]


def _validate_terminal_notification_suffix(
    events: Sequence[Mapping[str, Any]],
    *,
    terminal_index: int,
    require_receipt: bool,
) -> None:
    terminal_event = events[terminal_index]
    terminal = terminal_event["payload"]
    receipt_index = terminal_index + 1
    if terminal.get("notification_required") is False:
        if receipt_index != len(events):
            raise V11DiagnosticError(
                "V11 not-required terminal has post-terminal events"
            )
        return
    if receipt_index == len(events):
        if require_receipt:
            raise V11DiagnosticError("V11 terminal notification receipt is missing")
        return
    if (
        receipt_index + 1 != len(events)
        or events[receipt_index]["event_type"] != "terminal_notification_receipt"
    ):
        raise V11DiagnosticError("V11 terminal notification receipt order changed")
    payload = events[receipt_index]["payload"]
    if not isinstance(payload, Mapping) or set(payload) != {
        "scientific_terminal_event_sha256",
        "receipt",
    }:
        raise V11DiagnosticError("V11 terminal notification receipt schema changed")
    if payload["scientific_terminal_event_sha256"] != terminal_event.get(
        "event_sha256"
    ):
        raise V11DiagnosticError("V11 terminal notification receipt binding changed")
    receipt = payload["receipt"]
    if not isinstance(receipt, Mapping):
        raise V11DiagnosticError("V11 terminal notification receipt is invalid")
    _validate_notification_receipt(
        receipt,
        idempotency_key=str(terminal["notification_idempotency_key"]),
    )


def _progress_notification_requests(
    *,
    target_date: date,
    forecasts: Mapping[str, Mapping[str, Any]],
    scores: Mapping[str, Mapping[str, Any]],
    record: Mapping[str, Any],
) -> list[dict[str, Any]]:
    requests: list[dict[str, Any]] = []
    top12_models = [
        name for name in MODEL_ORDER if int(scores[name]["top12_hits"]) == 6
    ]
    specs: list[tuple[str, str, list[str]]] = []
    if top12_models:
        specs.append(
            (
                "top12_6of6_not_final6",
                "[LOTTO649] 【历史严格回测】V11 Top-12 命中 6/6（不是 Final-6 成功）",
                top12_models,
            )
        )
    if (
        record.get("new_within_run_record") is True
        and int(record["current_final6_hits"]) >= 3
    ):
        specs.append(
            (
                "new_final6_record",
                "[LOTTO649] 【历史严格回测】V11 Final-6 运行内里程碑",
                [CANDIDATE_MODEL],
            )
        )
    for kind, subject, affected_models in specs:
        model_lines = "\n".join(
            f"{name}: Top-12={scores[name]['top12_hits']}/6; "
            f"Final-6={scores[name]['final6_hits']}/6; "
            f"Top-12集合={forecasts[name]['top12']}"
            for name in affected_models
        )
        body = (
            f"目标日期: {target_date.isoformat()}\n"
            f"模型: {affected_models}\n"
            f"{model_lines}\n"
            "记录口径: 仅 V11 本次严格历史运行（run-local），不是跨版本全局纪录；"
            "global maximum unknown；legacy reported floor >=4/6；"
            "verified full-snapshot max=3/6。\n"
            "Top-12仅为coverage，不是Final-6成功；该通知不构成可预测性证据。"
        )
        requests.append(
            {
                "kind": kind,
                "model_names": affected_models,
                "subject": subject,
                "body": body,
            }
        )
    return requests


def _render_markdown(report: Mapping[str, Any]) -> str:
    decision = report["historical_decision"]
    lines = [
        "# V11 previous-bonus carryover historical diagnostic",
        "",
        "This is a consumed historical diagnostic, not blind confirmation. The model remains `not_activated`.",
        "",
        "## Identity and scope",
        "",
        f"- Experiment: `{report['experiment_id']}` / `{report['model_version']}`",
        f"- Registration commit: `{report['registration_commit']}`",
        f"- Implementation commit: `{report['implementation_commit']}`",
        f"- Claim SHA-256: `{report['claim_sha256']}`",
        f"- Ledger head before publication: `{report['ledger_head_before_publication']}`",
        f"- Registered data/source: `{json.dumps(report['preflight'].get('data', {}), sort_keys=True)}`",
        f"- Frozen research configuration: `{json.dumps(report['preflight'].get('configuration', {}), sort_keys=True)}`",
        f"- Frozen runtime/lock: `{json.dumps(report['preflight'].get('runtime', {}), sort_keys=True)}`",
        f"- Targets: `{report['historical_lane']['target_start']}` through `{report['historical_lane']['target_end']}` ({report['historical_lane']['target_count']})",
        f"- Decision: `{decision['decision']}`",
        "",
        "## Frozen feature sets",
        "",
    ]
    first_forecasts = report["per_target"][0]["forecast_payload"]["forecasts"]
    for model in MODEL_ORDER:
        lines.append(f"- `{model}`: `{first_forecasts[model]['feature_set']}`")
    lines.extend(
        [
            "",
            "## Scope summaries",
            "",
            "| Model | Scope | Draws | Top-6 | Top-12 | Top-18 | Brier | Log loss | Final-6 histogram |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    for model in MODEL_ORDER:
        for scope, summary in report["summaries"][model].items():
            histogram = json.dumps(summary["final6_hit_histogram"], sort_keys=True)
            lines.append(
                f"| {model} | {scope} | {summary['draws']} | {summary['avg_top6_hits']:.12g} | "
                f"{summary['avg_top12_hits']:.12g} | {summary['avg_top18_hits']:.12g} | "
                f"{summary['avg_brier']:.12g} | {summary['avg_log_loss']:.12g} | `{histogram}` |"
            )
    candidate = report["summaries"][CANDIDATE_MODEL]
    aggregate = next(iter(candidate.values()))
    lines.extend(
        [
            "",
            "## Primary, paired, mechanism, calibration, and yearly evidence",
            "",
            f"- Candidate raw exact p: `{aggregate['primary_exact_one_sided_p']}`; Holm adjusted p: `{aggregate.get('primary_holm_adjusted_p')}`; bootstrap CI: `{aggregate['primary_bootstrap_95_ci']}`",
            f"- Paired candidate minus V1: `{json.dumps(report['paired_candidate_minus_v1'], sort_keys=True)}`",
            f"- Paired candidate minus control: `{json.dumps(report['paired_candidate_minus_control'], sort_keys=True)}`",
            f"- Anchor mechanism: `{json.dumps(report['mechanism'], sort_keys=True)}`",
            f"- Candidate calibration: `{json.dumps(aggregate['calibration'], sort_keys=True)}`",
            f"- Candidate performance by year: `{json.dumps(aggregate['performance_by_year'], sort_keys=True)}`",
            "",
            "## Frozen ten-gate decision",
            "",
        ]
    )
    for number, name in enumerate(SCIENTIFIC_GATE_NAMES, start=1):
        lines.append(f"{number}. `{name}`: `{str(decision['gates'][name]).lower()}`")
    lines.extend(
        [
            "",
            f"All ten gates passed: `{str(decision['all_scientific_gates_passed']).lower()}`.",
            "",
            "## Warnings and audit trail",
            "",
            f"- Scientific/audit warnings: `{json.dumps(report['scientific_audit_warnings'], sort_keys=True)}`",
            f"- Operational warnings: `{json.dumps(report['operational_warnings'], sort_keys=True)}`",
            f"- Opportunity total (deduplicated Final-6 sets): `{report['opportunity_total']}`",
            "- Full per-target probabilities, rankings, Top-K sets, Final-6 sets, scores, calibration inputs, and chronology evidence are retained in the JSON report and hash-chain ledger.",
            "",
        ]
    )
    return "\n".join(lines)


def _claim_for_ledger(path: Path) -> tuple[dict[str, Any], str]:
    suffix = ".ledger.jsonl"
    if not path.name.endswith(suffix):
        raise V11DiagnosticError("V11 ledger path identity changed")
    claim_path = path.with_name(path.name[: -len(suffix)] + ".claim")
    try:
        raw = claim_path.read_bytes()
    except OSError as exc:
        raise V11DiagnosticError("V11 durable claim is missing") from exc
    if not raw.endswith(b"\n") or raw.count(b"\n") != 1:
        raise V11DiagnosticError("V11 claim framing is invalid")
    try:
        claim = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise V11DiagnosticError("V11 claim is invalid JSON") from exc
    if not isinstance(claim, dict) or _canonical_json_bytes(claim) + b"\n" != raw:
        raise V11DiagnosticError("V11 claim is not canonical JSON")
    required = {
        "schema_version",
        "experiment_id",
        "model_version",
        "seed",
        "registration_commit",
        "implementation_commit",
        "exact_command",
        "exact_command_sha256",
        "started_at_utc",
        "preflight",
        "analysis_plan",
        "analysis_plan_sha256",
        "status",
    }
    if set(claim) != required:
        raise V11DiagnosticError("V11 claim schema changed")
    if (
        claim["schema_version"] != 1
        or claim["experiment_id"] != EXPERIMENT_ID
        or claim["model_version"] != MODEL_VERSION
        or claim["seed"] != 649
        or claim["registration_commit"] != REGISTRATION_COMMIT
        or claim["status"] != "consumed_permanently_no_rerun"
        or not isinstance(claim["exact_command"], str)
        or not claim["exact_command"]
        or claim["exact_command_sha256"]
        != sha256(claim["exact_command"].encode("utf-8")).hexdigest()
        or not isinstance(claim["analysis_plan"], Mapping)
        or claim["analysis_plan_sha256"] != canonical_sha256(claim["analysis_plan"])
    ):
        raise V11DiagnosticError("V11 claim frozen identity changed")
    implementation = claim["implementation_commit"]
    if (
        not isinstance(implementation, str)
        or len(implementation) != 40
        or any(character not in "0123456789abcdef" for character in implementation)
    ):
        raise V11DiagnosticError("V11 claim implementation commit is invalid")
    return claim, sha256(raw).hexdigest()


def _same_payload(actual: Any, expected: Any, message: str) -> None:
    if not isinstance(actual, Mapping) or not isinstance(expected, Mapping):
        raise V11DiagnosticError(message)
    if _canonical_json_bytes(actual) != _canonical_json_bytes(expected):
        raise V11DiagnosticError(message)


def _is_lower_hex(value: Any, length: int) -> bool:
    return (
        isinstance(value, str)
        and len(value) == length
        and all(character in "0123456789abcdef" for character in value)
    )


def _validate_preflight_evidence(
    preflight: Mapping[str, Any],
    *,
    implementation_commit: str,
    expected_targets: int,
    registered_identity: V11RegisteredIdentity,
) -> None:
    if (
        expected_targets != registered_identity.analysis_target_count
        or len(registered_identity.analysis_scopes) != 3
    ):
        raise V11DiagnosticError("V11 registered analysis authority changed")
    required = {
        "passed",
        "audit_warnings",
        "registration_commit",
        "implementation_commit",
        "git",
        "configuration",
        "data",
        "runtime",
        "invocation",
        "references",
    }
    if set(preflight) != required:
        raise V11DiagnosticError("V11 preflight evidence schema is incomplete")
    git = preflight["git"]
    configuration = preflight["configuration"]
    data = preflight["data"]
    runtime = preflight["runtime"]
    if not all(
        isinstance(value, Mapping)
        for value in (
            git,
            configuration,
            data,
            runtime,
            preflight["invocation"],
            preflight["references"],
        )
    ):
        raise V11DiagnosticError("V11 preflight evidence sections are invalid")
    if (
        set(git)
        != {
            "branch",
            "exact_head",
            "remote_branch_head",
            "registration_ancestor",
            "changed_paths",
            "status_documentation",
            "ci",
        }
        or set(configuration)
        != {
            "path",
            "sha256",
            "registry_parameters_equal",
            "registry_status",
            "v1_base_source_commit",
            "v1_base_config_path",
            "v1_base_config_sha256",
            "v1_base_file_sha256",
        }
        or set(data)
        != {
            "path",
            "sha256",
            "draw_count",
            "history_through",
            "source_commit",
            "source_commit_ancestor_of_registration",
            "source_commit_ancestor_of_implementation",
            "source_git_blob",
            "target_count",
            "fixed_half_counts",
        }
        or set(runtime)
        != {
            "implementation",
            "python_version",
            "platform",
            "executable",
            "requirements_lock_path",
            "requirements_lock_sha256",
            "locked_distributions_verified",
            "distributions",
            "lock_sha256",
        }
        or preflight["references"] != {}
    ):
        raise V11DiagnosticError("V11 preflight section schema changed")
    if (
        preflight["passed"] is not True
        or preflight["audit_warnings"] != []
        or preflight["registration_commit"] != REGISTRATION_COMMIT
        or preflight["implementation_commit"] != implementation_commit
        or git.get("exact_head") != implementation_commit
        or git.get("remote_branch_head") != implementation_commit
        or git.get("registration_ancestor") is not True
        or not isinstance(git.get("branch"), str)
        or not git.get("branch")
        or git.get("changed_paths") != sorted(REQUIRED_IMPLEMENTATION_PATHS)
        or not isinstance(git.get("status_documentation"), Mapping)
    ):
        raise V11DiagnosticError("V11 Git/preflight changed paths or identity changed")
    status_documentation = git["status_documentation"]
    if set(status_documentation) != REQUIRED_STATUS_DOCUMENTATION_PATHS:
        raise V11DiagnosticError("V11 status documentation evidence set changed")
    for path_name, replacement_count in STATUS_REPLACEMENT_COUNTS.items():
        document = status_documentation[path_name]
        if (
            not isinstance(document, Mapping)
            or set(document)
            != {
                "path",
                "exact_status_replacements_only",
                "registration_sha256",
                "current_sha256",
                "replacement_count",
            }
            or document.get("path") != path_name
            or document.get("exact_status_replacements_only") is not True
            or not _is_lower_hex(document.get("registration_sha256"), 64)
            or not _is_lower_hex(document.get("current_sha256"), 64)
            or document.get("replacement_count") != replacement_count
        ):
            raise V11DiagnosticError("V11 status documentation evidence changed")
    ci = git.get("ci")
    if not isinstance(ci, Mapping) or set(ci) != {"registration", "implementation"}:
        raise V11DiagnosticError("V11 dual-commit CI evidence is incomplete")
    for commit_name in ("registration", "implementation"):
        item = ci[commit_name]
        if not isinstance(item, Mapping):
            raise V11DiagnosticError("V11 CI evidence is invalid")
        required_checks = item.get("required")
        successful = item.get("successful")
        if required_checks != REQUIRED_CI_CHECKS or successful != required_checks:
            raise V11DiagnosticError("V11 CI evidence is not uniformly green")
    if (
        configuration.get("path") != registered_identity.research_config_path
        or configuration.get("sha256") != registered_identity.research_config_sha256
        or configuration.get("registry_parameters_equal") is not True
        or configuration.get("registry_status") != "registered"
        or configuration.get("v1_base_source_commit")
        != registered_identity.v1_base_source_commit
        or configuration.get("v1_base_config_path")
        != registered_identity.v1_base_config_path
        or configuration.get("v1_base_config_sha256")
        != registered_identity.v1_base_config_sha256
        or configuration.get("v1_base_file_sha256")
        != [
            {"path": path, "sha256": digest}
            for path, digest in registered_identity.v1_base_file_sha256
        ]
    ):
        raise V11DiagnosticError("V11 configuration preflight evidence changed")
    source_git_blob = data.get("source_git_blob")
    fixed_halves = data.get("fixed_half_counts")
    if (
        data.get("path") != registered_identity.data_path
        or data.get("sha256") != registered_identity.data_sha256
        or data.get("draw_count") != registered_identity.data_draw_count
        or data.get("history_through") != registered_identity.data_history_through
        or data.get("source_commit") != registered_identity.data_source_commit
        or data.get("source_commit_ancestor_of_registration") is not True
        or data.get("source_commit_ancestor_of_implementation") is not True
        or data.get("target_count") != expected_targets
        or fixed_halves
        != [
            registered_identity.analysis_scopes[1][3],
            registered_identity.analysis_scopes[2][3],
        ]
        or not isinstance(source_git_blob, Mapping)
        or set(source_git_blob) != {"git_blob_byte_identical", "sha256", "byte_count"}
        or source_git_blob.get("git_blob_byte_identical") is not True
        or source_git_blob.get("sha256") != data.get("sha256")
        or type(source_git_blob.get("byte_count")) is not int
        or source_git_blob["byte_count"] < 1
    ):
        raise V11DiagnosticError("V11 registered data/source identity changed")
    if (
        runtime.get("implementation") != "CPython"
        or not isinstance(runtime.get("python_version"), str)
        or not runtime["python_version"].startswith("3.12.")
        or not isinstance(runtime.get("platform"), str)
        or not runtime["platform"]
        or not isinstance(runtime.get("executable"), str)
        or not runtime["executable"]
        or runtime.get("requirements_lock_path")
        != registered_identity.runtime_lock_path
        or runtime.get("requirements_lock_sha256")
        != registered_identity.runtime_lock_sha256
        or runtime.get("lock_sha256") != registered_identity.runtime_lock_sha256
        or not isinstance(runtime.get("locked_distributions_verified"), Mapping)
        or not isinstance(runtime.get("distributions"), list)
    ):
        raise V11DiagnosticError("V11 runtime preflight evidence changed")
    _validate_invocation_evidence(
        preflight["invocation"], runtime=runtime, identity=registered_identity
    )


@dataclass(frozen=True)
class _LedgerHead:
    head_sha256: str


@dataclass(frozen=True)
class _RegisteredSourceDateRow:
    draw_date: date
    raw: bytes


@dataclass(frozen=True)
class _RegisteredSourceRow:
    draw_date: date
    main: tuple[int, ...]
    bonus: int
    raw: bytes


def _registered_analysis_plan(
    rows: Sequence[_RegisteredSourceDateRow | _RegisteredSourceRow],
    identity: V11RegisteredIdentity,
) -> dict[str, Any]:
    try:
        target_start = date.fromisoformat(identity.analysis_target_start)
        target_end = date.fromisoformat(identity.analysis_target_end)
        reference = json.loads(identity.analysis_reference_json)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise V11DiagnosticError("V11 registered analysis plan is invalid") from exc
    target_date_values = [
        row.draw_date for row in rows if target_start <= row.draw_date <= target_end
    ]
    target_dates = [target.isoformat() for target in target_date_values]
    scopes = [
        {"name": name, "start": start, "end": end, "target_count": count}
        for name, start, end, count in identity.analysis_scopes
    ]
    scope_actual_counts: list[int] = []
    try:
        for scope in scopes:
            scope_start = date.fromisoformat(scope["start"])
            scope_end = date.fromisoformat(scope["end"])
            scope_actual_counts.append(
                sum(scope_start <= target <= scope_end for target in target_date_values)
            )
    except (TypeError, ValueError) as exc:
        raise V11DiagnosticError("V11 registered analysis plan is invalid") from exc
    if (
        not target_dates
        or len(target_dates) != identity.analysis_target_count
        or target_dates[0] != identity.analysis_target_start
        or target_dates[-1] != identity.analysis_target_end
        or len(scopes) != 3
        or scopes[0]
        != {
            "name": identity.analysis_scopes[0][0],
            "start": identity.analysis_target_start,
            "end": identity.analysis_target_end,
            "target_count": identity.analysis_target_count,
        }
        or sum(item["target_count"] for item in scopes[1:])
        != identity.analysis_target_count
        or scope_actual_counts
        != [
            identity.analysis_target_count,
            *[item["target_count"] for item in scopes[1:]],
        ]
        or not isinstance(reference, dict)
        or _canonical_json_bytes(reference).decode("utf-8")
        != identity.analysis_reference_json
        or identity.analysis_bootstrap_replicates < 1
        or identity.analysis_bootstrap_seed != 649
    ):
        raise V11DiagnosticError("V11 registered analysis plan is invalid")
    return {
        "target_dates": target_dates,
        "expected_target_count": identity.analysis_target_count,
        "scopes": scopes,
        "bootstrap_replicates": identity.analysis_bootstrap_replicates,
        "bootstrap_seed": identity.analysis_bootstrap_seed,
        "reference": reference,
        "exact_command": registered_v11_command(identity),
    }


def _request_analysis_plan(
    request: V11DiagnosticRequest,
    dates: Sequence[date],
) -> dict[str, Any]:
    aggregate = {
        "name": request.registered_identity.analysis_scopes[0][0],
        "start": dates[0].isoformat(),
        "end": dates[-1].isoformat(),
        "target_count": len(dates),
    }
    return {
        "target_dates": [target.isoformat() for target in dates],
        "expected_target_count": request.expected_target_count,
        "scopes": [
            aggregate,
            *[
                {
                    "name": scope.name,
                    "start": scope.start.isoformat(),
                    "end": scope.end.isoformat(),
                    "target_count": scope.target_count,
                }
                for scope in request.stability_scopes
            ],
        ],
        "bootstrap_replicates": request.bootstrap_replicates,
        "bootstrap_seed": request.bootstrap_seed,
        "reference": dict(request.reference),
        "exact_command": request.exact_command,
    }


def _validate_request_analysis_plan(
    request: V11DiagnosticRequest,
    dates: Sequence[date],
    trusted_rows: Sequence[_RegisteredSourceDateRow | _RegisteredSourceRow],
) -> dict[str, Any]:
    expected = _registered_analysis_plan(trusted_rows, request.registered_identity)
    candidate = _request_analysis_plan(request, dates)
    if _canonical_json_bytes(candidate) != _canonical_json_bytes(expected):
        raise V11DiagnosticError("V11 request differs from registered analysis plan")
    _validate_registered_command(
        request.exact_command,
        identity=request.registered_identity,
    )
    return expected


def _resolve_trusted_source_blob(
    claim: Mapping[str, Any],
    resolver: SourceBlobResolver,
    registered_identity: V11RegisteredIdentity,
) -> bytes:
    preflight = claim.get("preflight")
    data = preflight.get("data") if isinstance(preflight, Mapping) else None
    if not isinstance(data, Mapping):
        raise V11DiagnosticError("trusted registered source evidence is missing")
    source_commit = data.get("source_commit")
    source_path = data.get("path")
    expected_sha256 = data.get("sha256")
    if (
        source_commit != registered_identity.data_source_commit
        or source_path != registered_identity.data_path
        or expected_sha256 != registered_identity.data_sha256
    ):
        raise V11DiagnosticError("trusted registered source identity changed")
    try:
        blob = resolver(source_commit, source_path)
    except Exception as exc:
        raise V11DiagnosticError("trusted registered source resolver failed") from exc
    source_git_blob = data.get("source_git_blob")
    if (
        not isinstance(blob, bytes)
        or sha256(blob).hexdigest() != expected_sha256
        or not isinstance(source_git_blob, Mapping)
        or source_git_blob.get("byte_count") != len(blob)
    ):
        raise V11DiagnosticError("trusted registered source Git blob hash changed")
    return blob


def _registered_source_date_rows(
    blob: bytes,
    registered_identity: V11RegisteredIdentity,
) -> tuple[_RegisteredSourceDateRow, ...]:
    lines = blob.splitlines(keepends=True)
    header = b"draw_date,n1,n2,n3,n4,n5,n6,bonus\n"
    if (
        not lines
        or lines[0] != header
        or any(not line.endswith(b"\n") for line in lines)
    ):
        raise V11DiagnosticError("trusted registered source CSV framing changed")
    rows: list[_RegisteredSourceDateRow] = []
    for raw in lines[1:]:
        try:
            raw_date, separator, opaque_outcome = raw.partition(b",")
            if (
                separator != b","
                or not opaque_outcome
                or raw.count(b",") != 7
                or b"\r" in raw
            ):
                raise ValueError("field count")
            row_date = date.fromisoformat(raw_date.decode("ascii"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise V11DiagnosticError(
                "trusted registered source date row is invalid"
            ) from exc
        rows.append(_RegisteredSourceDateRow(row_date, raw))
    ordered = tuple(row.draw_date for row in rows)
    if ordered != tuple(sorted(ordered)) or len(set(ordered)) != len(ordered):
        raise V11DiagnosticError("trusted registered source chronology changed")
    if (
        registered_identity.data_draw_count != len(rows)
        or (rows[-1].draw_date.isoformat() if rows else None)
        != registered_identity.data_history_through
    ):
        raise V11DiagnosticError("trusted registered source bounds changed")
    return tuple(rows)


def _decode_registered_source_row(
    date_row: _RegisteredSourceDateRow,
) -> _RegisteredSourceRow:
    try:
        values = next(csv.reader([date_row.raw.decode("utf-8").rstrip("\n")]))
        if len(values) != 8 or date.fromisoformat(values[0]) != date_row.draw_date:
            raise ValueError("field count")
        main = _actual_main(tuple(int(value) for value in values[1:7]))
        bonus = int(values[7])
        if not 1 <= bonus <= 49 or bonus in main:
            raise ValueError("bonus")
    except (UnicodeDecodeError, ValueError, csv.Error, StopIteration) as exc:
        raise V11DiagnosticError("trusted registered source row is invalid") from exc
    return _RegisteredSourceRow(date_row.draw_date, main, bonus, date_row.raw)


def _decode_registered_source_rows(
    blob: bytes,
    registered_identity: V11RegisteredIdentity,
) -> tuple[_RegisteredSourceRow, ...]:
    return tuple(
        _decode_registered_source_row(row)
        for row in _registered_source_date_rows(blob, registered_identity)
    )


def _resolve_trusted_source_dates(
    claim: Mapping[str, Any],
    resolver: SourceBlobResolver,
    registered_identity: V11RegisteredIdentity,
) -> tuple[bytes, tuple[_RegisteredSourceDateRow, ...]]:
    blob = _resolve_trusted_source_blob(claim, resolver, registered_identity)
    return blob, _registered_source_date_rows(blob, registered_identity)


def _validate_failed_terminal_payload(
    payload: Mapping[str, Any],
    *,
    active_frozen: tuple[str, str] | None,
) -> None:
    if (
        not isinstance(payload, Mapping)
        or set(payload)
        != {
            "status",
            "error_type",
            "error_message",
            "last_frozen_target_date",
            "last_frozen_forecast_sha256",
        }
        or payload.get("status") != "consumed_archive_no_rerun"
        or not isinstance(payload.get("error_type"), str)
        or not payload["error_type"]
        or not isinstance(payload.get("error_message"), str)
        or payload.get("last_frozen_target_date")
        != (active_frozen[0] if active_frozen else None)
        or payload.get("last_frozen_forecast_sha256")
        != (active_frozen[1] if active_frozen else None)
    ):
        raise V11DiagnosticError("V11 failed terminal evidence changed")


def _consume_failed_terminal(
    events: Sequence[Mapping[str, Any]],
    index: int,
    *,
    active_frozen: tuple[str, str] | None,
) -> bool:
    if index >= len(events) or events[index].get("event_type") != "failed":
        return False
    _validate_failed_terminal_payload(
        events[index].get("payload"), active_frozen=active_frozen
    )
    if index + 1 != len(events):
        raise V11DiagnosticError("V11 ledger has events after failed terminal")
    return True


def _validate_acquisition_cleanup_receipt(
    receipt: Mapping[str, Any], paths: V11ArtifactPaths
) -> list[str]:
    if set(receipt) != {
        "schema_version",
        "phase",
        "stage_results",
        "parent_fsync",
    } or (
        receipt.get("schema_version") != 1
        or receipt.get("phase") != "post_claim_commit_cleanup"
    ):
        raise V11DiagnosticError("V11 acquisition cleanup schema changed")
    stage_results = receipt.get("stage_results")
    if not isinstance(stage_results, list) or len(stage_results) != 2:
        raise V11DiagnosticError("V11 acquisition stage cleanup evidence changed")
    expected = (
        ("claim", paths.claim_staging, paths.claim),
        ("ledger", paths.ledger_staging, paths.ledger),
    )
    for item, (role, stage, final) in zip(stage_results, expected):
        if not isinstance(item, Mapping) or set(item) != {
            "phase",
            "role",
            "path",
            "outcome",
            "error_type",
            "content_binding",
            "content_sha256",
        }:
            raise V11DiagnosticError("V11 acquisition stage result schema changed")
        if (
            item["phase"] != "stage_unlink"
            or item["role"] != role
            or item["path"] != _artifact_relative_identity(stage, paths.claim.parent)
            or not final.is_file()
        ):
            raise V11DiagnosticError("V11 acquisition artifact identity changed")
        outcome = item["outcome"]
        if outcome == "removed":
            valid = (
                item["error_type"] is None
                and item["content_binding"] is None
                and item["content_sha256"] is None
                and not _directory_entry_exists(stage)
            )
        elif outcome == "unlink_failed":
            valid = (
                item["error_type"] == "OSError"
                and item["content_binding"] == "mutable_final_bytes"
                and item["content_sha256"] is None
                and _directory_entry_exists(stage)
                and stat.S_ISREG(stage.lstat().st_mode)
                and _file_sha256(stage) == _file_sha256(final)
            )
        elif outcome == "foreign_inode_refused":
            try:
                expected_binding, expected_sha256 = _foreign_entry_binding(stage)
            except FileNotFoundError:
                valid = False
            else:
                valid = (
                    item["error_type"] == "V11DiagnosticError"
                    and item["content_binding"] == expected_binding
                    and item["content_sha256"] == expected_sha256
                )
        else:
            valid = False
        if not valid:
            raise V11DiagnosticError("V11 acquisition cleanup outcome was forged")
    parent = receipt.get("parent_fsync")
    if not isinstance(parent, Mapping) or set(parent) != {
        "phase",
        "path",
        "outcome",
        "error_type",
    }:
        raise V11DiagnosticError("V11 acquisition parent fsync schema changed")
    if (
        parent["phase"] != "parent_directory_fsync"
        or parent["path"] != "."
        or (parent["outcome"] == "succeeded" and parent["error_type"] is not None)
        or (parent["outcome"] == "failed" and parent["error_type"] != "OSError")
        or parent["outcome"] not in {"succeeded", "failed"}
    ):
        raise V11DiagnosticError("V11 acquisition parent fsync outcome changed")
    return _acquisition_operational_warnings(receipt)


def _replay_report(
    *,
    claim: Mapping[str, Any],
    preflight: Mapping[str, Any],
    claim_sha256: str,
    results: Mapping[str, Sequence[Mapping[str, Any]]],
    per_target: Sequence[Mapping[str, Any]],
    records: Sequence[Mapping[str, Any]],
    ledger_head: str,
    output_dir: Path,
    operational_warnings: Sequence[str],
    registered_identity: V11RegisteredIdentity,
) -> dict[str, Any]:
    plan = claim["analysis_plan"]
    target_dates = tuple(date.fromisoformat(value) for value in plan["target_dates"])
    scopes = tuple(
        V11Scope(
            item["name"],
            date.fromisoformat(item["start"]),
            date.fromisoformat(item["end"]),
            item["target_count"],
        )
        for item in plan["scopes"][1:]
    )
    request = V11DiagnosticRequest(
        root=output_dir,
        output_dir=output_dir,
        code_commit=claim["implementation_commit"],
        exact_command=claim["exact_command"],
        targets=tuple(V11TargetPlan(value, dict, lambda: ()) for value in target_dates),
        preflight=lambda: preflight,
        reference=plan["reference"],
        expected_target_count=plan["expected_target_count"],
        stability_scopes=scopes,  # type: ignore[arg-type]
        bootstrap_replicates=plan["bootstrap_replicates"],
        bootstrap_seed=plan["bootstrap_seed"],
        registered_identity=registered_identity,
    )
    return _build_report(
        request,
        preflight=preflight,
        claim_sha256=claim_sha256,
        results=results,
        per_target=per_target,
        record_ledger=records,
        ledger=_LedgerHead(ledger_head),  # type: ignore[arg-type]
        operational_warnings=operational_warnings,
    )


def validate_v11_ledger_state_machine(
    path: Path,
    *,
    expected_targets: int,
    require_terminal: bool = True,
    require_terminal_notification_receipt: bool = True,
    source_blob_resolver: SourceBlobResolver | None = None,
    registered_identity: V11RegisteredIdentity = REGISTERED_V11_IDENTITY,
) -> list[dict[str, Any]]:
    """Independently replay every derivable ledger value and final artifact."""

    if source_blob_resolver is None:
        raise V11DiagnosticError("trusted registered source resolver is required")
    events = verify_hash_chain_ledger(path)
    claim, claim_sha256 = _claim_for_ledger(path)
    plan = claim.get("analysis_plan")
    if (
        not isinstance(plan, Mapping)
        or expected_targets != registered_identity.analysis_target_count
    ):
        raise V11DiagnosticError("V11 claim analysis plan is missing")
    if not events or events[0]["event_type"] != "claimed":
        raise V11DiagnosticError("V11 ledger initial state sequence is invalid")
    _same_payload(
        events[0]["payload"],
        {
            "claim_sha256": claim_sha256,
            "implementation_commit": claim["implementation_commit"],
            "started_at_utc": claim["started_at_utc"],
        },
        "V11 claimed genesis does not bind canonical claim",
    )
    claim_started_at = _validated_timestamp(
        claim["started_at_utc"], field_name="claim started_at_utc"
    )
    preflight = claim.get("preflight")
    if (
        not isinstance(preflight, Mapping)
        or preflight.get("passed") is not True
        or preflight.get("audit_warnings")
        or preflight.get("registration_commit") != REGISTRATION_COMMIT
        or preflight.get("implementation_commit") != claim["implementation_commit"]
    ):
        raise V11DiagnosticError("V11 claim preflight binding is invalid")
    _validate_preflight_evidence(
        preflight,
        implementation_commit=claim["implementation_commit"],
        expected_targets=expected_targets,
        registered_identity=registered_identity,
    )
    trusted_blob, trusted_date_rows = _resolve_trusted_source_dates(
        claim, source_blob_resolver, registered_identity
    )
    expected_plan = _registered_analysis_plan(trusted_date_rows, registered_identity)
    _same_payload(
        plan,
        expected_plan,
        "V11 claim differs from registered analysis plan",
    )
    _validate_registered_command(
        claim["exact_command"],
        identity=registered_identity,
    )
    target_dates = expected_plan["target_dates"]
    trusted_index_by_date = {
        row.draw_date: index for index, row in enumerate(trusted_date_rows)
    }
    if len(events) == 2 and events[1]["event_type"] == "failed":
        _validate_failed_terminal_payload(events[1]["payload"], active_frozen=None)
        return events
    if len(events) < 2 or events[1]["event_type"] != "preflight_passed":
        raise V11DiagnosticError("V11 ledger preflight state is missing")
    _same_payload(
        events[1]["payload"], preflight, "V11 preflight event differs from claim"
    )
    if len(events) == 3 and events[2]["event_type"] == "failed":
        _validate_failed_terminal_payload(events[2]["payload"], active_frozen=None)
        return events
    paths = V11ArtifactPaths.in_directory(path.parent)
    if len(events) >= 3 and events[2]["event_type"] == "acquisition_cleanup_failed":
        cleanup_event = events[2].get("payload")
        if not isinstance(cleanup_event, Mapping) or set(cleanup_event) != {
            "acquisition_cleanup"
        }:
            raise V11DiagnosticError(
                "V11 failed acquisition cleanup event schema changed"
            )
        acquisition_cleanup = cleanup_event.get("acquisition_cleanup")
        if not isinstance(acquisition_cleanup, Mapping):
            raise V11DiagnosticError(
                "V11 failed acquisition cleanup evidence is missing"
            )
        if not _validate_acquisition_cleanup_receipt(acquisition_cleanup, paths):
            raise V11DiagnosticError(
                "V11 failed acquisition cleanup event claims clean evidence"
            )
        if len(events) != 4 or events[3]["event_type"] != "failed":
            raise V11DiagnosticError(
                "V11 failed acquisition cleanup must immediately archive"
            )
        _validate_failed_terminal_payload(events[3]["payload"], active_frozen=None)
        return events
    if len(events) < 3 or events[2]["event_type"] != "scoring_started":
        raise V11DiagnosticError("V11 ledger scoring-start state is missing")
    acquisition_cleanup = events[2]["payload"].get("acquisition_cleanup")
    if not isinstance(acquisition_cleanup, Mapping):
        raise V11DiagnosticError("V11 acquisition cleanup evidence is missing")
    acquisition_warnings = _validate_acquisition_cleanup_receipt(
        acquisition_cleanup, paths
    )
    if acquisition_warnings:
        raise V11DiagnosticError(
            "V11 scoring requires clean acquisition cleanup evidence"
        )
    _same_payload(
        events[2]["payload"],
        {
            "expected_targets": expected_targets,
            "target_start": target_dates[0],
            "target_end": target_dates[-1],
            "acquisition_cleanup": acquisition_cleanup,
            "acquisition_warnings": acquisition_warnings,
        },
        "V11 scoring-start plan differs from claim",
    )

    index = 3
    scored = 0
    previous_maximum = 0
    opportunity_u_values: list[int] = []
    results: dict[str, list[dict[str, Any]]] = {name: [] for name in MODEL_ORDER}
    per_target: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    operational_warnings: list[str] = list(acquisition_warnings)
    last_prediction_timestamp = claim_started_at
    while scored < expected_targets and index < len(events):
        event = events[index]
        if event["event_type"] == "failed":
            break
        if event["event_type"] != "prediction_frozen":
            raise V11DiagnosticError("V11 expected next durable prediction")
        target_text = target_dates[scored]
        target = date.fromisoformat(target_text)
        frozen = event["payload"]
        if set(frozen) != {
            "target_date",
            "forecast_payload",
            "forecast_sha256",
            "model_forecast_sha256",
            "prediction_frozen_at_utc",
        }:
            raise V11DiagnosticError("V11 frozen prediction evidence schema changed")
        prediction_timestamp = _validated_timestamp(
            frozen["prediction_frozen_at_utc"],
            field_name="prediction_frozen_at_utc",
        )
        if prediction_timestamp <= last_prediction_timestamp:
            raise V11DiagnosticError(
                "V11 prediction timestamp does not follow durable claim chronology"
            )
        last_prediction_timestamp = prediction_timestamp
        forecast = frozen.get("forecast_payload")
        if not isinstance(forecast, Mapping):
            raise V11DiagnosticError("V11 frozen forecast payload is missing")
        normalized = _validate_forecast_payload(forecast, target_date=target)
        source_index = trusted_index_by_date.get(target)
        if source_index is None or source_index == 0:
            raise V11DiagnosticError(
                "trusted registered source target/prefix is missing"
            )
        source_lines = trusted_blob.splitlines(keepends=True)
        expected_prefix_sha256 = sha256(
            b"".join(source_lines[: source_index + 1])
        ).hexdigest()
        expected_prefix = {
            "history_draws": source_index,
            "history_through": trusted_date_rows[
                source_index - 1
            ].draw_date.isoformat(),
            "strict_prefix_sha256": expected_prefix_sha256,
        }
        _same_payload(
            normalized["prefix"],
            expected_prefix,
            "trusted registered source prefix differs from frozen forecast",
        )
        _validate_forecast_source_contract(
            normalized,
            _decode_registered_source_row(trusted_date_rows[source_index - 1]),
        )
        forecast_sha = canonical_sha256(normalized)
        forecast_hashes = {
            name: canonical_sha256(normalized["forecasts"][name])
            for name in MODEL_ORDER
        }
        if (
            frozen.get("target_date") != target_text
            or frozen.get("forecast_sha256") != forecast_sha
            or frozen.get("model_forecast_sha256") != forecast_hashes
        ):
            raise V11DiagnosticError("V11 frozen forecast binding changed")
        index += 1
        if index >= len(events):
            if require_terminal:
                raise V11DiagnosticError("V11 durable prediction was never revealed")
            return events
        scored_event = events[index]
        if scored_event["event_type"] == "failed":
            _validate_failed_terminal_payload(
                scored_event["payload"],
                active_frozen=(target_text, forecast_sha),
            )
            index += 1
            if index != len(events):
                raise V11DiagnosticError("V11 ledger has events after failed terminal")
            return events
        if scored_event["event_type"] != "target_revealed_scored":
            raise V11DiagnosticError("V11 prediction was not immediately scored")
        scored_payload = scored_event["payload"]
        actual = _actual_main(scored_payload.get("actual_main", ()))
        source_row = _decode_registered_source_row(
            trusted_date_rows[trusted_index_by_date[target]]
        )
        if actual != source_row.main:
            raise V11DiagnosticError(
                "trusted registered source actual differs from ledger reveal"
            )
        forecasts = normalized["forecasts"]
        scores = {
            name: score_probability_forecast(forecasts[name], actual)
            for name in MODEL_ORDER
        }
        record = _build_progressive_record(
            target_date=target,
            forecast_sha256=forecast_sha,
            forecast=forecasts[CANDIDATE_MODEL],
            score=scores[CANDIDATE_MODEL],
            actual=actual,
            previous_maximum=previous_maximum,
            implementation_commit=claim["implementation_commit"],
        )
        opportunity = build_opportunity_record(
            forecasts,
            forecast_hashes,
            actual,
            target_date=target,
            prior_u_values=opportunity_u_values,
        )
        _same_payload(
            scored_payload,
            {
                "target_date": target_text,
                "forecast_sha256": forecast_sha,
                "actual_main": list(actual),
                "scores": scores,
                "progressive_record": record,
                "opportunity": opportunity,
            },
            "V11 scored evidence is not independently reproducible",
        )
        for name in MODEL_ORDER:
            results[name].append(scores[name])
        opportunity_u_values.append(opportunity["u_t"])
        records.append(record)
        per_target.append(
            {
                "target_date": target_text,
                "forecast_payload": normalized,
                "forecast_sha256": forecast_sha,
                "model_forecast_sha256": forecast_hashes,
                "actual_main": list(actual),
                "scores": scores,
                "progressive_record": record,
                "opportunity": opportunity,
            }
        )
        previous_maximum = record["new_maximum_final6_hits"]
        scored += 1
        index += 1
        exact = [
            item for item in opportunity["unique_final6_sets"] if item["exact_6of6"]
        ]
        if exact:
            if _consume_failed_terminal(events, index, active_frozen=None):
                return events
            if (
                index >= len(events)
                or events[index]["event_type"] != "historical_6of6_candidate_detected"
            ):
                raise V11DiagnosticError("V11 exact 6/6 detection event is missing")
            detection = events[index]["payload"]
            expected_exact = exact[0]
            for key, value in {
                "target_date": target_text,
                "final6": expected_exact["final6"],
                "primary_producer_model_name": expected_exact[
                    "primary_producer_model_name"
                ],
                "producer_model_names": expected_exact["producer_model_names"],
                "producer_forecast_sha256_by_model": expected_exact[
                    "producer_forecast_sha256_by_model"
                ],
                "forecast_sha256": forecast_sha,
                "scored_targets": scored,
            }.items():
                if detection.get(key) != value:
                    raise V11DiagnosticError("V11 exact 6/6 detection was forged")
            index += 1
            if _consume_failed_terminal(events, index, active_frozen=None):
                return events
            if (
                index >= len(events)
                or events[index]["event_type"]
                != "historical_6of6_leakage_audit_completed"
            ):
                raise V11DiagnosticError("V11 exact 6/6 audit event is missing")
            audit_payload = events[index]["payload"]
            audit = audit_payload.get("audit")
            if audit_payload.get("target_date") != target_text or not isinstance(
                audit, Mapping
            ):
                raise V11DiagnosticError("V11 exact 6/6 audit payload is invalid")
            if audit.get("required_check_names") != list(REQUIRED_6OF6_AUDIT_CHECKS):
                raise V11DiagnosticError("V11 exact 6/6 audit checklist changed")
            checks = audit.get("checks")
            if not isinstance(checks, list) or [
                item.get("name") for item in checks
            ] != list(REQUIRED_6OF6_AUDIT_CHECKS):
                raise V11DiagnosticError("V11 exact 6/6 audit evidence is incomplete")
            recomputed_clear = (
                audit.get("callback_error") is None
                and not audit.get("schema_errors")
                and all(
                    item.get("passed") is True
                    and item.get("evidence") not in (None, "", [], {})
                    for item in checks
                )
            )
            if audit.get("clear") is not recomputed_clear:
                raise V11DiagnosticError("V11 exact 6/6 audit result was forged")
            index += 1
            if index == len(events) and not require_terminal:
                return events
            if index < len(events) and events[index]["event_type"] == "failed":
                _validate_failed_terminal_payload(
                    events[index]["payload"], active_frozen=None
                )
                if index + 1 != len(events):
                    raise V11DiagnosticError(
                        "V11 ledger has events after failed 6/6 publication"
                    )
                return events
            terminal_type = (
                "historical_6of6_candidate_published"
                if recomputed_clear
                else "historical_6of6_candidate_archived_leakage_failed"
            )
            if index >= len(events) or events[index]["event_type"] != terminal_type:
                raise V11DiagnosticError("V11 exact 6/6 terminal disposition changed")
            terminal_index = index
            terminal = events[terminal_index]["payload"]
            expected_bundle_path = path.parent / (
                "historical-6of6-candidate__"
                f"{target_text}__{expected_exact['primary_producer_model_name']}__"
                "v11.0.0.json"
            )
            bundle_path = _artifact_from_relative_identity(
                path.parent,
                terminal.get("bundle_path"),
                expected=expected_bundle_path,
            )
            expected_bundle = _build_exact6_bundle(
                clear=recomputed_clear,
                target_date=target_text,
                exact=expected_exact,
                forecast_payload=normalized,
                forecast_sha256=forecast_sha,
                actual=actual,
                opportunity=opportunity,
                evaluation_by_model=scores,
                results=results,
                bootstrap_replicates=plan["bootstrap_replicates"],
                bootstrap_seed=plan["bootstrap_seed"],
                audit=audit,
                preflight=preflight,
                implementation_commit=claim["implementation_commit"],
                exact_command=claim["exact_command"],
                claim_path=_artifact_relative_identity(paths.claim, path.parent),
                claim_sha256=claim_sha256,
                ledger_head_before_bundle=events[terminal_index - 1]["event_sha256"],
                scored_targets=scored,
            )
            expected_bundle_raw = _pretty_json_bytes(expected_bundle)
            try:
                bundle_raw = bundle_path.read_bytes()
            except OSError as exc:
                raise V11DiagnosticError("V11 exact 6/6 bundle is missing") from exc
            if bundle_raw != expected_bundle_raw:
                raise V11DiagnosticError("V11 exact 6/6 bundle is not replayable")
            bundle_sha256 = sha256(bundle_raw).hexdigest()
            expected_terminal = _exact6_terminal_payload(
                expected_bundle,
                terminal_type=terminal_type,
                bundle_path=_artifact_relative_identity(bundle_path, path.parent),
                bundle_sha256=bundle_sha256,
                operational_warnings=operational_warnings,
            )
            _same_payload(
                terminal,
                expected_terminal,
                "V11 exact 6/6 notification or terminal was forged",
            )
            _validate_notification_envelope(terminal)
            _validate_terminal_notification_suffix(
                events,
                terminal_index=terminal_index,
                require_receipt=require_terminal_notification_receipt,
            )
            return events
        expected_progress = _progress_notification_requests(
            target_date=target,
            forecasts=forecasts,
            scores=scores,
            record=record,
        )
        for progress in expected_progress:
            if index < len(events) and events[index]["event_type"] == "failed":
                _validate_failed_terminal_payload(
                    events[index]["payload"], active_frozen=None
                )
                if index + 1 != len(events):
                    raise V11DiagnosticError(
                        "V11 ledger has events after failed terminal"
                    )
                return events
            if (
                index >= len(events)
                or events[index]["event_type"] != "progress_notification_outbox"
            ):
                raise V11DiagnosticError("V11 progress notification outbox is missing")
            notification = _notification_payload(
                progress["subject"],
                progress["body"],
                {
                    "kind": progress["kind"],
                    "target_date": target_text,
                    "forecast_sha256": forecast_sha,
                },
            )
            expected_outbox = {
                "kind": progress["kind"],
                "model_names": progress["model_names"],
                "target_date": target_text,
                "forecast_sha256": forecast_sha,
                **notification,
            }
            _same_payload(
                events[index]["payload"],
                expected_outbox,
                "V11 progress notification outbox was forged",
            )
            _validate_notification_envelope(events[index]["payload"])
            index += 1
            if index < len(events) and events[index]["event_type"] == "failed":
                _validate_failed_terminal_payload(
                    events[index]["payload"], active_frozen=None
                )
                if index + 1 != len(events):
                    raise V11DiagnosticError(
                        "V11 ledger has events after failed terminal"
                    )
                return events
            if (
                index >= len(events)
                or events[index]["event_type"] != "progress_notification_receipt"
            ):
                raise V11DiagnosticError("V11 progress notification receipt is missing")
            warning = _validate_notification_receipt(
                events[index]["payload"],
                idempotency_key=notification["notification_idempotency_key"],
            )
            if warning is not None:
                operational_warnings.append(warning)
            index += 1
        if index < len(events) and events[index]["event_type"] in {
            "progress_notification_outbox",
            "progress_notification_receipt",
        }:
            raise V11DiagnosticError("V11 unexpected progress notification event")

    if index < len(events) and events[index]["event_type"] == "failed":
        _validate_failed_terminal_payload(events[index]["payload"], active_frozen=None)
        index += 1
        if index != len(events):
            raise V11DiagnosticError("V11 ledger has events after failed terminal")
        return events
    if scored != expected_targets:
        if require_terminal:
            raise V11DiagnosticError("V11 ledger stopped before all targets")
        return events
    # Full-row semantic validation is intentionally deferred until every
    # registered target prediction has been frozen and revealed.
    _decode_registered_source_rows(trusted_blob, registered_identity)
    if index >= len(events) or events[index]["event_type"] != "scoring_completed":
        raise V11DiagnosticError(
            "V11 normal scoring/publication sequence is incomplete"
        )
    scoring_completed = events[index]
    expected_status = (
        "complete_621" if expected_targets == 621 else "synthetic_complete"
    )
    _same_payload(
        scoring_completed["payload"],
        {"scored_targets": expected_targets, "status": expected_status},
        "V11 scoring-completed payload changed",
    )
    index += 1
    if _consume_failed_terminal(events, index, active_frozen=None):
        return events
    if index >= len(events) or events[index]["event_type"] != "publication_started":
        raise V11DiagnosticError(
            "V11 normal scoring/publication sequence is incomplete"
        )
    publication_started = events[index]
    paths = V11ArtifactPaths.in_directory(path.parent)
    _same_payload(
        publication_started["payload"],
        {
            "scored_targets": expected_targets,
            "report_json": _artifact_relative_identity(paths.report_json, path.parent),
            "report_markdown": _artifact_relative_identity(
                paths.report_markdown, path.parent
            ),
        },
        "V11 publication paths changed",
    )
    index += 1
    if index < len(events) and events[index]["event_type"] == "failed":
        _validate_failed_terminal_payload(events[index]["payload"], active_frozen=None)
        if index + 1 != len(events):
            raise V11DiagnosticError("V11 ledger has events after failed terminal")
        return events
    if index == len(events) and not require_terminal:
        return events
    if index >= len(events) or events[index]["event_type"] != "published":
        raise V11DiagnosticError("V11 normal published terminal is missing")
    terminal_index = index
    terminal = events[terminal_index]["payload"]
    expected_report = _replay_report(
        claim=claim,
        preflight=preflight,
        claim_sha256=claim_sha256,
        results=results,
        per_target=per_target,
        records=records,
        ledger_head=publication_started["event_sha256"],
        output_dir=path.parent,
        operational_warnings=operational_warnings,
        registered_identity=registered_identity,
    )
    try:
        report_raw = paths.report_json.read_bytes()
        report = json.loads(report_raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise V11DiagnosticError("V11 published JSON report is unreadable") from exc
    expected_json = _pretty_json_bytes(expected_report)
    if report_raw != expected_json or report != expected_report:
        raise V11DiagnosticError("V11 published JSON report is not replayable")
    try:
        markdown_raw = paths.report_markdown.read_bytes()
    except OSError as exc:
        raise V11DiagnosticError("V11 published Markdown report is missing") from exc
    if markdown_raw != _render_markdown(expected_report).encode("utf-8"):
        raise V11DiagnosticError("V11 published Markdown report is not replayable")
    expected_terminal = _normal_terminal_payload(
        expected_report,
        json_path=_artifact_relative_identity(paths.report_json, path.parent),
        json_sha256=sha256(report_raw).hexdigest(),
        markdown_path=_artifact_relative_identity(paths.report_markdown, path.parent),
        markdown_sha256=sha256(markdown_raw).hexdigest(),
        scored_targets=expected_targets,
        implementation_commit=claim["implementation_commit"],
        operational_warnings=operational_warnings,
    )
    _same_payload(
        terminal,
        expected_terminal,
        "V11 published notification or terminal was forged",
    )
    _validate_notification_envelope(terminal)
    _validate_terminal_notification_suffix(
        events,
        terminal_index=terminal_index,
        require_receipt=require_terminal_notification_receipt,
    )
    return events


def run_v11_historical(request: V11DiagnosticRequest) -> dict[str, Any]:
    """Consume the sole V11 attempt through the registered reveal state machine."""

    targets = tuple(request.targets)
    if len(targets) != request.expected_target_count or not targets:
        raise V11DiagnosticError("V11 target count differs from registration")
    dates = [target.target_date for target in targets]
    if dates != sorted(dates) or len(set(dates)) != len(dates):
        raise V11DiagnosticError("V11 targets are not strictly ordered and unique")
    if len(request.stability_scopes) != 2:
        raise V11DiagnosticError("V11 requires exactly two stability halves")
    for scope in request.stability_scopes:
        if sum(scope.contains(target) for target in dates) != scope.target_count:
            raise V11DiagnosticError(f"V11 scope {scope.name} does not match targets")
    if sum(scope.target_count for scope in request.stability_scopes) != len(targets):
        raise V11DiagnosticError("V11 fixed halves do not partition targets")

    paths = V11ArtifactPaths.in_directory(request.output_dir)
    breakthrough_staging = tuple(
        request.output_dir.glob(".historical-6of6-candidate__*__v11.0.0.json.staging")
    )
    breakthrough_final = tuple(
        request.output_dir.glob("historical-6of6-candidate__*__v11.0.0.json")
    )
    existing = [
        path for path in paths.all_normal_paths() if _directory_entry_exists(path)
    ]
    existing.extend(breakthrough_staging)
    existing.extend(breakthrough_final)
    if existing:
        raise V11DiagnosticError(f"V11 artifact already exists: {existing[0].name}")
    preflight = dict(request.preflight())
    if preflight.get("passed") is not True or preflight.get("audit_warnings"):
        raise V11DiagnosticError("V11 preflight did not pass without warnings")
    if preflight.get("registration_commit") != REGISTRATION_COMMIT:
        raise V11DiagnosticError("V11 registration commit identity changed")
    if preflight.get("implementation_commit") != request.code_commit:
        raise V11DiagnosticError("V11 implementation commit identity changed")
    _validate_preflight_evidence(
        preflight,
        implementation_commit=request.code_commit,
        expected_targets=request.expected_target_count,
        registered_identity=request.registered_identity,
    )
    if request.source_blob_resolver is None:
        raise V11DiagnosticError("trusted registered source resolver is required")
    _trusted_blob, trusted_rows = _resolve_trusted_source_dates(
        {"preflight": preflight},
        request.source_blob_resolver,
        request.registered_identity,
    )
    analysis_plan = _validate_request_analysis_plan(request, dates, trusted_rows)

    started = _timestamp(request.clock())
    claim_payload = {
        "schema_version": 1,
        "experiment_id": EXPERIMENT_ID,
        "model_version": MODEL_VERSION,
        "seed": 649,
        "registration_commit": REGISTRATION_COMMIT,
        "implementation_commit": request.code_commit,
        "exact_command": request.exact_command,
        "exact_command_sha256": sha256(
            request.exact_command.encode("utf-8")
        ).hexdigest(),
        "started_at_utc": started,
        "preflight": preflight,
        "analysis_plan": analysis_plan,
        "analysis_plan_sha256": canonical_sha256(analysis_plan),
        "status": "consumed_permanently_no_rerun",
    }
    ledger: HashChainLedger | None = None
    terminal = False
    active_frozen: tuple[str, str] | None = None
    external_warnings: list[str] = []
    try:
        ledger, claim_sha256, acquisition_cleanup = _acquire_attempt(
            paths, claim_payload
        )
        acquisition_warnings = _acquisition_operational_warnings(acquisition_cleanup)
        external_warnings.extend(acquisition_warnings)
        ledger.append("preflight_passed", preflight)
        if acquisition_warnings:
            ledger.append(
                "acquisition_cleanup_failed",
                {"acquisition_cleanup": acquisition_cleanup},
            )
            cleanup_error = V11DiagnosticError("V11 acquisition cleanup was not clean")
            ledger.append(
                "failed",
                {
                    "error_type": type(cleanup_error).__name__,
                    "error_message": str(cleanup_error),
                    "status": "consumed_archive_no_rerun",
                    "last_frozen_target_date": None,
                    "last_frozen_forecast_sha256": None,
                },
            )
            terminal = True
            validate_v11_ledger_state_machine(
                paths.ledger,
                expected_targets=request.expected_target_count,
                source_blob_resolver=request.source_blob_resolver,
                registered_identity=request.registered_identity,
            )
            raise cleanup_error
        ledger.append(
            "scoring_started",
            {
                "expected_targets": request.expected_target_count,
                "target_start": dates[0].isoformat(),
                "target_end": dates[-1].isoformat(),
                "acquisition_cleanup": acquisition_cleanup,
                "acquisition_warnings": acquisition_warnings,
            },
        )
        results: dict[str, list[dict[str, Any]]] = {name: [] for name in MODEL_ORDER}
        per_target: list[dict[str, Any]] = []
        records: list[dict[str, Any]] = []
        previous_maximum = 0
        opportunity_u_values: list[int] = []
        for plan in targets:
            first = _validate_forecast_payload(
                plan.build_forecasts(), target_date=plan.target_date
            )
            repeated = _validate_forecast_payload(
                plan.build_forecasts(), target_date=plan.target_date
            )
            if _canonical_json_bytes(first) != _canonical_json_bytes(repeated):
                raise V11DiagnosticError("V11 repeated strict-prefix forecast changed")
            forecast_sha = canonical_sha256(first)
            forecasts = first["forecasts"]
            forecast_hashes = {
                name: canonical_sha256(forecasts[name]) for name in MODEL_ORDER
            }
            ledger.append(
                "prediction_frozen",
                {
                    "target_date": plan.target_date.isoformat(),
                    "forecast_payload": first,
                    "forecast_sha256": forecast_sha,
                    "model_forecast_sha256": forecast_hashes,
                    "prediction_frozen_at_utc": _timestamp(request.clock()),
                },
            )
            active_frozen = (plan.target_date.isoformat(), forecast_sha)

            # Sole outcome access: append() above has flushed and fsynced.
            actual = _actual_main(plan.reveal_actual())
            target_scores = {
                name: score_probability_forecast(forecasts[name], actual)
                for name in MODEL_ORDER
            }
            for name in MODEL_ORDER:
                results[name].append(target_scores[name])
            opportunity = build_opportunity_record(
                forecasts,
                forecast_hashes,
                actual,
                target_date=plan.target_date,
                prior_u_values=opportunity_u_values,
            )
            opportunity_u_values.append(int(opportunity["u_t"]))
            candidate_hits = int(target_scores[CANDIDATE_MODEL]["final6_hits"])
            record = _build_progressive_record(
                target_date=plan.target_date,
                forecast_sha256=forecast_sha,
                forecast=forecasts[CANDIDATE_MODEL],
                score=target_scores[CANDIDATE_MODEL],
                actual=actual,
                previous_maximum=previous_maximum,
                implementation_commit=request.code_commit,
            )
            records.append(record)
            scored_payload = {
                "target_date": plan.target_date.isoformat(),
                "forecast_sha256": forecast_sha,
                "actual_main": list(actual),
                "scores": target_scores,
                "progressive_record": record,
                "opportunity": opportunity,
            }
            ledger.append("target_revealed_scored", scored_payload)
            active_frozen = None
            per_target.append(
                {
                    "target_date": plan.target_date.isoformat(),
                    "forecast_payload": first,
                    "forecast_sha256": forecast_sha,
                    "model_forecast_sha256": forecast_hashes,
                    "actual_main": list(actual),
                    "scores": target_scores,
                    "progressive_record": record,
                    "opportunity": opportunity,
                }
            )

            exact_sets = [
                item for item in opportunity["unique_final6_sets"] if item["exact_6of6"]
            ]
            if exact_sets:
                exact = exact_sets[0]
                ledger.append(
                    "historical_6of6_candidate_detected",
                    {
                        "target_date": plan.target_date.isoformat(),
                        "final6": exact["final6"],
                        "primary_producer_model_name": exact[
                            "primary_producer_model_name"
                        ],
                        "producer_model_names": exact["producer_model_names"],
                        "producer_forecast_sha256_by_model": exact[
                            "producer_forecast_sha256_by_model"
                        ],
                        "forecast_sha256": forecast_sha,
                        "scored_targets": len(per_target),
                    },
                )
                audit_events = verify_hash_chain_ledger(paths.ledger)
                audit = _normalized_audit(
                    request.leakage_audit,
                    plan.target_date,
                    first,
                    actual,
                    claim_evidence={
                        "claim_sha256_matches": _file_sha256(paths.claim)
                        == claim_sha256,
                        "claimed_genesis_matches": audit_events[0]["payload"].get(
                            "claim_sha256"
                        )
                        == claim_sha256,
                        "claim_precedes_first_prediction": audit_events[0]["sequence"]
                        < next(
                            event["sequence"]
                            for event in audit_events
                            if event["event_type"] == "prediction_frozen"
                        ),
                        "ledger_contains_current_prediction": any(
                            event["event_type"] == "prediction_frozen"
                            and event["payload"].get("forecast_sha256") == forecast_sha
                            for event in audit_events
                        ),
                    },
                )
                ledger.append(
                    "historical_6of6_leakage_audit_completed",
                    {"target_date": plan.target_date.isoformat(), "audit": audit},
                )
                validate_v11_ledger_state_machine(
                    paths.ledger,
                    expected_targets=request.expected_target_count,
                    require_terminal=False,
                    source_blob_resolver=request.source_blob_resolver,
                    registered_identity=request.registered_identity,
                )
                bundle_path = request.output_dir / (
                    "historical-6of6-candidate__"
                    f"{plan.target_date.isoformat()}__"
                    f"{exact['primary_producer_model_name']}__v11.0.0.json"
                )
                clear = audit["clear"] is True
                bundle = _build_exact6_bundle(
                    clear=clear,
                    target_date=plan.target_date.isoformat(),
                    exact=exact,
                    forecast_payload=first,
                    forecast_sha256=forecast_sha,
                    actual=actual,
                    opportunity=opportunity,
                    evaluation_by_model=target_scores,
                    results=results,
                    bootstrap_replicates=request.bootstrap_replicates,
                    bootstrap_seed=request.bootstrap_seed,
                    audit=audit,
                    preflight=preflight,
                    implementation_commit=request.code_commit,
                    exact_command=request.exact_command,
                    claim_path=_artifact_relative_identity(
                        paths.claim, request.output_dir
                    ),
                    claim_sha256=claim_sha256,
                    ledger_head_before_bundle=ledger.head_sha256,
                    scored_targets=len(per_target),
                )
                publication_warnings = _safe_publish_bundle(bundle_path, bundle)
                external_warnings.extend(publication_warnings)
                terminal_type = (
                    "historical_6of6_candidate_published"
                    if clear
                    else "historical_6of6_candidate_archived_leakage_failed"
                )
                bundle_sha256 = _file_sha256(bundle_path)
                notification = _exact6_notification(
                    bundle,
                    terminal_type=terminal_type,
                    bundle_sha256=bundle_sha256,
                )
                terminal_payload = _exact6_terminal_payload(
                    bundle,
                    terminal_type=terminal_type,
                    bundle_path=_artifact_relative_identity(
                        bundle_path, request.output_dir
                    ),
                    bundle_sha256=bundle_sha256,
                    operational_warnings=external_warnings,
                )
                terminal_event = ledger.append(terminal_type, terminal_payload)
                terminal = True
                validate_v11_ledger_state_machine(
                    paths.ledger,
                    expected_targets=request.expected_target_count,
                    require_terminal_notification_receipt=False,
                    source_blob_resolver=request.source_blob_resolver,
                    registered_identity=request.registered_identity,
                )
                receipt = _dispatch_notification(request.notifier, notification)
                ledger.append(
                    "terminal_notification_receipt",
                    {
                        "scientific_terminal_event_sha256": terminal_event[
                            "event_sha256"
                        ],
                        "receipt": receipt,
                    },
                )
                if receipt["operational_warning"] is not None:
                    external_warnings.append(receipt["operational_warning"])
                validate_v11_ledger_state_machine(
                    paths.ledger,
                    expected_targets=request.expected_target_count,
                    source_blob_resolver=request.source_blob_resolver,
                    registered_identity=request.registered_identity,
                )
                return {
                    "status": terminal_type,
                    "claim_path": str(paths.claim),
                    "ledger_path": str(paths.ledger),
                    "bundle_path": str(bundle_path),
                    "scored_targets": len(per_target),
                    "stop_global_search": clear,
                    "notification_dispatched_after_terminal": receipt[
                        "dispatch_accepted"
                    ],
                    "notification_receipt": receipt,
                    "external_notification_warnings": external_warnings,
                }

            progress_requests = _progress_notification_requests(
                target_date=plan.target_date,
                forecasts=forecasts,
                scores=target_scores,
                record=record,
            )
            for progress in progress_requests:
                notification = _notification_payload(
                    progress["subject"],
                    progress["body"],
                    {
                        "kind": progress["kind"],
                        "target_date": plan.target_date.isoformat(),
                        "forecast_sha256": forecast_sha,
                    },
                )
                ledger.append(
                    "progress_notification_outbox",
                    {
                        "kind": progress["kind"],
                        "model_names": progress["model_names"],
                        "target_date": plan.target_date.isoformat(),
                        "forecast_sha256": forecast_sha,
                        **notification,
                    },
                )
                receipt = _dispatch_notification(request.notifier, notification)
                ledger.append("progress_notification_receipt", receipt)
                warning = receipt["operational_warning"]
                if warning is not None:
                    external_warnings.append(warning)
            previous_maximum = max(previous_maximum, candidate_hits)

        ledger.append(
            "scoring_completed",
            {
                "scored_targets": len(per_target),
                "status": "complete_621"
                if len(per_target) == 621
                else "synthetic_complete",
            },
        )
        ledger.append(
            "publication_started",
            {
                "scored_targets": len(per_target),
                "report_json": _artifact_relative_identity(
                    paths.report_json, request.output_dir
                ),
                "report_markdown": _artifact_relative_identity(
                    paths.report_markdown, request.output_dir
                ),
            },
        )
        report = _build_report(
            request,
            preflight=preflight,
            claim_sha256=claim_sha256,
            results=results,
            per_target=per_target,
            record_ledger=records,
            ledger=ledger,
            operational_warnings=external_warnings,
        )
        validate_v11_ledger_state_machine(
            paths.ledger,
            expected_targets=request.expected_target_count,
            require_terminal=False,
            source_blob_resolver=request.source_blob_resolver,
            registered_identity=request.registered_identity,
        )
        json_bytes = _pretty_json_bytes(report)
        markdown_bytes = _render_markdown(report).encode("utf-8")
        publication_warnings = _safe_publish_pair(paths, json_bytes, markdown_bytes)
        external_warnings.extend(publication_warnings)
        passed = report["historical_decision"]["all_scientific_gates_passed"]
        terminal_payload = _normal_terminal_payload(
            report,
            json_path=_artifact_relative_identity(
                paths.report_json, request.output_dir
            ),
            json_sha256=_file_sha256(paths.report_json),
            markdown_path=_artifact_relative_identity(
                paths.report_markdown, request.output_dir
            ),
            markdown_sha256=_file_sha256(paths.report_markdown),
            scored_targets=len(per_target),
            implementation_commit=request.code_commit,
            operational_warnings=external_warnings,
        )
        terminal_event = ledger.append("published", terminal_payload)
        terminal = True
        validate_v11_ledger_state_machine(
            paths.ledger,
            expected_targets=request.expected_target_count,
            require_terminal_notification_receipt=False,
            source_blob_resolver=request.source_blob_resolver,
            registered_identity=request.registered_identity,
        )
        sent = None
        receipt = None
        if passed:
            receipt = _dispatch_notification(request.notifier, terminal_payload)
            ledger.append(
                "terminal_notification_receipt",
                {
                    "scientific_terminal_event_sha256": terminal_event["event_sha256"],
                    "receipt": receipt,
                },
            )
            sent = receipt["dispatch_accepted"]
            if receipt["operational_warning"] is not None:
                external_warnings.append(receipt["operational_warning"])
        validate_v11_ledger_state_machine(
            paths.ledger,
            expected_targets=request.expected_target_count,
            source_blob_resolver=request.source_blob_resolver,
            registered_identity=request.registered_identity,
        )
        return {
            "status": "published",
            "claim_path": str(paths.claim),
            "ledger_path": str(paths.ledger),
            "json_path": str(paths.report_json),
            "markdown_path": str(paths.report_markdown),
            "report": report,
            "stop_global_search": False,
            "notification_dispatched_after_terminal": sent,
            "notification_receipt": receipt,
            "external_notification_warnings": external_warnings,
        }
    except Exception as exc:
        if ledger is not None and not terminal:
            try:
                ledger.append(
                    "failed",
                    {
                        "error_type": type(exc).__name__,
                        "error_message": str(exc),
                        "status": "consumed_archive_no_rerun",
                        "last_frozen_target_date": (
                            active_frozen[0] if active_frozen is not None else None
                        ),
                        "last_frozen_forecast_sha256": (
                            active_frozen[1] if active_frozen is not None else None
                        ),
                    },
                )
            except Exception:  # noqa: BLE001, S110 - preserve the primary failure
                pass
        raise
    finally:
        if ledger is not None:
            ledger.close()
