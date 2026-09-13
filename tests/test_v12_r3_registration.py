"""Verify the immutable R3 registration and its source-only execution boundary.

These checks import no V12 runtime, open no history/results/predictions and
never execute an authorization verifier.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REG = (
    "evidence/research_registrations/v12-post-rng-parity-composition-transition-v3.json"
)
CONFIG = "config/research-v12-0-2-post-rng-parity-composition-transition.yaml"
R1_REF = "0af20fc41fc5aaa0879dada0a258797a8bc14e20"
R1_PATH = (
    "evidence/research_registrations/v12-post-rng-parity-composition-transition-v1.json"
)
CORE_PATH = "src/lotto649/models/v12_parity_transition.py"
CORE_SHA = "fae93e0a6f76c6604eabe24f6b93676e22e87d7e567365b382484433fba2eb77"
FINGERPRINT = "af2e16a55ff0e817cf71208471e19e4f481bed63990f7e41268997c4c4b35c76"
NEW_PATHS = [
    "src/lotto649/v12_0_2_evidence.py",
    "src/lotto649/v12_0_2_registered_attempt.py",
    "tools/run_v12_0_2_historical.py",
    "tests/test_v12_0_2_registered_attempt.py",
    "tests/test_v12_0_2_evidence_equivalence.py",
    "tests/fixtures/v12_0_2_git_commit_projection.json",
]


def _canonical(value):
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode()


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _git(*args):
    return subprocess.run(("git", *args), cwd=ROOT, capture_output=True, check=False)


def _require_git(*args):
    result = _git(*args)
    assert result.returncode == 0, args
    return result.stdout


def _authority():
    result = _require_git(
        "log",
        "--full-history",
        "--no-renames",
        "--reverse",
        "--format=%H",
        "--diff-filter=A",
        "HEAD",
        "--",
        REG,
    )
    matches = result.decode("ascii").splitlines()
    assert len(matches) <= 1, "ambiguous registration adding authority"
    if not matches:
        assert _git("cat-file", "-e", f"HEAD:{REG}").returncode != 0, (
            "committed registration lacks an ordinary ADD authority"
        )
        return None
    authority = matches[0]
    parents = (
        _require_git("rev-list", "--parents", "-n", "1", authority)
        .decode("ascii")
        .split()
    )
    assert len(parents) == 2, (
        "registration source must be an ordinary single-parent commit"
    )
    added = _require_git(
        "diff-tree",
        "--no-commit-id",
        "--name-status",
        "--no-renames",
        "-r",
        authority,
        "--",
        REG,
    )
    assert added == f"A\t{REG}\n".encode(), (
        "authority must add the exact registered path"
    )
    return authority


def _at_authority(path):
    authority = _authority()
    return (
        (ROOT / path).read_bytes()
        if authority is None
        else _require_git("show", f"{authority}:{path}")
    )


def _exists_at_authority(path):
    authority = _authority()
    return (
        (ROOT / path).exists()
        if authority is None
        else _git("cat-file", "-e", f"{authority}:{path}").returncode == 0
    )


def _registration():
    raw = (ROOT / REG).read_bytes()
    value = json.loads(raw)
    assert raw == _canonical(value) + b"\n"
    assert _at_authority(REG) == raw
    return value


def test_r3_is_finalized_registered_and_execution_closed():
    r3 = _registration()
    assert r3["status"] == {
        "registration": "registered",
        "implementation": "not_implemented",
        "research_execution": "not_authorized",
        "historical_scoring": "not_scored",
        "prospective": "not_activated",
        "automatic_execution": "prohibited",
    }
    assert isinstance(r3["registered_on"], str)
    assert len(r3["base_head"]) == 40
    assert isinstance(r3["registered_files"], dict) and r3["registered_files"]
    assert REG not in r3["registered_files"], "seal cannot hash itself"
    assert r3["scope"]["live_lane"] == "none"
    assert set(r3["execution_authorizations"]) == {"historical"}


def test_r3_science_is_exact_r1_with_already_present_core():
    r3 = _registration()
    source = _require_git("show", f"{R1_REF}:{R1_PATH}")
    assert (
        _sha(source)
        == "4406bd25ee82195bff7a97b258885cb3bb3c1a8fb829f383c5e3c1616e169170"
    )
    r1 = json.loads(source)
    eq = r3["statistical_equivalence"]
    assert eq["statistical_behavior_changed"] is False
    fp = eq["fingerprint_payload"]
    assert _sha(_canonical(fp)) == FINGERPRINT == eq["fingerprint_sha256"]
    assert len(fp["contract_sections"]) == 10
    for key, digest in fp["contract_sections"].items():
        assert _sha(_canonical(r1[key])) == digest
    assert fp["seed"] == 649
    assert fp["historical_target_count"] == 627
    assert fp["half_target_counts"] == [314, 313]
    assert fp["gate_count"] == 10
    assert r1["model"]["version"] == "v12.0.0"
    assert _sha(_at_authority(CORE_PATH)) == CORE_SHA
    assert CORE_PATH not in r3["expected_implementation_paths"]
    for path, seal in r3["complete_R1_normative_sources"].items():
        raw = _require_git("show", f"{R1_REF}:{path}")
        assert seal == {
            "authority_commit": R1_REF,
            "bytes": len(raw),
            "sha256": _sha(raw),
        }


def test_r3_registration_tree_absences_remain_stable_after_i3():
    r3 = _registration()
    assert r3["expected_implementation_paths"] == NEW_PATHS
    assert len(r3["artifact_paths"]) == 9
    absent = [
        *NEW_PATHS,
        r3["execution_authorizations"]["historical"]["path"],
        *r3["artifact_paths"].values(),
    ]
    tree = r3["r3_git_authority"]["tree_assertions"]
    assert tree["absent_paths"] == absent
    for path in absent:
        assert not _exists_at_authority(path), path
    assert _sha(_at_authority("config.yaml")) == tree["config_yaml_sha256"]
    authority = _authority()
    if authority is not None:
        assert (
            _require_git("rev-parse", f"{authority}^").decode("ascii").strip()
            == r3["base_head"]
        )


def test_r3_file_seals_and_old_bytes_are_exact():
    r3 = _registration()
    assert r3["repository_documentation_sync"]["state"] == "completed_and_sealed_at_R3"
    for path, seal in r3["registered_files"].items():
        raw = _at_authority(path)
        assert seal == {"bytes": len(raw), "sha256": _sha(raw)}, path
    for path in r3["repository_documentation_sync"]["paths"]:
        assert (
            _sha(_at_authority(path))
            == r3["repository_documentation_sync"]["sha256"][path]
        )
    preserved = r3["legacy_byte_preservation"]
    assert set(preserved["manifest"]) == set(preserved["paths"])
    for path, seal in preserved["manifest"].items():
        base_bytes = _require_git("show", f"{r3['base_head']}:{path}")
        base_blob = (
            _require_git("rev-parse", f"{r3['base_head']}:{path}")
            .decode("ascii")
            .strip()
        )
        assert seal == {
            "git_blob": base_blob,
            "bytes": len(base_bytes),
            "sha256": _sha(base_bytes),
        }
        assert _at_authority(path) == base_bytes, path


def test_r3_config_identity_and_shared_contracts_are_exact():
    r3 = _registration()
    # JSON is a valid YAML representation. If root chooses conventional YAML
    # formatting, replace only this parser with yaml.safe_load.
    cfg = json.loads(_at_authority(CONFIG))
    assert cfg["experiment"]["id"] == "V12_0_2_historical_operational_rebinding"
    assert cfg["experiment"]["model_version"] == "v12.0.2"
    assert cfg["experiment"]["seed"] == 649
    assert (
        cfg["experiment"]["status"]
        == "registered_not_implemented_not_authorized_not_scored"
    )
    for key in cfg:
        if key not in {"experiment", "execution"}:
            assert cfg[key] == r3[key], key
    assert r3["canonical_command"] == [
        "python3.12",
        "tools/run_v12_0_2_historical.py",
        "--consume-v12-0-2-once",
    ]
    assert r3["historical_runtime_dependency_closure"]["equality_checkpoints"] == [
        "I3",
        "K_H3",
        "A_H_s3",
        "M_A_H3",
    ]
    assert r3["independent_review_and_CI"]["fresh_for"] == ["I3", "A_H_s3"]


def test_r3_exact_projection_and_safe_startup_are_preregistered():
    r3 = _registration()
    p = r3["git_commit_representation_contract"]
    assert p["raw_message"] == p["POST_message"] == "canonical_body_plus_exactly_one_LF"
    assert p["GET_message"] == "exact_canonical_body_no_trailing_LF"
    assert p["GET_unsigned_verification"] == {
        "verified": False,
        "reason": "unsigned",
        "signature": None,
        "payload": None,
        "verified_at": None,
    }
    assert p["representation_rules"] == [
        "no_strip",
        "no_rstrip",
        "no_whitespace_normalization",
        "no_alternate_message_form",
        "no_raw_bytes_change",
        "no_runtime_fallback_or_relaxation",
    ]
    s = r3["startup_receipt_contract"]
    assert "before_creation" in s["creation"]["read_only_authorization_gate"]
    assert s["required_phase_events"][:2] == [
        "authorized_startup_started",
        "capability_issued",
    ]
    assert s["continued_clean_clone_checks"]["filename_only_exception"] == "prohibited"
    assert s["pre_POST_intent"]["must_precede_each_POST"] is True
    assert s["pre_POST_intent"]["required_fields"] == [
        "phase_enum",
        "nonce_hex",
        "expected_lease_oid",
        "raw_commit_sha256",
        "request_body_bytes",
        "request_body_sha256",
    ]
    c = s["claim_and_scientific_ledger_binding"]
    assert c["checkpoint_fields"] == [
        "path",
        "sequence",
        "head_sha256",
        "prefix_byte_count",
        "prefix_sha256",
    ]
    assert c["retroactive_claim_or_scientific_binding_update"] == "prohibited"
    assert c["cyclic_dependency"] == "prohibited"
    assert r3["repository_global_attempt_lease"]["automatic_retry"] is False
    assert (
        r3["repository_global_attempt_lease"]["manual_retry_or_resume_same_version"]
        == "prohibited"
    )


def test_r3_closed_post_ref_shapes_and_agent_review_semantics():
    r3 = _registration()
    p = r3["git_commit_representation_contract"]
    assert p["POST_commit_request_shape"]["required_keys"] == [
        "tree",
        "parents",
        "author",
        "committer",
        "message",
    ]
    assert p["POST_commit_request_shape"]["optional_keys"] == []
    assert p["POST_commit_response_shape"]["required_keys"] == ["sha"]
    assert p["POST_commit_response_shape"]["optional_keys"] == [
        "node_id",
        "url",
        "html_url",
        "author",
        "committer",
        "tree",
        "message",
        "parents",
        "verification",
    ]
    assert (
        p["POST_commit_response_shape"]["message_identity_proof"]
        == "none_GET_is_the_sole_fixed_message_projection_check"
    )
    assert p["POST_ref_response_and_GET_ref_shape"]["required_keys"] == [
        "ref",
        "node_id",
        "url",
        "object",
    ]
    assert p["POST_ref_response_and_GET_ref_shape"]["object_required_keys"] == [
        "sha",
        "type",
        "url",
    ]
    review = r3["independent_review_and_CI"]
    assert review["axes"] == ["standards", "spec"]
    assert review["independence"]["different_GitHub_account_requirement"] is False
    assert review["record_exact_keys"] == [
        "axis",
        "check_id",
        "comment_body_sha256",
        "comment_id",
        "pr_number",
        "publisher_login",
        "review_session_id",
        "reviewer_agent_id",
    ]
    assert review["comment_body_exact_keys"] == [
        "schema_version",
        "axis",
        "base_sha",
        "head_sha",
        "closure_sha256",
        "verdict",
        "blocker_count",
        "major_count",
        "reviewer_kind",
        "reviewer_agent_id",
        "review_session_id",
        "publisher_login",
    ]
    assert review["comment_body_values"]["blocker_count"] == 0
    assert review["comment_body_values"]["major_count"] == 0
    assert "after_normal_auth_merge" in review["auth_source_review_discovery"]


def test_r3_preserves_known_v1_aggregate_evidence_status():
    r3 = _registration()
    o = r3["outcome_blindness"]
    assert o["prior_published_V1_aggregates_already_known"] is True
    assert o["raw_governed_history_or_target_records_opened_for_R3"] is False
    assert o["V12_forecast_or_score_available"] is False
    assert o["secrets_read"] is False
    assert o["prior_result_amnesia_or_restored_blindness_claim"] == "prohibited"
    assert "real_history_draws_results_predictions_and_secrets_read" not in o


def test_r3_static_scope_allows_only_future_isolated_synthetic_i3_tests():
    r3 = _registration()
    assert (
        r3["scope"]["R3_registration_execution"]
        == "static_only_no_runtime_verifier_canonical_or_worker_invocation"
    )
    assert (
        r3["scope"]["I3_review_execution"]
        == "isolated_synthetic_fixtures_and_closed_form_pure_validators_mock_adapters_and_mock_worker_paths_only"
    )
    assert r3["scope"]["I3_review_prohibitions"] == [
        "canonical_production_capability_or_attempt",
        "real_history_or_target_answers",
        "network_mutations",
        "registered_real_artifact_paths",
    ]
    assert (
        r3["outcome_blindness"]["R3_canonical_or_verifier_or_worker_invoked"] is False
    )


def test_r3_external_discovery_and_current_attempt_output_provenance():
    r3 = _registration()
    discovery = r3["independent_review_and_CI"]["auth_source_external_discovery"]
    assert len(discovery["allowed_GET_routes"]) == 6
    assert (
        discovery["allowed_GET_routes"][0]
        == "/repos/Jasper-Shi/lottopred/commits/{A_H_s3}/pulls?per_page=100"
    )
    assert discovery["pagination_or_additional_endpoint_expansion"] == "prohibited"
    assert "at_most_100_items" in discovery["list_completeness"]
    ownership = r3["startup_receipt_contract"]["post_claim_artifact_ownership"]
    assert ownership["registered_paths"] == list(r3["artifact_paths"].values())
    assert (
        ownership["filename_or_path_allowlist_without_live_creation_provenance"]
        == "prohibited"
    )
    assert ownership["preexisting_or_foreign_artifact_adoption"] == "prohibited"
    assert "same_current_issued_capability" in ownership["ownership_binding"]


def test_r3_source_has_only_the_registered_ten_paths():
    r3 = _registration()
    base = "3015078e251bdcbb92719e1b291b1807525fef16"
    docs = {
        "AGENTS.md",
        "docs/ARCHITECTURE.md",
        "docs/CODEX_HANDOFF.md",
        "docs/MODEL_PROTOCOL.md",
        "docs/OPERATIONS.md",
        "docs/RESEARCH_ROADMAP.md",
    }
    added = {
        REG,
        CONFIG,
        "docs/experiments/V12_0_2_historical_operational_rebinding.md",
        "tests/test_v12_r3_registration.py",
    }
    assert r3["base_head"] == r3["legacy_byte_preservation"]["base"] == base
    assert r3["registered_on"] == "2026-09-13"
    assert set(r3["registered_files"]) == docs | (added - {REG})
    sync = r3["repository_documentation_sync"]
    assert set(sync["paths"]) == set(sync["sha256"]) == docs
    critical_preserved = {
        CORE_PATH,
        "requirements/v12-historical.txt",
        R1_PATH,
        "evidence/research_registrations/v12-post-rng-parity-composition-transition-v2.json",
        "evidence/research_authorizations/v12-post-rng-parity-composition-transition-v2-historical.json",
        "src/lotto649/v12_0_1_evidence.py",
        "src/lotto649/v12_0_1_registered_attempt.py",
        "tools/run_v12_0_1_historical.py",
        "tests/test_v12_0_1_parity_transition.py",
        "tests/test_v12_0_1_registered_attempt.py",
    }
    assert critical_preserved <= set(r3["legacy_byte_preservation"]["paths"])
    authority = _authority()
    if authority is not None:
        changes = _require_git("diff", "--name-status", "--no-renames", base, authority)
        observed = set(changes.decode("utf-8").splitlines())
        assert observed == {f"M\t{path}" for path in docs} | {
            f"A\t{path}" for path in added
        }


@pytest.fixture
def synthetic_registration_repository(tmp_path, monkeypatch):
    environment = {
        "PATH": os.defpath,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_AUTHOR_NAME": "Synthetic Registration Author",
        "GIT_AUTHOR_EMAIL": "author@example.invalid",
        "GIT_COMMITTER_NAME": "Synthetic Registration Author",
        "GIT_COMMITTER_EMAIL": "author@example.invalid",
        "GIT_AUTHOR_DATE": "2001-01-01T00:00:00Z",
        "GIT_COMMITTER_DATE": "2001-01-01T00:00:00Z",
        "LC_ALL": "C",
    }

    def synthetic_git(*args):
        return subprocess.run(
            (
                "git",
                "-c",
                "core.hooksPath=/dev/null",
                "-c",
                "commit.gpgsign=false",
                *args,
            ),
            cwd=tmp_path,
            env=environment,
            capture_output=True,
            check=True,
        ).stdout

    synthetic_git("init", "-b", "main")
    synthetic_git("commit", "--allow-empty", "-m", "synthetic base")
    monkeypatch.setitem(globals(), "ROOT", tmp_path)
    return synthetic_git


def test_r3_rejects_two_reachable_same_blob_additions(
    tmp_path, synthetic_registration_repository
):
    synthetic_git = synthetic_registration_repository
    base = synthetic_git("rev-parse", "HEAD").decode("ascii").strip()
    for branch in ("left", "right"):
        synthetic_git("checkout", "-b", branch, base)
        registration = tmp_path / REG
        registration.parent.mkdir(parents=True, exist_ok=True)
        registration.write_bytes(b"{}\n")
        synthetic_git("add", "--", REG)
        synthetic_git("commit", "-m", "synthetic " + branch + " addition")
    synthetic_git("merge", "--no-ff", "left", "-m", "synthetic same-blob merge")
    with pytest.raises(AssertionError, match="ambiguous registration adding authority"):
        _authority()


def test_r3_rejects_registration_created_only_by_a_merge(
    tmp_path, synthetic_registration_repository
):
    synthetic_git = synthetic_registration_repository
    base = synthetic_git("rev-parse", "HEAD").decode("ascii").strip()
    for branch in ("left", "right"):
        synthetic_git("checkout", "-b", branch, base)
        synthetic_git("commit", "--allow-empty", "-m", "synthetic " + branch)
    synthetic_git("merge", "--no-ff", "--no-commit", "left")
    registration = tmp_path / REG
    registration.parent.mkdir(parents=True, exist_ok=True)
    registration.write_bytes(b"{}\n")
    synthetic_git("add", "--", REG)
    synthetic_git("commit", "-m", "synthetic merge-only registration")
    with pytest.raises(AssertionError, match="ordinary"):
        _authority()


def test_r3_binds_complete_source_authors_in_raw_commit_metadata():
    r3 = _registration()
    c = r3["source_author_provenance_contract"]
    assert (
        c["location"] == "raw_Git_message_of_exact_reviewed_I3_or_A_H_s3_source_commit"
    )
    assert c["trailer"]["prefix"] == "Research-Author-Provenance: "
    assert c["trailer"]["count"] == c["trailer"]["message_trailing_LF_count"] == 1
    p = c["payload"]
    assert p["schema_version"] == "lotto649-v12-source-author-provenance-v1"
    assert p["phase_by_source"] == {"I3": "I3", "A_H_s3": "A_H_s3"}
    assert p["required_keys"] == ["contributors", "phase", "schema_version"]
    assert p["contributor_required_keys"] == ["agent_id", "session_id"]
    assert p["optional_keys"] == p["contributor_optional_keys"] == []
    assert (p["minimum_contributors"], p["maximum_contributors"]) == (1, 64)
    assert p["identifier_maximum_UTF8_bytes"] == 256
    independence = c["review_independence"]
    assert (
        independence["each_reviewer_agent_id"]
        == "absent_from_all_contributor_agent_ids"
    )
    assert (
        independence["each_review_session_id"]
        == "absent_from_all_contributor_session_ids"
    )
    assert (
        independence["closed_review_body_and_record_key_sets"]
        == "unchanged_no_author_fields_added"
    )
    assert independence["different_GitHub_account_requirement"] is False
    review = r3["independent_review_and_CI"]["independence"]
    assert (
        review["source_author_binding"]
        == "exact_source_Git_message_Research-Author-Provenance_trailer_under_source_author_provenance_contract"
    )
    assert (
        review["author_separation"]
        == "both_reviewer_agent_ids_absent_from_all_contributor_agent_ids_and_both_review_session_ids_absent_from_all_contributor_session_ids"
    )
    assert c["scope"]["metadata_only"] is True
    assert c["scope"]["statistical_change"] is False
    assert c["scope"]["seventh_I3_path"] == "prohibited"
    resolution = r3["r3_git_authority"]["commit_resolution"]
    assert (
        resolution["traversal"]
        == "all_reachable_ancestors_without_path_history_simplification"
    )
    assert (
        resolution["add_validation"]
        == "explicit_no_rename_status_A_at_unique_ordinary_single_parent_source"
    )
