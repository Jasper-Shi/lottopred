import json
from dataclasses import dataclass
from datetime import date, timedelta
from hashlib import sha256
from pathlib import Path

import pandas as pd
import pytest

from lotto649.config import load_config
from lotto649.domain import Draw
from lotto649.research_diagnostics import (
    _publish_v8_report_pair,
    paired_top12_lift_interval,
    run_registered_v8_diagnostics,
    v8_historical_decision,
)
from lotto649.research_protocol import load_experiment_registry


ROOT = Path(__file__).resolve().parents[1]
V8_EXPERIMENT_ID = "V8_fixed_recurrence_harmonic"
V8_VERSION = "v8.0.0"
V8_CANDIDATE = "v8_spectral_phase"
V8_ROW_CONTROL = "v8_spectral_phase_row_control"
V8_PHASE_CONTROL = "v8_spectral_phase_rotation_control"
V8_REPORT_STEM = "v8_spectral_phase_v8.0.0_historical"


def _paired_frame(model_name: str, dates: list[str], hits: list[int]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "target_draw_date": dates,
            "model_name": [model_name] * len(dates),
            "top_12_hits": hits,
        }
    )


def test_paired_top12_bootstrap_matches_frozen_literal_oracle():
    dates = [f"2020-01-{day:02d}" for day in range(1, 6)]
    candidate = _paired_frame("v8_spectral_phase", dates, [4, 0, 5, 2, 4])
    control = _paired_frame(
        "v8_spectral_phase_row_control", dates, [3, 2, 2, 2, 2]
    )

    result = paired_top12_lift_interval(
        candidate,
        control,
        resamples=10_000,
        seed=649,
    )

    assert result == {
        "draws": 5,
        "mean_candidate_minus_row_control_top12_hits": pytest.approx(0.8),
        "bootstrap_95_ci": pytest.approx([-0.8, 2.2]),
        "bootstrap_resamples": 10_000,
        "bootstrap_seed": 649,
        "bootstrap_rng": "numpy.default_rng",
        "bootstrap_interval": "two_sided_95_percentile_linear",
    }


@pytest.mark.parametrize(
    ("candidate_dates", "control_dates", "message"),
    [
        (
            ["2020-01-01", "2020-01-02"],
            ["2020-01-02", "2020-01-01"],
            "identical ordered target dates",
        ),
        (
            ["2020-01-01", "2020-01-01"],
            ["2020-01-01", "2020-01-01"],
            "unique target dates",
        ),
        (
            ["2020-01-02", "2020-01-01"],
            ["2020-01-02", "2020-01-01"],
            "ascending target dates",
        ),
        (["not-a-date"], ["not-a-date"], "ISO target-date strings"),
        (["2020-01-01"], ["2020-01-01", "2020-01-02"], "row count"),
    ],
)
def test_paired_top12_bootstrap_rejects_reordered_duplicate_or_unpaired_inputs(
    candidate_dates,
    control_dates,
    message,
):
    candidate = _paired_frame("v8_spectral_phase", candidate_dates, [2] * len(candidate_dates))
    control = _paired_frame(
        "v8_spectral_phase_row_control",
        control_dates,
        [1] * len(control_dates),
    )

    with pytest.raises(RuntimeError, match=message):
        paired_top12_lift_interval(candidate, control, resamples=10_000, seed=649)


def _summary(*, control_null: bool | None = None) -> dict:
    result = {
        "primary_top12_lift_vs_theory": 0.1,
        "primary_holm_adjusted_p": 0.01,
        "primary_bootstrap_95_ci": [0.01, 0.2],
        "brier_delta_vs_fair": 0.0,
        "log_loss_delta_vs_fair": 0.0,
    }
    if control_null is not None:
        result["behaves_as_null"] = control_null
    return result


def _decision_payload() -> dict:
    return {
        "candidate": _summary(),
        "stability_halves": [
            {"candidate": _summary()},
            {"candidate": _summary()},
        ],
        "row_control": _summary(control_null=True),
        "row_control_halves": [
            _summary(control_null=True),
            _summary(control_null=True),
        ],
        "phase_control": _summary(control_null=True),
        "phase_control_halves": [
            _summary(control_null=True),
            _summary(control_null=True),
        ],
        "paired_candidate_minus_row_control": {
            "bootstrap_95_ci": [0.01, 0.2]
        },
        "paired_candidate_minus_row_control_halves": [
            {"bootstrap_95_ci": [0.01, 0.2]},
            {"bootstrap_95_ci": [0.01, 0.2]},
        ],
        "audit_warnings": [],
    }


V8_GATE_KEYS = {
    "positive_aggregate_primary_lift",
    "aggregate_holm_adjusted_p_at_most_0_05",
    "aggregate_bootstrap_lower_above_zero",
    "positive_primary_lift_in_both_fixed_halves",
    "proper_scores_within_fair_tolerance_aggregate_and_halves",
    "row_control_null_and_candidate_outperforms_it",
    "phase_control_null_aggregate_and_halves",
    "audit_clear",
}


def test_v8_historical_decision_requires_all_eight_frozen_gates():
    decision, warnings = v8_historical_decision(
        _decision_payload(), proper_score_tolerance=1.0e-9
    )

    assert warnings == []
    assert set(decision["gates"]) == V8_GATE_KEYS
    assert all(decision["gates"].values())
    assert decision["decision"] == "eligible_for_reviewed_shadow_activation"
    assert decision["shadow_activation"] == "not_activated"

    failed = _decision_payload()
    failed["paired_candidate_minus_row_control_halves"][1]["bootstrap_95_ci"][0] = 0.0
    decision, warnings = v8_historical_decision(
        failed, proper_score_tolerance=1.0e-9
    )

    assert warnings == []
    assert decision["decision"] == "reject"
    assert decision["gates"]["row_control_null_and_candidate_outperforms_it"] is False


def test_v8_historical_decision_records_each_non_null_control_as_warning():
    payload = _decision_payload()
    payload["row_control_halves"][0]["behaves_as_null"] = False
    payload["phase_control"]["behaves_as_null"] = False

    decision, warnings = v8_historical_decision(
        payload, proper_score_tolerance=1.0e-9
    )

    assert warnings == [
        "row_control_non_null:1",
        "phase_control_non_null:0",
    ]
    assert decision["gates"]["row_control_null_and_candidate_outperforms_it"] is False
    assert decision["gates"]["phase_control_null_aggregate_and_halves"] is False
    assert decision["gates"]["audit_clear"] is False


@pytest.mark.parametrize(
    ("case", "expected_false_gates"),
    [
        ("aggregate_lift", {"positive_aggregate_primary_lift"}),
        ("holm", {"aggregate_holm_adjusted_p_at_most_0_05"}),
        ("aggregate_interval", {"aggregate_bootstrap_lower_above_zero"}),
        ("half_lift", {"positive_primary_lift_in_both_fixed_halves"}),
        (
            "proper_score",
            {"proper_scores_within_fair_tolerance_aggregate_and_halves"},
        ),
        (
            "paired_row_interval",
            {"row_control_null_and_candidate_outperforms_it"},
        ),
        (
            "phase_control",
            {"phase_control_null_aggregate_and_halves", "audit_clear"},
        ),
        ("audit_warning", {"audit_clear"}),
    ],
)
def test_v8_historical_decision_has_no_rescue_for_any_frozen_gate(
    case,
    expected_false_gates,
):
    payload = _decision_payload()
    if case == "aggregate_lift":
        payload["candidate"]["primary_top12_lift_vs_theory"] = 0.0
    elif case == "holm":
        payload["candidate"]["primary_holm_adjusted_p"] = 0.0500001
    elif case == "aggregate_interval":
        payload["candidate"]["primary_bootstrap_95_ci"][0] = 0.0
    elif case == "half_lift":
        payload["stability_halves"][1]["candidate"][
            "primary_top12_lift_vs_theory"
        ] = 0.0
    elif case == "proper_score":
        payload["stability_halves"][0]["candidate"]["brier_delta_vs_fair"] = (
            1.1e-9
        )
    elif case == "paired_row_interval":
        payload["paired_candidate_minus_row_control_halves"][0][
            "bootstrap_95_ci"
        ][0] = 0.0
    elif case == "phase_control":
        payload["phase_control_halves"][1]["behaves_as_null"] = False
    elif case == "audit_warning":
        payload["audit_warnings"] = ["synthetic_integrity_warning"]
    else:  # pragma: no cover - the parametrization is exhaustive
        raise AssertionError(case)

    decision, _warnings = v8_historical_decision(
        payload,
        proper_score_tolerance=1.0e-9,
    )

    false_gates = {
        name for name, passed in decision["gates"].items() if not passed
    }
    assert false_gates == expected_false_gates
    assert decision["decision"] == "reject"
    assert decision["shadow_activation"] == "not_activated"


def _numbers(index: int) -> tuple[int, ...]:
    return tuple(
        sorted((((index * 7) + offset * 8) % 49) + 1 for offset in range(6))
    )


def _draw(draw_date: date, index: int) -> Draw:
    numbers = _numbers(index)
    bonus = next(number for number in range(1, 50) if number not in numbers)
    return Draw(draw_date, numbers, bonus)


def _synthetic_registered_draws() -> list[Draw]:
    draws = [
        *[
            _draw(date(2016, 1, 1) + timedelta(days=3 * index), index)
            for index in range(300)
        ],
        *[
            _draw(date(2019, 5, 15) + timedelta(days=3 * index), 300 + index)
            for index in range(65)
        ],
        *[
            _draw(date(2020, 1, 1) + timedelta(days=3 * index), 365 + index)
            for index in range(39)
        ],
        _draw(date(2020, 5, 20), 404),
        *[
            _draw(date(2020, 5, 23) + timedelta(days=3 * index), 405 + index)
            for index in range(267)
        ],
        *[
            _draw(date(2023, 1, 1) + timedelta(days=3 * index), 672 + index)
            for index in range(313)
        ],
        _draw(date(2025, 12, 31), 985),
        _draw(date(2026, 8, 12), 986),
    ]
    assert len(
        [draw for draw in draws if date(2020, 1, 1) <= draw.draw_date <= date(2025, 12, 31)]
    ) == 621
    return draws


def _diagnostic_frame(draws: list[Draw], model_name: str, top12_hits: int) -> pd.DataFrame:
    from lotto649.research_diagnostics import fair_constant_scores

    targets = [
        draw
        for draw in draws
        if date(2020, 1, 1) <= draw.draw_date <= date(2025, 12, 31)
    ]
    fair_brier, fair_log_loss = fair_constant_scores()
    return pd.DataFrame(
        {
            "target_draw_date": [draw.draw_date.isoformat() for draw in targets],
            "model_name": [model_name] * len(targets),
            "model_version": [V8_VERSION] * len(targets),
            "actual": [list(draw.numbers) for draw in targets],
            "bonus": [draw.bonus for draw in targets],
            "final_6_hits": [1] * len(targets),
            "top_6_hits": [1] * len(targets),
            "top_12_hits": [top12_hits] * len(targets),
            "top_18_hits": [max(2, top12_hits)] * len(targets),
            "brier_score": [fair_brier] * len(targets),
            "log_loss": [fair_log_loss] * len(targets),
            "mean_actual_rank": [25.0] * len(targets),
        }
    )


@dataclass(frozen=True)
class _BoundaryEvidence:
    registration_prefix_preserved: bool = True
    draws_fingerprint: str = "b" * 64


@dataclass
class _RunnerEnvironment:
    root: Path
    cfg: dict
    draws: list[Draw]
    output_dir: Path
    reference_report: Path
    reference_claim: Path


def _runner_environment(tmp_path: Path) -> _RunnerEnvironment:
    root = tmp_path / "repo"
    config_path = root / "config" / "research-v8-fixed-spectral-phase.yaml"
    config_path.parent.mkdir(parents=True)
    config_path.write_bytes(
        (ROOT / "config" / "research-v8-fixed-spectral-phase.yaml").read_bytes()
    )
    cfg = load_config(config_path)
    cfg["_root"] = root
    output_dir = root / "reports"
    output_dir.mkdir(parents=True)
    reference_report = output_dir / "v7_main_bonus_role_bias_v7.0.0_historical.json"
    reference_claim = output_dir / "v7_main_bonus_role_bias_v7.0.0_historical.claim"
    reference_report.write_bytes(
        (ROOT / "reports" / reference_report.name).read_bytes()
    )
    reference_claim.write_bytes((ROOT / "reports" / reference_claim.name).read_bytes())
    return _RunnerEnvironment(
        root=root,
        cfg=cfg,
        draws=_synthetic_registered_draws(),
        output_dir=output_dir,
        reference_report=reference_report,
        reference_claim=reference_claim,
    )


def _install_runner_mocks(monkeypatch, environment: _RunnerEnvironment, mutate=None):
    calls = []
    registry = load_experiment_registry(ROOT / "docs" / "experiments" / "registry.yaml")
    monkeypatch.setattr(
        "lotto649.research_diagnostics._validate_v8_git_audit",
        lambda _root, _commit: None,
    )

    def committed_bytes(_root, _commit, relative_path):
        relative = Path(relative_path).as_posix()
        if relative == "config/research-v8-fixed-spectral-phase.yaml":
            return Path(environment.cfg["_config_path"]).read_bytes()
        if relative == f"reports/{environment.reference_report.name}":
            return environment.reference_report.read_bytes()
        if relative == f"reports/{environment.reference_claim.name}":
            return environment.reference_claim.read_bytes()
        pytest.fail(f"unexpected committed-file request: {relative}")

    monkeypatch.setattr(
        "lotto649.research_diagnostics._read_v6_committed_file_bytes",
        committed_bytes,
    )
    monkeypatch.setattr(
        "lotto649.research_diagnostics.load_experiment_registry",
        lambda _path: registry,
    )
    monkeypatch.setattr(
        "lotto649.research_diagnostics._validate_v8_outcome_boundaries",
        lambda _root, _registration: _BoundaryEvidence(),
    )
    monkeypatch.setattr(
        "lotto649.research_diagnostics.load_draws",
        lambda _path: environment.draws,
    )
    monkeypatch.setattr(
        "lotto649.research_diagnostics.validated_registered_draw_prefix",
        lambda _path, _draws, **_kwargs: tuple(environment.draws),
    )

    def fake_backtest(draws, cfg, start, end):
        model_name = cfg["backtest"]["models"][0]
        claim_path = environment.output_dir / f"{V8_REPORT_STEM}.claim"
        assert claim_path.is_file(), "claim must exist before first score"
        assert tuple(draws) == tuple(environment.draws)
        calls.append((model_name, start, end, tuple(draws)))
        top12 = 2 if model_name == V8_CANDIDATE else 1
        frame = _diagnostic_frame(environment.draws, model_name, top12)
        if mutate is not None:
            mutate(model_name, frame)
        return frame

    monkeypatch.setattr(
        "lotto649.research_diagnostics.run_backtest",
        fake_backtest,
    )
    return calls


def test_v8_runner_uses_three_identical_source_backtests_and_schema4(
    tmp_path,
    monkeypatch,
):
    environment = _runner_environment(tmp_path)
    calls = _install_runner_mocks(monkeypatch, environment)
    import lotto649.research_diagnostics as diagnostics

    real_build_models = diagnostics.build_models
    real_bootstrap = diagnostics.bootstrap_mean_lift_interval
    real_paired = diagnostics.paired_top12_lift_interval
    factory_calls = []
    bootstrap_calls = []
    paired_calls = []

    def traced_build_models(cfg, requested=None):
        assert not (environment.output_dir / f"{V8_REPORT_STEM}.claim").exists()
        factory_calls.append(tuple(requested or ()))
        return real_build_models(cfg, requested=requested)

    monkeypatch.setattr(diagnostics, "build_models", traced_build_models)

    def traced_bootstrap(hits, expectation, *, resamples, seed, chunk_size=256):
        bootstrap_calls.append((len(hits), resamples, seed))
        return real_bootstrap(
            hits,
            expectation,
            resamples=resamples,
            seed=seed,
            chunk_size=chunk_size,
        )

    def traced_paired(
        candidate_frame,
        row_control_frame,
        *,
        resamples,
        seed,
        chunk_size=256,
    ):
        paired_calls.append((len(candidate_frame), resamples, seed))
        return real_paired(
            candidate_frame,
            row_control_frame,
            resamples=resamples,
            seed=seed,
            chunk_size=chunk_size,
        )

    monkeypatch.setattr(diagnostics, "bootstrap_mean_lift_interval", traced_bootstrap)
    monkeypatch.setattr(diagnostics, "paired_top12_lift_interval", traced_paired)

    result = run_registered_v8_diagnostics(
        environment.cfg,
        code_commit="8" * 40,
        output_dir=environment.output_dir,
    )

    assert [(name, start, end) for name, start, end, _draws in calls] == [
        (V8_CANDIDATE, date(2020, 1, 1), date(2025, 12, 31)),
        (V8_ROW_CONTROL, date(2020, 1, 1), date(2025, 12, 31)),
        (V8_PHASE_CONTROL, date(2020, 1, 1), date(2025, 12, 31)),
    ]
    assert factory_calls == [
        (V8_CANDIDATE, V8_ROW_CONTROL, V8_PHASE_CONTROL)
    ]
    assert bootstrap_calls == [
        (621, 10_000, 649),
        (621, 10_000, 649),
        (621, 10_000, 649),
        (307, 10_000, 649),
        (307, 10_000, 649),
        (307, 10_000, 649),
        (314, 10_000, 649),
        (314, 10_000, 649),
        (314, 10_000, 649),
    ]
    assert paired_calls == [
        (621, 10_000, 649),
        (307, 10_000, 649),
        (314, 10_000, 649),
    ]
    assert calls[0][3] == calls[1][3] == calls[2][3] == tuple(environment.draws)
    report = result["report"]
    assert report["schema_version"] == 4
    assert report["activation"] == {
        "eligible_targets": 621,
        "fair_fallback_targets": 39,
        "active_targets": 582,
        "first_active_target": "2020-05-20",
        "excluded_targets": 0,
    }
    assert [half["target_count"] for half in report["stability_halves"]] == [307, 314]
    assert len(report["paired_candidate_minus_row_control_halves"]) == 2
    assert len(report["comparisons"]) == 11
    assert report["comparisons"][-1] == report["candidate"]
    assert report["prospective_cohort"]["status"] == "not_activated"
    assert report["historical_decision"]["shadow_activation"] == "not_activated"
    claim_path = environment.output_dir / f"{V8_REPORT_STEM}.claim"
    assert report["one_shot_claim"]["sha256"] == sha256(claim_path.read_bytes()).hexdigest()
    assert Path(result["json_path"]).is_file()
    assert Path(result["markdown_path"]).is_file()
    assert claim_path.is_file()

    with pytest.raises(RuntimeError, match="claim already exists"):
        run_registered_v8_diagnostics(
            environment.cfg,
            code_commit="8" * 40,
            output_dir=environment.output_dir,
        )
    assert len(calls) == 3


def test_v8_preflight_failure_occurs_before_claim_or_score(tmp_path, monkeypatch):
    environment = _runner_environment(tmp_path)
    calls = _install_runner_mocks(monkeypatch, environment)
    monkeypatch.setattr(
        "lotto649.research_diagnostics._validate_v8_registration_and_config",
        lambda _cfg, _registration: (_ for _ in ()).throw(
            RuntimeError("synthetic V8 preflight failure")
        ),
    )

    with pytest.raises(RuntimeError, match="synthetic V8 preflight failure"):
        run_registered_v8_diagnostics(
            environment.cfg,
            code_commit="8" * 40,
            output_dir=environment.output_dir,
        )

    assert calls == []
    assert not (environment.output_dir / f"{V8_REPORT_STEM}.claim").exists()
    assert not (environment.output_dir / f"{V8_REPORT_STEM}.json").exists()
    assert not (environment.output_dir / f"{V8_REPORT_STEM}.md").exists()


@pytest.mark.parametrize(
    "artifact_name",
    [
        f"{V8_REPORT_STEM}.claim",
        f"{V8_REPORT_STEM}.json",
        f"{V8_REPORT_STEM}.md",
        f".{V8_REPORT_STEM}.json.tmp",
        f".{V8_REPORT_STEM}.md.tmp",
    ],
)
def test_v8_runner_refuses_any_preexisting_attempt_artifact_before_score(
    artifact_name,
    tmp_path,
    monkeypatch,
):
    environment = _runner_environment(tmp_path)
    calls = _install_runner_mocks(monkeypatch, environment)
    artifact = environment.output_dir / artifact_name
    artifact.write_text("prior immutable attempt evidence\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="already exists|temporary report"):
        run_registered_v8_diagnostics(
            environment.cfg,
            code_commit="8" * 40,
            output_dir=environment.output_dir,
        )

    assert calls == []
    assert artifact.read_text(encoding="utf-8") == (
        "prior immutable attempt evidence\n"
    )


def test_v8_runner_rejects_noncanonical_output_before_score(tmp_path, monkeypatch):
    environment = _runner_environment(tmp_path)
    calls = _install_runner_mocks(monkeypatch, environment)
    alternate = environment.root / "alternate-reports"
    alternate.mkdir()

    with pytest.raises(RuntimeError, match="canonical repository reports"):
        run_registered_v8_diagnostics(
            environment.cfg,
            code_commit="8" * 40,
            output_dir=alternate,
        )

    assert calls == []
    assert not (environment.output_dir / f"{V8_REPORT_STEM}.claim").exists()


def test_v8_loaded_config_tamper_fails_before_claim_or_score(tmp_path, monkeypatch):
    environment = _runner_environment(tmp_path)
    calls = _install_runner_mocks(monkeypatch, environment)
    environment.cfg["research"]["fixed_angular_frequency"] = "10*pi/49"

    with pytest.raises(RuntimeError, match="loaded V8 config"):
        run_registered_v8_diagnostics(
            environment.cfg,
            code_commit="8" * 40,
            output_dir=environment.output_dir,
        )

    assert calls == []
    assert not (environment.output_dir / f"{V8_REPORT_STEM}.claim").exists()


@pytest.mark.parametrize("reference_kind", ["report", "claim"])
def test_v8_reference_tamper_fails_before_claim_or_score(
    reference_kind,
    tmp_path,
    monkeypatch,
):
    environment = _runner_environment(tmp_path)
    calls = _install_runner_mocks(monkeypatch, environment)
    path = (
        environment.reference_report
        if reference_kind == "report"
        else environment.reference_claim
    )
    path.write_bytes(path.read_bytes() + b"\n")

    with pytest.raises(RuntimeError, match="fingerprint mismatch"):
        run_registered_v8_diagnostics(
            environment.cfg,
            code_commit="8" * 40,
            output_dir=environment.output_dir,
        )

    assert calls == []
    assert not (environment.output_dir / f"{V8_REPORT_STEM}.claim").exists()


def test_v8_registered_prefix_failure_occurs_before_claim_or_score(
    tmp_path,
    monkeypatch,
):
    environment = _runner_environment(tmp_path)
    calls = _install_runner_mocks(monkeypatch, environment)
    monkeypatch.setattr(
        "lotto649.research_diagnostics.validated_registered_draw_prefix",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("synthetic registered-prefix mismatch")
        ),
    )

    with pytest.raises(RuntimeError, match="registered-prefix mismatch"):
        run_registered_v8_diagnostics(
            environment.cfg,
            code_commit="8" * 40,
            output_dir=environment.output_dir,
        )

    assert calls == []
    assert not (environment.output_dir / f"{V8_REPORT_STEM}.claim").exists()


def test_v8_git_audit_rejects_dirty_or_mismatched_head(monkeypatch, tmp_path):
    import lotto649.research_diagnostics as diagnostics

    code_commit = "8" * 40
    monkeypatch.setattr(
        diagnostics,
        "_read_v6_git_audit_state",
        lambda _root: (code_commit, "?? untracked.py"),
    )
    with pytest.raises(RuntimeError, match="completely clean"):
        diagnostics._validate_v8_git_audit(tmp_path, code_commit)

    monkeypatch.setattr(
        diagnostics,
        "_read_v6_git_audit_state",
        lambda _root: ("9" * 40, ""),
    )
    with pytest.raises(RuntimeError, match="equal the local Git HEAD"):
        diagnostics._validate_v8_git_audit(tmp_path, code_commit)


def test_v8_frame_reordering_fails_after_claim_and_publishes_no_report(
    tmp_path,
    monkeypatch,
):
    environment = _runner_environment(tmp_path)

    def reorder(model_name, frame):
        if model_name == V8_ROW_CONTROL:
            frame.iloc[[0, 1]] = frame.iloc[[1, 0]].to_numpy()

    calls = _install_runner_mocks(monkeypatch, environment, mutate=reorder)

    with pytest.raises(RuntimeError, match="target dates mismatch"):
        run_registered_v8_diagnostics(
            environment.cfg,
            code_commit="8" * 40,
            output_dir=environment.output_dir,
        )

    assert len(calls) == 2
    assert (environment.output_dir / f"{V8_REPORT_STEM}.claim").is_file()
    assert not (environment.output_dir / f"{V8_REPORT_STEM}.json").exists()
    assert not (environment.output_dir / f"{V8_REPORT_STEM}.md").exists()


@pytest.mark.parametrize(
    "case",
    [
        "model_version",
        "target_date_object",
        "actual_fractional",
        "bonus_fractional",
        "hit_string",
        "hit_boolean",
        "topk_nesting",
        "final_not_subset",
        "brier_above_one",
        "log_loss_above_bound",
        "rank_below_bound",
    ],
)
def test_v8_candidate_frame_contract_fails_before_controls_or_reports(
    case,
    tmp_path,
    monkeypatch,
):
    environment = _runner_environment(tmp_path)

    def mutate(model_name, frame):
        if model_name != V8_CANDIDATE:
            return
        if case == "model_version":
            frame["model_version"] = "v8.changed"
        elif case == "target_date_object":
            frame["target_draw_date"] = frame["target_draw_date"].astype(object)
            frame.at[0, "target_draw_date"] = date.fromisoformat(
                frame.at[0, "target_draw_date"]
            )
        elif case == "actual_fractional":
            actual = list(frame.at[0, "actual"])
            actual[0] = float(actual[0]) + 0.5
            frame.at[0, "actual"] = actual
        elif case == "bonus_fractional":
            frame["bonus"] = frame["bonus"].astype(object)
            frame.at[0, "bonus"] = float(frame.at[0, "bonus"]) + 0.5
        elif case == "hit_string":
            frame["top_6_hits"] = "1"
        elif case == "hit_boolean":
            frame["top_6_hits"] = True
        elif case == "topk_nesting":
            frame["top_6_hits"] = 3
            frame["top_12_hits"] = 2
        elif case == "final_not_subset":
            frame["final_6_hits"] = 3
            frame["top_12_hits"] = 2
        elif case == "brier_above_one":
            frame["brier_score"] = 1.0001
        elif case == "log_loss_above_bound":
            frame["log_loss"] = 100.0
        elif case == "rank_below_bound":
            frame["mean_actual_rank"] = 3.0
        else:  # pragma: no cover - the parametrization is exhaustive
            raise AssertionError(case)

    calls = _install_runner_mocks(monkeypatch, environment, mutate=mutate)

    with pytest.raises(RuntimeError):
        run_registered_v8_diagnostics(
            environment.cfg,
            code_commit="8" * 40,
            output_dir=environment.output_dir,
        )

    assert len(calls) == 1
    assert (environment.output_dir / f"{V8_REPORT_STEM}.claim").is_file()
    assert not (environment.output_dir / f"{V8_REPORT_STEM}.json").exists()
    assert not (environment.output_dir / f"{V8_REPORT_STEM}.md").exists()


def test_v8_json_serialization_rejects_nan_and_retains_claim(
    tmp_path,
    monkeypatch,
):
    environment = _runner_environment(tmp_path)
    _install_runner_mocks(monkeypatch, environment)
    import lotto649.research_diagnostics as diagnostics

    real_summary = diagnostics._v8_summary

    def inject_nan(*args, **kwargs):
        summary = real_summary(*args, **kwargs)
        if summary["model_name"] == V8_CANDIDATE and summary["draws"] == 621:
            summary["avg_brier"] = float("nan")
        return summary

    monkeypatch.setattr(diagnostics, "_v8_summary", inject_nan)

    with pytest.raises(ValueError, match="Out of range float values"):
        run_registered_v8_diagnostics(
            environment.cfg,
            code_commit="8" * 40,
            output_dir=environment.output_dir,
        )

    assert (environment.output_dir / f"{V8_REPORT_STEM}.claim").is_file()
    assert not (environment.output_dir / f"{V8_REPORT_STEM}.json").exists()
    assert not (environment.output_dir / f"{V8_REPORT_STEM}.md").exists()


def test_v8_reports_are_byte_deterministic_across_independent_repositories(
    tmp_path,
    monkeypatch,
):
    first_environment = _runner_environment(tmp_path / "first")
    _install_runner_mocks(monkeypatch, first_environment)
    first = run_registered_v8_diagnostics(
        first_environment.cfg,
        code_commit="8" * 40,
        output_dir=first_environment.output_dir,
    )
    first_json = Path(first["json_path"]).read_bytes()
    first_markdown = Path(first["markdown_path"]).read_bytes()

    second_environment = _runner_environment(tmp_path / "second")
    _install_runner_mocks(monkeypatch, second_environment)
    second = run_registered_v8_diagnostics(
        second_environment.cfg,
        code_commit="8" * 40,
        output_dir=second_environment.output_dir,
    )

    assert Path(second["json_path"]).read_bytes() == first_json
    assert Path(second["markdown_path"]).read_bytes() == first_markdown


def test_v8_report_pair_rolls_back_caught_partial_publication(tmp_path, monkeypatch):
    json_path = tmp_path / "result.json"
    markdown_path = tmp_path / "result.md"
    json_temporary_path = tmp_path / ".result.json.tmp"
    markdown_temporary_path = tmp_path / ".result.md.tmp"
    import lotto649.research_diagnostics as diagnostics

    real_link = diagnostics.os.link
    calls = 0

    def fail_second_link(source, destination):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("synthetic second-link failure")
        return real_link(source, destination)

    monkeypatch.setattr(diagnostics.os, "link", fail_second_link)

    with pytest.raises(RuntimeError, match="complete V8 report pair"):
        _publish_v8_report_pair(
            json_path=json_path,
            markdown_path=markdown_path,
            json_temporary_path=json_temporary_path,
            markdown_temporary_path=markdown_temporary_path,
            json_text='{"schema_version":4}\n',
            markdown_text="# V8\n",
        )

    assert not json_path.exists()
    assert not markdown_path.exists()
    assert not json_temporary_path.exists()
    assert not markdown_temporary_path.exists()


def test_v8_report_pair_surfaces_rollback_failure_and_retains_evidence(
    tmp_path,
    monkeypatch,
):
    json_path = tmp_path / "result.json"
    markdown_path = tmp_path / "result.md"
    json_temporary_path = tmp_path / ".result.json.tmp"
    markdown_temporary_path = tmp_path / ".result.md.tmp"
    import lotto649.research_diagnostics as diagnostics

    real_link = diagnostics.os.link
    real_unlink = Path.unlink
    link_calls = 0

    def fail_second_link(source, destination):
        nonlocal link_calls
        link_calls += 1
        if link_calls == 2:
            raise OSError("synthetic second-link failure")
        return real_link(source, destination)

    def fail_published_json_rollback(path, *args, **kwargs):
        if path == json_path:
            raise OSError("synthetic rollback failure")
        return real_unlink(path, *args, **kwargs)

    monkeypatch.setattr(diagnostics.os, "link", fail_second_link)
    monkeypatch.setattr(Path, "unlink", fail_published_json_rollback)

    with pytest.raises(RuntimeError, match="rollback failed"):
        _publish_v8_report_pair(
            json_path=json_path,
            markdown_path=markdown_path,
            json_temporary_path=json_temporary_path,
            markdown_temporary_path=markdown_temporary_path,
            json_text='{"schema_version":4}\n',
            markdown_text="# V8\n",
        )

    assert json_path.is_file()
    assert not markdown_path.exists()
    assert json_temporary_path.is_file()
    assert markdown_temporary_path.is_file()


def test_v8_cleanup_failure_rolls_back_visible_final_pair(tmp_path, monkeypatch):
    json_path = tmp_path / "result.json"
    markdown_path = tmp_path / "result.md"
    json_temporary_path = tmp_path / ".result.json.tmp"
    markdown_temporary_path = tmp_path / ".result.md.tmp"
    real_unlink = Path.unlink

    def fail_markdown_staging_cleanup(path, *args, **kwargs):
        if path == markdown_temporary_path:
            raise OSError("synthetic staging cleanup failure")
        return real_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", fail_markdown_staging_cleanup)

    with pytest.raises(RuntimeError, match="final report pair was rolled back"):
        _publish_v8_report_pair(
            json_path=json_path,
            markdown_path=markdown_path,
            json_temporary_path=json_temporary_path,
            markdown_temporary_path=markdown_temporary_path,
            json_text='{"schema_version":4}\n',
            markdown_text="# V8\n",
        )

    assert not json_path.exists()
    assert not markdown_path.exists()
    assert not json_temporary_path.exists()
    assert markdown_temporary_path.is_file()


def test_v8_cleanup_directory_fsync_failure_rolls_back_final_pair(
    tmp_path,
    monkeypatch,
):
    json_path = tmp_path / "result.json"
    markdown_path = tmp_path / "result.md"
    json_temporary_path = tmp_path / ".result.json.tmp"
    markdown_temporary_path = tmp_path / ".result.md.tmp"
    import lotto649.research_diagnostics as diagnostics

    real_fsync = diagnostics._fsync_v8_directory
    calls = 0

    def fail_cleanup_fsync(directory):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("synthetic cleanup directory fsync failure")
        return real_fsync(directory)

    monkeypatch.setattr(diagnostics, "_fsync_v8_directory", fail_cleanup_fsync)

    with pytest.raises(RuntimeError, match="final report pair was rolled back"):
        _publish_v8_report_pair(
            json_path=json_path,
            markdown_path=markdown_path,
            json_temporary_path=json_temporary_path,
            markdown_temporary_path=markdown_temporary_path,
            json_text='{"schema_version":4}\n',
            markdown_text="# V8\n",
        )

    assert calls == 3
    assert not json_path.exists()
    assert not markdown_path.exists()
    assert not json_temporary_path.exists()
    assert not markdown_temporary_path.exists()


def test_cli_exposes_research_v8_with_required_code_commit(monkeypatch, capsys):
    import sys

    import lotto649.cli as cli

    captured = {}
    cfg = {
        "_root": "/tmp/v8-cli-root",
        "data": {"processed_csv": "data/processed/draws.csv"},
    }

    def fake_run(received_cfg, *, code_commit, output_dir):
        captured.update(cfg=received_cfg, code_commit=code_commit, output_dir=output_dir)
        return {
            "json_path": "v8.json",
            "markdown_path": "v8.md",
            "claim_path": "v8.claim",
            "report": {},
        }

    monkeypatch.setattr(cli, "load_config", lambda _path: cfg)
    monkeypatch.setattr(cli, "run_registered_v8_diagnostics", fake_run, raising=False)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "lotto649",
            "--config",
            "config/research-v8-fixed-spectral-phase.yaml",
            "research-v8",
            "--code-commit",
            "8" * 40,
        ],
    )

    cli.main()

    assert captured == {
        "cfg": cfg,
        "code_commit": "8" * 40,
        "output_dir": Path("/tmp/v8-cli-root/reports"),
    }
    assert json.loads(capsys.readouterr().out) == {
        "json_path": "v8.json",
        "markdown_path": "v8.md",
        "claim_path": "v8.claim",
    }
