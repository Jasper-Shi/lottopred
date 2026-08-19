#!/usr/bin/env python3
"""Manual entry point for the sole frozen V10 historical diagnostic.

This script is intentionally not wired into the package CLI or GitHub Actions.
It must be run from a clean, pushed, CI-green implementation commit under
CPython 3.12. Target outcome rows stay as opaque CSV bytes until the core
runner has durably fsynced that target's complete forecast receipt.
"""

from __future__ import annotations

import argparse
import csv
from datetime import date
from hashlib import sha256
from importlib import metadata
import io
import json
import platform
from pathlib import Path
import re
import shlex
import subprocess
import sys
from typing import Any
from urllib.parse import quote

import yaml

from lotto649.domain import Draw
from lotto649.models.baselines import RandomBaseline
from lotto649.models.v10_adjacent_pair_structure import (
    CANDIDATE_MODEL_NAME,
    CONTROL_MODEL_NAME,
    MODEL_VERSION as V10_MODEL_VERSION,
    forecast_v10,
    preflight_v10_model,
)
from lotto649.research_protocol import load_experiment_registry
from lotto649.v10_diagnostics import (
    MODEL_ORDER,
    V10DiagnosticError,
    V10DiagnosticRequest,
    V10Scope,
    V10TargetPlan,
    run_v10_historical,
)


ROOT = Path(__file__).resolve().parents[1]
REGISTRATION_COMMIT = "e7ac6b81d45b647ca1d144bdd8e21ce66a106185"
EXPERIMENT_ID = "V10_adjacent_pair_structure"
RESEARCH_CONFIG = Path("config/research-v10-adjacent-pair-structure.yaml")
REGISTRY = Path("docs/experiments/registry.yaml")
DATASET = Path("data/processed/draws.csv")
TARGET_START = date(2020, 1, 1)
TARGET_END = date(2025, 12, 31)
FROZEN_PATHS = (
    "config.yaml",
    ".github/workflows",
    "predictions",
    "evaluations",
    "reports",
    RESEARCH_CONFIG.as_posix(),
    "docs/experiments/V10_adjacent_pair_structure.md",
    REGISTRY.as_posix(),
    "docs/research/V10_adjacent_pair_structure_basis.md",
)
EXPECTED_DATA_SHA256 = (
    "edfb7f8a4a7711a630957d6f86b567e6b254caf7b1d1aaea0edf1d16a34155b3"
)
EXPECTED_LOCK_SHA256 = (
    "2fea4cf73cc2578b73c21e6600e31ad843bd903e8a2656b7a2543164ab8d801c"
)
EXPECTED_V5_SHA256 = (
    "b86391ada265d96f94e789f4962812d32771385702e2efa2285cb9ef96d5d6bb"
)
EXPECTED_V8_SHA256 = (
    "e9b51a5316811cbde2b06c36bb61ffffd04b283a4c886cb9ac213bb8fb7deed5"
)
EXPECTED_V8_CLAIM_SHA256 = (
    "6598a2f38462fe6274b9dfa6b6b8c51e6af367b551fd861ef8a582000d60c76d"
)
REQUIRED_CHECK_RUNS = frozenset({"test", "source-and-model-smoke"})
REQUIRED_IMPLEMENTATION_PATHS = frozenset(
    {
        "src/lotto649/models/v10_adjacent_pair_structure.py",
        "tests/test_v10_adjacent_pair_structure.py",
        "src/lotto649/v10_diagnostics.py",
        "tools/run_v10_historical.py",
        "tests/test_v10_diagnostics.py",
    }
)
ALLOWED_IMPLEMENTATION_DOCUMENTATION_PATHS = frozenset(
    {
        "docs/CODEX_HANDOFF.md",
        "docs/MODEL_PROTOCOL.md",
        "docs/RESEARCH_ROADMAP.md",
        "docs/experiments/V10_adjacent_pair_structure_implementation_audit.md",
    }
)
IMPLEMENTATION_PATHS = (
    REQUIRED_IMPLEMENTATION_PATHS | ALLOWED_IMPLEMENTATION_DOCUMENTATION_PATHS
)


def _run(
    *args: str,
    check: bool = True,
    timeout: float = 30,
) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(
            args,
            cwd=ROOT,
            check=check,
            capture_output=True,
            timeout=timeout,
        )
    except (
        FileNotFoundError,
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
    ) as exc:
        raise V10DiagnosticError(f"preflight command failed: {' '.join(args)}") from exc


def _git_bytes(*args: str) -> bytes:
    return _run("git", *args).stdout


def _git_text(*args: str) -> str:
    try:
        return _git_bytes(*args).decode("utf-8").strip()
    except UnicodeDecodeError as exc:
        raise V10DiagnosticError("Git preflight output is not UTF-8") from exc


def _sha256_bytes(payload: bytes) -> str:
    return sha256(payload).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_csv_row(raw_line: bytes) -> Draw:
    try:
        row = next(csv.reader(io.StringIO(raw_line.decode("utf-8"))))
        if len(row) != 8:
            raise ValueError("wrong field count")
        draw_date = date.fromisoformat(row[0])
        numbers = tuple(int(value) for value in row[1:7])
        bonus = int(row[7])
        return Draw(draw_date, numbers, bonus)  # type: ignore[arg-type]
    except (UnicodeDecodeError, ValueError, csv.Error, StopIteration) as exc:
        raise V10DiagnosticError("registered dataset contains an invalid CSV row") from exc


def _date_from_opaque_csv_row(raw_line: bytes) -> date:
    try:
        raw_date = raw_line.split(b",", 1)[0].decode("ascii")
        return date.fromisoformat(raw_date)
    except (UnicodeDecodeError, ValueError) as exc:
        raise V10DiagnosticError("registered dataset contains an invalid draw date") from exc


def _same_date_counterfactual_row(raw_line: bytes) -> bytes:
    """Return a legal, byte-distinct row without parsing its sealed outcome."""

    draw_date = _date_from_opaque_csv_row(raw_line).isoformat()
    candidates = (
        f"{draw_date},1,2,3,4,5,6,7\n".encode("ascii"),
        f"{draw_date},1,3,5,7,9,11,2\n".encode("ascii"),
    )
    return next(candidate for candidate in candidates if candidate != raw_line)


class SealedCsvFoldStore:
    """Keep target outcomes opaque until their post-receipt reveal callback."""

    def __init__(
        self,
        registered_blob: bytes,
        *,
        expected_draw_count: int = 4_432,
        expected_history_through: date = date(2026, 8, 15),
        target_start: date = TARGET_START,
        target_end: date = TARGET_END,
        first_half_end: date = date(2022, 12, 31),
        expected_target_count: int = 621,
        expected_half_counts: tuple[int, int] = (307, 314),
        implementation_commit: str | None = None,
        configuration_sha256: str | None = None,
    ) -> None:
        lines = registered_blob.splitlines(keepends=True)
        if not lines or lines[0] != b"draw_date,n1,n2,n3,n4,n5,n6,bonus\n":
            raise V10DiagnosticError("registered dataset header is not canonical")
        if len(lines) != expected_draw_count + 1 or any(
            not line.endswith(b"\n") for line in lines
        ):
            raise V10DiagnosticError(
                f"registered dataset must contain {expected_draw_count} complete rows"
            )
        self._header = lines[0]
        self._rows = tuple(lines[1:])
        self._dates = tuple(_date_from_opaque_csv_row(line) for line in self._rows)
        if list(self._dates) != sorted(self._dates) or len(set(self._dates)) != len(
            self._dates
        ):
            raise V10DiagnosticError("registered dataset dates are not strictly unique")
        if self._dates[-1] != expected_history_through:
            raise V10DiagnosticError("registered dataset history boundary changed")
        target_indices = [
            index
            for index, target_date in enumerate(self._dates)
            if target_start <= target_date <= target_end
        ]
        if len(target_indices) != expected_target_count:
            raise V10DiagnosticError(
                f"registered V10 target count must be exactly {expected_target_count}"
            )
        first_count = sum(
            self._dates[index] <= first_half_end for index in target_indices
        )
        second_count = len(target_indices) - first_count
        if (first_count, second_count) != expected_half_counts:
            raise V10DiagnosticError("registered V10 fixed-half counts changed")
        self._target_indices = tuple(target_indices)
        first_target_index = target_indices[0]
        self._history_rows = list(self._rows[:first_target_index])
        self._history = [_parse_csv_row(line) for line in self._history_rows]
        self._next_target = 0
        self._last_history: tuple[Draw, ...] | None = None
        self._last_history_rows: tuple[bytes, ...] | None = None
        self._last_payload: dict[str, Any] | None = None
        self._last_target: date | None = None
        self._last_actual: tuple[int, ...] | None = None
        self._last_source_index: int | None = None
        self._implementation_commit = implementation_commit
        self._configuration_sha256 = configuration_sha256
        self._registered_blob_sha256 = _sha256_bytes(registered_blob)
        self._preflight_evidence: dict[str, Any] | None = None

    def bind_preflight_evidence(self, evidence: dict[str, Any]) -> None:
        if self._preflight_evidence is not None:
            raise V10DiagnosticError("V10 preflight evidence was already bound")
        self._preflight_evidence = json.loads(
            json.dumps(evidence, sort_keys=True, allow_nan=False)
        )

    @property
    def target_dates(self) -> tuple[date, ...]:
        return tuple(self._dates[index] for index in self._target_indices)

    @property
    def initial_history_count(self) -> int:
        return self._target_indices[0]

    def _expected_index(self, target_date: date) -> int:
        if self._next_target >= len(self._target_indices):
            raise V10DiagnosticError("all registered V10 targets were already revealed")
        source_index = self._target_indices[self._next_target]
        if self._dates[source_index] != target_date:
            raise V10DiagnosticError("V10 target callbacks were invoked out of order")
        if len(self._history) != source_index or len(self._history_rows) != source_index:
            raise V10DiagnosticError("V10 history is not the exact target-truncated prefix")
        if self._history and self._history[-1].draw_date >= target_date:
            raise V10DiagnosticError("V10 store history is not strictly prior")
        return source_index

    def _random_payload(
        self,
        history: tuple[Draw, ...],
        target_date: date,
    ) -> dict[str, Any]:
        probabilities_by_label = RandomBaseline().predict(list(history), target_date)
        probabilities = tuple(probabilities_by_label[number] for number in range(1, 50))
        ranking = tuple(
            sorted(
                range(1, 50),
                key=lambda number: (-probabilities[number - 1], number),
            )
        )
        return {
            "feature_identity": "target_date_seeded_fair_random",
            "final6": sorted(ranking[:6]),
            "history_draws": len(history),
            "history_through": history[-1].draw_date.isoformat() if history else None,
            "model_name": "random",
            "model_version": "v1.0.0",
            "probabilities": {
                str(number): probabilities[number - 1] for number in range(1, 50)
            },
            "ranking": list(ranking),
            "seed": 649_000_000 + target_date.toordinal(),
            "target_date": target_date.isoformat(),
            "top6": list(ranking[:6]),
            "top12": list(ranking[:12]),
            "top18": list(ranking[:18]),
        }

    def build_forecasts(self, target_date: date) -> dict[str, Any]:
        self._expected_index(target_date)
        history = tuple(self._history)
        payload = self._payload_for_history(
            history,
            tuple(self._history_rows),
            target_date,
        )
        self._last_history = history
        self._last_history_rows = tuple(self._history_rows)
        self._last_payload = payload
        self._last_target = target_date
        return payload

    def _forecasts_for_history(
        self,
        history: tuple[Draw, ...],
        target_date: date,
    ) -> dict[str, Any]:
        candidate = forecast_v10(history, target_date, CANDIDATE_MODEL_NAME)
        control = forecast_v10(history, target_date, CONTROL_MODEL_NAME)
        return {
            CANDIDATE_MODEL_NAME: candidate.canonical_payload(),
            CONTROL_MODEL_NAME: control.canonical_payload(),
            "random": self._random_payload(history, target_date),
        }

    def _payload_for_history(
        self,
        history: tuple[Draw, ...],
        history_rows: tuple[bytes, ...],
        target_date: date,
    ) -> dict[str, Any]:
        payload = {
            "target_date": target_date.isoformat(),
            "prefix": {
                "history_draws": len(history),
                "history_through": (
                    history[-1].draw_date.isoformat() if history else None
                ),
                "strict_prefix_sha256": _sha256_bytes(
                    self._header + b"".join(history_rows)
                ),
            },
            "forecasts": self._forecasts_for_history(history, target_date),
        }
        if tuple(payload["forecasts"]) != MODEL_ORDER:
            raise V10DiagnosticError("V10 production forecast model order changed")
        return payload

    def _payload_from_sealed_rows(
        self,
        rows: tuple[bytes, ...],
        target_date: date,
    ) -> dict[str, Any]:
        """Independent suffix-mutation oracle that parses only the strict prefix."""

        dates = tuple(_date_from_opaque_csv_row(row) for row in rows)
        target_indices = [
            index for index, row_date in enumerate(dates) if row_date == target_date
        ]
        if len(target_indices) != 1:
            raise V10DiagnosticError("counterfactual sealed rows lack one target date")
        target_index = target_indices[0]
        history_rows = rows[:target_index]
        history = tuple(_parse_csv_row(row) for row in history_rows)
        if history and history[-1].draw_date >= target_date:
            raise V10DiagnosticError("counterfactual prefix is not strictly prior")
        return self._payload_for_history(history, history_rows, target_date)

    def reveal_actual(self, target_date: date) -> tuple[int, ...]:
        source_index = self._expected_index(target_date)
        if self._last_target != target_date or self._last_payload is None:
            raise V10DiagnosticError("V10 target was requested before forecast construction")
        # This is the first conversion of the opaque target row into numbers.
        target = _parse_csv_row(self._rows[source_index])
        if target.draw_date != target_date:
            raise V10DiagnosticError("V10 revealed target identity mismatch")
        self._history.append(target)
        self._history_rows.append(self._rows[source_index])
        self._next_target += 1
        self._last_actual = target.numbers
        self._last_source_index = source_index
        return target.numbers

    def leakage_audit(
        self,
        target_date: date,
        frozen_payload: dict[str, Any],
        actual: tuple[int, ...],
    ) -> dict[str, Any]:
        if (
            self._last_target != target_date
            or self._last_history is None
            or self._last_history_rows is None
            or self._last_payload is None
            or self._last_actual != tuple(actual)
            or self._last_source_index is None
        ):
            return {"clear": False, "checks": [], "reason": "audit state mismatch"}
        canonical_options = {
            "sort_keys": True,
            "separators": (",", ":"),
            "allow_nan": False,
        }
        frozen_bytes = json.dumps(
            frozen_payload,
            **canonical_options,
        ).encode("utf-8")
        replay = self._payload_for_history(
            self._last_history,
            self._last_history_rows,
            target_date,
        )
        replay_bytes = json.dumps(replay, **canonical_options).encode("utf-8")

        bonus_mutated_history = []
        for draw in self._last_history:
            replacement_bonus = next(
                number
                for number in range(1, 50)
                if number not in draw.numbers and number != draw.bonus
            )
            bonus_mutated_history.append(
                Draw(draw.draw_date, draw.numbers, replacement_bonus)
            )
        baseline_forecasts = self._forecasts_for_history(
            self._last_history,
            target_date,
        )
        bonus_mutated_forecasts = self._forecasts_for_history(
            tuple(bonus_mutated_history),
            target_date,
        )

        counterfactual_main_sets = (
            (1, 2, 3, 4, 5, 6),
            (1, 3, 5, 7, 9, 11),
            (1, 2, 3, 4, 5, 7),
            (3, 4, 5, 6, 7, 8),
            (1, 2, 4, 8, 16, 32),
            (7, 8, 20, 21, 33, 34),
            (2, 3, 4, 20, 30, 40),
        )
        candidate_indices = tuple(
            dict.fromkeys(
                (0, len(self._last_history) // 2, len(self._last_history) - 1)
            )
        )
        main_mutated_forecasts = baseline_forecasts
        selected_main_counterfactual: dict[str, Any] | None = None
        main_counterfactual_attempts: list[dict[str, Any]] = []
        for prior_index in candidate_indices:
            prior_draw = self._last_history[prior_index]
            for mutated_main in counterfactual_main_sets:
                if mutated_main == prior_draw.numbers:
                    continue
                mutated_bonus = next(
                    number for number in range(1, 50) if number not in mutated_main
                )
                main_mutated_history = list(self._last_history)
                main_mutated_history[prior_index] = Draw(
                    prior_draw.draw_date,
                    mutated_main,
                    mutated_bonus,
                )
                counterfactual_forecasts = self._forecasts_for_history(
                    tuple(main_mutated_history),
                    target_date,
                )
                candidate_changed = (
                    counterfactual_forecasts[CANDIDATE_MODEL_NAME]
                    != baseline_forecasts[CANDIDATE_MODEL_NAME]
                )
                control_changed = (
                    counterfactual_forecasts[CONTROL_MODEL_NAME]
                    != baseline_forecasts[CONTROL_MODEL_NAME]
                )
                main_counterfactual_attempts.append(
                    {
                        "candidate_changed": candidate_changed,
                        "control_changed": control_changed,
                        "prior_index": prior_index,
                        "replacement_main": list(mutated_main),
                    }
                )
                if candidate_changed and control_changed:
                    main_mutated_forecasts = counterfactual_forecasts
                    selected_main_counterfactual = {
                        "draw_date": prior_draw.draw_date.isoformat(),
                        "prior_index": prior_index,
                        "original_main": list(prior_draw.numbers),
                        "replacement_main": list(mutated_main),
                    }
                    break
            if selected_main_counterfactual is not None:
                break

        source_index = self._last_source_index
        target_row = self._rows[source_index]
        parsed_target = _parse_csv_row(target_row)
        replacement_target_row = _same_date_counterfactual_row(target_row)
        future_rows = self._rows[source_index + 1 :]
        replacement_future_rows = tuple(
            _same_date_counterfactual_row(row) for row in future_rows
        )
        target_counterfactual_rows = (
            *self._rows[:source_index],
            replacement_target_row,
            *future_rows,
        )
        future_counterfactual_rows = (
            *self._rows[: source_index + 1],
            *replacement_future_rows,
        )
        sealed_replay = self._payload_from_sealed_rows(self._rows, target_date)
        target_counterfactual_payload = self._payload_from_sealed_rows(
            target_counterfactual_rows,
            target_date,
        )
        future_counterfactual_payload = self._payload_from_sealed_rows(
            future_counterfactual_rows,
            target_date,
        )
        counterfactual_suffix_evidence = {
            "original_target_sha256": _sha256_bytes(target_row),
            "replacement_target_sha256": _sha256_bytes(replacement_target_row),
            "original_future_sha256": _sha256_bytes(b"".join(future_rows)),
            "replacement_future_sha256": _sha256_bytes(
                b"".join(replacement_future_rows)
            ),
            "target_date_preserved": (
                _date_from_opaque_csv_row(replacement_target_row) == target_date
            ),
            "future_dates_preserved": (
                tuple(_date_from_opaque_csv_row(row) for row in future_rows)
                == tuple(
                    _date_from_opaque_csv_row(row)
                    for row in replacement_future_rows
                )
            ),
            "forecast_sha256": _sha256_bytes(
                json.dumps(baseline_forecasts, **canonical_options).encode("utf-8")
            ),
        }

        preflight = self._preflight_evidence or {}
        current_head = (
            _git_text("rev-parse", "HEAD")
            if self._implementation_commit is not None
            else preflight.get("exact_head")
        )
        current_config_sha = (
            _file_sha256(ROOT / RESEARCH_CONFIG)
            if self._configuration_sha256 is not None
            else preflight.get("configuration_sha256")
        )
        prefix_sha = _sha256_bytes(
            self._header + b"".join(self._last_history_rows)
        )
        checks = [
            {
                "name": "chronology",
                "passed": all(draw.draw_date < target_date for draw in self._last_history),
                "evidence": {
                    "history_draws": len(self._last_history),
                    "history_through": self._last_history[-1].draw_date.isoformat(),
                    "target_date": target_date.isoformat(),
                },
            },
            {
                "name": "target_exclusion",
                "passed": (
                    b"actual" not in frozen_bytes.lower()
                    and sealed_replay == frozen_payload
                    and target_counterfactual_payload == sealed_replay
                    and replacement_target_row != target_row
                ),
                "evidence": counterfactual_suffix_evidence,
            },
            {
                "name": "future_exclusion",
                "passed": (
                    bool(future_rows)
                    and future_counterfactual_payload == sealed_replay
                    and tuple(_date_from_opaque_csv_row(row) for row in future_rows)
                    == tuple(
                        _date_from_opaque_csv_row(row)
                        for row in replacement_future_rows
                    )
                ),
                "evidence": {
                    **counterfactual_suffix_evidence,
                    "future_row_count": len(future_rows),
                },
            },
            {
                "name": "preprocessing",
                "passed": bonus_mutated_forecasts == baseline_forecasts,
                "evidence": {
                    "bonus_only_history_mutation_count": len(bonus_mutated_history),
                    "candidate_control_random_unchanged": (
                        bonus_mutated_forecasts == baseline_forecasts
                    ),
                },
            },
            {
                "name": "feature_selection",
                "passed": (
                    main_mutated_forecasts[CANDIDATE_MODEL_NAME]
                    != baseline_forecasts[CANDIDATE_MODEL_NAME]
                    and main_mutated_forecasts[CONTROL_MODEL_NAME]
                    != baseline_forecasts[CONTROL_MODEL_NAME]
                ),
                "evidence": {
                    "feature_identity": "sorted_main_gap_exactly_one",
                    "prior_main_counterfactual_changed_candidate": (
                        main_mutated_forecasts[CANDIDATE_MODEL_NAME]
                        != baseline_forecasts[CANDIDATE_MODEL_NAME]
                    ),
                    "prior_main_counterfactual_changed_targeted_control": (
                        main_mutated_forecasts[CONTROL_MODEL_NAME]
                        != baseline_forecasts[CONTROL_MODEL_NAME]
                    ),
                    "selected_prior_main_counterfactual": (
                        selected_main_counterfactual
                    ),
                    "prior_main_counterfactual_attempts": (
                        main_counterfactual_attempts
                    ),
                    "registration_commit": REGISTRATION_COMMIT,
                },
            },
            {
                "name": "model_selection",
                "passed": (
                    self._implementation_commit == current_head
                    and self._configuration_sha256 == current_config_sha
                    and tuple(baseline_forecasts) == MODEL_ORDER
                    and all(
                        baseline_forecasts[name]["model_version"]
                        == ("v1.0.0" if name == "random" else V10_MODEL_VERSION)
                        for name in MODEL_ORDER
                    )
                ),
                "evidence": {
                    "registration_commit": REGISTRATION_COMMIT,
                    "implementation_commit": self._implementation_commit,
                    "current_head": current_head,
                    "configuration_sha256": self._configuration_sha256,
                    "current_configuration_sha256": current_config_sha,
                    "model_order": list(baseline_forecasts),
                },
            },
            {
                "name": "source_integrity",
                "passed": (
                    parsed_target.draw_date == target_date
                    and parsed_target.numbers == tuple(actual)
                    and self._registered_blob_sha256
                    == preflight.get("registered_blob_sha256")
                ),
                "evidence": {
                    "registered_blob_sha256": self._registered_blob_sha256,
                    "preflight_registered_blob_sha256": preflight.get(
                        "registered_blob_sha256"
                    ),
                    "sealed_target_row_sha256": _sha256_bytes(target_row),
                    "revealed_actual": list(actual),
                },
            },
            {
                "name": "git_runtime_integrity",
                "passed": (
                    preflight.get("registration_ancestor") is True
                    and preflight.get("runtime_versions_verified") is True
                    and preflight.get("ci_required_checks_passed") is True
                    and preflight.get("remote_branch_head")
                    == self._implementation_commit
                    and current_head == self._implementation_commit
                ),
                "evidence": preflight,
            },
            {
                "name": "forecast_replay",
                "passed": replay_bytes == frozen_bytes,
                "evidence": {
                    "frozen_sha256": _sha256_bytes(frozen_bytes),
                    "replay_sha256": _sha256_bytes(replay_bytes),
                },
            },
            {
                "name": "prefix_identity",
                "passed": (
                    frozen_payload.get("prefix", {}).get("strict_prefix_sha256")
                    == prefix_sha
                    and frozen_payload.get("prefix", {}).get("history_through")
                    == self._last_history[-1].draw_date.isoformat()
                ),
                "evidence": {
                    "computed_prefix_sha256": prefix_sha,
                    "frozen_prefix": frozen_payload.get("prefix"),
                    "target_cutoff": self._last_history[-1].draw_date.isoformat(),
                },
            },
        ]
        return {
            "clear": all(check["passed"] for check in checks),
            "checks": checks,
            "audit_kind": (
                "chronology_target_future_preprocessing_feature_model_source_git_runtime"
            ),
        }

    def plans(self) -> tuple[V10TargetPlan, ...]:
        plans = []
        for target_date in self.target_dates:
            plans.append(
                V10TargetPlan(
                    target_date=target_date,
                    build_forecasts=lambda target_date=target_date: self.build_forecasts(
                        target_date
                    ),
                    reveal_actual=lambda target_date=target_date: self.reveal_actual(
                        target_date
                    ),
                )
            )
        return tuple(plans)


def _validate_working_dataset(registered_blob: bytes) -> None:
    working_lines = (ROOT / DATASET).read_bytes().splitlines(keepends=True)
    registered_lines = registered_blob.splitlines(keepends=True)
    if len(working_lines) < len(registered_lines):
        raise V10DiagnosticError("working dataset truncates the registered boundary")
    if working_lines[: len(registered_lines)] != registered_lines:
        raise V10DiagnosticError("working dataset revises the registered outcome prefix")
    working_dates = [_date_from_opaque_csv_row(line) for line in working_lines[1:]]
    if working_dates != sorted(working_dates) or len(working_dates) != len(
        set(working_dates)
    ):
        raise V10DiagnosticError("working dataset is not a strict chronological append")


def _normalized_distribution_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _locked_versions(lock_bytes: bytes) -> dict[str, str]:
    try:
        lines = lock_bytes.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise V10DiagnosticError("runtime lock is not UTF-8") from exc
    locked: dict[str, str] = {}
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.count("==") != 1:
            raise V10DiagnosticError("runtime lock contains a non-exact requirement")
        name, version = stripped.split("==", 1)
        normalized = _normalized_distribution_name(name)
        if not normalized or not version or normalized in locked:
            raise V10DiagnosticError("runtime lock contains an invalid/duplicate package")
        locked[normalized] = version
    if not locked:
        raise V10DiagnosticError("runtime lock contains no frozen distributions")
    return locked


def _validate_runtime_versions(
    lock_bytes: bytes,
    installed_versions: dict[str, str],
) -> dict[str, str]:
    locked = _locked_versions(lock_bytes)
    normalized_installed = {
        _normalized_distribution_name(name): version
        for name, version in installed_versions.items()
    }
    mismatches = {
        name: {"expected": version, "actual": normalized_installed.get(name)}
        for name, version in locked.items()
        if normalized_installed.get(name) != version
    }
    if mismatches:
        raise V10DiagnosticError(f"runtime distribution mismatch: {mismatches}")
    return locked


def _require_runtime_identity(
    implementation: str,
    version_info: tuple[int, int],
) -> None:
    if implementation != "CPython" or version_info != (3, 12):
        raise V10DiagnosticError("V10 historical run requires CPython 3.12")


def _runtime_manifest() -> dict[str, Any]:
    distributions = sorted(
        {
            (distribution.metadata.get("Name") or "UNKNOWN", distribution.version)
            for distribution in metadata.distributions()
        },
        key=lambda item: (item[0].lower(), item[1]),
    )
    installed_versions = {name: version for name, version in distributions}
    lock_bytes = (ROOT / "requirements-live.lock").read_bytes()
    locked = _validate_runtime_versions(lock_bytes, installed_versions)
    return {
        "implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "executable": sys.executable,
        "requirements_lock_path": "requirements-live.lock",
        "requirements_lock_sha256": _sha256_bytes(lock_bytes),
        "locked_distributions_verified": locked,
        "installed_distributions": [
            {"name": name, "version": version} for name, version in distributions
        ],
    }


def _validate_ci_check_runs(checks: list[dict[str, Any]]) -> dict[str, Any]:
    latest_by_app_and_name: dict[tuple[str, str], dict[str, Any]] = {}
    for check in checks:
        name = check.get("name")
        if not isinstance(name, str):
            continue
        app = check.get("app")
        if isinstance(app, dict):
            app_identity = str(app.get("slug") or app.get("id") or app.get("name"))
        else:
            app_identity = "unknown-app"
        key = (app_identity, name)
        prior = latest_by_app_and_name.get(key)
        if prior is None or int(check.get("id", 0)) > int(prior.get("id", 0)):
            latest_by_app_and_name[key] = check
    missing = sorted(
        name
        for name in REQUIRED_CHECK_RUNS
        if ("github-actions", name) not in latest_by_app_and_name
    )
    if missing:
        raise V10DiagnosticError(f"implementation CI lacks required checks: {missing}")
    failed_required = sorted(
        name
        for name in REQUIRED_CHECK_RUNS
        if latest_by_app_and_name[("github-actions", name)].get("status")
        != "completed"
        or latest_by_app_and_name[("github-actions", name)].get("conclusion")
        != "success"
    )
    if failed_required:
        raise V10DiagnosticError(
            f"implementation required CI is not green: {failed_required}"
        )
    nonpassing = sorted(
        f"{app_identity}:{name}"
        for (app_identity, name), check in latest_by_app_and_name.items()
        if check.get("status") != "completed"
        or check.get("conclusion") not in {"success", "neutral", "skipped"}
    )
    if nonpassing:
        raise V10DiagnosticError(
            f"implementation CI contains nonpassing checks: {nonpassing}"
        )
    return {
        "check_run_count": len(checks),
        "required_successful_checks": sorted(REQUIRED_CHECK_RUNS),
        "latest_check_conclusions": [
            {
                "app": app_identity,
                "name": name,
                "status": check.get("status"),
                "conclusion": check.get("conclusion"),
            }
            for (app_identity, name), check in sorted(
                latest_by_app_and_name.items()
            )
        ],
    }


def _validate_ci_green(code_commit: str) -> dict[str, Any]:
    response = _run(
        "gh",
        "api",
        "--method",
        "GET",
        "--paginate",
        "--slurp",
        f"repos/Jasper-Shi/lottopred/commits/{code_commit}/check-runs",
        "-f",
        "per_page=100",
    ).stdout
    try:
        pages = json.loads(response)
        checks = [
            check
            for page in pages
            for check in page["check_runs"]
        ]
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise V10DiagnosticError("unable to parse GitHub check-run preflight") from exc
    return _validate_ci_check_runs(checks)


def _require_exact_remote_head(actual_head: str, expected_head: str) -> str:
    if (
        len(actual_head) != 40
        or any(character not in "0123456789abcdef" for character in actual_head)
        or actual_head != expected_head
    ):
        raise V10DiagnosticError("GitHub remote branch is not the exact implementation HEAD")
    return actual_head


def _validate_github_branch_head(branch: str, code_commit: str) -> str:
    if not branch:
        raise V10DiagnosticError("V10 implementation requires a named Git branch")
    response = _run(
        "gh",
        "api",
        f"repos/Jasper-Shi/lottopred/git/ref/heads/{quote(branch, safe='')}",
        "--jq",
        ".object.sha",
    ).stdout
    try:
        actual_head = response.decode("ascii").strip()
    except UnicodeDecodeError as exc:
        raise V10DiagnosticError("GitHub remote branch SHA is not ASCII") from exc
    return _require_exact_remote_head(actual_head, code_commit)


def _validate_implementation_changed_paths(changed_text: str) -> list[str]:
    changed = [line for line in changed_text.splitlines() if line]
    changed_set = set(changed)
    unexpected = sorted(changed_set - IMPLEMENTATION_PATHS)
    missing = sorted(REQUIRED_IMPLEMENTATION_PATHS - changed_set)
    if unexpected or missing:
        raise V10DiagnosticError(
            f"V10 implementation path set mismatch; unexpected={unexpected}, missing={missing}"
        )
    return sorted(changed_set)


def _load_references() -> dict[str, Any]:
    v5_path = ROOT / "reports/v5_pair_affinity_v5.0.0_historical.json"
    v8_path = ROOT / "reports/v8_spectral_phase_v8.0.0_historical.json"
    v8_claim_path = ROOT / "reports/v8_spectral_phase_v8.0.0_historical.claim"
    identities = {
        "v5_report_sha256": _file_sha256(v5_path),
        "v8_report_sha256": _file_sha256(v8_path),
        "v8_claim_sha256": _file_sha256(v8_claim_path),
    }
    if identities != {
        "v5_report_sha256": EXPECTED_V5_SHA256,
        "v8_report_sha256": EXPECTED_V8_SHA256,
        "v8_claim_sha256": EXPECTED_V8_CLAIM_SHA256,
    }:
        raise V10DiagnosticError("frozen V5/V8 reference identity changed")
    try:
        v5 = json.loads(v5_path.read_text(encoding="utf-8"))
        v8 = json.loads(v8_path.read_text(encoding="utf-8"))
        v5_consumed = next(
            lane for lane in v5["lanes"] if lane["lane"] == "consumed_diagnostic"
        )
        v5_p = float(v5_consumed["candidate"]["primary_exact_one_sided_p"])
        ensemble = next(
            comparison
            for comparison in v8["comparisons"]
            if comparison["model_name"] == "ensemble"
        )
        ensemble_mean = float(ensemble["avg_top12_hits"])
    except (OSError, ValueError, KeyError, StopIteration, TypeError) as exc:
        raise V10DiagnosticError("frozen V5/V8 reference payload is invalid") from exc
    return {
        **identities,
        "v5_primary_exact_p": v5_p,
        "v1_ensemble_top12_mean": ensemble_mean,
        "comparisons": v8["comparisons"],
    }


def _preflight(
    *,
    code_commit: str,
    registered_blob: bytes,
    store: SealedCsvFoldStore,
    reference: dict[str, Any],
) -> dict[str, Any]:
    _require_runtime_identity(platform.python_implementation(), sys.version_info[:2])
    if ROOT.resolve() != Path(_git_text("rev-parse", "--show-toplevel")).resolve():
        raise V10DiagnosticError("V10 runner must execute at the repository top level")
    head = _git_text("rev-parse", "HEAD")
    if head != code_commit or head == REGISTRATION_COMMIT:
        raise V10DiagnosticError("V10 code commit must be the exact implementation HEAD")
    if _git_text("status", "--porcelain=v1", "--untracked-files=all"):
        raise V10DiagnosticError("V10 worktree must be completely clean before claim")
    ancestor = _run(
        "git",
        "merge-base",
        "--is-ancestor",
        REGISTRATION_COMMIT,
        head,
        check=False,
    )
    if ancestor.returncode != 0:
        raise V10DiagnosticError("V10 implementation does not descend from registration")
    changed_frozen = _git_text(
        "diff",
        "--name-only",
        REGISTRATION_COMMIT,
        head,
        "--",
        *FROZEN_PATHS,
    )
    if changed_frozen:
        raise V10DiagnosticError(f"V10 frozen/operational paths changed: {changed_frozen}")
    implementation_paths = _validate_implementation_changed_paths(
        _git_text("diff", "--name-only", REGISTRATION_COMMIT, head)
    )
    try:
        upstream = _git_text("rev-parse", "@{u}")
    except V10DiagnosticError as exc:
        raise V10DiagnosticError("V10 implementation branch must be pushed") from exc
    if upstream != head:
        raise V10DiagnosticError("V10 upstream branch does not equal exact HEAD")
    branch = _git_text("branch", "--show-current")
    remote_head = _validate_github_branch_head(branch, head)

    config_path = ROOT / RESEARCH_CONFIG
    disk_config = config_path.read_bytes()
    if disk_config != _git_bytes("show", f"{head}:{RESEARCH_CONFIG.as_posix()}"):
        raise V10DiagnosticError("V10 research config differs from exact HEAD")
    if disk_config != _git_bytes(
        "show", f"{REGISTRATION_COMMIT}:{RESEARCH_CONFIG.as_posix()}"
    ):
        raise V10DiagnosticError("V10 research config changed after registration")
    try:
        config = yaml.safe_load(disk_config.decode("utf-8"))
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        raise V10DiagnosticError("V10 research config is invalid") from exc
    if config.get("live") != {"enabled": False, "models": [], "shadow_models": []}:
        raise V10DiagnosticError("V10 research config must disable live models")
    if config.get("notifications") != {"enabled": False}:
        raise V10DiagnosticError("V10 research config must disable model notifications")
    if config.get("backtest", {}).get("models") != list(MODEL_ORDER):
        raise V10DiagnosticError("V10 research config model set/order changed")

    registry = load_experiment_registry(ROOT / REGISTRY)
    registration = registry.get(EXPERIMENT_ID)
    if (
        registration.status != "registered"
        or registration.result is not None
        or registration.model_name != CANDIDATE_MODEL_NAME
        or registration.model_version != "v10.0.0"
        or registration.multiplicity_family != "v5_pair_cooccurrence"
        or registration.variant_index != 2
        or registration.dataset_source_commit
        != "90177c80cfb070038d79508fb2e73305a297f516"
        or registration.dataset_sha256 != EXPECTED_DATA_SHA256
        or registration.dataset_draw_count != 4_432
        or registration.registration_history_through != date(2026, 8, 15)
    ):
        raise V10DiagnosticError("V10 registration identity/provenance changed")
    if len(registration.negative_controls) != 1 or (
        registration.negative_controls[0].kind,
        registration.negative_controls[0].seed,
    ) != ("target_date_seeded_fair_random", 649):
        raise V10DiagnosticError("V10 registered random control changed")
    if registration.parameters.get("targeted_control_kind") != (
        "frozen_global_label_bijection"
    ):
        raise V10DiagnosticError("V10 targeted control registration changed")

    if _sha256_bytes(registered_blob) != EXPECTED_DATA_SHA256:
        raise V10DiagnosticError("V10 registered source blob SHA-256 changed")
    _validate_working_dataset(registered_blob)
    if store.target_dates[0] < TARGET_START or store.target_dates[-1] > TARGET_END:
        raise V10DiagnosticError("V10 sealed target dates escape the historical lane")
    preflight_v10_model()
    runtime = _runtime_manifest()
    if runtime["requirements_lock_sha256"] != EXPECTED_LOCK_SHA256:
        raise V10DiagnosticError("V10 runtime lock identity changed")
    ci = _validate_ci_green(code_commit)
    store.bind_preflight_evidence(
        {
            "exact_head": head,
            "registration_ancestor": True,
            "configuration_sha256": _sha256_bytes(disk_config),
            "registered_blob_sha256": _sha256_bytes(registered_blob),
            "runtime_versions_verified": True,
            "ci_required_checks_passed": True,
            "implementation_paths": implementation_paths,
            "remote_branch": branch,
            "remote_branch_head": remote_head,
            "requirements_lock_sha256": runtime["requirements_lock_sha256"],
        }
    )
    return {
        "passed": True,
        "audit_warnings": [],
        "registration_commit": REGISTRATION_COMMIT,
        "registered_parameters": dict(registration.parameters),
        "configuration": {
            "path": RESEARCH_CONFIG.as_posix(),
            "sha256": _sha256_bytes(disk_config),
            "committed_exact_head": True,
            "unchanged_since_registration": True,
        },
        "data": {
            "path": DATASET.as_posix(),
            "source_commit": registration.dataset_source_commit,
            "registered_sha256": EXPECTED_DATA_SHA256,
            "registered_draw_count": 4_432,
            "registered_history_through": "2026-08-15",
            "historical_target_count": len(store.target_dates),
            "first_half_target_count": 307,
            "second_half_target_count": 314,
            "target_rows_opaque_until_receipt": True,
            "working_dataset_preserves_registered_prefix": True,
        },
        "references": {
            key: value for key, value in reference.items() if key.endswith("sha256")
        },
        "runtime": runtime,
        "git": {
            "exact_head": head,
            "registration_ancestor": True,
            "clean_worktree": True,
            "upstream_equals_head": True,
            "remote_branch": branch,
            "remote_branch_head": remote_head,
            "implementation_paths": implementation_paths,
            "ci": ci,
        },
        "chronology": {
            "target_dates_strictly_increasing_unique": True,
            "complete_expanding_prefix": True,
            "bonus_excluded_from_model_and_scores": True,
            "2026_scored_targets": 0,
        },
    }


class GitHubWorkflowNotifier:
    def __init__(self, branch: str, code_commit: str) -> None:
        self.branch = branch
        self.code_commit = code_commit

    def __call__(self, subject: str, body: str) -> bool:
        try:
            _validate_github_branch_head(self.branch, self.code_commit)
            completed = subprocess.run(
                [
                    "gh",
                    "workflow",
                    "run",
                    "email-test.yml",
                    "--ref",
                    self.branch,
                    "-f",
                    f"subject={subject}",
                    "-f",
                    f"body={body}",
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                timeout=30,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired, V10DiagnosticError):
            return False
        return completed.returncode == 0


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--code-commit", required=True)
    parser.add_argument(
        "--execute-consumed-historical-diagnostic",
        action="store_true",
        help="required acknowledgement that this permanently consumes V10",
    )
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    if not args.execute_consumed_historical_diagnostic:
        raise SystemExit(
            "refusing to acquire the one-shot claim without "
            "--execute-consumed-historical-diagnostic"
        )
    if (
        len(args.code_commit) != 40
        or any(character not in "0123456789abcdef" for character in args.code_commit)
    ):
        raise SystemExit("--code-commit must be a full lowercase Git SHA")
    registered_blob = _git_bytes(
        "show",
        "90177c80cfb070038d79508fb2e73305a297f516:data/processed/draws.csv",
    )
    store = SealedCsvFoldStore(
        registered_blob,
        implementation_commit=args.code_commit,
        configuration_sha256=_file_sha256(ROOT / RESEARCH_CONFIG),
    )
    reference = _load_references()
    branch = _git_text("branch", "--show-current")
    exact_command = shlex.join([sys.executable, *sys.argv])
    request = V10DiagnosticRequest(
        root=ROOT,
        output_dir=ROOT / "reports",
        code_commit=args.code_commit,
        exact_command=exact_command,
        targets=store.plans(),
        preflight=lambda: _preflight(
            code_commit=args.code_commit,
            registered_blob=registered_blob,
            store=store,
            reference=reference,
        ),
        reference=reference,
        expected_target_count=621,
        stability_scopes=(
            V10Scope("first_307", date(2020, 1, 1), date(2022, 12, 31), 307),
            V10Scope("second_314", date(2023, 1, 1), date(2025, 12, 31), 314),
        ),
        bootstrap_replicates=10_000,
        bootstrap_seed=649,
        notifier=GitHubWorkflowNotifier(branch, args.code_commit),
        leakage_audit=lambda target, payload, actual: store.leakage_audit(
            target,
            dict(payload),
            tuple(actual),
        ),
    )
    result = run_v10_historical(request)
    compact_result = {
        key: value
        for key, value in result.items()
        if key != "report"
    }
    print(
        json.dumps(
            compact_result,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            default=str,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
