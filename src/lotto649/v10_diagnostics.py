"""One-shot, leakage-safe V10 historical diagnostic infrastructure.

This module is intentionally independent of the normal model factory and
``run_backtest``.  The V10 historical attempt has a stricter state machine:
each deterministic forecast is durably receipted before its target may cross
the reveal seam.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from functools import lru_cache
from hashlib import sha256
import json
import math
import os
from pathlib import Path
from typing import Any, Self

import numpy as np


ZERO_EVENT_HASH = "0" * 64
EXPERIMENT_ID = "V10_adjacent_pair_structure"
MODEL_VERSION = "v10.0.0"
CANDIDATE_MODEL = "v10_adjacent_pair_structure"
TARGETED_CONTROL_MODEL = "v10_adjacency_label_bijection_control"
RANDOM_CONTROL_MODEL = "random"
MODEL_ORDER = (CANDIDATE_MODEL, TARGETED_CONTROL_MODEL, RANDOM_CONTROL_MODEL)
FAIR_PROBABILITY = 6.0 / 49.0
FAIR_TOTAL_SIX_SETS = 13_983_816
FAIR_EXPECTATIONS = {6: 36.0 / 49.0, 12: 72.0 / 49.0, 18: 108.0 / 49.0}
JOINT_AGGREGATE_THRESHOLD = 2.995732273553991
PROPER_SCORE_TOLERANCE = 1.0e-9
DEFAULT_REPORT_STEM = "v10_adjacent_pair_structure_v10.0.0_historical"


Notifier = Callable[[str, str], bool]
Clock = Callable[[], datetime]
REQUIRED_6OF6_AUDIT_CHECKS = (
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
HISTORICAL_GATE_NAMES = frozenset(
    {
        "positive_aggregate_primary_lift",
        "aggregate_holm_adjusted_p_at_most_0_05",
        "aggregate_bootstrap_lower_above_zero",
        "positive_primary_lift_in_both_fixed_halves",
        "candidate_outperforms_targeted_control_aggregate_and_halves",
        "proper_scores_within_fair_tolerance_aggregate_and_halves",
        "candidate_above_frozen_v1_ensemble_top12",
        "controls_null_aggregate_and_halves",
        "joint_mechanism_gate",
        "audit_clear",
    }
)


class V10DiagnosticError(RuntimeError):
    """Raised when the frozen V10 diagnostic cannot proceed safely."""


def _canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    try:
        text = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
            ensure_ascii=False,
        )
        return text.encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise V10DiagnosticError("V10 payload is not canonical finite JSON") from exc


def _directory_fsync(directory: Path) -> None:
    descriptor = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


class HashChainLedger:
    """Exclusive append-only JSONL ledger with a canonical SHA-256 chain."""

    def __init__(self, path: Path, handle) -> None:
        self.path = path
        self._handle = handle
        self._sequence = 0
        self._previous_hash = ZERO_EVENT_HASH
        self._closed = False

    @classmethod
    def create(cls, path: Path) -> Self:
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            handle = path.open("x", encoding="utf-8", newline="\n")
        except FileExistsError as exc:
            raise V10DiagnosticError("V10 attempt ledger already exists") from exc
        try:
            handle.flush()
            os.fsync(handle.fileno())
            _directory_fsync(path.parent)
        except OSError:
            handle.close()
            raise
        return cls(path, handle)

    def append(self, event_type: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        if self._closed:
            raise V10DiagnosticError("V10 attempt ledger is closed")
        if not event_type:
            raise V10DiagnosticError("V10 ledger event type must not be empty")
        event_without_hash = {
            "event_type": event_type,
            "payload": dict(payload),
            "previous_event_sha256": self._previous_hash,
            "sequence": self._sequence,
        }
        canonical_without_hash = _canonical_json_bytes(event_without_hash)
        event_hash = sha256(
            canonical_without_hash + self._previous_hash.encode("ascii")
        ).hexdigest()
        event = {**event_without_hash, "event_sha256": event_hash}
        serialized = _canonical_json_bytes(event) + b"\n"
        try:
            self._handle.write(serialized.decode("utf-8"))
            self._handle.flush()
            os.fsync(self._handle.fileno())
        except OSError as exc:
            raise V10DiagnosticError("unable to durably append V10 ledger event") from exc
        self._sequence += 1
        self._previous_hash = event_hash
        return event

    @property
    def head_sha256(self) -> str:
        return self._previous_hash

    @property
    def event_count(self) -> int:
        return self._sequence

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
        raw_lines = path.read_bytes().splitlines(keepends=True)
    except OSError as exc:
        raise V10DiagnosticError("unable to read V10 attempt ledger") from exc
    if not raw_lines:
        raise V10DiagnosticError("V10 attempt ledger is empty")
    previous_hash = ZERO_EVENT_HASH
    events: list[dict[str, Any]] = []
    for sequence, raw_line in enumerate(raw_lines):
        if not raw_line.endswith(b"\n"):
            raise V10DiagnosticError("V10 ledger line lacks a newline terminator")
        try:
            event = json.loads(raw_line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise V10DiagnosticError("V10 ledger line is not valid UTF-8 JSON") from exc
        if not isinstance(event, dict):
            raise V10DiagnosticError("V10 ledger event must be a JSON object")
        if _canonical_json_bytes(event) + b"\n" != raw_line:
            raise V10DiagnosticError("V10 ledger event is not canonical JSON")
        if event.get("sequence") != sequence:
            raise V10DiagnosticError("V10 ledger sequence is not contiguous")
        if event.get("previous_event_sha256") != previous_hash:
            raise V10DiagnosticError("V10 ledger previous-event hash mismatch")
        event_hash = event.get("event_sha256")
        if not isinstance(event_hash, str) or len(event_hash) != 64:
            raise V10DiagnosticError("V10 ledger event hash is invalid")
        event_without_hash = dict(event)
        event_without_hash.pop("event_sha256")
        expected_hash = sha256(
            _canonical_json_bytes(event_without_hash) + previous_hash.encode("ascii")
        ).hexdigest()
        if event_hash != expected_hash:
            raise V10DiagnosticError("V10 ledger event hash mismatch")
        previous_hash = event_hash
        events.append(event)
    return events


def _derived_6of6_audit_clear(audit: Any) -> bool:
    """Validate normalized audit evidence and independently derive clearance."""

    if not isinstance(audit, Mapping):
        raise V10DiagnosticError("V10 6/6 audit payload is invalid")
    expected_keys = {
        "callback_error",
        "checks",
        "clear",
        "declared_clear_ignored",
        "required_check_names",
        "schema_errors",
    }
    if set(audit) != expected_keys:
        raise V10DiagnosticError("V10 6/6 audit schema is not normalized")
    _canonical_json_bytes(audit)
    if audit.get("required_check_names") != list(REQUIRED_6OF6_AUDIT_CHECKS):
        raise V10DiagnosticError("V10 6/6 audit required-check identity changed")
    checks = audit.get("checks")
    if not isinstance(checks, list) or len(checks) != len(
        REQUIRED_6OF6_AUDIT_CHECKS
    ):
        raise V10DiagnosticError("V10 6/6 audit check count is invalid")
    check_passes: list[bool] = []
    for expected_name, check in zip(REQUIRED_6OF6_AUDIT_CHECKS, checks):
        if not isinstance(check, Mapping) or set(check) != {
            "evidence",
            "name",
            "passed",
        }:
            raise V10DiagnosticError("V10 6/6 audit check schema is invalid")
        if check.get("name") != expected_name or type(check.get("passed")) is not bool:
            raise V10DiagnosticError("V10 6/6 audit check identity/type is invalid")
        evidence = check.get("evidence")
        _canonical_json_bytes({"evidence": evidence})
        check_passes.append(
            check.get("passed") is True and evidence not in (None, "", [], {})
        )
    schema_errors = audit.get("schema_errors")
    if not isinstance(schema_errors, list) or any(
        not isinstance(error, str) for error in schema_errors
    ):
        raise V10DiagnosticError("V10 6/6 audit schema errors are invalid")
    callback_error = audit.get("callback_error")
    if callback_error is not None and (
        not isinstance(callback_error, Mapping)
        or not isinstance(callback_error.get("error_type"), str)
        or not isinstance(callback_error.get("error_message"), str)
    ):
        raise V10DiagnosticError("V10 6/6 audit callback error is invalid")
    declared_clear = audit.get("declared_clear_ignored")
    if declared_clear is not None and type(declared_clear) is not bool:
        raise V10DiagnosticError("V10 6/6 declared-clear record is invalid")
    derived = callback_error is None and not schema_errors and all(check_passes)
    if type(audit.get("clear")) is not bool or audit.get("clear") is not derived:
        raise V10DiagnosticError("V10 6/6 audit clear disagrees with its checks")
    return derived


def _validate_notification_outbox(
    payload: Mapping[str, Any],
    *,
    warnings_before: Sequence[str],
    notification_required: bool,
    expected_subject: str | None,
    expected_body: str | None,
    idempotency_context: Mapping[str, Any],
    error_message: str,
) -> None:
    """Validate the exact durable outbox written before any external dispatch."""

    expected = _notification_outbox_fields(
        warnings_before=warnings_before,
        notification_required=notification_required,
        subject=expected_subject,
        body=expected_body,
        idempotency_context=idempotency_context,
    )
    if any(payload.get(key) != value for key, value in expected.items()):
        raise V10DiagnosticError(error_message)


def _progress_notification_requests(
    *,
    forecast_payload: Mapping[str, Any],
    actual: Sequence[int],
    target_date: str,
    candidate_score: Mapping[str, Any],
    progressive_record: Mapping[str, Any],
) -> tuple[tuple[str, str, str], ...]:
    """Derive the exact in-run notification requests from one durable score."""

    forecasts = forecast_payload["forecasts"]
    candidate = forecasts[CANDIDATE_MODEL]
    requests: list[tuple[str, str, str]] = []
    current_hits = int(candidate_score["final6_hits"])
    if progressive_record.get("new_within_run_record") is True and current_hits >= 2:
        requests.append(
            (
                "new_record",
                f"[LOTTO649] 【历史严格回测】V10运行内新纪录 {current_hits}/6",
                (
                    "这是V10单次运行内纪录，尚不是跨版本全局纪录，需审计。\n"
                    f"开奖日期：{target_date}\n"
                    f"预测：{list(candidate['final6'])}\n"
                    f"实际：{list(actual)}\n"
                    "证据类型：已持久化后揭晓的历史严格walk-forward。"
                ),
            )
        )
    if int(candidate_score["top12_hits"]) == 6:
        requests.append(
            (
                "top12_complete",
                "[LOTTO649] 【历史严格回测】V10 Top-12包含完整6/6",
                (
                    f"开奖日期：{target_date}\n"
                    f"Top-12：{list(candidate['top12'])}\n"
                    f"实际：{list(actual)}\n"
                    "预测已在揭晓前写入并fsync到永久账本。"
                ),
            )
        )
    return tuple(requests)


def _progress_notification_context(
    *,
    code_commit: str,
    kind: str,
    target_date: str,
    forecast_sha256: str,
) -> dict[str, Any]:
    return {
        "code_commit": code_commit,
        "event_type": "progress_notification_outbox",
        "experiment_id": EXPERIMENT_ID,
        "forecast_sha256": forecast_sha256,
        "kind": kind,
        "target_date": target_date,
    }


def validate_v10_ledger_state_machine(
    path: Path,
    *,
    expected_targets: int,
    allow_publication_prefix: bool = False,
    allow_6of6_audit_prefix: bool = False,
    prospective_6of6_terminal: tuple[str, Mapping[str, Any]] | None = None,
    prospective_normal_terminal: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Verify both the hash chain and the frozen V10 event grammar."""

    events = verify_hash_chain_ledger(path)
    failed_terminal = events[-1].get("event_type") == "failed"
    body = events[:-1] if failed_terminal else events
    if prospective_6of6_terminal is not None:
        if failed_terminal:
            raise V10DiagnosticError("V10 failed ledger cannot project a 6/6 terminal")
        event_type, payload = prospective_6of6_terminal
        body = [*body, {"event_type": event_type, "payload": dict(payload)}]
    if prospective_normal_terminal is not None:
        if failed_terminal or prospective_6of6_terminal is not None:
            raise V10DiagnosticError("V10 cannot project conflicting terminals")
        body = [
            *body,
            {"event_type": "published", "payload": dict(prospective_normal_terminal)},
        ]
    if any(event.get("event_type") == "failed" for event in body):
        raise V10DiagnosticError("V10 failed event must be the unique final event")
    if failed_terminal:
        failure = events[-1].get("payload")
        if (
            not isinstance(failure, Mapping)
            or failure.get("status") != "consumed_archive_no_rerun"
            or not isinstance(failure.get("error_type"), str)
            or not isinstance(failure.get("error_message"), str)
        ):
            raise V10DiagnosticError("V10 failed terminal payload is invalid")

    def _valid_failed_prefix(index: int) -> bool:
        return failed_terminal and index == len(body)

    def _validate_rfc3339z(value: Any, *, field_name: str) -> None:
        if not isinstance(value, str):
            raise V10DiagnosticError(f"V10 {field_name} is not an RFC3339 UTC string")
        try:
            parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ").replace(
                tzinfo=timezone.utc
            )
        except ValueError as exc:
            raise V10DiagnosticError(
                f"V10 {field_name} is not an RFC3339 UTC string"
            ) from exc
        if _validate_timestamp(parsed) != value:
            raise V10DiagnosticError(f"V10 {field_name} is not canonical RFC3339 UTC")

    def _is_lower_hex(value: Any, length: int) -> bool:
        return (
            isinstance(value, str)
            and len(value) == length
            and all(character in "0123456789abcdef" for character in value)
        )

    def _matches_relocated_artifact(value: Any, expected: Path) -> bool:
        """Bind a copied artifact by its fixed output directory and filename."""

        if not isinstance(value, str) or not value:
            return False
        recorded = Path(value)
        return (
            recorded.name == expected.name
            and recorded.parent.name == expected.parent.name
        )

    def _load_bound_claim(
        *,
        require_preflight: bool = True,
    ) -> tuple[Path, Mapping[str, Any], str]:
        claim_path = V10ArtifactPaths.in_directory(path.parent).claim
        try:
            claim_bytes = claim_path.read_bytes()
            claim = json.loads(claim_bytes.decode("utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise V10DiagnosticError("V10 fixed claim artifact is invalid") from exc
        if not isinstance(claim, Mapping) or claim_bytes != (
            _canonical_json_bytes(claim) + b"\n"
        ):
            raise V10DiagnosticError("V10 fixed claim artifact is not canonical")
        expected_claim_keys = {
            "analysis_plan",
            "code_commit",
            "command",
            "configuration",
            "data",
            "experiment_id",
            "model_version",
            "references",
            "runtime",
            "seed",
            "started_at_utc",
            "status",
        }
        claimed = body[0].get("payload") if body else None
        if not isinstance(claimed, Mapping):
            raise V10DiagnosticError("V10 fixed claim lacks its claimed event")
        preflight: Mapping[str, Any] | None = None
        if len(body) > 1 and body[1].get("event_type") == "preflight_passed":
            raw_preflight = body[1].get("payload")
            if not isinstance(raw_preflight, Mapping):
                raise V10DiagnosticError("V10 fixed claim preflight is invalid")
            preflight = raw_preflight
        elif require_preflight:
            raise V10DiagnosticError("V10 fixed claim lacks its preflight binding")
        claim_sha = sha256(claim_bytes).hexdigest()
        _validate_rfc3339z(
            claim.get("started_at_utc"),
            field_name="claim artifact timestamp",
        )
        if (
            set(claim) != expected_claim_keys
            or claim_sha != claimed.get("claim_sha256")
            or claim.get("code_commit") != claimed.get("code_commit")
            or claim.get("started_at_utc") != claimed.get("started_at_utc")
            or not isinstance(claim.get("command"), str)
            or not claim.get("command")
            or claim.get("experiment_id") != EXPERIMENT_ID
            or claim.get("model_version") != MODEL_VERSION
            or claim.get("seed") != 649
            or claim.get("status") != "historical_diagnostic_claimed"
            or (
                preflight is not None
                and (
                    claim.get("configuration") != preflight.get("configuration")
                    or claim.get("data") != preflight.get("data")
                    or claim.get("references") != preflight.get("references")
                    or claim.get("runtime") != preflight.get("runtime")
                )
            )
        ):
            raise V10DiagnosticError("V10 fixed claim binding is invalid")
        return claim_path, claim, claim_sha

    opening = ("claimed", "preflight_passed", "scoring_started")
    index = 0
    for expected_type in opening:
        if _valid_failed_prefix(index):
            _load_bound_claim(require_preflight=index >= 2)
            return events
        if index >= len(body) or body[index].get("event_type") != expected_type:
            raise V10DiagnosticError("V10 ledger opening state sequence is invalid")
        payload = body[index].get("payload")
        if not isinstance(payload, Mapping):
            raise V10DiagnosticError("V10 ledger opening payload is invalid")
        if expected_type == "claimed":
            _validate_rfc3339z(payload.get("started_at_utc"), field_name="claim timestamp")
            code_commit = payload.get("code_commit")
            claim_sha = payload.get("claim_sha256")
            if not _is_lower_hex(code_commit, 40) or not _is_lower_hex(claim_sha, 64):
                raise V10DiagnosticError("V10 claimed Git/SHA identity is invalid")
        index += 1

    _load_bound_claim()

    scoring_started = body[2]["payload"]
    if scoring_started.get("expected_targets") != expected_targets:
        raise V10DiagnosticError("V10 scoring_started target count is invalid")
    target_dates: list[str] = []
    last_forecast_sha: str | None = None
    last_target: str | None = None
    last_candidate_score: Mapping[str, Any] | None = None
    last_actual: tuple[int, ...] | None = None
    last_forecast_payload: Mapping[str, Any] | None = None
    last_target_scores: Mapping[str, Mapping[str, Any]] | None = None
    previous_maximum = 0
    replayed_results: dict[str, list[dict[str, Any]]] = {
        model_name: [] for model_name in MODEL_ORDER
    }
    replayed_per_target: list[dict[str, Any]] = []
    replayed_record_ledger: list[dict[str, Any]] = []
    derived_notification_warnings: list[str] = []
    while index < len(body) and body[index].get("event_type") == "prediction_frozen":
        frozen = body[index].get("payload")
        if not isinstance(frozen, Mapping):
            raise V10DiagnosticError("V10 prediction_frozen payload is invalid")
        target = frozen.get("target_date")
        forecast_sha = frozen.get("forecast_sha256")
        if not isinstance(target, str) or not isinstance(forecast_sha, str):
            raise V10DiagnosticError("V10 frozen target/digest is missing")
        try:
            target_date = date.fromisoformat(target)
        except ValueError as exc:
            raise V10DiagnosticError("V10 frozen target date is invalid") from exc
        forecast_payload = frozen.get("forecast_payload")
        if not isinstance(forecast_payload, Mapping):
            raise V10DiagnosticError("V10 frozen forecast payload is missing")
        raw_forecasts = forecast_payload.get("forecasts")
        if not isinstance(raw_forecasts, Mapping) or set(raw_forecasts) != set(
            MODEL_ORDER
        ):
            raise V10DiagnosticError("V10 frozen model identity is invalid")
        ordered_forecast_payload = dict(forecast_payload)
        ordered_forecast_payload["forecasts"] = {
            model_name: raw_forecasts[model_name] for model_name in MODEL_ORDER
        }
        validated_payload = _validate_forecast_payload(
            ordered_forecast_payload,
            target_date=target_date,
        )
        expected_forecast_sha = sha256(
            _canonical_json_bytes(validated_payload)
        ).hexdigest()
        if forecast_sha != expected_forecast_sha:
            raise V10DiagnosticError("V10 frozen forecast payload digest mismatch")
        _validate_rfc3339z(
            frozen.get("prediction_frozen_at_utc"),
            field_name="prediction timestamp",
        )
        index += 1
        if _valid_failed_prefix(index):
            return events
        if index >= len(body) or body[index].get("event_type") != (
            "target_revealed_scored"
        ):
            raise V10DiagnosticError("V10 frozen prediction lacks its next scored event")
        scored = body[index].get("payload")
        if not isinstance(scored, Mapping):
            raise V10DiagnosticError("V10 target_revealed_scored payload is invalid")
        if scored.get("target_date") != target or scored.get("forecast_sha256") != (
            forecast_sha
        ):
            raise V10DiagnosticError("V10 freeze/score target or digest pairing mismatch")
        actual = _as_actual_main(scored.get("actual_main", ()))
        recorded_scores = scored.get("scores")
        forecasts = validated_payload["forecasts"]
        if (
            not isinstance(recorded_scores, Mapping)
            or set(recorded_scores) != set(MODEL_ORDER)
        ):
            raise V10DiagnosticError("V10 scored model order/identity is invalid")
        expected_scores: dict[str, dict[str, Any]] = {}
        full_scores: dict[str, dict[str, Any]] = {}
        for model_name in MODEL_ORDER:
            recalculated = score_probability_forecast(forecasts[model_name], actual)
            recalculated["joint_log_gain"] = (
                _joint_gain_from_payload(forecasts[model_name], actual)
                if model_name in (CANDIDATE_MODEL, TARGETED_CONTROL_MODEL)
                else None
            )
            full_scores[model_name] = recalculated
            expected_scores[model_name] = _public_score(recalculated)
            if _canonical_json_bytes(recorded_scores[model_name]) != (
                _canonical_json_bytes(expected_scores[model_name])
            ):
                raise V10DiagnosticError("V10 recorded score does not recompute")
        candidate_score = expected_scores[CANDIDATE_MODEL]
        current_hits = int(candidate_score["final6_hits"])
        expected_record = {
            "target_date": target,
            "previous_maximum_final6_hits": previous_maximum,
            "current_final6_hits": current_hits,
            "new_maximum_final6_hits": max(previous_maximum, current_hits),
            "new_within_run_record": current_hits > previous_maximum,
            "prediction": list(forecasts[CANDIDATE_MODEL]["final6"]),
            "actual": list(actual),
            "forecast_sha256": forecast_sha,
        }
        if _canonical_json_bytes(scored.get("progressive_record", {})) != (
            _canonical_json_bytes(expected_record)
        ):
            raise V10DiagnosticError("V10 progressive record does not recompute")
        for model_name in MODEL_ORDER:
            replayed_results[model_name].append(full_scores[model_name])
        replayed_record_ledger.append(expected_record)
        replayed_per_target.append(
            {
                "target_date": target,
                "forecast_payload": validated_payload,
                "forecast_sha256": forecast_sha,
                "actual_main": list(actual),
                "scores": expected_scores,
                "progressive_record": expected_record,
            }
        )
        previous_maximum = max(previous_maximum, current_hits)
        target_dates.append(target)
        last_forecast_sha = forecast_sha
        last_target = target
        last_candidate_score = candidate_score
        last_actual = actual
        last_forecast_payload = validated_payload
        last_target_scores = full_scores
        index += 1
        if current_hits == 6:
            break
        for kind, subject, notification_body in _progress_notification_requests(
            forecast_payload=validated_payload,
            actual=actual,
            target_date=target,
            candidate_score=candidate_score,
            progressive_record=expected_record,
        ):
            if _valid_failed_prefix(index):
                return events
            if index >= len(body) or body[index].get("event_type") != (
                "progress_notification_outbox"
            ):
                raise V10DiagnosticError(
                    "V10 score lacks its required progress notification outbox"
                )
            progress_payload = body[index].get("payload")
            if (
                not isinstance(progress_payload, Mapping)
                or set(progress_payload)
                != {
                    "email_dispatched",
                    "forecast_sha256",
                    "kind",
                    "notification_idempotency_key",
                    "notification_request",
                    "notification_required",
                    "notification_status",
                    "notification_warnings",
                    "notification_warnings_before_terminal",
                    "subject",
                    "target_date",
                }
                or progress_payload.get("kind") != kind
                or progress_payload.get("target_date") != target
                or progress_payload.get("forecast_sha256") != forecast_sha
            ):
                raise V10DiagnosticError(
                    "V10 progress notification outbox identity is invalid"
                )
            _validate_notification_outbox(
                progress_payload,
                warnings_before=derived_notification_warnings,
                notification_required=True,
                expected_subject=subject,
                expected_body=notification_body,
                idempotency_context=_progress_notification_context(
                    code_commit=body[0]["payload"]["code_commit"],
                    kind=kind,
                    target_date=target,
                    forecast_sha256=forecast_sha,
                ),
                error_message="V10 progress notification outbox is invalid",
            )
            derived_notification_warnings = list(
                progress_payload["notification_warnings"]
            )
            index += 1
    if target_dates != sorted(target_dates) or len(set(target_dates)) != len(target_dates):
        raise V10DiagnosticError("V10 ledger scored targets are not strictly unique")
    if _valid_failed_prefix(index):
        return events
    if index >= len(body):
        raise V10DiagnosticError("V10 ledger has no terminal/publishing state")

    next_type = body[index].get("event_type")
    if next_type == "historical_6of6_candidate_detected":
        if not target_dates:
            raise V10DiagnosticError("V10 6/6 candidate has no scored target")
        detected = body[index].get("payload")
        if not isinstance(detected, Mapping) or (
            detected.get("target_date") != last_target
            or detected.get("forecast_sha256") != last_forecast_sha
        ):
            raise V10DiagnosticError("V10 6/6 detection does not bind the last score")
        if last_candidate_score is None or last_candidate_score.get("final6_hits") != 6:
            raise V10DiagnosticError("V10 6/6 detection lacks a final-six 6/6 score")
        index += 1
        if _valid_failed_prefix(index):
            return events
        if index >= len(body) or body[index].get("event_type") != (
            "historical_6of6_leakage_audit_completed"
        ):
            raise V10DiagnosticError("V10 6/6 detection lacks its leakage audit")
        audit_event = body[index].get("payload")
        if not isinstance(audit_event, Mapping) or audit_event.get("target_date") != (
            last_target
        ):
            raise V10DiagnosticError("V10 6/6 leakage audit target mismatch")
        index += 1
        if _valid_failed_prefix(index):
            return events
        if index == len(body) and allow_6of6_audit_prefix:
            return events
        if index >= len(body):
            raise V10DiagnosticError("V10 6/6 audit lacks its dedicated terminal")
        terminal_type = body[index].get("event_type")
        if terminal_type not in {
            "historical_6of6_candidate_published",
            "historical_6of6_candidate_archived_leakage_failed",
        }:
            raise V10DiagnosticError("V10 6/6 terminal state is invalid")
        audit = audit_event.get("audit")
        audit_clear = _derived_6of6_audit_clear(audit)
        if audit_clear != (terminal_type == "historical_6of6_candidate_published"):
            raise V10DiagnosticError("V10 6/6 audit result and terminal disagree")
        terminal_payload = body[index].get("payload")
        if not isinstance(terminal_payload, Mapping):
            raise V10DiagnosticError("V10 6/6 terminal payload is invalid")
        expected_bundle_path = path.parent / (
            f"historical-6of6-candidate__{last_target}__v10.0.0.json"
        )
        if not _matches_relocated_artifact(
            terminal_payload.get("bundle_path"),
            expected_bundle_path,
        ):
            raise V10DiagnosticError("V10 6/6 terminal bundle path is invalid")
        if not expected_bundle_path.is_file() or terminal_payload.get(
            "bundle_sha256"
        ) != _file_sha256(expected_bundle_path):
            raise V10DiagnosticError("V10 6/6 terminal bundle digest is invalid")
        try:
            bundle = json.loads(expected_bundle_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise V10DiagnosticError("V10 6/6 published bundle is invalid") from exc
        if not isinstance(bundle, Mapping):
            raise V10DiagnosticError("V10 6/6 published bundle is not an object")
        preflight_payload = body[1]["payload"]
        data_evidence = preflight_payload.get("data")
        if not isinstance(data_evidence, Mapping):
            raise V10DiagnosticError("V10 6/6 preflight data evidence is missing")
        expected_source_commit = data_evidence.get("source_commit")
        expected_registration_commit = preflight_payload.get("registration_commit")
        if not _is_lower_hex(expected_source_commit, 40) or not _is_lower_hex(
            expected_registration_commit,
            40,
        ):
            raise V10DiagnosticError("V10 6/6 source/registration commit is invalid")
        expected_claim_path, _bound_claim_payload, bound_claim_sha = _load_bound_claim()
        claim_evidence = bundle.get("claim")
        expected_bundle_keys = {
            "actual",
            "claim",
            "evidence_lane",
            "experiment_id",
            "feature_identity",
            "forecast_payload",
            "forecast_sha256",
            "implementation_commit",
            "leakage_audit",
            "ledger",
            "model_name",
            "model_version",
            "normal_621_report",
            "parameters",
            "prediction",
            "registration_commit",
            "runtime",
            "schema_version",
            "scored_targets_before_stop",
            "seed",
            "source_commit",
            "status",
            "target_date",
            "training_cutoff",
        }
        if (
            last_actual is None
            or last_forecast_payload is None
            or set(bundle) != expected_bundle_keys
            or bundle.get("schema_version") != 1
            or bundle.get("status") != "historical-6of6-candidate"
            or bundle.get("experiment_id") != EXPERIMENT_ID
            or bundle.get("model_name") != CANDIDATE_MODEL
            or bundle.get("model_version") != MODEL_VERSION
            or bundle.get("feature_identity") != "sorted_main_gap_exactly_one"
            or bundle.get("seed") != 649
            or bundle.get("evidence_lane") != "consumed_historical_diagnostic"
            or bundle.get("target_date") != last_target
            or bundle.get("training_cutoff")
            != last_forecast_payload["prefix"].get("history_through")
            or bundle.get("forecast_sha256") != last_forecast_sha
            or bundle.get("forecast_payload") != last_forecast_payload
            or bundle.get("actual") != list(last_actual)
            or bundle.get("prediction")
            != list(last_forecast_payload["forecasts"][CANDIDATE_MODEL]["final6"])
            or bundle.get("leakage_audit") != audit
            or bundle.get("source_commit") != expected_source_commit
            or bundle.get("registration_commit") != expected_registration_commit
            or bundle.get("implementation_commit") != body[0]["payload"].get(
                "code_commit"
            )
            or bundle.get("parameters") != preflight_payload.get(
                "registered_parameters"
            )
            or bundle.get("runtime") != preflight_payload.get("runtime")
            or not isinstance(claim_evidence, Mapping)
            or set(claim_evidence) != {"path", "sha256"}
                or not _matches_relocated_artifact(
                    claim_evidence.get("path"),
                    expected_claim_path,
                )
            or claim_evidence.get("sha256") != bound_claim_sha
            or claim_evidence.get("sha256")
            != body[0]["payload"].get("claim_sha256")
            or bundle.get("scored_targets_before_stop") != len(target_dates)
            or bundle.get("normal_621_report") != "prohibited_after_early_stop"
        ):
            raise V10DiagnosticError("V10 6/6 bundle evidence binding is invalid")
        bundle_ledger = bundle.get("ledger")
        if (
            not isinstance(bundle_ledger, Mapping)
                or not _matches_relocated_artifact(bundle_ledger.get("path"), path)
            or bundle_ledger.get("head_sha256_before_bundle")
            != body[index - 1].get("event_sha256")
            or bundle_ledger.get("event_count_before_bundle") != index
        ):
            raise V10DiagnosticError("V10 6/6 bundle ledger binding is invalid")
        expected_subject = (
            "🚨 [LOTTO649] 历史严格回测成功预测 6/6"
            if audit_clear
            else "⚠️ [LOTTO649] 历史 6/6 候选泄漏审计失败"
        )
        if (
            set(terminal_payload)
            != {
                "bundle_path",
                "bundle_sha256",
                "email_dispatched",
                "notification_idempotency_key",
                "notification_request",
                "notification_required",
                "notification_status",
                "notification_warnings",
                "notification_warnings_before_terminal",
                "scored_targets",
                "subject",
                "target_date",
            }
            or last_target_scores is None
            or terminal_payload.get("target_date") != last_target
            or terminal_payload.get("scored_targets") != len(target_dates)
        ):
            raise V10DiagnosticError("V10 6/6 terminal notification is invalid")
        _validate_notification_outbox(
            terminal_payload,
            warnings_before=derived_notification_warnings,
            notification_required=True,
            expected_subject=expected_subject,
            expected_body=_six_of_six_notification_body(
                forecast_payload=last_forecast_payload,
                actual=last_actual,
                target_date=last_target,
                code_commit=body[0]["payload"]["code_commit"],
                audit_clear=audit_clear,
                target_scores=last_target_scores,
                scored_targets=len(target_dates),
            ),
            idempotency_context={
                "bundle_sha256": terminal_payload["bundle_sha256"],
                "code_commit": body[0]["payload"]["code_commit"],
                "event_type": terminal_type,
                "experiment_id": EXPERIMENT_ID,
                "target_date": last_target,
            },
            error_message="V10 6/6 terminal notification is invalid",
        )
        index += 1
        if index != len(body) or failed_terminal:
            raise V10DiagnosticError("V10 6/6 terminal has forbidden later events")
        return events

    if last_candidate_score is not None and last_candidate_score.get("final6_hits") == 6:
        raise V10DiagnosticError("V10 6/6 score lacks its detection event")
    if next_type != "scoring_completed":
        raise V10DiagnosticError("V10 normal ledger lacks scoring_completed")
    if len(target_dates) != expected_targets:
        raise V10DiagnosticError("V10 normal ledger target count is incomplete")
    completed = body[index].get("payload")
    if not isinstance(completed, Mapping) or completed.get("scored_targets") != (
        expected_targets
    ):
        raise V10DiagnosticError("V10 scoring_completed payload is invalid")
    index += 1
    if _valid_failed_prefix(index):
        return events
    if index >= len(body) or body[index].get("event_type") != "publication_started":
        raise V10DiagnosticError("V10 normal ledger lacks publication_started")
    publication = body[index].get("payload")
    expected_artifacts = V10ArtifactPaths.in_directory(path.parent)
    publication_warnings = (
        publication.get("notification_warnings")
        if isinstance(publication, Mapping)
        else None
    )
    if (
        not isinstance(publication, Mapping)
        or set(publication)
        != {
            "notification_warnings",
            "report_json",
            "report_markdown",
            "scored_targets",
        }
        or not isinstance(publication_warnings, list)
        or any(not isinstance(warning, str) for warning in publication_warnings)
        or publication_warnings != derived_notification_warnings
        or publication.get("scored_targets") != expected_targets
        or not _matches_relocated_artifact(
            publication.get("report_json"),
            expected_artifacts.report_json,
        )
        or not _matches_relocated_artifact(
            publication.get("report_markdown"),
            expected_artifacts.report_markdown,
        )
    ):
        raise V10DiagnosticError("V10 publication_started payload is invalid")
    index += 1
    if _valid_failed_prefix(index):
        return events
    if index == len(body) and allow_publication_prefix:
        return events
    if index >= len(body) or body[index].get("event_type") != "published":
        raise V10DiagnosticError("V10 normal ledger lacks published")
    published = body[index].get("payload")
    if not isinstance(published, Mapping):
        raise V10DiagnosticError("V10 published payload is invalid")
    published_warnings = published.get("notification_warnings")
    if (
        set(published)
        != {
            "all_scientific_gates_passed",
            "decision",
            "email_dispatched",
            "gates",
            "json_path",
            "json_sha256",
            "markdown_path",
            "markdown_sha256",
            "notification_idempotency_key",
            "notification_request",
            "notification_required",
            "notification_status",
            "notification_warnings",
            "notification_warnings_before_terminal",
            "scored_targets",
            "subject",
        }
        or not isinstance(published_warnings, list)
        or any(not isinstance(warning, str) for warning in published_warnings)
        or published_warnings[: len(publication_warnings)] != publication_warnings
        or not _matches_relocated_artifact(
            published.get("json_path"),
            expected_artifacts.report_json,
        )
        or not _matches_relocated_artifact(
            published.get("markdown_path"),
            expected_artifacts.report_markdown,
        )
        or published.get("scored_targets") != expected_targets
        or not expected_artifacts.report_json.is_file()
        or not expected_artifacts.report_markdown.is_file()
        or published.get("json_sha256")
        != _file_sha256(expected_artifacts.report_json)
        or published.get("markdown_sha256")
        != _file_sha256(expected_artifacts.report_markdown)
    ):
        raise V10DiagnosticError("V10 published paths/digests are invalid")
    try:
        report = json.loads(expected_artifacts.report_json.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise V10DiagnosticError("V10 published JSON report is invalid") from exc
    if not isinstance(report, Mapping):
        raise V10DiagnosticError("V10 published JSON report is not an object")
    decision = report.get("historical_decision")
    if not isinstance(decision, Mapping):
        raise V10DiagnosticError("V10 published decision is invalid")
    claim_path, claim_payload, claim_sha = _load_bound_claim()
    analysis_plan = claim_payload.get("analysis_plan")
    if not isinstance(analysis_plan, Mapping) or set(analysis_plan) != {
        "bootstrap_replicates",
        "bootstrap_seed",
        "reference",
        "stability_scopes",
    }:
        raise V10DiagnosticError("V10 claimed analysis plan is invalid")
    bootstrap_replicates = analysis_plan.get("bootstrap_replicates")
    bootstrap_seed = analysis_plan.get("bootstrap_seed")
    reference = analysis_plan.get("reference")
    raw_scopes = analysis_plan.get("stability_scopes")
    if (
        type(bootstrap_replicates) is not int
        or bootstrap_replicates < 1
        or bootstrap_seed != 649
        or not isinstance(reference, Mapping)
        or not isinstance(raw_scopes, list)
        or len(raw_scopes) != 2
    ):
        raise V10DiagnosticError("V10 claimed analysis plan values are invalid")
    _canonical_json_bytes(reference)
    stability_scopes: list[V10Scope] = []
    for raw_scope in raw_scopes:
        if not isinstance(raw_scope, Mapping) or set(raw_scope) != {
            "end",
            "name",
            "start",
            "target_count",
        }:
            raise V10DiagnosticError("V10 claimed stability scope is invalid")
        try:
            scope = V10Scope(
                name=raw_scope["name"],
                start=date.fromisoformat(raw_scope["start"]),
                end=date.fromisoformat(raw_scope["end"]),
                target_count=raw_scope["target_count"],
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise V10DiagnosticError("V10 claimed stability scope is invalid") from exc
        if (
            not isinstance(scope.name, str)
            or not scope.name
            or scope.name == "aggregate"
            or type(scope.target_count) is not int
            or scope.target_count < 0
            or scope.start > scope.end
        ):
            raise V10DiagnosticError("V10 claimed stability scope values are invalid")
        stability_scopes.append(scope)
    if len({scope.name for scope in stability_scopes}) != 2 or any(
        sum(scope.contains(date.fromisoformat(target)) for target in target_dates)
        != scope.target_count
        for scope in stability_scopes
    ):
        raise V10DiagnosticError("V10 claimed stability scopes do not match targets")
    if sum(scope.target_count for scope in stability_scopes) != expected_targets:
        raise V10DiagnosticError("V10 claimed stability scopes do not partition targets")
    scientific_sections = _build_scientific_report_sections(
        preflight=body[1]["payload"],
        results=replayed_results,
        per_target=replayed_per_target,
        record_ledger=replayed_record_ledger,
        stability_scopes=stability_scopes,
        bootstrap_replicates=bootstrap_replicates,
        bootstrap_seed=bootstrap_seed,
        reference=reference,
        expected_target_count=expected_targets,
    )
    if any(
        _canonical_json_bytes({key: report.get(key)})
        != _canonical_json_bytes({key: expected_value})
        for key, expected_value in scientific_sections.items()
    ):
        raise V10DiagnosticError(
            "V10 published scientific report does not replay from scored events"
        )
    expected_report = _assemble_normal_report(
        output_dir=path.parent,
        code_commit=body[0]["payload"]["code_commit"],
        exact_command=claim_payload["command"],
        claim_payload=claim_payload,
        claim_sha256=claim_sha,
        ledger_path=path,
        ledger_event_count=index,
        ledger_head_sha256=body[index - 1]["event_sha256"],
        preflight=body[1]["payload"],
        expected_target_count=expected_targets,
        target_dates=target_dates,
        scientific_sections=scientific_sections,
        notification_warnings=publication_warnings,
    )
    report_claim = report.get("one_shot_claim")
    report_ledger = report.get("attempt_ledger")
    if (
        not isinstance(report_claim, Mapping)
        or not _matches_relocated_artifact(report_claim.get("path"), claim_path)
        or not isinstance(report_ledger, Mapping)
        or not _matches_relocated_artifact(report_ledger.get("path"), path)
    ):
        raise V10DiagnosticError("V10 published report artifact paths are invalid")
    expected_report["one_shot_claim"]["path"] = report_claim["path"]
    expected_report["attempt_ledger"]["path"] = report_ledger["path"]
    if _canonical_json_bytes(report) != _canonical_json_bytes(expected_report):
        raise V10DiagnosticError("V10 published report template does not replay")
    try:
        markdown_bytes = expected_artifacts.report_markdown.read_bytes()
    except OSError as exc:
        raise V10DiagnosticError("V10 published Markdown report is unreadable") from exc
    if markdown_bytes != _render_markdown(expected_report).encode("utf-8"):
        raise V10DiagnosticError("V10 published Markdown does not render from JSON")
    if (
        not isinstance(report_claim, Mapping)
        or set(report_claim)
        != {
            "created_before_first_forecast_and_score",
            "path",
            "payload",
            "retention",
            "sha256",
        }
        or not _matches_relocated_artifact(report_claim.get("path"), claim_path)
        or report_claim.get("sha256") != claim_sha
        or report_claim.get("payload") != claim_payload
        or report_claim.get("created_before_first_forecast_and_score") is not True
        or report_claim.get("retention") != "permanent_success_or_failure"
    ):
        raise V10DiagnosticError("V10 published report claim binding is invalid")
    gates = decision.get("gates")
    if not isinstance(gates, Mapping) or set(gates) != HISTORICAL_GATE_NAMES:
        raise V10DiagnosticError("V10 published gates are invalid")
    if any(type(value) is not bool for value in gates.values()):
        raise V10DiagnosticError("V10 published gates are invalid")
    all_gates_passed = all(gates.values())
    expected_decision = (
        "eligible_for_separate_reviewed_shadow_decision"
        if all_gates_passed
        else "reject"
    )
    if (
        decision.get("all_scientific_gates_passed") is not all_gates_passed
        or decision.get("decision") != expected_decision
        or published.get("decision") != expected_decision
        or published.get("all_scientific_gates_passed") is not all_gates_passed
        or published.get("gates") != gates
        or report.get("code_commit") != body[0]["payload"].get("code_commit")
        or report.get("command") != claim_payload.get("command")
        or report.get("preflight") != body[1]["payload"]
        or report.get("historical_lane")
        != {
            "name": "consumed_historical_diagnostic",
            "target_count": expected_targets,
            "target_dates": target_dates,
            "excluded": [
                "1982-01-01..2019-12-31:training_prefix_only",
                "2026-01-01..2026-08-15:known_outcomes_excluded",
            ],
        }
        or report.get("notification_status_at_report_publication")
        != "pending_post_publication"
        or report.get("notification_result_authority")
        != "external_workflow_receipt_after_terminal"
        or not isinstance(report_ledger, Mapping)
        or not _matches_relocated_artifact(report_ledger.get("path"), path)
        or report_ledger.get("event_count_at_report") != index
        or report_ledger.get("head_sha256_at_report")
        != body[index - 1].get("event_sha256")
    ):
        raise V10DiagnosticError("V10 published report/event binding is invalid")
    expected_subject = (
        "[LOTTO649] 【历史严格回测】V10全部统计门槛通过"
        if all_gates_passed
        else None
    )
    _validate_notification_outbox(
        published,
        warnings_before=publication_warnings,
        notification_required=all_gates_passed,
        expected_subject=expected_subject,
        expected_body=(
            _normal_pass_notification_body() if all_gates_passed else None
        ),
        idempotency_context={
            "code_commit": body[0]["payload"]["code_commit"],
            "event_type": "published",
            "experiment_id": EXPERIMENT_ID,
            "json_sha256": published["json_sha256"],
            "markdown_sha256": published["markdown_sha256"],
        },
        error_message="V10 published notification receipt is invalid",
    )
    index += 1
    if index != len(body) or failed_terminal:
        raise V10DiagnosticError("V10 normal terminal has duplicate/later events")
    return events


@dataclass(frozen=True)
class V10Scope:
    """One frozen target-date scope used by the historical decision."""

    name: str
    start: date
    end: date
    target_count: int

    def contains(self, target_date: date) -> bool:
        return self.start <= target_date <= self.end


@dataclass(frozen=True)
class V10TargetPlan:
    """A reveal-gated target supplied to the one-shot state machine.

    ``build_forecasts`` may use only the already-revealed strict prefix.
    ``reveal_actual`` is deliberately a separate callback and is not invoked
    until the corresponding ``prediction_frozen`` event has been fsynced.
    """

    target_date: date
    build_forecasts: Callable[[], Mapping[str, Any]]
    reveal_actual: Callable[[], Sequence[int]]


@dataclass(frozen=True)
class V10ArtifactPaths:
    claim: Path
    ledger: Path
    report_json: Path
    report_markdown: Path
    report_json_staging: Path
    report_markdown_staging: Path

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
        )

    def normal_paths(self) -> tuple[Path, ...]:
        return (
            self.claim,
            self.ledger,
            self.report_json,
            self.report_markdown,
            self.report_json_staging,
            self.report_markdown_staging,
        )


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _never_notify(_subject: str, _body: str) -> bool:
    return False


@dataclass(frozen=True)
class V10DiagnosticRequest:
    """All dependencies for one consumed V10 diagnostic attempt.

    Production supplies the frozen 621 targets. Tests supply synthetic targets
    and explicit smaller scopes, so state-machine behavior can be exercised
    without opening or scoring the registered historical outcomes.
    """

    root: Path
    output_dir: Path
    code_commit: str
    exact_command: str
    targets: Sequence[V10TargetPlan]
    preflight: Callable[[], Mapping[str, Any]]
    reference: Mapping[str, Any]
    expected_target_count: int = 621
    stability_scopes: tuple[V10Scope, V10Scope] = (
        V10Scope("first_307", date(2020, 1, 1), date(2022, 12, 31), 307),
        V10Scope("second_314", date(2023, 1, 1), date(2025, 12, 31), 314),
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
            "reason": "no leakage audit dependency supplied",
        },
        compare=False,
        repr=False,
    )
    clock: Clock = field(default=_utc_now, compare=False, repr=False)


def _as_actual_main(actual_main: Sequence[int]) -> tuple[int, ...]:
    actual = tuple(actual_main)
    if len(actual) != 6 or len(set(actual)) != 6:
        raise V10DiagnosticError("actual main set must contain six distinct labels")
    if any(type(number) is not int or not 1 <= number <= 49 for number in actual):
        raise V10DiagnosticError("actual main labels must be integers in 1..49")
    return tuple(sorted(actual))


def _probability_vector(forecast: Mapping[str, Any]) -> tuple[float, ...]:
    raw = forecast.get("probabilities")
    if isinstance(raw, Mapping):
        if set(raw) != {str(number) for number in range(1, 50)}:
            raise V10DiagnosticError("forecast probability keys must be labels 1..49")
        values = tuple(raw[str(number)] for number in range(1, 50))
    elif isinstance(raw, (list, tuple)):
        values = tuple(raw)
    else:
        raise V10DiagnosticError("forecast probabilities are missing")
    if len(values) != 49 or any(type(value) not in (int, float) for value in values):
        raise V10DiagnosticError("forecast must contain 49 numeric probabilities")
    probabilities = tuple(float(value) for value in values)
    if not all(math.isfinite(value) and 0.0 < value < 1.0 for value in probabilities):
        raise V10DiagnosticError("forecast probabilities must be finite and in (0,1)")
    if abs(math.fsum(probabilities) - 6.0) > 1.0e-12:
        raise V10DiagnosticError("forecast probabilities must sum to six")
    return probabilities


def _ranking_vector(forecast: Mapping[str, Any], probabilities: tuple[float, ...]) -> tuple[int, ...]:
    raw = forecast.get("ranking")
    if not isinstance(raw, (list, tuple)):
        raise V10DiagnosticError("forecast full ranking is missing")
    ranking = tuple(raw)
    if len(ranking) != 49 or sorted(ranking) != list(range(1, 50)):
        raise V10DiagnosticError("forecast ranking must be a permutation of 1..49")
    expected = tuple(
        sorted(range(1, 50), key=lambda number: (-probabilities[number - 1], number))
    )
    if ranking != expected:
        raise V10DiagnosticError("forecast ranking violates probability/tie ordering")
    for key, size in (("top6", 6), ("top12", 12), ("top18", 18)):
        raw_top = forecast.get(key)
        if not isinstance(raw_top, (list, tuple)) or tuple(raw_top) != ranking[:size]:
            raise V10DiagnosticError(f"forecast {key} differs from the full ranking")
    raw_final = forecast.get("final6")
    if not isinstance(raw_final, (list, tuple)) or tuple(raw_final) != tuple(
        sorted(ranking[:6])
    ):
        raise V10DiagnosticError("forecast final6 must be sorted marginal Top-6")
    return ranking


def score_probability_forecast(
    forecast: Mapping[str, Any],
    actual_main: Sequence[int],
) -> dict[str, Any]:
    """Score one already-frozen 49-label forecast against a revealed set."""

    actual = _as_actual_main(actual_main)
    probabilities = _probability_vector(forecast)
    ranking = _ranking_vector(forecast, probabilities)
    actual_set = set(actual)
    ranks = {number: rank for rank, number in enumerate(ranking, start=1)}
    actual_ranks = [ranks[number] for number in actual]
    top6 = tuple(forecast["top6"])
    top12 = tuple(forecast["top12"])
    top18 = tuple(forecast["top18"])
    final6 = tuple(forecast["final6"])
    brier_terms = []
    log_terms = []
    for number, probability in enumerate(probabilities, start=1):
        observed = 1.0 if number in actual_set else 0.0
        brier_terms.append((probability - observed) ** 2)
        log_terms.append(
            -math.log(probability) if observed else -math.log(1.0 - probability)
        )
    target_date = forecast.get("target_date")
    if target_date is not None and not isinstance(target_date, str):
        raise V10DiagnosticError("forecast target_date must be an ISO string")
    return {
        "target_date": target_date,
        "model_name": forecast.get("model_name"),
        "model_version": forecast.get("model_version"),
        "actual": list(actual),
        "actual_ranks": actual_ranks,
        "mean_actual_rank": math.fsum(actual_ranks) / 6.0,
        "top6_hits": len(set(top6) & actual_set),
        "top12_hits": len(set(top12) & actual_set),
        "top18_hits": len(set(top18) & actual_set),
        "final6_hits": len(set(final6) & actual_set),
        "matched_final": sorted(set(final6) & actual_set),
        "brier_score": math.fsum(brier_terms) / 49.0,
        "log_loss": math.fsum(log_terms) / 49.0,
        "probabilities": list(probabilities),
    }


def _single_draw_top12_integer_coefficients() -> tuple[int, ...]:
    return tuple(
        math.comb(12, hits) * math.comb(37, 6 - hits)
        for hits in range(7)
    )


@lru_cache(maxsize=None)
def _exact_top12_integer_distribution(draw_count: int) -> tuple[int, ...]:
    """Return exact coefficients of the D-fold Top-12 hit polynomial."""

    if type(draw_count) is not int or draw_count < 1:
        raise V10DiagnosticError("exact Top-12 test requires a positive draw count")
    one_draw = _single_draw_top12_integer_coefficients()
    distribution = (1,)
    for _ in range(draw_count):
        updated = [0] * (len(distribution) + 6)
        for prior_hits, prior_count in enumerate(distribution):
            for draw_hits, draw_count_coefficient in enumerate(one_draw):
                updated[prior_hits + draw_hits] += (
                    prior_count * draw_count_coefficient
                )
        distribution = tuple(updated)
    return distribution


def exact_top12_upper_tail(total_hits: int, draw_count: int) -> float:
    """Exact draw-level convolution under Hypergeometric(49,12,6)."""

    if type(draw_count) is not int or draw_count < 1:
        raise V10DiagnosticError("exact Top-12 test requires a positive draw count")
    if type(total_hits) is not int or not 0 <= total_hits <= 6 * draw_count:
        raise V10DiagnosticError("exact Top-12 total hits are out of range")
    distribution = _exact_top12_integer_distribution(draw_count)
    numerator = sum(distribution[total_hits:])
    denominator = math.comb(49, 6) ** draw_count
    # CPython performs correctly scaled big-int true division here. No
    # probability enters the convolution; binary64 conversion happens once,
    # after the exact integer upper-tail numerator has been formed.
    return numerator / denominator


def _bootstrap_interval(
    values: Sequence[float],
    *,
    expectation: float,
    replicates: int,
    seed: int,
) -> list[float]:
    array = np.asarray(values, dtype=float)
    if array.ndim != 1 or len(array) == 0 or not np.isfinite(array).all():
        raise V10DiagnosticError("bootstrap requires a finite non-empty vector")
    if type(replicates) is not int or replicates < 1 or type(seed) is not int:
        raise V10DiagnosticError("bootstrap replicates/seed are invalid")
    rng = np.random.default_rng(seed)
    draws = np.empty(replicates, dtype=float)
    chunk_size = 256
    for start in range(0, replicates, chunk_size):
        stop = min(start + chunk_size, replicates)
        indices = rng.integers(0, len(array), size=(stop - start, len(array)))
        draws[start:stop] = array[indices].mean(axis=1) - expectation
    lower, upper = np.quantile(draws, [0.025, 0.975], method="linear")
    return [float(lower), float(upper)]


def _fair_constant_scores() -> tuple[float, float]:
    brier = (
        6 * (1.0 - FAIR_PROBABILITY) ** 2 + 43 * FAIR_PROBABILITY**2
    ) / 49.0
    log_loss = -(
        6 * math.log(FAIR_PROBABILITY)
        + 43 * math.log(1.0 - FAIR_PROBABILITY)
    ) / 49.0
    return brier, log_loss


def _calibration(scores: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    cells: list[list[tuple[float, int]]] = [[] for _ in range(10)]
    for score in scores:
        actual = set(_as_actual_main(score["actual"]))
        probabilities = tuple(float(value) for value in score["probabilities"])
        if len(probabilities) != 49:
            raise V10DiagnosticError("calibration score lacks 49 probabilities")
        for number, probability in enumerate(probabilities, start=1):
            index = min(9, int(probability * 10.0))
            cells[index].append((probability, int(number in actual)))
    total_cells = len(scores) * 49
    bins = []
    weighted_errors = []
    for index, bin_cells in enumerate(cells):
        if bin_cells:
            mean_forecast = math.fsum(item[0] for item in bin_cells) / len(bin_cells)
            observed_rate = math.fsum(item[1] for item in bin_cells) / len(bin_cells)
            weighted_errors.append(
                len(bin_cells) * abs(mean_forecast - observed_rate)
            )
        else:
            mean_forecast = None
            observed_rate = None
        bins.append(
            {
                "bin": index,
                "lower": index / 10.0,
                "upper": (index + 1) / 10.0,
                "right_closed": index == 9,
                "cell_count": len(bin_cells),
                "mean_forecast": mean_forecast,
                "observed_inclusion_rate": observed_rate,
            }
        )
    return {
        "bins": bins,
        "expected_calibration_error": math.fsum(weighted_errors) / total_cells,
    }


def summarize_v10_scope(
    scores: Sequence[Mapping[str, Any]],
    *,
    scope: str,
    bootstrap_replicates: int = 10_000,
    bootstrap_seed: int = 649,
) -> dict[str, Any]:
    """Return every registered bounded metric for one model/scope."""

    rows = list(scores)
    if not rows:
        raise V10DiagnosticError("V10 scope summary requires at least one score")
    required = {
        "top6_hits",
        "top12_hits",
        "top18_hits",
        "final6_hits",
        "mean_actual_rank",
        "brier_score",
        "log_loss",
        "actual",
        "probabilities",
    }
    if any(not required <= set(row) for row in rows):
        raise V10DiagnosticError("V10 score row is incomplete")
    top6 = [int(row["top6_hits"]) for row in rows]
    top12 = [int(row["top12_hits"]) for row in rows]
    top18 = [int(row["top18_hits"]) for row in rows]
    final6 = [int(row["final6_hits"]) for row in rows]
    if any(not 0 <= value <= 6 for values in (top6, top12, top18, final6) for value in values):
        raise V10DiagnosticError("V10 hit count is outside 0..6")
    if any(a > b or b > c for a, b, c in zip(top6, top12, top18)):
        raise V10DiagnosticError("V10 Top-K hits violate nesting")
    fair_brier, fair_log_loss = _fair_constant_scores()
    draws = len(rows)
    averages = {
        "avg_top6_hits": math.fsum(top6) / draws,
        "avg_top12_hits": math.fsum(top12) / draws,
        "avg_top18_hits": math.fsum(top18) / draws,
        "avg_actual_rank": math.fsum(float(row["mean_actual_rank"]) for row in rows)
        / draws,
        "avg_brier": math.fsum(float(row["brier_score"]) for row in rows) / draws,
        "avg_log_loss": math.fsum(float(row["log_loss"]) for row in rows) / draws,
    }
    years: dict[str, list[Mapping[str, Any]]] = {}
    for row in rows:
        target = row.get("target_date")
        if isinstance(target, str):
            try:
                year = str(date.fromisoformat(target).year)
            except ValueError as exc:
                raise V10DiagnosticError("score target_date is not ISO format") from exc
            years.setdefault(year, []).append(row)
    by_year = {
        year: {
            "draws": len(year_rows),
            "avg_top6_hits": math.fsum(float(row["top6_hits"]) for row in year_rows)
            / len(year_rows),
            "avg_top12_hits": math.fsum(float(row["top12_hits"]) for row in year_rows)
            / len(year_rows),
            "avg_top18_hits": math.fsum(float(row["top18_hits"]) for row in year_rows)
            / len(year_rows),
        }
        for year, year_rows in sorted(years.items())
    }
    joint_values = [
        float(row["joint_log_gain"])
        for row in rows
        if row.get("joint_log_gain") is not None
    ]
    summary = {
        "scope": scope,
        "model_name": rows[0].get("model_name"),
        "model_version": rows[0].get("model_version"),
        "draws": draws,
        **averages,
        "top6_lift_vs_theory": averages["avg_top6_hits"] - FAIR_EXPECTATIONS[6],
        "primary_top12_lift_vs_theory": (
            averages["avg_top12_hits"] - FAIR_EXPECTATIONS[12]
        ),
        "top18_lift_vs_theory": averages["avg_top18_hits"] - FAIR_EXPECTATIONS[18],
        "total_top12_hits": sum(top12),
        "primary_exact_one_sided_p": exact_top12_upper_tail(sum(top12), draws),
        "primary_bootstrap_95_ci": _bootstrap_interval(
            top12,
            expectation=FAIR_EXPECTATIONS[12],
            replicates=bootstrap_replicates,
            seed=bootstrap_seed,
        ),
        "fair_constant_brier": fair_brier,
        "fair_constant_log_loss": fair_log_loss,
        "brier_delta_vs_fair": averages["avg_brier"] - fair_brier,
        "log_loss_delta_vs_fair": averages["avg_log_loss"] - fair_log_loss,
        "final6_hit_histogram": {
            str(hits): final6.count(hits) for hits in range(7)
        },
        "calibration": _calibration(rows),
        "performance_by_year": by_year,
        "joint_log_gain_sum": math.fsum(joint_values) if joint_values else None,
    }
    return summary


def paired_top12_bootstrap(
    candidate_scores: Sequence[Mapping[str, Any]],
    control_scores: Sequence[Mapping[str, Any]],
    *,
    scope: str,
    bootstrap_replicates: int = 10_000,
    bootstrap_seed: int = 649,
) -> dict[str, Any]:
    candidate = list(candidate_scores)
    control = list(control_scores)
    if len(candidate) != len(control) or not candidate:
        raise V10DiagnosticError("paired Top-12 bootstrap inputs must align")
    candidate_dates = [row.get("target_date") for row in candidate]
    control_dates = [row.get("target_date") for row in control]
    if candidate_dates != control_dates or (
        all(value is not None for value in candidate_dates)
        and len(set(candidate_dates)) != len(candidate_dates)
    ):
        raise V10DiagnosticError("paired Top-12 target dates are not aligned")
    differences = [
        int(left["top12_hits"]) - int(right["top12_hits"])
        for left, right in zip(candidate, control)
    ]
    return {
        "scope": scope,
        "draws": len(differences),
        "mean_candidate_minus_targeted_control_top12_hits": (
            math.fsum(differences) / len(differences)
        ),
        "bootstrap_95_ci": _bootstrap_interval(
            differences,
            expectation=0.0,
            replicates=bootstrap_replicates,
            seed=bootstrap_seed,
        ),
    }


def holm_adjusted_pvalues(named_pvalues: Mapping[str, float]) -> dict[str, float]:
    """Apply the frozen append-only Holm step-down adjustment."""

    if not named_pvalues:
        raise V10DiagnosticError("Holm adjustment requires at least one p-value")
    values = []
    for name, raw in named_pvalues.items():
        if not isinstance(name, str) or not name:
            raise V10DiagnosticError("Holm p-value name is invalid")
        if type(raw) not in (int, float) or not math.isfinite(raw) or not 0.0 <= raw <= 1.0:
            raise V10DiagnosticError("Holm raw p-value is invalid")
        values.append((name, float(raw)))
    ordered = sorted(values, key=lambda item: (item[1], item[0]))
    adjusted: dict[str, float] = {}
    running = 0.0
    family_size = len(ordered)
    for index, (name, raw) in enumerate(ordered):
        running = max(running, (family_size - index) * raw)
        adjusted[name] = min(1.0, running)
    return adjusted


def _control_behaves_as_null(summary: Mapping[str, Any]) -> bool:
    return not (
        float(summary["primary_exact_one_sided_p"]) <= 0.05
        and float(summary["primary_bootstrap_95_ci"][0]) > 0.0
    )


def _scope_rows(
    rows: Sequence[Mapping[str, Any]],
    scope: V10Scope,
) -> list[Mapping[str, Any]]:
    selected = []
    for row in rows:
        target = row.get("target_date")
        if not isinstance(target, str):
            raise V10DiagnosticError("runner score row lacks a target date")
        try:
            target_date = date.fromisoformat(target)
        except ValueError as exc:
            raise V10DiagnosticError("runner score target date is invalid") from exc
        if scope.contains(target_date):
            selected.append(row)
    if len(selected) != scope.target_count:
        raise V10DiagnosticError(
            f"scope {scope.name} has {len(selected)} targets, expected {scope.target_count}"
        )
    return selected


def _joint_delta_sum(
    candidate_scores: Sequence[Mapping[str, Any]],
    control_scores: Sequence[Mapping[str, Any]],
) -> float:
    if len(candidate_scores) != len(control_scores) or not candidate_scores:
        raise V10DiagnosticError("joint candidate/control rows must align")
    deltas = []
    for candidate, control in zip(candidate_scores, control_scores):
        if candidate.get("target_date") != control.get("target_date"):
            raise V10DiagnosticError("joint candidate/control target dates differ")
        candidate_gain = candidate.get("joint_log_gain")
        control_gain = control.get("joint_log_gain")
        if candidate_gain is None or control_gain is None:
            raise V10DiagnosticError("joint candidate/control gain is missing")
        deltas.append(float(candidate_gain) - float(control_gain))
    return math.fsum(deltas)


def v10_historical_decision(
    *,
    candidate: Mapping[str, Any],
    candidate_halves: Sequence[Mapping[str, Any]],
    targeted_control: Mapping[str, Any],
    targeted_control_halves: Sequence[Mapping[str, Any]],
    random_control: Mapping[str, Any],
    random_control_halves: Sequence[Mapping[str, Any]],
    paired: Mapping[str, Any],
    paired_halves: Sequence[Mapping[str, Any]],
    joint: Mapping[str, Any],
    v1_ensemble_top12_mean: float,
    audit_warnings: Sequence[str],
    proper_score_tolerance: float = PROPER_SCORE_TOLERANCE,
) -> dict[str, Any]:
    """Apply all ten conjunctive historical gates without rescue metrics."""

    if not (
        len(candidate_halves)
        == len(targeted_control_halves)
        == len(random_control_halves)
        == len(paired_halves)
        == 2
    ):
        raise V10DiagnosticError("V10 decision requires exactly two frozen halves")
    candidate_scopes = [candidate, *candidate_halves]
    targeted_scopes = [targeted_control, *targeted_control_halves]
    random_scopes = [random_control, *random_control_halves]
    paired_scopes = [paired, *paired_halves]
    gates = {
        "positive_aggregate_primary_lift": (
            float(candidate["primary_top12_lift_vs_theory"]) > 0.0
        ),
        "aggregate_holm_adjusted_p_at_most_0_05": (
            float(candidate["primary_holm_adjusted_p"]) <= 0.05
        ),
        "aggregate_bootstrap_lower_above_zero": (
            float(candidate["primary_bootstrap_95_ci"][0]) > 0.0
        ),
        "positive_primary_lift_in_both_fixed_halves": all(
            float(summary["primary_top12_lift_vs_theory"]) > 0.0
            for summary in candidate_halves
        ),
        "candidate_outperforms_targeted_control_aggregate_and_halves": all(
            float(summary["bootstrap_95_ci"][0]) > 0.0
            for summary in paired_scopes
        ),
        "proper_scores_within_fair_tolerance_aggregate_and_halves": all(
            float(summary["brier_delta_vs_fair"]) <= proper_score_tolerance
            and float(summary["log_loss_delta_vs_fair"]) <= proper_score_tolerance
            for summary in candidate_scopes
        ),
        "candidate_above_frozen_v1_ensemble_top12": (
            float(candidate["avg_top12_hits"]) > float(v1_ensemble_top12_mean)
        ),
        "controls_null_aggregate_and_halves": all(
            _control_behaves_as_null(summary)
            for summary in [*targeted_scopes, *random_scopes]
        ),
        "joint_mechanism_gate": all(
            (
                float(joint["candidate_aggregate_log_gain"])
                >= JOINT_AGGREGATE_THRESHOLD,
                all(
                    float(value) > 0.0
                    for value in joint["candidate_half_log_gains"]
                ),
                float(joint["candidate_minus_control_aggregate_log_gain"]) > 0.0,
                all(
                    float(value) > 0.0
                    for value in joint[
                        "candidate_minus_control_half_log_gains"
                    ]
                ),
                float(joint["control_aggregate_log_gain"])
                < JOINT_AGGREGATE_THRESHOLD,
            )
        ),
        "audit_clear": not audit_warnings,
    }
    all_passed = all(gates.values())
    return {
        "decision": (
            "eligible_for_separate_reviewed_shadow_decision"
            if all_passed
            else "reject"
        ),
        "evidence_lane": "consumed_historical_diagnostic",
        "all_scientific_gates_passed": all_passed,
        "gates": gates,
        "proper_score_max_delta_vs_fair": proper_score_tolerance,
        "prospective_status": "not_activated",
        "live_role": "none",
    }


def _validate_timestamp(timestamp: datetime) -> str:
    if not isinstance(timestamp, datetime) or timestamp.tzinfo is None:
        raise V10DiagnosticError("V10 clock must return a timezone-aware datetime")
    normalized = timestamp.astimezone(timezone.utc)
    return normalized.isoformat(timespec="microseconds").replace("+00:00", "Z")


def _exclusive_write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        _directory_fsync(path.parent)
    except FileExistsError:
        raise
    except OSError as exc:
        raise V10DiagnosticError(f"unable to durably create {path.name}") from exc


def _claim_attempt(
    path: Path,
    *,
    request: V10DiagnosticRequest,
    preflight: Mapping[str, Any],
    started_at_utc: str,
) -> dict[str, Any]:
    payload = {
        "analysis_plan": {
            "bootstrap_replicates": request.bootstrap_replicates,
            "bootstrap_seed": request.bootstrap_seed,
            "reference": dict(request.reference),
            "stability_scopes": [
                {
                    "end": scope.end.isoformat(),
                    "name": scope.name,
                    "start": scope.start.isoformat(),
                    "target_count": scope.target_count,
                }
                for scope in request.stability_scopes
            ],
        },
        "code_commit": request.code_commit,
        "command": request.exact_command,
        "configuration": preflight.get("configuration"),
        "data": preflight.get("data"),
        "experiment_id": EXPERIMENT_ID,
        "model_version": MODEL_VERSION,
        "references": preflight.get("references"),
        "runtime": preflight.get("runtime"),
        "seed": 649,
        "started_at_utc": started_at_utc,
        "status": "historical_diagnostic_claimed",
    }
    try:
        _exclusive_write_bytes(path, _canonical_json_bytes(payload) + b"\n")
    except FileExistsError as exc:
        raise V10DiagnosticError(
            "V10 historical one-shot claim already exists; refusing to score"
        ) from exc
    return payload


def _assert_artifacts_absent(
    paths: V10ArtifactPaths,
    target_dates: Sequence[date],
) -> None:
    existing = [path for path in paths.normal_paths() if path.exists()]
    for target_date in target_dates:
        bundle = paths.claim.parent / (
            f"historical-6of6-candidate__{target_date.isoformat()}__v10.0.0.json"
        )
        staging = bundle.with_name(f".{bundle.name}.staging")
        if bundle.exists():
            existing.append(bundle)
        if staging.exists():
            existing.append(staging)
    if existing:
        names = ", ".join(sorted(path.name for path in existing))
        raise V10DiagnosticError(
            f"V10 one-shot artifact already exists; refusing to score: {names}"
        )


def _validate_forecast_payload(
    payload: Mapping[str, Any],
    *,
    target_date: date,
) -> dict[str, Any]:
    frozen = dict(payload)
    if frozen.get("target_date") != target_date.isoformat():
        raise V10DiagnosticError("forecast payload target date mismatch")
    if any(key in frozen for key in ("actual", "bonus", "prediction_frozen_at_utc")):
        raise V10DiagnosticError("forecast payload contains reveal/timestamp data")
    prefix = frozen.get("prefix")
    forecasts = frozen.get("forecasts")
    if not isinstance(prefix, Mapping) or not isinstance(forecasts, Mapping):
        raise V10DiagnosticError("forecast payload lacks prefix or model forecasts")
    if tuple(forecasts) != MODEL_ORDER or set(forecasts) != set(MODEL_ORDER):
        raise V10DiagnosticError("forecast payload model order/identity is not frozen")
    history_draws = prefix.get("history_draws")
    history_through = prefix.get("history_through")
    prefix_digest = prefix.get("strict_prefix_sha256")
    if type(history_draws) is not int or history_draws < 0:
        raise V10DiagnosticError("forecast prefix history count is invalid")
    if history_through is not None:
        try:
            if date.fromisoformat(history_through) >= target_date:
                raise V10DiagnosticError("forecast prefix is not strictly prior")
        except (TypeError, ValueError) as exc:
            raise V10DiagnosticError("forecast history-through date is invalid") from exc
    if (
        not isinstance(prefix_digest, str)
        or len(prefix_digest) != 64
        or any(character not in "0123456789abcdef" for character in prefix_digest)
    ):
        raise V10DiagnosticError("forecast strict-prefix digest is invalid")
    for expected_name in MODEL_ORDER:
        forecast = forecasts[expected_name]
        if not isinstance(forecast, Mapping):
            raise V10DiagnosticError("model forecast must be a JSON mapping")
        if forecast.get("model_name") != expected_name:
            raise V10DiagnosticError("model forecast identity mismatch")
        expected_version = "v1.0.0" if expected_name == RANDOM_CONTROL_MODEL else MODEL_VERSION
        if forecast.get("model_version") != expected_version:
            raise V10DiagnosticError("model forecast version mismatch")
        if forecast.get("target_date") != target_date.isoformat():
            raise V10DiagnosticError("model forecast target date mismatch")
        if forecast.get("history_draws") != history_draws:
            raise V10DiagnosticError("candidate/control history counts differ")
        if forecast.get("history_through") != history_through:
            raise V10DiagnosticError("candidate/control history cutoffs differ")
        probabilities = _probability_vector(forecast)
        _ranking_vector(forecast, probabilities)
    canonical = _canonical_json_bytes(frozen)
    if b"actual" in canonical.lower() or b"bonus" in canonical.lower():
        raise V10DiagnosticError("canonical forecast payload contains reveal fields")
    return frozen


def _joint_gain_from_payload(
    forecast: Mapping[str, Any],
    actual_main: Sequence[int],
) -> float:
    model_name = forecast.get("model_name")
    if model_name not in (CANDIDATE_MODEL, TARGETED_CONTROL_MODEL):
        raise V10DiagnosticError("joint gain requires V10 candidate/control")
    actual = _as_actual_main(actual_main)
    history_draws = forecast.get("history_draws")
    sum_a = forecast.get("sum_a")
    theta = forecast.get("theta")
    log_z = forecast.get("log_z")
    if type(history_draws) is not int or type(sum_a) is not int:
        raise V10DiagnosticError("joint gain forecast count fields are invalid")
    if type(theta) not in (int, float) or type(log_z) not in (int, float):
        raise V10DiagnosticError("joint gain forecast numeric fields are invalid")
    if 49 * sum_a == 30 * history_draws:
        return 0.0
    if model_name == TARGETED_CONTROL_MODEL:
        from .models.v10_adjacent_pair_structure import CONTROL_DESTINATIONS

        actual = tuple(
            sorted(CONTROL_DESTINATIONS[number - 1] for number in actual)
        )
    adjacency = sum(
        right - left == 1 for left, right in zip(actual, actual[1:])
    )
    gain = float(theta) * adjacency
    gain -= float(log_z)
    gain += math.log(FAIR_TOTAL_SIX_SETS)
    if not math.isfinite(gain):
        raise V10DiagnosticError("joint log gain is non-finite")
    return gain


def _write_staging_file(path: Path, payload: bytes) -> None:
    _exclusive_write_bytes(path, payload)


def _safe_publish_pair(
    *,
    json_path: Path,
    markdown_path: Path,
    json_staging: Path,
    markdown_staging: Path,
    json_bytes: bytes,
    markdown_bytes: bytes,
) -> None:
    staged: list[Path] = []
    try:
        _write_staging_file(json_staging, json_bytes)
        staged.append(json_staging)
        _write_staging_file(markdown_staging, markdown_bytes)
        staged.append(markdown_staging)
    except (FileExistsError, V10DiagnosticError) as exc:
        for path in reversed(staged):
            try:
                path.unlink()
            except OSError:
                pass
        raise V10DiagnosticError("unable to stage complete V10 report pair") from exc

    published: list[Path] = []
    try:
        os.link(json_staging, json_path)
        published.append(json_path)
        os.link(markdown_staging, markdown_path)
        published.append(markdown_path)
        _directory_fsync(json_path.parent)
    except OSError as exc:
        rollback_ok = True
        for path in reversed(published):
            try:
                path.unlink()
            except OSError:
                rollback_ok = False
        if rollback_ok:
            try:
                _directory_fsync(json_path.parent)
            except OSError:
                rollback_ok = False
        if json_path.exists() or markdown_path.exists():
            rollback_ok = False
        if rollback_ok:
            for path in (json_staging, markdown_staging):
                try:
                    path.unlink()
                except OSError:
                    rollback_ok = False
        message = (
            "V10 partial publication retained for Archive"
            if not rollback_ok
            else "unable to publish complete V10 report pair; claim retained"
        )
        raise V10DiagnosticError(message) from exc
    try:
        json_staging.unlink()
        markdown_staging.unlink()
        _directory_fsync(json_path.parent)
    except OSError as exc:
        raise V10DiagnosticError(
            "V10 report published but staging cleanup failed; evidence retained"
        ) from exc


def _safe_publish_bundle(path: Path, payload: Mapping[str, Any]) -> None:
    staging = path.with_name(f".{path.name}.staging")
    if path.exists() or staging.exists():
        raise V10DiagnosticError("V10 historical 6/6 bundle already exists")
    try:
        _write_staging_file(
            staging,
            json.dumps(
                payload,
                indent=2,
                sort_keys=True,
                allow_nan=False,
                ensure_ascii=False,
            ).encode("utf-8")
            + b"\n",
        )
        os.link(staging, path)
        _directory_fsync(path.parent)
        staging.unlink()
        _directory_fsync(path.parent)
    except OSError as exc:
        message = (
            "V10 historical 6/6 partial publication retained for Archive"
            if path.exists()
            else "unable to publish V10 historical 6/6 bundle; staging retained"
        )
        raise V10DiagnosticError(message) from exc


def _render_markdown(report: Mapping[str, Any]) -> str:
    decision = report["historical_decision"]
    candidate = report["scopes"]["aggregate"][CANDIDATE_MODEL]
    lines = [
        "# V10 Adjacent-Pair Structure Historical Diagnostic",
        "",
        "Status: consumed historical diagnostic only; not blind, confirmatory,",
        "prospective, or an automatic live/shadow promotion.",
        "",
        f"- Experiment: `{EXPERIMENT_ID}` / `{MODEL_VERSION}`",
        f"- Frozen implementation commit: `{report['code_commit']}`",
        f"- Targets: `{candidate['draws']}`",
        f"- Candidate Top-12 mean: `{candidate['avg_top12_hits']:.9f}`",
        f"- Candidate Top-12 lift: `{candidate['primary_top12_lift_vs_theory']:+.9f}`",
        f"- Candidate raw p: `{candidate['primary_exact_one_sided_p']:.9g}`",
        f"- Candidate Holm p: `{candidate['primary_holm_adjusted_p']:.9g}`",
        f"- Historical decision: **{decision['decision']}**",
        "- Prospective status: **not_activated**",
        "- V1 production and V3 shadow roles: unchanged",
        "",
        "## Frozen gate outcomes",
        "",
    ]
    for gate, passed in decision["gates"].items():
        lines.append(f"- `{gate}`: {'pass' if passed else 'fail'}")
    lines.extend(
        [
            "",
            "The JSON companion and permanent hash-chain ledger retain complete",
            "forecast, score, calibration, control, joint-gain, record, warning,",
            "and provenance evidence. A negative result is a valid outcome.",
            "",
        ]
    )
    return "\n".join(lines)


def _file_sha256(path: Path) -> str:
    digest = sha256()
    try:
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as exc:
        raise V10DiagnosticError(f"unable to hash {path.name}") from exc
    return digest.hexdigest()


def _notify(
    notifier: Notifier,
    *,
    subject: str,
    body: str,
    notification_warnings: list[str],
) -> bool:
    try:
        sent = notifier(subject, body)
    except Exception as exc:  # pragma: no cover - defensive external boundary
        notification_warnings.append(
            f"notification_exception:{type(exc).__name__}:{exc}"
        )
        return False
    if sent is not True:
        notification_warnings.append(f"notification_not_sent:{subject}")
        return False
    return True


def _normalized_6of6_audit(
    callback: Callable[[date, Mapping[str, Any], Sequence[int]], Mapping[str, Any]],
    *,
    target_date: date,
    forecast_payload: Mapping[str, Any],
    actual: Sequence[int],
) -> dict[str, Any]:
    """Derive audit clearance from required evidenced checks, never a claimed bool."""

    callback_error: dict[str, str] | None = None

    def _safe_text(value: object) -> str:
        return str(value).encode("utf-8", "backslashreplace").decode("utf-8")

    try:
        raw = callback(target_date, forecast_payload, actual)
    except Exception as exc:  # mandatory Archive branch, not generic failure
        raw = {}
        callback_error = {
            "error_type": type(exc).__name__,
            "error_message": _safe_text(exc),
        }
    if not isinstance(raw, Mapping):
        callback_error = {
            "error_type": "InvalidAuditPayload",
            "error_message": "leakage audit callback did not return a mapping",
        }
        raw = {}
    raw_checks = raw.get("checks")
    checks_by_name: dict[str, Mapping[str, Any]] = {}
    schema_errors: list[str] = []
    if not isinstance(raw_checks, list):
        schema_errors.append("checks must be a list")
        raw_checks = []
    for item in raw_checks:
        if not isinstance(item, Mapping):
            schema_errors.append("check must be a mapping")
            continue
        name = item.get("name")
        if not isinstance(name, str) or name in checks_by_name:
            schema_errors.append("check names must be unique strings")
            continue
        checks_by_name[name] = item
    unexpected = sorted(set(checks_by_name) - set(REQUIRED_6OF6_AUDIT_CHECKS))
    for name in unexpected:
        schema_errors.append(f"unexpected audit check:{name}")
    normalized_checks = []
    for name in REQUIRED_6OF6_AUDIT_CHECKS:
        item = checks_by_name.get(name)
        evidence = item.get("evidence") if item is not None else None
        try:
            evidence = json.loads(
                _canonical_json_bytes({"evidence": evidence}).decode("utf-8")
            )["evidence"]
        except V10DiagnosticError:
            schema_errors.append(f"noncanonical evidence:{name}")
            evidence = None
        passed = (
            item is not None
            and type(item.get("passed")) is bool
            and item.get("passed") is True
            and evidence not in (None, "", [], {})
        )
        if item is None:
            schema_errors.append(f"missing required check:{name}")
        elif type(item.get("passed")) is not bool:
            schema_errors.append(f"non-boolean passed:{name}")
        elif evidence in (None, "", [], {}):
            schema_errors.append(f"empty evidence:{name}")
        normalized_checks.append(
            {
                "name": name,
                "passed": passed,
                "evidence": evidence,
            }
        )
    declared_clear = raw.get("clear")
    if declared_clear is not None and type(declared_clear) is not bool:
        schema_errors.append("declared clear must be boolean when present")
        declared_clear = None
    clear = (
        callback_error is None
        and not schema_errors
        and all(check["passed"] for check in normalized_checks)
    )
    normalized = {
        "clear": clear,
        "declared_clear_ignored": declared_clear,
        "checks": normalized_checks,
        "schema_errors": schema_errors,
        "callback_error": callback_error,
        "required_check_names": list(REQUIRED_6OF6_AUDIT_CHECKS),
    }
    _derived_6of6_audit_clear(normalized)
    return normalized


def _breakthrough_benchmark_text(
    *,
    target_scores: Mapping[str, Mapping[str, Any]],
    scored_targets: int,
) -> str:
    lines = [
        f"已评分严格前缀目标数：{scored_targets}（命中后立即停止，未生成621期聚合门槛）",
        "理论公平期望：Top-6=36/49，Top-12=72/49，Top-18=108/49；p=6/49。",
    ]
    for model_name in MODEL_ORDER:
        score = target_scores[model_name]
        lines.append(
            f"{model_name}: Top6={score['top6_hits']}/6, "
            f"Top12={score['top12_hits']}/6, Top18={score['top18_hits']}/6, "
            f"final6={score['final6_hits']}/6, actual_ranks={score['actual_ranks']}, "
            f"Brier={score['brier_score']:.12g}, LogLoss={score['log_loss']:.12g}, "
            f"mean_rank={score['mean_actual_rank']:.12g}, "
            f"joint_log_gain={score.get('joint_log_gain')}"
        )
    return "\n".join(lines)


def _normal_pass_notification_body() -> str:
    return (
        "V10正常621期消费型历史诊断已持久发布，全部预注册门槛通过。\n"
        "这只表示可进入独立shadow评审，不会自动替换V1或V3。"
    )


def _six_of_six_notification_body(
    *,
    forecast_payload: Mapping[str, Any],
    actual: Sequence[int],
    target_date: str,
    code_commit: str,
    audit_clear: bool,
    target_scores: Mapping[str, Mapping[str, Any]],
    scored_targets: int,
) -> str:
    forecasts = forecast_payload["forecasts"]
    return (
        f"预测号码：{list(forecasts[CANDIDATE_MODEL]['final6'])}\n"
        f"实际号码：{list(actual)}\n"
        f"开奖日期：{target_date}\n"
        f"模型：{CANDIDATE_MODEL} {MODEL_VERSION}\n"
        f"训练截止：{forecast_payload['prefix']['history_through']}\n"
        f"泄漏审计：{'通过' if audit_clear else '失败，命中不是有效证据'}\n"
        f"Git提交：{code_commit}\n"
        "完整benchmark：\n"
        f"{_breakthrough_benchmark_text(target_scores=target_scores, scored_targets=scored_targets)}\n"
        "OOS理由：每期仅使用严格之前历史，预测先写入并fsync，"
        "之后才通过隔离reveal回调取得实际号码。"
    )


def _notification_outbox_fields(
    *,
    warnings_before: Sequence[str],
    notification_required: bool,
    subject: str | None,
    body: str | None,
    idempotency_context: Mapping[str, Any],
) -> dict[str, Any]:
    prior = list(warnings_before)
    if not notification_required:
        return {
            "email_dispatched": False,
            "notification_idempotency_key": None,
            "notification_request": None,
            "notification_required": False,
            "notification_status": "not_required",
            "notification_warnings": prior,
            "notification_warnings_before_terminal": prior,
            "subject": None,
        }
    if not isinstance(subject, str) or not subject or not isinstance(body, str) or not body:
        raise V10DiagnosticError("V10 notification outbox request is invalid")
    request = {"body": body, "subject": subject}
    idempotency_key = sha256(
        _canonical_json_bytes(
            {"context": dict(idempotency_context), "request": request}
        )
    ).hexdigest()
    return {
        "email_dispatched": False,
        "notification_idempotency_key": idempotency_key,
        "notification_request": request,
        "notification_required": True,
        "notification_status": "pending_external_receipt",
        "notification_warnings": [
            *prior,
            f"notification_pending_external_receipt:{idempotency_key}",
        ],
        "notification_warnings_before_terminal": prior,
        "subject": subject,
    }


def _public_score(score: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in score.items()
        if key != "probabilities"
    }


def _build_scientific_report_sections(
    *,
    preflight: Mapping[str, Any],
    results: Mapping[str, Sequence[Mapping[str, Any]]],
    per_target: Sequence[Mapping[str, Any]],
    record_ledger: Sequence[Mapping[str, Any]],
    stability_scopes: Sequence[V10Scope],
    bootstrap_replicates: int,
    bootstrap_seed: int,
    reference: Mapping[str, Any],
    expected_target_count: int,
) -> dict[str, Any]:
    """Build the scientific payload shared by publication and ledger replay."""

    if set(results) != set(MODEL_ORDER):
        raise V10DiagnosticError("V10 report results omit a registered model")
    if any(len(results[name]) != expected_target_count for name in MODEL_ORDER):
        raise V10DiagnosticError("V10 report model row counts are incomplete")
    if len(per_target) != expected_target_count or len(record_ledger) != (
        expected_target_count
    ):
        raise V10DiagnosticError("V10 report target evidence is incomplete")
    if len(stability_scopes) != 2:
        raise V10DiagnosticError("V10 report requires two fixed stability scopes")

    scopes: dict[str, dict[str, Any]] = {}
    scope_rows: dict[str, dict[str, list[Mapping[str, Any]]]] = {}
    registered_scopes: list[V10Scope | None] = [None, *stability_scopes]
    for scope in registered_scopes:
        scope_name = "aggregate" if scope is None else scope.name
        rows_by_model = {
            model_name: (
                list(results[model_name])
                if scope is None
                else _scope_rows(results[model_name], scope)
            )
            for model_name in MODEL_ORDER
        }
        scope_rows[scope_name] = rows_by_model
        model_summaries = {
            model_name: summarize_v10_scope(
                rows,
                scope=scope_name,
                bootstrap_replicates=bootstrap_replicates,
                bootstrap_seed=bootstrap_seed,
            )
            for model_name, rows in rows_by_model.items()
        }
        for control_name in (TARGETED_CONTROL_MODEL, RANDOM_CONTROL_MODEL):
            model_summaries[control_name]["behaves_as_null"] = (
                _control_behaves_as_null(model_summaries[control_name])
            )
        scopes[scope_name] = model_summaries

    candidate = scopes["aggregate"][CANDIDATE_MODEL]
    v5_p = reference.get("v5_primary_exact_p")
    if (
        type(v5_p) not in (int, float)
        or not math.isfinite(float(v5_p))
        or not 0.0 <= float(v5_p) <= 1.0
    ):
        raise V10DiagnosticError("V10 reference lacks the frozen V5 primary p-value")
    holm = holm_adjusted_pvalues(
        {
            "V5_pair_affinity": float(v5_p),
            EXPERIMENT_ID: float(candidate["primary_exact_one_sided_p"]),
        }
    )
    candidate["primary_holm_adjusted_p"] = holm[EXPERIMENT_ID]
    for scope in stability_scopes:
        scopes[scope.name][CANDIDATE_MODEL]["primary_holm_adjusted_p"] = None

    paired = {
        scope_name: paired_top12_bootstrap(
            rows_by_model[CANDIDATE_MODEL],
            rows_by_model[TARGETED_CONTROL_MODEL],
            scope=scope_name,
            bootstrap_replicates=bootstrap_replicates,
            bootstrap_seed=bootstrap_seed,
        )
        for scope_name, rows_by_model in scope_rows.items()
    }
    aggregate_candidate_rows = scope_rows["aggregate"][CANDIDATE_MODEL]
    aggregate_control_rows = scope_rows["aggregate"][TARGETED_CONTROL_MODEL]
    joint = {
        "candidate_aggregate_log_gain": math.fsum(
            float(row["joint_log_gain"]) for row in aggregate_candidate_rows
        ),
        "control_aggregate_log_gain": math.fsum(
            float(row["joint_log_gain"]) for row in aggregate_control_rows
        ),
        "candidate_minus_control_aggregate_log_gain": _joint_delta_sum(
            aggregate_candidate_rows,
            aggregate_control_rows,
        ),
        "candidate_half_log_gains": [
            math.fsum(
                float(row["joint_log_gain"])
                for row in scope_rows[scope.name][CANDIDATE_MODEL]
            )
            for scope in stability_scopes
        ],
        "control_half_log_gains": [
            math.fsum(
                float(row["joint_log_gain"])
                for row in scope_rows[scope.name][TARGETED_CONTROL_MODEL]
            )
            for scope in stability_scopes
        ],
        "candidate_minus_control_half_log_gains": [
            _joint_delta_sum(
                scope_rows[scope.name][CANDIDATE_MODEL],
                scope_rows[scope.name][TARGETED_CONTROL_MODEL],
            )
            for scope in stability_scopes
        ],
        "aggregate_candidate_threshold": JOINT_AGGREGATE_THRESHOLD,
        "operation_order": (
            "per_target_candidate_minus_control_then_math.fsum_target_date_ascending"
        ),
    }
    audit_warnings = list(preflight.get("audit_warnings", ()))
    for scope_name, model_summaries in scopes.items():
        for control_name in (TARGETED_CONTROL_MODEL, RANDOM_CONTROL_MODEL):
            if not model_summaries[control_name]["behaves_as_null"]:
                audit_warnings.append(f"{control_name}_non_null:{scope_name}")
    candidate_halves = [
        scopes[scope.name][CANDIDATE_MODEL] for scope in stability_scopes
    ]
    targeted_halves = [
        scopes[scope.name][TARGETED_CONTROL_MODEL] for scope in stability_scopes
    ]
    random_halves = [
        scopes[scope.name][RANDOM_CONTROL_MODEL] for scope in stability_scopes
    ]
    paired_halves = [paired[scope.name] for scope in stability_scopes]
    v1_mean = reference.get("v1_ensemble_top12_mean")
    if type(v1_mean) not in (int, float) or not math.isfinite(float(v1_mean)):
        raise V10DiagnosticError("V10 reference lacks the V1 ensemble Top-12 mean")
    historical_decision = v10_historical_decision(
        candidate=candidate,
        candidate_halves=candidate_halves,
        targeted_control=scopes["aggregate"][TARGETED_CONTROL_MODEL],
        targeted_control_halves=targeted_halves,
        random_control=scopes["aggregate"][RANDOM_CONTROL_MODEL],
        random_control_halves=random_halves,
        paired=paired["aggregate"],
        paired_halves=paired_halves,
        joint=joint,
        v1_ensemble_top12_mean=float(v1_mean),
        audit_warnings=audit_warnings,
    )
    gates = historical_decision.get("gates")
    if not isinstance(gates, Mapping) or set(gates) != HISTORICAL_GATE_NAMES:
        raise V10DiagnosticError("V10 historical decision gate identity changed")
    if any(type(value) is not bool for value in gates.values()):
        raise V10DiagnosticError("V10 historical decision gate type changed")
    return {
        "scopes": scopes,
        "paired_candidate_minus_targeted_control": paired,
        "joint_structure": joint,
        "progressive_record_ledger": list(record_ledger),
        "per_target": list(per_target),
        "comparisons": reference.get("comparisons", []),
        "multiplicity": {
            "family": "v5_pair_cooccurrence",
            "variant_index": 2,
            "raw_pvalues": {
                "V5_pair_affinity": float(v5_p),
                EXPERIMENT_ID: float(candidate["primary_exact_one_sided_p"]),
            },
            "holm_adjusted_pvalues": holm,
        },
        "historical_decision": historical_decision,
        "audit_warnings": audit_warnings,
    }


def _build_normal_report(
    *,
    request: V10DiagnosticRequest,
    preflight: Mapping[str, Any],
    claim_payload: Mapping[str, Any],
    claim_sha256: str,
    ledger: HashChainLedger,
    results: Mapping[str, Sequence[Mapping[str, Any]]],
    per_target: Sequence[Mapping[str, Any]],
    record_ledger: Sequence[Mapping[str, Any]],
    notification_warnings: Sequence[str],
) -> dict[str, Any]:
    scientific_sections = _build_scientific_report_sections(
        preflight=preflight,
        results=results,
        per_target=per_target,
        record_ledger=record_ledger,
        stability_scopes=request.stability_scopes,
        bootstrap_replicates=request.bootstrap_replicates,
        bootstrap_seed=request.bootstrap_seed,
        reference=request.reference,
        expected_target_count=request.expected_target_count,
    )
    return _assemble_normal_report(
        output_dir=request.output_dir,
        code_commit=request.code_commit,
        exact_command=request.exact_command,
        claim_payload=claim_payload,
        claim_sha256=claim_sha256,
        ledger_path=ledger.path,
        ledger_event_count=ledger.event_count,
        ledger_head_sha256=ledger.head_sha256,
        preflight=preflight,
        expected_target_count=request.expected_target_count,
        target_dates=[item.target_date.isoformat() for item in request.targets],
        scientific_sections=scientific_sections,
        notification_warnings=notification_warnings,
    )


def _assemble_normal_report(
    *,
    output_dir: Path,
    code_commit: str,
    exact_command: str,
    claim_payload: Mapping[str, Any],
    claim_sha256: str,
    ledger_path: Path,
    ledger_event_count: int,
    ledger_head_sha256: str,
    preflight: Mapping[str, Any],
    expected_target_count: int,
    target_dates: Sequence[str],
    scientific_sections: Mapping[str, Any],
    notification_warnings: Sequence[str],
) -> dict[str, Any]:
    """Assemble the exact immutable normal-report template."""

    return {
        "schema_version": 1,
        "experiment_id": EXPERIMENT_ID,
        "model_name": CANDIDATE_MODEL,
        "model_version": MODEL_VERSION,
        "status": "historical_diagnostic_complete",
        "evidence_warning": (
            "Consumed historical diagnostic only; not blind, confirmatory, "
            "prospective, or sufficient for automatic activation."
        ),
        "code_commit": code_commit,
        "command": exact_command,
        "one_shot_claim": {
            "path": str(V10ArtifactPaths.in_directory(output_dir).claim),
            "sha256": claim_sha256,
            "payload": dict(claim_payload),
            "created_before_first_forecast_and_score": True,
            "retention": "permanent_success_or_failure",
        },
        "attempt_ledger": {
            "path": str(ledger_path),
            "event_count_at_report": ledger_event_count,
            "head_sha256_at_report": ledger_head_sha256,
            "hash_chain": "sha256_canonical_json_previous_event",
        },
        "preflight": dict(preflight),
        "historical_lane": {
            "name": "consumed_historical_diagnostic",
            "target_count": expected_target_count,
            "target_dates": list(target_dates),
            "excluded": [
                "1982-01-01..2019-12-31:training_prefix_only",
                "2026-01-01..2026-08-15:known_outcomes_excluded",
            ],
        },
        **scientific_sections,
        "notification_warnings": list(notification_warnings),
        "notification_status_at_report_publication": "pending_post_publication",
        "notification_result_authority": "external_workflow_receipt_after_terminal",
        "post_publication_notification": {
            "required_only_if_all_scientific_gates_pass": True,
            "notification_result_authority": (
                "external_workflow_receipt_after_terminal"
            ),
            "request_recorded_in_attempt_ledger_event": "published",
            "status_at_report_publication": "pending_post_publication",
        },
        "live_roles": {
            "v1": "production_baseline_unchanged",
            "v3": "shadow_unchanged",
            "v10": "none_not_activated",
        },
        "prospective_cohort": {
            "status": "not_activated",
            "separate_review_required": True,
            "minimum_eligible_evaluated_draws": 208,
            "fixed_halves": [104, 104],
            "early_look": "prohibited",
            "extension": "prohibited",
        },
    }


def run_v10_historical(request: V10DiagnosticRequest) -> dict[str, Any]:
    """Execute the sole reveal-gated V10 attempt.

    The function is dependency-injected so unit tests use only synthetic draws.
    Production construction lives in ``tools/run_v10_historical.py``.
    """

    if not isinstance(request, V10DiagnosticRequest):
        raise TypeError("run_v10_historical requires V10DiagnosticRequest")
    if (
        len(request.code_commit) != 40
        or any(character not in "0123456789abcdef" for character in request.code_commit)
    ):
        raise V10DiagnosticError("V10 code_commit must be a full lowercase Git SHA")
    if request.expected_target_count < 1:
        raise V10DiagnosticError("V10 expected target count must be positive")
    targets = tuple(request.targets)
    target_dates = [target.target_date for target in targets]
    if len(targets) != request.expected_target_count:
        raise V10DiagnosticError(
            f"V10 target count is {len(targets)}, expected {request.expected_target_count}"
        )
    if target_dates != sorted(target_dates) or len(set(target_dates)) != len(target_dates):
        raise V10DiagnosticError("V10 target dates must be strictly increasing and unique")
    if len(request.stability_scopes) != 2:
        raise V10DiagnosticError("V10 requires exactly two fixed stability scopes")
    for scope in request.stability_scopes:
        if sum(scope.contains(target_date) for target_date in target_dates) != scope.target_count:
            raise V10DiagnosticError(f"V10 target dates do not match scope {scope.name}")
    if sum(scope.target_count for scope in request.stability_scopes) != len(targets):
        raise V10DiagnosticError("V10 fixed halves do not partition all targets")

    paths = V10ArtifactPaths.in_directory(request.output_dir)
    _assert_artifacts_absent(paths, target_dates)
    preflight = dict(request.preflight())
    if preflight.get("passed") is not True:
        raise V10DiagnosticError("V10 preflight did not pass")
    if preflight.get("audit_warnings"):
        raise V10DiagnosticError("V10 preflight contains audit warnings")

    started_at_utc = _validate_timestamp(request.clock())
    claim_payload = _claim_attempt(
        paths.claim,
        request=request,
        preflight=preflight,
        started_at_utc=started_at_utc,
    )
    claim_sha256 = _file_sha256(paths.claim)
    ledger: HashChainLedger | None = None
    terminal = False
    notification_warnings: list[str] = []
    external_notification_warnings: list[str] = []
    try:
        ledger = HashChainLedger.create(paths.ledger)
        ledger.append(
            "claimed",
            {
                "claim_sha256": claim_sha256,
                "code_commit": request.code_commit,
                "started_at_utc": started_at_utc,
            },
        )
        ledger.append("preflight_passed", preflight)
        ledger.append(
            "scoring_started",
            {
                "expected_targets": request.expected_target_count,
                "target_start": target_dates[0].isoformat(),
                "target_end": target_dates[-1].isoformat(),
            },
        )

        results: dict[str, list[dict[str, Any]]] = {
            name: [] for name in MODEL_ORDER
        }
        per_target: list[dict[str, Any]] = []
        record_ledger: list[dict[str, Any]] = []
        previous_maximum = 0
        for target_plan in targets:
            first_payload = _validate_forecast_payload(
                target_plan.build_forecasts(),
                target_date=target_plan.target_date,
            )
            first_bytes = _canonical_json_bytes(first_payload)
            repeated_payload = _validate_forecast_payload(
                target_plan.build_forecasts(),
                target_date=target_plan.target_date,
            )
            repeated_bytes = _canonical_json_bytes(repeated_payload)
            if repeated_bytes != first_bytes:
                raise V10DiagnosticError(
                    "V10 repeated strict-prefix forecast payload is not deterministic"
                )
            forecast_sha256 = sha256(first_bytes).hexdigest()
            frozen_at_utc = _validate_timestamp(request.clock())
            ledger.append(
                "prediction_frozen",
                {
                    "forecast_payload": first_payload,
                    "forecast_sha256": forecast_sha256,
                    "prediction_frozen_at_utc": frozen_at_utc,
                    "target_date": target_plan.target_date.isoformat(),
                },
            )

            # This is the sole reveal seam. HashChainLedger.append has already
            # flushed and fsynced the complete prediction_frozen event.
            actual = _as_actual_main(target_plan.reveal_actual())
            target_scores: dict[str, dict[str, Any]] = {}
            forecasts = first_payload["forecasts"]
            for model_name in MODEL_ORDER:
                score = score_probability_forecast(forecasts[model_name], actual)
                if model_name in (CANDIDATE_MODEL, TARGETED_CONTROL_MODEL):
                    score["joint_log_gain"] = _joint_gain_from_payload(
                        forecasts[model_name],
                        actual,
                    )
                else:
                    score["joint_log_gain"] = None
                target_scores[model_name] = score
                results[model_name].append(score)

            candidate_score = target_scores[CANDIDATE_MODEL]
            current_hits = int(candidate_score["final6_hits"])
            new_maximum = max(previous_maximum, current_hits)
            new_record = current_hits > previous_maximum
            record = {
                "target_date": target_plan.target_date.isoformat(),
                "previous_maximum_final6_hits": previous_maximum,
                "current_final6_hits": current_hits,
                "new_maximum_final6_hits": new_maximum,
                "new_within_run_record": new_record,
                "prediction": list(forecasts[CANDIDATE_MODEL]["final6"]),
                "actual": list(actual),
                "forecast_sha256": forecast_sha256,
            }
            record_ledger.append(record)
            scored_payload = {
                "actual_main": list(actual),
                "forecast_sha256": forecast_sha256,
                "progressive_record": record,
                "scores": {
                    model_name: _public_score(target_scores[model_name])
                    for model_name in MODEL_ORDER
                },
                "target_date": target_plan.target_date.isoformat(),
            }
            ledger.append("target_revealed_scored", scored_payload)
            per_target.append(
                {
                    "target_date": target_plan.target_date.isoformat(),
                    "forecast_payload": first_payload,
                    "forecast_sha256": forecast_sha256,
                    "actual_main": list(actual),
                    "scores": scored_payload["scores"],
                    "progressive_record": record,
                }
            )

            six_of_six_detected = current_hits == 6
            if six_of_six_detected:
                ledger.append(
                    "historical_6of6_candidate_detected",
                    {
                        "forecast_sha256": forecast_sha256,
                        "model_name": CANDIDATE_MODEL,
                        "model_version": MODEL_VERSION,
                        "status": "historical-6of6-candidate",
                        "target_date": target_plan.target_date.isoformat(),
                    },
                )
            previous_maximum = new_maximum
            if six_of_six_detected:
                audit = _normalized_6of6_audit(
                    request.leakage_audit,
                    target_date=target_plan.target_date,
                    forecast_payload=first_payload,
                    actual=actual,
                )
                ledger.append(
                    "historical_6of6_leakage_audit_completed",
                    {
                        "audit": audit,
                        "target_date": target_plan.target_date.isoformat(),
                    },
                )
                validate_v10_ledger_state_machine(
                    paths.ledger,
                    expected_targets=request.expected_target_count,
                    allow_6of6_audit_prefix=True,
                )
                bundle_path = request.output_dir / (
                    "historical-6of6-candidate__"
                    f"{target_plan.target_date.isoformat()}__v10.0.0.json"
                )
                bundle = {
                    "schema_version": 1,
                    "status": "historical-6of6-candidate",
                    "experiment_id": EXPERIMENT_ID,
                    "model_name": CANDIDATE_MODEL,
                    "model_version": MODEL_VERSION,
                    "source_commit": preflight.get("data", {}).get("source_commit"),
                    "registration_commit": preflight.get("registration_commit"),
                    "implementation_commit": request.code_commit,
                    "feature_identity": "sorted_main_gap_exactly_one",
                    "parameters": preflight.get("registered_parameters"),
                    "target_date": target_plan.target_date.isoformat(),
                    "training_cutoff": first_payload["prefix"]["history_through"],
                    "forecast_payload": first_payload,
                    "forecast_sha256": forecast_sha256,
                    "prediction": list(forecasts[CANDIDATE_MODEL]["final6"]),
                    "actual": list(actual),
                    "seed": 649,
                    "runtime": preflight.get("runtime"),
                    "claim": {
                        "path": str(paths.claim),
                        "sha256": claim_sha256,
                    },
                    "ledger": {
                        "path": str(paths.ledger),
                        "head_sha256_before_bundle": ledger.head_sha256,
                        "event_count_before_bundle": ledger.event_count,
                    },
                    "leakage_audit": audit,
                    "evidence_lane": "consumed_historical_diagnostic",
                    "scored_targets_before_stop": len(per_target),
                    "normal_621_report": "prohibited_after_early_stop",
                }
                _safe_publish_bundle(bundle_path, bundle)
                clear = audit["clear"] is True
                terminal_event = (
                    "historical_6of6_candidate_published"
                    if clear
                    else "historical_6of6_candidate_archived_leakage_failed"
                )
                subject = (
                    "🚨 [LOTTO649] 历史严格回测成功预测 6/6"
                    if clear
                    else "⚠️ [LOTTO649] 历史 6/6 候选泄漏审计失败"
                )
                warnings_before_terminal = list(notification_warnings)
                bundle_sha256 = _file_sha256(bundle_path)
                notification_body = _six_of_six_notification_body(
                    forecast_payload=first_payload,
                    actual=actual,
                    target_date=target_plan.target_date.isoformat(),
                    code_commit=request.code_commit,
                    audit_clear=clear,
                    target_scores=target_scores,
                    scored_targets=len(per_target),
                )
                terminal_payload = {
                    "bundle_path": str(bundle_path),
                    "bundle_sha256": bundle_sha256,
                    **_notification_outbox_fields(
                        warnings_before=warnings_before_terminal,
                        notification_required=True,
                        subject=subject,
                        body=notification_body,
                        idempotency_context={
                            "bundle_sha256": bundle_sha256,
                            "code_commit": request.code_commit,
                            "event_type": terminal_event,
                            "experiment_id": EXPERIMENT_ID,
                            "target_date": target_plan.target_date.isoformat(),
                        },
                    ),
                    "scored_targets": len(per_target),
                    "target_date": target_plan.target_date.isoformat(),
                }
                validate_v10_ledger_state_machine(
                    paths.ledger,
                    expected_targets=request.expected_target_count,
                    prospective_6of6_terminal=(
                        terminal_event,
                        terminal_payload,
                    ),
                )
                ledger.append(terminal_event, terminal_payload)
                terminal = True
                email_sent = _notify(
                    request.notifier,
                    subject=subject,
                    body=notification_body,
                    notification_warnings=external_notification_warnings,
                )
                return {
                    "status": terminal_event,
                    "claim_path": str(paths.claim),
                    "ledger_path": str(paths.ledger),
                    "bundle_path": str(bundle_path),
                    "notification_dispatched_after_terminal": email_sent,
                    "scored_targets": len(per_target),
                    "stop_global_search": clear,
                    "notification_warnings": terminal_payload[
                        "notification_warnings"
                    ],
                    "external_notification_warnings": (
                        external_notification_warnings
                    ),
                }

            for kind, progress_subject, progress_body in (
                _progress_notification_requests(
                    forecast_payload=first_payload,
                    actual=actual,
                    target_date=target_plan.target_date.isoformat(),
                    candidate_score=candidate_score,
                    progressive_record=record,
                )
            ):
                progress_payload = {
                    "forecast_sha256": forecast_sha256,
                    "kind": kind,
                    **_notification_outbox_fields(
                        warnings_before=notification_warnings,
                        notification_required=True,
                        subject=progress_subject,
                        body=progress_body,
                        idempotency_context=_progress_notification_context(
                            code_commit=request.code_commit,
                            kind=kind,
                            target_date=target_plan.target_date.isoformat(),
                            forecast_sha256=forecast_sha256,
                        ),
                    ),
                    "target_date": target_plan.target_date.isoformat(),
                }
                ledger.append("progress_notification_outbox", progress_payload)
                notification_warnings = list(
                    progress_payload["notification_warnings"]
                )
                _notify(
                    request.notifier,
                    subject=progress_subject,
                    body=progress_body,
                    notification_warnings=external_notification_warnings,
                )

        ledger.append(
            "scoring_completed",
            {
                "scored_targets": len(per_target),
                "status": "complete_621" if len(per_target) == 621 else "synthetic_complete",
            },
        )
        ledger.append(
            "publication_started",
            {
                "notification_warnings": list(notification_warnings),
                "report_json": str(paths.report_json),
                "report_markdown": str(paths.report_markdown),
                "scored_targets": len(per_target),
            },
        )
        report = _build_normal_report(
            request=request,
            preflight=preflight,
            claim_payload=claim_payload,
            claim_sha256=claim_sha256,
            ledger=ledger,
            results=results,
            per_target=per_target,
            record_ledger=record_ledger,
            notification_warnings=notification_warnings,
        )
        validate_v10_ledger_state_machine(
            paths.ledger,
            expected_targets=request.expected_target_count,
            allow_publication_prefix=True,
        )
        json_bytes = json.dumps(
            report,
            indent=2,
            sort_keys=True,
            allow_nan=False,
            ensure_ascii=False,
        ).encode("utf-8") + b"\n"
        markdown_bytes = _render_markdown(report).encode("utf-8")
        _safe_publish_pair(
            json_path=paths.report_json,
            markdown_path=paths.report_markdown,
            json_staging=paths.report_json_staging,
            markdown_staging=paths.report_markdown_staging,
            json_bytes=json_bytes,
            markdown_bytes=markdown_bytes,
        )
        all_gates_passed = report["historical_decision"][
            "all_scientific_gates_passed"
        ]
        alert_subject = (
            "[LOTTO649] 【历史严格回测】V10全部统计门槛通过"
            if all_gates_passed
            else None
        )
        json_sha256 = _file_sha256(paths.report_json)
        markdown_sha256 = _file_sha256(paths.report_markdown)
        alert_body = _normal_pass_notification_body() if all_gates_passed else None
        published_payload = {
            "all_scientific_gates_passed": all_gates_passed,
            "decision": report["historical_decision"]["decision"],
            "gates": report["historical_decision"]["gates"],
            "json_path": str(paths.report_json),
            "json_sha256": json_sha256,
            "markdown_path": str(paths.report_markdown),
            "markdown_sha256": markdown_sha256,
            "scored_targets": len(per_target),
            **_notification_outbox_fields(
                warnings_before=notification_warnings,
                notification_required=all_gates_passed,
                subject=alert_subject,
                body=alert_body,
                idempotency_context={
                    "code_commit": request.code_commit,
                    "event_type": "published",
                    "experiment_id": EXPERIMENT_ID,
                    "json_sha256": json_sha256,
                    "markdown_sha256": markdown_sha256,
                },
            ),
        }
        validate_v10_ledger_state_machine(
            paths.ledger,
            expected_targets=request.expected_target_count,
            prospective_normal_terminal=published_payload,
        )
        ledger.append("published", published_payload)
        terminal = True
        alert_sent: bool | None = None
        if all_gates_passed:
            alert_sent = _notify(
                request.notifier,
                subject=alert_subject,
                body=alert_body,
                notification_warnings=external_notification_warnings,
            )
        return {
            "status": "published",
            "claim_path": str(paths.claim),
            "ledger_path": str(paths.ledger),
            "json_path": str(paths.report_json),
            "markdown_path": str(paths.report_markdown),
            "report": report,
            "notification_dispatched_after_terminal": alert_sent,
            "notification_warnings": published_payload["notification_warnings"],
            "external_notification_warnings": external_notification_warnings,
            "stop_global_search": False,
        }
    except Exception as exc:
        if ledger is not None and not terminal:
            try:
                ledger.append(
                    "failed",
                    {
                        "error_message": str(exc),
                        "error_type": type(exc).__name__,
                        "notification_warnings": list(notification_warnings),
                        "status": "consumed_archive_no_rerun",
                    },
                )
            except Exception:
                pass
        raise
    finally:
        if ledger is not None:
            ledger.close()
