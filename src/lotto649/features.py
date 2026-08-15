from __future__ import annotations

import numpy as np
import pandas as pd

from .domain import Draw

BASE_P = 6 / 49


def indicator_matrix(draws: list[Draw]) -> np.ndarray:
    m = np.zeros((len(draws), 49), dtype=float)
    for r, d in enumerate(draws):
        for n in d.numbers:
            m[r, n - 1] = 1.0
    return m


def number_feature_frame(history: list[Draw], target_weekday: int, windows=(10, 25, 50, 100, 250), ema_half_life=35) -> pd.DataFrame:
    if not history:
        raise ValueError("history is empty")
    mat = indicator_matrix(history)
    rows = []
    alpha = 1 - np.exp(np.log(0.5) / ema_half_life)
    weights = (1 - alpha) ** np.arange(len(history) - 1, -1, -1)
    weights /= weights.sum()
    latest = set(history[-1].numbers)
    recent_sets = [set(d.numbers) for d in history]
    for n in range(1, 50):
        x = mat[:, n - 1]
        last_idx = np.flatnonzero(x)
        gap = len(history) if len(last_idx) == 0 else len(history) - 1 - int(last_idx[-1])
        row = {
            "number": n,
            "long_freq": float(x.mean()),
            "ema_freq": float(np.dot(x, weights)),
            "gap": float(gap),
            "in_prev": float(n in latest),
            "weekday": float(target_weekday),
            "number_scaled": n / 49.0,
        }
        for w in windows:
            use = x[-min(w, len(x)):]
            row[f"freq_{w}"] = float(use.mean())
        for lag in (1, 2, 3, 5):
            row[f"seen_last_{lag}"] = float(any(n in s for s in recent_sets[-lag:]))
        rows.append(row)
    return pd.DataFrame(rows)


def structure_features(draw: Draw) -> dict[str, float]:
    nums = draw.numbers
    gaps = [b - a for a, b in zip(nums, nums[1:])]
    return {
        "sum": float(sum(nums)),
        "odd_count": float(sum(n % 2 for n in nums)),
        "high_count": float(sum(n >= 25 for n in nums)),
        "range": float(nums[-1] - nums[0]),
        "adjacent_pairs": float(sum(1 for g in gaps if g == 1)),
        "mean_gap": float(np.mean(gaps)),
    }


def repeat_count(a: Draw, b: Draw) -> int:
    return len(set(a.numbers) & set(b.numbers))
