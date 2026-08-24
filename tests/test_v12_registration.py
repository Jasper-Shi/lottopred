from __future__ import annotations

import json
import subprocess
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
}

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
        "paired_candidate_minus_pseudo_control_top12_bootstrap_lower_"
        "strictly_positive_and_pseudo_and_random_controls_null_"
        "aggregate_and_halves"
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
    completed = subprocess.run(
        [
            "git",
            "-C",
            str(ROOT),
            "log",
            "--diff-filter=A",
            "--format=%H",
            "--",
            REGISTRATION_PATH,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    commits = completed.stdout.splitlines()
    assert len(commits) <= 1, "the immutable registration seal was added twice"
    return commits[0] if commits else None


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
    base_seal = json.loads((ROOT / history["base_seal_path"]).read_bytes())
    pin_events = [
        json.loads(line)
        for line in (ROOT / history["pin_registry_path"]).read_bytes().splitlines()
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
            "first_target": "2020-01-01",
            "last_target": "2025-12-31",
            "sha256": (
                "c339733dccc04c3ac25aca15ce991c31421ba35580488e7acadbea5672705782"
            ),
            "target_count": 627,
        },
        "first_half": {
            "bytes": 3454,
            "first_target": "2020-01-01",
            "last_target": "2022-12-31",
            "sha256": (
                "c3bea21f775ce8077d25b255ae18a3701b08b22f2bf39c812ce40e78f6edc2e5"
            ),
            "target_count": 314,
        },
        "second_half": {
            "bytes": 3443,
            "first_target": "2023-01-04",
            "last_target": "2025-12-31",
            "sha256": (
                "32f924f82aa85e2be7440c66cf7133ab1b16669ede77e7230efef8d7e473ee7b"
            ),
            "target_count": 313,
        },
    }


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
    assert config["execution"] == {
        "authorization": "valid_A_required",
        "authorization_seal": AUTHORIZATION_PATH,
        "automatic": False,
        "pre_A": "prohibited",
        "required_phase_order": "R < I < A",
    }
    assert config["notifications"] == {
        "language": "zh-CN",
        "post_A": "breakthrough_only_required",
        "pre_A": "prohibited",
    }
