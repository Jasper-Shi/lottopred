from dataclasses import dataclass
from datetime import date, timedelta
from hashlib import sha256
import json
import math
from pathlib import Path

import pandas as pd
import pytest

from lotto649.config import load_config
from lotto649.domain import Draw
from lotto649.research_diagnostics import (
    conditional_role_likelihood_ratio,
    role_audit_monte_carlo,
    run_registered_v7_diagnostics,
    v7_historical_decision,
)
from lotto649.research_protocol import load_experiment_registry


ROOT = Path(__file__).resolve().parents[1]
V7_EXPERIMENT_ID = "V7_post_rng_main_bonus_role_bias"
V7_CANDIDATE = "v7_main_bonus_role_bias"
V7_CONTROL = "v7_main_bonus_role_control"
V7_VERSION = "v7.0.0"
V7_START = date(2020, 1, 1)
V7_END = date(2025, 12, 31)
V7_REPORT_STEM = "v7_main_bonus_role_bias_v7.0.0_historical"


def _role_audit_fixture() -> list[Draw]:
    return [
        Draw(date(2020, 1, 1), (1, 2, 3, 4, 5, 6), 7),
        Draw(date(2020, 1, 4), (1, 2, 3, 4, 5, 6), 8),
    ]


def test_conditional_role_likelihood_ratio_matches_worked_oracle():
    expected = 24.0 * math.log(7.0 / 6.0) + 4.0 * math.log(7.0)

    statistic = conditional_role_likelihood_ratio(_role_audit_fixture())

    assert statistic == pytest.approx(expected, abs=1e-15)


def test_role_audit_monte_carlo_replays_one_frozen_rng_stream():
    first = role_audit_monte_carlo(
        _role_audit_fixture(),
        randomizations=5,
        seed=649,
    )
    second = role_audit_monte_carlo(
        _role_audit_fixture(),
        randomizations=5,
        seed=649,
    )

    assert first == second
    assert first == {
        "statistic": pytest.approx(11.483256912075454, abs=1e-15),
        "randomizations": 5,
        "seed": 649,
        "right_tail_exceedances": 1,
        "plus_one_right_tail_p": pytest.approx(1.0 / 3.0, abs=1e-15),
    }


def _passing_summary() -> dict:
    return {
        "primary_top12_lift_vs_theory": 0.1,
        "primary_holm_adjusted_p": 0.01,
        "primary_bootstrap_95_ci": [0.01, 0.2],
        "brier_delta_vs_fair": 0.0,
        "log_loss_delta_vs_fair": 0.0,
    }


def test_v7_historical_decision_requires_every_registered_gate():
    payload = {
        "candidate": _passing_summary(),
        "stability_halves": [
            {"candidate": _passing_summary()},
            {"candidate": _passing_summary()},
        ],
        "negative_control": {"behaves_as_null": True},
        "negative_control_halves": [
            {"behaves_as_null": True},
            {"behaves_as_null": True},
        ],
        "global_role_audit": {"plus_one_right_tail_p": 0.01},
    }

    decision, warnings = v7_historical_decision(
        payload,
        proper_score_tolerance=1.0e-9,
    )

    assert warnings == []
    assert decision["all_gates_passed"] is True
    assert decision["decision"] == "eligible_for_reviewed_shadow_activation"
    assert all(decision["gates"].values())

    payload["stability_halves"][1]["candidate"][
        "primary_top12_lift_vs_theory"
    ] = 0.0
    rejected, rejected_warnings = v7_historical_decision(
        payload,
        proper_score_tolerance=1.0e-9,
    )

    assert rejected_warnings == []
    assert rejected["all_gates_passed"] is False
    assert rejected["decision"] == "reject"
    assert rejected["gates"]["positive_primary_lift_in_both_fixed_halves"] is False


def test_v7_historical_decision_turns_control_anomaly_into_audit_warning():
    payload = {
        "candidate": _passing_summary(),
        "stability_halves": [
            {"candidate": _passing_summary()},
            {"candidate": _passing_summary()},
        ],
        "negative_control": {"behaves_as_null": True},
        "negative_control_halves": [
            {"behaves_as_null": True},
            {"behaves_as_null": False},
        ],
        "global_role_audit": {"plus_one_right_tail_p": 0.01},
    }

    decision, warnings = v7_historical_decision(
        payload,
        proper_score_tolerance=1.0e-9,
    )

    assert warnings == ["negative_control_non_null:2"]
    assert decision["decision"] == "reject"
    assert decision["gates"]["negative_control_null_aggregate_and_halves"] is False
    assert decision["gates"]["audit_clear"] is False


V7_HISTORICAL_GATE_KEYS = {
    "positive_aggregate_primary_lift",
    "aggregate_holm_adjusted_p_at_most_0_05",
    "aggregate_bootstrap_lower_above_zero",
    "positive_primary_lift_in_both_fixed_halves",
    "proper_scores_within_fair_tolerance_aggregate_and_halves",
    "global_role_audit_p_at_most_0_05",
    "negative_control_null_aggregate_and_halves",
    "audit_clear",
}


def _passing_decision_payload() -> dict:
    return {
        "candidate": _passing_summary(),
        "stability_halves": [
            {"candidate": _passing_summary()},
            {"candidate": _passing_summary()},
        ],
        "negative_control": {"behaves_as_null": True},
        "negative_control_halves": [
            {"behaves_as_null": True},
            {"behaves_as_null": True},
        ],
        "global_role_audit": {"plus_one_right_tail_p": 0.01},
        "audit_warnings": [],
    }


def _set_nested(payload: dict, path: tuple, value) -> None:
    destination = payload
    for key in path[:-1]:
        destination = destination[key]
    destination[path[-1]] = value


@pytest.mark.parametrize(
    ("path", "value", "failed_gates"),
    [
        (
            ("candidate", "primary_top12_lift_vs_theory"),
            0.0,
            {"positive_aggregate_primary_lift"},
        ),
        (
            ("candidate", "primary_holm_adjusted_p"),
            0.0500001,
            {"aggregate_holm_adjusted_p_at_most_0_05"},
        ),
        (
            ("candidate", "primary_bootstrap_95_ci"),
            [0.0, 0.2],
            {"aggregate_bootstrap_lower_above_zero"},
        ),
        (
            ("stability_halves", 0, "candidate", "primary_top12_lift_vs_theory"),
            0.0,
            {"positive_primary_lift_in_both_fixed_halves"},
        ),
        (
            ("stability_halves", 1, "candidate", "primary_top12_lift_vs_theory"),
            0.0,
            {"positive_primary_lift_in_both_fixed_halves"},
        ),
        *[
            (
                score_path,
                1.1e-9,
                {"proper_scores_within_fair_tolerance_aggregate_and_halves"},
            )
            for score_path in (
                ("candidate", "brier_delta_vs_fair"),
                ("candidate", "log_loss_delta_vs_fair"),
                ("stability_halves", 0, "candidate", "brier_delta_vs_fair"),
                ("stability_halves", 0, "candidate", "log_loss_delta_vs_fair"),
                ("stability_halves", 1, "candidate", "brier_delta_vs_fair"),
                ("stability_halves", 1, "candidate", "log_loss_delta_vs_fair"),
            )
        ],
        (
            ("global_role_audit", "plus_one_right_tail_p"),
            0.0500001,
            {"global_role_audit_p_at_most_0_05"},
        ),
        *[
            (
                control_path,
                False,
                {"negative_control_null_aggregate_and_halves", "audit_clear"},
            )
            for control_path in (
                ("negative_control", "behaves_as_null"),
                ("negative_control_halves", 0, "behaves_as_null"),
                ("negative_control_halves", 1, "behaves_as_null"),
            )
        ],
        (
            ("audit_warnings",),
            ["pre_existing_audit_warning"],
            {"audit_clear"},
        ),
    ],
)
def test_v7_historical_decision_has_no_unregistered_rescue_gate(
    path,
    value,
    failed_gates,
):
    payload = _passing_decision_payload()
    _set_nested(payload, path, value)

    decision, _warnings = v7_historical_decision(
        payload,
        proper_score_tolerance=1.0e-9,
    )

    assert set(decision["gates"]) == V7_HISTORICAL_GATE_KEYS
    assert {
        gate for gate, passed in decision["gates"].items() if not passed
    } == failed_gates
    assert decision["decision"] == "reject"
    assert decision["all_gates_passed"] is False


def _numbers(index: int) -> tuple[int, ...]:
    return tuple(
        sorted((((index * 7) + offset * 8) % 49) + 1 for offset in range(6))
    )


def _draw(draw_date: date, index: int) -> Draw:
    numbers = _numbers(index)
    bonus = next(number for number in range(1, 50) if number not in numbers)
    return Draw(draw_date, numbers, bonus)


def _synthetic_registered_draws() -> list[Draw]:
    pre_rng = [
        _draw(date(2016, 1, 1) + timedelta(days=3 * index), index)
        for index in range(300)
    ]
    burn_in = [
        _draw(date(2019, 5, 15) + timedelta(days=3 * index), 300 + index)
        for index in range(65)
    ]
    fallback_targets = [
        _draw(date(2020, 1, 1) + timedelta(days=3 * index), 365 + index)
        for index in range(39)
    ]
    first_active = [_draw(date(2020, 5, 20), 404)]
    remaining_first_half = [
        _draw(date(2020, 5, 23) + timedelta(days=3 * index), 405 + index)
        for index in range(267)
    ]
    second_half = [
        _draw(date(2023, 1, 1) + timedelta(days=3 * index), 672 + index)
        for index in range(313)
    ]
    second_half.append(_draw(date(2025, 12, 31), 985))
    registered_boundary = [_draw(date(2026, 8, 12), 986)]
    draws = [
        *pre_rng,
        *burn_in,
        *fallback_targets,
        *first_active,
        *remaining_first_half,
        *second_half,
        *registered_boundary,
    ]
    assert len([draw for draw in draws if V7_START <= draw.draw_date <= V7_END]) == 621
    return draws


def _expected_targets(draws: list[Draw]) -> list[Draw]:
    return [draw for draw in draws if V7_START <= draw.draw_date <= V7_END]


def _diagnostic_frame(
    draws: list[Draw],
    *,
    model_name: str,
    top12_hits: int,
) -> pd.DataFrame:
    from lotto649.research_diagnostics import fair_constant_scores

    targets = _expected_targets(draws)
    fair_brier, fair_log_loss = fair_constant_scores()
    return pd.DataFrame(
        {
            "target_draw_date": [draw.draw_date.isoformat() for draw in targets],
            "model_name": [model_name] * len(targets),
            "model_version": [V7_VERSION] * len(targets),
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


def _fractionalize_first_actual(frame: pd.DataFrame) -> None:
    actual = list(frame.at[0, "actual"])
    actual[0] = float(actual[0]) + 0.5
    frame.at[0, "actual"] = actual


def _fractionalize_first_bonus(frame: pd.DataFrame) -> None:
    frame["bonus"] = frame["bonus"].astype(object)
    frame.at[0, "bonus"] = float(frame.at[0, "bonus"]) + 0.5


@dataclass(frozen=True)
class _BoundaryEvidence:
    registration_prefix_preserved: bool = True
    draws_fingerprint: str = "b" * 64


@dataclass
class _Environment:
    root: Path
    cfg: dict
    draws: list[Draw]
    registry: object
    reference_path: Path
    output_dir: Path


def _environment(tmp_path: Path) -> _Environment:
    root = tmp_path / "repo"
    config_path = root / "config" / "research-v7-main-bonus-role-bias.yaml"
    config_path.parent.mkdir(parents=True)
    config_bytes = (ROOT / "config" / "research-v7-main-bonus-role-bias.yaml").read_bytes()
    config_path.write_bytes(config_bytes)
    cfg = load_config(config_path)
    cfg["_root"] = root

    reference_path = root / "reports" / "v6_entropy_regime_v6.0.0_historical.json"
    reference_path.parent.mkdir(parents=True)
    reference_path.write_bytes(
        (ROOT / "reports" / "v6_entropy_regime_v6.0.0_historical.json").read_bytes()
    )
    registry = load_experiment_registry(
        ROOT / "docs" / "experiments" / "registry.yaml"
    )
    draws = _synthetic_registered_draws()
    return _Environment(
        root=root,
        cfg=cfg,
        draws=draws,
        registry=registry,
        reference_path=reference_path,
        output_dir=root / "reports",
    )


def _install_valid_runner(
    monkeypatch,
    environment: _Environment,
    *,
    mutate_frame=None,
) -> list[tuple[str, date, date, tuple[Draw, ...]]]:
    calls: list[tuple[str, date, date, tuple[Draw, ...]]] = []
    config_path = Path(environment.cfg["_config_path"])

    monkeypatch.setattr(
        "lotto649.research_diagnostics._read_v6_git_audit_state",
        lambda _root: ("7" * 40, ""),
    )

    def committed_bytes(_root, _commit, relative_path):
        relative = Path(relative_path).as_posix()
        if relative == "config/research-v7-main-bonus-role-bias.yaml":
            return config_path.read_bytes()
        if relative == "reports/v6_entropy_regime_v6.0.0_historical.json":
            return environment.reference_path.read_bytes()
        pytest.fail(f"unexpected committed-file request: {relative}")

    monkeypatch.setattr(
        "lotto649.research_diagnostics._read_v6_committed_file_bytes",
        committed_bytes,
    )
    monkeypatch.setattr(
        "lotto649.research_diagnostics.load_experiment_registry",
        lambda _path: environment.registry,
    )
    monkeypatch.setattr(
        "lotto649.research_diagnostics._validate_v7_outcome_boundaries",
        lambda _root, _registration: _BoundaryEvidence(),
    )
    monkeypatch.setattr(
        "lotto649.research_diagnostics.load_draws",
        lambda _path: environment.draws,
    )

    def registered_prefix(_path, _draws, **kwargs):
        registration = environment.registry.get(V7_EXPERIMENT_ID)
        assert kwargs == {
            "expected_sha256": registration.dataset_sha256,
            "draw_count": registration.dataset_draw_count,
            "history_through": registration.registration_history_through,
        }
        return tuple(environment.draws)

    monkeypatch.setattr(
        "lotto649.research_diagnostics.validated_registered_draw_prefix",
        registered_prefix,
    )
    monkeypatch.setattr(
        "lotto649.research_diagnostics.role_audit_monte_carlo",
        lambda draws, *, randomizations, seed: {
            "statistic": 12.5,
            "randomizations": randomizations,
            "seed": seed,
            "right_tail_exceedances": 99,
            "plus_one_right_tail_p": 100 / 10_001,
        },
    )

    def fake_backtest(received_draws, cfg, start, end):
        model_name = cfg["backtest"]["models"][0]
        claim = (
            environment.output_dir
            / "v7_main_bonus_role_bias_v7.0.0_historical.claim"
        )
        assert claim.is_file(), "the one-shot claim must exist before scoring"
        calls.append((model_name, start, end, tuple(received_draws)))
        assert start == V7_START
        assert end == V7_END
        assert tuple(received_draws) == tuple(environment.draws)
        if model_name == V7_CANDIDATE:
            frame = _diagnostic_frame(
                environment.draws,
                model_name=model_name,
                top12_hits=2,
            )
        elif model_name == V7_CONTROL:
            frame = _diagnostic_frame(
                environment.draws,
                model_name=model_name,
                top12_hits=1,
            )
        else:
            pytest.fail(f"unexpected diagnostic model: {model_name}")
        if mutate_frame is not None:
            mutate_frame(model_name, frame)
        return frame

    monkeypatch.setattr(
        "lotto649.research_diagnostics.run_backtest",
        fake_backtest,
    )
    return calls


def _assert_no_v7_reports(environment: _Environment) -> None:
    assert not (environment.output_dir / f"{V7_REPORT_STEM}.json").exists()
    assert not (environment.output_dir / f"{V7_REPORT_STEM}.md").exists()


def _v7_claim_path(environment: _Environment) -> Path:
    return environment.output_dir / f"{V7_REPORT_STEM}.claim"


def _assert_no_v7_transient_artifacts(environment: _Environment) -> None:
    assert not (environment.output_dir / f".{V7_REPORT_STEM}.json.tmp").exists()
    assert not (environment.output_dir / f".{V7_REPORT_STEM}.md.tmp").exists()


def test_v7_runner_scores_only_registered_lane_with_identical_candidate_control_targets(
    tmp_path,
    monkeypatch,
):
    environment = _environment(tmp_path)
    calls = _install_valid_runner(monkeypatch, environment)

    result = run_registered_v7_diagnostics(
        environment.cfg,
        code_commit="7" * 40,
        output_dir=environment.output_dir,
    )

    assert [(name, start, end) for name, start, end, _draws in calls] == [
        (V7_CANDIDATE, V7_START, V7_END),
        (V7_CONTROL, V7_START, V7_END),
    ]
    assert calls[0][3] == calls[1][3] == tuple(environment.draws)
    report = result["report"]
    assert report["schema_version"] == 3
    assert report["experiment_id"] == V7_EXPERIMENT_ID
    assert report["historical_lane"] == {
        "name": "consumed_diagnostic",
        "dates": {"start": "2020-01-01", "end": "2025-12-31"},
        "target_count": 621,
        "development_status": "not_applicable",
        "legacy_validation_status": "not_applicable",
    }
    assert report["activation"] == {
        "eligible_targets": 621,
        "fair_fallback_targets": 39,
        "active_targets": 582,
        "first_active_target": "2020-05-20",
    }
    assert [half["target_count"] for half in report["stability_halves"]] == [
        307,
        314,
    ]
    assert report["candidate"]["draws"] == 621
    assert report["negative_control"]["draws"] == 621
    assert report["negative_control"]["model_name"] == V7_CONTROL
    assert report["global_role_audit"]["randomizations"] == 10_000
    assert report["reference_provenance"]["experiment_id"] == (
        "V6_fixed_boundary_js_regime"
    )
    assert len(report["comparisons"]) == 10
    assert report["comparisons"][-1] == report["candidate"]
    assert report["prospective_cohort"]["status"] == "not_activated"
    assert report["historical_decision"]["decision"] == (
        "eligible_for_reviewed_shadow_activation"
    )
    assert Path(result["json_path"]).is_file()
    assert Path(result["markdown_path"]).is_file()
    assert Path(result["claim_path"]) == _v7_claim_path(environment)
    assert _v7_claim_path(environment).is_file()
    assert report["one_shot_claim"] == {
        "path": f"reports/{V7_REPORT_STEM}.claim",
        "sha256": sha256(_v7_claim_path(environment).read_bytes()).hexdigest(),
        "created_before_first_score": True,
        "retention": "permanent_on_success_or_failure",
    }
    _assert_no_v7_transient_artifacts(environment)


@pytest.mark.parametrize(
    ("tamper", "message"),
    [
        (
            lambda environment, monkeypatch: monkeypatch.setattr(
                "lotto649.research_diagnostics._read_v6_git_audit_state",
                lambda _root: ("7" * 40, "?? untracked.txt"),
            ),
            "worktree must be completely clean",
        ),
        (
            lambda environment, _monkeypatch: environment.cfg["research"].__setitem__(
                "historical_target_count", 620
            ),
            "loaded V7 config differs from the committed Git blob",
        ),
        (
            lambda environment, _monkeypatch: environment.reference_path.write_bytes(
                environment.reference_path.read_bytes() + b"\n"
            ),
            "reference report fingerprint mismatch",
        ),
        (
            lambda environment, _monkeypatch: environment.draws.__setitem__(
                300,
                Draw(
                    environment.draws[300].draw_date,
                    environment.draws[300].numbers,
                    None,
                ),
            ),
            "global role-audit interval is incomplete",
        ),
    ],
    ids=["dirty-git", "loaded-config", "reference-hash", "missing-role"],
)
def test_v7_preflight_failure_occurs_before_first_score(
    tmp_path,
    monkeypatch,
    tamper,
    message,
):
    environment = _environment(tmp_path)
    calls = _install_valid_runner(monkeypatch, environment)
    tamper(environment, monkeypatch)

    with pytest.raises(RuntimeError, match=message):
        run_registered_v7_diagnostics(
            environment.cfg,
            code_commit="7" * 40,
            output_dir=environment.output_dir,
        )

    assert calls == []
    _assert_no_v7_reports(environment)


def test_v7_frame_target_tampering_fails_closed_without_reports(
    tmp_path,
    monkeypatch,
):
    environment = _environment(tmp_path)

    def mutate(model_name, frame):
        if model_name == V7_CONTROL:
            frame.at[0, "actual"] = [44, 45, 46, 47, 48, 49]

    calls = _install_valid_runner(
        monkeypatch,
        environment,
        mutate_frame=mutate,
    )

    with pytest.raises(RuntimeError, match="target outcome mismatch"):
        run_registered_v7_diagnostics(
            environment.cfg,
            code_commit="7" * 40,
            output_dir=environment.output_dir,
        )

    assert len(calls) == 2
    _assert_no_v7_reports(environment)
    assert _v7_claim_path(environment).is_file()


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda frame: frame.__setitem__("model_version", "v7.changed"),
            "model version mismatch",
        ),
        (
            lambda frame: frame.__setitem__("top_6_hits", 1.5),
            "hit counts must be finite integers",
        ),
        (
            lambda frame: frame.__setitem__("log_loss", float("inf")),
            "score columns must be finite and bounded",
        ),
        (
            lambda frame: frame.__setitem__("mean_actual_rank", 50.0),
            "score columns must be finite and bounded",
        ),
        (
            _fractionalize_first_actual,
            "target outcome must use exact integers",
        ),
        (
            _fractionalize_first_bonus,
            "target outcome must use exact integers",
        ),
        (
            lambda frame: frame.__setitem__("brier_score", 1.1),
            "score columns must be finite and bounded",
        ),
        (
            lambda frame: frame.__setitem__("mean_actual_rank", 3.0),
            "score columns must be finite and bounded",
        ),
        (
            lambda frame: frame.__setitem__("log_loss", 100.0),
            "score columns must be finite and bounded",
        ),
        (
            lambda frame: frame.__setitem__("final_6_hits", 3),
            "final hits must remain a subset of Top-12",
        ),
        (
            lambda frame: frame.__setitem__("top_6_hits", "1"),
            "hit counts must be finite integers",
        ),
        (
            lambda frame: frame.__setitem__("top_6_hits", True),
            "hit counts must be finite integers",
        ),
        (
            lambda frame: frame.__setitem__("brier_score", "0.1"),
            "score columns must be finite and bounded",
        ),
        (
            lambda frame: frame.__setitem__("log_loss", False),
            "score columns must be finite and bounded",
        ),
        (
            lambda frame: frame.__setitem__("mean_actual_rank", "25.0"),
            "score columns must be finite and bounded",
        ),
    ],
    ids=[
        "version",
        "fractional-hit",
        "infinite-score",
        "rank-upper-bound",
        "fractional-actual",
        "fractional-bonus",
        "brier-upper-bound",
        "rank-lower-bound",
        "log-loss-upper-bound",
        "final-top12-subset",
        "string-hit",
        "boolean-hit",
        "string-score",
        "boolean-score",
        "string-rank",
    ],
)
def test_v7_candidate_frame_contract_fails_before_control_or_report(
    tmp_path,
    monkeypatch,
    mutate,
    message,
):
    environment = _environment(tmp_path)

    def mutate_candidate(model_name, frame):
        if model_name == V7_CANDIDATE:
            mutate(frame)

    calls = _install_valid_runner(
        monkeypatch,
        environment,
        mutate_frame=mutate_candidate,
    )

    with pytest.raises(RuntimeError, match=message):
        run_registered_v7_diagnostics(
            environment.cfg,
            code_commit="7" * 40,
            output_dir=environment.output_dir,
        )

    assert len(calls) == 1
    _assert_no_v7_reports(environment)
    assert _v7_claim_path(environment).is_file()


def test_v7_runner_refuses_existing_output_before_first_score(
    tmp_path,
    monkeypatch,
):
    environment = _environment(tmp_path)
    calls = _install_valid_runner(monkeypatch, environment)
    environment.output_dir.mkdir(parents=True, exist_ok=True)
    existing = environment.output_dir / "v7_main_bonus_role_bias_v7.0.0_historical.json"
    existing.write_text("immutable\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="refusing to overwrite"):
        run_registered_v7_diagnostics(
            environment.cfg,
            code_commit="7" * 40,
            output_dir=environment.output_dir,
        )

    assert calls == []
    assert existing.read_text(encoding="utf-8") == "immutable\n"


def test_v7_runner_refuses_a_preexisting_one_shot_claim_before_first_score(
    tmp_path,
    monkeypatch,
):
    environment = _environment(tmp_path)
    calls = _install_valid_runner(monkeypatch, environment)
    claim = _v7_claim_path(environment)
    claim.write_text("prior attempt\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="claim already exists"):
        run_registered_v7_diagnostics(
            environment.cfg,
            code_commit="7" * 40,
            output_dir=environment.output_dir,
        )

    assert calls == []
    assert claim.read_text(encoding="utf-8") == "prior attempt\n"
    _assert_no_v7_reports(environment)


def test_successful_v7_claim_is_permanent_and_blocks_a_delayed_duplicate(
    tmp_path,
    monkeypatch,
):
    environment = _environment(tmp_path)
    calls = _install_valid_runner(monkeypatch, environment)

    first = run_registered_v7_diagnostics(
        environment.cfg,
        code_commit="7" * 40,
        output_dir=environment.output_dir,
    )

    claim = _v7_claim_path(environment)
    assert Path(first["claim_path"]) == claim
    assert claim.is_file()
    with pytest.raises(RuntimeError, match="claim already exists"):
        run_registered_v7_diagnostics(
            environment.cfg,
            code_commit="7" * 40,
            output_dir=environment.output_dir,
        )
    assert len(calls) == 2


def test_v7_report_publish_failure_retains_claim_and_no_partial_final_pair(
    tmp_path,
    monkeypatch,
):
    import os

    import lotto649.research_diagnostics as diagnostics

    environment = _environment(tmp_path)
    _install_valid_runner(monkeypatch, environment)
    original_link = os.link
    link_calls = 0

    def fail_second_link(source, destination):
        nonlocal link_calls
        link_calls += 1
        if link_calls == 2:
            raise OSError("synthetic second-publication failure")
        return original_link(source, destination)

    monkeypatch.setattr(diagnostics.os, "link", fail_second_link)

    with pytest.raises(RuntimeError, match="complete V7 report pair"):
        run_registered_v7_diagnostics(
            environment.cfg,
            code_commit="7" * 40,
            output_dir=environment.output_dir,
        )

    assert link_calls == 2
    assert _v7_claim_path(environment).is_file()
    _assert_no_v7_reports(environment)
    assert (environment.output_dir / f".{V7_REPORT_STEM}.json.tmp").is_file()
    assert (environment.output_dir / f".{V7_REPORT_STEM}.md.tmp").is_file()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("statistic", float("inf")),
        ("statistic", -0.1),
        ("randomizations", 9_999),
        ("seed", 650),
        ("right_tail_exceedances", -1),
        ("right_tail_exceedances", 10_001),
        ("plus_one_right_tail_p", 0.5),
    ],
)
def test_v7_role_audit_result_must_be_internally_consistent(
    tmp_path,
    monkeypatch,
    field,
    value,
):
    import lotto649.research_diagnostics as diagnostics

    environment = _environment(tmp_path)
    calls = _install_valid_runner(monkeypatch, environment)
    invalid = {
        "statistic": 12.5,
        "randomizations": 10_000,
        "seed": 649,
        "right_tail_exceedances": 99,
        "plus_one_right_tail_p": 100 / 10_001,
    }
    invalid[field] = value
    monkeypatch.setattr(
        diagnostics,
        "role_audit_monte_carlo",
        lambda _draws, *, randomizations, seed: invalid,
    )

    with pytest.raises(RuntimeError, match="role-audit result is inconsistent"):
        run_registered_v7_diagnostics(
            environment.cfg,
            code_commit="7" * 40,
            output_dir=environment.output_dir,
        )

    assert len(calls) == 2
    assert _v7_claim_path(environment).is_file()
    _assert_no_v7_reports(environment)


def test_v7_runner_refuses_noncanonical_output_before_first_score(
    tmp_path,
    monkeypatch,
):
    environment = _environment(tmp_path)
    calls = _install_valid_runner(monkeypatch, environment)

    with pytest.raises(RuntimeError, match="canonical repository reports directory"):
        run_registered_v7_diagnostics(
            environment.cfg,
            code_commit="7" * 40,
            output_dir=environment.root / "alternate-reports",
        )

    assert calls == []
    assert not (environment.root / "alternate-reports").exists()


def test_v7_runner_explicitly_binds_registered_bootstrap_protocol(
    tmp_path,
    monkeypatch,
):
    import lotto649.research_diagnostics as diagnostics

    environment = _environment(tmp_path)
    _install_valid_runner(monkeypatch, environment)
    original_bootstrap = diagnostics.bootstrap_mean_lift_interval
    original_quantile = diagnostics.np.quantile
    bootstrap_calls: list[tuple[int, int]] = []
    quantile_methods: list[str] = []

    def traced_bootstrap(
        hits,
        expectation,
        *,
        resamples,
        seed,
        chunk_size=256,
    ):
        bootstrap_calls.append((resamples, seed))
        return original_bootstrap(
            hits,
            expectation,
            resamples=resamples,
            seed=seed,
            chunk_size=chunk_size,
        )

    def traced_quantile(values, quantiles, *, method):
        quantile_methods.append(method)
        return original_quantile(values, quantiles, method=method)

    monkeypatch.setattr(diagnostics, "bootstrap_mean_lift_interval", traced_bootstrap)
    monkeypatch.setattr(diagnostics.np, "quantile", traced_quantile)

    run_registered_v7_diagnostics(
        environment.cfg,
        code_commit="7" * 40,
        output_dir=environment.output_dir,
    )

    assert bootstrap_calls == [(10_000, 649)] * 6
    assert quantile_methods == ["linear"] * 6


def test_v7_report_serialization_is_deterministic(tmp_path, monkeypatch):
    first_environment = _environment(tmp_path / "first")
    _install_valid_runner(monkeypatch, first_environment)

    first = run_registered_v7_diagnostics(
        first_environment.cfg,
        code_commit="7" * 40,
        output_dir=first_environment.output_dir,
    )
    second_environment = _environment(tmp_path / "second")
    _install_valid_runner(monkeypatch, second_environment)
    second = run_registered_v7_diagnostics(
        second_environment.cfg,
        code_commit="7" * 40,
        output_dir=second_environment.output_dir,
    )

    assert Path(first["json_path"]).read_bytes() == Path(second["json_path"]).read_bytes()
    assert Path(first["markdown_path"]).read_bytes() == Path(
        second["markdown_path"]
    ).read_bytes()


def test_cli_exposes_research_v7_with_required_code_commit(monkeypatch, capsys):
    import sys

    import lotto649.cli as cli

    captured = {}
    cfg = {
        "_root": "/tmp/v7-cli-root",
        "data": {"processed_csv": "data/processed/draws.csv"},
    }

    def fake_run(received_cfg, *, code_commit, output_dir):
        captured.update(
            cfg=received_cfg,
            code_commit=code_commit,
            output_dir=output_dir,
        )
        return {
            "json_path": "v7.json",
            "markdown_path": "v7.md",
            "claim_path": "v7.claim",
            "report": {},
        }

    monkeypatch.setattr(cli, "load_config", lambda _path: cfg)
    monkeypatch.setattr(cli, "run_registered_v7_diagnostics", fake_run)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "lotto649",
            "--config",
            "config/research-v7-main-bonus-role-bias.yaml",
            "research-v7",
            "--code-commit",
            "7" * 40,
        ],
    )

    cli.main()

    assert captured == {
        "cfg": cfg,
        "code_commit": "7" * 40,
        "output_dir": Path("/tmp/v7-cli-root/reports"),
    }
    assert json.loads(capsys.readouterr().out) == {
        "json_path": "v7.json",
        "markdown_path": "v7.md",
        "claim_path": "v7.claim",
    }
