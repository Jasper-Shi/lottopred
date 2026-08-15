from __future__ import annotations

from .baselines import RandomBaseline, LongFrequencyModel, RecentFrequencyModel, EmaGapModel
from .logistic import LogisticNumberModel
from .ensemble import EnsembleModel


def build_models(cfg: dict):
    logistic = LogisticNumberModel(
        training_draws=cfg["features"].get("logistic_training_draws", 480),
        min_samples=cfg["features"].get("min_logistic_samples", 300),
    )
    base = {
        "random": RandomBaseline(),
        "long_frequency": LongFrequencyModel(),
        "recent_frequency": RecentFrequencyModel(100),
        "ema_gap": EmaGapModel(),
        "logistic": logistic,
    }
    base["ensemble"] = EnsembleModel([
        (base["long_frequency"], 0.15),
        (base["recent_frequency"], 0.20),
        (base["ema_gap"], 0.20),
        (base["logistic"], 0.45),
    ])
    requested = cfg["backtest"].get("models", list(base))
    unknown = set(requested) - set(base)
    if unknown:
        raise ValueError(f"Unknown models requested: {sorted(unknown)}")
    return {name: base[name] for name in requested}
