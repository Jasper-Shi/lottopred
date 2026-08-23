from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from copy import deepcopy
from dataclasses import FrozenInstanceError
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest

from lotto649 import history_registry, verified_history
from lotto649.history_registry import (
    HistoryRegistryIntegrityError,
    load_history_registry,
    resolve_repository_head,
)
from lotto649.operational_history import load_published_history

ROOT = Path(__file__).resolve().parents[1]
GENESIS_COMMIT = "a6857d6b4e6e532062f484bcce4466f76ba4327b"
GENESIS_PARENT = "cf401a8873821b0f5647945752aee320f9452d57"
REGISTRY_PATH = (
    "evidence/operational_history/DI-2026-08-20-registered-history/pin-registry.jsonl"
)
GENESIS_EVENT_SHA256 = (
    "22bcfe219c091dbcdb751ef7a2d9d5251f3040770de6e2e825ac5c64fc69c63d"
)
GENESIS_BLOB = "e95aeaaa28d5c1b7e5fb636d0fc4a3c26ff31017"
GENESIS_FILE_SHA256 = "42a9df8ef861a5fad6e1d7e7639d3d9317e519c0e83e96d7b1148527215afb72"


def _clone_repository(tmp_path: Path) -> Path:
    repository = tmp_path / "repository"
    subprocess.run(
        ["git", "clone", "--no-local", "--quiet", str(ROOT), str(repository)],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(repository), "config", "user.email", "test@example.invalid"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(repository), "config", "user.name", "Registry Test"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(repository), "switch", "--detach", "--quiet", GENESIS_COMMIT],
        check=True,
        capture_output=True,
    )
    return repository


def _git_text(repository: Path, *arguments: str) -> str:
    return (
        subprocess.run(
            ["git", "-C", str(repository), *arguments],
            check=True,
            capture_output=True,
        )
        .stdout.decode("ascii")
        .strip()
    )


def _commit_all(repository: Path, message: str) -> str:
    _git_text(repository, "add", "-A")
    _git_text(repository, "commit", "-q", "-m", message)
    return _git_text(repository, "rev-parse", "HEAD")


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _append_registry_event(
    repository: Path,
    *,
    extra_change_at: str | None = None,
    target_date: str = "2026-08-26",
    wrong_recorded_suffix_sha: bool = False,
    rewrite_suffix_prefix: bool = False,
    suffix_evidence_commit: str | None = None,
    suffix_target_date: str | None = None,
    registry_head_sha256: str | None = None,
) -> tuple[str, dict[str, Any], bytes]:
    registry = repository / REGISTRY_PATH
    existing_registry_raw = registry.read_bytes()
    previous = json.loads(existing_registry_raw.splitlines()[-1])

    base_commit = _git_text(repository, "rev-parse", "HEAD")
    for authority in ("loto_quebec", "wclc"):
        evidence_raw = f"synthetic {authority} receipt for {target_date}\n".encode()
        evidence_sha256 = sha256(evidence_raw).hexdigest()
        relative_path = (
            f"evidence/live_sources/{authority}/{target_date}-{evidence_sha256}.html"
        )
        evidence_path = repository / relative_path
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_path.write_bytes(evidence_raw)
    if extra_change_at == "evidence":
        repository.joinpath("unrelated-evidence.txt").write_bytes(b"foreign change\n")
    evidence_commit = _commit_all(repository, "record synthetic source receipt")

    suffix_path = repository / previous["suffix"]["path"]
    previous_suffix_raw = suffix_path.read_bytes()
    if rewrite_suffix_prefix:
        previous_suffix_raw = (
            bytes([previous_suffix_raw[0] ^ 1]) + previous_suffix_raw[1:]
        )
    suffix_event = {
        "base_seal_sha256": previous["seal"]["sha256"],
        "draw": {
            "bonus": 7,
            "draw_date": suffix_target_date or target_date,
            "numbers": [1, 2, 3, 4, 5, 6],
        },
        "evidence_commit": suffix_evidence_commit or evidence_commit,
        "incident_id": "DI-2026-08-20-registered-history",
        "previous_event_sha256": previous["suffix"]["head_event_sha256"],
        "schema_version": "lotto649-history-suffix-event-v1",
        "sequence": previous["suffix"]["event_count"],
        "source_receipts": [],
    }
    suffix_event["event_sha256"] = sha256(_canonical_json(suffix_event)).hexdigest()
    suffix_raw = previous_suffix_raw + _canonical_json(suffix_event) + b"\n"
    suffix_path.write_bytes(suffix_raw)
    if extra_change_at == "suffix":
        repository.joinpath("unrelated-suffix.txt").write_bytes(b"foreign change\n")
    suffix_commit = _commit_all(repository, "append synthetic verified suffix")
    suffix_blob = _git_text(
        repository, "rev-parse", f"{suffix_commit}:{previous['suffix']['path']}"
    )

    event = deepcopy(previous)
    event.update(
        event_kind="append",
        sequence=previous["sequence"] + 1,
        previous_event_sha256=previous["event_sha256"],
        suffix={
            **previous["suffix"],
            "bytes": len(suffix_raw),
            "event_count": previous["suffix"]["event_count"] + 1,
            "git_blob": suffix_blob,
            "head_event_sha256": (registry_head_sha256 or suffix_event["event_sha256"]),
            "history_through": target_date,
            "sha256": (
                "0" * 64
                if wrong_recorded_suffix_sha
                else sha256(suffix_raw).hexdigest()
            ),
        },
        transaction={
            "base_commit": base_commit,
            "evidence_commit": evidence_commit,
            "suffix_commit": suffix_commit,
        },
    )
    event.pop("event_sha256")
    event["event_sha256"] = sha256(_canonical_json(event)).hexdigest()
    registry_raw = existing_registry_raw + _canonical_json(event) + b"\n"
    registry.write_bytes(registry_raw)
    if extra_change_at == "publication":
        repository.joinpath("unrelated-publication.txt").write_bytes(
            b"foreign change\n"
        )
    publication_commit = _commit_all(repository, "publish synthetic registry event")
    return publication_commit, event, suffix_raw


def _rewrite_latest_event(
    repository: Path,
    mutate: Callable[[dict[str, Any]], None],
) -> str:
    registry = repository / REGISTRY_PATH
    lines = registry.read_bytes().splitlines()
    event = json.loads(lines[-1])
    mutate(event)
    event.pop("event_sha256", None)
    event["event_sha256"] = sha256(_canonical_json(event)).hexdigest()
    registry.write_bytes(b"\n".join([*lines[:-1], _canonical_json(event)]) + b"\n")
    return _commit_all(repository, "rewrite latest synthetic registry event")


def _commit_registry_raw(repository: Path, raw: bytes, message: str) -> str:
    repository.joinpath(REGISTRY_PATH).write_bytes(raw)
    return _commit_all(repository, message)


def _normal_merge_genesis(repository: Path) -> str:
    _git_text(repository, "branch", "registry-side", GENESIS_COMMIT)
    _git_text(repository, "switch", "--detach", "--quiet", GENESIS_PARENT)
    marker = repository / "normal-main.txt"
    marker.write_bytes(b"unrelated first-parent main change\n")
    _commit_all(repository, "advance normal main")
    _git_text(
        repository, "merge", "--no-ff", "-q", "registry-side", "-m", "merge registry"
    )
    return _git_text(repository, "rev-parse", "HEAD")


def _normal_merge_publication(repository: Path, publication_commit: str) -> str:
    _git_text(repository, "branch", "publication-side", publication_commit)
    _git_text(repository, "switch", "--detach", "--quiet", GENESIS_PARENT)
    marker = repository / "normal-main.txt"
    marker.write_bytes(b"unrelated first-parent main change\n")
    _commit_all(repository, "advance normal main before publication merge")
    _git_text(
        repository,
        "merge",
        "--no-ff",
        "-q",
        "publication-side",
        "-m",
        "merge registry publication",
    )
    return _git_text(repository, "rev-parse", "HEAD")


def test_loads_the_registered_genesis_state_from_immutable_git_blobs():
    state = load_history_registry(ROOT, GENESIS_COMMIT)

    assert state.sequence == 0
    assert state.event_kind == "genesis_migration"
    assert state.event_sha256 == GENESIS_EVENT_SHA256
    assert state.provenance.registry_path == REGISTRY_PATH
    assert state.provenance.requested_revision == GENESIS_COMMIT
    assert state.provenance.resolved_revision == GENESIS_COMMIT
    assert state.provenance.publication_commit == GENESIS_COMMIT
    assert state.provenance.genesis_commit == GENESIS_COMMIT
    assert state.provenance.genesis_parent == GENESIS_PARENT
    assert state.provenance.git_blob == GENESIS_BLOB
    assert state.provenance.bytes == 1_170
    assert state.provenance.file_sha256 == GENESIS_FILE_SHA256
    assert state.provenance.event_count == 1
    assert state.provenance.head_event_sha256 == GENESIS_EVENT_SHA256

    assert state.seal.path.endswith("/seal.json")
    assert state.seal.commit == "b3056cd1772f8e992e27a9eb87e5037eb15e2b79"
    assert state.seal.git_blob == "23c05e7d2c1344f77085b228bfc919e88e3c4af3"
    assert state.seal.bytes == 4_586
    assert sha256(state.seal_raw).hexdigest() == state.seal.sha256

    assert state.suffix.path.endswith("/live_draws.jsonl")
    assert state.suffix.git_blob == "3fa0319cc9d98fc17c49d4917e222d2da10aef07"
    assert state.suffix.bytes == 3_079
    assert state.suffix.event_count == 2
    assert state.suffix.head_event_sha256 == (
        "3022b98fefbe3dbbc80423574319c169edcc845bf2218152c6abe18d0be27475"
    )
    assert state.suffix.history_through.isoformat() == "2026-08-22"
    assert sha256(state.suffix_raw).hexdigest() == state.suffix.sha256

    assert state.transaction.base_commit == state.seal.commit
    assert state.transaction.evidence_commit == (
        "60dbd42a502850091508491f9011f9a08acf894f"
    )
    assert state.transaction.suffix_commit == (
        "0b476b6de1f6bed1382c29187fd5cdaa4f70c153"
    )
    with pytest.raises(FrozenInstanceError):
        state.sequence = 1


def test_resolves_head_once_and_ignores_worktree_and_hostile_git_environment(
    tmp_path, monkeypatch
):
    repository = _clone_repository(tmp_path)
    state = load_history_registry(repository, resolve_repository_head(repository))
    repository.joinpath(REGISTRY_PATH).write_bytes(b"FOREIGN WORKTREE BYTES\n")
    repository.joinpath(state.seal.path).write_bytes(b"FOREIGN SEAL\n")
    repository.joinpath(state.suffix.path).write_bytes(b"FOREIGN SUFFIX\n")
    monkeypatch.setenv("GIT_DIR", str(tmp_path / "foreign.git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(tmp_path / "foreign-worktree"))
    monkeypatch.setenv("GIT_OBJECT_DIRECTORY", str(tmp_path / "foreign-objects"))
    monkeypatch.setenv("GIT_ALTERNATE_OBJECT_DIRECTORIES", str(tmp_path / "objects"))
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "core.repositoryformatversion")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "999")

    resolved = resolve_repository_head(repository)
    reloaded = load_history_registry(repository, resolved)

    assert resolved == GENESIS_COMMIT
    assert reloaded == state


def test_loads_the_latest_append_event_and_its_publication_provenance(tmp_path):
    repository = _clone_repository(tmp_path)
    publication_commit, event, suffix_raw = _append_registry_event(repository)

    state = load_history_registry(repository, publication_commit)

    assert state.sequence == 1
    assert state.event_kind == "append"
    assert state.event_sha256 == event["event_sha256"]
    assert state.suffix_raw == suffix_raw
    assert state.suffix.event_count == 3
    assert state.suffix.history_through.isoformat() == "2026-08-26"
    assert state.transaction.suffix_commit == event["transaction"]["suffix_commit"]
    assert state.provenance.requested_revision == publication_commit
    assert state.provenance.resolved_revision == publication_commit
    assert state.provenance.publication_commit == publication_commit
    assert state.provenance.event_count == 2
    assert state.provenance.head_event_sha256 == event["event_sha256"]


def test_loads_multiple_strictly_appended_registry_publications(tmp_path):
    repository = _clone_repository(tmp_path)
    first_publication, _, _ = _append_registry_event(repository)
    second_publication, second_event, second_suffix_raw = _append_registry_event(
        repository,
        target_date="2026-08-29",
    )

    state = load_history_registry(repository, second_publication)

    assert state.sequence == 2
    assert state.suffix.event_count == 4
    assert state.suffix.history_through.isoformat() == "2026-08-29"
    assert state.suffix_raw == second_suffix_raw
    assert state.transaction.base_commit == first_publication
    assert state.provenance.publication_commit == second_publication
    assert state.provenance.event_count == 3
    assert state.provenance.head_event_sha256 == second_event["event_sha256"]


def test_transparent_normal_merge_can_carry_the_genesis_registry_state(tmp_path):
    repository = _clone_repository(tmp_path)
    merge_commit = _normal_merge_genesis(repository)
    assert _git_text(repository, "rev-parse", f"{merge_commit}^2") == GENESIS_COMMIT

    state = load_history_registry(repository, merge_commit)

    assert state.sequence == 0
    assert state.provenance.resolved_revision == merge_commit
    assert state.provenance.publication_commit == GENESIS_COMMIT
    assert state.provenance.git_blob == GENESIS_BLOB


def test_transparent_normal_merge_preserves_the_append_publication_identity(tmp_path):
    repository = _clone_repository(tmp_path)
    publication_commit, event, _ = _append_registry_event(repository)
    merge_commit = _normal_merge_publication(repository, publication_commit)
    assert _git_text(repository, "rev-parse", f"{merge_commit}^2") == publication_commit

    state = load_history_registry(repository, merge_commit)

    assert state.event_sha256 == event["event_sha256"]
    assert state.provenance.resolved_revision == merge_commit
    assert state.provenance.publication_commit == publication_commit


def test_append_base_can_be_a_transparent_merge_and_code_descendant(tmp_path):
    repository = _clone_repository(tmp_path)
    _normal_merge_genesis(repository)
    repository.joinpath("src/transparent-reader-change.py").write_bytes(
        b"# unrelated reviewed code\n"
    )
    base_commit = _commit_all(repository, "transparent reader change")
    publication_commit, event, _ = _append_registry_event(repository)

    state = load_history_registry(repository, publication_commit)

    assert state.transaction.base_commit == base_commit
    assert state.provenance.publication_commit == publication_commit
    assert state.event_sha256 == event["event_sha256"]


def test_rejects_nonfrozen_registry_schema_and_bool_as_int(tmp_path):
    mutations = [
        lambda event: event.update(unregistered_extension=True),
        lambda event: event.pop("incident_id"),
        lambda event: event.update(schema_version="lotto649-history-pin-registry-v2"),
        lambda event: event.update(incident_id="DI-coordinated-rewrite"),
        lambda event: event.update(event_kind=[]),
        lambda event: event.update(event_kind={}),
        lambda event: event.update(sequence=True),
        lambda event: event["seal"].update(unregistered_extension=True),
        lambda event: event["seal"].update(bytes=True),
        lambda event: event["suffix"].pop("event_count"),
        lambda event: event["suffix"].update(event_count=True),
        lambda event: event["transaction"].update(evidence_commit=True),
    ]
    repository = _clone_repository(tmp_path)
    valid_publication, _, _ = _append_registry_event(repository)

    for mutate in mutations:
        _git_text(repository, "switch", "--detach", "--quiet", valid_publication)
        rewritten_revision = _rewrite_latest_event(repository, mutate)
        with pytest.raises(HistoryRegistryIntegrityError, match="schema"):
            load_history_registry(repository, rewritten_revision)


def test_rejects_coordinated_rewrites_of_frozen_and_monotonic_event_semantics(
    tmp_path,
):
    mutations = [
        lambda event: event["seal"].update(commit=GENESIS_PARENT),
        lambda event: event["suffix"].update(event_count=2),
        lambda event: event["suffix"].update(bytes=3_079),
        lambda event: event["suffix"].update(history_through="2026-08-22"),
        lambda event: event["suffix"].update(
            head_event_sha256=(
                "3022b98fefbe3dbbc80423574319c169edcc845bf2218152c6abe18d0be27475"
            )
        ),
        lambda event: event["transaction"].update(
            evidence_commit=event["transaction"]["base_commit"]
        ),
    ]
    repository = _clone_repository(tmp_path)
    valid_publication, _, _ = _append_registry_event(repository)

    for mutate in mutations:
        _git_text(repository, "switch", "--detach", "--quiet", valid_publication)
        rewritten_revision = _rewrite_latest_event(repository, mutate)
        with pytest.raises(HistoryRegistryIntegrityError, match="semantic"):
            load_history_registry(repository, rewritten_revision)


def test_rejects_extra_changes_in_the_evidence_suffix_and_publication_commits(
    tmp_path,
):
    repository = _clone_repository(tmp_path)

    for stage in ("evidence", "suffix", "publication"):
        _git_text(repository, "switch", "--detach", "--quiet", GENESIS_COMMIT)
        publication, _, _ = _append_registry_event(
            repository,
            extra_change_at=stage,
        )
        with pytest.raises(HistoryRegistryIntegrityError, match="closure"):
            load_history_registry(repository, publication)


def test_rejects_a_suffix_commit_that_rewrites_the_pinned_prefix(tmp_path):
    repository = _clone_repository(tmp_path)
    publication, _, _ = _append_registry_event(
        repository,
        rewrite_suffix_prefix=True,
    )

    with pytest.raises(HistoryRegistryIntegrityError, match="append-only"):
        load_history_registry(repository, publication)


def test_rejects_noncanonical_truncated_and_rehashed_registry_bytes(tmp_path):
    repository = _clone_repository(tmp_path)
    genesis_raw = repository.joinpath(REGISTRY_PATH).read_bytes()
    genesis_event = json.loads(genesis_raw)
    wrong_hash = deepcopy(genesis_event)
    wrong_hash["event_sha256"] = "0" * 64
    variants = [
        (json.dumps(genesis_event, indent=2, sort_keys=True) + "\n").encode(),
        genesis_raw.removesuffix(b"\n"),
        genesis_raw + b"\n",
        _canonical_json(wrong_hash) + b"\n",
    ]

    for index, raw in enumerate(variants):
        _git_text(repository, "switch", "--detach", "--quiet", GENESIS_COMMIT)
        revision = _commit_registry_raw(repository, raw, f"invalid registry {index}")
        with pytest.raises(HistoryRegistryIntegrityError):
            load_history_registry(repository, revision)


def test_requires_an_exact_reachable_full_commit_oid():
    for revision in (
        "HEAD",
        GENESIS_COMMIT.upper(),
        "f" * 39,
        "f" * 40,
        GENESIS_PARENT,
    ):
        with pytest.raises(HistoryRegistryIntegrityError):
            load_history_registry(ROOT, revision)


@pytest.mark.parametrize("shallow_boundary", [GENESIS_COMMIT, GENESIS_PARENT])
def test_rejects_every_shallow_repository_boundary(tmp_path, shallow_boundary):
    repository = _clone_repository(tmp_path)
    repository.joinpath(".git/shallow").write_text(
        f"{shallow_boundary}\n", encoding="ascii"
    )

    with pytest.raises(HistoryRegistryIntegrityError, match="full history"):
        load_history_registry(repository, GENESIS_COMMIT)


def test_rejects_nonregular_registry_tree_modes(tmp_path):
    repository = _clone_repository(tmp_path)
    registry = repository / REGISTRY_PATH
    registry.unlink()
    registry.symlink_to("foreign-registry.jsonl")
    revision = _commit_all(repository, "replace registry with symlink")

    with pytest.raises(HistoryRegistryIntegrityError, match="regular"):
        load_history_registry(repository, revision)


def test_replace_refs_and_grafts_cannot_rewrite_registered_ancestry(tmp_path):
    repository = _clone_repository(tmp_path)
    _git_text(repository, "replace", GENESIS_COMMIT, GENESIS_PARENT)
    grafts = repository / ".git/info/grafts"
    grafts.parent.mkdir(parents=True, exist_ok=True)
    grafts.write_text(f"{GENESIS_COMMIT}\n", encoding="ascii")

    state = load_history_registry(repository, GENESIS_COMMIT)

    assert state.provenance.genesis_parent == GENESIS_PARENT


def test_rejects_reserved_path_rewrite_then_restore_before_the_next_base(tmp_path):
    repository = _clone_repository(tmp_path)
    suffix_path = (
        repository / load_history_registry(repository, GENESIS_COMMIT).suffix.path
    )
    original = suffix_path.read_bytes()
    suffix_path.write_bytes(b"coordinated intermediate rewrite\n")
    _commit_all(repository, "rewrite reserved suffix")
    suffix_path.write_bytes(original)
    _commit_all(repository, "restore reserved suffix")
    publication, _, _ = _append_registry_event(repository)

    with pytest.raises(HistoryRegistryIntegrityError, match="reserved path"):
        load_history_registry(repository, publication)


def test_rejects_reserved_path_rewrite_then_restore_on_a_merged_side_branch(
    tmp_path,
):
    repository = _clone_repository(tmp_path)
    suffix_path = (
        repository / load_history_registry(repository, GENESIS_COMMIT).suffix.path
    )
    original = suffix_path.read_bytes()
    _git_text(repository, "switch", "--detach", "--quiet", GENESIS_PARENT)
    suffix_path.write_bytes(b"coordinated side-branch rewrite\n")
    _commit_all(repository, "rewrite reserved suffix on side branch")
    suffix_path.write_bytes(original)
    _commit_all(repository, "restore reserved suffix on side branch")
    _git_text(
        repository,
        "merge",
        "--no-ff",
        "-q",
        GENESIS_COMMIT,
        "-m",
        "merge registry after side-branch restoration",
    )
    merge_commit = _git_text(repository, "rev-parse", "HEAD")

    with pytest.raises(HistoryRegistryIntegrityError, match="reserved path"):
        load_published_history(repository, merge_commit)


@pytest.mark.parametrize(
    "overrides",
    [
        {"suffix_evidence_commit": GENESIS_PARENT},
        {"suffix_target_date": "2026-08-27"},
        {"registry_head_sha256": "f" * 64},
    ],
)
def test_each_registry_append_binds_its_own_suffix_event(tmp_path, overrides):
    repository = _clone_repository(tmp_path)
    publication, _, _ = _append_registry_event(repository, **overrides)

    with pytest.raises(HistoryRegistryIntegrityError, match="semantic"):
        load_history_registry(repository, publication)


def test_git_readers_disable_promisor_lazy_fetch(tmp_path):
    assert history_registry._git_environment()["GIT_NO_LAZY_FETCH"] == "1"
    assert verified_history._git_environment()["GIT_NO_LAZY_FETCH"] == "1"

    source = tmp_path / "source.git"
    partial = tmp_path / "partial"
    subprocess.run(
        ["git", "clone", "--bare", "--quiet", str(ROOT), str(source)],
        check=True,
        capture_output=True,
    )
    _git_text(source, "config", "uploadpack.allowFilter", "true")
    subprocess.run(
        [
            "git",
            "clone",
            "--quiet",
            "--filter=blob:none",
            "--no-checkout",
            source.as_uri(),
            str(partial),
        ],
        check=True,
        capture_output=True,
    )
    revision = _git_text(partial, "rev-parse", "HEAD")
    pack_directory = partial / ".git" / "objects" / "pack"
    before = sorted(path.name for path in pack_directory.iterdir())

    with pytest.raises(HistoryRegistryIntegrityError):
        load_history_registry(partial, revision)

    assert sorted(path.name for path in pack_directory.iterdir()) == before


def test_rejects_unpinned_reserved_changes_after_publication(tmp_path):
    repository = _clone_repository(tmp_path)
    publication, event, _ = _append_registry_event(repository)
    suffix_path = repository / event["suffix"]["path"]
    suffix_path.write_bytes(suffix_path.read_bytes() + b"unpinned bytes\n")
    unpinned_revision = _commit_all(repository, "change suffix without publication")

    with pytest.raises(HistoryRegistryIntegrityError, match="reserved path"):
        load_history_registry(repository, unpinned_revision)

    _git_text(repository, "switch", "--detach", "--quiet", publication)
    repository.joinpath("unrelated-code.py").write_bytes(b"# transparent\n")
    transparent_revision = _commit_all(repository, "transparent code change")
    state = load_history_registry(repository, transparent_revision)
    assert state.provenance.publication_commit == publication
    assert state.provenance.resolved_revision == transparent_revision
