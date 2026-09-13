"""Synthetic and closed-math evidence checks; never read target-answer files."""

from __future__ import annotations

import copy
import hashlib
import json
import math
from datetime import date, timedelta
from pathlib import Path

import pytest
import yaml

from lotto649 import v13_evidence as evidence
from lotto649.domain import Draw
from lotto649.models.v13_main_set_overlap import (
    MainDraw,
    forecast_candidate,
    forecast_control,
)


@pytest.fixture(scope="module")
def contract():
    import lotto649

    # Source only: no history, reports, evaluations or prediction payloads.
    root = Path(lotto649.__file__).resolve().parents[2]
    path = (
        root / "evidence/research_registrations/v13-post-rng-main-set-overlap-v1.json"
    )
    registration = json.loads(path.read_text())
    assert (
        hashlib.sha256(
            evidence.canonical_json_bytes(registration["scientific_contract"])
        ).hexdigest()
        == evidence.SCIENTIFIC_CONTRACT_SHA256
    )
    assert (
        hashlib.sha256(
            evidence.canonical_json_bytes(registration["operational_contract"])
        ).hexdigest()
        == evidence.OPERATIONAL_CONTRACT_SHA256
    )
    return registration


@pytest.fixture(scope="module")
def bindings():
    return {
        "synthetic_only": True,
        "pure_core_sha256": "a" * 64,
        "statistical_fingerprint_sha256": evidence.SCIENTIFIC_CONTRACT_SHA256,
        "operational_contract_sha256": evidence.OPERATIONAL_CONTRACT_SHA256,
    }


def _hash(value):
    return hashlib.sha256(evidence.canonical_json_bytes(value)).hexdigest()


def _refresh(payload):
    payload["forecast_sha256_by_model"] = {
        f["model_name"]: _hash(f) for f in payload["forecasts"]
    }
    return payload


@pytest.fixture(scope="module")
def fair_template(bindings):
    anchor = (4, 11, 19, 27, 38, 49)
    cutoff = date(2019, 5, 15)
    target = date(2019, 5, 18)
    main = [MainDraw(cutoff, anchor)]
    forecasts = [
        evidence.serialize_overlap_forecast(forecast_candidate(main, target)),
        evidence.serialize_overlap_forecast(forecast_control(main, target)),
        evidence.serialize_comparator_forecast(
            evidence.ENSEMBLE_MODEL_NAME, {i: 6.0 / 49.0 for i in range(1, 50)}
        ),
        evidence.serialize_comparator_forecast(
            evidence.RANDOM_MODEL_NAME, {i: 6.0 / 49.0 for i in range(1, 50)}
        ),
    ]
    return _refresh(
        {
            "schema_version": "lotto649-v13.0.0-frozen-forecast-v1",
            "classification": evidence.SYNTHETIC_CLASSIFICATION,
            "model_version": evidence.MODEL_VERSION,
            "target_draw_date": target.isoformat(),
            "history_through": cutoff.isoformat(),
            "training_cutoff_date": cutoff.isoformat(),
            "visible_prefix_sha256": "b" * 64,
            "visible_prefix_draw_count": 1,
            "bindings": copy.deepcopy(bindings),
            "forecasts": forecasts,
        }
    )


def _fixture_payload(template, target):
    result = copy.deepcopy(template)
    history = []
    day = date(2019, 5, 15)
    while day < target:
        numbers = (
            (1, 3, 5, 7, 9, 11) if len(history) % 2 == 0 else (25, 27, 29, 31, 33, 35)
        )
        history.append(MainDraw(day, numbers))
        day += timedelta(days=3 if day.weekday() == 2 else 4)
    result["target_draw_date"] = target.isoformat()
    result["history_through"] = result["training_cutoff_date"] = history[
        -1
    ].draw_date.isoformat()
    result["visible_prefix_draw_count"] = len(history)
    result["forecasts"][:2] = [
        evidence.serialize_overlap_forecast(forecast_candidate(history, target)),
        evidence.serialize_overlap_forecast(forecast_control(history, target)),
    ]
    return _refresh(result)


def _scored_rows(template, count, actual=(13, 14, 15, 16, 17, 18)):
    rows, counts = [], []
    for index, iso in enumerate(evidence._registered_dates()[:count]):
        target = date.fromisoformat(iso)
        payload = _fixture_payload(template, target)
        row = evidence.score_target(
            evidence.canonical_json_bytes(payload), Draw(target, actual, 49)
        )
        counts.append(row["unique_opportunity_count"])
        row.update(
            {
                "prediction_generated_at": "2026-09-13T00:00:00Z",
                "prediction_frozen_event_sequence": 2 * index + 1,
                "prediction_frozen_event_sha256": "c" * 64,
                "scored_event_sequence": 2 * index + 2,
                "scored_event_sha256": "d" * 64,
                "cumulative_opportunities": evidence.opportunity_summary(counts),
            }
        )
        rows.append(row)
    return rows


def test_closed_registered_schemas_and_no_old_runtime_imports(contract):
    op = contract["operational_contract"]["claim_ledger_publication"]
    assert evidence._FORECAST_KEYS == set(op["forecast_exact_keys"])
    assert evidence._STATE_KEYS == set(op["scientific_state_exact_keys"])
    assert evidence._PAYLOAD_KEYS == set(op["frozen_payload_exact_keys"])
    assert evidence._SCORE_KEYS == set(op["score_exact_keys"])
    assert evidence.GATE_NAMES == tuple(
        g["name"] for g in contract["scientific_contract"]["gates"]
    )
    source = Path(evidence.__file__).read_text()
    for forbidden in (
        "v12_0_2_evidence",
        "v12_parity_transition",
        "registered_attempt",
        "send_email",
        "load_published_history",
        "exec(",
        "eval(",
    ):
        assert forbidden not in source


@pytest.mark.parametrize(
    "payload",
    [
        b'{"x":1,"x":2}\n',
        b'{"x":NaN}\n',
        b'{"x":Infinity}\n',
        b'{ "x":1}\n',
        b'{"x":1}',
        b'{"x":1}\n\n',
        b'{"x":"\\ud800"}\n',
    ],
)
def test_canonical_json_rejects_duplicate_nonfinite_or_noncanonical(payload):
    with pytest.raises((ValueError, UnicodeError)):
        evidence.decode_canonical_json(payload)


def test_full49_hex_state_roundtrip(fair_template):
    raw = evidence.canonical_json_bytes(fair_template)
    evidence.validate_frozen_payload(raw)
    assert evidence.decode_canonical_json(raw) == fair_template
    for index, f in enumerate(fair_template["forecasts"]):
        assert set(f["probabilities"]) == {str(i) for i in range(1, 50)}
        assert len(f["ranking"]) == 49
        assert f["final6"] == [1, 2, 3, 4, 5, 6]
        for number in range(1, 50):
            assert (
                f["probabilities"][str(number)].hex()
                == f["probability_hex"][str(number)]
            )
        if index == 0:
            assert f["scientific_state"]["transformed_anchor"] is None
        if index == 1:
            assert f["scientific_state"]["transformed_anchor"] == [1, 5, 12, 20, 28, 39]


@pytest.mark.parametrize(
    "mutation",
    [
        "unknown_payload",
        "missing_payload",
        "date",
        "cutoff",
        "draw_count_bool",
        "prefix_sha",
        "forecast_order",
        "forecast_digest",
        "missing_probability",
        "probability_bool",
        "probability_hex",
        "ranking",
        "top6",
        "top12",
        "top18",
        "final6",
        "feature",
        "version",
        "unknown_forecast",
        "unknown_state",
        "negative_zero",
        "beta_hex",
        "mean",
        "mean_hex",
        "complement_mean",
        "log_z",
        "candidate_transformed",
        "control_map",
        "source_anchor",
        "source_date",
        "count_bool",
        "count_bound",
        "overlap_sum",
        "counts_sha",
        "projection_sha",
        "comparator_state",
        "comparator_final",
    ],
)
def test_tampering_rejected_before_reveal(fair_template, mutation):
    p = copy.deepcopy(fair_template)
    f, control, comparator = p["forecasts"][0], p["forecasts"][1], p["forecasts"][2]
    state = f["scientific_state"]
    if mutation == "unknown_payload":
        p["extra"] = 1
    elif mutation == "missing_payload":
        del p["bindings"]
    elif mutation == "date":
        p["target_draw_date"] = p["history_through"]
    elif mutation == "cutoff":
        p["training_cutoff_date"] = "2019-12-27"
    elif mutation == "draw_count_bool":
        p["visible_prefix_draw_count"] = True
    elif mutation == "prefix_sha":
        p["visible_prefix_sha256"] = "bad"
    elif mutation == "forecast_order":
        p["forecasts"].reverse()
    elif mutation == "forecast_digest":
        p["forecast_sha256_by_model"][f["model_name"]] = "e" * 64
    elif mutation == "missing_probability":
        del f["probabilities"]["49"]
    elif mutation == "probability_bool":
        f["probabilities"]["49"] = True
    elif mutation == "probability_hex":
        f["probability_hex"]["49"] = "0x1p-3"
    elif mutation == "ranking":
        f["ranking"][0], f["ranking"][1] = f["ranking"][1], f["ranking"][0]
    elif mutation in ("top6", "top12", "top18"):
        f[mutation][-1] = 49
    elif mutation == "final6":
        f["final6"] = [2, 3, 4, 5, 6, 7]
    elif mutation == "feature":
        f["feature_set"] = "other"
    elif mutation == "version":
        f["model_version"] = "v12.0.2"
    elif mutation == "unknown_forecast":
        f["extra"] = 0
    elif mutation == "unknown_state":
        state["eta"] = 0.0
    elif mutation == "negative_zero":
        state["beta"] = -0.0
        state["beta_hex"] = "-0x0.0p+0"
    elif mutation in ("mean", "complement_mean", "log_z"):
        state[mutation] = math.nextafter(state[mutation], math.inf)
        state[mutation + "_hex"] = state[mutation].hex()
    elif mutation in ("beta_hex", "mean_hex"):
        state[mutation] = "0x1.0000000000000p+0"
    elif mutation == "candidate_transformed":
        state["transformed_anchor"] = state["source_anchor"]
    elif mutation == "control_map":
        control["scientific_state"]["transformed_anchor"] = state["source_anchor"]
    elif mutation == "source_anchor":
        state["source_anchor"] = [1, 2, 3, 4, 5, 6]
    elif mutation == "source_date":
        state["source_draw_date"] = "2019-12-25"
    elif mutation == "count_bool":
        state["training_pair_count"] = False
    elif mutation == "count_bound":
        state["training_pair_count"] = 4444
    elif mutation == "overlap_sum":
        state["training_overlap_sum"] = 1
    elif mutation == "counts_sha":
        state["counts_sha256"] = "e" * 64
    elif mutation == "projection_sha":
        state["scientific_projection_sha256"] = "e" * 64
    elif mutation == "comparator_state":
        comparator["scientific_state"] = state
    elif mutation == "comparator_final":
        comparator["final6"] = [2, 3, 4, 5, 6, 7]
    if mutation != "forecast_digest":
        _refresh(p)
    with pytest.raises(ValueError):
        evidence.validate_frozen_payload(evidence.canonical_json_bytes(p))


def test_scoring_never_predicts_or_solves_and_excludes_bonus(
    fair_template, monkeypatch
):
    def forbidden(*args, **kwargs):
        raise AssertionError("reveal attempted to fit or predict")

    monkeypatch.setattr(evidence, "forecast_candidate", forbidden)
    monkeypatch.setattr(evidence, "forecast_control", forbidden)
    monkeypatch.setattr(evidence, "build_models", forbidden)
    raw = evidence.canonical_json_bytes(fair_template)
    one = evidence.score_target(
        raw, Draw(date(2019, 5, 18), (1, 13, 14, 15, 16, 17), 2)
    )
    two = evidence.score_target(
        raw, Draw(date(2019, 5, 18), (1, 13, 14, 15, 16, 17), 49)
    )
    assert one["scores"] == two["scores"]
    assert one["scores"][0]["matched_final6"] == [1]
    assert one["scores"][0]["final6_hits"] == 1
    assert one["scores"][0]["joint_log_gain"].hex() == "0x0.0p+0"
    assert one["unique_opportunity_count"] == 1
    assert one["unique_final6"][0]["producer_model_names"] == list(evidence.MODEL_ORDER)
    assert one["unique_final6"][0]["primary_producer"] == evidence.CANDIDATE_MODEL_NAME


@pytest.mark.parametrize("kind", ["date", "bonus"])
def test_reveal_date_and_bonus_validation(fair_template, kind):
    actual = Draw(
        date(2020, 1, 4) if kind == "date" else date(2019, 5, 18),
        (1, 2, 3, 4, 5, 6),
        49,
    )
    if kind == "bonus":
        object.__setattr__(actual, "bonus", 6)
    with pytest.raises(ValueError):
        evidence.score_target(evidence.canonical_json_bytes(fair_template), actual)


def test_nonzero_joint_law_uses_own_effective_anchor(bindings, fair_template):
    history = [
        MainDraw(date(2019, 5, 15), (4, 11, 19, 27, 38, 49)),
        MainDraw(date(2019, 5, 18), (4, 11, 19, 27, 38, 49)),
    ]
    p = copy.deepcopy(fair_template)
    p["visible_prefix_draw_count"] = 2
    p["history_through"] = p["training_cutoff_date"] = "2019-05-18"
    p["target_draw_date"] = "2019-05-22"
    p["forecasts"][:2] = [
        evidence.serialize_overlap_forecast(
            forecast_candidate(history, date(2019, 5, 22))
        ),
        evidence.serialize_overlap_forecast(
            forecast_control(history, date(2019, 5, 22))
        ),
    ]
    _refresh(p)
    actual = Draw(date(2019, 5, 22), (1, 4, 11, 19, 27, 38), 49)
    scored = evidence.score_target(evidence.canonical_json_bytes(p), actual)
    states = [f["scientific_state"] for f in p["forecasts"][:2]]
    assert states[0]["training_overlap_sum"] != states[1]["training_overlap_sum"]
    assert states[0]["counts_sha256"] != states[1]["counts_sha256"]
    for state, score in zip(states, scored["scores"][:2], strict=True):
        anchor = (
            state["source_anchor"]
            if state["transformed_anchor"] is None
            else state["transformed_anchor"]
        )
        k = len(set(actual.numbers) & set(anchor))
        expected = (evidence.LOG_N + state["beta"] * float(k)) - state["log_z"]
        assert score["joint_log_gain"].hex() == expected.hex()


@pytest.mark.parametrize(
    "name,n,hits", [("n1_h6", 1, 6), ("n2_h12", 2, 12), ("n2_h8", 2, 8)]
)
def test_registered_exact_tail_literals(contract, name, n, hits):
    expected = contract["scientific_contract"]["literal_oracles"]["statistics"][
        "exact_tail"
    ][name]
    result = evidence.exact_top12_tail(n, hits)
    assert result["value"].hex() == expected["value_hex"]
    assert result["numerator_hex"] == expected["numerator_hex"]
    assert result["denominator_hex"] == expected["denominator_hex"]


@pytest.mark.parametrize(
    "name,values",
    [
        ("all_zero_3", [0, 0, 0]),
        ("paired_minus1_zero_plus1", [-1, 0, 1]),
        ("top12_lift_hits_0_to_6", [h - 72.0 / 49.0 for h in range(7)]),
    ],
)
def test_registered_bootstrap_literals_restart_seed(contract, name, values):
    expected = contract["scientific_contract"]["literal_oracles"]["statistics"][
        "bootstrap"
    ][name]
    first = evidence.bootstrap_interval(values)
    second = evidence.bootstrap_interval(values)
    assert first == second
    assert first["lower"].hex() == expected["lower_hex"]
    assert first["upper"].hex() == expected["upper_hex"]
    assert (
        first["resamples"] == 10000
        and first["seed"] == 649
        and first["method"] == "linear"
    )


def test_registered_holm_opportunity_and_fair_literals(contract):
    cases = contract["scientific_contract"]["literal_oracles"]["statistics"]
    for case in cases["holm"]:
        assert evidence.holm_adjusted((*evidence.PRIOR_FAMILY_P, case["p13"])) == tuple(
            case["adjusted_vector"]
        )
    opportunity = evidence.opportunity_summary(cases["opportunity"]["counts"])
    assert opportunity == {
        "unique_opportunity_count": 7,
        "nominal_fair_exact6_chance": float.fromhex(cases["opportunity"]["chance_hex"]),
    }
    brier, loss = evidence._proper_scores(
        {n: 6.0 / 49.0 for n in range(1, 50)}, {1, 2, 3, 4, 5, 6}
    )
    assert brier.hex() == cases["proper_fair"]["brier_hex"]
    assert loss.hex() == cases["proper_fair"]["log_loss_hex"]


@pytest.mark.parametrize(
    "function,args",
    [
        (evidence.exact_top12_tail, (True, 1)),
        (evidence.exact_top12_tail, (0, 0)),
        (evidence.exact_top12_tail, (1, 7)),
        (evidence.bootstrap_interval, ([],)),
        (evidence.bootstrap_interval, ([True],)),
        (evidence.bootstrap_interval, ([float("nan")],)),
        (evidence.holm_adjusted, ([True],)),
        (evidence.holm_adjusted, ([1.1],)),
        (evidence.opportunity_summary, ([0],)),
        (evidence.opportunity_summary, ([True],)),
        (evidence.opportunity_summary, ([5],)),
    ],
)
def test_invalid_math_inputs(function, args):
    with pytest.raises(ValueError):
        function(*args)


def _passing_scopes():
    models = {
        name: {
            "top12_lift": 0.1,
            "top6_lift": 0.1,
            "top12_exact_p": {"value": 0.5},
            "top12_lift_ci95": {"lower": -0.1, "upper": 0.1},
            "joint_log_gain_sum": 0.0,
        }
        for name in evidence.MODEL_ORDER
    }
    models[evidence.CANDIDATE_MODEL_NAME].update(
        {
            "top12_exact_p": {"value": 0.01},
            "top12_lift_ci95": {"lower": 0.1, "upper": 0.2},
            "joint_log_gain_sum": evidence.LOG_20,
        }
    )
    contrasts = {
        name: {
            "top12_paired_ci95": {"lower": 0.1, "upper": 0.2},
            "brier_delta": 1e-9,
            "log_loss_delta": 1e-9,
            "joint_log_gain_sum": 1.0,
        }
        for name in (
            "candidate_minus_v1",
            "candidate_minus_cyclic_control",
            "candidate_minus_fair",
        )
    }
    endpoints = {
        "aggregate": ("2020-01-01", "2025-12-31"),
        "first_half": ("2020-01-01", "2022-12-31"),
        "second_half": ("2023-01-04", "2025-12-31"),
    }
    return {
        scope: {
            "n": evidence.TARGET_IDENTITIES[scope][0],
            "target_dates_sha256": evidence.TARGET_IDENTITIES[scope][1],
            "first_target": endpoints[scope][0],
            "last_target": endpoints[scope][1],
            "models": copy.deepcopy(models),
            "contrasts": copy.deepcopy(contrasts),
        }
        for scope in evidence.SCOPE_ORDER
    }


def _gates(scopes, **kwargs):
    return evidence.evaluate_ten_gates(
        scopes,
        audit_complete=kwargs.get("audit_complete", True),
        audit_warnings=kwargs.get("audit_warnings", ()),
    )


def test_gate_all_ten_exact_registered_names():
    result = _gates(_passing_scopes())
    assert len(result) == 10 and all(g["passed"] for g in result)
    assert tuple(g["name"] for g in result) == evidence.GATE_NAMES


@pytest.mark.parametrize("scope", evidence.SCOPE_ORDER)
@pytest.mark.parametrize(
    "gate,group,name,field,value",
    [
        (1, "models", evidence.CANDIDATE_MODEL_NAME, "top12_lift", 0.0),
        (7, "models", evidence.CANDIDATE_MODEL_NAME, "top6_lift", 0.0),
        (
            8,
            "contrasts",
            "candidate_minus_v1",
            "brier_delta",
            math.nextafter(1e-9, math.inf),
        ),
        (
            8,
            "contrasts",
            "candidate_minus_v1",
            "log_loss_delta",
            math.nextafter(1e-9, math.inf),
        ),
        (
            8,
            "contrasts",
            "candidate_minus_fair",
            "brier_delta",
            math.nextafter(1e-9, math.inf),
        ),
        (
            8,
            "contrasts",
            "candidate_minus_fair",
            "log_loss_delta",
            math.nextafter(1e-9, math.inf),
        ),
        (9, "contrasts", "candidate_minus_cyclic_control", "joint_log_gain_sum", 0.0),
    ],
)
def test_each_scope_strict_and_inclusive_gate_boundaries(
    scope, gate, group, name, field, value
):
    scopes = _passing_scopes()
    scopes[scope][group][name][field] = value
    expected_gate = 4 if gate == 1 and scope != "aggregate" else gate
    assert not _gates(scopes)[expected_gate - 1]["passed"]


@pytest.mark.parametrize("scope", evidence.SCOPE_ORDER)
@pytest.mark.parametrize(
    "control", (evidence.CONTROL_MODEL_NAME, evidence.RANDOM_MODEL_NAME)
)
@pytest.mark.parametrize(
    "field,value",
    [
        ("p", 0.05),
        ("lower", math.nextafter(0.0, math.inf)),
        ("upper", math.nextafter(0.0, -math.inf)),
    ],
)
def test_every_control_conjunction_boundary(scope, control, field, value):
    scopes = _passing_scopes()
    model = scopes[scope]["models"][control]
    if field == "p":
        model["top12_exact_p"]["value"] = value
    else:
        model["top12_lift_ci95"][field] = value
    assert not _gates(scopes)[5]["passed"]
    assert _gates(scopes)[9][
        "passed"
    ]  # scientific nonpassing != invented audit warning


@pytest.mark.parametrize("scope", evidence.SCOPE_ORDER)
@pytest.mark.parametrize(
    "contrast,gate", [("candidate_minus_v1", 5), ("candidate_minus_cyclic_control", 6)]
)
def test_each_paired_lower_must_be_strict(scope, contrast, gate):
    scopes = _passing_scopes()
    scopes[scope]["contrasts"][contrast]["top12_paired_ci95"]["lower"] = 0.0
    assert not _gates(scopes)[gate - 1]["passed"]


def test_remaining_gate_thresholds_and_audit():
    scopes = _passing_scopes()
    scopes["aggregate"]["models"][evidence.CANDIDATE_MODEL_NAME]["top12_exact_p"][
        "value"
    ] = math.nextafter(0.01, math.inf)
    assert not _gates(scopes)[1]["passed"]
    scopes = _passing_scopes()
    scopes["aggregate"]["models"][evidence.CANDIDATE_MODEL_NAME]["top12_lift_ci95"][
        "lower"
    ] = 0.0
    assert not _gates(scopes)[2]["passed"]
    for scope in evidence.SCOPE_ORDER:
        scopes = _passing_scopes()
        scopes[scope]["models"][evidence.CANDIDATE_MODEL_NAME]["joint_log_gain_sum"] = (
            math.nextafter(evidence.LOG_20, -math.inf) if scope == "aggregate" else 0.0
        )
        assert not _gates(scopes)[8]["passed"]
    scopes = _passing_scopes()
    scopes["aggregate"]["models"][evidence.CONTROL_MODEL_NAME]["joint_log_gain_sum"] = (
        evidence.LOG_20
    )
    assert not _gates(scopes)[8]["passed"]
    assert not _gates(_passing_scopes(), audit_complete=False)[9]["passed"]
    assert not _gates(_passing_scopes(), audit_warnings=["io_failure"])[9]["passed"]
    with pytest.raises(ValueError):
        _gates(_passing_scopes(), audit_complete=1)
    with pytest.raises(ValueError):
        _gates(_passing_scopes(), audit_warnings="warning")
    scopes = _passing_scopes()
    del scopes["second_half"]
    with pytest.raises(ValueError):
        _gates(scopes)


def test_partial_reports_never_infer_and_retain_all_descriptions(
    fair_template, bindings, monkeypatch
):
    rows = _scored_rows(fair_template, 2)

    def forbidden(*args, **kwargs):
        raise AssertionError("partial inference forbidden")

    monkeypatch.setattr(evidence, "exact_top12_tail", forbidden)
    monkeypatch.setattr(evidence, "bootstrap_interval", forbidden)
    monkeypatch.setattr(evidence, "holm_adjusted", forbidden)
    monkeypatch.setattr(evidence, "evaluate_ten_gates", forbidden)
    report = evidence.build_report(
        rows,
        bindings,
        audit_complete=True,
        stop_reason="Archive_after_claim_failure_no_retry",
    )
    assert report["disposition"] == "Archive"
    assert (
        report["scopes"] == {}
        and report["gates"] is None
        and report["multiplicity"] is None
    )
    assert set(report["annual_descriptive_only"]) == {
        str(year) for year in range(2020, 2026)
    }
    for model in report["partial_descriptive"].values():
        assert set(model["final6_histogram"]) == set("0123456")
        assert len(model["calibration_bins"]) == 10
        assert sum(b["count"] for b in model["calibration_bins"]) == 98
        assert sum(
            b["count"] * (b["observed_frequency"] or 0.0)
            for b in model["calibration_bins"]
        ) == pytest.approx(12.0)
        assert "top12_exact_p" not in model and "top12_lift_ci95" not in model
    for best in report["best_final6_by_model"].values():
        assert best["target_dates"] == [r["target_draw_date"] for r in rows]
    text = evidence.render_markdown(report)
    assert "v13_post_rng_main_set_overlap_v13.0.0_historical.json" in text
    assert text.endswith("\n") and not text.endswith("\n\n") and "\r" not in text
    for row in rows:
        assert row["target_draw_date"] in text
        assert evidence.canonical_json_bytes(row).decode().strip() in text
    assert "不是新增的独立机会" in text
    with pytest.raises(ValueError):
        evidence.summarize_scope(rows)


def test_capture_stop_and_unscored_never_claim_complete(fair_template, bindings):
    captured = _scored_rows(fair_template, 1, actual=(1, 2, 3, 4, 5, 6))
    report = evidence.build_report(
        captured,
        bindings,
        audit_complete=True,
        stop_reason="exact_final6_pending_independent_audit",
    )
    assert report["disposition"] == "pending_audit"
    assert not report["complete_registered_scope"] and report["gates"] is None
    assert report["audit"]["independent_leakage_audit"] == "pending"
    report = evidence.build_report(
        [],
        bindings,
        audit_complete=False,
        stop_reason="Archive_after_claim_failure_no_retry",
    )
    assert (
        report["disposition"] == "startup_failed_unscored" and report["gates"] is None
    )
    continued = _scored_rows(fair_template, 2, actual=(1, 2, 3, 4, 5, 6))
    with pytest.raises(ValueError):
        evidence.build_report(continued, bindings, audit_complete=True)


@pytest.mark.parametrize(
    "mutation",
    [
        "score",
        "score_bool",
        "unknown",
        "missing",
        "forecast_hash",
        "pred_sequence",
        "score_sequence",
        "pred_hash",
        "cumulative",
        "generated",
        "bindings",
        "gap",
    ],
)
def test_report_rejects_score_or_chronology_tampering(
    fair_template, bindings, mutation
):
    rows = _scored_rows(fair_template, 2)
    if mutation == "score":
        rows[0]["scores"][0]["top12_hits"] += 1
    elif mutation == "score_bool":
        rows[0]["scores"][0]["top12_hits"] = False
    elif mutation == "unknown":
        rows[0]["extra"] = 1
    elif mutation == "missing":
        del rows[0]["scored_event_sha256"]
    elif mutation == "forecast_hash":
        rows[0]["forecast_payload_sha256"] = "e" * 64
    elif mutation == "pred_sequence":
        rows[1]["prediction_frozen_event_sequence"] = 1
    elif mutation == "score_sequence":
        rows[0]["scored_event_sequence"] = 0
    elif mutation == "pred_hash":
        rows[0]["prediction_frozen_event_sha256"] = "bad"
    elif mutation == "cumulative":
        rows[1]["cumulative_opportunities"]["unique_opportunity_count"] = 1
    elif mutation == "generated":
        rows[1]["prediction_generated_at"] = "2026-09-12T00:00:00Z"
    elif mutation == "bindings":
        rows[1]["forecast_payload"]["bindings"]["extra"] = 1
    elif mutation == "gap":
        rows = rows[1:]
    with pytest.raises(ValueError):
        evidence.build_report(rows, bindings, audit_complete=True)


def test_full_fixed_synthetic_horizon_has_all_scopes_and_five_family(
    fair_template, bindings
):
    # Numbers are invented constant fixtures; only the published calendar is used.
    rows = _scored_rows(fair_template, 627)
    report = evidence.build_report(rows, bindings, audit_complete=True)
    assert report["complete_registered_scope"] and report["disposition"] == "Reject"
    assert [report["scopes"][s]["n"] for s in evidence.SCOPE_ORDER] == [627, 314, 313]
    assert report["multiplicity"]["input_vector"][:4] == list(evidence.PRIOR_FAMILY_P)
    assert report["multiplicity"]["candidate_zero_based_index"] == 4
    assert report["multiplicity"]["variant_index"] == 5
    assert report["multiplicity"]["ordered_variants"] == [
        "V2",
        "V3",
        "V11",
        "V12",
        "V13",
    ]
    for scope in report["scopes"].values():
        assert set(scope["models"]) == set(evidence.MODEL_ORDER)
        assert set(scope["contrasts"]) == {
            "candidate_minus_v1",
            "candidate_minus_cyclic_control",
            "candidate_minus_fair",
        }
    assert len(report["targets"]) == 627
    with pytest.raises(ValueError):
        evidence.summarize_scope(rows[:314])
    text = evidence.render_markdown(report)
    assert "0.000000" in text and "95% lift CI" in text
    assert all(iso in text for iso in evidence._registered_dates())


@pytest.fixture(scope="module")
def frozen_config(contract):
    import lotto649

    root = Path(lotto649.__file__).resolve().parents[2]
    raw = (root / "config.yaml").read_bytes()
    pin = next(
        item
        for item in contract["scientific_contract"]["comparators"][
            "frozen_source_manifest"
        ]
        if item["path"] == "config.yaml"
    )
    assert hashlib.sha256(raw).hexdigest() == pin["sha256"]
    return yaml.safe_load(raw)


def test_fresh_four_producer_graph_and_main_only_projection(frozen_config, monkeypatch):
    import numpy as np

    from lotto649.models import factory
    from lotto649.models.base import normalize_expected_six
    from lotto649.models.logistic import LogisticNumberModel

    graphs, projected, member_calls, fit_calls = [], [], [], []
    original_build = evidence.build_models
    original_candidate = evidence.forecast_candidate
    original_fit = factory.LogisticNumberModel.predict

    def build(config, requested):
        assert requested == ["ensemble", "random"]
        result = original_build(config, requested)
        graphs.append(result)
        return result

    def projected_candidate(prefix, target):
        assert all(
            type(row) is MainDraw
            and not hasattr(row, "bonus")
            and row.draw_date < target
            for row in prefix
        )
        projected.append(tuple(prefix))
        return original_candidate(prefix, target)

    def logistic(self, history, target):
        assert all(row.draw_date < target for row in history)
        fit_calls.append((self, target, len(history)))
        return original_fit(self, history, target)

    def inactive(*args, **kwargs):
        raise AssertionError("inactive V2/V3/V4 execution")

    monkeypatch.setattr(evidence, "build_models", build)
    monkeypatch.setattr(evidence, "forecast_candidate", projected_candidate)
    monkeypatch.setattr(LogisticNumberModel, "predict", logistic)
    for model in (
        factory.V2StatisticalModel,
        factory.V3BoostingModel,
        factory.V4EnsembleModel,
    ):
        monkeypatch.setattr(model, "predict", inactive)
        if hasattr(model, "fit"):
            monkeypatch.setattr(model, "fit", inactive)
    for model in (
        factory.LongFrequencyModel,
        factory.RecentFrequencyModel,
        factory.EmaGapModel,
    ):
        original = model.predict

        def wrapper(self, history, target, original=original):
            member_calls.append((type(self).__name__, target))
            assert history and all(row.draw_date < target for row in history)
            return original(self, history, target)

        monkeypatch.setattr(model, "predict", wrapper)
    history = []
    current = date(2016, 1, 2)
    last_forecasts = None
    for target in (date(2019, 5, 18), date(2019, 5, 22)):
        while current < target:
            numbers = (
                (1, 3, 5, 7, 9, 11)
                if len(history) % 2 == 0
                else (25, 27, 29, 31, 33, 35)
            )
            history.append(Draw(current, numbers, 49))
            current += timedelta(days=3 if current.weekday() == 2 else 4)
        last_forecasts = evidence.four_forecasts(history, target, frozen_config)
        assert [f["model_name"] for f in last_forecasts] == list(evidence.MODEL_ORDER)
        jitter = np.random.default_rng(649_000_000 + target.toordinal()).uniform(
            -1e-9, 1e-9, size=49
        )
        expected = normalize_expected_six(
            {n: 6.0 / 49.0 + float(jitter[n - 1]) for n in range(1, 50)}
        )
        assert last_forecasts[-1]["probabilities"] == {
            str(n): p for n, p in expected.items()
        }
        assert last_forecasts[-1]["final6"] == evidence.select_combination(expected, 12)
    assert graphs[0]["ensemble"] is not graphs[1]["ensemble"]
    assert graphs[0]["random"] is not graphs[1]["random"]
    assert len(projected) == 2 and all(len(prefix) > 300 for prefix in projected)
    assert len(member_calls) == 6 and len(fit_calls) == 2
    assert fit_calls[0][0] is not fit_calls[1][0]
    assert last_forecasts[0]["scientific_state"]["training_pair_count"] == 1


def test_config_change_and_bad_prefix_fail_before_model_execution(
    frozen_config, monkeypatch
):
    def forbidden(*args, **kwargs):
        raise AssertionError("invalid input reached a producer")

    monkeypatch.setattr(evidence, "build_models", forbidden)
    config = copy.deepcopy(frozen_config)
    config["features"]["ema_half_life"] += 1
    with pytest.raises(ValueError):
        evidence.four_forecasts(
            [Draw(date(2019, 5, 15), (1, 2, 3, 4, 5, 6), 49)], date(2019, 5, 18), config
        )
    with pytest.raises(ValueError):
        evidence.four_forecasts(
            [Draw(date(2019, 5, 18), (1, 2, 3, 4, 5, 6), 49)],
            date(2019, 5, 18),
            frozen_config,
        )
    with pytest.raises(ValueError):
        evidence.four_forecasts([], date(2019, 5, 18), frozen_config)


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_model",
        "missing_contrast",
        "missing_ci",
        "bool_metric",
        "nan_metric",
        "unknown_warning",
        "unknown_stop",
    ],
)
def test_closed_gate_and_failure_inputs(fair_template, bindings, mutation):
    scopes = _passing_scopes()
    if mutation == "missing_model":
        del scopes["first_half"]["models"][evidence.RANDOM_MODEL_NAME]
    elif mutation == "missing_contrast":
        del scopes["second_half"]["contrasts"]["candidate_minus_v1"]
    elif mutation == "missing_ci":
        del scopes["aggregate"]["models"][evidence.CANDIDATE_MODEL_NAME][
            "top12_lift_ci95"
        ]
    elif mutation == "bool_metric":
        scopes["aggregate"]["models"][evidence.CANDIDATE_MODEL_NAME]["top12_lift"] = (
            True
        )
    elif mutation == "nan_metric":
        scopes["aggregate"]["models"][evidence.CANDIDATE_MODEL_NAME]["top12_lift"] = (
            float("nan")
        )
    if mutation == "unknown_warning":
        with pytest.raises(ValueError):
            _gates(scopes, audit_warnings=["arbitrary exception text"])
    elif mutation == "unknown_stop":
        with pytest.raises(ValueError):
            evidence.build_report(
                [],
                bindings,
                audit_complete=False,
                stop_reason="arbitrary exception text",
            )
    else:
        with pytest.raises(ValueError):
            _gates(scopes)


def test_source_date_count_and_trailing_calendar_tampering(fair_template):
    for mutation in ("count_date", "skip_next", "unscheduled", "known2026"):
        payload = copy.deepcopy(fair_template)
        if mutation == "count_date":
            for f in payload["forecasts"][:2]:
                f["scientific_state"]["source_draw_date"] = "2019-05-18"
            payload["history_through"] = payload["training_cutoff_date"] = "2019-05-18"
            payload["target_draw_date"] = "2019-05-22"
        elif mutation == "skip_next":
            payload["target_draw_date"] = "2019-05-22"
        elif mutation == "unscheduled":
            payload["target_draw_date"] = "2019-05-19"
        else:
            payload["target_draw_date"] = "2026-01-03"
        _refresh(payload)
        with pytest.raises(ValueError):
            evidence.validate_frozen_payload(evidence.canonical_json_bytes(payload))


def test_descriptive_calibration_boundary_membership(fair_template):
    mapping = {str(n): 0.1 if n == 1 else 0.2 if n == 2 else 0.3 for n in range(1, 50)}
    row = {
        "actual": [1, 3, 5, 7, 9, 11],
        "forecast_payload": {"forecasts": [{"probabilities": mapping}]},
    }
    bins = evidence._calibration([row], 0)
    assert bins[0]["count"] == 0 and bins[0]["mean_probability"] is None
    assert bins[1]["count"] == 1 and bins[1]["observed_frequency"] == 1.0
    assert bins[2]["count"] == 1 and bins[2]["observed_frequency"] == 0.0
    assert bins[3]["count"] == 47 and bins[3]["observed_frequency"] == 5.0 / 47.0


def test_exact_tail_conserves_mass_and_inclusive_endpoints():
    for n in (1, 2, 7):
        coefficients = evidence._exact_top12_coefficients(n)
        assert sum(coefficients) == 13983816**n
        assert evidence.exact_top12_tail(n, 0)["value"] == 1.0
        assert int(evidence.exact_top12_tail(n, 6 * n)["numerator_hex"], 16) == 924**n
        total = n * 2
        upper = int(evidence.exact_top12_tail(n, total)["numerator_hex"], 16)
        strict = int(evidence.exact_top12_tail(n, total + 1)["numerator_hex"], 16)
        assert upper - strict == coefficients[total]


def test_statistical_paired_arithmetic_uses_aligned_differences_first():
    # Pure score arrays with cancellation test the declared aggregation order;
    # they are not model predictions, history, or an eligible report scope.
    rows = []
    for left, right in zip([1e16, 1.0, -1e16], [1e16, 0.0, -1e16], strict=True):
        scores = []
        for index, name in enumerate(evidence.MODEL_ORDER):
            scores.append(
                {
                    "model_name": name,
                    "top6_hits": 0,
                    "top12_hits": 0,
                    "top18_hits": 0,
                    "final6_hits": 0,
                    "mean_actual_rank": 25.0,
                    "brier_score": left if index == 0 else right,
                    "log_loss": left if index == 0 else right,
                    "joint_log_gain": left
                    if index == 0
                    else right
                    if index == 1
                    else None,
                }
            )
        rows.append(
            {
                "target_draw_date": f"2000-01-0{len(rows) + 1}",
                "actual": [1, 2, 3, 4, 5, 6],
                "scores": scores,
                "fair_scores": {"brier_score": right, "log_loss": right},
                "forecast_payload": {
                    "forecasts": [
                        {"probabilities": {str(n): 6.0 / 49.0 for n in range(1, 50)}}
                        for _ in evidence.MODEL_ORDER
                    ]
                },
            }
        )
    summary = evidence._scope_summary(rows)
    assert summary["contrasts"]["candidate_minus_v1"]["brier_delta"] == 1.0 / 3.0
    assert (
        summary["contrasts"]["candidate_minus_cyclic_control"]["joint_log_gain_sum"]
        == 1.0
    )
    assert summary["contrasts"]["candidate_minus_fair"]["log_loss_delta"] == 1.0 / 3.0


def test_synthetic_identity_never_masquerades_as_historical(fair_template, bindings):
    payload = copy.deepcopy(fair_template)
    payload["classification"] = evidence.CLASSIFICATION
    with pytest.raises(ValueError):
        evidence.validate_frozen_payload(evidence.canonical_json_bytes(payload))
    payload = copy.deepcopy(fair_template)
    del payload["bindings"]["synthetic_only"]
    with pytest.raises(ValueError):
        evidence.validate_frozen_payload(evidence.canonical_json_bytes(payload))
    rows = _scored_rows(fair_template, 1)
    report = evidence.build_report(
        rows,
        bindings,
        audit_complete=True,
        stop_reason="Archive_after_claim_failure_no_retry",
    )
    assert report["classification"] == "synthetic_fixture_only"
    assert "仅合成夹具测试" in evidence.render_markdown(report)
    report = evidence.build_report([], bindings, audit_complete=False)
    assert report["classification"] == "synthetic_fixture_only"
