from __future__ import annotations

from datetime import date
import math
import numpy as np
import pandas as pd

from .domain import Draw
from .features import indicator_matrix, BASE_P


def _z(values: np.ndarray) -> np.ndarray:
    s = float(np.std(values))
    return (values - float(np.mean(values))) / (s + 1e-9)


def rich_number_feature_frame(history: list[Draw], target_date: date) -> pd.DataFrame:
    """Leakage-safe per-number features for V2-V4.

    Every statistic is computed only from draws strictly before target_date.
    Date features are intentionally weak/shrunk because calendar patterns are
    especially prone to false discovery.
    """
    if len(history) < 20:
        raise ValueError("need at least 20 historical draws")
    mat = indicator_matrix(history)
    n_draws = len(history)
    last = set(history[-1].numbers)
    last2 = set(history[-2].numbers) if n_draws >= 2 else set()
    last_sum = sum(history[-1].numbers)
    sums = np.array([sum(d.numbers) for d in history], dtype=float)

    # Exponential histories with several decay rates.
    ema_cols: dict[int, np.ndarray] = {}
    for half_life in (12, 35, 90):
        alpha = 1 - math.exp(math.log(0.5) / half_life)
        weights = (1 - alpha) ** np.arange(n_draws - 1, -1, -1)
        weights /= weights.sum()
        ema_cols[half_life] = weights @ mat

    # Conditional frequency by weekday/month, strongly shrunk to fair baseline.
    weekday_idx = [i for i, d in enumerate(history) if d.draw_date.weekday() == target_date.weekday()]
    month_idx = [i for i, d in enumerate(history) if d.draw_date.month == target_date.month]
    weekday_freq = mat[weekday_idx].mean(axis=0) if weekday_idx else np.full(49, BASE_P)
    month_freq = mat[month_idx].mean(axis=0) if month_idx else np.full(49, BASE_P)
    weekday_shrunk = (len(weekday_idx) * weekday_freq + 200 * BASE_P) / (len(weekday_idx) + 200)
    month_shrunk = (len(month_idx) * month_freq + 300 * BASE_P) / (len(month_idx) + 300)

    # Transition: candidate occurrence after any number from the previous draw.
    transition = np.zeros(49, dtype=float)
    if n_draws > 80:
        prev_mask = np.zeros(n_draws - 1, dtype=bool)
        for i, d in enumerate(history[:-1]):
            if set(d.numbers) & last:
                prev_mask[i] = True
        if prev_mask.any():
            transition = mat[1:][prev_mask].mean(axis=0)
    transition = (transition * max(1, int(np.sum(prev_mask))) + 250 * BASE_P) / (max(1, int(np.sum(prev_mask))) + 250) if n_draws > 80 else np.full(49, BASE_P)

    rows = []
    for number in range(1, 50):
        x = mat[:, number - 1]
        hit_idx = np.flatnonzero(x)
        gap = n_draws if len(hit_idx) == 0 else n_draws - 1 - int(hit_idx[-1])
        gaps_between = np.diff(hit_idx) if len(hit_idx) >= 3 else np.array([8.0])
        expected_gap = float(np.mean(gaps_between))
        row = {
            "number": number,
            "number_scaled": number / 49.0,
            "long_freq": float(x.mean()),
            "freq_10": float(x[-10:].mean()),
            "freq_25": float(x[-25:].mean()),
            "freq_50": float(x[-50:].mean()),
            "freq_100": float(x[-100:].mean()),
            "freq_250": float(x[-250:].mean()),
            "ema_12": float(ema_cols[12][number - 1]),
            "ema_35": float(ema_cols[35][number - 1]),
            "ema_90": float(ema_cols[90][number - 1]),
            "gap": float(gap),
            "gap_ratio": float(gap / max(expected_gap, 1.0)),
            "in_prev": float(number in last),
            "in_prev2": float(number in last2),
            "weekday_freq": float(weekday_shrunk[number - 1]),
            "month_freq": float(month_shrunk[number - 1]),
            "transition_freq": float(transition[number - 1]),
            "sum_prev_centered": float((last_sum - 150.0) / 45.0),
            "sum_ma5_centered": float((sums[-5:].mean() - 150.0) / 45.0),
            "sum_ma20_centered": float((sums[-20:].mean() - 150.0) / 45.0),
            "sum_slope5": float(np.polyfit(np.arange(min(5, len(sums))), sums[-5:], 1)[0] / 20.0),
            "target_weekday": float(target_date.weekday() / 6.0),
            "target_month_sin": float(math.sin(2 * math.pi * target_date.month / 12)),
            "target_month_cos": float(math.cos(2 * math.pi * target_date.month / 12)),
        }
        rows.append(row)
    return pd.DataFrame(rows)


def standardized_signal_scores(frame: pd.DataFrame) -> np.ndarray:
    """Conservative V2 handcrafted score; small coefficients limit overfit."""
    score = (
        0.22 * _z(frame["ema_35"].to_numpy())
        + 0.10 * _z(frame["freq_100"].to_numpy())
        + 0.08 * _z(frame["weekday_freq"].to_numpy())
        + 0.05 * _z(frame["month_freq"].to_numpy())
        + 0.12 * _z(frame["transition_freq"].to_numpy())
        - 0.04 * _z(frame["gap_ratio"].to_numpy())
        - 0.03 * frame["in_prev"].to_numpy()
    )
    return score
