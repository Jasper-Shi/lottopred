from __future__ import annotations

from .baselines import RandomBaseline, LongFrequencyModel, RecentFrequencyModel, EmaGapModel
from .logistic import LogisticNumberModel
from .ensemble import EnsembleModel
from .v2_statistical import V2StatisticalModel
from .v3_boosting import V3BoostingModel
from .v4_ensemble import V4EnsembleModel


def build_models(cfg: dict, requested: list[str] | None = None):
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
    requested = requested if requested is not None else cfg["backtest"].get("models", list(base))
    unknown = set(requested) - set(base)
    if unknown:
        raise ValueError(f"Unknown models requested: {sorted(unknown)}")
    return {name: base[name] for name in requested}
