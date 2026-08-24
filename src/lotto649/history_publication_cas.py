"""Offline compare-and-swap publication for prepared history transactions.

This module deliberately proves only a local, complete bare Git object store.
It does not implement or claim GitHub/receive-pack compare-and-swap semantics.
"""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from .history_publication import PreparedPublication
from .operational_history import PublishedHistory, load_published_history

_MAIN_REF = "refs/heads/main"
_OID_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_FORBIDDEN_LOCAL_CONFIG_KEYS = frozenset(
    {"core.filesreflocktimeout", "core.packedrefstimeout"}
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


class PreparationIntegrityError(ValueError):
    """Raised before CAS when the prepared B/E/S/P transaction is invalid."""


class ReferenceIntegrityError(ValueError):
    """Raised when the local authority ref or object store is invalid."""


class PublicationTransportError(RuntimeError):
    """Raised by a ref adapter when a CAS acknowledgement is unavailable."""


class StalePublication(RuntimeError):
    """Raised when the authority is no longer at the prepared base."""

    def __init__(self, expected: str, observed: str) -> None:
        self.expected = expected
        self.observed = observed
        super().__init__(
            f"history publication base is stale: expected {expected}, observed {observed}"
        )


class PublicationConflict(RuntimeError):
    """Raised when another candidate wins while this CAS is in flight."""

    def __init__(self, expected: str, candidate: str, observed: str) -> None:
        self.expected = expected
        self.candidate = candidate
        self.observed = observed
        super().__init__(
            "history publication conflicted: "
            f"expected {expected}, candidate {candidate}, observed {observed}"
        )


class PublicationIndeterminate(RuntimeError):
    """Raised when the authority cannot be reread after CAS."""

    def __init__(
        self,
        expected: str,
        candidate: str,
        last_observed: str | None,
    ) -> None:
        self.expected = expected
        self.candidate = candidate
        self.last_observed = last_observed
        super().__init__(
            "history publication was not proven; downstream work must remain stopped"
        )


class PublicationNotAdvanced(RuntimeError):
    """Raised when the authority was reread successfully and remains at B."""

    def __init__(self, expected: str, candidate: str, ack: CasAck) -> None:
        self.expected = expected
        self.candidate = candidate
        self.ack = ack
        super().__init__("history publication did not advance the authority ref")


class PublishedReloadError(RuntimeError):
    """Raised when the advanced authority cannot be loaded through production."""

    def __init__(self, publication_commit: str) -> None:
        self.publication_commit = publication_commit
        super().__init__(f"published history reload failed for {publication_commit}")


class CasStatus(StrEnum):
    """Acknowledgement returned by a compare-and-swap adapter."""

    APPLIED = "applied"
    REJECTED = "rejected"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class CasAck:
    """Transport acknowledgement; never sufficient by itself for success."""

    status: CasStatus


class PublicationOutcome(StrEnum):
    """How the final authority reread proved the publication."""

    ADVANCED = "advanced"
    CONFIRMED_AFTER_REREAD = "confirmed_after_reread"
    ALREADY_PUBLISHED = "already_published"


@dataclass(frozen=True)
class PublicationReceipt:
    """A publication proven by a fresh production-authority reload."""

    expected_base: str
    publication_commit: str
    observed_before: str
    observed_after: str
    cas_ack: CasAck | None
    outcome: PublicationOutcome
    history: PublishedHistory


class HistoryRefStore(Protocol):
    """Minimal fixed-main authority port used by the publication state machine."""

    @property
    def repository(self) -> Path: ...

    def read(self) -> str: ...

    def compare_and_swap(self, expected: str, new: str) -> CasAck: ...


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


def _full_oid(value: object, *, label: str) -> str:
    if type(value) is not str or _OID_RE.fullmatch(value) is None:
        raise ReferenceIntegrityError(f"{label} must be a lowercase full commit OID")
    return value


def _is_partial_clone_config_key(name: str) -> bool:
    return name == "extensions.partialclone" or (
        name.startswith("remote.")
        and name.endswith((".promisor", ".partialclonefilter"))
    )


class LocalBareHistoryRefStore:
    """Atomic fixed-main CAS in one complete local bare Git object store."""

    def __init__(self, repository: str | Path) -> None:
        try:
            resolved = Path(repository).resolve(strict=True)
        except (OSError, TypeError, ValueError) as exc:
            raise ReferenceIntegrityError(
                "local authority repository is invalid"
            ) from exc
        if not resolved.is_dir():
            raise ReferenceIntegrityError("local authority repository is invalid")
        self._repository = resolved
        self._require_self_contained_control_files()
        self._require_self_contained_objects()
        self._require_self_contained_refs()
        self._require_single_git_directory()
        self._require_files_ref_backend()
        if self._git_text("rev-parse", "--is-bare-repository") != "true":
            raise ReferenceIntegrityError("local authority must be a bare repository")
        if self._git_text("rev-parse", "--is-shallow-repository") != "false":
            raise ReferenceIntegrityError("local authority requires complete history")
        try:
            head_ref = self._git_text("symbolic-ref", "-q", "HEAD")
        except ReferenceIntegrityError as exc:
            raise ReferenceIntegrityError(
                "local authority HEAD must be refs/heads/main"
            ) from exc
        if head_ref != _MAIN_REF:
            raise ReferenceIntegrityError(
                "local authority HEAD must be refs/heads/main"
            )
        for alternate_name in ("alternates", "http-alternates"):
            alternate_file = resolved / "objects" / "info" / alternate_name
            try:
                has_external_objects = alternate_file.is_file() and bool(
                    alternate_file.read_bytes()
                )
            except OSError as exc:
                raise ReferenceIntegrityError(
                    "local authority object store cannot be inspected"
                ) from exc
            if has_external_objects:
                raise ReferenceIntegrityError(
                    "local authority object store must be self-contained"
                )
        self._require_complete_objects()

    def _require_self_contained_control_files(self) -> None:
        required = (self._repository / "config", self._repository / "HEAD")
        optional = tuple(
            self._repository / name
            for name in ("config.worktree", "shallow", "packed-refs", "commondir")
        )
        try:
            for path in required:
                if path.is_symlink() or not path.is_file():
                    raise ReferenceIntegrityError(
                        "local authority control files must be self-contained"
                    )
            for path in optional:
                if os.path.lexists(path) and (path.is_symlink() or not path.is_file()):
                    raise ReferenceIntegrityError(
                        "local authority control files must be self-contained"
                    )
            config_paths = [self._repository / "config"]
            worktree_config = self._repository / "config.worktree"
            if worktree_config.is_file():
                config_paths.append(worktree_config)
            for config_path in config_paths:
                result = subprocess.run(
                    [
                        "git",
                        "config",
                        "--file",
                        str(config_path),
                        "--no-includes",
                        "--name-only",
                        "--list",
                    ],
                    check=False,
                    capture_output=True,
                    env=_git_environment(),
                )
                if result.returncode != 0:
                    raise ReferenceIntegrityError(
                        "local authority control files cannot be inspected"
                    )
                try:
                    names = result.stdout.decode("ascii").splitlines()
                except UnicodeDecodeError as exc:
                    raise ReferenceIntegrityError(
                        "local authority control files cannot be inspected"
                    ) from exc
                normalized_names = {name.lower() for name in names}
                if any(_is_partial_clone_config_key(name) for name in normalized_names):
                    raise ReferenceIntegrityError(
                        "local authority object store must be complete"
                    )
                if any(
                    name.startswith(("include.", "includeif.", "fsck."))
                    or name in _FORBIDDEN_LOCAL_CONFIG_KEYS
                    for name in normalized_names
                ):
                    raise ReferenceIntegrityError(
                        "local authority control files must be self-contained"
                    )
        except ReferenceIntegrityError:
            raise
        except (OSError, ValueError) as exc:
            raise ReferenceIntegrityError(
                "local authority control files cannot be inspected"
            ) from exc

    def _require_single_git_directory(self) -> None:
        try:
            git_directory_raw = self._git_text("rev-parse", "--absolute-git-dir")
            common_directory_raw = self._git_text("rev-parse", "--git-common-dir")
            if (
                not git_directory_raw
                or "\n" in git_directory_raw
                or not common_directory_raw
                or "\n" in common_directory_raw
            ):
                raise ReferenceIntegrityError(
                    "local authority object store must be self-contained"
                )
            git_directory = Path(git_directory_raw)
            if not git_directory.is_absolute():
                raise ReferenceIntegrityError(
                    "local authority object store must be self-contained"
                )
            git_directory = git_directory.resolve(strict=True)
            common_directory = Path(common_directory_raw)
            if not common_directory.is_absolute():
                common_directory = git_directory / common_directory
            common_directory = common_directory.resolve(strict=True)
        except ReferenceIntegrityError:
            raise
        except (OSError, RuntimeError, ValueError) as exc:
            raise ReferenceIntegrityError(
                "local authority object store cannot be inspected"
            ) from exc
        if git_directory != self._repository or common_directory != self._repository:
            raise ReferenceIntegrityError(
                "local authority object store must be self-contained"
            )

    def _require_self_contained_objects(self) -> None:
        objects = self._repository / "objects"
        if objects.is_symlink() or not objects.is_dir():
            raise ReferenceIntegrityError(
                "local authority object store must be self-contained"
            )
        pending = [objects]
        try:
            while pending:
                directory = pending.pop()
                with os.scandir(directory) as entries:
                    for entry in entries:
                        if entry.is_symlink():
                            raise ReferenceIntegrityError(
                                "local authority object store must be self-contained"
                            )
                        if entry.is_dir(follow_symlinks=False):
                            pending.append(Path(entry.path))
                        elif not entry.is_file(follow_symlinks=False):
                            raise ReferenceIntegrityError(
                                "local authority object store must be self-contained"
                            )
        except ReferenceIntegrityError:
            raise
        except OSError as exc:
            raise ReferenceIntegrityError(
                "local authority object store cannot be inspected"
            ) from exc

    def _require_self_contained_refs(self) -> None:
        head = self._repository / "HEAD"
        refs = self._repository / "refs"
        logs = self._repository / "logs"
        packed_refs = self._repository / "packed-refs"
        try:
            if head.is_symlink() or not head.is_file():
                raise ReferenceIntegrityError(
                    "local authority refs must be self-contained"
                )
            if refs.is_symlink() or not refs.is_dir():
                raise ReferenceIntegrityError(
                    "local authority refs must be self-contained"
                )
            if os.path.lexists(packed_refs) and (
                packed_refs.is_symlink() or not packed_refs.is_file()
            ):
                raise ReferenceIntegrityError(
                    "local authority refs must be self-contained"
                )
            if os.path.lexists(logs) and (logs.is_symlink() or not logs.is_dir()):
                raise ReferenceIntegrityError(
                    "local authority refs must be self-contained"
                )
            pending = [refs]
            if logs.is_dir():
                pending.append(logs)
            while pending:
                directory = pending.pop()
                with os.scandir(directory) as entries:
                    for entry in entries:
                        if entry.is_symlink():
                            raise ReferenceIntegrityError(
                                "local authority refs must be self-contained"
                            )
                        if entry.is_dir(follow_symlinks=False):
                            pending.append(Path(entry.path))
                        elif not entry.is_file(follow_symlinks=False):
                            raise ReferenceIntegrityError(
                                "local authority refs must be self-contained"
                            )
        except ReferenceIntegrityError:
            raise
        except OSError as exc:
            raise ReferenceIntegrityError(
                "local authority refs cannot be inspected"
            ) from exc

    def _require_files_ref_backend(self) -> None:
        backend = self._run("rev-parse", "--show-ref-format")
        if backend.returncode == 0:
            try:
                value = backend.stdout.decode("ascii").strip()
            except UnicodeDecodeError as exc:
                raise ReferenceIntegrityError(
                    "local authority refs cannot be inspected"
                ) from exc
            if value == "files":
                return
            if value != "--show-ref-format":
                raise ReferenceIntegrityError(
                    "local authority refs must be self-contained"
                )

        configured = self._run(
            "config",
            "--local",
            "--get",
            "extensions.refStorage",
        )
        if configured.returncode == 0:
            try:
                configured_value = configured.stdout.decode("ascii").strip()
            except UnicodeDecodeError as exc:
                raise ReferenceIntegrityError(
                    "local authority refs cannot be inspected"
                ) from exc
            if configured_value and configured_value != "files":
                raise ReferenceIntegrityError(
                    "local authority refs must be self-contained"
                )
        elif configured.returncode != 1:
            raise ReferenceIntegrityError("local authority refs cannot be inspected")
        if os.path.lexists(self._repository / "reftable"):
            raise ReferenceIntegrityError("local authority refs must be self-contained")

    def _require_complete_objects(self) -> None:
        partial_config = self._run(
            "config",
            "--local",
            "--get-regexp",
            (
                r"^(extensions\.partialclone|remote\..*\.promisor|"
                r"remote\..*\.partialclonefilter)$"
            ),
        )
        if partial_config.returncode == 0 and partial_config.stdout.strip():
            raise ReferenceIntegrityError(
                "local authority object store must be complete"
            )
        if partial_config.returncode not in {0, 1}:
            raise ReferenceIntegrityError(
                "local authority object store cannot be inspected"
            )
        try:
            if any((self._repository / "objects" / "pack").glob("*.promisor")):
                raise ReferenceIntegrityError(
                    "local authority object store must be complete"
                )
        except OSError as exc:
            raise ReferenceIntegrityError(
                "local authority object store cannot be inspected"
            ) from exc
        integrity = self._run(
            "-c",
            f"fsck.skipList={os.devnull}",
            "fsck",
            "--full",
            "--no-dangling",
        )
        if integrity.returncode != 0:
            raise ReferenceIntegrityError(
                "local authority object store must be complete"
            )

    @property
    def repository(self) -> Path:
        return self._repository

    def _run(self, *arguments: str) -> subprocess.CompletedProcess[bytes]:
        try:
            return subprocess.run(
                [
                    "git",
                    "-c",
                    f"core.hooksPath={os.devnull}",
                    "-c",
                    "core.filesRefLockTimeout=1000",
                    "-c",
                    "core.packedRefsTimeout=1000",
                    "-C",
                    str(self._repository),
                    *arguments,
                ],
                check=False,
                capture_output=True,
                env=_git_environment(),
            )
        except (OSError, ValueError) as exc:
            raise ReferenceIntegrityError("local Git authority is unavailable") from exc

    def _git_text(self, *arguments: str) -> str:
        result = self._run(*arguments)
        if result.returncode != 0:
            raise ReferenceIntegrityError("local Git authority query failed")
        try:
            return result.stdout.decode("ascii").strip()
        except UnicodeDecodeError as exc:
            raise ReferenceIntegrityError(
                "local Git authority output is invalid"
            ) from exc

    def _require_commit(self, value: object, *, label: str) -> str:
        oid = _full_oid(value, label=label)
        resolved = self._git_text(
            "rev-parse",
            "--verify",
            "--end-of-options",
            f"{oid}^{{commit}}",
        )
        if resolved != oid:
            raise ReferenceIntegrityError(f"{label} commit identity mismatch")
        return oid

    def read(self) -> str:
        symbolic = self._run("symbolic-ref", "-q", _MAIN_REF)
        if symbolic.returncode == 0:
            raise ReferenceIntegrityError("local main authority cannot be symbolic")
        if symbolic.returncode not in {1, 128}:
            raise ReferenceIntegrityError("local main authority is invalid")
        oid = self._git_text("show-ref", "--verify", "--hash", _MAIN_REF)
        return self._require_commit(oid, label="observed main")

    def compare_and_swap(self, expected: str, new: str) -> CasAck:
        expected_oid = self._require_commit(expected, label="expected")
        new_oid = self._require_commit(new, label="candidate")
        ancestry = self._run("merge-base", "--is-ancestor", expected_oid, new_oid)
        if ancestry.returncode == 1:
            raise PreparationIntegrityError(
                "history publication candidate is not a fast-forward"
            )
        if ancestry.returncode != 0:
            raise ReferenceIntegrityError("candidate ancestry cannot be verified")
        result = self._run(
            "update-ref",
            "--no-deref",
            _MAIN_REF,
            new_oid,
            expected_oid,
        )
        if result.returncode == 0:
            return CasAck(CasStatus.APPLIED)
        observed = self.read()
        if observed != expected_oid:
            return CasAck(CasStatus.REJECTED)
        return CasAck(CasStatus.UNKNOWN)


def _prepared_repository(
    prepared: PreparedPublication,
    ref_store: HistoryRefStore,
) -> Path:
    try:
        prepared_repository = Path(prepared.repository).resolve(strict=True)
        authority_repository = Path(ref_store.repository).resolve(strict=True)
    except (AttributeError, OSError, TypeError, ValueError) as exc:
        raise PreparationIntegrityError(
            "prepared candidate repository is invalid"
        ) from exc
    if prepared_repository != authority_repository:
        raise PreparationIntegrityError(
            "prepared candidate is not in the authority object store"
        )
    return authority_repository


def _validate_candidate(
    prepared: PreparedPublication,
    repository: Path,
) -> PublishedHistory:
    try:
        if type(prepared.target_draw_date) is not date:
            raise PreparationIntegrityError("prepared target date is invalid")
        base_commit = _full_oid(prepared.base_commit, label="prepared base")
        evidence_commit = _full_oid(prepared.evidence_commit, label="prepared evidence")
        suffix_commit = _full_oid(prepared.suffix_commit, label="prepared suffix")
        publication_commit = _full_oid(
            prepared.publication_commit, label="prepared publication"
        )
        if (
            type(prepared.suffix_head_event_sha256) is not str
            or _SHA256_RE.fullmatch(prepared.suffix_head_event_sha256) is None
            or type(prepared.registry_head_event_sha256) is not str
            or _SHA256_RE.fullmatch(prepared.registry_head_event_sha256) is None
        ):
            raise PreparationIntegrityError("prepared event identity is invalid")
        history = load_published_history(repository, publication_commit)
        if (
            history.registry.publication_commit != publication_commit
            or history.registry.head_event_sha256 != prepared.registry_head_event_sha256
            or history.registry_suffix.head_event_sha256
            != prepared.suffix_head_event_sha256
            or history.registry_suffix.history_through != prepared.target_draw_date
            or history.registry_transaction.base_commit != base_commit
            or history.registry_transaction.evidence_commit != evidence_commit
            or history.registry_transaction.suffix_commit != suffix_commit
            or not history.draws
            or history.draws[-1].draw_date != prepared.target_draw_date
        ):
            raise PreparationIntegrityError(
                "prepared candidate does not match its published B/E/S/P history"
            )
    except PreparationIntegrityError:
        raise
    except Exception as exc:
        raise PreparationIntegrityError(
            "prepared candidate failed production validation"
        ) from exc
    return history


def _reload_published(
    prepared: PreparedPublication,
    repository: Path,
) -> PublishedHistory:
    try:
        return _validate_candidate(prepared, repository)
    except Exception as exc:
        raise PublishedReloadError(prepared.publication_commit) from exc


def publish_prepared_history(
    prepared: PreparedPublication,
    ref_store: HistoryRefStore,
) -> PublicationReceipt:
    """CAS one prepared publication and prove it by rereading fixed main.

    No retry, merge, rebase, force operation, evaluation, or prediction occurs.
    """

    if type(prepared) is not PreparedPublication:
        raise PreparationIntegrityError("prepared candidate type is invalid")
    repository = _prepared_repository(prepared, ref_store)
    _validate_candidate(prepared, repository)
    try:
        observed_before = _full_oid(
            ref_store.read(),
            label="observed authority ref",
        )
    except Exception as exc:
        raise ReferenceIntegrityError("history authority ref cannot be read") from exc

    if observed_before == prepared.publication_commit:
        history = _reload_published(prepared, repository)
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

    try:
        ack = ref_store.compare_and_swap(
            prepared.base_commit,
            prepared.publication_commit,
        )
        if not isinstance(ack, CasAck):
            ack = CasAck(CasStatus.UNKNOWN)
    # Once an adapter call begins, even an integrity-looking exception may have
    # occurred after the ref moved. Only an authoritative reread can classify it.
    except Exception:  # noqa: BLE001
        ack = CasAck(CasStatus.UNKNOWN)
    try:
        observed_after = _full_oid(
            ref_store.read(),
            label="observed authority ref",
        )
    except Exception as exc:
        raise PublicationIndeterminate(
            prepared.base_commit,
            prepared.publication_commit,
            None,
        ) from exc

    if observed_after == prepared.base_commit:
        raise PublicationNotAdvanced(
            prepared.base_commit,
            prepared.publication_commit,
            ack,
        )
    if observed_after != prepared.publication_commit:
        raise PublicationConflict(
            prepared.base_commit,
            prepared.publication_commit,
            observed_after,
        )

    history = _reload_published(prepared, repository)
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
