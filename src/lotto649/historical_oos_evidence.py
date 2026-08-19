"""Permanent, score-preserving historical out-of-sample evidence imports.

This module never calls a predictor or the project's scoring code. It preserves
missing legacy forecast snapshots as unknown. Where a complete frozen snapshot
exists, it independently checks simple set-intersection hit counts against the
stored evaluation before admitting the opportunity as verified.
"""

from __future__ import annotations

import csv
from datetime import date
from hashlib import sha256
import io
import json
import math
from pathlib import Path
from typing import Any, Mapping


ZERO_HASH = "0" * 64
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


class HistoricalOOSEvidenceError(RuntimeError):
    """Raised when historical evidence cannot be imported without guessing."""


def _canonical_json(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise HistoricalOOSEvidenceError(
            "evidence is not canonical finite JSON"
        ) from exc


def _event(
    sequence: int, previous_hash: str, event_type: str, payload: Mapping[str, Any]
) -> dict[str, Any]:
    without_hash = {
        "event_type": event_type,
        "payload": dict(payload),
        "previous_event_sha256": previous_hash,
        "sequence": sequence,
    }
    event_hash = sha256(
        _canonical_json(without_hash) + previous_hash.encode("ascii")
    ).hexdigest()
    return {**without_hash, "event_sha256": event_hash}


def _required_source_bytes(
    source_bytes: Mapping[str, bytes], manifest: Mapping[str, Any], name: str
) -> bytes:
    sources = manifest.get("sources")
    if not isinstance(sources, Mapping) or not isinstance(sources.get(name), Mapping):
        raise HistoricalOOSEvidenceError(f"manifest source {name!r} is missing")
    source = sources[name]
    path = source.get("path")
    expected_hash = source.get("sha256")
    if not isinstance(path, str) or not isinstance(expected_hash, str):
        raise HistoricalOOSEvidenceError(f"manifest source {name!r} is invalid")
    raw = source_bytes.get(path)
    if not isinstance(raw, bytes):
        raise HistoricalOOSEvidenceError(f"source bytes for {path!r} are missing")
    if sha256(raw).hexdigest() != expected_hash:
        raise HistoricalOOSEvidenceError(f"source SHA-256 mismatch for {path!r}")
    return raw


def _validated_number_list(
    value: object,
    *,
    expected_size: int,
    label: str,
) -> list[int]:
    if (
        not isinstance(value, list)
        or len(value) != expected_size
        or any(type(number) is not int or not 1 <= number <= 49 for number in value)
        or len(set(value)) != expected_size
    ):
        raise HistoricalOOSEvidenceError(
            f"{label} must contain {expected_size} distinct labels in 1..49"
        )
    return value


def _legacy_opportunities(
    detail_csv_bytes: bytes, source_id: str
) -> list[dict[str, Any]]:
    try:
        text = detail_csv_bytes.decode("utf-8")
        rows = list(csv.DictReader(io.StringIO(text, newline="")))
    except (UnicodeDecodeError, csv.Error) as exc:
        raise HistoricalOOSEvidenceError("legacy detail CSV is invalid") from exc
    if not rows:
        raise HistoricalOOSEvidenceError("legacy detail CSV is empty")

    opportunities: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for source_row, row in enumerate(rows, start=2):
        try:
            actual_main = json.loads(row["actual"])
            matched_final = json.loads(row["matched_final"])
            final6_hits = int(row["final_6_hits"])
            top6_hits = int(row["top_6_hits"])
            top12_hits = int(row["top_12_hits"])
            top18_hits = int(row["top_18_hits"])
            bonus = int(row["bonus"])
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise HistoricalOOSEvidenceError(
                f"legacy detail CSV row {source_row} is invalid"
            ) from exc
        if any(
            type(hit_count) is not int or not 0 <= hit_count <= 6
            for hit_count in (final6_hits, top6_hits, top12_hits, top18_hits)
        ):
            raise HistoricalOOSEvidenceError(
                f"legacy detail CSV row {source_row} has an impossible hit count"
            )
        actual_main = _validated_number_list(
            actual_main,
            expected_size=6,
            label=f"legacy detail CSV row {source_row} actual main set",
        )
        matched_final = _validated_number_list(
            matched_final,
            expected_size=final6_hits,
            label=f"legacy detail CSV row {source_row} matched final set",
        )
        if (
            type(bonus) is not int
            or not 1 <= bonus <= 49
            or bonus in actual_main
            or not set(matched_final) <= set(actual_main)
            or not top6_hits <= top12_hits <= top18_hits
        ):
            raise HistoricalOOSEvidenceError(
                f"legacy detail CSV row {source_row} is internally inconsistent"
            )

        identity = (
            row["target_draw_date"],
            row["model_name"],
            row["model_version"],
        )
        if identity in seen:
            raise HistoricalOOSEvidenceError(
                f"duplicate opportunity in legacy detail CSV row {source_row}"
            )
        seen.add(identity)

        if final6_hits == 6:
            exact_status = "reported_unverified"
            success_class = "reported_unverified_final6"
        elif top12_hits == 6:
            exact_status = "reported_false"
            success_class = "top12_coverage_only"
        else:
            exact_status = "reported_false"
            success_class = "partial_final6"

        opportunities.append(
            {
                "audit": {
                    "chronology": "implementation_strict_prefix",
                    "independently_recomputable": False,
                    "pre_reveal_persistence": "not_proven",
                },
                "classification": {
                    "exact_final6_status": exact_status,
                    "stop_global_search": False,
                    "success_class": success_class,
                    "top12_all_main_status": (
                        "reported_true" if top12_hits == 6 else "reported_false"
                    ),
                },
                "evidence_lane": "consumed_historical_diagnostic",
                "forecast": {
                    "final6": None,
                    "forecast_sha256": None,
                    "snapshot_status": "missing_from_source",
                    "top12": None,
                    "top18": None,
                    "top6": None,
                },
                "model_name": row["model_name"],
                "reported_evaluation": {
                    "final6_hits": final6_hits,
                    "matched_final": matched_final,
                    "score_origin": "copied_not_recomputed",
                    "top12_hits": top12_hits,
                    "top18_hits": top18_hits,
                    "top6_hits": top6_hits,
                },
                "reported_model_version": row["model_version"],
                "source": {"source_id": source_id, "source_row": source_row},
                "target": {
                    "actual_main": actual_main,
                    "bonus": bonus,
                    "target_date": row["target_draw_date"],
                },
            }
        )
    return opportunities


def _legacy_bundle_opportunities(
    source_bytes: Mapping[str, bytes], manifest: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    bundles = manifest.get("legacy_bundles")
    if not isinstance(bundles, list) or not bundles:
        raise HistoricalOOSEvidenceError("manifest legacy_bundles must be non-empty")
    required = {
        "archive_path",
        "archive_sha256",
        "artifact_id",
        "artifact_name",
        "bundle_id",
        "chronology",
        "detail_path",
        "detail_sha256",
        "exact_duplicate_of",
        "head_sha",
        "job_id",
        "pre_reveal_persistence",
        "run_id",
        "summary_path",
        "summary_sha256",
    }
    opportunities: list[dict[str, Any]] = []
    duplicate_events: list[dict[str, Any]] = []
    by_bundle: dict[str, Mapping[str, Any]] = {}
    detail_owner: dict[str, str] = {}
    for bundle in bundles:
        if not isinstance(bundle, Mapping) or set(bundle) != required:
            raise HistoricalOOSEvidenceError("legacy bundle schema is invalid")
        bundle_id = bundle["bundle_id"]
        if not isinstance(bundle_id, str) or not bundle_id or bundle_id in by_bundle:
            raise HistoricalOOSEvidenceError("legacy bundle identity is invalid")
        for path_key, hash_key in (
            ("archive_path", "archive_sha256"),
            ("detail_path", "detail_sha256"),
            ("summary_path", "summary_sha256"),
        ):
            path = bundle[path_key]
            expected_hash = bundle[hash_key]
            raw = source_bytes.get(path) if isinstance(path, str) else None
            if (
                not isinstance(raw, bytes)
                or not isinstance(expected_hash, str)
                or sha256(raw).hexdigest() != expected_hash
            ):
                raise HistoricalOOSEvidenceError(
                    f"legacy bundle SHA-256 mismatch for {path!r}"
                )
        duplicate_of = bundle["exact_duplicate_of"]
        if duplicate_of is not None:
            original = by_bundle.get(duplicate_of)
            if original is None or original["detail_sha256"] != bundle["detail_sha256"]:
                raise HistoricalOOSEvidenceError(
                    "legacy duplicate stream does not match its declared source"
                )
            duplicate_events.append(
                {
                    "bundle_id": bundle_id,
                    "detail_sha256": bundle["detail_sha256"],
                    "exact_duplicate_of": duplicate_of,
                    "opportunities_added": 0,
                }
            )
        else:
            prior_owner = detail_owner.get(bundle["detail_sha256"])
            if prior_owner is not None:
                raise HistoricalOOSEvidenceError(
                    "exact duplicate detail stream lacks exact_duplicate_of"
                )
            detail_owner[bundle["detail_sha256"]] = bundle_id
            detail = source_bytes[bundle["detail_path"]]
            imported = _legacy_opportunities(detail, bundle_id)
            for opportunity in imported:
                opportunity["audit"]["chronology"] = bundle["chronology"]
                opportunity["audit"]["pre_reveal_persistence"] = bundle[
                    "pre_reveal_persistence"
                ]
                opportunity["audit"]["deduplication_status"] = (
                    "unknown_without_forecast_snapshot"
                )
                opportunity["source"].update(
                    {
                        "artifact_id": bundle["artifact_id"],
                        "head_sha": bundle["head_sha"],
                        "job_id": bundle["job_id"],
                        "run_id": bundle["run_id"],
                    }
                )
            opportunities.extend(imported)
        by_bundle[bundle_id] = bundle
    return opportunities, duplicate_events


def _coverage_gap_payloads(
    source_bytes: Mapping[str, bytes], manifest: Mapping[str, Any]
) -> list[dict[str, Any]]:
    raw_gaps = manifest.get("coverage_gaps")
    if not isinstance(raw_gaps, list):
        raise HistoricalOOSEvidenceError("manifest coverage_gaps must be a list")
    required = {
        "date_end",
        "date_start",
        "evidence_lane",
        "experiment_id",
        "model_name",
        "model_version",
        "reason",
        "reported_target_count",
        "source_path",
        "source_sha256",
    }
    payloads: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for raw_gap in raw_gaps:
        if not isinstance(raw_gap, Mapping) or set(raw_gap) != required:
            raise HistoricalOOSEvidenceError("coverage gap schema is invalid")
        source_path = raw_gap["source_path"]
        source_hash = raw_gap["source_sha256"]
        if not isinstance(source_path, str) or not isinstance(source_hash, str):
            raise HistoricalOOSEvidenceError("coverage gap source identity is invalid")
        raw = source_bytes.get(source_path)
        if not isinstance(raw, bytes) or sha256(raw).hexdigest() != source_hash:
            raise HistoricalOOSEvidenceError(
                f"coverage gap source SHA-256 mismatch for {source_path!r}"
            )
        identity = (
            str(raw_gap["experiment_id"]),
            str(raw_gap["model_name"]),
            str(raw_gap["model_version"]),
        )
        if identity in seen:
            raise HistoricalOOSEvidenceError("duplicate coverage gap")
        seen.add(identity)
        payloads.append(
            {
                **dict(raw_gap),
                "maximum_final6_hits": None,
                "per_target_final6": "unknown",
                "per_target_top12": "unknown",
            }
        )
    return payloads


def _canonical_hash_chain_events(raw: bytes, *, label: str) -> list[dict[str, Any]]:
    raw_lines = raw.splitlines(keepends=True)
    if not raw_lines:
        raise HistoricalOOSEvidenceError(f"{label} hash-chain ledger is empty")
    events: list[dict[str, Any]] = []
    previous_hash = ZERO_HASH
    for sequence, raw_line in enumerate(raw_lines):
        if not raw_line.endswith(b"\n"):
            raise HistoricalOOSEvidenceError(
                f"{label} hash-chain line lacks newline terminator"
            )
        try:
            event = json.loads(raw_line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise HistoricalOOSEvidenceError(
                f"{label} hash-chain line is invalid"
            ) from exc
        if not isinstance(event, dict) or _canonical_json(event) + b"\n" != raw_line:
            raise HistoricalOOSEvidenceError(
                f"{label} hash-chain line is not canonical JSON"
            )
        if event.get("sequence") != sequence:
            raise HistoricalOOSEvidenceError(f"{label} sequence is not contiguous")
        if event.get("previous_event_sha256") != previous_hash:
            raise HistoricalOOSEvidenceError(f"{label} previous-event hash mismatch")
        event_hash = event.get("event_sha256")
        without_hash = dict(event)
        without_hash.pop("event_sha256", None)
        expected_hash = sha256(
            _canonical_json(without_hash) + previous_hash.encode("ascii")
        ).hexdigest()
        if event_hash != expected_hash:
            raise HistoricalOOSEvidenceError(f"{label} event hash mismatch")
        events.append(event)
        previous_hash = expected_hash
    return events


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _iso_date(value: object, *, label: str) -> date:
    if not isinstance(value, str):
        raise HistoricalOOSEvidenceError(f"{label} must be an ISO date")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise HistoricalOOSEvidenceError(f"{label} must be an ISO date") from exc


def _validated_ranked_forecast(
    forecast: Mapping[str, Any],
    *,
    model_name: object,
    model_version: object,
    target_date: str,
    history_draws: int,
    history_through: str,
) -> dict[str, list[int]]:
    if (
        forecast.get("model_name") != model_name
        or forecast.get("model_version") != model_version
        or forecast.get("target_date") != target_date
        or forecast.get("history_draws") != history_draws
        or forecast.get("history_through") != history_through
    ):
        raise HistoricalOOSEvidenceError(
            "verified snapshot forecast identity or history mismatch"
        )

    ranking = _validated_number_list(
        forecast.get("ranking"),
        expected_size=49,
        label="verified snapshot ranking",
    )
    top6 = _validated_number_list(
        forecast.get("top6"),
        expected_size=6,
        label="verified snapshot top6",
    )
    top12 = _validated_number_list(
        forecast.get("top12"),
        expected_size=12,
        label="verified snapshot top12",
    )
    top18 = _validated_number_list(
        forecast.get("top18"),
        expected_size=18,
        label="verified snapshot top18",
    )
    final6 = _validated_number_list(
        forecast.get("final6"),
        expected_size=6,
        label="verified snapshot final6",
    )
    if top6 != ranking[:6] or top12 != ranking[:12] or top18 != ranking[:18]:
        raise HistoricalOOSEvidenceError(
            "verified snapshot Top-K sets differ from the stored ranking"
        )
    if final6 != sorted(ranking[:6]):
        raise HistoricalOOSEvidenceError(
            "verified snapshot final6 differs from sorted ranking Top-6"
        )

    raw_probabilities = forecast.get("probabilities")
    if isinstance(raw_probabilities, Mapping):
        if set(raw_probabilities) != {str(number) for number in range(1, 50)}:
            raise HistoricalOOSEvidenceError(
                "verified snapshot probability labels are incomplete"
            )
        values = [raw_probabilities[str(number)] for number in range(1, 50)]
    elif isinstance(raw_probabilities, list):
        values = raw_probabilities
    else:
        raise HistoricalOOSEvidenceError("verified snapshot probabilities are missing")
    if len(values) != 49 or any(type(value) not in (int, float) for value in values):
        raise HistoricalOOSEvidenceError(
            "verified snapshot probabilities must contain 49 numeric values"
        )
    probabilities = [float(value) for value in values]
    if (
        not all(math.isfinite(value) and 0.0 < value < 1.0 for value in probabilities)
        or abs(math.fsum(probabilities) - 6.0) > 1.0e-12
    ):
        raise HistoricalOOSEvidenceError(
            "verified snapshot probabilities violate the 6/49 contract"
        )
    expected_ranking = sorted(
        range(1, 50), key=lambda number: (-probabilities[number - 1], number)
    )
    if ranking != expected_ranking:
        raise HistoricalOOSEvidenceError(
            "verified snapshot ranking differs from probabilities"
        )
    return {
        "final6": final6,
        "ranking": ranking,
        "top6": top6,
        "top12": top12,
        "top18": top18,
    }


def _runner_preflight_clear(
    events: list[dict[str, Any]], report: Mapping[str, Any]
) -> bool:
    preflights = [
        (index, event.get("payload"))
        for index, event in enumerate(events)
        if event.get("event_type") == "preflight_passed"
    ]
    freeze_indices = [
        index
        for index, event in enumerate(events)
        if event.get("event_type") == "prediction_frozen"
    ]
    if len(preflights) != 1 or not freeze_indices:
        return False
    preflight_index, preflight = preflights[0]
    if (
        not isinstance(preflight, Mapping)
        or preflight_index >= min(freeze_indices)
        or report.get("preflight") != preflight
        or report.get("audit_warnings") != []
        or preflight.get("passed") is not True
        or preflight.get("audit_warnings") != []
    ):
        return False
    chronology = preflight.get("chronology")
    return (
        isinstance(chronology, Mapping)
        and chronology.get("2026_scored_targets") == 0
        and chronology.get("bonus_excluded_from_model_and_scores") is True
        and chronology.get("complete_expanding_prefix") is True
        and chronology.get("target_dates_strictly_increasing_unique") is True
    )


def _normalized_leakage_audit_clear(audit: object) -> bool:
    if not isinstance(audit, Mapping) or set(audit) != {
        "callback_error",
        "checks",
        "clear",
        "declared_clear_ignored",
        "required_check_names",
        "schema_errors",
    }:
        return False
    if audit.get("required_check_names") != list(REQUIRED_6OF6_AUDIT_CHECKS):
        return False
    checks = audit.get("checks")
    if not isinstance(checks, list) or len(checks) != len(REQUIRED_6OF6_AUDIT_CHECKS):
        return False
    check_passes: list[bool] = []
    for expected_name, check in zip(REQUIRED_6OF6_AUDIT_CHECKS, checks):
        if (
            not isinstance(check, Mapping)
            or set(check) != {"evidence", "name", "passed"}
            or check.get("name") != expected_name
            or type(check.get("passed")) is not bool
        ):
            return False
        evidence = check.get("evidence")
        try:
            _canonical_json({"evidence": evidence})
        except HistoricalOOSEvidenceError:
            return False
        check_passes.append(
            check.get("passed") is True and evidence not in (None, "", [], {})
        )
    schema_errors = audit.get("schema_errors")
    if not isinstance(schema_errors, list) or any(
        not isinstance(error, str) for error in schema_errors
    ):
        return False
    callback_error = audit.get("callback_error")
    if callback_error is not None and (
        not isinstance(callback_error, Mapping)
        or not isinstance(callback_error.get("error_type"), str)
        or not isinstance(callback_error.get("error_message"), str)
    ):
        return False
    declared_clear = audit.get("declared_clear_ignored")
    if declared_clear is not None and type(declared_clear) is not bool:
        return False
    derived = callback_error is None and not schema_errors and all(check_passes)
    return (
        type(audit.get("clear")) is bool and audit.get("clear") is derived and derived
    )


def _target_leakage_audit_clear(
    events: list[dict[str, Any]],
    *,
    forecast_sha256: str,
    model_name: object,
    model_version: object,
    reveal_index: int,
    target_date: str,
) -> bool:
    detected = [
        (index, event)
        for index, event in enumerate(events)
        if event.get("event_type") == "historical_6of6_candidate_detected"
        and isinstance(event.get("payload"), Mapping)
        and event["payload"].get("target_date") == target_date
    ]
    audits = [
        (index, event)
        for index, event in enumerate(events)
        if event.get("event_type") == "historical_6of6_leakage_audit_completed"
        and isinstance(event.get("payload"), Mapping)
        and event["payload"].get("target_date") == target_date
    ]
    terminals = [
        (index, event)
        for index, event in enumerate(events)
        if event.get("event_type")
        in {
            "historical_6of6_candidate_published",
            "historical_6of6_candidate_archived_leakage_failed",
        }
        and isinstance(event.get("payload"), Mapping)
        and event["payload"].get("target_date") == target_date
    ]
    if len(detected) != 1 or len(audits) != 1 or len(terminals) != 1:
        return False
    detected_index, detected_event = detected[0]
    audit_index, audit_event = audits[0]
    terminal_index, terminal_event = terminals[0]
    detected_payload = detected_event["payload"]
    if (
        not reveal_index < detected_index < audit_index < terminal_index
        or detected_payload.get("forecast_sha256") != forecast_sha256
        or detected_payload.get("model_name") != model_name
        or detected_payload.get("model_version") != model_version
    ):
        return False
    audit_clear = _normalized_leakage_audit_clear(audit_event["payload"].get("audit"))
    expected_terminal = (
        "historical_6of6_candidate_published"
        if audit_clear
        else "historical_6of6_candidate_archived_leakage_failed"
    )
    return terminal_event.get("event_type") == expected_terminal and audit_clear


def _verified_snapshot_opportunities(
    source_bytes: Mapping[str, bytes], manifest: Mapping[str, Any]
) -> list[dict[str, Any]]:
    raw_sources = manifest.get("verified_snapshot_sources", [])
    if not isinstance(raw_sources, list):
        raise HistoricalOOSEvidenceError(
            "manifest verified_snapshot_sources must be a list"
        )
    required = {
        "expected_target_count",
        "experiment_id",
        "ledger_path",
        "ledger_sha256",
        "model_name",
        "model_version",
        "report_path",
        "report_sha256",
    }
    opportunities: list[dict[str, Any]] = []
    for source in raw_sources:
        if not isinstance(source, Mapping) or set(source) != required:
            raise HistoricalOOSEvidenceError(
                "verified snapshot source schema is invalid"
            )
        ledger_path = source["ledger_path"]
        report_path = source["report_path"]
        if not isinstance(ledger_path, str) or not isinstance(report_path, str):
            raise HistoricalOOSEvidenceError("verified snapshot paths are invalid")
        ledger_bytes = source_bytes.get(ledger_path)
        report_bytes = source_bytes.get(report_path)
        if (
            not isinstance(ledger_bytes, bytes)
            or sha256(ledger_bytes).hexdigest() != source["ledger_sha256"]
        ):
            raise HistoricalOOSEvidenceError(
                "verified snapshot ledger SHA-256 mismatch"
            )
        if (
            not isinstance(report_bytes, bytes)
            or sha256(report_bytes).hexdigest() != source["report_sha256"]
        ):
            raise HistoricalOOSEvidenceError(
                "verified snapshot report SHA-256 mismatch"
            )
        try:
            report = json.loads(report_bytes)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise HistoricalOOSEvidenceError(
                "verified snapshot report is invalid"
            ) from exc
        if (
            not isinstance(report, Mapping)
            or report.get("experiment_id") != source["experiment_id"]
            or report.get("model_name") != source["model_name"]
            or report.get("model_version") != source["model_version"]
        ):
            raise HistoricalOOSEvidenceError(
                "verified snapshot report identity mismatch"
            )

        events = _canonical_hash_chain_events(ledger_bytes, label="verified source")
        runner_preflight_clear = _runner_preflight_clear(events, report)
        frozen: dict[
            str,
            tuple[dict[str, list[int]], str, str, int, Mapping[str, Any]],
        ] = {}
        reveal_positions: dict[str, list[int]] = {}
        for event_index, event in enumerate(events):
            if event.get("event_type") != "target_revealed_scored":
                continue
            payload = event.get("payload")
            if isinstance(payload, Mapping) and isinstance(
                payload.get("target_date"), str
            ):
                reveal_positions.setdefault(payload["target_date"], []).append(
                    event_index
                )
        last_freeze_target: date | None = None
        last_freeze_target_text: str | None = None
        last_history_through: date | None = None
        last_history_draws: int | None = None
        for event_index, event in enumerate(events):
            if event.get("event_type") != "prediction_frozen":
                continue
            payload = event.get("payload")
            if not isinstance(payload, Mapping):
                raise HistoricalOOSEvidenceError("prediction_frozen payload is invalid")
            target_date = payload.get("target_date")
            forecast_payload = payload.get("forecast_payload")
            if not isinstance(target_date, str) or not isinstance(
                forecast_payload, Mapping
            ):
                raise HistoricalOOSEvidenceError("prediction_frozen target is invalid")
            target_day = _iso_date(target_date, label="verified snapshot frozen target")
            if last_freeze_target is not None and target_day <= last_freeze_target:
                raise HistoricalOOSEvidenceError(
                    "verified snapshot frozen targets are not strictly increasing"
                )
            if last_freeze_target_text is not None:
                prior_reveals = reveal_positions.get(last_freeze_target_text, [])
                if len(prior_reveals) != 1 or prior_reveals[0] >= event_index:
                    raise HistoricalOOSEvidenceError(
                        "verified snapshot next target was frozen before the prior target reveal"
                    )
            forecasts = forecast_payload.get("forecasts")
            prefix = forecast_payload.get("prefix")
            if (
                forecast_payload.get("target_date") != target_date
                or not isinstance(forecasts, Mapping)
                or not isinstance(prefix, Mapping)
            ):
                raise HistoricalOOSEvidenceError(
                    "prediction_frozen forecast is invalid"
                )
            forecast = forecasts.get(source["model_name"])
            if not isinstance(forecast, Mapping) or target_date in frozen:
                raise HistoricalOOSEvidenceError(
                    "verified snapshot forecast is missing or duplicated"
                )
            forecast_hash = payload.get("forecast_sha256")
            prefix_hash = prefix.get("strict_prefix_sha256")
            history_draws = prefix.get("history_draws")
            history_through = prefix.get("history_through")
            if type(history_draws) is not int or history_draws <= 0:
                raise HistoricalOOSEvidenceError(
                    "verified snapshot prefix history_draws is invalid"
                )
            history_day = _iso_date(
                history_through,
                label="verified snapshot prefix history_through",
            )
            if (
                not _is_sha256(forecast_hash)
                or sha256(_canonical_json(forecast_payload)).hexdigest()
                != forecast_hash
                or not _is_sha256(prefix_hash)
                or history_day >= target_day
                or (
                    last_history_through is not None
                    and history_day <= last_history_through
                )
                or (
                    last_freeze_target is not None and history_day != last_freeze_target
                )
                or (
                    last_history_draws is not None
                    and history_draws != last_history_draws + 1
                )
            ):
                raise HistoricalOOSEvidenceError(
                    "verified snapshot forecast or prefix chronology mismatch"
                )
            validated_forecast = _validated_ranked_forecast(
                forecast,
                model_name=source["model_name"],
                model_version=source["model_version"],
                target_date=target_date,
                history_draws=history_draws,
                history_through=history_through,
            )
            frozen[target_date] = (
                validated_forecast,
                prefix_hash,
                forecast_hash,
                event_index,
                forecast_payload,
            )
            last_freeze_target = target_day
            last_freeze_target_text = target_date
            last_history_through = history_day
            last_history_draws = history_draws

        imported_for_source = 0
        ledger_per_target: list[dict[str, Any]] = []
        last_reveal_target: date | None = None
        for event_index, event in enumerate(events):
            if event.get("event_type") != "target_revealed_scored":
                continue
            payload = event.get("payload")
            if not isinstance(payload, Mapping):
                raise HistoricalOOSEvidenceError("target reveal payload is invalid")
            target_date = payload.get("target_date")
            scores = payload.get("scores")
            if not isinstance(target_date, str) or not isinstance(scores, Mapping):
                raise HistoricalOOSEvidenceError("target reveal identity is invalid")
            target_day = _iso_date(
                target_date, label="verified snapshot revealed target"
            )
            if last_reveal_target is not None and target_day <= last_reveal_target:
                raise HistoricalOOSEvidenceError(
                    "verified snapshot revealed targets are not strictly increasing"
                )
            score = scores.get(source["model_name"])
            if not isinstance(score, Mapping) or target_date not in frozen:
                raise HistoricalOOSEvidenceError("target reveal has no frozen snapshot")
            (
                forecast,
                prefix_hash,
                forecast_hash,
                freeze_index,
                forecast_payload,
            ) = frozen.pop(target_date)
            if freeze_index >= event_index:
                raise HistoricalOOSEvidenceError(
                    "verified snapshot target was revealed before it was frozen"
                )
            if payload.get("forecast_sha256") != forecast_hash:
                raise HistoricalOOSEvidenceError("target reveal forecast hash mismatch")
            if (
                score.get("target_date") != target_date
                or score.get("model_name") != source["model_name"]
                or score.get("model_version") != source["model_version"]
            ):
                raise HistoricalOOSEvidenceError(
                    "verified snapshot copied score identity mismatch"
                )
            actual = _validated_number_list(
                payload.get("actual_main"),
                expected_size=6,
                label="verified snapshot revealed actual main set",
            )
            score_actual = _validated_number_list(
                score.get("actual"),
                expected_size=6,
                label="verified snapshot copied score actual main set",
            )
            if sorted(score_actual) != sorted(actual):
                raise HistoricalOOSEvidenceError(
                    "verified snapshot copied score actual set mismatch"
                )
            actual = sorted(actual)
            actual_set = set(actual)
            expected_scores = {
                "final6_hits": len(set(forecast["final6"]) & actual_set),
                "top6_hits": len(set(forecast["top6"]) & actual_set),
                "top12_hits": len(set(forecast["top12"]) & actual_set),
                "top18_hits": len(set(forecast["top18"]) & actual_set),
            }
            if any(
                type(score.get(field)) is not int or score.get(field) != expected_value
                for field, expected_value in expected_scores.items()
            ) or score.get("matched_final") != sorted(
                set(forecast["final6"]) & actual_set
            ):
                raise HistoricalOOSEvidenceError(
                    "verified snapshot copied score mismatch"
                )
            final6_hits = expected_scores["final6_hits"]
            top12_hits = expected_scores["top12_hits"]
            final6 = forecast["final6"]
            if final6_hits == 6:
                leakage_audit_clear = _target_leakage_audit_clear(
                    events,
                    forecast_sha256=forecast_hash,
                    model_name=source["model_name"],
                    model_version=source["model_version"],
                    reveal_index=event_index,
                    target_date=target_date,
                )
                exact_status = "verified_true"
                stop_search = runner_preflight_clear and leakage_audit_clear
                success_class = (
                    "verified_historical_final6"
                    if stop_search
                    else "verified_historical_final6_audit_not_clear"
                )
                target_leakage_audit_status = (
                    "clear" if leakage_audit_clear else "not_clear_or_missing"
                )
            elif top12_hits == 6:
                exact_status = "verified_false"
                success_class = "top12_coverage_only"
                stop_search = False
                target_leakage_audit_status = "not_applicable_no_verified_6of6"
            else:
                exact_status = "verified_false"
                success_class = "partial_final6"
                stop_search = False
                target_leakage_audit_status = "not_applicable_no_verified_6of6"
            opportunities.append(
                {
                    "audit": {
                        "chronology": "strict_prefix_sha256_present",
                        "independently_recomputable": True,
                        "pre_reveal_persistence": "hash_chain_prediction_frozen",
                        "runner_preflight_status": (
                            "clear"
                            if runner_preflight_clear
                            else "not_clear_or_missing"
                        ),
                        "target_leakage_audit_status": target_leakage_audit_status,
                    },
                    "classification": {
                        "exact_final6_status": exact_status,
                        "stop_global_search": stop_search,
                        "success_class": success_class,
                        "top12_all_main_status": (
                            "reported_true" if top12_hits == 6 else "reported_false"
                        ),
                    },
                    "evidence_lane": "consumed_historical_diagnostic",
                    "forecast": {
                        "final6": final6,
                        "forecast_sha256": forecast_hash,
                        "ranking": forecast["ranking"],
                        "snapshot_status": "verified_full_snapshot",
                        "strict_prefix_sha256": prefix_hash,
                        "top12": forecast["top12"],
                        "top18": forecast["top18"],
                        "top6": forecast["top6"],
                    },
                    "model_name": source["model_name"],
                    "reported_evaluation": {
                        "final6_hits": final6_hits,
                        "matched_final": sorted(set(final6) & actual_set),
                        "score_origin": "independently_recomputed_and_matched",
                        "top12_hits": top12_hits,
                        "top18_hits": expected_scores["top18_hits"],
                        "top6_hits": expected_scores["top6_hits"],
                    },
                    "reported_model_version": source["model_version"],
                    "source": {
                        "experiment_id": source["experiment_id"],
                        "source_event_sha256": event["event_sha256"],
                        "source_ledger_path": ledger_path,
                    },
                    "target": {
                        "actual_main": actual,
                        "bonus": None,
                        "target_date": target_date,
                    },
                }
            )
            ledger_per_target.append(
                {
                    "actual_main": payload.get("actual_main"),
                    "forecast_payload": forecast_payload,
                    "forecast_sha256": payload.get("forecast_sha256"),
                    "progressive_record": payload.get("progressive_record"),
                    "scores": scores,
                    "target_date": target_date,
                }
            )
            imported_for_source += 1
            last_reveal_target = target_day
        if frozen or imported_for_source != source["expected_target_count"]:
            raise HistoricalOOSEvidenceError(
                "verified snapshot target coverage does not match manifest"
            )
        if report.get("per_target") != ledger_per_target:
            raise HistoricalOOSEvidenceError(
                "verified snapshot report per-target evidence differs from ledger"
            )
    return opportunities


def _validate_expected_high_water(
    manifest: Mapping[str, Any], result: Mapping[str, Any]
) -> None:
    expected = manifest.get("expected_high_water")
    if expected is None:
        return
    required = {
        "global_final6_max",
        "global_final6_max_status",
        "reported_final6_max_at_least",
        "verified_full_snapshot_final6_max",
    }
    if not isinstance(expected, Mapping) or set(expected) != required:
        raise HistoricalOOSEvidenceError("expected high-water schema is invalid")
    minimum = expected["reported_final6_max_at_least"]
    if (
        type(minimum) is not int
        or result["reported_final6_max"] < minimum
        or result["global_final6_max"] != expected["global_final6_max"]
        or result["global_final6_max_status"] != expected["global_final6_max_status"]
        or result["verified_full_snapshot_final6_max"]
        != expected["verified_full_snapshot_final6_max"]
    ):
        raise HistoricalOOSEvidenceError("historical evidence high-water mismatch")


def import_legacy_historical_artifact(
    *,
    source_bytes: Mapping[str, bytes],
    manifest: Mapping[str, Any],
    ledger_path: Path,
) -> dict[str, Any]:
    """Copy immutable source facts into a deterministic append-only ledger."""

    if manifest.get("schema_version") != 1:
        raise HistoricalOOSEvidenceError("unsupported historical evidence manifest")
    source_id = manifest.get("source_id")
    if not isinstance(source_id, str) or not source_id:
        raise HistoricalOOSEvidenceError("manifest source_id is invalid")
    if "legacy_bundles" in manifest:
        opportunities, duplicate_streams = _legacy_bundle_opportunities(
            source_bytes, manifest
        )
    else:
        detail = _required_source_bytes(source_bytes, manifest, "legacy_detail")
        _required_source_bytes(source_bytes, manifest, "legacy_summary")
        opportunities = _legacy_opportunities(detail, source_id)
        duplicate_streams = []
    coverage_gaps = _coverage_gap_payloads(source_bytes, manifest)
    verified_opportunities = _verified_snapshot_opportunities(source_bytes, manifest)

    events: list[dict[str, Any]] = []
    previous_hash = ZERO_HASH
    for event_type, payload in (
        [("source_registered", dict(manifest))]
        + [("opportunity", opportunity) for opportunity in opportunities]
        + [("duplicate_stream", stream) for stream in duplicate_streams]
        + [("coverage_gap", gap) for gap in coverage_gaps]
        + [("opportunity", opportunity) for opportunity in verified_opportunities]
    ):
        event = _event(len(events), previous_hash, event_type, payload)
        events.append(event)
        previous_hash = event["event_sha256"]
    ledger_bytes = b"".join(_canonical_json(event) + b"\n" for event in events)

    all_opportunities = opportunities + verified_opportunities
    reported_max = max(
        opportunity["reported_evaluation"]["final6_hits"]
        for opportunity in all_opportunities
    )
    verified_hits = [
        opportunity["reported_evaluation"]["final6_hits"]
        for opportunity in verified_opportunities
    ]
    result = {
        "event_count": len(events),
        "global_final6_max": None,
        "global_final6_max_status": "unknown_due_to_incomplete_coverage",
        "ledger_sha256": sha256(ledger_bytes).hexdigest(),
        "reported_final6_max": reported_max,
        "verified_full_snapshot_final6_max": (
            max(verified_hits) if verified_hits else None
        ),
    }
    _validate_expected_high_water(manifest, result)

    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with ledger_path.open("xb") as handle:
            handle.write(ledger_bytes)
    except FileExistsError as exc:
        if ledger_path.read_bytes() != ledger_bytes:
            raise HistoricalOOSEvidenceError(
                "existing historical evidence ledger is not the deterministic import"
            ) from exc
    return result


def validate_historical_oos_evidence(
    *,
    source_bytes: Mapping[str, bytes],
    manifest: Mapping[str, Any],
    ledger_path: Path,
) -> dict[str, Any]:
    """Fail closed unless sources and every canonical ledger link are intact."""

    try:
        ledger_bytes = ledger_path.read_bytes()
    except OSError as exc:
        raise HistoricalOOSEvidenceError(
            "historical evidence ledger is unreadable"
        ) from exc
    events = _canonical_hash_chain_events(ledger_bytes, label="historical evidence")

    source_id = manifest.get("source_id")
    if not isinstance(source_id, str) or not source_id:
        raise HistoricalOOSEvidenceError("manifest source_id is invalid")
    if "legacy_bundles" in manifest:
        legacy, duplicate_streams = _legacy_bundle_opportunities(source_bytes, manifest)
    else:
        detail = _required_source_bytes(source_bytes, manifest, "legacy_detail")
        _required_source_bytes(source_bytes, manifest, "legacy_summary")
        legacy = _legacy_opportunities(detail, source_id)
        duplicate_streams = []
    coverage_gaps = _coverage_gap_payloads(source_bytes, manifest)
    verified = _verified_snapshot_opportunities(source_bytes, manifest)
    expected = (
        [("source_registered", dict(manifest))]
        + [("opportunity", item) for item in legacy]
        + [("duplicate_stream", item) for item in duplicate_streams]
        + [("coverage_gap", item) for item in coverage_gaps]
        + [("opportunity", item) for item in verified]
    )
    if len(events) != len(expected) or any(
        event.get("event_type") != event_type or event.get("payload") != payload
        for event, (event_type, payload) in zip(events, expected)
    ):
        raise HistoricalOOSEvidenceError(
            "ledger content does not match immutable source evidence"
        )
    opportunities = [
        event["payload"] for event in events if event.get("event_type") == "opportunity"
    ]
    if not opportunities:
        raise HistoricalOOSEvidenceError("ledger has no historical opportunities")
    reported_max = max(
        opportunity["reported_evaluation"]["final6_hits"]
        for opportunity in opportunities
    )
    verified_hits = [
        opportunity["reported_evaluation"]["final6_hits"]
        for opportunity in opportunities
        if opportunity.get("forecast", {}).get("snapshot_status")
        == "verified_full_snapshot"
    ]
    result = {
        "event_count": len(events),
        "global_final6_max": None,
        "global_final6_max_status": "unknown_due_to_incomplete_coverage",
        "ledger_sha256": sha256(ledger_bytes).hexdigest(),
        "reported_final6_max": reported_max,
        "verified_full_snapshot_final6_max": (
            max(verified_hits) if verified_hits else None
        ),
    }
    _validate_expected_high_water(manifest, result)
    return result
