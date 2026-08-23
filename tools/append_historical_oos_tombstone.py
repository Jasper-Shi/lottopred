#!/usr/bin/env python3
"""Append or validate the historical OOS data-integrity tombstone offline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from lotto649.historical_oos_tombstone import (
    HistoricalOOSTombstoneError,
    append_data_integrity_tombstone,
    validate_data_integrity_tombstone,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--effective-date", required=True)
    parser.add_argument("--incident-id", required=True)
    parser.add_argument("--incident-path", required=True)
    parser.add_argument("--incident-sha256", required=True)
    parser.add_argument("--incident-artifact-commit", required=True)
    parser.add_argument("--seal-path", required=True)
    parser.add_argument("--seal-sha256", required=True)
    parser.add_argument("--sealed-artifact-commit", required=True)
    parser.add_argument(
        "--deployment-status",
        choices=("awaiting_main_branch_pin", "pinned_to_main_branch"),
        required=True,
    )
    parser.add_argument("--main-deployment-commit")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()

    operation = (
        validate_data_integrity_tombstone
        if args.validate_only
        else append_data_integrity_tombstone
    )
    try:
        result = operation(
            ledger_path=args.ledger,
            effective_date=args.effective_date,
            incident_id=args.incident_id,
            incident_path=args.incident_path,
            incident_sha256=args.incident_sha256,
            incident_artifact_commit=args.incident_artifact_commit,
            seal_path=args.seal_path,
            seal_sha256=args.seal_sha256,
            sealed_artifact_commit=args.sealed_artifact_commit,
            deployment_status=args.deployment_status,
            main_deployment_commit=args.main_deployment_commit,
        )
    except HistoricalOOSTombstoneError as exc:
        parser.exit(1, f"historical OOS tombstone error: {exc}\n")
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
