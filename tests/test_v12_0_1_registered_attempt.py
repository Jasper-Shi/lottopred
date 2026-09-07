"""Synthetic-only tests for V12.0.1 execution boundaries.

These tests never invoke the registered historical command or instantiate its
canonical attempt. Every writable repository and event stream is a fixture.
"""

from __future__ import annotations

import ast
import copy
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
LAUNCHER = ROOT / "tools/run_v12_0_1_historical.py"


@pytest.fixture
def launcher():
    loaded = runpy.run_path(str(LAUNCHER), run_name="synthetic_launcher_fixture")
    return loaded["main"].__globals__


def _launcher_sys(*, arguments=None, version=None):
    return SimpleNamespace(
        argv=[str(LAUNCHER), *(arguments or ["--consume-v12-0-1-once"])],
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
    [[], ["--consume-v12-once"], ["--consume-v12-0-1-once", "--retry"]],
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
        "--consume-v12-0-1-once",
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
    from lotto649 import v12_0_1_registered_attempt

    return v12_0_1_registered_attempt


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
            attempt._API_PREFIX + "/git/ref/heads/v12-consumption-v12.0.1",
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
            attempt._API_PREFIX + "/git/ref/heads/v12-consumption-v12.0.1",
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
            attempt._API_PREFIX + "/git/ref/heads/v12-consumption-v12.0.1",
            allow_absent=True,
        )
    assert len(calls) == 1


@pytest.mark.parametrize(
    "method,path,payload,allow_absent",
    [
        ("DELETE", "/git/refs/heads/v12-consumption-v12.0.1", None, False),
        ("PATCH", "/git/refs/heads/v12-consumption-v12.0.1", {"sha": "a" * 40}, False),
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
            {"ref": "refs/heads/v12-consumption-v12.0.1", "sha": "abc123"},
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
            payload=payload,
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


@pytest.fixture
def synthetic_authorization(attempt, monkeypatch, tmp_path):
    identifiers = dict(
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
    r2_raw = b"synthetic registration identity"
    core_raw = (ROOT / attempt.CORE_PATH).read_bytes()
    requirements = (ROOT / attempt.REQUIREMENTS_PATH).read_bytes()
    closure = [
        {"path": attempt.CORE_PATH, "git_blob": "a" * 40, "sha256": attempt.CORE_SHA256}
    ]
    runtime = {"synthetic_runtime": True}
    payload = {
        "schema_version": "lotto649-v12.0.1-historical-authorization-v1",
        "experiment_id": "synthetic_contract",
        "model_version": "v12.0.1",
        "repository": attempt.REPOSITORY,
        "branch": "main",
        "registration_commit": attempt.R2,
        "registration_sha256": attempt._sha(r2_raw),
        "scientific_registration_commit": attempt.R1,
        "statistical_fingerprint_sha256": attempt.FINGERPRINT,
        "pure_core_sha256": attempt.CORE_SHA256,
        "implementation_commit": identifiers["implementation"],
        "implementation_base": identifiers["implementation_base"],
        "implementation_merge": identifiers["implementation_merge"],
        "authorization_base": identifiers["base"],
        "canonical_command": attempt.COMMAND,
        "governed_history_authority": attempt.HISTORY_AUTHORITY,
        "governed_history_identity": {"synthetic_metadata": True},
        "runtime": runtime,
        "runtime_dependency_closure": closure,
        "runtime_dependency_closure_sha256": attempt._sha(attempt._canonical(closure)),
        "review_records": [],
    }
    state = {"head": identifiers["head"], "drift": None, "read_core": []}

    class SyntheticGit:
        root = tmp_path

        def require_full_clean(self):
            pass

        def head(self):
            return state["head"]

        def read_blob(self, commit, path):
            if path == attempt.AUTHORIZATION_PATH:
                return attempt._canonical(payload) + b"\n"
            if path == attempt.R2_PATH:
                return r2_raw
            if path == attempt.CORE_PATH:
                state["read_core"].append(commit)
                return core_raw + (
                    b"# synthetic drift\n" if commit == state["drift"] else b""
                )
            if path == attempt.REQUIREMENTS_PATH:
                return requirements
            raise AssertionError("unexpected metadata read")

        def parents(self, commit):
            return {
                identifiers["head"]: (identifiers["base"], identifiers["source"]),
                identifiers["source"]: (identifiers["base"],),
                identifiers["implementation_merge"]: (
                    identifiers["implementation_base"],
                    identifiers["implementation"],
                ),
            }[commit]

        def tree(self, commit):
            return (
                "b" * 40
                if commit in {identifiers["head"], identifiers["source"]}
                else "c" * 40
            )

        def changes(self, earlier, later):
            if (earlier, later) == (identifiers["base"], identifiers["source"]):
                return [("A", attempt.AUTHORIZATION_PATH)]
            assert (earlier, later) == (
                identifiers["implementation_base"],
                identifiers["implementation"],
            )
            return [("A", path) for path in attempt.IMPLEMENTATION_PATHS]

        def ancestor(self, _earlier, _later):
            return True

    git = SyntheticGit()
    monkeypatch.setattr(attempt, "GitRepository", lambda _root: git)
    monkeypatch.setattr(
        attempt,
        "_registered_authorities",
        lambda *_args: (
            {"authority": {"synthetic_metadata": True}},
            {"experiment_id": "synthetic_contract"},
        ),
    )
    monkeypatch.setattr(attempt, "runtime_identity", lambda: runtime)
    monkeypatch.setattr(
        attempt, "runtime_dependency_closure", lambda *_args: copy.deepcopy(closure)
    )
    monkeypatch.setattr(attempt, "_remote_protection", lambda _api: None)
    monkeypatch.setattr(attempt, "_remote_main", lambda _api: identifiers["head"])
    monkeypatch.setattr(attempt, "_verify_reviews", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(attempt, "_verify_worktree_runtime", lambda *_args: None)
    return SimpleNamespace(
        ids=identifiers, payload=payload, state=state, root=tmp_path, git=git
    )


def test_authorization_checks_core_directly_at_all_four_checkpoints(
    attempt, synthetic_authorization
):
    fixture = synthetic_authorization
    verified = attempt.verify_authorization(fixture.root, api=object())

    assert verified.execution_commit == fixture.ids["head"]
    assert fixture.state["read_core"] == [
        fixture.ids[key] for key in ("implementation", "base", "source", "head")
    ]


@pytest.mark.parametrize("checkpoint", ["implementation", "base", "source", "head"])
def test_any_checkpoint_core_drift_refuses_authority(
    attempt, synthetic_authorization, checkpoint
):
    fixture = synthetic_authorization
    fixture.state["drift"] = fixture.ids[checkpoint]

    with pytest.raises(attempt.AuthorizationError, match="pure-core SHA"):
        attempt.verify_authorization(fixture.root, api=object())


def test_auth_source_branch_itself_never_authorizes_execution(
    attempt, synthetic_authorization
):
    fixture = synthetic_authorization
    fixture.state["head"] = fixture.ids["source"]

    with pytest.raises(attempt.AuthorizationError, match="ordinary protected-main"):
        attempt.verify_authorization(fixture.root, api=object())


@pytest.fixture
def review_evidence(attempt):
    head, base, merge, closure = "a" * 40, "b" * 40, "c" * 40, "d" * 64
    responses = {
        "/pulls/41": {
            "number": 41,
            "state": "closed",
            "merged": True,
            "merge_commit_sha": merge,
            "head": {"sha": head},
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
    for index, axis in enumerate(("standards", "spec")):
        attestation = {
            "schema_version": "lotto649-v12-i2-independent-review-v1",
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
        body = json.dumps(attestation, sort_keys=True)
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
                "comment_body_sha256": attempt._sha(body.encode()),
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
            return copy.deepcopy(responses[path.removeprefix(attempt._API_PREFIX)])

    def verify():
        attempt._verify_reviews(
            SyntheticApi(),
            records,
            implementation=head,
            merge=merge,
            base=base,
            closure_sha256=closure,
        )

    return SimpleNamespace(
        records=records, responses=responses, verify=verify, head=head
    )


def test_two_independent_agents_may_have_one_honest_github_publisher(review_evidence):
    review_evidence.verify()


@pytest.mark.parametrize("field", ["reviewer_agent_id", "review_session_id"])
def test_review_axes_cannot_reuse_agent_or_session(review_evidence, attempt, field):
    review_evidence.records[1][field] = review_evidence.records[0][field]
    with pytest.raises(attempt.AuthorizationError):
        review_evidence.verify()


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
    checks = review_evidence.responses[
        f"/commits/{review_evidence.head}/check-runs?per_page=100"
    ]["check_runs"]
    checks[1]["name"] = "test"
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
        "wrong_issue",
        "wrong_publisher",
        "changed_bytes",
        "major",
        "head",
    ],
)
def test_review_comment_requires_immutable_bound_provenance(
    review_evidence, attempt, change
):
    comment = review_evidence.responses["/issues/comments/201"]
    if change == "edited":
        comment["updated_at"] = "2032-01-01T12:01:00Z"
    elif change == "missing_timestamps":
        comment.pop("updated_at")
        comment.pop("created_at")
    elif change == "wrong_issue":
        comment["issue_url"] += "2"
    elif change == "wrong_publisher":
        comment["user"]["login"] = "synthetic-false-identity"
    elif change == "changed_bytes":
        comment["body"] += " "
    else:
        body = json.loads(comment["body"])
        body["major_count" if change == "major" else "head_sha"] = (
            1 if change == "major" else "e" * 40
        )
        comment["body"] = json.dumps(body)
        review_evidence.records[0]["comment_body_sha256"] = attempt._sha(
            comment["body"].encode()
        )
    with pytest.raises(attempt.AuthorizationError):
        review_evidence.verify()


@pytest.fixture
def lease_evidence(attempt, synthetic_authorization, monkeypatch):
    fixture = synthetic_authorization
    raw_commit = (
        f"tree {'b' * 40}\nparent {'4' * 40}\nauthor Synthetic <fixture@example.invalid> 1700000000 +0000\ncommitter Synthetic <fixture@example.invalid> 1700000000 +0000\n\nsynthetic authorization metadata\n"
    ).encode()
    monkeypatch.setattr(fixture.git, "run", lambda *args: raw_commit, raising=False)
    monkeypatch.setattr(attempt.secrets, "token_hex", lambda size: "d" * 64)
    authority = attempt.verify_authorization(fixture.root, api=object())
    oid, raw, payload = attempt._lease_commit(fixture.git, authority, "d" * 64)
    observed = {
        "sha": oid,
        "tree": {"sha": payload["tree"]},
        "parents": [{"sha": parent} for parent in payload["parents"]],
        "author": payload["author"],
        "committer": payload["committer"],
        "message": payload["message"],
        "verification": {
            "verified": False,
            "signature": None,
            "payload": None,
            "reason": "unsigned",
        },
    }
    reference = {"ref": attempt.LEASE_REF, "object": {"sha": oid, "type": "commit"}}
    state = {
        "existing": False,
        "fail": None,
        "created": False,
        "calls": [],
        "observed": observed,
    }

    class SyntheticApi:
        def request_json(self, method, path, *, payload=None, allow_absent=False):
            suffix = path.removeprefix(attempt._API_PREFIX)
            state["calls"].append((method, suffix))
            if state["fail"] == (method, suffix):
                raise attempt.AuthorizationError("synthetic uncertain transport")
            if method == "GET" and suffix == "/git/ref/heads/v12-consumption-v12.0.1":
                if not state["created"]:
                    assert allow_absent
                return (
                    copy.deepcopy(reference)
                    if state["created"] or state["existing"]
                    else None
                )
            if method == "POST" and suffix == "/git/commits":
                return {"sha": oid}
            if method == "GET" and suffix == "/git/commits/" + oid:
                return copy.deepcopy(state["observed"])
            if method == "POST" and suffix == "/git/refs":
                assert payload == {"ref": attempt.LEASE_REF, "sha": oid}
                state["created"] = True
                return copy.deepcopy(reference)
            raise AssertionError("unexpected synthetic transport")

    return SimpleNamespace(
        authority=authority,
        api=SyntheticApi(),
        state=state,
        oid=oid,
        raw=raw,
        payload=payload,
        fixture=fixture,
    )


def test_lease_upload_verify_create_reread_order_and_single_use(
    attempt, lease_evidence
):
    fixture = lease_evidence
    lease = attempt.acquire_historical_lease(fixture.authority, fixture.api)
    assert fixture.state["calls"] == [
        ("GET", "/git/ref/heads/v12-consumption-v12.0.1"),
        ("POST", "/git/commits"),
        ("GET", "/git/commits/" + fixture.oid),
        ("POST", "/git/refs"),
        ("GET", "/git/ref/heads/v12-consumption-v12.0.1"),
    ]
    assert lease.commit == fixture.oid
    attempt._consume_lease(fixture.authority, lease)
    with pytest.raises(attempt.AttemptError):
        attempt._consume_lease(fixture.authority, lease)
    before = list(fixture.state["calls"])
    with pytest.raises(attempt.AttemptError):
        attempt.acquire_historical_lease(fixture.authority, fixture.api)
    assert fixture.state["calls"] == before


def test_existing_lease_never_uploads_or_creates(attempt, lease_evidence):
    fixture = lease_evidence
    fixture.state["existing"] = True
    with pytest.raises(attempt.AttemptError, match="already exists"):
        attempt.acquire_historical_lease(fixture.authority, fixture.api)
    assert fixture.state["calls"] == [("GET", "/git/ref/heads/v12-consumption-v12.0.1")]


@pytest.mark.parametrize("phase", ["absence", "upload", "verify", "create"])
def test_uncertain_lease_attempt_has_no_automatic_or_manual_same_capability_retry(
    attempt, lease_evidence, phase
):
    fixture = lease_evidence
    fixture.state["fail"] = {
        "absence": ("GET", "/git/ref/heads/v12-consumption-v12.0.1"),
        "upload": ("POST", "/git/commits"),
        "verify": ("GET", "/git/commits/" + fixture.oid),
        "create": ("POST", "/git/refs"),
    }[phase]
    with pytest.raises(attempt.AuthorizationError):
        attempt.acquire_historical_lease(fixture.authority, fixture.api)
    before = list(fixture.state["calls"])
    fixture.state["fail"] = None
    with pytest.raises(attempt.AttemptError):
        attempt.acquire_historical_lease(fixture.authority, fixture.api)
    assert fixture.state["calls"] == before
    assert sum(call == ("POST", "/git/refs") for call in before) <= 1


@pytest.mark.parametrize(
    "field", ["sha", "tree", "parents", "author", "message", "verification"]
)
def test_lease_object_mismatch_never_creates_ref(attempt, lease_evidence, field):
    fixture = lease_evidence
    wrong = {
        "sha": "e" * 40,
        "tree": {"sha": "e" * 40},
        "parents": [],
        "author": {},
        "message": "changed",
        "verification": {
            "verified": False,
            "signature": None,
            "payload": "unregistered raw payload",
            "reason": "unsigned",
        },
    }
    fixture.state["observed"][field] = wrong[field]
    with pytest.raises(attempt.AuthorizationError):
        attempt.acquire_historical_lease(fixture.authority, fixture.api)
    assert ("POST", "/git/refs") not in fixture.state["calls"]


@pytest.mark.parametrize("capability", ["VerifiedAuthorization", "Lease"])
def test_canonical_capabilities_cannot_be_directly_constructed(attempt, capability):
    with pytest.raises((attempt.AuthorizationError, attempt.AttemptError)):
        vars(attempt)[capability]()


@pytest.mark.parametrize(
    "field,value",
    [
        ("model_version", "v12.0.0"),
        ("branch", "synthetic-other-branch"),
        ("repository", "synthetic/other"),
        ("registration_commit", "e" * 40),
        ("scientific_registration_commit", "e" * 40),
        ("statistical_fingerprint_sha256", "e" * 64),
        ("pure_core_sha256", "e" * 64),
        ("canonical_command", "python alternate.py"),
        ("governed_history_authority", "e" * 40),
        ("governed_history_identity", {}),
        ("runtime", {"synthetic_runtime": False}),
        ("runtime_dependency_closure_sha256", "e" * 64),
    ],
)
def test_authorization_refuses_drift_in_every_frozen_binding(
    attempt, synthetic_authorization, field, value
):
    fixture = synthetic_authorization
    fixture.payload[field] = value
    with pytest.raises(attempt.AuthorizationError):
        attempt.verify_authorization(fixture.root, api=object())


def test_issued_authorization_rejects_later_mutation(attempt, synthetic_authorization):
    fixture = synthetic_authorization
    authority = attempt.verify_authorization(fixture.root, api=object())
    authority.payload["runtime"]["synthetic_runtime"] = False
    with pytest.raises(attempt.AuthorizationError, match="altered"):
        attempt.acquire_historical_lease(authority, object())


def test_auth_source_cannot_smuggle_second_changed_path(
    attempt, synthetic_authorization, monkeypatch
):
    fixture = synthetic_authorization
    original = fixture.git.changes

    def changes(earlier, later):
        result = original(earlier, later)
        return (
            result + [("M", "config.yaml")]
            if later == fixture.ids["source"]
            else result
        )

    monkeypatch.setattr(fixture.git, "changes", changes)
    with pytest.raises(attempt.AuthorizationError, match="auth-only"):
        attempt.verify_authorization(fixture.root, api=object())


def test_i2_cannot_include_seventh_path(attempt, synthetic_authorization, monkeypatch):
    fixture = synthetic_authorization
    original = fixture.git.changes

    def changes(earlier, later):
        result = original(earlier, later)
        return (
            result + [("M", "config.yaml")]
            if later == fixture.ids["implementation"]
            else result
        )

    monkeypatch.setattr(fixture.git, "changes", changes)
    with pytest.raises(attempt.AuthorizationError, match="I2 ancestry"):
        attempt.verify_authorization(fixture.root, api=object())


def test_local_auth_head_must_equal_current_remote_main(
    attempt, synthetic_authorization, monkeypatch
):
    monkeypatch.setattr(attempt, "_remote_main", lambda api: "e" * 40)
    with pytest.raises(attempt.AuthorizationError, match="exact protected remote"):
        attempt.verify_authorization(synthetic_authorization.root, api=object())


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


def test_history_reader_refuses_unclaimed_capability_without_reading_any_history(
    attempt, synthetic_authorization
):
    authority = attempt.verify_authorization(synthetic_authorization.root, api=object())
    with pytest.raises(attempt.AttemptError, match="active claimed"):
        attempt._load_governed_history(authority)


def _durable_case(*, first_main=(31, 33, 35, 37, 39, 41)):
    from datetime import date

    from lotto649 import v12_0_1_evidence as evidence
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
    ["R2", "R1", "HISTORY_AUTHORITY", "LEASE_REF", "REPOSITORY", "AUTHORIZATION_PATH"],
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
    with pytest.raises(attempt.AuthorizationError, match="clean"):
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
