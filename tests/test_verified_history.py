from __future__ import annotations

import json
import os
import subprocess
from copy import deepcopy
from dataclasses import FrozenInstanceError, dataclass
from datetime import date
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest

from lotto649.domain import Draw
from lotto649.verified_history import load_verified_history

ROOT = Path(__file__).resolve().parents[1]
INCIDENT_ID = "DI-2026-08-20-registered-history"
ARTIFACT_COMMIT = "b04393944ef12f78417dfb6151343c72d4c2a2ac"
REGISTERED_OLD_COMMIT = "90177c80cfb070038d79508fb2e73305a297f516"
BASE_PATH = f"data/processed/epochs/{INCIDENT_ID}/corrected_draws.csv"
SEAL_PATH = f"evidence/data_integrity/{INCIDENT_ID}/seal.json"
SUFFIX_PATH = f"data/processed/epochs/{INCIDENT_ID}/live_draws.jsonl"
BASE_FILE_SHA256 = "1e1bb768877d3f1b3b901a8cb897b6f439ff80f675c57e786cb54ff1179ac8ad"
BASE_ROWS_SHA256 = "58988bbb130be2142bc5a2b20df571cc458eabe66cd873773f55ca1dbfae8874"
OLD_FILE_SHA256 = "edfb7f8a4a7711a630957d6f86b567e6b254caf7b1d1aaea0edf1d16a34155b3"
OLD_ROWS_SHA256 = "257aef242bb898649b0923ac03f2271c7536ff7f840edf552c0dc6b4b03ce1dd"
DEPLOYED_SEAL_SHA256 = (
    "80397752105b567d6a8bdd3673b12ffa470a12efbd792719a4f6c89ef391f6fd"
)
DEPLOYED_SUFFIX_SHA256 = (
    "b91be6a4057648abd86dc0e6fc5d762fc4cd9b222519c147d635703cc550a803"
)
DEPLOYED_SUFFIX_HEAD_SHA256 = (
    "3022b98fefbe3dbbc80423574319c169edcc845bf2218152c6abe18d0be27475"
)
DEPLOYED_EVIDENCE_COMMIT = "60dbd42a502850091508491f9011f9a08acf894f"

ARTIFACT_PATHS = (
    BASE_PATH,
    f"evidence/data_integrity/{INCIDENT_ID}/incident.json",
    f"evidence/data_integrity/{INCIDENT_ID}/official_draws.csv",
    f"evidence/data_integrity/{INCIDENT_ID}/reconciliation.manifest.json",
    f"evidence/data_integrity/{INCIDENT_ID}/reviewed-adjudication.json",
    f"evidence/data_integrity/{INCIDENT_ID}/source-index.json",
)
CODE_PATHS = (
    "src/lotto649/data_integrity.py",
    "src/lotto649/official_history.py",
    "tests/test_data_integrity.py",
    "tests/test_data_integrity_incident.py",
    "tests/test_official_history.py",
    "tools/build_data_integrity_incident.py",
)


def _canonical_json(value: Any, *, newline: bool = False) -> bytes:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode()
    return raw + (b"\n" if newline else b"")


def _git_bytes(repository: Path, *arguments: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
    ).stdout


def _git_text(repository: Path, *arguments: str) -> str:
    return _git_bytes(repository, *arguments).decode().strip()


def _git_commit(repository: Path, message: str, created_at: str) -> None:
    environment = os.environ.copy()
    environment.update(
        GIT_AUTHOR_DATE=created_at,
        GIT_COMMITTER_DATE=created_at,
    )
    subprocess.run(
        ["git", "-C", str(repository), "commit", "-qm", message],
        check=True,
        capture_output=True,
        env=environment,
    )


def _write(repository: Path, relative_path: str, raw: bytes) -> None:
    path = repository / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)


def _blob_metadata(repository: Path, commit: str, relative_path: str) -> dict[str, Any]:
    raw = _git_bytes(repository, "show", f"{commit}:{relative_path}")
    return {
        "git_blob": _git_text(repository, "rev-parse", f"{commit}:{relative_path}"),
        "bytes": len(raw),
        "sha256": sha256(raw).hexdigest(),
    }


def _install_resealed_payload(repository: Path, payload: dict[str, Any]) -> str:
    resealed = deepcopy(payload)
    resealed.pop("seal_body_sha256", None)
    resealed["seal_body_sha256"] = sha256(_canonical_json(resealed)).hexdigest()
    raw = _canonical_json(resealed, newline=True)
    _write(repository, SEAL_PATH, raw)
    return sha256(raw).hexdigest()


@dataclass(frozen=True)
class SealedRepository:
    path: Path
    seal_sha256: str
    seal: dict[str, Any]
    artifact_commit: str
    seal_commit: str


@dataclass(frozen=True)
class InstalledSuffix:
    file_sha256: str
    head_event_sha256: str
    evidence_commit: str
    events: tuple[dict[str, Any], ...]


def _sealed_repository(
    tmp_path: Path, *, base_raw_override: bytes | None = None
) -> SealedRepository:
    repository = tmp_path / "repository"
    repository.mkdir()
    _git_text(repository, "init", "-q")
    _git_text(repository, "config", "user.email", "fixture@example.invalid")
    _git_text(repository, "config", "user.name", "Verified History Fixture")

    old_raw = _git_bytes(
        ROOT, "show", f"{REGISTERED_OLD_COMMIT}:data/processed/draws.csv"
    )
    assert sha256(old_raw).hexdigest() == OLD_FILE_SHA256
    _write(repository, "README.md", b"synthetic sealed-history repository\n")
    _write(repository, "data/processed/draws.csv", old_raw)
    _git_text(repository, "add", "README.md", "data/processed/draws.csv")
    _git_commit(repository, "registered parent", "2026-08-20T05:59:59Z")
    artifact_parent = _git_text(repository, "rev-parse", "HEAD")
    old_blob = _git_text(repository, "rev-parse", "HEAD:data/processed/draws.csv")

    registered_base_raw = _git_bytes(ROOT, "show", f"{ARTIFACT_COMMIT}:{BASE_PATH}")
    assert sha256(registered_base_raw).hexdigest() == BASE_FILE_SHA256
    base_raw = (
        base_raw_override if base_raw_override is not None else registered_base_raw
    )
    artifact_raw = {
        BASE_PATH: base_raw,
        f"evidence/data_integrity/{INCIDENT_ID}/incident.json": b"{}\n",
        f"evidence/data_integrity/{INCIDENT_ID}/official_draws.csv": b"official\n",
        f"evidence/data_integrity/{INCIDENT_ID}/reconciliation.manifest.json": b"{}\n",
        f"evidence/data_integrity/{INCIDENT_ID}/reviewed-adjudication.json": b"{}\n",
        f"evidence/data_integrity/{INCIDENT_ID}/source-index.json": b"{}\n",
    }
    for relative_path, raw in artifact_raw.items():
        _write(repository, relative_path, raw)
    for index, relative_path in enumerate(CODE_PATHS):
        _write(repository, relative_path, f"# frozen code {index}\n".encode())
    _git_text(repository, "add", *ARTIFACT_PATHS, *CODE_PATHS)
    _git_commit(repository, "closed corrected epoch", "2026-08-20T06:00:00Z")
    artifact_commit = _git_text(repository, "rev-parse", "HEAD")

    artifacts = {
        path: _blob_metadata(repository, artifact_commit, path)
        for path in sorted(ARTIFACT_PATHS)
    }
    code_identities = {
        path: _blob_metadata(repository, artifact_commit, path)
        for path in sorted(CODE_PATHS)
    }
    base = artifacts[BASE_PATH]
    manifest_path = (
        f"evidence/data_integrity/{INCIDENT_ID}/reconciliation.manifest.json"
    )
    manifest = artifacts[manifest_path]
    seal = {
        "schema_version": "lotto649-data-integrity-seal-v1",
        "incident_id": INCIDENT_ID,
        "artifact_commit": artifact_commit,
        "artifact_parent": artifact_parent,
        "artifact_commit_created_at": "2026-08-20T06:00:00Z",
        "status": "sealed_closed_corrected_epoch",
        "registered_old_identity": {
            "byte_sha256": sha256(old_raw).hexdigest(),
            "bytes": len(old_raw),
            "commit": artifact_parent,
            "draw_count": 4432,
            "git_blob": old_blob,
            "path": "data/processed/draws.csv",
            "rows_sha256": OLD_ROWS_SHA256,
        },
        "artifacts": artifacts,
        "corrected_epoch": {
            "path": BASE_PATH,
            "git_blob": base["git_blob"],
            "bytes": base["bytes"],
            "file_sha256": base["sha256"],
            "draw_count": 4442,
            "rows_sha256": BASE_ROWS_SHA256,
            "history_start": "1982-06-12",
            "history_through": "2026-08-15",
        },
        "reconciliation_manifest": {
            "path": manifest_path,
            "git_blob": manifest["git_blob"],
            "bytes": manifest["bytes"],
            "file_sha256": manifest["sha256"],
            "manifest_sha256": "9" * 64,
        },
        "source_collection": {
            "asset_count": 109,
            "collection_line_sha256": (
                "7e3328896d5bb7950c10cf5b9cca0e4d7cadd7265c6d4a4f6b3dcc8793b0a88a"
            ),
            "draw_count": 4442,
            "history_start": "1982-06-12",
            "history_through": "2026-08-15",
            "json_rows_sha256": BASE_ROWS_SHA256,
            "source_assets_sha256": (
                "1be14241443477f7ba347c8fe87605bb4c1367c7b7390f5f05762478a4c36b96"
            ),
        },
        "reconciliation_summary": {
            "old_count": 4432,
            "official_count": 4442,
            "decision_count": 4444,
            "unchanged": 4421,
            "inserted": 12,
            "deleted": 2,
            "updated": 9,
            "unresolved": 0,
            "corrected_count": 4442,
        },
        "code_identities": code_identities,
    }
    seal["seal_body_sha256"] = sha256(_canonical_json(seal)).hexdigest()
    seal_raw = _canonical_json(seal, newline=True)
    seal_sha256 = sha256(seal_raw).hexdigest()
    _write(repository, SEAL_PATH, seal_raw)
    _write(repository, SUFFIX_PATH, b"")
    _git_text(repository, "add", SEAL_PATH, SUFFIX_PATH)
    _git_commit(repository, "publish external seal", "2026-08-20T06:00:01Z")
    return SealedRepository(
        path=repository,
        seal_sha256=seal_sha256,
        seal=seal,
        artifact_commit=artifact_commit,
        seal_commit=_git_text(repository, "rev-parse", "HEAD"),
    )


def _draw_payload(draw: Draw) -> dict[str, Any]:
    return {
        "draw_date": draw.draw_date.isoformat(),
        "numbers": list(draw.numbers),
        "bonus": draw.bonus,
    }


def _row_sha256(draw: Draw) -> str:
    return sha256(_canonical_json(_draw_payload(draw))).hexdigest()


def _wclc_html(draw: Draw) -> bytes:
    date_text = draw.draw_date.strftime("%A, %B %d, %Y")
    numbers = " ".join(f"{value:02d}" for value in draw.numbers)
    return (
        f"<!doctype html><html><body>{date_text} "
        f"CLASSIC DRAW {numbers} Bonus {draw.bonus:02d}</body></html>"
    ).encode()


def _loto_quebec_html(draw: Draw) -> bytes:
    main = "".join(f'<span class="num">{value:02d}</span>' for value in draw.numbers)
    return (
        "<!doctype html><html><body>"
        f'<span id="dateAffichee">{draw.draw_date.isoformat()}</span>'
        '<div class="lqZoneProduit principal lotto-6-49">'
        f'<div class="numeros tirageClassique">{main}'
        f'<span class="num complementaire">{draw.bonus:02d}</span>'
        "</div></div></body></html>"
    ).encode()


def _install_suffix(
    fixture: SealedRepository, draws: tuple[Draw, ...]
) -> InstalledSuffix:
    evidence: dict[tuple[date, str], tuple[str, bytes]] = {}
    for draw in draws:
        draw_date = draw.draw_date.isoformat()
        evidence[(draw.draw_date, "wclc")] = (
            f"evidence/live_sources/wclc/{draw_date}.html",
            _wclc_html(draw),
        )
        evidence[(draw.draw_date, "loto_quebec")] = (
            f"evidence/live_sources/loto_quebec/{draw_date}.html",
            _loto_quebec_html(draw),
        )
    for path, raw in evidence.values():
        _write(fixture.path, path, raw)
    _git_text(fixture.path, "add", *(path for path, _ in evidence.values()))
    _git_commit(
        fixture.path,
        "record immutable source receipts",
        "2026-08-23T12:05:00Z",
    )
    evidence_commit = _git_text(fixture.path, "rev-parse", "HEAD")

    previous = fixture.seal_sha256
    events = []
    for sequence, draw in enumerate(draws):
        row_sha256 = _row_sha256(draw)
        draw_date = draw.draw_date.isoformat()
        receipts = [
            {
                "provider": "Western Canada Lottery Corporation",
                "source_type": "wclc_recent_html",
                "url": (
                    "https://www.wclc.com/winning-numbers/lotto-649-extra.htm"
                    "?WT.ac=Lottery_Lotto-649_Past-Winning-Numbers-Results-WCLC"
                ),
                "retrieved_at": "2026-08-23T12:00:00Z",
                "evidence_path": evidence[(draw.draw_date, "wclc")][0],
                "bytes": len(evidence[(draw.draw_date, "wclc")][1]),
                "sha256": sha256(evidence[(draw.draw_date, "wclc")][1]).hexdigest(),
                "supported_row_sha256": row_sha256,
                "independence_group": "wclc",
            },
            {
                "provider": "Loto-Québec",
                "source_type": "loto_quebec_detail_html",
                "url": (
                    "https://loteries.lotoquebec.com/en/lotteries/"
                    "lotto-6-49-resultats?widget=resultats&action=detailles&"
                    f"noproduit=212&date={draw_date}"
                ),
                "retrieved_at": "2026-08-23T12:00:01Z",
                "evidence_path": evidence[(draw.draw_date, "loto_quebec")][0],
                "bytes": len(evidence[(draw.draw_date, "loto_quebec")][1]),
                "sha256": sha256(
                    evidence[(draw.draw_date, "loto_quebec")][1]
                ).hexdigest(),
                "supported_row_sha256": row_sha256,
                "independence_group": "loto_quebec",
            },
        ]
        receipts.sort(
            key=lambda receipt: (
                receipt["independence_group"],
                receipt["provider"],
                receipt["source_type"],
                receipt["url"],
                receipt["sha256"],
            )
        )
        event = {
            "schema_version": "lotto649-history-suffix-event-v1",
            "incident_id": INCIDENT_ID,
            "sequence": sequence,
            "base_seal_sha256": fixture.seal_sha256,
            "previous_event_sha256": previous,
            "evidence_commit": evidence_commit,
            "draw": _draw_payload(draw),
            "source_receipts": receipts,
        }
        event["event_sha256"] = sha256(_canonical_json(event)).hexdigest()
        events.append(event)
        previous = event["event_sha256"]
    suffix_raw = b"".join(_canonical_json(event, newline=True) for event in events)
    _write(fixture.path, SUFFIX_PATH, suffix_raw)
    return InstalledSuffix(
        file_sha256=sha256(suffix_raw).hexdigest(),
        head_event_sha256=events[-1]["event_sha256"],
        evidence_commit=evidence_commit,
        events=tuple(events),
    )


def _rehash_event(event: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(event)
    result.pop("event_sha256", None)
    result["event_sha256"] = sha256(_canonical_json(result)).hexdigest()
    return result


def _write_suffix_events(
    repository: Path, events: tuple[dict[str, Any], ...]
) -> tuple[str, str]:
    raw = b"".join(_canonical_json(event, newline=True) for event in events)
    _write(repository, SUFFIX_PATH, raw)
    return sha256(raw).hexdigest(), events[-1]["event_sha256"]


def _replace_receipt_asset(
    fixture: SealedRepository,
    event: dict[str, Any],
    *,
    independence_group: str,
    raw: bytes,
) -> dict[str, Any]:
    return _replace_receipt_assets(
        fixture,
        event,
        raw_by_group={independence_group: raw},
    )


def _replace_receipt_assets(
    fixture: SealedRepository,
    event: dict[str, Any],
    *,
    raw_by_group: dict[str, bytes],
) -> dict[str, Any]:
    result = deepcopy(event)
    paths = []
    for receipt in result["source_receipts"]:
        group = receipt["independence_group"]
        replacement = raw_by_group.get(group)
        if replacement is None:
            current = (fixture.path / receipt["evidence_path"]).read_bytes()
            replacement = current + f"\n<!-- refreshed {group} -->\n".encode()
        _write(fixture.path, receipt["evidence_path"], replacement)
        paths.append(receipt["evidence_path"])
        receipt["bytes"] = len(replacement)
        receipt["sha256"] = sha256(replacement).hexdigest()
    _git_text(fixture.path, "add", *paths)
    _git_commit(
        fixture.path,
        "replace synthetic evidence assets",
        "2026-08-23T12:06:00Z",
    )
    result["evidence_commit"] = _git_text(fixture.path, "rev-parse", "HEAD")
    return _rehash_event(result)


def test_loads_git_bound_corrected_epoch_with_an_empty_suffix(tmp_path):
    fixture = _sealed_repository(tmp_path)

    history = load_verified_history(
        fixture.path,
        seal_path=SEAL_PATH,
        expected_seal_sha256=fixture.seal_sha256,
        suffix_path=SUFFIX_PATH,
    )

    assert history.epoch == INCIDENT_ID
    assert len(history.draws) == 4442
    assert history.draws[0].draw_date == date(1982, 6, 12)
    assert history.draws[-1].draw_date == date(2026, 8, 15)
    assert history.seal.file_sha256 == fixture.seal_sha256
    assert history.seal.artifact_commit == fixture.artifact_commit
    assert history.base.path == BASE_PATH
    assert history.base.rows_sha256 == BASE_ROWS_SHA256
    assert history.suffix.path == SUFFIX_PATH
    assert history.suffix.event_count == 0
    assert history.suffix.base_seal_sha256 == fixture.seal_sha256
    assert history.suffix.file_sha256 == sha256(b"").hexdigest()
    assert history.suffix.head_event_sha256 is None
    with pytest.raises(FrozenInstanceError):
        history.epoch = "mutated"


def test_rejects_a_noncanonical_seal_even_when_the_file_hash_is_pinned(tmp_path):
    fixture = _sealed_repository(tmp_path)
    noncanonical = (json.dumps(fixture.seal, indent=2, sort_keys=True) + "\n").encode()
    _write(fixture.path, SEAL_PATH, noncanonical)

    with pytest.raises(ValueError, match="canonical"):
        load_verified_history(
            fixture.path,
            seal_path=SEAL_PATH,
            expected_seal_sha256=sha256(noncanonical).hexdigest(),
            suffix_path=SUFFIX_PATH,
        )


def test_rejects_a_seal_whose_body_no_longer_matches_its_self_hash(tmp_path):
    fixture = _sealed_repository(tmp_path)
    tampered = {
        **fixture.seal,
        "artifact_commit_created_at": "2026-08-20T06:00:01Z",
    }
    raw = _canonical_json(tampered, newline=True)
    _write(fixture.path, SEAL_PATH, raw)

    with pytest.raises(ValueError, match="body SHA-256"):
        load_verified_history(
            fixture.path,
            seal_path=SEAL_PATH,
            expected_seal_sha256=sha256(raw).hexdigest(),
            suffix_path=SUFFIX_PATH,
        )


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda seal: seal.update(schema_version="lotto649-seal-v2"), "schema"),
        (lambda seal: seal.update(status="draft"), "status"),
        (lambda seal: seal.update(incident_id="DI-coordinated-rewrite"), "incident"),
        (
            lambda seal: seal.update(created_at=seal.pop("artifact_commit_created_at")),
            "schema",
        ),
        (lambda seal: seal.update(unregistered_extension=True), "schema"),
    ],
)
def test_rejects_coordinated_rewrites_of_frozen_seal_semantics(
    tmp_path, mutate, message
):
    fixture = _sealed_repository(tmp_path)
    tampered = deepcopy(fixture.seal)
    mutate(tampered)
    external_pin = _install_resealed_payload(fixture.path, tampered)

    with pytest.raises(ValueError, match=message):
        load_verified_history(
            fixture.path,
            seal_path=SEAL_PATH,
            expected_seal_sha256=external_pin,
            suffix_path=SUFFIX_PATH,
        )


@pytest.mark.parametrize(
    "mutate",
    [
        lambda seal: seal["registered_old_identity"].pop("byte_sha256"),
        lambda seal: seal["source_collection"].update(extension="not frozen"),
        lambda seal: seal["reconciliation_summary"].update(updated="9"),
        lambda seal: seal["corrected_epoch"].update(extension=True),
        lambda seal: seal["reconciliation_manifest"].pop("manifest_sha256"),
    ],
)
def test_rejects_nonfrozen_nested_seal_shapes_and_types(tmp_path, mutate):
    fixture = _sealed_repository(tmp_path)
    tampered = deepcopy(fixture.seal)
    mutate(tampered)
    external_pin = _install_resealed_payload(fixture.path, tampered)

    with pytest.raises(ValueError, match="schema"):
        load_verified_history(
            fixture.path,
            seal_path=SEAL_PATH,
            expected_seal_sha256=external_pin,
            suffix_path=SUFFIX_PATH,
        )


def test_rejects_a_seal_with_the_wrong_artifact_parent_after_coordinated_rehash(
    tmp_path,
):
    fixture = _sealed_repository(tmp_path)
    tampered = deepcopy(fixture.seal)
    tampered["artifact_parent"] = "0" * 40
    external_pin = _install_resealed_payload(fixture.path, tampered)

    with pytest.raises(ValueError, match="artifact parent"):
        load_verified_history(
            fixture.path,
            seal_path=SEAL_PATH,
            expected_seal_sha256=external_pin,
            suffix_path=SUFFIX_PATH,
        )


@pytest.mark.parametrize("inventory_name", ["artifacts", "code_identities"])
def test_rejects_an_incomplete_frozen_artifact_inventory(tmp_path, inventory_name):
    fixture = _sealed_repository(tmp_path)
    tampered = deepcopy(fixture.seal)
    tampered[inventory_name].pop(next(iter(tampered[inventory_name])))
    external_pin = _install_resealed_payload(fixture.path, tampered)

    with pytest.raises(ValueError, match="inventory"):
        load_verified_history(
            fixture.path,
            seal_path=SEAL_PATH,
            expected_seal_sha256=external_pin,
            suffix_path=SUFFIX_PATH,
        )


@pytest.mark.parametrize(
    ("field", "wrong"),
    [("git_blob", "0" * 40), ("bytes", 1), ("sha256", "0" * 64)],
)
def test_rejects_artifact_metadata_that_disagrees_with_git(tmp_path, field, wrong):
    fixture = _sealed_repository(tmp_path)
    tampered = deepcopy(fixture.seal)
    path = f"evidence/data_integrity/{INCIDENT_ID}/incident.json"
    tampered["artifacts"][path][field] = wrong
    external_pin = _install_resealed_payload(fixture.path, tampered)

    with pytest.raises(ValueError, match="artifact integrity"):
        load_verified_history(
            fixture.path,
            seal_path=SEAL_PATH,
            expected_seal_sha256=external_pin,
            suffix_path=SUFFIX_PATH,
        )


@pytest.mark.parametrize(
    ("field", "wrong"),
    [
        ("path", "data/processed/draws.csv"),
        ("git_blob", "0" * 40),
        ("bytes", 1),
        ("file_sha256", "0" * 64),
        ("draw_count", 4441),
        ("rows_sha256", "0" * 64),
        ("history_start", "1982-06-19"),
        ("history_through", "2026-08-12"),
    ],
)
def test_rejects_a_coordinated_rewrite_of_corrected_epoch_identity(
    tmp_path, field, wrong
):
    fixture = _sealed_repository(tmp_path)
    tampered = deepcopy(fixture.seal)
    tampered["corrected_epoch"][field] = wrong
    external_pin = _install_resealed_payload(fixture.path, tampered)

    with pytest.raises(ValueError, match="corrected epoch identity"):
        load_verified_history(
            fixture.path,
            seal_path=SEAL_PATH,
            expected_seal_sha256=external_pin,
            suffix_path=SUFFIX_PATH,
        )


def test_rejects_a_valid_but_wrong_git_commit_as_the_artifact_commit(tmp_path):
    fixture = _sealed_repository(tmp_path)
    tampered = deepcopy(fixture.seal)
    tampered["artifact_commit"] = fixture.seal_commit
    tampered["artifact_parent"] = fixture.artifact_commit
    external_pin = _install_resealed_payload(fixture.path, tampered)

    with pytest.raises(ValueError, match="artifact closure"):
        load_verified_history(
            fixture.path,
            seal_path=SEAL_PATH,
            expected_seal_sha256=external_pin,
            suffix_path=SUFFIX_PATH,
        )


@pytest.mark.parametrize(
    "mutate",
    [
        lambda seal: seal["reconciliation_manifest"].update(git_blob="0" * 40),
        lambda seal: seal["source_collection"].update(asset_count=108),
        lambda seal: seal["reconciliation_summary"].update(updated=8),
        lambda seal: seal["registered_old_identity"].update(byte_sha256="0" * 64),
        lambda seal: seal.update(artifact_commit_created_at="not-a-UTC-timestamp"),
    ],
)
def test_rejects_coordinated_rewrites_of_seal_semantics(tmp_path, mutate):
    fixture = _sealed_repository(tmp_path)
    tampered = deepcopy(fixture.seal)
    mutate(tampered)
    external_pin = _install_resealed_payload(fixture.path, tampered)

    with pytest.raises(ValueError, match="seal semantic"):
        load_verified_history(
            fixture.path,
            seal_path=SEAL_PATH,
            expected_seal_sha256=external_pin,
            suffix_path=SUFFIX_PATH,
        )


def test_rejects_a_resealed_artifact_commit_timestamp_not_found_in_git(tmp_path):
    fixture = _sealed_repository(tmp_path)
    tampered = deepcopy(fixture.seal)
    tampered["artifact_commit_created_at"] = "2099-01-01T00:00:00Z"
    external_pin = _install_resealed_payload(fixture.path, tampered)

    with pytest.raises(ValueError, match="seal semantic"):
        load_verified_history(
            fixture.path,
            seal_path=SEAL_PATH,
            expected_seal_sha256=external_pin,
            suffix_path=SUFFIX_PATH,
        )


def test_git_replace_cannot_rewrite_the_sealed_commit_identity(tmp_path):
    fixture = _sealed_repository(tmp_path)
    tree = _git_text(fixture.path, "rev-parse", f"{fixture.artifact_commit}^{{tree}}")
    parent = _git_text(fixture.path, "rev-parse", f"{fixture.artifact_commit}^")
    environment = os.environ.copy()
    environment.update(
        GIT_AUTHOR_DATE="2026-08-20T06:00:02Z",
        GIT_COMMITTER_DATE="2026-08-20T06:00:02Z",
    )
    fake = (
        subprocess.run(
            ["git", "-C", str(fixture.path), "commit-tree", tree, "-p", parent],
            input=b"coordinated replacement object\n",
            check=True,
            capture_output=True,
            env=environment,
        )
        .stdout.decode()
        .strip()
    )
    _git_text(fixture.path, "replace", fixture.artifact_commit, fake)
    attacker = deepcopy(fixture.seal)
    attacker["artifact_commit_created_at"] = "2026-08-20T06:00:02Z"
    attacker_pin = _install_resealed_payload(fixture.path, attacker)

    with pytest.raises(ValueError, match="semantic mismatch"):
        load_verified_history(
            fixture.path,
            seal_path=SEAL_PATH,
            expected_seal_sha256=attacker_pin,
            suffix_path=SUFFIX_PATH,
        )


def test_git_grafts_cannot_rewrite_the_sealed_commit_identity(tmp_path):
    fixture = _sealed_repository(tmp_path)
    grafts = fixture.path / ".git/info/grafts"
    grafts.parent.mkdir(parents=True, exist_ok=True)
    grafts.write_text(
        f"{fixture.artifact_commit} {fixture.seal_commit}\n",
        encoding="ascii",
    )

    history = load_verified_history(
        fixture.path,
        seal_path=SEAL_PATH,
        expected_seal_sha256=fixture.seal_sha256,
        suffix_path=SUFFIX_PATH,
    )

    assert len(history.draws) == 4442
    assert history.seal.artifact_commit == fixture.artifact_commit


def test_rejects_a_noncanonical_corrected_csv_even_when_resealed_in_git(tmp_path):
    base_raw = _git_bytes(ROOT, "show", f"{ARTIFACT_COMMIT}:{BASE_PATH}")
    noncanonical = base_raw.replace(b"1982-06-12,3,", b"1982-06-12,03,", 1)
    assert noncanonical != base_raw
    fixture = _sealed_repository(tmp_path, base_raw_override=noncanonical)

    with pytest.raises(ValueError, match="canonical CSV"):
        load_verified_history(
            fixture.path,
            seal_path=SEAL_PATH,
            expected_seal_sha256=fixture.seal_sha256,
            suffix_path=SUFFIX_PATH,
        )


def test_rejects_a_corrected_csv_with_a_missing_scheduled_draw(tmp_path):
    base_raw = _git_bytes(ROOT, "show", f"{ARTIFACT_COMMIT}:{BASE_PATH}")
    lines = base_raw.splitlines(keepends=True)
    incomplete = b"".join(line for line in lines if not line.startswith(b"2020-02-05,"))
    assert len(incomplete.splitlines()) + 1 == len(base_raw.splitlines())
    fixture = _sealed_repository(tmp_path, base_raw_override=incomplete)

    with pytest.raises(ValueError, match="exact schedule"):
        load_verified_history(
            fixture.path,
            seal_path=SEAL_PATH,
            expected_seal_sha256=fixture.seal_sha256,
            suffix_path=SUFFIX_PATH,
        )


def test_loads_one_suffix_draw_with_external_file_and_head_pins(tmp_path):
    fixture = _sealed_repository(tmp_path)
    draw = Draw(date(2026, 8, 19), (6, 7, 10, 32, 33, 36), 11)
    suffix = _install_suffix(fixture, (draw,))

    history = load_verified_history(
        fixture.path,
        seal_path=SEAL_PATH,
        expected_seal_sha256=fixture.seal_sha256,
        suffix_path=SUFFIX_PATH,
        expected_suffix_sha256=suffix.file_sha256,
        expected_suffix_head_sha256=suffix.head_event_sha256,
    )

    assert history.draws[-1] == draw
    assert len(history.draws) == 4443
    assert history.suffix.event_count == 1
    assert history.suffix.head_event_sha256 == suffix.head_event_sha256
    assert history.suffix.evidence_commits == (suffix.evidence_commit,)


def test_loads_two_contiguous_suffix_draws(tmp_path):
    fixture = _sealed_repository(tmp_path)
    first = Draw(date(2026, 8, 19), (6, 7, 10, 32, 33, 36), 11)
    second = Draw(date(2026, 8, 22), (11, 13, 21, 31, 34, 45), 5)
    suffix = _install_suffix(fixture, (first, second))

    history = load_verified_history(
        fixture.path,
        seal_path=SEAL_PATH,
        expected_seal_sha256=fixture.seal_sha256,
        suffix_path=SUFFIX_PATH,
        expected_suffix_sha256=suffix.file_sha256,
        expected_suffix_head_sha256=suffix.head_event_sha256,
    )

    assert history.draws[-2:] == (first, second)
    assert history.suffix.event_count == 2
    assert history.suffix.history_through == second.draw_date


@pytest.mark.parametrize("missing", ["file", "head"])
def test_nonempty_suffix_requires_both_external_pins(tmp_path, missing):
    fixture = _sealed_repository(tmp_path)
    draw = Draw(date(2026, 8, 19), (6, 7, 10, 32, 33, 36), 11)
    suffix = _install_suffix(fixture, (draw,))

    with pytest.raises(ValueError, match="requires external"):
        load_verified_history(
            fixture.path,
            seal_path=SEAL_PATH,
            expected_seal_sha256=fixture.seal_sha256,
            suffix_path=SUFFIX_PATH,
            expected_suffix_sha256=(None if missing == "file" else suffix.file_sha256),
            expected_suffix_head_sha256=(
                None if missing == "head" else suffix.head_event_sha256
            ),
        )


def test_external_suffix_file_pin_rejects_an_in_place_rewrite(tmp_path):
    fixture = _sealed_repository(tmp_path)
    draw = Draw(date(2026, 8, 19), (6, 7, 10, 32, 33, 36), 11)
    suffix = _install_suffix(fixture, (draw,))
    path = fixture.path / SUFFIX_PATH
    path.write_bytes(path.read_bytes().replace(b"2026-08-19", b"2026-08-18", 1))

    with pytest.raises(ValueError, match="external suffix SHA-256"):
        load_verified_history(
            fixture.path,
            seal_path=SEAL_PATH,
            expected_seal_sha256=fixture.seal_sha256,
            suffix_path=SUFFIX_PATH,
            expected_suffix_sha256=suffix.file_sha256,
            expected_suffix_head_sha256=suffix.head_event_sha256,
        )


def test_external_suffix_head_pin_rejects_a_complete_line_truncation(tmp_path):
    fixture = _sealed_repository(tmp_path)
    first = Draw(date(2026, 8, 19), (6, 7, 10, 32, 33, 36), 11)
    second = Draw(date(2026, 8, 22), (11, 13, 21, 31, 34, 45), 5)
    suffix = _install_suffix(fixture, (first, second))
    truncated = _canonical_json(suffix.events[0], newline=True)
    _write(fixture.path, SUFFIX_PATH, truncated)

    with pytest.raises(ValueError, match="external suffix head"):
        load_verified_history(
            fixture.path,
            seal_path=SEAL_PATH,
            expected_seal_sha256=fixture.seal_sha256,
            suffix_path=SUFFIX_PATH,
            expected_suffix_sha256=sha256(truncated).hexdigest(),
            expected_suffix_head_sha256=suffix.head_event_sha256,
        )


@pytest.mark.parametrize(
    "mutate",
    [
        lambda event: event.update(sequence=1),
        lambda event: event.update(previous_event_sha256="0" * 64),
        lambda event: event.update(base_seal_sha256="0" * 64),
    ],
)
def test_rejects_a_rehashed_suffix_with_a_broken_sequence_or_anchor(tmp_path, mutate):
    fixture = _sealed_repository(tmp_path)
    draw = Draw(date(2026, 8, 19), (6, 7, 10, 32, 33, 36), 11)
    suffix = _install_suffix(fixture, (draw,))
    event = deepcopy(suffix.events[0])
    mutate(event)
    event = _rehash_event(event)
    file_pin, head_pin = _write_suffix_events(fixture.path, (event,))

    with pytest.raises(ValueError, match="chain/schema"):
        load_verified_history(
            fixture.path,
            seal_path=SEAL_PATH,
            expected_seal_sha256=fixture.seal_sha256,
            suffix_path=SUFFIX_PATH,
            expected_suffix_sha256=file_pin,
            expected_suffix_head_sha256=head_pin,
        )


@pytest.mark.parametrize(
    "wrong_date",
    ["2026-08-15", "2026-08-18", "2026-08-22"],
)
def test_rejects_base_era_wrong_weekday_or_gapped_suffix_dates(tmp_path, wrong_date):
    fixture = _sealed_repository(tmp_path)
    draw = Draw(date(2026, 8, 19), (6, 7, 10, 32, 33, 36), 11)
    suffix = _install_suffix(fixture, (draw,))
    event = deepcopy(suffix.events[0])
    event["draw"]["draw_date"] = wrong_date
    event = _rehash_event(event)
    file_pin, head_pin = _write_suffix_events(fixture.path, (event,))

    with pytest.raises(ValueError, match="next scheduled date"):
        load_verified_history(
            fixture.path,
            seal_path=SEAL_PATH,
            expected_seal_sha256=fixture.seal_sha256,
            suffix_path=SUFFIX_PATH,
            expected_suffix_sha256=file_pin,
            expected_suffix_head_sha256=head_pin,
        )


@pytest.mark.parametrize("conflicting", [False, True])
def test_rejects_duplicate_or_conflicting_suffix_dates(tmp_path, conflicting):
    fixture = _sealed_repository(tmp_path)
    first = Draw(date(2026, 8, 19), (6, 7, 10, 32, 33, 36), 11)
    second = Draw(date(2026, 8, 22), (11, 13, 21, 31, 34, 45), 5)
    suffix = _install_suffix(fixture, (first, second))
    second_event = deepcopy(suffix.events[1])
    second_event["draw"] = _draw_payload(
        Draw(
            first.draw_date,
            second.numbers if conflicting else first.numbers,
            second.bonus if conflicting else first.bonus,
        )
    )
    second_event = _rehash_event(second_event)
    file_pin, head_pin = _write_suffix_events(
        fixture.path, (suffix.events[0], second_event)
    )

    with pytest.raises(ValueError, match="next scheduled date"):
        load_verified_history(
            fixture.path,
            seal_path=SEAL_PATH,
            expected_seal_sha256=fixture.seal_sha256,
            suffix_path=SUFFIX_PATH,
            expected_suffix_sha256=file_pin,
            expected_suffix_head_sha256=head_pin,
        )


def test_rejects_a_truncated_final_json_event(tmp_path):
    fixture = _sealed_repository(tmp_path)
    draw = Draw(date(2026, 8, 19), (6, 7, 10, 32, 33, 36), 11)
    suffix = _install_suffix(fixture, (draw,))
    path = fixture.path / SUFFIX_PATH
    truncated = path.read_bytes()[:-4]
    path.write_bytes(truncated)

    with pytest.raises(ValueError, match="truncated JSON"):
        load_verified_history(
            fixture.path,
            seal_path=SEAL_PATH,
            expected_seal_sha256=fixture.seal_sha256,
            suffix_path=SUFFIX_PATH,
            expected_suffix_sha256=sha256(truncated).hexdigest(),
            expected_suffix_head_sha256=suffix.head_event_sha256,
        )


def test_rejects_a_suffix_draw_with_only_one_source_authority(tmp_path):
    fixture = _sealed_repository(tmp_path)
    draw = Draw(date(2026, 8, 19), (6, 7, 10, 32, 33, 36), 11)
    suffix = _install_suffix(fixture, (draw,))
    event = deepcopy(suffix.events[0])
    event["source_receipts"] = event["source_receipts"][:1]
    event = _rehash_event(event)
    file_pin, head_pin = _write_suffix_events(fixture.path, (event,))

    with pytest.raises(ValueError, match="two independent"):
        load_verified_history(
            fixture.path,
            seal_path=SEAL_PATH,
            expected_seal_sha256=fixture.seal_sha256,
            suffix_path=SUFFIX_PATH,
            expected_suffix_sha256=file_pin,
            expected_suffix_head_sha256=head_pin,
        )


def test_rejects_noncanonical_source_receipt_order(tmp_path):
    fixture = _sealed_repository(tmp_path)
    draw = Draw(date(2026, 8, 19), (6, 7, 10, 32, 33, 36), 11)
    suffix = _install_suffix(fixture, (draw,))
    event = deepcopy(suffix.events[0])
    event["source_receipts"].reverse()
    event = _rehash_event(event)
    file_pin, head_pin = _write_suffix_events(fixture.path, (event,))

    with pytest.raises(ValueError, match="receipts are not canonical"):
        load_verified_history(
            fixture.path,
            seal_path=SEAL_PATH,
            expected_seal_sha256=fixture.seal_sha256,
            suffix_path=SUFFIX_PATH,
            expected_suffix_sha256=file_pin,
            expected_suffix_head_sha256=head_pin,
        )


@pytest.mark.parametrize(
    "mutate",
    [
        lambda receipt: receipt.update(provider="Self-reported WCLC"),
        lambda receipt: receipt.update(source_type="generic_html"),
        lambda receipt: receipt.update(url="https://example.com/results"),
        lambda receipt: receipt.update(
            evidence_path="evidence/live_sources/loto_quebec/../escaped.html"
        ),
    ],
)
def test_rejects_unfrozen_receipt_authority_or_path_metadata(tmp_path, mutate):
    fixture = _sealed_repository(tmp_path)
    draw = Draw(date(2026, 8, 19), (6, 7, 10, 32, 33, 36), 11)
    suffix = _install_suffix(fixture, (draw,))
    event = deepcopy(suffix.events[0])
    receipt = next(
        item
        for item in event["source_receipts"]
        if item["independence_group"] == "loto_quebec"
    )
    mutate(receipt)
    event = _rehash_event(event)
    file_pin, head_pin = _write_suffix_events(fixture.path, (event,))

    with pytest.raises(ValueError, match="receipt|evidence path"):
        load_verified_history(
            fixture.path,
            seal_path=SEAL_PATH,
            expected_seal_sha256=fixture.seal_sha256,
            suffix_path=SUFFIX_PATH,
            expected_suffix_sha256=file_pin,
            expected_suffix_head_sha256=head_pin,
        )


def test_rejects_a_loto_quebec_url_for_a_different_draw_date(tmp_path):
    fixture = _sealed_repository(tmp_path)
    draw = Draw(date(2026, 8, 19), (6, 7, 10, 32, 33, 36), 11)
    suffix = _install_suffix(fixture, (draw,))
    event = deepcopy(suffix.events[0])
    receipt = next(
        item
        for item in event["source_receipts"]
        if item["independence_group"] == "loto_quebec"
    )
    receipt["url"] = receipt["url"].replace("2026-08-19", "2026-08-22")
    event = _rehash_event(event)
    file_pin, head_pin = _write_suffix_events(fixture.path, (event,))

    with pytest.raises(ValueError, match="date query"):
        load_verified_history(
            fixture.path,
            seal_path=SEAL_PATH,
            expected_seal_sha256=fixture.seal_sha256,
            suffix_path=SUFFIX_PATH,
            expected_suffix_sha256=file_pin,
            expected_suffix_head_sha256=head_pin,
        )


def test_rejects_receipt_hash_metadata_that_disagrees_with_git(tmp_path):
    fixture = _sealed_repository(tmp_path)
    draw = Draw(date(2026, 8, 19), (6, 7, 10, 32, 33, 36), 11)
    suffix = _install_suffix(fixture, (draw,))
    event = deepcopy(suffix.events[0])
    event["source_receipts"][0]["sha256"] = "0" * 64
    event = _rehash_event(event)
    file_pin, head_pin = _write_suffix_events(fixture.path, (event,))

    with pytest.raises(ValueError, match="evidence asset"):
        load_verified_history(
            fixture.path,
            seal_path=SEAL_PATH,
            expected_seal_sha256=fixture.seal_sha256,
            suffix_path=SUFFIX_PATH,
            expected_suffix_sha256=file_pin,
            expected_suffix_head_sha256=head_pin,
        )


def test_rejects_git_verified_loto_quebec_bytes_for_a_different_row(tmp_path):
    fixture = _sealed_repository(tmp_path)
    draw = Draw(date(2026, 8, 19), (6, 7, 10, 32, 33, 36), 11)
    suffix = _install_suffix(fixture, (draw,))
    different = Draw(draw.draw_date, (1, 2, 3, 4, 5, 6), 7)
    event = _replace_receipt_asset(
        fixture,
        suffix.events[0],
        independence_group="loto_quebec",
        raw=_loto_quebec_html(different),
    )
    file_pin, head_pin = _write_suffix_events(fixture.path, (event,))

    with pytest.raises(ValueError, match="does not support"):
        load_verified_history(
            fixture.path,
            seal_path=SEAL_PATH,
            expected_seal_sha256=fixture.seal_sha256,
            suffix_path=SUFFIX_PATH,
            expected_suffix_sha256=file_pin,
            expected_suffix_head_sha256=head_pin,
        )


def test_rejects_a_second_wclc_target_date_with_an_invalid_classic_draw(tmp_path):
    fixture = _sealed_repository(tmp_path)
    draw = Draw(date(2026, 8, 19), (6, 7, 10, 32, 33, 36), 11)
    suffix = _install_suffix(fixture, (draw,))
    duplicate = (
        _wclc_html(draw)
        + b"<p>Wednesday, August 19, 2026 CLASSIC DRAW "
        + b"01 01 02 03 04 05 Bonus 06</p>"
    )
    event = _replace_receipt_asset(
        fixture,
        suffix.events[0],
        independence_group="wclc",
        raw=duplicate,
    )
    file_pin, head_pin = _write_suffix_events(fixture.path, (event,))

    with pytest.raises(ValueError, match="exactly one target"):
        load_verified_history(
            fixture.path,
            seal_path=SEAL_PATH,
            expected_seal_sha256=fixture.seal_sha256,
            suffix_path=SUFFIX_PATH,
            expected_suffix_sha256=file_pin,
            expected_suffix_head_sha256=head_pin,
        )


def test_rejects_two_classic_draw_blocks_under_one_wclc_target_date(tmp_path):
    fixture = _sealed_repository(tmp_path)
    draw = Draw(date(2026, 8, 19), (6, 7, 10, 32, 33, 36), 11)
    suffix = _install_suffix(fixture, (draw,))
    duplicate_block = _wclc_html(draw).replace(
        b"</body></html>",
        b" CLASSIC DRAW 01 02 03 04 05 06 Bonus 07</body></html>",
    )
    event = _replace_receipt_asset(
        fixture,
        suffix.events[0],
        independence_group="wclc",
        raw=duplicate_block,
    )
    file_pin, head_pin = _write_suffix_events(fixture.path, (event,))

    with pytest.raises(ValueError, match="exactly one target"):
        load_verified_history(
            fixture.path,
            seal_path=SEAL_PATH,
            expected_seal_sha256=fixture.seal_sha256,
            suffix_path=SUFFIX_PATH,
            expected_suffix_sha256=file_pin,
            expected_suffix_head_sha256=head_pin,
        )


def test_rejects_two_number_results_under_one_wclc_classic_draw(tmp_path):
    fixture = _sealed_repository(tmp_path)
    draw = Draw(date(2026, 8, 19), (6, 7, 10, 32, 33, 36), 11)
    suffix = _install_suffix(fixture, (draw,))
    duplicate_result = _wclc_html(draw).replace(
        b"</body></html>",
        b" 01 02 03 04 05 06 Bonus 07</body></html>",
    )
    event = _replace_receipt_asset(
        fixture,
        suffix.events[0],
        independence_group="wclc",
        raw=duplicate_result,
    )
    file_pin, head_pin = _write_suffix_events(fixture.path, (event,))

    with pytest.raises(ValueError, match="exactly one target"):
        load_verified_history(
            fixture.path,
            seal_path=SEAL_PATH,
            expected_seal_sha256=fixture.seal_sha256,
            suffix_path=SUFFIX_PATH,
            expected_suffix_sha256=file_pin,
            expected_suffix_head_sha256=head_pin,
        )


def test_rejects_a_result_from_a_later_block_after_malformed_classic_draw(tmp_path):
    fixture = _sealed_repository(tmp_path)
    draw = Draw(date(2026, 8, 19), (6, 7, 10, 32, 33, 36), 11)
    suffix = _install_suffix(fixture, (draw,))
    malformed = (
        b"<html><body>Wednesday, August 19, 2026 "
        b"CLASSIC DRAW MALFORMED GOLD BALL DRAW "
        b"06 07 10 32 33 36 Bonus 11</body></html>"
    )
    event = _replace_receipt_asset(
        fixture,
        suffix.events[0],
        independence_group="wclc",
        raw=malformed,
    )
    file_pin, head_pin = _write_suffix_events(fixture.path, (event,))

    with pytest.raises(ValueError, match="malformed"):
        load_verified_history(
            fixture.path,
            seal_path=SEAL_PATH,
            expected_seal_sha256=fixture.seal_sha256,
            suffix_path=SUFFIX_PATH,
            expected_suffix_sha256=file_pin,
            expected_suffix_head_sha256=head_pin,
        )


@pytest.mark.parametrize("suffix", [b"x", b".0"])
def test_rejects_a_noncanonical_wclc_bonus_token(tmp_path, suffix):
    fixture = _sealed_repository(tmp_path)
    draw = Draw(date(2026, 8, 19), (6, 7, 10, 32, 33, 36), 11)
    suffix_artifact = _install_suffix(fixture, (draw,))
    malformed = _wclc_html(draw).replace(b"Bonus 11", b"Bonus 11" + suffix)
    event = _replace_receipt_asset(
        fixture,
        suffix_artifact.events[0],
        independence_group="wclc",
        raw=malformed,
    )
    file_pin, head_pin = _write_suffix_events(fixture.path, (event,))

    with pytest.raises(ValueError, match="malformed"):
        load_verified_history(
            fixture.path,
            seal_path=SEAL_PATH,
            expected_seal_sha256=fixture.seal_sha256,
            suffix_path=SUFFIX_PATH,
            expected_suffix_sha256=file_pin,
            expected_suffix_head_sha256=head_pin,
        )


def test_rejects_a_second_malformed_wclc_occurrence_for_the_target_date(tmp_path):
    fixture = _sealed_repository(tmp_path)
    draw = Draw(date(2026, 8, 19), (6, 7, 10, 32, 33, 36), 11)
    suffix = _install_suffix(fixture, (draw,))
    target = draw.draw_date.strftime("%A, %B %d, %Y").encode()
    duplicate = _wclc_html(draw).replace(
        b"</body></html>",
        b"<p>" + target + b" malformed duplicate result</p></body></html>",
    )
    event = _replace_receipt_asset(
        fixture,
        suffix.events[0],
        independence_group="wclc",
        raw=duplicate,
    )
    file_pin, head_pin = _write_suffix_events(fixture.path, (event,))

    with pytest.raises(ValueError, match="exactly one target"):
        load_verified_history(
            fixture.path,
            seal_path=SEAL_PATH,
            expected_seal_sha256=fixture.seal_sha256,
            suffix_path=SUFFIX_PATH,
            expected_suffix_sha256=file_pin,
            expected_suffix_head_sha256=head_pin,
        )


@pytest.mark.parametrize(
    "malformed_target",
    [
        b"Wednesday, August 19, 20260",
        b"XWednesday, August 19, 2026Y",
    ],
)
def test_rejects_a_wclc_target_date_embedded_in_a_larger_token(
    tmp_path, malformed_target
):
    fixture = _sealed_repository(tmp_path)
    draw = Draw(date(2026, 8, 19), (6, 7, 10, 32, 33, 36), 11)
    suffix = _install_suffix(fixture, (draw,))
    raw = _wclc_html(draw).replace(b"Wednesday, August 19, 2026", malformed_target)
    event = _replace_receipt_asset(
        fixture,
        suffix.events[0],
        independence_group="wclc",
        raw=raw,
    )
    file_pin, head_pin = _write_suffix_events(fixture.path, (event,))

    with pytest.raises(ValueError, match="exactly one target"):
        load_verified_history(
            fixture.path,
            seal_path=SEAL_PATH,
            expected_seal_sha256=fixture.seal_sha256,
            suffix_path=SUFFIX_PATH,
            expected_suffix_sha256=file_pin,
            expected_suffix_head_sha256=head_pin,
        )


@pytest.mark.parametrize(
    "retrieved_at",
    [
        "2026-08-23T08:00:00-04:00",
        "2026-08-18T23:59:59Z",
        "2026-08-19T23:59:59Z",
    ],
)
def test_rejects_non_utc_or_predraw_receipt_timestamps(tmp_path, retrieved_at):
    fixture = _sealed_repository(tmp_path)
    draw = Draw(date(2026, 8, 19), (6, 7, 10, 32, 33, 36), 11)
    suffix = _install_suffix(fixture, (draw,))
    event = deepcopy(suffix.events[0])
    event["source_receipts"][0]["retrieved_at"] = retrieved_at
    event = _rehash_event(event)
    file_pin, head_pin = _write_suffix_events(fixture.path, (event,))

    with pytest.raises(ValueError, match="timestamp"):
        load_verified_history(
            fixture.path,
            seal_path=SEAL_PATH,
            expected_seal_sha256=fixture.seal_sha256,
            suffix_path=SUFFIX_PATH,
            expected_suffix_sha256=file_pin,
            expected_suffix_head_sha256=head_pin,
        )


def test_rejects_a_receipt_timestamp_after_its_evidence_commit(tmp_path):
    fixture = _sealed_repository(tmp_path)
    draw = Draw(date(2026, 8, 19), (6, 7, 10, 32, 33, 36), 11)
    suffix = _install_suffix(fixture, (draw,))
    event = deepcopy(suffix.events[0])
    event["source_receipts"][0]["retrieved_at"] = "2026-08-23T12:05:01Z"
    event = _rehash_event(event)
    file_pin, head_pin = _write_suffix_events(fixture.path, (event,))

    with pytest.raises(ValueError, match="timestamp"):
        load_verified_history(
            fixture.path,
            seal_path=SEAL_PATH,
            expected_seal_sha256=fixture.seal_sha256,
            suffix_path=SUFFIX_PATH,
            expected_suffix_sha256=file_pin,
            expected_suffix_head_sha256=head_pin,
        )


def test_rejects_an_evidence_commit_that_only_inherits_the_receipt_assets(tmp_path):
    fixture = _sealed_repository(tmp_path)
    draw = Draw(date(2026, 8, 19), (6, 7, 10, 32, 33, 36), 11)
    suffix = _install_suffix(fixture, (draw,))
    _write(fixture.path, "unrelated.txt", b"unrelated later commit\n")
    _git_text(fixture.path, "add", "unrelated.txt")
    _git_commit(fixture.path, "unrelated evidence commit", "2026-08-23T12:06:00Z")
    event = deepcopy(suffix.events[0])
    event["evidence_commit"] = _git_text(fixture.path, "rev-parse", "HEAD")
    event = _rehash_event(event)
    file_pin, head_pin = _write_suffix_events(fixture.path, (event,))

    with pytest.raises(ValueError, match="evidence commit"):
        load_verified_history(
            fixture.path,
            seal_path=SEAL_PATH,
            expected_seal_sha256=fixture.seal_sha256,
            suffix_path=SUFFIX_PATH,
            expected_suffix_sha256=file_pin,
            expected_suffix_head_sha256=head_pin,
        )


def test_rejects_identical_raw_bytes_claimed_as_two_independent_sources(tmp_path):
    fixture = _sealed_repository(tmp_path)
    draw = Draw(date(2026, 8, 19), (6, 7, 10, 32, 33, 36), 11)
    suffix = _install_suffix(fixture, (draw,))
    polyglot = _wclc_html(draw) + _loto_quebec_html(draw)
    event = _replace_receipt_assets(
        fixture,
        suffix.events[0],
        raw_by_group={"wclc": polyglot, "loto_quebec": polyglot},
    )
    file_pin, head_pin = _write_suffix_events(fixture.path, (event,))

    with pytest.raises(ValueError, match="independent"):
        load_verified_history(
            fixture.path,
            seal_path=SEAL_PATH,
            expected_seal_sha256=fixture.seal_sha256,
            suffix_path=SUFFIX_PATH,
            expected_suffix_sha256=file_pin,
            expected_suffix_head_sha256=head_pin,
        )


def test_git_bound_base_ignores_a_worktree_csv_rewrite(tmp_path):
    fixture = _sealed_repository(tmp_path)
    _write(fixture.path, BASE_PATH, b"attacker-controlled worktree bytes\n")

    history = load_verified_history(
        fixture.path,
        seal_path=SEAL_PATH,
        expected_seal_sha256=fixture.seal_sha256,
        suffix_path=SUFFIX_PATH,
    )

    assert len(history.draws) == 4442
    assert history.base.file_sha256 == BASE_FILE_SHA256


def test_sealed_history_verifies_after_a_git_clone_relocation(tmp_path):
    fixture = _sealed_repository(tmp_path)
    clone = tmp_path / "relocated repository"
    _git_text(tmp_path, "clone", "-q", str(fixture.path), str(clone))

    history = load_verified_history(
        clone,
        seal_path=SEAL_PATH,
        expected_seal_sha256=fixture.seal_sha256,
        suffix_path=SUFFIX_PATH,
    )

    assert history.seal.artifact_commit == fixture.artifact_commit
    assert history.base.git_blob == fixture.seal["corrected_epoch"]["git_blob"]


def test_rejects_the_wrong_external_seal_file_pin(tmp_path):
    fixture = _sealed_repository(tmp_path)

    with pytest.raises(ValueError, match="external seal SHA-256"):
        load_verified_history(
            fixture.path,
            seal_path=SEAL_PATH,
            expected_seal_sha256="0" * 64,
            suffix_path=SUFFIX_PATH,
        )


def test_rejects_an_empty_suffix_at_a_nonfrozen_path(tmp_path):
    fixture = _sealed_repository(tmp_path)
    wrong_path = "data/processed/epochs/unsealed/live_draws.jsonl"
    _write(fixture.path, wrong_path, b"")

    with pytest.raises(ValueError, match="suffix path"):
        load_verified_history(
            fixture.path,
            seal_path=SEAL_PATH,
            expected_seal_sha256=fixture.seal_sha256,
            suffix_path=wrong_path,
        )


def test_rejects_an_event_body_rewrite_without_a_matching_event_hash(tmp_path):
    fixture = _sealed_repository(tmp_path)
    draw = Draw(date(2026, 8, 19), (6, 7, 10, 32, 33, 36), 11)
    suffix = _install_suffix(fixture, (draw,))
    event = deepcopy(suffix.events[0])
    event["draw"]["bonus"] = 12
    file_pin, head_pin = _write_suffix_events(fixture.path, (event,))

    with pytest.raises(ValueError, match="event SHA-256"):
        load_verified_history(
            fixture.path,
            seal_path=SEAL_PATH,
            expected_seal_sha256=fixture.seal_sha256,
            suffix_path=SUFFIX_PATH,
            expected_suffix_sha256=file_pin,
            expected_suffix_head_sha256=head_pin,
        )


def test_rejects_nonfinite_json_in_a_suffix_draw(tmp_path):
    fixture = _sealed_repository(tmp_path)
    draw = Draw(date(2026, 8, 19), (6, 7, 10, 32, 33, 36), 11)
    suffix = _install_suffix(fixture, (draw,))
    raw = (
        (fixture.path / SUFFIX_PATH)
        .read_bytes()
        .replace(b'"numbers":[6,7,', b'"numbers":[NaN,7,', 1)
    )
    assert b"NaN" in raw
    _write(fixture.path, SUFFIX_PATH, raw)

    with pytest.raises(ValueError, match="canonical"):
        load_verified_history(
            fixture.path,
            seal_path=SEAL_PATH,
            expected_seal_sha256=fixture.seal_sha256,
            suffix_path=SUFFIX_PATH,
            expected_suffix_sha256=sha256(raw).hexdigest(),
            expected_suffix_head_sha256=suffix.head_event_sha256,
        )


def test_rejects_a_receipt_supported_row_hash_for_another_draw(tmp_path):
    fixture = _sealed_repository(tmp_path)
    draw = Draw(date(2026, 8, 19), (6, 7, 10, 32, 33, 36), 11)
    suffix = _install_suffix(fixture, (draw,))
    event = deepcopy(suffix.events[0])
    event["source_receipts"][0]["supported_row_sha256"] = "0" * 64
    event = _rehash_event(event)
    file_pin, head_pin = _write_suffix_events(fixture.path, (event,))

    with pytest.raises(ValueError, match="receipt identity"):
        load_verified_history(
            fixture.path,
            seal_path=SEAL_PATH,
            expected_seal_sha256=fixture.seal_sha256,
            suffix_path=SUFFIX_PATH,
            expected_suffix_sha256=file_pin,
            expected_suffix_head_sha256=head_pin,
        )


def test_reviewed_adjudication_receipts_fail_closed_in_suffix_v1(tmp_path):
    fixture = _sealed_repository(tmp_path)
    draw = Draw(date(2026, 8, 19), (6, 7, 10, 32, 33, 36), 11)
    suffix = _install_suffix(fixture, (draw,))
    event = deepcopy(suffix.events[0])
    event["source_receipts"][0]["independence_group"] = "reviewed_adjudication"
    event = _rehash_event(event)
    file_pin, head_pin = _write_suffix_events(fixture.path, (event,))

    with pytest.raises(ValueError, match="authority is not allowed"):
        load_verified_history(
            fixture.path,
            seal_path=SEAL_PATH,
            expected_seal_sha256=fixture.seal_sha256,
            suffix_path=SUFFIX_PATH,
            expected_suffix_sha256=file_pin,
            expected_suffix_head_sha256=head_pin,
        )


def test_git_bound_receipts_ignore_worktree_evidence_rewrites(tmp_path):
    fixture = _sealed_repository(tmp_path)
    draw = Draw(date(2026, 8, 19), (6, 7, 10, 32, 33, 36), 11)
    suffix = _install_suffix(fixture, (draw,))
    receipt_path = suffix.events[0]["source_receipts"][0]["evidence_path"]
    _write(fixture.path, receipt_path, b"attacker-controlled worktree evidence\n")

    history = load_verified_history(
        fixture.path,
        seal_path=SEAL_PATH,
        expected_seal_sha256=fixture.seal_sha256,
        suffix_path=SUFFIX_PATH,
        expected_suffix_sha256=suffix.file_sha256,
        expected_suffix_head_sha256=suffix.head_event_sha256,
    )

    assert history.draws[-1] == draw


def test_deployed_epoch_and_two_source_suffix_load_from_external_pins():
    history = load_verified_history(
        ROOT,
        seal_path=SEAL_PATH,
        expected_seal_sha256=DEPLOYED_SEAL_SHA256,
        suffix_path=SUFFIX_PATH,
        expected_suffix_sha256=DEPLOYED_SUFFIX_SHA256,
        expected_suffix_head_sha256=DEPLOYED_SUFFIX_HEAD_SHA256,
    )

    assert len(history.draws) == 4_444
    assert history.draws[-2] == Draw(date(2026, 8, 19), (6, 7, 10, 32, 33, 36), 11)
    assert history.draws[-1] == Draw(date(2026, 8, 22), (11, 13, 21, 31, 34, 45), 5)
    assert history.suffix.event_count == 2
    assert history.suffix.file_sha256 == DEPLOYED_SUFFIX_SHA256
    assert history.suffix.head_event_sha256 == DEPLOYED_SUFFIX_HEAD_SHA256
    assert history.suffix.evidence_commits == (DEPLOYED_EVIDENCE_COMMIT,) * 2
