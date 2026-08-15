from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from ..domain import Draw


class ProbabilityModel(ABC):
    name: str

    @abstractmethod
    def predict(self, history: list[Draw], target_date: date) -> dict[int, float]:
        raise NotImplementedError


def normalize_expected_six(scores: dict[int, float]) -> dict[int, float]:
    arr = [max(float(scores.get(n, 0.0)), 1e-9) for n in range(1, 50)]
    total = sum(arr)
    return {n: min(0.999999, arr[n - 1] * 6.0 / total) for n in range(1, 50)}
