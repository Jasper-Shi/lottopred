"""Create an isolated execution checkout at a proven history publication."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import stat
import subprocess
import tempfile
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime, timedelta
from itertools import islice
from pathlib import Path
from zoneinfo import ZoneInfo

from .config import load_config as _load_project_config
from .domain import Prediction
from .evaluation import evaluate_prediction
from .history_publication_cas import (
    CasAck,
    CasStatus,
    PublicationOutcome,
    PublicationReceipt,
)
from .history_publication_github import PRODUCTION_GITHUB_REPOSITORY
from .operational_history import (
    PublishedHistory,
    load_operational_history,
    load_published_history,
    operational_history_provenance,
)

_MAIN_REF = "refs/heads/main"
_FETCHED_MAIN_REF = "refs/remotes/history-authority/main"
_OID_RE = re.compile(r"^[0-9a-f]{40}$")
_OUTPUT_PATH_RE = re.compile(
    r"^(?P<directory>evaluations|predictions)/"
    r"(?P<draw_date>[0-9]{4}-[0-9]{2}-[0-9]{2})__"
    r"(?P<model_name>[A-Za-z0-9][A-Za-z0-9_.-]*)__"
    r"(?P<model_version>[A-Za-z0-9][A-Za-z0-9_.-]*)\.json$"
)
_OUTPUT_COMPONENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
_MAX_OUTPUTS = 128
_MAX_OUTPUT_BYTES = 2 * 1024 * 1024
_PRODUCTION_AUTHORITY_URL = (
    f"https://github.com/{PRODUCTION_GITHUB_REPOSITORY.full_name}.git"
)
_INHERITED_ENVIRONMENT = {
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
    "PATH",
    "SYSTEMROOT",
    "TEMP",
    "TMP",
    "TMPDIR",
}
_DRAW_TIME_ZONE = ZoneInfo("America/Toronto")
_PREDICTION_KEYS = {
    "final_combination",
    "generated_at",
    "metadata",
    "model_name",
    "model_version",
    "probabilities",
    "target_draw_date",
    "top12",
    "top18",
    "top6",
}


class HistoryExecutionHandoffError(RuntimeError):
    """Raised when an exact detached publication checkout cannot be proven."""


@dataclass(frozen=True)
class _WorkspaceBinding:
    """Private binding between one handoff checkout and its publication."""

    root: Path
    root_device: int
    root_inode: int
    git_device: int
    git_inode: int
    objects_device: int
    objects_inode: int
    publication_commit: str


_WORKSPACE_CAPABILITIES: dict[object, _WorkspaceBinding] = {}


@dataclass(frozen=True, init=False)
class ExecutionWorkspace:
    """Temporary clean checkout whose sole starting parent is publication P."""

    root: Path
    publication_commit: str
    history: PublishedHistory
    _capability: object = field(repr=False, compare=False)

    def __init__(
        self,
        *,
        root: Path,
        publication_commit: str,
        history: PublishedHistory,
        _capability: object,
    ) -> None:
        if (
            type(_capability) is not object
            or _capability not in _WORKSPACE_CAPABILITIES
        ):
            raise HistoryExecutionHandoffError(
                "execution workspace requires the handoff capability"
            )
        object.__setattr__(self, "root", root)
        object.__setattr__(self, "publication_commit", publication_commit)
        object.__setattr__(self, "history", history)
        object.__setattr__(self, "_capability", _capability)

    def load_config(self) -> dict[str, object]:
        """Load an independent configuration from the authenticated P tree."""

        _require_workspace_capability(self)
        _require_repository_integrity(self.root, self.publication_commit)
        _require_clean_detached_workspace(self.root, self.publication_commit)
        _require_exact_workspace_history(self)
        _require_final_workspace_controls(self)
        try:
            config = _load_project_config(self.root / "config.yaml")
        except Exception as exc:
            raise HistoryExecutionHandoffError(
                "execution workspace configuration could not be loaded from P"
            ) from exc
        if type(config) is not dict:
            raise HistoryExecutionHandoffError(
                "execution workspace configuration is malformed"
            )
        config["_root"] = self.root
        return config


@dataclass(frozen=True)
class FrozenExecutionFile:
    """Exact identity of one immutable file installed in artifact commit A."""

    path: str
    bytes: int
    sha256: str
    git_blob: str


@dataclass(frozen=True)
class FrozenExecutionArtifacts:
    """Unattached exact artifact commit whose sole parent is publication P."""

    repository: Path
    parent_commit: str
    tree_oid: str
    artifact_commit: str
    paths: tuple[str, ...]
    files: tuple[FrozenExecutionFile, ...]
    created_at: datetime


@dataclass(frozen=True)
class _OutputIdentity:
    directory: str
    draw_date: date
    model_name: str
    model_version: str


@dataclass(frozen=True)
class _OutputSnapshot:
    path: str
    raw: bytes
    payload: dict[str, object]


def _git_environment() -> dict[str, str]:
    environment = {
        key: value for key, value in os.environ.items() if key in _INHERITED_ENVIRONMENT
    }
    environment.update(
        {
            "GIT_CONFIG_COUNT": "0",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_SYSTEM": os.devnull,
            "GIT_GRAFT_FILE": os.devnull,
            "GIT_NO_LAZY_FETCH": "1",
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_TERMINAL_PROMPT": "0",
            "LANG": "C",
            "LC_ALL": "C",
        }
    )
    return environment


def _git(
    repository: Path | None,
    *arguments: str,
    input_bytes: bytes | None = None,
    check: bool = True,
    environment_overrides: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[bytes]:
    command = [
        "git",
        "-c",
        "core.hooksPath=/dev/null",
        "-c",
        "core.fsmonitor=false",
        "-c",
        "core.splitIndex=false",
        "-c",
        "core.untrackedCache=false",
        "-c",
        "index.sparse=false",
        "-c",
        "core.autocrlf=false",
        "-c",
        "submodule.recurse=false",
        "-c",
        "i18n.commitEncoding=UTF-8",
        "-c",
        "credential.helper=",
        "-c",
        "http.followRedirects=false",
        "-c",
        "protocol.version=2",
        "-c",
        f"fsck.skipList={os.devnull}",
    ]
    if repository is not None:
        command.extend(["-C", str(repository)])
    command.extend(arguments)
    try:
        environment = _git_environment()
        if environment_overrides is not None:
            environment.update(environment_overrides)
        return subprocess.run(
            command,
            check=check,
            capture_output=True,
            input=input_bytes,
            env=environment,
            timeout=120,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise HistoryExecutionHandoffError(
            "execution workspace Git operation failed"
        ) from exc


def _full_oid(value: object, *, label: str) -> str:
    if type(value) is not str or _OID_RE.fullmatch(value) is None:
        raise HistoryExecutionHandoffError(f"{label} must be a full SHA-1 OID")
    return value


def _validate_receipt(receipt: PublicationReceipt) -> tuple[str, str]:
    if type(receipt) is not PublicationReceipt:
        raise HistoryExecutionHandoffError("publication receipt has the wrong type")
    base = _full_oid(receipt.expected_base, label="publication base")
    publication = _full_oid(
        receipt.publication_commit,
        label="publication commit",
    )
    observed_after = _full_oid(
        receipt.observed_after,
        label="receipt observed-after commit",
    )
    if observed_after != publication:
        raise HistoryExecutionHandoffError("publication receipt did not observe P")
    if receipt.outcome is PublicationOutcome.ALREADY_PUBLISHED:
        observed_before = _full_oid(
            receipt.observed_before,
            label="receipt observed-before commit",
        )
        if observed_before != publication or receipt.cas_ack is not None:
            raise HistoryExecutionHandoffError(
                "already-published receipt is internally inconsistent"
            )
    elif receipt.outcome is PublicationOutcome.ADVANCED:
        observed_before = _full_oid(
            receipt.observed_before,
            label="receipt observed-before commit",
        )
        if (
            observed_before != base
            or type(receipt.cas_ack) is not CasAck
            or type(receipt.cas_ack.status) is not CasStatus
            or receipt.cas_ack.status is not CasStatus.APPLIED
        ):
            raise HistoryExecutionHandoffError(
                "advanced publication receipt is internally inconsistent"
            )
    elif receipt.outcome is PublicationOutcome.CONFIRMED_AFTER_REREAD:
        observed_before = _full_oid(
            receipt.observed_before,
            label="receipt observed-before commit",
        )
        if (
            observed_before != base
            or type(receipt.cas_ack) is not CasAck
            or type(receipt.cas_ack.status) is not CasStatus
            or receipt.cas_ack.status not in {CasStatus.REJECTED, CasStatus.UNKNOWN}
        ):
            raise HistoryExecutionHandoffError(
                "confirmed publication receipt is internally inconsistent"
            )
    else:
        raise HistoryExecutionHandoffError("publication receipt outcome is invalid")
    history = receipt.history
    if (
        type(history) is not PublishedHistory
        or history.registry.resolved_revision != publication
        or history.registry.publication_commit != publication
        or history.registry_transaction.base_commit != base
        or not history.draws
        or history.draws[-1].draw_date != history.registry_suffix.history_through
    ):
        raise HistoryExecutionHandoffError(
            "publication receipt history identity is invalid"
        )
    return base, publication


def _require_plain_history_tree(repository: Path, publication: str) -> None:
    listing = _git(repository, "ls-tree", "-r", "-z", publication).stdout
    for entry in listing.split(b"\0"):
        if not entry:
            continue
        try:
            metadata, raw_path = entry.split(b"\t", 1)
            mode, object_type, _oid = metadata.split(b" ", 2)
        except ValueError as exc:
            raise HistoryExecutionHandoffError(
                "publication tree listing is malformed"
            ) from exc
        if mode == b"160000" or object_type == b"commit":
            raise HistoryExecutionHandoffError(
                "execution publication may not contain Git submodules"
            )
        if raw_path == b".gitmodules" or b"/.gitmodules" in raw_path:
            raise HistoryExecutionHandoffError(
                "execution publication may not contain .gitmodules"
            )
        if object_type != b"blob" or mode not in {b"100644", b"100755"}:
            raise HistoryExecutionHandoffError(
                "execution publication tree must contain only regular files"
            )


def _require_regular_tree(path: Path) -> None:
    try:
        entries = tuple(os.scandir(path))
    except OSError as exc:
        raise HistoryExecutionHandoffError(
            "execution repository object store is unreadable"
        ) from exc
    for entry in entries:
        if entry.is_symlink():
            raise HistoryExecutionHandoffError(
                "execution repository must be self-contained"
            )
        if entry.is_dir(follow_symlinks=False):
            _require_regular_tree(Path(entry.path))
        elif not entry.is_file(follow_symlinks=False):
            raise HistoryExecutionHandoffError(
                "execution repository must contain only regular Git objects"
            )


def _require_self_contained_repository(repository: Path) -> None:
    git_directory = repository / ".git"
    objects = git_directory / "objects"
    try:
        if git_directory.is_symlink() or not git_directory.is_dir():
            raise HistoryExecutionHandoffError(
                "execution repository must be self-contained"
            )
        if objects.is_symlink() or not objects.is_dir():
            raise HistoryExecutionHandoffError(
                "execution repository must be self-contained"
            )
        for relative in (
            "objects/info/alternates",
            "objects/info/http-alternates",
            "shallow",
        ):
            if os.path.lexists(git_directory / relative):
                raise HistoryExecutionHandoffError(
                    "execution repository must be self-contained"
                )
    except OSError as exc:
        raise HistoryExecutionHandoffError(
            "execution repository controls are unreadable"
        ) from exc
    _require_regular_tree(git_directory)
    if tuple(objects.glob("pack/*.promisor")):
        raise HistoryExecutionHandoffError(
            "execution repository must be self-contained"
        )
    absolute_git_directory = (
        _git(repository, "rev-parse", "--absolute-git-dir")
        .stdout.decode("utf-8")
        .strip()
    )
    if Path(absolute_git_directory).resolve() != git_directory.resolve():
        raise HistoryExecutionHandoffError(
            "execution repository must be self-contained"
        )
    common_raw = (
        _git(repository, "rev-parse", "--git-common-dir").stdout.decode("utf-8").strip()
    )
    common = Path(common_raw)
    if not common.is_absolute():
        common = repository / common
    if common.resolve() != git_directory.resolve():
        raise HistoryExecutionHandoffError(
            "execution repository must be self-contained"
        )
    object_format = (
        _git(repository, "rev-parse", "--show-object-format")
        .stdout.decode("ascii")
        .strip()
    )
    if object_format != "sha1":
        raise HistoryExecutionHandoffError(
            "execution repository must use SHA-1 Git objects"
        )
    config_names = (
        _git(
            repository,
            "config",
            "--local",
            "--no-includes",
            "--name-only",
            "--list",
        )
        .stdout.decode("utf-8")
        .splitlines()
    )
    lowered = tuple(name.lower() for name in config_names)
    if any(
        name.startswith(
            ("include.", "includeif.", "fsck.", "filter.", "url.", "credential.")
        )
        or name == "http.followredirects"
        or name == "extensions.partialclone"
        or (name.startswith("remote.") and name.endswith(".promisor"))
        or (name.startswith("remote.") and name.endswith(".partialclonefilter"))
        for name in lowered
    ):
        raise HistoryExecutionHandoffError(
            "execution repository must be self-contained"
        )


def _require_repository_integrity(repository: Path, revision: str) -> None:
    _require_self_contained_repository(repository)
    shallow = (
        _git(repository, "rev-parse", "--is-shallow-repository")
        .stdout.decode("ascii")
        .strip()
    )
    if shallow != "false":
        raise HistoryExecutionHandoffError(
            "execution workspace history must be complete"
        )
    _git(repository, "fsck", "--full", "--no-dangling", revision)
    _require_plain_history_tree(repository, revision)


def _require_clean_detached_workspace(
    repository: Path,
    publication: str,
) -> None:
    observed = _git(repository, "rev-parse", "HEAD").stdout.decode("ascii").strip()
    if observed != publication:
        raise HistoryExecutionHandoffError("execution workspace is not at P")
    symbolic = _git(repository, "symbolic-ref", "-q", "HEAD", check=False)
    if symbolic.returncode != 1 or symbolic.stdout or symbolic.stderr:
        raise HistoryExecutionHandoffError(
            "execution workspace HEAD must be detached at P"
        )
    if _git(repository, "status", "--porcelain=v1", "-z").stdout:
        raise HistoryExecutionHandoffError("execution workspace is not clean")
    expected_tree = _git(repository, "rev-parse", f"{publication}^{{tree}}").stdout
    if _git(repository, "write-tree").stdout != expected_tree:
        raise HistoryExecutionHandoffError(
            "execution workspace index is not the publication tree"
        )


def _require_workspace_capability(workspace: ExecutionWorkspace) -> None:
    if type(workspace) is not ExecutionWorkspace:
        raise HistoryExecutionHandoffError(
            "execution workspace does not carry the handoff capability"
        )
    try:
        binding = _WORKSPACE_CAPABILITIES.get(workspace._capability)
    except TypeError as exc:
        raise HistoryExecutionHandoffError(
            "execution workspace does not carry the handoff capability"
        ) from exc
    try:
        canonical_root = workspace.root.resolve(strict=True)
        root_stat = canonical_root.stat(follow_symlinks=False)
        git_stat = (canonical_root / ".git").stat(follow_symlinks=False)
        objects_stat = (canonical_root / ".git" / "objects").stat(follow_symlinks=False)
    except (OSError, RuntimeError, TypeError) as exc:
        raise HistoryExecutionHandoffError(
            "execution workspace does not carry the handoff capability"
        ) from exc
    if (
        binding is None
        or not stat.S_ISDIR(root_stat.st_mode)
        or not stat.S_ISDIR(git_stat.st_mode)
        or not stat.S_ISDIR(objects_stat.st_mode)
        or canonical_root != binding.root
        or root_stat.st_dev != binding.root_device
        or root_stat.st_ino != binding.root_inode
        or git_stat.st_dev != binding.git_device
        or git_stat.st_ino != binding.git_inode
        or objects_stat.st_dev != binding.objects_device
        or objects_stat.st_ino != binding.objects_inode
        or workspace.publication_commit != binding.publication_commit
    ):
        raise HistoryExecutionHandoffError(
            "execution workspace does not carry the handoff capability"
        )


def _require_final_workspace_controls(workspace: ExecutionWorkspace) -> None:
    """Recheck local controls after the last Git consumer in an operation."""

    _require_regular_tree(workspace.root / ".git")
    _require_workspace_capability(workspace)


def _workspace_binding(
    root: Path,
    publication_commit: str,
) -> _WorkspaceBinding:
    try:
        canonical_root = root.resolve(strict=True)
        root_stat = canonical_root.stat(follow_symlinks=False)
        git_stat = (canonical_root / ".git").stat(follow_symlinks=False)
        objects_stat = (canonical_root / ".git" / "objects").stat(follow_symlinks=False)
    except (OSError, RuntimeError, TypeError) as exc:
        raise HistoryExecutionHandoffError(
            "execution workspace capability could not be issued"
        ) from exc
    if not all(
        stat.S_ISDIR(mode)
        for mode in (root_stat.st_mode, git_stat.st_mode, objects_stat.st_mode)
    ):
        raise HistoryExecutionHandoffError(
            "execution workspace capability could not be issued"
        )
    return _WorkspaceBinding(
        root=canonical_root,
        root_device=root_stat.st_dev,
        root_inode=root_stat.st_ino,
        git_device=git_stat.st_dev,
        git_inode=git_stat.st_ino,
        objects_device=objects_stat.st_dev,
        objects_inode=objects_stat.st_ino,
        publication_commit=publication_commit,
    )


def _require_exact_workspace_history(workspace: ExecutionWorkspace) -> None:
    try:
        observed = load_operational_history({"_root": workspace.root})
    except Exception as exc:
        raise HistoryExecutionHandoffError(
            "execution workspace failed production history reload"
        ) from exc
    if observed != workspace.history:
        raise HistoryExecutionHandoffError(
            "execution workspace history no longer matches publication P"
        )


def _load_execution_history(
    repository: Path,
    receipt: PublicationReceipt,
) -> PublishedHistory:
    try:
        history = load_operational_history({"_root": repository})
    except Exception as exc:
        raise HistoryExecutionHandoffError(
            "execution workspace failed production history reload"
        ) from exc
    if history != receipt.history:
        raise HistoryExecutionHandoffError(
            "execution workspace history differs from remote authority"
        )
    return history


def _freeze_output_paths(paths: Sequence[str]) -> tuple[str, ...]:
    if isinstance(paths, (str, bytes)) or not isinstance(paths, Sequence):
        raise HistoryExecutionHandoffError(
            "execution output paths must be a bounded sequence"
        )
    try:
        values = tuple(islice(iter(paths), _MAX_OUTPUTS + 1))
    except Exception as exc:
        raise HistoryExecutionHandoffError(
            "execution output paths could not be frozen"
        ) from exc
    if not values or len(values) > _MAX_OUTPUTS:
        raise HistoryExecutionHandoffError("execution output path count is invalid")
    if any(
        type(value) is not str or _OUTPUT_PATH_RE.fullmatch(value) is None
        for value in values
    ):
        raise HistoryExecutionHandoffError(
            "execution output path is not canonical or allowlisted"
        )
    if values != tuple(sorted(set(values))):
        raise HistoryExecutionHandoffError(
            "execution output paths must be sorted and unique"
        )
    for value in values:
        _parse_output_identity(value)
    return values


def _reject_duplicate_json_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _reject_json_constant(_value: str) -> None:
    raise ValueError("non-finite JSON number")


def _require_finite_json(value: object) -> None:
    if type(value) is float and not math.isfinite(value):
        raise ValueError("non-finite JSON number")
    if type(value) is dict:
        for nested in value.values():
            _require_finite_json(nested)
    elif type(value) is list:
        for nested in value:
            _require_finite_json(nested)


def _parse_output_identity(relative: str) -> _OutputIdentity:
    match = _OUTPUT_PATH_RE.fullmatch(relative)
    if match is None:
        raise HistoryExecutionHandoffError(
            "execution output path is not canonical or allowlisted"
        )
    raw_date = match.group("draw_date")
    try:
        draw_date = date.fromisoformat(raw_date)
    except ValueError as exc:
        raise HistoryExecutionHandoffError(
            "execution output path contains an invalid draw date"
        ) from exc
    if draw_date.isoformat() != raw_date or draw_date.weekday() not in {2, 5}:
        raise HistoryExecutionHandoffError(
            "execution output path contains an invalid draw date"
        )
    return _OutputIdentity(
        directory=match.group("directory"),
        draw_date=draw_date,
        model_name=match.group("model_name"),
        model_version=match.group("model_version"),
    )


def _parse_strict_json(raw: bytes, *, label: str) -> dict[str, object]:
    try:
        payload = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_json_keys,
            parse_constant=_reject_json_constant,
        )
        _require_finite_json(payload)
    except (RecursionError, UnicodeDecodeError, ValueError, TypeError) as exc:
        raise HistoryExecutionHandoffError(
            f"{label} must be strict UTF-8 JSON"
        ) from exc
    if type(payload) is not dict:
        raise HistoryExecutionHandoffError(f"{label} JSON must be an object")
    return payload


def _snapshot_output(repository: Path, relative: str) -> _OutputSnapshot:
    path = repository / relative
    descriptor: int | None = None
    try:
        descriptor = os.open(
            path,
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
        )
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_mode & 0o111:
            raise HistoryExecutionHandoffError(
                "execution output must be a non-executable regular file"
            )
        if before.st_size > _MAX_OUTPUT_BYTES:
            raise HistoryExecutionHandoffError("execution output is too large")
        chunks: list[bytes] = []
        remaining = _MAX_OUTPUT_BYTES + 1
        while remaining:
            chunk = os.read(descriptor, min(64 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        after = os.fstat(descriptor)
        current = path.lstat()
    except HistoryExecutionHandoffError:
        raise
    except OSError as exc:
        raise HistoryExecutionHandoffError(
            "execution output could not be read"
        ) from exc
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError as exc:
                raise HistoryExecutionHandoffError(
                    "execution output descriptor could not be closed"
                ) from exc
    before_identity = (
        before.st_dev,
        before.st_ino,
        before.st_mode,
        before.st_size,
        before.st_mtime_ns,
    )
    after_identity = (
        after.st_dev,
        after.st_ino,
        after.st_mode,
        after.st_size,
        after.st_mtime_ns,
    )
    current_identity = (
        current.st_dev,
        current.st_ino,
        current.st_mode,
        current.st_size,
        current.st_mtime_ns,
    )
    if (
        before_identity != after_identity
        or after_identity != current_identity
        or len(raw) != before.st_size
        or len(raw) > _MAX_OUTPUT_BYTES
    ):
        raise HistoryExecutionHandoffError(
            "execution output changed while it was being frozen"
        )
    return _OutputSnapshot(
        path=relative,
        raw=raw,
        payload=_parse_strict_json(raw, label="execution output"),
    )


def _aware_datetime(value: object, *, label: str) -> datetime:
    if type(value) is not str:
        raise HistoryExecutionHandoffError(f"{label} is invalid")
    try:
        parsed = datetime.fromisoformat(value)
        offset = parsed.utcoffset()
    except (OverflowError, TypeError, ValueError) as exc:
        raise HistoryExecutionHandoffError(f"{label} is invalid") from exc
    if offset is None or parsed.isoformat() != value:
        raise HistoryExecutionHandoffError(f"{label} is invalid")
    return parsed


def _number_list(value: object, *, length: int, label: str) -> list[int]:
    if (
        type(value) is not list
        or len(value) != length
        or any(type(number) is not int or not 1 <= number <= 49 for number in value)
        or len(set(value)) != length
    ):
        raise HistoryExecutionHandoffError(f"{label} is invalid")
    return value


def _validated_prediction(
    payload: dict[str, object],
    identity: _OutputIdentity,
) -> tuple[Prediction, datetime]:
    try:
        if set(payload) != _PREDICTION_KEYS:
            raise ValueError("prediction keys")
        if (
            payload["target_draw_date"] != identity.draw_date.isoformat()
            or payload["model_name"] != identity.model_name
            or payload["model_version"] != identity.model_version
            or type(payload["model_name"]) is not str
            or type(payload["model_version"]) is not str
        ):
            raise ValueError("prediction identity")
        probabilities_raw = payload["probabilities"]
        if type(probabilities_raw) is not dict or set(probabilities_raw) != {
            str(number) for number in range(1, 50)
        }:
            raise ValueError("prediction probabilities")
        probabilities: dict[int, float] = {}
        for raw_number, probability in probabilities_raw.items():
            if (
                type(probability) not in {int, float}
                or not math.isfinite(probability)
                or not 0 < probability < 1
            ):
                raise ValueError("prediction probability")
            probabilities[int(raw_number)] = float(probability)
        if not math.isclose(sum(probabilities.values()), 6.0, abs_tol=1e-9):
            raise ValueError("prediction probability total")
        top6 = _number_list(payload["top6"], length=6, label="prediction top6")
        top12 = _number_list(payload["top12"], length=12, label="prediction top12")
        top18 = _number_list(payload["top18"], length=18, label="prediction top18")
        ranked = sorted(
            probabilities, key=lambda number: (-probabilities[number], number)
        )
        if top6 != ranked[:6] or top12 != ranked[:12] or top18 != ranked[:18]:
            raise ValueError("prediction ranking")
        final = _number_list(
            payload["final_combination"],
            length=6,
            label="prediction final combination",
        )
        if final != sorted(final) or set(final) != set(top6):
            raise ValueError("prediction final combination")
        metadata = payload["metadata"]
        if type(metadata) is not dict:
            raise ValueError("prediction metadata")
        generated_at = _aware_datetime(
            payload["generated_at"],
            label="prediction generated_at",
        )
    except (
        HistoryExecutionHandoffError,
        KeyError,
        OverflowError,
        TypeError,
        ValueError,
    ) as exc:
        raise HistoryExecutionHandoffError(
            "execution prediction schema is invalid"
        ) from exc
    return (
        Prediction(
            target_draw_date=identity.draw_date,
            generated_at=generated_at,
            model_name=identity.model_name,
            model_version=identity.model_version,
            probabilities=probabilities,
            top6=top6,
            top12=top12,
            top18=top18,
            final_combination=final,
            metadata=metadata,
        ),
        generated_at,
    )


def _next_draw_date(after: date) -> date:
    return after + timedelta(days=3 if after.weekday() == 2 else 4)


def _validate_prediction_against_history(
    history: PublishedHistory,
    snapshot: _OutputSnapshot,
    identity: _OutputIdentity,
    *,
    created_at: datetime,
    publication_at: datetime,
) -> None:
    _prediction, generated_at = _validated_prediction(snapshot.payload, identity)
    expected_metadata = {
        "history_draws": len(history.draws),
        "history_through": history.draws[-1].draw_date.isoformat(),
        "operational_history": operational_history_provenance(history),
        "role": snapshot.payload["metadata"].get("role"),
    }
    if (
        identity.draw_date != _next_draw_date(history.draws[-1].draw_date)
        or set(snapshot.payload["metadata"]) != set(expected_metadata)
        or snapshot.payload["metadata"] != expected_metadata
        or expected_metadata["role"] not in {"primary", "shadow"}
        or generated_at.astimezone(UTC) < publication_at
        or generated_at.astimezone(UTC) > created_at
        or generated_at.astimezone(_DRAW_TIME_ZONE).date() >= identity.draw_date
        or created_at.astimezone(_DRAW_TIME_ZONE).date() >= identity.draw_date
    ):
        raise HistoryExecutionHandoffError(
            "execution prediction schema or chronology is invalid"
        )


def _validate_prediction_output(
    workspace: ExecutionWorkspace,
    snapshot: _OutputSnapshot,
    identity: _OutputIdentity,
    *,
    created_at: datetime,
    publication_at: datetime,
) -> None:
    _validate_prediction_against_history(
        workspace.history,
        snapshot,
        identity,
        created_at=created_at,
        publication_at=publication_at,
    )


def _validate_evaluation_output(
    workspace: ExecutionWorkspace,
    snapshot: _OutputSnapshot,
    identity: _OutputIdentity,
) -> None:
    draws = {draw.draw_date: draw for draw in workspace.history.draws}
    actual = draws.get(identity.draw_date)
    if actual is None:
        raise HistoryExecutionHandoffError("execution evaluation schema is invalid")
    prediction_relative = (
        f"predictions/{identity.draw_date.isoformat()}__"
        f"{identity.model_name}__{identity.model_version}.json"
    )
    try:
        base_commit = workspace.history.registry_transaction.base_commit
        base_parents = (
            _git(
                workspace.root,
                "rev-list",
                "--parents",
                "-n",
                "1",
                base_commit,
            )
            .stdout.decode("ascii")
            .split()
        )
        if len(base_parents) != 2 or base_parents[0] != base_commit:
            raise ValueError("source prediction base")
        source_history_commit = base_parents[1]
        if (
            _git(
                workspace.root,
                "cat-file",
                "-e",
                f"{source_history_commit}:{prediction_relative}",
                check=False,
            ).returncode
            == 0
        ):
            raise ValueError("source prediction is not a new immutable artifact")
        prediction_raw = _git(
            workspace.root,
            "cat-file",
            "blob",
            f"{base_commit}:{prediction_relative}",
        ).stdout
        prediction_payload = _parse_strict_json(
            prediction_raw,
            label="source prediction",
        )
        prediction, _generated_at = _validated_prediction(
            prediction_payload,
            _OutputIdentity(
                directory="predictions",
                draw_date=identity.draw_date,
                model_name=identity.model_name,
                model_version=identity.model_version,
            ),
        )
        source_history = load_published_history(
            workspace.root,
            source_history_commit,
        )
        _validate_prediction_against_history(
            source_history,
            _OutputSnapshot(
                path=prediction_relative,
                raw=prediction_raw,
                payload=prediction_payload,
            ),
            _OutputIdentity(
                directory="predictions",
                draw_date=identity.draw_date,
                model_name=identity.model_name,
                model_version=identity.model_version,
            ),
            created_at=_commit_instant(workspace.root, base_commit),
            publication_at=_commit_instant(
                workspace.root,
                source_history_commit,
            ),
        )
        expected = evaluate_prediction(prediction, actual)
        required_keys = set(expected) | {"actual_history"}
        allowed_keys = required_keys | {"email_sent"}
        if set(snapshot.payload) not in (required_keys, allowed_keys):
            raise ValueError("evaluation keys")
        if any(snapshot.payload.get(key) != value for key, value in expected.items()):
            raise ValueError("evaluation metrics")
        if snapshot.payload.get("actual_history") != operational_history_provenance(
            workspace.history
        ):
            raise ValueError("evaluation history")
        if (
            "email_sent" in snapshot.payload
            and type(snapshot.payload["email_sent"]) is not bool
        ):
            raise ValueError("evaluation notification")
    except (HistoryExecutionHandoffError, KeyError, TypeError, ValueError) as exc:
        raise HistoryExecutionHandoffError(
            "execution evaluation schema is invalid"
        ) from exc


def _validate_output_snapshot(
    workspace: ExecutionWorkspace,
    snapshot: _OutputSnapshot,
    *,
    created_at: datetime,
    publication_at: datetime,
) -> None:
    identity = _parse_output_identity(snapshot.path)
    if identity.directory == "predictions":
        _validate_prediction_output(
            workspace,
            snapshot,
            identity,
            created_at=created_at,
            publication_at=publication_at,
        )
    else:
        _validate_evaluation_output(workspace, snapshot, identity)


def _configured_live_prediction_contract(
    workspace: ExecutionWorkspace,
) -> tuple[date, str, dict[str, str]]:
    try:
        config = _load_project_config(workspace.root / "config.yaml")
        project = config["project"]
        live = config["live"]
        version = project["model_version"]
        models = live["models"]
        shadow_models = live["shadow_models"]
        if (
            type(config) is not dict
            or type(project) is not dict
            or type(live) is not dict
            or type(version) is not str
            or _OUTPUT_COMPONENT_RE.fullmatch(version) is None
            or type(models) is not list
            or not models
            or any(
                type(model) is not str or _OUTPUT_COMPONENT_RE.fullmatch(model) is None
                for model in models
            )
            or len(set(models)) != len(models)
            or type(shadow_models) is not list
            or any(type(model) is not str for model in shadow_models)
            or len(set(shadow_models)) != len(shadow_models)
            or not set(shadow_models).issubset(models)
        ):
            raise ValueError("live model configuration")
    except (KeyError, TypeError, ValueError) as exc:
        raise HistoryExecutionHandoffError(
            "execution live prediction cohort configuration is invalid"
        ) from exc
    return (
        _next_draw_date(workspace.history.draws[-1].draw_date),
        version,
        {model: "shadow" if model in shadow_models else "primary" for model in models},
    )


def _validate_live_prediction_cohort(
    workspace: ExecutionWorkspace,
    snapshots: tuple[_OutputSnapshot, ...],
) -> None:
    target, version, expected_roles = _configured_live_prediction_contract(workspace)
    observed: dict[str, _OutputSnapshot] = {}
    for snapshot in snapshots:
        identity = _parse_output_identity(snapshot.path)
        if identity.directory != "predictions":
            continue
        if identity.model_name in observed:
            raise HistoryExecutionHandoffError(
                "execution live prediction cohort is invalid"
            )
        observed[identity.model_name] = snapshot
        if (
            identity.draw_date != target
            or identity.model_version != version
            or identity.model_name not in expected_roles
            or snapshot.payload.get("metadata", {}).get("role")
            != expected_roles.get(identity.model_name)
        ):
            raise HistoryExecutionHandoffError(
                "execution live prediction cohort is invalid"
            )
    if set(observed) != set(expected_roles):
        raise HistoryExecutionHandoffError(
            "execution live prediction cohort is incomplete"
        )


def _utc_second(value: datetime) -> datetime:
    if type(value) is not datetime or value.microsecond != 0:
        raise HistoryExecutionHandoffError(
            "artifact creation time must be a whole-second UTC datetime"
        )
    try:
        offset = value.utcoffset()
    except (TypeError, ValueError, OverflowError) as exc:
        raise HistoryExecutionHandoffError(
            "artifact creation time must be a whole-second UTC datetime"
        ) from exc
    if offset is None or offset.total_seconds() != 0:
        raise HistoryExecutionHandoffError(
            "artifact creation time must be a whole-second UTC datetime"
        )
    return value.astimezone(UTC)


def _commit_instant(repository: Path, commit: str) -> datetime:
    raw = _git(repository, "cat-file", "commit", commit).stdout
    lines = [line for line in raw.splitlines() if line.startswith(b"committer ")]
    if len(lines) != 1:
        raise HistoryExecutionHandoffError("publication commit timestamp is malformed")
    try:
        _identity, raw_timestamp, raw_offset = lines[0].rsplit(b" ", 2)
        if (
            not raw_timestamp.isdigit()
            or re.fullmatch(rb"[+-][0-9]{4}", raw_offset) is None
            or int(raw_offset[1:3]) > 14
            or int(raw_offset[3:]) > 59
        ):
            raise ValueError("publication commit time is malformed")
        return datetime.fromtimestamp(int(raw_timestamp), UTC)
    except (OverflowError, ValueError) as exc:
        raise HistoryExecutionHandoffError(
            "publication commit timestamp is malformed"
        ) from exc


def _commit_utc_second(repository: Path, commit: str) -> datetime:
    raw = _git(repository, "cat-file", "commit", commit).stdout
    lines = [line for line in raw.splitlines() if line.startswith(b"committer ")]
    if len(lines) != 1 or not lines[0].endswith(b" +0000"):
        raise HistoryExecutionHandoffError("publication commit timestamp is malformed")
    return _commit_instant(repository, commit)


def _require_workspace_ready_for_outputs(
    workspace: ExecutionWorkspace,
    paths: tuple[str, ...],
    *,
    verify_authority: bool = True,
) -> None:
    _require_workspace_capability(workspace)
    repository = workspace.root
    publication = _full_oid(
        workspace.publication_commit,
        label="workspace publication",
    )
    if type(workspace.history) is not PublishedHistory or (
        workspace.history.registry.resolved_revision != publication
        or workspace.history.registry.publication_commit != publication
    ):
        raise HistoryExecutionHandoffError(
            "execution workspace history identity is invalid"
        )
    if verify_authority:
        _require_repository_integrity(repository, publication)
        _require_exact_workspace_history(workspace)
    observed = _git(repository, "rev-parse", "HEAD").stdout.decode("ascii").strip()
    if observed != publication:
        raise HistoryExecutionHandoffError("execution workspace moved away from P")
    symbolic = _git(repository, "symbolic-ref", "-q", "HEAD", check=False)
    if symbolic.returncode != 1 or symbolic.stdout or symbolic.stderr:
        raise HistoryExecutionHandoffError(
            "execution workspace must remain detached at P"
        )
    expected_tree = _git(repository, "rev-parse", f"{publication}^{{tree}}").stdout
    if _git(repository, "write-tree").stdout != expected_tree:
        raise HistoryExecutionHandoffError(
            "execution workspace index changed after handoff"
        )
    expected_status = b"".join(b"?? " + path.encode("ascii") + b"\0" for path in paths)
    status_raw = _git(
        repository,
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
    ).stdout
    if status_raw != expected_status:
        raise HistoryExecutionHandoffError(
            "execution workspace changes do not equal the exact output list"
        )
    ignored = _git(
        repository,
        "ls-files",
        "--others",
        "--ignored",
        "--exclude-standard",
        "-z",
    ).stdout
    if ignored:
        raise HistoryExecutionHandoffError(
            "execution workspace changes include ignored files"
        )
    for path in paths:
        exists = _git(
            repository,
            "cat-file",
            "-e",
            f"{publication}:{path}",
            check=False,
        )
        if exists.returncode == 0:
            raise HistoryExecutionHandoffError(
                "execution output would overwrite an immutable artifact"
            )


def freeze_execution_outputs(
    workspace: ExecutionWorkspace,
    paths: Sequence[str],
    *,
    created_at: datetime,
) -> FrozenExecutionArtifacts:
    """Freeze exact new prediction/evaluation bytes into unattached commit A."""

    frozen_paths = _freeze_output_paths(paths)
    instant = _utc_second(created_at)
    _require_workspace_ready_for_outputs(workspace, frozen_paths)
    if (
        instant.astimezone(_DRAW_TIME_ZONE).date()
        <= workspace.history.draws[-1].draw_date
    ):
        raise HistoryExecutionHandoffError(
            "artifact creation time must conservatively post-date history"
        )
    publication_instant = _commit_utc_second(
        workspace.root,
        workspace.publication_commit,
    )
    if instant < publication_instant:
        raise HistoryExecutionHandoffError(
            "artifact creation time predates publication P"
        )
    snapshots = tuple(_snapshot_output(workspace.root, path) for path in frozen_paths)
    for snapshot in snapshots:
        _validate_output_snapshot(
            workspace,
            snapshot,
            created_at=instant,
            publication_at=publication_instant,
        )
    _validate_live_prediction_cohort(workspace, snapshots)
    _require_workspace_ready_for_outputs(
        workspace,
        frozen_paths,
        verify_authority=False,
    )
    publication = workspace.publication_commit
    frozen_files: list[FrozenExecutionFile] = []
    with tempfile.TemporaryDirectory(prefix="lotto649-artifact-index-") as temporary:
        index_path = Path(temporary) / "index"
        index_environment = {"GIT_INDEX_FILE": str(index_path)}
        _git(
            workspace.root,
            "read-tree",
            publication,
            environment_overrides=index_environment,
        )
        for snapshot in snapshots:
            blob = (
                _git(
                    workspace.root,
                    "hash-object",
                    "-w",
                    "--stdin",
                    input_bytes=snapshot.raw,
                )
                .stdout.decode("ascii")
                .strip()
            )
            _full_oid(blob, label="frozen output blob")
            frozen_files.append(
                FrozenExecutionFile(
                    path=snapshot.path,
                    bytes=len(snapshot.raw),
                    sha256=hashlib.sha256(snapshot.raw).hexdigest(),
                    git_blob=blob,
                )
            )
            _git(
                workspace.root,
                "update-index",
                "--add",
                "--cacheinfo",
                "100644",
                blob,
                snapshot.path,
                environment_overrides=index_environment,
            )
        tree = (
            _git(
                workspace.root,
                "write-tree",
                environment_overrides=index_environment,
            )
            .stdout.decode("ascii")
            .strip()
        )
        _full_oid(tree, label="artifact tree")
    git_timestamp = instant.strftime("%Y-%m-%dT%H:%M:%S+00:00")
    identity_environment = {
        "GIT_AUTHOR_DATE": git_timestamp,
        "GIT_AUTHOR_EMAIL": "live-artifacts@lotto649.invalid",
        "GIT_AUTHOR_NAME": "LOTTO 6/49 Live Artifact Writer",
        "GIT_COMMITTER_DATE": git_timestamp,
        "GIT_COMMITTER_EMAIL": "live-artifacts@lotto649.invalid",
        "GIT_COMMITTER_NAME": "LOTTO 6/49 Live Artifact Writer",
    }
    artifact_commit = (
        _git(
            workspace.root,
            "commit-tree",
            tree,
            "-p",
            publication,
            input_bytes=b"chore: record verified lotto649 live artifacts\n",
            environment_overrides=identity_environment,
        )
        .stdout.decode("ascii")
        .strip()
    )
    _full_oid(artifact_commit, label="artifact commit")
    parents = (
        _git(
            workspace.root,
            "rev-list",
            "--parents",
            "-n",
            "1",
            artifact_commit,
        )
        .stdout.decode("ascii")
        .split()
    )
    if parents != [artifact_commit, publication]:
        raise HistoryExecutionHandoffError(
            "artifact commit does not have publication P as its sole parent"
        )
    _require_repository_integrity(workspace.root, artifact_commit)
    expected_delta = b"".join(
        b"A\0" + path.encode("ascii") + b"\0" for path in frozen_paths
    )
    observed_delta = _git(
        workspace.root,
        "diff-tree",
        "--no-commit-id",
        "--name-status",
        "--no-renames",
        "-r",
        "-z",
        publication,
        artifact_commit,
    ).stdout
    if observed_delta != expected_delta:
        raise HistoryExecutionHandoffError(
            "artifact commit delta differs from the exact output list"
        )
    for snapshot, file_identity in zip(snapshots, frozen_files, strict=True):
        listing = _git(
            workspace.root,
            "ls-tree",
            "-z",
            artifact_commit,
            "--",
            snapshot.path,
        ).stdout
        expected_listing = (
            f"100644 blob {file_identity.git_blob}\t{snapshot.path}\0".encode("ascii")
        )
        installed = _git(
            workspace.root,
            "cat-file",
            "blob",
            f"{artifact_commit}:{snapshot.path}",
        ).stdout
        if listing != expected_listing or installed != snapshot.raw:
            raise HistoryExecutionHandoffError(
                "artifact commit does not contain the exact frozen output bytes"
            )
    try:
        history = load_published_history(workspace.root, artifact_commit)
    except Exception as exc:
        raise HistoryExecutionHandoffError(
            "artifact commit failed production history validation"
        ) from exc
    normalized_history = replace(
        history,
        registry=replace(
            history.registry,
            requested_revision=publication,
            resolved_revision=publication,
        ),
    )
    if normalized_history != workspace.history:
        raise HistoryExecutionHandoffError(
            "artifact commit changed the verified history identity"
        )
    _require_workspace_ready_for_outputs(workspace, frozen_paths)
    for original in snapshots:
        observed = _snapshot_output(workspace.root, original.path)
        if observed.raw != original.raw:
            raise HistoryExecutionHandoffError(
                "execution output changed after it was frozen"
            )
    _require_final_workspace_controls(workspace)
    return FrozenExecutionArtifacts(
        repository=workspace.root,
        parent_commit=publication,
        tree_oid=tree,
        artifact_commit=artifact_commit,
        paths=frozen_paths,
        files=tuple(frozen_files),
        created_at=instant,
    )


@contextmanager
def _open_execution_workspace(
    receipt: PublicationReceipt,
    *,
    authority_url: str,
) -> Iterator[ExecutionWorkspace]:
    """Internal offline seam; production callers use the fixed GitHub wrapper."""

    _base, publication = _validate_receipt(receipt)
    if type(authority_url) is not str or not authority_url:
        raise HistoryExecutionHandoffError("history authority URL is invalid")
    with tempfile.TemporaryDirectory(prefix="lotto649-execution-") as temporary:
        temporary_root = Path(temporary)
        repository = temporary_root / "repository"
        template = temporary_root / "empty-template"
        template.mkdir()
        _git(
            None,
            "init",
            "--quiet",
            f"--template={template}",
            str(repository),
        )
        _git(
            repository,
            "fetch",
            "--quiet",
            "--no-tags",
            "--no-recurse-submodules",
            "--",
            authority_url,
            f"+{_MAIN_REF}:{_FETCHED_MAIN_REF}",
        )
        _require_self_contained_repository(repository)
        observed = (
            _git(repository, "rev-parse", _FETCHED_MAIN_REF)
            .stdout.decode("ascii")
            .strip()
        )
        if observed != publication:
            raise HistoryExecutionHandoffError(
                "history authority main does not equal publication P"
            )
        _require_repository_integrity(repository, publication)
        _git(repository, "checkout", "--quiet", "--detach", publication)
        _require_clean_detached_workspace(repository, publication)
        history = _load_execution_history(repository, receipt)
        binding = _workspace_binding(repository, publication)
        capability = object()
        try:
            _WORKSPACE_CAPABILITIES[capability] = binding
            yield ExecutionWorkspace(
                root=binding.root,
                publication_commit=publication,
                history=history,
                _capability=capability,
            )
        finally:
            _WORKSPACE_CAPABILITIES.pop(capability, None)


@contextmanager
def open_github_execution_workspace(
    receipt: PublicationReceipt,
) -> Iterator[ExecutionWorkspace]:
    """Open a temporary execution checkout from the fixed public authority."""

    with _open_execution_workspace(
        receipt,
        authority_url=_PRODUCTION_AUTHORITY_URL,
    ) as workspace:
        yield workspace
