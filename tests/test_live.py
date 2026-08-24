import json
from datetime import UTC, date, datetime
from types import SimpleNamespace

import pytest

from lotto649 import live
from lotto649.domain import Draw, Prediction
from lotto649.live import next_draw_date
from lotto649.notification import should_alert


def test_next_draw_date():
    assert next_draw_date(date(2026, 8, 12)) == date(2026, 8, 15)
    assert next_draw_date(date(2026, 8, 15)) == date(2026, 8, 19)


def test_notification_thresholds():
    cfg = {"notifications": {"min_final_hits": 4, "min_top12_hits": 5}}
    assert should_alert({"final_6_hits": 4, "top_12_hits": 2}, cfg)
    assert should_alert({"final_6_hits": 1, "top_12_hits": 5}, cfg)
    assert not should_alert({"final_6_hits": 3, "top_12_hits": 4}, cfg)


def test_due_evaluation_records_prediction_source_from_publication_commit(
    tmp_path,
    monkeypatch,
):
    publication_commit = "1" * 40
    actual = Draw(date(2026, 8, 22), (1, 2, 3, 4, 5, 6), 7)
    prediction = Prediction(
        target_draw_date=actual.draw_date,
        generated_at=datetime(2026, 8, 20, tzinfo=UTC),
        model_name="candidate",
        model_version="v1.0.0",
        probabilities={number: 6 / 49 for number in range(1, 50)},
        top6=[1, 2, 3, 4, 5, 6],
        top12=list(range(1, 13)),
        top18=list(range(1, 19)),
        final_combination=[1, 2, 3, 4, 5, 6],
        metadata={},
    )
    prediction_relative = "predictions/2026-08-22__candidate__v1.0.0.json"
    prediction_path = tmp_path / prediction_relative
    prediction_path.parent.mkdir()
    prediction_path.write_text(
        json.dumps(prediction.to_json_dict()),
        encoding="utf-8",
    )
    prediction_source = {
        "kind": "verified_operational_history",
        "history_publication_commit": "2" * 40,
        "prediction_origin_commit": "3" * 40,
    }
    provenance_calls = []
    saved = []

    def prediction_provenance(repository, publication, relative):
        provenance_calls.append((repository, publication, relative))
        return prediction_source

    monkeypatch.setattr(
        live,
        "evaluation_prediction_source",
        prediction_provenance,
        raising=False,
    )
    monkeypatch.setattr(
        live,
        "operational_history_provenance",
        lambda _history: {"epoch": "verified"},
    )
    monkeypatch.setattr(
        live,
        "save_evaluation",
        lambda _root, evaluation: saved.append(evaluation),
    )

    evaluations = live._evaluate_due_predictions(
        {
            "_root": str(tmp_path),
            "notifications": {"enabled": False},
        },
        SimpleNamespace(
            draws=(actual,),
            registry=SimpleNamespace(resolved_revision=publication_commit),
        ),
    )

    assert provenance_calls == [
        (tmp_path, publication_commit, prediction_relative),
    ]
    assert evaluations[0]["prediction_source"] == prediction_source
    assert saved == evaluations


def test_prediction_source_failure_prevents_evaluation_save_and_email(
    tmp_path,
    monkeypatch,
):
    actual = Draw(date(2026, 8, 22), (1, 2, 3, 4, 5, 6), 7)
    prediction = Prediction(
        target_draw_date=actual.draw_date,
        generated_at=datetime(2026, 8, 20, tzinfo=UTC),
        model_name="candidate",
        model_version="v1.0.0",
        probabilities={number: 6 / 49 for number in range(1, 50)},
        top6=[1, 2, 3, 4, 5, 6],
        top12=list(range(1, 13)),
        top18=list(range(1, 19)),
        final_combination=[1, 2, 3, 4, 5, 6],
        metadata={},
    )
    prediction_path = tmp_path / "predictions/2026-08-22__candidate__v1.0.0.json"
    prediction_path.parent.mkdir()
    prediction_path.write_text(
        json.dumps(prediction.to_json_dict()),
        encoding="utf-8",
    )
    side_effects = []

    def reject_prediction_source(*_args):
        raise RuntimeError("prediction provenance rejected")

    monkeypatch.setattr(
        live,
        "evaluation_prediction_source",
        reject_prediction_source,
        raising=False,
    )
    monkeypatch.setattr(
        live,
        "operational_history_provenance",
        lambda _history: {"epoch": "verified"},
    )
    monkeypatch.setattr(live, "should_alert", lambda _evaluation, _cfg: True)
    monkeypatch.setattr(
        live,
        "send_hit_alert",
        lambda _evaluation: side_effects.append("email"),
    )
    monkeypatch.setattr(
        live,
        "save_evaluation",
        lambda _root, _evaluation: side_effects.append("save"),
    )

    with pytest.raises(RuntimeError, match="prediction provenance rejected"):
        live._evaluate_due_predictions(
            {
                "_root": tmp_path,
                "notifications": {"enabled": True},
            },
            SimpleNamespace(
                draws=(actual,),
                registry=SimpleNamespace(resolved_revision="1" * 40),
            ),
        )

    assert side_effects == []
