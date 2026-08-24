"""Prepare an offline, unattached operational-history publication transaction."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from hashlib import sha256
from itertools import islice
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .domain import Draw
from .official_history import parse_lotoquebec_detail_html, parse_wclc_target_html
from .operational_history import load_published_history

_INCIDENT_ID = "DI-2026-08-20-registered-history"
_SUFFIX_PATH = f"data/processed/epochs/{_INCIDENT_ID}/live_draws.jsonl"
_REGISTRY_PATH = f"evidence/operational_history/{_INCIDENT_ID}/pin-registry.jsonl"
_SUFFIX_SCHEMA = "lotto649-history-suffix-event-v1"
_REGISTRY_SCHEMA = "lotto649-history-pin-registry-event-v1"
_MAX_SOURCE_BYTES = 2 * 1024 * 1024
_AUTHORITIES = {
    "loto_quebec": {
        "provider": "Loto-Québec",
        "source_type": "loto_quebec_detail_html",
        "hostname": "loteries.lotoquebec.com",
        "path": "/en/lotteries/lotto-6-49-resultats",
    },
    "wclc": {
        "provider": "Western Canada Lottery Corporation",
        "source_type": "wclc_recent_html",
        "hostname": "www.wclc.com",
        "path": "/winning-numbers/lotto-649-extra.htm",
    },
}
_ENVIRONMENT_KEYS = {
    "PATH",
    "SYSTEMROOT",
    "WINDIR",
    "PATHEXT",
    "TMPDIR",
    "TMP",
    "TEMP",
}


class HistoryPublicationError(ValueError):
    """Raised when an offline publication transaction cannot be prepared."""


@dataclass(frozen=True)
class RawSource:
    """One already-retrieved official source asset; preparation never networks."""

    authority: str
    url: str
    retrieved_at: datetime
    raw: bytes


@dataclass(frozen=True)
class PreparedPublication:
    """Unattached B -> E -> S -> P commit identities ready for later CAS."""

    repository: Path
    base_commit: str
    evidence_commit: str
    suffix_commit: str
    publication_commit: str
    target_draw_date: date
    suffix_head_event_sha256: str
    registry_head_event_sha256: str


def _canonical_json(value: Any, *, newline: bool = False) -> bytes:
    try:
        raw = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise HistoryPublicationError(
            "publication value is not canonical JSON"
        ) from exc
    return raw + (b"\n" if newline else b"")


def _git_environment(
    *, index_path: Path | None = None, created_at: datetime | None = None
) -> dict[str, str]:
    environment = {
        key: value for key, value in os.environ.items() if key in _ENVIRONMENT_KEYS
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
    if index_path is not None:
        environment["GIT_INDEX_FILE"] = str(index_path)
    if created_at is not None:
        git_timestamp = created_at.strftime("%Y-%m-%dT%H:%M:%S+00:00")
        environment.update(
            {
                "GIT_AUTHOR_DATE": git_timestamp,
                "GIT_AUTHOR_EMAIL": "history-writer@lotto649.invalid",
                "GIT_AUTHOR_NAME": "LOTTO 6/49 History Writer",
                "GIT_COMMITTER_DATE": git_timestamp,
                "GIT_COMMITTER_EMAIL": "history-writer@lotto649.invalid",
                "GIT_COMMITTER_NAME": "LOTTO 6/49 History Writer",
            }
        )
    return environment


def _git(
    repository: Path,
    *arguments: str,
    input_bytes: bytes | None = None,
    index_path: Path | None = None,
    created_at: datetime | None = None,
) -> bytes:
    try:
        completed = subprocess.run(
            [
                "git",
                "-c",
                "core.splitIndex=false",
                "-c",
                "core.untrackedCache=false",
                "-c",
                "core.fsmonitor=false",
                "-c",
                "index.sparse=false",
                "-c",
                "i18n.commitEncoding=UTF-8",
                "-C",
                str(repository),
                *arguments,
            ],
            input=input_bytes,
            check=False,
            capture_output=True,
            env=_git_environment(index_path=index_path, created_at=created_at),
        )
    except OSError as exc:
        raise HistoryPublicationError("Git is unavailable") from exc
    if completed.returncode != 0:
        raise HistoryPublicationError("Git could not prepare publication objects")
    return completed.stdout


def _git_text(
    repository: Path,
    *arguments: str,
    input_bytes: bytes | None = None,
    index_path: Path | None = None,
    created_at: datetime | None = None,
) -> str:
    try:
        return (
            _git(
                repository,
                *arguments,
                input_bytes=input_bytes,
                index_path=index_path,
                created_at=created_at,
            )
            .decode("ascii")
            .strip()
        )
    except UnicodeError as exc:
        raise HistoryPublicationError(
            "Git returned an invalid object identity"
        ) from exc


def _utc_second(value: object, field_name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise HistoryPublicationError(f"{field_name} must be timezone-aware")
    try:
        offset = value.utcoffset()
    except (OverflowError, TypeError, ValueError) as exc:
        raise HistoryPublicationError(f"{field_name} is invalid") from exc
    if offset is None:
        raise HistoryPublicationError(f"{field_name} must be timezone-aware")
    try:
        result = value.astimezone(UTC)
    except (OverflowError, TypeError, ValueError) as exc:
        raise HistoryPublicationError(f"{field_name} is invalid") from exc
    if result.microsecond != 0:
        raise HistoryPublicationError(f"{field_name} must have whole-second precision")
    return result


def _next_draw_date(high_water: date) -> date:
    if high_water.weekday() == 2:
        return high_water + timedelta(days=3)
    if high_water.weekday() == 5:
        return high_water + timedelta(days=4)
    raise HistoryPublicationError("published history high-water is off schedule")


def _draw_payload(draw: Draw) -> dict[str, Any]:
    return {
        "draw_date": draw.draw_date.isoformat(),
        "numbers": list(draw.numbers),
        "bonus": draw.bonus,
    }


def _validate_url(source: RawSource, target_date: date) -> tuple[dict[str, str], str]:
    authority = _AUTHORITIES.get(source.authority)
    if authority is None or type(source.url) is not str:
        raise HistoryPublicationError(
            "exactly one source per official authority is required"
        )
    try:
        parsed = urlsplit(source.url)
        port = parsed.port
    except ValueError as exc:
        raise HistoryPublicationError("source URL is invalid") from exc
    if (
        parsed.scheme != "https"
        or parsed.hostname != authority["hostname"]
        or parsed.path != authority["path"]
        or parsed.username is not None
        or parsed.password is not None
        or port not in {None, 443}
        or parsed.fragment
    ):
        raise HistoryPublicationError("source URL does not match its authority")
    expected_query = (
        f"date={target_date.isoformat()}" if source.authority == "loto_quebec" else ""
    )
    expected_url = f"https://{authority['hostname']}{authority['path']}"
    if expected_query:
        expected_url = f"{expected_url}?{expected_query}"
    if source.url != expected_url:
        raise HistoryPublicationError("source URL is not canonical")
    return authority, expected_url


def _validate_sources(
    sources: Sequence[RawSource], target_date: date, created_at: datetime
) -> tuple[Draw, tuple[dict[str, Any], ...], dict[str, bytes]]:
    if not isinstance(sources, Sequence) or isinstance(
        sources, (str, bytes, bytearray)
    ):
        raise HistoryPublicationError("exactly two RawSource values are required")
    try:
        source_values = tuple(islice(iter(sources), 3))
    except Exception as exc:
        raise HistoryPublicationError(
            "exactly two RawSource values are required"
        ) from exc
    if len(source_values) != 2 or any(
        type(source) is not RawSource for source in source_values
    ):
        raise HistoryPublicationError("exactly two RawSource values are required")
    if any(type(source.authority) is not str for source in source_values):
        raise HistoryPublicationError(
            "exactly one source per official authority is required"
        )
    by_authority = {source.authority: source for source in source_values}
    if set(by_authority) != set(_AUTHORITIES) or len(by_authority) != len(
        source_values
    ):
        raise HistoryPublicationError(
            "exactly one source per official authority is required"
        )
    if any(type(source.raw) is not bytes or not source.raw for source in source_values):
        raise HistoryPublicationError("source bytes must be nonempty immutable bytes")
    if any(len(source.raw) > _MAX_SOURCE_BYTES for source in source_values):
        raise HistoryPublicationError("source size exceeds the offline safety limit")
    if len({source.raw for source in source_values}) != len(source_values):
        raise HistoryPublicationError("official sources must have distinct raw bytes")

    parsed_draws: dict[str, Draw] = {}
    receipts: list[dict[str, Any]] = []
    evidence: dict[str, bytes] = {}
    for authority_name in sorted(by_authority):
        source = by_authority[authority_name]
        authority, canonical_url = _validate_url(source, target_date)
        retrieved_at = _utc_second(source.retrieved_at, "retrieved_at")
        if retrieved_at.date() <= target_date or retrieved_at > created_at:
            raise HistoryPublicationError(
                "source retrieval time is outside the audit window"
            )
        try:
            if authority_name == "wclc":
                draw = parse_wclc_target_html(source.raw, target_date)
            else:
                draw = parse_lotoquebec_detail_html(
                    source.raw.decode("utf-8"), target_date
                )
        except (UnicodeError, RuntimeError) as exc:
            raise HistoryPublicationError(
                f"{authority_name} source does not contain one strict target draw"
            ) from exc
        parsed_draws[authority_name] = draw
        raw_sha256 = sha256(source.raw).hexdigest()
        evidence_path = (
            f"evidence/live_sources/{authority_name}/"
            f"{target_date.isoformat()}-{raw_sha256}.html"
        )
        evidence[evidence_path] = source.raw
        receipts.append(
            {
                "provider": authority["provider"],
                "source_type": authority["source_type"],
                "url": canonical_url,
                "retrieved_at": retrieved_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "evidence_path": evidence_path,
                "bytes": len(source.raw),
                "sha256": raw_sha256,
                "supported_row_sha256": "",
                "independence_group": authority_name,
            }
        )
    if parsed_draws["loto_quebec"] != parsed_draws["wclc"]:
        raise HistoryPublicationError("official sources disagree on the target draw")
    draw = parsed_draws["loto_quebec"]
    row_sha256 = sha256(_canonical_json(_draw_payload(draw))).hexdigest()
    for receipt in receipts:
        receipt["supported_row_sha256"] = row_sha256
    receipts.sort(
        key=lambda receipt: (
            receipt["independence_group"],
            receipt["provider"],
            receipt["source_type"],
            receipt["url"],
            receipt["sha256"],
        )
    )
    return draw, tuple(receipts), evidence


def _read_blob(repository: Path, git_blob: str) -> bytes:
    return _git(repository, "cat-file", "blob", git_blob)


def _hash_blob(repository: Path, raw: bytes) -> str:
    return _git_text(repository, "hash-object", "-w", "--stdin", input_bytes=raw)


def _prepare_commit(
    repository: Path,
    *,
    index_path: Path,
    parent: str,
    changes: dict[str, bytes],
    message: str,
    created_at: datetime,
) -> tuple[str, dict[str, str]]:
    _git(repository, "read-tree", parent, index_path=index_path)
    blobs: dict[str, str] = {}
    for path, raw in sorted(changes.items()):
        git_blob = _hash_blob(repository, raw)
        _git(
            repository,
            "update-index",
            "--add",
            "--cacheinfo",
            "100644",
            git_blob,
            path,
            index_path=index_path,
        )
        blobs[path] = git_blob
    tree = _git_text(repository, "write-tree", index_path=index_path)
    commit = _git_text(
        repository,
        "commit-tree",
        tree,
        "-p",
        parent,
        "-m",
        message,
        created_at=created_at,
    )
    return commit, blobs


def prepare_history_publication(
    repository: str | Path,
    *,
    expected_base_commit: str,
    sources: Sequence[RawSource],
    created_at: datetime,
) -> PreparedPublication:
    """Create an unattached B -> E -> S -> P transaction without networking."""

    if not isinstance(repository, (str, Path)):
        raise HistoryPublicationError("repository path is invalid")
    try:
        repository_path = Path(repository).resolve(strict=True)
    except OSError as exc:
        raise HistoryPublicationError("repository does not exist") from exc
    if not repository_path.is_dir():
        raise HistoryPublicationError("repository path is invalid")
    commit_time = _utc_second(created_at, "created_at")
    try:
        published = load_published_history(repository_path, expected_base_commit)
    except ValueError as exc:
        raise HistoryPublicationError(
            "expected base is not a valid published history"
        ) from exc
    target_date = _next_draw_date(published.suffix.history_through)
    draw, receipts, evidence = _validate_sources(sources, target_date, commit_time)

    suffix_raw = _read_blob(repository_path, published.registry_suffix.git_blob)
    registry_raw = _read_blob(repository_path, published.registry.git_blob)
    if (
        len(suffix_raw) != published.registry_suffix.bytes
        or sha256(suffix_raw).hexdigest() != published.registry_suffix.sha256
        or len(registry_raw) != published.registry.bytes
        or sha256(registry_raw).hexdigest() != published.registry.file_sha256
    ):
        raise HistoryPublicationError("published base blobs changed identity")

    with tempfile.TemporaryDirectory(prefix="lotto649-history-index-") as temporary:
        index_path = Path(temporary) / "index"
        evidence_commit, _ = _prepare_commit(
            repository_path,
            index_path=index_path,
            parent=expected_base_commit,
            changes=evidence,
            message=f"Record official LOTTO 6/49 sources for {target_date.isoformat()}",
            created_at=commit_time,
        )
        suffix_event = {
            "schema_version": _SUFFIX_SCHEMA,
            "incident_id": _INCIDENT_ID,
            "sequence": published.registry_suffix.event_count,
            "base_seal_sha256": published.registry_seal.sha256,
            "previous_event_sha256": published.registry_suffix.head_event_sha256,
            "evidence_commit": evidence_commit,
            "draw": _draw_payload(draw),
            "source_receipts": list(receipts),
        }
        suffix_event["event_sha256"] = sha256(_canonical_json(suffix_event)).hexdigest()
        next_suffix_raw = suffix_raw + _canonical_json(suffix_event, newline=True)
        suffix_commit, suffix_blobs = _prepare_commit(
            repository_path,
            index_path=index_path,
            parent=evidence_commit,
            changes={_SUFFIX_PATH: next_suffix_raw},
            message=f"Append verified LOTTO 6/49 draw {target_date.isoformat()}",
            created_at=commit_time,
        )
        registry_event = {
            "event_kind": "append",
            "incident_id": _INCIDENT_ID,
            "previous_event_sha256": published.registry.head_event_sha256,
            "schema_version": _REGISTRY_SCHEMA,
            "seal": {
                "bytes": published.registry_seal.bytes,
                "commit": published.registry_seal.commit,
                "git_blob": published.registry_seal.git_blob,
                "path": published.registry_seal.path,
                "sha256": published.registry_seal.sha256,
            },
            "sequence": published.registry.event_count,
            "suffix": {
                "bytes": len(next_suffix_raw),
                "event_count": published.registry_suffix.event_count + 1,
                "git_blob": suffix_blobs[_SUFFIX_PATH],
                "head_event_sha256": suffix_event["event_sha256"],
                "history_through": target_date.isoformat(),
                "path": published.registry_suffix.path,
                "sha256": sha256(next_suffix_raw).hexdigest(),
            },
            "transaction": {
                "base_commit": expected_base_commit,
                "evidence_commit": evidence_commit,
                "suffix_commit": suffix_commit,
            },
        }
        registry_event["event_sha256"] = sha256(
            _canonical_json(registry_event)
        ).hexdigest()
        next_registry_raw = registry_raw + _canonical_json(registry_event, newline=True)
        publication_commit, _ = _prepare_commit(
            repository_path,
            index_path=index_path,
            parent=suffix_commit,
            changes={_REGISTRY_PATH: next_registry_raw},
            message=f"Publish verified LOTTO 6/49 draw {target_date.isoformat()}",
            created_at=commit_time,
        )

        try:
            candidate = load_published_history(repository_path, publication_commit)
        except ValueError as exc:
            raise HistoryPublicationError(
                "candidate publication failed production validation"
            ) from exc
        if (
            candidate.registry.publication_commit != publication_commit
            or candidate.draws[-1] != draw
            or candidate.registry.head_event_sha256 != registry_event["event_sha256"]
            or candidate.suffix.head_event_sha256 != suffix_event["event_sha256"]
        ):
            raise HistoryPublicationError("candidate publication identity mismatch")

    return PreparedPublication(
        repository=repository_path,
        base_commit=expected_base_commit,
        evidence_commit=evidence_commit,
        suffix_commit=suffix_commit,
        publication_commit=publication_commit,
        target_draw_date=target_date,
        suffix_head_event_sha256=suffix_event["event_sha256"],
        registry_head_event_sha256=registry_event["event_sha256"],
    )
