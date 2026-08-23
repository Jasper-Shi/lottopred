"""Resolve operational-history authority from an append-only Git registry."""

from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import date
from hashlib import sha256
from pathlib import Path
from typing import Any

INCIDENT_ID = "DI-2026-08-20-registered-history"
REGISTRY_PATH = f"evidence/operational_history/{INCIDENT_ID}/pin-registry.jsonl"
GENESIS_COMMIT = "a6857d6b4e6e532062f484bcce4466f76ba4327b"
GENESIS_PARENT = "cf401a8873821b0f5647945752aee320f9452d57"
GENESIS_EVENT_SHA256 = (
    "22bcfe219c091dbcdb751ef7a2d9d5251f3040770de6e2e825ac5c64fc69c63d"
)
GENESIS_GIT_BLOB = "e95aeaaa28d5c1b7e5fb636d0fc4a3c26ff31017"
GENESIS_FILE_SHA256 = "42a9df8ef861a5fad6e1d7e7639d3d9317e519c0e83e96d7b1148527215afb72"
GENESIS_BYTES = 1_170

_SCHEMA_VERSION = "lotto649-history-pin-registry-event-v1"
_SUFFIX_SCHEMA_VERSION = "lotto649-history-suffix-event-v1"
_EVENT_KEYS = {
    "event_kind",
    "event_sha256",
    "incident_id",
    "previous_event_sha256",
    "schema_version",
    "seal",
    "sequence",
    "suffix",
    "transaction",
}
_SEAL_KEYS = {"bytes", "commit", "git_blob", "path", "sha256"}
_SUFFIX_KEYS = {
    "bytes",
    "event_count",
    "git_blob",
    "head_event_sha256",
    "history_through",
    "path",
    "sha256",
}
_TRANSACTION_KEYS = {"base_commit", "evidence_commit", "suffix_commit"}
_SEAL_PATH = f"evidence/data_integrity/{INCIDENT_ID}/seal.json"
_SUFFIX_PATH = f"data/processed/epochs/{INCIDENT_ID}/live_draws.jsonl"
_OID_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_EVIDENCE_PATH_RE = re.compile(
    r"^evidence/live_sources/(?P<authority>loto_quebec|wclc)/"
    r"(?P<draw_date>[0-9]{4}-[0-9]{2}-[0-9]{2})-"
    r"(?P<sha256>[0-9a-f]{64})\.html$"
)
_INHERITED_ENVIRONMENT = {
    "HOME",
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
    "PATH",
    "SYSTEMROOT",
    "TEMP",
    "TMP",
    "TMPDIR",
}


class HistoryRegistryIntegrityError(ValueError):
    """Raised when registry authority cannot be proven from immutable Git data."""


@dataclass(frozen=True)
class RegistrySealIdentity:
    path: str
    commit: str
    git_blob: str
    bytes: int
    sha256: str


@dataclass(frozen=True)
class RegistrySuffixIdentity:
    path: str
    git_blob: str
    bytes: int
    sha256: str
    event_count: int
    head_event_sha256: str
    history_through: date


@dataclass(frozen=True)
class RegistryTransaction:
    base_commit: str
    evidence_commit: str
    suffix_commit: str


@dataclass(frozen=True)
class RegistryProvenance:
    registry_path: str
    requested_revision: str
    resolved_revision: str
    publication_commit: str
    genesis_commit: str
    genesis_parent: str
    git_blob: str
    bytes: int
    file_sha256: str
    event_count: int
    head_event_sha256: str


@dataclass(frozen=True)
class HistoryRegistryState:
    sequence: int
    event_kind: str
    event_sha256: str
    seal: RegistrySealIdentity
    suffix: RegistrySuffixIdentity
    transaction: RegistryTransaction
    seal_raw: bytes
    suffix_raw: bytes
    provenance: RegistryProvenance


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
        }
    )
    return environment


def _git_bytes(repository: Path, *arguments: str) -> bytes:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repository), *arguments],
            check=False,
            capture_output=True,
            env=_git_environment(),
        )
    except OSError as exc:
        raise HistoryRegistryIntegrityError("Git is unavailable") from exc
    if completed.returncode != 0:
        raise HistoryRegistryIntegrityError(
            "required immutable Git object is unavailable"
        )
    return completed.stdout


def _repository_path(repository: str | Path) -> Path:
    if not isinstance(repository, (str, Path)):
        raise HistoryRegistryIntegrityError("repository path is invalid")
    try:
        resolved = Path(repository).resolve(strict=True)
    except OSError as exc:
        raise HistoryRegistryIntegrityError("repository does not exist") from exc
    if not resolved.is_dir():
        raise HistoryRegistryIntegrityError("repository path is invalid")
    return resolved


def _resolve_exact_commit(repository: Path, revision: str) -> str:
    if not isinstance(revision, str) or _OID_RE.fullmatch(revision) is None:
        raise HistoryRegistryIntegrityError(
            "revision must be a full lowercase commit OID"
        )
    try:
        resolved = (
            _git_bytes(
                repository,
                "rev-parse",
                "--verify",
                "--end-of-options",
                f"{revision}^{{commit}}",
            )
            .decode("ascii")
            .strip()
        )
    except UnicodeError as exc:
        raise HistoryRegistryIntegrityError(
            "revision commit identity is invalid"
        ) from exc
    if resolved != revision:
        raise HistoryRegistryIntegrityError("revision commit identity mismatch")
    return resolved


def _require_full_history(repository: Path) -> None:
    try:
        shallow = (
            _git_bytes(repository, "rev-parse", "--is-shallow-repository")
            .decode("ascii")
            .strip()
        )
    except UnicodeError as exc:
        raise HistoryRegistryIntegrityError(
            "registry requires a full history checkout"
        ) from exc
    if shallow != "false":
        raise HistoryRegistryIntegrityError("registry requires a full history checkout")


def resolve_repository_head(repository: str | Path) -> str:
    """Resolve the repository's literal ``HEAD`` to one immutable commit OID."""

    repository_path = _repository_path(repository)
    try:
        resolved = (
            _git_bytes(
                repository_path,
                "rev-parse",
                "--verify",
                "--end-of-options",
                "HEAD^{commit}",
            )
            .decode("ascii")
            .strip()
        )
    except UnicodeError as exc:
        raise HistoryRegistryIntegrityError("repository HEAD is invalid") from exc
    if _OID_RE.fullmatch(resolved) is None:
        raise HistoryRegistryIntegrityError("repository HEAD is not a full commit OID")
    return resolved


def _commit_ancestry(repository: Path, commit: str) -> list[str]:
    try:
        return _git_bytes(repository, "rev-list", commit).decode("ascii").splitlines()
    except UnicodeError as exc:
        raise HistoryRegistryIntegrityError("commit ancestry is invalid") from exc


def _ancestry_parents(repository: Path, commit: str) -> dict[str, tuple[str, ...]]:
    try:
        lines = (
            _git_bytes(repository, "rev-list", "--parents", commit)
            .decode("ascii")
            .splitlines()
        )
    except UnicodeError as exc:
        raise HistoryRegistryIntegrityError("commit ancestry is invalid") from exc
    result: dict[str, tuple[str, ...]] = {}
    for line in lines:
        identities = line.split()
        if not identities or any(
            _OID_RE.fullmatch(value) is None for value in identities
        ):
            raise HistoryRegistryIntegrityError("commit ancestry is invalid")
        result[identities[0]] = tuple(identities[1:])
    return result


def _verify_genesis(repository: Path, revision: str) -> None:
    ancestry = _commit_ancestry(repository, revision)
    if not ancestry or ancestry[0] != revision or GENESIS_COMMIT not in ancestry:
        raise HistoryRegistryIntegrityError(
            "registry genesis is absent from the revision ancestry"
        )
    try:
        genesis_line = (
            _git_bytes(
                repository,
                "rev-list",
                "--parents",
                "-n",
                "1",
                GENESIS_COMMIT,
            )
            .decode("ascii")
            .strip()
            .split()
        )
    except UnicodeError as exc:
        raise HistoryRegistryIntegrityError(
            "registry genesis identity is invalid"
        ) from exc
    if genesis_line != [GENESIS_COMMIT, GENESIS_PARENT]:
        raise HistoryRegistryIntegrityError("registry genesis parent mismatch")


def _git_blob(repository: Path, commit: str, path: str) -> tuple[str, bytes]:
    try:
        entry = (
            _git_bytes(repository, "ls-tree", commit, "--", path)
            .decode("utf-8")
            .strip()
        )
        metadata, listed_path = entry.split("\t", 1)
        mode, object_type, git_blob = metadata.split(" ", 2)
    except (UnicodeError, ValueError) as exc:
        raise HistoryRegistryIntegrityError("Git blob identity is invalid") from exc
    if listed_path != path or mode != "100644" or object_type != "blob":
        raise HistoryRegistryIntegrityError("Git path is not a regular immutable blob")
    raw = _git_bytes(repository, "cat-file", "blob", git_blob)
    return git_blob, raw


def _canonical_json(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise HistoryRegistryIntegrityError(
            "registry event is not canonical JSON"
        ) from exc


def _has_exact_keys(value: object, keys: set[str]) -> bool:
    return isinstance(value, dict) and set(value) == keys


def _is_integer(value: object) -> bool:
    return type(value) is int and value >= 0


def _is_oid(value: object) -> bool:
    return isinstance(value, str) and _OID_RE.fullmatch(value) is not None


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and _SHA256_RE.fullmatch(value) is not None


def _validate_event_schema(event: dict[str, Any]) -> None:
    if not _has_exact_keys(event, _EVENT_KEYS):
        raise HistoryRegistryIntegrityError("registry event schema mismatch")
    seal = event["seal"]
    suffix = event["suffix"]
    transaction = event["transaction"]
    if (
        event["schema_version"] != _SCHEMA_VERSION
        or event["incident_id"] != INCIDENT_ID
        or not isinstance(event["event_kind"], str)
        or event["event_kind"] not in {"genesis_migration", "append"}
        or not _is_integer(event["sequence"])
        or not _is_sha256(event["event_sha256"])
        or not _is_sha256(event["previous_event_sha256"])
        or not _has_exact_keys(seal, _SEAL_KEYS)
        or seal["path"] != _SEAL_PATH
        or not _is_oid(seal["commit"])
        or not _is_oid(seal["git_blob"])
        or not _is_integer(seal["bytes"])
        or not _is_sha256(seal["sha256"])
        or not _has_exact_keys(suffix, _SUFFIX_KEYS)
        or suffix["path"] != _SUFFIX_PATH
        or not _is_oid(suffix["git_blob"])
        or not _is_integer(suffix["bytes"])
        or not _is_integer(suffix["event_count"])
        or not _is_sha256(suffix["sha256"])
        or not _is_sha256(suffix["head_event_sha256"])
        or not isinstance(suffix["history_through"], str)
        or not _has_exact_keys(transaction, _TRANSACTION_KEYS)
        or any(not _is_oid(transaction[key]) for key in _TRANSACTION_KEYS)
    ):
        raise HistoryRegistryIntegrityError("registry event schema mismatch")
    try:
        history_through = date.fromisoformat(suffix["history_through"])
    except ValueError as exc:
        raise HistoryRegistryIntegrityError("registry event schema mismatch") from exc
    if history_through.isoformat() != suffix["history_through"]:
        raise HistoryRegistryIntegrityError("registry event schema mismatch")


def _registry_events(raw: bytes) -> list[dict[str, Any]]:
    lines = raw.splitlines(keepends=True)
    if not lines or any(not line.endswith(b"\n") for line in lines):
        raise HistoryRegistryIntegrityError("registry is truncated")
    events: list[dict[str, Any]] = []
    for line in lines:
        try:
            event = json.loads(line)
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise HistoryRegistryIntegrityError(
                "registry event is invalid JSON"
            ) from exc
        if not isinstance(event, dict) or _canonical_json(event) + b"\n" != line:
            raise HistoryRegistryIntegrityError("registry event is not canonical JSON")
        events.append(event)
    return events


def _validate_event_chain(
    events: list[dict[str, Any]],
    genesis_raw: bytes,
    registry_raw: bytes,
) -> None:
    if not registry_raw.startswith(genesis_raw):
        raise HistoryRegistryIntegrityError("registered genesis event was rewritten")
    previous = ""
    for sequence, event in enumerate(events):
        _validate_event_schema(event)
        recorded_hash = event.get("event_sha256")
        body = dict(event)
        body.pop("event_sha256", None)
        if (
            not isinstance(recorded_hash, str)
            or sha256(_canonical_json(body)).hexdigest() != recorded_hash
        ):
            raise HistoryRegistryIntegrityError("registry event SHA-256 mismatch")
        expected_kind = "genesis_migration" if sequence == 0 else "append"
        expected_previous = event["seal"]["sha256"] if sequence == 0 else previous
        if (
            event.get("sequence") != sequence
            or event.get("event_kind") != expected_kind
            or event.get("previous_event_sha256") != expected_previous
        ):
            raise HistoryRegistryIntegrityError("registry event chain mismatch")
        previous = recorded_hash
    if events[0].get("event_sha256") != GENESIS_EVENT_SHA256:
        raise HistoryRegistryIntegrityError(
            "registered genesis event identity mismatch"
        )


def _validated_suffix_raw(
    repository: Path,
    event: dict[str, Any],
) -> bytes:
    suffix = event["suffix"]
    git_blob, raw = _git_blob(
        repository,
        event["transaction"]["suffix_commit"],
        suffix["path"],
    )
    if (
        git_blob != suffix["git_blob"]
        or len(raw) != suffix["bytes"]
        or sha256(raw).hexdigest() != suffix["sha256"]
    ):
        raise HistoryRegistryIntegrityError("registered history blob identity mismatch")
    return raw


def _validate_event_semantics(
    repository: Path,
    events: list[dict[str, Any]],
) -> tuple[bytes, ...]:
    genesis_seal = events[0]["seal"]
    previous_suffix = events[0]["suffix"]
    suffix_raws = [_validated_suffix_raw(repository, events[0])]
    if suffix_raws[0].count(b"\n") != previous_suffix["event_count"]:
        raise HistoryRegistryIntegrityError("registry event semantic mismatch")
    for event in events[1:]:
        suffix = event["suffix"]
        transaction = event["transaction"]
        if (
            event["seal"] != genesis_seal
            or suffix["event_count"] != previous_suffix["event_count"] + 1
            or suffix["bytes"] <= previous_suffix["bytes"]
            or date.fromisoformat(suffix["history_through"])
            <= date.fromisoformat(previous_suffix["history_through"])
            or suffix["git_blob"] == previous_suffix["git_blob"]
            or suffix["sha256"] == previous_suffix["sha256"]
            or suffix["head_event_sha256"] == previous_suffix["head_event_sha256"]
            or len(set(transaction.values())) != len(_TRANSACTION_KEYS)
        ):
            raise HistoryRegistryIntegrityError("registry event semantic mismatch")
        suffix_raw = _validated_suffix_raw(repository, event)
        previous_raw = suffix_raws[-1]
        appended = (
            suffix_raw[len(previous_raw) :]
            if suffix_raw.startswith(previous_raw)
            else b""
        )
        try:
            appended_event = json.loads(appended)
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise HistoryRegistryIntegrityError(
                "suffix is not an append-only canonical JSONL extension"
            ) from exc
        if (
            not suffix_raw.startswith(previous_raw)
            or appended.count(b"\n") != 1
            or not isinstance(appended_event, dict)
            or _canonical_json(appended_event) + b"\n" != appended
        ):
            raise HistoryRegistryIntegrityError(
                "suffix is not an append-only canonical JSONL extension"
            )
        appended_draw = appended_event.get("draw")
        if (
            suffix_raw.count(b"\n") != suffix["event_count"]
            or appended_event.get("schema_version") != _SUFFIX_SCHEMA_VERSION
            or appended_event.get("incident_id") != INCIDENT_ID
            or appended_event.get("sequence") != suffix["event_count"] - 1
            or appended_event.get("base_seal_sha256") != genesis_seal["sha256"]
            or appended_event.get("evidence_commit") != transaction["evidence_commit"]
            or appended_event.get("event_sha256") != suffix["head_event_sha256"]
            or not isinstance(appended_draw, dict)
            or appended_draw.get("draw_date") != suffix["history_through"]
        ):
            raise HistoryRegistryIntegrityError("registry event semantic mismatch")
        suffix_raws.append(suffix_raw)
        previous_suffix = suffix
    return tuple(suffix_raws)


def _publication_commits(
    repository: Path,
    revision: str,
    events: list[dict[str, Any]],
    registry_raw: bytes,
) -> tuple[str, ...]:
    parents = _ancestry_parents(repository, revision)
    lines = registry_raw.splitlines(keepends=True)
    publications = [GENESIS_COMMIT]
    for sequence, event in enumerate(events[1:], start=1):
        base_commit = event["transaction"]["base_commit"]
        suffix_commit = event["transaction"]["suffix_commit"]
        previous_raw = b"".join(lines[:sequence])
        expected_raw = b"".join(lines[: sequence + 1])
        _validate_transparent_base(
            repository,
            parents,
            publications[-1],
            base_commit,
            events[sequence - 1],
            previous_raw,
        )
        candidates: list[str] = []
        for commit, commit_parents in parents.items():
            if commit_parents != (suffix_commit,):
                continue
            try:
                _, candidate_raw = _git_blob(repository, commit, REGISTRY_PATH)
            except HistoryRegistryIntegrityError:
                continue
            if candidate_raw == expected_raw:
                candidates.append(commit)
        if len(candidates) != 1:
            raise HistoryRegistryIntegrityError(
                "registry publication topology mismatch"
            )
        publication = candidates[0]
        _validate_transaction_closure(repository, parents, event, publication)
        publications.append(publication)
    _validate_transparent_range(
        repository,
        parents,
        publications[-1],
        revision,
    )
    return tuple(publications)


def _is_ancestor(
    parents: dict[str, tuple[str, ...]],
    ancestor: str,
    descendant: str,
) -> bool:
    pending = [descendant]
    visited: set[str] = set()
    while pending:
        commit = pending.pop()
        if commit == ancestor:
            return True
        if commit in visited:
            continue
        visited.add(commit)
        pending.extend(parents.get(commit, ()))
    return False


def _reachable_commits(
    parents: dict[str, tuple[str, ...]],
    start: str,
) -> set[str]:
    pending = [start]
    reachable: set[str] = set()
    while pending:
        commit = pending.pop()
        if commit in reachable:
            continue
        reachable.add(commit)
        pending.extend(parents.get(commit, ()))
    return reachable


def _reserved_tree_diff(repository: Path, anchor: str, commit: str) -> bytes:
    return _git_bytes(
        repository,
        "diff",
        "--name-only",
        anchor,
        commit,
        "--",
        REGISTRY_PATH,
        _SEAL_PATH,
        _SUFFIX_PATH,
        "evidence/live_sources",
    )


def _validate_transparent_range(
    repository: Path,
    parents: dict[str, tuple[str, ...]],
    publication_commit: str,
    endpoint: str,
) -> None:
    if not _is_ancestor(parents, publication_commit, endpoint):
        raise HistoryRegistryIntegrityError("registry transparent ancestry mismatch")
    publication_ancestry = _reachable_commits(parents, publication_commit)
    endpoint_only = _reachable_commits(parents, endpoint) - publication_ancestry
    for commit in endpoint_only:
        commit_parents = parents.get(commit, ())
        if not commit_parents:
            raise HistoryRegistryIntegrityError(
                "registry transparent ancestry mismatch"
            )
        if _is_ancestor(parents, publication_commit, commit):
            changed = _reserved_tree_diff(repository, publication_commit, commit)
        else:
            changed = any(
                _reserved_tree_diff(repository, parent, commit)
                for parent in commit_parents
            )
        if changed:
            raise HistoryRegistryIntegrityError(
                "registry reserved path changed outside a publication"
            )


def _validate_transparent_base(
    repository: Path,
    parents: dict[str, tuple[str, ...]],
    previous_publication: str,
    base_commit: str,
    previous_event: dict[str, Any],
    previous_registry_raw: bytes,
) -> None:
    _validate_transparent_range(
        repository,
        parents,
        previous_publication,
        base_commit,
    )
    registry_blob, registry_raw = _git_blob(repository, base_commit, REGISTRY_PATH)
    seal_blob, seal_raw = _git_blob(repository, base_commit, _SEAL_PATH)
    suffix_blob, suffix_raw = _git_blob(repository, base_commit, _SUFFIX_PATH)
    seal = previous_event["seal"]
    suffix = previous_event["suffix"]
    if (
        registry_raw != previous_registry_raw
        or registry_blob
        != _git_blob(repository, previous_publication, REGISTRY_PATH)[0]
        or seal_blob != seal["git_blob"]
        or len(seal_raw) != seal["bytes"]
        or sha256(seal_raw).hexdigest() != seal["sha256"]
        or suffix_blob != suffix["git_blob"]
        or len(suffix_raw) != suffix["bytes"]
        or sha256(suffix_raw).hexdigest() != suffix["sha256"]
    ):
        raise HistoryRegistryIntegrityError(
            "registry transaction base identity mismatch"
        )


def _commit_changes(repository: Path, commit: str) -> tuple[tuple[str, str], ...]:
    try:
        lines = (
            _git_bytes(
                repository,
                "diff-tree",
                "--no-commit-id",
                "--no-renames",
                "--name-status",
                "-r",
                commit,
            )
            .decode("utf-8")
            .splitlines()
        )
        changes = tuple(tuple(line.split("\t", 1)) for line in lines)
    except UnicodeError as exc:
        raise HistoryRegistryIntegrityError(
            "registry transaction closure mismatch"
        ) from exc
    if any(len(change) != 2 for change in changes):
        raise HistoryRegistryIntegrityError("registry transaction closure mismatch")
    return changes  # type: ignore[return-value]


def _validate_transaction_closure(
    repository: Path,
    parents: dict[str, tuple[str, ...]],
    event: dict[str, Any],
    publication_commit: str,
) -> None:
    transaction = event["transaction"]
    base_commit = transaction["base_commit"]
    evidence_commit = transaction["evidence_commit"]
    suffix_commit = transaction["suffix_commit"]
    if (
        parents.get(evidence_commit) != (base_commit,)
        or parents.get(suffix_commit) != (evidence_commit,)
        or parents.get(publication_commit) != (suffix_commit,)
    ):
        raise HistoryRegistryIntegrityError("registry transaction closure mismatch")

    evidence_changes = _commit_changes(repository, evidence_commit)
    evidence_paths = sorted(path for status, path in evidence_changes if status == "A")
    evidence_matches = [_EVIDENCE_PATH_RE.fullmatch(path) for path in evidence_paths]
    if (
        len(evidence_changes) != 2
        or len(set(evidence_paths)) != 2
        or any(status != "A" for status, _ in evidence_changes)
        or any(match is None for match in evidence_matches)
        or {match["authority"] for match in evidence_matches if match is not None}
        != {"loto_quebec", "wclc"}
        or {match["draw_date"] for match in evidence_matches if match is not None}
        != {event["suffix"]["history_through"]}
    ):
        raise HistoryRegistryIntegrityError("registry transaction closure mismatch")
    for path, match in zip(evidence_paths, evidence_matches, strict=True):
        _, evidence_raw = _git_blob(repository, evidence_commit, path)
        if match is None or sha256(evidence_raw).hexdigest() != match["sha256"]:
            raise HistoryRegistryIntegrityError("registry transaction closure mismatch")

    if _commit_changes(repository, suffix_commit) != (("M", _SUFFIX_PATH),):
        raise HistoryRegistryIntegrityError("registry transaction closure mismatch")
    if _commit_changes(repository, publication_commit) != (("M", REGISTRY_PATH),):
        raise HistoryRegistryIntegrityError("registry transaction closure mismatch")


def load_history_registry(
    repository: str | Path,
    revision: str,
) -> HistoryRegistryState:
    """Load the latest history authority recorded at an exact Git revision."""

    repository_path = _repository_path(repository)
    _require_full_history(repository_path)
    resolved_revision = _resolve_exact_commit(repository_path, revision)
    _verify_genesis(repository_path, resolved_revision)

    registry_blob, registry_raw = _git_blob(
        repository_path, resolved_revision, REGISTRY_PATH
    )
    genesis_blob, genesis_raw = _git_blob(
        repository_path, GENESIS_COMMIT, REGISTRY_PATH
    )
    if (
        genesis_blob != GENESIS_GIT_BLOB
        or len(genesis_raw) != GENESIS_BYTES
        or sha256(genesis_raw).hexdigest() != GENESIS_FILE_SHA256
    ):
        raise HistoryRegistryIntegrityError("registered genesis file identity mismatch")
    events = _registry_events(registry_raw)
    _validate_event_chain(events, genesis_raw, registry_raw)
    suffix_raws = _validate_event_semantics(repository_path, events)
    publications = _publication_commits(
        repository_path, resolved_revision, events, registry_raw
    )
    latest = events[-1]

    seal = latest["seal"]
    suffix = latest["suffix"]
    transaction = latest["transaction"]
    seal_blob, seal_raw = _git_blob(repository_path, seal["commit"], seal["path"])
    suffix_blob, suffix_raw = _git_blob(
        repository_path, transaction["suffix_commit"], suffix["path"]
    )
    if (
        seal_blob != seal["git_blob"]
        or len(seal_raw) != seal["bytes"]
        or sha256(seal_raw).hexdigest() != seal["sha256"]
        or suffix_blob != suffix["git_blob"]
        or suffix_raw != suffix_raws[-1]
    ):
        raise HistoryRegistryIntegrityError("registered history blob identity mismatch")
    revision_seal_blob, revision_seal_raw = _git_blob(
        repository_path, resolved_revision, seal["path"]
    )
    revision_suffix_blob, revision_suffix_raw = _git_blob(
        repository_path, resolved_revision, suffix["path"]
    )
    if (
        revision_seal_blob != seal["git_blob"]
        or revision_seal_raw != seal_raw
        or revision_suffix_blob != suffix["git_blob"]
        or revision_suffix_raw != suffix_raw
    ):
        raise HistoryRegistryIntegrityError(
            "resolved revision does not carry the registered history blobs"
        )

    return HistoryRegistryState(
        sequence=latest["sequence"],
        event_kind=latest["event_kind"],
        event_sha256=latest["event_sha256"],
        seal=RegistrySealIdentity(**seal),
        suffix=RegistrySuffixIdentity(
            **{
                **suffix,
                "history_through": date.fromisoformat(suffix["history_through"]),
            }
        ),
        transaction=RegistryTransaction(**transaction),
        seal_raw=seal_raw,
        suffix_raw=suffix_raw,
        provenance=RegistryProvenance(
            registry_path=REGISTRY_PATH,
            requested_revision=revision,
            resolved_revision=resolved_revision,
            publication_commit=publications[-1],
            genesis_commit=GENESIS_COMMIT,
            genesis_parent=GENESIS_PARENT,
            git_blob=registry_blob,
            bytes=len(registry_raw),
            file_sha256=sha256(registry_raw).hexdigest(),
            event_count=len(events),
            head_event_sha256=latest["event_sha256"],
        ),
    )
