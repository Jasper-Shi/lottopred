"""Private exact-P worker for verified live output creation.

This module deliberately has no module/CLI entry point. The production parent
imports it from a detached, clean P checkout through a fixed isolated bootstrap.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType

_FIXED_ENV = {
    "GIT_CONFIG_COUNT": "0",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_SYSTEM": os.devnull,
    "GIT_GRAFT_FILE": os.devnull,
    "GIT_NO_LAZY_FETCH": "1",
    "GIT_NO_REPLACE_OBJECTS": "1",
    "LANG": "C",
    "LC_ALL": "C",
    "PATH": "/usr/bin:/bin",
    "TMPDIR": "/tmp",
}


class PublishedWorkerError(RuntimeError):
    """Raised when the process is not a clean detached exact-P execution."""


def _instant(raw: object) -> datetime:
    try:
        if type(raw) is not str:
            raise ValueError("not text")
        value = datetime.fromisoformat(raw)
        if (
            value.isoformat() != raw
            or value.microsecond != 0
            or value.utcoffset() is None
            or value.utcoffset().total_seconds() != 0
        ):
            raise ValueError("invalid timestamp")
    except (OverflowError, TypeError, ValueError) as exc:
        raise PublishedWorkerError(
            "generated_at must be a whole-second UTC datetime"
        ) from exc
    return value.astimezone(UTC)


def _git(root: Path, *arguments: str, allowed_codes: tuple[int, ...] = (0,)):
    completed = subprocess.run(
        [
            "git",
            "-c",
            "advice.graftFileDeprecated=false",
            "-C",
            str(root),
            *arguments,
        ],
        check=False,
        capture_output=True,
        env=_FIXED_ENV,
        timeout=120,
    )
    if completed.returncode not in allowed_codes or completed.stderr:
        raise PublishedWorkerError("P Git state could not be proven")
    return completed


def _require_clean_detached_p(root: Path) -> str:
    head = _git(root, "rev-parse", "HEAD").stdout.decode("ascii").strip()
    symbolic = _git(root, "symbolic-ref", "-q", "HEAD", allowed_codes=(1,))
    status = _git(
        root,
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
    )
    if symbolic.stdout or status.stdout:
        raise PublishedWorkerError("P checkout must start clean and detached")
    return head


def _module_inventory(root: Path) -> list[dict[str, str]]:
    package_root = (root / "src" / "lotto649").resolve(strict=True)
    inventory: list[dict[str, str]] = []
    for name, module in tuple(sys.modules.items()):
        if name != "lotto649" and not name.startswith("lotto649."):
            continue
        if type(module) is not ModuleType or type(module.__file__) is not str:
            raise PublishedWorkerError("lotto649 module origin is unavailable")
        origin = Path(module.__file__).resolve(strict=True)
        try:
            origin.relative_to(package_root)
        except ValueError as exc:
            raise PublishedWorkerError(
                "lotto649 module was not imported from P/src"
            ) from exc
        if origin.suffix != ".py":
            raise PublishedWorkerError("lotto649 module origin is not source code")
        raw = origin.read_bytes()
        inventory.append(
            {
                "git_blob": hashlib.sha1(
                    f"blob {len(raw)}\0".encode("ascii") + raw,
                    usedforsecurity=False,
                ).hexdigest(),
                "name": name,
                "path": origin.relative_to(root).as_posix(),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    inventory.sort(key=lambda entry: entry["name"])
    return inventory


def _main(root_value: object, generated_at_value: object) -> int:
    """Run only after the parent has installed P/src in isolated sys.path."""

    try:
        root = Path(root_value).resolve(strict=True)
        generated_at = _instant(generated_at_value)
        publication = _require_clean_detached_p(root)

        from lotto649.config import load_config
        from lotto649.live import _evaluate_due_predictions, _generate_next_predictions
        from lotto649.operational_history import load_operational_history

        cfg = load_config(root / "config.yaml")
        if Path(cfg.get("_root", "")).resolve(strict=True) != root:
            raise PublishedWorkerError("P configuration root is invalid")
        if (
            type(cfg.get("live")) is not dict
            or cfg["live"].get("enabled") is not True
            or type(cfg.get("data")) is not dict
            or cfg["data"].get("refresh_enabled") is not True
        ):
            raise PublishedWorkerError("P live gates are not explicitly enabled")
        history = load_operational_history(cfg)
        if (
            history.registry.resolved_revision != publication
            or history.registry.publication_commit != publication
        ):
            raise PublishedWorkerError("P history identity is inconsistent")
        evaluations = _evaluate_due_predictions(cfg, history)
        predictions = _generate_next_predictions(
            cfg,
            history,
            generated_at=generated_at,
        )
        paths = [
            (
                Path("evaluations")
                / (
                    f"{evaluation['target_draw_date']}__"
                    f"{evaluation['model_name']}__"
                    f"{evaluation['model_version']}.json"
                )
            ).as_posix()
            for evaluation in evaluations
        ]
        for path in predictions:
            paths.append(Path(path).relative_to(root).as_posix())
        payload = {
            "modules": _module_inventory(root),
            "paths": sorted(paths),
            "publication_commit": publication,
        }
        raw = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except Exception:  # noqa: BLE001 - never echo secrets or raw failure values
        sys.stderr.write("published live output execution failed\n")
        return 1
    sys.stdout.write(raw + "\n")
    return 0
