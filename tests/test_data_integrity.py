from copy import deepcopy
from dataclasses import FrozenInstanceError, fields, replace
from datetime import date
from hashlib import sha256
import json

import pytest

from lotto649.data_integrity import (
    HistoricalReconciliation,
    ReconciliationAuthority,
    ReconciliationIntegrityError,
    ReconciliationSummary,
    reconcile_historical_draws,
    validate_reconciliation_manifest,
)
from lotto649.domain import Draw


def _row_sha256(row: Draw) -> str:
    payload = {
        "draw_date": row.draw_date.isoformat(),
        "numbers": list(row.numbers),
        "bonus": row.bonus,
    }
    return sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _rows_sha256(rows: list[Draw] | tuple[Draw, ...]) -> str:
    payload = [
        {
            "draw_date": row.draw_date.isoformat(),
            "numbers": list(row.numbers),
            "bonus": row.bonus,
        }
        for row in sorted(rows, key=lambda row: row.draw_date)
    ]
    return sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _evidence_sha256(evidence: dict) -> str:
    canonical = deepcopy(evidence)
    canonical["supported_row_sha256s"] = sorted(set(canonical["supported_row_sha256s"]))
    canonical["rejected_row_sha256s"] = sorted(set(canonical["rejected_row_sha256s"]))
    return sha256(
        json.dumps(
            canonical,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _authority(
    old_rows: list[Draw] | tuple[Draw, ...],
    official_rows: list[Draw] | tuple[Draw, ...],
    *,
    expected_dates: tuple[date, ...] | None = None,
    evidence: tuple[dict, ...] = (),
    reviewed_adjudications: tuple[dict, ...] = (),
    independence_groups: tuple[tuple[dict, str], ...] | None = None,
) -> ReconciliationAuthority:
    if expected_dates is None:
        expected_dates = tuple(sorted({row.draw_date for row in official_rows}))
    all_evidence = (*evidence, *reviewed_adjudications)
    if independence_groups is None:
        independence_groups = tuple(
            (
                item,
                "|".join(
                    (
                        item["provider"],
                        item["source_type"],
                        item["url"] or "",
                        item["video_id"] or "",
                    )
                ),
            )
            for item in evidence
            if item["source_type"] != "reviewed_adjudication"
        )
    return ReconciliationAuthority(
        expected_dates=expected_dates,
        expected_old_rows_sha256=_rows_sha256(old_rows),
        expected_official_rows_sha256=_rows_sha256(official_rows),
        evidence_sha256_allowlist=tuple(
            sorted(_evidence_sha256(item) for item in all_evidence)
        ),
        reviewed_adjudication_sha256_allowlist=tuple(
            sorted(_evidence_sha256(item) for item in reviewed_adjudications)
        ),
        evidence_independence_groups=tuple(
            sorted(
                {(_evidence_sha256(item), group) for item, group in independence_groups}
            )
        ),
    )


def _rehash_manifest(manifest: dict) -> None:
    body = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    manifest["manifest_sha256"] = sha256(
        json.dumps(
            body,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _official_archive_evidence(
    summary: str,
    *,
    supports: tuple[Draw, ...] = (),
    rejects: tuple[Draw, ...] = (),
) -> dict:
    return {
        "provider": "Loto-Québec",
        "source_type": "official_results_archive",
        "url": "https://loteries.lotoquebec.com/official-history",
        "video_id": None,
        "download_sha256": "1" * 64,
        "frame_sha256": None,
        "frame_summary": summary,
        "supported_row_sha256s": [_row_sha256(row) for row in supports],
        "rejected_row_sha256s": [_row_sha256(row) for row in rejects],
    }


def _official_video_evidence(
    summary: str,
    *,
    supports: tuple[Draw, ...] = (),
    rejects: tuple[Draw, ...] = (),
) -> dict:
    return {
        "provider": "Loteries Loto-Québec",
        "source_type": "official_draw_video",
        "url": "https://www.youtube.com/watch?v=official-fixture",
        "video_id": "official-fixture",
        "download_sha256": "2" * 64,
        "frame_sha256": "3" * 64,
        "frame_summary": summary,
        "supported_row_sha256s": [_row_sha256(row) for row in supports],
        "rejected_row_sha256s": [_row_sha256(row) for row in rejects],
    }


def _reviewed_adjudication_evidence(
    summary: str, *, supports: tuple[Draw, ...], rejects: tuple[Draw, ...]
) -> dict:
    return {
        "provider": "Independent reconciliation review",
        "source_type": "reviewed_adjudication",
        "url": "https://example.invalid/reviewed-adjudication",
        "video_id": None,
        "download_sha256": "4" * 64,
        "frame_sha256": None,
        "frame_summary": summary,
        "supported_row_sha256s": [_row_sha256(row) for row in supports],
        "rejected_row_sha256s": [_row_sha256(row) for row in rejects],
    }


def test_reconcile_requires_an_external_authority():
    row = Draw(date(2020, 1, 1), (1, 2, 3, 4, 5, 6), 7)

    with pytest.raises(TypeError, match="authority"):
        reconcile_historical_draws([row], [row], {})


def test_wrong_external_authority_never_allows_closure():
    first = Draw(date(2020, 1, 1), (1, 2, 3, 4, 5, 6), 7)
    second = Draw(date(2020, 1, 4), (8, 9, 10, 11, 12, 13), 14)
    authority = ReconciliationAuthority(
        expected_dates=(first.draw_date, second.draw_date),
        expected_old_rows_sha256="f" * 64,
        expected_official_rows_sha256=_rows_sha256([first, second]),
        evidence_sha256_allowlist=(),
        reviewed_adjudication_sha256_allowlist=(),
    )

    result = reconcile_historical_draws([first, second], [first, second], {}, authority)

    assert result.closure_allowed is False


def test_manifest_binds_external_expected_date_set_and_row_hashes():
    first = Draw(date(2020, 1, 1), (1, 2, 3, 4, 5, 6), 7)
    second = Draw(date(2020, 1, 4), (8, 9, 10, 11, 12, 13), 14)
    old_rows = [first, second]
    official_rows = [first, second]
    authority = _authority(old_rows, official_rows)

    result = reconcile_historical_draws(old_rows, official_rows, {}, authority)

    coverage = result.manifest.to_dict()["coverage"]
    assert coverage["expected_date_count"] == 2
    assert coverage["history_start"] == "2020-01-01"
    assert coverage["history_through"] == "2020-01-04"
    assert (
        coverage["expected_dates_sha256"]
        == "2ef34d02476fca5911fbce2083fcce29ff387c576ceb8b6d94df9a49dbab90ab"
    )
    assert coverage["expected_old_rows_sha256"] == _rows_sha256(old_rows)
    assert coverage["expected_official_rows_sha256"] == _rows_sha256(official_rows)
    assert "expected_dates" not in coverage
    assert result.closure_allowed is True


def test_authority_rejects_a_noncanonical_expected_date_set():
    duplicate = date(2020, 1, 1)

    with pytest.raises(ReconciliationIntegrityError, match="expected_dates"):
        ReconciliationAuthority(
            expected_dates=(duplicate, duplicate),
            expected_old_rows_sha256="a" * 64,
            expected_official_rows_sha256="b" * 64,
            evidence_sha256_allowlist=(),
            reviewed_adjudication_sha256_allowlist=(),
        )


def test_missing_expected_date_is_reported_for_official_and_corrected_coverage():
    first = Draw(date(2020, 1, 1), (1, 2, 3, 4, 5, 6), 7)
    third = Draw(date(2020, 1, 8), (15, 16, 17, 18, 19, 20), 21)
    rows = [first, third]
    authority = _authority(
        rows,
        rows,
        expected_dates=(date(2020, 1, 1), date(2020, 1, 4), date(2020, 1, 8)),
    )

    result = reconcile_historical_draws(rows, rows, {}, authority)

    assert result.manifest.coverage_gaps == (
        "corrected_missing:2020-01-04",
        "official_missing:2020-01-04",
    )
    assert result.closure_allowed is False


def test_wrong_expected_date_boundaries_report_missing_and_unexpected_dates():
    first = Draw(date(2020, 1, 1), (1, 2, 3, 4, 5, 6), 7)
    second = Draw(date(2020, 1, 4), (8, 9, 10, 11, 12, 13), 14)
    rows = [first, second]
    authority = _authority(
        rows,
        rows,
        expected_dates=(date(2020, 1, 4), date(2020, 1, 8)),
    )

    result = reconcile_historical_draws(rows, rows, {}, authority)

    assert result.manifest.coverage_gaps == (
        "corrected_missing:2020-01-08",
        "corrected_unexpected:2020-01-01",
        "official_missing:2020-01-08",
        "official_unexpected:2020-01-01",
    )
    assert result.closure_allowed is False


def test_empty_authority_scope_cannot_close():
    authority = _authority([], [])

    result = reconcile_historical_draws([], [], {}, authority)

    assert result.closure_allowed is False


def test_single_date_authority_can_close_when_its_external_identity_matches():
    row = Draw(date(2020, 1, 1), (1, 2, 3, 4, 5, 6), 7)
    authority = _authority([row], [row])

    result = reconcile_historical_draws([row], [row], {}, authority)

    assert result.closure_allowed is True


def test_unallowlisted_source_evidence_cannot_resolve_a_change():
    anchor = Draw(date(2020, 1, 1), (1, 2, 3, 4, 5, 6), 7)
    inserted = Draw(date(2020, 1, 4), (8, 9, 10, 11, 12, 13), 14)
    evidence = (
        _official_archive_evidence("Archive row", supports=(inserted,)),
        _official_video_evidence("Video row", supports=(inserted,)),
    )
    old_rows = [anchor]
    official_rows = [anchor, inserted]
    authority = _authority(old_rows, official_rows)

    result = reconcile_historical_draws(
        old_rows,
        official_rows,
        {inserted.draw_date: evidence},
        authority,
    )

    assert result.decisions[1].decision_type == "unresolved_dispute"
    assert result.closure_allowed is False


def test_authority_allowlist_is_an_exact_required_evidence_set_not_a_menu():
    old = Draw(date(2020, 2, 29), (6, 12, 15, 18, 31, 43), 13)
    official = Draw(date(2020, 2, 29), (6, 12, 15, 18, 31, 46), 13)
    archive_support = _official_archive_evidence(
        "Archive supports official", supports=(official,)
    )
    video_support = _official_video_evidence(
        "Video supports official", supports=(official,)
    )
    omitted_conflict = _official_archive_evidence(
        "Second archive asset supports old", supports=(old,)
    )
    authority_evidence = (archive_support, video_support, omitted_conflict)

    result = reconcile_historical_draws(
        [old],
        [official],
        {official.draw_date: [archive_support, video_support]},
        _authority([old], [official], evidence=authority_evidence),
    )

    assert result.closure_allowed is False
    with pytest.raises(ReconciliationIntegrityError, match="external seal"):
        _ = result.corrected_draws


def test_reviewed_adjudication_requires_its_separate_authority_allowlist():
    old = Draw(date(2010, 9, 4), (1, 2, 3, 4, 5, 6), 7)
    official = Draw(date(2010, 9, 4), (8, 9, 10, 11, 12, 13), 14)
    anchor = Draw(date(2010, 9, 8), (15, 16, 17, 18, 19, 20), 21)
    conflicting = (
        _official_archive_evidence("Archive supports old", supports=(old,)),
        _official_video_evidence("Video supports official", supports=(official,)),
    )
    adjudication = _reviewed_adjudication_evidence(
        "Reviewed decision supports official and rejects old",
        supports=(official,),
        rejects=(old,),
    )
    old_rows = [old, anchor]
    official_rows = [official, anchor]
    self_declared_authority = _authority(
        old_rows,
        official_rows,
        evidence=(*conflicting, adjudication),
    )
    externally_allowed_authority = _authority(
        old_rows,
        official_rows,
        evidence=conflicting,
        reviewed_adjudications=(adjudication,),
    )

    self_declared = reconcile_historical_draws(
        old_rows,
        official_rows,
        {old.draw_date: (*conflicting, adjudication)},
        self_declared_authority,
    )
    externally_allowed = reconcile_historical_draws(
        old_rows,
        official_rows,
        {old.draw_date: (*conflicting, adjudication)},
        externally_allowed_authority,
    )

    assert self_declared.decisions[0].decision_type == "unresolved_dispute"
    assert self_declared.closure_allowed is False
    assert externally_allowed.decisions[0].decision_type == "update_numbers_or_bonus"
    assert externally_allowed.closure_allowed is True


def test_general_only_adjudication_cannot_masquerade_as_second_source_asset():
    old = Draw(date(2010, 9, 4), (1, 2, 3, 4, 5, 6), 7)
    official = Draw(date(2010, 9, 4), (8, 9, 10, 11, 12, 13), 14)
    archive = _official_archive_evidence(
        "Archive supports official", supports=(official,)
    )
    self_declared = _reviewed_adjudication_evidence(
        "Not externally allowed as an adjudication",
        supports=(official,),
        rejects=(old,),
    )
    evidence = (archive, self_declared)

    result = reconcile_historical_draws(
        [old],
        [official],
        {official.draw_date: evidence},
        _authority([old], [official], evidence=evidence),
    )

    assert result.decisions[0].decision_type == "unresolved_dispute"
    assert result.closure_allowed is False


def test_conflicting_allowlisted_adjudications_cannot_close():
    old = Draw(date(2010, 9, 4), (1, 2, 3, 4, 5, 6), 7)
    official = Draw(date(2010, 9, 4), (8, 9, 10, 11, 12, 13), 14)
    accepts_official = _reviewed_adjudication_evidence(
        "Review accepts official",
        supports=(official,),
        rejects=(old,),
    )
    accepts_old = _reviewed_adjudication_evidence(
        "Review accepts old",
        supports=(old,),
        rejects=(official,),
    )
    adjudications = (accepts_official, accepts_old)

    result = reconcile_historical_draws(
        [old],
        [official],
        {official.draw_date: adjudications},
        _authority(
            [old],
            [official],
            reviewed_adjudications=adjudications,
        ),
    )

    assert result.decisions[0].decision_type == "unresolved_dispute"
    assert result.closure_allowed is False


def test_evidence_claim_sha_must_belong_to_an_input_row():
    anchor = Draw(date(2020, 1, 1), (1, 2, 3, 4, 5, 6), 7)
    inserted = Draw(date(2020, 1, 4), (8, 9, 10, 11, 12, 13), 14)
    archive = _official_archive_evidence("Archive row", supports=(inserted,))
    archive["supported_row_sha256s"].append("f" * 64)
    video = _official_video_evidence("Video row", supports=(inserted,))
    evidence = (archive, video)
    old_rows = [anchor]
    official_rows = [anchor, inserted]
    authority = _authority(old_rows, official_rows, evidence=evidence)

    with pytest.raises(ReconciliationIntegrityError, match="input row"):
        reconcile_historical_draws(
            old_rows,
            official_rows,
            {inserted.draw_date: evidence},
            authority,
        )


def test_evidence_date_reference_must_claim_that_dates_old_or_official_row():
    anchor = Draw(date(2020, 1, 1), (1, 2, 3, 4, 5, 6), 7)
    inserted = Draw(date(2020, 1, 4), (8, 9, 10, 11, 12, 13), 14)
    misplaced = _official_archive_evidence(
        "Claims a different date", supports=(anchor,)
    )
    old_rows = [anchor]
    official_rows = [anchor, inserted]
    authority = _authority(old_rows, official_rows, evidence=(misplaced,))

    with pytest.raises(ReconciliationIntegrityError, match="same date"):
        reconcile_historical_draws(
            old_rows,
            official_rows,
            {inserted.draw_date: [misplaced]},
            authority,
        )


def test_multi_date_evidence_must_be_attached_to_every_claimed_row_date():
    unchanged = Draw(date(2020, 1, 1), (1, 2, 3, 4, 5, 6), 7)
    inserted = Draw(date(2020, 1, 4), (8, 9, 10, 11, 12, 13), 14)
    laundering_asset = _official_archive_evidence(
        "Supports inserted row but rejects unchanged row",
        supports=(inserted,),
        rejects=(unchanged,),
    )
    second_support = _official_video_evidence(
        "Second support for inserted row", supports=(inserted,)
    )
    evidence = (laundering_asset, second_support)
    old_rows = [unchanged]
    official_rows = [unchanged, inserted]

    with pytest.raises(ReconciliationIntegrityError, match="every claimed row date"):
        reconcile_historical_draws(
            old_rows,
            official_rows,
            {inserted.draw_date: evidence},
            _authority(old_rows, official_rows, evidence=evidence),
        )


def test_unchanged_row_becomes_unresolved_when_evidence_rejects_it_or_supports_third_row():
    current = Draw(date(2020, 1, 1), (1, 2, 3, 4, 5, 6), 7)
    other = Draw(date(2020, 1, 4), (8, 9, 10, 11, 12, 13), 14)
    rows = [current, other]
    rejecting = _official_archive_evidence(
        "Rejects the apparently unchanged row", rejects=(current,)
    )
    third_row_support = _official_archive_evidence(
        "Claims current date but also supports another input row",
        supports=(current, other),
    )

    results = tuple(
        reconcile_historical_draws(
            rows,
            rows,
            {
                current.draw_date: [evidence],
                **(
                    {other.draw_date: [evidence]}
                    if evidence is third_row_support
                    else {}
                ),
            },
            _authority(rows, rows, evidence=(evidence,)),
        )
        for evidence in (rejecting, third_row_support)
    )

    assert tuple(result.decisions[0].decision_type for result in results) == (
        "unresolved_dispute",
        "unresolved_dispute",
    )
    assert all(result.closure_allowed is False for result in results)


def test_unallowlisted_evidence_conflict_still_marks_equal_row_unresolved():
    current = Draw(date(2020, 1, 1), (1, 2, 3, 4, 5, 6), 7)
    anchor = Draw(date(2020, 1, 4), (8, 9, 10, 11, 12, 13), 14)
    rows = [current, anchor]
    rejecting = _official_archive_evidence(
        "Unallowlisted asset rejects current row", rejects=(current,)
    )

    result = reconcile_historical_draws(
        rows,
        rows,
        {current.draw_date: [rejecting]},
        _authority(rows, rows),
    )

    assert result.decisions[0].decision_type == "unresolved_dispute"
    assert result.closure_allowed is False


def test_unresolved_reconciliation_exposes_only_provisional_draws():
    old = Draw(date(2021, 8, 4), (3, 8, 21, 38, 42, 48), 27)
    official = Draw(date(2021, 8, 4), (3, 8, 21, 38, 42, 49), 27)
    anchor = Draw(date(2021, 8, 7), (1, 2, 4, 5, 6, 7), 8)
    old_rows = [old, anchor]
    official_rows = [official, anchor]

    result = reconcile_historical_draws(
        old_rows,
        official_rows,
        {},
        _authority(old_rows, official_rows),
    )

    assert result.provisional_draws == (old, anchor)
    with pytest.raises(ReconciliationIntegrityError, match="unresolved"):
        _ = result.corrected_draws


def test_unresolved_manifest_labels_projection_as_provisional_not_corrected():
    old = Draw(date(2021, 8, 4), (3, 8, 21, 38, 42, 48), 27)
    official = Draw(date(2021, 8, 4), (3, 8, 21, 38, 42, 49), 27)
    anchor = Draw(date(2021, 8, 7), (1, 2, 4, 5, 6, 7), 8)
    old_rows = [old, anchor]
    official_rows = [official, anchor]

    manifest = reconcile_historical_draws(
        old_rows,
        official_rows,
        {},
        _authority(old_rows, official_rows),
    ).manifest.to_dict()

    assert manifest["provisional_rows_sha256"] == _rows_sha256([old, anchor])
    assert manifest["corrected_rows_sha256"] is None


def test_corrected_draws_require_validator_granted_external_seal_capability():
    row = Draw(date(2020, 1, 1), (1, 2, 3, 4, 5, 6), 7)
    rows = [row]
    authority = _authority(rows, rows)
    produced = reconcile_historical_draws(rows, rows, {}, authority)

    with pytest.raises(ReconciliationIntegrityError, match="validated"):
        _ = produced.corrected_draws

    validated = validate_reconciliation_manifest(
        produced.manifest.to_dict(),
        rows,
        rows,
        authority,
        produced.manifest_sha256,
    )
    assert validated.corrected_draws == (row,)


def test_dataclass_replace_cannot_forge_corrected_draw_capability():
    old = Draw(date(2021, 8, 4), (3, 8, 21, 38, 42, 48), 27)
    official = Draw(date(2021, 8, 4), (3, 8, 21, 38, 42, 49), 27)
    unresolved = reconcile_historical_draws(
        [old],
        [official],
        {},
        _authority([old], [official]),
    )
    forged_decision = replace(
        unresolved.decisions[0],
        decision_type="update_numbers_or_bonus",
        resolution_policy="forged",
    )
    forged_manifest = replace(
        unresolved.manifest,
        decisions=(forged_decision,),
        closure_allowed=True,
        corrected_rows_sha256=_rows_sha256([official]),
    )
    forged = HistoricalReconciliation(forged_manifest)

    with pytest.raises(ReconciliationIntegrityError, match="validated"):
        _ = forged.corrected_draws


def test_transferred_private_token_cannot_validate_a_stale_hash_manifest():
    honest = Draw(date(2020, 1, 1), (1, 2, 3, 4, 5, 6), 7)
    forged_official = Draw(date(2020, 1, 1), (8, 9, 10, 11, 12, 13), 14)
    authority = _authority([honest], [honest])
    produced = reconcile_historical_draws([honest], [honest], {}, authority)
    validated = validate_reconciliation_manifest(
        produced.manifest.to_dict(),
        [honest],
        [honest],
        authority,
        produced.manifest_sha256,
    )
    forged_decision = replace(
        produced.decisions[0],
        decision_type="update_numbers_or_bonus",
        resolution_policy="forged",
        official_row=forged_official,
    )
    forged_manifest = replace(
        produced.manifest,
        decisions=(forged_decision,),
        corrected_rows_sha256=_rows_sha256([forged_official]),
    )

    class TokenTransfer(HistoricalReconciliation):
        _validation_capability = validated._validation_capability

    forged = TokenTransfer(forged_manifest)

    with pytest.raises(
        ReconciliationIntegrityError, match="exact validator result type"
    ):
        _ = forged.corrected_draws


def test_subclass_cannot_transfer_token_and_coherent_external_pin():
    honest = Draw(date(2020, 1, 1), (1, 2, 3, 4, 5, 6), 7)
    honest_authority = _authority([honest], [honest])
    honest_produced = reconcile_historical_draws(
        [honest],
        [honest],
        {},
        honest_authority,
    )
    validated = validate_reconciliation_manifest(
        honest_produced.manifest.to_dict(),
        [honest],
        [honest],
        honest_authority,
        honest_produced.manifest_sha256,
    )

    forged_row = Draw(date(2020, 1, 1), (8, 9, 10, 11, 12, 13), 14)
    forged_authority = _authority([forged_row], [forged_row])
    forged_produced = reconcile_historical_draws(
        [forged_row],
        [forged_row],
        {},
        forged_authority,
    )

    class CoherentTokenAndPinTransfer(HistoricalReconciliation):
        _validation_capability = validated._validation_capability
        _external_manifest_sha256 = forged_produced.manifest_sha256

    forged = CoherentTokenAndPinTransfer(forged_produced.manifest)

    with pytest.raises(
        ReconciliationIntegrityError, match="exact validator result type"
    ):
        _ = forged.corrected_draws


def test_manifest_validation_requires_an_external_expected_manifest_sha():
    first = Draw(date(2020, 1, 1), (1, 2, 3, 4, 5, 6), 7)
    second = Draw(date(2020, 1, 4), (8, 9, 10, 11, 12, 13), 14)
    rows = [first, second]
    authority = _authority(rows, rows)
    manifest = reconcile_historical_draws(rows, rows, {}, authority).manifest.to_dict()

    with pytest.raises(TypeError, match="expected_manifest_sha256"):
        validate_reconciliation_manifest(manifest, rows, rows, authority)


def test_manifest_validation_rejects_wrong_external_manifest_sha_pin():
    first = Draw(date(2020, 1, 1), (1, 2, 3, 4, 5, 6), 7)
    second = Draw(date(2020, 1, 4), (8, 9, 10, 11, 12, 13), 14)
    rows = [first, second]
    authority = _authority(rows, rows)
    manifest = reconcile_historical_draws(rows, rows, {}, authority).manifest.to_dict()

    with pytest.raises(ReconciliationIntegrityError, match="external expected"):
        validate_reconciliation_manifest(
            manifest,
            rows,
            rows,
            authority,
            "f" * 64,
        )


def test_manifest_validation_rejects_a_different_external_authority_identity():
    first = Draw(date(2020, 1, 1), (1, 2, 3, 4, 5, 6), 7)
    second = Draw(date(2020, 1, 4), (8, 9, 10, 11, 12, 13), 14)
    rows = [first, second]
    authority = _authority(rows, rows)
    produced = reconcile_historical_draws(rows, rows, {}, authority)
    manifest = produced.manifest.to_dict()
    different_authority = ReconciliationAuthority(
        expected_dates=authority.expected_dates,
        expected_old_rows_sha256=authority.expected_old_rows_sha256,
        expected_official_rows_sha256=authority.expected_official_rows_sha256,
        evidence_sha256_allowlist=("f" * 64,),
        reviewed_adjudication_sha256_allowlist=(),
    )

    with pytest.raises(ReconciliationIntegrityError, match="authority"):
        validate_reconciliation_manifest(
            manifest,
            rows,
            rows,
            different_authority,
            produced.manifest_sha256,
        )


def test_reconcile_records_unchanged_row_once_and_closes():
    row = Draw(date(2020, 1, 1), (1, 2, 3, 4, 5, 6), 7)

    result = reconcile_historical_draws([row], [row], {}, _authority([row], [row]))

    assert len(result.decisions) == 1
    assert result.decisions[0].decision_type == "unchanged"
    assert result.summary.unchanged == 1
    assert result.summary.corrected_count == 1
    assert result.provisional_draws == (row,)
    assert result.closure_allowed is True


def test_reconcile_inserts_evidenced_official_row():
    inserted = Draw(date(2020, 1, 4), (8, 9, 10, 11, 12, 13), 14)
    evidence = _official_archive_evidence(
        "Official row: 2020-01-04 08 09 10 11 12 13 bonus 14",
        supports=(inserted,),
    )
    video_evidence = _official_video_evidence(
        "Official result card: 08 09 10 11 12 13 bonus 14",
        supports=(inserted,),
    )

    source_evidence = (evidence, video_evidence)
    result = reconcile_historical_draws(
        [],
        [inserted],
        {inserted.draw_date: source_evidence},
        _authority([], [inserted], evidence=source_evidence),
    )

    assert len(result.decisions) == 1
    assert result.decisions[0].decision_type == "insert_missing_official_draw"
    assert len(result.decisions[0].official_evidence_refs) == 2
    assert result.summary.inserted == 1
    assert result.provisional_draws == (inserted,)
    assert result.closure_allowed is True


def test_reconcile_deletes_evidenced_spurious_wrong_year_row():
    anchor = Draw(date(2023, 12, 27), (1, 3, 5, 7, 9, 11), 13)
    spurious = Draw(date(2023, 12, 28), (2, 10, 16, 17, 24, 26), 18)
    evidence = _official_archive_evidence(
        "Official source chronology proves 2023-12-28 is a spurious wrong-year row",
        rejects=(spurious,),
    )
    video_evidence = _official_video_evidence(
        "Official chronology frame excludes the spurious wrong-year row",
        rejects=(spurious,),
    )

    source_evidence = (evidence, video_evidence)
    old_rows = [anchor, spurious]
    official_rows = [anchor]
    result = reconcile_historical_draws(
        old_rows,
        official_rows,
        {spurious.draw_date: source_evidence},
        _authority(old_rows, official_rows, evidence=source_evidence),
    )

    assert len(result.decisions) == 2
    assert result.decisions[1].decision_type == "delete_spurious_wrong_year_row"
    assert len(result.decisions[1].official_evidence_refs) == 2
    assert result.summary.deleted == 1
    assert result.provisional_draws == (anchor,)
    assert result.closure_allowed is True


def test_reconcile_updates_evidenced_numbers_or_bonus():
    old = Draw(date(2020, 2, 29), (6, 12, 15, 18, 31, 43), 13)
    official = Draw(date(2020, 2, 29), (6, 12, 15, 18, 31, 46), 13)
    evidence = _official_video_evidence(
        "Official result card: 06 12 15 18 31 46 bonus 13",
        supports=(official,),
    )
    archive_evidence = _official_archive_evidence(
        "Official archive row: 06 12 15 18 31 46 bonus 13",
        supports=(official,),
    )

    source_evidence = (archive_evidence, evidence)
    result = reconcile_historical_draws(
        [old],
        [official],
        {official.draw_date: source_evidence},
        _authority([old], [official], evidence=source_evidence),
    )

    assert len(result.decisions) == 1
    assert result.decisions[0].decision_type == "update_numbers_or_bonus"
    assert result.decisions[0].old_row == old
    assert result.decisions[0].official_row == official
    assert result.summary.updated == 1
    assert result.provisional_draws == (official,)
    assert result.closure_allowed is True


def test_reconcile_leaves_unsupported_dispute_unresolved_and_blocks_closure():
    old = Draw(date(2021, 8, 4), (3, 8, 21, 38, 42, 48), 27)
    official = Draw(date(2021, 8, 4), (3, 8, 21, 38, 42, 49), 27)

    result = reconcile_historical_draws(
        [old], [official], {}, _authority([old], [official])
    )

    assert len(result.decisions) == 1
    assert result.decisions[0].decision_type == "unresolved_dispute"
    assert result.summary.unresolved == 1
    assert result.provisional_draws == (old,)
    with pytest.raises(ReconciliationIntegrityError, match="unresolved"):
        _ = result.corrected_draws
    assert result.closure_allowed is False


def test_reconciliation_manifest_has_canonical_sha_and_row_bindings():
    row = Draw(date(2020, 1, 1), (1, 2, 3, 4, 5, 6), 7)
    authority = _authority([row], [row])

    result = reconcile_historical_draws([row], [row], {}, authority)
    manifest = result.manifest.to_dict()
    recorded_sha = manifest.pop("manifest_sha256")
    expected_sha = sha256(
        json.dumps(
            manifest,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()

    assert result.manifest_sha256 == recorded_sha == expected_sha
    assert (
        recorded_sha
        == "5d08bd592f73e64a350714d41ee963c597b74c6017873f833eb9638556122f76"
    )
    assert (
        manifest["authority_sha256"]
        == "710d2d1061600b564ff51c6a7fc5a3e390bcaf0c280cf69c9041b8d1bf62d510"
    )
    assert manifest["coverage"]["history_start"] == "2020-01-01"
    assert manifest["coverage"]["history_through"] == "2020-01-01"
    assert (
        manifest["decisions"][0]["old_row_sha256"]
        == "2282bd1a91b64194236a044aa2c666048afc853db5c077118bedcf2ab30a5c3a"
    )
    assert (
        manifest["decisions"][0]["official_row_sha256"]
        == "2282bd1a91b64194236a044aa2c666048afc853db5c077118bedcf2ab30a5c3a"
    )


def test_validate_manifest_round_trips_and_derives_corrected_draws():
    old = Draw(date(2020, 2, 29), (6, 12, 15, 18, 31, 43), 13)
    official = Draw(date(2020, 2, 29), (6, 12, 15, 18, 31, 46), 13)
    evidence = _official_video_evidence(
        "Official result card: 06 12 15 18 31 46 bonus 13",
        supports=(official,),
    )
    archive_evidence = _official_archive_evidence(
        "Official archive row: 06 12 15 18 31 46 bonus 13",
        supports=(official,),
    )
    source_evidence = (archive_evidence, evidence)
    authority = _authority([old], [official], evidence=source_evidence)
    produced = reconcile_historical_draws(
        [old], [official], {official.draw_date: source_evidence}, authority
    )

    validated = validate_reconciliation_manifest(
        produced.manifest.to_dict(),
        [old],
        [official],
        authority,
        produced.manifest_sha256,
    )

    assert validated == produced
    assert validated.corrected_draws == (official,)


def test_reconciliation_result_stores_manifest_as_its_only_authority():
    row = Draw(date(2020, 1, 1), (1, 2, 3, 4, 5, 6), 7)

    result = reconcile_historical_draws([row], [row], {}, _authority([row], [row]))

    assert tuple(
        field.name for field in fields(result) if not field.name.startswith("_")
    ) == ("manifest",)
    assert result.decisions is result.manifest.decisions
    assert result.summary is result.manifest.summary
    assert result.provisional_draws == (row,)
    assert result.closure_allowed is result.manifest.closure_allowed


def test_single_unadjudicated_evidence_cannot_resolve_a_change():
    inserted = Draw(date(2019, 6, 29), (2, 5, 19, 21, 29, 46), 15)
    evidence = _official_archive_evidence(
        "Official row: 2019-06-29 02 05 19 21 29 46 bonus 15",
        supports=(inserted,),
    )

    result = reconcile_historical_draws(
        [],
        [inserted],
        {inserted.draw_date: [evidence]},
        _authority([], [inserted], evidence=(evidence,)),
    )

    assert result.decisions[0].decision_type == "unresolved_dispute"
    assert result.summary.unresolved == 1
    assert result.provisional_draws == ()
    with pytest.raises(ReconciliationIntegrityError, match="unresolved"):
        _ = result.corrected_draws
    assert result.closure_allowed is False


def test_validate_manifest_rejects_direct_canonical_sha_tamper():
    row = Draw(date(2020, 1, 1), (1, 2, 3, 4, 5, 6), 7)
    authority = _authority([row], [row])
    produced = reconcile_historical_draws([row], [row], {}, authority)
    manifest = produced.manifest.to_dict()
    manifest["summary"]["unchanged"] = 0

    with pytest.raises(ReconciliationIntegrityError, match="canonical SHA-256"):
        validate_reconciliation_manifest(
            manifest,
            [row],
            [row],
            authority,
            produced.manifest_sha256,
        )


def test_validate_manifest_rejects_coordinated_decision_and_summary_tamper():
    old = Draw(date(2020, 2, 29), (6, 12, 15, 18, 31, 43), 13)
    official = Draw(date(2020, 2, 29), (6, 12, 15, 18, 31, 46), 13)
    evidence = (
        _official_archive_evidence("Official archive row", supports=(official,)),
        _official_video_evidence("Official video row", supports=(official,)),
    )
    authority = _authority([old], [official], evidence=evidence)
    manifest = reconcile_historical_draws(
        [old], [official], {official.draw_date: evidence}, authority
    ).manifest.to_dict()
    tampered = deepcopy(manifest)
    tampered["decisions"][0]["decision_type"] = "unchanged"
    tampered["summary"]["updated"] = 0
    tampered["summary"]["unchanged"] = 1
    _rehash_manifest(tampered)

    with pytest.raises(ReconciliationIntegrityError, match="independently recomputed"):
        validate_reconciliation_manifest(
            tampered,
            [old],
            [official],
            authority,
            tampered["manifest_sha256"],
        )


def test_manifest_canonicalizes_many_to_many_evidence_row_claims():
    first = Draw(date(2020, 1, 1), (1, 2, 3, 4, 5, 6), 7)
    second = Draw(date(2020, 1, 4), (8, 9, 10, 11, 12, 13), 14)
    evidence = _official_video_evidence(
        "One official video asset supports two result cards",
        supports=(second, first, second),
    )

    result = reconcile_historical_draws(
        [],
        [first, second],
        {first.draw_date: [evidence], second.draw_date: [evidence]},
        _authority([], [first, second], evidence=(evidence,)),
    )

    source_asset = result.manifest.to_dict()["source_assets"][0]
    assert source_asset["supported_row_sha256s"] == sorted(
        {_row_sha256(first), _row_sha256(second)}
    )


def test_conflicting_official_assets_remain_unresolved_until_adjudicated():
    old = Draw(date(2010, 9, 4), (1, 2, 3, 4, 5, 6), 7)
    official = Draw(date(2010, 9, 4), (8, 9, 10, 11, 12, 13), 14)
    conflicting = (
        _official_archive_evidence("Archive supports old row", supports=(old,)),
        _official_video_evidence("Video supports alternate row", supports=(official,)),
    )

    unresolved = reconcile_historical_draws(
        [old],
        [official],
        {official.draw_date: conflicting},
        _authority([old], [official], evidence=conflicting),
    )
    adjudication = _reviewed_adjudication_evidence(
        "Reviewed decision accepts alternate row and rejects old row",
        supports=(official,),
        rejects=(old,),
    )
    resolved = reconcile_historical_draws(
        [old],
        [official],
        {official.draw_date: [*conflicting, adjudication]},
        _authority(
            [old],
            [official],
            evidence=conflicting,
            reviewed_adjudications=(adjudication,),
        ),
    )

    assert unresolved.decisions[0].decision_type == "unresolved_dispute"
    assert unresolved.closure_allowed is False
    assert resolved.decisions[0].decision_type == "update_numbers_or_bonus"
    assert resolved.decisions[0].resolution_policy == "reviewed_adjudication"
    assert resolved.provisional_draws == (official,)
    assert resolved.closure_allowed is True


def test_each_input_row_has_one_decision_and_summary_is_exactly_recomputed():
    unchanged = Draw(date(2020, 1, 1), (1, 2, 3, 4, 5, 6), 7)
    inserted = Draw(date(2020, 1, 4), (8, 9, 10, 11, 12, 13), 14)
    deleted = Draw(date(2020, 1, 8), (15, 16, 17, 18, 19, 20), 21)
    old_update = Draw(date(2020, 1, 11), (22, 23, 24, 25, 26, 27), 28)
    official_update = Draw(date(2020, 1, 11), (22, 23, 24, 25, 26, 29), 28)
    old_unresolved = Draw(date(2020, 1, 15), (30, 31, 32, 33, 34, 35), 36)
    official_unresolved = Draw(date(2020, 1, 15), (30, 31, 32, 33, 34, 37), 36)
    evidence = {
        inserted.draw_date: [
            _official_archive_evidence("Insert archive", supports=(inserted,)),
            _official_video_evidence("Insert video", supports=(inserted,)),
        ],
        deleted.draw_date: [
            _official_archive_evidence("Delete archive", rejects=(deleted,)),
            _official_video_evidence("Delete video", rejects=(deleted,)),
        ],
        official_update.draw_date: [
            _official_archive_evidence("Update archive", supports=(official_update,)),
            _official_video_evidence("Update video", supports=(official_update,)),
        ],
    }
    old_rows = [unchanged, deleted, old_update, old_unresolved]
    official_rows = [
        unchanged,
        inserted,
        official_update,
        official_unresolved,
    ]
    source_evidence = tuple(
        item for references in evidence.values() for item in references
    )

    result = reconcile_historical_draws(
        old_rows,
        official_rows,
        evidence,
        _authority(old_rows, official_rows, evidence=source_evidence),
    )

    assert tuple(decision.draw_date for decision in result.decisions) == (
        date(2020, 1, 1),
        date(2020, 1, 4),
        date(2020, 1, 8),
        date(2020, 1, 11),
        date(2020, 1, 15),
    )
    assert result.summary == ReconciliationSummary(
        old_count=4,
        official_count=4,
        decision_count=5,
        unchanged=1,
        inserted=1,
        deleted=1,
        updated=1,
        unresolved=1,
        corrected_count=4,
    )
    assert result.provisional_draws == (
        unchanged,
        inserted,
        official_update,
        old_unresolved,
    )
    with pytest.raises(ReconciliationIntegrityError, match="unresolved"):
        _ = result.corrected_draws
    assert result.closure_allowed is False


def test_validate_manifest_derives_summary_coverage_and_corrected_rows():
    row = Draw(date(2020, 1, 1), (1, 2, 3, 4, 5, 6), 7)
    authority = _authority([row], [row])
    original = reconcile_historical_draws(
        [row], [row], {}, authority
    ).manifest.to_dict()

    for field, replacement in (
        ("summary", {**original["summary"], "unchanged": 0}),
        ("coverage_gaps", ["unregistered-gap"]),
        ("corrected_rows_sha256", "f" * 64),
    ):
        tampered = deepcopy(original)
        tampered[field] = replacement
        _rehash_manifest(tampered)
        with pytest.raises(
            ReconciliationIntegrityError, match="independently recomputed"
        ):
            validate_reconciliation_manifest(
                tampered,
                [row],
                [row],
                authority,
                tampered["manifest_sha256"],
            )


def test_validate_manifest_rejects_source_asset_hash_tamper():
    official = Draw(date(2020, 1, 4), (8, 9, 10, 11, 12, 13), 14)
    evidence = (
        _official_archive_evidence("Archive row", supports=(official,)),
        _official_video_evidence("Video row", supports=(official,)),
    )
    authority = _authority([], [official], evidence=evidence)
    manifest = reconcile_historical_draws(
        [], [official], {official.draw_date: evidence}, authority
    ).manifest.to_dict()
    manifest["source_assets"][0]["frame_summary"] = "tampered summary"
    _rehash_manifest(manifest)

    with pytest.raises(ReconciliationIntegrityError, match="evidence SHA-256"):
        validate_reconciliation_manifest(
            manifest,
            [],
            [official],
            authority,
            manifest["manifest_sha256"],
        )


def test_validate_manifest_wraps_malformed_source_asset_fields():
    official = Draw(date(2020, 1, 4), (8, 9, 10, 11, 12, 13), 14)
    evidence = (
        _official_archive_evidence("Archive row", supports=(official,)),
        _official_video_evidence("Video row", supports=(official,)),
    )
    authority = _authority([], [official], evidence=evidence)
    manifest = reconcile_historical_draws(
        [], [official], {official.draw_date: evidence}, authority
    ).manifest.to_dict()
    manifest["source_assets"][0]["download_sha256"] = "not-a-sha"
    _rehash_manifest(manifest)

    with pytest.raises(ReconciliationIntegrityError, match="Malformed manifest"):
        validate_reconciliation_manifest(
            manifest,
            [],
            [official],
            authority,
            manifest["manifest_sha256"],
        )


def test_reconciliation_result_and_nested_records_are_immutable():
    row = Draw(date(2020, 1, 1), (1, 2, 3, 4, 5, 6), 7)
    result = reconcile_historical_draws([row], [row], {}, _authority([row], [row]))

    with pytest.raises(FrozenInstanceError):
        result.closure_allowed = False
    with pytest.raises(FrozenInstanceError):
        result.summary.unchanged = 0
    with pytest.raises(FrozenInstanceError):
        result.manifest.manifest_sha256 = "0" * 64


def test_reconcile_rejects_evidence_not_bound_to_an_input_row():
    row = Draw(date(2020, 1, 1), (1, 2, 3, 4, 5, 6), 7)
    orphan_date = date(2020, 1, 4)
    evidence = _official_archive_evidence("Orphan evidence", supports=(row,))

    with pytest.raises(ValueError, match="no old or official row"):
        reconcile_historical_draws(
            [row],
            [row],
            {orphan_date: [evidence]},
            _authority([row], [row], evidence=(evidence,)),
        )


def test_two_frames_from_one_download_are_not_independent_assets():
    inserted = Draw(date(2020, 1, 4), (8, 9, 10, 11, 12, 13), 14)
    first_frame = _official_video_evidence("First frame", supports=(inserted,))
    second_frame = {
        **_official_video_evidence("Second frame", supports=(inserted,)),
        "frame_sha256": "5" * 64,
    }

    result = reconcile_historical_draws(
        [],
        [inserted],
        {inserted.draw_date: [first_frame, second_frame]},
        _authority([], [inserted], evidence=(first_frame, second_frame)),
    )

    assert result.decisions[0].decision_type == "unresolved_dispute"
    assert result.closure_allowed is False


def test_same_download_relabelled_as_another_source_is_not_independent():
    inserted = Draw(date(2020, 1, 4), (8, 9, 10, 11, 12, 13), 14)
    first = _official_video_evidence("Original source", supports=(inserted,))
    relabelled = {
        **_official_video_evidence("Relabelled source", supports=(inserted,)),
        "provider": "Another official label",
        "source_type": "official_results_archive",
        "frame_sha256": None,
    }

    result = reconcile_historical_draws(
        [],
        [inserted],
        {inserted.draw_date: [first, relabelled]},
        _authority([], [inserted], evidence=(first, relabelled)),
    )

    assert result.decisions[0].decision_type == "unresolved_dispute"
    assert result.closure_allowed is False


def test_two_downloads_from_one_source_identity_are_not_independent_by_default():
    inserted = Draw(date(2020, 1, 4), (8, 9, 10, 11, 12, 13), 14)
    first = _official_archive_evidence("First archive copy", supports=(inserted,))
    second = {
        **_official_archive_evidence("Second archive copy", supports=(inserted,)),
        "download_sha256": "6" * 64,
    }
    evidence = (first, second)

    result = reconcile_historical_draws(
        [],
        [inserted],
        {inserted.draw_date: evidence},
        _authority([], [inserted], evidence=evidence),
    )

    assert result.decisions[0].decision_type == "unresolved_dispute"
    assert result.closure_allowed is False
