from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path

from .backtest import run_backtest, summarize
from .config import load_config, resolve_path
from .data import save_draws, load_draws
from .data_sources import refresh_with_sources
from .live import run_live_cycle
from .research_diagnostics import (
    run_registered_v5_diagnostics,
    run_registered_v6_diagnostics,
)


def main():
    p = argparse.ArgumentParser(prog="lotto649")
    p.add_argument("--config", default=None)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("bootstrap", help="Build/refresh historical data from configured sources")
    b = sub.add_parser("backtest", help="Run strict walk-forward backtest")
    b.add_argument("--start", default=None)
    b.add_argument("--end", default=None)
    sub.add_parser("live", help="Refresh results, evaluate due predictions, create next predictions")
    research_v5 = sub.add_parser(
        "research-v5", help="Run the frozen V5 historical diagnostic and negative control"
    )
    research_v5.add_argument("--code-commit", required=True)
    research_v6 = sub.add_parser(
        "research-v6",
        help="Run the frozen V6 historical diagnostic and negative control",
    )
    research_v6.add_argument("--code-commit", required=True)
    args = p.parse_args()
    cfg = load_config(args.config)
    csv_path = resolve_path(cfg, cfg["data"]["processed_csv"])

    if args.cmd == "bootstrap":
        existing = load_draws(csv_path) if csv_path.exists() else []
        draws = refresh_with_sources(existing, cfg)
        save_draws(draws, csv_path)
        print(json.dumps({"draws": len(draws), "first": draws[0].draw_date.isoformat(), "last": draws[-1].draw_date.isoformat(), "path": str(csv_path)}, indent=2))
    elif args.cmd == "backtest":
        if not csv_path.exists():
            raise SystemExit("Missing processed draw data. Run `lotto649 bootstrap` first.")
        draws = load_draws(csv_path)
        start = date.fromisoformat(args.start or cfg["backtest"]["test_start"])
        end = date.fromisoformat(args.end or cfg["backtest"]["test_end"])
        frame = run_backtest(draws, cfg, start, end, Path(cfg["_root"]) / "reports")
        print(summarize(frame).to_string(index=False))
    elif args.cmd == "live":
        print(json.dumps(run_live_cycle(cfg), indent=2))
    elif args.cmd == "research-v5":
        result = run_registered_v5_diagnostics(
            cfg,
            code_commit=args.code_commit,
            output_dir=Path(cfg["_root"]) / "reports",
        )
        print(json.dumps({key: value for key, value in result.items() if key != "report"}, indent=2))
    elif args.cmd == "research-v6":
        result = run_registered_v6_diagnostics(
            cfg,
            code_commit=args.code_commit,
            output_dir=Path(cfg["_root"]) / "reports",
        )
        print(json.dumps({key: value for key, value in result.items() if key != "report"}, indent=2))


if __name__ == "__main__":
    main()
