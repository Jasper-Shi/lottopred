"""Production authority for the currently deployed verified draw history."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .verified_history import VerifiedHistory, load_verified_history

INCIDENT_ID = "DI-2026-08-20-registered-history"
DEPLOYED_SEAL_PATH = f"evidence/data_integrity/{INCIDENT_ID}/seal.json"
DEPLOYED_SUFFIX_PATH = f"data/processed/epochs/{INCIDENT_ID}/live_draws.jsonl"
DEPLOYED_SEAL_SHA256 = (
    "80397752105b567d6a8bdd3673b12ffa470a12efbd792719a4f6c89ef391f6fd"
)
DEPLOYED_SUFFIX_SHA256 = (
    "b91be6a4057648abd86dc0e6fc5d762fc4cd9b222519c147d635703cc550a803"
)
DEPLOYED_SUFFIX_HEAD_SHA256 = (
    "3022b98fefbe3dbbc80423574319c169edcc845bf2218152c6abe18d0be27475"
)


class OperationalHistoryConfigurationError(ValueError):
    """Raised when the repository root required by the authority is absent."""


def _repository_root(cfg: Mapping[str, Any]) -> Path:
    raw_root = cfg.get("_root")
    if isinstance(raw_root, Path):
        return raw_root
    if isinstance(raw_root, str) and raw_root:
        return Path(raw_root)
    raise OperationalHistoryConfigurationError(
        "operational history requires an explicit repository root"
    )


def load_operational_history(cfg: Mapping[str, Any]) -> VerifiedHistory:
    """Load the sole operational history using code-reviewed external pins.

    Caller-provided configuration cannot replace the registered paths or hashes.
    Updating any production authority is therefore a source change with tests and
    review, rather than a mutable runtime option.
    """

    return load_verified_history(
        _repository_root(cfg),
        seal_path=DEPLOYED_SEAL_PATH,
        expected_seal_sha256=DEPLOYED_SEAL_SHA256,
        suffix_path=DEPLOYED_SUFFIX_PATH,
        expected_suffix_sha256=DEPLOYED_SUFFIX_SHA256,
        expected_suffix_head_sha256=DEPLOYED_SUFFIX_HEAD_SHA256,
    )


def operational_history_provenance(history: VerifiedHistory) -> dict[str, Any]:
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
        "draw_count": len(history.draws),
        "history_through": history.suffix.history_through.isoformat(),
    }
