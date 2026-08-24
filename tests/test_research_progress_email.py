from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
GENERATED_AT = datetime(2026, 8, 24, 17, 20, 24, tzinfo=UTC)
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


def _clone_current_repository(tmp_path: Path) -> tuple[Path, str]:
    root = tmp_path / "full-repository"
    subprocess.run(
        ["git", "clone", "--no-local", "--quiet", str(ROOT), str(root)],
        check=True,
        capture_output=True,
    )
    return root, _repository_head(root)


def _repository_head(root: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _commit_fixture(root: Path, message: str) -> str:
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
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
        ["git", "-C", str(root), "commit", "--quiet", "-m", message],
        check=True,
        env=environment,
    )
    return _repository_head(root)


def _run_context(head: str) -> dict[str, str]:
    return {
        "GITHUB_ACTIONS": "true",
        "GITHUB_EVENT_NAME": "schedule",
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_REPOSITORY": "Jasper-Shi/lottopred",
        "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_RUN_ID": "32750000000",
        "GITHUB_RUN_NUMBER": "327",
        "GITHUB_SHA": head,
        "GITHUB_WORKFLOW_REF": (
            "Jasper-Shi/lottopred/.github/workflows/"
            "research-progress-email.yml@refs/heads/main"
        ),
        "GITHUB_WORKFLOW_SHA": head,
        "GITHUB_JOB": "progress-email",
    }


def test_report_ignores_committed_decoy_registry_and_seal(
    tmp_path: Path,
) -> None:
    from lotto649.research_progress_email import build_research_progress_report

    root, _head = _clone_current_repository(tmp_path)
    decoy = "ZZZ-untrusted-decoy"
    _write_json(
        root / "evidence" / "data_integrity" / decoy / "seal.json",
        {
            "corrected_epoch": {
                "draw_count": 9_000,
                "history_through": "2099-01-01",
            },
            "status": "sealed_closed_corrected_epoch",
        },
    )
    registry = root / "evidence" / "operational_history" / decoy
    registry.mkdir(parents=True)
    (registry / "pin-registry.jsonl").write_text(
        json.dumps(
            {
                "event_kind": "decoy",
                "suffix": {"event_count": 1, "history_through": "2099-01-02"},
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    head = _commit_fixture(root, "add untrusted decoy history files")

    report = build_research_progress_report(root, _run_context(head))

    assert "纠正后已提交验证视图：4444 期，截至 2026-08-22" in report.body
    assert "2099" not in report.body


def test_report_rejects_evaluation_beyond_published_history_chronology(
    tmp_path: Path,
) -> None:
    from lotto649.research_progress_email import (
        ProgressEmailError,
        build_research_progress_report,
    )

    root, _head = _clone_current_repository(tmp_path)
    source = root / "evaluations" / "2026-08-22__ensemble__v1.0.0.json"
    payload = json.loads(source.read_text(encoding="utf-8"))
    payload["target_draw_date"] = "2026-08-27"
    _write_json(
        root / "evaluations" / "2026-08-27__ensemble__v1.0.0.json",
        payload,
    )
    head = _commit_fixture(root, "add chronologically impossible evaluation")

    with pytest.raises(ProgressEmailError, match="chronology"):
        build_research_progress_report(root, _run_context(head))


@pytest.mark.parametrize("artifact", ["registry", "seal"])
def test_report_rejects_tampered_published_history_authority(
    tmp_path: Path, artifact: str
) -> None:
    from lotto649.research_progress_email import (
        ProgressEmailError,
        build_research_progress_report,
    )

    root, _head = _clone_current_repository(tmp_path)
    if artifact == "registry":
        path = (
            root
            / "evidence"
            / "operational_history"
            / "DI-2026-08-20-registered-history"
            / "pin-registry.jsonl"
        )
        path.write_bytes(path.read_bytes() + b"tampered\n")
    else:
        path = (
            root
            / "evidence"
            / "data_integrity"
            / "DI-2026-08-20-registered-history"
            / "seal.json"
        )
        seal = json.loads(path.read_text(encoding="utf-8"))
        seal["status"] = "tampered"
        _write_json(path, seal)
    head = _commit_fixture(root, f"tamper published history {artifact}")

    with pytest.raises(ProgressEmailError, match="published-history"):
        build_research_progress_report(root, _run_context(head))


def test_committed_snapshot_builds_truthful_eighteen_part_chinese_report(
    tmp_path: Path,
) -> None:
    from lotto649.research_progress_email import build_research_progress_report

    root, head = _clone_current_repository(tmp_path)

    report = build_research_progress_report(
        root, _run_context(head), generated_at=GENERATED_AT
    )

    assert report.subject == (
        "[LOTTO649研究进度] 第327次更新 — 已提交状态/ensemble v1.0.0"
    )
    assert (
        tuple(
            line[1 : line.index("】")]
            for line in report.body.splitlines()
            if line.startswith("【")
        )
        == HEADINGS
    )
    assert "本小时是否新增：未判定（无持久游标）" in report.body
    assert "当前 PR/CI：未查询" in report.body
    assert "当前远端保护：未查询" in report.body
    assert "Codex 线程内进行中工作：未查询" in report.body
    assert f"来源 SHA：{head}" in report.body
    assert "Actions run id：32750000000" in report.body
    assert "本次报告生成时间：2026-08-24T17:20:24Z" in report.body
    assert "第 327 次 workflow 更新，不代表累计研究小时" in report.body
    assert re.search(r"事实摘要 SHA-256：[0-9a-f]{64}", report.body)
    assert "Top-6/12/18：2/3/3" in report.body
    assert "正文生成时尚未调用 SMTP，不声明送达成功" in report.body


def test_latest_metrics_name_exact_evaluation_version_and_legacy_qualification(
    tmp_path: Path,
) -> None:
    from lotto649.research_progress_email import build_research_progress_report

    root, head = _clone_current_repository(tmp_path)

    report = build_research_progress_report(root, _run_context(head))

    recent_hits = next(
        line for line in report.body.splitlines() if line.startswith("【最近前瞻命中】")
    )
    top_hits = next(
        line for line in report.body.splitlines() if line.startswith("【Top-6/12/18】")
    )
    assert "ensemble v1.0.0" in recent_hits
    assert "ensemble v1.0.0" in top_hits
    assert "前事故/旧版畸形历史 cohort" in top_hits
    assert "descriptive-only" in top_hits
    assert "nonpromotion" in top_hits


def test_metric_version_is_not_relabelled_by_a_new_prediction_cohort(
    tmp_path: Path,
) -> None:
    from lotto649.research_progress_email import build_research_progress_report

    root, _head = _clone_current_repository(tmp_path)
    config_path = root / "config.yaml"
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace(
            "model_version: v1.0.0", "model_version: v2.0.0"
        ),
        encoding="utf-8",
    )
    for source in sorted((root / "predictions").glob("2026-08-26__*__v1.0.0.json")):
        payload = json.loads(source.read_text(encoding="utf-8"))
        payload["target_draw_date"] = "2026-08-29"
        payload["model_version"] = "v2.0.0"
        target = source.with_name(
            source.name.replace("2026-08-26", "2026-08-29").replace("v1.0.0", "v2.0.0")
        )
        _write_json(target, payload)
    head = _commit_fixture(root, "add a new-version prediction cohort")

    report = build_research_progress_report(root, _run_context(head))

    recent_hits = next(
        line for line in report.body.splitlines() if line.startswith("【最近前瞻命中】")
    )
    top_hits = next(
        line for line in report.body.splitlines() if line.startswith("【Top-6/12/18】")
    )
    models = next(
        line for line in report.body.splitlines() if line.startswith("【模型/版本】")
    )
    assert "ensemble v1.0.0" in recent_hits
    assert "ensemble v1.0.0" in top_hits
    assert "version=v2.0.0" in models


def test_verified_operational_metric_is_not_permanently_labelled_legacy(
    tmp_path: Path,
) -> None:
    from lotto649.research_progress_email import build_research_progress_report

    root, _head = _clone_current_repository(tmp_path)
    prediction_path = root / "predictions" / "2026-08-22__ensemble__v1.0.0.json"
    prediction = json.loads(prediction_path.read_text(encoding="utf-8"))
    prediction["metadata"]["history_draws"] = 4443
    _write_json(prediction_path, prediction)
    evaluation_path = root / "evaluations" / "2026-08-22__ensemble__v1.0.0.json"
    evaluation = json.loads(evaluation_path.read_text(encoding="utf-8"))
    evaluation["prediction_source"] = {
        "kind": "verified_operational_history",
        "claims": {
            "corrected_history": True,
            "promotion_evidence_eligible": True,
        },
    }
    _write_json(evaluation_path, evaluation)
    head = _commit_fixture(root, "classify one corrected operational evaluation")

    report = build_research_progress_report(root, _run_context(head))

    top_hits = next(
        line for line in report.body.splitlines() if line.startswith("【Top-6/12/18】")
    )
    assert "纠正后 verified operational cohort" in top_hits
    assert "前事故/旧版畸形历史 cohort" not in top_hits
    assert "不构成统计显著性或晋级结论" in top_hits


def test_report_fails_closed_if_stage_one_plan_enables_unattended_live_schedule(
    tmp_path: Path,
) -> None:
    from lotto649.research_progress_email import (
        ProgressEmailError,
        build_research_progress_report,
    )

    root, _head = _clone_current_repository(tmp_path)
    plan_path = next(
        (root / "evidence" / "release_canaries").glob(
            "*-production-live-canary-plan.json"
        )
    )
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    plan["stage2"]["unattended_schedule_in_stage_1"] = True
    _write_json(plan_path, plan)
    head = _commit_fixture(root, "enable an unsafe stage-one schedule")

    with pytest.raises(ProgressEmailError, match="schedule"):
        build_research_progress_report(root, _run_context(head))


def test_process_boundary_rejects_unreviewed_email_routing_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from lotto649 import notification
    from lotto649.research_progress_email import ProgressEmailError, main

    root, head = _clone_current_repository(tmp_path)
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

    root, _head = _clone_current_repository(tmp_path)
    config_path = root / "config.yaml"
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace(
            "model_version: v1.0.0", "model_version: v2.0.0"
        ),
        encoding="utf-8",
    )
    head = _commit_fixture(root, "introduce model version drift")

    with pytest.raises(ProgressEmailError, match="version"):
        build_research_progress_report(root, _run_context(head))


def test_report_distinguishes_pending_prediction_from_hourly_novelty(
    tmp_path: Path,
) -> None:
    from lotto649.research_progress_email import build_research_progress_report

    root, head = _clone_current_repository(tmp_path)

    report = build_research_progress_report(root, _run_context(head))

    recent_hits = next(
        line for line in report.body.splitlines() if line.startswith("【最近前瞻命中】")
    )
    assert "本小时是否新增：未判定（无持久游标）" in recent_hits
    assert "最新预测目标 2026-08-26 尚待同日已提交评估" in recent_hits
    assert "无新结果：" not in recent_hits


@pytest.mark.parametrize("field", ["actual", "top_12_hits"])
def test_report_recomputes_latest_hits_and_rejects_tampered_evaluation(
    tmp_path: Path, field: str
) -> None:
    from lotto649.research_progress_email import (
        ProgressEmailError,
        build_research_progress_report,
    )

    root, _head = _clone_current_repository(tmp_path)
    evaluation_path = root / "evaluations" / "2026-08-22__ensemble__v1.0.0.json"
    evaluation = json.loads(evaluation_path.read_text(encoding="utf-8"))
    if field == "actual":
        evaluation["actual"] = [1, 2, 3, 4, 5, 6]
    else:
        evaluation["top_12_hits"] = 4
        evaluation["top_18_hits"] = 4
    _write_json(evaluation_path, evaluation)
    head = _commit_fixture(root, f"tamper evaluation {field}")

    with pytest.raises(ProgressEmailError, match="actual|hit counts"):
        build_research_progress_report(root, _run_context(head))


def test_final_combination_may_validly_differ_from_ranked_top_six(
    tmp_path: Path,
) -> None:
    from lotto649.research_progress_email import build_research_progress_report

    root, _head = _clone_current_repository(tmp_path)
    prediction_path = root / "predictions" / "2026-08-22__ensemble__v1.0.0.json"
    prediction = json.loads(prediction_path.read_text(encoding="utf-8"))
    prediction["final_combination"] = [1, 2, 3, 4, 6, 7]
    _write_json(prediction_path, prediction)
    evaluation_path = root / "evaluations" / "2026-08-22__ensemble__v1.0.0.json"
    evaluation = json.loads(evaluation_path.read_text(encoding="utf-8"))
    evaluation["final_6_hits"] = 0
    evaluation["matched_final"] = []
    _write_json(evaluation_path, evaluation)
    head = _commit_fixture(root, "use an independent constrained final combination")

    report = build_research_progress_report(root, _run_context(head))

    assert "最终组合命中 0/6" in report.body
    assert "Top-6/12/18：2/3/3" in report.body


@pytest.mark.parametrize("field", ["history_through", "history_draws", "generated_at"])
def test_latest_prediction_cohort_rejects_future_information(
    tmp_path: Path, field: str
) -> None:
    from lotto649.research_progress_email import (
        ProgressEmailError,
        build_research_progress_report,
    )

    root, _head = _clone_current_repository(tmp_path)
    for path in sorted((root / "predictions").glob("2026-08-26__*__v1.0.0.json")):
        prediction = json.loads(path.read_text(encoding="utf-8"))
        if field == "history_through":
            prediction["metadata"]["history_through"] = "2026-08-25"
        elif field == "history_draws":
            prediction["metadata"]["history_draws"] = 9999
        else:
            prediction["generated_at"] = "2026-08-26T00:00:00-04:00"
        _write_json(path, prediction)
    head = _commit_fixture(root, f"leak future prediction {field}")

    with pytest.raises(ProgressEmailError, match="chronology|published history"):
        build_research_progress_report(root, _run_context(head))


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
        ("GITHUB_RUN_NUMBER", "01"),
        ("GITHUB_RUN_NUMBER", "0"),
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

    root = ROOT
    head = _repository_head(root)
    context = {**_run_context(head), name: value}

    with pytest.raises(ProgressEmailError):
        build_research_progress_report(root, context)


def test_report_rejects_a_different_scheduled_workflow_identity(tmp_path: Path) -> None:
    from lotto649.research_progress_email import (
        ProgressEmailError,
        build_research_progress_report,
    )

    root = ROOT
    head = _repository_head(root)
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

    root, head = _clone_current_repository(tmp_path)
    first_context = {
        **_run_context(head),
        "SMTP_USERNAME": "secret-user-marker",
        "SMTP_PASSWORD": "secret-password-marker",
    }
    first = build_research_progress_report(
        root, first_context, generated_at=GENERATED_AT
    )

    (root / "config.yaml").write_text("malicious: uncommitted\n", encoding="utf-8")
    second = build_research_progress_report(
        root,
        {
            **_run_context(head),
            "SMTP_USERNAME": "different-secret-user-marker",
            "SMTP_PASSWORD": "different-secret-password-marker",
        },
        generated_at=GENERATED_AT,
    )

    assert second == first
    assert "secret" not in first.subject
    assert "secret" not in first.body


def test_report_ignores_local_git_replacement_objects(tmp_path: Path) -> None:
    from lotto649.research_progress_email import build_research_progress_report

    root, original_head = _clone_current_repository(tmp_path)
    expected = build_research_progress_report(
        root, _run_context(original_head), generated_at=GENERATED_AT
    )
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

    observed = build_research_progress_report(
        root, _run_context(original_head), generated_at=GENERATED_AT
    )

    assert observed == expected


def test_report_requires_a_full_history_checkout(tmp_path: Path) -> None:
    from lotto649.research_progress_email import (
        ProgressEmailError,
        build_research_progress_report,
    )

    root, head = _clone_current_repository(tmp_path)
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

    root, head = _clone_current_repository(tmp_path)
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
    assert subject.startswith("[LOTTO649研究进度] 第327次更新")
    assert "正文生成时尚未调用 SMTP，不声明送达成功" in body
    assert "sender@example.invalid" not in body
    assert "not-a-real-secret" not in body
