#!/usr/bin/env python3
"""Seal the corrected historical-data epoch from immutable Git objects only.

The seal is a second-stage commitment.  It does not read any incident artifact
from the worktree: every artifact and code identity is resolved from the
registered artifact commit.  Validation additionally requires a caller-owned
SHA-256 of the complete seal file, so a coordinated rewrite of the seal and its
self hash cannot create its own trust root.
"""

from __future__ import annotations

import argparse
import csv
import hmac
import io
import json
import math
import os
import re
import secrets
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from hashlib import sha1, sha256
from pathlib import Path
from typing import Any, NoReturn

_SHA1_RE = re.compile(r"[0-9a-f]{40}")
_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_INCIDENT_SCHEMA = "lotto649-data-integrity-incident-v1"
_SOURCE_INDEX_SCHEMA = "lotto649-official-source-index-v1"
_REVIEW_SCHEMA = "lotto649-reviewed-adjudication-v1"
_MANIFEST_SCHEMA = "lotto649-historical-reconciliation-v1"
_SEAL_SCHEMA = "lotto649-data-integrity-seal-v1"
_SEALED_STATUS = "sealed_closed_corrected_epoch"


class IncidentSealError(RuntimeError):
    """Raised when an immutable incident cannot be sealed or validated."""


@dataclass(frozen=True)
class IncidentSealPolicy:
    """Externally registered identities required before a seal may be created."""

    incident_id: str
    artifact_commit: str
    artifact_parent: str
    artifact_commit_created_at: str
    old_commit: str
    old_path: str
    old_blob: str
    old_byte_sha256: str
    old_bytes: int
    old_draw_count: int
    old_rows_sha256: str
    manifest_sha256: str
    official_rows_sha256: str
    source_assets_sha256: str
    official_collection_line_sha256: str
    history_start: str
    history_through: str
    source_asset_count: int


_INCIDENT_ROOT = "evidence/data_integrity/DI-2026-08-20-registered-history"
_CORRECTED_PATH = (
    "data/processed/epochs/DI-2026-08-20-registered-history/corrected_draws.csv"
)
_INCIDENT_PATH = f"{_INCIDENT_ROOT}/incident.json"
_OFFICIAL_PATH = f"{_INCIDENT_ROOT}/official_draws.csv"
_MANIFEST_PATH = f"{_INCIDENT_ROOT}/reconciliation.manifest.json"
_REVIEW_PATH = f"{_INCIDENT_ROOT}/reviewed-adjudication.json"
_SOURCE_INDEX_PATH = f"{_INCIDENT_ROOT}/source-index.json"

ARTIFACT_PATHS = (
    _CORRECTED_PATH,
    _INCIDENT_PATH,
    _OFFICIAL_PATH,
    _MANIFEST_PATH,
    _REVIEW_PATH,
    _SOURCE_INDEX_PATH,
)
CODE_IDENTITY_PATHS = (
    "src/lotto649/data_integrity.py",
    "src/lotto649/official_history.py",
    "tests/test_data_integrity.py",
    "tests/test_data_integrity_incident.py",
    "tests/test_official_history.py",
    "tools/build_data_integrity_incident.py",
)
ARTIFACT_COMMIT_PATHS = tuple(sorted((*ARTIFACT_PATHS, *CODE_IDENTITY_PATHS)))

_EXPECTED_SUMMARY = {
    "old_count": 4_432,
    "official_count": 4_442,
    "decision_count": 4_444,
    "unchanged": 4_421,
    "inserted": 12,
    "deleted": 2,
    "updated": 9,
    "unresolved": 0,
    "corrected_count": 4_442,
}

REGISTERED_SEAL_POLICY = IncidentSealPolicy(
    incident_id="DI-2026-08-20-registered-history",
    artifact_commit="b04393944ef12f78417dfb6151343c72d4c2a2ac",
    artifact_parent="e585ae797ddcafa423121bf473d70b177a3bd92c",
    artifact_commit_created_at="2026-08-23T16:58:17Z",
    old_commit="90177c80cfb070038d79508fb2e73305a297f516",
    old_path="data/processed/draws.csv",
    old_blob="5afa689b7b206a27af78d14368588de00b4a4812",
    old_byte_sha256=(
        "edfb7f8a4a7711a630957d6f86b567e6b254caf7b1d1aaea0edf1d16a34155b3"
    ),
    old_bytes=136_236,
    old_draw_count=4_432,
    old_rows_sha256=(
        "257aef242bb898649b0923ac03f2271c7536ff7f840edf552c0dc6b4b03ce1dd"
    ),
    manifest_sha256=(
        "987bf9daaff088c66b43cef17ffdc71a9eb28d64f25aec5cbc88a2d55bdec32d"
    ),
    official_rows_sha256=(
        "58988bbb130be2142bc5a2b20df571cc458eabe66cd873773f55ca1dbfae8874"
    ),
    source_assets_sha256=(
        "1be14241443477f7ba347c8fe87605bb4c1367c7b7390f5f05762478a4c36b96"
    ),
    official_collection_line_sha256=(
        "7e3328896d5bb7950c10cf5b9cca0e4d7cadd7265c6d4a4f6b3dcc8793b0a88a"
    ),
    history_start="1982-06-12",
    history_through="2026-08-15",
    source_asset_count=109,
)


def _canonical_json(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise IncidentSealError("value is not finite canonical JSON") from exc


def _seal_bytes(value: Any) -> bytes:
    return _canonical_json(value) + b"\n"


def _sha256(raw: bytes) -> str:
    return sha256(raw).hexdigest()


def _reject_json_constant(value: str) -> NoReturn:
    raise IncidentSealError(f"JSON contains a non-finite number: {value}")


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise IncidentSealError(f"JSON contains a duplicate key: {key}")
        result[key] = value
    return result


def _assert_finite(value: Any) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise IncidentSealError("JSON contains a non-finite number")
    if isinstance(value, dict):
        for nested in value.values():
            _assert_finite(nested)
    elif isinstance(value, list):
        for nested in value:
            _assert_finite(nested)


def _load_json(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(
            raw,
            object_pairs_hook=_unique_json_object,
            parse_constant=_reject_json_constant,
        )
    except IncidentSealError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IncidentSealError(f"{label} is not valid UTF-8 JSON") from exc
    _assert_finite(value)
    if not isinstance(value, dict):
        raise IncidentSealError(f"{label} must contain a JSON object")
    return value


def _git_process(
    repository: Path, *arguments: str
) -> subprocess.CompletedProcess[bytes]:
    environment = os.environ.copy()
    environment["GIT_NO_REPLACE_OBJECTS"] = "1"
    environment["GIT_GRAFT_FILE"] = os.devnull
    try:
        return subprocess.run(
            ["git", "-C", str(repository), *arguments],
            check=False,
            capture_output=True,
            env=environment,
        )
    except OSError as exc:
        raise IncidentSealError("unable to execute Git") from exc


def _git(repository: Path, *arguments: str) -> bytes:
    result = _git_process(repository, *arguments)
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise IncidentSealError(f"Git verification failed: {detail}")
    return result.stdout


def _repository_root(repository: Path) -> Path:
    try:
        candidate = repository.resolve(strict=True)
    except OSError as exc:
        raise IncidentSealError("repository does not exist") from exc
    raw_top = _git(candidate, "rev-parse", "--show-toplevel").decode().strip()
    try:
        top = Path(raw_top).resolve(strict=True)
    except OSError as exc:
        raise IncidentSealError("Git worktree root does not exist") from exc
    if candidate != top:
        raise IncidentSealError("repository must be the Git worktree top level")
    return top


def _require_sha(value: str, pattern: re.Pattern[str], label: str) -> None:
    if not pattern.fullmatch(value):
        raise IncidentSealError(f"{label} must be a full lowercase hexadecimal hash")


def _git_blob(repository: Path, commit: str, path: str) -> tuple[bytes, dict[str, Any]]:
    entry = _git(repository, "ls-tree", "-z", commit, "--", path)
    if not entry.endswith(b"\0") or entry.count(b"\0") != 1:
        raise IncidentSealError(f"Git tree entry is missing or malformed: {path}")
    try:
        metadata, listed_path = entry[:-1].split(b"\t", 1)
        mode, object_type, blob = metadata.decode("ascii").split(" ", 2)
        decoded_path = listed_path.decode("utf-8")
    except (UnicodeDecodeError, ValueError) as exc:
        raise IncidentSealError(f"Git tree entry is malformed: {path}") from exc
    if decoded_path != path or mode != "100644" or object_type != "blob":
        raise IncidentSealError(f"Git tree identity mismatch: {path}")
    _require_sha(blob, _SHA1_RE, f"Git blob for {path}")
    raw = _git(repository, "cat-file", "blob", blob)
    calculated_blob = sha1(f"blob {len(raw)}\0".encode("ascii") + raw).hexdigest()
    if not hmac.compare_digest(calculated_blob, blob):
        raise IncidentSealError(f"Git blob content mismatch: {path}")
    return raw, {"git_blob": blob, "bytes": len(raw), "sha256": _sha256(raw)}


def _normalize_commit_time(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.strip())
    except ValueError as exc:
        raise IncidentSealError("artifact commit time is malformed") from exc
    if parsed.tzinfo is None:
        raise IncidentSealError("artifact commit time has no timezone")
    return parsed.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _verify_commit_boundary(repository: Path, policy: IncidentSealPolicy) -> None:
    for value, label in (
        (policy.artifact_commit, "artifact commit"),
        (policy.artifact_parent, "artifact parent"),
        (policy.old_commit, "registered old commit"),
    ):
        _require_sha(value, _SHA1_RE, label)
        resolved = _git(repository, "rev-parse", f"{value}^{{commit}}").decode().strip()
        if resolved != value:
            raise IncidentSealError(f"{label} does not resolve exactly")
        if _git(repository, "cat-file", "-t", value).decode().strip() != "commit":
            raise IncidentSealError(f"{label} is not a commit object")

    parents = (
        _git(repository, "show", "-s", "--format=%P", policy.artifact_commit)
        .decode()
        .strip()
        .split()
    )
    if parents != [policy.artifact_parent]:
        raise IncidentSealError("artifact commit parent identity mismatch")
    ancestry = _git_process(
        repository,
        "merge-base",
        "--is-ancestor",
        policy.old_commit,
        policy.artifact_parent,
    )
    if ancestry.returncode != 0:
        raise IncidentSealError("registered old commit is not an artifact ancestor")

    changed_raw = _git(
        repository,
        "diff-tree",
        "--no-commit-id",
        "--name-only",
        "--no-renames",
        "-r",
        "-z",
        policy.artifact_parent,
        policy.artifact_commit,
    )
    changed = tuple(
        sorted(part.decode("utf-8") for part in changed_raw.split(b"\0") if part)
    )
    if changed != ARTIFACT_COMMIT_PATHS:
        raise IncidentSealError("artifact commit exact path set mismatch")

    artifact_commit_created_at = _normalize_commit_time(
        _git(repository, "show", "-s", "--format=%cI", policy.artifact_commit)
        .decode()
        .strip()
    )
    if artifact_commit_created_at != policy.artifact_commit_created_at:
        raise IncidentSealError("artifact commit timestamp mismatch")


def _draw_dict(draw_date: date, numbers: tuple[int, ...], bonus: int) -> dict[str, Any]:
    return {
        "draw_date": draw_date.isoformat(),
        "numbers": list(numbers),
        "bonus": bonus,
    }


def _parse_draw_csv(
    raw: bytes, label: str
) -> tuple[tuple[date, tuple[int, ...], int], ...]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise IncidentSealError(f"{label} is not UTF-8") from exc
    rows = csv.reader(io.StringIO(text, newline=""))
    expected_header = [
        "draw_date",
        "n1",
        "n2",
        "n3",
        "n4",
        "n5",
        "n6",
        "bonus",
    ]
    try:
        header = next(rows)
    except StopIteration as exc:
        raise IncidentSealError(f"{label} is empty") from exc
    if header != expected_header:
        raise IncidentSealError(f"{label} has an unexpected CSV header")

    result: list[tuple[date, tuple[int, ...], int]] = []
    previous: date | None = None
    for line_number, row in enumerate(rows, start=2):
        if len(row) != 8:
            raise IncidentSealError(f"{label} row {line_number} has wrong width")
        try:
            draw_date = date.fromisoformat(row[0])
            numbers = tuple(int(value) for value in row[1:7])
            bonus = int(row[7])
        except ValueError as exc:
            raise IncidentSealError(f"{label} row {line_number} is malformed") from exc
        if row[0] != draw_date.isoformat():
            raise IncidentSealError(f"{label} row {line_number} date is noncanonical")
        if (
            len(numbers) != 6
            or tuple(sorted(numbers)) != numbers
            or len(set(numbers)) != 6
            or any(number < 1 or number > 49 for number in numbers)
            or bonus < 1
            or bonus > 49
            or bonus in numbers
        ):
            raise IncidentSealError(f"{label} row {line_number} violates 6/49")
        if previous is not None and draw_date <= previous:
            raise IncidentSealError(f"{label} is not strictly chronological")
        result.append((draw_date, numbers, bonus))
        previous = draw_date
    return tuple(result)


def _rows_sha256(rows: Sequence[tuple[date, tuple[int, ...], int]]) -> str:
    return _sha256(
        _canonical_json(
            [
                _draw_dict(draw_date, numbers, bonus)
                for draw_date, numbers, bonus in rows
            ]
        )
    )


def _row_dict(row: tuple[date, tuple[int, ...], int] | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return _draw_dict(*row)


def _row_sha256(row: tuple[date, tuple[int, ...], int] | None) -> str | None:
    return _sha256(_canonical_json(_row_dict(row))) if row is not None else None


def _expected_draw_dates(through: date) -> tuple[date, ...]:
    dates: list[date] = []
    cursor = date(1982, 6, 12)
    last_weekly = date(1985, 9, 7)
    while cursor <= min(last_weekly, through):
        dates.append(cursor)
        cursor += timedelta(days=7)
    cursor = date(1985, 9, 11)
    while cursor <= through:
        if cursor.weekday() in {2, 5}:
            dates.append(cursor)
        cursor += timedelta(days=1)
    return tuple(dates)


def _validate_registered_old(
    repository: Path, policy: IncidentSealPolicy
) -> tuple[dict[str, Any], tuple[tuple[date, tuple[int, ...], int], ...]]:
    raw, identity = _git_blob(repository, policy.old_commit, policy.old_path)
    rows = _parse_draw_csv(raw, "registered old CSV")
    expected = {
        "commit": policy.old_commit,
        "path": policy.old_path,
        "git_blob": policy.old_blob,
        "bytes": policy.old_bytes,
        "byte_sha256": policy.old_byte_sha256,
        "draw_count": policy.old_draw_count,
        "rows_sha256": policy.old_rows_sha256,
    }
    actual = {
        "commit": policy.old_commit,
        "path": policy.old_path,
        "git_blob": identity["git_blob"],
        "bytes": identity["bytes"],
        "byte_sha256": identity["sha256"],
        "draw_count": len(rows),
        "rows_sha256": _rows_sha256(rows),
    }
    if actual != expected:
        raise IncidentSealError("registered old history identity mismatch")
    return actual, rows


def _expected_source_paths(through: date) -> tuple[str, ...]:
    annual = [f"annual/{year}.html" for year in range(1982, through.year)]
    detail = [
        f"detail/{draw_date.isoformat()}.html"
        for draw_date in _expected_draw_dates(through)
        if draw_date.year == through.year
    ]
    return (*annual, *detail)


def _validate_source_index(
    source_index: dict[str, Any], policy: IncidentSealPolicy
) -> dict[str, Any]:
    expected_top = {
        "schema_version",
        "incident_id",
        "collection_asset_count",
        "source_assets_sha256",
        "official_draw_count",
        "official_collection_line_sha256",
        "official_json_rows_sha256",
        "assets",
    }
    if set(source_index) != expected_top:
        raise IncidentSealError("source index field set mismatch")
    if (
        source_index["schema_version"] != _SOURCE_INDEX_SCHEMA
        or source_index["incident_id"] != policy.incident_id
        or source_index["collection_asset_count"] != policy.source_asset_count
        or source_index["source_assets_sha256"] != policy.source_assets_sha256
        or source_index["official_draw_count"] != _EXPECTED_SUMMARY["official_count"]
        or source_index["official_collection_line_sha256"]
        != policy.official_collection_line_sha256
        or source_index["official_json_rows_sha256"] != policy.official_rows_sha256
    ):
        raise IncidentSealError("source index registered identity mismatch")
    assets = source_index["assets"]
    if not isinstance(assets, list) or len(assets) != policy.source_asset_count:
        raise IncidentSealError("source index asset collection mismatch")
    through = date.fromisoformat(policy.history_through)
    expected_paths = _expected_source_paths(through)
    actual_paths: list[str] = []
    identity_rows: list[dict[str, Any]] = []
    for asset in assets:
        if not isinstance(asset, dict) or set(asset) != {
            "relative_path",
            "scope",
            "source_type",
            "url",
            "bytes",
            "raw_sha256",
            "fetch_batch_completed_at",
        }:
            raise IncidentSealError("source index asset field set mismatch")
        relative_path = asset["relative_path"]
        if not isinstance(relative_path, str):
            raise IncidentSealError("source index asset path is malformed")
        if (
            not isinstance(asset["bytes"], int)
            or isinstance(asset["bytes"], bool)
            or asset["bytes"] <= 0
            or not isinstance(asset["raw_sha256"], str)
            or not _SHA256_RE.fullmatch(asset["raw_sha256"])
            or not isinstance(asset["url"], str)
        ):
            raise IncidentSealError("source index asset identity is malformed")
        actual_paths.append(relative_path)
        identity_rows.append(
            {
                "relative_path": relative_path,
                "url": asset["url"],
                "bytes": asset["bytes"],
                "raw_sha256": asset["raw_sha256"],
            }
        )
    if tuple(actual_paths) != expected_paths:
        raise IncidentSealError("source index exact asset path set mismatch")
    if _sha256(_canonical_json(identity_rows)) != policy.source_assets_sha256:
        raise IncidentSealError("source index aggregate identity mismatch")
    return {
        "asset_count": source_index["collection_asset_count"],
        "source_assets_sha256": source_index["source_assets_sha256"],
        "draw_count": source_index["official_draw_count"],
        "collection_line_sha256": source_index["official_collection_line_sha256"],
        "json_rows_sha256": source_index["official_json_rows_sha256"],
        "history_start": policy.history_start,
        "history_through": policy.history_through,
    }


def _validate_manifest(
    manifest: dict[str, Any],
    old_rows: Sequence[tuple[date, tuple[int, ...], int]],
    official_rows: Sequence[tuple[date, tuple[int, ...], int]],
    policy: IncidentSealPolicy,
) -> dict[str, Any]:
    if manifest.get("schema_version") != _MANIFEST_SCHEMA:
        raise IncidentSealError("reconciliation manifest schema mismatch")
    recorded = manifest.get("manifest_sha256")
    if recorded != policy.manifest_sha256:
        raise IncidentSealError("reconciliation manifest external pin mismatch")
    body = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    if _sha256(_canonical_json(body)) != policy.manifest_sha256:
        raise IncidentSealError("reconciliation manifest self hash mismatch")
    if (
        manifest.get("summary") != _EXPECTED_SUMMARY
        or manifest.get("closure_allowed") is not True
        or manifest.get("coverage_gaps") != []
        or manifest.get("corrected_rows_sha256") != policy.official_rows_sha256
        or manifest.get("provisional_rows_sha256") != policy.official_rows_sha256
    ):
        raise IncidentSealError("reconciliation manifest closure mismatch")
    coverage = manifest.get("coverage")
    expected_coverage_subset = {
        "actual_old_rows_sha256": policy.old_rows_sha256,
        "expected_old_rows_sha256": policy.old_rows_sha256,
        "actual_official_rows_sha256": policy.official_rows_sha256,
        "expected_official_rows_sha256": policy.official_rows_sha256,
        "expected_date_count": _EXPECTED_SUMMARY["official_count"],
        "history_start": policy.history_start,
        "history_through": policy.history_through,
    }
    if not isinstance(coverage, dict) or any(
        coverage.get(key) != value for key, value in expected_coverage_subset.items()
    ):
        raise IncidentSealError("reconciliation manifest coverage mismatch")

    old_by_date = {row[0]: row for row in old_rows}
    official_by_date = {row[0]: row for row in official_rows}
    union_dates = tuple(sorted(old_by_date.keys() | official_by_date.keys()))
    decisions = manifest.get("decisions")
    if not isinstance(decisions, list) or len(decisions) != len(union_dates):
        raise IncidentSealError("reconciliation decision set mismatch")
    counts = {"unchanged": 0, "inserted": 0, "deleted": 0, "updated": 0}
    for decision, draw_date in zip(decisions, union_dates, strict=True):
        if not isinstance(decision, dict):
            raise IncidentSealError("reconciliation decision is malformed")
        old = old_by_date.get(draw_date)
        official = official_by_date.get(draw_date)
        if old is None:
            category = "inserted"
            decision_type = "insert_missing_official_draw"
        elif official is None:
            category = "deleted"
            decision_type = "delete_spurious_wrong_year_row"
        elif old == official:
            category = "unchanged"
            decision_type = "unchanged"
        else:
            category = "updated"
            decision_type = "update_numbers_or_bonus"
        counts[category] += 1
        expected_resolution = (
            "exact_row_equality" if category == "unchanged" else "reviewed_adjudication"
        )
        if (
            decision.get("draw_date") != draw_date.isoformat()
            or decision.get("decision_type") != decision_type
            or decision.get("resolution_policy") != expected_resolution
            or decision.get("old_row") != _row_dict(old)
            or decision.get("official_row") != _row_dict(official)
            or decision.get("old_row_sha256") != _row_sha256(old)
            or decision.get("official_row_sha256") != _row_sha256(official)
        ):
            raise IncidentSealError("reconciliation decision differs from source rows")
        evidence_refs = decision.get("official_evidence_refs")
        if not isinstance(evidence_refs, list) or (
            category == "unchanged" and evidence_refs != []
        ):
            raise IncidentSealError("reconciliation decision evidence mismatch")
        if category != "unchanged" and len(evidence_refs) < 2:
            raise IncidentSealError("changed decision lacks adjudicated evidence")
    if counts != {
        key: _EXPECTED_SUMMARY[key]
        for key in ("unchanged", "inserted", "deleted", "updated")
    }:
        raise IncidentSealError("reconciliation decision counts mismatch")
    return dict(_EXPECTED_SUMMARY)


def _validate_review(
    review: dict[str, Any],
    old_rows: Sequence[tuple[date, tuple[int, ...], int]],
    official_rows: Sequence[tuple[date, tuple[int, ...], int]],
    policy: IncidentSealPolicy,
) -> None:
    if (
        review.get("schema_version") != _REVIEW_SCHEMA
        or review.get("incident_id") != policy.incident_id
        or review.get("summary") != _EXPECTED_SUMMARY
        or review.get("disposition")
        != "accept_official_history_for_all_enumerated_changes"
    ):
        raise IncidentSealError("reviewed adjudication identity mismatch")
    changes = review.get("changes")
    if not isinstance(changes, list) or len(changes) != 23:
        raise IncidentSealError("reviewed adjudication change set mismatch")
    old_by_date = {row[0]: row for row in old_rows}
    official_by_date = {row[0]: row for row in official_rows}
    expected: list[tuple[date, str]] = []
    for draw_date in sorted(old_by_date.keys() | official_by_date.keys()):
        old = old_by_date.get(draw_date)
        official = official_by_date.get(draw_date)
        if old == official:
            continue
        change_type = (
            "insert" if old is None else "delete" if official is None else "update"
        )
        expected.append((draw_date, change_type))
    actual: list[tuple[date, str]] = []
    for change in changes:
        if not isinstance(change, dict):
            raise IncidentSealError("reviewed adjudication change is malformed")
        try:
            draw_date = date.fromisoformat(change["draw_date"])
        except (KeyError, TypeError, ValueError) as exc:
            raise IncidentSealError("reviewed adjudication date is malformed") from exc
        change_type = change.get("change_type")
        old = old_by_date.get(draw_date)
        official = official_by_date.get(draw_date)
        if (
            change.get("old_row") != _row_dict(old)
            or change.get("official_row") != _row_dict(official)
            or change.get("old_row_sha256") != _row_sha256(old)
            or change.get("official_row_sha256") != _row_sha256(official)
        ):
            raise IncidentSealError("reviewed adjudication differs from source rows")
        actual.append((draw_date, change_type))
    if actual != expected:
        raise IncidentSealError("reviewed adjudication exact change set mismatch")


def _validate_incident(
    incident: dict[str, Any],
    registered_old: dict[str, Any],
    source_collection: dict[str, Any],
    artifact_identities: dict[str, dict[str, Any]],
    policy: IncidentSealPolicy,
) -> None:
    expected_keys = {
        "schema_version",
        "incident_id",
        "created_at",
        "status",
        "seal_status",
        "external_evidence_artifact_status",
        "scientific_disposition",
        "registered_old_source",
        "official_source",
        "reconciliation_summary",
        "manifest_sha256_external_pin",
        "reconciliation_authority",
        "artifact_inventory",
    }
    if set(incident) != expected_keys:
        raise IncidentSealError("incident field set mismatch")
    if (
        incident["schema_version"] != _INCIDENT_SCHEMA
        or incident["incident_id"] != policy.incident_id
        or incident["status"] != "reconciliation_closed_artifact_unsealed"
        or incident["seal_status"] != "awaiting_artifact_commit_seal"
        or incident["registered_old_source"] != registered_old
        or incident["official_source"] != source_collection
        or incident["reconciliation_summary"] != _EXPECTED_SUMMARY
        or incident["manifest_sha256_external_pin"] != policy.manifest_sha256
    ):
        raise IncidentSealError("incident registered metadata mismatch")
    expected_inventory_paths = set(ARTIFACT_PATHS) - {_INCIDENT_PATH}
    inventory = incident["artifact_inventory"]
    if not isinstance(inventory, dict) or set(inventory) != expected_inventory_paths:
        raise IncidentSealError("incident exact artifact inventory mismatch")
    for path in expected_inventory_paths:
        identity = artifact_identities[path]
        if inventory[path] != {
            "bytes": identity["bytes"],
            "sha256": identity["sha256"],
        }:
            raise IncidentSealError("incident artifact inventory identity mismatch")


def _build_seal_body(repository: Path, policy: IncidentSealPolicy) -> dict[str, Any]:
    repository = _repository_root(repository)
    _verify_commit_boundary(repository, policy)

    artifact_raw: dict[str, bytes] = {}
    artifact_identities: dict[str, dict[str, Any]] = {}
    for path in ARTIFACT_PATHS:
        raw, identity = _git_blob(repository, policy.artifact_commit, path)
        artifact_raw[path] = raw
        artifact_identities[path] = identity
    code_identities = {
        path: _git_blob(repository, policy.artifact_commit, path)[1]
        for path in CODE_IDENTITY_PATHS
    }

    registered_old, old_rows = _validate_registered_old(repository, policy)
    official_rows = _parse_draw_csv(artifact_raw[_OFFICIAL_PATH], "official CSV")
    corrected_rows = _parse_draw_csv(artifact_raw[_CORRECTED_PATH], "corrected CSV")
    expected_dates = _expected_draw_dates(date.fromisoformat(policy.history_through))
    if (
        tuple(row[0] for row in official_rows) != expected_dates
        or official_rows != corrected_rows
        or len(official_rows) != _EXPECTED_SUMMARY["official_count"]
        or _rows_sha256(official_rows) != policy.official_rows_sha256
    ):
        raise IncidentSealError(
            "corrected epoch differs from complete official history"
        )

    source_index = _load_json(artifact_raw[_SOURCE_INDEX_PATH], "source-index.json")
    source_collection = _validate_source_index(source_index, policy)
    manifest = _load_json(artifact_raw[_MANIFEST_PATH], "reconciliation manifest")
    summary = _validate_manifest(manifest, old_rows, official_rows, policy)
    review = _load_json(artifact_raw[_REVIEW_PATH], "reviewed adjudication")
    _validate_review(review, old_rows, official_rows, policy)
    incident = _load_json(artifact_raw[_INCIDENT_PATH], "incident.json")
    _validate_incident(
        incident,
        registered_old,
        source_collection,
        artifact_identities,
        policy,
    )

    corrected_identity = artifact_identities[_CORRECTED_PATH]
    manifest_identity = artifact_identities[_MANIFEST_PATH]
    return {
        "schema_version": _SEAL_SCHEMA,
        "incident_id": policy.incident_id,
        "artifact_commit": policy.artifact_commit,
        "artifact_parent": policy.artifact_parent,
        "artifact_commit_created_at": policy.artifact_commit_created_at,
        "status": _SEALED_STATUS,
        "registered_old_identity": registered_old,
        "artifacts": artifact_identities,
        "corrected_epoch": {
            "path": _CORRECTED_PATH,
            "git_blob": corrected_identity["git_blob"],
            "bytes": corrected_identity["bytes"],
            "file_sha256": corrected_identity["sha256"],
            "draw_count": len(corrected_rows),
            "rows_sha256": _rows_sha256(corrected_rows),
            "history_start": corrected_rows[0][0].isoformat(),
            "history_through": corrected_rows[-1][0].isoformat(),
        },
        "reconciliation_manifest": {
            "path": _MANIFEST_PATH,
            "git_blob": manifest_identity["git_blob"],
            "bytes": manifest_identity["bytes"],
            "file_sha256": manifest_identity["sha256"],
            "manifest_sha256": manifest["manifest_sha256"],
        },
        "source_collection": source_collection,
        "reconciliation_summary": summary,
        "code_identities": code_identities,
    }


def _exclusive_flags() -> int:
    flags = os.O_RDWR | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    return flags


def _open_unique_staging(path: Path) -> tuple[Path, int]:
    for _ in range(32):
        staging = path.parent / f".{path.name}.staging-{secrets.token_hex(16)}"
        try:
            return staging, os.open(staging, _exclusive_flags(), 0o644)
        except FileExistsError:
            continue
        except OSError as exc:
            raise IncidentSealError("unable to create seal staging file") from exc
    raise IncidentSealError("unable to allocate a unique seal staging path")


def _archive_owned_path(path: Path, raw_sha256: str) -> Path:
    """Move an owned residual out of its formal name without replacing anything."""
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise IncidentSealError("unable to bind failed-seal residual") from exc
    try:
        try:
            opened = os.fstat(descriptor)
        except OSError as exc:
            raise IncidentSealError("unable to bind failed-seal residual") from exc
        captured_identity = (opened.st_dev, opened.st_ino)
        captured_sha256 = _descriptor_sha256(descriptor)
        archive_identity = (
            raw_sha256
            if hmac.compare_digest(captured_sha256, raw_sha256)
            else f"untrusted-{captured_sha256}"
        )
        for _ in range(32):
            archive_directory = path.parent / (
                f".{path.name}.failed-{archive_identity}-{secrets.token_hex(16)}"
            )
            try:
                os.mkdir(archive_directory, 0o700)
            except FileExistsError:
                continue
            except OSError as exc:
                raise IncidentSealError(
                    "unable to reserve failed-seal archive"
                ) from exc
            archive_path = archive_directory / path.name
            moved = False
            primary_error: OSError | None = None
            try:
                os.rename(path, archive_path)
            except OSError as rename_exc:
                primary_error = rename_exc
                moved = _path_matches_identity(
                    archive_path, captured_identity
                ) and not os.path.lexists(path)
            else:
                moved = True
            if not moved:
                fallback_error: OSError | None = None
                try:
                    os.replace(path, archive_path)
                except OSError as exc:
                    fallback_error = exc
                    moved = _path_matches_identity(
                        archive_path, captured_identity
                    ) and not os.path.lexists(path)
                else:
                    moved = True
                if not moved:
                    try:
                        if not os.path.lexists(archive_path):
                            os.rmdir(archive_directory)
                    except OSError:
                        pass
                    raise IncidentSealError(
                        "unable to archive owned seal residual"
                    ) from ExceptionGroup(
                        "seal archive primary and fallback failures",
                        [
                            error
                            for error in (primary_error, fallback_error)
                            if error is not None
                        ],
                    )
            if (
                not _path_matches_identity(archive_path, captured_identity)
                or _descriptor_sha256(descriptor) != captured_sha256
                or os.path.lexists(path)
            ):
                raise IncidentSealError(
                    "failed-seal archive verification failed; residual at "
                    f"{archive_path}"
                )
            try:
                _fsync_parent(archive_path)
            except OSError as exc:
                raise IncidentSealError(
                    f"failed-seal archive durability failed; residual archived at "
                    f"{archive_path}"
                ) from exc
            try:
                _fsync_parent(path)
            except OSError as exc:
                raise IncidentSealError(
                    "failed-seal archive source-parent durability failed; residual "
                    f"archived at {archive_path}"
                ) from exc
            return archive_path
        raise IncidentSealError("unable to allocate failed-seal archive")
    finally:
        try:
            os.close(descriptor)
        except OSError:
            pass


def _remove_or_archive_owned(path: Path, raw_sha256: str) -> Path | None:
    try:
        os.unlink(path)
        return None
    except FileNotFoundError:
        return None
    except OSError:
        return _archive_owned_path(path, raw_sha256)


def _fsync_parent(path: Path) -> None:
    directory_flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        directory_flags |= os.O_DIRECTORY
    descriptor = os.open(path.parent, directory_flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _rollback_published_seal(path: Path, raw_sha256: str) -> Path | None:
    return _archive_owned_path(path, raw_sha256)


def _path_matches_identity(path: Path, owned_identity: tuple[int, int]) -> bool:
    try:
        current = os.lstat(path)
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise IncidentSealError("unable to inspect seal path ownership") from exc
    return (current.st_dev, current.st_ino) == owned_identity


def _descriptor_sha256(descriptor: int) -> str:
    digest = sha256()
    offset = 0
    try:
        while True:
            chunk = os.pread(descriptor, 1024 * 1024, offset)
            if not chunk:
                return digest.hexdigest()
            digest.update(chunk)
            offset += len(chunk)
    except OSError as exc:
        raise IncidentSealError("unable to verify seal staging bytes") from exc


def _published_seal_matches(
    path: Path,
    owned_identity: tuple[int, int],
    descriptor: int,
    raw_sha256: str,
) -> bool:
    try:
        opened = os.fstat(descriptor)
    except OSError as exc:
        raise IncidentSealError("unable to inspect seal descriptor") from exc
    if (opened.st_dev, opened.st_ino) != owned_identity or (
        _descriptor_sha256(descriptor) != raw_sha256
    ):
        return False
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        published_descriptor = os.open(path, flags)
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise IncidentSealError("unable to open published seal") from exc
    try:
        published = os.fstat(published_descriptor)
        published_identity = (published.st_dev, published.st_ino)
        if published_identity != owned_identity:
            return False
        if _descriptor_sha256(published_descriptor) != raw_sha256:
            return False
        return _path_matches_identity(path, published_identity)
    except OSError as exc:
        raise IncidentSealError("unable to inspect published seal") from exc
    finally:
        os.close(published_descriptor)


def _rollback_link_side_effect_if_owned(
    path: Path, owned_identity: tuple[int, int], raw_sha256: str
) -> Path | None:
    """Retire a formal hardlink created before a failed link call returned."""
    if not _path_matches_identity(path, owned_identity):
        return None
    return _rollback_published_seal(path, raw_sha256)


def _rollback_successful_link_result(
    path: Path, owned_identity: tuple[int, int], raw_sha256: str
) -> Path | None:
    """Retire the destination entry after os.link reported success."""
    if not os.path.lexists(path):
        return None
    archive_identity = (
        raw_sha256
        if _path_matches_identity(path, owned_identity)
        else f"untrusted-link-result-{secrets.token_hex(8)}"
    )
    return _rollback_published_seal(path, archive_identity)


def _write_exclusive(path: Path, raw: bytes) -> None:
    if os.path.lexists(path):
        raise IncidentSealError("refusing to overwrite an existing seal")
    raw_sha256 = _sha256(raw)
    staging, descriptor = _open_unique_staging(path)
    try:
        opened_identity = os.fstat(descriptor)
    except OSError as exc:
        os.close(descriptor)
        _remove_or_archive_owned(staging, raw_sha256)
        raise IncidentSealError("unable to identify seal staging file") from exc
    owned_identity = (opened_identity.st_dev, opened_identity.st_ino)
    link_attempted = False
    link_returned = False
    try:
        try:
            with os.fdopen(descriptor, "wb", closefd=False) as handle:
                remaining = memoryview(raw)
                while remaining:
                    written = handle.write(remaining)
                    if (
                        not isinstance(written, int)
                        or isinstance(written, bool)
                        or written <= 0
                        or written > len(remaining)
                    ):
                        raise OSError("seal staging write made no valid progress")
                    remaining = remaining[written:]
                handle.flush()
                os.fsync(handle.fileno())
        except OSError as exc:
            if _path_matches_identity(staging, owned_identity):
                _remove_or_archive_owned(staging, raw_sha256)
            raise IncidentSealError("unable to durably write seal") from exc

        if not _path_matches_identity(staging, owned_identity) or (
            _descriptor_sha256(descriptor) != raw_sha256
        ):
            raise IncidentSealError("seal staging ownership changed")

        try:
            link_attempted = True
            os.link(staging, path, follow_symlinks=False)
            link_returned = True
        except FileExistsError as exc:
            _rollback_link_side_effect_if_owned(path, owned_identity, raw_sha256)
            if _path_matches_identity(staging, owned_identity):
                _remove_or_archive_owned(staging, raw_sha256)
            raise IncidentSealError("refusing to overwrite an existing seal") from exc
        except OSError as exc:
            _rollback_link_side_effect_if_owned(path, owned_identity, raw_sha256)
            if _path_matches_identity(staging, owned_identity):
                _remove_or_archive_owned(staging, raw_sha256)
            raise IncidentSealError("unable to publish seal exclusively") from exc

        if not _published_seal_matches(path, owned_identity, descriptor, raw_sha256):
            _rollback_successful_link_result(path, owned_identity, raw_sha256)
            raise IncidentSealError("published seal ownership changed")
        if not _path_matches_identity(staging, owned_identity):
            _rollback_successful_link_result(path, owned_identity, raw_sha256)
            raise IncidentSealError("seal staging ownership changed")

        try:
            staging_archive = _remove_or_archive_owned(staging, raw_sha256)
        except IncidentSealError as exc:
            _rollback_published_seal(path, raw_sha256)
            raise IncidentSealError("unable to retire seal staging path") from exc
        if staging_archive is not None:
            final_archive = _rollback_published_seal(path, raw_sha256)
            raise IncidentSealError(
                "unable to retire seal staging path; "
                f"staging archived at {staging_archive}; "
                f"publication archived at {final_archive}"
            )

        if not _published_seal_matches(path, owned_identity, descriptor, raw_sha256):
            _rollback_successful_link_result(path, owned_identity, raw_sha256)
            raise IncidentSealError("published seal ownership changed")

        try:
            _fsync_parent(path)
        except OSError as exc:
            archive = _rollback_published_seal(path, raw_sha256)
            archive_note = f"; residual archived at {archive}" if archive else ""
            raise IncidentSealError(
                "unable to fsync seal parent directory; publication rolled back"
                f"{archive_note}"
            ) from exc
        if not _published_seal_matches(path, owned_identity, descriptor, raw_sha256):
            _rollback_successful_link_result(path, owned_identity, raw_sha256)
            raise IncidentSealError("published seal ownership changed")
    except BaseException as error:
        cleanup_errors: list[Exception] = []
        if link_attempted:
            try:
                if _path_matches_identity(path, owned_identity):
                    _rollback_published_seal(path, raw_sha256)
                elif link_returned and os.path.lexists(path):
                    _rollback_successful_link_result(path, owned_identity, raw_sha256)
            except (IncidentSealError, OSError) as cleanup_error:
                cleanup_errors.append(cleanup_error)
        try:
            staging_owned = _path_matches_identity(staging, owned_identity)
        except (IncidentSealError, OSError) as cleanup_error:
            cleanup_errors.append(cleanup_error)
            staging_owned = False
        if staging_owned:
            try:
                _remove_or_archive_owned(staging, raw_sha256)
            except (IncidentSealError, OSError) as cleanup_error:
                cleanup_errors.append(cleanup_error)
        for cleanup_error in cleanup_errors:
            error.add_note(f"seal cleanup also failed: {cleanup_error}")
        raise
    finally:
        try:
            os.close(descriptor)
        except OSError:
            pass


def create_data_integrity_incident_seal(
    *, repository: Path, seal_path: Path, policy: IncidentSealPolicy
) -> dict[str, Any]:
    """Create one immutable seal candidate from the registered artifact commit."""
    body = _build_seal_body(repository, policy)
    payload = {
        **body,
        "seal_body_sha256": _sha256(_canonical_json(body)),
    }
    _write_exclusive(seal_path, _seal_bytes(payload))
    return payload


def validate_data_integrity_incident_seal(
    *,
    repository: Path,
    seal_path: Path,
    expected_seal_sha256: str,
    policy: IncidentSealPolicy,
) -> dict[str, Any]:
    """Validate a seal using an independently supplied whole-file SHA-256."""
    _require_sha(expected_seal_sha256, _SHA256_RE, "expected seal SHA-256")
    try:
        raw = seal_path.read_bytes()
    except OSError as exc:
        raise IncidentSealError("unable to read seal") from exc
    if not hmac.compare_digest(_sha256(raw), expected_seal_sha256):
        raise IncidentSealError("seal file external SHA-256 mismatch")
    payload = _load_json(raw, "seal.json")
    if raw != _seal_bytes(payload):
        raise IncidentSealError("seal.json is not canonical finite JSON")
    expected_keys = {
        "schema_version",
        "incident_id",
        "artifact_commit",
        "artifact_parent",
        "artifact_commit_created_at",
        "status",
        "registered_old_identity",
        "artifacts",
        "corrected_epoch",
        "reconciliation_manifest",
        "source_collection",
        "reconciliation_summary",
        "code_identities",
        "seal_body_sha256",
    }
    if set(payload) != expected_keys:
        raise IncidentSealError("seal exact field set mismatch")
    body = {key: value for key, value in payload.items() if key != "seal_body_sha256"}
    recorded_body_sha256 = payload["seal_body_sha256"]
    if (
        not isinstance(recorded_body_sha256, str)
        or not _SHA256_RE.fullmatch(recorded_body_sha256)
        or not hmac.compare_digest(_sha256(_canonical_json(body)), recorded_body_sha256)
    ):
        raise IncidentSealError("seal body SHA-256 mismatch")
    expected_body = _build_seal_body(repository, policy)
    if body != expected_body:
        raise IncidentSealError("seal differs from immutable Git artifacts")
    return payload


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True, type=Path)
    parser.add_argument("--seal-path", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        payload = create_data_integrity_incident_seal(
            repository=args.repository,
            seal_path=args.seal_path,
            policy=REGISTERED_SEAL_POLICY,
        )
    except IncidentSealError as exc:
        print(f"incident seal failed: {exc}", file=sys.stderr)
        return 2
    raw = args.seal_path.read_bytes()
    print(
        json.dumps(
            {
                "artifact_commit": payload["artifact_commit"],
                "incident_id": payload["incident_id"],
                "seal_file_sha256": _sha256(raw),
                "status": payload["status"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
