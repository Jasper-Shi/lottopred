from __future__ import annotations

import ast
import sys
from pathlib import Path
from types import ModuleType

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "email-test.yml"
HOURLY_WORKFLOW = ROOT / ".github" / "workflows" / "research-progress-email.yml"


def _workflow_payload() -> dict:
    return yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def _hourly_workflow_payload() -> dict:
    return yaml.load(
        HOURLY_WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader
    )


def _send_step() -> dict:
    steps = _workflow_payload()["jobs"]["email-test"]["steps"]
    return next(
        step for step in steps if step.get("name") == "Send Gmail configuration test"
    )


def _send_script() -> str:
    run = _send_step()["run"]
    marker = "python - <<'PY'\n"
    return run.split(marker, 1)[1].rsplit("\nPY", 1)[0]


def _execute_send_script(
    monkeypatch: pytest.MonkeyPatch,
    *,
    subject: str | None,
    body: str | None,
) -> list[tuple[str, str]]:
    captured: list[tuple[str, str]] = []
    notification = ModuleType("lotto649.notification")

    def send_email(observed_subject: str, observed_body: str) -> bool:
        captured.append((observed_subject, observed_body))
        return True

    notification.send_email = send_email  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "lotto649.notification", notification)
    for name, value in {
        "RESEARCH_EMAIL_SUBJECT": subject,
        "RESEARCH_EMAIL_BODY": body,
    }.items():
        if value is None:
            monkeypatch.delenv(name, raising=False)
        else:
            monkeypatch.setenv(name, value)

    exec(compile(_send_script(), "email-test.yml", "exec"), {})
    return captured


def test_manual_dispatch_accepts_optional_progress_subject_and_body() -> None:
    manual = _workflow_payload()["on"]["workflow_dispatch"]

    assert manual["inputs"] == {
        "subject": {
            "description": "Optional research-progress email subject",
            "required": "false",
            "type": "string",
        },
        "body": {
            "description": "Optional research-progress email body",
            "required": "false",
            "type": "string",
        },
    }


def test_dispatch_values_cross_the_shell_boundary_only_through_environment() -> None:
    step = _send_step()

    assert step["env"]["RESEARCH_EMAIL_SUBJECT"] == "${{ inputs.subject }}"
    assert step["env"]["RESEARCH_EMAIL_BODY"] == "${{ inputs.body }}"
    assert "${{" not in step["run"]


@pytest.mark.parametrize(
    ("subject", "body", "expected"),
    [
        (
            None,
            None,
            (
                "LOTTO 6/49 alert system is ready",
                "Gmail SMTP configuration succeeded. Future configured model-hit "
                "alerts will be sent automatically.",
            ),
        ),
        (
            "[LOTTO649研究进度] 第1小时更新 — 审计",
            "安全内容：'\"`$(echo not-run)`\n过去一小时没有发现新的有效预测信号。",
            (
                "[LOTTO649研究进度] 第1小时更新 — 审计",
                "安全内容：'\"`$(echo not-run)`\n过去一小时没有发现新的有效预测信号。",
            ),
        ),
    ],
)
def test_send_step_uses_dispatch_content_or_fixed_smoke_defaults(
    monkeypatch: pytest.MonkeyPatch,
    subject: str | None,
    body: str | None,
    expected: tuple[str, str],
) -> None:
    assert _execute_send_script(monkeypatch, subject=subject, body=body) == [expected]


def test_workflow_has_explicit_read_only_repository_permission() -> None:
    assert _workflow_payload()["permissions"] == {"contents": "read"}


def test_workflow_remains_manual_or_fixed_smoke_only_without_a_schedule() -> None:
    triggers = _workflow_payload()["on"]

    assert set(triggers) == {"workflow_dispatch", "push"}
    assert triggers["push"] == {
        "branches": ["main"],
        "paths": ["email-test-trigger.txt"],
    }


def test_smtp_credentials_are_secret_references_and_never_printed() -> None:
    step = _send_step()

    assert {
        name: step["env"][name]
        for name in {
            "SMTP_USERNAME",
            "SMTP_PASSWORD",
            "SMTP_HOST",
            "SMTP_PORT",
            "EMAIL_FROM",
            "EMAIL_TO",
        }
    } == {
        "SMTP_USERNAME": "${{ secrets.SMTP_USERNAME }}",
        "SMTP_PASSWORD": "${{ secrets.SMTP_PASSWORD }}",
        "SMTP_HOST": "${{ secrets.SMTP_HOST }}",
        "SMTP_PORT": "${{ secrets.SMTP_PORT }}",
        "EMAIL_FROM": "${{ secrets.EMAIL_FROM }}",
        "EMAIL_TO": "${{ secrets.EMAIL_TO }}",
    }
    assert "secrets." not in step["run"]
    print_calls = [
        node
        for node in ast.walk(ast.parse(_send_script()))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "print"
    ]
    assert print_calls
    assert all(
        all(isinstance(argument, ast.Constant) for argument in call.args)
        for call in print_calls
    )


def test_repo_native_progress_email_is_an_hourly_schedule_only() -> None:
    triggers = _hourly_workflow_payload()["on"]

    assert set(triggers) == {"schedule"}
    assert triggers["schedule"] == [{"cron": "17 * * * *"}]


def test_hourly_progress_job_is_read_only_bounded_and_smtp_only() -> None:
    workflow = _hourly_workflow_payload()

    assert workflow["permissions"] == {"contents": "read"}
    assert set(workflow["jobs"]) == {"progress-email"}
    job = workflow["jobs"]["progress-email"]
    assert job["timeout-minutes"] == "8"
    assert job["concurrency"] == {
        "group": "lotto649-hourly-research-progress-email",
        "cancel-in-progress": "false",
    }
    assert job["runs-on"] == "ubuntu-latest"

    steps = job["steps"]
    assert steps[0] == {
        "uses": "actions/checkout@v4",
        "with": {"fetch-depth": "0", "persist-credentials": "false"},
    }
    assert steps[1] == {
        "uses": "actions/setup-python@v5",
        "with": {"python-version": "3.12"},
    }
    assert steps[2] == {
        "run": "python -m pip install --no-deps --no-build-isolation -e ."
    }
    assert steps[3] == {
        "name": "Send one committed-state Chinese progress email",
        "env": {
            "SMTP_USERNAME": "${{ secrets.SMTP_USERNAME }}",
            "SMTP_PASSWORD": "${{ secrets.SMTP_PASSWORD }}",
        },
        "run": "python -m lotto649.research_progress_email",
    }
    workflow_text = HOURLY_WORKFLOW.read_text(encoding="utf-8")
    assert "LOTTO_GITHUB_PUBLICATION_TOKEN" not in workflow_text
    assert "workflow_dispatch" not in workflow_text
    assert "curl " not in workflow_text
    assert "gh " not in workflow_text
    assert "lotto649 live" not in workflow_text
    assert "lotto649 backtest" not in workflow_text
    assert "lotto649 bootstrap" not in workflow_text
