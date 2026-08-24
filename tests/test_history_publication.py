from __future__ import annotations

import json
import subprocess
from collections.abc import Iterator, Sequence
from datetime import UTC, date, datetime, tzinfo
from hashlib import sha256
from pathlib import Path
from typing import cast

import pytest

from lotto649 import history_publication
from lotto649.history_publication import (
    HistoryPublicationError,
    PreparedPublication,
    RawSource,
    prepare_history_publication,
)
from lotto649.operational_history import load_published_history

ROOT = Path(__file__).resolve().parents[1]
SUFFIX_PATH = "data/processed/epochs/DI-2026-08-20-registered-history/live_draws.jsonl"
REGISTRY_PATH = (
    "evidence/operational_history/DI-2026-08-20-registered-history/pin-registry.jsonl"
)


def _git(repository: Path, *arguments: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
    ).stdout


def _git_text(repository: Path, *arguments: str) -> str:
    return _git(repository, *arguments).decode("utf-8").strip()


def _clone_repository(tmp_path: Path) -> Path:
    repository = tmp_path / "repository"
    subprocess.run(
        ["git", "clone", "--no-local", "--quiet", str(ROOT), str(repository)],
        check=True,
        capture_output=True,
    )
    return repository


def _clone_bare_repository(tmp_path: Path) -> Path:
    repository = tmp_path / "repository.git"
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
    return repository


def _wclc_html() -> bytes:
    return (
        b"<!doctype html><html><body>Wednesday, August 26, 2026 "
        b"CLASSIC DRAW 02 07 18 23 35 49 Bonus 11</body></html>"
    )


def _loto_quebec_html() -> bytes:
    return (
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


def _sources() -> tuple[RawSource, RawSource]:
    return (
        RawSource(
            authority="wclc",
            url="https://www.wclc.com/winning-numbers/lotto-649-extra.htm",
            retrieved_at=datetime(2026, 8, 27, 12, 0, tzinfo=UTC),
            raw=_wclc_html(),
        ),
        RawSource(
            authority="loto_quebec",
            url=(
                "https://loteries.lotoquebec.com/en/lotteries/"
                "lotto-6-49-resultats?date=2026-08-26"
            ),
            retrieved_at=datetime(2026, 8, 27, 12, 0, 1, tzinfo=UTC),
            raw=_loto_quebec_html(),
        ),
    )


def _second_sources() -> tuple[RawSource, RawSource]:
    return (
        RawSource(
            authority="wclc",
            url="https://www.wclc.com/winning-numbers/lotto-649-extra.htm",
            retrieved_at=datetime(2026, 8, 30, 12, 0, tzinfo=UTC),
            raw=(
                b"<!doctype html><html><body>Saturday, August 29, 2026 "
                b"CLASSIC DRAW 01 09 17 28 34 46 Bonus 12</body></html>"
            ),
        ),
        RawSource(
            authority="loto_quebec",
            url=(
                "https://loteries.lotoquebec.com/en/lotteries/"
                "lotto-6-49-resultats?date=2026-08-29"
            ),
            retrieved_at=datetime(2026, 8, 30, 12, 0, 1, tzinfo=UTC),
            raw=(
                b"<!doctype html><html><body>"
                b'<span id="dateAffichee">2026-08-29</span>'
                b'<div class="lqZoneProduit principal lotto-6-49">'
                b'<div class="numeros tirageClassique">'
                b'<span class="num">01</span><span class="num">09</span>'
                b'<span class="num">17</span><span class="num">28</span>'
                b'<span class="num">34</span><span class="num">46</span>'
                b'<span class="num complementaire">12</span>'
                b"</div></div></body></html>"
            ),
        ),
    )


def _repository_state(repository: Path) -> tuple[str, str, bytes, str, bytes]:
    return (
        _git_text(repository, "rev-parse", "HEAD"),
        _git_text(repository, "symbolic-ref", "-q", "HEAD"),
        _git(repository, "for-each-ref", "--format=%(refname) %(objectname)"),
        _git_text(repository, "write-tree"),
        _git(repository, "status", "--porcelain=v1", "--untracked-files=all"),
    )


def test_prepare_builds_an_unattached_reader_valid_b_e_s_p_transaction(tmp_path: Path):
    repository = _clone_repository(tmp_path)
    base_commit = _git_text(repository, "rev-parse", "HEAD")
    state_before = _repository_state(repository)

    prepared = prepare_history_publication(
        repository,
        expected_base_commit=base_commit,
        sources=_sources(),
        created_at=datetime(2026, 8, 27, 12, 5, tzinfo=UTC),
    )

    assert isinstance(prepared, PreparedPublication)
    assert prepared.repository == repository.resolve()
    assert prepared.base_commit == base_commit
    assert prepared.target_draw_date == date(2026, 8, 26)
    assert (
        _git_text(repository, "rev-parse", f"{prepared.evidence_commit}^")
        == base_commit
    )
    assert (
        _git_text(repository, "rev-parse", f"{prepared.suffix_commit}^")
        == prepared.evidence_commit
    )
    assert (
        _git_text(repository, "rev-parse", f"{prepared.publication_commit}^")
        == prepared.suffix_commit
    )
    assert _repository_state(repository) == state_before

    evidence_changes = _git_text(
        repository,
        "diff-tree",
        "--no-commit-id",
        "--name-status",
        "-r",
        prepared.evidence_commit,
    ).splitlines()
    expected_paths = {
        (
            "A\tevidence/live_sources/wclc/2026-08-26-"
            f"{sha256(_wclc_html()).hexdigest()}.html"
        ),
        (
            "A\tevidence/live_sources/loto_quebec/2026-08-26-"
            f"{sha256(_loto_quebec_html()).hexdigest()}.html"
        ),
    }
    assert set(evidence_changes) == expected_paths
    assert (
        _git_text(
            repository,
            "diff-tree",
            "--no-commit-id",
            "--name-status",
            "-r",
            prepared.suffix_commit,
        )
        == f"M\t{SUFFIX_PATH}"
    )
    assert (
        _git_text(
            repository,
            "diff-tree",
            "--no-commit-id",
            "--name-status",
            "-r",
            prepared.publication_commit,
        )
        == f"M\t{REGISTRY_PATH}"
    )

    suffix_event = json.loads(
        _git(
            repository, "show", f"{prepared.suffix_commit}:{SUFFIX_PATH}"
        ).splitlines()[-1]
    )
    registry_event = json.loads(
        _git(
            repository, "show", f"{prepared.publication_commit}:{REGISTRY_PATH}"
        ).splitlines()[-1]
    )
    assert suffix_event["draw"] == {
        "bonus": 11,
        "draw_date": "2026-08-26",
        "numbers": [2, 7, 18, 23, 35, 49],
    }
    assert suffix_event["evidence_commit"] == prepared.evidence_commit
    assert suffix_event["event_sha256"] == prepared.suffix_head_event_sha256
    receipts = {
        receipt["independence_group"]: receipt
        for receipt in suffix_event["source_receipts"]
    }
    assert receipts["wclc"]["bytes"] == len(_wclc_html())
    assert receipts["wclc"]["retrieved_at"] == "2026-08-27T12:00:00Z"
    assert receipts["loto_quebec"]["bytes"] == len(_loto_quebec_html())
    assert receipts["loto_quebec"]["retrieved_at"] == "2026-08-27T12:00:01Z"
    assert registry_event["event_sha256"] == prepared.registry_head_event_sha256
    assert registry_event["transaction"] == {
        "base_commit": base_commit,
        "evidence_commit": prepared.evidence_commit,
        "suffix_commit": prepared.suffix_commit,
    }

    published = load_published_history(repository, prepared.publication_commit)
    assert len(published.draws) == 4_445
    assert published.draws[-1].draw_date == date(2026, 8, 26)
    assert published.registry.publication_commit == prepared.publication_commit


def test_prepare_rejects_a_non_sequence_source_set_without_changing_repository(
    tmp_path: Path,
):
    repository = _clone_repository(tmp_path)
    base_commit = _git_text(repository, "rev-parse", "HEAD")
    state_before = _repository_state(repository)

    with pytest.raises(HistoryPublicationError, match="two RawSource"):
        prepare_history_publication(
            repository,
            expected_base_commit=base_commit,
            sources=cast("tuple[RawSource, ...]", object()),
            created_at=datetime(2026, 8, 27, 12, 5, tzinfo=UTC),
        )

    assert _repository_state(repository) == state_before


class _MissingOffset(tzinfo):
    def utcoffset(self, value: datetime | None):
        return None


class _InvalidOffset(tzinfo):
    def utcoffset(self, value: datetime | None):
        return "invalid"


class _ChangingSourceSequence(Sequence[RawSource]):
    def __init__(
        self,
        small: tuple[RawSource, RawSource],
        oversized: tuple[RawSource, RawSource],
    ) -> None:
        self._small = small
        self._oversized = oversized
        self.iterations = 0

    def __len__(self) -> int:
        return 2

    def __getitem__(self, index: int) -> RawSource:
        return self._small[index]

    def __iter__(self) -> Iterator[RawSource]:
        self.iterations += 1
        values = self._oversized if self.iterations == 3 else self._small
        return iter(values)


class _OverlongSourceSequence(Sequence[RawSource]):
    def __init__(self, source: RawSource) -> None:
        self._source = source
        self.consumed = 0

    def __len__(self) -> int:
        return 2

    def __getitem__(self, index: int) -> RawSource:
        return self._source

    def __iter__(self) -> Iterator[RawSource]:
        for _ in range(10_000):
            self.consumed += 1
            yield self._source


class _DeceptiveString(str):
    __hash__ = str.__hash__

    def __eq__(self, other: object) -> bool:
        return True

    def __ne__(self, other: object) -> bool:
        return False


class _ChangingRawSource(RawSource):
    def __getattribute__(self, name: str):
        if name != "raw":
            return super().__getattribute__(name)
        reads = super().__getattribute__("_raw_reads")
        object.__setattr__(self, "_raw_reads", reads + 1)
        if reads < 3:
            return super().__getattribute__("_small_raw")
        return super().__getattribute__("_oversized_raw")


def test_prepare_rejects_a_timestamp_without_a_real_utc_offset(tmp_path: Path):
    repository = _clone_repository(tmp_path)
    base_commit = _git_text(repository, "rev-parse", "HEAD")

    with pytest.raises(HistoryPublicationError, match="timezone-aware"):
        prepare_history_publication(
            repository,
            expected_base_commit=base_commit,
            sources=_sources(),
            created_at=datetime(2026, 8, 27, 12, 5, tzinfo=_MissingOffset()),
        )


@pytest.mark.parametrize("field_name", ["created_at", "retrieved_at"])
def test_prepare_wraps_an_invalid_timezone_as_a_publication_error(
    tmp_path: Path, field_name: str
):
    repository = _clone_repository(tmp_path)
    base_commit = _git_text(repository, "rev-parse", "HEAD")
    sources = list(_sources())
    created_at = datetime(2026, 8, 27, 12, 5, tzinfo=UTC)
    invalid_time = datetime(2026, 8, 27, 12, 0, tzinfo=_InvalidOffset())
    if field_name == "created_at":
        created_at = invalid_time
    else:
        source = sources[0]
        sources[0] = RawSource(
            authority=source.authority,
            url=source.url,
            retrieved_at=invalid_time,
            raw=source.raw,
        )

    with pytest.raises(HistoryPublicationError, match=f"{field_name} is invalid"):
        prepare_history_publication(
            repository,
            expected_base_commit=base_commit,
            sources=tuple(sources),
            created_at=created_at,
        )


def test_prepare_rejects_a_non_string_authority_as_a_publication_error(
    tmp_path: Path,
):
    repository = _clone_repository(tmp_path)
    base_commit = _git_text(repository, "rev-parse", "HEAD")
    wclc, loto_quebec = _sources()
    malformed = RawSource(
        authority=cast("str", ["wclc"]),
        url=wclc.url,
        retrieved_at=wclc.retrieved_at,
        raw=wclc.raw,
    )

    with pytest.raises(HistoryPublicationError, match="official authority"):
        prepare_history_publication(
            repository,
            expected_base_commit=base_commit,
            sources=(malformed, loto_quebec),
            created_at=datetime(2026, 8, 27, 12, 5, tzinfo=UTC),
        )


@pytest.mark.parametrize("field_name", ["authority", "url"])
def test_prepare_rejects_string_subclasses_before_writing_git_objects(
    tmp_path: Path, field_name: str
):
    repository = _clone_repository(tmp_path)
    base_commit = _git_text(repository, "rev-parse", "HEAD")
    wclc, loto_quebec = _sources()
    malformed = RawSource(
        authority=(
            _DeceptiveString(wclc.authority)
            if field_name == "authority"
            else wclc.authority
        ),
        url=(
            _DeceptiveString(f"{wclc.url}?token=IMMUTABLE_SECRET")
            if field_name == "url"
            else wclc.url
        ),
        retrieved_at=wclc.retrieved_at,
        raw=wclc.raw,
    )
    state_before = _repository_state(repository)
    objects_before = _git(repository, "count-objects", "-v")

    with pytest.raises(HistoryPublicationError):
        prepare_history_publication(
            repository,
            expected_base_commit=base_commit,
            sources=(malformed, loto_quebec),
            created_at=datetime(2026, 8, 27, 12, 5, tzinfo=UTC),
        )

    assert _git(repository, "count-objects", "-v") == objects_before
    assert _repository_state(repository) == state_before


def test_prepare_preserves_dirty_worktree_index_refs_and_hostile_git_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    repository = _clone_repository(tmp_path)
    base_commit = _git_text(repository, "rev-parse", "HEAD")
    readme = repository / "README.md"
    readme.write_bytes(readme.read_bytes() + b"\nstaged caller change\n")
    _git(repository, "add", "README.md")
    readme.write_bytes(readme.read_bytes() + b"unstaged caller change\n")
    (repository / "caller-untracked.txt").write_bytes(b"caller state\n")
    state_before = _repository_state(repository)
    foreign_index = tmp_path / "foreign-index"
    foreign_index.write_bytes(b"caller-owned index sentinel\n")

    with monkeypatch.context() as context:
        context.setenv("GIT_INDEX_FILE", str(foreign_index))
        context.setenv("GIT_OBJECT_DIRECTORY", str(tmp_path / "hostile-objects"))
        prepared = prepare_history_publication(
            repository,
            expected_base_commit=base_commit,
            sources=_sources(),
            created_at=datetime(2026, 8, 27, 12, 5, tzinfo=UTC),
        )

    assert prepared.base_commit == base_commit
    assert foreign_index.read_bytes() == b"caller-owned index sentinel\n"
    assert _repository_state(repository) == state_before


def test_prepare_private_index_ignores_repository_split_index_config(tmp_path: Path):
    repository = _clone_repository(tmp_path)
    base_commit = _git_text(repository, "rev-parse", "HEAD")
    _git(repository, "config", "core.splitIndex", "true")
    state_before = _repository_state(repository)
    git_directory = Path(_git_text(repository, "rev-parse", "--git-dir"))
    if not git_directory.is_absolute():
        git_directory = repository / git_directory
    shared_before = tuple(git_directory.glob("sharedindex.*"))

    prepare_history_publication(
        repository,
        expected_base_commit=base_commit,
        sources=_sources(),
        created_at=datetime(2026, 8, 27, 12, 5, tzinfo=UTC),
    )

    assert tuple(git_directory.glob("sharedindex.*")) == shared_before
    assert _repository_state(repository) == state_before


def test_prepare_commit_identities_ignore_repository_commit_encoding(tmp_path: Path):
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    first_root.mkdir()
    second_root.mkdir()
    first = _clone_repository(first_root)
    second = _clone_repository(second_root)
    base_commit = _git_text(first, "rev-parse", "HEAD")
    assert _git_text(second, "rev-parse", "HEAD") == base_commit
    _git(second, "config", "i18n.commitEncoding", "ISO-8859-1")

    first_prepared = prepare_history_publication(
        first,
        expected_base_commit=base_commit,
        sources=_sources(),
        created_at=datetime(2026, 8, 27, 12, 5, tzinfo=UTC),
    )
    second_prepared = prepare_history_publication(
        second,
        expected_base_commit=base_commit,
        sources=_sources(),
        created_at=datetime(2026, 8, 27, 12, 5, tzinfo=UTC),
    )

    assert (
        second_prepared.evidence_commit,
        second_prepared.suffix_commit,
        second_prepared.publication_commit,
    ) == (
        first_prepared.evidence_commit,
        first_prepared.suffix_commit,
        first_prepared.publication_commit,
    )


def test_prepare_rejects_disagreeing_sources_without_writing_git_objects(
    tmp_path: Path,
):
    repository = _clone_repository(tmp_path)
    base_commit = _git_text(repository, "rev-parse", "HEAD")
    wclc, loto_quebec = _sources()
    disagreeing = RawSource(
        authority=loto_quebec.authority,
        url=loto_quebec.url,
        retrieved_at=loto_quebec.retrieved_at,
        raw=loto_quebec.raw.replace(b">49<", b">48<"),
    )
    state_before = _repository_state(repository)
    objects_before = _git(repository, "count-objects", "-v")

    with pytest.raises(HistoryPublicationError, match="disagree"):
        prepare_history_publication(
            repository,
            expected_base_commit=base_commit,
            sources=(wclc, disagreeing),
            created_at=datetime(2026, 8, 27, 12, 5, tzinfo=UTC),
        )

    assert _git(repository, "count-objects", "-v") == objects_before
    assert _repository_state(repository) == state_before


def test_prepare_rejects_oversized_source_before_writing_git_objects(tmp_path: Path):
    repository = _clone_repository(tmp_path)
    base_commit = _git_text(repository, "rev-parse", "HEAD")
    wclc, loto_quebec = _sources()
    oversized = RawSource(
        authority=wclc.authority,
        url=wclc.url,
        retrieved_at=wclc.retrieved_at,
        raw=wclc.raw + b" " * (2 * 1024 * 1024 + 1),
    )
    state_before = _repository_state(repository)
    objects_before = _git(repository, "count-objects", "-v")

    with pytest.raises(HistoryPublicationError, match="source size"):
        prepare_history_publication(
            repository,
            expected_base_commit=base_commit,
            sources=(oversized, loto_quebec),
            created_at=datetime(2026, 8, 27, 12, 5, tzinfo=UTC),
        )

    assert _git(repository, "count-objects", "-v") == objects_before
    assert _repository_state(repository) == state_before


def test_prepare_freezes_a_stateful_source_sequence_before_validation(tmp_path: Path):
    repository = _clone_repository(tmp_path)
    base_commit = _git_text(repository, "rev-parse", "HEAD")
    wclc, loto_quebec = _sources()
    oversized_wclc = RawSource(
        authority=wclc.authority,
        url=wclc.url,
        retrieved_at=wclc.retrieved_at,
        raw=wclc.raw + b" " * (2 * 1024 * 1024 + 1),
    )
    sources = _ChangingSourceSequence(
        (wclc, loto_quebec),
        (oversized_wclc, loto_quebec),
    )

    prepared = prepare_history_publication(
        repository,
        expected_base_commit=base_commit,
        sources=sources,
        created_at=datetime(2026, 8, 27, 12, 5, tzinfo=UTC),
    )

    suffix_event = json.loads(
        _git(
            repository,
            "show",
            f"{prepared.suffix_commit}:{SUFFIX_PATH}",
        ).splitlines()[-1]
    )
    assert sources.iterations == 1
    assert (
        max(receipt["bytes"] for receipt in suffix_event["source_receipts"])
        <= 2 * 1024 * 1024
    )


def test_prepare_bounds_consumption_of_an_overlong_source_sequence(tmp_path: Path):
    repository = _clone_repository(tmp_path)
    base_commit = _git_text(repository, "rev-parse", "HEAD")
    sources = _OverlongSourceSequence(_sources()[0])
    state_before = _repository_state(repository)
    objects_before = _git(repository, "count-objects", "-v")

    with pytest.raises(HistoryPublicationError, match="two RawSource"):
        prepare_history_publication(
            repository,
            expected_base_commit=base_commit,
            sources=sources,
            created_at=datetime(2026, 8, 27, 12, 5, tzinfo=UTC),
        )

    assert sources.consumed <= 3
    assert _git(repository, "count-objects", "-v") == objects_before
    assert _repository_state(repository) == state_before


def test_prepare_rejects_raw_source_subclasses_before_writing_git_objects(
    tmp_path: Path,
):
    repository = _clone_repository(tmp_path)
    base_commit = _git_text(repository, "rev-parse", "HEAD")
    wclc, loto_quebec = _sources()
    changing = _ChangingRawSource(
        authority=wclc.authority,
        url=wclc.url,
        retrieved_at=wclc.retrieved_at,
        raw=wclc.raw,
    )
    object.__setattr__(changing, "_raw_reads", 0)
    object.__setattr__(changing, "_small_raw", wclc.raw)
    object.__setattr__(
        changing,
        "_oversized_raw",
        wclc.raw + b" " * (2 * 1024 * 1024 + 1),
    )
    state_before = _repository_state(repository)
    objects_before = _git(repository, "count-objects", "-v")

    with pytest.raises(HistoryPublicationError, match="two RawSource"):
        prepare_history_publication(
            repository,
            expected_base_commit=base_commit,
            sources=(changing, loto_quebec),
            created_at=datetime(2026, 8, 27, 12, 5, tzinfo=UTC),
        )

    assert _git(repository, "count-objects", "-v") == objects_before
    assert _repository_state(repository) == state_before


@pytest.mark.parametrize("authority", ["wclc", "loto_quebec"])
def test_prepare_rejects_unregistered_source_query_before_writing_objects(
    tmp_path: Path, authority: str
):
    repository = _clone_repository(tmp_path)
    base_commit = _git_text(repository, "rev-parse", "HEAD")
    sources = list(_sources())
    index = next(
        index for index, source in enumerate(sources) if source.authority == authority
    )
    original = sources[index]
    separator = "&" if "?" in original.url else "?"
    sources[index] = RawSource(
        authority=original.authority,
        url=f"{original.url}{separator}token=IMMUTABLE_SECRET",
        retrieved_at=original.retrieved_at,
        raw=original.raw,
    )
    state_before = _repository_state(repository)
    objects_before = _git(repository, "count-objects", "-v")

    with pytest.raises(HistoryPublicationError, match="source URL"):
        prepare_history_publication(
            repository,
            expected_base_commit=base_commit,
            sources=tuple(sources),
            created_at=datetime(2026, 8, 27, 12, 5, tzinfo=UTC),
        )

    assert _git(repository, "count-objects", "-v") == objects_before
    assert _repository_state(repository) == state_before


@pytest.mark.parametrize("authority", ["wclc", "loto_quebec"])
def test_prepare_requires_the_exact_canonical_source_url(
    tmp_path: Path, authority: str
):
    repository = _clone_repository(tmp_path)
    base_commit = _git_text(repository, "rev-parse", "HEAD")
    sources = list(_sources())
    index = next(
        index for index, source in enumerate(sources) if source.authority == authority
    )
    original = sources[index]
    sources[index] = RawSource(
        authority=original.authority,
        url=original.url.replace(".com/", ".com:443/", 1),
        retrieved_at=original.retrieved_at,
        raw=original.raw,
    )

    with pytest.raises(HistoryPublicationError, match="source URL"):
        prepare_history_publication(
            repository,
            expected_base_commit=base_commit,
            sources=tuple(sources),
            created_at=datetime(2026, 8, 27, 12, 5, tzinfo=UTC),
        )


def test_prepare_can_extend_an_unattached_prior_publication(tmp_path: Path):
    repository = _clone_repository(tmp_path)
    base_commit = _git_text(repository, "rev-parse", "HEAD")
    first = prepare_history_publication(
        repository,
        expected_base_commit=base_commit,
        sources=_sources(),
        created_at=datetime(2026, 8, 27, 12, 5, tzinfo=UTC),
    )

    second = prepare_history_publication(
        repository,
        expected_base_commit=first.publication_commit,
        sources=_second_sources(),
        created_at=datetime(2026, 8, 30, 12, 5, tzinfo=UTC),
    )

    assert second.base_commit == first.publication_commit
    assert second.target_draw_date == date(2026, 8, 29)
    published = load_published_history(repository, second.publication_commit)
    assert len(published.draws) == 4_446
    assert published.draws[-1].draw_date == date(2026, 8, 29)
    assert published.registry.event_count == 3


def test_prepare_operates_in_the_same_bare_object_store_used_by_cas(tmp_path: Path):
    repository = _clone_bare_repository(tmp_path)
    base_commit = _git_text(repository, "rev-parse", "HEAD")
    head_before = (repository / "HEAD").read_bytes()
    refs_before = _git(repository, "for-each-ref", "--format=%(refname) %(objectname)")

    prepared = prepare_history_publication(
        repository,
        expected_base_commit=base_commit,
        sources=_sources(),
        created_at=datetime(2026, 8, 27, 12, 5, tzinfo=UTC),
    )

    assert prepared.repository == repository.resolve()
    assert _git_text(repository, "rev-parse", "HEAD") == base_commit
    assert (repository / "HEAD").read_bytes() == head_before
    assert (
        _git(repository, "for-each-ref", "--format=%(refname) %(objectname)")
        == refs_before
    )
    published = load_published_history(repository, prepared.publication_commit)
    assert published.registry.publication_commit == prepared.publication_commit


def test_late_validation_failure_changes_no_authority_or_caller_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    repository = _clone_repository(tmp_path)
    base_commit = _git_text(repository, "rev-parse", "HEAD")
    _git(repository, "config", "core.splitIndex", "true")
    state_before = _repository_state(repository)
    git_directory = Path(_git_text(repository, "rev-parse", "--git-dir"))
    if not git_directory.is_absolute():
        git_directory = repository / git_directory
    shared_before = tuple(git_directory.glob("sharedindex.*"))
    real_loader = history_publication.load_published_history
    calls = 0

    def fail_candidate_load(repository_path: Path, revision: str):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise ValueError("injected candidate validation failure")
        return real_loader(repository_path, revision)

    monkeypatch.setattr(
        history_publication,
        "load_published_history",
        fail_candidate_load,
    )

    with pytest.raises(HistoryPublicationError, match="candidate publication"):
        prepare_history_publication(
            repository,
            expected_base_commit=base_commit,
            sources=_sources(),
            created_at=datetime(2026, 8, 27, 12, 5, tzinfo=UTC),
        )

    assert _repository_state(repository) == state_before
    assert tuple(git_directory.glob("sharedindex.*")) == shared_before
    assert b"unreachable commit" in _git(
        repository,
        "fsck",
        "--unreachable",
        "--no-reflogs",
    )
