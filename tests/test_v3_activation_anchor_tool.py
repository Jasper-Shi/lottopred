from __future__ import annotations

from datetime import date, timedelta
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from types import ModuleType

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "prepare_v3_activation_anchor.py"
EXPERIMENT_ID = "V3_frozen_shadow_cohort"
COHORT_START = "2099-01-10"
HISTORY_DRAW_COUNT = 4001
REGISTRY_PATH = "docs/experiments/registry.yaml"
ACTIVATION_JSON_PATH = (
    "reports/prospective/"
    "V3_frozen_shadow_cohort__v3.0.0__activation.json"
)
ACTIVATION_MARKDOWN_PATH = (
    "reports/prospective/"
    "V3_frozen_shadow_cohort__v3.0.0__activation.md"
)
ACTIVATION_CLAIM_PATH = (
    "reports/prospective/"
    "V3_frozen_shadow_cohort__v3.0.0__activation.claim"
)
SENTINEL_PATHS = (
    REGISTRY_PATH,
    "config.yaml",
    "src/lotto649/live.py",
    "predictions/sentinel.json",
    "evaluations/sentinel.json",
)


def _git(repository: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _commit_at(repository: Path, message: str, committed_at: str) -> str:
    environment = os.environ.copy()
    environment["GIT_AUTHOR_DATE"] = committed_at
    environment["GIT_COMMITTER_DATE"] = committed_at
    completed = subprocess.run(
        ["git", "-C", str(repository), "commit", "-m", message],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )
    assert completed.stdout
    return _git(repository, "rev-parse", "HEAD")


def _commit(repository: Path, message: str) -> str:
    return _commit_at(
        repository,
        message,
        "2026-08-16T12:00:00-04:00",
    )


def _write(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)


def _synthetic_history_bytes() -> bytes:
    draw_dates = [date(2026, 8, 15)]
    while len(draw_dates) < HISTORY_DRAW_COUNT:
        previous = draw_dates[-1]
        days = 3 if previous.weekday() == 5 else 4
        draw_dates.append(previous - timedelta(days=days))
    lines = ["draw_date,n1,n2,n3,n4,n5,n6,bonus\n"]
    lines.extend(
        f"{draw_date.isoformat()},1,9,17,34,36,43,24\n"
        for draw_date in reversed(draw_dates)
    )
    return "".join(lines).encode("utf-8")


@pytest.fixture
def registered_repository(tmp_path: Path) -> tuple[Path, str, dict]:
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init")
    _git(repository, "config", "user.name", "Activation Tool Test")
    _git(repository, "config", "user.email", "activation@example.test")

    registry_payload = yaml.safe_load(
        (ROOT / "docs" / "experiments" / "registry.yaml").read_text(
            encoding="utf-8"
        )
    )
    registration = next(
        row
        for row in registry_payload["experiments"]
        if row["id"] == EXPERIMENT_ID
    )
    registration["parameters"]["newest_known_excluded_snapshot_target"] = (
        "2099-01-07"
    )
    for relative_path in registration["parameters"]["frozen_implementation_paths"]:
        _write(repository / relative_path, b"frozen\n")
    _write(repository / "config.yaml", b"config sentinel\n")
    _write(repository / "src" / "lotto649" / "live.py", b"live sentinel\n")
    _write(repository / "predictions" / "sentinel.json", b"prediction sentinel\n")
    _write(repository / "evaluations" / "sentinel.json", b"evaluation sentinel\n")

    draws_raw = _synthetic_history_bytes()
    _write(repository / "data" / "processed" / "draws.csv", draws_raw)
    _git(repository, "add", ".")
    data_commit = _commit(repository, "Add frozen inputs")

    boundary = {
        "source_commit": data_commit,
        "sha256": sha256(draws_raw).hexdigest(),
        "draw_count": HISTORY_DRAW_COUNT,
        "history_through": date(2026, 8, 15),
    }
    registration["registration_dataset"].update(boundary)
    registration["registration_dataset"]["path"] = (
        "data/processed/draws.csv"
    )
    registration["outcomes_known_at_registration"].update(boundary)
    registry_path = repository / "docs" / "experiments" / "registry.yaml"
    _write(
        registry_path,
        yaml.safe_dump(registry_payload, sort_keys=False).encode(),
    )
    _git(repository, "add", "docs/experiments/registry.yaml")
    freeze_commit = _commit(repository, "Register V3 prospective cohort")

    _write(repository / "after-freeze.txt", b"unrelated\n")
    _git(repository, "add", "after-freeze.txt")
    _commit(repository, "Add non-frozen follow-up")
    _git(
        repository,
        "update-ref",
        "refs/remotes/origin/main",
        _git(repository, "rev-parse", "HEAD"),
    )
    return repository, freeze_commit, registration


def _run_tool(
    repository: Path,
    freeze_commit: str,
    *extra_arguments: str,
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--repository",
            str(repository),
            "--experiment-id",
            EXPERIMENT_ID,
            "--freeze-commit",
            freeze_commit,
            "--cohort-start",
            COHORT_START,
            *extra_arguments,
        ],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )


def _activation_paths(registration: dict) -> tuple[str, str, str]:
    parameters = registration["parameters"]
    paths = (
        parameters["activation_anchor_json"],
        parameters["activation_anchor_markdown"],
        parameters["activation_anchor_claim"],
    )
    assert paths == (
        ACTIVATION_JSON_PATH,
        ACTIVATION_MARKDOWN_PATH,
        ACTIVATION_CLAIM_PATH,
    )
    return paths


@pytest.fixture
def producer_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "v3_activation_anchor_tool_under_test",
        SCRIPT,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _main_arguments(repository: Path, freeze_commit: str) -> list[str]:
    return [
        "--repository",
        str(repository),
        "--experiment-id",
        EXPERIMENT_ID,
        "--freeze-commit",
        freeze_commit,
        "--cohort-start",
        COHORT_START,
        "--write",
    ]


def test_cli_dry_run_reports_deterministic_artifacts_without_writing(
    registered_repository: tuple[Path, str, dict],
) -> None:
    repository, freeze_commit, registration = registered_repository

    first = _run_tool(repository, freeze_commit)
    second = _run_tool(repository, freeze_commit)

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    assert first.stdout == second.stdout
    summary = json.loads(first.stdout)
    assert summary["mode"] == "dry-run"
    assert summary["written"] is False
    assert summary["freeze_commit"] == freeze_commit
    assert summary["cohort_start"] == COHORT_START
    artifact_paths = {
        item["path"] for item in summary["artifacts"]
    }
    assert artifact_paths == {
        registration["parameters"]["activation_anchor_json"],
        registration["parameters"]["activation_anchor_markdown"],
        registration["parameters"]["activation_anchor_claim"],
    }
    assert all(len(item["sha256"]) == 64 for item in summary["artifacts"])
    assert all(not (repository / path).exists() for path in artifact_paths)


def test_cli_allows_head_equal_to_freeze_without_an_intermediate_commit(
    registered_repository: tuple[Path, str, dict],
) -> None:
    repository, freeze_commit, registration = registered_repository
    _git(repository, "switch", "--detach", freeze_commit)
    _git(
        repository,
        "update-ref",
        "refs/remotes/origin/main",
        freeze_commit,
    )

    completed = _run_tool(repository, freeze_commit)

    assert completed.returncode == 0, completed.stderr
    summary = json.loads(completed.stdout)
    assert summary["head_commit"] == freeze_commit
    assert summary["freeze_commit"] == freeze_commit
    assert summary["mode"] == "dry-run"
    assert all(
        not (repository / path).exists()
        for path in _activation_paths(registration)
    )


def test_cli_head_equal_freeze_rejects_symlinked_frozen_path(
    registered_repository: tuple[Path, str, dict],
) -> None:
    repository, _, registration = registered_repository
    frozen_path = registration["parameters"]["frozen_implementation_paths"][0]
    candidate = repository / frozen_path
    candidate.unlink()
    candidate.symlink_to("not-a-regular-frozen-file")
    registry_path = repository / REGISTRY_PATH
    registry_path.write_text(
        registry_path.read_text(encoding="utf-8") + "\n# symlink freeze audit\n",
        encoding="utf-8",
    )
    _git(repository, "add", frozen_path, REGISTRY_PATH)
    freeze_commit = _commit(repository, "Freeze an invalid symlink path")

    completed = _run_tool(repository, freeze_commit)

    assert completed.returncode == 2
    assert "regular file" in completed.stderr.lower()
    assert not (repository / "reports" / "prospective").exists()


def test_cli_rejects_unrelated_follow_up_commit_as_supplied_freeze(
    registered_repository: tuple[Path, str, dict],
) -> None:
    repository, _, _ = registered_repository
    unrelated_commit = _git(repository, "rev-parse", "HEAD")

    completed = _run_tool(repository, unrelated_commit)

    assert completed.returncode == 2
    assert "freeze commit" in completed.stderr.lower()
    assert REGISTRY_PATH in completed.stderr
    assert not (repository / "reports" / "prospective").exists()


def test_cli_write_publishes_only_three_schema_bound_artifacts(
    registered_repository: tuple[Path, str, dict],
) -> None:
    repository, freeze_commit, registration = registered_repository
    before = {
        path: (repository / path).read_bytes() for path in SENTINEL_PATHS
    }
    outcome_sha256 = registration["outcomes_known_at_registration"]["sha256"]
    expected_json = (
        "{\n"
        f'  "cohort_start": "{COHORT_START}",\n'
        '  "decision": "continue_shadow",\n'
        f'  "experiment_id": "{EXPERIMENT_ID}",\n'
        f'  "freeze_commit": "{freeze_commit}",\n'
        '  "model_name": "v3_boosting",\n'
        '  "model_version": "v3.0.0",\n'
        f'  "outcome_draw_count": {HISTORY_DRAW_COUNT},\n'
        '  "outcome_history_through": "2026-08-15",\n'
        '  "outcome_path": "data/processed/draws.csv",\n'
        f'  "outcome_sha256": "{outcome_sha256}",\n'
        '  "role": "shadow",\n'
        '  "schema_version": 1\n'
        "}\n"
    ).encode()
    expected_markdown = (
        "# V3 prospective activation anchor\n\n"
        "This anchor records only frozen identity and committed outcome-boundary "
        "evidence. It contains no performance result and does not activate live "
        "prediction.\n\n"
        f"- Experiment: `{EXPERIMENT_ID}`\n"
        "- Model: `v3_boosting v3.0.0`\n"
        f"- Freeze commit: `{freeze_commit}`\n"
        "- Outcome path: `data/processed/draws.csv`\n"
        f"- Outcome SHA-256: `{outcome_sha256}`\n"
        f"- Outcome draws: `{HISTORY_DRAW_COUNT}`\n"
        "- Outcomes through: `2026-08-15`\n"
        f"- Planned cohort start: `{COHORT_START}`\n"
        "- Decision: `continue_shadow`\n"
        "- Role: `shadow`\n"
    ).encode()
    expected_claim = (
        "{\n"
        '  "claim": "prepare_activation_anchor_without_performance_review",\n'
        f'  "cohort_start": "{COHORT_START}",\n'
        '  "decision": "continue_shadow",\n'
        f'  "experiment_id": "{EXPERIMENT_ID}",\n'
        f'  "freeze_commit": "{freeze_commit}",\n'
        '  "live_activation": false,\n'
        '  "model_name": "v3_boosting",\n'
        '  "model_version": "v3.0.0",\n'
        '  "role": "shadow",\n'
        '  "schema_version": 1\n'
        "}\n"
    ).encode()
    expected_artifacts = {
        ACTIVATION_JSON_PATH: expected_json,
        ACTIVATION_MARKDOWN_PATH: expected_markdown,
        ACTIVATION_CLAIM_PATH: expected_claim,
    }

    completed = _run_tool(repository, freeze_commit, "--write")

    assert completed.returncode == 0, completed.stderr
    summary = json.loads(completed.stdout)
    assert summary["mode"] == "write"
    assert summary["written"] is True
    paths = [item["path"] for item in summary["artifacts"]]
    assert set(paths) == set(expected_artifacts)
    for item in summary["artifacts"]:
        raw = (repository / item["path"]).read_bytes()
        assert raw == expected_artifacts[item["path"]]
        assert sha256(raw).hexdigest() == item["sha256"]
        assert len(raw) == item["bytes"]
    assert {
        path: (repository / path).read_bytes() for path in SENTINEL_PATHS
    } == before
    assert _git(repository, "diff", "--", REGISTRY_PATH) == ""
    changed_paths = {
        line[3:]
        for line in _git(
            repository,
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
        ).splitlines()
    }
    assert changed_paths == set(paths)


def test_cli_rejects_registration_drift_after_freeze(
    registered_repository: tuple[Path, str, dict],
) -> None:
    repository, freeze_commit, _ = registered_repository
    registry_path = repository / REGISTRY_PATH
    payload = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    registration = next(
        row
        for row in payload["experiments"]
        if row["id"] == EXPERIMENT_ID
    )
    registration["parameters"]["learning_rate"] = 0.061
    _write(registry_path, yaml.safe_dump(payload, sort_keys=False).encode())
    _git(repository, "add", REGISTRY_PATH)
    _commit(repository, "Drift the registered V3 behavior")

    completed = _run_tool(repository, freeze_commit)

    assert completed.returncode == 2
    assert "registration" in completed.stderr.lower()
    assert "freeze" in completed.stderr.lower()
    assert not (repository / "reports" / "prospective").exists()


@pytest.mark.parametrize("dirty_kind", ["untracked", "staged", "unstaged"])
def test_cli_rejects_dirty_repository_without_reading_or_writing_artifacts(
    registered_repository: tuple[Path, str, dict],
    dirty_kind: str,
) -> None:
    repository, freeze_commit, _ = registered_repository
    if dirty_kind == "unstaged":
        _write(repository / "after-freeze.txt", b"unstaged dirty\n")
    else:
        _write(repository / "uncommitted.txt", b"dirty\n")
        if dirty_kind == "staged":
            _git(repository, "add", "uncommitted.txt")

    completed = _run_tool(repository, freeze_commit)

    assert completed.returncode == 2
    assert "repository must be clean" in completed.stderr.lower()
    assert not (repository / "reports" / "prospective").exists()


def test_cli_requires_registered_not_activated_state(
    registered_repository: tuple[Path, str, dict],
) -> None:
    repository, freeze_commit, _ = registered_repository
    registry_path = repository / REGISTRY_PATH
    payload = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    registration = next(
        row
        for row in payload["experiments"]
        if row["id"] == EXPERIMENT_ID
    )
    registration["status"] = "historical_diagnostic_complete"
    _write(registry_path, yaml.safe_dump(payload, sort_keys=False).encode())
    _git(repository, "add", REGISTRY_PATH)
    _commit(repository, "Move experiment out of registered state")

    completed = _run_tool(repository, freeze_commit)

    assert completed.returncode == 2
    assert "must be registered" in completed.stderr.lower()
    assert "not_activated" in completed.stderr
    assert not (repository / "reports" / "prospective").exists()


@pytest.mark.parametrize(
    ("parameter", "value", "message"),
    [
        (
            "activation_anchor_commit_changes",
            "activation_and_other_files",
            "exactly three",
        ),
        ("activation_anchor_enables_live", True, "must not enable live"),
        (
            "activation_anchor_commit_deadline",
            "on_or_before_cohort_start",
            "anchor commit deadline",
        ),
        (
            "release_commit_deadline",
            "on_or_before_cohort_start",
            "release commit deadline",
        ),
    ],
)
def test_cli_rejects_invalid_frozen_anchor_protocol_markers(
    registered_repository: tuple[Path, str, dict],
    parameter: str,
    value: object,
    message: str,
) -> None:
    repository, _, _ = registered_repository
    registry_path = repository / REGISTRY_PATH
    payload = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    registration = next(
        row
        for row in payload["experiments"]
        if row["id"] == EXPERIMENT_ID
    )
    registration["parameters"][parameter] = value
    _write(registry_path, yaml.safe_dump(payload, sort_keys=False).encode())
    _git(repository, "add", REGISTRY_PATH)
    freeze_commit = _commit(repository, "Freeze an invalid anchor protocol")
    _git(
        repository,
        "update-ref",
        "refs/remotes/origin/main",
        freeze_commit,
    )

    completed = _run_tool(repository, freeze_commit)

    assert completed.returncode == 2
    assert message in completed.stderr.lower()
    assert not (repository / "reports" / "prospective").exists()


def test_cli_rejects_suspiciously_small_committed_history(
    registered_repository: tuple[Path, str, dict],
) -> None:
    repository, _, _ = registered_repository
    data_path = repository / "data" / "processed" / "draws.csv"
    small_raw = b"".join(data_path.read_bytes().splitlines(keepends=True)[:2])
    _write(data_path, small_raw)
    _git(repository, "add", "data/processed/draws.csv")
    data_commit = _commit(repository, "Commit a suspiciously small outcome history")

    registry_path = repository / REGISTRY_PATH
    payload = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    registration = next(
        row
        for row in payload["experiments"]
        if row["id"] == EXPERIMENT_ID
    )
    first_date = date.fromisoformat(small_raw.splitlines()[1].split(b",", 1)[0].decode())
    boundary = {
        "source_commit": data_commit,
        "sha256": sha256(small_raw).hexdigest(),
        "draw_count": 1,
        "history_through": first_date,
    }
    registration["registration_dataset"].update(boundary)
    registration["outcomes_known_at_registration"].update(boundary)
    _write(registry_path, yaml.safe_dump(payload, sort_keys=False).encode())
    _git(repository, "add", REGISTRY_PATH)
    freeze_commit = _commit(repository, "Freeze a suspiciously small history")
    _git(
        repository,
        "update-ref",
        "refs/remotes/origin/main",
        freeze_commit,
    )

    completed = _run_tool(repository, freeze_commit)

    assert completed.returncode == 2
    assert "expected more than 4,000 historical draws" in completed.stderr.lower()
    assert not (repository / "reports" / "prospective").exists()


def test_cli_accepts_only_append_only_committed_outcomes(
    registered_repository: tuple[Path, str, dict],
) -> None:
    repository, freeze_commit, registration = registered_repository
    draws_path = repository / "data" / "processed" / "draws.csv"
    appended_raw = draws_path.read_bytes() + (
        b"2026-08-19,2,10,18,35,37,44,25\n"
    )
    _write(draws_path, appended_raw)
    _git(repository, "add", "data/processed/draws.csv")
    appended_commit = _commit(repository, "Append a verified draw")
    _git(
        repository,
        "update-ref",
        "refs/remotes/origin/main",
        appended_commit,
    )

    completed = _run_tool(repository, freeze_commit, "--write")

    assert completed.returncode == 0, completed.stderr
    anchor = json.loads(
        (repository / _activation_paths(registration)[0]).read_text(
            encoding="utf-8"
        )
    )
    assert anchor["outcome_sha256"] == sha256(appended_raw).hexdigest()
    assert anchor["outcome_draw_count"] == HISTORY_DRAW_COUNT + 1
    assert anchor["outcome_history_through"] == "2026-08-19"


def test_cli_rejects_suspicious_append_only_outcome_gap(
    registered_repository: tuple[Path, str, dict],
) -> None:
    repository, freeze_commit, _ = registered_repository
    draws_path = repository / "data" / "processed" / "draws.csv"
    _write(
        draws_path,
        draws_path.read_bytes() + b"2026-09-05,2,10,18,35,37,44,25\n",
    )
    _git(repository, "add", "data/processed/draws.csv")
    gap_commit = _commit(repository, "Append an outcome after a suspicious gap")
    _git(
        repository,
        "update-ref",
        "refs/remotes/origin/main",
        gap_commit,
    )

    completed = _run_tool(repository, freeze_commit)

    assert completed.returncode == 2
    assert "suspicious historical gap" in completed.stderr.lower()
    assert not (repository / "reports" / "prospective").exists()


def test_cli_rejects_missing_origin_main_tracking_ref(
    registered_repository: tuple[Path, str, dict],
) -> None:
    repository, freeze_commit, _ = registered_repository
    _git(repository, "update-ref", "-d", "refs/remotes/origin/main")

    completed = _run_tool(repository, freeze_commit)

    assert completed.returncode == 2
    assert "refs/remotes/origin/main" in completed.stderr
    assert not (repository / "reports" / "prospective").exists()


def test_cli_rejects_origin_main_sibling_of_head(
    registered_repository: tuple[Path, str, dict],
) -> None:
    repository, freeze_commit, _ = registered_repository
    original_head = _git(repository, "rev-parse", "HEAD")
    _git(repository, "switch", "--detach", freeze_commit)
    _write(repository / "remote-sibling.txt", b"remote sibling\n")
    _git(repository, "add", "remote-sibling.txt")
    remote_sibling = _commit(repository, "Create a sibling remote main")
    _git(repository, "switch", "--detach", original_head)
    _git(
        repository,
        "update-ref",
        "refs/remotes/origin/main",
        remote_sibling,
    )

    completed = _run_tool(repository, freeze_commit)

    assert completed.returncode == 2
    assert "origin/main" in completed.stderr.lower()
    assert "exactly equal" in completed.stderr.lower()
    assert not (repository / "reports" / "prospective").exists()


def test_cli_rejects_feature_commit_after_origin_main(
    registered_repository: tuple[Path, str, dict],
) -> None:
    repository, freeze_commit, _ = registered_repository
    _write(repository / "feature-only.txt", b"feature commit\n")
    _git(repository, "add", "feature-only.txt")
    _commit(repository, "Add feature commit after origin main")

    completed = _run_tool(repository, freeze_commit)

    assert completed.returncode == 2
    assert "head must exactly equal" in completed.stderr.lower()
    assert "refs/remotes/origin/main" in completed.stderr
    assert not (repository / "reports" / "prospective").exists()


def test_cli_rejects_head_rewrite_of_latest_origin_main_outcome(
    registered_repository: tuple[Path, str, dict],
) -> None:
    repository, freeze_commit, _ = registered_repository
    draws_path = repository / "data" / "processed" / "draws.csv"
    main_raw = draws_path.read_bytes() + (
        b"2026-08-19,2,10,18,35,37,44,25\n"
    )
    _write(draws_path, main_raw)
    _git(repository, "add", "data/processed/draws.csv")
    latest_main = _commit(repository, "Append latest origin main outcome")
    _git(
        repository,
        "update-ref",
        "refs/remotes/origin/main",
        latest_main,
    )

    rewritten = (
        b"draw_date,n1,n2,n3,n4,n5,n6,bonus\n"
        b"2026-08-15,1,9,17,34,36,43,24\n"
        b"2026-08-19,3,11,19,35,38,45,26\n"
    )
    _write(draws_path, rewritten)
    _git(repository, "add", "data/processed/draws.csv")
    _commit(repository, "Rewrite latest origin main outcome")

    completed = _run_tool(repository, freeze_commit)

    assert completed.returncode == 2
    assert "origin/main" in completed.stderr.lower()
    assert "exactly equal" in completed.stderr.lower()
    assert not (repository / "reports" / "prospective").exists()


def test_cli_rejects_rewritten_registered_outcome_prefix(
    registered_repository: tuple[Path, str, dict],
) -> None:
    repository, freeze_commit, _ = registered_repository
    draws_path = repository / "data" / "processed" / "draws.csv"
    rows = draws_path.read_bytes().splitlines(keepends=True)
    first_date = rows[1].split(b",", 1)[0]
    rows[1] = first_date + b",2,10,18,35,37,44,25\n"
    _write(draws_path, b"".join(rows))
    _git(repository, "add", "data/processed/draws.csv")
    rewritten_commit = _commit(repository, "Rewrite a known outcome")
    _git(
        repository,
        "update-ref",
        "refs/remotes/origin/main",
        rewritten_commit,
    )

    completed = _run_tool(repository, freeze_commit)

    assert completed.returncode == 2
    assert "preserve" in completed.stderr.lower()
    assert not (repository / "reports" / "prospective").exists()


def test_cli_rejects_frozen_implementation_drift(
    registered_repository: tuple[Path, str, dict],
) -> None:
    repository, freeze_commit, registration = registered_repository
    frozen_path = registration["parameters"]["frozen_implementation_paths"][0]
    _write(repository / frozen_path, b"drifted\n")
    _git(repository, "add", frozen_path)
    _commit(repository, "Drift frozen runtime code")

    completed = _run_tool(repository, freeze_commit)

    assert completed.returncode == 2
    assert "frozen" in completed.stderr.lower()
    assert not (repository / "reports" / "prospective").exists()


def test_cli_rejects_freeze_commit_not_reachable_from_head(
    registered_repository: tuple[Path, str, dict],
) -> None:
    repository, registered_freeze, _ = registered_repository
    original_head = _git(repository, "rev-parse", "HEAD")
    _git(repository, "switch", "--detach", registered_freeze)
    _write(repository / "sibling.txt", b"sibling\n")
    registry_path = repository / REGISTRY_PATH
    registry_path.write_text(
        registry_path.read_text(encoding="utf-8") + "\n# sibling freeze\n",
        encoding="utf-8",
    )
    _git(repository, "add", "sibling.txt", REGISTRY_PATH)
    sibling_freeze = _commit(repository, "Create an unreachable sibling freeze")
    _git(repository, "switch", "--detach", original_head)

    completed = _run_tool(repository, sibling_freeze)

    assert completed.returncode == 2
    assert "not an ancestor" in completed.stderr.lower()
    assert not (repository / "reports" / "prospective").exists()


@pytest.mark.parametrize(
    ("cohort_start", "message"),
    [
        ("2099-01-06", "wednesday or saturday"),
        ("2026-08-15", "future"),
        ("2099-01-07", "excluded snapshot"),
    ],
)
def test_cli_rejects_invalid_prospective_start(
    registered_repository: tuple[Path, str, dict],
    cohort_start: str,
    message: str,
) -> None:
    repository, freeze_commit, _ = registered_repository

    completed = _run_tool(
        repository,
        freeze_commit,
        "--cohort-start",
        cohort_start,
    )

    assert completed.returncode == 2
    assert message in completed.stderr.lower()
    assert not (repository / "reports" / "prospective").exists()


def test_cli_write_never_overwrites_an_ignored_existing_artifact(
    registered_repository: tuple[Path, str, dict],
) -> None:
    repository, freeze_commit, registration = registered_repository
    json_path, markdown_path, claim_path = _activation_paths(registration)
    exclude_path = repository / ".git" / "info" / "exclude"
    exclude_path.write_text(
        exclude_path.read_text(encoding="utf-8") + f"\n/{claim_path}\n",
        encoding="utf-8",
    )
    sentinel = b"do not overwrite\n"
    _write(repository / claim_path, sentinel)
    assert _git(repository, "status", "--porcelain=v1", "--untracked-files=all") == ""

    completed = _run_tool(repository, freeze_commit, "--write")

    assert completed.returncode == 2
    assert "already exists" in completed.stderr.lower()
    assert (repository / claim_path).read_bytes() == sentinel
    assert not (repository / json_path).exists()
    assert not (repository / markdown_path).exists()


def test_cli_write_rejects_ignored_artifact_path_even_when_absent(
    registered_repository: tuple[Path, str, dict],
) -> None:
    repository, freeze_commit, registration = registered_repository
    paths = _activation_paths(registration)
    exclude_path = repository / ".git" / "info" / "exclude"
    exclude_path.write_text(
        exclude_path.read_text(encoding="utf-8")
        + f"\n/{ACTIVATION_CLAIM_PATH}\n",
        encoding="utf-8",
    )
    assert all(not (repository / path).exists() for path in paths)
    assert _git(repository, "status", "--porcelain=v1", "--untracked-files=all") == ""

    completed = _run_tool(repository, freeze_commit, "--write")

    assert completed.returncode == 2
    assert "ignored" in completed.stderr.lower()
    assert ACTIVATION_CLAIM_PATH in completed.stderr
    assert all(not (repository / path).exists() for path in paths)


def test_cli_write_rejects_symlinked_registered_parent(
    registered_repository: tuple[Path, str, dict],
    tmp_path: Path,
) -> None:
    repository, freeze_commit, _ = registered_repository
    outside = tmp_path / "outside"
    outside.mkdir()
    exclude_path = repository / ".git" / "info" / "exclude"
    exclude_path.write_text(
        exclude_path.read_text(encoding="utf-8") + "\n/reports\n",
        encoding="utf-8",
    )
    (repository / "reports").symlink_to(outside, target_is_directory=True)
    assert _git(repository, "status", "--porcelain=v1", "--untracked-files=all") == ""

    completed = _run_tool(repository, freeze_commit, "--write")

    assert completed.returncode == 2
    assert "symlink" in completed.stderr.lower()
    assert list(outside.iterdir()) == []


def test_main_rejects_parent_symlink_swap_without_writing_outside_repository(
    registered_repository: tuple[Path, str, dict],
    producer_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    capfd: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    repository, freeze_commit, _ = registered_repository
    outside = tmp_path / "swap-outside"
    outside.mkdir()

    class SwappingOperations(producer_module.PublisherOperations):
        swapped = False

        def link(
            self,
            source_name: str,
            destination_name: str,
            *,
            source_directory_fd: int,
            destination_directory_fd: int,
            artifact_path: str,
        ) -> None:
            if not self.swapped:
                registered_parent = repository / "reports" / "prospective"
                held_parent = repository / "reports" / "held-prospective"
                registered_parent.rename(held_parent)
                registered_parent.symlink_to(outside, target_is_directory=True)
                self.swapped = True
            super().link(
                source_name,
                destination_name,
                source_directory_fd=source_directory_fd,
                destination_directory_fd=destination_directory_fd,
                artifact_path=artifact_path,
            )

    operations = SwappingOperations()
    monkeypatch.setattr(
        producer_module,
        "_new_publisher_operations",
        lambda: operations,
    )

    result = producer_module.main(_main_arguments(repository, freeze_commit))

    captured = capfd.readouterr()
    assert result == 2
    assert "registered parent" in captured.err.lower()
    assert "changed" in captured.err.lower()
    assert list(outside.iterdir()) == []
    held = repository / "reports" / "held-prospective"
    assert all(not (held / Path(path).name).exists() for path in _activation_paths(_))


def test_main_rolls_back_all_links_on_precommit_publication_failure(
    registered_repository: tuple[Path, str, dict],
    producer_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    capfd: pytest.CaptureFixture[str],
) -> None:
    repository, freeze_commit, registration = registered_repository

    class SecondLinkFails(producer_module.PublisherOperations):
        link_count = 0

        def link(self, *args, **kwargs) -> None:
            self.link_count += 1
            if self.link_count == 2:
                raise OSError("synthetic second-link failure")
            super().link(*args, **kwargs)

    monkeypatch.setattr(
        producer_module,
        "_new_publisher_operations",
        SecondLinkFails,
    )

    result = producer_module.main(_main_arguments(repository, freeze_commit))

    captured = capfd.readouterr()
    assert result == 2
    assert "before durable commit point" in captured.err.lower()
    assert "rollback completed" in captured.err.lower()
    assert all(
        not (repository / path).exists()
        for path in _activation_paths(registration)
    )
    assert list(repository.glob(".v3-activation-anchor-stage-*")) == []


def test_main_reports_rollback_failure_and_retains_partial_evidence(
    registered_repository: tuple[Path, str, dict],
    producer_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    capfd: pytest.CaptureFixture[str],
) -> None:
    repository, freeze_commit, registration = registered_repository

    class LinkAndRollbackFail(producer_module.PublisherOperations):
        link_count = 0

        def link(self, *args, **kwargs) -> None:
            self.link_count += 1
            if self.link_count == 2:
                raise OSError("synthetic link failure")
            super().link(*args, **kwargs)

        def unlink(self, name: str, *, directory_fd: int, purpose: str) -> None:
            if purpose == "rollback":
                raise OSError("synthetic rollback failure")
            super().unlink(name, directory_fd=directory_fd, purpose=purpose)

    monkeypatch.setattr(
        producer_module,
        "_new_publisher_operations",
        LinkAndRollbackFail,
    )

    result = producer_module.main(_main_arguments(repository, freeze_commit))

    captured = capfd.readouterr()
    assert result == 2
    assert "rollback failed" in captured.err.lower()
    assert "evidence retained" in captured.err.lower()
    assert any(
        (repository / path).exists()
        for path in _activation_paths(registration)
    )
    assert list(repository.glob(".v3-activation-anchor-stage-*"))


def test_main_treats_final_parent_fsync_failure_as_precommit_and_rolls_back(
    registered_repository: tuple[Path, str, dict],
    producer_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    capfd: pytest.CaptureFixture[str],
) -> None:
    repository, freeze_commit, registration = registered_repository

    class FinalParentFsyncFails(producer_module.PublisherOperations):
        def fsync(self, descriptor: int, *, purpose: str) -> None:
            if purpose == "final_parent":
                raise OSError("synthetic final-parent fsync failure")
            super().fsync(descriptor, purpose=purpose)

    monkeypatch.setattr(
        producer_module,
        "_new_publisher_operations",
        FinalParentFsyncFails,
    )

    result = producer_module.main(_main_arguments(repository, freeze_commit))

    captured = capfd.readouterr()
    assert result == 2
    assert "before durable commit point" in captured.err.lower()
    assert "rollback completed" in captured.err.lower()
    assert all(
        not (repository / path).exists()
        for path in _activation_paths(registration)
    )


def test_main_rolls_back_then_reraises_keyboard_interrupt_from_second_link(
    registered_repository: tuple[Path, str, dict],
    producer_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, freeze_commit, registration = registered_repository

    class SecondLinkInterrupted(producer_module.PublisherOperations):
        link_count = 0

        def link(self, *args, **kwargs) -> None:
            self.link_count += 1
            if self.link_count == 2:
                raise KeyboardInterrupt("synthetic publication interrupt")
            super().link(*args, **kwargs)

    monkeypatch.setattr(
        producer_module,
        "_new_publisher_operations",
        SecondLinkInterrupted,
    )

    with pytest.raises(KeyboardInterrupt, match="synthetic publication interrupt"):
        producer_module.main(_main_arguments(repository, freeze_commit))

    assert all(
        not (repository / path).exists()
        for path in _activation_paths(registration)
    )
    assert list(repository.glob(".v3-activation-anchor-stage-*")) == []


@pytest.mark.parametrize("mutation", ["head", "registry", "data"])
def test_main_precommit_validator_rejects_git_state_toctou(
    registered_repository: tuple[Path, str, dict],
    producer_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    capfd: pytest.CaptureFixture[str],
    mutation: str,
) -> None:
    repository, freeze_commit, registration = registered_repository

    class MutatingOperations(producer_module.PublisherOperations):
        mutated = False

        def fsync(self, descriptor: int, *, purpose: str) -> None:
            super().fsync(descriptor, purpose=purpose)
            if mutation == "head" and purpose == "stage_directory" and not self.mutated:
                _write(repository / "head-race.txt", b"head changed\n")
                _git(repository, "add", "head-race.txt")
                _commit(repository, "Move HEAD during anchor publication")
                self.mutated = True

        def link(self, *args, **kwargs) -> None:
            super().link(*args, **kwargs)
            if self.mutated or mutation == "head":
                return
            target = (
                repository / REGISTRY_PATH
                if mutation == "registry"
                else repository / "data" / "processed" / "draws.csv"
            )
            target.write_bytes(target.read_bytes() + b"# synthetic race\n")
            self.mutated = True

    monkeypatch.setattr(
        producer_module,
        "_new_publisher_operations",
        MutatingOperations,
    )

    result = producer_module.main(_main_arguments(repository, freeze_commit))

    captured = capfd.readouterr()
    assert result == 2
    assert "precommit git state changed" in captured.err.lower()
    assert all(
        not (repository / path).exists()
        for path in _activation_paths(registration)
    )
    assert list(repository.glob(".v3-activation-anchor-stage-*")) == []


@pytest.mark.parametrize("mutation", ["data", "parent"])
def test_main_revalidates_after_final_parent_fsync_before_commit_point(
    registered_repository: tuple[Path, str, dict],
    producer_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    capfd: pytest.CaptureFixture[str],
    tmp_path: Path,
    mutation: str,
) -> None:
    repository, freeze_commit, registration = registered_repository
    outside = tmp_path / "post-fsync-outside"
    outside.mkdir()

    class PostFsyncMutation(producer_module.PublisherOperations):
        mutated = False

        def fsync(self, descriptor: int, *, purpose: str) -> None:
            super().fsync(descriptor, purpose=purpose)
            if purpose != "final_parent" or self.mutated:
                return
            if mutation == "data":
                data_path = repository / "data" / "processed" / "draws.csv"
                data_path.write_bytes(data_path.read_bytes() + b"# post-fsync race\n")
            else:
                registered_parent = repository / "reports" / "prospective"
                held_parent = repository / "reports" / "post-fsync-held"
                registered_parent.rename(held_parent)
                registered_parent.symlink_to(outside, target_is_directory=True)
            self.mutated = True

    monkeypatch.setattr(
        producer_module,
        "_new_publisher_operations",
        PostFsyncMutation,
    )

    result = producer_module.main(_main_arguments(repository, freeze_commit))

    captured = capfd.readouterr()
    assert result == 2
    expected = (
        "precommit git state changed"
        if mutation == "data"
        else "registered parent changed"
    )
    assert expected in captured.err.lower()
    assert list(outside.iterdir()) == []
    held = repository / "reports" / "post-fsync-held"
    assert all(
        not (held / Path(path).name).exists()
        for path in _activation_paths(registration)
    )


def test_main_rejects_final_deleted_immediately_after_last_link(
    registered_repository: tuple[Path, str, dict],
    producer_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    capfd: pytest.CaptureFixture[str],
) -> None:
    repository, freeze_commit, registration = registered_repository

    class LastLinkFinalDeleted(producer_module.PublisherOperations):
        link_count = 0

        def link(self, *args, **kwargs) -> None:
            super().link(*args, **kwargs)
            self.link_count += 1
            if self.link_count == 3:
                (repository / kwargs["artifact_path"]).unlink()

    monkeypatch.setattr(
        producer_module,
        "_new_publisher_operations",
        LastLinkFinalDeleted,
    )

    result = producer_module.main(_main_arguments(repository, freeze_commit))

    captured = capfd.readouterr()
    assert result == 2
    assert "precommit git state changed" in captured.err.lower()
    assert "expected worktree paths missing" in captured.err.lower()
    assert all(
        not (repository / path).exists()
        for path in _activation_paths(registration)
    )
    assert list(repository.glob(".v3-activation-anchor-stage-*")) == []


@pytest.mark.parametrize("fault", ["stage_cleanup", "root_cleanup_fsync"])
def test_main_warns_but_succeeds_for_postcommit_cleanup_failure(
    registered_repository: tuple[Path, str, dict],
    producer_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    capfd: pytest.CaptureFixture[str],
    fault: str,
) -> None:
    repository, freeze_commit, registration = registered_repository

    class PostCommitCleanupFails(producer_module.PublisherOperations):
        def unlink(self, name: str, *, directory_fd: int, purpose: str) -> None:
            if fault == "stage_cleanup" and purpose == "stage_cleanup":
                raise OSError("synthetic stage cleanup failure")
            super().unlink(name, directory_fd=directory_fd, purpose=purpose)

        def fsync(self, descriptor: int, *, purpose: str) -> None:
            if fault == "root_cleanup_fsync" and purpose == "root_cleanup":
                raise OSError("synthetic root cleanup fsync failure")
            super().fsync(descriptor, purpose=purpose)

    monkeypatch.setattr(
        producer_module,
        "_new_publisher_operations",
        PostCommitCleanupFails,
    )

    with pytest.warns(RuntimeWarning, match="durably published.*cleanup failed"):
        result = producer_module.main(_main_arguments(repository, freeze_commit))

    captured = capfd.readouterr()
    assert result == 0, captured.err
    assert json.loads(captured.out)["written"] is True
    assert all(
        (repository / path).is_file()
        for path in _activation_paths(registration)
    )


def test_cli_rejects_artifact_path_that_was_added_then_deleted(
    registered_repository: tuple[Path, str, dict],
) -> None:
    repository, freeze_commit, registration = registered_repository
    paths = _activation_paths(registration)
    for path in paths:
        _write(repository / path, f"historical {path}\n".encode())
    _git(repository, "add", *paths)
    _commit(repository, "Add historical activation artifacts")
    for path in paths:
        (repository / path).unlink()
    _git(repository, "add", *paths)
    deleted_commit = _commit(repository, "Delete historical activation artifacts")
    _git(
        repository,
        "update-ref",
        "refs/remotes/origin/main",
        deleted_commit,
    )

    completed = _run_tool(repository, freeze_commit)

    assert completed.returncode == 2
    assert "git history" in completed.stderr.lower()
    assert paths[0] in completed.stderr
    assert all(not (repository / path).exists() for path in paths)


def test_cli_rejects_start_not_after_head_commit_date(
    registered_repository: tuple[Path, str, dict],
) -> None:
    repository, freeze_commit, _ = registered_repository
    _write(repository / "future-commit.txt", b"future dated\n")
    _git(repository, "add", "future-commit.txt")
    future_commit = _commit_at(
        repository,
        "Add a future-dated commit",
        "2099-01-10T00:01:00-05:00",
    )
    _git(
        repository,
        "update-ref",
        "refs/remotes/origin/main",
        future_commit,
    )

    completed = _run_tool(repository, freeze_commit)

    assert completed.returncode == 2
    assert "head commit" in completed.stderr.lower()
    assert "cohort start" in completed.stderr.lower()
    assert not (repository / "reports" / "prospective").exists()


def test_cli_rejects_shallow_repository(
    registered_repository: tuple[Path, str, dict],
    tmp_path: Path,
) -> None:
    repository, freeze_commit, _ = registered_repository
    shallow = tmp_path / "shallow"
    subprocess.run(
        [
            "git",
            "clone",
            "--quiet",
            "--depth=1",
            repository.as_uri(),
            str(shallow),
        ],
        check=True,
    )

    completed = _run_tool(shallow, freeze_commit)

    assert completed.returncode == 2
    assert "non-shallow" in completed.stderr.lower()
    assert not (shallow / "reports" / "prospective").exists()
