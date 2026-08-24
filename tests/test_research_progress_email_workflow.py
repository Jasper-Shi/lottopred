from __future__ import annotations

import ast
import sys
from pathlib import Path
from types import ModuleType

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "email-test.yml"


def _workflow_payload() -> dict:
    return yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


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
