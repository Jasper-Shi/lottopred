from datetime import date
from pathlib import Path
import sys

import pytest

from lotto649.domain import Draw


ROOT = Path(__file__).resolve().parents[1]


def test_default_backtest_suite_excludes_v3_and_v4_historical_recomputation():
    from lotto649.config import load_config

    cfg = load_config(ROOT / "config.yaml")

    assert cfg["backtest"]["models"] == [
        "random",
        "ema_gap",
        "v2_statistical",
    ]


def test_prospective_monitor_is_read_only_and_never_auto_claims_or_scores():
    workflow = (ROOT / ".github" / "workflows" / "prospective.yml").read_text(
        encoding="utf-8"
    )

    assert "contents: read" in workflow
    assert "workflow_run:" in workflow
    assert "fetch-depth: 0" in workflow
    assert "requirements-live.lock" in workflow
    assert "prospective-audit --experiment V3_frozen_shadow_cohort" in workflow
    assert "raw_count == minimum - 1" in workflow
    assert "prospective-claim" not in workflow
    assert "prospective-formal-look" not in workflow
    assert "contents: write" not in workflow
    assert "git commit" not in workflow


def test_ci_tests_install_the_frozen_live_dependency_constraints():
    workflow = (ROOT / ".github" / "workflows" / "test.yml").read_text(
        encoding="utf-8"
    )

    assert "python-version: '3.12'" in workflow
    assert "python -m pip install -c requirements-live.lock -e '.[dev]'" in workflow


def test_prospective_audit_help_covers_active_and_closed_cohorts(
    monkeypatch,
    capsys,
):
    import lotto649.cli as cli

    monkeypatch.setattr(sys, "argv", ["lotto649", "--help"])

    with pytest.raises(SystemExit) as exc_info:
        cli.main()

    assert exc_info.value.code == 0
    output = capsys.readouterr().out
    assert "active or closed" in output
    assert "prospective cohort" in output


def test_backtest_cli_applies_an_explicit_consumed_regression_model_subset(
    tmp_path,
    monkeypatch,
    capsys,
):
    import lotto649.cli as cli

    csv_path = tmp_path / "draws.csv"
    csv_path.write_text("fixture\n", encoding="utf-8")
    cfg = {
        "_root": str(tmp_path),
        "data": {"processed_csv": str(csv_path)},
        "backtest": {
            "test_start": "2025-01-01",
            "test_end": "2025-01-08",
            "models": ["v3_boosting"],
        },
    }
    draw = Draw(date(2024, 12, 28), (1, 2, 3, 4, 5, 6), 7)
    observed = {}

    class Summary:
        def to_string(self, *, index):
            assert index is False
            return "consumed regression"

    def fake_run_backtest(draws, effective_cfg, start, end, reports):
        observed.update(
            draws=draws,
            models=effective_cfg["backtest"]["models"],
            start=start,
            end=end,
            reports=reports,
        )
        return object()

    monkeypatch.setattr(cli, "load_config", lambda _path: cfg)
    monkeypatch.setattr(cli, "load_draws", lambda _path: [draw])
    monkeypatch.setattr(cli, "run_backtest", fake_run_backtest)
    monkeypatch.setattr(cli, "summarize", lambda _frame: Summary())
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "lotto649",
            "backtest",
            "--models",
            "random",
            "ema_gap",
            "v2_statistical",
        ],
    )

    cli.main()

    assert observed == {
        "draws": [draw],
        "models": ["random", "ema_gap", "v2_statistical"],
        "start": date(2025, 1, 1),
        "end": date(2025, 1, 8),
        "reports": Path(tmp_path) / "reports",
    }
    assert capsys.readouterr().out.strip() == "consumed regression"
