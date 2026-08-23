from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from .backtest import run_backtest, summarize
from .config import load_config
from .live import run_live_cycle


def _require_data_refresh_enabled(cfg: dict) -> None:
    data_cfg = cfg.get("data")
    if not isinstance(data_cfg, dict) or data_cfg.get("refresh_enabled") is not True:
        raise SystemExit(
            "data refresh is disabled; data.refresh_enabled must be explicitly true"
        )


def _require_backtest_enabled(cfg: dict) -> None:
    backtest_cfg = cfg.get("backtest")
    if not isinstance(backtest_cfg, dict) or backtest_cfg.get("enabled") is not True:
        raise SystemExit(
            "backtest execution is disabled; backtest.enabled must be explicitly true"
        )


def main():
    p = argparse.ArgumentParser(prog="lotto649")
    p.add_argument("--config", default=None)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser(
        "bootstrap", help="Build/refresh historical data from configured sources"
    )
    b = sub.add_parser("backtest", help="Run strict walk-forward backtest")
    b.add_argument("--start", default=None)
    b.add_argument("--end", default=None)
    sub.add_parser(
        "live",
        help="Refresh results, evaluate due predictions, create next predictions",
    )
    args = p.parse_args()
    cfg = load_config(args.config)

    if args.cmd == "bootstrap":
        _require_data_refresh_enabled(cfg)
        raise SystemExit(
            "verified history append writer is not implemented; "
            "bootstrap remains paused"
        )
    elif args.cmd == "backtest":
        _require_backtest_enabled(cfg)
        start = date.fromisoformat(args.start or cfg["backtest"]["test_start"])
        end = date.fromisoformat(args.end or cfg["backtest"]["test_end"])
        frame = run_backtest(cfg, start, end, Path(cfg["_root"]) / "reports")
        print(summarize(frame).to_string(index=False))
    elif args.cmd == "live":
        print(json.dumps(run_live_cycle(cfg), indent=2))


if __name__ == "__main__":
    main()
