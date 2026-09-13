"""Synthetic-only regression tests; never load history or run the real models."""

import importlib.util
import json
import math
from datetime import date
from pathlib import Path

import numpy as np
import pytest

from lotto649.domain import Draw

SPEC = importlib.util.spec_from_file_location(
    "v1_diagnostic",
    Path(__file__).parents[1] / "tools/run_v1_verified_history_diagnostic.py",
)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


@pytest.fixture
def draws():
    return [
        Draw(date(2019, 12, 28), (21, 22, 23, 24, 25, 26), 49),
        Draw(date(2020, 1, 1), (7, 8, 9, 10, 11, 12), 49),
        Draw(date(2020, 1, 4), (13, 14, 15, 16, 17, 18), 49),
        Draw(date(2020, 1, 8), (19, 20, 21, 22, 23, 24), 49),
    ]


def uniform_forecast(prefix, target):
    assert all(draw.draw_date < target for draw in prefix)
    return {name: {n: 6 / 49 for n in range(1, 50)} for name in module.PRODUCERS}


def biased(favorites):
    return {n: 0.2 if n in favorites else 4.8 / 43 for n in range(1, 50)}


def test_freeze_files_and_ledger_fsync_before_reveal(tmp_path, draws, monkeypatch):
    directory = tmp_path / "synthetic-ordering"
    module._new_directory(directory)
    bindings = {
        "classification": "synthetic_fixture_only",
        "source_git_commit": "synthetic",
        "expected_target_count": 3,
        "synthetic_target_dates": [d.draw_date.isoformat() for d in draws[1:]],
    }
    module.exclusive_json(directory / "claim.json", bindings)
    trail = []
    original_sync, original_append = module.os.fsync, module.Ledger.append
    monkeypatch.setattr(
        module.os, "fsync", lambda fd: (original_sync(fd), trail.append("fsync"))[0]
    )

    def append(self, kind, payload):
        result = original_append(self, kind, payload)
        assert trail[-1] == "fsync"
        trail.append(kind)
        return result

    monkeypatch.setattr(module.Ledger, "append", append)
    positions = {d.draw_date: i for i, d in enumerate(draws)}

    def reveal(target):
        assert trail[-1] == "prediction_frozen"
        files = list((directory / "predictions").glob(f"{target.isoformat()}__*.json"))
        assert len(files) == 3
        assert all(
            json.loads(p.read_text())["target_date"] == target.isoformat()
            for p in files
        )
        trail.append("reveal")
        return draws[positions[target]]

    report = module._sequence(
        directory,
        [d.draw_date for d in draws[1:]],
        lambda t: draws[: positions[t]],
        reveal,
        uniform_forecast,
        bindings,
        lambda: "2000-01-01T00:00:00Z",
    )
    assert report["scored_target_count"] == 3
    assert module.verify(directory)["scored_target_count"] == 3


def test_fsync_failure_never_reveals_target(tmp_path, draws, monkeypatch):
    directory = tmp_path / "synthetic-durability-failure"
    module._new_directory(directory)
    bindings = {"classification": "synthetic_fixture_only"}
    module.exclusive_json(directory / "claim.json", bindings)
    state, revealed = {"kind": None}, []
    original_sync, original_append = module.os.fsync, module.Ledger.append

    def fsync(fd):
        if state["kind"] == "prediction_frozen":
            raise OSError("synthetic fsync failure")
        original_sync(fd)

    def append(self, kind, payload):
        state["kind"] = kind
        try:
            return original_append(self, kind, payload)
        finally:
            state["kind"] = None

    monkeypatch.setattr(module.os, "fsync", fsync)
    monkeypatch.setattr(module.Ledger, "append", append)
    with pytest.raises(OSError):
        module._sequence(
            directory,
            [draws[1].draw_date],
            lambda t: draws[:1],
            lambda t: revealed.append(t),
            uniform_forecast,
            bindings,
            module.now,
        )
    assert revealed == []
    assert directory.exists()
    assert len(list((directory / "predictions").glob("*.json"))) == 3


def test_changed_target_and_future_do_not_change_first_frozen_payload(tmp_path, draws):
    changed = [
        draws[0],
        Draw(draws[1].draw_date, (30, 31, 32, 33, 34, 35), 49),
        Draw(draws[2].draw_date, (37, 38, 39, 40, 41, 42), 49),
        draws[3],
    ]
    module.run_synthetic(tmp_path / "original", draws, uniform_forecast)
    module.run_synthetic(tmp_path / "changed", changed, uniform_forecast)
    for producer in module.PRODUCERS:
        path = f"predictions/2020-01-01__{producer}.json"
        assert (tmp_path / "original" / path).read_bytes() == (
            tmp_path / "changed" / path
        ).read_bytes()


@pytest.mark.parametrize(
    "mutation", ["missing", "extra", "nan", "zero", "one", "sum", "string"]
)
def test_full_probability_contract(mutation):
    values = {n: 6 / 49 for n in range(1, 50)}
    if mutation == "missing":
        values.pop(49)
    elif mutation == "extra":
        values[50] = 0.1
    elif mutation == "string":
        values["1"] = values.pop(1)
    else:
        values[1] = {"nan": float("nan"), "zero": 0.0, "one": 1.0, "sum": 0.9}[mutation]
    with pytest.raises(module.DiagnosticError):
        module.probability_payload(values)


def test_label_control_uses_fixed_mapping_without_refit():
    values = biased(range(1, 7))
    target = date(2020, 1, 1)
    labels = np.random.default_rng(649 + target.toordinal()).permutation(range(1, 50))
    control = module.label_permuted(values, target)
    assert control == {int(label): values[n] for n, label in enumerate(labels, 1)}
    assert sorted(control.values()) == sorted(values.values())
    assert values == biased(range(1, 7))


@pytest.mark.parametrize("producer", module.PRODUCERS)
def test_first_final6_from_any_producer_stops_before_next_forecast(
    tmp_path, draws, producer
):
    calls = []

    def forecast(prefix, target):
        calls.append(target)
        result = uniform_forecast(prefix, target)
        result[producer] = biased(range(7, 13))
        return result

    directory = tmp_path / "synthetic-first-exact"
    report = module.run_synthetic(directory, draws, forecast)
    assert calls == [draws[1].draw_date]
    assert report["partial"] and report["stopped_on_first_final6"]
    assert report["independent_leakage_audit"] == "pending"
    assert report["notification"] == "pending_default_route_by_operator"
    assert report["rows"][0]["exact_final6_producers"] == [producer]
    assert report["scopes"]["aggregate"]["producers"][producer]["fair_null_p"] is None
    assert module.verify(directory)["stopped_on_first_final6"]


def test_existing_output_directory_refuses_even_if_empty(tmp_path, draws):
    directory = tmp_path / "synthetic-no-overwrite"
    directory.mkdir()
    with pytest.raises(FileExistsError):
        module.run_synthetic(
            directory, draws, lambda *args: pytest.fail("forecast retried")
        )
    assert list(directory.iterdir()) == []


def test_synthetic_cannot_write_canonical_report_path(tmp_path, draws):
    with pytest.raises(module.DiagnosticError):
        module.run_synthetic(tmp_path / "reports" / "anything", draws, uniform_forecast)


def test_scoring_and_fair_calibration_closed_form(tmp_path, draws):
    report = module.run_synthetic(
        tmp_path / "synthetic-metrics", draws, uniform_forecast
    )
    summary = report["scopes"]["aggregate"]["producers"][module.PRODUCERS[0]]
    p = 6 / 49
    assert summary["mean_brier"] == pytest.approx(p * (1 - p))
    assert summary["mean_binary_log_loss"] == pytest.approx(
        -p * math.log(p) - (1 - p) * math.log1p(-p)
    )
    assert summary["mean_hits"] == {
        "top6": 0.0,
        "top12": 2.0,
        "top18": 4.0,
        "final6": 0.0,
    }
    assert summary["final6_distribution"] == {
        str(i): 3 if i == 0 else 0 for i in range(7)
    }
    assert summary["all_best_dates"] == [d.draw_date.isoformat() for d in draws[1:]]
    bucket = summary["calibration"][1]
    assert bucket["count"] == 147 and bucket["positive_count"] == 18
    assert bucket["mean_probability"] == pytest.approx(p)
    assert bucket["observed_frequency"] == pytest.approx(p)
    assert sum(b["count"] for b in summary["calibration"]) == 147


def test_fair_null_moments_and_tail_oracles():
    for k in (6, 12, 18):
        distribution = module.null_distribution(1, k)
        mean = sum(j * p for j, p in enumerate(distribution))
        variance = sum((j - mean) ** 2 * p for j, p in enumerate(distribution))
        assert module.fair_moments(k) == pytest.approx(
            {"mean": mean, "variance": variance}
        )
        assert module.exact_upper_tail(1, k, 6) == pytest.approx(
            math.comb(k, 6) / math.comb(49, 6)
        )
        assert module.exact_upper_tail(2, k, 12) == pytest.approx(
            (math.comb(k, 6) / math.comb(49, 6)) ** 2
        )
        assert module.exact_upper_tail(2, k, 0) == pytest.approx(1.0)
    assert module.holm([0.01, 0.04, 0.03]) == pytest.approx([0.03, 0.06, 0.06])


def test_bootstrap_alignment_and_constant_difference_oracle():
    indices = module.bootstrap_indices(25)
    assert indices.shape == (2000, 25)
    assert np.array_equal(indices, module.bootstrap_indices(25))
    assert np.all((indices[:, 1:12] - indices[:, :11]) % 25 == 1)
    difference = np.ones((25, 4)) * np.array([1, -1, 2, 0])
    intervals = np.quantile(difference[indices].mean(axis=1), [0.025, 0.975], axis=0)
    assert np.array_equal(intervals, [[1, -1, 2, 0], [1, -1, 2, 0]])


def test_all_controls_count_once_per_unique_set(tmp_path, draws):
    report = module.run_synthetic(
        tmp_path / "synthetic-opportunities", draws, uniform_forecast
    )
    opportunities = report["opportunities"]
    assert opportunities["per_target_unique_counts"] == [1, 1, 1]
    assert opportunities["cumulative_count"] == 3
    assert opportunities["fair_probability_at_least_one_final6"] == pytest.approx(
        -math.expm1(3 * math.log1p(-1 / math.comb(49, 6)))
    )


def test_fixed_target_identity_and_halves():
    dates = module.target_dates()
    assert len(dates) == 627
    assert len([d for d in dates if d.year <= 2022]) == 314
    assert len([d for d in dates if d.year >= 2023]) == 313
    assert (
        module.digest("".join(d.isoformat() + "\n" for d in dates).encode())
        == "c339733dccc04c3ac25aca15ce991c31421ba35580488e7acadbea5672705782"
    )


@pytest.mark.parametrize(
    "artifact", ["prediction", "evaluation", "report", "ledger", "markdown"]
)
def test_readonly_verifier_rejects_tampering(tmp_path, draws, artifact):
    directory = tmp_path / "synthetic-tamper"
    module.run_synthetic(directory, draws, uniform_forecast)
    paths = {
        "prediction": next((directory / "predictions").glob("*.json")),
        "evaluation": next((directory / "evaluations").glob("*.json")),
        "report": directory / "report.json",
        "ledger": directory / "ledger.jsonl",
        "markdown": directory / "report.md",
    }
    path = paths[artifact]
    path.chmod(0o644)
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises((module.DiagnosticError, json.JSONDecodeError)):
        module.verify(directory)


class FakeAPI:
    def __init__(self, responses):
        self.responses, self.calls, self.guard_started = list(responses), [], False

    def request(self, method, endpoint, body=None):
        self.calls.append((method, endpoint, body))
        result = self.responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def remote_records():
    head = "a" * 40
    record = {"ref": module.REMOTE_REF, "object": {"sha": head, "type": "commit"}}
    return head, [
        (200, {"object": {"sha": head, "type": "commit"}}),
        (404, {"message": "Not Found"}),
        (201, record),
        (200, record),
    ]


def test_remote_once_exact_404_create_and_reread():
    head, responses = remote_records()
    api = FakeAPI(responses)
    module.run_once_remote_guard(api, head)
    assert [call[0] for call in api.calls] == ["GET", "GET", "POST", "GET"]
    assert api.calls[2][2] == {"ref": module.REMOTE_REF, "sha": head}
    with pytest.raises(module.DiagnosticError):
        module.run_once_remote_guard(api, head)
    assert len(api.calls) == 4


@pytest.mark.parametrize(
    "absence", [(200, {}), (403, {}), (404, {"message": "other"}), (500, {})]
)
def test_no_remote_creation_without_exact_absence(absence):
    head, responses = remote_records()
    responses[1] = absence
    api = FakeAPI(responses)
    with pytest.raises(module.DiagnosticError):
        module.run_once_remote_guard(api, head)
    assert all(method == "GET" for method, _, _ in api.calls)


@pytest.mark.parametrize(
    "failure",
    [
        (500, {}),
        RuntimeError("uncertain"),
        (
            201,
            {"ref": module.REMOTE_REF, "object": {"sha": "b" * 40, "type": "commit"}},
        ),
    ],
)
def test_uncertain_remote_creation_is_not_retried(failure):
    head, responses = remote_records()
    responses[2] = failure
    api = FakeAPI(responses)
    with pytest.raises((module.DiagnosticError, RuntimeError)):
        module.run_once_remote_guard(api, head)
    with pytest.raises(module.DiagnosticError):
        module.run_once_remote_guard(api, head)
    assert sum(method == "POST" for method, _, _ in api.calls) == 1


def test_remote_main_drift_refuses_before_consumption():
    head, responses = remote_records()
    responses[0] = (200, {"object": {"sha": "b" * 40, "type": "commit"}})
    api = FakeAPI(responses)
    with pytest.raises(module.DiagnosticError):
        module.run_once_remote_guard(api, head)
    assert len(api.calls) == 1


def test_missing_registration_rejects_before_history_network_or_outputs(
    tmp_path, monkeypatch
):
    called = []
    monkeypatch.setattr(
        module,
        "source_bindings",
        lambda root: (_ for _ in ()).throw(module.DiagnosticError("unregistered")),
    )
    monkeypatch.setattr(module, "GitHubMetadataAPI", lambda: called.append("network"))
    with pytest.raises(module.DiagnosticError):
        module.run_registered(tmp_path)
    assert called == [] and list(tmp_path.iterdir()) == []


def test_existing_real_directory_rejects_before_remote_guard(tmp_path, monkeypatch):
    directory = tmp_path / module.OUTPUT
    directory.mkdir(parents=True)
    monkeypatch.setattr(
        module, "source_bindings", lambda root: {"source_git_commit": "a" * 40}
    )
    monkeypatch.setattr(
        module, "GitHubMetadataAPI", lambda: pytest.fail("remote guard called")
    )
    with pytest.raises(module.DiagnosticError):
        module.run_registered(tmp_path)
    assert list(directory.iterdir()) == []
