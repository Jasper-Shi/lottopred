from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import date
import json
from math import comb, log
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .backtest import run_backtest
from .config import resolve_path
from .data import load_draws
from .research_protocol import file_sha256, load_experiment_registry, permute_draw_outcomes


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
    lower, upper = np.quantile(lifts, [0.025, 0.975])
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
) -> dict[str, Any]:
    rows = frame.loc[frame["model_name"] == model_name]
    if rows.empty:
        raise ValueError(f"missing primary rows for {model_name}")
    hits = rows["top_12_hits"].to_numpy(dtype=int)
    total_hits = int(hits.sum())
    raw_p = exact_topk_upper_tail(total_hits, len(hits), 12)
    lower, upper = bootstrap_mean_lift_interval(hits, FAIR_EXPECTATIONS[12])
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
    actual_sha256 = file_sha256(dataset_path)
    if actual_sha256 != registration.dataset_sha256:
        raise RuntimeError(
            "registration dataset fingerprint mismatch; run from the frozen source commit"
        )
    draws = load_draws(dataset_path)
    if len(draws) != registration.dataset_draw_count:
        raise RuntimeError("registration dataset draw count mismatch")
    if draws[-1].draw_date != registration.registration_history_through:
        raise RuntimeError("registration dataset history boundary mismatch")

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
    control_draws = permute_draw_outcomes(draws, seed=registration.seed)
    control_cfg = deepcopy(cfg)
    control_cfg["backtest"]["models"] = [CANDIDATE_NAME]

    lane_payloads = []
    for lane in HISTORICAL_LANES:
        normal_frame = run_backtest(draws, cfg, lane.start, lane.end)
        control_frame = run_backtest(control_draws, control_cfg, lane.start, lane.end)
        total_targets, eligible_targets = _eligible_target_count(
            draws, lane, minimum_history
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
        "dataset": {
            "path": registration.dataset_path,
            "source_commit": registration.dataset_source_commit,
            "sha256": registration.dataset_sha256,
            "draw_count": registration.dataset_draw_count,
            "history_through": registration.registration_history_through.isoformat(),
        },
        "negative_control_seed": registration.seed,
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
