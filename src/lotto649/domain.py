from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date, datetime
from typing import Iterable


@dataclass(frozen=True)
class Draw:
    draw_date: date
    numbers: tuple[int, int, int, int, int, int]
    bonus: int | None = None

    def __post_init__(self) -> None:
        nums = tuple(sorted(self.numbers))
        if len(nums) != 6 or len(set(nums)) != 6 or any(n < 1 or n > 49 for n in nums):
            raise ValueError(f"Invalid 6/49 numbers: {self.numbers}")
        if self.bonus is not None and not (1 <= self.bonus <= 49):
            raise ValueError(f"Invalid bonus: {self.bonus}")
        if self.bonus is not None and self.bonus in nums:
            raise ValueError(f"Bonus duplicates main number: {self.bonus}")
        object.__setattr__(self, "numbers", nums)


@dataclass
class Prediction:
    target_draw_date: date
    generated_at: datetime
    model_name: str
    model_version: str
    probabilities: dict[int, float]
    top6: list[int]
    top12: list[int]
    top18: list[int]
    final_combination: list[int]
    metadata: dict

    def to_json_dict(self) -> dict:
        d = asdict(self)
        d["target_draw_date"] = self.target_draw_date.isoformat()
        d["generated_at"] = self.generated_at.isoformat()
        d["probabilities"] = {str(k): v for k, v in self.probabilities.items()}
        return d


def hit_count(predicted: Iterable[int], actual: Iterable[int]) -> int:
    return len(set(predicted) & set(actual))
