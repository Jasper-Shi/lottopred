from __future__ import annotations

from datetime import date

from .base import ProbabilityModel, normalize_expected_six
from ..domain import Draw


class V4EnsembleModel(ProbabilityModel):
    """Diversified ensemble of independent-ish V1/V2/V3 signal families."""
    name = "v4_ensemble"

    def __init__(self, members: list[tuple[ProbabilityModel, float]]):
        self.members = members

    def predict(self, history: list[Draw], target_date: date) -> dict[int, float]:
        total = sum(w for _, w in self.members)
        out = {n: 0.0 for n in range(1, 50)}
        for model, weight in self.members:
            p = model.predict(history, target_date)
            for n in out:
                out[n] += weight * p[n] / total
        return normalize_expected_six(out)
