from datetime import date
import json

from lotto649.domain import Draw
import pytest

from lotto649.live import (
    evaluate_due_predictions,
    generate_next_predictions,
    next_draw_date,
    run_live_cycle,
)
from lotto649.notification import should_alert
from lotto649.research_protocol import draw_digest, snapshot_digest


def test_next_draw_date():
    assert next_draw_date(date(2026, 8, 12)) == date(2026, 8, 15)
    assert next_draw_date(date(2026, 8, 15)) == date(2026, 8, 19)


def test_notification_thresholds():
    cfg = {"notifications": {"min_final_hits": 4, "min_top12_hits": 5}}
    assert should_alert({"final_6_hits": 4, "top_12_hits": 2}, cfg)
    assert should_alert({"final_6_hits": 1, "top_12_hits": 5}, cfg)
    assert not should_alert({"final_6_hits": 3, "top_12_hits": 4}, cfg)


def test_future_evaluation_binds_snapshot_and_verified_data_boundary(tmp_path):
    target = date(2027, 1, 6)
    payload = {
        "target_draw_date": target.isoformat(),
        "generated_at": "2027-01-03T12:00:00-05:00",
        "model_name": "audit_model",
        "model_version": "v9.0.0",
        "probabilities": {str(number): 6 / 49 for number in range(1, 50)},
        "top6": [1, 2, 3, 4, 5, 6],
        "top12": list(range(1, 13)),
        "top18": list(range(1, 19)),
        "final_combination": [1, 2, 3, 4, 5, 6],
        "metadata": {
            "role": "shadow",
            "history_draws": 2,
            "history_through": "2027-01-02",
        },
    }
    prediction_path = tmp_path / "predictions" / (
        "2027-01-06__audit_model__v9.0.0.json"
    )
    prediction_path.parent.mkdir()
    prediction_path.write_text(json.dumps(payload), encoding="utf-8")
    draws = [
        Draw(date(2027, 1, 2), (8, 9, 10, 11, 12, 13), 14),
        Draw(target, (1, 2, 3, 4, 5, 6), 7),
    ]
    cfg = {"_root": str(tmp_path), "notifications": {"enabled": False}}

    evaluations = evaluate_due_predictions(cfg, draws)

    assert len(evaluations) == 1
    evaluation = evaluations[0]
    assert evaluation["prediction_snapshot_path"] == (
        "predictions/2027-01-06__audit_model__v9.0.0.json"
    )
    assert evaluation["prediction_snapshot_digest"] == snapshot_digest(payload)
    assert evaluation["actual_draw_digest"] == draw_digest(draws[-1])
    assert evaluation["verified_data_draw_count"] == 2
    assert evaluation["verified_data_history_through"] == "2027-01-06"
    saved = json.loads(
        (tmp_path / "evaluations" / prediction_path.name).read_text(encoding="utf-8")
    )
    assert saved == evaluation


def test_research_config_cannot_run_or_generate_live_predictions(tmp_path):
    cfg = {
        "_root": str(tmp_path),
        "live": {"enabled": False, "models": [], "shadow_models": []},
    }
    draws = [Draw(date(2027, 1, 2), (1, 2, 3, 4, 5, 6), 7)]

    with pytest.raises(RuntimeError, match="live execution is disabled"):
        generate_next_predictions(cfg, draws)
    with pytest.raises(RuntimeError, match="live execution is disabled"):
        evaluate_due_predictions(cfg, draws)
    with pytest.raises(RuntimeError, match="live execution is disabled"):
        run_live_cycle(cfg)
