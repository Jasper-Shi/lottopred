from __future__ import annotations

from datetime import date, timedelta, datetime
from pathlib import Path
import json
import sys
import warnings as py_warnings

from .config import resolve_path
from .data import save_draws, load_draws
from .data_sources import refresh_with_sources
from .domain import Draw, Prediction
from .evaluation import evaluate_prediction
from .models.factory import build_models
from .notification import should_alert, send_hit_alert
from .predictor import make_prediction
from .research_protocol import (
    draw_digest,
    load_experiment_registry,
    snapshot_digest,
)
from .storage import save_prediction, save_evaluation


def _require_live_enabled(cfg: dict) -> None:
    if cfg.get("live", {}).get("enabled", True) is False:
        raise RuntimeError("live execution is disabled by this configuration")


def next_draw_date(after: date) -> date:
    for delta in range(1, 8):
        d = after + timedelta(days=delta)
        if d.weekday() in (2, 5):
            return d
    raise RuntimeError("unreachable")


def refresh_data(cfg: dict) -> list[Draw]:
    csv_path = resolve_path(cfg, cfg["data"]["processed_csv"])
    existing = load_draws(csv_path) if csv_path.exists() else []
    draws = refresh_with_sources(existing, cfg)
    save_draws(draws, csv_path)
    return draws


def evaluate_due_predictions(
    cfg: dict,
    draws: list[Draw],
    *,
    held_model_versions: set[tuple[str, str]] | None = None,
    model_version_quotas: dict[tuple[str, str], int] | None = None,
) -> list[dict]:
    _require_live_enabled(cfg)
    root = Path(cfg["_root"])
    actual_by_date = {d.draw_date.isoformat(): d for d in draws}
    completed = []
    held = held_model_versions or set()
    quotas = model_version_quotas or {}
    admitted: dict[tuple[str, str], int] = {}
    for path in sorted((root / "predictions").glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        identity = (payload.get("model_name"), payload.get("model_version"))
        if identity in held or admitted.get(identity, 0) >= quotas.get(
            identity,
            sys.maxsize,
        ):
            continue
        actual = actual_by_date.get(payload["target_draw_date"])
        if not actual:
            continue
        eval_path = root / "evaluations" / path.name
        if eval_path.exists():
            continue
        pred = Prediction(
            target_draw_date=date.fromisoformat(payload["target_draw_date"]),
            generated_at=datetime.fromisoformat(payload["generated_at"]),
            model_name=payload["model_name"],
            model_version=payload["model_version"],
            probabilities={int(k): float(v) for k, v in payload["probabilities"].items()},
            top6=payload["top6"], top12=payload["top12"], top18=payload["top18"],
            final_combination=payload["final_combination"], metadata=payload.get("metadata", {}),
        )
        ev = evaluate_prediction(pred, actual)
        ev.update(
            {
                "prediction_snapshot_digest": snapshot_digest(payload),
                "prediction_snapshot_path": path.relative_to(root).as_posix(),
                "actual_draw_digest": draw_digest(actual),
                "verified_data_draw_count": len(draws),
                "verified_data_history_through": draws[-1].draw_date.isoformat(),
            }
        )
        if cfg["notifications"].get("enabled", True) and should_alert(ev, cfg):
            ev["email_sent"] = send_hit_alert(ev)
        save_evaluation(root, ev)
        completed.append(ev)
        admitted[identity] = admitted.get(identity, 0) + 1
    return completed


def _prospective_warning(
    code: str,
    *,
    model_name: str,
    experiment_id: str,
    detail: object,
) -> str:
    return (
        f"{code}: model={model_name} experiment={experiment_id} "
        f"detail={detail}"
    )


def _prospective_collection_interlocks(
    cfg: dict,
) -> tuple[
    set[tuple[str, str]],
    dict[tuple[str, str], int],
    list[str],
]:
    """Performance-blind hold preventing an unreviewed 209th V3 evaluation."""
    root = Path(cfg["_root"])
    live_cfg = cfg.get("live", {})
    versions = live_cfg.get("model_versions", {})
    experiments = live_cfg.get("model_version_experiments", {})
    if not isinstance(versions, dict) or not isinstance(experiments, dict):
        return set(), {}, []
    if not experiments:
        return set(), {}, []

    def candidate_evidence_exists(model_name: str, version: str) -> bool:
        pattern = f"*__{model_name}__{version}.json"
        return any((root / "predictions").glob(pattern)) or any(
            (root / "evaluations").glob(pattern)
        )
    held: set[tuple[str, str]] = set()
    quotas: dict[tuple[str, str], int] = {}
    messages: list[str] = []
    try:
        registry = load_experiment_registry(
            root / "docs" / "experiments" / "registry.yaml"
        )
    except Exception as exc:
        for model_name, experiment_id in experiments.items():
            version = versions.get(model_name)
            if not isinstance(version, str) or not candidate_evidence_exists(
                model_name,
                version,
            ):
                continue
            held.add((model_name, version))
            messages.append(
                _prospective_warning(
                    "prospective_collection_audit_failed",
                    model_name=model_name,
                    experiment_id=experiment_id,
                    detail=exc,
                )
            )
        return held, quotas, messages
    for model_name, experiment_id in experiments.items():
        version = versions.get(model_name)
        if not isinstance(version, str):
            continue
        identity = (model_name, version)
        try:
            registration = registry.get(experiment_id)
        except KeyError as exc:
            if candidate_evidence_exists(model_name, version):
                held.add(identity)
                messages.append(
                    _prospective_warning(
                        "prospective_collection_audit_failed",
                        model_name=model_name,
                        experiment_id=experiment_id,
                        detail=exc,
                    )
                )
            continue
        cohort = registration.prospective
        if (
            registration.model_name != model_name
            or registration.model_version != version
            or cohort.role != "shadow"
        ):
            if candidate_evidence_exists(model_name, version):
                held.add(identity)
                messages.append(
                    _prospective_warning(
                        "prospective_collection_audit_failed",
                        model_name=model_name,
                        experiment_id=experiment_id,
                        detail="registered prospective identity mismatch",
                    )
                )
            continue
        if cohort.status == "closed":
            held.add(identity)
            messages.append(
                _prospective_warning(
                    "prospective_collection_interlocked",
                    model_name=model_name,
                    experiment_id=experiment_id,
                    detail="prospective cohort is closed",
                )
            )
            continue
        if not (
            registration.status == "prospective_shadow"
            and cohort.status == "active"
        ):
            if candidate_evidence_exists(model_name, version):
                held.add(identity)
                messages.append(
                    _prospective_warning(
                        "prospective_collection_audit_failed",
                        model_name=model_name,
                        experiment_id=experiment_id,
                        detail="candidate evidence exists outside an active cohort",
                    )
                )
            continue

        formal_paths = tuple(
            registration.parameters.get(name)
            for name in (
                "formal_look_claim",
                "formal_look_attempt",
                "formal_look_json",
                "formal_look_markdown",
            )
        )
        if any(
            isinstance(path, str) and (root / path).exists()
            for path in formal_paths
        ):
            held.add(identity)
            messages.append(
                _prospective_warning(
                    "prospective_collection_interlocked",
                    model_name=model_name,
                    experiment_id=experiment_id,
                    detail="formal-look evidence already exists",
                )
            )
            continue

        raw_evaluations = len(
            tuple(
                (root / "evaluations").glob(
                    f"*__{model_name}__{version}.json"
                )
            )
        )
        if raw_evaluations < cohort.minimum_eligible_draws:
            quotas[identity] = cohort.minimum_eligible_draws - raw_evaluations
            continue
        try:
            from .prospective import audit_registered_cohort

            aggregate = audit_registered_cohort(root, experiment_id)
        except Exception as exc:
            held.add(identity)
            messages.append(
                _prospective_warning(
                    "prospective_collection_audit_failed",
                    model_name=model_name,
                    experiment_id=experiment_id,
                    detail=exc,
                )
            )
            continue
        if aggregate.status in {
            "ready",
            "waiting_for_earlier_pending",
            "overdue",
            "formal_look_recorded",
        }:
            held.add(identity)
            messages.append(
                _prospective_warning(
                    "prospective_collection_interlocked",
                    model_name=model_name,
                    experiment_id=experiment_id,
                    detail=f"cohort audit status is {aggregate.status}",
                )
            )
        elif aggregate.status == "collecting":
            quotas[identity] = 1
        else:
            held.add(identity)
            messages.append(
                _prospective_warning(
                    "prospective_collection_audit_failed",
                    model_name=model_name,
                    experiment_id=experiment_id,
                    detail=f"unsupported cohort audit status {aggregate.status!r}",
                )
            )
    return held, quotas, messages


def _generate_next_predictions(
    cfg: dict,
    draws: list[Draw],
    *,
    interlocked_model_versions: set[tuple[str, str]] | None = None,
    interlock_warnings: list[str] | None = None,
) -> tuple[list[Path], list[str]]:
    _require_live_enabled(cfg)
    root = Path(cfg["_root"])
    default_version = cfg["project"].get("model_version", "v1.0.0")
    model_versions = cfg.get("live", {}).get("model_versions", {})
    if not isinstance(model_versions, dict):
        raise ValueError("live.model_versions must be a mapping")
    if any(
        not isinstance(model_name, str)
        or not isinstance(version, str)
        or not version.strip()
        for model_name, version in model_versions.items()
    ):
        raise ValueError(
            "live.model_versions must map model names to a non-empty version string"
        )
    version_experiments = cfg.get("live", {}).get(
        "model_version_experiments",
        {},
    )
    if not isinstance(version_experiments, dict) or any(
        not isinstance(model_name, str)
        or not isinstance(experiment_id, str)
        or not experiment_id.strip()
        for model_name, experiment_id in version_experiments.items()
    ):
        raise ValueError(
            "live.model_version_experiments must map model names to a non-empty "
            "experiment id"
        )
    if set(version_experiments) - set(model_versions):
        raise ValueError(
            "live.model_version_experiments must correspond to live.model_versions"
        )
    target = next_draw_date(draws[-1].draw_date)
    paths = []
    requested = cfg.get("live", {}).get("models")
    models = build_models(cfg, requested=requested)
    unknown_version_models = set(model_versions) - set(models)
    if unknown_version_models:
        raise ValueError(
            "live.model_versions contains unknown live models: "
            f"{sorted(unknown_version_models)}"
        )
    effective_versions = dict(model_versions)
    prospective_release_metadata: dict[str, dict[str, str]] = {}
    interlocked = interlocked_model_versions or set()
    suppressed_models: set[str] = {
        model_name
        for model_name, version in interlocked
        if model_versions.get(model_name) == version
    }
    prediction_warnings: list[str] = list(interlock_warnings or [])
    for model_name, version in model_versions.items():
        if version != default_version and model_name not in version_experiments:
            suppressed_models.add(model_name)
            effective_versions.pop(model_name, None)
            prediction_warnings.append(
                _prospective_warning(
                    "prospective_experiment_gate_missing",
                    model_name=model_name,
                    experiment_id="unregistered",
                    detail=(
                        f"non-default model version {version!r} requires a registered "
                        "live.model_version_experiments gate"
                    ),
                )
            )
    if version_experiments:
        registry_path = root / "docs" / "experiments" / "registry.yaml"
        try:
            if not registry_path.is_file():
                raise ValueError(
                    "registered live model version requires experiment registry"
                )
            registry = load_experiment_registry(registry_path)
        except Exception as exc:
            registry = None
            for model_name, experiment_id in version_experiments.items():
                suppressed_models.add(model_name)
                effective_versions.pop(model_name, None)
                prediction_warnings.append(
                    _prospective_warning(
                        "prospective_registry_verification_failed",
                        model_name=model_name,
                        experiment_id=experiment_id,
                        detail=exc,
                    )
                )
        shadow_models = set(cfg.get("live", {}).get("shadow_models", []))
        for model_name, experiment_id in version_experiments.items():
            if model_name in suppressed_models:
                continue
            if registry is None:
                continue
            try:
                registration = registry.get(experiment_id)
            except KeyError as exc:
                suppressed_models.add(model_name)
                effective_versions.pop(model_name, None)
                prediction_warnings.append(
                    _prospective_warning(
                        "prospective_experiment_not_found",
                        model_name=model_name,
                        experiment_id=experiment_id,
                        detail=exc,
                    )
                )
                continue
            if (
                registration.model_name != model_name
                or registration.model_version != model_versions[model_name]
                or registration.prospective.role != "shadow"
                or model_name not in shadow_models
            ):
                suppressed_models.add(model_name)
                effective_versions.pop(model_name, None)
                prediction_warnings.append(
                    _prospective_warning(
                        "prospective_experiment_identity_mismatch",
                        model_name=model_name,
                        experiment_id=experiment_id,
                        detail=(
                            "live model version does not match its registered shadow "
                            "experiment"
                        ),
                    )
                )
                continue
            if registration.prospective.status == "not_activated":
                effective_versions.pop(model_name)
                continue
            if not (
                registration.status == "prospective_shadow"
                and registration.prospective.status == "active"
            ):
                suppressed_models.add(model_name)
                effective_versions.pop(model_name, None)
                prediction_warnings.append(
                    _prospective_warning(
                        "prospective_collection_interlocked",
                        model_name=model_name,
                        experiment_id=experiment_id,
                        detail="prospective cohort is not open for collection",
                    )
                )
                continue

            # Import locally so the ordinary V1 path has no prospective-module
            # dependency and tests can replace the verifier at this public seam.
            from .prospective import verify_live_release

            try:
                release = verify_live_release(root, experiment_id)
            except Exception as exc:
                suppressed_models.add(model_name)
                prediction_warnings.append(
                    _prospective_warning(
                        "prospective_release_verification_failed",
                        model_name=model_name,
                        experiment_id=experiment_id,
                        detail=exc,
                    )
                )
                continue
            cohort = registration.prospective
            if (
                release.experiment_id != experiment_id
                or release.model_name != model_name
                or release.model_version != model_versions[model_name]
                or release.freeze_commit != cohort.freeze_commit
                or release.activation_commit != cohort.activation_commit
            ):
                suppressed_models.add(model_name)
                prediction_warnings.append(
                    _prospective_warning(
                        "prospective_release_identity_mismatch",
                        model_name=model_name,
                        experiment_id=experiment_id,
                        detail=(
                            "registered model version does not match verified live "
                            "release identity"
                        ),
                    )
                )
                continue
            if (
                cohort.cohort_start is None
                or cohort.outcomes_known_at_activation is None
                or target < cohort.cohort_start
                or target <= cohort.outcomes_known_at_activation.history_through
            ):
                suppressed_models.add(model_name)
                prediction_warnings.append(
                    _prospective_warning(
                        "prospective_target_outside_cohort",
                        model_name=model_name,
                        experiment_id=experiment_id,
                        detail=(
                            "target must be on or after cohort_start and strictly "
                            "after the activation-known outcome boundary"
                        ),
                    )
                )
                continue
            lock_sha256 = release.frozen_path_sha256.get("requirements-live.lock")
            if (
                not isinstance(lock_sha256, str)
                or len(lock_sha256) != 64
                or any(character not in "0123456789abcdef" for character in lock_sha256)
            ):
                suppressed_models.add(model_name)
                prediction_warnings.append(
                    _prospective_warning(
                        "prospective_runtime_lock_missing",
                        model_name=model_name,
                        experiment_id=experiment_id,
                        detail=(
                            "verified live release is missing the frozen requirements "
                            "lock"
                        ),
                    )
                )
                continue
            prospective_release_metadata[model_name] = {
                "experiment_id": experiment_id,
                "freeze_commit": release.freeze_commit,
                "activation_commit": release.activation_commit,
                "release_commit": release.release_commit,
                "generation_source_commit": release.evidence_commit,
                "immutable_registration_digest": (
                    release.immutable_registration_digest
                ),
                "activation_anchor_sha256": release.activation_anchor_sha256,
                "frozen_manifest_sha256": release.frozen_manifest_sha256,
                "requirements_live_lock_sha256": lock_sha256,
            }
    for model in models.values():
        if model.name in suppressed_models:
            continue
        version = effective_versions.get(model.name, default_version)
        try:
            pred = make_prediction(model, draws, target, cfg, version)
        except Exception as exc:
            experiment_id = version_experiments.get(model.name)
            if experiment_id is None:
                raise
            prediction_warnings.append(
                _prospective_warning(
                    "prospective_prediction_failed",
                    model_name=model.name,
                    experiment_id=experiment_id,
                    detail=exc,
                )
            )
            continue
        if model.name in cfg.get("live", {}).get("shadow_models", []):
            pred.metadata["role"] = "shadow"
        else:
            pred.metadata["role"] = "primary"
        if model.name in prospective_release_metadata:
            pred.metadata["prospective_release"] = prospective_release_metadata[
                model.name
            ]
        path = root / "predictions" / f"{target.isoformat()}__{model.name}__{version}.json"
        if path.exists():
            continue
        paths.append(save_prediction(root, pred))
    return paths, prediction_warnings


def generate_next_predictions(cfg: dict, draws: list[Draw]) -> list[Path]:
    interlocked, _, interlock_warnings = _prospective_collection_interlocks(cfg)
    paths, prediction_warnings = _generate_next_predictions(
        cfg,
        draws,
        interlocked_model_versions=interlocked,
        interlock_warnings=interlock_warnings,
    )
    for message in prediction_warnings:
        py_warnings.warn(message, RuntimeWarning, stacklevel=2)
    return paths


def run_live_cycle(cfg: dict) -> dict:
    _require_live_enabled(cfg)
    interlocked, quotas, interlock_warnings = _prospective_collection_interlocks(cfg)
    draws = refresh_data(cfg)
    evaluations = evaluate_due_predictions(
        cfg,
        draws,
        held_model_versions=interlocked,
        model_version_quotas=quotas,
    )
    predictions, prediction_warnings = _generate_next_predictions(
        cfg,
        draws,
        interlocked_model_versions=interlocked,
        interlock_warnings=interlock_warnings,
    )
    for message in prediction_warnings:
        py_warnings.warn(message, RuntimeWarning, stacklevel=2)
    return {
        "latest_draw": draws[-1].draw_date.isoformat(),
        "draw_count": len(draws),
        "evaluations_created": len(evaluations),
        "predictions_created": [str(p) for p in predictions],
        "prediction_warnings": prediction_warnings,
    }
