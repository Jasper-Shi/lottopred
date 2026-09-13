"""R3 evidence equivalence on invented rows, closed oracles, and sealed source.

No history reader, registered attempt, runtime verifier, worker, SMTP sender,
network service, or real artifact path is invoked. Calendar dates are public
registered identities; every main-number set below is an invented fixture.
"""

from __future__ import annotations

import ast
import hashlib
import json
import math
from copy import deepcopy
from datetime import date, timedelta
from fractions import Fraction
from itertools import product
from pathlib import Path

import numpy as np
import pytest

from lotto649 import v12_0_1_evidence as old
from lotto649 import v12_0_2_evidence as new
from lotto649.domain import Draw
from lotto649.models import v12_parity_transition as core

ROOT = Path(__file__).resolve().parents[1]
CORE_SHA256 = "fae93e0a6f76c6604eabe24f6b93676e22e87d7e567365b382484433fba2eb77"
OLD_EVIDENCE_SHA256 = "495c3907ac9181ea8f0fc2bf4f285ff09aa992e4c7d10094adeb281e8adc70ae"
FINGERPRINT = "af2e16a55ff0e817cf71208471e19e4f481bed63990f7e41268997c4c4b35c76"
IDENTITY_REPLACEMENTS = (
    (
        "Pure serialization and inference for the frozen V12.0.1 diagnostic.",
        "Pure serialization and inference for the frozen V12.0.2 diagnostic.",
    ),
    ('MODEL_VERSION = "v12.0.1"', 'MODEL_VERSION = "v12.0.2"'),
    (
        'EXPERIMENT_ID = "V12_0_1_post_rng_parity_composition_transition_operational_rebinding"',
        'EXPERIMENT_ID = "V12_0_2_historical_operational_rebinding"',
    ),
    (
        "lotto649.v12.0.1.historical-diagnostic-report.v1",
        "lotto649.v12.0.2.historical-diagnostic-report.v1",
    ),
    ("# V12.0.1 历史严格回测诊断", "# V12.0.2 历史严格回测诊断"),
)
SYNTHETIC_TARGET = date(2032, 2, 4)
SYNTHETIC_BINDINGS = {"synthetic_fixture_only": True, "audit_token": "合成|only"}
V1_CONFIG = {
    "project": {"seed": 649, "model_version": "v1.0.0"},
    "prediction": {"candidate_pool_size": 12},
    "features": {"logistic_training_draws": 480, "min_logistic_samples": 300},
}


def _digest(value):
    return hashlib.sha256(old.canonical_json_bytes(value)).hexdigest()


def _prefix(*, tilted):
    return tuple(
        Draw(SYNTHETIC_TARGET - timedelta(days=10 - i), (1, 3, 5, 7, 9, 11))
        for i in range(2 if tilted else 1)
    )


def _payload(module, *, tilted=False, target=SYNTHETIC_TARGET):
    # A fixed synthetic prefix, independent of any registered target answer.
    prefix = tuple(
        Draw(target - timedelta(days=10 - i), draw.numbers)
        for i, draw in enumerate(_prefix(tilted=tilted))
    )
    fair = {label: 6.0 / 49.0 for label in range(1, 50)}
    return {
        "classification": "synthetic_fixture_only",
        "target_draw_date": target.isoformat(),
        "history_through": prefix[-1].draw_date.isoformat(),
        "forecasts": [
            module.serialize_parity_forecast(core.forecast_candidate(prefix, target)),
            module.serialize_parity_forecast(core.forecast_control(prefix, target)),
            module.serialize_comparator_forecast("ensemble_v1.0.0", fair),
            module.serialize_comparator_forecast("random_v1.0.0", fair),
        ],
    }


def _rebind_row(row):
    """Expected metadata changes only, with every affected digest recomputed.

    Never drop a digest or normalize a number/rank/score/state. Only the two
    H12 producers change model_version; V1 and random identities remain exact.
    """
    result = deepcopy(row)
    forecasts = result["forecast_payload"]["forecasts"]
    for forecast in forecasts[:2]:
        assert forecast["model_version"] == "v12.0.1"
        forecast["model_version"] = "v12.0.2"
    digest_by_name = {
        forecast["model_name"]: _digest(forecast) for forecast in forecasts
    }
    result["forecast_payload_sha256"] = _digest(result["forecast_payload"])
    for index, score in enumerate(result["scores"]):
        if index < 2:
            assert score["model_version"] == "v12.0.1"
            score["model_version"] = "v12.0.2"
        score["forecast_sha256"] = digest_by_name[score["model_name"]]
    for collection in ("unique_final6", "exact_final6_opportunities"):
        for item in result[collection]:
            item["forecast_sha256_by_producer"] = {
                name: digest_by_name[name] for name in item["producer_model_names"]
            }
    return result


def _rows(module, count=3, *, exact_first=False, registered=False):
    dates = (
        tuple(date.fromisoformat(value) for value in old._registered_dates())
        if registered
        else tuple(SYNTHETIC_TARGET + timedelta(days=i) for i in range(count))
    )
    result = []
    for index, target in enumerate(dates[:count]):
        payload = _payload(module, tilted=not registered, target=target)
        numbers = (
            (1, 2, 3, 4, 5, 6)
            if exact_first and index == 0
            else (40, 42, 44, 46, 48, 49)
            if registered
            else (
                (13, 15, 17, 19, 21, 23),
                (2, 4, 6, 8, 10, 12),
                (1, 14, 15, 28, 29, 42),
            )[index % 3]
        )
        result.append(
            module.score_target(
                module.canonical_json_bytes(payload), Draw(target, numbers)
            )
        )
    return result


def _rebind_report(report):
    result = deepcopy(report)
    assert (
        result["schema_version"] == "lotto649.v12.0.1.historical-diagnostic-report.v1"
    )
    assert result["experiment_id"] == old.EXPERIMENT_ID
    assert result["model_version"] == "v12.0.1"
    result["schema_version"] = "lotto649.v12.0.2.historical-diagnostic-report.v1"
    result["experiment_id"] = "V12_0_2_historical_operational_rebinding"
    result["model_version"] = "v12.0.2"
    result["targets"] = [_rebind_row(row) for row in report["targets"]]
    return result


def test_sealed_source_has_exactly_five_identity_changes_and_identical_ast():
    source = (ROOT / "src/lotto649/v12_0_1_evidence.py").read_bytes()
    assert hashlib.sha256(source).hexdigest() == OLD_EVIDENCE_SHA256
    assert (
        hashlib.sha256(
            (ROOT / "src/lotto649/models/v12_parity_transition.py").read_bytes()
        ).hexdigest()
        == CORE_SHA256
    )
    expected = source
    for before, after in IDENTITY_REPLACEMENTS:
        assert expected.count(before.encode()) == 1
        expected = expected.replace(before.encode(), after.encode())
    actual = (ROOT / "src/lotto649/v12_0_2_evidence.py").read_bytes()
    assert actual == expected
    assert ast.dump(ast.parse(actual)) == ast.dump(ast.parse(expected))
    seal = json.loads(
        (
            ROOT
            / "evidence/research_registrations/v12-post-rng-parity-composition-transition-v3.json"
        ).read_bytes()
    )
    assert seal["statistical_equivalence"]["fingerprint_sha256"] == FINGERPRINT
    assert (
        seal["legacy_byte_preservation"]["manifest"][
            "src/lotto649/v12_0_1_evidence.py"
        ]["sha256"]
        == OLD_EVIDENCE_SHA256
    )
    assert new.MODEL_ORDER == old.MODEL_ORDER
    assert new.GATE_NAMES == old.GATE_NAMES
    assert new.TARGET_IDENTITIES == old.TARGET_IDENTITIES


@pytest.mark.parametrize("tilted", [False, True])
def test_four_forecasts_keep_each_probability_rank_feature_and_scientific_state(tilted):
    prefix = _prefix(tilted=tilted)
    left = old.four_forecasts(prefix, SYNTHETIC_TARGET, deepcopy(V1_CONFIG))
    right = new.four_forecasts(prefix, SYNTHETIC_TARGET, deepcopy(V1_CONFIG))
    for index, (before, after) in enumerate(zip(left, right, strict=True)):
        expected = deepcopy(before)
        if index < 2:
            expected["model_version"] = "v12.0.2"
        assert after == expected
        assert len(after["probabilities"]) == len(after["ranking"]) == 49
        assert set(after["ranking"]) == set(range(1, 50))
        assert after["ranking"] == sorted(
            range(1, 50), key=lambda label: (-after["probabilities"][str(label)], label)
        )
        assert math.fsum(after["probabilities"].values()) == pytest.approx(6, abs=1e-12)
        assert [len(after[f"top{k}"]) for k in (6, 12, 18)] == [6, 12, 18]


@pytest.mark.parametrize("tilted", [False, True])
@pytest.mark.parametrize("actual", [(1, 2, 3, 4, 5, 6), (13, 15, 17, 19, 21, 23)])
def test_frozen_score_and_opportunity_identity_changes_are_explicit(tilted, actual):
    before_payload = _payload(old, tilted=tilted)
    after_payload = _payload(new, tilted=tilted)
    before_bytes = old.canonical_json_bytes(before_payload)
    after_bytes = new.canonical_json_bytes(after_payload)
    assert old.validate_frozen_payload(before_bytes) is None
    assert new.validate_frozen_payload(after_bytes) is None
    revealed = Draw(SYNTHETIC_TARGET, actual, 49)
    before = old.score_target(before_bytes, revealed)
    after = new.score_target(after_bytes, revealed)
    assert after == _rebind_row(before)
    assert after["forecast_payload_sha256"] != before["forecast_payload_sha256"]
    for index, score in enumerate(after["scores"]):
        forecast = after_payload["forecasts"][index]
        probabilities = forecast["probabilities"]
        expected_brier = (
            math.fsum(
                (probabilities[str(label)] - int(label in actual)) ** 2
                for label in range(1, 50)
            )
            / 49
        )
        expected_loss = (
            -math.fsum(
                math.log(probabilities[str(label)])
                if label in actual
                else math.log1p(-probabilities[str(label)])
                for label in range(1, 50)
            )
            / 49
        )
        assert score["brier_score"] == expected_brier
        assert score["log_loss"] == expected_loss
        assert score["final6_hits"] == len(set(actual) & set(forecast["final6"]))
        assert (
            score["mean_actual_rank"]
            == math.fsum(forecast["ranking"].index(label) + 1 for label in actual) / 6
        )
        for k in (6, 12, 18):
            assert score[f"top{k}_hits"] == len(set(actual) & set(forecast[f"top{k}"]))
        if index >= 2:
            assert (
                score["forecast_sha256"] == before["scores"][index]["forecast_sha256"]
            )
    assert after["unique_opportunity_count"] == len(
        {tuple(forecast["final6"]) for forecast in after_payload["forecasts"]}
    )


def test_scope_metrics_calibration_contrasts_and_fixed_resamples_match_exactly():
    before_rows, after_rows = _rows(old), _rows(new)
    assert after_rows == [_rebind_row(row) for row in before_rows]
    before, after = old.summarize_scope(before_rows), new.summarize_scope(after_rows)
    assert after == before
    for index, model_name in enumerate(new.MODEL_ORDER):
        summary = after["models"][model_name]
        bins = summary["calibration_bins"]
        assert len(bins) == 10
        assert sum(item["count"] for item in bins) == 49 * len(after_rows)
        for bin_index, actual_bin in enumerate(bins):
            samples = [
                (
                    row["forecast_payload"]["forecasts"][index]["probabilities"][
                        str(label)
                    ],
                    int(label in row["actual"]),
                )
                for row in after_rows
                for label in range(1, 50)
                if bin_index / 10
                <= row["forecast_payload"]["forecasts"][index]["probabilities"][
                    str(label)
                ]
                < (bin_index + 1) / 10
            ]
            assert actual_bin["count"] == len(samples)
            assert actual_bin["mean_probability"] == (
                math.fsum(p for p, _ in samples) / len(samples) if samples else None
            )
            assert actual_bin["observed_frequency"] == (
                math.fsum(y for _, y in samples) / len(samples) if samples else None
            )
        assert summary["final6_histogram"] == {
            str(hits): sum(
                row["scores"][index]["final6_hits"] == hits for row in after_rows
            )
            for hits in range(7)
        }
    for contrast, other in (("candidate_minus_v1", 2), ("candidate_minus_pseudo", 1)):
        differences = [
            row["scores"][0]["top12_hits"] - row["scores"][other]["top12_hits"]
            for row in after_rows
        ]
        assert after["contrasts"][contrast][
            "top12_paired_ci95"
        ] == new.bootstrap_interval(differences)


@pytest.mark.parametrize("n", [1, 2, 3])
def test_exact_top12_integer_tails_match_finite_closed_sample_space(n):
    weights = [math.comb(12, hits) * math.comb(37, 6 - hits) for hits in range(7)]
    sample_space = list(product(range(7), repeat=n))
    denominator = math.comb(49, 6) ** n
    for threshold in range(6 * n + 1):
        numerator = sum(
            math.prod(weights[hits] for hits in outcome)
            for outcome in sample_space
            if sum(outcome) >= threshold
        )
        expected = {
            "value": numerator / denominator,
            "numerator_hex": hex(numerator),
            "denominator_hex": hex(denominator),
        }
        assert (
            new.exact_top12_tail(n, threshold)
            == old.exact_top12_tail(n, threshold)
            == expected
        )


@pytest.mark.parametrize("values", [(1.0,), (-1.5, 0.0, 2.25, 4.0), (0, 0, 0)])
def test_bootstrap_matches_independent_seeded_complete_row_oracle(values):
    indices = np.random.default_rng(649).integers(
        0, len(values), size=(10_000, len(values))
    )
    means = [
        math.fsum(values[index] for index in sample) / len(values) for sample in indices
    ]
    lower, upper = np.quantile(means, [0.025, 0.975], method="linear")
    expected = {
        "lower": float(lower),
        "upper": float(upper),
        "seed": 649,
        "resamples": 10_000,
        "method": "linear",
    }
    assert new.bootstrap_interval(values) == old.bootstrap_interval(values) == expected
    new.bootstrap_interval((500.0, 800.0))
    assert new.bootstrap_interval(values) == expected


@pytest.mark.parametrize("counts", [(), (1,), (1, 2, 3, 4), (4, 4, 4)])
def test_opportunity_probability_is_same_union_of_per_draw_unique_sets(counts):
    expected = 1 - math.prod(
        Fraction(math.comb(49, 6) - count, math.comb(49, 6)) for count in counts
    )
    before, after = old.opportunity_summary(counts), new.opportunity_summary(counts)
    assert after == before
    assert after["cumulative_unique_opportunity_count"] == sum(counts)
    assert after["cumulative_fair_probability"] == pytest.approx(
        float(expected), rel=2e-15
    )


@pytest.mark.parametrize(
    "values,expected",
    [
        ((1.0, 1.0, 0.9783404732169021, 0.0125), (1.0, 1.0, 1.0, 0.05)),
        ((0.01, 0.04, 0.03), (0.03, 0.06, 0.06)),
        ((0.1, 0.1), (0.2, 0.2)),
    ],
)
def test_holm_preserves_family_size_ties_and_inclusive_threshold(values, expected):
    assert new.holm_adjusted(values) == old.holm_adjusted(values) == expected


def _passing_scopes():
    scopes = {}
    for scope in new.SCOPE_ORDER:
        control = {
            "top12_exact_p": {"value": math.nextafter(0.05, math.inf)},
            "top12_lift_ci95": {"lower": 0.0, "upper": 0.0},
            "joint_log_gain_sum": 0.0,
        }
        scopes[scope] = {
            "models": {
                core.CANDIDATE_MODEL_NAME: {
                    "top12_lift": 0.1,
                    "top6_lift": 0.1,
                    "top12_exact_p": {"value": 0.0125},
                    "top12_lift_ci95": {"lower": 0.01, "upper": 0.2},
                    "joint_log_gain_sum": math.log(20) if scope == "aggregate" else 1.0,
                },
                core.CONTROL_MODEL_NAME: deepcopy(control),
                new.RANDOM_MODEL_NAME: deepcopy(control),
                new.ENSEMBLE_MODEL_NAME: {},
            },
            "contrasts": {
                "candidate_minus_v1": {
                    "top12_paired_ci95": {"lower": 0.01, "upper": 0.2},
                    "brier_delta": 1e-9,
                    "log_loss_delta": 1e-9,
                },
                "candidate_minus_pseudo": {
                    "top12_paired_ci95": {"lower": 0.01, "upper": 0.2},
                    "joint_log_gain_sum": 1.0,
                },
                "candidate_minus_fair": {"brier_delta": 1e-9, "log_loss_delta": 1e-9},
            },
        }
    return scopes


@pytest.mark.parametrize("gate", range(1, 11))
def test_each_gate_retains_same_inclusive_or_strict_rejection_boundary(gate):
    scopes = _passing_scopes()
    assert all(
        item["passed"]
        for item in new.evaluate_ten_gates(
            scopes, audit_complete=True, audit_warnings=()
        )
    )
    candidate = scopes["aggregate"]["models"][core.CANDIDATE_MODEL_NAME]
    warnings = ()
    if gate == 1:
        candidate["top12_lift"] = 0.0
    elif gate == 2:
        candidate["top12_exact_p"]["value"] = math.nextafter(0.0125, math.inf)
    elif gate == 3:
        candidate["top12_lift_ci95"]["lower"] = 0.0
    elif gate == 4:
        scopes["first_half"]["models"][core.CANDIDATE_MODEL_NAME]["top12_lift"] = 0.0
    elif gate == 5:
        scopes["second_half"]["contrasts"]["candidate_minus_v1"]["top12_paired_ci95"][
            "lower"
        ] = 0.0
    elif gate == 6:
        scopes["first_half"]["models"][core.CONTROL_MODEL_NAME]["top12_exact_p"][
            "value"
        ] = 0.05
    elif gate == 7:
        scopes["second_half"]["models"][core.CANDIDATE_MODEL_NAME]["top6_lift"] = 0.0
    elif gate == 8:
        scopes["first_half"]["contrasts"]["candidate_minus_fair"]["brier_delta"] = (
            math.nextafter(1e-9, math.inf)
        )
    elif gate == 9:
        candidate["joint_log_gain_sum"] = math.nextafter(math.log(20), -math.inf)
    else:
        warnings = ("synthetic_default_notification_failed",)
    before = old.evaluate_ten_gates(
        scopes, audit_complete=True, audit_warnings=warnings
    )
    after = new.evaluate_ten_gates(scopes, audit_complete=True, audit_warnings=warnings)
    assert after == before
    assert [item["number"] for item in after if not item["passed"]] == [gate]


@pytest.fixture(scope="module")
def complete_reports():
    # Pure in-memory fixtures: calendar schedule plus invented repeated outcomes.
    return tuple(
        module.build_report(
            _rows(module, 627, registered=True), SYNTHETIC_BINDINGS, audit_complete=True
        )
        for module in (old, new)
    )


def test_complete_report_preserves_all_scopes_inference_and_all_627_rows(
    complete_reports,
):
    before, after = complete_reports
    assert after == _rebind_report(before)
    assert [after["scopes"][scope]["n"] for scope in new.SCOPE_ORDER] == [627, 314, 313]
    assert after["disposition"] == "Reject"
    assert after["gates"] == before["gates"]
    assert after["multiplicity"]["variant_index"] == 4
    assert after["eligible_evidence"] is after["promotion_authority"] is False
    assert after["statistical_fingerprint_sha256"] == FINGERPRINT
    assert after["required_pure_core_sha256"] == CORE_SHA256
    assert after["exclusions"] == before["exclusions"]
    assert len(after["annual_descriptive_only"]) == 6
    assert old.render_markdown(before).replace(
        "# V12.0.1 历史严格回测诊断", "# V12.0.2 历史严格回测诊断"
    ) == new.render_markdown(after)
    assert (
        len(
            [
                line
                for line in new.render_markdown(after).splitlines()
                if line.startswith("| 20")
            ]
        )
        == 627 * 4
    )


@pytest.mark.parametrize(
    "audit_complete,warnings",
    [(False, ()), (True, ("synthetic_default_notification_failed",))],
)
def test_complete_report_retains_audit_and_notification_failure_archive(
    complete_reports, monkeypatch, audit_complete, warnings
):
    results = []
    for module, report in zip((old, new), complete_reports, strict=True):
        summaries = {scope["n"]: scope for scope in report["scopes"].values()}
        # Reuse proven synthetic inference only to isolate disposition predicates.
        monkeypatch.setattr(
            module,
            "_scope_summary",
            lambda rows, bound=summaries: deepcopy(bound[len(rows)]),
        )
        results.append(
            module.build_report(
                report["targets"],
                SYNTHETIC_BINDINGS,
                audit_complete=audit_complete,
                audit_warnings=warnings,
            )
        )
    assert results[1] == _rebind_report(results[0])
    assert results[1]["disposition"] == "Archive"
    assert results[1]["gates"][9]["passed"] is False


@pytest.mark.parametrize(
    "exact,warnings",
    [(False, ()), (True, ()), (True, ("synthetic_default_notification_failed",))],
)
def test_partial_exact_hit_and_notification_markers_never_fabricate_complete_results(
    exact, warnings
):
    reason = (
        "exact_final6_pending_independent_audit" if exact else "synthetic_interruption"
    )
    results = [
        module.build_report(
            _rows(module, 1, exact_first=exact, registered=True),
            SYNTHETIC_BINDINGS,
            audit_complete=False,
            audit_warnings=warnings,
            stop_reason=reason,
        )
        for module in (old, new)
    ]
    assert results[1] == _rebind_report(results[0])
    after = results[1]
    assert after["processed_target_count"] == 1
    assert after["gates"] is after["multiplicity"] is None
    assert after["scopes"] == {}
    assert after["disposition"] == (
        "pending_audit" if exact and not warnings else "Archive"
    )
    assert bool(after["targets"][0]["exact_final6_opportunities"]) == exact
    assert (
        after["targets"][0]["top12_all_six_producers"]
        == results[0]["targets"][0]["top12_all_six_producers"]
    )
    assert after["eligible_evidence"] is after["promotion_authority"] is False
    assert "未运行的目标没有预测或评分" in new.render_markdown(after)


@pytest.mark.parametrize("module", [old, new])
def test_empty_or_after_exact_hit_reports_cannot_create_scientific_success(module):
    empty = module.build_report(
        [],
        SYNTHETIC_BINDINGS,
        audit_complete=False,
        stop_reason="synthetic_pre_score_stop",
    )
    assert empty["disposition"] == "Archive" and empty["targets"] == []
    with pytest.raises(ValueError, match="continued after an exact Final-6"):
        module.build_report(
            _rows(module, 2, exact_first=True, registered=True),
            SYNTHETIC_BINDINGS,
            audit_complete=True,
        )


@pytest.mark.parametrize(
    "mutation",
    ["same_day", "future", "reorder", "missing", "probability", "rank", "version"],
)
def test_both_versions_refuse_chronology_identity_and_score_tampering(mutation):
    for module in (old, new):
        payload = _payload(module)
        if mutation in {"same_day", "future"}:
            payload["history_through"] = (
                SYNTHETIC_TARGET + timedelta(days=mutation == "future")
            ).isoformat()
        elif mutation == "reorder":
            payload["forecasts"].reverse()
        elif mutation == "missing":
            payload["forecasts"].pop()
        elif mutation == "probability":
            payload["forecasts"][0]["probabilities"]["1"] = 0.5
        elif mutation == "rank":
            payload["forecasts"][0]["ranking"].reverse()
        else:
            payload["forecasts"][0]["model_version"] = "unregistered"
        with pytest.raises(ValueError):
            module.validate_frozen_payload(module.canonical_json_bytes(payload))


@pytest.mark.parametrize(
    "raw",
    [
        b'{"a":1,"a":2}\n',
        b'{"a":NaN}\n',
        b'{"a":Infinity}\n',
        b'{"a":1}',
        b'{"a":1}\n\n',
        b'{ "a":1}\n',
    ],
)
def test_canonical_wire_validation_remains_fail_closed(raw):
    for module in (old, new):
        with pytest.raises(ValueError):
            module.decode_canonical_json(raw)
    value = {"z": "中文", "a": [True, None, 1, 0.5]}
    assert new.canonical_json_bytes(value) == old.canonical_json_bytes(value)


@pytest.mark.parametrize("values", [(), (True,), (math.nan,), (math.inf,)])
def test_statistical_inputs_cannot_be_empty_boolean_or_nonfinite(values):
    for module in (old, new):
        with pytest.raises(ValueError):
            module.bootstrap_interval(values)
        with pytest.raises(ValueError):
            module.holm_adjusted(values)


@pytest.mark.parametrize(
    "mutation", ["empty", "same_day", "future", "duplicate", "seed"]
)
def test_four_forecasts_refuse_invalid_prefix_before_comparator_fit(
    monkeypatch, mutation
):
    for module in (old, new):
        prefix = list(_prefix(tilted=True))
        config = deepcopy(V1_CONFIG)
        if mutation == "empty":
            prefix = []
        elif mutation in {"same_day", "future"}:
            prefix.append(
                Draw(
                    SYNTHETIC_TARGET + timedelta(days=mutation == "future"),
                    (1, 2, 3, 4, 5, 6),
                )
            )
        elif mutation == "duplicate":
            prefix.append(prefix[-1])
        else:
            config["project"]["seed"] = 650

        def forbidden_fit(*args, **kwargs):
            pytest.fail("invalid chronology or identity reached model construction")

        monkeypatch.setattr(module, "build_models", forbidden_fit)
        with pytest.raises(ValueError):
            module.four_forecasts(prefix, SYNTHETIC_TARGET, config)


def test_even_all_gate_pass_stays_consumed_without_promotion(
    complete_reports, monkeypatch
):
    results = []
    artificial = _passing_scopes()
    for module, report in zip((old, new), complete_reports, strict=True):
        summaries = {}
        for name, source in report["scopes"].items():
            scope = deepcopy(source)
            for model, values in artificial[name]["models"].items():
                scope["models"][model].update(values)
            for contrast, values in artificial[name]["contrasts"].items():
                scope["contrasts"][contrast].update(values)
            summaries[scope["n"]] = scope
        # Artificial predicates isolate the unchanged governance meaning.
        monkeypatch.setattr(
            module,
            "_scope_summary",
            lambda rows, bound=summaries: deepcopy(bound[len(rows)]),
        )
        results.append(
            module.build_report(
                report["targets"], SYNTHETIC_BINDINGS, audit_complete=True
            )
        )
    assert results[1] == _rebind_report(results[0])
    assert all(gate["passed"] for gate in results[1]["gates"])
    assert results[1]["disposition"] == "consumed_diagnostic_all_gates_pass"
    assert results[1]["eligible_evidence"] is results[1]["promotion_authority"] is False
    assert "已消耗的历史诊断数据" in new.render_markdown(results[1])


def test_terminal_marker_prevents_complete_disposition_even_with_627_rows(
    complete_reports,
):
    results = [
        module.build_report(
            report["targets"],
            SYNTHETIC_BINDINGS,
            audit_complete=True,
            stop_reason="synthetic_terminal_error",
        )
        for module, report in zip((old, new), complete_reports, strict=True)
    ]
    assert results[1] == _rebind_report(results[0])
    assert results[1]["processed_target_count"] == 627
    assert results[1]["complete_registered_scope"] is False
    assert results[1]["gates"] is None
    assert results[1]["disposition"] == "Archive"
