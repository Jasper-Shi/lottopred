"""Append-only governance for invalidated historical OOS evidence.

This module does not import data, models, predictors, or the project scorer.  It
validates the already-registered historical ledger as an opaque canonical hash
chain, appends a data-integrity tombstone, and derives the governed evidence
view from those event semantics.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterator, Mapping, Sequence
from datetime import date
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import Any

ZERO_HASH = "0" * 64
LEGACY_EVENT_COUNT = 18_259
LEGACY_OPPORTUNITY_COUNT = 18_251
LEGACY_LEDGER_SHA256 = (
    "546d21c96a3f3c5f077ea3b07b7a654a4d4b556a32274a5e17214443de0bf797"
)
LEGACY_HEAD_EVENT_SHA256 = (
    "a8d1d9168eabda5914e8e0b5da4983524ada7f9b1bbe204e22bb1a645e511f19"
)
TOMBSTONE_STATUS = "no_eligible_evidence_after_data_integrity_tombstone"
DEPLOYMENT_STATUSES = frozenset({"awaiting_main_branch_pin", "pinned_to_main_branch"})
CLOSED_NONPROMOTION_VERSIONS = (
    "V2",
    "V4",
    "V5",
    "V6",
    "V7",
    "V8",
    "V10",
    "V11",
)


class HistoricalOOSTombstoneError(RuntimeError):
    """Raised when the ledger or its governance events fail closed."""


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
        raise HistoricalOOSTombstoneError(
            "historical OOS governance is not canonical finite JSON"
        ) from exc


def _is_hex(value: object, length: int) -> bool:
    return (
        isinstance(value, str)
        and len(value) == length
        and all(character in "0123456789abcdef" for character in value)
    )


def _artifact_path(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise HistoricalOOSTombstoneError(f"{label} path is required")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts:
        raise HistoricalOOSTombstoneError(f"{label} path must be repository-relative")
    return path.as_posix()


def _event(
    sequence: int,
    previous_hash: str,
    event_type: str,
    payload: Mapping[str, Any],
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


def _canonical_chain(raw: bytes) -> list[dict[str, Any]]:
    lines = raw.splitlines(keepends=True)
    if not lines:
        raise HistoricalOOSTombstoneError("historical OOS ledger is empty")
    events: list[dict[str, Any]] = []
    previous_hash = ZERO_HASH
    for sequence, line in enumerate(lines):
        if not line.endswith(b"\n"):
            raise HistoricalOOSTombstoneError(
                "historical OOS ledger line lacks newline terminator"
            )
        try:
            event = json.loads(line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise HistoricalOOSTombstoneError(
                "historical OOS ledger line is invalid JSON"
            ) from exc
        if not isinstance(event, dict) or _canonical_json(event) + b"\n" != line:
            raise HistoricalOOSTombstoneError(
                "historical OOS ledger line is not canonical JSON"
            )
        if event.get("sequence") != sequence:
            raise HistoricalOOSTombstoneError(
                "historical OOS ledger sequence is not contiguous"
            )
        if event.get("previous_event_sha256") != previous_hash:
            raise HistoricalOOSTombstoneError(
                "historical OOS ledger previous-event hash mismatch"
            )
        without_hash = dict(event)
        event_hash = without_hash.pop("event_sha256", None)
        expected_hash = sha256(
            _canonical_json(without_hash) + previous_hash.encode("ascii")
        ).hexdigest()
        if event_hash != expected_hash:
            raise HistoricalOOSTombstoneError(
                "historical OOS ledger event hash mismatch"
            )
        events.append(event)
        previous_hash = expected_hash
    return events


def _legacy_prefix(raw: bytes, events: Sequence[Mapping[str, Any]]) -> bytes:
    lines = raw.splitlines(keepends=True)
    if len(lines) < LEGACY_EVENT_COUNT:
        raise HistoricalOOSTombstoneError(
            "historical OOS ledger is shorter than the registered legacy prefix"
        )
    prefix = b"".join(lines[:LEGACY_EVENT_COUNT])
    if (
        sha256(prefix).hexdigest() != LEGACY_LEDGER_SHA256
        or events[LEGACY_EVENT_COUNT - 1].get("event_sha256")
        != LEGACY_HEAD_EVENT_SHA256
    ):
        raise HistoricalOOSTombstoneError(
            "historical OOS legacy prefix identity mismatch"
        )
    return prefix


def _event_specs(
    *,
    effective_date: str,
    incident_id: str,
    incident_path: str,
    incident_sha256: str,
    incident_artifact_commit: str,
    seal_path: str,
    seal_sha256: str,
    sealed_artifact_commit: str,
    deployment_status: str,
    main_deployment_commit: str | None,
) -> tuple[tuple[str, dict[str, Any]], ...]:
    try:
        if date.fromisoformat(effective_date).isoformat() != effective_date:
            raise ValueError
    except (TypeError, ValueError) as exc:
        raise HistoricalOOSTombstoneError("effective_date must be an ISO date") from exc
    if not isinstance(incident_id, str) or not incident_id:
        raise HistoricalOOSTombstoneError("incident_id is required")
    for value, label, length in (
        (incident_sha256, "incident SHA-256", 64),
        (incident_artifact_commit, "incident artifact commit", 40),
        (seal_sha256, "seal SHA-256", 64),
        (sealed_artifact_commit, "sealed artifact commit", 40),
    ):
        if not _is_hex(value, length):
            raise HistoricalOOSTombstoneError(f"{label} is invalid")
    if deployment_status not in DEPLOYMENT_STATUSES:
        raise HistoricalOOSTombstoneError("deployment status is invalid")
    if deployment_status == "awaiting_main_branch_pin":
        if main_deployment_commit is not None:
            raise HistoricalOOSTombstoneError(
                "awaiting deployment must not claim a main branch commit"
            )
    elif not _is_hex(main_deployment_commit, 40):
        raise HistoricalOOSTombstoneError(
            "pinned deployment requires a main branch commit"
        )

    authority = {
        "deployment": {
            "main_branch_commit": main_deployment_commit,
            "status": deployment_status,
        },
        "incident": {
            "artifact_commit": incident_artifact_commit,
            "path": _artifact_path(incident_path, label="incident"),
            "sha256": incident_sha256,
        },
        "seal": {
            "path": _artifact_path(seal_path, label="seal"),
            "sealed_artifact_commit": sealed_artifact_commit,
            "sha256": seal_sha256,
        },
    }
    return (
        (
            "data_integrity_incident_registered",
            {
                "authority": authority,
                "effective_date": effective_date,
                "incident_id": incident_id,
            },
        ),
        (
            "opportunity_set_tombstoned",
            {
                "disposition": {
                    "eligible": False,
                    "eligibility": "ineligible",
                    "evidence_use": "registered_data_only",
                },
                "effective_date": effective_date,
                "incident_id": incident_id,
                "selection": {
                    "event_type": "opportunity",
                    "legacy_prefix_event_count": LEGACY_EVENT_COUNT,
                    "mode": "all_matching_events_in_legacy_prefix",
                },
            },
        ),
        (
            "high_water_erratum",
            {
                "effective_date": effective_date,
                "eligible_final6_high_water": None,
                "eligible_opportunity_count": 0,
                "eligible_top12_high_water": None,
                "incident_id": incident_id,
                "model_disposition": {
                    "closed_nonpromotion_retained_for_versions": list(
                        CLOSED_NONPROMOTION_VERSIONS
                    ),
                    "legacy_opportunity_metric_scope": (
                        "all_opportunities_in_legacy_prefix"
                    ),
                    "legacy_opportunity_numeric_metrics": "withdrawn",
                    "v1_operational_status": "paused_baseline_no_edge_claim",
                    "v3_operational_status": ("paused_shadow_nonpromotion_retained"),
                    "v3_promotion_status": "never_promoted",
                    "v9_numeric_evidence": "none",
                },
                "status": TOMBSTONE_STATUS,
                "stop_global_search": False,
            },
        ),
    )


def _governed_result(
    *,
    raw: bytes,
    events: Sequence[Mapping[str, Any]],
    specs: Sequence[tuple[str, Mapping[str, Any]]],
) -> dict[str, Any]:
    prefix = _legacy_prefix(raw, events)
    if len(events) != LEGACY_EVENT_COUNT + len(specs):
        raise HistoricalOOSTombstoneError(
            "historical OOS tombstone suffix must contain exactly three events"
        )
    suffix = events[LEGACY_EVENT_COUNT:]
    expected_types = [event_type for event_type, _payload in specs]
    if [event.get("event_type") for event in suffix] != expected_types:
        raise HistoricalOOSTombstoneError(
            "historical OOS tombstone event order is invalid"
        )
    if suffix[0].get("payload") != specs[0][1]:
        raise HistoricalOOSTombstoneError(
            "historical OOS incident authority identity mismatch"
        )
    if suffix[1].get("payload") != specs[1][1]:
        raise HistoricalOOSTombstoneError(
            "historical OOS opportunity tombstone semantics mismatch"
        )

    historical_opportunities = [
        event
        for event in events[:LEGACY_EVENT_COUNT]
        if event.get("event_type") == "opportunity"
    ]
    if len(historical_opportunities) != LEGACY_OPPORTUNITY_COUNT:
        raise HistoricalOOSTombstoneError(
            "historical OOS opportunity count differs from the fixed prefix"
        )
    selector = suffix[1]["payload"]["selection"]
    selected_sequences = {
        event["sequence"]
        for event in events[: selector["legacy_prefix_event_count"]]
        if event.get("event_type") == selector["event_type"]
    }
    eligible_opportunities = [
        event
        for event in historical_opportunities
        if event["sequence"] not in selected_sequences
    ]
    eligible_final6 = [
        event["payload"]["reported_evaluation"]["final6_hits"]
        for event in eligible_opportunities
    ]
    eligible_top12 = [
        event["payload"]["reported_evaluation"]["top12_hits"]
        for event in eligible_opportunities
    ]
    derived = {
        "eligible_final6_high_water": (
            max(eligible_final6) if eligible_final6 else None
        ),
        "eligible_opportunity_count": len(eligible_opportunities),
        "eligible_top12_high_water": max(eligible_top12) if eligible_top12 else None,
        "status": (
            TOMBSTONE_STATUS
            if not eligible_opportunities
            else "eligible_historical_evidence_remains"
        ),
        "stop_global_search": any(
            event["payload"].get("classification", {}).get("stop_global_search") is True
            for event in eligible_opportunities
        ),
    }
    erratum = suffix[2].get("payload")
    expected_erratum = dict(specs[2][1])
    for key, value in derived.items():
        expected_erratum[key] = value
    if erratum != expected_erratum:
        raise HistoricalOOSTombstoneError(
            "historical OOS high-water erratum does not match governed projection"
        )
    if len(selected_sequences) != LEGACY_OPPORTUNITY_COUNT or suffix[1]["payload"][
        "disposition"
    ] != {
        "eligible": False,
        "eligibility": "ineligible",
        "evidence_use": "registered_data_only",
    }:
        raise HistoricalOOSTombstoneError(
            "historical OOS tombstone does not cover every old opportunity"
        )
    model_disposition = erratum["model_disposition"]
    return {
        **derived,
        "authority": suffix[0]["payload"]["authority"],
        "closed_nonpromotion_retained_for_versions": model_disposition[
            "closed_nonpromotion_retained_for_versions"
        ],
        "event_count": len(events),
        "legacy_opportunity_metric_scope": model_disposition[
            "legacy_opportunity_metric_scope"
        ],
        "legacy_opportunity_numeric_metrics": model_disposition[
            "legacy_opportunity_numeric_metrics"
        ],
        "historical_opportunity_count": len(historical_opportunities),
        "ledger_sha256": sha256(raw).hexdigest(),
        "legacy_ledger_sha256": LEGACY_LEDGER_SHA256,
        "legacy_prefix_preserved": raw.startswith(prefix),
        "registered_data_only_opportunity_count": len(selected_sequences),
        "v1_operational_status": model_disposition["v1_operational_status"],
        "v3_operational_status": model_disposition["v3_operational_status"],
        "v3_promotion_status": model_disposition["v3_promotion_status"],
        "v9_numeric_evidence": model_disposition["v9_numeric_evidence"],
    }


def validate_data_integrity_tombstone(
    *,
    ledger_path: Path,
    effective_date: str,
    incident_id: str,
    incident_path: str,
    incident_sha256: str,
    incident_artifact_commit: str,
    seal_path: str,
    seal_sha256: str,
    sealed_artifact_commit: str,
    deployment_status: str,
    main_deployment_commit: str | None,
) -> dict[str, Any]:
    """Validate authority bindings and derive the strict governed view."""

    specs = _event_specs(
        effective_date=effective_date,
        incident_id=incident_id,
        incident_path=incident_path,
        incident_sha256=incident_sha256,
        incident_artifact_commit=incident_artifact_commit,
        seal_path=seal_path,
        seal_sha256=seal_sha256,
        sealed_artifact_commit=sealed_artifact_commit,
        deployment_status=deployment_status,
        main_deployment_commit=main_deployment_commit,
    )
    try:
        raw = ledger_path.read_bytes()
    except OSError as exc:
        raise HistoricalOOSTombstoneError(
            "historical OOS ledger is unreadable"
        ) from exc
    events = _canonical_chain(raw)
    return _governed_result(raw=raw, events=events, specs=specs)


def governed_opportunity_view(
    *,
    ledger_path: Path,
    effective_date: str,
    incident_id: str,
    incident_path: str,
    incident_sha256: str,
    incident_artifact_commit: str,
    seal_path: str,
    seal_sha256: str,
    sealed_artifact_commit: str,
    deployment_status: str,
    main_deployment_commit: str | None,
) -> Iterator[dict[str, Any]]:
    """Yield the immutable raw opportunities with their strict-view overlay."""

    specs = _event_specs(
        effective_date=effective_date,
        incident_id=incident_id,
        incident_path=incident_path,
        incident_sha256=incident_sha256,
        incident_artifact_commit=incident_artifact_commit,
        seal_path=seal_path,
        seal_sha256=seal_sha256,
        sealed_artifact_commit=sealed_artifact_commit,
        deployment_status=deployment_status,
        main_deployment_commit=main_deployment_commit,
    )
    try:
        raw = ledger_path.read_bytes()
    except OSError as exc:
        raise HistoricalOOSTombstoneError(
            "historical OOS ledger is unreadable"
        ) from exc
    events = _canonical_chain(raw)
    _governed_result(raw=raw, events=events, specs=specs)
    tombstone = events[LEGACY_EVENT_COUNT + 1]
    disposition = tombstone["payload"]["disposition"]
    for event in events[:LEGACY_EVENT_COUNT]:
        if event.get("event_type") != "opportunity":
            continue
        yield {
            "governance": {
                **disposition,
                "incident_id": incident_id,
                "tombstone_event_sha256": tombstone["event_sha256"],
            },
            "raw_event": event,
        }


def append_data_integrity_tombstone(
    *,
    ledger_path: Path,
    effective_date: str,
    incident_id: str,
    incident_path: str,
    incident_sha256: str,
    incident_artifact_commit: str,
    seal_path: str,
    seal_sha256: str,
    sealed_artifact_commit: str,
    deployment_status: str,
    main_deployment_commit: str | None,
) -> dict[str, Any]:
    """Append the incident, tombstone, and erratum to the fixed legacy ledger."""

    specs = _event_specs(
        effective_date=effective_date,
        incident_id=incident_id,
        incident_path=incident_path,
        incident_sha256=incident_sha256,
        incident_artifact_commit=incident_artifact_commit,
        seal_path=seal_path,
        seal_sha256=seal_sha256,
        sealed_artifact_commit=sealed_artifact_commit,
        deployment_status=deployment_status,
        main_deployment_commit=main_deployment_commit,
    )
    try:
        before = ledger_path.read_bytes()
    except OSError as exc:
        raise HistoricalOOSTombstoneError(
            "historical OOS ledger is unreadable"
        ) from exc
    events = _canonical_chain(before)
    prefix = _legacy_prefix(before, events)
    expected_events = list(events[:LEGACY_EVENT_COUNT])
    previous_hash = LEGACY_HEAD_EVENT_SHA256
    for event_type, payload in specs:
        event = _event(len(expected_events), previous_hash, event_type, payload)
        expected_events.append(event)
        previous_hash = event["event_sha256"]
    expected = prefix + b"".join(
        _canonical_json(event) + b"\n" for event in expected_events[LEGACY_EVENT_COUNT:]
    )

    if before == prefix:
        try:
            with ledger_path.open("ab") as handle:
                handle.write(expected[len(prefix) :])
                handle.flush()
                os.fsync(handle.fileno())
        except OSError as exc:
            raise HistoricalOOSTombstoneError(
                "historical OOS tombstone append failed"
            ) from exc
    elif before != expected:
        raise HistoricalOOSTombstoneError(
            "historical OOS ledger is not the accepted prefix or tombstone state"
        )
    try:
        final = ledger_path.read_bytes()
    except OSError as exc:
        raise HistoricalOOSTombstoneError(
            "historical OOS tombstone append is unreadable"
        ) from exc
    if final != expected:
        raise HistoricalOOSTombstoneError(
            "historical OOS tombstone append was not durable and exact"
        )
    final_events = _canonical_chain(final)
    return _governed_result(raw=final, events=final_events, specs=specs)
