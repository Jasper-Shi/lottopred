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
from .prospective import (
    audit_registered_cohort,
    claim_registered_formal_look,
    run_registered_formal_look,
)
from .research_protocol import load_experiment_registry
from .research_diagnostics import (
    run_registered_v5_diagnostics,
    run_registered_v6_diagnostics,
    run_registered_v7_diagnostics,
    run_registered_v8_diagnostics,
)


def main():
    p = argparse.ArgumentParser(prog="lotto649")
    p.add_argument("--config", default=None)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("bootstrap", help="Build/refresh historical data from configured sources")
    b = sub.add_parser("backtest", help="Run strict walk-forward backtest")
    b.add_argument("--start", default=None)
    b.add_argument("--end", default=None)
    b.add_argument(
        "--models",
        nargs="+",
        default=None,
        help="Explicit model subset for a labeled historical regression",
    )
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
    research_v7 = sub.add_parser(
        "research-v7",
        help="Run the frozen V7 historical diagnostic and role negative control",
    )
    research_v7.add_argument("--code-commit", required=True)
    research_v8 = sub.add_parser(
        "research-v8",
        help="Run the frozen V8 historical diagnostic and spectral controls",
    )
    research_v8.add_argument("--code-commit", required=True)
    prospective_audit = sub.add_parser(
        "prospective-audit",
        help="Audit immutable evidence for one active or closed prospective cohort",
    )
    prospective_audit.add_argument("--experiment", required=True)
    prospective_claim = sub.add_parser(
        "prospective-claim",
        help="Create the performance-blind claim for an exact ready checkpoint",
    )
    prospective_claim.add_argument("--experiment", required=True)
    prospective_formal = sub.add_parser(
        "prospective-formal-look",
        help="Run the sole formal look after its claim is committed",
    )
    prospective_formal.add_argument("--experiment", required=True)
    args = p.parse_args()
    cfg = load_config(args.config)

    if args.cmd == "bootstrap":
        csv_path = resolve_path(cfg, cfg["data"]["processed_csv"])
        existing = load_draws(csv_path) if csv_path.exists() else []
        draws = refresh_with_sources(existing, cfg)
        save_draws(draws, csv_path)
        print(json.dumps({"draws": len(draws), "first": draws[0].draw_date.isoformat(), "last": draws[-1].draw_date.isoformat(), "path": str(csv_path)}, indent=2))
    elif args.cmd == "backtest":
        csv_path = resolve_path(cfg, cfg["data"]["processed_csv"])
        if not csv_path.exists():
            raise SystemExit("Missing processed draw data. Run `lotto649 bootstrap` first.")
        draws = load_draws(csv_path)
        start = date.fromisoformat(args.start or cfg["backtest"]["test_start"])
        end = date.fromisoformat(args.end or cfg["backtest"]["test_end"])
        if args.models is not None:
            cfg["backtest"] = {**cfg["backtest"], "models": args.models}
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
    elif args.cmd == "research-v7":
        result = run_registered_v7_diagnostics(
            cfg,
            code_commit=args.code_commit,
            output_dir=Path(cfg["_root"]) / "reports",
        )
        print(json.dumps({key: value for key, value in result.items() if key != "report"}, indent=2))
    elif args.cmd == "research-v8":
        result = run_registered_v8_diagnostics(
            cfg,
            code_commit=args.code_commit,
            output_dir=Path(cfg["_root"]) / "reports",
        )
        print(json.dumps({key: value for key, value in result.items() if key != "report"}, indent=2))
    elif args.cmd == "prospective-audit":
        aggregate = audit_registered_cohort(
            Path(cfg["_root"]),
            args.experiment,
        )
        registration = load_experiment_registry(
            Path(cfg["_root"]) / "docs" / "experiments" / "registry.yaml"
        ).get(args.experiment)
        minimum = registration.prospective.minimum_eligible_draws
        print(
            json.dumps(
                {
                    "experiment_id": args.experiment,
                    "status": aggregate.status,
                    "eligible_evaluated_count": len(aggregate.eligible_evaluated),
                    "pending_count": len(aggregate.pending),
                    "excluded_count": len(aggregate.excluded),
                    "checkpoint_count": len(aggregate.checkpoint),
                    "remaining_to_checkpoint": max(
                        0,
                        minimum - len(aggregate.eligible_evaluated),
                    ),
                    "formal_look_count": aggregate.formal_look_count,
                },
                indent=2,
            )
        )
    elif args.cmd == "prospective-claim":
        path = claim_registered_formal_look(
            Path(cfg["_root"]),
            args.experiment,
        )
        print(
            json.dumps(
                {
                    "experiment_id": args.experiment,
                    "claim_path": str(path),
                    "next_step": "commit this claim before running the formal look",
                },
                indent=2,
            )
        )
    elif args.cmd == "prospective-formal-look":
        result = run_registered_formal_look(
            Path(cfg["_root"]),
            args.experiment,
        )
        print(
            json.dumps(
                {
                    "experiment_id": args.experiment,
                    "checkpoint_digest": result.checkpoint_digest,
                    "eligible_evaluated_count": result.eligible_evaluated_count,
                    "gate_outcome": result.gate_outcome,
                    "decision": result.decision,
                    "formal_claim_commit": result.formal_claim_commit,
                    "formal_attempt_path": result.formal_attempt_path,
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
