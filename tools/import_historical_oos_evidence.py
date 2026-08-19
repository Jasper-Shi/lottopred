#!/usr/bin/env python3
"""Import or validate permanent historical OOS evidence without model execution."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from lotto649.historical_oos_evidence import (
    HistoricalOOSEvidenceError,
    import_legacy_historical_artifact,
    validate_historical_oos_evidence,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = Path("evidence/historical/actions/31888527837/manifest.json")
DEFAULT_LEDGER = Path("reports/historical_oos/global_opportunities.jsonl")


def _repo_path(repo_root: Path, value: object) -> Path:
    if not isinstance(value, str) or not value:
        raise HistoricalOOSEvidenceError("manifest contains an invalid source path")
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise HistoricalOOSEvidenceError(
            "manifest source paths must be repository-relative"
        )
    return repo_root / relative


def _source_paths(manifest: Mapping[str, Any]) -> list[str]:
    paths: set[str] = set()
    for bundle in manifest.get("legacy_bundles", []):
        if not isinstance(bundle, Mapping):
            raise HistoricalOOSEvidenceError("manifest legacy bundle is invalid")
        for key in ("archive_path", "detail_path", "summary_path"):
            value = bundle.get(key)
            _repo_path(ROOT, value)
            paths.add(str(value))
    for gap in manifest.get("coverage_gaps", []):
        if not isinstance(gap, Mapping):
            raise HistoricalOOSEvidenceError("manifest coverage gap is invalid")
        value = gap.get("source_path")
        _repo_path(ROOT, value)
        paths.add(str(value))
    for source in manifest.get("verified_snapshot_sources", []):
        if not isinstance(source, Mapping):
            raise HistoricalOOSEvidenceError("manifest verified source is invalid")
        for key in ("ledger_path", "report_path"):
            value = source.get(key)
            _repo_path(ROOT, value)
            paths.add(str(value))
    if not paths:
        sources = manifest.get("sources")
        if not isinstance(sources, Mapping):
            raise HistoricalOOSEvidenceError("manifest has no registered sources")
        for source in sources.values():
            if not isinstance(source, Mapping):
                raise HistoricalOOSEvidenceError("manifest source is invalid")
            value = source.get("path")
            _repo_path(ROOT, value)
            paths.add(str(value))
    return sorted(paths)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    manifest_path = (
        args.manifest if args.manifest.is_absolute() else repo_root / args.manifest
    )
    ledger_path = args.ledger if args.ledger.is_absolute() else repo_root / args.ledger
    try:
        manifest = json.loads(manifest_path.read_bytes())
        if not isinstance(manifest, Mapping):
            raise HistoricalOOSEvidenceError("manifest root must be an object")
        source_bytes = {
            path: _repo_path(repo_root, path).read_bytes()
            for path in _source_paths(manifest)
        }
        operation = (
            validate_historical_oos_evidence
            if args.validate_only
            else import_legacy_historical_artifact
        )
        result = operation(
            source_bytes=source_bytes,
            manifest=manifest,
            ledger_path=ledger_path,
        )
    except (OSError, json.JSONDecodeError, HistoricalOOSEvidenceError) as exc:
        parser.exit(1, f"historical OOS evidence error: {exc}\n")
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
