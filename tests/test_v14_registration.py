"""Offline V14 registration checks: source bytes, Git metadata and exact math only.

No project import, historical data/result blob, actual prediction, canonical
attempt, authorization capability, lease, worker or network is exercised.
The synthetic Git repositories contain only fabricated inert source bytes.

Author: /root/v13_exception_spec_review
Session: v14-registration-tests-authoring-20260913
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import re
import subprocess
from datetime import date, timedelta
from fractions import Fraction
from functools import lru_cache
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REG = "evidence/research_registrations/v14-long-frequency-fixed-five-disjoint-groups-v1.json"
CONFIG = "config/research-v14-long-frequency-fixed-five-disjoint-groups.yaml"
EXPERIMENT = "docs/experiments/V14_long_frequency_fixed_five_disjoint_groups.md"
BASIS = "docs/research/V14_long_frequency_fixed_five_disjoint_groups_basis.md"
TEST = "tests/test_v14_registration.py"
BASE = "b1c99b02d9e18ca66b806b00c41a739daeae6740"
SCIENCE_SHA = "eea3c0e7e4c5ba93859757e4e994d9d8be1a3a5f7f8b071a89d9bf57e28e60f1"
OPERATION_SHA = "3b12f518e51089fd529787f013a4a3db14cabfdf18a209f63546969a7a5946e2"
STATUS = ["REGISTERED", "NOT IMPLEMENTED", "NOT AUTHORIZED", "NOT SCORED"]
MODIFIED = {
    "docs/CODEX_HANDOFF.md",
    "docs/MODEL_PROTOCOL.md",
    "docs/RESEARCH_ROADMAP.md",
}
ARCHIVE_ROOT = "evidence/research_preparation/v14-fixed-five-20260913"
ARCHIVE_INPUTS = {
    "pre-outcome-concept.md": {
        "bytes": 11077,
        "sha256": "687889c948d9351c012a4e291c905ee4d469d87a5d8e25f2ea34cc7d5edb4e89",
    },
    "source-map.md": {
        "bytes": 17207,
        "sha256": "986b238a6d7424ff02089a8a8576bf00ca0887fd5f9eafc09f805747f95a2fda",
    },
    "science-v2-original.md": {
        "bytes": 35641,
        "sha256": "92c8b07dcd0b02b7998ce9d0f092292a25040b6f429d7e7de833e61da25f6fac",
    },
    "math-contract.md": {
        "bytes": 14632,
        "sha256": "65144487d26e4f889759e9b8d61304a8983b04361ff005b3524f9b09a8ac3c8c",
    },
    "math-oracle.py.txt": {
        "bytes": 4523,
        "sha256": "6c84f5827b45ddb8384945f7463456fbcdd10d8c75686beaaea9c347f5fe87e3",
    },
    "math-oracle-result.json": {
        "bytes": 36704,
        "sha256": "26848efeb56618195b0da11ca3dac8ea2171b60d7f09ffcc2d12a6a81bc09a8d",
    },
    "independent-math-review.md": {
        "bytes": 9042,
        "sha256": "ee622a61a5a5cbfbf7733a369905e26ccb960307cd8f3b54f62765a3864c0176",
    },
    "independent-science-v2-review.md": {
        "bytes": 3887,
        "sha256": "2b80b084e3fe03d81175d17e8a686d9d2a7b13236f1e34f69203c5bc12043884",
    },
    "synthetic-validator-v1.py.txt": {
        "bytes": 25937,
        "sha256": "b0a4edd72108b92f8912d5b168d0ca4351a41730185e0c4c5c9dbaf150074d26",
    },
    "synthetic-v1-failure.json": {
        "bytes": 3235,
        "sha256": "995a4138ca6d08a2c161d1b420ab977fd3437638e94c87e8df2dbaeb4a5612ac",
    },
    "synthetic-validator-v2.py.txt": {
        "bytes": 26401,
        "sha256": "b049983864a89b1f29f67cc26bdb01f7e82396707055f02b08e63af2d979b701",
    },
    "synthetic-v2-result.json": {
        "bytes": 10880,
        "sha256": "e1617d6d22f43b1f6abe11fff647e4664037025a2a8e164464375a3651e9d3e4",
    },
    "synthetic-v2.log": {
        "bytes": 196,
        "sha256": "44e9467611513d577320e3da31646a3919629e920e0b33272f669b80e609f414",
    },
    "synthetic-static-review.md": {
        "bytes": 4827,
        "sha256": "46c445f8367faa6612e3cbd5acb33affbc4384217baaef620c51fc14660ba969",
    },
    "synthetic-v2-static-delta-review.json": {
        "bytes": 576,
        "sha256": "fa4aa0446b63e0cbda3c6d8583de43bc5ddab38707df44dfd4cdba23b6cce9f1",
    },
    "original-operational-map.md": {
        "bytes": 28598,
        "sha256": "7bb87c8b945c1c233d298ee5c31f99fecfabfb924db391045d41bdf6c26d70c4",
    },
}
ARCHIVE_PATHS = {
    f"{ARCHIVE_ROOT}/{name}" for name in (*ARCHIVE_INPUTS, "README.md", "manifest.json")
}
ADDED = {EXPERIMENT, BASIS, CONFIG, REG, TEST} | ARCHIVE_PATHS
ALLOWED = MODIFIED | ADDED
IMPLEMENTATION = [
    "src/lotto649/models/v14_long_frequency.py",
    "src/lotto649/v14_five_group_selection.py",
    "src/lotto649/v14_evidence.py",
    "src/lotto649/v14_registered_attempt.py",
    "tools/run_v14_historical.py",
    "tests/test_v14_probability_selection.py",
    "tests/test_v14_evidence.py",
    "tests/test_v14_registered_attempt.py",
    "tests/fixtures/v14_git_commit_projection.json",
]
NOTIFICATION_REGISTRATION = {
    "docs/experiments/V14_capture_notification_delivery.md",
    "evidence/research_registrations/v14-capture-notification-v1.json",
}
NOTIFICATION_IMPLEMENTATION = {
    ".github/workflows/v14-audited-capture-email.yml",
    ".github/workflows/v14-notification-readiness.yml",
    "src/lotto649/v14_capture_notification.py",
    "tools/notify_v14_audited_capture.py",
    "tests/test_v14_capture_notification.py",
    "tests/fixtures/v14_notification_git_projection.json",
}
CONTRIBUTORS = [
    ["/root", "01a07e02-2cf6-77f2-92ad-125229fa0a95"],
    ["/root/multi_group_research_design_check", "01a07e02-2cf6-77f2-92ad-125229fa0a95"],
    [
        "/root/v13_auth_helper_readiness_review",
        "v14-operational-registration-authoring-20260913",
    ],
    [
        "/root/v13_exception_spec_review",
        "successor-probability-synthetic-authoring-20260913",
    ],
    [
        "/root/v13_exception_spec_review",
        "v13-successor-five-group-math-authoring-20260913",
    ],
    ["/root/v13_exception_spec_review", "v14-registration-tests-authoring-20260913"],
    [
        "/root/v13_test_exception_contract_map",
        "v14-complete-scientific-registration-basis-authoring-20260913",
    ],
    [
        "/root/v13_test_exception_contract_map",
        "v14-scientific-contract-authoring-20260913",
    ],
    [
        "/root/v14_default_notification_route_map",
        "v14-default-notification-route-map-20260913",
    ],
    [
        "/root/v14_default_notification_route_map",
        "v14-github-protection-token-capability-research-20260913",
    ],
]
SCHEMA = {
    "schema_version",
    "experiment_id",
    "model_version",
    "status",
    "registration_base",
    "scientific_contract",
    "statistical_fingerprint_sha256",
    "operational_contract",
    "operational_contract_sha256",
    "registered_files",
    "preserved_tree_manifest",
    "preserved_tree_manifest_sha256",
    "preparation_provenance",
}
AUTHOR = (
    "/root/v13_exception_spec_review",
    "v14-registration-tests-authoring-20260913",
)
ROOT_AUTHOR = ("/root", "01a07e02-2cf6-77f2-92ad-125229fa0a95")


def _plain(value):
    if value is None or type(value) in {str, bool, int}:
        return
    if type(value) is float:
        assert math.isfinite(value), "nonfinite JSON value"
        return
    if type(value) is list:
        for item in value:
            _plain(item)
        return
    assert type(value) is dict, "plain JSON types required"
    assert all(type(key) is str for key in value), "string JSON keys required"
    for item in value.values():
        _plain(item)


def _canonical(value):
    _plain(value)
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _unique(pairs):
    result = {}
    for key, value in pairs:
        assert key not in result, "duplicate JSON key"
        result[key] = value
    return result


def _decode(raw):
    assert type(raw) is bytes, "bytes required"
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique)
    assert _canonical(value) == raw, "noncanonical JSON bytes"
    return value


def _hex(value, length):
    assert type(value) is str and re.fullmatch(f"[0-9a-f]{{{length}}}", value), (
        "canonical lowercase digest required"
    )


def _path(value):
    assert type(value) is str and value and "\\" not in value, "unsafe path"
    assert not value.startswith("/") and "\x00" not in value, "unsafe path"
    assert all(character.isprintable() for character in value), "unsafe path"
    assert all(part not in {"", ".", ".."} for part in value.split("/")), "unsafe path"


def _git(*args):
    environment = {
        "PATH": os.defpath,
        "LC_ALL": "C",
        "LANG": "C",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_GRAFT_FILE": "/dev/null",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_NO_LAZY_FETCH": "1",
    }
    return subprocess.run(
        (
            "git",
            "-c",
            "core.hooksPath=/dev/null",
            "-c",
            "core.fsmonitor=false",
            "-c",
            "protocol.allow=never",
            "-c",
            "advice.graftFileDeprecated=false",
            *args,
        ),
        cwd=ROOT,
        env=environment,
        capture_output=True,
        check=False,
    )


def _require_git(*args):
    result = _git(*args)
    assert result.returncode == 0, "fixed read-only Git request failed"
    return result.stdout


@lru_cache(maxsize=32)
def _authority_for_head(repository, head):
    assert Path(repository) == ROOT
    rows = _require_git("rev-list", "--parents", head).decode("ascii").splitlines()
    matches = []
    addition = f"A\t{REG}\n".encode()
    for row in rows:
        commit, *parents = row.split()
        for oid in (commit, *parents):
            _hex(oid, 40)
        if not parents:
            assert _git("cat-file", "-e", f"{commit}:{REG}").returncode != 0, (
                "registration root/merge introduction lacks ordinary ADD"
            )
            continue
        changes = [
            _require_git(
                "diff-tree",
                "--no-commit-id",
                "--name-status",
                "--no-renames",
                "-r",
                parent,
                commit,
                "--",
                REG,
            )
            for parent in parents
        ]
        assert all(change in {b"", addition} for change in changes), (
            "immutable registration changed on a reachable parent-child edge"
        )
        if all(change == addition for change in changes):
            assert len(parents) == 1, (
                "registration root/merge introduction lacks ordinary ADD"
            )
            matches.append(commit)
        # A normal merge may import the seal into a parent that lacked it, but
        # at least one other parent must carry exactly the unchanged seal.
    assert len(matches) <= 1, "ambiguous registration ADD authority"
    if not matches:
        assert _git("cat-file", "-e", f"{head}:{REG}").returncode != 0, (
            "committed registration lacks ordinary ADD authority"
        )
        return None
    return matches[0]


def _authority():
    # Traverse every reachable ancestor. A path-limited log can simplify away
    # an independently introduced same-blob side-branch registration.
    assert _require_git("rev-parse", "--is-shallow-repository") == b"false\n", (
        "full Git history required"
    )
    head = _require_git("rev-parse", "--verify", "HEAD").decode("ascii").strip()
    _hex(head, 40)
    return _authority_for_head(str(ROOT), head)


def _at_source(path, authority):
    _path(path)
    if authority is not None:
        return _require_git("show", f"{authority}:{path}")
    current = ROOT
    for part in path.split("/"):
        current /= part
        assert not current.is_symlink(), "draft source cannot be symlink"
    return current.read_bytes()


def _tree(ref):
    records = []
    for raw in _require_git("ls-tree", "-r", "-z", ref).split(b"\x00"):
        if not raw:
            continue
        metadata, path = raw.split(b"\t", 1)
        mode, kind, oid = metadata.decode("ascii").split()
        records.append(
            {"mode": mode, "type": kind, "oid": oid, "path": path.decode("utf-8")}
        )
    return sorted(records, key=lambda item: item["path"])


def _validate_seal(value):
    assert type(value) is dict and set(value) == SCHEMA, "closed registration schema"
    assert value["schema_version"] == "lotto649-v14-registration-v1"
    assert value["experiment_id"] == "V14_long_frequency_fixed_five_disjoint_groups"
    assert value["model_version"] == "v14.0.0"
    assert type(value["status"]) is list and value["status"] == STATUS, "closed status"
    assert value["registration_base"] == BASE, "fixed registration base"
    assert type(value["scientific_contract"]) is dict
    assert value["statistical_fingerprint_sha256"] == SCIENCE_SHA
    assert _sha(_canonical(value["scientific_contract"])) == SCIENCE_SHA, (
        "scientific fingerprint mismatch"
    )
    assert type(value["operational_contract"]) is dict
    _hex(value["operational_contract_sha256"], 64)
    assert value["operational_contract_sha256"] == OPERATION_SHA, (
        "fixed operational contract"
    )
    assert (
        _sha(_canonical(value["operational_contract"]))
        == (value["operational_contract_sha256"])
    ), "operational fingerprint mismatch"
    records = value["registered_files"]
    assert type(records) is list and len(records) == len(ALLOWED) - 1
    paths = []
    for record in records:
        assert type(record) is dict and set(record) == {
            "path",
            "git_blob",
            "bytes",
            "sha256",
        }, "closed registered-file record"
        _path(record["path"])
        _hex(record["git_blob"], 40)
        _hex(record["sha256"], 64)
        assert type(record["bytes"]) is int and record["bytes"] > 0
        paths.append(record["path"])
    assert paths == sorted(ALLOWED - {REG}), "exact registered paths, no self-seal"
    preserved = value["preserved_tree_manifest"]
    assert type(preserved) is list and preserved
    paths = []
    for record in preserved:
        assert type(record) is dict and set(record) == {
            "mode",
            "type",
            "oid",
            "path",
        }, "closed preserved-tree record"
        _path(record["path"])
        _hex(record["oid"], 40)
        assert record["mode"] in {"100644", "100755", "120000", "160000"}
        assert record["type"] == ("commit" if record["mode"] == "160000" else "blob")
        assert record["path"] not in ALLOWED
        paths.append(record["path"])
    assert paths == sorted(set(paths)), "unique sorted preserved-tree paths"
    _hex(value["preserved_tree_manifest_sha256"], 64)
    assert _sha(_canonical(preserved)) == value["preserved_tree_manifest_sha256"], (
        "preservation fingerprint mismatch"
    )
    provenance = value["preparation_provenance"]
    assert type(provenance) is dict and set(provenance) == {"contributors", "scope"}
    assert type(provenance["scope"]) is str and provenance["scope"].strip()
    assert all(character.isprintable() for character in provenance["scope"])
    contributors = provenance["contributors"]
    assert type(contributors) is list and 1 <= len(contributors) <= 64
    pairs = []
    for contributor in contributors:
        assert type(contributor) is dict and set(contributor) == {
            "agent_id",
            "session_id",
            "role",
        }, "closed authoring contributor record"
        for field in contributor.values():
            assert type(field) is str and field == field.strip() and field
            assert all(character.isprintable() for character in field)
            assert len(field.encode("utf-8")) <= 256
        pairs.append((contributor["agent_id"], contributor["session_id"]))
    assert pairs == sorted(set(pairs)), "unique sorted actual authoring sessions"
    assert AUTHOR in pairs, "actual registration test author must be disclosed"
    assert ROOT_AUTHOR in pairs, "actual root integration session must be disclosed"
    assert set(pairs) == {tuple(pair) for pair in CONTRIBUTORS}, (
        "complete fixed actual authoring provenance"
    )


@pytest.fixture(scope="module")
def registration():
    raw = _at_source(REG, None)
    value = _decode(raw)
    _validate_seal(value)
    authority = _authority()
    assert _at_source(REG, authority) == raw, "registration seal changed after source"
    return value


def test_v14_registered_files_bind_exact_source_bytes(registration):
    authority = _authority()
    for record in registration["registered_files"]:
        raw = _at_source(record["path"], authority)
        blob = hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()
        assert record == {
            "path": record["path"],
            "git_blob": blob,
            "bytes": len(raw),
            "sha256": _sha(raw),
        }, record["path"]


def test_v14_source_preserves_all_prior_tree_objects_without_opening_them(registration):
    expected = [record for record in _tree(BASE) if record["path"] not in ALLOWED]
    assert registration["preserved_tree_manifest"] == expected
    authority = _authority()
    actual = [
        record for record in _tree(authority or "HEAD") if record["path"] not in ALLOWED
    ]
    assert actual == expected


def test_v14_registration_source_has_exactly_twenty_six_changes(registration):
    authority = _authority()
    expected = {f"M\t{path}" for path in MODIFIED} | {f"A\t{path}" for path in ADDED}
    if authority is not None:
        parent = _require_git("rev-parse", f"{authority}^").decode("ascii").strip()
        assert parent == BASE
        changes = _require_git("diff", "--name-status", "--no-renames", BASE, authority)
        assert set(changes.decode("utf-8").splitlines()) == expected
    else:
        tracked = _require_git("diff", "--name-status", "--no-renames", BASE)
        untracked = _require_git("ls-files", "--others", "--exclude-standard", "-z")
        changes = set(tracked.decode("utf-8").splitlines())
        changes |= {
            "A\t" + path.decode("utf-8") for path in untracked.split(b"\0") if path
        }
        assert changes == expected


@pytest.mark.parametrize(
    "raw",
    [
        b'{"x":1,"x":2}\n',
        b'{"x": NaN}\n',
        b'{"x":Infinity}\n',
        b'{"x":-Infinity}\n',
        b'{"x":1}',
        b'{ "x":1}\n',
        b'{"x":1}\n\n',
    ],
)
def test_v14_rejects_noncanonical_or_duplicate_json(raw):
    with pytest.raises(AssertionError):
        _decode(raw)


@pytest.fixture
def synthetic_git_repository(tmp_path, monkeypatch):
    environment = {
        "PATH": os.defpath,
        "LC_ALL": "C",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_GRAFT_FILE": "/dev/null",
        "GIT_AUTHOR_NAME": "Synthetic Registration Fixture",
        "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
        "GIT_COMMITTER_NAME": "Synthetic Registration Fixture",
        "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
        "GIT_AUTHOR_DATE": "2001-01-01T00:00:00Z",
        "GIT_COMMITTER_DATE": "2001-01-01T00:00:00Z",
    }

    def run(*args):
        return subprocess.run(
            (
                "git",
                "-c",
                "core.hooksPath=/dev/null",
                "-c",
                "commit.gpgsign=false",
                *args,
            ),
            cwd=tmp_path,
            env=environment,
            capture_output=True,
            check=True,
        ).stdout

    run("init", "-b", "main")
    run("commit", "--allow-empty", "-m", "synthetic base")
    monkeypatch.setitem(globals(), "ROOT", tmp_path)
    return run


def _write_synthetic_seal():
    path = ROOT / REG
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b'{"synthetic_fixture_only":true}\n')


def test_v14_draft_fallback_only_before_seal_exists_at_head(synthetic_git_repository):
    run = synthetic_git_repository
    _write_synthetic_seal()
    assert _authority() is None
    run("add", "--", REG)
    run("commit", "-m", "synthetic ordinary registration")
    source = run("rev-parse", "HEAD").decode("ascii").strip()
    assert _authority() == source
    assert _at_source(REG, source) == b'{"synthetic_fixture_only":true}\n'


def test_v14_source_absence_is_not_rechecked_at_later_implementation_head(
    synthetic_git_repository,
):
    run = synthetic_git_repository
    _write_synthetic_seal()
    run("add", "--", REG)
    run("commit", "-m", "synthetic registration")
    source = run("rev-parse", "HEAD").decode("ascii").strip()
    path = ROOT / IMPLEMENTATION[0]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('"""Inert synthetic source; never imported."""\n')
    run("add", "--", IMPLEMENTATION[0])
    run("commit", "-m", "synthetic later implementation")
    assert _authority() == source
    assert IMPLEMENTATION[0] not in {record["path"] for record in _tree(source)}
    assert IMPLEMENTATION[0] in {record["path"] for record in _tree("HEAD")}


def test_v14_rejects_two_reachable_same_blob_additions(synthetic_git_repository):
    run = synthetic_git_repository
    base = run("rev-parse", "HEAD").decode("ascii").strip()
    for branch in ("left", "right"):
        run("checkout", "-b", branch, base)
        _write_synthetic_seal()
        run("add", "--", REG)
        run("commit", "-m", "synthetic " + branch)
    run("merge", "--no-ff", "left", "-m", "synthetic same-blob merge")
    with pytest.raises(AssertionError, match="ambiguous registration ADD authority"):
        _authority()


def test_v14_rejects_deleted_then_readded_registration(synthetic_git_repository):
    run = synthetic_git_repository
    _write_synthetic_seal()
    run("add", "--", REG)
    run("commit", "-m", "synthetic first addition")
    run("rm", "--", REG)
    run("commit", "-m", "synthetic deletion")
    _write_synthetic_seal()
    run("add", "--", REG)
    run("commit", "-m", "synthetic repeated addition")
    with pytest.raises(AssertionError, match="immutable registration changed"):
        _authority()


def test_v14_rejects_merge_only_registration(synthetic_git_repository):
    run = synthetic_git_repository
    run("checkout", "-b", "side")
    run("commit", "--allow-empty", "-m", "synthetic side")
    run("checkout", "main")
    run("merge", "--no-ff", "--no-commit", "side")
    _write_synthetic_seal()
    run("add", "--", REG)
    run("commit", "-m", "synthetic merge-only addition")
    with pytest.raises(AssertionError, match="ordinary ADD|one parent"):
        _authority()


def test_v14_draft_symlink_cannot_supply_source_bytes(tmp_path, monkeypatch):
    monkeypatch.setitem(globals(), "ROOT", tmp_path)
    outside = tmp_path / "synthetic-outside"
    outside.write_bytes(b"inert fixture")
    parent = tmp_path / "docs"
    parent.mkdir()
    (parent / "fixture.md").symlink_to(outside)
    with pytest.raises(AssertionError, match="symlink"):
        _at_source("docs/fixture.md", None)


def test_v14_rejects_hidden_merge_origin_even_with_one_ordinary_add(
    synthetic_git_repository,
):
    run = synthetic_git_repository
    base = run("rev-parse", "HEAD").decode("ascii").strip()
    run("checkout", "-b", "ordinary", base)
    _write_synthetic_seal()
    run("add", "--", REG)
    run("commit", "-m", "synthetic ordinary addition")
    run("checkout", "-b", "merge-origin", base)
    run("checkout", "-b", "inert-side")
    run("commit", "--allow-empty", "-m", "synthetic inert side")
    run("checkout", "merge-origin")
    run("merge", "--no-ff", "--no-commit", "inert-side")
    _write_synthetic_seal()
    run("add", "--", REG)
    run("commit", "-m", "synthetic second merge-only origin")
    run("merge", "--no-ff", "ordinary", "-m", "synthetic identical-blob merge")
    with pytest.raises(AssertionError, match="root/merge introduction"):
        _authority()


def test_v14_rejects_root_commit_registration(synthetic_git_repository):
    run = synthetic_git_repository
    run("checkout", "--orphan", "synthetic-root")
    _write_synthetic_seal()
    run("add", "--", REG)
    run("commit", "-m", "synthetic invalid root registration")
    with pytest.raises(AssertionError, match="root/merge introduction"):
        _authority()


def test_v14_rejects_modify_then_restore_same_seal_blob(synthetic_git_repository):
    run = synthetic_git_repository
    _write_synthetic_seal()
    run("add", "--", REG)
    run("commit", "-m", "synthetic registration")
    (ROOT / REG).write_bytes(b'{"synthetic_fixture_only":"altered"}\n')
    run("add", "--", REG)
    run("commit", "-m", "synthetic forbidden modification")
    _write_synthetic_seal()
    run("add", "--", REG)
    run("commit", "-m", "synthetic byte restoration")
    with pytest.raises(AssertionError, match="immutable registration changed"):
        _authority()


def test_v14_rejects_delete_then_merge_restore_without_second_ordinary_add(
    synthetic_git_repository,
):
    run = synthetic_git_repository
    _write_synthetic_seal()
    run("add", "--", REG)
    run("commit", "-m", "synthetic registration")
    source = run("rev-parse", "HEAD").decode("ascii").strip()
    run("checkout", "-b", "kept", source)
    run("commit", "--allow-empty", "-m", "synthetic retained branch")
    run("checkout", "-b", "deleted", source)
    run("rm", "--", REG)
    run("commit", "-m", "synthetic forbidden deletion")
    run("merge", "--no-ff", "--no-commit", "kept")
    _write_synthetic_seal()
    run("add", "--", REG)
    run("commit", "-m", "synthetic merge restoration")
    with pytest.raises(AssertionError, match="immutable registration changed"):
        _authority()


def test_v14_ordinary_merge_can_import_unchanged_registration(synthetic_git_repository):
    run = synthetic_git_repository
    run("checkout", "-b", "registration")
    _write_synthetic_seal()
    run("add", "--", REG)
    run("commit", "-m", "synthetic registration")
    source = run("rev-parse", "HEAD").decode("ascii").strip()
    run("checkout", "main")
    run("commit", "--allow-empty", "-m", "synthetic main progress")
    run("merge", "--no-ff", "registration", "-m", "synthetic normal merge")
    assert _authority() == source


def _validate_config(value):
    expected = {
        "schema_version": "lotto649-v14-inert-config-v1",
        "experiment_id": "V14_long_frequency_fixed_five_disjoint_groups",
        "model_version": "v14.0.0",
        "registration_path": REG,
        "statistical_fingerprint_sha256": SCIENCE_SHA,
        "operational_contract_sha256": OPERATION_SHA,
        "historical_enabled": False,
        "live_enabled": False,
        "dispatch_enabled": False,
        "default_model_activation": False,
    }
    assert type(value) is dict and set(value) == set(expected), (
        "closed configuration schema"
    )
    for key in (
        "historical_enabled",
        "live_enabled",
        "dispatch_enabled",
        "default_model_activation",
    ):
        assert value[key] is False, "registration configuration must remain inactive"
    assert value == expected, "fixed inert configuration identity"


def test_v14_config_has_no_execution_authority(registration):
    assert len(SCHEMA) == 13
    assert len(ALLOWED) == 26 and len(ARCHIVE_PATHS) == 18
    assert len(registration["registered_files"]) == 25
    _validate_config(_decode(_at_source(CONFIG, _authority())))


@pytest.mark.parametrize(
    "mutation",
    [
        "extra",
        "missing",
        "historical",
        "live",
        "dispatch",
        "default",
        "numeric_false",
        "science_digest",
        "operation_digest",
        "registration_path",
        "model_version",
    ],
)
def test_v14_rejects_config_activation_or_identity_changes(registration, mutation):
    value = _decode(_at_source(CONFIG, _authority()))
    if mutation == "extra":
        value["worker"] = "run"
    elif mutation == "missing":
        del value["dispatch_enabled"]
    elif mutation in {"historical", "live", "dispatch"}:
        value[mutation + "_enabled"] = True
    elif mutation == "default":
        value["default_model_activation"] = True
    elif mutation == "numeric_false":
        value["historical_enabled"] = 0
    elif mutation == "science_digest":
        value["statistical_fingerprint_sha256"] = "0" * 64
    elif mutation == "operation_digest":
        value["operational_contract_sha256"] = "0" * 64
    elif mutation == "registration_path":
        value["registration_path"] = "../authorization.json"
    elif mutation == "model_version":
        value["model_version"] = "v13.0.0"
    with pytest.raises(AssertionError):
        _validate_config(value)


@pytest.mark.parametrize(
    "mutation",
    [
        "extra_key",
        "missing_key",
        "status",
        "status_tuple",
        "wrong_version",
        "wrong_base",
        "science",
        "science_digest",
        "redigested_science",
        "operation",
        "operation_digest",
        "redigested_operation",
        "preserved_digest",
        "reordered_files",
        "duplicate_file",
        "self_seal",
        "path_escape",
        "bool_size",
        "file_extra_key",
        "uppercase_blob",
        "preserved_extra_key",
        "preserved_mode",
        "duplicate_preserved",
        "empty_provenance",
        "duplicate_contributor",
        "missing_contributor",
        "unsafe_contributor",
        "invented_contributor",
    ],
)
def test_v14_rejects_mutated_closed_registration(registration, mutation):
    value = copy.deepcopy(registration)
    if mutation == "extra_key":
        value["execution_permission"] = True
    elif mutation == "missing_key":
        del value["status"]
    elif mutation == "status":
        value["status"][-1] = "SCORED"
    elif mutation == "status_tuple":
        value["status"] = tuple(STATUS)
    elif mutation == "wrong_version":
        value["model_version"] = "v13.0.0"
    elif mutation == "wrong_base":
        value["registration_base"] = "a" * 40
    elif mutation in {"science", "redigested_science"}:
        value["scientific_contract"]["unregistered_override"] = True
        if mutation == "redigested_science":
            value["statistical_fingerprint_sha256"] = _sha(
                _canonical(value["scientific_contract"])
            )
    elif mutation == "science_digest":
        value["statistical_fingerprint_sha256"] = "0" * 64
    elif mutation in {"operation", "redigested_operation"}:
        value["operational_contract"]["unregistered_override"] = True
        if mutation == "redigested_operation":
            value["operational_contract_sha256"] = _sha(
                _canonical(value["operational_contract"])
            )
    elif mutation == "operation_digest":
        value["operational_contract_sha256"] = "0" * 64
    elif mutation == "preserved_digest":
        value["preserved_tree_manifest_sha256"] = "0" * 64
    elif mutation == "reordered_files":
        value["registered_files"].reverse()
    elif mutation == "duplicate_file":
        value["registered_files"][1] = value["registered_files"][0]
    elif mutation == "self_seal":
        value["registered_files"][0]["path"] = REG
    elif mutation == "path_escape":
        value["registered_files"][0]["path"] = "docs/../config.yaml"
    elif mutation == "bool_size":
        value["registered_files"][0]["bytes"] = True
    elif mutation == "file_extra_key":
        value["registered_files"][0]["capability"] = True
    elif mutation == "uppercase_blob":
        value["registered_files"][0]["git_blob"] = "A" * 40
    elif mutation == "preserved_extra_key":
        value["preserved_tree_manifest"][0]["payload"] = "not permitted"
    elif mutation == "preserved_mode":
        value["preserved_tree_manifest"][0]["mode"] = "040000"
    elif mutation == "duplicate_preserved":
        value["preserved_tree_manifest"].append(value["preserved_tree_manifest"][0])
    elif mutation == "empty_provenance":
        value["preparation_provenance"] = []
    elif mutation == "duplicate_contributor":
        value["preparation_provenance"]["contributors"].append(
            value["preparation_provenance"]["contributors"][0]
        )
    elif mutation == "missing_contributor":
        value["preparation_provenance"]["contributors"].pop()
    elif mutation == "unsafe_contributor":
        value["preparation_provenance"]["contributors"][0]["role"] = "role\nsecond line"
    elif mutation == "invented_contributor":
        value["preparation_provenance"]["contributors"][0]["agent_id"] = "/invented"
    with pytest.raises(AssertionError):
        _validate_seal(value)


def test_v14_preparation_archive_keeps_original_bytes_inert(registration):
    records = {row["path"]: row for row in registration["registered_files"]}
    assert set(ARCHIVE_INPUTS) == {
        "pre-outcome-concept.md",
        "source-map.md",
        "science-v2-original.md",
        "math-contract.md",
        "math-oracle.py.txt",
        "math-oracle-result.json",
        "independent-math-review.md",
        "independent-science-v2-review.md",
        "synthetic-validator-v1.py.txt",
        "synthetic-v1-failure.json",
        "synthetic-validator-v2.py.txt",
        "synthetic-v2-result.json",
        "synthetic-v2.log",
        "synthetic-static-review.md",
        "synthetic-v2-static-delta-review.json",
        "original-operational-map.md",
    }
    for name, expected in ARCHIVE_INPUTS.items():
        path = f"{ARCHIVE_ROOT}/{name}"
        assert records[path]["bytes"] == expected["bytes"]
        assert records[path]["sha256"] == expected["sha256"]
        # These are reviewed source/preparation/synthetic receipts, not draw evidence.
        raw = _at_source(path, _authority())
        assert len(raw) == expected["bytes"] and _sha(raw) == expected["sha256"]
    assert not any(path.endswith(".py") for path in ARCHIVE_PATHS)
    assert not any(Path(path).name.startswith("test_") for path in ARCHIVE_PATHS)


def test_v14_future_implementation_paths_absent_only_at_registration_source(
    registration,
):
    absent = (
        set(IMPLEMENTATION) | NOTIFICATION_REGISTRATION | NOTIFICATION_IMPLEMENTATION
    )
    assert len(IMPLEMENTATION) == 9
    assert len(NOTIFICATION_REGISTRATION) == 2
    assert len(NOTIFICATION_IMPLEMENTATION) == 6
    authority = _authority()
    source_paths = {row["path"] for row in _tree(authority or "HEAD")}
    assert not source_paths & absent
    if authority is None:
        for path in absent:
            target = ROOT / path
            assert not target.exists() and not target.is_symlink(), path
    # Once later source commits exist, only the immutable R14 tree is examined.


def test_v14_preserves_production_and_prior_model_bytes_without_importing(registration):
    base = {row["path"]: row for row in _tree(BASE)}
    source = {row["path"]: row for row in _tree(_authority() or "HEAD")}
    protected = {
        path
        for path in base
        if path.startswith((".github/workflows/", "src/"))
        or path in {"config.yaml", "pyproject.toml", "requirements/v12-historical.txt"}
    }
    assert protected
    assert all(source[path] == base[path] for path in protected)


def test_v14_shallow_origin_cannot_be_accepted(synthetic_git_repository):
    run = synthetic_git_repository
    _write_synthetic_seal()
    run("add", "--", REG)
    run("commit", "-m", "synthetic registration")
    head = run("rev-parse", "HEAD").decode("ascii").strip()
    (ROOT / ".git/shallow").write_text(head + "\n", encoding="ascii")
    with pytest.raises(AssertionError, match="full Git history required"):
        _authority()


def test_v14_metadata_git_cannot_lazy_fetch_or_inherit_credentials(monkeypatch):
    seen = []

    def capture(command, **kwargs):
        seen.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, b"", b"")

    monkeypatch.setattr(subprocess, "run", capture)
    _git("cat-file", "-e", "0" * 40)
    command, options = seen[0]
    assert "protocol.allow=never" in command
    assert options["env"]["GIT_NO_LAZY_FETCH"] == "1"
    assert options["env"]["GIT_NO_REPLACE_OBJECTS"] == "1"
    assert options["env"]["GIT_CONFIG_NOSYSTEM"] == "1"
    assert not any(
        name.startswith(("GH_", "GITHUB_", "SMTP_")) for name in options["env"]
    )


def _five_group_coefficient_cdf(maximum, draws_inside=None):
    """Integer coefficient DP; no random labels and no six-set enumeration."""
    degree = 6 if draws_inside is None else draws_inside
    coefficients = [1] + [0] * degree
    for _ in range(5):
        updated = [0] * (degree + 1)
        for total, count in enumerate(coefficients):
            for h in range(min(maximum, 6, degree - total) + 1):
                updated[total + h] += count * math.comb(6, h)
        coefficients = updated
    if draws_inside is not None:
        return coefficients[draws_inside]
    return sum(coefficients[k] * math.comb(19, 6 - k) for k in range(7))


def _occupancy_counts():
    """Independent occupancy recursion counts five groups and nineteen outside."""
    global_counts = [0] * 7
    conditional = [[0] * 7 for _ in range(7)]

    def visit(group, used, largest, ways):
        if group == 5:
            conditional[used][largest] += ways
            global_counts[largest] += ways * math.comb(19, 6 - used)
            return
        for hit in range(7 - used):
            visit(group + 1, used + hit, max(largest, hit), ways * math.comb(6, hit))

    visit(0, 0, 0, 1)
    return global_counts, conditional


FIVE_WEIGHTS = [27132, 5093064, 7564500, 1230100, 67725, 1290, 5]
POOL_WEIGHTS = [
    [1, 0, 0, 0, 0, 0, 0],
    [0, 30, 0, 0, 0, 0, 0],
    [0, 360, 75, 0, 0, 0, 0],
    [0, 2160, 1800, 100, 0, 0, 0],
    [0, 6480, 18450, 2400, 75, 0, 0],
    [0, 7776, 105300, 27600, 1800, 30, 0],
    [0, 0, 373950, 198400, 20700, 720, 5],
]
POOL_MEANS = [
    Fraction(0),
    Fraction(1),
    Fraction(34, 29),
    Fraction(303, 203),
    Fraction(3392, 1827),
    Fraction(51421, 23751),
    Fraction(95302, 39585),
]


def test_v14_exact_five_disjoint_group_null_has_two_independent_count_oracles(
    registration,
):
    cdfs = [_five_group_coefficient_cdf(m) for m in range(7)]
    dp_weights = [cdf - (cdfs[m - 1] if m else 0) for m, cdf in enumerate(cdfs)]
    occupancy, _ = _occupancy_counts()
    assert dp_weights == occupancy == FIVE_WEIGHTS
    denominator = math.comb(49, 6)
    assert sum(dp_weights) == denominator == 13983816
    assert sum(m * w for m, w in enumerate(dp_weights)) == 24189744
    assert sum(m * m * w for m, w in enumerate(dp_weights)) == 47537994
    mean = Fraction(sum(m * w for m, w in enumerate(dp_weights)), denominator)
    variance = (
        Fraction(sum(m * m * w for m, w in enumerate(dp_weights)), denominator)
        - mean**2
    )
    assert mean == Fraction(43822, 25333)
    assert variance == Fraction(24039506739, 59042001788)
    assert [sum(dp_weights[k:]) for k in (3, 4, 5, 6)] == [1299120, 69020, 1295, 5]
    law = registration["scientific_contract"]["fair_maximum_law"]
    assert law["weights_m0_through_m6"] == dp_weights
    assert law["denominator"] == law["weight_sum"] == denominator
    assert law["first_moment_weight_sum"] == 24189744
    assert law["second_moment_weight_sum"] == 47537994
    assert (
        Fraction(law["mean_fraction"]["numerator"], law["mean_fraction"]["denominator"])
        == mean
    )
    assert (
        Fraction(
            law["variance_fraction"]["numerator"],
            law["variance_fraction"]["denominator"],
        )
        == variance
    )


@pytest.mark.parametrize("q", range(7))
def test_v14_same_pool_conditional_null_and_mixture(registration, q):
    cdfs = [_five_group_coefficient_cdf(m, q) for m in range(7)]
    weights = [cdf - (cdfs[m - 1] if m else 0) for m, cdf in enumerate(cdfs)]
    _, conditional = _occupancy_counts()
    assert weights == conditional[q] == POOL_WEIGHTS[q]
    assert sum(weights) == math.comb(30, q)
    assert (
        Fraction(sum(m * w for m, w in enumerate(weights)), math.comb(30, q))
        == POOL_MEANS[q]
    )
    # Reconstruct each unconditional mass by summing all possible outside counts.
    mixture = [
        sum(POOL_WEIGHTS[k][m] * math.comb(19, 6 - k) for k in range(7))
        for m in range(7)
    ]
    assert mixture == FIVE_WEIGHTS
    law = registration["scientific_contract"]["same_pool_law"]
    row = law["rows"][q]
    assert row["q"] == q and row["denominator"] == math.comb(30, q)
    assert row["weights_m0_through_m6"] == weights
    assert Fraction(row["mean_numerator"], row["mean_denominator"]) == POOL_MEANS[q]
    assert law["only_descriptive_no_secondary_significance"] is True
    assert law["full_observed_q_sequence_is_not_fixed_exogenous_condition"] is True


def test_v14_fixed_snake_positions_have_five_disjoint_capture_ids(registration):
    columns = [[] for _ in range(5)]
    for position in range(30):
        row, column = divmod(position, 5)
        columns[column if row % 2 == 0 else 4 - column].append(position + 1)
    assert columns == [
        [1, 10, 11, 20, 21, 30],
        [2, 9, 12, 19, 22, 29],
        [3, 8, 13, 18, 23, 28],
        [4, 7, 14, 17, 24, 27],
        [5, 6, 15, 16, 25, 26],
    ]
    assert len(columns) == 5 and all(len(column) == 6 for column in columns)
    assert sorted(position for column in columns for position in column) == list(
        range(1, 31)
    )
    assert all(sum(column) == 93 for column in columns)
    selection = registration["scientific_contract"]["group_selection"]
    assert selection["group_count"] == 5 and selection["group_size"] == 6
    assert selection["capture_eligible_ids"] == ["G1", "G2", "G3", "G4", "G5"]
    assert selection["fixed_groups"] == [
        {"id": f"G{j + 1}", "rank_positions": col} for j, col in enumerate(columns)
    ]
    assert selection["rank_position_matrix"] == [list(row) for row in zip(*columns)]
    assert selection["legacy_aliases"] == {
        "final_combination": "G1",
        "final_6_hits": "H1",
    }
    assert selection["top6_is_ranking_diagnostic_not_sixth_ticket"] is True
    assert selection["top12_top18_complete_coverage_is_not_capture"] is True
    assert (
        selection["winning_group_must_never_be_renamed_to_G1_or_legacy_final"] is True
    )
    assert selection["joint_probability_model_defined"] is False
    # Rank positions are construction metadata, never actual selected lottery labels.


def test_v14_machine_schemas_agree_with_the_actual_closed_seal_and_config(registration):
    operation = registration["operational_contract"]
    contracts = operation["schema_contracts"]
    assert contracts["all_unknown_keys_rejected"] is True
    assert len(operation) == contracts["operational_top_level_key_count"] == 19
    assert set(operation) == set(contracts["operational_top_level_required_keys"])
    definitions = contracts["definitions"]
    assert len(definitions) == contracts["definition_count"] == 97
    for definition in definitions.values():
        assert definition["key_count"] == len(definition["required_keys"])
        assert len(set(definition["required_keys"])) == len(definition["required_keys"])
        assert definition["unknown_keys"] == "reject"
    assert definitions["Seal"]["key_count"] == 13
    assert set(definitions["Seal"]["required_keys"]) == SCHEMA
    assert definitions["Seal"]["optional_keys"] == []
    assert contracts["seal_status_exact"] == registration["status"] == STATUS
    assert definitions["RegisteredFile"]["key_count"] == 4
    assert set(definitions["RegisteredFile"]["required_keys"]) == {
        "path",
        "git_blob",
        "bytes",
        "sha256",
    }
    assert definitions["RegisteredFile"]["optional_keys"] == []
    config = _decode(_at_source(CONFIG, _authority()))
    assert definitions["Config"]["key_count"] == 10
    assert set(definitions["Config"]["required_keys"]) == set(config)
    assert definitions["Config"]["optional_keys"] == []
    assert definitions["Forecast"]["key_count"] == 26
    assert set(definitions["Forecast"]["required_keys"]) == {
        "schema_version",
        "experiment_id",
        "model_id",
        "model_version",
        "selector_id",
        "probability_source_name",
        "probability_source_version",
        "probability_adapter_version",
        "feature_set_id",
        "target_ordinal",
        "target_draw_date",
        "history_through",
        "training_cutoff_date",
        "visible_prefix_draw_count",
        "visible_prefix_sha256",
        "generated_at",
        "probabilities",
        "ranking",
        "top6",
        "top12",
        "top18",
        "top30",
        "groups",
        "final_combination",
        "capture_eligible_group_ids",
        "bindings",
    }
    assert definitions["Forecast"]["optional_keys"] == []
    assert set(definitions["PreparationProvenance"]["required_keys"]) == {
        "contributors",
        "scope",
    }
    assert set(definitions["Contributor"]["required_keys"]) == {
        "agent_id",
        "session_id",
        "role",
    }


def test_v14_operational_paths_and_order_create_no_present_authority(registration):
    operation = registration["operational_contract"]
    identity = operation["identity"]
    assert (
        identity["repository"] == "Jasper-Shi/lottopred"
        and identity["branch"] == "main"
    )
    assert (
        identity["registration_base"] == BASE and identity["registration_path"] == REG
    )
    assert identity["config_path"] == CONFIG
    assert identity["experiment_id"] == "V14_long_frequency_fixed_five_disjoint_groups"
    assert identity["model_version"] == "v14.0.0"
    assert identity["lease_ref"] == "refs/heads/v14-consumption-v14.0.0"
    assert identity["canonical_command"] == [
        "python3.12",
        "tools/run_v14_historical.py",
        "--consume-v14-once",
    ]
    paths = operation["path_sets"]
    assert paths["implementation_add"] == IMPLEMENTATION
    assert paths["implementation_change_count"] == 9
    assert set(paths["notification_registration_add"]) == NOTIFICATION_REGISTRATION
    assert paths["notification_registration_change_count"] == 2
    assert set(paths["notification_implementation_add"]) == NOTIFICATION_IMPLEMENTATION
    assert paths["notification_implementation_change_count"] == 6
    assert set(paths["registration_modified"]) == MODIFIED
    assert set(paths["registration_fixed_add"]) == {
        EXPERIMENT,
        BASIS,
        CONFIG,
        REG,
        TEST,
    }
    assert set(paths["preparation_archive_add"]) == ARCHIVE_PATHS
    assert paths["registration_change_count"] == 26
    assert paths["registered_files_excluding_seal_count"] == 25
    topology = operation["phase_topology"]
    assert topology["order"] == [
        "R14",
        "R_N14",
        "M_R_N14",
        "I_N14",
        "K_N14",
        "I14",
        "K_H14",
        "A_H_s14",
        "M_A_H14",
        "L_H14",
        "run_H14",
    ]
    assert topology["historical_implementation_sole_parent"] == "K_N14"
    assert topology["historical_implementation_merge_ordered_parents"] == [
        "K_N14",
        "I14",
    ]
    assert topology["authorization_source_sole_parent"] == "K_H14"
    assert topology["authorization_merge_ordered_parents"] == ["K_H14", "A_H_s14"]
    assert topology["source_branch_grants_execution"] is False
    assert topology["future_values_resolved_only_from_actual_git"] is True
    assert topology["R_absence_checked_at"] == "unique_R14_source_tree_only"
    activation = operation["activation"]
    for key in (
        "formal_registration_grants_execution",
        "historical_enabled_at_registration",
        "live_enabled",
        "live_lane",
        "new_scientific_results_generated_by_this_draft",
        "old_authority_reuse",
        "dispatch_enabled",
        "default_model_activation",
    ):
        assert activation[key] is False
    assert (
        activation["registration_status"]
        == "registered_not_implemented_not_authorized_not_scored"
    )


def test_v14_worker_authorization_and_evidence_paths_absent_at_R_source(registration):
    operation = registration["operational_contract"]
    paths = operation["path_sets"]
    stem = "reports/v14_long_frequency_fixed_five_disjoint_groups_v14.0.0_historical"
    expected = {
        "claim": stem + ".claim",
        "json": stem + ".json",
        "ledger": stem + ".ledger.jsonl",
        "manifest": stem + ".commit-manifest.json",
        "markdown": stem + ".md",
        "startup": stem + ".startup.jsonl",
    }
    assert paths["worker_outputs"] == expected and paths["worker_output_count"] == 6
    assert paths["staging"] == [stem + ".json.staging", stem + ".md.staging"]
    assert paths["artifact_index"] == stem + ".commit-manifest.json.index"
    authorization = "evidence/research_authorizations/v14-long-frequency-fixed-five-disjoint-groups-v1-historical.json"
    assert operation["identity"]["authorization_path"] == authorization
    assert paths["authorization_add"] == [authorization]
    absent = (
        set(expected.values())
        | set(paths["staging"])
        | {paths["artifact_index"], authorization}
    )
    source_paths = {row["path"] for row in _tree(_authority() or "HEAD")}
    assert not source_paths & absent
    prefixes = (
        "evidence/research_audits/v14.0.0/",
        "evidence/research_notifications/v14.0.0/",
    )
    assert not any(path.startswith(prefixes) for path in source_paths)
    assert not any(
        path.startswith("reports/historical-five-group-6of6-candidate__")
        and path.endswith("__v14.0.0.json")
        for path in source_paths
    )
    if _authority() is None:
        for path in absent | set(prefixes):
            target = ROOT / path
            assert not target.exists() and not target.is_symlink(), path
        report_dir = ROOT / "reports"
        if report_dir.is_dir():
            assert not any(
                report_dir.glob("historical-five-group-6of6-candidate__*__v14.0.0.json")
            )


def test_v14_one_shot_lease_chronology_and_future_runtime_pins_are_explicit(
    registration,
):
    operation = registration["operational_contract"]
    github = operation["fixed_github"]
    assert github["origin"] == "https://api.github.com"
    assert github["prefix"] == "/repos/Jasper-Shi/lottopred"
    assert github["absence_status"] == 404
    assert (
        github["maximum_createRef_attempts"]
        == github["maximum_commit_POST_attempts"]
        == 1
    )
    assert github["max_retries"] == 0
    assert github["redirects"] is False and github["trust_env"] is False
    assert github["update_or_delete_ref"] is False
    assert github["existing_or_uncertain_ref"] == "terminal_no_adoption_no_retry"
    runtime = operation["runtime_closure"]
    assert runtime["core_sha256_at_R"] is None and runtime["core_first_freeze"] == "I14"
    assert runtime["core_nonnull_required_from"] == [
        "I14",
        "K_H14",
        "A_H_s14",
        "M_A_H14",
    ]
    assert runtime["core_path"] == "src/lotto649/v14_five_group_selection.py"
    assert runtime["python"] == "CPython3.12.11" and runtime["isolation"] == [
        "-I",
        "-S",
        "-B",
    ]
    assert runtime["requirements_path"] == "requirements/v12-historical.txt"
    assert (
        runtime["requirements_sha256"]
        == "a0dfeac17ad7e1c41dffe4b41b4810156fb028f879d312430bfc517672a570c6"
    )
    assert runtime["distribution_count"] == 27
    assert runtime["historical_loaded_module_runtime_recheck"] == [
        "before_facts",
        "before_entry",
        "before_model",
        "before_freeze",
        "before_worker_artifact",
    ]
    ledger = operation["scientific_ledger"]
    assert ledger["canonical_history_reads_before_authorized_claim"] is False
    assert ledger["first_intent_before_any_model_or_feature_call"] is True
    assert ledger["freeze_all_five_groups_before_reveal"] is True
    assert (
        ledger["model_calls_per_target"] == 1
        and ledger["reforecast_or_resume"] is False
    )
    assert ledger["per_target_event_count"] == 5
    assert ledger["complete_no_capture_event_count"] == 1 + 627 * 5 + 1
    assert [row["kind"] for row in ledger["per_target"]] == [
        "first_forecast_generation_intent",
        "forecast_generation_intent",
        "prediction_frozen",
        "target_reveal_intent",
        "target_revealed",
        "target_scored",
    ]


def test_v14_notification_is_separate_unimplemented_default_route_and_reviews_independent(
    registration,
):
    operation = registration["operational_contract"]
    notification = operation["notification"]
    assert set(notification["registration_paths"]) == NOTIFICATION_REGISTRATION
    assert set(notification["implementation_paths"]) == NOTIFICATION_IMPLEMENTATION
    assert notification["deployment_before_historical_I"] is True
    assert notification["actual_deployment_established_by_this_draft"] is False
    assert notification["caller_text_or_route_override"] is False
    assert notification["credential_values_read_by_agent"] is False
    assert notification["default_sender"] == "lotto649.notification.send_email"
    assert notification["SMTP_secret_names"] == ["SMTP_USERNAME", "SMTP_PASSWORD"]
    assert notification["maximum_authorized_SMTP_calls"] == 1
    assert (
        notification["remaining_N_contract"]
        == "must_be_separately_sealed_and_implemented_before_I14"
    )
    authorization = operation["authorization"]
    assert (
        authorization["N_readiness_required_before_I14_and_reverified_before_A"] is True
    )
    assert (
        authorization["exact_PR_check_name"] == "test"
        and authorization["push_check_name"] == "push-test"
    )
    assert (
        authorization["CI_status"] == "completed"
        and authorization["CI_conclusion"] == "success"
    )
    assert authorization["ambiguous_or_duplicate_test"] == "reject"
    assert authorization["local_validation_before_token"] is True
    assert (
        authorization["facts_are_inert"] is True
        and authorization["facts_create_no_files_or_capabilities"] is True
    )
    reviews = operation["source_author_provenance"]
    assert (
        reviews["minimum_distinct_reviewer_agents"]
        == reviews["minimum_distinct_sessions"]
        == 2
    )
    assert reviews["per_phase_independent_axes"] == ["standards", "spec"]
    assert reviews["new_session_does_not_restore_author_independence"] is True
    assert reviews["same_truthful_publisher_allowed"] is True


def test_v14_fixed_calendar_and_history_identity_are_metadata_only(registration):
    science = registration["scientific_contract"]
    identity = science["identity"]
    assert identity["experiment"] == "V14_long_frequency_fixed_five_disjoint_groups"
    assert (
        identity["model_version"] == "v14.0.0"
        and type(identity["seed"]) is int
        and identity["seed"] == 649
    )
    assert identity["probability_source_class"] == "LongFrequencyModel"
    assert identity["evidence_lane"] == "consumed_historical_diagnostic_only"
    assert identity["live_lane"] == "none" and identity["historical_attempt_limit"] == 1
    scope = science["scope"]
    assert [item["count"] for item in scope["scopes"]] == [627, 314, 313]
    assert [item["id"] for item in scope["scopes"]] == [
        "aggregate",
        "first_half",
        "second_half",
    ]
    for item in scope["scopes"]:
        current = date.fromisoformat(item["first_target"])
        end = date.fromisoformat(item["last_target"])
        days = []
        while current <= end:
            if current.weekday() in {2, 5}:
                days.append(current.isoformat())
            current += timedelta(days=1)
        assert len(days) == item["count"]
        assert (
            _sha(("\n".join(days) + "\n").encode("ascii"))
            == item["target_dates_sha256"]
        )
        assert all("2020-01-01" <= day <= "2025-12-31" for day in days)
    assert scope["history_count"] == 4444 and scope["history_start"] == "1982-06-12"
    assert scope["history_through"] == "2026-08-22" and scope["scoring_count"] == 627
    assert scope["all_2026_excluded_from_scoring_and_target_visible_prefixes"] is True
    assert scope["later_published_appends_forbidden"] is True
    old_registration = (
        "evidence/research_registrations/v13-post-rng-main-set-overlap-v1.json"
    )
    old_bytes = _require_git("show", BASE + ":" + old_registration)
    assert (
        _sha(old_bytes)
        == "36543acd288418c0cfbf561024b2ca60fa483b8aae6a6988026b76dde861e759"
    )
    old = _decode(old_bytes)
    assert (
        scope["history_identity"]
        == old["scientific_contract"]["scope"]["history_identity"]
    )
    assert (
        scope["history_identity"]["commit"]
        == "4a617f2c1575a165b42878600753a01ddf2ced03"
    )
    operation = registration["operational_contract"]["identity"]
    assert operation["history_authority"] == scope["history_identity"]["commit"]
    assert operation["experiment_id"] == identity["experiment"]
    assert operation["model_version"] == identity["model_version"]
    for key in (
        "model_id",
        "model_version",
        "selector_id",
        "probability_source_class",
        "probability_source_name",
        "probability_source_version",
        "probability_adapter_version",
        "feature_set_id",
        "seed",
    ):
        assert operation[key] == identity[key], (
            "science/operation identity mismatch: " + key
        )
    assert operation["seed"] == identity["seed"]


def test_v14_prior_probability_source_is_pinned_without_import(registration):
    science = registration["scientific_contract"]
    source = science["source_contract"]
    paths = {
        "src/lotto649/models/baselines.py",
        "src/lotto649/models/base.py",
        "src/lotto649/features.py",
        "src/lotto649/domain.py",
        "src/lotto649/optimizer.py",
        "src/lotto649/__init__.py",
        "src/lotto649/models/__init__.py",
        "requirements/v12-historical.txt",
        "config.yaml",
    }
    assert (
        source["fixed_source_checkpoint"] == "182a4245bbaf0c444ef1e16c1b5beb120eec327f"
    )
    assert source["proposed_registration_base"] == BASE
    assert {row["path"] for row in source["source_files"]} == paths
    assert len(source["source_files"]) == len(paths)
    for row in source["source_files"]:
        assert row["path"] in paths  # Bound reads to source/configuration only.
        raw = _require_git(
            "show", source["fixed_source_checkpoint"] + ":" + row["path"]
        )
        assert _sha(raw) == row["sha256"]
        assert (
            hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()
            == row["git_blob"]
        )
        assert row["git_mode"] == "100644"
        assert _at_source(row["path"], _authority()) == raw
    probability = science["probability"]
    assert probability["strength_literal"] == "250.0"
    assert probability["effective_feature_columns"] == ["long_freq"]
    assert probability["source_has_no_intrinsic_minimum_300_gate"] is True
    assert science["training"]["minimum_visible_draws"] == 300
    assert science["training"]["no_rolling_window_or_post_rng_truncation"] is True
    assert science["training"]["no_same_target_reprediction"] is True
    assert probability["output_gate"]["checked_before_target_reveal"] is True
    assert (
        probability["output_gate"]["mass_expression"]
        == "abs(math.fsum(p_i for i in ascending labels 1..49)-6.0)<=1e-12"
    )
    assert probability["no_probability_repair"] is True
    assert probability["rational_oracle_is_not_bitwise_implementation"] is True
    assert source["legacy_select_combination_is_not_called"] is True
    assert source["no_additional_empirical_factory_producer"] is True
    runtime = science["runtime"]
    exact = runtime["exact_runtime"]
    assert exact["implementation"] == "cpython" and exact["python_version"] == "3.12.11"
    assert len(exact["installed_distributions"]) == runtime["distribution_count"] == 27
    assert exact["installed_distributions"]["numpy"] == "2.3.5"
    assert exact["installed_distributions"]["pandas"] == "2.3.3"
    # These are metadata assertions; this test itself remains portable on CI.


def test_v14_exact_local_primary_and_twelve_descriptive_intervals(registration):
    science = registration["scientific_contract"]
    primary = science["primary_statistics"]
    assert primary["n"] == 627 and primary["sole_primary_scope"] == "aggregate"
    assert primary["alpha_fraction"] == {"numerator": 1, "denominator": 20}
    assert primary["upper_tail"]["include_equality"] is True
    assert primary["upper_tail"]["integer_storage"] == ["hex(A)", "hex(B)"]
    assert primary["half_scope_p_values_cannot_promote_or_rescue_primary"] is True
    assert primary["local_nominal_not_Goal_global_adjusted"] is True
    assert [(row["n"], row["minimum_T"]) for row in primary["threshold_oracles"]] == [
        (627, 1112),
        (314, 563),
        (313, 561),
        (104, 192),
    ]
    assert primary["threshold_oracles"][-1]["role"] == "inactive_future_math_only"
    intervals = science["descriptive_intervals"]
    expected = [
        (scope, n, kind)
        for scope, n in (("aggregate", 627), ("first_half", 314), ("second_half", 313))
        for kind in ("M_fair", "M_same_pool", "Brier_fair", "LogLoss_fair")
    ]
    assert len(intervals["intervals"]) == intervals["count"] == 12
    assert [(row["scope"], row["n"], row["id"]) for row in intervals["intervals"]] == [
        (scope, n, scope + "_" + kind) for scope, n, kind in expected
    ]
    assert intervals["fresh_generator_per_interval"] == "numpy.random.default_rng(649)"
    assert intervals["resamples"] == 10000 and intervals["endpoint"] is False
    assert intervals["replacement"] is True
    assert intervals["additional_annual_group_topk_calibration_CIs"] is False
    assert intervals["extra_approval_gates"] is False
    assert intervals["complete_qualified_Reject_still_reports_all_12"] is True
    assert science["multiplicity"]["Goal_global_adjusted_p_defined"] is False
    assert science["multiplicity"]["complete_attempt_accounting_required"] == [
        "all versions and attempts",
        "timestamps and design changes",
        "exposure and consumed intervals",
        "candidate and rule rationale",
        "negative/failed/closed results",
        "shared target/date relationships",
        "primary and secondary endpoints",
        "any corrections or adjustments",
    ]
    assert (
        science["multiplicity"]["duplicate_dates_are_not_new_independent_opportunities"]
        is True
    )


def test_v14_scoring_capture_and_failure_interpretation_remain_closed(registration):
    science = registration["scientific_contract"]
    scoring = science["scoring"]
    assert scoring["actual_main_size"] == 6 and scoring["bonus_never_scored"] is True
    assert scoring["binary_log_loss"]["clip_epsilon"] is None
    assert (
        scoring["binary_log_loss"]["loss_i"]
        == "-(y_i*math.log(p_i)+(1.0-y_i)*math.log(1.0-p_i))"
    )
    assert scoring["binary_log_loss"]["no_clipping_or_log1p_substitution"] is True
    bins = scoring["calibration"]
    assert bins["bin_count"] == 10
    assert bins["bin_boundaries_literals"] == [
        "0.0",
        "0.1",
        "0.2",
        "0.3",
        "0.4",
        "0.5",
        "0.6",
        "0.7",
        "0.8",
        "0.9",
        "1.0",
    ]
    assert bins["within_draw_49_labels_are_not_independent_draws"] is True
    stop = science["stopping"]
    assert (
        stop["capture_at_target_627_still_has_all_fixed_horizon_p_CI_pass_null"] is True
    )
    assert stop["any_missing_or_fault_is_terminal"] is True
    assert (
        stop["no_partial_group_M_or_zero_imputation_or_skipping_or_extension"] is True
    )
    assert all(state["retry"] is False for state in stop["states"])
    states = {state["id"]: state for state in stop["states"]}
    assert len(states) == len(stop["states"]) == 10
    assert set(states) == {
        "startup_failed_unscored_no_retry",
        "execution_failed_archive_no_retry",
        "frozen_failure_phase_unknown_no_retry",
        "capture_pending_independent_audit",
        "capture_unqualified",
        "capture_audit_passed_pending_completion",
        "audited_historical_five_group_capture_completed",
        "complete_internal_audit_passed_external_audit_pending",
        "Reject",
        "complete_historical_diagnostic_conditionpass_unpromoted",
    }
    assert states["Reject"]["Goal_complete"] is False
    assert (
        states["complete_historical_diagnostic_conditionpass_unpromoted"][
            "Goal_complete"
        ]
        is False
    )
    assert states["capture_audit_passed_pending_completion"]["Goal_complete"] is False
    assert science["interpretation"]["prospective"]["active"] is False
    assert science["interpretation"]["prospective"]["planning_count"] == 104
    assert (
        science["interpretation"][
            "no_purchase_numbers_or_future_winning_recommendation"
        ]
        is True
    )
    assert science["interpretation"]["no_relabel_as_old_single_Final6"] is True
    assert (
        science["interpretation"][
            "Goal_not_complete_from_tests_registration_merge_or_Reject"
        ]
        is True
    )


PREFIX_DOMAIN = "lotto649-v14-visible-prior-draw-prefix-v1\n"
PREFIX_ORACLE_ROWS = [
    {"draw_date": "2001-01-03", "numbers": [1, 2, 3, 4, 5, 6], "bonus": 7},
    {"draw_date": "2001-01-06", "numbers": [8, 9, 10, 11, 12, 13], "bonus": None},
]
PREFIX_ORACLE_BYTES = (
    b"lotto649-v14-visible-prior-draw-prefix-v1\n"
    b'[{"bonus":7,"draw_date":"2001-01-03","numbers":[1,2,3,4,5,6]},'
    b'{"bonus":null,"draw_date":"2001-01-06","numbers":[8,9,10,11,12,13]}]\n'
)
PREFIX_ORACLE_SHA = "2652aac7383ec4ceeb0a438e256edc25a61ebcb6d5843cc0b37d0f7295982ae2"


def _canonical_iso_date(value):
    assert type(value) is str, "native canonical date string required"
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        raise AssertionError("canonical ISO date required") from None
    assert parsed.isoformat() == value, "canonical ISO date required"
    return parsed


def _synthetic_prefix_bytes(
    rows,
    target_draw_date,
    expected_cutoff,
    expected_count,
    *,
    nullable_bonus_authorized,
):
    """Independent byte-domain oracle, not the future history reader or model.

    The explicit nullable flag models a pre-existing synthetic authority policy.
    It does not grant a production caller permission to replace a missing bonus.
    The registered two-row serialization example is below the formal 300-row
    minimum; exercising it never validates a formal training coordinator.
    """
    assert type(rows) is list and rows, "nonempty complete prefix rows required"
    assert type(expected_count) is int and expected_count > 0, (
        "native positive count required"
    )
    assert len(rows) == expected_count, "prefix count mismatch"
    assert type(nullable_bonus_authorized) is bool, (
        "explicit synthetic bonus policy required"
    )
    target = _canonical_iso_date(target_draw_date)
    cutoff = _canonical_iso_date(expected_cutoff)
    previous = None
    for row in rows:
        assert type(row) is dict and set(row) == {"draw_date", "numbers", "bonus"}, (
            "closed prior-row schema"
        )
        current = _canonical_iso_date(row["draw_date"])
        assert previous is None or current > previous, (
            "strict chronological order required"
        )
        assert current < target, "target and future rows forbidden"
        previous = current
        numbers = row["numbers"]
        assert type(numbers) is list and len(numbers) == 6, (
            "six canonical main labels required"
        )
        assert all(type(number) is int and 1 <= number <= 49 for number in numbers), (
            "native main integer domain"
        )
        assert numbers == sorted(set(numbers)), (
            "main labels must be unique and ascending"
        )
        bonus = row["bonus"]
        if bonus is None:
            assert nullable_bonus_authorized, "null bonus lacks synthetic authority"
        else:
            assert type(bonus) is int and 1 <= bonus <= 49, (
                "native bonus integer domain"
            )
            assert bonus not in numbers, "bonus cannot equal a main label"
    assert previous == cutoff, "prefix cutoff mismatch"
    # _canonical is J=C+LF. The domain has its own LF and the array retains one.
    return PREFIX_DOMAIN.encode("utf-8") + _canonical(rows)


def test_v14_full_prefix_serialization_has_closed_independent_byte_oracle():
    raw = _synthetic_prefix_bytes(
        PREFIX_ORACLE_ROWS,
        "2001-01-10",
        "2001-01-06",
        2,
        nullable_bonus_authorized=True,
    )
    assert raw == PREFIX_ORACLE_BYTES
    assert len(raw) == 173
    assert _sha(raw) == PREFIX_ORACLE_SHA
    assert raw.endswith(b"\n") and not raw.endswith(b"\n\n")
    assert _sha(raw + b"\n") != PREFIX_ORACLE_SHA
    assert _sha(raw[:-1]) != PREFIX_ORACLE_SHA
    assert _sha(_canonical(PREFIX_ORACLE_ROWS)[:-1]) != PREFIX_ORACLE_SHA
    assert (
        _sha(_canonical([row["draw_date"] for row in PREFIX_ORACLE_ROWS])[:-1])
        != PREFIX_ORACLE_SHA
    )


@pytest.mark.parametrize("changed_field", ["main", "bonus", "explicit_null"])
def test_v14_same_dates_do_not_hide_changed_prefix_contents(changed_field):
    rows = copy.deepcopy(PREFIX_ORACLE_ROWS)
    if changed_field == "main":
        rows[0]["numbers"] = [1, 2, 3, 4, 5, 14]
    elif changed_field == "bonus":
        rows[0]["bonus"] = 15
    else:
        rows[0]["bonus"] = None
    raw = _synthetic_prefix_bytes(
        rows, "2001-01-10", "2001-01-06", 2, nullable_bonus_authorized=True
    )
    assert _sha(raw) != PREFIX_ORACLE_SHA


@pytest.mark.parametrize(
    "mutation",
    [
        "empty",
        "extra_row_key",
        "missing_bonus",
        "reordered_rows",
        "duplicate_date",
        "noncanonical_date",
        "wrong_count",
        "bool_count",
        "wrong_cutoff",
        "target_row",
        "future_row",
        "bool_main",
        "float_main",
        "duplicate_main",
        "unsorted_main",
        "out_of_range_main",
        "tuple_main",
        "bool_bonus",
        "float_bonus",
        "out_of_range_bonus",
        "main_equals_bonus",
        "unauthorized_null",
    ],
)
def test_v14_prefix_oracle_rejects_incomplete_noncanonical_or_future_rows(mutation):
    rows = copy.deepcopy(PREFIX_ORACLE_ROWS)
    count = 2
    cutoff = "2001-01-06"
    target = "2001-01-10"
    nullable = True
    if mutation == "empty":
        rows = []
    elif mutation == "extra_row_key":
        rows[0]["after_target"] = True
    elif mutation == "missing_bonus":
        del rows[0]["bonus"]
    elif mutation == "reordered_rows":
        rows.reverse()
    elif mutation == "duplicate_date":
        rows[1]["draw_date"] = rows[0]["draw_date"]
    elif mutation == "noncanonical_date":
        rows[0]["draw_date"] = "20010103"
    elif mutation == "wrong_count":
        count = 3
    elif mutation == "bool_count":
        count = True
    elif mutation == "wrong_cutoff":
        cutoff = "2001-01-03"
    elif mutation == "target_row":
        target = "2001-01-06"
    elif mutation == "future_row":
        target = "2001-01-05"
    elif mutation == "bool_main":
        rows[0]["numbers"][0] = True
    elif mutation == "float_main":
        rows[0]["numbers"][0] = 1.0
    elif mutation == "duplicate_main":
        rows[0]["numbers"][0] = 2
    elif mutation == "unsorted_main":
        rows[0]["numbers"].reverse()
    elif mutation == "out_of_range_main":
        rows[0]["numbers"][0] = 0
    elif mutation == "tuple_main":
        rows[0]["numbers"] = tuple(rows[0]["numbers"])
    elif mutation == "bool_bonus":
        rows[0]["bonus"] = True
    elif mutation == "float_bonus":
        rows[0]["bonus"] = 7.0
    elif mutation == "out_of_range_bonus":
        rows[0]["bonus"] = 50
    elif mutation == "main_equals_bonus":
        rows[0]["bonus"] = 1
    elif mutation == "unauthorized_null":
        nullable = False
    with pytest.raises(AssertionError):
        _synthetic_prefix_bytes(
            rows, target, cutoff, count, nullable_bonus_authorized=nullable
        )


def test_v14_registered_full_prefix_identity_matches_the_byte_oracle(registration):
    operation = registration["operational_contract"]
    prefix = operation["scientific_ledger"]["visible_prefix_identity"]
    assert prefix["domain"] == PREFIX_DOMAIN
    assert prefix["encoding"] == "UTF8(domain)+J(chronological PriorDrawRow list)"
    assert prefix["digest"] == "sha256" and prefix["schema"] == "PriorDrawRow"
    assert prefix["oracle_rows"] == PREFIX_ORACLE_ROWS
    assert prefix["oracle_bytes"] == len(PREFIX_ORACLE_BYTES) == 173
    assert prefix["oracle_sha256"] == _sha(PREFIX_ORACLE_BYTES) == PREFIX_ORACLE_SHA
    assert prefix["function_path"] == "src/lotto649/v14_evidence.py"
    assert (
        prefix["function_signature"]
        == "visible_prefix_sha256(history, target_draw_date, expected_cutoff, expected_count) -> str"
    )
    assert prefix["full_governed_prior_prefix_required"] is True
    assert prefix["bonus_preserved_for_identity_only"] is True
    assert prefix["target_and_future_rows_forbidden"] is True
    assert prefix["precompute_future_target_digest_table_forbidden"] is True
    assert prefix["minimum_production_prefix_count"] == 300
    row_schema = operation["schema_contracts"]["definitions"]["PriorDrawRow"]
    assert row_schema["key_count"] == 3 and row_schema["optional_keys"] == []
    assert set(row_schema["required_keys"]) == {"draw_date", "numbers", "bonus"}
    assert operation["hash_encodings"]["J"] == "C plus exactly one LF"


def test_v14_bootstrap_closure_and_prelaunch_proof_schemas_are_bound(registration):
    operation = registration["operational_contract"]
    definitions = operation["schema_contracts"]["definitions"]
    bootstrap = operation["runtime_closure"]["initial_bootstrap"]
    assert bootstrap["first_freeze"] == "I14" and bootstrap["sha256_at_R"] is None
    assert bootstrap["equal_at"] == ["I14", "K_H14", "A_H_s14", "M_A_H14"]
    assert bootstrap["auth_keys"] == ["initial_bootstrap", "initial_bootstrap_sha256"]
    assert bootstrap["schema"] == "InitialBootstrap"
    assert bootstrap["prelaunch_proof_schema"] == "PrelaunchProof"
    assert bootstrap["prelaunch_proof_contains_full_sterile_response"] is True
    assert bootstrap["probe_only_after_actual_historical_authorization"] is True
    assert bootstrap["normal_probe_environment_has_credentials"] is False
    assert (
        bootstrap["precredential_local_source_runtime_bootstrap_verification"] is True
    )
    assert bootstrap["pre_popen_complete_recheck"] is True
    assert bootstrap["inventory_complete_including_ignored_pyc"] is True
    assert bootstrap["no_runtime_repair"] is True
    assert bootstrap["source_review_pre_spawn_scope_required"] is True
    assert (
        bootstrap["normal_child_execve_limit"] == 1
        and bootstrap["process_retry_limit"] == 0
    )
    assert bootstrap["parent_to_child_live_fd_transfer_only"] is True
    assert bootstrap["caller_handoff_variables"] == "reject"
    assert bootstrap["runtime_schema_unchanged_seven_keys"] is True
    assert bootstrap["constructed_environment_platform_additions"] == []
    assert bootstrap["runtime_environment_platform_added_names"] == {
        "darwin": ["__CF_USER_TEXT_ENCODING"],
    }
    assert bootstrap["platform_added_value_read_recorded_or_forwarded"] is False
    assert bootstrap["sole_child_credential_variable"] == "GH_TOKEN"
    assert bootstrap["internal_handoff_variables"] == [
        "V14_STARTUP_FD",
        "V14_HANDOFF_FD",
        "V14_SUPERVISOR_PID",
        "V14_SPAWN_NONCE",
    ]
    assert bootstrap["fixed_variable_values"] == {
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "TZ": "UTC",
        "PATH": "sealed python executable directory:/usr/bin:/bin",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONSAFEPATH": "1",
    }
    assert definitions["Runtime"]["key_count"] == 7
    assert definitions["InitialBootstrap"]["key_count"] == 17
    assert set(definitions["InitialBootstrap"]["required_keys"]) == {
        "schema_version",
        "python_version",
        "normal_executable",
        "executable_aliases",
        "launcher_path",
        "launcher_git_blob",
        "launcher_sha256",
        "supervisor_function",
        "isolated_supervisor_command",
        "normal_child_command",
        "isolated_child_command",
        "environment_policy",
        "runtime_inventory",
        "runtime_inventory_sha256",
        "active_startup_paths",
        "sterile_probe",
        "credential_provider",
    }
    assert definitions["PrelaunchProof"]["key_count"] == 14
    assert definitions["BootstrapProbeResult"]["key_count"] == 19
    assert set(definitions["BootstrapProbeResult"]["required_keys"]) == {
        "schema_version",
        "executable",
        "real_executable",
        "prefix",
        "base_prefix",
        "sys_path",
        "module_origins",
        "exec_prefix",
        "base_exec_prefix",
        "site_prefixes",
        "enable_user_site",
        "safe_path",
        "no_user_site",
        "no_site",
        "dont_write_bytecode",
        "sitecustomize_file",
        "sitecustomize_cached",
        "usercustomize_loaded",
        "project_loaded",
    }
    assert set(definitions["PrelaunchProof"]["required_keys"]) == {
        "schema_version",
        "verified_at",
        "execution_commit",
        "implementation_commit",
        "source_root",
        "source_manifest_sha256",
        "runtime_identity_sha256",
        "bootstrap_contract_sha256",
        "bootstrap_inventory_sha256",
        "sterile_probe_sha256",
        "environment_policy_sha256",
        "supervisor_pid",
        "supervisor_source_sha256",
        "sterile_probe",
    }
    assert definitions["Authorization"]["key_count"] == 28
    for schema, count in (
        ("Authorization", 28),
        ("StartupIdentity", 22),
        ("ReviewComment", 16),
        ("ClosureAudit", 32),
    ):
        assert definitions[schema]["key_count"] == count
        assert "initial_bootstrap_sha256" in definitions[schema]["required_keys"]
    authorization = operation["authorization"]
    assert authorization["initial_bootstrap_equal_at"] == [
        "I14",
        "K_H14",
        "A_H_s14",
        "M_A_H14",
    ]
    assert authorization["initial_bootstrap_required_before_GH_TOKEN"] is True
    normal = ["python3.12", "tools/run_v14_historical.py", "--consume-v14-once"]
    assert (
        bootstrap["normal_child_command"]
        == normal
        == operation["identity"]["canonical_command"]
    )
    assert bootstrap["isolated_child_command"] == [
        normal[0],
        "-I",
        "-S",
        "-B",
        *normal[1:],
    ]
    assert bootstrap["supervisor_command"] == [
        "python3.12",
        "-I",
        "-S",
        "-B",
        "tools/run_v14_historical.py",
        "--supervise-v14-once",
    ]
    assert bootstrap["supervisor_file"] == "tools/run_v14_historical.py"
    assert bootstrap["supervisor_function"] == "supervise_v14_once"


STARTUP_KINDS = [
    "attempt_entered",
    "normal_child_spawn_intent",
    "normal_child_spawn_receipt",
    "child_isolated_attached",
    "capability_issued",
    "lease_absence_confirmed",
    "lease_commit_POST_intent",
    "lease_commit_POST_receipt",
    "lease_commit_GET_verified",
    "lease_ref_POST_intent",
    "lease_ref_POST_receipt",
    "lease_ref_reread_verified",
    "startup_checkpoint",
    "claim_created",
    "scientific_ledger_started",
    "history_load_intent",
]


def test_v14_supervisor_handoff_precedes_capability_claim_and_history(registration):
    startup = registration["operational_contract"]["startup"]
    phases = startup["phases"]
    assert startup["phase_count"] == len(phases) == 16
    assert [phase["sequence"] for phase in phases] == list(range(16))
    assert [phase["kind"] for phase in phases] == STARTUP_KINDS
    for phase in phases:
        assert phase["payload_key_count"] == len(phase["payload_required_keys"])
        assert len(set(phase["payload_required_keys"])) == phase["payload_key_count"]
        assert phase["payload_optional_keys"] == []
    assert startup["entry_writer"] == "current_isolated_supervisor"
    assert startup["supervisor_owned_sequences"] == [0, 1, 2]
    assert startup["child_owned_sequences"] == list(range(3, 16))
    assert startup["popen_after_sequence"] == 1 and startup["popen_limit"] == 1
    assert startup["handoff_checkpoint_sequence"] == 2
    assert startup["capability_after_sequence"] == 3
    assert (
        startup["checkpoint_sequence"] == 12 and startup["sealed_after_sequence"] == 15
    )
    assert startup["governed_history_after"] == "phase15_sealed_post_claim_and_ledger"
    assert startup["later_process_adoption"] is False
    assert startup["no_seventh_entry_artifact"] is True
    assert startup["parent_liveness_rechecked_at"] == [
        "before_lease",
        "before_history",
        "before_generation",
        "before_freeze",
        "before_artifact",
    ]
    assert set(phases[0]["payload_required_keys"]) == {
        "identity",
        "verified_facts_sha256",
        "prelaunch_proof",
    }
    assert set(phases[1]["payload_required_keys"]) == {
        "prelaunch_proof",
        "normal_command",
        "normal_executable",
        "environment_policy_sha256",
        "spawn_nonce_hex",
    }


def test_v14_N_protection_read_capability_is_separate_from_default_workflow_token(
    registration,
):
    operation = registration["operational_contract"]
    notification = operation["notification"]
    assert notification["default_GITHUB_TOKEN_protection_read_supported"] is False
    assert notification["actual_protection_App_provisioned_by_this_draft"] is False
    assert (
        notification["protection_token_kind"]
        == "github_app_installation_read_only_protection"
    )
    assert notification["protection_app_installed_repository"] == "Jasper-Shi/lottopred"
    assert notification["protection_permission"] == {"administration": "read"}
    assert notification["protection_get_paths"] == [
        "/repos/Jasper-Shi/lottopred/branches/main/protection",
        "/repos/Jasper-Shi/lottopred/branches/main/protection/enforce_admins",
    ]
    assert notification["readiness_verifier_GET_only"] is True
    assert notification["readiness_end_to_end_GET_only"] is False
    assert notification["readiness_independent_token_lifecycle_methods"] == [
        "POST",
        "DELETE",
    ]
    assert notification["readiness_repository_mutation"] is False
    assert notification["readiness_SMTP"] is False
    assert notification["token_mint_method"] == "POST"
    assert notification["token_revoke_method"] == "DELETE"
    assert notification["maximum_token_lifetime_seconds"] == 3600
    assert notification["readiness_record_head_order"] == ["K_N14", "K_H14"]
    assert notification["readiness_records_in_Auth_count"] == 2
    assert notification["same_default_SMTP_unchanged"] is True
    assert notification["caller_text_or_route_override"] is False
    definitions = operation["schema_contracts"]["definitions"]
    assert definitions["NotificationDeployment"]["key_count"] == 18
    assert "protection_reader" in definitions["NotificationDeployment"]["required_keys"]
    assert "readiness_records" in definitions["NotificationDeployment"]["required_keys"]
    assert definitions["NotificationProtectionReader"]["key_count"] == 13
    assert definitions["ProtectionPermissions"]["required_keys"] == ["administration"]


def _synthetic_closed_object(value, definition):
    assert type(value) is dict and set(value) == set(definition["required_keys"]), (
        "closed synthetic descriptor"
    )
    assert definition["optional_keys"] == [] and definition["unknown_keys"] == "reject"


def _fake_prelaunch_proof():
    """Fabricated safe metadata only; no source path/commit here is an authority."""
    probe = {
        "schema_version": "lotto649-v14.0.0-bootstrap-probe-result-v1",
        "executable": "/synthetic-v14-runtime/bin/python3.12",
        "real_executable": "/synthetic-v14-runtime/base/python3.12",
        "prefix": "/synthetic-v14-runtime/venv",
        "base_prefix": "/synthetic-v14-runtime/base",
        "exec_prefix": "/synthetic-v14-runtime/venv",
        "base_exec_prefix": "/synthetic-v14-runtime/base",
        "site_prefixes": ["/synthetic-v14-runtime/venv"],
        "enable_user_site": False,
        "safe_path": True,
        "no_user_site": 1,
        "no_site": 0,
        "dont_write_bytecode": 1,
        "sitecustomize_file": "/synthetic-v14-runtime/lib/sitecustomize.py",
        "sitecustomize_cached": "/synthetic-v14-runtime/lib/__pycache__/sitecustomize.cpython-312.pyc",
        "usercustomize_loaded": False,
        "project_loaded": False,
        "sys_path": [
            "/synthetic-v14-runtime/lib",
            "/synthetic-v14-runtime/lib-dynload",
            "/synthetic-v14-runtime/site-packages",
        ],
        "module_origins": [
            {"name": "builtins", "origin": "builtin"},
            {"name": "sys", "origin": "builtin"},
        ],
    }
    return {
        "schema_version": "lotto649-v14.0.0-prelaunch-proof-v1",
        "verified_at": "2001-01-01T00:00:00Z",
        "execution_commit": "1" * 40,
        "implementation_commit": "2" * 40,
        "source_root": "/synthetic-v14-source",
        "source_manifest_sha256": "3" * 64,
        "runtime_identity_sha256": "4" * 64,
        "bootstrap_contract_sha256": "5" * 64,
        "bootstrap_inventory_sha256": "6" * 64,
        "sterile_probe_sha256": _sha(_canonical(probe)),
        "environment_policy_sha256": "7" * 64,
        "supervisor_pid": 101,
        "supervisor_source_sha256": "8" * 64,
        "sterile_probe": probe,
    }


def _verify_synthetic_prelaunch_binding(proof, expected, definitions):
    """Relation oracle for forged descriptors, not the future runtime verifier."""
    _synthetic_closed_object(proof, definitions["PrelaunchProof"])
    assert type(proof["supervisor_pid"]) is int and proof["supervisor_pid"] > 0, (
        "native supervisor identity"
    )
    probe = proof["sterile_probe"]
    _synthetic_closed_object(probe, definitions["BootstrapProbeResult"])
    for key in (
        "enable_user_site",
        "safe_path",
        "usercustomize_loaded",
        "project_loaded",
    ):
        assert type(probe[key]) is bool, "native probe boolean"
    for key in ("no_user_site", "no_site", "dont_write_bytecode"):
        assert type(probe[key]) is int, "native probe integer flag"
    assert type(probe["module_origins"]) is list
    for origin in probe["module_origins"]:
        _synthetic_closed_object(origin, definitions["BootstrapModuleOrigin"])
    names = [item["name"] for item in probe["module_origins"]]
    assert names == sorted(set(names)), "unique full module-origin projection"
    assert proof["sterile_probe_sha256"] == _sha(_canonical(probe)), (
        "full probe binding"
    )
    # expected represents independently sealed source/runtime metadata in this toy.
    # Its equality is not a statement that any real runtime was inspected.
    assert probe == expected["sterile_probe"], (
        "unregistered executable startup path or origin"
    )
    for key in proof:
        assert proof[key] == expected[key], "source runtime bootstrap proof binding"


def test_v14_prelaunch_full_probe_binding_accepts_only_identical_synthetic_metadata(
    registration,
):
    definitions = registration["operational_contract"]["schema_contracts"][
        "definitions"
    ]
    expected = _fake_prelaunch_proof()
    _verify_synthetic_prelaunch_binding(copy.deepcopy(expected), expected, definitions)


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_full_probe",
        "extra_proof_key",
        "source_changed",
        "inventory_changed",
        "environment_changed",
        "boolean_pid",
        "stale_probe_digest",
        "unknown_alias",
        "added_path",
        "cwd_path",
        "added_module",
        "changed_origin",
        "duplicate_origin",
        "probe_extra_key",
        "other_site_prefix",
        "user_site_enabled",
        "unsafe_path",
        "site_disabled",
        "bytecode_enabled",
        "wrong_hook",
        "wrong_cache",
        "user_hook_loaded",
        "project_loaded",
        "boolean_flag_alias",
        "integer_flag_alias",
    ],
)
def test_v14_prelaunch_binding_rejects_forged_or_stale_synthetic_descriptors(
    registration, mutation
):
    definitions = registration["operational_contract"]["schema_contracts"][
        "definitions"
    ]
    expected = _fake_prelaunch_proof()
    proof = copy.deepcopy(expected)
    if mutation == "missing_full_probe":
        del proof["sterile_probe"]
    elif mutation == "extra_proof_key":
        proof["caller_approved"] = True
    elif mutation == "source_changed":
        proof["source_manifest_sha256"] = "a" * 64
    elif mutation == "inventory_changed":
        proof["bootstrap_inventory_sha256"] = "a" * 64
    elif mutation == "environment_changed":
        proof["environment_policy_sha256"] = "a" * 64
    elif mutation == "boolean_pid":
        proof["supervisor_pid"] = True
    elif mutation == "stale_probe_digest":
        proof["sterile_probe_sha256"] = "a" * 64
    else:
        probe = proof["sterile_probe"]
        if mutation == "unknown_alias":
            probe["real_executable"] = "/synthetic-unregistered/python3.12"
        elif mutation == "added_path":
            probe["sys_path"].append("/synthetic-user-site")
        elif mutation == "cwd_path":
            probe["sys_path"].append("")
        elif mutation == "added_module":
            probe["module_origins"].append(
                {
                    "name": "unregistered_startup",
                    "origin": "/synthetic-user-site/startup.py",
                }
            )
        elif mutation == "changed_origin":
            probe["module_origins"][0]["origin"] = "/synthetic-user-site/builtins.py"
        elif mutation == "duplicate_origin":
            probe["module_origins"].append(probe["module_origins"][0])
        elif mutation == "probe_extra_key":
            probe["ignored_hook"] = True
        elif mutation == "other_site_prefix":
            probe["site_prefixes"].append("/synthetic-system-site")
        elif mutation == "user_site_enabled":
            probe["enable_user_site"] = True
        elif mutation == "unsafe_path":
            probe["safe_path"] = False
        elif mutation == "site_disabled":
            probe["no_site"] = 1
        elif mutation == "bytecode_enabled":
            probe["dont_write_bytecode"] = 0
        elif mutation == "wrong_hook":
            probe["sitecustomize_file"] = "/synthetic-unregistered/sitecustomize.py"
        elif mutation == "wrong_cache":
            probe["sitecustomize_cached"] = "/synthetic-unregistered/sitecustomize.pyc"
        elif mutation == "user_hook_loaded":
            probe["usercustomize_loaded"] = True
        elif mutation == "project_loaded":
            probe["project_loaded"] = True
        elif mutation == "boolean_flag_alias":
            probe["safe_path"] = 1
        elif mutation == "integer_flag_alias":
            probe["no_user_site"] = True
        # A self-consistent forged digest still cannot alter sealed expectations.
        proof["sterile_probe_sha256"] = _sha(_canonical(probe))
    with pytest.raises(AssertionError):
        _verify_synthetic_prelaunch_binding(proof, expected, definitions)


def _fake_live_handoff():
    handoff = {
        "schema_version": "lotto649-v14.0.0-supervisor-handoff-v1",
        "supervisor_pid": 101,
        "child_pid": 102,
        "spawn_nonce_hex": "a" * 64,
        "startup_prefix": {
            "path": "synthetic/startup.jsonl",
            "sequence": 2,
            "bytes": 123,
            "sha256": "b" * 64,
        },
        "bootstrap_contract_sha256": "c" * 64,
        "environment_policy_sha256": "d" * 64,
    }
    observations = {
        "parent_alive": True,
        "current_parent_pid": 101,
        "current_child_pid": 102,
        "startup_received_by_inheritance": True,
        "parent_startup_writer_closed": True,
        "handoff_writer_closed": True,
        "handoff_fd_is_pipe": True,
        "exactly_one_object_then_eof": True,
        "startup_nlink": 1,
        "original_dev_inode": [1, 2],
        "observed_dev_inode": [1, 2],
    }
    return handoff, observations


def _verify_synthetic_live_handoff(handoff, expected, observations, definitions):
    """Simulated process facts only; does not open or transfer a descriptor."""
    _synthetic_closed_object(handoff, definitions["SupervisorHandoff"])
    _synthetic_closed_object(handoff["startup_prefix"], definitions["Checkpoint"])
    for key in ("supervisor_pid", "child_pid"):
        assert type(handoff[key]) is int and handoff[key] > 0, (
            "native live process identity"
        )
    assert handoff == expected, "sealed one-child handoff identity"
    assert handoff["startup_prefix"]["sequence"] == 2, (
        "handoff only after spawn receipt"
    )
    for key in (
        "parent_alive",
        "startup_received_by_inheritance",
        "parent_startup_writer_closed",
        "handoff_writer_closed",
        "handoff_fd_is_pipe",
        "exactly_one_object_then_eof",
    ):
        assert observations[key] is True, "live inherited one-writer boundary"
    assert observations["current_parent_pid"] == handoff["supervisor_pid"]
    assert observations["current_child_pid"] == handoff["child_pid"]
    assert observations["original_dev_inode"] == observations["observed_dev_inode"]
    assert (
        type(observations["startup_nlink"]) is int
        and observations["startup_nlink"] == 1
    )


def test_v14_live_handoff_identity_accepts_one_complete_synthetic_transfer(
    registration,
):
    definitions = registration["operational_contract"]["schema_contracts"][
        "definitions"
    ]
    expected, observations = _fake_live_handoff()
    _verify_synthetic_live_handoff(
        copy.deepcopy(expected), expected, observations, definitions
    )


@pytest.mark.parametrize(
    "mutation",
    [
        "parent_dead",
        "parent_pid",
        "child_pid",
        "nonce",
        "checkpoint",
        "reopened_path",
        "parent_writer_open",
        "pipe_writer_open",
        "not_pipe",
        "multiple_objects",
        "inode_changed",
        "extra_link",
        "bool_pid",
        "extra_key",
    ],
)
def test_v14_handoff_rejects_later_adoption_or_unknown_process_and_fd_metadata(
    registration, mutation
):
    definitions = registration["operational_contract"]["schema_contracts"][
        "definitions"
    ]
    expected, observations = _fake_live_handoff()
    handoff = copy.deepcopy(expected)
    if mutation == "parent_dead":
        observations["parent_alive"] = False
    elif mutation == "parent_pid":
        observations["current_parent_pid"] = 103
    elif mutation == "child_pid":
        observations["current_child_pid"] = 103
    elif mutation == "nonce":
        handoff["spawn_nonce_hex"] = "e" * 64
    elif mutation == "checkpoint":
        handoff["startup_prefix"]["sequence"] = 1
    elif mutation == "reopened_path":
        observations["startup_received_by_inheritance"] = False
    elif mutation == "parent_writer_open":
        observations["parent_startup_writer_closed"] = False
    elif mutation == "pipe_writer_open":
        observations["handoff_writer_closed"] = False
    elif mutation == "not_pipe":
        observations["handoff_fd_is_pipe"] = False
    elif mutation == "multiple_objects":
        observations["exactly_one_object_then_eof"] = False
    elif mutation == "inode_changed":
        observations["observed_dev_inode"] = [1, 3]
    elif mutation == "extra_link":
        observations["startup_nlink"] = 2
    elif mutation == "bool_pid":
        handoff["child_pid"] = True
    elif mutation == "extra_key":
        handoff["new_owner"] = True
    with pytest.raises(AssertionError):
        _verify_synthetic_live_handoff(handoff, expected, observations, definitions)


HOMEBREW_STDLIB = "/opt/homebrew/Cellar/python@3.12/3.12.11/Frameworks/Python.framework/Versions/3.12/lib/python3.12"
HOMEBREW_HOOK_SOURCE_SHA = (
    "8f53bbf5e6a5679f47dbdabf680e30dd6159220d11c601786d95bf2ae72c1b38"
)
HOMEBREW_HOOK_CACHE_SHA = (
    "0f4e9870b6206583d72f74d0a34b7c6bafc8c6617450739dcf6b5308d5e012ad"
)
HOMEBREW_HOOK_HEADER = "cb0d0d0a000000009dae8668b90e0000"


def test_v14_only_existing_pinned_homebrew_hook_can_be_bound_at_future_I(registration):
    """Read registration metadata only; this does not read/decode/execute a cache."""
    bootstrap = registration["operational_contract"]["runtime_closure"][
        "initial_bootstrap"
    ]
    hook = bootstrap["sole_permitted_homebrew_hook"]
    assert hook["source_path"] == HOMEBREW_STDLIB + "/sitecustomize.py"
    assert (
        hook["cache_path"]
        == HOMEBREW_STDLIB + "/__pycache__/sitecustomize.cpython-312.pyc"
    )
    assert hook["source_sha256"] == HOMEBREW_HOOK_SOURCE_SHA
    assert hook["cache_sha256"] == HOMEBREW_HOOK_CACHE_SHA
    assert hook["source_bytes"] == 3769 and hook["cache_bytes"] == 4050
    assert hook["source_mode"] == hook["cache_mode"] == "0644"
    assert hook["source_mtime_integer"] == 1753656989
    assert hook["cache_header_hex"] == HOMEBREW_HOOK_HEADER
    assert hook["cache_compile_mode"] == "exec"
    assert (
        type(hook["cache_compile_optimize"]) is int
        and hook["cache_compile_optimize"] == 0
    )
    assert hook["cache_compile_dont_inherit"] is True
    assert hook["cache_equivalence_required_before_credentials"] is True
    assert hook["execute_compiled_or_cached_code_in_validator"] is False
    assert hook["current_cache_equivalence_executed"] is False
    assert hook["current_source_and_cache_metadata_read_only_observed"] is True
    assert hook["independent_I_binding_still_required"] is True
    assert hook["old_V13_authority_inherited"] is False
    assert hook["global_addsitedir_branch_must_be_unreachable"] is True
    assert hook["direct_imports"] == ["re", "os", "site", "sys"]
    assert hook["split_roots_required_absent"] == [
        "/opt/homebrew/opt/python-tk@3.12/libexec",
        "/opt/homebrew/opt/python-gdbm@3.12/libexec",
    ]
    assert bootstrap["forbidden_active_startup"] == [
        "any .pth",
        "all sitecustomize forms except sole pinned Homebrew source and equivalent pinned cache",
        "any usercustomize form",
        "existing startup zip",
        "CWD/empty/tools/user-site sys.path entries",
        "system site enabled",
        "Homebrew tk/gdbm split libexec roots",
    ]
    probe = hook["expected_normal_probe"]
    assert len(probe) == 17
    assert probe["sitecustomize_file"] == hook["source_path"]
    assert probe["sitecustomize_cached"] == hook["cache_path"]
    assert probe["site_prefixes"] == [probe["prefix"]] == [probe["exec_prefix"]]
    assert probe["base_prefix"] == probe["base_exec_prefix"]
    assert probe["sys_path"] == [
        HOMEBREW_STDLIB.rsplit("/", 1)[0] + "/python312.zip",
        HOMEBREW_STDLIB,
        HOMEBREW_STDLIB + "/lib-dynload",
        probe["prefix"] + "/lib/python3.12/site-packages",
    ]
    assert probe["safe_path"] is True
    for key in ("enable_user_site", "usercustomize_loaded", "project_loaded"):
        assert probe[key] is False
    for key, value in (("no_user_site", 1), ("no_site", 0), ("dont_write_bytecode", 1)):
        assert type(probe[key]) is int and probe[key] == value


def _fake_hook_surface(hook):
    """Fictional observations of registered metadata; no filesystem inspection."""
    return {
        "active_hook_entries": [
            {
                "path": hook[k + "_path"],
                "bytes": hook[k + "_bytes"],
                "sha256": hook[k + "_sha256"],
                "mode": hook[k + "_mode"],
            }
            for k in ("source", "cache")
        ],
        "cache_header_hex": hook["cache_header_hex"],
        "cache_equivalent": True,
        "startup_zip_exists": False,
        "system_site_enabled": False,
        "existing_split_roots": [],
    }


def _verify_synthetic_hook_surface(observations, hook):
    """Allowlist relation oracle; cache equivalence here is an invented boolean.

    Future implementation must establish actual authenticated code equivalence;
    this toy neither decodes cached code nor certifies any installed runtime.
    """
    expected = _fake_hook_surface(hook)
    assert type(observations) is dict and set(observations) == set(expected)
    entries = observations["active_hook_entries"]
    assert type(entries) is list and len(entries) == 2, "sole source/cache pair"
    for entry in entries:
        assert type(entry) is dict and set(entry) == {"path", "bytes", "sha256", "mode"}
        assert type(entry["bytes"]) is int and entry["bytes"] > 0
    assert observations["cache_equivalent"] is True, (
        "authenticated cache equivalence required"
    )
    assert observations["startup_zip_exists"] is False
    assert observations["system_site_enabled"] is False
    assert observations == expected, "unregistered startup hook surface"


def test_v14_exact_two_hook_descriptors_are_accepted_only_as_synthetic_metadata(
    registration,
):
    hook = registration["operational_contract"]["runtime_closure"]["initial_bootstrap"][
        "sole_permitted_homebrew_hook"
    ]
    _verify_synthetic_hook_surface(_fake_hook_surface(hook), hook)


@pytest.mark.parametrize(
    "mutation",
    [
        "source_digest",
        "cache_digest",
        "source_path",
        "cache_path",
        "source_size",
        "mode",
        "cache_header",
        "cache_unequal",
        "cache_unchecked",
        "pth",
        "usercustomize",
        "other_cache",
        "zip_exists",
        "system_site",
        "split_libexec",
        "unknown_approval",
    ],
)
def test_v14_unregistered_hooks_or_unverified_cache_fail_synthetic_allowlist(
    registration, mutation
):
    hook = registration["operational_contract"]["runtime_closure"]["initial_bootstrap"][
        "sole_permitted_homebrew_hook"
    ]
    observations = _fake_hook_surface(hook)
    if mutation == "source_digest":
        observations["active_hook_entries"][0]["sha256"] = "0" * 64
    elif mutation == "cache_digest":
        observations["active_hook_entries"][1]["sha256"] = "0" * 64
    elif mutation == "source_path":
        observations["active_hook_entries"][0]["path"] = (
            "/synthetic-extra/sitecustomize.py"
        )
    elif mutation == "cache_path":
        observations["active_hook_entries"][1]["path"] = (
            "/synthetic-extra/sitecustomize.pyc"
        )
    elif mutation == "source_size":
        observations["active_hook_entries"][0]["bytes"] += 1
    elif mutation == "mode":
        observations["active_hook_entries"][0]["mode"] = "0666"
    elif mutation == "cache_header":
        observations["cache_header_hex"] = "0" * 32
    elif mutation == "cache_unequal":
        observations["cache_equivalent"] = False
    elif mutation == "cache_unchecked":
        observations["cache_equivalent"] = None
    elif mutation in ("pth", "usercustomize", "other_cache"):
        leaf = {
            "pth": "extra.pth",
            "usercustomize": "usercustomize.py",
            "other_cache": "sitecustomize.opt-1.pyc",
        }[mutation]
        observations["active_hook_entries"].append(
            {
                "path": "/synthetic-extra/" + leaf,
                "bytes": 1,
                "sha256": "0" * 64,
                "mode": "0644",
            }
        )
    elif mutation == "zip_exists":
        observations["startup_zip_exists"] = True
    elif mutation == "system_site":
        observations["system_site_enabled"] = True
    elif mutation == "split_libexec":
        observations["existing_split_roots"] = [hook["split_roots_required_absent"][0]]
    elif mutation == "unknown_approval":
        observations["caller_approved_hook"] = True
    with pytest.raises(AssertionError):
        _verify_synthetic_hook_surface(observations, hook)
