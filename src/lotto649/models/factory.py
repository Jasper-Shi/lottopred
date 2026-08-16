from __future__ import annotations

from .baselines import RandomBaseline, LongFrequencyModel, RecentFrequencyModel, EmaGapModel
from .logistic import LogisticNumberModel
from .ensemble import EnsembleModel
from .v2_statistical import V2StatisticalModel
from .v3_boosting import V3BoostingModel
from .v4_ensemble import V4EnsembleModel
from .v5_pair_affinity import V5PairAffinityModel
from .v6_entropy_regime import V6EntropyRegimeModel
from .v7_main_bonus_role_bias import (
    V7MainBonusRoleBiasModel,
    V7MainBonusRoleControlModel,
)
from .v8_spectral_phase import (
    V8SpectralPhaseModel,
    V8SpectralPhaseRotationControlModel,
    V8SpectralPhaseRowControlModel,
)


_V8_MODEL_NAMES = {
    "v8_spectral_phase",
    "v8_spectral_phase_row_control",
    "v8_spectral_phase_rotation_control",
}
_FROZEN_V8_RESEARCH_CONFIG = {
    "experiment_id": "V8_fixed_recurrence_harmonic",
    "family": "periodicity_frequency_domain",
    "variant_index": 1,
    "post_rng_start_date": "2019-05-15",
    "active_minimum_post_rng_prior_draws": 104,
    "history_integrity": "exact_verified_source_blob_prefix",
    "missing_or_disputed_draw_policy": "invalid_pipeline_archive",
    "fair_inclusion_probability": 6.0 / 49.0,
    "fixed_period_draws": 49.0 / 6.0,
    "fixed_angular_frequency": "12*pi/49",
    "coefficient_estimator": "raw_fourier_projection_2_over_D",
    "probability_link": "stable_sigmoid",
    "bisection_iterations": 256,
    "probability_sum_absolute_tolerance": 1.0e-12,
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
    "bootstrap_seed": 649,
    "negative_controls": [
        "strict_prefix_whole_draw_permutation",
        "per_number_spectral_phase_rotation",
    ],
    "control_null_rule": "raw_p_gt_0_05_or_ci_includes_zero",
    "row_control_direct_comparison": (
        "paired_candidate_minus_row_control_top12_hits"
    ),
    "row_control_direct_bootstrap_replicates": 10_000,
    "row_control_direct_bootstrap_rng": "numpy.default_rng",
    "row_control_direct_bootstrap_seed": 649,
    "row_control_direct_bootstrap_interval": (
        "two_sided_95_percentile_linear"
    ),
    "row_control_direct_gate": (
        "lower_endpoint_strictly_above_zero_aggregate_and_halves"
    ),
    "prospective_exact_eligible_evaluated_draws": 208,
    "prospective_half_draws": 104,
    "prospective_history_integrity": "exact_snapshot_bound_source_blob_prefix",
    "reference_report": (
        "reports/v7_main_bonus_role_bias_v7.0.0_historical.json"
    ),
    "reference_report_sha256": (
        "242018714a17a78a8b99309e4391e153c293a02121738addd2bb8f9f74d6c121"
    ),
    "reference_claim": (
        "reports/v7_main_bonus_role_bias_v7.0.0_historical.claim"
    ),
    "reference_claim_sha256": (
        "1443982f9b40ba5b460632211baa17b4aff7cb9cdcd48010c0a538f141344290"
    ),
}


def _matches_frozen_value(actual: object, expected: object) -> bool:
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return actual.keys() == expected.keys() and all(
            _matches_frozen_value(actual[key], value)
            for key, value in expected.items()
        )
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(
            _matches_frozen_value(actual_value, expected_value)
            for actual_value, expected_value in zip(actual, expected)
        )
    return actual == expected


def _validate_frozen_v8_configuration(
    cfg: dict,
    requested_names: list[str],
) -> None:
    selected_v8 = set(requested_names) & _V8_MODEL_NAMES
    if not selected_v8:
        return
    if set(requested_names) - _V8_MODEL_NAMES:
        raise ValueError(
            "frozen V8 research configuration cannot mix selectable models"
        )
    if not _matches_frozen_value(
        cfg.get("research"),
        _FROZEN_V8_RESEARCH_CONFIG,
    ):
        raise ValueError("frozen V8 research configuration does not match v8.0.0")
    if cfg.get("project", {}).get("model_version") != "v8.0.0" or cfg.get(
        "project", {}
    ).get("seed") != 649:
        raise ValueError("frozen V8 research configuration does not match v8.0.0")
    if not _matches_frozen_value(
        cfg.get("live"),
        {"enabled": False, "models": [], "shadow_models": []},
    ):
        raise ValueError("frozen V8 research configuration must disable live use")
    backtest = cfg.get("backtest", {})
    if (
        not _matches_frozen_value(backtest.get("min_history_draws"), 104)
        or not _matches_frozen_value(backtest.get("test_start"), "2020-01-01")
        or not _matches_frozen_value(backtest.get("test_end"), "2025-12-31")
        or not _matches_frozen_value(backtest.get("top_k"), [6, 12, 18])
    ):
        raise ValueError("frozen V8 research configuration does not match v8.0.0")
    model_versions = backtest.get("model_versions", {})
    if any(
        name in model_versions and model_versions[name] != "v8.0.0"
        for name in selected_v8
    ):
        raise ValueError("frozen V8 research configuration does not match v8.0.0")


def build_models(cfg: dict, requested: list[str] | None = None):
    use_all_models = requested is None and "models" not in cfg["backtest"]
    requested_names = list(
        requested
        if requested is not None
        else cfg["backtest"].get("models", [])
    )
    logistic = LogisticNumberModel(
        training_draws=cfg["features"].get("logistic_training_draws", 480),
        min_samples=cfg["features"].get("min_logistic_samples", 300),
    )
    v2 = V2StatisticalModel()
    v3 = V3BoostingModel(
        training_draws=cfg["features"].get("v3_training_draws", 280),
        stride=cfg["features"].get("v3_stride", 14),
        min_history=cfg["features"].get("v3_min_history", 300),
    )
    base = {
        "random": RandomBaseline(),
        "long_frequency": LongFrequencyModel(),
        "recent_frequency": RecentFrequencyModel(100),
        "ema_gap": EmaGapModel(),
        "logistic": logistic,
        "v2_statistical": v2,
        "v3_boosting": v3,
        "v5_pair_affinity": V5PairAffinityModel(),
        "v6_entropy_regime": V6EntropyRegimeModel(),
        "v7_main_bonus_role_bias": V7MainBonusRoleBiasModel(),
        "v7_main_bonus_role_control": V7MainBonusRoleControlModel(),
        "v8_spectral_phase": V8SpectralPhaseModel(),
        "v8_spectral_phase_row_control": V8SpectralPhaseRowControlModel(),
        "v8_spectral_phase_rotation_control": (
            V8SpectralPhaseRotationControlModel()
        ),
    }
    base["ensemble"] = EnsembleModel([
        (base["long_frequency"], 0.15),
        (base["recent_frequency"], 0.20),
        (base["ema_gap"], 0.20),
        (base["logistic"], 0.45),
    ])
    base["v4_ensemble"] = V4EnsembleModel([
        (base["ema_gap"], 0.20),
        (base["v2_statistical"], 0.35),
        (base["v3_boosting"], 0.45),
    ])
    if use_all_models:
        requested_names = [name for name in base if name not in _V8_MODEL_NAMES]
    _validate_frozen_v8_configuration(cfg, requested_names)
    unknown = set(requested_names) - set(base)
    if unknown:
        raise ValueError(f"Unknown models requested: {sorted(unknown)}")
    return {name: base[name] for name in requested_names}
