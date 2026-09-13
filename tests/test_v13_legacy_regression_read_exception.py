"""Source/metadata checks for the narrowly authorized legacy regression lane."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "900054719a4ac089d4c059830b5c7162f2543616"
REG = "evidence/research_registrations/v13-legacy-regression-read-exception-v1.json"
R13 = "evidence/research_registrations/v13-post-rng-main-set-overlap-v1.json"


def _git(*args: str) -> bytes:
    return subprocess.check_output(
        ["git", "-C", str(ROOT), "-c", "core.hooksPath=/dev/null", *args]
    )


def _record() -> dict:
    raw = (ROOT / REG).read_bytes()
    value = json.loads(raw)
    assert (
        raw
        == (
            json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            + "\n"
        ).encode()
    )
    return value


def test_exception_preserves_original_science_and_runtime_authority():
    value = _record()
    original = (ROOT / R13).read_bytes()
    assert hashlib.sha256(original).hexdigest() == value["original_r13"]["sha256"]
    assert original == _git("show", f"{BASE}:{R13}")
    source = json.loads(original)
    assert (
        value["original_r13"]["scientific_contract_sha256"]
        == source["statistical_fingerprint_sha256"]
    )
    assert (
        value["original_r13"]["operational_contract_sha256"]
        == source["operational_contract_sha256"]
    )
    assert value["model_version"] == "v13.0.0"
    assert value["historical_execution_authority"] is False
    assert value["changes_v13_scientific_behavior"] is False
    assert value["retroactive_permission"] is False
    assert value["scope"]["first_registration_pr_ci_included"] is True
    assert value["scope"]["v13_tests"] == "synthetic_source_math_only"
    assert value["scope"]["allows_real_v13_prediction_or_scoring"] is False
    assert value["scope"]["allows_email_or_operational_network_mutation"] is False


def test_exception_freezes_existing_test_and_dependency_sources_by_metadata():
    value = _record()
    assert value["baseline_sha"] == BASE
    tree = {}
    for line in _git("ls-tree", "-r", "--full-tree", BASE).decode().splitlines():
        metadata, path = line.split("\t", 1)
        mode, kind, oid = metadata.split()
        if (
            path.startswith(("src/", "tools/", "tests/", "requirements/"))
            or path == "pyproject.toml"
        ):
            tree[path] = {"path": path, "mode": mode, "type": kind, "oid": oid}
    assert value["legacy_source_metadata"] == [tree[path] for path in sorted(tree)]
    # Inspect source objects only, never data/report/answer payloads.
    for entry in value["legacy_source_metadata"]:
        mode, kind, oid = (
            _git("ls-tree", "HEAD", "--", entry["path"])
            .decode()
            .split("\t", 1)[0]
            .split()
        )
        assert (mode, kind, oid) == (entry["mode"], entry["type"], entry["oid"]), entry[
            "path"
        ]


def test_exception_preserves_incident_and_registered_supporting_bytes():
    value = _record()
    for entry in value["registered_files"]:
        raw = (ROOT / entry["path"]).read_bytes()
        assert len(raw) == entry["bytes"], entry["path"]
        assert hashlib.sha256(raw).hexdigest() == entry["sha256"], entry["path"]
    incident = json.loads((ROOT / value["incident_record"]).read_bytes())
    assert incident["test_exit_code"] == 2
    assert incident["test_completed_cases"] == 230
    assert incident["test_result"] == "interrupted_not_complete_not_full_suite_pass"
    assert incident["permission_exception"] == "not_approved"
    assert incident["V13_prediction_or_scoring_performed"] is False
    assert value["permission"]["user_message"] == "OK，你有我的授权，你可以继续去做。"
    assert value["permission"]["receipt_observation_utc"] == "2026-09-13T15:26:08Z"


def test_log_guard_hides_fixture_payload_and_preserves_failure(tmp_path):
    (tmp_path / "conftest.py").write_bytes((ROOT / "tests/conftest.py").read_bytes())
    sentinel = "SYNTHETIC_PAYLOAD_MUST_NOT_APPEAR"
    (tmp_path / "test_fixture.py").write_text(
        "def test_pass():\n    assert True\n\n"
        "def test_fail():\n    print(" + repr(sentinel) + ")\n"
        "    import warnings\n    warnings.warn(" + repr(sentinel) + ")\n"
        "    assert False, " + repr(sentinel) + "\n"
    )
    result = subprocess.run(
        [sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider"],
        cwd=tmp_path,
        env={"PATH": os.defpath, "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "1 failed, 1 passed" in result.stdout
    assert "FAILED test_fixture.py::test_fail" in result.stdout
    assert sentinel not in result.stdout + result.stderr
