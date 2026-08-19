from __future__ import annotations

from datetime import date
from hashlib import sha256
from pathlib import Path

import yaml

from lotto649.research_protocol import load_experiment_registry


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs" / "experiments" / "registry.yaml"
CONFIG = ROOT / "config" / "research-v10-adjacent-pair-structure.yaml"
DEFAULT_CONFIG = ROOT / "config.yaml"
WORKFLOWS = ROOT / ".github" / "workflows"


def test_v10_registration_freezes_one_unscored_adjacent_pair_variant() -> None:
    registration = load_experiment_registry(REGISTRY).get(
        "V10_adjacent_pair_structure"
    )

    assert registration.family == "structural_set_features"
    assert registration.model_name == "v10_adjacent_pair_structure"
    assert registration.model_version == "v10.0.0"
    assert registration.status == "registered"
    assert registration.registration_file == (
        "docs/experiments/V10_adjacent_pair_structure.md"
    )
    assert registration.registered_on == date(2026, 8, 19)
    assert registration.seed == 649
    assert registration.primary_metric == "top12_hits_lift_vs_theory"
    # V5 pre-registered every future pair/co-occurrence attempt in this
    # append-only family.  V10 is structurally different, but its statistic is
    # still a sum over 48 same-draw label pairs, so it cannot reset multiplicity.
    assert registration.multiplicity_family == "v5_pair_cooccurrence"
    assert registration.variant_index == 2
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
        "90177c80cfb070038d79508fb2e73305a297f516"
    )
    assert registration.outcomes_known_sha256 == registration.dataset_sha256
    assert registration.outcomes_known_draw_count == 4432
    assert registration.outcomes_known_through == date(2026, 8, 15)

    params = registration.parameters
    assert params["evidence_lane"] == "consumed_historical_diagnostic"
    assert params["historical_target_start"] == "2020-01-01"
    assert params["historical_target_end"] == "2025-12-31"
    assert params["historical_target_count"] == 621
    assert params["history_window"] == "complete_expanding_verified_prefix"
    assert params["minimum_history_draws"] == 1
    assert params["adjacency_definition"] == "sorted_main_gap_exactly_one"
    assert params["adjacency_wrap_49_to_1"] is False
    assert params["fair_category_counts"] == [
        7059052,
        5430040,
        1357510,
        132440,
        4730,
        44,
    ]
    assert params["fair_mean_adjacency"] == "30/49"
    assert params["fair_variance_adjacency"] == "2365/4802"
    assert params["model_family"] == "one_parameter_exponential_tilt"
    assert params["parameter_estimator"] == "conjugate_prior_map_plugin"
    assert params["prior_strength_fair_draw_equivalents"] == 1
    assert params["moment_integer_numerator"] == "49*sum_A+30"
    assert params["moment_integer_denominator"] == "49*(D+1)"
    assert params["moment_binary64_conversion"] == "CPython_int_true_division"
    assert params["moment_comparison_operand"] == "binary64_m"
    assert params["moment_fraction_or_cross_multiply"] == "prohibited"
    assert params["moment_D2_T2_numerator"] == 128
    assert params["moment_D2_T2_denominator"] == 147
    assert params["moment_D2_T2_binary64_hex"] == "0x1.bdd2b899406f7p-1"
    assert params["moment_D2_T2_theta_hex"] == "0x1.d4c61abbdd33cp-2"
    assert params["root_bracket"] == [-64.0, 64.0]
    assert params["root_bisection_iterations"] == 256
    assert params["root_equality_branch"] == "upper"
    assert params["root_early_exit"] == "prohibited"
    assert params["root_bracket_expansion"] == "prohibited"
    assert params["numerical_arithmetic"] == "ieee754_binary64"
    assert params["numerical_summation"] == "math.fsum_ascending_a"
    assert params["exact_fair_bypass"] == "49*sum_A==30*D"
    assert params["exact_fair_bypass_logZ"] == "math.log(13983816)"
    assert params["exact_fair_bypass_logZ_hex"] == "0x1.07412c1f4cc68p+4"
    assert params["exact_fair_bypass_joint_log_gain"] == "0x0.0p+0"
    assert params["marginal_count_table_canonicalization"] == (
        "json_compact_rows_labels_1_to_49_columns_adjacency_0_to_5"
    )
    assert params["marginal_count_table_sha256"] == (
        "7d14a90bc388cb0e02dda77ff315a1662492c2cb44f6d5497e297354804d781b"
    )
    assert params["marginal_numerator"] == (
        "math.fsum_exp_log_N_ai_plus_a_theta_minus_ell_max_ascending_a"
    )
    assert params["marginal_denominator"] == "partition_W_same_ell_max"
    assert params["marginal_ratio_shortcut"] == "prohibited"
    assert params["marginal_oracle_theta_neg_1_3_label_1_hex"] == (
        "0x1.0e2c39c67edaep-3"
    )
    assert params["reflection_probability_comparison"] == (
        "exact_binary64_equality"
    )
    assert params["joint_structure_metric"] == (
        "complete_set_prequential_log_score_advantage_vs_fair"
    )
    assert params["joint_structure_gate_role"] == (
        "mandatory_conjunctive_non_primary"
    )
    assert params["joint_candidate_aggregate_log_evalue_minimum"] == "log(20)"
    assert params["joint_control_aggregate_log_evalue_maximum"] == "log(20)"
    assert params["joint_half_candidate_log_gain"] == "strictly_positive"
    assert params["joint_candidate_minus_control_log_gain"] == (
        "strictly_positive_aggregate_and_halves"
    )
    assert params["joint_control_half_sums"] == "report_only_no_threshold"
    assert params["joint_per_target_operation_order"] == (
        "theta_times_A_minus_logZ_plus_log_fair_total"
    )
    assert params["joint_scope_target_order"] == "target_date_ascending"
    assert params["joint_scope_summation"] == "math.fsum"
    assert params["joint_delta_construction"] == (
        "per_target_candidate_minus_control_then_math_fsum"
    )
    assert params["final_combination"] == "sorted_marginal_top6"
    assert params["joint_map"] == "prohibited"
    assert params["ranking_tie_break"] == "probability_desc_number_asc"
    assert params["full_ranking_required"] is True
    assert params["hit_histogram_keys"] == [0, 1, 2, 3, 4, 5, 6]
    assert params["calibration_bins"] == 10
    assert params["calibration_bin_edges"] == (
        "fixed_equal_width_0_to_1_last_bin_right_closed"
    )
    assert params["calibration_outputs"] == (
        "count_mean_forecast_observed_inclusion_rate_ece"
    )
    assert params["calibration_role"] == "descriptive_not_a_decision_gate"
    assert params["performance_by_year"] == "required_descriptive"
    assert params["performance_by_regime"] == (
        "fixed_halves_only_no_posthoc_regimes"
    )
    assert params["prediction_timestamp_field"] == "prediction_frozen_at_utc"
    assert params["prediction_timestamp_format"] == "rfc3339_utc_Z"
    assert params["prediction_timestamp_role"] == (
        "audit_metadata_never_model_input"
    )
    assert params["historical_one_shot"] is True
    assert params["historical_claim_retention"] == "permanent_success_or_failure"
    assert params["historical_claim"] == (
        "reports/v10_adjacent_pair_structure_v10.0.0_historical.claim"
    )
    assert params["historical_report_json"] == (
        "reports/v10_adjacent_pair_structure_v10.0.0_historical.json"
    )
    assert params["historical_report_markdown"] == (
        "reports/v10_adjacent_pair_structure_v10.0.0_historical.md"
    )
    assert params["historical_prediction_freeze"] == (
        "deterministic_forecast_payload_sha256_in_timestamped_event_before_actual_access"
    )
    assert params["forecast_payload_timestamp"] == "excluded"
    assert params["forecast_payload_determinism"] == (
        "byte_for_byte_repeated_calls"
    )
    assert params["per_target_event_order"] == (
        "prediction_frozen_then_target_revealed_scored"
    )
    assert params["per_target_prediction_frozen_durability"] == (
        "append_flush_fsync_before_actual_access"
    )
    assert params["per_target_actual_access"] == (
        "prohibited_before_durable_prediction_frozen_event"
    )
    assert params["per_target_scored_durability"] == (
        "append_flush_fsync_before_next_target"
    )
    assert params["runtime_python"] == "CPython_3.12"
    assert params["runtime_lock_path"] == "requirements-live.lock"
    assert params["runtime_lock_sha256"] == (
        "2fea4cf73cc2578b73c21e6600e31ad843bd903e8a2656b7a2543164ab8d801c"
    )
    assert params["breakthrough_historical_6of6_status"] == (
        "historical-6of6-candidate"
    )
    assert params["breakthrough_stop_v10_scoring_on_final6_6of6"] is True
    assert params["breakthrough_stop_global_search"] == "audit_clear_only"
    assert params["breakthrough_leakage_audit"] == "mandatory_immediate"
    assert params["breakthrough_audit_clear_required_for_success"] is True
    assert params["breakthrough_audit_failure_terminal"] == (
        "historical_6of6_candidate_archived_leakage_failed"
    )
    assert params["breakthrough_bundle_leakage_audit"] == (
        "complete_result_required_before_publication"
    )
    assert params["breakthrough_email_language"] == "Chinese"
    assert params["breakthrough_email_title"] == (
        "🚨 [LOTTO649] 历史严格回测成功预测 6/6"
    )
    assert params["breakthrough_email_failure_policy"] == (
        "preserve_evidence_and_emit_warning"
    )
    assert params["breakthrough_audit_failure_email_title"] == (
        "⚠️ [LOTTO649] 历史 6/6 候选泄漏审计失败"
    )
    assert params["breakthrough_bundle_publication"] == (
        "staged_fsynced_exclusive_no_overwrite"
    )
    assert params["breakthrough_normal_621_report"] == (
        "prohibited_after_early_stop"
    )
    assert params["historical_terminal_success_states"] == [
        "published_after_exactly_621_scored_targets",
        "historical_6of6_candidate_published_after_at_least_1_scored_target",
    ]
    assert params["historical_terminal_failure_states"] == [
        "failed",
        "historical_6of6_candidate_archived_leakage_failed",
    ]
    assert params["new_within_run_final6_record_minimum_hits"] == 2
    assert params["all_scientific_gates_passed_alert"] == (
        "immediate_after_durable_report"
    )
    assert params["primary_exact_test"] == (
        "hypergeometric_draw_level_convolution_upper_tail"
    )
    assert params["bootstrap_replicates"] == 10000
    assert params["bootstrap_rng"] == "numpy.default_rng"
    assert params["bootstrap_seed"] == 649
    assert params["bootstrap_interval"] == (
        "two_sided_95_percentile_linear"
    )
    assert params["holm_family_size_at_registration"] == 2
    assert params["proper_score_max_delta_vs_fair"] == 1.0e-9
    assert params["v1_formal_gate"] == (
        "candidate_aggregate_top12_mean_strictly_above_ensemble"
    )
    assert params["v1_comparison_scope"] == "all_v1_production_models_reported"
    assert params["targeted_control_kind"] == "frozen_global_label_bijection"
    assert params["targeted_control_spec_location"] == (
        "research_parameters_due_frozen_protocol_enum"
    )
    assert params["control_payload_template"] == (
        "lotto649-v10-adjacency-control-v1:649:{source-label}"
    )
    assert params["control_map_sha256"] == (
        "c533509f258e0bb8bdd9fabac8a017ee689e07af0f1d6daf4d36ee63873c0562"
    )
    assert len(params["control_map_destinations_by_source"]) == 49
    assert params["control_map_destinations_by_source"][0] == 3
    assert params["control_map_destinations_by_source"][-1] == 49
    assert params["control_target"] == "unchanged"
    assert params["control_bonus"] == "excluded"
    assert params["control_seed_retries"] == "prohibited"

    ranked_sources = sorted(
        range(1, 50),
        key=lambda source: (
            sha256(
                f"lotto649-v10-adjacency-control-v1:649:{source}".encode()
            ).digest(),
            source,
        ),
    )
    generated = [0] * 49
    for destination, source in enumerate(ranked_sources, start=1):
        generated[source - 1] = destination
    assert generated == params["control_map_destinations_by_source"]
    canonical = ",".join(
        f"{source}:{destination}"
        for source, destination in enumerate(generated, start=1)
    )
    assert canonical == params["control_map_canonical"]
    assert sha256(canonical.encode()).hexdigest() == params["control_map_sha256"]
    assert params["comparison_reference_report"] == (
        "reports/v8_spectral_phase_v8.0.0_historical.json"
    )
    assert params["comparison_reference_report_sha256"] == (
        "e9b51a5316811cbde2b06c36bb61ffffd04b283a4c886cb9ac213bb8fb7deed5"
    )
    assert params["prospective_exact_eligible_evaluated_draws"] == 208
    assert params["prospective_half_draws"] == 104
    assert params["prospective_early_look"] == "prohibited"
    assert params["prospective_extension"] == "prohibited"

    assert len(registration.negative_controls) == 1
    assert registration.negative_controls[0].kind == "target_date_seeded_fair_random"
    assert registration.negative_controls[0].seed == 649
    assert registration.prospective.status == "not_activated"
    assert registration.prospective.role == "shadow"
    assert registration.prospective.minimum_eligible_draws == 208
    assert registration.prospective.freeze_commit is None
    assert registration.prospective.activation_commit is None
    assert registration.prospective.outcomes_known_at_activation is None
    assert registration.prospective.cohort_start is None


def test_v10_research_config_isolated_from_live_models() -> None:
    payload = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    registration = load_experiment_registry(REGISTRY).get(
        "V10_adjacent_pair_structure"
    )

    assert payload["project"]["model_version"] == "v10.0.0"
    assert payload["project"]["seed"] == 649
    assert payload["backtest"] == {
        "start": "2020-01-01",
        "end": "2025-12-31",
        "min_history_draws": 1,
        "models": [
            "v10_adjacent_pair_structure",
            "v10_adjacency_label_bijection_control",
            "random",
        ],
    }
    assert payload["live"] == {
        "enabled": False,
        "models": [],
        "shadow_models": [],
    }
    assert payload["notifications"]["enabled"] is False
    assert payload["data"]["processed_csv"] == "data/processed/draws.csv"
    assert payload["data"]["registered_source_commit"] == (
        registration.dataset_source_commit
    )
    assert payload["data"]["registered_sha256"] == registration.dataset_sha256
    assert payload["data"]["registered_draw_count"] == (
        registration.dataset_draw_count
    )
    assert payload["data"]["registered_history_through"] == (
        registration.registration_history_through.isoformat()
    )
    assert payload["research"]["experiment_id"] == "V10_adjacent_pair_structure"
    assert payload["research"]["historical_target_count"] == 621
    assert payload["research"]["full_ranking_required"] is True
    assert payload["research"]["hit_histogram_keys"] == [0, 1, 2, 3, 4, 5, 6]
    assert dict(registration.parameters) == payload["research"]


def test_v10_is_absent_from_production_and_automatic_workflows() -> None:
    production = yaml.safe_load(DEFAULT_CONFIG.read_text(encoding="utf-8"))
    production_models = {
        *production["backtest"]["models"],
        *production["live"]["models"],
        *production["live"]["shadow_models"],
    }
    assert not any(name.startswith("v10_") for name in production_models)

    workflow_paths = sorted((*WORKFLOWS.glob("*.yml"), *WORKFLOWS.glob("*.yaml")))
    workflow_text = "\n".join(
        path.read_text(encoding="utf-8") for path in workflow_paths
    )
    assert "research-v10" not in workflow_text
    assert "run_v10_adjacent_pair_structure" not in workflow_text
