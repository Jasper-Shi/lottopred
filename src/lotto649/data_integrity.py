"""Fail-closed historical reconciliation from externally anchored evidence.

This module does not read or authenticate source files. Before constructing a
``ReconciliationAuthority``, the integration layer must verify the actual asset
bytes, paths, and hashes against a separately sealed registry. Validation must
also receive the expected manifest SHA-256 from an external immutable seal, not
from the manifest being checked. Unit tests use literal external allowlists and
pins to model that trust boundary.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from hashlib import sha256
import json
import re
from typing import Any

from .domain import Draw


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_VALIDATED_RECONCILIATION_CAPABILITY = object()


class ReconciliationIntegrityError(ValueError):
    pass


@dataclass(frozen=True)
class ReconciliationAuthority:
    expected_dates: tuple[date, ...]
    expected_old_rows_sha256: str
    expected_official_rows_sha256: str
    evidence_sha256_allowlist: tuple[str, ...]
    reviewed_adjudication_sha256_allowlist: tuple[str, ...]
    evidence_independence_groups: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.expected_dates, tuple) or any(
            type(value) is not date for value in self.expected_dates
        ):
            raise ReconciliationIntegrityError(
                "Authority expected_dates must be a tuple of dates"
            )
        if self.expected_dates != tuple(sorted(set(self.expected_dates))):
            raise ReconciliationIntegrityError(
                "Authority expected_dates must be sorted and unique"
            )
        for field_name in (
            "expected_old_rows_sha256",
            "expected_official_rows_sha256",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
                raise ReconciliationIntegrityError(
                    f"Authority {field_name} must be a canonical SHA-256"
                )
        for field_name in (
            "evidence_sha256_allowlist",
            "reviewed_adjudication_sha256_allowlist",
        ):
            values = getattr(self, field_name)
            if not isinstance(values, tuple) or values != tuple(sorted(set(values))):
                raise ReconciliationIntegrityError(
                    f"Authority {field_name} must be a sorted unique tuple"
                )
            if any(
                not isinstance(value, str) or not _SHA256_RE.fullmatch(value)
                for value in values
            ):
                raise ReconciliationIntegrityError(
                    f"Authority {field_name} must contain canonical SHA-256 values"
                )
        if not set(self.reviewed_adjudication_sha256_allowlist) <= set(
            self.evidence_sha256_allowlist
        ):
            raise ReconciliationIntegrityError(
                "Reviewed adjudication allowlist must be a subset of evidence allowlist"
            )
        groups = self.evidence_independence_groups
        if not isinstance(groups, tuple) or any(
            not isinstance(item, tuple)
            or len(item) != 2
            or not isinstance(item[0], str)
            or not _SHA256_RE.fullmatch(item[0])
            or not isinstance(item[1], str)
            or not item[1]
            for item in groups
        ):
            raise ReconciliationIntegrityError(
                "Authority evidence_independence_groups must contain SHA/group pairs"
            )
        if groups != tuple(sorted(set(groups))) or len(
            {item[0] for item in groups}
        ) != len(groups):
            raise ReconciliationIntegrityError(
                "Authority evidence_independence_groups must be canonical and unique"
            )
        if not {item[0] for item in groups} <= set(self.evidence_sha256_allowlist):
            raise ReconciliationIntegrityError(
                "Authority independence evidence must be in the evidence allowlist"
            )

    def body_dict(self) -> dict[str, Any]:
        return {
            "expected_dates": [
                value.isoformat() for value in sorted(self.expected_dates)
            ],
            "expected_old_rows_sha256": self.expected_old_rows_sha256,
            "expected_official_rows_sha256": self.expected_official_rows_sha256,
            "evidence_sha256_allowlist": sorted(self.evidence_sha256_allowlist),
            "reviewed_adjudication_sha256_allowlist": sorted(
                self.reviewed_adjudication_sha256_allowlist
            ),
            "evidence_independence_groups": [
                list(item) for item in self.evidence_independence_groups
            ],
        }

    @property
    def authority_sha256(self) -> str:
        return sha256(_canonical_json(self.body_dict())).hexdigest()


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


@dataclass(frozen=True)
class EvidenceReference:
    provider: str
    source_type: str
    url: str | None
    video_id: str | None
    download_sha256: str
    frame_sha256: str | None
    frame_summary: str
    supported_row_sha256s: tuple[str, ...]
    rejected_row_sha256s: tuple[str, ...]

    def body_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "source_type": self.source_type,
            "url": self.url,
            "video_id": self.video_id,
            "download_sha256": self.download_sha256,
            "frame_sha256": self.frame_sha256,
            "frame_summary": self.frame_summary,
            "supported_row_sha256s": list(self.supported_row_sha256s),
            "rejected_row_sha256s": list(self.rejected_row_sha256s),
        }

    @property
    def evidence_sha256(self) -> str:
        return sha256(_canonical_json(self.body_dict())).hexdigest()

    def to_manifest_dict(self) -> dict[str, Any]:
        return {**self.body_dict(), "evidence_sha256": self.evidence_sha256}


def _evidence_reference(
    value: EvidenceReference | Mapping[str, Any],
) -> EvidenceReference:
    if isinstance(value, EvidenceReference):
        raw = value.body_dict()
    elif isinstance(value, Mapping):
        raw = value
    else:
        raise TypeError(
            "Evidence references must be mappings or EvidenceReference values"
        )

    raw_supported = raw.get("supported_row_sha256s", ())
    raw_rejected = raw.get("rejected_row_sha256s", ())
    if not isinstance(raw_supported, (list, tuple)) or not isinstance(
        raw_rejected, (list, tuple)
    ):
        raise ValueError("Evidence row claims must be lists or tuples")
    if any(not isinstance(value, str) for value in (*raw_supported, *raw_rejected)):
        raise ValueError("Evidence row claims must contain SHA-256 strings")
    reference = EvidenceReference(
        provider=raw.get("provider"),
        source_type=raw.get("source_type"),
        url=raw.get("url"),
        video_id=raw.get("video_id"),
        download_sha256=raw.get("download_sha256"),
        frame_sha256=raw.get("frame_sha256"),
        frame_summary=raw.get("frame_summary"),
        supported_row_sha256s=tuple(sorted(set(raw_supported))),
        rejected_row_sha256s=tuple(sorted(set(raw_rejected))),
    )

    for field_name in ("provider", "source_type", "download_sha256", "frame_summary"):
        if not isinstance(getattr(reference, field_name), str) or not getattr(
            reference, field_name
        ):
            raise ValueError(f"Evidence reference requires non-empty {field_name}")
    if not reference.url and not reference.video_id:
        raise ValueError("Evidence reference requires url or video_id")
    if reference.url is not None and not isinstance(reference.url, str):
        raise ValueError("Evidence url must be a string or null")
    if reference.video_id is not None and not isinstance(reference.video_id, str):
        raise ValueError("Evidence video_id must be a string or null")
    if not _SHA256_RE.fullmatch(reference.download_sha256):
        raise ValueError(
            "Evidence download_sha256 must be lowercase hexadecimal SHA-256"
        )
    if reference.frame_sha256 is not None and not _SHA256_RE.fullmatch(
        reference.frame_sha256
    ):
        raise ValueError("Evidence frame_sha256 must be lowercase hexadecimal SHA-256")
    if not reference.supported_row_sha256s and not reference.rejected_row_sha256s:
        raise ValueError(
            "Evidence reference must support or reject at least one row SHA-256"
        )
    for row_sha256 in (
        *reference.supported_row_sha256s,
        *reference.rejected_row_sha256s,
    ):
        if not isinstance(row_sha256, str) or not _SHA256_RE.fullmatch(row_sha256):
            raise ValueError(
                "Evidence row claims must be lowercase hexadecimal SHA-256"
            )
    if set(reference.supported_row_sha256s) & set(reference.rejected_row_sha256s):
        raise ValueError(
            "One evidence asset cannot both support and reject the same row"
        )
    return reference


def _evidence_by_date(
    evidence_by_date: Mapping[date, Any],
) -> dict[date, tuple[EvidenceReference, ...]]:
    normalized = {}
    for draw_date, values in evidence_by_date.items():
        if not isinstance(draw_date, date):
            raise TypeError("Evidence keys must be datetime.date values")
        if isinstance(values, (EvidenceReference, Mapping)):
            values = [values]
        references = tuple(_evidence_reference(value) for value in values)
        normalized[draw_date] = tuple(
            sorted(set(references), key=lambda reference: reference.evidence_sha256)
        )
    return normalized


@dataclass(frozen=True)
class ReconciliationDecision:
    draw_date: date
    decision_type: str
    resolution_policy: str
    old_row: Draw | None
    official_row: Draw | None
    official_evidence_refs: tuple[str, ...] = ()

    def to_manifest_dict(self) -> dict[str, Any]:
        return {
            "draw_date": self.draw_date.isoformat(),
            "decision_type": self.decision_type,
            "resolution_policy": self.resolution_policy,
            "old_row": _draw_dict(self.old_row),
            "old_row_sha256": _draw_sha256(self.old_row),
            "official_row": _draw_dict(self.official_row),
            "official_row_sha256": _draw_sha256(self.official_row),
            "official_evidence_refs": list(self.official_evidence_refs),
        }


@dataclass(frozen=True)
class ReconciliationSummary:
    old_count: int
    official_count: int
    decision_count: int
    unchanged: int
    inserted: int
    deleted: int
    updated: int
    unresolved: int
    corrected_count: int

    def to_manifest_dict(self) -> dict[str, int]:
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
class ReconciliationCoverage:
    history_start: date | None
    history_through: date | None
    expected_date_count: int
    expected_dates_sha256: str
    expected_old_rows_sha256: str
    expected_official_rows_sha256: str
    actual_old_rows_sha256: str
    actual_official_rows_sha256: str
    coverage_anchor_sha256: str

    def to_manifest_dict(self) -> dict[str, Any]:
        return {
            "history_start": self.history_start.isoformat()
            if self.history_start
            else None,
            "history_through": self.history_through.isoformat()
            if self.history_through
            else None,
            "expected_date_count": self.expected_date_count,
            "expected_dates_sha256": self.expected_dates_sha256,
            "expected_old_rows_sha256": self.expected_old_rows_sha256,
            "expected_official_rows_sha256": self.expected_official_rows_sha256,
            "actual_old_rows_sha256": self.actual_old_rows_sha256,
            "actual_official_rows_sha256": self.actual_official_rows_sha256,
            "coverage_anchor_sha256": self.coverage_anchor_sha256,
        }


@dataclass(frozen=True)
class ReconciliationManifest:
    schema_version: str
    authority_sha256: str
    coverage: ReconciliationCoverage
    source_assets: tuple[EvidenceReference, ...]
    decisions: tuple[ReconciliationDecision, ...]
    summary: ReconciliationSummary
    coverage_gaps: tuple[str, ...]
    provisional_rows_sha256: str
    corrected_rows_sha256: str | None
    closure_allowed: bool
    manifest_sha256: str

    def body_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "authority_sha256": self.authority_sha256,
            "coverage": self.coverage.to_manifest_dict(),
            "source_assets": [
                source.to_manifest_dict() for source in self.source_assets
            ],
            "decisions": [decision.to_manifest_dict() for decision in self.decisions],
            "summary": self.summary.to_manifest_dict(),
            "coverage_gaps": list(self.coverage_gaps),
            "provisional_rows_sha256": self.provisional_rows_sha256,
            "corrected_rows_sha256": self.corrected_rows_sha256,
            "closure_allowed": self.closure_allowed,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.body_dict(), "manifest_sha256": self.manifest_sha256}


@dataclass(frozen=True)
class HistoricalReconciliation:
    manifest: ReconciliationManifest
    _validation_capability: object | None = field(
        default=None,
        init=False,
        repr=False,
        compare=False,
    )
    _external_manifest_sha256: str | None = field(
        default=None,
        init=False,
        repr=False,
        compare=False,
    )

    @property
    def decisions(self) -> tuple[ReconciliationDecision, ...]:
        return self.manifest.decisions

    @property
    def summary(self) -> ReconciliationSummary:
        return self.manifest.summary

    @property
    def provisional_draws(self) -> tuple[Draw, ...]:
        return _provisional_draws_from_decisions(self.manifest.decisions)

    @property
    def corrected_draws(self) -> tuple[Draw, ...]:
        if type(self) is not HistoricalReconciliation:
            raise ReconciliationIntegrityError(
                "Corrected draws require the exact validator result type"
            )
        if self._validation_capability is not _VALIDATED_RECONCILIATION_CAPABILITY:
            raise ReconciliationIntegrityError(
                "Reconciliation is not validated, is unresolved, or lacks an external seal"
            )
        calculated_manifest_sha256 = sha256(
            _canonical_json(self.manifest.body_dict())
        ).hexdigest()
        if (
            self._external_manifest_sha256 is None
            or self.manifest.manifest_sha256 != self._external_manifest_sha256
            or calculated_manifest_sha256 != self._external_manifest_sha256
        ):
            raise ReconciliationIntegrityError(
                "Reconciliation no longer matches its validated external seal"
            )
        if not self.closure_allowed:
            raise ReconciliationIntegrityError(
                "Reconciliation is unresolved or has not passed its external seal"
            )
        corrected = self.provisional_draws
        if (
            self.manifest.coverage_gaps
            or any(
                decision.decision_type == "unresolved_dispute"
                for decision in self.decisions
            )
            or self.manifest.corrected_rows_sha256 != _rows_sha256(corrected)
        ):
            raise ReconciliationIntegrityError(
                "Validated reconciliation manifest has no corrected draw projection"
            )
        return corrected

    @property
    def closure_allowed(self) -> bool:
        return self.manifest.closure_allowed

    @property
    def manifest_sha256(self) -> str:
        return self.manifest.manifest_sha256


def _draw_dict(draw: Draw | None) -> dict[str, Any] | None:
    if draw is None:
        return None
    return {
        "draw_date": draw.draw_date.isoformat(),
        "numbers": list(draw.numbers),
        "bonus": draw.bonus,
    }


def _draw_sha256(draw: Draw | None) -> str | None:
    payload = _draw_dict(draw)
    return sha256(_canonical_json(payload)).hexdigest() if payload is not None else None


def _provisional_draws_from_decisions(
    decisions: Sequence[ReconciliationDecision],
) -> tuple[Draw, ...]:
    provisional = []
    for decision in decisions:
        if decision.decision_type == "delete_spurious_wrong_year_row":
            continue
        row = (
            decision.old_row
            if decision.decision_type == "unresolved_dispute"
            else decision.official_row
        )
        if row is not None:
            provisional.append(row)
    return tuple(provisional)


def _resolution_policy(
    old_row: Draw | None,
    official_row: Draw | None,
    references: tuple[EvidenceReference, ...],
    evidence_allowlist: set[str],
    reviewed_adjudication_allowlist: set[str],
    evidence_independence_groups: Mapping[str, str],
) -> str | None:
    old_sha256 = _draw_sha256(old_row)
    official_sha256 = _draw_sha256(official_row)
    if old_row == official_row:
        conflicts_with_equal_row = any(
            old_sha256 in reference.rejected_row_sha256s
            or any(
                row_sha256 != old_sha256
                for row_sha256 in reference.supported_row_sha256s
            )
            for reference in references
        )
        if conflicts_with_equal_row:
            return None
        return "exact_row_equality"

    trusted_references = tuple(
        reference
        for reference in references
        if reference.evidence_sha256 in evidence_allowlist
        and reference.source_type != "reviewed_adjudication"
    )
    authorized_adjudications = tuple(
        reference
        for reference in references
        if reference.source_type == "reviewed_adjudication"
        and reference.evidence_sha256 in evidence_allowlist
        and reference.evidence_sha256 in reviewed_adjudication_allowlist
    )
    if official_sha256 is not None:
        supporting = tuple(
            reference
            for reference in trusted_references
            if official_sha256 in reference.supported_row_sha256s
        )
        conflicting = any(
            official_sha256 in reference.rejected_row_sha256s
            or (
                old_sha256 is not None and old_sha256 in reference.supported_row_sha256s
            )
            for reference in references
        )
        adjudicated = any(
            official_sha256 in reference.supported_row_sha256s
            and (old_sha256 is None or old_sha256 in reference.rejected_row_sha256s)
            for reference in authorized_adjudications
        )
        adjudication_conflict = any(
            official_sha256 in reference.rejected_row_sha256s
            or (
                old_sha256 is not None and old_sha256 in reference.supported_row_sha256s
            )
            for reference in authorized_adjudications
        )
    else:
        supporting = tuple(
            reference
            for reference in trusted_references
            if old_sha256 in reference.rejected_row_sha256s
        )
        conflicting = any(
            old_sha256 in reference.supported_row_sha256s for reference in references
        )
        adjudicated = any(
            old_sha256 in reference.rejected_row_sha256s
            for reference in authorized_adjudications
        )
        adjudication_conflict = any(
            old_sha256 in reference.supported_row_sha256s
            for reference in authorized_adjudications
        )

    if adjudication_conflict:
        return None
    if adjudicated:
        return "reviewed_adjudication"
    if conflicting:
        return None
    independent_groups = {
        evidence_independence_groups[reference.evidence_sha256]
        for reference in supporting
        if reference.evidence_sha256 in evidence_independence_groups
    }
    independent_downloads = {reference.download_sha256 for reference in supporting}
    if len(independent_groups) >= 2 and len(independent_downloads) >= 2:
        return "two_independent_source_assets"
    return None


def _rows_sha256(draws: Sequence[Draw]) -> str:
    rows = [_draw_dict(draw) for draw in sorted(draws, key=lambda draw: draw.draw_date)]
    return sha256(_canonical_json(rows)).hexdigest()


def _coverage(
    authority: ReconciliationAuthority,
    old_draws: Sequence[Draw],
    official_draws: Sequence[Draw],
) -> ReconciliationCoverage:
    expected_dates = tuple(sorted(set(authority.expected_dates)))
    anchor_body = {
        "history_start": expected_dates[0].isoformat() if expected_dates else None,
        "history_through": expected_dates[-1].isoformat() if expected_dates else None,
        "expected_date_count": len(expected_dates),
        "expected_dates_sha256": sha256(
            _canonical_json([value.isoformat() for value in expected_dates])
        ).hexdigest(),
        "expected_old_rows_sha256": authority.expected_old_rows_sha256,
        "expected_official_rows_sha256": authority.expected_official_rows_sha256,
        "actual_old_rows_sha256": _rows_sha256(old_draws),
        "actual_official_rows_sha256": _rows_sha256(official_draws),
    }
    return ReconciliationCoverage(
        history_start=expected_dates[0] if expected_dates else None,
        history_through=expected_dates[-1] if expected_dates else None,
        expected_date_count=anchor_body["expected_date_count"],
        expected_dates_sha256=anchor_body["expected_dates_sha256"],
        expected_old_rows_sha256=authority.expected_old_rows_sha256,
        expected_official_rows_sha256=authority.expected_official_rows_sha256,
        actual_old_rows_sha256=anchor_body["actual_old_rows_sha256"],
        actual_official_rows_sha256=anchor_body["actual_official_rows_sha256"],
        coverage_anchor_sha256=sha256(_canonical_json(anchor_body)).hexdigest(),
    )


def _coverage_gaps(
    expected_dates: Sequence[date],
    official_draws: Sequence[Draw],
    projected_draws: Sequence[Draw],
) -> tuple[str, ...]:
    expected = set(expected_dates)
    gaps = []
    for label, draws in (
        ("official", official_draws),
        ("corrected", projected_draws),
    ):
        actual = {draw.draw_date for draw in draws}
        gaps.extend(
            f"{label}_missing:{draw_date.isoformat()}"
            for draw_date in sorted(expected - actual)
        )
        gaps.extend(
            f"{label}_unexpected:{draw_date.isoformat()}"
            for draw_date in sorted(actual - expected)
        )
    return tuple(sorted(gaps))


def _manifest(
    *,
    authority: ReconciliationAuthority,
    old_draws: Sequence[Draw],
    official_draws: Sequence[Draw],
    source_assets: tuple[EvidenceReference, ...],
    decisions: tuple[ReconciliationDecision, ...],
    summary: ReconciliationSummary,
    coverage_gaps: tuple[str, ...],
    closure_allowed: bool,
) -> ReconciliationManifest:
    provisional_draws = _provisional_draws_from_decisions(decisions)
    provisional_rows_sha256 = _rows_sha256(provisional_draws)
    values = {
        "schema_version": "lotto649-historical-reconciliation-v1",
        "authority_sha256": authority.authority_sha256,
        "coverage": _coverage(authority, old_draws, official_draws),
        "source_assets": source_assets,
        "decisions": decisions,
        "summary": summary,
        "coverage_gaps": coverage_gaps,
        "provisional_rows_sha256": provisional_rows_sha256,
        "corrected_rows_sha256": provisional_rows_sha256 if closure_allowed else None,
        "closure_allowed": closure_allowed,
    }
    provisional = ReconciliationManifest(**values, manifest_sha256="")
    return ReconciliationManifest(
        **values,
        manifest_sha256=sha256(_canonical_json(provisional.body_dict())).hexdigest(),
    )


def _by_date(draws: Sequence[Draw], label: str) -> dict[date, Draw]:
    result: dict[date, Draw] = {}
    for draw in draws:
        if draw.draw_date in result:
            raise ValueError(f"Duplicate {label} draw date: {draw.draw_date}")
        result[draw.draw_date] = draw
    return result


def reconcile_historical_draws(
    old_draws: Sequence[Draw],
    official_draws: Sequence[Draw],
    evidence_by_date: Mapping[date, Any],
    authority: ReconciliationAuthority,
) -> HistoricalReconciliation:
    old_by_date = _by_date(old_draws, "old")
    official_by_date = _by_date(official_draws, "official")
    evidence = _evidence_by_date(evidence_by_date)
    input_row_dates_by_sha256 = {
        row_sha256: draw.draw_date
        for draw in [*old_by_date.values(), *official_by_date.values()]
        if (row_sha256 := _draw_sha256(draw)) is not None
    }
    input_row_sha256s = set(input_row_dates_by_sha256)
    evidence_allowlist = set(authority.evidence_sha256_allowlist)
    reviewed_adjudication_allowlist = set(
        authority.reviewed_adjudication_sha256_allowlist
    )
    evidence_independence_groups = dict(authority.evidence_independence_groups)
    provided_evidence_sha256s = {
        reference.evidence_sha256
        for references in evidence.values()
        for reference in references
    }
    authority_evidence_complete = provided_evidence_sha256s == evidence_allowlist
    row_dates = old_by_date.keys() | official_by_date.keys()
    orphan_evidence_dates = sorted(evidence.keys() - row_dates)
    if orphan_evidence_dates:
        raise ValueError(
            "Evidence has no old or official row for date(s): "
            + ", ".join(draw_date.isoformat() for draw_date in orphan_evidence_dates)
        )
    attached_dates_by_evidence_sha256: dict[str, set[date]] = {}
    for draw_date, references in evidence.items():
        for reference in references:
            attached_dates_by_evidence_sha256.setdefault(
                reference.evidence_sha256, set()
            ).add(draw_date)
    for draw_date, references in evidence.items():
        date_row_sha256s = {
            row_sha256
            for draw in (old_by_date.get(draw_date), official_by_date.get(draw_date))
            if draw is not None and (row_sha256 := _draw_sha256(draw)) is not None
        }
        for reference in references:
            claimed_sha256s = {
                *reference.supported_row_sha256s,
                *reference.rejected_row_sha256s,
            }
            if not claimed_sha256s <= input_row_sha256s:
                raise ReconciliationIntegrityError(
                    "Evidence claim SHA-256 does not belong to an input row"
                )
            if not claimed_sha256s & date_row_sha256s:
                raise ReconciliationIntegrityError(
                    "Evidence reference must claim an old or official row on the same date"
                )
            claimed_dates = {
                input_row_dates_by_sha256[row_sha256] for row_sha256 in claimed_sha256s
            }
            if (
                not claimed_dates
                <= attached_dates_by_evidence_sha256[reference.evidence_sha256]
            ):
                raise ReconciliationIntegrityError(
                    "Evidence must be attached to every claimed row date"
                )
    decisions = []
    for draw_date in sorted(row_dates):
        old_row = old_by_date.get(draw_date)
        official_row = official_by_date.get(draw_date)
        references = evidence.get(draw_date, ())
        refs = tuple(reference.evidence_sha256 for reference in references)
        resolution_policy = _resolution_policy(
            old_row,
            official_row,
            references,
            evidence_allowlist,
            reviewed_adjudication_allowlist,
            evidence_independence_groups,
        )
        if old_row == official_row and resolution_policy is not None:
            decision_type = "unchanged"
        elif (
            old_row is None
            and official_row is not None
            and resolution_policy is not None
        ):
            decision_type = "insert_missing_official_draw"
        elif (
            old_row is not None
            and official_row is None
            and resolution_policy is not None
        ):
            decision_type = "delete_spurious_wrong_year_row"
        elif (
            old_row is not None
            and official_row is not None
            and resolution_policy is not None
        ):
            decision_type = "update_numbers_or_bonus"
        else:
            decision_type = "unresolved_dispute"
            resolution_policy = "insufficient_or_conflicting_evidence"
        decisions.append(
            ReconciliationDecision(
                draw_date,
                decision_type,
                resolution_policy,
                old_row,
                official_row,
                refs,
            )
        )
    decisions_tuple = tuple(decisions)
    inserted = sum(
        decision.decision_type == "insert_missing_official_draw"
        for decision in decisions_tuple
    )
    deleted = sum(
        decision.decision_type == "delete_spurious_wrong_year_row"
        for decision in decisions_tuple
    )
    updated = sum(
        decision.decision_type == "update_numbers_or_bonus"
        for decision in decisions_tuple
    )
    unresolved = sum(
        decision.decision_type == "unresolved_dispute" for decision in decisions_tuple
    )
    provisional_draws = _provisional_draws_from_decisions(decisions_tuple)
    summary = ReconciliationSummary(
        old_count=len(old_by_date),
        official_count=len(official_by_date),
        decision_count=len(decisions_tuple),
        unchanged=sum(
            decision.decision_type == "unchanged" for decision in decisions_tuple
        ),
        inserted=inserted,
        deleted=deleted,
        updated=updated,
        unresolved=unresolved,
        corrected_count=len(provisional_draws),
    )
    used_reference_hashes = {
        reference_hash
        for decision in decisions_tuple
        for reference_hash in decision.official_evidence_refs
    }
    source_assets = tuple(
        sorted(
            {
                reference
                for references in evidence.values()
                for reference in references
                if reference.evidence_sha256 in used_reference_hashes
            },
            key=lambda reference: reference.evidence_sha256,
        )
    )
    authority_rows_match = authority.expected_old_rows_sha256 == _rows_sha256(
        tuple(old_by_date.values())
    ) and authority.expected_official_rows_sha256 == _rows_sha256(
        tuple(official_by_date.values())
    )
    coverage_gaps = _coverage_gaps(
        authority.expected_dates,
        tuple(official_by_date.values()),
        provisional_draws,
    )
    closure_allowed = (
        unresolved == 0
        and authority_rows_match
        and authority_evidence_complete
        and bool(authority.expected_dates)
        and not coverage_gaps
    )
    manifest = _manifest(
        authority=authority,
        old_draws=tuple(old_by_date[draw_date] for draw_date in sorted(old_by_date)),
        official_draws=tuple(
            official_by_date[draw_date] for draw_date in sorted(official_by_date)
        ),
        source_assets=source_assets,
        decisions=decisions_tuple,
        summary=summary,
        coverage_gaps=coverage_gaps,
        closure_allowed=closure_allowed,
    )
    return HistoricalReconciliation(manifest=manifest)


def _validate_reconciliation_manifest(
    manifest: ReconciliationManifest | Mapping[str, Any],
    old_draws: Sequence[Draw],
    official_draws: Sequence[Draw],
    authority: ReconciliationAuthority,
    expected_manifest_sha256: str,
) -> HistoricalReconciliation:
    manifest_dict = (
        manifest.to_dict()
        if isinstance(manifest, ReconciliationManifest)
        else dict(manifest)
    )
    recorded_sha256 = manifest_dict.get("manifest_sha256")
    if not isinstance(recorded_sha256, str) or not _SHA256_RE.fullmatch(
        recorded_sha256
    ):
        raise ReconciliationIntegrityError("Manifest has no valid manifest_sha256")
    if not isinstance(expected_manifest_sha256, str) or not _SHA256_RE.fullmatch(
        expected_manifest_sha256
    ):
        raise ReconciliationIntegrityError(
            "Manifest external expected SHA-256 is invalid"
        )
    if recorded_sha256 != expected_manifest_sha256:
        raise ReconciliationIntegrityError(
            "Manifest does not match external expected SHA-256"
        )
    body = {
        key: value for key, value in manifest_dict.items() if key != "manifest_sha256"
    }
    try:
        calculated_sha256 = sha256(_canonical_json(body)).hexdigest()
    except (TypeError, ValueError) as exc:
        raise ReconciliationIntegrityError(
            "Manifest is not canonical JSON data"
        ) from exc
    if calculated_sha256 != recorded_sha256:
        raise ReconciliationIntegrityError("Manifest canonical SHA-256 mismatch")
    if manifest_dict.get("authority_sha256") != authority.authority_sha256:
        raise ReconciliationIntegrityError("Manifest authority SHA-256 mismatch")

    raw_assets = manifest_dict.get("source_assets")
    if not isinstance(raw_assets, list):
        raise ReconciliationIntegrityError("Manifest source_assets must be a list")
    assets_by_hash: dict[str, EvidenceReference] = {}
    for raw_asset in raw_assets:
        if not isinstance(raw_asset, Mapping):
            raise ReconciliationIntegrityError(
                "Manifest source asset must be an object"
            )
        recorded_evidence_sha256 = raw_asset.get("evidence_sha256")
        reference = _evidence_reference(
            {key: value for key, value in raw_asset.items() if key != "evidence_sha256"}
        )
        if recorded_evidence_sha256 != reference.evidence_sha256:
            raise ReconciliationIntegrityError("Source asset evidence SHA-256 mismatch")
        if reference.evidence_sha256 in assets_by_hash:
            raise ReconciliationIntegrityError(
                "Duplicate source asset evidence SHA-256"
            )
        assets_by_hash[reference.evidence_sha256] = reference

    raw_decisions = manifest_dict.get("decisions")
    if not isinstance(raw_decisions, list):
        raise ReconciliationIntegrityError("Manifest decisions must be a list")
    evidence_by_date: dict[date, list[EvidenceReference]] = {}
    for raw_decision in raw_decisions:
        if not isinstance(raw_decision, Mapping):
            raise ReconciliationIntegrityError("Manifest decision must be an object")
        try:
            draw_date = date.fromisoformat(raw_decision["draw_date"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ReconciliationIntegrityError(
                "Manifest decision has invalid draw_date"
            ) from exc
        raw_refs = raw_decision.get("official_evidence_refs")
        if not isinstance(raw_refs, list) or any(
            not isinstance(reference_hash, str) for reference_hash in raw_refs
        ):
            raise ReconciliationIntegrityError(
                "Manifest decision official_evidence_refs must be a string list"
            )
        try:
            evidence_by_date[draw_date] = [
                assets_by_hash[reference_hash] for reference_hash in raw_refs
            ]
        except KeyError as exc:
            raise ReconciliationIntegrityError(
                "Manifest decision references an unknown source asset"
            ) from exc

    expected = reconcile_historical_draws(
        old_draws, official_draws, evidence_by_date, authority
    )
    if _canonical_json(expected.manifest.to_dict()) != _canonical_json(manifest_dict):
        raise ReconciliationIntegrityError(
            "Manifest does not match independently recomputed reconciliation"
        )
    validated = HistoricalReconciliation(manifest=expected.manifest)
    object.__setattr__(
        validated,
        "_validation_capability",
        _VALIDATED_RECONCILIATION_CAPABILITY,
    )
    object.__setattr__(
        validated,
        "_external_manifest_sha256",
        expected_manifest_sha256,
    )
    return validated


def validate_reconciliation_manifest(
    manifest: ReconciliationManifest | Mapping[str, Any],
    old_draws: Sequence[Draw],
    official_draws: Sequence[Draw],
    authority: ReconciliationAuthority,
    expected_manifest_sha256: str,
) -> HistoricalReconciliation:
    try:
        return _validate_reconciliation_manifest(
            manifest,
            old_draws,
            official_draws,
            authority,
            expected_manifest_sha256,
        )
    except ReconciliationIntegrityError:
        raise
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
        raise ReconciliationIntegrityError("Malformed manifest") from exc
