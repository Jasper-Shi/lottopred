from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import NoReturn

from .domain import Prediction
from .evaluation import evaluate_prediction
from .history_execution_handoff import evaluation_prediction_source
from .models.factory import build_models
from .notification import send_hit_alert, should_alert
from .operational_history import operational_history_provenance
from .predictor import make_prediction
from .storage import save_evaluation, save_prediction
from .verified_history import VerifiedHistory


def _require_live_enabled(cfg: dict) -> None:
    live_cfg = cfg.get("live")
    if not isinstance(live_cfg, dict) or live_cfg.get("enabled") is not True:
        raise RuntimeError(
            "live execution is disabled; live.enabled must be explicitly true"
        )


def _require_data_refresh_enabled(cfg: dict) -> None:
    data_cfg = cfg.get("data")
    if not isinstance(data_cfg, dict) or data_cfg.get("refresh_enabled") is not True:
        raise RuntimeError(
            "data refresh is disabled; data.refresh_enabled must be explicitly true"
        )


def _require_verified_history_append_writer() -> NoReturn:
    raise RuntimeError(
        "verified history append writer is not implemented; live remains paused"
    )


def next_draw_date(after: date) -> date:
    for delta in range(1, 8):
        d = after + timedelta(days=delta)
        if d.weekday() in (2, 5):
            return d
    raise RuntimeError("unreachable")


def refresh_data(cfg: dict) -> VerifiedHistory:
    _require_live_enabled(cfg)
    _require_data_refresh_enabled(cfg)
    _require_verified_history_append_writer()


def _evaluate_due_predictions(cfg: dict, history: VerifiedHistory) -> list[dict]:
    root = Path(cfg["_root"])
    draws = history.draws
    source_provenance = operational_history_provenance(history)
    actual_by_date = {d.draw_date.isoformat(): d for d in draws}
    completed = []
    for path in sorted((root / "predictions").glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        actual = actual_by_date.get(payload["target_draw_date"])
        if not actual:
            continue
        eval_path = root / "evaluations" / path.name
        if eval_path.exists():
            continue
        pred = Prediction(
            target_draw_date=date.fromisoformat(payload["target_draw_date"]),
            generated_at=datetime.fromisoformat(payload["generated_at"]),
            model_name=payload["model_name"],
            model_version=payload["model_version"],
            probabilities={
                int(k): float(v) for k, v in payload["probabilities"].items()
            },
            top6=payload["top6"],
            top12=payload["top12"],
            top18=payload["top18"],
            final_combination=payload["final_combination"],
            metadata=payload.get("metadata", {}),
        )
        ev = evaluate_prediction(pred, actual)
        ev["actual_history"] = source_provenance
        ev["prediction_source"] = evaluation_prediction_source(
            root,
            history.registry.resolved_revision,
            path.relative_to(root).as_posix(),
        )
        if cfg["notifications"].get("enabled", True) and should_alert(ev, cfg):
            try:
                ev["email_sent"] = send_hit_alert(ev)
            except Exception:  # noqa: BLE001 - SMTP cannot block immutable evidence
                ev["email_sent"] = False
        save_evaluation(root, ev)
        completed.append(ev)
    return completed


def evaluate_due_predictions(cfg: dict) -> list[dict]:
    _require_live_enabled(cfg)
    _require_data_refresh_enabled(cfg)
    _require_verified_history_append_writer()


def _generate_next_predictions(
    cfg: dict,
    history: VerifiedHistory,
    *,
    generated_at: datetime | None = None,
) -> list[Path]:
    root = Path(cfg["_root"])
    draws = history.draws
    source_provenance = operational_history_provenance(history)
    version = cfg["project"].get("model_version", "v1.0.0")
    target = next_draw_date(draws[-1].draw_date)
    paths = []
    requested = cfg.get("live", {}).get("models")
    for model in build_models(cfg, requested=requested).values():
        pred = make_prediction(
            model,
            draws,
            target,
            cfg,
            version,
            generated_at=generated_at,
        )
        if model.name in cfg.get("live", {}).get("shadow_models", []):
            pred.metadata["role"] = "shadow"
        else:
            pred.metadata["role"] = "primary"
        pred.metadata["operational_history"] = source_provenance
        path = (
            root / "predictions" / f"{target.isoformat()}__{model.name}__{version}.json"
        )
        if path.exists():
            continue
        paths.append(save_prediction(root, pred))
    return paths


def generate_next_predictions(cfg: dict) -> list[Path]:
    _require_live_enabled(cfg)
    _require_data_refresh_enabled(cfg)
    _require_verified_history_append_writer()


def run_live_cycle(cfg: dict) -> dict:
    _require_live_enabled(cfg)
    _require_data_refresh_enabled(cfg)
    history = refresh_data(cfg)
    draws = history.draws
    evaluations = _evaluate_due_predictions(cfg, history)
    predictions = _generate_next_predictions(cfg, history)
    return {
        "latest_draw": draws[-1].draw_date.isoformat(),
        "draw_count": len(draws),
        "evaluations_created": len(evaluations),
        "predictions_created": [str(p) for p in predictions],
    }
