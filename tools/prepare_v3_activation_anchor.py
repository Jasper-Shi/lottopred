#!/usr/bin/env python3
"""Prepare, but never activate, the frozen V3 prospective cohort anchor."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping, Sequence
import csv
from datetime import date, datetime
from hashlib import sha256
import io
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile
import warnings
from zoneinfo import ZoneInfo

import yaml

from lotto649.data import validate_continuity
from lotto649.domain import Draw
from lotto649.research_protocol import (
    GitEvidenceError,
    OutcomeBoundary,
    VerifiedOutcomeBoundary,
    load_experiment_registry,
    verify_frozen_paths,
)


REGISTRY_PATH = "docs/experiments/registry.yaml"
DEFAULT_EXPERIMENT_ID = "V3_frozen_shadow_cohort"
OUTCOME_PATH = "data/processed/draws.csv"
TORONTO = ZoneInfo("America/Toronto")
REQUIRED_ANCHOR_FIELDS = {
    "schema_version",
    "experiment_id",
    "model_name",
    "model_version",
    "freeze_commit",
    "decision",
    "role",
    "outcome_path",
    "outcome_sha256",
    "outcome_draw_count",
    "outcome_history_through",
    "cohort_start",
}


class ActivationAnchorError(RuntimeError):
    """Raised when an activation anchor cannot be prepared safely."""


def _run_git(
    repository: Path,
    *arguments: str,
    check: bool = True,
) -> subprocess.CompletedProcess[bytes]:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repository), *arguments],
            check=False,
            capture_output=True,
        )
    except OSError as exc:
        raise ActivationAnchorError("unable to run Git") from exc
    if check and completed.returncode != 0:
        detail = completed.stderr.decode(errors="replace").strip()
        suffix = f": {detail}" if detail else ""
        raise ActivationAnchorError(f"Git command failed{suffix}")
    return completed


def _git_text(repository: Path, *arguments: str) -> str:
    raw = _run_git(repository, *arguments).stdout
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ActivationAnchorError("Git output is not valid UTF-8") from exc


def _resolve_repository(value: str) -> Path:
    repository = Path(value).resolve(strict=True)
    top_level = Path(
        _git_text(repository, "rev-parse", "--show-toplevel").strip()
    ).resolve(strict=True)
    if repository != top_level:
        raise ActivationAnchorError("repository must be the Git worktree top level")
    shallow = _git_text(
        repository, "rev-parse", "--is-shallow-repository"
    ).strip()
    if shallow != "false":
        raise ActivationAnchorError("repository must be complete and non-shallow")
    dirty = _git_text(
        repository,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
    ).strip()
    if dirty:
        raise ActivationAnchorError("repository must be clean before anchor preparation")
    return repository


def _full_commit(repository: Path, value: str, label: str) -> str:
    if len(value) != 40 or any(character not in "0123456789abcdef" for character in value):
        raise ActivationAnchorError(f"{label} must be a full lowercase Git SHA")
    resolved = _git_text(repository, "rev-parse", f"{value}^{{commit}}").strip()
    if resolved != value:
        raise ActivationAnchorError(f"{label} does not resolve exactly")
    return resolved


def _is_ancestor(repository: Path, ancestor: str, descendant: str) -> bool:
    completed = _run_git(
        repository,
        "merge-base",
        "--is-ancestor",
        ancestor,
        descendant,
        check=False,
    )
    if completed.returncode == 0:
        return True
    if completed.returncode == 1:
        return False
    raise ActivationAnchorError("Git ancestry check failed")


def _load_committed_registration(repository: Path, experiment_id: str):
    registry_path = repository / REGISTRY_PATH
    committed = _run_git(repository, "show", f"HEAD:{REGISTRY_PATH}").stdout
    try:
        worktree = registry_path.read_bytes()
    except OSError as exc:
        raise ActivationAnchorError("committed experiment registry is unavailable") from exc
    if worktree != committed:
        raise ActivationAnchorError("worktree registry differs from committed HEAD")
    registry = load_experiment_registry(registry_path)
    try:
        registration = registry.get(experiment_id)
    except KeyError as exc:
        raise ActivationAnchorError(f"unknown experiment: {experiment_id}") from exc
    if (
        registration.status != "registered"
        or registration.result is not None
        or registration.prospective.status != "not_activated"
    ):
        raise ActivationAnchorError(
            "experiment must be registered with a not_activated cohort and no result"
        )
    return registration


def _registration_row(raw: bytes, experiment_id: str) -> Mapping[str, object]:
    try:
        payload = yaml.safe_load(raw.decode("utf-8"))
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        raise ActivationAnchorError("committed registration YAML is invalid") from exc
    if not isinstance(payload, Mapping):
        raise ActivationAnchorError("committed registration root is invalid")
    experiments = payload.get("experiments")
    if not isinstance(experiments, list):
        raise ActivationAnchorError("committed registration rows are invalid")
    matches = [
        row
        for row in experiments
        if isinstance(row, Mapping) and row.get("id") == experiment_id
    ]
    if len(matches) != 1:
        raise ActivationAnchorError("committed registration row is not unique")
    return matches[0]


def _verify_registration_freeze(
    repository: Path,
    experiment_id: str,
    freeze_commit: str,
) -> None:
    changed_paths = {
        path
        for path in _git_text(
            repository,
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            freeze_commit,
            "--",
            REGISTRY_PATH,
        ).splitlines()
        if path
    }
    if REGISTRY_PATH not in changed_paths:
        raise ActivationAnchorError(
            f"freeze commit must itself commit {REGISTRY_PATH}"
        )
    try:
        frozen_raw = _run_git(
            repository,
            "show",
            f"{freeze_commit}:{REGISTRY_PATH}",
        ).stdout
        head_raw = _run_git(repository, "show", f"HEAD:{REGISTRY_PATH}").stdout
    except ActivationAnchorError as exc:
        raise ActivationAnchorError(
            "registration must already exist at the freeze commit"
        ) from exc
    frozen_row = _registration_row(frozen_raw, experiment_id)
    head_row = _registration_row(head_raw, experiment_id)
    if frozen_row != head_row:
        raise ActivationAnchorError("registration row differs from the freeze commit")


def _frozen_paths(registration) -> tuple[str, ...]:
    raw_paths = registration.parameters.get("frozen_implementation_paths")
    if (
        not isinstance(raw_paths, Sequence)
        or isinstance(raw_paths, (str, bytes))
        or not raw_paths
        or any(not isinstance(path, str) or not path for path in raw_paths)
    ):
        raise ActivationAnchorError("registered frozen implementation paths are invalid")
    paths = tuple(raw_paths)
    if len(paths) != len(set(paths)):
        raise ActivationAnchorError("registered frozen implementation paths are not unique")
    return paths


def _verify_freeze(
    repository: Path,
    registration,
    freeze_commit: str,
    head_commit: str,
) -> None:
    if not _is_ancestor(repository, freeze_commit, head_commit):
        raise ActivationAnchorError("freeze commit is not an ancestor of HEAD")
    paths = _frozen_paths(registration)
    if freeze_commit == head_commit:
        for path in paths:
            entry = _git_text(repository, "ls-tree", freeze_commit, "--", path).strip()
            try:
                metadata, listed_path = entry.split("\t", 1)
                mode, object_type, _ = metadata.split(" ", 2)
            except ValueError as exc:
                raise ActivationAnchorError(
                    f"frozen path is missing or malformed at freeze: {path}"
                ) from exc
            if (
                listed_path != path
                or object_type != "blob"
                or mode not in {"100644", "100755"}
            ):
                raise ActivationAnchorError(
                    f"frozen path must be a regular file at freeze: {path}"
                )
        return
    verify_frozen_paths(
        repository,
        freeze_commit=freeze_commit,
        evidence_commit=head_commit,
        paths=paths,
    )


def _parse_committed_draws(raw: bytes) -> tuple[Draw, ...]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ActivationAnchorError("committed outcome data is not UTF-8") from exc
    rows = csv.reader(io.StringIO(text, newline=""))
    try:
        header = next(rows)
    except StopIteration as exc:
        raise ActivationAnchorError("committed outcome data is empty") from exc
    if header != ["draw_date", "n1", "n2", "n3", "n4", "n5", "n6", "bonus"]:
        raise ActivationAnchorError("committed outcome data has an unexpected header")
    draws: list[Draw] = []
    try:
        for row in rows:
            if not row:
                continue
            if len(row) != 8:
                raise ActivationAnchorError("committed outcome data has a malformed row")
            draws.append(
                Draw(
                    date.fromisoformat(row[0]),
                    tuple(int(value) for value in row[1:7]),  # type: ignore[arg-type]
                    int(row[7]),
                )
            )
    except ValueError as exc:
        raise ActivationAnchorError("committed outcome data has an invalid draw") from exc
    if not draws:
        raise ActivationAnchorError("committed outcome data has no draws")
    dates = [draw.draw_date for draw in draws]
    if dates != sorted(dates) or len(dates) != len(set(dates)):
        raise ActivationAnchorError("committed outcome data is not strictly chronological")
    try:
        validate_continuity(draws)
    except RuntimeError as exc:
        raise ActivationAnchorError(str(exc)) from exc
    return tuple(draws)


def _verified_outcome_boundary(repository: Path, head_commit: str, registration):
    if registration.dataset_path != OUTCOME_PATH:
        raise ActivationAnchorError("registered outcome path is not supported")

    remote = _run_git(
        repository,
        "rev-parse",
        "--verify",
        "refs/remotes/origin/main^{commit}",
        check=False,
    )
    if remote.returncode != 0:
        raise ActivationAnchorError(
            "required refs/remotes/origin/main tracking ref is missing"
        )
    try:
        origin_main_commit = remote.stdout.decode("utf-8").strip()
    except UnicodeDecodeError as exc:
        raise ActivationAnchorError("origin/main commit is not valid UTF-8") from exc
    origin_main_commit = _full_commit(
        repository,
        origin_main_commit,
        "origin/main commit",
    )
    if origin_main_commit != head_commit:
        raise ActivationAnchorError(
            "HEAD must exactly equal refs/remotes/origin/main before anchor preparation"
        )

    raw = _run_git(repository, "show", f"{head_commit}:{OUTCOME_PATH}").stdout
    draws = _parse_committed_draws(raw)
    boundary = OutcomeBoundary(
        source_commit=head_commit,
        sha256=sha256(raw).hexdigest(),
        draw_count=len(draws),
        history_through=draws[-1].draw_date,
    )
    registration_boundary = OutcomeBoundary(
        source_commit=registration.outcomes_known_source_commit,
        sha256=registration.outcomes_known_sha256,
        draw_count=registration.outcomes_known_draw_count,
        history_through=registration.outcomes_known_through,
    )
    try:
        origin_raw = _run_git(
            repository,
            "show",
            f"{origin_main_commit}:{OUTCOME_PATH}",
        ).stdout
        origin_draws = _parse_committed_draws(origin_raw)
        origin_boundary = OutcomeBoundary(
            source_commit=origin_main_commit,
            sha256=sha256(origin_raw).hexdigest(),
            draw_count=len(origin_draws),
            history_through=origin_draws[-1].draw_date,
        )
        VerifiedOutcomeBoundary.from_repository(
            repository,
            origin_boundary,
            registration_boundary=registration_boundary,
        )
    except (ActivationAnchorError, GitEvidenceError) as exc:
        raise ActivationAnchorError(
            "origin/main committed draws do not preserve the registered prefix"
        ) from exc
    try:
        VerifiedOutcomeBoundary.from_repository(
            repository,
            boundary,
            registration_boundary=origin_boundary,
        )
    except GitEvidenceError as exc:
        raise ActivationAnchorError(
            "HEAD data does not preserve the origin/main committed draws prefix"
        ) from exc
    return boundary


def _commit_toronto_date(repository: Path, commit: str) -> date:
    raw = _git_text(repository, "show", "-s", "--format=%cI", commit).strip()
    try:
        committed_at = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise ActivationAnchorError("HEAD commit timestamp is invalid") from exc
    if committed_at.tzinfo is None:
        raise ActivationAnchorError("HEAD commit timestamp must include a timezone")
    return committed_at.astimezone(TORONTO).date()


def _parse_cohort_start(
    value: str,
    registration,
    boundary: OutcomeBoundary,
    *,
    head_commit_date: date,
) -> date:
    try:
        cohort_start = date.fromisoformat(value)
    except ValueError as exc:
        raise ActivationAnchorError("cohort start must be an ISO date") from exc
    if cohort_start.weekday() not in {2, 5}:
        raise ActivationAnchorError("cohort start must be a Wednesday or Saturday")
    today = datetime.now(TORONTO).date()
    if cohort_start <= today:
        raise ActivationAnchorError("cohort start must be in the future in Toronto")
    if cohort_start <= head_commit_date:
        raise ActivationAnchorError(
            "cohort start must be after the HEAD commit date in Toronto"
        )
    latest_known = max(boundary.history_through, registration.outcomes_known_through)
    if cohort_start <= latest_known:
        raise ActivationAnchorError("cohort start must follow all known outcomes")
    excluded_target = registration.parameters.get(
        "newest_known_excluded_snapshot_target"
    )
    if excluded_target is not None:
        try:
            excluded_date = date.fromisoformat(str(excluded_target))
        except ValueError as exc:
            raise ActivationAnchorError(
                "registered excluded snapshot target is invalid"
            ) from exc
        if cohort_start <= excluded_date:
            raise ActivationAnchorError(
                "cohort start must follow the newest excluded snapshot target"
            )
    return cohort_start


def _safe_artifact_path(repository: Path, value: object) -> tuple[str, Path]:
    if not isinstance(value, str) or not value:
        raise ActivationAnchorError("activation artifact path is invalid")
    pure = PurePosixPath(value)
    if (
        pure.is_absolute()
        or not pure.parts
        or value != pure.as_posix()
        or "\x00" in value
        or any(part in {"", ".", "..", ".git"} for part in pure.parts)
    ):
        raise ActivationAnchorError("activation artifact path is unsafe")
    destination = repository.joinpath(*pure.parts)
    for ancestor in (repository.joinpath(*pure.parts[:index]) for index in range(1, len(pure.parts))):
        if ancestor.is_symlink():
            raise ActivationAnchorError("activation artifact parent cannot be a symlink")
    if os.path.lexists(destination):
        raise ActivationAnchorError(f"activation artifact already exists: {value}")
    ignored = _run_git(
        repository,
        "check-ignore",
        "--no-index",
        "--",
        value,
        check=False,
    )
    if ignored.returncode == 0:
        raise ActivationAnchorError(
            f"activation artifact path is ignored by Git: {value}"
        )
    if ignored.returncode != 1:
        raise ActivationAnchorError(
            f"unable to verify Git ignore status for activation artifact: {value}"
        )
    historical_commits = tuple(
        commit
        for commit in _git_text(
            repository,
            "log",
            "--all",
            "--format=%H",
            "--",
            value,
        ).splitlines()
        if commit
    )
    if historical_commits:
        raise ActivationAnchorError(
            f"activation artifact path already appeared in Git history: {value}"
        )
    committed = _run_git(
        repository,
        "cat-file",
        "-e",
        f"HEAD:{value}",
        check=False,
    )
    if committed.returncode == 0:
        raise ActivationAnchorError(f"activation artifact already exists in HEAD: {value}")
    if committed.returncode not in {0, 128}:
        raise ActivationAnchorError("unable to prove activation artifact absence")
    return value, destination


def _canonical_json_bytes(payload: Mapping[str, object]) -> bytes:
    return (
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _artifact_bytes(
    repository: Path,
    registration,
    freeze_commit: str,
    boundary: OutcomeBoundary,
    cohort_start: date,
) -> dict[str, bytes]:
    parameters = registration.parameters
    if (
        parameters.get("activation_anchor_commit_deadline")
        != "before_cohort_start_toronto_date"
    ):
        raise ActivationAnchorError("registered anchor commit deadline is invalid")
    if (
        parameters.get("release_commit_deadline")
        != "before_cohort_start_toronto_date"
    ):
        raise ActivationAnchorError("registered release commit deadline is invalid")
    if (
        parameters.get("activation_anchor_commit_changes")
        != "exact_three_activation_artifacts_only"
    ):
        raise ActivationAnchorError(
            "activation anchor protocol must publish exactly three artifacts"
        )
    if parameters.get("activation_anchor_enables_live") is not False:
        raise ActivationAnchorError("activation anchor must not enable live execution")
    if parameters.get("activation_anchor_schema_version") != 1:
        raise ActivationAnchorError("unsupported activation anchor schema")
    required_fields = parameters.get("activation_anchor_required_fields")
    if (
        not isinstance(required_fields, Sequence)
        or isinstance(required_fields, (str, bytes))
        or set(required_fields) != REQUIRED_ANCHOR_FIELDS
        or len(required_fields) != len(REQUIRED_ANCHOR_FIELDS)
    ):
        raise ActivationAnchorError("registered activation anchor fields are invalid")
    configured = (
        parameters.get("activation_anchor_json"),
        parameters.get("activation_anchor_markdown"),
        parameters.get("activation_anchor_claim"),
    )
    resolved = tuple(
        _safe_artifact_path(repository, value) for value in configured
    )
    paths = tuple(path for path, _ in resolved)
    if len(set(paths)) != 3:
        raise ActivationAnchorError("activation artifact paths must be unique")

    payload = {
        "schema_version": 1,
        "experiment_id": registration.experiment_id,
        "model_name": registration.model_name,
        "model_version": registration.model_version,
        "freeze_commit": freeze_commit,
        "decision": "continue_shadow",
        "role": registration.prospective.role,
        "outcome_path": OUTCOME_PATH,
        "outcome_sha256": boundary.sha256,
        "outcome_draw_count": boundary.draw_count,
        "outcome_history_through": boundary.history_through.isoformat(),
        "cohort_start": cohort_start.isoformat(),
    }
    markdown = (
        "# V3 prospective activation anchor\n\n"
        "This anchor records only frozen identity and committed outcome-boundary "
        "evidence. It contains no performance result and does not activate live "
        "prediction.\n\n"
        f"- Experiment: `{registration.experiment_id}`\n"
        f"- Model: `{registration.model_name} {registration.model_version}`\n"
        f"- Freeze commit: `{freeze_commit}`\n"
        f"- Outcome path: `{OUTCOME_PATH}`\n"
        f"- Outcome SHA-256: `{boundary.sha256}`\n"
        f"- Outcome draws: `{boundary.draw_count}`\n"
        f"- Outcomes through: `{boundary.history_through.isoformat()}`\n"
        f"- Planned cohort start: `{cohort_start.isoformat()}`\n"
        "- Decision: `continue_shadow`\n"
        "- Role: `shadow`\n"
    ).encode("utf-8")
    claim = _canonical_json_bytes(
        {
            "schema_version": 1,
            "claim": "prepare_activation_anchor_without_performance_review",
            "experiment_id": registration.experiment_id,
            "model_name": registration.model_name,
            "model_version": registration.model_version,
            "freeze_commit": freeze_commit,
            "cohort_start": cohort_start.isoformat(),
            "decision": "continue_shadow",
            "role": "shadow",
            "live_activation": False,
        }
    )
    return {
        paths[0]: _canonical_json_bytes(payload),
        paths[1]: markdown,
        paths[2]: claim,
    }


def _summary(
    artifacts: Mapping[str, bytes],
    *,
    freeze_commit: str,
    head_commit: str,
    cohort_start: date,
    write: bool,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "mode": "write" if write else "dry-run",
        "written": write,
        "experiment_id": DEFAULT_EXPERIMENT_ID,
        "freeze_commit": freeze_commit,
        "head_commit": head_commit,
        "cohort_start": cohort_start.isoformat(),
        "artifacts": [
            {
                "path": path,
                "sha256": sha256(raw).hexdigest(),
                "bytes": len(raw),
            }
            for path, raw in sorted(artifacts.items())
        ],
    }


class PublisherOperations:
    """Small OS adapter for no-follow, directory-fd-relative publication."""

    _DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW

    def open_root(self, repository: Path) -> int:
        return os.open(repository, self._DIRECTORY_FLAGS)

    def open_directory(self, name: str, *, parent_fd: int) -> int:
        return os.open(name, self._DIRECTORY_FLAGS, dir_fd=parent_fd)

    def make_directory(self, name: str, *, parent_fd: int) -> None:
        os.mkdir(name, mode=0o755, dir_fd=parent_fd)

    def create_stage_directory(self, repository: Path) -> str:
        stage = Path(
            tempfile.mkdtemp(prefix=".v3-activation-anchor-stage-", dir=repository)
        )
        if stage.parent != repository or "/" in stage.name:
            raise ActivationAnchorError("staging directory escaped the repository")
        return stage.name

    def create_file(self, name: str, *, directory_fd: int) -> int:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
        return os.open(name, flags, 0o600, dir_fd=directory_fd)

    def write_all(self, descriptor: int, raw: bytes) -> None:
        remaining = memoryview(raw)
        while remaining:
            written = os.write(descriptor, remaining)
            if written < 1:
                raise OSError("short write while staging activation artifact")
            remaining = remaining[written:]

    def fsync(self, descriptor: int, *, purpose: str) -> None:
        del purpose
        os.fsync(descriptor)

    def close(self, descriptor: int) -> None:
        os.close(descriptor)

    def stat(self, name: str, *, directory_fd: int) -> os.stat_result:
        return os.stat(name, dir_fd=directory_fd, follow_symlinks=False)

    def fstat(self, descriptor: int) -> os.stat_result:
        return os.fstat(descriptor)

    def link(
        self,
        source_name: str,
        destination_name: str,
        *,
        source_directory_fd: int,
        destination_directory_fd: int,
        artifact_path: str,
    ) -> None:
        del artifact_path
        os.link(
            source_name,
            destination_name,
            src_dir_fd=source_directory_fd,
            dst_dir_fd=destination_directory_fd,
            follow_symlinks=False,
        )

    def unlink(self, name: str, *, directory_fd: int, purpose: str) -> None:
        del purpose
        os.unlink(name, dir_fd=directory_fd)

    def remove_directory(self, name: str, *, parent_fd: int) -> None:
        os.rmdir(name, dir_fd=parent_fd)


def _new_publisher_operations() -> PublisherOperations:
    return PublisherOperations()


def _open_directory_chain(
    root_fd: int,
    parts: tuple[str, ...],
    operations: PublisherOperations,
    held_descriptors: list[int],
    *,
    create: bool,
) -> int:
    current = root_fd
    for part in parts:
        try:
            child = operations.open_directory(part, parent_fd=current)
        except FileNotFoundError:
            if not create:
                raise
            operations.make_directory(part, parent_fd=current)
            operations.fsync(current, purpose="parent_creation")
            child = operations.open_directory(part, parent_fd=current)
        held_descriptors.append(child)
        current = child
    return current


def _verify_registered_parent(
    root_fd: int,
    parts: tuple[str, ...],
    expected_fd: int,
    operations: PublisherOperations,
) -> None:
    reopened: list[int] = []
    try:
        try:
            actual_fd = _open_directory_chain(
                root_fd,
                parts,
                operations,
                reopened,
                create=False,
            )
        except OSError as exc:
            raise ActivationAnchorError(
                "registered parent changed during publication"
            ) from exc
        expected = operations.fstat(expected_fd)
        actual = operations.fstat(actual_fd)
        if (expected.st_dev, expected.st_ino) != (actual.st_dev, actual.st_ino):
            raise ActivationAnchorError(
                "registered parent changed during publication"
            )
    finally:
        for descriptor in reversed(reopened):
            operations.close(descriptor)


def _cleanup_stage(
    *,
    root_fd: int,
    stage_fd: int,
    stage_name: str,
    staged_names: Sequence[str],
    operations: PublisherOperations,
) -> list[str]:
    errors: list[str] = []
    for name in staged_names:
        try:
            operations.unlink(
                name,
                directory_fd=stage_fd,
                purpose="stage_cleanup",
            )
        except FileNotFoundError:
            continue
        except OSError as exc:
            errors.append(f"stage file {name}: {exc}")
    try:
        operations.fsync(stage_fd, purpose="stage_cleanup")
    except OSError as exc:
        errors.append(f"stage directory fsync: {exc}")
    try:
        operations.remove_directory(stage_name, parent_fd=root_fd)
    except FileNotFoundError:
        pass
    except OSError as exc:
        errors.append(f"stage directory removal: {exc}")
    try:
        operations.fsync(root_fd, purpose="root_cleanup")
    except OSError as exc:
        errors.append(f"repository directory fsync: {exc}")
    return errors


def _rollback_publication(
    published: Sequence[tuple[str, int, str, int, int]],
    parent_fds: Sequence[int],
    operations: PublisherOperations,
) -> list[str]:
    errors: list[str] = []
    for artifact_path, parent_fd, name, device, inode in reversed(published):
        try:
            current = operations.stat(name, directory_fd=parent_fd)
        except FileNotFoundError:
            continue
        except OSError as exc:
            errors.append(f"inspect {artifact_path}: {exc}")
            continue
        if (current.st_dev, current.st_ino) != (device, inode):
            errors.append(f"refused to unlink replaced artifact {artifact_path}")
            continue
        try:
            operations.unlink(
                name,
                directory_fd=parent_fd,
                purpose="rollback",
            )
        except OSError as exc:
            errors.append(f"unlink {artifact_path}: {exc}")
    for parent_fd in dict.fromkeys(parent_fds):
        try:
            operations.fsync(parent_fd, purpose="rollback_parent")
        except OSError as exc:
            errors.append(f"rollback parent fsync: {exc}")
    return errors


def _close_descriptors(
    descriptors: Sequence[int],
    operations: PublisherOperations,
) -> list[str]:
    errors: list[str] = []
    for descriptor in reversed(tuple(dict.fromkeys(descriptors))):
        try:
            operations.close(descriptor)
        except OSError as exc:
            errors.append(f"close fd {descriptor}: {exc}")
    return errors


def _validate_precommit_state(
    repository: Path,
    *,
    expected_head: str,
    expected_registry_sha256: str,
    expected_data_sha256: str,
    expected_paths: Sequence[str],
) -> None:
    def changed(detail: str) -> ActivationAnchorError:
        return ActivationAnchorError(f"precommit Git state changed: {detail}")

    current_head = _git_text(repository, "rev-parse", "HEAD^{commit}").strip()
    if current_head != expected_head:
        raise changed("HEAD moved")
    current_origin = _git_text(
        repository,
        "rev-parse",
        "--verify",
        "refs/remotes/origin/main^{commit}",
    ).strip()
    if current_origin != expected_head:
        raise changed("refs/remotes/origin/main moved")

    for path, expected_digest in (
        (REGISTRY_PATH, expected_registry_sha256),
        (OUTCOME_PATH, expected_data_sha256),
    ):
        committed = _run_git(repository, "show", f"{expected_head}:{path}").stdout
        if sha256(committed).hexdigest() != expected_digest:
            raise changed(f"committed {path} identity differs")
        try:
            worktree = (repository / path).read_bytes()
        except OSError as exc:
            raise changed(f"worktree {path} is unavailable") from exc
        if sha256(worktree).hexdigest() != expected_digest:
            raise changed(f"worktree {path} identity differs")

    expected = set(expected_paths)
    if len(expected) != len(expected_paths):
        raise changed("expected worktree path set contains duplicates")
    status = _run_git(
        repository,
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
    ).stdout
    unexpected: list[str] = []
    observed: set[str] = set()
    for record in status.split(b"\0"):
        if not record:
            continue
        try:
            decoded = record.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise changed("worktree status is not valid UTF-8") from exc
        if not decoded.startswith("?? "):
            unexpected.append(decoded)
            continue
        path = decoded[3:]
        if path not in expected or path in observed:
            unexpected.append(decoded)
            continue
        observed.add(path)
    if unexpected:
        raise changed("unexpected worktree entry: " + ", ".join(unexpected))
    missing = sorted(expected - observed)
    if missing:
        raise changed("expected worktree paths missing: " + ", ".join(missing))


def _publish_artifacts(
    repository: Path,
    artifacts: Mapping[str, bytes],
    *,
    precommit_validator: Callable[[Sequence[str]], None],
) -> None:
    operations = _new_publisher_operations()
    root_fd: int | None = None
    stage_fd: int | None = None
    stage_name: str | None = None
    staged: dict[str, str] = {}
    parent_fds: dict[tuple[str, ...], int] = {}
    held_descriptors: list[int] = []
    published: list[tuple[str, int, str, int, int]] = []
    durable = False

    try:
        root_fd = operations.open_root(repository)
        held_descriptors.append(root_fd)
        for relative_path in sorted(artifacts):
            pure = PurePosixPath(relative_path)
            parent_parts = tuple(pure.parts[:-1])
            if parent_parts not in parent_fds:
                parent_fds[parent_parts] = _open_directory_chain(
                    root_fd,
                    parent_parts,
                    operations,
                    held_descriptors,
                    create=True,
                )

        stage_name = operations.create_stage_directory(repository)
        stage_fd = operations.open_directory(stage_name, parent_fd=root_fd)
        held_descriptors.append(stage_fd)
        for index, (relative_path, raw) in enumerate(sorted(artifacts.items())):
            stage_file = f"artifact-{index}"
            descriptor = operations.create_file(
                stage_file,
                directory_fd=stage_fd,
            )
            try:
                operations.write_all(descriptor, raw)
                operations.fsync(descriptor, purpose="stage_file")
            finally:
                operations.close(descriptor)
            staged[relative_path] = stage_file
        operations.fsync(stage_fd, purpose="stage_directory")

        stage_paths = tuple(
            f"{stage_name}/{name}" for name in staged.values()
        )
        final_paths = tuple(artifacts)
        precommit_validator(stage_paths)

        for relative_path in sorted(artifacts):
            pure = PurePosixPath(relative_path)
            parent_fd = parent_fds[tuple(pure.parts[:-1])]
            try:
                operations.stat(pure.name, directory_fd=parent_fd)
            except FileNotFoundError:
                continue
            raise ActivationAnchorError(
                f"activation artifact appeared during staging: {relative_path}"
            )

        for relative_path in sorted(artifacts):
            pure = PurePosixPath(relative_path)
            parent_fd = parent_fds[tuple(pure.parts[:-1])]
            stage_file = staged[relative_path]
            staged_stat = operations.stat(stage_file, directory_fd=stage_fd)
            try:
                operations.link(
                    stage_file,
                    pure.name,
                    source_directory_fd=stage_fd,
                    destination_directory_fd=parent_fd,
                    artifact_path=relative_path,
                )
            except FileExistsError as exc:
                raise ActivationAnchorError(
                    f"activation artifact appeared during publication: {relative_path}"
                ) from exc
            published.append(
                (
                    relative_path,
                    parent_fd,
                    pure.name,
                    staged_stat.st_dev,
                    staged_stat.st_ino,
                )
            )

        for parent_parts, parent_fd in parent_fds.items():
            _verify_registered_parent(
                root_fd,
                parent_parts,
                parent_fd,
                operations,
            )
        published_paths = (*stage_paths, *final_paths)
        precommit_validator(published_paths)
        for parent_fd in dict.fromkeys(parent_fds.values()):
            operations.fsync(parent_fd, purpose="final_parent")
        for parent_parts, parent_fd in parent_fds.items():
            _verify_registered_parent(
                root_fd,
                parent_parts,
                parent_fd,
                operations,
            )
        precommit_validator(published_paths)
        durable = True
    except BaseException as primary:
        rollback_errors = _rollback_publication(
            published,
            tuple(parent_fds.values()),
            operations,
        )
        if rollback_errors:
            close_errors = _close_descriptors(held_descriptors, operations)
            details = "; ".join((*rollback_errors, *close_errors))
            raise ActivationAnchorError(
                "activation publication failed before durable commit point; "
                f"rollback failed; evidence retained in {stage_name or 'repository'}: "
                f"{details}"
            ) from primary
        cleanup_errors: list[str] = []
        if root_fd is not None and stage_fd is not None and stage_name is not None:
            cleanup_errors = _cleanup_stage(
                root_fd=root_fd,
                stage_fd=stage_fd,
                stage_name=stage_name,
                staged_names=tuple(staged.values()),
                operations=operations,
            )
        close_errors = _close_descriptors(held_descriptors, operations)
        retained = (*cleanup_errors, *close_errors)
        if retained:
            raise ActivationAnchorError(
                "activation publication failed before durable commit point; "
                "rollback completed but staging cleanup failed; evidence retained: "
                + "; ".join(retained)
            ) from primary
        if isinstance(primary, Exception):
            raise ActivationAnchorError(
                "activation publication failed before durable commit point; "
                f"rollback completed: {primary}"
            ) from primary
        raise

    if not durable or root_fd is None or stage_fd is None or stage_name is None:
        raise ActivationAnchorError("activation publication missed its commit point")
    cleanup_errors = _cleanup_stage(
        root_fd=root_fd,
        stage_fd=stage_fd,
        stage_name=stage_name,
        staged_names=tuple(staged.values()),
        operations=operations,
    )
    cleanup_errors.extend(_close_descriptors(held_descriptors, operations))
    if cleanup_errors:
        warnings.warn(
            "activation artifacts durably published; cleanup failed: "
            + "; ".join(cleanup_errors),
            RuntimeWarning,
            stacklevel=2,
        )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate and prepare the three frozen V3 activation-anchor artifacts; "
            "dry-run is the default."
        )
    )
    parser.add_argument("--repository", required=True)
    parser.add_argument(
        "--experiment-id",
        default=DEFAULT_EXPERIMENT_ID,
        choices=(DEFAULT_EXPERIMENT_ID,),
    )
    parser.add_argument("--freeze-commit", required=True)
    parser.add_argument("--cohort-start", required=True)
    parser.add_argument(
        "--write",
        action="store_true",
        help="exclusively create the three artifacts after all checks pass",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        repository = _resolve_repository(arguments.repository)
        head_commit = _full_commit(
            repository,
            _git_text(repository, "rev-parse", "HEAD").strip(),
            "HEAD",
        )
        expected_registry_sha256 = sha256(
            _run_git(repository, "show", f"{head_commit}:{REGISTRY_PATH}").stdout
        ).hexdigest()
        freeze_commit = _full_commit(
            repository,
            arguments.freeze_commit,
            "freeze commit",
        )
        registration = _load_committed_registration(
            repository,
            arguments.experiment_id,
        )
        _verify_registration_freeze(
            repository,
            arguments.experiment_id,
            freeze_commit,
        )
        _verify_freeze(
            repository,
            registration,
            freeze_commit,
            head_commit,
        )
        boundary = _verified_outcome_boundary(
            repository,
            head_commit,
            registration,
        )
        cohort_start = _parse_cohort_start(
            arguments.cohort_start,
            registration,
            boundary,
            head_commit_date=_commit_toronto_date(repository, head_commit),
        )
        artifacts = _artifact_bytes(
            repository,
            registration,
            freeze_commit,
            boundary,
            cohort_start,
        )
        if arguments.write:
            def validate_precommit(expected_paths: Sequence[str]) -> None:
                _validate_precommit_state(
                    repository,
                    expected_head=head_commit,
                    expected_registry_sha256=expected_registry_sha256,
                    expected_data_sha256=boundary.sha256,
                    expected_paths=expected_paths,
                )

            _publish_artifacts(
                repository,
                artifacts,
                precommit_validator=validate_precommit,
            )
        summary = _summary(
            artifacts,
            freeze_commit=freeze_commit,
            head_commit=head_commit,
            cohort_start=cohort_start,
            write=arguments.write,
        )
    except (ActivationAnchorError, GitEvidenceError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    sys.stdout.buffer.write(_canonical_json_bytes(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
