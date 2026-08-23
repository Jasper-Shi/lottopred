from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "seal_data_integrity_incident.py"
TOOL_SPEC = importlib.util.spec_from_file_location(
    "seal_data_integrity_incident_tool", TOOL_PATH
)
assert TOOL_SPEC is not None and TOOL_SPEC.loader is not None
seal_tool = importlib.util.module_from_spec(TOOL_SPEC)
sys.modules[TOOL_SPEC.name] = seal_tool
TOOL_SPEC.loader.exec_module(seal_tool)


def _canonical_json(value) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode()


def _coordinated_rewrite(payload, mutate) -> bytes:
    body = {key: value for key, value in payload.items() if key != "seal_body_sha256"}
    mutate(body)
    rewritten = {
        **body,
        "seal_body_sha256": sha256(_canonical_json(body)).hexdigest(),
    }
    return _canonical_json(rewritten) + b"\n"


def _shared_repository(tmp_path: Path, name: str) -> Path:
    repository = tmp_path / name
    subprocess.run(
        [
            "git",
            "clone",
            "-q",
            "--shared",
            "--no-checkout",
            str(ROOT),
            str(repository),
        ],
        check=True,
        capture_output=True,
    )
    return repository


def _commit_tree_edit(
    *,
    repository: Path,
    index_path: Path,
    base_tree: str,
    parent: str,
    relative_path: str,
    raw: bytes,
    created_at: str,
) -> str:
    blob = (
        subprocess.run(
            ["git", "-C", str(repository), "hash-object", "-w", "--stdin"],
            input=raw,
            check=True,
            capture_output=True,
        )
        .stdout.decode()
        .strip()
    )
    index_environment = {**os.environ, "GIT_INDEX_FILE": str(index_path)}
    subprocess.run(
        ["git", "-C", str(repository), "read-tree", base_tree],
        check=True,
        env=index_environment,
    )
    subprocess.run(
        [
            "git",
            "-C",
            str(repository),
            "update-index",
            "--add",
            "--cacheinfo",
            "100644",
            blob,
            relative_path,
        ],
        check=True,
        env=index_environment,
    )
    tree = subprocess.run(
        ["git", "-C", str(repository), "write-tree"],
        check=True,
        capture_output=True,
        text=True,
        env=index_environment,
    ).stdout.strip()
    commit_environment = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Seal Test",
        "GIT_AUTHOR_EMAIL": "test@example.invalid",
        "GIT_COMMITTER_NAME": "Seal Test",
        "GIT_COMMITTER_EMAIL": "test@example.invalid",
        "GIT_AUTHOR_DATE": created_at,
        "GIT_COMMITTER_DATE": created_at,
    }
    return (
        subprocess.run(
            ["git", "-C", str(repository), "commit-tree", tree, "-p", parent],
            input=b"adversarial artifact commit\n",
            check=True,
            capture_output=True,
            env=commit_environment,
        )
        .stdout.decode()
        .strip()
    )


def test_creates_and_validates_a_seal_over_the_registered_git_artifact(tmp_path):
    seal_path = tmp_path / "seal.json"

    created = seal_tool.create_data_integrity_incident_seal(
        repository=ROOT,
        seal_path=seal_path,
        policy=seal_tool.REGISTERED_SEAL_POLICY,
    )

    raw = seal_path.read_bytes()
    expected_file_sha256 = sha256(raw).hexdigest()
    assert raw.endswith(b"\n")
    assert b"\n " not in raw
    assert json.loads(raw) == created
    assert created["schema_version"] == "lotto649-data-integrity-seal-v1"
    assert set(created) == {
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
    assert created["incident_id"] == "DI-2026-08-20-registered-history"
    assert created["artifact_commit"] == ("b04393944ef12f78417dfb6151343c72d4c2a2ac")
    assert created["artifact_parent"] == ("e585ae797ddcafa423121bf473d70b177a3bd92c")
    assert created["artifact_commit_created_at"] == "2026-08-23T16:58:17Z"
    assert not hasattr(seal_tool.REGISTERED_SEAL_POLICY, "created_at")
    assert created["status"] == "sealed_closed_corrected_epoch"
    assert created["reconciliation_manifest"]["manifest_sha256"] == (
        "987bf9daaff088c66b43cef17ffdc71a9eb28d64f25aec5cbc88a2d55bdec32d"
    )
    assert created["corrected_epoch"]["draw_count"] == 4_442
    assert set(created["corrected_epoch"]) == {
        "path",
        "git_blob",
        "bytes",
        "file_sha256",
        "draw_count",
        "rows_sha256",
        "history_start",
        "history_through",
    }
    assert set(created["registered_old_identity"]) == {
        "commit",
        "path",
        "git_blob",
        "bytes",
        "byte_sha256",
        "draw_count",
        "rows_sha256",
    }
    assert set(created["source_collection"]) == {
        "asset_count",
        "source_assets_sha256",
        "draw_count",
        "collection_line_sha256",
        "json_rows_sha256",
        "history_start",
        "history_through",
    }
    assert set(created["artifacts"]) == {
        "data/processed/epochs/DI-2026-08-20-registered-history/corrected_draws.csv",
        "evidence/data_integrity/DI-2026-08-20-registered-history/incident.json",
        "evidence/data_integrity/DI-2026-08-20-registered-history/official_draws.csv",
        (
            "evidence/data_integrity/DI-2026-08-20-registered-history/"
            "reconciliation.manifest.json"
        ),
        (
            "evidence/data_integrity/DI-2026-08-20-registered-history/"
            "reviewed-adjudication.json"
        ),
        "evidence/data_integrity/DI-2026-08-20-registered-history/source-index.json",
    }
    assert set(created["code_identities"]) == {
        "src/lotto649/data_integrity.py",
        "src/lotto649/official_history.py",
        "tests/test_data_integrity.py",
        "tests/test_data_integrity_incident.py",
        "tests/test_official_history.py",
        "tools/build_data_integrity_incident.py",
    }
    assert all(
        set(identity) == {"git_blob", "bytes", "sha256"}
        for identity in (
            *created["artifacts"].values(),
            *created["code_identities"].values(),
        )
    )
    assert created["reconciliation_summary"] == {
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

    validated = seal_tool.validate_data_integrity_incident_seal(
        repository=ROOT,
        seal_path=seal_path,
        expected_seal_sha256=expected_file_sha256,
        policy=seal_tool.REGISTERED_SEAL_POLICY,
    )
    assert validated == created


def test_creator_refuses_to_overwrite_any_existing_seal_bytes(tmp_path):
    seal_path = tmp_path / "seal.json"
    existing = b"owner-controlled-existing-seal\n"
    seal_path.write_bytes(existing)

    with pytest.raises(
        seal_tool.IncidentSealError,
        match="refusing to overwrite an existing seal",
    ):
        seal_tool.create_data_integrity_incident_seal(
            repository=ROOT,
            seal_path=seal_path,
            policy=seal_tool.REGISTERED_SEAL_POLICY,
        )

    assert seal_path.read_bytes() == existing


def test_creator_preserves_and_refuses_a_foreign_dangling_symlink(tmp_path):
    seal_path = tmp_path / "seal.json"
    missing_target = tmp_path / "foreign-missing-target"
    seal_path.symlink_to(missing_target)

    with pytest.raises(
        seal_tool.IncidentSealError,
        match="refusing to overwrite an existing seal",
    ):
        seal_tool.create_data_integrity_incident_seal(
            repository=ROOT,
            seal_path=seal_path,
            policy=seal_tool.REGISTERED_SEAL_POLICY,
        )

    assert seal_path.is_symlink()
    assert seal_path.readlink() == missing_target
    assert not missing_target.exists()
    assert list(tmp_path.glob(".seal.json.staging-*")) == []


def test_concurrent_creators_have_exactly_one_exclusive_winner(tmp_path):
    seal_path = tmp_path / "seal.json"

    def attempt_creation():
        try:
            payload = seal_tool.create_data_integrity_incident_seal(
                repository=ROOT,
                seal_path=seal_path,
                policy=seal_tool.REGISTERED_SEAL_POLICY,
            )
        except seal_tool.IncidentSealError as exc:
            return "rejected", str(exc)
        return "created", payload["seal_body_sha256"]

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(lambda _index: attempt_creation(), range(2)))

    assert sorted(outcome[0] for outcome in outcomes) == ["created", "rejected"]
    assert "refusing to overwrite an existing seal" in next(
        outcome[1] for outcome in outcomes if outcome[0] == "rejected"
    )
    raw = seal_path.read_bytes()
    assert (
        seal_tool.validate_data_integrity_incident_seal(
            repository=ROOT,
            seal_path=seal_path,
            expected_seal_sha256=sha256(raw).hexdigest(),
            policy=seal_tool.REGISTERED_SEAL_POLICY,
        )["status"]
        == "sealed_closed_corrected_epoch"
    )
    assert list(tmp_path.glob(".seal.json.staging-*")) == []


def test_link_side_effect_then_error_rolls_back_the_formal_seal(tmp_path, monkeypatch):
    seal_path = tmp_path / "seal.json"
    real_link = seal_tool.os.link

    def link_then_raise(source, destination, *, follow_symlinks=True):
        real_link(source, destination, follow_symlinks=follow_symlinks)
        raise OSError("injected error after link side effect")

    monkeypatch.setattr(seal_tool.os, "link", link_then_raise)

    with pytest.raises(
        seal_tool.IncidentSealError,
        match="unable to publish seal exclusively",
    ):
        seal_tool.create_data_integrity_incident_seal(
            repository=ROOT,
            seal_path=seal_path,
            policy=seal_tool.REGISTERED_SEAL_POLICY,
        )

    assert not os.path.lexists(seal_path)
    assert list(tmp_path.glob(".seal.json.staging-*")) == []


def test_link_side_effect_then_base_exception_rolls_back_the_formal_seal(
    tmp_path, monkeypatch
):
    seal_path = tmp_path / "seal.json"
    real_link = seal_tool.os.link

    def link_then_interrupt(source, destination, *, follow_symlinks=True):
        real_link(source, destination, follow_symlinks=follow_symlinks)
        raise KeyboardInterrupt("injected interruption after link side effect")

    monkeypatch.setattr(seal_tool.os, "link", link_then_interrupt)

    with pytest.raises(KeyboardInterrupt, match="injected interruption"):
        seal_tool.create_data_integrity_incident_seal(
            repository=ROOT,
            seal_path=seal_path,
            policy=seal_tool.REGISTERED_SEAL_POLICY,
        )

    assert not os.path.lexists(seal_path)
    assert list(tmp_path.glob(".seal.json.staging-*")) == []


def test_postlink_identity_inspection_error_rolls_back_the_formal_seal(
    tmp_path, monkeypatch
):
    seal_path = tmp_path / "seal.json"
    real_lstat = seal_tool.os.lstat
    failed = False

    def fail_first_postlink_inspection(path):
        nonlocal failed
        try:
            final_exists = Path(path) == seal_path and real_lstat(path) is not None
        except FileNotFoundError:
            final_exists = False
        if final_exists and not failed:
            failed = True
            raise OSError("injected postlink identity inspection failure")
        return real_lstat(path)

    monkeypatch.setattr(seal_tool.os, "lstat", fail_first_postlink_inspection)

    with pytest.raises(
        seal_tool.IncidentSealError,
        match="unable to inspect seal path ownership",
    ):
        seal_tool.create_data_integrity_incident_seal(
            repository=ROOT,
            seal_path=seal_path,
            policy=seal_tool.REGISTERED_SEAL_POLICY,
        )

    assert not os.path.lexists(seal_path)
    assert list(tmp_path.glob(".seal.json.staging-*")) == []


def test_link_error_uses_the_original_staging_identity_after_a_path_swap(
    tmp_path, monkeypatch
):
    seal_path = tmp_path / "seal.json"
    real_link = seal_tool.os.link
    real_unlink = seal_tool.os.unlink
    foreign = b"foreign replacement staging bytes\n"

    def link_swap_then_raise(source, destination, *, follow_symlinks=True):
        real_link(source, destination, follow_symlinks=follow_symlinks)
        real_unlink(source)
        Path(source).write_bytes(foreign)
        raise OSError("injected error after link and staging swap")

    monkeypatch.setattr(seal_tool.os, "link", link_swap_then_raise)

    with pytest.raises(
        seal_tool.IncidentSealError,
        match="unable to publish seal exclusively",
    ):
        seal_tool.create_data_integrity_incident_seal(
            repository=ROOT,
            seal_path=seal_path,
            policy=seal_tool.REGISTERED_SEAL_POLICY,
        )

    assert not os.path.lexists(seal_path)
    foreign_staging = list(tmp_path.glob(".seal.json.staging-*"))
    assert len(foreign_staging) == 1
    assert foreign_staging[0].read_bytes() == foreign


def test_successful_link_of_a_swapped_staging_file_leaves_no_formal_seal(
    tmp_path, monkeypatch
):
    seal_path = tmp_path / "seal.json"
    real_link = seal_tool.os.link
    real_unlink = seal_tool.os.unlink
    foreign = b"foreign replacement linked as the formal seal\n"

    def swap_then_link(source, destination, *, follow_symlinks=True):
        real_unlink(source)
        Path(source).write_bytes(foreign)
        real_link(source, destination, follow_symlinks=follow_symlinks)

    monkeypatch.setattr(seal_tool.os, "link", swap_then_link)

    with pytest.raises(seal_tool.IncidentSealError, match="ownership changed"):
        seal_tool.create_data_integrity_incident_seal(
            repository=ROOT,
            seal_path=seal_path,
            policy=seal_tool.REGISTERED_SEAL_POLICY,
        )

    assert not os.path.lexists(seal_path)
    foreign_staging = list(tmp_path.glob(".seal.json.staging-*"))
    assert len(foreign_staging) == 1
    assert foreign_staging[0].read_bytes() == foreign


def test_formal_seal_swap_during_staging_retirement_cannot_return_success(
    tmp_path, monkeypatch
):
    seal_path = tmp_path / "seal.json"
    real_unlink = seal_tool.os.unlink
    foreign = b"foreign formal seal installed during staging cleanup\n"

    def unlink_staging_then_swap_formal(path):
        if Path(path).name.startswith(".seal.json.staging-"):
            real_unlink(path)
            real_unlink(seal_path)
            seal_path.write_bytes(foreign)
            return None
        return real_unlink(path)

    monkeypatch.setattr(seal_tool.os, "unlink", unlink_staging_then_swap_formal)

    with pytest.raises(seal_tool.IncidentSealError, match="ownership changed"):
        seal_tool.create_data_integrity_incident_seal(
            repository=ROOT,
            seal_path=seal_path,
            policy=seal_tool.REGISTERED_SEAL_POLICY,
        )

    assert not os.path.lexists(seal_path)


def test_formal_seal_swap_during_final_byte_verification_cannot_return_success(
    tmp_path, monkeypatch
):
    seal_path = tmp_path / "seal.json"
    real_pread = seal_tool.os.pread
    real_unlink = seal_tool.os.unlink
    hash_starts = 0
    foreign = b"foreign formal seal installed during final verification\n"

    def swap_on_final_hash(descriptor, length, offset):
        nonlocal hash_starts
        if offset == 0:
            hash_starts += 1
            if hash_starts == 7:
                real_unlink(seal_path)
                seal_path.write_bytes(foreign)
        return real_pread(descriptor, length, offset)

    monkeypatch.setattr(seal_tool.os, "pread", swap_on_final_hash)

    with pytest.raises(seal_tool.IncidentSealError, match="ownership changed"):
        seal_tool.create_data_integrity_incident_seal(
            repository=ROOT,
            seal_path=seal_path,
            policy=seal_tool.REGISTERED_SEAL_POLICY,
        )

    assert not os.path.lexists(seal_path)


def test_partial_write_then_failure_leaves_no_final_or_staging_path(
    tmp_path, monkeypatch
):
    seal_path = tmp_path / "seal.json"
    real_fdopen = seal_tool.os.fdopen

    class PartialThenFail:
        def __init__(self, handle):
            self.handle = handle
            self.write_calls = 0

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.handle.close()

        def write(self, raw):
            self.write_calls += 1
            if self.write_calls == 1:
                return self.handle.write(raw[:17])
            raise OSError("injected write failure after a true partial write")

        def flush(self):
            return self.handle.flush()

        def fileno(self):
            return self.handle.fileno()

    monkeypatch.setattr(
        seal_tool.os,
        "fdopen",
        lambda descriptor, *args, **kwargs: PartialThenFail(
            real_fdopen(descriptor, *args, **kwargs)
        ),
    )

    with pytest.raises(seal_tool.IncidentSealError, match="durably write seal"):
        seal_tool.create_data_integrity_incident_seal(
            repository=ROOT,
            seal_path=seal_path,
            policy=seal_tool.REGISTERED_SEAL_POLICY,
        )

    assert not os.path.lexists(seal_path)
    assert list(tmp_path.glob(".seal.json.staging-*")) == []


def test_flush_failure_leaves_no_final_or_staging_path(tmp_path, monkeypatch):
    seal_path = tmp_path / "seal.json"
    real_fdopen = seal_tool.os.fdopen

    class FlushFailure:
        def __init__(self, handle):
            self.handle = handle

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.handle.close()

        def write(self, raw):
            return self.handle.write(raw)

        def flush(self):
            raise OSError("injected flush failure")

        def fileno(self):
            return self.handle.fileno()

    monkeypatch.setattr(
        seal_tool.os,
        "fdopen",
        lambda descriptor, *args, **kwargs: FlushFailure(
            real_fdopen(descriptor, *args, **kwargs)
        ),
    )

    with pytest.raises(seal_tool.IncidentSealError, match="durably write seal"):
        seal_tool.create_data_integrity_incident_seal(
            repository=ROOT,
            seal_path=seal_path,
            policy=seal_tool.REGISTERED_SEAL_POLICY,
        )

    assert not os.path.lexists(seal_path)
    assert list(tmp_path.glob(".seal.json.staging-*")) == []


def test_file_fsync_failure_leaves_no_final_or_staging_path(tmp_path, monkeypatch):
    seal_path = tmp_path / "seal.json"

    def fail_file_fsync(_descriptor):
        raise OSError("injected file fsync failure")

    monkeypatch.setattr(seal_tool.os, "fsync", fail_file_fsync)

    with pytest.raises(seal_tool.IncidentSealError, match="durably write seal"):
        seal_tool.create_data_integrity_incident_seal(
            repository=ROOT,
            seal_path=seal_path,
            policy=seal_tool.REGISTERED_SEAL_POLICY,
        )

    assert not os.path.lexists(seal_path)
    assert list(tmp_path.glob(".seal.json.staging-*")) == []


def test_staging_unlink_failure_archives_staging_and_rolls_back_final(
    tmp_path, monkeypatch
):
    seal_path = tmp_path / "seal.json"
    real_unlink = seal_tool.os.unlink

    def fail_staging_unlink(path):
        if Path(path).name.startswith(".seal.json.staging-"):
            raise OSError("injected staging unlink failure")
        return real_unlink(path)

    monkeypatch.setattr(seal_tool.os, "unlink", fail_staging_unlink)

    with pytest.raises(
        seal_tool.IncidentSealError,
        match="unable to retire seal staging path",
    ):
        seal_tool.create_data_integrity_incident_seal(
            repository=ROOT,
            seal_path=seal_path,
            policy=seal_tool.REGISTERED_SEAL_POLICY,
        )

    assert not os.path.lexists(seal_path)
    assert list(tmp_path.glob(".seal.json.staging-*")) == []
    archive_directories = list(tmp_path.glob(".*.failed-*"))
    assert len(archive_directories) == 2
    assert all(list(directory.iterdir()) for directory in archive_directories)


def test_parent_fsync_failure_rolls_back_the_published_final_path(
    tmp_path, monkeypatch
):
    seal_path = tmp_path / "seal.json"
    real_fsync = seal_tool.os.fsync
    calls = 0

    def fail_first_parent_fsync(descriptor):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected parent fsync failure")
        return real_fsync(descriptor)

    monkeypatch.setattr(seal_tool.os, "fsync", fail_first_parent_fsync)

    with pytest.raises(
        seal_tool.IncidentSealError,
        match="publication rolled back",
    ):
        seal_tool.create_data_integrity_incident_seal(
            repository=ROOT,
            seal_path=seal_path,
            policy=seal_tool.REGISTERED_SEAL_POLICY,
        )

    assert calls == 4
    assert not os.path.lexists(seal_path)
    assert list(tmp_path.glob(".seal.json.staging-*")) == []


def test_failed_archive_destination_fsync_is_reported_with_formal_path_empty(
    tmp_path, monkeypatch
):
    seal_path = tmp_path / "seal.json"
    real_fsync = seal_tool.os.fsync
    calls = 0

    def fail_publication_and_archive_destination_fsync(descriptor):
        nonlocal calls
        calls += 1
        if calls in {2, 3}:
            raise OSError("injected parent or archive fsync failure")
        return real_fsync(descriptor)

    monkeypatch.setattr(
        seal_tool.os,
        "fsync",
        fail_publication_and_archive_destination_fsync,
    )

    with pytest.raises(
        seal_tool.IncidentSealError,
        match="archive durability failed.*residual archived at",
    ):
        seal_tool.create_data_integrity_incident_seal(
            repository=ROOT,
            seal_path=seal_path,
            policy=seal_tool.REGISTERED_SEAL_POLICY,
        )

    assert not os.path.lexists(seal_path)
    archive_directories = list(tmp_path.glob(".seal.json.failed-*"))
    assert len(archive_directories) == 1
    assert (archive_directories[0] / "seal.json").is_file()


def test_rollback_rename_failure_uses_safe_fallback_archive_and_reports_its_path(
    tmp_path, monkeypatch
):
    seal_path = tmp_path / "seal.json"
    real_fsync = seal_tool.os.fsync
    real_rename = seal_tool.os.rename
    fsync_calls = 0
    formal_rename_calls = 0

    def fail_first_parent_fsync(descriptor):
        nonlocal fsync_calls
        fsync_calls += 1
        if fsync_calls == 2:
            raise OSError("injected parent fsync failure")
        return real_fsync(descriptor)

    def fail_first_formal_path_rename(source, destination):
        nonlocal formal_rename_calls
        if Path(source) == seal_path:
            formal_rename_calls += 1
            if formal_rename_calls == 1:
                raise OSError("injected rollback rename failure")
        return real_rename(source, destination)

    monkeypatch.setattr(seal_tool.os, "fsync", fail_first_parent_fsync)
    monkeypatch.setattr(seal_tool.os, "rename", fail_first_formal_path_rename)

    with pytest.raises(
        seal_tool.IncidentSealError,
        match="residual archived at",
    ):
        seal_tool.create_data_integrity_incident_seal(
            repository=ROOT,
            seal_path=seal_path,
            policy=seal_tool.REGISTERED_SEAL_POLICY,
        )

    assert not os.path.lexists(seal_path)
    assert list(tmp_path.glob(".seal.json.staging-*")) == []
    archive_directories = list(tmp_path.glob(".seal.json.failed-*"))
    assert len(archive_directories) == 1
    archived_seal = archive_directories[0] / "seal.json"
    assert archived_seal.is_file()
    assert sha256(archived_seal.read_bytes()).hexdigest() in archive_directories[0].name


def test_archive_fallback_unlink_failure_cannot_leave_the_formal_path(
    tmp_path, monkeypatch
):
    seal_path = tmp_path / "seal.json"
    real_fsync = seal_tool.os.fsync
    real_rename = seal_tool.os.rename
    real_unlink = seal_tool.os.unlink
    fsync_calls = 0

    def fail_publication_fsync(descriptor):
        nonlocal fsync_calls
        fsync_calls += 1
        if fsync_calls == 2:
            raise OSError("injected publication parent fsync failure")
        return real_fsync(descriptor)

    def fail_formal_rename(source, destination):
        if Path(source) == seal_path:
            raise OSError("injected primary archive rename failure")
        return real_rename(source, destination)

    def fail_formal_unlink(path):
        if Path(path) == seal_path:
            raise OSError("injected formal unlink failure")
        return real_unlink(path)

    monkeypatch.setattr(seal_tool.os, "fsync", fail_publication_fsync)
    monkeypatch.setattr(seal_tool.os, "rename", fail_formal_rename)
    monkeypatch.setattr(seal_tool.os, "unlink", fail_formal_unlink)

    with pytest.raises(seal_tool.IncidentSealError, match="publication rolled back"):
        seal_tool.create_data_integrity_incident_seal(
            repository=ROOT,
            seal_path=seal_path,
            policy=seal_tool.REGISTERED_SEAL_POLICY,
        )

    assert not os.path.lexists(seal_path)
    archive_directories = list(tmp_path.glob(".seal.json.failed-*"))
    assert len(archive_directories) == 1
    assert (archive_directories[0] / "seal.json").is_file()


def test_archive_rename_side_effect_then_error_preserves_the_owned_archive(
    tmp_path, monkeypatch
):
    seal_path = tmp_path / "seal.json"
    real_fsync = seal_tool.os.fsync
    real_rename = seal_tool.os.rename
    fsync_calls = 0

    def fail_publication_fsync(descriptor):
        nonlocal fsync_calls
        fsync_calls += 1
        if fsync_calls == 2:
            raise OSError("injected publication parent fsync failure")
        return real_fsync(descriptor)

    def rename_then_raise(source, destination):
        if Path(source) == seal_path:
            real_rename(source, destination)
            raise OSError("injected error after archive rename side effect")
        return real_rename(source, destination)

    monkeypatch.setattr(seal_tool.os, "fsync", fail_publication_fsync)
    monkeypatch.setattr(seal_tool.os, "rename", rename_then_raise)

    with pytest.raises(seal_tool.IncidentSealError, match="publication rolled back"):
        seal_tool.create_data_integrity_incident_seal(
            repository=ROOT,
            seal_path=seal_path,
            policy=seal_tool.REGISTERED_SEAL_POLICY,
        )

    assert not os.path.lexists(seal_path)
    archive_directories = list(tmp_path.glob(".seal.json.failed-*"))
    assert len(archive_directories) == 1
    archived = archive_directories[0] / "seal.json"
    assert archived.is_file()
    assert sha256(archived.read_bytes()).hexdigest() in archive_directories[0].name


def test_archive_replace_side_effect_then_error_preserves_the_owned_archive(
    tmp_path, monkeypatch
):
    seal_path = tmp_path / "seal.json"
    real_fsync = seal_tool.os.fsync
    real_rename = seal_tool.os.rename
    real_replace = seal_tool.os.replace
    fsync_calls = 0

    def fail_publication_fsync(descriptor):
        nonlocal fsync_calls
        fsync_calls += 1
        if fsync_calls == 2:
            raise OSError("injected publication parent fsync failure")
        return real_fsync(descriptor)

    def fail_formal_rename(source, destination):
        if Path(source) == seal_path:
            raise OSError("injected primary archive rename failure")
        return real_rename(source, destination)

    def replace_then_raise(source, destination):
        if Path(source) == seal_path:
            real_replace(source, destination)
            raise OSError("injected error after archive replace side effect")
        return real_replace(source, destination)

    monkeypatch.setattr(seal_tool.os, "fsync", fail_publication_fsync)
    monkeypatch.setattr(seal_tool.os, "rename", fail_formal_rename)
    monkeypatch.setattr(seal_tool.os, "replace", replace_then_raise)

    with pytest.raises(seal_tool.IncidentSealError, match="publication rolled back"):
        seal_tool.create_data_integrity_incident_seal(
            repository=ROOT,
            seal_path=seal_path,
            policy=seal_tool.REGISTERED_SEAL_POLICY,
        )

    assert not os.path.lexists(seal_path)
    archive_directories = list(tmp_path.glob(".seal.json.failed-*"))
    assert len(archive_directories) == 1
    archived = archive_directories[0] / "seal.json"
    assert archived.is_file()
    assert sha256(archived.read_bytes()).hexdigest() in archive_directories[0].name


def test_rollback_parent_fsync_failure_keeps_an_auditable_failed_archive(
    tmp_path, monkeypatch
):
    seal_path = tmp_path / "seal.json"
    real_fsync = seal_tool.os.fsync
    fsync_calls = 0

    def fail_publication_and_rollback_fsync(descriptor):
        nonlocal fsync_calls
        fsync_calls += 1
        if fsync_calls in {2, 4}:
            raise OSError("injected parent fsync failure")
        return real_fsync(descriptor)

    monkeypatch.setattr(
        seal_tool.os,
        "fsync",
        fail_publication_and_rollback_fsync,
    )

    with pytest.raises(
        seal_tool.IncidentSealError,
        match="source-parent durability failed.*residual archived at",
    ):
        seal_tool.create_data_integrity_incident_seal(
            repository=ROOT,
            seal_path=seal_path,
            policy=seal_tool.REGISTERED_SEAL_POLICY,
        )

    assert fsync_calls == 4
    assert not os.path.lexists(seal_path)
    assert list(tmp_path.glob(".seal.json.staging-*")) == []
    archive_directories = list(tmp_path.glob(".seal.json.failed-*"))
    assert len(archive_directories) == 1
    archived_seal = archive_directories[0] / "seal.json"
    assert archived_seal.is_file()
    assert sha256(archived_seal.read_bytes()).hexdigest() in archive_directories[0].name


@pytest.mark.parametrize(
    ("case", "mutate"),
    [
        (
            "status",
            lambda body: body.update(status="attacker-declared-sealed"),
        ),
        (
            "artifact commit",
            lambda body: body.update(
                artifact_commit="e585ae797ddcafa423121bf473d70b177a3bd92c"
            ),
        ),
        (
            "artifact path",
            lambda body: body["corrected_epoch"].update(
                path="data/processed/epochs/attacker/corrected_draws.csv"
            ),
        ),
        (
            "artifact blob",
            lambda body: body["artifacts"][
                "data/processed/epochs/DI-2026-08-20-registered-history/"
                "corrected_draws.csv"
            ].update(git_blob="0" * 40),
        ),
        (
            "artifact content",
            lambda body: body["artifacts"][
                "data/processed/epochs/DI-2026-08-20-registered-history/"
                "corrected_draws.csv"
            ].update(sha256="0" * 64),
        ),
        (
            "manifest external pin",
            lambda body: body["reconciliation_manifest"].update(
                manifest_sha256="0" * 64
            ),
        ),
        (
            "reconciliation count",
            lambda body: body["reconciliation_summary"].update(old_count=4_433),
        ),
        (
            "missing artifact",
            lambda body: body["artifacts"].pop(
                "evidence/data_integrity/DI-2026-08-20-registered-history/"
                "source-index.json"
            ),
        ),
        (
            "extra artifact",
            lambda body: body["artifacts"].update(
                {
                    "evidence/data_integrity/attacker.json": {
                        "git_blob": "0" * 40,
                        "bytes": 0,
                        "sha256": "0" * 64,
                    }
                }
            ),
        ),
    ],
)
def test_validator_rejects_coordinated_seal_and_self_hash_rewrites(
    tmp_path, case, mutate
):
    seal_path = tmp_path / "seal.json"
    payload = seal_tool.create_data_integrity_incident_seal(
        repository=ROOT,
        seal_path=seal_path,
        policy=seal_tool.REGISTERED_SEAL_POLICY,
    )
    rewritten = _coordinated_rewrite(payload, mutate)
    seal_path.write_bytes(rewritten)

    with pytest.raises(
        seal_tool.IncidentSealError,
        match="differs from immutable Git artifacts",
    ):
        seal_tool.validate_data_integrity_incident_seal(
            repository=ROOT,
            seal_path=seal_path,
            expected_seal_sha256=sha256(rewritten).hexdigest(),
            policy=seal_tool.REGISTERED_SEAL_POLICY,
        )


def test_validator_requires_the_caller_owned_whole_file_sha256(tmp_path):
    seal_path = tmp_path / "seal.json"
    seal_tool.create_data_integrity_incident_seal(
        repository=ROOT,
        seal_path=seal_path,
        policy=seal_tool.REGISTERED_SEAL_POLICY,
    )

    with pytest.raises(
        seal_tool.IncidentSealError,
        match="seal file external SHA-256 mismatch",
    ):
        seal_tool.validate_data_integrity_incident_seal(
            repository=ROOT,
            seal_path=seal_path,
            expected_seal_sha256="0" * 64,
            policy=seal_tool.REGISTERED_SEAL_POLICY,
        )


def test_validator_rejects_a_stale_body_hash_with_matching_whole_file_sha(tmp_path):
    seal_path = tmp_path / "seal.json"
    payload = seal_tool.create_data_integrity_incident_seal(
        repository=ROOT,
        seal_path=seal_path,
        policy=seal_tool.REGISTERED_SEAL_POLICY,
    )
    payload["status"] = "attacker-declared-sealed"
    rewritten = _canonical_json(payload) + b"\n"
    seal_path.write_bytes(rewritten)

    with pytest.raises(seal_tool.IncidentSealError, match="seal body SHA-256 mismatch"):
        seal_tool.validate_data_integrity_incident_seal(
            repository=ROOT,
            seal_path=seal_path,
            expected_seal_sha256=sha256(rewritten).hexdigest(),
            policy=seal_tool.REGISTERED_SEAL_POLICY,
        )


def test_validator_rejects_noncanonical_bytes_with_matching_whole_file_sha(tmp_path):
    seal_path = tmp_path / "seal.json"
    payload = seal_tool.create_data_integrity_incident_seal(
        repository=ROOT,
        seal_path=seal_path,
        policy=seal_tool.REGISTERED_SEAL_POLICY,
    )
    rewritten = (
        json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    ).encode()
    seal_path.write_bytes(rewritten)

    with pytest.raises(
        seal_tool.IncidentSealError,
        match="seal.json is not canonical finite JSON",
    ):
        seal_tool.validate_data_integrity_incident_seal(
            repository=ROOT,
            seal_path=seal_path,
            expected_seal_sha256=sha256(rewritten).hexdigest(),
            policy=seal_tool.REGISTERED_SEAL_POLICY,
        )


def test_validator_rejects_duplicate_json_keys_with_matching_whole_file_sha(tmp_path):
    seal_path = tmp_path / "seal.json"
    seal_tool.create_data_integrity_incident_seal(
        repository=ROOT,
        seal_path=seal_path,
        policy=seal_tool.REGISTERED_SEAL_POLICY,
    )
    raw = seal_path.read_bytes()
    needle = b'"status":"sealed_closed_corrected_epoch"'
    assert raw.count(needle) == 1
    rewritten = raw.replace(
        needle,
        b'"status":"attacker","status":"sealed_closed_corrected_epoch"',
        1,
    )
    seal_path.write_bytes(rewritten)

    with pytest.raises(
        seal_tool.IncidentSealError,
        match="JSON contains a duplicate key: status",
    ):
        seal_tool.validate_data_integrity_incident_seal(
            repository=ROOT,
            seal_path=seal_path,
            expected_seal_sha256=sha256(rewritten).hexdigest(),
            policy=seal_tool.REGISTERED_SEAL_POLICY,
        )


def test_validator_rejects_nan_with_matching_whole_file_sha(tmp_path):
    seal_path = tmp_path / "seal.json"
    seal_tool.create_data_integrity_incident_seal(
        repository=ROOT,
        seal_path=seal_path,
        policy=seal_tool.REGISTERED_SEAL_POLICY,
    )
    raw = seal_path.read_bytes()
    needle = b'"draw_count":4442'
    assert raw.count(needle) >= 1
    rewritten = raw.replace(needle, b'"draw_count":NaN', 1)
    seal_path.write_bytes(rewritten)

    with pytest.raises(
        seal_tool.IncidentSealError,
        match="JSON contains a non-finite number: NaN",
    ):
        seal_tool.validate_data_integrity_incident_seal(
            repository=ROOT,
            seal_path=seal_path,
            expected_seal_sha256=sha256(rewritten).hexdigest(),
            policy=seal_tool.REGISTERED_SEAL_POLICY,
        )


def test_dirty_worktree_artifacts_and_code_cannot_influence_the_git_seal(tmp_path):
    clean_seal_path = tmp_path / "clean-seal.json"
    seal_tool.create_data_integrity_incident_seal(
        repository=ROOT,
        seal_path=clean_seal_path,
        policy=seal_tool.REGISTERED_SEAL_POLICY,
    )

    dirty_repository = tmp_path / "dirty-repository"
    subprocess.run(
        [
            "git",
            "clone",
            "-q",
            "--shared",
            "--no-checkout",
            str(ROOT),
            str(dirty_repository),
        ],
        check=True,
        capture_output=True,
    )
    for relative_path in (
        "evidence/data_integrity/DI-2026-08-20-registered-history/incident.json",
        "data/processed/epochs/DI-2026-08-20-registered-history/corrected_draws.csv",
        "tools/build_data_integrity_incident.py",
    ):
        target = dirty_repository / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"attacker worktree bytes\n")

    dirty_seal_path = tmp_path / "dirty-seal.json"
    seal_tool.create_data_integrity_incident_seal(
        repository=dirty_repository,
        seal_path=dirty_seal_path,
        policy=seal_tool.REGISTERED_SEAL_POLICY,
    )

    clean_bytes = clean_seal_path.read_bytes()
    assert dirty_seal_path.read_bytes() == clean_bytes
    assert (
        seal_tool.validate_data_integrity_incident_seal(
            repository=dirty_repository,
            seal_path=dirty_seal_path,
            expected_seal_sha256=sha256(clean_bytes).hexdigest(),
            policy=seal_tool.REGISTERED_SEAL_POLICY,
        )["status"]
        == "sealed_closed_corrected_epoch"
    )


def test_creator_rejects_an_artifact_commit_with_any_other_path_set(tmp_path):
    repository = _shared_repository(tmp_path, "repository")
    attacker_commit = _commit_tree_edit(
        repository=repository,
        index_path=tmp_path / "attacker.index",
        base_tree=seal_tool.REGISTERED_SEAL_POLICY.artifact_commit,
        parent=seal_tool.REGISTERED_SEAL_POLICY.artifact_commit,
        relative_path="unexpected.txt",
        raw=b"not part of the artifact boundary\n",
        created_at="2026-08-21T00:00:00Z",
    )
    attacker_policy = replace(
        seal_tool.REGISTERED_SEAL_POLICY,
        artifact_commit=attacker_commit,
        artifact_parent=seal_tool.REGISTERED_SEAL_POLICY.artifact_commit,
        artifact_commit_created_at="2026-08-21T00:00:00Z",
    )

    with pytest.raises(
        seal_tool.IncidentSealError,
        match="artifact commit exact path set mismatch",
    ):
        seal_tool.create_data_integrity_incident_seal(
            repository=repository,
            seal_path=tmp_path / "seal.json",
            policy=attacker_policy,
        )


def test_creator_rejects_an_exact_path_commit_with_coordinated_manifest_rewrite(
    tmp_path,
):
    repository = _shared_repository(tmp_path, "repository")
    manifest_path = (
        "evidence/data_integrity/DI-2026-08-20-registered-history/"
        "reconciliation.manifest.json"
    )
    manifest = json.loads(
        subprocess.run(
            [
                "git",
                "-C",
                str(repository),
                "show",
                f"{seal_tool.REGISTERED_SEAL_POLICY.artifact_commit}:{manifest_path}",
            ],
            check=True,
            capture_output=True,
        ).stdout
    )
    manifest["summary"]["old_count"] = 4_433
    manifest_body = {
        key: value for key, value in manifest.items() if key != "manifest_sha256"
    }
    manifest["manifest_sha256"] = sha256(_canonical_json(manifest_body)).hexdigest()
    attacker_commit = _commit_tree_edit(
        repository=repository,
        index_path=tmp_path / "attacker.index",
        base_tree=seal_tool.REGISTERED_SEAL_POLICY.artifact_commit,
        parent=seal_tool.REGISTERED_SEAL_POLICY.artifact_parent,
        relative_path=manifest_path,
        raw=_canonical_json(manifest) + b"\n",
        created_at="2026-08-21T00:00:00Z",
    )
    attacker_policy = replace(
        seal_tool.REGISTERED_SEAL_POLICY,
        artifact_commit=attacker_commit,
        artifact_commit_created_at="2026-08-21T00:00:00Z",
    )

    with pytest.raises(
        seal_tool.IncidentSealError,
        match="reconciliation manifest external pin mismatch",
    ):
        seal_tool.create_data_integrity_incident_seal(
            repository=repository,
            seal_path=tmp_path / "seal.json",
            policy=attacker_policy,
        )


def test_creator_fails_closed_when_a_shallow_clone_lacks_the_parent_object(tmp_path):
    repository = _shared_repository(tmp_path, "shallow-repository")
    (repository / ".git" / "shallow").write_text(
        f"{seal_tool.REGISTERED_SEAL_POLICY.artifact_commit}\n"
    )
    visible_commit_line = subprocess.run(
        [
            "git",
            "-C",
            str(repository),
            "rev-list",
            "--parents",
            "-1",
            seal_tool.REGISTERED_SEAL_POLICY.artifact_commit,
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert visible_commit_line == seal_tool.REGISTERED_SEAL_POLICY.artifact_commit

    seal_path = tmp_path / "seal.json"
    with pytest.raises(
        seal_tool.IncidentSealError,
        match="artifact commit parent identity mismatch",
    ):
        seal_tool.create_data_integrity_incident_seal(
            repository=repository,
            seal_path=seal_path,
            policy=seal_tool.REGISTERED_SEAL_POLICY,
        )
    assert not os.path.lexists(seal_path)
