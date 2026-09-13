"""Registered, manual V1 diagnostic; no production, V12, draw-source network or email actions."""

from __future__ import annotations

# Restart the fixed manual entry before importing packages or local model code.
import os
import sys

if __name__ == "__main__" and not (
    sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
):
    environment = {
        "PATH": "/usr/bin:/bin",
        "LANG": "C",
        "LC_ALL": "C",
        "TMPDIR": "/tmp",
        "GIT_CONFIG_COUNT": "0",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_SYSTEM": "/dev/null",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_NO_LAZY_FETCH": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_GRAFT_FILE": "/dev/null",
    }
    if "GH_TOKEN" in os.environ:
        environment["GH_TOKEN"] = os.environ["GH_TOKEN"]
    os.execve(
        sys.executable,
        [sys.executable, "-I", "-S", "-B", os.path.abspath(__file__), *sys.argv[1:]],
        environment,
    )

import argparse
import hashlib
import importlib.metadata
import json
import math
import platform
import re
import subprocess
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, date, datetime, timedelta
from functools import lru_cache
from pathlib import Path

EXPERIMENT = "V1_ensemble_verified_history_diagnostic_20260913"
BASE_COMMIT = "40f6e4098d4ed59f9421196efb8573c66c48928a"
REGISTRATION = "evidence/research_registrations/v1-ensemble-verified-history-diagnostic-20260913.json"
OUTPUT = "reports/v1_ensemble_verified_history_diagnostic_20260913"
REMOTE_REF = "refs/heads/v1-ensemble-history-consumed-20260913"
PRODUCERS = ("ensemble_v1.0.0", "random_v1.0.0", "label_permuted_ensemble_v1.0.0")
METRICS = ("top6", "top12", "top18", "final6")
FAIR = 6 / 49
SEED = 649
ZERO_HASH = "0" * 64


class DiagnosticError(ValueError):
    """Invalid inputs or permanent one-shot failure; never an instruction to retry."""


def canonical(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode()


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def sync_directory(directory: Path) -> None:
    fd = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def exclusive_json(path: Path, value: object) -> str:
    raw = canonical(value)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o444)
    with os.fdopen(fd, "wb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    sync_directory(path.parent)
    return digest(raw)


class Ledger:
    def __init__(self, directory: Path, clock: Callable[[], str]):
        self.path = directory / "ledger.jsonl"
        fd = os.open(
            self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o444
        )
        self.handle = os.fdopen(fd, "wb")
        self.sequence, self.previous, self.clock = 0, ZERO_HASH, clock
        self.poisoned = False
        sync_directory(directory)

    def append(self, kind: str, payload: dict) -> dict:
        if self.poisoned:
            raise DiagnosticError("ledger durability failed; no retry")
        event = {
            "sequence": self.sequence,
            "previous_sha256": self.previous,
            "recorded_at": self.clock(),
            "kind": kind,
            "payload": payload,
        }
        event["event_sha256"] = digest(canonical(event))
        try:
            self.handle.write(canonical(event))
            self.handle.flush()
            os.fsync(self.handle.fileno())
        except BaseException:
            self.poisoned = True
            raise
        self.sequence += 1
        self.previous = event["event_sha256"]
        return event

    def close(self) -> None:
        self.handle.close()


def validate_probabilities(probabilities: Mapping[int, float]) -> dict[int, float]:
    if set(probabilities) != set(range(1, 50)) or any(
        type(n) is not int for n in probabilities
    ):
        raise DiagnosticError("probabilities must contain exactly integer labels 1..49")
    result = {n: float(probabilities[n]) for n in range(1, 50)}
    if any(not math.isfinite(p) or not 0 < p < 1 for p in result.values()):
        raise DiagnosticError(
            "probabilities must be finite and strictly between zero and one"
        )
    if not math.isclose(math.fsum(result.values()), 6, rel_tol=0, abs_tol=1e-9):
        raise DiagnosticError("probabilities must sum to six")
    return result


def probability_payload(probabilities: Mapping[int, float]) -> dict:
    from lotto649.optimizer import rank_numbers, select_combination

    probabilities = validate_probabilities(probabilities)
    ranked = rank_numbers(probabilities)
    return {
        "probabilities": {str(n): probabilities[n] for n in range(1, 50)},
        "ranking": ranked,
        "top6": ranked[:6],
        "top12": ranked[:12],
        "top18": ranked[:18],
        "final6": select_combination(probabilities, 12),
    }


def label_permuted(
    probabilities: Mapping[int, float], target: date
) -> dict[int, float]:
    import numpy as np

    labels = np.random.default_rng(SEED + target.toordinal()).permutation(range(1, 50))
    return {int(label): probabilities[n] for n, label in enumerate(labels, 1)}


def draw_record(draw: object) -> dict:
    from lotto649.domain import Draw

    if type(draw) is not Draw or type(draw.draw_date) is not date:
        raise DiagnosticError("expected a validated Draw")
    return {
        "draw_date": draw.draw_date.isoformat(),
        "numbers": list(draw.numbers),
        "bonus": draw.bonus,
    }


def score(prediction: dict, actual: object) -> dict:
    from lotto649.evaluation import binary_log_loss, brier_score, mean_actual_rank

    draw = draw_record(actual)
    if prediction["target_date"] != draw["draw_date"]:
        raise DiagnosticError("reveal target mismatch")
    probabilities = validate_probabilities(
        {int(n): p for n, p in prediction["probabilities"].items()}
    )
    if any(
        prediction[key] != value
        for key, value in probability_payload(probabilities).items()
    ):
        raise DiagnosticError("prediction probabilities and ranking disagree")
    numbers = set(draw["numbers"])
    return {
        "producer": prediction["producer"],
        "hits": {key: len(numbers.intersection(prediction[key])) for key in METRICS},
        "brier": brier_score(probabilities, actual.numbers),
        "binary_log_loss": binary_log_loss(probabilities, actual.numbers),
        "mean_actual_rank": mean_actual_rank(probabilities, actual.numbers),
    }


def opportunity_summary(rows: Sequence[dict]) -> dict:
    counts = [row["unique_opportunity_count"] for row in rows]
    return {
        "per_target_unique_counts": counts,
        "cumulative_count": sum(counts),
        "fair_probability_at_least_one_final6": -math.expm1(
            math.fsum(math.log1p(-count / math.comb(49, 6)) for count in counts)
        ),
        "includes_controls": True,
        "fair_baseline_is_not_an_extra_ticket": True,
    }


def target_dates() -> list[date]:
    current, result = date(2020, 1, 1), []
    while current <= date(2025, 12, 31):
        if current.weekday() in (2, 5):
            result.append(current)
        current += timedelta(days=1)
    return result


def _new_directory(directory: Path) -> None:
    if any(parent.is_symlink() for parent in (directory, *directory.parents)):
        raise DiagnosticError("output parent contains a symlink")
    directory.mkdir(mode=0o700, parents=False, exist_ok=False)
    sync_directory(directory.parent)
    (directory / "predictions").mkdir()
    (directory / "evaluations").mkdir()
    sync_directory(directory)


def _sequence(
    directory: Path,
    targets: Sequence[date],
    prefix_for: Callable,
    reveal: Callable,
    forecast: Callable,
    bindings: dict,
    clock: Callable,
    *,
    check_sources: Callable = lambda: None,
) -> dict:
    if (
        not targets
        or any(type(t) is not date for t in targets)
        or list(targets) != sorted(set(targets))
    ):
        raise DiagnosticError("targets must be nonempty and strictly increasing")
    ledger = Ledger(directory, clock)
    rows, stopped = [], False
    try:
        ledger.append(
            "claim_bound",
            {"claim_sha256": digest((directory / "claim.json").read_bytes())},
        )
        check_sources()
        for target in targets:
            prefix = list(prefix_for(target))
            records = [draw_record(draw) for draw in prefix]
            dates = [draw.draw_date for draw in prefix]
            if not dates or dates != sorted(set(dates)) or dates[-1] >= target:
                raise DiagnosticError(
                    "prefix contains target/future, duplicates or is empty"
                )
            prefix_hash = digest(canonical(records))
            probabilities = forecast(tuple(prefix), target)
            if set(probabilities) != set(PRODUCERS):
                raise DiagnosticError("exactly three registered producers required")
            # Validate all producers before freezing any of this target's snapshots.
            payloads = {
                name: probability_payload(probabilities[name]) for name in PRODUCERS
            }
            snapshots, frozen = {}, {}
            for name in PRODUCERS:
                payload = {
                    **payloads[name],
                    "experiment_id": EXPERIMENT,
                    "algorithm_version": "v1.0.0",
                    "experiment_version": 1,
                    "producer": name,
                    "target_date": target.isoformat(),
                    "training_cutoff": dates[-1].isoformat(),
                    "history_draw_count": len(prefix),
                    "visible_prefix_sha256": prefix_hash,
                    "generated_at": clock(),
                    "seed": SEED,
                    "bindings": bindings,
                }
                relative = f"predictions/{target.isoformat()}__{name}.json"
                frozen[name] = {
                    "path": relative,
                    "sha256": exclusive_json(directory / relative, payload),
                }
                snapshots[name] = payload
            ledger.append(
                "prediction_frozen",
                {"target_date": target.isoformat(), "snapshots": frozen},
            )
            # This is the first point at which the target's actual Draw may be requested.
            actual = reveal(target)
            actual_record = draw_record(actual)
            scores = {name: score(snapshots[name], actual) for name in PRODUCERS}
            unique = {tuple(snapshots[name]["final6"]) for name in PRODUCERS}
            exact = [name for name in PRODUCERS if scores[name]["hits"]["final6"] == 6]
            row = {
                "target_date": target.isoformat(),
                "actual": actual_record,
                "predictions": snapshots,
                "scores": scores,
                "snapshots": frozen,
                "unique_opportunity_count": len(unique),
                "exact_final6_producers": exact,
            }
            relative = f"evaluations/{target.isoformat()}.json"
            evaluation_hash = exclusive_json(directory / relative, row)
            ledger.append(
                "target_revealed_scored",
                {
                    "target_date": target.isoformat(),
                    "path": relative,
                    "sha256": evaluation_hash,
                },
            )
            rows.append(row)
            if bindings["classification"] != "synthetic_fixture_only" and (
                len(rows) % 25 == 0 or len(rows) == len(targets)
            ):
                print(
                    f"Scored {len(rows)}/{len(targets)} targets through {target.isoformat()}",
                    flush=True,
                )
            if exact:
                stopped = True
                ledger.append(
                    "final6_candidate_detected",
                    {
                        "target_date": target.isoformat(),
                        "producers": exact,
                        "independent_leakage_audit": "pending",
                        "notification": "pending_default_route_by_operator",
                    },
                )
                break
        check_sources()
        report = build_report(
            rows, expected_count=len(targets), stopped=stopped, bindings=bindings
        )
        report["ledger_head_sha256"] = ledger.previous
        exclusive_json(directory / "report.json", report)
        markdown = render_markdown(report).encode()
        fd = os.open(
            directory / "report.md", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444
        )
        with os.fdopen(fd, "wb") as handle:
            handle.write(markdown)
            handle.flush()
            os.fsync(handle.fileno())
        sync_directory(directory)
        return report
    finally:
        ledger.close()


def run_synthetic(
    directory: Path,
    fixtures: Sequence[object],
    forecast: Callable,
    *,
    clock: Callable = lambda: "2000-01-01T00:00:00Z",
) -> dict:
    """Synthetic-only test seam; never imports or accepts a real-history loader."""
    if "reports" in directory.parts or len(fixtures) < 2:
        raise DiagnosticError(
            "synthetic output must be outside research reports with a prefix"
        )
    _new_directory(directory)
    bindings = {
        "classification": "synthetic_fixture_only",
        "source_git_commit": "synthetic",
        "expected_target_count": len(fixtures) - 1,
        "synthetic_target_dates": [d.draw_date.isoformat() for d in fixtures[1:]],
    }
    exclusive_json(directory / "claim.json", bindings)
    positions = {draw.draw_date: i for i, draw in enumerate(fixtures)}
    return _sequence(
        directory,
        [draw.draw_date for draw in fixtures[1:]],
        lambda target: fixtures[: positions[target]],
        lambda target: fixtures[positions[target]],
        forecast,
        bindings,
        clock,
    )


def fair_moments(k: int) -> dict:
    return {"mean": 6 * k / 49, "variance": 6 * (k / 49) * (1 - k / 49) * 43 / 48}


@lru_cache(maxsize=64)
def null_distribution(n: int, k: int):
    import numpy as np

    if type(n) is not int or n < 1 or k not in (6, 12, 18):
        raise DiagnosticError("invalid finite fair null scope")
    kernel = np.array(
        [
            math.comb(k, j) * math.comb(49 - k, 6 - j) / math.comb(49, 6)
            for j in range(7)
        ]
    )
    distribution = np.array([1.0])
    for _ in range(n):
        distribution = np.convolve(distribution, kernel)
    return distribution


def exact_upper_tail(n: int, k: int, observed: int) -> float:
    if type(observed) is not int or not 0 <= observed <= 6 * n:
        raise DiagnosticError("invalid observed total")
    return min(1.0, float(math.fsum(null_distribution(n, k)[observed:])))


def holm(pvalues: Sequence[float]) -> list[float]:
    ordered = sorted(range(len(pvalues)), key=lambda i: (pvalues[i], i))
    result, previous = [0.0] * len(pvalues), 0.0
    for rank, index in enumerate(ordered):
        previous = max(previous, min(1.0, (len(pvalues) - rank) * pvalues[index]))
        result[index] = previous
    return result


def bootstrap_indices(n: int):
    import numpy as np

    if n < 1:
        raise DiagnosticError("bootstrap requires rows")
    rng = np.random.default_rng(SEED)
    starts = rng.integers(0, n, size=(2000, math.ceil(n / 12)))
    return ((starts[:, :, None] + np.arange(12)) % n).reshape(2000, -1)[:, :n]


def calibration(rows: Sequence[dict], producer: str) -> list[dict]:
    bins = [
        {
            "lower": i / 10,
            "upper": (i + 1) / 10,
            "count": 0,
            "probability_sum": 0.0,
            "positive_count": 0,
        }
        for i in range(10)
    ]
    for row in rows:
        actual = set(row["actual"]["numbers"])
        probabilities = row["predictions"][producer]["probabilities"]
        for number in map(str, range(1, 50)):
            probability = probabilities[number]
            bucket = bins[min(9, int(probability * 10))]
            bucket["count"] += 1
            bucket["probability_sum"] += probability
            bucket["positive_count"] += int(int(number) in actual)
    for bucket in bins:
        count = bucket["count"]
        bucket["mean_probability"] = (
            bucket["probability_sum"] / count if count else None
        )
        bucket["observed_frequency"] = (
            bucket["positive_count"] / count if count else None
        )
    return bins


def scope_summary(rows: Sequence[dict], *, inference: bool) -> dict:
    import numpy as np

    if not rows:
        return {"target_count": 0, "producers": {}, "paired_difference_ci95": None}
    arrays = {
        name: np.array(
            [[row["scores"][name]["hits"][key] for key in METRICS] for row in rows],
            dtype=float,
        )
        for name in PRODUCERS
    }
    indices = bootstrap_indices(len(rows)) if inference else None
    result = {"target_count": len(rows), "producers": {}, "paired_difference_ci95": {}}
    for name in PRODUCERS:
        scores = [row["scores"][name] for row in rows]
        best = max(item["hits"]["final6"] for item in scores)
        summary = {
            "mean_hits": dict(zip(METRICS, arrays[name].mean(axis=0).tolist())),
            "final6_distribution": {
                str(i): sum(s["hits"]["final6"] == i for s in scores) for i in range(7)
            },
            "best_final6_hits": best,
            "all_best_dates": [
                row["target_date"]
                for row in rows
                if row["scores"][name]["hits"]["final6"] == best
            ],
            "mean_brier": math.fsum(s["brier"] for s in scores) / len(rows),
            "mean_binary_log_loss": math.fsum(s["binary_log_loss"] for s in scores)
            / len(rows),
            "calibration": calibration(rows, name),
            "fair_null_p": None,
            "holm_3_topk_p": None,
            "mean_hit_ci95": None,
        }
        summary["primary_top12_lift"] = summary["mean_hits"]["top12"] - 72 / 49
        if inference:
            pvalues = [
                exact_upper_tail(len(rows), k, int(arrays[name][:, i].sum()))
                for i, k in enumerate((6, 12, 18))
            ]
            summary["fair_null_p"] = dict(zip(METRICS[:3], pvalues))
            summary["holm_3_topk_p"] = dict(zip(METRICS[:3], holm(pvalues)))
            intervals = np.quantile(
                arrays[name][indices].mean(axis=1),
                [0.025, 0.975],
                axis=0,
                method="linear",
            ).T.tolist()
            summary["mean_hit_ci95"] = dict(zip(METRICS, intervals))
        result["producers"][name] = summary
    if inference:
        for control in PRODUCERS[1:]:
            delta = arrays[PRODUCERS[0]] - arrays[control]
            intervals = np.quantile(
                delta[indices].mean(axis=1), [0.025, 0.975], axis=0, method="linear"
            ).T.tolist()
            result["paired_difference_ci95"][control] = dict(zip(METRICS, intervals))
    return result


def build_report(
    rows: Sequence[dict], *, expected_count: int, stopped: bool, bindings: dict
) -> dict:
    complete = len(rows) == expected_count
    split = 314 if expected_count == 627 else math.ceil(expected_count / 2)
    return {
        "experiment_id": EXPERIMENT,
        "algorithm_version": "v1.0.0",
        "experiment_version": 1,
        "classification": bindings["classification"],
        "eligible_for_promotion": False,
        "expected_target_count": expected_count,
        "scored_target_count": len(rows),
        "complete_fixed_cohort": complete,
        "partial": not complete,
        "stopped_on_first_final6": stopped,
        "independent_leakage_audit": "pending" if stopped else "not_triggered",
        "notification": "pending_default_route_by_operator"
        if stopped
        else "not_triggered",
        "control_hit_does_not_prove_candidate_advantage": True,
        "inference": {
            "interpretation": "consumed historical diagnostic only; no promotion",
            "p_method": "finite sum-hypergeometric upper tail by floating convolution",
            "holm_family": "three Top-K p-values per producer per scope; not global correction",
            "bootstrap": {
                "method": "circular moving blocks",
                "block_length": 12,
                "replicates": 2000,
                "seed": SEED,
                "quantiles": "linear",
            },
            "fixed_cohort_inference_available": complete,
        },
        "fair": {
            "topk": {str(k): fair_moments(k) for k in (6, 12, 18)},
            "brier": FAIR * (1 - FAIR),
            "binary_log_loss": -FAIR * math.log(FAIR) - (1 - FAIR) * math.log1p(-FAIR),
        },
        "opportunities": opportunity_summary(rows),
        "bindings": bindings,
        "scopes": {
            "aggregate": scope_summary(rows, inference=complete),
            "first_half": scope_summary(rows[:split], inference=complete),
            "second_half": scope_summary(rows[split:], inference=complete),
        },
        "rows": list(rows),
    }


def render_markdown(report: dict) -> str:
    lines = [
        "# V1 ensemble verified-history diagnostic",
        "",
        "Consumed historical diagnostic; no promotion or future-winning claim.",
        f"Model: v1.0.0; experiment version: 1; scored: {report['scored_target_count']}/{report['expected_target_count']}.",
        f"Partial: {report['partial']}; independent leakage audit: {report['independent_leakage_audit']}.",
        "",
        "| Producer | Mean Top-6 | Mean Top-12 | Mean Top-18 | Mean Final-6 | Best Final-6 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name in PRODUCERS:
        summary = report["scopes"]["aggregate"]["producers"][name]
        means = summary["mean_hits"]
        lines.append(
            f"| {name} | "
            + " | ".join(f"{means[key]:.6f}" for key in METRICS)
            + f" | {summary['best_final6_hits']} |"
        )
    lines += [
        "",
        "All dates, 49 probabilities and rankings, calibration, null p-values, Holm adjustments,",
        "block-bootstrap intervals, both fixed halves and all best-date ties are in report.json.",
        "Controls count as opportunities; a control hit does not show ensemble superiority.",
        f"Unique opportunities: {report['opportunities']['cumulative_count']}.",
        "",
    ]
    return "\n".join(lines)


def _read_json(path: Path) -> dict:
    raw = path.read_bytes()
    value = json.loads(raw)
    if canonical(value) != raw:
        raise DiagnosticError("noncanonical or duplicate-key JSON")
    return value


def verify(directory: Path) -> dict:
    """Read-only chronology/hash verification; does not import any history loader."""
    previous, pending, scored, stopped = ZERO_HASH, None, 0, False
    rows, needs_stop = [], []
    claim = _read_json(directory / "claim.json")
    expected_dates = claim.get(
        "synthetic_target_dates", [t.isoformat() for t in target_dates()]
    )
    events = (directory / "ledger.jsonl").read_bytes().splitlines(keepends=True)
    for sequence, raw in enumerate(events):
        event = json.loads(raw)
        signature = event.pop("event_sha256")
        if (
            canonical({**event, "event_sha256": signature}) != raw
            or event["sequence"] != sequence
            or event["previous_sha256"] != previous
            or digest(canonical(event)) != signature
            or stopped
        ):
            raise DiagnosticError("ledger chronology/hash mismatch")
        previous = signature
        kind, payload = event["kind"], event["payload"]
        if sequence == 0:
            if kind != "claim_bound" or payload["claim_sha256"] != digest(
                canonical(claim)
            ):
                raise DiagnosticError("claim binding mismatch")
        elif kind == "prediction_frozen":
            if (
                pending is not None
                or needs_stop
                or set(payload["snapshots"]) != set(PRODUCERS)
                or scored >= len(expected_dates)
                or payload["target_date"] != expected_dates[scored]
            ):
                raise DiagnosticError("unpaired forecast")
            pending = payload
            for name, record in payload["snapshots"].items():
                expected = f"predictions/{payload['target_date']}__{name}.json"
                if record["path"] != expected:
                    raise DiagnosticError("snapshot path mismatch")
                prediction = _read_json(directory / expected)
                if (
                    digest(canonical(prediction)) != record["sha256"]
                    or prediction["bindings"] != claim
                    or prediction["producer"] != name
                    or prediction["target_date"] != payload["target_date"]
                    or prediction["training_cutoff"] >= prediction["target_date"]
                ):
                    raise DiagnosticError("snapshot digest/binding mismatch")
        elif kind == "target_revealed_scored":
            if pending is None or payload["target_date"] != pending["target_date"]:
                raise DiagnosticError("reveal precedes its durable forecast")
            expected = f"evaluations/{payload['target_date']}.json"
            if payload["path"] != expected:
                raise DiagnosticError("evaluation path mismatch")
            row = _read_json(directory / expected)
            if (
                digest(canonical(row)) != payload["sha256"]
                or row["snapshots"] != pending["snapshots"]
            ):
                raise DiagnosticError("evaluation digest mismatch")
            from lotto649.domain import Draw

            actual = row["actual"]
            draw = Draw(
                date.fromisoformat(actual["draw_date"]),
                tuple(actual["numbers"]),
                actual["bonus"],
            )
            for name in PRODUCERS:
                stored = _read_json(directory / pending["snapshots"][name]["path"])
                if (
                    stored != row["predictions"][name]
                    or score(stored, draw) != row["scores"][name]
                ):
                    raise DiagnosticError("evaluation score/payload mismatch")
            needs_stop = [
                name for name in PRODUCERS if row["scores"][name]["hits"]["final6"] == 6
            ]
            unique = {tuple(row["predictions"][name]["final6"]) for name in PRODUCERS}
            if (
                row["unique_opportunity_count"] != len(unique)
                or row["exact_final6_producers"] != needs_stop
            ):
                raise DiagnosticError(
                    "opportunity or exact-hit classification mismatch"
                )
            rows.append(row)
            pending, scored = None, scored + 1
        elif kind == "final6_candidate_detected":
            if (
                pending is not None
                or not needs_stop
                or payload["producers"] != needs_stop
                or payload["target_date"] != rows[-1]["target_date"]
            ):
                raise DiagnosticError("candidate detection precedes scoring")
            stopped = True
        else:
            raise DiagnosticError("unexpected ledger event")
    if not events or pending is not None or bool(needs_stop) != stopped:
        raise DiagnosticError("incomplete ledger; preserve and do not retry")
    report = _read_json(directory / "report.json")
    recomputed = build_report(
        rows,
        expected_count=claim["expected_target_count"],
        stopped=stopped,
        bindings=claim,
    )
    recomputed["ledger_head_sha256"] = previous
    if report != recomputed or (directory / "report.md").read_text() != render_markdown(
        report
    ):
        raise DiagnosticError("report ledger binding mismatch")
    return {
        "event_count": len(events),
        "scored_target_count": scored,
        "ledger_head_sha256": previous,
        "stopped_on_first_final6": stopped,
    }


class GitHubMetadataAPI:
    """Fixed GitHub metadata transport; no redirects, proxy overrides or retries."""

    def __init__(self):
        from urllib.request import HTTPRedirectHandler, ProxyHandler, build_opener

        token = os.environ.get("GH_TOKEN", "")
        if not token or len(token) > 512 or any(c.isspace() for c in token):
            raise DiagnosticError("GitHub authentication unavailable")

        class NoRedirect(HTTPRedirectHandler):
            def redirect_request(self, *args, **kwargs):
                raise DiagnosticError("GitHub redirect prohibited")

        self._token = token
        self._opener = build_opener(ProxyHandler({}), NoRedirect())
        self.guard_started = False

    def request(
        self, method: str, endpoint: str, body: dict | None = None
    ) -> tuple[int, dict]:
        from urllib.error import HTTPError
        from urllib.request import Request

        allowed = {
            "/git/ref/heads/main",
            "/git/ref/heads/" + REMOTE_REF.removeprefix("refs/heads/"),
            "/git/refs",
        }
        if endpoint not in allowed or method not in ("GET", "POST"):
            raise DiagnosticError("unregistered GitHub metadata operation")
        request = Request(
            "https://api.github.com/repos/Jasper-Shi/lottopred" + endpoint,
            data=canonical(body) if body is not None else None,
            method=method,
            headers={
                "Authorization": "Bearer " + self._token,
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "Content-Type": "application/json",
            },
        )
        try:
            try:
                response = self._opener.open(request, timeout=30)
            except HTTPError as error:
                response = error
            with response:
                status, raw = response.code, response.read(2_000_001)
            if len(raw) > 2_000_000:
                raise DiagnosticError("oversized GitHub response")
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                raise DiagnosticError("invalid GitHub response")
            return status, payload
        except Exception:  # noqa: BLE001 -- authenticated exceptions must not escape.
            raise DiagnosticError(
                "GitHub metadata operation failed; no retry"
            ) from None


def run_once_remote_guard(api: object, source_head: str) -> None:
    """Consume one independent V1 ref after exact 404; never a V12 lease."""
    if len(source_head) != 40 or any(c not in "0123456789abcdef" for c in source_head):
        raise DiagnosticError("complete source SHA required")
    if getattr(api, "guard_started", False):
        raise DiagnosticError("one-shot guard already started; no retry")
    api.guard_started = True
    status, main = api.request("GET", "/git/ref/heads/main")
    if (
        status != 200
        or not isinstance(main.get("object"), dict)
        or main["object"].get("sha") != source_head
        or main["object"].get("type") != "commit"
    ):
        raise DiagnosticError("remote main is not the reviewed source HEAD")
    endpoint = "/git/ref/heads/" + REMOTE_REF.removeprefix("refs/heads/")
    status, absence = api.request("GET", endpoint)
    if status != 404 or absence.get("message") != "Not Found":
        raise DiagnosticError("consumption ref absent-state unproven; no retry")
    status, created = api.request(
        "POST", "/git/refs", {"ref": REMOTE_REF, "sha": source_head}
    )

    def exact_ref(payload):
        return (
            payload.get("ref") == REMOTE_REF
            and isinstance(payload.get("object"), dict)
            and payload["object"].get("type") == "commit"
            and payload["object"].get("sha") == source_head
        )

    if status != 201 or not exact_ref(created):
        raise DiagnosticError("consumption ref creation uncertain; no retry")
    status, observed = api.request("GET", endpoint)
    if status != 200 or not exact_ref(observed):
        raise DiagnosticError("consumption ref reread uncertain; no retry")


def git(root: Path, *arguments: str) -> bytes:
    environment = {
        "PATH": "/usr/bin:/bin",
        "LANG": "C",
        "LC_ALL": "C",
        "GIT_CONFIG_COUNT": "0",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_SYSTEM": "/dev/null",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_NO_LAZY_FETCH": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_GRAFT_FILE": "/dev/null",
    }
    completed = subprocess.run(
        [
            "/usr/bin/git",
            "--no-replace-objects",
            "-c",
            "core.fsmonitor=false",
            "-c",
            "core.hooksPath=/dev/null",
            "-C",
            str(root),
            *arguments,
        ],
        env=environment,
        check=False,
        capture_output=True,
        timeout=60,
    )
    if completed.returncode:
        raise DiagnosticError("fixed Git metadata verification failed")
    return completed.stdout


def runtime_identity(root: Path) -> dict:
    packages = {}
    for distribution in importlib.metadata.distributions():
        name = re.sub(r"[-_.]+", "-", distribution.metadata["Name"]).lower()
        if name in packages:
            raise DiagnosticError("ambiguous installed distribution")
        packages[name] = distribution.version
    return {
        "implementation": sys.implementation.name,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "byteorder": sys.byteorder,
        "dependency_manifest_sha256": digest(
            (root / "requirements/v12-historical.txt").read_bytes()
        ),
        "installed_distributions": packages,
    }


def source_bindings(root: Path, *, running: bool = False) -> dict:
    if platform.python_implementation() != "CPython" or sys.version_info[:2] != (3, 12):
        raise DiagnosticError("CPython 3.12 required")
    if not (root / ".git").is_dir() or (root / ".git").is_symlink():
        raise DiagnosticError("independent full clone required")
    if git(root, "rev-parse", "--is-shallow-repository").strip() != b"false":
        raise DiagnosticError("full history required")
    status_args = ("--", ".", f":(exclude){OUTPUT}/") if running else ()
    if git(
        root, "status", "--porcelain=v1", "--untracked-files=all", *status_args
    ).strip():
        raise DiagnosticError("clean committed source HEAD required")
    head = git(root, "rev-parse", "HEAD").decode().strip()
    registration_raw = git(root, "show", f"{head}:{REGISTRATION}")
    registration = json.loads(registration_raw)
    if (
        registration_raw != (root / REGISTRATION).read_bytes()
        or registration["experiment_id"] != EXPERIMENT
    ):
        raise DiagnosticError("registered experiment manifest required")
    requirements = {
        "experiment_version": 1,
        "seed": SEED,
        "target_count": 627,
        "history_count": 4444,
        "history_through": "2026-08-22",
        "target_start": "2020-01-01",
        "target_end": "2025-12-31",
        "half_counts": [314, 313],
        "output_directory": OUTPUT,
    }
    if any(registration.get(key) != value for key, value in requirements.items()):
        raise DiagnosticError("registered fixed scope differs")
    cohorts = {
        "aggregate": target_dates(),
        "first_half": target_dates()[:314],
        "second_half": target_dates()[314:],
    }
    for scope, dates in cohorts.items():
        raw_dates = "".join(t.isoformat() + "\n" for t in dates).encode()
        if digest(raw_dates) != registration["target_date_identities"][scope]["sha256"]:
            raise DiagnosticError("registered target-date identity differs")
    if registration["execution"].get("remote_once_ref") != REMOTE_REF:
        raise DiagnosticError("registered repository-wide one-shot ref differs")
    base = git(root, "rev-parse", f"{BASE_COMMIT}^{{commit}}").decode().strip()
    if (
        registration["base_commit"] != base
        or registration["algorithm_version"] != "v1.0.0"
    ):
        raise DiagnosticError("fixed V1 source identity differs")
    required_paths = {
        line
        for line in git(root, "ls-tree", "-r", "--name-only", base, "--", "src")
        .decode()
        .splitlines()
        if line.endswith(".py")
    } | {"config.yaml", "requirements/v12-historical.txt"}
    if set(registration["model_source_paths"]) != required_paths:
        raise DiagnosticError("registered source inventory incomplete")
    if not running and any((root / "src").rglob("*.pyc")):
        raise DiagnosticError("fresh checkout without source bytecode required")
    for name, module in tuple(sys.modules.items()):
        if name == "lotto649" or name.startswith("lotto649."):
            filename = getattr(module, "__file__", None)
            module_path = root / "src" / Path(*name.split("."))
            allowed = {
                module_path.with_suffix(".py").resolve(),
                (module_path / "__init__.py").resolve(),
            }
            if filename is None or Path(filename).resolve() not in allowed:
                raise DiagnosticError("runtime import escaped registered source clone")
    for relative, expected_hash in registration["model_source_paths"].items():
        raw = git(root, "show", f"{base}:{relative}")
        if (
            digest(raw) != expected_hash
            or raw != git(root, "show", f"{head}:{relative}")
            or (root / relative).is_symlink()
            or (root / relative).read_bytes() != raw
        ):
            raise DiagnosticError("registered source/config changed")
    implementation = registration["implementation_source_paths"]
    if set(implementation) != {
        "tools/run_v1_verified_history_diagnostic.py",
        "tests/test_v1_verified_history_diagnostic.py",
    }:
        raise DiagnosticError("registered harness/test identity missing")
    for relative, expected_hash in implementation.items():
        raw = git(root, "show", f"{head}:{relative}")
        if digest(raw) != expected_hash or (root / relative).read_bytes() != raw:
            raise DiagnosticError("registered harness/test bytes differ")
    runtime = runtime_identity(root)
    if runtime != registration["runtime"]:
        raise DiagnosticError("frozen runtime identity differs")
    return {
        "classification": registration["classification"],
        "source_git_commit": head,
        "registered_data_provenance": registration["governed_history_identity"],
        "remote_once_ref": REMOTE_REF,
        "remote_once_commit": head,
        "base_commit": base,
        "registration_sha256": digest(registration_raw),
        "expected_target_count": 627,
        "feature_identity": "unchanged V1 source files sealed in model_source_sha256",
        "model_source_sha256": registration["model_source_paths"],
        "implementation_source_sha256": implementation,
        "runtime": runtime,
    }


def run_registered(root: Path) -> dict:
    bindings = source_bindings(root)
    directory = root / OUTPUT
    if os.path.lexists(directory):
        raise DiagnosticError("existing output directory; preserve it and do not retry")
    run_once_remote_guard(GitHubMetadataAPI(), bindings["source_git_commit"])
    _new_directory(directory)
    exclusive_json(directory / "claim.json", bindings)
    from lotto649.config import load_config
    from lotto649.models.factory import build_models
    from lotto649.operational_history import load_published_history

    history = load_published_history(root, bindings["source_git_commit"])
    draws = history.draws
    expected = bindings["registered_data_provenance"]
    identities = expected["immutable_objects"]
    if (
        history.registry.file_sha256 != identities["registry"]["sha256"]
        or history.seal.file_sha256 != identities["seal"]["sha256"]
        or history.base.rows_sha256 != identities["base"]["rows_sha256"]
        or history.suffix.file_sha256 != identities["suffix"]["sha256"]
        or history.suffix.head_event_sha256 != identities["suffix"]["head_sha256"]
    ):
        raise DiagnosticError("fixed governed data object authority differs; no retry")
    if len(draws) != 4444 or draws[-1].draw_date != date(2026, 8, 22):
        raise DiagnosticError("fixed governed history identity differs; no retry")
    targets = target_dates()
    positions = {draw.draw_date: i for i, draw in enumerate(draws)}
    if len(targets) != 627 or any(target not in positions for target in targets):
        raise DiagnosticError("fixed 627 target cohort differs; no retry")
    cfg = load_config(root / "config.yaml")
    models = build_models(cfg, requested=["ensemble", "random"])

    def forecast(prefix, target):
        candidate = models["ensemble"].predict(list(prefix), target)
        return {
            PRODUCERS[0]: candidate,
            PRODUCERS[1]: models["random"].predict(list(prefix), target),
            PRODUCERS[2]: label_permuted(candidate, target),
        }

    def check_sources():
        observed = source_bindings(root, running=True)
        if observed != bindings:
            raise DiagnosticError("source/runtime drift during attempt; no retry")

    # The only allowed working-tree change is the fixed, exclusive audit directory.
    return _sequence(
        directory,
        targets,
        lambda target: draws[: positions[target]],
        lambda target: draws[positions[target]],
        forecast,
        bindings,
        now,
        check_sources=check_sources,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--run-once", action="store_true")
    mode.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    sys.dont_write_bytecode = True
    if sys.flags.isolated and sys.flags.no_site:
        prefix = Path(sys.executable).absolute().parent.parent
        if not (prefix / "pyvenv.cfg").is_file():
            print(
                "Use the registered CPython 3.12 virtual environment.", file=sys.stderr
            )
            return 1
        site = prefix / "lib" / "python3.12" / "site-packages"
        if not site.is_dir():
            print(
                "Registered virtual environment packages unavailable.", file=sys.stderr
            )
            return 1
        sys.path.append(str(site))
    sys.path.insert(0, str(root / "src"))
    try:
        result = verify(root / OUTPUT) if args.verify else run_registered(root)
        print(
            json.dumps(
                {
                    "experiment_id": EXPERIMENT,
                    "verified": bool(args.verify),
                    "scored_target_count": result["scored_target_count"],
                }
            )
        )
        return 0
    except Exception:  # noqa: BLE001 -- preserve one-shot failures without private exception text.
        print(
            "V1 diagnostic stopped; preserve existing outputs and do not retry.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
