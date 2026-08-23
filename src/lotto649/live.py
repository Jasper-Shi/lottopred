from __future__ import annotations

from datetime import date, timedelta, datetime
from pathlib import Path
import json

from .config import resolve_path
from .data import save_draws, load_draws
from .data_sources import refresh_with_sources
from .domain import Draw, Prediction
from .evaluation import evaluate_prediction
from .models.factory import build_models
from .notification import should_alert, send_hit_alert
from .predictor import make_prediction
from .storage import save_prediction, save_evaluation


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


def next_draw_date(after: date) -> date:
    for delta in range(1, 8):
        d = after + timedelta(days=delta)
        if d.weekday() in (2, 5):
            return d
    raise RuntimeError("unreachable")


def refresh_data(cfg: dict) -> list[Draw]:
    _require_live_enabled(cfg)
    _require_data_refresh_enabled(cfg)
    csv_path = resolve_path(cfg, cfg["data"]["processed_csv"])
    existing = load_draws(csv_path) if csv_path.exists() else []
    draws = refresh_with_sources(existing, cfg)
    save_draws(draws, csv_path)
    return draws


def evaluate_due_predictions(cfg: dict, draws: list[Draw]) -> list[dict]:
    _require_live_enabled(cfg)
    _require_data_refresh_enabled(cfg)
    root = Path(cfg["_root"])
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
            probabilities={int(k): float(v) for k, v in payload["probabilities"].items()},
            top6=payload["top6"], top12=payload["top12"], top18=payload["top18"],
            final_combination=payload["final_combination"], metadata=payload.get("metadata", {}),
        )
        ev = evaluate_prediction(pred, actual)
        if cfg["notifications"].get("enabled", True) and should_alert(ev, cfg):
            ev["email_sent"] = send_hit_alert(ev)
        save_evaluation(root, ev)
        completed.append(ev)
    return completed


def generate_next_predictions(cfg: dict, draws: list[Draw]) -> list[Path]:
    _require_live_enabled(cfg)
    _require_data_refresh_enabled(cfg)
    root = Path(cfg["_root"])
    version = cfg["project"].get("model_version", "v1.0.0")
    target = next_draw_date(draws[-1].draw_date)
    paths = []
    requested = cfg.get("live", {}).get("models")
    for model in build_models(cfg, requested=requested).values():
        pred = make_prediction(model, draws, target, cfg, version)
        if model.name in cfg.get("live", {}).get("shadow_models", []):
            pred.metadata["role"] = "shadow"
        else:
            pred.metadata["role"] = "primary"
        path = root / "predictions" / f"{target.isoformat()}__{model.name}__{version}.json"
        if path.exists():
            continue
        paths.append(save_prediction(root, pred))
    return paths


def run_live_cycle(cfg: dict) -> dict:
    _require_live_enabled(cfg)
    _require_data_refresh_enabled(cfg)
    draws = refresh_data(cfg)
    evaluations = evaluate_due_predictions(cfg, draws)
    predictions = generate_next_predictions(cfg, draws)
    return {
        "latest_draw": draws[-1].draw_date.isoformat(),
        "draw_count": len(draws),
        "evaluations_created": len(evaluations),
        "predictions_created": [str(p) for p in predictions],
    }
