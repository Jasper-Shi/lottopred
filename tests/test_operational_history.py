from __future__ import annotations

import json
import subprocess
from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from lotto649.domain import Draw, Prediction
from lotto649.operational_history import (
    OperationalHistoryConfigurationError,
    load_operational_history,
    operational_history_provenance,
)

ROOT = Path(__file__).resolve().parents[1]
INCIDENT_ID = "DI-2026-08-20-registered-history"
SEAL_PATH = f"evidence/data_integrity/{INCIDENT_ID}/seal.json"
SUFFIX_PATH = f"data/processed/epochs/{INCIDENT_ID}/live_draws.jsonl"
REGISTRY_PATH = f"evidence/operational_history/{INCIDENT_ID}/pin-registry.jsonl"
SEAL_SHA256 = "80397752105b567d6a8bdd3673b12ffa470a12efbd792719a4f6c89ef391f6fd"
SUFFIX_SHA256 = "b91be6a4057648abd86dc0e6fc5d762fc4cd9b222519c147d635703cc550a803"
SUFFIX_HEAD_SHA256 = "3022b98fefbe3dbbc80423574319c169edcc845bf2218152c6abe18d0be27475"
GENESIS_COMMIT = "a6857d6b4e6e532062f484bcce4466f76ba4327b"


def test_deployed_operational_history_loads_only_from_frozen_authority():
    history = load_operational_history({"_root": str(ROOT)})

    assert len(history.draws) == 4_444
    assert history.draws[-2] == Draw(date(2026, 8, 19), (6, 7, 10, 32, 33, 36), 11)
    assert history.draws[-1] == Draw(date(2026, 8, 22), (11, 13, 21, 31, 34, 45), 5)
    assert history.seal.path == SEAL_PATH
    assert history.seal.file_sha256 == SEAL_SHA256
    assert history.suffix.path == SUFFIX_PATH
    assert history.suffix.file_sha256 == SUFFIX_SHA256
    assert history.suffix.head_event_sha256 == SUFFIX_HEAD_SHA256
    assert operational_history_provenance(history) == {
        "epoch": INCIDENT_ID,
        "seal_sha256": SEAL_SHA256,
        "artifact_commit": "b04393944ef12f78417dfb6151343c72d4c2a2ac",
        "base_rows_sha256": (
            "58988bbb130be2142bc5a2b20df571cc458eabe66cd873773f55ca1dbfae8874"
        ),
        "base_draw_count": 4_442,
        "suffix_sha256": SUFFIX_SHA256,
        "suffix_head_sha256": SUFFIX_HEAD_SHA256,
        "suffix_event_count": 2,
        "suffix_evidence_commits": [
            "60dbd42a502850091508491f9011f9a08acf894f",
            "60dbd42a502850091508491f9011f9a08acf894f",
        ],
        "observed_revision": history.registry.resolved_revision,
        "publication_commit": GENESIS_COMMIT,
        "registry_path": REGISTRY_PATH,
        "registry_genesis_commit": GENESIS_COMMIT,
        "registry_git_blob": "e95aeaaa28d5c1b7e5fb636d0fc4a3c26ff31017",
        "registry_sha256": (
            "42a9df8ef861a5fad6e1d7e7639d3d9317e519c0e83e96d7b1148527215afb72"
        ),
        "registry_event_count": 1,
        "registry_head_sha256": (
            "22bcfe219c091dbcdb751ef7a2d9d5251f3040770de6e2e825ac5c64fc69c63d"
        ),
        "seal_git_blob": "23c05e7d2c1344f77085b228bfc919e88e3c4af3",
        "suffix_git_blob": "3fa0319cc9d98fc17c49d4917e222d2da10aef07",
        "suffix_commit": "0b476b6de1f6bed1382c29187fd5cdaa4f70c153",
        "latest_evidence_commit": ("60dbd42a502850091508491f9011f9a08acf894f"),
        "draw_count": 4_444,
        "history_through": "2026-08-22",
    }


def test_operational_history_reads_authority_from_git_not_worktree(tmp_path):
    repository = tmp_path / "repository"
    subprocess.run(
        ["git", "clone", "--no-local", "--quiet", str(ROOT), str(repository)],
        check=True,
        capture_output=True,
    )
    for relative in (SEAL_PATH, SUFFIX_PATH, REGISTRY_PATH):
        (repository / relative).write_bytes(b"FOREIGN WORKTREE BYTES\n")

    history = load_operational_history({"_root": str(repository)})

    assert len(history.draws) == 4_444
    assert history.draws[-1].draw_date == date(2026, 8, 22)


def test_operational_history_ignores_hostile_git_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("GIT_DIR", str(tmp_path / "foreign.git"))
    monkeypatch.setenv("GIT_OBJECT_DIRECTORY", str(tmp_path / "foreign-objects"))
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "core.repositoryformatversion")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "999")

    history = load_operational_history({"_root": str(ROOT)})

    assert len(history.draws) == 4_444


def test_operational_history_does_not_accept_caller_pin_overrides(
    tmp_path, monkeypatch
):
    from lotto649 import operational_history

    sentinel = object()
    captured = {}

    def fake_loader(repository, revision):
        captured["repository"] = repository
        captured["revision"] = revision
        return sentinel

    monkeypatch.setattr(
        operational_history,
        "resolve_repository_head",
        lambda _repository: "a" * 40,
    )
    monkeypatch.setattr(operational_history, "load_published_history", fake_loader)

    result = operational_history.load_operational_history(
        {
            "_root": str(tmp_path),
            "verified_history": {
                "expected_seal_sha256": "f" * 64,
                "expected_suffix_sha256": "e" * 64,
                "expected_suffix_head_sha256": "d" * 64,
            },
        }
    )

    assert result is sentinel
    assert captured == {
        "repository": tmp_path,
        "revision": "a" * 40,
    }


@pytest.mark.parametrize("root", [None, "", 1, object()])
def test_operational_history_requires_an_explicit_repository_root(root):
    with pytest.raises(
        OperationalHistoryConfigurationError,
        match="repository root",
    ):
        load_operational_history({"_root": root})


def test_backtest_report_carries_verified_history_provenance(monkeypatch):
    from lotto649 import backtest

    draws = (
        Draw(date(2026, 8, 19), (6, 7, 10, 32, 33, 36), 11),
        Draw(date(2026, 8, 22), (11, 13, 21, 31, 34, 45), 5),
    )
    provenance = {
        "epoch": INCIDENT_ID,
        "seal_sha256": SEAL_SHA256,
    }

    class FairModel:
        name = "fair"

        def predict(self, _history, _target_date):
            return {number: 6 / 49 for number in range(1, 50)}

    monkeypatch.setattr(
        backtest,
        "load_operational_history",
        lambda _cfg: SimpleNamespace(draws=draws),
    )
    monkeypatch.setattr(
        backtest,
        "operational_history_provenance",
        lambda _history: provenance,
    )
    monkeypatch.setattr(backtest, "build_models", lambda _cfg: {"fair": FairModel()})

    frame = backtest.run_backtest(
        {
            "_root": "/verified-repository",
            "backtest": {"enabled": True, "min_history_draws": 1},
            "prediction": {"candidate_pool_size": 12},
            "project": {"model_version": "test"},
        },
        date(2026, 8, 22),
        date(2026, 8, 22),
    )

    expected_provenance = json.dumps(
        provenance,
        sort_keys=True,
        separators=(",", ":"),
    )
    assert frame.loc[0, "operational_history"] == expected_provenance
    assert frame.loc[0, "training_history_draws"] == 1
    assert frame.loc[0, "training_history_through"] == "2026-08-19"
    assert backtest.summarize(frame).loc[0, "operational_history"] == (
        expected_provenance
    )


def test_empty_backtest_refuses_to_publish_unprovenanced_reports(
    tmp_path,
    monkeypatch,
):
    from lotto649 import backtest

    monkeypatch.setattr(
        backtest,
        "load_operational_history",
        lambda _cfg: SimpleNamespace(draws=()),
    )
    monkeypatch.setattr(
        backtest,
        "operational_history_provenance",
        lambda _history: {"epoch": INCIDENT_ID},
    )
    monkeypatch.setattr(backtest, "build_models", lambda _cfg: {})

    output_dir = tmp_path / "reports"
    with pytest.raises(RuntimeError, match="refusing to publish empty reports"):
        backtest.run_backtest(
            {
                "_root": str(tmp_path),
                "backtest": {"enabled": True, "min_history_draws": 1},
                "project": {"model_version": "test"},
            },
            date(2026, 8, 22),
            date(2026, 8, 22),
            output_dir,
        )

    assert not output_dir.exists()


def test_live_prediction_carries_verified_training_history(tmp_path, monkeypatch):
    from lotto649 import live

    draws = (Draw(date(2026, 8, 22), (11, 13, 21, 31, 34, 45), 5),)
    history = SimpleNamespace(draws=draws)
    provenance = {"epoch": INCIDENT_ID, "seal_sha256": SEAL_SHA256}
    captured = []

    class Model:
        name = "candidate"

    prediction = Prediction(
        target_draw_date=date(2026, 8, 26),
        generated_at=datetime(2026, 8, 23, tzinfo=UTC),
        model_name="candidate",
        model_version="test",
        probabilities={number: 6 / 49 for number in range(1, 50)},
        top6=[1, 2, 3, 4, 5, 6],
        top12=list(range(1, 13)),
        top18=list(range(1, 19)),
        final_combination=[1, 2, 3, 4, 5, 6],
        metadata={},
    )

    monkeypatch.setattr(
        live,
        "operational_history_provenance",
        lambda _history: provenance,
    )
    monkeypatch.setattr(
        live,
        "build_models",
        lambda _cfg, requested: {"candidate": Model()},
    )
    monkeypatch.setattr(
        live,
        "make_prediction",
        lambda *_args, **_kwargs: prediction,
    )
    monkeypatch.setattr(
        live,
        "save_prediction",
        lambda _root, saved: captured.append(saved) or Path("prediction.json"),
    )

    paths = live._generate_next_predictions(
        {
            "_root": str(tmp_path),
            "live": {"models": ["candidate"]},
            "project": {"model_version": "test"},
        },
        history,
    )

    assert paths == [Path("prediction.json")]
    assert captured[0].metadata["operational_history"] == provenance


def test_live_evaluation_carries_verified_actual_history(tmp_path, monkeypatch):
    from lotto649 import live

    actual = Draw(date(2026, 8, 22), (11, 13, 21, 31, 34, 45), 5)
    history = SimpleNamespace(
        draws=(actual,),
        registry=SimpleNamespace(resolved_revision=GENESIS_COMMIT),
    )
    provenance = {"epoch": INCIDENT_ID, "seal_sha256": SEAL_SHA256}
    prediction = Prediction(
        target_draw_date=actual.draw_date,
        generated_at=datetime(2026, 8, 20, tzinfo=UTC),
        model_name="candidate",
        model_version="test",
        probabilities={number: 6 / 49 for number in range(1, 50)},
        top6=[1, 2, 3, 4, 5, 6],
        top12=list(range(1, 13)),
        top18=list(range(1, 19)),
        final_combination=[1, 2, 3, 4, 5, 6],
        metadata={"operational_history": {"epoch": "legacy"}},
    )
    prediction_path = tmp_path / "predictions" / "candidate.json"
    prediction_path.parent.mkdir()
    prediction_path.write_text(
        json.dumps(prediction.to_json_dict()),
        encoding="utf-8",
    )
    captured = []

    monkeypatch.setattr(
        live,
        "operational_history_provenance",
        lambda _history: provenance,
    )
    monkeypatch.setattr(
        live,
        "evaluation_prediction_source",
        lambda _repository, _publication, _relative: {"kind": "test-fixture"},
    )
    monkeypatch.setattr(
        live,
        "save_evaluation",
        lambda _root, evaluation: captured.append(evaluation),
    )

    evaluations = live._evaluate_due_predictions(
        {
            "_root": str(tmp_path),
            "notifications": {"enabled": False},
        },
        history,
    )

    assert evaluations[0]["actual_history"] == provenance
    assert captured[0]["actual_history"] == provenance
