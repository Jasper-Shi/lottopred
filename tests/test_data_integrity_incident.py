from __future__ import annotations

from dataclasses import replace
from datetime import date
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "build_data_integrity_incident.py"
TOOL_SPEC = importlib.util.spec_from_file_location(
    "build_data_integrity_incident_tool", TOOL_PATH
)
assert TOOL_SPEC is not None and TOOL_SPEC.loader is not None
incident_tool = importlib.util.module_from_spec(TOOL_SPEC)
sys.modules[TOOL_SPEC.name] = incident_tool
TOOL_SPEC.loader.exec_module(incident_tool)


ANNUAL_HTML = b"""<!doctype html><table>
<tr><td class="date">2020-01-04</td><td>
<div class="numerosGagnants principal">
<span>08</span><span>09</span><span>10</span><span>11</span>
<span>12</span><span>13</span>(<span>14</span>)
</div></td></tr>
<tr><td class="date">2020-01-01</td><td>
<div class="numerosGagnants principal">
<span>01</span><span>02</span><span>03</span><span>04</span>
<span>05</span><span>06</span>(<span>07</span>)
</div></td></tr>
</table>"""

OLD_CSV = b"""draw_date,n1,n2,n3,n4,n5,n6,bonus
2020-01-01,1,2,3,4,5,8,7
2020-01-02,15,16,17,18,19,20,21
"""


def _git(repository: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repository), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _fixture_policy(tmp_path: Path):
    repository = tmp_path / "repo"
    repository.mkdir()
    _git(repository, "init", "-q")
    _git(repository, "config", "user.email", "test@example.invalid")
    _git(repository, "config", "user.name", "Test")
    old_path = repository / "data" / "processed" / "draws.csv"
    old_path.parent.mkdir(parents=True)
    old_path.write_bytes(OLD_CSV)
    _git(repository, "add", "data/processed/draws.csv")
    _git(repository, "commit", "-qm", "fixture old history")
    commit = _git(repository, "rev-parse", "HEAD")
    blob = _git(repository, "rev-parse", f"{commit}:data/processed/draws.csv")

    annual_dir = tmp_path / "annual"
    detail_dir = tmp_path / "detail"
    annual_dir.mkdir()
    detail_dir.mkdir()
    annual_path = annual_dir / "2020.html"
    annual_path.write_bytes(ANNUAL_HTML)
    os.utime(annual_path, (1_787_184_000, 1_787_184_000))

    policy = incident_tool.IncidentPolicy(
        incident_id="DI-TEST",
        created_at="2026-08-20T05:00:00Z",
        old_commit=commit,
        old_path="data/processed/draws.csv",
        old_blob=blob,
        old_bytes_sha256=sha256(OLD_CSV).hexdigest(),
        old_count=2,
        old_rows_sha256=(
            "ad319ed0dcb6c888c3cebf641bb7a4f76549418b16a3c11a9b67c053022a33d6"
        ),
        annual_years=(2020,),
        detail_dates=(),
        expected_dates=(date(2020, 1, 1), date(2020, 1, 4)),
        expected_source_assets_sha256=(
            "10c225cb80b218c755f04ac6b78a24028ed255e30a0f6bcbde6ca9b2d828de5c"
        ),
        expected_official_text_rows_sha256=(
            "c2b8f97e822acf87008dc0fde617bcd5ade9be6d9aaae7c43e30bf71c72d9098"
        ),
        expected_official_rows_sha256=(
            "3ba186f94ca5ec146677a11201408ce9692b95f0330e3f2b644c139913ed974c"
        ),
        expected_changes=(
            incident_tool.ChangeExpectation(date(2020, 1, 1), "update"),
            incident_tool.ChangeExpectation(date(2020, 1, 2), "delete"),
            incident_tool.ChangeExpectation(date(2020, 1, 4), "insert"),
        ),
        expected_summary=incident_tool.ExpectedSummary(
            old_count=2,
            official_count=2,
            decision_count=3,
            unchanged=0,
            inserted=1,
            deleted=1,
            updated=1,
            unresolved=0,
            corrected_count=2,
        ),
        require_full_schedule=False,
        official_fetch_batch_completed_at="2026-08-20T04:59:00Z",
        external_evidence=(),
    )
    return repository, annual_dir, detail_dir, policy


def _build(tmp_path: Path):
    repository, annual_dir, detail_dir, policy = _fixture_policy(tmp_path)
    output_root = tmp_path / "output"
    result = incident_tool.build_data_integrity_incident(
        annual_dir=annual_dir,
        detail_dir=detail_dir,
        repository=repository,
        output_root=output_root,
        policy=policy,
    )
    return repository, annual_dir, detail_dir, output_root, policy, result


def _coordinated_json_rewrite(output_root: Path, relative_path: str, mutate) -> None:
    artifact = output_root / relative_path
    payload = json.loads(artifact.read_text())
    mutate(payload)
    raw = (
        json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    ).encode()
    artifact.write_bytes(raw)
    incident_path = (
        output_root / "evidence" / "data_integrity" / "DI-TEST" / "incident.json"
    )
    incident = json.loads(incident_path.read_text())
    incident["artifact_inventory"][relative_path] = {
        "bytes": len(raw),
        "sha256": sha256(raw).hexdigest(),
    }
    incident_path.write_text(
        json.dumps(incident, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    )


def test_builds_a_closed_incident_only_after_external_manifest_validation(tmp_path):
    repository, _, _, output_root, policy, result = _build(tmp_path)

    incident_dir = output_root / "evidence" / "data_integrity" / policy.incident_id
    epoch_csv = (
        output_root
        / "data"
        / "processed"
        / "epochs"
        / policy.incident_id
        / "corrected_draws.csv"
    )
    assert sorted(path.name for path in incident_dir.iterdir()) == [
        "incident.json",
        "official_draws.csv",
        "reconciliation.manifest.json",
        "reviewed-adjudication.json",
        "source-index.json",
    ]
    assert epoch_csv.read_text() == (
        "draw_date,n1,n2,n3,n4,n5,n6,bonus\n"
        "2020-01-01,1,2,3,4,5,6,7\n"
        "2020-01-04,8,9,10,11,12,13,14\n"
    )
    assert result.summary.to_manifest_dict() == {
        "old_count": 2,
        "official_count": 2,
        "decision_count": 3,
        "unchanged": 0,
        "inserted": 1,
        "deleted": 1,
        "updated": 1,
        "unresolved": 0,
        "corrected_count": 2,
    }
    verified = incident_tool.verify_data_integrity_incident(
        repository=repository,
        output_root=output_root,
        policy=policy,
    )
    assert verified.corrected_draws == result.corrected_draws
    incident = json.loads((incident_dir / "incident.json").read_text())
    assert incident["seal_status"] == "awaiting_artifact_commit_seal"
    assert not (incident_dir / "seal.json").exists()


def test_rejects_semantically_unchanged_raw_source_byte_tampering(tmp_path):
    repository, annual_dir, detail_dir, policy = _fixture_policy(tmp_path)
    (annual_dir / "2020.html").write_bytes(ANNUAL_HTML + b"\n<!-- tampered -->")

    with pytest.raises(
        incident_tool.IncidentBuildError,
        match="raw source collection SHA-256 mismatch",
    ):
        incident_tool.build_data_integrity_incident(
            annual_dir=annual_dir,
            detail_dir=detail_dir,
            repository=repository,
            output_root=tmp_path / "output",
            policy=policy,
        )


def test_rejects_a_missing_expected_raw_source(tmp_path):
    repository, annual_dir, detail_dir, policy = _fixture_policy(tmp_path)
    (annual_dir / "2020.html").unlink()

    with pytest.raises(
        incident_tool.IncidentBuildError, match="annual raw source file set mismatch"
    ):
        incident_tool.build_data_integrity_incident(
            annual_dir=annual_dir,
            detail_dir=detail_dir,
            repository=repository,
            output_root=tmp_path / "output",
            policy=policy,
        )


def test_rejects_a_registered_old_git_blob_identity_mismatch(tmp_path):
    repository, annual_dir, detail_dir, policy = _fixture_policy(tmp_path)
    wrong_policy = replace(policy, old_blob="0" * 40)

    with pytest.raises(
        incident_tool.IncidentBuildError, match="old Git blob identity mismatch"
    ):
        incident_tool.build_data_integrity_incident(
            annual_dir=annual_dir,
            detail_dir=detail_dir,
            repository=repository,
            output_root=tmp_path / "output",
            policy=wrong_policy,
        )


@pytest.mark.parametrize(
    "relative_path",
    [
        "evidence/data_integrity/DI-TEST/reviewed-adjudication.json",
        "evidence/data_integrity/DI-TEST/reconciliation.manifest.json",
        "data/processed/epochs/DI-TEST/corrected_draws.csv",
    ],
)
def test_verifier_rejects_adjudication_manifest_or_csv_tampering(
    tmp_path, relative_path
):
    repository, _, _, output_root, policy, _ = _build(tmp_path)
    artifact = output_root / relative_path
    artifact.write_bytes(artifact.read_bytes() + b"\n")

    with pytest.raises(
        incident_tool.IncidentBuildError, match="artifact integrity mismatch"
    ):
        incident_tool.verify_data_integrity_incident(
            repository=repository,
            output_root=output_root,
            policy=policy,
        )


def test_builder_refuses_to_overwrite_an_existing_incident(tmp_path):
    repository, annual_dir, detail_dir, output_root, policy, _ = _build(tmp_path)

    with pytest.raises(incident_tool.IncidentBuildError, match="refusing to overwrite"):
        incident_tool.build_data_integrity_incident(
            annual_dir=annual_dir,
            detail_dir=detail_dir,
            repository=repository,
            output_root=output_root,
            policy=policy,
        )


def test_identical_source_bytes_with_different_mtimes_are_byte_deterministic(tmp_path):
    repository, annual_dir, detail_dir, policy = _fixture_policy(tmp_path)
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    incident_tool.build_data_integrity_incident(
        annual_dir=annual_dir,
        detail_dir=detail_dir,
        repository=repository,
        output_root=first_root,
        policy=policy,
    )
    os.utime(annual_dir / "2020.html", (1_800_000_000, 1_800_000_000))

    incident_tool.build_data_integrity_incident(
        annual_dir=annual_dir,
        detail_dir=detail_dir,
        repository=repository,
        output_root=second_root,
        policy=policy,
    )

    first_files = {
        path.relative_to(first_root): path.read_bytes()
        for path in first_root.rglob("*")
        if path.is_file()
    }
    second_files = {
        path.relative_to(second_root): path.read_bytes()
        for path in second_root.rglob("*")
        if path.is_file()
    }
    assert second_files == first_files


@pytest.mark.parametrize(
    ("case", "mutate"),
    [
        ("asset deletion", lambda payload: payload["assets"].clear()),
        ("schema", lambda payload: payload.update(schema_version="attacker-v1")),
        (
            "path",
            lambda payload: payload["assets"][0].update(
                relative_path="annual/attacker.html"
            ),
        ),
        ("scope", lambda payload: payload["assets"][0].update(scope="2019")),
        (
            "url",
            lambda payload: payload["assets"][0].update(
                url="https://attacker.invalid/2020"
            ),
        ),
        (
            "bytes",
            lambda payload: payload["assets"][0].update(
                bytes=payload["assets"][0]["bytes"] + 1
            ),
        ),
        (
            "raw SHA",
            lambda payload: payload["assets"][0].update(raw_sha256="0" * 64),
        ),
    ],
)
def test_verifier_rejects_coordinated_source_index_asset_rewrites(
    tmp_path, case, mutate
):
    repository, _, _, output_root, policy, _ = _build(tmp_path)
    relative_path = "evidence/data_integrity/DI-TEST/source-index.json"
    _coordinated_json_rewrite(output_root, relative_path, mutate)

    with pytest.raises(incident_tool.IncidentBuildError, match="source index"):
        incident_tool.verify_data_integrity_incident(
            repository=repository,
            output_root=output_root,
            policy=policy,
        )


def test_verifier_rejects_coordinated_external_evidence_and_corroboration_deletion(
    tmp_path,
):
    repository, annual_dir, detail_dir, policy = _fixture_policy(tmp_path)
    policy = replace(
        policy,
        external_evidence=(
            {
                "evidence_id": "fixture-corroboration",
                "provider": "Fixture archive",
                "source_type": "archived_result",
                "draw_dates": ["2020-01-01"],
                "url": "https://example.invalid/fixture",
                "download_bytes": 123,
                "download_sha256": "a" * 64,
                "frame_summary": "Fixture supports the official row.",
            },
        ),
    )
    output_root = tmp_path / "output"
    incident_tool.build_data_integrity_incident(
        annual_dir=annual_dir,
        detail_dir=detail_dir,
        repository=repository,
        output_root=output_root,
        policy=policy,
    )
    relative_path = "evidence/data_integrity/DI-TEST/reviewed-adjudication.json"

    def remove_review_evidence(payload):
        payload["external_evidence"] = []
        for change in payload["changes"]:
            change["corroborating_evidence_ids"] = []

    _coordinated_json_rewrite(output_root, relative_path, remove_review_evidence)

    with pytest.raises(incident_tool.IncidentBuildError, match="reviewed adjudication"):
        incident_tool.verify_data_integrity_incident(
            repository=repository,
            output_root=output_root,
            policy=policy,
        )


def test_nonembedded_external_assets_are_labeled_metadata_only(tmp_path):
    repository, annual_dir, detail_dir, policy = _fixture_policy(tmp_path)
    policy = replace(
        policy,
        external_evidence=(
            {
                "evidence_id": "fixture-corroboration",
                "provider": "Fixture archive",
                "source_type": "archived_result",
                "draw_dates": ["2020-01-01"],
                "url": "https://example.invalid/fixture",
                "download_bytes": 123,
                "download_sha256": "a" * 64,
                "frame_summary": "Fixture supports the official row.",
            },
        ),
    )
    output_root = tmp_path / "output"
    incident_tool.build_data_integrity_incident(
        annual_dir=annual_dir,
        detail_dir=detail_dir,
        repository=repository,
        output_root=output_root,
        policy=policy,
    )
    incident_dir = output_root / "evidence" / "data_integrity" / "DI-TEST"
    review = json.loads((incident_dir / "reviewed-adjudication.json").read_text())
    incident = json.loads((incident_dir / "incident.json").read_text())
    manifest = json.loads((incident_dir / "reconciliation.manifest.json").read_text())

    assert review["external_evidence_handling"] == {
        "artifact_count": 1,
        "artifact_status": "metadata_verified_during_review_not_embedded",
        "automatic_two_source_resolution_use": "none",
        "closure_basis": "externally_allowlisted_reviewed_adjudication",
    }
    assert {asset["artifact_status"] for asset in review["external_evidence"]} == {
        "metadata_verified_during_review_not_embedded"
    }
    assert incident["external_evidence_artifact_status"] == (
        "metadata_verified_during_review_not_embedded"
    )
    assert manifest["coverage"]["expected_date_count"] == 2
    assert incident["reconciliation_authority"]["evidence_independence_groups"] == []


def test_verifier_requires_the_exact_reconstructed_incident_authority(tmp_path):
    repository, _, _, output_root, policy, _ = _build(tmp_path)
    incident_path = (
        output_root / "evidence" / "data_integrity" / "DI-TEST" / "incident.json"
    )
    incident = json.loads(incident_path.read_text())
    incident["reconciliation_authority"]["attacker_note"] = "ignored extra field"
    incident_path.write_text(
        json.dumps(incident, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    )

    with pytest.raises(incident_tool.IncidentBuildError, match="authority differs"):
        incident_tool.verify_data_integrity_incident(
            repository=repository,
            output_root=output_root,
            policy=policy,
        )


@pytest.mark.parametrize("field", ["official_source", "reconciliation_summary"])
def test_verifier_rejects_coordinated_incident_derived_metadata_rewrites(
    tmp_path, field
):
    repository, _, _, output_root, policy, _ = _build(tmp_path)
    incident_path = (
        output_root / "evidence" / "data_integrity" / "DI-TEST" / "incident.json"
    )
    incident = json.loads(incident_path.read_text())
    if field == "official_source":
        incident[field]["asset_count"] = 0
    else:
        incident[field]["inserted"] = 0
    incident_path.write_text(
        json.dumps(incident, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    )

    with pytest.raises(
        incident_tool.IncidentBuildError, match="incident derived metadata"
    ):
        incident_tool.verify_data_integrity_incident(
            repository=repository,
            output_root=output_root,
            policy=policy,
        )
