#!/usr/bin/env python3
"""Execute the reviewed live output seam from the authenticated P checkout."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import sysconfig
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType


class PublishedWorkerError(RuntimeError):
    """Raised when this process is not running only reviewed code from P."""


def _dependency_paths() -> tuple[str, ...]:
    """Find installed libraries without importing site or executing .pth files."""

    candidates: list[Path] = []
    for key in ("purelib", "platlib"):
        value = sysconfig.get_path(key)
        if type(value) is str and value:
            candidates.append(Path(value))
    executable_prefix = Path(sys.executable).absolute().parent.parent
    version = f"python{sys.version_info.major}.{sys.version_info.minor}"
    candidates.extend(
        (
            executable_prefix / "lib" / version / "site-packages",
            executable_prefix / "Lib" / "site-packages",
        )
    )
    result: list[str] = []
    for candidate in candidates:
        try:
            canonical = str(candidate.resolve(strict=True))
        except (OSError, RuntimeError):
            continue
        if canonical not in result:
            result.append(canonical)
    return tuple(result)


def _instant(raw: str) -> datetime:
    try:
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


def _module_inventory(root: Path) -> list[dict[str, str]]:
    package_root = (root / "src" / "lotto649").resolve(strict=True)
    inventory: list[dict[str, str]] = []
    for name, module in tuple(sys.modules.items()):
        if name != "lotto649" and not name.startswith("lotto649."):
            continue
        if type(module) is not ModuleType or type(module.__file__) is not str:
            raise PublishedWorkerError("lotto649 module origin is unavailable")
        try:
            origin = Path(module.__file__).resolve(strict=True)
            origin.relative_to(package_root)
        except (OSError, RuntimeError, TypeError, ValueError) as exc:
            raise PublishedWorkerError(
                "lotto649 module was not imported from P/src"
            ) from exc
        if origin.suffix != ".py":
            raise PublishedWorkerError("lotto649 module origin is not source code")
        raw = origin.read_bytes()
        relative = origin.relative_to(root).as_posix()
        inventory.append(
            {
                "git_blob": hashlib.sha1(
                    f"blob {len(raw)}\0".encode("ascii") + raw,
                    usedforsecurity=False,
                ).hexdigest(),
                "name": name,
                "path": relative,
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    inventory.sort(key=lambda entry: entry["name"])
    if len({entry["name"] for entry in inventory}) != len(inventory):
        raise PublishedWorkerError("lotto649 module inventory is ambiguous")
    return inventory


def run_worker(root: Path, *, generated_at: datetime) -> dict[str, object]:
    try:
        canonical_root = root.resolve(strict=True)
        source = (canonical_root / "src").resolve(strict=True)
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        raise PublishedWorkerError("P checkout is unavailable") from exc
    if source.parent != canonical_root:
        raise PublishedWorkerError("P source root is invalid")
    if any(name == "lotto649" or name.startswith("lotto649.") for name in sys.modules):
        _module_inventory(canonical_root)
    for candidate in _dependency_paths():
        if candidate not in sys.path:
            sys.path.append(candidate)
    source_text = str(source)
    if source_text in sys.path:
        sys.path.remove(source_text)
    sys.path.insert(0, source_text)

    from lotto649.config import load_config
    from lotto649.live import _run_verified_live_outputs
    from lotto649.operational_history import load_operational_history

    _module_inventory(canonical_root)
    cfg = load_config(canonical_root / "config.yaml")
    if Path(cfg.get("_root", "")).resolve(strict=True) != canonical_root:
        raise PublishedWorkerError("P configuration root is invalid")
    if (
        type(cfg.get("live")) is not dict
        or cfg["live"].get("enabled") is not True
        or type(cfg.get("data")) is not dict
        or cfg["data"].get("refresh_enabled") is not True
    ):
        raise PublishedWorkerError("P live-cycle gates are not explicitly enabled")
    history = load_operational_history(cfg)
    publication = history.registry.resolved_revision
    if history.registry.publication_commit != publication:
        raise PublishedWorkerError("P history publication identity is inconsistent")
    paths = _run_verified_live_outputs(
        cfg,
        history,
        generated_at=generated_at,
    )
    modules = _module_inventory(canonical_root)
    if type(paths) is not tuple:
        raise PublishedWorkerError("P live output paths have the wrong type")
    return {
        "modules": modules,
        "paths": list(paths),
        "publication_commit": publication,
    }


def _main() -> int:
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--generated-at", required=True)
    arguments = parser.parse_args()
    try:
        root = Path(__file__).resolve(strict=True).parents[1]
        payload = run_worker(root, generated_at=_instant(arguments.generated_at))
        raw = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except Exception:  # noqa: BLE001 - keep worker failures secret-free
        sys.stderr.write("published live output execution failed\n")
        return 1
    sys.stdout.write(raw + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
