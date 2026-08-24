from __future__ import annotations

import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

import lotto649.history_publication_cas as publication_cas
from lotto649.history_publication import (
    PreparedPublication,
    RawSource,
    prepare_history_publication,
)
from lotto649.history_publication_cas import (
    CasAck,
    CasStatus,
    LocalBareHistoryRefStore,
    PreparationIntegrityError,
    PublicationConflict,
    PublicationIndeterminate,
    PublicationNotAdvanced,
    PublicationTransportError,
    PublishedReloadError,
    StalePublication,
    publish_prepared_history,
)

ROOT = Path(__file__).resolve().parents[1]


class _Store:
    def __init__(
        self,
        repository: Path,
        current: str,
        *,
        ack: CasAck | None = None,
        after: str | None = None,
    ) -> None:
        self.repository = repository
        self.current = current
        self.ack = ack or CasAck(CasStatus.APPLIED)
        self.after = after
        self.cas_calls: list[tuple[str, str]] = []

    def read(self) -> str:
        return self.current

    def compare_and_swap(self, expected: str, new: str) -> CasAck:
        self.cas_calls.append((expected, new))
        if self.after is not None:
            self.current = self.after
        return self.ack


class _AppliedThenRaisedStore(_Store):
    def compare_and_swap(self, expected: str, new: str) -> CasAck:
        self.cas_calls.append((expected, new))
        self.current = new
        raise PublicationTransportError("acknowledgement was lost")


class _AppliedThenArbitraryErrorStore(_Store):
    def __init__(
        self,
        repository: Path,
        current: str,
        error: Exception,
    ) -> None:
        super().__init__(repository, current)
        self.error = error

    def compare_and_swap(self, expected: str, new: str) -> CasAck:
        self.cas_calls.append((expected, new))
        self.current = new
        raise self.error


class _AppliedThenUnreadableStore(_AppliedThenArbitraryErrorStore):
    def __init__(self, repository: Path, current: str) -> None:
        super().__init__(
            repository,
            current,
            publication_cas.ReferenceIntegrityError("post-update read failed"),
        )
        self._reads = 0

    def read(self) -> str:
        self._reads += 1
        if self._reads > 1:
            raise publication_cas.ReferenceIntegrityError("post-update read failed")
        return super().read()


class _UnreadableAfterCasStore(_Store):
    def __init__(self, repository: Path, current: str) -> None:
        super().__init__(repository, current)
        self._reads = 0

    def read(self) -> str:
        self._reads += 1
        if self._reads > 1:
            raise OSError("authority unavailable")
        return super().read()


def _oid(character: str) -> str:
    return character * 40


class _DeceptiveOid(str):
    def __eq__(self, other: object) -> bool:
        return True

    def __ne__(self, other: object) -> bool:
        return False


class _DeceptiveDate(date):
    def __eq__(self, other: object) -> bool:
        return True

    def __ne__(self, other: object) -> bool:
        return False


class _PreparedSubclass(PreparedPublication):
    pass


def _prepared(tmp_path: Path) -> PreparedPublication:
    return PreparedPublication(
        repository=tmp_path,
        base_commit=_oid("1"),
        evidence_commit=_oid("2"),
        suffix_commit=_oid("3"),
        publication_commit=_oid("4"),
        target_draw_date=date(2026, 8, 26),
        suffix_head_event_sha256="5" * 64,
        registry_head_event_sha256="6" * 64,
    )


def _published(prepared: PreparedPublication):
    return SimpleNamespace(
        draws=(SimpleNamespace(draw_date=prepared.target_draw_date),),
        registry=SimpleNamespace(
            publication_commit=prepared.publication_commit,
            head_event_sha256=prepared.registry_head_event_sha256,
        ),
        registry_suffix=SimpleNamespace(
            head_event_sha256=prepared.suffix_head_event_sha256,
            history_through=prepared.target_draw_date,
        ),
        registry_transaction=SimpleNamespace(
            base_commit=prepared.base_commit,
            evidence_commit=prepared.evidence_commit,
            suffix_commit=prepared.suffix_commit,
        ),
    )


def test_invalid_candidate_is_rejected_before_cas(monkeypatch, tmp_path: Path):
    prepared = _prepared(tmp_path)
    store = _Store(
        prepared.repository,
        prepared.base_commit,
        after=prepared.publication_commit,
    )

    def reject_candidate(repository: Path, revision: str):
        raise ValueError("invalid candidate")

    monkeypatch.setattr(publication_cas, "load_published_history", reject_candidate)

    with pytest.raises(PreparationIntegrityError, match="candidate"):
        publish_prepared_history(prepared, store)

    assert store.cas_calls == []
    assert store.current == prepared.base_commit


def test_stale_initial_head_is_rejected_without_cas(monkeypatch, tmp_path: Path):
    prepared = _prepared(tmp_path)
    store = _Store(
        prepared.repository,
        _oid("7"),
        after=prepared.publication_commit,
    )
    monkeypatch.setattr(
        publication_cas,
        "load_published_history",
        lambda repository, revision: _published(prepared),
    )

    with pytest.raises(StalePublication) as raised:
        publish_prepared_history(prepared, store)

    assert raised.value.expected == prepared.base_commit
    assert raised.value.observed == _oid("7")
    assert store.cas_calls == []


def test_malformed_initial_authority_identity_is_an_integrity_error(
    monkeypatch, tmp_path: Path
):
    prepared = _prepared(tmp_path)
    store = _Store(prepared.repository, "not-an-oid")
    monkeypatch.setattr(
        publication_cas,
        "load_published_history",
        lambda repository, revision: _published(prepared),
    )

    with pytest.raises(publication_cas.ReferenceIntegrityError, match="authority ref"):
        publish_prepared_history(prepared, store)

    assert store.cas_calls == []


def test_authority_oid_must_be_an_exact_string(monkeypatch, tmp_path: Path):
    prepared = _prepared(tmp_path)
    store = _Store(
        prepared.repository,
        _DeceptiveOid(prepared.base_commit),
    )
    monkeypatch.setattr(
        publication_cas,
        "load_published_history",
        lambda repository, revision: _published(prepared),
    )

    with pytest.raises(publication_cas.ReferenceIntegrityError, match="authority ref"):
        publish_prepared_history(prepared, store)

    assert store.cas_calls == []


def test_prepared_candidate_must_use_the_exact_public_type(monkeypatch, tmp_path: Path):
    valid = _prepared(tmp_path)
    prepared = _PreparedSubclass(
        repository=valid.repository,
        base_commit=valid.base_commit,
        evidence_commit=valid.evidence_commit,
        suffix_commit=valid.suffix_commit,
        publication_commit=valid.publication_commit,
        target_draw_date=valid.target_draw_date,
        suffix_head_event_sha256=valid.suffix_head_event_sha256,
        registry_head_event_sha256=valid.registry_head_event_sha256,
    )
    store = _Store(
        prepared.repository,
        prepared.base_commit,
        after=prepared.publication_commit,
    )
    monkeypatch.setattr(
        publication_cas,
        "load_published_history",
        lambda repository, revision: _published(valid),
    )

    with pytest.raises(PreparationIntegrityError, match="candidate type"):
        publish_prepared_history(prepared, store)

    assert store.cas_calls == []


def test_prepared_target_date_must_be_an_exact_date(monkeypatch, tmp_path: Path):
    valid = _prepared(tmp_path)
    prepared = PreparedPublication(
        repository=valid.repository,
        base_commit=valid.base_commit,
        evidence_commit=valid.evidence_commit,
        suffix_commit=valid.suffix_commit,
        publication_commit=valid.publication_commit,
        target_draw_date=_DeceptiveDate(2099, 1, 1),
        suffix_head_event_sha256=valid.suffix_head_event_sha256,
        registry_head_event_sha256=valid.registry_head_event_sha256,
    )
    store = _Store(
        prepared.repository,
        prepared.base_commit,
        after=prepared.publication_commit,
    )
    monkeypatch.setattr(
        publication_cas,
        "load_published_history",
        lambda repository, revision: _published(valid),
    )

    with pytest.raises(PreparationIntegrityError, match="target date"):
        publish_prepared_history(prepared, store)

    assert store.cas_calls == []


@pytest.mark.parametrize("status", [CasStatus.REJECTED, CasStatus.UNKNOWN])
def test_observed_candidate_confirms_ambiguous_or_rejected_ack(
    monkeypatch, tmp_path: Path, status: CasStatus
):
    prepared = _prepared(tmp_path)
    store = _Store(
        prepared.repository,
        prepared.base_commit,
        ack=CasAck(status),
        after=prepared.publication_commit,
    )
    loads: list[str] = []

    def load(repository: Path, revision: str):
        loads.append(revision)
        return _published(prepared)

    monkeypatch.setattr(publication_cas, "load_published_history", load)

    receipt = publish_prepared_history(prepared, store)

    assert receipt.outcome == "confirmed_after_reread"
    assert receipt.expected_base == prepared.base_commit
    assert receipt.publication_commit == prepared.publication_commit
    assert receipt.observed_after == prepared.publication_commit
    assert receipt.history is not None
    assert loads == [prepared.publication_commit, prepared.publication_commit]


def test_applied_ack_returns_only_after_authority_reload(monkeypatch, tmp_path: Path):
    prepared = _prepared(tmp_path)
    store = _Store(
        prepared.repository,
        prepared.base_commit,
        after=prepared.publication_commit,
    )
    loads: list[str] = []

    def load(repository: Path, revision: str):
        loads.append(revision)
        return _published(prepared)

    monkeypatch.setattr(publication_cas, "load_published_history", load)

    receipt = publish_prepared_history(prepared, store)

    assert receipt.outcome == "advanced"
    assert loads == [prepared.publication_commit, prepared.publication_commit]


def test_applied_then_raised_ack_is_confirmed_only_by_reread(
    monkeypatch, tmp_path: Path
):
    prepared = _prepared(tmp_path)
    store = _AppliedThenRaisedStore(prepared.repository, prepared.base_commit)
    monkeypatch.setattr(
        publication_cas,
        "load_published_history",
        lambda repository, revision: _published(prepared),
    )

    receipt = publish_prepared_history(prepared, store)

    assert receipt.outcome == "confirmed_after_reread"
    assert receipt.cas_ack == CasAck(CasStatus.UNKNOWN)
    assert store.current == prepared.publication_commit


@pytest.mark.parametrize(
    "error",
    [
        OSError("transport failed after update"),
        publication_cas.ReferenceIntegrityError("read failed after update"),
    ],
)
def test_any_exception_after_cas_attempt_is_reconciled_by_reread(
    monkeypatch, tmp_path: Path, error: Exception
):
    prepared = _prepared(tmp_path)
    store = _AppliedThenArbitraryErrorStore(
        prepared.repository,
        prepared.base_commit,
        error,
    )
    monkeypatch.setattr(
        publication_cas,
        "load_published_history",
        lambda repository, revision: _published(prepared),
    )

    receipt = publish_prepared_history(prepared, store)

    assert receipt.outcome == "confirmed_after_reread"
    assert receipt.cas_ack == CasAck(CasStatus.UNKNOWN)
    assert store.current == prepared.publication_commit


def test_exception_after_update_and_failed_reread_is_indeterminate(
    monkeypatch, tmp_path: Path
):
    prepared = _prepared(tmp_path)
    store = _AppliedThenUnreadableStore(prepared.repository, prepared.base_commit)
    monkeypatch.setattr(
        publication_cas,
        "load_published_history",
        lambda repository, revision: _published(prepared),
    )

    with pytest.raises(PublicationIndeterminate) as raised:
        publish_prepared_history(prepared, store)

    assert raised.value.last_observed is None


def test_candidate_already_at_authority_is_idempotently_reloaded(
    monkeypatch, tmp_path: Path
):
    prepared = _prepared(tmp_path)
    store = _Store(prepared.repository, prepared.publication_commit)
    loads: list[str] = []

    def load(repository: Path, revision: str):
        loads.append(revision)
        return _published(prepared)

    monkeypatch.setattr(publication_cas, "load_published_history", load)

    receipt = publish_prepared_history(prepared, store)

    assert receipt.outcome == "already_published"
    assert receipt.cas_ack is None
    assert store.cas_calls == []
    assert loads == [prepared.publication_commit, prepared.publication_commit]


def test_unknown_ack_with_unchanged_head_is_not_success(monkeypatch, tmp_path: Path):
    prepared = _prepared(tmp_path)
    store = _Store(
        prepared.repository,
        prepared.base_commit,
        ack=CasAck(CasStatus.UNKNOWN),
        after=prepared.base_commit,
    )
    monkeypatch.setattr(
        publication_cas,
        "load_published_history",
        lambda repository, revision: _published(prepared),
    )

    with pytest.raises(PublicationNotAdvanced) as raised:
        publish_prepared_history(prepared, store)

    assert raised.value.expected == prepared.base_commit
    assert raised.value.ack.status is CasStatus.UNKNOWN


def test_third_head_after_cas_is_a_conflict(monkeypatch, tmp_path: Path):
    prepared = _prepared(tmp_path)
    third = _oid("8")
    store = _Store(
        prepared.repository,
        prepared.base_commit,
        ack=CasAck(CasStatus.REJECTED),
        after=third,
    )
    monkeypatch.setattr(
        publication_cas,
        "load_published_history",
        lambda repository, revision: _published(prepared),
    )

    with pytest.raises(PublicationConflict) as raised:
        publish_prepared_history(prepared, store)

    assert raised.value.expected == prepared.base_commit
    assert raised.value.candidate == prepared.publication_commit
    assert raised.value.observed == third


def test_malformed_authority_identity_after_cas_is_indeterminate(
    monkeypatch, tmp_path: Path
):
    prepared = _prepared(tmp_path)
    store = _Store(
        prepared.repository,
        prepared.base_commit,
        ack=CasAck(CasStatus.UNKNOWN),
        after="not-an-oid",
    )
    monkeypatch.setattr(
        publication_cas,
        "load_published_history",
        lambda repository, revision: _published(prepared),
    )

    with pytest.raises(PublicationIndeterminate) as raised:
        publish_prepared_history(prepared, store)

    assert raised.value.last_observed is None


def test_unreadable_authority_after_cas_is_indeterminate(monkeypatch, tmp_path: Path):
    prepared = _prepared(tmp_path)
    store = _UnreadableAfterCasStore(prepared.repository, prepared.base_commit)
    monkeypatch.setattr(
        publication_cas,
        "load_published_history",
        lambda repository, revision: _published(prepared),
    )

    with pytest.raises(PublicationIndeterminate) as raised:
        publish_prepared_history(prepared, store)

    assert raised.value.last_observed is None


def test_prepared_repository_must_be_the_authority_object_store(
    monkeypatch, tmp_path: Path
):
    prepared = _prepared(tmp_path)
    other = tmp_path / "other"
    other.mkdir()
    store = _Store(other, prepared.base_commit)
    loads: list[str] = []
    monkeypatch.setattr(
        publication_cas,
        "load_published_history",
        lambda repository, revision: loads.append(revision),
    )

    with pytest.raises(PreparationIntegrityError, match="object store"):
        publish_prepared_history(prepared, store)

    assert loads == []
    assert store.cas_calls == []


def test_candidate_transaction_identity_mismatch_never_calls_cas(
    monkeypatch, tmp_path: Path
):
    prepared = _prepared(tmp_path)
    store = _Store(prepared.repository, prepared.base_commit)
    invalid = _published(prepared)
    invalid.registry_transaction.base_commit = _oid("9")
    monkeypatch.setattr(
        publication_cas,
        "load_published_history",
        lambda repository, revision: invalid,
    )

    with pytest.raises(PreparationIntegrityError, match="B/E/S/P"):
        publish_prepared_history(prepared, store)

    assert store.cas_calls == []


def test_post_cas_reload_failure_is_not_reported_as_success(
    monkeypatch, tmp_path: Path
):
    prepared = _prepared(tmp_path)
    store = _Store(
        prepared.repository,
        prepared.base_commit,
        after=prepared.publication_commit,
    )
    calls = 0

    def load(repository: Path, revision: str):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise ValueError("authority reload failed")
        return _published(prepared)

    monkeypatch.setattr(publication_cas, "load_published_history", load)

    with pytest.raises(PublishedReloadError, match="reload"):
        publish_prepared_history(prepared, store)

    assert store.current == prepared.publication_commit


def _git(repository: Path, *arguments: str, input_bytes: bytes | None = None) -> bytes:
    return subprocess.run(
        ["git", "-C", str(repository), *arguments],
        input=input_bytes,
        check=True,
        capture_output=True,
    ).stdout


def _commit(repository: Path, tree: str, *, parent: str | None, message: str) -> str:
    arguments = ["commit-tree", tree]
    if parent is not None:
        arguments.extend(["-p", parent])
    environment = {
        **os.environ,
        "GIT_AUTHOR_NAME": "History Test",
        "GIT_AUTHOR_EMAIL": "history@example.invalid",
        "GIT_AUTHOR_DATE": "2026-08-27T12:00:00Z",
        "GIT_COMMITTER_NAME": "History Test",
        "GIT_COMMITTER_EMAIL": "history@example.invalid",
        "GIT_COMMITTER_DATE": "2026-08-27T12:00:00Z",
    }
    return (
        subprocess.run(
            ["git", "-C", str(repository), *arguments],
            input=(message + "\n").encode(),
            check=True,
            capture_output=True,
            env=environment,
        )
        .stdout.decode()
        .strip()
    )


def _bare_graph(tmp_path: Path) -> tuple[Path, str, str, str, str]:
    repository = tmp_path / "authority.git"
    subprocess.run(
        ["git", "init", "--bare", "--quiet", str(repository)],
        check=True,
        capture_output=True,
    )
    tree = _git(repository, "mktree", input_bytes=b"").decode().strip()
    base = _commit(repository, tree, parent=None, message="base")
    first = _commit(repository, tree, parent=base, message="first")
    second = _commit(repository, tree, parent=base, message="second")
    unrelated = _commit(repository, tree, parent=None, message="unrelated")
    _git(repository, "update-ref", "refs/heads/main", base)
    _git(repository, "symbolic-ref", "HEAD", "refs/heads/main")
    return repository, base, first, second, unrelated


def test_local_ref_store_compare_and_swap_allows_only_one_concurrent_writer(
    tmp_path: Path,
):
    repository, base, first, second, _ = _bare_graph(tmp_path)
    store = LocalBareHistoryRefStore(repository)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                lambda candidate: store.compare_and_swap(base, candidate),
                (first, second),
            )
        )

    assert sorted(result.status.value for result in results) == [
        "applied",
        "rejected",
    ]
    assert store.read() in {first, second}


def test_local_ref_store_rejects_non_fast_forward_candidate(tmp_path: Path):
    repository, base, _, _, unrelated = _bare_graph(tmp_path)
    store = LocalBareHistoryRefStore(repository)

    with pytest.raises(PreparationIntegrityError, match="fast-forward"):
        store.compare_and_swap(base, unrelated)

    assert store.read() == base


def test_local_ref_store_ignores_hostile_git_environment(monkeypatch, tmp_path: Path):
    repository, base, _, _, _ = _bare_graph(tmp_path)
    hostile = tmp_path / "hostile.git"
    subprocess.run(
        ["git", "init", "--bare", "--quiet", str(hostile)],
        check=True,
        capture_output=True,
    )
    monkeypatch.setenv("GIT_DIR", str(hostile))
    monkeypatch.setenv("GIT_OBJECT_DIRECTORY", str(hostile / "objects"))
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(tmp_path / "foreign-config"))

    store = LocalBareHistoryRefStore(repository)

    assert store.read() == base


def test_local_ref_store_rejects_symbolic_main(tmp_path: Path):
    repository, base, _, _, _ = _bare_graph(tmp_path)
    _git(repository, "update-ref", "refs/heads/actual", base)
    _git(repository, "symbolic-ref", "refs/heads/main", "refs/heads/actual")

    with pytest.raises(publication_cas.ReferenceIntegrityError, match="HEAD.*main"):
        LocalBareHistoryRefStore(repository)


def test_local_ref_store_requires_literal_head_to_be_main(tmp_path: Path):
    repository, base, _, _, _ = _bare_graph(tmp_path)
    _git(repository, "update-ref", "refs/heads/feature", base)
    _git(repository, "symbolic-ref", "HEAD", "refs/heads/feature")

    with pytest.raises(publication_cas.ReferenceIntegrityError, match="HEAD.*main"):
        LocalBareHistoryRefStore(repository)


@pytest.mark.parametrize("alternate_name", ["alternates", "http-alternates"])
def test_local_ref_store_rejects_external_object_alternates(
    tmp_path: Path, alternate_name: str
):
    repository, _, _, _, _ = _bare_graph(tmp_path)
    alternate_file = repository / "objects" / "info" / alternate_name
    alternate_file.write_text("/external/object/store\n", encoding="utf-8")

    with pytest.raises(publication_cas.ReferenceIntegrityError, match="self-contained"):
        LocalBareHistoryRefStore(repository)


def test_local_ref_store_rejects_symlinked_object_store(tmp_path: Path):
    repository, _, _, _, _ = _bare_graph(tmp_path)
    external_objects = tmp_path / "external-objects"
    (repository / "objects").rename(external_objects)
    (repository / "objects").symlink_to(external_objects, target_is_directory=True)

    with pytest.raises(publication_cas.ReferenceIntegrityError, match="self-contained"):
        LocalBareHistoryRefStore(repository)


def test_local_ref_store_rejects_a_special_object_store_entry(tmp_path: Path):
    repository, base, _, _, _ = _bare_graph(tmp_path)
    tree = _git(repository, "rev-parse", f"{base}^{{tree}}").decode().strip()
    tree_path = repository / "objects" / tree[:2] / tree[2:]
    tree_path.unlink()
    os.mkfifo(tree_path)

    with pytest.raises(publication_cas.ReferenceIntegrityError, match="self-contained"):
        LocalBareHistoryRefStore(repository)


def test_local_ref_store_rejects_external_git_common_directory(tmp_path: Path):
    common, base, _, _, _ = _bare_graph(tmp_path)
    wrapper = tmp_path / "wrapper.git"
    (wrapper / "objects").mkdir(parents=True)
    (wrapper / "refs").mkdir()
    (wrapper / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (wrapper / "config").write_text(
        "[core]\n\trepositoryformatversion = 0\n\tbare = true\n",
        encoding="utf-8",
    )
    (wrapper / "commondir").write_text(f"{common}\n", encoding="utf-8")
    common_main_before = _git(common, "show-ref", "--hash", "refs/heads/main")
    assert common_main_before.decode().strip() == base
    assert _git(wrapper, "rev-parse", "--git-common-dir").decode().strip() == str(
        common
    )

    with pytest.raises(
        publication_cas.ReferenceIntegrityError,
        match="object store must be self-contained",
    ):
        LocalBareHistoryRefStore(wrapper)

    assert _git(common, "show-ref", "--hash", "refs/heads/main") == common_main_before


def test_local_ref_store_rejects_symlinked_authority_ref(tmp_path: Path):
    repository, base, _, _, _ = _bare_graph(tmp_path)
    external_main = tmp_path / "external-main"
    external_main.write_text(f"{base}\n", encoding="ascii")
    main_ref = repository / "refs" / "heads" / "main"
    main_ref.unlink()
    main_ref.symlink_to(external_main)

    with pytest.raises(publication_cas.ReferenceIntegrityError, match="self-contained"):
        LocalBareHistoryRefStore(repository)

    assert external_main.read_text(encoding="ascii") == f"{base}\n"


def test_local_ref_store_rejects_external_repository_config(tmp_path: Path):
    repository, _, _, _, _ = _bare_graph(tmp_path)
    external_config = tmp_path / "external-config"
    (repository / "config").rename(external_config)
    (repository / "config").symlink_to(external_config)

    with pytest.raises(publication_cas.ReferenceIntegrityError, match="self-contained"):
        LocalBareHistoryRefStore(repository)


def test_local_ref_store_rejects_external_config_includes(tmp_path: Path):
    repository, _, _, _, _ = _bare_graph(tmp_path)
    external_config = tmp_path / "included-config"
    external_config.write_text("[core]\n\tlogAllRefUpdates = false\n", encoding="utf-8")
    _git(repository, "config", "--add", "include.path", str(external_config))

    with pytest.raises(publication_cas.ReferenceIntegrityError, match="self-contained"):
        LocalBareHistoryRefStore(repository)


def test_local_ref_store_rejects_conditional_external_config_includes(
    tmp_path: Path,
):
    repository, _, _, _, _ = _bare_graph(tmp_path)
    external_config = tmp_path / "included-config"
    external_config.write_text("[core]\n\tlogAllRefUpdates = false\n", encoding="utf-8")
    local_config = repository / "config"
    local_config.write_text(
        local_config.read_text(encoding="utf-8")
        + f'\n[includeIf "gitdir:**"]\n\tpath = {external_config}\n',
        encoding="utf-8",
    )

    with pytest.raises(publication_cas.ReferenceIntegrityError, match="self-contained"):
        LocalBareHistoryRefStore(repository)


def test_local_ref_store_rejects_repository_fsck_policy_overrides(tmp_path: Path):
    repository, _, _, _, _ = _bare_graph(tmp_path)
    external_skip_list = tmp_path / "external-skip-list"
    external_skip_list.write_bytes(b"")
    _git(repository, "config", "fsck.skipList", str(external_skip_list))

    with pytest.raises(publication_cas.ReferenceIntegrityError, match="self-contained"):
        LocalBareHistoryRefStore(repository)


@pytest.mark.parametrize(
    "config_key",
    ["core.filesRefLockTimeout", "core.packedRefsTimeout"],
)
def test_local_ref_store_rejects_repository_ref_lock_policy_overrides(
    tmp_path: Path,
    config_key: str,
):
    repository, _, _, _, _ = _bare_graph(tmp_path)
    _git(repository, "config", config_key, "-1")

    with pytest.raises(publication_cas.ReferenceIntegrityError, match="self-contained"):
        LocalBareHistoryRefStore(repository)


@pytest.mark.parametrize(
    ("config_key", "config_value"),
    [
        ("extensions.partialClone", "origin"),
        ("remote.origin.promisor", "true"),
        ("remote.origin.partialCloneFilter", "blob:none"),
    ],
)
def test_local_ref_store_rejects_worktree_scoped_partial_clone_markers(
    tmp_path: Path,
    config_key: str,
    config_value: str,
):
    repository, _, _, _, _ = _bare_graph(tmp_path)
    _git(repository, "config", "extensions.worktreeConfig", "true")
    _git(repository, "config", "--worktree", config_key, config_value)

    with pytest.raises(publication_cas.ReferenceIntegrityError, match="complete"):
        LocalBareHistoryRefStore(repository)


def test_local_ref_store_rejects_external_shallow_marker(tmp_path: Path):
    repository, _, _, _, _ = _bare_graph(tmp_path)
    (repository / "shallow").symlink_to(tmp_path / "external-shallow")

    with pytest.raises(publication_cas.ReferenceIntegrityError, match="self-contained"):
        LocalBareHistoryRefStore(repository)


def test_local_ref_store_rejects_external_reflog(tmp_path: Path):
    repository, _, _, _, _ = _bare_graph(tmp_path)
    _git(repository, "config", "core.logAllRefUpdates", "true")
    external_log = tmp_path / "external-main.log"
    external_log.write_bytes(b"")
    log_path = repository / "logs" / "refs" / "heads" / "main"
    log_path.parent.mkdir(parents=True)
    log_path.symlink_to(external_log)

    with pytest.raises(publication_cas.ReferenceIntegrityError, match="self-contained"):
        LocalBareHistoryRefStore(repository)

    assert external_log.read_bytes() == b""


@pytest.mark.parametrize("externalize", [False, True])
def test_local_ref_store_rejects_reftable_authority(tmp_path: Path, externalize: bool):
    repository = tmp_path / "reftable.git"
    initialized = subprocess.run(
        [
            "git",
            "init",
            "--bare",
            "--quiet",
            "--ref-format=reftable",
            str(repository),
        ],
        check=False,
        capture_output=True,
    )
    if initialized.returncode != 0:
        pytest.skip("installed Git does not support the reftable backend")
    tree = _git(repository, "mktree", input_bytes=b"").decode().strip()
    base = _commit(repository, tree, parent=None, message="base")
    _git(repository, "update-ref", "refs/heads/main", base)
    _git(repository, "symbolic-ref", "HEAD", "refs/heads/main")
    assert _git(repository, "rev-parse", "--show-ref-format") == b"reftable\n"
    if externalize:
        external_reftable = tmp_path / "external-reftable"
        (repository / "reftable").rename(external_reftable)
        (repository / "reftable").symlink_to(
            external_reftable,
            target_is_directory=True,
        )

    with pytest.raises(publication_cas.ReferenceIntegrityError, match="self-contained"):
        LocalBareHistoryRefStore(repository)


@pytest.mark.parametrize("marker", ["config", "pack-file"])
def test_local_ref_store_rejects_promisor_object_stores(tmp_path: Path, marker: str):
    repository, _, _, _, _ = _bare_graph(tmp_path)
    if marker == "config":
        _git(repository, "config", "remote.origin.promisor", "true")
    else:
        (repository / "objects" / "pack" / "fake.promisor").write_bytes(b"")

    with pytest.raises(publication_cas.ReferenceIntegrityError, match="complete"):
        LocalBareHistoryRefStore(repository)


def test_local_ref_store_rejects_a_missing_reachable_object(tmp_path: Path):
    repository, base, _, _, _ = _bare_graph(tmp_path)
    tree = _git(repository, "rev-parse", f"{base}^{{tree}}").decode().strip()
    tree_path = repository / "objects" / tree[:2] / tree[2:]
    assert tree_path.is_file()
    tree_path.rename(tmp_path / "missing-tree-object")

    with pytest.raises(publication_cas.ReferenceIntegrityError, match="complete"):
        LocalBareHistoryRefStore(repository)


def test_local_ref_store_rejects_a_corrupt_reachable_object(tmp_path: Path):
    repository, base, _, _, _ = _bare_graph(tmp_path)
    tree = _git(repository, "rev-parse", f"{base}^{{tree}}").decode().strip()
    tree_path = repository / "objects" / tree[:2] / tree[2:]
    tree_path.unlink()
    tree_path.write_bytes(b"")

    with pytest.raises(publication_cas.ReferenceIntegrityError, match="complete"):
        LocalBareHistoryRefStore(repository)


def test_prepare_and_local_cas_publish_one_reader_verified_history(tmp_path: Path):
    repository = tmp_path / "authority.git"
    subprocess.run(
        [
            "git",
            "clone",
            "--bare",
            "--no-local",
            "--quiet",
            str(ROOT),
            str(repository),
        ],
        check=True,
        capture_output=True,
    )
    base_commit = _git(repository, "rev-parse", "HEAD").decode().strip()
    _git(repository, "update-ref", "refs/heads/main", base_commit)
    _git(repository, "symbolic-ref", "HEAD", "refs/heads/main")
    wclc_raw = (
        b"<!doctype html><html><body>Wednesday, August 26, 2026 "
        b"CLASSIC DRAW 02 07 18 23 35 49 Bonus 11</body></html>"
    )
    loto_quebec_raw = (
        b"<!doctype html><html><body>"
        b'<span id="dateAffichee">2026-08-26</span>'
        b'<div class="lqZoneProduit principal lotto-6-49">'
        b'<div class="numeros tirageClassique">'
        b'<span class="num">02</span><span class="num">07</span>'
        b'<span class="num">18</span><span class="num">23</span>'
        b'<span class="num">35</span><span class="num">49</span>'
        b'<span class="num complementaire">11</span>'
        b"</div></div></body></html>"
    )
    prepared = prepare_history_publication(
        repository,
        expected_base_commit=base_commit,
        sources=(
            RawSource(
                authority="wclc",
                url="https://www.wclc.com/winning-numbers/lotto-649-extra.htm",
                retrieved_at=datetime(2026, 8, 27, 12, 0, tzinfo=UTC),
                raw=wclc_raw,
            ),
            RawSource(
                authority="loto_quebec",
                url=(
                    "https://loteries.lotoquebec.com/en/lotteries/"
                    "lotto-6-49-resultats?date=2026-08-26"
                ),
                retrieved_at=datetime(2026, 8, 27, 12, 0, 1, tzinfo=UTC),
                raw=loto_quebec_raw,
            ),
        ),
        created_at=datetime(2026, 8, 27, 12, 5, tzinfo=UTC),
    )
    store = LocalBareHistoryRefStore(repository)

    receipt = publish_prepared_history(prepared, store)

    assert receipt.outcome == "advanced"
    assert store.read() == prepared.publication_commit
    assert _git(repository, "rev-parse", "HEAD").decode().strip() == (
        prepared.publication_commit
    )
    assert receipt.history.registry.publication_commit == prepared.publication_commit
    assert len(receipt.history.draws) == 4_445
    assert receipt.history.draws[-1].draw_date == date(2026, 8, 26)
