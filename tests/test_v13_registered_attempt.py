"""Synthetic-only tests for V13.0.0 execution boundaries.

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
import shlex
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Self

import pytest

ROOT = Path(__file__).resolve().parents[1]


LAUNCHER = ROOT / "tools/run_v13_historical.py"


@pytest.fixture
def launcher():
    loaded = runpy.run_path(str(LAUNCHER), run_name="synthetic_launcher_fixture")
    return loaded["main"].__globals__


def _launcher_sys(*, arguments=None, version=None):
    return SimpleNamespace(
        argv=[str(LAUNCHER), *(arguments or ["--consume-v13-once"])],
        implementation=SimpleNamespace(name="cpython"),
        version_info=(3, 12, 11) if version is None else version,
        flags=SimpleNamespace(isolated=False, no_site=False),
        dont_write_bytecode=False,
        executable="/synthetic/venv/bin/python3.12",
        stderr=sys.stderr,
        path=[],
    )


@pytest.mark.parametrize(
    "arguments",
    [[], ["--consume-v12-once"], ["--consume-v13-once", "--retry"]],
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
        "--consume-v13-once",
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
    from lotto649 import v13_registered_attempt

    return v13_registered_attempt


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
            attempt._API_PREFIX + "/git/ref/heads/v13-consumption-v13.0.0",
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
            attempt._API_PREFIX + "/git/ref/heads/v13-consumption-v13.0.0",
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
            attempt._API_PREFIX + "/git/ref/heads/v13-consumption-v13.0.0",
            allow_absent=True,
        )
    assert len(calls) == 1


@pytest.mark.parametrize(
    "method,path,payload,allow_absent",
    [
        ("DELETE", "/git/refs/heads/v13-consumption-v13.0.0", None, False),
        ("PATCH", "/git/refs/heads/v13-consumption-v13.0.0", {"sha": "a" * 40}, False),
        ("GET", "/git/ref/heads/main", None, True),
        ("GET", "/git/commits/abc123", None, False),
        ("POST", "/git/refs", {"ref": "refs/heads/main", "sha": "a" * 40}, False),
        (
            "POST",
            "/git/refs",
            {"ref": "refs/heads/v13-consumption-v12.0.0", "sha": "a" * 40},
            False,
        ),
        (
            "POST",
            "/git/refs",
            {"ref": "refs/heads/v13-consumption-v13.0.0", "sha": "abc123"},
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
    from datetime import date, timedelta

    from lotto649 import v13_evidence as evidence
    from lotto649.domain import Draw
    from lotto649.models.v13_main_set_overlap import (
        MainDraw,
        forecast_candidate,
        forecast_control,
    )

    targets = (date(2020, 1, 1), date(2020, 1, 4))
    base = Draw(date(2019, 12, 28), (1, 2, 3, 4, 5, 6))
    initial = []
    day = date(2019, 5, 15)
    while day <= base.draw_date:
        if day.weekday() in {2, 5}:
            initial.append(Draw(day, (1, 2, 3, 4, 5, 6)))
        day += timedelta(days=1)
    actual = {
        targets[0]: Draw(targets[0], first_main),
        targets[1]: Draw(targets[1], (37, 39, 41, 43, 45, 47)),
    }
    calls = {"prefix": [], "forecast": [], "reveal": [], "notify": []}

    def prefix_for(target):
        calls["prefix"].append(target)
        return (*initial, *(actual[earlier] for earlier in targets if earlier < target))

    def forecast(prefix, target):
        calls["forecast"].append(target)
        fair = {label: 6.0 / 49.0 for label in range(1, 50)}
        return [
            evidence.serialize_overlap_forecast(
                forecast_candidate(
                    tuple(MainDraw(row.draw_date, row.numbers) for row in prefix),
                    target,
                )
            ),
            evidence.serialize_overlap_forecast(
                forecast_control(
                    tuple(MainDraw(row.draw_date, row.numbers) for row in prefix),
                    target,
                )
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
        "bindings": {
            "fixture": "durable-regression",
            "seed": 649,
            "pure_core_sha256": "a" * 64,
            "statistical_fingerprint_sha256": attempt.FINGERPRINT,
            "operational_contract_sha256": attempt.OPERATIONAL_SHA256,
        },
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


def test_durable_exact_final6_stops_before_next_prefix_without_worker_mail(
    attempt, tmp_path
):
    case = _durable_case(first_main=(1, 2, 3, 4, 5, 6))
    directory = tmp_path / "synthetic-exact-final6"
    report = _durable_run(attempt, directory, case)
    assert all(
        case.calls[key] == [case.targets[0]] for key in ("prefix", "forecast", "reveal")
    )
    assert not case.calls["notify"]
    assert report["disposition"] == "pending_audit"
    assert report["gates"] is None
    assert report["processed_target_count"] == 1
    assert report["targets"][0]["exact_final6_opportunities"]
    kinds = [event["event_kind"] for event in _durable_events(attempt, directory)]
    assert kinds.count("historical_6of6_candidate_detected") == 1
    assert kinds.index("target_revealed_scored") < kinds.index(
        "historical_6of6_candidate_detected"
    )
    assert not any("notification" in kind for kind in kinds)


def test_durable_top12_records_and_continues_without_worker_mail(attempt, tmp_path):
    case = _durable_case(first_main=(7, 8, 9, 10, 11, 12))
    directory = tmp_path / "synthetic-top12"
    report = _durable_run(attempt, directory, case)
    assert case.calls["forecast"] == case.calls["reveal"] == list(case.targets)
    assert not case.calls["notify"]
    assert report["processed_target_count"] == 2
    assert report["stop_reason"] is None
    kinds = [event["event_kind"] for event in _durable_events(attempt, directory)]
    assert kinds.count("historical_top12_all_six_detected") == 1
    assert not any("notification" in kind for kind in kinds)
    assert "historical_6of6_candidate_detected" not in kinds
    assert report["audit"]["warnings"] == []


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
    ["R13", "HISTORY_AUTHORITY", "LEASE_REF", "REPOSITORY", "AUTHORIZATION_PATH"],
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
    manifest = json.loads(paths["manifest"].read_bytes())
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


def _rewrite_synthetic_events(attempt, path, events):
    previous = "0" * 64
    raw = []
    for sequence, event in enumerate(events):
        event.pop("event_sha256", None)
        event["sequence"] = sequence
        event["previous_event_sha256"] = previous
        previous = hashlib.sha256(attempt._canonical(event)).hexdigest()
        event["event_sha256"] = previous
        raw.append(attempt._canonical(event) + b"\n")
    path.write_bytes(b"".join(raw))


def test_durable_auditor_rejects_reveal_without_frozen_prediction(attempt, tmp_path):
    directory = tmp_path / "synthetic-unfrozen"
    _durable_run(attempt, directory, _durable_case())
    path = attempt._paths(directory, synthetic=True)["ledger"]
    events = _durable_events(attempt, directory)
    _rewrite_synthetic_events(attempt, path, [events[0], *events[2:]])
    with pytest.raises(attempt.AttemptError, match="reveal lacks"):
        attempt.audit_ledger(path)


def test_durable_auditor_rejects_rehashed_reverse_target_order(attempt, tmp_path):
    directory = tmp_path / "synthetic-reversed"
    _durable_run(attempt, directory, _durable_case())
    path = attempt._paths(directory, synthetic=True)["ledger"]
    events = _durable_events(attempt, directory)
    assert len(events) == 5
    _rewrite_synthetic_events(
        attempt, path, [events[0], events[3], events[4], events[1], events[2]]
    )
    with pytest.raises(
        attempt.AttemptError, match="chronological|exact frozen forecast receipt"
    ):
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
            [*warnings, "source_integrity_failure"],
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


# R13 additions below use independently fabricated metadata and fail guards.  The
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
        (ROOT / "tests/fixtures/v13_git_commit_projection.json").read_bytes()
    )


@pytest.fixture(autouse=True)
def forbid_production_execution_and_network(monkeypatch, attempt):
    def forbidden(*_args, **_kwargs):
        pytest.fail(
            "I13 synthetic tests must not create production authority or read history"
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
        (("ref",), "refs/heads/v13-consumption-v12.0.1"),
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


def _author_payload(*, phase="I13", contributors=None):
    return {
        "schema_version": "lotto649-v13-source-author-provenance-v1",
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


@pytest.mark.parametrize("phase", ["I13", "A_H_s13"])
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
        attempt._source_author_provenance(_raw_author_commit(payload), "I13")
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
        "duplicate_key": trailer.replace(
            b'"phase":"I13"', b'"phase":"I13","phase":"I13"'
        ),
    }[malformation]
    with pytest.raises(attempt.AuthorizationError):
        attempt._source_author_provenance(_raw_author_commit(message=malformed), "I13")


@pytest.mark.parametrize(
    "field,value",
    [
        ("phase", "I2"),
        ("phase", "A_H_s13"),
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
        attempt._source_author_provenance(_raw_author_commit(payload), "I13")


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
        attempt._source_author_provenance(_raw_author_commit(payload), "I13")


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
        attempt._source_author_provenance(_raw_author_commit(payload), "I13")


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
def test_unissued_transport_rejects_even_exact_post_body_before_sending(
    attempt, monkeypatch, projection, route, request_key, response_key
):
    body = _canonical_fixture(projection[request_key])
    api, calls = _http_fixture(
        attempt,
        monkeypatch,
        _HttpResponse(status=201, body=_canonical_fixture(projection[response_key])),
    )
    with pytest.raises(attempt.AuthorizationError):
        api.request_json("POST", attempt._API_PREFIX + route, body_bytes=body)
    assert not calls and api.last_status is None
    with pytest.raises(attempt.AuthorizationError):
        api.request_json("POST", attempt._API_PREFIX + route, body_bytes=body)
    assert not calls


@pytest.mark.parametrize(
    "route,request_key",
    [("/git/commits", "post_commit_request"), ("/git/refs", "post_ref_request")],
)
def test_unissued_transport_never_reaches_prepared_failure_response(
    attempt, monkeypatch, projection, route, request_key
):
    body = _canonical_fixture(projection[request_key])
    api, calls = _http_fixture(
        attempt, monkeypatch, OSError("synthetic-private-transport-body")
    )
    with pytest.raises(attempt.AuthorizationError) as caught:
        api.request_json("POST", attempt._API_PREFIX + route, body_bytes=body)
    assert "synthetic-private" not in str(caught.value)
    assert api.last_status is None
    with pytest.raises(attempt.AuthorizationError):
        api.request_json("POST", attempt._API_PREFIX + route, body_bytes=body)
    assert not calls


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
    state = {"phase": "I13", "contributors": contributors, "calls": []}
    for index, axis in enumerate(("standards", "spec")):
        attestation = {
            "schema_version": "lotto649-v13-i13-independent-review-v1",
            "axis": axis,
            "base_sha": base,
            "head_sha": head,
            "closure_sha256": closure,
            "operational_contract_sha256": attempt.OPERATIONAL_SHA256,
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
    comment["body"] = (_canonical_fixture(body) + b"\n").decode()
    fixture.records[index]["comment_body_sha256"] = hashlib.sha256(
        comment["body"].encode()
    ).hexdigest()


@pytest.mark.parametrize(
    "phase,schema",
    [
        ("I13", "lotto649-v13-i13-independent-review-v1"),
        ("A_H_s13", "lotto649-v13-ah13-independent-review-v1"),
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
    fixture.state["phase"] = "A_H_s13"
    for index in range(2):
        _change_review_body(
            fixture, index, "schema_version", "lotto649-v13-ah13-independent-review-v1"
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
            phase="A_H_s13",
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
        comments[0]["body"] = (_canonical_fixture(body) + b"\n").decode()
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
    # Inert validator exercise with deliberately nonproduction source identities.
    monkeypatch.setattr(attempt, "REPOSITORY", "synthetic/fixture.invalid")
    monkeypatch.setattr(attempt, "R13", "7" * 40)
    monkeypatch.setattr(attempt, "HISTORY_AUTHORITY", "8" * 40)
    monkeypatch.setattr(attempt, "REGISTRATION_PATH", "synthetic/registration.json")
    monkeypatch.setattr(attempt, "AUTHORIZATION_PATH", "synthetic/authorization.json")
    monkeypatch.setattr(attempt, "COMMAND", ["synthetic-never-execute"])
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
    ids["base"] = ids["implementation_merge"]
    registration = b"synthetic registration identity"
    core = b"# fabricated synthetic core source, never executed\n"
    core_sha256 = hashlib.sha256(core).hexdigest()
    requirements = b"# fabricated synthetic dependency manifest\n"
    monkeypatch.setattr(
        attempt, "REQUIREMENTS_SHA256", hashlib.sha256(requirements).hexdigest()
    )
    closure = [{"path": attempt.CORE_PATH, "git_blob": "a" * 40, "sha256": core_sha256}]
    source_bytes = {
        path: ("synthetic fixed source " + path + "\n").encode()
        for path in attempt.IMPLEMENTATION_PATHS
    }
    source_bytes[attempt.CORE_PATH] = core
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
        "schema_version": "lotto649-v13.0.0-historical-authorization-v1",
        "experiment_id": "synthetic_contract",
        "model_version": "v13.0.0",
        "repository": attempt.REPOSITORY,
        "branch": "main",
        "registration_commit": attempt.R13,
        "registration_sha256": hashlib.sha256(registration).hexdigest(),
        "scientific_registration_commit": attempt.R13,
        "statistical_fingerprint_sha256": attempt.FINGERPRINT,
        "pure_core_sha256": core_sha256,
        "operational_contract_sha256": attempt.OPERATIONAL_SHA256,
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
            if path == attempt.REGISTRATION_PATH:
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
                ids["implementation"]: (ids["implementation_base"],),
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
        return {}, {
            "identity": {
                "experiment_id": "synthetic_contract",
                "governed_history_identity": {"synthetic_metadata": True},
            }
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
    monkeypatch.setattr(attempt, "_verify_registered_numerics", lambda _science: None)
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
    assert fixture.state["read_core"] == [
        expected[0],
        *(oid for oid in expected for _ in range(2)),
    ]
    assert fixture.state["read_lock"] == expected
    assert fixture.state["closure_reads"] == expected
    assert fixture.state["registered_reads"] == [fixture.ids["head"], *expected]
    assert fixture.state["review_phases"] == ["I13", "A_H_s13"]
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
        attempt._source_author_provenance(raw, "I13")


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


def test_v13_source_rejects_all_old_runtime_imports_and_has_new_core_boundary(attempt):
    tree = ast.parse((ROOT / "src/lotto649/v13_registered_attempt.py").read_bytes())
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert "v12" not in (node.module or "")
        if isinstance(node, ast.Import):
            assert all("v12" not in alias.name for alias in node.names)
    assert attempt.CORE_PATH in attempt.IMPLEMENTATION_PATHS
    assert len(attempt.IMPLEMENTATION_PATHS) == 8
    assert attempt.COMMAND == [
        "python3.12",
        "tools/run_v13_historical.py",
        "--consume-v13-once",
    ]


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
        ("manifest_staging", "manifest"),
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
        "src/lotto649/v13_registered_attempt.py",
        "src/lotto649/v13_evidence.py",
        "tools/run_v13_historical.py",
    ],
)
def test_new_historical_sources_satisfy_frozen_static_capability_inventory(
    attempt, relative
):
    # Source text only: no runtime closure, authorizer or worker is instantiated.
    attempt._check_source_safety(relative, ast.parse((ROOT / relative).read_text()))


def test_registered_i13_paths_runtime_roots_and_closed_auth_fields_are_explicit(
    attempt,
):
    assert len(attempt.IMPLEMENTATION_PATHS) == 8
    assert attempt.CORE_PATH in attempt.IMPLEMENTATION_PATHS
    assert attempt.CORE_PATH in attempt._CLOSURE_ROOTS
    assert set(attempt._ARTIFACT_NAMES) == {
        "startup",
        "claim",
        "ledger",
        "json",
        "markdown",
        "manifest",
        "json_staging",
        "markdown_staging",
        "manifest_staging",
    }
    assert attempt.LEASE_REF == "refs/heads/v13-consumption-v13.0.0"
    assert attempt._NOTIFICATION_REF == "refs/heads/v13-notification-v13.0.0"
    assert len(attempt._EXACT_RUNTIME["installed_distributions"]) == 27
    assert attempt._EXACT_RUNTIME["python_version"] == "3.12.11"


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
    tree = ast.parse((ROOT / "src/lotto649/v13_registered_attempt.py").read_text())
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
    # in I13 tests; dynamic ordering is exercised through the synthetic components.
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


# V13-only global notification protocol. All service state and callbacks below
# are synthetic fixtures; no requests/SMTP/production authority is reachable.
class _SyntheticSharedNotificationService:
    def __init__(self, attempt, *, failure=None, barrier=None):
        from threading import Lock

        self.attempt = attempt
        self.failure = failure
        self.barrier = barrier
        self.lock = Lock()
        self.ref = None
        self.commits = {}
        self.calls = []

    def get_ref(self, reference):
        assert reference == self.attempt._SYNTHETIC_NOTIFICATION_REF
        self.calls.append(("get_ref", reference))
        if self.failure == "absence_redirect":
            return 302, {"message": "Not Found"}
        if self.failure == "absence_malformed":
            return 404, {"message": "not found"}
        if self.failure == "absence_boolean":
            return True, {"message": "Not Found"}
        if self.failure == "reread_unknown" and self.ref is not None:
            raise TimeoutError("synthetic diagnostic must not escape")
        if self.ref is None:
            return 404, {"message": "Not Found"}
        oid = "0" * 40 if self.failure == "reread_mismatch" else self.ref
        return 200, self.ref_response(reference, oid)

    def ref_response(self, reference, oid):
        return {
            "ref": reference,
            "node_id": "synthetic-node",
            "url": self.attempt._API_ORIGIN
            + self.attempt._API_PREFIX
            + "/git/"
            + reference,
            "object": {
                "sha": oid,
                "type": "commit",
                "url": self.attempt._API_ORIGIN
                + self.attempt._API_PREFIX
                + "/git/commits/"
                + oid,
            },
        }

    def post_commit(self, raw):
        self.calls.append(("post_commit", raw))
        request = json.loads(raw)
        oid, _raw, _message = self.attempt._notification_request_parts(
            request, synthetic=True
        )
        with self.lock:
            self.commits[oid] = request
        if self.barrier:
            self.barrier.wait(timeout=10)
        if self.failure == "commit_unknown":
            raise TimeoutError("synthetic diagnostic must not escape")
        if self.failure == "commit_wrong_oid":
            return 201, {"sha": "0" * 40}
        return 201, {"sha": oid}

    def create_ref(self, raw):
        self.calls.append(("create_ref", raw))
        request = json.loads(raw)
        assert request["ref"] == self.attempt._SYNTHETIC_NOTIFICATION_REF
        with self.lock:
            if self.ref is not None:
                return 422, {"message": "Reference already exists"}
            self.ref = request["sha"]
        if self.failure == "ref_unknown":
            raise TimeoutError("synthetic diagnostic must not escape")
        return 201, self.ref_response(request["ref"], request["sha"])

    def get_commit(self, oid):
        self.calls.append(("get_commit", oid))
        request = self.commits[oid]
        origin, prefix = self.attempt._API_ORIGIN, self.attempt._API_PREFIX
        parent = request["parents"][0]
        value = {
            "sha": oid,
            "node_id": "synthetic-node",
            "url": origin + prefix + "/git/commits/" + oid,
            "html_url": "https://github.com/"
            + self.attempt.REPOSITORY
            + "/commit/"
            + oid,
            "author": request["author"],
            "committer": request["committer"],
            "tree": {
                "sha": request["tree"],
                "url": origin + prefix + "/git/trees/" + request["tree"],
            },
            "parents": [
                {
                    "sha": parent,
                    "url": origin + prefix + "/git/commits/" + parent,
                    "html_url": "https://github.com/"
                    + self.attempt.REPOSITORY
                    + "/commit/"
                    + parent,
                }
            ],
            "message": request["message"][:-1],
            "verification": {
                "verified": False,
                "reason": "unsigned",
                "signature": None,
                "payload": None,
                "verified_at": None,
            },
        }
        if self.failure == "get_message_lf":
            value["message"] += "\n"
        if self.failure == "get_extra":
            value["author"] = {**value["author"], "extra": 1}
        return value


def _notification_case(attempt, tmp_path, *, failure=None):
    service = _SyntheticSharedNotificationService(attempt, failure=failure)
    invocation = attempt.prepare_synthetic_notification(
        tmp_path / "synthetic-notify", service
    )
    return service, invocation


def _notification_events(attempt, invocation):
    path = attempt._NOTIFICATION_STATES[invocation]["paths"]["journal"]
    return [json.loads(line) for line in path.read_bytes().splitlines()]


def test_v13_notification_concurrent_fresh_clones_two_uploads_one_atomic_winner_one_send(
    attempt, tmp_path
):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier, Lock

    service = _SyntheticSharedNotificationService(attempt, barrier=Barrier(2))
    left = attempt.prepare_synthetic_notification(tmp_path / "synthetic-left", service)
    right = attempt.prepare_synthetic_notification(
        tmp_path / "synthetic-right", service
    )
    sent = []
    lock = Lock()

    def sender(subject, body):
        with lock:
            sent.append((subject, body))
        return True

    def drive(invocation):
        try:
            return attempt.run_synthetic_notification(
                invocation, service, sender, pre_send=lambda: None
            )
        except attempt.AttemptError:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(drive, (left, right)))
    assert sum(result is not None for result in results) == 1
    assert next(result for result in results if result)["result"] == "sent"
    assert len(sent) == 1
    assert len(service.commits) == 2
    assert sum(name == "create_ref" for name, _ in service.calls) == 2
    assert service.ref in service.commits
    for invocation in (left, right):
        with pytest.raises(attempt.AttemptError):
            attempt.run_synthetic_notification(
                invocation, service, sender, pre_send=lambda: None
            )
    assert len(sent) == 1


@pytest.mark.parametrize(
    "failure", ["absence_redirect", "absence_malformed", "absence_boolean"]
)
def test_v13_notification_requires_fresh_exact_literal_404_before_files(
    attempt, tmp_path, failure
):
    service = _SyntheticSharedNotificationService(attempt, failure=failure)
    with pytest.raises(attempt.AttemptError):
        attempt.prepare_synthetic_notification(tmp_path / "synthetic-absent", service)
    assert not (tmp_path / "synthetic-absent").exists()
    assert service.commits == {}


def test_v13_notification_present_identical_oid_cannot_issue_or_adopt(
    attempt, tmp_path
):
    service, invocation = _notification_case(attempt, tmp_path)
    service.ref = attempt._NOTIFICATION_STATES[invocation]["expected"]
    with pytest.raises(attempt.AttemptError):
        attempt.prepare_synthetic_notification(tmp_path / "synthetic-second", service)
    sent = []
    with pytest.raises(attempt.AttemptError):
        attempt.run_synthetic_notification(
            invocation, service, lambda *args: sent.append(args), pre_send=lambda: None
        )
    assert not sent
    assert service.ref == attempt._NOTIFICATION_STATES[invocation]["expected"]


@pytest.mark.parametrize(
    "failure",
    [
        "commit_unknown",
        "commit_wrong_oid",
        "ref_unknown",
        "reread_unknown",
        "reread_mismatch",
        "get_message_lf",
        "get_extra",
    ],
)
def test_v13_notification_uncertain_or_mismatched_edge_preserves_bytes_and_never_retries(
    attempt, tmp_path, failure
):
    service, invocation = _notification_case(attempt, tmp_path, failure=failure)
    sent = []
    with pytest.raises(attempt.AttemptError) as caught:
        attempt.run_synthetic_notification(
            invocation, service, lambda *args: sent.append(args), pre_send=lambda: None
        )
    assert "synthetic diagnostic" not in str(caught.value)
    assert not sent
    state = attempt._NOTIFICATION_STATES[invocation]
    before = {
        name: path.read_bytes()
        for name, path in state["paths"].items()
        if path.exists()
    }
    calls = list(service.calls)
    with pytest.raises(attempt.AttemptError):
        attempt.run_synthetic_notification(
            invocation, service, lambda *_: True, pre_send=lambda: None
        )
    assert service.calls == calls
    assert {
        name: path.read_bytes()
        for name, path in state["paths"].items()
        if path.exists()
    } == before
    assert sum(name == "post_commit" for name, _ in service.calls) == 1
    assert sum(name == "create_ref" for name, _ in service.calls) <= 1


@pytest.mark.parametrize("failure", ["main", "audit", "ownership"])
def test_v13_notification_winner_pre_send_failure_consumes_claim_without_takeover(
    attempt, tmp_path, failure
):
    service, invocation = _notification_case(attempt, tmp_path)
    sent = []

    def pre_send():
        if failure == "ownership":
            attempt._NOTIFICATION_STATES[invocation]["paths"]["intent"].write_bytes(
                b"synthetic replaced bytes"
            )
        else:
            raise attempt.AuthorizationError("synthetic main or audit changed")

    with pytest.raises(attempt.AttemptError):
        attempt.run_synthetic_notification(
            invocation, service, lambda *args: sent.append(args), pre_send=pre_send
        )
    assert service.ref is not None
    assert not sent
    with pytest.raises(attempt.AttemptError):
        attempt.prepare_synthetic_notification(tmp_path / "synthetic-takeover", service)


@pytest.mark.parametrize("outcome", [True, False, None, "exception", "timeout"])
def test_v13_notification_every_smtp_outcome_consumes_one_slot_without_retry(
    attempt, tmp_path, outcome
):
    service, invocation = _notification_case(attempt, tmp_path)
    sent = []

    def sender(subject, body):
        sent.append((subject, body))
        events = _notification_events(attempt, invocation)
        assert events[-1]["kind"] == "notification_send_intent"
        if outcome == "exception":
            raise RuntimeError("synthetic private detail")
        if outcome == "timeout":
            raise TimeoutError("synthetic uncertain SMTP")
        return outcome

    result = attempt.run_synthetic_notification(
        invocation, service, sender, pre_send=lambda: None
    )
    assert result["result"] == (
        "sent" if outcome is True else "failed" if outcome is False else "unknown"
    )
    assert len(sent) == 1
    assert len(_notification_events(attempt, invocation)) == 9
    with pytest.raises(attempt.AttemptError):
        attempt.run_synthetic_notification(
            invocation, service, sender, pre_send=lambda: None
        )
    with pytest.raises(attempt.AttemptError):
        attempt.prepare_synthetic_notification(tmp_path / "synthetic-restart", service)
    assert len(sent) == 1


def test_v13_notification_frozen_identity_claim_intent_journal_result_graph_is_acyclic(
    attempt, tmp_path
):
    service, invocation = _notification_case(attempt, tmp_path)
    state = attempt._NOTIFICATION_STATES[invocation]
    result = attempt.run_synthetic_notification(
        invocation, service, lambda *_: True, pre_send=lambda: None
    )
    intent = json.loads(state["paths"]["intent"].read_bytes())
    claim = json.loads(state["request"]["message"])
    assert (
        claim["intent_identity_sha256"]
        == hashlib.sha256(_canonical_fixture(intent["identity"]) + b"\n").hexdigest()
    )
    assert (
        claim["intent_identity_sha256"]
        != hashlib.sha256(state["paths"]["intent"].read_bytes()).hexdigest()
    )
    assert "intent_sha256" not in claim
    assert len(claim) == 11 and len(intent) == 12 and len(intent["identity"]) == 13
    assert (
        result["sealed_journal"]["sha256"]
        == hashlib.sha256(state["paths"]["journal"].read_bytes()).hexdigest()
    )
    events = _notification_events(attempt, invocation)
    assert (
        events[0]["payload"]["intent_sha256"]
        == hashlib.sha256(state["paths"]["intent"].read_bytes()).hexdigest()
    )
    previous = None
    for index, raw in enumerate(
        state["paths"]["journal"].read_bytes().splitlines(keepends=True)
    ):
        item = json.loads(raw)
        assert item["sequence"] == index
        assert item["previous_event_sha256"] == previous
        assert "event_sha256" not in item
        previous = hashlib.sha256(raw).hexdigest()
    for phase in ("notification_commit", "notification_ref"):
        event = next(item for item in events if item["kind"] == phase + "_POST_intent")
        wire = next(
            raw
            for name, raw in service.calls
            if name == ("post_commit" if phase.endswith("commit") else "create_ref")
        )
        assert (
            event["payload"]["request_body_sha256"] == hashlib.sha256(wire).hexdigest()
        )
        assert event["payload"]["request_body_bytes"] == len(wire)


@pytest.mark.parametrize(
    "change",
    [
        "add_lf",
        "strip_space",
        "author_extra",
        "parent_extra",
        "verification_extra",
        "wrong_tree",
        "wrong_purpose",
    ],
)
def test_v13_notification_raw_git_and_closed_nested_projection_never_normalize(
    attempt, tmp_path, change
):
    service, invocation = _notification_case(attempt, tmp_path)
    state = attempt._NOTIFICATION_STATES[invocation]
    service.post_commit(state["commit_bytes"])
    observed = copy.deepcopy(service.get_commit(state["expected"]))
    if change == "add_lf":
        observed["message"] += "\n"
    elif change == "strip_space":
        observed["message"] += " "
    elif change == "author_extra":
        observed["author"]["extra"] = 1
    elif change == "parent_extra":
        observed["parents"][0]["extra"] = 1
    elif change == "verification_extra":
        observed["verification"]["extra"] = 1
    elif change == "wrong_tree":
        observed["tree"]["sha"] = "0" * 40
    else:
        observed["message"] = observed["message"].replace(
            "notification-claim", "consumption-lease"
        )
    with pytest.raises(attempt.AuthorizationError):
        attempt._verify_notification_get(
            state["expected"], state["request"], observed, synthetic=True
        )
    attempt._notification_close(invocation)


def test_v13_notification_capability_cannot_be_constructed_copied_or_deserialized(
    attempt, tmp_path
):
    service, invocation = _notification_case(attempt, tmp_path)
    for constructor in (
        lambda: attempt._NotificationInvocation(),
        lambda: copy.copy(invocation),
        lambda: copy.deepcopy(invocation),
    ):
        with pytest.raises(attempt.AuthorizationError):
            constructor()
    for fabricated in ({}, object(), object.__new__(attempt._NotificationInvocation)):
        with pytest.raises(attempt.AttemptError):
            attempt.run_synthetic_notification(
                fabricated, service, lambda *_: True, pre_send=lambda: None
            )

    class Fake(attempt._NotificationInvocation):
        pass

    with pytest.raises(attempt.AttemptError):
        attempt.run_synthetic_notification(
            object.__new__(Fake), service, lambda *_: True, pre_send=lambda: None
        )
    attempt._notification_close(invocation)


def test_v13_notification_never_calls_historical_capabilities_or_worker(
    attempt, tmp_path, monkeypatch
):
    def forbidden(*_args, **_kwargs):
        pytest.fail("notification must not touch historical authority/history")

    for name in (
        "verify_authorization",
        "begin_authorized_startup",
        "acquire_historical_lease",
        "_run_canonical",
        "_load_governed_history",
        "_issue_authorization",
        "_issue_lease",
    ):
        monkeypatch.setattr(attempt, name, forbidden)
    service, invocation = _notification_case(attempt, tmp_path)
    result = attempt.run_synthetic_notification(
        invocation, service, lambda *_: True, pre_send=lambda: None
    )
    assert result["result"] == "sent"
    assert all(attempt.LEASE_REF not in str(value) for _name, value in service.calls)


def test_v13_worker_has_no_top12_or_final6_mail_route_or_callback(attempt):
    tree = ast.parse((ROOT / "src/lotto649/v13_registered_attempt.py").read_bytes())
    for name in ("_drive_sequence", "_run_canonical", "run_synthetic_attempt"):
        function = next(
            item
            for item in tree.body
            if isinstance(item, ast.FunctionDef) and item.name == name
        )
        assert not any(
            arg.arg == "notify"
            for arg in (*function.args.args, *function.args.kwonlyargs)
        )
        assert not any(
            isinstance(item, ast.Name)
            and item.id
            in {
                "send_email",
                "_default_notification",
                "notify_audited_capture",
                "prepare_synthetic_notification",
                "_issue_notification_files",
            }
            for item in ast.walk(function)
        )
    drive = next(
        item
        for item in tree.body
        if isinstance(item, ast.FunctionDef) and item.name == "_drive_sequence"
    )
    source = ast.get_source_segment(
        (ROOT / "src/lotto649/v13_registered_attempt.py").read_text(), drive
    )
    assert '"global_stop_search": True' in source
    assert "notification_attempt_started" not in source


def test_v13_notification_partial_fsync_preserves_intent_and_prevents_post(
    attempt, tmp_path, monkeypatch
):
    service, invocation = _notification_case(attempt, tmp_path)
    state = attempt._NOTIFICATION_STATES[invocation]
    original = state["paths"]["intent"].read_bytes()
    real_fsync = os.fsync
    journal_inode = state["paths"]["journal"].stat().st_ino

    def fail(descriptor):
        if os.fstat(descriptor).st_ino == journal_inode:
            raise OSError("synthetic fsync failure")
        real_fsync(descriptor)

    monkeypatch.setattr(attempt.os, "fsync", fail)
    with pytest.raises(attempt.AttemptError):
        attempt.run_synthetic_notification(
            invocation,
            service,
            lambda *_: pytest.fail("send forbidden"),
            pre_send=lambda: None,
        )
    assert state["paths"]["intent"].read_bytes() == original
    assert state["paths"]["journal"].exists()
    assert all(name != "post_commit" for name, _raw in service.calls)
    assert not state["paths"]["result"].exists()


def test_v13_pre_authorization_checks_all_registered_closed_scalar_hex_oracles(attempt):
    seal = json.loads((ROOT / attempt.REGISTRATION_PATH).read_bytes())
    assert (
        hashlib.sha256(
            _canonical_fixture(seal["scientific_contract"]) + b"\n"
        ).hexdigest()
        == attempt.FINGERPRINT
    )
    attempt._verify_registered_numerics(seal["scientific_contract"])


def test_v13_pre_authorization_rejects_changed_libm_scalar_without_any_forecast(
    attempt, monkeypatch
):
    from lotto649.models import v13_main_set_overlap as core

    seal = json.loads((ROOT / attempt.REGISTRATION_PATH).read_bytes())
    original = core.moments

    def changed(beta):
        mean, complement, log_z = original(beta)
        return mean, complement, log_z + 0.001

    monkeypatch.setattr(core, "moments", changed)
    with pytest.raises(attempt.AuthorizationError):
        attempt._verify_registered_numerics(seal["scientific_contract"])


@pytest.mark.parametrize(
    "mutation", [None, "extra", "missing", "duplicate", "wrong_patch", "wrong_platform"]
)
def test_v13_runtime_requires_exact_27_distributions_and_cpython_patch(
    attempt, tmp_path, monkeypatch, mutation
):
    root = tmp_path / "synthetic-runtime"
    manifest = root / attempt.REQUIREMENTS_PATH
    manifest.parent.mkdir(parents=True)
    manifest.write_bytes((ROOT / attempt.REQUIREMENTS_PATH).read_bytes())
    monkeypatch.setattr(
        attempt, "__file__", str(root / "src/lotto649/v13_registered_attempt.py")
    )
    installed = [
        SimpleNamespace(metadata={"Name": name}, version=version)
        for name, version in attempt._EXACT_RUNTIME["installed_distributions"].items()
    ]
    if mutation == "extra":
        installed.append(
            SimpleNamespace(metadata={"Name": "synthetic-extra"}, version="1.0")
        )
    elif mutation == "missing":
        installed.pop()
    elif mutation == "duplicate":
        installed.append(installed[0])
    monkeypatch.setattr(attempt, "distributions", lambda: installed)
    monkeypatch.setattr(
        attempt,
        "sys",
        SimpleNamespace(
            implementation=SimpleNamespace(name="cpython"),
            version_info=(3, 12, 12) if mutation == "wrong_patch" else (3, 12, 11),
            float_info=sys.float_info,
            byteorder="little",
        ),
    )
    monkeypatch.setattr(
        attempt,
        "platform",
        SimpleNamespace(
            python_version=lambda: "3.12.11",
            platform=lambda: (
                "synthetic-other"
                if mutation == "wrong_platform"
                else attempt._EXACT_RUNTIME["platform"]
            ),
            machine=lambda: "arm64",
        ),
    )
    if mutation is None:
        assert attempt.runtime_identity() == attempt._EXACT_RUNTIME
    else:
        with pytest.raises(attempt.AuthorizationError):
            attempt.runtime_identity()


@pytest.mark.parametrize(
    "module",
    [
        "v12_0_1_registered_attempt",
        "v12_0_2_registered_attempt",
        "v12_0_1_evidence",
        "v12_0_2_evidence",
        "models.v12_parity_transition",
    ],
)
def test_v13_static_closure_rejects_old_execution_modules_at_any_import_depth(
    attempt, module
):
    for source in (
        f"import lotto649.{module}\n",
        f"def hidden():\n    from lotto649.{module} import main\n",
    ):
        with pytest.raises(attempt.AuthorizationError):
            attempt._check_source_safety(attempt.ATTEMPT_PATH, ast.parse(source))


def test_v13_complete_static_closure_reads_source_only_and_contains_no_old_v12(
    attempt, monkeypatch
):
    # Same source-only test in a combined repository or this isolated draft overlay.
    root = ROOT if (ROOT / "src/lotto649/domain.py").is_file() else ROOT / "_harness"
    inventory = sorted(
        path.relative_to(root).as_posix() for path in (root / "src").rglob("*.py")
    )
    inventory.extend(
        path for path in attempt._CLOSURE_ROOTS if not path.startswith("src/")
    )
    allowed_assets = {
        attempt.REGISTRATION_PATH,
        attempt.CONFIG_PATH,
        "config.yaml",
        attempt.REQUIREMENTS_PATH,
    }
    reads = []

    class SourceOnlyGit:
        def __init__(self, _repository):
            self.root = root

        def run(self, *args):
            assert args == ("ls-tree", "-r", "--name-only", "1" * 40)
            return ("\n".join(sorted(set(inventory))) + "\n").encode()

        def read_blob(self, commit, path):
            assert commit == "1" * 40
            assert (
                path in allowed_assets
                or path.startswith("src/")
                and path.endswith(".py")
                or path == attempt.LAUNCHER_PATH
            )
            reads.append(path)
            return (root / path).read_bytes()

        def oid(self, commit, path):
            raw = self.read_blob(commit, path)
            return hashlib.sha1(
                b"blob " + str(len(raw)).encode() + b"\0" + raw
            ).hexdigest()

    monkeypatch.setattr(attempt, "GitRepository", SourceOnlyGit)
    closure = attempt.runtime_dependency_closure(root, "1" * 40)
    paths = [item["path"] for item in closure]
    assert paths == sorted(set(paths))
    assert set(attempt._CLOSURE_ROOTS) <= set(paths)
    assert "src/lotto649/notification.py" in paths
    assert all(
        "v12_0_1_" not in path
        and "v12_0_2_" not in path
        and "v12_parity_transition" not in path
        for path in paths
    )
    assert all(
        not path.startswith(("data/", "reports/", "predictions/", "evaluations/"))
        for path in reads
    )


def test_v13_notification_independent_inert_fixture_binds_raw_object_and_projection(
    attempt, projection
):
    fixed = projection["notification_projection"]
    raw = fixed["raw_commit_utf8"].encode()
    assert fixed["classification"] == "synthetic_fixture_only"
    assert len(raw) == fixed["raw_commit_byte_count"]
    assert (
        hashlib.sha1(b"commit " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        == fixed["raw_commit_sha1"]
    )
    assert hashlib.sha256(raw).hexdigest() == fixed["raw_commit_sha256"]
    assert (
        fixed["identity_sha256"]
        == hashlib.sha256(_canonical_fixture(fixed["identity"]) + b"\n").hexdigest()
    )
    assert fixed["canonical_body"]["intent_identity_sha256"] == fixed["identity_sha256"]
    assert (
        raw.split(b"\n\n", 1)[1] == _canonical_fixture(fixed["canonical_body"]) + b"\n"
    )
    assert fixed["get_commit_response"]["message"].encode() == _canonical_fixture(
        fixed["canonical_body"]
    )
    request = _canonical_fixture(fixed["post_commit_request"])
    assert len(request) == fixed["post_commit_request_byte_count"]
    assert hashlib.sha256(request).hexdigest() == fixed["post_commit_request_sha256"]
    # Validator-only calls on fabricated metadata never issue facts or capability.
    before = len(attempt._NOTIFICATION_STATES)
    oid, actual_raw, message = attempt._notification_request_parts(
        fixed["post_commit_request"]
    )
    assert oid == fixed["raw_commit_sha1"]
    assert actual_raw == raw
    assert message == fixed["get_commit_response"]["message"]
    attempt._verify_notification_get(
        oid, fixed["post_commit_request"], fixed["get_commit_response"]
    )
    attempt._verify_notification_ref(
        attempt._NOTIFICATION_REF, oid, fixed["get_ref_response"]
    )
    assert len(attempt._NOTIFICATION_STATES) == before


def test_v13_archive_without_capture_does_not_claim_a_six_of_six_audit_stop(
    attempt, tmp_path
):
    path = tmp_path / "synthetic-archive.jsonl"
    ledger = attempt.DurableLedger(path, {"fixture": True})
    ledger.append("synthetic_attempt_claimed", {"claim_sha256": "a" * 64})
    ledger.append(
        "attempt_archived", {"reason": "worker_failure", "retry_allowed": False}
    )
    ledger.close()
    result = attempt.audit_ledger(path)
    assert result["stopped_for_audit"] is False
    assert result["scored_target_count"] == 0


@pytest.mark.parametrize("entrypoint", ["prepare", "verify"])
@pytest.mark.parametrize("topology", ["root", "chain", "merge", "duplicate_parent"])
def test_i13_requires_one_ordinary_source_child_even_with_exact_eight_path_diff(
    attempt, synthetic_authorization, monkeypatch, entrypoint, topology
):
    fixture = synthetic_authorization
    base = fixture.ids["implementation_base"]
    invalid = {
        "root": (),
        "chain": ("a" * 40,),
        "merge": (base, "a" * 40),
        "duplicate_parent": (base, base),
    }[topology]
    original = fixture.git.parents
    monkeypatch.setattr(
        fixture.git,
        "parents",
        lambda commit: (
            invalid if commit == fixture.ids["implementation"] else original(commit)
        ),
    )
    before = (len(attempt._ISSUED_AUTHORITIES), len(attempt._VERIFIED_FACTS))
    with pytest.raises(attempt.AuthorizationError):
        if entrypoint == "prepare":
            monkeypatch.setattr(
                attempt, "_remote_main", lambda _api: fixture.ids["base"]
            )
            attempt.build_authorization_payload(
                fixture.root,
                implementation_commit=fixture.ids["implementation"],
                implementation_merge=fixture.ids["implementation_merge"],
                authorization_base=fixture.ids["base"],
                review_records=[],
                api=object(),
            )
        else:
            attempt.verify_authorization(fixture.root, api=object())
    assert (len(attempt._ISSUED_AUTHORITIES), len(attempt._VERIFIED_FACTS)) == before
    assert fixture.state["review_phases"] == []
    assert list(fixture.root.iterdir()) == []


def test_i13_one_ordinary_source_child_allows_inert_preparation(
    attempt, synthetic_authorization, monkeypatch
):
    fixture = synthetic_authorization
    monkeypatch.setattr(attempt, "_remote_main", lambda _api: fixture.ids["base"])
    payload = attempt.build_authorization_payload(
        fixture.root,
        implementation_commit=fixture.ids["implementation"],
        implementation_merge=fixture.ids["implementation_merge"],
        authorization_base=fixture.ids["base"],
        review_records=[],
        api=object(),
    )
    assert payload == fixture.payload
    assert list(fixture.root.iterdir()) == []


@pytest.fixture
def synthetic_artifact_publication(attempt, monkeypatch, tmp_path):
    # Exercise the publication mechanics only with an isolated fabricated Git tree,
    # inert SimpleNamespace authority and synthetic names; never issue a capability.
    root = tmp_path / "synthetic-publication-clone"
    root.mkdir()
    _fixture_git(root, "init", "--quiet", "--initial-branch=main")
    (root / "synthetic-source.txt").write_text("synthetic source only\n")
    _fixture_git(root, "add", "synthetic-source.txt")
    _fixture_git(root, "commit", "--quiet", "-m", "synthetic source fixture")
    base = _fixture_git(root, "rev-parse", "HEAD")
    temporary = tmp_path / "synthetic-os-temp"
    temporary.mkdir()
    monkeypatch.setattr(attempt, "_ARTIFACT_INDEX_OS_TEMP", str(temporary))
    output = root / "synthetic-output"
    output.mkdir()
    names = {
        "startup": "z-startup.jsonl",
        "claim": "a-claim.json",
        "ledger": "c-ledger.jsonl",
        "json": "b-result.json",
        "markdown": "m-result.md",
        "manifest": "synthetic-manifest.json",
        "manifest_staging": "synthetic-manifest.staging",
    }
    paths = {key: output / name for key, name in names.items()}
    for key in ("startup", "claim", "ledger", "json", "markdown"):
        paths[key].write_bytes(("synthetic fixture only: " + key + "\n").encode())
    startup = paths["startup"].read_bytes()
    authority = SimpleNamespace(
        execution_commit=base,
        authorization_sha256="a" * 64,
        startup=SimpleNamespace(
            sealed=True,
            byte_count=len(startup),
            digest_sha256=hashlib.sha256(startup).hexdigest(),
        ),
    )

    class SyntheticGit(attempt.GitRepository):
        def require_full_clean(self, *, authority=None):
            assert authority is not None

    git = SyntheticGit(root)

    def publish(staging, final, raw):
        assert (staging, final) == ("manifest_staging", "manifest")
        assert not paths[final].exists()
        paths[final].write_bytes(raw)

    monkeypatch.setattr(
        attempt, "_owned_artifacts", lambda _authority: SimpleNamespace(publish=publish)
    )
    state = {"commands": [], "index": None, "failure": None, "last_bytes": None}
    real_run = subprocess.run

    def observed_run(arguments, **kwargs):
        index = kwargs["env"].get("GIT_INDEX_FILE")
        if index is not None:
            index = Path(index)
            state["index"] = index
            state["commands"].append(arguments[-1])
            assert index.parent == temporary
            assert index.name.startswith("lotto649-v13-artifact-index-")
            assert len(index.name.removeprefix("lotto649-v13-artifact-index-")) == 32
            assert index.exists()
            assert kwargs["umask"] == 0o077
            assert index.stat().st_mode & 0o777 == 0o600
            state["last_bytes"] = index.read_bytes()
            if state["failure"] in arguments:
                return SimpleNamespace(
                    returncode=1, stdout=b"", stderr=b"synthetic private failure"
                )
        result = real_run(arguments, **kwargs)
        if index is not None:
            state["last_bytes"] = index.read_bytes()
        return result

    monkeypatch.setattr(
        attempt,
        "subprocess",
        SimpleNamespace(run=observed_run, SubprocessError=subprocess.SubprocessError),
    )
    return SimpleNamespace(
        root=root,
        temporary=temporary,
        paths=paths,
        authority=authority,
        git=git,
        state=state,
    )


def test_artifact_publication_sorts_five_inputs_and_removes_only_successful_temp_index(
    attempt, synthetic_artifact_publication
):
    case = synthetic_artifact_publication
    original_index = (case.root / ".git/index").read_bytes()
    commit = attempt._publish_git_manifest(
        case.git,
        case.authority,
        case.paths,
        startup_checkpoint={"synthetic_fixture_only": True},
    )
    manifest = json.loads(case.paths["manifest"].read_bytes())
    expected = sorted(
        case.paths[key].relative_to(case.root).as_posix()
        for key in ("startup", "claim", "ledger", "json", "markdown")
    )
    assert [entry["path"] for entry in manifest["files"]] == expected
    assert all(
        set(entry) == {"path", "git_blob", "sha256", "bytes"}
        for entry in manifest["files"]
    )
    assert case.git.parents(commit) == (case.authority.execution_commit,)
    assert {
        path
        for _status, path in case.git.changes(case.authority.execution_commit, commit)
    } == {*expected, case.paths["manifest"].relative_to(case.root).as_posix()}
    assert case.git.head() == case.authority.execution_commit
    assert (case.root / ".git/index").read_bytes() == original_index
    assert case.state["index"] is not None and not case.state["index"].exists()
    assert list(case.temporary.iterdir()) == []
    assert not list(case.root.rglob(".v13.0.0-index-*"))


@pytest.mark.parametrize("failure", ["read-tree", "update-index", "write-tree"])
def test_artifact_publication_failure_preserves_owned_os_temp_index(
    attempt, synthetic_artifact_publication, failure
):
    case = synthetic_artifact_publication
    case.state["failure"] = failure
    with pytest.raises(attempt.AttemptError):
        attempt._publish_git_manifest(
            case.git,
            case.authority,
            case.paths,
            startup_checkpoint={"synthetic_fixture_only": True},
        )
    index = case.state["index"]
    assert index.exists()
    assert index.read_bytes() == case.state["last_bytes"]
    assert index.stat().st_mode & 0o777 == 0o600
    assert case.git.head() == case.authority.execution_commit
    assert case.paths["manifest"].exists()


def test_artifact_publication_scope_failure_preserves_index(
    attempt, synthetic_artifact_publication, monkeypatch
):
    case = synthetic_artifact_publication
    monkeypatch.setattr(
        type(case.git), "changes", lambda *_: [("A", "synthetic-wrong-path")]
    )
    with pytest.raises(attempt.AttemptError, match="scope"):
        attempt._publish_git_manifest(
            case.git,
            case.authority,
            case.paths,
            startup_checkpoint={"synthetic_fixture_only": True},
        )
    assert case.state["index"].exists()
    assert case.state["index"].read_bytes() == case.state["last_bytes"]


@pytest.mark.parametrize("step", [1, 2, 3])
def test_startup_rejects_backward_clock_before_append_or_post_and_poison_is_terminal(
    attempt, tmp_path, monkeypatch, projection, step
):
    instants = iter(
        [
            "2032-01-01T00:00:10Z",
            *[f"2032-01-01T00:00:{10 + i}Z" for i in range(1, step)],
            "2032-01-01T00:00:09.999999Z",
        ]
    )
    monkeypatch.setattr(attempt, "_utc_now", lambda: next(instants))
    journal = _synthetic_startup(attempt, tmp_path / "synthetic-monotone-clock")
    effects = []
    operations = [
        lambda: journal.append("capability_issued", {}),
        lambda: journal.append("lease_absence_confirmed", {"http_status": 404}),
        lambda: journal.intent(
            "lease_commit",
            projection["nonce_hex"],
            projection["raw_commit_sha1"],
            projection["raw_commit_sha256"],
            _canonical_fixture(projection["post_commit_request"]),
        ),
    ]
    try:
        for operation in operations[: step - 1]:
            operation()
        before = journal.path.read_bytes()
        with pytest.raises(attempt.AttemptError):
            operations[step - 1]()
            effects.append("synthetic POST must never begin")
        assert effects == []
        assert journal.path.read_bytes() == before
        monkeypatch.setattr(attempt, "_utc_now", lambda: "2032-01-01T00:01:00Z")
        with pytest.raises(attempt.AttemptError):
            operations[step - 1]()
        assert journal.path.read_bytes() == before
    finally:
        journal.close()


@pytest.mark.parametrize(
    "second",
    [
        "2032-01-01T00:00:00Z",
        "2032-01-01T00:00:00.000000Z",
        "2032-01-01T00:00:00.000001Z",
    ],
)
def test_startup_monotone_clock_allows_equal_or_later_instants(
    attempt, tmp_path, monkeypatch, second
):
    instants = iter(["2032-01-01T00:00:00Z", second])
    monkeypatch.setattr(attempt, "_utc_now", lambda: next(instants))
    journal = _synthetic_startup(attempt, tmp_path / "synthetic-equal-clock")
    try:
        journal.append("capability_issued", {})
        assert len(journal.path.read_bytes().splitlines()) == 2
        with pytest.raises(AttributeError):
            journal.last_instant = "caller cannot replace clock state"
    finally:
        journal.close()


@pytest.mark.parametrize(
    "source",
    [
        "breakpoint()",
        "loader = breakpoint; loader()",
        "loaders = [breakpoint]; loaders[0]()",
        "help('synthetic_unregistered_module')",
        "loader = help; loader('synthetic_unregistered_module')",
    ],
)
def test_closure_rejects_builtin_debugger_and_help_loader_without_executing_them(
    attempt, source
):
    with pytest.raises(attempt.AuthorizationError):
        attempt._check_source_safety(attempt.ATTEMPT_PATH, ast.parse(source))


@pytest.mark.parametrize("capture_kind", ["final6", "top12"])
@pytest.mark.parametrize(
    "mutation",
    [
        "no_forecast_or_score",
        "no_score",
        "empty",
        "wrong_target",
        "wrong_digest",
        "missing_producer",
        "duplicate",
        "intervening",
        "truncated",
    ],
)
def test_ledger_capture_must_be_exact_complete_immediately_scored_cohort(
    attempt, tmp_path, capture_kind, mutation
):
    first_main = (
        (1, 2, 3, 4, 5, 6) if capture_kind == "final6" else (7, 8, 9, 10, 11, 12)
    )
    directory = tmp_path / "synthetic-capture-grammar"
    _durable_run(attempt, directory, _durable_case(first_main=first_main))
    events = _durable_events(attempt, directory)
    capture = events[3]
    assert capture["event_kind"] == (
        "historical_6of6_candidate_detected"
        if capture_kind == "final6"
        else "historical_top12_all_six_detected"
    )
    values_key = "opportunities" if capture_kind == "final6" else "producers"
    changed = events[:4]
    if mutation == "no_forecast_or_score":
        changed = [events[0], capture]
    elif mutation == "no_score":
        changed = [events[0], events[1], capture]
    elif mutation == "empty":
        capture["payload"][values_key] = []
    elif mutation == "wrong_target":
        capture["payload"]["target_draw_date"] = "2032-01-07"
    elif mutation == "wrong_digest":
        capture["payload"]["forecast_payload_sha256"] = "c" * 64
    elif mutation == "missing_producer":
        if capture_kind == "final6":
            capture["payload"][values_key][0]["producer_model_names"] = []
        else:
            capture["payload"][values_key] = capture["payload"][values_key][1:]
    elif mutation == "duplicate":
        changed.append(copy.deepcopy(capture))
    elif mutation == "intervening":
        separator = copy.deepcopy(events[0])
        separator["event_kind"] = "synthetic_fixture_event"
        separator["payload"] = {"value": "intervening synthetic event"}
        changed.insert(3, separator)
    elif mutation == "truncated":
        changed = changed[:3]
    path = attempt._paths(directory, synthetic=True)["ledger"]
    _rewrite_synthetic_events(attempt, path, changed)
    preserved = path.read_bytes()
    with pytest.raises(attempt.AttemptError):
        attempt.audit_ledger(path)
    assert path.read_bytes() == preserved


@pytest.mark.parametrize(
    "mutation",
    [
        "sequence",
        "bool_sequence",
        "digest",
        "time",
        "target",
        "forecast_body",
        "frozen_binding",
        "fake_opportunities",
        "fake_hits",
    ],
)
def test_ledger_scored_receipt_binds_exact_prior_frozen_event_even_after_rehash(
    attempt, tmp_path, mutation
):
    directory = tmp_path / "synthetic-cross-event-receipt"
    _durable_run(attempt, directory, _durable_case())
    events = _durable_events(attempt, directory)
    row = events[2]["payload"]
    if mutation == "sequence":
        row["prediction_frozen_event_sequence"] = 0
    elif mutation == "bool_sequence":
        row["prediction_frozen_event_sequence"] = True
    elif mutation == "digest":
        row["prediction_frozen_event_sha256"] = "c" * 64
    elif mutation == "time":
        row["prediction_generated_at"] = "2032-01-01T00:00:00Z"
    elif mutation == "target":
        row["target_draw_date"] = "2032-01-07"
    elif mutation == "forecast_body":
        row["forecast_payload"]["forecasts"][0]["top6"] = [2, 3, 4, 5, 6, 7]
    elif mutation == "frozen_binding":
        events[1]["payload"]["forecast_payload"]["bindings"]["synthetic_extra"] = True
        digest = hashlib.sha256(
            attempt._canonical(events[1]["payload"]["forecast_payload"]) + b"\n"
        ).hexdigest()
        events[1]["payload"]["forecast_payload_sha256"] = digest
    elif mutation == "fake_opportunities":
        row["exact_final6_opportunities"] = [{"hits": 6}]
    else:
        row["scores"][0]["final6_hits"] = 6
    path = attempt._paths(directory, synthetic=True)["ledger"]
    _rewrite_synthetic_events(attempt, path, events)
    with pytest.raises(attempt.AttemptError):
        attempt.audit_ledger(path)
    with pytest.raises(attempt.AttemptError):
        attempt._durable_scored_rows(path)


def test_ledger_cannot_forecast_again_after_durable_exact6_capture(attempt, tmp_path):
    directory = tmp_path / "synthetic-stop"
    _durable_run(attempt, directory, _durable_case(first_main=(1, 2, 3, 4, 5, 6)))
    events = _durable_events(attempt, directory)
    events.append(copy.deepcopy(events[1]))
    path = attempt._paths(directory, synthetic=True)["ledger"]
    _rewrite_synthetic_events(attempt, path, events)
    with pytest.raises(attempt.AttemptError):
        attempt.audit_ledger(path)


def test_artifact_index_temp_root_cannot_be_inside_execution_clone(
    attempt, synthetic_artifact_publication, monkeypatch
):
    case = synthetic_artifact_publication
    monkeypatch.setattr(attempt, "_ARTIFACT_INDEX_OS_TEMP", str(case.root))
    with pytest.raises(attempt.AttemptError):
        attempt._publish_git_manifest(
            case.git,
            case.authority,
            case.paths,
            startup_checkpoint={"synthetic_fixture_only": True},
        )
    assert case.state["commands"] == []
    assert not list(case.root.glob("lotto649-v13-artifact-index-*"))


def test_artifact_index_exclusive_collision_never_adopts_or_retries(
    attempt, synthetic_artifact_publication, monkeypatch
):
    case = synthetic_artifact_publication
    monkeypatch.setattr(attempt.secrets, "token_hex", lambda size: "a" * (2 * size))
    foreign = case.temporary / ("lotto649-v13-artifact-index-" + "a" * 32)
    foreign.write_bytes(b"synthetic foreign bytes")
    with pytest.raises(FileExistsError):
        attempt._publish_git_manifest(
            case.git,
            case.authority,
            case.paths,
            startup_checkpoint={"synthetic_fixture_only": True},
        )
    assert foreign.read_bytes() == b"synthetic foreign bytes"
    assert case.state["commands"] == []
    assert list(case.temporary.iterdir()) == [foreign]


def test_artifact_index_replaced_after_git_success_is_preserved_not_cleaned(
    attempt, synthetic_artifact_publication, monkeypatch
):
    case = synthetic_artifact_publication
    original = type(case.git).changes

    def replace_index(git, earlier, later):
        result = original(git, earlier, later)
        index = case.state["index"]
        index.rename(index.with_name(index.name + ".synthetic-original"))
        index.write_bytes(b"synthetic foreign replacement")
        index.chmod(0o600)
        return result

    monkeypatch.setattr(type(case.git), "changes", replace_index)
    with pytest.raises(attempt.AttemptError):
        attempt._publish_git_manifest(
            case.git,
            case.authority,
            case.paths,
            startup_checkpoint={"synthetic_fixture_only": True},
        )
    assert case.state["index"].read_bytes() == b"synthetic foreign replacement"
    assert len(list(case.temporary.iterdir())) == 2


# Production notification tests adapted from the frozen 86-case source-only draft.


@pytest.fixture
def _np_ns(attempt, monkeypatch):
    namespace = attempt.notify_audited_capture.__globals__
    for name, value in (
        ("_NOTIFICATION_FACTS", {}),
        ("_NOTIFICATION_TRANSPORTS", {}),
        ("_PRODUCTION_NOTIFICATION_ISSUANCE", []),
        ("_NOTIFICATION_STATES", {}),
    ):
        monkeypatch.setitem(namespace, name, value)
    yield namespace
    for invocation in tuple(namespace["_NOTIFICATION_STATES"]):
        namespace["_notification_close"](invocation)
    for facts in tuple(namespace["_NOTIFICATION_FACTS"]):
        namespace["_close_notification_facts"](facts)


class _np_Response:
    def __init__(self, url, status=200, body=None, headers=None, fail=False):
        self.url = url
        self.status_code = status
        self.body = body
        self.fail = fail
        self.headers = {"Content-Type": "application/json", **(headers or {})}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def iter_content(self, size):
        if self.fail:
            raise RuntimeError("synthetic-credential-never-display")
        if isinstance(self.body, bytes):
            yield self.body
        else:
            yield json.dumps(self.body).encode()


class _np_Session:
    def __init__(self):
        self.headers = {}
        self.calls = []
        self.queue = []
        self.mounts = []
        self.trust_env = True

    def mount(self, *args):
        self.mounts.append(args)

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        response = self.queue.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response


def _np_api_fixture(_np_ns, monkeypatch):
    session = _np_Session()
    import requests

    monkeypatch.setattr(requests, "Session", lambda: session)
    api = _np_ns["_NotificationHTTP"]("synthetic-token")
    return api, session


@pytest.mark.parametrize(
    "route",
    [
        "/git/ref/heads/v13-consumption-v13.0.0",
        "/git/matching-refs/heads",
        "/git/ref/heads/main?evil=true",
        "/git/commits/main",
        "/git/commits/" + "a" * 39,
    ],
)
def test_production_notification_notification_adapter_rejects_other_purpose_or_nonliteral_routes(
    _np_ns, monkeypatch, route
):
    api, session = _np_api_fixture(_np_ns, monkeypatch)
    with pytest.raises(_np_ns["AuthorizationError"]):
        api.request_json("GET", _np_ns["_API_PREFIX"] + route)
    assert session.calls == [] and api._terminal


@pytest.mark.parametrize("method", ["PATCH", "DELETE", "PUT"])
def test_production_notification_notification_adapter_never_updates_deletes_or_retries(
    _np_ns, monkeypatch, method
):
    api, session = _np_api_fixture(_np_ns, monkeypatch)
    with pytest.raises(_np_ns["AuthorizationError"]):
        api.request_json(method, _np_ns["_API_PREFIX"] + "/git/refs", body_bytes=b"{}")
    assert session.calls == [] and api._terminal


@pytest.mark.parametrize("status", [301, 302, 401, 403, 429, 500])
def test_production_notification_notification_absence_requires_exact404_and_terminal_status(
    _np_ns, monkeypatch, status
):
    api, s = _np_api_fixture(_np_ns, monkeypatch)
    url = (
        _np_ns["_API_ORIGIN"]
        + _np_ns["_API_PREFIX"]
        + "/git/ref/heads/v13-notification-v13.0.0"
    )
    s.queue = [_np_Response(url, status, {"message": "Not Found"})]
    with pytest.raises(_np_ns["TransportError"]):
        api.get_ref(_np_ns["_NOTIFICATION_REF"])
    with pytest.raises(_np_ns["AuthorizationError"]):
        api.get_ref(_np_ns["_NOTIFICATION_REF"])
    assert len(s.calls) == 1


@pytest.mark.parametrize(
    "body,headers",
    [
        (b'{"message":"Not Found","message":"Not Found"}', {}),
        (b'{"message":NaN}', {}),
        ({"message": "Not Found", "other": True}, {}),
        ({"message": "Not Found"}, {"Link": "next"}),
        ({"message": "Not Found"}, {"Content-Encoding": "gzip"}),
    ],
)
def test_production_notification_notification_absence_malformed_unknown_and_pagination_rejected(
    _np_ns, monkeypatch, body, headers
):
    api, s = _np_api_fixture(_np_ns, monkeypatch)
    url = (
        _np_ns["_API_ORIGIN"]
        + _np_ns["_API_PREFIX"]
        + "/git/ref/heads/v13-notification-v13.0.0"
    )
    s.queue = [_np_Response(url, 404, body, headers)]
    with pytest.raises(_np_ns["TransportError"]):
        api.get_ref(_np_ns["_NOTIFICATION_REF"])
    assert api._terminal and len(s.calls) == 1


def test_production_notification_adapter_absence_is_fixed_tls_no_proxy_no_redirect_no_retry(
    _np_ns, monkeypatch
):
    api, s = _np_api_fixture(_np_ns, monkeypatch)
    url = (
        _np_ns["_API_ORIGIN"]
        + _np_ns["_API_PREFIX"]
        + "/git/ref/heads/v13-notification-v13.0.0"
    )
    s.queue = [_np_Response(url, 404, {"message": "Not Found", "status": "404"})]
    assert api.get_ref(_np_ns["_NOTIFICATION_REF"]) == (404, {"message": "Not Found"})
    assert s.trust_env is False
    assert s.mounts[0][1].max_retries.total == 0
    assert s.calls[0] == (
        "GET",
        url,
        {
            "allow_redirects": False,
            "stream": True,
            "timeout": (10, 30),
            "proxies": {},
            "verify": True,
        },
    )
    assert s.headers["Authorization"] == "Bearer synthetic-token"


@pytest.mark.parametrize("route", ["/git/commits", "/git/refs"])
def test_production_notification_read_only_notification_api_cannot_post(
    _np_ns, monkeypatch, route
):
    api, s = _np_api_fixture(_np_ns, monkeypatch)
    with pytest.raises(_np_ns["AuthorizationError"]):
        api.request_json("POST", _np_ns["_API_PREFIX"] + route, body_bytes=b"{}")
    assert not s.calls and api._terminal


@pytest.mark.parametrize("token", ["", "a b", "a\nb", "a" * 513])
def test_production_notification_credential_rejection_never_echoes_value(
    _np_ns, monkeypatch, token
):
    with pytest.raises(_np_ns["AuthorizationError"]) as caught:
        _np_ns["_NotificationHTTP"](token)
    assert str(caught.value) == "GitHub credential unavailable"


@pytest.mark.parametrize("value", [None, {}, object()])
def test_production_notification_notification_facts_cannot_be_fabricated(_np_ns, value):
    with pytest.raises(_np_ns["AuthorizationError"]):
        _np_ns["_notification_facts"](value)
    with pytest.raises(_np_ns["AuthorizationError"]):
        _np_ns["_VerifiedNotificationFacts"]()


def _np__git(root, *args):
    result = subprocess.run(
        ["/usr/bin/git", "-C", str(root), *args],
        env={
            "PATH": "/usr/bin:/bin",
            "HOME": str(root),
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_AUTHOR_NAME": "Synthetic",
            "GIT_AUTHOR_EMAIL": "synthetic@example.invalid",
            "GIT_COMMITTER_NAME": "Synthetic",
            "GIT_COMMITTER_EMAIL": "synthetic@example.invalid",
        },
        capture_output=True,
        check=True,
    )
    return result.stdout.decode().strip()


@pytest.fixture
def _np_repo(tmp_path):
    root = tmp_path / "synthetic-git"
    root.mkdir()
    _np__git(root, "init", "-q")
    (root / "base.txt").write_text("synthetic\n")
    _np__git(root, "add", "base.txt")
    _np__git(root, "commit", "-qm", "Synthetic root")
    return root


def test_production_notification_full_dag_single_add_provenance_accepts_ordinary_adoption(
    _np_ns, _np_repo
):
    path = "audit.json"
    base = _np__git(_np_repo, "rev-parse", "HEAD")
    _np__git(_np_repo, "checkout", "-qb", "synthetic-source")
    (_np_repo / path).write_text("{}\n")
    _np__git(_np_repo, "add", path)
    _np__git(_np_repo, "commit", "-qm", "Synthetic addition")
    source = _np__git(_np_repo, "rev-parse", "HEAD")
    _np__git(_np_repo, "checkout", "-q", "master")
    _np__git(
        _np_repo,
        "merge",
        "--no-ff",
        "-qm",
        "Synthetic ordinary merge",
        "synthetic-source",
    )
    assert (
        _np_ns["_notification_blob_origin"](
            _np_ns["GitRepository"](_np_repo),
            _np__git(_np_repo, "rev-parse", "HEAD"),
            path,
        )
        == source
    )
    assert source != base


@pytest.mark.parametrize(
    "kind",
    ["modify_restore", "delete_restore", "chmod_restore", "side_branch_modify_restore"],
)
def test_production_notification_full_dag_never_accepts_restore_even_identical_final_blob(
    _np_ns, _np_repo, kind
):
    path = "audit.json"
    (_np_repo / path).write_text("{}\n")
    _np__git(_np_repo, "add", path)
    _np__git(_np_repo, "commit", "-qm", "Synthetic addition")
    if kind == "side_branch_modify_restore":
        _np__git(_np_repo, "checkout", "-qb", "synthetic-bad")
    if kind == "delete_restore":
        (_np_repo / path).unlink()
    elif kind == "chmod_restore":
        os.chmod(_np_repo / path, 0o755)
    else:
        (_np_repo / path).write_text('{"changed":true}\n')
    _np__git(_np_repo, "add", "-A")
    _np__git(_np_repo, "commit", "-qm", "Synthetic forbidden change")
    (_np_repo / path).write_text("{}\n")
    os.chmod(_np_repo / path, 0o644)
    _np__git(_np_repo, "add", "-A")
    _np__git(_np_repo, "commit", "-qm", "Synthetic restoration")
    if kind == "side_branch_modify_restore":
        _np__git(_np_repo, "checkout", "-q", "master")
        _np__git(
            _np_repo,
            "merge",
            "--no-ff",
            "-qm",
            "Synthetic hidden merge",
            "synthetic-bad",
        )
    with pytest.raises(_np_ns["AuthorizationError"]):
        _np_ns["_notification_blob_origin"](
            _np_ns["GitRepository"](_np_repo),
            _np__git(_np_repo, "rev-parse", "HEAD"),
            path,
        )


def test_production_notification_retained_capture_fd_rejects_replace_and_reopen(
    _np_ns, _np_repo
):
    path = "audit.json"
    (_np_repo / path).write_text("{}\n")
    _np__git(_np_repo, "add", path)
    _np__git(_np_repo, "commit", "-qm", "Synthetic addition")
    record = _np_ns["_notification_read_immutable"](
        _np_ns["GitRepository"](_np_repo), _np__git(_np_repo, "rev-parse", "HEAD"), path
    )
    try:
        _np_ns["_notification_check_immutable"](record)
        (_np_repo / "replacement").write_text("{}\n")
        os.replace(_np_repo / "replacement", _np_repo / path)
        with pytest.raises(_np_ns["AuthorizationError"]):
            _np_ns["_notification_check_immutable"](record)
    finally:
        os.close(record["fd"])
        os.close(record["parent_fd"])


@pytest.mark.parametrize("kind", ["write", "hardlink", "parent_symlink"])
def test_production_notification_retained_capture_fd_rejects_byte_nlink_or_parent_changes(
    _np_ns, _np_repo, kind
):
    (_np_repo / "nested").mkdir()
    path = "nested/audit.json"
    (_np_repo / path).write_text("{}\n")
    _np__git(_np_repo, "add", path)
    _np__git(_np_repo, "commit", "-qm", "Synthetic addition")
    record = _np_ns["_notification_read_immutable"](
        _np_ns["GitRepository"](_np_repo), _np__git(_np_repo, "rev-parse", "HEAD"), path
    )
    try:
        if kind == "write":
            (_np_repo / path).write_text('{"x":1}\n')
        elif kind == "hardlink":
            os.link(_np_repo / path, _np_repo / "other")
        else:
            os.rename(_np_repo / "nested", _np_repo / "moved")
            (_np_repo / "nested").symlink_to(
                _np_repo / "moved", target_is_directory=True
            )
        with pytest.raises(_np_ns["AuthorizationError"]):
            _np_ns["_notification_check_immutable"](record)
    finally:
        os.close(record["fd"])
        os.close(record["parent_fd"])


def _np_author_raw(_np_ns, persons=None):
    body = {
        "schema_version": "lotto649-v13-capture-publication-authors-v1",
        "contributors": persons
        or [
            {"agent_id": "/root/synthetic_author", "session_id": "synthetic-authoring"}
        ],
    }
    return (
        b"tree "
        + b"a" * 40
        + b"\n\nSynthetic publication\n\nCapture-Publication-Authors: "
        + _np_ns["_canonical"](body)
        + b"\n"
    )


def test_production_notification_capture_authors_use_separate_canonical_trailer_not_r13_phase(
    _np_ns,
):
    result = _np_ns["_capture_publication_authors"](_np_author_raw(_np_ns))
    assert result == [
        {"agent_id": "/root/synthetic_author", "session_id": "synthetic-authoring"}
    ]


@pytest.mark.parametrize(
    "mutation",
    [
        lambda x: x + b"\n",
        lambda x: x.replace(b"Capture-", b" Capture-"),
        lambda x: x.replace(b"Capture-", b"Research-"),
        lambda x: x.replace(b"contributors", b"unknown"),
        lambda x: x.replace(
            b"\n\nSynthetic", b"\n\nCapture-Publication-Authors: {}\nSynthetic"
        ),
    ],
)
def test_production_notification_capture_authors_reject_malformed_framing_or_schema(
    _np_ns, mutation
):
    with pytest.raises(_np_ns["AuthorizationError"]):
        _np_ns["_capture_publication_authors"](mutation(_np_author_raw(_np_ns)))


@pytest.fixture
def _np_registration():
    return json.loads(
        (
            ROOT
            / "evidence/research_registrations/v13-post-rng-main-set-overlap-v1.json"
        ).read_bytes()
    )


def _np_synthetic_chain(_np_ns, _np_registration):
    operation = _np_registration["operational_contract"]
    order = _np_registration["scientific_contract"]["identity"]["producer_order"]
    state = {
        "source_draw_date": "2019-12-28",
        "source_anchor": [1, 2, 3, 4, 5, 6],
        "transformed_anchor": None,
        "training_pair_count": 0,
        "training_overlap_sum": 0,
        "scientific_projection_sha256": "a" * 64,
        "counts_sha256": "b" * 64,
    }
    for key, value in (
        ("beta", 0.0),
        ("mean", 36 / 49),
        ("complement_mean", 6 - 36 / 49),
        ("log_z", 1.0),
    ):
        state[key] = value
        state[key + "_hex"] = value.hex()
    forecasts = []
    for index, name in enumerate(order):
        item = {
            "model_name": name,
            "model_version": "v13.0.0" if index < 2 else "v1.0.0",
            "feature_set": "synthetic_frozen_record",
            "probabilities": {str(n): 6 / 49 for n in range(1, 50)},
            "probability_hex": {str(n): (6 / 49).hex() for n in range(1, 50)},
            "ranking": list(range(1, 50)),
            "top6": list(range(1, 7)),
            "top12": list(range(1, 13)),
            "top18": list(range(1, 19)),
            "final6": list(range(1, 7)),
            "scientific_state": copy.deepcopy(state) if index < 2 else None,
        }
        if index == 1:
            item["scientific_state"]["transformed_anchor"] = [2, 3, 4, 5, 6, 7]
        forecasts.append(item)
    hashes = {
        item["model_name"]: _np_ns["_sha"](_np_ns["_canonical"](item) + b"\n")
        for item in forecasts
    }
    bindings = {"classification": "consumed_historical_diagnostic_only"}
    frozen = {
        "schema_version": "lotto649-v13.0.0-frozen-forecast-v1",
        "classification": "consumed_historical_diagnostic_only",
        "model_version": "v13.0.0",
        "target_draw_date": "2020-01-01",
        "history_through": "2019-12-28",
        "training_cutoff_date": "2019-12-28",
        "visible_prefix_sha256": "c" * 64,
        "visible_prefix_draw_count": 1,
        "bindings": bindings,
        "forecasts": forecasts,
        "forecast_sha256_by_model": hashes,
    }
    digest = _np_ns["_sha"](_np_ns["_canonical"](frozen) + b"\n")
    opportunities = [
        {
            "final6": list(range(1, 7)),
            "primary_producer": order[0],
            "producer_model_names": order,
            "forecast_sha256_by_producer": hashes,
            "hits": 6,
        }
    ]
    events = []

    def add(kind, payload):
        event = {
            "schema_version": "lotto649-v13.0.0-attempt-ledger-v1",
            "sequence": len(events),
            "recorded_at": "2026-09-13T00:00:00Z",
            "previous_event_sha256": events[-1]["event_sha256"] if events else "0" * 64,
            "event_kind": kind,
            "bindings": bindings,
            "payload": payload,
        }
        event["event_sha256"] = _np_ns["_sha"](_np_ns["_canonical"](event))
        events.append(event)

    # Fabricated closed metadata; full publication replaces it with real bytes.
    checkpoint = {
        "path": operation["startup"]["path"],
        "sequence": 9,
        "head_sha256": "a" * 64,
        "prefix_byte_count": 1,
        "prefix_sha256": "b" * 64,
    }
    add("attempt_claimed", {"claim_sha256": "d" * 64, "startup_checkpoint": checkpoint})
    add(
        "prediction_frozen",
        {"forecast_payload": frozen, "forecast_payload_sha256": digest},
    )
    row = {
        "target_draw_date": "2020-01-01",
        "actual": list(range(1, 7)),
        "bonus": 7,
        "forecast_payload": frozen,
        "forecast_payload_sha256": digest,
        "prediction_generated_at": events[1]["recorded_at"],
        "prediction_frozen_event_sequence": 1,
        "prediction_frozen_event_sha256": events[1]["event_sha256"],
        "scores": [],
        "fair_scores": {"brier_score": 0.1, "log_loss": 0.3},
        "unique_final6": opportunities,
        "unique_opportunity_count": 1,
        "exact_final6_opportunities": opportunities,
        "top12_all_six_producers": order,
        "cumulative_opportunities": {
            "unique_opportunity_count": 1,
            "nominal_fair_exact6_chance": 1 / 13983816,
        },
    }
    for index, name in enumerate(order):
        row["scores"].append(
            {
                "model_name": name,
                "model_version": forecasts[index]["model_version"],
                "forecast_sha256": hashes[name],
                "top6_hits": 6,
                "top12_hits": 6,
                "top18_hits": 6,
                "final6_hits": 6,
                "matched_final6": list(range(1, 7)),
                "mean_actual_rank": 3.5,
                "brier_score": 0.1,
                "log_loss": 0.3,
                "joint_log_gain": None,
            }
        )
    add("target_revealed_scored", row)
    add(
        "historical_6of6_candidate_detected",
        {
            "target_draw_date": "2020-01-01",
            "forecast_payload_sha256": digest,
            "opportunities": opportunities,
            "audit_status": "independent_leakage_audit_pending",
            "eligible_evidence": False,
            "global_stop_search": True,
        },
    )
    return events


def _np_rechain(_np_ns, events):
    for index, event in enumerate(events):
        event["sequence"] = index
        event["previous_event_sha256"] = (
            events[index - 1]["event_sha256"] if index else "0" * 64
        )
        event["event_sha256"] = _np_ns["_sha"](
            _np_ns["_canonical"](
                {k: v for k, v in event.items() if k != "event_sha256"}
            )
        )
    return b"".join(_np_ns["_canonical"](event) + b"\n" for event in events)


def test_production_notification_dedicated_frozen_byte_audit_never_calls_any_scientific_or_historical_seam(
    _np_ns, _np_registration, monkeypatch
):
    forbidden = [
        "audit_ledger",
        "_ledger_payload",
        "score_target",
        "_validated_rows",
        "build_report",
        "validate_frozen_payload",
        "moments",
        "solve_map_beta",
        "select_combination",
        "four_forecasts",
        "_load_governed_history",
        "verify_authorization",
        "_issue_verified_facts",
        "_issue_authorization",
        "begin_authorized_startup",
        "acquire_historical_lease",
        "_run_canonical",
        "_drive_sequence",
    ]
    calls = []

    def forbidden_call(*args, **kwargs):
        calls.append(True)
        raise AssertionError("scientific/historical seam called")

    for key in forbidden:
        monkeypatch.setitem(_np_ns, key, forbidden_call)
    events = _np_synthetic_chain(_np_ns, _np_registration)
    raw = _np_rechain(_np_ns, events)
    result = _np_ns["_notification_ledger_metadata"](
        raw, _np_registration["operational_contract"]
    )
    assert result == {
        "event_count": 4,
        "scored_target_count": 1,
        "head_sha256": events[-1]["event_sha256"],
        "pending_forecast": False,
        "stopped_for_audit": True,
        "file_sha256": hashlib.sha256(raw).hexdigest(),
    }
    assert calls == []


@pytest.mark.parametrize(
    "mutation",
    [
        lambda events: events[1]["payload"]["forecast_payload"].update({"unknown": 1}),
        lambda events: events[1]["payload"]["forecast_payload"]["forecasts"][0].update(
            {"unknown": 1}
        ),
        lambda events: events[2]["payload"]["scores"][0].update({"unknown": 1}),
        lambda events: events[2]["payload"].update(
            {"prediction_frozen_event_sequence": 0}
        ),
        lambda events: events[2]["payload"].update(
            {"prediction_generated_at": "2026-09-12T00:00:00Z"}
        ),
        lambda events: events[1].update({"recorded_at": "2026-09-12T00:00:00Z"}),
        lambda events: events[3]["payload"].update({"global_stop_search": False}),
        lambda events: events.append(copy.deepcopy(events[1])),
        lambda events: events[1].update({"event_kind": "unregistered_event"}),
        lambda events: events[3]["payload"].update({"eligible_evidence": True}),
    ],
)
def test_production_notification_dedicated_byte_audit_rejects_rehashed_schema_phase_and_binding_changes(
    _np_ns, _np_registration, mutation
):
    events = _np_synthetic_chain(_np_ns, _np_registration)
    mutation(events)
    with pytest.raises(_np_ns["AuthorizationError"]):
        _np_ns["_notification_ledger_metadata"](
            _np_rechain(_np_ns, events), _np_registration["operational_contract"]
        )


def test_production_notification_dedicated_byte_audit_rejects_absent_capture_and_partial_line(
    _np_ns, _np_registration
):
    events = _np_synthetic_chain(_np_ns, _np_registration)
    for raw in (_np_rechain(_np_ns, events[:-1]), _np_rechain(_np_ns, events)[:-1]):
        with pytest.raises(_np_ns["AuthorizationError"]):
            _np_ns["_notification_ledger_metadata"](
                raw, _np_registration["operational_contract"]
            )


def _np_synthetic_publication_review(_np_ns):
    source, base, head = "a" * 40, "b" * 40, "c" * 40
    _np_repo = {"full_name": _np_ns["REPOSITORY"]}
    pr = {
        "number": 51,
        "state": "closed",
        "merged": True,
        "merge_commit_sha": head,
        "head": {"sha": source, "repo": _np_repo},
        "base": {"sha": base, "ref": "main", "repo": _np_repo},
    }
    check = {
        "id": 71,
        "name": "test",
        "head_sha": source,
        "status": "completed",
        "conclusion": "success",
        "app": {"slug": "github-actions"},
    }
    comments = []
    for index, axis in enumerate(("standards", "spec")):
        body = {
            "schema_version": "lotto649-v13-capture-publication-independent-review-v1",
            "axis": axis,
            "base_sha": base,
            "head_sha": source,
            "closure_sha256": "d" * 64,
            "operational_contract_sha256": _np_ns["OPERATIONAL_SHA256"],
            "verdict": "pass",
            "blocker_count": 0,
            "major_count": 0,
            "reviewer_kind": "independent_agent",
            "reviewer_agent_id": "/root/synthetic_" + axis,
            "review_session_id": "synthetic-" + axis,
            "publisher_login": "synthetic-publisher",
        }
        comments.append(
            {
                "id": 90 + index,
                "body": (_np_ns["_canonical"](body) + b"\n").decode(),
                "user": {"login": "synthetic-publisher"},
                "created_at": "2026-09-13T00:00:00Z",
                "updated_at": "2026-09-13T00:00:00Z",
                "issue_url": _np_ns["_API_ORIGIN"]
                + _np_ns["_API_PREFIX"]
                + "/issues/51",
            }
        )
    routes = {
        f"/commits/{source}/pulls?per_page=100": [pr],
        "/pulls/51": pr,
        f"/commits/{source}/check-runs?per_page=100": {
            "total_count": 1,
            "check_runs": [check],
        },
        "/check-runs/71": check,
        "/issues/51/comments?per_page=100": comments,
        **{"/issues/comments/" + str(comment["id"]): comment for comment in comments},
    }

    class API:
        def request_json(self, method, path):
            assert method == "GET"
            return copy.deepcopy(routes[path.removeprefix(_np_ns["_API_PREFIX"])])

    return (
        API(),
        routes,
        {
            "head": head,
            "source": source,
            "base": base,
            "closure_sha256": "d" * 64,
            "excluded": [],
        },
    )


def test_production_notification_publication_review_two_actual_independent_agents_same_real_publisher_allowed(
    _np_ns,
):
    api, _routes, kwargs = _np_synthetic_publication_review(_np_ns)
    result = _np_ns["_notification_publication_reviews"](None, api, **kwargs)
    assert len(result) == 2 and {item["publisher_login"] for item in result} == {
        "synthetic-publisher"
    }


@pytest.mark.parametrize(
    "change",
    [
        "edited",
        "duplicate_check",
        "missing_spec",
        "same_agent",
        "source_author",
        "false_integer",
        "unknown_key",
        "stale_head",
        "different_reread",
        "bad_publisher",
    ],
)
def test_production_notification_publication_review_rejects_ambiguous_changed_or_nonindependent_evidence(
    _np_ns, change
):
    api, routes, kwargs = _np_synthetic_publication_review(_np_ns)
    comments = routes["/issues/51/comments?per_page=100"]
    if change == "duplicate_check":
        checks = routes["/commits/" + kwargs["source"] + "/check-runs?per_page=100"]
        checks["total_count"] = 2
        checks["check_runs"] *= 2
    elif change == "missing_spec":
        comments.pop()
    elif change == "source_author":
        kwargs["excluded"] = [
            {"agent_id": "/root/synthetic_standards", "session_id": "other-session"}
        ]
    elif change == "edited":
        comments[0]["updated_at"] = "2026-09-13T01:00:00Z"
    elif change == "different_reread":
        routes["/issues/comments/90"] = {
            **comments[0],
            "updated_at": "2026-09-13T01:00:00Z",
        }
    elif change == "bad_publisher":
        comments[0]["user"]["login"] = "not-actual-publisher"
    else:
        body = json.loads(comments[1]["body"])
        if change == "same_agent":
            body["reviewer_agent_id"] = "/root/synthetic_standards"
        if change == "false_integer":
            body["major_count"] = False
        if change == "unknown_key":
            body["unknown"] = True
        if change == "stale_head":
            body["head_sha"] = "e" * 40
        comments[1]["body"] = (_np_ns["_canonical"](body) + b"\n").decode()
    with pytest.raises(_np_ns["AuthorizationError"]):
        _np_ns["_notification_publication_reviews"](None, api, **kwargs)


def _np_prepared_production_fixture(_np_ns, monkeypatch, tmp_path):
    root = tmp_path / "synthetic-notification-only"
    root.mkdir()
    api, session = _np_api_fixture(_np_ns, monkeypatch)
    url = (
        _np_ns["_API_ORIGIN"]
        + _np_ns["_API_PREFIX"]
        + "/git/ref/heads/v13-notification-v13.0.0"
    )
    session.queue = [_np_Response(url, 404, {"message": "Not Found"})]
    publication_raw = (
        b"tree "
        + b"d" * 40
        + b"\nparent "
        + b"a" * 40
        + b"\nparent "
        + b"b" * 40
        + b"\nauthor Synthetic <fixture@example.invalid> 1704067200 -0400"
        + b"\ncommitter Synthetic <fixture@example.invalid> 1704067200 -0400"
        + b"\n\nSynthetic publication only\n"
    )
    publication = hashlib.sha1(
        b"commit " + str(len(publication_raw)).encode() + b"\x00" + publication_raw
    ).hexdigest()
    proof = {
        "repository": str(root),
        "publication": publication,
        "publication_committer_time": "2024-01-01T00:00:00Z",
        "tree": "d" * 40,
        "runtime_closure": [],
        "audit": {"target_draw_date": "2020-01-01"},
        "bundle_path": "reports/historical-6of6-candidate__2020-01-01__v13_post_rng_main_set_overlap__v13.0.0.json",
        "bundle_sha256": "a" * 64,
        "audit_path": "evidence/research_audits/v13.0.0/historical-6of6__2020-01-01__v13_post_rng_main_set_overlap.json",
        "audit_sha256": "b" * 64,
    }
    facts = object.__new__(_np_ns["_VerifiedNotificationFacts"])
    _np_ns["_NOTIFICATION_FACTS"][facts] = {
        "proof": proof,
        "stamp": _np_ns["_canonical"](proof),
        "files": [],
        "closed": False,
        "poisoned": False,
        "started": False,
        "api": api,
        "invocation": None,
    }

    class Git:
        def __init__(self, path):
            self.root = path

        def require_full_clean(self):
            pass

        def head(self):
            return publication

        def run(self, *args):
            assert args == ("cat-file", "commit", publication)
            return publication_raw

    monkeypatch.setitem(_np_ns, "GitRepository", Git)
    monkeypatch.setitem(_np_ns, "_verify_worktree_runtime", lambda *args: None)
    monkeypatch.setitem(_np_ns, "_remote_protection", lambda *args: None)
    monkeypatch.setitem(_np_ns, "_remote_main", lambda *args: publication)
    invocation = _np_ns["_prepare_production_notification"](facts, api)
    return facts, invocation, api, session


def test_production_notification_production_issuer_requires_same_issued_identity_not_caller_dictionary(
    _np_ns, tmp_path
):
    with pytest.raises(_np_ns["AuthorizationError"]):
        _np_ns["_issue_notification_files"](
            tmp_path, {}, "2026-09-13T00:00:00Z", synthetic=False
        )
    assert list(tmp_path.iterdir()) == []


def test_production_notification_production_prepare_issues_owned_files_after_exact404_without_science(
    _np_ns, monkeypatch, tmp_path
):
    def fail(*args, **kwargs):
        raise AssertionError("scientific or historical path invoked")

    for key in (
        "_load_governed_history",
        "verify_authorization",
        "begin_authorized_startup",
        "_issue_authorization",
        "_run_canonical",
        "four_forecasts",
        "score_target",
        "moments",
        "solve_map_beta",
        "select_combination",
    ):
        monkeypatch.setitem(_np_ns, key, fail)
    facts, invocation, api, session = _np_prepared_production_fixture(
        _np_ns, monkeypatch, tmp_path
    )
    try:
        state = _np_ns["_notification_state"](invocation)
        assert state["sequence"] == 1 and state["synthetic"] is False
        assert state["reference"] == _np_ns["_NOTIFICATION_REF"]
        assert [call[0] for call in session.calls] == ["GET"]
        with pytest.raises(_np_ns["AuthorizationError"]):
            _np_ns["_prepare_production_notification"](facts, api)
        assert len(session.calls) == 1
    finally:
        _np_ns["_notification_close"](invocation)
        _np_ns["_close_notification_facts"](facts)


def test_production_notification_direct_notification_post_cannot_bypass_durable_protocol_phase(
    _np_ns, monkeypatch, tmp_path
):
    facts, invocation, api, session = _np_prepared_production_fixture(
        _np_ns, monkeypatch, tmp_path
    )
    try:
        state = _np_ns["_notification_state"](invocation)
        with pytest.raises(_np_ns["AuthorizationError"]):
            api.post_commit(state["commit_bytes"])
        assert len(session.calls) == 1 and api._terminal
    finally:
        _np_ns["_notification_close"](invocation)
        _np_ns["_close_notification_facts"](facts)


def test_production_notification_bound_notification_post_uses_exact_durable_bytes_and_consumes_once(
    _np_ns, monkeypatch, tmp_path
):
    facts, invocation, api, session = _np_prepared_production_fixture(
        _np_ns, monkeypatch, tmp_path
    )
    try:
        state = _np_ns["_notification_state"](invocation)
        session.queue = [
            _np_Response(
                _np_ns["_API_ORIGIN"] + _np_ns["_API_PREFIX"] + "/git/commits",
                201,
                {"sha": state["expected"]},
            )
        ]
        _np_ns["_notification_post"](invocation, api, "notification_commit")
        assert state["sequence"] == 3 and state["commit_consumed"] is True
        assert session.calls[-1][2]["data"] is state["commit_bytes"]
        assert len(session.calls) == 2
        with pytest.raises(_np_ns["AttemptError"]):
            _np_ns["_notification_post"](invocation, api, "notification_commit")
        assert len(session.calls) == 2
    finally:
        _np_ns["_notification_close"](invocation)
        _np_ns["_close_notification_facts"](facts)


def test_production_notification_notification_purpose_stamp_rejects_facts_mutation(
    _np_ns, monkeypatch, tmp_path
):
    facts, invocation, _api, session = _np_prepared_production_fixture(
        _np_ns, monkeypatch, tmp_path
    )
    try:
        _np_ns["_NOTIFICATION_FACTS"][facts]["proof"]["publication"] = "e" * 40
        with pytest.raises(_np_ns["AuthorizationError"]):
            _np_ns["_notification_facts"](facts)
        assert len(session.calls) == 1
    finally:
        _np_ns["_notification_close"](invocation)
        _np_ns["_close_notification_facts"](facts)


def test_production_notification_notification_facts_subclass_and_copy_cannot_adopt(
    _np_ns, monkeypatch, tmp_path
):
    facts, invocation, _api, _session = _np_prepared_production_fixture(
        _np_ns, monkeypatch, tmp_path
    )
    try:

        class Subclass(_np_ns["_VerifiedNotificationFacts"]):
            pass

        for value in (
            object.__new__(Subclass),
            object.__new__(_np_ns["_VerifiedNotificationFacts"]),
        ):
            with pytest.raises(_np_ns["AuthorizationError"]):
                _np_ns["_notification_facts"](value)
        with pytest.raises(_np_ns["AuthorizationError"]):
            copy.copy(facts)
    finally:
        _np_ns["_notification_close"](invocation)
        _np_ns["_close_notification_facts"](facts)


def test_production_notification_notification_fragment_has_no_scientific_call_or_historical_capability_edges():
    import ast

    source = (ROOT / "src/lotto649/v13_registered_attempt.py").read_text()
    start = source.index("# BEGIN V13 POST-AUDIT NOTIFICATION IMPLEMENTATION\n")
    end = source.index("# END V13 POST-AUDIT NOTIFICATION IMPLEMENTATION\n", start)
    tree = ast.parse(source[start:end])
    forbidden = {
        "audit_ledger",
        "_ledger_payload",
        "score_target",
        "_validated_rows",
        "build_report",
        "validate_frozen_payload",
        "moments",
        "solve_map_beta",
        "select_combination",
        "four_forecasts",
        "_load_governed_history",
        "verify_authorization",
        "_issue_verified_facts",
        "_issue_authorization",
        "begin_authorized_startup",
        "acquire_historical_lease",
        "_run_canonical",
        "_drive_sequence",
        "load_published_history",
        "predict",
        "fit",
    }
    calls = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    calls |= {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert calls.isdisjoint(forbidden)


@pytest.mark.parametrize(
    "case",
    [
        "claim_then_fake_capture",
        "empty_opportunities",
        "wrong_capture_date",
        "wrong_capture_hash",
        "capture_before_score",
        "two_captures",
        "fabricated_final6",
        "empty_top12",
        "duplicate_top12",
        "top12_without_score",
    ],
)
def test_production_notification_notification_terminal_capture_requires_just_scored_exact_nonempty_identity(
    _np_ns, _np_registration, case
):
    events = _np_synthetic_chain(_np_ns, _np_registration)
    if case == "claim_then_fake_capture":
        events = [events[0], events[-1]]
    elif case == "empty_opportunities":
        events[2]["payload"]["exact_final6_opportunities"] = []
        events[3]["payload"]["opportunities"] = []
    elif case == "wrong_capture_date":
        events[3]["payload"]["target_draw_date"] = "2020-01-04"
    elif case == "wrong_capture_hash":
        events[3]["payload"]["forecast_payload_sha256"] = "e" * 64
    elif case == "capture_before_score":
        events = [events[0], events[1], events[3], events[2]]
    elif case == "two_captures":
        events.append(copy.deepcopy(events[-1]))
    elif case == "fabricated_final6":
        events[2]["payload"]["exact_final6_opportunities"][0]["final6"] = [
            1,
            2,
            3,
            4,
            5,
            7,
        ]
    else:
        events[3]["event_kind"] = "historical_top12_all_six_detected"
        events[3]["payload"] = {
            "target_draw_date": "2020-01-01",
            "forecast_payload_sha256": events[2]["payload"]["forecast_payload_sha256"],
            "producers": [],
            "eligible_evidence": False,
        }
        if case == "duplicate_top12":
            events.append(copy.deepcopy(events[3]))
        if case == "top12_without_score":
            events = [events[0], events[3]]
    with pytest.raises(_np_ns["AuthorizationError"]):
        _np_ns["_notification_ledger_metadata"](
            _np_rechain(_np_ns, events), _np_registration["operational_contract"]
        )


def test_production_notification_notification_rehashed_forged_prediction_receipt_hash_is_rejected(
    _np_ns, _np_registration
):
    events = _np_synthetic_chain(_np_ns, _np_registration)
    events[2]["payload"]["prediction_frozen_event_sha256"] = "f" * 64
    raw = _np_rechain(_np_ns, events)
    # The outer hash chain is internally valid; the receipt still must reference
    # the exact preceding frozen event, not an arbitrary well-formed digest.
    with pytest.raises(_np_ns["AuthorizationError"], match="exact preceding freeze"):
        _np_ns["_notification_ledger_metadata"](
            raw, _np_registration["operational_contract"]
        )


def test_production_notification_notification_cannot_skip_stored_exact6_claim_then_continue(
    _np_ns, _np_registration
):
    events = _np_synthetic_chain(_np_ns, _np_registration)
    events[2]["payload"]["exact_final6_opportunities"] = []
    with pytest.raises(
        _np_ns["AuthorizationError"], match="stored opportunity metadata"
    ):
        _np_ns["_notification_ledger_metadata"](
            _np_rechain(_np_ns, events), _np_registration["operational_contract"]
        )


@pytest.mark.parametrize(
    "extra",
    [
        "def synthetic_escape(obj):\n    return obj.format(target_date='synthetic')\n",
        "def synthetic_escape(obj):\n    return obj._request_json_checked('GET', '/synthetic')\n",
        "def synthetic_escape():\n    import requests\n    return requests.Session()\n",
        "def synthetic_escape():\n    import requests as alias\n    return alias.Session()\n",
        "def synthetic_escape(fd):\n    return os.pread(fd, 1, 0)\n",
        "def synthetic_escape(fd):\n    reader = os.pread\n    return reader(fd, 1, 0)\n",
        "def synthetic_escape(path):\n    return os.mkdir(path)\n",
        "def synthetic_escape(path):\n    creator = os.mkdir\n    return creator(path)\n",
    ],
)
def test_notification_scoped_capabilities_cannot_escape_into_added_function(
    attempt, extra
):
    source = (ROOT / attempt.ATTEMPT_PATH).read_text()
    assert "format" not in attempt._REGISTERED_ATTRIBUTE_NAMES
    assert "_request_json_checked" not in attempt._REGISTERED_ATTRIBUTE_NAMES
    with pytest.raises(attempt.AuthorizationError):
        attempt._check_source_safety(
            attempt.ATTEMPT_PATH, ast.parse(source + "\n" + extra)
        )


@pytest.mark.parametrize(
    "qualified,change",
    [
        ("_NotificationHTTP.__init__", "mutation"),
        ("_NotificationHTTP.request_json", "mutation"),
        ("verify_notification_publication", "mutation"),
        ("_notification_read_immutable", "mutation"),
        ("_notification_safe_directory", "mutation"),
        ("_prepare_production_notification", "mutation"),
        ("_require_production_notification_issuance", "mutation"),
        ("_issue_notification_files", "mutation"),
        ("verify_notification_publication", "duplicate"),
        ("verify_notification_publication", "move"),
    ],
)
def test_notification_sensitive_function_qualified_identity_and_entire_ast_are_fixed(
    attempt, qualified, change
):
    tree = ast.parse((ROOT / attempt.ATTEMPT_PATH).read_text())
    parents = {
        child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)
    }
    node = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and attempt._source_function_owner(node, parents)[0] == qualified
    )
    if change == "mutation":
        node.body.append(ast.Pass())
    elif change == "duplicate":
        tree.body.append(copy.deepcopy(node))
    else:
        tree.body.remove(node)
        wrapper = ast.parse("class SyntheticMovedIssuer:\n    pass\n").body[0]
        wrapper.body = [node]
        tree.body.append(wrapper)
    with pytest.raises(attempt.AuthorizationError):
        attempt._check_source_safety(attempt.ATTEMPT_PATH, tree)


@pytest.fixture
def synthetic_notification_source_reference(attempt, monkeypatch):
    monkeypatch.setattr(attempt, "R13", "1" * 40)
    monkeypatch.setattr(attempt, "REGISTRATION_PATH", "synthetic/registration.json")
    config_path = "synthetic/config.yaml"
    seal = {
        "registered_files": [
            {"path": config_path, "git_blob": "b" * 40, "sha256": "b" * 64}
        ],
        "preserved_tree_manifest": [],
    }
    raw = attempt._canonical(seal) + b"\n"
    monkeypatch.setattr(attempt, "REGISTRATION_SHA256", hashlib.sha256(raw).hexdigest())
    entries = [
        {
            "path": attempt.REGISTRATION_PATH,
            "git_blob": "c" * 40,
            "sha256": attempt.REGISTRATION_SHA256,
        },
        {"path": config_path, "git_blob": "b" * 40, "sha256": "b" * 64},
    ]
    state = {"raw": raw, "config_oid": "b" * 40, "reads": []}

    class Git:
        def ancestor(self, earlier, later):
            return True

        def read_blob(self, commit, path):
            assert (commit, path) == (attempt.R13, attempt.REGISTRATION_PATH)
            state["reads"].append((commit, path))
            return state["raw"]

        def oid(self, commit, path):
            return (
                "c" * 40 if path == attempt.REGISTRATION_PATH else state["config_oid"]
            )

        def parents(self, commit):
            return ("3" * 40, "4" * 40)

    kwargs = {
        "head": "7" * 40,
        "execution": "5" * 40,
        "worker": "6" * 40,
        "auth": {
            "runtime_dependency_closure": entries,
            "implementation_files": [],
            "implementation_commit": "2" * 40,
            "implementation_merge": "3" * 40,
        },
        "operation": {},
    }
    return SimpleNamespace(
        git=Git(), state=state, config_path=config_path, kwargs=kwargs
    )


@pytest.mark.parametrize("role", ["seal", "config"])
@pytest.mark.parametrize(
    "mutation",
    [None, "wrong_digest", "wrong_commit", "wrong_pin", "later_runtime_checkpoint"],
)
def test_r13_source_reference_takes_exact_registered_authority_before_overlapping_runtime_entry(
    attempt, synthetic_notification_source_reference, role, mutation
):
    case = synthetic_notification_source_reference
    reference = {
        "path": attempt.REGISTRATION_PATH if role == "seal" else case.config_path,
        "git_commit": attempt.R13,
        "sha256": attempt.REGISTRATION_SHA256 if role == "seal" else "b" * 64,
    }
    if mutation == "wrong_digest":
        reference["sha256"] = "e" * 64
    elif mutation == "wrong_commit":
        reference["git_commit"] = "8" * 40
    elif mutation == "wrong_pin":
        if role == "seal":
            case.state["raw"] += b" "
        else:
            case.state["config_oid"] = "e" * 40
    elif mutation == "later_runtime_checkpoint":
        reference["git_commit"] = "2" * 40
    if mutation in {None, "later_runtime_checkpoint"}:
        assert (
            attempt._notification_reference_digest(case.git, reference, **case.kwargs)
            == reference["sha256"]
        )
    else:
        with pytest.raises(attempt.AuthorizationError):
            attempt._notification_reference_digest(case.git, reference, **case.kwargs)
    assert case.state["reads"] == [(attempt.R13, attempt.REGISTRATION_PATH)]


@pytest.mark.parametrize(
    "mutation",
    [
        None,
        "wrong_oid",
        "duplicate_committer",
        "missing_committer",
        "invalid_timezone",
        "out_of_range",
    ],
)
def test_notification_publication_timestamp_is_exact_immutable_git_metadata(
    attempt, mutation
):
    committer = b"committer Synthetic <fixture@example.invalid> 1704067200 -0400"
    if mutation == "duplicate_committer":
        committer += b"\n" + committer
    elif mutation == "missing_committer":
        committer = b"encoding UTF-8"
    elif mutation == "invalid_timezone":
        committer = committer[:-5] + b"+9999"
    elif mutation == "out_of_range":
        committer = committer.replace(b"1704067200", b"999999999999999999999999")
    raw = (
        b"tree "
        + b"a" * 40
        + b"\nauthor Synthetic <fixture@example.invalid> 1704067200 +0000\n"
        + committer
        + b"\n\nSynthetic fixed publication\n"
    )
    oid = hashlib.sha1(b"commit " + str(len(raw)).encode() + b"\x00" + raw).hexdigest()
    git = SimpleNamespace(run=lambda *args: raw)
    if mutation == "wrong_oid":
        oid = "e" * 40
    if mutation is None:
        assert (
            attempt._notification_publication_time(git, oid) == "2024-01-01T00:00:00Z"
        )
    else:
        with pytest.raises(attempt.AuthorizationError):
            attempt._notification_publication_time(git, oid)


def test_production_notification_claim_uses_publication_instant_while_intent_uses_current_utc(
    _np_ns, attempt, monkeypatch, tmp_path
):
    from datetime import datetime as real_datetime

    class Clock:
        fromtimestamp = staticmethod(real_datetime.fromtimestamp)
        fromisoformat = staticmethod(real_datetime.fromisoformat)

        @staticmethod
        def now(_zone):
            raise AssertionError("claim must not consult wallclock")

    monkeypatch.setitem(_np_ns, "datetime", Clock)
    monkeypatch.setitem(_np_ns, "_utc_now", lambda: "2035-01-01T00:00:00Z")
    facts, invocation, _api, session = _np_prepared_production_fixture(
        _np_ns, monkeypatch, tmp_path
    )
    state = _np_ns["_notification_state"](invocation)
    request = state["request"]
    assert (
        _np_ns["_notification_facts"](facts)["proof"]["publication_committer_time"]
        == "2024-01-01T00:00:00Z"
    )
    assert (
        request["author"]["date"]
        == request["committer"]["date"]
        == "2024-01-01T00:00:00Z"
    )
    assert state["intent"]["started_at"] == "2035-01-01T00:00:00Z"
    person = "LOTTO649 V13 Notification Claim <lotto649-v13-notification@users.noreply.github.com> 1704067200 +0000"
    raw = (
        f"tree {request['tree']}\nparent {request['parents'][0]}\nauthor {person}\ncommitter {person}\n\n"
        + request["message"]
    ).encode()
    expected = hashlib.sha1(
        b"commit " + str(len(raw)).encode() + b"\x00" + raw
    ).hexdigest()
    assert state["expected"] == expected
    _np_ns["_verify_notification_post"](expected, request, {"sha": expected})
    service = _SyntheticSharedNotificationService(attempt)
    service.commits[expected] = request
    observed = service.get_commit(expected)
    _np_ns["_verify_notification_get"](expected, request, observed)
    observed = copy.deepcopy(observed)
    observed["committer"]["date"] = "2035-01-01T00:00:00Z"
    with pytest.raises(_np_ns["AuthorizationError"]):
        _np_ns["_verify_notification_get"](expected, request, observed)
    altered = copy.deepcopy(request)
    altered["author"]["date"] = altered["committer"]["date"] = "2035-01-01T00:00:00Z"
    altered_oid, _, _ = _np_ns["_notification_request_parts"](altered)
    assert altered_oid != expected
    with pytest.raises(_np_ns["AuthorizationError"]):
        _np_ns["_verify_notification_post"](expected, request, {"sha": altered_oid})
    assert [call[0] for call in session.calls] == ["GET"]


@pytest.mark.parametrize(
    "provided_time", ["2024-01-01T00:00:00Z", "2035-01-01T00:00:00Z"]
)
def test_notification_private_issuance_time_is_bound_to_verified_publication_proof(
    _np_ns, monkeypatch, tmp_path, provided_time
):
    identity = {"synthetic_inert_identity": True}
    facts = object()
    state = {
        "started": True,
        "invocation": None,
        "proof": {"publication_committer_time": "2024-01-01T00:00:00Z"},
    }
    monkeypatch.setitem(
        _np_ns,
        "_notification_facts",
        lambda observed: state if observed is facts else pytest.fail("unknown facts"),
    )
    _np_ns["_PRODUCTION_NOTIFICATION_ISSUANCE"].append(
        {
            "identity": identity,
            "used": False,
            "directory": tmp_path,
            "committer_time": provided_time,
            "stamp": _np_ns["_canonical"](identity),
            "facts": facts,
        }
    )
    if provided_time == state["proof"]["publication_committer_time"]:
        _np_ns["_require_production_notification_issuance"](
            tmp_path, identity, provided_time
        )
    else:
        with pytest.raises(_np_ns["AuthorizationError"]):
            _np_ns["_require_production_notification_issuance"](
                tmp_path, identity, provided_time
            )
    assert list(tmp_path.iterdir()) == []


# Full publication fixture contribution: /root/v13_notification_production_draft,
# v13-notification-integration-fixture-authoring-20260913.
# Integrated without replacing any primary validator; startup envelope aligned
# with the registered actual producer by /root/v13_attempt_draft,
# v13-attempt-startup-binding-fix-20260913.
HARNESS = ROOT / "src/lotto649/v13_registered_attempt.py"
REGISTRATION_SOURCE = (
    ROOT / "evidence/research_registrations/v13-post-rng-main-set-overlap-v1.json"
)
REQUIREMENTS_SOURCE = ROOT / "requirements/v12-historical.txt"


def canonical(value):
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


class GitFixture:
    def __init__(self, root):
        self.root = root
        self.environment = {
            "PATH": "/usr/bin:/bin",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_AUTHOR_NAME": "Synthetic fixture only",
            "GIT_AUTHOR_EMAIL": "synthetic@example.invalid",
            "GIT_COMMITTER_NAME": "Synthetic fixture only",
            "GIT_COMMITTER_EMAIL": "synthetic@example.invalid",
            "GIT_AUTHOR_DATE": "2026-09-13T00:00:00Z",
            "GIT_COMMITTER_DATE": "2026-09-13T00:00:00Z",
        }

    def run(self, *args, raw=None):
        result = subprocess.run(
            ["/usr/bin/git", "-C", str(self.root), *args],
            input=raw,
            capture_output=True,
            env=self.environment,
            check=True,
        )
        return result.stdout

    def text(self, *args):
        return self.run(*args).decode().strip()

    def put(self, path, raw):
        file = self.root / path
        file.parent.mkdir(parents=True, exist_ok=True)
        assert not file.exists(), ("fixture cannot overwrite", path)
        file.write_bytes(raw)
        os.chmod(file, 0o644)

    def replace_source_before_commit(self, path, raw):
        # Only fixture-controlled uncommitted source replacement. No audited
        # prediction/evaluation/ledger/report is overwritten.
        assert path.startswith("docs/")
        (self.root / path).write_bytes(raw)

    def commit(self, message):
        self.run("add", "-A")
        self.run("commit", "-q", "--cleanup=verbatim", "-F", "-", raw=message)
        return self.text("rev-parse", "HEAD")

    def branch(self, name):
        self.run("checkout", "-qb", name)

    def merge_main(self, branch):
        self.run("checkout", "-q", "synthetic-main")
        self.run("merge", "--no-ff", "-qm", "Synthetic ordinary merge", branch)
        return self.text("rev-parse", "HEAD")


class SyntheticResponse:
    def __init__(self, url, value):
        self.url = url
        self.status_code = 200
        self.value = value
        self.headers = {"Content-Type": "application/json"}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def iter_content(self, _size):
        yield canonical(self.value)


class SyntheticSession:
    def __init__(self, routes):
        self.headers = {}
        self.routes = routes
        self.calls = []
        self.trust_env = True

    def mount(self, *args):
        pass

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        assert method == "GET", "No synthetic test may reach POST or SMTP"
        assert url in self.routes, ("unregistered fixture route", url)
        return SyntheticResponse(url, copy.deepcopy(self.routes[url]))


def source_message(phase, people):
    value = {
        "schema_version": "lotto649-v13-source-author-provenance-v1",
        "phase": phase,
        "contributors": people,
    }
    return (
        b"Synthetic "
        + phase.encode()
        + b" source\n\nResearch-Author-Provenance: "
        + canonical(value)
        + b"\n"
    )


def review_facts(ns, routes, *, source, base, merge, closure, phase, number):
    prefix = ns["_API_ORIGIN"] + ns["_API_PREFIX"]
    repository = {"full_name": ns["REPOSITORY"]}
    pr = {
        "number": number,
        "state": "closed",
        "merged": True,
        "merged_at": "2026-09-13T00:00:00Z",
        "merge_commit_sha": merge,
        "head": {"sha": source, "repo": repository},
        "base": {"sha": base, "ref": "main", "repo": repository},
    }
    check_id = number * 10
    check = {
        "id": check_id,
        "name": "test",
        "head_sha": source,
        "status": "completed",
        "conclusion": "success",
        "app": {"slug": "github-actions"},
    }
    routes[prefix + f"/commits/{source}/pulls?per_page=100"] = [pr]
    routes[prefix + f"/pulls/{number}"] = pr
    routes[prefix + f"/commits/{source}/check-runs?per_page=100"] = {
        "total_count": 1,
        "check_runs": [check],
    }
    routes[prefix + f"/check-runs/{check_id}"] = check
    records = []
    comments = []
    schema = {
        "I13": "lotto649-v13-i13-independent-review-v1",
        "A_H_s13": "lotto649-v13-ah13-independent-review-v1",
        "capture": "lotto649-v13-capture-publication-independent-review-v1",
    }[phase]
    for index, axis in enumerate(("standards", "spec")):
        agent = f"/root/synthetic_{phase}_{axis}"
        session = f"synthetic-{phase}-{axis}"
        body = {
            "schema_version": schema,
            "axis": axis,
            "base_sha": base,
            "head_sha": source,
            "closure_sha256": closure,
            "operational_contract_sha256": ns["OPERATIONAL_SHA256"],
            "verdict": "pass",
            "blocker_count": 0,
            "major_count": 0,
            "reviewer_kind": "independent_agent",
            "reviewer_agent_id": agent,
            "review_session_id": session,
            "publisher_login": "synthetic-publisher",
        }
        raw = canonical(body) + b"\n"
        comment_id = number * 100 + index
        comment = {
            "id": comment_id,
            "body": raw.decode(),
            "created_at": "2026-09-13T00:00:00Z",
            "updated_at": "2026-09-13T00:00:00Z",
            "issue_url": prefix + f"/issues/{number}",
            "user": {"login": "synthetic-publisher"},
        }
        comments.append(comment)
        routes[prefix + f"/issues/comments/{comment_id}"] = comment
        records.append(
            {
                "axis": axis,
                "check_id": check_id,
                "comment_body_sha256": sha(raw),
                "comment_id": comment_id,
                "pr_number": number,
                "publisher_login": "synthetic-publisher",
                "review_session_id": session,
                "reviewer_agent_id": agent,
            }
        )
    routes[prefix + f"/issues/{number}/comments?per_page=100"] = comments
    return records


@pytest.fixture
def ns(attempt, monkeypatch):
    namespace = attempt.notify_audited_capture.__globals__
    for name in (
        "_NOTIFICATION_FACTS",
        "_NOTIFICATION_TRANSPORTS",
        "_NOTIFICATION_STATES",
    ):
        monkeypatch.setitem(namespace, name, {})
    monkeypatch.setitem(namespace, "_PRODUCTION_NOTIFICATION_ISSUANCE", [])
    yield namespace
    for facts in tuple(namespace["_NOTIFICATION_FACTS"]):
        namespace["_close_notification_facts"](facts)


def build_publication_fixture(ns, monkeypatch, tmp_path, mutation=None):
    registration = json.loads(REGISTRATION_SOURCE.read_bytes())
    science = copy.deepcopy(registration["scientific_contract"])
    operation = copy.deepcopy(registration["operational_contract"])
    root = tmp_path / "synthetic-closed-publication"
    root.mkdir()
    gf = GitFixture(root)
    gf.run("init", "-q", "-b", "synthetic-main")
    # An artificial source tree exercises the actual static closure parser. It
    # never stands in for verification of the production runtime closure.
    initial = {
        "src/lotto649/__init__.py": b'"""Synthetic package."""\n',
        "src/lotto649/models/__init__.py": b'"""Synthetic models."""\n',
        "src/lotto649/operational_history.py": b'"""Synthetic inert history-reader source, never called."""\n',
        "src/lotto649/domain.py": b'"""Synthetic inert domain source, never called."""\n',
        "src/lotto649/models/factory.py": b'"""Synthetic inert factory source, never called."""\n',
        "src/lotto649/notification.py": b'"""Synthetic inert sender source, never called."""\n',
        "config.yaml": b'{"synthetic_fixture_only":true}\n',
        ns["REQUIREMENTS_PATH"]: REQUIREMENTS_SOURCE.read_bytes(),
        "synthetic-history-metadata.txt": b"Synthetic metadata pin; no operational history or outcomes.\n",
    }
    modify_paths = ns["_REGISTRATION_STATUSES"]["M"]
    for path in modify_paths:
        initial[path] = b"Synthetic pre-registration source.\n"
    for path, raw in initial.items():
        gf.put(path, raw)
    base = gf.commit(b"Synthetic history/source metadata authority\n")
    history_pin = {
        "commit": base,
        "path": "synthetic-history-metadata.txt",
        "mode": "100644",
        "type": "blob",
        "git_blob": blob(initial["synthetic-history-metadata.txt"]),
        "bytes": len(initial["synthetic-history-metadata.txt"]),
    }
    monkeypatch.setitem(ns, "HISTORY_AUTHORITY", base)
    monkeypatch.setitem(ns, "_PRIOR_ACCOUNTING_PINS", [history_pin])
    synthetic_history = copy.deepcopy(
        operation["identity"]["governed_history_identity"]
    )
    synthetic_history["commit"] = base
    for pin in synthetic_history["immutable_objects"].values():
        pin["git_blob"] = history_pin["git_blob"]
        pin["sha256"] = sha(initial["synthetic-history-metadata.txt"])
        pin["bytes"] = history_pin["bytes"]
        if "commit" in pin:
            pin["commit"] = base
        if "genesis_commit" in pin:
            pin["genesis_commit"] = base
    operation["identity"]["governed_history_authority"] = base
    operation["identity"]["governed_history_identity"] = synthetic_history
    operation["authorization"]["prior_family_accounting_preflight"]["object_pins"] = [
        history_pin
    ]
    science["scope"]["history_authority"] = base
    science["scope"]["history_identity"] = synthetic_history
    fingerprint = sha(canonical(science) + b"\n")
    op_sha = sha(canonical(operation) + b"\n")
    monkeypatch.setitem(ns, "FINGERPRINT", fingerprint)
    monkeypatch.setitem(ns, "OPERATIONAL_SHA256", op_sha)
    authors = {
        phase: [
            {
                "agent_id": "/root/synthetic_" + phase + "_author",
                "session_id": "synthetic-" + phase + "-authoring",
            }
        ]
        for phase in ("R13", "I13", "A_H_s13")
    }
    metadata_git = ns["GitRepository"](root)
    preserved = ns["_tree_metadata"](metadata_git, base)
    registration_paths = set().union(*map(set, ns["_REGISTRATION_STATUSES"].values()))
    preserved = [
        entry for entry in preserved if entry["path"] not in registration_paths
    ]
    gf.branch("synthetic-r13")
    for path in modify_paths:
        gf.replace_source_before_commit(path, b"Synthetic registered source.\n")
    for path in ns["_REGISTRATION_STATUSES"]["A"]:
        if path == ns["REGISTRATION_PATH"]:
            continue
        if path == ns["CONFIG_PATH"]:
            value = {
                "schema_version": "lotto649-v13-research-config-v1",
                "experiment_id": "V13_post_rng_main_set_overlap",
                "model_version": "v13.0.0",
                "seed": 649,
                "historical_only": True,
                "registration_path": ns["REGISTRATION_PATH"],
                "scientific_contract_sha256": fingerprint,
                "operational_contract_sha256": op_sha,
                "activation": "registration_only_no_runtime_wiring",
            }
            raw = canonical(value) + b"\n"
        else:
            raw = b'"""Synthetic registered source fixture."""\n'
        gf.put(path, raw)
    registered = []
    for path in sorted(registration_paths - {ns["REGISTRATION_PATH"]}):
        raw = (root / path).read_bytes()
        registered.append(
            {"path": path, "git_blob": blob(raw), "bytes": len(raw), "sha256": sha(raw)}
        )
    seal = {
        "schema_version": registration["schema_version"],
        "experiment_id": "V13_post_rng_main_set_overlap",
        "model_version": "v13.0.0",
        "status": registration["status"],
        "registration_base": base,
        "scientific_contract": science,
        "statistical_fingerprint_sha256": fingerprint,
        "operational_contract": operation,
        "operational_contract_sha256": op_sha,
        "registered_files": registered,
        "preserved_tree_manifest": preserved,
        "preserved_tree_manifest_sha256": sha(canonical(preserved) + b"\n"),
        "preparation_provenance": {
            "contributors": [{**authors["R13"][0], "role": "synthetic fixture author"}],
            "scope": "Synthetic fixture only; no actual historical evidence.",
        },
    }
    seal_raw = canonical(seal) + b"\n"
    gf.put(ns["REGISTRATION_PATH"], seal_raw)
    r13 = gf.commit(source_message("R13", authors["R13"]))
    monkeypatch.setitem(ns, "R13", r13)
    monkeypatch.setitem(ns, "REGISTRATION_SHA256", sha(seal_raw))
    r13_merge = gf.merge_main("synthetic-r13")
    gf.branch("synthetic-i13")
    for path in ns["IMPLEMENTATION_PATHS"]:
        raw = (
            b'"""Synthetic frozen implementation source."""\n'
            if path.endswith(".py")
            else b"{}\n"
        )
        if path in (ns["ATTEMPT_PATH"], ns["LAUNCHER_PATH"]):
            # Preserve the production sealed-function inventory and its exact
            # AST digests; these source bytes are inspected, never executed
            # from the synthetic repository.
            raw = (HARNESS.parents[2] / path).read_bytes()
        gf.put(path, raw)
    implementation = gf.commit(source_message("I13", authors["I13"]))
    implementation_merge = gf.merge_main("synthetic-i13")
    # Source/origin metadata are fixture inputs, not validator replacements.
    monkeypatch.setitem(ns, "__file__", str(root / ns["ATTEMPT_PATH"]))
    fake_modules = {
        name: SimpleNamespace(__file__=str(root / path))
        for name, path in {
            "lotto649": "src/lotto649/__init__.py",
            "lotto649.models": "src/lotto649/models/__init__.py",
            "lotto649.v13_registered_attempt": ns["ATTEMPT_PATH"],
        }.items()
    }
    supplied_sys = SimpleNamespace(
        modules=fake_modules,
        # Explicit synthetic runtime observations keep this graph portable.
        # Actual installed runtime is independently checked by source preflight.
        implementation=SimpleNamespace(name="cpython"),
        version_info=(3, 12, 11),
        float_info=SimpleNamespace(radix=2, mant_dig=53, max_exp=1024),
        byteorder="little",
        flags=SimpleNamespace(isolated=0, no_site=0),
        dont_write_bytecode=True,
        stderr=sys.stderr,
    )
    monkeypatch.setitem(ns, "sys", supplied_sys)
    observed_runtime = copy.deepcopy(ns["_EXACT_RUNTIME"])
    monkeypatch.setitem(
        ns,
        "platform",
        SimpleNamespace(
            python_version=lambda: observed_runtime["python_version"],
            platform=lambda: observed_runtime["platform"],
            machine=lambda: observed_runtime["machine"],
        ),
    )
    supplied_distributions = [
        SimpleNamespace(metadata={"Name": name}, version=version)
        for name, version in observed_runtime["installed_distributions"].items()
    ]
    monkeypatch.setitem(ns, "distributions", lambda: supplied_distributions)
    closure = ns["_core_and_closure"](metadata_git, implementation)
    implementation_files = ns["_implementation_manifest"](metadata_git, implementation)
    closure_sha = sha(canonical(closure))
    runtime = ns["runtime_identity"]()
    routes = {}
    i_reviews = review_facts(
        ns,
        routes,
        source=implementation,
        base=r13_merge,
        merge=implementation_merge,
        closure=closure_sha,
        phase="I13",
        number=101,
    )
    auth = {
        "schema_version": "lotto649-v13.0.0-historical-authorization-v1",
        "experiment_id": "V13_post_rng_main_set_overlap",
        "model_version": "v13.0.0",
        "repository": ns["REPOSITORY"],
        "branch": "main",
        "registration_commit": r13,
        "registration_sha256": sha(seal_raw),
        "scientific_registration_commit": r13,
        "statistical_fingerprint_sha256": fingerprint,
        "operational_contract_sha256": op_sha,
        "pure_core_sha256": sha((root / ns["CORE_PATH"]).read_bytes()),
        "implementation_commit": implementation,
        "implementation_base": r13_merge,
        "implementation_merge": implementation_merge,
        "authorization_base": implementation_merge,
        "canonical_command": ns["COMMAND"],
        "governed_history_authority": base,
        "governed_history_identity": synthetic_history,
        "runtime": runtime,
        "implementation_files": implementation_files,
        "implementation_files_sha256": sha(canonical(implementation_files)),
        "runtime_dependency_closure": closure,
        "runtime_dependency_closure_sha256": closure_sha,
        "review_records": i_reviews,
    }
    if mutation == "wrong_authorization":
        auth["model_version"] = "v13.0.999"
    if mutation == "wrong_core":
        auth["pure_core_sha256"] = "f" * 64
    if mutation == "wrong_closure":
        auth["runtime_dependency_closure"] = copy.deepcopy(closure[:-1])
        auth["runtime_dependency_closure_sha256"] = sha(
            canonical(auth["runtime_dependency_closure"])
        )
    gf.branch("synthetic-auth")
    auth_raw = canonical(auth) + b"\n"
    gf.put(ns["AUTHORIZATION_PATH"], auth_raw)
    auth_source = gf.commit(source_message("A_H_s13", authors["A_H_s13"]))
    execution = gf.merge_main("synthetic-auth")
    a_reviews = review_facts(
        ns,
        routes,
        source=auth_source,
        base=implementation_merge,
        merge=execution,
        closure=closure_sha,
        phase="A_H_s13",
        number=102,
    )
    # An unattached local synthetic Git object is metadata only. No Lease object,
    # consumption ref, worker, history reader or execution capability is created.
    person = {
        "name": "LOTTO649 V13 Consumption Lease",
        "email": "lotto649-v13-lease@users.noreply.github.com",
        "date": "2026-09-13T00:00:00Z",
    }
    lease_body = {
        "schema_version": "lotto649-v13-consumption-lease-v1",
        "authorization_seal_sha256": sha(auth_raw),
        "canonical_command": ns["COMMAND"],
        "execution_authority_M_A": execution,
        "nonce_hex": "1" * 64,
    }
    lease_request = {
        "tree": metadata_git.tree(execution),
        "parents": [execution],
        "author": person,
        "committer": dict(person),
        "message": (canonical(lease_body) + b"\n").decode(),
    }
    lease_oid, lease_raw, _projection = ns["_lease_request_parts"](lease_request)
    assert (
        gf.run("hash-object", "-t", "commit", "-w", "--stdin", raw=lease_raw)
        .decode()
        .strip()
        == lease_oid
    )
    worker_paths = operation["claim_ledger_publication"]["worker_outputs"]
    original_facts = {
        "repository": str(root),
        "execution_commit": execution,
        "source_commit": auth_source,
        "payload": auth,
        "authorization_sha256": sha(auth_raw),
        "authorization_review_records": a_reviews,
    }
    startup_identity = {
        "execution_authority_M_A_H13": execution,
        "registration_R13": r13,
        "source_A_H_s13": auth_source,
        "implementation_commit": implementation,
        "authorization_base": implementation_merge,
        "registration_sha256": sha(seal_raw),
        "config_sha256": sha((root / ns["CONFIG_PATH"]).read_bytes()),
        "authorization_sha256": sha(auth_raw),
        "historical_runtime_dependency_closure_sha256": closure_sha,
        "runtime_identity_sha256": sha(canonical(runtime)),
        "requirements_sha256": ns["REQUIREMENTS_SHA256"],
        "required_pure_core_sha256": auth["pure_core_sha256"],
        "statistical_fingerprint_sha256": fingerprint,
        "operational_contract_sha256": op_sha,
        "verified_facts_sha256": sha(canonical(original_facts)),
    }
    lease_ref_request = {"ref": ns["LEASE_REF"], "sha": lease_oid}

    def startup_intent(phase, request):
        raw = canonical(request)
        return {
            "phase_enum": phase,
            "nonce_hex": "1" * 64,
            "expected_lease_oid": lease_oid,
            "raw_commit_sha256": sha(lease_raw),
            "request_body_bytes": len(raw),
            "request_body_sha256": sha(raw),
        }

    def startup_receipt(phase):
        return {
            "phase_enum": phase,
            "result_enum": "success",
            "http_status": 201,
            "validated_oid": lease_oid,
        }

    first_payloads = [
        {
            "repository": ns["REPOSITORY"],
            "branch": "main",
            "startup_identity": startup_identity,
        },
        {},
        {"http_status": 404},
        startup_intent("lease_commit", lease_request),
        startup_receipt("lease_commit"),
        {"validated_oid": lease_oid},
        startup_intent("lease_ref", lease_ref_request),
        startup_receipt("lease_ref"),
        {"validated_oid": lease_oid},
        {},
    ]
    startup_lines = []

    def append_startup(kind, payload):
        value = {
            "schema_version": "lotto649-v13.0.0-historical-startup-v1",
            "sequence": len(startup_lines),
            "generated_at": (
                f"2026-09-13T00:00:{len(startup_lines) if len(startup_lines) < 10 else len(startup_lines) + 2:02d}Z"
                if mutation == "distinct_producer_clock"
                else "2026-09-13T00:00:00Z"
            ),
            "previous_event_sha256": sha(startup_lines[-1]) if startup_lines else None,
            "kind": kind,
            "payload": payload,
        }
        startup_lines.append(canonical(value) + b"\n")

    for kind, payload in zip(ns["_STARTUP_PHASES"][:10], first_payloads, strict=True):
        append_startup(kind, payload)
    checkpoint = {
        "path": worker_paths["startup"],
        "sequence": 9,
        "head_sha256": sha(startup_lines[9]),
        "prefix_byte_count": sum(map(len, startup_lines[:10])),
        "prefix_sha256": sha(b"".join(startup_lines[:10])),
    }
    bindings = {
        **auth,
        "startup_checkpoint": checkpoint,
        "verified_facts_sha256": sha(canonical(original_facts)),
        "execution_authority_M_A_H13": execution,
        "authorization_source_A_H_s13": auth_source,
        "authorization_sha256": sha(auth_raw),
        "lease_ref": ns["LEASE_REF"],
        "lease_commit_L_H13": lease_oid,
        "nonce_hex": "1" * 64,
        "seed": 649,
        "classification": "consumed_historical_diagnostic_only",
    }
    claim = {
        "schema_version": "lotto649-v13.0.0-permanent-claim-v1",
        "claimed_at": (
            "2026-09-13T00:00:10Z"
            if mutation == "distinct_producer_clock"
            else "2026-09-13T00:00:00Z"
        ),
        "bindings": bindings,
        "verified_authorization_facts": original_facts,
    }
    claim_raw = canonical(claim) + b"\n"
    events = synthetic_chain(ns, seal)
    if mutation == "distinct_producer_clock":
        for event, second in zip(events, (11, 15, 16, 17), strict=True):
            event["recorded_at"] = f"2026-09-13T00:00:{second:02d}Z"
        events[2]["payload"]["prediction_generated_at"] = events[1]["recorded_at"]
    for event in events:
        event["bindings"] = bindings
    frozen = events[1]["payload"]["forecast_payload"]
    frozen["bindings"] = bindings
    frozen_sha = sha(canonical(frozen) + b"\n")
    events[0]["payload"] = {
        "claim_sha256": sha(claim_raw),
        "startup_checkpoint": checkpoint,
    }
    events[1]["payload"]["forecast_payload_sha256"] = frozen_sha
    events[2]["payload"]["forecast_payload_sha256"] = frozen_sha
    events[3]["payload"]["forecast_payload_sha256"] = frozen_sha
    rechain(ns, events)
    events[2]["payload"]["prediction_frozen_event_sha256"] = events[1]["event_sha256"]
    if mutation == "forged_frozen_receipt":
        events[2]["payload"]["prediction_frozen_event_sha256"] = "e" * 64
    if mutation == "fake_terminal_capture":
        events[3]["payload"]["opportunities"] = []
    ledger_raw = rechain(ns, events)
    append_startup("claim_created", {"claim_sha256": sha(claim_raw)})
    append_startup(
        "scientific_ledger_started", {"first_event_sha256": events[0]["event_sha256"]}
    )
    append_startup("history_load_intent", {})
    startup_raw = b"".join(startup_lines)
    ledger = {
        "event_count": 4,
        "scored_target_count": 1,
        "head_sha256": events[-1]["event_sha256"],
        "pending_forecast": False,
        "stopped_for_audit": True,
        "file_sha256": sha(ledger_raw),
    }
    row = {
        **events[2]["payload"],
        "scored_event_sequence": 2,
        "scored_event_sha256": events[2]["event_sha256"],
    }
    report_keys = [
        "annual_descriptive_only",
        "audit",
        "audit_publication",
        "best_final6_by_model",
        "bindings",
        "candidate_audit_handoff",
        "claim_sha256",
        "classification",
        "classification_zh",
        "complete_registered_scope",
        "cyclic_control",
        "disposition",
        "eligible_evidence",
        "exclusions",
        "expected_target_count",
        "experiment_id",
        "fair_baselines",
        "gates",
        "independent_leakage_audit",
        "ledger",
        "model_order",
        "model_version",
        "multiplicity",
        "operational_contract_sha256",
        "opportunities",
        "opportunity_interpretation",
        "partial_descriptive",
        "primary_metric",
        "processed_target_count",
        "promotion_authority",
        "required_pure_core_sha256",
        "schema_version",
        "scope_order",
        "scopes",
        "seed",
        "statistical_fingerprint_sha256",
        "stop_reason",
        "targets",
    ]
    report = {key: None for key in report_keys}
    report.update(
        {
            "schema_version": "lotto649.v13.0.0.historical-diagnostic-report.v1",
            "experiment_id": "V13_post_rng_main_set_overlap",
            "model_version": "v13.0.0",
            "classification": "consumed_historical_diagnostic_only",
            "bindings": bindings,
            "ledger": ledger,
            "claim_sha256": sha(claim_raw),
            "processed_target_count": 1,
            "independent_leakage_audit": "pending",
            "audit_publication": "pending_git_integration",
            "targets": [row],
        }
    )
    report_raw = canonical(report) + b"\n"
    markdown_raw = b"# Synthetic frozen worker report\n\nFixture only; no actual research result.\n"
    payloads = {
        "startup": startup_raw,
        "claim": claim_raw,
        "ledger": ledger_raw,
        "json": report_raw,
        "markdown": markdown_raw,
    }
    manifest = {
        "schema_version": "lotto649-v13.0.0-report-commit-manifest-v1",
        "classification": "consumed_historical_diagnostic_only",
        "parent_commit": execution,
        "authorization_sha256": sha(auth_raw),
        "files": [
            {
                "path": worker_paths[role],
                "git_blob": blob(raw),
                "sha256": sha(raw),
                "bytes": len(raw),
            }
            for role, raw in sorted(
                payloads.items(), key=lambda pair: worker_paths[pair[0]]
            )
        ],
        "startup_checkpoint": checkpoint,
        "sealed_startup": {
            "path": worker_paths["startup"],
            "bytes": len(startup_raw),
            "sha256": sha(startup_raw),
        },
        "self_reference": "containing_commit_resolved_from_Git_object_not_embedded",
    }
    if mutation == "startup_manifest_unclosed":
        manifest["startup_checkpoint"] = {"unexpected": True}
        manifest["sealed_startup"] = "invalid type"
    if mutation == "startup_sealed_bytes_unbound":
        manifest["sealed_startup"]["sha256"] = "f" * 64
    if mutation == "startup_prefix_bytes_unbound":
        manifest["startup_checkpoint"] = {
            **checkpoint,
            "prefix_sha256": "f" * 64,
        }
    payloads["manifest"] = canonical(manifest) + b"\n"
    if mutation == "distinct_producer_clock":
        # Publication follows all fabricated event instants, while M and the
        # raw historical lease projection retain the earlier fixed 00:00 date.
        gf.environment["GIT_AUTHOR_DATE"] = "2026-09-13T00:01:00Z"
        gf.environment["GIT_COMMITTER_DATE"] = "2026-09-13T00:01:00Z"
    gf.branch("synthetic-worker-artifacts")
    for role, raw in payloads.items():
        gf.put(worker_paths[role], raw)
    worker = gf.commit(b"Synthetic immutable six-file worker evidence\n")
    worker_publication = gf.merge_main("synthetic-worker-artifacts")
    target = "2020-01-01"
    producers = science["identity"]["producer_order"]
    primary = producers[0]
    capture_paths = {
        role: template.format(target_date=target, primary_model_name=primary)
        for role, template in operation["capture_audit_notification"]["paths"].items()
    }
    source_contributors = sorted(
        [person for people in authors.values() for person in people],
        key=lambda person: (person["agent_id"].encode(), person["session_id"].encode()),
    )
    auditor = {
        "agent_id": "/root/synthetic_capture_auditor",
        "session_id": "synthetic-capture-audit",
    }
    audit = {
        "schema_version": "lotto649-v13.0.0-capture-independent-audit-v1",
        "experiment_id": "V13_post_rng_main_set_overlap",
        "model_version": "v13.0.0",
        "target_draw_date": target,
        "final6": list(range(1, 7)),
        "primary_model_name": primary,
        "producer_model_names": producers,
        "worker_artifact_commit": worker,
        "execution_commit": execution,
        "registration_commit": r13,
        "scientific_contract_sha256": fingerprint,
        "operational_contract_sha256": op_sha,
        "claim_sha256": sha(claim_raw),
        "ledger_sha256": sha(ledger_raw),
        "forecast_payload_sha256": frozen_sha,
        "reviewer_agent_id": auditor["agent_id"],
        "review_session_id": auditor["session_id"],
        "source_contributors": source_contributors,
        "audited_at": "2026-09-13T00:00:00Z",
        "verdict": "pass",
        "blocker_count": 0,
        "major_count": 0,
        "dimensions": {},
        "limitations": [
            "Wholly synthetic fixture: these statements are not an audit of real data, chronology or outcomes."
        ],
    }
    for dimension in science["stopping_and_notifications"]["audit_dimensions"]:
        reference = {
            "path": "docs/experiments/V13_post_rng_main_set_overlap.md",
            "sha256": sha(
                (
                    root / "docs/experiments/V13_post_rng_main_set_overlap.md"
                ).read_bytes()
            ),
            "git_commit": r13,
        }
        if mutation in {"r13_seal_reference", "r13_config_reference"}:
            selected = (
                ns["REGISTRATION_PATH"]
                if mutation == "r13_seal_reference"
                else ns["CONFIG_PATH"]
            )
            reference = {
                "path": selected,
                "sha256": sha((root / selected).read_bytes()),
                "git_commit": r13,
            }
        if mutation == "wrong_reference_sha":
            reference["sha256"] = "e" * 64
        if dimension == "full history authority":
            reference = {
                "path": history_pin["path"],
                "sha256": sha(initial[history_pin["path"]]),
                "git_commit": base,
            }
        if dimension == "Git topology/closure/runtime":
            reference = {
                "path": ns["CORE_PATH"],
                "sha256": sha((root / ns["CORE_PATH"]).read_bytes()),
                "git_commit": implementation,
            }
        if dimension == "immutable prediction-before-reveal ledger":
            reference = {
                "path": worker_paths["ledger"],
                "sha256": sha(ledger_raw),
                "git_commit": worker,
            }
        audit["dimensions"][dimension] = {"verdict": "pass", "evidence": [reference]}
    if mutation == "failed_audit":
        audit["dimensions"]["target and future exclusion"]["verdict"] = "fail"
    if mutation == "author_is_auditor":
        audit["reviewer_agent_id"] = authors["I13"][0]["agent_id"]
    audit_raw = canonical(audit) + b"\n"
    audit_md = ns["render_capture_audit_markdown"](audit)
    if mutation == "wrong_audit_render":
        audit_md = b"# Altered but consistently hashed synthetic audit\n"
    bundle = {
        "schema_version": "lotto649-v13.0.0-historical-6of6-candidate-v1",
        "experiment_id": "V13_post_rng_main_set_overlap",
        "model_version": "v13.0.0",
        "classification": "consumed_historical_diagnostic_only",
        "target_draw_date": target,
        "final6": list(range(1, 7)),
        "primary_model_name": primary,
        "producer_model_names": producers,
        "worker_artifact_commit": worker,
        "execution_commit": execution,
        "claim_sha256": sha(claim_raw),
        "ledger_sha256": sha(ledger_raw),
        "forecast_payload_sha256": frozen_sha,
        "audit_json_path": capture_paths["independent_audit_json"],
        "audit_json_sha256": sha(audit_raw),
        "audit_markdown_path": capture_paths["independent_audit_markdown"],
        "audit_markdown_sha256": sha(audit_md),
        "audit_verdict": "pass",
    }
    if mutation == "wrong_bundle":
        bundle["forecast_payload_sha256"] = "e" * 64
    gf.branch("synthetic-capture-publication")
    for path, raw in (
        (capture_paths["independent_audit_json"], audit_raw),
        (capture_paths["independent_audit_markdown"], audit_md),
        (capture_paths["candidate_bundle"], canonical(bundle) + b"\n"),
    ):
        gf.put(path, raw)
    capture_authors = sorted(
        [
            auditor,
            {
                "agent_id": "/root/synthetic_capture_publisher",
                "session_id": "synthetic-capture-publication",
            },
        ],
        key=lambda person: (person["agent_id"].encode(), person["session_id"].encode()),
    )
    trailer = {
        "schema_version": "lotto649-v13-capture-publication-authors-v1",
        "contributors": capture_authors,
    }
    publication_source = gf.commit(
        b"Synthetic audited capture publication\n\nCapture-Publication-Authors: "
        + canonical(trailer)
        + b"\n"
    )
    publication = gf.merge_main("synthetic-capture-publication")
    review_facts(
        ns,
        routes,
        source=publication_source,
        base=worker_publication,
        merge=publication,
        closure=closure_sha,
        phase="capture",
        number=103,
    )
    prefix = ns["_API_ORIGIN"] + ns["_API_PREFIX"]
    routes[prefix] = {
        "node_id": ns["REPOSITORY_NODE_ID"],
        "full_name": ns["REPOSITORY"],
        "default_branch": "main",
        "private": False,
    }
    routes[prefix + "/hash-algorithm"] = {"hash_algorithm": "sha1"}
    routes[prefix + "/branches/main/protection"] = {
        "enforce_admins": {"enabled": True},
        "allow_force_pushes": {"enabled": False},
        "allow_deletions": {"enabled": False},
    }
    routes[prefix + "/git/ref/heads/main"] = {
        "ref": "refs/heads/main",
        "object": {"type": "commit", "sha": publication},
    }
    if mutation in {"wrong_i_review", "wrong_a_review", "wrong_n_review"}:
        number = {"wrong_i_review": 101, "wrong_a_review": 102, "wrong_n_review": 103}[
            mutation
        ]
        comment = routes[prefix + f"/issues/comments/{number * 100}"]
        value = json.loads(comment["body"])
        value["major_count"] = 1
        comment["body"] = (canonical(value) + b"\n").decode()
    if mutation == "wrong_main":
        routes[prefix + "/git/ref/heads/main"]["object"]["sha"] = worker_publication
    if mutation == "wrong_loaded_origin":
        fake_modules["lotto649.v13_registered_attempt"].__file__ = str(
            root.parent / "foreign-source.py"
        )
    session = SyntheticSession(routes)
    import requests

    monkeypatch.setattr(requests, "Session", lambda: session)
    api = ns["_NotificationHTTP"]("synthetic-token-not-a-real-credential")
    return SimpleNamespace(
        root=root,
        git=gf,
        api=api,
        session=session,
        ns=ns,
        history_path=history_pin["path"],
        publication=publication,
        publication_time=(
            "2026-09-13T00:01:00Z"
            if mutation == "distinct_producer_clock"
            else "2026-09-13T00:00:00Z"
        ),
        source=publication_source,
        worker=worker,
        execution=execution,
        capture_paths=capture_paths,
        authors=source_contributors,
    )


def synthetic_chain(ns, registration):
    operation = registration["operational_contract"]
    order = registration["scientific_contract"]["identity"]["producer_order"]
    state = {
        "source_draw_date": "2019-12-28",
        "source_anchor": [1, 2, 3, 4, 5, 6],
        "transformed_anchor": None,
        "training_pair_count": 0,
        "training_overlap_sum": 0,
        "scientific_projection_sha256": "a" * 64,
        "counts_sha256": "b" * 64,
    }
    for key, value in (
        ("beta", 0.0),
        ("mean", 36 / 49),
        ("complement_mean", 6 - 36 / 49),
        ("log_z", 1.0),
    ):
        state[key] = value
        state[key + "_hex"] = value.hex()
    forecasts = []
    for index, name in enumerate(order):
        item = {
            "model_name": name,
            "model_version": "v13.0.0" if index < 2 else "v1.0.0",
            "feature_set": "synthetic_frozen_record",
            "probabilities": {str(n): 6 / 49 for n in range(1, 50)},
            "probability_hex": {str(n): (6 / 49).hex() for n in range(1, 50)},
            "ranking": list(range(1, 50)),
            "top6": list(range(1, 7)),
            "top12": list(range(1, 13)),
            "top18": list(range(1, 19)),
            "final6": list(range(1, 7)),
            "scientific_state": copy.deepcopy(state) if index < 2 else None,
        }
        if index == 1:
            item["scientific_state"]["transformed_anchor"] = [2, 3, 4, 5, 6, 7]
        forecasts.append(item)
    hashes = {
        item["model_name"]: ns["_sha"](ns["_canonical"](item) + b"\n")
        for item in forecasts
    }
    bindings = {"classification": "consumed_historical_diagnostic_only"}
    frozen = {
        "schema_version": "lotto649-v13.0.0-frozen-forecast-v1",
        "classification": "consumed_historical_diagnostic_only",
        "model_version": "v13.0.0",
        "target_draw_date": "2020-01-01",
        "history_through": "2019-12-28",
        "training_cutoff_date": "2019-12-28",
        "visible_prefix_sha256": "c" * 64,
        "visible_prefix_draw_count": 1,
        "bindings": bindings,
        "forecasts": forecasts,
        "forecast_sha256_by_model": hashes,
    }
    digest = ns["_sha"](ns["_canonical"](frozen) + b"\n")
    opportunities = [
        {
            "final6": list(range(1, 7)),
            "primary_producer": order[0],
            "producer_model_names": order,
            "forecast_sha256_by_producer": hashes,
            "hits": 6,
        }
    ]
    events = []

    def add(kind, payload):
        event = {
            "schema_version": "lotto649-v13.0.0-attempt-ledger-v1",
            "sequence": len(events),
            "recorded_at": "2026-09-13T00:00:00Z",
            "previous_event_sha256": events[-1]["event_sha256"] if events else "0" * 64,
            "event_kind": kind,
            "bindings": bindings,
            "payload": payload,
        }
        event["event_sha256"] = ns["_sha"](ns["_canonical"](event))
        events.append(event)

    # Fabricated closed metadata; full publication replaces it with real bytes.
    checkpoint = {
        "path": operation["startup"]["path"],
        "sequence": 9,
        "head_sha256": "a" * 64,
        "prefix_byte_count": 1,
        "prefix_sha256": "b" * 64,
    }
    add("attempt_claimed", {"claim_sha256": "d" * 64, "startup_checkpoint": checkpoint})
    add(
        "prediction_frozen",
        {"forecast_payload": frozen, "forecast_payload_sha256": digest},
    )
    row = {
        "target_draw_date": "2020-01-01",
        "actual": list(range(1, 7)),
        "bonus": 7,
        "forecast_payload": frozen,
        "forecast_payload_sha256": digest,
        "prediction_generated_at": events[1]["recorded_at"],
        "prediction_frozen_event_sequence": 1,
        "prediction_frozen_event_sha256": events[1]["event_sha256"],
        "scores": [],
        "fair_scores": {"brier_score": 0.1, "log_loss": 0.3},
        "unique_final6": opportunities,
        "unique_opportunity_count": 1,
        "exact_final6_opportunities": opportunities,
        "top12_all_six_producers": order,
        "cumulative_opportunities": {
            "unique_opportunity_count": 1,
            "nominal_fair_exact6_chance": 1 / 13983816,
        },
    }
    for index, name in enumerate(order):
        row["scores"].append(
            {
                "model_name": name,
                "model_version": forecasts[index]["model_version"],
                "forecast_sha256": hashes[name],
                "top6_hits": 6,
                "top12_hits": 6,
                "top18_hits": 6,
                "final6_hits": 6,
                "matched_final6": list(range(1, 7)),
                "mean_actual_rank": 3.5,
                "brier_score": 0.1,
                "log_loss": 0.3,
                "joint_log_gain": None,
            }
        )
    add("target_revealed_scored", row)
    add(
        "historical_6of6_candidate_detected",
        {
            "target_draw_date": "2020-01-01",
            "forecast_payload_sha256": digest,
            "opportunities": opportunities,
            "audit_status": "independent_leakage_audit_pending",
            "eligible_evidence": False,
            "global_stop_search": True,
        },
    )
    return events


def rechain(ns, events):
    for index, event in enumerate(events):
        event["sequence"] = index
        event["previous_event_sha256"] = (
            events[index - 1]["event_sha256"] if index else "0" * 64
        )
        event["event_sha256"] = ns["_sha"](
            ns["_canonical"]({k: v for k, v in event.items() if k != "event_sha256"})
        )
    return b"".join(ns["_canonical"](event) + b"\n" for event in events)


@pytest.mark.parametrize("clock_case", [None, "distinct_producer_clock"])
def test_complete_synthetic_publication_traversal_uses_real_validators(
    ns, monkeypatch, tmp_path, clock_case
):
    fixture = build_publication_fixture(ns, monkeypatch, tmp_path, clock_case)
    calls = []
    original_read = ns["GitRepository"].read_blob

    def guarded_read(self, commit, path):
        calls.append(path)
        assert path != fixture.history_path, (
            "notification opened synthetic governed-history payload"
        )
        return original_read(self, commit, path)

    monkeypatch.setattr(ns["GitRepository"], "read_blob", guarded_read)
    watched = {
        "_registration_origin",
        "_registered_authorities",
        "_notification_authorization_metadata",
        "_core_and_closure",
        "runtime_dependency_closure",
        "_check_source_safety",
        "_verify_worktree_runtime",
        "_verify_loaded_modules",
        "_verify_reviews",
        "_discover_authorization_reviews",
        "_notification_publication_reviews",
        "_notification_reference_digest",
        "_notification_capture_artifacts",
        "_notification_ledger_metadata",
        "_notification_frozen_bytes",
        "_notification_blob_origin",
        "_capture_publication_authors",
        "_notification_read_immutable",
        "render_capture_audit_markdown",
    }
    forbidden = {
        "verify_authorization",
        "_issue_verified_facts",
        "_issue_authorization",
        "begin_authorized_startup",
        "_run_canonical",
        "_issue_lease",
        "acquire_historical_lease",
        "_load_governed_history",
        "score_target",
        "solve_map_beta",
        "moments",
        "select_combination",
        "four_forecasts",
        "_verify_registered_numerics",
        "build_report",
        "predict",
        "fit",
        "_default_notification",
        "send_email",
        "_issue_notification_files",
        "_notification_safe_directory",
        "load_published_history",
        "forecast_candidate",
        "forecast_control",
        "_drive_notification",
        "_drive_sequence",
    }
    observed = set()

    def trace(frame, event, _arg):
        if event == "call":
            name = frame.f_code.co_name
            assert name not in forbidden, (
                "notification entered scientific/historical seam",
                name,
            )
            if name in watched:
                observed.add(name)

    previous_profile = sys.getprofile()
    try:
        sys.setprofile(trace)
        facts = ns["verify_notification_publication"](fixture.root, api=fixture.api)
    finally:
        sys.setprofile(previous_profile)
    assert observed == watched, ("real validators not reached", watched - observed)
    try:
        state = ns["_notification_facts"](facts)
        assert state["proof"]["publication"] == fixture.publication
        assert state["proof"]["publication_committer_time"] == fixture.publication_time
        assert state["proof"]["audit"]["worker_artifact_commit"] == fixture.worker
        assert len(state["files"]) == 9
        assert state["started"] is False and state["invocation"] is None
        assert state["proof"]["audit"]["source_contributors"] == fixture.authors
        assert all(method == "GET" for method, _url, _kwargs in fixture.session.calls)
        assert not (fixture.root / "evidence/research_notifications").exists()
        assert not ns["_NOTIFICATION_STATES"]
        assert fixture.git.run("status", "--porcelain=v1") == b""
    finally:
        ns["_close_notification_facts"](facts)


@pytest.mark.parametrize(
    "mutation",
    [
        "wrong_i_review",
        "wrong_a_review",
        "wrong_n_review",
        "wrong_authorization",
        "wrong_core",
        "wrong_closure",
        "failed_audit",
        "author_is_auditor",
        "wrong_audit_render",
        "wrong_bundle",
        "fake_terminal_capture",
        "forged_frozen_receipt",
        "wrong_main",
        "wrong_loaded_origin",
        "wrong_reference_sha",
        "startup_manifest_unclosed",
        "startup_sealed_bytes_unbound",
        "startup_prefix_bytes_unbound",
    ],
)
def test_full_synthetic_mutations_block_before_intent_or_post(
    ns, monkeypatch, tmp_path, mutation
):
    fixture = build_publication_fixture(ns, monkeypatch, tmp_path, mutation)
    with pytest.raises(ns["AuthorizationError"]):
        ns["verify_notification_publication"](fixture.root, api=fixture.api)
    assert all(method == "GET" for method, _url, _kwargs in fixture.session.calls)
    assert not (fixture.root / "evidence/research_notifications").exists()
    assert not ns["_NOTIFICATION_STATES"] and not ns["_NOTIFICATION_FACTS"]


@pytest.mark.parametrize("reference", ["r13_seal_reference", "r13_config_reference"])
def test_full_graph_accepts_exact_r13_source_authority_even_in_runtime_closure(
    ns, monkeypatch, tmp_path, reference
):
    fixture = build_publication_fixture(ns, monkeypatch, tmp_path, reference)
    facts = ns["verify_notification_publication"](fixture.root, api=fixture.api)
    try:
        proof = ns["_notification_facts"](facts)["proof"]
        assert proof["publication"] == fixture.publication
        assert proof["publication_committer_time"] == "2026-09-13T00:00:00Z"
    finally:
        ns["_close_notification_facts"](facts)


# Startup metadata/byte-binding regression author: /root/v13_attempt_draft.
# Actual session: v13-attempt-startup-binding-fix-20260913.
# Inputs below come solely from the manually constructed synthetic graph.
def _startup_publication_fixture_inputs(ns, fixture):
    git = ns["GitRepository"](fixture.root)
    seal = json.loads(git.read_blob(ns["R13"], ns["REGISTRATION_PATH"]))
    operation = seal["operational_contract"]
    paths = operation["claim_ledger_publication"]["worker_outputs"]
    return {
        "git": git,
        "operation": operation,
        "execution": fixture.execution,
        "raw": git.read_blob(fixture.worker, paths["startup"]),
        "manifest": json.loads(git.read_blob(fixture.worker, paths["manifest"])),
        "claim": json.loads(git.read_blob(fixture.worker, paths["claim"])),
        "claim_raw": git.read_blob(fixture.worker, paths["claim"]),
        "events": [
            json.loads(line)
            for line in git.read_blob(fixture.worker, paths["ledger"]).splitlines()
        ],
    }


def _startup_metadata_validate(ns, data):
    ns["_notification_startup_metadata"](
        data["git"],
        data["raw"],
        data["manifest"],
        data["claim"],
        data["claim_raw"],
        data["events"],
        data["execution"],
        data["operation"],
    )


def _startup_metadata_copy(data):
    # Git itself remains the read-only synthetic repository adapter; do not copy
    # any descriptors, transport, capability or real source repository state.
    return {
        key: value if key == "git" else copy.deepcopy(value)
        for key, value in data.items()
    }


def _startup_metadata_rebind_bytes(ns, data, startup_events):
    """Recompute all acyclic receipts, so mutation tests exceed hash-chain checks."""
    lines = []
    for sequence, value in enumerate(startup_events):
        value["sequence"] = sequence
        value["previous_event_sha256"] = sha(lines[-1]) if lines else None
        lines.append(canonical(value) + b"\n")
    if len(lines) >= 10:
        checkpoint = {
            "path": data["operation"]["startup"]["path"],
            "sequence": 9,
            "head_sha256": sha(lines[9]),
            "prefix_byte_count": sum(map(len, lines[:10])),
            "prefix_sha256": sha(b"".join(lines[:10])),
        }
        data["manifest"]["startup_checkpoint"] = copy.deepcopy(checkpoint)
        data["claim"]["bindings"]["startup_checkpoint"] = copy.deepcopy(checkpoint)
        data["claim_raw"] = canonical(data["claim"]) + b"\n"
        first = data["events"][0]
        first["bindings"] = copy.deepcopy(data["claim"]["bindings"])
        first["payload"]["startup_checkpoint"] = copy.deepcopy(checkpoint)
        first["payload"]["claim_sha256"] = sha(data["claim_raw"])
        first["event_sha256"] = sha(
            canonical(
                {key: value for key, value in first.items() if key != "event_sha256"}
            )
        )
        if len(startup_events) > 10:
            startup_events[10]["payload"] = {"claim_sha256": sha(data["claim_raw"])}
        if len(startup_events) > 11:
            startup_events[11]["payload"] = {
                "first_event_sha256": first["event_sha256"]
            }
    lines = []
    for value in startup_events:
        value["previous_event_sha256"] = sha(lines[-1]) if lines else None
        lines.append(canonical(value) + b"\n")
    data["raw"] = b"".join(lines)
    data["manifest"]["sealed_startup"] = {
        "path": data["operation"]["startup"]["path"],
        "bytes": len(data["raw"]),
        "sha256": sha(data["raw"]),
    }


def test_notification_startup_closed_nested_metadata_and_actual_prefix(
    ns, monkeypatch, tmp_path
):
    fixture = build_publication_fixture(ns, monkeypatch, tmp_path)
    original = _startup_publication_fixture_inputs(ns, fixture)
    _startup_metadata_validate(ns, original)
    cases = [
        ("sealed_startup", "path", "synthetic-foreign-startup.jsonl"),
        ("sealed_startup", "bytes", True),
        ("sealed_startup", "bytes", -1),
        ("sealed_startup", "bytes", len(original["raw"]) + 1),
        ("sealed_startup", "sha256", "a" * 64),
        ("sealed_startup", "unknown", True),
        ("startup_checkpoint", "path", "synthetic-foreign-prefix.jsonl"),
        ("startup_checkpoint", "sequence", True),
        ("startup_checkpoint", "sequence", 9.0),
        ("startup_checkpoint", "sequence", 10),
        ("startup_checkpoint", "prefix_byte_count", True),
        ("startup_checkpoint", "prefix_byte_count", 0),
        ("startup_checkpoint", "prefix_byte_count", len(original["raw"])),
        ("startup_checkpoint", "head_sha256", "A" * 64),
        ("startup_checkpoint", "head_sha256", "a" * 64),
        ("startup_checkpoint", "prefix_sha256", "a" * 64),
        ("startup_checkpoint", "unknown", True),
    ]
    for container, field, value in cases:
        data = _startup_metadata_copy(original)
        data["manifest"][container][field] = value
        with pytest.raises(ns["AuthorizationError"]):
            _startup_metadata_validate(ns, data)
    for container in ("sealed_startup", "startup_checkpoint"):
        for invalid in (None, "invalid type", [], {"unexpected": True}):
            data = _startup_metadata_copy(original)
            data["manifest"][container] = invalid
            with pytest.raises(ns["AuthorizationError"]):
                _startup_metadata_validate(ns, data)
        for field in original["manifest"][container]:
            data = _startup_metadata_copy(original)
            del data["manifest"][container][field]
            with pytest.raises(ns["AuthorizationError"]):
                _startup_metadata_validate(ns, data)
    for stream in ("claim", "first_ledger"):
        data = _startup_metadata_copy(original)
        checkpoint = (
            data["claim"]["bindings"]
            if stream == "claim"
            else data["events"][0]["payload"]
        )["startup_checkpoint"]
        checkpoint["prefix_sha256"] = "d" * 64
        with pytest.raises(ns["AuthorizationError"]):
            _startup_metadata_validate(ns, data)
    assert not fixture.session.calls


def test_notification_startup_rehashed_phase_and_byte_tampering_is_rejected(
    ns, monkeypatch, tmp_path
):
    fixture = build_publication_fixture(ns, monkeypatch, tmp_path)
    original = _startup_publication_fixture_inputs(ns, fixture)
    phases = [json.loads(line) for line in original["raw"].splitlines()]
    for sequence in range(13):
        data = _startup_metadata_copy(original)
        changed = copy.deepcopy(phases)
        changed[sequence]["payload"]["unregistered_extra"] = True
        _startup_metadata_rebind_bytes(ns, data, changed)
        # Post-checkpoint rebinding sets these two known receipt objects afresh.
        # Add the unregistered field afterwards, then rehash only the full stream.
        if sequence in {10, 11}:
            changed[sequence]["payload"]["unregistered_extra"] = True
            lines = []
            for event in changed:
                event["previous_event_sha256"] = sha(lines[-1]) if lines else None
                lines.append(canonical(event) + b"\n")
            data["raw"] = b"".join(lines)
            data["manifest"]["sealed_startup"].update(
                bytes=len(data["raw"]), sha256=sha(data["raw"])
            )
        with pytest.raises(ns["AuthorizationError"]):
            _startup_metadata_validate(ns, data)
    mutations = [
        (
            0,
            "startup_identity",
            {
                **phases[0]["payload"]["startup_identity"],
                "authorization_base": "a" * 40,
            },
        ),
        (0, "repository", "synthetic/foreign"),
        (0, "branch", "synthetic-other"),
        (2, "http_status", "404"),
        (3, "request_body_sha256", "a" * 64),
        (3, "request_body_bytes", True),
        (3, "nonce_hex", "2" * 64),
        (3, "raw_commit_sha256", "a" * 64),
        (4, "http_status", 200),
        (4, "result_enum", "transport_failed"),
        (5, "validated_oid", "a" * 40),
        (6, "phase_enum", "lease_commit"),
        (6, "request_body_sha256", "a" * 64),
        (7, "validated_oid", "a" * 40),
        (8, "validated_oid", "a" * 40),
    ]
    for sequence, field, value in mutations:
        data = _startup_metadata_copy(original)
        changed = copy.deepcopy(phases)
        changed[sequence]["payload"][field] = value
        _startup_metadata_rebind_bytes(ns, data, changed)
        with pytest.raises(ns["AuthorizationError"]):
            _startup_metadata_validate(ns, data)
    for label in (
        "truncated",
        "appended",
        "reordered",
        "backward_clock",
        "duplicate_kind",
    ):
        data = _startup_metadata_copy(original)
        changed = copy.deepcopy(phases)
        if label == "truncated":
            changed = changed[:10]
        elif label == "appended":
            changed.append(copy.deepcopy(changed[-1]))
        elif label == "reordered":
            changed[4], changed[5] = changed[5], changed[4]
        elif label == "backward_clock":
            changed[1]["generated_at"] = "2026-09-12T23:59:59Z"
        else:
            changed[4]["kind"] = changed[3]["kind"]
        _startup_metadata_rebind_bytes(ns, data, changed)
        with pytest.raises(ns["AuthorizationError"]):
            _startup_metadata_validate(ns, data)
    for raw in (
        original["raw"][:-1],
        b"not a startup journal\n",
        original["raw"] + b"\n",
    ):
        data = _startup_metadata_copy(original)
        data["raw"] = raw
        data["manifest"]["sealed_startup"].update(bytes=len(raw), sha256=sha(raw))
        with pytest.raises(ns["AuthorizationError"]):
            _startup_metadata_validate(ns, data)
    assert not fixture.session.calls


def test_notification_startup_receipts_and_cross_stream_clocks_bind_actual_bytes(
    ns, monkeypatch, tmp_path
):
    fixture = build_publication_fixture(ns, monkeypatch, tmp_path)
    original = _startup_publication_fixture_inputs(ns, fixture)
    for mutation in (
        "claim_receipt",
        "first_event_receipt",
        "claim_facts_extra",
        "bindings_extra",
        "claim_clock_before",
        "ledger_clock_before",
        "forecast_before_history_intent",
    ):
        data = _startup_metadata_copy(original)
        if mutation == "claim_receipt":
            data["events"][0]["payload"]["claim_sha256"] = "a" * 64
        elif mutation == "first_event_receipt":
            data["events"][0]["event_sha256"] = "a" * 64
        elif mutation == "claim_facts_extra":
            data["claim"]["verified_authorization_facts"]["extra"] = True
        elif mutation == "bindings_extra":
            data["claim"]["bindings"]["extra"] = True
        elif mutation == "claim_clock_before":
            data["claim"]["claimed_at"] = "2026-09-12T23:59:59Z"
        elif mutation == "ledger_clock_before":
            data["events"][0]["recorded_at"] = "2026-09-12T23:59:59Z"
        else:
            data["events"][1]["recorded_at"] = "2026-09-12T23:59:59Z"
        with pytest.raises(ns["AuthorizationError"]):
            _startup_metadata_validate(ns, data)
    assert not fixture.session.calls


# Precredential synthetic checks authored by /root,
# root-v13-implementation-integration-20260913.
@pytest.fixture
def _pc_ns(attempt):
    return attempt.main.__globals__


def _pc_inputs(ns, monkeypatch, tmp_path, *, failure=None):
    calls = []
    operation = json.loads((ROOT / ns["REGISTRATION_PATH"]).read_bytes())[
        "operational_contract"
    ]
    runtime = copy.deepcopy(operation["runtime_closure"]["exact_runtime"])
    manifest = [{"path": "synthetic-only.py", "bytes": 1, "sha256": "a" * 64}]
    closure = [{"path": "synthetic-only.py", "sha256": "b" * 64}]
    keys = operation["authorization"]["authorization_schema"]["required_keys"]
    authorization = dict.fromkeys(keys)
    authorization.update(
        runtime=copy.deepcopy(runtime),
        pure_core_sha256="c" * 64,
        implementation_files=copy.deepcopy(manifest),
        implementation_files_sha256=ns["_sha"](ns["_canonical"](manifest)),
        runtime_dependency_closure=copy.deepcopy(closure),
        runtime_dependency_closure_sha256=ns["_sha"](ns["_canonical"](closure)),
    )
    if failure == "authorization_runtime":
        authorization["runtime"]["python_version"] = "0.0.0"
    elif failure == "manifest":
        authorization["implementation_files"] = []
    elif failure == "manifest_digest":
        authorization["implementation_files_sha256"] = "d" * 64
    elif failure == "core_type":
        authorization["pure_core_sha256"] = None
    elif failure == "closure":
        authorization["runtime_dependency_closure"] = []
    elif failure == "closure_digest":
        authorization["runtime_dependency_closure_sha256"] = "e" * 64
    elif failure == "unknown_auth_key":
        authorization["unknown"] = True
    raw = ns["_canonical"](authorization) + b"\n"
    if failure == "noncanonical":
        raw += b"\n"

    class LocalGit:
        def __init__(self, root):
            assert root == tmp_path

        def require_full_clean(self):
            calls.append("clean")
            if failure == "dirty":
                raise ns["AuthorizationError"]("synthetic dirty source")

        def head(self):
            calls.append("head")
            return (
                "2" if failure == "head_moved" and calls.count("head") > 1 else "1"
            ) * 40

        def read_blob(self, head, path):
            assert head == "1" * 40 and path == ns["AUTHORIZATION_PATH"]
            calls.append("authorization_bytes")
            if failure == "missing_auth":
                raise ns["AuthorizationError"]("synthetic missing auth")
            return raw

    def registered(git, head):
        assert isinstance(git, LocalGit) and head == "1" * 40
        calls.append("registered_source")
        if failure == "registration":
            raise ns["AuthorizationError"]("synthetic registration failure")
        return {}, operation

    def runtime_observation():
        calls.append("runtime")
        if failure == "runtime_rejected":
            raise ns["AuthorizationError"]("synthetic observed runtime rejected")
        result = copy.deepcopy(runtime)
        if failure == "runtime_contract":
            result["machine"] = "synthetic-mismatch"
        return result

    def manifest_observation(git, head):
        assert isinstance(git, LocalGit) and head == "1" * 40
        calls.append("manifest")
        return manifest

    def core_observation(git, head, *, required_core_sha256):
        assert isinstance(git, LocalGit) and head == "1" * 40
        assert required_core_sha256 == "c" * 64
        calls.append("bound_core_closure")
        if failure == "core_rejected":
            raise ns["AuthorizationError"]("synthetic core mismatch")
        return closure

    def worktree_observation(git, head, observed_closure):
        assert isinstance(git, LocalGit) and head == "1" * 40
        assert observed_closure is closure
        calls.append("worktree_loaded_source")
        if failure == "loaded_source":
            raise ns["AuthorizationError"]("synthetic changed loaded source")

    def forbidden(*args, **kwargs):
        raise AssertionError(
            "Local precredential check must not create remote or execution capabilities"
        )

    substitutions = {
        "GitRepository": LocalGit,
        "_registered_authorities": registered,
        "runtime_identity": runtime_observation,
        "_implementation_manifest": manifest_observation,
        "_core_and_closure": core_observation,
        "_verify_worktree_runtime": worktree_observation,
        "FixedGitHubApi": forbidden,
        "_NotificationHTTP": forbidden,
        "verify_authorization": forbidden,
        "begin_authorized_startup": forbidden,
        "acquire_historical_lease": forbidden,
        "_run_canonical": forbidden,
        "verify_notification_publication": forbidden,
        "_prepare_production_notification": forbidden,
    }
    for name, value in substitutions.items():
        monkeypatch.setitem(ns, name, value)
    return calls


def test_precredential_check_binds_local_metadata_without_issuing_any_capability(
    _pc_ns, monkeypatch, tmp_path
):
    calls = _pc_inputs(_pc_ns, monkeypatch, tmp_path)
    assert _pc_ns["_precredential_local_runtime"](tmp_path) is None
    assert calls == [
        "clean",
        "head",
        "registered_source",
        "runtime",
        "authorization_bytes",
        "manifest",
        "bound_core_closure",
        "worktree_loaded_source",
        "clean",
        "head",
    ]


@pytest.mark.parametrize(
    "failure",
    [
        "dirty",
        "registration",
        "runtime_rejected",
        "runtime_contract",
        "missing_auth",
        "authorization_runtime",
        "manifest",
        "manifest_digest",
        "core_type",
        "core_rejected",
        "closure",
        "closure_digest",
        "unknown_auth_key",
        "noncanonical",
        "loaded_source",
        "head_moved",
    ],
)
def test_precredential_local_failures_cannot_construct_transport_or_execution(
    _pc_ns, monkeypatch, tmp_path, failure
):
    _pc_inputs(_pc_ns, monkeypatch, tmp_path, failure=failure)
    with pytest.raises(_pc_ns["AuthorizationError"]):
        _pc_ns["_precredential_local_runtime"](tmp_path)


@pytest.mark.parametrize(
    "entry,adapter",
    [("main", "FixedGitHubApi"), ("notify_audited_capture", "_NotificationHTTP")],
)
def test_production_entries_require_local_verification_before_token_expression(
    entry, adapter
):
    tree = ast.parse((ROOT / "src/lotto649/v13_registered_attempt.py").read_text())
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == entry
    )
    calls = [node for node in ast.walk(function) if isinstance(node, ast.Call)]
    preflight = [
        node
        for node in calls
        if isinstance(node.func, ast.Name)
        and node.func.id == "_precredential_local_runtime"
    ]
    transport = [
        node
        for node in calls
        if isinstance(node.func, ast.Name) and node.func.id == adapter
    ]
    assert len(preflight) == len(transport) == 1
    assert preflight[0].lineno < transport[0].lineno
    assert (
        isinstance(preflight[0].args[0], ast.Name)
        and preflight[0].args[0].id == "repository"
    )
    token_reads = [
        node
        for node in calls
        if isinstance(node.func, ast.Attribute)
        and node.func.attr == "get"
        and node.args
        and isinstance(node.args[0], ast.Constant)
        and node.args[0].value == "GH_TOKEN"
    ]
    assert len(token_reads) == 1
    assert token_reads[0].lineno >= transport[0].lineno > preflight[0].lineno


@pytest.mark.parametrize(
    "qualified",
    [
        "_notification_checkpoint_metadata",
        "_notification_startup_metadata",
        "_notification_capture_artifacts",
        "_notification_ledger_metadata",
        "_precredential_local_runtime",
    ],
)
@pytest.mark.parametrize("change", ["mutation", "duplicate", "move"])
def test_startup_publication_byte_validators_and_precredential_helper_are_sealed(
    attempt, qualified, change
):
    tree = ast.parse((ROOT / attempt.ATTEMPT_PATH).read_text())
    node = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == qualified
    )
    if change == "mutation":
        node.body.append(ast.Pass())
    elif change == "duplicate":
        tree.body.append(copy.deepcopy(node))
    else:
        tree.body.remove(node)
        wrapper = ast.parse("class SyntheticMovedBoundary:\n    pass\n").body[0]
        wrapper.body = [node]
        tree.body.append(wrapper)
    with pytest.raises(attempt.AuthorizationError):
        attempt._check_source_safety(attempt.ATTEMPT_PATH, tree)


# Historical transport purpose regression author: /root/v13_notification_production_draft.
# Actual session: v13-historical-transport-purpose-fix-authoring-20260913.
@pytest.fixture
def _ht_ns(attempt, monkeypatch):
    namespace = attempt.acquire_historical_lease.__globals__
    monkeypatch.setitem(namespace, "_HISTORICAL_TRANSPORTS", {})
    monkeypatch.setitem(namespace, "_HISTORICAL_TRANSPORT_OWNERS", [])
    # Existing tests use synthetic inert facts in the same imported module.
    # Isolate this fixture's empty issuance domain, restoring all prior state
    # afterwards; no real issuance/authority function is replaced by this reset.
    for registry in ("_ISSUED_AUTHORITIES", "_ISSUED_LEASES", "_VERIFIED_FACTS"):
        monkeypatch.setitem(namespace, registry, [])
    return namespace


class _HTResponse:
    def __init__(self, value, status=200, *, raw=None):
        self.value = value
        self.status_code = status
        self.url = None
        self.headers = {"Content-Type": "application/json"}
        self.raw = raw

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def iter_content(self, _size):
        yield self.raw if self.raw is not None else json.dumps(self.value).encode()


class _HTSession:
    def __init__(self):
        self.headers = {}
        self.calls = []
        self.routes = {}
        self.trust_env = None
        self.hook = None

    def mount(self, *_args):
        pass

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        if self.hook is not None:
            self.hook(method, url, kwargs)
        response = self.routes[(method, url)]
        if isinstance(response, BaseException):
            raise response
        response.url = url
        return response


@pytest.fixture
def _ht_fixture(_ht_ns, monkeypatch, tmp_path):
    import requests

    sessions = []

    def factory():
        session = _HTSession()
        sessions.append(session)
        return session

    monkeypatch.setattr(requests, "Session", factory)
    api = _ht_ns["FixedGitHubApi"]("synthetic-fixture-not-a-credential")
    session = sessions[0]
    projection = json.loads(
        (ROOT / "tests/fixtures/v13_git_commit_projection.json").read_bytes()
    )
    prefix = _ht_ns["_API_ORIGIN"] + _ht_ns["_API_PREFIX"]
    lease_path = prefix + "/git/ref/heads/v13-consumption-v13.0.0"
    session.routes.update(
        {
            ("GET", prefix): _HTResponse(
                {
                    "node_id": _ht_ns["REPOSITORY_NODE_ID"],
                    "full_name": _ht_ns["REPOSITORY"],
                    "default_branch": "main",
                    "private": False,
                }
            ),
            ("GET", prefix + "/hash-algorithm"): _HTResponse(
                {"hash_algorithm": "sha1"}
            ),
            ("GET", prefix + "/branches/main/protection"): _HTResponse(
                {
                    "enforce_admins": {"enabled": True},
                    "allow_force_pushes": {"enabled": False},
                    "allow_deletions": {"enabled": False},
                }
            ),
            ("GET", prefix + "/git/ref/heads/main"): _HTResponse(
                {
                    "ref": "refs/heads/main",
                    "object": {"type": "commit", "sha": "6" * 40},
                }
            ),
            ("GET", lease_path): _HTResponse({"message": "Not Found"}, 404),
            ("POST", prefix + "/git/commits"): _HTResponse(
                projection["post_commit_response"], 201
            ),
            ("POST", prefix + "/git/refs"): _HTResponse(
                projection["post_ref_response"], 201
            ),
            (
                "GET",
                prefix + "/git/commits/" + projection["post_commit_response"]["sha"],
            ): _HTResponse(projection["get_commit_response"]),
        }
    )
    journal = _ht_ns["StartupJournal"].for_synthetic(
        tmp_path / "synthetic-startup", {"synthetic_fixture_only": True}
    )
    journal.append("capability_issued", {})
    authority = SimpleNamespace(
        repository=tmp_path,
        execution_commit="6" * 40,
        authorization_sha256="a" * 64,
        startup=journal,
        facts=object(),
    )
    consumed = []
    stamp = {"raw": b"synthetic-authority-input-only"}
    issued = []

    def require(candidate, *, consume=False):
        if candidate is not authority:
            raise _ht_ns["AuthorizationError"]("synthetic authority identity differs")
        journal.verify_owned()
        if consume:
            if consumed:
                raise _ht_ns["AuthorizationError"]("synthetic already consumed")
            consumed.append(candidate)

    def context(candidate):
        require(candidate)
        if not consumed:
            raise _ht_ns["AuthorizationError"]("synthetic authority was not consumed")
        return {
            "stamp": stamp["raw"],
            "facts": authority.facts,
            "startup": authority.startup,
        }

    class Git:
        def __init__(self, root):
            assert root == tmp_path

        def require_full_clean(self, **kwargs):
            assert not kwargs or kwargs == {"authority": authority}

        def head(self):
            return "6" * 40

        def tree(self, oid):
            assert oid == "6" * 40
            return "b" * 40

        def run(self, *args):
            assert args == ("cat-file", "commit", "6" * 40)
            return (
                b"tree "
                + b"b" * 40
                + b"\ncommitter Synthetic <synthetic@example.invalid> 1700000000 +0000\n\nSynthetic source metadata\n"
            )

    def lease_result(candidate, oid, nonce):
        assert candidate is authority
        issued.append((candidate, oid, nonce))
        return "synthetic-result-with-no-capability"

    # Exactly two upstream authority seams are injected. No production facts,
    # execution authority or Lease object is constructed or inserted in registries.
    monkeypatch.setitem(_ht_ns, "_require_authorization_capability", require)
    monkeypatch.setitem(_ht_ns, "_historical_authority_context", context)
    monkeypatch.setitem(_ht_ns, "GitRepository", Git)
    monkeypatch.setitem(_ht_ns, "_issue_lease", lease_result)
    monkeypatch.setitem(
        _ht_ns,
        "secrets",
        SimpleNamespace(token_hex=lambda count: "d" * 64 if count == 32 else None),
    )
    value = SimpleNamespace(
        api=api,
        session=session,
        sessions=sessions,
        projection=projection,
        prefix=prefix,
        lease_path=lease_path,
        journal=journal,
        authority=authority,
        consumed=consumed,
        stamp=stamp,
        issued=issued,
        require=require,
    )
    yield value
    journal.close()


def _ht_bind(_ht_ns, f):
    f.require(f.authority, consume=True)
    _ht_ns["_bind_historical_transport"](f.api, f.authority)


def _ht_plan(_ht_ns, f):
    _ht_bind(_ht_ns, f)
    assert (
        f.api.request_json(
            "GET",
            _ht_ns["_API_PREFIX"] + "/git/ref/heads/v13-consumption-v13.0.0",
            allow_absent=True,
        )
        is None
    )
    f.journal.append("lease_absence_confirmed", {"http_status": 404})
    return _ht_ns["_plan_historical_transport"](f.api, f.authority, "d" * 64)


def _ht_commit_intent(_ht_ns, f):
    oid, raw, payload = _ht_plan(_ht_ns, f)
    body = _ht_ns["_canonical"](payload)
    f.journal.intent("lease_commit", "d" * 64, oid, _ht_ns["_sha"](raw), body)
    return oid, raw, payload, body


def _ht_advance_commit(_ht_ns, f):
    oid, raw, payload = _ht_plan(_ht_ns, f)
    _ht_ns["_post_lease_request"](
        f.api,
        f.journal,
        phase="lease_commit",
        nonce="d" * 64,
        oid=oid,
        raw_sha256=_ht_ns["_sha"](raw),
        request_bytes=_ht_ns["_canonical"](payload),
        commit_payload=payload,
    )
    f.api.request_json("GET", _ht_ns["_API_PREFIX"] + "/git/commits/" + oid)
    f.journal.append("lease_commit_GET_verified", {"validated_oid": oid})
    return oid, raw, payload


def _ht_posts(f):
    return [call for call in f.session.calls if call[0] == "POST"]


@pytest.mark.parametrize(
    "role,route",
    [("post_commit_request", "/git/commits"), ("post_ref_request", "/git/refs")],
)
def test_default_transport_rejects_even_exact_registered_post(
    _ht_ns, _ht_fixture, role, route
):
    f = _ht_fixture
    with pytest.raises(_ht_ns["AuthorizationError"], match="read-only"):
        f.api.request_json(
            "POST",
            _ht_ns["_API_PREFIX"] + route,
            body_bytes=_ht_ns["_canonical"](f.projection[role]),
        )
    assert f.session.calls == []
    with pytest.raises(_ht_ns["AuthorizationError"]):
        f.api.request_json("GET", _ht_ns["_API_PREFIX"])
    assert f.session.calls == []


def test_unissued_authority_cannot_bind_real_context(_ht_ns, monkeypatch):
    import requests

    monkeypatch.setattr(requests, "Session", _HTSession)
    api = _ht_ns["FixedGitHubApi"]("synthetic")
    with pytest.raises((_ht_ns["AuthorizationError"], AttributeError)):
        _ht_ns["_bind_historical_transport"](api, object())
    assert api._terminal
    assert _ht_ns["_HISTORICAL_TRANSPORT_OWNERS"] == []


def test_constructor_cannot_reset_or_subclass_transport(_ht_ns, _ht_fixture):
    f = _ht_fixture
    with pytest.raises(_ht_ns["AuthorizationError"]):
        f.api.__init__("synthetic-reinitialize")
    assert len(f.sessions) == 1
    assert f.api._terminal

    class Foreign(_ht_ns["FixedGitHubApi"]):
        pass

    with pytest.raises(_ht_ns["AuthorizationError"]):
        Foreign("synthetic")
    assert len(f.sessions) == 1


@pytest.mark.parametrize(
    "change",
    [
        "same_api",
        "new_api",
        "foreign_authority",
        "changed_facts",
        "changed_stamp",
        "changed_startup",
        "session",
        "flags",
        "status",
    ],
)
def test_purpose_and_original_binding_never_reset(_ht_ns, _ht_fixture, change):
    f = _ht_fixture
    _ht_bind(_ht_ns, f)
    target = f.api
    if change == "new_api":
        target = _ht_ns["FixedGitHubApi"]("another-synthetic")
    if change in {"same_api", "new_api", "foreign_authority"}:
        with pytest.raises(_ht_ns["AuthorizationError"]):
            _ht_ns["_bind_historical_transport"](
                target, object() if change == "foreign_authority" else f.authority
            )
    else:
        if change == "changed_facts":
            f.authority.facts = object()
        elif change == "changed_stamp":
            f.stamp["raw"] = b"changed"
        elif change == "changed_startup":
            f.authority.startup = object()
        elif change == "session":
            f.api._session = _HTSession()
        elif change == "flags":
            f.api._commit_post_attempted = True
        else:
            f.api._last_status = 404
        with pytest.raises(_ht_ns["AuthorizationError"]):
            f.api.request_json("GET", _ht_ns["_API_PREFIX"])
    assert _ht_posts(f) == []


@pytest.mark.parametrize(
    "change",
    ["no404", "old404", "notfound200", "malformed404", "timeout404", "repeat404"],
)
def test_fresh_exact_absence_required_once(_ht_ns, _ht_fixture, change):
    f = _ht_fixture
    if change == "old404":
        f.api.request_json(
            "GET",
            _ht_ns["_API_PREFIX"] + "/git/ref/heads/v13-consumption-v13.0.0",
            allow_absent=True,
        )
    _ht_bind(_ht_ns, f)
    if change in {"no404", "old404"}:
        with pytest.raises(_ht_ns["AuthorizationError"]):
            _ht_ns["_plan_historical_transport"](f.api, f.authority, "d" * 64)
    else:
        if change == "notfound200":
            f.session.routes[("GET", f.lease_path)] = _HTResponse(
                {"message": "Not Found"}, 200
            )
        elif change == "malformed404":
            f.session.routes[("GET", f.lease_path)] = _HTResponse(
                {"message": "wrong"}, 404
            )
        elif change == "timeout404":
            f.session.routes[("GET", f.lease_path)] = OSError(
                "synthetic-private-do-not-expose"
            )
        if change == "repeat404":
            f.api.request_json(
                "GET",
                _ht_ns["_API_PREFIX"] + "/git/ref/heads/v13-consumption-v13.0.0",
                allow_absent=True,
            )
        with pytest.raises(_ht_ns["AuthorizationError"]) as caught:
            f.api.request_json(
                "GET",
                _ht_ns["_API_PREFIX"] + "/git/ref/heads/v13-consumption-v13.0.0",
                allow_absent=True,
            )
        assert "synthetic-private" not in str(caught.value)
    assert _ht_posts(f) == []


@pytest.mark.parametrize(
    "change",
    [
        "no_intent",
        "changed_body",
        "notification_ref",
        "early_ref",
        "early_commit_get",
        "durable_bytes",
        "planned_bytes",
        "unowned_intent",
        "duplicate_intent",
    ],
)
def test_durable_exact_intent_and_protocol_order_gate_post(
    _ht_ns, _ht_fixture, change, tmp_path
):
    f = _ht_fixture
    oid, raw, payload = _ht_plan(_ht_ns, f)
    body = _ht_ns["_canonical"](payload)
    if change not in {"no_intent", "early_ref", "early_commit_get"}:
        f.journal.intent("lease_commit", "d" * 64, oid, _ht_ns["_sha"](raw), body)
    if change == "changed_body":
        payload = copy.deepcopy(payload)
        payload["tree"] = "c" * 40
        body = _ht_ns["_canonical"](payload)
    elif change == "durable_bytes":
        with f.journal.path.open("ab") as stream:
            stream.write(b"foreign")
    elif change == "planned_bytes":
        _ht_ns["_HISTORICAL_TRANSPORTS"][f.api]["plan"]["ref_bytes"] = b"{}"
    elif change == "unowned_intent":
        original = f.journal.path.read_bytes()
        f.journal.path.unlink()
        f.journal.path.write_bytes(original)
    elif change == "duplicate_intent":
        with pytest.raises(_ht_ns["AttemptError"]):
            f.journal.intent("lease_commit", "d" * 64, oid, _ht_ns["_sha"](raw), body)
    route = "/git/commits"
    if change in {"notification_ref", "early_ref"}:
        route = "/git/refs"
        body = _ht_ns["_canonical"](
            {
                "ref": "refs/heads/v13-notification-v13.0.0"
                if change == "notification_ref"
                else _ht_ns["LEASE_REF"],
                "sha": oid,
            }
        )
    with pytest.raises((_ht_ns["AuthorizationError"], _ht_ns["AttemptError"])):
        if change == "early_commit_get":
            f.api.request_json("GET", _ht_ns["_API_PREFIX"] + "/git/commits/" + oid)
        else:
            f.api.request_json("POST", _ht_ns["_API_PREFIX"] + route, body_bytes=body)
    assert _ht_posts(f) == []


@pytest.mark.parametrize("phase", ["commit", "ref"])
@pytest.mark.parametrize(
    "failure", ["timeout", "bad201", "rejected", "duplicate", "reentrant"]
)
def test_started_slots_are_terminal_on_failure_or_repeat(
    _ht_ns, _ht_fixture, phase, failure
):
    f = _ht_fixture
    if phase == "commit":
        oid, raw, _payload, body = _ht_commit_intent(_ht_ns, f)
        route = "/git/commits"
    else:
        oid, raw, _payload = _ht_advance_commit(_ht_ns, f)
        body = _ht_ns["_canonical"]({"ref": _ht_ns["LEASE_REF"], "sha": oid})
        f.journal.intent("lease_ref", "d" * 64, oid, _ht_ns["_sha"](raw), body)
        route = "/git/refs"
    key = ("POST", f.prefix + route)
    if failure == "timeout":
        f.session.routes[key] = OSError("synthetic-private-do-not-expose")
    elif failure == "bad201":
        f.session.routes[key] = _HTResponse({"sha": "f" * 40}, 201)
    elif failure == "rejected":
        f.session.routes[key] = _HTResponse({"message": "synthetic"}, 403)
    elif failure == "reentrant":

        def reenter(method, _url, _kwargs):
            if method == "POST":
                f.api.request_json(
                    "POST", _ht_ns["_API_PREFIX"] + route, body_bytes=body
                )

        f.session.hook = reenter
    before = len(_ht_posts(f))
    if failure == "duplicate":
        f.api.request_json("POST", _ht_ns["_API_PREFIX"] + route, body_bytes=body)
    else:
        with pytest.raises(_ht_ns["AuthorizationError"]) as caught:
            f.api.request_json("POST", _ht_ns["_API_PREFIX"] + route, body_bytes=body)
        assert "synthetic-private" not in str(caught.value)
    with pytest.raises(_ht_ns["AuthorizationError"]):
        f.api.request_json("POST", _ht_ns["_API_PREFIX"] + route, body_bytes=body)
    assert len(_ht_posts(f)) == before + 1
    new = _ht_ns["FixedGitHubApi"]("synthetic-new-instance")
    with pytest.raises(_ht_ns["AuthorizationError"]):
        _ht_ns["_bind_historical_transport"](new, f.authority)


def test_entire_acquire_protocol_uses_real_transport_and_durable_startup(
    _ht_ns, _ht_fixture
):
    f = _ht_fixture

    def switch_after_ref(method, url, _kwargs):
        if method == "POST" and url.endswith("/git/refs"):
            f.session.routes[("GET", f.lease_path)] = _HTResponse(
                f.projection["post_ref_response"]
            )

    f.session.hook = switch_after_ref
    assert (
        _ht_ns["acquire_historical_lease"](f.authority, f.api)
        == "synthetic-result-with-no-capability"
    )
    assert len(f.issued) == 1
    assert len(_ht_posts(f)) == 2
    assert _ht_posts(f)[0][2]["data"] == _ht_ns["_canonical"](
        f.projection["post_commit_request"]
    )
    assert _ht_posts(f)[1][2]["data"] == _ht_ns["_canonical"](
        f.projection["post_ref_request"]
    )
    for _method, _url, kwargs in f.session.calls:
        assert kwargs["verify"] is True and kwargs["allow_redirects"] is False
        assert kwargs["timeout"] == (10, 30) and kwargs["proxies"] == {}
    events = [json.loads(line) for line in f.journal.path.read_bytes().splitlines()]
    assert tuple(e["kind"] for e in events) == _ht_ns["_STARTUP_PHASES"][:9]
    f.journal.checkpoint()
    f.journal.append("claim_created", {"claim_sha256": "a" * 64})
    f.journal.append("scientific_ledger_started", {"first_event_sha256": "b" * 64})
    f.journal.append("history_load_intent", {})
    f.journal.seal()
    assert f.journal.sealed
    assert _ht_ns["_HISTORICAL_TRANSPORTS"][f.api]["phase"] == "complete"
    assert (
        not _ht_ns["_ISSUED_AUTHORITIES"]
        and not _ht_ns["_ISSUED_LEASES"]
        and not _ht_ns["_VERIFIED_FACTS"]
    )
    with pytest.raises(_ht_ns["AuthorizationError"]):
        _ht_ns["acquire_historical_lease"](f.authority, f.api)
    assert len(_ht_posts(f)) == 2 and len(f.issued) == 1


@pytest.mark.parametrize(
    "mutation",
    ["forged_receipt", "forged_commit_get", "wrong_commit_get", "failed_commit_get"],
)
def test_manual_receipts_cannot_replace_verified_transport_facts(
    _ht_ns, _ht_fixture, mutation
):
    f = _ht_fixture
    oid, raw, _payload, body = _ht_commit_intent(_ht_ns, f)
    if mutation == "forged_receipt":
        f.journal.receipt("lease_commit", "success", 201, oid)
        with pytest.raises(_ht_ns["AuthorizationError"]):
            f.api.request_json("GET", _ht_ns["_API_PREFIX"] + "/git/commits/" + oid)
        assert _ht_posts(f) == []
        return
    f.api.request_json("POST", _ht_ns["_API_PREFIX"] + "/git/commits", body_bytes=body)
    f.journal.receipt("lease_commit", "success", 201, oid)
    if mutation == "forged_commit_get":
        f.journal.append("lease_commit_GET_verified", {"validated_oid": oid})
        ref = _ht_ns["_canonical"]({"ref": _ht_ns["LEASE_REF"], "sha": oid})
        f.journal.intent("lease_ref", "d" * 64, oid, _ht_ns["_sha"](raw), ref)
        with pytest.raises(_ht_ns["AuthorizationError"]):
            f.api.request_json(
                "POST", _ht_ns["_API_PREFIX"] + "/git/refs", body_bytes=ref
            )
    else:
        path = _ht_ns["_API_PREFIX"] + "/git/commits/" + oid
        if mutation == "wrong_commit_get":
            path = _ht_ns["_API_PREFIX"] + "/git/commits/" + "f" * 40
        else:
            response = copy.deepcopy(f.projection["get_commit_response"])
            response["parents"][0]["sha"] = "f" * 40
            f.session.routes[("GET", f.prefix + "/git/commits/" + oid)] = _HTResponse(
                response
            )
        with pytest.raises(_ht_ns["AuthorizationError"]):
            f.api.request_json("GET", path)
    assert len(_ht_posts(f)) == 1


@pytest.mark.parametrize(
    "route",
    [
        "/git/ref/heads/v13-notification-v13.0.0",
        "/git/refs/heads/v13-consumption-v13.0.0",
    ],
)
def test_cross_purpose_or_unregistered_ref_get_is_terminal(_ht_ns, _ht_fixture, route):
    f = _ht_fixture
    _ht_bind(_ht_ns, f)
    with pytest.raises(_ht_ns["AuthorizationError"]):
        f.api.request_json("GET", _ht_ns["_API_PREFIX"] + route, allow_absent=True)
    with pytest.raises(_ht_ns["AuthorizationError"]):
        f.api.request_json("GET", _ht_ns["_API_PREFIX"])
    assert f.session.calls == []


def test_direct_private_adapter_entry_still_cannot_post_without_purpose(
    _ht_ns, _ht_fixture
):
    f = _ht_fixture
    with pytest.raises(_ht_ns["AuthorizationError"]):
        f.api._request_json_checked(
            "POST",
            _ht_ns["_API_PREFIX"] + "/git/commits",
            body_bytes=_ht_ns["_canonical"](f.projection["post_commit_request"]),
        )
    assert f.session.calls == []
    assert f.api._terminal


@pytest.mark.parametrize("storage", ["untracked", "ignored", "tracked"])
@pytest.mark.parametrize(
    "relative", ["src/ast.py", "src/json.py", "src/json/__init__.py"]
)
def test_launcher_rejects_stdlib_shadow_names_before_source_path_is_exposed(
    launcher, launcher_repository, storage, relative
):
    root = launcher_repository
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    # The canary is never imported. Its presence alone must stop the bootstrap.
    path.write_text("raise AssertionError('synthetic unregistered import executed')\n")
    if storage == "ignored":
        (root / ".gitignore").write_text(relative + "\n")
        _fixture_git(root, "add", ".gitignore")
        _fixture_git(root, "commit", "--quiet", "-m", "synthetic ignore rule")
    elif storage == "tracked":
        _fixture_git(root, "add", relative)
        _fixture_git(root, "commit", "--quiet", "-m", "synthetic committed shadow")
    with pytest.raises(RuntimeError, match="unregistered top-level source"):
        launcher["_verify_initial_sources"](root)


@pytest.mark.parametrize("storage", ["untracked", "ignored"])
@pytest.mark.parametrize(
    "relative", ["src/lotto649/unknown.py", "unowned-artifact.txt"]
)
def test_launcher_requires_clean_complete_tree_including_ignored_files(
    launcher, launcher_repository, storage, relative
):
    root = launcher_repository
    path = root / relative
    path.write_text("synthetic foreign file; not executed\n")
    if storage == "ignored":
        (root / ".gitignore").write_text(relative + "\n")
        _fixture_git(root, "add", ".gitignore")
        _fixture_git(root, "commit", "--quiet", "-m", "synthetic ignored foreign file")
    with pytest.raises(RuntimeError, match="before package imports"):
        launcher["_verify_initial_sources"](root)


def test_launcher_allows_clean_tracked_nonimport_documentation(
    launcher, launcher_repository
):
    (launcher_repository / "README.md").write_text("Synthetic tracked documentation.\n")
    _fixture_git(launcher_repository, "add", "README.md")
    _fixture_git(
        launcher_repository, "commit", "--quiet", "-m", "synthetic documentation"
    )
    launcher["_verify_initial_sources"](launcher_repository)


def test_isolated_bootstrap_stops_shadow_canary_before_path_change_or_import(
    launcher_repository, tmp_path
):
    marker = tmp_path / "synthetic-import-marker"
    # A child has an explicitly fabricated environment and only invokes the
    # source verifier, never main, the attempt module or any authority factory.
    (launcher_repository / "src/ast.py").write_text(
        "from pathlib import Path\n"
        + f"Path({str(marker)!r}).write_text('synthetic canary executed')\n"
    )
    script = (
        "import runpy, sys\nfrom pathlib import Path\n"
        + f"ns = runpy.run_path({str(LAUNCHER)!r}, run_name='synthetic_bootstrap_check')\n"
        + "try:\n"
        + f"    ns['_verify_initial_sources'](Path({str(launcher_repository)!r}))\n"
        + "except RuntimeError:\n    raise SystemExit(42)\n"
        + f"sys.path.insert(0, {str(launcher_repository / 'src')!r})\n"
        + "import ast\nraise SystemExit(99)\n"
    )
    result = subprocess.run(
        [sys.executable, "-I", "-S", "-B", "-c", script],
        env={"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C"},
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 42
    assert not marker.exists()
    assert result.stdout == result.stderr == b""


@pytest.mark.parametrize(
    "key,value",
    [
        ("filter.unregistered.clean", "synthetic-command"),
        ("filter.unregistered.process", "synthetic-command"),
        ("core.fsmonitor", "synthetic-command"),
        ("core.hooksPath", "/synthetic-hooks"),
        ("core.worktree", "/synthetic-worktree"),
        ("include.path", "/synthetic-config"),
        ("includeIf.gitdir:/synthetic/.path", "/synthetic-config"),
        ("diff.external", "synthetic-command"),
    ],
)
def test_launcher_rejects_unregistered_config_before_status(
    launcher, launcher_repository, monkeypatch, key, value
):
    _fixture_git(launcher_repository, "config", "--local", key, value)
    commands = []
    original = launcher["_git"]

    def observed_git(root, *arguments):
        commands.append(arguments)
        return original(root, *arguments)

    monkeypatch.setitem(launcher, "_git", observed_git)
    with pytest.raises(RuntimeError, match="local Git configuration") as caught:
        launcher["_verify_initial_sources"](launcher_repository)
    assert value not in str(caught.value)
    assert commands[0][0] == "config"
    assert not any(command[0] == "status" for command in commands)


def test_launcher_allows_registered_clone_and_branch_config(
    launcher, launcher_repository
):
    for key, value in (
        ("remote.origin.url", "https://github.com/Jasper-Shi/lottopred.git"),
        ("remote.origin.fetch", "+refs/heads/*:refs/remotes/origin/*"),
        ("branch.codex/synthetic.remote", "origin"),
        ("branch.codex/synthetic.merge", "refs/heads/main"),
    ):
        _fixture_git(launcher_repository, "config", "--local", key, value)
    launcher["_verify_initial_sources"](launcher_repository)


def test_launcher_rejects_clean_filter_before_it_can_execute(
    launcher, launcher_repository, tmp_path
):
    root = launcher_repository
    source = root / "synthetic-content.txt"
    source.write_text("before synthetic change\n")
    (root / ".gitattributes").write_text("synthetic-content.txt filter=unregistered\n")
    _fixture_git(root, "add", ".gitattributes", source.name)
    _fixture_git(root, "commit", "--quiet", "-m", "synthetic attributes fixture")
    marker = tmp_path / "synthetic-filter-marker"
    _fixture_git(
        root,
        "config",
        "--local",
        "filter.unregistered.clean",
        "/usr/bin/tee " + shlex.quote(str(marker)),
    )
    source.write_text("after! synthetic change\n")
    with pytest.raises(RuntimeError, match="local Git configuration"):
        launcher["_verify_initial_sources"](root)
    assert not marker.exists()
    _fixture_git(root, "status", "--porcelain=v1")
    assert marker.read_bytes() == source.read_bytes()


@pytest.mark.parametrize(
    "relative",
    [
        "src/lotto649/__init__.so",
        "src/lotto649/__init__.cpython-312-darwin.so",
        "src/lotto649/v13_registered_attempt.so",
        "src/lotto649/v13_registered_attempt.cpython-312-darwin.so",
        "src/lotto649/v13_registered_attempt.pyd",
        "src/lotto649/v13_registered_attempt/__init__.py",
    ],
)
def test_launcher_rejects_committed_initial_import_loader_substitutes(
    launcher, launcher_repository, relative
):
    candidate = launcher_repository / relative
    candidate.parent.mkdir(parents=True, exist_ok=True)
    candidate.write_bytes(b"")  # Loader candidate only, never imported or loaded.
    _fixture_git(launcher_repository, "add", relative)
    _fixture_git(
        launcher_repository, "commit", "--quiet", "-m", "synthetic loader fixture"
    )
    with pytest.raises(RuntimeError, match="source loader"):
        launcher["_verify_initial_sources"](launcher_repository)
