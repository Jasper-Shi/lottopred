"""One-shot V12.0.1 authority, durable ordering, and fixed GitHub boundary.

Importing this module cannot instantiate the registered attempt.  Only ``main``
can enter the canonical path; every external identity is checked before a lease,
and a permanent exclusive claim precedes the governed-history read.  The small
synthetic driver uses a different namespace and has no authorization capability.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import platform
import re
import secrets
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from importlib.metadata import distributions
from itertools import pairwise
from pathlib import Path, PurePosixPath
from threading import Lock
from typing import Any

REPOSITORY = "Jasper-Shi/lottopred"
REPOSITORY_NODE_ID = "R_kgDOT41pdQ"
R2 = "89c7b2857e2fffa83a9e62ab402cf4b88f9b16be"
R1 = "0af20fc41fc5aaa0879dada0a258797a8bc14e20"
HISTORY_AUTHORITY = "4a617f2c1575a165b42878600753a01ddf2ced03"
CORE_PATH = "src/lotto649/models/v12_parity_transition.py"
CORE_SHA256 = "fae93e0a6f76c6604eabe24f6b93676e22e87d7e567365b382484433fba2eb77"
FINGERPRINT = "af2e16a55ff0e817cf71208471e19e4f481bed63990f7e41268997c4c4b35c76"
REQUIREMENTS_PATH = "requirements/v12-historical.txt"
REQUIREMENTS_SHA256 = "a0dfeac17ad7e1c41dffe4b41b4810156fb028f879d312430bfc517672a570c6"
R1_PATH = (
    "evidence/research_registrations/v12-post-rng-parity-composition-transition-v1.json"
)
R2_PATH = (
    "evidence/research_registrations/v12-post-rng-parity-composition-transition-v2.json"
)
CONFIG_PATH = "config/research-v12-0-1-post-rng-parity-composition-transition.yaml"
AUTHORIZATION_PATH = "evidence/research_authorizations/v12-post-rng-parity-composition-transition-v2-historical.json"
LEASE_REF = "refs/heads/v12-consumption-v12.0.1"
COMMAND = ["python3.12", "tools/run_v12_0_1_historical.py", "--consume-v12-0-1-once"]
IMPLEMENTATION_PATHS = (
    CORE_PATH,
    "src/lotto649/v12_0_1_evidence.py",
    "src/lotto649/v12_0_1_registered_attempt.py",
    "tools/run_v12_0_1_historical.py",
    "tests/test_v12_0_1_parity_transition.py",
    "tests/test_v12_0_1_registered_attempt.py",
)
_STEM = "v12_post_rng_parity_composition_transition_v12.0.1_historical"
_ARTIFACT_NAMES = {
    "claim": _STEM + ".claim",
    "ledger": _STEM + ".ledger.jsonl",
    "json": _STEM + ".json",
    "markdown": _STEM + ".md",
    "json_staging": _STEM + ".json.staging",
    "markdown_staging": _STEM + ".md.staging",
    "commit": _STEM + ".commit.json",
    "commit_staging": _STEM + ".commit.json.staging",
}
_API_PREFIX = "/repos/Jasper-Shi/lottopred"
_API_ORIGIN = "https://api.github.com"
_OID = re.compile(r"[0-9a-f]{40}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_ROUTE_OVERRIDES = frozenset({"SMTP_HOST", "SMTP_PORT", "EMAIL_FROM", "EMAIL_TO"})
_EXTERNAL_MODULES = frozenset(
    {"numpy", "pandas", "requests", "yaml", "sklearn", "scipy", "bs4", "pypdf"}
)
_CLOSURE_ROOTS = (
    "config.yaml",
    CONFIG_PATH,
    R1_PATH,
    R2_PATH,
    REQUIREMENTS_PATH,
    "src/lotto649/config.py",
    "src/lotto649/domain.py",
    "src/lotto649/features.py",
    "src/lotto649/research_features.py",
    "src/lotto649/models/factory.py",
    "src/lotto649/notification.py",
    "src/lotto649/operational_history.py",
    *IMPLEMENTATION_PATHS[:4],
)


_CAPABILITY_LOCK = Lock()
_ISSUED_AUTHORITIES: list[tuple[Any, bytes]] = []
_USED_AUTHORITIES: list[Any] = []
_ISSUED_LEASES: list[tuple[Any, Any, tuple[str, str, str]]] = []
_USED_LEASES: list[Any] = []
_ACTIVE_ATTEMPTS: list[Any] = []


class AuthorizationError(RuntimeError):
    """An authority or runtime fact could not be proved without execution."""


class AttemptError(RuntimeError):
    """The permanent attempt cannot proceed or be retried."""


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise AuthorizationError("duplicate JSON key")
        result[key] = value
    return result


def _invalid_constant(_value: str) -> None:
    raise AuthorizationError("nonfinite JSON value")


def _json(raw: bytes) -> dict[str, Any]:
    try:
        result = json.loads(
            raw, object_pairs_hook=_object_pairs, parse_constant=_invalid_constant
        )
    except (ValueError, UnicodeError) as exc:
        raise AuthorizationError("invalid JSON evidence") from exc
    if type(result) is not dict:
        raise AuthorizationError("JSON evidence must be an object")
    return result


def _oid(value: object) -> str:
    if type(value) is not str or _OID.fullmatch(value) is None:
        raise AuthorizationError("a complete immutable SHA-1 is required")
    return value


def _digest(value: object) -> str:
    if type(value) is not str or _SHA256.fullmatch(value) is None:
        raise AuthorizationError("a complete SHA-256 is required")
    return value


def _relative(path: str) -> str:
    parsed = PurePosixPath(path)
    if (
        not path
        or parsed.is_absolute()
        or str(parsed) != path
        or ".." in parsed.parts
        or "\\" in path
        or "\x00" in path
    ):
        raise AuthorizationError("unsafe repository path")
    return path


def _git_environment() -> dict[str, str]:
    return {
        "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
        "LANG": "C",
        "LC_ALL": "C",
        "GIT_CONFIG_COUNT": "0",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_SYSTEM": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_GRAFT_FILE": os.devnull,
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_NO_LAZY_FETCH": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_ATTR_NOSYSTEM": "1",
    }


@dataclass(frozen=True)
class GitRepository:
    root: Path

    def run(self, *arguments: str, input_bytes: bytes | None = None) -> bytes:
        try:
            result = subprocess.run(
                [
                    "/usr/bin/git",
                    "-c",
                    "core.hooksPath=/dev/null",
                    "-c",
                    "core.fsmonitor=false",
                    "-C",
                    str(self.root),
                    *arguments,
                ],
                input=input_bytes,
                capture_output=True,
                check=False,
                env=_git_environment(),
                timeout=120,
            )
        except (OSError, subprocess.SubprocessError):
            raise AuthorizationError("safe Git operation failed") from None
        if result.returncode != 0:
            raise AuthorizationError("immutable Git evidence unavailable")
        return result.stdout

    def text(self, *arguments: str) -> str:
        try:
            return self.run(*arguments).decode("ascii").strip()
        except UnicodeError as exc:
            raise AuthorizationError("invalid Git metadata") from exc

    def head(self) -> str:
        return _oid(self.text("rev-parse", "--verify", "HEAD"))

    def parents(self, commit: str) -> tuple[str, ...]:
        return tuple(
            _oid(item)
            for item in self.text("show", "-s", "--format=%P", _oid(commit)).split()
        )

    def tree(self, commit: str) -> str:
        return _oid(self.text("rev-parse", _oid(commit) + "^{tree}"))

    def oid(self, commit: str, path: str) -> str:
        entries = self.run("ls-tree", "-z", _oid(commit), "--", _relative(path)).split(
            b"\0"
        )
        if len(entries) != 2 or entries[-1] != b"":
            raise AuthorizationError("missing or ambiguous Git blob")
        metadata, observed_path = entries[0].split(b"\t", 1)
        mode, kind, blob = metadata.decode("ascii").split()
        if (
            observed_path.decode("utf-8") != path
            or mode not in {"100644", "100755"}
            or kind != "blob"
        ):
            raise AuthorizationError("runtime path is not an ordinary Git blob")
        return _oid(blob)

    def read_blob(self, commit: str, path: str) -> bytes:
        return self.run("cat-file", "blob", self.oid(commit, path))

    def ancestor(self, earlier: str, later: str) -> bool:
        return self.text("merge-base", _oid(earlier), _oid(later)) == earlier

    def changes(self, earlier: str, later: str) -> list[tuple[str, str]]:
        raw = self.run(
            "diff-tree",
            "--no-commit-id",
            "--no-renames",
            "-r",
            "--name-status",
            "-z",
            _oid(earlier),
            _oid(later),
        ).split(b"\0")
        if raw[-1] != b"" or len(raw[:-1]) % 2:
            raise AuthorizationError("invalid Git tree difference")
        return [
            (raw[i].decode("ascii"), raw[i + 1].decode("utf-8"))
            for i in range(0, len(raw) - 1, 2)
        ]

    def require_full_clean(self) -> None:
        git_directory = self.root / ".git"
        if not git_directory.is_dir() or any(
            parent.is_symlink() for parent in (git_directory, *git_directory.parents)
        ):
            raise AuthorizationError("an independent nonsymlink Git clone is required")
        if any(
            os.path.lexists(git_directory / relative)
            for relative in (
                "info/grafts",
                "objects/info/alternates",
                "objects/info/http-alternates",
                "shallow",
            )
        ):
            raise AuthorizationError(
                "alternate, grafted, or shallow Git objects are prohibited"
            )
        allowed_config = {
            "core.repositoryformatversion",
            "core.filemode",
            "core.bare",
            "core.logallrefupdates",
            "core.ignorecase",
            "core.precomposeunicode",
            "remote.origin.url",
            "remote.origin.fetch",
        }
        config_keys = (
            self.run("config", "--local", "--name-only", "--list")
            .decode("utf-8")
            .splitlines()
        )
        if any(
            key not in allowed_config
            and re.fullmatch(r"branch\.[A-Za-z0-9/_-]+\.(?:remote|merge)", key) is None
            for key in config_keys
        ):
            raise AuthorizationError("unregistered local Git configuration")
        if self.text("rev-parse", "--is-shallow-repository") != "false":
            raise AuthorizationError("full Git history is required")
        if self.text("rev-parse", "--show-object-format") != "sha1":
            raise AuthorizationError("SHA-1 Git object format is required")
        if self.run("for-each-ref", "--format=%(refname)", "refs/replace"):
            raise AuthorizationError("replacement refs are prohibited")
        if self.run("status", "--porcelain=v1", "--untracked-files=all"):
            raise AuthorizationError("the canonical checkout must be clean")


def _module_path(module: str, inventory: set[str]) -> str:
    stem = "src/" + module.replace(".", "/")
    candidates = [
        item for item in (stem + ".py", stem + "/__init__.py") if item in inventory
    ]
    if len(candidates) != 1:
        raise AuthorizationError("unresolved or ambiguous local import")
    return candidates[0]


def _dotted(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return _dotted(node.value) + "." + node.attr
    return ""


_SENSITIVE_FUNCTION_AST = {
    (
        IMPLEMENTATION_PATHS[2],
        "_issue_authorization",
    ): "bfa314aab4df940edf9b8a8c02a19a399c68204f0ae69b1b7d6050e5db2de7e0",
    (
        IMPLEMENTATION_PATHS[2],
        "_verify_loaded_modules",
    ): "5e28b8ed294c2c6a8961eccc8ef7e76e51a3879db4f09af11d007055ff9ace5f",
    (
        IMPLEMENTATION_PATHS[2],
        "_issue_lease",
    ): "b0987c4f2c0a72b7c0c90686a4ae6dbb2d096e4b690354893f34b1fdcf386bbf",
    (
        IMPLEMENTATION_PATHS[3],
        "main",
    ): "ab7c9d472575200a7ce99dc0c4a871a1453e8a08cc1781c034bc2a1917fdb9e2",
}
_LEGACY_GETTER_SOURCE_SHA256 = (
    "baaeafcda224ce9626bf5b9071474c1e10342d34b42b20aa1445822de52b662a"
)
_FROZEN_DATA_SETTERS = {
    (
        "src/lotto649/domain.py",
        "fbcb22747ae361767df070c6e50af49fda1aa190b72fd39894afa1c879a50b7a",
    ): frozenset({"b670571ab2d883b7cd61dc8306083f26c1d603f53175166e23692cf02d689c40"}),
    ("src/lotto649/data_integrity.py", _LEGACY_GETTER_SOURCE_SHA256): frozenset(
        {
            "ca1e2bf0b9a95b4f3f13f8391138edd26e865397be43eb2ffea846e5c3a5c79e",
            "a38d6e63ca34fabfa8c5bb88829b237abf3a0c4780610ae629aa7b693db3695d",
        }
    ),
}
_PROCESS_CALL_AST = {
    "src/lotto649/history_registry.py": frozenset(
        {"01612ee07dfae5d11557f72ec46afd22192bc6e98f206db953953c93ef2ee517"}
    ),
    "src/lotto649/verified_history.py": frozenset(
        {
            "2ccd79064e38e9554815b4414e13e5e0dcb6c661c0b014d15ac0cdfac1f3fa4b",
            "954fb51d2cea4bcbd582460f9285afbf486272b4a2d63cc67c443e1cd12c79a8",
            "01612ee07dfae5d11557f72ec46afd22192bc6e98f206db953953c93ef2ee517",
        }
    ),
    IMPLEMENTATION_PATHS[2]: frozenset(
        {
            "f5f6801159316fb8716b4d1807221bf315d8a8443ce9ec398307862964f5d0bc",
            "91188ac951a6be0d442ad076e46bb9c96a3d3859ce29447504011be67544c1b7",
        }
    ),
    IMPLEMENTATION_PATHS[3]: frozenset(
        {"a467584555ea4b83948d5ba8334ae507b275e4f934fc0968024bea19bd00207b"}
    ),
}
_LEGACY_PROCESS_SOURCE_SHA256 = {
    "src/lotto649/history_registry.py": "5b0cde9f95da8181fb46f64ffeeaa148ddd625c9ae951e34470c8b3d6c8596d8",
    "src/lotto649/verified_history.py": "214e59071f3f8d232aca5f7850060a88568c35fb89246dea64f99c20265ead80",
}


def _check_source_safety(
    path: str, tree: ast.AST, *, blob_sha256: str | None = None
) -> None:
    """Static imports only; narrow reflection syntax is sealed, never inferred.

    Self/launcher exceptions bind entire function ASTs, and the containing Git
    blobs are in the reviewed closure at all four checkpoints. The inherited
    data getters additionally bind their registration-time source digest.
    """
    parents = {
        child: parent
        for parent in ast.walk(tree)
        for child in ast.iter_child_nodes(parent)
    }
    trusted_nodes: set[ast.AST] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            expected = _SENSITIVE_FUNCTION_AST.get((path, node.name))
            if (
                expected is not None
                and _sha(ast.dump(node, include_attributes=False).encode()) == expected
            ):
                trusted_nodes.update(ast.walk(node))
    dynamic_names = {
        "__import__",
        "eval",
        "exec",
        "compile",
        "globals",
        "locals",
        "vars",
        "getattr",
        "setattr",
        "delattr",
        "__builtins__",
    }
    forbidden_attributes = {
        "__dict__",
        "__getattribute__",
        "__getattr__",
        "__subclasses__",
        "__globals__",
        "__builtins__",
        "__code__",
        "__closure__",
        "__loader__",
        "import_module",
        "load_module",
        "exec_module",
        "module_from_spec",
        "spec_from_file_location",
        "load_library",
        "load",
        "system",
        "popen",
        "Popen",
        "check_call",
        "check_output",
        "execv",
        "execvp",
        "execvpe",
        "spawnl",
        "spawnlp",
        "spawnv",
        "spawnvp",
    }
    sys_aliases = {"sys"}
    process_aliases = {"subprocess"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "sys":
                    sys_aliases.add(alias.asname or alias.name)
                if alias.name == "subprocess":
                    process_aliases.add(alias.asname or alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module == "subprocess" or (
                node.module == "os"
                and any(
                    alias.name in forbidden_attributes | {"execve"}
                    for alias in node.names
                )
            ):
                raise AuthorizationError("process execution aliases are prohibited")
            if any(alias.name == "*" for alias in node.names):
                raise AuthorizationError("wildcard imports are prohibited")
            if node.module == "sys" and any(
                alias.name
                in {"modules", "path", "meta_path", "path_hooks", "path_importer_cache"}
                for alias in node.names
            ):
                raise AuthorizationError("import-state aliases are prohibited")
            if node.module == "importlib.metadata" and any(
                alias.name != "distributions" for alias in node.names
            ):
                raise AuthorizationError("unregistered metadata reflection import")
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in dynamic_names:
            call = parents.get(node)
            data_getter = (
                path == "src/lotto649/data_integrity.py"
                and blob_sha256 == _LEGACY_GETTER_SOURCE_SHA256
                and node.id == "getattr"
                and isinstance(call, ast.Call)
                and call.func is node
                and len(call.args) == 2
                and isinstance(call.args[0], ast.Name)
                and call.args[0].id in {"self", "reference"}
                and isinstance(call.args[1], ast.Name)
                and call.args[1].id == "field_name"
                and not call.keywords
            )
            if not data_getter:
                raise AuthorizationError(
                    "dynamic import or reflection capability is prohibited"
                )
        if (
            isinstance(node, ast.Name)
            and isinstance(node.ctx, ast.Load)
            and node.id in sys_aliases | process_aliases
        ):
            parent = parents.get(node)
            if not isinstance(parent, ast.Attribute) or parent.value is not node:
                raise AuthorizationError("import-state object aliases are prohibited")
        if isinstance(node, ast.Attribute):
            dotted = _dotted(node)
            if node.attr in forbidden_attributes:
                raise AuthorizationError(
                    "dynamic import or reflection attribute is prohibited"
                )
            if node.attr == "execve" and node not in trusted_nodes:
                raise AuthorizationError("unregistered process execution")
            if dotted.partition(".")[0] in process_aliases:
                enclosing = parents.get(node)
                if node.attr not in {"SubprocessError", "TimeoutExpired"} and (
                    node.attr != "run"
                    or not isinstance(enclosing, ast.Call)
                    or enclosing.func is not node
                    or _sha(ast.dump(enclosing, include_attributes=False).encode())
                    not in _PROCESS_CALL_AST.get(path, frozenset())
                    or (
                        path in _LEGACY_PROCESS_SOURCE_SHA256
                        and blob_sha256 != _LEGACY_PROCESS_SOURCE_SHA256[path]
                    )
                ):
                    # Exception classes are inert metadata, not execution ports.
                    raise AuthorizationError(
                        "unregistered subprocess execution or alias"
                    )
            import_state = node.attr in {
                "modules",
                "meta_path",
                "path_hooks",
                "path_importer_cache",
            } or (
                node.attr == "path"
                and (dotted.partition(".")[0] in sys_aliases or ".sys.path" in dotted)
            )
            if import_state and node not in trusted_nodes:
                raise AuthorizationError("unregistered import state access")
            if (
                node.attr in {"__new__", "__setattr__"}
                and node not in trusted_nodes
                and not (path == CORE_PATH and blob_sha256 == CORE_SHA256)
            ):
                enclosing = parents.get(node)
                if not isinstance(enclosing, ast.Call) or _sha(
                    ast.dump(enclosing, include_attributes=False).encode()
                ) not in _FROZEN_DATA_SETTERS.get((path, blob_sha256), frozenset()):
                    raise AuthorizationError("unregistered capability reflection")
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = (
                [alias.name for alias in node.names]
                if isinstance(node, ast.Import)
                else [node.module or ""]
            )
            for name in names:
                top = name.partition(".")[0]
                if top in {"builtins", "runpy", "ctypes", "marshal", "pickle"} or (
                    top == "importlib"
                    and not (
                        isinstance(node, ast.ImportFrom)
                        and name == "importlib.metadata"
                    )
                ):
                    raise AuthorizationError("unregistered code loading module")


def runtime_dependency_closure(repository: Path, commit: str) -> list[dict[str, str]]:
    git = GitRepository(repository)
    inventory = set(
        git.run("ls-tree", "-r", "--name-only", _oid(commit))
        .decode("utf-8")
        .splitlines()
    )
    pending = list(_CLOSURE_ROOTS)
    included: dict[str, dict[str, str]] = {}
    while pending:
        path = pending.pop()
        if path in included:
            continue
        raw = git.read_blob(commit, path)
        included[path] = {
            "path": path,
            "git_blob": git.oid(commit, path),
            "sha256": _sha(raw),
        }
        if not path.endswith(".py"):
            continue
        try:
            tree = ast.parse(raw, filename=path)
        except (SyntaxError, ValueError) as exc:
            raise AuthorizationError("invalid runtime source") from exc
        _check_source_safety(path, tree, blob_sha256=_sha(raw))
        module = path.removeprefix("src/").removesuffix(".py").replace("/", ".")
        package = (
            module.removesuffix(".__init__")
            if module.endswith(".__init__")
            else module.rpartition(".")[0]
        )
        if path.startswith("src/lotto649/"):
            parent = PurePosixPath(path).parent
            while str(parent).startswith("src/lotto649"):
                initializer = str(parent / "__init__.py")
                if initializer not in inventory:
                    raise AuthorizationError("local package initializer is absent")
                pending.append(initializer)
                parent = parent.parent
        for node in ast.walk(tree):
            imports: list[str] = []
            if isinstance(node, ast.Import):
                imports = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    pieces = package.split(".")
                    if node.level > len(pieces):
                        raise AuthorizationError(
                            "relative import escapes local package"
                        )
                    prefix = ".".join(pieces[: len(pieces) - node.level + 1])
                    base = prefix + ("." + node.module if node.module else "")
                else:
                    base = node.module or ""
                imports = [base]
                if base.startswith("lotto649"):
                    for alias in node.names:
                        child = base + "." + alias.name
                        stem = "src/" + child.replace(".", "/")
                        if (
                            stem + ".py" in inventory
                            or stem + "/__init__.py" in inventory
                        ):
                            imports.append(child)
            for imported in imports:
                top = imported.partition(".")[0]
                if top == "lotto649":
                    pending.append(_module_path(imported, inventory))
                elif (
                    top not in sys.stdlib_module_names
                    and top not in _EXTERNAL_MODULES
                    and top != "__future__"
                ):
                    raise AuthorizationError("unregistered external runtime import")
    return [included[path] for path in sorted(included)]


def runtime_identity() -> dict[str, Any]:
    if (
        sys.implementation.name != "cpython"
        or sys.version_info[:2] != (3, 12)
        or sys.float_info.radix != 2
        or sys.float_info.mant_dig != 53
        or sys.float_info.max_exp != 1024
    ):
        raise AuthorizationError("registered CPython 3.12 binary64 runtime is required")
    root = Path(__file__).resolve().parents[2]
    manifest = (root / REQUIREMENTS_PATH).read_bytes()
    if _sha(manifest) != REQUIREMENTS_SHA256:
        raise AuthorizationError("frozen dependency manifest differs")
    expected = {}
    for line in manifest.decode("ascii").splitlines():
        if line and not line.startswith("#"):
            name, version = line.split("==")
            expected[re.sub(r"[-_.]+", "-", name).lower()] = version
    installed: dict[str, str] = {}
    for distribution in distributions():
        name = re.sub(r"[-_.]+", "-", distribution.metadata["Name"]).lower()
        if name in installed:
            raise AuthorizationError("duplicate installed distribution")
        installed[name] = distribution.version
    if any(installed.get(name) != version for name, version in expected.items()):
        raise AuthorizationError("installed frozen dependency version differs")
    return {
        "implementation": sys.implementation.name,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "byteorder": sys.byteorder,
        "dependency_manifest_sha256": REQUIREMENTS_SHA256,
        "installed_distributions": dict(sorted(installed.items())),
    }


class FixedGitHubApi:
    """Fixed origin/repository transport. A lease-ref 404 is the sole absence."""

    def __init__(self, token: str) -> None:
        import requests

        if (
            type(token) is not str
            or not token
            or len(token) > 512
            or any(ord(c) < 33 or c.isspace() for c in token)
        ):
            raise AuthorizationError("GitHub credential unavailable")
        self._session = requests.Session()
        self._create_ref_attempted = False
        self._session.trust_env = False
        self._session.headers.update(
            {
                "Authorization": "Bearer " + token,
                "Accept": "application/vnd.github+json",
                "Accept-Encoding": "identity",
                "User-Agent": "lotto649-v12.0.1",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )

    def request_json(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        allow_absent: bool = False,
    ) -> dict[str, Any] | None:
        suffix = path.removeprefix(_API_PREFIX)
        get_allowed = (
            suffix
            in {
                "",
                "/branches/main/protection",
                "/git/ref/heads/main",
                "/git/ref/heads/v12-consumption-v12.0.1",
                "/hash-algorithm",
            }
            or re.fullmatch(
                r"/(?:pulls|issues/comments|check-runs)/[1-9][0-9]*", suffix
            )
            or re.fullmatch(r"/git/commits/[0-9a-f]{40}", suffix)
            or re.fullmatch(r"/commits/[0-9a-f]{40}/check-runs\?per_page=100", suffix)
        )
        post_allowed = suffix in {"/git/commits", "/git/refs"}
        if (
            not path.startswith(_API_PREFIX)
            or not (
                (method == "GET" and get_allowed and payload is None)
                or (method == "POST" and post_allowed and type(payload) is dict)
            )
            or (
                allow_absent
                and (
                    method != "GET"
                    or suffix != "/git/ref/heads/v12-consumption-v12.0.1"
                )
            )
        ):
            raise AuthorizationError("GitHub capability does not permit this request")
        if (
            method == "POST"
            and suffix == "/git/refs"
            and (set(payload or {}) != {"ref", "sha"} or payload["ref"] != LEASE_REF)
        ):
            raise AuthorizationError(
                "only the exact immutable lease ref may be created"
            )
        if method == "POST" and suffix == "/git/refs":
            _oid(payload["sha"])
            with _CAPABILITY_LOCK:
                if self._create_ref_attempted:
                    raise AttemptError("createRef was already attempted; no retry")
                self._create_ref_attempted = True
        url = _API_ORIGIN + path
        try:
            kwargs: dict[str, Any] = {
                "allow_redirects": False,
                "stream": True,
                "timeout": (10, 30),
            }
            if payload is not None:
                kwargs["json"] = payload
            with self._session.request(method, url, **kwargs) as response:
                if response.url != url:
                    raise AuthorizationError("GitHub response origin differs")
                expected_status = 201 if method == "POST" else 200
                absent = response.status_code == 404 and allow_absent
                if response.status_code != expected_status and not absent:
                    raise AuthorizationError("GitHub evidence request failed")
                if (
                    response.headers.get("Content-Encoding", "identity").lower()
                    != "identity"
                ):
                    raise AuthorizationError("encoded GitHub response refused")
                if (
                    response.headers.get("Content-Type", "").split(";", 1)[0].lower()
                    != "application/json"
                ):
                    raise AuthorizationError("GitHub evidence must be JSON")
                chunks: list[bytes] = []
                length = 0
                for chunk in response.iter_content(65536):
                    length += len(chunk)
                    if length > 2 * 1024 * 1024:
                        raise AuthorizationError("GitHub evidence exceeds bound")
                    chunks.append(chunk)
                result = _json(b"".join(chunks))
                if absent:
                    if (
                        result.get("message") != "Not Found"
                        or set(result) - {"message", "documentation_url", "status"}
                        or result.get("status", "404") != "404"
                    ):
                        raise AuthorizationError("ambiguous GitHub lease absence")
                    return None
                return result
        except AuthorizationError:
            raise
        except Exception:  # noqa: BLE001 -- transport errors may expose credentials.
            # Transport exceptions can embed authorization headers. Never chain.
            raise AuthorizationError("GitHub transport failed; no retry") from None


def _required_response(api: FixedGitHubApi, path: str) -> dict[str, Any]:
    response = api.request_json("GET", _API_PREFIX + path)
    if type(response) is not dict:
        raise AuthorizationError("missing GitHub attestation")
    return response


def _remote_main(api: FixedGitHubApi) -> str:
    response = _required_response(api, "/git/ref/heads/main")
    if (
        response.get("ref") != "refs/heads/main"
        or response.get("object", {}).get("type") != "commit"
    ):
        raise AuthorizationError("remote main identity is invalid")
    return _oid(response["object"]["sha"])


def _remote_protection(api: FixedGitHubApi) -> None:
    repository = _required_response(api, "")
    if (
        repository.get("node_id") != REPOSITORY_NODE_ID
        or repository.get("full_name") != REPOSITORY
        or repository.get("default_branch") != "main"
        or repository.get("private") is not False
    ):
        raise AuthorizationError("fixed public repository identity differs")
    if _required_response(api, "/hash-algorithm") != {"hash_algorithm": "sha1"}:
        raise AuthorizationError("remote Git object format differs")
    protection = _required_response(api, "/branches/main/protection")
    for key, expected in (
        ("enforce_admins", True),
        ("allow_force_pushes", False),
        ("allow_deletions", False),
    ):
        if (
            type(protection.get(key)) is not dict
            or protection[key].get("enabled") is not expected
        ):
            raise AuthorizationError("remote main protection is insufficient")


def _registered_authorities(
    git: GitRepository, head: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    if (
        not git.ancestor(R1, R2)
        or not git.ancestor(R2, head)
        or len(git.parents(R2)) != 1
    ):
        raise AuthorizationError("registration ancestry differs")
    added = git.text(
        "log", "--format=%H", "--diff-filter=A", head, "--", R2_PATH
    ).splitlines()
    if added != [R2]:
        raise AuthorizationError("registration adding authority is ambiguous")
    r2_raw = git.read_blob(R2, R2_PATH)
    if git.read_blob(head, R2_PATH) != r2_raw:
        raise AuthorizationError("R2 registration blob drift")
    r2 = _json(r2_raw)
    r1_raw = git.read_blob(R1, R1_PATH)
    if (
        _sha(r1_raw)
        != "4406bd25ee82195bff7a97b258885cb3bb3c1a8fb829f383c5e3c1616e169170"
    ):
        raise AuthorizationError("scientific registration differs")
    r1 = _json(r1_raw)
    for path, identity in r2["registered_files"].items():
        raw = git.read_blob(R2, path)
        if len(raw) != identity["bytes"] or _sha(raw) != identity["sha256"]:
            raise AuthorizationError("R2 authority seal differs")
    authority_paths = set(git.text("ls-tree", "-r", "--name-only", R2).splitlines())
    if authority_paths.intersection(
        r2["r2_git_authority"]["tree_assertions"]["absent_paths"]
    ):
        raise AuthorizationError("R2 contains implementation or execution authority")
    if (
        _sha(git.read_blob(R2, "config.yaml"))
        != r2["r2_git_authority"]["tree_assertions"]["config_yaml_sha256"]
    ):
        raise AuthorizationError("registration-time config differs")
    fingerprint = r2["statistical_equivalence"]["fingerprint_payload"]
    if (
        _sha(_canonical(fingerprint)) != FINGERPRINT
        or r2["statistical_equivalence"]["fingerprint_sha256"] != FINGERPRINT
    ):
        raise AuthorizationError("statistical fingerprint differs")
    for section, digest in fingerprint["contract_sections"].items():
        if _sha(_canonical(r1[section])) != digest:
            raise AuthorizationError("inherited statistical contract differs")
    if (
        r2["governed_history"]["authority_commit"] != HISTORY_AUTHORITY
        or git.text("cat-file", "-t", HISTORY_AUTHORITY) != "commit"
    ):
        raise AuthorizationError("fixed governed-history authority is absent")
    return r1, r2


def _core_and_closure(git: GitRepository, commit: str) -> list[dict[str, str]]:
    if _sha(git.read_blob(commit, CORE_PATH)) != CORE_SHA256:
        raise AuthorizationError("registered pure-core SHA-256 differs")
    if _sha(git.read_blob(commit, REQUIREMENTS_PATH)) != REQUIREMENTS_SHA256:
        raise AuthorizationError("frozen dependency manifest differs")
    return runtime_dependency_closure(git.root, commit)


def _require_normal_merge(
    git: GitRepository, merge: str, base: str, source: str
) -> None:
    if git.parents(merge) != (base, source) or git.tree(merge) != git.tree(source):
        raise AuthorizationError("ordinary merge parents or source tree differ")


def _verify_reviews(
    api: FixedGitHubApi,
    records: Sequence[Mapping[str, Any]],
    *,
    implementation: str,
    merge: str,
    base: str,
    closure_sha256: str,
) -> None:
    if len(records) != 2 or {r.get("axis") for r in records} != {"standards", "spec"}:
        raise AuthorizationError("two independent review axes are required")
    if (
        len({r.get("reviewer_agent_id") for r in records}) != 2
        or len({r.get("review_session_id") for r in records}) != 2
    ):
        raise AuthorizationError(
            "review agents and sessions must be independently identified"
        )
    pr_numbers = {r.get("pr_number") for r in records}
    check_ids = {r.get("check_id") for r in records}
    if len(pr_numbers) != 1 or len(check_ids) != 1:
        raise AuthorizationError("review evidence disagrees on PR or CI")
    pr_number, check_id = next(iter(pr_numbers)), next(iter(check_ids))
    if (
        type(pr_number) is not int
        or pr_number <= 0
        or type(check_id) is not int
        or check_id <= 0
    ):
        raise AuthorizationError("PR/check identifiers are invalid")
    pr = _required_response(api, f"/pulls/{pr_number}")
    if (
        pr.get("number") != pr_number
        or pr.get("state") != "closed"
        or pr.get("merged") is not True
        or pr.get("merge_commit_sha") != merge
        or pr.get("head", {}).get("sha") != implementation
        or pr.get("base", {}).get("sha") != base
        or pr.get("base", {}).get("ref") != "main"
        or pr.get("base", {}).get("repo", {}).get("full_name") != REPOSITORY
    ):
        raise AuthorizationError("implementation PR attestation differs")
    checks = _required_response(
        api, f"/commits/{implementation}/check-runs?per_page=100"
    )
    if (
        type(checks.get("total_count")) is not int
        or not 0 <= checks["total_count"] <= 100
        or type(checks.get("check_runs")) is not list
        or len(checks["check_runs"]) != checks["total_count"]
        or any(type(check) is not dict for check in checks["check_runs"])
    ):
        raise AuthorizationError("CI evidence is incomplete")
    candidates = [
        check for check in checks["check_runs"] if check.get("name") == "test"
    ]
    if len(candidates) != 1 or candidates[0].get("id") != check_id:
        raise AuthorizationError("exactly one unambiguous test check is required")
    check = _required_response(api, f"/check-runs/{check_id}")
    if (
        check.get("id") != check_id
        or check.get("head_sha") != implementation
        or check.get("name") != "test"
        or check.get("status") != "completed"
        or check.get("conclusion") != "success"
        or check.get("app", {}).get("slug") != "github-actions"
    ):
        raise AuthorizationError("implementation CI did not pass at reviewed head")
    for record in records:
        comment_id = record.get("comment_id")
        if type(comment_id) is not int or comment_id <= 0:
            raise AuthorizationError("review comment identity is invalid")
        comment = _required_response(api, f"/issues/comments/{comment_id}")
        body = comment.get("body")
        created_at = comment.get("created_at")
        if (
            type(created_at) is not str
            or re.fullmatch(
                r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z", created_at
            )
            is None
        ):
            raise AuthorizationError("review creation time is missing or invalid")
        try:
            datetime.fromisoformat(created_at)
        except ValueError:
            raise AuthorizationError("review creation time is invalid") from None
        if (
            comment.get("id") != comment_id
            or type(body) is not str
            or comment.get("user", {}).get("login") != record.get("publisher_login")
            or comment.get("issue_url")
            != _API_ORIGIN + _API_PREFIX + f"/issues/{pr_number}"
            or comment.get("updated_at") != comment.get("created_at")
            or _sha(body.encode("utf-8")) != record.get("comment_body_sha256")
        ):
            raise AuthorizationError("immutable review comment provenance differs")
        attestation = _json(body.encode("utf-8"))
        expected = {
            "schema_version": "lotto649-v12-i2-independent-review-v1",
            "axis": record["axis"],
            "base_sha": base,
            "head_sha": implementation,
            "closure_sha256": closure_sha256,
            "verdict": "pass",
            "blocker_count": 0,
            "major_count": 0,
            "reviewer_kind": "independent_agent",
            "reviewer_agent_id": record["reviewer_agent_id"],
            "review_session_id": record["review_session_id"],
            "publisher_login": record["publisher_login"],
        }
        if attestation != expected or not all(
            type(expected[key]) is str and expected[key]
            for key in ("reviewer_agent_id", "review_session_id", "publisher_login")
        ):
            raise AuthorizationError(
                "review body does not bind the complete reviewed source"
            )


def build_authorization_payload(
    repository: Path,
    *,
    implementation_commit: str,
    implementation_merge: str,
    authorization_base: str,
    review_records: Sequence[Mapping[str, Any]],
    api: FixedGitHubApi,
) -> dict[str, Any]:
    """Read-only preparation. This payload has no authority on a source branch."""
    git = GitRepository(repository)
    implementation, merge, base = map(
        _oid, (implementation_commit, implementation_merge, authorization_base)
    )
    r1, r2 = _registered_authorities(git, base)
    parents = git.parents(merge)
    if len(parents) != 2 or parents[1] != implementation:
        raise AuthorizationError("implementation merge is not ordinary")
    implementation_base = parents[0]
    _require_normal_merge(git, merge, implementation_base, implementation)
    if (
        not git.ancestor(R2, implementation_base)
        or not git.ancestor(merge, base)
        or implementation == base
        or not git.ancestor(implementation, base)
    ):
        raise AuthorizationError("R2/I2/K_H2 order differs")
    if set(git.changes(implementation_base, implementation)) != {
        ("A", path) for path in IMPLEMENTATION_PATHS
    }:
        raise AuthorizationError("I2 must add exactly the six registered paths")
    closure = _core_and_closure(git, implementation)
    if _core_and_closure(git, base) != closure:
        raise AuthorizationError("historical closure drift after I2")
    _remote_protection(api)
    if _remote_main(api) != base:
        raise AuthorizationError("K_H2 is not current protected remote main")
    _verify_reviews(
        api,
        review_records,
        implementation=implementation,
        merge=merge,
        base=implementation_base,
        closure_sha256=_sha(_canonical(closure)),
    )
    return {
        "schema_version": "lotto649-v12.0.1-historical-authorization-v1",
        "experiment_id": r2["experiment_id"],
        "model_version": "v12.0.1",
        "repository": REPOSITORY,
        "branch": "main",
        "registration_commit": R2,
        "registration_sha256": _sha(git.read_blob(R2, R2_PATH)),
        "scientific_registration_commit": R1,
        "statistical_fingerprint_sha256": FINGERPRINT,
        "pure_core_sha256": CORE_SHA256,
        "implementation_commit": implementation,
        "implementation_base": implementation_base,
        "implementation_merge": merge,
        "authorization_base": base,
        "canonical_command": COMMAND,
        "governed_history_authority": HISTORY_AUTHORITY,
        "governed_history_identity": r1["authority"],
        "runtime": runtime_identity(),
        "runtime_dependency_closure": closure,
        "runtime_dependency_closure_sha256": _sha(_canonical(closure)),
        "review_records": [dict(record) for record in review_records],
    }


@dataclass(frozen=True, init=False)
class VerifiedAuthorization:
    repository: Path
    execution_commit: str
    source_commit: str
    payload: dict[str, Any]
    authorization_sha256: str

    def __new__(cls, *args: Any, **kwargs: Any) -> Any:
        raise AuthorizationError("authorization is issued only by the verifier")


def _issue_authorization(
    repository: Path, execution: str, source: str, payload: dict[str, Any], digest: str
) -> VerifiedAuthorization:
    authority = object.__new__(VerifiedAuthorization)
    for name, value in (
        ("repository", repository),
        ("execution_commit", execution),
        ("source_commit", source),
        ("payload", payload),
        ("authorization_sha256", digest),
    ):
        object.__setattr__(authority, name, value)
    with _CAPABILITY_LOCK:
        _ISSUED_AUTHORITIES.append((authority, _authorization_stamp(authority)))
    return authority


def _authorization_stamp(authority: VerifiedAuthorization) -> bytes:
    return _canonical(
        {
            "repository": str(authority.repository),
            "execution_commit": authority.execution_commit,
            "source_commit": authority.source_commit,
            "payload": authority.payload,
            "authorization_sha256": authority.authorization_sha256,
        }
    )


def _require_authorization_capability(
    authority: VerifiedAuthorization, *, consume: bool = False
) -> None:
    with _CAPABILITY_LOCK:
        matches = [raw for issued, raw in _ISSUED_AUTHORITIES if issued is authority]
        if len(matches) != 1 or _authorization_stamp(authority) != matches[0]:
            raise AuthorizationError("unissued or altered authorization capability")
        if consume:
            if any(used is authority for used in _USED_AUTHORITIES):
                raise AttemptError(
                    "authorization lease acquisition was already attempted"
                )
            _USED_AUTHORITIES.append(authority)


def verify_authorization(
    repository: Path, *, api: FixedGitHubApi
) -> VerifiedAuthorization:
    git = GitRepository(repository)
    git.require_full_clean()
    head = git.head()
    r1, r2 = _registered_authorities(git, head)
    raw = git.read_blob(head, AUTHORIZATION_PATH)
    authorization = _json(raw)
    if raw not in {_canonical(authorization), _canonical(authorization) + b"\n"}:
        raise AuthorizationError("authorization JSON is not canonical")
    expected_keys = {
        "schema_version",
        "experiment_id",
        "model_version",
        "repository",
        "branch",
        "registration_commit",
        "registration_sha256",
        "scientific_registration_commit",
        "statistical_fingerprint_sha256",
        "pure_core_sha256",
        "implementation_commit",
        "implementation_base",
        "implementation_merge",
        "authorization_base",
        "canonical_command",
        "governed_history_authority",
        "governed_history_identity",
        "runtime",
        "runtime_dependency_closure",
        "runtime_dependency_closure_sha256",
        "review_records",
    }
    if set(authorization) != expected_keys:
        raise AuthorizationError("authorization schema differs")
    required = {
        "schema_version": "lotto649-v12.0.1-historical-authorization-v1",
        "experiment_id": r2["experiment_id"],
        "model_version": "v12.0.1",
        "repository": REPOSITORY,
        "branch": "main",
        "registration_commit": R2,
        "scientific_registration_commit": R1,
        "registration_sha256": _sha(git.read_blob(R2, R2_PATH)),
        "statistical_fingerprint_sha256": FINGERPRINT,
        "pure_core_sha256": CORE_SHA256,
        "canonical_command": COMMAND,
        "governed_history_authority": HISTORY_AUTHORITY,
        "governed_history_identity": r1["authority"],
        "runtime": runtime_identity(),
    }
    if any(authorization[key] != value for key, value in required.items()):
        raise AuthorizationError("authorization fixed identity differs")
    implementation = _oid(authorization["implementation_commit"])
    implementation_base = _oid(authorization["implementation_base"])
    implementation_merge = _oid(authorization["implementation_merge"])
    base = _oid(authorization["authorization_base"])
    parents = git.parents(head)
    if len(parents) != 2 or parents[0] != base:
        raise AuthorizationError(
            "only an ordinary protected-main authorization merge executes"
        )
    source = parents[1]
    _require_normal_merge(git, head, base, source)
    if (
        git.parents(source) != (base,)
        or git.changes(base, source) != [("A", AUTHORIZATION_PATH)]
        or git.read_blob(source, AUTHORIZATION_PATH) != raw
    ):
        raise AuthorizationError(
            "authorization source must be an auth-only child of K_H2"
        )
    _require_normal_merge(
        git, implementation_merge, implementation_base, implementation
    )
    if (
        set(git.changes(implementation_base, implementation))
        != {("A", path) for path in IMPLEMENTATION_PATHS}
        or not git.ancestor(R2, implementation_base)
        or not git.ancestor(implementation_merge, base)
        or implementation == base
    ):
        raise AuthorizationError("complete registered I2 ancestry is required")
    closure = authorization["runtime_dependency_closure"]
    if _sha(_canonical(closure)) != authorization["runtime_dependency_closure_sha256"]:
        raise AuthorizationError("authorization runtime closure hash differs")
    for checkpoint in (implementation, base, source, head):
        if _core_and_closure(git, checkpoint) != closure:
            raise AuthorizationError(
                "runtime/core identity differs at historical checkpoint"
            )
    _remote_protection(api)
    if _remote_main(api) != head:
        raise AuthorizationError(
            "local HEAD is not exact protected remote authorization main"
        )
    _verify_reviews(
        api,
        authorization["review_records"],
        implementation=implementation,
        merge=implementation_merge,
        base=implementation_base,
        closure_sha256=authorization["runtime_dependency_closure_sha256"],
    )
    _verify_worktree_runtime(git, head, closure)
    return _issue_authorization(repository, head, source, authorization, _sha(raw))


def _verify_worktree_runtime(
    git: GitRepository, head: str, closure: Sequence[Mapping[str, str]]
) -> None:
    for entry in closure:
        path = git.root / entry["path"]
        if (
            path.is_symlink()
            or not path.is_file()
            or _sha(path.read_bytes()) != entry["sha256"]
            or git.oid(head, entry["path"]) != entry["git_blob"]
        ):
            raise AuthorizationError("working runtime differs from reviewed closure")
    _verify_loaded_modules(git.root, closure)


def _verify_loaded_modules(root: Path, closure: Sequence[Mapping[str, str]]) -> None:
    expected = {entry["path"]: entry["sha256"] for entry in closure}
    for name, module in tuple(sys.modules.items()):
        if name == "lotto649" or name.startswith("lotto649."):
            if module is None:
                raise AuthorizationError("local module is incomplete")
            try:
                origin = Path(module.__file__).resolve(strict=True)
                relative = origin.relative_to(root.resolve()).as_posix()
            except (AttributeError, TypeError, ValueError, OSError):
                raise AuthorizationError(
                    "local module origin is outside reviewed runtime"
                ) from None
            if expected.get(relative) != _sha(origin.read_bytes()):
                raise AuthorizationError(
                    "unregistered or replaced local runtime module"
                )


@dataclass(frozen=True, init=False)
class Lease:
    ref: str
    commit: str
    nonce_hex: str

    def __new__(cls, *args: Any, **kwargs: Any) -> Any:
        raise AttemptError("lease is issued only after exact remote acquisition")


def _issue_lease(authority: VerifiedAuthorization, commit: str, nonce: str) -> Lease:
    lease = object.__new__(Lease)
    for name, value in (("ref", LEASE_REF), ("commit", commit), ("nonce_hex", nonce)):
        object.__setattr__(lease, name, value)
    with _CAPABILITY_LOCK:
        _ISSUED_LEASES.append((lease, authority, (LEASE_REF, commit, nonce)))
    return lease


def _consume_lease(authority: VerifiedAuthorization, lease: Lease) -> None:
    _require_authorization_capability(authority)
    with _CAPABILITY_LOCK:
        if not any(
            issued is lease
            and owner is authority
            and snapshot == (lease.ref, lease.commit, lease.nonce_hex)
            for issued, owner, snapshot in _ISSUED_LEASES
        ) or any(used is lease for used in _USED_LEASES):
            raise AttemptError("unissued, foreign, or already-used lease capability")
        _USED_LEASES.append(lease)


def _lease_commit(
    git: GitRepository, authority: VerifiedAuthorization, nonce: str
) -> tuple[str, bytes, dict[str, Any]]:
    if _SHA256.fullmatch(nonce) is None:
        raise AuthorizationError("lease nonce is invalid")
    commit_raw = git.run("cat-file", "commit", authority.execution_commit)
    headers, _message = commit_raw.split(b"\n\n", 1)
    committer = [
        line for line in headers.splitlines() if line.startswith(b"committer ")
    ]
    if len(committer) != 1:
        raise AuthorizationError("authorization committer is ambiguous")
    match = re.search(rb" ([0-9]+) [+-][0-9]{4}$", committer[0])
    if match is None:
        raise AuthorizationError("authorization timestamp is invalid")
    instant = int(match[1])
    timestamp = datetime.fromtimestamp(instant, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    body = (
        _canonical(
            {
                "schema_version": "lotto649-v12-consumption-lease-v1",
                "authorization_seal_sha256": authority.authorization_sha256,
                "canonical_command": COMMAND,
                "execution_authority_M_A": authority.execution_commit,
                "nonce_hex": nonce,
            }
        )
        + b"\n"
    )
    tree = git.tree(authority.execution_commit)
    identity = (
        "LOTTO649 V12 Consumption Lease <lotto649-v12-lease@users.noreply.github.com>"
    )
    raw = (
        f"tree {tree}\nparent {authority.execution_commit}\nauthor {identity} {instant} +0000\ncommitter {identity} {instant} +0000\n\n".encode(
            "ascii"
        )
        + body
    )
    oid = hashlib.sha1(
        b"commit " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()
    signature = {
        "name": "LOTTO649 V12 Consumption Lease",
        "email": "lotto649-v12-lease@users.noreply.github.com",
        "date": timestamp,
    }
    payload = {
        "tree": tree,
        "parents": [authority.execution_commit],
        "author": signature,
        "committer": signature,
        "message": body.decode("utf-8"),
    }
    return oid, raw, payload


def _verify_lease_object(
    observed: Mapping[str, Any],
    expected_oid: str,
    raw: bytes,
    payload: Mapping[str, Any],
) -> None:
    if (
        observed.get("sha") != expected_oid
        or observed.get("tree", {}).get("sha") != payload["tree"]
        or [parent.get("sha") for parent in observed.get("parents", [])]
        != payload["parents"]
        or observed.get("author") != payload["author"]
        or observed.get("committer") != payload["committer"]
        or observed.get("message") != payload["message"]
    ):
        raise AuthorizationError("remote lease commit differs from canonical object")
    verification = observed.get("verification")
    if (
        type(verification) is not dict
        or verification.get("verified") is not False
        or verification.get("signature") is not None
        or verification.get("payload") is not None
        or verification.get("reason") != "unsigned"
    ):
        raise AuthorizationError("lease contains an unregistered signature")
    # The locally recomputed OID binds raw headers/order and every message byte.
    if (
        hashlib.sha1(b"commit " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        != expected_oid
    ):
        raise AuthorizationError("canonical lease object digest differs")


def acquire_historical_lease(
    authority: VerifiedAuthorization, api: FixedGitHubApi
) -> Lease:
    """At most one createRef call. Errors propagate and never grant a retry."""
    _require_authorization_capability(authority, consume=True)
    git = GitRepository(authority.repository)
    _remote_protection(api)
    if (
        _remote_main(api) != authority.execution_commit
        or git.head() != authority.execution_commit
    ):
        raise AuthorizationError("authority moved before lease")
    if (
        api.request_json(
            "GET",
            _API_PREFIX + "/git/ref/heads/v12-consumption-v12.0.1",
            allow_absent=True,
        )
        is not None
    ):
        raise AttemptError("the repository-global attempt lease already exists")
    nonce = secrets.token_hex(32)
    oid, raw, payload = _lease_commit(git, authority, nonce)
    created = api.request_json("POST", _API_PREFIX + "/git/commits", payload=payload)
    if type(created) is not dict or created.get("sha") != oid:
        raise AttemptError("lease upload is uncertain; no retry")
    observed = _required_response(api, "/git/commits/" + oid)
    _verify_lease_object(observed, oid, raw, payload)
    result = api.request_json(
        "POST", _API_PREFIX + "/git/refs", payload={"ref": LEASE_REF, "sha": oid}
    )
    if (
        type(result) is not dict
        or result.get("ref") != LEASE_REF
        or result.get("object", {}).get("sha") != oid
        or result.get("object", {}).get("type") != "commit"
    ):
        raise AttemptError("lease creation is uncertain; no retry")
    reread = _required_response(api, "/git/ref/heads/v12-consumption-v12.0.1")
    if (
        reread.get("ref") != LEASE_REF
        or reread.get("object", {}).get("sha") != oid
        or reread.get("object", {}).get("type") != "commit"
    ):
        raise AttemptError("lease reread differs; no retry")
    if _remote_main(api) != authority.execution_commit:
        raise AttemptError("main moved after lease; no retry")
    return _issue_lease(authority, oid, nonce)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _fsync_directory(directory: Path) -> None:
    descriptor = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _exclusive_bytes(path: Path, raw: bytes) -> None:
    if any(parent.is_symlink() for parent in (path, *path.parents)):
        raise AttemptError("audit output symlink is prohibited")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    _fsync_directory(path.parent)


def _publish_exclusive(staging: Path, destination: Path, raw: bytes) -> None:
    """An exclusive hard-link publishes staged bytes without replacing a name."""
    if staging.parent != destination.parent:
        raise AttemptError("report staging must share its output directory")
    _exclusive_bytes(staging, raw)
    os.link(staging, destination, follow_symlinks=False)
    _fsync_directory(destination.parent)
    staging.unlink()
    _fsync_directory(destination.parent)


class DurableLedger:
    """One open exclusive descriptor, contiguous hash chain, fsync per event."""

    def __init__(self, path: Path, bindings: Mapping[str, Any]) -> None:
        self.path = path
        self._bindings = json.loads(_canonical(dict(bindings)))
        self._sequence = 0
        self._head = "0" * 64
        self._closed = False
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        self._stream = os.fdopen(descriptor, "wb")
        _fsync_directory(path.parent)

    @property
    def head(self) -> str:
        return self._head

    def append(self, kind: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        if self._closed:
            raise AttemptError("closed ledger cannot append or retry")
        event = {
            "schema_version": "lotto649-v12.0.1-attempt-ledger-v1",
            "sequence": self._sequence,
            "previous_event_sha256": self._head,
            "event_kind": kind,
            "recorded_at": _utc_now(),
            "bindings": self._bindings,
            "payload": dict(payload),
        }
        digest = _sha(_canonical(event))
        event["event_sha256"] = digest
        try:
            self._stream.write(_canonical(event) + b"\n")
            self._stream.flush()
            os.fsync(self._stream.fileno())
        except BaseException:  # Poison even interrupted writes before re-raising.
            self._closed = True
            self._stream.close()
            raise
        self._head = digest
        self._sequence += 1
        return event

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            self._stream.close()


def audit_ledger(path: Path) -> dict[str, Any]:
    """Read a local synthetic or already-consumed chain without recalculation."""
    raw = path.read_bytes()
    if not raw or not raw.endswith(b"\n"):
        raise AttemptError("incomplete durable ledger")
    previous = "0" * 64
    pending: tuple[str, str] | None = None
    count = 0
    stopped = False
    bindings: object = None
    targets: set[str] = set()
    previous_target: date | None = None
    for number, line in enumerate(raw.splitlines()):
        event = _json(line)
        if _canonical(event) != line:
            raise AttemptError("noncanonical ledger event")
        recorded_digest = event.pop("event_sha256", None)
        if (
            event.get("sequence") != number
            or event.get("previous_event_sha256") != previous
            or _sha(_canonical(event)) != recorded_digest
        ):
            raise AttemptError("ledger hash chain differs")
        previous = recorded_digest
        if number == 0:
            bindings = event.get("bindings")
        elif event.get("bindings") != bindings:
            raise AttemptError("ledger identity changed")
        kind, payload = event.get("event_kind"), event.get("payload", {})
        if kind == "prediction_frozen":
            if pending is not None or stopped:
                raise AttemptError("forecast ordering violated")
            frozen = payload.get("forecast_payload")
            if type(frozen) is not dict:
                raise AttemptError("forecast payload missing")
            digest = _sha(_canonical(frozen) + b"\n")
            target = frozen.get("target_draw_date")
            if target in targets or payload.get("forecast_payload_sha256") != digest:
                raise AttemptError("duplicate forecast or incorrect payload digest")
            target_date = date.fromisoformat(target)
            if previous_target is not None and target_date <= previous_target:
                raise AttemptError("ledger targets are not strictly chronological")
            previous_target = target_date
            if date.fromisoformat(frozen["history_through"]) >= date.fromisoformat(
                target
            ):
                raise AttemptError("forecast chronology violated")
            targets.add(target)
            pending = (target, digest)
        elif kind == "target_revealed_scored":
            if pending != (
                payload.get("target_draw_date"),
                payload.get("forecast_payload_sha256"),
            ):
                raise AttemptError("reveal lacks preceding exact frozen forecast")
            pending = None
            count += 1
        elif kind == "historical_6of6_candidate_detected":
            if pending is not None:
                raise AttemptError("6/6 detection precedes durable scoring")
            stopped = True
    return {
        "event_count": len(raw.splitlines()),
        "scored_target_count": count,
        "head_sha256": previous,
        "pending_forecast": pending is not None,
        "stopped_for_audit": stopped,
        "file_sha256": _sha(raw),
    }


def _prefix_identity(prefix: Sequence[Any], target: date) -> tuple[list[Any], str, str]:
    from .domain import Draw

    rows = list(prefix)
    if not rows or any(type(row) is not Draw for row in rows):
        raise AttemptError("a nonempty strict Draw prefix is required")
    dates = [row.draw_date for row in rows]
    if any(left >= right for left, right in pairwise(dates)) or dates[-1] >= target:
        raise AttemptError("prefix includes a duplicate, target, or future draw")
    canonical = [
        {
            "draw_date": row.draw_date.isoformat(),
            "numbers": list(row.numbers),
            "bonus": row.bonus,
        }
        for row in rows
    ]
    return rows, _sha(_canonical(canonical) + b"\n"), dates[-1].isoformat()


def _drive_sequence(
    targets: Sequence[date],
    prefix_for: Callable[[date], Sequence[Any]],
    reveal: Callable[[date], Any],
    forecast: Callable[[Sequence[Any], date], Sequence[Mapping[str, Any]]],
    *,
    bindings: Mapping[str, Any],
    ledger: DurableLedger,
    notify: Callable[[str, str], bool] | None,
    synthetic: bool,
) -> tuple[list[dict[str, Any]], list[str], str | None]:
    from .domain import Draw
    from .v12_0_1_evidence import (
        canonical_json_bytes,
        opportunity_summary,
        score_target,
        validate_frozen_payload,
    )

    dates = list(targets)
    if any(type(target) is not date for target in dates) or any(
        left >= right for left, right in pairwise(dates)
    ):
        raise AttemptError("target dates must be unique and strictly increasing")
    rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    opportunities: list[int] = []
    for target in dates:
        prefix, prefix_digest, history_through = _prefix_identity(
            prefix_for(target), target
        )
        predictions = forecast(tuple(prefix), target)
        payload = {
            "schema_version": "lotto649-v12.0.1-frozen-forecast-v1",
            "classification": "synthetic_fixture_only"
            if synthetic
            else "consumed_historical_diagnostic_only",
            "model_version": "v12.0.1",
            "target_draw_date": target.isoformat(),
            "history_through": history_through,
            "training_cutoff_date": history_through,
            "visible_prefix_sha256": prefix_digest,
            "visible_prefix_draw_count": len(prefix),
            "bindings": dict(bindings),
            "forecasts": [dict(item) for item in predictions],
        }
        frozen_raw = canonical_json_bytes(payload)
        validate_frozen_payload(frozen_raw)
        digest = _sha(frozen_raw)
        frozen_event = ledger.append(
            "prediction_frozen",
            {"forecast_payload": payload, "forecast_payload_sha256": digest},
        )
        # A reveal adapter receives only the date, after the successful fsync.
        actual = reveal(target)
        if type(actual) is not Draw or actual.draw_date != target:
            raise AttemptError("reveal returned an incorrect target")
        row = score_target(frozen_raw, actual)
        row["forecast_payload_sha256"] = digest
        row["prediction_generated_at"] = frozen_event["recorded_at"]
        row["prediction_frozen_event_sequence"] = frozen_event["sequence"]
        row["prediction_frozen_event_sha256"] = frozen_event["event_sha256"]
        opportunities.append(row["unique_opportunity_count"])
        row["cumulative_opportunities"] = opportunity_summary(opportunities)
        scored_event = ledger.append("target_revealed_scored", row)
        row["scored_event_sequence"] = scored_event["sequence"]
        row["scored_event_sha256"] = scored_event["event_sha256"]
        rows.append(row)
        exact = row["exact_final6_opportunities"]
        top12 = row["top12_all_six_producers"]
        if exact:
            ledger.append(
                "historical_6of6_candidate_detected",
                {
                    "target_draw_date": target.isoformat(),
                    "forecast_payload_sha256": digest,
                    "opportunities": exact,
                    "audit_status": "independent_leakage_audit_pending",
                    "eligible_evidence": False,
                    "global_stop_search": False,
                },
            )
        elif top12:
            ledger.append(
                "historical_top12_all_six_detected",
                {
                    "target_draw_date": target.isoformat(),
                    "forecast_payload_sha256": digest,
                    "producers": top12,
                    "eligible_evidence": False,
                },
            )
        if exact or top12:
            category = "Final-6 6/6" if exact else "Top-12 覆盖 6 个主号码"
            subject = "历史诊断/审计候选、不可晋升 — " + category
            body = f"分类：历史诊断/审计候选、不可晋升\n模型版本：v12.0.1\n历史目标日期：{target.isoformat()}\n训练截止：{history_through}\n事件：{category}\n预测摘要：{digest}\n仅为 consumed historical diagnostic，不是下一期预测或购票建议。\n"
            if exact:
                body += "本次历史运行已停止，等待独立 chronology/leakage audit。\n"
            ledger.append(
                "notification_attempt_started",
                {
                    "target_draw_date": target.isoformat(),
                    "kind": "final6" if exact else "top12",
                    "classification_zh": "历史诊断/审计候选、不可晋升",
                },
            )
            try:
                sent = bool(notify(subject, body)) if notify is not None else False
            except Exception:  # noqa: BLE001 -- notification failure never recomputes.
                sent = False
            ledger.append(
                "notification_attempt_finished",
                {"target_draw_date": target.isoformat(), "email_sent": sent},
            )
            if not sent:
                warnings.append("notification_not_sent:" + target.isoformat())
            if exact:
                return rows, warnings, "exact_final6_pending_independent_audit"
    return rows, warnings, None


def _paths(directory: Path, *, synthetic: bool) -> dict[str, Path]:
    if synthetic:
        return {
            key: directory / ("synthetic_" + name)
            for key, name in _ARTIFACT_NAMES.items()
        }
    return {key: directory / name for key, name in _ARTIFACT_NAMES.items()}


def _require_fresh_outputs(paths: Mapping[str, Path]) -> None:
    if any(os.path.lexists(path) for path in paths.values()):
        raise AttemptError("a permanent claim or output already exists; no retry")
    directory = paths["claim"].parent
    if any(parent.is_symlink() for parent in (directory, *directory.parents)):
        raise AttemptError("audit output parent cannot be a symlink")


def _report_files(
    paths: Mapping[str, Path],
    rows: Sequence[dict[str, Any]],
    bindings: Mapping[str, Any],
    *,
    ledger: DurableLedger,
    warnings: Sequence[str],
    stop_reason: str | None,
    synthetic: bool,
) -> dict[str, Any]:
    from .v12_0_1_evidence import build_report, canonical_json_bytes, render_markdown

    audit = audit_ledger(paths["ledger"])
    complete = (
        stop_reason is None
        and not warnings
        and audit["scored_target_count"] == len(rows)
        and not audit["pending_forecast"]
    )
    report_bindings = {
        **dict(bindings),
        "claim_sha256": _sha(paths["claim"].read_bytes()),
        "ledger": audit,
    }
    report = build_report(
        rows,
        report_bindings,
        audit_complete=complete,
        audit_warnings=tuple(warnings),
        stop_reason=stop_reason,
    )
    if synthetic:
        report["classification"] = "synthetic_fixture_only"
        report["synthetic_fixture_only"] = True
        report["eligible_evidence"] = False
    report["independent_leakage_audit"] = (
        "pending"
        if stop_reason == "exact_final6_pending_independent_audit"
        else "not_required_no_exact_final6"
    )
    report["audit_publication"] = "pending_git_integration"
    json_raw = canonical_json_bytes(report)
    markdown_raw = render_markdown(report).encode("utf-8")
    if synthetic:
        markdown_raw = b"# SYNTHETIC FIXTURE ONLY\n\n" + markdown_raw
    _publish_exclusive(paths["json_staging"], paths["json"], json_raw)
    _publish_exclusive(paths["markdown_staging"], paths["markdown"], markdown_raw)
    ledger.close()
    return report


def _durable_scored_rows(path: Path) -> list[dict[str, Any]]:
    """Recover only already-frozen scored bytes, never recompute a forecast."""
    audit_ledger(path)
    rows = []
    for raw in path.read_bytes().splitlines():
        event = _json(raw)
        if event["event_kind"] == "target_revealed_scored":
            row = event["payload"]
            row["scored_event_sequence"] = event["sequence"]
            row["scored_event_sha256"] = event["event_sha256"]
            rows.append(row)
    return rows


def _synthetic_root(output_root: Path, bindings: Mapping[str, Any]) -> Path:
    root = output_root.absolute()
    if root.name in {"reports", "predictions", "evaluations", "evidence"} or any(
        (parent / ".git").exists() for parent in (root, *root.parents)
    ):
        raise AttemptError("synthetic artifacts cannot be created in a repository")
    encoded = _canonical(dict(bindings))
    if any(
        identity.encode() in encoded
        for identity in (
            R2,
            R1,
            HISTORY_AUTHORITY,
            LEASE_REF,
            REPOSITORY,
            AUTHORIZATION_PATH,
        )
    ):
        raise AttemptError("synthetic bindings cannot impersonate registered authority")
    if root.exists() and (root.is_symlink() or any(root.iterdir())):
        raise AttemptError("synthetic output directory must be new or empty")
    root.mkdir(parents=True, exist_ok=True)
    _exclusive_bytes(root / ".synthetic-v12-0-1", b"synthetic_fixture_only\n")
    return root


def run_synthetic_attempt(
    output_root: Path,
    targets: Sequence[date],
    prefix_for: Callable[[date], Sequence[Any]],
    reveal: Callable[[date], Any],
    forecast: Callable[[Sequence[Any], date], Sequence[Mapping[str, Any]]],
    *,
    bindings: Mapping[str, Any],
    notify: Callable[[str, str], bool] | None = None,
) -> dict[str, Any]:
    """Synthetic-only ordering seam; cannot acquire authority or write Git."""
    directory = _synthetic_root(output_root, bindings)
    paths = _paths(directory, synthetic=True)
    identity = {
        "classification": "synthetic_fixture_only",
        "synthetic_bindings": dict(bindings),
    }
    _require_fresh_outputs(paths)
    _exclusive_bytes(paths["claim"], _canonical(identity) + b"\n")
    ledger = DurableLedger(paths["ledger"], identity)
    ledger.append(
        "synthetic_attempt_claimed", {"claim_sha256": _sha(paths["claim"].read_bytes())}
    )
    try:
        rows, warnings, stop_reason = _drive_sequence(
            targets,
            prefix_for,
            reveal,
            forecast,
            bindings=identity,
            ledger=ledger,
            notify=notify,
            synthetic=True,
        )
        report = _report_files(
            paths,
            rows,
            identity,
            ledger=ledger,
            warnings=warnings,
            stop_reason=stop_reason,
            synthetic=True,
        )
        manifest = {
            "schema_version": "lotto649-v12-synthetic-artifacts-v1",
            "classification": "synthetic_fixture_only",
            "files": {
                paths[key].name: _sha(paths[key].read_bytes())
                for key in ("claim", "ledger", "json", "markdown")
            },
            "git_commit": None,
        }
        _publish_exclusive(
            paths["commit_staging"], paths["commit"], _canonical(manifest) + b"\n"
        )
        return report
    except Exception:
        ledger.close()
        raise


def _require_default_notification_environment() -> None:
    if any(name in os.environ for name in _ROUTE_OVERRIDES):
        raise AuthorizationError("SMTP routing overrides are prohibited")


def _default_notification(subject: str, body: str) -> bool:
    from .notification import send_email

    _require_default_notification_environment()
    return send_email(subject, body)


def _load_governed_history(
    authority: VerifiedAuthorization,
) -> tuple[Any, dict[str, Any]]:
    """Only the canonical post-lease/post-claim path calls this reader."""
    if not any(active is authority for active in _ACTIVE_ATTEMPTS):
        raise AttemptError("governed history requires an active claimed capability")
    import yaml

    from .operational_history import (
        load_published_history,
        operational_history_provenance,
    )

    history = load_published_history(authority.repository, HISTORY_AUTHORITY)
    provenance = operational_history_provenance(history)
    registered = authority.payload["governed_history_identity"]
    expected = registered["immutable_objects"]
    if (
        len(history.draws) != 4444
        or history.draws[0].draw_date != date(1982, 6, 12)
        or history.draws[-1].draw_date != date(2026, 8, 22)
    ):
        raise AttemptError("fixed governed-history dates or draw count differ")
    if any(a.draw_date >= b.draw_date for a, b in pairwise(history.draws)):
        raise AttemptError("governed history is not strictly chronological")
    expected_provenance = {
        "observed_revision": HISTORY_AUTHORITY,
        "registry_genesis_commit": expected["registry"]["genesis_commit"],
        "registry_git_blob": expected["registry"]["git_blob"],
        "registry_sha256": expected["registry"]["sha256"],
        "registry_head_sha256": expected["registry"]["head_sha256"],
        "seal_sha256": expected["seal"]["sha256"],
        "seal_git_blob": expected["seal"]["git_blob"],
        "base_rows_sha256": expected["base"]["rows_sha256"],
        "base_draw_count": 4442,
        "suffix_git_blob": expected["suffix"]["git_blob"],
        "suffix_sha256": expected["suffix"]["sha256"],
        "suffix_head_sha256": expected["suffix"]["head_sha256"],
        "suffix_event_count": 2,
    }
    if any(provenance.get(key) != value for key, value in expected_provenance.items()):
        raise AttemptError("fixed governed-history identity differs")
    git = GitRepository(authority.repository)
    cfg = yaml.safe_load(git.read_blob(HISTORY_AUTHORITY, "config.yaml"))
    if type(cfg) is not dict:
        raise AttemptError("fixed V1 comparator configuration is invalid")
    return history, cfg


def _target_dates(history: Any, registration: Mapping[str, Any]) -> list[date]:
    targets = [
        row.draw_date
        for row in history.draws
        if date(2020, 1, 1) <= row.draw_date <= date(2025, 12, 31)
    ]
    scopes = {
        "aggregate": targets,
        "first_half": targets[:314],
        "second_half": targets[314:],
    }
    for name, dates in scopes.items():
        raw = "".join(target.isoformat() + "\n" for target in dates).encode("ascii")
        identity = registration["target_date_identities"][name]
        if (
            len(dates) != identity["target_count"]
            or len(raw) != identity["bytes"]
            or _sha(raw) != identity["sha256"]
        ):
            raise AttemptError("fixed historical target scope differs")
    return targets


def _publish_git_manifest(
    git: GitRepository, authority: VerifiedAuthorization, paths: Mapping[str, Path]
) -> str:
    """Create an unattached artifact commit with a self-reference-free manifest.

    No ref changes and no network publication occur here. The manifest names
    its parent and tree inputs; its own containing commit is discovered from
    the immutable commit object, avoiding impossible self-referential bytes.
    """
    file_keys = ("claim", "ledger", "json", "markdown")
    files = []
    for key in file_keys:
        path = paths[key]
        raw = path.read_bytes()
        oid = (
            git.run("hash-object", "-w", "--stdin", input_bytes=raw)
            .decode("ascii")
            .strip()
        )
        files.append(
            {
                "path": path.relative_to(git.root).as_posix(),
                "git_blob": _oid(oid),
                "sha256": _sha(raw),
                "bytes": len(raw),
            }
        )
    manifest = {
        "schema_version": "lotto649-v12.0.1-report-commit-manifest-v1",
        "classification": "consumed_historical_diagnostic_only",
        "parent_commit": authority.execution_commit,
        "authorization_sha256": authority.authorization_sha256,
        "files": files,
        "self_reference": "containing_commit_resolved_from_Git_object_not_embedded",
    }
    _publish_exclusive(
        paths["commit_staging"], paths["commit"], _canonical(manifest) + b"\n"
    )
    raw = paths["commit"].read_bytes()
    files.append(
        {
            "path": paths["commit"].relative_to(git.root).as_posix(),
            "git_blob": _oid(
                git.run("hash-object", "-w", "--stdin", input_bytes=raw)
                .decode()
                .strip()
            ),
        }
    )
    # Build a fresh index explicitly; never stage the caller's index or directory.
    index = paths["commit"].parent / (".v12.0.1-index-" + secrets.token_hex(16))
    environment = _git_environment()
    environment["GIT_INDEX_FILE"] = str(index)

    def index_git(*arguments: str, input_bytes: bytes | None = None) -> bytes:
        try:
            result = subprocess.run(
                [
                    "/usr/bin/git",
                    "-c",
                    "core.hooksPath=/dev/null",
                    "-C",
                    str(git.root),
                    *arguments,
                ],
                input=input_bytes,
                env=environment,
                capture_output=True,
                timeout=120,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            raise AttemptError(
                "artifact commit construction failed; no retry"
            ) from None
        if result.returncode:
            raise AttemptError("artifact commit construction failed; no retry")
        return result.stdout

    try:
        index_git("read-tree", authority.execution_commit)
        entries = b"".join(
            f"100644 {entry['git_blob']}\t{entry['path']}\0".encode() for entry in files
        )
        index_git("update-index", "-z", "--index-info", input_bytes=entries)
        tree = _oid(index_git("write-tree").decode().strip())
        now = int(datetime.now(UTC).timestamp())
        identity = "LOTTO649 V12 Historical Evidence <lotto649-v12-evidence@users.noreply.github.com>"
        message = b"Record immutable V12.0.1 consumed historical diagnostic artifacts\n"
        commit_raw = (
            f"tree {tree}\nparent {authority.execution_commit}\nauthor {identity} {now} +0000\ncommitter {identity} {now} +0000\n\n".encode(
                "ascii"
            )
            + message
        )
        commit = _oid(
            git.run(
                "hash-object", "-t", "commit", "-w", "--stdin", input_bytes=commit_raw
            )
            .decode()
            .strip()
        )
        if git.parents(commit) != (authority.execution_commit,) or {
            path for _status, path in git.changes(authority.execution_commit, commit)
        } != {entry["path"] for entry in files}:
            raise AttemptError("artifact commit scope differs")
        return commit
    finally:
        if index.exists():
            index.unlink()


def _run_canonical(authority: VerifiedAuthorization, lease: Lease) -> dict[str, Any]:
    _consume_lease(authority, lease)
    from .v12_0_1_evidence import four_forecasts

    git = GitRepository(authority.repository)
    paths = _paths(authority.repository / "reports", synthetic=False)
    _require_fresh_outputs(paths)
    bindings = {
        **authority.payload,
        "execution_authority_M_A_H2": authority.execution_commit,
        "authorization_source_A_H_s2": authority.source_commit,
        "authorization_sha256": authority.authorization_sha256,
        "lease_ref": lease.ref,
        "lease_commit_L_H2": lease.commit,
        "nonce_hex": lease.nonce_hex,
        "seed": 649,
        "classification": "consumed_historical_diagnostic_only",
    }
    _exclusive_bytes(
        paths["claim"],
        _canonical(
            {
                "schema_version": "lotto649-v12.0.1-permanent-claim-v1",
                "claimed_at": _utc_now(),
                "bindings": bindings,
            }
        )
        + b"\n",
    )
    ledger = DurableLedger(paths["ledger"], bindings)
    ledger.append(
        "attempt_claimed", {"claim_sha256": _sha(paths["claim"].read_bytes())}
    )
    _ACTIVE_ATTEMPTS.append(authority)
    rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    stop_reason: str | None = None
    try:
        history, cfg = _load_governed_history(authority)
        r1 = _json(git.read_blob(R1, R1_PATH))
        targets = _target_dates(history, r1)
        positions = {row.draw_date: number for number, row in enumerate(history.draws)}

        def prefix_for(target: date) -> Sequence[Any]:
            return history.draws[: positions[target]]

        def reveal(target: date) -> Any:
            return history.draws[positions[target]]

        def forecast(
            prefix: Sequence[Any], target: date
        ) -> Sequence[Mapping[str, Any]]:
            _verify_worktree_runtime(
                git,
                authority.execution_commit,
                authority.payload["runtime_dependency_closure"],
            )
            return four_forecasts(prefix, target, cfg)

        rows, warnings, stop_reason = _drive_sequence(
            targets,
            prefix_for,
            reveal,
            forecast,
            bindings=bindings,
            ledger=ledger,
            notify=_default_notification,
            synthetic=False,
        )
        _verify_worktree_runtime(
            git,
            authority.execution_commit,
            authority.payload["runtime_dependency_closure"],
        )
    except Exception:  # noqa: BLE001 -- permanent failures never retry.
        # Never retry or include exception text, which may contain source values.
        stop_reason = "Archive_after_claim_failure_no_retry"
        warnings.append("one_shot_worker_failed_after_claim")
        ledger.append(
            "attempt_archived", {"reason": stop_reason, "retry_allowed": False}
        )
        rows = _durable_scored_rows(paths["ledger"])
    report = _report_files(
        paths,
        rows,
        bindings,
        ledger=ledger,
        warnings=warnings,
        stop_reason=stop_reason,
        synthetic=False,
    )
    commit = _publish_git_manifest(git, authority, paths)
    return {
        "artifact_commit": commit,
        "classification": "consumed_historical_diagnostic_only",
        "report_path": str(paths["json"]),
        "stop_reason": stop_reason,
        "report": report,
    }


def main() -> int:
    """The only canonical entry, invoked by the isolated fixed launcher."""
    try:
        if sys.argv[1:] != [COMMAND[-1]] or not (
            sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
        ):
            raise AuthorizationError("the fixed isolated launcher is required")
        _require_default_notification_environment()
        repository = Path(__file__).resolve().parents[2]
        api = FixedGitHubApi(os.environ.get("GH_TOKEN", ""))
        authority = verify_authorization(repository, api=api)
        _require_fresh_outputs(_paths(repository / "reports", synthetic=False))
        lease = acquire_historical_lease(authority, api)
        result = _run_canonical(authority, lease)
        print(
            _canonical(
                {
                    "artifact_commit": result["artifact_commit"],
                    "classification": result["classification"],
                    "report_path": result["report_path"],
                    "stop_reason": result["stop_reason"],
                }
            ).decode("utf-8")
        )
        return (
            0 if result["stop_reason"] != "Archive_after_claim_failure_no_retry" else 1
        )
    except Exception:  # noqa: BLE001 -- never expose authenticated exceptions.
        print(
            "V12.0.1 authority or one-shot execution failed; preserve all evidence and do not retry.",
            file=sys.stderr,
        )
        return 1
