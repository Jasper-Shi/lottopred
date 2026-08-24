from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from .domain import Draw, Prediction
from .optimizer import rank_numbers, select_combination


def make_prediction(
    model,
    history: list[Draw],
    target_date: date,
    cfg: dict,
    model_version: str,
    *,
    generated_at: datetime | None = None,
) -> Prediction:
    probs = model.predict(history, target_date)
    ranked = rank_numbers(probs)
    final = select_combination(probs, cfg["prediction"].get("candidate_pool_size", 12))
    tz = ZoneInfo(cfg["project"].get("timezone", "America/Toronto"))
    return Prediction(
        target_draw_date=target_date,
        generated_at=generated_at or datetime.now(tz),
        model_name=model.name,
        model_version=model_version,
        probabilities=probs,
        top6=ranked[:6],
        top12=ranked[:12],
        top18=ranked[:18],
        final_combination=final,
        metadata={
            "history_draws": len(history),
            "history_through": history[-1].draw_date.isoformat() if history else None,
        },
    )
