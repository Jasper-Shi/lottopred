from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import pytest

from lotto649.historical_oos_evidence import (
    HistoricalOOSEvidenceError,
    import_legacy_historical_artifact,
    validate_historical_oos_evidence,
)


DETAIL_BYTES = (
    b"target_draw_date,model_name,model_version,actual,bonus,final_6_hits,"
    b"top_6_hits,top_12_hits,top_18_hits,matched_final,brier_score,log_loss,"
    b"mean_actual_rank\n"
    b'2020-06-13,v4_ensemble,v1.0.0,"[3, 31, 34, 38, 45, 48]",12,4,4,'
    b'6,6,"[3, 31, 34, 45]",0.1,0.2,4.5\n'
    b'2021-10-06,v4_ensemble,v1.0.0,"[7, 18, 19, 38, 42, 46]",31,2,2,'
    b'6,6,"[19, 38]",0.1,0.2,7.5\n'
)
SUMMARY_BYTES = b"model_name,draws\nv4_ensemble,2\n"
ROOT = Path(__file__).resolve().parents[1]
V10_LEDGER_PATH = "reports/v10_adjacent_pair_structure_v10.0.0_historical.ledger.jsonl"
V10_REPORT_PATH = "reports/v10_adjacent_pair_structure_v10.0.0_historical.json"
V10_LEDGER_SHA256 = "774434e8cd34664f4546a7874f043dbf752e9aaf579ef9d020639cf2d8c4d3c9"
V10_REPORT_SHA256 = "26fe097bad44c6563a1c4d659a42b0bbdbdc7e3414bc62e37a3ec5108edd49c6"
CATALOG_MANIFEST_PATH = "evidence/historical/actions/31888527837/manifest.json"


def _manifest() -> dict:
    return {
        "schema_version": 1,
        "source_id": "github-actions-31888527837",
        "github_actions": {
            "run_id": 31888527837,
            "job_id": 95021219682,
            "artifact_id": 9247962892,
            "artifact_name": "v2-v4-research-reports",
            "head_sha": "2310713e3f6fc6ae61a165874c049ac3cb69dffb",
            "archive_sha256": (
                "2e9a7d6ecd163fd64bd87354f5cf8e5776723ffaad572e1740d9cb6bea62cd50"
            ),
        },
        "sources": {
            "legacy_detail": {
                "path": "detail.csv",
                "sha256": sha256(DETAIL_BYTES).hexdigest(),
            },
            "legacy_summary": {
                "path": "summary.csv",
                "sha256": sha256(SUMMARY_BYTES).hexdigest(),
            },
        },
        "evidence_gaps": [
            "legacy_final6_values_missing",
            "legacy_top12_values_missing",
            "legacy_per_target_prefix_hash_missing",
            "legacy_pre_reveal_persistence_not_proven",
        ],
        "coverage_gaps": [],
    }


def _repository_catalog_sources(manifest: dict) -> dict[str, bytes]:
    source_paths: set[str] = set()
    for bundle in manifest["legacy_bundles"]:
        source_paths.update(
            (bundle["archive_path"], bundle["detail_path"], bundle["summary_path"])
        )
    for gap in manifest["coverage_gaps"]:
        source_paths.add(gap["source_path"])
    for source in manifest["verified_snapshot_sources"]:
        source_paths.update((source["ledger_path"], source["report_path"]))
    return {path: (ROOT / path).read_bytes() for path in source_paths}


def _manifest_with_v10() -> dict:
    manifest = _manifest()
    manifest["verified_snapshot_sources"] = [
        {
            "expected_target_count": 621,
            "experiment_id": "V10_adjacent_pair_structure",
            "ledger_path": V10_LEDGER_PATH,
            "ledger_sha256": V10_LEDGER_SHA256,
            "model_name": "v10_adjacent_pair_structure",
            "model_version": "v10.0.0",
            "report_path": V10_REPORT_PATH,
            "report_sha256": V10_REPORT_SHA256,
        }
    ]
    return manifest


def _v10_sources(*, ledger_bytes: bytes | None = None) -> dict[str, bytes]:
    return {
        "detail.csv": DETAIL_BYTES,
        "summary.csv": SUMMARY_BYTES,
        V10_LEDGER_PATH: (
            (ROOT / V10_LEDGER_PATH).read_bytes()
            if ledger_bytes is None
            else ledger_bytes
        ),
        V10_REPORT_PATH: (ROOT / V10_REPORT_PATH).read_bytes(),
    }


def _coordinated_tampered_v10_report() -> bytes:
    report = json.loads((ROOT / V10_REPORT_PATH).read_bytes())
    score = report["per_target"][0]["scores"]["v10_adjacent_pair_structure"]
    score["top12_hits"] += 1
    return json.dumps(
        report,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode()


def _canonical_test_source_ledger(
    event_specs: list[tuple[str, dict]],
) -> bytes:
    previous_hash = "0" * 64
    lines: list[bytes] = []
    for sequence, (event_type, payload) in enumerate(event_specs):
        event_without_hash = {
            "event_type": event_type,
            "payload": payload,
            "previous_event_sha256": previous_hash,
            "sequence": sequence,
        }
        event_hash = sha256(
            json.dumps(
                event_without_hash,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            ).encode()
            + previous_hash.encode("ascii")
        ).hexdigest()
        event = {**event_without_hash, "event_sha256": event_hash}
        lines.append(
            json.dumps(
                event,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            ).encode()
            + b"\n"
        )
        previous_hash = event_hash
    return b"".join(lines)


def _synthetic_verified_six_sources(
    audit_mode: str,
    *,
    preflight_clear: bool = True,
) -> tuple[dict, dict[str, bytes]]:
    target_date = "2020-01-01"
    model_name = "synthetic_candidate"
    model_version = "synthetic-v1"
    final6 = [1, 2, 3, 4, 5, 6]
    preflight = {
        "audit_warnings": ([] if preflight_clear else ["synthetic preflight failure"]),
        "chronology": {
            "2026_scored_targets": 0,
            "bonus_excluded_from_model_and_scores": True,
            "complete_expanding_prefix": True,
            "target_dates_strictly_increasing_unique": True,
        },
        "passed": preflight_clear,
    }
    forecast = {
        "final6": final6,
        "history_draws": 100,
        "history_through": "2019-12-28",
        "model_name": model_name,
        "model_version": model_version,
        "probabilities": {str(number): 6.0 / 49.0 for number in range(1, 50)},
        "ranking": list(range(1, 50)),
        "target_date": target_date,
        "top6": final6,
        "top12": list(range(1, 13)),
        "top18": list(range(1, 19)),
    }
    forecast_payload = {
        "forecasts": {model_name: forecast},
        "prefix": {
            "history_draws": 100,
            "history_through": "2019-12-28",
            "strict_prefix_sha256": "a" * 64,
        },
        "target_date": target_date,
    }
    forecast_sha = sha256(
        json.dumps(
            forecast_payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode()
    ).hexdigest()
    score = {
        "actual": final6,
        "final6_hits": 6,
        "matched_final": final6,
        "model_name": model_name,
        "model_version": model_version,
        "target_date": target_date,
        "top6_hits": 6,
        "top12_hits": 6,
        "top18_hits": 6,
    }
    progressive_record = {"current_final6_hits": 6, "target_date": target_date}
    reveal_payload = {
        "actual_main": final6,
        "forecast_sha256": forecast_sha,
        "progressive_record": progressive_record,
        "scores": {model_name: score},
        "target_date": target_date,
    }
    per_target = {
        "actual_main": final6,
        "forecast_payload": forecast_payload,
        "forecast_sha256": forecast_sha,
        "progressive_record": progressive_record,
        "scores": {model_name: score},
        "target_date": target_date,
    }
    event_specs = [
        ("preflight_passed", preflight),
        (
            "prediction_frozen",
            {
                "forecast_payload": forecast_payload,
                "forecast_sha256": forecast_sha,
                "target_date": target_date,
            },
        ),
        ("target_revealed_scored", reveal_payload),
    ]
    if audit_mode != "missing":
        required_checks = [
            "chronology",
            "target_exclusion",
            "future_exclusion",
            "preprocessing",
            "feature_selection",
            "model_selection",
            "source_integrity",
            "git_runtime_integrity",
            "forecast_replay",
            "prefix_identity",
        ]
        clear = audit_mode == "clear"
        audit = {
            "callback_error": None,
            "checks": [
                {
                    "evidence": {"synthetic": name},
                    "name": name,
                    "passed": clear,
                }
                for name in required_checks
            ],
            "clear": clear,
            "declared_clear_ignored": None,
            "required_check_names": required_checks,
            "schema_errors": [] if clear else ["synthetic audit failure"],
        }
        event_specs.extend(
            [
                (
                    "historical_6of6_candidate_detected",
                    {
                        "forecast_sha256": forecast_sha,
                        "model_name": model_name,
                        "model_version": model_version,
                        "status": "historical-6of6-candidate",
                        "target_date": target_date,
                    },
                ),
                (
                    "historical_6of6_leakage_audit_completed",
                    {"audit": audit, "target_date": target_date},
                ),
                (
                    (
                        "historical_6of6_candidate_published"
                        if clear
                        else "historical_6of6_candidate_archived_leakage_failed"
                    ),
                    {"target_date": target_date},
                ),
            ]
        )
    ledger_bytes = _canonical_test_source_ledger(event_specs)
    report = {
        "audit_warnings": preflight["audit_warnings"],
        "experiment_id": "synthetic_verified_six",
        "model_name": model_name,
        "model_version": model_version,
        "per_target": [per_target],
        "preflight": preflight,
    }
    report_bytes = json.dumps(
        report,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode()
    manifest = _manifest()
    manifest["verified_snapshot_sources"] = [
        {
            "expected_target_count": 1,
            "experiment_id": "synthetic_verified_six",
            "ledger_path": "synthetic-six.ledger.jsonl",
            "ledger_sha256": sha256(ledger_bytes).hexdigest(),
            "model_name": model_name,
            "model_version": model_version,
            "report_path": "synthetic-six.report.json",
            "report_sha256": sha256(report_bytes).hexdigest(),
        }
    ]
    sources = {
        "detail.csv": DETAIL_BYTES,
        "summary.csv": SUMMARY_BYTES,
        "synthetic-six.ledger.jsonl": ledger_bytes,
        "synthetic-six.report.json": report_bytes,
    }
    return manifest, sources


def _rechain_tampered_v10_source(mutation: str) -> bytes:
    events = [
        json.loads(line) for line in (ROOT / V10_LEDGER_PATH).read_text().splitlines()
    ]
    mutated = False
    replacement_forecast_hash: str | None = None
    tampered_target_date: str | None = None
    if mutation == "reveal_before_freeze":
        freeze_index = next(
            index
            for index, event in enumerate(events)
            if event["event_type"] == "prediction_frozen"
        )
        target_date = events[freeze_index]["payload"]["target_date"]
        reveal_index = next(
            index
            for index, event in enumerate(events)
            if event["event_type"] == "target_revealed_scored"
            and event["payload"]["target_date"] == target_date
        )
        reveal = events.pop(reveal_index)
        events.insert(freeze_index, reveal)
        mutated = True
    elif mutation == "target_pairs_out_of_date_order":
        first_freeze = next(
            index
            for index, event in enumerate(events)
            if event["event_type"] == "prediction_frozen"
        )
        first_pair = events[first_freeze : first_freeze + 2]
        second_pair = events[first_freeze + 2 : first_freeze + 4]
        assert [event["event_type"] for event in first_pair] == [
            "prediction_frozen",
            "target_revealed_scored",
        ]
        assert [event["event_type"] for event in second_pair] == [
            "prediction_frozen",
            "target_revealed_scored",
        ]
        events[first_freeze : first_freeze + 4] = second_pair + first_pair
        mutated = True
    elif mutation == "next_freeze_before_prior_reveal":
        first_freeze = next(
            index
            for index, event in enumerate(events)
            if event["event_type"] == "prediction_frozen"
        )
        freeze_a, reveal_a, freeze_b, reveal_b = events[first_freeze : first_freeze + 4]
        assert [
            freeze_a["event_type"],
            reveal_a["event_type"],
            freeze_b["event_type"],
            reveal_b["event_type"],
        ] == [
            "prediction_frozen",
            "target_revealed_scored",
            "prediction_frozen",
            "target_revealed_scored",
        ]
        events[first_freeze : first_freeze + 4] = [
            freeze_a,
            freeze_b,
            reveal_a,
            reveal_b,
        ]
        mutated = True
    for event in events:
        if mutated:
            break
        if mutation in {
            "final6_hits",
            "top6_hits",
            "top12_hits",
            "top18_hits",
            "matched_final",
        }:
            if event["event_type"] != "target_revealed_scored":
                continue
            score = event["payload"]["scores"]["v10_adjacent_pair_structure"]
            if score["final6_hits"] >= 5 or score["top12_hits"] >= 5:
                continue
            if mutation == "matched_final":
                score["matched_final"] = (
                    [] if score["matched_final"] else [score["actual"][0]]
                )
            else:
                score[mutation] += 1
        elif mutation == "actual_duplicate":
            if event["event_type"] != "target_revealed_scored":
                continue
            score = event["payload"]["scores"]["v10_adjacent_pair_structure"]
            score["actual"][1] = score["actual"][0]
        else:
            if event["event_type"] != "prediction_frozen":
                continue
            if (
                mutation
                in {"prefix_skips_previous_target", "prefix_history_draws_jumps"}
                and event["payload"]["target_date"] == "2020-01-01"
            ):
                continue
            forecast_payload = event["payload"]["forecast_payload"]
            forecast = forecast_payload["forecasts"]["v10_adjacent_pair_structure"]
            if mutation == "duplicate_final6":
                forecast["final6"][1] = forecast["final6"][0]
            elif mutation == "final6_not_sorted_top6":
                forecast["final6"] = list(reversed(forecast["final6"]))
            elif mutation == "top6_not_ranking_prefix":
                forecast["top6"] = list(reversed(forecast["top6"]))
            elif mutation == "top12_not_ranking_prefix":
                forecast["top12"] = list(reversed(forecast["top12"]))
            elif mutation == "top18_not_ranking_prefix":
                forecast["top18"] = list(reversed(forecast["top18"]))
            elif mutation == "ranking_duplicate":
                forecast["ranking"][1] = forecast["ranking"][0]
            elif mutation == "top18_out_of_range":
                forecast["top18"][0] = 50
            elif mutation == "probability_ranking_mismatch":
                first = str(forecast["ranking"][0])
                last = str(forecast["ranking"][-1])
                probabilities = forecast["probabilities"]
                probabilities[first], probabilities[last] = (
                    probabilities[last],
                    probabilities[first],
                )
            elif mutation == "prefix_history_not_before_target":
                forecast_payload["prefix"]["history_through"] = event["payload"][
                    "target_date"
                ]
            elif mutation == "prefix_history_draws_missing":
                forecast_payload["prefix"].pop("history_draws")
            elif mutation == "prefix_forecast_history_mismatch":
                forecast_payload["prefix"]["history_draws"] -= 1
            elif mutation == "prefix_skips_previous_target":
                forecast_payload["prefix"]["history_through"] = "2020-01-02"
                forecast["history_through"] = "2020-01-02"
            elif mutation == "prefix_history_draws_jumps":
                forecast_payload["prefix"]["history_draws"] += 1
                forecast["history_draws"] += 1
            else:
                raise AssertionError(f"unsupported test mutation: {mutation}")
            replacement_forecast_hash = sha256(
                json.dumps(
                    forecast_payload,
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                    allow_nan=False,
                ).encode()
            ).hexdigest()
            event["payload"]["forecast_sha256"] = replacement_forecast_hash
            tampered_target_date = event["payload"]["target_date"]
        mutated = True
        break
    assert mutated

    if replacement_forecast_hash is not None:
        for event in events:
            if (
                event["event_type"] == "target_revealed_scored"
                and event["payload"]["target_date"] == tampered_target_date
            ):
                event["payload"]["forecast_sha256"] = replacement_forecast_hash
                break
        else:
            raise AssertionError("test source has no reveal for tampered forecast")

    previous_hash = "0" * 64
    canonical_lines: list[bytes] = []
    for sequence, event in enumerate(events):
        event["sequence"] = sequence
        event["previous_event_sha256"] = previous_hash
        event_without_hash = dict(event)
        event_without_hash.pop("event_sha256", None)
        canonical_without_hash = json.dumps(
            event_without_hash,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode()
        event_hash = sha256(
            canonical_without_hash + previous_hash.encode("ascii")
        ).hexdigest()
        event["event_sha256"] = event_hash
        canonical_lines.append(
            json.dumps(
                event,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            ).encode()
            + b"\n"
        )
        previous_hash = event_hash
    return b"".join(canonical_lines)


def test_import_copies_legacy_hit_counts_without_turning_top12_into_success(
    tmp_path: Path,
) -> None:
    ledger_path = tmp_path / "global_opportunities.jsonl"

    result = import_legacy_historical_artifact(
        source_bytes={"detail.csv": DETAIL_BYTES, "summary.csv": SUMMARY_BYTES},
        manifest=_manifest(),
        ledger_path=ledger_path,
    )

    assert result == {
        "event_count": 3,
        "global_final6_max": None,
        "global_final6_max_status": "unknown_due_to_incomplete_coverage",
        "ledger_sha256": result["ledger_sha256"],
        "reported_final6_max": 4,
        "verified_full_snapshot_final6_max": None,
    }
    events = [json.loads(line) for line in ledger_path.read_text().splitlines()]
    first_opportunity = events[1]["payload"]
    assert first_opportunity["reported_evaluation"] == {
        "final6_hits": 4,
        "matched_final": [3, 31, 34, 45],
        "score_origin": "copied_not_recomputed",
        "top12_hits": 6,
        "top18_hits": 6,
        "top6_hits": 4,
    }
    assert first_opportunity["forecast"] == {
        "final6": None,
        "forecast_sha256": None,
        "snapshot_status": "missing_from_source",
        "top12": None,
        "top18": None,
        "top6": None,
    }
    assert first_opportunity["classification"] == {
        "exact_final6_status": "reported_false",
        "stop_global_search": False,
        "success_class": "top12_coverage_only",
        "top12_all_main_status": "reported_true",
    }


def test_validate_accepts_canonical_source_bound_hash_chain(tmp_path: Path) -> None:
    ledger_path = tmp_path / "global_opportunities.jsonl"
    manifest = _manifest()
    sources = {"detail.csv": DETAIL_BYTES, "summary.csv": SUMMARY_BYTES}
    import_legacy_historical_artifact(
        source_bytes=sources,
        manifest=manifest,
        ledger_path=ledger_path,
    )

    result = validate_historical_oos_evidence(
        source_bytes=sources,
        manifest=manifest,
        ledger_path=ledger_path,
    )

    assert result == {
        "event_count": 3,
        "global_final6_max": None,
        "global_final6_max_status": "unknown_due_to_incomplete_coverage",
        "ledger_sha256": result["ledger_sha256"],
        "reported_final6_max": 4,
        "verified_full_snapshot_final6_max": None,
    }


def test_import_rejects_duplicate_model_target_opportunities(tmp_path: Path) -> None:
    header, first_row, _second_row = DETAIL_BYTES.splitlines(keepends=True)
    duplicate_detail = header + first_row + first_row
    manifest = _manifest()
    manifest["sources"]["legacy_detail"]["sha256"] = sha256(
        duplicate_detail
    ).hexdigest()

    with pytest.raises(HistoricalOOSEvidenceError, match="duplicate opportunity"):
        import_legacy_historical_artifact(
            source_bytes={
                "detail.csv": duplicate_detail,
                "summary.csv": SUMMARY_BYTES,
            },
            manifest=manifest,
            ledger_path=tmp_path / "global_opportunities.jsonl",
        )


def test_import_is_idempotent_but_never_rewrites_existing_ledger(
    tmp_path: Path,
) -> None:
    ledger_path = tmp_path / "global_opportunities.jsonl"
    manifest = _manifest()
    sources = {"detail.csv": DETAIL_BYTES, "summary.csv": SUMMARY_BYTES}
    first = import_legacy_historical_artifact(
        source_bytes=sources,
        manifest=manifest,
        ledger_path=ledger_path,
    )
    original_bytes = ledger_path.read_bytes()

    second = import_legacy_historical_artifact(
        source_bytes=sources,
        manifest=manifest,
        ledger_path=ledger_path,
    )

    assert second == first
    assert ledger_path.read_bytes() == original_bytes


def test_import_preserves_aggregate_only_attempt_as_an_explicit_coverage_gap(
    tmp_path: Path,
) -> None:
    report_bytes = b'{"model_name":"v5_pair_affinity","model_version":"v5.0.0"}\n'
    manifest = _manifest()
    manifest["coverage_gaps"] = [
        {
            "date_end": "2025-12-31",
            "date_start": "2020-01-01",
            "evidence_lane": "consumed_historical_diagnostic",
            "experiment_id": "V5_pair_affinity",
            "model_name": "v5_pair_affinity",
            "model_version": "v5.0.0",
            "reason": "aggregate_report_only",
            "reported_target_count": 621,
            "source_path": "v5-report.json",
            "source_sha256": sha256(report_bytes).hexdigest(),
        }
    ]
    sources = {
        "detail.csv": DETAIL_BYTES,
        "summary.csv": SUMMARY_BYTES,
        "v5-report.json": report_bytes,
    }

    result = import_legacy_historical_artifact(
        source_bytes=sources,
        manifest=manifest,
        ledger_path=tmp_path / "global_opportunities.jsonl",
    )

    assert result["event_count"] == 4
    events = [
        json.loads(line)
        for line in (tmp_path / "global_opportunities.jsonl").read_text().splitlines()
    ]
    assert events[-1]["event_type"] == "coverage_gap"
    assert events[-1]["payload"] == {
        "date_end": "2025-12-31",
        "date_start": "2020-01-01",
        "evidence_lane": "consumed_historical_diagnostic",
        "experiment_id": "V5_pair_affinity",
        "maximum_final6_hits": None,
        "model_name": "v5_pair_affinity",
        "model_version": "v5.0.0",
        "per_target_final6": "unknown",
        "per_target_top12": "unknown",
        "reason": "aggregate_report_only",
        "reported_target_count": 621,
        "source_path": "v5-report.json",
        "source_sha256": sha256(report_bytes).hexdigest(),
    }


def test_import_copies_v10_frozen_snapshots_without_rerunning_predictions(
    tmp_path: Path,
) -> None:
    v10_ledger = (ROOT / V10_LEDGER_PATH).read_bytes()
    v10_report = (ROOT / V10_REPORT_PATH).read_bytes()
    manifest = _manifest()
    manifest["verified_snapshot_sources"] = [
        {
            "expected_target_count": 621,
            "experiment_id": "V10_adjacent_pair_structure",
            "ledger_path": V10_LEDGER_PATH,
            "ledger_sha256": (
                "774434e8cd34664f4546a7874f043dbf752e9aaf579ef9d020639cf2d8c4d3c9"
            ),
            "model_name": "v10_adjacent_pair_structure",
            "model_version": "v10.0.0",
            "report_path": V10_REPORT_PATH,
            "report_sha256": (
                "26fe097bad44c6563a1c4d659a42b0bbdbdc7e3414bc62e37a3ec5108edd49c6"
            ),
        }
    ]
    sources = {
        "detail.csv": DETAIL_BYTES,
        "summary.csv": SUMMARY_BYTES,
        V10_LEDGER_PATH: v10_ledger,
        V10_REPORT_PATH: v10_report,
    }

    result = import_legacy_historical_artifact(
        source_bytes=sources,
        manifest=manifest,
        ledger_path=tmp_path / "global_opportunities.jsonl",
    )

    assert result == {
        "event_count": 624,
        "global_final6_max": None,
        "global_final6_max_status": "unknown_due_to_incomplete_coverage",
        "ledger_sha256": result["ledger_sha256"],
        "reported_final6_max": 4,
        "verified_full_snapshot_final6_max": 3,
    }
    events = [
        json.loads(line)
        for line in (tmp_path / "global_opportunities.jsonl").read_text().splitlines()
    ]
    assert events[-1]["payload"]["reported_evaluation"]["score_origin"] == (
        "independently_recomputed_and_matched"
    )


def test_import_catalogs_exact_duplicate_artifact_without_counting_new_opportunities(
    tmp_path: Path,
) -> None:
    manifest = _manifest()
    manifest["legacy_bundles"] = [
        {
            "archive_path": "artifact-a.zip",
            "archive_sha256": sha256(b"zip-a").hexdigest(),
            "artifact_id": 1,
            "artifact_name": "reports",
            "bundle_id": "artifact-1",
            "chronology": "implementation_strict_prefix",
            "detail_path": "detail.csv",
            "detail_sha256": sha256(DETAIL_BYTES).hexdigest(),
            "exact_duplicate_of": None,
            "head_sha": "a" * 40,
            "job_id": 11,
            "pre_reveal_persistence": "not_proven",
            "run_id": 111,
            "summary_path": "summary.csv",
            "summary_sha256": sha256(SUMMARY_BYTES).hexdigest(),
        },
        {
            "archive_path": "artifact-b.zip",
            "archive_sha256": sha256(b"zip-b").hexdigest(),
            "artifact_id": 2,
            "artifact_name": "reports",
            "bundle_id": "artifact-2",
            "chronology": "implementation_strict_prefix",
            "detail_path": "detail.csv",
            "detail_sha256": sha256(DETAIL_BYTES).hexdigest(),
            "exact_duplicate_of": "artifact-1",
            "head_sha": "b" * 40,
            "job_id": 22,
            "pre_reveal_persistence": "not_proven",
            "run_id": 222,
            "summary_path": "summary.csv",
            "summary_sha256": sha256(SUMMARY_BYTES).hexdigest(),
        },
    ]
    sources = {
        "artifact-a.zip": b"zip-a",
        "artifact-b.zip": b"zip-b",
        "detail.csv": DETAIL_BYTES,
        "summary.csv": SUMMARY_BYTES,
    }

    result = import_legacy_historical_artifact(
        source_bytes=sources,
        manifest=manifest,
        ledger_path=tmp_path / "global_opportunities.jsonl",
    )

    assert result["event_count"] == 4
    events = [
        json.loads(line)
        for line in (tmp_path / "global_opportunities.jsonl").read_text().splitlines()
    ]
    assert [event["event_type"] for event in events] == [
        "source_registered",
        "opportunity",
        "opportunity",
        "duplicate_stream",
    ]
    assert events[-1]["payload"] == {
        "bundle_id": "artifact-2",
        "detail_sha256": sha256(DETAIL_BYTES).hexdigest(),
        "exact_duplicate_of": "artifact-1",
        "opportunities_added": 0,
    }


def test_validate_rejects_tampered_verified_snapshot_source(tmp_path: Path) -> None:
    v10_ledger = (ROOT / V10_LEDGER_PATH).read_bytes()
    v10_report = (ROOT / V10_REPORT_PATH).read_bytes()
    manifest = _manifest()
    manifest["verified_snapshot_sources"] = [
        {
            "expected_target_count": 621,
            "experiment_id": "V10_adjacent_pair_structure",
            "ledger_path": V10_LEDGER_PATH,
            "ledger_sha256": (
                "774434e8cd34664f4546a7874f043dbf752e9aaf579ef9d020639cf2d8c4d3c9"
            ),
            "model_name": "v10_adjacent_pair_structure",
            "model_version": "v10.0.0",
            "report_path": V10_REPORT_PATH,
            "report_sha256": (
                "26fe097bad44c6563a1c4d659a42b0bbdbdc7e3414bc62e37a3ec5108edd49c6"
            ),
        }
    ]
    sources = {
        "detail.csv": DETAIL_BYTES,
        "summary.csv": SUMMARY_BYTES,
        V10_LEDGER_PATH: v10_ledger,
        V10_REPORT_PATH: v10_report,
    }
    ledger_path = tmp_path / "global_opportunities.jsonl"
    import_legacy_historical_artifact(
        source_bytes=sources,
        manifest=manifest,
        ledger_path=ledger_path,
    )

    with pytest.raises(
        HistoricalOOSEvidenceError,
        match="verified snapshot report SHA-256 mismatch",
    ):
        validate_historical_oos_evidence(
            source_bytes={**sources, V10_REPORT_PATH: v10_report + b"tampered"},
            manifest=manifest,
            ledger_path=ledger_path,
        )


def test_import_rejects_coordinated_report_per_target_tamper(tmp_path: Path) -> None:
    tampered_report = _coordinated_tampered_v10_report()
    manifest = _manifest_with_v10()
    manifest["verified_snapshot_sources"][0]["report_sha256"] = sha256(
        tampered_report
    ).hexdigest()
    sources = _v10_sources()
    sources[V10_REPORT_PATH] = tampered_report

    with pytest.raises(HistoricalOOSEvidenceError, match="report per-target"):
        import_legacy_historical_artifact(
            source_bytes=sources,
            manifest=manifest,
            ledger_path=tmp_path / "global_opportunities.jsonl",
        )


@pytest.mark.parametrize(
    "mutation",
    [
        "final6_hits",
        "top6_hits",
        "top12_hits",
        "top18_hits",
        "matched_final",
    ],
)
def test_import_rejects_coordinated_score_tamper_after_source_rechain(
    tmp_path: Path,
    mutation: str,
) -> None:
    tampered_ledger = _rechain_tampered_v10_source(mutation)
    manifest = _manifest_with_v10()
    manifest["verified_snapshot_sources"][0]["ledger_sha256"] = sha256(
        tampered_ledger
    ).hexdigest()

    with pytest.raises(HistoricalOOSEvidenceError, match="copied score mismatch"):
        import_legacy_historical_artifact(
            source_bytes=_v10_sources(ledger_bytes=tampered_ledger),
            manifest=manifest,
            ledger_path=tmp_path / "global_opportunities.jsonl",
        )


@pytest.mark.parametrize(
    "mutation",
    [
        "duplicate_final6",
        "final6_not_sorted_top6",
        "top6_not_ranking_prefix",
        "top12_not_ranking_prefix",
        "top18_not_ranking_prefix",
        "ranking_duplicate",
        "top18_out_of_range",
        "probability_ranking_mismatch",
        "actual_duplicate",
    ],
)
def test_import_rejects_malformed_verified_snapshot_after_source_rechain(
    tmp_path: Path,
    mutation: str,
) -> None:
    tampered_ledger = _rechain_tampered_v10_source(mutation)
    manifest = _manifest_with_v10()
    manifest["verified_snapshot_sources"][0]["ledger_sha256"] = sha256(
        tampered_ledger
    ).hexdigest()

    with pytest.raises(HistoricalOOSEvidenceError, match="verified snapshot"):
        import_legacy_historical_artifact(
            source_bytes=_v10_sources(ledger_bytes=tampered_ledger),
            manifest=manifest,
            ledger_path=tmp_path / "global_opportunities.jsonl",
        )


@pytest.mark.parametrize(
    "mutation",
    [
        "reveal_before_freeze",
        "target_pairs_out_of_date_order",
        "next_freeze_before_prior_reveal",
    ],
)
def test_import_rejects_reordered_freeze_and_reveal_events_after_rechain(
    tmp_path: Path,
    mutation: str,
) -> None:
    tampered_ledger = _rechain_tampered_v10_source(mutation)
    manifest = _manifest_with_v10()
    manifest["verified_snapshot_sources"][0]["ledger_sha256"] = sha256(
        tampered_ledger
    ).hexdigest()

    with pytest.raises(HistoricalOOSEvidenceError, match="target|frozen|order"):
        import_legacy_historical_artifact(
            source_bytes=_v10_sources(ledger_bytes=tampered_ledger),
            manifest=manifest,
            ledger_path=tmp_path / "global_opportunities.jsonl",
        )


@pytest.mark.parametrize(
    "mutation",
    [
        "prefix_history_not_before_target",
        "prefix_history_draws_missing",
        "prefix_forecast_history_mismatch",
        "prefix_skips_previous_target",
        "prefix_history_draws_jumps",
    ],
)
def test_import_rejects_invalid_prefix_history_metadata_after_rechain(
    tmp_path: Path,
    mutation: str,
) -> None:
    tampered_ledger = _rechain_tampered_v10_source(mutation)
    manifest = _manifest_with_v10()
    manifest["verified_snapshot_sources"][0]["ledger_sha256"] = sha256(
        tampered_ledger
    ).hexdigest()

    with pytest.raises(HistoricalOOSEvidenceError, match="prefix|history"):
        import_legacy_historical_artifact(
            source_bytes=_v10_sources(ledger_bytes=tampered_ledger),
            manifest=manifest,
            ledger_path=tmp_path / "global_opportunities.jsonl",
        )


@pytest.mark.parametrize(
    "audit_mode,expected_stop",
    [("missing", False), ("failed", False), ("clear", True)],
)
def test_verified_six_stops_only_with_clear_runner_and_leakage_audits(
    tmp_path: Path,
    audit_mode: str,
    expected_stop: bool,
) -> None:
    manifest, sources = _synthetic_verified_six_sources(audit_mode)
    ledger_path = tmp_path / "global_opportunities.jsonl"

    import_legacy_historical_artifact(
        source_bytes=sources,
        manifest=manifest,
        ledger_path=ledger_path,
    )

    verified = json.loads(ledger_path.read_text().splitlines()[-1])["payload"]
    assert verified["reported_evaluation"]["final6_hits"] == 6
    assert verified["classification"]["exact_final6_status"] == "verified_true"
    assert verified["classification"]["stop_global_search"] is expected_stop
    assert verified["audit"]["runner_preflight_status"] == "clear"
    assert verified["audit"]["target_leakage_audit_status"] == (
        "clear" if audit_mode == "clear" else "not_clear_or_missing"
    )


def test_verified_six_with_clear_leakage_audit_does_not_stop_after_failed_preflight(
    tmp_path: Path,
) -> None:
    manifest, sources = _synthetic_verified_six_sources("clear", preflight_clear=False)
    ledger_path = tmp_path / "global_opportunities.jsonl"

    import_legacy_historical_artifact(
        source_bytes=sources,
        manifest=manifest,
        ledger_path=ledger_path,
    )

    verified = json.loads(ledger_path.read_text().splitlines()[-1])["payload"]
    assert verified["classification"]["exact_final6_status"] == "verified_true"
    assert verified["classification"]["stop_global_search"] is False
    assert verified["classification"]["success_class"] == (
        "verified_historical_final6_audit_not_clear"
    )
    assert verified["audit"]["runner_preflight_status"] == "not_clear_or_missing"
    assert verified["audit"]["target_leakage_audit_status"] == "clear"


def test_repository_catalog_has_literal_two_level_high_water_without_duplicate_runs(
    tmp_path: Path,
) -> None:
    manifest = json.loads((ROOT / CATALOG_MANIFEST_PATH).read_bytes())

    result = import_legacy_historical_artifact(
        source_bytes=_repository_catalog_sources(manifest),
        manifest=manifest,
        ledger_path=tmp_path / "global_opportunities.jsonl",
    )

    assert result == {
        "event_count": 16774,
        "global_final6_max": None,
        "global_final6_max_status": "unknown_due_to_incomplete_coverage",
        "ledger_sha256": result["ledger_sha256"],
        "reported_final6_max": 4,
        "verified_full_snapshot_final6_max": 3,
    }


def test_import_fails_closed_when_registered_high_water_disagrees_with_sources(
    tmp_path: Path,
) -> None:
    manifest = _manifest()
    manifest["expected_high_water"] = {
        "global_final6_max": None,
        "global_final6_max_status": "unknown_due_to_incomplete_coverage",
        "reported_final6_max_at_least": 5,
        "verified_full_snapshot_final6_max": None,
    }

    with pytest.raises(HistoricalOOSEvidenceError, match="high-water mismatch"):
        import_legacy_historical_artifact(
            source_bytes={"detail.csv": DETAIL_BYTES, "summary.csv": SUMMARY_BYTES},
            manifest=manifest,
            ledger_path=tmp_path / "global_opportunities.jsonl",
        )


def test_import_rejects_impossible_copied_hit_count(tmp_path: Path) -> None:
    impossible_detail = DETAIL_BYTES.replace(b",4,4,6,6,", b",4,4,7,6,", 1)
    manifest = _manifest()
    manifest["sources"]["legacy_detail"]["sha256"] = sha256(
        impossible_detail
    ).hexdigest()

    with pytest.raises(HistoricalOOSEvidenceError, match="hit count"):
        import_legacy_historical_artifact(
            source_bytes={
                "detail.csv": impossible_detail,
                "summary.csv": SUMMARY_BYTES,
            },
            manifest=manifest,
            ledger_path=tmp_path / "global_opportunities.jsonl",
        )


@pytest.mark.parametrize(
    "original,replacement",
    [
        (
            b'"[3, 31, 34, 38, 45, 48]",12,4,',
            b'"[3, 3, 34, 38, 45, 48]",12,4,',
        ),
        (b'"[3, 31, 34, 45]",0.1,', b'"[3, 31, 34, 44]",0.1,'),
        (b'"[3, 31, 34, 45]",0.1,', b'"[3]",0.1,'),
        (b'",12,4,4,6,6,', b'",3,4,4,6,6,'),
    ],
)
def test_import_rejects_malformed_legacy_actual_or_matched_arrays(
    tmp_path: Path,
    original: bytes,
    replacement: bytes,
) -> None:
    malformed_detail = DETAIL_BYTES.replace(original, replacement, 1)
    assert malformed_detail != DETAIL_BYTES
    manifest = _manifest()
    manifest["sources"]["legacy_detail"]["sha256"] = sha256(
        malformed_detail
    ).hexdigest()

    with pytest.raises(HistoricalOOSEvidenceError, match="legacy detail CSV row"):
        import_legacy_historical_artifact(
            source_bytes={
                "detail.csv": malformed_detail,
                "summary.csv": SUMMARY_BYTES,
            },
            manifest=manifest,
            ledger_path=tmp_path / "global_opportunities.jsonl",
        )


def test_reported_six_without_snapshot_never_becomes_verified_success(
    tmp_path: Path,
) -> None:
    header, first_row, _second_row = DETAIL_BYTES.splitlines(keepends=True)
    reported_six_detail = header + first_row.replace(
        b',4,4,6,6,"[3, 31, 34, 45]",',
        b',6,6,6,6,"[3, 31, 34, 38, 45, 48]",',
    )
    manifest = _manifest()
    manifest["sources"]["legacy_detail"]["sha256"] = sha256(
        reported_six_detail
    ).hexdigest()
    ledger_path = tmp_path / "global_opportunities.jsonl"

    result = import_legacy_historical_artifact(
        source_bytes={
            "detail.csv": reported_six_detail,
            "summary.csv": SUMMARY_BYTES,
        },
        manifest=manifest,
        ledger_path=ledger_path,
    )

    opportunity = json.loads(ledger_path.read_text().splitlines()[1])["payload"]
    assert result["reported_final6_max"] == 6
    assert result["global_final6_max"] is None
    assert opportunity["classification"] == {
        "exact_final6_status": "reported_unverified",
        "stop_global_search": False,
        "success_class": "reported_unverified_final6",
        "top12_all_main_status": "reported_true",
    }


def test_validate_rejects_a_tampered_global_ledger_link(tmp_path: Path) -> None:
    ledger_path = tmp_path / "global_opportunities.jsonl"
    manifest = _manifest()
    sources = {"detail.csv": DETAIL_BYTES, "summary.csv": SUMMARY_BYTES}
    import_legacy_historical_artifact(
        source_bytes=sources,
        manifest=manifest,
        ledger_path=ledger_path,
    )
    ledger_path.write_bytes(
        ledger_path.read_bytes().replace(b'"final6_hits":4', b'"final6_hits":5', 1)
    )

    with pytest.raises(HistoricalOOSEvidenceError, match="event hash mismatch"):
        validate_historical_oos_evidence(
            source_bytes=sources,
            manifest=manifest,
            ledger_path=ledger_path,
        )


def test_import_rejects_a_tampered_raw_archive(tmp_path: Path) -> None:
    manifest = _manifest()
    manifest["legacy_bundles"] = [
        {
            "archive_path": "artifact.zip",
            "archive_sha256": sha256(b"immutable-zip").hexdigest(),
            "artifact_id": 1,
            "artifact_name": "reports",
            "bundle_id": "artifact-1",
            "chronology": "implementation_strict_prefix",
            "detail_path": "detail.csv",
            "detail_sha256": sha256(DETAIL_BYTES).hexdigest(),
            "exact_duplicate_of": None,
            "head_sha": "a" * 40,
            "job_id": 11,
            "pre_reveal_persistence": "not_proven",
            "run_id": 111,
            "summary_path": "summary.csv",
            "summary_sha256": sha256(SUMMARY_BYTES).hexdigest(),
        }
    ]

    with pytest.raises(HistoricalOOSEvidenceError, match="SHA-256 mismatch"):
        import_legacy_historical_artifact(
            source_bytes={
                "artifact.zip": b"tampered-zip",
                "detail.csv": DETAIL_BYTES,
                "summary.csv": SUMMARY_BYTES,
            },
            manifest=manifest,
            ledger_path=tmp_path / "global_opportunities.jsonl",
        )


def test_repository_ledger_validates_against_every_registered_source() -> None:
    manifest = json.loads((ROOT / CATALOG_MANIFEST_PATH).read_bytes())

    result = validate_historical_oos_evidence(
        source_bytes=_repository_catalog_sources(manifest),
        manifest=manifest,
        ledger_path=ROOT / "reports/historical_oos/global_opportunities.jsonl",
    )

    assert result == {
        "event_count": 16774,
        "global_final6_max": None,
        "global_final6_max_status": "unknown_due_to_incomplete_coverage",
        "ledger_sha256": (
            "979b1b0d05eea8426e6cee21c1fb1676415abdaf84199263d5c4aba6b7c08e06"
        ),
        "reported_final6_max": 4,
        "verified_full_snapshot_final6_max": 3,
    }
