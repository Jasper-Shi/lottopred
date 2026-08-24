from __future__ import annotations

import csv
import io
import json
import subprocess
from datetime import date, timedelta
from hashlib import sha256
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT_ID = "V12_post_rng_parity_composition_transition"
MODEL_VERSION = "v12.0.0"
MAIN_AUTHORITY_COMMIT = "4a617f2c1575a165b42878600753a01ddf2ced03"

BASIS_PATH = "docs/research/V12_post_rng_parity_composition_transition_basis.md"
EXPERIMENT_PATH = "docs/experiments/V12_post_rng_parity_composition_transition.md"
CONFIG_PATH = "config/research-v12-post-rng-parity-composition-transition.yaml"
RUNTIME_LOCK_PATH = "requirements/v12-historical.txt"
REGISTRATION_PATH = (
    "evidence/research_registrations/v12-post-rng-parity-composition-transition-v1.json"
)
AUTHORIZATION_PATH = (
    "evidence/research_authorizations/"
    "v12-post-rng-parity-composition-transition-v1.json"
)
CANARY_PLAN_PATH = (
    "evidence/release_canaries/2026-08-27-production-live-canary-plan.json"
)
CANARY_SUCCESS_PATH = (
    "evidence/release_canaries/stage1-production-live-canary-success.json"
)
AUTHORIZATION_SUMMARY_PATHS = (
    "docs/CODEX_HANDOFF.md",
    "docs/MODEL_PROTOCOL.md",
    "docs/RESEARCH_ROADMAP.md",
)
AUTHORIZATION_SUMMARY_SENTENCE = (
    "Only normal merge `M_A` at protected remote `main`/HEAD executes; "
    "`A_s` is non-authoritative."
)
GLOBAL_ATTEMPT_LEASE_REF = "refs/heads/v12-consumption-v12.0.0"

REGISTERED_FILES = (
    BASIS_PATH,
    EXPERIMENT_PATH,
    CONFIG_PATH,
    RUNTIME_LOCK_PATH,
)
IMPLEMENTATION_PATHS = (
    "src/lotto649/models/v12_parity_transition.py",
    "src/lotto649/v12_evidence.py",
    "src/lotto649/v12_registered_attempt.py",
    "tools/run_v12_historical.py",
    "tests/test_v12_parity_transition.py",
    "tests/test_v12_registered_attempt.py",
)
ARTIFACT_PATHS = {
    "historical_claim": (
        "reports/v12_post_rng_parity_composition_transition_v12.0.0_historical.claim"
    ),
    "historical_attempt_ledger": (
        "reports/v12_post_rng_parity_composition_transition_"
        "v12.0.0_historical.ledger.jsonl"
    ),
    "historical_report_json": (
        "reports/v12_post_rng_parity_composition_transition_v12.0.0_historical.json"
    ),
    "historical_report_markdown": (
        "reports/v12_post_rng_parity_composition_transition_v12.0.0_historical.md"
    ),
    "historical_report_json_staging": (
        "reports/v12_post_rng_parity_composition_transition_"
        "v12.0.0_historical.json.staging"
    ),
    "historical_report_markdown_staging": (
        "reports/v12_post_rng_parity_composition_transition_"
        "v12.0.0_historical.md.staging"
    ),
}

CANONICAL_COMMAND = [
    "python3.12",
    "tools/run_v12_historical.py",
    "--consume-v12-once",
]

PSEUDO_PARITY_SET = [
    1,
    2,
    5,
    6,
    7,
    8,
    9,
    10,
    12,
    16,
    17,
    18,
    20,
    24,
    28,
    29,
    32,
    33,
    40,
    41,
    42,
    43,
    44,
    48,
    49,
]

SCIENTIFIC_GATES = [
    "aggregate_candidate_top12_lift_strictly_positive",
    ("aggregate_candidate_four_variant_holm_adjusted_exact_p_at_most_0.05"),
    "aggregate_candidate_top12_bootstrap_lower_strictly_positive",
    "candidate_top12_lift_strictly_positive_in_both_halves",
    (
        "paired_candidate_minus_v1_top12_bootstrap_lower_strictly_"
        "positive_aggregate_and_halves"
    ),
    (
        "candidate_minus_pseudo_top12_bootstrap_lower_strictly_positive_and_"
        "pseudo_and_random_each_exact_fair_top12_p_strictly_above_0.05_and_"
        "fixed_seed_bootstrap_top12_lift_interval_includes_zero_in_every_scope"
    ),
    "candidate_top6_lift_strictly_positive_aggregate_and_halves",
    (
        "candidate_brier_and_log_loss_deltas_vs_fair_and_v1_at_most_"
        "1e-9_aggregate_and_halves"
    ),
    (
        "joint_law_candidate_log_gain_at_least_log20_aggregate_positive_"
        "halves_candidate_minus_control_positive_all_scopes_control_"
        "below_log20"
    ),
    "no_audit_warning",
]

HISTORICAL_GOVERNANCE = {
    "evidence_classification": "consumed_historical_diagnostic_only",
    "eligible_evidence": "prohibited",
    "exact_final6": {
        "attempt_action": "stop_current_attempt_pending_audit",
        "global_research_action": "continue",
        "global_stop_search": "prohibited",
        "notification_action": "send_once_after_durable_detection",
        "notification_classification_zh": "历史诊断/审计候选、不可晋升",
        "success_language": "prohibited",
    },
    "global_historical_oos_ledger_write": "prohibited",
    "opportunity_ledger": "v12_local_attempt_ledger_only",
    "promotion_from_historical_lane": "prohibited",
    "top12": {
        "attempt_action": "continue",
        "global_stop_search": "prohibited",
        "notification_action": "send_once_after_durable_detection",
        "notification_classification_zh": "历史诊断/审计候选、不可晋升",
        "success_language": "prohibited",
    },
}

CONTROL_NULL_CONTRACT = {
    "candidate_minus_pseudo": {
        "bootstrap": "fixed_seed_649_10000_two_sided_95_linear_percentile",
        "metric": "paired_top12_hit_difference",
        "requirement": "lower_endpoint_strictly_positive_in_every_scope",
    },
    "control_models": [
        "v12_pseudo_parity_composition_transition_control",
        "random_v1.0.0",
    ],
    "each_control": {
        "bootstrap": "fixed_seed_649_10000_two_sided_95_linear_percentile",
        "bootstrap_top12_lift_requirement": "interval_includes_zero",
        "conjunction": "exact_p_and_bootstrap_both_required",
        "exact_one_sided_fair_top12_p_requirement": "strictly_greater_than_0.05",
    },
    "no_control_or_scope_selection": True,
    "scopes": ["aggregate", "first_half", "second_half"],
}

TARGET_DATE_ENCODING = {
    "charset": "UTF-8",
    "line_record": "one_canonical_YYYY-MM-DD_date",
    "line_terminator": "LF",
    "trailing_line_terminator": True,
}

PRODUCTION_CANARY_PREREQUISITE = {
    "acceptance": {
        "authorization_topology": {
            "authorization_base_K": (
                "exact_protected_main_commit_containing_I_merge_and_C"
            ),
            "authorization_merge_M_A": {
                "first_parent": "K",
                "second_parent": "A_s",
                "tree": "identical_to_A_s",
            },
            "authorization_source_A_s": {
                "diff_from_K": "execution_authorization_json_only",
                "sole_parent": "K",
            },
            "canary_success_C": "strict_ancestor_of_K_and_M_A",
            "implementation_I_merge": "strict_ancestor_of_K_and_M_A",
            "registration_R": "strict_ancestor_of_I",
            "relative_order_I_and_C": "unconstrained",
        },
        "evidence_binding_in_authorization_json": (
            "commit_path_blob_bytes_sha256_required"
        ),
        "evidence_commit_relation": (
            "C_strict_ancestor_of_M_A_and_reachable_from_protected_remote_main"
        ),
        "historical_execution": "prohibited_until_valid_completed_evidence",
        "runner_authority": {
            "branch": "main",
            "head": "M_A",
            "repository": "Jasper-Shi/lottopred",
        },
        "v12_authorization_seal_minting": ("prohibited_until_valid_completed_evidence"),
    },
    "caller_bypass": {
        "cli_or_environment_override": "prohibited",
        "evidence_path_override": "prohibited",
        "receipt_injection": "prohibited",
        "verification_source": (
            "fixed_path_at_C_in_M_A_ancestry_and_protected_remote_main"
        ),
    },
    "evidence_path": CANARY_SUCCESS_PATH,
    "evidence_schema": "lotto649.production-live-canary-success.v1",
    "registration_observation": "absent_not_run",
    "required_bindings": {
        "plan": {
            "authority_commit": MAIN_AUTHORITY_COMMIT,
            "bytes": 7084,
            "git_blob": "88ef58825a5ff4a22c82d7db23a3572557ec672c",
            "path": CANARY_PLAN_PATH,
            "sha256": (
                "16fac454983b714733dcee3996812ae5e0415c27303176aaefdd9cb3ac7feea4"
            ),
        },
        "protected_main_receipt": {
            "allow_deletions": False,
            "allow_force_pushes": False,
            "enforce_admins": True,
            "observed_after_successful_run": True,
            "required": True,
        },
        "publication_and_authoritative_reload_receipts": {
            "authoritative_reload_A": "required",
            "fresh_full_history_reload": True,
            "history_draw_count": 4445,
            "history_through": "2026-08-26",
            "publication_P": "required",
            "receipt_digests": "required",
            "topology": "P -> A",
        },
        "reviewed_main_sha": {
            "binding": "expected_sha_equals_workflow_head_sha_equals_checkout_head",
            "branch": "main",
            "format": "lowercase_40_hex_sha1",
            "repository": "Jasper-Shi/lottopred",
            "source": "post_merge_independent_review",
        },
        "workflow_run": {
            "conclusion": "success",
            "event": "workflow_dispatch",
            "path": ".github/workflows/live.yml",
            "repository": "Jasper-Shi/lottopred",
            "run_id": "positive_integer",
        },
    },
}

REPOSITORY_GLOBAL_ATTEMPT_LEASE = {
    "absence_precondition": {
        "accepted_observation": "exact_GitHub_404_for_literal_ref",
        "always_fresh_reread": True,
        "must_precede": [
            "local_claim",
            "governed_history_load",
            "forecast",
            "outcome_access",
        ],
        "ref": GLOBAL_ATTEMPT_LEASE_REF,
        "ref_resolution": "literal_exact_ref_only",
        "refuse_observations": [
            "preexisting_ref",
            "ref_target_other_than_exact_L",
            "unreadable",
            "ambiguous_absence",
            "transport_or_auth_failure",
        ],
    },
    "attempt_limit": 1,
    "caller_bypass": "prohibited",
    "grant": {
        "post_create_fresh_reread": "required",
        "required_observation": "literal_ref_targets_exact_L",
        "sole_grant": "successful_single_createRef_and_exact_reread",
    },
    "immutable_ref": {
        "delete": "prohibited",
        "update": "prohibited",
    },
    "lease_commit_L": {
        "commit_metadata": {
            "author": {
                "email": "lotto649-v12-lease@users.noreply.github.com",
                "name": "LOTTO649 V12 Consumption Lease",
            },
            "committer": {
                "email": "lotto649-v12-lease@users.noreply.github.com",
                "name": "LOTTO649 V12 Consumption Lease",
            },
            "headers": {
                "allowed_exact_order": ["tree", "parent", "author", "committer"],
                "extra": "prohibited",
                "signature": "prohibited",
            },
            "message": {
                "additional_bytes": "prohibited",
                "raw_bytes": "canonical_body_exactly",
                "trailing_LF_count": 1,
            },
            "object_format": "sha1",
            "timestamp": {
                "author_equals_committer": True,
                "precision": "whole_seconds",
                "source": "exact_M_A_committer_timestamp",
                "timezone": "+0000",
            },
        },
        "canonical_body": {
            "encoding": "canonical_JSON_UTF-8_with_trailing_LF",
            "exact_keys": [
                "authorization_seal_sha256",
                "canonical_command",
                "execution_authority_M_A",
                "nonce_hex",
                "schema_version",
            ],
            "schema_version": "lotto649-v12-consumption-lease-v1",
        },
        "nonce": {
            "encoding": "lowercase_hex_64_characters",
            "freshness": "new_for_the_single_attempt_never_reused",
            "source": "cryptographic_OS_random_32_bytes",
        },
        "sole_parent": "M_A",
        "tree": "identical_to_M_A",
    },
    "local_artifact_bindings": {
        "historical_claim": ["lease_ref", "lease_commit_L", "nonce_hex"],
        "ledger_events": ["lease_ref", "lease_commit_L", "nonce_hex"],
    },
    "publication": {
        "automatic_retry": False,
        "commit_upload": "GitHub_git_commits_create_exact_L_before_createRef",
        "create_commit_returned_sha": "must_equal_locally_computed_L",
        "createRef_attempts": 1,
        "GET_L_before_createRef": "required_exact_commit_object_verification",
        "mismatch_action": (
            "stop_before_createRef_local_claim_history_load_forecast_outcome_access"
        ),
        "operation": "GitHub_git_refs_createRef",
        "ref": GLOBAL_ATTEMPT_LEASE_REF,
        "required_target": "exact_L",
    },
    "ref": GLOBAL_ATTEMPT_LEASE_REF,
    "repository": "Jasper-Shi/lottopred",
    "scope": "repository_global_not_local_O_EXCL",
}

CANARY_INTEGRATION_EVIDENCE_CONTRACT = {
    "independent_review_comments": {
        "independence": "reviewer_not_C_author_or_canary_workflow_actor",
        "per_axis_record": {
            "axis": "exact_required_axis",
            "body_sha256": "lowercase_64_hex",
            "comment_id": "positive_integer_immutable",
            "reviewed_head": "equals_pull_request_head_sha",
            "verdict": "pass",
        },
        "required_axes": ["Standards", "Spec"],
    },
    "pull_request": {
        "base_ref": "main",
        "base_sha": "canonical_lowercase_40_hex",
        "head_sha": "canonical_lowercase_40_hex",
        "merge_sha": "equals_C",
        "number": "positive_integer",
        "state": "merged",
    },
    "required_check": {
        "app": "github-actions",
        "conclusion": "success",
        "head": "equals_pull_request_head_sha",
        "name": "test",
        "run_id": "positive_integer",
    },
    "self_attestation": "prohibited",
}

K_ALLOWED_STATIC_PATHS = [
    "data/processed/epochs/DI-2026-08-20-registered-history/live_draws.jsonl",
    "evaluations/2026-08-26__ema_gap__v1.0.0.json",
    "evaluations/2026-08-26__ensemble__v1.0.0.json",
    "evaluations/2026-08-26__logistic__v1.0.0.json",
    "evaluations/2026-08-26__long_frequency__v1.0.0.json",
    "evaluations/2026-08-26__random__v1.0.0.json",
    "evaluations/2026-08-26__recent_frequency__v1.0.0.json",
    "evaluations/2026-08-26__v3_boosting__v1.0.0.json",
    "evidence/operational_history/DI-2026-08-20-registered-history/pin-registry.jsonl",
    CANARY_SUCCESS_PATH,
    "predictions/2026-08-29__ema_gap__v1.0.0.json",
    "predictions/2026-08-29__ensemble__v1.0.0.json",
    "predictions/2026-08-29__logistic__v1.0.0.json",
    "predictions/2026-08-29__long_frequency__v1.0.0.json",
    "predictions/2026-08-29__random__v1.0.0.json",
    "predictions/2026-08-29__recent_frequency__v1.0.0.json",
    "predictions/2026-08-29__v3_boosting__v1.0.0.json",
]

AUTHORIZATION_BASE_K_INTEGRITY = {
    "allowed_changes_from_M_I": {
        "content_addressed_source_additions": [
            "evidence/live_sources/loto_quebec/2026-08-26-{sha256}.html",
            "evidence/live_sources/wclc/2026-08-26-{sha256}.html",
        ],
        "exact_static_paths": K_ALLOWED_STATIC_PATHS,
        "path_set_bound_by_C_evidence": True,
        "scope": "exact_Stage1_canary_publication_artifacts_and_C_only",
    },
    "base": "reviewed_implementation_merge_M_I",
    "preserve_all_other_tree_entries": True,
    "prohibited_drift": ["src", "config", "workflows", "documentation_semantics"],
}

RUNTIME_DEPENDENCY_CLOSURE = {
    "algorithm": {
        "dynamic_or_unresolved_local_import": "prohibited",
        "include_all_transitive_local_imports": True,
        "local_namespace": "lotto649",
        "record": "repository_relative_path_and_git_blob",
        "sort": "path_ascending",
    },
    "binding": {
        "actual_blob_list": "bound_in_I_review_and_authorization_JSON",
        "checkpoints": ["I", "K", "A_s", "M_A"],
        "required_equality": "exact_same_path_and_git_blob_manifest",
        "schema": "lotto649-v12-runtime-dependency-closure-v1",
    },
    "seed_paths": [
        "config.yaml",
        CONFIG_PATH,
        REGISTRATION_PATH,
        RUNTIME_LOCK_PATH,
        "src/lotto649/config.py",
        "src/lotto649/domain.py",
        "src/lotto649/features.py",
        "src/lotto649/models/factory.py",
        "src/lotto649/models/v12_parity_transition.py",
        "src/lotto649/notification.py",
        "src/lotto649/operational_history.py",
        "src/lotto649/research_features.py",
        "src/lotto649/v12_evidence.py",
        "src/lotto649/v12_registered_attempt.py",
        "tools/run_v12_historical.py",
    ],
}


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _registration() -> dict[str, Any]:
    return json.loads((ROOT / REGISTRATION_PATH).read_bytes())


def _registration_commit() -> str | None:
    final_commits: list[str | None] = []
    for relative_path in (REGISTRATION_PATH, CONFIG_PATH):
        completed = subprocess.run(
            [
                "git",
                "-C",
                str(ROOT),
                "log",
                "-1",
                "--format=%H",
                "--",
                relative_path,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        final_commits.append(completed.stdout.strip() or None)
    assert len(set(final_commits)) == 1, (
        "the final registration seal and config must change together at R"
    )
    return final_commits[0]


def _git_path_exists(commit: str, relative_path: str) -> bool:
    completed = subprocess.run(
        ["git", "-C", str(ROOT), "cat-file", "-e", f"{commit}:{relative_path}"],
        check=False,
        capture_output=True,
    )
    return completed.returncode == 0


def _git_bytes(commit: str, relative_path: str) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(ROOT), "show", f"{commit}:{relative_path}"],
        check=True,
        capture_output=True,
    )
    return completed.stdout


def _git_blob(commit: str, relative_path: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", f"{commit}:{relative_path}"],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _authority_target_dates_from_git(registration: dict[str, Any]) -> list[date]:
    authority = registration["authority"]
    immutable = authority["immutable_objects"]
    history = authority["published_history"]

    seal_raw = _git_bytes(MAIN_AUTHORITY_COMMIT, history["base_seal_path"])
    registry_raw = _git_bytes(MAIN_AUTHORITY_COMMIT, history["pin_registry_path"])
    assert len(seal_raw) == immutable["seal"]["bytes"]
    assert sha256(seal_raw).hexdigest() == immutable["seal"]["sha256"]
    assert (
        _git_blob(MAIN_AUTHORITY_COMMIT, history["base_seal_path"])
        == immutable["seal"]["git_blob"]
    )
    assert len(registry_raw) == immutable["registry"]["bytes"]
    assert sha256(registry_raw).hexdigest() == immutable["registry"]["sha256"]
    assert (
        _git_blob(MAIN_AUTHORITY_COMMIT, history["pin_registry_path"])
        == immutable["registry"]["git_blob"]
    )

    pin_events = [json.loads(line) for line in registry_raw.splitlines()]
    pin = pin_events[-1]
    suffix_path = pin["suffix"]["path"]
    suffix_raw = _git_bytes(MAIN_AUTHORITY_COMMIT, suffix_path)
    assert len(suffix_raw) == immutable["suffix"]["bytes"]
    assert sha256(suffix_raw).hexdigest() == immutable["suffix"]["sha256"]
    assert (
        _git_blob(MAIN_AUTHORITY_COMMIT, suffix_path) == immutable["suffix"]["git_blob"]
    )
    suffix_events = [json.loads(line) for line in suffix_raw.splitlines()]
    assert suffix_events[-1]["event_sha256"] == immutable["suffix"]["head_sha256"]

    seal = json.loads(seal_raw)
    base_path = seal["corrected_epoch"]["path"]
    base_raw = _git_bytes(MAIN_AUTHORITY_COMMIT, base_path)
    assert len(base_raw) == immutable["base"]["bytes"]
    assert sha256(base_raw).hexdigest() == immutable["base"]["sha256"]
    assert _git_blob(MAIN_AUTHORITY_COMMIT, base_path) == immutable["base"]["git_blob"]

    rows = csv.DictReader(io.StringIO(base_raw.decode("UTF-8")))
    dates = [date.fromisoformat(row["draw_date"]) for row in rows]
    dates.extend(
        date.fromisoformat(event["draw"]["draw_date"]) for event in suffix_events
    )
    return dates


def _calendar_bytes(first_target: str, last_target: str) -> bytes:
    current = date.fromisoformat(first_target)
    final = date.fromisoformat(last_target)
    records: list[str] = []
    while current <= final:
        if current.weekday() in (2, 5):
            records.append(current.isoformat())
        current += timedelta(days=1)
    return ("\n".join(records) + "\n").encode("UTF-8")


def _assert_absent_at_registration(relative_path: str) -> None:
    registration_commit = _registration_commit()
    if registration_commit is None:
        assert not (ROOT / relative_path).exists(), relative_path
    else:
        assert not _git_path_exists(registration_commit, relative_path), relative_path


def test_v12_registration_files_are_present_and_seal_is_canonical_json() -> None:
    for relative_path in (*REGISTERED_FILES, REGISTRATION_PATH):
        assert (ROOT / relative_path).is_file(), relative_path

    raw = (ROOT / REGISTRATION_PATH).read_bytes()
    registration = json.loads(raw)
    assert raw == _canonical_json(registration) + b"\n"
    assert registration["schema_version"] == "lotto649-research-registration-v1"
    assert registration["experiment_id"] == EXPERIMENT_ID
    assert registration["model_version"] == MODEL_VERSION
    assert registration["registered_on"] == "2026-08-24"


def test_v12_registered_file_hashes_bind_basis_experiment_config_and_runtime() -> None:
    registration = _registration()
    registered_files = registration["registered_files"]
    registration_commit = _registration_commit()

    assert list(registered_files) == sorted(REGISTERED_FILES)
    for relative_path in REGISTERED_FILES:
        raw = (ROOT / relative_path).read_bytes()
        if registration_commit is not None:
            assert _git_bytes(registration_commit, relative_path) == raw
        assert registered_files[relative_path] == {
            "bytes": len(raw),
            "sha256": sha256(raw).hexdigest(),
        }
    if registration_commit is not None:
        assert (
            _git_bytes(registration_commit, REGISTRATION_PATH)
            == (ROOT / REGISTRATION_PATH).read_bytes()
        )


def test_v12_status_is_registered_only_and_execution_is_not_authorized() -> None:
    registration = _registration()

    assert registration["status"] == {
        "automatic_execution": "prohibited",
        "historical_scoring": "not_scored",
        "implementation": "not_implemented",
        "prospective": "not_activated",
        "registration": "registered",
        "research_execution": "not_authorized",
    }
    assert registration["phases"] == {
        "authorization": "A_absent",
        "forecast_or_score_before_A": "prohibited",
        "implementation": "I_absent",
        "registration": "R_frozen",
        "required_order": "R < I < A",
    }
    assert registration["execution_authorization_path"] == AUTHORIZATION_PATH
    _assert_absent_at_registration(AUTHORIZATION_PATH)

    assert registration["expected_implementation_paths"] == list(IMPLEMENTATION_PATHS)
    for relative_path in IMPLEMENTATION_PATHS:
        _assert_absent_at_registration(relative_path)

    assert registration["artifact_paths"] == ARTIFACT_PATHS
    for relative_path in ARTIFACT_PATHS.values():
        _assert_absent_at_registration(relative_path)


def test_v12_A_requires_completed_stage1_production_canary_evidence() -> None:
    registration = _registration()
    config = yaml.safe_load((ROOT / CONFIG_PATH).read_text(encoding="utf-8"))

    prerequisite = registration["production_canary_prerequisite"]
    assert prerequisite == config["production_canary_prerequisite"]
    for key, expected in PRODUCTION_CANARY_PREREQUISITE.items():
        if key != "required_bindings":
            assert prerequisite[key] == expected
    for key, expected in PRODUCTION_CANARY_PREREQUISITE["required_bindings"].items():
        observed = prerequisite["required_bindings"][key]
        if key == "reviewed_main_sha":
            for nested_key, nested_expected in expected.items():
                assert observed[nested_key] == nested_expected
        else:
            assert observed == expected
    _assert_absent_at_registration(CANARY_SUCCESS_PATH)

    plan_identity = PRODUCTION_CANARY_PREREQUISITE["required_bindings"]["plan"]
    plan_raw = _git_bytes(MAIN_AUTHORITY_COMMIT, CANARY_PLAN_PATH)
    assert len(plan_raw) == plan_identity["bytes"]
    assert sha256(plan_raw).hexdigest() == plan_identity["sha256"]
    assert (
        _git_blob(MAIN_AUTHORITY_COMMIT, CANARY_PLAN_PATH) == plan_identity["git_blob"]
    )
    plan = json.loads(plan_raw)
    assert plan["status"] == "merged_armed_not_executed"
    assert plan["stage"]["deployment_state"] == "merged_armed_not_executed"
    assert plan["stage2"]["condition"] == (
        "stage_1_canary_success_and_independent_review"
    )


def test_v12_authorization_summaries_defer_execution_to_M_A() -> None:
    registration = _registration()
    config = yaml.safe_load((ROOT / CONFIG_PATH).read_text(encoding="utf-8"))
    expected = {
        "invariant": (
            "only_normal_merge_M_A_at_protected_remote_main_HEAD_executes_"
            "A_s_non_authoritative"
        ),
        "paths": list(AUTHORIZATION_SUMMARY_PATHS),
        "required_sentence": AUTHORIZATION_SUMMARY_SENTENCE,
    }

    assert registration["authorization_summary_contract"] == expected
    assert config["authorization_summary_contract"] == expected
    for relative_path in AUTHORIZATION_SUMMARY_PATHS:
        summary = (ROOT / relative_path).read_text(encoding="utf-8")
        assert AUTHORIZATION_SUMMARY_SENTENCE in summary, relative_path
        assert "canary-success evidence `C`" in summary, relative_path
        assert "No successful canary evidence exists" in summary, relative_path
        assert "No V12 forecast or score exists" in summary, relative_path


def test_v12_attempt_limit_is_enforced_by_one_repository_global_lease() -> None:
    registration = _registration()
    config = yaml.safe_load((ROOT / CONFIG_PATH).read_text(encoding="utf-8"))

    assert registration["historical_scope"]["historical_attempt_limit"] == 1
    assert config["historical_scope"]["historical_attempt_limit"] == 1
    assert registration["repository_global_attempt_lease"] == (
        REPOSITORY_GLOBAL_ATTEMPT_LEASE
    )
    assert config["repository_global_attempt_lease"] == (
        REPOSITORY_GLOBAL_ATTEMPT_LEASE
    )
    for relative_path in (BASIS_PATH, EXPERIMENT_PATH):
        specification = (ROOT / relative_path).read_text(encoding="utf-8")
        assert GLOBAL_ATTEMPT_LEASE_REF in specification, relative_path
        assert "exactly one atomic GitHub `createRef`" in specification, relative_path
        assert "Never delete or update the lease ref" in specification, relative_path
        assert (
            "GitHub create-commit returned SHA must equal locally computed L"
            in specification
        ), relative_path


def test_v12_canary_and_runtime_authority_cannot_self_attest_or_drift() -> None:
    registration = _registration()
    config = yaml.safe_load((ROOT / CONFIG_PATH).read_text(encoding="utf-8"))
    prerequisite = registration["production_canary_prerequisite"]

    assert prerequisite == config["production_canary_prerequisite"]
    assert prerequisite["required_bindings"]["canary_success_integration_C"] == (
        CANARY_INTEGRATION_EVIDENCE_CONTRACT
    )
    assert prerequisite["required_bindings"]["reviewed_main_sha"] == {
        "binding": "expected_sha_equals_workflow_head_sha_equals_checkout_head",
        "branch": "main",
        "format": "lowercase_40_hex_sha1",
        "independent_review_evidence": {
            "body_sha256": "lowercase_64_hex",
            "comment_id": "positive_integer_immutable",
            "reviewed_sha": "equals_expected_sha",
            "reviewer": "independent_not_workflow_actor_or_commit_author",
            "verdict": "pass",
        },
        "not_satisfied_by": "old_live_run_or_workflow_file_hash",
        "repository": "Jasper-Shi/lottopred",
        "source": "post_merge_independent_review",
    }
    assert registration["authorization_base_K_integrity"] == (
        AUTHORIZATION_BASE_K_INTEGRITY
    )
    assert config["authorization_base_K_integrity"] == (AUTHORIZATION_BASE_K_INTEGRITY)
    assert registration["runtime_dependency_closure"] == RUNTIME_DEPENDENCY_CLOSURE
    assert config["runtime_dependency_closure"] == RUNTIME_DEPENDENCY_CLOSURE


def test_v12_authority_is_current_main_published_history_without_2026_scoring() -> None:
    registration = _registration()
    authority = registration["authority"]

    assert authority["repository"] == "Jasper-Shi/lottopred"
    assert authority["branch"] == "main"
    assert authority["commit"] == MAIN_AUTHORITY_COMMIT
    assert authority["published_history"] == {
        "base_draw_count": 4442,
        "base_history_through": "2026-08-15",
        "base_seal_path": (
            "evidence/data_integrity/DI-2026-08-20-registered-history/seal.json"
        ),
        "draw_count": 4444,
        "history_start": "1982-06-12",
        "history_through": "2026-08-22",
        "incident_id": "DI-2026-08-20-registered-history",
        "kind": "PublishedHistory",
        "pin_registry_path": (
            "evidence/operational_history/DI-2026-08-20-registered-history/"
            "pin-registry.jsonl"
        ),
        "suffix_event_count": 2,
    }

    history = authority["published_history"]
    base_seal = json.loads(_git_bytes(MAIN_AUTHORITY_COMMIT, history["base_seal_path"]))
    pin_events = [
        json.loads(line)
        for line in _git_bytes(
            MAIN_AUTHORITY_COMMIT, history["pin_registry_path"]
        ).splitlines()
    ]
    pin = pin_events[-1]
    assert base_seal["corrected_epoch"]["draw_count"] == history["base_draw_count"]
    assert (
        base_seal["corrected_epoch"]["history_through"]
        == history["base_history_through"]
    )
    assert pin["suffix"]["event_count"] == history["suffix_event_count"]
    assert pin["suffix"]["history_through"] == history["history_through"]
    assert (
        history["base_draw_count"] + history["suffix_event_count"]
        == history["draw_count"]
        == 4444
    )
    assert len(_authority_target_dates_from_git(registration)) == history["draw_count"]

    scope = registration["historical_scope"]
    assert scope["known_2026"] == {
        "classification": "consumed_excluded",
        "history_through": "2026-08-22",
        "scored_target_count": 0,
        "start": "2026-01-01",
    }


def test_v12_corrected_consumed_historical_scope_is_exactly_627_targets() -> None:
    registration = _registration()
    scope = registration["historical_scope"]

    assert scope["evidence_lane"] == "consumed_historical_diagnostic"
    assert scope["historical_attempt_limit"] == 1
    assert scope["burn_in"] == {
        "first_draw": "2019-05-15",
        "last_draw": "2019-12-28",
        "scored_target_count": 0,
    }
    assert scope["aggregate"] == {
        "first_target": "2020-01-01",
        "last_target": "2025-12-31",
        "target_count": 627,
    }
    assert scope["halves"] == [
        {
            "first_target": "2020-01-01",
            "last_target": "2022-12-31",
            "name": "first_half",
            "target_count": 314,
        },
        {
            "first_target": "2023-01-04",
            "last_target": "2025-12-31",
            "name": "second_half",
            "target_count": 313,
        },
    ]
    assert sum(half["target_count"] for half in scope["halves"]) == 627
    assert scope["aggregate"]["target_count"] == 627
    assert all(half["last_target"] < "2026-01-01" for half in scope["halves"])
    assert scope["known_2026"]["scored_target_count"] == 0
    assert registration["target_date_identities"] == {
        "aggregate": {
            "bytes": 6897,
            "encoding": TARGET_DATE_ENCODING,
            "first_target": "2020-01-01",
            "last_target": "2025-12-31",
            "sha256": (
                "c339733dccc04c3ac25aca15ce991c31421ba35580488e7acadbea5672705782"
            ),
            "target_count": 627,
        },
        "first_half": {
            "bytes": 3454,
            "encoding": TARGET_DATE_ENCODING,
            "first_target": "2020-01-01",
            "last_target": "2022-12-31",
            "sha256": (
                "c3bea21f775ce8077d25b255ae18a3701b08b22f2bf39c812ce40e78f6edc2e5"
            ),
            "target_count": 314,
        },
        "second_half": {
            "bytes": 3443,
            "encoding": TARGET_DATE_ENCODING,
            "first_target": "2023-01-04",
            "last_target": "2025-12-31",
            "sha256": (
                "32f924f82aa85e2be7440c66cf7133ab1b16669ede77e7230efef8d7e473ee7b"
            ),
            "target_count": 313,
        },
    }


def test_v12_target_date_bytes_match_fixed_git_history_and_calendar() -> None:
    registration = _registration()
    registered_dates = _authority_target_dates_from_git(registration)

    for identity in registration["target_date_identities"].values():
        raw = _calendar_bytes(identity["first_target"], identity["last_target"])
        calendar_dates = [
            date.fromisoformat(line.decode("ASCII")) for line in raw.splitlines()
        ]
        git_dates = [
            target
            for target in registered_dates
            if identity["first_target"] <= target.isoformat() <= identity["last_target"]
        ]
        git_raw = ("\n".join(target.isoformat() for target in git_dates) + "\n").encode(
            "UTF-8"
        )
        assert git_raw == raw
        assert all(target.weekday() in (2, 5) for target in calendar_dates)
        assert identity["encoding"] == TARGET_DATE_ENCODING
        assert len(calendar_dates) == identity["target_count"]
        assert len(raw) == identity["bytes"]
        assert sha256(raw).hexdigest() == identity["sha256"]


def test_v12_consumed_history_can_never_enter_global_evidence_or_stop_research() -> (
    None
):
    registration = _registration()
    config = yaml.safe_load((ROOT / CONFIG_PATH).read_text(encoding="utf-8"))

    assert registration["historical_governance"] == HISTORICAL_GOVERNANCE
    assert config["historical_governance"] == HISTORICAL_GOVERNANCE
    assert config["notifications"] == {
        "classification_zh": "历史诊断/审计候选、不可晋升",
        "language": "zh-CN",
        "post_A": "historical_diagnostic_audit_candidate_only",
        "pre_A": "prohibited",
        "promotion_language": "prohibited",
        "success_language": "prohibited",
    }
    assert registration["notifications"] == config["notifications"]


def test_v12_model_and_control_identities_are_frozen_without_scoring() -> None:
    registration = _registration()
    model = registration["model"]
    controls = registration["controls"]

    assert model == {
        "beta_prior": "N(0,1)",
        "bucket_counts": [134596, 1062600, 3187800, 4655200, 3491400, 1275120, 177100],
        "candidate_name": "v12_post_rng_parity_composition_transition",
        "coefficient": "one_signed_scalar_beta",
        "final6": "sorted_marginal_top6",
        "law": "lag_one_conditional_parity_exponential_family",
        "probability_contract": "labels_1_to_49_open_interval_fsum_six_abs_1e-12",
        "ranking_tie_break": "probability_desc_number_asc",
        "rng_regime_start": "2019-05-15",
        "seed": 649,
        "solver": "strict_bracket_exact_256_step_bisection_no_early_stop",
        "target_or_future_access_before_forecast_freeze": "prohibited",
        "version": MODEL_VERSION,
    }

    pseudo_canonical = (
        "1,2,5,6,7,8,9,10,12,16,17,18,20,24,28,29,32,33,40,41,42,43,44,48,49"
    )
    assert controls["pseudo_parity"] == {
        "canonical_utf8": pseudo_canonical,
        "label_correlation_with_true_parity": "-9/40",
        "labels": PSEUDO_PARITY_SET,
        "model_name": "v12_pseudo_parity_composition_transition_control",
        "role": "fixed_sanity_control_not_discovery",
        "sha256": "bfbb8cb711e0734aea8a29f6c02aee41a0f39a36643b3155245dc3550bbf14dd",
    }
    assert (
        sha256(pseudo_canonical.encode("utf-8")).hexdigest()
        == (controls["pseudo_parity"]["sha256"])
    )
    assert controls["comparators"] == ["ensemble_v1.0.0", "random_v1.0.0"]
    assert controls["opportunity_order"] == [
        "v12_post_rng_parity_composition_transition",
        "v12_pseudo_parity_composition_transition_control",
        "ensemble_v1.0.0",
        "random_v1.0.0",
    ]


def test_v12_multiplicity_and_all_ten_scientific_gates_are_frozen() -> None:
    registration = _registration()

    assert registration["multiplicity"] == {
        "family": "transition_markov",
        "family_size": 4,
        "holm_input_vector": [1.0, 1.0, 0.9783404732169021, "p_raw_v12"],
        "procedure": "general_holm_step_down",
        "variant_index": 4,
        "v12_passing_equivalent": "min(1.0,4.0*p_raw_v12)",
    }
    assert registration["gates"] == {
        "combination": "all_ten_conjunctive",
        "count": 10,
        "ordered": SCIENTIFIC_GATES,
    }
    assert registration["control_null_contract"] == CONTROL_NULL_CONTRACT


def test_v12_config_is_registration_bound_and_cannot_enable_execution() -> None:
    registration = _registration()
    config = yaml.safe_load((ROOT / CONFIG_PATH).read_text(encoding="utf-8"))

    assert config["experiment"] == {
        "id": EXPERIMENT_ID,
        "model_version": MODEL_VERSION,
        "registration_seal": REGISTRATION_PATH,
        "seed": 649,
        "status": "registered_not_implemented_not_authorized_not_scored",
    }
    assert config["data"] == registration["authority"]["published_history"]
    assert config["historical_scope"] == registration["historical_scope"]
    assert config["canonical_command"] == CANONICAL_COMMAND
    assert config["artifact_paths"] == ARTIFACT_PATHS
    assert registration["canonical_command"] == CANONICAL_COMMAND
    assert registration["artifact_paths"] == ARTIFACT_PATHS
    assert len(registration["artifact_paths"]) == 6
    assert config["control_null_contract"] == CONTROL_NULL_CONTRACT
    assert config["execution"] == {
        "authorization": "valid_A_required",
        "authorization_seal": AUTHORIZATION_PATH,
        "automatic": False,
        "pre_A": "prohibited",
        "required_phase_order": "R < I < A",
    }
    assert config["notifications"] == {
        "classification_zh": "历史诊断/审计候选、不可晋升",
        "language": "zh-CN",
        "post_A": "historical_diagnostic_audit_candidate_only",
        "pre_A": "prohibited",
        "promotion_language": "prohibited",
        "success_language": "prohibited",
    }
