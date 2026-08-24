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
        "notification_classification_zh": "历史诊断/审计候选、不可晋升",
        "success_language": "prohibited",
    },
    "global_historical_oos_ledger_write": "prohibited",
    "opportunity_ledger": "v12_local_attempt_ledger_only",
    "promotion_from_historical_lane": "prohibited",
    "top12": {
        "attempt_action": "continue",
        "global_stop_search": "prohibited",
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
