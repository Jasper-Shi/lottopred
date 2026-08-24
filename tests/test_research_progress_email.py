from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

import pytest


HEADINGS = (
    "时间",
    "当前阶段",
    "已完成事项",
    "正在进行",
    "下一步",
    "阻塞项",
    "风险",
    "分支/提交",
    "PR/CI",
    "main 保护",
    "canary",
    "三开关状态",
    "数据期数/截止日期",
    "最近前瞻命中",
    "Top-6/12/18",
    "模型/版本",
    "邮件状态",
    "是否需要用户行动",
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )


def _committed_repository(
    tmp_path: Path,
    *,
    config_model_version: str = "v1.0.0",
    evaluation_target: str = "2026-08-22",
) -> tuple[Path, str]:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "config.yaml").write_text(
        f"""\
project:
  timezone: America/Toronto
  model_version: {config_model_version}
data:
  refresh_enabled: true
backtest:
  enabled: false
live:
  enabled: true
  models: [random, ensemble, v3_boosting]
  shadow_models: [v3_boosting]
""",
        encoding="utf-8",
    )
    incident = root / "evidence" / "data_integrity" / "incident"
    _write_json(
        incident / "seal.json",
        {
            "corrected_epoch": {
                "draw_count": 4442,
                "history_through": "2026-08-15",
            },
            "status": "sealed_closed_corrected_epoch",
        },
    )
    registry = root / "evidence" / "operational_history" / "incident"
    registry.mkdir(parents=True)
    (registry / "pin-registry.jsonl").write_text(
        json.dumps(
            {
                "event_kind": "genesis_migration",
                "suffix": {
                    "event_count": 2,
                    "history_through": "2026-08-22",
                },
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    release = root / "evidence" / "release_canaries"
    _write_json(
        release / "2026-08-24-production-main-protection.json",
        {
            "main": "9" * 40,
            "protection": {
                "allow_deletions": False,
                "allow_force_pushes": False,
                "enforce_admins": True,
            },
            "repository": "Jasper-Shi/lottopred",
            "verified_at": "2026-08-24T13:08:14Z",
        },
    )
    _write_json(
        release / "2026-08-24-github-publication-canary.json",
        {
            "created_at": "2026-08-24T13:06:51Z",
            "delete_rejected": True,
            "exact_blob_tree_commit_oids": True,
            "force_update_rejected": True,
            "fresh_anonymous_full_fetch": "8" * 40,
            "stale_update_refs_rejected": True,
            "successful_update_refs": True,
        },
    )
    _write_json(
        release / "2026-08-27-production-live-canary-plan.json",
        {
            "credential": {"installed": False},
            "execution": {
                "not_before": "2026-08-27T15:15:00Z",
                "official_source_gate": {
                    "authorities": ["loto_quebec", "wclc"],
                    "draw_date": "2026-08-26",
                    "requirement": "both_authorities_publish_and_agree",
                },
            },
            "legacy_due_prediction_cohort": {
                "classification": "descriptive_only_nonpromotion",
                "target_draw": "2026-08-26",
            },
            "stage2": {
                "condition": "stage_1_canary_success_and_independent_review",
                "unattended_schedule_in_stage_1": False,
            },
            "status": "preregistered_not_executed",
        },
    )

    predictions = root / "predictions"
    evaluations = root / "evaluations"
    for model, role in (
        ("random", "primary"),
        ("ensemble", "primary"),
        ("v3_boosting", "shadow"),
    ):
        _write_json(
            predictions / f"2026-08-26__{model}__v1.0.0.json",
            {
                "metadata": {
                    "history_draws": 4434,
                    "history_through": "2026-08-22",
                    "role": role,
                },
                "model_name": model,
                "model_version": "v1.0.0",
                "target_draw_date": "2026-08-26",
            },
        )
        _write_json(
            evaluations / f"{evaluation_target}__{model}__v1.0.0.json",
            {
                "final_6_hits": 2 if model == "ensemble" else 1,
                "model_name": model,
                "model_version": "v1.0.0",
                "target_draw_date": evaluation_target,
                "top_6_hits": 2 if model == "ensemble" else 1,
                "top_12_hits": 3 if model == "ensemble" else 2,
                "top_18_hits": 3 if model == "ensemble" else 2,
            },
        )

    subprocess.run(
        ["git", "init", "--quiet", "--initial-branch=main", str(root)],
        check=True,
    )
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    environment = {
        **os.environ,
        "GIT_AUTHOR_DATE": "2026-08-24T16:13:24Z",
        "GIT_AUTHOR_EMAIL": "test@example.invalid",
        "GIT_AUTHOR_NAME": "Test",
        "GIT_COMMITTER_DATE": "2026-08-24T16:13:24Z",
        "GIT_COMMITTER_EMAIL": "test@example.invalid",
        "GIT_COMMITTER_NAME": "Test",
    }
    subprocess.run(
        ["git", "-C", str(root), "commit", "--quiet", "-m", "Merge pull request #33"],
        check=True,
        env=environment,
    )
    head = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return root, head


def _run_context(head: str) -> dict[str, str]:
    return {
        "GITHUB_ACTIONS": "true",
        "GITHUB_EVENT_NAME": "schedule",
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_REPOSITORY": "Jasper-Shi/lottopred",
        "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_RUN_ID": "32750000000",
        "GITHUB_SHA": head,
        "GITHUB_WORKFLOW_REF": (
            "Jasper-Shi/lottopred/.github/workflows/"
            "research-progress-email.yml@refs/heads/main"
        ),
        "GITHUB_WORKFLOW_SHA": head,
        "GITHUB_JOB": "progress-email",
    }


def test_committed_snapshot_builds_truthful_eighteen_part_chinese_report(
    tmp_path: Path,
) -> None:
    from lotto649.research_progress_email import build_research_progress_report

    root, head = _committed_repository(tmp_path)

    report = build_research_progress_report(root, _run_context(head))

    assert report.subject == "[LOTTO 6/49] 中文小时进度 — 已提交证据截至 2026-08-24"
    assert (
        tuple(
            line[1 : line.index("】")]
            for line in report.body.splitlines()
            if line.startswith("【")
        )
        == HEADINGS
    )
    assert "无新结果" in report.body
    assert "当前 PR/CI：未查询" in report.body
    assert "当前远端保护：未查询" in report.body
    assert "Codex 线程内进行中工作：未查询" in report.body
    assert f"来源 SHA：{head}" in report.body
    assert "Actions run id：32750000000" in report.body
    assert re.search(r"事实摘要 SHA-256：[0-9a-f]{64}", report.body)
    assert "Top-6/12/18：2/3/3" in report.body
    assert "正文生成时尚未调用 SMTP，不声明送达成功" in report.body


def test_process_boundary_rejects_unreviewed_email_routing_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from lotto649 import notification
    from lotto649.research_progress_email import ProgressEmailError, main

    root, head = _committed_repository(tmp_path)
    monkeypatch.chdir(root)
    for name, value in _run_context(head).items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("EMAIL_TO", "unreviewed@example.invalid")
    calls: list[tuple[str, str]] = []

    def observe_send(subject: str, body: str) -> bool:
        calls.append((subject, body))
        return True

    monkeypatch.setattr(notification, "send_email", observe_send)

    with pytest.raises(ProgressEmailError, match="override"):
        main()

    assert calls == []


def test_report_rejects_model_version_drift_between_config_and_artifacts(
    tmp_path: Path,
) -> None:
    from lotto649.research_progress_email import (
        ProgressEmailError,
        build_research_progress_report,
    )

    root, head = _committed_repository(tmp_path, config_model_version="v2.0.0")

    with pytest.raises(ProgressEmailError, match="version"):
        build_research_progress_report(root, _run_context(head))


def test_report_does_not_say_a_committed_result_is_missing(tmp_path: Path) -> None:
    from lotto649.research_progress_email import build_research_progress_report

    root, head = _committed_repository(tmp_path, evaluation_target="2026-08-26")

    report = build_research_progress_report(root, _run_context(head))

    recent_hits = next(
        line for line in report.body.splitlines() if line.startswith("【最近前瞻命中】")
    )
    assert "有新结果" in recent_hits
    assert "已有同日已提交评估" in recent_hits
    assert "尚无同日已提交评估" not in recent_hits


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("GITHUB_ACTIONS", "false"),
        ("GITHUB_EVENT_NAME", "workflow_dispatch"),
        ("GITHUB_REF", "refs/heads/topic"),
        ("GITHUB_REPOSITORY", "jasper-shi/lottopred"),
        ("GITHUB_RUN_ATTEMPT", "2"),
        ("GITHUB_RUN_ATTEMPT", "01"),
        ("GITHUB_RUN_ID", "032750000000"),
        ("GITHUB_RUN_ID", "0"),
        ("GITHUB_SHA", "A" * 40),
    ],
)
def test_report_fails_closed_outside_first_scheduled_main_attempt(
    tmp_path: Path, name: str, value: str
) -> None:
    from lotto649.research_progress_email import (
        ProgressEmailError,
        build_research_progress_report,
    )

    root, head = _committed_repository(tmp_path)
    context = {**_run_context(head), name: value}

    with pytest.raises(ProgressEmailError):
        build_research_progress_report(root, context)


def test_report_rejects_a_different_scheduled_workflow_identity(tmp_path: Path) -> None:
    from lotto649.research_progress_email import (
        ProgressEmailError,
        build_research_progress_report,
    )

    root, head = _committed_repository(tmp_path)
    context = {
        **_run_context(head),
        "GITHUB_WORKFLOW_REF": (
            "Jasper-Shi/lottopred/.github/workflows/email-test.yml@refs/heads/main"
        ),
    }

    with pytest.raises(ProgressEmailError, match="WORKFLOW"):
        build_research_progress_report(root, context)


def test_report_uses_committed_blobs_and_never_digests_secrets(tmp_path: Path) -> None:
    from lotto649.research_progress_email import build_research_progress_report

    root, head = _committed_repository(tmp_path)
    first_context = {
        **_run_context(head),
        "SMTP_USERNAME": "secret-user-marker",
        "SMTP_PASSWORD": "secret-password-marker",
    }
    first = build_research_progress_report(root, first_context)

    (root / "config.yaml").write_text("malicious: uncommitted\n", encoding="utf-8")
    second = build_research_progress_report(
        root,
        {
            **_run_context(head),
            "SMTP_USERNAME": "different-secret-user-marker",
            "SMTP_PASSWORD": "different-secret-password-marker",
        },
    )

    assert second == first
    assert "secret" not in first.subject
    assert "secret" not in first.body


def test_report_ignores_local_git_replacement_objects(tmp_path: Path) -> None:
    from lotto649.research_progress_email import build_research_progress_report

    root, original_head = _committed_repository(tmp_path)
    expected = build_research_progress_report(root, _run_context(original_head))
    config_path = root / "config.yaml"
    replacement_config = config_path.read_text(encoding="utf-8").replace(
        "refresh_enabled: true", "refresh_enabled: false"
    )
    config_path.write_text(replacement_config, encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "config.yaml"], check=True)
    environment = {
        **os.environ,
        "GIT_AUTHOR_DATE": "2026-08-24T17:13:24Z",
        "GIT_AUTHOR_EMAIL": "test@example.invalid",
        "GIT_AUTHOR_NAME": "Test",
        "GIT_COMMITTER_DATE": "2026-08-24T17:13:24Z",
        "GIT_COMMITTER_EMAIL": "test@example.invalid",
        "GIT_COMMITTER_NAME": "Test",
    }
    subprocess.run(
        ["git", "-C", str(root), "commit", "--quiet", "-m", "replacement"],
        check=True,
        env=environment,
    )
    replacement_head = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    subprocess.run(
        ["git", "-C", str(root), "switch", "--quiet", "--detach", original_head],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(root), "replace", original_head, replacement_head],
        check=True,
    )

    observed = build_research_progress_report(root, _run_context(original_head))

    assert observed == expected


def test_report_requires_a_full_history_checkout(tmp_path: Path) -> None:
    from lotto649.research_progress_email import (
        ProgressEmailError,
        build_research_progress_report,
    )

    root, head = _committed_repository(tmp_path)
    (root / ".git" / "shallow").write_text(f"{head}\n", encoding="ascii")

    with pytest.raises(ProgressEmailError, match="full-history"):
        build_research_progress_report(root, _run_context(head))


@pytest.mark.parametrize("smtp_result", [True, False])
def test_process_boundary_attempts_exactly_one_email_without_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    smtp_result: bool,
) -> None:
    from lotto649 import notification
    from lotto649.research_progress_email import ProgressEmailError, main

    root, head = _committed_repository(tmp_path)
    monkeypatch.chdir(root)
    for name, value in _run_context(head).items():
        monkeypatch.setenv(name, value)
    for name in ("SMTP_HOST", "SMTP_PORT", "EMAIL_FROM", "EMAIL_TO"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("SMTP_USERNAME", "sender@example.invalid")
    monkeypatch.setenv("SMTP_PASSWORD", "not-a-real-secret")
    calls: list[tuple[str, str]] = []

    def observe_send(subject: str, body: str) -> bool:
        calls.append((subject, body))
        return smtp_result

    monkeypatch.setattr(notification, "send_email", observe_send)

    if smtp_result:
        assert main() == 0
    else:
        with pytest.raises(ProgressEmailError, match="not sent"):
            main()

    assert len(calls) == 1
    subject, body = calls[0]
    assert subject.startswith("[LOTTO 6/49] 中文小时进度")
    assert "正文生成时尚未调用 SMTP，不声明送达成功" in body
    assert "sender@example.invalid" not in body
    assert "not-a-real-secret" not in body
