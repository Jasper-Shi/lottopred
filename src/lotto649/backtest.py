from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd

from .domain import Prediction
from .evaluation import evaluate_prediction
from .models.factory import build_models
from .optimizer import rank_numbers, select_combination


def _prediction_at(model, history, target, cfg, version: str):
    probs = model.predict(history, target.draw_date)
    ranked = rank_numbers(probs)
    return Prediction(
        target_draw_date=target.draw_date,
        generated_at=datetime.combine(target.draw_date, datetime.min.time(), tzinfo=ZoneInfo("UTC")),
        model_name=model.name,
        model_version=version,
        probabilities=probs,
        top6=ranked[:6],
        top12=ranked[:12],
        top18=ranked[:18],
        final_combination=select_combination(probs, cfg["prediction"].get("candidate_pool_size", 12)),
        metadata={
            "mode": "walk_forward",
            "history_draws": len(history),
            "history_through": history[-1].draw_date.isoformat(),
        },
    )


def run_backtest(draws, cfg, start: date, end: date, output_dir: Path | None = None) -> pd.DataFrame:
    models = build_models(cfg)
    min_hist = cfg["backtest"].get("min_history_draws", 300)
    version = cfg["project"].get("model_version", "v1.0.0")
    rows = []
    for idx, target in enumerate(draws):
        if target.draw_date < start or target.draw_date > end or idx < min_hist:
            continue
        history = draws[:idx]
        for model in models.values():
            pred = _prediction_at(model, history, target, cfg, version)
            rows.append(evaluate_prediction(pred, target))
    frame = pd.DataFrame(rows)
    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        frame.to_csv(output_dir / f"backtest_{start}_{end}_detail.csv", index=False)
        summarize(frame).to_csv(output_dir / f"backtest_{start}_{end}_summary.csv", index=False)
    return frame


def summarize(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    agg = frame.groupby("model_name").agg(
        draws=("final_6_hits", "size"),
        avg_final_hits=("final_6_hits", "mean"),
        avg_top12_hits=("top_12_hits", "mean"),
        avg_top18_hits=("top_18_hits", "mean"),
        avg_brier=("brier_score", "mean"),
        avg_log_loss=("log_loss", "mean"),
        avg_actual_rank=("mean_actual_rank", "mean"),
        hit_3plus=("final_6_hits", lambda s: float((s >= 3).mean())),
        hit_4plus=("final_6_hits", lambda s: float((s >= 4).mean())),
    ).reset_index()
    random_row = agg[agg.model_name == "random"]
    baseline = float(random_row.avg_final_hits.iloc[0]) if len(random_row) else 36 / 49
    agg["final_hit_lift_vs_random"] = agg.avg_final_hits - baseline
    return agg.sort_values(["avg_final_hits", "avg_top12_hits"], ascending=False)
