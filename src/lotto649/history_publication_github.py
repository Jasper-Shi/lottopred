"""Publish one prepared history transaction through GitHub exact CAS.

The module uploads only content-addressed Git objects, attempts one GraphQL
``updateRefs`` mutation with an exact old OID, rereads the authoritative ref,
and requires a separately fetched production-history reload before success.
It does not collect sources, evaluate predictions, or enable any workflow.
"""

from __future__ import annotations

import base64
import json
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Protocol

import requests

from .history_publication import PreparedPublication
from .history_publication_cas import (
    CasAck,
    CasStatus,
    PreparationIntegrityError,
    PublicationConflict,
    PublicationIndeterminate,
    PublicationOutcome,
    PublicationReceipt,
    PublishedReloadError,
    ReferenceIntegrityError,
    StalePublication,
)
from .operational_history import PublishedHistory, load_published_history

_MAIN_REF = "refs/heads/main"
_OID_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_NODE_ID_RE = re.compile(r"^[A-Za-z0-9_=-]+$")
_REPOSITORY_COMPONENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,99}$")
_SIGNATURE_RE = re.compile(
    rb"^LOTTO 6/49 History Writer <history-writer@lotto649\.invalid> "
    rb"([0-9]+) \+0000$"
)
_SUFFIX_PATH = "data/processed/epochs/DI-2026-08-20-registered-history/live_draws.jsonl"
_REGISTRY_PATH = (
    "evidence/operational_history/DI-2026-08-20-registered-history/pin-registry.jsonl"
)
_GRAPHQL_UPDATE_REFS = """mutation UpdateHistoryRef($input: UpdateRefsInput!) {
  updateRefs(input: $input) {
    clientMutationId
  }
}"""
_GITHUB_API_ORIGIN = "https://api.github.com"
_MAX_API_RESPONSE_BYTES = 1024 * 1024
_INHERITED_ENVIRONMENT = {
    "PATH",
    "SYSTEMROOT",
    "WINDIR",
    "PATHEXT",
    "TMPDIR",
    "TMP",
    "TEMP",
}


class GitHubPublicationError(RuntimeError):
    """Raised before CAS when GitHub object publication cannot be proven."""


@dataclass(frozen=True)
class GitHubRepositoryIdentity:
    """Immutable GitHub repository identity used by the publisher."""

    owner: str
    name: str
    node_id: str

    def __post_init__(self) -> None:
        if (
            type(self.owner) is not str
            or _REPOSITORY_COMPONENT_RE.fullmatch(self.owner) is None
            or type(self.name) is not str
            or _REPOSITORY_COMPONENT_RE.fullmatch(self.name) is None
            or type(self.node_id) is not str
            or _NODE_ID_RE.fullmatch(self.node_id) is None
        ):
            raise ValueError("GitHub repository identity is invalid")

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.name}"


PRODUCTION_GITHUB_REPOSITORY = GitHubRepositoryIdentity(
    owner="Jasper-Shi",
    name="lottopred",
    node_id="R_kgDOT41pdQ",
)


class GitHubApi(Protocol):
    """Bounded JSON GitHub API transport; authentication stays behind the port."""

    def request_json(
        self,
        method: str,
        path: str,
        *,
        payload: object | None = None,
    ) -> object: ...


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _reject_json_constant(_value: str) -> None:
    raise ValueError("non-finite JSON number")


def _reject_json_float(_value: str) -> None:
    raise ValueError("floating-point JSON number")


def _is_allowed_api_path(method: str, path: str) -> bool:
    if path == "/graphql":
        return method == "POST"
    repository_path = "/repos/Jasper-Shi/lottopred"
    if path == repository_path:
        return method == "GET"
    relative = path.removeprefix(repository_path + "/")
    if relative == path:
        return False
    if relative in {
        "branches/main/protection",
        "git/ref/heads/main",
        "hash-algorithm",
    }:
        return method == "GET"
    if relative in {"git/blobs", "git/trees", "git/commits"}:
        return method == "POST"
    if relative.startswith("git/commits/"):
        return (
            method == "GET"
            and _OID_RE.fullmatch(relative.removeprefix("git/commits/")) is not None
        )
    return False


class RequestsGitHubApi:
    """Fixed-origin bounded GitHub JSON client with an in-memory credential."""

    def __init__(self, token: str) -> None:
        if (
            type(token) is not str
            or not token
            or len(token) > 512
            or any(character.isspace() or ord(character) < 33 for character in token)
        ):
            raise GitHubPublicationError("GitHub credential is invalid")
        session = requests.Session()
        session.trust_env = False
        session.headers.update(
            {
                "Accept": "application/vnd.github+json",
                "Accept-Encoding": "identity",
                "Authorization": f"Bearer {token}",
                "User-Agent": "lotto649-history-publisher/1",
                "X-GitHub-Api-Version": "2026-03-10",
            }
        )
        self._session = session

    def request_json(
        self,
        method: str,
        path: str,
        *,
        payload: object | None = None,
    ) -> object:
        if (
            type(method) is not str
            or method not in {"GET", "POST"}
            or type(path) is not str
            or len(path) > 512
            or not path.startswith("/")
            or "//" in path
            or "\\" in path
            or "?" in path
            or "#" in path
            or any(part in {"", ".", ".."} for part in path.split("/")[1:])
            or not path.isascii()
            or not _is_allowed_api_path(method, path)
        ):
            raise GitHubPublicationError("GitHub API path is invalid")
        if (method == "GET" and payload is not None) or (
            method == "POST" and type(payload) is not dict
        ):
            raise GitHubPublicationError("GitHub API payload is invalid")
        url = _GITHUB_API_ORIGIN + path
        kwargs: dict[str, object] = {
            "allow_redirects": False,
            "stream": True,
            "timeout": (10, 30),
        }
        if payload is not None:
            kwargs["json"] = payload
        try:
            response_context = self._session.request(method, url, **kwargs)
            with response_context as response:
                expected_status = 200 if method == "GET" or path == "/graphql" else 201
                if response.status_code != expected_status:
                    raise GitHubPublicationError(
                        "GitHub API response status is invalid"
                    )
                if type(response.url) is not str or response.url != url:
                    raise GitHubPublicationError("GitHub API response URL is invalid")
                content_type = response.headers.get("Content-Type")
                media_type = (
                    content_type.partition(";")[0].strip().lower()
                    if type(content_type) is str
                    else ""
                )
                if media_type != "application/json" and not media_type.endswith(
                    "+json"
                ):
                    raise GitHubPublicationError("GitHub API response must be JSON")
                content_encoding = response.headers.get("Content-Encoding")
                if content_encoding is not None and (
                    type(content_encoding) is not str
                    or content_encoding.strip().lower() != "identity"
                ):
                    raise GitHubPublicationError(
                        "GitHub API response must not use Content-Encoding"
                    )
                content_length = response.headers.get("Content-Length")
                declared_length: int | None = None
                if content_length is not None:
                    if (
                        type(content_length) is not str
                        or not content_length.isascii()
                        or not content_length.isdigit()
                    ):
                        raise GitHubPublicationError(
                            "GitHub API Content-Length is invalid"
                        )
                    normalized = content_length.lstrip("0") or "0"
                    maximum = str(_MAX_API_RESPONSE_BYTES)
                    if len(normalized) > len(maximum) or (
                        len(normalized) == len(maximum) and normalized > maximum
                    ):
                        raise GitHubPublicationError(
                            "GitHub API response exceeds size limit"
                        )
                    declared_length = int(normalized)
                chunks = []
                total = 0
                for chunk in response.iter_content(chunk_size=64 * 1024):
                    if not chunk:
                        continue
                    if type(chunk) is not bytes:
                        raise GitHubPublicationError(
                            "GitHub API response is not immutable bytes"
                        )
                    total += len(chunk)
                    if total > _MAX_API_RESPONSE_BYTES:
                        raise GitHubPublicationError(
                            "GitHub API response exceeds size limit"
                        )
                    chunks.append(chunk)
                if declared_length is not None and total != declared_length:
                    raise GitHubPublicationError(
                        "GitHub API response length is invalid"
                    )
                if total == 0:
                    raise GitHubPublicationError("GitHub API response is empty")
        except GitHubPublicationError:
            raise
        except Exception:  # noqa: BLE001 - redact all transport implementation errors
            raise GitHubPublicationError("GitHub API transport failed") from None
        try:
            decoded = b"".join(chunks).decode("utf-8")
            result = json.loads(
                decoded,
                object_pairs_hook=_reject_duplicate_keys,
                parse_constant=_reject_json_constant,
                parse_float=_reject_json_float,
            )
        except (UnicodeDecodeError, ValueError):
            raise GitHubPublicationError(
                "GitHub API response JSON is invalid"
            ) from None
        if type(result) is not dict:
            raise GitHubPublicationError("GitHub API response JSON is invalid")
        return result


class GitHubSnapshotLoader(Protocol):
    """Load one expected main OID from a fresh remote-authority snapshot."""

    def load(
        self,
        repository: GitHubRepositoryIdentity,
        expected_head: str,
    ) -> PublishedHistory: ...


def _run_fresh_git(*arguments: str) -> bytes:
    try:
        completed = subprocess.run(
            ["git", *arguments],
            check=False,
            capture_output=True,
            env=_git_environment(),
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
        raise GitHubPublicationError("fresh GitHub snapshot is unavailable") from exc
    if completed.returncode != 0:
        raise GitHubPublicationError("fresh GitHub snapshot is unavailable")
    return completed.stdout


def _fresh_git_text(*arguments: str) -> str:
    try:
        return _run_fresh_git(*arguments).decode("ascii").strip()
    except UnicodeDecodeError as exc:
        raise GitHubPublicationError("fresh GitHub snapshot is invalid") from exc


class FreshBareGitHubSnapshotLoader:
    """Fetch fixed public main into a new full bare repository and load it."""

    def load(
        self,
        repository: GitHubRepositoryIdentity,
        expected_head: str,
    ) -> PublishedHistory:
        if (
            type(repository) is not GitHubRepositoryIdentity
            or repository != PRODUCTION_GITHUB_REPOSITORY
            or type(expected_head) is not str
            or _OID_RE.fullmatch(expected_head) is None
        ):
            raise GitHubPublicationError("fresh GitHub snapshot request is invalid")
        with tempfile.TemporaryDirectory(
            prefix="lotto649-github-history-"
        ) as temporary:
            bare_repository = Path(temporary) / "authority.git"
            empty_template = Path(temporary) / "empty-template"
            empty_template.mkdir()
            _run_fresh_git(
                "init",
                "--bare",
                "--object-format=sha1",
                f"--template={empty_template}",
                str(bare_repository),
            )
            clone_url = "https://github.com/Jasper-Shi/lottopred.git"
            _run_fresh_git(
                "-c",
                f"core.hooksPath={os.devnull}",
                "-c",
                "credential.helper=",
                "-c",
                "http.followRedirects=false",
                "-c",
                "protocol.version=2",
                "-C",
                str(bare_repository),
                "fetch",
                "--no-tags",
                "--no-recurse-submodules",
                clone_url,
                f"{_MAIN_REF}:{_MAIN_REF}",
            )
            _run_fresh_git(
                "-C",
                str(bare_repository),
                "symbolic-ref",
                "HEAD",
                _MAIN_REF,
            )
            observed = _fresh_git_text(
                "-C",
                str(bare_repository),
                "show-ref",
                "--verify",
                "--hash",
                _MAIN_REF,
            )
            shallow = _fresh_git_text(
                "-C",
                str(bare_repository),
                "rev-parse",
                "--is-shallow-repository",
            )
            if observed != expected_head or shallow != "false":
                raise GitHubPublicationError("fresh GitHub main identity mismatch")
            _run_fresh_git(
                "-c",
                f"fsck.skipList={os.devnull}",
                "-C",
                str(bare_repository),
                "fsck",
                "--full",
                "--no-dangling",
            )
            try:
                history = load_published_history(bare_repository, expected_head)
            except Exception as exc:
                raise GitHubPublicationError(
                    "fresh GitHub history failed production validation"
                ) from exc
            if history.registry.resolved_revision != expected_head:
                raise GitHubPublicationError("fresh GitHub history identity mismatch")
            return history


@dataclass(frozen=True)
class _BlobChange:
    path: str
    oid: str
    raw: bytes


@dataclass(frozen=True)
class _GitSignature:
    name: str
    email: str
    date: str

    def payload(self) -> dict[str, str]:
        return {"name": self.name, "email": self.email, "date": self.date}


@dataclass(frozen=True)
class _CommitUpload:
    oid: str
    parent: str
    base_tree: str
    tree: str
    message: str
    author: _GitSignature
    committer: _GitSignature
    changes: tuple[_BlobChange, ...]


@dataclass(frozen=True)
class _UploadPlan:
    prepared: PreparedPublication
    commits: tuple[_CommitUpload, _CommitUpload, _CommitUpload]


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
    repository: Path,
    *arguments: str,
    input_bytes: bytes | None = None,
) -> bytes:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repository), *arguments],
            input=input_bytes,
            check=False,
            capture_output=True,
            env=_git_environment(),
        )
    except (OSError, ValueError) as exc:
        raise PreparationIntegrityError("prepared Git objects are unavailable") from exc
    if completed.returncode != 0:
        raise PreparationIntegrityError("prepared Git objects are unavailable")
    return completed.stdout


def _git_text(
    repository: Path,
    *arguments: str,
    input_bytes: bytes | None = None,
) -> str:
    try:
        return (
            _git(repository, *arguments, input_bytes=input_bytes)
            .decode("ascii")
            .strip()
        )
    except UnicodeDecodeError as exc:
        raise PreparationIntegrityError("prepared Git identity is invalid") from exc


def _full_oid(value: object, *, label: str) -> str:
    if type(value) is not str or _OID_RE.fullmatch(value) is None:
        raise PreparationIntegrityError(f"{label} must be a full Git OID")
    return value


def _full_sha256(value: object, *, label: str) -> str:
    if type(value) is not str or _SHA256_RE.fullmatch(value) is None:
        raise PreparationIntegrityError(f"{label} must be a full SHA-256")
    return value


def _resolved_repository(prepared: PreparedPublication) -> Path:
    if type(prepared) is not PreparedPublication:
        raise PreparationIntegrityError("prepared candidate type is invalid")
    try:
        repository = Path(prepared.repository).resolve(strict=True)
    except (OSError, TypeError, ValueError) as exc:
        raise PreparationIntegrityError("prepared repository is invalid") from exc
    if not repository.is_dir():
        raise PreparationIntegrityError("prepared repository is invalid")
    return repository


def _validate_prepared(
    prepared: PreparedPublication,
    repository: Path,
) -> PublishedHistory:
    try:
        if type(prepared.target_draw_date) is not date:
            raise PreparationIntegrityError("prepared target date is invalid")
        base = _full_oid(prepared.base_commit, label="prepared base")
        evidence = _full_oid(prepared.evidence_commit, label="prepared evidence")
        suffix = _full_oid(prepared.suffix_commit, label="prepared suffix")
        publication = _full_oid(
            prepared.publication_commit,
            label="prepared publication",
        )
        registry_head = _full_sha256(
            prepared.registry_head_event_sha256,
            label="prepared registry head",
        )
        suffix_head = _full_sha256(
            prepared.suffix_head_event_sha256,
            label="prepared suffix head",
        )
        history = load_published_history(repository, publication)
        if (
            history.registry.publication_commit != publication
            or history.registry.resolved_revision != publication
            or history.registry_transaction.base_commit != base
            or history.registry_transaction.evidence_commit != evidence
            or history.registry_transaction.suffix_commit != suffix
            or history.registry.head_event_sha256 != registry_head
            or history.registry_suffix.head_event_sha256 != suffix_head
            or history.registry_suffix.history_through != prepared.target_draw_date
            or not history.draws
            or history.draws[-1].draw_date != prepared.target_draw_date
        ):
            raise PreparationIntegrityError(
                "prepared candidate does not match published B/E/S/P history"
            )
        return history
    except PreparationIntegrityError:
        raise
    except Exception as exc:
        raise PreparationIntegrityError(
            "prepared candidate failed production validation"
        ) from exc


def _parse_signature(raw: bytes) -> _GitSignature:
    match = _SIGNATURE_RE.fullmatch(raw)
    if match is None:
        raise PreparationIntegrityError("prepared commit signature is not canonical")
    try:
        timestamp = int(match.group(1))
        instant = datetime.fromtimestamp(timestamp, UTC)
    except (OverflowError, ValueError) as exc:
        raise PreparationIntegrityError(
            "prepared commit signature is not canonical"
        ) from exc
    return _GitSignature(
        name="LOTTO 6/49 History Writer",
        email="history-writer@lotto649.invalid",
        date=instant.strftime("%Y-%m-%dT%H:%M:%SZ"),
    )


def _tree_entry(repository: Path, commit: str, path: str) -> _BlobChange:
    raw_entry = _git(repository, "ls-tree", "-z", commit, "--", path)
    try:
        metadata, actual_path = raw_entry.removesuffix(b"\0").split(b"\t", 1)
        mode, kind, oid_raw = metadata.split(b" ")
        decoded_path = actual_path.decode("utf-8")
        oid = oid_raw.decode("ascii")
    except (UnicodeDecodeError, ValueError) as exc:
        raise PreparationIntegrityError("prepared tree entry is invalid") from exc
    if (
        mode != b"100644"
        or kind != b"blob"
        or decoded_path != path
        or _OID_RE.fullmatch(oid) is None
    ):
        raise PreparationIntegrityError("prepared tree entry is invalid")
    blob = _git(repository, "cat-file", "blob", oid)
    calculated = _git_text(
        repository,
        "hash-object",
        "-t",
        "blob",
        "--stdin",
        input_bytes=blob,
    )
    if calculated != oid:
        raise PreparationIntegrityError("prepared blob identity is invalid")
    return _BlobChange(path=path, oid=oid, raw=blob)


def _verify_tree_object(repository: Path, tree: str) -> None:
    raw_tree = _git(repository, "cat-file", "tree", tree)
    calculated = _git_text(
        repository,
        "hash-object",
        "-t",
        "tree",
        "--stdin",
        input_bytes=raw_tree,
    )
    if calculated != tree:
        raise PreparationIntegrityError("prepared tree identity is invalid")


def _verify_repository_objects(repository: Path, publication: str) -> None:
    try:
        config_names = (
            _git(
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
        raise PreparationIntegrityError("prepared Git config is invalid") from exc
    if any(
        name.lower().startswith(("fsck.", "include.", "includeif."))
        for name in config_names
    ):
        raise PreparationIntegrityError("prepared Git fsck policy is not trusted")
    _git(
        repository,
        "-c",
        f"fsck.skipList={os.devnull}",
        "fsck",
        "--full",
        "--no-dangling",
        publication,
    )


def _changed_paths(repository: Path, parent: str, commit: str) -> tuple[str, ...]:
    raw = _git(
        repository,
        "diff-tree",
        "--no-commit-id",
        "--name-status",
        "-r",
        "-z",
        parent,
        commit,
    )
    parts = raw.removesuffix(b"\0").split(b"\0") if raw else []
    if len(parts) % 2 != 0:
        raise PreparationIntegrityError("prepared commit delta is invalid")
    paths = []
    for index in range(0, len(parts), 2):
        status = parts[index]
        try:
            path = parts[index + 1].decode("utf-8")
        except UnicodeDecodeError as exc:
            raise PreparationIntegrityError("prepared commit delta is invalid") from exc
        if status not in {b"A", b"M"} or not path or path.startswith("/"):
            raise PreparationIntegrityError("prepared commit delta is invalid")
        paths.append(path)
    return tuple(paths)


def _expected_message(prepared: PreparedPublication, commit: str) -> str:
    draw_date = prepared.target_draw_date.isoformat()
    messages = {
        prepared.evidence_commit: f"Record official LOTTO 6/49 sources for {draw_date}",
        prepared.suffix_commit: f"Append verified LOTTO 6/49 draw {draw_date}",
        prepared.publication_commit: f"Publish verified LOTTO 6/49 draw {draw_date}",
    }
    try:
        return messages[commit]
    except KeyError as exc:
        raise PreparationIntegrityError(
            "prepared commit identity is unexpected"
        ) from exc


def _expected_paths(
    prepared: PreparedPublication,
    commit: str,
    paths: tuple[str, ...],
) -> None:
    if commit == prepared.evidence_commit:
        expected_prefixes = {
            "evidence/live_sources/loto_quebec/",
            "evidence/live_sources/wclc/",
        }
        prefixes = {
            prefix
            for prefix in expected_prefixes
            if any(path.startswith(prefix) for path in paths)
        }
        if (
            len(paths) != 2
            or prefixes != expected_prefixes
            or any(not path.endswith(".html") for path in paths)
        ):
            raise PreparationIntegrityError("prepared evidence delta is invalid")
        return
    expected = (
        _SUFFIX_PATH
        if commit == prepared.suffix_commit
        else _REGISTRY_PATH
        if commit == prepared.publication_commit
        else ""
    )
    if paths != (expected,):
        raise PreparationIntegrityError("prepared publication delta is invalid")


def _freeze_commit(
    prepared: PreparedPublication,
    repository: Path,
    commit: str,
    expected_parent: str,
) -> _CommitUpload:
    raw_commit = _git(repository, "cat-file", "commit", commit)
    calculated = _git_text(
        repository,
        "hash-object",
        "-t",
        "commit",
        "--stdin",
        input_bytes=raw_commit,
    )
    if calculated != commit:
        raise PreparationIntegrityError("prepared commit identity is invalid")
    try:
        header_raw, message_raw = raw_commit.split(b"\n\n", 1)
        header_lines = header_raw.splitlines()
        if len(header_lines) != 4:
            raise ValueError("unexpected commit headers")
        tree_line, parent_line, author_line, committer_line = header_lines
        tree = tree_line.removeprefix(b"tree ").decode("ascii")
        parent = parent_line.removeprefix(b"parent ").decode("ascii")
        if not tree_line.startswith(b"tree ") or not parent_line.startswith(b"parent "):
            raise ValueError("unexpected commit topology")
        if not author_line.startswith(b"author ") or not committer_line.startswith(
            b"committer "
        ):
            raise ValueError("unexpected commit signature")
        author = _parse_signature(author_line.removeprefix(b"author "))
        committer = _parse_signature(committer_line.removeprefix(b"committer "))
        message = message_raw.decode("utf-8")
    except (UnicodeDecodeError, ValueError) as exc:
        raise PreparationIntegrityError("prepared commit object is invalid") from exc
    expected_message = _expected_message(prepared, commit)
    if (
        _OID_RE.fullmatch(tree) is None
        or parent != expected_parent
        or message != expected_message + "\n"
    ):
        raise PreparationIntegrityError("prepared commit object is invalid")
    _verify_tree_object(repository, tree)
    paths = _changed_paths(repository, parent, commit)
    _expected_paths(prepared, commit, paths)
    base_tree = _git_text(repository, "show", "-s", "--format=%T", parent)
    if _OID_RE.fullmatch(base_tree) is None:
        raise PreparationIntegrityError("prepared base tree identity is invalid")
    _verify_tree_object(repository, base_tree)
    changes = tuple(_tree_entry(repository, commit, path) for path in paths)
    return _CommitUpload(
        oid=commit,
        parent=parent,
        base_tree=base_tree,
        tree=tree,
        message=message,
        author=author,
        committer=committer,
        changes=changes,
    )


def _freeze_upload_plan(prepared: PreparedPublication) -> _UploadPlan:
    repository = _resolved_repository(prepared)
    _validate_prepared(prepared, repository)
    _verify_repository_objects(repository, prepared.publication_commit)
    commits = (
        _freeze_commit(
            prepared,
            repository,
            prepared.evidence_commit,
            prepared.base_commit,
        ),
        _freeze_commit(
            prepared,
            repository,
            prepared.suffix_commit,
            prepared.evidence_commit,
        ),
        _freeze_commit(
            prepared,
            repository,
            prepared.publication_commit,
            prepared.suffix_commit,
        ),
    )
    return _UploadPlan(prepared=prepared, commits=commits)


def _request(
    api: GitHubApi,
    method: str,
    path: str,
    *,
    payload: object | None = None,
) -> Any:
    try:
        return api.request_json(method, path, payload=payload)
    except Exception as exc:
        raise GitHubPublicationError("GitHub API request failed before CAS") from exc


def _mapping(value: object, *, label: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise GitHubPublicationError(f"GitHub {label} response is invalid")
    return value


def _repository_path(repository: GitHubRepositoryIdentity) -> str:
    return f"/repos/{repository.owner}/{repository.name}"


def _preflight_repository(
    repository: GitHubRepositoryIdentity,
    api: GitHubApi,
) -> None:
    response = _mapping(
        _request(api, "GET", _repository_path(repository)),
        label="repository",
    )
    if (
        response.get("node_id") != repository.node_id
        or response.get("full_name") != repository.full_name
        or response.get("default_branch") != "main"
        or response.get("private") is not False
    ):
        raise GitHubPublicationError("GitHub repository identity is invalid")
    hash_algorithm = _mapping(
        _request(
            api,
            "GET",
            f"{_repository_path(repository)}/hash-algorithm",
        ),
        label="hash algorithm",
    )
    if hash_algorithm != {"hash_algorithm": "sha1"}:
        raise GitHubPublicationError("GitHub repository hash algorithm is invalid")
    protection = _mapping(
        _request(
            api,
            "GET",
            f"{_repository_path(repository)}/branches/main/protection",
        ),
        label="branch protection",
    )
    enforce_admins = protection.get("enforce_admins")
    allow_force_pushes = protection.get("allow_force_pushes")
    allow_deletions = protection.get("allow_deletions")
    if (
        type(enforce_admins) is not dict
        or enforce_admins.get("enabled") is not True
        or type(allow_force_pushes) is not dict
        or allow_force_pushes.get("enabled") is not False
        or type(allow_deletions) is not dict
        or allow_deletions.get("enabled") is not False
    ):
        raise GitHubPublicationError("GitHub main protection is insufficient")


def _read_main(
    repository: GitHubRepositoryIdentity,
    api: GitHubApi,
) -> str:
    try:
        response = _mapping(
            api.request_json(
                "GET",
                f"{_repository_path(repository)}/git/ref/heads/main",
                payload=None,
            ),
            label="reference",
        )
        target = response.get("object")
        if (
            response.get("ref") != _MAIN_REF
            or type(target) is not dict
            or target.get("type") != "commit"
            or type(target.get("sha")) is not str
            or _OID_RE.fullmatch(target["sha"]) is None
        ):
            raise ValueError("invalid reference")
        return target["sha"]
    except Exception as exc:
        raise ReferenceIntegrityError("GitHub main authority cannot be read") from exc


def _upload_plan(
    plan: _UploadPlan,
    repository: GitHubRepositoryIdentity,
    api: GitHubApi,
) -> None:
    base_path = _repository_path(repository)
    for commit in plan.commits:
        for change in commit.changes:
            blob_response = _mapping(
                _request(
                    api,
                    "POST",
                    f"{base_path}/git/blobs",
                    payload={
                        "content": base64.b64encode(change.raw).decode("ascii"),
                        "encoding": "base64",
                    },
                ),
                label="blob",
            )
            if blob_response.get("sha") != change.oid:
                raise GitHubPublicationError("GitHub blob identity mismatch")
        tree_response = _mapping(
            _request(
                api,
                "POST",
                f"{base_path}/git/trees",
                payload={
                    "base_tree": commit.base_tree,
                    "tree": [
                        {
                            "path": change.path,
                            "mode": "100644",
                            "type": "blob",
                            "sha": change.oid,
                        }
                        for change in commit.changes
                    ],
                },
            ),
            label="tree",
        )
        if tree_response.get("sha") != commit.tree:
            raise GitHubPublicationError("GitHub tree identity mismatch")
        commit_response = _mapping(
            _request(
                api,
                "POST",
                f"{base_path}/git/commits",
                payload={
                    "message": commit.message,
                    "tree": commit.tree,
                    "parents": [commit.parent],
                    "author": commit.author.payload(),
                    "committer": commit.committer.payload(),
                },
            ),
            label="commit",
        )
        if commit_response.get("sha") != commit.oid:
            raise GitHubPublicationError("GitHub commit identity mismatch")
    publication = _mapping(
        _request(
            api,
            "GET",
            f"{base_path}/git/commits/{plan.prepared.publication_commit}",
        ),
        label="commit",
    )
    if publication.get("sha") != plan.prepared.publication_commit:
        raise GitHubPublicationError("GitHub publication commit is unavailable")


def _attempt_cas(
    prepared: PreparedPublication,
    repository: GitHubRepositoryIdentity,
    api: GitHubApi,
) -> CasAck:
    client_mutation_id = f"history-publication:{prepared.publication_commit}"
    payload = {
        "query": _GRAPHQL_UPDATE_REFS,
        "variables": {
            "input": {
                "repositoryId": repository.node_id,
                "refUpdates": [
                    {
                        "name": _MAIN_REF,
                        "beforeOid": prepared.base_commit,
                        "afterOid": prepared.publication_commit,
                        "force": False,
                    }
                ],
                "clientMutationId": client_mutation_id,
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
        if (
            type(update) is not dict
            or update.get("clientMutationId") != client_mutation_id
        ):
            return CasAck(CasStatus.UNKNOWN)
        return CasAck(CasStatus.APPLIED)
    except Exception:  # noqa: BLE001
        return CasAck(CasStatus.UNKNOWN)


def _reload_remote(
    prepared: PreparedPublication,
    repository: GitHubRepositoryIdentity,
    snapshot_loader: GitHubSnapshotLoader,
) -> PublishedHistory:
    try:
        history = snapshot_loader.load(repository, prepared.publication_commit)
        if (
            type(history) is not PublishedHistory
            or history.registry.resolved_revision != prepared.publication_commit
            or history.registry.publication_commit != prepared.publication_commit
            or history.registry_transaction.base_commit != prepared.base_commit
            or history.registry_transaction.evidence_commit != prepared.evidence_commit
            or history.registry_transaction.suffix_commit != prepared.suffix_commit
            or history.registry.head_event_sha256 != prepared.registry_head_event_sha256
            or history.registry_suffix.head_event_sha256
            != prepared.suffix_head_event_sha256
            or not history.draws
            or history.draws[-1].draw_date != prepared.target_draw_date
        ):
            raise ValueError("fresh history identity mismatch")
        return history
    except Exception as exc:
        raise PublishedReloadError(prepared.publication_commit) from exc


def _publish_with_ports(
    prepared: PreparedPublication,
    *,
    api: GitHubApi,
    snapshot_loader: GitHubSnapshotLoader,
) -> PublicationReceipt:
    """Internal state-machine seam with fakes only at true external boundaries."""

    repository = PRODUCTION_GITHUB_REPOSITORY
    plan = _freeze_upload_plan(prepared)
    _preflight_repository(repository, api)
    observed_before = _read_main(repository, api)
    if observed_before == prepared.publication_commit:
        history = _reload_remote(prepared, repository, snapshot_loader)
        return PublicationReceipt(
            expected_base=prepared.base_commit,
            publication_commit=prepared.publication_commit,
            observed_before=observed_before,
            observed_after=observed_before,
            cas_ack=None,
            outcome=PublicationOutcome.ALREADY_PUBLISHED,
            history=history,
        )
    if observed_before != prepared.base_commit:
        raise StalePublication(prepared.base_commit, observed_before)

    _upload_plan(plan, repository, api)
    ack = _attempt_cas(prepared, repository, api)
    try:
        observed_after = _read_main(repository, api)
    except Exception as exc:
        raise PublicationIndeterminate(
            prepared.base_commit,
            prepared.publication_commit,
            None,
        ) from exc
    if observed_after == prepared.base_commit:
        raise PublicationIndeterminate(
            prepared.base_commit,
            prepared.publication_commit,
            observed_after,
        )
    if observed_after != prepared.publication_commit:
        raise PublicationConflict(
            prepared.base_commit,
            prepared.publication_commit,
            observed_after,
        )
    history = _reload_remote(prepared, repository, snapshot_loader)
    outcome = (
        PublicationOutcome.ADVANCED
        if ack.status is CasStatus.APPLIED
        else PublicationOutcome.CONFIRMED_AFTER_REREAD
    )
    return PublicationReceipt(
        expected_base=prepared.base_commit,
        publication_commit=prepared.publication_commit,
        observed_before=observed_before,
        observed_after=observed_after,
        cas_ack=ack,
        outcome=outcome,
        history=history,
    )


def publish_prepared_history_to_github(
    prepared: PreparedPublication,
    *,
    token: str,
) -> PublicationReceipt:
    """Publish through fixed GitHub authority and prove it by a fresh public fetch."""

    return _publish_with_ports(
        prepared,
        api=RequestsGitHubApi(token),
        snapshot_loader=FreshBareGitHubSnapshotLoader(),
    )
