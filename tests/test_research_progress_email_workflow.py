from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "email-test.yml"


def _workflow_payload() -> dict:
    return yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def test_manual_email_dispatch_accepts_safe_progress_subject_and_body() -> None:
    payload = _workflow_payload()
    manual = payload["on"]["workflow_dispatch"]

    assert set(manual["inputs"]) == {"subject", "body"}
    assert manual["inputs"]["subject"]["required"] == "false"
    assert manual["inputs"]["body"]["required"] == "false"

    step = payload["jobs"]["email-test"]["steps"][-1]
    assert step["env"]["SMTP_USERNAME"] == "${{ secrets.SMTP_USERNAME }}"
    assert step["env"]["SMTP_PASSWORD"] == "${{ secrets.SMTP_PASSWORD }}"
    assert step["env"]["RESEARCH_EMAIL_SUBJECT"] == "${{ inputs.subject }}"
    assert step["env"]["RESEARCH_EMAIL_BODY"] == "${{ inputs.body }}"
    assert "${{ inputs.subject }}" not in step["run"]
    assert "${{ inputs.body }}" not in step["run"]

