from __future__ import annotations

import base64
import hashlib
import os
import subprocess
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from threading import Event, Lock, Thread, get_ident
from typing import Iterator

import pytest

import lotto649.history_artifact_publication_github as artifact_publication
import lotto649.history_execution_handoff as execution_handoff
from lotto649.history_artifact_publication_github import (
    ArtifactPublicationReceipt,
    _publish_with_ports,
    publish_frozen_execution_artifacts_to_github,
)
from lotto649.history_execution_handoff import (
    FrozenExecutionArtifacts,
    FrozenExecutionFile,
    HistoryExecutionHandoffError,
    _issue_frozen_execution_artifacts,
    _open_execution_workspace,
)
from lotto649.history_publication_cas import (
    CasAck,
    CasStatus,
    PreparationIntegrityError,
    PublicationOutcome,
    PublicationIndeterminate,
    PublicationConflict,
    PublicationReceipt,
    PublishedReloadError,
    StalePublication,
)
from lotto649.history_publication_github import (
    PRODUCTION_GITHUB_REPOSITORY,
    GitHubPublicationError,
)
from lotto649.operational_history import PublishedHistory, load_published_history

ROOT = Path(__file__).resolve().parents[1]
PREDICTION_PATH = "predictions/2026-08-26__publisher_fixture__v1.0.0.json"
PREDICTION_RAW = b'{"fixture":"exact artifact bytes"}\n'


def _git(
    repository: Path,
    *arguments: str,
    input_bytes: bytes | None = None,
    environment: dict[str, str] | None = None,
) -> bytes:
    return subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        input=input_bytes,
        env=environment,
    ).stdout


@dataclass(frozen=True)
class ArtifactFixture:
    artifacts: FrozenExecutionArtifacts
    history: PublishedHistory
    raw_commit: bytes
    parent_tree: str


@contextmanager
def _artifact_fixture(tmp_path: Path) -> Iterator[ArtifactFixture]:
    head = _git(ROOT, "rev-parse", "HEAD").decode("ascii").strip()
    transparent = load_published_history(ROOT, head)
    publication = transparent.registry.publication_commit
    history = load_published_history(ROOT, publication)
    receipt = PublicationReceipt(
        expected_base=history.registry_transaction.base_commit,
        publication_commit=publication,
        observed_before=history.registry_transaction.base_commit,
        observed_after=publication,
        cas_ack=CasAck(CasStatus.APPLIED),
        outcome=PublicationOutcome.ADVANCED,
        history=history,
    )
    authority = tmp_path / "authority.git"
    subprocess.run(
        ["git", "init", "--bare", "--quiet", str(authority)],
        check=True,
        capture_output=True,
    )
    _git(ROOT, "push", "--quiet", str(authority), f"{publication}:refs/heads/main")
    _git(authority, "symbolic-ref", "HEAD", "refs/heads/main")

    with _open_execution_workspace(receipt, authority_url=str(authority)) as workspace:
        blob = (
            _git(
                workspace.root,
                "hash-object",
                "-w",
                "--stdin",
                input_bytes=PREDICTION_RAW,
            )
            .decode("ascii")
            .strip()
        )
        index = tmp_path / "artifact-index"
        index_environment = os.environ.copy()
        index_environment["GIT_INDEX_FILE"] = str(index)
        _git(
            workspace.root,
            "read-tree",
            publication,
            environment=index_environment,
        )
        _git(
            workspace.root,
            "update-index",
            "--add",
            "--cacheinfo",
            "100644",
            blob,
            PREDICTION_PATH,
            environment=index_environment,
        )
        tree = (
            _git(workspace.root, "write-tree", environment=index_environment)
            .decode("ascii")
            .strip()
        )
        created_at = datetime(2026, 8, 24, 12, tzinfo=UTC)
        git_timestamp = created_at.strftime("%Y-%m-%dT%H:%M:%S+00:00")
        commit_environment = os.environ.copy()
        commit_environment.update(
            {
                "GIT_AUTHOR_DATE": git_timestamp,
                "GIT_AUTHOR_EMAIL": "live-artifacts@lotto649.invalid",
                "GIT_AUTHOR_NAME": "LOTTO 6/49 Live Artifact Writer",
                "GIT_COMMITTER_DATE": git_timestamp,
                "GIT_COMMITTER_EMAIL": "live-artifacts@lotto649.invalid",
                "GIT_COMMITTER_NAME": "LOTTO 6/49 Live Artifact Writer",
            }
        )
        artifact_commit = (
            _git(
                workspace.root,
                "commit-tree",
                tree,
                "-p",
                publication,
                input_bytes=b"chore: record verified lotto649 live artifacts\n",
                environment=commit_environment,
            )
            .decode("ascii")
            .strip()
        )
        artifacts = _issue_frozen_execution_artifacts(
            workspace,
            repository=workspace.root,
            parent_commit=publication,
            tree_oid=tree,
            artifact_commit=artifact_commit,
            paths=(PREDICTION_PATH,),
            files=(
                FrozenExecutionFile(
                    path=PREDICTION_PATH,
                    bytes=len(PREDICTION_RAW),
                    sha256=hashlib.sha256(PREDICTION_RAW).hexdigest(),
                    git_blob=blob,
                ),
            ),
            created_at=created_at,
        )
        yield ArtifactFixture(
            artifacts=artifacts,
            history=history,
            raw_commit=_git(workspace.root, "cat-file", "commit", artifact_commit),
            parent_tree=(
                _git(workspace.root, "show", "-s", "--format=%T", publication)
                .decode("ascii")
                .strip()
            ),
        )


class FakeGitHubApi:
    def __init__(
        self,
        fixture: ArtifactFixture,
        *,
        initial_head: str | None = None,
        cas_behavior: str = "advance",
        mismatched_upload: str | None = None,
    ) -> None:
        self.fixture = fixture
        self.head = initial_head or fixture.artifacts.parent_commit
        self.cas_behavior = cas_behavior
        self.mismatched_upload = mismatched_upload
        self.calls: list[tuple[str, str, object | None]] = []
        self.ref_reads = 0

    def request_json(
        self,
        method: str,
        path: str,
        *,
        payload: object | None = None,
    ) -> object:
        self.calls.append((method, path, payload))
        if (method, path) == ("GET", "/repos/Jasper-Shi/lottopred"):
            return {
                "node_id": PRODUCTION_GITHUB_REPOSITORY.node_id,
                "full_name": "Jasper-Shi/lottopred",
                "default_branch": "main",
                "private": False,
            }
        if (method, path) == (
            "GET",
            "/repos/Jasper-Shi/lottopred/hash-algorithm",
        ):
            return {"hash_algorithm": "sha1"}
        if (method, path) == (
            "GET",
            "/repos/Jasper-Shi/lottopred/branches/main/protection",
        ):
            return {
                "enforce_admins": {"enabled": True},
                "allow_force_pushes": {"enabled": False},
                "allow_deletions": {"enabled": False},
            }
        if (method, path) == (
            "GET",
            "/repos/Jasper-Shi/lottopred/git/ref/heads/main",
        ):
            self.ref_reads += 1
            if self.cas_behavior == "unreadable" and self.ref_reads > 1:
                raise OSError("simulated unreadable authoritative ref")
            return {
                "ref": "refs/heads/main",
                "object": {"type": "commit", "sha": self.head},
            }
        if (method, path) == (
            "POST",
            "/repos/Jasper-Shi/lottopred/git/blobs",
        ):
            return {
                "sha": (
                    "0" * 40
                    if self.mismatched_upload == "blob"
                    else self.fixture.artifacts.files[0].git_blob
                )
            }
        if (method, path) == (
            "POST",
            "/repos/Jasper-Shi/lottopred/git/trees",
        ):
            return {
                "sha": (
                    "0" * 40
                    if self.mismatched_upload == "tree"
                    else self.fixture.artifacts.tree_oid
                )
            }
        if (method, path) == (
            "POST",
            "/repos/Jasper-Shi/lottopred/git/commits",
        ):
            return {
                "sha": (
                    "0" * 40
                    if self.mismatched_upload == "commit"
                    else self.fixture.artifacts.artifact_commit
                )
            }
        if (method, path) == (
            "GET",
            "/repos/Jasper-Shi/lottopred/git/commits/"
            + self.fixture.artifacts.artifact_commit,
        ):
            return {"sha": self.fixture.artifacts.artifact_commit}
        if (method, path) == ("POST", "/graphql"):
            if self.cas_behavior in {"advance", "unknown_advance", "raise_advance"}:
                self.head = self.fixture.artifacts.artifact_commit
            elif self.cas_behavior == "third":
                self.head = "f" * 40
            elif self.cas_behavior not in {"stay", "unreadable"}:
                raise AssertionError(f"unknown CAS behavior: {self.cas_behavior}")
            if self.cas_behavior == "unknown_advance":
                return {"errors": [{"message": "ambiguous acknowledgement"}]}
            if self.cas_behavior == "raise_advance":
                raise OSError("simulated lost acknowledgement")
            return {
                "data": {
                    "updateRefs": {
                        "clientMutationId": (
                            "artifact-publication:"
                            + self.fixture.artifacts.artifact_commit
                        )
                    }
                }
            }
        raise AssertionError(f"unexpected API call: {(method, path, payload)!r}")


class ThreadRecordingGitHubApi(FakeGitHubApi):
    def __init__(self, fixture: ArtifactFixture) -> None:
        super().__init__(fixture)
        self.calling_threads: list[int] = []
        self._calls_lock = Lock()

    def request_json(
        self,
        method: str,
        path: str,
        *,
        payload: object | None = None,
    ) -> object:
        with self._calls_lock:
            self.calling_threads.append(get_ident())
        return super().request_json(method, path, payload=payload)


class FakeArtifactVerifier:
    def __init__(self, fixture: ArtifactFixture, *, fail: bool = False) -> None:
        self.fixture = fixture
        self.fail = fail
        self.calls: list[tuple[object, object]] = []

    def verify(self, repository: object, plan: object) -> PublishedHistory:
        self.calls.append((repository, plan))
        if self.fail:
            raise OSError("simulated fresh fetch failure")
        return load_published_history(
            self.fixture.artifacts.repository,
            self.fixture.artifacts.artifact_commit,
        )


def test_publication_requires_an_active_freeze_capability() -> None:
    with pytest.raises(HistoryExecutionHandoffError, match="freeze capability"):
        publish_frozen_execution_artifacts_to_github(object(), token="sentinel-token")


def test_exact_artifact_commit_advances_fixed_main_once_and_is_freshly_verified(
    tmp_path: Path,
) -> None:
    with _artifact_fixture(tmp_path) as fixture:
        api = FakeGitHubApi(fixture)
        verifier = FakeArtifactVerifier(fixture)

        receipt = _publish_with_ports(
            fixture.artifacts,
            api=api,
            artifact_verifier=verifier,
        )

        assert receipt == ArtifactPublicationReceipt(
            expected_parent=fixture.artifacts.parent_commit,
            artifact_commit=fixture.artifacts.artifact_commit,
            observed_before=fixture.artifacts.parent_commit,
            observed_after=fixture.artifacts.artifact_commit,
            cas_ack=CasAck(CasStatus.APPLIED),
            outcome=PublicationOutcome.ADVANCED,
            history=load_published_history(
                fixture.artifacts.repository,
                fixture.artifacts.artifact_commit,
            ),
        )
        graphql = [call for call in api.calls if call[:2] == ("POST", "/graphql")]
        assert graphql == [
            (
                "POST",
                "/graphql",
                {
                    "query": (
                        "mutation UpdateArtifactRef($input: UpdateRefsInput!) {\n"
                        "  updateRefs(input: $input) {\n"
                        "    clientMutationId\n"
                        "  }\n"
                        "}"
                    ),
                    "variables": {
                        "input": {
                            "repositoryId": PRODUCTION_GITHUB_REPOSITORY.node_id,
                            "refUpdates": [
                                {
                                    "name": "refs/heads/main",
                                    "beforeOid": fixture.artifacts.parent_commit,
                                    "afterOid": fixture.artifacts.artifact_commit,
                                    "force": False,
                                }
                            ],
                            "clientMutationId": (
                                "artifact-publication:"
                                + fixture.artifacts.artifact_commit
                            ),
                        }
                    },
                },
            )
        ]
        assert len(verifier.calls) == 1
        blob_payload = next(
            call[2]
            for call in api.calls
            if call[:2] == ("POST", "/repos/Jasper-Shi/lottopred/git/blobs")
        )
        assert blob_payload == {
            "content": base64.b64encode(PREDICTION_RAW).decode("ascii"),
            "encoding": "base64",
        }
        tree_payload = next(
            call[2]
            for call in api.calls
            if call[:2] == ("POST", "/repos/Jasper-Shi/lottopred/git/trees")
        )
        assert tree_payload == {
            "base_tree": fixture.parent_tree,
            "tree": [
                {
                    "path": PREDICTION_PATH,
                    "mode": "100644",
                    "type": "blob",
                    "sha": fixture.artifacts.files[0].git_blob,
                }
            ],
        }
        signature = {
            "name": "LOTTO 6/49 Live Artifact Writer",
            "email": "live-artifacts@lotto649.invalid",
            "date": "2026-08-24T12:00:00Z",
        }
        commit_payload = next(
            call[2]
            for call in api.calls
            if call[:2] == ("POST", "/repos/Jasper-Shi/lottopred/git/commits")
        )
        assert commit_payload == {
            "message": "chore: record verified lotto649 live artifacts\n",
            "tree": fixture.artifacts.tree_oid,
            "parents": [fixture.artifacts.parent_commit],
            "author": signature,
            "committer": signature,
        }


def test_already_published_artifact_is_freshly_verified_without_any_write(
    tmp_path: Path,
) -> None:
    with _artifact_fixture(tmp_path) as fixture:
        api = FakeGitHubApi(
            fixture,
            initial_head=fixture.artifacts.artifact_commit,
        )
        verifier = FakeArtifactVerifier(fixture)

        receipt = _publish_with_ports(
            fixture.artifacts,
            api=api,
            artifact_verifier=verifier,
        )

        assert receipt.outcome is PublicationOutcome.ALREADY_PUBLISHED
        assert receipt.cas_ack is None
        assert receipt.observed_before == fixture.artifacts.artifact_commit
        assert len(verifier.calls) == 1
        assert all(method == "GET" for method, _path, _payload in api.calls)


def test_one_capability_never_retries_a_cas_or_object_upload(
    tmp_path: Path,
) -> None:
    with _artifact_fixture(tmp_path) as fixture:
        api = FakeGitHubApi(fixture, cas_behavior="stay")
        verifier = FakeArtifactVerifier(fixture)

        with pytest.raises(PublicationIndeterminate):
            _publish_with_ports(
                fixture.artifacts,
                api=api,
                artifact_verifier=verifier,
            )
        writes_after_first_attempt = [call for call in api.calls if call[0] == "POST"]

        with pytest.raises(PublicationIndeterminate):
            _publish_with_ports(
                fixture.artifacts,
                api=api,
                artifact_verifier=verifier,
            )

        assert [call for call in api.calls if call[0] == "POST"] == (
            writes_after_first_attempt
        )
        assert sum(call[:2] == ("POST", "/graphql") for call in api.calls) == 1


def test_one_capability_allows_only_one_concurrent_remote_publication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _artifact_fixture(tmp_path) as fixture:
        api = ThreadRecordingGitHubApi(fixture)
        verifier = FakeArtifactVerifier(fixture)
        first_upload_entered = Event()
        release_first_upload = Event()
        upload_lock = Lock()
        upload_threads: list[int] = []
        original_upload = artifact_publication._upload_plan

        def blocking_upload(plan: object, target_api: object) -> None:
            with upload_lock:
                upload_threads.append(get_ident())
                first = len(upload_threads) == 1
            if first:
                first_upload_entered.set()
                assert release_first_upload.wait(timeout=30)
            original_upload(plan, target_api)

        monkeypatch.setattr(artifact_publication, "_upload_plan", blocking_upload)
        receipts: list[ArtifactPublicationReceipt] = []
        errors: list[BaseException] = []

        def publish() -> None:
            try:
                receipts.append(
                    _publish_with_ports(
                        fixture.artifacts,
                        api=api,
                        artifact_verifier=verifier,
                    )
                )
            except BaseException as exc:  # noqa: BLE001 - thread result capture
                errors.append(exc)

        first = Thread(target=publish)
        second = Thread(target=publish)
        first.start()
        assert first_upload_entered.wait(timeout=30)
        second.start()
        second.join(timeout=30)
        release_first_upload.set()
        first.join(timeout=30)
        second.join(timeout=30)

        assert not first.is_alive()
        assert not second.is_alive()
        assert len(receipts) == 1
        assert len(errors) == 1
        assert isinstance(errors[0], HistoryExecutionHandoffError)
        assert len(set(api.calling_threads)) == 1
        assert len(upload_threads) == 1
        assert sum(call[:2] == ("POST", "/graphql") for call in api.calls) == 1


def test_workspace_revocation_waits_for_the_active_publication_lease(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture_context = _artifact_fixture(tmp_path)
    fixture = fixture_context.__enter__()
    api = FakeGitHubApi(fixture)
    verifier = FakeArtifactVerifier(fixture)
    upload_entered = Event()
    release_upload = Event()
    revoke_entered = Event()
    close_finished = Event()
    original_upload = artifact_publication._upload_plan
    original_revoke = execution_handoff._revoke_frozen_artifacts
    receipts: list[ArtifactPublicationReceipt] = []
    publish_errors: list[BaseException] = []
    close_errors: list[BaseException] = []

    def blocking_upload(plan: object, target_api: object) -> None:
        upload_entered.set()
        assert release_upload.wait(timeout=30)
        original_upload(plan, target_api)

    def observed_revoke(workspace_capability: object) -> None:
        revoke_entered.set()
        original_revoke(workspace_capability)

    def publish() -> None:
        try:
            receipts.append(
                _publish_with_ports(
                    fixture.artifacts,
                    api=api,
                    artifact_verifier=verifier,
                )
            )
        except BaseException as exc:  # noqa: BLE001 - thread result capture
            publish_errors.append(exc)

    def close_context() -> None:
        try:
            fixture_context.__exit__(None, None, None)
        except BaseException as exc:  # noqa: BLE001 - thread result capture
            close_errors.append(exc)
        finally:
            close_finished.set()

    monkeypatch.setattr(artifact_publication, "_upload_plan", blocking_upload)
    monkeypatch.setattr(execution_handoff, "_revoke_frozen_artifacts", observed_revoke)
    publisher = Thread(target=publish)
    closer = Thread(target=close_context)
    publisher.start()
    try:
        assert upload_entered.wait(timeout=30)
        closer.start()
        assert revoke_entered.wait(timeout=30)
        assert not close_finished.wait(timeout=1)
    finally:
        release_upload.set()
    publisher.join(timeout=30)
    closer.join(timeout=30)

    assert not publisher.is_alive()
    assert not closer.is_alive()
    assert publish_errors == []
    assert close_errors == []
    assert len(receipts) == 1
    assert receipts[0].outcome is PublicationOutcome.ADVANCED
    assert sum(call[:2] == ("POST", "/graphql") for call in api.calls) == 1


@pytest.mark.parametrize("marker", ["commondir", "promisor"])
def test_post_freeze_git_indirection_markers_fail_before_remote_requests(
    tmp_path: Path,
    marker: str,
) -> None:
    with _artifact_fixture(tmp_path) as fixture:
        git_directory = fixture.artifacts.repository / ".git"
        if marker == "commondir":
            (git_directory / "commondir").write_text(
                f"{git_directory}\n",
                encoding="utf-8",
            )
        else:
            (git_directory / "objects" / "pack" / "post-freeze.promisor").touch()
        api = FakeGitHubApi(fixture)

        with pytest.raises(PreparationIntegrityError, match="self-contained"):
            _publish_with_ports(
                fixture.artifacts,
                api=api,
                artifact_verifier=FakeArtifactVerifier(fixture),
            )

        assert api.calls == []


def test_local_tree_identity_tampering_fails_before_any_remote_request(
    tmp_path: Path,
) -> None:
    with _artifact_fixture(tmp_path) as fixture:
        object.__setattr__(fixture.artifacts, "tree_oid", "f" * 40)
        api = FakeGitHubApi(fixture)

        with pytest.raises(HistoryExecutionHandoffError, match="freeze capability"):
            _publish_with_ports(
                fixture.artifacts,
                api=api,
                artifact_verifier=FakeArtifactVerifier(fixture),
            )

        assert api.calls == []


def test_local_file_size_sha_and_blob_identity_are_all_revalidated_before_network(
    tmp_path: Path,
) -> None:
    with _artifact_fixture(tmp_path) as fixture:
        file = fixture.artifacts.files[0]
        cases = (
            ("bytes", file.bytes + 1),
            ("sha256", "f" * 64),
            ("git_blob", "f" * 40),
        )
        for field, invalid in cases:
            original = getattr(file, field)
            object.__setattr__(file, field, invalid)
            api = FakeGitHubApi(fixture)

            with pytest.raises(HistoryExecutionHandoffError, match="freeze capability"):
                _publish_with_ports(
                    fixture.artifacts,
                    api=api,
                    artifact_verifier=FakeArtifactVerifier(fixture),
                )

            assert api.calls == []
            object.__setattr__(file, field, original)


@pytest.mark.parametrize("mismatch", ["blob", "tree", "commit"])
def test_remote_object_identity_mismatch_fails_before_cas(
    tmp_path: Path,
    mismatch: str,
) -> None:
    with _artifact_fixture(tmp_path) as fixture:
        api = FakeGitHubApi(fixture, mismatched_upload=mismatch)

        with pytest.raises(GitHubPublicationError, match="identity"):
            _publish_with_ports(
                fixture.artifacts,
                api=api,
                artifact_verifier=FakeArtifactVerifier(fixture),
            )

        assert all(call[:2] != ("POST", "/graphql") for call in api.calls)


@pytest.mark.parametrize("cas_behavior", ["unknown_advance", "raise_advance"])
def test_lost_or_invalid_cas_ack_is_confirmed_only_by_reread_and_fresh_fetch(
    tmp_path: Path,
    cas_behavior: str,
) -> None:
    with _artifact_fixture(tmp_path) as fixture:
        api = FakeGitHubApi(fixture, cas_behavior=cas_behavior)
        verifier = FakeArtifactVerifier(fixture)

        receipt = _publish_with_ports(
            fixture.artifacts,
            api=api,
            artifact_verifier=verifier,
        )

        assert receipt.outcome is PublicationOutcome.CONFIRMED_AFTER_REREAD
        assert receipt.cas_ack == CasAck(CasStatus.UNKNOWN)
        assert api.ref_reads == 2
        assert len(verifier.calls) == 1


@pytest.mark.parametrize(
    ("cas_behavior", "error_type"),
    [
        ("stay", PublicationIndeterminate),
        ("unreadable", PublicationIndeterminate),
        ("third", PublicationConflict),
    ],
)
def test_every_non_a_post_cas_state_fails_closed(
    tmp_path: Path,
    cas_behavior: str,
    error_type: type[Exception],
) -> None:
    with _artifact_fixture(tmp_path) as fixture:
        api = FakeGitHubApi(fixture, cas_behavior=cas_behavior)
        verifier = FakeArtifactVerifier(fixture)

        with pytest.raises(error_type):
            _publish_with_ports(
                fixture.artifacts,
                api=api,
                artifact_verifier=verifier,
            )

        assert sum(call[:2] == ("POST", "/graphql") for call in api.calls) == 1
        assert verifier.calls == []


def test_unrelated_initial_head_is_stale_and_never_written(
    tmp_path: Path,
) -> None:
    with _artifact_fixture(tmp_path) as fixture:
        api = FakeGitHubApi(fixture, initial_head="e" * 40)

        with pytest.raises(StalePublication):
            _publish_with_ports(
                fixture.artifacts,
                api=api,
                artifact_verifier=FakeArtifactVerifier(fixture),
            )

        assert all(method == "GET" for method, _path, _payload in api.calls)


def test_fresh_artifact_verification_failure_never_returns_success(
    tmp_path: Path,
) -> None:
    with _artifact_fixture(tmp_path) as fixture:
        api = FakeGitHubApi(fixture)

        with pytest.raises(PublishedReloadError):
            _publish_with_ports(
                fixture.artifacts,
                api=api,
                artifact_verifier=FakeArtifactVerifier(fixture, fail=True),
            )

        assert api.head == fixture.artifacts.artifact_commit


def test_fresh_bare_repository_proves_exact_a_and_rejects_wrong_ref_or_bytes(
    tmp_path: Path,
) -> None:
    with _artifact_fixture(tmp_path) as fixture:
        api = FakeGitHubApi(
            fixture,
            initial_head=fixture.artifacts.artifact_commit,
        )
        capturing_verifier = FakeArtifactVerifier(fixture)
        _publish_with_ports(
            fixture.artifacts,
            api=api,
            artifact_verifier=capturing_verifier,
        )
        plan = capturing_verifier.calls[0][1]
        authority = tmp_path / "fresh-authority.git"
        subprocess.run(
            ["git", "init", "--bare", "--quiet", str(authority)],
            check=True,
            capture_output=True,
        )
        _git(
            fixture.artifacts.repository,
            "push",
            "--quiet",
            str(authority),
            f"{fixture.artifacts.artifact_commit}:refs/heads/main",
        )
        _git(authority, "symbolic-ref", "HEAD", "refs/heads/main")

        history = artifact_publication._verify_plan_in_repository(authority, plan)

        assert history.registry.resolved_revision == fixture.artifacts.artifact_commit
        assert history.registry.publication_commit == fixture.artifacts.parent_commit

        _git(
            authority,
            "update-ref",
            "refs/heads/main",
            fixture.artifacts.parent_commit,
        )
        with pytest.raises(GitHubPublicationError, match="main identity"):
            artifact_publication._verify_plan_in_repository(authority, plan)
        _git(
            authority,
            "update-ref",
            "refs/heads/main",
            fixture.artifacts.artifact_commit,
        )
        wrong_file = replace(plan.files[0], raw=b"different remote bytes\n")
        wrong_plan = replace(plan, files=(wrong_file,))
        with pytest.raises(GitHubPublicationError, match="file mismatch"):
            artifact_publication._verify_plan_in_repository(authority, wrong_plan)


def test_expired_freeze_capability_fails_before_any_remote_request(
    tmp_path: Path,
) -> None:
    with _artifact_fixture(tmp_path) as fixture:
        artifacts = fixture.artifacts
        api = FakeGitHubApi(fixture)
        verifier = FakeArtifactVerifier(fixture)

    with pytest.raises(HistoryExecutionHandoffError, match="freeze capability"):
        _publish_with_ports(
            artifacts,
            api=api,
            artifact_verifier=verifier,
        )

    assert api.calls == []


def test_capability_is_rechecked_after_fresh_remote_verification(
    tmp_path: Path,
) -> None:
    with _artifact_fixture(tmp_path) as fixture:
        api = FakeGitHubApi(fixture)

        class MutatingVerifier(FakeArtifactVerifier):
            def verify(self, repository: object, plan: object) -> PublishedHistory:
                history = super().verify(repository, plan)
                object.__setattr__(
                    self.fixture.artifacts,
                    "parent_commit",
                    "f" * 40,
                )
                return history

        with pytest.raises(HistoryExecutionHandoffError, match="capability"):
            _publish_with_ports(
                fixture.artifacts,
                api=api,
                artifact_verifier=MutatingVerifier(fixture),
            )

        assert api.head == fixture.artifacts.artifact_commit
