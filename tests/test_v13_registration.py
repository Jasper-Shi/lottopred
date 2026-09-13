"""Offline checks for V13's immutable registration, without any model execution.

Only registration/configuration/source bytes, Git tree metadata, fixed calendar
and closed mathematical identities are read. No governed-history or result blob,
authorization verifier, production capability, worker, lease or email is opened.
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
REG = "evidence/research_registrations/v13-post-rng-main-set-overlap-v1.json"
CONFIG = "config/research-v13-post-rng-main-set-overlap.yaml"
EXPERIMENT = "docs/experiments/V13_post_rng_main_set_overlap.md"
BASIS = "docs/research/V13_post_rng_main_set_overlap_basis.md"
TEST = "tests/test_v13_registration.py"
BASE = "f247649be2928bfc7cbf5a00c0a400eedadb89f2"
SCIENCE_SHA = "7d86364d43907a64d3eb45f23ebb2fdfc2edf807633748e329cd64e0c8341a37"
OPERATION_SHA = "69f5eb033a678bf42fe6aeb49ece451934c413a0e4fcd5bc8e1d5e27cb06f382"
STATUS = ["REGISTERED", "NOT IMPLEMENTED", "NOT AUTHORIZED", "NOT SCORED"]
MODIFIED = {
    "docs/CODEX_HANDOFF.md",
    "docs/MODEL_PROTOCOL.md",
    "docs/RESEARCH_ROADMAP.md",
}
ADDED = {EXPERIMENT, BASIS, CONFIG, REG, TEST}
ALLOWED = MODIFIED | ADDED
IMPLEMENTATION = [
    "src/lotto649/models/v13_main_set_overlap.py",
    "src/lotto649/v13_evidence.py",
    "src/lotto649/v13_registered_attempt.py",
    "tools/run_v13_historical.py",
    "tests/test_v13_main_set_overlap.py",
    "tests/test_v13_registered_attempt.py",
    "tests/test_v13_evidence.py",
    "tests/fixtures/v13_git_commit_projection.json",
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
    }
    return subprocess.run(
        ("git", "-c", "core.hooksPath=/dev/null", *args),
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
    assert value["schema_version"] == "lotto649-v13-registration-v1"
    assert value["experiment_id"] == "V13_post_rng_main_set_overlap"
    assert value["model_version"] == "v13.0.0"
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
    assert set(pairs) == {
        ("/root", "root-v13-registration-integration-20260913"),
        ("/root/i3_evidence", "v13-science-draft-authoring-20260913"),
        ("/root/i3_evidence", "v13-registration-tests-authoring-20260913"),
        ("/root/v13_novelty_review", "v13-novelty-no-outcomes-20260913-01"),
        (
            "/root/i3_independent_output_audit",
            "v13-operational-contract-authoring-20260913",
        ),
    }, "complete known actual authoring provenance"


@pytest.fixture(scope="module")
def registration():
    raw = _at_source(REG, None)
    value = _decode(raw)
    _validate_seal(value)
    authority = _authority()
    assert _at_source(REG, authority) == raw, "registration seal changed after source"
    return value


def test_v13_closed_registered_status_and_fingerprint(registration):
    _validate_seal(registration)
    science = registration["scientific_contract"]
    assert science["identity"]["model_version"] == "v13.0.0"
    assert science["identity"]["seed"] == 649
    assert science["scope"]["live_lane"] == "none"
    assert science["scope"]["historical_attempt_limit"] == 1


def test_v13_registered_files_bind_exact_source_bytes(registration):
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


def test_v13_source_preserves_all_prior_tree_objects_without_opening_them(registration):
    expected = [record for record in _tree(BASE) if record["path"] not in ALLOWED]
    assert registration["preserved_tree_manifest"] == expected
    authority = _authority()
    actual = [
        record for record in _tree(authority or "HEAD") if record["path"] not in ALLOWED
    ]
    assert actual == expected
    # This checks historical predictions/results/data only by Git object identity.
    # No blob content from those namespaces is read.


def test_v13_registration_source_has_exactly_eight_changes(registration):
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


def test_v13_fixed_calendar_scope_without_opening_draw_records(registration):
    science = registration["scientific_contract"]
    scopes = science["scope"]["scopes"]
    assert [scope["count"] for scope in scopes] == [627, 314, 313]
    for scope in scopes:
        current = date.fromisoformat(scope["first_target"])
        end = date.fromisoformat(scope["last_target"])
        days = []
        while current <= end:
            if current.weekday() in {2, 5}:
                days.append(current.isoformat())
            current += timedelta(days=1)
        raw = ("\n".join(days) + "\n").encode("ascii")
        assert len(days) == scope["count"]
        assert _sha(raw) == scope["target_dates_sha256"]
        assert all(day < "2026-01-01" for day in days)
    assert science["scope"]["history_authority"] == (
        "4a617f2c1575a165b42878600753a01ddf2ced03"
    )
    assert science["scope"]["history_count"] == 4444
    assert science["scope"]["history_through"] == "2026-08-22"


def test_v13_closed_combinatorial_oracles_and_cyclic_control(registration):
    science = registration["scientific_contract"]
    weights = tuple(math.comb(6, k) * math.comb(43, 6 - k) for k in range(7))
    assert list(weights) == science["law"]["N_k"]
    count = math.comb(49, 6)
    assert sum(weights) == count == 13983816
    mean = sum(Fraction(k * n, count) for k, n in enumerate(weights))
    variance = sum(Fraction(k * k * n, count) for k, n in enumerate(weights)) - mean**2
    assert mean == Fraction(36, 49)
    assert variance == Fraction(5547, 9604)
    tilted_count = sum(n * 2**k for k, n in enumerate(weights))
    tilted_mean = Fraction(
        sum(k * n * 2**k for k, n in enumerate(weights)), tilted_count
    )
    assert tilted_count == 27251830
    assert tilted_mean == Fraction(3319260, 2725183)
    assert tilted_mean / 6 == Fraction(553210, 2725183)
    assert (6 - tilted_mean) / 43 == Fraction(303066, 2725183)
    control = science["cyclic_control"]
    mapping = [1 + label % 49 for label in range(1, 50)]
    assert control["map_labels"] == mapping
    assert _sha(_canonical(mapping)) == control["map_sha256"]
    assert Fraction(49 * Fraction(5, 8) - 36, 258) == Fraction(-1, 48)
    assert Fraction(5, 8) - Fraction(36, 49) == Fraction(-43, 392)


def test_v13_literal_oracles_are_finite_self_consistent_and_not_executed(registration):
    oracles = registration["scientific_contract"]["literal_oracles"]["closed_math"]
    assert len(oracles["moment_oracles"]) == 4
    assert len(oracles["root_oracles"]) == 9
    for record in oracles["moment_oracles"] + oracles["root_oracles"]:
        for value in record["outputs"].values():
            assert set(value) == {"decimal", "hex"}
            number = float.fromhex(value["hex"])
            assert math.isfinite(number)
            assert type(value["decimal"]) is float
            assert number.hex() == value["decimal"].hex()
    roots = {record["name"]: record for record in oracles["root_oracles"]}
    assert roots["fair_49"]["outputs"]["beta"]["hex"] == "0x0.0p+0"
    assert roots["fair_49"]["outputs"]["score_at_root"]["hex"] == (
        "-0x1.1000000000000p-49"
    )
    for record in roots.values():
        pairs = record["counts_run_length"]
        assert sum(item["count"] for item in pairs) == record["D"]
        assert sum(item["count"] * item["value"] for item in pairs) == record["Ksum"]
    # The normative program is hashed prose. Never eval/exec/import it in R13.


def test_v13_one_primary_five_entry_family_and_ten_gates(registration):
    science = registration["scientific_contract"]
    assert science["multiplicity"]["ordered_raw_p"] == [
        1.0,
        1.0,
        0.9783404732169021,
        0.5909687963172663,
        "p13_aggregate_exact_top12",
    ]
    assert [gate["number"] for gate in science["gates"]] == list(range(1, 11))
    assert science["statistics"]["bootstrap"]["seed"] == 649
    assert science["statistics"]["bootstrap"]["resamples"] == 10000
    assert science["binary64"]["bisection"]["iterations"] == 256
    assert science["binary64"]["bisection"]["early_stop"] is False
    assert science["binary64"]["bisection"]["fallback"] is False


@pytest.mark.parametrize(
    "mutation",
    [
        "extra_key",
        "missing_key",
        "changed_status",
        "status_tuple",
        "wrong_version",
        "wrong_base",
        "changed_science",
        "science_digest",
        "changed_operation",
        "operation_digest",
        "redigested_operation",
        "notification_ref_substitution",
        "notification_global_limit",
        "redigested_science",
        "preserved_digest",
        "reordered_files",
        "duplicate_file",
        "self_seal",
        "path_escape",
        "bool_size",
        "extra_file_key",
        "upper_blob",
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
def test_v13_rejects_mutated_closed_registration(registration, mutation):
    value = copy.deepcopy(registration)
    if mutation == "extra_key":
        value["future_authorization"] = "invented"
    elif mutation == "missing_key":
        del value["status"]
    elif mutation == "changed_status":
        value["status"][-1] = "SCORED"
    elif mutation == "status_tuple":
        value["status"] = tuple(STATUS)
    elif mutation == "wrong_version":
        value["model_version"] = "v12.0.2"
    elif mutation == "wrong_base":
        value["registration_base"] = "a" * 40
    elif mutation == "changed_science":
        value["scientific_contract"]["identity"]["seed"] = 650
    elif mutation == "science_digest":
        value["statistical_fingerprint_sha256"] = "0" * 64
    elif mutation == "changed_operation":
        value["operational_contract"]["unregistered_override"] = True
    elif mutation == "operation_digest":
        value["operational_contract_sha256"] = "0" * 64
    elif mutation == "redigested_operation":
        value["operational_contract"]["unregistered_override"] = True
        value["operational_contract_sha256"] = _sha(
            _canonical(value["operational_contract"])
        )
    elif mutation == "notification_ref_substitution":
        value["operational_contract"]["capture_audit_notification"][
            "global_notification_claim"
        ]["ref"] = "refs/heads/v13-consumption-v13.0.0"
        value["operational_contract_sha256"] = _sha(
            _canonical(value["operational_contract"])
        )
    elif mutation == "notification_global_limit":
        value["operational_contract"]["capture_audit_notification"][
            "global_notification_claim"
        ]["global_maximum_authorized_SMTP_calls"] = 2
        value["operational_contract_sha256"] = _sha(
            _canonical(value["operational_contract"])
        )
    elif mutation == "redigested_science":
        value["scientific_contract"]["identity"]["seed"] = 650
        value["statistical_fingerprint_sha256"] = _sha(
            _canonical(value["scientific_contract"])
        )
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
    elif mutation == "extra_file_key":
        value["registered_files"][0]["capability"] = True
    elif mutation == "upper_blob":
        value["registered_files"][0]["git_blob"] = "A" * 40
    elif mutation == "preserved_extra_key":
        value["preserved_tree_manifest"][0]["content"] = "must not read"
    elif mutation == "preserved_mode":
        value["preserved_tree_manifest"][0]["mode"] = "040000"
    elif mutation == "duplicate_preserved":
        value["preserved_tree_manifest"].append(value["preserved_tree_manifest"][0])
    elif mutation == "empty_provenance":
        value["preparation_provenance"] = []
    elif mutation == "duplicate_contributor":
        contributors = value["preparation_provenance"]["contributors"]
        contributors.append(contributors[0])
    elif mutation == "missing_contributor":
        value["preparation_provenance"]["contributors"].pop()
    elif mutation == "unsafe_contributor":
        value["preparation_provenance"]["contributors"][0]["role"] = "role\nsecond line"
    elif mutation == "invented_contributor":
        value["preparation_provenance"]["contributors"][0]["agent_id"] = "/invented"
    with pytest.raises(AssertionError):
        _validate_seal(value)


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
def test_v13_rejects_noncanonical_or_duplicate_json(raw):
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


def test_v13_draft_fallback_only_before_seal_exists_at_head(synthetic_git_repository):
    run = synthetic_git_repository
    _write_synthetic_seal()
    assert _authority() is None
    run("add", "--", REG)
    run("commit", "-m", "synthetic ordinary registration")
    source = run("rev-parse", "HEAD").decode("ascii").strip()
    assert _authority() == source
    assert _at_source(REG, source) == b'{"synthetic_fixture_only":true}\n'


def test_v13_source_absence_is_not_rechecked_at_later_implementation_head(
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


def test_v13_rejects_two_reachable_same_blob_additions(synthetic_git_repository):
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


def test_v13_rejects_deleted_then_readded_registration(synthetic_git_repository):
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


def test_v13_rejects_merge_only_registration(synthetic_git_repository):
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


def test_v13_draft_symlink_cannot_supply_source_bytes(tmp_path, monkeypatch):
    monkeypatch.setitem(globals(), "ROOT", tmp_path)
    outside = tmp_path / "synthetic-outside"
    outside.write_bytes(b"inert fixture")
    parent = tmp_path / "docs"
    parent.mkdir()
    (parent / "fixture.md").symlink_to(outside)
    with pytest.raises(AssertionError, match="symlink"):
        _at_source("docs/fixture.md", None)


def _validate_config(value, operational_sha):
    assert type(value) is dict and set(value) == {
        "schema_version",
        "experiment_id",
        "model_version",
        "seed",
        "historical_only",
        "registration_path",
        "scientific_contract_sha256",
        "operational_contract_sha256",
        "activation",
    }, "closed configuration schema"
    assert type(value["seed"]) is int and value["seed"] == 649
    assert value["historical_only"] is True
    assert value == {
        "schema_version": "lotto649-v13-research-config-v1",
        "experiment_id": "V13_post_rng_main_set_overlap",
        "model_version": "v13.0.0",
        "seed": 649,
        "historical_only": True,
        "registration_path": REG,
        "scientific_contract_sha256": SCIENCE_SHA,
        "operational_contract_sha256": operational_sha,
        "activation": "registration_only_no_runtime_wiring",
    }, "configuration identity or digest mismatch"


def test_v13_canonical_config_is_closed_and_execution_inert(registration):
    raw = _at_source(CONFIG, _authority())
    _validate_config(_decode(raw), registration["operational_contract_sha256"])


@pytest.mark.parametrize(
    "mutation",
    [
        "extra_key",
        "missing_key",
        "bool_seed",
        "numeric_historical_only",
        "activate",
        "wrong_science_sha",
        "wrong_operation_sha",
        "wrong_path",
    ],
)
def test_v13_rejects_config_schema_type_digest_or_activation_changes(
    registration, mutation
):
    value = _decode(_at_source(CONFIG, _authority()))
    if mutation == "extra_key":
        value["live"] = True
    elif mutation == "missing_key":
        del value["historical_only"]
    elif mutation == "bool_seed":
        value["seed"] = True
    elif mutation == "numeric_historical_only":
        value["historical_only"] = 1
    elif mutation == "activate":
        value["activation"] = "run_now"
    elif mutation == "wrong_science_sha":
        value["scientific_contract_sha256"] = "0" * 64
    elif mutation == "wrong_operation_sha":
        value["operational_contract_sha256"] = "0" * 64
    elif mutation == "wrong_path":
        value["registration_path"] = "../registration.json"
    with pytest.raises(AssertionError):
        _validate_config(value, registration["operational_contract_sha256"])


def test_v13_rejects_hidden_merge_origin_even_with_one_ordinary_add(
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


def test_v13_rejects_root_commit_registration(synthetic_git_repository):
    run = synthetic_git_repository
    run("checkout", "--orphan", "synthetic-root")
    _write_synthetic_seal()
    run("add", "--", REG)
    run("commit", "-m", "synthetic invalid root registration")
    with pytest.raises(AssertionError, match="root/merge introduction"):
        _authority()


def test_v13_rejects_modify_then_restore_same_seal_blob(synthetic_git_repository):
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


def test_v13_rejects_delete_then_merge_restore_without_second_ordinary_add(
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


def test_v13_ordinary_merge_can_import_unchanged_registration(synthetic_git_repository):
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


def test_v13_closed_operational_schemas_and_hash_domains(registration):
    operation = registration["operational_contract"]
    assert set(operation) == {
        "activation",
        "authoring",
        "authorization",
        "capture_audit_notification",
        "claim_ledger_publication",
        "fixed_github",
        "hash_encodings",
        "identity",
        "inherited_sources",
        "lease",
        "registration",
        "runtime_closure",
        "schema_contracts",
        "schema_version",
        "source_author_provenance",
        "startup",
    }
    schema = operation["registration"]["seal_schema"]
    assert set(schema["required_keys"]) == SCHEMA
    assert schema["optional_keys"] == []
    assert schema["schema_version"] == "lotto649-v13-registration-v1"
    assert schema["fixed_values"]["status"] == STATUS
    assert set(schema["preserved_tree_manifest_entry_exact_keys"]) == {
        "mode",
        "type",
        "oid",
        "path",
    }
    assert set(schema["registered_files_entry_exact_keys"]) == {
        "path",
        "git_blob",
        "bytes",
        "sha256",
    }
    assert set(schema["preparation_provenance_exact_keys"]) == {"contributors", "scope"}
    encodings = operation["hash_encodings"]
    for key in (
        "scientific_contract_sha256",
        "operational_contract_sha256",
        "preserved_tree_manifest_sha256",
    ):
        assert "C_plus_LF" in encodings[key]
    for key in (
        "implementation_files_sha256",
        "runtime_dependency_closure_sha256",
        "runtime_identity_sha256",
        "verified_facts_sha256",
    ):
        assert "NO LF" in encodings[key]
    assert (
        "complete canonical startup event C_plus_LF"
        in (encodings["startup_previous_and_head"])
    )
    counts = operation["schema_contracts"]
    assert counts["registration_seal_key_count"] == 13
    assert counts["authorization_key_count"] == 24
    assert counts["review_record_key_count"] == 8
    assert counts["review_comment_key_count"] == 13
    assert operation["source_author_provenance"]["phases"] == ["R13", "I13", "A_H_s13"]


def test_v13_implementation_authorization_outputs_absent_at_registration_source(
    registration,
):
    operation = registration["operational_contract"]
    assert operation["authorization"]["implementation_paths"] == sorted(IMPLEMENTATION)
    assert operation["registration"]["implementation_absent_at_R13"] == sorted(
        IMPLEMENTATION
    )
    outputs = operation["claim_ledger_publication"]["worker_outputs"]
    assert set(outputs) == {
        "startup",
        "claim",
        "ledger",
        "json",
        "markdown",
        "json_staging",
        "markdown_staging",
        "manifest",
        "manifest_staging",
    }
    stem = "reports/v13_post_rng_main_set_overlap_v13.0.0_historical"
    suffixes = {
        "startup": ".startup.jsonl",
        "claim": ".claim",
        "ledger": ".ledger.jsonl",
        "json": ".json",
        "markdown": ".md",
        "json_staging": ".json.staging",
        "markdown_staging": ".md.staging",
        "manifest": ".commit-manifest.json",
        "manifest_staging": ".commit-manifest.json.staging",
    }
    assert outputs == {role: stem + suffix for role, suffix in suffixes.items()}
    authorization = "evidence/research_authorizations/v13-post-rng-main-set-overlap-v1-historical.json"
    assert operation["identity"]["authorization_path"] == authorization
    assert operation["registration"]["authorization_absent_at_R13"] == authorization
    absent = set(IMPLEMENTATION) | {authorization} | set(outputs.values())
    authority = _authority()
    paths = {record["path"] for record in _tree(authority or "HEAD")}
    assert not paths & absent
    captures = (
        "evidence/research_audits/v13.0.0/",
        "evidence/research_notifications/v13.0.0/",
    )
    for path in paths:
        assert not path.startswith(captures)
        assert not (
            path.startswith("reports/historical-6of6-candidate__")
            and path.endswith("__v13.0.0.json")
        )
    if authority is None:
        for path in absent:
            target = ROOT / path
            assert not target.exists() and not target.is_symlink(), path
        for prefix in captures:
            target = ROOT / prefix
            assert not target.exists() and not target.is_symlink(), prefix
        assert not list(
            (ROOT / "reports").glob("historical-6of6-candidate__*__v13.0.0.json")
        )


def test_v13_no_cli_workflow_live_or_default_config_activation(registration):
    operation = registration["operational_contract"]
    identity = operation["identity"]
    assert identity["repository"] == "Jasper-Shi/lottopred"
    assert identity["branch"] == "main"
    assert identity["registration_path"] == REG
    assert identity["config_path"] == CONFIG
    assert identity["scientific_contract_sha256"] == SCIENCE_SHA
    assert identity["lease_ref"] == "refs/heads/v13-consumption-v13.0.0"
    assert identity["canonical_command"] == [
        "python3.12",
        "tools/run_v13_historical.py",
        "--consume-v13-once",
    ]
    activation = operation["activation"]
    assert activation["R13_status"] == STATUS
    assert activation["formal_registration_grants_execution"] is False
    assert activation["live_lane"].startswith("none;")
    assert activation["preauthorization_prohibited"] == [
        "governed operational history load",
        "target answers",
        "canonical attempt or execution capability",
        "real startup claim ledger lease or report",
        "formal worker",
        "workflow CLI live configuration or scheduler activation",
        "email or network mutation",
    ]
    base = {record["path"]: record for record in _tree(BASE)}
    source = {record["path"]: record for record in _tree(_authority() or "HEAD")}
    protected = {
        path
        for path in base
        if path.startswith(".github/workflows/")
        or path in {"config.yaml", "src/lotto649/cli.py", "pyproject.toml"}
    }
    assert protected
    assert all(source[path] == base[path] for path in protected)


def test_v13_runtime_is_registered_metadata_not_current_test_runtime(registration):
    runtime = registration["operational_contract"]["runtime_closure"]
    assert runtime["core_path"] == IMPLEMENTATION[0]
    assert runtime["requirements_path"] == "requirements/v12-historical.txt"
    assert runtime["requirements_sha256"] == (
        "a0dfeac17ad7e1c41dffe4b41b4810156fb028f879d312430bfc517672a570c6"
    )
    exact = runtime["exact_runtime"]
    assert exact["implementation"] == "cpython"
    assert exact["python_version"] == "3.12.11"
    assert exact["machine"] == "arm64" and exact["byteorder"] == "little"
    assert runtime["distribution_count"] == len(exact["installed_distributions"]) == 27
    assert exact["installed_distributions"]["numpy"] == "2.3.5"
    phases = registration["operational_contract"]["startup"]["required_phase_events"]
    assert phases == [
        "authorized_startup_started",
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
    # Registration unit tests remain portable; exact worker-runtime validation
    # belongs to the separately authorized implementation, never this test.


def test_v13_authorization_reviews_claim_and_startup_schemas_are_closed(registration):
    operation = registration["operational_contract"]
    authorization = operation["authorization"]
    auth_schema = authorization["authorization_schema"]
    assert auth_schema["optional_keys"] == []
    assert set(auth_schema["required_keys"]) == {
        "schema_version",
        "experiment_id",
        "model_version",
        "repository",
        "branch",
        "registration_commit",
        "registration_sha256",
        "scientific_registration_commit",
        "statistical_fingerprint_sha256",
        "operational_contract_sha256",
        "pure_core_sha256",
        "implementation_commit",
        "implementation_base",
        "implementation_merge",
        "authorization_base",
        "canonical_command",
        "governed_history_authority",
        "governed_history_identity",
        "runtime",
        "implementation_files",
        "implementation_files_sha256",
        "runtime_dependency_closure",
        "runtime_dependency_closure_sha256",
        "review_records",
    }
    record = authorization["review_record_schema"]
    assert record["optional_keys"] == []
    assert set(record["required_keys"]) == {
        "axis",
        "check_id",
        "comment_body_sha256",
        "comment_id",
        "pr_number",
        "publisher_login",
        "review_session_id",
        "reviewer_agent_id",
    }
    comment = authorization["review_comment_schema"]
    assert comment["optional_keys"] == []
    assert set(comment["required_keys"]) == {
        "schema_version",
        "axis",
        "base_sha",
        "head_sha",
        "closure_sha256",
        "operational_contract_sha256",
        "verdict",
        "blocker_count",
        "major_count",
        "reviewer_kind",
        "reviewer_agent_id",
        "review_session_id",
        "publisher_login",
    }
    assert set(authorization["facts_preimage_exact_keys"]) == {
        "repository",
        "execution_commit",
        "source_commit",
        "payload",
        "authorization_sha256",
        "authorization_review_records",
    }
    claim = operation["claim_ledger_publication"]["claim_schema"]
    assert claim["optional_keys"] == []
    assert set(claim["required_keys"]) == {
        "schema_version",
        "claimed_at",
        "bindings",
        "verified_authorization_facts",
    }
    startup = operation["startup"]
    assert set(startup["phase_payload_exact_keys"]) == set(
        startup["required_phase_events"]
    )
    assert startup["phase_payload_exact_keys"]["capability_issued"] == []
    assert startup["phase_payload_exact_keys"]["history_load_intent"] == []
    assert startup["phase_payload_exact_keys"]["claim_created"] == ["claim_sha256"]
    assert startup["phase_payload_exact_keys"]["scientific_ledger_started"] == [
        "first_event_sha256"
    ]


def test_v13_prior_p_pin_checks_git_metadata_without_reading_report(registration):
    binding = registration["scientific_contract"]["multiplicity"]["v12_binding"]
    source = "c9b483f6e89bf73eade28829188fbebe745e28c0"
    path = "reports/v12_post_rng_parity_composition_transition_v12.0.2_historical.json"
    blob = "338dea7e401ee385807cd954151664825d0e8a68"
    assert binding["source_commit"] == source
    assert binding["report_sha256"] == (
        "5582ce55fd1fbfece3f5402501bf0470d4e60b1f35c5f66aae02d928cfaa496a"
    )
    assert binding["value"] == 0.5909687963172663
    assert _require_git("ls-tree", "-z", source, "--", path) == (
        f"100644 blob {blob}\t{path}\0".encode()
    )
    assert _require_git("cat-file", "-s", blob) == b"14597956\n"
    # This proves pointer/size stability, not a fresh numeric audit of the
    # report. Never cat/show/read its contents in a registration test: they
    # include target answers. The supplied p and SHA remain frozen accounting.


def test_v13_notification_uses_distinct_global_winner_claim_and_closed_journal(
    registration,
):
    operation = registration["operational_contract"]
    capture = operation["capture_audit_notification"]
    claim = capture["global_notification_claim"]
    notification_ref = "refs/heads/v13-notification-v13.0.0"
    historical_ref = "refs/heads/v13-consumption-v13.0.0"
    assert claim["ref"] == notification_ref
    assert claim["historical_lease_ref"] == historical_ref
    assert notification_ref != operation["identity"]["lease_ref"] == historical_ref
    assert type(claim["global_maximum_authorized_SMTP_calls"]) is int
    assert claim["global_maximum_authorized_SMTP_calls"] == 1
    assert claim["global_maximum_POST_calls_claim"].startswith("NOT ASSERTED")
    for key in (
        "maximum_commit_POST_attempts_per_invocation",
        "maximum_createRef_attempts_per_invocation",
        "maximum_default_SMTP_calls_per_winning_invocation",
    ):
        assert type(claim[key]) is int and claim[key] == 1
    body_keys = {
        "schema_version",
        "experiment_id",
        "model_version",
        "target_draw_date",
        "notification_kind",
        "audited_publication_commit",
        "audit_json_sha256",
        "candidate_bundle_sha256",
        "intent_identity_sha256",
        "operational_contract_sha256",
        "nonce_hex",
    }
    assert claim["claim_body_optional_keys"] == []
    assert set(claim["claim_body_required_keys"]) == body_keys
    assert set(claim["claim_body_values"]) == body_keys
    assert claim["claim_body_values"]["schema_version"] == (
        "lotto649-v13.0.0-notification-claim-v1"
    )
    projection = claim["projection_contract"]
    assert set(projection["canonical_body_exact_keys"]) == body_keys
    assert projection["POST_ref_request_shape"]["ref"] == notification_ref
    assert projection["POST_ref_response_and_GET_ref_shape"]["ref"] == notification_ref
    assert projection["POST_ref_request_shape"]["required_keys"] == ["ref", "sha"]
    assert projection["POST_ref_request_shape"]["optional_keys"] == []
    assert projection["GET_message"] == "exact_canonical_body_no_trailing_LF"
    assert projection["POST_message"] == "canonical_body_plus_exactly_one_LF"
    assert (
        "no_historical_lease_schema_or_ref_reuse" in projection["representation_rules"]
    )
    intent = capture["notification_intent_schema"]
    assert intent["retry_allowed"] is False
    assert intent["optional_keys"] == intent["identity_optional_keys"] == []
    assert set(intent["required_keys"]) == {
        "schema_version",
        "identity",
        "identity_sha256",
        "expected_claim_oid",
        "raw_commit_sha256",
        "commit_request_bytes",
        "commit_request_sha256",
        "ref_request_bytes",
        "ref_request_sha256",
        "started_at",
        "state",
        "retry_allowed",
    }
    assert set(intent["identity_required_keys"]) == {
        "experiment_id",
        "model_version",
        "target_draw_date",
        "notification_kind",
        "candidate_bundle_path",
        "candidate_bundle_sha256",
        "audit_json_path",
        "audit_json_sha256",
        "audited_publication_commit",
        "publication_tree_oid",
        "scientific_contract_sha256",
        "operational_contract_sha256",
        "nonce_hex",
    }
    journal = capture["notification_journal_schema"]
    assert journal["initial_previous_sha256"] is None
    assert journal["event_optional_keys"] == []
    assert set(journal["event_required_keys"]) == {
        "schema_version",
        "sequence",
        "generated_at",
        "previous_event_sha256",
        "kind",
        "payload",
    }
    assert journal["phases"] == [
        "notification_intent_frozen",
        "notification_commit_POST_intent",
        "notification_commit_POST_receipt",
        "notification_commit_GET_verified",
        "notification_ref_POST_intent",
        "notification_ref_POST_receipt",
        "notification_ref_reread_verified",
        "notification_send_intent",
        "notification_send_result",
    ]
    assert set(journal["phase_payload_exact_keys"]) == set(journal["phases"])
    assert journal["phase_payload_exact_keys"]["notification_send_result"] == [
        "result_enum"
    ]
    result = capture["notification_result_schema"]
    assert result["retry_allowed"] is False and result["optional_keys"] == []
    assert result["result_values"] == ["sent", "failed", "unknown", "not_sent"]
    assert set(result["required_keys"]) == {
        "schema_version",
        "experiment_id",
        "model_version",
        "target_draw_date",
        "notification_kind",
        "intent_sha256",
        "claim_commit",
        "sealed_journal",
        "completed_at",
        "result",
        "retry_allowed",
    }
    assert result["sealed_journal_exact_keys"] == ["path", "bytes", "sha256"]
    publication = capture["notification_evidence_publication"]
    assert "only its exact owned local intent, journal and any result" in publication
    assert (
        "cannot publish over winner paths or create alternate failure-evidence paths"
        in publication
    )
    # These are frozen requirements for future I13 tests, not fake production
    # capabilities or a claim that an unimplemented SMTP protocol has run.


def test_v13_global_notification_claim_requires_all_future_synthetic_cases(
    registration,
):
    cases = registration["operational_contract"]["capture_audit_notification"][
        "required_I13_synthetic_cases"
    ]
    assert cases == [
        "concurrent_two_fresh_clones_both404_two_commit_uploads_exactly_one_atomic_createRef_winner_and_one_SMTP_call",
        "fresh_exact_literal_notification_ref404_is_required_no_list_absence_or_redirect",
        "present_ref_including_same_expected_OID_never_issues_notification_capability",
        "createRef_loser_or_ref_mismatch_cannot_adopt_winner_or_send",
        "uncertain_commit_POST_or_createRef_or_reread_preserves_intent_and_never_sends_or_retries",
        "winner_pre_SMTP_ownership_or_main_or_audit_failure_consumes_global_claim_no_takeover",
        "SMTP_true_false_exception_timeout_unknown_each_consume_same_send_slot_no_retry_or_second_process_send",
        "durable_intent_request_hashes_precede_each_POST_and_send_intent_precedes_SMTP",
        "intent_identity_preimage_remote_claim_complete_intent_journal_result_graph_is_acyclic",
        "notification_commit_raw_CplusLF_POST_CplusLF_GET_CnoLF_exact_OID_and_closed_nested_projection",
        "notification_capability_rejects_copy_subclass_deserialization_fabrication_restart_and_borrowed_marker",
        "historical_lease_and_worker_are_never_reused_or_invoked_by_notification_procedure",
        "Top12_only_never_starts_notification_intent_journal_claim_or_SMTP",
        "notification_preserves_uncertain_partial_files_no_update_delete_resume_or_alternate_logs",
    ]
    assert len(cases) == len(set(cases)) == 14


def test_v13_capture_paths_include_immutable_notification_journal(registration):
    operation = registration["operational_contract"]
    expected = {
        "candidate_bundle": "reports/historical-6of6-candidate__{target_date}__{primary_model_name}__v13.0.0.json",
        "independent_audit_json": "evidence/research_audits/v13.0.0/historical-6of6__{target_date}__{primary_model_name}.json",
        "independent_audit_markdown": "evidence/research_audits/v13.0.0/historical-6of6__{target_date}__{primary_model_name}.md",
        "notification_intent": "evidence/research_notifications/v13.0.0/historical-6of6__{target_date}.intent.json",
        "notification_journal": "evidence/research_notifications/v13.0.0/historical-6of6__{target_date}.journal.jsonl",
        "notification_result": "evidence/research_notifications/v13.0.0/historical-6of6__{target_date}.result.json",
    }
    assert operation["capture_audit_notification"]["paths"] == expected
    assert operation["registration"]["capture_namespaces_absent_at_R13"] == expected
    assert (
        operation["capture_audit_notification"]["notification_journal_schema"]["path"]
        == (expected["notification_journal"])
    )
    # The registration-source absence test covers entire audit/notification
    # namespaces, including any rendered date/model and every journal path.


def test_v13_json_markdown_and_two_journal_hash_domains_are_distinct(registration):
    encodings = registration["operational_contract"]["hash_encodings"]
    assert (
        "JSON documents only"
        in encodings["all_seals_config_claim_reports_audit_notifications"]
    )
    assert (
        "does NOT describe Markdown"
        in encodings["all_seals_config_claim_reports_audit_notifications"]
    )
    assert "never JSON serialization" in encodings["markdown"]
    assert "one final LF" in encodings["markdown"]
    assert "NO LF inherited from R3" in encodings["scientific_event_hash"]
    assert (
        "Initial previous_event_sha256 is64zerohex"
        in encodings["scientific_event_hash"]
    )
    assert (
        "complete canonical startup event C_plus_LF"
        in encodings["startup_previous_and_head"]
    )
    assert "initial previous null" in encodings["notification_journal"]
    assert "Whole-line C_plus_LF SHA chain" in encodings["notification_journal"]
    assert "Whole intent SHA is separate" in encodings["notification_identity_sha256"]


def test_v13_all_prior_accounting_pins_are_metadata_only_and_fixed(registration):
    operation = registration["operational_contract"]
    prior = operation["authorization"]["prior_family_accounting_preflight"]
    assert prior["schema_version"] == "lotto649-v13-prior-accounting-metadata-v1"
    assert (
        prior["scientific_vector_unchanged"]
        == (registration["scientific_contract"]["multiplicity"]["ordered_raw_p"])
    )
    keys = {"commit", "path", "mode", "type", "git_blob", "bytes"}
    assert set(prior["object_pin_exact_keys"]) == keys
    assert len(prior["object_pins"]) == 6
    seen = set()
    for pin in prior["object_pins"]:
        assert type(pin) is dict and set(pin) == keys
        _hex(pin["commit"], 40)
        _hex(pin["git_blob"], 40)
        _path(pin["path"])
        assert pin["mode"] == "100644" and pin["type"] == "blob"
        assert type(pin["bytes"]) is int and pin["bytes"] > 0
        identity = (pin["commit"], pin["path"])
        assert identity not in seen
        seen.add(identity)
        expected = (
            f"{pin['mode']} {pin['type']} {pin['git_blob']}\t{pin['path']}\0".encode()
        )
        assert (
            _require_git("ls-tree", "-z", pin["commit"], "--", pin["path"]) == expected
        )
        assert _require_git("cat-file", "-t", pin["git_blob"]) == b"blob\n"
        assert (
            _require_git("cat-file", "-s", pin["git_blob"])
            == f"{pin['bytes']}\n".encode()
        )
        assert _git("merge-base", "--is-ancestor", pin["commit"], BASE).returncode == 0
    assert prior["known_previous_report_sha256"] == (
        "5582ce55fd1fbfece3f5402501bf0470d4e60b1f35c5f66aae02d928cfaa496a"
    )
    assert "Never read/parse" in prior["read_scope"]
    assert "do not freshly extract values" in prior["reliance"]
    # No show/cat-file-p/read_bytes on report or audit payloads occurs here.
