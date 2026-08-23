"""Read a Git-bound corrected history through one fail-closed interface."""

from __future__ import annotations

import csv
import io
import json
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import parse_qs, urlsplit

from bs4 import BeautifulSoup

from .domain import Draw
from .official_history import (
    canonical_official_rows_sha256,
    expected_lotto649_draw_dates,
    parse_lotoquebec_detail_html,
)

_INCIDENT_ID = "DI-2026-08-20-registered-history"
_SEAL_SCHEMA = "lotto649-data-integrity-seal-v1"
_SEALED_STATUS = "sealed_closed_corrected_epoch"
_SEAL_KEYS = {
    "schema_version",
    "incident_id",
    "artifact_commit",
    "artifact_parent",
    "artifact_commit_created_at",
    "status",
    "registered_old_identity",
    "artifacts",
    "corrected_epoch",
    "reconciliation_manifest",
    "source_collection",
    "reconciliation_summary",
    "code_identities",
    "seal_body_sha256",
}
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_GIT_OID_RE = re.compile(r"^[0-9a-f]{40}$")
_REGISTERED_OLD_KEYS = {
    "byte_sha256",
    "bytes",
    "commit",
    "draw_count",
    "git_blob",
    "path",
    "rows_sha256",
}
_SOURCE_COLLECTION_KEYS = {
    "asset_count",
    "collection_line_sha256",
    "draw_count",
    "history_start",
    "history_through",
    "json_rows_sha256",
    "source_assets_sha256",
}
_SUMMARY_KEYS = {
    "old_count",
    "official_count",
    "decision_count",
    "unchanged",
    "inserted",
    "deleted",
    "updated",
    "unresolved",
    "corrected_count",
}
_CORRECTED_KEYS = {
    "path",
    "git_blob",
    "bytes",
    "file_sha256",
    "draw_count",
    "rows_sha256",
    "history_start",
    "history_through",
}
_MANIFEST_KEYS = {
    "path",
    "git_blob",
    "bytes",
    "file_sha256",
    "manifest_sha256",
}
_BASE_PATH = f"data/processed/epochs/{_INCIDENT_ID}/corrected_draws.csv"
_BASE_FILE_SHA256 = "1e1bb768877d3f1b3b901a8cb897b6f439ff80f675c57e786cb54ff1179ac8ad"
_BASE_ROWS_SHA256 = "58988bbb130be2142bc5a2b20df571cc458eabe66cd873773f55ca1dbfae8874"
_BASE_DRAW_COUNT = 4_442
_BASE_HISTORY_START = "1982-06-12"
_BASE_HISTORY_THROUGH = "2026-08-15"
_INCIDENT_DIRECTORY = f"evidence/data_integrity/{_INCIDENT_ID}"
_MANIFEST_PATH = f"{_INCIDENT_DIRECTORY}/reconciliation.manifest.json"
_ARTIFACT_PATHS = {
    _BASE_PATH,
    f"{_INCIDENT_DIRECTORY}/incident.json",
    f"{_INCIDENT_DIRECTORY}/official_draws.csv",
    f"{_INCIDENT_DIRECTORY}/reconciliation.manifest.json",
    f"{_INCIDENT_DIRECTORY}/reviewed-adjudication.json",
    f"{_INCIDENT_DIRECTORY}/source-index.json",
}
_CODE_PATHS = {
    "src/lotto649/data_integrity.py",
    "src/lotto649/official_history.py",
    "tests/test_data_integrity.py",
    "tests/test_data_integrity_incident.py",
    "tests/test_official_history.py",
    "tools/build_data_integrity_incident.py",
}
_INVENTORY_ENTRY_KEYS = {"git_blob", "bytes", "sha256"}
_SUFFIX_PATH = f"data/processed/epochs/{_INCIDENT_ID}/live_draws.jsonl"
_SUFFIX_SCHEMA = "lotto649-history-suffix-event-v1"
_SUFFIX_EVENT_KEYS = {
    "schema_version",
    "incident_id",
    "sequence",
    "base_seal_sha256",
    "previous_event_sha256",
    "evidence_commit",
    "draw",
    "source_receipts",
    "event_sha256",
}
_DRAW_KEYS = {"draw_date", "numbers", "bonus"}
_RECEIPT_KEYS = {
    "provider",
    "source_type",
    "url",
    "retrieved_at",
    "evidence_path",
    "bytes",
    "sha256",
    "supported_row_sha256",
    "independence_group",
}
_RECEIPT_AUTHORITIES = {
    "wclc": {
        "provider": "Western Canada Lottery Corporation",
        "source_type": "wclc_recent_html",
        "hostname": "www.wclc.com",
        "url_path": "/winning-numbers/lotto-649-extra.htm",
        "evidence_prefix": "evidence/live_sources/wclc/",
    },
    "loto_quebec": {
        "provider": "Loto-Québec",
        "source_type": "loto_quebec_detail_html",
        "hostname": "loteries.lotoquebec.com",
        "url_path": "/en/lotteries/lotto-6-49-resultats",
        "evidence_prefix": "evidence/live_sources/loto_quebec/",
    },
}
_WEEKDAYS = "Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday"
_MONTHS = (
    "January|February|March|April|May|June|July|August|September|October|"
    "November|December"
)
_NEXT_WCLC_DATE_RE = re.compile(
    rf"\b(?:{_WEEKDAYS}),\s+(?:{_MONTHS})\s+\d{{1,2}},\s+\d{{4}}\b"
)
_UTC_TIMESTAMP_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"
)


class VerifiedHistoryIntegrityError(ValueError):
    """Raised when sealed history evidence does not satisfy its authority."""


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
        raise VerifiedHistoryIntegrityError("JSON value is not canonical") from exc
    return raw + (b"\n" if newline else b"")


def _git_environment() -> dict[str, str]:
    """Return a minimal Git environment without caller-selected authorities."""
    environment = {
        key: os.environ[key]
        for key in (
            "PATH",
            "SYSTEMROOT",
            "WINDIR",
            "PATHEXT",
            "TMPDIR",
            "TMP",
            "TEMP",
        )
        if key in os.environ
    }
    environment.update(
        {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_NO_LAZY_FETCH": "1",
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_GRAFT_FILE": os.devnull,
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_TERMINAL_PROMPT": "0",
            "LC_ALL": "C",
            "LANG": "C",
        }
    )
    return environment


def _is_integer(value: object) -> bool:
    return type(value) is int and value >= 0


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and _SHA256_RE.fullmatch(value) is not None


def _has_keys(value: object, keys: set[str]) -> bool:
    return isinstance(value, dict) and set(value) == keys


def _validate_frozen_nested_schema(seal: dict[str, Any]) -> None:
    old = seal.get("registered_old_identity")
    source = seal.get("source_collection")
    summary = seal.get("reconciliation_summary")
    corrected = seal.get("corrected_epoch")
    manifest = seal.get("reconciliation_manifest")
    if (
        not _has_keys(old, _REGISTERED_OLD_KEYS)
        or not _is_sha256(old["byte_sha256"])
        or not _is_integer(old["bytes"])
        or not isinstance(old["commit"], str)
        or _GIT_OID_RE.fullmatch(old["commit"]) is None
        or not _is_integer(old["draw_count"])
        or not isinstance(old["git_blob"], str)
        or _GIT_OID_RE.fullmatch(old["git_blob"]) is None
        or not isinstance(old["path"], str)
        or not old["path"]
        or not _is_sha256(old["rows_sha256"])
        or not _has_keys(source, _SOURCE_COLLECTION_KEYS)
        or not _is_integer(source["asset_count"])
        or not _is_sha256(source["collection_line_sha256"])
        or not _is_integer(source["draw_count"])
        or not isinstance(source["history_start"], str)
        or not isinstance(source["history_through"], str)
        or not _is_sha256(source["json_rows_sha256"])
        or not _is_sha256(source["source_assets_sha256"])
        or not _has_keys(summary, _SUMMARY_KEYS)
        or any(not _is_integer(summary[key]) for key in _SUMMARY_KEYS)
        or not _has_keys(corrected, _CORRECTED_KEYS)
        or not isinstance(corrected["path"], str)
        or not isinstance(corrected["git_blob"], str)
        or _GIT_OID_RE.fullmatch(corrected["git_blob"]) is None
        or not _is_integer(corrected["bytes"])
        or not _is_sha256(corrected["file_sha256"])
        or not _is_integer(corrected["draw_count"])
        or not _is_sha256(corrected["rows_sha256"])
        or not isinstance(corrected["history_start"], str)
        or not isinstance(corrected["history_through"], str)
        or not _has_keys(manifest, _MANIFEST_KEYS)
        or not isinstance(manifest["path"], str)
        or not isinstance(manifest["git_blob"], str)
        or _GIT_OID_RE.fullmatch(manifest["git_blob"]) is None
        or not _is_integer(manifest["bytes"])
        or not _is_sha256(manifest["file_sha256"])
        or not _is_sha256(manifest["manifest_sha256"])
    ):
        raise VerifiedHistoryIntegrityError("frozen nested seal schema mismatch")


def _validate_inventory_schema(seal: dict[str, Any]) -> None:
    for field_name, expected_paths in (
        ("artifacts", _ARTIFACT_PATHS),
        ("code_identities", _CODE_PATHS),
    ):
        inventory = seal.get(field_name)
        if not isinstance(inventory, dict) or set(inventory) != expected_paths:
            raise VerifiedHistoryIntegrityError("frozen artifact inventory mismatch")
        for path, entry in inventory.items():
            if (
                not _has_keys(entry, _INVENTORY_ENTRY_KEYS)
                or not isinstance(entry["git_blob"], str)
                or _GIT_OID_RE.fullmatch(entry["git_blob"]) is None
                or not _is_integer(entry["bytes"])
                or not _is_sha256(entry["sha256"])
                or not isinstance(path, str)
            ):
                raise VerifiedHistoryIntegrityError(
                    "frozen artifact inventory schema mismatch"
                )


@dataclass(frozen=True)
class SealProvenance:
    path: str
    file_sha256: str
    body_sha256: str
    artifact_commit: str
    artifact_parent: str
    status: str


@dataclass(frozen=True)
class BaseProvenance:
    path: str
    git_blob: str
    bytes: int
    file_sha256: str
    rows_sha256: str
    draw_count: int
    history_start: date
    history_through: date


@dataclass(frozen=True)
class SuffixProvenance:
    """Authenticated suffix state.

    ``base_seal_sha256`` is always the chain anchor. With zero events,
    ``head_event_sha256`` is ``None``. ``file_sha256`` is the empty-byte hash
    when an empty suffix file was supplied, and ``None`` only when no suffix
    path was configured.
    """

    path: str | None
    bytes: int
    file_sha256: str | None
    event_count: int
    base_seal_sha256: str
    head_event_sha256: str | None
    history_through: date
    evidence_commits: tuple[str, ...]


@dataclass(frozen=True)
class VerifiedHistory:
    draws: tuple[Draw, ...]
    epoch: str
    seal: SealProvenance
    base: BaseProvenance
    suffix: SuffixProvenance


def _git_bytes(repository: Path, *arguments: str) -> bytes:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repository), *arguments],
            check=False,
            capture_output=True,
            env=_git_environment(),
        )
    except OSError as exc:
        raise VerifiedHistoryIntegrityError("Git is unavailable") from exc
    if completed.returncode != 0:
        raise VerifiedHistoryIntegrityError("sealed Git artifact is unavailable")
    return completed.stdout


def _git_commit_created_at(repository: Path, commit: str) -> datetime:
    try:
        raw = _git_bytes(repository, "show", "-s", "--format=%cI", commit)
        value = raw.decode("ascii").strip()
        timestamp = datetime.fromisoformat(value)
    except (UnicodeError, ValueError) as exc:
        raise VerifiedHistoryIntegrityError("Git commit timestamp is invalid") from exc
    if timestamp.tzinfo is None:
        raise VerifiedHistoryIntegrityError("Git commit timestamp is invalid")
    return timestamp.astimezone(UTC)


def _validate_artifact_commit(repository: Path, seal: dict[str, Any]) -> None:
    artifact_commit = seal.get("artifact_commit")
    artifact_parent = seal.get("artifact_parent")
    if (
        not isinstance(artifact_commit, str)
        or _GIT_OID_RE.fullmatch(artifact_commit) is None
    ):
        raise VerifiedHistoryIntegrityError("artifact commit identity is invalid")
    if (
        not isinstance(artifact_parent, str)
        or _GIT_OID_RE.fullmatch(artifact_parent) is None
    ):
        raise VerifiedHistoryIntegrityError("artifact parent identity is invalid")
    try:
        resolved = (
            _git_bytes(repository, "rev-parse", f"{artifact_commit}^{{commit}}")
            .decode("ascii")
            .strip()
        )
        lineage = (
            _git_bytes(repository, "rev-list", "--parents", "-n", "1", artifact_commit)
            .decode("ascii")
            .strip()
            .split()
        )
    except UnicodeError as exc:
        raise VerifiedHistoryIntegrityError(
            "artifact commit identity is invalid"
        ) from exc
    if resolved != artifact_commit or not lineage or lineage[0] != artifact_commit:
        raise VerifiedHistoryIntegrityError("artifact commit identity mismatch")
    if lineage != [artifact_commit, artifact_parent]:
        raise VerifiedHistoryIntegrityError("artifact parent mismatch")
    try:
        changed_paths = (
            _git_bytes(
                repository,
                "diff-tree",
                "--no-commit-id",
                "--name-only",
                "-r",
                artifact_commit,
            )
            .decode("utf-8")
            .splitlines()
        )
    except UnicodeError as exc:
        raise VerifiedHistoryIntegrityError("artifact closure is invalid") from exc
    if set(changed_paths) != _ARTIFACT_PATHS | _CODE_PATHS or len(changed_paths) != len(
        _ARTIFACT_PATHS | _CODE_PATHS
    ):
        raise VerifiedHistoryIntegrityError("artifact closure mismatch")


def _git_artifact_bytes(repository: Path, commit: str, path: str) -> tuple[str, bytes]:
    try:
        tree_entry = (
            _git_bytes(repository, "ls-tree", commit, "--", path)
            .decode("utf-8")
            .strip()
        )
        metadata, listed_path = tree_entry.split("\t", 1)
        mode, object_type, git_blob = metadata.split(" ", 2)
    except (UnicodeError, ValueError) as exc:
        raise VerifiedHistoryIntegrityError("artifact integrity mismatch") from exc
    if listed_path != path or mode not in {"100644", "100755"} or object_type != "blob":
        raise VerifiedHistoryIntegrityError("artifact integrity mismatch")
    raw = _git_bytes(repository, "show", f"{commit}:{path}")
    return git_blob, raw


def _validate_git_inventories(repository: Path, seal: dict[str, Any]) -> None:
    commit = seal["artifact_commit"]
    for inventory_name in ("artifacts", "code_identities"):
        for path, expected in seal[inventory_name].items():
            git_blob, raw = _git_artifact_bytes(repository, commit, path)
            if (
                git_blob != expected["git_blob"]
                or len(raw) != expected["bytes"]
                or sha256(raw).hexdigest() != expected["sha256"]
            ):
                raise VerifiedHistoryIntegrityError("artifact integrity mismatch")


def _validate_corrected_epoch_identity(seal: dict[str, Any]) -> None:
    corrected = seal["corrected_epoch"]
    inventory = seal["artifacts"][_BASE_PATH]
    if (
        corrected["path"] != _BASE_PATH
        or corrected["git_blob"] != inventory["git_blob"]
        or corrected["bytes"] != inventory["bytes"]
        or corrected["file_sha256"] != inventory["sha256"]
        or corrected["draw_count"] != _BASE_DRAW_COUNT
        or corrected["rows_sha256"] != _BASE_ROWS_SHA256
        or corrected["history_start"] != _BASE_HISTORY_START
        or corrected["history_through"] != _BASE_HISTORY_THROUGH
    ):
        raise VerifiedHistoryIntegrityError("corrected epoch identity mismatch")


def _validate_seal_semantics(repository: Path, seal: dict[str, Any]) -> None:
    created_at = seal["artifact_commit_created_at"]
    if (
        not isinstance(created_at, str)
        or _UTC_TIMESTAMP_RE.fullmatch(created_at) is None
    ):
        raise VerifiedHistoryIntegrityError("seal semantic mismatch")
    try:
        timestamp = datetime.fromisoformat(created_at.removesuffix("Z") + "+00:00")
    except ValueError as exc:
        raise VerifiedHistoryIntegrityError("seal semantic mismatch") from exc
    if timestamp.tzinfo != UTC:
        raise VerifiedHistoryIntegrityError("seal semantic mismatch")
    git_created_at = _git_commit_created_at(repository, seal["artifact_commit"])
    expected_created_at = git_created_at.strftime("%Y-%m-%dT%H:%M:%SZ")
    if created_at != expected_created_at:
        raise VerifiedHistoryIntegrityError("seal semantic mismatch")

    manifest = seal["reconciliation_manifest"]
    manifest_inventory = seal["artifacts"][_MANIFEST_PATH]
    if (
        manifest["path"] != _MANIFEST_PATH
        or manifest["git_blob"] != manifest_inventory["git_blob"]
        or manifest["bytes"] != manifest_inventory["bytes"]
        or manifest["file_sha256"] != manifest_inventory["sha256"]
    ):
        raise VerifiedHistoryIntegrityError("seal semantic mismatch")

    expected_source = {
        "asset_count": 109,
        "collection_line_sha256": (
            "7e3328896d5bb7950c10cf5b9cca0e4d7cadd7265c6d4a4f6b3dcc8793b0a88a"
        ),
        "draw_count": _BASE_DRAW_COUNT,
        "history_start": _BASE_HISTORY_START,
        "history_through": _BASE_HISTORY_THROUGH,
        "json_rows_sha256": _BASE_ROWS_SHA256,
        "source_assets_sha256": (
            "1be14241443477f7ba347c8fe87605bb4c1367c7b7390f5f05762478a4c36b96"
        ),
    }
    expected_summary = {
        "old_count": 4_432,
        "official_count": 4_442,
        "decision_count": 4_444,
        "unchanged": 4_421,
        "inserted": 12,
        "deleted": 2,
        "updated": 9,
        "unresolved": 0,
        "corrected_count": 4_442,
    }
    if (
        seal["source_collection"] != expected_source
        or seal["reconciliation_summary"] != expected_summary
    ):
        raise VerifiedHistoryIntegrityError("seal semantic mismatch")

    old = seal["registered_old_identity"]
    if old["path"] != "data/processed/draws.csv" or old["draw_count"] != 4_432:
        raise VerifiedHistoryIntegrityError("seal semantic mismatch")
    try:
        old_blob, old_raw = _git_artifact_bytes(repository, old["commit"], old["path"])
        old_draws = _parse_csv(old_raw)
    except VerifiedHistoryIntegrityError as exc:
        raise VerifiedHistoryIntegrityError("seal semantic mismatch") from exc
    if (
        old_blob != old["git_blob"]
        or len(old_raw) != old["bytes"]
        or sha256(old_raw).hexdigest() != old["byte_sha256"]
        or len(old_draws) != old["draw_count"]
        or canonical_official_rows_sha256(old_draws) != old["rows_sha256"]
    ):
        raise VerifiedHistoryIntegrityError("seal semantic mismatch")
    completed = subprocess.run(
        [
            "git",
            "-C",
            str(repository),
            "merge-base",
            "--is-ancestor",
            old["commit"],
            seal["artifact_commit"],
        ],
        check=False,
        capture_output=True,
        env=_git_environment(),
    )
    if completed.returncode != 0:
        raise VerifiedHistoryIntegrityError("seal semantic mismatch")


def _canonical_csv(draws: tuple[Draw, ...]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(["draw_date", "n1", "n2", "n3", "n4", "n5", "n6", "bonus"])
    for draw in draws:
        writer.writerow([draw.draw_date.isoformat(), *draw.numbers, draw.bonus])
    return output.getvalue().encode("utf-8")


def _draw_from_payload(value: object) -> Draw:
    if not _has_keys(value, _DRAW_KEYS):
        raise VerifiedHistoryIntegrityError("suffix Draw schema mismatch")
    raw_date = value["draw_date"]
    raw_numbers = value["numbers"]
    raw_bonus = value["bonus"]
    if (
        not isinstance(raw_date, str)
        or not isinstance(raw_numbers, list)
        or len(raw_numbers) != 6
        or any(type(number) is not int for number in raw_numbers)
        or type(raw_bonus) is not int
    ):
        raise VerifiedHistoryIntegrityError("suffix Draw schema mismatch")
    try:
        draw_date = date.fromisoformat(raw_date)
        draw = Draw(draw_date, tuple(raw_numbers), raw_bonus)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise VerifiedHistoryIntegrityError("suffix Draw is invalid") from exc
    if raw_date != draw_date.isoformat() or tuple(raw_numbers) != draw.numbers:
        raise VerifiedHistoryIntegrityError("suffix Draw is not canonical")
    return draw


def _draw_payload(draw: Draw) -> dict[str, Any]:
    return {
        "draw_date": draw.draw_date.isoformat(),
        "numbers": list(draw.numbers),
        "bonus": draw.bonus,
    }


def _row_sha256(draw: Draw) -> str:
    return sha256(_canonical_json(_draw_payload(draw))).hexdigest()


def _next_draw_date(draw_date: date) -> date:
    if draw_date.weekday() == 2:
        return draw_date + timedelta(days=3)
    if draw_date.weekday() == 5:
        return draw_date + timedelta(days=4)
    raise VerifiedHistoryIntegrityError("history high-water is off schedule")


def _validate_evidence_commit(
    repository: Path, artifact_commit: str, evidence_commit: object
) -> str:
    if (
        not isinstance(evidence_commit, str)
        or _GIT_OID_RE.fullmatch(evidence_commit) is None
    ):
        raise VerifiedHistoryIntegrityError("suffix evidence commit is invalid")
    try:
        resolved = (
            _git_bytes(repository, "rev-parse", f"{evidence_commit}^{{commit}}")
            .decode("ascii")
            .strip()
        )
    except UnicodeError as exc:
        raise VerifiedHistoryIntegrityError(
            "suffix evidence commit is invalid"
        ) from exc
    if resolved != evidence_commit or evidence_commit == artifact_commit:
        raise VerifiedHistoryIntegrityError("suffix evidence commit is invalid")
    completed = subprocess.run(
        [
            "git",
            "-C",
            str(repository),
            "merge-base",
            "--is-ancestor",
            artifact_commit,
            evidence_commit,
        ],
        check=False,
        capture_output=True,
        env=_git_environment(),
    )
    if completed.returncode != 0:
        raise VerifiedHistoryIntegrityError(
            "suffix evidence commit is outside sealed lineage"
        )
    return evidence_commit


def _evidence_commit_changed_paths(
    repository: Path, evidence_commit: str
) -> frozenset[str]:
    try:
        lineage = (
            _git_bytes(
                repository,
                "rev-list",
                "--parents",
                "-n",
                "1",
                evidence_commit,
            )
            .decode("ascii")
            .strip()
            .split()
        )
        raw_changes = _git_bytes(
            repository,
            "diff-tree",
            "--no-commit-id",
            "--name-status",
            "--no-renames",
            "-r",
            evidence_commit,
        ).decode("utf-8")
    except UnicodeError as exc:
        raise VerifiedHistoryIntegrityError(
            "suffix evidence commit is invalid"
        ) from exc
    if len(lineage) != 2 or lineage[0] != evidence_commit:
        raise VerifiedHistoryIntegrityError(
            "suffix evidence commit must have one parent"
        )
    changes: dict[str, str] = {}
    for line in raw_changes.splitlines():
        try:
            status, path = line.split("\t", 1)
        except ValueError as exc:
            raise VerifiedHistoryIntegrityError(
                "suffix evidence commit change set is invalid"
            ) from exc
        if (
            status not in {"A", "M"}
            or path in changes
            or (
                path != ".gitattributes"
                and not path.startswith("evidence/live_sources/")
            )
        ):
            raise VerifiedHistoryIntegrityError(
                "suffix evidence commit change set is invalid"
            )
        changes[path] = status
    if not changes:
        raise VerifiedHistoryIntegrityError(
            "suffix evidence commit change set is invalid"
        )
    return frozenset(changes)


def _strict_wclc_target_draw(raw: bytes, expected_date: date) -> Draw:
    try:
        html = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise VerifiedHistoryIntegrityError("WCLC evidence is not UTF-8") from exc
    text = re.sub(
        r"\s+", " ", BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    )
    target = (
        f"{expected_date.strftime('%A')}, {expected_date.strftime('%B')} "
        f"{expected_date.day}, {expected_date.year}"
    )
    target_start = re.compile(
        rf"(?<![A-Za-z0-9]){re.escape(target)}(?![A-Za-z0-9])",
        re.IGNORECASE,
    )
    target_matches = list(target_start.finditer(text))
    if len(target_matches) != 1:
        raise VerifiedHistoryIntegrityError(
            "WCLC evidence must contain exactly one target draw occurrence"
        )
    match = target_matches[0]
    next_date = _NEXT_WCLC_DATE_RE.search(text, match.end())
    end = next_date.start() if next_date is not None else len(text)
    segment = text[match.end() : end]
    classic_matches = list(
        re.finditer(r"\bCLASSIC\s+DRAW\b", segment, flags=re.IGNORECASE)
    )
    if len(classic_matches) != 1:
        raise VerifiedHistoryIntegrityError(
            "WCLC evidence must contain exactly one target draw occurrence"
        )
    result_pattern = (
        r"(?<![0-9])"
        r"([0-9]{1,2})\s+([0-9]{1,2})\s+([0-9]{1,2})\s+"
        r"([0-9]{1,2})\s+([0-9]{1,2})\s+([0-9]{1,2})\s+"
        r"Bonus\s+([0-9]{1,2})(?=\s|$)"
    )
    remainder = segment[classic_matches[0].end() :]
    ball_match = re.match(rf"\s*{result_pattern}", remainder, re.IGNORECASE)
    if ball_match is None:
        raise VerifiedHistoryIntegrityError("WCLC target draw is malformed")
    result_matches = list(re.finditer(result_pattern, remainder, re.IGNORECASE))
    if len(result_matches) != 1:
        raise VerifiedHistoryIntegrityError(
            "WCLC evidence must contain exactly one target draw result"
        )
    balls = [int(value) for value in ball_match.groups()]
    try:
        draw = Draw(expected_date, tuple(balls[:6]), balls[6])
    except ValueError as exc:
        raise VerifiedHistoryIntegrityError("WCLC target draw is invalid") from exc
    if tuple(balls[:6]) != draw.numbers:
        raise VerifiedHistoryIntegrityError("WCLC target draw is not canonical")
    return draw


def _validate_receipt_url(receipt: dict[str, Any], draw: Draw) -> dict[str, str]:
    group = receipt.get("independence_group")
    authority = _RECEIPT_AUTHORITIES.get(group)
    if authority is None:
        raise VerifiedHistoryIntegrityError("suffix receipt authority is not allowed")
    if (
        receipt.get("provider") != authority["provider"]
        or receipt.get("source_type") != authority["source_type"]
        or not isinstance(receipt.get("url"), str)
    ):
        raise VerifiedHistoryIntegrityError("suffix receipt authority mismatch")
    parsed = urlsplit(receipt["url"])
    if (
        parsed.scheme != "https"
        or parsed.hostname != authority["hostname"]
        or parsed.path != authority["url_path"]
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port not in {None, 443}
        or parsed.fragment
    ):
        raise VerifiedHistoryIntegrityError("suffix receipt URL mismatch")
    if group == "loto_quebec":
        query = parse_qs(parsed.query, keep_blank_values=True)
        if query.get("date") != [draw.draw_date.isoformat()]:
            raise VerifiedHistoryIntegrityError(
                "Loto-Québec receipt date query mismatch"
            )
    return authority


def _validate_source_receipts(
    repository: Path,
    evidence_commit: str,
    draw: Draw,
    value: object,
) -> None:
    if not isinstance(value, list) or len(value) < 2:
        raise VerifiedHistoryIntegrityError(
            "suffix draw requires two independent source receipts"
        )
    row_sha256 = _row_sha256(draw)
    evidence_commit_created_at = _git_commit_created_at(repository, evidence_commit)
    evidence_commit_paths = _evidence_commit_changed_paths(repository, evidence_commit)
    sort_keys = []
    groups = set()
    evidence_paths = set()
    evidence_sha256s = set()
    for receipt in value:
        if not _has_keys(receipt, _RECEIPT_KEYS):
            raise VerifiedHistoryIntegrityError("suffix receipt schema mismatch")
        authority = _validate_receipt_url(receipt, draw)
        group = receipt["independence_group"]
        groups.add(group)
        retrieved_at = receipt["retrieved_at"]
        if (
            not isinstance(retrieved_at, str)
            or _UTC_TIMESTAMP_RE.fullmatch(retrieved_at) is None
        ):
            raise VerifiedHistoryIntegrityError("suffix receipt timestamp is invalid")
        try:
            parsed_timestamp = datetime.fromisoformat(
                retrieved_at.removesuffix("Z") + "+00:00"
            )
        except ValueError as exc:
            raise VerifiedHistoryIntegrityError(
                "suffix receipt timestamp is invalid"
            ) from exc
        if (
            parsed_timestamp.tzinfo != UTC
            or parsed_timestamp.date() <= draw.draw_date
            or parsed_timestamp > evidence_commit_created_at
        ):
            raise VerifiedHistoryIntegrityError("suffix receipt timestamp is invalid")
        evidence_path = receipt["evidence_path"]
        if not isinstance(evidence_path, str):
            raise VerifiedHistoryIntegrityError("suffix evidence path is invalid")
        pure_path = PurePosixPath(evidence_path)
        if (
            evidence_path != pure_path.as_posix()
            or pure_path.is_absolute()
            or ".." in pure_path.parts
            or not evidence_path.startswith(authority["evidence_prefix"])
            or evidence_path in evidence_paths
            or evidence_path not in evidence_commit_paths
        ):
            raise VerifiedHistoryIntegrityError(
                "suffix evidence path is invalid for evidence commit"
            )
        evidence_paths.add(evidence_path)
        if (
            not _is_integer(receipt["bytes"])
            or receipt["bytes"] <= 0
            or not _is_sha256(receipt["sha256"])
            or receipt["supported_row_sha256"] != row_sha256
        ):
            raise VerifiedHistoryIntegrityError("suffix receipt identity mismatch")
        evidence_sha256s.add(receipt["sha256"])
        _, raw = _git_artifact_bytes(repository, evidence_commit, evidence_path)
        if len(raw) != receipt["bytes"] or sha256(raw).hexdigest() != receipt["sha256"]:
            raise VerifiedHistoryIntegrityError("suffix evidence asset mismatch")
        if group == "wclc":
            parsed_draw = _strict_wclc_target_draw(raw, draw.draw_date)
        else:
            try:
                parsed_draw = parse_lotoquebec_detail_html(
                    raw.decode("utf-8"), draw.draw_date
                )
            except (UnicodeDecodeError, RuntimeError) as exc:
                raise VerifiedHistoryIntegrityError(
                    "Loto-Québec evidence is invalid"
                ) from exc
        if parsed_draw != draw or _row_sha256(parsed_draw) != row_sha256:
            raise VerifiedHistoryIntegrityError(
                "suffix evidence does not support the canonical row"
            )
        sort_keys.append(
            (
                group,
                receipt["provider"],
                receipt["source_type"],
                receipt["url"],
                receipt["sha256"],
            )
        )
    if groups != set(_RECEIPT_AUTHORITIES):
        raise VerifiedHistoryIntegrityError(
            "suffix receipt independence groups mismatch"
        )
    if len(evidence_sha256s) != len(value):
        raise VerifiedHistoryIntegrityError(
            "suffix receipts do not contain independent raw source bytes"
        )
    if sort_keys != sorted(sort_keys) or len(set(sort_keys)) != len(sort_keys):
        raise VerifiedHistoryIntegrityError("suffix receipts are not canonical")


def _parse_suffix(
    repository: Path,
    raw: bytes,
    *,
    seal: dict[str, Any],
    expected_seal_sha256: str,
    expected_suffix_sha256: str | None,
    expected_suffix_head_sha256: str | None,
    high_water: date,
) -> tuple[tuple[Draw, ...], tuple[str, ...], str]:
    if not _is_sha256(expected_suffix_sha256) or not _is_sha256(
        expected_suffix_head_sha256
    ):
        raise VerifiedHistoryIntegrityError(
            "nonempty suffix requires external file and head SHA-256 pins"
        )
    if sha256(raw).hexdigest() != expected_suffix_sha256:
        raise VerifiedHistoryIntegrityError("external suffix SHA-256 mismatch")
    if not raw.endswith(b"\n"):
        raise VerifiedHistoryIntegrityError("suffix contains truncated JSON")
    raw_lines = raw.splitlines(keepends=True)
    events = []
    for line_number, raw_line in enumerate(raw_lines, start=1):
        try:
            event = json.loads(raw_line)
        except (UnicodeError, json.JSONDecodeError, TypeError) as exc:
            raise VerifiedHistoryIntegrityError(
                f"suffix line {line_number} is invalid JSON"
            ) from exc
        if (
            not isinstance(event, dict)
            or _canonical_json(event, newline=True) != raw_line
        ):
            raise VerifiedHistoryIntegrityError("suffix event is not canonical JSON")
        events.append(event)

    previous_hash = expected_seal_sha256
    previous_date = high_water
    draws = []
    evidence_commits = []
    for sequence, event in enumerate(events):
        if (
            set(event) != _SUFFIX_EVENT_KEYS
            or event.get("schema_version") != _SUFFIX_SCHEMA
            or event.get("incident_id") != _INCIDENT_ID
            or type(event.get("sequence")) is not int
            or event["sequence"] != sequence
            or event.get("base_seal_sha256") != expected_seal_sha256
            or event.get("previous_event_sha256") != previous_hash
            or not _is_sha256(event.get("event_sha256"))
        ):
            raise VerifiedHistoryIntegrityError("suffix event chain/schema mismatch")
        event_body = dict(event)
        recorded_event_hash = event_body.pop("event_sha256")
        if sha256(_canonical_json(event_body)).hexdigest() != recorded_event_hash:
            raise VerifiedHistoryIntegrityError("suffix event SHA-256 mismatch")
        draw = _draw_from_payload(event["draw"])
        if draw.draw_date != _next_draw_date(previous_date):
            raise VerifiedHistoryIntegrityError(
                "suffix draw does not match the next scheduled date"
            )
        evidence_commit = _validate_evidence_commit(
            repository, seal["artifact_commit"], event["evidence_commit"]
        )
        _validate_source_receipts(
            repository, evidence_commit, draw, event["source_receipts"]
        )
        draws.append(draw)
        evidence_commits.append(evidence_commit)
        previous_date = draw.draw_date
        previous_hash = recorded_event_hash
    if previous_hash != expected_suffix_head_sha256:
        raise VerifiedHistoryIntegrityError("external suffix head SHA-256 mismatch")
    return tuple(draws), tuple(evidence_commits), previous_hash


def _parse_csv(raw: bytes) -> tuple[Draw, ...]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise VerifiedHistoryIntegrityError("corrected epoch is not UTF-8") from exc
    reader = csv.reader(io.StringIO(text, newline=""))
    expected_header = [
        "draw_date",
        "n1",
        "n2",
        "n3",
        "n4",
        "n5",
        "n6",
        "bonus",
    ]
    try:
        header = next(reader)
    except StopIteration as exc:
        raise VerifiedHistoryIntegrityError("corrected epoch is empty") from exc
    if header != expected_header:
        raise VerifiedHistoryIntegrityError("corrected epoch CSV header is invalid")
    draws = []
    for line_number, row in enumerate(reader, start=2):
        if len(row) != 8:
            raise VerifiedHistoryIntegrityError(
                f"corrected epoch row {line_number} is malformed"
            )
        try:
            draws.append(
                Draw(
                    date.fromisoformat(row[0]),
                    tuple(int(value) for value in row[1:7]),  # type: ignore[arg-type]
                    int(row[7]),
                )
            )
        except (TypeError, ValueError) as exc:
            raise VerifiedHistoryIntegrityError(
                f"corrected epoch row {line_number} violates Draw"
            ) from exc
    return tuple(draws)


def _local_path(repository: Path, value: str | Path) -> tuple[Path, str]:
    candidate = Path(value)
    path = candidate if candidate.is_absolute() else repository / candidate
    try:
        relative = path.resolve(strict=True).relative_to(repository)
    except (OSError, ValueError) as exc:
        raise VerifiedHistoryIntegrityError(
            "history path is outside repository"
        ) from exc
    return path, relative.as_posix()


def _load_verified_history_from_immutable_bytes(
    repository: Path,
    *,
    seal_raw: bytes,
    seal_relative: str,
    expected_seal_sha256: str,
    suffix_raw: bytes = b"",
    suffix_relative: str | None = None,
    expected_suffix_sha256: str | None = None,
    expected_suffix_head_sha256: str | None = None,
) -> VerifiedHistory:
    """Validate corrected history from immutable, already-resolved Git bytes."""
    try:
        repository = repository.resolve(strict=True)
    except OSError as exc:
        raise VerifiedHistoryIntegrityError("repository does not exist") from exc
    if sha256(seal_raw).hexdigest() != expected_seal_sha256:
        raise VerifiedHistoryIntegrityError("external seal SHA-256 mismatch")
    try:
        seal: dict[str, Any] = json.loads(seal_raw)
    except (UnicodeError, json.JSONDecodeError, TypeError) as exc:
        raise VerifiedHistoryIntegrityError("seal is not valid JSON") from exc
    if not isinstance(seal, dict) or _canonical_json(seal, newline=True) != seal_raw:
        raise VerifiedHistoryIntegrityError("seal is not canonical JSON")
    recorded_body_sha256 = seal.get("seal_body_sha256")
    seal_body = dict(seal)
    seal_body.pop("seal_body_sha256", None)
    if (
        not isinstance(recorded_body_sha256, str)
        or sha256(_canonical_json(seal_body)).hexdigest() != recorded_body_sha256
    ):
        raise VerifiedHistoryIntegrityError("seal body SHA-256 mismatch")
    if set(seal) != _SEAL_KEYS or seal.get("schema_version") != _SEAL_SCHEMA:
        raise VerifiedHistoryIntegrityError("frozen seal schema mismatch")
    if seal.get("status") != _SEALED_STATUS:
        raise VerifiedHistoryIntegrityError("sealed status mismatch")
    if seal.get("incident_id") != _INCIDENT_ID:
        raise VerifiedHistoryIntegrityError("sealed incident mismatch")
    expected_seal_path = f"evidence/data_integrity/{_INCIDENT_ID}/seal.json"
    if seal_relative != expected_seal_path:
        raise VerifiedHistoryIntegrityError("sealed incident path mismatch")
    _validate_frozen_nested_schema(seal)
    _validate_inventory_schema(seal)
    _validate_artifact_commit(repository, seal)
    _validate_git_inventories(repository, seal)
    _validate_corrected_epoch_identity(seal)
    _validate_seal_semantics(repository, seal)

    corrected = seal["corrected_epoch"]
    base_raw = _git_bytes(
        repository,
        "show",
        f"{seal['artifact_commit']}:{corrected['path']}",
    )
    draws = _parse_csv(base_raw)
    if _canonical_csv(draws) != base_raw:
        raise VerifiedHistoryIntegrityError("corrected epoch is not canonical CSV")
    expected_dates = tuple(
        expected_lotto649_draw_dates(date.fromisoformat(_BASE_HISTORY_THROUGH))
    )
    if (
        len(draws) != _BASE_DRAW_COUNT
        or tuple(draw.draw_date for draw in draws) != expected_dates
    ):
        raise VerifiedHistoryIntegrityError(
            "corrected epoch does not match the exact schedule"
        )
    if canonical_official_rows_sha256(draws) != _BASE_ROWS_SHA256:
        raise VerifiedHistoryIntegrityError("corrected epoch row SHA-256 mismatch")
    if sha256(base_raw).hexdigest() != _BASE_FILE_SHA256:
        raise VerifiedHistoryIntegrityError("corrected epoch identity mismatch")

    suffix_draws: tuple[Draw, ...] = ()
    evidence_commits: tuple[str, ...] = ()
    suffix_head: str | None = None
    if suffix_relative is not None and suffix_relative != _SUFFIX_PATH:
        raise VerifiedHistoryIntegrityError("suffix path mismatch")
    if suffix_raw:
        suffix_draws, evidence_commits, suffix_head = _parse_suffix(
            repository,
            suffix_raw,
            seal=seal,
            expected_seal_sha256=expected_seal_sha256,
            expected_suffix_sha256=expected_suffix_sha256,
            expected_suffix_head_sha256=expected_suffix_head_sha256,
            high_water=draws[-1].draw_date,
        )
    elif expected_suffix_sha256 is not None or expected_suffix_head_sha256 is not None:
        raise VerifiedHistoryIntegrityError("empty suffix cannot have suffix pins")

    all_draws = (*draws, *suffix_draws)

    base = BaseProvenance(
        path=corrected["path"],
        git_blob=corrected["git_blob"],
        bytes=corrected["bytes"],
        file_sha256=corrected["file_sha256"],
        rows_sha256=corrected["rows_sha256"],
        draw_count=corrected["draw_count"],
        history_start=date.fromisoformat(corrected["history_start"]),
        history_through=date.fromisoformat(corrected["history_through"]),
    )
    return VerifiedHistory(
        draws=all_draws,
        epoch=seal["incident_id"],
        seal=SealProvenance(
            path=seal_relative,
            file_sha256=expected_seal_sha256,
            body_sha256=seal["seal_body_sha256"],
            artifact_commit=seal["artifact_commit"],
            artifact_parent=seal["artifact_parent"],
            status=seal["status"],
        ),
        base=base,
        suffix=SuffixProvenance(
            path=suffix_relative,
            bytes=len(suffix_raw),
            file_sha256=(
                sha256(suffix_raw).hexdigest() if suffix_relative is not None else None
            ),
            event_count=len(suffix_draws),
            base_seal_sha256=expected_seal_sha256,
            head_event_sha256=suffix_head,
            history_through=all_draws[-1].draw_date,
            evidence_commits=evidence_commits,
        ),
    )


def load_verified_history(
    repository: Path,
    *,
    seal_path: str | Path,
    expected_seal_sha256: str,
    suffix_path: str | Path | None = None,
    expected_suffix_sha256: str | None = None,
    expected_suffix_head_sha256: str | None = None,
) -> VerifiedHistory:
    """Load corrected draws authenticated by local seal and suffix paths.

    This compatibility seam validates the supplied local files. Operational
    callers use the registry-backed authority, which resolves immutable Git
    blobs before calling the private validator above.
    """
    try:
        repository = repository.resolve(strict=True)
    except OSError as exc:
        raise VerifiedHistoryIntegrityError("repository does not exist") from exc
    seal_file, seal_relative = _local_path(repository, seal_path)
    seal_raw = seal_file.read_bytes()
    suffix_relative = None
    suffix_raw = b""
    if suffix_path is not None:
        suffix_file, suffix_relative = _local_path(repository, suffix_path)
        suffix_raw = suffix_file.read_bytes()
    return _load_verified_history_from_immutable_bytes(
        repository,
        seal_raw=seal_raw,
        seal_relative=seal_relative,
        expected_seal_sha256=expected_seal_sha256,
        suffix_raw=suffix_raw,
        suffix_relative=suffix_relative,
        expected_suffix_sha256=expected_suffix_sha256,
        expected_suffix_head_sha256=expected_suffix_head_sha256,
    )
