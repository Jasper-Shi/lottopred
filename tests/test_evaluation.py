from datetime import date, datetime, timezone

from lotto649.domain import Draw, Prediction
from lotto649.evaluation import evaluate_prediction


def test_hits_and_probability_scores():
    p = {n: 6 / 49 for n in range(1, 50)}
    pred = Prediction(
        date(2026, 8, 12), datetime.now(timezone.utc), "x", "v1", p,
        [1, 2, 3, 4, 5, 6], list(range(1, 13)), list(range(1, 19)), [1, 2, 3, 4, 5, 6], {}
    )
    actual = Draw(date(2026, 8, 12), (1, 2, 9, 20, 30, 40), 7)
    ev = evaluate_prediction(pred, actual)
    assert ev["final_6_hits"] == 2
    assert ev["top_12_hits"] == 3
    assert ev["brier_score"] > 0
    assert ev["log_loss"] > 0
