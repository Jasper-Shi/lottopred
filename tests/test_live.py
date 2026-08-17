from datetime import date
import json
from pathlib import Path
from types import SimpleNamespace

from lotto649.domain import Draw
import lotto649.live as live_module
import pytest
import yaml

from lotto649.live import (
    evaluate_due_predictions,
    generate_next_predictions,
    next_draw_date,
    run_live_cycle,
)
from lotto649.notification import should_alert
from lotto649.research_protocol import draw_digest, snapshot_digest


ROOT = Path(__file__).resolve().parents[1]


def _live_prediction_config(tmp_path, *, model_versions=None):
    live = {
        "models": ["recent_frequency", "v3_boosting"],
        "shadow_models": ["v3_boosting"],
    }
    if model_versions is not None:
        live["model_versions"] = model_versions
    return {
        "_root": str(tmp_path),
        "project": {
            "model_version": "v1.0.0",
            "timezone": "America/Toronto",
        },
        "live": live,
        "features": {
            "logistic_training_draws": 480,
            "min_logistic_samples": 300,
            "v3_training_draws": 280,
            "v3_stride": 14,
            "v3_min_history": 300,
        },
        "prediction": {"candidate_pool_size": 12},
    }


def _single_live_history():
    return [Draw(date(2027, 1, 2), (1, 2, 3, 4, 5, 6), 7)]


def _verified_v3_release_evidence():
    return SimpleNamespace(
        experiment_id="V3_frozen_shadow_cohort",
        model_name="v3_boosting",
        model_version="v3.0.0",
        freeze_commit="a" * 40,
        activation_commit="b" * 40,
        release_commit="c" * 40,
        evidence_commit="d" * 40,
        immutable_registration_digest="1" * 64,
        activation_anchor_sha256="2" * 64,
        frozen_manifest_sha256="3" * 64,
        frozen_path_sha256={"requirements-live.lock": "4" * 64},
    )


def _write_v3_registry(
    tmp_path,
    *,
    active: bool,
    cohort_start: date = date(2026, 8, 19),
) -> None:
    payload = yaml.safe_load(
        (ROOT / "docs" / "experiments" / "registry.yaml").read_text(
            encoding="utf-8"
        )
    )
    v3 = next(
        experiment
        for experiment in payload["experiments"]
        if experiment["id"] == "V3_frozen_shadow_cohort"
    )
    if active:
        v3["status"] = "prospective_shadow"
        v3["prospective"] = {
            "status": "active",
            "role": "shadow",
            "minimum_eligible_draws": 208,
            "commit_deadline": "before_target_local_date",
            "freeze_commit": "a" * 40,
            "activation_commit": "b" * 40,
            "outcomes_known_at_activation": {
                "source_commit": v3["outcomes_known_at_registration"][
                    "source_commit"
                ],
                "sha256": v3["outcomes_known_at_registration"]["sha256"],
                "draw_count": v3["outcomes_known_at_registration"]["draw_count"],
                "history_through": v3["outcomes_known_at_registration"][
                    "history_through"
                ],
            },
            "cohort_start": cohort_start,
        }
        v3["result"] = {
            "decision": "continue_shadow",
            "decided_on": date(2026, 8, 16),
            "implementation_commit": "a" * 40,
            "report_json": "reports/prospective/v3-activation.json",
            "report_markdown": "docs/V2_V4_RESULTS.md",
            "result_file": "docs/experiments/V3_frozen_shadow_cohort.md",
            "historical_primary_signal_supported": False,
            "shadow_activation": "active",
        }
    registry_path = tmp_path / "docs" / "experiments" / "registry.yaml"
    registry_path.parent.mkdir(parents=True)
    registry_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def test_non_default_model_version_without_experiment_gate_suppresses_only_that_model(
    tmp_path,
):
    cfg = _live_prediction_config(
        tmp_path,
        model_versions={"v3_boosting": "v3.0.0"},
    )

    with pytest.warns(RuntimeWarning, match="prospective_experiment_gate_missing"):
        paths = generate_next_predictions(cfg, _single_live_history())

    assert [path.name for path in paths] == [
        "2027-01-06__recent_frequency__v1.0.0.json"
    ]
    assert not any("v3_boosting" in path.name for path in paths)


def test_registered_model_version_override_stays_dormant_until_cohort_is_active(
    tmp_path,
):
    _write_v3_registry(tmp_path, active=False)
    cfg = _live_prediction_config(
        tmp_path,
        model_versions={"v3_boosting": "v3.0.0"},
    )
    cfg["live"]["model_version_experiments"] = {
        "v3_boosting": "V3_frozen_shadow_cohort"
    }

    paths = generate_next_predictions(cfg, _single_live_history())

    assert {path.name for path in paths} == {
        "2027-01-06__recent_frequency__v1.0.0.json",
        "2027-01-06__v3_boosting__v1.0.0.json",
    }


def test_registered_model_version_override_activates_only_from_active_registry(
    tmp_path,
    monkeypatch,
):
    _write_v3_registry(tmp_path, active=True)
    cfg = _live_prediction_config(
        tmp_path,
        model_versions={"v3_boosting": "v3.0.0"},
    )
    cfg["live"]["model_version_experiments"] = {
        "v3_boosting": "V3_frozen_shadow_cohort"
    }
    monkeypatch.setattr(
        "lotto649.prospective.verify_live_release",
        lambda repository, experiment_id: _verified_v3_release_evidence(),
    )

    paths = generate_next_predictions(cfg, _single_live_history())

    assert {path.name for path in paths} == {
        "2027-01-06__recent_frequency__v1.0.0.json",
        "2027-01-06__v3_boosting__v3.0.0.json",
    }
    v3_payload = json.loads(
        next(path for path in paths if "v3_boosting" in path.name).read_text(
            encoding="utf-8"
        )
    )
    assert v3_payload["metadata"]["prospective_release"] == {
        "activation_anchor_sha256": "2" * 64,
        "activation_commit": "b" * 40,
        "experiment_id": "V3_frozen_shadow_cohort",
        "freeze_commit": "a" * 40,
        "frozen_manifest_sha256": "3" * 64,
        "generation_source_commit": "d" * 40,
        "immutable_registration_digest": "1" * 64,
        "release_commit": "c" * 40,
        "requirements_live_lock_sha256": "4" * 64,
    }


def test_active_registered_version_requires_verified_release_before_any_write(
    tmp_path,
    monkeypatch,
):
    _write_v3_registry(tmp_path, active=True)
    cfg = _live_prediction_config(
        tmp_path,
        model_versions={"v3_boosting": "v3.0.0"},
    )
    cfg["live"]["model_version_experiments"] = {
        "v3_boosting": "V3_frozen_shadow_cohort"
    }

    def reject_release(repository, experiment_id):
        raise RuntimeError("frozen release evidence is invalid")

    monkeypatch.setattr(
        "lotto649.prospective.verify_live_release",
        reject_release,
    )

    with pytest.warns(RuntimeWarning, match="prospective_release_verification_failed"):
        paths = generate_next_predictions(cfg, _single_live_history())

    assert [path.name for path in paths] == [
        "2027-01-06__recent_frequency__v1.0.0.json"
    ]
    assert not any("v3_boosting" in path.name for path in paths)


def test_active_registered_version_rejects_release_identity_mismatch_before_write(
    tmp_path,
    monkeypatch,
):
    _write_v3_registry(tmp_path, active=True)
    cfg = _live_prediction_config(
        tmp_path,
        model_versions={"v3_boosting": "v3.0.0"},
    )
    cfg["live"]["model_version_experiments"] = {
        "v3_boosting": "V3_frozen_shadow_cohort"
    }
    evidence = _verified_v3_release_evidence()
    evidence = SimpleNamespace(**{**vars(evidence), "model_version": "v3.0.1"})
    monkeypatch.setattr(
        "lotto649.prospective.verify_live_release",
        lambda repository, experiment_id: evidence,
    )

    with pytest.warns(RuntimeWarning, match="prospective_release_identity_mismatch"):
        paths = generate_next_predictions(cfg, _single_live_history())

    assert [path.name for path in paths] == [
        "2027-01-06__recent_frequency__v1.0.0.json"
    ]
    assert not any("v3_boosting" in path.name for path in paths)


def test_active_registered_version_rejects_target_before_cohort_start(
    tmp_path,
    monkeypatch,
):
    _write_v3_registry(
        tmp_path,
        active=True,
        cohort_start=date(2027, 1, 10),
    )
    cfg = _live_prediction_config(
        tmp_path,
        model_versions={"v3_boosting": "v3.0.0"},
    )
    cfg["live"]["model_version_experiments"] = {
        "v3_boosting": "V3_frozen_shadow_cohort"
    }
    monkeypatch.setattr(
        "lotto649.prospective.verify_live_release",
        lambda repository, experiment_id: _verified_v3_release_evidence(),
    )

    with pytest.warns(RuntimeWarning, match="prospective_target_outside_cohort"):
        paths = generate_next_predictions(cfg, _single_live_history())

    assert [path.name for path in paths] == [
        "2027-01-06__recent_frequency__v1.0.0.json"
    ]
    assert not any("v3_boosting" in path.name for path in paths)


def test_unknown_registered_experiment_suppresses_only_prospective_model(
    tmp_path,
):
    _write_v3_registry(tmp_path, active=False)
    cfg = _live_prediction_config(
        tmp_path,
        model_versions={"v3_boosting": "v3.0.0"},
    )
    cfg["live"]["model_version_experiments"] = {
        "v3_boosting": "missing_experiment"
    }

    with pytest.warns(RuntimeWarning, match="prospective_experiment_not_found"):
        paths = generate_next_predictions(cfg, _single_live_history())

    assert [path.name for path in paths] == [
        "2027-01-06__recent_frequency__v1.0.0.json"
    ]
    assert not any("v3_boosting" in path.name for path in paths)


@pytest.mark.parametrize("registry_text", [None, "not: [valid yaml"])
def test_missing_or_invalid_registry_suppresses_only_prospective_model(
    tmp_path,
    registry_text,
):
    cfg = _live_prediction_config(
        tmp_path,
        model_versions={"v3_boosting": "v3.0.0"},
    )
    cfg["live"]["model_version_experiments"] = {
        "v3_boosting": "V3_frozen_shadow_cohort"
    }
    if registry_text is not None:
        registry_path = tmp_path / "docs" / "experiments" / "registry.yaml"
        registry_path.parent.mkdir(parents=True)
        registry_path.write_text(registry_text, encoding="utf-8")

    with pytest.warns(
        RuntimeWarning,
        match="prospective_registry_verification_failed",
    ):
        paths = generate_next_predictions(cfg, _single_live_history())

    assert [path.name for path in paths] == [
        "2027-01-06__recent_frequency__v1.0.0.json"
    ]
    assert not any("v3_boosting" in path.name for path in paths)


def test_registered_experiment_identity_mismatch_suppresses_only_shadow(tmp_path):
    _write_v3_registry(tmp_path, active=False)
    registry_path = tmp_path / "docs" / "experiments" / "registry.yaml"
    payload = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    v3 = next(
        experiment
        for experiment in payload["experiments"]
        if experiment["id"] == "V3_frozen_shadow_cohort"
    )
    v3["model_version"] = "v3.0.1"
    registry_path.write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )
    cfg = _live_prediction_config(
        tmp_path,
        model_versions={"v3_boosting": "v3.0.0"},
    )
    cfg["live"]["model_version_experiments"] = {
        "v3_boosting": "V3_frozen_shadow_cohort"
    }

    with pytest.warns(
        RuntimeWarning,
        match="prospective_experiment_identity_mismatch",
    ):
        paths = generate_next_predictions(cfg, _single_live_history())

    assert [path.name for path in paths] == [
        "2027-01-06__recent_frequency__v1.0.0.json"
    ]
    assert not any("v3_boosting" in path.name for path in paths)


def test_prospective_model_prediction_failure_does_not_block_v1(
    tmp_path,
    monkeypatch,
):
    _write_v3_registry(tmp_path, active=True)
    cfg = _live_prediction_config(
        tmp_path,
        model_versions={"v3_boosting": "v3.0.0"},
    )
    cfg["live"]["model_version_experiments"] = {
        "v3_boosting": "V3_frozen_shadow_cohort"
    }
    monkeypatch.setattr(
        "lotto649.prospective.verify_live_release",
        lambda repository, experiment_id: _verified_v3_release_evidence(),
    )
    from lotto649.live import make_prediction as real_make_prediction

    def fail_v3(model, draws, target, config, version):
        if model.name == "v3_boosting":
            raise RuntimeError("synthetic V3 contract failure")
        return real_make_prediction(model, draws, target, config, version)

    monkeypatch.setattr("lotto649.live.make_prediction", fail_v3)

    with pytest.warns(RuntimeWarning, match="prospective_prediction_failed"):
        paths = generate_next_predictions(cfg, _single_live_history())

    assert [path.name for path in paths] == [
        "2027-01-06__recent_frequency__v1.0.0.json"
    ]
    assert not any("v3_boosting" in path.name for path in paths)


def test_shared_prediction_storage_failure_is_not_suppressed(tmp_path, monkeypatch):
    cfg = _live_prediction_config(tmp_path)

    def fail_storage(*_args, **_kwargs):
        raise OSError("synthetic shared storage failure")

    monkeypatch.setattr("lotto649.live.save_prediction", fail_storage)

    with pytest.raises(OSError, match="shared storage failure"):
        generate_next_predictions(cfg, _single_live_history())


@pytest.mark.parametrize(
    ("raw_count", "audit_status", "held", "audit_calls"),
    [
        (207, "ready", False, 0),
        (208, "collecting", False, 1),
        (208, "waiting_for_earlier_pending", True, 1),
        (208, "ready", True, 1),
        (208, "overdue", True, 1),
        (208, "formal_look_recorded", True, 1),
    ],
)
def test_prospective_collection_interlock_starts_only_at_registered_checkpoint(
    tmp_path,
    monkeypatch,
    raw_count,
    audit_status,
    held,
    audit_calls,
):
    _write_v3_registry(tmp_path, active=True)
    cfg = _live_prediction_config(
        tmp_path,
        model_versions={"v3_boosting": "v3.0.0"},
    )
    cfg["live"]["model_version_experiments"] = {
        "v3_boosting": "V3_frozen_shadow_cohort"
    }
    evaluations = tmp_path / "evaluations"
    evaluations.mkdir()
    for index in range(raw_count):
        (evaluations / f"{index:03d}__v3_boosting__v3.0.0.json").write_text(
            "{}\n",
            encoding="utf-8",
        )
    calls = []

    def fake_audit(repository, experiment_id):
        calls.append((repository, experiment_id))
        return SimpleNamespace(status=audit_status)

    monkeypatch.setattr(
        "lotto649.prospective.audit_registered_cohort",
        fake_audit,
    )

    holds, quotas, messages = live_module._prospective_collection_interlocks(cfg)

    identity = ("v3_boosting", "v3.0.0")
    assert (identity in holds) is held
    assert len(calls) == audit_calls
    assert bool(messages) is held
    if held:
        assert identity not in quotas
    else:
        assert quotas[identity] == 1


def test_prospective_collection_audit_failure_holds_only_candidate(
    tmp_path,
    monkeypatch,
):
    _write_v3_registry(tmp_path, active=True)
    cfg = _live_prediction_config(
        tmp_path,
        model_versions={"v3_boosting": "v3.0.0"},
    )
    cfg["live"]["model_version_experiments"] = {
        "v3_boosting": "V3_frozen_shadow_cohort"
    }
    evaluations = tmp_path / "evaluations"
    evaluations.mkdir()
    for index in range(208):
        (evaluations / f"{index:03d}__v3_boosting__v3.0.0.json").write_text(
            "{}\n",
            encoding="utf-8",
        )

    def fail_audit(repository, experiment_id):
        raise RuntimeError("synthetic integrity failure")

    monkeypatch.setattr(
        "lotto649.prospective.audit_registered_cohort",
        fail_audit,
    )

    holds, quotas, messages = live_module._prospective_collection_interlocks(cfg)

    assert holds == {("v3_boosting", "v3.0.0")}
    assert quotas == {}
    assert len(messages) == 1
    assert "prospective_collection_audit_failed" in messages[0]


def test_formal_claim_interlock_stops_v3_without_running_full_audit(
    tmp_path,
    monkeypatch,
):
    _write_v3_registry(tmp_path, active=True)
    cfg = _live_prediction_config(
        tmp_path,
        model_versions={"v3_boosting": "v3.0.0"},
    )
    cfg["live"]["model_version_experiments"] = {
        "v3_boosting": "V3_frozen_shadow_cohort"
    }
    claim = (
        tmp_path
        / "reports"
        / "prospective"
        / "V3_frozen_shadow_cohort__v3.0.0__formal.claim"
    )
    claim.parent.mkdir(parents=True)
    claim.write_text("sealed\n", encoding="utf-8")

    def forbidden_audit(*_args, **_kwargs):
        raise AssertionError("claim interlock must precede full audit")

    monkeypatch.setattr(
        "lotto649.prospective.audit_registered_cohort",
        forbidden_audit,
    )

    with pytest.warns(RuntimeWarning, match="prospective_collection_interlocked"):
        paths = generate_next_predictions(cfg, _single_live_history())

    assert [path.name for path in paths] == [
        "2027-01-06__recent_frequency__v1.0.0.json"
    ]


def test_interlocked_due_evaluation_skips_only_v3(tmp_path):
    cfg = _live_prediction_config(tmp_path)
    cfg["notifications"] = {"enabled": False}
    history = _single_live_history()
    paths = generate_next_predictions(cfg, history)
    actual = Draw(date(2027, 1, 6), (7, 8, 9, 10, 11, 12), 13)

    completed = evaluate_due_predictions(
        cfg,
        [*history, actual],
        held_model_versions={("v3_boosting", "v1.0.0")},
    )

    assert [item["model_name"] for item in completed] == ["recent_frequency"]
    assert (tmp_path / "evaluations" / paths[0].name).is_file()
    assert not (
        tmp_path
        / "evaluations"
        / "2027-01-06__v3_boosting__v1.0.0.json"
    ).exists()


def test_raw_207_catchup_admits_only_one_v3_evaluation_but_all_v1(
    tmp_path,
    monkeypatch,
):
    _write_v3_registry(tmp_path, active=True)
    cfg = _live_prediction_config(
        tmp_path,
        model_versions={"v3_boosting": "v3.0.0"},
    )
    cfg["live"]["model_version_experiments"] = {
        "v3_boosting": "V3_frozen_shadow_cohort"
    }
    cfg["notifications"] = {"enabled": False}
    monkeypatch.setattr(
        "lotto649.prospective.verify_live_release",
        lambda repository, experiment_id: _verified_v3_release_evidence(),
    )

    first_history = [Draw(date(2026, 12, 26), (1, 2, 3, 4, 5, 6), 7)]
    generate_next_predictions(cfg, first_history)
    first_actual = Draw(date(2026, 12, 30), (7, 8, 9, 10, 11, 12), 13)
    second_history = [*first_history, first_actual]
    generate_next_predictions(cfg, second_history)
    second_actual = Draw(date(2027, 1, 2), (14, 15, 16, 17, 18, 19), 20)

    evaluations = tmp_path / "evaluations"
    evaluations.mkdir()
    for index in range(207):
        (evaluations / f"{index:03d}__v3_boosting__v3.0.0.json").write_text(
            "{}\n",
            encoding="utf-8",
        )
    holds, quotas, messages = live_module._prospective_collection_interlocks(cfg)
    assert holds == set()
    assert messages == []
    assert quotas == {("v3_boosting", "v3.0.0"): 1}

    completed = evaluate_due_predictions(
        cfg,
        [*second_history, second_actual],
        held_model_versions=holds,
        model_version_quotas=quotas,
    )

    assert [item["model_name"] for item in completed].count("recent_frequency") == 2
    assert [item["model_name"] for item in completed].count("v3_boosting") == 1
    assert not (
        evaluations / "2027-01-02__v3_boosting__v3.0.0.json"
    ).exists()


def test_ready_208_live_cycle_keeps_v1_and_admits_no_209th_v3_evaluation(
    tmp_path,
    monkeypatch,
):
    _write_v3_registry(tmp_path, active=True)
    cfg = _live_prediction_config(
        tmp_path,
        model_versions={"v3_boosting": "v3.0.0"},
    )
    cfg["live"]["model_version_experiments"] = {
        "v3_boosting": "V3_frozen_shadow_cohort"
    }
    cfg["notifications"] = {"enabled": False}
    monkeypatch.setattr(
        "lotto649.prospective.verify_live_release",
        lambda repository, experiment_id: _verified_v3_release_evidence(),
    )
    history = [Draw(date(2026, 12, 30), (1, 2, 3, 4, 5, 6), 7)]
    initial_paths = generate_next_predictions(cfg, history)
    assert any("v3_boosting__v3.0.0" in path.name for path in initial_paths)

    evaluations = tmp_path / "evaluations"
    evaluations.mkdir()
    for index in range(208):
        (evaluations / f"{index:03d}__v3_boosting__v3.0.0.json").write_text(
            "{}\n",
            encoding="utf-8",
        )
    monkeypatch.setattr(
        "lotto649.prospective.audit_registered_cohort",
        lambda repository, experiment_id: SimpleNamespace(status="ready"),
    )
    actual = Draw(date(2027, 1, 2), (7, 8, 9, 10, 11, 12), 13)
    monkeypatch.setattr(
        "lotto649.live.refresh_data",
        lambda _cfg: [*history, actual],
    )

    with pytest.warns(RuntimeWarning, match="prospective_collection_interlocked"):
        result = run_live_cycle(cfg)

    assert result["evaluations_created"] == 1
    assert [Path(path).name for path in result["predictions_created"]] == [
        "2027-01-06__recent_frequency__v1.0.0.json"
    ]
    assert not (
        evaluations / "2027-01-02__v3_boosting__v3.0.0.json"
    ).exists()
    assert (
        evaluations / "2027-01-02__recent_frequency__v1.0.0.json"
    ).is_file()


def test_live_without_model_version_overrides_preserves_default_version(tmp_path):
    cfg = _live_prediction_config(tmp_path)

    paths = generate_next_predictions(cfg, _single_live_history())

    assert {path.name for path in paths} == {
        "2027-01-06__recent_frequency__v1.0.0.json",
        "2027-01-06__v3_boosting__v1.0.0.json",
    }
    payloads = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    assert {payload["model_version"] for payload in payloads} == {"v1.0.0"}


def test_live_rejects_non_mapping_model_versions_before_writing(tmp_path):
    cfg = _live_prediction_config(tmp_path, model_versions=["v3.0.0"])

    with pytest.raises(ValueError, match="live.model_versions must be a mapping"):
        generate_next_predictions(cfg, _single_live_history())

    assert not (tmp_path / "predictions").exists()


def test_live_rejects_model_version_for_unknown_live_model_before_writing(tmp_path):
    cfg = _live_prediction_config(
        tmp_path,
        model_versions={"v3_boostng": "v3.0.0"},
    )

    with pytest.raises(ValueError, match="unknown live models.*v3_boostng"):
        generate_next_predictions(cfg, _single_live_history())

    assert not (tmp_path / "predictions").exists()


@pytest.mark.parametrize("version", ["", "   "])
def test_live_rejects_empty_model_version_before_writing(tmp_path, version):
    cfg = _live_prediction_config(
        tmp_path,
        model_versions={"v3_boosting": version},
    )

    with pytest.raises(ValueError, match="non-empty version string"):
        generate_next_predictions(cfg, _single_live_history())

    assert not (tmp_path / "predictions").exists()


def test_live_rejects_non_string_model_version_before_writing(tmp_path):
    cfg = _live_prediction_config(
        tmp_path,
        model_versions={"v3_boosting": 3},
    )

    with pytest.raises(ValueError, match="non-empty version string"):
        generate_next_predictions(cfg, _single_live_history())

    assert not (tmp_path / "predictions").exists()


def test_live_model_version_override_does_not_overwrite_existing_snapshot(tmp_path):
    cfg = _live_prediction_config(
        tmp_path,
        model_versions={"v3_boosting": "v3.0.0"},
    )
    existing = (
        tmp_path
        / "predictions"
        / "2027-01-06__v3_boosting__v3.0.0.json"
    )
    existing.parent.mkdir()
    original = b"immutable pre-draw snapshot\n"
    existing.write_bytes(original)

    with pytest.warns(RuntimeWarning, match="prospective_experiment_gate_missing"):
        paths = generate_next_predictions(cfg, _single_live_history())

    assert [path.name for path in paths] == [
        "2027-01-06__recent_frequency__v1.0.0.json"
    ]
    assert existing.read_bytes() == original


def test_next_draw_date():
    assert next_draw_date(date(2026, 8, 12)) == date(2026, 8, 15)
    assert next_draw_date(date(2026, 8, 15)) == date(2026, 8, 19)


def test_live_cycle_reports_structured_prospective_warning_without_blocking_v1(
    tmp_path,
    monkeypatch,
):
    warning = (
        "prospective_release_verification_failed: model=v3_boosting "
        "experiment=V3_frozen_shadow_cohort detail=invalid release"
    )
    v1_path = tmp_path / "predictions" / "v1.json"
    monkeypatch.setattr(
        "lotto649.live.refresh_data",
        lambda cfg: _single_live_history(),
    )
    monkeypatch.setattr(
        "lotto649.live.evaluate_due_predictions",
        lambda cfg, draws, **_kwargs: [],
    )
    monkeypatch.setattr(
        "lotto649.live._generate_next_predictions",
        lambda cfg, draws, **_kwargs: ([v1_path], [warning]),
    )

    with pytest.warns(RuntimeWarning, match="prospective_release_verification_failed"):
        result = run_live_cycle({"_root": str(tmp_path), "live": {}})

    assert result == {
        "latest_draw": "2027-01-02",
        "draw_count": 1,
        "evaluations_created": 0,
        "predictions_created": [str(v1_path)],
        "prediction_warnings": [warning],
    }


def test_notification_thresholds():
    cfg = {"notifications": {"min_final_hits": 4, "min_top12_hits": 5}}
    assert should_alert({"final_6_hits": 4, "top_12_hits": 2}, cfg)
    assert should_alert({"final_6_hits": 1, "top_12_hits": 5}, cfg)
    assert not should_alert({"final_6_hits": 3, "top_12_hits": 4}, cfg)


def test_future_evaluation_binds_snapshot_and_verified_data_boundary(tmp_path):
    target = date(2027, 1, 6)
    payload = {
        "target_draw_date": target.isoformat(),
        "generated_at": "2027-01-03T12:00:00-05:00",
        "model_name": "audit_model",
        "model_version": "v9.0.0",
        "probabilities": {str(number): 6 / 49 for number in range(1, 50)},
        "top6": [1, 2, 3, 4, 5, 6],
        "top12": list(range(1, 13)),
        "top18": list(range(1, 19)),
        "final_combination": [1, 2, 3, 4, 5, 6],
        "metadata": {
            "role": "shadow",
            "history_draws": 2,
            "history_through": "2027-01-02",
        },
    }
    prediction_path = tmp_path / "predictions" / (
        "2027-01-06__audit_model__v9.0.0.json"
    )
    prediction_path.parent.mkdir()
    prediction_path.write_text(json.dumps(payload), encoding="utf-8")
    draws = [
        Draw(date(2027, 1, 2), (8, 9, 10, 11, 12, 13), 14),
        Draw(target, (1, 2, 3, 4, 5, 6), 7),
    ]
    cfg = {"_root": str(tmp_path), "notifications": {"enabled": False}}

    evaluations = evaluate_due_predictions(cfg, draws)

    assert len(evaluations) == 1
    evaluation = evaluations[0]
    assert evaluation["prediction_snapshot_path"] == (
        "predictions/2027-01-06__audit_model__v9.0.0.json"
    )
    assert evaluation["prediction_snapshot_digest"] == snapshot_digest(payload)
    assert evaluation["actual_draw_digest"] == draw_digest(draws[-1])
    assert evaluation["verified_data_draw_count"] == 2
    assert evaluation["verified_data_history_through"] == "2027-01-06"
    saved = json.loads(
        (tmp_path / "evaluations" / prediction_path.name).read_text(encoding="utf-8")
    )
    assert saved == evaluation


def test_research_config_cannot_run_or_generate_live_predictions(tmp_path):
    cfg = {
        "_root": str(tmp_path),
        "live": {"enabled": False, "models": [], "shadow_models": []},
    }
    draws = [Draw(date(2027, 1, 2), (1, 2, 3, 4, 5, 6), 7)]

    with pytest.raises(RuntimeError, match="live execution is disabled"):
        generate_next_predictions(cfg, draws)
    with pytest.raises(RuntimeError, match="live execution is disabled"):
        evaluate_due_predictions(cfg, draws)
    with pytest.raises(RuntimeError, match="live execution is disabled"):
        run_live_cycle(cfg)
