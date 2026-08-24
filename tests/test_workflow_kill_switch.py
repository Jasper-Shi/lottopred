from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
DISABLED_CONFIG_SHA256 = (
    "ad3237bc57c85013e85dad16d1b6f04f43b50991d666a4b1528bf5b8614a76b6"
)
STAGE1_CONFIG_SHA256 = (
    "d53a9a9eed5ab434b021472135d6aed65c2c052339e0dfb88f8c00d46c0d8931"
)
FALSE_OUTPUTS = {
    "live.yml": {"refresh": "false", "live": "false", "cycle": "false"},
    "integration.yml": {
        "refresh": "false",
        "backtest": "false",
        "live": "false",
        "cycle": "false",
    },
    "backtest.yml": {"refresh": "false", "backtest": "false"},
}
VERIFIED_HISTORY_WORKFLOWS = [
    *FALSE_OUTPUTS,
    "research-v2-fast.yml",
    "research-v2-v4.yml",
    "test.yml",
]
_MATCH_CHECKOUT = object()
OLD_REVIEWED_SHA = "4f778662697dab353d4dee98d517c45dd29cd2a5"


def _workflow(workflow_name: str) -> dict:
    payload = yaml.safe_load(
        (ROOT / ".github" / "workflows" / workflow_name).read_text(encoding="utf-8")
    )
    assert len(payload["jobs"]) == 1
    return payload


def _steps(workflow_name: str) -> list[dict]:
    return next(iter(_workflow(workflow_name)["jobs"].values()))["steps"]


def _disabled_config_bytes() -> bytes:
    candidate = (ROOT / "config.yaml").read_bytes()
    disabled = candidate.replace(b"refresh_enabled: true", b"refresh_enabled: false")
    disabled = disabled.replace(
        b"live:\n  # Data-integrity incident kill switch. Missing/non-true remains disabled.\n  enabled: true",
        b"live:\n  # Data-integrity incident kill switch. Missing/non-true remains disabled.\n  enabled: false",
    )
    assert hashlib.sha256(disabled).hexdigest() == DISABLED_CONFIG_SHA256
    return disabled


def _initialize_git_checkout(repository: Path, config_bytes: bytes) -> str:
    (repository / "config.yaml").write_bytes(config_bytes)
    subprocess.run(
        ["git", "init", "--quiet", "--initial-branch=main", str(repository)],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(repository), "add", "config.yaml"],
        check=True,
        capture_output=True,
    )
    environment = {
        **os.environ,
        "GIT_AUTHOR_EMAIL": "test@example.invalid",
        "GIT_AUTHOR_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "test@example.invalid",
        "GIT_COMMITTER_NAME": "Test",
    }
    subprocess.run(
        ["git", "-C", str(repository), "commit", "--quiet", "-m", "fixture"],
        check=True,
        capture_output=True,
        env=environment,
    )
    return subprocess.run(
        ["git", "-C", str(repository), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _run_guard(
    tmp_path: Path,
    workflow_name: str,
    *,
    config_bytes: bytes | None,
    github_env: dict[str, str] | None = None,
    frozen_now: str | None = None,
    expected_sha: str | None | object = _MATCH_CHECKOUT,
) -> tuple[subprocess.CompletedProcess[str], dict[str, str], list[str]]:
    if config_bytes is not None:
        head = _initialize_git_checkout(tmp_path, config_bytes)
    else:
        head = "0" * 40
    output_path = tmp_path / "github-output.txt"
    script = _steps(workflow_name)[1]["run"]
    if frozen_now is not None:
        assert "datetime.now(UTC)" in script
        script = script.replace("datetime.now(UTC)", frozen_now)
    environment = {
        key: value for key, value in os.environ.items() if not key.startswith("GITHUB_")
    }
    environment.update(
        {
            "GITHUB_OUTPUT": str(output_path),
            "GITHUB_REPOSITORY": "Jasper-Shi/lottopred",
            "GITHUB_EVENT_NAME": "workflow_dispatch",
            "GITHUB_REF": "refs/heads/main",
            "GITHUB_SHA": head,
        }
    )
    if expected_sha is _MATCH_CHECKOUT:
        environment["STAGE1_EXPECTED_SHA"] = head
    elif expected_sha is not None:
        environment["STAGE1_EXPECTED_SHA"] = expected_sha
    if github_env:
        environment.update(github_env)
    completed = subprocess.run(
        ["bash", "-c", script],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    output_lines = output_path.read_text(encoding="utf-8").splitlines()
    observed = dict(line.split("=", 1) for line in output_lines)
    return completed, observed, output_lines


def test_committed_stage1_config_changes_only_the_two_live_gates():
    from lotto649.config import load_config

    config_bytes = (ROOT / "config.yaml").read_bytes()
    cfg = load_config(ROOT / "config.yaml")

    assert hashlib.sha256(config_bytes).hexdigest() == STAGE1_CONFIG_SHA256
    assert cfg["data"]["refresh_enabled"] is True
    assert cfg["live"]["enabled"] is True
    assert cfg["backtest"]["enabled"] is False
    assert (
        _disabled_config_bytes()
        .replace(b"refresh_enabled: false", b"refresh_enabled: true", 1)
        .replace(
            b"live:\n  # Data-integrity incident kill switch. Missing/non-true remains disabled.\n  enabled: false",
            b"live:\n  # Data-integrity incident kill switch. Missing/non-true remains disabled.\n  enabled: true",
        )
        == config_bytes
    )


@pytest.mark.parametrize("workflow_name", VERIFIED_HISTORY_WORKFLOWS)
def test_verified_history_consumers_checkout_full_git_history(workflow_name):
    checkout = _steps(workflow_name)[0]

    assert checkout["uses"] == "actions/checkout@v4"
    assert checkout["with"]["fetch-depth"] == 0
    if workflow_name in FALSE_OUTPUTS:
        assert checkout["with"]["persist-credentials"] is False


@pytest.mark.parametrize("workflow_name", FALSE_OUTPUTS)
def test_stage1_workflows_have_read_only_repository_permission(workflow_name):
    assert _workflow(workflow_name)["permissions"] == {"contents": "read"}


def test_live_stage1_requires_operator_supplied_expected_sha():
    dispatch = _workflow("live.yml")[True]

    assert set(dispatch) == {"workflow_dispatch"}
    expected_sha = dispatch["workflow_dispatch"]["inputs"]["expected_sha"]
    assert expected_sha["required"] is True
    assert expected_sha["type"] == "string"
    assert "default" not in expected_sha
    assert _steps("live.yml")[1]["env"] == {
        "STAGE1_EXPECTED_SHA": "${{ inputs.expected_sha }}"
    }


def test_integration_runs_when_operational_history_boundaries_change():
    changed_paths = set(_workflow("integration.yml")[True]["pull_request"]["paths"])

    assert {
        "data/processed/epochs/**",
        "evidence/data_integrity/**",
        "evidence/live_sources/**",
        "src/lotto649/backtest.py",
        "src/lotto649/data_integrity.py",
        "src/lotto649/official_history.py",
        "src/lotto649/operational_history.py",
        "src/lotto649/verified_history.py",
    } <= changed_paths


@pytest.mark.parametrize("workflow_name", FALSE_OUTPUTS)
def test_execution_guard_precedes_and_conditions_every_runtime_step(workflow_name):
    steps = _steps(workflow_name)
    guard = steps[1]

    assert steps[0]["uses"] == "actions/checkout@v4"
    assert guard["id"] == "execution_guard"
    assert guard["name"] == "Read Stage-1 execution guards"
    assert "config.yaml" in guard["run"]
    assert "hashlib.sha256" in guard["run"]
    assert DISABLED_CONFIG_SHA256 in guard["run"]
    assert STAGE1_CONFIG_SHA256 in guard["run"]
    assert "read_text" not in guard["run"]
    assert "pip install" not in guard["run"]
    assert "setup-python" not in guard["run"]
    assert all(
        "steps.execution_guard.outputs." in step.get("if", "")
        and "== 'true'" in step["if"]
        for step in steps[2:]
    )


@pytest.mark.parametrize("workflow_name", FALSE_OUTPUTS)
def test_disabled_config_is_recognized_and_remains_fully_sealed(
    tmp_path,
    workflow_name,
):
    completed, observed, output_lines = _run_guard(
        tmp_path,
        workflow_name,
        config_bytes=_disabled_config_bytes(),
        expected_sha=None,
    )

    assert completed.returncode == 0, completed.stderr
    assert "Verified incident-disabled config" in completed.stdout
    assert observed == FALSE_OUTPUTS[workflow_name]
    assert output_lines == [f"{name}=false" for name in FALSE_OUTPUTS[workflow_name]]


@pytest.mark.parametrize("workflow_name", ["integration.yml", "backtest.yml"])
def test_non_live_workflows_recognize_stage1_config_but_remain_fully_sealed(
    tmp_path,
    workflow_name,
):
    completed, observed, _output_lines = _run_guard(
        tmp_path,
        workflow_name,
        config_bytes=(ROOT / "config.yaml").read_bytes(),
    )

    assert completed.returncode == 0, completed.stderr
    assert (
        "Verified Stage-1 live config; this workflow remains sealed" in completed.stdout
    )
    assert observed == FALSE_OUTPUTS[workflow_name]


def test_live_guard_allows_exact_stage1_manual_main_dispatch_after_not_before(
    tmp_path,
):
    completed, observed, output_lines = _run_guard(
        tmp_path,
        "live.yml",
        config_bytes=(ROOT / "config.yaml").read_bytes(),
        frozen_now="datetime(2026, 8, 27, 15, 15, tzinfo=UTC)",
        expected_sha=_MATCH_CHECKOUT,
    )

    assert completed.returncode == 0, completed.stderr
    assert "Authorized exact Stage-1 production canary" in completed.stdout
    assert observed == {"refresh": "true", "live": "true", "cycle": "true"}
    assert output_lines[:3] == ["refresh=false", "live=false", "cycle=false"]


def test_live_guard_rejects_missing_expected_sha_after_writing_false_outputs(
    tmp_path,
):
    completed, observed, output_lines = _run_guard(
        tmp_path,
        "live.yml",
        config_bytes=(ROOT / "config.yaml").read_bytes(),
        frozen_now="datetime(2026, 8, 27, 15, 15, tzinfo=UTC)",
        expected_sha=None,
    )

    assert completed.returncode != 0
    assert observed == FALSE_OUTPUTS["live.yml"]
    assert output_lines == ["refresh=false", "live=false", "cycle=false"]


def test_old_reviewed_sha_cannot_authorize_an_arbitrary_future_commit(tmp_path):
    assert OLD_REVIEWED_SHA not in _steps("live.yml")[1]["run"]
    completed, observed, output_lines = _run_guard(
        tmp_path,
        "live.yml",
        config_bytes=(ROOT / "config.yaml").read_bytes(),
        frozen_now="datetime(2026, 8, 27, 15, 15, tzinfo=UTC)",
        expected_sha=OLD_REVIEWED_SHA,
    )

    assert completed.returncode != 0
    assert observed == FALSE_OUTPUTS["live.yml"]
    assert output_lines == ["refresh=false", "live=false", "cycle=false"]


@pytest.mark.parametrize(
    ("github_env", "expected_sha", "frozen_now"),
    [
        (
            {"GITHUB_REPOSITORY": "attacker/fork"},
            _MATCH_CHECKOUT,
            "datetime(2026, 8, 27, 15, 15, tzinfo=UTC)",
        ),
        (
            {"GITHUB_EVENT_NAME": "push"},
            _MATCH_CHECKOUT,
            "datetime(2026, 8, 27, 15, 15, tzinfo=UTC)",
        ),
        (
            {"GITHUB_REF": "refs/heads/feature"},
            _MATCH_CHECKOUT,
            "datetime(2026, 8, 27, 15, 15, tzinfo=UTC)",
        ),
        (
            {"GITHUB_SHA": "f" * 40},
            _MATCH_CHECKOUT,
            "datetime(2026, 8, 27, 15, 15, tzinfo=UTC)",
        ),
        (
            {"GITHUB_SHA": OLD_REVIEWED_SHA},
            OLD_REVIEWED_SHA,
            "datetime(2026, 8, 27, 15, 15, tzinfo=UTC)",
        ),
        (
            {},
            _MATCH_CHECKOUT,
            "datetime(2026, 8, 27, 15, 14, 59, tzinfo=UTC)",
        ),
    ],
    ids=[
        "repository",
        "event",
        "ref",
        "github-sha",
        "checkout-head",
        "not-before",
    ],
)
def test_live_guard_fails_closed_when_any_context_gate_mismatches(
    tmp_path,
    github_env,
    expected_sha,
    frozen_now,
):
    completed, observed, output_lines = _run_guard(
        tmp_path,
        "live.yml",
        config_bytes=(ROOT / "config.yaml").read_bytes(),
        github_env=github_env,
        frozen_now=frozen_now,
        expected_sha=expected_sha,
    )

    assert completed.returncode != 0
    assert observed == FALSE_OUTPUTS["live.yml"]
    assert output_lines == ["refresh=false", "live=false", "cycle=false"]


@pytest.mark.parametrize(
    "expected_sha",
    ["0" * 39, "0" * 41, "g" * 40, "A" * 40, "  " + "0" * 40],
    ids=["short", "long", "non-hex", "uppercase", "leading-space"],
)
def test_live_guard_rejects_noncanonical_expected_sha(tmp_path, expected_sha):
    completed, observed, output_lines = _run_guard(
        tmp_path,
        "live.yml",
        config_bytes=(ROOT / "config.yaml").read_bytes(),
        frozen_now="datetime(2026, 8, 27, 15, 15, tzinfo=UTC)",
        expected_sha=expected_sha,
    )

    assert completed.returncode != 0
    assert observed == FALSE_OUTPUTS["live.yml"]
    assert output_lines == ["refresh=false", "live=false", "cycle=false"]


@pytest.mark.parametrize("workflow_name", FALSE_OUTPUTS)
@pytest.mark.parametrize("config_state", ["missing", "unreadable-directory"])
def test_workflow_guard_unavailable_config_outputs_false_and_exits_successfully(
    tmp_path,
    workflow_name,
    config_state,
):
    if config_state == "unreadable-directory":
        (tmp_path / "config.yaml").mkdir()
    output_path = tmp_path / "github-output.txt"
    completed = subprocess.run(
        ["bash", "-c", _steps(workflow_name)[1]["run"]],
        cwd=tmp_path,
        env={"GITHUB_OUTPUT": str(output_path), "PATH": os.environ["PATH"]},
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "config.yaml is unavailable" in completed.stdout
    observed = dict(
        line.split("=", 1)
        for line in output_path.read_text(encoding="utf-8").splitlines()
    )
    assert observed == FALSE_OUTPUTS[workflow_name]


@pytest.mark.parametrize("workflow_name", FALSE_OUTPUTS)
def test_workflow_guard_rejects_any_unapproved_config_bytes(tmp_path, workflow_name):
    completed, observed, _output_lines = _run_guard(
        tmp_path,
        workflow_name,
        config_bytes=(ROOT / "config.yaml").read_bytes() + b"\n",
    )

    assert completed.returncode == 0, completed.stderr
    assert "Unapproved config SHA-256" in completed.stdout
    assert observed == FALSE_OUTPUTS[workflow_name]


def test_live_workflow_exposes_publication_capability_only_to_one_step():
    workflow = _workflow("live.yml")
    steps = _steps("live.yml")
    serialized_steps = [yaml.safe_dump(step, sort_keys=True) for step in steps]
    capability_steps = [
        step
        for step, serialized in zip(steps, serialized_steps, strict=True)
        if "LOTTO_GITHUB_PUBLICATION_TOKEN" in serialized
    ]

    assert len(capability_steps) == 1
    execution = capability_steps[0]
    assert execution["name"] == "Run protected production live canary"
    assert execution["if"] == "steps.execution_guard.outputs.cycle == 'true'"
    assert execution["env"] == {
        "LOTTO_GITHUB_PUBLICATION_TOKEN": "${{ secrets.LOTTO_GITHUB_PUBLICATION_TOKEN }}",
        "SMTP_USERNAME": "${{ secrets.SMTP_USERNAME }}",
        "SMTP_PASSWORD": "${{ secrets.SMTP_PASSWORD }}",
    }
    assert 'os.environ.pop("LOTTO_GITHUB_PUBLICATION_TOKEN")' in execution["run"]
    call_lines = [
        line.strip()
        for line in execution["run"].splitlines()
        if line.strip().startswith("orchestrate_github_live_cycle(")
    ]
    assert call_lines == ["orchestrate_github_live_cycle(token=publication_token)"]
    workflow_text = (ROOT / ".github" / "workflows" / "live.yml").read_text(
        encoding="utf-8"
    )
    assert workflow["permissions"] == {"contents": "read"}
    assert "lotto649 live" not in workflow_text
    assert "publish_prepared_history_to_github" not in workflow_text
    assert "publish_frozen_execution_artifacts_to_github" not in workflow_text


@pytest.mark.parametrize("workflow_name", FALSE_OUTPUTS)
def test_stage1_workflows_have_no_ordinary_git_write_or_retry_path(workflow_name):
    workflow = _workflow(workflow_name)
    workflow_text = (ROOT / ".github" / "workflows" / workflow_name).read_text(
        encoding="utf-8"
    )

    assert "continue-on-error" not in workflow_text
    assert "git add" not in workflow_text
    assert "git commit" not in workflow_text
    assert "git push" not in workflow_text
    assert "retry" not in workflow_text.lower()
    assert "strategy" not in next(iter(workflow["jobs"].values()))


def test_release_docs_bind_stage1_to_manual_live_only_double_approval():
    architecture = (ROOT / "docs" / "ARCHITECTURE.md").read_text(encoding="utf-8")
    handoff = (ROOT / "docs" / "CODEX_HANDOFF.md").read_text(encoding="utf-8")
    operations = (ROOT / "docs" / "OPERATIONS.md").read_text(encoding="utf-8")
    architecture_words = " ".join(architecture.split())
    handoff_words = " ".join(handoff.split())
    operations_words = " ".join(operations.split())

    assert DISABLED_CONFIG_SHA256 in architecture_words
    assert DISABLED_CONFIG_SHA256 in operations_words
    assert STAGE1_CONFIG_SHA256 in architecture_words
    assert STAGE1_CONFIG_SHA256 in handoff_words
    assert "manual `workflow_dispatch`" in architecture_words
    assert "backtest.enabled=false" in architecture_words
    assert "no ordinary Git push or unattended schedule" in architecture_words
    assert "Stage 2 may add scheduling only in a separate PR" in architecture_words
    assert "same commit" in operations_words
    assert "runtime switches remain a second gate" in operations_words
    assert "config-only" in operations_words
    assert "not sufficient to re-enable" in operations_words
    assert "operational_history.py" in architecture_words
    assert "operational-history read seam" in operations_words
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "committed processed dataset" not in agents
    assert "verified operational-history seam" in agents
    for words in (architecture_words, operations_words):
        assert "direct `run_backtest`" in words
        assert "`refresh_with_sources`" in words
        assert "missing or unreadable `config.yaml`" in words
        assert "Offline preparation" in words
        assert "network collector" in words
        assert "remote exact-CAS publisher" in words


def test_handoff_matches_current_main_artifacts_and_incident_hold():
    handoff = (ROOT / "docs" / "CODEX_HANDOFF.md").read_text(encoding="utf-8")
    handoff_words = " ".join(handoff.replace(">", "").split())
    draw_lines = (
        (ROOT / "data" / "processed" / "draws.csv")
        .read_text(encoding="utf-8")
        .splitlines()
    )

    assert "2026-08-23" in handoff
    assert "e3c39dda3233cec5933430f22afd6aa8d78a998d" in handoff
    assert "9f16e20c726c7b65eed1d387c4c725d51248f570" in handoff
    assert "4,434" in handoff
    assert "through 2026-08-22" in handoff
    assert "evaluations/2026-08-19__v3_boosting__v1.0.0.json" in handoff
    assert "evaluations/2026-08-22__v3_boosting__v1.0.0.json" in handoff
    assert "predictions/2026-08-26__v3_boosting__v1.0.0.json" in handoff
    assert "execution is currently suspended" in handoff_words
    assert "90177c8" not in handoff
    assert "still ends on 2026-08-12" not in handoff
    assert "Let normal live jobs continue" not in handoff
    assert "latest checked live run after the bridge fallback fix" not in handoff
    assert len(draw_lines) - 1 == 4434
    assert draw_lines[-1].startswith("2026-08-22,")
    assert len(list((ROOT / "evaluations").glob("2026-08-19__*.json"))) == 7
    assert len(list((ROOT / "evaluations").glob("2026-08-22__*.json"))) == 7
    assert len(list((ROOT / "predictions").glob("2026-08-26__*.json"))) == 7
