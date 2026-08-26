"""Fail-closed orchestration for one exact GitHub live publication cycle."""

from __future__ import annotations

import hashlib
import json
import os
import re
import signal
import stat
import subprocess
import sys
from threading import Event, Thread
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import yaml

from .config import ROOT as PROJECT_ROOT
from .history_artifact_publication_github import (
    ArtifactPublicationReceipt,
    publish_frozen_execution_artifacts_to_github,
)
from .history_execution_handoff import (
    ExecutionWorkspace,
    FrozenExecutionArtifacts,
    FrozenExecutionFile,
    freeze_execution_outputs,
    open_github_execution_workspace,
)
from .history_publication import (
    RawSource,
    PreparedPublication,
    prepare_history_publication,
)
from .history_publication_cas import (
    CasAck,
    CasStatus,
    PublicationOutcome,
    PublicationReceipt,
)
from .history_publication_github import publish_prepared_history_to_github
from .history_registry import resolve_repository_head
from .live import next_draw_date
from .official_source_collection import (
    OfficialSourceCollection,
    RequestsOfficialSourceHttpClient,
    collect_official_sources,
)
from .notification import (
    PublishedPreDrawRecommendation,
    send_pre_draw_recommendation,
)
from .operational_history import PublishedHistory, load_operational_history

_OID_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_MODULE_NAME_RE = re.compile(r"^lotto649(?:\.[A-Za-z_][A-Za-z0-9_]*)*$")
_MODULE_PATH_RE = re.compile(
    r"^src/lotto649/(?:[A-Za-z_][A-Za-z0-9_]*/)*"
    r"(?:__init__|[A-Za-z_][A-Za-z0-9_]*)\.py$"
)
_OUTPUT_PATH_RE = re.compile(
    r"^(?:evaluations|predictions)/"
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}__"
    r"[A-Za-z0-9][A-Za-z0-9_.-]*__"
    r"[A-Za-z0-9][A-Za-z0-9_.-]*\.json$"
)
_MAX_OUTPUTS = 128
_MAX_MANIFEST_BYTES = 64 * 1024
_MAX_WORKER_BYTES = 256 * 1024
_WORKER_PATH = "src/lotto649/_live_worker.py"
_SMTP_ENVIRONMENT = ("SMTP_PASSWORD", "SMTP_USERNAME")
_DRAW_TIME_ZONE = ZoneInfo("America/Toronto")
_TRUSTED_PATH = "/usr/bin:/bin"
_FIXED_SUBPROCESS_ENVIRONMENT = {
    "GIT_CONFIG_COUNT": "0",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_SYSTEM": os.devnull,
    "GIT_GRAFT_FILE": os.devnull,
    "GIT_NO_LAZY_FETCH": "1",
    "GIT_NO_REPLACE_OBJECTS": "1",
    "LANG": "C",
    "LC_ALL": "C",
    "PATH": _TRUSTED_PATH,
    "TMPDIR": "/tmp",
}
_P_BOOTSTRAP = """\
import pathlib,sys,sysconfig
root=pathlib.Path(sys.argv[1]).resolve(strict=True)
paths=[]
for key in ('purelib','platlib'):
 value=sysconfig.get_path(key)
 if value: paths.append(pathlib.Path(value))
prefix=pathlib.Path(sys.executable).absolute().parent.parent
version=f'python{sys.version_info.major}.{sys.version_info.minor}'
paths.extend((prefix/'lib'/version/'site-packages',prefix/'Lib'/'site-packages'))
for value in paths:
 try: candidate=str(value.resolve(strict=True))
 except OSError: continue
 if candidate not in sys.path: sys.path.append(candidate)
sys.path.insert(0,str((root/'src').resolve(strict=True)))
from lotto649 import _live_worker
raise SystemExit(_live_worker._main(root,sys.argv[2]))
"""


class LiveOrchestrationError(RuntimeError):
    """Raised when cross-stage live-cycle evidence is inconsistent."""


class PublishedCodeExecutionError(LiveOrchestrationError):
    """Raised when exact-P code does not produce a proven output manifest."""


@dataclass(frozen=True)
class LiveCycleReceipt:
    """Complete P/A publication receipts plus the exact committed output paths."""

    history_publication: PublicationReceipt
    artifact_publication: ArtifactPublicationReceipt
    output_paths: tuple[str, ...]
    purchase_recommendation: PublishedPreDrawRecommendation | None
    purchase_recommendation_email_attempted: bool
    purchase_recommendation_email_sent: bool


@dataclass(frozen=True)
class _PublishedModuleIdentity:
    name: str
    path: str
    git_blob: str
    sha256: str


@dataclass(frozen=True)
class _WorkerProcessResult:
    returncode: int
    stdout: bytes
    stderr: bytes


@dataclass(frozen=True)
class _LiveOutputManifest:
    publication_commit: str
    paths: tuple[str, ...]
    modules: tuple[_PublishedModuleIdentity, ...] = ()


def _full_oid(value: object, *, label: str) -> str:
    if type(value) is not str or _OID_RE.fullmatch(value) is None:
        raise LiveOrchestrationError(f"{label} must be a full SHA-1 OID")
    return value


def _utc_second(clock: Callable[[], datetime], *, label: str) -> datetime:
    try:
        value = clock()
        if type(value) is not datetime or value.microsecond != 0:
            raise ValueError("not a whole-second datetime")
        offset = value.utcoffset()
        if offset is None or offset.total_seconds() != 0:
            raise ValueError("not UTC")
    except Exception as exc:
        raise LiveOrchestrationError(
            f"{label} clock must return a whole-second UTC datetime"
        ) from exc
    return value.astimezone(UTC)


def _require_enabled(cfg: object) -> dict[str, Any]:
    if type(cfg) is not dict:
        raise LiveOrchestrationError("live-cycle configuration must be a dictionary")
    live_cfg = cfg.get("live")
    if type(live_cfg) is not dict or live_cfg.get("enabled") is not True:
        raise RuntimeError(
            "live execution is disabled; live.enabled must be explicitly true"
        )
    data_cfg = cfg.get("data")
    if type(data_cfg) is not dict or data_cfg.get("refresh_enabled") is not True:
        raise RuntimeError(
            "data refresh is disabled; data.refresh_enabled must be explicitly true"
        )
    return cfg


def _repository_root(cfg: dict[str, Any]) -> Path:
    raw = cfg.get("_root")
    if not isinstance(raw, (str, Path)):
        raise LiveOrchestrationError("live-cycle repository root is invalid")
    try:
        root = Path(raw).resolve(strict=True)
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        raise LiveOrchestrationError("live-cycle repository root is invalid") from exc
    if not root.is_dir():
        raise LiveOrchestrationError("live-cycle repository root is invalid")
    return root


def _load_production_config() -> dict[str, Any]:
    """Load config from literal B, never from mutable worktree bytes."""

    try:
        root = PROJECT_ROOT.resolve(strict=True)
        head = resolve_repository_head(root)
        raw = _p_git_bytes(root, "cat-file", "blob", f"{head}:config.yaml")
        payload = yaml.safe_load(raw)
    except Exception as exc:
        raise LiveOrchestrationError(
            "production config could not be loaded from literal HEAD"
        ) from exc
    if type(payload) is not dict:
        raise LiveOrchestrationError("production config at literal HEAD is invalid")
    payload["_root"] = root
    payload["_authority_head"] = head
    return payload


def _validate_base_history(history: object) -> tuple[PublishedHistory, str, date]:
    if type(history) is not PublishedHistory or not history.draws:
        raise LiveOrchestrationError("literal HEAD history has the wrong type")
    base = _full_oid(history.registry.resolved_revision, label="literal HEAD")
    if history.registry.requested_revision != base:
        raise LiveOrchestrationError("literal HEAD history revision is inconsistent")
    return history, base, next_draw_date(history.draws[-1].draw_date)


def _valid_publication_outcome(
    *,
    outcome: object,
    observed_before: object,
    expected: str,
    installed: str,
    ack: object,
) -> bool:
    if outcome is PublicationOutcome.ALREADY_PUBLISHED:
        return observed_before == installed and ack is None
    if outcome is PublicationOutcome.ADVANCED:
        return (
            observed_before == expected
            and type(ack) is CasAck
            and ack.status is CasStatus.APPLIED
        )
    if outcome is PublicationOutcome.CONFIRMED_AFTER_REREAD:
        return (
            observed_before == expected
            and type(ack) is CasAck
            and ack.status in {CasStatus.REJECTED, CasStatus.UNKNOWN}
        )
    return False


def _validate_p_receipt(
    receipt: object,
    *,
    prepared: PreparedPublication,
    base_history: PublishedHistory,
) -> PublicationReceipt:
    if type(receipt) is not PublicationReceipt:
        raise LiveOrchestrationError(
            "history publication returned the wrong receipt type"
        )
    if (
        receipt.expected_base != prepared.base_commit
        or receipt.publication_commit != prepared.publication_commit
        or receipt.observed_after != prepared.publication_commit
        or not _valid_publication_outcome(
            outcome=receipt.outcome,
            observed_before=receipt.observed_before,
            expected=prepared.base_commit,
            installed=prepared.publication_commit,
            ack=receipt.cas_ack,
        )
    ):
        raise LiveOrchestrationError("history publication receipt is inconsistent")
    history = receipt.history
    if (
        type(history) is not PublishedHistory
        or history.registry.requested_revision != prepared.publication_commit
        or history.registry.resolved_revision != prepared.publication_commit
        or history.registry.publication_commit != prepared.publication_commit
        or history.registry_transaction.base_commit != prepared.base_commit
        or history.registry_transaction.evidence_commit != prepared.evidence_commit
        or history.registry_transaction.suffix_commit != prepared.suffix_commit
        or history.registry.head_event_sha256 != prepared.registry_head_event_sha256
        or history.registry_suffix.head_event_sha256
        != prepared.suffix_head_event_sha256
        or history.registry_suffix.history_through != prepared.target_draw_date
        or not history.draws
        or history.draws[-1].draw_date != prepared.target_draw_date
        or len(history.draws) != len(base_history.draws) + 1
        or history.draws[:-1] != base_history.draws
        or history.registry_seal != base_history.registry_seal
        or history.base != base_history.base
    ):
        raise LiveOrchestrationError("published P history identity is inconsistent")
    return receipt


def _validate_manifest(
    manifest: object,
    *,
    publication: str,
) -> _LiveOutputManifest:
    if type(manifest) is not _LiveOutputManifest:
        raise PublishedCodeExecutionError(
            "published code returned the wrong manifest type"
        )
    if manifest.publication_commit != publication:
        raise PublishedCodeExecutionError("published code manifest is not bound to P")
    paths = manifest.paths
    if (
        type(paths) is not tuple
        or not paths
        or len(paths) > _MAX_OUTPUTS
        or paths != tuple(sorted(set(paths)))
        or any(
            type(path) is not str or _OUTPUT_PATH_RE.fullmatch(path) is None
            for path in paths
        )
    ):
        raise PublishedCodeExecutionError(
            "published code manifest paths are not exact canonical outputs"
        )
    return manifest


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate manifest key")
        result[key] = value
    return result


def _reject_json_constant(_value: str) -> None:
    raise ValueError("non-finite manifest value")


def _parse_worker_manifest(raw: bytes) -> _LiveOutputManifest:
    if not raw or len(raw) > _MAX_MANIFEST_BYTES:
        raise PublishedCodeExecutionError("published-code manifest size is invalid")
    try:
        payload = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_json_constant,
        )
        canonical = (
            json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            ).encode("utf-8")
            + b"\n"
        )
        if (
            raw != canonical
            or type(payload) is not dict
            or set(payload)
            != {
                "modules",
                "paths",
                "publication_commit",
            }
        ):
            raise ValueError("noncanonical manifest")
        raw_paths = payload["paths"]
        raw_modules = payload["modules"]
        if type(raw_paths) is not list or type(raw_modules) is not list:
            raise ValueError("manifest collections")
        paths = tuple(raw_paths)
        modules = tuple(
            _PublishedModuleIdentity(
                name=entry["name"],
                path=entry["path"],
                git_blob=entry["git_blob"],
                sha256=entry["sha256"],
            )
            for entry in raw_modules
            if type(entry) is dict
            and set(entry) == {"git_blob", "name", "path", "sha256"}
        )
        if len(modules) != len(raw_modules):
            raise ValueError("manifest module entries")
        manifest = _LiveOutputManifest(
            publication_commit=payload["publication_commit"],
            paths=paths,
            modules=modules,
        )
    except (KeyError, RecursionError, TypeError, UnicodeDecodeError, ValueError) as exc:
        raise PublishedCodeExecutionError(
            "published code returned a noncanonical manifest"
        ) from exc
    return manifest


def _p_git_bytes(repository: Path, *arguments: str) -> bytes:
    try:
        completed = subprocess.run(
            [
                "git",
                "-c",
                "advice.graftFileDeprecated=false",
                "-C",
                str(repository),
                *arguments,
            ],
            check=False,
            capture_output=True,
            env=_FIXED_SUBPROCESS_ENVIRONMENT,
            timeout=120,
        )
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        raise PublishedCodeExecutionError(
            "published-code module identity could not be proven from P"
        ) from exc
    if completed.returncode != 0 or completed.stderr:
        raise PublishedCodeExecutionError(
            "published-code module identity could not be proven from P"
        )
    return completed.stdout


def _validate_module_inventory(
    workspace: ExecutionWorkspace,
    manifest: _LiveOutputManifest,
) -> None:
    modules = manifest.modules
    names = tuple(module.name for module in modules)
    paths = tuple(module.path for module in modules)
    if (
        not modules
        or names != tuple(sorted(set(names)))
        or len(set(paths)) != len(paths)
        or not {
            "lotto649",
            "lotto649._live_worker",
            "lotto649.live",
            "lotto649.operational_history",
        }.issubset(names)
    ):
        raise PublishedCodeExecutionError(
            "published-code module inventory is incomplete or noncanonical"
        )
    for module in modules:
        suffix = module.name.removeprefix("lotto649").lstrip(".")
        if suffix:
            stem = suffix.replace(".", "/")
            expected_paths = {
                f"src/lotto649/{stem}.py",
                f"src/lotto649/{stem}/__init__.py",
            }
        else:
            expected_paths = {"src/lotto649/__init__.py"}
        if (
            type(module.name) is not str
            or _MODULE_NAME_RE.fullmatch(module.name) is None
            or type(module.path) is not str
            or _MODULE_PATH_RE.fullmatch(module.path) is None
            or module.path not in expected_paths
            or type(module.git_blob) is not str
            or _OID_RE.fullmatch(module.git_blob) is None
            or type(module.sha256) is not str
            or _SHA256_RE.fullmatch(module.sha256) is None
        ):
            raise PublishedCodeExecutionError(
                "published-code module inventory entry is invalid"
            )
        raw = _p_git_bytes(
            workspace.root,
            "cat-file",
            "blob",
            f"{workspace.publication_commit}:{module.path}",
        )
        listing = _p_git_bytes(
            workspace.root,
            "ls-tree",
            "-z",
            workspace.publication_commit,
            "--",
            module.path,
        )
        expected_listing = f"100644 blob {module.git_blob}\t{module.path}\0".encode(
            "ascii"
        )
        calculated_blob = hashlib.sha1(
            f"blob {len(raw)}\0".encode("ascii") + raw,
            usedforsecurity=False,
        ).hexdigest()
        if (
            listing != expected_listing
            or calculated_blob != module.git_blob
            or hashlib.sha256(raw).hexdigest() != module.sha256
        ):
            raise PublishedCodeExecutionError(
                "published-code module inventory differs from exact P"
            )


def _read_regular_file_no_follow(path: Path, *, maximum: int) -> bytes:
    descriptor: int | None = None
    try:
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_size > maximum:
            raise ValueError("not a bounded regular file")
        raw = os.read(descriptor, maximum + 1)
        after = os.fstat(descriptor)
        current = path.lstat()
    except (OSError, ValueError) as exc:
        raise PublishedCodeExecutionError(
            "published-code worker file is invalid"
        ) from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
    identity = lambda value: (  # noqa: E731 - compact immutable stat projection
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_size,
        value.st_mtime_ns,
    )
    if (
        identity(before) != identity(after)
        or identity(after) != identity(current)
        or len(raw) != before.st_size
        or len(raw) > maximum
    ):
        raise PublishedCodeExecutionError(
            "published-code worker file changed while being verified"
        )
    return raw


def _require_exact_p_worker(
    workspace: ExecutionWorkspace,
    script: Path,
) -> None:
    raw = _read_regular_file_no_follow(script, maximum=_MAX_WORKER_BYTES)
    publication = workspace.publication_commit
    committed = _p_git_bytes(
        workspace.root,
        "cat-file",
        "blob",
        f"{publication}:{_WORKER_PATH}",
    )
    oid = hashlib.sha1(
        f"blob {len(raw)}\0".encode("ascii") + raw,
        usedforsecurity=False,
    ).hexdigest()
    listing = _p_git_bytes(
        workspace.root,
        "ls-tree",
        "-z",
        publication,
        "--",
        _WORKER_PATH,
    )
    if raw != committed or listing != f"100644 blob {oid}\t{_WORKER_PATH}\0".encode(
        "ascii"
    ):
        raise PublishedCodeExecutionError("published-code worker differs from exact P")


def _require_no_lotto649_bytecode(workspace: ExecutionWorkspace) -> None:
    root = workspace.root / "src" / "lotto649"
    pending = [root]
    try:
        while pending:
            directory = pending.pop()
            for entry in os.scandir(directory):
                if entry.is_symlink():
                    raise ValueError("symlink in source tree")
                if entry.is_dir(follow_symlinks=False):
                    if entry.name == "__pycache__":
                        raise ValueError("bytecode cache in source tree")
                    pending.append(Path(entry.path))
                elif entry.name.endswith(".pyc"):
                    raise ValueError("bytecode file in source tree")
    except (OSError, ValueError) as exc:
        raise PublishedCodeExecutionError(
            "published-code source tree contains forbidden bytecode"
        ) from exc


def _kill_worker(process: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except (OSError, ProcessLookupError):
        try:
            process.kill()
        except OSError:
            pass


def _run_bounded_worker(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    timeout: int = 900,
) -> _WorkerProcessResult:
    """Capture a worker without allowing either output pipe to grow unbounded."""

    try:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        raise PublishedCodeExecutionError(
            "published-code worker did not start"
        ) from exc
    assert process.stdout is not None
    assert process.stderr is not None
    overflow = Event()
    buffers = {"stdout": bytearray(), "stderr": bytearray()}

    def read_bounded(label: str, stream) -> None:
        while True:
            chunk = stream.read(8192)
            if not chunk:
                return
            remaining = _MAX_MANIFEST_BYTES + 1 - len(buffers[label])
            if remaining > 0:
                buffers[label].extend(chunk[:remaining])
            if len(buffers[label]) > _MAX_MANIFEST_BYTES:
                overflow.set()
                _kill_worker(process)
                return

    readers = (
        Thread(target=read_bounded, args=("stdout", process.stdout), daemon=True),
        Thread(target=read_bounded, args=("stderr", process.stderr), daemon=True),
    )
    for reader in readers:
        reader.start()
    try:
        returncode = process.wait(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        _kill_worker(process)
        process.wait()
        for reader in readers:
            reader.join(timeout=5)
        raise PublishedCodeExecutionError("published-code worker timed out") from exc
    except BaseException:
        _kill_worker(process)
        try:
            process.wait()
        except BaseException:
            pass
        for reader in readers:
            reader.join(timeout=5)
        raise
    for reader in readers:
        reader.join(timeout=5)
    if any(reader.is_alive() for reader in readers):
        _kill_worker(process)
        process.wait()
        raise PublishedCodeExecutionError("published-code worker output did not close")
    if overflow.is_set():
        raise PublishedCodeExecutionError(
            "published-code worker output exceeded its bound"
        )
    return _WorkerProcessResult(
        returncode=returncode,
        stdout=bytes(buffers["stdout"]),
        stderr=bytes(buffers["stderr"]),
    )


def _normalize_history_to_p(
    history: PublishedHistory, publication: str
) -> PublishedHistory:
    return replace(
        history,
        registry=replace(
            history.registry,
            requested_revision=publication,
            resolved_revision=publication,
        ),
    )


def _validate_artifacts(
    artifacts: object,
    *,
    workspace: ExecutionWorkspace,
    manifest: _LiveOutputManifest,
    created_at: datetime,
) -> FrozenExecutionArtifacts:
    if type(artifacts) is not FrozenExecutionArtifacts:
        raise LiveOrchestrationError("artifact freeze returned the wrong type")
    try:
        repository = artifacts.repository.resolve(strict=True)
        workspace_root = workspace.root.resolve(strict=True)
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        raise LiveOrchestrationError("artifact freeze repository is invalid") from exc
    files = artifacts.files
    if (
        repository != workspace_root
        or artifacts.parent_commit != workspace.publication_commit
        or type(artifacts.artifact_commit) is not str
        or _OID_RE.fullmatch(artifacts.artifact_commit) is None
        or artifacts.paths != manifest.paths
        or artifacts.created_at != created_at
        or type(files) is not tuple
        or any(type(file) is not FrozenExecutionFile for file in files)
        or tuple(file.path for file in files) != manifest.paths
    ):
        raise LiveOrchestrationError("artifact freeze identity is inconsistent")
    return artifacts


def _load_frozen_purchase_recommendation(
    artifacts: FrozenExecutionArtifacts,
    *,
    workspace: ExecutionWorkspace,
) -> PublishedPreDrawRecommendation | None:
    prediction_paths = tuple(
        path for path in artifacts.paths if path.startswith("predictions/")
    )
    if not prediction_paths:
        return None
    try:
        raw_config = _p_git_bytes(
            workspace.root,
            "cat-file",
            "blob",
            f"{workspace.publication_commit}:config.yaml",
        )
        config = yaml.safe_load(raw_config)
        project = config["project"]
        live_config = config["live"]
        version = project["model_version"]
        models = live_config["models"]
        shadow_models = live_config["shadow_models"]
        if (
            type(config) is not dict
            or type(project) is not dict
            or type(live_config) is not dict
            or type(version) is not str
            or type(models) is not list
            or any(type(model) is not str for model in models)
            or len(models) != len(set(models))
            or "ensemble" not in models
            or type(shadow_models) is not list
            or any(type(model) is not str for model in shadow_models)
            or "ensemble" in shadow_models
            or not workspace.history.draws
        ):
            raise ValueError("configured recommendation identity")
        target = next_draw_date(workspace.history.draws[-1].draw_date)
        relative = f"predictions/{target.isoformat()}__ensemble__{version}.json"
        if relative not in prediction_paths:
            raise ValueError("ensemble prediction is absent")
        frozen_files = tuple(file for file in artifacts.files if file.path == relative)
        if len(frozen_files) != 1:
            raise ValueError("ensemble frozen identity")
        frozen = frozen_files[0]
        raw = _p_git_bytes(
            artifacts.repository,
            "cat-file",
            "blob",
            f"{artifacts.artifact_commit}:{relative}",
        )
        listing = _p_git_bytes(
            artifacts.repository,
            "ls-tree",
            "-z",
            artifacts.artifact_commit,
            "--",
            relative,
        )
        calculated_blob = hashlib.sha1(
            f"blob {len(raw)}\0".encode("ascii") + raw,
            usedforsecurity=False,
        ).hexdigest()
        if (
            len(raw) != frozen.bytes
            or hashlib.sha256(raw).hexdigest() != frozen.sha256
            or calculated_blob != frozen.git_blob
            or listing != f"100644 blob {frozen.git_blob}\t{relative}\0".encode("ascii")
        ):
            raise ValueError("ensemble artifact bytes")
        payload = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_json_constant,
        )
        expected_keys = {
            "final_combination",
            "generated_at",
            "metadata",
            "model_name",
            "model_version",
            "probabilities",
            "target_draw_date",
            "top6",
            "top12",
            "top18",
        }
        metadata = payload["metadata"]
        final = payload["final_combination"]
        generated_at = datetime.fromisoformat(payload["generated_at"])
        if (
            type(payload) is not dict
            or set(payload) != expected_keys
            or payload["target_draw_date"] != target.isoformat()
            or payload["model_name"] != "ensemble"
            or payload["model_version"] != version
            or type(metadata) is not dict
            or metadata.get("role") != "primary"
            or type(final) is not list
            or len(final) != 6
            or any(type(number) is not int for number in final)
        ):
            raise ValueError("ensemble prediction payload")
        return PublishedPreDrawRecommendation(
            target_draw_date=target,
            generated_at=generated_at,
            model_name="ensemble",
            model_version=version,
            final_combination=tuple(final),
            snapshot_path=relative,
            snapshot_sha256=frozen.sha256,
            artifact_commit=artifacts.artifact_commit,
        )
    except (
        KeyError,
        OSError,
        OverflowError,
        PublishedCodeExecutionError,
        RecursionError,
        TypeError,
        UnicodeError,
        ValueError,
    ) as exc:
        raise LiveOrchestrationError(
            "published ensemble recommendation is invalid"
        ) from exc


def _validate_a_receipt(
    receipt: object,
    *,
    artifacts: FrozenExecutionArtifacts,
    p_history: PublishedHistory,
) -> ArtifactPublicationReceipt:
    if type(receipt) is not ArtifactPublicationReceipt:
        raise LiveOrchestrationError(
            "artifact publication returned the wrong receipt type"
        )
    if (
        receipt.expected_parent != artifacts.parent_commit
        or receipt.artifact_commit != artifacts.artifact_commit
        or receipt.observed_after != artifacts.artifact_commit
        or not _valid_publication_outcome(
            outcome=receipt.outcome,
            observed_before=receipt.observed_before,
            expected=artifacts.parent_commit,
            installed=artifacts.artifact_commit,
            ack=receipt.cas_ack,
        )
    ):
        raise LiveOrchestrationError("artifact publication receipt is inconsistent")
    history = receipt.history
    if (
        type(history) is not PublishedHistory
        or history.registry.requested_revision != artifacts.artifact_commit
        or history.registry.resolved_revision != artifacts.artifact_commit
        or history.registry.publication_commit != artifacts.parent_commit
        or _normalize_history_to_p(history, artifacts.parent_commit) != p_history
    ):
        raise LiveOrchestrationError("artifact publication history differs from P")
    return receipt


def _trusted_utc_now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def orchestrate_github_live_cycle(*, token: str) -> LiveCycleReceipt:
    """Run the sole fixed production B/E/S/P/A state machine."""

    cfg = _load_production_config()
    enabled_cfg = _require_enabled(cfg)
    if type(token) is not str or not token:
        raise LiveOrchestrationError("GitHub token must be a nonempty string")
    root = _repository_root(enabled_cfg)
    base_history, base, target = _validate_base_history(
        load_operational_history(enabled_cfg)
    )
    if enabled_cfg.get("_authority_head") != base:
        raise LiveOrchestrationError(
            "production config and operational history resolved different B commits"
        )
    http_client = RequestsOfficialSourceHttpClient()
    collection = collect_official_sources(
        target,
        http_client=http_client,
        clock=_trusted_utc_now,
    )
    if (
        type(collection) is not OfficialSourceCollection
        or type(collection.sources) is not tuple
        or len(collection.sources) != 2
        or any(type(source) is not RawSource for source in collection.sources)
    ):
        raise LiveOrchestrationError("official collection returned the wrong type")
    collection_time = _utc_second(
        lambda: collection.completed_at,
        label="source collection",
    )
    prepared = prepare_history_publication(
        root,
        expected_base_commit=base,
        sources=collection.sources,
        created_at=collection_time,
    )
    if (
        type(prepared) is not PreparedPublication
        or prepared.repository.resolve(strict=True) != root
        or prepared.base_commit != base
        or prepared.target_draw_date != target
    ):
        raise LiveOrchestrationError("prepared B/E/S/P identity is inconsistent")
    p_receipt = _validate_p_receipt(
        publish_prepared_history_to_github(prepared, token=token),
        prepared=prepared,
        base_history=base_history,
    )
    with open_github_execution_workspace(p_receipt) as workspace:
        if (
            type(workspace) is not ExecutionWorkspace
            or workspace.publication_commit != prepared.publication_commit
            or workspace.history != p_receipt.history
        ):
            raise LiveOrchestrationError("execution workspace differs from P")
        generated_at = _utc_second(
            _trusted_utc_now,
            label="published-code execution",
        )
        if generated_at < collection_time:
            raise LiveOrchestrationError(
                "published-code execution predates source collection"
            )
        manifest = _validate_manifest(
            _execute_published_code(workspace, generated_at=generated_at),
            publication=prepared.publication_commit,
        )
        artifact_time = _utc_second(_trusted_utc_now, label="artifact freeze")
        if artifact_time < generated_at:
            raise LiveOrchestrationError("artifact clock moved backwards")
        artifacts = _validate_artifacts(
            freeze_execution_outputs(
                workspace,
                manifest.paths,
                created_at=artifact_time,
            ),
            workspace=workspace,
            manifest=manifest,
            created_at=artifact_time,
        )
        recommendation = _load_frozen_purchase_recommendation(
            artifacts,
            workspace=workspace,
        )
        a_receipt = _validate_a_receipt(
            publish_frozen_execution_artifacts_to_github(artifacts, token=token),
            artifacts=artifacts,
            p_history=p_receipt.history,
        )
        recommendation_email_attempted = False
        recommendation_email_sent = False
        if (
            recommendation is not None
            and a_receipt.outcome is not PublicationOutcome.ALREADY_PUBLISHED
        ):
            notification_time = _utc_second(
                _trusted_utc_now,
                label="pre-draw recommendation",
            )
            if (
                notification_time.astimezone(_DRAW_TIME_ZONE).date()
                < recommendation.target_draw_date
            ):
                recommendation_email_attempted = True
                try:
                    recommendation_email_sent = send_pre_draw_recommendation(
                        recommendation
                    )
                except Exception:  # noqa: BLE001 - never replay a published ticket
                    recommendation_email_sent = False
        return LiveCycleReceipt(
            history_publication=p_receipt,
            artifact_publication=a_receipt,
            output_paths=manifest.paths,
            purchase_recommendation=recommendation,
            purchase_recommendation_email_attempted=recommendation_email_attempted,
            purchase_recommendation_email_sent=recommendation_email_sent,
        )


def _execute_published_code(
    workspace: ExecutionWorkspace,
    *,
    generated_at: datetime,
) -> _LiveOutputManifest:
    if type(workspace) is not ExecutionWorkspace:
        raise PublishedCodeExecutionError("published-code workspace has the wrong type")
    instant = _utc_second(lambda: generated_at, label="published-code execution")
    try:
        p_config = workspace.load_config()
        _require_enabled(p_config)
    except Exception as exc:
        raise PublishedCodeExecutionError(
            "published-code workspace failed its pre-execution P revalidation"
        ) from exc
    try:
        root = workspace.root.resolve(strict=True)
        script = root / _WORKER_PATH
        script_stat = script.lstat()
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        raise PublishedCodeExecutionError(
            "published-code worker is unavailable from P"
        ) from exc
    if not stat.S_ISREG(script_stat.st_mode) or script.is_symlink():
        raise PublishedCodeExecutionError("published-code worker is unavailable from P")
    _require_exact_p_worker(workspace, script)
    _require_no_lotto649_bytecode(workspace)
    environment = {
        **_FIXED_SUBPROCESS_ENVIRONMENT,
        **{
            key: value
            for key in _SMTP_ENVIRONMENT
            if type((value := os.environ.get(key))) is str and value
        },
    }
    command = [
        sys.executable,
        "-I",
        "-S",
        "-B",
        "-c",
        _P_BOOTSTRAP,
        str(root),
        instant.isoformat(),
    ]
    completed = _run_bounded_worker(
        command,
        cwd=root,
        env=environment,
        timeout=900,
    )
    if (
        len(completed.stdout) > _MAX_MANIFEST_BYTES
        or len(completed.stderr) > _MAX_MANIFEST_BYTES
        or completed.returncode != 0
        or completed.stderr
    ):
        raise PublishedCodeExecutionError(
            "published-code worker did not return a clean success"
        )
    manifest = _parse_worker_manifest(completed.stdout)
    _validate_module_inventory(workspace, manifest)
    _require_exact_p_worker(workspace, script)
    _require_no_lotto649_bytecode(workspace)
    return manifest
