from __future__ import annotations

from datetime import date

from .base import ProbabilityModel, normalize_expected_six
from ..domain import Draw


class EnsembleModel(ProbabilityModel):
    name = "ensemble"

    def __init__(self, members: list[tuple[ProbabilityModel, float]]):
        self.members = members

    def predict(self, history: list[Draw], target_date: date) -> dict[int, float]:
        out = {n: 0.0 for n in range(1, 50)}
        total_w = sum(w for _, w in self.members)
        for model, w in self.members:
            p = model.predict(history, target_date)
            for n in out:
                out[n] += w * p[n] / total_w
        return normalize_expected_six(out)
