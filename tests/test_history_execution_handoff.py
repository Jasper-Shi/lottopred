from __future__ import annotations

import json
import os
import subprocess
from contextlib import contextmanager
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest

import lotto649.history_execution_handoff as history_handoff
from lotto649.domain import Prediction
from lotto649.evaluation import evaluate_prediction
from lotto649.history_execution_handoff import (
    ExecutionWorkspace,
    HistoryExecutionHandoffError,
    _open_execution_workspace,
)
from lotto649.history_publication import (
    RawSource,
    prepare_history_publication,
)
from lotto649.history_publication_cas import (
    CasAck,
    CasStatus,
    PublicationOutcome,
    PublicationReceipt,
)
from lotto649.operational_history import (
    load_published_history,
    operational_history_provenance,
)

ROOT = Path(__file__).resolve().parents[1]


def _git(repository: Path, *arguments: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
    )


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


def _prediction_payload(
    history,
    target: date,
    generated_at: datetime,
    *,
    model_name: str = "model",
    model_version: str = "v1.0.0",
    role: str = "primary",
) -> dict[str, object]:
    probabilities = {str(number): 6 / 49 for number in range(1, 50)}
    return {
        "final_combination": [1, 2, 3, 4, 5, 6],
        "generated_at": generated_at.isoformat(),
        "metadata": {
            "history_draws": len(history.draws),
            "history_through": history.draws[-1].draw_date.isoformat(),
            "operational_history": operational_history_provenance(history),
            "role": role,
        },
        "model_name": model_name,
        "model_version": model_version,
        "probabilities": probabilities,
        "target_draw_date": target.isoformat(),
        "top6": [1, 2, 3, 4, 5, 6],
        "top12": list(range(1, 13)),
        "top18": list(range(1, 19)),
    }


def _prediction_from_payload(payload: dict[str, object]) -> Prediction:
    return Prediction(
        target_draw_date=date.fromisoformat(payload["target_draw_date"]),
        generated_at=datetime.fromisoformat(payload["generated_at"]),
        model_name=payload["model_name"],
        model_version=payload["model_version"],
        probabilities={
            int(number): probability
            for number, probability in payload["probabilities"].items()
        },
        top6=payload["top6"],
        top12=payload["top12"],
        top18=payload["top18"],
        final_combination=payload["final_combination"],
        metadata=payload["metadata"],
    )


def _write_json(path: Path, payload: dict[str, object]) -> bytes:
    raw = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    path.parent.mkdir(exist_ok=True)
    path.write_bytes(raw)
    return raw


def _write_valid_prediction(
    workspace: ExecutionWorkspace,
    created_at: datetime,
    *,
    model_name: str = "model",
    model_version: str = "v1.0.0",
    role: str = "primary",
) -> tuple[str, bytes]:
    target = _next_draw_date(workspace.history.draws[-1].draw_date)
    relative = f"predictions/{target.isoformat()}__{model_name}__{model_version}.json"
    raw = _write_json(
        workspace.root / relative,
        _prediction_payload(
            workspace.history,
            target,
            created_at,
            model_name=model_name,
            model_version=model_version,
            role=role,
        ),
    )
    return relative, raw


def _write_required_predictions(
    workspace: ExecutionWorkspace,
    created_at: datetime,
) -> tuple[tuple[str, ...], tuple[bytes, ...]]:
    config = workspace.load_config()
    models = config["live"]["models"]
    shadow_models = set(config["live"]["shadow_models"])
    model_version = config["project"]["model_version"]
    written = tuple(
        _write_valid_prediction(
            workspace,
            created_at,
            model_name=model,
            model_version=model_version,
            role="shadow" if model in shadow_models else "primary",
        )
        for model in models
    )
    return (
        tuple(path for path, _raw in written),
        tuple(raw for _path, raw in written),
    )


def _write_valid_evaluation(
    workspace: ExecutionWorkspace,
    *,
    model_name: str = "handoff_fixture",
) -> tuple[str, bytes]:
    target = workspace.history.draws[-1].draw_date
    prediction_path = (
        workspace.root
        / "predictions"
        / f"{target.isoformat()}__{model_name}__v1.0.0.json"
    )
    prediction_payload = json.loads(prediction_path.read_text(encoding="utf-8"))
    actual = next(draw for draw in workspace.history.draws if draw.draw_date == target)
    evaluation = evaluate_prediction(
        _prediction_from_payload(prediction_payload),
        actual,
    )
    evaluation["actual_history"] = operational_history_provenance(workspace.history)
    relative = f"evaluations/{target.isoformat()}__{model_name}__v1.0.0.json"
    return relative, _write_json(workspace.root / relative, evaluation)


def _candidate(
    tmp_path: Path,
    *,
    base_symlink: bool = False,
    source_prediction_after_draw: bool = False,
):
    repository = tmp_path / "caller"
    subprocess.run(
        ["git", "clone", "--no-local", "--quiet", str(ROOT), str(repository)],
        check=True,
        capture_output=True,
    )
    if base_symlink:
        (repository / "unsafe-link").symlink_to("README.md")
        _git(repository, "add", "unsafe-link")
        subprocess.run(
            [
                "git",
                "-C",
                str(repository),
                "-c",
                "user.name=handoff-test",
                "-c",
                "user.email=handoff-test@lotto649.invalid",
                "commit",
                "--quiet",
                "-m",
                "add unsafe execution symlink",
            ],
            check=True,
            capture_output=True,
        )
    initial = _git(repository, "rev-parse", "HEAD").stdout.decode().strip()
    base_history = load_published_history(repository, initial)
    target = _next_draw_date(base_history.draws[-1].draw_date)
    generated_at = datetime.combine(
        target + timedelta(days=1 if source_prediction_after_draw else -1),
        datetime.min.time(),
        UTC,
    ).replace(hour=12)
    prediction = _prediction_payload(
        base_history,
        target,
        generated_at,
        model_name="handoff_fixture",
    )
    prediction_path = (
        repository
        / "predictions"
        / f"{target.isoformat()}__handoff_fixture__v1.0.0.json"
    )
    _write_json(prediction_path, prediction)
    _git(repository, "add", str(prediction_path.relative_to(repository)))
    prediction_commit_at = generated_at + timedelta(minutes=1)
    commit_environment = os.environ.copy()
    commit_environment.update(
        {
            "GIT_AUTHOR_DATE": prediction_commit_at.isoformat(),
            "GIT_COMMITTER_DATE": prediction_commit_at.isoformat(),
        }
    )
    subprocess.run(
        [
            "git",
            "-C",
            str(repository),
            "-c",
            "user.name=handoff-test",
            "-c",
            "user.email=handoff-test@lotto649.invalid",
            "commit",
            "--quiet",
            "-m",
            "add fixture pre-draw prediction",
        ],
        check=True,
        capture_output=True,
        env=commit_environment,
    )
    base = _git(repository, "rev-parse", "HEAD").stdout.decode().strip()
    created_at = datetime.combine(
        target + timedelta(days=2 if source_prediction_after_draw else 1),
        datetime.min.time(),
        UTC,
    ).replace(hour=12)
    prepared = prepare_history_publication(
        repository,
        expected_base_commit=base,
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
    published = load_published_history(repository, prepared.publication_commit)
    receipt = PublicationReceipt(
        expected_base=prepared.base_commit,
        publication_commit=prepared.publication_commit,
        observed_before=prepared.base_commit,
        observed_after=prepared.publication_commit,
        cas_ack=CasAck(CasStatus.APPLIED),
        outcome=PublicationOutcome.ADVANCED,
        history=published,
    )
    authority = tmp_path / "authority.git"
    subprocess.run(
        ["git", "init", "--bare", "--quiet", str(authority)],
        check=True,
        capture_output=True,
    )
    _git(
        repository,
        "push",
        "--quiet",
        str(authority),
        f"{prepared.publication_commit}:refs/heads/main",
    )
    _git(authority, "symbolic-ref", "HEAD", "refs/heads/main")
    return repository, prepared, receipt, authority


def _caller_state(repository: Path) -> tuple[bytes, bytes, bytes]:
    return (
        _git(repository, "rev-parse", "HEAD").stdout,
        _git(repository, "write-tree").stdout,
        _git(repository, "status", "--porcelain=v1", "-z").stdout,
    )


def test_handoff_uses_an_independent_clean_detached_publication_workspace(
    tmp_path: Path,
) -> None:
    caller, prepared, receipt, authority = _candidate(tmp_path)
    _git(caller, "switch", "--detach", "--quiet", prepared.base_commit)
    (caller / "README.md").write_text("staged caller change\n", encoding="utf-8")
    _git(caller, "add", "README.md")
    (caller / "caller-untracked.txt").write_text("caller only\n", encoding="utf-8")
    before = _caller_state(caller)

    with _open_execution_workspace(
        receipt,
        authority_url=str(authority),
    ) as workspace:
        workspace_root = workspace.root
        assert workspace.root != caller
        assert _git(workspace.root, "rev-parse", "HEAD").stdout.decode().strip() == (
            prepared.publication_commit
        )
        symbolic = subprocess.run(
            ["git", "-C", str(workspace.root), "symbolic-ref", "-q", "HEAD"],
            check=False,
            capture_output=True,
        )
        assert symbolic.returncode == 1
        assert _git(workspace.root, "status", "--porcelain=v1", "-z").stdout == b""
        assert workspace.history.registry.resolved_revision == (
            prepared.publication_commit
        )
        assert workspace.history.registry.publication_commit == (
            prepared.publication_commit
        )
        execution_cfg = workspace.load_config()
        assert execution_cfg["_root"] == workspace.root
        assert execution_cfg["project"]["seed"] == 649
        unrelated_cfg = {"project": {"seed": -1}}
        unrelated_cfg["project"]["seed"] = 0
        assert execution_cfg["project"]["seed"] == 649
        assert _caller_state(caller) == before

    assert not workspace_root.exists()
    assert _caller_state(caller) == before


def test_public_handoff_uses_only_the_fixed_anonymous_github_authority(
    monkeypatch,
) -> None:
    sentinel_receipt = object()
    sentinel_workspace = object()
    calls: list[tuple[object, str]] = []

    @contextmanager
    def fake_open(receipt, *, authority_url):
        calls.append((receipt, authority_url))
        yield sentinel_workspace

    monkeypatch.setattr(history_handoff, "_open_execution_workspace", fake_open)

    with history_handoff.open_github_execution_workspace(sentinel_receipt) as workspace:
        assert workspace is sentinel_workspace

    assert calls == [(sentinel_receipt, "https://github.com/Jasper-Shi/lottopred.git")]


def test_handoff_rejects_inconsistent_receipts_before_any_git_operation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _caller, _prepared, receipt, authority = _candidate(tmp_path)
    invalid_receipts = (
        replace(receipt, cas_ack=CasAck(CasStatus.UNKNOWN)),
        replace(
            receipt,
            outcome=PublicationOutcome.CONFIRMED_AFTER_REREAD,
            cas_ack=CasAck(CasStatus.APPLIED),
        ),
        replace(receipt, outcome=[]),
    )
    git_calls: list[object] = []

    def forbidden_git(*args, **kwargs):
        git_calls.append((args, kwargs))
        raise AssertionError("invalid receipt reached Git")

    monkeypatch.setattr(history_handoff, "_git", forbidden_git)

    for invalid in invalid_receipts:
        with (
            pytest.raises(HistoryExecutionHandoffError, match="receipt"),
            _open_execution_workspace(
                invalid,
                authority_url=str(authority),
            ),
        ):
            pass

    assert git_calls == []


def test_handoff_rejects_a_publication_tree_with_a_symlink(
    tmp_path: Path,
) -> None:
    _caller, _prepared, receipt, authority = _candidate(
        tmp_path,
        base_symlink=True,
    )

    with (
        pytest.raises(HistoryExecutionHandoffError, match="regular files"),
        _open_execution_workspace(
            receipt,
            authority_url=str(authority),
        ),
    ):
        pass


def test_handoff_requires_authority_main_itself_to_equal_publication_p(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _caller, prepared, receipt, authority = _candidate(tmp_path)
    _git(
        authority,
        "update-ref",
        "refs/heads/main",
        prepared.base_commit,
        prepared.publication_commit,
    )
    real_temporary_directory = history_handoff.tempfile.TemporaryDirectory
    created: list[Path] = []

    def tracking_temporary_directory(*args, **kwargs):
        temporary = real_temporary_directory(*args, **kwargs)
        created.append(Path(temporary.name))
        return temporary

    monkeypatch.setattr(
        history_handoff.tempfile,
        "TemporaryDirectory",
        tracking_temporary_directory,
    )

    with (
        pytest.raises(HistoryExecutionHandoffError, match="authority main"),
        _open_execution_workspace(
            receipt,
            authority_url=str(authority),
        ),
    ):
        pass

    assert created
    assert all(not path.exists() for path in created)


def test_handoff_cleans_the_independent_workspace_when_the_caller_raises(
    tmp_path: Path,
) -> None:
    _caller, _prepared, receipt, authority = _candidate(tmp_path)
    workspace_root: Path | None = None

    with (
        pytest.raises(LookupError, match="injected caller failure"),
        _open_execution_workspace(
            receipt,
            authority_url=str(authority),
        ) as workspace,
    ):
        workspace_root = workspace.root
        raise LookupError("injected caller failure")

    assert workspace_root is not None
    assert not workspace_root.exists()


def test_handoff_rejects_an_alternate_object_store_in_the_fresh_workspace(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _caller, _prepared, receipt, authority = _candidate(tmp_path)
    real_git = history_handoff._git

    def injecting_git(repository, *arguments, **kwargs):
        result = real_git(repository, *arguments, **kwargs)
        if repository is not None and arguments and arguments[0] == "fetch":
            info = Path(repository) / ".git" / "objects" / "info"
            info.mkdir(parents=True, exist_ok=True)
            (info / "alternates").write_text(
                str(authority / "objects") + "\n",
                encoding="utf-8",
            )
        return result

    monkeypatch.setattr(history_handoff, "_git", injecting_git)

    with (
        pytest.raises(HistoryExecutionHandoffError, match="self-contained"),
        _open_execution_workspace(
            receipt,
            authority_url=str(authority),
        ),
    ):
        pass


def test_execution_workspace_cannot_be_constructed_without_handoff_capability(
    tmp_path: Path,
) -> None:
    _caller, prepared, receipt, authority = _candidate(tmp_path)

    with _open_execution_workspace(
        receipt,
        authority_url=str(authority),
    ) as workspace:
        with pytest.raises((TypeError, HistoryExecutionHandoffError)):
            ExecutionWorkspace(
                root=workspace.root,
                publication_commit=prepared.publication_commit,
                history=workspace.history,
            )

        created_at = datetime.combine(
            workspace.history.draws[-1].draw_date + timedelta(days=1),
            datetime.min.time(),
            UTC,
        ).replace(hour=12)
        relative, _raw = _write_valid_prediction(workspace, created_at)
        forged = replace(
            workspace,
            history=replace(
                workspace.history,
                draws=workspace.history.draws[:-1],
            ),
        )
        with pytest.raises(HistoryExecutionHandoffError, match="history"):
            history_handoff.freeze_execution_outputs(
                forged,
                (relative,),
                created_at=created_at,
            )

        alternate = tmp_path / "transferred-workspace"
        subprocess.run(
            [
                "git",
                "clone",
                "--no-local",
                "--quiet",
                str(workspace.root),
                str(alternate),
            ],
            check=True,
            capture_output=True,
        )
        _git(alternate, "checkout", "--quiet", "--detach", workspace.publication_commit)
        transferred = replace(
            workspace,
            root=alternate,
            history=load_published_history(alternate, workspace.publication_commit),
        )
        with pytest.raises(HistoryExecutionHandoffError, match="capability"):
            transferred.load_config()

        with pytest.raises(TypeError, match="dataclass"):
            replace(workspace._capability, root=alternate)


def test_execution_workspace_capability_rejects_same_path_directory_replacement(
    tmp_path: Path,
) -> None:
    _caller, _prepared, receipt, authority = _candidate(tmp_path)

    with _open_execution_workspace(
        receipt,
        authority_url=str(authority),
    ) as workspace:
        original_root = workspace.root
        retired_root = original_root.parent / "retired-repository"
        original_root.rename(retired_root)
        subprocess.run(
            [
                "git",
                "clone",
                "--no-local",
                "--quiet",
                str(retired_root),
                str(original_root),
            ],
            check=True,
            capture_output=True,
        )
        _git(
            original_root,
            "checkout",
            "--quiet",
            "--detach",
            workspace.publication_commit,
        )

        with pytest.raises(HistoryExecutionHandoffError, match="capability"):
            workspace.load_config()


def test_execution_workspace_capability_rejects_git_directory_replacement(
    tmp_path: Path,
) -> None:
    _caller, _prepared, receipt, authority = _candidate(tmp_path)

    with _open_execution_workspace(
        receipt,
        authority_url=str(authority),
    ) as workspace:
        alternate = tmp_path / "alternate-git-directory"
        subprocess.run(
            [
                "git",
                "clone",
                "--no-local",
                "--quiet",
                str(workspace.root),
                str(alternate),
            ],
            check=True,
            capture_output=True,
        )
        _git(
            alternate,
            "checkout",
            "--quiet",
            "--detach",
            workspace.publication_commit,
        )
        (workspace.root / ".git").rename(workspace.root.parent / "retired-git")
        (alternate / ".git").rename(workspace.root / ".git")

        with pytest.raises(
            HistoryExecutionHandoffError,
            match="capability|self-contained",
        ):
            workspace.load_config()


def test_execution_workspace_rejects_external_git_config_symlink(
    tmp_path: Path,
) -> None:
    _caller, _prepared, receipt, authority = _candidate(tmp_path)

    with _open_execution_workspace(
        receipt,
        authority_url=str(authority),
    ) as workspace:
        config_path = workspace.root / ".git" / "config"
        external_config = tmp_path / "external-git-config"
        external_config.write_bytes(config_path.read_bytes())
        config_path.unlink()
        config_path.symlink_to(external_config)

        with pytest.raises(HistoryExecutionHandoffError, match="self-contained"):
            workspace.load_config()


def test_execution_workspace_rechecks_git_controls_after_git_consumption(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _caller, _prepared, receipt, authority = _candidate(tmp_path)

    with _open_execution_workspace(
        receipt,
        authority_url=str(authority),
    ) as workspace:
        real_git = history_handoff._git
        external_config = tmp_path / "late-external-git-config"
        injected = False

        def injecting_git(repository, *arguments, **kwargs):
            nonlocal injected
            result = real_git(repository, *arguments, **kwargs)
            if (
                not injected
                and repository == workspace.root
                and arguments[:2] == ("rev-parse", "--absolute-git-dir")
            ):
                config_path = workspace.root / ".git" / "config"
                external_config.write_bytes(config_path.read_bytes())
                config_path.unlink()
                config_path.symlink_to(external_config)
                injected = True
            return result

        monkeypatch.setattr(history_handoff, "_git", injecting_git)

        with pytest.raises(HistoryExecutionHandoffError, match="self-contained"):
            workspace.load_config()


def test_freeze_outputs_creates_an_unattached_exact_single_parent_commit(
    tmp_path: Path,
) -> None:
    _caller, prepared, receipt, authority = _candidate(tmp_path)

    with _open_execution_workspace(
        receipt,
        authority_url=str(authority),
    ) as workspace:
        created_at = datetime.combine(
            workspace.history.draws[-1].draw_date + timedelta(days=1),
            datetime.min.time(),
            UTC,
        ).replace(hour=12)
        predictions, prediction_raws = _write_required_predictions(
            workspace,
            created_at,
        )
        evaluation, evaluation_raw = _write_valid_evaluation(workspace)
        raw_by_path = dict(zip(predictions, prediction_raws, strict=True))
        raw_by_path[evaluation] = evaluation_raw
        output_paths = tuple(sorted((evaluation, *predictions)))
        head_before = _git(workspace.root, "rev-parse", "HEAD").stdout
        index_tree_before = _git(workspace.root, "write-tree").stdout
        refs_before = _git(workspace.root, "show-ref").stdout

        frozen = history_handoff.freeze_execution_outputs(
            workspace,
            output_paths,
            created_at=created_at,
        )

        assert frozen.repository == workspace.root
        assert frozen.parent_commit == prepared.publication_commit
        assert frozen.paths == output_paths
        assert tuple(file.path for file in frozen.files) == output_paths
        assert tuple(file.bytes for file in frozen.files) == tuple(
            len(raw_by_path[path]) for path in output_paths
        )
        assert (
            _git(workspace.root, "rev-parse", f"{frozen.artifact_commit}^").stdout
            == head_before
        )
        assert _git(workspace.root, "rev-parse", "HEAD").stdout == head_before
        assert _git(workspace.root, "write-tree").stdout == index_tree_before
        assert _git(workspace.root, "show-ref").stdout == refs_before
        assert _git(
            workspace.root,
            "diff-tree",
            "--no-commit-id",
            "--name-status",
            "--no-renames",
            "-r",
            "-z",
            prepared.publication_commit,
            frozen.artifact_commit,
        ).stdout == b"".join(
            b"A\x00" + path.encode("ascii") + b"\x00" for path in output_paths
        )
        published = load_published_history(
            workspace.root,
            frozen.artifact_commit,
        )
        assert published.registry.resolved_revision == frozen.artifact_commit
        assert published.registry.publication_commit == prepared.publication_commit
        for path in output_paths:
            assert (
                _git(
                    workspace.root,
                    "cat-file",
                    "blob",
                    f"{frozen.artifact_commit}:{path}",
                ).stdout
                == raw_by_path[path]
            )


def test_freeze_rejects_a_json_object_that_is_not_a_bound_audit_artifact(
    tmp_path: Path,
) -> None:
    _caller, _prepared, receipt, authority = _candidate(tmp_path)

    with _open_execution_workspace(
        receipt,
        authority_url=str(authority),
    ) as workspace:
        target = _next_draw_date(workspace.history.draws[-1].draw_date)
        relative = f"predictions/{target.isoformat()}__model__v1.0.0.json"
        _write_json(workspace.root / relative, {"kind": "prediction"})
        created_at = datetime.combine(
            workspace.history.draws[-1].draw_date + timedelta(days=1),
            datetime.min.time(),
            UTC,
        ).replace(hour=12)

        with pytest.raises(HistoryExecutionHandoffError, match="prediction schema"):
            history_handoff.freeze_execution_outputs(
                workspace,
                (relative,),
                created_at=created_at,
            )


def test_freeze_rejects_prediction_identity_provenance_and_chronology_mismatches(
    tmp_path: Path,
) -> None:
    _caller, _prepared, receipt, authority = _candidate(tmp_path)

    with _open_execution_workspace(
        receipt,
        authority_url=str(authority),
    ) as workspace:
        created_at = datetime.combine(
            workspace.history.draws[-1].draw_date + timedelta(days=1),
            datetime.min.time(),
            UTC,
        ).replace(hour=12)
        target = _next_draw_date(workspace.history.draws[-1].draw_date)
        relative = f"predictions/{target.isoformat()}__model__v1.0.0.json"
        valid = _prediction_payload(workspace.history, target, created_at)
        invalid_payloads = []

        wrong_model = json.loads(json.dumps(valid))
        wrong_model["model_name"] = "different_model"
        invalid_payloads.append(wrong_model)

        wrong_history = json.loads(json.dumps(valid))
        wrong_history["metadata"]["operational_history"] = {"epoch": "forged"}
        invalid_payloads.append(wrong_history)

        post_commit_generation = json.loads(json.dumps(valid))
        post_commit_generation["generated_at"] = (
            created_at + timedelta(seconds=1)
        ).isoformat()
        invalid_payloads.append(post_commit_generation)

        for payload in invalid_payloads:
            _write_json(workspace.root / relative, payload)
            with pytest.raises(
                HistoryExecutionHandoffError,
                match="prediction schema|chronology",
            ):
                history_handoff.freeze_execution_outputs(
                    workspace,
                    (relative,),
                    created_at=created_at,
                )


def test_freeze_requires_the_exact_configured_live_prediction_cohort(
    tmp_path: Path,
) -> None:
    _caller, _prepared, receipt, authority = _candidate(tmp_path)

    with _open_execution_workspace(
        receipt,
        authority_url=str(authority),
    ) as workspace:
        created_at = datetime.combine(
            workspace.history.draws[-1].draw_date + timedelta(days=1),
            datetime.min.time(),
            UTC,
        ).replace(hour=12)
        config = workspace.load_config()
        model_name = config["live"]["models"][0]
        relative, _raw = _write_valid_prediction(
            workspace,
            created_at,
            model_name=model_name,
            model_version=config["project"]["model_version"],
        )

        with pytest.raises(
            HistoryExecutionHandoffError,
            match="live prediction cohort",
        ):
            history_handoff.freeze_execution_outputs(
                workspace,
                (relative,),
                created_at=created_at,
            )


def test_freeze_binds_live_prediction_versions_and_roles_to_p_config(
    tmp_path: Path,
) -> None:
    _caller, _prepared, receipt, authority = _candidate(tmp_path)

    with _open_execution_workspace(
        receipt,
        authority_url=str(authority),
    ) as workspace:
        created_at = datetime.combine(
            workspace.history.draws[-1].draw_date + timedelta(days=1),
            datetime.min.time(),
            UTC,
        ).replace(hour=12)
        config = workspace.load_config()
        predictions, prediction_raws = _write_required_predictions(
            workspace,
            created_at,
        )
        raw_by_path = dict(zip(predictions, prediction_raws, strict=True))
        primary_model = next(
            model
            for model in config["live"]["models"]
            if model not in config["live"]["shadow_models"]
        )
        primary_path = next(
            path for path in predictions if f"__{primary_model}__" in path
        )
        primary_payload = json.loads(raw_by_path[primary_path])
        primary_payload["metadata"]["role"] = "shadow"
        _write_json(workspace.root / primary_path, primary_payload)

        with pytest.raises(
            HistoryExecutionHandoffError,
            match="live prediction cohort",
        ):
            history_handoff.freeze_execution_outputs(
                workspace,
                tuple(sorted(predictions)),
                created_at=created_at,
            )

        (workspace.root / primary_path).write_bytes(raw_by_path[primary_path])
        wrong_version = "v9.9.9"
        wrong_path = primary_path.replace(
            f"__{config['project']['model_version']}.json",
            f"__{wrong_version}.json",
        )
        wrong_payload = json.loads(raw_by_path[primary_path])
        wrong_payload["model_version"] = wrong_version
        (workspace.root / primary_path).unlink()
        _write_json(workspace.root / wrong_path, wrong_payload)
        wrong_paths = tuple(
            sorted(wrong_path if path == primary_path else path for path in predictions)
        )

        with pytest.raises(
            HistoryExecutionHandoffError,
            match="live prediction cohort",
        ):
            history_handoff.freeze_execution_outputs(
                workspace,
                wrong_paths,
                created_at=created_at,
            )


def test_freeze_rejects_an_evaluation_not_bound_to_p_actual_history(
    tmp_path: Path,
) -> None:
    _caller, _prepared, receipt, authority = _candidate(tmp_path)

    with _open_execution_workspace(
        receipt,
        authority_url=str(authority),
    ) as workspace:
        relative, _raw = _write_valid_evaluation(workspace)
        payload = json.loads((workspace.root / relative).read_text(encoding="utf-8"))
        payload["actual_history"] = {"epoch": "forged"}
        _write_json(workspace.root / relative, payload)
        created_at = datetime.combine(
            workspace.history.draws[-1].draw_date + timedelta(days=1),
            datetime.min.time(),
            UTC,
        ).replace(hour=12)

        with pytest.raises(HistoryExecutionHandoffError, match="evaluation schema"):
            history_handoff.freeze_execution_outputs(
                workspace,
                (relative,),
                created_at=created_at,
            )


def test_freeze_rejects_evaluation_of_a_prediction_created_after_the_draw(
    tmp_path: Path,
) -> None:
    _caller, _prepared, receipt, authority = _candidate(
        tmp_path,
        source_prediction_after_draw=True,
    )

    with _open_execution_workspace(
        receipt,
        authority_url=str(authority),
    ) as workspace:
        relative, _raw = _write_valid_evaluation(workspace)
        created_at = datetime.combine(
            workspace.history.draws[-1].draw_date + timedelta(days=3),
            datetime.min.time(),
            UTC,
        ).replace(hour=12)

        with pytest.raises(
            HistoryExecutionHandoffError,
            match="evaluation schema|chronology",
        ):
            history_handoff.freeze_execution_outputs(
                workspace,
                (relative,),
                created_at=created_at,
            )


def test_freeze_rejects_repository_tampering_after_workspace_handoff(
    tmp_path: Path,
) -> None:
    _caller, _prepared, receipt, authority = _candidate(tmp_path)

    with _open_execution_workspace(
        receipt,
        authority_url=str(authority),
    ) as workspace:
        created_at = datetime.combine(
            workspace.history.draws[-1].draw_date + timedelta(days=1),
            datetime.min.time(),
            UTC,
        ).replace(hour=12)
        relative, _raw = _write_valid_prediction(workspace, created_at)
        info = workspace.root / ".git" / "objects" / "info"
        info.mkdir(parents=True, exist_ok=True)
        (info / "alternates").write_text(
            str(authority / "objects") + "\n",
            encoding="utf-8",
        )

        with pytest.raises(HistoryExecutionHandoffError, match="self-contained"):
            history_handoff.freeze_execution_outputs(
                workspace,
                (relative,),
                created_at=created_at,
            )

        (info / "alternates").unlink()
        _git(workspace.root, "config", "fsck.missingEmail", "ignore")
        with pytest.raises(HistoryExecutionHandoffError, match="self-contained"):
            history_handoff.freeze_execution_outputs(
                workspace,
                (relative,),
                created_at=created_at,
            )


def test_freeze_rejects_same_size_output_mutation_after_snapshot(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _caller, _prepared, receipt, authority = _candidate(tmp_path)

    with _open_execution_workspace(
        receipt,
        authority_url=str(authority),
    ) as workspace:
        created_at = datetime.combine(
            workspace.history.draws[-1].draw_date + timedelta(days=1),
            datetime.min.time(),
            UTC,
        ).replace(hour=12)
        predictions, prediction_raws = _write_required_predictions(
            workspace,
            created_at,
        )
        relative = predictions[0]
        original_raw = prediction_raws[0]
        changed_raw = original_raw.replace(b'"role": "primary"', b'"role": "changed"')
        assert len(changed_raw) == len(original_raw)
        real_git = history_handoff._git
        mutated = False

        def mutate_after_commit(repository, *arguments, **kwargs):
            nonlocal mutated
            result = real_git(repository, *arguments, **kwargs)
            if arguments and arguments[0] == "commit-tree" and not mutated:
                (workspace.root / relative).write_bytes(changed_raw)
                mutated = True
            return result

        monkeypatch.setattr(history_handoff, "_git", mutate_after_commit)

        with pytest.raises(HistoryExecutionHandoffError, match="changed"):
            history_handoff.freeze_execution_outputs(
                workspace,
                tuple(sorted(predictions)),
                created_at=created_at,
            )

        assert mutated


def test_freeze_outputs_rejects_an_ignored_secret_file(
    tmp_path: Path,
) -> None:
    _caller, _prepared, receipt, authority = _candidate(tmp_path)

    with _open_execution_workspace(
        receipt,
        authority_url=str(authority),
    ) as workspace:
        created_at = datetime.combine(
            workspace.history.draws[-1].draw_date + timedelta(days=1),
            datetime.min.time(),
            UTC,
        ).replace(hour=12)
        relative, _raw = _write_valid_prediction(workspace, created_at)
        (workspace.root / ".env").write_text(
            "DO_NOT_CAPTURE=secret\n",
            encoding="utf-8",
        )
        with pytest.raises(
            HistoryExecutionHandoffError,
            match="changes",
        ):
            history_handoff.freeze_execution_outputs(
                workspace,
                (relative,),
                created_at=created_at,
            )


@pytest.mark.parametrize(
    "paths",
    [
        (),
        "predictions/2099-01-04__model__v1.0.0.json",
        ("data/processed/forbidden.json",),
        ("predictions/../forbidden.json",),
        (
            "predictions/2099-01-04__model__v1.0.0.json",
            "predictions/2099-01-04__model__v1.0.0.json",
        ),
        (
            "predictions/2099-01-04__model__v1.0.0.json",
            "evaluations/2099-01-01__model__v1.0.0.json",
        ),
    ],
)
def test_freeze_rejects_noncanonical_output_lists_before_git(
    paths,
    monkeypatch,
) -> None:
    git_calls: list[object] = []

    def forbidden_git(*args, **kwargs):
        git_calls.append((args, kwargs))
        raise AssertionError("invalid output list reached Git")

    monkeypatch.setattr(history_handoff, "_git", forbidden_git)

    with pytest.raises(HistoryExecutionHandoffError, match="output path"):
        history_handoff.freeze_execution_outputs(
            object(),
            paths,
            created_at=datetime(2099, 1, 2, 12, tzinfo=UTC),
        )

    assert git_calls == []


def test_freeze_rejects_any_unlisted_workspace_change(
    tmp_path: Path,
) -> None:
    _caller, _prepared, receipt, authority = _candidate(tmp_path)

    with _open_execution_workspace(
        receipt,
        authority_url=str(authority),
    ) as workspace:
        created_at = datetime.combine(
            workspace.history.draws[-1].draw_date + timedelta(days=1),
            datetime.min.time(),
            UTC,
        ).replace(hour=12)
        relative, _raw = _write_valid_prediction(workspace, created_at)
        (workspace.root / "unexpected.txt").write_text(
            "unexpected\n",
            encoding="utf-8",
        )
        with pytest.raises(HistoryExecutionHandoffError, match="changes"):
            history_handoff.freeze_execution_outputs(
                workspace,
                (relative,),
                created_at=created_at,
            )


@pytest.mark.parametrize(
    "raw",
    [
        b'{"duplicate":1,"duplicate":2}\n',
        b'{"value":NaN}\n',
        b'{"value":1e999}\n',
        b"[]\n",
        b"\xff\n",
    ],
)
def test_freeze_rejects_non_strict_output_json(
    tmp_path: Path,
    raw: bytes,
) -> None:
    _caller, _prepared, receipt, authority = _candidate(tmp_path)

    with _open_execution_workspace(
        receipt,
        authority_url=str(authority),
    ) as workspace:
        relative = (
            f"evaluations/{workspace.history.draws[-1].draw_date.isoformat()}"
            "__model__v1.0.0.json"
        )
        (workspace.root / "evaluations").mkdir(exist_ok=True)
        (workspace.root / relative).write_bytes(raw)
        created_at = datetime.combine(
            workspace.history.draws[-1].draw_date + timedelta(days=1),
            datetime.min.time(),
            UTC,
        ).replace(hour=12)

        with pytest.raises(HistoryExecutionHandoffError, match="JSON"):
            history_handoff.freeze_execution_outputs(
                workspace,
                (relative,),
                created_at=created_at,
            )


def test_freeze_rejects_an_artifact_time_before_publication_p(
    tmp_path: Path,
) -> None:
    _caller, _prepared, receipt, authority = _candidate(tmp_path)

    with _open_execution_workspace(
        receipt,
        authority_url=str(authority),
    ) as workspace:
        relative = (
            f"predictions/{_next_draw_date(workspace.history.draws[-1].draw_date).isoformat()}"
            "__model__v1.0.0.json"
        )
        _write_json(workspace.root / relative, {"kind": "prediction"})
        before_publication = datetime.combine(
            workspace.history.draws[-1].draw_date + timedelta(days=1),
            datetime.min.time(),
            UTC,
        ).replace(hour=5)

        with pytest.raises(
            HistoryExecutionHandoffError,
            match="publication",
        ):
            history_handoff.freeze_execution_outputs(
                workspace,
                (relative,),
                created_at=before_publication,
            )
