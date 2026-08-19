from __future__ import annotations

from datetime import date
from hashlib import sha256
from pathlib import Path

import yaml

from lotto649.research_protocol import load_experiment_registry


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs" / "experiments" / "registry.yaml"
CONFIG = ROOT / "config" / "research-v11-previous-bonus-carryover.yaml"
DEFAULT_CONFIG = ROOT / "config.yaml"
WORKFLOWS = ROOT / ".github" / "workflows"


def test_v11_registration_exists_before_any_scoring() -> None:
    registration = load_experiment_registry(REGISTRY).get(
        "V11_previous_bonus_carryover"
    )

    assert registration.model_name == "v11_previous_bonus_carryover"
    assert registration.status == "registered"


def test_v11_identity_evidence_boundary_and_multiplicity_are_frozen() -> None:
    registration = load_experiment_registry(REGISTRY).get(
        "V11_previous_bonus_carryover"
    )

    assert registration.family == "cross_draw_role_transition"
    assert registration.model_version == "v11.0.0"
    assert registration.registration_file == (
        "docs/experiments/V11_previous_bonus_carryover.md"
    )
    assert registration.registered_on == date(2026, 8, 19)
    assert registration.seed == 649
    assert registration.primary_metric == "top12_hits_lift_vs_theory"
    assert registration.multiplicity_family == "transition_markov"
    assert registration.variant_index == 3
    assert registration.result is None
    assert registration.dataset_source_commit == (
        "90177c80cfb070038d79508fb2e73305a297f516"
    )
    assert registration.dataset_sha256 == (
        "edfb7f8a4a7711a630957d6f86b567e6b254caf7b1d1aaea0edf1d16a34155b3"
    )
    assert registration.dataset_draw_count == 4432
    assert registration.registration_history_through == date(2026, 8, 15)
    assert registration.outcomes_known_source_commit == (
        registration.dataset_source_commit
    )
    assert registration.outcomes_known_sha256 == registration.dataset_sha256
    assert registration.outcomes_known_draw_count == 4432
    assert registration.outcomes_known_through == date(2026, 8, 15)
    assert (ROOT / registration.registration_file).is_file()

    params = registration.parameters
    assert params["evidence_lane"] == "consumed_historical_diagnostic"
    assert params["scoring_before_registration"] == "prohibited"
    assert params["historical_target_count"] == 621
    assert [half["target_count"] for half in params["stability_halves"]] == [
        307,
        314,
    ]
    assert params["holm_family_size_at_registration"] == 3
    assert params["holm_prior_entries"] == [
        {
            "experiment": "V2_statistical_transition_bearing",
            "compatible_primary_p": False,
            "holm_p_entry": 1.0,
        },
        {
            "experiment": "V3_boosting_transition_bearing",
            "compatible_primary_p": False,
            "holm_p_entry": 1.0,
        },
    ]
    assert params["holm_v11_rule"] == "min(1.0,3.0*raw_primary_p)"
    assert params["v1_probability_contract"] == (
        "exact_labels_1_to_49_open_interval_math.fsum_within_abs_1e-12_of_six"
    )
    assert params["v1_base_source_commit"] == (
        "86549d2650fe98cd48375fa77b5b8521ca271df2"
    )
    for frozen_file in params["v1_base_file_sha256"]:
        path = ROOT / frozen_file["path"]
        assert path.is_file()
        assert sha256(path.read_bytes()).hexdigest() == frozen_file["sha256"]


def test_v11_direct_marginal_formula_and_binary64_oracles_are_literal() -> None:
    params = (
        load_experiment_registry(REGISTRY)
        .get("V11_previous_bonus_carryover")
        .parameters
    )

    assert params["rng_regime_start"] == "2019-05-15"
    assert params["rng_regime_source"] == (
        "official_ALC_first_rng_draw_date_not_outcome_selected"
    )
    assert params["transition_prefix"] == (
        "post_rng_adjacent_source_destination_with_destination_strictly_before_target"
    )
    assert params["current_anchor"] == "immediately_previous_draw_published_bonus"
    assert params["target_bonus_use"] == "prohibited"
    assert params["v1_base_model"] == "ensemble"
    assert params["v1_base_version"] == "v1.0.0"
    assert params["v1_anchor_probability"] == (
        "q_b=original_v1_ensemble_marginal_for_anchor"
    )
    assert params["beta_prior"] == "N(0,1)"
    assert params["beta_score"] == (
        "U(beta)=math.fsum([-beta, *residuals_in_target_date_order])"
    )
    assert params["beta_score_operation_order"] == (
        "construct_chronological_residual_list_then_one_math.fsum_with_"
        "negative_beta_first"
    )
    assert params["root_bracket_radius"] == "B=float(D+64)"
    assert params["root_bisection_iterations"] == 256
    assert params["root_equality_branch"] == "upper"
    assert params["root_early_exit"] == "prohibited"
    assert params["root_bracket_expansion"] == "prohibited"
    assert params["root_return"] == ("lower+(upper-lower)/2.0_after_iteration_256")
    assert params["beta_zero_branch"] == ("D==0_or_U(0.0)==0.0_returns_positive_zero")
    assert params["beta_oracle_q"] == "four_repetitions_of_6_over_49"
    assert params["beta_oracle_y"] == [1, 0, 0, 1]
    assert params["beta_oracle_hex"] == "0x1.e35d1e3820caep-1"
    assert params["beta_oracle_r_hex"] == "0x1.0e5170e3ef9a9p-2"
    assert params["balanced_oracle_beta_hex"] == "0x0.0p+0"

    assert params["anchor_tilt"] == "r_b=sigmoid(logit(q_b)+beta)"
    assert params["positive_branch_anchor"] == "p_b=r_b"
    assert params["positive_branch_nonanchor"] == ("p_i=q_i*(6-r_b)/(6-q_b)")
    assert params["negative_branch_anchor"] == "p_b=r_b"
    assert params["negative_branch_nonanchor"] == ("p_i=q_i+(q_b-r_b)*(1-q_i)/(42+q_b)")
    assert params["negative_branch_denominator_identity"] == (
        "math.fsum(1-q_i_for_i_not_b)=42+q_b"
    )
    assert params["feature_off_identity"] == (
        "beta_positive_zero_or_r_b_equals_q_b_returns_original_v1_mapping_bitwise"
    )
    assert params["probability_repair"] == "prohibited"
    assert params["probability_sum_absolute_tolerance"] == 1.0e-12
    assert params["ranking_tie_break"] == "probability_desc_number_asc"
    assert params["final_combination"] == "sorted_marginal_top6"
    assert params["final6_maximum_change_from_v1"] == "one_label_replacement"
    assert params["joint_map"] == "prohibited"

    assert params["redistribution_oracle_q_anchor_hex"] == "0x1.999999999999ap-3"
    assert params["redistribution_oracle_q_nonanchor"] == "29/240"
    assert params["redistribution_oracle_positive_beta"] == "math.log(2.0)"
    assert params["redistribution_oracle_positive_anchor_hex"] == (
        "0x1.5555555555555p-2"
    )
    assert params["redistribution_oracle_positive_nonanchor_hex"] == (
        "0x1.e38e38e38e38fp-4"
    )
    assert params["redistribution_oracle_negative_beta"] == "-math.log(2.0)"
    assert params["redistribution_oracle_negative_anchor_hex"] == (
        "0x1.c71c71c71c71ep-4"
    )
    assert params["redistribution_oracle_negative_nonanchor_hex"] == (
        "0x1.f684bda12f685p-4"
    )


def test_v11_pseudo_bonus_control_hash_and_shared_base_are_frozen() -> None:
    registration = load_experiment_registry(REGISTRY).get(
        "V11_previous_bonus_carryover"
    )
    params = registration.parameters

    assert len(registration.negative_controls) == 2
    assert registration.negative_controls[0].kind == ("within_draw_bonus_reassignment")
    assert registration.negative_controls[0].seed == 649
    assert registration.negative_controls[1].kind == ("target_date_seeded_fair_random")
    assert registration.negative_controls[1].seed == 649
    assert params["candidate_control_model"] == (
        "v11_previous_bonus_carryover_pseudo_bonus_control"
    )
    assert params["control_payload_template"] == (
        "lotto649-v11-bonus-anchor-control-v1:649:{ISO-date}:{label}"
    )
    assert params["control_selection"] == (
        "minimum_full_sha256_digest_bytes_then_label_over_source_draw_seven_label_union"
    )
    assert params["control_identity_allowed"] is True
    assert params["control_retry"] == "prohibited"
    assert params["control_target"] == "unchanged_next_six_main_numbers"
    assert params["candidate_control_shared_base"] == (
        "same_original_v1_history_and_same_original_v1_49_marginals"
    )

    union = range(1, 8)
    ranked = sorted(
        union,
        key=lambda label: (
            sha256(
                (f"lotto649-v11-bonus-anchor-control-v1:649:2020-01-01:{label}").encode(
                    "utf-8"
                )
            ).digest(),
            label,
        ),
    )
    winning_label = ranked[0]
    winning_digest = sha256(
        (f"lotto649-v11-bonus-anchor-control-v1:649:2020-01-01:{winning_label}").encode(
            "utf-8"
        )
    ).hexdigest()
    assert winning_label == params["control_oracle_pseudo_bonus"] == 4
    assert (
        winning_digest
        == params["control_oracle_winning_digest"]
        == ("1052da1f3ebf9c1bfe2f06998f13ebc812c01dd08fd9b0b21cc20fd35d0840c8")
    )
    assert params["global_random_conditional_role_audit"] == (
        "deferred_excluded_from_v11.0.0"
    )
    assert params["global_random_conditional_role_audit_runner"] == "prohibited"
    assert params["global_random_conditional_role_audit_gate"] == "none"
    assert params["fair_random_model"] == "random"
    assert params["fair_random_version"] == "v1.0.0"
    assert params["fair_random_seed_formula"] == ("649000000+target_date.toordinal()")
    assert params["fair_random_rng"] == "numpy.random.default_rng"
    assert params["fair_random_jitter"] == (
        "one_Uniform(-1e-9,1e-9)_draw_per_ascending_label"
    )
    assert params["fair_random_probability_base"] == "6/49"
    assert params["fair_random_normalization"] == ("frozen_normalize_expected_six")
    assert params["fair_random_role"] == (
        "descriptive_fair_sanity_control_never_supports_v11"
    )
    assert params["fair_random_null_rule"] == (
        "raw_exact_p_gt_0_05_or_bootstrap_ci_includes_zero"
    )
    assert params["fair_random_gate_scopes"] == [
        "aggregate_621",
        "first_307",
        "second_314",
    ]


def test_v11_gates_evidence_ledger_and_prospective_boundary_are_frozen() -> None:
    registration = load_experiment_registry(REGISTRY).get(
        "V11_previous_bonus_carryover"
    )
    params = registration.parameters

    assert params["scientific_gate_count"] == 10
    assert params["scientific_gate_combination"] == "all_ten_conjunctive"
    assert params["scientific_gates"] == [
        "aggregate_candidate_top12_lift_strictly_positive",
        "aggregate_candidate_holm_adjusted_exact_p_at_most_0.05",
        "aggregate_candidate_top12_bootstrap_lower_strictly_positive",
        "candidate_top12_lift_strictly_positive_in_both_halves",
        (
            "paired_candidate_minus_v1_top12_bootstrap_lower_strictly_"
            "positive_aggregate_and_halves"
        ),
        (
            "paired_candidate_minus_control_top12_bootstrap_lower_strictly_"
            "positive_and_pseudo_bonus_and_random_controls_null_aggregate_"
            "and_halves"
        ),
        "candidate_top6_lift_strictly_positive_aggregate_and_halves",
        (
            "candidate_brier_and_log_loss_no_worse_than_fair_or_v1_by_more_"
            "than_1e-9_aggregate_and_halves"
        ),
        "all_anchor_mechanism_log_g_d_candidate_control_conditions_pass",
        "no_audit_warning",
    ]
    assert params["primary_fair_expectation"] == "72/49"
    assert params["top6_fair_expectation"] == "36/49"
    assert params["top18_fair_expectation"] == "108/49"
    assert params["paired_top12_contrasts"] == [
        "candidate_minus_v1_ensemble",
        "candidate_minus_pseudo_bonus_control",
    ]
    assert params["mechanism_fair_log_gain"] == (
        "log_g=y*log(r_b/(6/49))+(1-y)*log((1-r_b)/(43/49))"
    )
    assert params["mechanism_v1_log_gain"] == (
        "d=y*log(r_b/q_b)+(1-y)*log((1-r_b)/(1-q_b))"
    )
    assert params["mechanism_candidate_aggregate_minimum"] == "log(20)"
    assert params["mechanism_candidate_aggregate_threshold_binary64"] == (
        2.995732273553991
    )
    assert params["mechanism_candidate_halves"] == ("log_g_positive_and_d_positive")
    assert params["mechanism_control_aggregate_maximum"] == (
        "log_g_strictly_less_than_log20"
    )
    assert params["mechanism_candidate_minus_control"] == (
        "log_g_and_d_strictly_positive_aggregate_and_halves"
    )
    assert params["mechanism_scalar_six_set_law"] == (
        "R(S)=r_b/C(48,5)_if_anchor_in_S_else_(1-r_b)/C(48,6)"
    )

    assert params["historical_claim"] == (
        "reports/v11_previous_bonus_carryover_v11.0.0_historical.claim"
    )
    assert params["historical_attempt_ledger"] == (
        "reports/v11_previous_bonus_carryover_v11.0.0_historical.ledger.jsonl"
    )
    assert params["historical_report_json"] == (
        "reports/v11_previous_bonus_carryover_v11.0.0_historical.json"
    )
    assert params["historical_report_markdown"] == (
        "reports/v11_previous_bonus_carryover_v11.0.0_historical.md"
    )
    assert params["per_target_prediction_frozen_durability"] == (
        "append_flush_fsync_before_actual_access"
    )
    assert params["opportunity_models"] == [
        "v11_previous_bonus_carryover",
        "v11_previous_bonus_carryover_pseudo_bonus_control",
        "ensemble_v1.0.0",
        "random_v1.0.0",
    ]
    assert params["opportunity_count_per_target_bounds"] == "1_through_4"
    assert params["opportunity_same_target_deduplication"] == (
        "identical_sorted_final6_counted_once"
    )
    assert params["opportunity_primary_producer"] == (
        "first_registered_opportunity_model_with_identical_sorted_final6"
    )
    assert params["opportunity_bundle_producers"] == (
        "primary_model_name_in_path_and_all_producer_model_names_in_registered_order"
    )
    assert params["opportunity_identical_final6_bundle_count"] == (
        "one_per_target_unique_sorted_final6"
    )
    assert params["opportunity_required_fields"] == (
        "target_primary_producer_model_name_producer_model_names_"
        "producer_forecast_sha256_by_model_final6_actual_hits_chronology_status"
    )
    assert params["opportunity_familywise_fair_probability"] == (
        "-math.expm1(math.fsum(math.log1p(-u_t/13983816)_in_target_date_order))"
    )
    assert params["breakthrough_email_language"] == "Chinese"
    assert params["breakthrough_email_title"] == (
        "🚨 [LOTTO649] 历史严格回测成功预测 6/6"
    )
    assert params["automatic_historical_execution"] == "prohibited"
    assert params["historical_post_claim_failure"] == ("consumed_archive_no_rerun")
    assert params["implementation_source_paths"] == [
        "src/lotto649/models/v11_previous_bonus_carryover.py",
        "src/lotto649/v11_diagnostics.py",
        "tools/run_v11_historical.py",
        "tests/test_v11_previous_bonus_carryover.py",
        "tests/test_v11_diagnostics.py",
    ]
    assert params["required_implementation_status_documentation_paths"] == [
        "docs/CODEX_HANDOFF.md",
        "docs/MODEL_PROTOCOL.md",
        "docs/RESEARCH_ROADMAP.md",
    ]
    assert params["implementation_changed_path_policy"] == (
        "exact_required_five_source_paths_plus_required_three_status_docs"
    )
    assert params["implementation_status_doc_mutation"] == (
        "implemented_not_scored_not_activated_only"
    )

    assert registration.prospective.status == "not_activated"
    assert registration.prospective.role == "shadow"
    assert registration.prospective.minimum_eligible_draws == 208
    assert registration.prospective.freeze_commit is None
    assert registration.prospective.activation_commit is None
    assert registration.prospective.outcomes_known_at_activation is None
    assert registration.prospective.cohort_start is None
    assert params["prospective_exact_eligible_evaluated_draws"] == 208
    assert params["prospective_half_draws"] == 104
    assert params["prospective_status"] == "not_activated"
    assert params["prospective_early_look"] == "prohibited"
    assert params["prospective_extension"] == "prohibited"


def test_v11_research_config_is_a_literal_registry_copy_and_live_is_off() -> None:
    payload = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    registration = load_experiment_registry(REGISTRY).get(
        "V11_previous_bonus_carryover"
    )

    assert payload["project"] == {
        "timezone": "America/Toronto",
        "model_version": "v11.0.0",
        "seed": 649,
    }
    assert payload["backtest"] == {
        "start": "2020-01-01",
        "end": "2025-12-31",
        "min_history_draws": 1,
        "models": [
            "v11_previous_bonus_carryover",
            "v11_previous_bonus_carryover_pseudo_bonus_control",
            "ensemble",
            "random",
        ],
    }
    assert payload["live"] == {
        "enabled": False,
        "models": [],
        "shadow_models": [],
    }
    assert payload["notifications"]["enabled"] is False
    assert payload["data"]["processed_csv"] == registration.dataset_path
    assert payload["data"]["registered_source_commit"] == (
        registration.dataset_source_commit
    )
    assert payload["data"]["registered_sha256"] == registration.dataset_sha256
    assert payload["data"]["registered_draw_count"] == (registration.dataset_draw_count)
    assert payload["data"]["registered_history_through"] == (
        registration.registration_history_through.isoformat()
    )
    assert dict(registration.parameters) == payload["research"]


def test_v11_is_absent_from_production_and_automatic_workflows() -> None:
    production = yaml.safe_load(DEFAULT_CONFIG.read_text(encoding="utf-8"))
    production_models = {
        *production["backtest"]["models"],
        *production["live"]["models"],
        *production["live"]["shadow_models"],
    }
    assert not any(name.startswith("v11_") for name in production_models)

    workflow_paths = sorted((*WORKFLOWS.glob("*.yml"), *WORKFLOWS.glob("*.yaml")))
    workflow_text = "\n".join(
        path.read_text(encoding="utf-8") for path in workflow_paths
    )
    assert "research-v11" not in workflow_text
    assert "run_v11" not in workflow_text
