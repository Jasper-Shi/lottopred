"""Publish one frozen live-artifact commit through GitHub exact CAS.

The public entry point is fixed to ``Jasper-Shi/lottopred`` main. It re-freezes
the capability-bound local commit, uploads exact Git objects, attempts at most
one compare-and-swap, then requires a new anonymous full fetch before success.
"""

from __future__ import annotations

import base64
import hashlib
import os
import re
import stat
import subprocess
import tempfile
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from .history_execution_handoff import (
    FrozenExecutionArtifacts,
    FrozenExecutionFile,
    _lease_frozen_execution_artifacts,
    _require_frozen_execution_artifacts,
)
from .history_publication_cas import (
    CasAck,
    CasStatus,
    PreparationIntegrityError,
    PublicationConflict,
    PublicationIndeterminate,
    PublicationOutcome,
    PublishedReloadError,
    StalePublication,
)
from .history_publication_github import (
    PRODUCTION_GITHUB_REPOSITORY,
    GitHubApi,
    GitHubPublicationError,
    GitHubRepositoryIdentity,
    RequestsGitHubApi,
    _preflight_repository,
    _read_main,
)
from .operational_history import PublishedHistory, load_published_history

_MAIN_REF = "refs/heads/main"
_OID_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_OUTPUT_PATH_RE = re.compile(
    r"^(?:evaluations|predictions)/"
    r"(?P<draw_date>[0-9]{4}-[0-9]{2}-[0-9]{2})__"
    r"[A-Za-z0-9][A-Za-z0-9_.-]*__"
    r"[A-Za-z0-9][A-Za-z0-9_.-]*\.json$"
)
_MAX_OUTPUTS = 128
_MAX_OUTPUT_BYTES = 2 * 1024 * 1024
_ARTIFACT_MESSAGE = "chore: record verified lotto649 live artifacts\n"
_ARTIFACT_NAME = "LOTTO 6/49 Live Artifact Writer"
_ARTIFACT_EMAIL = "live-artifacts@lotto649.invalid"
_GRAPHQL_UPDATE_REFS = """mutation UpdateArtifactRef($input: UpdateRefsInput!) {
  updateRefs(input: $input) {
    clientMutationId
  }
}"""
_INHERITED_ENVIRONMENT = {
    "PATH",
    "SYSTEMROOT",
    "WINDIR",
    "PATHEXT",
    "TMPDIR",
    "TMP",
    "TEMP",
}


@dataclass(frozen=True)
class ArtifactPublicationReceipt:
    """An artifact advance proven by an authoritative reread and fresh fetch."""

    expected_parent: str
    artifact_commit: str
    observed_before: str
    observed_after: str
    cas_ack: CasAck | None
    outcome: PublicationOutcome
    history: PublishedHistory


@dataclass(frozen=True)
class _ArtifactSignature:
    name: str
    email: str
    date: str

    def payload(self) -> dict[str, str]:
        return {"name": self.name, "email": self.email, "date": self.date}


@dataclass(frozen=True)
class _ArtifactFile:
    path: str
    oid: str
    raw: bytes
    sha256: str


@dataclass(frozen=True)
class _ArtifactPlan:
    repository: Path
    parent_commit: str
    parent_tree: str
    tree_oid: str
    artifact_commit: str
    raw_commit: bytes
    message: str
    signature: _ArtifactSignature
    paths: tuple[str, ...]
    files: tuple[_ArtifactFile, ...]
    history: PublishedHistory


class GitHubArtifactVerifier(Protocol):
    """Prove the expected artifact from a new anonymous full Git fetch."""

    def verify(
        self,
        repository: GitHubRepositoryIdentity,
        plan: _ArtifactPlan,
    ) -> PublishedHistory: ...


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


def _run_git(
    repository: Path | None,
    *arguments: str,
    input_bytes: bytes | None = None,
    fresh: bool = False,
) -> bytes:
    command = ["git"]
    if repository is not None:
        command.extend(["-C", str(repository)])
    command.extend(arguments)
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            input=input_bytes,
            env=_git_environment(),
            timeout=120,
        )
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        error = (
            GitHubPublicationError("fresh GitHub artifact is unavailable")
            if fresh
            else PreparationIntegrityError(
                "frozen artifact Git objects are unavailable"
            )
        )
        raise error from exc
    if completed.returncode != 0:
        if fresh:
            raise GitHubPublicationError("fresh GitHub artifact is unavailable")
        raise PreparationIntegrityError("frozen artifact Git objects are unavailable")
    return completed.stdout


def _git_text(
    repository: Path,
    *arguments: str,
    input_bytes: bytes | None = None,
    fresh: bool = False,
) -> str:
    try:
        return (
            _run_git(
                repository,
                *arguments,
                input_bytes=input_bytes,
                fresh=fresh,
            )
            .decode("ascii")
            .strip()
        )
    except UnicodeDecodeError as exc:
        error = (
            GitHubPublicationError("fresh GitHub artifact is invalid")
            if fresh
            else PreparationIntegrityError("frozen artifact identity is invalid")
        )
        raise error from exc


def _full_oid(value: object, *, label: str) -> str:
    if type(value) is not str or _OID_RE.fullmatch(value) is None:
        raise PreparationIntegrityError(f"{label} must be a full SHA-1 OID")
    return value


def _regular_object_store(path: Path) -> None:
    try:
        entries = tuple(os.scandir(path))
    except OSError as exc:
        raise PreparationIntegrityError(
            "frozen artifact object store is unreadable"
        ) from exc
    for entry in entries:
        if entry.is_symlink():
            raise PreparationIntegrityError(
                "frozen artifact object store must be self-contained"
            )
        if entry.is_dir(follow_symlinks=False):
            _regular_object_store(Path(entry.path))
        elif not entry.is_file(follow_symlinks=False):
            raise PreparationIntegrityError(
                "frozen artifact object store must contain regular objects"
            )


def _resolved_repository(artifacts: FrozenExecutionArtifacts) -> Path:
    if not isinstance(artifacts.repository, Path):
        raise PreparationIntegrityError("frozen artifact repository is invalid")
    try:
        repository = artifacts.repository.resolve(strict=True)
        git_directory = repository / ".git"
        objects = git_directory / "objects"
        repository_stat = repository.stat(follow_symlinks=False)
        git_stat = git_directory.stat(follow_symlinks=False)
        objects_stat = objects.stat(follow_symlinks=False)
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        raise PreparationIntegrityError(
            "frozen artifact repository is invalid"
        ) from exc
    if (
        repository != artifacts.repository
        or not stat.S_ISDIR(repository_stat.st_mode)
        or not stat.S_ISDIR(git_stat.st_mode)
        or not stat.S_ISDIR(objects_stat.st_mode)
    ):
        raise PreparationIntegrityError("frozen artifact repository is invalid")
    for forbidden in (
        objects / "info" / "alternates",
        objects / "info" / "http-alternates",
        git_directory / "commondir",
        git_directory / "shallow",
    ):
        if os.path.lexists(forbidden):
            raise PreparationIntegrityError(
                "frozen artifact repository must be complete and self-contained"
            )
    _regular_object_store(objects)
    if tuple(objects.glob("pack/*.promisor")):
        raise PreparationIntegrityError(
            "frozen artifact repository must be complete and self-contained"
        )
    return repository


def _require_repository_controls(repository: Path) -> None:
    git_directory = repository / ".git"
    try:
        absolute_git_directory = Path(
            _git_text(repository, "rev-parse", "--absolute-git-dir")
        ).resolve(strict=True)
        common_raw = _git_text(repository, "rev-parse", "--git-common-dir")
        common_directory = Path(common_raw)
        if not common_directory.is_absolute():
            common_directory = repository / common_directory
        common_directory = common_directory.resolve(strict=True)
        expected_git_directory = git_directory.resolve(strict=True)
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        raise PreparationIntegrityError(
            "frozen artifact repository must be complete and self-contained"
        ) from exc
    if (
        absolute_git_directory != expected_git_directory
        or common_directory != expected_git_directory
    ):
        raise PreparationIntegrityError(
            "frozen artifact repository must be complete and self-contained"
        )
    try:
        names = (
            _run_git(
                repository,
                "config",
                "--no-includes",
                "--name-only",
                "--list",
            )
            .decode("utf-8")
            .splitlines()
        )
    except UnicodeDecodeError as exc:
        raise PreparationIntegrityError(
            "frozen artifact Git config is invalid"
        ) from exc
    lowered = tuple(name.lower() for name in names)
    if any(
        name.startswith(("fsck.", "include.", "includeif."))
        or name == "extensions.partialclone"
        or (
            name.startswith("remote.")
            and name.endswith((".promisor", ".partialclonefilter"))
        )
        for name in lowered
    ):
        raise PreparationIntegrityError("frozen artifact Git config is not trusted")
    if (
        _git_text(repository, "rev-parse", "--show-object-format") != "sha1"
        or _git_text(repository, "rev-parse", "--is-shallow-repository") != "false"
    ):
        raise PreparationIntegrityError(
            "frozen artifact requires complete SHA-1 history"
        )


def _canonical_paths(artifacts: FrozenExecutionArtifacts) -> tuple[str, ...]:
    paths = artifacts.paths
    if (
        type(paths) is not tuple
        or not paths
        or len(paths) > _MAX_OUTPUTS
        or any(type(path) is not str for path in paths)
    ):
        raise PreparationIntegrityError(
            "frozen artifact paths must be bounded, sorted, and unique"
        )
    if paths != tuple(sorted(set(paths))):
        raise PreparationIntegrityError(
            "frozen artifact paths must be bounded, sorted, and unique"
        )
    for path in paths:
        match = _OUTPUT_PATH_RE.fullmatch(path) if len(path) <= 512 else None
        if match is None:
            raise PreparationIntegrityError("frozen artifact path is not allowlisted")
        try:
            draw_date = datetime.strptime(match.group("draw_date"), "%Y-%m-%d").date()
        except ValueError as exc:
            raise PreparationIntegrityError(
                "frozen artifact path draw date is invalid"
            ) from exc
        if draw_date.isoformat() != match.group(
            "draw_date"
        ) or draw_date.weekday() not in {
            2,
            5,
        }:
            raise PreparationIntegrityError("frozen artifact path draw date is invalid")
        try:
            path.encode("ascii")
        except UnicodeEncodeError as exc:
            raise PreparationIntegrityError(
                "frozen artifact path is not canonical ASCII"
            ) from exc
    return paths


def _canonical_instant(value: object) -> datetime:
    if type(value) is not datetime or value.microsecond != 0:
        raise PreparationIntegrityError(
            "frozen artifact creation time must be whole-second UTC"
        )
    try:
        offset = value.utcoffset()
    except (OverflowError, TypeError, ValueError) as exc:
        raise PreparationIntegrityError(
            "frozen artifact creation time must be whole-second UTC"
        ) from exc
    if offset is None or offset.total_seconds() != 0:
        raise PreparationIntegrityError(
            "frozen artifact creation time must be whole-second UTC"
        )
    return value.astimezone(UTC)


def _expected_signature(instant: datetime) -> tuple[bytes, _ArtifactSignature]:
    epoch = int(instant.timestamp())
    raw = f"{_ARTIFACT_NAME} <{_ARTIFACT_EMAIL}> {epoch} +0000".encode("ascii")
    return (
        raw,
        _ArtifactSignature(
            name=_ARTIFACT_NAME,
            email=_ARTIFACT_EMAIL,
            date=instant.strftime("%Y-%m-%dT%H:%M:%SZ"),
        ),
    )


def _validate_commit_object(
    repository: Path,
    artifacts: FrozenExecutionArtifacts,
    instant: datetime,
) -> tuple[bytes, str, str, _ArtifactSignature]:
    parent = _full_oid(artifacts.parent_commit, label="frozen artifact parent")
    tree = _full_oid(artifacts.tree_oid, label="frozen artifact tree")
    commit = _full_oid(artifacts.artifact_commit, label="frozen artifact commit")
    if _git_text(repository, "rev-parse", f"{parent}^{{commit}}") != parent:
        raise PreparationIntegrityError("frozen artifact parent is unavailable")
    if _git_text(repository, "rev-parse", f"{commit}^{{commit}}") != commit:
        raise PreparationIntegrityError("frozen artifact commit is unavailable")
    raw_commit = _run_git(repository, "cat-file", "commit", commit)
    calculated = _git_text(
        repository,
        "hash-object",
        "-t",
        "commit",
        "--stdin",
        input_bytes=raw_commit,
    )
    if calculated != commit:
        raise PreparationIntegrityError("frozen artifact commit identity is invalid")
    try:
        raw_headers, raw_message = raw_commit.split(b"\n\n", 1)
        headers = raw_headers.splitlines()
        if len(headers) != 4:
            raise ValueError("unexpected headers")
        tree_line, parent_line, author_line, committer_line = headers
        observed_tree = tree_line.removeprefix(b"tree ").decode("ascii")
        observed_parent = parent_line.removeprefix(b"parent ").decode("ascii")
    except (UnicodeDecodeError, ValueError) as exc:
        raise PreparationIntegrityError(
            "frozen artifact commit is not canonical"
        ) from exc
    expected_signature, signature = _expected_signature(instant)
    if (
        tree_line != f"tree {tree}".encode("ascii")
        or parent_line != f"parent {parent}".encode("ascii")
        or observed_tree != tree
        or observed_parent != parent
        or author_line != b"author " + expected_signature
        or committer_line != b"committer " + expected_signature
        or raw_message != _ARTIFACT_MESSAGE.encode("utf-8")
    ):
        raise PreparationIntegrityError("frozen artifact commit is not canonical")
    parents = _git_text(repository, "rev-list", "--parents", "-n", "1", commit).split()
    if parents != [commit, parent]:
        raise PreparationIntegrityError(
            "frozen artifact commit must have P as its sole parent"
        )
    raw_tree = _run_git(repository, "cat-file", "tree", tree)
    if (
        _git_text(
            repository,
            "hash-object",
            "-t",
            "tree",
            "--stdin",
            input_bytes=raw_tree,
        )
        != tree
    ):
        raise PreparationIntegrityError("frozen artifact tree identity is invalid")
    parent_tree = _git_text(repository, "show", "-s", "--format=%T", parent)
    if _OID_RE.fullmatch(parent_tree) is None:
        raise PreparationIntegrityError("frozen artifact parent tree is invalid")
    return raw_commit, parent_tree, tree, signature


def _validate_files(
    repository: Path,
    artifacts: FrozenExecutionArtifacts,
    paths: tuple[str, ...],
) -> tuple[_ArtifactFile, ...]:
    files = artifacts.files
    if (
        type(files) is not tuple
        or len(files) != len(paths)
        or any(type(file) is not FrozenExecutionFile for file in files)
        or tuple(file.path for file in files) != paths
    ):
        raise PreparationIntegrityError(
            "frozen artifact files do not match the exact path list"
        )
    expected_delta = b"".join(b"A\0" + path.encode("ascii") + b"\0" for path in paths)
    observed_delta = _run_git(
        repository,
        "diff-tree",
        "--no-commit-id",
        "--name-status",
        "--no-renames",
        "-r",
        "-z",
        artifacts.parent_commit,
        artifacts.artifact_commit,
    )
    if observed_delta != expected_delta:
        raise PreparationIntegrityError(
            "frozen artifact commit must add only the exact artifact paths"
        )
    frozen: list[_ArtifactFile] = []
    for path, file in zip(paths, files, strict=True):
        if (
            type(file) is not FrozenExecutionFile
            or type(file.bytes) is not int
            or not 0 <= file.bytes <= _MAX_OUTPUT_BYTES
            or type(file.sha256) is not str
            or _SHA256_RE.fullmatch(file.sha256) is None
            or type(file.git_blob) is not str
            or _OID_RE.fullmatch(file.git_blob) is None
        ):
            raise PreparationIntegrityError("frozen artifact file identity is invalid")
        raw = _run_git(
            repository,
            "cat-file",
            "blob",
            f"{artifacts.artifact_commit}:{path}",
        )
        listing = _run_git(
            repository,
            "ls-tree",
            "-z",
            artifacts.artifact_commit,
            "--",
            path,
        )
        expected_listing = f"100644 blob {file.git_blob}\t{path}\0".encode("ascii")
        calculated_oid = _git_text(
            repository,
            "hash-object",
            "-t",
            "blob",
            "--stdin",
            input_bytes=raw,
        )
        calculated_sha256 = hashlib.sha256(raw).hexdigest()
        if (
            listing != expected_listing
            or len(raw) != file.bytes
            or calculated_oid != file.git_blob
            or calculated_sha256 != file.sha256
        ):
            raise PreparationIntegrityError(
                "frozen artifact commit bytes do not match the freeze record"
            )
        frozen.append(
            _ArtifactFile(
                path=path,
                oid=file.git_blob,
                raw=raw,
                sha256=file.sha256,
            )
        )
    return tuple(frozen)


def _normalized_history(
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


def _load_exact_history(
    repository: Path,
    artifact_commit: str,
    parent_commit: str,
    expected: PublishedHistory,
) -> PublishedHistory:
    try:
        history = load_published_history(repository, artifact_commit)
    except Exception as exc:
        raise PreparationIntegrityError(
            "frozen artifact failed production history validation"
        ) from exc
    if (
        type(history) is not PublishedHistory
        or history.registry.resolved_revision != artifact_commit
        or history.registry.publication_commit != parent_commit
        or _normalized_history(history, parent_commit) != expected
    ):
        raise PreparationIntegrityError(
            "frozen artifact changed the verified history identity"
        )
    return history


def _freeze_artifact_plan(
    artifacts: FrozenExecutionArtifacts,
    history: PublishedHistory,
) -> _ArtifactPlan:
    repository = _resolved_repository(artifacts)
    parent = _full_oid(artifacts.parent_commit, label="frozen artifact parent")
    commit = _full_oid(artifacts.artifact_commit, label="frozen artifact commit")
    if (
        type(history) is not PublishedHistory
        or history.registry.resolved_revision != parent
        or history.registry.publication_commit != parent
    ):
        raise PreparationIntegrityError(
            "frozen artifact capability history does not identify P"
        )
    instant = _canonical_instant(artifacts.created_at)
    paths = _canonical_paths(artifacts)
    _require_repository_controls(repository)
    _run_git(repository, "fsck", "--full", "--no-dangling", commit)
    raw_commit, parent_tree, tree, signature = _validate_commit_object(
        repository,
        artifacts,
        instant,
    )
    files = _validate_files(repository, artifacts, paths)
    _load_exact_history(repository, commit, parent, history)
    _run_git(repository, "fsck", "--full", "--no-dangling", commit)
    return _ArtifactPlan(
        repository=repository,
        parent_commit=parent,
        parent_tree=parent_tree,
        tree_oid=tree,
        artifact_commit=commit,
        raw_commit=raw_commit,
        message=_ARTIFACT_MESSAGE,
        signature=signature,
        paths=paths,
        files=files,
        history=history,
    )


def _mapping(value: object, *, label: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise GitHubPublicationError(f"GitHub artifact {label} response is invalid")
    return value


def _request(
    api: GitHubApi,
    method: str,
    path: str,
    *,
    payload: object | None = None,
) -> dict[str, Any]:
    try:
        response = api.request_json(method, path, payload=payload)
    except Exception as exc:
        raise GitHubPublicationError(
            "GitHub artifact API request failed before CAS"
        ) from exc
    return _mapping(response, label=path)


def _upload_plan(plan: _ArtifactPlan, api: GitHubApi) -> None:
    base = "/repos/Jasper-Shi/lottopred"
    for file in plan.files:
        response = _request(
            api,
            "POST",
            f"{base}/git/blobs",
            payload={
                "content": base64.b64encode(file.raw).decode("ascii"),
                "encoding": "base64",
            },
        )
        if response.get("sha") != file.oid:
            raise GitHubPublicationError("GitHub artifact blob identity mismatch")
    tree = _request(
        api,
        "POST",
        f"{base}/git/trees",
        payload={
            "base_tree": plan.parent_tree,
            "tree": [
                {
                    "path": file.path,
                    "mode": "100644",
                    "type": "blob",
                    "sha": file.oid,
                }
                for file in plan.files
            ],
        },
    )
    if tree.get("sha") != plan.tree_oid:
        raise GitHubPublicationError("GitHub artifact tree identity mismatch")
    commit = _request(
        api,
        "POST",
        f"{base}/git/commits",
        payload={
            "message": plan.message,
            "tree": plan.tree_oid,
            "parents": [plan.parent_commit],
            "author": plan.signature.payload(),
            "committer": plan.signature.payload(),
        },
    )
    if commit.get("sha") != plan.artifact_commit:
        raise GitHubPublicationError("GitHub artifact commit identity mismatch")
    installed = _request(
        api,
        "GET",
        f"{base}/git/commits/{plan.artifact_commit}",
    )
    if installed.get("sha") != plan.artifact_commit:
        raise GitHubPublicationError("GitHub artifact commit is unavailable")


def _attempt_cas(plan: _ArtifactPlan, api: GitHubApi) -> CasAck:
    mutation_id = f"artifact-publication:{plan.artifact_commit}"
    payload = {
        "query": _GRAPHQL_UPDATE_REFS,
        "variables": {
            "input": {
                "repositoryId": PRODUCTION_GITHUB_REPOSITORY.node_id,
                "refUpdates": [
                    {
                        "name": _MAIN_REF,
                        "beforeOid": plan.parent_commit,
                        "afterOid": plan.artifact_commit,
                        "force": False,
                    }
                ],
                "clientMutationId": mutation_id,
            }
        },
    }
    try:
        response = api.request_json("POST", "/graphql", payload=payload)
        if type(response) is not dict or (
            "errors" in response and response["errors"] != []
        ):
            return CasAck(CasStatus.UNKNOWN)
        data = response.get("data")
        update = data.get("updateRefs") if type(data) is dict else None
        if type(update) is not dict or update.get("clientMutationId") != mutation_id:
            return CasAck(CasStatus.UNKNOWN)
        return CasAck(CasStatus.APPLIED)
    except Exception:  # noqa: BLE001 - the authoritative reread decides the outcome
        return CasAck(CasStatus.UNKNOWN)


def _verify_remote(
    plan: _ArtifactPlan,
    artifact_verifier: GitHubArtifactVerifier,
) -> PublishedHistory:
    try:
        history = artifact_verifier.verify(PRODUCTION_GITHUB_REPOSITORY, plan)
    except Exception as exc:
        raise PublishedReloadError(plan.artifact_commit) from exc
    if (
        type(history) is not PublishedHistory
        or history.registry.resolved_revision != plan.artifact_commit
        or history.registry.publication_commit != plan.parent_commit
        or _normalized_history(history, plan.parent_commit) != plan.history
    ):
        raise PublishedReloadError(plan.artifact_commit)
    return history


def _verify_plan_in_repository(
    repository: Path, plan: _ArtifactPlan
) -> PublishedHistory:
    if _git_text(repository, "rev-parse", "--show-object-format", fresh=True) != "sha1":
        raise GitHubPublicationError("fresh GitHub artifact hash algorithm mismatch")
    if (
        _git_text(repository, "rev-parse", "--is-shallow-repository", fresh=True)
        != "false"
    ):
        raise GitHubPublicationError("fresh GitHub artifact history is incomplete")
    observed = _git_text(
        repository,
        "show-ref",
        "--verify",
        "--hash",
        _MAIN_REF,
        fresh=True,
    )
    if observed != plan.artifact_commit:
        raise GitHubPublicationError("fresh GitHub artifact main identity mismatch")
    _run_git(
        repository,
        "fsck",
        "--full",
        "--no-dangling",
        plan.artifact_commit,
        fresh=True,
    )
    raw_commit = _run_git(
        repository,
        "cat-file",
        "commit",
        plan.artifact_commit,
        fresh=True,
    )
    if raw_commit != plan.raw_commit:
        raise GitHubPublicationError("fresh GitHub artifact commit bytes mismatch")
    parents = _git_text(
        repository,
        "rev-list",
        "--parents",
        "-n",
        "1",
        plan.artifact_commit,
        fresh=True,
    ).split()
    if parents != [plan.artifact_commit, plan.parent_commit]:
        raise GitHubPublicationError("fresh GitHub artifact topology mismatch")
    tree = _git_text(
        repository,
        "show",
        "-s",
        "--format=%T",
        plan.artifact_commit,
        fresh=True,
    )
    if tree != plan.tree_oid:
        raise GitHubPublicationError("fresh GitHub artifact tree mismatch")
    expected_delta = b"".join(
        b"A\0" + path.encode("ascii") + b"\0" for path in plan.paths
    )
    delta = _run_git(
        repository,
        "diff-tree",
        "--no-commit-id",
        "--name-status",
        "--no-renames",
        "-r",
        "-z",
        plan.parent_commit,
        plan.artifact_commit,
        fresh=True,
    )
    if delta != expected_delta:
        raise GitHubPublicationError("fresh GitHub artifact delta mismatch")
    for file in plan.files:
        raw = _run_git(
            repository,
            "cat-file",
            "blob",
            f"{plan.artifact_commit}:{file.path}",
            fresh=True,
        )
        listing = _run_git(
            repository,
            "ls-tree",
            "-z",
            plan.artifact_commit,
            "--",
            file.path,
            fresh=True,
        )
        expected_listing = f"100644 blob {file.oid}\t{file.path}\0".encode("ascii")
        if (
            raw != file.raw
            or listing != expected_listing
            or hashlib.sha256(raw).hexdigest() != file.sha256
        ):
            raise GitHubPublicationError("fresh GitHub artifact file mismatch")
    try:
        history = load_published_history(repository, plan.artifact_commit)
    except Exception as exc:
        raise GitHubPublicationError(
            "fresh GitHub artifact failed production history validation"
        ) from exc
    if (
        type(history) is not PublishedHistory
        or history.registry.resolved_revision != plan.artifact_commit
        or history.registry.publication_commit != plan.parent_commit
        or _normalized_history(history, plan.parent_commit) != plan.history
    ):
        raise GitHubPublicationError("fresh GitHub artifact changed verified history")
    return history


class FreshBareGitHubArtifactVerifier:
    """Fetch fixed public main into a new complete bare repository and prove A."""

    def verify(
        self,
        repository: GitHubRepositoryIdentity,
        plan: _ArtifactPlan,
    ) -> PublishedHistory:
        if (
            type(repository) is not GitHubRepositoryIdentity
            or repository != PRODUCTION_GITHUB_REPOSITORY
            or type(plan) is not _ArtifactPlan
        ):
            raise GitHubPublicationError("fresh GitHub artifact request is invalid")
        with tempfile.TemporaryDirectory(
            prefix="lotto649-github-artifact-"
        ) as temporary:
            bare_repository = Path(temporary) / "authority.git"
            empty_template = Path(temporary) / "empty-template"
            empty_template.mkdir()
            _run_git(
                None,
                "init",
                "--bare",
                "--object-format=sha1",
                f"--template={empty_template}",
                str(bare_repository),
                fresh=True,
            )
            _run_git(
                bare_repository,
                "-c",
                f"core.hooksPath={os.devnull}",
                "-c",
                "credential.helper=",
                "-c",
                "http.followRedirects=false",
                "-c",
                "protocol.version=2",
                "fetch",
                "--no-tags",
                "--no-recurse-submodules",
                "https://github.com/Jasper-Shi/lottopred.git",
                f"{_MAIN_REF}:{_MAIN_REF}",
                fresh=True,
            )
            _run_git(
                bare_repository,
                "symbolic-ref",
                "HEAD",
                _MAIN_REF,
                fresh=True,
            )
            return _verify_plan_in_repository(bare_repository, plan)


def _publish_with_ports(
    artifacts: FrozenExecutionArtifacts,
    *,
    api: GitHubApi,
    artifact_verifier: GitHubArtifactVerifier,
) -> ArtifactPublicationReceipt:
    """State-machine seam with fakes only at the true external boundaries."""

    with _lease_frozen_execution_artifacts(artifacts) as binding:
        plan = _freeze_artifact_plan(artifacts, binding.history)
        _require_frozen_execution_artifacts(artifacts)
        _preflight_repository(PRODUCTION_GITHUB_REPOSITORY, api)
        observed_before = _read_main(PRODUCTION_GITHUB_REPOSITORY, api)
        if observed_before == plan.artifact_commit:
            history = _verify_remote(plan, artifact_verifier)
            _require_frozen_execution_artifacts(artifacts)
            return ArtifactPublicationReceipt(
                expected_parent=plan.parent_commit,
                artifact_commit=plan.artifact_commit,
                observed_before=observed_before,
                observed_after=observed_before,
                cas_ack=None,
                outcome=PublicationOutcome.ALREADY_PUBLISHED,
                history=history,
            )
        if observed_before != plan.parent_commit:
            raise StalePublication(plan.parent_commit, observed_before)

        if binding.cas_attempted:
            raise PublicationIndeterminate(
                plan.parent_commit,
                plan.artifact_commit,
                observed_before,
            )
        _upload_plan(plan, api)
        binding.cas_attempted = True
        ack = _attempt_cas(plan, api)
        try:
            observed_after = _read_main(PRODUCTION_GITHUB_REPOSITORY, api)
        except Exception as exc:
            raise PublicationIndeterminate(
                plan.parent_commit,
                plan.artifact_commit,
                None,
            ) from exc
        if observed_after == plan.parent_commit:
            raise PublicationIndeterminate(
                plan.parent_commit,
                plan.artifact_commit,
                observed_after,
            )
        if observed_after != plan.artifact_commit:
            raise PublicationConflict(
                plan.parent_commit,
                plan.artifact_commit,
                observed_after,
            )
        history = _verify_remote(plan, artifact_verifier)
        _require_frozen_execution_artifacts(artifacts)
        outcome = (
            PublicationOutcome.ADVANCED
            if ack.status is CasStatus.APPLIED
            else PublicationOutcome.CONFIRMED_AFTER_REREAD
        )
        return ArtifactPublicationReceipt(
            expected_parent=plan.parent_commit,
            artifact_commit=plan.artifact_commit,
            observed_before=observed_before,
            observed_after=observed_after,
            cas_ack=ack,
            outcome=outcome,
            history=history,
        )


def publish_frozen_execution_artifacts_to_github(
    artifacts: FrozenExecutionArtifacts,
    *,
    token: str,
) -> ArtifactPublicationReceipt:
    """Publish one active freeze-issued artifact to fixed production main."""

    _require_frozen_execution_artifacts(artifacts)
    return _publish_with_ports(
        artifacts,
        api=RequestsGitHubApi(token),
        artifact_verifier=FreshBareGitHubArtifactVerifier(),
    )
