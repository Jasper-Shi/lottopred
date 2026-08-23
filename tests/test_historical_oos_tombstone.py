from __future__ import annotations

import json
import os
import subprocess
import sys
from hashlib import sha256
from pathlib import Path

import pytest

from lotto649.historical_oos_tombstone import (
    LEGACY_EVENT_COUNT,
    LEGACY_LEDGER_SHA256,
    HistoricalOOSTombstoneError,
    append_data_integrity_tombstone,
    governed_opportunity_view,
    validate_data_integrity_tombstone,
)

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "reports/historical_oos/global_opportunities.jsonl"
SCHEMA = ROOT / "reports/historical_oos/global_opportunities.schema.json"
PROTOCOL = ROOT / "docs/HISTORICAL_OOS_EVIDENCE_PROTOCOL.md"
AUTHORITY = {
    "effective_date": "2026-08-23",
    "incident_id": "DI-2026-08-20-registered-history",
    "incident_path": (
        "evidence/data_integrity/DI-2026-08-20-registered-history/incident.json"
    ),
    "incident_sha256": (
        "b74e21722e1d95667504415c445169969d8a2810eaf3df90be3d83b359234ce5"
    ),
    "incident_artifact_commit": "b04393944ef12f78417dfb6151343c72d4c2a2ac",
    "seal_path": ("evidence/data_integrity/DI-2026-08-20-registered-history/seal.json"),
    "seal_sha256": ("80397752105b567d6a8bdd3673b12ffa470a12efbd792719a4f6c89ef391f6fd"),
    "sealed_artifact_commit": "b04393944ef12f78417dfb6151343c72d4c2a2ac",
    "deployment_status": "pinned_to_main_branch",
    "main_deployment_commit": "8debb2e13d117124dbf4b7cdf7e8744ee23e0e89",
}


def _append(tmp_path: Path) -> tuple[Path, bytes, dict]:
    legacy_bytes = b"".join(
        LEDGER.read_bytes().splitlines(keepends=True)[:LEGACY_EVENT_COUNT]
    )
    ledger_path = tmp_path / "global_opportunities.jsonl"
    ledger_path.write_bytes(legacy_bytes)
    result = append_data_integrity_tombstone(
        ledger_path=ledger_path,
        **AUTHORITY,
    )
    return ledger_path, legacy_bytes, result


def _git_bytes(*args: str) -> bytes:
    completed = subprocess.run(
        ("git", "-C", str(ROOT), *args),
        check=True,
        capture_output=True,
        env={
            **os.environ,
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_GRAFT_FILE": os.devnull,
        },
    )
    return completed.stdout


def _rechain(events: list[dict]) -> bytes:
    previous_hash = "0" * 64
    lines: list[bytes] = []
    for sequence, event in enumerate(events):
        without_hash = {
            "event_type": event["event_type"],
            "payload": event["payload"],
            "previous_event_sha256": previous_hash,
            "sequence": sequence,
        }
        canonical_without_hash = json.dumps(
            without_hash,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode()
        event_hash = sha256(
            canonical_without_hash + previous_hash.encode("ascii")
        ).hexdigest()
        chained = {**without_hash, "event_sha256": event_hash}
        lines.append(
            json.dumps(
                chained,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            ).encode()
            + b"\n"
        )
        previous_hash = event_hash
    return b"".join(lines)


def test_append_preserves_the_fixed_18259_event_ledger_as_an_exact_prefix(
    tmp_path: Path,
) -> None:
    ledger_path, legacy_bytes, result = _append(tmp_path)

    appended_bytes = ledger_path.read_bytes()
    events = [json.loads(line) for line in appended_bytes.splitlines()]
    assert len(legacy_bytes.splitlines()) == LEGACY_EVENT_COUNT == 18_259
    assert sha256(legacy_bytes).hexdigest() == LEGACY_LEDGER_SHA256
    assert appended_bytes.startswith(legacy_bytes)
    assert appended_bytes[: len(legacy_bytes)] == legacy_bytes
    assert [event["event_type"] for event in events[LEGACY_EVENT_COUNT:]] == [
        "data_integrity_incident_registered",
        "opportunity_set_tombstoned",
        "high_water_erratum",
    ]
    assert result["event_count"] == 18_262
    assert result["legacy_prefix_preserved"] is True


def test_governed_view_tombstones_every_old_opportunity_and_uses_null_high_water(
    tmp_path: Path,
) -> None:
    ledger_path, legacy_bytes, _result = _append(tmp_path)

    result = validate_data_integrity_tombstone(
        ledger_path=ledger_path,
        **AUTHORITY,
    )
    suffix = ledger_path.read_bytes()[len(legacy_bytes) :]
    events = [json.loads(line) for line in suffix.splitlines()]
    tombstone = events[1]["payload"]
    erratum = events[2]["payload"]

    assert tombstone["selection"] == {
        "event_type": "opportunity",
        "legacy_prefix_event_count": 18_259,
        "mode": "all_matching_events_in_legacy_prefix",
    }
    assert tombstone["disposition"] == {
        "eligible": False,
        "eligibility": "ineligible",
        "evidence_use": "registered_data_only",
    }
    assert result["historical_opportunity_count"] == 18_251
    assert result["registered_data_only_opportunity_count"] == 18_251
    assert result["eligible_opportunity_count"] == 0
    assert result["eligible_final6_high_water"] is None
    assert result["eligible_top12_high_water"] is None
    assert result["ledger_sha256"] == (
        "1ab120c1db07fd2cc0b0dd34408c7182fab8ee2f2e00c265e258827d6623e476"
    )
    assert result["status"] == ("no_eligible_evidence_after_data_integrity_tombstone")
    assert result["stop_global_search"] is False
    assert erratum["eligible_final6_high_water"] is None
    assert erratum["eligible_top12_high_water"] is None
    assert b"0/6" not in suffix


def test_erratum_withdraws_all_legacy_metrics_and_preserves_exact_dispositions(
    tmp_path: Path,
) -> None:
    ledger_path, legacy_bytes, _result = _append(tmp_path)

    result = validate_data_integrity_tombstone(
        ledger_path=ledger_path,
        **AUTHORITY,
    )
    suffix = ledger_path.read_bytes()[len(legacy_bytes) :]
    closed_versions = ["V2", "V4", "V5", "V6", "V7", "V8", "V10", "V11"]

    assert result["legacy_opportunity_numeric_metrics"] == "withdrawn"
    assert result["legacy_opportunity_metric_scope"] == (
        "all_opportunities_in_legacy_prefix"
    )
    assert result["closed_nonpromotion_retained_for_versions"] == closed_versions
    assert result["v1_operational_status"] == "paused_baseline_no_edge_claim"
    assert result["v3_operational_status"] == ("paused_shadow_nonpromotion_retained")
    assert result["v3_promotion_status"] == "never_promoted"
    assert result["v9_numeric_evidence"] == "none"
    assert b"reported_final6_max" not in suffix
    assert b"verified_full_snapshot_final6_max" not in suffix


def test_offline_cli_requires_explicit_authority_and_validates_the_append(
    tmp_path: Path,
) -> None:
    ledger_path = tmp_path / "global_opportunities.jsonl"
    ledger_path.write_bytes(
        b"".join(LEDGER.read_bytes().splitlines(keepends=True)[:LEGACY_EVENT_COUNT])
    )
    command = (
        sys.executable,
        str(ROOT / "tools/append_historical_oos_tombstone.py"),
        "--ledger",
        str(ledger_path),
        "--effective-date",
        str(AUTHORITY["effective_date"]),
        "--incident-id",
        str(AUTHORITY["incident_id"]),
        "--incident-path",
        str(AUTHORITY["incident_path"]),
        "--incident-sha256",
        str(AUTHORITY["incident_sha256"]),
        "--incident-artifact-commit",
        str(AUTHORITY["incident_artifact_commit"]),
        "--seal-path",
        str(AUTHORITY["seal_path"]),
        "--seal-sha256",
        str(AUTHORITY["seal_sha256"]),
        "--sealed-artifact-commit",
        str(AUTHORITY["sealed_artifact_commit"]),
        "--deployment-status",
        str(AUTHORITY["deployment_status"]),
        "--main-deployment-commit",
        str(AUTHORITY["main_deployment_commit"]),
    )

    environment = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    appended = subprocess.run(
        command,
        check=True,
        capture_output=True,
        env=environment,
        text=True,
    )
    validated = subprocess.run(
        (*command, "--validate-only"),
        check=True,
        capture_output=True,
        env=environment,
        text=True,
    )

    assert json.loads(appended.stdout)["eligible_opportunity_count"] == 0
    assert json.loads(validated.stdout) == json.loads(appended.stdout)


def test_strict_view_marks_each_old_opportunity_without_mutating_raw_events(
    tmp_path: Path,
) -> None:
    ledger_path, legacy_bytes, _result = _append(tmp_path)
    raw_events = [json.loads(line) for line in legacy_bytes.splitlines()]
    raw_opportunities = [
        event for event in raw_events if event["event_type"] == "opportunity"
    ]

    governed = list(governed_opportunity_view(ledger_path=ledger_path, **AUTHORITY))

    assert len(governed) == len(raw_opportunities) == 18_251
    assert [item["raw_event"] for item in governed] == raw_opportunities
    assert all(
        item["governance"]["evidence_use"] == "registered_data_only"
        and item["governance"]["eligible"] is False
        and item["governance"]["eligibility"] == "ineligible"
        and item["governance"]["tombstone_event_sha256"]
        for item in governed
    )


def test_schema_registers_the_three_append_only_governance_event_types() -> None:
    schema = json.loads(SCHEMA.read_bytes())

    assert schema["properties"]["event_type"]["enum"][-3:] == [
        "data_integrity_incident_registered",
        "opportunity_set_tombstoned",
        "high_water_erratum",
    ]
    assert schema["$defs"]["opportunitySetTombstoned"]["properties"]["disposition"][
        "properties"
    ] == {
        "eligible": {"const": False},
        "eligibility": {"const": "ineligible"},
        "evidence_use": {"const": "registered_data_only"},
    }
    erratum = schema["$defs"]["highWaterErratum"]["properties"]
    assert erratum["eligible_final6_high_water"] == {"type": "null"}
    assert erratum["eligible_top12_high_water"] == {"type": "null"}
    assert erratum["stop_global_search"] == {"const": False}
    disposition = erratum["model_disposition"]["properties"]
    assert disposition["legacy_opportunity_metric_scope"] == {
        "const": "all_opportunities_in_legacy_prefix"
    }
    assert disposition["legacy_opportunity_numeric_metrics"] == {"const": "withdrawn"}
    assert schema["$defs"]["closedNonpromotionVersions"]["const"] == [
        "V2",
        "V4",
        "V5",
        "V6",
        "V7",
        "V8",
        "V10",
        "V11",
    ]


def test_incident_and_seal_authority_are_bound_to_the_deployed_main_pin(
    tmp_path: Path,
) -> None:
    ledger_path, _legacy_bytes, _result = _append(tmp_path)

    result = validate_data_integrity_tombstone(
        ledger_path=ledger_path,
        **AUTHORITY,
    )

    assert result["authority"] == {
        "deployment": {
            "main_branch_commit": AUTHORITY["main_deployment_commit"],
            "status": "pinned_to_main_branch",
        },
        "incident": {
            "artifact_commit": AUTHORITY["incident_artifact_commit"],
            "path": AUTHORITY["incident_path"],
            "sha256": AUTHORITY["incident_sha256"],
        },
        "seal": {
            "path": AUTHORITY["seal_path"],
            "sealed_artifact_commit": AUTHORITY["sealed_artifact_commit"],
            "sha256": AUTHORITY["seal_sha256"],
        },
    }
    with pytest.raises(
        HistoricalOOSTombstoneError,
        match="incident authority identity mismatch",
    ):
        validate_data_integrity_tombstone(
            ledger_path=ledger_path,
            **{**AUTHORITY, "incident_sha256": "0" * 64},
        )


def test_deployed_authority_matches_the_registered_git_artifacts() -> None:
    deployment_commit = AUTHORITY["main_deployment_commit"]
    incident_path = AUTHORITY["incident_path"]
    seal_path = AUTHORITY["seal_path"]
    assert isinstance(deployment_commit, str)

    incident_bytes = _git_bytes("show", f"{deployment_commit}:{incident_path}")
    seal_bytes = _git_bytes("show", f"{deployment_commit}:{seal_path}")
    assert sha256(incident_bytes).hexdigest() == AUTHORITY["incident_sha256"]
    assert sha256(seal_bytes).hexdigest() == AUTHORITY["seal_sha256"]
    assert (
        _git_bytes(
            "show",
            f"{AUTHORITY['incident_artifact_commit']}:{incident_path}",
        )
        == incident_bytes
    )
    subprocess.run(
        (
            "git",
            "-C",
            str(ROOT),
            "merge-base",
            "--is-ancestor",
            str(AUTHORITY["sealed_artifact_commit"]),
            deployment_commit,
        ),
        check=True,
        capture_output=True,
        env={
            **os.environ,
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_GRAFT_FILE": os.devnull,
        },
    )
    seal = json.loads(seal_bytes)
    assert seal["artifact_commit"] == AUTHORITY["sealed_artifact_commit"]


def test_protocol_states_the_tombstone_semantics_without_numeric_reinterpretation() -> (
    None
):
    protocol = PROTOCOL.read_text()

    for statement in (
        "no_eligible_evidence_after_data_integrity_tombstone",
        "registered_data_only",
        "eligible=false",
        "eligible count is `0`",
        "Final-6 high-water is `null`",
        "Top-12 high-water is `null`",
        "must never be rendered as `0/6`",
        "stop_global_search=false",
        "pinned_to_main_branch",
        "all 18,251 opportunities",
        "V1 is a paused baseline",
        "never-promoted shadow",
        "V9 has no numeric evidence",
    ):
        assert statement in protocol


def test_repository_ledger_is_the_validated_tombstoned_artifact() -> None:
    result = validate_data_integrity_tombstone(
        ledger_path=LEDGER,
        **AUTHORITY,
    )

    assert result["event_count"] == 18_262
    assert result["legacy_prefix_preserved"] is True
    assert result["eligible_opportunity_count"] == 0
    assert result["eligible_final6_high_water"] is None
    assert result["eligible_top12_high_water"] is None
    assert result["ledger_sha256"] == (
        "1ab120c1db07fd2cc0b0dd34408c7182fab8ee2f2e00c265e258827d6623e476"
    )


def test_fixed_prefix_identity_rejects_a_fully_rechained_old_event_tamper(
    tmp_path: Path,
) -> None:
    ledger_path, _legacy_bytes, _result = _append(tmp_path)
    events = [json.loads(line) for line in ledger_path.read_bytes().splitlines()]
    events[0]["payload"]["tampered"] = True
    ledger_path.write_bytes(_rechain(events))

    with pytest.raises(
        HistoricalOOSTombstoneError,
        match="legacy prefix identity mismatch",
    ):
        validate_data_integrity_tombstone(ledger_path=ledger_path, **AUTHORITY)


def test_rechained_erratum_cannot_self_report_a_numeric_zero_high_water(
    tmp_path: Path,
) -> None:
    ledger_path, _legacy_bytes, _result = _append(tmp_path)
    events = [json.loads(line) for line in ledger_path.read_bytes().splitlines()]
    events[-1]["payload"]["eligible_final6_high_water"] = 0
    ledger_path.write_bytes(_rechain(events))

    with pytest.raises(
        HistoricalOOSTombstoneError,
        match="erratum does not match governed projection",
    ):
        validate_data_integrity_tombstone(ledger_path=ledger_path, **AUTHORITY)


def test_append_is_idempotent_for_the_same_explicit_authority(tmp_path: Path) -> None:
    ledger_path, _legacy_bytes, first = _append(tmp_path)
    first_bytes = ledger_path.read_bytes()

    second = append_data_integrity_tombstone(ledger_path=ledger_path, **AUTHORITY)

    assert second == first
    assert ledger_path.read_bytes() == first_bytes


@pytest.mark.parametrize(
    ("deployment_status", "main_deployment_commit", "message"),
    [
        (
            "awaiting_main_branch_pin",
            "a" * 40,
            "awaiting deployment must not claim",
        ),
        ("pinned_to_main_branch", None, "requires a main branch commit"),
    ],
)
def test_deployment_status_cannot_fabricate_or_omit_a_main_pin(
    tmp_path: Path,
    deployment_status: str,
    main_deployment_commit: str | None,
    message: str,
) -> None:
    ledger_path = tmp_path / "global_opportunities.jsonl"
    legacy_bytes = b"".join(
        LEDGER.read_bytes().splitlines(keepends=True)[:LEGACY_EVENT_COUNT]
    )
    ledger_path.write_bytes(legacy_bytes)

    with pytest.raises(HistoricalOOSTombstoneError, match=message):
        append_data_integrity_tombstone(
            ledger_path=ledger_path,
            **{
                **AUTHORITY,
                "deployment_status": deployment_status,
                "main_deployment_commit": main_deployment_commit,
            },
        )
    assert ledger_path.read_bytes() == legacy_bytes
