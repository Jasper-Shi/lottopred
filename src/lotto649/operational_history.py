"""Production authority for the currently deployed verified draw history."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .history_registry import (
    RegistryProvenance,
    RegistrySealIdentity,
    RegistrySuffixIdentity,
    RegistryTransaction,
    load_history_registry,
    resolve_repository_head,
)
from .verified_history import (
    VerifiedHistory,
    _load_verified_history_from_immutable_bytes,
)

INCIDENT_ID = "DI-2026-08-20-registered-history"


class OperationalHistoryConfigurationError(ValueError):
    """Raised when the repository root required by the authority is absent."""


class OperationalHistoryIntegrityError(ValueError):
    """Raised when the registry and verified history disagree."""


@dataclass(frozen=True)
class PublishedHistory(VerifiedHistory):
    """Verified draws plus the immutable Git publication authority."""

    registry: RegistryProvenance
    registry_seal: RegistrySealIdentity
    registry_suffix: RegistrySuffixIdentity
    registry_transaction: RegistryTransaction


def _repository_root(cfg: Mapping[str, Any]) -> Path:
    raw_root = cfg.get("_root")
    if isinstance(raw_root, Path):
        return raw_root
    if isinstance(raw_root, str) and raw_root:
        return Path(raw_root)
    raise OperationalHistoryConfigurationError(
        "operational history requires an explicit repository root"
    )


def load_published_history(repository: Path, revision: str) -> PublishedHistory:
    """Load one exact Git revision through the registry and history validators."""

    authority = load_history_registry(repository, revision)
    history = _load_verified_history_from_immutable_bytes(
        repository,
        seal_raw=authority.seal_raw,
        seal_relative=authority.seal.path,
        expected_seal_sha256=authority.seal.sha256,
        suffix_raw=authority.suffix_raw,
        suffix_relative=authority.suffix.path,
        expected_suffix_sha256=authority.suffix.sha256,
        expected_suffix_head_sha256=authority.suffix.head_event_sha256,
    )
    if (
        history.epoch != INCIDENT_ID
        or history.seal.file_sha256 != authority.seal.sha256
        or history.suffix.file_sha256 != authority.suffix.sha256
        or history.suffix.event_count != authority.suffix.event_count
        or history.suffix.head_event_sha256 != authority.suffix.head_event_sha256
        or history.suffix.history_through != authority.suffix.history_through
        or not history.suffix.evidence_commits
        or history.suffix.evidence_commits[-1] != authority.transaction.evidence_commit
    ):
        raise OperationalHistoryIntegrityError(
            "registry authority does not match verified history"
        )
    return PublishedHistory(
        draws=history.draws,
        epoch=history.epoch,
        seal=history.seal,
        base=history.base,
        suffix=history.suffix,
        registry=authority.provenance,
        registry_seal=authority.seal,
        registry_suffix=authority.suffix,
        registry_transaction=authority.transaction,
    )


def load_operational_history(cfg: Mapping[str, Any]) -> PublishedHistory:
    """Load the sole operational history from the immutable registry at HEAD.

    Caller configuration cannot replace the registry, revision, paths, or hashes.
    The repository's HEAD is resolved once to an exact commit before validation.
    """

    repository = _repository_root(cfg)
    revision = resolve_repository_head(repository)
    return load_published_history(repository, revision)


def operational_history_provenance(history: PublishedHistory) -> dict[str, Any]:
    """Return the canonical JSON-safe identity carried into audit artifacts."""

    return {
        "epoch": history.epoch,
        "seal_sha256": history.seal.file_sha256,
        "artifact_commit": history.seal.artifact_commit,
        "base_rows_sha256": history.base.rows_sha256,
        "base_draw_count": history.base.draw_count,
        "suffix_sha256": history.suffix.file_sha256,
        "suffix_head_sha256": history.suffix.head_event_sha256,
        "suffix_event_count": history.suffix.event_count,
        "suffix_evidence_commits": list(history.suffix.evidence_commits),
        "observed_revision": history.registry.resolved_revision,
        "publication_commit": history.registry.publication_commit,
        "registry_path": history.registry.registry_path,
        "registry_genesis_commit": history.registry.genesis_commit,
        "registry_git_blob": history.registry.git_blob,
        "registry_sha256": history.registry.file_sha256,
        "registry_event_count": history.registry.event_count,
        "registry_head_sha256": history.registry.head_event_sha256,
        "seal_git_blob": history.registry_seal.git_blob,
        "suffix_git_blob": history.registry_suffix.git_blob,
        "suffix_commit": history.registry_transaction.suffix_commit,
        "latest_evidence_commit": history.registry_transaction.evidence_commit,
        "draw_count": len(history.draws),
        "history_through": history.suffix.history_through.isoformat(),
    }
