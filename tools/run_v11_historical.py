#!/usr/bin/env python3
"""Manual-only production adapter for the sole V11 historical diagnostic.

The adapter is intentionally not connected to the package CLI or automation.
Its preflight and sealed data store are defined below and are dependency-
injected into :func:`lotto649.v11_diagnostics.run_v11_historical`.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import platform
import re
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from copy import deepcopy
from datetime import date
from hashlib import sha256
from importlib import metadata
from pathlib import Path
from typing import Any
from urllib.parse import quote

import yaml

from lotto649.config import load_config
from lotto649.domain import Draw
from lotto649.models.baselines import RandomBaseline
from lotto649.models.factory import build_models
from lotto649.models.v11_previous_bonus_carryover import (
    V1BaseSnapshot,
    V11Forecast,
    V11ForecastBundle,
    V11Transition,
    forecast_v11_bundle,
    make_transition,
    preflight_v11_model,
    select_pseudo_bonus,
)
from lotto649.v11_diagnostics import (
    CANDIDATE_MODEL,
    CONTROL_MODEL,
    FEATURE_SET_BY_MODEL,
    RANDOM_MODEL,
    REGISTERED_V11_IDENTITY,
    REGISTRATION_COMMIT,
    V1_MODEL,
    V11DiagnosticError,
    V11DiagnosticRequest,
    V11Scope,
    V11TargetPlan,
    canonical_sha256,
    registered_v11_command,
    run_v11_historical,
)

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT_ID = "V11_previous_bonus_carryover"
RESEARCH_CONFIG = Path("config/research-v11-previous-bonus-carryover.yaml")
REGISTRY = Path("docs/experiments/registry.yaml")
DATASET = Path("data/processed/draws.csv")
V1_CONFIG = Path("config.yaml")
RUNTIME_LOCK = Path("requirements-live.lock")
TARGET_START = date(2020, 1, 1)
TARGET_END = date(2025, 12, 31)
FIRST_HALF_END = date(2022, 12, 31)
RNG_START = date(2019, 5, 15)
EXPECTED_DATA_SHA256 = REGISTERED_V11_IDENTITY.data_sha256
EXPECTED_DATA_DRAW_COUNT = REGISTERED_V11_IDENTITY.data_draw_count
EXPECTED_HISTORY_THROUGH = date.fromisoformat(
    REGISTERED_V11_IDENTITY.data_history_through
)
EXPECTED_LOCK_SHA256 = REGISTERED_V11_IDENTITY.runtime_lock_sha256
EXPECTED_V1_CONFIG_SHA256 = REGISTERED_V11_IDENTITY.v1_base_config_sha256
EXPECTED_TARGET_COUNTS = (621, 307, 314)
REQUIRED_CHECK_RUNS = frozenset({"test", "source-and-model-smoke"})
STATUS_DOCUMENT_REPLACEMENTS: dict[str, tuple[tuple[bytes, bytes], ...]] = {
    "docs/CODEX_HANDOFF.md": (
        (
            b"| V11 previous-bonus carryover | Registered, not implemented or scored |",
            b"| V11 previous-bonus carryover | Implemented; not scored or activated |",
        ),
        (
            b"is registered as `v11.0.0`, but it is not implemented, scored, or activated.",
            b"is implemented as registered `v11.0.0`, but it is not scored or activated.",
        ),
    ),
    "docs/MODEL_PROTOCOL.md": (
        (
            b"`V11_previous_bonus_carryover v11.0.0` is registered but not implemented,\nscored, or activated.",
            b"`V11_previous_bonus_carryover v11.0.0` is implemented as registered but not\nscored or activated.",
        ),
    ),
    "docs/RESEARCH_ROADMAP.md": (
        (
            b"| `v11.0.0` | Registered; not implemented or scored |",
            b"| `v11.0.0` | Implemented; not scored or activated |",
        ),
    ),
}
STATUS_DOCUMENT_REGISTRATION_SHA256 = {
    "docs/CODEX_HANDOFF.md": (
        "e78b392a7e5076210c7f77d3088f8272ab0870fb7ba26e1ff3ad46bac60fa918"
    ),
    "docs/MODEL_PROTOCOL.md": (
        "4660bc2e716d3f277b57530f3fbdb0e8bab0664968a5f96ff6a31c176df3703f"
    ),
    "docs/RESEARCH_ROADMAP.md": (
        "e2e62cbc0721c8c51fc8a9c55a926eab3084c8a542f0d19d485266e61beabd31"
    ),
}
REQUIRED_SOURCE_PATHS = frozenset(
    {
        "src/lotto649/models/v11_previous_bonus_carryover.py",
        "src/lotto649/v11_diagnostics.py",
        "tools/run_v11_historical.py",
        "tests/test_v11_previous_bonus_carryover.py",
        "tests/test_v11_diagnostics.py",
    }
)
REQUIRED_STATUS_DOCUMENTATION_PATHS = frozenset(
    {
        "docs/CODEX_HANDOFF.md",
        "docs/MODEL_PROTOCOL.md",
        "docs/RESEARCH_ROADMAP.md",
    }
)
REQUIRED_IMPLEMENTATION_PATHS = (
    REQUIRED_SOURCE_PATHS | REQUIRED_STATUS_DOCUMENTATION_PATHS
)


def _validate_implementation_changed_paths(changed_text: str) -> list[str]:
    """Require exactly the registered five implementation and three status paths."""

    try:
        changed = [line for line in changed_text.splitlines() if line]
    except (AttributeError, UnicodeError) as exc:
        raise V11DiagnosticError("implementation changed paths are invalid") from exc
    if (
        len(changed) != len(set(changed))
        or set(changed) != REQUIRED_IMPLEMENTATION_PATHS
    ):
        raise V11DiagnosticError(
            "V11 implementation must change exactly eight registered paths"
        )
    return sorted(changed)


def _validate_status_documentation_blobs(
    path: str, registration_blob: bytes, current_blob: bytes
) -> dict[str, object]:
    """Allow only the four byte-exact frozen status replacements."""

    replacements = STATUS_DOCUMENT_REPLACEMENTS.get(path)
    if replacements is None:
        raise V11DiagnosticError("V11 status document path is not registered")
    if _sha256_bytes(registration_blob) != STATUS_DOCUMENT_REGISTRATION_SHA256[path]:
        raise V11DiagnosticError("V11 registered status document hash changed")
    expected = registration_blob
    for old, new in replacements:
        if expected.count(old) != 1 or new in registration_blob:
            raise V11DiagnosticError("V11 registered status phrase identity changed")
        expected = expected.replace(old, new, 1)
    if current_blob != expected:
        raise V11DiagnosticError(
            "V11 status document differs beyond exact frozen status replacements"
        )
    return {
        "path": path,
        "exact_status_replacements_only": True,
        "registration_sha256": _sha256_bytes(registration_blob),
        "current_sha256": _sha256_bytes(current_blob),
        "replacement_count": len(replacements),
    }


def _validate_registered_source_blob(
    captured_blob: bytes, git_blob: bytes, expected_sha256: str
) -> dict[str, object]:
    if git_blob != captured_blob:
        raise V11DiagnosticError(
            "registered Git source blob differs from captured bytes"
        )
    actual_sha256 = _sha256_bytes(captured_blob)
    if actual_sha256 != expected_sha256:
        raise V11DiagnosticError("registered Git source blob hash changed")
    return {
        "git_blob_byte_identical": True,
        "sha256": actual_sha256,
        "byte_count": len(captured_blob),
    }


def _run(
    *args: str,
    check: bool = True,
    timeout: float = 30.0,
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
        raise V11DiagnosticError(f"preflight command failed: {' '.join(args)}") from exc


def _git_bytes(*args: str) -> bytes:
    return _run("git", *args).stdout


def _git_text(*args: str) -> str:
    try:
        return _git_bytes(*args).decode("utf-8").strip()
    except UnicodeDecodeError as exc:
        raise V11DiagnosticError("Git preflight output is not UTF-8") from exc


def _resolve_registered_source_blob(source_commit: str, source_path: str) -> bytes:
    if (
        source_commit != REGISTERED_V11_IDENTITY.data_source_commit
        or source_path != REGISTERED_V11_IDENTITY.data_path
    ):
        raise V11DiagnosticError("registered source resolver identity changed")
    return _git_bytes("show", f"{source_commit}:{source_path}")


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_bytes(value: bytes) -> str:
    return sha256(value).hexdigest()


def _date_from_opaque_row(raw: bytes) -> date:
    try:
        return date.fromisoformat(raw.split(b",", 1)[0].decode("ascii"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise V11DiagnosticError("registered dataset row has invalid date") from exc


def _parse_csv_row(raw: bytes) -> Draw:
    try:
        values = next(csv.reader(io.StringIO(raw.decode("utf-8"))))
        if len(values) != 8:
            raise ValueError("wrong field count")
        return Draw(
            date.fromisoformat(values[0]),
            tuple(int(value) for value in values[1:7]),  # type: ignore[arg-type]
            int(values[7]),
        )
    except (UnicodeDecodeError, ValueError, csv.Error, StopIteration) as exc:
        raise V11DiagnosticError("registered dataset row is invalid") from exc


BaseBuilder = Callable[[tuple[Draw, ...], date, str], V1BaseSnapshot]
RandomBuilder = Callable[[tuple[Draw, ...], date], Mapping[int, float]]
BundleBuilder = Callable[
    [V1BaseSnapshot, tuple[V11Transition, ...], Draw], V11ForecastBundle
]


class SealedCsvFoldStore:
    """Expose target outcomes only through sequential post-receipt callbacks."""

    HEADER = b"draw_date,n1,n2,n3,n4,n5,n6,bonus\n"

    def __init__(
        self,
        registered_blob: bytes,
        *,
        expected_draw_count: int = EXPECTED_DATA_DRAW_COUNT,
        expected_history_through: date = EXPECTED_HISTORY_THROUGH,
        target_start: date = TARGET_START,
        target_end: date = TARGET_END,
        first_half_end: date = FIRST_HALF_END,
        expected_target_count: int = 621,
        expected_half_counts: tuple[int, int] = (307, 314),
        base_builder: BaseBuilder | None = None,
        random_builder: RandomBuilder | None = None,
        bundle_builder: BundleBuilder = forecast_v11_bundle,
    ) -> None:
        lines = registered_blob.splitlines(keepends=True)
        if not lines or lines[0] != self.HEADER:
            raise V11DiagnosticError("registered dataset header is not canonical")
        if len(lines) != expected_draw_count + 1 or any(
            not line.endswith(b"\n") for line in lines
        ):
            raise V11DiagnosticError("registered dataset row count changed")
        self._header = lines[0]
        self._rows = tuple(lines[1:])
        self._registered_blob = registered_blob
        self._expected_draw_count = expected_draw_count
        self._expected_history_through = expected_history_through
        prefix_hasher = sha256()
        prefix_hasher.update(self._header)
        prefix_hashes = [prefix_hasher.hexdigest()]
        for row in self._rows:
            prefix_hasher.update(row)
            prefix_hashes.append(prefix_hasher.hexdigest())
        self._prefix_hashes = tuple(prefix_hashes)
        self._dates = tuple(_date_from_opaque_row(row) for row in self._rows)
        if self._dates != tuple(sorted(self._dates)) or len(set(self._dates)) != len(
            self._dates
        ):
            raise V11DiagnosticError("registered dataset dates are not unique/ordered")
        if self._dates[-1] != expected_history_through:
            raise V11DiagnosticError("registered dataset history boundary changed")
        self._target_indices = tuple(
            index
            for index, draw_date in enumerate(self._dates)
            if target_start <= draw_date <= target_end
        )
        if len(self._target_indices) != expected_target_count:
            raise V11DiagnosticError("registered V11 target count changed")
        first_count = sum(
            self._dates[index] <= first_half_end for index in self._target_indices
        )
        if (
            first_count,
            len(self._target_indices) - first_count,
        ) != expected_half_counts:
            raise V11DiagnosticError("registered V11 half counts changed")
        if self._target_indices != tuple(
            range(self._target_indices[0], self._target_indices[-1] + 1)
        ):
            raise V11DiagnosticError("V11 targets are not a contiguous draw fold")
        self._current_index = self._target_indices[0]
        # Only rows strictly before the first target are decoded here.
        self._history = [
            _parse_csv_row(row) for row in self._rows[: self._current_index]
        ]
        self._base_builder = base_builder or self._production_base_builder
        self._random_builder = random_builder or self._production_random_builder
        self._bundle_builder = bundle_builder
        self._base_cache: dict[tuple[str, date], V1BaseSnapshot] = {}
        self._transition_cache: tuple[V11Transition, ...] = ()
        self._next_transition_destination_index = 1
        self._payload_cache: dict[date, dict[str, Any]] = {}
        self._preflight_evidence: Mapping[str, Any] | None = None
        self._v1_config = load_config(ROOT / V1_CONFIG)

    @property
    def target_dates(self) -> tuple[date, ...]:
        return tuple(self._dates[index] for index in self._target_indices)

    def _prefix_sha256(self, row_count: int) -> str:
        if type(row_count) is not int or not 0 <= row_count <= len(self._rows):
            raise V11DiagnosticError("V11 prefix row count is invalid")
        return self._prefix_hashes[row_count]

    def _production_base_builder(
        self, history: tuple[Draw, ...], target_date: date, prefix_sha256: str
    ) -> V1BaseSnapshot:
        # build_models creates a fresh V1 graph for this destination.  Only the
        # immutable resulting snapshot is cached by full-prefix hash + date.
        model = build_models(self._v1_config, requested=[V1_MODEL])[V1_MODEL]
        probabilities_map = model.predict(list(history), target_date)
        if set(probabilities_map) != set(range(1, 50)):
            raise V11DiagnosticError("V1 ensemble labels changed")
        probabilities = tuple(float(probabilities_map[label]) for label in range(1, 50))
        ranking = tuple(
            sorted(range(1, 50), key=lambda label: (-probabilities[label - 1], label))
        )
        return V1BaseSnapshot(
            target_date=target_date,
            history_draws=len(history),
            history_through=history[-1].draw_date,
            strict_prefix_sha256=prefix_sha256,
            probabilities=probabilities,
            ranking=ranking,
            top6=ranking[:6],
            top12=ranking[:12],
            top18=ranking[:18],
            final6=tuple(sorted(ranking[:6])),
        )

    @staticmethod
    def _production_random_builder(
        history: tuple[Draw, ...], target_date: date
    ) -> Mapping[int, float]:
        return RandomBaseline().predict(list(history), target_date)

    def _base_for(
        self, history: tuple[Draw, ...], target_date: date, prefix_sha256: str
    ) -> V1BaseSnapshot:
        key = (prefix_sha256, target_date)
        if key not in self._base_cache:
            self._base_cache[key] = self._base_builder(
                history, target_date, prefix_sha256
            )
        return self._base_cache[key]

    @staticmethod
    def _forecast_dict(forecast: V11Forecast) -> dict[str, Any]:
        return {
            "model_name": forecast.model_name,
            "model_version": forecast.model_version,
            "feature_set": FEATURE_SET_BY_MODEL[forecast.model_name],
            "target_date": forecast.target_date.isoformat(),
            "history_draws": forecast.history_draws,
            "history_through": (
                forecast.history_through.isoformat()
                if forecast.history_through is not None
                else None
            ),
            "anchor_source_date": forecast.anchor_source_date.isoformat(),
            "anchor_kind": forecast.anchor_kind,
            "anchor": forecast.anchor,
            "transition_count": forecast.transition_count,
            "D": forecast.transition_count,
            "beta": forecast.beta,
            "q_b": forecast.q_b,
            "r_b": forecast.r_b,
            "probabilities": {
                str(label): forecast.probabilities[label - 1] for label in range(1, 50)
            },
            "ranking": list(forecast.ranking),
            "top6": list(forecast.top6),
            "top12": list(forecast.top12),
            "top18": list(forecast.top18),
            "final6": list(forecast.final6),
        }

    @staticmethod
    def _base_forecast_dict(base: V1BaseSnapshot) -> dict[str, Any]:
        return {
            "model_name": V1_MODEL,
            "model_version": "v1.0.0",
            "feature_set": FEATURE_SET_BY_MODEL[V1_MODEL],
            "target_date": base.target_date.isoformat(),
            "history_draws": base.history_draws,
            "history_through": base.history_through.isoformat(),
            "strict_prefix_sha256": base.strict_prefix_sha256,
            "probabilities": {
                str(label): base.probabilities[label - 1] for label in range(1, 50)
            },
            "ranking": list(base.ranking),
            "top6": list(base.top6),
            "top12": list(base.top12),
            "top18": list(base.top18),
            "final6": list(base.final6),
        }

    @staticmethod
    def _random_forecast_dict(
        probabilities_map: Mapping[int, float],
        *,
        history: tuple[Draw, ...],
        target_date: date,
    ) -> dict[str, Any]:
        probabilities = tuple(float(probabilities_map[label]) for label in range(1, 50))
        ranking = tuple(
            sorted(range(1, 50), key=lambda label: (-probabilities[label - 1], label))
        )
        return {
            "model_name": RANDOM_MODEL,
            "model_version": "v1.0.0",
            "feature_set": FEATURE_SET_BY_MODEL[RANDOM_MODEL],
            "target_date": target_date.isoformat(),
            "history_draws": len(history),
            "history_through": history[-1].draw_date.isoformat(),
            "seed": 649_000_000 + target_date.toordinal(),
            "probabilities": {
                str(label): probabilities[label - 1] for label in range(1, 50)
            },
            "ranking": list(ranking),
            "top6": list(ranking[:6]),
            "top12": list(ranking[:12]),
            "top18": list(ranking[:18]),
            "final6": sorted(ranking[:6]),
        }

    def _visible_transitions(self) -> tuple[V11Transition, ...]:
        history = tuple(self._history)
        additions: list[V11Transition] = []
        while self._next_transition_destination_index < len(history):
            destination_index = self._next_transition_destination_index
            self._next_transition_destination_index += 1
            source = history[destination_index - 1]
            destination = history[destination_index]
            if source.draw_date < RNG_START or destination.draw_date < RNG_START:
                continue
            prefix_history = history[:destination_index]
            prefix_sha = self._prefix_sha256(destination_index)
            base = self._base_for(prefix_history, destination.draw_date, prefix_sha)
            additions.append(make_transition(base, source, destination))
        if additions:
            self._transition_cache = (*self._transition_cache, *additions)
        return self._transition_cache

    def build_forecasts(self, target_date: date) -> dict[str, Any]:
        if (
            self._current_index >= len(self._rows)
            or self._dates[self._current_index] != target_date
        ):
            raise V11DiagnosticError("V11 forecast requested outside sequential fold")
        if target_date in self._payload_cache:
            return deepcopy(self._payload_cache[target_date])
        history = tuple(self._history)
        if not history or history[-1].draw_date >= target_date:
            raise V11DiagnosticError("V11 history is not a strict non-empty prefix")
        prefix_sha = self._prefix_sha256(self._current_index)
        base = self._base_for(history, target_date, prefix_sha)
        transitions = self._visible_transitions()
        bundle = self._bundle_builder(base, transitions, history[-1])
        if bundle.base is not base:
            raise V11DiagnosticError("V11 arms did not share the exact V1 base object")
        candidate = self._forecast_dict(bundle.candidate)
        control = self._forecast_dict(bundle.control)
        pseudo_label, pseudo_digest = select_pseudo_bonus(history[-1])
        if control["anchor"] != pseudo_label:
            raise V11DiagnosticError("V11 pseudo-control anchor identity changed")
        control["pseudo_bonus_selection_sha256"] = pseudo_digest
        v1 = self._base_forecast_dict(base)
        random = self._random_forecast_dict(
            self._random_builder(history, target_date),
            history=history,
            target_date=target_date,
        )
        payload = {
            "target_date": target_date.isoformat(),
            "prefix": {
                "history_draws": len(history),
                "history_through": history[-1].draw_date.isoformat(),
                "strict_prefix_sha256": prefix_sha,
            },
            "forecasts": {
                CANDIDATE_MODEL: candidate,
                CONTROL_MODEL: control,
                V1_MODEL: v1,
                RANDOM_MODEL: random,
            },
        }
        self._payload_cache[target_date] = payload
        return deepcopy(payload)

    def reveal_actual(self, target_date: date) -> tuple[int, ...]:
        if self._dates[self._current_index] != target_date:
            raise V11DiagnosticError("V11 reveal requested outside sequential fold")
        if target_date not in self._payload_cache:
            raise V11DiagnosticError(
                "V11 reveal requested before forecast construction"
            )
        draw = _parse_csv_row(self._rows[self._current_index])
        self._history.append(draw)
        self._current_index += 1
        return draw.numbers

    def plans(self) -> tuple[V11TargetPlan, ...]:
        return tuple(
            V11TargetPlan(
                target_date,
                lambda target_date=target_date: self.build_forecasts(target_date),
                lambda target_date=target_date: self.reveal_actual(target_date),
            )
            for target_date in self.target_dates
        )

    def bind_preflight_evidence(self, evidence: Mapping[str, Any]) -> None:
        self._preflight_evidence = deepcopy(dict(evidence))

    def _counterfactual_replay(self, target_date: date) -> dict[str, Any]:
        target_index = self._dates.index(target_date)
        replacements = []
        replacement_rows = list(self._rows)
        for index in range(target_index, len(replacement_rows)):
            first = f"{self._dates[index].isoformat()},1,2,3,4,5,6,7\n".encode("ascii")
            second = f"{self._dates[index].isoformat()},44,45,46,47,48,49,43\n".encode(
                "ascii"
            )
            replacement = first if replacement_rows[index] != first else second
            replacements.append(replacement)
            replacement_rows[index] = replacement
        mutated_blob = self._header + b"".join(replacement_rows)
        replay_store = SealedCsvFoldStore(
            mutated_blob,
            expected_draw_count=self._expected_draw_count,
            expected_history_through=self._expected_history_through,
            target_start=target_date,
            target_end=target_date,
            first_half_end=target_date,
            expected_target_count=1,
            expected_half_counts=(1, 0),
            base_builder=self._base_builder,
            random_builder=self._random_builder,
            bundle_builder=self._bundle_builder,
        )
        replay = replay_store.build_forecasts(target_date)
        return {
            "payload": replay,
            "target_index": target_index,
            "replaced_target_and_future_row_count": len(replacements),
            "original_target_and_future_sha256": _sha256_bytes(
                b"".join(self._rows[target_index:])
            ),
            "counterfactual_target_and_future_sha256": _sha256_bytes(
                b"".join(replacements)
            ),
        }

    def leakage_audit(
        self,
        target_date: date,
        forecast_payload: Mapping[str, Any],
        actual: Sequence[int],
    ) -> dict[str, Any]:
        evidence = self._preflight_evidence or {}
        prefix = forecast_payload.get("prefix", {})
        replay = self._payload_cache.get(target_date)
        counterfactual = self._counterfactual_replay(target_date)
        counterfactual_payload = counterfactual["payload"]
        original_sha = canonical_sha256(forecast_payload)
        counterfactual_sha = canonical_sha256(counterfactual_payload)
        models_unchanged = {
            name: canonical_sha256(forecast_payload["forecasts"][name])
            == canonical_sha256(counterfactual_payload["forecasts"][name])
            for name in (CANDIDATE_MODEL, CONTROL_MODEL, V1_MODEL, RANDOM_MODEL)
        }
        checks = {
            "chronology": {
                "history_through": prefix.get("history_through"),
                "target_date": target_date.isoformat(),
                "strict": prefix.get("history_through") < target_date.isoformat(),
            },
            "target_exclusion": {
                "target_row_index": self._dates.index(target_date),
                "prefix_row_count": prefix.get("history_draws"),
                "target_outside_prefix": self._dates.index(target_date)
                == prefix.get("history_draws"),
                "counterfactual_target_and_future_rows_replaced": counterfactual[
                    "replaced_target_and_future_row_count"
                ],
                "counterfactual_suffix_differs": counterfactual[
                    "original_target_and_future_sha256"
                ]
                != counterfactual["counterfactual_target_and_future_sha256"],
            },
            "future_exclusion": {
                "forecast_prefix_sha256": prefix.get("strict_prefix_sha256"),
                "counterfactual_payload_sha256": counterfactual_sha,
                "original_payload_sha256": original_sha,
                "all_four_model_payloads_unchanged": all(models_unchanged.values()),
                "model_payloads_unchanged": models_unchanged,
            },
            "preprocessing": {
                "registered_blob_sha256": evidence.get("registered_blob_sha256"),
                "canonical_header": self._header == self.HEADER,
            },
            "feature_selection": {
                "registration_commit": REGISTRATION_COMMIT,
                "configuration_sha256": evidence.get("configuration_sha256"),
                "frozen_one_parameter_model": True,
            },
            "model_selection": {
                "registration_ancestor": evidence.get("registration_ancestor"),
                "changed_paths_verified": evidence.get("changed_paths_verified"),
            },
            "source_integrity": {
                "source_commit": evidence.get("source_commit"),
                "registered_draw_count": len(self._rows),
            },
            "git_runtime_integrity": {
                "exact_head": evidence.get("exact_head"),
                "remote_branch_head": evidence.get("remote_branch_head"),
                "ci_required_checks_passed": evidence.get("ci_required_checks_passed"),
                "runtime_versions_verified": evidence.get("runtime_versions_verified"),
            },
            "forecast_replay": {
                "forecast_sha256": original_sha,
                "cached_replay_sha256": canonical_sha256(replay) if replay else None,
                "byte_identical": replay is not None
                and canonical_sha256(replay) == original_sha,
                "counterfactual_replay_byte_identical": counterfactual_sha
                == original_sha,
            },
            "prefix_identity": {
                "recorded": prefix.get("strict_prefix_sha256"),
                "recomputed": self._prefix_sha256(self._dates.index(target_date)),
            },
        }
        normalized = []
        for name in (
            "chronology",
            "target_exclusion",
            "future_exclusion",
            "preprocessing",
            "feature_selection",
            "model_selection",
            "source_integrity",
            "git_runtime_integrity",
            "forecast_replay",
            "prefix_identity",
        ):
            item = checks[name]
            passed = all(
                value not in (None, False, "", [], {}) for value in item.values()
            )
            if name == "prefix_identity":
                passed = item["recorded"] == item["recomputed"]
            normalized.append({"name": name, "passed": passed, "evidence": item})
        return {
            "clear": all(item["passed"] for item in normalized),
            "checks": normalized,
        }


def _runtime_manifest() -> dict[str, Any]:
    distributions = sorted(
        {
            (
                distribution.metadata.get("Name") or "UNKNOWN",
                distribution.version,
            )
            for distribution in metadata.distributions()
        },
        key=lambda item: (item[0].lower(), item[1]),
    )
    installed = {name: version for name, version in distributions}
    lock_bytes = (ROOT / RUNTIME_LOCK).read_bytes()
    locked = _validate_runtime_versions(lock_bytes, installed)
    return {
        "implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "executable": sys.executable,
        "requirements_lock_path": RUNTIME_LOCK.as_posix(),
        "requirements_lock_sha256": _sha256_bytes(lock_bytes),
        "locked_distributions_verified": locked,
        "distributions": [
            {"name": name, "version": version} for name, version in distributions
        ],
    }


def _normalized_distribution_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _locked_versions(lock_bytes: bytes) -> dict[str, str]:
    try:
        lines = lock_bytes.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise V11DiagnosticError("runtime lock is not UTF-8") from exc
    locked: dict[str, str] = {}
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.count("==") != 1:
            raise V11DiagnosticError("runtime lock has a non-exact requirement")
        name, version = stripped.split("==", 1)
        normalized = _normalized_distribution_name(name)
        if not normalized or not version or normalized in locked:
            raise V11DiagnosticError("runtime lock has invalid/duplicate package")
        locked[normalized] = version
    if not locked:
        raise V11DiagnosticError("runtime lock has no frozen distributions")
    return locked


def _validate_runtime_versions(
    lock_bytes: bytes, installed_versions: Mapping[str, str]
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
        raise V11DiagnosticError(f"runtime distribution mismatch: {mismatches}")
    return locked


def _validate_ci_check_runs(checks: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    relevant = {
        name: [check for check in checks if check.get("name") == name]
        for name in REQUIRED_CHECK_RUNS
    }
    missing = {name for name, named in relevant.items() if not named}
    if missing:
        raise V11DiagnosticError(
            f"V11 required CI checks are not green: {sorted(missing)}"
        )
    non_green = {
        name: [
            {"status": check.get("status"), "conclusion": check.get("conclusion")}
            for check in named
            if not (
                check.get("status") == "completed"
                and check.get("conclusion") == "success"
            )
        ]
        for name, named in relevant.items()
        if any(
            not (
                check.get("status") == "completed"
                and check.get("conclusion") == "success"
            )
            for check in named
        )
    }
    if non_green:
        raise V11DiagnosticError(
            f"V11 required CI checks are not uniformly green: {non_green}"
        )
    return {
        "required": sorted(REQUIRED_CHECK_RUNS),
        "successful": sorted(REQUIRED_CHECK_RUNS),
    }


def _remote_repository() -> tuple[str, str]:
    remote = _git_text("remote", "get-url", "origin")
    match = re.search(r"github\.com[/:]([^/]+)/([^/]+?)(?:\.git)?$", remote)
    if not match:
        raise V11DiagnosticError("origin is not a parseable GitHub repository")
    return match.group(1), match.group(2)


def _validate_ci_green(commit: str) -> dict[str, Any]:
    owner, repository = _remote_repository()
    raw = _run(
        "gh",
        "api",
        f"repos/{owner}/{repository}/commits/{commit}/check-runs",
        "--paginate",
        timeout=60,
    ).stdout
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise V11DiagnosticError("GitHub check-runs response is invalid") from exc
    checks = payload.get("check_runs") if isinstance(payload, Mapping) else None
    if not isinstance(checks, list):
        raise V11DiagnosticError("GitHub check-runs response lacks check runs")
    return _validate_ci_check_runs(checks)


def _configuration_evidence() -> tuple[dict[str, Any], dict[str, Any]]:
    config = yaml.safe_load((ROOT / RESEARCH_CONFIG).read_text(encoding="utf-8"))
    registry = yaml.safe_load((ROOT / REGISTRY).read_text(encoding="utf-8"))
    if not isinstance(config, Mapping) or not isinstance(registry, Mapping):
        raise V11DiagnosticError("V11 config/registry is invalid")
    entries = [
        entry
        for entry in registry.get("experiments", [])
        if entry.get("id") == EXPERIMENT_ID
    ]
    if len(entries) != 1 or entries[0].get("parameters") != config.get("research"):
        raise V11DiagnosticError("V11 config and registry parameters differ")
    return dict(config), dict(entries[0])


def _preflight(
    store: SealedCsvFoldStore,
    registered_blob: bytes,
    invocation: Mapping[str, Any],
) -> dict[str, Any]:
    if platform.python_implementation() != "CPython" or sys.version_info[:2] != (3, 12):
        raise V11DiagnosticError("V11 historical run requires CPython 3.12")
    head = _git_text("rev-parse", "HEAD")
    if _git_text("status", "--porcelain=v1"):
        raise V11DiagnosticError("V11 historical run requires a clean worktree")
    if (
        _run(
            "git", "merge-base", "--is-ancestor", REGISTRATION_COMMIT, head, check=False
        ).returncode
        != 0
    ):
        raise V11DiagnosticError("V11 registration commit is not an ancestor")
    changed_text = _git_text("diff", "--name-only", f"{REGISTRATION_COMMIT}..{head}")
    changed_paths = _validate_implementation_changed_paths(changed_text)
    status_docs = {}
    for path in sorted(REQUIRED_STATUS_DOCUMENTATION_PATHS):
        registration_blob = _git_bytes("show", f"{REGISTRATION_COMMIT}:{path}")
        status_docs[path] = _validate_status_documentation_blobs(
            path, registration_blob, (ROOT / path).read_bytes()
        )
    branch = _git_text("branch", "--show-current")
    if not branch:
        raise V11DiagnosticError("V11 historical run requires a named branch")
    owner, repository = _remote_repository()
    try:
        remote_head = (
            _run(
                "gh",
                "api",
                f"repos/{owner}/{repository}/branches/{quote(branch, safe='')}",
                "--jq",
                ".commit.sha",
            )
            .stdout.decode("ascii")
            .strip()
        )
    except UnicodeDecodeError as exc:
        raise V11DiagnosticError("GitHub branch head is not ASCII") from exc
    if remote_head != head:
        raise V11DiagnosticError("V11 exact HEAD is not pushed to origin branch")
    registration_ci = _validate_ci_green(REGISTRATION_COMMIT)
    implementation_ci = _validate_ci_green(head)
    config, registry_entry = _configuration_evidence()
    if (
        RESEARCH_CONFIG.as_posix() != REGISTERED_V11_IDENTITY.research_config_path
        or _file_sha256(ROOT / RESEARCH_CONFIG)
        != REGISTERED_V11_IDENTITY.research_config_sha256
    ):
        raise V11DiagnosticError("frozen V11 research config hash changed")
    if (
        V1_CONFIG.as_posix() != REGISTERED_V11_IDENTITY.v1_base_config_path
        or _file_sha256(ROOT / V1_CONFIG)
        != REGISTERED_V11_IDENTITY.v1_base_config_sha256
    ):
        raise V11DiagnosticError("frozen V1 config hash changed")
    research = config["research"]
    expected_v1_files = [
        {"path": path, "sha256": digest}
        for path, digest in REGISTERED_V11_IDENTITY.v1_base_file_sha256
    ]
    if (
        research.get("v1_base_source_commit")
        != REGISTERED_V11_IDENTITY.v1_base_source_commit
        or research.get("v1_base_config_path")
        != REGISTERED_V11_IDENTITY.v1_base_config_path
        or research.get("v1_base_config_sha256")
        != REGISTERED_V11_IDENTITY.v1_base_config_sha256
        or research.get("v1_base_file_sha256") != expected_v1_files
    ):
        raise V11DiagnosticError("frozen V1 registered references changed")
    for item in expected_v1_files:
        if _file_sha256(ROOT / item["path"]) != item["sha256"]:
            raise V11DiagnosticError(f"frozen V1 source hash changed: {item['path']}")
    if (
        RUNTIME_LOCK.as_posix() != REGISTERED_V11_IDENTITY.runtime_lock_path
        or _file_sha256(ROOT / RUNTIME_LOCK)
        != REGISTERED_V11_IDENTITY.runtime_lock_sha256
    ):
        raise V11DiagnosticError("runtime lock hash changed")
    registered_data = config.get("data", {})
    if (
        DATASET.as_posix() != REGISTERED_V11_IDENTITY.data_path
        or registered_data.get("processed_csv") != REGISTERED_V11_IDENTITY.data_path
        or registered_data.get("registered_source_commit")
        != REGISTERED_V11_IDENTITY.data_source_commit
        or registered_data.get("registered_sha256")
        != REGISTERED_V11_IDENTITY.data_sha256
        or registered_data.get("registered_draw_count")
        != REGISTERED_V11_IDENTITY.data_draw_count
        or str(registered_data.get("registered_history_through"))
        != REGISTERED_V11_IDENTITY.data_history_through
    ):
        raise V11DiagnosticError("frozen registered data identity changed")
    source_commit = REGISTERED_V11_IDENTITY.data_source_commit
    for descendant, label in (
        (REGISTRATION_COMMIT, "registration"),
        (head, "implementation"),
    ):
        if (
            _run(
                "git",
                "merge-base",
                "--is-ancestor",
                source_commit,
                descendant,
                check=False,
            ).returncode
            != 0
        ):
            raise V11DiagnosticError(
                f"V11 registered source commit is not an ancestor of {label}"
            )
    source_blob = _git_bytes("show", f"{source_commit}:{DATASET.as_posix()}")
    source_blob_evidence = _validate_registered_source_blob(
        registered_blob, source_blob, EXPECTED_DATA_SHA256
    )
    data_sha = source_blob_evidence["sha256"]
    if store.target_dates[0] != TARGET_START or store.target_dates[-1] != TARGET_END:
        raise V11DiagnosticError("registered V11 target boundaries changed")
    preflight_v11_model()
    runtime = _runtime_manifest()
    evidence = {
        "exact_head": head,
        "remote_branch_head": remote_head,
        "registration_ancestor": True,
        "changed_paths_verified": True,
        "ci_required_checks_passed": True,
        "runtime_versions_verified": True,
        "registered_blob_sha256": data_sha,
        "configuration_sha256": REGISTERED_V11_IDENTITY.research_config_sha256,
        "source_commit": source_commit,
    }
    store.bind_preflight_evidence(evidence)
    return {
        "passed": True,
        "audit_warnings": [],
        "registration_commit": REGISTRATION_COMMIT,
        "implementation_commit": head,
        "git": {
            "branch": branch,
            "exact_head": head,
            "remote_branch_head": remote_head,
            "registration_ancestor": True,
            "changed_paths": changed_paths,
            "status_documentation": status_docs,
            "ci": {
                "registration": registration_ci,
                "implementation": implementation_ci,
            },
        },
        "configuration": {
            "path": REGISTERED_V11_IDENTITY.research_config_path,
            "sha256": evidence["configuration_sha256"],
            "registry_parameters_equal": True,
            "registry_status": registry_entry["status"],
            "v1_base_source_commit": REGISTERED_V11_IDENTITY.v1_base_source_commit,
            "v1_base_config_path": REGISTERED_V11_IDENTITY.v1_base_config_path,
            "v1_base_config_sha256": (REGISTERED_V11_IDENTITY.v1_base_config_sha256),
            "v1_base_file_sha256": expected_v1_files,
        },
        "data": {
            "path": DATASET.as_posix(),
            "sha256": data_sha,
            "draw_count": EXPECTED_DATA_DRAW_COUNT,
            "history_through": EXPECTED_HISTORY_THROUGH.isoformat(),
            "source_commit": source_commit,
            "source_commit_ancestor_of_registration": True,
            "source_commit_ancestor_of_implementation": True,
            "source_git_blob": source_blob_evidence,
            "target_count": len(store.target_dates),
            "fixed_half_counts": [307, 314],
        },
        "runtime": {**runtime, "lock_sha256": EXPECTED_LOCK_SHA256},
        "invocation": dict(invocation),
        "references": {},
    }


class GitHubWorkflowNotifier:
    """Dispatch an already-durable outbox request through the email workflow."""

    def __init__(self, expected_implementation_commit: str) -> None:
        self._expected_implementation_commit = expected_implementation_commit

    def __call__(self, subject: str, body: str) -> bool:
        owner, repository = _remote_repository()
        branch = _git_text("branch", "--show-current")
        try:
            branch_head = (
                _run(
                    "gh",
                    "api",
                    f"repos/{owner}/{repository}/branches/{quote(branch, safe='')}",
                    "--jq",
                    ".commit.sha",
                    timeout=30,
                )
                .stdout.decode("ascii")
                .strip()
            )
        except UnicodeDecodeError as exc:
            raise V11DiagnosticError("notification branch head is not ASCII") from exc
        if branch_head != self._expected_implementation_commit:
            raise V11DiagnosticError(
                "notification branch drifted from preflight implementation commit"
            )
        _run(
            "gh",
            "workflow",
            "run",
            ".github/workflows/email-test.yml",
            "--repo",
            f"{owner}/{repository}",
            "--ref",
            branch,
            "-f",
            f"subject={subject}",
            "-f",
            f"body={body}",
            timeout=60,
        )
        return True


def _canonical_invocation(
    argv: Sequence[str],
    *,
    cwd: Path | None = None,
    runtime_executable: str | None = None,
    implementation: str | None = None,
    version_info: Sequence[int] | None = None,
) -> dict[str, Any]:
    actual_cwd = Path.cwd() if cwd is None else cwd
    actual_executable = (
        sys.executable if runtime_executable is None else runtime_executable
    )
    actual_implementation = (
        platform.python_implementation() if implementation is None else implementation
    )
    actual_version = sys.version_info if version_info is None else version_info
    expected_tool = (
        ROOT / REGISTERED_V11_IDENTITY.command_tool_relative_path
    ).resolve()
    expected_arguments = [
        "--consume-v11-once",
        "--output-dir",
        REGISTERED_V11_IDENTITY.command_output_relative_path,
    ]
    if (
        actual_cwd.resolve() != ROOT.resolve()
        or len(argv) != 4
        or Path(argv[0]).resolve() != expected_tool
        or list(argv[1:]) != expected_arguments
        or actual_implementation != "CPython"
        or tuple(actual_version[:2]) != (3, 12)
        or not actual_executable
    ):
        raise V11DiagnosticError("V11 production invocation is not canonical")
    return {
        "logical_command": registered_v11_command(REGISTERED_V11_IDENTITY),
        "runtime_executable": actual_executable,
        "tool_relative_path": REGISTERED_V11_IDENTITY.command_tool_relative_path,
        "arguments": expected_arguments,
        "output_relative_path": (REGISTERED_V11_IDENTITY.command_output_relative_path),
        "working_directory_relative_to_root": ".",
    }


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the sole registered V11 consumed historical diagnostic"
    )
    parser.add_argument(
        "--consume-v11-once",
        action="store_true",
        help="required explicit acknowledgement that claim acquisition is permanent",
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    invocation = _canonical_invocation(sys.argv)
    args = _arguments()
    if not args.consume_v11_once:
        raise V11DiagnosticError("refusing without --consume-v11-once")
    if args.output_dir.resolve() != (ROOT / "reports").resolve():
        raise V11DiagnosticError(
            "V11 artifacts must use the registered reports directory"
        )
    registered_blob = (ROOT / DATASET).read_bytes()
    store = SealedCsvFoldStore(registered_blob)
    head = _git_text("rev-parse", "HEAD")
    request = V11DiagnosticRequest(
        root=ROOT,
        output_dir=args.output_dir.resolve(),
        code_commit=head,
        exact_command=registered_v11_command(REGISTERED_V11_IDENTITY),
        targets=store.plans(),
        preflight=lambda: _preflight(store, registered_blob, invocation),
        reference={},
        expected_target_count=621,
        stability_scopes=(
            V11Scope("first_307", TARGET_START, FIRST_HALF_END, 307),
            V11Scope("second_314", date(2023, 1, 1), TARGET_END, 314),
        ),
        bootstrap_replicates=10_000,
        bootstrap_seed=649,
        notifier=GitHubWorkflowNotifier(head),
        leakage_audit=store.leakage_audit,
        source_blob_resolver=_resolve_registered_source_blob,
        registered_identity=REGISTERED_V11_IDENTITY,
    )
    result = run_v11_historical(request)
    public_result = {key: value for key, value in result.items() if key != "report"}
    print(json.dumps(public_result, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
