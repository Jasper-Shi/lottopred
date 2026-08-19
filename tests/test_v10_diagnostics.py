from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
import importlib.util
import json
import math
from math import comb
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

import lotto649.v10_diagnostics as diagnostics
from lotto649.v10_diagnostics import (
    MODEL_ORDER,
    RANDOM_CONTROL_MODEL,
    HashChainLedger,
    V10ArtifactPaths,
    V10DiagnosticError,
    V10DiagnosticRequest,
    V10Scope,
    V10TargetPlan,
    holm_adjusted_pvalues,
    paired_top12_bootstrap,
    run_v10_historical,
    score_probability_forecast,
    summarize_v10_scope,
    validate_v10_ledger_state_machine,
    verify_hash_chain_ledger,
    v10_historical_decision,
)


TOOL_PATH = Path(__file__).resolve().parents[1] / "tools" / "run_v10_historical.py"
TOOL_SPEC = importlib.util.spec_from_file_location("v10_historical_tool", TOOL_PATH)
assert TOOL_SPEC is not None and TOOL_SPEC.loader is not None
v10_cli = importlib.util.module_from_spec(TOOL_SPEC)
sys.modules[TOOL_SPEC.name] = v10_cli
TOOL_SPEC.loader.exec_module(v10_cli)


def test_hash_chain_ledger_is_canonical_contiguous_and_verifiable(tmp_path: Path) -> None:
    ledger_path = tmp_path / "attempt.ledger.jsonl"

    with HashChainLedger.create(ledger_path) as ledger:
        first = ledger.append("claimed", {"value": 1})
        second = ledger.append("preflight_passed", {"value": 2})

    events = verify_hash_chain_ledger(ledger_path)
    assert events == [first, second]
    assert [event["sequence"] for event in events] == [0, 1]
    assert events[0]["previous_event_sha256"] == "0" * 64
    assert events[1]["previous_event_sha256"] == events[0]["event_sha256"]
    assert ledger_path.read_bytes() == b"".join(
        (
            json.dumps(event, sort_keys=True, separators=(",", ":"), allow_nan=False)
            + "\n"
        ).encode("utf-8")
        for event in events
    )


def test_scope_summary_reports_exact_hits_scores_calibration_and_zero_bins() -> None:
    probability = 6.0 / 49.0
    forecast = {
        "model_name": "synthetic",
        "model_version": "v10.0.0",
        "probabilities": [probability] * 49,
        "ranking": list(range(1, 50)),
        "top6": list(range(1, 7)),
        "top12": list(range(1, 13)),
        "top18": list(range(1, 19)),
        "final6": list(range(1, 7)),
    }
    scores = [score_probability_forecast(forecast, (1, 2, 3, 4, 5, 6))] * 2

    summary = summarize_v10_scope(
        scores,
        scope="synthetic_two",
        bootstrap_replicates=10,
        bootstrap_seed=649,
    )

    assert summary["draws"] == 2
    assert summary["avg_top6_hits"] == 6.0
    assert summary["avg_top12_hits"] == 6.0
    assert summary["avg_top18_hits"] == 6.0
    assert summary["avg_actual_rank"] == 3.5
    assert summary["avg_brier"] == pytest.approx(0.10745522698875469)
    assert summary["avg_log_loss"] == pytest.approx(0.37177617994345286)
    assert summary["brier_delta_vs_fair"] == pytest.approx(0.0)
    assert summary["log_loss_delta_vs_fair"] == pytest.approx(0.0)
    assert summary["final6_hit_histogram"] == {
        "0": 0,
        "1": 0,
        "2": 0,
        "3": 0,
        "4": 0,
        "5": 0,
        "6": 2,
    }
    assert summary["primary_exact_one_sided_p"] == pytest.approx(
        (comb(12, 6) / comb(49, 6)) ** 2
    )
    assert summary["primary_bootstrap_95_ci"] == pytest.approx(
        [6.0 - 72.0 / 49.0, 6.0 - 72.0 / 49.0]
    )
    bins = summary["calibration"]["bins"]
    assert len(bins) == 10
    assert [item["cell_count"] for item in bins] == [0, 98, 0, 0, 0, 0, 0, 0, 0, 0]
    assert bins[1]["mean_forecast"] == pytest.approx(probability)
    assert bins[1]["observed_inclusion_rate"] == pytest.approx(probability)
    assert summary["calibration"]["expected_calibration_error"] == pytest.approx(0.0)


def test_exact_top12_tail_uses_integer_polynomial_convolution_oracles() -> None:
    coefficients = tuple(comb(12, hits) * comb(37, 6 - hits) for hits in range(7))
    one_draw = diagnostics._exact_top12_integer_distribution(1)
    two_draws = diagnostics._exact_top12_integer_distribution(2)

    assert one_draw == coefficients
    assert all(type(value) is int for value in two_draws)
    assert two_draws == tuple(
        sum(
            coefficients[left] * coefficients[right]
            for left in range(7)
            for right in range(7)
            if left + right == total
        )
        for total in range(13)
    )
    denominator = comb(49, 6)
    assert diagnostics.exact_top12_upper_tail(0, 2) == 1.0
    assert diagnostics.exact_top12_upper_tail(12, 2) == (
        coefficients[6] ** 2 / denominator**2
    )
    assert diagnostics.exact_top12_upper_tail(11, 2) == (
        (two_draws[11] + two_draws[12]) / denominator**2
    )


def test_exact_top12_tail_handles_extreme_621_draw_integer_counts() -> None:
    distribution = diagnostics._exact_top12_integer_distribution(621)

    assert len(distribution) == 6 * 621 + 1
    assert all(type(value) is int and value >= 0 for value in distribution)
    assert sum(distribution) == comb(49, 6) ** 621
    assert diagnostics.exact_top12_upper_tail(6 * 621, 621) == (
        comb(12, 6) ** 621 / comb(49, 6) ** 621
    )


def _passing_decision_inputs() -> dict:
    candidate = {
        "primary_top12_lift_vs_theory": 0.1,
        "primary_holm_adjusted_p": 0.05,
        "primary_bootstrap_95_ci": [0.01, 0.2],
        "brier_delta_vs_fair": 1.0e-9,
        "log_loss_delta_vs_fair": 1.0e-9,
        "avg_top12_hits": 1.6,
    }
    control = {
        "primary_exact_one_sided_p": math.nextafter(0.05, math.inf),
        "primary_bootstrap_95_ci": [0.01, 0.2],
    }
    paired = {"bootstrap_95_ci": [math.nextafter(0.0, math.inf), 0.2]}
    return {
        "candidate": candidate,
        "candidate_halves": [deepcopy(candidate), deepcopy(candidate)],
        "targeted_control": deepcopy(control),
        "targeted_control_halves": [deepcopy(control), deepcopy(control)],
        "random_control": deepcopy(control),
        "random_control_halves": [deepcopy(control), deepcopy(control)],
        "paired": deepcopy(paired),
        "paired_halves": [deepcopy(paired), deepcopy(paired)],
        "joint": {
            "candidate_aggregate_log_gain": 2.995732273553991,
            "candidate_half_log_gains": [
                math.nextafter(0.0, math.inf),
                math.nextafter(0.0, math.inf),
            ],
            "candidate_minus_control_aggregate_log_gain": math.nextafter(
                0.0, math.inf
            ),
            "candidate_minus_control_half_log_gains": [
                math.nextafter(0.0, math.inf),
                math.nextafter(0.0, math.inf),
            ],
            "control_aggregate_log_gain": math.nextafter(
                2.995732273553991, -math.inf
            ),
        },
        "v1_ensemble_top12_mean": math.nextafter(1.6, -math.inf),
        "audit_warnings": [],
        "proper_score_tolerance": 1.0e-9,
    }


def test_v10_decision_passes_every_frozen_boundary_operator_literal() -> None:
    decision = v10_historical_decision(**_passing_decision_inputs())

    assert decision["all_scientific_gates_passed"] is True
    assert all(decision["gates"].values())


def test_v10_decision_each_of_the_ten_gates_fails_at_its_boundary() -> None:
    cases = []

    def case(name, mutate):
        cases.append((name, mutate))

    case(
        "positive_aggregate_primary_lift",
        lambda values: values["candidate"].update(
            primary_top12_lift_vs_theory=0.0
        ),
    )
    case(
        "aggregate_holm_adjusted_p_at_most_0_05",
        lambda values: values["candidate"].update(
            primary_holm_adjusted_p=math.nextafter(0.05, math.inf)
        ),
    )
    case(
        "aggregate_bootstrap_lower_above_zero",
        lambda values: values["candidate"].update(
            primary_bootstrap_95_ci=[0.0, 0.2]
        ),
    )
    case(
        "positive_primary_lift_in_both_fixed_halves",
        lambda values: values["candidate_halves"][1].update(
            primary_top12_lift_vs_theory=0.0
        ),
    )
    case(
        "candidate_outperforms_targeted_control_aggregate_and_halves",
        lambda values: values["paired_halves"][0].update(
            bootstrap_95_ci=[0.0, 0.2]
        ),
    )
    case(
        "proper_scores_within_fair_tolerance_aggregate_and_halves",
        lambda values: values["candidate_halves"][1].update(
            log_loss_delta_vs_fair=math.nextafter(1.0e-9, math.inf)
        ),
    )
    case(
        "candidate_above_frozen_v1_ensemble_top12",
        lambda values: values.update(v1_ensemble_top12_mean=1.6),
    )
    case(
        "controls_null_aggregate_and_halves",
        lambda values: values["random_control_halves"][0].update(
            primary_exact_one_sided_p=0.05,
            primary_bootstrap_95_ci=[math.nextafter(0.0, math.inf), 0.2],
        ),
    )
    case(
        "joint_mechanism_gate",
        lambda values: values["joint"].update(
            control_aggregate_log_gain=2.995732273553991
        ),
    )
    case(
        "audit_clear",
        lambda values: values.update(audit_warnings=["synthetic_warning"]),
    )

    for expected_gate, mutate in cases:
        values = _passing_decision_inputs()
        mutate(values)
        decision = v10_historical_decision(**values)
        assert decision["gates"][expected_gate] is False, expected_gate
        assert decision["all_scientific_gates_passed"] is False


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        (
            "candidate_aggregate_log_gain",
            math.nextafter(2.995732273553991, -math.inf),
        ),
        ("candidate_half_log_gains", [0.0, 1.0]),
        ("candidate_minus_control_aggregate_log_gain", 0.0),
        ("candidate_minus_control_half_log_gains", [1.0, 0.0]),
        ("control_aggregate_log_gain", 2.995732273553991),
    ],
)
def test_each_joint_gate_comparison_is_literal(field: str, replacement) -> None:
    values = _passing_decision_inputs()
    values["joint"][field] = replacement

    decision = v10_historical_decision(**values)

    assert decision["gates"]["joint_mechanism_gate"] is False


def test_joint_delta_is_formed_per_target_before_fsum_not_aggregate_subtraction() -> None:
    targets = ["2030-01-01", "2030-01-02", "2030-01-03"]
    candidate_values = [1.0e292, 1.0e292, 1.0e308]
    control_values = [1.0e292, 1.0e308, 1.0e16]
    candidate = [
        {"target_date": target, "joint_log_gain": value}
        for target, value in zip(targets, candidate_values)
    ]
    control = [
        {"target_date": target, "joint_log_gain": value}
        for target, value in zip(targets, control_values)
    ]

    per_target_then_fsum = diagnostics._joint_delta_sum(candidate, control)

    assert per_target_then_fsum == math.fsum(
        left - right for left, right in zip(candidate_values, control_values)
    )
    assert per_target_then_fsum != (
        math.fsum(candidate_values) - math.fsum(control_values)
    )
    with pytest.raises(V10DiagnosticError, match="target dates differ"):
        diagnostics._joint_delta_sum(candidate, list(reversed(control)))


def test_paired_bootstrap_seed_linear_quantile_and_holm_two_family_oracles() -> None:
    dates = [f"2030-01-0{index}" for index in range(1, 6)]
    candidate_hits = np.asarray([0, 1, 4, 2, 6], dtype=float)
    control_hits = np.asarray([0, 2, 1, 2, 3], dtype=float)
    candidate = [
        {"target_date": target, "top12_hits": int(hits)}
        for target, hits in zip(dates, candidate_hits)
    ]
    control = [
        {"target_date": target, "top12_hits": int(hits)}
        for target, hits in zip(dates, control_hits)
    ]
    differences = candidate_hits - control_hits
    rng = np.random.default_rng(649)
    indices = rng.integers(0, 5, size=(10_000, 5))
    expected = np.quantile(
        differences[indices].mean(axis=1),
        [0.025, 0.975],
        method="linear",
    )

    paired = paired_top12_bootstrap(
        candidate,
        control,
        scope="synthetic",
        bootstrap_replicates=10_000,
        bootstrap_seed=649,
    )

    assert paired["bootstrap_95_ci"] == pytest.approx(expected.tolist())
    assert holm_adjusted_pvalues({"v5": 0.04, "v10": 0.01}) == pytest.approx(
        {"v10": 0.02, "v5": 0.04}
    )
    with pytest.raises(V10DiagnosticError, match="not aligned"):
        paired_top12_bootstrap(
            candidate,
            list(reversed(control)),
            scope="synthetic",
            bootstrap_replicates=10,
            bootstrap_seed=649,
        )


def _model_forecast(model_name: str, target: date) -> dict:
    probability = 6.0 / 49.0
    ranking = list(range(1, 50))
    payload = {
        "feature_identity": (
            "target_date_seeded_fair_random"
            if model_name == RANDOM_CONTROL_MODEL
            else "sorted_main_gap_exactly_one"
        ),
        "final6": ranking[:6],
        "history_draws": 0,
        "history_through": None,
        "model_name": model_name,
        "model_version": (
            "v1.0.0" if model_name == RANDOM_CONTROL_MODEL else "v10.0.0"
        ),
        "probabilities": {str(number): probability for number in ranking},
        "ranking": ranking,
        "seed": 649,
        "target_date": target.isoformat(),
        "top6": ranking[:6],
        "top12": ranking[:12],
        "top18": ranking[:18],
    }
    if model_name != RANDOM_CONTROL_MODEL:
        payload.update(
            {
                "log_z": 16.45359639530337,
                "moment_binary64": 30.0 / 49.0,
                "moment_denominator": 49,
                "moment_numerator": 30,
                "sum_a": 0,
                "theta": 0.0,
            }
        )
    return payload


def _forecast_payload(target: date) -> dict:
    return {
        "target_date": target.isoformat(),
        "prefix": {
            "history_draws": 0,
            "history_through": None,
            "strict_prefix_sha256": "a" * 64,
        },
        "forecasts": {
            model_name: _model_forecast(model_name, target)
            for model_name in MODEL_ORDER
        },
    }


class _TickingClock:
    def __init__(self) -> None:
        self.value = datetime(2030, 1, 1, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        value = self.value
        self.value += timedelta(microseconds=1)
        return value


def _synthetic_request(
    tmp_path: Path,
    *,
    actuals: list[tuple[int, ...]],
    audit_clear: bool = True,
    event_log: list[tuple[str, str]] | None = None,
    notifications: list[tuple[str, str]] | None = None,
) -> V10DiagnosticRequest:
    events = event_log if event_log is not None else []
    sent = notifications if notifications is not None else []
    start = date(2030, 1, 1)
    dates = [start + timedelta(days=index) for index in range(len(actuals))]
    plans = []
    ledger_path = V10ArtifactPaths.in_directory(tmp_path).ledger
    for target, actual in zip(dates, actuals):

        def build(target: date = target) -> dict:
            events.append(("build", target.isoformat()))
            return _forecast_payload(target)

        def reveal(
            target: date = target,
            actual: tuple[int, ...] = actual,
        ) -> tuple[int, ...]:
            ledger_events = verify_hash_chain_ledger(ledger_path)
            assert ledger_events[-1]["event_type"] == "prediction_frozen"
            assert ledger_events[-1]["payload"]["target_date"] == target.isoformat()
            events.append(("reveal", target.isoformat()))
            return actual

        plans.append(V10TargetPlan(target, build, reveal))

    if len(dates) == 1:
        scopes = (
            V10Scope("synthetic_first", dates[0], dates[0], 1),
            V10Scope(
                "synthetic_second",
                dates[0] + timedelta(days=1),
                dates[0] + timedelta(days=1),
                0,
            ),
        )
    else:
        scopes = (
            V10Scope("synthetic_first", dates[0], dates[0], 1),
            V10Scope("synthetic_second", dates[1], dates[-1], len(dates) - 1),
        )

    def notify(subject: str, body: str) -> bool:
        sent.append((subject, body))
        return True

    return V10DiagnosticRequest(
        root=tmp_path,
        output_dir=tmp_path,
        code_commit="1" * 40,
        exact_command="synthetic-v10-no-real-data",
        targets=plans,
        preflight=lambda: {
            "passed": True,
            "audit_warnings": [],
            "configuration": {"kind": "synthetic"},
            "data": {
                "kind": "synthetic_no_real_outcomes",
                "source_commit": "2" * 40,
            },
            "references": {"kind": "synthetic"},
            "runtime": {"python": "synthetic"},
            "registration_commit": "0" * 40,
            "registered_parameters": {"synthetic": True},
        },
        reference={
            "v5_primary_exact_p": 0.5,
            "v1_ensemble_top12_mean": 72.0 / 49.0,
            "comparisons": [],
        },
        expected_target_count=len(plans),
        stability_scopes=scopes,
        bootstrap_replicates=10,
        bootstrap_seed=649,
        notifier=notify,
        leakage_audit=lambda target, forecast, actual: {
            "clear": audit_clear,
            "checks": [
                {
                    "name": name,
                    "passed": audit_clear,
                    "evidence": {
                        "kind": "synthetic_no_real_outcome",
                        "target_date": target.isoformat(),
                        "forecast_target": forecast["target_date"],
                        "actual": list(actual),
                    },
                }
                for name in diagnostics.REQUIRED_6OF6_AUDIT_CHECKS
            ],
        },
        clock=_TickingClock(),
    )


def test_synthetic_vertical_slice_fsyncs_each_freeze_before_reveal_and_publishes(
    tmp_path: Path,
) -> None:
    call_order: list[tuple[str, str]] = []
    request = _synthetic_request(
        tmp_path,
        actuals=[(44, 45, 46, 47, 48, 49), (38, 39, 40, 41, 42, 43)],
        event_log=call_order,
    )

    result = run_v10_historical(request)

    assert result["status"] == "published"
    assert result["report"]["historical_decision"]["decision"] == "reject"
    assert result["report"]["historical_lane"]["target_count"] == 2
    assert call_order == [
        ("build", "2030-01-01"),
        ("build", "2030-01-01"),
        ("reveal", "2030-01-01"),
        ("build", "2030-01-02"),
        ("build", "2030-01-02"),
        ("reveal", "2030-01-02"),
    ]
    ledger_events = verify_hash_chain_ledger(Path(result["ledger_path"]))
    assert [event["event_type"] for event in ledger_events] == [
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
    prediction_event = ledger_events[3]["payload"]
    assert prediction_event["prediction_frozen_at_utc"].endswith("Z")
    assert "prediction_frozen_at_utc" not in prediction_event["forecast_payload"]
    assert "actual" not in json.dumps(prediction_event["forecast_payload"]).lower()
    assert Path(result["json_path"]).is_file()
    assert Path(result["markdown_path"]).is_file()
    assert not V10ArtifactPaths.in_directory(tmp_path).report_json_staging.exists()
    assert not V10ArtifactPaths.in_directory(tmp_path).report_markdown_staging.exists()


def test_progress_notification_outbox_is_fsynced_before_dispatch_and_next_target(
    tmp_path: Path,
) -> None:
    ledger_path = V10ArtifactPaths.in_directory(tmp_path).ledger
    notification_receipts: list[bytes] = []
    request = _synthetic_request(
        tmp_path,
        actuals=[(1, 2, 44, 45, 46, 47), (38, 39, 40, 41, 42, 43)],
    )

    def notifier(_subject: str, _body: str) -> bool:
        events = verify_hash_chain_ledger(ledger_path)
        assert events[-1]["event_type"] == "progress_notification_outbox"
        assert events[-1]["payload"]["notification_status"] == (
            "pending_external_receipt"
        )
        notification_receipts.append(ledger_path.read_bytes())
        return False

    replacement = dict(request.__dict__)
    replacement["notifier"] = notifier
    result = run_v10_historical(V10DiagnosticRequest(**replacement))

    events = verify_hash_chain_ledger(ledger_path)
    event_types = [event["event_type"] for event in events]
    first_score = event_types.index("target_revealed_scored")
    progress = event_types.index("progress_notification_outbox")
    second_freeze = event_types.index("prediction_frozen", first_score + 1)
    assert first_score < progress < second_freeze
    progress_payload = events[progress]["payload"]
    assert progress_payload["kind"] == "new_record"
    assert progress_payload["target_date"] == "2030-01-01"
    assert progress_payload["notification_warnings"][-1].startswith(
        "notification_pending_external_receipt:"
    )
    publication = next(
        event for event in events if event["event_type"] == "publication_started"
    )
    assert publication["payload"]["notification_warnings"] == (
        progress_payload["notification_warnings"]
    )
    assert result["report"]["notification_warnings"] == (
        progress_payload["notification_warnings"]
    )
    assert len(notification_receipts) == 1


def test_progress_notification_outbox_append_failure_never_calls_notifier(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    notifications: list[tuple[str, str]] = []
    request = _synthetic_request(
        tmp_path,
        actuals=[(1, 2, 44, 45, 46, 47), (38, 39, 40, 41, 42, 43)],
        notifications=notifications,
    )
    original_append = HashChainLedger.append

    def fail_progress_outbox(self, event_type, payload):
        if event_type == "progress_notification_outbox":
            raise OSError("synthetic progress outbox fsync failure")
        return original_append(self, event_type, payload)

    monkeypatch.setattr(HashChainLedger, "append", fail_progress_outbox)

    with pytest.raises(OSError, match="progress outbox fsync"):
        run_v10_historical(request)

    assert notifications == []
    events = verify_hash_chain_ledger(V10ArtifactPaths.in_directory(tmp_path).ledger)
    assert events[-1]["event_type"] == "failed"


def test_pair_publication_race_retains_staging_if_any_final_path_survives(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    json_path = tmp_path / "report.json"
    markdown_path = tmp_path / "report.md"
    json_staging = tmp_path / ".report.json.staging"
    markdown_staging = tmp_path / ".report.md.staging"
    original_link = diagnostics.os.link

    def racing_link(source, destination):
        destination = Path(destination)
        if destination == markdown_path:
            markdown_path.write_bytes(b"concurrent publisher\n")
        return original_link(source, destination)

    monkeypatch.setattr(diagnostics.os, "link", racing_link)

    with pytest.raises(V10DiagnosticError, match="partial publication retained"):
        diagnostics._safe_publish_pair(
            json_path=json_path,
            markdown_path=markdown_path,
            json_staging=json_staging,
            markdown_staging=markdown_staging,
            json_bytes=b"{}\n",
            markdown_bytes=b"# report\n",
        )

    assert not json_path.exists()
    assert markdown_path.read_bytes() == b"concurrent publisher\n"
    assert json_staging.read_bytes() == b"{}\n"
    assert markdown_staging.read_bytes() == b"# report\n"


def test_bundle_publication_race_retains_staging_and_final_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle_path = tmp_path / "bundle.json"
    staging = tmp_path / ".bundle.json.staging"
    original_link = diagnostics.os.link

    def racing_link(source, destination):
        bundle_path.write_bytes(b"concurrent publisher\n")
        return original_link(source, destination)

    monkeypatch.setattr(diagnostics.os, "link", racing_link)

    with pytest.raises(V10DiagnosticError, match="partial publication retained"):
        diagnostics._safe_publish_bundle(bundle_path, {"synthetic": True})

    assert bundle_path.read_bytes() == b"concurrent publisher\n"
    assert staging.is_file()


@pytest.mark.parametrize(
    ("audit_clear", "terminal_event", "expected_subject", "stop_global_search"),
    [
        (
            True,
            "historical_6of6_candidate_published",
            "🚨 [LOTTO649] 历史严格回测成功预测 6/6",
            True,
        ),
        (
            False,
            "historical_6of6_candidate_archived_leakage_failed",
            "⚠️ [LOTTO649] 历史 6/6 候选泄漏审计失败",
            False,
        ),
    ],
)
def test_synthetic_6of6_stops_before_next_target_and_takes_audited_terminal_branch(
    tmp_path: Path,
    audit_clear: bool,
    terminal_event: str,
    expected_subject: str,
    stop_global_search: bool,
) -> None:
    notifications: list[tuple[str, str]] = []
    request = _synthetic_request(
        tmp_path,
        actuals=[(1, 2, 3, 4, 5, 6)],
        audit_clear=audit_clear,
        notifications=notifications,
    )

    result = run_v10_historical(request)

    assert result["status"] == terminal_event
    assert result["scored_targets"] == 1
    assert result["stop_global_search"] is stop_global_search
    assert not V10ArtifactPaths.in_directory(tmp_path).report_json.exists()
    assert not V10ArtifactPaths.in_directory(tmp_path).report_markdown.exists()
    bundle = json.loads(Path(result["bundle_path"]).read_text())
    assert bundle["normal_621_report"] == "prohibited_after_early_stop"
    assert bundle["leakage_audit"]["clear"] is audit_clear
    assert bundle["source_commit"] == "2" * 40
    assert bundle["registration_commit"] == "0" * 40
    assert bundle["implementation_commit"] == "1" * 40
    ledger_events = verify_hash_chain_ledger(Path(result["ledger_path"]))
    event_types = [event["event_type"] for event in ledger_events]
    assert event_types[-3:] == [
        "historical_6of6_candidate_detected",
        "historical_6of6_leakage_audit_completed",
        terminal_event,
    ]
    assert "scoring_completed" not in event_types
    assert any(subject == expected_subject for subject, _body in notifications)


def test_existing_artifact_fails_before_preflight_or_any_forecast(tmp_path: Path) -> None:
    request = _synthetic_request(
        tmp_path,
        actuals=[(44, 45, 46, 47, 48, 49)],
    )
    paths = V10ArtifactPaths.in_directory(tmp_path)
    paths.claim.write_text("already consumed", encoding="utf-8")

    with pytest.raises(V10DiagnosticError, match="already exists"):
        run_v10_historical(request)

    assert not paths.ledger.exists()


def test_post_claim_failure_is_durably_archived_and_cannot_rerun(tmp_path: Path) -> None:
    target = date(2030, 1, 1)
    request = _synthetic_request(
        tmp_path,
        actuals=[(44, 45, 46, 47, 48, 49)],
    )

    def fail_reveal() -> tuple[int, ...]:
        events = verify_hash_chain_ledger(
            V10ArtifactPaths.in_directory(tmp_path).ledger
        )
        assert events[-1]["event_type"] == "prediction_frozen"
        raise RuntimeError("synthetic reveal failure")

    replacement = dict(request.__dict__)
    replacement["targets"] = [
        V10TargetPlan(
            target,
            lambda: _forecast_payload(target),
            fail_reveal,
        )
    ]
    request = V10DiagnosticRequest(**replacement)
    with pytest.raises(RuntimeError, match="synthetic reveal failure"):
        run_v10_historical(request)

    paths = V10ArtifactPaths.in_directory(tmp_path)
    events = verify_hash_chain_ledger(paths.ledger)
    assert events[-1]["event_type"] == "failed"
    assert events[-1]["payload"]["status"] == "consumed_archive_no_rerun"
    assert validate_v10_ledger_state_machine(
        paths.ledger,
        expected_targets=1,
    ) == events
    assert paths.claim.is_file()
    with pytest.raises(V10DiagnosticError, match="already exists"):
        run_v10_historical(request)


def _synthetic_csv_blob(
    *,
    target_main: tuple[int, ...] = (7, 17, 27, 37, 47, 48),
    future_main: tuple[int, ...] = (2, 12, 22, 32, 42, 48),
    target_bonus: int = 8,
    future_bonus: int = 9,
) -> bytes:
    target_values = ",".join(str(number) for number in target_main)
    future_values = ",".join(str(number) for number in future_main)
    return (
        "draw_date,n1,n2,n3,n4,n5,n6,bonus\n"
        "2019-12-28,10,20,30,40,45,49,1\n"
        f"2020-01-01,{target_values},{target_bonus}\n"
        "2020-01-02,13,23,33,43,46,49,1\n"
        f"2020-01-03,{future_values},{future_bonus}\n"
    ).encode("ascii")


def _small_sealed_store(blob: bytes, **kwargs) -> v10_cli.SealedCsvFoldStore:
    options = {
        "expected_draw_count": 4,
        "expected_history_through": date(2020, 1, 3),
        "target_start": date(2020, 1, 1),
        "target_end": date(2020, 1, 2),
        "first_half_end": date(2020, 1, 1),
        "expected_target_count": 2,
        "expected_half_counts": (1, 1),
        "implementation_commit": "1" * 40,
        "configuration_sha256": "c" * 64,
    }
    options.update(kwargs)
    return v10_cli.SealedCsvFoldStore(blob, **options)


def test_production_sealed_store_parses_target_only_after_fsynced_receipt_and_updates_prefix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parsed_dates: list[date] = []
    original_parser = v10_cli._parse_csv_row
    ledger_path = V10ArtifactPaths.in_directory(tmp_path).ledger

    def guarded_parser(raw_line: bytes):
        draw_date = v10_cli._date_from_opaque_csv_row(raw_line)
        if draw_date >= date(2020, 1, 1):
            ledger_events = verify_hash_chain_ledger(ledger_path)
            assert ledger_events[-1]["event_type"] == "prediction_frozen"
            assert ledger_events[-1]["payload"]["target_date"] == draw_date.isoformat()
        parsed_dates.append(draw_date)
        return original_parser(raw_line)

    monkeypatch.setattr(v10_cli, "_parse_csv_row", guarded_parser)
    store = _small_sealed_store(_synthetic_csv_blob())
    assert parsed_dates == [date(2019, 12, 28)]
    request = V10DiagnosticRequest(
        root=tmp_path,
        output_dir=tmp_path,
        code_commit="1" * 40,
        exact_command="synthetic-production-adapter",
        targets=store.plans(),
        preflight=lambda: {
            "passed": True,
            "audit_warnings": [],
            "configuration": {},
            "data": {},
            "references": {},
            "runtime": {},
        },
        reference={
            "v5_primary_exact_p": 0.5,
            "v1_ensemble_top12_mean": 1.5,
            "comparisons": [],
        },
        expected_target_count=2,
        stability_scopes=(
            V10Scope("first", date(2020, 1, 1), date(2020, 1, 1), 1),
            V10Scope("second", date(2020, 1, 2), date(2020, 1, 2), 1),
        ),
        bootstrap_replicates=10,
        notifier=lambda _subject, _body: True,
        clock=_TickingClock(),
    )

    result = run_v10_historical(request)

    assert result["status"] == "published"
    assert parsed_dates == [
        date(2019, 12, 28),
        date(2020, 1, 1),
        date(2020, 1, 2),
    ]
    targets = result["report"]["per_target"]
    assert targets[0]["forecast_payload"]["prefix"]["history_draws"] == 1
    assert targets[1]["forecast_payload"]["prefix"]["history_draws"] == 2
    assert targets[1]["forecast_payload"]["prefix"]["history_through"] == (
        "2020-01-01"
    )


def test_sealed_target_future_and_bonus_bytes_cannot_change_forecasts() -> None:
    baseline = _small_sealed_store(_synthetic_csv_blob())
    target_main_changed = _small_sealed_store(
        _synthetic_csv_blob(target_main=(6, 16, 26, 36, 46, 49))
    )
    future_main_changed = _small_sealed_store(
        _synthetic_csv_blob(future_main=(3, 13, 23, 33, 43, 49))
    )
    bonus_changed = _small_sealed_store(
        _synthetic_csv_blob(target_bonus=9, future_bonus=10)
    )

    first_target = date(2020, 1, 1)
    baseline_payload = baseline.build_forecasts(first_target)
    assert target_main_changed.build_forecasts(first_target) == baseline_payload
    assert future_main_changed.build_forecasts(first_target) == baseline_payload
    assert bonus_changed.build_forecasts(first_target)["forecasts"] == (
        baseline_payload["forecasts"]
    )
    baseline_actual = baseline.reveal_actual(first_target)
    assert target_main_changed.reveal_actual(first_target) != baseline_actual
    assert future_main_changed.reveal_actual(first_target) == baseline_actual
    assert bonus_changed.reveal_actual(first_target) == baseline_actual

    second_target = date(2020, 1, 2)
    baseline_second = baseline.build_forecasts(second_target)["forecasts"]
    assert future_main_changed.build_forecasts(second_target)["forecasts"] == (
        baseline_second
    )
    assert bonus_changed.build_forecasts(second_target)["forecasts"] == (
        baseline_second
    )


def test_production_leakage_audit_uses_distinct_same_date_suffix_counterfactuals(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / v10_cli.RESEARCH_CONFIG
    config_path.parent.mkdir(parents=True)
    config_path.write_text("synthetic: true\n", encoding="utf-8")
    configuration_sha256 = v10_cli._file_sha256(config_path)
    implementation_commit = "1" * 40
    monkeypatch.setattr(v10_cli, "ROOT", tmp_path)
    monkeypatch.setattr(
        v10_cli,
        "_git_text",
        lambda *args: implementation_commit if args == ("rev-parse", "HEAD") else "",
    )
    blob = _synthetic_csv_blob(
        target_main=(1, 2, 3, 4, 5, 6),
        target_bonus=7,
    )
    store = _small_sealed_store(
        blob,
        implementation_commit=implementation_commit,
        configuration_sha256=configuration_sha256,
    )
    store.bind_preflight_evidence(
        {
            "exact_head": implementation_commit,
            "registration_ancestor": True,
            "registered_blob_sha256": v10_cli._sha256_bytes(blob),
            "runtime_versions_verified": True,
            "ci_required_checks_passed": True,
            "remote_branch_head": implementation_commit,
        }
    )
    target = date(2020, 1, 1)
    payload = store.build_forecasts(target)
    actual = store.reveal_actual(target)

    audit = store.leakage_audit(target, payload, actual)

    assert audit["clear"] is True
    assert {check["name"] for check in audit["checks"]} == set(
        diagnostics.REQUIRED_6OF6_AUDIT_CHECKS
    )
    assert all(
        check["passed"] is True and check["evidence"] for check in audit["checks"]
    )
    target_check = next(
        check for check in audit["checks"] if check["name"] == "target_exclusion"
    )
    assert target_check["evidence"]["original_target_sha256"] != (
        target_check["evidence"]["replacement_target_sha256"]
    )
    feature_check = next(
        check for check in audit["checks"] if check["name"] == "feature_selection"
    )
    assert feature_check["evidence"][
        "prior_main_counterfactual_changed_candidate"
    ] is True
    assert feature_check["evidence"][
        "prior_main_counterfactual_changed_targeted_control"
    ] is True
    assert feature_check["evidence"]["selected_prior_main_counterfactual"][
        "replacement_main"
    ] == [3, 4, 5, 6, 7, 8]
    attempts = feature_check["evidence"]["prior_main_counterfactual_attempts"]
    assert any(
        attempt["candidate_changed"] and not attempt["control_changed"]
        for attempt in attempts
    )
    assert any(
        attempt["control_changed"] and not attempt["candidate_changed"]
        for attempt in attempts
    )


def test_sealed_store_locks_the_production_621_and_307_314_counts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    header = b"draw_date,n1,n2,n3,n4,n5,n6,bonus\n"
    rows = [b"2019-12-28,10,20,30,40,45,49,1\n"]
    first_dates = [date(2020, 1, 1) + timedelta(days=index) for index in range(307)]
    second_dates = [date(2023, 1, 1) + timedelta(days=index) for index in range(314)]
    rows.extend(
        f"{target.isoformat()},1,3,5,7,9,11,2\n".encode("ascii")
        for target in [*first_dates, *second_dates]
    )
    rows.append(b"2026-08-15,2,4,6,8,10,12,1\n")
    parsed = []
    original_parser = v10_cli._parse_csv_row

    def parser(raw_line: bytes):
        parsed.append(v10_cli._date_from_opaque_csv_row(raw_line))
        return original_parser(raw_line)

    monkeypatch.setattr(v10_cli, "_parse_csv_row", parser)
    store = v10_cli.SealedCsvFoldStore(
        header + b"".join(rows),
        expected_draw_count=623,
        expected_history_through=date(2026, 8, 15),
    )

    assert len(store.target_dates) == 621
    assert sum(target <= date(2022, 12, 31) for target in store.target_dates) == 307
    assert sum(target >= date(2023, 1, 1) for target in store.target_dates) == 314
    assert parsed == [date(2019, 12, 28)]


def test_runtime_lock_ci_and_implementation_path_preflight_helpers_fail_closed() -> None:
    lock = b"numpy==2.3.5\nPyYAML==6.0.3\n"
    assert v10_cli._validate_runtime_versions(
        lock,
        {"NumPy": "2.3.5", "pyyaml": "6.0.3", "pytest": "9.0.0"},
    ) == {"numpy": "2.3.5", "pyyaml": "6.0.3"}
    with pytest.raises(V10DiagnosticError, match="runtime distribution mismatch"):
        v10_cli._validate_runtime_versions(
            lock,
            {"numpy": "2.3.4", "PyYAML": "6.0.3"},
        )
    with pytest.raises(V10DiagnosticError, match="CPython 3.12"):
        v10_cli._require_runtime_identity("CPython", (3, 13))

    required = [
        {
            "id": 1,
            "name": "test",
            "status": "completed",
            "conclusion": "success",
            "app": {"slug": "github-actions"},
        },
        {
            "id": 2,
            "name": "source-and-model-smoke",
            "status": "completed",
            "conclusion": "success",
            "app": {"slug": "github-actions"},
        },
        {
            "id": 3,
            "name": "gmail-alert-smoke-test",
            "status": "completed",
            "conclusion": "failure",
            "app": {"slug": "github-actions"},
        },
    ]
    with pytest.raises(V10DiagnosticError, match="nonpassing checks"):
        v10_cli._validate_ci_check_runs(required)
    passing = [
        *required[:2],
        {
            **required[2],
            "conclusion": "neutral",
        },
    ]
    ci = v10_cli._validate_ci_check_runs(passing)
    assert ci["required_successful_checks"] == ["source-and-model-smoke", "test"]
    with pytest.raises(V10DiagnosticError, match="lacks required checks"):
        v10_cli._validate_ci_check_runs([required[0], required[2]])
    with pytest.raises(V10DiagnosticError, match="lacks required checks"):
        v10_cli._validate_ci_check_runs(
            [
                {**required[0], "app": {"slug": "evil-spoof"}},
                {**required[1], "app": {"slug": "evil-spoof"}},
            ]
        )
    with pytest.raises(V10DiagnosticError, match="not green"):
        v10_cli._validate_ci_check_runs(
            [
                *passing,
                {
                    "id": 4,
                    "name": "test",
                    "status": "completed",
                    "conclusion": "failure",
                    "app": {"slug": "github-actions"},
                },
            ]
        )

    core_paths = "\n".join(sorted(v10_cli.REQUIRED_IMPLEMENTATION_PATHS))
    assert v10_cli._validate_implementation_changed_paths(core_paths) == sorted(
        v10_cli.REQUIRED_IMPLEMENTATION_PATHS
    )
    allowed_paths = "\n".join(sorted(v10_cli.IMPLEMENTATION_PATHS))
    assert v10_cli._validate_implementation_changed_paths(allowed_paths) == sorted(
        v10_cli.IMPLEMENTATION_PATHS
    )
    with pytest.raises(V10DiagnosticError, match="unexpected"):
        v10_cli._validate_implementation_changed_paths(
            allowed_paths + "\nsrc/lotto649/live.py"
        )


def test_remote_branch_identity_is_exact_and_notifier_fails_before_dispatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = "1" * 40
    assert v10_cli._require_exact_remote_head(expected, expected) == expected
    with pytest.raises(V10DiagnosticError, match="remote branch"):
        v10_cli._require_exact_remote_head("2" * 40, expected)
    with pytest.raises(V10DiagnosticError, match="remote branch"):
        v10_cli._require_exact_remote_head("not-a-sha", expected)

    monkeypatch.setattr(
        v10_cli,
        "_validate_github_branch_head",
        lambda _branch, _commit: (_ for _ in ()).throw(
            V10DiagnosticError("synthetic remote branch moved")
        ),
    )
    monkeypatch.setattr(
        v10_cli.subprocess,
        "run",
        lambda *_args, **_kwargs: pytest.fail("dispatch ran after ref mismatch"),
    )
    notifier = v10_cli.GitHubWorkflowNotifier("codex/v10", expected)

    assert notifier("synthetic subject", "synthetic body") is False


def test_notifier_remote_ref_check_has_a_bounded_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed_timeouts: list[float | None] = []

    def timeout_run(*args, **kwargs):
        observed_timeouts.append(kwargs.get("timeout"))
        raise subprocess.TimeoutExpired(args, kwargs.get("timeout"))

    monkeypatch.setattr(v10_cli.subprocess, "run", timeout_run)
    notifier = v10_cli.GitHubWorkflowNotifier("codex/v10", "1" * 40)

    assert notifier("synthetic subject", "synthetic body") is False
    assert observed_timeouts == [30]


def test_working_source_and_frozen_reference_helpers_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    blob = _synthetic_csv_blob()
    data_path = tmp_path / "data" / "processed"
    data_path.mkdir(parents=True)
    (data_path / "draws.csv").write_bytes(
        blob + b"2020-01-04,3,13,23,33,43,49,1\n"
    )
    monkeypatch.setattr(v10_cli, "ROOT", tmp_path)
    v10_cli._validate_working_dataset(blob)
    (data_path / "draws.csv").write_bytes(blob.replace(b",7,17,", b",6,17,"))
    with pytest.raises(V10DiagnosticError, match="revises"):
        v10_cli._validate_working_dataset(blob)

    reports = tmp_path / "reports"
    reports.mkdir()
    v5_path = reports / "v5_pair_affinity_v5.0.0_historical.json"
    v8_path = reports / "v8_spectral_phase_v8.0.0_historical.json"
    claim_path = reports / "v8_spectral_phase_v8.0.0_historical.claim"
    v5_path.write_text(
        json.dumps(
            {
                "lanes": [
                    {
                        "lane": "consumed_diagnostic",
                        "candidate": {"primary_exact_one_sided_p": 0.25},
                    }
                ]
            }
        )
    )
    v8_path.write_text(
        json.dumps(
            {
                "comparisons": [
                    {"model_name": "ensemble", "avg_top12_hits": 1.4}
                ]
            }
        )
    )
    claim_path.write_text("synthetic claim\n")
    monkeypatch.setattr(v10_cli, "EXPECTED_V5_SHA256", v10_cli._file_sha256(v5_path))
    monkeypatch.setattr(v10_cli, "EXPECTED_V8_SHA256", v10_cli._file_sha256(v8_path))
    monkeypatch.setattr(
        v10_cli,
        "EXPECTED_V8_CLAIM_SHA256",
        v10_cli._file_sha256(claim_path),
    )
    references = v10_cli._load_references()
    assert references["v5_primary_exact_p"] == 0.25
    assert references["v1_ensemble_top12_mean"] == 1.4
    v8_path.write_text("{}")
    with pytest.raises(V10DiagnosticError, match="identity changed"):
        v10_cli._load_references()


def test_cli_requires_explicit_consumed_one_shot_acknowledgement() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(Path(v10_cli.__file__)),
            "--code-commit",
            "1" * 40,
        ],
        cwd=Path(v10_cli.__file__).resolve().parents[1],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert completed.returncode != 0
    assert "--execute-consumed-historical-diagnostic" in completed.stderr


def _rechain_events(path: Path, events: list[dict]) -> None:
    with HashChainLedger.create(path) as ledger:
        for event in events:
            ledger.append(event["event_type"], event["payload"])


def test_ledger_state_machine_rejects_hash_valid_missing_reordered_and_duplicate_events(
    tmp_path: Path,
) -> None:
    request = _synthetic_request(
        tmp_path / "valid",
        actuals=[(44, 45, 46, 47, 48, 49), (38, 39, 40, 41, 42, 43)],
    )
    result = run_v10_historical(request)
    valid_events = verify_hash_chain_ledger(Path(result["ledger_path"]))
    assert validate_v10_ledger_state_machine(
        Path(result["ledger_path"]), expected_targets=2
    ) == valid_events

    mutations = {
        "missing": valid_events[:4] + valid_events[5:],
        "reordered": [valid_events[1], valid_events[0], *valid_events[2:]],
        "duplicate": [*valid_events[:5], valid_events[4], *valid_events[5:]],
    }
    for name, events in mutations.items():
        bad_path = tmp_path / f"{name}.jsonl"
        _rechain_events(bad_path, events)
        with pytest.raises(V10DiagnosticError):
            validate_v10_ledger_state_machine(bad_path, expected_targets=2)


def test_ledger_state_machine_accepts_failed_terminal_after_any_valid_prefix(
    tmp_path: Path,
) -> None:
    normal = run_v10_historical(
        _synthetic_request(
            tmp_path / "normal",
            actuals=[(44, 45, 46, 47, 48, 49), (38, 39, 40, 41, 42, 43)],
        )
    )
    normal_events = verify_hash_chain_ledger(Path(normal["ledger_path"]))
    six = run_v10_historical(
        _synthetic_request(tmp_path / "six", actuals=[(1, 2, 3, 4, 5, 6)])
    )
    six_events = verify_hash_chain_ledger(Path(six["ledger_path"]))
    failed = {
        "event_type": "failed",
        "payload": {
            "error_message": "synthetic interruption",
            "error_type": "RuntimeError",
            "status": "consumed_archive_no_rerun",
        },
    }
    prefixes = {
        "claimed": (normal_events[:1], 2, Path(normal["claim_path"])),
        "frozen": (normal_events[:4], 2, Path(normal["claim_path"])),
        "six_audited": (six_events[:-1], 1, Path(six["claim_path"])),
    }
    for name, (prefix, expected_targets, source_claim) in prefixes.items():
        failure_dir = tmp_path / f"failed-{name}"
        failure_dir.mkdir()
        path = failure_dir / "attempt.ledger.jsonl"
        V10ArtifactPaths.in_directory(failure_dir).claim.write_bytes(
            source_claim.read_bytes()
        )
        with HashChainLedger.create(path) as ledger:
            for event in [*prefix, failed]:
                ledger.append(event["event_type"], event["payload"])
        events = validate_v10_ledger_state_machine(
            path,
            expected_targets=expected_targets,
        )
        assert events[-1]["event_type"] == "failed"

    publication_path = Path(normal["ledger_path"])
    publication_path.unlink()
    _rechain_events(publication_path, [*normal_events[:9], failed])
    events = validate_v10_ledger_state_machine(
        publication_path,
        expected_targets=2,
    )
    assert events[-1]["event_type"] == "failed"


@pytest.mark.parametrize(
    "mutation",
    ["claimed_identity", "forecast_payload", "timestamp", "score"],
)
def test_ledger_state_machine_rejects_semantically_tampered_but_rechained_events(
    tmp_path: Path,
    mutation: str,
) -> None:
    result = run_v10_historical(
        _synthetic_request(
            tmp_path / "source",
            actuals=[(44, 45, 46, 47, 48, 49), (38, 39, 40, 41, 42, 43)],
        )
    )
    events = json.loads(
        json.dumps(verify_hash_chain_ledger(Path(result["ledger_path"])))
    )
    frozen = next(
        event for event in events if event["event_type"] == "prediction_frozen"
    )
    scored = next(
        event for event in events if event["event_type"] == "target_revealed_scored"
    )
    if mutation == "claimed_identity":
        events[0]["payload"]["code_commit"] = "z" * 40
        events[0]["payload"]["claim_sha256"] = "x" * 64
    elif mutation == "forecast_payload":
        frozen["payload"]["forecast_payload"]["prefix"][
            "strict_prefix_sha256"
        ] = "b" * 64
    elif mutation == "timestamp":
        frozen["payload"]["prediction_frozen_at_utc"] = "not-rfc3339z"
    else:
        scored["payload"]["scores"][diagnostics.CANDIDATE_MODEL]["top12_hits"] += 1
    path = tmp_path / f"tampered-{mutation}.jsonl"
    _rechain_events(path, events)

    with pytest.raises(V10DiagnosticError):
        validate_v10_ledger_state_machine(path, expected_targets=2)


def test_ledger_state_machine_binds_normal_report_to_fixed_claim_artifact(
    tmp_path: Path,
) -> None:
    result = run_v10_historical(
        _synthetic_request(
            tmp_path,
            actuals=[(44, 45, 46, 47, 48, 49), (38, 39, 40, 41, 42, 43)],
        )
    )
    claim_path = Path(result["claim_path"])
    claim = json.loads(claim_path.read_text(encoding="utf-8"))
    claim["seed"] = 650
    claim_path.write_text(
        json.dumps(claim, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    report_path = Path(result["json_path"])
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["one_shot_claim"]["sha256"] = diagnostics._file_sha256(claim_path)
    report["one_shot_claim"]["payload"] = claim
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    ledger_path = Path(result["ledger_path"])
    events = json.loads(json.dumps(verify_hash_chain_ledger(ledger_path)))
    published = next(event for event in events if event["event_type"] == "published")
    published["payload"]["json_sha256"] = diagnostics._file_sha256(report_path)
    ledger_path.unlink()
    _rechain_events(ledger_path, events)

    with pytest.raises(V10DiagnosticError, match="claim"):
        validate_v10_ledger_state_machine(ledger_path, expected_targets=2)


def test_failed_terminal_still_binds_the_permanent_claim_artifact(
    tmp_path: Path,
) -> None:
    result = run_v10_historical(
        _synthetic_request(
            tmp_path,
            actuals=[(44, 45, 46, 47, 48, 49), (38, 39, 40, 41, 42, 43)],
        )
    )
    claim_path = Path(result["claim_path"])
    claim = json.loads(claim_path.read_text(encoding="utf-8"))
    claim["seed"] = 650
    claim_path.write_text(
        json.dumps(claim, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    ledger_path = Path(result["ledger_path"])
    events = json.loads(json.dumps(verify_hash_chain_ledger(ledger_path)))
    events[0]["payload"]["claim_sha256"] = diagnostics._file_sha256(claim_path)
    failed = {
        "event_type": "failed",
        "payload": {
            "error_message": "synthetic interruption",
            "error_type": "RuntimeError",
            "status": "consumed_archive_no_rerun",
        },
    }
    ledger_path.unlink()
    _rechain_events(ledger_path, [events[0], failed])

    with pytest.raises(V10DiagnosticError, match="claim"):
        validate_v10_ledger_state_machine(ledger_path, expected_targets=2)


def test_ledger_state_machine_rejects_audit_false_with_forged_clear_success(
    tmp_path: Path,
) -> None:
    result = run_v10_historical(
        _synthetic_request(tmp_path, actuals=[(1, 2, 3, 4, 5, 6)])
    )
    ledger_path = Path(result["ledger_path"])
    events = json.loads(json.dumps(verify_hash_chain_ledger(ledger_path)))
    audit_event = next(
        event
        for event in events
        if event["event_type"] == "historical_6of6_leakage_audit_completed"
    )
    audit_event["payload"]["audit"]["checks"][0]["passed"] = False
    assert audit_event["payload"]["audit"]["clear"] is True
    ledger_path.unlink()
    _rechain_events(ledger_path, events)

    with pytest.raises(V10DiagnosticError, match="audit"):
        validate_v10_ledger_state_machine(ledger_path, expected_targets=1)


@pytest.mark.parametrize("mutation", ["seed", "runtime", "claim_sha256"])
def test_ledger_state_machine_rejects_rehashed_6of6_bundle_identity_tampering(
    tmp_path: Path,
    mutation: str,
) -> None:
    result = run_v10_historical(
        _synthetic_request(tmp_path, actuals=[(1, 2, 3, 4, 5, 6)])
    )
    bundle_path = Path(result["bundle_path"])
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    if mutation == "seed":
        bundle["seed"] = 650
    elif mutation == "runtime":
        bundle["runtime"] = {"python": "forged"}
    else:
        bundle["claim"]["sha256"] = "f" * 64
    bundle_path.write_text(
        json.dumps(bundle, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    ledger_path = Path(result["ledger_path"])
    events = json.loads(json.dumps(verify_hash_chain_ledger(ledger_path)))
    terminal = events[-1]
    terminal["payload"]["bundle_sha256"] = diagnostics._file_sha256(bundle_path)
    ledger_path.unlink()
    _rechain_events(ledger_path, events)

    with pytest.raises(V10DiagnosticError, match="bundle"):
        validate_v10_ledger_state_machine(ledger_path, expected_targets=1)


def test_6of6_terminal_is_never_appended_before_last_fallible_validation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    notifications: list[tuple[str, str]] = []
    request = _synthetic_request(
        tmp_path,
        actuals=[(1, 2, 3, 4, 5, 6)],
        notifications=notifications,
    )
    original_validator = diagnostics.validate_v10_ledger_state_machine
    calls = 0

    def fail_second_validation(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("synthetic final validation I/O failure")
        return original_validator(*args, **kwargs)

    monkeypatch.setattr(
        diagnostics,
        "validate_v10_ledger_state_machine",
        fail_second_validation,
    )

    with pytest.raises(OSError, match="synthetic final validation"):
        run_v10_historical(request)

    ledger_path = V10ArtifactPaths.in_directory(tmp_path).ledger
    events = verify_hash_chain_ledger(ledger_path)
    assert events[-1]["event_type"] == "failed"
    assert not any(
        event["event_type"]
        in {
            "historical_6of6_candidate_published",
            "historical_6of6_candidate_archived_leakage_failed",
        }
        for event in events
    )
    assert notifications == []
    assert original_validator(ledger_path, expected_targets=1) == events


@pytest.mark.parametrize("mutation", ["decision", "gates", "json_sha256", "json_path"])
def test_ledger_state_machine_rejects_published_payload_not_bound_to_report(
    tmp_path: Path,
    mutation: str,
) -> None:
    result = run_v10_historical(
        _synthetic_request(
            tmp_path,
            actuals=[(44, 45, 46, 47, 48, 49), (38, 39, 40, 41, 42, 43)],
        )
    )
    ledger_path = Path(result["ledger_path"])
    events = json.loads(json.dumps(verify_hash_chain_ledger(ledger_path)))
    published = next(event for event in events if event["event_type"] == "published")
    if mutation == "decision":
        published["payload"]["decision"] = "forged"
    elif mutation == "gates":
        published["payload"]["gates"] = {"forged": True}
    elif mutation == "json_sha256":
        published["payload"]["json_sha256"] = "f" * 64
    else:
        published["payload"]["json_path"] = str(tmp_path / "forged.json")
    ledger_path.unlink()
    _rechain_events(ledger_path, events)

    with pytest.raises(V10DiagnosticError, match="published"):
        validate_v10_ledger_state_machine(ledger_path, expected_targets=2)


def test_ledger_state_machine_rebuilds_scientific_report_from_scored_events(
    tmp_path: Path,
) -> None:
    result = run_v10_historical(
        _synthetic_request(
            tmp_path,
            actuals=[(44, 45, 46, 47, 48, 49), (38, 39, 40, 41, 42, 43)],
        )
    )
    report_path = Path(result["json_path"])
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["per_target"][0]["actual_main"] = [1, 2, 3, 4, 5, 6]
    report["scopes"]["aggregate"][diagnostics.CANDIDATE_MODEL][
        "avg_top12_hits"
    ] = 99.0
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    ledger_path = Path(result["ledger_path"])
    events = json.loads(json.dumps(verify_hash_chain_ledger(ledger_path)))
    published = next(event for event in events if event["event_type"] == "published")
    published["payload"]["json_sha256"] = diagnostics._file_sha256(report_path)
    ledger_path.unlink()
    _rechain_events(ledger_path, events)

    with pytest.raises(V10DiagnosticError, match="scientific report"):
        validate_v10_ledger_state_machine(ledger_path, expected_targets=2)


def test_ledger_state_machine_rejects_forged_report_gates_and_alert(
    tmp_path: Path,
) -> None:
    result = run_v10_historical(
        _synthetic_request(
            tmp_path,
            actuals=[(44, 45, 46, 47, 48, 49), (38, 39, 40, 41, 42, 43)],
        )
    )
    report_path = Path(result["json_path"])
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["historical_decision"]["gates"] = {"forged": True}
    report["historical_decision"]["all_scientific_gates_passed"] = True
    report["historical_decision"][
        "decision"
    ] = "eligible_for_separate_reviewed_shadow_decision"
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    ledger_path = Path(result["ledger_path"])
    events = json.loads(json.dumps(verify_hash_chain_ledger(ledger_path)))
    published = next(event for event in events if event["event_type"] == "published")
    published["payload"].update(
        {
            "all_scientific_gates_passed": True,
            "decision": "eligible_for_separate_reviewed_shadow_decision",
            "gates": {"forged": True},
            "json_sha256": diagnostics._file_sha256(report_path),
        }
    )
    events.append(
        {
            "event_type": "all_scientific_gates_alert_attempted",
            "payload": {
                "email_dispatched": True,
                "notification_warnings": [],
                "subject": "[LOTTO649] 【历史严格回测】V10全部统计门槛通过",
            },
        }
    )
    ledger_path.unlink()
    _rechain_events(ledger_path, events)

    with pytest.raises(V10DiagnosticError, match="scientific report"):
        validate_v10_ledger_state_machine(ledger_path, expected_targets=2)


def test_ledger_state_machine_rejects_forged_activation_status_in_report(
    tmp_path: Path,
) -> None:
    result = run_v10_historical(
        _synthetic_request(
            tmp_path,
            actuals=[(44, 45, 46, 47, 48, 49), (38, 39, 40, 41, 42, 43)],
        )
    )
    report_path = Path(result["json_path"])
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["live_roles"]["v10"] = "production_activated"
    report["prospective_cohort"]["status"] = "activated"
    report["notification_warnings"] = []
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    ledger_path = Path(result["ledger_path"])
    events = json.loads(json.dumps(verify_hash_chain_ledger(ledger_path)))
    published = next(event for event in events if event["event_type"] == "published")
    published["payload"]["json_sha256"] = diagnostics._file_sha256(report_path)
    ledger_path.unlink()
    _rechain_events(ledger_path, events)

    with pytest.raises(V10DiagnosticError, match="report"):
        validate_v10_ledger_state_machine(ledger_path, expected_targets=2)


def test_ledger_state_machine_rejects_forged_markdown_even_when_rehashed(
    tmp_path: Path,
) -> None:
    result = run_v10_historical(
        _synthetic_request(
            tmp_path,
            actuals=[(44, 45, 46, 47, 48, 49), (38, 39, 40, 41, 42, 43)],
        )
    )
    markdown_path = Path(result["markdown_path"])
    markdown_path.write_text("# V10 ACTIVATED IN PRODUCTION\n", encoding="utf-8")
    ledger_path = Path(result["ledger_path"])
    events = json.loads(json.dumps(verify_hash_chain_ledger(ledger_path)))
    published = next(event for event in events if event["event_type"] == "published")
    published["payload"]["markdown_sha256"] = diagnostics._file_sha256(
        markdown_path
    )
    ledger_path.unlink()
    _rechain_events(ledger_path, events)

    with pytest.raises(V10DiagnosticError, match="Markdown"):
        validate_v10_ledger_state_machine(ledger_path, expected_targets=2)


@pytest.mark.parametrize("audit_mode", ["empty", "exception", "malformed"])
def test_6of6_invalid_or_exception_audit_always_uses_dedicated_archive_terminal(
    tmp_path: Path,
    audit_mode: str,
) -> None:
    request = _synthetic_request(tmp_path, actuals=[(1, 2, 3, 4, 5, 6)])

    def audit(_target, _forecast, _actual):
        if audit_mode == "exception":
            raise RuntimeError("synthetic audit crash")
        if audit_mode == "malformed":
            return "not-a-mapping"
        return {"clear": True, "checks": []}

    replacement = dict(request.__dict__)
    replacement["leakage_audit"] = audit
    result = run_v10_historical(V10DiagnosticRequest(**replacement))

    assert result["status"] == (
        "historical_6of6_candidate_archived_leakage_failed"
    )
    bundle = json.loads(Path(result["bundle_path"]).read_text())
    assert bundle["leakage_audit"]["clear"] is False
    assert bundle["leakage_audit"]["schema_errors"] or bundle[
        "leakage_audit"
    ]["callback_error"]
    events = verify_hash_chain_ledger(Path(result["ledger_path"]))
    assert events[-1]["event_type"] == (
        "historical_6of6_candidate_archived_leakage_failed"
    )


@pytest.mark.parametrize("audit_mode", ["extra_failed", "nan", "nonserializable"])
def test_6of6_extra_failure_or_noncanonical_audit_evidence_archives_safely(
    tmp_path: Path,
    audit_mode: str,
) -> None:
    request = _synthetic_request(tmp_path, actuals=[(1, 2, 3, 4, 5, 6)])

    def audit(_target, _forecast, _actual):
        checks = [
            {"name": name, "passed": True, "evidence": {"synthetic": True}}
            for name in diagnostics.REQUIRED_6OF6_AUDIT_CHECKS
        ]
        if audit_mode == "extra_failed":
            checks.append(
                {"name": "extra_adversarial_check", "passed": False, "evidence": "x"}
            )
        elif audit_mode == "nan":
            checks[0]["evidence"] = {"not_finite": math.nan}
        else:
            checks[0]["evidence"] = object()
        return {"clear": True, "checks": checks}

    replacement = dict(request.__dict__)
    replacement["leakage_audit"] = audit
    result = run_v10_historical(V10DiagnosticRequest(**replacement))

    assert result["status"] == "historical_6of6_candidate_archived_leakage_failed"
    bundle_bytes = Path(result["bundle_path"]).read_bytes()
    bundle = json.loads(bundle_bytes)
    assert bundle["leakage_audit"]["clear"] is False
    assert bundle["leakage_audit"]["schema_errors"]
    events = validate_v10_ledger_state_machine(
        Path(result["ledger_path"]),
        expected_targets=1,
    )
    assert events[-1]["event_type"] == (
        "historical_6of6_candidate_archived_leakage_failed"
    )


def test_6of6_email_contains_complete_three_model_target_benchmark(tmp_path: Path) -> None:
    notifications: list[tuple[str, str]] = []
    request = _synthetic_request(
        tmp_path,
        actuals=[(1, 2, 3, 4, 5, 6)],
        notifications=notifications,
    )

    result = run_v10_historical(request)

    assert result["status"] == "historical_6of6_candidate_published"
    _subject, body = notifications[-1]
    for required in (
        "v10_adjacent_pair_structure",
        "v10_adjacency_label_bijection_control",
        "random",
        "Top6=",
        "Top12=",
        "Top18=",
        "Brier=",
        "LogLoss=",
        "joint_log_gain=",
        "理论公平期望",
    ):
        assert required in body


@pytest.mark.parametrize("audit_clear", [True, False])
def test_6of6_terminal_receipt_cannot_hide_notification_failure(
    tmp_path: Path,
    audit_clear: bool,
) -> None:
    request = _synthetic_request(
        tmp_path,
        actuals=[(1, 2, 3, 4, 5, 6)],
        audit_clear=audit_clear,
    )
    terminal_bytes_seen: list[bytes] = []

    def notifier(_subject: str, _body: str) -> bool:
        ledger_path = V10ArtifactPaths.in_directory(tmp_path).ledger
        terminal = verify_hash_chain_ledger(ledger_path)[-1]
        assert terminal["event_type"] in {
            "historical_6of6_candidate_published",
            "historical_6of6_candidate_archived_leakage_failed",
        }
        assert terminal["payload"]["notification_status"] == (
            "pending_external_receipt"
        )
        terminal_bytes_seen.append(ledger_path.read_bytes())
        return False

    replacement = dict(request.__dict__)
    replacement["notifier"] = notifier
    result = run_v10_historical(V10DiagnosticRequest(**replacement))
    ledger_path = Path(result["ledger_path"])
    events = json.loads(json.dumps(verify_hash_chain_ledger(ledger_path)))
    assert events[-1]["payload"]["email_dispatched"] is False
    assert events[-1]["payload"]["notification_warnings"]
    assert terminal_bytes_seen == [ledger_path.read_bytes()]
    events[-1]["payload"]["notification_warnings"] = []
    ledger_path.unlink()
    _rechain_events(ledger_path, events)

    with pytest.raises(V10DiagnosticError, match="6/6 terminal notification"):
        validate_v10_ledger_state_machine(ledger_path, expected_targets=1)


@pytest.mark.parametrize("audit_clear", [True, False])
def test_6of6_terminal_cannot_drop_warning_derived_from_progress_outbox(
    tmp_path: Path,
    audit_clear: bool,
) -> None:
    request = _synthetic_request(
        tmp_path,
        actuals=[(1, 2, 44, 45, 46, 47), (1, 2, 3, 4, 5, 6)],
        audit_clear=audit_clear,
    )
    replacement = dict(request.__dict__)
    replacement["notifier"] = lambda _subject, _body: False
    result = run_v10_historical(V10DiagnosticRequest(**replacement))

    ledger_path = Path(result["ledger_path"])
    events = json.loads(json.dumps(verify_hash_chain_ledger(ledger_path)))
    progress = next(
        event for event in events if event["event_type"] == "progress_notification_outbox"
    )
    terminal = events[-1]["payload"]
    assert terminal["notification_warnings_before_terminal"] == progress["payload"][
        "notification_warnings"
    ]
    terminal["notification_warnings_before_terminal"] = []
    terminal["notification_warnings"] = [terminal["notification_warnings"][-1]]
    ledger_path.unlink()
    _rechain_events(ledger_path, events)

    with pytest.raises(V10DiagnosticError, match="6/6 terminal notification"):
        validate_v10_ledger_state_machine(ledger_path, expected_targets=2)


def test_normal_publication_warnings_are_derived_from_progress_outbox(
    tmp_path: Path,
) -> None:
    request = _synthetic_request(
        tmp_path,
        actuals=[(1, 2, 44, 45, 46, 47), (38, 39, 40, 41, 42, 43)],
    )
    replacement = dict(request.__dict__)
    replacement["notifier"] = lambda _subject, _body: False
    result = run_v10_historical(V10DiagnosticRequest(**replacement))

    ledger_path = Path(result["ledger_path"])
    events = json.loads(json.dumps(verify_hash_chain_ledger(ledger_path)))
    assert any(
        event["event_type"] == "progress_notification_outbox" for event in events
    )
    publication = next(
        event for event in events if event["event_type"] == "publication_started"
    )
    publication["payload"]["notification_warnings"] = []
    ledger_path.unlink()
    _rechain_events(ledger_path, events)

    with pytest.raises(V10DiagnosticError, match="publication_started"):
        validate_v10_ledger_state_machine(ledger_path, expected_targets=2)


@pytest.mark.parametrize("notifier_mode", ["false", "exception"])
def test_post_publication_significance_notification_failure_is_durable_in_ledger(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    notifier_mode: str,
) -> None:
    request = _synthetic_request(
        tmp_path,
        actuals=[(44, 45, 46, 47, 48, 49), (38, 39, 40, 41, 42, 43)],
    )
    monkeypatch.setattr(
        diagnostics,
        "v10_historical_decision",
        lambda **_kwargs: {
            "decision": "eligible_for_separate_reviewed_shadow_decision",
            "evidence_lane": "consumed_historical_diagnostic",
            "all_scientific_gates_passed": True,
            "gates": {
                name: True for name in diagnostics.HISTORICAL_GATE_NAMES
            },
            "proper_score_max_delta_vs_fair": 1.0e-9,
            "prospective_status": "not_activated",
            "live_role": "none",
        },
    )

    terminal_bytes_seen: list[bytes] = []

    def notifier(_subject: str, _body: str) -> bool:
        ledger_path = V10ArtifactPaths.in_directory(tmp_path).ledger
        terminal = verify_hash_chain_ledger(ledger_path)[-1]
        assert terminal["event_type"] == "published"
        assert terminal["payload"]["notification_status"] == (
            "pending_external_receipt"
        )
        terminal_bytes_seen.append(ledger_path.read_bytes())
        if notifier_mode == "exception":
            raise RuntimeError("synthetic notification crash")
        return False

    replacement = dict(request.__dict__)
    replacement["notifier"] = notifier
    result = run_v10_historical(V10DiagnosticRequest(**replacement))

    events = verify_hash_chain_ledger(Path(result["ledger_path"]))
    assert terminal_bytes_seen == [Path(result["ledger_path"]).read_bytes()]
    assert events[-1]["event_type"] == "published"
    assert events[-1]["payload"]["email_dispatched"] is False
    assert events[-1]["payload"]["notification_status"] == (
        "pending_external_receipt"
    )
    assert events[-1]["payload"]["notification_warnings"][-1].startswith(
        "notification_pending_external_receipt:"
    )
    assert events[-1]["payload"]["notification_warnings"]
    assert result["notification_warnings"]
    assert result["notification_dispatched_after_terminal"] is False
    assert result["report"]["post_publication_notification"][
        "request_recorded_in_attempt_ledger_event"
    ] == "published"
    assert result["report"]["notification_status_at_report_publication"] == (
        "pending_post_publication"
    )
    assert result["report"]["notification_result_authority"] == (
        "external_workflow_receipt_after_terminal"
    )


def test_normal_success_alert_waits_for_last_fallible_artifact_validation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    notifications: list[tuple[str, str]] = []
    request = _synthetic_request(
        tmp_path,
        actuals=[(44, 45, 46, 47, 48, 49), (38, 39, 40, 41, 42, 43)],
        notifications=notifications,
    )
    monkeypatch.setattr(
        diagnostics,
        "v10_historical_decision",
        lambda **_kwargs: {
            "decision": "eligible_for_separate_reviewed_shadow_decision",
            "evidence_lane": "consumed_historical_diagnostic",
            "all_scientific_gates_passed": True,
            "gates": {
                name: True for name in diagnostics.HISTORICAL_GATE_NAMES
            },
            "proper_score_max_delta_vs_fair": 1.0e-9,
            "prospective_status": "not_activated",
            "live_role": "none",
        },
    )
    original_validator = diagnostics.validate_v10_ledger_state_machine
    calls = 0

    def fail_second_validation(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("synthetic post-publication validation failure")
        return original_validator(*args, **kwargs)

    monkeypatch.setattr(
        diagnostics,
        "validate_v10_ledger_state_machine",
        fail_second_validation,
    )

    with pytest.raises(OSError, match="post-publication validation"):
        run_v10_historical(request)

    events = verify_hash_chain_ledger(V10ArtifactPaths.in_directory(tmp_path).ledger)
    assert notifications == []
    assert events[-1]["event_type"] == "failed"
    assert not any(event["event_type"] == "published" for event in events)
    assert original_validator(
        V10ArtifactPaths.in_directory(tmp_path).ledger,
        expected_targets=2,
    ) == events


def test_normal_terminal_append_failure_never_calls_success_notifier(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    notifications: list[tuple[str, str]] = []
    request = _synthetic_request(
        tmp_path,
        actuals=[(44, 45, 46, 47, 48, 49), (38, 39, 40, 41, 42, 43)],
        notifications=notifications,
    )
    monkeypatch.setattr(
        diagnostics,
        "v10_historical_decision",
        lambda **_kwargs: {
            "decision": "eligible_for_separate_reviewed_shadow_decision",
            "evidence_lane": "consumed_historical_diagnostic",
            "all_scientific_gates_passed": True,
            "gates": {
                name: True for name in diagnostics.HISTORICAL_GATE_NAMES
            },
            "proper_score_max_delta_vs_fair": 1.0e-9,
            "prospective_status": "not_activated",
            "live_role": "none",
        },
    )
    original_append = HashChainLedger.append
    terminal_failed = False

    def fail_first_terminal_append(self, event_type, payload):
        nonlocal terminal_failed
        if event_type == "published" and not terminal_failed:
            terminal_failed = True
            raise OSError("synthetic terminal fsync failure")
        return original_append(self, event_type, payload)

    monkeypatch.setattr(HashChainLedger, "append", fail_first_terminal_append)

    with pytest.raises(OSError, match="terminal fsync"):
        run_v10_historical(request)

    events = verify_hash_chain_ledger(V10ArtifactPaths.in_directory(tmp_path).ledger)
    assert notifications == []
    assert events[-1]["event_type"] == "failed"


@pytest.mark.parametrize("audit_clear", [True, False])
def test_6of6_terminal_append_failure_never_calls_notifier(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    audit_clear: bool,
) -> None:
    notifications: list[tuple[str, str]] = []
    request = _synthetic_request(
        tmp_path,
        actuals=[(1, 2, 3, 4, 5, 6)],
        audit_clear=audit_clear,
        notifications=notifications,
    )
    terminal_type = (
        "historical_6of6_candidate_published"
        if audit_clear
        else "historical_6of6_candidate_archived_leakage_failed"
    )
    original_append = HashChainLedger.append
    terminal_failed = False

    def fail_first_terminal_append(self, event_type, payload):
        nonlocal terminal_failed
        if event_type == terminal_type and not terminal_failed:
            terminal_failed = True
            raise OSError("synthetic 6of6 terminal fsync failure")
        return original_append(self, event_type, payload)

    monkeypatch.setattr(HashChainLedger, "append", fail_first_terminal_append)

    with pytest.raises(OSError, match="6of6 terminal fsync"):
        run_v10_historical(request)

    events = verify_hash_chain_ledger(V10ArtifactPaths.in_directory(tmp_path).ledger)
    assert notifications == []
    assert events[-1]["event_type"] == "failed"


def test_normal_success_receipt_is_the_unique_last_event(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    notifications: list[tuple[str, str]] = []
    request = _synthetic_request(
        tmp_path,
        actuals=[(44, 45, 46, 47, 48, 49), (38, 39, 40, 41, 42, 43)],
        notifications=notifications,
    )
    monkeypatch.setattr(
        diagnostics,
        "v10_historical_decision",
        lambda **_kwargs: {
            "decision": "eligible_for_separate_reviewed_shadow_decision",
            "evidence_lane": "consumed_historical_diagnostic",
            "all_scientific_gates_passed": True,
            "gates": {
                name: True for name in diagnostics.HISTORICAL_GATE_NAMES
            },
            "proper_score_max_delta_vs_fair": 1.0e-9,
            "prospective_status": "not_activated",
            "live_role": "none",
        },
    )
    original_validator = diagnostics.validate_v10_ledger_state_machine
    calls = 0

    def reject_post_terminal_validation(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls > 2:
            raise AssertionError("validator called after terminal receipt")
        return original_validator(*args, **kwargs)

    monkeypatch.setattr(
        diagnostics,
        "validate_v10_ledger_state_machine",
        reject_post_terminal_validation,
    )

    result = run_v10_historical(request)

    events = verify_hash_chain_ledger(Path(result["ledger_path"]))
    assert calls == 2
    assert len(notifications) == 1
    assert events[-1]["event_type"] == "published"
    assert events[-1]["payload"]["email_dispatched"] is False
    assert events[-1]["payload"]["notification_status"] == (
        "pending_external_receipt"
    )
    assert result["notification_dispatched_after_terminal"] is True
    assert events[-1]["payload"]["notification_request"] == {
        "body": notifications[0][1],
        "subject": notifications[0][0],
    }
    assert not any(
        event["event_type"] == "all_scientific_gates_alert_attempted"
        for event in events
    )
    assert original_validator(Path(result["ledger_path"]), expected_targets=2) == events


@pytest.mark.parametrize("email_sent", [False, True])
def test_normal_terminal_receipt_cannot_hide_or_forge_notification_warning(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    email_sent: bool,
) -> None:
    request = _synthetic_request(
        tmp_path,
        actuals=[(44, 45, 46, 47, 48, 49), (38, 39, 40, 41, 42, 43)],
    )
    replacement = dict(request.__dict__)
    replacement["notifier"] = lambda _subject, _body: email_sent
    monkeypatch.setattr(
        diagnostics,
        "v10_historical_decision",
        lambda **_kwargs: {
            "decision": "eligible_for_separate_reviewed_shadow_decision",
            "evidence_lane": "consumed_historical_diagnostic",
            "all_scientific_gates_passed": True,
            "gates": {
                name: True for name in diagnostics.HISTORICAL_GATE_NAMES
            },
            "proper_score_max_delta_vs_fair": 1.0e-9,
            "prospective_status": "not_activated",
            "live_role": "none",
        },
    )
    result = run_v10_historical(V10DiagnosticRequest(**replacement))
    ledger_path = Path(result["ledger_path"])
    events = json.loads(json.dumps(verify_hash_chain_ledger(ledger_path)))
    terminal = events[-1]["payload"]
    if email_sent:
        terminal["notification_warnings"].append("notification_not_sent:forged")
    else:
        terminal["notification_warnings"] = []
    ledger_path.unlink()
    _rechain_events(ledger_path, events)

    with pytest.raises(V10DiagnosticError, match="notification receipt"):
        validate_v10_ledger_state_machine(ledger_path, expected_targets=2)


def test_normal_terminal_receipt_cannot_drop_prepublication_warnings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _synthetic_request(
        tmp_path,
        actuals=[(1, 2, 44, 45, 46, 47), (38, 39, 40, 41, 42, 43)],
    )
    notification_results = iter((False, False))
    replacement = dict(request.__dict__)
    replacement["notifier"] = lambda _subject, _body: next(notification_results)
    monkeypatch.setattr(
        diagnostics,
        "v10_historical_decision",
        lambda **_kwargs: {
            "decision": "eligible_for_separate_reviewed_shadow_decision",
            "evidence_lane": "consumed_historical_diagnostic",
            "all_scientific_gates_passed": True,
            "gates": {
                name: True for name in diagnostics.HISTORICAL_GATE_NAMES
            },
            "proper_score_max_delta_vs_fair": 1.0e-9,
            "prospective_status": "not_activated",
            "live_role": "none",
        },
    )
    result = run_v10_historical(V10DiagnosticRequest(**replacement))
    ledger_path = Path(result["ledger_path"])
    events = json.loads(json.dumps(verify_hash_chain_ledger(ledger_path)))
    publication = next(
        event for event in events if event["event_type"] == "publication_started"
    )
    assert publication["payload"]["notification_warnings"]
    assert events[-1]["payload"]["email_dispatched"] is False
    assert len(events[-1]["payload"]["notification_warnings"]) == 2
    events[-1]["payload"]["notification_warnings"][0] = (
        "notification_not_sent:forged_replacement"
    )
    ledger_path.unlink()
    _rechain_events(ledger_path, events)

    with pytest.raises(V10DiagnosticError, match="published"):
        validate_v10_ledger_state_machine(ledger_path, expected_targets=2)


@pytest.mark.parametrize("mutation", ["request", "idempotency_key"])
def test_normal_terminal_outbox_request_and_idempotency_are_rebuilt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    request = _synthetic_request(
        tmp_path,
        actuals=[(44, 45, 46, 47, 48, 49), (38, 39, 40, 41, 42, 43)],
    )
    monkeypatch.setattr(
        diagnostics,
        "v10_historical_decision",
        lambda **_kwargs: {
            "decision": "eligible_for_separate_reviewed_shadow_decision",
            "evidence_lane": "consumed_historical_diagnostic",
            "all_scientific_gates_passed": True,
            "gates": {
                name: True for name in diagnostics.HISTORICAL_GATE_NAMES
            },
            "proper_score_max_delta_vs_fair": 1.0e-9,
            "prospective_status": "not_activated",
            "live_role": "none",
        },
    )
    result = run_v10_historical(request)
    ledger_path = Path(result["ledger_path"])
    events = json.loads(json.dumps(verify_hash_chain_ledger(ledger_path)))
    if mutation == "request":
        events[-1]["payload"]["notification_request"]["body"] = "forged activation"
    else:
        events[-1]["payload"]["notification_idempotency_key"] = "f" * 64
    ledger_path.unlink()
    _rechain_events(ledger_path, events)

    with pytest.raises(V10DiagnosticError, match="notification"):
        validate_v10_ledger_state_machine(ledger_path, expected_targets=2)
