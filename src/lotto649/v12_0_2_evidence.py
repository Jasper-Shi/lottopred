"""Pure serialization and inference for the frozen V12.0.2 diagnostic.

Nothing in this module loads history, grants execution, observes a clock, writes
an artifact, or sends a notification. The registered attempt owns those seams.
Scoring consumes the exact canonical bytes frozen before the reveal.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from datetime import date, timedelta
from functools import lru_cache
from itertools import pairwise
from typing import Any

import numpy as np

from .domain import Draw
from .models.factory import build_models
from .models.v12_parity_transition import (
    CANDIDATE_MODEL_NAME,
    CONTROL_MODEL_NAME,
    FAIR_MEAN,
    FAIR_SET_COUNT,
    PSEUDO_PARTITION_LABELS,
    PSEUDO_PARTITION_SHA256,
    STANDARDIZED_BUCKET_STATES,
    TRUE_ODD_LABELS,
    ParityForecast,
    forecast_candidate,
    forecast_control,
    tilted_moment_log_z,
)
from .optimizer import select_combination

JsonObject = dict[str, Any]
MODEL_VERSION = "v12.0.2"
EXPERIMENT_ID = "V12_0_2_historical_operational_rebinding"
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
LOG_20 = math.log(20.0)
BOOTSTRAP_SEED = 649
BOOTSTRAP_RESAMPLES = 10_000
CLASSIFICATION = "consumed_historical_diagnostic_only"
CLASSIFICATION_ZH = "历史诊断/审计候选、不可晋升"
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
    "aggregate_candidate_top12_lift_strictly_positive",
    "aggregate_candidate_four_variant_holm_adjusted_exact_p_at_most_0.05",
    "aggregate_candidate_top12_bootstrap_lower_strictly_positive",
    "candidate_top12_lift_strictly_positive_in_both_halves",
    "paired_candidate_minus_v1_top12_bootstrap_lower_strictly_positive_aggregate_and_halves",
    "candidate_minus_pseudo_top12_bootstrap_lower_strictly_positive_and_pseudo_and_random_each_exact_fair_top12_p_strictly_above_0.05_and_fixed_seed_bootstrap_top12_lift_interval_includes_zero_in_every_scope",
    "candidate_top6_lift_strictly_positive_aggregate_and_halves",
    "candidate_brier_and_log_loss_deltas_vs_fair_and_v1_at_most_1e-9_aggregate_and_halves",
    "joint_law_candidate_log_gain_at_least_log20_aggregate_positive_halves_candidate_minus_control_positive_all_scopes_control_below_log20",
    "no_audit_warning",
)
_FEATURES = {
    CANDIDATE_MODEL_NAME: "frozen_post_rng_lag_one_true_parity_composition",
    CONTROL_MODEL_NAME: "frozen_post_rng_lag_one_pseudo_parity_composition",
    ENSEMBLE_MODEL_NAME: "frozen_v1_long_recent_ema_gap_logistic_ensemble",
    RANDOM_MODEL_NAME: "frozen_v1_target_date_seeded_fair_jitter",
}
_FORECAST_KEYS = {
    "model_name",
    "model_version",
    "feature_set",
    "probabilities",
    "ranking",
    "top6",
    "top12",
    "top18",
    "final6",
    "scientific_state",
}
_STATE_KEYS = {
    "transition_count",
    "previous_bucket",
    "x_prev",
    "beta",
    "eta",
    "expected_bucket",
    "log_z",
}


def _require_json(value: object) -> None:
    if value is None or type(value) in {str, bool, int}:
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
        len(probabilities) != 49
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
        "ranking": ranking,
        "top6": ranking[:6],
        "top12": ranking[:12],
        "top18": ranking[:18],
        "final6": list(final6),
        "scientific_state": state,
    }
    _validate_forecast(result)
    return result


def serialize_parity_forecast(forecast: ParityForecast) -> JsonObject:
    if type(forecast) is not ParityForecast:
        raise ValueError("exact registered ParityForecast required")
    forecast.__post_init__()
    state = {
        "transition_count": forecast.transition_count,
        "previous_bucket": forecast.previous_bucket,
        "x_prev": forecast.x_prev,
        "beta": forecast.beta,
        "eta": forecast.eta,
        "expected_bucket": forecast.expected_bucket,
        "log_z": forecast.log_z,
    }
    return _serialize_forecast(
        forecast.model_name, dict(forecast.probabilities), forecast.final6, state
    )


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
    raw = forecast["probabilities"]
    if type(raw) is not dict or set(raw) != {str(label) for label in range(1, 50)}:
        raise ValueError("serialized probability labels mismatch")
    probabilities = _probabilities({label: raw[str(label)] for label in range(1, 50)})
    ranking = _numbers(forecast["ranking"], 49)
    if ranking != sorted(
        probabilities, key=lambda label: (-probabilities[label], label)
    ):
        raise ValueError("ranking is not probability descending and label ascending")
    for k in (6, 12, 18):
        if _numbers(forecast[f"top{k}"], k) != ranking[:k]:
            raise ValueError("Top-K is not a ranking prefix")
    final6 = _numbers(forecast["final6"], 6, sorted_set=True)
    if not set(final6) <= set(forecast["top12"]):
        raise ValueError("Final-6 is outside frozen candidate pool")
    state = forecast["scientific_state"]
    if name in MODEL_ORDER[2:]:
        if state is not None:
            raise ValueError("comparator cannot assert a parity joint law")
        return
    if (
        final6 != sorted(ranking[:6])
        or type(state) is not dict
        or set(state) != _STATE_KEYS
    ):
        raise ValueError("parity forecast state or Final-6 mismatch")
    if (
        type(state["transition_count"]) is not int
        or state["transition_count"] < 0
        or type(state["previous_bucket"]) is not int
        or not 0 <= state["previous_bucket"] <= 6
        or any(
            type(state[key]) is not float or not math.isfinite(state[key])
            for key in ("x_prev", "beta", "eta", "expected_bucket", "log_z")
        )
        or state["x_prev"] != STANDARDIZED_BUCKET_STATES[state["previous_bucket"]]
        or state["eta"] != state["beta"] * state["x_prev"]
        or (state["transition_count"] == 0 and state["beta"] != 0.0)
    ):
        raise ValueError("parity scientific state mismatch")
    if state["beta"] == 0.0:
        if state["beta"].hex() != "0x0.0p+0" or state["eta"].hex() != "0x0.0p+0":
            raise ValueError("fair bypass must use positive zero")
        mean, log_z = FAIR_MEAN, math.log(float(FAIR_SET_COUNT))
        expected = {label: FAIR_PROBABILITY for label in range(1, 50)}
    else:
        moment = tilted_moment_log_z(state["eta"])
        mean, log_z = moment.expected_bucket, moment.log_z
        selected = (
            TRUE_ODD_LABELS if name == CANDIDATE_MODEL_NAME else PSEUDO_PARTITION_LABELS
        )
        expected = {
            label: mean / 25.0 if label in selected else (6.0 - mean) / 24.0
            for label in range(1, 50)
        }
    if (
        state["expected_bucket"] != mean
        or state["log_z"] != log_z
        or probabilities != expected
    ):
        raise ValueError("frozen marginals disagree with registered joint law")


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
        v1_config.get("project", {}).get("seed") != 649
        or v1_config.get("project", {}).get("model_version") != "v1.0.0"
        or v1_config.get("prediction", {}).get("candidate_pool_size") != 12
        or v1_config.get("features", {}).get("logistic_training_draws") != 480
        or v1_config.get("features", {}).get("min_logistic_samples") != 300
    ):
        raise ValueError("V1 comparator configuration differs from frozen registration")
    models = build_models(v1_config, requested=["ensemble", "random"])
    return [
        serialize_parity_forecast(forecast_candidate(history, target_date)),
        serialize_parity_forecast(forecast_control(history, target_date)),
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


def _validated_frozen_payload(frozen_payload: bytes) -> JsonObject:
    payload = decode_canonical_json(frozen_payload)
    if type(payload) is not dict:
        raise ValueError("frozen payload must be an object")
    target = _date(payload.get("target_draw_date"))
    if _date(payload.get("history_through")) >= target:
        raise ValueError("visible-history chronology mismatch")
    forecasts = payload.get("forecasts")
    if type(forecasts) is not list or len(forecasts) != 4:
        raise ValueError("four complete frozen forecasts required")
    for forecast in forecasts:
        _validate_forecast(forecast)
    if tuple(forecast["model_name"] for forecast in forecasts) != MODEL_ORDER:
        raise ValueError("registered four-model order mismatch")
    if (
        forecasts[0]["scientific_state"]["transition_count"]
        != forecasts[1]["scientific_state"]["transition_count"]
    ):
        raise ValueError("candidate and control transition counts differ")
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
            selected = (
                TRUE_ODD_LABELS
                if name == CANDIDATE_MODEL_NAME
                else PSEUDO_PARTITION_LABELS
            )
            bucket = sum(label in selected for label in main)
            gain = (
                0.0
                if state["beta"] == 0.0
                else LOG_N + state["beta"] * state["x_prev"] * bucket - state["log_z"]
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
        "cumulative_unique_opportunity_count": sum(counts),
        "cumulative_fair_probability": chance,
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
    for row in result:
        if type(row) is not dict:
            raise ValueError("scored row must be an object")
        target = _date(row.get("target_draw_date"))
        if previous is not None and target <= previous:
            raise ValueError("scored rows must be strictly chronological")
        previous = target
        actual = _numbers(row.get("actual"), 6, sorted_set=True)
        recomputed = score_target(
            canonical_json_bytes(row["forecast_payload"]),
            Draw(target, tuple(actual), row.get("bonus")),
        )
        if any(row.get(key) != value for key, value in recomputed.items()):
            raise ValueError("scored row disagrees with its frozen payload")
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
    for name, model_index in (("candidate_minus_v1", 2), ("candidate_minus_pseudo", 1)):
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
    """Summarize any synthetic scope; the report builder enforces fixed dates."""
    return _scope_summary(_validated_rows(rows))


def _audit_inputs(
    audit_complete: bool, audit_warnings: Sequence[str]
) -> tuple[str, ...]:
    if type(audit_complete) is not bool or isinstance(audit_warnings, (str, bytes)):
        raise ValueError("explicit audit completeness and warning list required")
    warnings = tuple(audit_warnings)
    if any(type(warning) is not str or not warning for warning in warnings):
        raise ValueError("audit warnings must be nonempty text")
    return warnings


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
    aggregate = scopes["aggregate"]
    candidate = aggregate["models"][CANDIDATE_MODEL_NAME]
    p_vector = (1.0, 1.0, 0.9783404732169021, candidate["top12_exact_p"]["value"])
    corrected_p = holm_adjusted(p_vector)[3]
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
            scope["contrasts"]["candidate_minus_pseudo"]["top12_paired_ci95"]["lower"]
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
            scope["contrasts"]["candidate_minus_pseudo"]["joint_log_gain_sum"] > 0.0
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
    if type(bindings) is not dict or (
        stop_reason is not None and (type(stop_reason) is not str or not stop_reason)
    ):
        raise ValueError("report bindings or stop reason is invalid")
    _require_json(bindings)
    observed = _validated_rows(rows) if rows else ()
    expected = _registered_dates()
    dates = tuple(row["target_draw_date"] for row in observed)
    if dates != expected[: len(dates)]:
        raise ValueError("report targets are not the registered chronological prefix")
    exact_hits = [
        row["target_draw_date"] for row in observed if row["exact_final6_opportunities"]
    ]
    if exact_hits and (len(exact_hits) != 1 or exact_hits[0] != dates[-1]):
        raise ValueError("forecasting continued after an exact Final-6 detection")
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
            scopes["aggregate"]["models"][CANDIDATE_MODEL_NAME]["top12_exact_p"][
                "value"
            ],
        ]
        multiplicity = {
            "family": "transition_markov",
            "variant_index": 4,
            "input_vector": vector,
            "adjusted_vector": list(holm_adjusted(vector)),
        }
    if (
        exact_hits
        and stop_reason == "exact_final6_pending_independent_audit"
        and not warnings
    ):
        disposition = "pending_audit"
    elif not complete or not audit_complete or warnings:
        disposition = "Archive"
    elif all(gate["passed"] for gate in gates):
        disposition = "consumed_diagnostic_all_gates_pass"
    else:
        disposition = "Reject"
    annual: JsonObject = {}
    for year in sorted({value[:4] for value in dates}):
        subset = [
            row for row in observed if row["target_draw_date"].startswith(year + "-")
        ]
        annual[year] = {
            name: _model_summary(subset, index, inference=False)
            for index, name in enumerate(MODEL_ORDER)
        }
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
        "schema_version": "lotto649.v12.0.2.historical-diagnostic-report.v1",
        "experiment_id": EXPERIMENT_ID,
        "model_version": MODEL_VERSION,
        "seed": 649,
        "classification": CLASSIFICATION,
        "classification_zh": CLASSIFICATION_ZH,
        "statistical_fingerprint_sha256": "af2e16a55ff0e817cf71208471e19e4f481bed63990f7e41268997c4c4b35c76",
        "required_pure_core_sha256": "fae93e0a6f76c6604eabe24f6b93676e22e87d7e567365b382484433fba2eb77",
        "primary_metric": "mean_top12_main_number_hits_minus_72_over_49",
        "pseudo_control": {
            "model_name": CONTROL_MODEL_NAME,
            "role": "fixed_sanity_control_not_discovery",
            "selected_labels": sorted(PSEUDO_PARTITION_LABELS),
            "partition_sha256": PSEUDO_PARTITION_SHA256,
            "true_pseudo_label_contingency": [[10, 15], [15, 9]],
            "label_correlation_with_true_parity": "-9/40",
            "independent_of_true_parity": False,
        },
        "eligible_evidence": False,
        "promotion_authority": False,
        "complete_registered_scope": complete,
        "expected_target_count": 627,
        "processed_target_count": len(observed),
        "disposition": disposition,
        "stop_reason": stop_reason,
        "bindings": bindings,
        "audit": {"complete": audit_complete, "warnings": list(warnings)},
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
    """Render every processed target; no best-date filtering or future advice."""
    _require_json(report)
    lines = [
        "# V12.0.2 历史严格回测诊断",
        "",
        CLASSIFICATION_ZH,
        "",
        f"状态：{report['disposition']}；已评分 {report['processed_target_count']}/627 期。",
        "2020–2025 是已消耗的历史诊断数据；彩票公平且不可预测是默认解释。",
        "这些结果不具备晋升或未来购票建议的效力。",
        "",
        "## 审计与身份",
        "",
        "```json",
        canonical_json_bytes({"bindings": report["bindings"], "audit": report["audit"]})
        .decode("utf-8")
        .rstrip(),
        "```",
        "",
        "## 公平理论基准",
        "",
        "| Top‑6 | Top‑12 | Top‑18 | 单一 Final‑6 的 6/6 概率 |",
        "|---:|---:|---:|---:|",
        "| 36/49 | 72/49 | 108/49 | 1/13,983,816 |",
        "",
    ]
    if report["gates"] is None:
        lines += [
            "此次没有完整的 627 期十项 gates 报告；未运行的目标没有预测或评分。",
            "",
        ]
    else:
        lines += [
            "## 三个固定区间",
            "",
            "| 区间 | 模型 | n | Top‑6 | Top‑12 | Top‑18 | Brier | Log Loss | Top‑12 exact p | 95% lift CI |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
        ]
        for scope_name in SCOPE_ORDER:
            scope = report["scopes"][scope_name]
            for name in MODEL_ORDER:
                model = scope["models"][name]
                interval = model["top12_lift_ci95"]
                lines.append(
                    f"| {scope_name} | {name} | {scope['n']} | {model['mean_top6_hits']:.12g} | {model['mean_top12_hits']:.12g} | {model['mean_top18_hits']:.12g} | {model['brier_score']:.12g} | {model['log_loss']:.12g} | {model['top12_exact_p']['value']:.12g} | [{interval['lower']:.12g}, {interval['upper']:.12g}] |"
                )
        lines += ["", "## 十项 gates", "", "| # | 注册 gate | 通过 |", "|---:|---|---|"]
        lines += [
            f"| {gate['number']} | {gate['name']} | {gate['passed']} |"
            for gate in report["gates"]
        ]
    lines += [
        "",
        "## 全部已处理目标",
        "",
        "完整 1–49 概率、排名、各预测摘要及逐期审计绑定保存在同名 JSON 报告的 targets 中。",
        "年度描述、含空箱的十箱 calibration、Final‑6 的 0–6 分布、全部最佳命中日期和控制组对比也保存在该 JSON 中。",
        "",
        "| 目标日 | 训练截止 | 模型 | Top‑6 | Top‑12 | Top‑18 | Final‑6 | 实际号码 | 命中 6/12/18/Final |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for row in report["targets"]:
        for forecast, score in zip(
            row["forecast_payload"]["forecasts"], row["scores"], strict=True
        ):
            cells = [
                row["target_draw_date"],
                row["forecast_payload"]["history_through"],
                forecast["model_name"],
                forecast["top6"],
                forecast["top12"],
                forecast["top18"],
                forecast["final6"],
                row["actual"],
                f"{score['top6_hits']}/{score['top12_hits']}/{score['top18_hits']}/{score['final6_hits']}",
            ]
            lines.append("| " + " | ".join(_text(cell) for cell in cells) + " |")
    return "\n".join(lines) + "\n"
