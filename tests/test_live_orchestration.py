from __future__ import annotations

from contextlib import contextmanager
from dataclasses import replace
from datetime import UTC, datetime
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


def _fixture_ports(events: list[str]):
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

    return orchestration._OrchestrationPorts(
        load_history=load,
        collect_sources=collect,
        prepare_history=prepare,
        publish_history=publish_history,
        open_workspace=open_workspace,
        execute_published_code=execute,
        freeze_outputs=freeze,
        publish_artifacts=publish_artifacts,
    )


def test_full_cycle_success_preserves_order_and_context_through_a_publication():
    events: list[str] = []
    ports = _fixture_ports(events)
    cfg = {
        "_root": ROOT,
        "data": {"refresh_enabled": True},
        "live": {"enabled": True},
    }

    receipt = orchestration._orchestrate_with_ports(
        cfg,
        token="secret",
        clock=lambda: CREATED_AT,
        ports=ports,
    )

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


def test_p_side_live_seam_returns_exact_sorted_paths_and_uses_supplied_instant(
    monkeypatch,
):
    history = _base_history()
    generated_at = datetime(2026, 8, 24, 12, tzinfo=UTC)
    observed: list[datetime] = []
    evaluation = {
        "target_draw_date": "2026-08-22",
        "model_name": "zeta",
        "model_version": "v1.0.0",
    }

    monkeypatch.setattr(
        live,
        "_evaluate_due_predictions",
        lambda _cfg, _history: [evaluation],
    )

    def generate(_cfg, _history, *, generated_at):
        observed.append(generated_at)
        return [
            ROOT / "predictions/2026-08-26__alpha__v1.0.0.json",
        ]

    monkeypatch.setattr(live, "_generate_next_predictions", generate)

    paths = live._run_verified_live_outputs(
        {
            "_root": ROOT,
            "data": {"refresh_enabled": True},
            "live": {"enabled": True},
        },
        history,
        generated_at=generated_at,
    )

    assert paths == (
        "evaluations/2026-08-22__zeta__v1.0.0.json",
        "predictions/2026-08-26__alpha__v1.0.0.json",
    )
    assert observed == [generated_at]


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
        str(ROOT / "tools/run_verified_live_outputs.py"),
        "--generated-at",
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


def test_committed_false_gates_disconnect_public_wrapper(monkeypatch):
    reached = []

    def forbidden():
        reached.append("adapter")
        raise AssertionError("network adapter reached")

    monkeypatch.setattr(orchestration, "RequestsOfficialSourceHttpClient", forbidden)

    with pytest.raises(RuntimeError, match="live execution is disabled"):
        orchestration.orchestrate_github_live_cycle(token="unused-secret")

    assert reached == []


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
    script = repository / "tools" / "run_verified_live_outputs.py"
    script.parent.mkdir(parents=True)
    script.write_bytes(b"print('reviewed')\n")
    subprocess.run(
        ["git", "init", "--quiet", str(repository)],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(repository), "add", "tools/run_verified_live_outputs.py"],
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
        ("collect_sources", ["load-B", "failed"]),
        ("publish_history", ["collect", "prepare", "failed"]),
        ("execute_published_code", ["context-enter", "failed", "context-exit"]),
        ("publish_artifacts", ["freeze-A", "failed", "context-exit"]),
    ],
)
def test_failure_truncates_cycle_without_retry_and_closes_post_p_context(
    stage,
    expected_tail,
):
    events: list[str] = []
    ports = _fixture_ports(events)
    original = getattr(ports, stage)
    calls = 0

    def fail(*args, **kwargs):
        nonlocal calls
        calls += 1
        events.append("failed")
        raise _StageFailure(stage)

    ports = replace(ports, **{stage: fail})
    cfg = {
        "_root": ROOT,
        "data": {"refresh_enabled": True},
        "live": {"enabled": True},
    }

    with pytest.raises(_StageFailure, match=stage):
        orchestration._orchestrate_with_ports(
            cfg,
            token="secret",
            clock=lambda: CREATED_AT,
            ports=ports,
        )

    assert calls == 1
    assert events[-len(expected_tail) :] == expected_tail
    if stage != "publish_artifacts":
        assert "publish-A" not in events
    assert original is not fail


def test_p_receipt_mismatch_stops_before_execution_context():
    events: list[str] = []
    ports = _fixture_ports(events)
    publish = ports.publish_history

    def mismatch(*args, **kwargs):
        receipt = publish(*args, **kwargs)
        return replace(receipt, expected_base="f" * 40)

    ports = replace(ports, publish_history=mismatch)
    with pytest.raises(
        orchestration.LiveOrchestrationError,
        match="receipt is inconsistent",
    ):
        orchestration._orchestrate_with_ports(
            {
                "_root": ROOT,
                "data": {"refresh_enabled": True},
                "live": {"enabled": True},
            },
            token="secret",
            clock=lambda: CREATED_AT,
            ports=ports,
        )

    assert "context-enter" not in events


def test_prediction_clock_cannot_predate_collected_draw_or_publication():
    events: list[str] = []
    ports = _fixture_ports(events)
    too_early = datetime(2026, 8, 27, 9, tzinfo=UTC)

    with pytest.raises(
        orchestration.LiveOrchestrationError,
        match="predates source collection",
    ):
        orchestration._orchestrate_with_ports(
            {
                "_root": ROOT,
                "data": {"refresh_enabled": True},
                "live": {"enabled": True},
            },
            token="secret",
            clock=lambda: too_early,
            ports=ports,
        )

    assert events[-2:] == ["context-enter", "context-exit"]
    assert "execute-P" not in events


def test_a_receipt_history_mismatch_closes_context_and_returns_no_success():
    events: list[str] = []
    ports = _fixture_ports(events)
    publish = ports.publish_artifacts

    def mismatch(*args, **kwargs):
        receipt = publish(*args, **kwargs)
        bad_history = replace(receipt.history, draws=receipt.history.draws[:-1])
        return replace(receipt, history=bad_history)

    ports = replace(ports, publish_artifacts=mismatch)
    with pytest.raises(
        orchestration.LiveOrchestrationError,
        match="history differs from P",
    ):
        orchestration._orchestrate_with_ports(
            {
                "_root": ROOT,
                "data": {"refresh_enabled": True},
                "live": {"enabled": True},
            },
            token="secret",
            clock=lambda: CREATED_AT,
            ports=ports,
        )

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
    worker = ROOT / "tools" / "run_verified_live_outputs.py"
    code = "\n".join(
        (
            "import importlib.util, sys",
            f"spec = importlib.util.spec_from_file_location('worker', {str(worker)!r})",
            "module = importlib.util.module_from_spec(spec)",
            "spec.loader.exec_module(module)",
            "for value in module._dependency_paths(): sys.path.append(value)",
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
