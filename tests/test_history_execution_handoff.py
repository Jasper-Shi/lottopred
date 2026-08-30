from __future__ import annotations

import hashlib
import json
import os
import subprocess
from contextlib import contextmanager
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from threading import Event, Lock, Thread

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

_LEGACY_2026_08_26_ORIGIN = "9f16e20c726c7b65eed1d387c4c725d51248f570"
_LEGACY_2026_08_26_PARENT = "0ef18836530ebb7083e0c8e5d557e5cdc3d476a4"
_LEGACY_2026_08_26_HISTORY = (
    "9d5d79130c77fb2642069d4b49e8ecc65615ab0f",
    "f7f47b29cd1281043672784843a06d8a8a0abf8e0bdcf511805f9346e3f37773",
    136_297,
)
_LEGACY_2026_08_26_PREDICTIONS = {
    "ema_gap": (
        "a8159032ec7aa47627ac432e5303b1b838843f2c",
        "803af5c6f56d8b7ce3f75e0052015f9b1030e9d27d67f886af6a213ef26894c2",
        2_191,
        "2026-08-23T11:35:59.681632-04:00",
        "primary",
    ),
    "ensemble": (
        "f2df110923a0f5136a66bb1dcc35376cc3931ed6",
        "c07e6118a2ed61132626602f7ab74e3baca659aa28a2033656ae2587207ce166",
        2_188,
        "2026-08-23T11:36:01.073756-04:00",
        "primary",
    ),
    "logistic": (
        "ee83fff0fbcd7ce768880a7e3a367486d8553e16",
        "58032d0b9b6e40314a82039431cb3868468277929c6dfa4d23eb673918f3e270",
        2_198,
        "2026-08-23T11:36:00.968438-04:00",
        "primary",
    ),
    "long_frequency": (
        "73275cbd248fcbac78ed67256e3341a3c7539e34",
        "7f7cfc90e8e7c8d58117656035975353586e3ceb6f8bde0fc125d3b1778d3622",
        2_200,
        "2026-08-23T11:35:59.655183-04:00",
        "primary",
    ),
    "random": (
        "0df842e837613306f27cdfc2dccc2a852b307154",
        "d1afd687db881a6a9bbe9eaef5abdca58d973d59bc77ead4ec341998688ba86d",
        2_193,
        "2026-08-23T11:35:59.640444-04:00",
        "primary",
    ),
    "recent_frequency": (
        "7f82f326ec33009eaac4e7c933b5f1abb826fab0",
        "f0a4fee650f064ec2cf0b243923e645ce93ccb480aefff02d36a450a967473bf",
        2_182,
        "2026-08-23T11:35:59.669104-04:00",
        "primary",
    ),
    "v3_boosting": (
        "3b1547434d6bda7bc9f58d90b270b55631aaf689",
        "fe51480b5a15b24dcf6551396edafb84c8363f40998a1bc1a53348ec2a65e0f6",
        2_199,
        "2026-08-23T11:36:01.458977-04:00",
        "shadow",
    ),
}


class _ObservedLock:
    def __init__(self, lock: Lock, acquire_entered: Event) -> None:
        self._lock = lock
        self._acquire_entered = acquire_entered

    def acquire(self, blocking: bool = True) -> bool:
        self._acquire_entered.set()
        return self._lock.acquire(blocking=blocking)

    def release(self) -> None:
        self._lock.release()


class _ObservedArtifactRegistry(dict[object, object]):
    def __init__(self, iteration_started: Event, release_iteration: Event) -> None:
        super().__init__()
        self._iteration_started = iteration_started
        self._release_iteration = release_iteration

    def items(self):
        iterator = super().items().__iter__()
        self._iteration_started.set()
        assert self._release_iteration.wait(timeout=30)
        yield from iterator


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
    classify_prediction_source: bool = True,
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
    if classify_prediction_source:
        prediction_relative = prediction_path.relative_to(workspace.root).as_posix()
        evaluation["prediction_source"] = history_handoff.evaluation_prediction_source(
            workspace.root,
            workspace.publication_commit,
            prediction_relative,
        )
    else:
        evaluation["prediction_source"] = {"kind": "unverified-test-fixture"}
    relative = f"evaluations/{target.isoformat()}__{model_name}__v1.0.0.json"
    return relative, _write_json(workspace.root / relative, evaluation)


def _candidate(
    tmp_path: Path,
    *,
    base_symlink: bool = False,
    intervening_prediction_merge: bool = True,
    intervening_prediction_history: bool = False,
    prediction_history_attack: str | None = None,
    source_prediction_after_draw: bool = False,
):
    repository = tmp_path / "caller"
    subprocess.run(
        ["git", "clone", "--no-local", "--quiet", str(ROOT), str(repository)],
        check=True,
        capture_output=True,
    )
    source_head = _git(repository, "rev-parse", "HEAD").stdout.decode().strip()
    source_history = load_published_history(repository, source_head)
    target = _next_draw_date(source_history.draws[-1].draw_date)
    anchor_at = datetime.combine(
        target - timedelta(days=2),
        datetime.min.time(),
        UTC,
    ).replace(hour=12)
    anchor_environment = os.environ.copy()
    anchor_environment.update(
        {
            "GIT_AUTHOR_DATE": anchor_at.isoformat(),
            "GIT_COMMITTER_DATE": anchor_at.isoformat(),
        }
    )
    anchor = (
        subprocess.run(
            [
                "git",
                "-C",
                str(repository),
                "-c",
                "user.name=handoff-test",
                "-c",
                "user.email=handoff-test@lotto649.invalid",
                "commit-tree",
                f"{source_head}^{{tree}}",
                "-p",
                source_head,
                "-m",
                "create pre-draw handoff fixture anchor",
            ],
            check=True,
            capture_output=True,
            env=anchor_environment,
        )
        .stdout.decode()
        .strip()
    )
    _git(repository, "switch", "--detach", "--quiet", anchor)
    if base_symlink:
        (repository / "unsafe-link").symlink_to("README.md")
        _git(repository, "add", "unsafe-link")
        symlink_environment = os.environ.copy()
        symlink_at = anchor_at + timedelta(minutes=1)
        symlink_environment.update(
            {
                "GIT_AUTHOR_DATE": symlink_at.isoformat(),
                "GIT_COMMITTER_DATE": symlink_at.isoformat(),
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
                "add unsafe execution symlink",
            ],
            check=True,
            capture_output=True,
            env=symlink_environment,
        )
    initial = _git(repository, "rev-parse", "HEAD").stdout.decode().strip()
    if prediction_history_attack in {"side_add", "side_conflict"}:
        _git(repository, "branch", "handoff-attack-side", initial)
    base_history = load_published_history(repository, initial)
    assert _next_draw_date(base_history.draws[-1].draw_date) == target
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
    prediction_raw = _write_json(prediction_path, prediction)
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
    prediction_origin = _git(repository, "rev-parse", "HEAD").stdout.decode().strip()
    symbolic_head = subprocess.run(
        ["git", "-C", str(repository), "symbolic-ref", "-q", "--short", "HEAD"],
        check=False,
        capture_output=True,
    )
    assert symbolic_head.returncode in {0, 1}
    main_branch = (
        symbolic_head.stdout.decode().strip() if symbolic_head.returncode == 0 else None
    )

    def restore_mainline(detached_commit: str) -> None:
        if main_branch is None:
            _git(repository, "switch", "--detach", "--quiet", detached_commit)
        else:
            _git(repository, "switch", "--quiet", main_branch)

    def commit_staged(message: str, committed_at: datetime) -> None:
        environment = os.environ.copy()
        environment.update(
            {
                "GIT_AUTHOR_DATE": committed_at.isoformat(),
                "GIT_COMMITTER_DATE": committed_at.isoformat(),
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
                message,
            ],
            check=True,
            capture_output=True,
            env=environment,
        )

    if prediction_history_attack in {"mutate_restore", "delete_readd", "mode_flip"}:
        if prediction_history_attack == "mutate_restore":
            changed = json.loads(prediction_raw)
            changed["metadata"]["role"] = "shadow"
            _write_json(prediction_path, changed)
            _git(repository, "add", str(prediction_path.relative_to(repository)))
            commit_staged(
                "mutate committed prediction",
                prediction_commit_at + timedelta(minutes=1),
            )
        elif prediction_history_attack == "delete_readd":
            prediction_path.unlink()
            _git(
                repository,
                "add",
                "--update",
                str(prediction_path.relative_to(repository)),
            )
            commit_staged(
                "delete committed prediction",
                prediction_commit_at + timedelta(minutes=1),
            )
        else:
            prediction_path.chmod(0o755)
            _git(repository, "add", str(prediction_path.relative_to(repository)))
            commit_staged(
                "change committed prediction mode",
                prediction_commit_at + timedelta(minutes=1),
            )
        prediction_path.write_bytes(prediction_raw)
        prediction_path.chmod(0o644)
        _git(repository, "add", str(prediction_path.relative_to(repository)))
        commit_staged(
            "restore committed prediction",
            prediction_commit_at + timedelta(minutes=2),
        )
    elif prediction_history_attack in {"side_add", "side_conflict"}:
        _git(repository, "switch", "--quiet", "handoff-attack-side")
        if prediction_history_attack == "side_conflict":
            changed = json.loads(prediction_raw)
            changed["metadata"]["role"] = "shadow"
            _write_json(prediction_path, changed)
        else:
            prediction_path.write_bytes(prediction_raw)
        _git(repository, "add", str(prediction_path.relative_to(repository)))
        commit_staged(
            "independently add prediction on side branch",
            prediction_commit_at + timedelta(minutes=1),
        )
        restore_mainline(prediction_origin)
        merge_environment = os.environ.copy()
        merge_environment.update(
            {
                "GIT_AUTHOR_DATE": (
                    prediction_commit_at + timedelta(minutes=2)
                ).isoformat(),
                "GIT_COMMITTER_DATE": (
                    prediction_commit_at + timedelta(minutes=2)
                ).isoformat(),
            }
        )
        merged = subprocess.run(
            [
                "git",
                "-C",
                str(repository),
                "-c",
                "user.name=handoff-test",
                "-c",
                "user.email=handoff-test@lotto649.invalid",
                "merge",
                "--quiet",
                "--no-ff",
                "handoff-attack-side",
                "-m",
                "merge independent prediction branch",
            ],
            check=False,
            capture_output=True,
            env=merge_environment,
        )
        if prediction_history_attack == "side_conflict":
            assert merged.returncode == 1
            prediction_path.write_bytes(prediction_raw)
            _git(repository, "add", str(prediction_path.relative_to(repository)))
            commit_staged(
                "resolve prediction conflict to original bytes",
                prediction_commit_at + timedelta(minutes=2),
            )
        else:
            assert merged.returncode == 0
    elif prediction_history_attack is not None:
        raise AssertionError(
            f"unknown prediction history attack: {prediction_history_attack}"
        )
    if intervening_prediction_history:

        def commit_fixture_file(
            path: str,
            contents: str,
            message: str,
            committed_at: datetime,
        ) -> None:
            (repository / path).write_text(contents, encoding="utf-8")
            _git(repository, "add", path)
            environment = os.environ.copy()
            environment.update(
                {
                    "GIT_AUTHOR_DATE": committed_at.isoformat(),
                    "GIT_COMMITTER_DATE": committed_at.isoformat(),
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
                    message,
                ],
                check=True,
                capture_output=True,
                env=environment,
            )

        commit_fixture_file(
            "fixture-main.txt",
            "ordinary main change\n",
            "ordinary main change after prediction",
            prediction_commit_at + timedelta(minutes=1),
        )
        if intervening_prediction_merge:
            detached_mainline = (
                _git(repository, "rev-parse", "HEAD").stdout.decode().strip()
            )
            _git(
                repository,
                "switch",
                "--quiet",
                "-c",
                "handoff-side",
                f"{prediction_origin}^",
            )
            commit_fixture_file(
                "fixture-side.txt",
                "ordinary side change\n",
                "ordinary side change after prediction",
                prediction_commit_at + timedelta(minutes=2),
            )
            restore_mainline(detached_mainline)
            merge_environment = os.environ.copy()
            merge_environment.update(
                {
                    "GIT_AUTHOR_DATE": (
                        prediction_commit_at + timedelta(minutes=3)
                    ).isoformat(),
                    "GIT_COMMITTER_DATE": (
                        prediction_commit_at + timedelta(minutes=3)
                    ).isoformat(),
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
                    "merge",
                    "--quiet",
                    "--no-ff",
                    "handoff-side",
                    "-m",
                    "merge ordinary side change",
                ],
                check=True,
                capture_output=True,
                env=merge_environment,
            )
        commit_fixture_file(
            "fixture-code.txt",
            "ordinary code change\n",
            "ordinary code change after merge",
            prediction_commit_at + timedelta(minutes=4),
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


def _legacy_2026_08_26_candidate(
    tmp_path: Path,
    *,
    corrupt_manifest: bool = False,
):
    repository = tmp_path / "legacy-caller"
    subprocess.run(
        ["git", "clone", "--no-local", "--quiet", str(ROOT), str(repository)],
        check=True,
        capture_output=True,
    )
    manifest_relative = (
        "evidence/data_integrity/DI-2026-08-20-registered-history/"
        "legacy-2026-08-26-prediction-cohort.json"
    )
    manifest_destination = repository / manifest_relative
    manifest_destination.parent.mkdir(parents=True, exist_ok=True)
    manifest_raw = (ROOT / manifest_relative).read_bytes()
    if corrupt_manifest:
        manifest_raw = manifest_raw.replace(
            b'"corrected_history_claim": false',
            b'"corrected_history_claim": true',
            1,
        )
    manifest_destination.write_bytes(manifest_raw)
    _git(repository, "add", manifest_relative)
    staged_manifest = subprocess.run(
        [
            "git",
            "-C",
            str(repository),
            "diff",
            "--cached",
            "--quiet",
            "--",
            manifest_relative,
        ],
        check=False,
        capture_output=True,
    )
    if staged_manifest.returncode not in (0, 1) or staged_manifest.stderr:
        raise RuntimeError("legacy manifest fixture staging could not be inspected")
    manifest_commit_at = datetime(2026, 8, 24, 12, tzinfo=UTC)
    manifest_environment = os.environ.copy()
    manifest_environment.update(
        {
            "GIT_AUTHOR_DATE": manifest_commit_at.isoformat(),
            "GIT_COMMITTER_DATE": manifest_commit_at.isoformat(),
        }
    )
    if staged_manifest.returncode == 1:
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
                "install sealed legacy prediction manifest",
            ],
            check=True,
            capture_output=True,
            env=manifest_environment,
        )
    base = _git(repository, "rev-parse", "HEAD").stdout.decode().strip()
    base_history = load_published_history(repository, base)
    target = _next_draw_date(base_history.draws[-1].draw_date)
    assert target == date(2026, 8, 26)
    created_at = datetime(2026, 8, 27, 12, tzinfo=UTC)
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
    authority = tmp_path / "legacy-authority.git"
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
    return prepared, receipt, authority, created_at


def _caller_state(repository: Path) -> tuple[bytes, bytes, bytes]:
    return (
        _git(repository, "rev-parse", "HEAD").stdout,
        _git(repository, "write-tree").stdout,
        _git(repository, "status", "--porcelain=v1", "-z").stdout,
    )


def test_candidate_fixture_preserves_a_detached_source_head(
    tmp_path: Path,
    monkeypatch,
) -> None:
    detached_source = tmp_path / "detached-source"
    subprocess.run(
        ["git", "clone", "--no-local", "--quiet", str(ROOT), str(detached_source)],
        check=True,
        capture_output=True,
    )
    _git(detached_source, "switch", "--detach", "--quiet", "HEAD")
    _git(
        detached_source,
        "-c",
        "user.name=handoff-test",
        "-c",
        "user.email=handoff-test@lotto649.invalid",
        "commit",
        "--quiet",
        "--allow-empty",
        "-m",
        "detached CI merge fixture",
    )
    assert (
        subprocess.run(
            ["git", "-C", str(detached_source), "symbolic-ref", "-q", "HEAD"],
            check=False,
            capture_output=True,
        ).returncode
        == 1
    )
    monkeypatch.setitem(globals(), "ROOT", detached_source)
    candidate_root = tmp_path / "candidate"
    candidate_root.mkdir()

    caller, prepared, _receipt, _authority = _candidate(
        candidate_root,
        intervening_prediction_history=True,
    )

    assert (
        subprocess.run(
            ["git", "-C", str(caller), "symbolic-ref", "-q", "HEAD"],
            check=False,
            capture_output=True,
        ).returncode
        == 1
    )
    assert _git(caller, "rev-parse", "HEAD").stdout.decode().strip() == (
        prepared.base_commit
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


def test_frozen_execution_artifacts_cannot_be_constructed_without_freeze(
    tmp_path: Path,
) -> None:
    with pytest.raises(HistoryExecutionHandoffError, match="freeze capability"):
        history_handoff.FrozenExecutionArtifacts(
            repository=tmp_path,
            parent_commit="1" * 40,
            tree_oid="2" * 40,
            artifact_commit="3" * 40,
            paths=("predictions/2026-08-26__model__v1.0.0.json",),
            files=(),
            created_at=datetime(2026, 8, 24, 12, tzinfo=UTC),
        )


def test_frozen_artifact_capability_is_exact_and_expires_with_workspace(
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
        predictions, _raws = _write_required_predictions(workspace, created_at)
        evaluation, _raw = _write_valid_evaluation(workspace)
        frozen = history_handoff.freeze_execution_outputs(
            workspace,
            tuple(sorted((evaluation, *predictions))),
            created_at=created_at,
        )

        assert (
            history_handoff._require_frozen_execution_artifacts(frozen).artifacts
            is frozen
        )
        original_tree = frozen.tree_oid
        object.__setattr__(frozen, "tree_oid", "f" * 40)
        with pytest.raises(HistoryExecutionHandoffError, match="freeze capability"):
            history_handoff._require_frozen_execution_artifacts(frozen)
        object.__setattr__(frozen, "tree_oid", original_tree)
        with pytest.raises(HistoryExecutionHandoffError, match="freeze capability"):
            replace(frozen, artifact_commit="f" * 40)

    with pytest.raises(HistoryExecutionHandoffError, match="freeze capability"):
        history_handoff._require_frozen_execution_artifacts(frozen)


def test_workspace_revocation_cannot_miss_a_concurrent_artifact_issuance(
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
        predictions, _raws = _write_required_predictions(workspace, created_at)
        evaluation, _raw = _write_valid_evaluation(workspace)
        frozen = history_handoff.freeze_execution_outputs(
            workspace,
            tuple(sorted((evaluation, *predictions))),
            created_at=created_at,
        )
        binding = history_handoff._require_frozen_execution_artifacts(frozen)
        blocked_lock = Lock()
        blocked_lock.acquire()
        revoke_waiting = Event()
        binding.publication_lock = _ObservedLock(blocked_lock, revoke_waiting)
        revoke_errors: list[BaseException] = []

        def revoke() -> None:
            try:
                history_handoff._revoke_frozen_artifacts(workspace._capability)
            except BaseException as exc:  # noqa: BLE001 - thread result capture
                revoke_errors.append(exc)

        revoker = Thread(target=revoke)
        revoker.start()
        assert revoke_waiting.wait(timeout=30)
        try:
            with pytest.raises(HistoryExecutionHandoffError, match="closing"):
                history_handoff._issue_frozen_execution_artifacts(
                    workspace,
                    repository=frozen.repository,
                    parent_commit=frozen.parent_commit,
                    tree_oid=frozen.tree_oid,
                    artifact_commit=frozen.artifact_commit,
                    paths=frozen.paths,
                    files=frozen.files,
                    created_at=frozen.created_at,
                )
        finally:
            blocked_lock.release()
        revoker.join(timeout=30)

        assert not revoker.is_alive()
        assert revoke_errors == []
        assert all(
            candidate.workspace_capability is not workspace._capability
            for candidate in history_handoff._FROZEN_ARTIFACT_CAPABILITIES.values()
        )


def test_two_workspaces_cannot_mutate_the_artifact_registry_during_revocation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _caller, prepared, receipt, authority = _candidate(tmp_path)
    iteration_started = Event()
    release_iteration = Event()
    registry = _ObservedArtifactRegistry(iteration_started, release_iteration)
    monkeypatch.setattr(history_handoff, "_FROZEN_ARTIFACT_CAPABILITIES", registry)

    with (
        _open_execution_workspace(
            receipt,
            authority_url=str(authority),
        ) as first_workspace,
        _open_execution_workspace(
            receipt,
            authority_url=str(authority),
        ) as second_workspace,
    ):
        tree = (
            _git(
                first_workspace.root,
                "rev-parse",
                f"{prepared.publication_commit}^{{tree}}",
            )
            .stdout.decode("ascii")
            .strip()
        )
        created_at = datetime(2026, 8, 24, 12, tzinfo=UTC)

        def issue(workspace: ExecutionWorkspace) -> None:
            history_handoff._issue_frozen_execution_artifacts(
                workspace,
                repository=workspace.root,
                parent_commit=prepared.publication_commit,
                tree_oid=tree,
                artifact_commit=prepared.publication_commit,
                paths=(),
                files=(),
                created_at=created_at,
            )

        issue(first_workspace)
        revoke_errors: list[BaseException] = []
        issue_errors: list[BaseException] = []
        issue_finished = Event()

        def revoke() -> None:
            try:
                history_handoff._revoke_frozen_artifacts(first_workspace._capability)
            except BaseException as exc:  # noqa: BLE001 - thread result capture
                revoke_errors.append(exc)

        def issue_second() -> None:
            try:
                issue(second_workspace)
            except BaseException as exc:  # noqa: BLE001 - thread result capture
                issue_errors.append(exc)
            finally:
                issue_finished.set()

        revoker = Thread(target=revoke)
        issuer = Thread(target=issue_second)
        revoker.start()
        assert iteration_started.wait(timeout=30)
        issuer.start()
        issue_finished.wait(timeout=1)
        release_iteration.set()
        revoker.join(timeout=30)
        issuer.join(timeout=30)

        assert not revoker.is_alive()
        assert not issuer.is_alive()
        assert revoke_errors == []
        assert issue_errors == []
        assert all(
            candidate.workspace_capability is not first_workspace._capability
            for candidate in registry.values()
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


def test_freeze_recomputes_and_rejects_forged_prediction_source(
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
        predictions, _raws = _write_required_predictions(workspace, created_at)
        relative, _raw = _write_valid_evaluation(workspace)
        payload = json.loads((workspace.root / relative).read_text(encoding="utf-8"))
        payload["prediction_source"]["claims"]["promotion_evidence_eligible"] = False
        _write_json(workspace.root / relative, payload)

        with pytest.raises(HistoryExecutionHandoffError, match="evaluation schema"):
            history_handoff.freeze_execution_outputs(
                workspace,
                tuple(sorted((relative, *predictions))),
                created_at=created_at,
            )


def test_freeze_accepts_only_exact_legacy_2026_08_26_prediction_cohort(
    tmp_path: Path,
) -> None:
    prepared, receipt, authority, created_at = _legacy_2026_08_26_candidate(tmp_path)

    with _open_execution_workspace(
        receipt,
        authority_url=str(authority),
    ) as workspace:
        origin_parents = (
            _git(
                workspace.root,
                "rev-list",
                "--parents",
                "-n",
                "1",
                _LEGACY_2026_08_26_ORIGIN,
            )
            .stdout.decode()
            .split()
        )
        assert origin_parents == [
            _LEGACY_2026_08_26_ORIGIN,
            _LEGACY_2026_08_26_PARENT,
        ]
        history_blob, history_sha256, history_bytes = _LEGACY_2026_08_26_HISTORY
        history_raw = _git(
            workspace.root,
            "cat-file",
            "blob",
            f"{_LEGACY_2026_08_26_ORIGIN}:data/processed/draws.csv",
        ).stdout
        assert (
            _git(
                workspace.root,
                "rev-parse",
                f"{_LEGACY_2026_08_26_ORIGIN}:data/processed/draws.csv",
            )
            .stdout.decode()
            .strip()
            == history_blob
        )
        assert len(history_raw) == history_bytes
        assert hashlib.sha256(history_raw).hexdigest() == history_sha256
        assert len(history_raw.splitlines()) - 1 == 4_434
        assert history_raw.splitlines()[-1].startswith(b"2026-08-22,")

        predictions, _raws = _write_required_predictions(workspace, created_at)
        evaluations = []
        for model_name, expected in _LEGACY_2026_08_26_PREDICTIONS.items():
            blob_oid, raw_sha256, raw_bytes, generated_at, role = expected
            relative = f"predictions/2026-08-26__{model_name}__v1.0.0.json"
            raw = _git(
                workspace.root,
                "cat-file",
                "blob",
                f"{_LEGACY_2026_08_26_ORIGIN}:{relative}",
            ).stdout
            assert (
                _git(
                    workspace.root,
                    "rev-parse",
                    f"{_LEGACY_2026_08_26_ORIGIN}:{relative}",
                )
                .stdout.decode()
                .strip()
                == blob_oid
            )
            assert len(raw) == raw_bytes
            assert hashlib.sha256(raw).hexdigest() == raw_sha256
            payload = json.loads(raw)
            assert payload["generated_at"] == generated_at
            assert payload["metadata"] == {
                "history_draws": 4_434,
                "history_through": "2026-08-22",
                "role": role,
            }
            evaluation, evaluation_raw = _write_valid_evaluation(
                workspace,
                model_name=model_name,
            )
            prediction_source = json.loads(evaluation_raw)["prediction_source"]
            assert set(prediction_source) == {
                "claims",
                "kind",
                "legacy_manifest",
                "origin",
                "prediction",
                "schema_version",
                "training_history",
            }
            assert prediction_source["kind"] == "sealed_legacy_incident_history"
            assert prediction_source["claims"] == {
                "corrected_history": False,
                "promotion_evidence_eligible": False,
            }
            assert prediction_source["legacy_manifest"]["sha256"] == (
                "04f115049f81fa462810a18b756e7d893633b0195705bf27d8e4e5c91d52fc02"
            )
            evaluations.append(evaluation)

        output_paths = tuple(sorted((*evaluations, *predictions)))
        frozen = history_handoff.freeze_execution_outputs(
            workspace,
            output_paths,
            created_at=created_at,
        )

        assert frozen.parent_commit == prepared.publication_commit
        assert frozen.paths == output_paths


def test_prediction_source_rejects_legacy_manifest_byte_substitution_at_b_and_p(
    tmp_path: Path,
) -> None:
    _prepared, receipt, authority, _created_at = _legacy_2026_08_26_candidate(
        tmp_path,
        corrupt_manifest=True,
    )

    with _open_execution_workspace(
        receipt,
        authority_url=str(authority),
    ) as workspace:
        with pytest.raises(
            HistoryExecutionHandoffError,
            match="manifest|prediction source",
        ):
            history_handoff.evaluation_prediction_source(
                workspace.root,
                workspace.publication_commit,
                "predictions/2026-08-26__logistic__v1.0.0.json",
            )


def test_freeze_accepts_evaluation_from_immutable_prediction_origin_before_merge(
    tmp_path: Path,
) -> None:
    caller, prepared, receipt, authority = _candidate(
        tmp_path,
        intervening_prediction_history=True,
    )
    base_parents = (
        _git(caller, "rev-list", "--parents", "-n", "1", prepared.base_commit)
        .stdout.decode()
        .split()
    )
    merge_parents = (
        _git(caller, "rev-list", "--parents", "-n", "1", base_parents[1])
        .stdout.decode()
        .split()
    )
    assert len(base_parents) == 2
    assert len(merge_parents) == 3

    with _open_execution_workspace(
        receipt,
        authority_url=str(authority),
    ) as workspace:
        target = workspace.history.draws[-1].draw_date
        prediction_relative = (
            f"predictions/{target.isoformat()}__handoff_fixture__v1.0.0.json"
        )
        prediction_origins = (
            _git(
                workspace.root,
                "log",
                "--format=%H",
                "--diff-filter=A",
                "--",
                prediction_relative,
            )
            .stdout.decode()
            .splitlines()
        )
        assert len(prediction_origins) == 1
        origin_parents = (
            _git(
                workspace.root,
                "rev-list",
                "--parents",
                "-n",
                "1",
                prediction_origins[0],
            )
            .stdout.decode()
            .split()
        )
        assert len(origin_parents) == 2

        created_at = datetime.combine(
            target + timedelta(days=1),
            datetime.min.time(),
            UTC,
        ).replace(hour=12)
        predictions, _raws = _write_required_predictions(workspace, created_at)
        relative, evaluation_raw = _write_valid_evaluation(workspace)
        prediction_source = json.loads(evaluation_raw)["prediction_source"]
        assert set(prediction_source) == {
            "claims",
            "kind",
            "origin",
            "prediction",
            "schema_version",
            "training_history",
        }
        assert prediction_source["schema_version"] == (
            "lotto649-evaluation-prediction-source-v1"
        )
        assert prediction_source["kind"] == "verified_operational_history"
        assert prediction_source["claims"] == {
            "corrected_history": True,
            "promotion_evidence_eligible": True,
        }
        assert set(prediction_source["origin"]) == {
            "commit",
            "commit_raw_sha256",
            "committed_at",
            "parent",
            "resolved_from_base_commit",
        }
        assert set(prediction_source["prediction"]) == {
            "bytes",
            "generated_at",
            "git_blob",
            "mode",
            "path",
            "role",
            "sha256",
        }
        output_paths = tuple(sorted((relative, *predictions)))

        frozen = history_handoff.freeze_execution_outputs(
            workspace,
            output_paths,
            created_at=created_at,
        )

        assert frozen.parent_commit == prepared.publication_commit
        assert frozen.paths == output_paths


@pytest.mark.parametrize(
    "prediction_history_attack",
    (
        "side_add",
        "side_conflict",
        "mutate_restore",
        "delete_readd",
        "mode_flip",
    ),
)
def test_prediction_source_rejects_any_path_history_after_its_unique_origin(
    tmp_path: Path,
    prediction_history_attack: str,
) -> None:
    _caller, _prepared, receipt, authority = _candidate(
        tmp_path,
        prediction_history_attack=prediction_history_attack,
    )

    with _open_execution_workspace(
        receipt,
        authority_url=str(authority),
    ) as workspace:
        target = workspace.history.draws[-1].draw_date
        prediction_relative = (
            f"predictions/{target.isoformat()}__handoff_fixture__v1.0.0.json"
        )

        with pytest.raises(HistoryExecutionHandoffError, match="prediction"):
            history_handoff.evaluation_prediction_source(
                workspace.root,
                workspace.publication_commit,
                prediction_relative,
            )


def test_evaluation_prediction_source_requires_a_real_path_object(
    tmp_path: Path,
) -> None:
    _caller, _prepared, receipt, authority = _candidate(tmp_path)

    with _open_execution_workspace(
        receipt,
        authority_url=str(authority),
    ) as workspace:
        target = workspace.history.draws[-1].draw_date
        prediction_relative = (
            f"predictions/{target.isoformat()}__handoff_fixture__v1.0.0.json"
        )

        source = history_handoff.evaluation_prediction_source(
            workspace.root,
            workspace.publication_commit,
            prediction_relative,
        )
        assert source["kind"] == "verified_operational_history"
        with pytest.raises(HistoryExecutionHandoffError, match="must be a Path"):
            history_handoff.evaluation_prediction_source(
                str(workspace.root),
                workspace.publication_commit,
                prediction_relative,
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
        relative, _raw = _write_valid_evaluation(
            workspace,
            classify_prediction_source=False,
        )
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


@pytest.mark.parametrize("history_substitution", ("graft", "replacement_ref"))
def test_prediction_source_rejects_git_history_substitution_controls(
    tmp_path: Path,
    history_substitution: str,
) -> None:
    _caller, prepared, receipt, authority = _candidate(tmp_path)

    with _open_execution_workspace(
        receipt,
        authority_url=str(authority),
    ) as workspace:
        if history_substitution == "graft":
            grafts = workspace.root / ".git" / "info" / "grafts"
            grafts.parent.mkdir(parents=True, exist_ok=True)
            grafts.write_text(
                f"{prepared.base_commit} {prepared.base_commit}^\n",
                encoding="ascii",
            )
        else:
            _git(
                workspace.root,
                "replace",
                prepared.base_commit,
                f"{prepared.base_commit}^",
            )
        target = workspace.history.draws[-1].draw_date
        prediction_relative = (
            f"predictions/{target.isoformat()}__handoff_fixture__v1.0.0.json"
        )

        with pytest.raises(
            HistoryExecutionHandoffError,
            match="self-contained|replacement history",
        ):
            history_handoff.evaluation_prediction_source(
                workspace.root,
                workspace.publication_commit,
                prediction_relative,
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
