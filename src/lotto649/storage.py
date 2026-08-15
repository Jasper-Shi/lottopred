from __future__ import annotations

import json
from pathlib import Path

from .domain import Prediction


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


def save_prediction(root: Path, pred: Prediction, overwrite: bool = False) -> Path:
    path = root / "predictions" / f"{pred.target_draw_date.isoformat()}__{pred.model_name}__{pred.model_version}.json"
    if path.exists() and not overwrite:
        raise FileExistsError(f"Prediction snapshot already exists and is immutable: {path}")
    atomic_json(path, pred.to_json_dict())
    return path


def save_evaluation(root: Path, evaluation: dict, overwrite: bool = False) -> Path:
    path = root / "evaluations" / f"{evaluation['target_draw_date']}__{evaluation['model_name']}__{evaluation['model_version']}.json"
    if path.exists() and not overwrite:
        raise FileExistsError(f"Evaluation already exists: {path}")
    atomic_json(path, evaluation)
    return path


def load_prediction(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
