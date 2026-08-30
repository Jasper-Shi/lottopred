from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import yaml

ROOT = Path(__file__).resolve().parents[1]
BASE_HEAD = "1b74e4ed629b26bca4dceda3ec4a93cc09272479"
V1_REGISTRATION_COMMIT = "0af20fc41fc5aaa0879dada0a258797a8bc14e20"
V1_REGISTRATION_PATH = (
    "evidence/research_registrations/v12-post-rng-parity-composition-transition-v1.json"
)
V1_AUTHORIZATION_PATH = (
    "evidence/research_authorizations/"
    "v12-post-rng-parity-composition-transition-v1.json"
)
V1_LEASE_REF = "refs/heads/v12-consumption-v12.0.0"

R2_EXPERIMENT_PATH = "docs/experiments/V12_0_1_operational_rebinding.md"
R2_BASIS_PATH = "docs/research/V12_0_1_operational_rebinding_basis.md"
R2_CONFIG_PATH = "config/research-v12-0-1-post-rng-parity-composition-transition.yaml"
R2_REGISTRATION_PATH = (
    "evidence/research_registrations/v12-post-rng-parity-composition-transition-v2.json"
)
V1_CLOSURE_PATH = (
    "evidence/research_closures/"
    "v12-post-rng-parity-composition-transition-v1-"
    "superseded-unexecuted.json"
)
R2_CANARY_PLAN_PATH = (
    "evidence/release_canaries/2026-09-10-v12.0.1-production-live-canary-plan.json"
)
R2_CANARY_SUCCESS_PATH = (
    "evidence/release_canaries/stage1-r2-v12.0.1-production-live-canary-success.json"
)
R2_HISTORICAL_AUTHORIZATION_PATH = (
    "evidence/research_authorizations/"
    "v12-post-rng-parity-composition-transition-v2-historical.json"
)
R2_LIVE_AUTHORIZATION_PATH = (
    "evidence/research_authorizations/"
    "v12-post-rng-parity-composition-transition-v2-live.json"
)
R2_HISTORICAL_LEASE_REF = "refs/heads/v12-consumption-v12.0.1"
R2_LIVE_CANARY_LEASE_REF = "refs/heads/v12-live-canary-v12.0.1"

STATISTICAL_CORE_PATH = "src/lotto649/models/v12_parity_transition.py"
STATISTICAL_CORE_SHA256 = (
    "fae93e0a6f76c6604eabe24f6b93676e22e87d7e567365b382484433fba2eb77"
)
STATISTICAL_FINGERPRINT_SHA256 = (
    "af2e16a55ff0e817cf71208471e19e4f481bed63990f7e41268997c4c4b35c76"
)
V1_REGISTRATION_SHA256 = (
    "4406bd25ee82195bff7a97b258885cb3bb3c1a8fb829f383c5e3c1616e169170"
)
SECTION_HASHES = {
    "control_null_contract": (
        "f050c82f101a17f5126a8a8db61c7f484d83e605f27213b6803306d74fab2d8c"
    ),
    "controls": ("cf590452b19f1dfbae0f0fbd2b1db3ce47b290c0011b2889413bdca529f271e0"),
    "gates": "d64633c7179128d0fce76f37ead0f5740ef13e725a941794102ddc0fa00f2396",
    "historical_governance": (
        "d33abcabd1bfa7548f8eab680d4efab864f52b271e111cab7212a1f0245366fc"
    ),
    "historical_scope": (
        "7106f906239761694647b3f60f2ce8c5855d5b61ef8e74539b262aacf0a03a65"
    ),
    "mathematical_contract": (
        "6c2391fa3d58ea1161af90282028e28d787ce52de38cb03e43366d89cf7ed832"
    ),
    "model": "2a97e0a6e18860c31027828302fb9230ab44bfa1b3a846663fc84c1483d66b7f",
    "multiplicity": (
        "d0ce22e9e36441d9d497af56c1675f98ee618d83ea1a146a7851a7c8c5e57997"
    ),
    "notifications": (
        "bb1bd1de4219d90b931b3789c33d1df4fdab36d22fb7d0ac4a2becc4eab33af2"
    ),
    "target_date_identities": (
        "1264cd4fc34cd33bdfdcabba79be6efe3a6902068a17b9ed61d9ee667baccf77"
    ),
}
RUNTIME_LOCK_SHA256 = "a0dfeac17ad7e1c41dffe4b41b4810156fb028f879d312430bfc517672a570c6"

R2_IMPLEMENTATION_PATHS = (
    STATISTICAL_CORE_PATH,
    "src/lotto649/v12_0_1_evidence.py",
    "src/lotto649/v12_0_1_registered_attempt.py",
    "tools/run_v12_0_1_historical.py",
    "tests/test_v12_0_1_parity_transition.py",
    "tests/test_v12_0_1_registered_attempt.py",
)

R2_DOCUMENTATION_SYNC_PATHS = (
    "AGENTS.md",
    "docs/ARCHITECTURE.md",
    "docs/CODEX_HANDOFF.md",
    "docs/MODEL_PROTOCOL.md",
    "docs/OPERATIONS.md",
    "docs/RESEARCH_ROADMAP.md",
)
R2_DOCUMENTATION_SYNC_SHA256 = {
    "AGENTS.md": ("332bb70be33d3d02c1b3d534d0c494024dd845b1ce0f4f0cf05e3a43f7e6bfe7"),
    "docs/ARCHITECTURE.md": (
        "ae92bf302bc76814b09c8e91b5ff9e7e8e2bb0909feda31eaaa451c54233c691"
    ),
    "docs/CODEX_HANDOFF.md": (
        "1e0ed362b2c555fe1e5c9f58b203809dde6cfe5928fc9a1b0b3cc85e73d861ca"
    ),
    "docs/MODEL_PROTOCOL.md": (
        "5c6f48af7291b37cb742451a0ed69a2638a9aa0d4b86dbcd6e5f4bb74d9e9b0f"
    ),
    "docs/OPERATIONS.md": (
        "b9ab3b8b2cc98fab82e62c27e6a7e72f5bdec417a5c4f43c7795aeb718da7661"
    ),
    "docs/RESEARCH_ROADMAP.md": (
        "f6578ad3a05b92a1d1a1e2b47cd91292a4a61836a26e479866dddd0c214e531a"
    ),
}

R2_CONFIG_YAML_SHA256 = (
    "d53a9a9eed5ab434b021472135d6aed65c2c052339e0dfb88f8c00d46c0d8931"
)


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _load_json(relative_path: str) -> dict[str, Any]:
    return json.loads((ROOT / relative_path).read_bytes())


def _load_yaml(relative_path: str) -> dict[str, Any]:
    value = yaml.safe_load((ROOT / relative_path).read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _git(*arguments: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ("git", *arguments),
        cwd=ROOT,
        check=False,
        capture_output=True,
    )


def _r2_authority_commit() -> str | None:
    result = _git(
        "log",
        "--reverse",
        "--format=%H",
        "--diff-filter=A",
        "--",
        R2_REGISTRATION_PATH,
    )
    assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
    commits = tuple(line for line in result.stdout.decode("ascii").splitlines() if line)
    assert len(commits) <= 1
    return commits[0] if commits else None


def _bytes_at_r2_authority(relative_path: str) -> bytes:
    authority_commit = _r2_authority_commit()
    if authority_commit is None:
        return (ROOT / relative_path).read_bytes()
    result = _git("show", f"{authority_commit}:{relative_path}")
    assert result.returncode == 0, relative_path
    return result.stdout


def _path_exists_at_r2_authority(relative_path: str) -> bool:
    authority_commit = _r2_authority_commit()
    if authority_commit is None:
        return (ROOT / relative_path).exists()
    return _git("cat-file", "-e", f"{authority_commit}:{relative_path}").returncode == 0


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    assert parsed.tzinfo is not None
    assert parsed.utcoffset() == timedelta(0)
    return parsed.astimezone(UTC)


def _freeze_precedes_deadline(*, freeze_time: datetime, deadline: datetime) -> bool:
    return freeze_time < deadline


def test_r2_registration_artifacts_exist_and_machine_seals_are_canonical() -> None:
    required = (
        R2_EXPERIMENT_PATH,
        R2_BASIS_PATH,
        R2_CONFIG_PATH,
        R2_REGISTRATION_PATH,
        V1_CLOSURE_PATH,
        R2_CANARY_PLAN_PATH,
    )
    for relative_path in required:
        assert (ROOT / relative_path).is_file(), relative_path

    for relative_path in (R2_REGISTRATION_PATH, V1_CLOSURE_PATH):
        raw = (ROOT / relative_path).read_bytes()
        assert raw == _canonical_json(json.loads(raw)) + b"\n"


def test_v12_0_0_is_closed_only_as_superseded_unexecuted() -> None:
    closure = _load_json(V1_CLOSURE_PATH)

    assert closure == {
        "base_head": BASE_HEAD,
        "closure_reason": "fixed_forward_canary_window_expired",
        "experiment_id": "V12_post_rng_parity_composition_transition",
        "forbidden_dispositions": ["Archive", "Reject", "consumed"],
        "model_version": "v12.0.0",
        "old_authorization_path": V1_AUTHORIZATION_PATH,
        "old_lease_ref": V1_LEASE_REF,
        "registration_commit": V1_REGISTRATION_COMMIT,
        "registration_path": V1_REGISTRATION_PATH,
        "remote_absence_claim": "not_made_offline",
        "replacement_model_version": "v12.0.1",
        "schema_version": "lotto649-research-registration-closure-v1",
        "scientific_disposition": None,
        "status": "superseded_unexecuted",
    }
    assert not (ROOT / V1_AUTHORIZATION_PATH).exists()


def test_r2_statistical_fingerprint_is_exactly_v1_plus_the_frozen_core() -> None:
    v1_raw = (ROOT / V1_REGISTRATION_PATH).read_bytes()
    v1 = json.loads(v1_raw)
    r2 = _load_json(R2_REGISTRATION_PATH)
    equivalence = r2["statistical_equivalence"]

    assert hashlib.sha256(v1_raw).hexdigest() == V1_REGISTRATION_SHA256
    assert equivalence["source"] == {
        "model_version": "v12.0.0",
        "registration_commit": V1_REGISTRATION_COMMIT,
        "registration_path": V1_REGISTRATION_PATH,
        "registration_sha256": V1_REGISTRATION_SHA256,
    }
    assert equivalence["classification"] == "operational_rebinding_only"
    assert equivalence["statistical_behavior_changed"] is False

    payload = equivalence["fingerprint_payload"]
    assert payload == {
        "contract_sections": SECTION_HASHES,
        "core": {
            "path": STATISTICAL_CORE_PATH,
            "sha256": STATISTICAL_CORE_SHA256,
        },
        "gate_count": 10,
        "half_target_counts": [314, 313],
        "historical_target_count": 627,
        "hypothesis_id": "H12",
        "primary_metric": "mean_top12_main_number_hits_minus_72_over_49",
        "seed": 649,
    }
    for section, expected_hash in SECTION_HASHES.items():
        assert hashlib.sha256(_canonical_json(v1[section])).hexdigest() == expected_hash
    assert hashlib.sha256(_canonical_json(payload)).hexdigest() == (
        STATISTICAL_FINGERPRINT_SHA256
    )
    assert equivalence["fingerprint_sha256"] == STATISTICAL_FINGERPRINT_SHA256


def test_r2_has_new_registration_authorization_lease_report_and_canary_ids() -> None:
    r2 = _load_json(R2_REGISTRATION_PATH)
    config = _load_yaml(R2_CONFIG_PATH)

    assert r2["model_version"] == "v12.0.1"
    assert r2["registration_path"] == R2_REGISTRATION_PATH
    assert r2["execution_authorizations"] == {
        "historical": {
            "path": R2_HISTORICAL_AUTHORIZATION_PATH,
            "state_at_R2": "absent",
        },
        "live": {
            "path": R2_LIVE_AUTHORIZATION_PATH,
            "state_at_R2": "absent",
        },
    }
    assert r2["repository_global_attempt_lease"]["ref"] == (R2_HISTORICAL_LEASE_REF)
    assert r2["live_canary_lease"]["ref"] == R2_LIVE_CANARY_LEASE_REF
    assert r2["production_canary_prerequisite"]["plan_path"] == (R2_CANARY_PLAN_PATH)
    assert r2["production_canary_prerequisite"]["success_path"] == (
        R2_CANARY_SUCCESS_PATH
    )
    assert r2["artifact_paths"] == config["artifact_paths"]
    assert len(r2["artifact_paths"]) == 8
    assert all("v12.0.1" in path for path in r2["artifact_paths"].values())
    assert all("v12.0.0" not in path for path in r2["artifact_paths"].values())
    assert r2["canonical_command"] == [
        "python3.12",
        "tools/run_v12_0_1_historical.py",
        "--consume-v12-0-1-once",
    ]


def test_r2_precedes_i2_and_every_execution_path_is_absent_and_closed() -> None:
    r2 = _load_json(R2_REGISTRATION_PATH)
    config = _load_yaml(R2_CONFIG_PATH)

    assert r2["status"] == {
        "automatic_execution": "prohibited",
        "historical_scoring": "not_scored",
        "implementation": "not_implemented",
        "prospective": "not_activated",
        "registration": "registered",
        "research_execution": "not_authorized",
    }
    phase = r2["phase_contract"]
    assert phase["at_R2"] == "all_execution_fail_closed"
    assert phase["shared_order"] == "R2 < I2"
    assert phase["historical_lane"] == {
        "authorization": "A_H2_absent",
        "excluded_live_prerequisites": [
            "D0",
            "W2",
            "S2",
            "C2",
            "M_C2",
            "K_L2",
            "A_L2",
        ],
        "required_order": "R2 < I2 < K_H2 < A_H_s2 < M_A_H2 < L_H2 < run_H2",
    }
    assert phase["live_lane"] == {
        "authorization": "A_L2_absent",
        "partial_order": [
            "R2 < D0",
            "R2 < I2",
            "D0 < W2",
            "I2 < W2",
            "W2 < S2 < C2 < M_C2 < K_L2 < A_L_s2 < M_A_L2",
        ],
        "production_wiring": "W2_absent",
    }
    assert config["phase_contract"] == phase
    assert r2["expected_implementation_paths"] == list(R2_IMPLEMENTATION_PATHS)
    assert config["execution"]["pre_authorization"] == "prohibited"
    assert config["execution"]["automatic"] is False


def test_r2_git_authority_proves_registration_time_absence_and_config_hash() -> None:
    r2 = _load_json(R2_REGISTRATION_PATH)
    authority = r2["r2_git_authority"]
    absent_paths = (
        *R2_IMPLEMENTATION_PATHS,
        R2_HISTORICAL_AUTHORIZATION_PATH,
        R2_LIVE_AUTHORIZATION_PATH,
        R2_CANARY_SUCCESS_PATH,
    )

    assert authority == {
        "binding_state": "binds_on_first_normal_commit_adding_registration",
        "commit_resolution": {
            "algorithm": "first_ancestor_commit_adding_exact_registration_path",
            "registration_path": R2_REGISTRATION_PATH,
        },
        "registration_blob_equality_after_binding": "required",
        "self_reference": "prohibited",
        "tree_assertions": {
            "absent_paths": list(absent_paths),
            "config_yaml_sha256": R2_CONFIG_YAML_SHA256,
            "registered_files_binding": (
                "exact_paths_bytes_and_sha256_in_R2_authority_tree"
            ),
        },
    }
    authority_commit = _r2_authority_commit()
    if authority_commit is not None:
        assert (
            _bytes_at_r2_authority(R2_REGISTRATION_PATH)
            == (ROOT / R2_REGISTRATION_PATH).read_bytes()
        )
    for relative_path in absent_paths:
        assert not _path_exists_at_r2_authority(relative_path), relative_path
    assert hashlib.sha256(_bytes_at_r2_authority("config.yaml")).hexdigest() == (
        R2_CONFIG_YAML_SHA256
    )


def test_old_stage1_reseal_is_a_separate_all_false_phase() -> None:
    r2 = _load_json(R2_REGISTRATION_PATH)
    plan = _load_json(R2_CANARY_PLAN_PATH)
    reseal = r2["old_stage1_reseal_prerequisite"]

    assert reseal == plan["prerequisites"]["old_stage1_reseal_D0"]
    assert _load_yaml(R2_CONFIG_PATH)["old_stage1_reseal_prerequisite"] == reseal
    assert reseal["state"] == "required_separate_unimplemented"
    assert reseal["changes_in_r2"] == []
    assert reseal["required_runtime_outputs"] == {
        "backtest": False,
        "integration": False,
        "live": False,
    }
    assert reseal["must_precede"] == "W2_and_any_live_recovery_dispatch"


def test_fixed_forward_canary_is_sep9_to_sep12_and_never_slides() -> None:
    r2 = _load_json(R2_REGISTRATION_PATH)
    config = _load_yaml(R2_CONFIG_PATH)
    plan = _load_json(R2_CANARY_PLAN_PATH)
    execution = plan["execution"]
    expiry = plan["expiry"]

    assert date.fromisoformat(execution["canary_draw"]).weekday() == 2
    assert date.fromisoformat(execution["next_prediction_target"]).weekday() == 5
    assert execution == {
        "canary_draw": "2026-09-09",
        "dispatch_not_after": "2026-09-11T15:15:00Z",
        "dispatch_not_before": "2026-09-10T15:15:00Z",
        "entrypoint": "future_complete_I2_production_wiring_only",
        "next_prediction_target": "2026-09-12",
        "official_source_gate": {
            "authorities": ["loto_quebec", "wclc"],
            "draw_date": "2026-09-09",
            "requirement": "both_authorities_publish_and_agree",
        },
        "seed_prediction_freeze": {
            "comparison": "freeze_time_utc_strictly_less_than_deadline_utc",
            "deadline_exclusive": True,
            "deadline_utc": "2026-09-09T04:00:00Z",
            "target_day_timezone": "America/Toronto",
            "target_local_day": "2026-09-09",
        },
        "topology": ["B", "E", "S", "P", "A"],
    }
    assert expiry == {
        "automatic_status": "superseded_unexecuted",
        "date_roll_forward": "prohibited",
        "dispatch_after_window": "prohibited",
        "historical_lane_effect": "none",
        "new_registration_and_version_required": True,
        "trigger_if_seed_deadline_missed": True,
        "trigger_if_dispatch_window_missed": True,
        "seed_deadline_miss_predicate": (
            "freeze_time_utc_greater_than_or_equal_to_deadline_utc"
        ),
        "status_scope": "V12.0.1_live_lane_only",
    }
    assert plan["failure_policy"]["automatic_retry"] is False
    prerequisite = r2["production_canary_prerequisite"]
    assert config["production_canary_prerequisite"] == prerequisite
    assert prerequisite["seed_prediction_freeze"] == execution["seed_prediction_freeze"]
    assert prerequisite["fixed_canary_draw"] == execution["canary_draw"]
    assert (
        prerequisite["fixed_next_prediction_target"]
        == execution["next_prediction_target"]
    )
    assert prerequisite["date_roll_forward"] == expiry["date_roll_forward"]


def test_seed_deadline_is_exclusive_start_of_target_day_in_toronto() -> None:
    plan = _load_json(R2_CANARY_PLAN_PATH)
    freeze = plan["execution"]["seed_prediction_freeze"]
    target = date.fromisoformat(plan["execution"]["canary_draw"])
    toronto = ZoneInfo(freeze["target_day_timezone"])
    deadline = _parse_utc(freeze["deadline_utc"])
    target_day_start = datetime.combine(target, time.min, tzinfo=toronto)
    last_valid_whole_second = deadline - timedelta(seconds=1)

    assert freeze["deadline_exclusive"] is True
    assert deadline == target_day_start.astimezone(UTC)
    assert _freeze_precedes_deadline(
        freeze_time=last_valid_whole_second,
        deadline=deadline,
    )
    assert last_valid_whole_second.astimezone(toronto).date() < target
    assert not _freeze_precedes_deadline(freeze_time=deadline, deadline=deadline)
    assert deadline.astimezone(toronto).date() == target


def test_future_production_wiring_requires_complete_i2_and_is_not_permanently_closed() -> (
    None
):
    r2 = _load_json(R2_REGISTRATION_PATH)
    plan = _load_json(R2_CANARY_PLAN_PATH)
    wiring = plan["production_wiring_W2"]

    assert wiring == r2["production_wiring_contract"]
    assert _load_yaml(R2_CONFIG_PATH)["production_wiring_contract"] == wiring
    assert wiring["absent_at_R2"] is True
    assert wiring["complete_reviewed_I2_required"] is True
    assert wiring["may_be_armed_after_I2"] is True
    assert wiring["permanent_fail_closed"] is False
    assert wiring["runtime_dependency_closure_freezes_at"] == "W2"
    assert wiring["closure_equality_checkpoints"] == [
        "W2",
        "K_L2",
        "A_L_s2",
        "M_A_L2",
    ]
    assert wiring["W2_may_fill_only_digest_bindings"] == [
        "reviewed_protected_main_commit_sha",
        "config_git_blob_oid",
        "config_sha256",
        "workflow_git_blob_oid",
        "workflow_sha256",
        "live_runtime_dependency_closure_sha256",
    ]
    assert wiring["non_digest_W2_fields"] == "prohibited"


def test_historical_authorization_is_independent_of_live_canary() -> None:
    r2 = _load_json(R2_REGISTRATION_PATH)
    config = _load_yaml(R2_CONFIG_PATH)
    historical = r2["historical_authorization_contract"]

    assert historical == {
        "authorization": "A_H2",
        "authorization_prerequisites": [
            "registered_R2_authority",
            "complete_independently_reviewed_I2",
            "protected_remote_main_K_H2",
            "fixed_governed_history_authority",
            "historical_runtime_dependency_closure_frozen_at_I2",
        ],
        "excluded_prerequisites": [
            "D0",
            "W2",
            "S2",
            "C2",
            "M_C2",
            "K_L2",
            "A_L2",
            "future_draw_outcome",
            "live_canary_success",
        ],
        "one_shot_execution_prerequisites": [
            "normal_M_A_H2_at_protected_remote_main_HEAD",
            "fresh_exact_v12.0.1_historical_lease",
        ],
    }
    assert r2["historical_runtime_dependency_closure"] == {
        "equality_checkpoints": ["I2", "K_H2", "A_H_s2", "M_A_H2"],
        "freezes_at": "I2",
        "state_at_R2": "absent_until_complete_I2",
    }
    assert config["historical_authorization_contract"] == historical


def test_live_authorization_has_its_own_complete_forward_chain() -> None:
    r2 = _load_json(R2_REGISTRATION_PATH)
    config = _load_yaml(R2_CONFIG_PATH)
    live = r2["live_authorization_contract"]

    assert live == {
        "activation_authority": "normal_M_A_L2_at_protected_remote_main_HEAD",
        "authorization": "A_L2",
        "authorization_prerequisites": [
            "registered_R2_authority",
            "complete_independently_reviewed_I2",
            "old_stage1_all_false_reseal_D0",
            "complete_W2_digest_bindings",
            "timely_immutable_pre_draw_S2",
            "fresh_exact_v12.0.1_live_canary_lease_before_C2",
            "successful_one_shot_C2",
            "normal_self_reference_free_M_C2",
            "protected_remote_main_K_L2",
            "live_runtime_dependency_closure_frozen_at_W2",
        ],
    }
    assert config["live_authorization_contract"] == live


def test_live_dispatch_identity_is_frozen_at_r2_and_manual_only() -> None:
    r2 = _load_json(R2_REGISTRATION_PATH)
    config = _load_yaml(R2_CONFIG_PATH)
    plan = _load_json(R2_CANARY_PLAN_PATH)
    expected = {
        "automatic_retry": False,
        "branch": "main",
        "event": "workflow_dispatch",
        "manual_only": True,
        "repository": "Jasper-Shi/lottopred",
        "schedule": "prohibited",
        "workflow": ".github/workflows/live.yml",
    }

    assert plan["live_dispatch_identity"] == expected
    assert r2["live_dispatch_identity"] == expected
    assert config["live_dispatch_identity"] == expected


def test_registration_schema_and_status_are_formal_not_draft() -> None:
    r2 = _load_json(R2_REGISTRATION_PATH)
    experiment = (ROOT / R2_EXPERIMENT_PATH).read_text(encoding="utf-8")
    basis = (ROOT / R2_BASIS_PATH).read_text(encoding="utf-8")

    assert r2["schema_version"] == "lotto649-research-registration-v2"
    assert r2["status"]["registration"] == "registered"
    assert "R2 DRAFT" not in experiment.upper()
    assert "R2 DRAFT" not in basis.upper()


def test_repository_documentation_sync_is_required_before_r2_authority_commit() -> None:
    r2 = _load_json(R2_REGISTRATION_PATH)
    config = _load_yaml(R2_CONFIG_PATH)

    assert r2["repository_documentation_sync"] == {
        "binding": "exact_bytes_in_R2_git_authority_tree",
        "must_complete_before": "R2_authority_commit",
        "paths": list(R2_DOCUMENTATION_SYNC_PATHS),
        "sha256": R2_DOCUMENTATION_SYNC_SHA256,
        "state": "completed_by_external_owner_and_sealed_at_R2",
    }
    assert (
        config["repository_documentation_sync"] == (r2["repository_documentation_sync"])
    )
    for relative_path, expected_hash in R2_DOCUMENTATION_SYNC_SHA256.items():
        assert hashlib.sha256(_bytes_at_r2_authority(relative_path)).hexdigest() == (
            expected_hash
        )


def test_r2_seal_binds_only_outcome_blind_registered_files() -> None:
    r2 = _load_json(R2_REGISTRATION_PATH)
    expected = (
        R2_BASIS_PATH,
        R2_EXPERIMENT_PATH,
        R2_CONFIG_PATH,
        *R2_DOCUMENTATION_SYNC_PATHS,
        V1_CLOSURE_PATH,
        R2_CANARY_PLAN_PATH,
        "requirements/v12-historical.txt",
    )

    assert list(r2["registered_files"]) == sorted(expected)
    for relative_path in expected:
        raw = _bytes_at_r2_authority(relative_path)
        assert r2["registered_files"][relative_path] == {
            "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        }
    assert r2["runtime"]["dependency_manifest_sha256"] == RUNTIME_LOCK_SHA256
    assert r2["outcome_blindness"] == {
        "canonical_attempt_instantiated": False,
        "implementation_review_inputs": "synthetic_fixtures_and_closed_form_oracles_only",
        "live_or_canonical_worker_run": False,
        "real_2020_2025_outcomes_read": False,
        "real_2026_outcomes_read": False,
        "statistical_change_after_outcome_access": "prohibited",
    }
