"""Fixed, isolated launcher for the registered V12.0.1 historical attempt.

The launcher is not authorization. The registered verifier must still prove
protected-main authority and acquire the one-shot lease before any history read.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import sysconfig
from pathlib import Path

_FLAG = "--consume-v12-0-1-once"
_ROUTING_OVERRIDES = ("SMTP_HOST", "SMTP_PORT", "EMAIL_FROM", "EMAIL_TO")
_SECRET_NAMES = ("GH_TOKEN", "SMTP_USERNAME", "SMTP_PASSWORD")
_FIXED_ENVIRONMENT = {
    "GIT_CONFIG_COUNT": "0",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_SYSTEM": os.devnull,
    "GIT_GRAFT_FILE": os.devnull,
    "GIT_NO_LAZY_FETCH": "1",
    "GIT_NO_REPLACE_OBJECTS": "1",
    "GIT_OPTIONAL_LOCKS": "0",
    "GIT_TERMINAL_PROMPT": "0",
    "LANG": "C",
    "LC_ALL": "C",
    "PATH": "/usr/bin:/bin",
    "TMPDIR": "/tmp",
}
_INITIAL_SOURCES = (
    "tools/run_v12_0_1_historical.py",
    "src/lotto649/__init__.py",
    "src/lotto649/v12_0_1_registered_attempt.py",
)


def _git(root: Path, *arguments: str) -> bytes:
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
        env=_FIXED_ENVIRONMENT,
        check=False,
        capture_output=True,
        timeout=60,
    )
    if completed.returncode:
        raise RuntimeError("launcher requires intact immutable Git objects")
    return completed.stdout


def _verify_initial_sources(root: Path) -> None:
    if (root / ".git").is_symlink() or not (root / ".git").is_dir():
        raise RuntimeError("launcher requires an independent complete clone")
    if _git(root, "rev-parse", "--is-shallow-repository").strip() != b"false":
        raise RuntimeError("launcher refuses shallow history")
    head = _git(root, "rev-parse", "--verify", "HEAD").decode("ascii").strip()
    if re.fullmatch(r"[0-9a-f]{40}", head) is None:
        raise RuntimeError("launcher requires a complete SHA-1 commit identity")
    for relative in _INITIAL_SOURCES:
        source = root / relative
        if any(part.is_symlink() for part in (source, *source.parents)):
            raise RuntimeError("launcher refuses source symlinks")
        entry = _git(root, "ls-tree", "-z", head, "--", relative)
        metadata, path = entry.rstrip(b"\0").split(b"\t")
        mode, kind, _oid = metadata.split(b" ")
        if mode != b"100644" or kind != b"blob" or path.decode() != relative:
            raise RuntimeError("launcher source is not a registered plain file")
        if source.read_bytes() != _git(root, "show", f"{head}:{relative}"):
            raise RuntimeError("launcher refuses uncommitted source bytes")
    if any((root / "src").rglob("*.pyc")):
        raise RuntimeError("launcher requires a fresh source checkout without bytecode")


def main() -> int:
    if sys.argv[1:] != [_FLAG]:
        print(f"Usage: python3.12 tools/run_v12_0_1_historical.py {_FLAG}")
        return 2
    if sys.implementation.name != "cpython" or sys.version_info[:2] != (3, 12):
        print("V12.0.1 requires the registered CPython 3.12 runtime.", file=sys.stderr)
        return 2
    if any(name in os.environ for name in _ROUTING_OVERRIDES):
        print(
            "V12.0.1 accepts only the repository default SMTP route.", file=sys.stderr
        )
        return 2
    source = Path(__file__).absolute()
    root = source.parent.parent
    if not (sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode):
        environment = dict(_FIXED_ENVIRONMENT)
        for name in _SECRET_NAMES:
            if name in os.environ:
                environment[name] = os.environ[name]
        os.execve(
            sys.executable,
            [sys.executable, "-I", "-S", "-B", str(source), _FLAG],
            environment,
        )
        return 2
    try:
        _verify_initial_sources(root)
        paths = []
        for key in ("purelib", "platlib"):
            value = sysconfig.get_path(key)
            if value:
                paths.append(Path(value))
        prefix = Path(sys.executable).absolute().parent.parent
        version = f"python{sys.version_info.major}.{sys.version_info.minor}"
        paths.extend(
            (
                prefix / "lib" / version / "site-packages",
                prefix / "Lib" / "site-packages",
            )
        )
        for path in paths:
            if path.is_dir():
                candidate = str(path.resolve(strict=True))
                if candidate not in sys.path:
                    sys.path.append(candidate)
        sys.path.insert(0, str((root / "src").resolve(strict=True)))
        from lotto649.v12_0_1_registered_attempt import main as registered_main

        return registered_main()
    except Exception:  # noqa: BLE001 -- never expose authenticated exception text.
        # Failure text is deliberately fixed: transport/runtime exceptions may
        # otherwise contain environment values or authenticated request details.
        print(
            "V12.0.1 stopped before returning a verified result; do not retry.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
