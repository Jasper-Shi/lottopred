from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
DISABLED_CONFIG_SHA256 = (
    "ad3237bc57c85013e85dad16d1b6f04f43b50991d666a4b1528bf5b8614a76b6"
)
WORKFLOWS = {
    "live.yml": {
        "commands": {"lotto649 live": "cycle"},
        "outputs": {
            "refresh": "false",
            "live": "false",
            "cycle": "false",
        },
    },
    "integration.yml": {
        "commands": {
            "lotto649 bootstrap": "refresh",
            "lotto649 backtest": "backtest",
            "lotto649 live": "cycle",
        },
        "outputs": {
            "refresh": "false",
            "backtest": "false",
            "live": "false",
            "cycle": "false",
        },
    },
    "backtest.yml": {
        "commands": {
            "lotto649 bootstrap": "refresh",
            "lotto649 backtest": "backtest",
        },
        "outputs": {
            "refresh": "false",
            "backtest": "false",
        },
    },
}
WORKFLOW_SWITCHES = {
    "live.yml": [("data", "refresh_enabled"), ("live", "enabled")],
    "integration.yml": [
        ("data", "refresh_enabled"),
        ("backtest", "enabled"),
        ("live", "enabled"),
    ],
    "backtest.yml": [("data", "refresh_enabled"), ("backtest", "enabled")],
}


def _steps(workflow_name: str) -> list[dict]:
    payload = yaml.safe_load(
        (ROOT / ".github" / "workflows" / workflow_name).read_text(
            encoding="utf-8"
        )
    )
    assert len(payload["jobs"]) == 1
    return next(iter(payload["jobs"].values()))["steps"]


@pytest.mark.parametrize("workflow_name", WORKFLOWS)
def test_execution_guard_precedes_and_conditions_every_runtime_step(workflow_name):
    steps = _steps(workflow_name)

    assert steps[0]["uses"] == "actions/checkout@v4"
    guard = steps[1]
    assert guard["id"] == "execution_guard"
    assert guard["name"] == "Read incident execution guards"
    assert "config.yaml" in guard["run"]
    assert "hashlib.sha256" in guard["run"]
    assert DISABLED_CONFIG_SHA256 in guard["run"]
    assert "read_text" not in guard["run"]
    assert "splitlines" not in guard["run"]
    assert "pip install" not in guard["run"]
    assert "setup-python" not in guard["run"]
    assert "lotto649 " not in guard["run"]
    assert '"any"' not in guard["run"]
    assert all(
        "steps.execution_guard.outputs." in step.get("if", "")
        and "== 'true'" in step["if"]
        for step in steps[2:]
    )

    for command, output in WORKFLOWS[workflow_name]["commands"].items():
        matching = [
            step
            for step in steps
            if any(
                line.strip().startswith(command)
                for line in step.get("run", "").splitlines()
            )
        ]
        assert len(matching) == 1
        assert matching[0]["if"] == (
            f"steps.execution_guard.outputs.{output} == 'true'"
        )


@pytest.mark.parametrize("workflow_name", WORKFLOWS)
def test_committed_disabled_config_makes_workflow_guard_exit_successfully(
    tmp_path,
    workflow_name,
):
    steps = _steps(workflow_name)
    guard_script = steps[1]["run"]
    config_bytes = (ROOT / "config.yaml").read_bytes()
    assert hashlib.sha256(config_bytes).hexdigest() == DISABLED_CONFIG_SHA256
    (tmp_path / "config.yaml").write_bytes(config_bytes)
    output_path = tmp_path / "github-output.txt"
    env = {**os.environ, "GITHUB_OUTPUT": str(output_path)}

    completed = subprocess.run(
        ["bash", "-c", guard_script],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "Verified incident-disabled config" in completed.stdout
    observed = dict(
        line.split("=", 1)
        for line in output_path.read_text(encoding="utf-8").splitlines()
    )
    assert observed == WORKFLOWS[workflow_name]["outputs"]


@pytest.mark.parametrize("workflow_name", ["live.yml", "integration.yml"])
def test_live_workflow_stage_remains_sealed_after_live_only_toggle(
    tmp_path,
    workflow_name,
):
    (tmp_path / "config.yaml").write_text(
        """data:
  refresh_enabled: false
backtest:
  enabled: false
live:
  enabled: true
""",
        encoding="utf-8",
    )
    output_path = tmp_path / "github-output.txt"
    completed = subprocess.run(
        ["bash", "-c", _steps(workflow_name)[1]["run"]],
        cwd=tmp_path,
        env={**os.environ, "GITHUB_OUTPUT": str(output_path)},
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    observed = dict(
        line.split("=", 1)
        for line in output_path.read_text(encoding="utf-8").splitlines()
    )
    assert observed["refresh"] == "false"
    assert observed["live"] == "false"
    assert observed["cycle"] == "false"
    assert "Unapproved config SHA-256" in completed.stdout


@pytest.mark.parametrize("workflow_name", WORKFLOWS)
@pytest.mark.parametrize(
    "yaml_value",
    ["true", '"true"'],
    ids=["boolean-true", "string-true"],
)
def test_workflow_guard_rejects_unapproved_true_toggle(
    tmp_path,
    workflow_name,
    yaml_value,
):
    (tmp_path / "config.yaml").write_text(
        f"""data:
  refresh_enabled: {yaml_value}
backtest:
  enabled: {yaml_value}
live:
  enabled: {yaml_value}
""",
        encoding="utf-8",
    )
    output_path = tmp_path / "github-output.txt"
    completed = subprocess.run(
        ["bash", "-c", _steps(workflow_name)[1]["run"]],
        cwd=tmp_path,
        env={**os.environ, "GITHUB_OUTPUT": str(output_path)},
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "Unapproved config SHA-256" in completed.stdout
    observed = dict(
        line.split("=", 1)
        for line in output_path.read_text(encoding="utf-8").splitlines()
    )
    assert set(observed.values()) == {"false"}


@pytest.mark.parametrize("workflow_name", WORKFLOWS)
def test_workflow_guard_rejects_any_byte_change_to_disabled_config(
    tmp_path,
    workflow_name,
):
    config_bytes = (ROOT / "config.yaml").read_bytes() + b"\n"
    assert hashlib.sha256(config_bytes).hexdigest() != DISABLED_CONFIG_SHA256
    (tmp_path / "config.yaml").write_bytes(config_bytes)
    output_path = tmp_path / "github-output.txt"
    completed = subprocess.run(
        ["bash", "-c", _steps(workflow_name)[1]["run"]],
        cwd=tmp_path,
        env={**os.environ, "GITHUB_OUTPUT": str(output_path)},
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "Unapproved config SHA-256" in completed.stdout
    observed = dict(
        line.split("=", 1)
        for line in output_path.read_text(encoding="utf-8").splitlines()
    )
    assert set(observed.values()) == {"false"}


@pytest.mark.parametrize(
    ("workflow_name", "duplicate_section", "duplicate_key"),
    [
        (workflow_name, section, key)
        for workflow_name, switches in WORKFLOW_SWITCHES.items()
        for section, key in switches
    ],
)
@pytest.mark.parametrize("duplicate_kind", ["section", "key"])
def test_workflow_guard_fails_closed_for_duplicate_switch_definitions(
    tmp_path,
    workflow_name,
    duplicate_section,
    duplicate_key,
    duplicate_kind,
):
    switches = [
        ("data", "refresh_enabled"),
        ("backtest", "enabled"),
        ("live", "enabled"),
    ]
    blocks = []
    for section, key in switches:
        values = ["true"]
        if duplicate_kind == "key" and section == duplicate_section:
            values.append("true")
        block = [f"{section}:", *(f"  {key}: {value}" for value in values)]
        blocks.append("\n".join(block))
    if duplicate_kind == "section":
        blocks.append(f"{duplicate_section}:\n  {duplicate_key}: true")
    (tmp_path / "config.yaml").write_text(
        "\n".join(blocks) + "\n",
        encoding="utf-8",
    )
    output_path = tmp_path / "github-output.txt"
    completed = subprocess.run(
        ["bash", "-c", _steps(workflow_name)[1]["run"]],
        cwd=tmp_path,
        env={**os.environ, "GITHUB_OUTPUT": str(output_path)},
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    observed = dict(
        line.split("=", 1)
        for line in output_path.read_text(encoding="utf-8").splitlines()
    )
    assert set(observed.values()) == {"false"}


@pytest.mark.parametrize("workflow_name", WORKFLOWS)
@pytest.mark.parametrize(
    "config_text",
    [
        """data :
  refresh_enabled: true
data:
  refresh_enabled: true
backtest:
  enabled: true
live:
  enabled: true
""",
        """data:
  refresh_enabled : true
  refresh_enabled: true
backtest:
  enabled: true
live:
  enabled: true
""",
        """data:
  "refresh_enabled": true
  refresh_enabled: true
backtest:
  enabled: true
live:
  enabled: true
""",
    ],
    ids=["spaced-section", "spaced-key", "quoted-key"],
)
def test_workflow_guard_rejects_yaml_equivalent_key_bypasses(
    tmp_path,
    workflow_name,
    config_text,
):
    (tmp_path / "config.yaml").write_text(config_text, encoding="utf-8")
    output_path = tmp_path / "github-output.txt"
    completed = subprocess.run(
        ["bash", "-c", _steps(workflow_name)[1]["run"]],
        cwd=tmp_path,
        env={**os.environ, "GITHUB_OUTPUT": str(output_path)},
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    observed = dict(
        line.split("=", 1)
        for line in output_path.read_text(encoding="utf-8").splitlines()
    )
    assert set(observed.values()) == {"false"}


def test_incident_docs_require_sha_bound_and_runtime_double_approval():
    architecture = (ROOT / "docs" / "ARCHITECTURE.md").read_text(
        encoding="utf-8"
    )
    operations = (ROOT / "docs" / "OPERATIONS.md").read_text(encoding="utf-8")
    architecture_words = " ".join(architecture.split())
    operations_words = " ".join(operations.split())

    assert DISABLED_CONFIG_SHA256 in architecture_words
    assert DISABLED_CONFIG_SHA256 in operations_words
    assert "same reviewed commit" in architecture_words
    assert "same commit" in operations_words
    assert "second, independent approval gate" in architecture_words
    assert "runtime switches remain a second gate" in operations_words
    assert "config-only" in architecture_words
    assert "config-only" in operations_words
    assert "never sufficient to reopen" in architecture_words
    assert "not sufficient to re-enable" in operations_words
