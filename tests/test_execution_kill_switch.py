from __future__ import annotations

import importlib
import sys
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

import lotto649.live as live_module
from lotto649.domain import Draw

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
    from lotto649 import cli

    data_cfg = {"processed_csv": "data/processed/draws.csv"}
    if enablement is not _MISSING:
        data_cfg["refresh_enabled"] = enablement
    cfg = {"_root": str(tmp_path), "data": data_cfg}

    def forbidden(*_args, **_kwargs):
        raise AssertionError("disabled bootstrap reached a side-effect boundary")

    monkeypatch.setattr(cli, "load_config", lambda _path: cfg)
    monkeypatch.setattr(cli, "resolve_path", forbidden, raising=False)
    monkeypatch.setattr(cli, "load_draws", forbidden, raising=False)
    monkeypatch.setattr(cli, "refresh_with_sources", forbidden, raising=False)
    monkeypatch.setattr(cli, "save_draws", forbidden, raising=False)
    monkeypatch.setattr(sys, "argv", ["lotto649", "bootstrap"])

    with pytest.raises(SystemExit, match="data refresh is disabled"):
        cli.main()


def test_bootstrap_stays_blocked_until_verified_suffix_writer_exists(
    tmp_path,
    monkeypatch,
):
    from lotto649 import cli

    cfg = {
        "_root": str(tmp_path),
        "data": {
            "refresh_enabled": True,
            "processed_csv": "data/processed/draws.csv",
        },
    }

    def forbidden(*_args, **_kwargs):
        raise AssertionError("bootstrap reached the legacy mutable data path")

    monkeypatch.setattr(cli, "load_config", lambda _path: cfg)
    monkeypatch.setattr(cli, "resolve_path", forbidden, raising=False)
    monkeypatch.setattr(cli, "load_draws", forbidden, raising=False)
    monkeypatch.setattr(cli, "refresh_with_sources", forbidden, raising=False)
    monkeypatch.setattr(cli, "save_draws", forbidden, raising=False)
    monkeypatch.setattr(sys, "argv", ["lotto649", "bootstrap"])

    with pytest.raises(SystemExit, match="verified history append writer"):
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
    from lotto649 import cli

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
    monkeypatch.setattr(cli, "resolve_path", forbidden, raising=False)
    monkeypatch.setattr(cli, "load_draws", forbidden, raising=False)
    monkeypatch.setattr(cli, "run_backtest", forbidden)
    monkeypatch.setattr(cli, "summarize", forbidden)
    monkeypatch.setattr(sys, "argv", ["lotto649", "backtest"])

    with pytest.raises(SystemExit, match="backtest execution is disabled"):
        cli.main()


def test_cli_backtest_delegates_to_verified_operational_boundary(
    tmp_path,
    monkeypatch,
    capsys,
):
    from lotto649 import cli

    cfg = {
        "_root": str(tmp_path),
        "backtest": {
            "enabled": True,
            "test_start": "2025-01-01",
            "test_end": "2025-01-08",
        },
    }
    frame = object()
    calls = []

    def forbidden(*_args, **_kwargs):
        raise AssertionError("CLI backtest reached the legacy processed CSV")

    def fake_run_backtest(received_cfg, start, end, output_dir):
        calls.append((received_cfg, start, end, output_dir))
        return frame

    monkeypatch.setattr(cli, "load_config", lambda _path: cfg)
    monkeypatch.setattr(cli, "resolve_path", forbidden, raising=False)
    monkeypatch.setattr(cli, "load_draws", forbidden, raising=False)
    monkeypatch.setattr(cli, "run_backtest", fake_run_backtest)
    monkeypatch.setattr(
        cli,
        "summarize",
        lambda received: SimpleNamespace(
            to_string=lambda *, index: "verified" if received is frame else "wrong"
        ),
    )
    monkeypatch.setattr(sys, "argv", ["lotto649", "backtest"])

    cli.main()

    assert calls == [
        (
            cfg,
            date(2025, 1, 1),
            date(2025, 1, 8),
            tmp_path / "reports",
        )
    ]
    assert capsys.readouterr().out.strip() == "verified"


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

    def forbidden(*_args, **_kwargs):
        raise AssertionError("disabled live entry point reached a side effect")

    monkeypatch.setattr(live_module, "build_models", forbidden)
    monkeypatch.setattr(
        live_module, "load_operational_history", forbidden, raising=False
    )
    monkeypatch.setattr(live_module, "operational_history_provenance", forbidden)

    for entry_point, args in (
        (live_module.refresh_data, (cfg,)),
        (live_module.evaluate_due_predictions, (cfg,)),
        (live_module.generate_next_predictions, (cfg,)),
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

    monkeypatch.setattr(
        live_module, "load_operational_history", forbidden, raising=False
    )
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

    monkeypatch.setattr(
        live_module,
        "refresh_data",
        lambda _cfg: SimpleNamespace(draws=tuple(draws)),
    )
    monkeypatch.setattr(
        live_module,
        "_evaluate_due_predictions",
        lambda _cfg, _draws: [{"ok": True}],
    )
    monkeypatch.setattr(
        live_module,
        "_generate_next_predictions",
        lambda _cfg, _draws: [Path("prediction.json")],
    )

    assert live_module.run_live_cycle(cfg) == {
        "latest_draw": "2026-08-15",
        "draw_count": 1,
        "evaluations_created": 1,
        "predictions_created": ["prediction.json"],
    }


def test_live_refresh_stays_blocked_until_verified_suffix_writer_exists(
    tmp_path,
    monkeypatch,
):
    cfg = {
        "_root": str(tmp_path),
        "data": {
            "refresh_enabled": True,
            "processed_csv": "data/processed/draws.csv",
        },
        "live": {"enabled": True},
    }

    def forbidden(*_args, **_kwargs):
        raise AssertionError("live refresh reached the legacy mutable data path")

    monkeypatch.setattr(
        live_module, "load_operational_history", forbidden, raising=False
    )

    with pytest.raises(RuntimeError, match="verified history append writer"):
        live_module.refresh_data(cfg)

    with pytest.raises(RuntimeError, match="verified history append writer"):
        live_module.run_live_cycle(cfg)


@pytest.mark.parametrize(
    "enablement",
    [_MISSING, False, None, 1, "true"],
    ids=["missing", "false", "null", "integer", "string"],
)
def test_direct_backtest_requires_literal_true_before_model_or_report_access(
    tmp_path,
    monkeypatch,
    enablement,
):
    import lotto649.backtest as backtest_module

    backtest_cfg = {}
    if enablement is not _MISSING:
        backtest_cfg["enabled"] = enablement
    cfg = {"backtest": backtest_cfg}
    output_dir = tmp_path / "reports"

    def forbidden(*_args, **_kwargs):
        raise AssertionError("disabled direct backtest reached model construction")

    monkeypatch.setattr(backtest_module, "build_models", forbidden)
    monkeypatch.setattr(backtest_module, "load_operational_history", forbidden)
    monkeypatch.setattr(backtest_module, "operational_history_provenance", forbidden)

    with pytest.raises(RuntimeError, match="backtest execution is disabled"):
        backtest_module.run_backtest(
            cfg,
            date(2025, 1, 1),
            date(2025, 1, 8),
            output_dir,
        )

    assert not output_dir.exists()


def test_direct_backtest_accepts_literal_true_without_writing_when_no_output_requested(
    monkeypatch,
):
    import lotto649.backtest as backtest_module

    calls = []
    provenance_calls = []
    cfg = {
        "_root": "/verified-repository",
        "backtest": {"enabled": True, "min_history_draws": 300},
        "project": {"model_version": "v1.0.0"},
    }

    def fake_history(received_cfg):
        calls.append(received_cfg)
        return SimpleNamespace(draws=())

    def fake_provenance(history):
        provenance_calls.append(history)
        return {"epoch": "verified"}

    monkeypatch.setattr(backtest_module, "build_models", lambda _cfg: {})
    monkeypatch.setattr(backtest_module, "load_operational_history", fake_history)
    monkeypatch.setattr(
        backtest_module,
        "operational_history_provenance",
        fake_provenance,
    )

    frame = backtest_module.run_backtest(
        cfg,
        date(2025, 1, 1),
        date(2025, 1, 8),
    )

    assert frame.empty
    assert calls == [cfg]
    assert len(provenance_calls) == 1


@pytest.mark.parametrize(
    "module_name",
    ["lotto649.data_sources", "lotto649.data"],
    ids=["reconciled-refresh", "legacy-refresh"],
)
@pytest.mark.parametrize(
    "enablement",
    [_MISSING, False, None, 1, "true"],
    ids=["missing", "false", "null", "integer", "string"],
)
def test_direct_refresh_requires_literal_true_before_any_source_access(
    monkeypatch,
    module_name,
    enablement,
):
    refresh_module = importlib.import_module(module_name)
    data_cfg = {
        "history_url": "https://invalid.example/archive",
        "bridge_year_url": "https://invalid.example/{year}",
        "recent_url": "https://invalid.example/recent",
    }
    if enablement is not _MISSING:
        data_cfg["refresh_enabled"] = enablement

    def forbidden(*_args, **_kwargs):
        raise AssertionError("disabled direct refresh reached a network source")

    monkeypatch.setattr(refresh_module, "fetch_wclc_archive", forbidden)
    monkeypatch.setattr(refresh_module, "fetch_bridge_years", forbidden)
    monkeypatch.setattr(refresh_module, "fetch_wclc_recent_draws", forbidden)

    with pytest.raises(RuntimeError, match="data refresh is disabled"):
        refresh_module.refresh_with_sources([], {"data": data_cfg})


@pytest.mark.parametrize(
    "module_name",
    ["lotto649.data_sources", "lotto649.data"],
    ids=["reconciled-refresh", "legacy-refresh"],
)
def test_direct_refresh_accepts_literal_true_with_offline_sources(
    monkeypatch,
    module_name,
):
    refresh_module = importlib.import_module(module_name)
    monkeypatch.setattr(refresh_module, "fetch_wclc_archive", lambda _url: [])
    monkeypatch.setattr(
        refresh_module,
        "fetch_bridge_years",
        lambda _template, _start, _end: [],
    )
    monkeypatch.setattr(refresh_module, "fetch_wclc_recent_draws", lambda _url: [])
    if module_name == "lotto649.data_sources":
        monkeypatch.setattr(
            refresh_module,
            "reconcile_by_era",
            lambda existing, _archive, _bridge, _recent, _start: existing,
        )
    else:
        monkeypatch.setattr(refresh_module, "validate_continuity", lambda _draws: None)

    result = refresh_module.refresh_with_sources(
        [],
        {
            "data": {
                "refresh_enabled": True,
                "history_url": "offline://archive",
                "bridge_year_url": "offline://bridge/{year}",
                "recent_url": "offline://recent",
            }
        },
    )

    assert result == []


@pytest.mark.parametrize(
    "entry_point_name",
    ["evaluate_due_predictions", "generate_next_predictions"],
    ids=["evaluation", "generation"],
)
@pytest.mark.parametrize(
    "refresh_enabled",
    [_MISSING, False, None, 1, "true"],
    ids=["missing", "false", "null", "integer", "string"],
)
def test_evaluation_and_generation_require_literal_refresh_true_before_side_effects(
    monkeypatch,
    entry_point_name,
    refresh_enabled,
):
    data_cfg = {}
    if refresh_enabled is not _MISSING:
        data_cfg["refresh_enabled"] = refresh_enabled
    cfg = {
        "_root": "/must-not-be-read",
        "data": data_cfg,
        "live": {"enabled": True},
        "project": {"model_version": "v1.0.0"},
    }

    def forbidden(*_args, **_kwargs):
        raise AssertionError("partial live enablement reached a side effect")

    monkeypatch.setattr(live_module, "Path", forbidden)
    monkeypatch.setattr(live_module, "build_models", forbidden)
    monkeypatch.setattr(
        live_module, "load_operational_history", forbidden, raising=False
    )
    monkeypatch.setattr(live_module, "operational_history_provenance", forbidden)

    with pytest.raises(RuntimeError, match="data refresh is disabled"):
        getattr(live_module, entry_point_name)(cfg)


def test_evaluation_and_generation_stay_blocked_until_verified_suffix_writer_exists(
    monkeypatch,
):
    cfg = {
        "_root": "/must-not-be-read",
        "data": {"refresh_enabled": True},
        "live": {"enabled": True},
        "project": {"model_version": "v1.0.0"},
    }

    def forbidden(*_args, **_kwargs):
        raise AssertionError("public live helper bypassed the suffix writer")

    monkeypatch.setattr(
        live_module, "load_operational_history", forbidden, raising=False
    )
    monkeypatch.setattr(live_module, "build_models", forbidden)

    for entry_point in (
        live_module.evaluate_due_predictions,
        live_module.generate_next_predictions,
    ):
        with pytest.raises(RuntimeError, match="verified history append writer"):
            entry_point(cfg)
