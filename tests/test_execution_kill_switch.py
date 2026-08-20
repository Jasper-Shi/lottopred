from __future__ import annotations

from datetime import date
from pathlib import Path
import sys

import pytest

from lotto649.domain import Draw
import lotto649.live as live_module


ROOT = Path(__file__).resolve().parents[1]
_MISSING = object()


def test_incident_config_explicitly_disables_mutating_execution():
    from lotto649.config import load_config

    cfg = load_config(ROOT / "config.yaml")

    assert cfg["data"]["refresh_enabled"] is False
    assert cfg["live"]["enabled"] is False
    assert cfg["backtest"]["enabled"] is False


@pytest.mark.parametrize(
    "enablement",
    [_MISSING, False, None, 1, "true"],
    ids=["missing", "false", "null", "integer", "string"],
)
def test_bootstrap_requires_literal_true_before_path_or_source_access(
    tmp_path,
    monkeypatch,
    enablement,
):
    import lotto649.cli as cli

    data_cfg = {"processed_csv": "data/processed/draws.csv"}
    if enablement is not _MISSING:
        data_cfg["refresh_enabled"] = enablement
    cfg = {"_root": str(tmp_path), "data": data_cfg}

    def forbidden(*_args, **_kwargs):
        raise AssertionError("disabled bootstrap reached a side-effect boundary")

    monkeypatch.setattr(cli, "load_config", lambda _path: cfg)
    monkeypatch.setattr(cli, "resolve_path", forbidden)
    monkeypatch.setattr(cli, "load_draws", forbidden)
    monkeypatch.setattr(cli, "refresh_with_sources", forbidden)
    monkeypatch.setattr(cli, "save_draws", forbidden)
    monkeypatch.setattr(sys, "argv", ["lotto649", "bootstrap"])

    with pytest.raises(SystemExit, match="data refresh is disabled"):
        cli.main()


@pytest.mark.parametrize(
    "enablement",
    [_MISSING, False, None, 1, "true"],
    ids=["missing", "false", "null", "integer", "string"],
)
def test_backtest_requires_literal_true_before_path_or_model_access(
    tmp_path,
    monkeypatch,
    enablement,
):
    import lotto649.cli as cli

    backtest_cfg = {
        "test_start": "2025-01-01",
        "test_end": "2025-01-08",
    }
    if enablement is not _MISSING:
        backtest_cfg["enabled"] = enablement
    cfg = {
        "_root": str(tmp_path),
        "data": {"processed_csv": "data/processed/draws.csv"},
        "backtest": backtest_cfg,
    }

    def forbidden(*_args, **_kwargs):
        raise AssertionError("disabled backtest reached an execution boundary")

    monkeypatch.setattr(cli, "load_config", lambda _path: cfg)
    monkeypatch.setattr(cli, "resolve_path", forbidden)
    monkeypatch.setattr(cli, "load_draws", forbidden)
    monkeypatch.setattr(cli, "run_backtest", forbidden)
    monkeypatch.setattr(cli, "summarize", forbidden)
    monkeypatch.setattr(sys, "argv", ["lotto649", "backtest"])

    with pytest.raises(SystemExit, match="backtest execution is disabled"):
        cli.main()


@pytest.mark.parametrize("live_enabled", [_MISSING, False, None, 1, "true"])
def test_live_entry_points_require_literal_true_before_side_effects(
    tmp_path,
    monkeypatch,
    live_enabled,
):
    live_cfg = {}
    if live_enabled is not _MISSING:
        live_cfg["enabled"] = live_enabled
    cfg = {
        "_root": str(tmp_path),
        "data": {
            "refresh_enabled": True,
            "processed_csv": "data/processed/draws.csv",
        },
        "live": live_cfg,
    }
    draws = [Draw(date(2026, 8, 15), (1, 2, 3, 4, 5, 6), 7)]

    def forbidden(*_args, **_kwargs):
        raise AssertionError("disabled live entry point reached a side effect")

    monkeypatch.setattr(live_module, "resolve_path", forbidden)
    monkeypatch.setattr(live_module, "build_models", forbidden)

    for entry_point, args in (
        (live_module.refresh_data, (cfg,)),
        (live_module.evaluate_due_predictions, (cfg, draws)),
        (live_module.generate_next_predictions, (cfg, draws)),
    ):
        with pytest.raises(RuntimeError, match="live execution is disabled"):
            entry_point(*args)

    monkeypatch.setattr(live_module, "refresh_data", forbidden)
    with pytest.raises(RuntimeError, match="live execution is disabled"):
        live_module.run_live_cycle(cfg)


@pytest.mark.parametrize("refresh_enabled", [_MISSING, False, None, 1, "true"])
def test_live_refresh_and_cycle_require_literal_refresh_true_first(
    tmp_path,
    monkeypatch,
    refresh_enabled,
):
    data_cfg = {"processed_csv": "data/processed/draws.csv"}
    if refresh_enabled is not _MISSING:
        data_cfg["refresh_enabled"] = refresh_enabled
    cfg = {
        "_root": str(tmp_path),
        "data": data_cfg,
        "live": {"enabled": True},
    }

    def forbidden(*_args, **_kwargs):
        raise AssertionError("disabled refresh reached a side effect")

    monkeypatch.setattr(live_module, "resolve_path", forbidden)
    with pytest.raises(RuntimeError, match="data refresh is disabled"):
        live_module.refresh_data(cfg)

    monkeypatch.setattr(live_module, "refresh_data", forbidden)
    with pytest.raises(RuntimeError, match="data refresh is disabled"):
        live_module.run_live_cycle(cfg)


def test_literal_true_allows_main_live_cycle_contract(monkeypatch):
    draws = [Draw(date(2026, 8, 15), (1, 2, 3, 4, 5, 6), 7)]
    cfg = {
        "data": {"refresh_enabled": True},
        "live": {"enabled": True},
    }

    monkeypatch.setattr(live_module, "refresh_data", lambda _cfg: draws)
    monkeypatch.setattr(
        live_module,
        "evaluate_due_predictions",
        lambda _cfg, _draws: [{"ok": True}],
    )
    monkeypatch.setattr(
        live_module,
        "generate_next_predictions",
        lambda _cfg, _draws: [Path("prediction.json")],
    )

    assert live_module.run_live_cycle(cfg) == {
        "latest_draw": "2026-08-15",
        "draw_count": 1,
        "evaluations_created": 1,
        "predictions_created": ["prediction.json"],
    }
