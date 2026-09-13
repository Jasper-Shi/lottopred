"""Synthetic-only tests for V12.0.2 execution boundaries.

These tests never invoke the registered historical command or instantiate its
canonical attempt. Every writable repository and event stream is a fixture.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import json
import os
import runpy
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Self

import pytest

ROOT = Path(__file__).resolve().parents[1]


LAUNCHER = ROOT / "tools/run_v12_0_2_historical.py"


@pytest.fixture
def launcher():
    loaded = runpy.run_path(str(LAUNCHER), run_name="synthetic_launcher_fixture")
    return loaded["main"].__globals__


def _launcher_sys(*, arguments=None, version=None):
    return SimpleNamespace(
        argv=[str(LAUNCHER), *(arguments or ["--consume-v12-0-2-once"])],
        implementation=SimpleNamespace(name="cpython"),
        version_info=sys.version_info if version is None else version,
        flags=SimpleNamespace(isolated=False, no_site=False),
        dont_write_bytecode=False,
        executable="/synthetic/venv/bin/python3.12",
        stderr=sys.stderr,
        path=[],
    )


@pytest.mark.parametrize(
    "arguments",
    [[], ["--consume-v12-once"], ["--consume-v12-0-2-once", "--retry"]],
)
def test_launcher_rejects_every_alternate_command_before_reexec(
    launcher, monkeypatch, arguments
):
    runtime = _launcher_sys()
    runtime.argv = [str(LAUNCHER), *arguments]
    monkeypatch.setitem(launcher, "sys", runtime)
    monkeypatch.setitem(launcher, "os", SimpleNamespace(environ={}))

    assert launcher["main"]() == 2


@pytest.mark.parametrize("version", [(3, 11), (3, 13), (3, 14)])
def test_launcher_requires_registered_cpython_minor(launcher, monkeypatch, version):
    monkeypatch.setitem(launcher, "sys", _launcher_sys(version=version))
    monkeypatch.setitem(launcher, "os", SimpleNamespace(environ={}))

    assert launcher["main"]() == 2


@pytest.mark.parametrize("key", ["SMTP_HOST", "SMTP_PORT", "EMAIL_FROM", "EMAIL_TO"])
def test_launcher_refuses_routing_overrides_without_printing_values(
    launcher, monkeypatch, capsys, key
):
    monkeypatch.setitem(launcher, "sys", _launcher_sys())
    monkeypatch.setitem(
        launcher, "os", SimpleNamespace(environ={key: "synthetic-private-value"})
    )

    assert launcher["main"]() == 2
    captured = capsys.readouterr()
    assert "synthetic-private-value" not in captured.out + captured.err


def test_launcher_reexec_scrubs_injected_runtime_git_proxy_and_routing(
    launcher, monkeypatch
):
    calls = []
    environment = {
        "GH_TOKEN": "synthetic-token",
        "SMTP_USERNAME": "synthetic@example.invalid",
        "SMTP_PASSWORD": "synthetic-password",
        "PATH": "/untrusted/bin",
        "PYTHONPATH": "/untrusted/python",
        "PYTHONHOME": "/untrusted/home",
        "HTTP_PROXY": "https://untrusted.invalid",
        "HTTPS_PROXY": "https://untrusted.invalid",
        "SSL_CERT_FILE": "/untrusted/certificate",
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": "core.sshCommand",
        "GIT_CONFIG_VALUE_0": "untrusted-command",
        "GIT_ASKPASS": "/untrusted/askpass",
    }
    runtime = _launcher_sys()
    monkeypatch.setitem(launcher, "sys", runtime)
    monkeypatch.setitem(
        launcher,
        "os",
        SimpleNamespace(
            environ=environment,
            execve=lambda *args: calls.append(args),
        ),
    )

    assert launcher["main"]() == 2  # A real execve never returns.
    assert len(calls) == 1
    executable, arguments, child_environment = calls[0]
    assert executable == runtime.executable
    assert arguments == [
        executable,
        "-I",
        "-S",
        "-B",
        str(LAUNCHER),
        "--consume-v12-0-2-once",
    ]
    assert child_environment == {
        **launcher["_FIXED_ENVIRONMENT"],
        **{key: environment[key] for key in launcher["_SECRET_NAMES"]},
    }
    assert environment["PATH"] == "/untrusted/bin"


def _fixture_git(root: Path, *arguments: str) -> str:
    environment = {
        "PATH": "/usr/bin:/bin",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_AUTHOR_NAME": "Synthetic test",
        "GIT_AUTHOR_EMAIL": "test@example.invalid",
        "GIT_COMMITTER_NAME": "Synthetic test",
        "GIT_COMMITTER_EMAIL": "test@example.invalid",
        "GIT_AUTHOR_DATE": "2020-01-01T00:00:00+0000",
        "GIT_COMMITTER_DATE": "2020-01-01T00:00:00+0000",
    }
    return subprocess.run(
        ["/usr/bin/git", "-C", str(root), *arguments],
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


@pytest.fixture
def launcher_repository(tmp_path, launcher):
    root = tmp_path / "synthetic-clone"
    root.mkdir()
    _fixture_git(root, "init", "--quiet", "--initial-branch=main")
    for relative in launcher["_INITIAL_SOURCES"]:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# Synthetic source fixture, never executed.\n")
    _fixture_git(root, "add", ".")
    _fixture_git(root, "commit", "--quiet", "-m", "synthetic source tree")
    return root


def test_launcher_binds_initial_import_sources_to_plain_git_blobs(
    launcher, launcher_repository
):
    launcher["_verify_initial_sources"](launcher_repository)


@pytest.mark.parametrize("index", [0, 1, 2])
def test_launcher_refuses_changed_initial_source_bytes(
    launcher, launcher_repository, index
):
    path = launcher_repository / launcher["_INITIAL_SOURCES"][index]
    path.write_text("# Changed synthetic source.\n")

    with pytest.raises(RuntimeError, match="uncommitted source"):
        launcher["_verify_initial_sources"](launcher_repository)


def test_launcher_refuses_untracked_source_bytecode(launcher, launcher_repository):
    cache = launcher_repository / "src/lotto649/__pycache__"
    cache.mkdir()
    (cache / "injected.cpython-312.pyc").write_bytes(b"synthetic bytecode")

    with pytest.raises(RuntimeError, match="without bytecode"):
        launcher["_verify_initial_sources"](launcher_repository)


def test_launcher_refuses_source_symlinks(launcher, launcher_repository, tmp_path):
    path = launcher_repository / launcher["_INITIAL_SOURCES"][1]
    outside = tmp_path / "outside.py"
    outside.write_bytes(path.read_bytes())
    path.unlink()
    path.symlink_to(outside)

    with pytest.raises(RuntimeError, match="symlink"):
        launcher["_verify_initial_sources"](launcher_repository)


def test_launcher_git_failure_never_exposes_transport_diagnostics(
    launcher, monkeypatch
):
    calls = []

    def fail(*args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(
            returncode=1, stdout=b"", stderr=b"synthetic-private-transport-details"
        )

    monkeypatch.setitem(launcher, "subprocess", SimpleNamespace(run=fail))
    with pytest.raises(RuntimeError, match="intact immutable Git objects") as caught:
        launcher["_git"](Path("/synthetic"), "rev-parse", "HEAD")
    assert "synthetic-private" not in str(caught.value)
    assert calls[0][0][0][0] == "/usr/bin/git"
    assert calls[0][1]["env"] == launcher["_FIXED_ENVIRONMENT"]


@pytest.fixture
def attempt():
    from lotto649 import v12_0_2_registered_attempt

    return v12_0_2_registered_attempt


class _HttpResponse:
    def __init__(self, *, status=200, body=b"{}", url=None, headers=None):
        self.status_code = status
        self.body = body
        self.url = url
        self.headers = (
            {"Content-Type": "application/json"} if headers is None else headers
        )

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_args):
        return False

    def iter_content(self, _size):
        yield self.body


def _http_fixture(attempt, monkeypatch, response):
    api = attempt.FixedGitHubApi("synthetic-token")
    calls = []

    def request(method, url, **kwargs):
        calls.append((method, url, kwargs))
        if isinstance(response, Exception):
            raise response
        if response.url is None:
            response.url = url
        return response

    monkeypatch.setattr(api._session, "request", request)
    assert api._session.trust_env is False
    assert api._session.get_adapter("https://api.github.com").max_retries.total == 0
    return api, calls


@pytest.mark.parametrize("status", [301, 302, 307, 401, 403, 429, 500, 503])
def test_lease_absence_requires_direct_exact_404(attempt, monkeypatch, status):
    api, calls = _http_fixture(attempt, monkeypatch, _HttpResponse(status=status))

    with pytest.raises(attempt.AuthorizationError):
        api.request_json(
            "GET",
            attempt._API_PREFIX + "/git/ref/heads/v12-consumption-v12.0.2",
            allow_absent=True,
        )
    assert len(calls) == 1
    assert calls[0][2]["allow_redirects"] is False


def test_exact_not_found_is_the_only_accepted_lease_absence(attempt, monkeypatch):
    api, calls = _http_fixture(
        attempt,
        monkeypatch,
        _HttpResponse(status=404, body=b'{"message":"Not Found"}'),
    )

    assert (
        api.request_json(
            "GET",
            attempt._API_PREFIX + "/git/ref/heads/v12-consumption-v12.0.2",
            allow_absent=True,
        )
        is None
    )
    assert len(calls) == 1


@pytest.mark.parametrize("body", [b"{}", b"not JSON", b'{"message":"Rate limited"}'])
def test_malformed_404_never_grants_lease_absence(attempt, monkeypatch, body):
    api, calls = _http_fixture(
        attempt, monkeypatch, _HttpResponse(status=404, body=body)
    )

    with pytest.raises(attempt.AuthorizationError):
        api.request_json(
            "GET",
            attempt._API_PREFIX + "/git/ref/heads/v12-consumption-v12.0.2",
            allow_absent=True,
        )
    assert len(calls) == 1


@pytest.mark.parametrize(
    "method,path,payload,allow_absent",
    [
        ("DELETE", "/git/refs/heads/v12-consumption-v12.0.2", None, False),
        ("PATCH", "/git/refs/heads/v12-consumption-v12.0.2", {"sha": "a" * 40}, False),
        ("GET", "/git/ref/heads/main", None, True),
        ("GET", "/git/commits/abc123", None, False),
        ("POST", "/git/refs", {"ref": "refs/heads/main", "sha": "a" * 40}, False),
        (
            "POST",
            "/git/refs",
            {"ref": "refs/heads/v12-consumption-v12.0.0", "sha": "a" * 40},
            False,
        ),
        (
            "POST",
            "/git/refs",
            {"ref": "refs/heads/v12-consumption-v12.0.2", "sha": "abc123"},
            False,
        ),
    ],
)
def test_github_capability_refuses_other_actions_before_transport(
    attempt, monkeypatch, method, path, payload, allow_absent
):
    api, calls = _http_fixture(attempt, monkeypatch, _HttpResponse())

    with pytest.raises(attempt.AuthorizationError):
        api.request_json(
            method,
            attempt._API_PREFIX + path,
            body_bytes=None if payload is None else _canonical_fixture(payload),
            allow_absent=allow_absent,
        )
    assert not calls


def test_transport_failure_has_no_credential_exception_chain(attempt, monkeypatch):
    import traceback

    api, calls = _http_fixture(
        attempt, monkeypatch, OSError("Authorization: Bearer synthetic-secret-detail")
    )

    with pytest.raises(attempt.AuthorizationError) as caught:
        api.request_json("GET", attempt._API_PREFIX + "/git/ref/heads/main")
    rendered = "".join(traceback.format_exception(caught.value))
    assert "synthetic-secret-detail" not in rendered
    assert len(calls) == 1


@pytest.mark.parametrize(
    "source",
    [
        "import importlib as alias\nalias.import_module('lotto649.hidden')",
        "from importlib import import_module as alias\nalias('lotto649.hidden')",
        "from builtins import __import__ as alias\nalias('lotto649.hidden')",
        "loader = __import__\nloader('lotto649.hidden')",
        "loader = eval\nloader('1')",
        "getter = getattr\ngetter(object(), 'hidden')",
        "setter = setattr\nsetter(object(), 'hidden', 1)",
        "import sys as alias\nalias.modules['lotto649.hidden'] = None",
        "import sys as alias\nalias.path.append('/unregistered')",
        "import importlib.metadata as alias\nalias.sys.modules['builtins']",
        "globals()['__builtins__']['__import__']('lotto649.hidden')",
        "object.__getattribute__(object(), '__class__')",
        "().__class__.__base__.__subclasses__()",
        "from lotto649.domain import *",
    ],
)
def test_source_closure_refuses_dynamic_imports_and_reflection(attempt, source):
    with pytest.raises(attempt.AuthorizationError):
        attempt._check_source_safety(
            "src/lotto649/synthetic_module.py", ast.parse(source)
        )


def test_safe_nested_static_imports_remain_auditable(attempt):
    attempt._check_source_safety(
        "src/lotto649/synthetic_module.py",
        ast.parse(
            "from .domain import Draw\ndef call():\n    import math\n    return math.fsum([])"
        ),
    )


@pytest.mark.parametrize("key", ["SMTP_HOST", "SMTP_PORT", "EMAIL_FROM", "EMAIL_TO"])
def test_default_notification_refuses_all_caller_routing_overrides(
    attempt, monkeypatch, key
):
    from lotto649 import notification

    calls = []
    monkeypatch.setattr(notification, "send_email", lambda *args: calls.append(args))
    for name in attempt._ROUTE_OVERRIDES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv(key, "synthetic-secret-routing-value")
    with pytest.raises(attempt.AuthorizationError) as caught:
        attempt._default_notification("synthetic subject", "synthetic body")
    assert "synthetic-secret" not in str(caught.value)
    assert calls == []


def test_notification_uses_only_reviewed_repository_default_route(attempt, monkeypatch):
    from lotto649 import notification

    calls = []
    monkeypatch.setattr(
        notification,
        "send_email",
        lambda *args, **kwargs: calls.append((args, kwargs)) or True,
    )
    for name in attempt._ROUTE_OVERRIDES:
        monkeypatch.delenv(name, raising=False)
    assert attempt._default_notification("synthetic subject", "synthetic body") is True
    assert calls == [(("synthetic subject", "synthetic body"), {})]


def _durable_case(*, first_main=(31, 33, 35, 37, 39, 41)):
    from datetime import date

    from lotto649 import v12_0_2_evidence as evidence
    from lotto649.domain import Draw

    targets = (date(2020, 1, 1), date(2020, 1, 4))
    base = Draw(date(2019, 12, 28), (1, 2, 3, 4, 5, 6))
    actual = {
        targets[0]: Draw(targets[0], first_main),
        targets[1]: Draw(targets[1], (37, 39, 41, 43, 45, 47)),
    }
    calls = {"prefix": [], "forecast": [], "reveal": [], "notify": []}

    def prefix_for(target):
        calls["prefix"].append(target)
        return (base, *(actual[earlier] for earlier in targets if earlier < target))

    def forecast(prefix, target):
        calls["forecast"].append(target)
        fair = {label: 6.0 / 49.0 for label in range(1, 50)}
        return [
            evidence.serialize_parity_forecast(
                evidence.forecast_candidate(prefix, target)
            ),
            evidence.serialize_parity_forecast(
                evidence.forecast_control(prefix, target)
            ),
            evidence.serialize_comparator_forecast(evidence.ENSEMBLE_MODEL_NAME, fair),
            evidence.serialize_comparator_forecast(evidence.RANDOM_MODEL_NAME, fair),
        ]

    def reveal(target):
        calls["reveal"].append(target)
        return actual[target]

    def notify(subject, body):
        calls["notify"].append((subject, body))
        return True

    return SimpleNamespace(
        targets=targets,
        base=base,
        actual=actual,
        calls=calls,
        prefix_for=prefix_for,
        forecast=forecast,
        reveal=reveal,
        notify=notify,
    )


def _durable_run(attempt, directory, case, **overrides):
    arguments = {
        "output_root": directory,
        "targets": case.targets,
        "prefix_for": case.prefix_for,
        "reveal": case.reveal,
        "forecast": case.forecast,
        "bindings": {"fixture": "durable-regression", "seed": 649},
        "notify": case.notify,
    }
    arguments.update(overrides)
    return attempt.run_synthetic_attempt(**arguments)


def _durable_events(attempt, directory):
    path = attempt._paths(directory, synthetic=True)["ledger"]
    return [json.loads(line) for line in path.read_bytes().splitlines()]


def test_durable_all_four_forecasts_fsync_before_reveal_and_score_before_next(
    attempt, monkeypatch, tmp_path
):
    case = _durable_case()
    directory = tmp_path / "durable-order"
    ledger_path = attempt._paths(directory, synthetic=True)["ledger"]
    durable = []
    real_fsync = os.fsync

    def observe_fsync(descriptor):
        real_fsync(descriptor)
        if (
            ledger_path.exists()
            and os.fstat(descriptor).st_ino == ledger_path.stat().st_ino
        ):
            durable.append(json.loads(ledger_path.read_bytes().splitlines()[-1]))

    monkeypatch.setattr(attempt.os, "fsync", observe_fsync)
    original_forecast, original_reveal = case.forecast, case.reveal

    def forecast(prefix, target):
        if target == case.targets[1]:
            assert durable[-1]["event_kind"] == "target_revealed_scored"
            assert (
                durable[-1]["payload"]["target_draw_date"]
                == case.targets[0].isoformat()
            )
        return original_forecast(prefix, target)

    def reveal(target):
        event = durable[-1]
        assert event["event_kind"] == "prediction_frozen"
        frozen = event["payload"]["forecast_payload"]
        assert frozen["target_draw_date"] == target.isoformat()
        assert len(frozen["forecasts"]) == 4
        assert all(len(item["probabilities"]) == 49 for item in frozen["forecasts"])
        return original_reveal(target)

    report = _durable_run(attempt, directory, case, forecast=forecast, reveal=reveal)
    assert case.calls["forecast"] == list(case.targets)
    assert case.calls["reveal"] == list(case.targets)
    assert report["processed_target_count"] == 2
    assert attempt.audit_ledger(ledger_path)["scored_target_count"] == 2


def test_durable_fsync_failure_never_reveals_or_retries(attempt, monkeypatch, tmp_path):
    case = _durable_case()
    directory = tmp_path / "failed-fsync"
    paths = attempt._paths(directory, synthetic=True)
    real_fsync = os.fsync

    def fail_prediction_fsync(descriptor):
        if (
            paths["ledger"].exists()
            and os.fstat(descriptor).st_ino == paths["ledger"].stat().st_ino
        ):
            event = json.loads(paths["ledger"].read_bytes().splitlines()[-1])
            if event["event_kind"] == "prediction_frozen":
                raise OSError("synthetic fsync failure")
        real_fsync(descriptor)

    monkeypatch.setattr(attempt.os, "fsync", fail_prediction_fsync)
    with pytest.raises(OSError, match="synthetic fsync"):
        _durable_run(attempt, directory, case)
    assert case.calls["forecast"] == [case.targets[0]]
    assert case.calls["reveal"] == []
    assert paths["claim"].exists()
    assert not paths["json"].exists()
    before = {path.name: path.read_bytes() for path in directory.iterdir()}
    with pytest.raises(attempt.AttemptError):
        _durable_run(attempt, directory, case)
    assert before == {path.name: path.read_bytes() for path in directory.iterdir()}
    assert case.calls["forecast"] == [case.targets[0]]


def test_durable_ledger_append_is_poisoned_after_failed_fsync(
    attempt, monkeypatch, tmp_path
):
    ledger = attempt.DurableLedger(
        tmp_path / "synthetic.ledger.jsonl", {"fixture": True}
    )
    fsync_calls = []

    def fail_fsync(descriptor):
        fsync_calls.append(descriptor)
        raise OSError("synthetic fsync failure")

    monkeypatch.setattr(attempt.os, "fsync", fail_fsync)
    with pytest.raises(OSError):
        ledger.append("synthetic_fixture_event", {"value": 1})
    with pytest.raises(attempt.AttemptError):
        ledger.append("synthetic_fixture_event", {"value": 2})
    assert len(fsync_calls) == 1
    ledger.close()


@pytest.mark.parametrize("target_order", ["duplicate", "reversed"])
def test_durable_invalid_target_sequence_stops_before_prefix_forecast_or_reveal(
    attempt, tmp_path, target_order
):
    case = _durable_case()
    targets = (
        (case.targets[0], case.targets[0])
        if target_order == "duplicate"
        else case.targets[::-1]
    )
    with pytest.raises(attempt.AttemptError, match="target dates"):
        _durable_run(attempt, tmp_path / target_order, case, targets=targets)
    assert all(
        not case.calls[key] for key in ("prefix", "forecast", "reveal", "notify")
    )


@pytest.mark.parametrize("prefix_kind", ["target", "future", "duplicate", "reversed"])
def test_durable_bad_prefix_never_forecasts_or_reveals(attempt, tmp_path, prefix_kind):
    case = _durable_case()
    first, second = case.targets
    bad = {
        "target": (case.base, case.actual[first]),
        "future": (case.base, case.actual[second]),
        "duplicate": (case.base, case.base),
        "reversed": (case.actual[first], case.base),
    }[prefix_kind]
    with pytest.raises(attempt.AttemptError, match="prefix"):
        _durable_run(
            attempt, tmp_path / prefix_kind, case, prefix_for=lambda _target: bad
        )
    assert case.calls["forecast"] == case.calls["reveal"] == case.calls["notify"] == []


@pytest.mark.parametrize(
    "malformation", ["empty", "incomplete", "wrong_order", "wrong_ranking"]
)
def test_durable_malformed_frozen_forecasts_are_rejected_before_reveal(
    attempt, tmp_path, malformation
):
    case = _durable_case()

    def forecast(prefix, target):
        predictions = case.forecast(prefix, target)
        if malformation == "empty":
            return []
        if malformation == "incomplete":
            return predictions[:3]
        if malformation == "wrong_order":
            return predictions[::-1]
        predictions[0]["ranking"] = predictions[0]["ranking"][::-1]
        return predictions

    with pytest.raises(ValueError):
        _durable_run(attempt, tmp_path / malformation, case, forecast=forecast)
    assert case.calls["forecast"] == [case.targets[0]]
    assert case.calls["reveal"] == []
    events = _durable_events(attempt, tmp_path / malformation)
    assert not any(event["event_kind"] == "prediction_frozen" for event in events)


def test_durable_reveal_error_consumes_synthetic_attempt_without_recalculation(
    attempt, tmp_path
):
    case = _durable_case()
    directory = tmp_path / "reveal-error"

    def reveal(target):
        case.calls["reveal"].append(target)
        raise RuntimeError("synthetic reveal failure")

    with pytest.raises(RuntimeError, match="synthetic reveal failure"):
        _durable_run(attempt, directory, case, reveal=reveal)
    assert case.calls["forecast"] == case.calls["reveal"] == [case.targets[0]]
    audit = attempt.audit_ledger(attempt._paths(directory, synthetic=True)["ledger"])
    assert audit["pending_forecast"] is True
    assert audit["scored_target_count"] == 0
    with pytest.raises(attempt.AttemptError):
        _durable_run(attempt, directory, case)
    assert case.calls["forecast"] == [case.targets[0]]


def test_durable_exact_final6_stops_before_next_prefix_and_notifies_once(
    attempt, tmp_path
):
    case = _durable_case(first_main=(1, 2, 3, 4, 5, 6))
    directory = tmp_path / "synthetic-exact-final6"
    report = _durable_run(attempt, directory, case)
    assert all(
        case.calls[key] == [case.targets[0]] for key in ("prefix", "forecast", "reveal")
    )
    assert len(case.calls["notify"]) == 1
    subject, body = case.calls["notify"][0]
    assert "历史诊断/审计候选、不可晋升" in subject
    assert "训练截止：2019-12-28" in body
    assert report["disposition"] == "pending_audit"
    assert report["gates"] is None
    assert report["processed_target_count"] == 1
    assert len(report["targets"][0]["exact_final6_opportunities"]) == 1
    assert (
        len(
            report["targets"][0]["exact_final6_opportunities"][0][
                "producer_model_names"
            ]
        )
        == 4
    )
    kinds = [event["event_kind"] for event in _durable_events(attempt, directory)]
    assert kinds.count("historical_6of6_candidate_detected") == 1
    assert (
        kinds.index("target_revealed_scored")
        < kinds.index("historical_6of6_candidate_detected")
        < kinds.index("notification_attempt_started")
    )
    assert (
        kinds.count("notification_attempt_started")
        == kinds.count("notification_attempt_finished")
        == 1
    )


@pytest.mark.parametrize("notification_fails", [False, True])
def test_durable_top12_one_notification_continues_without_reforecast(
    attempt, tmp_path, notification_fails
):
    case = _durable_case(first_main=(7, 8, 9, 10, 11, 12))
    directory = tmp_path / "synthetic-top12"

    def notify(subject, body):
        case.calls["notify"].append((subject, body))
        events = _durable_events(attempt, directory)
        assert events[-1]["event_kind"] == "notification_attempt_started"
        assert any(
            event["event_kind"] == "historical_top12_all_six_detected"
            for event in events
        )
        if notification_fails:
            raise RuntimeError("synthetic-private-notification-detail")
        return True

    report = _durable_run(attempt, directory, case, notify=notify)
    assert case.calls["forecast"] == case.calls["reveal"] == list(case.targets)
    assert len(case.calls["notify"]) == 1
    assert report["processed_target_count"] == 2
    assert report["stop_reason"] is None
    kinds = [event["event_kind"] for event in _durable_events(attempt, directory)]
    assert kinds.count("historical_top12_all_six_detected") == 1
    assert (
        kinds.count("notification_attempt_started")
        == kinds.count("notification_attempt_finished")
        == 1
    )
    assert "historical_6of6_candidate_detected" not in kinds
    expected_warnings = (
        ["notification_not_sent:2020-01-01"] if notification_fails else []
    )
    assert report["audit"]["warnings"] == expected_warnings
    assert "synthetic-private-notification-detail" not in json.dumps(report)


@pytest.mark.parametrize("directory_kind", ["reserved", "inside_repository"])
def test_durable_synthetic_path_cannot_enter_canonical_repository(
    attempt, tmp_path, directory_kind
):
    case = _durable_case()
    if directory_kind == "reserved":
        directory = tmp_path / "reports"
    else:
        repository = tmp_path / "synthetic-repository"
        (repository / ".git").mkdir(parents=True)
        directory = repository / "temporary-output"
    with pytest.raises(attempt.AttemptError):
        _durable_run(attempt, directory, case)
    assert not directory.exists()
    assert all(not values for values in case.calls.values())


@pytest.mark.parametrize(
    "identity",
    ["R3", "R1", "HISTORY_AUTHORITY", "LEASE_REF", "REPOSITORY", "AUTHORIZATION_PATH"],
)
def test_durable_synthetic_bindings_cannot_impersonate_registered_authority(
    attempt, tmp_path, identity
):
    case = _durable_case()
    directory = tmp_path / "invalid-bindings"
    value = getattr(attempt, identity)
    with pytest.raises(attempt.AttemptError, match="impersonate"):
        _durable_run(attempt, directory, case, bindings={"nested": {"identity": value}})
    assert not directory.exists()
    assert all(not values for values in case.calls.values())


def test_durable_synthetic_artifacts_are_marked_and_have_no_git_authority(
    attempt, tmp_path
):
    case = _durable_case()
    directory = tmp_path / "synthetic-artifacts"
    report = _durable_run(attempt, directory, case)
    paths = attempt._paths(directory, synthetic=True)
    assert report["classification"] == "synthetic_fixture_only"
    assert report["eligible_evidence"] is False
    assert all(path.name.startswith("synthetic_") for path in paths.values())
    manifest = json.loads(paths["commit"].read_bytes())
    assert manifest["classification"] == "synthetic_fixture_only"
    assert manifest["git_commit"] is None
    assert paths["markdown"].read_bytes().startswith(b"# SYNTHETIC FIXTURE ONLY\n")
    assert all(
        event["bindings"]["classification"] == "synthetic_fixture_only"
        for event in _durable_events(attempt, directory)
    )


def test_durable_repeat_does_not_overwrite_any_artifact(attempt, tmp_path):
    case = _durable_case()
    directory = tmp_path / "no-overwrite"
    _durable_run(attempt, directory, case)
    before = {path.name: path.read_bytes() for path in directory.iterdir()}
    with pytest.raises(attempt.AttemptError):
        _durable_run(attempt, directory, case)
    assert {path.name: path.read_bytes() for path in directory.iterdir()} == before
    assert case.calls["forecast"] == list(case.targets)


def test_durable_exclusive_ledger_and_publication_keep_existing_bytes(
    attempt, tmp_path
):
    path = tmp_path / "synthetic-existing.ledger.jsonl"
    original = b"synthetic-owned-original\n"
    path.write_bytes(original)
    with pytest.raises(FileExistsError):
        attempt.DurableLedger(path, {"fixture": True})
    assert path.read_bytes() == original
    staging = tmp_path / "synthetic.json.staging"
    destination = tmp_path / "synthetic.json"
    destination.write_bytes(original)
    with pytest.raises(FileExistsError):
        attempt._publish_exclusive(staging, destination, b"synthetic-new\n")
    assert destination.read_bytes() == original
    assert staging.read_bytes() == b"synthetic-new\n"


@pytest.mark.parametrize(
    "tamper",
    ["payload", "sequence", "previous_hash", "duplicate_event", "missing_final_lf"],
)
def test_durable_hash_chain_rejects_tampered_synthetic_bytes(attempt, tmp_path, tamper):
    path = tmp_path / "synthetic-chain.jsonl"
    ledger = attempt.DurableLedger(path, {"fixture": True})
    ledger.append("synthetic_fixture_event", {"value": 1})
    ledger.append("synthetic_fixture_event", {"value": 2})
    ledger.close()
    assert attempt.audit_ledger(path)["event_count"] == 2
    original = path.read_bytes()
    if tamper == "missing_final_lf":
        changed = original[:-1]
    elif tamper == "duplicate_event":
        changed = original + original.splitlines(keepends=True)[-1]
    else:
        events = [json.loads(line) for line in original.splitlines()]
        if tamper == "payload":
            events[1]["payload"]["value"] = 3
        elif tamper == "sequence":
            events[1]["sequence"] = 99
        else:
            events[1]["previous_event_sha256"] = "0" * 64
        changed = b"".join(attempt._canonical(event) + b"\n" for event in events)
    path.write_bytes(changed)
    with pytest.raises(attempt.AttemptError):
        attempt.audit_ledger(path)


def test_durable_auditor_rejects_reveal_without_frozen_prediction(attempt, tmp_path):
    path = tmp_path / "synthetic-unfrozen-reveal.jsonl"
    ledger = attempt.DurableLedger(path, {"fixture": True})
    ledger.append(
        "target_revealed_scored",
        {"target_draw_date": "2020-01-01", "forecast_payload_sha256": "a" * 64},
    )
    ledger.close()
    with pytest.raises(attempt.AttemptError, match="reveal lacks"):
        attempt.audit_ledger(path)


def test_durable_auditor_rejects_rehashed_reverse_target_order(attempt, tmp_path):
    path = tmp_path / "synthetic-reverse-targets.jsonl"
    ledger = attempt.DurableLedger(path, {"fixture": True})
    for target in ("2020-01-04", "2020-01-01"):
        frozen = {"target_draw_date": target, "history_through": "2019-12-28"}
        digest = attempt._sha(attempt._canonical(frozen) + b"\n")
        ledger.append(
            "prediction_frozen",
            {"forecast_payload": frozen, "forecast_payload_sha256": digest},
        )
        ledger.append(
            "target_revealed_scored",
            {"target_draw_date": target, "forecast_payload_sha256": digest},
        )
    ledger.close()
    with pytest.raises(attempt.AttemptError):
        attempt.audit_ledger(path)


def test_registered_git_reader_accepts_clean_independent_synthetic_repository(
    attempt, launcher_repository
):
    attempt.GitRepository(launcher_repository).require_full_clean()


@pytest.mark.parametrize(
    "relative",
    [
        "info/grafts",
        "objects/info/alternates",
        "objects/info/http-alternates",
        "shallow",
    ],
)
def test_registered_git_reader_rejects_grafts_alternates_and_shallow_metadata(
    attempt, launcher_repository, relative
):
    path = launcher_repository / ".git" / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"")
    with pytest.raises(attempt.AuthorizationError, match="prohibited"):
        attempt.GitRepository(launcher_repository).require_full_clean()


@pytest.mark.parametrize(
    "key,value",
    [
        ("core.sshCommand", "synthetic-command"),
        ("core.fsmonitor", "synthetic-command"),
        ("core.hooksPath", "/synthetic-hooks"),
        ("include.path", "/synthetic-config"),
        ("filter.synthetic.smudge", "synthetic-command"),
    ],
)
def test_registered_git_reader_rejects_unregistered_local_configuration(
    attempt, launcher_repository, key, value
):
    _fixture_git(launcher_repository, "config", "--local", key, value)
    with pytest.raises(attempt.AuthorizationError, match="local Git configuration"):
        attempt.GitRepository(launcher_repository).require_full_clean()


def test_registered_git_reader_rejects_dirty_worktree(attempt, launcher_repository):
    (launcher_repository / "synthetic-untracked.txt").write_text("synthetic")
    with pytest.raises(attempt.AuthorizationError):
        attempt.GitRepository(launcher_repository).require_full_clean()


@pytest.fixture
def remote_repository_evidence(attempt):
    responses = {
        "": {
            "node_id": attempt.REPOSITORY_NODE_ID,
            "full_name": attempt.REPOSITORY,
            "default_branch": "main",
            "private": False,
        },
        "/hash-algorithm": {"hash_algorithm": "sha1"},
        "/branches/main/protection": {
            "enforce_admins": {"enabled": True},
            "allow_force_pushes": {"enabled": False},
            "allow_deletions": {"enabled": False},
        },
        "/git/ref/heads/main": {
            "ref": "refs/heads/main",
            "object": {"sha": "a" * 40, "type": "commit"},
        },
    }

    class SyntheticApi:
        def request_json(self, method, path):
            assert method == "GET"
            return copy.deepcopy(responses[path.removeprefix(attempt._API_PREFIX)])

    return SimpleNamespace(responses=responses, api=SyntheticApi())


def test_remote_repository_identity_protection_and_complete_main_sha(
    attempt, remote_repository_evidence
):
    attempt._remote_protection(remote_repository_evidence.api)
    assert attempt._remote_main(remote_repository_evidence.api) == "a" * 40


@pytest.mark.parametrize(
    "field", ["enforce_admins", "allow_force_pushes", "allow_deletions"]
)
def test_each_remote_main_protection_must_hold(
    attempt, remote_repository_evidence, field
):
    protection = remote_repository_evidence.responses["/branches/main/protection"]
    protection[field]["enabled"] = not protection[field]["enabled"]
    with pytest.raises(attempt.AuthorizationError, match="protection"):
        attempt._remote_protection(remote_repository_evidence.api)


@pytest.mark.parametrize(
    "field,value",
    [
        ("node_id", "synthetic-other-node"),
        ("full_name", "synthetic/other"),
        ("default_branch", "synthetic-branch"),
        ("private", True),
    ],
)
def test_remote_repository_cannot_be_substituted(
    attempt, remote_repository_evidence, field, value
):
    remote_repository_evidence.responses[""][field] = value
    with pytest.raises(attempt.AuthorizationError, match="repository identity"):
        attempt._remote_protection(remote_repository_evidence.api)


def test_remote_main_ref_requires_full_sha(attempt, remote_repository_evidence):
    remote_repository_evidence.responses["/git/ref/heads/main"]["object"]["sha"] = (
        "a" * 7
    )
    with pytest.raises(attempt.AuthorizationError):
        attempt._remote_main(remote_repository_evidence.api)


@pytest.mark.parametrize(
    "source",
    [
        "import subprocess as s\ns.run(['python', '-c', 'import lotto649.unregistered'])",
        "import os\nos.system('python -c synthetic')",
        "from subprocess import run as execute\nexecute(['python', '-c', 'synthetic'])",
        "from importlib.metadata import distributions\nnext(distributions()).entry_points[0].load()",
    ],
)
def test_source_closure_refuses_process_and_entrypoint_import_bypasses(attempt, source):
    with pytest.raises(attempt.AuthorizationError):
        attempt._check_source_safety(
            "src/lotto649/synthetic_module.py", ast.parse(source)
        )


@pytest.mark.parametrize(
    "source",
    [
        "import operator\nloader = operator.attrgetter('__class__.__init__.__globals__')(obj)",
        "from operator import attrgetter as access\naccess('__class__')(obj)",
        "import operator\noperator.methodcaller('__getattribute__', '__class__')(obj)",
        "from operator import methodcaller as invoke\ninvoke('__getattribute__','__class__')(obj)",
        "import types\nf = types.FunctionType(code, environment)",
        "from types import FunctionType as build\nf = build(code, environment)",
        "import pandas as pd\npd.eval(payload)",
        "module.exec(payload)",
        "module.compile(payload)",
        "from typing import get_type_hints as resolve\nresolve(obj)",
        "import typing\ntyping.get_type_hints(obj)",
    ],
)
def test_source_closure_refuses_indirect_reflection_constructors(attempt, source):
    with pytest.raises(attempt.AuthorizationError):
        attempt._check_source_safety(
            "src/lotto649/synthetic_module.py", ast.parse(source)
        )


def test_late_integrity_failure_after_exact_hit_archives_but_retains_audit_requirement(
    attempt, monkeypatch, tmp_path
):
    original = attempt._drive_sequence

    def inject_late_failure(*args, **kwargs):
        rows, warnings, reason = original(*args, **kwargs)
        assert reason == "exact_final6_pending_independent_audit"
        return (
            rows,
            [*warnings, "synthetic_late_integrity_failure"],
            "Archive_after_claim_failure_no_retry",
        )

    monkeypatch.setattr(attempt, "_drive_sequence", inject_late_failure)
    case = _durable_case(first_main=(1, 2, 3, 4, 5, 6))
    report = _durable_run(attempt, tmp_path / "synthetic-late-failure", case)
    assert report["disposition"] == "Archive"
    assert report["independent_leakage_audit"] == "pending"
    assert report["audit"]["complete"] is False
    assert report["targets"][0]["exact_final6_opportunities"]
    assert report["eligible_evidence"] is False
    assert case.calls["forecast"] == [case.targets[0]]
    handoff = report["candidate_audit_handoff"]
    assert handoff["status"] == "independent_audit_pending"
    assert handoff["write_policy"] == "write_once_only_after_independent_audit"
    assert handoff["target_draw_date"] == case.targets[0].isoformat()
    assert "synthetic" in handoff["report_path_after_audit"]
    assert not list(tmp_path.rglob("historical-6of6-candidate__*"))


@pytest.mark.parametrize(
    "source",
    [
        "import typing\nref = typing.ForwardRef(\"__import__('lotto649.synthetic_hidden')\")\nref._evaluate({}, {}, recursive_guard=frozenset())",
        "from typing import ForwardRef\nForwardRef(\"__import__('lotto649.synthetic_hidden')\")._evaluate({}, {}, recursive_guard=frozenset())",
        "from typing import ForwardRef as make_ref\nmake_ref(payload)",
    ],
)
def test_type_annotation_evaluation_cannot_hide_a_dynamic_import(attempt, source):
    with pytest.raises(attempt.AuthorizationError):
        attempt._check_source_safety(
            "src/lotto649/synthetic_module.py", ast.parse(source)
        )


@pytest.mark.parametrize(
    "member",
    [
        "execl",
        "execlp",
        "execle",
        "execv",
        "execvp",
        "execvpe",
        "execve",
        "posix_spawn",
        "posix_spawnp",
        "spawnl",
        "spawnlp",
        "spawnle",
        "spawnlpe",
        "spawnv",
        "spawnvp",
        "spawnve",
        "spawnvpe",
        "startfile",
        "system",
        "popen",
    ],
)
@pytest.mark.parametrize("aliased", [False, True])
def test_os_execution_members_require_exact_registered_capabilities(
    attempt, member, aliased
):
    source = (
        f"from os import {member} as launch\nlaunch(payload)"
        if aliased
        else f"import os\nos.{member}(payload)"
    )
    with pytest.raises(attempt.AuthorizationError):
        attempt._check_source_safety(
            "src/lotto649/synthetic_module.py", ast.parse(source)
        )


@pytest.mark.parametrize(
    "source",
    [
        "import os\nescaped = os\nescaped.execl(payload)",
        "import os\nescaped = [os][0]\nescaped.posix_spawn(payload)",
        "import os\nget_os = lambda: os\nget_os().execl(payload)",
        "import typing\nescaped = typing\nescaped.ForwardRef(payload)",
        "import os\nmember = os.path.os\nmember.execl(payload)",
    ],
)
def test_registered_module_objects_cannot_escape_member_capability_checks(
    attempt, source
):
    with pytest.raises(attempt.AuthorizationError):
        attempt._check_source_safety(
            "src/lotto649/synthetic_module.py", ast.parse(source)
        )


@pytest.mark.parametrize(
    "source",
    [
        "try:\n    1 / 0\nexcept Exception as error:\n    error.__traceback__.tb_frame.f_globals['__builtins__']['__import__']('lotto649.synthetic_hidden')",
        "generator = (None for _ in ())\ngenerator.gi_frame.f_globals['__builtins__']['__import__']('lotto649.synthetic_hidden')",
        "coroutine.cr_frame.f_globals['__builtins__']['__import__']('lotto649.synthetic_hidden')",
    ],
)
def test_frame_reflection_cannot_introduce_unregistered_code_without_imports(
    attempt, source
):
    with pytest.raises(attempt.AuthorizationError):
        attempt._check_source_safety(
            "src/lotto649/synthetic_module.py", ast.parse(source)
        )


@pytest.mark.parametrize(
    "source",
    [
        "from lotto649.notification import os\nos.execl(payload)",
        "from .notification import os as escaped\nescaped.execl(payload)",
        "import os\nos = hidden_provider()\nos.path.lexists(payload)",
        "import os\ndef wrapper(os):\n    return os.path.lexists(payload)",
        "from pathlib import Path\nPath = hidden_provider()\nPath(payload)",
    ],
)
def test_registered_capabilities_cannot_be_reexported_or_rebound(attempt, source):
    with pytest.raises(attempt.AuthorizationError):
        attempt._check_source_safety(
            "src/lotto649/synthetic_module.py", ast.parse(source)
        )


def test_isolated_venv_never_inherits_system_site_packages(
    launcher, monkeypatch, tmp_path
):
    prefix = tmp_path / "synthetic-frozen-venv"
    prefix.mkdir()
    (prefix / "pyvenv.cfg").write_text("# Synthetic venv marker.\n")
    runtime = _launcher_sys()
    runtime.executable = str(prefix / "bin/python3.12")
    runtime.version_info = SimpleNamespace(major=3, minor=12)
    monkeypatch.setitem(launcher, "sys", runtime)
    calls = []
    monkeypatch.setitem(
        launcher,
        "sysconfig",
        SimpleNamespace(
            get_path=lambda key: calls.append(key) or "/synthetic-system-packages"
        ),
    )
    assert launcher["_runtime_search_paths"]() == [
        prefix / "lib/python3.12/site-packages",
        prefix / "Lib/site-packages",
    ]
    assert calls == []


def test_base_interpreter_uses_only_its_sysconfig_paths(
    launcher, monkeypatch, tmp_path
):
    runtime = _launcher_sys()
    runtime.executable = str(tmp_path / "synthetic-base/bin/python3.12")
    runtime.version_info = SimpleNamespace(major=3, minor=12)
    monkeypatch.setitem(launcher, "sys", runtime)
    paths = {"purelib": "/synthetic/base/purelib", "platlib": "/synthetic/base/platlib"}
    monkeypatch.setitem(launcher, "sysconfig", SimpleNamespace(get_path=paths.get))
    assert launcher["_runtime_search_paths"]() == [
        Path(value) for value in paths.values()
    ]


# R3 additions below use independently fabricated metadata and fail guards.  The
# fixture does not observe a server or invoke a canonical attempt.


def _canonical_fixture(value):
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


@pytest.fixture
def projection():
    return json.loads(
        (ROOT / "tests/fixtures/v12_0_2_git_commit_projection.json").read_bytes()
    )


@pytest.fixture(autouse=True)
def forbid_production_execution_and_network(monkeypatch, attempt):
    def forbidden(*_args, **_kwargs):
        pytest.fail(
            "I3 synthetic tests must not create production authority or read history"
        )

    monkeypatch.setattr(attempt, "_run_canonical", forbidden)
    monkeypatch.setattr(attempt, "_load_governed_history", forbidden)
    monkeypatch.setattr(attempt, "_issue_authorization", forbidden)
    import requests

    monkeypatch.setattr(requests.sessions.Session, "request", forbidden)


def test_independent_projection_fixture_raw_git_and_request_oracles(projection):
    raw = projection["raw_commit_utf8"].encode("utf-8")
    body = _canonical_fixture(projection["canonical_body"])
    assert projection["classification"] == "synthetic_fixture_only"
    assert projection["canonical_body_utf8"].encode() == body
    assert len(raw) == projection["raw_commit_byte_count"]
    assert (
        hashlib.sha1(b"commit " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        == projection["raw_commit_sha1"]
    )
    assert hashlib.sha256(raw).hexdigest() == projection["raw_commit_sha256"]
    headers, message = raw.split(b"\n\n", 1)
    assert [line.split(b" ", 1)[0] for line in headers.splitlines()] == [
        b"tree",
        b"parent",
        b"author",
        b"committer",
    ]
    assert message == body + b"\n"
    assert projection["post_commit_request"]["message"].encode() == body + b"\n"
    assert projection["get_commit_response"]["message"].encode() == body
    sent = _canonical_fixture(projection["post_commit_request"])
    assert len(sent) == projection["post_commit_request_byte_count"]
    assert hashlib.sha256(sent).hexdigest() == projection["post_commit_request_sha256"]
    assert (
        projection["post_commit_response"]["sha"]
        == projection["get_commit_response"]["sha"]
        == projection["raw_commit_sha1"]
    )


def test_lease_raw_constructor_matches_independent_fixed_oracle(attempt, projection):
    class SyntheticGit:
        def run(self, *arguments):
            assert arguments == ("cat-file", "commit", projection["execution_commit"])
            return projection["execution_commit_raw"].encode()

        def tree(self, commit):
            assert commit == projection["execution_commit"]
            return projection["execution_tree"]

    inert_metadata = SimpleNamespace(
        execution_commit=projection["execution_commit"],
        authorization_sha256=projection["authorization_seal_sha256"],
    )
    oid, raw, payload = attempt._lease_commit(
        SyntheticGit(), inert_metadata, projection["nonce_hex"]
    )
    assert oid == projection["raw_commit_sha1"]
    assert raw == projection["raw_commit_utf8"].encode()
    assert payload == projection["post_commit_request"]


def _verify_projection(attempt, projection, observed=None):
    attempt._verify_lease_object(
        projection["get_commit_response"] if observed is None else observed,
        projection["raw_commit_sha1"],
        projection["raw_commit_utf8"].encode(),
        projection["post_commit_request"],
    )


def test_get_projection_accepts_only_registered_no_lf_message(attempt, projection):
    _verify_projection(attempt, projection)


@pytest.mark.parametrize(
    "change", ["lf", "two_lf", "crlf", "space", "indent", "noncanonical"]
)
def test_get_projection_never_trims_or_accepts_another_message_form(
    attempt, projection, change
):
    observed = copy.deepcopy(projection["get_commit_response"])
    original = observed["message"]
    observed["message"] = {
        "lf": original + "\n",
        "two_lf": original + "\n\n",
        "crlf": original + "\r\n",
        "space": original + " ",
        "indent": " " + original,
        "noncanonical": json.dumps(projection["canonical_body"], sort_keys=True),
    }[change]
    with pytest.raises(attempt.AuthorizationError):
        _verify_projection(attempt, projection, observed)


_GET_OBJECT_PATHS = [
    (),
    ("author",),
    ("committer",),
    ("tree",),
    ("parents", 0),
    ("verification",),
]


def _at_path(value, path):
    for key in path:
        value = value[key]
    return value


@pytest.mark.parametrize("path", _GET_OBJECT_PATHS)
@pytest.mark.parametrize("change", ["unknown", "missing"])
def test_get_projection_rejects_unknown_or_missing_key_at_every_object_depth(
    attempt, projection, path, change
):
    observed = copy.deepcopy(projection["get_commit_response"])
    target = _at_path(observed, path)
    if change == "unknown":
        target["unregistered_field"] = "synthetic-private-server-text"
    else:
        target.pop(next(iter(target)))
    with pytest.raises(attempt.AuthorizationError):
        _verify_projection(attempt, projection, observed)


@pytest.mark.parametrize(
    "path,value",
    [
        (("sha",), "e" * 40),
        (("sha",), "F" * 40),
        (("sha",), "f9d38cc"),
        (("node_id",), ""),
        (("node_id",), 1),
        (("url",), "https://evil.invalid/commit"),
        (("html_url",), "http://github.com/Jasper-Shi/lottopred/commit/"),
        (("tree", "sha"), "e" * 40),
        (
            ("tree", "url"),
            "https://api.github.com/repos/other/repo/git/trees/" + "b" * 40,
        ),
        (("author", "name"), "Wrong"),
        (("committer", "email"), "wrong@example.invalid"),
        (("author", "date"), "2023-11-14T22:13:20+00:00"),
        (("committer", "date"), "2023-11-14T22:13:20.000000Z"),
        (("parents",), []),
        (("parents",), ["6" * 40]),
        (("parents", 0, "sha"), "e" * 40),
        (
            ("parents", 0, "url"),
            "https://api.github.com/repos/Jasper-Shi/lottopred/git/commits/" + "e" * 40,
        ),
        (("verification", "verified"), 0),
        (("verification", "verified"), True),
        (("verification", "reason"), "valid"),
        (("verification", "signature"), ""),
        (("verification", "payload"), ""),
        (("verification", "verified_at"), "2023-11-14T22:13:20Z"),
        (("message",), None),
        (("message",), 1),
    ],
)
def test_get_projection_binds_exact_types_identity_dates_urls_and_unsigned_state(
    attempt, projection, path, value
):
    observed = copy.deepcopy(projection["get_commit_response"])
    _at_path(observed, path[:-1])[path[-1]] = value
    with pytest.raises(attempt.AuthorizationError):
        _verify_projection(attempt, projection, observed)


@pytest.mark.parametrize("mutation", ["message", "header", "lf", "parent", "signature"])
def test_get_projection_cannot_replace_local_raw_content_address(
    attempt, projection, mutation
):
    raw = projection["raw_commit_utf8"].encode()
    if mutation == "message":
        raw = raw.replace(b'"nonce_hex":"d', b'"nonce_hex":"e', 1)
    elif mutation == "header":
        raw = raw.replace(b" +0000\n", b" -0000\n", 1)
    elif mutation == "lf":
        raw = raw[:-1]
    elif mutation == "parent":
        raw = raw.replace(b"parent " + b"6" * 40, b"parent " + b"e" * 40)
    else:
        raw = raw.replace(b"\n\n", b"\ngpgsig synthetic\n\n", 1)
    with pytest.raises(attempt.AuthorizationError):
        attempt._verify_lease_object(
            projection["get_commit_response"],
            projection["raw_commit_sha1"],
            raw,
            projection["post_commit_request"],
        )


def test_post_response_requires_oid_and_allows_typed_non_authoritative_message(
    attempt, projection
):
    for message in (
        None,
        "different display text",
        projection["canonical_body_utf8"] + "\n",
        "",
    ):
        response = dict(projection["post_commit_response"])
        if message is not None:
            response["message"] = message
        attempt._verify_lease_post_response(
            response, projection["raw_commit_sha1"], projection["post_commit_request"]
        )


@pytest.mark.parametrize(
    "response", [{}, {"sha": "e" * 40}, {"sha": True}, {"sha": "f" * 7}]
)
def test_post_response_cannot_substitute_metadata_for_expected_oid(
    attempt, projection, response
):
    with pytest.raises(attempt.AuthorizationError):
        attempt._verify_lease_post_response(
            response, projection["raw_commit_sha1"], projection["post_commit_request"]
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("message", {}),
        ("unregistered", 1),
        ("node_id", ""),
        ("verification", {"verified": False}),
        ("url", "https://evil.invalid"),
    ],
)
def test_post_response_closes_optional_metadata_schema(
    attempt, projection, field, value
):
    response = {**projection["post_commit_response"], field: value}
    with pytest.raises(attempt.AuthorizationError):
        attempt._verify_lease_post_response(
            response, projection["raw_commit_sha1"], projection["post_commit_request"]
        )


def test_ref_response_matches_independent_registered_shape(attempt, projection):
    attempt._verify_lease_ref(
        projection["get_ref_response"], projection["raw_commit_sha1"]
    )


@pytest.mark.parametrize(
    "path,value",
    [
        (("ref",), "refs/heads/v12-consumption-v12.0.1"),
        (("node_id",), ""),
        (("url",), "https://evil.invalid"),
        (("object", "sha"), "e" * 40),
        (("object", "type"), "tag"),
        (("object", "url"), "https://evil.invalid"),
    ],
)
def test_ref_response_rejects_old_lease_wrong_identity_or_url(
    attempt, projection, path, value
):
    observed = copy.deepcopy(projection["get_ref_response"])
    _at_path(observed, path[:-1])[path[-1]] = value
    with pytest.raises(attempt.AuthorizationError):
        attempt._verify_lease_ref(observed, projection["raw_commit_sha1"])


@pytest.mark.parametrize("path", [(), ("object",)])
@pytest.mark.parametrize("change", ["unknown", "missing"])
def test_ref_response_schema_is_closed_at_each_depth(attempt, projection, path, change):
    observed = copy.deepcopy(projection["get_ref_response"])
    target = _at_path(observed, path)
    if change == "unknown":
        target["unregistered"] = True
    else:
        target.pop(next(iter(target)))
    with pytest.raises(attempt.AuthorizationError):
        attempt._verify_lease_ref(observed, projection["raw_commit_sha1"])


def _author_payload(*, phase="I3", contributors=None):
    return {
        "schema_version": "lotto649-v12-source-author-provenance-v1",
        "phase": phase,
        "contributors": contributors
        if contributors is not None
        else [
            {"agent_id": "synthetic-author", "session_id": "synthetic-author-session"}
        ],
    }


def _raw_author_commit(payload=None, *, message=None):
    if message is None:
        message = (
            b"Synthetic source only.\n\nResearch-Author-Provenance: "
            + _canonical_fixture(_author_payload() if payload is None else payload)
            + b"\n"
        )
    return (
        f"tree {'b' * 40}\nparent {'a' * 40}\nauthor Synthetic <fixture@example.invalid> 1700000000 +0000\ncommitter Synthetic <fixture@example.invalid> 1700000000 +0000\n\n".encode()
        + message
    )


@pytest.mark.parametrize("phase", ["I3", "A_H_s3"])
def test_source_author_provenance_binds_exact_raw_message_and_phase(attempt, phase):
    payload = _author_payload(phase=phase)
    assert (
        attempt._source_author_provenance(_raw_author_commit(payload), phase)
        == payload["contributors"]
    )


def test_source_author_provenance_preserves_distinct_same_agent_sessions_and_unicode(
    attempt,
):
    payload = _author_payload(
        contributors=[
            {"agent_id": "synthetic-author", "session_id": "first"},
            {"agent_id": "synthetic-author", "session_id": "second"},
            {"agent_id": "研究者", "session_id": "会话"},
        ]
    )
    assert (
        attempt._source_author_provenance(_raw_author_commit(payload), "I3")
        == payload["contributors"]
    )


@pytest.mark.parametrize(
    "malformation",
    [
        "absent",
        "two",
        "indented",
        "tab",
        "no_space",
        "double_space",
        "no_lf",
        "two_lf",
        "crlf",
        "suffix",
        "folded",
        "spaced_json",
        "invalid_utf8",
        "duplicate_key",
    ],
)
def test_source_author_trailer_rejects_ambiguous_or_normalized_message(
    attempt, malformation
):
    trailer = (
        b"Research-Author-Provenance: " + _canonical_fixture(_author_payload()) + b"\n"
    )
    malformed = {
        "absent": b"Synthetic source.\n",
        "two": trailer + trailer,
        "indented": b" " + trailer,
        "tab": b"\t" + trailer,
        "no_space": trailer.replace(b": ", b":", 1),
        "double_space": trailer.replace(b": ", b":  ", 1),
        "no_lf": trailer[:-1],
        "two_lf": trailer + b"\n",
        "crlf": trailer[:-1] + b"\r\n",
        "suffix": trailer + b"other-trailer: true\n",
        "folded": trailer.replace(b'"phase"', b'\n "phase"'),
        "spaced_json": b"Research-Author-Provenance: "
        + json.dumps(_author_payload()).encode()
        + b"\n",
        "invalid_utf8": trailer.replace(b"synthetic-author", b"\xff", 1),
        "duplicate_key": trailer.replace(b'"phase":"I3"', b'"phase":"I3","phase":"I3"'),
    }[malformation]
    with pytest.raises(attempt.AuthorizationError):
        attempt._source_author_provenance(_raw_author_commit(message=malformed), "I3")


@pytest.mark.parametrize(
    "field,value",
    [
        ("phase", "I2"),
        ("phase", "A_H_s3"),
        ("schema_version", "wrong"),
        ("contributors", []),
        ("contributors", {}),
        ("contributors", [1]),
        ("future_source_sha", "a" * 40),
    ],
)
def test_source_author_payload_has_closed_phase_and_key_contract(attempt, field, value):
    payload = _author_payload()
    payload[field] = value
    with pytest.raises(attempt.AuthorizationError):
        attempt._source_author_provenance(_raw_author_commit(payload), "I3")


@pytest.mark.parametrize("field", ["agent_id", "session_id"])
@pytest.mark.parametrize(
    "value",
    [
        "",
        " ",
        " leading",
        "trailing\t",
        "line\nbreak",
        "carriage\rreturn",
        "null\0char",
        "delete\x7fchar",
        "a" * 257,
        "中" * 86,
        None,
        1,
        True,
    ],
)
def test_source_author_identifier_preserves_strict_utf8_type_length_and_controls(
    attempt, field, value
):
    payload = _author_payload()
    payload["contributors"][0][field] = value
    with pytest.raises(attempt.AuthorizationError):
        attempt._source_author_provenance(_raw_author_commit(payload), "I3")


@pytest.mark.parametrize(
    "change", ["duplicate_pair", "unsorted", "unknown", "missing", "too_many"]
)
def test_source_author_contributors_require_complete_closed_sorted_unique_records(
    attempt, change
):
    payload = _author_payload()
    original = payload["contributors"][0]
    if change == "duplicate_pair":
        payload["contributors"].append(dict(original))
    elif change == "unsorted":
        payload["contributors"] = [
            {"agent_id": "z", "session_id": "z"},
            {"agent_id": "a", "session_id": "a"},
        ]
    elif change == "unknown":
        original["github_login"] = "not-provenance"
    elif change == "missing":
        original.pop("agent_id")
    else:
        payload["contributors"] = [
            {"agent_id": f"agent-{i:02}", "session_id": f"session-{i:02}"}
            for i in range(65)
        ]
    with pytest.raises(attempt.AuthorizationError):
        attempt._source_author_provenance(_raw_author_commit(payload), "I3")


def test_registered_git_reader_rejects_unexpected_ignored_output(
    attempt, launcher_repository
):
    (launcher_repository / ".gitignore").write_text("synthetic-ignored-output/\n")
    _fixture_git(launcher_repository, "add", ".gitignore")
    _fixture_git(
        launcher_repository, "commit", "--quiet", "-m", "synthetic ignore rule"
    )
    directory = launcher_repository / "synthetic-ignored-output"
    directory.mkdir()
    (directory / "hidden.json").write_text("{}\n")
    with pytest.raises(attempt.AuthorizationError):
        attempt.GitRepository(launcher_repository).require_full_clean()


@pytest.mark.parametrize(
    "body",
    [
        b'{"a":1,"a":2}',
        b'{"a":NaN}',
        b'{"a":Infinity}',
        b'{"a":-Infinity}',
        b"\xff",
        b"{} trailing",
    ],
)
def test_transport_rejects_duplicate_nonfinite_and_nonjson_response_without_body_leak(
    attempt, monkeypatch, body
):
    api, calls = _http_fixture(attempt, monkeypatch, _HttpResponse(body=body))
    with pytest.raises(attempt.AuthorizationError) as caught:
        api.request_json("GET", attempt._API_PREFIX)
    assert "trailing" not in str(caught.value)
    assert len(calls) == 1


@pytest.mark.parametrize(
    "path",
    [
        "/commits/" + "a" * 40 + "/pulls?per_page=100",
        "/issues/41/comments?per_page=100",
        "/commits/" + "a" * 40 + "/check-runs?per_page=100",
    ],
)
def test_review_discovery_fixed_get_routes_accept_complete_first_page(
    attempt, monkeypatch, path
):
    body = b'{"total_count":0,"check_runs":[]}' if "check-runs" in path else b"[]"
    api, calls = _http_fixture(attempt, monkeypatch, _HttpResponse(body=body))
    assert api.request_json("GET", attempt._API_PREFIX + path) == json.loads(body)
    assert len(calls) == 1
    assert calls[0][2]["timeout"] == (10, 30)
    assert calls[0][2]["allow_redirects"] is False


@pytest.mark.parametrize(
    "path",
    [
        "/commits/abc/pulls?per_page=100",
        "/commits/" + "a" * 40 + "/pulls?per_page=99",
        "/issues/41/comments?per_page=100&page=2",
        "/issues/0/comments?per_page=100",
        "/issues/41/comments",
        "/commits/" + "a" * 40 + "/check-runs?per_page=100&page=2",
    ],
)
def test_review_discovery_refuses_unregistered_parameter_or_page_before_transport(
    attempt, monkeypatch, path
):
    api, calls = _http_fixture(attempt, monkeypatch, _HttpResponse(body=b"[]"))
    with pytest.raises(attempt.AuthorizationError):
        api.request_json("GET", attempt._API_PREFIX + path)
    assert calls == []


@pytest.mark.parametrize(
    "path",
    [
        "/commits/" + "a" * 40 + "/pulls?per_page=100",
        "/issues/41/comments?per_page=100",
        "/commits/" + "a" * 40 + "/check-runs?per_page=100",
    ],
)
def test_review_discovery_next_page_is_terminal_not_followed(
    attempt, monkeypatch, path
):
    headers = {
        "Content-Type": "application/json",
        "Link": '<https://api.github.com/unregistered?page=2>; rel="next"',
    }
    api, calls = _http_fixture(
        attempt, monkeypatch, _HttpResponse(body=b"[]", headers=headers)
    )
    with pytest.raises(attempt.AuthorizationError):
        api.request_json("GET", attempt._API_PREFIX + path)
    assert len(calls) == 1


@pytest.mark.parametrize(
    "route,request_key,response_key",
    [
        ("/git/commits", "post_commit_request", "post_commit_response"),
        ("/git/refs", "post_ref_request", "post_ref_response"),
    ],
)
def test_each_post_sends_the_identical_canonical_body_bytes_once(
    attempt, monkeypatch, projection, route, request_key, response_key
):
    body = _canonical_fixture(projection[request_key])
    api, calls = _http_fixture(
        attempt,
        monkeypatch,
        _HttpResponse(status=201, body=_canonical_fixture(projection[response_key])),
    )
    result = api.request_json("POST", attempt._API_PREFIX + route, body_bytes=body)
    assert result == projection[response_key]
    assert len(calls) == 1
    assert calls[0][2]["data"] is body
    assert "json" not in calls[0][2]
    assert api.last_status == 201
    with pytest.raises(attempt.AuthorizationError):
        api.request_json("POST", attempt._API_PREFIX + route, body_bytes=body)
    assert len(calls) == 1


@pytest.mark.parametrize(
    "route,request_key",
    [("/git/commits", "post_commit_request"), ("/git/refs", "post_ref_request")],
)
def test_uncertain_post_is_poisoned_before_transport_and_cannot_retry(
    attempt, monkeypatch, projection, route, request_key
):
    body = _canonical_fixture(projection[request_key])
    api, calls = _http_fixture(
        attempt, monkeypatch, OSError("synthetic-private-transport-body")
    )
    with pytest.raises(attempt.AuthorizationError) as caught:
        api.request_json("POST", attempt._API_PREFIX + route, body_bytes=body)
    assert "synthetic-private" not in str(caught.value)
    assert caught.value.result_enum == "transport_failed"
    assert caught.value.http_status is None
    with pytest.raises(attempt.AuthorizationError):
        api.request_json("POST", attempt._API_PREFIX + route, body_bytes=body)
    assert len(calls) == 1


@pytest.mark.parametrize(
    "mutation",
    ["lf", "spaced", "duplicate", "nonfinite", "signature", "extra", "wrong_parents"],
)
def test_post_requires_exact_finite_closed_canonical_request_before_transport(
    attempt, monkeypatch, projection, mutation
):
    payload = copy.deepcopy(projection["post_commit_request"])
    body = _canonical_fixture(payload)
    if mutation == "lf":
        body += b"\n"
    elif mutation == "spaced":
        body = json.dumps(payload).encode()
    elif mutation == "duplicate":
        body = body[:-1] + b',"tree":"' + b"b" * 40 + b'"}'
    elif mutation == "nonfinite":
        body = body[:-1] + b',"unknown":NaN}'
    elif mutation == "signature":
        payload["signature"] = "synthetic"
        body = _canonical_fixture(payload)
    elif mutation == "extra":
        payload["unregistered"] = True
        body = _canonical_fixture(payload)
    else:
        payload["parents"] = ["6" * 40, "4" * 40]
        body = _canonical_fixture(payload)
    api, calls = _http_fixture(attempt, monkeypatch, _HttpResponse(status=201))
    with pytest.raises(attempt.AuthorizationError):
        api.request_json("POST", attempt._API_PREFIX + "/git/commits", body_bytes=body)
    assert calls == []


@pytest.mark.parametrize("status", [True, 99, 600, "201", None])
def test_http_status_type_and_range_never_enter_a_safe_receipt(
    attempt, monkeypatch, status
):
    api, calls = _http_fixture(attempt, monkeypatch, _HttpResponse(status=status))
    with pytest.raises(attempt.AuthorizationError) as caught:
        api.request_json("GET", attempt._API_PREFIX)
    assert caught.value.http_status is None
    assert len(calls) == 1


def _synthetic_startup(attempt, directory):
    return attempt.StartupJournal.for_synthetic(
        directory.resolve(), {"synthetic_fixture_only": True}
    )


def _startup_events(journal):
    raw = journal.path.read_bytes()
    assert raw.endswith(b"\n")
    return [json.loads(line) for line in raw.splitlines()]


def _startup_to_checkpoint(attempt, directory, projection):
    journal = _synthetic_startup(attempt, directory)
    journal.append("capability_issued", {})
    journal.append("lease_absence_confirmed", {"http_status": 404})
    nonce, oid, raw_sha = (
        projection["nonce_hex"],
        projection["raw_commit_sha1"],
        projection["raw_commit_sha256"],
    )
    journal.intent(
        "lease_commit",
        nonce,
        oid,
        raw_sha,
        _canonical_fixture(projection["post_commit_request"]),
    )
    journal.receipt("lease_commit", "success", 201, oid)
    journal.append("lease_commit_GET_verified", {"validated_oid": oid})
    journal.intent(
        "lease_ref",
        nonce,
        oid,
        raw_sha,
        _canonical_fixture(projection["post_ref_request"]),
    )
    journal.receipt("lease_ref", "success", 201, oid)
    journal.append("lease_ref_reread_verified", {"validated_oid": oid})
    checkpoint = journal.checkpoint()
    return journal, checkpoint


def test_startup_first_event_file_and_parent_fsync_precede_any_capability(
    attempt, monkeypatch, tmp_path
):
    calls = []
    real_fsync = os.fsync

    def track(descriptor):
        status = os.fstat(descriptor)
        calls.append((status.st_ino, status.st_mode))
        real_fsync(descriptor)

    monkeypatch.setattr(attempt.os, "fsync", track)
    journal = _synthetic_startup(attempt, tmp_path / "first-event")
    try:
        raw = journal.path.read_bytes()
        events = _startup_events(journal)
        assert len(events) == 1
        assert events[0]["sequence"] == 0
        assert events[0]["previous_event_sha256"] is None
        file_inode = journal.path.stat().st_ino
        parent_inode = journal.path.parent.stat().st_ino
        assert [inode for inode, _mode in calls][-2:] == [file_inode, parent_inode]
        assert journal.path.stat().st_mode & 0o777 == 0o600
        assert journal.byte_count == len(raw)
        assert journal.digest_sha256 == hashlib.sha256(raw).hexdigest()
        assert journal.head_sha256 == hashlib.sha256(raw).hexdigest()
        journal.verify_owned()
    finally:
        journal.close()


def test_startup_hash_chain_uses_complete_previous_canonical_line_including_lf(
    attempt, tmp_path
):
    journal = _synthetic_startup(attempt, tmp_path / "line-chain")
    try:
        journal.append("capability_issued", {})
        journal.append("lease_absence_confirmed", {"http_status": 404})
        lines = journal.path.read_bytes().splitlines(keepends=True)
        events = [json.loads(line) for line in lines]
        for index, (event, line) in enumerate(zip(events, lines, strict=True)):
            assert line == _canonical_fixture(event) + b"\n"
            assert event["sequence"] == index
            expected = (
                None if index == 0 else hashlib.sha256(lines[index - 1]).hexdigest()
            )
            assert event["previous_event_sha256"] == expected
            if index:
                assert (
                    event["previous_event_sha256"]
                    != hashlib.sha256(lines[index - 1][:-1]).hexdigest()
                )
        assert journal.head_sha256 == hashlib.sha256(lines[-1]).hexdigest()
        assert journal.digest_sha256 == hashlib.sha256(b"".join(lines)).hexdigest()
    finally:
        journal.close()


@pytest.mark.parametrize("operation", ["first_file", "first_parent"])
def test_startup_initial_durability_failure_preserves_bytes_and_never_issues_capability(
    attempt, monkeypatch, tmp_path, operation
):
    real_fsync = os.fsync
    count = 0

    def fail_at(descriptor):
        nonlocal count
        count += 1
        if count == (1 if operation == "first_file" else 2):
            raise OSError("synthetic-private-fsync-detail")
        real_fsync(descriptor)

    directory = (tmp_path / operation).resolve()
    monkeypatch.setattr(attempt.os, "fsync", fail_at)
    with pytest.raises((attempt.AttemptError, OSError)):
        _synthetic_startup(attempt, directory)
    files = list(directory.iterdir())
    assert len(files) == 1
    original = files[0].read_bytes()
    monkeypatch.setattr(attempt.os, "fsync", real_fsync)
    with pytest.raises((attempt.AttemptError, FileExistsError)):
        _synthetic_startup(attempt, directory)
    assert files[0].read_bytes() == original


@pytest.mark.parametrize(
    "bad", ["unknown_event", "wrong_order", "arbitrary_field", "wrong_status"]
)
def test_startup_events_are_closed_and_ordered_before_any_write(attempt, tmp_path, bad):
    journal = _synthetic_startup(attempt, tmp_path / bad)
    before = journal.path.read_bytes()
    kind, payload = {
        "unknown_event": ("print_secret", {"value": "synthetic-private-value"}),
        "wrong_order": ("history_load_intent", {}),
        "arbitrary_field": ("capability_issued", {"token": "synthetic-private-value"}),
        "wrong_status": ("lease_absence_confirmed", {"http_status": 200}),
    }[bad]
    try:
        with pytest.raises(attempt.AttemptError):
            journal.append(kind, payload)
        assert journal.path.read_bytes() == before
    finally:
        journal.close()


def test_startup_intent_binds_exact_body_bytes_and_is_durable_before_mock_post(
    attempt, monkeypatch, tmp_path, projection
):
    journal = _synthetic_startup(attempt, tmp_path / "intent-before-post")
    journal.append("capability_issued", {})
    journal.append("lease_absence_confirmed", {"http_status": 404})
    durable = []
    real_fsync = os.fsync

    def observe(descriptor):
        real_fsync(descriptor)
        if os.fstat(descriptor).st_ino == journal.path.stat().st_ino:
            durable.append(journal.path.read_bytes())

    monkeypatch.setattr(attempt.os, "fsync", observe)
    body = _canonical_fixture(projection["post_commit_request"])
    try:
        journal.intent(
            "lease_commit",
            projection["nonce_hex"],
            projection["raw_commit_sha1"],
            projection["raw_commit_sha256"],
            body,
        )
        event = json.loads(durable[-1].splitlines()[-1])
        payload = event["payload"]
        assert payload["request_body_bytes"] == len(body)
        assert payload["request_body_sha256"] == hashlib.sha256(body).hexdigest()
        assert payload["expected_lease_oid"] == projection["raw_commit_sha1"]
        assert payload["raw_commit_sha256"] == projection["raw_commit_sha256"]
        assert payload["nonce_hex"] == projection["nonce_hex"]
        assert "request_body" not in payload
        assert body not in durable[-1]
    finally:
        journal.close()


def test_startup_intent_fsync_failure_poisoned_no_post_no_repair_or_resume(
    attempt, monkeypatch, tmp_path, projection
):
    journal = _synthetic_startup(attempt, tmp_path / "intent-failed")
    journal.append("capability_issued", {})
    journal.append("lease_absence_confirmed", {"http_status": 404})
    calls = []

    def fail(descriptor):
        calls.append(descriptor)
        raise OSError("synthetic-secret-fsync-error")

    monkeypatch.setattr(attempt.os, "fsync", fail)
    arguments = (
        "lease_commit",
        projection["nonce_hex"],
        projection["raw_commit_sha1"],
        projection["raw_commit_sha256"],
        _canonical_fixture(projection["post_commit_request"]),
    )
    try:
        with pytest.raises((attempt.AttemptError, OSError)):
            journal.intent(*arguments)
        before = journal.path.read_bytes()
        with pytest.raises(attempt.AttemptError):
            journal.intent(*arguments)
        assert journal.path.read_bytes() == before
        assert len(calls) == 1
        assert b"synthetic-secret" not in before
    finally:
        journal.close()


@pytest.mark.parametrize(
    "result,status",
    [
        ("http_rejected", 403),
        ("transport_failed", None),
        ("malformed_response", 201),
        ("identity_mismatch", 201),
        ("io_failed", None),
        ("authority_failed", None),
    ],
)
def test_startup_failure_receipt_is_safe_durable_terminal_and_preserved(
    attempt, tmp_path, projection, result, status
):
    journal = _synthetic_startup(attempt, tmp_path / result)
    journal.append("capability_issued", {})
    journal.append("lease_absence_confirmed", {"http_status": 404})
    journal.intent(
        "lease_commit",
        projection["nonce_hex"],
        projection["raw_commit_sha1"],
        projection["raw_commit_sha256"],
        _canonical_fixture(projection["post_commit_request"]),
    )
    try:
        with pytest.raises(attempt.AttemptError):
            journal.receipt("lease_commit", result, status)
        payload = _startup_events(journal)[-1]["payload"]
        assert payload == {
            "phase_enum": "lease_commit",
            "result_enum": result,
            "http_status": status,
            "validated_oid": None,
        }
        before = journal.path.read_bytes()
        with pytest.raises(attempt.AttemptError):
            journal.append(
                "lease_commit_GET_verified",
                {"validated_oid": projection["raw_commit_sha1"]},
            )
        assert journal.path.read_bytes() == before
    finally:
        journal.close()


@pytest.mark.parametrize(
    "result,status,oid",
    [
        ("success", 200, None),
        ("success", 201, "e" * 40),
        ("success", True, None),
        ("private-error-text", None, None),
        ("http_rejected", 99, None),
        ("http_rejected", 600, None),
        ("http_rejected", "403", None),
        ("transport_failed", None, "e" * 40),
    ],
)
def test_startup_rejects_unsanitized_or_unvalidated_receipt_before_writing(
    attempt, tmp_path, projection, result, status, oid
):
    journal = _synthetic_startup(attempt, tmp_path / "bad-receipt")
    journal.append("capability_issued", {})
    journal.append("lease_absence_confirmed", {"http_status": 404})
    journal.intent(
        "lease_commit",
        projection["nonce_hex"],
        projection["raw_commit_sha1"],
        projection["raw_commit_sha256"],
        _canonical_fixture(projection["post_commit_request"]),
    )
    before = journal.path.read_bytes()
    try:
        with pytest.raises(attempt.AttemptError):
            journal.receipt("lease_commit", result, status, oid)
        assert journal.path.read_bytes() == before
    finally:
        journal.close()


def test_startup_checkpoint_claim_ledger_and_sealed_manifest_binding_are_acyclic(
    attempt, tmp_path, projection
):
    journal, checkpoint = _startup_to_checkpoint(
        attempt, tmp_path / "acyclic", projection
    )
    try:
        prefix = journal.path.read_bytes()
        binding = checkpoint.as_dict()
        assert set(binding) == {
            "path",
            "sequence",
            "head_sha256",
            "prefix_byte_count",
            "prefix_sha256",
        }
        assert binding["prefix_byte_count"] == len(prefix)
        assert binding["prefix_sha256"] == hashlib.sha256(prefix).hexdigest()
        assert (
            binding["head_sha256"]
            == hashlib.sha256(prefix.splitlines(keepends=True)[-1]).hexdigest()
        )
        claim = (
            _canonical_fixture(
                {"synthetic_fixture_only": True, "startup_checkpoint": binding}
            )
            + b"\n"
        )
        claim_sha = hashlib.sha256(claim).hexdigest()
        first_scientific = (
            _canonical_fixture(
                {
                    "synthetic_fixture_only": True,
                    "startup_checkpoint": binding,
                    "claim_sha256": claim_sha,
                }
            )
            + b"\n"
        )
        first_sha = hashlib.sha256(first_scientific).hexdigest()
        journal.append("claim_created", {"claim_sha256": claim_sha})
        journal.append("scientific_ledger_started", {"first_event_sha256": first_sha})
        journal.append("history_load_intent", {})
        journal.seal()
        journal.verify_owned()
        full = journal.path.read_bytes()
        assert full[: len(prefix)] == prefix
        assert checkpoint.as_dict() == binding
        assert journal.byte_count == len(full)
        assert journal.digest_sha256 == hashlib.sha256(full).hexdigest()
        assert journal.digest_sha256 != binding["prefix_sha256"]
        assert "startup_sha256" not in json.loads(claim)
        with pytest.raises(attempt.AttemptError):
            journal.append("history_load_intent", {})
        assert journal.path.read_bytes() == full
    finally:
        journal.close()


@pytest.mark.parametrize(
    "mutation", ["chmod", "replace", "hardlink", "append", "truncate", "symlink"]
)
def test_startup_ownership_rejects_foreign_identity_or_bytes_even_with_matching_name(
    attempt, tmp_path, mutation
):
    journal = _synthetic_startup(attempt, tmp_path / mutation)
    original = journal.path.read_bytes()
    if mutation == "chmod":
        journal.path.chmod(0o644)
    elif mutation == "replace":
        journal.path.unlink()
        journal.path.write_bytes(original)
        journal.path.chmod(0o600)
    elif mutation == "hardlink":
        os.link(journal.path, journal.path.with_name("foreign-link"))
    elif mutation == "append":
        with journal.path.open("ab") as stream:
            stream.write(b" ")
    elif mutation == "truncate":
        journal.path.write_bytes(original[:-1])
    else:
        other = journal.path.with_name("foreign-target")
        journal.path.rename(other)
        journal.path.symlink_to(other)
    try:
        with pytest.raises(attempt.AttemptError):
            journal.verify_owned()
    finally:
        journal.close()


def test_startup_sealed_fd_remains_owned_until_close_and_cannot_be_adopted(
    attempt, tmp_path, projection
):
    directory = tmp_path / "retained-fd"
    journal, _checkpoint = _startup_to_checkpoint(attempt, directory, projection)
    journal.append("claim_created", {"claim_sha256": "a" * 64})
    journal.append("scientific_ledger_started", {"first_event_sha256": "b" * 64})
    journal.append("history_load_intent", {})
    journal.seal()
    journal.verify_owned()
    original = journal.path.read_bytes()
    with pytest.raises((attempt.AttemptError, FileExistsError)):
        _synthetic_startup(attempt, directory)
    journal.verify_owned()
    journal.close()
    with pytest.raises(attempt.AttemptError):
        journal.verify_owned()
    assert journal.path.read_bytes() == original


@pytest.fixture
def review_evidence(attempt):
    head, base, merge, closure = "a" * 40, "b" * 40, "c" * 40, "d" * 64
    responses = {
        "/pulls/41": {
            "number": 41,
            "state": "closed",
            "merged": True,
            "merge_commit_sha": merge,
            "head": {"sha": head, "repo": {"full_name": attempt.REPOSITORY}},
            "base": {
                "sha": base,
                "ref": "main",
                "repo": {"full_name": attempt.REPOSITORY},
            },
        },
        f"/commits/{head}/check-runs?per_page=100": {
            "total_count": 2,
            "check_runs": [
                {"id": 101, "name": "test"},
                {"id": 102, "name": "push-test"},
            ],
        },
        "/check-runs/101": {
            "id": 101,
            "name": "test",
            "head_sha": head,
            "status": "completed",
            "conclusion": "success",
            "app": {"slug": "github-actions"},
        },
    }
    records = []
    contributors = [
        {"agent_id": "synthetic-author", "session_id": "synthetic-author-session"}
    ]
    state = {"phase": "I3", "contributors": contributors, "calls": []}
    for index, axis in enumerate(("standards", "spec")):
        attestation = {
            "schema_version": "lotto649-v12-i3-independent-review-v1",
            "axis": axis,
            "base_sha": base,
            "head_sha": head,
            "closure_sha256": closure,
            "verdict": "pass",
            "blocker_count": 0,
            "major_count": 0,
            "reviewer_kind": "independent_agent",
            "reviewer_agent_id": f"synthetic-{axis}-agent",
            "review_session_id": f"synthetic-{axis}-session",
            "publisher_login": "synthetic-actual-publisher",
        }
        body = _canonical_fixture(attestation).decode()
        comment_id = 201 + index
        responses[f"/issues/comments/{comment_id}"] = {
            "id": comment_id,
            "body": body,
            "user": {"login": attestation["publisher_login"]},
            "issue_url": attempt._API_ORIGIN + attempt._API_PREFIX + "/issues/41",
            "created_at": "2032-01-01T12:00:00Z",
            "updated_at": "2032-01-01T12:00:00Z",
        }
        records.append(
            {
                "axis": axis,
                "pr_number": 41,
                "check_id": 101,
                "comment_id": comment_id,
                "comment_body_sha256": hashlib.sha256(body.encode()).hexdigest(),
                **{
                    key: attestation[key]
                    for key in (
                        "reviewer_agent_id",
                        "review_session_id",
                        "publisher_login",
                    )
                },
            }
        )

    class SyntheticApi:
        def request_json(self, method, path):
            assert method == "GET"
            assert path.startswith(attempt._API_PREFIX)
            state["calls"].append(path.removeprefix(attempt._API_PREFIX))
            return copy.deepcopy(responses[path.removeprefix(attempt._API_PREFIX)])

    class SyntheticGit:
        def run(self, *arguments):
            assert arguments == ("cat-file", "commit", head)
            return _raw_author_commit(
                _author_payload(
                    phase=state["phase"], contributors=state["contributors"]
                )
            )

    def verify():
        attempt._verify_reviews(
            SyntheticApi(),
            records,
            implementation=head,
            merge=merge,
            base=base,
            closure_sha256=closure,
            git=SyntheticGit(),
            phase=state["phase"],
        )

    return SimpleNamespace(
        records=records,
        responses=responses,
        state=state,
        verify=verify,
        head=head,
        base=base,
        merge=merge,
        closure=closure,
        api=SyntheticApi(),
        git=SyntheticGit(),
    )


def _change_review_body(fixture, index, key, value):
    comment = fixture.responses[f"/issues/comments/{201 + index}"]
    body = json.loads(comment["body"])
    body[key] = value
    comment["body"] = _canonical_fixture(body).decode()
    fixture.records[index]["comment_body_sha256"] = hashlib.sha256(
        comment["body"].encode()
    ).hexdigest()


@pytest.mark.parametrize(
    "phase,schema",
    [
        ("I3", "lotto649-v12-i3-independent-review-v1"),
        ("A_H_s3", "lotto649-v12-ah3-independent-review-v1"),
    ],
)
def test_each_phase_requires_fresh_independent_review_but_one_honest_publisher_is_allowed(
    review_evidence, phase, schema
):
    fixture = review_evidence
    fixture.state["phase"] = phase
    for index in range(2):
        _change_review_body(fixture, index, "schema_version", schema)
    fixture.verify()


@pytest.mark.parametrize("field", ["reviewer_agent_id", "review_session_id"])
def test_review_axes_cannot_reuse_agent_or_session(review_evidence, attempt, field):
    review_evidence.records[1][field] = review_evidence.records[0][field]
    with pytest.raises(attempt.AuthorizationError):
        review_evidence.verify()


@pytest.mark.parametrize(
    "author_field,review_field",
    [("agent_id", "reviewer_agent_id"), ("session_id", "review_session_id")],
)
def test_review_excludes_every_source_author_agent_and_session_independently(
    review_evidence, attempt, author_field, review_field
):
    fixture = review_evidence
    contributor = {
        "agent_id": "other-synthetic-author",
        "session_id": "other-author-session",
    }
    contributor[author_field] = fixture.records[1][review_field]
    fixture.state["contributors"] = sorted(
        [*fixture.state["contributors"], contributor],
        key=lambda item: (item["agent_id"].encode(), item["session_id"].encode()),
    )
    with pytest.raises(attempt.AuthorizationError):
        fixture.verify()
    assert fixture.state["calls"] == []


@pytest.mark.parametrize("count", [-1, 0, 1, 3, 101, True, None])
def test_review_check_listing_must_be_complete(review_evidence, attempt, count):
    review_evidence.responses[
        f"/commits/{review_evidence.head}/check-runs?per_page=100"
    ]["total_count"] = count
    with pytest.raises(attempt.AuthorizationError):
        review_evidence.verify()


def test_duplicate_test_check_is_ambiguous_even_when_one_passed(
    review_evidence, attempt
):
    review_evidence.responses[
        f"/commits/{review_evidence.head}/check-runs?per_page=100"
    ]["check_runs"][1]["name"] = "test"
    with pytest.raises(attempt.AuthorizationError):
        review_evidence.verify()


@pytest.mark.parametrize(
    "field,value",
    [
        ("head_sha", "e" * 40),
        ("conclusion", "failure"),
        ("status", "in_progress"),
        ("app", {"slug": "synthetic-spoof"}),
    ],
)
def test_review_ci_binds_successful_actions_at_exact_head(
    review_evidence, attempt, field, value
):
    review_evidence.responses["/check-runs/101"][field] = value
    with pytest.raises(attempt.AuthorizationError):
        review_evidence.verify()


@pytest.mark.parametrize(
    "change",
    [
        "edited",
        "missing_timestamps",
        "invalid_timestamp",
        "offset_timestamp",
        "wrong_issue",
        "wrong_publisher",
        "changed_bytes",
        "major",
        "bool_count",
        "head",
        "old_schema",
        "author_field",
    ],
)
def test_review_comment_requires_immutable_closed_bound_provenance(
    review_evidence, attempt, change
):
    fixture = review_evidence
    comment = fixture.responses["/issues/comments/201"]
    if change == "edited":
        comment["updated_at"] = "2032-01-01T12:01:00Z"
    elif change == "missing_timestamps":
        comment.pop("created_at")
        comment.pop("updated_at")
    elif change == "invalid_timestamp":
        comment["created_at"] = comment["updated_at"] = "2032-02-31T12:00:00Z"
    elif change == "offset_timestamp":
        comment["created_at"] = comment["updated_at"] = "2032-01-01T12:00:00+00:00"
    elif change == "wrong_issue":
        comment["issue_url"] += "2"
    elif change == "wrong_publisher":
        comment["user"]["login"] = "synthetic-false-identity"
    elif change == "changed_bytes":
        comment["body"] += " "
    else:
        field, value = {
            "major": ("major_count", 1),
            "bool_count": ("major_count", False),
            "head": ("head_sha", "e" * 40),
            "old_schema": ("schema_version", "lotto649-v12-i2-independent-review-v1"),
            "author_field": ("author_agent_id", "synthetic-author"),
        }[change]
        _change_review_body(fixture, 0, field, value)
    with pytest.raises(attempt.AuthorizationError):
        fixture.verify()


@pytest.mark.parametrize(
    "field,value",
    [
        ("pr_number", True),
        ("pr_number", 0),
        ("check_id", "101"),
        ("comment_id", -1),
        ("unknown", 1),
        ("reviewer_agent_id", ""),
        ("review_session_id", " synthetic"),
        ("publisher_login", ""),
    ],
)
def test_review_record_schema_and_identifiers_are_closed(
    review_evidence, attempt, field, value
):
    review_evidence.records[0][field] = value
    with pytest.raises(attempt.AuthorizationError):
        review_evidence.verify()


@pytest.mark.parametrize(
    "path,value",
    [
        (("merge_commit_sha",), "e" * 40),
        (("merged",), False),
        (("head", "repo", "full_name"), "other/repository"),
        (("base", "sha"), "e" * 40),
        (("base", "ref"), "other-branch"),
    ],
)
def test_review_pr_binds_fixed_repository_main_and_normal_merge(
    review_evidence, attempt, path, value
):
    _at_path(review_evidence.responses["/pulls/41"], path[:-1])[path[-1]] = value
    with pytest.raises(attempt.AuthorizationError):
        review_evidence.verify()


@pytest.fixture
def authorization_discovery(review_evidence, attempt):
    fixture = review_evidence
    fixture.state["phase"] = "A_H_s3"
    for index in range(2):
        _change_review_body(
            fixture, index, "schema_version", "lotto649-v12-ah3-independent-review-v1"
        )
    associated = copy.deepcopy(fixture.responses["/pulls/41"])
    associated["merged_at"] = "2032-01-01T12:01:00Z"
    fixture.responses[f"/commits/{fixture.head}/pulls?per_page=100"] = [associated]
    fixture.responses["/issues/41/comments?per_page=100"] = [
        copy.deepcopy(fixture.responses[f"/issues/comments/{201 + i}"])
        for i in range(2)
    ]

    def discover_and_verify():
        records = attempt._discover_authorization_reviews(
            fixture.api,
            source=fixture.head,
            base=fixture.base,
            merge=fixture.merge,
            closure_sha256=fixture.closure,
        )
        attempt._verify_reviews(
            fixture.api,
            records,
            implementation=fixture.head,
            merge=fixture.merge,
            base=fixture.base,
            closure_sha256=fixture.closure,
            git=fixture.git,
            phase="A_H_s3",
        )
        return records

    return SimpleNamespace(fixture=fixture, verify=discover_and_verify)


def test_authorization_reviews_are_discovered_externally_then_refetched_by_id(
    authorization_discovery,
):
    case = authorization_discovery
    records = case.verify()
    assert records == sorted(case.fixture.records, key=lambda record: record["axis"])
    calls = case.fixture.state["calls"]
    expected = {
        f"/commits/{case.fixture.head}/pulls?per_page=100",
        "/pulls/41",
        "/issues/41/comments?per_page=100",
        "/issues/comments/201",
        "/issues/comments/202",
        f"/commits/{case.fixture.head}/check-runs?per_page=100",
        "/check-runs/101",
    }
    assert set(calls) == expected
    assert calls.index("/issues/41/comments?per_page=100") < calls.index(
        "/issues/comments/201"
    )


@pytest.mark.parametrize(
    "change",
    [
        "duplicate_pr",
        "wrong_merge",
        "wrong_source",
        "wrong_base",
        "unmerged",
        "duplicate_axis",
        "old_schema",
        "wrong_closure",
        "duplicate_check",
        "incomplete_checks",
        "too_many_prs",
        "too_many_comments",
    ],
)
def test_authorization_discovery_rejects_ambiguity_incompleteness_and_stale_source(
    authorization_discovery, attempt, change
):
    case = authorization_discovery
    fixture = case.fixture
    prs = fixture.responses[f"/commits/{fixture.head}/pulls?per_page=100"]
    comments = fixture.responses["/issues/41/comments?per_page=100"]
    checks = fixture.responses[f"/commits/{fixture.head}/check-runs?per_page=100"]
    if change == "duplicate_pr":
        prs.append(copy.deepcopy(prs[0]))
    elif change == "wrong_merge":
        prs[0]["merge_commit_sha"] = "e" * 40
    elif change == "wrong_source":
        prs[0]["head"]["sha"] = "e" * 40
    elif change == "wrong_base":
        prs[0]["base"]["sha"] = "e" * 40
    elif change == "unmerged":
        prs[0]["merged_at"] = None
    elif change == "duplicate_axis":
        comments.append(copy.deepcopy(comments[0]))
    elif change in {"old_schema", "wrong_closure"}:
        body = json.loads(comments[0]["body"])
        body["schema_version" if change == "old_schema" else "closure_sha256"] = (
            "lotto649-v12-i2-independent-review-v1"
            if change == "old_schema"
            else "e" * 64
        )
        comments[0]["body"] = _canonical_fixture(body).decode()
    elif change == "duplicate_check":
        checks["check_runs"][1]["name"] = "test"
    elif change == "incomplete_checks":
        checks["total_count"] = 3
    elif change == "too_many_prs":
        prs.extend({} for _ in range(100))
    else:
        comments.extend({"body": "ordinary comment"} for _ in range(99))
    with pytest.raises(attempt.AuthorizationError):
        case.verify()


def test_discovered_comment_must_match_fresh_immutable_id_refetch(
    authorization_discovery, attempt
):
    case = authorization_discovery
    case.fixture.responses["/issues/comments/201"]["body"] += (
        " changed after collection"
    )
    with pytest.raises(attempt.AuthorizationError):
        case.verify()


@pytest.fixture
def synthetic_authorization(attempt, monkeypatch, tmp_path):
    ids = dict(
        zip(
            (
                "implementation_base",
                "implementation",
                "implementation_merge",
                "base",
                "source",
                "head",
            ),
            (str(i) * 40 for i in range(1, 7)),
            strict=True,
        )
    )
    registration = b"synthetic registration identity"
    core = (ROOT / attempt.CORE_PATH).read_bytes()
    requirements = (ROOT / attempt.REQUIREMENTS_PATH).read_bytes()
    closure = [
        {"path": attempt.CORE_PATH, "git_blob": "a" * 40, "sha256": attempt.CORE_SHA256}
    ]
    source_bytes = {
        path: ("synthetic fixed source " + path + "\n").encode()
        for path in attempt.IMPLEMENTATION_PATHS
    }
    files = [
        {
            "path": path,
            "git_blob": "c" * 40,
            "sha256": hashlib.sha256(source_bytes[path]).hexdigest(),
            "bytes": len(source_bytes[path]),
        }
        for path in sorted(source_bytes)
    ]
    runtime = {"synthetic_runtime": True}
    payload = {
        "schema_version": "lotto649-v12.0.2-historical-authorization-v1",
        "experiment_id": "synthetic_contract",
        "model_version": "v12.0.2",
        "repository": attempt.REPOSITORY,
        "branch": "main",
        "registration_commit": attempt.R3,
        "registration_sha256": hashlib.sha256(registration).hexdigest(),
        "scientific_registration_commit": attempt.R1,
        "statistical_fingerprint_sha256": attempt.FINGERPRINT,
        "pure_core_sha256": attempt.CORE_SHA256,
        "implementation_commit": ids["implementation"],
        "implementation_base": ids["implementation_base"],
        "implementation_merge": ids["implementation_merge"],
        "authorization_base": ids["base"],
        "canonical_command": attempt.COMMAND,
        "governed_history_authority": attempt.HISTORY_AUTHORITY,
        "governed_history_identity": {"synthetic_metadata": True},
        "runtime": runtime,
        "implementation_files": files,
        "implementation_files_sha256": hashlib.sha256(
            _canonical_fixture(files)
        ).hexdigest(),
        "runtime_dependency_closure": closure,
        "runtime_dependency_closure_sha256": hashlib.sha256(
            _canonical_fixture(closure)
        ).hexdigest(),
        "review_records": [],
    }
    state = {
        "head": ids["head"],
        "drift": None,
        "drift_kind": "core",
        "read_core": [],
        "read_lock": [],
        "closure_reads": [],
        "registered_reads": [],
        "review_phases": [],
    }

    class SyntheticGit:
        root = tmp_path

        def require_full_clean(self):
            pass

        def head(self):
            return state["head"]

        def read_blob(self, commit, path):
            changed = commit == state["drift"]
            if path == attempt.AUTHORIZATION_PATH:
                return _canonical_fixture(payload) + b"\n"
            if path == attempt.R3_PATH:
                return registration
            if path == attempt.CORE_PATH:
                state["read_core"].append(commit)
                return core + (
                    b"# drift\n" if changed and state["drift_kind"] == "core" else b""
                )
            if path == attempt.REQUIREMENTS_PATH:
                state["read_lock"].append(commit)
                return requirements + (
                    b"# drift\n" if changed and state["drift_kind"] == "lock" else b""
                )
            if path in source_bytes:
                return source_bytes[path] + (
                    b"# drift\n"
                    if changed and state["drift_kind"] == "implementation"
                    else b""
                )
            raise AssertionError("unexpected immutable metadata read")

        def oid(self, _commit, path):
            assert path in source_bytes
            return "c" * 40

        def parents(self, commit):
            return {
                ids["head"]: (ids["base"], ids["source"]),
                ids["source"]: (ids["base"],),
                ids["implementation_merge"]: (
                    ids["implementation_base"],
                    ids["implementation"],
                ),
            }[commit]

        def tree(self, commit):
            return "b" * 40 if commit in {ids["head"], ids["source"]} else "c" * 40

        def changes(self, earlier, later):
            if (earlier, later) == (ids["base"], ids["source"]):
                return [("A", attempt.AUTHORIZATION_PATH)]
            assert (earlier, later) == (
                ids["implementation_base"],
                ids["implementation"],
            )
            return [("A", path) for path in attempt.IMPLEMENTATION_PATHS]

        def ancestor(self, _earlier, _later):
            return True

    def registered(_git, commit):
        state["registered_reads"].append(commit)
        return {"authority": {"synthetic_metadata": True}}, {
            "experiment_id": "synthetic_contract"
        }

    def read_closure(_repository, commit):
        state["closure_reads"].append(commit)
        return [
            *copy.deepcopy(closure),
            *(
                [{"path": "synthetic_drift", "git_blob": "e" * 40, "sha256": "e" * 64}]
                if commit == state["drift"] and state["drift_kind"] == "closure"
                else []
            ),
        ]

    def reviews(*_args, **kwargs):
        state["review_phases"].append(kwargs["phase"])

    git = SyntheticGit()
    monkeypatch.setattr(attempt, "GitRepository", lambda _root: git)
    monkeypatch.setattr(attempt, "_registered_authorities", registered)
    monkeypatch.setattr(attempt, "runtime_identity", lambda: runtime)
    monkeypatch.setattr(attempt, "runtime_dependency_closure", read_closure)
    monkeypatch.setattr(attempt, "_remote_protection", lambda _api: None)
    monkeypatch.setattr(attempt, "_remote_main", lambda _api: ids["head"])
    monkeypatch.setattr(attempt, "_verify_reviews", reviews)
    monkeypatch.setattr(
        attempt,
        "_discover_authorization_reviews",
        lambda *_args, **_kwargs: [{"synthetic_review_facts": True}],
    )
    monkeypatch.setattr(attempt, "_verify_worktree_runtime", lambda *_args: None)
    return SimpleNamespace(
        ids=ids, payload=payload, state=state, root=tmp_path, git=git
    )


def test_read_only_authorization_checks_all_four_checkpoints_and_issues_only_inert_facts(
    attempt, synthetic_authorization
):
    fixture = synthetic_authorization
    before = len(attempt._ISSUED_AUTHORITIES)
    facts = attempt.verify_authorization(fixture.root, api=object())
    expected = [
        fixture.ids[key] for key in ("implementation", "base", "source", "head")
    ]
    assert type(facts) is attempt.VerifiedAuthorizationFacts
    assert facts.execution_commit == fixture.ids["head"]
    assert fixture.state["read_core"] == expected
    assert fixture.state["read_lock"] == expected
    assert fixture.state["closure_reads"] == expected
    assert fixture.state["registered_reads"] == [fixture.ids["head"], *expected]
    assert fixture.state["review_phases"] == ["I3", "A_H_s3"]
    assert len(attempt._ISSUED_AUTHORITIES) == before
    assert list(fixture.root.iterdir()) == []
    with pytest.raises(attempt.AuthorizationError):
        attempt._require_authorization_capability(facts)


@pytest.mark.parametrize("checkpoint", ["implementation", "base", "source", "head"])
@pytest.mark.parametrize("kind", ["core", "lock", "closure", "implementation"])
def test_any_frozen_checkpoint_drift_refuses_inert_authorization_before_capability(
    attempt, synthetic_authorization, checkpoint, kind
):
    fixture = synthetic_authorization
    fixture.state["drift"] = fixture.ids[checkpoint]
    fixture.state["drift_kind"] = kind
    with pytest.raises(attempt.AuthorizationError):
        attempt.verify_authorization(fixture.root, api=object())
    assert list(fixture.root.iterdir()) == []


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema_version", "lotto649-v12.0.1-historical-authorization-v1"),
        ("model_version", "v12.0.1"),
        ("branch", "other"),
        ("repository", "other/repo"),
        ("registration_commit", "e" * 40),
        ("scientific_registration_commit", "e" * 40),
        ("statistical_fingerprint_sha256", "e" * 64),
        ("pure_core_sha256", "e" * 64),
        (
            "canonical_command",
            ["python3.12", "tools/run_v12_0_1_historical.py", "--consume-v12-0-1-once"],
        ),
        ("governed_history_authority", "e" * 40),
        ("governed_history_identity", {}),
        ("runtime", {"synthetic_runtime": False}),
        ("runtime_dependency_closure_sha256", "e" * 64),
        ("implementation_files_sha256", "e" * 64),
        ("authorization_review_records", []),
    ],
)
def test_authorization_rejects_old_identity_runtime_or_self_embedded_future_review(
    attempt, synthetic_authorization, field, value
):
    fixture = synthetic_authorization
    fixture.payload[field] = value
    with pytest.raises(attempt.AuthorizationError):
        attempt.verify_authorization(fixture.root, api=object())


def test_auth_source_branch_has_no_execution_authority(
    attempt, synthetic_authorization
):
    fixture = synthetic_authorization
    fixture.state["head"] = fixture.ids["source"]
    with pytest.raises(attempt.AuthorizationError):
        attempt.verify_authorization(fixture.root, api=object())


@pytest.mark.parametrize("phase", ["implementation", "source"])
def test_registered_source_cannot_smuggle_a_seventh_or_second_path(
    attempt, synthetic_authorization, monkeypatch, phase
):
    fixture = synthetic_authorization
    original = fixture.git.changes

    def changes(earlier, later):
        result = original(earlier, later)
        return (
            result + [("M", "config.yaml")] if later == fixture.ids[phase] else result
        )

    monkeypatch.setattr(fixture.git, "changes", changes)
    with pytest.raises(attempt.AuthorizationError):
        attempt.verify_authorization(fixture.root, api=object())


def test_authorization_must_equal_fresh_protected_remote_main(
    attempt, synthetic_authorization, monkeypatch
):
    monkeypatch.setattr(attempt, "_remote_main", lambda _api: "e" * 40)
    with pytest.raises(attempt.AuthorizationError):
        attempt.verify_authorization(synthetic_authorization.root, api=object())


def test_inert_fact_mutation_is_rejected_without_startup_or_execution_capability(
    attempt, synthetic_authorization
):
    fixture = synthetic_authorization
    facts = attempt.verify_authorization(fixture.root, api=object())
    facts.payload["runtime"]["synthetic_runtime"] = False
    with pytest.raises(attempt.AuthorizationError):
        attempt._require_verified_facts(facts)
    assert list(fixture.root.iterdir()) == []


@pytest.mark.parametrize(
    "capability", ["VerifiedAuthorizationFacts", "VerifiedAuthorization", "Lease"]
)
def test_authorization_facts_and_execution_capabilities_cannot_be_directly_constructed(
    attempt, capability
):
    with pytest.raises((attempt.AuthorizationError, attempt.AttemptError)):
        vars(attempt)[capability]()


@pytest.mark.parametrize(
    "body", [b'{"a":1e9999}', b'{"a":"\\ud800"}', '{"a":1}'.encode("utf-16")]
)
def test_transport_rejects_overflow_surrogate_and_non_utf8_json(
    attempt, monkeypatch, body
):
    api, calls = _http_fixture(attempt, monkeypatch, _HttpResponse(body=body))
    with pytest.raises(attempt.AuthorizationError):
        api.request_json("GET", attempt._API_PREFIX)
    assert len(calls) == 1


def test_source_author_provenance_rejects_surrogate_as_safe_authorization_failure(
    attempt,
):
    body = _canonical_fixture(_author_payload()).replace(
        b"synthetic-author-session", b"\\ud800"
    )
    raw = _raw_author_commit(message=b"Research-Author-Provenance: " + body + b"\n")
    with pytest.raises(attempt.AuthorizationError):
        attempt._source_author_provenance(raw, "I3")


@pytest.mark.parametrize(
    "timestamp",
    [
        "2032-02-31T00:00:00Z",
        "2032-01-01T00:00:00+00:00",
        "2032-01-01T00:00:00",
        "2032-01-01T00:00:00.1234567Z",
        "synthetic-private-clock",
        None,
    ],
)
def test_startup_rejects_non_utc_or_invalid_trusted_clock_without_writing_it(
    attempt, monkeypatch, tmp_path, timestamp
):
    journal = _synthetic_startup(attempt, tmp_path / "bad-clock")
    original = journal.path.read_bytes()
    monkeypatch.setattr(attempt, "_utc_now", lambda: timestamp)
    try:
        with pytest.raises(attempt.AttemptError):
            journal.append("capability_issued", {})
        assert journal.path.read_bytes() == original
    finally:
        journal.close()


def test_startup_short_write_is_preserved_and_never_completed_on_retry(
    attempt, monkeypatch, tmp_path
):
    journal = _synthetic_startup(attempt, tmp_path / "partial-line")
    original = journal.path.read_bytes()
    real_write = os.write
    writes = []

    def partial(descriptor, raw):
        writes.append(bytes(raw))
        return real_write(descriptor, raw[:17])

    monkeypatch.setattr(attempt.os, "write", partial)
    try:
        with pytest.raises(attempt.AttemptError):
            journal.append("capability_issued", {})
        partial_bytes = journal.path.read_bytes()
        assert partial_bytes == original + writes[0][:17]
        assert not partial_bytes.endswith(b"\n")
        with pytest.raises(attempt.AttemptError):
            journal.append("capability_issued", {})
        assert len(writes) == 1
        assert journal.path.read_bytes() == partial_bytes
    finally:
        journal.close()


@pytest.mark.parametrize("mutation", ["offset", "closed_fd", "parent_renamed"])
def test_startup_retained_descriptor_and_parent_identity_cannot_be_replaced(
    attempt, tmp_path, mutation
):
    journal = _synthetic_startup(attempt, tmp_path / mutation)
    descriptor = journal.initial_identity["fd"]
    if mutation == "offset":
        os.lseek(descriptor, 0, os.SEEK_SET)
    elif mutation == "closed_fd":
        os.close(descriptor)
    else:
        journal.path.parent.rename(journal.path.parent.with_name("moved-parent"))
    try:
        with pytest.raises(attempt.AttemptError):
            journal.verify_owned()
    finally:
        # close() must be safe even if outside interference already closed the FD.
        journal.close()


@pytest.mark.parametrize(
    "directory_kind", ["reserved", "inside_git", "symlink", "unsafe_parent"]
)
def test_startup_synthetic_factory_refuses_repository_reserved_and_unsafe_paths(
    attempt, tmp_path, directory_kind
):
    directory = tmp_path / "synthetic-startup"
    if directory_kind == "reserved":
        directory = tmp_path / "reports"
    elif directory_kind == "inside_git":
        (tmp_path / ".git").mkdir()
    elif directory_kind == "symlink":
        actual = tmp_path / "actual"
        actual.mkdir()
        directory.symlink_to(actual, target_is_directory=True)
    else:
        parent = tmp_path / "unsafe"
        parent.mkdir()
        parent.chmod(0o777)
        directory = parent / "synthetic-startup"
    with pytest.raises((attempt.AttemptError, OSError)):
        attempt.StartupJournal.for_synthetic(
            directory.absolute(), {"synthetic_fixture_only": True}
        )
    assert not list(tmp_path.rglob("synthetic-startup.jsonl"))


@pytest.mark.parametrize(
    "identity",
    [
        {},
        {"synthetic_fixture_only": 1},
        {"synthetic_fixture_only": True, "authorization": "synthetic"},
        {"synthetic_fixture_only": False},
    ],
)
def test_startup_synthetic_facts_cannot_grow_into_authority(
    attempt, tmp_path, identity
):
    directory = tmp_path / "rejected-synthetic"
    with pytest.raises(attempt.AttemptError):
        attempt.StartupJournal.for_synthetic(directory, identity)
    assert not directory.exists()


def test_unissued_facts_cannot_create_any_startup_bytes(attempt, tmp_path):
    forged = SimpleNamespace(repository=tmp_path, execution_commit="a" * 40, payload={})
    with pytest.raises(attempt.AuthorizationError):
        attempt.begin_authorized_startup(forged)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    "name",
    [
        "_prefix_identity",
        "_drive_sequence",
        "_target_dates",
        "_durable_scored_rows",
        "audit_ledger",
    ],
)
def test_scientific_worker_function_ast_is_exact_except_registered_module_identity(
    name,
):
    older = ast.parse((ROOT / "src/lotto649/v12_0_1_registered_attempt.py").read_text())
    newer = ast.parse((ROOT / "src/lotto649/v12_0_2_registered_attempt.py").read_text())
    old_function = next(
        node
        for node in older.body
        if isinstance(node, ast.FunctionDef) and node.name == name
    )
    new_function = copy.deepcopy(
        next(
            node
            for node in newer.body
            if isinstance(node, ast.FunctionDef) and node.name == name
        )
    )
    for node in ast.walk(new_function):
        if isinstance(node, ast.ImportFrom) and node.module == "v12_0_2_evidence":
            node.module = "v12_0_1_evidence"
        elif isinstance(node, ast.Constant) and type(node.value) is str:
            node.value = {
                "v12.0.2": "v12.0.1",
                "lotto649-v12.0.2-frozen-forecast-v1": "lotto649-v12.0.1-frozen-forecast-v1",
                "分类：历史诊断/审计候选、不可晋升\n模型版本：v12.0.2\n历史目标日期：": "分类：历史诊断/审计候选、不可晋升\n模型版本：v12.0.1\n历史目标日期：",
            }.get(node.value, node.value)
    assert ast.dump(new_function, include_attributes=False) == ast.dump(
        old_function, include_attributes=False
    )


def _post_arguments(projection, phase):
    arguments = {
        "phase": phase,
        "nonce": projection["nonce_hex"],
        "oid": projection["raw_commit_sha1"],
        "raw_sha256": projection["raw_commit_sha256"],
        "request_bytes": _canonical_fixture(
            projection[
                "post_commit_request" if phase == "lease_commit" else "post_ref_request"
            ]
        ),
    }
    if phase == "lease_commit":
        arguments["commit_payload"] = projection["post_commit_request"]
    return arguments


def _startup_before_post(attempt, directory, projection, phase):
    journal = _synthetic_startup(attempt, directory)
    journal.append("capability_issued", {})
    journal.append("lease_absence_confirmed", {"http_status": 404})
    if phase == "lease_ref":
        arguments = _post_arguments(projection, "lease_commit")
        journal.intent(
            "lease_commit",
            arguments["nonce"],
            arguments["oid"],
            arguments["raw_sha256"],
            arguments["request_bytes"],
        )
        journal.receipt("lease_commit", "success", 201, arguments["oid"])
        _verify_projection(attempt, projection)
        journal.append("lease_commit_GET_verified", {"validated_oid": arguments["oid"]})
    return journal


@pytest.mark.parametrize("phase", ["lease_commit", "lease_ref"])
def test_integrated_post_helper_fsyncs_exact_intent_before_one_mock_request(
    attempt, monkeypatch, tmp_path, projection, phase
):
    journal = _startup_before_post(attempt, tmp_path / phase, projection, phase)
    arguments = _post_arguments(projection, phase)
    observed = []
    durable = []
    real_fsync = os.fsync

    def fsync(descriptor):
        real_fsync(descriptor)
        if os.fstat(descriptor).st_ino == journal.path.stat().st_ino:
            durable.append(journal.path.read_bytes())

    class SyntheticApi:
        last_status = 201

        def request_json(self, method, path, *, body_bytes):
            assert method == "POST"
            assert path == attempt._API_PREFIX + (
                "/git/commits" if phase == "lease_commit" else "/git/refs"
            )
            assert body_bytes is arguments["request_bytes"]
            assert journal.path.read_bytes() == durable[-1]
            intent = json.loads(durable[-1].splitlines()[-1])
            assert intent["kind"] == phase + "_POST_intent"
            assert (
                intent["payload"]["request_body_sha256"]
                == hashlib.sha256(body_bytes).hexdigest()
            )
            observed.append((method, path, body_bytes))
            return copy.deepcopy(
                projection[
                    "post_commit_response"
                    if phase == "lease_commit"
                    else "post_ref_response"
                ]
            )

    monkeypatch.setattr(attempt.os, "fsync", fsync)
    try:
        attempt._post_lease_request(SyntheticApi(), journal, **arguments)
        assert len(observed) == 1
        assert _startup_events(journal)[-1]["payload"]["result_enum"] == "success"
        assert (
            _startup_events(journal)[-1]["payload"]["validated_oid"]
            == projection["raw_commit_sha1"]
        )
        with pytest.raises(attempt.AttemptError):
            attempt._post_lease_request(SyntheticApi(), journal, **arguments)
        assert len(observed) == 1
    finally:
        journal.close()


@pytest.mark.parametrize("phase", ["lease_commit", "lease_ref"])
def test_integrated_post_intent_fsync_failure_prevents_transport(
    attempt, monkeypatch, tmp_path, projection, phase
):
    journal = _startup_before_post(attempt, tmp_path / phase, projection, phase)
    observed = []

    class SyntheticApi:
        def request_json(self, *_args, **_kwargs):
            observed.append("forbidden request")
            raise AssertionError("request must not follow undurable intent")

    def fail(_descriptor):
        raise OSError("synthetic-private-disk-detail")

    monkeypatch.setattr(attempt.os, "fsync", fail)
    try:
        with pytest.raises(attempt.AttemptError):
            attempt._post_lease_request(
                SyntheticApi(), journal, **_post_arguments(projection, phase)
            )
        assert observed == []
        assert _startup_events(journal)[-1]["kind"] == phase + "_POST_intent"
    finally:
        journal.close()


@pytest.mark.parametrize("phase", ["lease_commit", "lease_ref"])
@pytest.mark.parametrize("failure", ["transport", "identity", "receipt_fsync"])
def test_integrated_post_uncertainty_is_durable_sanitized_and_has_no_retry(
    attempt, monkeypatch, tmp_path, projection, phase, failure
):
    journal = _startup_before_post(
        attempt, tmp_path / f"{phase}-{failure}", projection, phase
    )
    arguments = _post_arguments(projection, phase)
    observed = []
    real_fsync = os.fsync

    class SyntheticApi:
        last_status = 201

        def request_json(self, *_args, **_kwargs):
            observed.append("attempted")
            if failure == "transport":
                raise OSError("synthetic-private-transport-secret")
            if failure == "identity":
                return {"sha": "e" * 40, "secret": "synthetic-private-response"}
            return copy.deepcopy(
                projection[
                    "post_commit_response"
                    if phase == "lease_commit"
                    else "post_ref_response"
                ]
            )

    def fsync(descriptor):
        if failure == "receipt_fsync" and observed:
            raise OSError("synthetic-private-fsync-secret")
        real_fsync(descriptor)

    monkeypatch.setattr(attempt.os, "fsync", fsync)
    try:
        with pytest.raises(attempt.AttemptError) as caught:
            attempt._post_lease_request(SyntheticApi(), journal, **arguments)
        assert "synthetic-private" not in str(caught.value)
        assert b"synthetic-private" not in journal.path.read_bytes()
        before = journal.path.read_bytes()
        with pytest.raises(attempt.AttemptError):
            attempt._post_lease_request(SyntheticApi(), journal, **arguments)
        assert journal.path.read_bytes() == before
        assert observed == ["attempted"]
        events = _startup_events(journal)
        assert sum(event["kind"] == phase + "_POST_intent" for event in events) == 1
    finally:
        journal.close()


def _synthetic_artifacts(attempt, directory):
    return attempt.OwnedArtifacts.for_synthetic(directory.resolve())


def test_owned_artifacts_allow_only_current_exclusive_creations(attempt, tmp_path):
    owner = _synthetic_artifacts(attempt, tmp_path / "owned-claim")
    try:
        assert owner.allowed_paths() == set()
        assert "startup" not in owner.paths
        owner.create_bytes("claim", b'{"synthetic_fixture_only":true}\n')
        path = owner.paths["claim"]
        assert path.name.startswith("synthetic_")
        assert path.read_bytes() == b'{"synthetic_fixture_only":true}\n'
        assert path.stat().st_mode & 0o777 == 0o600
        assert owner.allowed_paths() == {path.name}
        owner.verify_owned()
        before = path.read_bytes()
        with pytest.raises(attempt.AttemptError):
            owner.create_bytes("claim", b"replacement\n")
        assert path.read_bytes() == before
    finally:
        owner.close()


def test_owned_artifact_factory_does_not_adopt_preexisting_registered_filename(
    attempt, tmp_path
):
    directory = tmp_path / "foreign-claim"
    directory.mkdir()
    path = attempt._paths(directory, synthetic=True)["claim"]
    original = b"synthetic existing evidence\n"
    path.write_bytes(original)
    with pytest.raises(attempt.AttemptError):
        _synthetic_artifacts(attempt, directory)
    assert path.read_bytes() == original


@pytest.mark.parametrize(
    "mutation", ["bytes", "chmod", "replace", "hardlink", "symlink", "foreign_file"]
)
def test_owned_artifacts_refuse_name_only_allowances_and_foreign_changes(
    attempt, tmp_path, mutation
):
    owner = _synthetic_artifacts(attempt, tmp_path / mutation)
    owner.create_bytes("claim", b"synthetic claim\n")
    path = owner.paths["claim"]
    original = path.read_bytes()
    if mutation == "bytes":
        path.write_bytes(b"changed synthetic claim\n")
    elif mutation == "chmod":
        path.chmod(0o644)
    elif mutation == "replace":
        path.unlink()
        path.write_bytes(original)
        path.chmod(0o600)
    elif mutation == "hardlink":
        os.link(path, path.with_name("foreign-link"))
    elif mutation == "symlink":
        other = path.with_name("foreign-target")
        path.rename(other)
        path.symlink_to(other)
    else:
        path.with_name("foreign-file").write_bytes(b"unexpected\n")
    try:
        with pytest.raises(attempt.AttemptError):
            owner.verify_owned()
        with pytest.raises(attempt.AttemptError):
            owner.allowed_paths()
    finally:
        owner.close()


def test_owned_ledger_stream_binds_each_fsynced_append_and_keeps_identity_after_close(
    attempt, tmp_path
):
    owner = _synthetic_artifacts(attempt, tmp_path / "owned-ledger")
    stream = owner.create_stream("ledger")
    path = owner.paths["ledger"]
    try:
        owner.verify_owned()
        first = b'{"sequence":0,"synthetic_fixture_only":true}\n'
        stream.write(first)
        stream.flush()
        os.fsync(stream.fileno())
        owner.record_append("ledger", first)
        assert owner.allowed_paths() == {path.name}
        owner.verify_owned()
        second = b'{"sequence":1,"synthetic_fixture_only":true}\n'
        stream.write(second)
        stream.flush()
        os.fsync(stream.fileno())
        owner.record_append("ledger", second)
        owner.close_stream("ledger")
        assert path.read_bytes() == first + second
        owner.verify_owned()
    finally:
        owner.close()


def test_owned_ledger_rejects_unrecorded_or_wrong_appended_bytes(attempt, tmp_path):
    owner = _synthetic_artifacts(attempt, tmp_path / "wrong-ledger")
    stream = owner.create_stream("ledger")
    actual = b"actual synthetic bytes\n"
    stream.write(actual)
    stream.flush()
    os.fsync(stream.fileno())
    try:
        with pytest.raises(attempt.AttemptError):
            owner.record_append("ledger", b"different bytes\n")
        assert owner.paths["ledger"].read_bytes() == actual
        with pytest.raises(attempt.AttemptError):
            owner.verify_owned()
    finally:
        owner.close()


@pytest.mark.parametrize(
    "staging,final",
    [
        ("json_staging", "json"),
        ("markdown_staging", "markdown"),
        ("commit_staging", "commit"),
    ],
)
def test_owned_atomic_publication_keeps_creation_provenance_after_staging_unlink(
    attempt, tmp_path, staging, final
):
    owner = _synthetic_artifacts(attempt, tmp_path / final)
    raw = b"synthetic frozen output\n"
    try:
        owner.publish(staging, final, raw)
        assert not owner.paths[staging].exists()
        assert owner.paths[final].read_bytes() == raw
        assert owner.paths[final].stat().st_nlink == 1
        assert owner.allowed_paths() == {owner.paths[final].name}
        owner.verify_owned()
        with pytest.raises(attempt.AttemptError):
            owner.publish(staging, final, b"replacement\n")
        assert owner.paths[final].read_bytes() == raw
    finally:
        owner.close()


@pytest.mark.parametrize("stage", ["staging_exists", "destination_exists"])
def test_owned_publication_refuses_foreign_staging_or_destination_without_overwrite(
    attempt, tmp_path, stage
):
    owner = _synthetic_artifacts(attempt, tmp_path / stage)
    path = owner.paths["json_staging" if stage == "staging_exists" else "json"]
    path.write_bytes(b"foreign fixed bytes\n")
    try:
        with pytest.raises(attempt.AttemptError):
            owner.publish("json_staging", "json", b"replacement\n")
        assert path.read_bytes() == b"foreign fixed bytes\n"
    finally:
        owner.close()


@pytest.mark.parametrize(
    "action", ["unknown_role", "startup_role", "claim_stream", "wrong_pair"]
)
def test_owned_artifact_roles_do_not_expand_authorized_scope(attempt, tmp_path, action):
    owner = _synthetic_artifacts(attempt, tmp_path / action)
    try:
        with pytest.raises(attempt.AttemptError):
            if action == "unknown_role":
                owner.create_bytes("arbitrary", b"synthetic\n")
            elif action == "startup_role":
                owner.create_bytes("startup", b"synthetic\n")
            elif action == "claim_stream":
                owner.create_stream("claim")
            else:
                owner.publish("json_staging", "commit", b"synthetic\n")
    finally:
        owner.close()


def test_owned_artifact_write_failure_is_terminal_and_preserves_partial_bytes(
    attempt, monkeypatch, tmp_path
):
    owner = _synthetic_artifacts(attempt, tmp_path / "failed-owned-write")
    real_write = os.write
    calls = []

    def short(descriptor, raw):
        calls.append(bytes(raw))
        return real_write(descriptor, raw[:7])

    monkeypatch.setattr(attempt.os, "write", short)
    try:
        with pytest.raises(attempt.AttemptError):
            owner.create_bytes("claim", b"synthetic claim bytes\n")
        assert owner.paths["claim"].read_bytes() == b"synthet"
        with pytest.raises(attempt.AttemptError):
            owner.create_bytes("claim", b"synthetic retry\n")
        assert len(calls) == 1
    finally:
        owner.close()


@pytest.mark.parametrize(
    "relative",
    [
        "src/lotto649/v12_0_2_registered_attempt.py",
        "src/lotto649/v12_0_2_evidence.py",
        "tools/run_v12_0_2_historical.py",
    ],
)
def test_new_historical_sources_satisfy_frozen_static_capability_inventory(
    attempt, relative
):
    # Source text only: no runtime closure, authorizer or worker is instantiated.
    attempt._check_source_safety(relative, ast.parse((ROOT / relative).read_text()))


def test_registered_i3_paths_and_runtime_roots_are_explicit_and_separate(attempt):
    config = json.loads(
        (
            ROOT / "config/research-v12-0-2-post-rng-parity-composition-transition.yaml"
        ).read_bytes()
    )
    registration = json.loads(
        (
            ROOT
            / "evidence/research_registrations/v12-post-rng-parity-composition-transition-v3.json"
        ).read_bytes()
    )
    assert set(attempt.IMPLEMENTATION_PATHS) == set(
        registration["expected_implementation_paths"]
    )
    assert len(attempt.IMPLEMENTATION_PATHS) == 6
    assert attempt.CORE_PATH not in attempt.IMPLEMENTATION_PATHS
    assert set(
        registration["historical_runtime_dependency_closure"]["seed_paths"]
    ).issubset(set(attempt._CLOSURE_ROOTS))
    assert attempt.COMMAND == config["canonical_command"]
    assert attempt.LEASE_REF == config["repository_global_attempt_lease"]["ref"]
    assert set(attempt._ARTIFACT_NAMES.values()) == {
        Path(path).name for path in config["artifact_paths"].values()
    }


def test_owned_publication_parent_fsync_failure_preserves_both_names_without_retry(
    attempt, monkeypatch, tmp_path
):
    owner = _synthetic_artifacts(attempt, tmp_path / "publication-fsync")
    real_fsync = os.fsync
    real_link = os.link
    links = []

    def link(*args, **kwargs):
        result = real_link(*args, **kwargs)
        links.append((args, kwargs))
        return result

    def fsync(descriptor):
        if links:
            raise OSError("synthetic-private-parent-fsync")
        real_fsync(descriptor)

    monkeypatch.setattr(attempt.os, "link", link)
    monkeypatch.setattr(attempt.os, "fsync", fsync)
    try:
        with pytest.raises((attempt.AttemptError, OSError)):
            owner.publish("json_staging", "json", b"synthetic report\n")
        assert owner.paths["json_staging"].read_bytes() == b"synthetic report\n"
        assert owner.paths["json"].read_bytes() == b"synthetic report\n"
        with pytest.raises(attempt.AttemptError):
            owner.publish("json_staging", "json", b"synthetic replacement\n")
        assert len(links) == 1
    finally:
        owner.close()


def test_owned_stream_fsync_failure_never_advances_or_allows_another_append(
    attempt, monkeypatch, tmp_path
):
    owner = _synthetic_artifacts(attempt, tmp_path / "ledger-fsync")
    stream = owner.create_stream("ledger")
    raw = b"synthetic scientific event\n"
    stream.write(raw)
    stream.flush()
    calls = []

    def fail(descriptor):
        calls.append(descriptor)
        raise OSError("synthetic-private-file-fsync")

    monkeypatch.setattr(attempt.os, "fsync", fail)
    try:
        with pytest.raises((attempt.AttemptError, OSError)):
            owner.record_append("ledger", raw)
        with pytest.raises(attempt.AttemptError):
            owner.record_append("ledger", raw)
        assert len(calls) == 1
        assert owner.paths["ledger"].read_bytes() == raw
    finally:
        owner.close()


def test_owned_retired_staging_cannot_reappear_as_an_allowed_output(attempt, tmp_path):
    owner = _synthetic_artifacts(attempt, tmp_path / "retired-staging")
    owner.publish("json_staging", "json", b"synthetic frozen report\n")
    owner.paths["json_staging"].write_bytes(b"foreign staging reuse\n")
    try:
        with pytest.raises(attempt.AttemptError):
            owner.allowed_paths()
        assert owner.paths["json"].read_bytes() == b"synthetic frozen report\n"
    finally:
        owner.close()


@pytest.mark.parametrize("mutation", ["rename_parent", "unsafe_parent"])
def test_owned_artifact_parent_identity_and_permissions_remain_fixed(
    attempt, tmp_path, mutation
):
    directory = tmp_path / mutation
    owner = _synthetic_artifacts(attempt, directory)
    owner.create_bytes("claim", b"synthetic claim\n")
    if mutation == "rename_parent":
        directory.rename(tmp_path / "moved")
        directory.mkdir()
    else:
        directory.chmod(0o777)
    try:
        with pytest.raises(attempt.AttemptError):
            owner.verify_owned()
    finally:
        owner.close()


def test_owned_artifact_synthetic_factory_rejects_dangling_git_marker(
    attempt, tmp_path
):
    (tmp_path / ".git").symlink_to(tmp_path / "absent")
    directory = tmp_path / "synthetic-output"
    with pytest.raises(attempt.AttemptError):
        _synthetic_artifacts(attempt, directory)
    assert not directory.exists()


def _source_function(name):
    tree = ast.parse((ROOT / "src/lotto649/v12_0_2_registered_attempt.py").read_text())
    return next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == name
    )


def _source_calls(function, name):
    return sorted(
        [
            node
            for node in ast.walk(function)
            if isinstance(node, ast.Call) and ast.unparse(node.func) == name
        ],
        key=lambda node: node.lineno,
    )


def _assigned_value(function, name):
    return next(
        node.value
        for node in function.body
        if isinstance(node, (ast.Assign, ast.AnnAssign))
        and (
            (
                isinstance(node, ast.Assign)
                and any(
                    isinstance(target, ast.Name) and target.id == name
                    for target in node.targets
                )
            )
            or (
                isinstance(node, ast.AnnAssign)
                and isinstance(node.target, ast.Name)
                and node.target.id == name
            )
        )
    )


def _dict_expressions(node):
    assert isinstance(node, ast.Dict)
    return {
        key.value: value
        for key, value in zip(node.keys, node.values, strict=True)
        if isinstance(key, ast.Constant)
    }


def test_canonical_composition_source_freezes_checkpoint_claim_ledger_and_startup_before_history():
    # This is an explicit source-order audit. The canonical function is never run
    # in I3 tests; dynamic ordering is exercised through the synthetic components.
    function = _source_function("_run_canonical")
    consume = _source_calls(function, "_consume_lease")[0]
    checkpoint = _source_calls(function, "authority.startup.checkpoint")[0]
    create_claim = _source_calls(function, "owner.create_bytes")[0]
    first_event = _source_calls(function, "ledger.append")[0]
    startup_events = _source_calls(function, "authority.startup.append")
    seal = _source_calls(function, "authority.startup.seal")[0]
    active = _source_calls(function, "_ACTIVE_ATTEMPTS.append")[0]
    load = _source_calls(function, "_load_governed_history")[0]
    assert [call.args[0].value for call in startup_events] == [
        "claim_created",
        "scientific_ledger_started",
        "history_load_intent",
    ]
    positions = [
        consume.lineno,
        checkpoint.lineno,
        create_claim.lineno,
        first_event.lineno,
        *(call.lineno for call in startup_events),
        seal.lineno,
        active.lineno,
        load.lineno,
    ]
    assert positions == sorted(set(positions))
    assert create_claim.args[0].value == "claim"
    assert first_event.args[0].value == "attempt_claimed"
    first_payload = _dict_expressions(first_event.args[1])
    assert ast.unparse(first_payload["claim_sha256"]) == "claim_sha256"
    assert ast.unparse(first_payload["startup_checkpoint"]) == "checkpoint"
    bindings = _dict_expressions(_assigned_value(function, "bindings"))
    assert ast.unparse(bindings["startup_checkpoint"]) == "checkpoint"
    assert (
        ast.unparse(bindings["verified_facts_sha256"])
        == "_sha(_canonical(facts_preimage))"
    )
    claim_json = next(
        node
        for node in ast.walk(create_claim)
        if isinstance(node, ast.Dict)
        and any(
            isinstance(key, ast.Constant)
            and key.value == "verified_authorization_facts"
            for key in node.keys
        )
    )
    claim_fields = _dict_expressions(claim_json)
    assert ast.unparse(claim_fields["verified_authorization_facts"]) == "facts_preimage"
    assert ast.unparse(claim_fields["bindings"]) == "bindings"
    assert not any(
        isinstance(node, ast.Attribute) and node.attr in {"digest_sha256", "byte_count"}
        for node in ast.walk(claim_json)
    )
    # Every valid history exposure rechecks the sealed original FD and all current
    # owned outputs via the complete-clean boundary, after the startup seal.
    clean_checks = _source_calls(function, "git.require_full_clean")
    assert any(seal.lineno < check.lineno < load.lineno for check in clean_checks)


def test_final_manifest_source_binds_full_sealed_startup_separately_from_checkpoint():
    function = _source_function("_publish_git_manifest")
    file_keys = _assigned_value(function, "file_keys")
    assert isinstance(file_keys, ast.Tuple)
    assert [node.value for node in file_keys.elts] == [
        "startup",
        "claim",
        "ledger",
        "json",
        "markdown",
    ]
    manifest = _dict_expressions(_assigned_value(function, "manifest"))
    assert ast.unparse(manifest["startup_checkpoint"]) == "dict(startup_checkpoint)"
    sealed = _dict_expressions(manifest["sealed_startup"])
    assert ast.unparse(sealed["bytes"]) == "authority.startup.byte_count"
    assert ast.unparse(sealed["sha256"]) == "authority.startup.digest_sha256"
    assert (
        manifest["self_reference"].value
        == "containing_commit_resolved_from_Git_object_not_embedded"
    )
    assert "artifact_commit" not in manifest
    asserts_sealed = [
        node
        for node in function.body
        if isinstance(node, ast.If)
        and ast.unparse(node.test) == "not authority.startup.sealed"
    ]
    assert len(asserts_sealed) == 1
    assert asserts_sealed[0].lineno < _source_calls(function, "owner.publish")[0].lineno
    assert (
        _source_calls(function, "git.require_full_clean")[0].lineno
        < asserts_sealed[0].lineno
    )


def test_history_source_read_is_guarded_by_active_claim_sealed_startup_and_cleanliness():
    function = _source_function("_load_governed_history")
    load = _source_calls(function, "load_published_history")[0]
    assert ast.unparse(load.args[1]) == "HISTORY_AUTHORITY"
    conditions = [
        node
        for node in function.body
        if isinstance(node, ast.If) and node.lineno < load.lineno
    ]
    assert any("_ACTIVE_ATTEMPTS" in ast.unparse(node.test) for node in conditions)
    assert any(
        ast.unparse(node.test) == "not authority.startup.sealed" for node in conditions
    )
    clean = [
        node
        for node in ast.walk(function)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "require_full_clean"
    ]
    assert len(clean) == 1 and clean[0].lineno < load.lineno


def test_canonical_main_source_read_only_authority_precedes_startup_lease_and_worker():
    function = _source_function("main")
    names = [
        "verify_authorization",
        "begin_authorized_startup",
        "acquire_historical_lease",
        "_run_canonical",
    ]
    calls = [_source_calls(function, name) for name in names]
    assert all(len(group) == 1 for group in calls)
    positions = [group[0].lineno for group in calls]
    assert positions == sorted(set(positions))
    facts_function = _source_function("verify_authorization")
    assert not _source_calls(facts_function, "_issue_authorization")
    assert not _source_calls(facts_function, "StartupJournal._from_verified_facts")
    assert len(_source_calls(facts_function, "_issue_verified_facts")) == 1
