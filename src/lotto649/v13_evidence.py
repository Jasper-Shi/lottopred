"""Pure serialization and inference for the frozen V13.0.0 diagnostic.

Nothing in this module loads history, grants execution, observes a clock, writes
an artifact, or sends a notification. The registered attempt owns those seams.
Scoring consumes the exact canonical bytes frozen before the reveal.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from datetime import date, datetime, timedelta
from functools import lru_cache
from itertools import pairwise
from typing import Any

import numpy as np

from .domain import Draw
from .models.factory import build_models
from .models.v13_main_set_overlap import (
    MainDraw,
    OverlapForecast,
    forecast_candidate,
    forecast_control,
    moments,
    validate_forecast,
)
from .optimizer import select_combination

JsonObject = dict[str, Any]
CANDIDATE_MODEL_NAME = "v13_post_rng_main_set_overlap"
CONTROL_MODEL_NAME = "v13_cyclic_anchor_overlap_control"
MODEL_VERSION = "v13.0.0"
FAIR_SET_COUNT = 13_983_816
ARTIFACT_STEM = "v13_post_rng_main_set_overlap_v13.0.0_historical"
SCIENTIFIC_CONTRACT_SHA256 = (
    "7d86364d43907a64d3eb45f23ebb2fdfc2edf807633748e329cd64e0c8341a37"
)
OPERATIONAL_CONTRACT_SHA256 = (
    "69f5eb033a678bf42fe6aeb49ece451934c413a0e4fcd5bc8e1d5e27cb06f382"
)
_FROZEN_V1_CONFIG_SHA256 = (
    "e28659a9b271f044881bd64042f78850861902b9db400e8641fca1214bf0773c"
)
PRIOR_FAMILY_P = (1.0, 1.0, 0.9783404732169021, 0.5909687963172663)
CYCLIC_MAP_SHA256 = "6db8d037c252c737f8e3091d4961e677345cb5eee0a6cf11709b06600d557ad6"
EXPERIMENT_ID = "V13_post_rng_main_set_overlap"
ENSEMBLE_MODEL_NAME = "ensemble_v1.0.0"
RANDOM_MODEL_NAME = "random_v1.0.0"
MODEL_ORDER = (
    CANDIDATE_MODEL_NAME,
    CONTROL_MODEL_NAME,
    ENSEMBLE_MODEL_NAME,
    RANDOM_MODEL_NAME,
)
SCOPE_ORDER = ("aggregate", "first_half", "second_half")
FAIR_PROBABILITY = 6.0 / 49.0
FAIR_TOP12 = 72.0 / 49.0
LOG_N = float.fromhex("0x1.07412c1f4cc68p+4")
LOG_20 = float.fromhex("0x1.7f7427b73e391p+1")
BOOTSTRAP_SEED = 649
BOOTSTRAP_RESAMPLES = 10_000
AUDIT_WARNING_CODES = (
    "one_shot_worker_failed_after_claim",
    "source_integrity_failure",
    "runtime_failure",
    "chronology_failure",
    "numerical_failure",
    "io_failure",
    "worker_failure",
)
STOP_REASONS = (
    None,
    "Archive_after_claim_failure_no_retry",
    "exact_final6_pending_independent_audit",
)
CLASSIFICATION = "consumed_historical_diagnostic_only"
SYNTHETIC_CLASSIFICATION = "synthetic_fixture_only"
CLASSIFICATION_ZH = "历史严格回测；历史诊断/审计候选、不可晋升"
TARGET_IDENTITIES = {
    "aggregate": (
        627,
        "c339733dccc04c3ac25aca15ce991c31421ba35580488e7acadbea5672705782",
    ),
    "first_half": (
        314,
        "c3bea21f775ce8077d25b255ae18a3701b08b22f2bf39c812ce40e78f6edc2e5",
    ),
    "second_half": (
        313,
        "32f924f82aa85e2be7440c66cf7133ab1b16669ede77e7230efef8d7e473ee7b",
    ),
}
GATE_NAMES = (
    "aggregate_positive_primary",
    "aggregate_family_holm",
    "aggregate_primary_interval",
    "both_half_primary",
    "paired_v1_superiority",
    "correlated_controls_conservative_conjunction",
    "all_scope_top6",
    "proper_scores",
    "joint_law",
    "zero_audit_warnings",
)
FEATURES = {
    "v13_post_rng_main_set_overlap": "post_rng_adjacent_main_set_overlap_one_scalar_normal_prior",
    "v13_cyclic_anchor_overlap_control": "post_rng_adjacent_main_set_overlap_one_scalar_fixed_cyclic_source_anchor",
    "ensemble_v1.0.0": "frozen_v1_long_recent_ema_gap_logistic_ensemble",
    "random_v1.0.0": "frozen_v1_target_date_seeded_fair_jitter",
}
_FEATURES = FEATURES
_FORECAST_KEYS = {
    "model_name",
    "model_version",
    "feature_set",
    "probabilities",
    "probability_hex",
    "ranking",
    "top6",
    "top12",
    "top18",
    "final6",
    "scientific_state",
}
_STATE_KEYS = {
    "source_draw_date",
    "source_anchor",
    "transformed_anchor",
    "training_pair_count",
    "training_overlap_sum",
    "scientific_projection_sha256",
    "counts_sha256",
    "beta",
    "beta_hex",
    "mean",
    "mean_hex",
    "complement_mean",
    "complement_mean_hex",
    "log_z",
    "log_z_hex",
}
_PAYLOAD_KEYS = {
    "schema_version",
    "classification",
    "model_version",
    "target_draw_date",
    "history_through",
    "training_cutoff_date",
    "visible_prefix_sha256",
    "visible_prefix_draw_count",
    "bindings",
    "forecasts",
    "forecast_sha256_by_model",
}
_SCORE_KEYS = {
    "model_name",
    "model_version",
    "forecast_sha256",
    "top6_hits",
    "top12_hits",
    "top18_hits",
    "final6_hits",
    "matched_final6",
    "mean_actual_rank",
    "brier_score",
    "log_loss",
    "joint_log_gain",
}
_BASE_SCORED_KEYS = {
    "target_draw_date",
    "actual",
    "bonus",
    "forecast_payload",
    "forecast_payload_sha256",
    "scores",
    "fair_scores",
    "unique_final6",
    "unique_opportunity_count",
    "top12_all_six_producers",
    "exact_final6_opportunities",
}
_ROW_KEYS = _BASE_SCORED_KEYS | {
    "prediction_generated_at",
    "prediction_frozen_event_sequence",
    "prediction_frozen_event_sha256",
    "cumulative_opportunities",
    "scored_event_sequence",
    "scored_event_sha256",
}


def _require_json(value: object) -> None:
    if type(value) is str:
        try:
            value.encode("utf-8")
        except UnicodeEncodeError as error:
            raise ValueError("invalid Unicode scalar") from error
        return
    if value is None or type(value) in {bool, int}:
        return
    if type(value) is float and math.isfinite(value):
        return
    if type(value) is list:
        for item in value:
            _require_json(item)
        return
    if type(value) is dict and all(type(key) is str for key in value):
        for item in value.values():
            _require_json(item)
        return
    raise ValueError("evidence must contain only finite, plain JSON values")


def canonical_json_bytes(value: object) -> bytes:
    """Encode finite plain JSON with exactly one trailing LF."""
    _require_json(value)
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


def _unique_object(pairs: list[tuple[str, Any]]) -> JsonObject:
    result: JsonObject = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(_value: str) -> None:
    raise ValueError("nonfinite JSON constant")


def decode_canonical_json(payload: bytes) -> Any:
    """Reject duplicate keys, nonfinite numbers, and alternative encodings."""
    if type(payload) is not bytes:
        raise ValueError("canonical payload must be bytes")
    value = json.loads(
        payload.decode("utf-8"),
        object_pairs_hook=_unique_object,
        parse_constant=_reject_constant,
    )
    if canonical_json_bytes(value) != payload:
        raise ValueError("payload is not canonical JSON")
    return value


def _date(value: object) -> date:
    if type(value) is not str:
        raise ValueError("date must be canonical ISO text")
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError("date must be canonical ISO text")
    return parsed


def _numbers(value: object, size: int, *, sorted_set: bool = False) -> list[int]:
    if (
        type(value) is not list
        or len(value) != size
        or any(type(number) is not int or not 1 <= number <= 49 for number in value)
        or len(set(value)) != size
        or (sorted_set and value != sorted(value))
    ):
        raise ValueError("invalid registered label sequence")
    return value


def _probabilities(probabilities: Mapping[int, float]) -> dict[int, float]:
    if (
        type(probabilities) is not dict
        or len(probabilities) != 49
        or any(type(key) is not int for key in probabilities)
        or set(probabilities) != set(range(1, 50))
        or any(
            type(value) is not float
            or not math.isfinite(value)
            or not 0.0 < value < 1.0
            for value in probabilities.values()
        )
    ):
        raise ValueError("invalid registered probability mapping")
    result = {label: probabilities[label] for label in range(1, 50)}
    if abs(math.fsum(result.values()) - 6.0) > 1e-12:
        raise ValueError("probabilities do not sum to expected six")
    return result


def _serialize_forecast(
    model_name: str,
    probabilities: Mapping[int, float],
    final6: Sequence[int],
    state: JsonObject | None,
) -> JsonObject:
    probabilities = _probabilities(probabilities)
    ranking = sorted(probabilities, key=lambda label: (-probabilities[label], label))
    result = {
        "model_name": model_name,
        "model_version": MODEL_VERSION if model_name in MODEL_ORDER[:2] else "v1.0.0",
        "feature_set": _FEATURES[model_name],
        "probabilities": {str(label): probabilities[label] for label in range(1, 50)},
        "probability_hex": {
            str(label): probabilities[label].hex() for label in range(1, 50)
        },
        "ranking": ranking,
        "top6": ranking[:6],
        "top12": ranking[:12],
        "top18": ranking[:18],
        "final6": list(final6),
        "scientific_state": state,
    }
    _validate_forecast(result)
    return result


def serialize_overlap_forecast(forecast: OverlapForecast) -> JsonObject:
    """Serialize an issued new-core value without refitting it."""
    if type(forecast) is not OverlapForecast:
        raise ValueError("exact registered OverlapForecast required")
    validate_forecast(forecast)
    state = {
        "source_draw_date": forecast.source_draw_date.isoformat(),
        "source_anchor": list(forecast.source_anchor),
        "transformed_anchor": None
        if forecast.transformed_anchor is None
        else list(forecast.transformed_anchor),
        "training_pair_count": forecast.training_pair_count,
        "training_overlap_sum": forecast.training_overlap_sum,
        "scientific_projection_sha256": forecast.scientific_projection_sha256,
        "counts_sha256": forecast.counts_sha256,
        "beta": forecast.beta,
        "beta_hex": forecast.beta_hex,
        "mean": forecast.mean,
        "mean_hex": forecast.mean_hex,
        "complement_mean": forecast.complement_mean,
        "complement_mean_hex": forecast.complement_mean_hex,
        "log_z": forecast.log_z,
        "log_z_hex": forecast.log_z_hex,
    }
    result = _serialize_forecast(
        forecast.model_name, dict(forecast.probabilities), forecast.final6, state
    )
    if result["probability_hex"] != {
        str(label): value for label, value in forecast.probability_hex
    }:
        raise ValueError("core probability hex mismatch")
    return result


def serialize_comparator_forecast(
    model_name: str,
    probabilities: Mapping[int, float],
) -> JsonObject:
    if model_name not in MODEL_ORDER[2:]:
        raise ValueError("unregistered comparator")
    probabilities = _probabilities(probabilities)
    return _serialize_forecast(
        model_name, probabilities, select_combination(probabilities, 12), None
    )


def _digest(value: object, length: int = 64) -> str:
    if (
        type(value) is not str
        or len(value) != length
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise ValueError("invalid full lowercase digest")
    return value


def _binary64(value: object, hex_value: object) -> float:
    if (
        type(value) is not float
        or not math.isfinite(value)
        or type(hex_value) is not str
        or value.hex() != hex_value
    ):
        raise ValueError("numeric and canonical binary64 hex disagree")
    return value


def _validate_forecast(forecast: object) -> None:
    if type(forecast) is not dict or set(forecast) != _FORECAST_KEYS:
        raise ValueError("forecast schema mismatch")
    name = forecast["model_name"]
    if type(name) is not str or name not in MODEL_ORDER:
        raise ValueError("unregistered model")
    expected_version = MODEL_VERSION if name in MODEL_ORDER[:2] else "v1.0.0"
    if (
        forecast["model_version"] != expected_version
        or forecast["feature_set"] != _FEATURES[name]
    ):
        raise ValueError("forecast scientific identity mismatch")
    raw, encoded = forecast["probabilities"], forecast["probability_hex"]
    labels = {str(label) for label in range(1, 50)}
    if (
        type(raw) is not dict
        or type(encoded) is not dict
        or set(raw) != labels
        or set(encoded) != labels
    ):
        raise ValueError("serialized probability labels mismatch")
    probabilities = _probabilities(
        {
            label: _binary64(raw[str(label)], encoded[str(label)])
            for label in range(1, 50)
        }
    )
    ranking = _numbers(forecast["ranking"], 49)
    if ranking != sorted(
        probabilities, key=lambda label: (-probabilities[label], label)
    ):
        raise ValueError("ranking is not probability descending and label ascending")
    for k in (6, 12, 18):
        if _numbers(forecast[f"top{k}"], k) != ranking[:k]:
            raise ValueError("Top-K is not a ranking prefix")
    final6 = _numbers(forecast["final6"], 6, sorted_set=True)
    state = forecast["scientific_state"]
    if name in MODEL_ORDER[2:]:
        if state is not None or final6 != select_combination(probabilities, 12):
            raise ValueError("comparator state or frozen optimizer selection mismatch")
        return
    if (
        final6 != sorted(ranking[:6])
        or type(state) is not dict
        or set(state) != _STATE_KEYS
    ):
        raise ValueError("overlap forecast state or Final-6 mismatch")
    source = _date(state["source_draw_date"])
    if source < date(2019, 5, 15) or source >= date(2026, 1, 1):
        raise ValueError("source anchor outside registered visible regime")
    if source.weekday() not in (2, 5):
        raise ValueError("source date is not on the registered calendar")
    anchor = _numbers(state["source_anchor"], 6, sorted_set=True)
    transformed = state["transformed_anchor"]
    if name == CANDIDATE_MODEL_NAME:
        if transformed is not None:
            raise ValueError("candidate must have null transformed anchor")
        effective = anchor
    else:
        effective = _numbers(transformed, 6, sorted_set=True)
        if effective != sorted(1 + (label % 49) for label in anchor):
            raise ValueError("control is not the fixed cyclic source-anchor map")
    D, total = state["training_pair_count"], state["training_overlap_sum"]
    if (
        type(D) is not int
        or not 0 <= D <= 4443
        or type(total) is not int
        or not 0 <= total <= 6 * D
    ):
        raise ValueError("invalid training pair count or overlap sum")
    expected_source = date(2019, 5, 15)
    for _ in range(D):
        expected_source += timedelta(days=3 if expected_source.weekday() == 2 else 4)
    if expected_source != source:
        raise ValueError("scientific source date and complete pair count disagree")
    _digest(state["scientific_projection_sha256"])
    _digest(state["counts_sha256"])
    for key in ("beta", "mean", "complement_mean", "log_z"):
        _binary64(state[key], state[key + "_hex"])
    beta = state["beta"]
    residual = 49 * total - 36 * D
    if D == 0 or residual == 0:
        if beta.hex() != "0x0.0p+0":
            raise ValueError("exact integer fair bypass needs positive zero")
    elif (
        beta == 0.0 or (beta > 0.0) != (residual > 0) or abs(beta) >= float(6 * D + 64)
    ):
        raise ValueError("coefficient sign or bracket inconsistent with integer data")
    if (
        D == 0
        and state["counts_sha256"]
        != hashlib.sha256(canonical_json_bytes([])).hexdigest()
    ):
        raise ValueError("empty training count digest mismatch")
    # Moment validation evaluates the law at stored beta, never solves/refits it.
    mean, complement, log_z = moments(beta)
    if any(
        state[key].hex() != value.hex()
        for key, value in (
            ("mean", mean),
            ("complement_mean", complement),
            ("log_z", log_z),
        )
    ):
        raise ValueError("frozen moments disagree with registered binary64 law")
    expected = {
        label: FAIR_PROBABILITY
        if beta == 0.0
        else mean / 6.0
        if label in effective
        else complement / 43.0
        for label in range(1, 50)
    }
    if any(
        probabilities[label].hex() != expected[label].hex() for label in range(1, 50)
    ):
        raise ValueError("frozen marginals disagree with effective anchor law")


def four_forecasts(
    history_prefix: Sequence[Draw],
    target_date: date,
    v1_config: dict,
) -> list[JsonObject]:
    """Compute four models only from the supplied already-visible prefix."""
    history = tuple(history_prefix)
    if (
        type(target_date) is not date
        or not history
        or any(
            type(draw) is not Draw or type(draw.draw_date) is not date
            for draw in history
        )
    ):
        raise ValueError("strict nonempty history prefix required")
    for draw in history:
        _numbers(list(draw.numbers), 6, sorted_set=True)
        if draw.bonus is not None and (
            type(draw.bonus) is not int
            or not 1 <= draw.bonus <= 49
            or draw.bonus in draw.numbers
        ):
            raise ValueError("history prefix has an invalid bonus")
    if any(draw.draw_date >= target_date for draw in history) or any(
        later.draw_date <= earlier.draw_date for earlier, later in pairwise(history)
    ):
        raise ValueError("history is not a strictly increasing pre-target prefix")
    if (
        type(v1_config) is not dict
        or hashlib.sha256(canonical_json_bytes(v1_config)).hexdigest()
        != _FROZEN_V1_CONFIG_SHA256
    ):
        raise ValueError("V1 comparator configuration differs from frozen registration")
    scientific_history = tuple(
        MainDraw(draw.draw_date, tuple(draw.numbers)) for draw in history
    )
    models = build_models(v1_config, requested=["ensemble", "random"])
    return [
        serialize_overlap_forecast(forecast_candidate(scientific_history, target_date)),
        serialize_overlap_forecast(forecast_control(scientific_history, target_date)),
        serialize_comparator_forecast(
            ENSEMBLE_MODEL_NAME, models["ensemble"].predict(list(history), target_date)
        ),
        serialize_comparator_forecast(
            RANDOM_MODEL_NAME, models["random"].predict(list(history), target_date)
        ),
    ]


def _proper_scores(
    probabilities: Mapping[int, float], actual: set[int]
) -> tuple[float, float]:
    brier = (
        math.fsum(
            (probabilities[label] - float(label in actual)) ** 2
            for label in range(1, 50)
        )
        / 49.0
    )
    log_loss = (
        -math.fsum(
            math.log(probabilities[label])
            if label in actual
            else math.log1p(-probabilities[label])
            for label in range(1, 50)
        )
        / 49.0
    )
    return brier, log_loss


def _classification(bindings: JsonObject) -> str:
    if "synthetic_only" in bindings:
        if bindings["synthetic_only"] is not True:
            raise ValueError("synthetic marker must be literal true")
        return SYNTHETIC_CLASSIFICATION
    return CLASSIFICATION


def _validated_frozen_payload(frozen_payload: bytes) -> JsonObject:
    payload = decode_canonical_json(frozen_payload)
    if type(payload) is not dict or set(payload) != _PAYLOAD_KEYS:
        raise ValueError("frozen payload schema mismatch")
    if (
        payload["schema_version"] != "lotto649-v13.0.0-frozen-forecast-v1"
        or payload["classification"] not in (CLASSIFICATION, SYNTHETIC_CLASSIFICATION)
        or payload["model_version"] != MODEL_VERSION
    ):
        raise ValueError("frozen payload identity mismatch")
    target = _date(payload["target_draw_date"])
    cutoff = _date(payload["history_through"])
    if (
        cutoff >= target
        or target >= date(2026, 1, 1)
        or target.weekday() not in (2, 5)
        or cutoff + timedelta(days=3 if cutoff.weekday() == 2 else 4) != target
        or payload["training_cutoff_date"] != payload["history_through"]
    ):
        raise ValueError("visible-history chronology mismatch")
    _digest(payload["visible_prefix_sha256"])
    count = payload["visible_prefix_draw_count"]
    if (
        type(count) is not int
        or not 1 <= count <= 4444
        or type(payload["bindings"]) is not dict
    ):
        raise ValueError("invalid prefix count or binding object")
    if payload["classification"] != _classification(payload["bindings"]):
        raise ValueError("synthetic and historical evidence identities cannot mix")
    forecasts = payload["forecasts"]
    if type(forecasts) is not list or len(forecasts) != 4:
        raise ValueError("four complete frozen forecasts required")
    for forecast in forecasts:
        _validate_forecast(forecast)
    if tuple(forecast["model_name"] for forecast in forecasts) != MODEL_ORDER:
        raise ValueError("registered four-model order mismatch")
    first, control = (forecast["scientific_state"] for forecast in forecasts[:2])
    for key in (
        "source_draw_date",
        "source_anchor",
        "training_pair_count",
        "scientific_projection_sha256",
    ):
        if first[key] != control[key]:
            raise ValueError("candidate/control source-prefix identity mismatch")
    if (
        first["source_draw_date"] != cutoff.isoformat()
        or first["training_pair_count"] >= count
    ):
        raise ValueError("scientific source does not match visible prefix")
    digests = payload["forecast_sha256_by_model"]
    if type(digests) is not dict or set(digests) != set(MODEL_ORDER):
        raise ValueError("four forecast digests required")
    for forecast in forecasts:
        if (
            _digest(digests[forecast["model_name"]])
            != hashlib.sha256(canonical_json_bytes(forecast)).hexdigest()
        ):
            raise ValueError("frozen forecast digest mismatch")
    return payload


def validate_frozen_payload(frozen_payload: bytes) -> None:
    """Validate all four forecasts before permitting any target reveal."""
    _validated_frozen_payload(frozen_payload)


def score_target(frozen_payload: bytes, actual: Draw) -> JsonObject:
    """Score only a canonical frozen payload; the caller proves its durability."""
    payload = _validated_frozen_payload(frozen_payload)
    if type(actual) is not Draw:
        raise ValueError("revealed Draw required")
    target = _date(payload["target_draw_date"])
    if type(actual.draw_date) is not date or actual.draw_date != target:
        raise ValueError("target chronology mismatch")
    main = _numbers(list(actual.numbers), 6, sorted_set=True)
    if actual.bonus is not None and (
        type(actual.bonus) is not int
        or not 1 <= actual.bonus <= 49
        or actual.bonus in main
    ):
        raise ValueError("invalid bonus")
    forecasts = payload["forecasts"]
    actual_set = set(main)
    scores = []
    unique: dict[tuple[int, ...], JsonObject] = {}
    for forecast in forecasts:
        name = forecast["model_name"]
        digest = hashlib.sha256(canonical_json_bytes(forecast)).hexdigest()
        probabilities = {
            label: forecast["probabilities"][str(label)] for label in range(1, 50)
        }
        brier, log_loss = _proper_scores(probabilities, actual_set)
        ranks = {label: index + 1 for index, label in enumerate(forecast["ranking"])}
        state = forecast["scientific_state"]
        gain = None
        if state is not None:
            anchor = (
                state["source_anchor"]
                if state["transformed_anchor"] is None
                else state["transformed_anchor"]
            )
            overlap = len(actual_set & set(anchor))
            gain = (
                0.0
                if state["beta"] == 0.0
                else (LOG_N + state["beta"] * float(overlap)) - state["log_z"]
            )
        matches = sorted(actual_set & set(forecast["final6"]))
        scores.append(
            {
                "model_name": name,
                "model_version": forecast["model_version"],
                "forecast_sha256": digest,
                "top6_hits": len(actual_set & set(forecast["top6"])),
                "top12_hits": len(actual_set & set(forecast["top12"])),
                "top18_hits": len(actual_set & set(forecast["top18"])),
                "final6_hits": len(matches),
                "matched_final6": matches,
                "mean_actual_rank": math.fsum(ranks[label] for label in main) / 6.0,
                "brier_score": brier,
                "log_loss": log_loss,
                "joint_log_gain": gain,
            }
        )
        key = tuple(forecast["final6"])
        if key not in unique:
            unique[key] = {
                "final6": list(key),
                "primary_producer": name,
                "producer_model_names": [],
                "forecast_sha256_by_producer": {},
                "hits": len(matches),
            }
        unique[key]["producer_model_names"].append(name)
        unique[key]["forecast_sha256_by_producer"][name] = digest
    fair_brier, fair_loss = _proper_scores(
        {label: FAIR_PROBABILITY for label in range(1, 50)}, actual_set
    )
    opportunities = list(unique.values())
    result = {
        "target_draw_date": target.isoformat(),
        "actual": main,
        "bonus": actual.bonus,
        "forecast_payload": payload,
        "forecast_payload_sha256": hashlib.sha256(frozen_payload).hexdigest(),
        "scores": scores,
        "fair_scores": {"brier_score": fair_brier, "log_loss": fair_loss},
        "unique_final6": opportunities,
        "unique_opportunity_count": len(opportunities),
        "top12_all_six_producers": [
            score["model_name"] for score in scores if score["top12_hits"] == 6
        ],
        "exact_final6_opportunities": [
            item for item in opportunities if item["hits"] == 6
        ],
    }
    _require_json(result)
    return result


def opportunity_summary(unique_counts: Sequence[int]) -> JsonObject:
    counts = tuple(unique_counts)
    if any(type(count) is not int or not 1 <= count <= 4 for count in counts):
        raise ValueError("each target must have one to four unique opportunities")
    chance = (
        -math.expm1(math.fsum(math.log1p(-count / FAIR_SET_COUNT) for count in counts))
        if counts
        else 0.0
    )
    return {
        "unique_opportunity_count": sum(counts),
        "nominal_fair_exact6_chance": chance,
    }


@lru_cache(maxsize=6)
def _exact_top12_coefficients(n: int) -> tuple[int, ...]:
    weights = tuple(math.comb(12, hits) * math.comb(37, 6 - hits) for hits in range(7))
    coefficients = [1]
    for _ in range(n):
        updated = [0] * (len(coefficients) + 6)
        for total, count in enumerate(coefficients):
            for hits, weight in enumerate(weights):
                updated[total + hits] += count * weight
        coefficients = updated
    return tuple(coefficients)


def exact_top12_tail(n: int, total_hits: int) -> JsonObject:
    """Inclusive upper tail of the exact integer fair Top-12 convolution."""
    if (
        type(n) is not int
        or n < 1
        or type(total_hits) is not int
        or not 0 <= total_hits <= 6 * n
    ):
        raise ValueError("invalid exact-tail sample size or total")
    coefficients = _exact_top12_coefficients(n)
    denominator = FAIR_SET_COUNT**n
    if sum(coefficients) != denominator:
        raise ValueError("integer convolution does not conserve fair mass")
    numerator = sum(coefficients[total_hits:])
    return {
        "value": numerator / denominator,
        "numerator_hex": hex(numerator),
        "denominator_hex": hex(denominator),
    }


def bootstrap_interval(values: Sequence[float | int]) -> JsonObject:
    """Fresh-seed, complete-row 10,000-resample linear-percentile interval."""
    observed = tuple(values)
    if not observed or any(
        type(value) not in {int, float} or not math.isfinite(value)
        for value in observed
    ):
        raise ValueError("bootstrap needs nonempty finite numeric rows")
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    indices = rng.integers(0, len(observed), size=(BOOTSTRAP_RESAMPLES, len(observed)))
    means = np.array(
        [
            math.fsum(observed[int(index)] for index in sample) / len(observed)
            for sample in indices
        ],
        dtype=np.float64,
    )
    lower, upper = np.quantile(means, [0.025, 0.975], method="linear")
    return {
        "lower": float(lower),
        "upper": float(upper),
        "seed": BOOTSTRAP_SEED,
        "resamples": BOOTSTRAP_RESAMPLES,
        "method": "linear",
    }


def holm_adjusted(p_values: Sequence[float]) -> tuple[float, ...]:
    values = tuple(p_values)
    if not values or any(
        type(value) not in {float, int}
        or not math.isfinite(value)
        or not 0.0 <= value <= 1.0
        for value in values
    ):
        raise ValueError("Holm requires finite probabilities")
    ordered = sorted(range(len(values)), key=lambda index: (values[index], index))
    adjusted = [0.0] * len(values)
    running = 0.0
    for rank, index in enumerate(ordered):
        running = max(running, min(1.0, (len(values) - rank) * values[index]))
        adjusted[index] = float(running)
    return tuple(adjusted)


def _validated_rows(rows: Sequence[JsonObject]) -> tuple[JsonObject, ...]:
    result = tuple(rows)
    if not result:
        raise ValueError("a scored scope cannot be empty")
    previous = None
    previous_sequence = -1
    previous_generated = None
    first_bindings = None
    for row in result:
        if type(row) is not dict or set(row) != _ROW_KEYS:
            raise ValueError("complete closed scored row required")
        _require_json(row)
        target = _date(row["target_draw_date"])
        if previous is not None and target <= previous:
            raise ValueError("scored rows must be strictly chronological")
        previous = target
        actual = _numbers(row["actual"], 6, sorted_set=True)
        recomputed = score_target(
            canonical_json_bytes(row["forecast_payload"]),
            Draw(target, tuple(actual), row["bonus"]),
        )
        if canonical_json_bytes(
            {key: row[key] for key in _BASE_SCORED_KEYS}
        ) != canonical_json_bytes(recomputed):
            raise ValueError("scored row disagrees with its frozen payload")
        if first_bindings is None:
            first_bindings = row["forecast_payload"]["bindings"]
        if canonical_json_bytes(
            row["forecast_payload"]["bindings"]
        ) != canonical_json_bytes(first_bindings):
            raise ValueError("scored rows changed immutable bindings")
        generated = row["prediction_generated_at"]
        if (
            type(generated) is not str
            or len(generated) < 20
            or generated[10] != "T"
            or not generated.endswith("Z")
        ):
            raise ValueError("prediction time must be UTCZ")
        instant = datetime.fromisoformat(generated)
        if previous_generated is not None and instant < previous_generated:
            raise ValueError("prediction times are not monotone")
        previous_generated = instant
        forecast_sequence, scored_sequence = (
            row["prediction_frozen_event_sequence"],
            row["scored_event_sequence"],
        )
        if (
            type(forecast_sequence) is not int
            or type(scored_sequence) is not int
            or not previous_sequence < forecast_sequence < scored_sequence
        ):
            raise ValueError("frozen/scored event chronology mismatch")
        previous_sequence = scored_sequence
        _digest(row["prediction_frozen_event_sha256"])
        _digest(row["scored_event_sha256"])
        # Scope slices retain cohort-wide cumulative values; build_report checks
        # the entire prefix once before grouping, while this validator preserves them.
        if type(row["cumulative_opportunities"]) is not dict or set(
            row["cumulative_opportunities"]
        ) != {"unique_opportunity_count", "nominal_fair_exact6_chance"}:
            raise ValueError("cumulative opportunity schema mismatch")
    return result


def _mean(values: Sequence[float | int]) -> float:
    return math.fsum(values) / len(values)


def _calibration(rows: Sequence[JsonObject], model_index: int) -> list[JsonObject]:
    probabilities: list[list[float]] = [[] for _ in range(10)]
    outcomes: list[list[int]] = [[] for _ in range(10)]
    for row in rows:
        actual = set(row["actual"])
        mapping = row["forecast_payload"]["forecasts"][model_index]["probabilities"]
        for label in range(1, 50):
            probability = mapping[str(label)]
            for index in range(10):
                if index / 10.0 <= probability < (index + 1) / 10.0:
                    probabilities[index].append(probability)
                    outcomes[index].append(int(label in actual))
                    break
            else:
                raise ValueError("probability outside fixed calibration bins")
    return [
        {
            "lower": index / 10.0,
            "upper": (index + 1) / 10.0,
            "count": len(probabilities[index]),
            "mean_probability": _mean(probabilities[index])
            if probabilities[index]
            else None,
            "observed_frequency": _mean(outcomes[index]) if outcomes[index] else None,
        }
        for index in range(10)
    ]


def _model_summary(
    rows: Sequence[JsonObject], model_index: int, *, inference: bool
) -> JsonObject:
    scores = [row["scores"][model_index] for row in rows]
    result: JsonObject = {
        "model_name": MODEL_ORDER[model_index],
        "draw_count": len(rows),
        "mean_final6_hits": _mean([score["final6_hits"] for score in scores]),
        "mean_actual_rank": _mean([score["mean_actual_rank"] for score in scores]),
        "brier_score": _mean([score["brier_score"] for score in scores]),
        "log_loss": _mean([score["log_loss"] for score in scores]),
        "final6_histogram": {
            str(hits): sum(score["final6_hits"] == hits for score in scores)
            for hits in range(7)
        },
        "joint_log_gain_sum": math.fsum(score["joint_log_gain"] for score in scores)
        if model_index < 2
        else None,
        "calibration_bins": _calibration(rows, model_index),
    }
    for k in (6, 12, 18):
        mean = _mean([score[f"top{k}_hits"] for score in scores])
        result[f"mean_top{k}_hits"] = mean
        result[f"top{k}_lift"] = mean - 6.0 * k / 49.0
    if inference:
        result["top12_exact_p"] = exact_top12_tail(
            len(scores), sum(score["top12_hits"] for score in scores)
        )
        result["top12_lift_ci95"] = bootstrap_interval(
            [score["top12_hits"] - FAIR_TOP12 for score in scores]
        )
    return result


def _scope_summary(rows: Sequence[JsonObject]) -> JsonObject:
    models = {
        name: _model_summary(rows, index, inference=True)
        for index, name in enumerate(MODEL_ORDER)
    }
    candidate = [row["scores"][0] for row in rows]
    contrasts: JsonObject = {}
    for name, model_index in (
        ("candidate_minus_v1", 2),
        ("candidate_minus_cyclic_control", 1),
    ):
        others = [row["scores"][model_index] for row in rows]
        contrast = {
            "top12_paired_ci95": bootstrap_interval(
                [
                    left["top12_hits"] - right["top12_hits"]
                    for left, right in zip(candidate, others, strict=True)
                ]
            ),
            "brier_delta": _mean(
                [
                    left["brier_score"] - right["brier_score"]
                    for left, right in zip(candidate, others, strict=True)
                ]
            ),
            "log_loss_delta": _mean(
                [
                    left["log_loss"] - right["log_loss"]
                    for left, right in zip(candidate, others, strict=True)
                ]
            ),
        }
        if model_index == 1:
            contrast["joint_log_gain_sum"] = math.fsum(
                left["joint_log_gain"] - right["joint_log_gain"]
                for left, right in zip(candidate, others, strict=True)
            )
        contrasts[name] = contrast
    contrasts["candidate_minus_fair"] = {
        "brier_delta": _mean(
            [
                row["scores"][0]["brier_score"] - row["fair_scores"]["brier_score"]
                for row in rows
            ]
        ),
        "log_loss_delta": _mean(
            [
                row["scores"][0]["log_loss"] - row["fair_scores"]["log_loss"]
                for row in rows
            ]
        ),
    }
    dates = [row["target_draw_date"] for row in rows]
    return {
        "n": len(rows),
        "first_target": dates[0],
        "last_target": dates[-1],
        "target_dates_sha256": hashlib.sha256(
            ("\n".join(dates) + "\n").encode("utf-8")
        ).hexdigest(),
        "models": models,
        "contrasts": contrasts,
    }


def summarize_scope(rows: Sequence[JsonObject]) -> JsonObject:
    """Infer only after the full 627-target horizon; never on a stopped half."""
    observed = _validated_rows(rows)
    dates = [row["target_draw_date"] for row in observed]
    identity = (
        len(observed),
        hashlib.sha256(("\n".join(dates) + "\n").encode()).hexdigest(),
    )
    if identity != TARGET_IDENTITIES["aggregate"] or any(
        row["exact_final6_opportunities"] for row in observed
    ):
        raise ValueError("inference requires the exact complete uncaptured 627 horizon")
    return _scope_summary(observed)


def _audit_inputs(
    audit_complete: bool, audit_warnings: Sequence[str]
) -> tuple[str, ...]:
    if type(audit_complete) is not bool or isinstance(audit_warnings, (str, bytes)):
        raise ValueError("explicit audit completeness and warning list required")
    warnings = tuple(audit_warnings)
    if any(
        type(warning) is not str or warning not in AUDIT_WARNING_CODES
        for warning in warnings
    ):
        raise ValueError("audit warning must be a registered safe enum")
    return warnings


def _validate_gate_inputs(scopes: Mapping[str, JsonObject]) -> None:
    """Reject missing or nonnumeric gate inputs instead of truthy substitutes."""

    def number(value: object) -> None:
        if type(value) is not float or not math.isfinite(value):
            raise ValueError("gate metric must be finite binary64")

    def interval(value: object) -> None:
        if type(value) is not dict or not {"lower", "upper"} <= set(value):
            raise ValueError("gate interval is incomplete")
        number(value["lower"])
        number(value["upper"])
        if value["lower"] > value["upper"]:
            raise ValueError("gate interval is reversed")

    for scope_name, scope in scopes.items():
        if type(scope) is not dict or set(scope) != {
            "n",
            "first_target",
            "last_target",
            "target_dates_sha256",
            "models",
            "contrasts",
        }:
            raise ValueError("gate scope is incomplete")
        if (
            type(scope["n"]) is not int
            or (scope["n"], scope["target_dates_sha256"])
            != TARGET_IDENTITIES[scope_name]
        ):
            raise ValueError("gate scope has the wrong fixed horizon")
        endpoints = {
            "aggregate": ("2020-01-01", "2025-12-31"),
            "first_half": ("2020-01-01", "2022-12-31"),
            "second_half": ("2023-01-04", "2025-12-31"),
        }
        if (scope["first_target"], scope["last_target"]) != endpoints[scope_name]:
            raise ValueError("gate scope endpoint mismatch")
        models, contrasts = scope["models"], scope["contrasts"]
        if type(models) is not dict or set(models) != set(MODEL_ORDER):
            raise ValueError("gate scope must include all four producers")
        if type(contrasts) is not dict or set(contrasts) != {
            "candidate_minus_v1",
            "candidate_minus_cyclic_control",
            "candidate_minus_fair",
        }:
            raise ValueError("gate scope must include all fixed contrasts")
        for name, model in models.items():
            if type(model) is not dict or not {
                "top12_lift",
                "top6_lift",
                "top12_exact_p",
                "top12_lift_ci95",
                "joint_log_gain_sum",
            } <= set(model):
                raise ValueError("gate model summary is incomplete")
            number(model["top12_lift"])
            number(model["top6_lift"])
            probability = model["top12_exact_p"]
            if type(probability) is not dict or "value" not in probability:
                raise ValueError("gate exact p is incomplete")
            number(probability["value"])
            if not 0.0 <= probability["value"] <= 1.0:
                raise ValueError("gate exact p is outside probability domain")
            interval(model["top12_lift_ci95"])
            if name in MODEL_ORDER[:2]:
                number(model["joint_log_gain_sum"])
        for name, contrast in contrasts.items():
            if type(contrast) is not dict or not {
                "brier_delta",
                "log_loss_delta",
            } <= set(contrast):
                raise ValueError("gate contrast is incomplete")
            number(contrast["brier_delta"])
            number(contrast["log_loss_delta"])
            if name != "candidate_minus_fair":
                interval(contrast.get("top12_paired_ci95"))
            if name == "candidate_minus_cyclic_control":
                number(contrast.get("joint_log_gain_sum"))


def evaluate_ten_gates(
    scopes: Mapping[str, JsonObject],
    *,
    audit_complete: bool,
    audit_warnings: Sequence[str],
) -> list[JsonObject]:
    warnings = _audit_inputs(audit_complete, audit_warnings)
    if set(scopes) != set(SCOPE_ORDER):
        raise ValueError("all three registered scopes are mandatory")
    _require_json(dict(scopes))
    _validate_gate_inputs(scopes)
    aggregate = scopes["aggregate"]
    candidate = aggregate["models"][CANDIDATE_MODEL_NAME]
    p_vector = (*PRIOR_FAMILY_P, candidate["top12_exact_p"]["value"])
    corrected_p = holm_adjusted(p_vector)[4]
    ordered = [scopes[name] for name in SCOPE_ORDER]
    checks = [
        candidate["top12_lift"] > 0.0,
        corrected_p <= 0.05,
        candidate["top12_lift_ci95"]["lower"] > 0.0,
        all(
            scope["models"][CANDIDATE_MODEL_NAME]["top12_lift"] > 0.0
            for scope in ordered[1:]
        ),
        all(
            scope["contrasts"]["candidate_minus_v1"]["top12_paired_ci95"]["lower"] > 0.0
            for scope in ordered
        ),
        all(
            scope["contrasts"]["candidate_minus_cyclic_control"]["top12_paired_ci95"][
                "lower"
            ]
            > 0.0
            and all(
                scope["models"][control]["top12_exact_p"]["value"] > 0.05
                and scope["models"][control]["top12_lift_ci95"]["lower"]
                <= 0.0
                <= scope["models"][control]["top12_lift_ci95"]["upper"]
                for control in (CONTROL_MODEL_NAME, RANDOM_MODEL_NAME)
            )
            for scope in ordered
        ),
        all(
            scope["models"][CANDIDATE_MODEL_NAME]["top6_lift"] > 0.0
            for scope in ordered
        ),
        all(
            scope["contrasts"][reference][metric] <= 1e-9
            for scope in ordered
            for reference in ("candidate_minus_fair", "candidate_minus_v1")
            for metric in ("brier_delta", "log_loss_delta")
        ),
        candidate["joint_log_gain_sum"] >= LOG_20
        and all(
            scope["models"][CANDIDATE_MODEL_NAME]["joint_log_gain_sum"] > 0.0
            for scope in ordered[1:]
        )
        and all(
            scope["contrasts"]["candidate_minus_cyclic_control"]["joint_log_gain_sum"]
            > 0.0
            for scope in ordered
        )
        and aggregate["models"][CONTROL_MODEL_NAME]["joint_log_gain_sum"] < LOG_20,
        audit_complete and not warnings,
    ]
    return [
        {"number": number, "name": name, "passed": bool(passed)}
        for number, (name, passed) in enumerate(zip(GATE_NAMES, checks, strict=True), 1)
    ]


def _registered_dates() -> tuple[str, ...]:
    current = date(2020, 1, 1)
    last = date(2025, 12, 31)
    result = []
    while current <= last:
        if current.weekday() in (2, 5):
            result.append(current.isoformat())
        current += timedelta(days=1)
    return tuple(result)


def build_report(
    rows: Sequence[JsonObject],
    bindings: JsonObject,
    *,
    audit_complete: bool,
    audit_warnings: Sequence[str] = (),
    stop_reason: str | None = None,
) -> JsonObject:
    """Build complete registered diagnostics or an explicitly incomplete report."""
    warnings = _audit_inputs(audit_complete, audit_warnings)
    if type(bindings) is not dict or stop_reason not in STOP_REASONS:
        raise ValueError("report bindings or stop reason is invalid")
    _require_json(bindings)
    _digest(bindings.get("pure_core_sha256"))
    if (
        bindings.get("statistical_fingerprint_sha256") != SCIENTIFIC_CONTRACT_SHA256
        or bindings.get("operational_contract_sha256") != OPERATIONAL_CONTRACT_SHA256
    ):
        raise ValueError("report scientific/operational bindings mismatch")
    observed = _validated_rows(rows) if rows else ()
    if observed and canonical_json_bytes(
        observed[0]["forecast_payload"]["bindings"]
    ) != canonical_json_bytes(bindings):
        raise ValueError("report bindings differ from frozen forecasts")
    counts = []
    for row in observed:
        counts.append(row["unique_opportunity_count"])
        if canonical_json_bytes(
            row["cumulative_opportunities"]
        ) != canonical_json_bytes(opportunity_summary(counts)):
            raise ValueError("cumulative opportunity arithmetic mismatch")
    expected = _registered_dates()
    dates = tuple(row["target_draw_date"] for row in observed)
    if dates != expected[: len(dates)]:
        raise ValueError("report targets are not the registered chronological prefix")
    exact_hits = [
        row["target_draw_date"] for row in observed if row["exact_final6_opportunities"]
    ]
    if exact_hits and (len(exact_hits) != 1 or exact_hits[0] != dates[-1]):
        raise ValueError("forecasting continued after an exact Final-6 detection")
    if stop_reason == "exact_final6_pending_independent_audit" and not exact_hits:
        raise ValueError("capture stop reason requires a frozen exact Final-6")
    complete = len(observed) == 627 and stop_reason is None and not exact_hits
    scopes: JsonObject = {}
    gates = None
    multiplicity = None
    if complete:
        grouped = {
            "aggregate": observed,
            "first_half": observed[:314],
            "second_half": observed[314:],
        }
        for name in SCOPE_ORDER:
            summary = _scope_summary(grouped[name])
            if (summary["n"], summary["target_dates_sha256"]) != TARGET_IDENTITIES[
                name
            ]:
                raise ValueError("fixed historical scope identity mismatch")
            scopes[name] = summary
        gates = evaluate_ten_gates(
            scopes, audit_complete=audit_complete, audit_warnings=warnings
        )
        vector = [
            1.0,
            1.0,
            0.9783404732169021,
            0.5909687963172663,
            scopes["aggregate"]["models"][CANDIDATE_MODEL_NAME]["top12_exact_p"][
                "value"
            ],
        ]
        multiplicity = {
            "family": "transition_markov",
            "scope": "five_variant_family_only_not_Goal_global",
            "ordered_variants": ["V2", "V3", "V11", "V12", "V13"],
            "candidate_zero_based_index": 4,
            "prior_value_provenance": {
                "v11_source_registration_commit": "0af20fc41fc5aaa0879dada0a258797a8bc14e20",
                "v11_accounting_only": True,
                "v12_source_commit": "c9b483f6e89bf73eade28829188fbebe745e28c0",
                "v12_report_sha256": "5582ce55fd1fbfece3f5402501bf0470d4e60b1f35c5f66aae02d928cfaa496a",
                "verification": "preauthorization_metadata_pins_and_reliance_on_completed_independent_audit_no_runtime_report_read",
            },
            "variant_index": 5,
            "input_vector": vector,
            "adjusted_vector": list(holm_adjusted(vector)),
        }
    if (
        exact_hits
        and stop_reason == "exact_final6_pending_independent_audit"
        and not warnings
    ):
        disposition = "pending_audit"
    elif not observed:
        disposition = "startup_failed_unscored"
    elif not complete or not audit_complete or warnings:
        disposition = "Archive"
    elif all(gate["passed"] for gate in gates):
        disposition = "historical_diagnostic_pass_unpromoted"
    else:
        disposition = "Reject"
    annual: JsonObject = {}
    for year in ("2020", "2021", "2022", "2023", "2024", "2025"):
        subset = [
            row for row in observed if row["target_draw_date"].startswith(year + "-")
        ]
        annual[year] = (
            {
                name: _model_summary(subset, index, inference=False)
                for index, name in enumerate(MODEL_ORDER)
            }
            if subset
            else {}
        )
    best: JsonObject = {}
    if observed:
        for index, name in enumerate(MODEL_ORDER):
            best_hits = max(row["scores"][index]["final6_hits"] for row in observed)
            best[name] = {
                "final6_hits": best_hits,
                "target_dates": [
                    row["target_draw_date"]
                    for row in observed
                    if row["scores"][index]["final6_hits"] == best_hits
                ],
            }
    report = {
        "schema_version": "lotto649.v13.0.0.historical-diagnostic-report.v1",
        "experiment_id": EXPERIMENT_ID,
        "model_version": MODEL_VERSION,
        "seed": 649,
        "classification": _classification(bindings),
        "classification_zh": (
            "仅合成夹具测试；不属于历史预测或可采信研究证据"
            if _classification(bindings) == SYNTHETIC_CLASSIFICATION
            else CLASSIFICATION_ZH
        ),
        "statistical_fingerprint_sha256": SCIENTIFIC_CONTRACT_SHA256,
        "operational_contract_sha256": OPERATIONAL_CONTRACT_SHA256,
        "required_pure_core_sha256": bindings["pure_core_sha256"],
        "primary_metric": "mean_top12_main_number_hits_minus_72_over_49",
        "cyclic_control": {
            "model_name": CONTROL_MODEL_NAME,
            "role": "correlated_fair_null_sanity_control_not_independent_replication",
            "map": "pi(i)=1+(i mod49)",
            "map_sha256": CYCLIC_MAP_SHA256,
            "source_only_transformation": True,
            "own_training_counts_and_coefficient": True,
            "fair_correlation_given_anchor": "(49*r-36)/258",
            "unconditional_fair_correlation": "-1/48",
            "non_null_control_is_integrity_warning": False,
        },
        "eligible_evidence": False,
        "promotion_authority": False,
        "complete_registered_scope": complete,
        "expected_target_count": 627,
        "processed_target_count": len(observed),
        "disposition": disposition,
        "stop_reason": stop_reason,
        "bindings": bindings,
        "audit": {
            "complete": audit_complete,
            "scope": "worker_record_consistency_not_independent_leakage_audit",
            "warning_count": len(warnings),
            "warnings": list(warnings),
            "independent_leakage_audit": "pending" if exact_hits else "not_claimed",
        },
        "fair_baselines": {
            "probability": FAIR_PROBABILITY,
            "top6_mean": 36.0 / 49.0,
            "top12_mean": FAIR_TOP12,
            "top18_mean": 108.0 / 49.0,
            "exact_final6_probability": 1.0 / FAIR_SET_COUNT,
        },
        "scope_order": list(SCOPE_ORDER),
        "model_order": list(MODEL_ORDER),
        "scopes": scopes,
        "multiplicity": multiplicity,
        "gates": gates,
        "annual_descriptive_only": annual,
        "best_final6_by_model": best,
        "opportunities": opportunity_summary(
            [row["unique_opportunity_count"] for row in observed]
        ),
        "opportunity_interpretation": {
            "nominal_only": True,
            "anytime_p_value": False,
            "Goal_global_multiplicity": False,
            "reused_v1_random_across_versions_are_new_independent_opportunities": False,
            "identity": "target_date_and_sorted_final6",
            "ledger": "new_V13_local_consumed_diagnostic_only_never_existing_eligible_OOS",
        },
        "partial_descriptive": {
            name: _model_summary(observed, index, inference=False)
            for index, name in enumerate(MODEL_ORDER)
        }
        if observed
        else {},
        "exclusions": {
            "burn_in_scored": 0,
            "known_2026_scored": 0,
            "known_2026_classification": "consumed_excluded",
            "unprocessed_target_count": 627 - len(observed),
        },
        "targets": list(observed),
    }
    _require_json(report)
    return report


def _text(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_markdown(report: JsonObject) -> str:
    """Render every target and all fixed descriptive/inferential comparisons."""
    _require_json(report)
    lines = [
        "# V13.0.0 历史严格回测诊断",
        "",
        report["classification_zh"],
        "",
        f"状态：{report['disposition']}；已评分 {report['processed_target_count']}/627 期。",
        "2020–2025 是已消耗的历史诊断数据；彩票公平且不可预测是默认解释。",
        "这些结果不具备晋升或未来购票建议的效力。",
        f"[完整 JSON：全部 49 个概率及其十六进制、排名与审计绑定]({ARTIFACT_STEM}.json)",
        "",
        "## 身份与审计",
        "",
        "```json",
        canonical_json_bytes(
            {
                "bindings": report["bindings"],
                "audit": report["audit"],
                "cyclic_control": report["cyclic_control"],
                "claim_sha256": report.get("claim_sha256"),
                "ledger": report.get("ledger"),
            }
        ).decode("utf-8")[:-1],
        "```",
        "",
        "独立 leakage audit 与 worker 记录一致性检查分开；此报告本身不宣称独立审计通过。",
        "控制组仅为固定循环源锚点的相关公平零假设检查，不是独立复制或保证消除信号。",
        "",
        "## 公平理论基准",
        "",
        "| Top-6 | Top-12 | Top-18 | 单组 Final-6 6/6 概率 |",
        "|---:|---:|---:|---:|",
        "| 36/49 | 72/49 | 108/49 | 1/13,983,816 |",
        "",
    ]
    if report["gates"] is None:
        lines += [
            "本次仅有部分或未评分证据；不计算完整区间的 p 值、Holm、置信区间或十项 gates。",
            "",
        ]
    else:
        lines += [
            "## 三个固定区间",
            "",
            "| 区间 | 模型 | n | Top-6 | Top-12 | Top-18 | Final-6 | 平均真实排名 | Brier | Log Loss | joint gain | exact p | 95% lift CI |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
        ]
        for scope_name in SCOPE_ORDER:
            scope = report["scopes"][scope_name]
            for name in MODEL_ORDER:
                m = scope["models"][name]
                interval = m["top12_lift_ci95"]
                joint = (
                    "null"
                    if m["joint_log_gain_sum"] is None
                    else f"{m['joint_log_gain_sum']:.6f}"
                )
                lines.append(
                    f"| {scope_name} | {name} | {scope['n']} | {m['mean_top6_hits']:.6f} | {m['mean_top12_hits']:.6f} | {m['mean_top18_hits']:.6f} | {m['mean_final6_hits']:.6f} | {m['mean_actual_rank']:.6f} | {m['brier_score']:.6f} | {m['log_loss']:.6f} | {joint} | {m['top12_exact_p']['value']:.8g} | [{interval['lower']:.6f}, {interval['upper']:.6f}] |"
                )
        lines += [
            "",
            "### 配对比较",
            "",
            "| 区间 | 对比 | Top-12 95% CI | Brier 差 | Log Loss 差 | joint gain 差 |",
            "|---|---|---|---:|---:|---:|",
        ]
        for scope_name in SCOPE_ORDER:
            for name, contrast in report["scopes"][scope_name]["contrasts"].items():
                ci = contrast.get("top12_paired_ci95")
                interval = (
                    "不适用"
                    if ci is None
                    else f"[{ci['lower']:.6f}, {ci['upper']:.6f}]"
                )
                joint = (
                    "不适用"
                    if "joint_log_gain_sum" not in contrast
                    else f"{contrast['joint_log_gain_sum']:.6f}"
                )
                lines.append(
                    f"| {scope_name} | {name} | {interval} | {contrast['brier_delta']:.6f} | {contrast['log_loss_delta']:.6f} | {joint} |"
                )
        lines += [
            "",
            "区间为固定种子的逐期重采样描述；不保证备择假设下对序列依赖稳健。",
            "",
            "### 五模型家族 Holm",
            "",
            "仅对固定 V2/V3/V11/V12/V13 家族计数，不是整个 Goal 的全局校正。",
            "",
            "| 版本 | 原始 p | 调整 p |",
            "|---|---:|---:|",
        ]
        for name, raw, adjusted in zip(
            report["multiplicity"]["ordered_variants"],
            report["multiplicity"]["input_vector"],
            report["multiplicity"]["adjusted_vector"],
            strict=True,
        ):
            lines.append(f"| {name} | {raw:.8g} | {adjusted:.8g} |")
        lines += [
            "",
            "### 十项 gates",
            "",
            "| # | 注册 gate | 通过 |",
            "|---:|---|---|",
        ]
        for gate in report["gates"]:
            lines.append(f"| {gate['number']} | {gate['name']} | {gate['passed']} |")
    lines += [
        "",
        "## 全部最佳命中并列日期",
        "",
        "| 模型 | 最高 Final-6 命中 | 全部并列日期 |",
        "|---|---:|---|",
    ]
    for name in MODEL_ORDER:
        if name in report["best_final6_by_model"]:
            best = report["best_final6_by_model"][name]
            lines.append(
                f"| {name} | {best['final6_hits']} | {', '.join(best['target_dates'])} |"
            )
    descriptions = [("已观察全部", report["partial_descriptive"])]
    descriptions.extend(
        ("年度 " + year, report["annual_descriptive_only"][year])
        for year in ("2020", "2021", "2022", "2023", "2024", "2025")
    )
    for title, models in descriptions:
        lines += [
            "",
            "## " + title + "：描述性指标",
            "",
            "| 模型 | n | Top-6 | Top-12 | Top-18 | Final-6 | 平均真实排名 | Brier | Log Loss | joint gain |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for name, m in models.items():
            joint = (
                "null"
                if m["joint_log_gain_sum"] is None
                else f"{m['joint_log_gain_sum']:.6f}"
            )
            lines.append(
                f"| {name} | {m['draw_count']} | {m['mean_top6_hits']:.6f} | {m['mean_top12_hits']:.6f} | {m['mean_top18_hits']:.6f} | {m['mean_final6_hits']:.6f} | {m['mean_actual_rank']:.6f} | {m['brier_score']:.6f} | {m['log_loss']:.6f} | {joint} |"
            )
        lines += [
            "",
            "| 模型 | Final-6 0 | 1 | 2 | 3 | 4 | 5 | 6 |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for name, m in models.items():
            lines.append(
                "| "
                + name
                + " | "
                + " | ".join(str(m["final6_histogram"][str(h)]) for h in range(7))
                + " |"
            )
        lines += [
            "",
            "| 模型 | 概率箱 [下界,上界) | 数量 | 平均概率 | 实际频率 |",
            "|---|---|---:|---:|---:|",
        ]
        for name, m in models.items():
            for bin_ in m["calibration_bins"]:
                probability = (
                    "null"
                    if bin_["mean_probability"] is None
                    else f"{bin_['mean_probability']:.6f}"
                )
                observed = (
                    "null"
                    if bin_["observed_frequency"] is None
                    else f"{bin_['observed_frequency']:.6f}"
                )
                lines.append(
                    f"| {name} | [{bin_['lower']:.1f},{bin_['upper']:.1f}) | {bin_['count']} | {probability} | {observed} |"
                )
    opp = report["opportunities"]
    lines += [
        "",
        "## 机会计数",
        "",
        f"本次已评分前缀去重机会数：{opp['unique_opportunity_count']}；名义公平机会值：{opp['nominal_fair_exact6_chance']:.8g}。",
        "这只是固定计划/已观察前缀的名义记账，不是自适应停止下精确无条件概率、anytime p 值或全局显著性。",
        "跨版本重复的 V1/random 同日期同组号码不是新增的独立机会。",
        "",
        "## 全部已处理目标",
        "",
    ]
    for row in report["targets"]:
        lines += [
            f"### {row['target_draw_date']}",
            "",
            f"训练截止：{row['forecast_payload']['history_through']}；生成时间：{row['prediction_generated_at']}。",
            f"实际主号码：{row['actual']}；bonus 仅审计记录：{row['bonus']}。",
            "",
            "| 模型 | Top-6 | Top-12 | Top-18 | Final-6 | 命中 6/12/18/Final | 平均真实排名 | Brier | Log Loss |",
            "|---|---|---|---|---|---|---:|---:|---:|",
        ]
        for forecast, score in zip(
            row["forecast_payload"]["forecasts"], row["scores"], strict=True
        ):
            cells = [
                forecast["model_name"],
                forecast["top6"],
                forecast["top12"],
                forecast["top18"],
                forecast["final6"],
                f"{score['top6_hits']}/{score['top12_hits']}/{score['top18_hits']}/{score['final6_hits']}",
                f"{score['mean_actual_rank']:.6f}",
                f"{score['brier_score']:.6f}",
                f"{score['log_loss']:.6f}",
            ]
            lines.append("| " + " | ".join(_text(cell) for cell in cells) + " |")
        lines += [
            "",
            "<details><summary>全部 49 数字概率/hex、完整排名、科学状态及逐期绑定</summary>",
            "",
            "```json",
            canonical_json_bytes(row).decode("utf-8")[:-1],
            "```",
            "",
            "</details>",
            "",
        ]
    return "\n".join(lines).rstrip("\n") + "\n"
