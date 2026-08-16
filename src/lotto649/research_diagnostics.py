from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import date
import json
from hashlib import sha256
from math import comb, fsum, log
import os
from pathlib import Path
import subprocess
from typing import Any

import numpy as np
import pandas as pd
import yaml

from .backtest import run_backtest
from .config import resolve_path
from .data import load_draws
from .models.v6_entropy_regime import analyze_entropy_regime
from .research_protocol import (
    OutcomeBoundary,
    VerifiedOutcomeBoundary,
    file_sha256,
    load_experiment_registry,
    permute_draw_outcomes,
    validated_registered_draw_prefix,
    walk_forward_folds,
)


EXPERIMENT_ID = "V5_pair_affinity"
CANDIDATE_NAME = "v5_pair_affinity"
REQUIRED_COMPARISON_MODELS = (
    "random",
    "long_frequency",
    "recent_frequency",
    "ema_gap",
    "logistic",
    "ensemble",
    "v3_boosting",
    CANDIDATE_NAME,
)
FAIR_P = 6.0 / 49.0
FAIR_EXPECTATIONS = {6: 36.0 / 49.0, 12: 72.0 / 49.0, 18: 108.0 / 49.0}
EVALUATION_LOG_LOSS_EPSILON = 1.0e-12
MAX_BINARY_LOG_LOSS = max(
    -log(EVALUATION_LOG_LOSS_EPSILON),
    -log(1.0 - (1.0 - EVALUATION_LOG_LOSS_EPSILON)),
)


def _conditional_role_lr_from_counts(
    main_counts: np.ndarray,
    bonus_counts: np.ndarray,
) -> float:
    terms: list[float] = []
    for main_count, bonus_count in zip(main_counts, bonus_counts):
        selected_count = int(main_count + bonus_count)
        if selected_count == 0:
            continue
        if main_count:
            terms.append(
                int(main_count)
                * log(int(main_count) / (6.0 * selected_count / 7.0))
            )
        if bonus_count:
            terms.append(
                int(bonus_count)
                * log(int(bonus_count) / (selected_count / 7.0))
            )
    return 2.0 * fsum(terms)


def conditional_role_likelihood_ratio(draws) -> float:
    """Return the registered conditional main:bonus 6:1 likelihood ratio."""
    from .research_protocol import validate_draw_chronology

    validate_draw_chronology(draws)
    main_counts = np.zeros(49, dtype=np.int64)
    bonus_counts = np.zeros(49, dtype=np.int64)
    for draw in draws:
        for number in draw.numbers:
            main_counts[number - 1] += 1
        bonus_counts[draw.bonus - 1] += 1
    return _conditional_role_lr_from_counts(main_counts, bonus_counts)


def role_audit_monte_carlo(
    draws,
    *,
    randomizations: int = 10_000,
    seed: int = 649,
) -> dict[str, Any]:
    """Calibrate the registered role statistic by within-draw reassignment."""
    from .research_protocol import validate_draw_chronology

    if randomizations < 1:
        raise ValueError("randomizations must be positive")
    if seed < 0:
        raise ValueError("seed must be non-negative")
    validate_draw_chronology(draws)
    observed = conditional_role_likelihood_ratio(draws)
    seven_sets = [tuple(sorted((*draw.numbers, draw.bonus))) for draw in draws]
    rng = np.random.default_rng(seed)
    exceedances = 0
    for _ in range(randomizations):
        main_counts = np.zeros(49, dtype=np.int64)
        bonus_counts = np.zeros(49, dtype=np.int64)
        for seven in seven_sets:
            bonus_index = int(rng.integers(0, 7))
            for index, number in enumerate(seven):
                if index == bonus_index:
                    bonus_counts[number - 1] += 1
                else:
                    main_counts[number - 1] += 1
        randomized = _conditional_role_lr_from_counts(main_counts, bonus_counts)
        if randomized >= observed:
            exceedances += 1
    return {
        "statistic": observed,
        "randomizations": randomizations,
        "seed": seed,
        "right_tail_exceedances": exceedances,
        "plus_one_right_tail_p": (1 + exceedances) / (randomizations + 1),
    }


def v7_historical_decision(
    payload: dict[str, Any],
    *,
    proper_score_tolerance: float,
) -> tuple[dict[str, Any], list[str]]:
    """Apply the complete frozen V7 historical gate without rescue metrics."""
    candidate = payload["candidate"]
    halves = payload["stability_halves"]
    control_summaries = [
        payload["negative_control"],
        *payload["negative_control_halves"],
    ]
    candidate_summaries = [candidate, *(half["candidate"] for half in halves)]
    warnings = list(payload.get("audit_warnings", ()))
    warnings.extend(
        f"negative_control_non_null:{index}"
        for index, summary in enumerate(control_summaries)
        if not summary["behaves_as_null"]
    )
    gates = {
        "positive_aggregate_primary_lift": (
            candidate["primary_top12_lift_vs_theory"] > 0.0
        ),
        "aggregate_holm_adjusted_p_at_most_0_05": (
            candidate["primary_holm_adjusted_p"] <= 0.05
        ),
        "aggregate_bootstrap_lower_above_zero": (
            candidate["primary_bootstrap_95_ci"][0] > 0.0
        ),
        "positive_primary_lift_in_both_fixed_halves": all(
            half["candidate"]["primary_top12_lift_vs_theory"] > 0.0
            for half in halves
        ),
        "proper_scores_within_fair_tolerance_aggregate_and_halves": all(
            summary["brier_delta_vs_fair"] <= proper_score_tolerance
            and summary["log_loss_delta_vs_fair"] <= proper_score_tolerance
            for summary in candidate_summaries
        ),
        "global_role_audit_p_at_most_0_05": (
            payload["global_role_audit"]["plus_one_right_tail_p"] <= 0.05
        ),
        "negative_control_null_aggregate_and_halves": all(
            summary["behaves_as_null"] for summary in control_summaries
        ),
        "audit_clear": not warnings,
    }
    all_pass = all(gates.values())
    return (
        {
            "decision": (
                "eligible_for_reviewed_shadow_activation" if all_pass else "reject"
            ),
            "historical_primary_signal_supported": all_pass,
            "proper_score_max_delta_vs_fair": proper_score_tolerance,
            "gates": gates,
            "all_gates_passed": all_pass,
            "shadow_activation": "not_activated",
        },
        warnings,
    )

V6_EXPERIMENT_ID = "V6_fixed_boundary_js_regime"
V6_CANDIDATE_NAME = "v6_entropy_regime"
V6_MODEL_VERSION = "v6.0.0"
V6_REFERENCE_EXPERIMENT_ID = "V5_pair_affinity"
V6_RESEARCH_CONFIG_PATH = Path("config/research-v6-entropy-regime.yaml")
V6_REFERENCE_MODEL_VERSIONS = (
    ("random", "v1.0.0"),
    ("long_frequency", "v1.0.0"),
    ("recent_frequency", "v1.0.0"),
    ("ema_gap", "v1.0.0"),
    ("logistic", "v1.0.0"),
    ("ensemble", "v1.0.0"),
    ("v3_boosting", "v1.0.0"),
    ("v5_pair_affinity", "v5.0.0"),
)

V7_EXPERIMENT_ID = "V7_post_rng_main_bonus_role_bias"
V7_CANDIDATE_NAME = "v7_main_bonus_role_bias"
V7_CONTROL_NAME = "v7_main_bonus_role_control"
V7_MODEL_VERSION = "v7.0.0"
V7_REFERENCE_EXPERIMENT_ID = "V6_fixed_boundary_js_regime"
V7_RESEARCH_CONFIG_PATH = Path("config/research-v7-main-bonus-role-bias.yaml")
V7_REFERENCE_MODEL_VERSIONS = (
    ("random", "v1.0.0"),
    ("long_frequency", "v1.0.0"),
    ("recent_frequency", "v1.0.0"),
    ("ema_gap", "v1.0.0"),
    ("logistic", "v1.0.0"),
    ("ensemble", "v1.0.0"),
    ("v3_boosting", "v1.0.0"),
    ("v5_pair_affinity", "v5.0.0"),
    ("v6_entropy_regime", "v6.0.0"),
)
V7_TARGET_START = date(2020, 1, 1)
V7_TARGET_END = date(2025, 12, 31)
V7_RNG_START = date(2019, 5, 15)
V7_ACTIVE_MINIMUM = 104
V7_REPORT_STEM = "v7_main_bonus_role_bias_v7.0.0_historical"
V7_HALF_RANGES = (
    ("2020_2022", date(2020, 1, 1), date(2022, 12, 31), 307),
    ("2023_2025", date(2023, 1, 1), date(2025, 12, 31), 314),
)
V7_EXPECTED_PARAMETERS = {
    "post_rng_start_date": "2019-05-15",
    "active_minimum_post_rng_prior_draws": 104,
    "history_window": "expanding_post_rng",
    "main_role_pseudocount": 3.0,
    "bonus_role_pseudocount": 0.5,
    "pseudocount_prior": "seven_role_dirichlet_half",
    "fair_conditional_main_bonus_odds": 6.0,
    "signal": "log_smoothed_main_bonus_odds_minus_log_6",
    "fair_fallback": "exact_constant_6_over_49",
    "all_zero_signal_behavior": "exact_constant_6_over_49",
    "probability_link": "stable_sigmoid",
    "intercept_constraint": "sum_probabilities_equals_6",
    "intercept_solver": "deterministic_bisection",
    "bisection_lower": "negative_64_minus_max_abs_signal",
    "bisection_upper": "positive_64_plus_max_abs_signal",
    "bisection_iterations": 256,
    "bisection_requires_strict_bracket": True,
    "bisection_endpoint_clipping": "prohibited",
    "probability_sum_absolute_tolerance": 1.0e-12,
    "output_labels": "integers_1_through_49",
    "training": "none",
    "calibration": "none",
    "signal_scale": "none",
    "combination_constraints": "none",
    "ensemble_members": "none",
    "historical_bonus_input": "strictly_lagged_post_rng_only",
    "target_bonus_input": "prohibited",
    "revealed_target_bonus_audit": "global_role_audit_only",
    "scoring_target": "six_main_numbers_only",
    "historical_primary_gate_lane": "consumed_diagnostic",
    "historical_target_start": "2020-01-01",
    "historical_target_end": "2025-12-31",
    "historical_target_count": 621,
    "post_rng_burn_in_draw_count_through_2019": 65,
    "historical_fair_fallback_target_count": 39,
    "historical_active_target_count": 582,
    "first_historical_active_target": "2020-05-20",
    "historical_development_status": "not_applicable",
    "historical_legacy_validation_status": "not_applicable",
    "stability_half_1_start": "2020-01-01",
    "stability_half_1_end": "2022-12-31",
    "stability_half_1_target_count": 307,
    "stability_half_2_start": "2023-01-01",
    "stability_half_2_end": "2025-12-31",
    "stability_half_2_target_count": 314,
    "primary_exact_test": "hypergeometric_draw_level_convolution_upper_tail",
    "bootstrap_replicates": 10_000,
    "bootstrap_rng": "numpy.default_rng",
    "bootstrap_seed": 649,
    "bootstrap_interval": "two_sided_95_percentile_linear",
    "proper_score_max_delta_vs_fair": 1.0e-9,
    "global_role_audit_statistic": "conditional_6_to_1_likelihood_ratio",
    "global_role_audit_start": "2019-05-15",
    "global_role_audit_end": "2025-12-31",
    "global_role_audit_zero_term": "zero",
    "global_role_audit_randomizations": 10_000,
    "global_role_audit_rng": "numpy.default_rng",
    "global_role_audit_seed": 649,
    "global_role_audit_p_value": "plus_one_right_tail",
    "global_role_audit_max_p": 0.05,
    "control_scope": "predict_history_only",
    "control_rng_reinitialized_per_prediction": True,
    "control_post_rng_draws": "exactly_one_sorted_seven_role_choice_per_draw",
    "control_target_outcome": "unchanged",
    "prospective_exact_eligible_evaluated_draws": 208,
    "prospective_half_draws": 104,
    "prospective_early_look": "prohibited",
    "prospective_extension": "prohibited",
    "reference_report": "reports/v6_entropy_regime_v6.0.0_historical.json",
    "reference_report_sha256": (
        "12400a4b5164b030225827d47a8024a1ec7aeaeb32fa64cd2fab0b46ff8d4c2a"
    ),
}
V7_EXPECTED_RESEARCH_CONFIG = {
    "experiment_id": V7_EXPERIMENT_ID,
    "family": "draw_role_exchangeability",
    "variant_index": 1,
    "post_rng_start_date": "2019-05-15",
    "active_minimum_post_rng_prior_draws": 104,
    "main_role_pseudocount": 3.0,
    "bonus_role_pseudocount": 0.5,
    "revealed_target_bonus_audit": "global_role_audit_only",
    "probability_sum_absolute_tolerance": 1.0e-12,
    "bisection_iterations": 256,
    "historical_target_count": 621,
    "post_rng_burn_in_draw_count_through_2019": 65,
    "historical_fair_fallback_target_count": 39,
    "historical_active_target_count": 582,
    "first_historical_active_target": "2020-05-20",
    "stability_halves": [
        {"start": "2020-01-01", "end": "2022-12-31", "target_count": 307},
        {"start": "2023-01-01", "end": "2025-12-31", "target_count": 314},
    ],
    "bootstrap_replicates": 10_000,
    "global_role_audit_randomizations": 10_000,
    "negative_control": "within_draw_bonus_reassignment",
    "prospective_exact_eligible_evaluated_draws": 208,
    "prospective_half_draws": 104,
    "reference_report": "reports/v6_entropy_regime_v6.0.0_historical.json",
    "reference_report_sha256": (
        "12400a4b5164b030225827d47a8024a1ec7aeaeb32fa64cd2fab0b46ff8d4c2a"
    ),
}


@dataclass(frozen=True)
class HistoricalLane:
    name: str
    start: date
    end: date
    interpretation: str


HISTORICAL_LANES = (
    HistoricalLane(
        "development",
        date(1982, 1, 1),
        date(2014, 12, 31),
        "historical development diagnostic only",
    ),
    HistoricalLane(
        "legacy_validation",
        date(2015, 1, 1),
        date(2019, 12, 31),
        "exposed historical validation diagnostic",
    ),
    HistoricalLane(
        "consumed_diagnostic",
        date(2020, 1, 1),
        date(2025, 12, 31),
        "consumed historical diagnostic; never blind or confirmatory",
    ),
)


def _configuration_manifest(cfg: dict) -> dict[str, Any]:
    effective = {
        key: deepcopy(value)
        for key, value in cfg.items()
        if not str(key).startswith("_")
    }
    canonical = json.dumps(
        effective,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode()
    config_path = cfg.get("_config_path")
    if config_path is None:
        source = "in-memory"
        source_sha256 = sha256(canonical).hexdigest()
    else:
        path = Path(config_path)
        root = Path(cfg["_root"])
        try:
            source = str(path.relative_to(root))
        except ValueError:
            source = str(path)
        source_sha256 = file_sha256(path)
    return {
        "source": source,
        "source_sha256": source_sha256,
        "effective_sha256": sha256(canonical).hexdigest(),
        "effective": effective,
    }


def single_draw_topk_pmf(k: int) -> np.ndarray:
    if not 0 <= k <= 49:
        raise ValueError("k must be between 0 and 49")
    denominator = comb(49, 6)
    probabilities = np.zeros(7, dtype=float)
    for hits in range(7):
        if hits <= k and 6 - hits <= 49 - k:
            probabilities[hits] = comb(k, hits) * comb(49 - k, 6 - hits) / denominator
    return probabilities


def exact_topk_upper_tail(total_hits: int, draw_count: int, k: int = 12) -> float:
    if draw_count < 1:
        raise ValueError("draw_count must be positive")
    if total_hits <= 0:
        return 1.0
    if total_hits > 6 * draw_count:
        return 0.0

    one_draw = single_draw_topk_pmf(k)
    distribution = np.array([1.0])
    for _ in range(draw_count):
        active = len(distribution)
        updated = np.zeros(active + 6, dtype=float)
        for hits, probability in enumerate(one_draw):
            if probability:
                updated[hits : hits + active] += probability * distribution
        distribution = updated
    return float(np.clip(np.sum(distribution[total_hits:]), 0.0, 1.0))


def bootstrap_mean_lift_interval(
    hits: np.ndarray,
    expectation: float,
    *,
    resamples: int = 10_000,
    seed: int = 649,
    chunk_size: int = 256,
) -> tuple[float, float]:
    values = np.asarray(hits, dtype=float)
    if values.ndim != 1 or len(values) == 0:
        raise ValueError("hits must be a non-empty one-dimensional array")
    if resamples < 1 or chunk_size < 1:
        raise ValueError("resamples and chunk_size must be positive")

    rng = np.random.default_rng(seed)
    lifts = np.empty(resamples, dtype=float)
    for start in range(0, resamples, chunk_size):
        stop = min(start + chunk_size, resamples)
        sample_indices = rng.integers(0, len(values), size=(stop - start, len(values)))
        lifts[start:stop] = values[sample_indices].mean(axis=1) - expectation
    lower, upper = np.quantile(lifts, [0.025, 0.975], method="linear")
    return float(lower), float(upper)


def fair_constant_scores() -> tuple[float, float]:
    brier = (6 * (1.0 - FAIR_P) ** 2 + 43 * FAIR_P**2) / 49
    log_loss = -(6 * log(FAIR_P) + 43 * log(1.0 - FAIR_P)) / 49
    return brier, log_loss


def _model_summary(frame: pd.DataFrame, model_name: str) -> dict[str, Any]:
    rows = frame.loc[frame["model_name"] == model_name]
    if rows.empty:
        raise ValueError(f"missing diagnostic rows for {model_name}")
    versions = sorted(set(rows["model_version"]))
    if len(versions) != 1:
        raise ValueError(f"multiple versions found for {model_name}: {versions}")
    return {
        "model_name": model_name,
        "model_version": versions[0],
        "draws": int(len(rows)),
        "avg_top6_hits": float(rows["top_6_hits"].mean()),
        "avg_top12_hits": float(rows["top_12_hits"].mean()),
        "avg_top18_hits": float(rows["top_18_hits"].mean()),
        "avg_brier": float(rows["brier_score"].mean()),
        "avg_log_loss": float(rows["log_loss"].mean()),
        "avg_actual_rank": float(rows["mean_actual_rank"].mean()),
    }


def registered_primary_summary(
    frame: pd.DataFrame,
    model_name: str = CANDIDATE_NAME,
    *,
    multiplicity_family_size: int = 1,
    bootstrap_resamples: int = 10_000,
    bootstrap_seed: int = 649,
) -> dict[str, Any]:
    rows = frame.loc[frame["model_name"] == model_name]
    if rows.empty:
        raise ValueError(f"missing primary rows for {model_name}")
    hits = rows["top_12_hits"].to_numpy(dtype=int)
    total_hits = int(hits.sum())
    raw_p = exact_topk_upper_tail(total_hits, len(hits), 12)
    lower, upper = bootstrap_mean_lift_interval(
        hits,
        FAIR_EXPECTATIONS[12],
        resamples=bootstrap_resamples,
        seed=bootstrap_seed,
    )
    fair_brier, fair_log_loss = fair_constant_scores()
    summary = _model_summary(frame, model_name)
    summary.update(
        {
            "total_top12_hits": total_hits,
            "top6_lift_vs_theory": summary["avg_top6_hits"] - FAIR_EXPECTATIONS[6],
            "primary_top12_lift_vs_theory": (
                summary["avg_top12_hits"] - FAIR_EXPECTATIONS[12]
            ),
            "top18_lift_vs_theory": summary["avg_top18_hits"] - FAIR_EXPECTATIONS[18],
            "primary_exact_one_sided_p": raw_p,
            "primary_holm_adjusted_p": min(1.0, multiplicity_family_size * raw_p),
            "primary_bootstrap_95_ci": [lower, upper],
            "fair_constant_brier": fair_brier,
            "fair_constant_log_loss": fair_log_loss,
            "brier_delta_vs_fair": summary["avg_brier"] - fair_brier,
            "log_loss_delta_vs_fair": summary["avg_log_loss"] - fair_log_loss,
        }
    )
    return summary


def _eligible_target_count(draws, lane: HistoricalLane, minimum_history: int) -> tuple[int, int]:
    total = 0
    eligible = 0
    for index, draw in enumerate(draws):
        if lane.start <= draw.draw_date <= lane.end:
            total += 1
            if index >= minimum_history:
                eligible += 1
    return total, eligible


def _lane_payload(
    normal_frame: pd.DataFrame,
    control_frame: pd.DataFrame,
    lane: HistoricalLane,
    *,
    total_targets: int,
    eligible_targets: int,
    multiplicity_family_size: int,
) -> dict[str, Any]:
    comparisons = [_model_summary(normal_frame, name) for name in REQUIRED_COMPARISON_MODELS]
    if any(item["draws"] != eligible_targets for item in comparisons):
        raise RuntimeError(f"incomplete comparison rows in {lane.name}")
    candidate = registered_primary_summary(
        normal_frame,
        multiplicity_family_size=multiplicity_family_size,
    )
    control = registered_primary_summary(
        control_frame,
        multiplicity_family_size=multiplicity_family_size,
    )
    control["behaves_as_null"] = not (
        control["primary_exact_one_sided_p"] <= 0.05
        and control["primary_bootstrap_95_ci"][0] > 0.0
    )
    return {
        "lane": lane.name,
        "dates": {"start": lane.start.isoformat(), "end": lane.end.isoformat()},
        "interpretation": lane.interpretation,
        "total_targets": total_targets,
        "eligible_targets": eligible_targets,
        "excluded_before_minimum_history": total_targets - eligible_targets,
        "candidate": candidate,
        "negative_control": control,
        "comparisons": comparisons,
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# V5 Pair-Affinity Historical Diagnostic",
        "",
        "Status: historical diagnostic only. No result in this report is blind,",
        "confirmatory, prospective, or sufficient for production promotion.",
        "",
        f"- Experiment: `{payload['experiment_id']}` / `{payload['model_version']}`",
        f"- Frozen implementation commit: `{payload['code_commit']}`",
        f"- Dataset SHA-256: `{payload['dataset']['sha256']}`",
        f"- Research config: `{payload['configuration']['source']}`",
        f"- Research config SHA-256: `{payload['configuration']['source_sha256']}`",
        f"- Effective config SHA-256: `{payload['configuration']['effective_sha256']}`",
        f"- Negative-control seed: `{payload['negative_control_seed']}`",
        "- Primary metric: mean Top-12 hits lift versus exact `72/49`",
        "",
        "## Registered lane results",
        "",
        "| Lane | Draws | Top-12 | Lift | Exact one-sided p | Holm p | 95% bootstrap CI | Control lift | Control null? |",
        "|---|---:|---:|---:|---:|---:|---|---:|---|",
    ]
    for lane in payload["lanes"]:
        candidate = lane["candidate"]
        control = lane["negative_control"]
        ci = candidate["primary_bootstrap_95_ci"]
        lines.append(
            "| {lane} | {draws} | {top12:.6f} | {lift:+.6f} | {p:.6g} | "
            "{holm:.6g} | [{lower:+.6f}, {upper:+.6f}] | {control_lift:+.6f} | {null} |".format(
                lane=lane["lane"],
                draws=candidate["draws"],
                top12=candidate["avg_top12_hits"],
                lift=candidate["primary_top12_lift_vs_theory"],
                p=candidate["primary_exact_one_sided_p"],
                holm=candidate["primary_holm_adjusted_p"],
                lower=ci[0],
                upper=ci[1],
                control_lift=control["primary_top12_lift_vs_theory"],
                null="yes" if control["behaves_as_null"] else "NO — AUDIT REQUIRED",
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation boundary",
            "",
            "All signs, proper scores, operational comparisons, and negative-control",
            "results are retained in the JSON companion report. Historical outcomes",
            "cannot activate or promote the model. Any behavior change made after",
            "reading this report requires a new version and new prospective cohort.",
            "",
        ]
    )
    return "\n".join(lines)


def run_registered_v5_diagnostics(
    cfg: dict,
    *,
    code_commit: str,
    output_dir: Path,
) -> dict[str, Any]:
    if len(code_commit) != 40 or any(c not in "0123456789abcdef" for c in code_commit):
        raise ValueError("code_commit must be a full lowercase Git SHA")

    root = Path(cfg["_root"])
    registry = load_experiment_registry(root / "docs" / "experiments" / "registry.yaml")
    registration = registry.get(EXPERIMENT_ID)
    dataset_path = resolve_path(cfg, cfg["data"]["processed_csv"])
    draws = load_draws(dataset_path)
    registered_draws = validated_registered_draw_prefix(
        dataset_path,
        draws,
        expected_sha256=registration.dataset_sha256,
        draw_count=registration.dataset_draw_count,
        history_through=registration.registration_history_through,
    )

    configured_models = tuple(cfg["backtest"].get("models", []))
    if configured_models != REQUIRED_COMPARISON_MODELS:
        raise RuntimeError("research config comparison set differs from the registration")
    if cfg["backtest"].get("model_versions", {}).get(CANDIDATE_NAME) != registration.model_version:
        raise RuntimeError("candidate model version differs from the registration")

    family_size = sum(
        item.multiplicity_family == registration.multiplicity_family
        for item in registry.experiments
    )
    minimum_history = int(registration.parameters["minimum_history_draws"])
    control_draws = permute_draw_outcomes(registered_draws, seed=registration.seed)
    control_cfg = deepcopy(cfg)
    control_cfg["backtest"]["models"] = [CANDIDATE_NAME]

    lane_payloads = []
    for lane in HISTORICAL_LANES:
        normal_frame = run_backtest(registered_draws, cfg, lane.start, lane.end)
        control_frame = run_backtest(control_draws, control_cfg, lane.start, lane.end)
        total_targets, eligible_targets = _eligible_target_count(
            registered_draws, lane, minimum_history
        )
        lane_payloads.append(
            _lane_payload(
                normal_frame,
                control_frame,
                lane,
                total_targets=total_targets,
                eligible_targets=eligible_targets,
                multiplicity_family_size=family_size,
            )
        )

    payload = {
        "schema_version": 1,
        "experiment_id": registration.experiment_id,
        "model_name": registration.model_name,
        "model_version": registration.model_version,
        "status": "historical_diagnostic_complete",
        "evidence_warning": (
            "All lanes are historical diagnostics; none is blind, confirmatory, or prospective."
        ),
        "code_commit": code_commit,
        "command": (
            "lotto649 --config config/research-v5-pair-affinity.yaml "
            f"research-v5 --code-commit {code_commit}"
        ),
        "comparison_models": list(REQUIRED_COMPARISON_MODELS),
        "configuration": _configuration_manifest(cfg),
        "dataset": {
            "path": registration.dataset_path,
            "source_commit": registration.dataset_source_commit,
            "sha256": registration.dataset_sha256,
            "draw_count": registration.dataset_draw_count,
            "history_through": registration.registration_history_through.isoformat(),
        },
        "negative_control_seed": registration.seed,
        "registered_parameters": dict(registration.parameters),
        "multiplicity_family": registration.multiplicity_family,
        "multiplicity_family_size": family_size,
        "lanes": lane_payloads,
        "prospective_cohort": "not_activated",
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "v5_pair_affinity_v5.0.0_historical.json"
    markdown_path = output_dir / "v5_pair_affinity_v5.0.0_historical.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    markdown_path.write_text(_render_markdown(payload), encoding="utf-8")
    return {"json_path": str(json_path), "markdown_path": str(markdown_path), "report": payload}


def _require_full_git_sha(value: str, field: str) -> None:
    if len(value) != 40 or any(character not in "0123456789abcdef" for character in value):
        raise ValueError(f"{field} must be a full lowercase Git SHA")


def _read_v6_git_audit_state(root: Path) -> tuple[str, str]:
    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        tracked_status = subprocess.run(
            ["git", "status", "--porcelain=v1", "--untracked-files=all"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.rstrip("\n")
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        raise RuntimeError("unable to audit the local Git state for V6") from exc
    return head, tracked_status


def _validate_v6_git_audit(root: Path, code_commit: str) -> None:
    head, tracked_status = _read_v6_git_audit_state(root)
    if code_commit != head:
        raise RuntimeError("V6 code_commit must equal the local Git HEAD")
    if tracked_status:
        raise RuntimeError("V6 worktree must be completely clean before scoring")


def _read_v6_committed_file_bytes(
    root: Path,
    code_commit: str,
    relative_path: Path,
) -> bytes:
    try:
        return subprocess.run(
            ["git", "show", f"{code_commit}:{relative_path.as_posix()}"],
            cwd=root,
            check=True,
            capture_output=True,
        ).stdout
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        raise RuntimeError(
            f"unable to read committed V6 file: {relative_path.as_posix()}"
        ) from exc


def _validated_v6_configuration_manifest(
    root: Path,
    cfg: dict,
    code_commit: str,
) -> dict[str, Any]:
    config_value = cfg.get("_config_path")
    if config_value is None:
        raise RuntimeError("V6 scoring requires the canonical research config path")
    expected_path = (root / V6_RESEARCH_CONFIG_PATH).resolve()
    try:
        actual_path = Path(config_value).resolve(strict=True)
    except OSError as exc:
        raise RuntimeError("V6 research config file is missing") from exc
    if actual_path != expected_path:
        raise RuntimeError("V6 scoring requires the canonical research config path")

    disk_bytes = actual_path.read_bytes()
    committed_bytes = _read_v6_committed_file_bytes(
        root,
        code_commit,
        V6_RESEARCH_CONFIG_PATH,
    )
    if disk_bytes != committed_bytes:
        raise RuntimeError("V6 research config differs from the committed Git blob")
    try:
        committed_config = yaml.safe_load(committed_bytes.decode("utf-8"))
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        raise RuntimeError("committed V6 research config is not valid UTF-8 YAML") from exc
    effective = {
        key: deepcopy(value)
        for key, value in cfg.items()
        if not str(key).startswith("_")
    }
    manifest = _configuration_manifest(cfg)
    if committed_config != effective:
        raise RuntimeError("loaded V6 config differs from the committed Git blob")
    return manifest


def _registered_dataset_identity(registration) -> dict[str, Any]:
    return {
        "path": registration.dataset_path,
        "source_commit": registration.dataset_source_commit,
        "sha256": registration.dataset_sha256,
        "draw_count": registration.dataset_draw_count,
        "history_through": registration.registration_history_through.isoformat(),
    }


def _known_outcomes_identity(registration) -> dict[str, Any]:
    return {
        "source_commit": registration.outcomes_known_source_commit,
        "sha256": registration.outcomes_known_sha256,
        "draw_count": registration.outcomes_known_draw_count,
        "history_through": registration.outcomes_known_through.isoformat(),
    }


def _validate_v6_outcome_boundaries(root: Path, registration):
    diagnostic_boundary = OutcomeBoundary(
        source_commit=registration.dataset_source_commit,
        sha256=registration.dataset_sha256,
        draw_count=registration.dataset_draw_count,
        history_through=registration.registration_history_through,
    )
    known_boundary = OutcomeBoundary(
        source_commit=registration.outcomes_known_source_commit,
        sha256=registration.outcomes_known_sha256,
        draw_count=registration.outcomes_known_draw_count,
        history_through=registration.outcomes_known_through,
    )
    evidence = VerifiedOutcomeBoundary.from_repository(
        root,
        known_boundary,
        registration_boundary=diagnostic_boundary,
    )
    if evidence.path != registration.dataset_path:
        raise RuntimeError("V6 outcome boundary path differs from the registration")
    return evidence


def _validate_v6_registration_and_config(cfg: dict, registration) -> None:
    if (
        registration.experiment_id != V6_EXPERIMENT_ID
        or registration.model_name != V6_CANDIDATE_NAME
        or registration.model_version != V6_MODEL_VERSION
    ):
        raise RuntimeError("V6 registration identity mismatch")
    if registration.status != "registered":
        raise RuntimeError("V6 registration status must be registered before scoring")
    registered_minimum_history = registration.parameters.get("minimum_history_draws")
    if registered_minimum_history != 300:
        raise RuntimeError("V6 minimum history must remain exactly 300")
    if tuple(cfg["backtest"].get("models", ())) != (V6_CANDIDATE_NAME,):
        raise RuntimeError("V6 research config must run only v6_entropy_regime")
    if (
        cfg["backtest"].get("model_versions", {}).get(V6_CANDIDATE_NAME)
        != registration.model_version
    ):
        raise RuntimeError("V6 research config model version mismatch")
    if cfg.get("project", {}).get("model_version") != registration.model_version:
        raise RuntimeError("V6 project model version mismatch")
    if cfg["backtest"].get("min_history_draws") != registered_minimum_history:
        raise RuntimeError("V6 minimum history differs from the registration")
    if list(cfg["backtest"].get("top_k", ())) != [6, 12, 18]:
        raise RuntimeError("V6 research config must retain Top-6/12/18 scoring")
    if int(cfg.get("project", {}).get("seed", -1)) != registration.seed:
        raise RuntimeError("V6 project seed differs from the registration")
    if cfg.get("live") != {
        "enabled": False,
        "models": [],
        "shadow_models": [],
    }:
        raise RuntimeError("V6 research config must disable the live path")
    controls = tuple(registration.negative_controls)
    if len(controls) != 1 or controls[0].kind != "whole_draw_date_permutation":
        raise RuntimeError("V6 must retain its sole whole-draw date-permutation control")
    if controls[0].seed != registration.seed:
        raise RuntimeError("V6 negative-control seed differs from the registration")
    if registration.parameters.get("historical_primary_gate_lane") != "consumed_diagnostic":
        raise RuntimeError("V6 historical Holm gate lane differs from the registration")
    if registration.prospective.status != "not_activated":
        raise RuntimeError("V6 prospective cohort must remain not_activated")
    if registration.prospective.freeze_commit is not None:
        raise RuntimeError("an unactivated V6 cohort cannot have a freeze commit")
    if getattr(registration.prospective, "activation_commit", None) is not None:
        raise RuntimeError("an unactivated V6 cohort cannot have an activation commit")
    if (
        getattr(registration.prospective, "outcomes_known_at_activation", None)
        is not None
    ):
        raise RuntimeError("an unactivated V6 cohort cannot have an activation boundary")
    if registration.prospective.cohort_start is not None:
        raise RuntimeError("an unactivated V6 cohort cannot have a start date")


def _reference_error(message: str) -> RuntimeError:
    return RuntimeError(f"frozen V5 reference {message}")


def _validate_reference_summary(
    summary: Any,
    *,
    expected_name: str,
    expected_version: str,
    eligible_targets: int,
) -> None:
    if not isinstance(summary, dict):
        raise _reference_error("summary must be an object")
    if summary.get("model_name") != expected_name:
        raise _reference_error(f"model name mismatch for {expected_name}")
    if summary.get("model_version") != expected_version:
        raise _reference_error(f"model version mismatch for {expected_name}")
    if summary.get("draws") != eligible_targets:
        raise _reference_error(f"row count mismatch for {expected_name}")


def _load_validated_v5_reference(
    root: Path,
    registration,
    reference_registration,
    registered_draws,
) -> tuple[dict[str, Any], Path, str]:
    reference_value = registration.parameters.get("reference_report")
    expected_sha256 = registration.parameters.get("reference_report_sha256")
    if not isinstance(reference_value, str) or not reference_value:
        raise RuntimeError("V6 registration is missing its reference report path")
    if (
        not isinstance(expected_sha256, str)
        or len(expected_sha256) != 64
        or any(character not in "0123456789abcdef" for character in expected_sha256)
    ):
        raise RuntimeError("V6 registration has an invalid reference report SHA-256")
    if reference_registration.result is None:
        raise _reference_error("registration has no frozen result")
    v6_minimum_history = registration.parameters["minimum_history_draws"]
    if reference_registration.parameters.get("minimum_history_draws") != v6_minimum_history:
        raise _reference_error("V5 registry minimum history differs from V6")
    if reference_value != reference_registration.result.report_json:
        raise _reference_error("path differs from the V5 result registration")

    reference_path = resolve_path({"_root": root}, reference_value)
    if not reference_path.is_file():
        raise _reference_error("report file is missing")
    actual_sha256 = file_sha256(reference_path)
    if actual_sha256 != expected_sha256:
        raise RuntimeError("reference report fingerprint mismatch")
    try:
        payload = json.loads(reference_path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _reference_error("is not valid UTF-8 JSON") from exc
    if not isinstance(payload, dict):
        raise _reference_error("root must be an object")

    expected_identity = {
        "schema_version": 1,
        "experiment_id": reference_registration.experiment_id,
        "model_name": reference_registration.model_name,
        "model_version": reference_registration.model_version,
        "code_commit": reference_registration.result.implementation_commit,
    }
    for field, expected in expected_identity.items():
        if payload.get(field) != expected:
            raise _reference_error(f"{field} mismatch")
    if reference_registration.experiment_id != V6_REFERENCE_EXPERIMENT_ID:
        raise _reference_error("registry experiment identity mismatch")

    v6_dataset = _registered_dataset_identity(registration)
    v5_dataset = _registered_dataset_identity(reference_registration)
    if v5_dataset != v6_dataset:
        raise _reference_error("registration dataset differs from V6")
    if payload.get("dataset") != v6_dataset:
        raise _reference_error("report dataset identity mismatch")

    report_parameters = payload.get("registered_parameters")
    if (
        not isinstance(report_parameters, dict)
        or report_parameters.get("minimum_history_draws") != v6_minimum_history
    ):
        raise _reference_error("registered minimum history differs from V6")
    report_configuration = payload.get("configuration")
    try:
        reference_config_minimum = report_configuration["effective"]["backtest"][
            "min_history_draws"
        ]
    except (KeyError, TypeError):
        raise _reference_error("effective config minimum history is missing") from None
    if reference_config_minimum != v6_minimum_history:
        raise _reference_error("effective config minimum history differs from V6")

    expected_names = [name for name, _version in V6_REFERENCE_MODEL_VERSIONS]
    if payload.get("comparison_models") != expected_names:
        raise _reference_error("comparison model set mismatch")
    reference_lanes = payload.get("lanes")
    if not isinstance(reference_lanes, list) or len(reference_lanes) != len(
        HISTORICAL_LANES
    ):
        raise _reference_error("lane set mismatch")

    minimum_history = v6_minimum_history
    for lane, lane_payload in zip(HISTORICAL_LANES, reference_lanes):
        if not isinstance(lane_payload, dict) or lane_payload.get("lane") != lane.name:
            raise _reference_error("lane order or name mismatch")
        expected_dates = {
            "start": lane.start.isoformat(),
            "end": lane.end.isoformat(),
        }
        if lane_payload.get("dates") != expected_dates:
            raise _reference_error(f"lane dates mismatch for {lane.name}")
        total_targets, eligible_targets = _eligible_target_count(
            registered_draws, lane, minimum_history
        )
        expected_counts = {
            "total_targets": total_targets,
            "eligible_targets": eligible_targets,
            "excluded_before_minimum_history": total_targets - eligible_targets,
        }
        for field, expected in expected_counts.items():
            if lane_payload.get(field) != expected:
                raise _reference_error(f"{field} mismatch for {lane.name}")

        comparisons = lane_payload.get("comparisons")
        if not isinstance(comparisons, list) or len(comparisons) != len(
            V6_REFERENCE_MODEL_VERSIONS
        ):
            raise _reference_error(f"comparison summaries mismatch for {lane.name}")
        for summary, (model_name, model_version) in zip(
            comparisons, V6_REFERENCE_MODEL_VERSIONS
        ):
            _validate_reference_summary(
                summary,
                expected_name=model_name,
                expected_version=model_version,
                eligible_targets=eligible_targets,
            )
        _validate_reference_summary(
            lane_payload.get("candidate"),
            expected_name="v5_pair_affinity",
            expected_version="v5.0.0",
            eligible_targets=eligible_targets,
        )
    return payload, reference_path, actual_sha256


def _eligible_target_dates(draws, lane: HistoricalLane, minimum_history: int) -> list[str]:
    return [
        fold.target.draw_date.isoformat()
        for fold in walk_forward_folds(draws, lane.start, lane.end, minimum_history)
    ]


def _validate_v6_frame(
    frame: pd.DataFrame,
    *,
    lane: HistoricalLane,
    expected_target_dates: list[str],
) -> None:
    required_columns = {
        "target_draw_date",
        "model_name",
        "model_version",
        "top_6_hits",
        "top_12_hits",
        "top_18_hits",
        "brier_score",
        "log_loss",
        "mean_actual_rank",
    }
    missing = required_columns - set(frame.columns)
    if missing:
        raise RuntimeError(f"V6 backtest missing columns in {lane.name}: {sorted(missing)}")
    if len(frame) != len(expected_target_dates):
        raise RuntimeError(f"V6 backtest row count mismatch in {lane.name}")
    if set(frame["model_name"]) != {V6_CANDIDATE_NAME}:
        raise RuntimeError(f"V6 backtest model identity mismatch in {lane.name}")
    if set(frame["model_version"]) != {V6_MODEL_VERSION}:
        raise RuntimeError(f"V6 backtest model version mismatch in {lane.name}")
    actual_dates = [str(value) for value in frame["target_draw_date"]]
    if actual_dates != expected_target_dates:
        raise RuntimeError(f"V6 backtest target dates mismatch in {lane.name}")

    try:
        hits = frame[["top_6_hits", "top_12_hits", "top_18_hits"]].to_numpy(
            dtype=float
        )
    except (TypeError, ValueError) as exc:
        raise RuntimeError(
            f"V6 hit counts must be finite integers in {lane.name}"
        ) from exc
    if not np.isfinite(hits).all() or not np.equal(hits, np.floor(hits)).all():
        raise RuntimeError(f"V6 hit counts must be finite integers in {lane.name}")
    if np.any(hits < 0.0) or np.any(hits > 6.0):
        raise RuntimeError(f"V6 hit counts must be between 0 and 6 in {lane.name}")
    if np.any(hits[:, 0] > hits[:, 1]) or np.any(hits[:, 1] > hits[:, 2]):
        raise RuntimeError(
            f"V6 hit counts must satisfy Top-6 <= Top-12 <= Top-18 in {lane.name}"
        )

    try:
        proper_scores = frame[["brier_score", "log_loss"]].to_numpy(dtype=float)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(
            f"V6 proper scores must be finite and non-negative in {lane.name}"
        ) from exc
    if not np.isfinite(proper_scores).all() or np.any(proper_scores < 0.0):
        raise RuntimeError(
            f"V6 proper scores must be finite and non-negative in {lane.name}"
        )

    try:
        actual_ranks = frame["mean_actual_rank"].to_numpy(dtype=float)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(
            f"V6 mean actual rank must be finite and between 1 and 49 in {lane.name}"
        ) from exc
    if (
        not np.isfinite(actual_ranks).all()
        or np.any(actual_ranks < 1.0)
        or np.any(actual_ranks > 49.0)
    ):
        raise RuntimeError(
            f"V6 mean actual rank must be finite and between 1 and 49 in {lane.name}"
        )


def _activation_summary(draws, lane: HistoricalLane, minimum_history: int) -> dict[str, Any]:
    folds = tuple(
        walk_forward_folds(draws, lane.start, lane.end, minimum_history)
    )
    active_targets = sum(
        analyze_entropy_regime(list(fold.history), fold.target.draw_date).active
        for fold in folds
    )
    eligible_targets = len(folds)
    return {
        "eligible_targets": eligible_targets,
        "active_targets": active_targets,
        "inactive_targets": eligible_targets - active_targets,
        "activation_rate": active_targets / eligible_targets if eligible_targets else 0.0,
    }


def _v6_lane_payload(
    normal_frame: pd.DataFrame,
    control_frame: pd.DataFrame,
    lane: HistoricalLane,
    *,
    total_targets: int,
    eligible_targets: int,
    family_size: int,
    reference_comparisons: list[dict[str, Any]],
    candidate_activation: dict[str, Any],
    control_activation: dict[str, Any],
) -> dict[str, Any]:
    is_holm_lane = lane.name == "consumed_diagnostic"
    candidate = registered_primary_summary(
        normal_frame,
        model_name=V6_CANDIDATE_NAME,
        multiplicity_family_size=family_size if is_holm_lane else 1,
    )
    if not is_holm_lane:
        candidate["primary_holm_adjusted_p"] = None
    control = registered_primary_summary(
        control_frame,
        model_name=V6_CANDIDATE_NAME,
        multiplicity_family_size=1,
    )
    control["primary_holm_adjusted_p"] = None
    control["behaves_as_null"] = not (
        control["primary_exact_one_sided_p"] <= 0.05
        and control["primary_bootstrap_95_ci"][0] > 0.0
    )
    return {
        "lane": lane.name,
        "dates": {"start": lane.start.isoformat(), "end": lane.end.isoformat()},
        "interpretation": lane.interpretation,
        "total_targets": total_targets,
        "eligible_targets": eligible_targets,
        "excluded_before_minimum_history": total_targets - eligible_targets,
        "candidate_activation": candidate_activation,
        "control_activation": control_activation,
        "candidate": candidate,
        "negative_control": control,
        "comparisons": deepcopy(reference_comparisons) + [deepcopy(candidate)],
    }


def _v6_historical_decision(
    lanes: list[dict[str, Any]],
    *,
    proper_score_tolerance: float,
) -> tuple[dict[str, Any], list[str]]:
    consumed = next(lane for lane in lanes if lane["lane"] == "consumed_diagnostic")
    positive_all_lanes = all(
        lane["candidate"]["primary_top12_lift_vs_theory"] > 0.0 for lane in lanes
    )
    consumed_holm = consumed["candidate"]["primary_holm_adjusted_p"] <= 0.05
    consumed_ci = consumed["candidate"]["primary_bootstrap_95_ci"][0] > 0.0
    proper_scores = all(
        lane["candidate"]["brier_delta_vs_fair"] <= proper_score_tolerance
        and lane["candidate"]["log_loss_delta_vs_fair"] <= proper_score_tolerance
        for lane in lanes
    )
    controls_null = all(lane["negative_control"]["behaves_as_null"] for lane in lanes)
    audit_warnings = [
        f"negative_control_non_null:{lane['lane']}"
        for lane in lanes
        if not lane["negative_control"]["behaves_as_null"]
    ]
    gates = {
        "positive_primary_lift_all_lanes": positive_all_lanes,
        "consumed_holm_adjusted_p_at_most_0_05": consumed_holm,
        "consumed_bootstrap_lower_above_zero": consumed_ci,
        "proper_scores_within_fair_tolerance_all_lanes": proper_scores,
        "negative_controls_null_all_lanes": controls_null,
        "audit_clear": not audit_warnings,
    }
    all_pass = all(gates.values())
    return (
        {
            "decision": (
                "eligible_for_reviewed_shadow_activation" if all_pass else "reject"
            ),
            "historical_primary_signal_supported": all_pass,
            "holm_gate_lane": "consumed_diagnostic",
            "proper_score_max_delta_vs_fair": proper_score_tolerance,
            "gates": gates,
            "all_gates_passed": all_pass,
            "shadow_activation": "not_activated",
        },
        audit_warnings,
    )


def _render_v6_markdown(payload: dict[str, Any]) -> str:
    diagnostic = payload["data_boundaries"]["historical_diagnostic_prefix"]
    known = payload["data_boundaries"]["outcomes_known_at_registration"]
    reference = payload["reference_provenance"]
    decision = payload["historical_decision"]
    lines = [
        "# V6 Fixed-Boundary Entropy-Regime Historical Diagnostic",
        "",
        "Status: historical diagnostic only. No result here is blind, confirmatory,",
        "prospective, or an automatic shadow/production promotion.",
        "",
        f"- Experiment: `{payload['experiment_id']}` / `{payload['model_version']}`",
        f"- Frozen implementation commit: `{payload['code_commit']}`",
        f"- Exact command: `{payload['command']}`",
        f"- Diagnostic prefix: {diagnostic['draw_count']} draws through "
        f"`{diagnostic['history_through']}` (`{diagnostic['sha256']}`)",
        f"- Outcomes known at registration: {known['draw_count']} draws through "
        f"`{known['history_through']}` (`{known['sha256']}`)",
        "- Data-boundary Git verification: passed; registered prefix preserved",
        f"- Reused V5 reference: `{reference['path']}` (`{reference['sha256']}`)",
        f"- Research config: `{payload['configuration']['source']}`",
        f"- Effective config SHA-256: `{payload['configuration']['effective_sha256']}`",
        "- Primary metric: mean Top-12 hits lift versus exact `72/49`",
        "- Sole historical Holm gate: consumed diagnostic lane",
        "",
        "## Registered lane results",
        "",
        "| Lane | Draws | Active | Top-12 | Lift | Raw p | Holm p | 95% CI | Brier delta | Log-loss delta | Control active | Control lift | Control null? |",
        "|---|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---|",
    ]
    for lane in payload["lanes"]:
        candidate = lane["candidate"]
        control = lane["negative_control"]
        ci = candidate["primary_bootstrap_95_ci"]
        holm = candidate["primary_holm_adjusted_p"]
        holm_text = f"{holm:.6g}" if holm is not None else "n/a"
        lines.append(
            "| {lane} | {draws} | {active} | {top12:.6f} | {lift:+.6f} | "
            "{raw_p:.6g} | {holm} | [{lower:+.6f}, {upper:+.6f}] | "
            "{brier:+.6g} | {log_loss:+.6g} | {control_active} | "
            "{control_lift:+.6f} | {control_null} |".format(
                lane=lane["lane"],
                draws=candidate["draws"],
                active=lane["candidate_activation"]["active_targets"],
                top12=candidate["avg_top12_hits"],
                lift=candidate["primary_top12_lift_vs_theory"],
                raw_p=candidate["primary_exact_one_sided_p"],
                holm=holm_text,
                lower=ci[0],
                upper=ci[1],
                brier=candidate["brier_delta_vs_fair"],
                log_loss=candidate["log_loss_delta_vs_fair"],
                control_active=lane["control_activation"]["active_targets"],
                control_lift=control["primary_top12_lift_vs_theory"],
                control_null="yes" if control["behaves_as_null"] else "NO — AUDIT",
            )
        )
    lines.extend(
        [
            "",
            "## Frozen historical decision",
            "",
            f"Decision: **{decision['decision']}**. Prospective status remains "
            "**not_activated**.",
            "",
        ]
    )
    for gate, passed in decision["gates"].items():
        lines.append(f"- `{gate}`: {'pass' if passed else 'fail'}")
    lines.extend(
        [
            "",
            "The JSON companion retains every secondary metric, the complete reused",
            "comparison summaries, activation counts, control results, hashes, and",
            "provenance. Any behavior change after reading these outcomes requires a",
            "new model version and a new prospective cohort.",
            "",
        ]
    )
    return "\n".join(lines)


def run_registered_v6_diagnostics(
    cfg: dict,
    *,
    code_commit: str,
    output_dir: Path,
) -> dict[str, Any]:
    """Run the single frozen V6 diagnostic without recomputing old comparisons."""
    _require_full_git_sha(code_commit, "code_commit")
    root = Path(cfg["_root"])
    _validate_v6_git_audit(root, code_commit)
    configuration_manifest = _validated_v6_configuration_manifest(
        root,
        cfg,
        code_commit,
    )
    json_path = output_dir / "v6_entropy_regime_v6.0.0_historical.json"
    markdown_path = output_dir / "v6_entropy_regime_v6.0.0_historical.md"
    if json_path.exists() or markdown_path.exists():
        raise RuntimeError("V6 historical report already exists; refusing to overwrite")
    registry = load_experiment_registry(root / "docs" / "experiments" / "registry.yaml")
    registration = registry.get(V6_EXPERIMENT_ID)
    reference_registration = registry.get(V6_REFERENCE_EXPERIMENT_ID)
    _validate_v6_registration_and_config(cfg, registration)
    outcome_evidence = _validate_v6_outcome_boundaries(root, registration)

    dataset_path = resolve_path(cfg, cfg["data"]["processed_csv"])
    draws = load_draws(dataset_path)
    registered_draws = validated_registered_draw_prefix(
        dataset_path,
        draws,
        expected_sha256=registration.dataset_sha256,
        draw_count=registration.dataset_draw_count,
        history_through=registration.registration_history_through,
    )
    reference, reference_path, reference_sha256 = _load_validated_v5_reference(
        root,
        registration,
        reference_registration,
        registered_draws,
    )

    family_size = sum(
        item.multiplicity_family == registration.multiplicity_family
        for item in registry.experiments
    )
    if family_size < 1:
        raise RuntimeError("V6 multiplicity family is empty")
    minimum_history = int(registration.parameters["minimum_history_draws"])
    proper_score_tolerance = float(
        registration.parameters["proper_score_max_delta_vs_fair"]
    )
    if proper_score_tolerance < 0.0:
        raise RuntimeError("V6 proper-score tolerance must be non-negative")

    # All configuration, dataset, registry, and frozen-reference identities above
    # are validated before this first scoring call can occur.
    control_draws = permute_draw_outcomes(registered_draws, seed=registration.seed)
    lane_payloads = []
    for lane, reference_lane in zip(HISTORICAL_LANES, reference["lanes"]):
        expected_target_dates = _eligible_target_dates(
            registered_draws, lane, minimum_history
        )
        candidate_activation = _activation_summary(
            registered_draws, lane, minimum_history
        )
        control_activation = _activation_summary(control_draws, lane, minimum_history)

        normal_frame = run_backtest(registered_draws, cfg, lane.start, lane.end)
        _validate_v6_frame(
            normal_frame,
            lane=lane,
            expected_target_dates=expected_target_dates,
        )
        control_frame = run_backtest(control_draws, cfg, lane.start, lane.end)
        _validate_v6_frame(
            control_frame,
            lane=lane,
            expected_target_dates=expected_target_dates,
        )
        total_targets, eligible_targets = _eligible_target_count(
            registered_draws, lane, minimum_history
        )
        lane_payloads.append(
            _v6_lane_payload(
                normal_frame,
                control_frame,
                lane,
                total_targets=total_targets,
                eligible_targets=eligible_targets,
                family_size=family_size,
                reference_comparisons=reference_lane["comparisons"],
                candidate_activation=candidate_activation,
                control_activation=control_activation,
            )
        )

    historical_decision, audit_warnings = _v6_historical_decision(
        lane_payloads,
        proper_score_tolerance=proper_score_tolerance,
    )
    prospective = registration.prospective
    payload = {
        "schema_version": 2,
        "experiment_id": registration.experiment_id,
        "model_name": registration.model_name,
        "model_version": registration.model_version,
        "status": "historical_diagnostic_complete",
        "evidence_warning": (
            "All lanes are consumed historical diagnostics; none is blind, "
            "confirmatory, or prospective."
        ),
        "code_commit": code_commit,
        "command": (
            "lotto649 --config config/research-v6-entropy-regime.yaml "
            f"research-v6 --code-commit {code_commit}"
        ),
        "comparison_models": [
            *(name for name, _version in V6_REFERENCE_MODEL_VERSIONS),
            V6_CANDIDATE_NAME,
        ],
        "configuration": configuration_manifest,
        "data_boundaries": {
            "historical_diagnostic_prefix": _registered_dataset_identity(registration),
            "outcomes_known_at_registration": _known_outcomes_identity(registration),
        },
        "data_boundary_verification": {
            "git_verified": True,
            "registration_prefix_preserved": (
                outcome_evidence.registration_prefix_preserved
            ),
            "known_outcomes_draws_fingerprint": outcome_evidence.draws_fingerprint,
        },
        "reference_provenance": {
            "path": str(reference_path.relative_to(root)),
            "sha256": reference_sha256,
            "schema_version": reference["schema_version"],
            "experiment_id": reference["experiment_id"],
            "model_name": reference["model_name"],
            "model_version": reference["model_version"],
            "implementation_commit": reference["code_commit"],
            "dataset": deepcopy(reference["dataset"]),
            "reused_models": [name for name, _version in V6_REFERENCE_MODEL_VERSIONS],
            "policy": "frozen summaries reused; reference models were not refitted",
        },
        "registered_parameters": dict(registration.parameters),
        "negative_control": {
            "kind": registration.negative_controls[0].kind,
            "seed": registration.negative_controls[0].seed,
            "scope": "all eligible targets; never active-only",
        },
        "multiplicity_family": registration.multiplicity_family,
        "multiplicity_family_size": family_size,
        "lanes": lane_payloads,
        "historical_decision": historical_decision,
        "audit_warnings": audit_warnings,
        "prospective_cohort": {
            "status": prospective.status,
            "role": prospective.role,
            "minimum_eligible_draws": prospective.minimum_eligible_draws,
            "commit_deadline": prospective.commit_deadline,
            "freeze_commit": prospective.freeze_commit,
            "activation_commit": getattr(prospective, "activation_commit", None),
            "outcomes_known_at_activation": None,
            "cohort_start": (
                prospective.cohort_start.isoformat()
                if prospective.cohort_start is not None
                else None
            ),
        },
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        with json_path.open("x", encoding="utf-8") as handle:
            handle.write(
                json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n"
            )
        with markdown_path.open("x", encoding="utf-8") as handle:
            handle.write(_render_v6_markdown(payload))
    except FileExistsError as exc:
        raise RuntimeError(
            "V6 historical report already exists; refusing to overwrite"
        ) from exc
    return {
        "json_path": str(json_path),
        "markdown_path": str(markdown_path),
        "report": payload,
    }


def _validate_v7_git_audit(root: Path, code_commit: str) -> None:
    head, worktree_status = _read_v6_git_audit_state(root)
    if code_commit != head:
        raise RuntimeError("V7 code_commit must equal the local Git HEAD")
    if worktree_status:
        raise RuntimeError("V7 worktree must be completely clean before scoring")


def _validated_v7_configuration_manifest(
    root: Path,
    cfg: dict,
    code_commit: str,
) -> dict[str, Any]:
    config_value = cfg.get("_config_path")
    if config_value is None:
        raise RuntimeError("V7 scoring requires the canonical research config path")
    expected_path = (root / V7_RESEARCH_CONFIG_PATH).resolve()
    try:
        actual_path = Path(config_value).resolve(strict=True)
    except OSError as exc:
        raise RuntimeError("V7 research config file is missing") from exc
    if actual_path != expected_path:
        raise RuntimeError("V7 scoring requires the canonical research config path")

    disk_bytes = actual_path.read_bytes()
    committed_bytes = _read_v6_committed_file_bytes(
        root,
        code_commit,
        V7_RESEARCH_CONFIG_PATH,
    )
    if disk_bytes != committed_bytes:
        raise RuntimeError("V7 research config differs from the committed Git blob")
    try:
        committed_config = yaml.safe_load(committed_bytes.decode("utf-8"))
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        raise RuntimeError("committed V7 research config is not valid UTF-8 YAML") from exc
    effective = {
        key: deepcopy(value)
        for key, value in cfg.items()
        if not str(key).startswith("_")
    }
    if committed_config != effective:
        raise RuntimeError("loaded V7 config differs from the committed Git blob")
    return _configuration_manifest(cfg)


def _validate_v7_outcome_boundaries(root: Path, registration):
    diagnostic_boundary = OutcomeBoundary(
        source_commit=registration.dataset_source_commit,
        sha256=registration.dataset_sha256,
        draw_count=registration.dataset_draw_count,
        history_through=registration.registration_history_through,
    )
    known_boundary = OutcomeBoundary(
        source_commit=registration.outcomes_known_source_commit,
        sha256=registration.outcomes_known_sha256,
        draw_count=registration.outcomes_known_draw_count,
        history_through=registration.outcomes_known_through,
    )
    evidence = VerifiedOutcomeBoundary.from_repository(
        root,
        known_boundary,
        registration_boundary=diagnostic_boundary,
    )
    if evidence.path != registration.dataset_path:
        raise RuntimeError("V7 outcome boundary path differs from the registration")
    return evidence


def _validate_v7_registration_and_config(cfg: dict, registration) -> None:
    if (
        registration.experiment_id != V7_EXPERIMENT_ID
        or registration.family != "draw_role_exchangeability"
        or registration.model_name != V7_CANDIDATE_NAME
        or registration.model_version != V7_MODEL_VERSION
        or registration.multiplicity_family != "draw_role_exchangeability"
        or registration.variant_index != 1
    ):
        raise RuntimeError("V7 registration identity mismatch")
    if (
        registration.registration_file
        != "docs/experiments/V7_main_bonus_role_bias.md"
        or registration.registered_on != date(2026, 8, 16)
    ):
        raise RuntimeError("V7 registration provenance mismatch")
    if registration.status != "registered" or registration.result is not None:
        raise RuntimeError("V7 must remain an unscored registered experiment")
    if registration.primary_metric != "top12_hits_lift_vs_theory":
        raise RuntimeError("V7 primary metric differs from the registration")
    if registration.seed != 649:
        raise RuntimeError("V7 protocol seed differs from the registration")
    if dict(registration.parameters) != V7_EXPECTED_PARAMETERS:
        raise RuntimeError("V7 registered parameters differ from the frozen protocol")

    expected_project = {
        "timezone": "America/Toronto",
        "model_version": V7_MODEL_VERSION,
        "seed": 649,
    }
    if cfg.get("project") != expected_project:
        raise RuntimeError("V7 project configuration differs from the registration")
    expected_backtest = {
        "min_history_draws": 300,
        "test_start": "2020-01-01",
        "test_end": "2025-12-31",
        "top_k": [6, 12, 18],
        "models": [V7_CANDIDATE_NAME],
        "model_versions": {V7_CANDIDATE_NAME: V7_MODEL_VERSION},
    }
    if cfg.get("backtest") != expected_backtest:
        raise RuntimeError("V7 backtest configuration differs from the registration")
    if cfg.get("research") != V7_EXPECTED_RESEARCH_CONFIG:
        raise RuntimeError("V7 research configuration differs from the registration")
    if cfg.get("data", {}).get("processed_csv") != registration.dataset_path:
        raise RuntimeError("V7 configured dataset path differs from the registration")
    if cfg.get("live") != {
        "enabled": False,
        "models": [],
        "shadow_models": [],
    }:
        raise RuntimeError("V7 research config must disable the live path")
    if cfg.get("notifications", {}).get("enabled") is not False:
        raise RuntimeError("V7 research config must disable notifications")

    controls = tuple(registration.negative_controls)
    if len(controls) != 1 or controls[0].kind != "within_draw_bonus_reassignment":
        raise RuntimeError("V7 control differs from the registered role reassignment")
    if controls[0].seed != 649:
        raise RuntimeError("V7 control seed differs from the registration")
    prospective = registration.prospective
    if (
        prospective.status != "not_activated"
        or prospective.role != "shadow"
        or prospective.minimum_eligible_draws != 208
        or prospective.commit_deadline != "before_target_local_date"
        or prospective.freeze_commit is not None
        or prospective.activation_commit is not None
        or prospective.outcomes_known_at_activation is not None
        or prospective.cohort_start is not None
    ):
        raise RuntimeError("V7 prospective cohort differs from the registration")


def _v7_reference_error(message: str) -> RuntimeError:
    return RuntimeError(f"frozen V6 reference {message}")


def _validate_v7_reference_summary(
    summary: Any,
    *,
    expected_name: str,
    expected_version: str,
) -> None:
    if not isinstance(summary, dict):
        raise _v7_reference_error("comparison summary must be an object")
    expected_identity = {
        "model_name": expected_name,
        "model_version": expected_version,
        "draws": 621,
    }
    for field, expected in expected_identity.items():
        if summary.get(field) != expected:
            raise _v7_reference_error(
                f"comparison {field} mismatch for {expected_name}"
            )
    bounded_fields = {
        "avg_top6_hits": (0.0, 6.0),
        "avg_top12_hits": (0.0, 6.0),
        "avg_top18_hits": (0.0, 6.0),
        "avg_brier": (0.0, float("inf")),
        "avg_log_loss": (0.0, float("inf")),
        "avg_actual_rank": (1.0, 49.0),
    }
    for field, (lower, upper) in bounded_fields.items():
        value = summary.get(field)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise _v7_reference_error(
                f"comparison {field} is invalid for {expected_name}"
            )
        numeric = float(value)
        if not np.isfinite(numeric) or numeric < lower or numeric > upper:
            raise _v7_reference_error(
                f"comparison {field} is invalid for {expected_name}"
            )


def _load_validated_v6_reference_for_v7(
    root: Path,
    code_commit: str,
    registration,
    reference_registration,
) -> tuple[dict[str, Any], Path, str, list[dict[str, Any]]]:
    reference_value = registration.parameters["reference_report"]
    expected_sha256 = registration.parameters["reference_report_sha256"]
    if reference_registration.experiment_id != V7_REFERENCE_EXPERIMENT_ID:
        raise _v7_reference_error("registry experiment identity mismatch")
    if (
        reference_registration.model_name != "v6_entropy_regime"
        or reference_registration.model_version != "v6.0.0"
        or reference_registration.status != "closed_rejected"
        or reference_registration.result is None
        or reference_registration.result.decision != "reject"
    ):
        raise _v7_reference_error("registry result identity mismatch")
    if reference_value != reference_registration.result.report_json:
        raise _v7_reference_error("path differs from the V6 result registration")
    if _registered_dataset_identity(reference_registration) != (
        _registered_dataset_identity(registration)
    ):
        raise _v7_reference_error("registration dataset differs from V7")

    reference_path = resolve_path({"_root": root}, reference_value)
    if not reference_path.is_file():
        raise _v7_reference_error("report file is missing")
    actual_sha256 = file_sha256(reference_path)
    if actual_sha256 != expected_sha256:
        raise RuntimeError("reference report fingerprint mismatch")
    try:
        relative_path = reference_path.resolve(strict=True).relative_to(
            root.resolve(strict=True)
        )
    except (OSError, ValueError) as exc:
        raise _v7_reference_error("report must be inside the repository") from exc
    committed_bytes = _read_v6_committed_file_bytes(
        root,
        code_commit,
        relative_path,
    )
    disk_bytes = reference_path.read_bytes()
    if disk_bytes != committed_bytes:
        raise RuntimeError("V6 reference report differs from the committed Git blob")
    try:
        payload = json.loads(disk_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _v7_reference_error("report is not valid UTF-8 JSON") from exc
    if not isinstance(payload, dict):
        raise _v7_reference_error("report root must be an object")

    expected_identity = {
        "schema_version": 2,
        "experiment_id": reference_registration.experiment_id,
        "model_name": reference_registration.model_name,
        "model_version": reference_registration.model_version,
        "code_commit": reference_registration.result.implementation_commit,
        "status": "historical_diagnostic_complete",
    }
    for field, expected in expected_identity.items():
        if payload.get(field) != expected:
            raise _v7_reference_error(f"{field} mismatch")
    if payload.get("data_boundaries") != {
        "historical_diagnostic_prefix": _registered_dataset_identity(registration),
        "outcomes_known_at_registration": _known_outcomes_identity(registration),
    }:
        raise _v7_reference_error("data-boundary identity mismatch")

    expected_names = [name for name, _version in V7_REFERENCE_MODEL_VERSIONS]
    if payload.get("comparison_models") != expected_names:
        raise _v7_reference_error("comparison model set mismatch")
    lanes = payload.get("lanes")
    if not isinstance(lanes, list) or [lane.get("lane") for lane in lanes] != [
        lane.name for lane in HISTORICAL_LANES
    ]:
        raise _v7_reference_error("lane set mismatch")
    consumed = lanes[-1]
    expected_consumed = {
        "lane": "consumed_diagnostic",
        "dates": {"start": "2020-01-01", "end": "2025-12-31"},
        "total_targets": 621,
        "eligible_targets": 621,
        "excluded_before_minimum_history": 0,
    }
    for field, expected in expected_consumed.items():
        if consumed.get(field) != expected:
            raise _v7_reference_error(f"consumed-lane {field} mismatch")
    comparisons = consumed.get("comparisons")
    if not isinstance(comparisons, list) or len(comparisons) != len(
        V7_REFERENCE_MODEL_VERSIONS
    ):
        raise _v7_reference_error("consumed-lane comparisons mismatch")
    for summary, (model_name, model_version) in zip(
        comparisons,
        V7_REFERENCE_MODEL_VERSIONS,
    ):
        _validate_v7_reference_summary(
            summary,
            expected_name=model_name,
            expected_version=model_version,
        )
    if consumed.get("candidate") != comparisons[-1]:
        raise _v7_reference_error("consumed-lane candidate summary mismatch")
    return payload, reference_path, actual_sha256, deepcopy(comparisons)


def _v7_preflight_targets(draws, minimum_history: int) -> tuple[list, dict[str, Any]]:
    folds = list(
        walk_forward_folds(
            draws,
            V7_TARGET_START,
            V7_TARGET_END,
            minimum_history,
        )
    )
    if len(folds) != 621:
        raise RuntimeError("V7 historical target count must remain exactly 621")
    target_dates = [fold.target.draw_date for fold in folds]
    half_counts = [
        sum(start <= target_date <= end for target_date in target_dates)
        for _name, start, end, _count in V7_HALF_RANGES
    ]
    if half_counts != [307, 314]:
        raise RuntimeError("V7 stability-half counts must remain exactly 307 and 314")

    active_flags = []
    for fold in folds:
        post_rng_count = sum(
            V7_RNG_START <= draw.draw_date < fold.target.draw_date
            for draw in fold.history
        )
        active_flags.append(post_rng_count >= V7_ACTIVE_MINIMUM)
    active_dates = [
        target_date
        for target_date, active in zip(target_dates, active_flags)
        if active
    ]
    fallback_count = active_flags.count(False)
    if (
        fallback_count != 39
        or len(active_dates) != 582
        or not active_dates
        or active_dates[0] != date(2020, 5, 20)
    ):
        raise RuntimeError(
            "V7 activation counts must remain 39 fallback, 582 active, "
            "first active 2020-05-20"
        )
    return folds, {
        "eligible_targets": len(folds),
        "fair_fallback_targets": fallback_count,
        "active_targets": len(active_dates),
        "first_active_target": active_dates[0].isoformat(),
    }


def _v7_exact_integer(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise TypeError("not an exact integer")
    return int(value)


def _v7_exact_real(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(
        value,
        (int, float, np.integer, np.floating),
    ):
        raise TypeError("not an exact real number")
    return float(value)


def _validate_v7_frame(
    frame: pd.DataFrame,
    *,
    model_name: str,
    expected_targets,
) -> None:
    required_columns = {
        "target_draw_date",
        "model_name",
        "model_version",
        "actual",
        "bonus",
        "final_6_hits",
        "top_6_hits",
        "top_12_hits",
        "top_18_hits",
        "brier_score",
        "log_loss",
        "mean_actual_rank",
    }
    missing = required_columns - set(frame.columns)
    if missing:
        raise RuntimeError(f"V7 backtest missing columns: {sorted(missing)}")
    if len(frame) != len(expected_targets):
        raise RuntimeError("V7 backtest row count mismatch")
    if set(frame["model_name"]) != {model_name}:
        raise RuntimeError("V7 backtest model identity mismatch")
    if set(frame["model_version"]) != {V7_MODEL_VERSION}:
        raise RuntimeError("V7 backtest model version mismatch")
    expected_dates = [target.draw_date.isoformat() for target in expected_targets]
    if [str(value) for value in frame["target_draw_date"]] != expected_dates:
        raise RuntimeError("V7 backtest target dates mismatch")

    for row, target in zip(frame.to_dict("records"), expected_targets):
        try:
            actual = tuple(_v7_exact_integer(number) for number in row["actual"])
            bonus = _v7_exact_integer(row["bonus"])
        except TypeError as exc:
            raise RuntimeError(
                "V7 backtest target outcome must use exact integers"
            ) from exc
        if actual != target.numbers or bonus != target.bonus:
            raise RuntimeError("V7 backtest target outcome mismatch")

    hit_columns = ["final_6_hits", "top_6_hits", "top_12_hits", "top_18_hits"]
    try:
        hits = np.asarray(
            [
                [_v7_exact_integer(value) for value in row]
                for row in frame[hit_columns].itertuples(index=False, name=None)
            ],
            dtype=np.int64,
        )
    except (TypeError, ValueError) as exc:
        raise RuntimeError("V7 hit counts must be finite integers") from exc
    if not np.isfinite(hits).all():
        raise RuntimeError("V7 hit counts must be finite integers")
    if np.any(hits < 0.0) or np.any(hits > 6.0):
        raise RuntimeError("V7 hit counts must be between 0 and 6")
    if np.any(hits[:, 1] > hits[:, 2]) or np.any(hits[:, 2] > hits[:, 3]):
        raise RuntimeError("V7 hit counts must satisfy Top-6 <= Top-12 <= Top-18")
    if np.any(hits[:, 0] > hits[:, 2]):
        raise RuntimeError("V7 final hits must remain a subset of Top-12")

    try:
        scores = np.asarray(
            [
                [_v7_exact_real(value) for value in row]
                for row in frame[["brier_score", "log_loss"]].itertuples(
                    index=False,
                    name=None,
                )
            ],
            dtype=float,
        )
        ranks = np.asarray(
            [_v7_exact_real(value) for value in frame["mean_actual_rank"]],
            dtype=float,
        )
    except (TypeError, ValueError) as exc:
        raise RuntimeError("V7 score columns must be finite and bounded") from exc
    brier_scores = scores[:, 0]
    log_losses = scores[:, 1]
    if (
        not np.isfinite(scores).all()
        or np.any(brier_scores < 0.0)
        or np.any(brier_scores > 1.0)
        or np.any(log_losses < 0.0)
        or np.any(log_losses > MAX_BINARY_LOG_LOSS)
    ):
        raise RuntimeError("V7 score columns must be finite and bounded")
    if (
        not np.isfinite(ranks).all()
        or np.any(ranks < 3.5)
        or np.any(ranks > 46.5)
    ):
        raise RuntimeError("V7 score columns must be finite and bounded")


def _v7_summary(
    frame: pd.DataFrame,
    model_name: str,
    *,
    holm_family_size: int | None,
    bootstrap_resamples: int,
    bootstrap_seed: int,
) -> dict[str, Any]:
    summary = registered_primary_summary(
        frame,
        model_name=model_name,
        multiplicity_family_size=holm_family_size or 1,
        bootstrap_resamples=bootstrap_resamples,
        bootstrap_seed=bootstrap_seed,
    )
    if holm_family_size is None:
        summary["primary_holm_adjusted_p"] = None
    return summary


def _v7_control_null(summary: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(summary)
    result["behaves_as_null"] = not (
        result["primary_exact_one_sided_p"] <= 0.05
        and result["primary_bootstrap_95_ci"][0] > 0.0
    )
    return result


def _validated_v7_role_audit_result(
    result: Any,
    *,
    randomizations: int,
    seed: int,
) -> dict[str, Any]:
    required_fields = {
        "statistic",
        "randomizations",
        "seed",
        "right_tail_exceedances",
        "plus_one_right_tail_p",
    }
    try:
        if not isinstance(result, dict) or set(result) != required_fields:
            raise TypeError("unexpected role-audit fields")
        statistic_value = result["statistic"]
        p_value = result["plus_one_right_tail_p"]
        if isinstance(statistic_value, bool) or not isinstance(
            statistic_value,
            (int, float, np.integer, np.floating),
        ):
            raise TypeError("invalid role statistic")
        if isinstance(p_value, bool) or not isinstance(
            p_value,
            (int, float, np.integer, np.floating),
        ):
            raise TypeError("invalid role p-value")
        statistic = float(statistic_value)
        actual_randomizations = _v7_exact_integer(result["randomizations"])
        actual_seed = _v7_exact_integer(result["seed"])
        exceedances = _v7_exact_integer(result["right_tail_exceedances"])
        actual_p = float(p_value)
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError("V7 global role-audit result is inconsistent") from exc

    expected_p = (1 + exceedances) / (randomizations + 1)
    if (
        not np.isfinite(statistic)
        or statistic < 0.0
        or actual_randomizations != randomizations
        or actual_seed != seed
        or not 0 <= exceedances <= randomizations
        or not np.isfinite(actual_p)
        or not 0.0 <= actual_p <= 1.0
        or actual_p != expected_p
    ):
        raise RuntimeError("V7 global role-audit result is inconsistent")
    return {
        "statistic": statistic,
        "randomizations": actual_randomizations,
        "seed": actual_seed,
        "right_tail_exceedances": exceedances,
        "plus_one_right_tail_p": actual_p,
    }


def _v7_half_frame(
    frame: pd.DataFrame,
    start: date,
    end: date,
) -> pd.DataFrame:
    dates = frame["target_draw_date"].map(str)
    mask = (dates >= start.isoformat()) & (dates <= end.isoformat())
    return frame.loc[mask].reset_index(drop=True)


def _render_v7_markdown(payload: dict[str, Any]) -> str:
    decision = payload["historical_decision"]
    lines = [
        "# V7 Post-RNG Main/Bonus Role-Bias Historical Diagnostic",
        "",
        "Status: consumed historical diagnostic only. It is not blind,",
        "confirmatory, prospective, or an automatic shadow/production promotion.",
        "",
        f"- Experiment: `{payload['experiment_id']}` / `{payload['model_version']}`",
        f"- Frozen implementation commit: `{payload['code_commit']}`",
        f"- Exact command: `{payload['command']}`",
        f"- Permanent one-shot claim: `{payload['one_shot_claim']['path']}`",
        f"- Claim SHA-256: `{payload['one_shot_claim']['sha256']}`",
        f"- Research config SHA-256: `{payload['configuration']['source_sha256']}`",
        f"- V6 reference SHA-256: `{payload['reference_provenance']['sha256']}`",
        "- Applicable prediction lane: 2020-01-01 through 2025-12-31 only",
        "- Development and legacy-validation lanes: not applicable and not scored",
        "",
        "## Registered prediction results",
        "",
        "| Scope | Model | Draws | Top-12 | Lift | Raw p | Holm p | 95% CI | Brier delta | Log-loss delta |",
        "|---|---|---:|---:|---:|---:|---:|---|---:|---:|",
    ]
    rows = [
        ("aggregate", payload["candidate"]),
        ("aggregate control", payload["negative_control"]),
    ]
    for half in payload["stability_halves"]:
        rows.extend(
            [
                (half["name"], half["candidate"]),
                (f"{half['name']} control", half["negative_control"]),
            ]
        )
    for scope, summary in rows:
        ci = summary["primary_bootstrap_95_ci"]
        holm = summary["primary_holm_adjusted_p"]
        lines.append(
            "| {scope} | {model} | {draws} | {top12:.6f} | {lift:+.6f} | "
            "{raw:.6g} | {holm} | [{lower:+.6f}, {upper:+.6f}] | "
            "{brier:+.6g} | {logloss:+.6g} |".format(
                scope=scope,
                model=summary["model_name"],
                draws=summary["draws"],
                top12=summary["avg_top12_hits"],
                lift=summary["primary_top12_lift_vs_theory"],
                raw=summary["primary_exact_one_sided_p"],
                holm=f"{holm:.6g}" if holm is not None else "n/a",
                lower=ci[0],
                upper=ci[1],
                brier=summary["brier_delta_vs_fair"],
                logloss=summary["log_loss_delta_vs_fair"],
            )
        )
    audit = payload["global_role_audit"]
    activation = payload["activation"]
    lines.extend(
        [
            "",
            "## Registered integrity and role audit",
            "",
            f"- Targets: `{activation['eligible_targets']}`; fair fallback: "
            f"`{activation['fair_fallback_targets']}`; active: "
            f"`{activation['active_targets']}`; first active: "
            f"`{activation['first_active_target']}`",
            f"- Global role statistic G: `{audit['statistic']}`",
            f"- Global role audit plus-one p: `{audit['plus_one_right_tail_p']}` "
            f"from `{audit['randomizations']}` randomizations",
            "",
            "## Frozen historical decision",
            "",
            f"Decision: **{decision['decision']}**. Prospective status remains "
            "**not_activated**.",
            "",
        ]
    )
    for gate, passed in decision["gates"].items():
        lines.append(f"- `{gate}`: {'pass' if passed else 'fail'}")
    lines.extend(
        [
            "",
            "The JSON companion retains the frozen comparison summaries, complete",
            "aggregate/half candidate and control metrics, data/config/code hashes,",
            "registered parameters, audit warnings, and prospective boundary.",
            "",
        ]
    )
    return "\n".join(lines)


def _write_v7_exclusive_text(path: Path, text: str) -> None:
    with path.open("x", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())


def _claim_v7_historical_attempt(claim_path: Path, code_commit: str) -> None:
    claim_text = json.dumps(
        {
            "code_commit": code_commit,
            "experiment_id": V7_EXPERIMENT_ID,
            "model_version": V7_MODEL_VERSION,
            "status": "historical_diagnostic_claimed",
        },
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ) + "\n"
    try:
        _write_v7_exclusive_text(claim_path, claim_text)
    except FileExistsError as exc:
        raise RuntimeError(
            "V7 historical one-shot claim already exists; refusing to score"
        ) from exc
    except OSError as exc:
        raise RuntimeError(
            "unable to create the durable V7 historical one-shot claim"
        ) from exc


def _publish_v7_report_pair(
    *,
    json_path: Path,
    markdown_path: Path,
    json_temporary_path: Path,
    markdown_temporary_path: Path,
    json_text: str,
    markdown_text: str,
) -> None:
    try:
        _write_v7_exclusive_text(json_temporary_path, json_text)
        _write_v7_exclusive_text(markdown_temporary_path, markdown_text)
    except OSError as exc:
        raise RuntimeError(
            "unable to stage the complete V7 report pair; claim retained"
        ) from exc

    published: list[Path] = []
    try:
        os.link(json_temporary_path, json_path)
        published.append(json_path)
        os.link(markdown_temporary_path, markdown_path)
        published.append(markdown_path)
    except OSError as exc:
        for path in reversed(published):
            try:
                path.unlink()
            except OSError:
                pass
        raise RuntimeError(
            "unable to publish the complete V7 report pair; claim retained"
        ) from exc

    try:
        json_temporary_path.unlink()
        markdown_temporary_path.unlink()
    except OSError as exc:
        raise RuntimeError(
            "V7 report pair was published but temporary cleanup failed; "
            "permanent claim retained for audit"
        ) from exc


def run_registered_v7_diagnostics(
    cfg: dict,
    *,
    code_commit: str,
    output_dir: Path,
) -> dict[str, Any]:
    """Run the single frozen V7 diagnostic after every audit preflight passes."""
    _require_full_git_sha(code_commit, "code_commit")
    root = Path(cfg["_root"])
    canonical_output_dir = (root / "reports").resolve()
    if output_dir.resolve() != canonical_output_dir:
        raise RuntimeError(
            "V7 output must be the canonical repository reports directory"
        )
    output_dir = canonical_output_dir
    json_path = output_dir / f"{V7_REPORT_STEM}.json"
    markdown_path = output_dir / f"{V7_REPORT_STEM}.md"
    claim_path = output_dir / f"{V7_REPORT_STEM}.claim"
    json_temporary_path = output_dir / f".{V7_REPORT_STEM}.json.tmp"
    markdown_temporary_path = output_dir / f".{V7_REPORT_STEM}.md.tmp"
    if claim_path.exists():
        raise RuntimeError(
            "V7 historical one-shot claim already exists; refusing to score"
        )
    if json_temporary_path.exists() or markdown_temporary_path.exists():
        raise RuntimeError(
            "V7 historical temporary report exists; refusing to score"
        )
    if json_path.exists() or markdown_path.exists():
        raise RuntimeError("V7 historical report already exists; refusing to overwrite")
    _validate_v7_git_audit(root, code_commit)
    configuration_manifest = _validated_v7_configuration_manifest(
        root,
        cfg,
        code_commit,
    )
    registry = load_experiment_registry(root / "docs" / "experiments" / "registry.yaml")
    registration = registry.get(V7_EXPERIMENT_ID)
    reference_registration = registry.get(V7_REFERENCE_EXPERIMENT_ID)
    _validate_v7_registration_and_config(cfg, registration)
    outcome_evidence = _validate_v7_outcome_boundaries(root, registration)

    dataset_path = resolve_path(cfg, cfg["data"]["processed_csv"])
    draws = load_draws(dataset_path)
    registered_draws = validated_registered_draw_prefix(
        dataset_path,
        draws,
        expected_sha256=registration.dataset_sha256,
        draw_count=registration.dataset_draw_count,
        history_through=registration.registration_history_through,
    )
    reference, reference_path, reference_sha256, reference_comparisons = (
        _load_validated_v6_reference_for_v7(
            root,
            code_commit,
            registration,
            reference_registration,
        )
    )
    minimum_history = int(cfg["backtest"]["min_history_draws"])
    folds, activation = _v7_preflight_targets(registered_draws, minimum_history)
    expected_targets = [fold.target for fold in folds]
    family_size = sum(
        experiment.multiplicity_family == registration.multiplicity_family
        for experiment in registry.experiments
    )
    if family_size != 1:
        raise RuntimeError("V7 multiplicity family must contain exactly one variant")

    audit_draws = [
        draw
        for draw in registered_draws
        if V7_RNG_START <= draw.draw_date <= V7_TARGET_END
    ]
    if (
        len(audit_draws) != 686
        or audit_draws[0].draw_date != V7_RNG_START
        or audit_draws[-1].draw_date != V7_TARGET_END
        or any(draw.bonus is None for draw in audit_draws)
    ):
        raise RuntimeError("V7 global role-audit interval is incomplete")

    _claim_v7_historical_attempt(claim_path, code_commit)
    claim_sha256 = file_sha256(claim_path)

    # No performance-scoring call is allowed above this line. Candidate and
    # control receive the same immutable outcomes; the control model transforms
    # only each strictly prior history prefix inside predict().
    candidate_frame = run_backtest(
        registered_draws,
        cfg,
        V7_TARGET_START,
        V7_TARGET_END,
    )
    _validate_v7_frame(
        candidate_frame,
        model_name=V7_CANDIDATE_NAME,
        expected_targets=expected_targets,
    )
    control_cfg = deepcopy(cfg)
    control_cfg["backtest"]["models"] = [V7_CONTROL_NAME]
    control_cfg["backtest"]["model_versions"] = {
        V7_CONTROL_NAME: V7_MODEL_VERSION
    }
    control_frame = run_backtest(
        registered_draws,
        control_cfg,
        V7_TARGET_START,
        V7_TARGET_END,
    )
    _validate_v7_frame(
        control_frame,
        model_name=V7_CONTROL_NAME,
        expected_targets=expected_targets,
    )
    if not candidate_frame[["target_draw_date", "actual", "bonus"]].equals(
        control_frame[["target_draw_date", "actual", "bonus"]]
    ):
        raise RuntimeError("V7 candidate/control target identities differ")

    bootstrap_resamples = registration.parameters["bootstrap_replicates"]
    bootstrap_seed = registration.parameters["bootstrap_seed"]
    candidate = _v7_summary(
        candidate_frame,
        V7_CANDIDATE_NAME,
        holm_family_size=family_size,
        bootstrap_resamples=bootstrap_resamples,
        bootstrap_seed=bootstrap_seed,
    )
    negative_control = _v7_control_null(
        _v7_summary(
            control_frame,
            V7_CONTROL_NAME,
            holm_family_size=None,
            bootstrap_resamples=bootstrap_resamples,
            bootstrap_seed=bootstrap_seed,
        )
    )
    stability_halves = []
    negative_control_halves = []
    for name, start, end, expected_count in V7_HALF_RANGES:
        candidate_half_frame = _v7_half_frame(candidate_frame, start, end)
        control_half_frame = _v7_half_frame(control_frame, start, end)
        if len(candidate_half_frame) != expected_count or len(control_half_frame) != (
            expected_count
        ):
            raise RuntimeError(f"V7 {name} target count mismatch after scoring")
        candidate_half = _v7_summary(
            candidate_half_frame,
            V7_CANDIDATE_NAME,
            holm_family_size=None,
            bootstrap_resamples=bootstrap_resamples,
            bootstrap_seed=bootstrap_seed,
        )
        control_half = _v7_control_null(
            _v7_summary(
                control_half_frame,
                V7_CONTROL_NAME,
                holm_family_size=None,
                bootstrap_resamples=bootstrap_resamples,
                bootstrap_seed=bootstrap_seed,
            )
        )
        negative_control_halves.append(deepcopy(control_half))
        half_dates = [
            target.draw_date
            for target in expected_targets
            if start <= target.draw_date <= end
        ]
        active_count = sum(
            target_date >= date(2020, 5, 20) for target_date in half_dates
        )
        stability_halves.append(
            {
                "name": name,
                "dates": {"start": start.isoformat(), "end": end.isoformat()},
                "target_count": expected_count,
                "activation": {
                    "fair_fallback_targets": expected_count - active_count,
                    "active_targets": active_count,
                },
                "candidate": candidate_half,
                "negative_control": control_half,
            }
        )

    audit_randomizations = registration.parameters[
        "global_role_audit_randomizations"
    ]
    audit_seed = registration.parameters["global_role_audit_seed"]
    raw_global_role_audit = role_audit_monte_carlo(
        audit_draws,
        randomizations=audit_randomizations,
        seed=audit_seed,
    )
    global_role_audit = _validated_v7_role_audit_result(
        raw_global_role_audit,
        randomizations=audit_randomizations,
        seed=audit_seed,
    )
    global_role_audit = {
        **global_role_audit,
        "draw_count": len(audit_draws),
        "dates": {"start": "2019-05-15", "end": "2025-12-31"},
        "comparison_operator": "greater_than_or_equal",
        "p_value_method": "plus_one_right_tail",
    }
    decision_input = {
        "candidate": candidate,
        "stability_halves": stability_halves,
        "negative_control": negative_control,
        "negative_control_halves": negative_control_halves,
        "global_role_audit": global_role_audit,
        "audit_warnings": [],
    }
    historical_decision, audit_warnings = v7_historical_decision(
        decision_input,
        proper_score_tolerance=registration.parameters[
            "proper_score_max_delta_vs_fair"
        ],
    )
    prospective = registration.prospective
    payload = {
        "schema_version": 3,
        "experiment_id": registration.experiment_id,
        "model_name": registration.model_name,
        "model_version": registration.model_version,
        "status": "historical_diagnostic_complete",
        "evidence_warning": (
            "The sole prediction lane is consumed historical diagnostic evidence; "
            "it is not blind, confirmatory, or prospective."
        ),
        "code_commit": code_commit,
        "command": (
            "lotto649 --config config/research-v7-main-bonus-role-bias.yaml "
            f"research-v7 --code-commit {code_commit}"
        ),
        "one_shot_claim": {
            "path": str(claim_path.relative_to(root)),
            "sha256": claim_sha256,
            "created_before_first_score": True,
            "retention": "permanent_on_success_or_failure",
        },
        "configuration": configuration_manifest,
        "data_boundaries": {
            "historical_diagnostic_prefix": _registered_dataset_identity(registration),
            "outcomes_known_at_registration": _known_outcomes_identity(registration),
        },
        "data_boundary_verification": {
            "git_verified": True,
            "registration_prefix_preserved": (
                outcome_evidence.registration_prefix_preserved
            ),
            "known_outcomes_draws_fingerprint": outcome_evidence.draws_fingerprint,
        },
        "reference_provenance": {
            "path": str(reference_path.relative_to(root)),
            "sha256": reference_sha256,
            "schema_version": reference["schema_version"],
            "experiment_id": reference["experiment_id"],
            "model_name": reference["model_name"],
            "model_version": reference["model_version"],
            "implementation_commit": reference["code_commit"],
            "dataset": deepcopy(
                reference["data_boundaries"]["historical_diagnostic_prefix"]
            ),
            "lane": "consumed_diagnostic",
            "target_count": 621,
            "reused_models": [
                name for name, _version in V7_REFERENCE_MODEL_VERSIONS
            ],
            "policy": "frozen consumed-lane summaries reused; no comparison refit",
        },
        "registered_parameters": dict(registration.parameters),
        "multiplicity_family": registration.multiplicity_family,
        "multiplicity_family_size": family_size,
        "comparison_models": [
            *(name for name, _version in V7_REFERENCE_MODEL_VERSIONS),
            V7_CANDIDATE_NAME,
        ],
        "historical_lane": {
            "name": "consumed_diagnostic",
            "dates": {"start": "2020-01-01", "end": "2025-12-31"},
            "target_count": 621,
            "development_status": "not_applicable",
            "legacy_validation_status": "not_applicable",
        },
        "activation": activation,
        "negative_control_activation": deepcopy(activation),
        "candidate": candidate,
        "negative_control_spec": {
            "kind": registration.negative_controls[0].kind,
            "seed": registration.negative_controls[0].seed,
            "scope": "strictly prior prediction history only; target unchanged",
        },
        "negative_control": negative_control,
        "stability_halves": stability_halves,
        "negative_control_halves": negative_control_halves,
        "comparisons": [*reference_comparisons, deepcopy(candidate)],
        "global_role_audit": global_role_audit,
        "historical_decision": historical_decision,
        "audit_warnings": audit_warnings,
        "prospective_cohort": {
            "status": prospective.status,
            "role": prospective.role,
            "minimum_eligible_draws": prospective.minimum_eligible_draws,
            "fixed_half_draws": registration.parameters["prospective_half_draws"],
            "commit_deadline": prospective.commit_deadline,
            "freeze_commit": prospective.freeze_commit,
            "activation_commit": prospective.activation_commit,
            "outcomes_known_at_activation": None,
            "cohort_start": None,
            "early_look": "prohibited",
            "extension": "prohibited",
        },
    }
    json_text = json.dumps(
        payload,
        indent=2,
        sort_keys=True,
        allow_nan=False,
    ) + "\n"
    markdown_text = _render_v7_markdown(payload)
    _publish_v7_report_pair(
        json_path=json_path,
        markdown_path=markdown_path,
        json_temporary_path=json_temporary_path,
        markdown_temporary_path=markdown_temporary_path,
        json_text=json_text,
        markdown_text=markdown_text,
    )
    return {
        "json_path": str(json_path),
        "markdown_path": str(markdown_path),
        "claim_path": str(claim_path),
        "report": payload,
    }
