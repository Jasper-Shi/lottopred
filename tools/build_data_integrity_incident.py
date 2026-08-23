#!/usr/bin/env python3
"""Build and verify the frozen 2026-08-20 historical-data incident artifact.

The builder is intentionally offline. It authenticates the registered history
from Git, reads every expected Loto-Québec capture before constructing a
reconciliation authority, derives every correction from the old/official diff,
and refuses to overwrite an existing incident or corrected-data epoch.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import csv
from dataclasses import dataclass
from datetime import date
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

from lotto649.data_integrity import (
    EvidenceReference,
    HistoricalReconciliation,
    ReconciliationAuthority,
    ReconciliationIntegrityError,
    reconcile_historical_draws,
    validate_reconciliation_manifest,
)
from lotto649.domain import Draw
from lotto649.official_history import (
    canonical_official_rows_sha256,
    canonical_official_text_rows_sha256,
    expected_lotto649_draw_dates,
    parse_lotoquebec_annual_html,
    parse_lotoquebec_detail_html,
    validate_complete_official_history,
)


ANNUAL_URL = (
    "https://assets.lotoquebec.com/jeux/experience/resultats/banniere/"
    "V1/tirages/anterieurs/212/{year}/en"
)
DETAIL_URL = (
    "https://loteries.lotoquebec.com/en/lotteries/lotto-6-49-resultats"
    "?widget=resultats&action=detailles&noproduit=212&date={draw_date}"
)
EXTERNAL_EVIDENCE_ARTIFACT_STATUS = "metadata_verified_during_review_not_embedded"


class IncidentBuildError(RuntimeError):
    """Raised when the incident cannot be built or verified fail-closed."""


@dataclass(frozen=True, order=True)
class ChangeExpectation:
    draw_date: date
    change_type: str

    def __post_init__(self) -> None:
        if self.change_type not in {"insert", "delete", "update"}:
            raise ValueError(f"Unsupported expected change type: {self.change_type}")


@dataclass(frozen=True)
class ExpectedSummary:
    old_count: int
    official_count: int
    decision_count: int
    unchanged: int
    inserted: int
    deleted: int
    updated: int
    unresolved: int
    corrected_count: int

    def to_dict(self) -> dict[str, int]:
        return {
            "old_count": self.old_count,
            "official_count": self.official_count,
            "decision_count": self.decision_count,
            "unchanged": self.unchanged,
            "inserted": self.inserted,
            "deleted": self.deleted,
            "updated": self.updated,
            "unresolved": self.unresolved,
            "corrected_count": self.corrected_count,
        }


@dataclass(frozen=True)
class IncidentPolicy:
    incident_id: str
    created_at: str
    old_commit: str
    old_path: str
    old_blob: str
    old_bytes_sha256: str
    old_count: int
    old_rows_sha256: str
    annual_years: tuple[int, ...]
    detail_dates: tuple[date, ...]
    expected_dates: tuple[date, ...]
    expected_source_assets_sha256: str
    expected_official_text_rows_sha256: str
    expected_official_rows_sha256: str
    expected_changes: tuple[ChangeExpectation, ...]
    expected_summary: ExpectedSummary
    require_full_schedule: bool
    official_fetch_batch_completed_at: str
    external_evidence: tuple[Mapping[str, Any], ...]


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _artifact_json(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _sha256(raw: bytes) -> str:
    return sha256(raw).hexdigest()


def _draw_dict(draw: Draw | None) -> dict[str, Any] | None:
    if draw is None:
        return None
    return {
        "draw_date": draw.draw_date.isoformat(),
        "numbers": list(draw.numbers),
        "bonus": draw.bonus,
    }


def _row_sha256(draw: Draw | None) -> str | None:
    return _sha256(_canonical_json(_draw_dict(draw))) if draw is not None else None


def _rows_sha256(draws: Sequence[Draw]) -> str:
    return _sha256(
        _canonical_json(
            [_draw_dict(draw) for draw in sorted(draws, key=lambda row: row.draw_date)]
        )
    )


def _csv_bytes(draws: Sequence[Draw]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(["draw_date", "n1", "n2", "n3", "n4", "n5", "n6", "bonus"])
    for draw in sorted(draws, key=lambda row: row.draw_date):
        writer.writerow([draw.draw_date.isoformat(), *draw.numbers, draw.bonus])
    return output.getvalue().encode("utf-8")


def _parse_draw_csv(raw: bytes, label: str) -> tuple[Draw, ...]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise IncidentBuildError(f"{label} is not UTF-8") from exc
    rows = csv.reader(io.StringIO(text, newline=""))
    try:
        header = next(rows)
    except StopIteration as exc:
        raise IncidentBuildError(f"{label} is empty") from exc
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
    if header != expected_header:
        raise IncidentBuildError(f"{label} has an unexpected CSV header")
    draws: list[Draw] = []
    seen: set[date] = set()
    for line_number, row in enumerate(rows, start=2):
        if len(row) != 8:
            raise IncidentBuildError(f"{label} row {line_number} has 8-field violation")
        try:
            draw = Draw(
                date.fromisoformat(row[0]),
                tuple(int(value) for value in row[1:7]),  # type: ignore[arg-type]
                int(row[7]),
            )
        except (TypeError, ValueError) as exc:
            raise IncidentBuildError(
                f"{label} row {line_number} violates the Draw contract"
            ) from exc
        if draw.draw_date in seen:
            raise IncidentBuildError(f"{label} contains duplicate draw dates")
        draws.append(draw)
        seen.add(draw.draw_date)
    if draws != sorted(draws, key=lambda row: row.draw_date):
        raise IncidentBuildError(f"{label} is not in chronological order")
    return tuple(draws)


def _git(repository: Path, *arguments: str) -> bytes:
    try:
        result = subprocess.run(
            ["git", "-C", str(repository), *arguments],
            check=False,
            capture_output=True,
        )
    except OSError as exc:
        raise IncidentBuildError("unable to execute Git") from exc
    if result.returncode != 0:
        detail = result.stderr.decode(errors="replace").strip()
        raise IncidentBuildError(f"Git identity check failed: {detail}")
    return result.stdout


def _load_old_draws(
    repository: Path, policy: IncidentPolicy
) -> tuple[tuple[Draw, ...], dict[str, Any]]:
    try:
        repository = repository.resolve(strict=True)
    except OSError as exc:
        raise IncidentBuildError("repository does not exist") from exc
    top = Path(
        _git(repository, "rev-parse", "--show-toplevel").decode().strip()
    ).resolve(strict=True)
    if top != repository:
        raise IncidentBuildError("repository must be the Git worktree top level")
    if (
        len(policy.old_commit) != 40
        or _git(repository, "rev-parse", f"{policy.old_commit}^{{commit}}")
        .decode()
        .strip()
        != policy.old_commit
    ):
        raise IncidentBuildError("registered old commit does not resolve exactly")
    tree_entry = (
        _git(repository, "ls-tree", policy.old_commit, "--", policy.old_path)
        .decode()
        .strip()
    )
    try:
        metadata, listed_path = tree_entry.split("\t", 1)
        mode, object_type, blob = metadata.split(" ", 2)
    except ValueError as exc:
        raise IncidentBuildError("registered old Git tree entry is malformed") from exc
    if (
        listed_path != policy.old_path
        or mode not in {"100644", "100755"}
        or object_type != "blob"
        or blob != policy.old_blob
    ):
        raise IncidentBuildError("registered old Git blob identity mismatch")
    raw = _git(repository, "show", f"{policy.old_commit}:{policy.old_path}")
    if _sha256(raw) != policy.old_bytes_sha256:
        raise IncidentBuildError("registered old CSV byte SHA-256 mismatch")
    draws = _parse_draw_csv(raw, "registered old CSV")
    if len(draws) != policy.old_count:
        raise IncidentBuildError("registered old CSV draw count mismatch")
    if _rows_sha256(draws) != policy.old_rows_sha256:
        raise IncidentBuildError("registered old CSV row SHA-256 mismatch")
    return draws, {
        "commit": policy.old_commit,
        "path": policy.old_path,
        "git_blob": policy.old_blob,
        "bytes": len(raw),
        "byte_sha256": _sha256(raw),
        "draw_count": len(draws),
        "rows_sha256": _rows_sha256(draws),
    }


def _source_asset_digest(records: Sequence[Mapping[str, Any]]) -> str:
    identity_rows = [
        {
            "relative_path": record["relative_path"],
            "url": record["url"],
            "bytes": record["bytes"],
            "raw_sha256": record["raw_sha256"],
        }
        for record in records
    ]
    return _sha256(_canonical_json(identity_rows))


def _read_official_sources(
    annual_dir: Path,
    detail_dir: Path,
    policy: IncidentPolicy,
) -> tuple[tuple[Draw, ...], tuple[dict[str, Any], ...], dict[str, bytes]]:
    expected_annual = {f"{year}.html" for year in policy.annual_years}
    expected_detail = {
        f"{draw_date.isoformat()}.html" for draw_date in policy.detail_dates
    }
    try:
        actual_annual = {path.name for path in annual_dir.iterdir() if path.is_file()}
        actual_detail = {path.name for path in detail_dir.iterdir() if path.is_file()}
    except OSError as exc:
        raise IncidentBuildError("official raw source directory is missing") from exc
    if actual_annual != expected_annual:
        raise IncidentBuildError("annual raw source file set mismatch")
    if actual_detail != expected_detail:
        raise IncidentBuildError("detail raw source file set mismatch")

    raw_by_relative_path: dict[str, bytes] = {}
    records: list[dict[str, Any]] = []
    for year in policy.annual_years:
        path = annual_dir / f"{year}.html"
        try:
            raw = path.read_bytes()
        except OSError as exc:
            raise IncidentBuildError(
                f"unable to read annual raw source: {year}"
            ) from exc
        relative = f"annual/{year}.html"
        raw_by_relative_path[relative] = raw
        records.append(
            {
                "relative_path": relative,
                "source_type": "loto_quebec_annual_history_html",
                "scope": str(year),
                "url": ANNUAL_URL.format(year=year),
                "bytes": len(raw),
                "raw_sha256": _sha256(raw),
                "fetch_batch_completed_at": policy.official_fetch_batch_completed_at,
            }
        )
    for draw_date in policy.detail_dates:
        path = detail_dir / f"{draw_date.isoformat()}.html"
        try:
            raw = path.read_bytes()
        except OSError as exc:
            raise IncidentBuildError(
                f"unable to read detail raw source: {draw_date}"
            ) from exc
        relative = f"detail/{draw_date.isoformat()}.html"
        raw_by_relative_path[relative] = raw
        records.append(
            {
                "relative_path": relative,
                "source_type": "loto_quebec_draw_detail_html",
                "scope": draw_date.isoformat(),
                "url": DETAIL_URL.format(draw_date=draw_date.isoformat()),
                "bytes": len(raw),
                "raw_sha256": _sha256(raw),
                "fetch_batch_completed_at": policy.official_fetch_batch_completed_at,
            }
        )
    records_tuple = tuple(sorted(records, key=lambda row: row["relative_path"]))
    if _source_asset_digest(records_tuple) != policy.expected_source_assets_sha256:
        raise IncidentBuildError("official raw source collection SHA-256 mismatch")

    draws: list[Draw] = []
    for year in policy.annual_years:
        raw = raw_by_relative_path[f"annual/{year}.html"]
        try:
            draws.extend(parse_lotoquebec_annual_html(raw.decode("utf-8"), year))
        except (UnicodeDecodeError, RuntimeError) as exc:
            raise IncidentBuildError(
                f"unable to parse official annual history for {year}"
            ) from exc
    for draw_date in policy.detail_dates:
        raw = raw_by_relative_path[f"detail/{draw_date.isoformat()}.html"]
        try:
            draws.append(parse_lotoquebec_detail_html(raw.decode("utf-8"), draw_date))
        except (UnicodeDecodeError, RuntimeError) as exc:
            raise IncidentBuildError(
                f"unable to parse official detail history for {draw_date}"
            ) from exc
    official_draws = tuple(sorted(draws, key=lambda row: row.draw_date))
    through = policy.expected_dates[-1] if policy.expected_dates else None
    if through is None:
        raise IncidentBuildError("official expected date boundary cannot be empty")
    actual_dates = tuple(draw.draw_date for draw in official_draws)
    if actual_dates != policy.expected_dates:
        raise IncidentBuildError("official history coverage mismatch")
    if policy.require_full_schedule:
        try:
            validate_complete_official_history(official_draws, through)
        except RuntimeError as exc:
            raise IncidentBuildError("official history schedule mismatch") from exc
        if tuple(expected_lotto649_draw_dates(through)) != policy.expected_dates:
            raise IncidentBuildError("incident policy expected date schedule mismatch")
    if (
        canonical_official_text_rows_sha256(official_draws)
        != policy.expected_official_text_rows_sha256
    ):
        raise IncidentBuildError("official text-row SHA-256 mismatch")
    if (
        canonical_official_rows_sha256(official_draws)
        != policy.expected_official_rows_sha256
    ):
        raise IncidentBuildError("official JSON-row SHA-256 mismatch")
    return official_draws, records_tuple, raw_by_relative_path


@dataclass(frozen=True)
class _DerivedChange:
    draw_date: date
    change_type: str
    old_row: Draw | None
    official_row: Draw | None


def _derive_changes(
    old_draws: Sequence[Draw], official_draws: Sequence[Draw]
) -> tuple[tuple[_DerivedChange, ...], ExpectedSummary]:
    old_by_date = {draw.draw_date: draw for draw in old_draws}
    official_by_date = {draw.draw_date: draw for draw in official_draws}
    changes: list[_DerivedChange] = []
    unchanged = 0
    for draw_date in sorted(old_by_date.keys() | official_by_date.keys()):
        old = old_by_date.get(draw_date)
        official = official_by_date.get(draw_date)
        if old == official:
            unchanged += 1
            continue
        if old is None:
            change_type = "insert"
        elif official is None:
            change_type = "delete"
        else:
            change_type = "update"
        changes.append(_DerivedChange(draw_date, change_type, old, official))
    inserted = sum(change.change_type == "insert" for change in changes)
    deleted = sum(change.change_type == "delete" for change in changes)
    updated = sum(change.change_type == "update" for change in changes)
    summary = ExpectedSummary(
        old_count=len(old_draws),
        official_count=len(official_draws),
        decision_count=len(old_by_date.keys() | official_by_date.keys()),
        unchanged=unchanged,
        inserted=inserted,
        deleted=deleted,
        updated=updated,
        unresolved=0,
        corrected_count=len(old_draws) + inserted - deleted,
    )
    return tuple(changes), summary


def _review_document(
    policy: IncidentPolicy,
    changes: Sequence[_DerivedChange],
    source_by_scope: Mapping[str, Mapping[str, Any]],
    summary: ExpectedSummary,
) -> dict[str, Any]:
    external_by_date: dict[str, list[str]] = {}
    external_assets = []
    for raw_asset in policy.external_evidence:
        asset = dict(raw_asset)
        asset_id = asset.get("evidence_id")
        draw_dates = asset.get("draw_dates")
        if not isinstance(asset_id, str) or not isinstance(draw_dates, list):
            raise IncidentBuildError("external adjudication evidence is malformed")
        if asset.get("artifact_status") not in {
            None,
            EXTERNAL_EVIDENCE_ARTIFACT_STATUS,
        }:
            raise IncidentBuildError(
                "external adjudication evidence artifact status is inconsistent"
            )
        asset["artifact_status"] = EXTERNAL_EVIDENCE_ARTIFACT_STATUS
        external_assets.append(asset)
        for draw_date in draw_dates:
            if not isinstance(draw_date, str):
                raise IncidentBuildError("external evidence draw date is malformed")
            external_by_date.setdefault(draw_date, []).append(asset_id)

    change_rows = []
    for change in changes:
        old_sha256 = _row_sha256(change.old_row)
        official_sha256 = _row_sha256(change.official_row)
        source = source_by_scope[str(change.draw_date.year)]
        if change.change_type == "delete":
            determination = (
                "Reject the registered row because the complete official annual "
                "table contains no draw on this non-scheduled date."
            )
            supported = []
            rejected = [old_sha256]
        elif change.change_type == "insert":
            determination = (
                "Insert the row exactly as published in the complete official "
                "annual table."
            )
            supported = [official_sha256]
            rejected = []
        else:
            determination = (
                "Replace the registered row with the exact official annual-table "
                "row; corroborating evidence is recorded where available."
            )
            supported = [official_sha256]
            rejected = [old_sha256]
        change_rows.append(
            {
                "draw_date": change.draw_date.isoformat(),
                "change_type": change.change_type,
                "old_row": _draw_dict(change.old_row),
                "old_row_sha256": old_sha256,
                "official_row": _draw_dict(change.official_row),
                "official_row_sha256": official_sha256,
                "supported_row_sha256s": supported,
                "rejected_row_sha256s": rejected,
                "official_annual_source": {
                    "url": source["url"],
                    "raw_sha256": source["raw_sha256"],
                    "relative_path": source["relative_path"],
                },
                "corroborating_evidence_ids": sorted(
                    external_by_date.get(change.draw_date.isoformat(), [])
                ),
                "determination": determination,
            }
        )
    known_change_dates = {change.draw_date.isoformat() for change in changes}
    unknown_external_dates = sorted(set(external_by_date) - known_change_dates)
    if unknown_external_dates:
        raise IncidentBuildError(
            "external evidence refers to a non-change date: "
            + ",".join(unknown_external_dates)
        )
    return {
        "schema_version": "lotto649-reviewed-adjudication-v1",
        "incident_id": policy.incident_id,
        "reviewed_at": policy.created_at,
        "review_scope": (
            "All differences between the registered Git history and the complete "
            "offline Loto-Québec history through the incident boundary."
        ),
        "disposition": "accept_official_history_for_all_enumerated_changes",
        "method": (
            "Changes are derived from the full old-versus-official date-keyed diff; "
            "no correction row is hard-coded into the builder."
        ),
        "root_cause_findings": [
            "The registered source omitted official scheduled draws.",
            "Two registered 2023 dates duplicated official 2022 rows under the wrong year.",
            "Nine registered rows disagreed with the official numbers or bonus.",
        ],
        "summary": summary.to_dict(),
        "changes": change_rows,
        "external_evidence_handling": {
            "artifact_count": len(external_assets),
            "artifact_status": EXTERNAL_EVIDENCE_ARTIFACT_STATUS,
            "automatic_two_source_resolution_use": "none",
            "closure_basis": "externally_allowlisted_reviewed_adjudication",
        },
        "external_evidence": sorted(
            external_assets, key=lambda asset: str(asset["evidence_id"])
        ),
    }


def _source_reference(
    change: _DerivedChange, source: Mapping[str, Any]
) -> EvidenceReference:
    old_sha256 = _row_sha256(change.old_row)
    official_sha256 = _row_sha256(change.official_row)
    if change.change_type == "delete":
        supports: tuple[str, ...] = ()
        rejects = (old_sha256,) if old_sha256 else ()
        summary = (
            f"Complete Loto-Québec {change.draw_date.year} annual table rejects "
            f"the non-scheduled registered row on {change.draw_date}."
        )
    else:
        supports = (official_sha256,) if official_sha256 else ()
        rejects = ()
        summary = (
            f"Loto-Québec {change.draw_date.year} annual table publishes the "
            f"official row for {change.draw_date}."
        )
    return EvidenceReference(
        provider="Loto-Québec",
        source_type="official_annual_history",
        url=str(source["url"]),
        video_id=None,
        download_sha256=str(source["raw_sha256"]),
        frame_sha256=None,
        frame_summary=summary,
        supported_row_sha256s=supports,
        rejected_row_sha256s=rejects,
    )


def _review_reference(
    policy: IncidentPolicy,
    changes: Sequence[_DerivedChange],
    review_bytes: bytes,
) -> EvidenceReference:
    supported = tuple(
        sorted(
            value
            for change in changes
            if (value := _row_sha256(change.official_row)) is not None
        )
    )
    rejected = tuple(
        sorted(
            value
            for change in changes
            if change.change_type in {"delete", "update"}
            and (value := _row_sha256(change.old_row)) is not None
        )
    )
    return EvidenceReference(
        provider="Historical data-integrity incident review",
        source_type="reviewed_adjudication",
        url=(
            "repository:evidence/data_integrity/"
            f"{policy.incident_id}/reviewed-adjudication.json"
        ),
        video_id=None,
        download_sha256=_sha256(review_bytes),
        frame_sha256=None,
        frame_summary=(
            f"Reviewed adjudication binds and disposes all {len(changes)} "
            "old-versus-official change dates."
        ),
        supported_row_sha256s=supported,
        rejected_row_sha256s=rejected,
    )


def _authority_dict(authority: ReconciliationAuthority) -> dict[str, Any]:
    return {**authority.body_dict(), "authority_sha256": authority.authority_sha256}


def _authority_from_dict(value: Mapping[str, Any]) -> ReconciliationAuthority:
    try:
        authority = ReconciliationAuthority(
            expected_dates=tuple(
                date.fromisoformat(item) for item in value["expected_dates"]
            ),
            expected_old_rows_sha256=value["expected_old_rows_sha256"],
            expected_official_rows_sha256=value["expected_official_rows_sha256"],
            evidence_sha256_allowlist=tuple(value["evidence_sha256_allowlist"]),
            reviewed_adjudication_sha256_allowlist=tuple(
                value["reviewed_adjudication_sha256_allowlist"]
            ),
            evidence_independence_groups=tuple(
                tuple(item) for item in value["evidence_independence_groups"]
            ),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise IncidentBuildError(
            "incident reconciliation authority is malformed"
        ) from exc
    if value.get("authority_sha256") != authority.authority_sha256:
        raise IncidentBuildError("incident reconciliation authority SHA-256 mismatch")
    return authority


def _artifact_paths(output_root: Path, incident_id: str) -> tuple[Path, Path]:
    incident_dir = output_root / "evidence" / "data_integrity" / incident_id
    epoch_dir = output_root / "data" / "processed" / "epochs" / incident_id
    return incident_dir, epoch_dir


def _write_exclusive(path: Path, raw: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    try:
        descriptor = os.open(path, flags, 0o644)
    except FileExistsError as exc:
        raise IncidentBuildError(
            f"refusing to overwrite existing artifact: {path}"
        ) from exc
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        try:
            path.unlink()
        except OSError:
            pass
        raise


def _assert_policy_diff(
    policy: IncidentPolicy,
    changes: Sequence[_DerivedChange],
    summary: ExpectedSummary,
) -> None:
    actual_changes = tuple(
        ChangeExpectation(change.draw_date, change.change_type) for change in changes
    )
    if actual_changes != policy.expected_changes:
        raise IncidentBuildError("old-versus-official change set mismatch")
    if summary != policy.expected_summary:
        raise IncidentBuildError("old-versus-official summary mismatch")


@dataclass(frozen=True)
class _IncidentDerivation:
    changes: tuple[_DerivedChange, ...]
    summary: ExpectedSummary
    review_bytes: bytes
    authority: ReconciliationAuthority
    reconciliation: HistoricalReconciliation


def _derive_incident_reconciliation(
    policy: IncidentPolicy,
    old_draws: Sequence[Draw],
    official_draws: Sequence[Draw],
    source_records: Sequence[Mapping[str, Any]],
) -> _IncidentDerivation:
    changes, summary = _derive_changes(old_draws, official_draws)
    _assert_policy_diff(policy, changes, summary)
    source_by_scope = {str(record["scope"]): record for record in source_records}
    review = _review_document(policy, changes, source_by_scope, summary)
    review_bytes = _artifact_json(review)
    annual_refs = {
        change.draw_date: _source_reference(
            change, source_by_scope[str(change.draw_date.year)]
        )
        for change in changes
    }
    review_ref = _review_reference(policy, changes, review_bytes)
    evidence_by_date = {
        change.draw_date: (annual_refs[change.draw_date], review_ref)
        for change in changes
    }
    all_refs = tuple(annual_refs.values()) + (review_ref,)
    authority = ReconciliationAuthority(
        expected_dates=policy.expected_dates,
        expected_old_rows_sha256=policy.old_rows_sha256,
        expected_official_rows_sha256=policy.expected_official_rows_sha256,
        evidence_sha256_allowlist=tuple(
            sorted(reference.evidence_sha256 for reference in all_refs)
        ),
        reviewed_adjudication_sha256_allowlist=(review_ref.evidence_sha256,),
        evidence_independence_groups=(),
    )
    reconciliation = reconcile_historical_draws(
        old_draws, official_draws, evidence_by_date, authority
    )
    if reconciliation.summary.to_manifest_dict() != summary.to_dict():
        raise IncidentBuildError("reconciliation summary differs from independent diff")
    if not reconciliation.closure_allowed:
        raise IncidentBuildError("reconciliation did not close")
    return _IncidentDerivation(
        changes=changes,
        summary=summary,
        review_bytes=review_bytes,
        authority=authority,
        reconciliation=reconciliation,
    )


def build_data_integrity_incident(
    *,
    annual_dir: Path,
    detail_dir: Path,
    repository: Path,
    output_root: Path,
    policy: IncidentPolicy,
) -> HistoricalReconciliation:
    """Build a new incident artifact and return its externally validated result."""
    incident_dir, epoch_dir = _artifact_paths(output_root, policy.incident_id)
    if incident_dir.exists() or epoch_dir.exists():
        raise IncidentBuildError("refusing to overwrite an existing incident epoch")

    old_draws, old_identity = _load_old_draws(repository, policy)
    official_draws, source_records, _ = _read_official_sources(
        annual_dir, detail_dir, policy
    )
    derivation = _derive_incident_reconciliation(
        policy, old_draws, official_draws, source_records
    )
    review_bytes = derivation.review_bytes
    authority = derivation.authority
    reconciliation = derivation.reconciliation
    manifest_bytes = _artifact_json(reconciliation.manifest.to_dict())
    external_manifest_pin = reconciliation.manifest_sha256
    try:
        validated = validate_reconciliation_manifest(
            json.loads(manifest_bytes),
            old_draws,
            official_draws,
            authority,
            external_manifest_pin,
        )
        corrected_draws = validated.corrected_draws
    except (ReconciliationIntegrityError, ValueError) as exc:
        raise IncidentBuildError(
            "externally pinned manifest validation failed"
        ) from exc
    if corrected_draws != official_draws:
        raise IncidentBuildError(
            "closed corrected projection differs from official history"
        )

    official_csv = _csv_bytes(official_draws)
    corrected_csv = _csv_bytes(corrected_draws)
    source_index = {
        "schema_version": "lotto649-official-source-index-v1",
        "incident_id": policy.incident_id,
        "collection_asset_count": len(source_records),
        "source_assets_sha256": _source_asset_digest(source_records),
        "official_draw_count": len(official_draws),
        "official_collection_line_sha256": canonical_official_text_rows_sha256(
            official_draws
        ),
        "official_json_rows_sha256": canonical_official_rows_sha256(official_draws),
        "assets": list(source_records),
    }
    source_index_bytes = _artifact_json(source_index)

    relative_incident = Path("evidence") / "data_integrity" / policy.incident_id
    relative_epoch = Path("data") / "processed" / "epochs" / policy.incident_id
    payloads = {
        (relative_incident / "source-index.json").as_posix(): source_index_bytes,
        (relative_incident / "reviewed-adjudication.json").as_posix(): review_bytes,
        (relative_incident / "reconciliation.manifest.json").as_posix(): manifest_bytes,
        (relative_incident / "official_draws.csv").as_posix(): official_csv,
        (relative_epoch / "corrected_draws.csv").as_posix(): corrected_csv,
    }
    inventory = {
        path: {"bytes": len(raw), "sha256": _sha256(raw)}
        for path, raw in sorted(payloads.items())
    }
    incident = {
        "schema_version": "lotto649-data-integrity-incident-v1",
        "incident_id": policy.incident_id,
        "created_at": policy.created_at,
        "status": "reconciliation_closed_artifact_unsealed",
        "seal_status": "awaiting_artifact_commit_seal",
        "external_evidence_artifact_status": EXTERNAL_EVIDENCE_ARTIFACT_STATUS,
        "scientific_disposition": (
            "The registered history is invalid as strict real-calendar evidence; "
            "downstream model evidence requires reclassification and a corrected-source rerun."
        ),
        "registered_old_source": old_identity,
        "official_source": {
            "asset_count": len(source_records),
            "source_assets_sha256": _source_asset_digest(source_records),
            "draw_count": len(official_draws),
            "collection_line_sha256": canonical_official_text_rows_sha256(
                official_draws
            ),
            "json_rows_sha256": canonical_official_rows_sha256(official_draws),
            "history_start": official_draws[0].draw_date.isoformat(),
            "history_through": official_draws[-1].draw_date.isoformat(),
        },
        "reconciliation_summary": validated.summary.to_manifest_dict(),
        "manifest_sha256_external_pin": external_manifest_pin,
        "reconciliation_authority": _authority_dict(authority),
        "artifact_inventory": inventory,
    }
    incident_bytes = _artifact_json(incident)

    incident_dir.parent.mkdir(parents=True, exist_ok=True)
    epoch_dir.parent.mkdir(parents=True, exist_ok=True)
    try:
        incident_dir.mkdir()
        epoch_dir.mkdir()
    except FileExistsError as exc:
        raise IncidentBuildError(
            "refusing to overwrite an existing incident epoch"
        ) from exc
    for relative_path, raw in payloads.items():
        _write_exclusive(output_root / relative_path, raw)
    _write_exclusive(incident_dir / "incident.json", incident_bytes)
    return validated


def _load_json(path: Path, label: str) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_bytes())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IncidentBuildError(f"{label} is unavailable or invalid") from exc
    if not isinstance(value, Mapping):
        raise IncidentBuildError(f"{label} must be a JSON object")
    return value


def _expected_source_asset_identities(
    policy: IncidentPolicy,
) -> tuple[dict[str, str], ...]:
    identities = [
        {
            "relative_path": f"annual/{year}.html",
            "source_type": "loto_quebec_annual_history_html",
            "scope": str(year),
            "url": ANNUAL_URL.format(year=year),
        }
        for year in policy.annual_years
    ]
    identities.extend(
        {
            "relative_path": f"detail/{draw_date.isoformat()}.html",
            "source_type": "loto_quebec_draw_detail_html",
            "scope": draw_date.isoformat(),
            "url": DETAIL_URL.format(draw_date=draw_date.isoformat()),
        }
        for draw_date in policy.detail_dates
    )
    return tuple(sorted(identities, key=lambda row: row["relative_path"]))


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _validate_source_index(
    value: Mapping[str, Any], policy: IncidentPolicy
) -> tuple[dict[str, Any], ...]:
    expected_root_keys = {
        "schema_version",
        "incident_id",
        "collection_asset_count",
        "source_assets_sha256",
        "official_draw_count",
        "official_collection_line_sha256",
        "official_json_rows_sha256",
        "assets",
    }
    if set(value) != expected_root_keys:
        raise IncidentBuildError("source index schema fields mismatch")
    if value.get("schema_version") != "lotto649-official-source-index-v1":
        raise IncidentBuildError("source index schema version mismatch")
    if value.get("incident_id") != policy.incident_id:
        raise IncidentBuildError("source index incident identity mismatch")
    raw_assets = value.get("assets")
    if not isinstance(raw_assets, list):
        raise IncidentBuildError("source index assets must be a list")
    expected_identities = _expected_source_asset_identities(policy)
    if value.get("collection_asset_count") != len(expected_identities) or len(
        raw_assets
    ) != len(expected_identities):
        raise IncidentBuildError("source index asset count mismatch")
    asset_keys = {
        "relative_path",
        "source_type",
        "scope",
        "url",
        "bytes",
        "raw_sha256",
        "fetch_batch_completed_at",
    }
    assets: list[dict[str, Any]] = []
    for index, (raw_asset, identity) in enumerate(
        zip(raw_assets, expected_identities, strict=True)
    ):
        if not isinstance(raw_asset, Mapping) or set(raw_asset) != asset_keys:
            raise IncidentBuildError(f"source index asset {index} schema mismatch")
        asset = dict(raw_asset)
        for field_name, expected in identity.items():
            if asset.get(field_name) != expected:
                raise IncidentBuildError(
                    f"source index asset {index} {field_name} mismatch"
                )
        if (
            type(asset.get("bytes")) is not int
            or asset["bytes"] <= 0
            or not _is_sha256(asset.get("raw_sha256"))
        ):
            raise IncidentBuildError(
                f"source index asset {index} byte identity mismatch"
            )
        if (
            asset.get("fetch_batch_completed_at")
            != policy.official_fetch_batch_completed_at
        ):
            raise IncidentBuildError(
                f"source index asset {index} fetch-batch registration mismatch"
            )
        assets.append(asset)
    calculated_assets_sha256 = _source_asset_digest(assets)
    if (
        value.get("source_assets_sha256") != calculated_assets_sha256
        or calculated_assets_sha256 != policy.expected_source_assets_sha256
    ):
        raise IncidentBuildError("source index asset aggregate SHA-256 mismatch")
    if (
        value.get("official_draw_count") != policy.expected_summary.official_count
        or value.get("official_collection_line_sha256")
        != policy.expected_official_text_rows_sha256
        or value.get("official_json_rows_sha256")
        != policy.expected_official_rows_sha256
    ):
        raise IncidentBuildError("source index official-row identity mismatch")
    return tuple(assets)


def verify_data_integrity_incident(
    *, repository: Path, output_root: Path, policy: IncidentPolicy
) -> HistoricalReconciliation:
    """Verify artifact bytes and return the externally pinned reconciliation."""
    incident_dir, epoch_dir = _artifact_paths(output_root, policy.incident_id)
    if (incident_dir / "seal.json").exists():
        raise IncidentBuildError(
            "unexpected seal.json in the unsealed incident artifact"
        )
    incident = _load_json(incident_dir / "incident.json", "incident.json")
    if incident.get("incident_id") != policy.incident_id:
        raise IncidentBuildError("incident identity mismatch")
    if incident.get("seal_status") != "awaiting_artifact_commit_seal":
        raise IncidentBuildError("incident seal status mismatch")
    if (
        incident.get("external_evidence_artifact_status")
        != EXTERNAL_EVIDENCE_ARTIFACT_STATUS
    ):
        raise IncidentBuildError("incident external evidence artifact status mismatch")
    old_draws, old_identity = _load_old_draws(repository, policy)
    if incident.get("registered_old_source") != old_identity:
        raise IncidentBuildError("incident old Git identity mismatch")
    inventory = incident.get("artifact_inventory")
    if not isinstance(inventory, Mapping):
        raise IncidentBuildError("incident artifact inventory is malformed")
    expected_paths = {
        (Path("evidence") / "data_integrity" / policy.incident_id / filename).as_posix()
        for filename in (
            "source-index.json",
            "reviewed-adjudication.json",
            "reconciliation.manifest.json",
            "official_draws.csv",
        )
    }
    expected_paths.add(
        (
            Path("data")
            / "processed"
            / "epochs"
            / policy.incident_id
            / "corrected_draws.csv"
        ).as_posix()
    )
    if set(inventory) != expected_paths:
        raise IncidentBuildError("incident artifact inventory path set mismatch")
    for relative_path in sorted(expected_paths):
        raw = (output_root / relative_path).read_bytes()
        expected = inventory[relative_path]
        if not isinstance(expected, Mapping) or expected != {
            "bytes": len(raw),
            "sha256": _sha256(raw),
        }:
            raise IncidentBuildError(f"artifact integrity mismatch: {relative_path}")

    source_index = _load_json(incident_dir / "source-index.json", "source-index.json")
    source_records = _validate_source_index(source_index, policy)
    official_draws = _parse_draw_csv(
        (incident_dir / "official_draws.csv").read_bytes(), "official_draws.csv"
    )
    if (
        canonical_official_rows_sha256(official_draws)
        != policy.expected_official_rows_sha256
    ):
        raise IncidentBuildError("official artifact row SHA-256 mismatch")
    derivation = _derive_incident_reconciliation(
        policy, old_draws, official_draws, source_records
    )
    expected_official_source = {
        "asset_count": len(source_records),
        "source_assets_sha256": _source_asset_digest(source_records),
        "draw_count": len(official_draws),
        "collection_line_sha256": canonical_official_text_rows_sha256(official_draws),
        "json_rows_sha256": canonical_official_rows_sha256(official_draws),
        "history_start": official_draws[0].draw_date.isoformat(),
        "history_through": official_draws[-1].draw_date.isoformat(),
    }
    if (
        incident.get("official_source") != expected_official_source
        or incident.get("reconciliation_summary") != derivation.summary.to_dict()
    ):
        raise IncidentBuildError(
            "incident derived metadata differs from reconstruction"
        )
    actual_review_bytes = (incident_dir / "reviewed-adjudication.json").read_bytes()
    if actual_review_bytes != derivation.review_bytes:
        raise IncidentBuildError(
            "reviewed adjudication differs from the fixed policy reconstruction"
        )
    authority_raw = incident.get("reconciliation_authority")
    if not isinstance(authority_raw, Mapping):
        raise IncidentBuildError("incident reconciliation authority is missing")
    _authority_from_dict(authority_raw)
    if _canonical_json(dict(authority_raw)) != _canonical_json(
        _authority_dict(derivation.authority)
    ):
        raise IncidentBuildError(
            "incident reconciliation authority differs from reconstruction"
        )
    manifest = _load_json(
        incident_dir / "reconciliation.manifest.json",
        "reconciliation.manifest.json",
    )
    manifest_pin = incident.get("manifest_sha256_external_pin")
    if manifest_pin != derivation.reconciliation.manifest_sha256 or _canonical_json(
        manifest
    ) != _canonical_json(derivation.reconciliation.manifest.to_dict()):
        raise IncidentBuildError(
            "incident manifest differs from the fixed policy reconstruction"
        )
    try:
        validated = validate_reconciliation_manifest(
            manifest,
            old_draws,
            official_draws,
            derivation.authority,
            derivation.reconciliation.manifest_sha256,
        )
        corrected = validated.corrected_draws
    except ReconciliationIntegrityError as exc:
        raise IncidentBuildError("incident manifest validation failed") from exc
    corrected_csv = _parse_draw_csv(
        (epoch_dir / "corrected_draws.csv").read_bytes(), "corrected_draws.csv"
    )
    if corrected_csv != corrected:
        raise IncidentBuildError("corrected CSV differs from validated reconciliation")
    if validated.summary.to_manifest_dict() != policy.expected_summary.to_dict():
        raise IncidentBuildError("validated incident summary mismatch")
    return validated


_PRODUCTION_EXTERNAL_EVIDENCE: tuple[Mapping[str, Any], ...] = (
    {
        "evidence_id": "banq-le-quotidien-1989-11-09-p2",
        "provider": "Bibliothèque et Archives nationales du Québec",
        "source_type": "government_archive_contemporaneous_newspaper_scan",
        "draw_dates": ["1989-11-08"],
        "notice_url": "https://numerique.banq.qc.ca/patrimoine/details/52327/4223996",
        "download_url": "https://diffusion2.banq.qc.ca/pdfjs-3.10.111-dist_banq_2025/web/pdf.php/XgNRQD4EE-Sc2NJVnbS2Uw",
        "download_bytes": 47_727_873,
        "download_sha256": "c4fb96f04cfeaf9f14199c20e9a5e244a75846ee50f064cb8ecb297dce93f744",
        "page": 2,
        "frame_sha256": "4c8255017494c9deb4bbf505f0ca7addb49d04cc29849641e74b962c87ea554e",
        "frame_summary": "Le Quotidien reports 09 17 28 36 44 46, complémentaire 2.",
    },
    {
        "evidence_id": "banq-progres-dimanche-1989-11-12-p2",
        "provider": "Bibliothèque et Archives nationales du Québec",
        "source_type": "government_archive_contemporaneous_loto_quebec_result_scan",
        "draw_dates": ["1989-11-08"],
        "notice_url": "https://numerique.banq.qc.ca/patrimoine/details/52327/4295284",
        "download_url": "https://diffusion2.banq.qc.ca/pdfjs-3.10.111-dist_banq_2025/web/pdf.php/4k5_xTCVdymt5PQ1sXMf6A",
        "download_bytes": 112_432_487,
        "download_sha256": "226e9a5e07ef4744a9c398ab2c2ffd0c5859df963da46458a7e23513da54212d",
        "page": 2,
        "frame_sha256": "62e6801c7a956906fd41543c7e379e938652c7da86dd1bf4423351564496b87a",
        "frame_summary": "The Loto-Québec result box reports 09 17 28 36 44 46, complémentaire 2.",
    },
    {
        "evidence_id": "loto-quebec-cnw-2010-09-04",
        "provider": "Loto-Québec via Canada Newswire",
        "source_type": "same_night_official_transmission_bulletin",
        "draw_dates": ["2010-09-04"],
        "url": "https://www.newswire.ca/fr/news-releases/loto-quebec---rapport-de-transmission---diffusion-de-la-structure---lotto649-545343702.html",
        "published_at": "2010-09-04T23:24:00-04:00",
        "download_bytes": 192_007,
        "download_sha256": "6dd89d9e0eae56d2f903f643f1c8b04e8c887181a45acf12bc2c9c425e20e2d2",
        "normalized_result_line_sha256": "5eeddc7037aa314a22a3797f5448992ff621ae8185d02f97f1891d1290842db3",
        "frame_summary": "Official bulletin reports 11-13-17-18-20-45, complémentaire 41.",
    },
    {
        "evidence_id": "loto-quebec-video-2019-06-29",
        "provider": "Loto-Québec official YouTube channel",
        "source_type": "official_draw_video",
        "draw_dates": ["2019-06-29"],
        "video_id": "mUcSxzt941w",
        "url": "https://www.youtube.com/watch?v=mUcSxzt941w",
        "download_bytes": 9_507_361,
        "download_sha256": "8526f7a60fb579241460ace647d80c1c4914920e5f5d7c0ab6a62b468e03159a",
        "frame_sha256": "1cf4491f0a8439f4bc429b9fdaed31e5fbeefbefb6d13f2b707d05db2d3d5b43",
        "frame_summary": "Official result frame reports 02 05 19 21 29 46, bonus 15.",
    },
    {
        "evidence_id": "loto-quebec-video-2020-02-29",
        "provider": "Loto-Québec official YouTube channel",
        "source_type": "official_draw_video",
        "draw_dates": ["2020-02-29"],
        "video_id": "7r_gdJFJ_c8",
        "url": "https://www.youtube.com/watch?v=7r_gdJFJ_c8",
        "download_bytes": 9_727_890,
        "download_sha256": "a4253312fccc507aca3775d42bd44ed06fd8e91eb87d392025d9ca13ada5b175",
        "frame_sha256": "0f016038ec31bb465870825418cad3afd707f0bb3dffbcd25f1ebdf58f2831d2",
        "frame_summary": "Official result frame reports 06 12 15 18 31 46, bonus 13.",
    },
    {
        "evidence_id": "loto-quebec-video-2020-03-21",
        "provider": "Loto-Québec official YouTube channel",
        "source_type": "official_draw_video",
        "draw_dates": ["2020-03-21"],
        "video_id": "8chDrTVE-U8",
        "url": "https://www.youtube.com/watch?v=8chDrTVE-U8",
        "download_bytes": 10_579_905,
        "download_sha256": "1bab7d26974f74f09fda81b7f475bffaa65eede3965199ab96b553ebc5ae17d5",
        "frame_sha256": "357a10c25565b5f22e32fbe0e671603eecff2593334bcd232de1f5dd474e9fc6",
        "frame_summary": "Official result frame reports 06 11 22 36 37 45, bonus 10.",
    },
    {
        "evidence_id": "loto-quebec-video-2020-04-11",
        "provider": "Loto-Québec official YouTube channel",
        "source_type": "official_draw_video",
        "draw_dates": ["2020-04-11"],
        "video_id": "48vD7p_0q9s",
        "url": "https://www.youtube.com/watch?v=48vD7p_0q9s",
        "download_bytes": 10_846_468,
        "download_sha256": "73263f833cc08f98ec048bf4ed2fc5c555c8494c76e30a959ec52cedfb0f5c06",
        "frame_sha256": "3c53318688b7b8a1dba4339eb2ec85df9e4c97ce4691a5337b77f85c131a5035",
        "frame_summary": "Official result frame reports 10 14 17 32 35 42, bonus 26.",
    },
    {
        "evidence_id": "loto-quebec-video-2020-07-01",
        "provider": "Loto-Québec official YouTube channel",
        "source_type": "official_draw_video",
        "draw_dates": ["2020-07-01"],
        "video_id": "xzdpIJV7ugE",
        "url": "https://www.youtube.com/watch?v=xzdpIJV7ugE",
        "download_bytes": 9_702_900,
        "download_sha256": "ebc296e782022731607c48f1265c6a20971b2d04e3a55169e400341807baab0a",
        "frame_sha256": "ef1e0622886662ada04e32c3b8536cb9d40796712a22e2511e783f38e0cad339",
        "frame_summary": "Official result frame reports 01 12 27 30 34 49, bonus 35.",
    },
    {
        "evidence_id": "loto-quebec-video-2020-08-15",
        "provider": "Loto-Québec official YouTube channel",
        "source_type": "official_draw_video",
        "draw_dates": ["2020-08-15"],
        "video_id": "Y5bf0fbP3pk",
        "url": "https://www.youtube.com/watch?v=Y5bf0fbP3pk",
        "download_bytes": 9_774_237,
        "download_sha256": "4984a8c07e402a3c36fc8b34ff3d7e9f134bfcd98a4b81b5f25341f210f29df4",
        "frame_sha256": "6c6a7144765974508022abfdceb7612e4ad3a85f0f2641dfea71fa3b799c8d5a",
        "frame_summary": "Official result frame reports 06 07 11 18 22 43, bonus 09.",
    },
    {
        "evidence_id": "loto-quebec-video-2021-06-16",
        "provider": "Loto-Québec official YouTube channel",
        "source_type": "official_draw_video",
        "draw_dates": ["2021-06-16"],
        "video_id": "CAPziRd8LKk",
        "url": "https://www.youtube.com/watch?v=CAPziRd8LKk",
        "download_bytes": 10_766_781,
        "download_sha256": "92a579b72cc51c143f58860870beff1cb20d64ceb8de99cbc9950501023f97a2",
        "frame_sha256": "89d69ba1399cb8fe774abb00f537abd19ed97c8e1e1906fa9b00fdf86141df5a",
        "frame_summary": "Official result frame reports 16 23 32 33 37 45, bonus 03.",
    },
    {
        "evidence_id": "loto-quebec-video-2021-08-04",
        "provider": "Loto-Québec official YouTube channel",
        "source_type": "official_draw_video",
        "draw_dates": ["2021-08-04"],
        "video_id": "QfW1H4qfzTA",
        "url": "https://www.youtube.com/watch?v=QfW1H4qfzTA",
        "download_bytes": 9_518_852,
        "download_sha256": "6391f5fa41c8ef179ca42148cf50e5a655fec433ce8500d78bec7bcc1175f1b6",
        "frame_sha256": "ae34a02ac762387f19d2fcb1cddcd9a71df10359d16236bc8e81f8d9b6e6a7be",
        "frame_summary": "Official result frame reports 03 08 21 38 42 49, bonus 27.",
    },
)


REGISTERED_POLICY = IncidentPolicy(
    incident_id="DI-2026-08-20-registered-history",
    created_at="2026-08-20T05:35:00Z",
    old_commit="90177c80cfb070038d79508fb2e73305a297f516",
    old_path="data/processed/draws.csv",
    old_blob="5afa689b7b206a27af78d14368588de00b4a4812",
    old_bytes_sha256="edfb7f8a4a7711a630957d6f86b567e6b254caf7b1d1aaea0edf1d16a34155b3",
    old_count=4_432,
    old_rows_sha256="257aef242bb898649b0923ac03f2271c7536ff7f840edf552c0dc6b4b03ce1dd",
    annual_years=tuple(range(1982, 2026)),
    detail_dates=tuple(
        draw_date
        for draw_date in expected_lotto649_draw_dates(date(2026, 8, 15))
        if draw_date.year == 2026
    ),
    expected_dates=tuple(expected_lotto649_draw_dates(date(2026, 8, 15))),
    expected_source_assets_sha256="1be14241443477f7ba347c8fe87605bb4c1367c7b7390f5f05762478a4c36b96",
    expected_official_text_rows_sha256="7e3328896d5bb7950c10cf5b9cca0e4d7cadd7265c6d4a4f6b3dcc8793b0a88a",
    expected_official_rows_sha256="58988bbb130be2142bc5a2b20df571cc458eabe66cd873773f55ca1dbfae8874",
    expected_changes=tuple(
        ChangeExpectation(date.fromisoformat(draw_date), change_type)
        for draw_date, change_type in (
            ("1989-11-08", "update"),
            ("1998-05-02", "insert"),
            ("2010-09-04", "update"),
            ("2012-08-15", "insert"),
            ("2012-08-18", "insert"),
            ("2019-06-29", "insert"),
            ("2020-02-05", "insert"),
            ("2020-02-29", "update"),
            ("2020-03-21", "update"),
            ("2020-04-11", "update"),
            ("2020-07-01", "update"),
            ("2020-08-15", "update"),
            ("2021-06-16", "update"),
            ("2021-08-04", "update"),
            ("2021-08-14", "insert"),
            ("2021-08-25", "insert"),
            ("2021-12-18", "insert"),
            ("2021-12-25", "insert"),
            ("2022-12-28", "insert"),
            ("2022-12-31", "insert"),
            ("2023-12-28", "delete"),
            ("2023-12-30", "insert"),
            ("2023-12-31", "delete"),
        )
    ),
    expected_summary=ExpectedSummary(
        old_count=4_432,
        official_count=4_442,
        decision_count=4_444,
        unchanged=4_421,
        inserted=12,
        deleted=2,
        updated=9,
        unresolved=0,
        corrected_count=4_442,
    ),
    require_full_schedule=True,
    official_fetch_batch_completed_at="2026-08-20T05:35:00Z",
    external_evidence=_PRODUCTION_EXTERNAL_EVIDENCE,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--annual-dir", required=True, type=Path)
    parser.add_argument("--detail-dir", required=True, type=Path)
    parser.add_argument("--repository", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = build_data_integrity_incident(
            annual_dir=args.annual_dir,
            detail_dir=args.detail_dir,
            repository=args.repository,
            output_root=args.output_root,
            policy=REGISTERED_POLICY,
        )
    except IncidentBuildError as exc:
        print(f"incident build failed: {exc}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "incident_id": REGISTERED_POLICY.incident_id,
                "manifest_sha256": result.manifest_sha256,
                "summary": result.summary.to_manifest_dict(),
                "seal_status": "awaiting_artifact_commit_seal",
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
