from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = (
    ROOT
    / "evidence"
    / "release_canaries"
    / "2026-08-27-production-live-canary-plan.json"
)
LIVE_WORKFLOW_PATH = ROOT / ".github" / "workflows" / "live.yml"
LEGACY_MANIFEST_PATH = (
    ROOT
    / "evidence"
    / "data_integrity"
    / "DI-2026-08-20-registered-history"
    / "legacy-2026-08-26-prediction-cohort.json"
)
ARMED_CONFIG_SHA256 = "d53a9a9eed5ab434b021472135d6aed65c2c052339e0dfb88f8c00d46c0d8931"
MODELS = [
    "random",
    "long_frequency",
    "recent_frequency",
    "ema_gap",
    "logistic",
    "ensemble",
    "v3_boosting",
]


def _plan() -> dict:
    return json.loads(PLAN_PATH.read_text(encoding="utf-8"))


def _workflow() -> dict:
    return yaml.load(
        LIVE_WORKFLOW_PATH.read_text(encoding="utf-8"), Loader=yaml.BaseLoader
    )


def test_plan_binds_exact_armed_config_and_reviewed_main() -> None:
    plan = _plan()
    config_bytes = (ROOT / "config.yaml").read_bytes()
    config = yaml.safe_load(config_bytes)

    assert hashlib.sha256(config_bytes).hexdigest() == ARMED_CONFIG_SHA256
    assert plan["config"] == {
        "backtest_enabled": False,
        "data_refresh_enabled": True,
        "live_enabled": True,
        "path": "config.yaml",
        "sha256": ARMED_CONFIG_SHA256,
    }
    assert config["data"]["refresh_enabled"] is True
    assert config["live"]["enabled"] is True
    assert config["backtest"]["enabled"] is False

    baseline = plan["production_baseline"]
    assert baseline["main_commit"] == ("60f972b217f7bd23d1b4807e96034db0cfd1fe2e")
    assert baseline["live_orchestration"] == {
        "merge_commit": "2fe56a40532f7be2586a5cfc004699561556e849",
        "pull_request": 31,
    }
    assert baseline["prediction_origin_fix"] == {
        "head_commit": "69d59709dd5f8d9c6d8e761dc84d784af844144d",
        "merge_commit": "60f972b217f7bd23d1b4807e96034db0cfd1fe2e",
        "pull_request": 32,
    }
    origin_gate = next(
        gate
        for gate in plan["prerequisites"]
        if gate["id"] == "source_prediction_ancestor_origin_fix"
    )
    assert origin_gate["state"] == "satisfied"


def test_plan_preregisters_exact_history_and_complete_model_cohorts() -> None:
    plan = _plan()
    expected = plan["expected_success"]

    assert expected["history"] == {
        "draw_count": 4445,
        "history_through": "2026-08-26",
    }
    assert expected["evaluations"]["count"] == 7
    assert expected["evaluations"]["target_draw"] == "2026-08-26"
    assert expected["predictions"]["count"] == 7
    assert expected["predictions"]["target_draw"] == "2026-08-29"
    for artifact_kind in ("evaluations", "predictions"):
        cohort = expected[artifact_kind]["models"]
        assert cohort["primary"] + cohort["shadow"] == MODELS
        assert cohort["shadow"] == ["v3_boosting"]
    assert expected["preservation"] == {
        "existing_prediction_count": 7,
        "target_draw": "2026-08-26",
        "unchanged_bytes": True,
    }


def test_due_legacy_evaluations_are_descriptive_only_and_nonpromotion() -> None:
    plan = _plan()
    legacy = plan["legacy_due_prediction_cohort"]
    manifest_bytes = LEGACY_MANIFEST_PATH.read_bytes()
    manifest = json.loads(manifest_bytes)

    assert legacy == {
        "classification": "descriptive_only_nonpromotion",
        "evaluation_count": 7,
        "manifest_path": str(LEGACY_MANIFEST_PATH.relative_to(ROOT)),
        "manifest_sha256": (
            "04f115049f81fa462810a18b756e7d893633b0195705bf27d8e4e5c91d52fc02"
        ),
        "target_draw": "2026-08-26",
    }
    assert hashlib.sha256(manifest_bytes).hexdigest() == legacy["manifest_sha256"]
    assert manifest["corrected_history_claim"] is False
    assert manifest["promotion_eligible"] is False
    assert len(manifest["predictions"]) == 7

    classification = plan["expected_success"]["evaluations"]["classification"]
    assert classification == {
        "actual_history": "corrected_operational_history",
        "prediction_source": {
            "claims": {
                "corrected_history": False,
                "promotion_evidence_eligible": False,
            },
            "kind": "sealed_legacy_incident_history",
        },
    }


def test_stage1_workflow_is_manual_read_only_and_capability_scoped() -> None:
    plan = _plan()
    workflow = _workflow()
    workflow_text = LIVE_WORKFLOW_PATH.read_text(encoding="utf-8")

    assert set(workflow["on"]) == {"workflow_dispatch"}
    assert workflow["permissions"] == {"contents": "read"}
    assert plan["workflow"]["triggers"] == ["workflow_dispatch"]
    assert plan["workflow"]["permissions"] == {"contents": "read"}

    steps = workflow["jobs"]["live"]["steps"]
    checkout = steps[0]
    assert checkout["uses"] == "actions/checkout@v4"
    assert checkout["with"] == {
        "fetch-depth": "0",
        "persist-credentials": "false",
    }

    canary_step = next(
        step
        for step in steps
        if step.get("name") == "Run protected production live canary"
    )
    assert set(canary_step["env"]) == {
        "LOTTO_GITHUB_PUBLICATION_TOKEN",
        "SMTP_PASSWORD",
        "SMTP_USERNAME",
    }
    assert canary_step["env"]["LOTTO_GITHUB_PUBLICATION_TOKEN"] == (
        "${{ secrets.LOTTO_GITHUB_PUBLICATION_TOKEN }}"
    )
    assert workflow_text.count("secrets.LOTTO_GITHUB_PUBLICATION_TOKEN") == 1
    assert workflow_text.count("orchestrate_github_live_cycle(") == 1
    assert (
        "orchestrate_github_live_cycle(token=publication_token)" in (canary_step["run"])
    )
    assert ARMED_CONFIG_SHA256 in workflow_text
    not_before = datetime.fromisoformat(
        plan["execution"]["not_before"].replace("Z", "+00:00")
    )
    assert (
        "not_before = datetime("
        f"{not_before.year}, {not_before.month}, {not_before.day}, "
        f"{not_before.hour}, {not_before.minute}, tzinfo=UTC)"
    ) in workflow_text

    forbidden_commands = (
        "lotto649 live",
        "git add",
        "git commit",
        "git push",
        "git reset",
        "git merge",
        "git rebase",
    )
    assert not any(command in workflow_text for command in forbidden_commands)
    assert "retry" not in workflow_text.lower()


def test_stage1_has_no_schedule_and_stage2_requires_separate_reviewed_pr() -> None:
    plan = _plan()

    assert plan["status"] == "preregistered_not_executed"
    assert plan["stage"] == {
        "branch_state": "disconnected_until_independent_review",
        "id": "stage-1",
        "purpose": "one_manual_production_canary",
    }
    assert plan["execution"] == {
        "entrypoint": "orchestrate_github_live_cycle(*, token=...)",
        "not_before": "2026-08-27T15:15:00Z",
        "official_source_gate": {
            "authorities": ["loto_quebec", "wclc"],
            "draw_date": "2026-08-26",
            "requirement": "both_authorities_publish_and_agree",
        },
        "topology": ["B", "E", "S", "P", "A"],
    }
    assert plan["failure_policy"]["automatic_retry_after_worker_start"] is False
    assert plan["failure_policy"]["ordinary_git_push"] is False
    assert plan["failure_policy"]["forward_reseal"] == {
        "data_refresh_enabled": False,
        "live_enabled": False,
        "required": True,
        "workflow": "sealed_no_op",
    }
    assert plan["failure_policy"]["rewrite_acknowledged_commits"] is False
    assert plan["stage2"] == {
        "condition": "stage_1_canary_success_and_independent_review",
        "separate_pull_request": True,
        "unattended_schedule_in_stage_1": False,
    }
    assert plan["workflow"]["other_workflows"] == {
        "backtest.yml": "all_false_no_op",
        "integration.yml": "all_false_no_op",
    }
    assert plan["credential"]["installed"] is False
    assert plan["credential"]["workflow_scope"] == (
        "protected_production_canary_step_only"
    )
    assert plan["sanitization"] == {
        "contains_recipient_addresses": False,
        "contains_secret_values": False,
    }
