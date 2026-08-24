from __future__ import annotations

import base64
import hashlib
import os
import shutil
import subprocess
import tempfile
import zlib
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
import requests

import lotto649.history_publication_github as github_publication

from lotto649.history_publication import (
    PreparedPublication,
    RawSource,
    prepare_history_publication,
)
from lotto649.history_publication_cas import (
    CasStatus,
    PreparationIntegrityError,
    PublicationConflict,
    PublicationIndeterminate,
    PublicationOutcome,
    PublishedReloadError,
    StalePublication,
)
from lotto649.history_publication_github import (
    PRODUCTION_GITHUB_REPOSITORY,
    FreshBareGitHubSnapshotLoader,
    GitHubPublicationError,
    GitHubRepositoryIdentity,
    RequestsGitHubApi,
    _publish_with_ports as publish_prepared_history_to_github,
)
from lotto649.operational_history import PublishedHistory, load_published_history


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = PRODUCTION_GITHUB_REPOSITORY


def _git_text(repository: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _next_draw_date(draw_date: date) -> date:
    return draw_date + timedelta(days=3 if draw_date.weekday() == 2 else 4)


def _wclc_html(draw_date: date) -> bytes:
    weekdays = (
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    )
    months = (
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    )
    display_date = (
        f"{weekdays[draw_date.weekday()]}, {months[draw_date.month - 1]} "
        f"{draw_date.day}, {draw_date.year}"
    )
    return (
        b"<!doctype html><html><body>"
        + display_date.encode("ascii")
        + b" CLASSIC DRAW 02 07 18 23 35 49 Bonus 11</body></html>"
    )


def _loto_quebec_html(draw_date: date) -> bytes:
    return (
        b"<!doctype html><html><body>"
        + f'<span id="dateAffichee">{draw_date.isoformat()}</span>'.encode()
        + b'<div class="lqZoneProduit principal lotto-6-49">'
        b'<div class="numeros tirageClassique">'
        b'<span class="num">02</span><span class="num">07</span>'
        b'<span class="num">18</span><span class="num">23</span>'
        b'<span class="num">35</span><span class="num">49</span>'
        b'<span class="num complementaire">11</span>'
        b"</div></div></body></html>"
    )


def _prepared_publication(tmp_path: Path) -> PreparedPublication:
    repository = tmp_path / "repository"
    subprocess.run(
        ["git", "clone", "--no-local", "--quiet", str(ROOT), str(repository)],
        check=True,
        capture_output=True,
    )
    base_commit = _git_text(repository, "rev-parse", "HEAD")
    base_history = load_published_history(repository, base_commit)
    target = _next_draw_date(base_history.draws[-1].draw_date)
    created_at = datetime.combine(
        target + timedelta(days=1),
        datetime.min.time(),
        UTC,
    ).replace(hour=12)
    return prepare_history_publication(
        repository,
        expected_base_commit=base_commit,
        sources=(
            RawSource(
                authority="wclc",
                url="https://www.wclc.com/winning-numbers/lotto-649-extra.htm",
                retrieved_at=created_at,
                raw=_wclc_html(target),
            ),
            RawSource(
                authority="loto_quebec",
                url=(
                    "https://loteries.lotoquebec.com/en/lotteries/"
                    f"lotto-6-49-resultats?date={target.isoformat()}"
                ),
                retrieved_at=created_at,
                raw=_loto_quebec_html(target),
            ),
        ),
        created_at=created_at,
    )


@pytest.fixture(scope="module")
def prepared_publication(
    tmp_path_factory: pytest.TempPathFactory,
) -> PreparedPublication:
    return _prepared_publication(tmp_path_factory.mktemp("github-publication"))


def _git_object_sha(kind: str, raw: bytes) -> str:
    header = f"{kind} {len(raw)}\0".encode("ascii")
    return hashlib.sha1(header + raw).hexdigest()  # noqa: S324


class _ExactApi:
    def __init__(self, prepared: PreparedPublication) -> None:
        self._prepared = prepared
        self.current = prepared.base_commit
        self._temporary = tempfile.TemporaryDirectory(prefix="github-api-fake-")
        self._tree_index = 0
        self.calls: list[tuple[str, str, object | None]] = []

    def _tree_oid(self, payload: dict[str, object]) -> str:
        base_tree = payload["base_tree"]
        entries = payload["tree"]
        assert isinstance(base_tree, str)
        assert isinstance(entries, list)
        self._tree_index += 1
        index = Path(self._temporary.name) / f"index-{self._tree_index}"
        environment = {**os.environ, "GIT_INDEX_FILE": str(index)}
        subprocess.run(
            ["git", "-C", str(self._prepared.repository), "read-tree", base_tree],
            check=True,
            capture_output=True,
            env=environment,
        )
        for entry in entries:
            assert isinstance(entry, dict)
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(self._prepared.repository),
                    "update-index",
                    "--add",
                    "--cacheinfo",
                    str(entry["mode"]),
                    str(entry["sha"]),
                    str(entry["path"]),
                ],
                check=True,
                capture_output=True,
                env=environment,
            )
        return subprocess.run(
            ["git", "-C", str(self._prepared.repository), "write-tree"],
            check=True,
            capture_output=True,
            text=True,
            env=environment,
        ).stdout.strip()

    @staticmethod
    def _commit_oid(payload: dict[str, object]) -> str:
        message = payload["message"]
        tree = payload["tree"]
        parents = payload["parents"]
        author = payload["author"]
        committer = payload["committer"]
        assert isinstance(message, str)
        assert isinstance(tree, str)
        assert isinstance(parents, list) and len(parents) == 1
        assert isinstance(author, dict)
        assert isinstance(committer, dict)

        def signature(kind: str, actor: dict[str, object]) -> bytes:
            instant = datetime.fromisoformat(str(actor["date"]).replace("Z", "+00:00"))
            assert instant.tzinfo is not None and instant.utcoffset() == timedelta(0)
            return (
                f"{kind} {actor['name']} <{actor['email']}> "
                f"{int(instant.timestamp())} +0000\n"
            ).encode("utf-8")

        raw = (
            f"tree {tree}\nparent {parents[0]}\n".encode("ascii")
            + signature("author", author)
            + signature("committer", committer)
            + b"\n"
            + message.encode("utf-8")
        )
        return _git_object_sha("commit", raw)

    def request_json(
        self,
        method: str,
        path: str,
        *,
        payload: object | None = None,
    ) -> object:
        self.calls.append((method, path, payload))
        if method == "GET" and path == "/repos/Jasper-Shi/lottopred":
            return {
                "id": 1,
                "node_id": REPOSITORY.node_id,
                "full_name": "Jasper-Shi/lottopred",
                "default_branch": "main",
                "private": False,
            }
        if method == "GET" and path.endswith("/hash-algorithm"):
            return {"hash_algorithm": "sha1"}
        if method == "GET" and path.endswith("/branches/main/protection"):
            return {
                "enforce_admins": {"enabled": True},
                "allow_force_pushes": {"enabled": False},
                "allow_deletions": {"enabled": False},
            }
        if method == "GET" and path.endswith("/git/ref/heads/main"):
            return {
                "ref": "refs/heads/main",
                "object": {"type": "commit", "sha": self.current},
            }
        if method == "POST" and path.endswith("/git/blobs"):
            assert isinstance(payload, dict)
            assert payload["encoding"] == "base64"
            raw = base64.b64decode(payload["content"], validate=True)
            return {"sha": _git_object_sha("blob", raw)}
        if method == "POST" and path.endswith("/git/trees"):
            assert isinstance(payload, dict)
            return {"sha": self._tree_oid(payload)}
        if method == "POST" and path.endswith("/git/commits"):
            assert isinstance(payload, dict)
            return {"sha": self._commit_oid(payload)}
        if method == "GET" and path.endswith("/git/commits/" + self.current):
            return {"sha": self.current}
        if method == "POST" and path == "/graphql":
            assert isinstance(payload, dict)
            assert (
                payload["query"]
                == """mutation UpdateHistoryRef($input: UpdateRefsInput!) {
  updateRefs(input: $input) {
    clientMutationId
  }
}"""
            )
            variables = payload["variables"]
            assert isinstance(variables, dict)
            assert variables == {
                "input": {
                    "repositoryId": REPOSITORY.node_id,
                    "refUpdates": [
                        {
                            "name": "refs/heads/main",
                            "beforeOid": self.current,
                            "afterOid": self._prepared.publication_commit,
                            "force": False,
                        }
                    ],
                    "clientMutationId": (
                        f"history-publication:{self._prepared.publication_commit}"
                    ),
                }
            }
            self.current = self._prepared.publication_commit
            return {
                "data": {
                    "updateRefs": {
                        "clientMutationId": variables["input"]["clientMutationId"]
                    }
                }
            }
        if method == "GET" and "/git/commits/" in path:
            requested = path.rsplit("/", 1)[1]
            return {"sha": requested}
        raise AssertionError(f"unexpected request: {method} {path}")


class _CandidateSnapshotLoader:
    def __init__(self, prepared: PreparedPublication) -> None:
        self._prepared = prepared
        self.calls: list[tuple[GitHubRepositoryIdentity, str]] = []

    def load(
        self,
        repository: GitHubRepositoryIdentity,
        expected_head: str,
    ) -> PublishedHistory:
        self.calls.append((repository, expected_head))
        return load_published_history(self._prepared.repository, expected_head)


def test_remote_publish_uploads_exact_objects_then_cas_and_reloads(
    prepared_publication: PreparedPublication,
) -> None:
    prepared = prepared_publication
    api = _ExactApi(prepared)
    loader = _CandidateSnapshotLoader(prepared)

    receipt = publish_prepared_history_to_github(
        prepared,
        api=api,
        snapshot_loader=loader,
    )

    assert receipt.expected_base == prepared.base_commit
    assert receipt.publication_commit == prepared.publication_commit
    assert receipt.observed_before == prepared.base_commit
    assert receipt.observed_after == prepared.publication_commit
    assert receipt.outcome is PublicationOutcome.ADVANCED
    assert receipt.history.draws[-1].draw_date == prepared.target_draw_date
    assert api.current == prepared.publication_commit
    assert loader.calls == [(REPOSITORY, prepared.publication_commit)]
    graph_calls = [call for call in api.calls if call[1] == "/graphql"]
    assert len(graph_calls) == 1
    commit_calls = [call for call in api.calls if call[1].endswith("/git/commits")]
    expected_commits = (
        prepared.evidence_commit,
        prepared.suffix_commit,
        prepared.publication_commit,
    )
    assert len(commit_calls) == len(expected_commits)
    for (_method, _path, payload), commit in zip(
        commit_calls,
        expected_commits,
        strict=True,
    ):
        assert isinstance(payload, dict)
        raw_commit = subprocess.run(
            ["git", "-C", str(prepared.repository), "cat-file", "commit", commit],
            check=True,
            capture_output=True,
        ).stdout
        assert payload["message"] == raw_commit.split(b"\n\n", 1)[1].decode("utf-8")
        assert payload["message"].endswith("\n")


def test_public_entrypoint_fixes_the_github_and_fresh_snapshot_adapters(
    prepared_publication: PreparedPublication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = _ExactApi(prepared_publication)
    loader = _CandidateSnapshotLoader(prepared_publication)
    observed_tokens: list[str] = []

    def api_factory(token: str) -> _ExactApi:
        observed_tokens.append(token)
        return api

    monkeypatch.setattr(github_publication, "RequestsGitHubApi", api_factory)
    monkeypatch.setattr(
        github_publication,
        "FreshBareGitHubSnapshotLoader",
        lambda: loader,
    )

    receipt = github_publication.publish_prepared_history_to_github(
        prepared_publication,
        token="sentinel-token",
    )

    assert observed_tokens == ["sentinel-token"]
    assert receipt.publication_commit == prepared_publication.publication_commit
    assert loader.calls == [
        (REPOSITORY, prepared_publication.publication_commit),
    ]


def test_invalid_candidate_stops_before_any_github_request(
    prepared_publication: PreparedPublication,
) -> None:
    prepared = replace(
        prepared_publication,
        publication_commit="f" * 40,
    )
    api = _ExactApi(prepared_publication)

    with pytest.raises(PreparationIntegrityError):
        publish_prepared_history_to_github(
            prepared,
            api=api,
            snapshot_loader=_CandidateSnapshotLoader(prepared_publication),
        )

    assert api.calls == []


def test_corrupt_nested_local_tree_stops_before_any_github_request(
    prepared_publication: PreparedPublication,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repository = tmp_path / "corrupt-repository"
    shutil.copytree(prepared_publication.repository, repository)
    prepared = replace(prepared_publication, repository=repository)
    tree = _git_text(
        repository,
        "rev-parse",
        f"{prepared.evidence_commit}:evidence/live_sources",
    )
    loose = repository / ".git" / "objects" / tree[:2] / tree[2:]
    loose.parent.mkdir(parents=True, exist_ok=True)
    if loose.exists():
        loose.chmod(0o600)
    loose.write_bytes(zlib.compress(b"tree 0\0"))
    valid_history = load_published_history(
        prepared_publication.repository,
        prepared_publication.publication_commit,
    )
    monkeypatch.setattr(
        github_publication,
        "load_published_history",
        lambda _repository, _revision: valid_history,
    )
    api = _ExactApi(prepared_publication)

    with pytest.raises(PreparationIntegrityError):
        publish_prepared_history_to_github(
            prepared,
            api=api,
            snapshot_loader=_CandidateSnapshotLoader(prepared_publication),
        )

    assert api.calls == []


def test_repository_fsck_policy_override_stops_before_any_github_request(
    prepared_publication: PreparedPublication,
    tmp_path: Path,
) -> None:
    repository = tmp_path / "policy-repository"
    shutil.copytree(prepared_publication.repository, repository)
    subprocess.run(
        [
            "git",
            "-C",
            str(repository),
            "config",
            "--local",
            "fsck.badDate",
            "ignore",
        ],
        check=True,
        capture_output=True,
    )
    prepared = replace(prepared_publication, repository=repository)
    api = _ExactApi(prepared_publication)

    with pytest.raises(PreparationIntegrityError, match="fsck policy"):
        publish_prepared_history_to_github(
            prepared,
            api=api,
            snapshot_loader=_CandidateSnapshotLoader(prepared_publication),
        )

    assert api.calls == []


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("registry_head_event_sha256", "f" * 63),
        ("suffix_head_event_sha256", "F" * 64),
    ],
)
def test_malformed_event_hash_stops_before_any_github_request(
    prepared_publication: PreparedPublication,
    field: str,
    value: str,
) -> None:
    prepared = replace(prepared_publication, **{field: value})
    api = _ExactApi(prepared_publication)

    with pytest.raises(PreparationIntegrityError, match="SHA-256"):
        publish_prepared_history_to_github(
            prepared,
            api=api,
            snapshot_loader=_CandidateSnapshotLoader(prepared_publication),
        )

    assert api.calls == []


def test_stale_remote_head_stops_before_object_upload(
    prepared_publication: PreparedPublication,
) -> None:
    api = _ExactApi(prepared_publication)
    api.current = "a" * 40

    with pytest.raises(StalePublication) as raised:
        publish_prepared_history_to_github(
            prepared_publication,
            api=api,
            snapshot_loader=_CandidateSnapshotLoader(prepared_publication),
        )

    assert raised.value.observed == "a" * 40
    assert all(method == "GET" for method, _path, _payload in api.calls)


class _UnprotectedApi(_ExactApi):
    def request_json(
        self,
        method: str,
        path: str,
        *,
        payload: object | None = None,
    ) -> object:
        response = super().request_json(method, path, payload=payload)
        if path.endswith("/branches/main/protection"):
            return {
                "enforce_admins": {"enabled": False},
                "allow_force_pushes": {"enabled": True},
                "allow_deletions": {"enabled": False},
            }
        return response


class _WrongHashAlgorithmApi(_ExactApi):
    def request_json(
        self,
        method: str,
        path: str,
        *,
        payload: object | None = None,
    ) -> object:
        response = super().request_json(method, path, payload=payload)
        if path.endswith("/hash-algorithm"):
            return {"hash_algorithm": "sha256"}
        return response


def test_non_sha1_repository_stops_before_ref_read_or_upload(
    prepared_publication: PreparedPublication,
) -> None:
    api = _WrongHashAlgorithmApi(prepared_publication)

    with pytest.raises(GitHubPublicationError, match="hash algorithm"):
        publish_prepared_history_to_github(
            prepared_publication,
            api=api,
            snapshot_loader=_CandidateSnapshotLoader(prepared_publication),
        )

    assert [path for _method, path, _payload in api.calls] == [
        "/repos/Jasper-Shi/lottopred",
        "/repos/Jasper-Shi/lottopred/hash-algorithm",
    ]


def test_unprotected_main_stops_before_ref_read_or_upload(
    prepared_publication: PreparedPublication,
) -> None:
    api = _UnprotectedApi(prepared_publication)

    with pytest.raises(GitHubPublicationError, match="protection"):
        publish_prepared_history_to_github(
            prepared_publication,
            api=api,
            snapshot_loader=_CandidateSnapshotLoader(prepared_publication),
        )

    assert [path for _method, path, _payload in api.calls] == [
        "/repos/Jasper-Shi/lottopred",
        "/repos/Jasper-Shi/lottopred/hash-algorithm",
        "/repos/Jasper-Shi/lottopred/branches/main/protection",
    ]


def test_already_published_remote_head_skips_upload_and_cas(
    prepared_publication: PreparedPublication,
) -> None:
    api = _ExactApi(prepared_publication)
    api.current = prepared_publication.publication_commit
    loader = _CandidateSnapshotLoader(prepared_publication)

    receipt = publish_prepared_history_to_github(
        prepared_publication,
        api=api,
        snapshot_loader=loader,
    )

    assert receipt.outcome is PublicationOutcome.ALREADY_PUBLISHED
    assert all(method == "GET" for method, _path, _payload in api.calls)
    assert loader.calls == [(REPOSITORY, prepared_publication.publication_commit)]


class _WrongObjectApi(_ExactApi):
    def __init__(self, prepared: PreparedPublication, phase: str) -> None:
        super().__init__(prepared)
        self._phase = phase

    def request_json(
        self,
        method: str,
        path: str,
        *,
        payload: object | None = None,
    ) -> object:
        response = super().request_json(method, path, payload=payload)
        object_phase = (
            "blob"
            if method == "POST" and path.endswith("/git/blobs")
            else "tree"
            if method == "POST" and path.endswith("/git/trees")
            else "commit"
            if method == "POST" and path.endswith("/git/commits")
            else "publication"
            if method == "GET"
            and path.endswith("/git/commits/" + self._prepared.publication_commit)
            else ""
        )
        if object_phase == self._phase:
            return {"sha": "b" * 40}
        return response


@pytest.mark.parametrize("phase", ["blob", "tree", "commit", "publication"])
def test_object_identity_mismatch_stops_before_cas(
    prepared_publication: PreparedPublication,
    phase: str,
) -> None:
    api = _WrongObjectApi(prepared_publication, phase)

    with pytest.raises(GitHubPublicationError, match="identity|unavailable"):
        publish_prepared_history_to_github(
            prepared_publication,
            api=api,
            snapshot_loader=_CandidateSnapshotLoader(prepared_publication),
        )

    assert not any(path == "/graphql" for _method, path, _payload in api.calls)
    assert api.current == prepared_publication.base_commit


class _AppliedThenLostAckApi(_ExactApi):
    def request_json(
        self,
        method: str,
        path: str,
        *,
        payload: object | None = None,
    ) -> object:
        response = super().request_json(method, path, payload=payload)
        if path == "/graphql":
            raise RuntimeError("ack lost after mutation")
        return response


def test_lost_ack_is_confirmed_only_by_reread_and_fresh_reload(
    prepared_publication: PreparedPublication,
) -> None:
    api = _AppliedThenLostAckApi(prepared_publication)

    receipt = publish_prepared_history_to_github(
        prepared_publication,
        api=api,
        snapshot_loader=_CandidateSnapshotLoader(prepared_publication),
    )

    assert receipt.outcome is PublicationOutcome.CONFIRMED_AFTER_REREAD
    assert receipt.cas_ack is not None
    assert receipt.cas_ack.status is CasStatus.UNKNOWN
    assert len([call for call in api.calls if call[1] == "/graphql"]) == 1


class _RejectedCasApi(_ExactApi):
    def request_json(
        self,
        method: str,
        path: str,
        *,
        payload: object | None = None,
    ) -> object:
        if path == "/graphql":
            self.calls.append((method, path, payload))
            return {"data": None, "errors": [{"message": "stale"}]}
        return super().request_json(method, path, payload=payload)


def test_unknown_cas_that_still_observes_base_is_indeterminate(
    prepared_publication: PreparedPublication,
) -> None:
    api = _RejectedCasApi(prepared_publication)

    with pytest.raises(PublicationIndeterminate) as raised:
        publish_prepared_history_to_github(
            prepared_publication,
            api=api,
            snapshot_loader=_CandidateSnapshotLoader(prepared_publication),
        )

    assert raised.value.last_observed == prepared_publication.base_commit
    assert api.current == prepared_publication.base_commit
    assert len([call for call in api.calls if call[1] == "/graphql"]) == 1


class _ConflictingCasApi(_RejectedCasApi):
    def request_json(
        self,
        method: str,
        path: str,
        *,
        payload: object | None = None,
    ) -> object:
        response = super().request_json(method, path, payload=payload)
        if path == "/graphql":
            self.current = "c" * 40
        return response


def test_concurrent_third_head_is_a_conflict_without_retry(
    prepared_publication: PreparedPublication,
) -> None:
    api = _ConflictingCasApi(prepared_publication)

    with pytest.raises(PublicationConflict) as raised:
        publish_prepared_history_to_github(
            prepared_publication,
            api=api,
            snapshot_loader=_CandidateSnapshotLoader(prepared_publication),
        )

    assert raised.value.observed == "c" * 40
    assert len([call for call in api.calls if call[1] == "/graphql"]) == 1


class _UnreadableAfterCasApi(_ExactApi):
    def __init__(self, prepared: PreparedPublication) -> None:
        super().__init__(prepared)
        self._ref_reads = 0

    def request_json(
        self,
        method: str,
        path: str,
        *,
        payload: object | None = None,
    ) -> object:
        if method == "GET" and path.endswith("/git/ref/heads/main"):
            self._ref_reads += 1
            if self._ref_reads == 2:
                raise RuntimeError("authority unavailable")
        return super().request_json(method, path, payload=payload)


def test_unreadable_ref_after_cas_is_indeterminate(
    prepared_publication: PreparedPublication,
) -> None:
    api = _UnreadableAfterCasApi(prepared_publication)

    with pytest.raises(PublicationIndeterminate):
        publish_prepared_history_to_github(
            prepared_publication,
            api=api,
            snapshot_loader=_CandidateSnapshotLoader(prepared_publication),
        )

    assert api.current == prepared_publication.publication_commit


class _FailedSnapshotLoader:
    def load(
        self,
        repository: GitHubRepositoryIdentity,
        expected_head: str,
    ) -> PublishedHistory:
        raise RuntimeError(f"cannot fetch {repository.full_name} at {expected_head}")


def test_remote_reload_failure_blocks_success_after_cas(
    prepared_publication: PreparedPublication,
) -> None:
    api = _ExactApi(prepared_publication)

    with pytest.raises(PublishedReloadError):
        publish_prepared_history_to_github(
            prepared_publication,
            api=api,
            snapshot_loader=_FailedSnapshotLoader(),
        )

    assert api.current == prepared_publication.publication_commit


class _JsonResponse:
    def __init__(
        self,
        *,
        url: str,
        raw: bytes = b'{"ok":true}',
        status_code: int = 200,
        content_type: str = "application/json; charset=utf-8",
    ) -> None:
        self.url = url
        self.status_code = status_code
        self.headers = {
            "Content-Type": content_type,
            "Content-Length": str(len(raw)),
        }
        self._raw = raw

    def __enter__(self) -> _JsonResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def iter_content(self, *, chunk_size: int) -> tuple[bytes, ...]:
        assert chunk_size == 64 * 1024
        return (self._raw,)


def test_requests_github_api_uses_one_fixed_origin_and_scrubbed_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict[str, object] = {}

    def fake_request(
        session: requests.Session,
        method: str,
        url: str,
        **kwargs: object,
    ) -> _JsonResponse:
        observed.update(
            {
                "trust_env": session.trust_env,
                "authorization": session.headers.get("Authorization"),
                "accept_encoding": session.headers.get("Accept-Encoding"),
                "api_version": session.headers.get("X-GitHub-Api-Version"),
                "method": method,
                "url": url,
                **kwargs,
            }
        )
        return _JsonResponse(url=url)

    monkeypatch.setattr(requests.Session, "request", fake_request)

    response = RequestsGitHubApi("sentinel-token").request_json(
        "GET",
        "/repos/Jasper-Shi/lottopred",
    )

    assert response == {"ok": True}
    assert observed == {
        "trust_env": False,
        "authorization": "Bearer sentinel-token",
        "accept_encoding": "identity",
        "api_version": "2026-03-10",
        "method": "GET",
        "url": "https://api.github.com/repos/Jasper-Shi/lottopred",
        "allow_redirects": False,
        "stream": True,
        "timeout": (10, 30),
    }


@pytest.mark.parametrize(
    "token",
    ["", "has a space", "line\nbreak", "x" * 513],
)
def test_requests_github_api_rejects_an_invalid_token(token: str) -> None:
    with pytest.raises(GitHubPublicationError, match="credential"):
        RequestsGitHubApi(token)


def test_requests_github_api_rejects_an_absolute_or_traversing_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected_request(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("network must be unreachable")

    monkeypatch.setattr(requests.Session, "request", unexpected_request)
    api = RequestsGitHubApi("sentinel-token")

    for path in ("https://evil.invalid/", "/repos/../other"):
        with pytest.raises(GitHubPublicationError, match="path"):
            api.request_json("GET", path)


def test_requests_github_api_rejects_redirect_or_duplicate_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = iter(
        (
            _JsonResponse(
                url="https://api.github.com/repos/Jasper-Shi/lottopred",
                status_code=302,
            ),
            _JsonResponse(
                url="https://api.github.com/repos/Jasper-Shi/lottopred",
                raw=b'{"sha":"a","sha":"b"}',
            ),
        )
    )
    monkeypatch.setattr(
        requests.Session,
        "request",
        lambda *_args, **_kwargs: next(responses),
    )
    api = RequestsGitHubApi("sentinel-token")

    with pytest.raises(GitHubPublicationError, match="status"):
        api.request_json("GET", "/repos/Jasper-Shi/lottopred")
    with pytest.raises(GitHubPublicationError, match="JSON"):
        api.request_json("GET", "/repos/Jasper-Shi/lottopred")


def test_requests_github_api_rejects_untrusted_response_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wrong_url = _JsonResponse(url="https://evil.invalid/response")
    wrong_type = _JsonResponse(
        url="https://api.github.com/repos/Jasper-Shi/lottopred",
        content_type="text/html",
    )
    encoded = _JsonResponse(
        url="https://api.github.com/repos/Jasper-Shi/lottopred",
    )
    encoded.headers["Content-Encoding"] = "gzip"
    wrong_length = _JsonResponse(
        url="https://api.github.com/repos/Jasper-Shi/lottopred",
    )
    wrong_length.headers["Content-Length"] = "999"
    huge_length = _JsonResponse(
        url="https://api.github.com/repos/Jasper-Shi/lottopred",
    )
    huge_length.headers["Content-Length"] = "9" * 5_000
    responses = iter((wrong_url, wrong_type, encoded, wrong_length, huge_length))
    monkeypatch.setattr(
        requests.Session,
        "request",
        lambda *_args, **_kwargs: next(responses),
    )
    api = RequestsGitHubApi("sentinel-token")

    for pattern in ("URL", "JSON", "Content-Encoding", "length", "size"):
        with pytest.raises(GitHubPublicationError, match=pattern):
            api.request_json("GET", "/repos/Jasper-Shi/lottopred")


@pytest.mark.parametrize(
    "raw",
    [b'{"value":NaN}', b'{"value":1e999}'],
)
def test_requests_github_api_rejects_nonfinite_numeric_json(
    monkeypatch: pytest.MonkeyPatch,
    raw: bytes,
) -> None:
    url = "https://api.github.com/repos/Jasper-Shi/lottopred"
    monkeypatch.setattr(
        requests.Session,
        "request",
        lambda *_args, **_kwargs: _JsonResponse(url=url, raw=raw),
    )

    with pytest.raises(GitHubPublicationError, match="JSON"):
        RequestsGitHubApi("sentinel-token").request_json(
            "GET",
            "/repos/Jasper-Shi/lottopred",
        )


def test_requests_github_api_does_not_expose_token_on_transport_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = "sentinel-token-must-not-leak"

    def failed_request(*_args: object, **_kwargs: object) -> object:
        raise requests.ConnectionError(token)

    monkeypatch.setattr(requests.Session, "request", failed_request)

    with pytest.raises(GitHubPublicationError) as raised:
        RequestsGitHubApi(token).request_json(
            "GET",
            "/repos/Jasper-Shi/lottopred",
        )

    assert token not in str(raised.value)
    assert raised.value.__cause__ is None


def test_fresh_loader_fetches_exact_public_main_into_a_new_bare_repository(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "sentinel-token-must-not-reach-git")
    monkeypatch.setenv("GH_TOKEN", "another-sentinel-token")
    expected_head = _git_text(ROOT, "rev-parse", "HEAD")
    source_bare = tmp_path / "source.git"
    subprocess.run(
        ["git", "clone", "--bare", "--quiet", str(ROOT), str(source_bare)],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        [
            "git",
            "-C",
            str(source_bare),
            "update-ref",
            "refs/heads/main",
            expected_head,
        ],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        [
            "git",
            "-C",
            str(source_bare),
            "symbolic-ref",
            "HEAD",
            "refs/heads/main",
        ],
        check=True,
        capture_output=True,
    )
    real_run = subprocess.run
    temporary_repositories: list[Path] = []
    fetch_environments: list[dict[str, str]] = []

    def local_fetch_run(
        arguments: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[Any]:
        rewritten = list(arguments)
        if "https://github.com/Jasper-Shi/lottopred.git" in rewritten:
            index = rewritten.index("https://github.com/Jasper-Shi/lottopred.git")
            rewritten[index] = str(source_bare)
            temporary_repositories.append(Path(rewritten[rewritten.index("-C") + 1]))
            environment = kwargs.get("env")
            assert isinstance(environment, dict)
            fetch_environments.append(environment)
        return real_run(rewritten, **kwargs)

    monkeypatch.setattr(subprocess, "run", local_fetch_run)

    history = FreshBareGitHubSnapshotLoader().load(REPOSITORY, expected_head)

    assert history.registry.resolved_revision == expected_head
    assert len(history.draws) == 4_444
    assert len(temporary_repositories) == 1
    assert len(fetch_environments) == 1
    assert "GITHUB_TOKEN" not in fetch_environments[0]
    assert "GH_TOKEN" not in fetch_environments[0]
    assert fetch_environments[0]["GIT_TERMINAL_PROMPT"] == "0"
    assert temporary_repositories[0] != ROOT
    assert not temporary_repositories[0].exists()
