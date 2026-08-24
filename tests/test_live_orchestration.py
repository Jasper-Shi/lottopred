from __future__ import annotations

from contextlib import contextmanager
from dataclasses import replace
from datetime import UTC, datetime, timedelta
import hashlib
import io
import os
from pathlib import Path
import subprocess
import sys

import pytest

from lotto649.history_artifact_publication_github import ArtifactPublicationReceipt
from lotto649.history_execution_handoff import (
    ExecutionWorkspace,
    FrozenExecutionArtifacts,
    FrozenExecutionFile,
)
from lotto649.history_publication import PreparedPublication, RawSource
from lotto649.history_publication_cas import (
    CasAck,
    CasStatus,
    PublicationOutcome,
    PublicationReceipt,
)
from lotto649.official_source_collection import OfficialSourceCollection
from lotto649.operational_history import load_published_history

import lotto649.live_orchestration as orchestration
from lotto649 import live


ROOT = Path(__file__).resolve().parents[1]
B = "1" * 40
E = "2" * 40
S = "3" * 40
P = "4" * 40
A = "5" * 40
CREATED_AT = datetime(2026, 8, 27, 12, tzinfo=UTC)
OUTPUT_PATH = "predictions/2026-08-29__candidate__v1.0.0.json"


def _base_history():
    head = (
        orchestration.subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
        )
        .stdout.decode("ascii")
        .strip()
    )
    history = load_published_history(ROOT, head)
    return replace(
        history,
        registry=replace(
            history.registry,
            requested_revision=B,
            resolved_revision=B,
        ),
    )


def _published_history(base):
    target = orchestration.next_draw_date(base.draws[-1].draw_date)
    draw_type = type(base.draws[-1])
    draw = draw_type(target, (1, 2, 3, 4, 5, 6), 7)
    suffix_sha = "6" * 64
    suffix_head = "7" * 64
    registry_sha = "8" * 64
    return replace(
        base,
        draws=base.draws + (draw,),
        suffix=replace(
            base.suffix,
            bytes=base.suffix.bytes + 1,
            file_sha256=suffix_sha,
            event_count=base.suffix.event_count + 1,
            head_event_sha256=suffix_head,
            history_through=target,
            evidence_commits=base.suffix.evidence_commits + (E,),
        ),
        registry=replace(
            base.registry,
            requested_revision=P,
            resolved_revision=P,
            publication_commit=P,
            git_blob="9" * 40,
            bytes=base.registry.bytes + 1,
            file_sha256=registry_sha,
            event_count=base.registry.event_count + 1,
            head_event_sha256="a" * 64,
        ),
        registry_suffix=replace(
            base.registry_suffix,
            git_blob="b" * 40,
            bytes=base.registry_suffix.bytes + 1,
            sha256=suffix_sha,
            event_count=base.registry_suffix.event_count + 1,
            head_event_sha256=suffix_head,
            history_through=target,
        ),
        registry_transaction=replace(
            base.registry_transaction,
            base_commit=B,
            evidence_commit=E,
            suffix_commit=S,
        ),
    )


def _workspace(history):
    workspace = object.__new__(ExecutionWorkspace)
    object.__setattr__(workspace, "root", ROOT)
    object.__setattr__(workspace, "publication_commit", P)
    object.__setattr__(workspace, "history", history)
    object.__setattr__(workspace, "_capability", object())
    return workspace


def _artifacts():
    artifacts = object.__new__(FrozenExecutionArtifacts)
    object.__setattr__(artifacts, "repository", ROOT)
    object.__setattr__(artifacts, "parent_commit", P)
    object.__setattr__(artifacts, "tree_oid", "c" * 40)
    object.__setattr__(artifacts, "artifact_commit", A)
    object.__setattr__(artifacts, "paths", (OUTPUT_PATH,))
    object.__setattr__(
        artifacts,
        "files",
        (
            FrozenExecutionFile(
                path=OUTPUT_PATH,
                bytes=1,
                sha256="d" * 64,
                git_blob="e" * 40,
            ),
        ),
    )
    object.__setattr__(artifacts, "created_at", CREATED_AT)
    object.__setattr__(artifacts, "_capability", object())
    return artifacts


def _fixture_ports(events: list[str], monkeypatch):
    base = _base_history()
    published = _published_history(base)
    artifact_history = replace(
        published,
        registry=replace(
            published.registry,
            requested_revision=A,
            resolved_revision=A,
        ),
    )
    target = published.draws[-1].draw_date
    source_time = datetime(2026, 8, 27, 10, tzinfo=UTC)
    collection = OfficialSourceCollection(
        sources=(
            RawSource("wclc", "https://wclc.invalid", source_time, b"wclc"),
            RawSource("loto_quebec", "https://lq.invalid", source_time, b"lq"),
        ),
        completed_at=source_time,
    )
    prepared = PreparedPublication(ROOT, B, E, S, P, target, "7" * 64, "a" * 64)
    p_receipt = PublicationReceipt(
        B,
        P,
        B,
        P,
        CasAck(CasStatus.APPLIED),
        PublicationOutcome.ADVANCED,
        published,
    )
    workspace = _workspace(published)
    artifacts = _artifacts()
    a_receipt = ArtifactPublicationReceipt(
        P,
        A,
        P,
        A,
        CasAck(CasStatus.APPLIED),
        PublicationOutcome.ADVANCED,
        artifact_history,
    )

    def load(_cfg):
        events.append("load-B")
        return base

    def collect(observed_target, *, clock):
        assert observed_target == target
        assert callable(clock)
        events.append("collect")
        return collection

    def prepare(repository, **kwargs):
        assert repository == ROOT
        assert kwargs == {
            "expected_base_commit": B,
            "sources": collection.sources,
            "created_at": source_time,
        }
        events.append("prepare")
        return prepared

    def publish_history(observed, *, token):
        assert observed is prepared
        assert token == "secret"
        events.append("publish-P")
        return p_receipt

    @contextmanager
    def open_workspace(observed):
        assert observed is p_receipt
        events.append("context-enter")
        try:
            yield workspace
        finally:
            events.append("context-exit")

    def execute(observed, *, generated_at):
        assert observed is workspace
        assert generated_at == CREATED_AT
        events.append("execute-P")
        return orchestration._LiveOutputManifest(P, (OUTPUT_PATH,))

    def freeze(observed_workspace, paths, *, created_at):
        assert observed_workspace is workspace
        assert paths == (OUTPUT_PATH,)
        assert created_at == CREATED_AT
        events.append("freeze-A")
        return artifacts

    def publish_artifacts(observed, *, token):
        assert observed is artifacts
        assert token == "secret"
        events.append("publish-A")
        return a_receipt

    monkeypatch.setattr(
        orchestration,
        "_load_production_config",
        lambda: {
            "_root": ROOT,
            "_authority_head": B,
            "data": {"refresh_enabled": True},
            "live": {"enabled": True},
        },
    )
    monkeypatch.setattr(orchestration, "_trusted_utc_now", lambda: CREATED_AT)
    monkeypatch.setattr(orchestration, "load_operational_history", load)
    monkeypatch.setattr(
        orchestration,
        "RequestsOfficialSourceHttpClient",
        lambda: object(),
    )
    monkeypatch.setattr(
        orchestration,
        "collect_official_sources",
        lambda observed_target, *, http_client, clock: collect(
            observed_target,
            clock=clock,
        ),
    )
    monkeypatch.setattr(orchestration, "prepare_history_publication", prepare)
    monkeypatch.setattr(
        orchestration,
        "publish_prepared_history_to_github",
        publish_history,
    )
    monkeypatch.setattr(
        orchestration, "open_github_execution_workspace", open_workspace
    )
    monkeypatch.setattr(orchestration, "_execute_published_code", execute)
    monkeypatch.setattr(orchestration, "freeze_execution_outputs", freeze)
    monkeypatch.setattr(
        orchestration,
        "publish_frozen_execution_artifacts_to_github",
        publish_artifacts,
    )
    return {
        "base": base,
        "published": published,
        "p_receipt": p_receipt,
        "a_receipt": a_receipt,
    }


def test_full_cycle_success_preserves_order_and_context_through_a_publication(
    monkeypatch,
):
    events: list[str] = []
    _fixture_ports(events, monkeypatch)

    receipt = orchestration.orchestrate_github_live_cycle(token="secret")

    assert receipt.history_publication.publication_commit == P
    assert receipt.artifact_publication.artifact_commit == A
    assert receipt.output_paths == (OUTPUT_PATH,)
    assert events == [
        "load-B",
        "collect",
        "prepare",
        "publish-P",
        "context-enter",
        "execute-P",
        "freeze-A",
        "publish-A",
        "context-exit",
    ]


def test_live_module_has_no_aggregate_output_bypass():
    assert not hasattr(live, "_run_verified_live_outputs")


def test_prediction_generation_passes_the_frozen_instant_into_predictor(
    monkeypatch,
    tmp_path,
):
    history = _base_history()
    generated_at = datetime(2026, 8, 24, 12, tzinfo=UTC)
    observed = []

    class Model:
        name = "candidate"

    class SavedPrediction:
        metadata = {}

    monkeypatch.setattr(
        live,
        "build_models",
        lambda _cfg, requested: {"candidate": Model()},
    )

    def predict(_model, _draws, _target, _cfg, _version, *, generated_at):
        observed.append(generated_at)
        return SavedPrediction()

    monkeypatch.setattr(live, "make_prediction", predict)
    monkeypatch.setattr(
        live,
        "operational_history_provenance",
        lambda _history: {"publication": P},
    )
    monkeypatch.setattr(
        live,
        "save_prediction",
        lambda _root, _prediction: tmp_path / "prediction.json",
    )

    live._generate_next_predictions(
        {
            "_root": tmp_path,
            "live": {"models": ["candidate"], "shadow_models": []},
            "project": {"model_version": "v1.0.0"},
        },
        history,
        generated_at=generated_at,
    )

    assert observed == [generated_at]


def test_published_code_runs_isolated_from_p_with_only_smtp_environment(
    monkeypatch,
):
    actual_head = (
        subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
        )
        .stdout.decode("ascii")
        .strip()
    )
    history = _base_history()
    history = replace(
        history,
        registry=replace(
            history.registry,
            requested_revision=actual_head,
            resolved_revision=actual_head,
            publication_commit=actual_head,
        ),
    )
    workspace = _workspace(history)
    object.__setattr__(workspace, "publication_commit", actual_head)
    entries = []
    for name, relative in (
        ("lotto649", "src/lotto649/__init__.py"),
        ("lotto649.live", "src/lotto649/live.py"),
        ("lotto649.operational_history", "src/lotto649/operational_history.py"),
    ):
        raw = subprocess.run(
            ["git", "-C", str(ROOT), "show", f"{actual_head}:{relative}"],
            check=True,
            capture_output=True,
        ).stdout
        blob = hashlib.sha1(
            f"blob {len(raw)}\0".encode("ascii") + raw,
            usedforsecurity=False,
        ).hexdigest()
        entries.append(
            {
                "git_blob": blob,
                "name": name,
                "path": relative,
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    payload = {
        "modules": entries,
        "paths": [OUTPUT_PATH],
        "publication_commit": actual_head,
    }
    raw_manifest = (
        orchestration.json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode()
    captured = {}

    monkeypatch.setenv("SMTP_USERNAME", "sender@example.test")
    monkeypatch.setenv("SMTP_PASSWORD", "app-password")
    monkeypatch.setenv("GITHUB_TOKEN", "must-not-cross")
    monkeypatch.setenv("LOTTO_GITHUB_PUBLICATION_TOKEN", "must-not-cross")
    monkeypatch.setenv("PYTHONPATH", "/hostile")
    monkeypatch.setattr(
        ExecutionWorkspace,
        "load_config",
        lambda self: {
            "_root": self.root,
            "data": {"refresh_enabled": True},
            "live": {"enabled": True},
        },
    )
    monkeypatch.setattr(
        orchestration,
        "_require_exact_p_worker",
        lambda _workspace, _script: None,
    )
    monkeypatch.setattr(
        orchestration,
        "_require_no_lotto649_bytecode",
        lambda _workspace: None,
    )
    monkeypatch.setattr(
        orchestration,
        "_validate_module_inventory",
        lambda _workspace, _manifest: None,
    )

    def run(command, **kwargs):
        captured["command"] = command
        captured.update(kwargs)
        return orchestration._WorkerProcessResult(0, raw_manifest, b"")

    monkeypatch.setattr(orchestration, "_run_bounded_worker", run)

    manifest = orchestration._execute_published_code(
        workspace,
        generated_at=CREATED_AT,
    )

    assert manifest.publication_commit == actual_head
    assert manifest.paths == (OUTPUT_PATH,)
    assert len(manifest.modules) == 3
    assert captured["command"] == [
        sys.executable,
        "-I",
        "-S",
        "-B",
        "-c",
        orchestration._P_BOOTSTRAP,
        str(ROOT),
        CREATED_AT.isoformat(),
    ]
    assert captured["cwd"] == ROOT
    assert captured["env"] == {
        "GIT_CONFIG_COUNT": "0",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_SYSTEM": os.devnull,
        "GIT_GRAFT_FILE": os.devnull,
        "GIT_NO_LAZY_FETCH": "1",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "LANG": "C",
        "LC_ALL": "C",
        "PATH": "/usr/bin:/bin",
        "TMPDIR": "/tmp",
        "SMTP_USERNAME": "sender@example.test",
        "SMTP_PASSWORD": "app-password",
    }
    assert "GITHUB_TOKEN" not in captured["env"]
    assert "LOTTO_GITHUB_PUBLICATION_TOKEN" not in captured["env"]
    assert "PYTHONPATH" not in captured["env"]


def test_public_wrapper_reads_real_disabled_config_before_any_adapter(
    monkeypatch,
):
    reached: list[str] = []
    monkeypatch.setattr(
        orchestration,
        "_load_production_config",
        lambda: {
            "_root": ROOT,
            "data": {"refresh_enabled": False},
            "live": {"enabled": False},
        },
    )

    def forbidden():
        reached.append("adapter")
        raise AssertionError("adapter constructed while incident gates were false")

    monkeypatch.setattr(orchestration, "RequestsOfficialSourceHttpClient", forbidden)

    try:
        orchestration.orchestrate_github_live_cycle(token="secret")
    except RuntimeError as exc:
        assert "live execution is disabled" in str(exc)
    else:
        raise AssertionError("disabled production wrapper unexpectedly ran")

    assert reached == []
    try:
        orchestration.orchestrate_github_live_cycle(
            {
                "_root": ROOT,
                "data": {"refresh_enabled": True},
                "live": {"enabled": True},
            },
            token="secret",
            clock=lambda: CREATED_AT,
        )
    except TypeError:
        pass
    else:
        raise AssertionError("public wrapper accepted forged cfg/clock")


def test_stage1_committed_config_reaches_the_protected_history_boundary(monkeypatch):
    from lotto649.config import load_config

    cfg = load_config(ROOT / "config.yaml")
    cfg["_root"] = ROOT
    cfg["_authority_head"] = B
    reached = []

    class ReachedProtectedBoundary(RuntimeError):
        pass

    def stop_at_history(received):
        reached.append(received)
        raise ReachedProtectedBoundary

    monkeypatch.setattr(orchestration, "_load_production_config", lambda: cfg)
    monkeypatch.setattr(orchestration, "load_operational_history", stop_at_history)

    with pytest.raises(ReachedProtectedBoundary):
        orchestration.orchestrate_github_live_cycle(token="unused-secret")

    assert reached == [cfg]


@pytest.mark.parametrize(
    "raw",
    [
        b'{"modules":[],"modules":[],"paths":[],"publication_commit":"x"}\n',
        b'{"extra":1,"modules":[],"paths":[],"publication_commit":"x"}\n',
        b'{\n  "modules": [], "paths": [], "publication_commit": "x"\n}\n',
        b'{"modules":[],"paths":[NaN],"publication_commit":"x"}\n',
    ],
)
def test_worker_manifest_rejects_duplicate_extra_or_noncanonical_json(raw):
    with pytest.raises(orchestration.PublishedCodeExecutionError):
        orchestration._parse_worker_manifest(raw)


def test_module_inventory_binds_each_module_name_to_its_p_source_path():
    workspace = _workspace(_published_history(_base_history()))
    manifest = orchestration._LiveOutputManifest(
        P,
        (OUTPUT_PATH,),
        (
            orchestration._PublishedModuleIdentity(
                "lotto649",
                "src/lotto649/__init__.py",
                "1" * 40,
                "1" * 64,
            ),
            orchestration._PublishedModuleIdentity(
                "lotto649.live",
                "src/lotto649/__init__.py",
                "1" * 40,
                "1" * 64,
            ),
            orchestration._PublishedModuleIdentity(
                "lotto649.operational_history",
                "src/lotto649/operational_history.py",
                "1" * 40,
                "1" * 64,
            ),
        ),
    )

    with pytest.raises(
        orchestration.PublishedCodeExecutionError,
        match="inventory is incomplete|entry is invalid",
    ):
        orchestration._validate_module_inventory(workspace, manifest)


def test_exact_p_worker_rejects_worktree_replacement(tmp_path):
    repository = tmp_path / "repository"
    script = repository / "src" / "lotto649" / "_live_worker.py"
    script.parent.mkdir(parents=True)
    script.write_bytes(b"print('reviewed')\n")
    subprocess.run(
        ["git", "init", "--quiet", str(repository)],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(repository), "add", "src/lotto649/_live_worker.py"],
        check=True,
        capture_output=True,
    )
    environment = os.environ.copy()
    environment.update(
        {
            "GIT_AUTHOR_EMAIL": "test@example.invalid",
            "GIT_AUTHOR_NAME": "Test",
            "GIT_COMMITTER_EMAIL": "test@example.invalid",
            "GIT_COMMITTER_NAME": "Test",
        }
    )
    subprocess.run(
        ["git", "-C", str(repository), "commit", "--quiet", "-m", "fixture"],
        check=True,
        capture_output=True,
        env=environment,
    )
    publication = (
        subprocess.run(
            ["git", "-C", str(repository), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
        )
        .stdout.decode("ascii")
        .strip()
    )
    workspace = _workspace(_published_history(_base_history()))
    object.__setattr__(workspace, "root", repository)
    object.__setattr__(workspace, "publication_commit", publication)

    orchestration._require_exact_p_worker(workspace, script)
    script.write_bytes(b"print('replaced')\n")

    with pytest.raises(
        orchestration.PublishedCodeExecutionError,
        match="differs from exact P",
    ):
        orchestration._require_exact_p_worker(workspace, script)


class _StageFailure(RuntimeError):
    pass


@pytest.mark.parametrize(
    ("stage", "expected_tail"),
    [
        ("collect_official_sources", ["load-B", "failed"]),
        ("publish_prepared_history_to_github", ["collect", "prepare", "failed"]),
        ("_execute_published_code", ["context-enter", "failed", "context-exit"]),
        (
            "publish_frozen_execution_artifacts_to_github",
            ["freeze-A", "failed", "context-exit"],
        ),
    ],
)
def test_failure_truncates_cycle_without_retry_and_closes_post_p_context(
    stage,
    expected_tail,
    monkeypatch,
):
    events: list[str] = []
    _fixture_ports(events, monkeypatch)
    calls = 0

    def fail(*args, **kwargs):
        nonlocal calls
        calls += 1
        events.append("failed")
        raise _StageFailure(stage)

    monkeypatch.setattr(orchestration, stage, fail)

    with pytest.raises(_StageFailure, match=stage):
        orchestration.orchestrate_github_live_cycle(token="secret")

    assert calls == 1
    assert events[-len(expected_tail) :] == expected_tail
    if stage != "publish_frozen_execution_artifacts_to_github":
        assert "publish-A" not in events


def test_p_receipt_mismatch_stops_before_execution_context(monkeypatch):
    events: list[str] = []
    _fixture_ports(events, monkeypatch)
    publish = orchestration.publish_prepared_history_to_github

    def mismatch(*args, **kwargs):
        receipt = publish(*args, **kwargs)
        return replace(receipt, expected_base="f" * 40)

    monkeypatch.setattr(
        orchestration,
        "publish_prepared_history_to_github",
        mismatch,
    )
    with pytest.raises(
        orchestration.LiveOrchestrationError,
        match="receipt is inconsistent",
    ):
        orchestration.orchestrate_github_live_cycle(token="secret")

    assert "context-enter" not in events


def test_prediction_clock_cannot_predate_collected_draw_or_publication(monkeypatch):
    events: list[str] = []
    _fixture_ports(events, monkeypatch)
    too_early = datetime(2026, 8, 27, 9, tzinfo=UTC)
    monkeypatch.setattr(orchestration, "_trusted_utc_now", lambda: too_early)

    with pytest.raises(
        orchestration.LiveOrchestrationError,
        match="predates source collection",
    ):
        orchestration.orchestrate_github_live_cycle(token="secret")

    assert events[-2:] == ["context-enter", "context-exit"]
    assert "execute-P" not in events


def test_a_receipt_history_mismatch_closes_context_and_returns_no_success(monkeypatch):
    events: list[str] = []
    _fixture_ports(events, monkeypatch)
    publish = orchestration.publish_frozen_execution_artifacts_to_github

    def mismatch(*args, **kwargs):
        receipt = publish(*args, **kwargs)
        bad_history = replace(receipt.history, draws=receipt.history.draws[:-1])
        return replace(receipt, history=bad_history)

    monkeypatch.setattr(
        orchestration,
        "publish_frozen_execution_artifacts_to_github",
        mismatch,
    )
    with pytest.raises(
        orchestration.LiveOrchestrationError,
        match="history differs from P",
    ):
        orchestration.orchestrate_github_live_cycle(token="secret")

    assert events[-2:] == ["publish-A", "context-exit"]


def test_isolated_no_site_bootstrap_can_import_runtime_dependencies():
    source = ROOT / "src"
    code = "\n".join(
        (
            "import pathlib, sys, sysconfig",
            "assert 'site' not in sys.modules",
            "assert 'sitecustomize' not in sys.modules",
            "for key in ('purelib', 'platlib'):",
            "    value = sysconfig.get_path(key)",
            "    if value and value not in sys.path: sys.path.append(value)",
            f"sys.path.insert(0, {str(source)!r})",
            "import yaml, numpy, sklearn, lotto649",
            "origin = pathlib.Path(lotto649.__file__).resolve()",
            f"origin.relative_to(pathlib.Path({str(source / 'lotto649')!r}).resolve())",
            "assert 'sitecustomize' not in sys.modules",
        )
    )
    completed = subprocess.run(
        [sys.executable, "-I", "-S", "-B", "-c", code],
        check=False,
        capture_output=True,
        env={
            "LANG": "C",
            "LC_ALL": "C",
            "PATH": "/usr/bin:/bin",
            "TMPDIR": "/tmp",
        },
        timeout=120,
    )

    assert completed.returncode == 0, completed.stderr.decode("utf-8", "replace")
    assert completed.stdout == b""
    assert completed.stderr == b""


def test_no_site_bootstrap_finds_python_311_312_style_venv_packages(tmp_path):
    venv = tmp_path / "venv"
    subprocess.run(
        [sys.executable, "-m", "venv", "--without-pip", str(venv)],
        check=True,
        capture_output=True,
    )
    venv_python = venv / "bin" / "python"
    site_packages = (
        venv
        / "lib"
        / f"python{sys.version_info.major}.{sys.version_info.minor}"
        / "site-packages"
    )
    site_packages.mkdir(parents=True, exist_ok=True)
    (site_packages / "only_in_this_venv.py").write_text(
        "VALUE = 'venv-only'\n",
        encoding="utf-8",
    )
    code = "\n".join(
        (
            "import pathlib, sys, sysconfig",
            "paths=[]",
            "for key in ('purelib','platlib'):",
            " value=sysconfig.get_path(key)",
            " if value: paths.append(pathlib.Path(value))",
            "prefix=pathlib.Path(sys.executable).absolute().parent.parent",
            "version=f'python{sys.version_info.major}.{sys.version_info.minor}'",
            "paths.extend((prefix/'lib'/version/'site-packages',prefix/'Lib'/'site-packages'))",
            "for value in paths:",
            " try: candidate=str(value.resolve(strict=True))",
            " except OSError: continue",
            " if candidate not in sys.path: sys.path.append(candidate)",
            "import only_in_this_venv",
            "assert only_in_this_venv.VALUE == 'venv-only'",
            "assert 'site' not in sys.modules",
            "assert 'sitecustomize' not in sys.modules",
        )
    )
    completed = subprocess.run(
        [str(venv_python), "-I", "-S", "-B", "-c", code],
        check=False,
        capture_output=True,
        env={
            "LANG": "C",
            "LC_ALL": "C",
            "PATH": "/usr/bin:/bin",
            "TMPDIR": "/tmp",
        },
        timeout=120,
    )

    assert completed.returncode == 0, completed.stderr.decode("utf-8", "replace")
    assert completed.stdout == b""
    assert completed.stderr == b""


def _run_private_worker_fixture(
    tmp_path,
    *,
    generated_at,
    evaluations,
    predictions,
):
    repository = tmp_path / "published"
    package = repository / "src" / "lotto649"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "_live_worker.py").write_bytes(
        (ROOT / "src" / "lotto649" / "_live_worker.py").read_bytes()
    )
    (package / "config.py").write_text(
        """\
from pathlib import Path


def load_config(path):
    return {
        "_root": Path(path).resolve().parent,
        "data": {"refresh_enabled": True},
        "live": {"enabled": True},
    }
""",
        encoding="utf-8",
    )
    (package / "operational_history.py").write_text(
        """\
import subprocess
from types import SimpleNamespace


def load_operational_history(cfg):
    publication = subprocess.run(
        ["git", "-C", str(cfg["_root"]), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
    ).stdout.decode("ascii").strip()
    registry = SimpleNamespace(
        resolved_revision=publication,
        publication_commit=publication,
    )
    return SimpleNamespace(registry=registry)
""",
        encoding="utf-8",
    )
    live_source = (
        """\
from pathlib import Path

"""
        + f"_EVALUATIONS = {evaluations!r}\n"
        + f"_PREDICTIONS = {predictions!r}\n"
        + """

def _evaluate_due_predictions(cfg, history):
    del history
    completed = []
    for relative, raw in sorted(_EVALUATIONS.items()):
        output = Path(cfg["_root"]) / relative
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(raw)
        target, model, version = output.stem.split("__")
        completed.append({
            "target_draw_date": target,
            "model_name": model,
            "model_version": version,
        })
    return completed


def _generate_next_predictions(cfg, history, *, generated_at):
    del history, generated_at
    completed = []
    for relative, raw in sorted(_PREDICTIONS.items()):
        output = Path(cfg["_root"]) / relative
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(raw)
        completed.append(output)
    return completed
"""
    )
    (package / "live.py").write_text(live_source, encoding="utf-8")
    (repository / "config.yaml").write_text("fixture: true\n", encoding="utf-8")
    subprocess.run(
        ["git", "init", "--quiet", str(repository)],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(repository), "add", "."],
        check=True,
        capture_output=True,
    )
    environment = os.environ.copy()
    environment.update(
        {
            "GIT_AUTHOR_EMAIL": "test@example.invalid",
            "GIT_AUTHOR_NAME": "Test",
            "GIT_COMMITTER_EMAIL": "test@example.invalid",
            "GIT_COMMITTER_NAME": "Test",
        }
    )
    subprocess.run(
        [
            "git",
            "-c",
            "commit.gpgsign=false",
            "-c",
            "core.hooksPath=/dev/null",
            "-C",
            str(repository),
            "commit",
            "--quiet",
            "-m",
            "published fixture",
        ],
        check=True,
        capture_output=True,
        env=environment,
    )
    publication = (
        subprocess.run(
            ["git", "-C", str(repository), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
        )
        .stdout.decode("ascii")
        .strip()
    )
    subprocess.run(
        ["git", "-C", str(repository), "checkout", "--detach", "--quiet", publication],
        check=True,
        capture_output=True,
    )

    completed = subprocess.run(
        [
            sys.executable,
            "-I",
            "-S",
            "-B",
            "-c",
            orchestration._P_BOOTSTRAP,
            str(repository),
            generated_at.isoformat(),
        ],
        check=False,
        capture_output=True,
        env=orchestration._FIXED_SUBPROCESS_ENVIRONMENT,
        timeout=120,
    )

    assert completed.returncode == 0, completed.stderr.decode("utf-8", "replace")
    assert completed.stderr == b""
    manifest = orchestration._parse_worker_manifest(completed.stdout)
    orchestration._validate_manifest(manifest, publication=publication)
    workspace = type(
        "Workspace",
        (),
        {"root": repository, "publication_commit": publication},
    )()
    orchestration._validate_module_inventory(workspace, manifest)
    assert "lotto649._live_worker" in {module.name for module in manifest.modules}
    assert all((repository / path).is_file() for path in manifest.paths)
    return repository, manifest


def test_private_worker_outputs_join_real_freeze_with_proven_p_inventory(tmp_path):
    from test_history_execution_handoff import (
        _candidate,
        _open_execution_workspace,
        _write_required_predictions,
        _write_valid_evaluation,
    )

    handoff_root = tmp_path / "handoff"
    handoff_root.mkdir()
    _caller, prepared, receipt, authority = _candidate(handoff_root)
    with _open_execution_workspace(
        receipt,
        authority_url=str(authority),
    ) as workspace:
        generated_at = datetime.combine(
            workspace.history.draws[-1].draw_date + timedelta(days=1),
            datetime.min.time(),
            UTC,
        ).replace(hour=12)
        prediction_paths, prediction_raws = _write_required_predictions(
            workspace,
            generated_at,
        )
        evaluation_path, evaluation_raw = _write_valid_evaluation(workspace)
        evaluations = {evaluation_path: evaluation_raw}
        predictions = dict(zip(prediction_paths, prediction_raws, strict=True))
        expected_raw = {**evaluations, **predictions}
        expected_paths = tuple(sorted(expected_raw))
        for relative in expected_paths:
            (workspace.root / relative).unlink()

        worker_root, manifest = _run_private_worker_fixture(
            tmp_path,
            generated_at=generated_at,
            evaluations=evaluations,
            predictions=predictions,
        )
        assert manifest.paths == expected_paths
        for relative in manifest.paths:
            output = workspace.root / relative
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes((worker_root / relative).read_bytes())

        frozen = orchestration.freeze_execution_outputs(
            workspace,
            manifest.paths,
            created_at=generated_at,
        )

        assert frozen.parent_commit == prepared.publication_commit
        assert frozen.paths == manifest.paths
        assert tuple(file.path for file in frozen.files) == manifest.paths
        assert tuple(file.sha256 for file in frozen.files) == tuple(
            hashlib.sha256(expected_raw[path]).hexdigest() for path in manifest.paths
        )


def test_bounded_worker_kills_stdout_flood_without_retry():
    command = [
        sys.executable,
        "-I",
        "-S",
        "-B",
        "-c",
        "import os; os.write(1, b'x' * (1024 * 1024))",
    ]

    with pytest.raises(
        orchestration.PublishedCodeExecutionError,
        match="exceeded its bound",
    ):
        orchestration._run_bounded_worker(
            command,
            cwd=ROOT,
            env={
                "LANG": "C",
                "LC_ALL": "C",
                "PATH": "/usr/bin:/bin",
                "TMPDIR": "/tmp",
            },
            timeout=10,
        )


def test_bounded_worker_kills_child_and_reraises_base_exception(monkeypatch):
    class Process:
        pid = 123456789
        stdout = io.BytesIO()
        stderr = io.BytesIO()

        def __init__(self):
            self.waits = 0

        def wait(self, timeout=None):
            self.waits += 1
            if self.waits == 1:
                raise KeyboardInterrupt
            return -9

    process = Process()
    killed = []
    monkeypatch.setattr(orchestration.subprocess, "Popen", lambda *_a, **_kw: process)
    monkeypatch.setattr(
        orchestration, "_kill_worker", lambda observed: killed.append(observed)
    )

    with pytest.raises(KeyboardInterrupt):
        orchestration._run_bounded_worker(
            [sys.executable, "-c", "pass"],
            cwd=ROOT,
            env={"PATH": "/usr/bin:/bin"},
            timeout=10,
        )

    assert killed == [process]
    assert process.waits == 2


def test_published_code_rejects_preexisting_python_bytecode(tmp_path):
    source = tmp_path / "src" / "lotto649"
    cache = source / "__pycache__"
    cache.mkdir(parents=True)
    (source / "__init__.py").write_text("", encoding="utf-8")
    (cache / "live.cpython-312.pyc").write_bytes(b"malicious")
    workspace = _workspace(_published_history(_base_history()))
    object.__setattr__(workspace, "root", tmp_path)

    with pytest.raises(
        orchestration.PublishedCodeExecutionError,
        match="forbidden bytecode",
    ):
        orchestration._require_no_lotto649_bytecode(workspace)


@pytest.mark.parametrize("failure", ["nonzero", "stderr", "timeout"])
def test_published_code_transport_failures_are_typed_and_never_retried(
    monkeypatch,
    failure,
):
    history = _published_history(_base_history())
    workspace = _workspace(history)
    calls = 0
    monkeypatch.setattr(
        ExecutionWorkspace,
        "load_config",
        lambda self: {
            "_root": self.root,
            "data": {"refresh_enabled": True},
            "live": {"enabled": True},
        },
    )
    monkeypatch.setattr(
        orchestration,
        "_require_exact_p_worker",
        lambda _workspace, _script: None,
    )
    monkeypatch.setattr(
        orchestration,
        "_require_no_lotto649_bytecode",
        lambda _workspace: None,
    )

    def run(command, **kwargs):
        nonlocal calls
        calls += 1
        if failure == "timeout":
            raise orchestration.PublishedCodeExecutionError("timeout")
        return orchestration._WorkerProcessResult(
            1 if failure == "nonzero" else 0,
            b"",
            b"worker noise" if failure == "stderr" else b"",
        )

    monkeypatch.setattr(orchestration, "_run_bounded_worker", run)
    with pytest.raises(orchestration.PublishedCodeExecutionError):
        orchestration._execute_published_code(
            workspace,
            generated_at=CREATED_AT,
        )

    assert calls == 1


def test_no_direct_worker_tool_or_injectable_orchestration_bypass_exists():
    assert not (ROOT / "tools" / "run_verified_live_outputs.py").exists()
    assert (ROOT / "src" / "lotto649" / "_live_worker.py").is_file()
    assert not hasattr(live, "_run_verified_live_outputs")
    assert not hasattr(orchestration, "_OrchestrationPorts")
    assert not hasattr(orchestration, "_orchestrate_with_ports")


def test_smtp_exception_does_not_block_evaluation_or_prediction(
    tmp_path,
    monkeypatch,
):
    from lotto649.domain import Draw, Prediction

    actual = Draw(orchestration.date(2026, 8, 22), (1, 2, 3, 4, 5, 6), 7)
    prediction = Prediction(
        target_draw_date=actual.draw_date,
        generated_at=datetime(2026, 8, 20, tzinfo=UTC),
        model_name="candidate",
        model_version="v1.0.0",
        probabilities={number: 6 / 49 for number in range(1, 50)},
        top6=[1, 2, 3, 4, 5, 6],
        top12=list(range(1, 13)),
        top18=list(range(1, 19)),
        final_combination=[1, 2, 3, 4, 5, 6],
        metadata={},
    )
    prediction_path = tmp_path / "predictions/2026-08-22__candidate__v1.0.0.json"
    prediction_path.parent.mkdir()
    prediction_path.write_text(
        orchestration.json.dumps(prediction.to_json_dict()),
        encoding="utf-8",
    )
    saved = []
    monkeypatch.setattr(live, "operational_history_provenance", lambda _h: {"p": P})
    monkeypatch.setattr(
        live,
        "evaluation_prediction_source",
        lambda _repository, _publication, _relative: {"kind": "test-fixture"},
    )
    monkeypatch.setattr(live, "should_alert", lambda _ev, _cfg: True)
    monkeypatch.setattr(
        live,
        "send_hit_alert",
        lambda _ev: (_ for _ in ()).throw(OSError("smtp unavailable")),
    )
    monkeypatch.setattr(
        live,
        "save_evaluation",
        lambda _root, evaluation: saved.append(evaluation),
    )

    completed = live._evaluate_due_predictions(
        {
            "_root": tmp_path,
            "notifications": {"enabled": True},
        },
        type(
            "History",
            (),
            {
                "draws": (actual,),
                "registry": type("Registry", (), {"resolved_revision": P})(),
            },
        )(),
    )

    assert completed[0]["email_sent"] is False
    assert saved == completed
