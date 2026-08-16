from copy import deepcopy
from datetime import date, timedelta
from hashlib import sha256
import json
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest
import yaml

from lotto649.domain import Draw
from lotto649.research_diagnostics import (
    HISTORICAL_LANES,
    run_registered_v6_diagnostics,
)
from lotto649.research_protocol import walk_forward_folds


V6_EXPERIMENT_ID = "V6_fixed_boundary_js_regime"
V6_MODEL = "v6_entropy_regime"
V6_VERSION = "v6.0.0"
REFERENCE_MODELS = (
    ("random", "v1.0.0"),
    ("long_frequency", "v1.0.0"),
    ("recent_frequency", "v1.0.0"),
    ("ema_gap", "v1.0.0"),
    ("logistic", "v1.0.0"),
    ("ensemble", "v1.0.0"),
    ("v3_boosting", "v1.0.0"),
    ("v5_pair_affinity", "v5.0.0"),
)


def _draw(draw_date: date, offset: int) -> Draw:
    numbers = tuple(sorted(((offset * 7 + step * 8) % 49) + 1 for step in range(6)))
    bonus = next(number for number in range(1, 50) if number not in numbers)
    return Draw(draw_date, numbers, bonus)


def _summary(model_name: str, model_version: str, draws: int) -> dict:
    return {
        "model_name": model_name,
        "model_version": model_version,
        "draws": draws,
        "avg_top6_hits": 0.75,
        "avg_top12_hits": 1.5,
        "avg_top18_hits": 2.25,
        "avg_brier": 0.1075,
        "avg_log_loss": 0.372,
        "avg_actual_rank": 25.0,
    }


def _eligible_dates(draws: list[Draw], lane, minimum_history: int = 300) -> list[str]:
    return [
        fold.target.draw_date.isoformat()
        for fold in walk_forward_folds(
            draws, lane.start, lane.end, minimum_history
        )
    ]


def _write_csv(path: Path, draws: list[Draw]) -> str:
    header = "draw_date,n1,n2,n3,n4,n5,n6,bonus\n"
    rows = [
        f"{draw.draw_date.isoformat()},{','.join(map(str, draw.numbers))},{draw.bonus}\n"
        for draw in draws
    ]
    payload = (header + "".join(rows)).encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return sha256(payload).hexdigest()


def _reference_payload(draws: list[Draw], dataset_sha256: str) -> dict:
    lanes = []
    for lane in HISTORICAL_LANES:
        eligible_dates = _eligible_dates(draws, lane)
        total_targets = sum(
            lane.start <= draw.draw_date <= lane.end for draw in draws
        )
        comparisons = [
            _summary(model_name, model_version, len(eligible_dates))
            for model_name, model_version in REFERENCE_MODELS
        ]
        lanes.append(
            {
                "lane": lane.name,
                "dates": {
                    "start": lane.start.isoformat(),
                    "end": lane.end.isoformat(),
                },
                "total_targets": total_targets,
                "eligible_targets": len(eligible_dates),
                "excluded_before_minimum_history": (
                    total_targets - len(eligible_dates)
                ),
                "candidate": deepcopy(comparisons[-1]),
                "negative_control": {},
                "comparisons": comparisons,
            }
        )
    return {
        "schema_version": 1,
        "experiment_id": "V5_pair_affinity",
        "model_name": "v5_pair_affinity",
        "model_version": "v5.0.0",
        "code_commit": "5" * 40,
        "registered_parameters": {"minimum_history_draws": 300},
        "configuration": {
            "effective": {"backtest": {"min_history_draws": 300}}
        },
        "comparison_models": [name for name, _version in REFERENCE_MODELS],
        "dataset": {
            "path": "data/processed/draws.csv",
            "source_commit": "3" * 40,
            "sha256": dataset_sha256,
            "draw_count": len(draws),
            "history_through": draws[-1].draw_date.isoformat(),
        },
        "lanes": lanes,
    }


def _environment(tmp_path: Path):
    draws = [
        *(
            _draw(date(1979, 7, 1) + timedelta(days=index * 3), index)
            for index in range(300)
        ),
        _draw(date(1981, 12, 29), 0),
        _draw(date(1982, 1, 2), 1),
        _draw(date(2014, 12, 31), 2),
        _draw(date(2015, 1, 3), 3),
        _draw(date(2019, 12, 31), 4),
        _draw(date(2020, 1, 4), 5),
        _draw(date(2025, 12, 31), 6),
        _draw(date(2026, 8, 12), 7),
    ]
    dataset_path = tmp_path / "data" / "processed" / "draws.csv"
    dataset_sha256 = _write_csv(dataset_path, draws)
    reference = _reference_payload(draws, dataset_sha256)
    reference_path = tmp_path / "reports" / "v5-reference.json"
    reference_path.parent.mkdir(parents=True, exist_ok=True)
    reference_path.write_text(
        json.dumps(reference, indent=2, sort_keys=True), encoding="utf-8"
    )

    v5_registration = SimpleNamespace(
        experiment_id="V5_pair_affinity",
        model_name="v5_pair_affinity",
        model_version="v5.0.0",
        dataset_path="data/processed/draws.csv",
        dataset_source_commit="3" * 40,
        dataset_sha256=dataset_sha256,
        dataset_draw_count=len(draws),
        registration_history_through=draws[-1].draw_date,
        multiplicity_family="v5_pair_cooccurrence",
        parameters={"minimum_history_draws": 300},
        result=SimpleNamespace(
            implementation_commit="5" * 40,
            report_json="reports/v5-reference.json",
        ),
    )
    prospective = SimpleNamespace(
        status="not_activated",
        role="shadow",
        minimum_eligible_draws=208,
        commit_deadline="before_target_local_date",
        freeze_commit=None,
        activation_commit=None,
        outcomes_known_at_activation=None,
        cohort_start=None,
    )
    parameters = {
        "minimum_history_draws": 300,
        "historical_primary_gate_lane": "consumed_diagnostic",
        "proper_score_max_delta_vs_fair": 1.0e-9,
        "reference_report": "reports/v5-reference.json",
        "reference_report_sha256": sha256(reference_path.read_bytes()).hexdigest(),
    }
    v6_registration = SimpleNamespace(
        experiment_id=V6_EXPERIMENT_ID,
        model_name=V6_MODEL,
        model_version=V6_VERSION,
        status="registered",
        dataset_path="data/processed/draws.csv",
        dataset_source_commit="3" * 40,
        dataset_sha256=dataset_sha256,
        dataset_draw_count=len(draws),
        registration_history_through=draws[-1].draw_date,
        outcomes_known_source_commit="9" * 40,
        outcomes_known_sha256="a" * 64,
        outcomes_known_draw_count=len(draws) + 1,
        outcomes_known_through=date(2026, 8, 15),
        multiplicity_family="entropy_regime",
        seed=649,
        parameters=parameters,
        negative_controls=(
            SimpleNamespace(kind="whole_draw_date_permutation", seed=649),
        ),
        prospective=prospective,
    )
    registrations = {
        v5_registration.experiment_id: v5_registration,
        v6_registration.experiment_id: v6_registration,
    }
    registry = SimpleNamespace(
        experiments=(v5_registration, v6_registration),
        get=lambda experiment_id: registrations[experiment_id],
    )
    cfg = {
        "_root": str(tmp_path),
        "project": {
            "model_version": V6_VERSION,
            "seed": 649,
            "timezone": "America/Toronto",
        },
        "data": {"processed_csv": str(dataset_path)},
        "backtest": {
            "min_history_draws": 300,
            "top_k": [6, 12, 18],
            "models": [V6_MODEL],
            "model_versions": {V6_MODEL: V6_VERSION},
        },
        "features": {},
        "prediction": {"candidate_pool_size": 12, "final_size": 6},
        "live": {"enabled": False, "models": [], "shadow_models": []},
        "notifications": {"enabled": False},
    }
    config_path = tmp_path / "config" / "research-v6-entropy-regime.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        yaml.safe_dump(
            {key: value for key, value in cfg.items() if not key.startswith("_")},
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    cfg["_config_path"] = config_path
    return SimpleNamespace(
        draws=draws,
        dataset_path=dataset_path,
        reference=reference,
        reference_path=reference_path,
        v5_registration=v5_registration,
        v6_registration=v6_registration,
        registry=registry,
        cfg=cfg,
    )


def _frame(draws: list[Draw], lane, *, top12_hits: int) -> pd.DataFrame:
    dates = _eligible_dates(draws, lane)
    return pd.DataFrame(
        {
            "target_draw_date": dates,
            "model_name": [V6_MODEL] * len(dates),
            "model_version": [V6_VERSION] * len(dates),
            "top_6_hits": [1] * len(dates),
            "top_12_hits": [top12_hits] * len(dates),
            "top_18_hits": [2] * len(dates),
            "brier_score": [0.108] * len(dates),
            "log_loss": [0.377] * len(dates),
            "mean_actual_rank": [24.0] * len(dates),
        }
    )


def _install_valid_run(monkeypatch, environment):
    calls = []
    analyses = []
    control_draws = [
        Draw(target.draw_date, source.numbers, source.bonus)
        for target, source in zip(environment.draws, reversed(environment.draws))
    ]

    monkeypatch.setattr(
        "lotto649.research_diagnostics.load_experiment_registry",
        lambda _path: environment.registry,
    )
    monkeypatch.setattr(
        "lotto649.research_diagnostics._read_v6_git_audit_state",
        lambda _root: ("6" * 40, ""),
    )
    monkeypatch.setattr(
        "lotto649.research_diagnostics._read_v6_committed_file_bytes",
        lambda _root, _commit, _path: Path(environment.cfg["_config_path"]).read_bytes(),
    )
    monkeypatch.setattr(
        "lotto649.research_diagnostics._validate_v6_outcome_boundaries",
        lambda _root, _registration: SimpleNamespace(
            registration_prefix_preserved=True,
            draws_fingerprint="b" * 64,
        ),
    )
    monkeypatch.setattr(
        "lotto649.research_diagnostics.load_draws",
        lambda _path: environment.draws,
    )
    monkeypatch.setattr(
        "lotto649.research_diagnostics.permute_draw_outcomes",
        lambda received, *, seed: (
            control_draws
            if tuple(received) == tuple(environment.draws) and seed == 649
            else pytest.fail("control must permute the registered prefix with seed 649")
        ),
    )

    def fake_analyze(history, target_date):
        analyses.append((tuple(history), target_date))
        return SimpleNamespace(active=target_date.year % 2 == 1)

    def fake_backtest(received_draws, cfg, start, end):
        assert cfg["backtest"]["models"] == [V6_MODEL]
        lane = next(
            lane
            for lane in HISTORICAL_LANES
            if lane.start == start and lane.end == end
        )
        source = "normal" if tuple(received_draws) == tuple(environment.draws) else "control"
        calls.append((lane.name, source, tuple(cfg["backtest"]["models"])))
        return _frame(
            environment.draws,
            lane,
            top12_hits=2 if source == "normal" else 1,
        )

    monkeypatch.setattr(
        "lotto649.research_diagnostics.analyze_entropy_regime", fake_analyze
    )
    monkeypatch.setattr(
        "lotto649.research_diagnostics.run_backtest", fake_backtest
    )
    return calls, analyses


@pytest.mark.parametrize(
    ("git_state", "message"),
    [
        (("7" * 40, ""), "must equal the local Git HEAD"),
        (("6" * 40, " M src/lotto649/example.py"), "worktree must be completely clean"),
        (("6" * 40, "?? src/lotto649/untracked.py"), "worktree must be completely clean"),
    ],
    ids=["head-mismatch", "tracked-dirty", "untracked-dirty"],
)
def test_v6_git_audit_fails_before_first_backtest(
    tmp_path, monkeypatch, git_state, message
):
    environment = _environment(tmp_path)
    calls, _analyses = _install_valid_run(monkeypatch, environment)
    monkeypatch.setattr(
        "lotto649.research_diagnostics._read_v6_git_audit_state",
        lambda _root: git_state,
    )

    with pytest.raises(RuntimeError, match=message):
        run_registered_v6_diagnostics(
            environment.cfg,
            code_commit="6" * 40,
            output_dir=tmp_path / "out",
        )

    assert calls == []
    assert not (tmp_path / "out").exists()


def test_v6_config_blob_and_loaded_config_are_bound_before_first_backtest(
    tmp_path, monkeypatch
):
    environment = _environment(tmp_path)
    calls, _analyses = _install_valid_run(monkeypatch, environment)
    monkeypatch.setattr(
        "lotto649.research_diagnostics._read_v6_committed_file_bytes",
        lambda _root, _commit, _path: b"project: {model_version: changed}\n",
    )

    with pytest.raises(RuntimeError, match="differs from the committed Git blob"):
        run_registered_v6_diagnostics(
            environment.cfg,
            code_commit="6" * 40,
            output_dir=tmp_path / "out",
        )

    assert calls == []
    assert not (tmp_path / "out").exists()


def test_v6_rejects_noncanonical_config_path_before_first_backtest(
    tmp_path, monkeypatch
):
    environment = _environment(tmp_path)
    calls, _analyses = _install_valid_run(monkeypatch, environment)
    alternate = tmp_path / "alternate.yaml"
    alternate.write_bytes(Path(environment.cfg["_config_path"]).read_bytes())
    environment.cfg["_config_path"] = alternate

    with pytest.raises(RuntimeError, match="canonical research config path"):
        run_registered_v6_diagnostics(
            environment.cfg,
            code_commit="6" * 40,
            output_dir=tmp_path / "out",
        )

    assert calls == []
    assert not (tmp_path / "out").exists()


def test_v6_refuses_to_overwrite_an_existing_report_before_first_backtest(
    tmp_path, monkeypatch
):
    environment = _environment(tmp_path)
    calls, _analyses = _install_valid_run(monkeypatch, environment)
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    existing = output_dir / "v6_entropy_regime_v6.0.0_historical.json"
    existing.write_text("immutable\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="refusing to overwrite"):
        run_registered_v6_diagnostics(
            environment.cfg,
            code_commit="6" * 40,
            output_dir=output_dir,
        )

    assert calls == []
    assert existing.read_text(encoding="utf-8") == "immutable\n"


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda environment: setattr(
                environment.v6_registration,
                "status",
                "historical_diagnostic_complete",
            ),
            "registration status must be registered",
        ),
        (
            lambda environment: environment.v6_registration.parameters.__setitem__(
                "minimum_history_draws", 299
            ),
            "minimum history must remain exactly 300",
        ),
        (
            lambda environment: environment.v5_registration.parameters.__setitem__(
                "minimum_history_draws", 299
            ),
            "V5 registry minimum history differs from V6",
        ),
    ],
    ids=["registration-status", "v6-minimum", "v5-registry-minimum"],
)
def test_v6_registration_preflight_is_frozen_before_first_backtest(
    tmp_path, monkeypatch, mutate, message
):
    environment = _environment(tmp_path)
    calls, _analyses = _install_valid_run(monkeypatch, environment)
    mutate(environment)

    with pytest.raises(RuntimeError, match=message):
        run_registered_v6_diagnostics(
            environment.cfg,
            code_commit="6" * 40,
            output_dir=tmp_path / "out",
        )

    assert calls == []
    assert not (tmp_path / "out").exists()


def test_v6_known_outcome_git_boundary_fails_before_first_backtest(
    tmp_path, monkeypatch
):
    environment = _environment(tmp_path)
    calls, _analyses = _install_valid_run(monkeypatch, environment)

    def reject_boundary(_root, _registration):
        raise RuntimeError("known outcome boundary mismatch")

    monkeypatch.setattr(
        "lotto649.research_diagnostics._validate_v6_outcome_boundaries",
        reject_boundary,
    )

    with pytest.raises(RuntimeError, match="known outcome boundary mismatch"):
        run_registered_v6_diagnostics(
            environment.cfg,
            code_commit="6" * 40,
            output_dir=tmp_path / "out",
        )

    assert calls == []
    assert not (tmp_path / "out").exists()


def test_v6_runner_reuses_frozen_references_and_scores_every_target_once_per_path(
    tmp_path, monkeypatch
):
    environment = _environment(tmp_path)
    calls, analyses = _install_valid_run(monkeypatch, environment)

    result = run_registered_v6_diagnostics(
        environment.cfg,
        code_commit="6" * 40,
        output_dir=tmp_path / "out",
    )

    assert calls == [
        (lane.name, source, (V6_MODEL,))
        for lane in HISTORICAL_LANES
        for source in ("normal", "control")
    ]
    assert len(analyses) == 2 * sum(
        len(_eligible_dates(environment.draws, lane))
        for lane in HISTORICAL_LANES
    )
    report = result["report"]
    assert report["schema_version"] == 2
    assert report["experiment_id"] == V6_EXPERIMENT_ID
    assert report["command"] == (
        "lotto649 --config config/research-v6-entropy-regime.yaml "
        f"research-v6 --code-commit {'6' * 40}"
    )
    assert report["data_boundaries"] == {
        "historical_diagnostic_prefix": {
            "path": "data/processed/draws.csv",
            "source_commit": "3" * 40,
            "sha256": environment.v6_registration.dataset_sha256,
            "draw_count": len(environment.draws),
            "history_through": "2026-08-12",
        },
        "outcomes_known_at_registration": {
            "source_commit": "9" * 40,
            "sha256": "a" * 64,
            "draw_count": len(environment.draws) + 1,
            "history_through": "2026-08-15",
        },
    }
    assert report["data_boundary_verification"] == {
        "git_verified": True,
        "registration_prefix_preserved": True,
        "known_outcomes_draws_fingerprint": "b" * 64,
    }
    assert report["reference_provenance"]["sha256"] == (
        environment.v6_registration.parameters["reference_report_sha256"]
    )
    assert report["prospective_cohort"]["status"] == "not_activated"
    assert report["prospective_cohort"]["freeze_commit"] is None
    assert report["prospective_cohort"]["activation_commit"] is None
    assert report["prospective_cohort"]["outcomes_known_at_activation"] is None
    assert report["prospective_cohort"]["cohort_start"] is None
    assert report["historical_decision"]["holm_gate_lane"] == "consumed_diagnostic"
    assert report["historical_decision"]["proper_score_max_delta_vs_fair"] == 1e-9
    for lane, reference_lane in zip(report["lanes"], environment.reference["lanes"]):
        assert lane["comparisons"][:-1] == reference_lane["comparisons"]
        assert lane["comparisons"][-1] == lane["candidate"]
        assert lane["candidate"]["draws"] == lane["eligible_targets"]
        assert lane["negative_control"]["draws"] == lane["eligible_targets"]
        assert (
            lane["candidate_activation"]["active_targets"]
            + lane["candidate_activation"]["inactive_targets"]
            == lane["eligible_targets"]
        )
        assert (
            lane["control_activation"]["active_targets"]
            + lane["control_activation"]["inactive_targets"]
            == lane["eligible_targets"]
        )
        if lane["lane"] == "consumed_diagnostic":
            assert lane["candidate"]["primary_holm_adjusted_p"] is not None
        else:
            assert lane["candidate"]["primary_holm_adjusted_p"] is None
        assert lane["negative_control"]["primary_holm_adjusted_p"] is None


def test_v6_report_serialization_is_deterministic(tmp_path, monkeypatch):
    environment = _environment(tmp_path)
    _install_valid_run(monkeypatch, environment)

    first = run_registered_v6_diagnostics(
        environment.cfg,
        code_commit="6" * 40,
        output_dir=tmp_path / "first",
    )
    second = run_registered_v6_diagnostics(
        environment.cfg,
        code_commit="6" * 40,
        output_dir=tmp_path / "second",
    )

    assert Path(first["json_path"]).read_bytes() == Path(second["json_path"]).read_bytes()
    assert Path(first["markdown_path"]).read_bytes() == Path(
        second["markdown_path"]
    ).read_bytes()


def test_v6_json_serialization_rejects_nonfinite_audit_values(
    tmp_path, monkeypatch
):
    environment = _environment(tmp_path)
    calls, _analyses = _install_valid_run(monkeypatch, environment)
    environment.cfg["features"]["nonfinite_audit_guard"] = float("nan")

    with pytest.raises(ValueError, match="Out of range float values"):
        run_registered_v6_diagnostics(
            environment.cfg,
            code_commit="6" * 40,
            output_dir=tmp_path / "out",
        )

    assert calls == []
    assert not (tmp_path / "out" / "v6_entropy_regime_v6.0.0_historical.json").exists()
    assert not (tmp_path / "out" / "v6_entropy_regime_v6.0.0_historical.md").exists()


def test_v6_reference_hash_tampering_fails_before_first_backtest(
    tmp_path, monkeypatch
):
    environment = _environment(tmp_path)
    calls, _analyses = _install_valid_run(monkeypatch, environment)
    environment.reference_path.write_text(
        environment.reference_path.read_text(encoding="utf-8") + "\n",
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="reference report fingerprint mismatch"):
        run_registered_v6_diagnostics(
            environment.cfg,
            code_commit="6" * 40,
            output_dir=tmp_path / "out",
        )

    assert calls == []
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize(
    "tamper",
    [
        lambda report: report.__setitem__("experiment_id", "wrong"),
        lambda report: report.__setitem__("model_version", "v5.changed"),
        lambda report: report["dataset"].__setitem__("sha256", "0" * 64),
        lambda report: report["lanes"][0]["dates"].__setitem__(
            "start", "1983-01-01"
        ),
        lambda report: report["lanes"][0].__setitem__("eligible_targets", 999),
        lambda report: report["lanes"][0]["comparisons"][0].__setitem__(
            "model_version", "v1.changed"
        ),
        lambda report: report["lanes"][0]["comparisons"][0].__setitem__(
            "draws", 999
        ),
        lambda report: report["registered_parameters"].__setitem__(
            "minimum_history_draws", 299
        ),
        lambda report: report["configuration"]["effective"]["backtest"].__setitem__(
            "min_history_draws", 299
        ),
    ],
    ids=[
        "experiment",
        "version",
        "dataset",
        "lane-dates",
        "eligible-count",
        "comparison-version",
        "comparison-row-count",
        "registered-minimum-history",
        "effective-config-minimum-history",
    ],
)
def test_v6_reference_semantic_tampering_fails_before_first_backtest(
    tmp_path, monkeypatch, tamper
):
    environment = _environment(tmp_path)
    tamper(environment.reference)
    environment.reference_path.write_text(
        json.dumps(environment.reference, indent=2, sort_keys=True), encoding="utf-8"
    )
    environment.v6_registration.parameters["reference_report_sha256"] = sha256(
        environment.reference_path.read_bytes()
    ).hexdigest()
    calls, _analyses = _install_valid_run(monkeypatch, environment)

    with pytest.raises(RuntimeError, match="frozen V5 reference"):
        run_registered_v6_diagnostics(
            environment.cfg,
            code_commit="6" * 40,
            output_dir=tmp_path / "out",
        )

    assert calls == []
    assert not (tmp_path / "out").exists()


def test_v6_candidate_frame_identity_tampering_fails_without_report(
    tmp_path, monkeypatch
):
    environment = _environment(tmp_path)
    calls, _analyses = _install_valid_run(monkeypatch, environment)

    def wrong_version_backtest(received_draws, cfg, start, end):
        lane = next(
            lane
            for lane in HISTORICAL_LANES
            if lane.start == start and lane.end == end
        )
        calls.append((lane.name, "tampered", tuple(cfg["backtest"]["models"])))
        frame = _frame(environment.draws, lane, top12_hits=2)
        frame["model_version"] = "v6.changed"
        return frame

    monkeypatch.setattr(
        "lotto649.research_diagnostics.run_backtest", wrong_version_backtest
    )

    with pytest.raises(RuntimeError, match="V6 backtest model version mismatch"):
        run_registered_v6_diagnostics(
            environment.cfg,
            code_commit="6" * 40,
            output_dir=tmp_path / "out",
        )

    assert len(calls) == 1
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda frame: frame.__setitem__("top_6_hits", [1.5] * len(frame)),
            "hit counts must be finite integers",
        ),
        (
            lambda frame: frame.__setitem__("top_18_hits", [7] * len(frame)),
            "hit counts must be between 0 and 6",
        ),
        (
            lambda frame: (
                frame.__setitem__("top_6_hits", [3] * len(frame)),
                frame.__setitem__("top_12_hits", [2] * len(frame)),
            ),
            "hit counts must satisfy Top-6 <= Top-12 <= Top-18",
        ),
        (
            lambda frame: frame.__setitem__("brier_score", [-0.01] * len(frame)),
            "proper scores must be finite and non-negative",
        ),
        (
            lambda frame: frame.__setitem__("log_loss", [float("inf")] * len(frame)),
            "proper scores must be finite and non-negative",
        ),
        (
            lambda frame: frame.__setitem__("mean_actual_rank", [0.0] * len(frame)),
            "mean actual rank must be finite and between 1 and 49",
        ),
        (
            lambda frame: frame.__setitem__(
                "mean_actual_rank", [float("nan")] * len(frame)
            ),
            "mean actual rank must be finite and between 1 and 49",
        ),
    ],
    ids=[
        "fractional-hits",
        "hits-out-of-range",
        "nonmonotone-hits",
        "negative-brier",
        "infinite-logloss",
        "rank-out-of-range",
        "nonfinite-rank",
    ],
)
def test_v6_frame_metric_contract_fails_before_control_or_report(
    tmp_path, monkeypatch, mutate, message
):
    environment = _environment(tmp_path)
    calls, _analyses = _install_valid_run(monkeypatch, environment)

    def tampered_backtest(received_draws, cfg, start, end):
        lane = next(
            lane
            for lane in HISTORICAL_LANES
            if lane.start == start and lane.end == end
        )
        calls.append((lane.name, "tampered", tuple(cfg["backtest"]["models"])))
        frame = _frame(environment.draws, lane, top12_hits=2)
        mutate(frame)
        return frame

    monkeypatch.setattr(
        "lotto649.research_diagnostics.run_backtest", tampered_backtest
    )

    with pytest.raises(RuntimeError, match=message):
        run_registered_v6_diagnostics(
            environment.cfg,
            code_commit="6" * 40,
            output_dir=tmp_path / "out",
        )

    assert len(calls) == 1
    assert not (tmp_path / "out").exists()


def test_cli_exposes_research_v6_with_required_code_commit(monkeypatch, capsys):
    import sys

    import lotto649.cli as cli

    captured = {}
    cfg = {
        "_root": "/tmp/v6-cli-root",
        "data": {"processed_csv": "data/processed/draws.csv"},
    }

    def fake_run(received_cfg, *, code_commit, output_dir):
        captured.update(
            cfg=received_cfg,
            code_commit=code_commit,
            output_dir=output_dir,
        )
        return {"json_path": "v6.json", "markdown_path": "v6.md", "report": {}}

    monkeypatch.setattr(cli, "load_config", lambda _path: cfg)
    monkeypatch.setattr(cli, "run_registered_v6_diagnostics", fake_run)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "lotto649",
            "--config",
            "config/research-v6-entropy-regime.yaml",
            "research-v6",
            "--code-commit",
            "6" * 40,
        ],
    )

    cli.main()

    assert captured == {
        "cfg": cfg,
        "code_commit": "6" * 40,
        "output_dir": Path("/tmp/v6-cli-root/reports"),
    }
    assert json.loads(capsys.readouterr().out) == {
        "json_path": "v6.json",
        "markdown_path": "v6.md",
    }
