from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Mapping
from zoneinfo import ZoneInfo

from .operational_history import PublishedHistory, load_published_history


_EXPECTED_REPOSITORY = "Jasper-Shi/lottopred"
_EXPECTED_REF = "refs/heads/main"
_EXPECTED_EVENT = "schedule"
_EXPECTED_WORKFLOW_REF = (
    "Jasper-Shi/lottopred/.github/workflows/research-progress-email.yml@refs/heads/main"
)
_EXPECTED_JOB = "progress-email"
_SHA1_RE = re.compile(r"[0-9a-f]{40}")
_RUN_ID_RE = re.compile(r"[1-9][0-9]{0,19}")
_MODEL_RE = re.compile(r"[a-z0-9_]{1,64}")
_VERSION_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,31}")
_ARTIFACT_RE = re.compile(
    r"(?P<date>[0-9]{4}-[0-9]{2}-[0-9]{2})"
    r"__(?P<model>[a-z0-9_]{1,64})"
    r"__(?P<version>[A-Za-z0-9][A-Za-z0-9._-]{0,31})\.json"
)
_MAX_GIT_OUTPUT = 1_000_000
_MAX_JSON_BYTES = 256_000
_MAX_CONFIG_BYTES = 128_000
_MAX_ARTIFACTS = 1_000
_MAX_SUBJECT_CHARS = 180
_MAX_BODY_CHARS = 16_000
_UNREVIEWED_EMAIL_OVERRIDES = ("SMTP_HOST", "SMTP_PORT", "EMAIL_FROM", "EMAIL_TO")
_TORONTO = ZoneInfo("America/Toronto")
_INHERITED_GIT_ENVIRONMENT = {
    "HOME",
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
    "PATH",
    "SYSTEMROOT",
    "TEMP",
    "TMP",
    "TMPDIR",
}


class ProgressEmailError(RuntimeError):
    """The committed snapshot or fixed Actions context is not safe to report."""


@dataclass(frozen=True)
class ResearchProgressReport:
    subject: str
    body: str
    facts_digest: str


@dataclass(frozen=True)
class _RunContext:
    repository: str
    event_name: str
    ref: str
    sha: str
    run_id: str
    run_number: str
    run_attempt: str
    workflow_ref: str
    workflow_sha: str
    job: str


def _fail(message: str) -> ProgressEmailError:
    return ProgressEmailError(message)


def _require_string(value: object, *, name: str, maximum: int = 256) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise _fail(f"{name} must be a non-empty bounded string")
    if any(ord(character) < 32 for character in value):
        raise _fail(f"{name} contains control characters")
    return value


def _parse_run_context(environment: Mapping[str, str]) -> _RunContext:
    required = {
        "GITHUB_ACTIONS": "true",
        "GITHUB_REPOSITORY": _EXPECTED_REPOSITORY,
        "GITHUB_EVENT_NAME": _EXPECTED_EVENT,
        "GITHUB_REF": _EXPECTED_REF,
        "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_WORKFLOW_REF": _EXPECTED_WORKFLOW_REF,
        "GITHUB_JOB": _EXPECTED_JOB,
    }
    for name, expected in required.items():
        observed = environment.get(name)
        if observed != expected:
            raise _fail(f"{name} is not the authorized fixed value")

    sha = environment.get("GITHUB_SHA", "")
    workflow_sha = environment.get("GITHUB_WORKFLOW_SHA", "")
    run_id = environment.get("GITHUB_RUN_ID", "")
    run_number = environment.get("GITHUB_RUN_NUMBER", "")
    if _SHA1_RE.fullmatch(sha) is None:
        raise _fail("GITHUB_SHA is not a canonical SHA-1")
    if workflow_sha != sha:
        raise _fail("GITHUB_WORKFLOW_SHA does not equal GITHUB_SHA")
    if _RUN_ID_RE.fullmatch(run_id) is None:
        raise _fail("GITHUB_RUN_ID is not a canonical positive decimal id")
    if _RUN_ID_RE.fullmatch(run_number) is None:
        raise _fail("GITHUB_RUN_NUMBER is not a canonical positive decimal id")
    return _RunContext(
        repository=_EXPECTED_REPOSITORY,
        event_name=_EXPECTED_EVENT,
        ref=_EXPECTED_REF,
        sha=sha,
        run_id=run_id,
        run_number=run_number,
        run_attempt="1",
        workflow_ref=_EXPECTED_WORKFLOW_REF,
        workflow_sha=workflow_sha,
        job=_EXPECTED_JOB,
    )


def _git(root: Path, arguments: list[str], *, maximum: int = _MAX_GIT_OUTPUT) -> bytes:
    environment = {
        key: value
        for key, value in os.environ.items()
        if key in _INHERITED_GIT_ENVIRONMENT
    }
    environment.update(
        {
            "GIT_CONFIG_COUNT": "0",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_SYSTEM": os.devnull,
            "GIT_GRAFT_FILE": os.devnull,
            "GIT_NO_LAZY_FETCH": "1",
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_OPTIONAL_LOCKS": "0",
        }
    )
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), *arguments],
            check=False,
            capture_output=True,
            env=environment,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        raise _fail("committed Git evidence is unavailable") from exc
    if completed.returncode != 0:
        raise _fail("committed Git evidence could not be read cleanly")
    if len(completed.stdout) > maximum:
        raise _fail("committed Git evidence exceeds its size limit")
    return completed.stdout


def _head(root: Path) -> str:
    output = _git(root, ["rev-parse", "--verify", "HEAD^{commit}"], maximum=64)
    try:
        value = output.decode("ascii").strip()
    except UnicodeDecodeError as exc:
        raise _fail("checkout HEAD is not ASCII") from exc
    if _SHA1_RE.fullmatch(value) is None:
        raise _fail("checkout HEAD is not a canonical SHA-1")
    return value


def _require_full_history(root: Path) -> None:
    output = _git(
        root,
        ["rev-parse", "--is-shallow-repository"],
        maximum=16,
    )
    try:
        value = output.decode("ascii").strip()
    except UnicodeDecodeError as exc:
        raise _fail("full-history checkout status is not ASCII") from exc
    if value != "false":
        raise _fail("a full-history checkout is required")


def _committed_blob(root: Path, path: str, *, maximum: int = _MAX_JSON_BYTES) -> bytes:
    if not path or path.startswith("/") or ".." in Path(path).parts or "\x00" in path:
        raise _fail("committed evidence path is not canonical")
    return _git(root, ["show", f"HEAD:{path}"], maximum=maximum)


def _committed_paths(root: Path, prefix: str) -> tuple[str, ...]:
    output = _git(
        root,
        ["ls-tree", "-r", "-z", "--name-only", "HEAD", "--", prefix],
        maximum=_MAX_GIT_OUTPUT,
    )
    raw_paths = output.split(b"\x00")
    if raw_paths and raw_paths[-1] == b"":
        raw_paths.pop()
    if len(raw_paths) > _MAX_ARTIFACTS:
        raise _fail("committed artifact count exceeds its limit")
    paths: list[str] = []
    for raw_path in raw_paths:
        try:
            path = raw_path.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise _fail("committed evidence path is not UTF-8") from exc
        if not path.startswith(f"{prefix.rstrip('/')}/"):
            raise _fail("committed evidence escaped its expected directory")
        paths.append(path)
    return tuple(paths)


def _object_without_duplicate_keys(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _fail("committed JSON contains a duplicate key")
        result[key] = value
    return result


def _parse_json(raw: bytes, *, name: str) -> dict[str, object]:
    if not raw or len(raw) > _MAX_JSON_BYTES or b"\x00" in raw:
        raise _fail(f"{name} is empty, binary, or oversized")
    try:
        payload = json.loads(raw, object_pairs_hook=_object_without_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _fail(f"{name} is not strict UTF-8 JSON") from exc
    if not isinstance(payload, dict):
        raise _fail(f"{name} must contain a JSON object")
    return payload


def _json_blob(root: Path, path: str) -> dict[str, object]:
    return _parse_json(_committed_blob(root, path), name=path)


def _mapping(value: object, *, name: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise _fail(f"{name} must be an object")
    return value


def _boolean(value: object, *, name: str) -> bool:
    if type(value) is not bool:
        raise _fail(f"{name} must be a boolean")
    return value


def _integer(value: object, *, name: str, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise _fail(f"{name} must be an integer in range")
    return value


def _number_sequence(value: object, *, name: str, size: int) -> tuple[int, ...]:
    if not isinstance(value, list) or len(value) != size:
        raise _fail(f"{name} must contain exactly {size} numbers")
    numbers = tuple(value)
    if (
        any(type(number) is not int or not 1 <= number <= 49 for number in numbers)
        or len(set(numbers)) != size
    ):
        raise _fail(f"{name} is not a canonical LOTTO 6/49 number sequence")
    return numbers


def _iso_date(value: object, *, name: str) -> str:
    text = _require_string(value, name=name, maximum=10)
    try:
        parsed = date.fromisoformat(text)
    except ValueError as exc:
        raise _fail(f"{name} is not an ISO date") from exc
    if parsed.isoformat() != text:
        raise _fail(f"{name} is not a canonical ISO date")
    return text


def _iso_datetime(value: object, *, name: str) -> str:
    text = _require_string(value, name=name, maximum=40)
    candidate = f"{text[:-1]}+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise _fail(f"{name} is not an ISO timestamp") from exc
    if parsed.tzinfo is None:
        raise _fail(f"{name} must include a timezone")
    if parsed.isoformat() != candidate:
        raise _fail(f"{name} is not a canonical ISO timestamp")
    return text


def _parsed_iso_datetime(value: object, *, name: str) -> datetime:
    text = _iso_datetime(value, name=name)
    candidate = f"{text[:-1]}+00:00" if text.endswith("Z") else text
    return datetime.fromisoformat(candidate)


def _report_instant(value: datetime | None) -> tuple[datetime, str]:
    instant = datetime.now(UTC).replace(microsecond=0) if value is None else value
    if (
        type(instant) is not datetime
        or instant.tzinfo is None
        or instant.utcoffset() != timedelta(0)
        or instant.microsecond != 0
    ):
        raise _fail("generated_at must be a whole-second UTC datetime")
    canonical = instant.isoformat().replace("+00:00", "Z")
    return instant, canonical


def _parse_config(raw: bytes) -> dict[str, object]:
    if not raw or len(raw) > _MAX_CONFIG_BYTES or b"\x00" in raw:
        raise _fail("config.yaml is empty, binary, or oversized")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise _fail("config.yaml is not UTF-8") from exc
    if "\t" in text or "\r" in text:
        raise _fail("config.yaml contains non-canonical whitespace")

    wanted = {
        ("project", "model_version"),
        ("data", "refresh_enabled"),
        ("backtest", "enabled"),
        ("live", "enabled"),
        ("live", "models"),
        ("live", "shadow_models"),
    }
    observed: dict[tuple[str, str], str] = {}
    section = ""
    for raw_line in text.splitlines():
        if not raw_line or raw_line.lstrip().startswith("#"):
            continue
        top = re.fullmatch(r"([a-z_]+):", raw_line)
        if top:
            section = top.group(1)
            continue
        item = re.fullmatch(r"  ([a-z_]+):(?: )(.+)", raw_line)
        if not item:
            continue
        key = (section, item.group(1))
        if key not in wanted:
            continue
        if key in observed:
            raise _fail(f"config.yaml duplicates {section}.{item.group(1)}")
        observed[key] = item.group(2)
    missing = wanted - set(observed)
    if missing:
        raise _fail("config.yaml omits required progress facts")

    def parse_bool(section_name: str, key_name: str) -> bool:
        value = observed[(section_name, key_name)]
        if value not in {"true", "false"}:
            raise _fail(f"config {section_name}.{key_name} is not a literal boolean")
        return value == "true"

    def parse_models(key_name: str) -> tuple[str, ...]:
        value = observed[("live", key_name)]
        if not value.startswith("[") or not value.endswith("]"):
            raise _fail(f"config live.{key_name} is not a canonical inline list")
        items = tuple(part.strip() for part in value[1:-1].split(",") if part.strip())
        if not items or len(items) > 32 or len(set(items)) != len(items):
            raise _fail(f"config live.{key_name} has an invalid model set")
        if any(_MODEL_RE.fullmatch(item) is None for item in items):
            raise _fail(f"config live.{key_name} contains an invalid model name")
        return items

    version = observed[("project", "model_version")]
    if _VERSION_RE.fullmatch(version) is None:
        raise _fail("config project.model_version is not canonical")
    models = parse_models("models")
    shadow_models = parse_models("shadow_models")
    if not set(shadow_models) < set(models):
        raise _fail("shadow models must be a proper subset of live models")
    return {
        "model_version": version,
        "refresh_enabled": parse_bool("data", "refresh_enabled"),
        "backtest_enabled": parse_bool("backtest", "enabled"),
        "live_enabled": parse_bool("live", "enabled"),
        "models": models,
        "shadow_models": shadow_models,
    }


def _single_matching_path(
    paths: tuple[str, ...], pattern: re.Pattern[str], *, name: str
) -> str:
    matches = sorted(path for path in paths if pattern.fullmatch(path))
    if not matches:
        raise _fail(f"no committed {name} evidence exists")
    return matches[-1]


def _release_facts(root: Path) -> dict[str, object]:
    paths = _committed_paths(root, "evidence/release_canaries")
    protection_path = _single_matching_path(
        paths,
        re.compile(
            r"evidence/release_canaries/[0-9]{4}-[0-9]{2}-[0-9]{2}"
            r"-production-main-protection\.json"
        ),
        name="main-protection",
    )
    publication_path = _single_matching_path(
        paths,
        re.compile(
            r"evidence/release_canaries/[0-9]{4}-[0-9]{2}-[0-9]{2}"
            r"-github-publication-canary\.json"
        ),
        name="publication-canary",
    )
    plan_path = _single_matching_path(
        paths,
        re.compile(
            r"evidence/release_canaries/[0-9]{4}-[0-9]{2}-[0-9]{2}"
            r"-production-live-canary-plan\.json"
        ),
        name="production-live-canary plan",
    )

    protection = _json_blob(root, protection_path)
    if protection.get("repository") != _EXPECTED_REPOSITORY:
        raise _fail("main-protection evidence names the wrong repository")
    protection_settings = _mapping(
        protection.get("protection"), name="main-protection.protection"
    )
    protection_verified_at = _iso_datetime(
        protection.get("verified_at"), name="main-protection.verified_at"
    )
    protection_facts = {
        "path": protection_path,
        "verified_at": protection_verified_at,
        "enforce_admins": _boolean(
            protection_settings.get("enforce_admins"),
            name="main-protection.enforce_admins",
        ),
        "allow_force_pushes": _boolean(
            protection_settings.get("allow_force_pushes"),
            name="main-protection.allow_force_pushes",
        ),
        "allow_deletions": _boolean(
            protection_settings.get("allow_deletions"),
            name="main-protection.allow_deletions",
        ),
    }

    publication = _json_blob(root, publication_path)
    publication_created_at = _iso_datetime(
        publication.get("created_at"), name="publication-canary.created_at"
    )
    publication_checks = {
        key: _boolean(publication.get(key), name=f"publication-canary.{key}")
        for key in (
            "delete_rejected",
            "exact_blob_tree_commit_oids",
            "force_update_rejected",
            "stale_update_refs_rejected",
            "successful_update_refs",
        )
    }
    fresh_fetch = publication.get("fresh_anonymous_full_fetch")
    if not isinstance(fresh_fetch, str) or _SHA1_RE.fullmatch(fresh_fetch) is None:
        raise _fail("publication-canary fresh fetch is not a canonical SHA-1")
    publication_facts = {
        "path": publication_path,
        "created_at": publication_created_at,
        "passed": all(publication_checks.values()),
        **publication_checks,
    }

    plan = _json_blob(root, plan_path)
    credential = _mapping(plan.get("credential"), name="live-canary-plan.credential")
    execution = _mapping(plan.get("execution"), name="live-canary-plan.execution")
    source_gate = _mapping(
        execution.get("official_source_gate"), name="live-canary-plan.source_gate"
    )
    stage2 = _mapping(plan.get("stage2"), name="live-canary-plan.stage2")
    legacy_cohort = _mapping(
        plan.get("legacy_due_prediction_cohort"),
        name="live-canary-plan.legacy_due_prediction_cohort",
    )
    plan_status = _require_string(
        plan.get("status"), name="live-canary-plan.status", maximum=80
    )
    authorities = source_gate.get("authorities")
    if not isinstance(authorities, list) or authorities != ["loto_quebec", "wclc"]:
        raise _fail("live-canary source authorities are not the approved pair")
    plan_facts = {
        "path": plan_path,
        "status": plan_status,
        "credential_installed_at_registration": _boolean(
            credential.get("installed"), name="live-canary-plan.credential.installed"
        ),
        "not_before": _iso_datetime(
            execution.get("not_before"), name="live-canary-plan.not_before"
        ),
        "source_draw_date": _iso_date(
            source_gate.get("draw_date"), name="live-canary-plan.source_draw_date"
        ),
        "source_requirement": _require_string(
            source_gate.get("requirement"),
            name="live-canary-plan.source_requirement",
            maximum=100,
        ),
        "stage1_unattended_schedule": _boolean(
            stage2.get("unattended_schedule_in_stage_1"),
            name="live-canary-plan.stage1_schedule",
        ),
        "legacy_classification": _require_string(
            legacy_cohort.get("classification"),
            name="live-canary-plan.legacy_classification",
            maximum=80,
        ),
        "legacy_target_draw": _iso_date(
            legacy_cohort.get("target_draw"),
            name="live-canary-plan.legacy_target_draw",
        ),
    }
    if plan_facts["stage1_unattended_schedule"] is not False:
        raise _fail("Stage-1 unattended live schedule must remain disabled")
    if plan_facts["legacy_classification"] != "descriptive_only_nonpromotion":
        raise _fail("legacy cohort classification is not the reviewed value")
    return {
        "protection": protection_facts,
        "publication_canary": publication_facts,
        "live_canary_plan": plan_facts,
    }


def _history_facts(
    root: Path, revision: str
) -> tuple[dict[str, object], PublishedHistory]:
    try:
        history = load_published_history(root, revision)
    except (OSError, ValueError) as exc:
        raise _fail("production published-history validation failed") from exc
    if type(history) is not PublishedHistory or not history.draws:
        raise _fail("production history loader did not return PublishedHistory")
    draw_dates = tuple(draw.draw_date for draw in history.draws)
    if any(
        previous >= current for previous, current in zip(draw_dates, draw_dates[1:])
    ):
        raise _fail("published history chronology is not strictly increasing")
    history_through = draw_dates[-1]
    if history.suffix.history_through != history_through:
        raise _fail("published history suffix and draw chronology disagree")
    if history.registry.resolved_revision != revision:
        raise _fail("published history was not loaded from the source revision")
    return (
        {
            "epoch": history.epoch,
            "registry_path": history.registry.registry_path,
            "registry_sha256": history.registry.file_sha256,
            "seal_sha256": history.seal.file_sha256,
            "suffix_sha256": history.suffix.file_sha256,
            "observed_revision": history.registry.resolved_revision,
            "draw_count": len(history.draws),
            "history_through": history_through.isoformat(),
        },
        history,
    )


def _artifact_payloads(root: Path, directory: str) -> list[dict[str, object]]:
    paths = _committed_paths(root, directory)
    payloads: list[dict[str, object]] = []
    for path in paths:
        basename = path.rsplit("/", 1)[-1]
        match = _ARTIFACT_RE.fullmatch(basename)
        if match is None:
            if basename == ".gitkeep":
                continue
            raise _fail(f"{directory} contains a non-canonical artifact name")
        payload = _json_blob(root, path)
        target_date = _iso_date(
            payload.get("target_draw_date"), name=f"{path}.target_draw_date"
        )
        model = _require_string(payload.get("model_name"), name=f"{path}.model_name")
        version = _require_string(
            payload.get("model_version"), name=f"{path}.model_version"
        )
        if (
            target_date != match.group("date")
            or model != match.group("model")
            or version != match.group("version")
        ):
            raise _fail(f"{path} filename and payload disagree")
        payloads.append({"path": path, **payload})
    if not payloads:
        raise _fail(f"no committed {directory} artifacts exist")
    return payloads


def _prediction_and_evaluation_facts(
    root: Path,
    config: dict[str, object],
    *,
    published_history: PublishedHistory,
    legacy_classification: str,
    legacy_target_draw: str,
) -> dict[str, object]:
    predictions = _artifact_payloads(root, "predictions")
    evaluations = _artifact_payloads(root, "evaluations")
    latest_prediction_date = max(
        str(payload["target_draw_date"]) for payload in predictions
    )
    latest_predictions = [
        payload
        for payload in predictions
        if payload["target_draw_date"] == latest_prediction_date
    ]
    models = tuple(str(model) for model in config["models"])
    observed_models = tuple(
        sorted(str(payload["model_name"]) for payload in latest_predictions)
    )
    if observed_models != tuple(sorted(models)):
        raise _fail("latest prediction cohort does not match configured live models")

    versions: set[str] = set()
    primary: list[str] = []
    shadow: list[str] = []
    history_counts: set[int] = set()
    history_dates: set[str] = set()
    seen_models: set[str] = set()
    latest_target_date = date.fromisoformat(latest_prediction_date)
    published_history_through = published_history.draws[-1].draw_date.isoformat()
    published_draw_count = len(published_history.draws)
    for payload in latest_predictions:
        model = str(payload["model_name"])
        if model in seen_models:
            raise _fail("latest prediction cohort duplicates a model")
        seen_models.add(model)
        version = str(payload["model_version"])
        if _VERSION_RE.fullmatch(version) is None:
            raise _fail("latest prediction cohort has an invalid version")
        versions.add(version)
        metadata = _mapping(payload.get("metadata"), name="prediction metadata")
        role = metadata.get("role")
        if role not in {"primary", "shadow"}:
            raise _fail("prediction role is not primary or shadow")
        (shadow if role == "shadow" else primary).append(model)
        history_draws = _integer(
            metadata.get("history_draws"),
            name="prediction history_draws",
            minimum=1,
            maximum=10_000,
        )
        history_counts.add(history_draws)
        history_through = _iso_date(
            metadata.get("history_through"), name="prediction history_through"
        )
        history_dates.add(history_through)
        generated_at = _parsed_iso_datetime(
            payload.get("generated_at"), name="prediction generated_at"
        )
        if (
            date.fromisoformat(history_through) >= latest_target_date
            or history_through > published_history_through
            or history_draws > published_draw_count
            or generated_at.astimezone(_TORONTO).date() >= latest_target_date
        ):
            raise _fail(
                "latest prediction chronology exceeds published history or draw time"
            )
    if (
        versions != {str(config["model_version"])}
        or len(history_counts) != 1
        or len(history_dates) != 1
    ):
        raise _fail("latest prediction version or history metadata is inconsistent")
    expected_shadow = set(str(model) for model in config["shadow_models"])
    if set(shadow) != expected_shadow or set(primary) != set(models) - expected_shadow:
        raise _fail("latest prediction roles disagree with committed config")

    latest_evaluation_date = max(
        str(payload["target_draw_date"]) for payload in evaluations
    )
    if latest_evaluation_date > published_history_through:
        raise _fail("evaluation chronology exceeds published history")
    if latest_prediction_date <= published_history_through:
        raise _fail("prediction chronology does not extend published history")
    latest_evaluations = [
        payload
        for payload in evaluations
        if payload["target_draw_date"] == latest_evaluation_date
    ]
    preferred = next(
        (
            payload
            for payload in latest_evaluations
            if payload["model_name"] == "ensemble"
        ),
        sorted(latest_evaluations, key=lambda item: str(item["model_name"]))[0],
    )
    matching_predictions = [
        payload
        for payload in predictions
        if payload["target_draw_date"] == preferred["target_draw_date"]
        and payload["model_name"] == preferred["model_name"]
        and payload["model_version"] == preferred["model_version"]
    ]
    if len(matching_predictions) != 1:
        raise _fail("latest evaluation does not identify exactly one prediction")
    metric_prediction = matching_predictions[0]
    metric_metadata = _mapping(
        metric_prediction.get("metadata"), name="evaluated prediction metadata"
    )
    metric_history_through = _iso_date(
        metric_metadata.get("history_through"),
        name="evaluated prediction history_through",
    )
    metric_history_draws = _integer(
        metric_metadata.get("history_draws"),
        name="evaluated prediction history_draws",
        minimum=1,
        maximum=10_000,
    )
    corrected_metric_draws = sum(
        draw.draw_date.isoformat() <= metric_history_through
        for draw in published_history.draws
    )
    metric_target_date = date.fromisoformat(str(preferred["target_draw_date"]))
    metric_generated_at = _parsed_iso_datetime(
        metric_prediction.get("generated_at"),
        name="evaluated prediction generated_at",
    )
    if (
        date.fromisoformat(metric_history_through) >= metric_target_date
        or metric_generated_at.astimezone(_TORONTO).date() >= metric_target_date
    ):
        raise _fail("evaluated prediction chronology is not strictly pre-draw")
    prediction_source = preferred.get("prediction_source")
    if prediction_source is None:
        if (
            metric_history_draws == corrected_metric_draws
            or legacy_classification != "descriptive_only_nonpromotion"
            or str(preferred["target_draw_date"]) >= legacy_target_draw
        ):
            raise _fail("latest evaluation lacks explicit prediction provenance")
        metric_qualification = "legacy_descriptive_only_nonpromotion"
    else:
        source = _mapping(prediction_source, name="evaluation.prediction_source")
        claims = _mapping(
            source.get("claims"), name="evaluation.prediction_source.claims"
        )
        kind = source.get("kind")
        corrected_claim = _boolean(
            claims.get("corrected_history"),
            name="evaluation.prediction_source.claims.corrected_history",
        )
        promotion_claim = _boolean(
            claims.get("promotion_evidence_eligible"),
            name=("evaluation.prediction_source.claims.promotion_evidence_eligible"),
        )
        if (
            kind == "sealed_legacy_incident_history"
            and corrected_claim is False
            and promotion_claim is False
            and legacy_classification == "descriptive_only_nonpromotion"
            and preferred["target_draw_date"] == legacy_target_draw
        ):
            metric_qualification = "legacy_descriptive_only_nonpromotion"
        elif (
            kind == "verified_operational_history"
            and corrected_claim is True
            and promotion_claim is True
            and metric_history_draws == corrected_metric_draws
        ):
            metric_qualification = "corrected_operational_promotion_eligible"
        else:
            raise _fail("latest evaluation prediction provenance is inconsistent")
    recorded_top_hits = tuple(
        _integer(
            preferred.get(key),
            name=f"evaluation.{key}",
            minimum=0,
            maximum=6,
        )
        for key in ("top_6_hits", "top_12_hits", "top_18_hits")
    )
    recorded_final_hits = _integer(
        preferred.get("final_6_hits"),
        name="evaluation.final_6_hits",
        minimum=0,
        maximum=6,
    )
    actual_draws = [
        draw
        for draw in published_history.draws
        if draw.draw_date.isoformat() == preferred["target_draw_date"]
    ]
    if len(actual_draws) != 1:
        raise _fail("latest evaluation actual draw is absent from published history")
    actual_draw = actual_draws[0]
    evaluation_actual = _number_sequence(
        preferred.get("actual"), name="evaluation.actual", size=6
    )
    evaluation_bonus = _integer(
        preferred.get("bonus"), name="evaluation.bonus", minimum=1, maximum=49
    )
    if (
        evaluation_actual != actual_draw.numbers
        or evaluation_bonus != actual_draw.bonus
    ):
        raise _fail("latest evaluation actual draw disagrees with published history")

    final_combination = _number_sequence(
        metric_prediction.get("final_combination"),
        name="prediction.final_combination",
        size=6,
    )
    top6 = _number_sequence(
        metric_prediction.get("top6"), name="prediction.top6", size=6
    )
    top12 = _number_sequence(
        metric_prediction.get("top12"), name="prediction.top12", size=12
    )
    top18 = _number_sequence(
        metric_prediction.get("top18"), name="prediction.top18", size=18
    )
    if not set(top6) < set(top12) or not set(top12) < set(top18):
        raise _fail("evaluated prediction candidate pools are inconsistent")
    actual_numbers = set(actual_draw.numbers)
    final_hits = len(set(final_combination) & actual_numbers)
    top_hits = tuple(len(set(pool) & actual_numbers) for pool in (top6, top12, top18))
    if recorded_final_hits != final_hits or recorded_top_hits != top_hits:
        raise _fail("latest evaluation hit counts disagree with recomputation")
    if not top_hits[0] <= top_hits[1] <= top_hits[2]:
        raise _fail("latest evaluation hit counts are inconsistent")
    return {
        "latest_prediction_date": latest_prediction_date,
        "latest_evaluation_date": latest_evaluation_date,
        "latest_prediction_pending_evaluation": (
            latest_prediction_date > latest_evaluation_date
        ),
        "metric_model": str(preferred["model_name"]),
        "metric_version": str(preferred["model_version"]),
        "metric_qualification": metric_qualification,
        "metric_prediction_path": str(metric_prediction["path"]),
        "metric_history_draws": metric_history_draws,
        "metric_corrected_history_draws": corrected_metric_draws,
        "metric_history_through": metric_history_through,
        "final_hits": final_hits,
        "top_hits": top_hits,
        "models": tuple(models),
        "versions": tuple(sorted(versions)),
        "primary_models": tuple(sorted(primary)),
        "shadow_models": tuple(sorted(shadow)),
        "prediction_history_draws": next(iter(history_counts)),
        "prediction_history_through": next(iter(history_dates)),
    }


def _commit_facts(root: Path) -> dict[str, str]:
    output = _git(
        root,
        ["show", "-s", "--format=%H%n%cI%n%s", "HEAD"],
        maximum=1_024,
    )
    try:
        lines = output.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise _fail("commit metadata is not UTF-8") from exc
    if len(lines) != 3:
        raise _fail("commit metadata is not canonical")
    sha, committed_at, summary = lines
    if _SHA1_RE.fullmatch(sha) is None:
        raise _fail("commit metadata SHA is not canonical")
    _iso_datetime(committed_at, name="commit timestamp")
    _require_string(summary, name="commit summary", maximum=200)
    return {"sha": sha, "committed_at": committed_at, "summary": summary}


def _digest(facts: dict[str, object]) -> str:
    canonical = json.dumps(
        facts,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _enabled(value: object) -> str:
    return "开" if value is True else "关"


def build_research_progress_report(
    repo_root: Path,
    run_context: Mapping[str, str],
    *,
    generated_at: datetime | None = None,
) -> ResearchProgressReport:
    """Build one deterministic Chinese report from the checked-out commit.

    No live source, model, data-refresh, backtest, or GitHub API is imported or
    invoked. External live state is deliberately labeled as not queried.
    """

    root = repo_root.resolve(strict=True)
    if not root.is_dir():
        raise _fail("repository root is not a directory")
    context = _parse_run_context(run_context)
    _generated_instant, generated_at_text = _report_instant(generated_at)
    _require_full_history(root)
    head = _head(root)
    if head != context.sha:
        raise _fail("GITHUB_SHA does not equal checkout HEAD")

    config = _parse_config(
        _committed_blob(root, "config.yaml", maximum=_MAX_CONFIG_BYTES)
    )
    commit = _commit_facts(root)
    if commit["sha"] != head:
        raise _fail("commit metadata does not describe checkout HEAD")
    history, published_history = _history_facts(root, head)
    release = _release_facts(root)
    plan = _mapping(release["live_canary_plan"], name="release.live_canary_plan")
    artifacts = _prediction_and_evaluation_facts(
        root,
        config,
        published_history=published_history,
        legacy_classification=str(plan["legacy_classification"]),
        legacy_target_draw=str(plan["legacy_target_draw"]),
    )

    facts: dict[str, object] = {
        "schema": "lotto649.research-progress-email.facts.v1",
        "run": {
            "repository": context.repository,
            "event_name": context.event_name,
            "ref": context.ref,
            "sha": context.sha,
            "run_id": context.run_id,
            "run_number": context.run_number,
            "run_attempt": context.run_attempt,
            "workflow_ref": context.workflow_ref,
            "workflow_sha": context.workflow_sha,
            "job": context.job,
        },
        "commit": commit,
        "generated_at": generated_at_text,
        "config": config,
        "history": history,
        "release": release,
        "artifacts": artifacts,
    }
    facts_digest = _digest(facts)
    switches = (
        f"data.refresh={_enabled(config['refresh_enabled'])}；"
        f"live={_enabled(config['live_enabled'])}；"
        f"backtest={_enabled(config['backtest_enabled'])}"
    )
    protection = _mapping(release["protection"], name="release.protection")
    publication = _mapping(
        release["publication_canary"], name="release.publication_canary"
    )
    top6, top12, top18 = artifacts["top_hits"]  # type: ignore[misc]
    metric_identity = f"{artifacts['metric_model']} {artifacts['metric_version']}"
    if artifacts["metric_qualification"] == "legacy_descriptive_only_nonpromotion":
        metric_qualification = (
            "前事故/旧版畸形历史 cohort：descriptive-only、nonpromotion"
        )
    else:
        metric_qualification = (
            "纠正后 verified operational cohort：promotion evidence eligibility=是，"
            "但单次结果不构成统计显著性或晋级结论"
        )
    if artifacts["latest_prediction_pending_evaluation"]:
        latest_result = (
            f"最新预测目标 {artifacts['latest_prediction_date']} 尚待同日已提交评估"
        )
    else:
        latest_result = (
            f"最新预测目标 {artifacts['latest_prediction_date']} 已有同日已提交评估"
        )
    credential_state = (
        "登记时已安装"
        if plan["credential_installed_at_registration"]
        else "登记时未安装"
    )
    body = "\n".join(
        (
            "LOTTO 6/49 中文小时进度（只读、已提交证据）",
            "",
            "【时间】"
            f"本次报告生成时间：{generated_at_text}；"
            f"已提交证据截至提交时间：{commit['committed_at']}；"
            f"Actions run id：{context.run_id}；第 {context.run_number} 次 workflow 更新，"
            "不代表累计研究小时，也不是 GitHub 服务端开始时间。",
            "【当前阶段】"
            f"Stage-1 配置已提交（{switches}）；production canary 的已提交计划状态："
            f"{plan['status']}；Stage-1 计划声明无人值守 live 定时为"
            f"{_enabled(plan['stage1_unattended_schedule'])}。",
            "【已完成事项】"
            f"一次性远端发布 canary 的已提交证据通过：{publication['passed']}；"
            f"main 保护证据记录于 {protection['verified_at']}。",
            "【正在进行】"
            "Codex 线程内进行中工作：未查询；本任务只读取当前提交并发送状态邮件。",
            "【下一步】"
            "依已提交计划：满足发布凭据、精确 SHA、时间和双官方来源门后，只运行一次手动 production canary；"
            "成功并复审后才另行评审 live 定时。",
            "【阻塞项】"
            f"发布凭据{credential_state}；最早时间 {plan['not_before']}；"
            f"目标开奖 {plan['source_draw_date']} 的双来源当前状态未查询。",
            "【风险】"
            "外部状态可能晚于本提交，当前远端状态均不作推断；彩票公平且不可预测仍是默认解释，"
            "现有结果不证明稳定优势。",
            "【分支/提交】"
            f"分支：main（{context.ref}）；来源 SHA：{head}；提交说明：{commit['summary']}。",
            "【PR/CI】"
            "当前 PR/CI：未查询；只报告来源提交，不把提交信息等同于当前 Actions 结论。",
            "【main 保护】"
            "当前远端保护：未查询；已提交观察值："
            f"admins={protection['enforce_admins']}、"
            f"force-push={protection['allow_force_pushes']}、"
            f"deletion={protection['allow_deletions']}。",
            "【canary】"
            f"一次性合成 canary 已提交结果：{'通过' if publication['passed'] else '未通过'}；"
            f"production live canary 当前外部状态未查询，计划记录为 {plan['status']}。",
            f"【三开关状态】{switches}；开关不等于 workflow 已获执行授权。",
            "【数据期数/截止日期】"
            f"纠正后已提交验证视图：{history['draw_count']} 期，截至 {history['history_through']}；"
            f"最新预测自身记录的旧输入：{artifacts['prediction_history_draws']} 期，"
            f"截至 {artifacts['prediction_history_through']}。",
            "【最近前瞻命中】"
            "本小时是否新增：未判定（无持久游标）；"
            f"{latest_result}；"
            f"最近已提交评估为 {artifacts['latest_evaluation_date']} 的 "
            f"{metric_identity}，最终组合命中 {artifacts['final_hits']}/6；"
            f"{metric_qualification}。",
            "【Top-6/12/18】"
            f"最近已提交 {metric_identity} 评估 Top-6/12/18："
            f"{top6}/{top12}/{top18}；{metric_qualification}；"
            "该描述性结果不外推统计显著性。",
            "【模型/版本】"
            f"primary={','.join(artifacts['primary_models'])}；"
            f"shadow={','.join(artifacts['shadow_models'])}；"
            f"version={','.join(artifacts['versions'])}。",
            "【邮件状态】正文生成时尚未调用 SMTP，不声明送达成功；程序不会自动重试。",
            "【是否需要用户行动】"
            "仅在已提交计划所列窄权限发布凭据仍未配置时需要配置；当前 Secrets/外部状态未查询。",
            "",
            f"来源 SHA：{head}",
            f"Actions run id：{context.run_id}",
            f"事实摘要 SHA-256：{facts_digest}",
        )
    )
    subject = (
        f"[LOTTO649研究进度] 第{context.run_number}次更新 — "
        f"已提交状态/{metric_identity}"
    )
    if len(subject) > _MAX_SUBJECT_CHARS or len(body) > _MAX_BODY_CHARS:
        raise _fail("rendered progress email exceeds its output limit")
    return ResearchProgressReport(
        subject=subject,
        body=body,
        facts_digest=facts_digest,
    )


def main() -> int:
    if any(name in os.environ for name in _UNREVIEWED_EMAIL_OVERRIDES):
        raise _fail("unreviewed SMTP routing override is present")
    report = build_research_progress_report(
        Path.cwd(),
        os.environ,
        generated_at=datetime.now(UTC).replace(microsecond=0),
    )
    from lotto649.notification import send_email

    if not send_email(report.subject, report.body):
        raise _fail("SMTP configuration is missing; progress email was not sent")
    print("Chinese research progress email sent for the committed snapshot")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
