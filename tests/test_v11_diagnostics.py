from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import shutil
import subprocess
import sys
from copy import deepcopy
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest

import lotto649.v11_diagnostics as diagnostics
from lotto649.domain import Draw
from lotto649.models.v11_previous_bonus_carryover import (
    V1BaseSnapshot,
    forecast_v11_bundle,
    select_pseudo_bonus,
)
from lotto649.v11_diagnostics import (
    CANDIDATE_MODEL,
    CONTROL_MODEL,
    FEATURE_SET_BY_MODEL,
    MODEL_ORDER,
    V11ArtifactPaths,
    V11DiagnosticError,
    V11DiagnosticRequest,
    V11Scope,
    V11TargetPlan,
    anchor_log_gains,
    build_opportunity_record,
    exact_top12_upper_tail,
    holm_v11_adjusted_p,
    paired_top12_bootstrap,
    run_v11_historical,
    score_probability_forecast,
    summarize_v11_scope,
    v11_historical_decision,
    validate_v11_ledger_state_machine,
    verify_hash_chain_ledger,
)

TOOL_PATH = Path(__file__).resolve().parents[1] / "tools" / "run_v11_historical.py"
TOOL_SPEC = importlib.util.spec_from_file_location("v11_historical_tool", TOOL_PATH)
assert TOOL_SPEC is not None and TOOL_SPEC.loader is not None
v11_cli = importlib.util.module_from_spec(TOOL_SPEC)
sys.modules[TOOL_SPEC.name] = v11_cli
TOOL_SPEC.loader.exec_module(v11_cli)


def _forecast(
    model_name: str,
    target: date,
    *,
    history_draws: int = 10,
    history_through: date | None = None,
    prefix_sha256: str = "a" * 64,
    previous_draw: Draw | None = None,
) -> dict:
    probability = 6.0 / 49.0
    ranking = list(range(1, 50))
    through = history_through or target - timedelta(days=1)
    payload = {
        "model_name": model_name,
        "model_version": "v11.0.0"
        if model_name in {CANDIDATE_MODEL, CONTROL_MODEL}
        else "v1.0.0",
        "feature_set": FEATURE_SET_BY_MODEL[model_name],
        "target_date": target.isoformat(),
        "probabilities": {str(label): probability for label in ranking},
        "ranking": ranking,
        "top6": ranking[:6],
        "top12": ranking[:12],
        "top18": ranking[:18],
        "final6": ranking[:6],
        "history_draws": history_draws,
        "history_through": through.isoformat(),
    }
    if model_name in {CANDIDATE_MODEL, CONTROL_MODEL}:
        payload.update(
            {
                "anchor_source_date": through.isoformat(),
                "anchor_kind": "published_bonus"
                if model_name == CANDIDATE_MODEL
                else "deterministic_pseudo_bonus",
                "anchor": (
                    previous_draw.bonus
                    if model_name == CANDIDATE_MODEL and previous_draw is not None
                    else (
                        select_pseudo_bonus(previous_draw)[0]
                        if previous_draw is not None
                        else (7 if model_name == CANDIDATE_MODEL else 8)
                    )
                ),
                "transition_count": 4,
                "D": 4,
                "beta": 0.0,
                "q_b": probability,
                "r_b": probability,
            }
        )
        if model_name == CONTROL_MODEL and previous_draw is not None:
            payload["pseudo_bonus_selection_sha256"] = select_pseudo_bonus(
                previous_draw
            )[1]
    elif model_name == diagnostics.V1_MODEL:
        payload["strict_prefix_sha256"] = prefix_sha256
    else:
        payload["seed"] = 649_000_000 + target.toordinal()
    return payload


def _payload(
    target: date,
    *,
    history_draws: int = 10,
    history_through: date | None = None,
    prefix_sha256: str = "a" * 64,
    previous_draw: Draw | None = None,
) -> dict:
    through = history_through or target - timedelta(days=1)
    forecasts = {
        name: _forecast(
            name,
            target,
            history_draws=history_draws,
            history_through=through,
            prefix_sha256=prefix_sha256,
            previous_draw=previous_draw,
        )
        for name in MODEL_ORDER
    }
    return {
        "target_date": target.isoformat(),
        "prefix": {
            "history_draws": history_draws,
            "history_through": through.isoformat(),
            "strict_prefix_sha256": prefix_sha256,
        },
        "forecasts": forecasts,
    }


def _synthetic_preflight_for_blob(
    blob: bytes,
    *,
    draw_count: int,
    history_through: date,
    target_count: int,
    fixed_half_counts: tuple[int, int],
    registered_identity: diagnostics.V11RegisteredIdentity | None = None,
) -> dict:
    identity = registered_identity or _synthetic_registered_identity(
        blob, draw_count=draw_count, history_through=history_through
    )
    status_documentation = {
        path: {
            "path": path,
            "exact_status_replacements_only": True,
            "registration_sha256": "5" * 64,
            "current_sha256": "6" * 64,
            "replacement_count": diagnostics.STATUS_REPLACEMENT_COUNTS[path],
        }
        for path in sorted(diagnostics.REQUIRED_STATUS_DOCUMENTATION_PATHS)
    }
    return {
        "passed": True,
        "audit_warnings": [],
        "registration_commit": diagnostics.REGISTRATION_COMMIT,
        "implementation_commit": "1" * 40,
        "git": {
            "branch": "synthetic",
            "exact_head": "1" * 40,
            "remote_branch_head": "1" * 40,
            "registration_ancestor": True,
            "changed_paths": sorted(diagnostics.REQUIRED_IMPLEMENTATION_PATHS),
            "status_documentation": status_documentation,
            "ci": {
                "registration": {
                    "required": diagnostics.REQUIRED_CI_CHECKS,
                    "successful": diagnostics.REQUIRED_CI_CHECKS,
                },
                "implementation": {
                    "required": diagnostics.REQUIRED_CI_CHECKS,
                    "successful": diagnostics.REQUIRED_CI_CHECKS,
                },
            },
        },
        "configuration": {
            "path": identity.research_config_path,
            "sha256": identity.research_config_sha256,
            "registry_parameters_equal": True,
            "registry_status": "registered",
            "v1_base_source_commit": identity.v1_base_source_commit,
            "v1_base_config_path": identity.v1_base_config_path,
            "v1_base_config_sha256": identity.v1_base_config_sha256,
            "v1_base_file_sha256": [
                {"path": path, "sha256": digest}
                for path, digest in identity.v1_base_file_sha256
            ],
        },
        "data": {
            "path": identity.data_path,
            "sha256": identity.data_sha256,
            "draw_count": identity.data_draw_count,
            "history_through": identity.data_history_through,
            "source_commit": identity.data_source_commit,
            "source_commit_ancestor_of_registration": True,
            "source_commit_ancestor_of_implementation": True,
            "target_count": target_count,
            "fixed_half_counts": list(fixed_half_counts),
            "source_git_blob": {
                "git_blob_byte_identical": True,
                "sha256": identity.data_sha256,
                "byte_count": len(blob),
            },
        },
        "runtime": {
            "implementation": "CPython",
            "python_version": "3.12.0",
            "platform": "synthetic-platform",
            "executable": "/synthetic/python3.12",
            "requirements_lock_path": identity.runtime_lock_path,
            "requirements_lock_sha256": identity.runtime_lock_sha256,
            "lock_sha256": identity.runtime_lock_sha256,
            "locked_distributions_verified": {},
            "distributions": [],
        },
        "invocation": {
            "logical_command": diagnostics.registered_v11_command(identity),
            "runtime_executable": "/synthetic/python3.12",
            "tool_relative_path": identity.command_tool_relative_path,
            "arguments": [
                "--consume-v11-once",
                "--output-dir",
                identity.command_output_relative_path,
            ],
            "output_relative_path": identity.command_output_relative_path,
            "working_directory_relative_to_root": ".",
        },
        "references": {},
    }


def _synthetic_registered_identity(
    blob: bytes,
    *,
    draw_count: int,
    history_through: date,
    target_start: date | None = None,
    target_end: date | None = None,
    target_count: int = 1,
    scopes: tuple[V11Scope, V11Scope] | None = None,
) -> diagnostics.V11RegisteredIdentity:
    start = target_start or history_through
    end = target_end or start
    registered_scopes = scopes or (
        V11Scope("first", start, end, target_count),
        V11Scope("second", end + timedelta(days=1), end + timedelta(days=1), 0),
    )
    return diagnostics.V11RegisteredIdentity(
        research_config_path="config/research-v11-previous-bonus-carryover.yaml",
        research_config_sha256="3" * 64,
        data_path="data/processed/draws.csv",
        data_source_commit="2" * 40,
        data_sha256=hashlib.sha256(blob).hexdigest(),
        data_draw_count=draw_count,
        data_history_through=history_through.isoformat(),
        runtime_lock_path="requirements-live.lock",
        runtime_lock_sha256="4" * 64,
        v1_base_source_commit="7" * 40,
        v1_base_config_path="config.yaml",
        v1_base_config_sha256="8" * 64,
        v1_base_file_sha256=tuple(
            (path, "9" * 64)
            for path, _digest in diagnostics.REGISTERED_V11_IDENTITY.v1_base_file_sha256
        ),
        analysis_target_start=start.isoformat(),
        analysis_target_end=end.isoformat(),
        analysis_target_count=target_count,
        analysis_scopes=(
            ("aggregate", start.isoformat(), end.isoformat(), target_count),
            *tuple(
                (
                    scope.name,
                    scope.start.isoformat(),
                    scope.end.isoformat(),
                    scope.target_count,
                )
                for scope in registered_scopes
            ),
        ),
        analysis_bootstrap_replicates=10,
        analysis_bootstrap_seed=649,
        analysis_reference_json="{}",
        command_python="python3.12",
        command_tool_relative_path="tools/run_v11_historical.py",
        command_output_relative_path=".",
    )


class _Clock:
    def __init__(self) -> None:
        self.now = datetime(2030, 1, 1, tzinfo=UTC)

    def __call__(self) -> datetime:
        value = self.now
        self.now += timedelta(microseconds=1)
        return value


class _OneShotLedgerIoFault:
    def __init__(self, delegate, mode: str) -> None:
        self._delegate = delegate
        self.mode = mode
        self.fired = False

    def write(self, value: str) -> int:
        if self.mode == "partial_write" and not self.fired:
            self.fired = True
            midpoint = max(1, len(value) // 2)
            self._delegate.write(value[:midpoint])
            self._delegate.flush()
            raise OSError("synthetic partial ledger write")
        return self._delegate.write(value)

    def flush(self) -> None:
        if self.mode == "flush" and not self.fired:
            self._delegate.flush()
            self.fired = True
            raise OSError("synthetic ledger flush failure")
        self._delegate.flush()

    def __getattr__(self, name: str):
        return getattr(self._delegate, name)


def _request(
    tmp_path: Path,
    actuals: list[tuple[int, ...]],
    *,
    audit_clear: bool = True,
    calls: list[tuple[str, str]] | None = None,
) -> V11DiagnosticRequest:
    call_log = calls if calls is not None else []
    start = date(2030, 1, 1)
    targets = []
    ledger_path = V11ArtifactPaths.in_directory(tmp_path).ledger
    history_draw = Draw(start - timedelta(days=1), (20, 21, 22, 23, 24, 25), 26)
    source_draws = [history_draw]
    for index, actual in enumerate(actuals):
        bonus = next(label for label in range(1, 50) if label not in actual)
        source_draws.append(Draw(start + timedelta(days=index), actual, bonus))
    source_header = b"draw_date,n1,n2,n3,n4,n5,n6,bonus\n"

    def source_row(draw: Draw) -> bytes:
        return (
            ",".join(
                [
                    draw.draw_date.isoformat(),
                    *(str(number) for number in draw.numbers),
                    str(draw.bonus),
                ]
            )
            + "\n"
        ).encode("ascii")

    source_rows = [source_row(draw) for draw in source_draws]
    source_blob = source_header + b"".join(source_rows)
    for index, actual in enumerate(actuals):
        target = start + timedelta(days=index)
        previous_draw = source_draws[index]
        prefix_sha256 = hashlib.sha256(
            source_header + b"".join(source_rows[: index + 1])
        ).hexdigest()
        frozen_payload = _payload(
            target,
            history_draws=index + 1,
            history_through=previous_draw.draw_date,
            prefix_sha256=prefix_sha256,
            previous_draw=previous_draw,
        )

        def build(target: date = target, payload: dict = frozen_payload) -> dict:
            call_log.append(("build", target.isoformat()))
            return deepcopy(payload)

        def reveal(
            target: date = target,
            actual: tuple[int, ...] = actual,
        ) -> tuple[int, ...]:
            events = verify_hash_chain_ledger(ledger_path)
            assert events[-1]["event_type"] == "prediction_frozen"
            assert events[-1]["payload"]["target_date"] == target.isoformat()
            call_log.append(("reveal", target.isoformat()))
            return actual

        targets.append(V11TargetPlan(target, build, reveal))
    dates = [target.target_date for target in targets]
    if len(dates) == 1:
        scopes = (
            V11Scope("first", dates[0], dates[0], 1),
            V11Scope(
                "second", dates[0] + timedelta(days=1), dates[0] + timedelta(days=1), 0
            ),
        )
    else:
        scopes = (
            V11Scope("first", dates[0], dates[0], 1),
            V11Scope("second", dates[1], dates[-1], len(dates) - 1),
        )
    registered_identity = _synthetic_registered_identity(
        source_blob,
        draw_count=len(source_draws),
        history_through=source_draws[-1].draw_date,
        target_start=dates[0],
        target_end=dates[-1],
        target_count=len(dates),
        scopes=scopes,
    )
    preflight = _synthetic_preflight_for_blob(
        source_blob,
        draw_count=len(source_draws),
        history_through=source_draws[-1].draw_date,
        target_count=len(actuals),
        fixed_half_counts=(scopes[0].target_count, scopes[1].target_count),
        registered_identity=registered_identity,
    )

    def resolve_source(commit: str, path: str) -> bytes:
        if commit != "2" * 40 or path != "data/processed/draws.csv":
            raise AssertionError("unexpected synthetic source identity")
        return source_blob

    return V11DiagnosticRequest(
        root=tmp_path,
        output_dir=tmp_path,
        code_commit="1" * 40,
        exact_command=diagnostics.registered_v11_command(registered_identity),
        targets=targets,
        preflight=lambda: deepcopy(preflight),
        reference={},
        expected_target_count=len(targets),
        stability_scopes=scopes,
        bootstrap_replicates=10,
        leakage_audit=lambda target, forecast, actual: {
            "clear": audit_clear,
            "checks": [
                {
                    "name": name,
                    "passed": audit_clear,
                    "evidence": {"target": target.isoformat(), "actual": list(actual)},
                }
                for name in diagnostics.REQUIRED_6OF6_AUDIT_CHECKS
            ],
        },
        clock=_Clock(),
        source_blob_resolver=resolve_source,
        registered_identity=registered_identity,
    )


def _rewrite_chain(path: Path, events: list[dict]) -> None:
    previous = diagnostics.ZERO_EVENT_HASH
    rewritten = []
    for sequence, source in enumerate(events):
        without_hash = {
            "event_type": source["event_type"],
            "payload": source["payload"],
            "previous_event_sha256": previous,
            "sequence": sequence,
        }
        event_hash = hashlib.sha256(
            diagnostics._canonical_json_bytes(without_hash) + previous.encode("ascii")
        ).hexdigest()
        rewritten.append({**without_hash, "event_sha256": event_hash})
        previous = event_hash
    path.write_bytes(
        b"".join(
            diagnostics._canonical_json_bytes(event) + b"\n" for event in rewritten
        )
    )


def _rewrite_claim(path: Path, claim: dict, events: list[dict]) -> None:
    raw = diagnostics._canonical_json_bytes(claim) + b"\n"
    path.write_bytes(raw)
    events[0]["payload"]["claim_sha256"] = hashlib.sha256(raw).hexdigest()


@pytest.mark.parametrize("fault", ["partial_write", "flush", "fsync"])
def test_hash_chain_append_io_fault_restores_durable_preappend_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault: str,
) -> None:
    path = tmp_path / "transactional.ledger.jsonl"
    ledger = diagnostics.HashChainLedger.create(path)
    ledger.append("baseline", {"value": 1})
    wrapper = _OneShotLedgerIoFault(ledger._handle, fault)
    ledger._handle = wrapper
    if fault == "fsync":
        original_fsync = diagnostics.os.fsync

        def fail_once(descriptor: int) -> None:
            if descriptor == wrapper.fileno() and not wrapper.fired:
                wrapper.fired = True
                raise OSError("synthetic ledger fsync failure")
            original_fsync(descriptor)

        monkeypatch.setattr(diagnostics.os, "fsync", fail_once)

    with pytest.raises(V11DiagnosticError, match="durably append"):
        ledger.append("faulted", {"value": 2})

    assert [event["event_type"] for event in verify_hash_chain_ledger(path)] == [
        "baseline"
    ]
    ledger.append("after_rollback", {"value": 3})
    ledger.close()
    assert [event["event_type"] for event in verify_hash_chain_ledger(path)] == [
        "baseline",
        "after_rollback",
    ]


def test_hash_chain_append_rollback_fsync_failure_marks_ledger_corrupt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "rollback-fsync.ledger.jsonl"
    ledger = diagnostics.HashChainLedger.create(path)
    ledger.append("baseline", {"value": 1})
    original_fsync = diagnostics.os.fsync
    remaining_failures = 2

    def fail_append_and_rollback_fsync(descriptor: int) -> None:
        nonlocal remaining_failures
        if descriptor == ledger._handle.fileno() and remaining_failures:
            remaining_failures -= 1
            raise OSError("SECRET synthetic double fsync failure")
        original_fsync(descriptor)

    monkeypatch.setattr(diagnostics.os, "fsync", fail_append_and_rollback_fsync)

    with pytest.raises(V11DiagnosticError, match="rollback_failed.*corrupt"):
        ledger.append("faulted", {"value": 2})
    with pytest.raises(V11DiagnosticError, match="retained corrupt"):
        ledger.append("must_not_continue", {"value": 3})

    ledger.close()


def test_public_runner_seam_fsyncs_full_four_model_forecast_before_reveal(
    tmp_path: Path,
) -> None:
    calls: list[tuple[str, str]] = []
    request = _request(
        tmp_path,
        [(44, 45, 46, 47, 48, 49), (38, 39, 40, 41, 42, 43)],
        calls=calls,
    )

    result = run_v11_historical(request)

    assert result["status"] == "published"
    assert calls == [
        ("build", "2030-01-01"),
        ("build", "2030-01-01"),
        ("reveal", "2030-01-01"),
        ("build", "2030-01-02"),
        ("build", "2030-01-02"),
        ("reveal", "2030-01-02"),
    ]
    events = verify_hash_chain_ledger(Path(result["ledger_path"]))
    assert [event["event_type"] for event in events] == [
        "claimed",
        "preflight_passed",
        "scoring_started",
        "prediction_frozen",
        "target_revealed_scored",
        "prediction_frozen",
        "target_revealed_scored",
        "scoring_completed",
        "publication_started",
        "published",
    ]
    frozen = events[3]["payload"]
    assert set(frozen["forecast_payload"]["forecasts"]) == set(MODEL_ORDER)
    assert "prediction_frozen_at_utc" not in frozen["forecast_payload"]
    assert "actual" not in json.dumps(frozen["forecast_payload"]).lower()
    scored = events[4]["payload"]
    opportunity = scored["opportunity"]
    assert opportunity["u_t"] == 1
    only = opportunity["unique_final6_sets"][0]
    assert only["primary_producer_model_name"] == CANDIDATE_MODEL
    assert only["producer_model_names"] == [
        CANDIDATE_MODEL,
        CONTROL_MODEL,
        "ensemble_v1.0.0",
        "random_v1.0.0",
    ]
    assert set(only["producer_forecast_sha256_by_model"]) == set(
        only["producer_model_names"]
    )
    assert len(set(only["producer_forecast_sha256_by_model"].values())) == 4
    validate_v11_ledger_state_machine(
        Path(result["ledger_path"]),
        expected_targets=2,
        source_blob_resolver=request.source_blob_resolver,
        registered_identity=request.registered_identity,
    )


def test_registered_target_rows_are_not_decoded_before_all_predictions_are_frozen(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _request(
        tmp_path,
        [(44, 45, 46, 47, 48, 49), (38, 39, 40, 41, 42, 43)],
    )
    paths = V11ArtifactPaths.in_directory(tmp_path)
    original_reader = diagnostics.csv.reader
    target_dates = {target.target_date.isoformat() for target in request.targets}
    decoder_observations: list[tuple[str, list[str]]] = []

    def observe_decoder(*args, **kwargs):
        events = verify_hash_chain_ledger(paths.ledger)
        frozen_targets = [
            event["payload"]["target_date"]
            for event in events
            if event["event_type"] == "prediction_frozen"
        ]
        row_text = args[0][0]
        row_date = row_text.split(",", 1)[0]
        if row_date in target_dates:
            decoder_observations.append((row_date, frozen_targets))
            assert row_date in frozen_targets
            assert paths.claim.is_file()
        return original_reader(*args, **kwargs)

    monkeypatch.setattr(diagnostics.csv, "reader", observe_decoder)
    run_v11_historical(request)

    assert {row_date for row_date, _frozen in decoder_observations} == target_dates


def test_opportunity_schema_deduplicates_producers_and_fsum_uses_target_u_values() -> (
    None
):
    target = date(2030, 1, 1)
    forecasts = {name: _forecast(name, target) for name in MODEL_ORDER}
    forecasts["random"] = {**forecasts["random"], "final6": [7, 8, 9, 10, 11, 12]}
    hashes = {name: str(index + 1) * 64 for index, name in enumerate(MODEL_ORDER)}

    first = build_opportunity_record(
        forecasts,
        hashes,
        (1, 2, 3, 4, 5, 49),
        target_date=target,
        prior_u_values=(),
    )
    second = build_opportunity_record(
        {name: _forecast(name, target + timedelta(days=1)) for name in MODEL_ORDER},
        hashes,
        (44, 45, 46, 47, 48, 49),
        target_date=target + timedelta(days=1),
        prior_u_values=(2,),
    )

    assert first["u_t"] == 2
    assert first["unique_final6_sets"][0] == {
        "target": "2030-01-01",
        "primary_producer_model_name": CANDIDATE_MODEL,
        "producer_model_names": [
            CANDIDATE_MODEL,
            CONTROL_MODEL,
            "ensemble_v1.0.0",
        ],
        "producer_forecast_sha256_by_model": {
            CANDIDATE_MODEL: "1" * 64,
            CONTROL_MODEL: "2" * 64,
            "ensemble_v1.0.0": "3" * 64,
        },
        "final6": [1, 2, 3, 4, 5, 6],
        "actual": [1, 2, 3, 4, 5, 49],
        "hits": 5,
        "chronology_status": "prediction_frozen_fsynced_before_reveal",
        "exact_6of6": False,
    }
    assert first["unique_final6_sets"][1]["primary_producer_model_name"] == (
        "random_v1.0.0"
    )
    assert first["unique_final6_sets"][1]["producer_model_names"] == ["random_v1.0.0"]
    assert first["unique_final6_sets"][1]["producer_forecast_sha256_by_model"] == {
        "random_v1.0.0": "4" * 64
    }
    assert second["cumulative_familywise_fair_probability"].hex() == (
        "0x1.ccb526d05ac1cp-23"
    )


@pytest.mark.parametrize(
    ("r_b_hex", "response", "expected_log_g_hex", "expected_d_hex"),
    [
        ("0x1.5555555555555p-2", 0, "-0x1.1970f2bd42617p-2", "-0x1.7565011e49675p-3"),
        ("0x1.5555555555555p-2", 1, "0x1.005eee78d91a2p+0", "0x1.058aefa811451p-1"),
        ("0x1.c71c71c71c71ep-4", 0, "0x1.a4a5cac16aef2p-7", "0x1.af8e8210a4152p-4"),
        ("0x1.c71c71c71c71ep-4", 1, "-0x1.8dfb931f71680p-4", "-0x1.2cf25fad8f1c3p-1"),
    ],
)
def test_anchor_gain_wrapper_preserves_registered_observed_branch_oracles(
    r_b_hex: str,
    response: int,
    expected_log_g_hex: str,
    expected_d_hex: str,
) -> None:
    log_g, d_value = anchor_log_gains(0.2, float.fromhex(r_b_hex), response)

    assert log_g.hex() == expected_log_g_hex
    assert d_value.hex() == expected_d_hex


def test_single_draw_exact_top12_six_hit_tail_matches_combinatorial_oracle() -> None:
    assert exact_top12_upper_tail(6, 1) == math.comb(12, 6) / math.comb(49, 6)


def _passing_decision_inputs() -> dict:
    candidate = {
        "primary_top12_lift_vs_theory": 0.1,
        "primary_holm_adjusted_p": 0.05,
        "primary_bootstrap_95_ci": [0.01, 0.2],
        "top6_lift_vs_theory": 0.1,
        "avg_brier": 0.1,
        "avg_log_loss": 0.2,
        "brier_delta_vs_fair": 1.0e-9,
        "log_loss_delta_vs_fair": 1.0e-9,
    }
    null_control = {
        "primary_exact_one_sided_p": math.nextafter(0.05, math.inf),
        "primary_bootstrap_95_ci": [0.01, 0.2],
    }
    v1 = {"avg_brier": 0.1, "avg_log_loss": 0.2}
    paired = {"bootstrap_95_ci": [math.nextafter(0.0, math.inf), 0.2]}
    return {
        "candidate": candidate,
        "candidate_halves": [deepcopy(candidate), deepcopy(candidate)],
        "control": deepcopy(null_control),
        "control_halves": [deepcopy(null_control), deepcopy(null_control)],
        "random_control": deepcopy(null_control),
        "random_control_halves": [deepcopy(null_control), deepcopy(null_control)],
        "v1": v1,
        "v1_halves": [deepcopy(v1), deepcopy(v1)],
        "paired_v1": deepcopy(paired),
        "paired_v1_halves": [deepcopy(paired), deepcopy(paired)],
        "paired_control": deepcopy(paired),
        "paired_control_halves": [deepcopy(paired), deepcopy(paired)],
        "mechanism": {
            "candidate_aggregate_log_g": 2.995732273553991,
            "candidate_aggregate_d": math.nextafter(0.0, math.inf),
            "candidate_half_log_g": [1.0, 1.0],
            "candidate_half_d": [1.0, 1.0],
            "control_aggregate_log_g": math.nextafter(2.995732273553991, -math.inf),
            "candidate_minus_control_aggregate_log_g": 1.0,
            "candidate_minus_control_aggregate_d": 1.0,
            "candidate_minus_control_half_log_g": [1.0, 1.0],
            "candidate_minus_control_half_d": [1.0, 1.0],
        },
        "audit_warnings": [],
    }


def test_exact_ten_gate_conjunction_uses_every_registered_boundary() -> None:
    decision = v11_historical_decision(**_passing_decision_inputs())

    assert tuple(decision["gates"]) == diagnostics.SCIENTIFIC_GATE_NAMES
    assert decision["all_scientific_gates_passed"] is True

    cases = [
        (0, lambda value: value["candidate"].update(primary_top12_lift_vs_theory=0.0)),
        (
            1,
            lambda value: value["candidate"].update(
                primary_holm_adjusted_p=math.nextafter(0.05, math.inf)
            ),
        ),
        (
            2,
            lambda value: value["candidate"].update(primary_bootstrap_95_ci=[0.0, 0.2]),
        ),
        (
            3,
            lambda value: value["candidate_halves"][0].update(
                primary_top12_lift_vs_theory=0.0
            ),
        ),
        (
            4,
            lambda value: value["paired_v1_halves"][1].update(
                bootstrap_95_ci=[0.0, 0.2]
            ),
        ),
        (5, lambda value: value["paired_control"].update(bootstrap_95_ci=[0.0, 0.2])),
        (6, lambda value: value["candidate"].update(top6_lift_vs_theory=0.0)),
        (
            7,
            lambda value: value["candidate_halves"][1].update(
                log_loss_delta_vs_fair=math.nextafter(1.0e-9, math.inf)
            ),
        ),
        (
            8,
            lambda value: value["mechanism"].update(
                candidate_minus_control_half_d=[1.0, 0.0]
            ),
        ),
        (9, lambda value: value.update(audit_warnings=["synthetic_warning"])),
    ]
    for index, mutate in cases:
        inputs = _passing_decision_inputs()
        mutate(inputs)
        failed = v11_historical_decision(**inputs)
        assert failed["gates"][diagnostics.SCIENTIFIC_GATE_NAMES[index]] is False
        assert failed["all_scientific_gates_passed"] is False


@pytest.mark.parametrize(
    ("audit_clear", "terminal_type", "stop_global_search"),
    [
        (True, "historical_6of6_candidate_published", True),
        (False, "historical_6of6_candidate_archived_leakage_failed", False),
    ],
)
def test_exact_final6_stops_after_durable_multi_producer_evidence_and_full_audit(
    tmp_path: Path,
    audit_clear: bool,
    terminal_type: str,
    stop_global_search: bool,
) -> None:
    request = _request(tmp_path, [(1, 2, 3, 4, 5, 6)], audit_clear=audit_clear)
    notification_receipts: list[tuple[str, str]] = []
    ledger_path = V11ArtifactPaths.in_directory(tmp_path).ledger

    def notifier(subject: str, body: str) -> bool:
        events = verify_hash_chain_ledger(ledger_path)
        assert events[-1]["event_type"] == terminal_type
        assert events[-1]["payload"]["notification_status"] == (
            "pending_external_receipt"
        )
        notification_receipts.append((subject, body))
        return True

    values = dict(request.__dict__)
    values["notifier"] = notifier
    result = run_v11_historical(V11DiagnosticRequest(**values))

    assert result["status"] == terminal_type
    assert result["scored_targets"] == 1
    assert result["stop_global_search"] is stop_global_search
    assert notification_receipts
    assert not V11ArtifactPaths.in_directory(tmp_path).report_json.exists()
    bundle = json.loads(Path(result["bundle_path"]).read_text(encoding="utf-8"))
    assert bundle["primary_producer_model_name"] == CANDIDATE_MODEL
    assert bundle["producer_model_names"] == [
        CANDIDATE_MODEL,
        CONTROL_MODEL,
        "ensemble_v1.0.0",
        "random_v1.0.0",
    ]
    assert set(bundle["producer_forecast_sha256_by_model"]) == set(
        bundle["producer_model_names"]
    )
    assert bundle["leakage_audit"]["clear"] is audit_clear
    assert bundle["status"] == (
        "historical-6of6-candidate" if audit_clear else "Archive"
    )
    assert set(bundle["evaluation_by_model"]) == set(MODEL_ORDER)
    assert set(bundle["scored_prefix_benchmark"]) == set(MODEL_ORDER)
    subject, body = notification_receipts[0]
    assert ("成功预测" in subject) is audit_clear
    assert "生产者模型版本" in body
    assert "截至停止点完整四模型benchmark" in body
    assert diagnostics.MODEL_VERSION in body
    events = validate_v11_ledger_state_machine(
        ledger_path,
        expected_targets=1,
        source_blob_resolver=request.source_blob_resolver,
        registered_identity=request.registered_identity,
    )
    assert [event["event_type"] for event in events[-4:]] == [
        "historical_6of6_candidate_detected",
        "historical_6of6_leakage_audit_completed",
        terminal_type,
        "terminal_notification_receipt",
    ]


def test_post_claim_failure_is_archived_and_permanent_claim_blocks_rerun(
    tmp_path: Path,
) -> None:
    request = _request(tmp_path, [(44, 45, 46, 47, 48, 49)])
    target = request.targets[0].target_date
    original_build = request.targets[0].build_forecasts

    def fail_reveal() -> tuple[int, ...]:
        events = verify_hash_chain_ledger(
            V11ArtifactPaths.in_directory(tmp_path).ledger
        )
        assert events[-1]["event_type"] == "prediction_frozen"
        raise RuntimeError("synthetic opaque reveal failed")

    values = dict(request.__dict__)
    values["targets"] = [V11TargetPlan(target, original_build, fail_reveal)]
    failing = V11DiagnosticRequest(**values)

    with pytest.raises(RuntimeError, match="opaque reveal failed"):
        run_v11_historical(failing)

    paths = V11ArtifactPaths.in_directory(tmp_path)
    events = validate_v11_ledger_state_machine(
        paths.ledger,
        expected_targets=1,
        source_blob_resolver=request.source_blob_resolver,
        registered_identity=request.registered_identity,
    )
    assert events[-1]["event_type"] == "failed"
    assert events[-1]["payload"]["status"] == "consumed_archive_no_rerun"
    assert paths.claim.is_file()
    with pytest.raises(V11DiagnosticError, match="already exists"):
        run_v11_historical(failing)


def test_production_preflight_accepts_exact_eight_paths() -> None:
    changed = "\n".join(sorted(v11_cli.REQUIRED_IMPLEMENTATION_PATHS)) + "\n"
    assert set(v11_cli._validate_implementation_changed_paths(changed)) == (
        v11_cli.REQUIRED_IMPLEMENTATION_PATHS
    )
    with pytest.raises(V11DiagnosticError, match="exactly eight"):
        v11_cli._validate_implementation_changed_paths(
            changed + "src/lotto649/live.py\n"
        )


def test_registered_command_is_machine_independent_and_production_argv_is_exact(
    tmp_path: Path,
) -> None:
    assert diagnostics.registered_v11_command() == (
        "python3.12 tools/run_v11_historical.py --consume-v11-once --output-dir reports"
    )
    canonical_argv = [
        str(TOOL_PATH),
        "--consume-v11-once",
        "--output-dir",
        "reports",
    ]
    evidence = v11_cli._canonical_invocation(
        canonical_argv,
        cwd=v11_cli.ROOT,
        runtime_executable="/venv-a/bin/python3.12",
        implementation="CPython",
        version_info=(3, 12),
    )
    assert evidence["logical_command"] == diagnostics.registered_v11_command()
    assert "/venv-a" not in evidence["logical_command"]

    for forged in (
        canonical_argv[:-2],
        [*canonical_argv, "--extra"],
        [*canonical_argv[:3], str((v11_cli.ROOT / "reports").resolve())],
    ):
        with pytest.raises(V11DiagnosticError, match="invocation"):
            v11_cli._canonical_invocation(
                forged,
                cwd=v11_cli.ROOT,
                runtime_executable="/venv-b/bin/python3.12",
                implementation="CPython",
                version_info=(3, 12),
            )
    with pytest.raises(V11DiagnosticError, match="invocation"):
        v11_cli._canonical_invocation(
            canonical_argv,
            cwd=tmp_path,
            runtime_executable="/venv-b/bin/python3.12",
            implementation="CPython",
            version_info=(3, 12),
        )


@pytest.mark.parametrize("terminal_kind", ["normal", "exact_6of6"])
def test_published_evidence_replays_after_output_directory_relocation(
    tmp_path: Path,
    terminal_kind: str,
) -> None:
    original = tmp_path / "original" / "reports"
    relocated = tmp_path / "relocated" / "reports"
    actuals = (
        [(1, 2, 3, 4, 5, 6)]
        if terminal_kind == "exact_6of6"
        else [(44, 45, 46, 47, 48, 49), (38, 39, 40, 41, 42, 43)]
    )
    request = _request(original, actuals)

    run_v11_historical(request)
    shutil.copytree(original, relocated)

    relocated_paths = V11ArtifactPaths.in_directory(relocated)
    events = validate_v11_ledger_state_machine(
        relocated_paths.ledger,
        expected_targets=request.expected_target_count,
        source_blob_resolver=request.source_blob_resolver,
        registered_identity=request.registered_identity,
    )
    scoring_started = next(
        event for event in events if event["event_type"] == "scoring_started"
    )["payload"]
    cleanup = scoring_started["acquisition_cleanup"]
    assert [item["outcome"] for item in cleanup["stage_results"]] == [
        "removed",
        "removed",
    ]
    assert cleanup["parent_fsync"]["outcome"] == "succeeded"
    assert scoring_started["acquisition_warnings"] == []
    assert events[-1]["event_type"] in {
        "published",
        "terminal_notification_receipt",
    }
    for artifact in relocated.iterdir():
        if artifact.is_file():
            assert str(original).encode("utf-8") not in artifact.read_bytes()


def test_frozen_identity_mismatch_fails_before_permanent_claim_or_forecast(
    tmp_path: Path,
) -> None:
    calls: list[tuple[str, str]] = []
    request = _request(
        tmp_path,
        [(44, 45, 46, 47, 48, 49), (38, 39, 40, 41, 42, 43)],
        calls=calls,
    )
    original_preflight = request.preflight

    def mismatched_preflight() -> dict:
        evidence = original_preflight()
        evidence["runtime"]["requirements_lock_sha256"] = "a" * 64
        evidence["runtime"]["lock_sha256"] = "a" * 64
        return evidence

    values = dict(request.__dict__)
    values["preflight"] = mismatched_preflight

    with pytest.raises(V11DiagnosticError, match="runtime preflight"):
        run_v11_historical(V11DiagnosticRequest(**values))

    paths = V11ArtifactPaths.in_directory(tmp_path)
    assert calls == []
    assert not any(path.exists() for path in paths.all_normal_paths())


@pytest.mark.parametrize(
    "attack",
    ["bootstrap", "command", "target_dates", "scope_boundary", "reference"],
)
def test_registered_analysis_plan_mismatch_fails_before_claim_or_forecast(
    tmp_path: Path,
    attack: str,
) -> None:
    calls: list[tuple[str, str]] = []
    request = _request(
        tmp_path,
        [(44, 45, 46, 47, 48, 49), (38, 39, 40, 41, 42, 43)],
        calls=calls,
    )
    values = dict(request.__dict__)
    if attack == "bootstrap":
        values["bootstrap_replicates"] = 1
    elif attack == "command":
        values["exact_command"] = "not-registered"
    elif attack == "target_dates":
        shifted = [
            V11TargetPlan(
                item.target_date + timedelta(days=2),
                item.build_forecasts,
                item.reveal_actual,
            )
            for item in request.targets
        ]
        values["targets"] = shifted
        values["stability_scopes"] = (
            V11Scope("first", shifted[0].target_date, shifted[0].target_date, 1),
            V11Scope("second", shifted[1].target_date, shifted[1].target_date, 1),
        )
    elif attack == "scope_boundary":
        first, second = request.stability_scopes
        values["stability_scopes"] = (
            V11Scope(
                first.name,
                first.start - timedelta(days=1),
                first.end,
                first.target_count,
            ),
            second,
        )
    else:
        values["reference"] = {"forged_reference": 1}

    with pytest.raises(V11DiagnosticError, match="analysis plan|canonical command"):
        run_v11_historical(V11DiagnosticRequest(**values))

    paths = V11ArtifactPaths.in_directory(tmp_path)
    assert calls == []
    assert not any(path.exists() for path in paths.all_normal_paths())


def test_status_documents_must_equal_exact_registered_blob_replacements() -> None:
    root = Path(__file__).resolve().parents[1]
    for path in sorted(v11_cli.REQUIRED_STATUS_DOCUMENTATION_PATHS):
        registered = subprocess.run(
            ["git", "show", f"{diagnostics.REGISTRATION_COMMIT}:{path}"],
            cwd=root,
            check=True,
            capture_output=True,
        ).stdout
        current = (root / path).read_bytes()

        evidence = v11_cli._validate_status_documentation_blobs(
            path, registered, current
        )

        assert evidence["exact_status_replacements_only"] is True
        with pytest.raises(V11DiagnosticError, match="exact frozen status"):
            v11_cli._validate_status_documentation_blobs(
                path, registered, current + b"\n"
            )


def test_control_null_requires_interval_to_actually_contain_zero() -> None:
    inputs = _passing_decision_inputs()
    inputs["control"].update(
        primary_exact_one_sided_p=0.01,
        primary_bootstrap_95_ci=[-0.2, -0.01],
    )

    decision = v11_historical_decision(**inputs)

    assert decision["gates"][diagnostics.SCIENTIFIC_GATE_NAMES[5]] is False


def test_ci_duplicate_failure_or_pending_cannot_be_hidden_by_success() -> None:
    successful = {
        "name": "test",
        "status": "completed",
        "conclusion": "success",
    }
    smoke = {
        "name": "source-and-model-smoke",
        "status": "completed",
        "conclusion": "success",
    }
    for conflicting in (
        {"name": "test", "status": "completed", "conclusion": "failure"},
        {"name": "test", "status": "in_progress", "conclusion": None},
    ):
        with pytest.raises(V11DiagnosticError, match="not uniformly green"):
            v11_cli._validate_ci_check_runs([successful, smoke, conflicting])


def test_registered_source_blob_must_match_git_object_byte_for_byte() -> None:
    blob = b"draw_date,n1,n2,n3,n4,n5,n6,bonus\n"
    expected = hashlib.sha256(blob).hexdigest()

    evidence = v11_cli._validate_registered_source_blob(blob, blob, expected)

    assert evidence["git_blob_byte_identical"] is True
    with pytest.raises(V11DiagnosticError, match="Git source blob"):
        v11_cli._validate_registered_source_blob(blob, blob + b"x", expected)


def test_production_source_resolver_only_reads_the_frozen_git_object(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, ...]] = []

    def git_bytes(*args: str) -> bytes:
        calls.append(args)
        return b"registered-source"

    monkeypatch.setattr(v11_cli, "_git_bytes", git_bytes)
    identity = diagnostics.REGISTERED_V11_IDENTITY

    assert (
        v11_cli._resolve_registered_source_blob(
            identity.data_source_commit, identity.data_path
        )
        == b"registered-source"
    )
    assert calls == [("show", f"{identity.data_source_commit}:{identity.data_path}")]
    with pytest.raises(V11DiagnosticError, match="resolver identity"):
        v11_cli._resolve_registered_source_blob("a" * 40, identity.data_path)
    assert len(calls) == 1


def test_notification_adapter_refuses_branch_drift_before_workflow_dispatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands: list[tuple[str, ...]] = []
    monkeypatch.setattr(v11_cli, "_remote_repository", lambda: ("owner", "repo"))
    monkeypatch.setattr(v11_cli, "_git_text", lambda *_args: "implementation-branch")

    def fake_run(*args: str, **_kwargs):
        commands.append(args)
        return subprocess.CompletedProcess(args, 0, stdout=("2" * 40).encode())

    monkeypatch.setattr(v11_cli, "_run", fake_run)
    notifier = v11_cli.GitHubWorkflowNotifier("1" * 40)

    with pytest.raises(V11DiagnosticError, match="branch drifted"):
        notifier("subject", "body")

    assert any("branches/implementation-branch" in part for part in commands[0])
    assert all("workflow" not in command for args in commands for command in args)


@pytest.mark.parametrize(
    "attack",
    [
        "preflight_false",
        "fake_claim_seed",
        "score_99",
        "opportunity_99",
        "progress_99",
        "missing_scoring",
        "missing_publication",
        "fake_report_binding",
        "fake_markdown",
        "fake_publication_warning",
        "fake_acquisition_warning",
        "fake_changed_paths",
    ],
)
def test_semantic_replay_rejects_coordinated_rechain_attacks(
    tmp_path: Path, attack: str
) -> None:
    output = tmp_path / attack
    output.mkdir()
    request = _request(
        output,
        [(44, 45, 46, 47, 48, 49), (38, 39, 40, 41, 42, 43)],
    )
    run_v11_historical(request)
    paths = V11ArtifactPaths.in_directory(output)
    events = verify_hash_chain_ledger(paths.ledger)
    claim = json.loads(paths.claim.read_bytes())

    if attack == "preflight_false":
        claim["preflight"]["passed"] = False
        events[1]["payload"]["passed"] = False
        _rewrite_claim(paths.claim, claim, events)
    elif attack == "fake_claim_seed":
        claim["seed"] = 99
        _rewrite_claim(paths.claim, claim, events)
    elif attack == "score_99":
        next(
            event for event in events if event["event_type"] == "target_revealed_scored"
        )["payload"]["scores"][CANDIDATE_MODEL]["final6_hits"] = 99
    elif attack == "opportunity_99":
        next(
            event for event in events if event["event_type"] == "target_revealed_scored"
        )["payload"]["opportunity"]["u_t"] = 99
    elif attack == "progress_99":
        next(
            event for event in events if event["event_type"] == "target_revealed_scored"
        )["payload"]["progressive_record"]["current_final6_hits"] = 99
    elif attack == "missing_scoring":
        events = [
            event for event in events if event["event_type"] != "target_revealed_scored"
        ]
    elif attack == "missing_publication":
        events = [
            event for event in events if event["event_type"] != "publication_started"
        ]
    elif attack == "fake_report_binding":
        terminal = next(event for event in events if event["event_type"] == "published")
        terminal["payload"]["json_path"] = str(output / "forged.json")
        terminal["payload"]["json_sha256"] = "9" * 64
    elif attack == "fake_markdown":
        paths.report_markdown.write_bytes(
            paths.report_markdown.read_bytes() + b"forged\n"
        )
        terminal = next(event for event in events if event["event_type"] == "published")
        terminal["payload"]["markdown_sha256"] = hashlib.sha256(
            paths.report_markdown.read_bytes()
        ).hexdigest()
    elif attack == "fake_publication_warning":
        terminal = next(event for event in events if event["event_type"] == "published")
        terminal["payload"]["operational_warnings"].append(
            "publication_stage_cleanup_failed:forged:OSError"
        )
    elif attack == "fake_acquisition_warning":
        forged_warning = "acquisition_cleanup_failed:" + "f" * 64
        scoring_started = next(
            event for event in events if event["event_type"] == "scoring_started"
        )
        scoring_started["payload"]["acquisition_warnings"].append(forged_warning)
        _rewrite_chain(paths.ledger, events)
        events = verify_hash_chain_ledger(paths.ledger)
        report = json.loads(paths.report_json.read_bytes())
        report["operational_warnings"].append(forged_warning)
        publication_started = next(
            event for event in events if event["event_type"] == "publication_started"
        )
        report["ledger_head_before_publication"] = publication_started["event_sha256"]
        report_bytes = (
            json.dumps(
                report,
                indent=2,
                sort_keys=True,
                allow_nan=False,
                ensure_ascii=False,
            ).encode("utf-8")
            + b"\n"
        )
        markdown_bytes = diagnostics._render_markdown(report).encode("utf-8")
        paths.report_json.write_bytes(report_bytes)
        paths.report_markdown.write_bytes(markdown_bytes)
        terminal = next(event for event in events if event["event_type"] == "published")
        terminal["payload"]["operational_warnings"].append(forged_warning)
        terminal["payload"]["json_sha256"] = hashlib.sha256(report_bytes).hexdigest()
        terminal["payload"]["markdown_sha256"] = hashlib.sha256(
            markdown_bytes
        ).hexdigest()
    else:
        claim["preflight"]["git"]["changed_paths"] = ["src/lotto649/v11_diagnostics.py"]
        events[1]["payload"]["git"]["changed_paths"] = [
            "src/lotto649/v11_diagnostics.py"
        ]
        _rewrite_claim(paths.claim, claim, events)
    _rewrite_chain(paths.ledger, events)

    with pytest.raises(V11DiagnosticError):
        validate_v11_ledger_state_machine(
            paths.ledger,
            expected_targets=2,
            source_blob_resolver=request.source_blob_resolver,
            registered_identity=request.registered_identity,
        )


def test_semantic_replay_rejects_fully_coordinated_actual_substitution_against_trusted_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    trusted = _request(
        tmp_path / "unused-trusted",
        [(44, 45, 46, 47, 48, 49), (38, 39, 40, 41, 42, 43)],
    )
    assert trusted.source_blob_resolver is not None
    trusted_blob = trusted.source_blob_resolver("2" * 40, "data/processed/draws.csv")
    forged_dir = tmp_path / "forged"
    forged_dir.mkdir()
    forged = _request(
        forged_dir,
        [(44, 45, 46, 47, 48, 49), (14, 15, 16, 17, 18, 19)],
    )
    forged_preflight = forged.preflight

    def claim_trusted_source_while_revealing_forged_actual() -> dict:
        evidence = dict(forged_preflight())
        data = dict(evidence["data"])
        trusted_sha = hashlib.sha256(trusted_blob).hexdigest()
        data["sha256"] = trusted_sha
        data["source_git_blob"] = {
            "git_blob_byte_identical": True,
            "sha256": trusted_sha,
            "byte_count": len(trusted_blob),
        }
        evidence["data"] = data
        return evidence

    values = dict(forged.__dict__)
    values["preflight"] = claim_trusted_source_while_revealing_forged_actual
    values["source_blob_resolver"] = trusted.source_blob_resolver
    values["registered_identity"] = trusted.registered_identity
    original_validator = diagnostics.validate_v11_ledger_state_machine
    monkeypatch.setattr(
        diagnostics,
        "validate_v11_ledger_state_machine",
        lambda *_args, **_kwargs: [],
    )
    run_v11_historical(V11DiagnosticRequest(**values))
    monkeypatch.setattr(
        diagnostics, "validate_v11_ledger_state_machine", original_validator
    )

    with pytest.raises(
        V11DiagnosticError,
        match="trusted registered source actual differs from ledger reveal",
    ):
        validate_v11_ledger_state_machine(
            V11ArtifactPaths.in_directory(forged_dir).ledger,
            expected_targets=2,
            source_blob_resolver=lambda _commit, _path: trusted_blob,
            registered_identity=trusted.registered_identity,
        )


def test_partial_failed_ledger_still_rejects_incomplete_preflight_evidence(
    tmp_path: Path,
) -> None:
    request = _request(tmp_path, [(44, 45, 46, 47, 48, 49)])
    target = request.targets[0].target_date
    original_build = request.targets[0].build_forecasts

    def fail_reveal() -> tuple[int, ...]:
        raise RuntimeError("synthetic stop after frozen prediction")

    values = dict(request.__dict__)
    values["targets"] = [V11TargetPlan(target, original_build, fail_reveal)]
    with pytest.raises(RuntimeError, match="stop after frozen"):
        run_v11_historical(V11DiagnosticRequest(**values))
    paths = V11ArtifactPaths.in_directory(tmp_path)
    events = validate_v11_ledger_state_machine(
        paths.ledger,
        expected_targets=1,
        source_blob_resolver=request.source_blob_resolver,
        registered_identity=request.registered_identity,
    )
    claim = json.loads(paths.claim.read_bytes())
    claim["preflight"].pop("runtime")
    events[1]["payload"].pop("runtime")
    _rewrite_claim(paths.claim, claim, events)
    _rewrite_chain(paths.ledger, events)

    with pytest.raises(V11DiagnosticError, match="preflight evidence"):
        validate_v11_ledger_state_machine(
            paths.ledger,
            expected_targets=1,
            source_blob_resolver=request.source_blob_resolver,
            registered_identity=request.registered_identity,
        )


def test_partial_failed_ledger_rejects_nonregistered_changed_path_set(
    tmp_path: Path,
) -> None:
    request, paths, events = _produce_failed_after_frozen_ledger(tmp_path)
    claim = json.loads(paths.claim.read_bytes())
    forged_paths = ["src/lotto649/v11_diagnostics.py"]
    claim["preflight"]["git"]["changed_paths"] = forged_paths
    events[1]["payload"]["git"]["changed_paths"] = forged_paths
    _rewrite_claim(paths.claim, claim, events)
    _rewrite_chain(paths.ledger, events)

    with pytest.raises(V11DiagnosticError, match="changed paths"):
        validate_v11_ledger_state_machine(
            paths.ledger,
            expected_targets=1,
            source_blob_resolver=request.source_blob_resolver,
            registered_identity=request.registered_identity,
        )


def test_partial_failed_ledger_rejects_coordinated_alternate_legal_source_blob(
    tmp_path: Path,
) -> None:
    request, paths, events = _produce_failed_after_frozen_ledger(tmp_path)
    assert request.source_blob_resolver is not None
    original_blob = request.source_blob_resolver("2" * 40, "data/processed/draws.csv")
    alternate_blob = original_blob.replace(
        b"2030-01-01,44,45,46,47,48,49,1\n",
        b"2030-01-01,44,45,46,47,48,49,2\n",
    )
    assert alternate_blob != original_blob
    alternate_sha = hashlib.sha256(alternate_blob).hexdigest()
    claim = json.loads(paths.claim.read_bytes())
    data = claim["preflight"]["data"]
    data["source_commit"] = "7" * 40
    data["sha256"] = alternate_sha
    data["source_git_blob"] = {
        "git_blob_byte_identical": True,
        "sha256": alternate_sha,
        "byte_count": len(alternate_blob),
    }
    events[1]["payload"]["data"] = deepcopy(data)
    _rewrite_claim(paths.claim, claim, events)
    _rewrite_chain(paths.ledger, events)

    with pytest.raises(V11DiagnosticError, match="registered.*identity|source commit"):
        validate_v11_ledger_state_machine(
            paths.ledger,
            expected_targets=1,
            source_blob_resolver=lambda commit, _path: (
                alternate_blob if commit == "7" * 40 else original_blob
            ),
            registered_identity=request.registered_identity,
        )


@pytest.mark.parametrize(
    "attack",
    ["research_config", "runtime_lock", "v1_source", "v1_config", "v1_files"],
)
def test_partial_failed_ledger_binds_every_frozen_registered_identity_family(
    tmp_path: Path,
    attack: str,
) -> None:
    request, paths, events = _produce_failed_after_frozen_ledger(tmp_path)
    claim = json.loads(paths.claim.read_bytes())
    preflight = claim["preflight"]
    if attack == "research_config":
        preflight["configuration"]["sha256"] = "a" * 64
    elif attack == "runtime_lock":
        preflight["runtime"]["requirements_lock_sha256"] = "a" * 64
        preflight["runtime"]["lock_sha256"] = "a" * 64
    elif attack == "v1_source":
        preflight["configuration"]["v1_base_source_commit"] = "a" * 40
    elif attack == "v1_config":
        preflight["configuration"]["v1_base_config_sha256"] = "a" * 64
    else:
        preflight["configuration"]["v1_base_file_sha256"][0]["sha256"] = "a" * 64
    events[1]["payload"] = deepcopy(preflight)
    _rewrite_claim(paths.claim, claim, events)
    _rewrite_chain(paths.ledger, events)

    with pytest.raises(V11DiagnosticError, match="configuration|runtime"):
        validate_v11_ledger_state_machine(
            paths.ledger,
            expected_targets=1,
            source_blob_resolver=request.source_blob_resolver,
            registered_identity=request.registered_identity,
        )


@pytest.mark.parametrize(
    "attack", ["bootstrap", "command", "target_dates", "scope", "reference"]
)
def test_partial_failed_ledger_rejects_coordinated_registered_plan_rechain(
    tmp_path: Path,
    attack: str,
) -> None:
    request, paths, events = _produce_failed_after_frozen_ledger(tmp_path)
    claim = json.loads(paths.claim.read_bytes())
    if attack == "bootstrap":
        claim["analysis_plan"]["bootstrap_replicates"] = 1
    elif attack == "command":
        claim["exact_command"] = "coordinated-forged-command"
    elif attack == "target_dates":
        claim["analysis_plan"]["target_dates"] = ["2029-12-31"]
    elif attack == "scope":
        claim["analysis_plan"]["scopes"][1]["start"] = "2029-12-31"
    else:
        claim["analysis_plan"]["reference"] = {"forged": True}
    if "analysis_plan_sha256" in claim:
        claim["analysis_plan_sha256"] = diagnostics.canonical_sha256(
            claim["analysis_plan"]
        )
    if "exact_command_sha256" in claim:
        claim["exact_command_sha256"] = hashlib.sha256(
            claim["exact_command"].encode("utf-8")
        ).hexdigest()
    _rewrite_claim(paths.claim, claim, events)
    _rewrite_chain(paths.ledger, events)

    with pytest.raises(V11DiagnosticError, match="analysis plan|canonical command"):
        validate_v11_ledger_state_machine(
            paths.ledger,
            expected_targets=1,
            source_blob_resolver=request.source_blob_resolver,
            registered_identity=request.registered_identity,
        )


def _produce_failed_after_frozen_ledger(
    tmp_path: Path,
) -> tuple[V11DiagnosticRequest, V11ArtifactPaths, list[dict]]:
    request = _request(tmp_path, [(44, 45, 46, 47, 48, 49)])
    target = request.targets[0].target_date
    original_build = request.targets[0].build_forecasts

    def fail_reveal() -> tuple[int, ...]:
        raise RuntimeError("synthetic stop after frozen prediction")

    values = dict(request.__dict__)
    values["targets"] = [V11TargetPlan(target, original_build, fail_reveal)]
    with pytest.raises(RuntimeError, match="stop after frozen"):
        run_v11_historical(V11DiagnosticRequest(**values))
    paths = V11ArtifactPaths.in_directory(tmp_path)
    return request, paths, verify_hash_chain_ledger(paths.ledger)


def test_failed_after_prediction_requires_the_complete_terminal_schema(
    tmp_path: Path,
) -> None:
    request, paths, events = _produce_failed_after_frozen_ledger(tmp_path)
    failed = events[-1]
    assert failed["event_type"] == "failed"
    assert failed["payload"]["last_frozen_target_date"] is not None
    failed["payload"].pop("error_type")
    _rewrite_chain(paths.ledger, events)

    with pytest.raises(V11DiagnosticError, match="failed terminal evidence"):
        validate_v11_ledger_state_machine(
            paths.ledger,
            expected_targets=1,
            source_blob_resolver=request.source_blob_resolver,
            registered_identity=request.registered_identity,
        )


def test_failed_between_targets_requires_complete_schema_and_null_active_binding(
    tmp_path: Path,
) -> None:
    request = _request(
        tmp_path,
        [(44, 45, 46, 47, 48, 49), (38, 39, 40, 41, 42, 43)],
    )
    targets = list(request.targets)

    def fail_second_build() -> dict:
        raise RuntimeError("synthetic failure between targets")

    targets[1] = V11TargetPlan(
        targets[1].target_date, fail_second_build, targets[1].reveal_actual
    )
    values = dict(request.__dict__)
    values["targets"] = targets
    with pytest.raises(RuntimeError, match="between targets"):
        run_v11_historical(V11DiagnosticRequest(**values))
    paths = V11ArtifactPaths.in_directory(tmp_path)
    events = verify_hash_chain_ledger(paths.ledger)
    failed = events[-1]
    assert failed["event_type"] == "failed"
    assert failed["payload"]["last_frozen_target_date"] is None
    assert failed["payload"]["last_frozen_forecast_sha256"] is None
    failed["payload"].pop("error_message")
    _rewrite_chain(paths.ledger, events)

    with pytest.raises(V11DiagnosticError, match="failed terminal evidence"):
        validate_v11_ledger_state_machine(
            paths.ledger,
            expected_targets=2,
            source_blob_resolver=request.source_blob_resolver,
            registered_identity=request.registered_identity,
        )


@pytest.mark.parametrize(
    "failed_event",
    [
        "historical_6of6_candidate_detected",
        "historical_6of6_leakage_audit_completed",
        "publication_started",
    ],
)
def test_each_post_score_failure_transition_is_replayable_and_strict(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failed_event: str,
) -> None:
    request = (
        _request(tmp_path, [(1, 2, 3, 4, 5, 6)])
        if failed_event.startswith("historical_6of6")
        else _request(
            tmp_path,
            [(44, 45, 46, 47, 48, 49), (38, 39, 40, 41, 42, 43)],
        )
    )
    original_append = diagnostics.HashChainLedger.append
    faulted = False

    def fail_once(
        ledger: diagnostics.HashChainLedger, event_type: str, payload: dict
    ) -> dict:
        nonlocal faulted
        if event_type == failed_event and not faulted:
            faulted = True
            raise RuntimeError(f"synthetic {failed_event} append failure")
        return original_append(ledger, event_type, payload)

    monkeypatch.setattr(diagnostics.HashChainLedger, "append", fail_once)
    with pytest.raises(RuntimeError, match=failed_event):
        run_v11_historical(request)

    paths = V11ArtifactPaths.in_directory(tmp_path)
    events = validate_v11_ledger_state_machine(
        paths.ledger,
        expected_targets=request.expected_target_count,
        source_blob_resolver=request.source_blob_resolver,
        registered_identity=request.registered_identity,
    )
    assert events[-1]["event_type"] == "failed"
    assert events[-1]["payload"]["last_frozen_target_date"] is None
    events[-1]["payload"]["unexpected"] = True
    _rewrite_chain(paths.ledger, events)
    with pytest.raises(V11DiagnosticError, match="failed terminal evidence"):
        validate_v11_ledger_state_machine(
            paths.ledger,
            expected_targets=request.expected_target_count,
            source_blob_resolver=request.source_blob_resolver,
            registered_identity=request.registered_identity,
        )


def test_semantic_replay_rejects_non_rfc3339_prediction_timestamp(
    tmp_path: Path,
) -> None:
    request, paths, events = _produce_failed_after_frozen_ledger(tmp_path)
    frozen = next(
        event for event in events if event["event_type"] == "prediction_frozen"
    )
    frozen["payload"]["prediction_frozen_at_utc"] = "2030-01-01 00:00:00"
    _rewrite_chain(paths.ledger, events)

    with pytest.raises(V11DiagnosticError, match="timestamp"):
        validate_v11_ledger_state_machine(
            paths.ledger,
            expected_targets=1,
            source_blob_resolver=request.source_blob_resolver,
            registered_identity=request.registered_identity,
        )


@pytest.mark.parametrize(
    ("field", "forged_value"),
    [
        ("anchor", 27),
        ("beta", 0.25),
        ("q_b", 0.2),
        ("r_b", 0.2),
    ],
)
def test_semantic_replay_rejects_rehashed_anchor_probability_contract_forgery(
    tmp_path: Path,
    field: str,
    forged_value: float,
) -> None:
    request, paths, events = _produce_failed_after_frozen_ledger(tmp_path)
    frozen = next(
        event for event in events if event["event_type"] == "prediction_frozen"
    )
    payload = frozen["payload"]["forecast_payload"]
    payload["forecasts"][CANDIDATE_MODEL][field] = forged_value
    forecast_sha = diagnostics.canonical_sha256(payload)
    frozen["payload"]["forecast_sha256"] = forecast_sha
    frozen["payload"]["model_forecast_sha256"][CANDIDATE_MODEL] = (
        diagnostics.canonical_sha256(payload["forecasts"][CANDIDATE_MODEL])
    )
    failed = events[-1]["payload"]
    failed["last_frozen_forecast_sha256"] = forecast_sha
    _rewrite_chain(paths.ledger, events)

    with pytest.raises(V11DiagnosticError, match="anchor|tilt|probability"):
        validate_v11_ledger_state_machine(
            paths.ledger,
            expected_targets=1,
            source_blob_resolver=request.source_blob_resolver,
            registered_identity=request.registered_identity,
        )


def test_semantic_replay_rejects_deleted_control_anchor_digest(
    tmp_path: Path,
) -> None:
    request, paths, events = _produce_failed_after_frozen_ledger(tmp_path)
    frozen = next(
        event for event in events if event["event_type"] == "prediction_frozen"
    )
    payload = frozen["payload"]["forecast_payload"]
    payload["forecasts"][CONTROL_MODEL].pop("pseudo_bonus_selection_sha256")
    forecast_sha = diagnostics.canonical_sha256(payload)
    frozen["payload"]["forecast_sha256"] = forecast_sha
    frozen["payload"]["model_forecast_sha256"][CONTROL_MODEL] = (
        diagnostics.canonical_sha256(payload["forecasts"][CONTROL_MODEL])
    )
    events[-1]["payload"]["last_frozen_forecast_sha256"] = forecast_sha
    _rewrite_chain(paths.ledger, events)

    with pytest.raises(V11DiagnosticError, match="pseudo|control"):
        validate_v11_ledger_state_machine(
            paths.ledger,
            expected_targets=1,
            source_blob_resolver=request.source_blob_resolver,
            registered_identity=request.registered_identity,
        )


@pytest.mark.parametrize(
    "residual", ["claim", "ledger", "claim_staging", "ledger_staging"]
)
def test_any_acquisition_residue_permanently_blocks_forecast_and_reveal(
    tmp_path: Path, residual: str
) -> None:
    calls: list[tuple[str, str]] = []
    request = _request(
        tmp_path,
        [(44, 45, 46, 47, 48, 49), (38, 39, 40, 41, 42, 43)],
        calls=calls,
    )
    path = getattr(V11ArtifactPaths.in_directory(tmp_path), residual)
    path.write_bytes(b"residual\n" if residual != "ledger" else b"")

    with pytest.raises(V11DiagnosticError, match="already exists"):
        run_v11_historical(request)

    assert calls == []


def test_acquisition_ledger_link_fault_rolls_back_before_claim_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    request = _request(
        tmp_path,
        [(44, 45, 46, 47, 48, 49), (38, 39, 40, 41, 42, 43)],
    )
    original_link = diagnostics.os.link

    def fail_ledger_link(source: Path, destination: Path) -> None:
        if Path(destination) == V11ArtifactPaths.in_directory(tmp_path).ledger:
            raise OSError("synthetic ledger hardlink failure")
        original_link(source, destination)

    monkeypatch.setattr(diagnostics.os, "link", fail_ledger_link)

    with pytest.raises(OSError, match="ledger hardlink failure"):
        run_v11_historical(request)

    paths = V11ArtifactPaths.in_directory(tmp_path)
    assert not any(path.exists() for path in paths.all_normal_paths())


@pytest.mark.parametrize(
    "fault", ["claim_write", "claim_post_fsync", "claim_hash", "claimed_append"]
)
def test_acquisition_precommit_faults_leave_no_reusable_partial_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    calls: list[tuple[str, str]] = []
    request = _request(
        tmp_path,
        [(44, 45, 46, 47, 48, 49), (38, 39, 40, 41, 42, 43)],
        calls=calls,
    )
    paths = V11ArtifactPaths.in_directory(tmp_path)
    if fault == "claim_write":
        original_write = diagnostics._write_staging

        def fail_claim_write(path: Path, payload: bytes) -> tuple[int, int]:
            if path == paths.claim_staging:
                raise OSError(f"synthetic {fault}")
            return original_write(path, payload)

        monkeypatch.setattr(diagnostics, "_write_staging", fail_claim_write)
    elif fault == "claim_post_fsync":
        original_directory_fsync = diagnostics._directory_fsync
        failed_once = False

        def fail_claim_parent_fsync(path: Path) -> None:
            nonlocal failed_once
            if path == tmp_path and not failed_once:
                failed_once = True
                raise OSError("synthetic claim_post_fsync")
            original_directory_fsync(path)

        monkeypatch.setattr(diagnostics, "_directory_fsync", fail_claim_parent_fsync)
    elif fault == "claim_hash":
        original_hash = diagnostics._file_sha256

        def wrong_claim_hash(path: Path) -> str:
            return "0" * 64 if path == paths.claim_staging else original_hash(path)

        monkeypatch.setattr(diagnostics, "_file_sha256", wrong_claim_hash)
    else:
        original_append = diagnostics.HashChainLedger.append

        def fail_claimed(
            ledger: diagnostics.HashChainLedger, event_type: str, payload: dict
        ) -> dict:
            if event_type == "claimed":
                raise OSError("synthetic claimed append")
            return original_append(ledger, event_type, payload)

        monkeypatch.setattr(diagnostics.HashChainLedger, "append", fail_claimed)

    with pytest.raises((OSError, V11DiagnosticError)):
        run_v11_historical(request)

    assert calls == []
    assert not any(path.exists() for path in paths.all_normal_paths())


def test_losing_concurrent_acquisition_never_deletes_winner_stages_or_finals(
    tmp_path: Path,
) -> None:
    request = _request(
        tmp_path,
        [(44, 45, 46, 47, 48, 49), (38, 39, 40, 41, 42, 43)],
    )
    paths = V11ArtifactPaths.in_directory(tmp_path)
    base_preflight = request.preflight
    winner_claim = b"winner-claim-stage\n"
    winner_ledger = b"winner-ledger-stage\n"

    def racing_preflight() -> dict:
        paths.claim_staging.write_bytes(winner_claim)
        paths.ledger_staging.write_bytes(winner_ledger)
        diagnostics.os.link(paths.claim_staging, paths.claim)
        diagnostics.os.link(paths.ledger_staging, paths.ledger)
        return dict(base_preflight())

    values = dict(request.__dict__)
    values["preflight"] = racing_preflight

    with pytest.raises(V11DiagnosticError, match="already exists"):
        run_v11_historical(V11DiagnosticRequest(**values))

    assert paths.claim_staging.read_bytes() == winner_claim
    assert paths.claim.read_bytes() == winner_claim
    assert paths.ledger_staging.read_bytes() == winner_ledger
    assert paths.ledger.read_bytes() == winner_ledger
    assert paths.claim_staging.stat().st_ino == paths.claim.stat().st_ino
    assert paths.ledger_staging.stat().st_ino == paths.ledger.stat().st_ino


@pytest.mark.parametrize("role", ["claim", "ledger"])
def test_acquisition_rejects_foreign_stage_swap_before_link_without_forecast(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    role: str,
) -> None:
    calls: list[tuple[str, str]] = []
    request = _request(
        tmp_path,
        [(44, 45, 46, 47, 48, 49), (38, 39, 40, 41, 42, 43)],
        calls=calls,
    )
    paths = V11ArtifactPaths.in_directory(tmp_path)
    target_stage = paths.claim_staging if role == "claim" else paths.ledger_staging
    target_final = paths.claim if role == "claim" else paths.ledger
    foreign = f"foreign-{role}-stage\n".encode()
    original_link = diagnostics.os.link

    def swap_before_link(source: Path, destination: Path) -> None:
        source_path = Path(source)
        destination_path = Path(destination)
        if destination_path == target_final:
            source_path.unlink()
            source_path.write_bytes(foreign)
        original_link(source_path, destination_path)

    monkeypatch.setattr(diagnostics.os, "link", swap_before_link)

    with pytest.raises(V11DiagnosticError):
        run_v11_historical(request)

    assert calls == []
    assert target_stage.read_bytes() == foreign
    assert target_final.read_bytes() == foreign
    assert target_stage.stat().st_ino == target_final.stat().st_ino
    failure = json.loads(paths.acquisition_failure.read_bytes())
    assert failure["status"] == "consumed_archive_acquisition_failure"
    assert failure["rollback_failures"]


def test_acquisition_rejects_ledger_stage_swap_before_identity_capture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, str]] = []
    request = _request(
        tmp_path,
        [(44, 45, 46, 47, 48, 49), (38, 39, 40, 41, 42, 43)],
        calls=calls,
    )
    paths = V11ArtifactPaths.in_directory(tmp_path)
    foreign = b"foreign-ledger-stage\n"
    original_create = diagnostics.HashChainLedger.create

    def create_then_swap(
        cls: type[diagnostics.HashChainLedger], path: Path
    ) -> diagnostics.HashChainLedger:
        del cls
        ledger = original_create(path)
        Path(path).unlink()
        Path(path).write_bytes(foreign)
        return ledger

    monkeypatch.setattr(
        diagnostics.HashChainLedger, "create", classmethod(create_then_swap)
    )

    with pytest.raises(V11DiagnosticError):
        run_v11_historical(request)

    assert calls == []
    assert paths.ledger_staging.read_bytes() == foreign
    assert paths.ledger.read_bytes() == foreign
    failure = json.loads(paths.acquisition_failure.read_bytes())
    assert failure["status"] == "consumed_archive_acquisition_failure"


def test_acquisition_cleanup_failure_is_structured_bound_and_secret_free(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, str]] = []
    request = _request(
        tmp_path,
        [(44, 45, 46, 47, 48, 49), (38, 39, 40, 41, 42, 43)],
        calls=calls,
    )
    paths = V11ArtifactPaths.in_directory(tmp_path)
    original_unlink_owned = diagnostics._unlink_owned_path
    failed_once = False

    def fail_claim_stage_cleanup(path: Path, identity: tuple[int, int]) -> None:
        nonlocal failed_once
        if path == paths.claim_staging and not failed_once:
            failed_once = True
            raise OSError("SECRET ACQUISITION CLEANUP MESSAGE")
        original_unlink_owned(path, identity)

    monkeypatch.setattr(diagnostics, "_unlink_owned_path", fail_claim_stage_cleanup)

    with pytest.raises(V11DiagnosticError, match="acquisition cleanup"):
        run_v11_historical(request)

    assert calls == []
    events = verify_hash_chain_ledger(paths.ledger)
    assert [event["event_type"] for event in events] == [
        "claimed",
        "preflight_passed",
        "acquisition_cleanup_failed",
        "failed",
    ]
    cleanup = events[2]["payload"]["acquisition_cleanup"]

    assert cleanup["schema_version"] == 1
    assert cleanup["phase"] == "post_claim_commit_cleanup"
    assert [item["role"] for item in cleanup["stage_results"]] == [
        "claim",
        "ledger",
    ]
    claim_result = cleanup["stage_results"][0]
    assert claim_result["path"] == paths.claim_staging.name
    assert claim_result["outcome"] == "unlink_failed"
    assert claim_result["error_type"] == "OSError"
    assert claim_result["content_binding"] == "mutable_final_bytes"
    assert claim_result["content_sha256"] is None
    assert paths.claim_staging.read_bytes() == paths.claim.read_bytes()
    assert "owned_identity" not in claim_result
    assert diagnostics._acquisition_operational_warnings(cleanup) == [
        "acquisition_cleanup_failed:" + diagnostics.canonical_sha256(cleanup)
    ]
    assert b"SECRET ACQUISITION CLEANUP MESSAGE" not in paths.ledger.read_bytes()


def test_acquisition_parent_cleanup_oserror_subclass_is_exactly_replayable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _request(
        tmp_path,
        [(44, 45, 46, 47, 48, 49), (38, 39, 40, 41, 42, 43)],
    )
    paths = V11ArtifactPaths.in_directory(tmp_path)
    original_fsync = diagnostics._directory_fsync
    calls = 0

    def fail_cleanup_parent_once(directory: Path) -> None:
        nonlocal calls
        if directory == tmp_path:
            calls += 1
            if calls == 5:
                raise PermissionError("SECRET cleanup parent permission detail")
        original_fsync(directory)

    monkeypatch.setattr(diagnostics, "_directory_fsync", fail_cleanup_parent_once)

    with pytest.raises(V11DiagnosticError, match="acquisition cleanup"):
        run_v11_historical(request)
    events = validate_v11_ledger_state_machine(
        paths.ledger,
        expected_targets=2,
        source_blob_resolver=request.source_blob_resolver,
        registered_identity=request.registered_identity,
    )
    cleanup = events[2]["payload"]["acquisition_cleanup"]

    assert events[2]["event_type"] == "acquisition_cleanup_failed"
    assert events[3]["event_type"] == "failed"
    assert cleanup["parent_fsync"]["outcome"] == "failed"
    assert cleanup["parent_fsync"]["error_type"] == "OSError"
    assert b"SECRET cleanup parent permission detail" not in paths.ledger.read_bytes()


def test_acquisition_cleanup_file_disappearing_during_unlink_counts_as_removed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _request(
        tmp_path,
        [(44, 45, 46, 47, 48, 49), (38, 39, 40, 41, 42, 43)],
    )
    paths = V11ArtifactPaths.in_directory(tmp_path)
    original_unlink_owned = diagnostics._unlink_owned_path
    raced = False

    def disappear_then_report_missing(path: Path, identity: tuple[int, int]) -> None:
        nonlocal raced
        if path == paths.claim_staging and not raced:
            raced = True
            Path.unlink(path)
            raise FileNotFoundError("synthetic already removed")
        original_unlink_owned(path, identity)

    monkeypatch.setattr(
        diagnostics, "_unlink_owned_path", disappear_then_report_missing
    )

    result = run_v11_historical(request)
    events = validate_v11_ledger_state_machine(
        paths.ledger,
        expected_targets=2,
        source_blob_resolver=request.source_blob_resolver,
        registered_identity=request.registered_identity,
    )
    scoring = next(
        event for event in events if event["event_type"] == "scoring_started"
    )["payload"]

    assert result["status"] == "published"
    assert scoring["acquisition_cleanup"]["stage_results"][0]["outcome"] == ("removed")
    assert scoring["acquisition_warnings"] == []


def test_acquisition_cleanup_receipt_coordinated_rechain_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _request(
        tmp_path,
        [(44, 45, 46, 47, 48, 49), (38, 39, 40, 41, 42, 43)],
    )
    paths = V11ArtifactPaths.in_directory(tmp_path)
    original_unlink_owned = diagnostics._unlink_owned_path
    failed_once = False

    def fail_claim_stage_cleanup(path: Path, identity: tuple[int, int]) -> None:
        nonlocal failed_once
        if path == paths.claim_staging and not failed_once:
            failed_once = True
            raise OSError("synthetic cleanup failure")
        original_unlink_owned(path, identity)

    monkeypatch.setattr(diagnostics, "_unlink_owned_path", fail_claim_stage_cleanup)
    with pytest.raises(V11DiagnosticError, match="acquisition cleanup"):
        run_v11_historical(request)
    events = verify_hash_chain_ledger(paths.ledger)
    cleanup = events[2]["payload"]["acquisition_cleanup"]
    assert cleanup["stage_results"][0]["error_type"] == "OSError"
    cleanup["stage_results"][0]["error_type"] = "PermissionError"
    _rewrite_chain(paths.ledger, events)

    with pytest.raises(V11DiagnosticError, match="cleanup outcome"):
        validate_v11_ledger_state_machine(
            paths.ledger,
            expected_targets=2,
            source_blob_resolver=request.source_blob_resolver,
            registered_identity=request.registered_identity,
        )


def test_clean_acquisition_rejects_coordinated_removed_to_unlink_failed_rewrite(
    tmp_path: Path,
) -> None:
    request = _request(
        tmp_path,
        [(44, 45, 46, 47, 48, 49), (38, 39, 40, 41, 42, 43)],
    )
    paths = V11ArtifactPaths.in_directory(tmp_path)
    run_v11_historical(request)
    events = verify_hash_chain_ledger(paths.ledger)
    scoring = next(
        event for event in events if event["event_type"] == "scoring_started"
    )["payload"]
    cleanup = scoring["acquisition_cleanup"]
    ledger_result = cleanup["stage_results"][1]
    assert ledger_result["outcome"] == "removed"
    ledger_result.update(
        outcome="unlink_failed",
        error_type="OSError",
        content_binding="mutable_final_bytes",
        content_sha256=None,
    )
    forged_warning = "acquisition_cleanup_failed:" + diagnostics.canonical_sha256(
        cleanup
    )
    scoring["acquisition_warnings"] = [forged_warning]
    _rewrite_chain(paths.ledger, events)
    events = verify_hash_chain_ledger(paths.ledger)

    report = json.loads(paths.report_json.read_bytes())
    report["operational_warnings"] = [forged_warning]
    report["ledger_head_before_publication"] = next(
        event for event in events if event["event_type"] == "publication_started"
    )["event_sha256"]
    report_bytes = (
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
            allow_nan=False,
            ensure_ascii=False,
        ).encode("utf-8")
        + b"\n"
    )
    markdown_bytes = diagnostics._render_markdown(report).encode("utf-8")
    paths.report_json.write_bytes(report_bytes)
    paths.report_markdown.write_bytes(markdown_bytes)
    terminal = next(event for event in events if event["event_type"] == "published")
    terminal["payload"]["operational_warnings"] = [forged_warning]
    terminal["payload"]["json_sha256"] = hashlib.sha256(report_bytes).hexdigest()
    terminal["payload"]["markdown_sha256"] = hashlib.sha256(markdown_bytes).hexdigest()
    _rewrite_chain(paths.ledger, events)
    paths.ledger_staging.write_bytes(paths.ledger.read_bytes())

    with pytest.raises(V11DiagnosticError, match="clean acquisition cleanup"):
        validate_v11_ledger_state_machine(
            paths.ledger,
            expected_targets=2,
            source_blob_resolver=request.source_blob_resolver,
            registered_identity=request.registered_identity,
        )


@pytest.mark.parametrize(
    "fault",
    [
        "claim_unlink_failed",
        "ledger_unlink_failed",
        "ledger_foreign_inode_refused",
        "parent_fsync_failed",
    ],
)
def test_non_clean_acquisition_cleanup_archives_before_scoring_and_replays_after_relocation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault: str,
) -> None:
    original = tmp_path / "original"
    relocated = tmp_path / "relocated"
    calls: list[tuple[str, str]] = []
    request = _request(
        original,
        [(44, 45, 46, 47, 48, 49), (38, 39, 40, 41, 42, 43)],
        calls=calls,
    )
    paths = V11ArtifactPaths.in_directory(original)
    if fault == "parent_fsync_failed":
        original_directory_fsync = diagnostics._directory_fsync
        fsync_calls = 0

        def fail_cleanup_parent(directory: Path) -> None:
            nonlocal fsync_calls
            if directory == original:
                fsync_calls += 1
                if fsync_calls == 5:
                    raise OSError("SECRET synthetic cleanup parent fsync failure")
            original_directory_fsync(directory)

        monkeypatch.setattr(diagnostics, "_directory_fsync", fail_cleanup_parent)
    else:
        original_unlink_owned = diagnostics._unlink_owned_path
        faulted = False

        def fail_stage_cleanup(path: Path, identity: tuple[int, int]) -> None:
            nonlocal faulted
            target = (
                paths.claim_staging
                if fault == "claim_unlink_failed"
                else paths.ledger_staging
            )
            if path == target and not faulted:
                faulted = True
                if fault == "ledger_foreign_inode_refused":
                    path.unlink()
                    path.write_bytes(b"foreign ledger staging evidence\n")
                    original_unlink_owned(path, identity)
                    raise AssertionError("foreign inode must be refused")
                raise OSError("SECRET synthetic stage cleanup failure")
            original_unlink_owned(path, identity)

        monkeypatch.setattr(diagnostics, "_unlink_owned_path", fail_stage_cleanup)

    with pytest.raises(V11DiagnosticError, match="acquisition cleanup"):
        run_v11_historical(request)

    assert calls == []
    events = verify_hash_chain_ledger(paths.ledger)
    assert [event["event_type"] for event in events] == [
        "claimed",
        "preflight_passed",
        "acquisition_cleanup_failed",
        "failed",
    ]
    assert set(events[2]["payload"]) == {"acquisition_cleanup"}
    cleanup = events[2]["payload"]["acquisition_cleanup"]
    assert diagnostics._acquisition_operational_warnings(cleanup)
    assert events[3]["payload"] == {
        "error_type": "V11DiagnosticError",
        "error_message": "V11 acquisition cleanup was not clean",
        "status": "consumed_archive_no_rerun",
        "last_frozen_target_date": None,
        "last_frozen_forecast_sha256": None,
    }
    assert b"SECRET" not in paths.ledger.read_bytes()
    validate_v11_ledger_state_machine(
        paths.ledger,
        expected_targets=2,
        source_blob_resolver=request.source_blob_resolver,
        registered_identity=request.registered_identity,
    )

    shutil.copytree(original, relocated)
    relocated_paths = V11ArtifactPaths.in_directory(relocated)
    validate_v11_ledger_state_machine(
        relocated_paths.ledger,
        expected_targets=2,
        source_blob_resolver=request.source_blob_resolver,
        registered_identity=request.registered_identity,
    )


@pytest.mark.parametrize(
    "attack",
    ["missing_failed", "scoring_after_cleanup", "event_after_failed", "clean_receipt"],
)
def test_failed_acquisition_cleanup_event_requires_non_clean_evidence_and_immediate_terminal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    attack: str,
) -> None:
    request = _request(
        tmp_path,
        [(44, 45, 46, 47, 48, 49), (38, 39, 40, 41, 42, 43)],
    )
    paths = V11ArtifactPaths.in_directory(tmp_path)
    original_unlink_owned = diagnostics._unlink_owned_path
    faulted = False

    def fail_claim_stage_cleanup(path: Path, identity: tuple[int, int]) -> None:
        nonlocal faulted
        if path == paths.claim_staging and not faulted:
            faulted = True
            raise OSError("synthetic claim stage cleanup failure")
        original_unlink_owned(path, identity)

    monkeypatch.setattr(diagnostics, "_unlink_owned_path", fail_claim_stage_cleanup)
    with pytest.raises(V11DiagnosticError, match="acquisition cleanup"):
        run_v11_historical(request)
    events = verify_hash_chain_ledger(paths.ledger)
    if attack == "missing_failed":
        events.pop()
    elif attack == "scoring_after_cleanup":
        events.insert(3, {"event_type": "scoring_started", "payload": {}})
    elif attack == "event_after_failed":
        events.append({"event_type": "forged_post_terminal", "payload": {}})
    else:
        claim_result = events[2]["payload"]["acquisition_cleanup"]["stage_results"][0]
        claim_result.update(
            outcome="removed",
            error_type=None,
            content_binding=None,
            content_sha256=None,
        )
        paths.claim_staging.unlink()
    _rewrite_chain(paths.ledger, events)

    with pytest.raises(V11DiagnosticError, match="cleanup"):
        validate_v11_ledger_state_machine(
            paths.ledger,
            expected_targets=2,
            source_blob_resolver=request.source_blob_resolver,
            registered_identity=request.registered_identity,
        )


def test_first_post_claim_append_fault_is_durably_archived(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    request = _request(
        tmp_path,
        [(44, 45, 46, 47, 48, 49), (38, 39, 40, 41, 42, 43)],
    )
    original_append = diagnostics.HashChainLedger.append
    failed_once = False

    def fail_preflight_once(
        ledger: diagnostics.HashChainLedger, event_type: str, payload: dict
    ) -> dict:
        nonlocal failed_once
        if event_type == "preflight_passed" and not failed_once:
            failed_once = True
            raise OSError("synthetic post-claim append fault")
        return original_append(ledger, event_type, payload)

    monkeypatch.setattr(diagnostics.HashChainLedger, "append", fail_preflight_once)

    with pytest.raises(OSError, match="post-claim append fault"):
        run_v11_historical(request)

    paths = V11ArtifactPaths.in_directory(tmp_path)
    events = validate_v11_ledger_state_machine(
        paths.ledger,
        expected_targets=2,
        source_blob_resolver=request.source_blob_resolver,
        registered_identity=request.registered_identity,
    )
    assert paths.claim.is_file()
    assert [event["event_type"] for event in events] == ["claimed", "failed"]


def test_pair_publication_second_link_fault_rolls_back_owned_final(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = V11ArtifactPaths.in_directory(tmp_path)
    original_link = diagnostics.os.link
    calls = 0

    def fail_second_link(source: Path, destination: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("synthetic second hardlink failure")
        original_link(source, destination)

    monkeypatch.setattr(diagnostics.os, "link", fail_second_link)

    with pytest.raises(V11DiagnosticError, match="partial publication"):
        diagnostics._safe_publish_pair(paths, b"{}\n", b"# report\n")

    assert not paths.report_json.exists()
    assert not paths.report_markdown.exists()
    assert paths.report_json_staging.exists()
    assert paths.report_markdown_staging.exists()


def test_pair_publication_stage_cleanup_is_part_of_commit_and_rolls_back_finals(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = V11ArtifactPaths.in_directory(tmp_path)
    original_unlink = Path.unlink

    def fail_json_stage_cleanup(path: Path, *args, **kwargs) -> None:
        if path == paths.report_json_staging:
            raise OSError("synthetic committed cleanup failure")
        original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", fail_json_stage_cleanup)

    with pytest.raises(V11DiagnosticError, match="partial publication"):
        diagnostics._safe_publish_pair(paths, b"{}\n", b"# report\n")

    assert not paths.report_json.exists()
    assert not paths.report_markdown.exists()
    assert paths.report_json_staging.exists()


def test_pair_publication_second_stage_cleanup_fault_rolls_back_owned_finals(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = V11ArtifactPaths.in_directory(tmp_path)
    original_unlink = Path.unlink

    def fail_markdown_stage_cleanup(path: Path, *args, **kwargs) -> None:
        if path == paths.report_markdown_staging:
            raise OSError("synthetic second stage cleanup failure")
        original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", fail_markdown_stage_cleanup)

    with pytest.raises(V11DiagnosticError, match="partial publication"):
        diagnostics._safe_publish_pair(paths, b"{}\n", b"# report\n")

    assert not paths.report_json.exists()
    assert not paths.report_markdown.exists()
    assert not paths.report_json_staging.exists()
    assert paths.report_markdown_staging.exists()


def test_report_cleanup_fault_archives_before_publication_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    request = _request(
        tmp_path,
        [(44, 45, 46, 47, 48, 49), (38, 39, 40, 41, 42, 43)],
    )
    paths = V11ArtifactPaths.in_directory(tmp_path)
    original_unlink = Path.unlink

    def fail_report_stage_cleanup(path: Path, *args, **kwargs) -> None:
        if path == paths.report_json_staging:
            raise OSError("synthetic committed report cleanup failure")
        original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", fail_report_stage_cleanup)

    with pytest.raises(V11DiagnosticError, match="partial publication"):
        run_v11_historical(request)
    events = validate_v11_ledger_state_machine(
        paths.ledger,
        expected_targets=2,
        source_blob_resolver=request.source_blob_resolver,
        registered_identity=request.registered_identity,
    )

    assert not paths.report_json.exists()
    assert not paths.report_markdown.exists()
    assert events[-1]["event_type"] == "failed"
    assert events[-1]["payload"]["status"] == "consumed_archive_no_rerun"


def test_pair_publication_final_fsync_fault_rolls_back_both_finals(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = V11ArtifactPaths.in_directory(tmp_path)
    original_fsync = diagnostics._directory_fsync
    calls = 0

    def fail_commit_fsync(directory: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 3:
            raise OSError("synthetic final parent fsync failure")
        original_fsync(directory)

    monkeypatch.setattr(diagnostics, "_directory_fsync", fail_commit_fsync)

    with pytest.raises(V11DiagnosticError, match="partial publication"):
        diagnostics._safe_publish_pair(paths, b"{}\n", b"# report\n")

    assert not paths.report_json.exists()
    assert not paths.report_markdown.exists()


def test_pair_publication_raced_away_stages_still_rollback_finals_on_commit_fsync(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = V11ArtifactPaths.in_directory(tmp_path)
    original_unlink_owned = diagnostics._unlink_owned_path
    original_fsync = diagnostics._directory_fsync
    fsync_calls = 0

    def race_stage_away(path: Path, identity: tuple[int, int]) -> None:
        if path in {paths.report_json_staging, paths.report_markdown_staging}:
            Path.unlink(path)
            return
        original_unlink_owned(path, identity)

    def fail_commit_fsync(directory: Path) -> None:
        nonlocal fsync_calls
        fsync_calls += 1
        if fsync_calls == 3:
            raise OSError("synthetic commit fsync after raced stages")
        original_fsync(directory)

    monkeypatch.setattr(diagnostics, "_unlink_owned_path", race_stage_away)
    monkeypatch.setattr(diagnostics, "_directory_fsync", fail_commit_fsync)

    with pytest.raises(V11DiagnosticError, match="partial publication"):
        diagnostics._safe_publish_pair(paths, b"{}\n", b"# report\n")

    assert not paths.report_json.exists()
    assert not paths.report_markdown.exists()


def test_pair_publication_rollback_fsync_failure_is_explicit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = V11ArtifactPaths.in_directory(tmp_path)
    original_fsync = diagnostics._directory_fsync
    calls = 0

    def fail_commit_and_rollback_fsync(directory: Path) -> None:
        nonlocal calls
        calls += 1
        if calls >= 3:
            raise OSError(f"synthetic publication fsync failure {calls}")
        original_fsync(directory)

    monkeypatch.setattr(diagnostics, "_directory_fsync", fail_commit_and_rollback_fsync)

    with pytest.raises(V11DiagnosticError, match="rollback_failed.*parent_fsync"):
        diagnostics._safe_publish_pair(paths, b"{}\n", b"# report\n")


def test_pair_publication_foreign_second_final_survives_race(
    tmp_path: Path,
) -> None:
    paths = V11ArtifactPaths.in_directory(tmp_path)
    paths.report_markdown.write_bytes(b"foreign\n")

    with pytest.raises(V11DiagnosticError, match="partial publication"):
        diagnostics._safe_publish_pair(paths, b"{}\n", b"# report\n")

    assert not paths.report_json.exists()
    assert paths.report_markdown.read_bytes() == b"foreign\n"


def test_pair_publication_rejects_stage_swap_before_link_without_linking_second_final(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = V11ArtifactPaths.in_directory(tmp_path)
    original_link = diagnostics.os.link
    destinations: list[Path] = []

    def swap_first_stage_before_link(source: Path, destination: Path) -> None:
        source_path = Path(source)
        destination_path = Path(destination)
        destinations.append(destination_path)
        if destination_path == paths.report_json:
            source_path.unlink()
            source_path.write_bytes(b"foreign-stage\n")
        original_link(source_path, destination_path)

    monkeypatch.setattr(diagnostics.os, "link", swap_first_stage_before_link)

    with pytest.raises(V11DiagnosticError, match="rollback_failed"):
        diagnostics._safe_publish_pair(paths, b"{}\n", b"# report\n")

    assert destinations == [paths.report_json]
    assert paths.report_json.read_bytes() == b"foreign-stage\n"
    assert not paths.report_markdown.exists()


def test_bundle_publication_link_fault_retains_stage_without_final(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    final = tmp_path / "historical-6of6-candidate__synthetic.json"
    monkeypatch.setattr(
        diagnostics.os,
        "link",
        lambda _source, _destination: (_ for _ in ()).throw(
            OSError("synthetic bundle link failure")
        ),
    )

    with pytest.raises(V11DiagnosticError, match="partial bundle"):
        diagnostics._safe_publish_bundle(final, {"status": "synthetic"})

    assert not final.exists()
    assert final.with_name(f".{final.name}.staging").exists()


def test_bundle_publication_rejects_foreign_stage_swap_before_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    final = tmp_path / "historical-6of6-candidate__synthetic.json"
    staging = final.with_name(f".{final.name}.staging")
    original_link = diagnostics.os.link

    def swap_stage_before_link(source: Path, destination: Path) -> None:
        source_path = Path(source)
        source_path.unlink()
        source_path.write_bytes(b"foreign-stage\n")
        original_link(source_path, destination)

    monkeypatch.setattr(diagnostics.os, "link", swap_stage_before_link)

    with pytest.raises(V11DiagnosticError, match="rollback_failed"):
        diagnostics._safe_publish_bundle(final, {"status": "synthetic"})

    assert staging.read_bytes() == b"foreign-stage\n"
    assert final.read_bytes() == b"foreign-stage\n"


def test_bundle_raced_away_stage_still_rolls_back_final_on_commit_fsync(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    final = tmp_path / "historical-6of6-candidate__synthetic.json"
    staging = final.with_name(f".{final.name}.staging")
    original_unlink_owned = diagnostics._unlink_owned_path
    original_fsync = diagnostics._directory_fsync
    calls = 0

    def race_stage_away(path: Path, identity: tuple[int, int]) -> None:
        if path == staging:
            Path.unlink(path)
            return
        original_unlink_owned(path, identity)

    def fail_commit_fsync(directory: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("synthetic bundle commit fsync")
        original_fsync(directory)

    monkeypatch.setattr(diagnostics, "_unlink_owned_path", race_stage_away)
    monkeypatch.setattr(diagnostics, "_directory_fsync", fail_commit_fsync)

    with pytest.raises(V11DiagnosticError, match="partial bundle"):
        diagnostics._safe_publish_bundle(final, {"status": "synthetic"})

    assert not final.exists()
    assert not staging.exists()


def test_bundle_stage_cleanup_is_part_of_commit_and_rolls_back_final(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    final = tmp_path / "historical-6of6-candidate__synthetic.json"
    staging = final.with_name(f".{final.name}.staging")
    original_unlink = Path.unlink

    def fail_stage_cleanup(path: Path, *args, **kwargs) -> None:
        if path == staging:
            raise OSError("synthetic bundle cleanup failure")
        original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", fail_stage_cleanup)

    with pytest.raises(V11DiagnosticError, match="partial bundle"):
        diagnostics._safe_publish_bundle(final, {"status": "synthetic"})

    assert not final.exists()
    assert staging.exists()


def test_breakthrough_cleanup_fault_archives_before_bundle_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    request = _request(tmp_path, [(1, 2, 3, 4, 5, 6)])
    original_unlink = Path.unlink

    def fail_breakthrough_stage_cleanup(path: Path, *args, **kwargs) -> None:
        if path.name.startswith(".historical-6of6-candidate__"):
            raise OSError("synthetic committed bundle cleanup failure")
        original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", fail_breakthrough_stage_cleanup)

    with pytest.raises(V11DiagnosticError, match="partial bundle"):
        run_v11_historical(request)
    paths = V11ArtifactPaths.in_directory(tmp_path)
    events = validate_v11_ledger_state_machine(
        paths.ledger,
        expected_targets=1,
        source_blob_resolver=request.source_blob_resolver,
        registered_identity=request.registered_identity,
    )

    assert not any(tmp_path.glob("historical-6of6-candidate__*.json"))
    assert events[-1]["event_type"] == "failed"
    assert events[-1]["payload"]["status"] == "consumed_archive_no_rerun"


@pytest.mark.parametrize("mode", ["false", "exception"])
def test_progress_notification_has_durable_receipt_and_operational_only_warning(
    tmp_path: Path, mode: str
) -> None:
    request = _request(
        tmp_path,
        [(1, 2, 3, 4, 5, 7), (38, 39, 40, 41, 42, 43)],
    )

    def notifier(_subject: str, _body: str) -> bool:
        if mode == "exception":
            raise RuntimeError("SECRET MUST NOT BE PERSISTED")
        return False

    values = dict(request.__dict__)
    values["notifier"] = notifier
    result = run_v11_historical(V11DiagnosticRequest(**values))
    paths = V11ArtifactPaths.in_directory(tmp_path)
    events = verify_hash_chain_ledger(paths.ledger)
    progress = [
        event
        for event in events
        if event["event_type"]
        in {"progress_notification_outbox", "progress_notification_receipt"}
    ]

    assert [event["event_type"] for event in progress] == [
        "progress_notification_outbox",
        "progress_notification_receipt",
        "progress_notification_outbox",
        "progress_notification_receipt",
    ]
    assert all(
        event["payload"]["outcome"]
        == ("exception" if mode == "exception" else "returned_false")
        for event in progress[1::2]
    )
    assert result["report"]["operational_warnings"]
    assert result["report"]["historical_decision"]["gates"][
        diagnostics.SCIENTIFIC_GATE_NAMES[9]
    ]
    assert b"SECRET MUST NOT BE PERSISTED" not in paths.ledger.read_bytes()
    validate_v11_ledger_state_machine(
        paths.ledger,
        expected_targets=2,
        source_blob_resolver=request.source_blob_resolver,
        registered_identity=request.registered_identity,
    )


def test_breakthrough_audit_replays_after_target_and_future_counterfactual_rows(
    tmp_path: Path,
) -> None:
    blob = (
        "draw_date,n1,n2,n3,n4,n5,n6,bonus\n"
        "2019-12-28,10,20,30,40,45,49,1\n"
        "2020-01-01,1,2,3,4,5,6,7\n"
        "2020-01-02,8,9,10,11,12,13,14\n"
    ).encode("ascii")

    def base_builder(history: tuple, target: date, prefix: str) -> V1BaseSnapshot:
        probabilities = (6.0 / 49.0,) * 49
        ranking = tuple(range(1, 50))
        return V1BaseSnapshot(
            target_date=target,
            history_draws=len(history),
            history_through=history[-1].draw_date,
            strict_prefix_sha256=prefix,
            probabilities=probabilities,
            ranking=ranking,
            top6=ranking[:6],
            top12=ranking[:12],
            top18=ranking[:18],
            final6=ranking[:6],
        )

    store = v11_cli.SealedCsvFoldStore(
        blob,
        expected_draw_count=3,
        expected_history_through=date(2020, 1, 2),
        target_start=date(2020, 1, 1),
        target_end=date(2020, 1, 1),
        first_half_end=date(2020, 1, 1),
        expected_target_count=1,
        expected_half_counts=(1, 0),
        base_builder=base_builder,
        random_builder=lambda _history, _target: {
            label: 6.0 / 49.0 for label in range(1, 50)
        },
    )
    scopes = (
        V11Scope("first", date(2020, 1, 1), date(2020, 1, 1), 1),
        V11Scope("second", date(2020, 1, 2), date(2020, 1, 2), 0),
    )
    registered_identity = _synthetic_registered_identity(
        blob,
        draw_count=3,
        history_through=date(2020, 1, 2),
        target_start=date(2020, 1, 1),
        target_end=date(2020, 1, 1),
        target_count=1,
        scopes=scopes,
    )

    def preflight() -> dict:
        store.bind_preflight_evidence(
            {
                "exact_head": "1" * 40,
                "remote_branch_head": "1" * 40,
                "registration_ancestor": True,
                "changed_paths_verified": True,
                "ci_required_checks_passed": True,
                "runtime_versions_verified": True,
                "registered_blob_sha256": hashlib.sha256(blob).hexdigest(),
                "configuration_sha256": "3" * 64,
                "source_commit": "2" * 40,
            }
        )
        return _synthetic_preflight_for_blob(
            blob,
            draw_count=3,
            history_through=date(2020, 1, 2),
            target_count=1,
            fixed_half_counts=(1, 0),
            registered_identity=registered_identity,
        )

    request = V11DiagnosticRequest(
        root=tmp_path,
        output_dir=tmp_path,
        code_commit="1" * 40,
        exact_command=diagnostics.registered_v11_command(registered_identity),
        targets=store.plans(),
        preflight=preflight,
        reference={},
        expected_target_count=1,
        stability_scopes=scopes,
        bootstrap_replicates=10,
        leakage_audit=store.leakage_audit,
        clock=_Clock(),
        source_blob_resolver=lambda _commit, _path: blob,
        registered_identity=registered_identity,
    )

    result = run_v11_historical(request)
    bundle = json.loads(Path(result["bundle_path"]).read_bytes())
    checks = {item["name"]: item for item in bundle["leakage_audit"]["checks"]}

    assert result["status"] == "historical_6of6_candidate_published"
    assert checks["claim"]["passed"] is True
    assert (
        checks["future_exclusion"]["evidence"]["all_four_model_payloads_unchanged"]
        is True
    )
    assert (
        checks["target_exclusion"]["evidence"]["counterfactual_suffix_differs"] is True
    )


@pytest.mark.parametrize("mode", ["false", "exception"])
def test_terminal_notification_failure_cannot_change_scientific_terminal(
    tmp_path: Path, mode: str
) -> None:
    request = _request(tmp_path, [(1, 2, 3, 4, 5, 6)])
    paths = V11ArtifactPaths.in_directory(tmp_path)

    def notifier(_subject: str, _body: str) -> bool:
        events_before = verify_hash_chain_ledger(paths.ledger)
        assert events_before[-1]["event_type"] == "historical_6of6_candidate_published"
        if mode == "exception":
            raise RuntimeError("secret terminal failure")
        return False

    values = dict(request.__dict__)
    values["notifier"] = notifier
    result = run_v11_historical(V11DiagnosticRequest(**values))
    events_after = verify_hash_chain_ledger(paths.ledger)

    assert events_after[-2]["event_type"] == "historical_6of6_candidate_published"
    assert events_after[-1]["event_type"] == "terminal_notification_receipt"
    assert (
        events_after[-1]["payload"]["scientific_terminal_event_sha256"]
        == (events_after[-2]["event_sha256"])
    )
    assert all(event["event_type"] != "failed" for event in events_after)
    assert result["notification_dispatched_after_terminal"] is False
    assert result["notification_receipt"]["outcome"] == (
        "exception" if mode == "exception" else "returned_false"
    )
    assert b"secret terminal failure" not in paths.ledger.read_bytes()


def test_terminal_receipt_append_fault_leaves_auditable_pending_scientific_terminal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    request = _request(tmp_path, [(1, 2, 3, 4, 5, 6)])
    paths = V11ArtifactPaths.in_directory(tmp_path)
    original_append = diagnostics.HashChainLedger.append

    def fail_terminal_receipt(
        ledger: diagnostics.HashChainLedger, event_type: str, payload: dict
    ) -> dict:
        if event_type == "terminal_notification_receipt":
            raise OSError("synthetic terminal receipt fsync failure")
        return original_append(ledger, event_type, payload)

    monkeypatch.setattr(diagnostics.HashChainLedger, "append", fail_terminal_receipt)

    with pytest.raises(OSError, match="terminal receipt fsync failure"):
        run_v11_historical(request)

    events = verify_hash_chain_ledger(paths.ledger)
    assert events[-1]["event_type"] == "historical_6of6_candidate_published"
    assert all(event["event_type"] != "failed" for event in events)
    validate_v11_ledger_state_machine(
        paths.ledger,
        expected_targets=1,
        require_terminal_notification_receipt=False,
        source_blob_resolver=request.source_blob_resolver,
        registered_identity=request.registered_identity,
    )
    with pytest.raises(V11DiagnosticError, match="receipt"):
        validate_v11_ledger_state_machine(
            paths.ledger,
            expected_targets=1,
            source_blob_resolver=request.source_blob_resolver,
            registered_identity=request.registered_identity,
        )


@pytest.mark.parametrize("fault", ["partial_write", "flush", "fsync"])
@pytest.mark.parametrize("terminal_kind", ["exact_6of6", "normal_published"])
def test_terminal_receipt_real_io_fault_restores_pending_scientific_terminal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault: str,
    terminal_kind: str,
) -> None:
    if terminal_kind == "exact_6of6":
        request = _request(tmp_path, [(1, 2, 3, 4, 5, 6)])
        expected_terminal = "historical_6of6_candidate_published"
    else:
        original_decision = diagnostics.v11_historical_decision

        def force_scientific_pass(**kwargs) -> dict:
            decision = original_decision(**kwargs)
            decision["gates"] = {
                name: True for name in diagnostics.SCIENTIFIC_GATE_NAMES
            }
            decision["all_scientific_gates_passed"] = True
            decision["decision"] = "eligible_for_separate_reviewed_shadow_decision"
            return decision

        monkeypatch.setattr(
            diagnostics, "v11_historical_decision", force_scientific_pass
        )
        request = _request(
            tmp_path,
            [(44, 45, 46, 47, 48, 49), (38, 39, 40, 41, 42, 43)],
        )
        expected_terminal = "published"

    original_append = diagnostics.HashChainLedger.append
    original_fsync = diagnostics.os.fsync
    armed_wrapper: _OneShotLedgerIoFault | None = None

    def arm_real_io_fault(
        ledger: diagnostics.HashChainLedger, event_type: str, payload: dict
    ) -> dict:
        nonlocal armed_wrapper
        if event_type == "terminal_notification_receipt" and armed_wrapper is None:
            armed_wrapper = _OneShotLedgerIoFault(ledger._handle, fault)
            ledger._handle = armed_wrapper
        return original_append(ledger, event_type, payload)

    def fail_armed_fsync(descriptor: int) -> None:
        if (
            fault == "fsync"
            and armed_wrapper is not None
            and descriptor == armed_wrapper.fileno()
            and not armed_wrapper.fired
        ):
            armed_wrapper.fired = True
            raise OSError("synthetic terminal receipt fsync failure")
        original_fsync(descriptor)

    monkeypatch.setattr(diagnostics.HashChainLedger, "append", arm_real_io_fault)
    monkeypatch.setattr(diagnostics.os, "fsync", fail_armed_fsync)

    with pytest.raises(V11DiagnosticError, match="append rolled back"):
        run_v11_historical(request)

    paths = V11ArtifactPaths.in_directory(tmp_path)
    events = verify_hash_chain_ledger(paths.ledger)
    assert events[-1]["event_type"] == expected_terminal
    assert all(event["event_type"] != "failed" for event in events)
    validate_v11_ledger_state_machine(
        paths.ledger,
        expected_targets=request.expected_target_count,
        require_terminal_notification_receipt=False,
        source_blob_resolver=request.source_blob_resolver,
        registered_identity=request.registered_identity,
    )


@pytest.mark.parametrize("attack", ["terminal_hash", "idempotency_key", "duplicate"])
def test_terminal_notification_receipt_rechain_attacks_are_rejected(
    tmp_path: Path, attack: str
) -> None:
    request = _request(tmp_path, [(1, 2, 3, 4, 5, 6)])
    paths = V11ArtifactPaths.in_directory(tmp_path)
    run_v11_historical(request)
    events = verify_hash_chain_ledger(paths.ledger)
    receipt = events[-1]
    assert receipt["event_type"] == "terminal_notification_receipt"
    if attack == "terminal_hash":
        receipt["payload"]["scientific_terminal_event_sha256"] = "9" * 64
    elif attack == "idempotency_key":
        receipt["payload"]["receipt"]["notification_idempotency_key"] = "9" * 64
    else:
        events.append(deepcopy(receipt))
    _rewrite_chain(paths.ledger, events)

    with pytest.raises(V11DiagnosticError, match="receipt"):
        validate_v11_ledger_state_machine(
            paths.ledger,
            expected_targets=1,
            source_blob_resolver=request.source_blob_resolver,
            registered_identity=request.registered_identity,
        )


@pytest.mark.parametrize("mode", ["false", "exception"])
def test_normal_published_terminal_dispatch_has_durable_operational_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
) -> None:
    original_decision = diagnostics.v11_historical_decision

    def force_scientific_pass(**kwargs) -> dict:
        decision = original_decision(**kwargs)
        decision["gates"] = {name: True for name in diagnostics.SCIENTIFIC_GATE_NAMES}
        decision["all_scientific_gates_passed"] = True
        decision["decision"] = "eligible_for_separate_reviewed_shadow_decision"
        return decision

    monkeypatch.setattr(diagnostics, "v11_historical_decision", force_scientific_pass)
    request = _request(
        tmp_path,
        [(44, 45, 46, 47, 48, 49), (38, 39, 40, 41, 42, 43)],
    )

    def notifier(_subject: str, _body: str) -> bool:
        events = verify_hash_chain_ledger(
            V11ArtifactPaths.in_directory(tmp_path).ledger
        )
        assert events[-1]["event_type"] == "published"
        if mode == "exception":
            raise RuntimeError("NORMAL TERMINAL SECRET")
        return False

    values = dict(request.__dict__)
    values["notifier"] = notifier
    result = run_v11_historical(V11DiagnosticRequest(**values))
    paths = V11ArtifactPaths.in_directory(tmp_path)
    events = validate_v11_ledger_state_machine(
        paths.ledger,
        expected_targets=2,
        source_blob_resolver=request.source_blob_resolver,
        registered_identity=request.registered_identity,
    )

    assert [event["event_type"] for event in events[-2:]] == [
        "published",
        "terminal_notification_receipt",
    ]
    assert events[-1]["payload"]["receipt"]["outcome"] == (
        "exception" if mode == "exception" else "returned_false"
    )
    assert result["notification_dispatched_after_terminal"] is False
    assert b"NORMAL TERMINAL SECRET" not in paths.ledger.read_bytes()


def test_run_local_records_below_three_do_not_claim_or_notify_historical_record(
    tmp_path: Path,
) -> None:
    request = _request(
        tmp_path,
        [(1, 20, 30, 40, 45, 49), (1, 2, 30, 40, 45, 49)],
    )
    calls: list[tuple[str, str]] = []
    values = dict(request.__dict__)
    values["notifier"] = lambda subject, body: calls.append((subject, body)) or True
    result = run_v11_historical(V11DiagnosticRequest(**values))

    assert calls == []
    records = result["report"]["progressive_record_ledger"]
    assert [record["current_final6_hits"] for record in records] == [1, 2]
    assert all(record["record_scope"] == "v11_run_local" for record in records)
    assert all(record["global_historical_maximum"] == "unknown" for record in records)
    assert all(
        record["feature_set"] == FEATURE_SET_BY_MODEL[CANDIDATE_MODEL]
        for record in records
    )


def test_three_hit_run_local_milestone_notification_is_honest_and_durable(
    tmp_path: Path,
) -> None:
    request = _request(
        tmp_path,
        [(1, 2, 3, 40, 45, 49), (38, 39, 40, 41, 42, 43)],
    )
    calls: list[tuple[str, str]] = []
    values = dict(request.__dict__)
    values["notifier"] = lambda subject, body: calls.append((subject, body)) or True
    run_v11_historical(V11DiagnosticRequest(**values))
    events = verify_hash_chain_ledger(V11ArtifactPaths.in_directory(tmp_path).ledger)

    assert len(calls) == 1
    subject, body = calls[0]
    assert "【历史严格回测】" in subject
    assert "run-local" in body
    assert "global maximum unknown" in body
    assert "legacy reported floor >=4/6" in body
    assert [
        event["event_type"] for event in events if "notification" in event["event_type"]
    ] == [
        "progress_notification_outbox",
        "progress_notification_receipt",
    ]


def test_top12_alert_reports_hits_for_the_actual_affected_model(
    tmp_path: Path,
) -> None:
    request = _request(
        tmp_path,
        [(44, 45, 46, 47, 48, 49), (38, 39, 40, 41, 42, 43)],
    )
    first_target = request.targets[0].target_date
    original_first_build = request.targets[0].build_forecasts

    def first_payload() -> dict:
        payload = original_first_build()
        random = payload["forecasts"][diagnostics.RANDOM_MODEL]
        ranking = [*range(1, 7), *range(44, 50), *range(7, 44)]
        scale = 6.0 / math.fsum(range(1, 50))
        random["probabilities"] = {
            str(label): (49 - index) * scale for index, label in enumerate(ranking)
        }
        random["ranking"] = ranking
        random["top6"] = ranking[:6]
        random["top12"] = ranking[:12]
        random["top18"] = ranking[:18]
        random["final6"] = sorted(ranking[:6])
        return payload

    targets = list(request.targets)
    targets[0] = V11TargetPlan(first_target, first_payload, targets[0].reveal_actual)
    calls: list[tuple[str, str]] = []
    values = dict(request.__dict__)
    values["targets"] = targets
    values["notifier"] = lambda subject, body: calls.append((subject, body)) or True

    run_v11_historical(V11DiagnosticRequest(**values))

    assert len(calls) == 1
    assert diagnostics.RANDOM_MODEL in calls[0][1]
    assert f"{diagnostics.RANDOM_MODEL}: Top-12=6/6" in calls[0][1]
    assert f"{CANDIDATE_MODEL}: Top-12=6/6" not in calls[0][1]


def test_progress_receipt_append_fault_archives_before_next_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[str, str]] = []
    request = _request(
        tmp_path,
        [(1, 2, 3, 40, 45, 49), (38, 39, 40, 41, 42, 43)],
        calls=calls,
    )
    original_append = diagnostics.HashChainLedger.append

    def fail_receipt(
        ledger: diagnostics.HashChainLedger, event_type: str, payload: dict
    ) -> dict:
        if event_type == "progress_notification_receipt":
            raise OSError("synthetic receipt fsync failure")
        return original_append(ledger, event_type, payload)

    monkeypatch.setattr(diagnostics.HashChainLedger, "append", fail_receipt)

    with pytest.raises(OSError, match="receipt fsync failure"):
        run_v11_historical(request)

    paths = V11ArtifactPaths.in_directory(tmp_path)
    events = validate_v11_ledger_state_machine(
        paths.ledger,
        expected_targets=2,
        source_blob_resolver=request.source_blob_resolver,
        registered_identity=request.registered_identity,
    )
    assert [event["event_type"] for event in events[-2:]] == [
        "progress_notification_outbox",
        "failed",
    ]
    assert all(target != "2030-01-02" for kind, target in calls if kind == "build")


def test_progress_outbox_append_fault_never_dispatches_notification(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    request = _request(
        tmp_path,
        [(1, 2, 3, 40, 45, 49), (38, 39, 40, 41, 42, 43)],
    )
    dispatches: list[str] = []
    values = dict(request.__dict__)
    values["notifier"] = lambda subject, _body: dispatches.append(subject) or True
    original_append = diagnostics.HashChainLedger.append

    def fail_outbox(
        ledger: diagnostics.HashChainLedger, event_type: str, payload: dict
    ) -> dict:
        if event_type == "progress_notification_outbox":
            raise OSError("synthetic outbox fsync failure")
        return original_append(ledger, event_type, payload)

    monkeypatch.setattr(diagnostics.HashChainLedger, "append", fail_outbox)

    with pytest.raises(OSError, match="outbox fsync failure"):
        run_v11_historical(V11DiagnosticRequest(**values))

    paths = V11ArtifactPaths.in_directory(tmp_path)
    events = validate_v11_ledger_state_machine(
        paths.ledger,
        expected_targets=2,
        source_blob_resolver=request.source_blob_resolver,
        registered_identity=request.registered_identity,
    )
    assert dispatches == []
    assert events[-1]["event_type"] == "failed"


def test_sealed_store_builds_each_fresh_v1_destination_once_and_never_parses_future(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    blob = (
        "draw_date,n1,n2,n3,n4,n5,n6,bonus\n"
        "2019-12-28,10,20,30,40,45,49,1\n"
        "2020-01-01,44,45,46,47,48,49,2\n"
        "2020-01-02,38,39,40,41,42,43,2\n"
        "2020-01-03,7,17,27,37,47,48,8\n"
    ).encode("ascii")
    parsed_dates: list[date] = []
    target_decode_heads: list[tuple[str, str]] = []
    ledger_path = V11ArtifactPaths.in_directory(tmp_path).ledger
    original_parser = v11_cli._parse_csv_row

    def parse_guard(raw: bytes):
        draw_date = v11_cli._date_from_opaque_row(raw)
        parsed_dates.append(draw_date)
        if draw_date >= date(2020, 1, 1):
            events = verify_hash_chain_ledger(ledger_path)
            target_decode_heads.append(
                (events[-1]["event_type"], events[-1]["payload"]["target_date"])
            )
        return original_parser(raw)

    monkeypatch.setattr(v11_cli, "_parse_csv_row", parse_guard)
    base_calls: list[tuple[date, str]] = []

    def base_builder(
        history: tuple,
        target_date: date,
        prefix_sha256: str,
    ) -> V1BaseSnapshot:
        base_calls.append((target_date, prefix_sha256))
        probabilities = (6.0 / 49.0,) * 49
        ranking = tuple(range(1, 50))
        return V1BaseSnapshot(
            target_date=target_date,
            history_draws=len(history),
            history_through=history[-1].draw_date,
            strict_prefix_sha256=prefix_sha256,
            probabilities=probabilities,
            ranking=ranking,
            top6=ranking[:6],
            top12=ranking[:12],
            top18=ranking[:18],
            final6=ranking[:6],
        )

    store = v11_cli.SealedCsvFoldStore(
        blob,
        expected_draw_count=4,
        expected_history_through=date(2020, 1, 3),
        target_start=date(2020, 1, 1),
        target_end=date(2020, 1, 2),
        first_half_end=date(2020, 1, 1),
        expected_target_count=2,
        expected_half_counts=(1, 1),
        base_builder=base_builder,
        random_builder=lambda _history, _target: {
            label: 6.0 / 49.0 for label in range(1, 50)
        },
    )
    scopes = (
        V11Scope("first", date(2020, 1, 1), date(2020, 1, 1), 1),
        V11Scope("second", date(2020, 1, 2), date(2020, 1, 2), 1),
    )
    registered_identity = _synthetic_registered_identity(
        blob,
        draw_count=4,
        history_through=date(2020, 1, 3),
        target_start=date(2020, 1, 1),
        target_end=date(2020, 1, 2),
        target_count=2,
        scopes=scopes,
    )
    assert parsed_dates == [date(2019, 12, 28)]
    request = V11DiagnosticRequest(
        root=tmp_path,
        output_dir=tmp_path,
        code_commit="1" * 40,
        exact_command=diagnostics.registered_v11_command(registered_identity),
        targets=store.plans(),
        preflight=lambda: _synthetic_preflight_for_blob(
            blob,
            draw_count=4,
            history_through=date(2020, 1, 3),
            target_count=2,
            fixed_half_counts=(1, 1),
            registered_identity=registered_identity,
        ),
        reference={},
        expected_target_count=2,
        stability_scopes=scopes,
        bootstrap_replicates=10,
        clock=_Clock(),
        source_blob_resolver=lambda _commit, _path: blob,
        registered_identity=registered_identity,
    )

    result = run_v11_historical(request)

    assert result["status"] == "published"
    assert parsed_dates == [
        date(2019, 12, 28),
        date(2020, 1, 1),
        date(2020, 1, 2),
    ]
    assert target_decode_heads == [
        ("prediction_frozen", "2020-01-01"),
        ("prediction_frozen", "2020-01-02"),
    ]
    assert [target for target, _digest in base_calls] == [
        date(2020, 1, 1),
        date(2020, 1, 2),
    ]
    assert len({digest for _target, digest in base_calls}) == 2
    assert (
        result["report"]["per_target"][1]["forecast_payload"]["prefix"][
            "history_through"
        ]
        == "2020-01-01"
    )


def test_sealed_store_incrementally_reuses_old_transitions_and_literal_prefix_hashes() -> (
    None
):
    rows = [
        b"2019-12-28,10,20,30,40,45,49,1\n",
        b"2020-01-01,44,45,46,47,48,49,2\n",
        b"2020-01-02,38,39,40,41,42,43,2\n",
        b"2020-01-03,7,17,27,37,47,48,8\n",
    ]
    header = b"draw_date,n1,n2,n3,n4,n5,n6,bonus\n"
    base_dates: list[date] = []
    transition_snapshots: list[tuple] = []

    def base_builder(history: tuple, target: date, prefix: str) -> V1BaseSnapshot:
        base_dates.append(target)
        probabilities = (6.0 / 49.0,) * 49
        ranking = tuple(range(1, 50))
        return V1BaseSnapshot(
            target_date=target,
            history_draws=len(history),
            history_through=history[-1].draw_date,
            strict_prefix_sha256=prefix,
            probabilities=probabilities,
            ranking=ranking,
            top6=ranking[:6],
            top12=ranking[:12],
            top18=ranking[:18],
            final6=ranking[:6],
        )

    def bundle_builder(base, transitions, source):
        transition_snapshots.append(transitions)
        return forecast_v11_bundle(base, transitions, source)

    store = v11_cli.SealedCsvFoldStore(
        header + b"".join(rows),
        expected_draw_count=4,
        expected_history_through=date(2020, 1, 3),
        target_start=date(2020, 1, 1),
        target_end=date(2020, 1, 3),
        first_half_end=date(2020, 1, 1),
        expected_target_count=3,
        expected_half_counts=(1, 2),
        base_builder=base_builder,
        random_builder=lambda _history, _target: {
            label: 6.0 / 49.0 for label in range(1, 50)
        },
        bundle_builder=bundle_builder,
    )
    payloads = []
    for target in store.target_dates:
        payloads.append(store.build_forecasts(target))
        store.reveal_actual(target)

    assert [payload["prefix"]["strict_prefix_sha256"] for payload in payloads] == [
        hashlib.sha256(header + b"".join(rows[:count])).hexdigest()
        for count in (1, 2, 3)
    ]
    assert [len(snapshot) for snapshot in transition_snapshots] == [0, 1, 2]
    assert transition_snapshots[1][0] is transition_snapshots[2][0]
    assert base_dates == [date(2020, 1, 1), date(2020, 1, 2), date(2020, 1, 3)]


def test_scope_metrics_cover_exact_tail_bootstrap_proper_scores_gain_and_calibration() -> (
    None
):
    target = date(2030, 1, 1)
    forecast = _forecast(CANDIDATE_MODEL, target)
    first = score_probability_forecast(forecast, (1, 2, 3, 4, 5, 6))
    second = {**first, "target_date": "2030-01-02"}

    summary = summarize_v11_scope(
        [first, second],
        scope="synthetic_two",
        bootstrap_replicates=10,
        bootstrap_seed=649,
    )
    paired = paired_top12_bootstrap(
        [first, second],
        [{**first, "top12_hits": 5}, {**second, "top12_hits": 5}],
        scope="synthetic_two",
        bootstrap_replicates=10,
        bootstrap_seed=649,
    )

    assert summary["avg_top6_hits"] == 6.0
    assert summary["avg_top12_hits"] == 6.0
    assert summary["avg_top18_hits"] == 6.0
    assert summary["brier_delta_vs_fair"] == pytest.approx(0.0)
    assert summary["log_loss_delta_vs_fair"] == pytest.approx(0.0)
    assert summary["log_g_sum"] == pytest.approx(2 * first["log_g"])
    assert summary["d_sum"] == pytest.approx(0.0)
    assert summary["final6_hit_histogram"] == {
        "0": 0,
        "1": 0,
        "2": 0,
        "3": 0,
        "4": 0,
        "5": 0,
        "6": 2,
    }
    assert len(summary["calibration"]["bins"]) == 10
    assert paired["bootstrap_95_ci"] == [1.0, 1.0]
    assert holm_v11_adjusted_p(0.01) == 0.03
