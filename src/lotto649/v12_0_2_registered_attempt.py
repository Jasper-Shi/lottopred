"""One-shot V12.0.2 authority, durable ordering, and fixed GitHub boundary.

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
import stat
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
R3 = "d8dcd31ab9bc4a78eaac26decf80e3259b973d71"
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
R3_PATH = (
    "evidence/research_registrations/v12-post-rng-parity-composition-transition-v3.json"
)
CONFIG_PATH = "config/research-v12-0-2-post-rng-parity-composition-transition.yaml"
AUTHORIZATION_PATH = "evidence/research_authorizations/v12-post-rng-parity-composition-transition-v3-historical.json"
LEASE_REF = "refs/heads/v12-consumption-v12.0.2"
COMMAND = ["python3.12", "tools/run_v12_0_2_historical.py", "--consume-v12-0-2-once"]
EVIDENCE_PATH = "src/lotto649/v12_0_2_evidence.py"
ATTEMPT_PATH = "src/lotto649/v12_0_2_registered_attempt.py"
LAUNCHER_PATH = "tools/run_v12_0_2_historical.py"
IMPLEMENTATION_PATHS = (
    EVIDENCE_PATH,
    ATTEMPT_PATH,
    LAUNCHER_PATH,
    "tests/test_v12_0_2_registered_attempt.py",
    "tests/test_v12_0_2_evidence_equivalence.py",
    "tests/fixtures/v12_0_2_git_commit_projection.json",
)
_STEM = "v12_post_rng_parity_composition_transition_v12.0.2_historical"
_ARTIFACT_NAMES = {
    "claim": _STEM + ".claim",
    "ledger": _STEM + ".ledger.jsonl",
    "json": _STEM + ".json",
    "markdown": _STEM + ".md",
    "json_staging": _STEM + ".json.staging",
    "markdown_staging": _STEM + ".md.staging",
    "commit": _STEM + ".commit.json",
    "commit_staging": _STEM + ".commit.json.staging",
    "startup": _STEM + ".startup.jsonl",
}
_API_PREFIX = "/repos/Jasper-Shi/lottopred"
_API_ORIGIN = "https://api.github.com"
_OID = re.compile(r"[0-9a-f]{40}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_ROUTE_OVERRIDES = frozenset({"SMTP_HOST", "SMTP_PORT", "EMAIL_FROM", "EMAIL_TO"})
_EXTERNAL_MODULES = frozenset(
    {"numpy", "pandas", "requests", "yaml", "sklearn", "scipy", "bs4", "pypdf"}
)
# These are the standard-library roots actually used by the frozen historical
# closure, rather than every module the running interpreter happens to offer.
# A newly introduced loader/reflection module cannot silently enlarge that set.
_STDLIB_MODULES = frozenset(
    {
        "__future__",
        "abc",
        "ast",
        "collections",
        "csv",
        "dataclasses",
        "datetime",
        "email",
        "fractions",
        "functools",
        "hashlib",
        "importlib",
        "io",
        "itertools",
        "json",
        "math",
        "os",
        "pathlib",
        "platform",
        "re",
        "secrets",
        "smtplib",
        "stat",
        "subprocess",
        "sys",
        "sysconfig",
        "threading",
        "typing",
        "urllib",
    }
)
# Static capability inventory derived from the reviewed historical source
# closure. Verification must never expand this inventory from the source it is
# being asked to authorize. This constrains repository code, not arbitrary
# Python or the internals of the separately pinned dependency distributions.
_REGISTERED_IMPORT_MODULES = frozenset(
    {
        "ast",
        "csv",
        "hashlib",
        "io",
        "itertools",
        "json",
        "math",
        "numpy",
        "os",
        "pandas",
        "platform",
        "re",
        "requests",
        "secrets",
        "smtplib",
        "stat",
        "subprocess",
        "sys",
        "sysconfig",
        "yaml",
    }
)
_REGISTERED_FROM_IMPORTS = {
    "__future__": frozenset({"annotations"}),
    "abc": frozenset({"ABC", "abstractmethod"}),
    "bs4": frozenset({"BeautifulSoup"}),
    "collections.abc": frozenset({"Callable", "Iterable", "Mapping", "Sequence"}),
    "dataclasses": frozenset({"asdict", "dataclass"}),
    "datetime": frozenset({"UTC", "date", "datetime", "timedelta"}),
    "email.message": frozenset({"EmailMessage"}),
    "fractions": frozenset({"Fraction"}),
    "functools": frozenset({"lru_cache"}),
    "hashlib": frozenset({"sha256"}),
    "importlib.metadata": frozenset({"distributions"}),
    "itertools": frozenset({"pairwise"}),
    "pathlib": frozenset({"Path", "PurePosixPath"}),
    "sklearn.ensemble": frozenset({"HistGradientBoostingClassifier"}),
    "sklearn.linear_model": frozenset({"LogisticRegression"}),
    "sklearn.pipeline": frozenset({"make_pipeline"}),
    "sklearn.preprocessing": frozenset({"StandardScaler"}),
    "threading": frozenset({"Lock"}),
    "typing": frozenset({"Any", "Iterable", "Self"}),
    "urllib.parse": frozenset({"urlsplit"}),
}
_REGISTERED_MODULE_API = {
    "ast": frozenset(
        {
            "AST",
            "AnnAssign",
            "Attribute",
            "Call",
            "ClassDef",
            "FunctionDef",
            "Import",
            "ImportFrom",
            "Load",
            "Name",
            "Store",
            "arg",
            "dump",
            "iter_child_nodes",
            "parse",
            "walk",
        }
    ),
    "csv": frozenset(
        {
            "reader",
            "writer",
        }
    ),
    "datetime.date": frozenset(
        {
            "fromisoformat",
        }
    ),
    "datetime.datetime": frozenset(
        {
            "fromisoformat",
            "fromtimestamp",
            "now",
            "strptime",
        }
    ),
    "hashlib": frozenset(
        {
            "sha1",
            "sha256",
        }
    ),
    "io": frozenset(
        {
            "StringIO",
        }
    ),
    "itertools": frozenset(
        {
            "combinations",
        }
    ),
    "json": frozenset(
        {
            "JSONDecodeError",
            "dumps",
            "loads",
        }
    ),
    "math": frozenset(
        {
            "comb",
            "cos",
            "exp",
            "expm1",
            "fsum",
            "isfinite",
            "log",
            "log1p",
            "pi",
            "sin",
            "sqrt",
        }
    ),
    "numpy": frozenset(
        {
            "arange",
            "array",
            "clip",
            "diff",
            "dot",
            "exp",
            "flatnonzero",
            "float64",
            "full",
            "log",
            "mean",
            "ndarray",
            "polyfit",
            "quantile",
            "random",
            "random.default_rng",
            "std",
            "sum",
            "unique",
            "zeros",
        }
    ),
    "os": frozenset(
        {
            "O_CREAT",
            "O_DIRECTORY",
            "O_EXCL",
            "O_NOFOLLOW",
            "O_RDONLY",
            "O_RDWR",
            "O_WRONLY",
            "SEEK_CUR",
            "close",
            "devnull",
            "dup",
            "environ",
            "environ.get",
            "environ.items",
            "execve",
            "fdopen",
            "fstat",
            "fsync",
            "getenv",
            "link",
            "lseek",
            "mkdir",
            "open",
            "path",
            "path.lexists",
            "pread",
            "stat",
            "unlink",
            "write",
        }
    ),
    "pandas": frozenset(
        {
            "DataFrame",
            "concat",
        }
    ),
    "platform": frozenset(
        {
            "machine",
            "platform",
            "python_version",
        }
    ),
    "re": frozenset(
        {
            "IGNORECASE",
            "compile",
            "escape",
            "finditer",
            "fullmatch",
            "match",
            "search",
            "sub",
        }
    ),
    "requests": frozenset(
        {
            "Session",
            "adapters",
            "adapters.HTTPAdapter",
        }
    ),
    "secrets": frozenset(
        {
            "token_hex",
        }
    ),
    "smtplib": frozenset(
        {
            "SMTP",
        }
    ),
    "stat": frozenset(
        {
            "S_IMODE",
            "S_ISDIR",
            "S_ISREG",
            "S_ISVTX",
        }
    ),
    "subprocess": frozenset(
        {
            "SubprocessError",
            "run",
        }
    ),
    "sys": frozenset(
        {
            "argv",
            "byteorder",
            "dont_write_bytecode",
            "executable",
            "flags",
            "flags.isolated",
            "flags.no_site",
            "float_info",
            "float_info.mant_dig",
            "float_info.max_exp",
            "float_info.radix",
            "implementation",
            "implementation.name",
            "modules",
            "modules.items",
            "path",
            "path.append",
            "path.insert",
            "stderr",
            "version_info",
            "version_info.major",
            "version_info.minor",
        }
    ),
    "sysconfig": frozenset(
        {
            "get_path",
        }
    ),
    "yaml": frozenset(
        {
            "safe_load",
        }
    ),
}
_REGISTERED_LOCAL_IMPORTS = {
    "lotto649.domain": frozenset({"Draw"}),
    "lotto649.features": frozenset(
        {"BASE_P", "indicator_matrix", "number_feature_frame"}
    ),
    "lotto649.history_registry": frozenset(
        {
            "RegistryProvenance",
            "RegistrySealIdentity",
            "RegistrySuffixIdentity",
            "RegistryTransaction",
            "load_history_registry",
            "resolve_repository_head",
        }
    ),
    "lotto649.models.base": frozenset({"ProbabilityModel", "normalize_expected_six"}),
    "lotto649.models.baselines": frozenset(
        {"EmaGapModel", "LongFrequencyModel", "RandomBaseline", "RecentFrequencyModel"}
    ),
    "lotto649.models.ensemble": frozenset({"EnsembleModel"}),
    "lotto649.models.factory": frozenset({"build_models"}),
    "lotto649.models.logistic": frozenset({"LogisticNumberModel"}),
    "lotto649.models.v12_parity_transition": frozenset(
        {
            "CANDIDATE_MODEL_NAME",
            "CONTROL_MODEL_NAME",
            "FAIR_MEAN",
            "FAIR_SET_COUNT",
            "PSEUDO_PARTITION_LABELS",
            "PSEUDO_PARTITION_SHA256",
            "ParityForecast",
            "STANDARDIZED_BUCKET_STATES",
            "TRUE_ODD_LABELS",
            "forecast_candidate",
            "forecast_control",
            "tilted_moment_log_z",
        }
    ),
    "lotto649.models.v2_statistical": frozenset({"V2StatisticalModel"}),
    "lotto649.models.v3_boosting": frozenset({"V3BoostingModel"}),
    "lotto649.models.v4_ensemble": frozenset({"V4EnsembleModel"}),
    "lotto649.notification": frozenset({"send_email"}),
    "lotto649.official_history": frozenset(
        {
            "canonical_official_rows_sha256",
            "expected_lotto649_draw_dates",
            "parse_lotoquebec_detail_html",
            "parse_wclc_target_html",
        }
    ),
    "lotto649.operational_history": frozenset(
        {"load_published_history", "operational_history_provenance"}
    ),
    "lotto649.optimizer": frozenset({"select_combination"}),
    "lotto649.research_features": frozenset(
        {"rich_number_feature_frame", "standardized_signal_scores"}
    ),
    "lotto649.v12_0_2_evidence": frozenset(
        {
            "build_report",
            "canonical_json_bytes",
            "four_forecasts",
            "opportunity_summary",
            "render_markdown",
            "score_target",
            "validate_frozen_payload",
        }
    ),
    "lotto649.v12_0_2_registered_attempt": frozenset({"main"}),
    "lotto649.verified_history": frozenset(
        {"VerifiedHistory", "_load_verified_history_from_immutable_bytes"}
    ),
}
_REGISTERED_ATTRIBUTE_NAMES = frozenset(
    {
        "AST",
        "AnnAssign",
        "Attribute",
        "Call",
        "ClassDef",
        "DataFrame",
        "FunctionDef",
        "HTTPAdapter",
        "IGNORECASE",
        "Import",
        "ImportFrom",
        "JSONDecodeError",
        "Load",
        "Name",
        "O_CREAT",
        "O_DIRECTORY",
        "O_EXCL",
        "O_NOFOLLOW",
        "O_RDONLY",
        "O_RDWR",
        "O_WRONLY",
        "SEEK_CUR",
        "SMTP",
        "S_IMODE",
        "S_ISDIR",
        "S_ISREG",
        "S_ISVTX",
        "Session",
        "Store",
        "StringIO",
        "SubprocessError",
        "__file__",
        "__init__",
        "__new__",
        "__post_init__",
        "__setattr__",
        "_bindings",
        "_cache_key",
        "_cache_value",
        "_closed",
        "_commit_post_attempted",
        "_create",
        "_create_ref_attempted",
        "_from_verified_facts",
        "_head",
        "_last_status",
        "_owner",
        "_request_active",
        "_sequence",
        "_session",
        "_stream",
        "_terminal",
        "_training_frame",
        "absolute",
        "adapters",
        "add",
        "allowed_paths",
        "ancestor",
        "any",
        "append",
        "arange",
        "arg",
        "args",
        "argv",
        "array",
        "artifact_commit",
        "as_dict",
        "as_posix",
        "asname",
        "astimezone",
        "astype",
        "attr",
        "authorization_review_records",
        "authorization_sha256",
        "base",
        "beta",
        "bonus",
        "byte_count",
        "byteorder",
        "changes",
        "checkpoint",
        "clip",
        "close",
        "close_stream",
        "closed",
        "columns",
        "comb",
        "combinations",
        "commit",
        "compile",
        "concat",
        "copy",
        "cos",
        "count",
        "create_bytes",
        "create_stream",
        "ctx",
        "date",
        "day",
        "decode",
        "default_rng",
        "destination_bucket",
        "destination_date",
        "devnull",
        "diff",
        "digest_sha256",
        "dont_write_bytecode",
        "dot",
        "draw_count",
        "draw_date",
        "draws",
        "dump",
        "dumps",
        "dup",
        "encode",
        "end",
        "endswith",
        "environ",
        "epoch",
        "escape",
        "eta",
        "event_count",
        "evidence_commit",
        "evidence_commits",
        "executable",
        "execution_commit",
        "execve",
        "exists",
        "exp",
        "expected_bucket",
        "expm1",
        "extend",
        "facts",
        "fdopen",
        "file_sha256",
        "fileno",
        "final6",
        "find_all",
        "finditer",
        "fit",
        "flags",
        "flatnonzero",
        "float64",
        "float_info",
        "flush",
        "fragment",
        "fromhex",
        "fromisoformat",
        "fromtimestamp",
        "fstat",
        "fsum",
        "fsync",
        "full",
        "fullmatch",
        "func",
        "generated_at",
        "genesis_commit",
        "get",
        "get_path",
        "get_text",
        "getenv",
        "getvalue",
        "git_blob",
        "groups",
        "head",
        "head_event_sha256",
        "head_sha256",
        "headers",
        "hex",
        "hexdigest",
        "history_through",
        "hostname",
        "http_status",
        "id",
        "implementation",
        "initial_identity",
        "insert",
        "integers",
        "intent",
        "intersection",
        "is_absolute",
        "is_dir",
        "is_file",
        "is_symlink",
        "isfinite",
        "isin",
        "isoformat",
        "isolated",
        "isspace",
        "issubset",
        "items",
        "iter_child_nodes",
        "iter_content",
        "iterdir",
        "iterrows",
        "join",
        "keywords",
        "last_status",
        "level",
        "lexists",
        "link",
        "loads",
        "log",
        "log1p",
        "log_z",
        "login",
        "long_freq",
        "lower",
        "lseek",
        "lstat",
        "lstrip",
        "machine",
        "major",
        "mant_dig",
        "match",
        "max_exp",
        "mean",
        "members",
        "metadata",
        "min_history",
        "min_samples",
        "minor",
        "mkdir",
        "model_name",
        "module",
        "modules",
        "month",
        "mount",
        "name",
        "names",
        "ndarray",
        "no_site",
        "nonce_hex",
        "now",
        "number",
        "numbers",
        "oid",
        "open",
        "parent",
        "parents",
        "parse",
        "partition",
        "parts",
        "password",
        "path",
        "paths",
        "payload",
        "pi",
        "platform",
        "polyfit",
        "pop",
        "port",
        "pread",
        "predict",
        "predict_proba",
        "prefix_byte_count",
        "prefix_sha256",
        "previous_bucket",
        "probabilities",
        "provenance",
        "publication_commit",
        "publish",
        "python_version",
        "quantile",
        "radix",
        "random",
        "ranking",
        "read_blob",
        "read_bytes",
        "reader",
        "receipt",
        "record_append",
        "ref",
        "registry",
        "registry_path",
        "registry_seal",
        "registry_suffix",
        "registry_transaction",
        "relative_to",
        "removeprefix",
        "removesuffix",
        "replace",
        "repository",
        "request",
        "request_json",
        "require_full_clean",
        "resolve",
        "resolved_revision",
        "result_enum",
        "returncode",
        "rglob",
        "root",
        "rows_sha256",
        "rpartition",
        "rstrip",
        "run",
        "safe_load",
        "scheme",
        "seal",
        "seal_raw",
        "sealed",
        "search",
        "select",
        "selected_labels",
        "send_message",
        "sequence",
        "set_content",
        "sha1",
        "sha256",
        "sin",
        "source_commit",
        "split",
        "splitlines",
        "sqrt",
        "st_dev",
        "st_ino",
        "st_mode",
        "st_nlink",
        "st_size",
        "start",
        "startswith",
        "starttls",
        "startup",
        "stat",
        "status_code",
        "std",
        "stderr",
        "stdout",
        "strftime",
        "stride",
        "strip",
        "strptime",
        "sub",
        "suffix",
        "suffix_commit",
        "suffix_raw",
        "sum",
        "target_date",
        "target_draw_date",
        "text",
        "timestamp",
        "to_numpy",
        "token_hex",
        "toordinal",
        "top12",
        "top18",
        "top6",
        "training_draws",
        "transaction",
        "transition_count",
        "transitions",
        "tree",
        "trust_env",
        "tzinfo",
        "uniform",
        "unique",
        "unlink",
        "update",
        "url",
        "username",
        "value",
        "values",
        "verified_identity",
        "verify_owned",
        "version",
        "version_info",
        "walk",
        "weekday",
        "window",
        "write",
        "writer",
        "writerow",
        "x_prev",
        "x_source",
        "year",
        "zeros",
    }
)

_CLOSURE_ROOTS = (
    "config.yaml",
    "config/research-v12-0-2-post-rng-parity-composition-transition.yaml",
    "config/research-v12-post-rng-parity-composition-transition.yaml",
    "evidence/research_registrations/v12-post-rng-parity-composition-transition-v1.json",
    "evidence/research_registrations/v12-post-rng-parity-composition-transition-v2.json",
    "evidence/research_registrations/v12-post-rng-parity-composition-transition-v3.json",
    "requirements/v12-historical.txt",
    "src/lotto649/config.py",
    "src/lotto649/domain.py",
    "src/lotto649/features.py",
    "src/lotto649/models/factory.py",
    "src/lotto649/models/v12_parity_transition.py",
    "src/lotto649/notification.py",
    "src/lotto649/operational_history.py",
    "src/lotto649/research_features.py",
    "src/lotto649/v12_0_2_evidence.py",
    "src/lotto649/v12_0_2_registered_attempt.py",
    "tools/run_v12_0_2_historical.py",
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
            raw.decode("utf-8"),
            object_pairs_hook=_object_pairs,
            parse_constant=_invalid_constant,
        )
        _canonical(result)
    except (ValueError, UnicodeError, OverflowError, RecursionError):
        raise AuthorizationError("invalid JSON evidence") from None
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

    def require_full_clean(
        self, *, authority: VerifiedAuthorization | None = None
    ) -> None:
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
        if self.run("status", "--porcelain=v1", "-z", "--untracked-files=no"):
            raise AuthorizationError("tracked canonical files must be clean")
        allowed: set[str] = set()
        if authority is not None:
            _require_authorization_capability(authority)
            if (
                self.root != authority.repository
                or self.head() != authority.execution_commit
            ):
                raise AuthorizationError(
                    "owned artifacts cannot substitute another repository or HEAD"
                )
            authority.startup.verify_owned()
            if (
                authority.startup.path
                != self.root / "reports" / _ARTIFACT_NAMES["startup"]
            ):
                raise AuthorizationError("owned startup path differs")
            allowed.add(authority.startup.path.relative_to(self.root).as_posix())
            allowed.update(_owned_artifacts(authority).allowed_paths())
        raw_others = self.run("ls-files", "--others", "-z")
        try:
            others = {
                _relative(item.decode("utf-8"))
                for item in raw_others.split(b"\0")
                if item
            }
        except UnicodeError:
            raise AuthorizationError("untracked path encoding differs") from None
        if others != allowed:
            raise AuthorizationError(
                "untracked or ignored files lack current creation provenance"
            )


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
        "src/lotto649/v12_0_2_registered_attempt.py",
        "__init__",
    ): "2d75234e45076dcc7d640d3ef40dc7a84574d99dee3505661765d1129e42235a",
    (
        "src/lotto649/v12_0_2_registered_attempt.py",
        "_create",
    ): "da738b9541b29d8ddcb7fc8683372d969a9e26dd830eb58fc6bde7c2c65ad2b2",
    (
        "src/lotto649/v12_0_2_registered_attempt.py",
        "_issue_authorization",
    ): "ff9e4784432eb3135d363cd53398278bd63d6a153f02592853e0ab34cac9d91d",
    (
        "src/lotto649/v12_0_2_registered_attempt.py",
        "_issue_lease",
    ): "b0987c4f2c0a72b7c0c90686a4ae6dbb2d096e4b690354893f34b1fdcf386bbf",
    (
        "src/lotto649/v12_0_2_registered_attempt.py",
        "_issue_verified_facts",
    ): "5fa1da583be2ba05352457b1dfa48913b9bc14e5a179130a4303c46cbaf105fa",
    (
        "src/lotto649/v12_0_2_registered_attempt.py",
        "_verify_loaded_modules",
    ): "5e28b8ed294c2c6a8961eccc8ef7e76e51a3879db4f09af11d007055ff9ace5f",
    (
        "src/lotto649/v12_0_2_registered_attempt.py",
        "for_synthetic",
    ): "bd35d81e278b90d25b24fe1d51311b01ec18348dc2c761c15bcdd49338b90e4f",
    (
        "tools/run_v12_0_2_historical.py",
        "main",
    ): "014eed8ea0a875f19e26e6fd9a6513b5d94c8c60b9e70b44030c0a48f9f0eaba",
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
    ATTEMPT_PATH: frozenset(
        {
            "f5f6801159316fb8716b4d1807221bf315d8a8443ce9ec398307862964f5d0bc",
            "91188ac951a6be0d442ad076e46bb9c96a3d3859ce29447504011be67544c1b7",
        }
    ),
    LAUNCHER_PATH: frozenset(
        {"a467584555ea4b83948d5ba8334ae507b275e4f934fc0968024bea19bd00207b"}
    ),
}
_LEGACY_PROCESS_SOURCE_SHA256 = {
    "src/lotto649/history_registry.py": "5b0cde9f95da8181fb46f64ffeeaa148ddd625c9ae951e34470c8b3d6c8596d8",
    "src/lotto649/verified_history.py": "214e59071f3f8d232aca5f7850060a88568c35fb89246dea64f99c20265ead80",
}


def _check_import_capabilities(
    path: str, tree: ast.AST, parents: Mapping[ast.AST, ast.AST]
) -> None:
    """Check fixed imports, exact API paths, and direct alias propagation."""
    bindings: dict[str, str] = {}
    module_aliases: set[str] = set()
    module = path.removeprefix("src/").removesuffix(".py").replace("/", ".")
    package = (
        module.removesuffix(".__init__")
        if module.endswith(".__init__")
        else module.rpartition(".")[0]
    )
    for node in ast.walk(tree):
        entries: list[tuple[str, str]] = []
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name not in _REGISTERED_IMPORT_MODULES:
                    raise AuthorizationError("unregistered module import capability")
                bound_name = alias.asname or alias.name
                module_aliases.add(bound_name)
                entries.append((bound_name, alias.name))
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                pieces = package.split(".")
                if node.level > len(pieces):
                    raise AuthorizationError(
                        "relative import escapes the registered package"
                    )
                prefix = ".".join(pieces[: len(pieces) - node.level + 1])
                base = prefix + ("." + node.module if node.module else "")
            else:
                base = node.module or ""
            allowed = (
                _REGISTERED_LOCAL_IMPORTS.get(base, frozenset())
                if base.startswith("lotto649")
                else _REGISTERED_FROM_IMPORTS.get(base, frozenset())
            )
            for alias in node.names:
                if alias.name not in allowed:
                    raise AuthorizationError("unregistered imported member capability")
                if base != "__future__":
                    entries.append(
                        (alias.asname or alias.name, base + "." + alias.name)
                    )
        for bound_name, origin in entries:
            if bound_name in bindings and bindings[bound_name] != origin:
                raise AuthorizationError("import capability alias is rebound")
            bindings[bound_name] = origin
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Attribute)
            and node.attr not in _REGISTERED_ATTRIBUTE_NAMES
        ):
            raise AuthorizationError("unregistered object attribute capability")
        if isinstance(node, ast.Name) and node.id in bindings:
            parent = parents.get(node)
            if isinstance(node.ctx, ast.Store):
                # Dataclass fields with no value do not rebind a module name.
                data_field = (
                    isinstance(parent, ast.AnnAssign)
                    and parent.value is None
                    and isinstance(parents.get(parent), ast.ClassDef)
                )
                if not data_field:
                    raise AuthorizationError("imported capability cannot be rebound")
            if (
                isinstance(node.ctx, ast.Load)
                and node.id in module_aliases
                and (not isinstance(parent, ast.Attribute) or parent.value is not node)
            ):
                raise AuthorizationError("module capability cannot escape as a value")
        if isinstance(node, ast.arg) and node.arg in bindings:
            raise AuthorizationError("argument shadows an imported capability")
        if isinstance(node, (ast.ClassDef, ast.FunctionDef)) and node.name in bindings:
            raise AuthorizationError("definition shadows an imported capability")
        if isinstance(node, ast.Attribute):
            root_name, separator, member_path = _dotted(node).partition(".")
            origin = bindings.get(root_name)
            if (
                separator
                and origin is not None
                and member_path not in _REGISTERED_MODULE_API.get(origin, frozenset())
            ):
                raise AuthorizationError("unregistered module API member capability")


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
    _check_import_capabilities(path, tree, parents)
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
        "attrgetter",
        "methodcaller",
        "FunctionType",
        "LambdaType",
        "CodeType",
        "ModuleType",
        "new_class",
        "resolve_bases",
        "DynamicClassAttribute",
        "get_type_hints",
        "get_annotations",
        "evaluate_forward_ref",
        "_eval_type",
        "ForwardRef",
        "_evaluate",
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
            if any(alias.name in forbidden_attributes for alias in node.names):
                raise AuthorizationError(
                    "reflection or code-loading aliases are prohibited"
                )
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
            # Regex compilation is the existing parser capability; Python/code
            # evaluation ports remain forbidden when reached as attributes too.
            regular_expression_compile = dotted == "re.compile"
            if node.attr in forbidden_attributes or (
                node.attr in dynamic_names and not regular_expression_compile
            ):
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
                node.attr in {"__new__", "__setattr__", "__init__"}
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
                if not (
                    isinstance(node, ast.ImportFrom) and node.level
                ) and top not in _STDLIB_MODULES | _EXTERNAL_MODULES | {"lotto649"}:
                    raise AuthorizationError("unregistered runtime import root")
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
                    top not in _STDLIB_MODULES
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


# Authored by /root/i3_transport, session i3-transport-authoring-20260913.
# Root integration must include this actual contributor in source provenance.


def _closed_object(
    value: object, required: set[str], optional: set[str] | None = None
) -> dict[str, Any]:
    if (
        type(value) is not dict
        or not required.issubset(value)
        or set(value) - required - (optional or set())
    ):
        raise AuthorizationError("unregistered GitHub object shape")
    return value


def _exact_string(value: object, expected: str) -> None:
    if type(value) is not str or value != expected:
        raise AuthorizationError("GitHub object identity differs")


def _nonempty_node(value: object) -> None:
    if type(value) is not str or not value:
        raise AuthorizationError("GitHub node metadata is malformed")


def _lease_request_parts(payload: object) -> tuple[str, bytes, str]:
    """Reconstruct the registered raw object solely from the closed request."""
    request = _closed_object(
        payload, {"tree", "parents", "author", "committer", "message"}
    )
    tree = _oid(request["tree"])
    parents = request["parents"]
    if type(parents) is not list or len(parents) != 1:
        raise AuthorizationError("lease must have exactly one parent")
    parent = _oid(parents[0])
    expected_name = "LOTTO649 V12 Consumption Lease"
    expected_email = "lotto649-v12-lease@users.noreply.github.com"
    author = _closed_object(request["author"], {"name", "email", "date"})
    committer = _closed_object(request["committer"], {"name", "email", "date"})
    for identity in (author, committer):
        _exact_string(identity["name"], expected_name)
        _exact_string(identity["email"], expected_email)
        if (
            type(identity["date"]) is not str
            or re.fullmatch(
                r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z",
                identity["date"],
            )
            is None
        ):
            raise AuthorizationError("lease timestamp differs")
    if author != committer:
        raise AuthorizationError("lease identities differ")
    try:
        parsed_date = datetime.strptime(author["date"], "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=UTC
        )
        instant = int(parsed_date.timestamp())
        message = request["message"]
        if type(message) is not str or not message.endswith("\n"):
            raise AuthorizationError("lease POST message differs")
        message_bytes = message.encode("utf-8")
        canonical_body = message_bytes[:-1]
        body = _json(canonical_body)
        if _canonical(body) != canonical_body:
            raise AuthorizationError("lease message is not canonical JSON plus one LF")
    except AuthorizationError:
        raise
    except (ValueError, UnicodeError, OverflowError, OSError):
        raise AuthorizationError(
            "lease request encoding or date is malformed"
        ) from None
    _closed_object(
        body,
        {
            "authorization_seal_sha256",
            "canonical_command",
            "execution_authority_M_A",
            "nonce_hex",
            "schema_version",
        },
    )
    _digest(body["authorization_seal_sha256"])
    _digest(body["nonce_hex"])
    _exact_string(body["execution_authority_M_A"], parent)
    _exact_string(body["schema_version"], "lotto649-v12-consumption-lease-v1")
    if (
        type(body["canonical_command"]) is not list
        or any(type(part) is not str for part in body["canonical_command"])
        or body["canonical_command"] != COMMAND
    ):
        raise AuthorizationError("unregistered lease command")
    identity_line = f"{expected_name} <{expected_email}> {instant} +0000"
    raw = (
        f"tree {tree}\nparent {parent}\nauthor {identity_line}\ncommitter {identity_line}\n\n".encode(
            "ascii"
        )
        + message_bytes
    )
    oid = hashlib.sha1(
        b"commit " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()
    return oid, raw, canonical_body.decode("utf-8")


def _verify_lease_metadata(
    key: str, value: object, oid: str, payload: Mapping[str, Any]
) -> None:
    commit_url = _API_ORIGIN + _API_PREFIX + "/git/commits/" + oid
    html_url = "https://github.com/" + REPOSITORY + "/commit/" + oid
    if key == "node_id":
        _nonempty_node(value)
    elif key == "url":
        _exact_string(value, commit_url)
    elif key == "html_url":
        _exact_string(value, html_url)
    elif key in {"author", "committer"}:
        identity = _closed_object(value, {"name", "email", "date"})
        for field in ("name", "email", "date"):
            _exact_string(identity[field], payload[key][field])
    elif key == "tree":
        tree = _closed_object(value, {"sha", "url"})
        _exact_string(tree["sha"], payload["tree"])
        _exact_string(
            tree["url"], _API_ORIGIN + _API_PREFIX + "/git/trees/" + payload["tree"]
        )
    elif key == "parents":
        if type(value) is not list or len(value) != 1:
            raise AuthorizationError("GitHub parent collection differs")
        parent = _closed_object(value[0], {"sha", "url", "html_url"})
        parent_oid = payload["parents"][0]
        _exact_string(parent["sha"], parent_oid)
        _exact_string(
            parent["url"], _API_ORIGIN + _API_PREFIX + "/git/commits/" + parent_oid
        )
        _exact_string(
            parent["html_url"],
            "https://github.com/" + REPOSITORY + "/commit/" + parent_oid,
        )
    elif key == "verification":
        verification = _closed_object(
            value, {"verified", "reason", "signature", "payload", "verified_at"}
        )
        if (
            verification["verified"] is not False
            or verification["signature"] is not None
            or verification["payload"] is not None
            or verification["verified_at"] is not None
        ):
            raise AuthorizationError("GitHub lease unsigned verification differs")
        _exact_string(verification["reason"], "unsigned")
    else:
        raise AuthorizationError("unregistered GitHub metadata field")


def _verify_lease_post_response(
    observed: object, oid: str, payload: Mapping[str, Any]
) -> None:
    expected_oid, _raw, _body = _lease_request_parts(payload)
    _exact_string(_oid(oid), expected_oid)
    response = _closed_object(
        observed,
        {"sha"},
        {
            "node_id",
            "url",
            "html_url",
            "author",
            "committer",
            "tree",
            "message",
            "parents",
            "verification",
        },
    )
    _exact_string(response["sha"], oid)
    for key in response:
        if key == "sha":
            continue
        if key == "message":
            # POST display text is typed metadata, never the message proof.
            if type(response[key]) is not str:
                raise AuthorizationError("GitHub POST message metadata is malformed")
        else:
            _verify_lease_metadata(key, response[key], oid, payload)


def _verify_lease_object(
    observed: object, oid: str, raw: bytes, payload: Mapping[str, Any]
) -> None:
    expected_oid, expected_raw, canonical_body = _lease_request_parts(payload)
    if type(raw) is not bytes or raw != expected_raw:
        raise AuthorizationError("canonical lease raw bytes differ")
    _exact_string(_oid(oid), expected_oid)
    response = _closed_object(
        observed,
        {
            "sha",
            "node_id",
            "url",
            "html_url",
            "author",
            "committer",
            "tree",
            "message",
            "parents",
            "verification",
        },
    )
    _exact_string(response["sha"], oid)
    # This is an exact registered projection, never strip/rstrip/normalization.
    _exact_string(response["message"], canonical_body)
    for key in response:
        if key not in {"sha", "message"}:
            _verify_lease_metadata(key, response[key], oid, payload)


def _verify_lease_ref(observed: object, oid: str) -> None:
    _oid(oid)
    response = _closed_object(observed, {"ref", "node_id", "url", "object"})
    _exact_string(response["ref"], LEASE_REF)
    _nonempty_node(response["node_id"])
    _exact_string(response["url"], _API_ORIGIN + _API_PREFIX + "/git/" + LEASE_REF)
    ref_object = _closed_object(response["object"], {"sha", "type", "url"})
    _exact_string(ref_object["sha"], oid)
    _exact_string(ref_object["type"], "commit")
    _exact_string(ref_object["url"], _API_ORIGIN + _API_PREFIX + "/git/commits/" + oid)


class TransportError(AuthorizationError):
    """Only closed safe facts cross the HTTP failure boundary."""

    def __init__(self, result_enum: str, http_status: int | None = None) -> None:
        if result_enum not in {
            "http_rejected",
            "transport_failed",
            "malformed_response",
            "identity_mismatch",
        }:
            raise AuthorizationError("unregistered transport result enum")
        if http_status is not None and (
            type(http_status) is not int or not 100 <= http_status <= 599
        ):
            raise AuthorizationError("unregistered HTTP status")
        self.result_enum = result_enum
        self.http_status = http_status
        super().__init__(result_enum)


def _transport_json(raw: bytes) -> dict[str, Any] | list[dict[str, Any]]:
    """Decode strict UTF-8 JSON; reject duplicate keys and every nonfinite form."""
    try:
        result = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_object_pairs,
            parse_constant=_invalid_constant,
        )
        # Also rejects finite-looking decimal overflow and unpaired surrogates.
        _canonical(result)
    except (
        AuthorizationError,
        ValueError,
        UnicodeError,
        OverflowError,
        RecursionError,
    ):
        raise TransportError("malformed_response") from None
    if type(result) not in {dict, list}:
        raise TransportError("malformed_response")
    return result


class FixedGitHubApi:
    """Closed fixed-origin transport, with one poisoned slot per mutation."""

    def __init__(self, token: str) -> None:
        import requests

        if (
            type(token) is not str
            or not token
            or len(token) > 512
            or any(ord(character) < 33 or character.isspace() for character in token)
        ):
            raise AuthorizationError("GitHub credential unavailable")
        self._session = requests.Session()
        self._session.trust_env = False
        self._session.mount("https://", requests.adapters.HTTPAdapter(max_retries=0))
        self._session.headers.update(
            {
                "Authorization": "Bearer " + token,
                "Accept": "application/vnd.github+json",
                "Accept-Encoding": "identity",
                "Content-Type": "application/json",
                "User-Agent": "lotto649-v12.0.2",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )
        self._commit_post_attempted = False
        self._create_ref_attempted = False
        self._last_status: int | None = None
        self._request_active = False
        self._terminal = False

    @property
    def last_status(self) -> int | None:
        """Status for the current/latest serialized call; never response text."""
        return self._last_status

    def request_json(
        self,
        method: str,
        path: str,
        *,
        body_bytes: bytes | None = None,
        allow_absent: bool = False,
    ) -> dict[str, Any] | list[dict[str, Any]] | None:
        if (
            type(method) is not str
            or type(path) is not str
            or type(allow_absent) is not bool
        ):
            raise AuthorizationError("GitHub request types differ")
        if not path.startswith(_API_PREFIX):
            raise AuthorizationError("GitHub repository route differs")
        suffix = path[len(_API_PREFIX) :]
        lease_path = "/git/ref/heads/v12-consumption-v12.0.2"
        collection = bool(
            re.fullmatch(
                r"/commits/[0-9a-f]{40}/(?:pulls|check-runs)\?per_page=100", suffix
            )
            or re.fullmatch(r"/issues/[1-9][0-9]*/comments\?per_page=100", suffix)
        )
        get_allowed = (
            suffix
            in {
                "",
                "/branches/main/protection",
                "/git/ref/heads/main",
                lease_path,
                "/hash-algorithm",
            }
            or re.fullmatch(
                r"/(?:pulls|issues/comments|check-runs)/[1-9][0-9]*", suffix
            )
            is not None
            or re.fullmatch(r"/git/commits/[0-9a-f]{40}", suffix) is not None
            or collection
        )
        if not (
            (method == "GET" and get_allowed and body_bytes is None)
            or (
                method == "POST"
                and suffix in {"/git/commits", "/git/refs"}
                and type(body_bytes) is bytes
            )
        ) or (allow_absent and (method != "GET" or suffix != lease_path)):
            raise AuthorizationError("GitHub capability does not permit this request")
        if method == "POST":
            try:
                request = _transport_json(body_bytes)
                if _canonical(request) != body_bytes:
                    raise AuthorizationError("GitHub POST bytes are not canonical")
                if suffix == "/git/commits":
                    _lease_request_parts(request)
                else:
                    request = _closed_object(request, {"ref", "sha"})
                    _exact_string(request["ref"], LEASE_REF)
                    _oid(request["sha"])
            except TransportError:
                raise AuthorizationError("GitHub POST bytes are malformed") from None
        with _CAPABILITY_LOCK:
            if self._terminal or self._request_active:
                raise AuthorizationError("GitHub transport cannot be reused")
            if method == "POST":
                if suffix == "/git/commits":
                    if self._commit_post_attempted:
                        raise AuthorizationError(
                            "commit POST already attempted; no retry"
                        )
                    self._commit_post_attempted = True
                else:
                    if self._create_ref_attempted:
                        raise AuthorizationError(
                            "createRef already attempted; no retry"
                        )
                    self._create_ref_attempted = True
            self._request_active = True
            self._last_status = None
        url = _API_ORIGIN + path
        try:
            kwargs: dict[str, Any] = {
                "allow_redirects": False,
                "stream": True,
                "timeout": (10, 30),
                "proxies": {},
            }
            if body_bytes is not None:
                kwargs["data"] = body_bytes
            with self._session.request(method, url, **kwargs) as response:
                status = response.status_code
                if type(status) is not int or not 100 <= status <= 599:
                    raise TransportError("malformed_response")
                self._last_status = status
                if response.url != url:
                    raise TransportError("identity_mismatch", status)
                expected_status = 201 if method == "POST" else 200
                absent = status == 404 and allow_absent
                if status != expected_status and not absent:
                    raise TransportError("http_rejected", status)
                encoding = response.headers.get("Content-Encoding", "identity")
                content_type = response.headers.get("Content-Type", "")
                if (
                    type(encoding) is not str
                    or encoding.lower() != "identity"
                    or type(content_type) is not str
                    or content_type.split(";", 1)[0].lower() != "application/json"
                    or (collection and response.headers.get("Link", "") != "")
                ):
                    raise TransportError("malformed_response", status)
                chunks: list[bytes] = []
                length = 0
                for chunk in response.iter_content(65536):
                    if type(chunk) is not bytes:
                        raise TransportError("malformed_response", status)
                    length += len(chunk)
                    if length > 2 * 1024 * 1024:
                        raise TransportError("malformed_response", status)
                    chunks.append(chunk)
                try:
                    result = _transport_json(b"".join(chunks))
                except TransportError:
                    raise TransportError("malformed_response", status) from None
                if absent:
                    try:
                        absence = _closed_object(
                            result, {"message"}, {"documentation_url", "status"}
                        )
                        _exact_string(absence["message"], "Not Found")
                        if "status" in absence:
                            _exact_string(absence["status"], "404")
                        if (
                            "documentation_url" in absence
                            and type(absence["documentation_url"]) is not str
                        ):
                            raise AuthorizationError("malformed absence metadata")
                    except AuthorizationError:
                        raise TransportError("malformed_response", status) from None
                    return None
                if collection:
                    if suffix.endswith("/check-runs?per_page=100"):
                        if type(result) is not dict or set(result) != {
                            "total_count",
                            "check_runs",
                        }:
                            raise TransportError("malformed_response", status)
                        count, items = result["total_count"], result["check_runs"]
                        if (
                            type(count) is not int
                            or type(items) is not list
                            or count != len(items)
                        ):
                            raise TransportError("malformed_response", status)
                    else:
                        items = result
                    if (
                        type(items) is not list
                        or len(items) > 100
                        or any(type(item) is not dict for item in items)
                    ):
                        raise TransportError("malformed_response", status)
                elif type(result) is not dict:
                    raise TransportError("malformed_response", status)
                return result
        except TransportError:
            self._terminal = True
            raise
        except Exception:  # noqa: BLE001 -- arbitrary transport text can contain credentials.
            self._terminal = True
            raise TransportError("transport_failed", self._last_status) from None
        finally:
            with _CAPABILITY_LOCK:
                self._request_active = False


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
    if not git.ancestor(R1, R3) or not git.ancestor(R3, head):
        raise AuthorizationError("registration ancestry differs")
    added = git.text(
        "log",
        "--full-history",
        "--no-renames",
        "--reverse",
        "--format=%H",
        "--diff-filter=A",
        _oid(head),
        "--",
        R3_PATH,
    ).splitlines()
    parents = git.parents(R3)
    if (
        added != [R3]
        or len(parents) != 1
        or ("A", R3_PATH) not in git.changes(parents[0], R3)
    ):
        raise AuthorizationError("registration adding authority is ambiguous")
    r3_raw = git.read_blob(R3, R3_PATH)
    if (
        _sha(r3_raw)
        != "34088616fb9a2666bcc6acc7944cce44946e880594d1517cbe7fec554995fef0"
        or git.read_blob(head, R3_PATH) != r3_raw
    ):
        raise AuthorizationError("R3 registration blob drift")
    r3 = _json(r3_raw)
    r1_raw = git.read_blob(R1, R1_PATH)
    if (
        _sha(r1_raw)
        != "4406bd25ee82195bff7a97b258885cb3bb3c1a8fb829f383c5e3c1616e169170"
    ):
        raise AuthorizationError("scientific registration differs")
    r1 = _json(r1_raw)
    for path, identity in r3["registered_files"].items():
        raw = git.read_blob(R3, path)
        if len(raw) != identity["bytes"] or _sha(raw) != identity["sha256"]:
            raise AuthorizationError("R3 authority seal differs")
    authority_paths = set(git.text("ls-tree", "-r", "--name-only", R3).splitlines())
    assertions = r3["r3_git_authority"]["tree_assertions"]
    if authority_paths.intersection(assertions["absent_paths"]):
        raise AuthorizationError("R3 contains implementation or execution authority")
    if _sha(git.read_blob(R3, "config.yaml")) != assertions["config_yaml_sha256"]:
        raise AuthorizationError("registration-time config differs")
    for path, identity in r3["complete_R1_normative_sources"].items():
        raw = git.read_blob(R1, path)
        if (
            identity["authority_commit"] != R1
            or len(raw) != identity["bytes"]
            or _sha(raw) != identity["sha256"]
        ):
            raise AuthorizationError("complete scientific source differs")
    for path, identity in r3["legacy_byte_preservation"]["manifest"].items():
        for checkpoint in (r3["legacy_byte_preservation"]["base"], R3, head):
            raw = git.read_blob(checkpoint, path)
            if (
                git.oid(checkpoint, path) != identity["git_blob"]
                or len(raw) != identity["bytes"]
                or _sha(raw) != identity["sha256"]
            ):
                raise AuthorizationError("sealed legacy dependency changed")
    fingerprint = r3["statistical_equivalence"]["fingerprint_payload"]
    if (
        _sha(_canonical(fingerprint)) != FINGERPRINT
        or r3["statistical_equivalence"]["fingerprint_sha256"] != FINGERPRINT
    ):
        raise AuthorizationError("statistical fingerprint differs")
    for section, digest in fingerprint["contract_sections"].items():
        if _sha(_canonical(r1[section])) != digest:
            raise AuthorizationError("inherited statistical contract differs")
    if (
        r3["governed_history"]["authority_commit"] != HISTORY_AUTHORITY
        or git.text("cat-file", "-t", HISTORY_AUTHORITY) != "commit"
    ):
        raise AuthorizationError("fixed governed-history authority is absent")
    return r1, r3


def _implementation_manifest(git: GitRepository, commit: str) -> list[dict[str, Any]]:
    result = []
    for path in sorted(IMPLEMENTATION_PATHS):
        raw = git.read_blob(commit, path)
        result.append(
            {
                "path": path,
                "git_blob": git.oid(commit, path),
                "sha256": _sha(raw),
                "bytes": len(raw),
            }
        )
    return result


def _provenance_identifier(value: object) -> str:
    if (
        type(value) is not str
        or not value
        or len(value.encode("utf-8")) > 256
        or any(ord(c) < 32 or ord(c) == 127 for c in value)
        or value[0] in " \t\n\r\v\f"
        or value[-1] in " \t\n\r\v\f"
    ):
        raise AuthorizationError("source contributor identity is invalid")
    return value


def _source_author_provenance(raw_commit: bytes, phase: str) -> list[dict[str, str]]:
    if (
        type(raw_commit) is not bytes
        or phase not in {"I3", "A_H_s3"}
        or b"\n\n" not in raw_commit
    ):
        raise AuthorizationError("source author provenance is unavailable")
    _headers, message = raw_commit.split(b"\n\n", 1)
    marker = b"Research-Author-Provenance:"
    prefix = marker + b" "
    lines = message.split(b"\n")
    occurrences = [
        line for line in lines if line.lstrip(b" \t\r\v\f").startswith(marker)
    ]
    if (
        len(lines) < 2
        or lines[-1] != b""
        or not lines[-2].startswith(prefix)
        or occurrences != [lines[-2]]
        or b"\r" in lines[-2]
    ):
        raise AuthorizationError("source author trailer framing differs")
    raw = lines[-2][len(prefix) :]
    body = _json(raw)
    if (
        raw != _canonical(body)
        or set(body) != {"schema_version", "phase", "contributors"}
        or body["schema_version"] != "lotto649-v12-source-author-provenance-v1"
        or body["phase"] != phase
    ):
        raise AuthorizationError("source author trailer schema differs")
    contributors = body["contributors"]
    if type(contributors) is not list or not 1 <= len(contributors) <= 64:
        raise AuthorizationError("source contributors are missing or unbounded")
    pairs = []
    for contributor in contributors:
        if type(contributor) is not dict or set(contributor) != {
            "agent_id",
            "session_id",
        }:
            raise AuthorizationError("source contributor record schema differs")
        agent = _provenance_identifier(contributor["agent_id"])
        session = _provenance_identifier(contributor["session_id"])
        pairs.append((agent.encode("utf-8"), session.encode("utf-8")))
    if pairs != sorted(set(pairs)):
        raise AuthorizationError("source contributors are duplicated or unsorted")
    return contributors


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
    git: GitRepository,
    phase: str,
) -> None:
    contributors = _source_author_provenance(
        git.run("cat-file", "commit", _oid(implementation)), phase
    )
    record_keys = {
        "axis",
        "check_id",
        "comment_body_sha256",
        "comment_id",
        "pr_number",
        "publisher_login",
        "review_session_id",
        "reviewer_agent_id",
    }
    if type(records) not in {list, tuple} or any(
        type(r) is not dict or set(r) != record_keys for r in records
    ):
        raise AuthorizationError("closed review record schema differs")
    for record in records:
        agent = _provenance_identifier(record["reviewer_agent_id"])
        session = _provenance_identifier(record["review_session_id"])
        _provenance_identifier(record["publisher_login"])
        _digest(record["comment_body_sha256"])
        if agent in {c["agent_id"] for c in contributors} or session in {
            c["session_id"] for c in contributors
        }:
            raise AuthorizationError(
                "a source author cannot independently review that source"
            )
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
        or pr.get("head", {}).get("repo", {}).get("full_name") != REPOSITORY
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
            "schema_version": (
                "lotto649-v12-i3-independent-review-v1"
                if phase == "I3"
                else "lotto649-v12-ah3-independent-review-v1"
            ),
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
        if (
            type(attestation.get("blocker_count")) is not int
            or type(attestation.get("major_count")) is not int
        ):
            raise AuthorizationError("review counts must be integer zero")
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
    r1, r3 = _registered_authorities(git, base)
    parents = git.parents(merge)
    if len(parents) != 2 or parents[1] != implementation:
        raise AuthorizationError("implementation merge is not ordinary")
    implementation_base = parents[0]
    _require_normal_merge(git, merge, implementation_base, implementation)
    if (
        not git.ancestor(R3, implementation_base)
        or not git.ancestor(merge, base)
        or implementation == base
        or not git.ancestor(implementation, base)
    ):
        raise AuthorizationError("R3/I3/K_H3 order differs")
    if set(git.changes(implementation_base, implementation)) != {
        ("A", path) for path in IMPLEMENTATION_PATHS
    }:
        raise AuthorizationError("I3 must add exactly the six registered paths")
    closure = _core_and_closure(git, implementation)
    implementation_files = _implementation_manifest(git, implementation)
    if _implementation_manifest(git, base) != implementation_files:
        raise AuthorizationError("registered implementation files drifted")
    if _core_and_closure(git, base) != closure:
        raise AuthorizationError("historical closure drift after I3")
    _remote_protection(api)
    if _remote_main(api) != base:
        raise AuthorizationError("K_H3 is not current protected remote main")
    _verify_reviews(
        api,
        review_records,
        implementation=implementation,
        merge=merge,
        base=implementation_base,
        closure_sha256=_sha(_canonical(closure)),
        git=git,
        phase="I3",
    )
    return {
        "schema_version": "lotto649-v12.0.2-historical-authorization-v1",
        "experiment_id": r3["experiment_id"],
        "model_version": "v12.0.2",
        "repository": REPOSITORY,
        "branch": "main",
        "registration_commit": R3,
        "registration_sha256": _sha(git.read_blob(R3, R3_PATH)),
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
        "implementation_files": implementation_files,
        "implementation_files_sha256": _sha(_canonical(implementation_files)),
        "runtime_dependency_closure": closure,
        "runtime_dependency_closure_sha256": _sha(_canonical(closure)),
        "review_records": [dict(record) for record in review_records],
    }


def _required_collection(api: FixedGitHubApi, path: str) -> list[dict[str, Any]]:
    result = api.request_json("GET", _API_PREFIX + path)
    if (
        type(result) is not list
        or len(result) > 100
        or any(type(item) is not dict for item in result)
    ):
        raise AuthorizationError("registered first-page collection is incomplete")
    return result


def _discover_authorization_reviews(
    api: FixedGitHubApi, *, source: str, base: str, merge: str, closure_sha256: str
) -> list[dict[str, Any]]:
    _oid(source)
    _oid(base)
    _oid(merge)
    _digest(closure_sha256)
    prs = _required_collection(api, f"/commits/{source}/pulls?per_page=100")
    matching = [
        pr
        for pr in prs
        if pr.get("head", {}).get("sha") == source
        and pr.get("base", {}).get("sha") == base
        and pr.get("base", {}).get("ref") == "main"
        and pr.get("head", {}).get("repo", {}).get("full_name") == REPOSITORY
        and pr.get("base", {}).get("repo", {}).get("full_name") == REPOSITORY
        and pr.get("merge_commit_sha") == merge
        and pr.get("state") == "closed"
        and pr.get("merged_at") is not None
    ]
    if len(matching) != 1:
        raise AuthorizationError("authorization PR discovery is ambiguous")
    pr_number = matching[0].get("number")
    if type(pr_number) is not int or pr_number <= 0:
        raise AuthorizationError("authorization PR identifier is invalid")
    comments = _required_collection(api, f"/issues/{pr_number}/comments?per_page=100")
    checks = _required_response(api, f"/commits/{source}/check-runs?per_page=100")
    if (
        type(checks.get("total_count")) is not int
        or not 0 <= checks["total_count"] <= 100
        or type(checks.get("check_runs")) is not list
        or len(checks["check_runs"]) != checks["total_count"]
        or any(type(check) is not dict for check in checks["check_runs"])
    ):
        raise AuthorizationError("authorization CI collection is incomplete")
    candidates = [
        check for check in checks["check_runs"] if check.get("name") == "test"
    ]
    if (
        len(candidates) != 1
        or type(candidates[0].get("id")) is not int
        or candidates[0]["id"] <= 0
    ):
        raise AuthorizationError("authorization test check is ambiguous")
    records = []
    for comment in comments:
        body_text = comment.get("body")
        if type(body_text) is not str:
            raise AuthorizationError("authorization comment body type differs")
        try:
            body = _json(body_text.encode("utf-8"))
        except (AuthorizationError, UnicodeError):
            # Ordinary conversational comments provide no attestation.
            continue
        if (
            body.get("schema_version") != "lotto649-v12-ah3-independent-review-v1"
            or body.get("head_sha") != source
            or body.get("base_sha") != base
            or body.get("closure_sha256") != closure_sha256
        ):
            continue
        records.append(
            {
                "axis": body.get("axis"),
                "check_id": candidates[0]["id"],
                "comment_body_sha256": _sha(body_text.encode("utf-8")),
                "comment_id": comment.get("id"),
                "pr_number": pr_number,
                "publisher_login": comment.get("user", {}).get("login"),
                "review_session_id": body.get("review_session_id"),
                "reviewer_agent_id": body.get("reviewer_agent_id"),
            }
        )
    if len(records) != 2 or {record["axis"] for record in records} != {
        "standards",
        "spec",
    }:
        raise AuthorizationError("authorization review discovery is ambiguous")
    return sorted(records, key=lambda record: record["axis"])


@dataclass(frozen=True, init=False)
class VerifiedAuthorizationFacts:
    """Integrity-bound read-only facts; cannot lease, claim or expose history."""

    repository: Path
    execution_commit: str
    source_commit: str
    payload: dict[str, Any]
    authorization_sha256: str
    authorization_review_records: list[dict[str, Any]]

    def __new__(cls, *args: Any, **kwargs: Any) -> Any:
        raise AuthorizationError(
            "verified facts are issued only by read-only validation"
        )


_VERIFIED_FACTS: list[tuple[Any, bytes]] = []
_STARTED_FACTS: list[Any] = []


def _facts_preimage(facts: VerifiedAuthorizationFacts) -> dict[str, Any]:
    return {
        "repository": str(facts.repository),
        "execution_commit": facts.execution_commit,
        "source_commit": facts.source_commit,
        "payload": facts.payload,
        "authorization_sha256": facts.authorization_sha256,
        "authorization_review_records": facts.authorization_review_records,
    }


def _issue_verified_facts(
    repository: Path,
    execution: str,
    source: str,
    payload: dict[str, Any],
    digest: str,
    reviews: list[dict[str, Any]],
) -> VerifiedAuthorizationFacts:
    facts = object.__new__(VerifiedAuthorizationFacts)
    for name, value in (
        ("repository", repository),
        ("execution_commit", execution),
        ("source_commit", source),
        ("payload", payload),
        ("authorization_sha256", digest),
        ("authorization_review_records", reviews),
    ):
        object.__setattr__(facts, name, value)
    with _CAPABILITY_LOCK:
        _VERIFIED_FACTS.append((facts, _canonical(_facts_preimage(facts))))
    return facts


def _require_verified_facts(facts: VerifiedAuthorizationFacts) -> dict[str, Any]:
    with _CAPABILITY_LOCK:
        matches = [raw for issued, raw in _VERIFIED_FACTS if issued is facts]
        if len(matches) != 1 or _canonical(_facts_preimage(facts)) != matches[0]:
            raise AuthorizationError(
                "unissued or altered read-only authorization facts"
            )
    identity = {
        "execution_authority_M_A_H3": facts.execution_commit,
        "registration_R3": R3,
        "source_A_H_s3": facts.source_commit,
        "implementation_commit": facts.payload["implementation_commit"],
        "authorization_base": facts.payload["authorization_base"],
        "registration_sha256": facts.payload["registration_sha256"],
        "config_sha256": _sha(
            GitRepository(facts.repository).read_blob(R3, CONFIG_PATH)
        ),
        "authorization_sha256": facts.authorization_sha256,
        "historical_runtime_dependency_closure_sha256": facts.payload[
            "runtime_dependency_closure_sha256"
        ],
        "runtime_identity_sha256": _sha(_canonical(facts.payload["runtime"])),
        "requirements_sha256": REQUIREMENTS_SHA256,
        "required_pure_core_sha256": CORE_SHA256,
        "statistical_fingerprint_sha256": FINGERPRINT,
        "verified_facts_sha256": _sha(matches[0]),
    }
    return {
        "repository": facts.repository,
        "head": facts.execution_commit,
        "startup_identity": identity,
    }


@dataclass(frozen=True, init=False)
class VerifiedAuthorization:
    repository: Path
    execution_commit: str
    source_commit: str
    payload: dict[str, Any]
    authorization_sha256: str
    facts: VerifiedAuthorizationFacts
    startup: StartupJournal

    def __new__(cls, *args: Any, **kwargs: Any) -> Any:
        raise AuthorizationError(
            "execution authority requires durable authorized startup"
        )


def _issue_authorization(
    facts: VerifiedAuthorizationFacts, startup: StartupJournal
) -> VerifiedAuthorization:
    verified = _require_verified_facts(facts)
    startup.verify_owned()
    if startup.verified_identity != verified["startup_identity"]:
        raise AuthorizationError("startup does not bind these verified facts")
    authority = object.__new__(VerifiedAuthorization)
    for name, value in (
        ("repository", facts.repository),
        ("execution_commit", facts.execution_commit),
        ("source_commit", facts.source_commit),
        ("payload", facts.payload),
        ("authorization_sha256", facts.authorization_sha256),
        ("facts", facts),
        ("startup", startup),
    ):
        object.__setattr__(authority, name, value)
    with _CAPABILITY_LOCK:
        _ISSUED_AUTHORITIES.append((authority, _authorization_stamp(authority)))
    return authority


def _authorization_stamp(authority: VerifiedAuthorization) -> bytes:
    return _canonical(
        {
            "verified_facts": _facts_preimage(authority.facts),
            "repository": str(authority.repository),
            "execution_commit": authority.execution_commit,
            "source_commit": authority.source_commit,
            "payload": authority.payload,
            "authorization_sha256": authority.authorization_sha256,
            "startup_initial_identity": authority.startup.initial_identity,
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
    authority.startup.verify_owned()


def begin_authorized_startup(
    facts: VerifiedAuthorizationFacts,
) -> VerifiedAuthorization:
    _require_verified_facts(facts)
    with _CAPABILITY_LOCK:
        if any(used is facts for used in _STARTED_FACTS):
            raise AttemptError("authorized startup was already attempted; no retry")
        _STARTED_FACTS.append(facts)
    git = GitRepository(facts.repository)
    git.require_full_clean()
    if git.head() != facts.execution_commit:
        raise AuthorizationError("verified authorization HEAD moved")
    _verify_worktree_runtime(
        git, facts.execution_commit, facts.payload["runtime_dependency_closure"]
    )
    _require_fresh_outputs(_paths(facts.repository / "reports", synthetic=False))
    startup = StartupJournal._from_verified_facts(facts)
    authority = _issue_authorization(facts, startup)
    startup.append("capability_issued", {})
    OwnedArtifacts(authority)
    return authority


def verify_authorization(
    repository: Path, *, api: FixedGitHubApi
) -> VerifiedAuthorizationFacts:
    git = GitRepository(repository)
    git.require_full_clean()
    _require_fresh_outputs(_paths(repository / "reports", synthetic=False))
    head = git.head()
    r1, r3 = _registered_authorities(git, head)
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
        "implementation_files",
        "implementation_files_sha256",
        "runtime_dependency_closure",
        "runtime_dependency_closure_sha256",
        "review_records",
    }
    if set(authorization) != expected_keys:
        raise AuthorizationError("authorization schema differs")
    required = {
        "schema_version": "lotto649-v12.0.2-historical-authorization-v1",
        "experiment_id": r3["experiment_id"],
        "model_version": "v12.0.2",
        "repository": REPOSITORY,
        "branch": "main",
        "registration_commit": R3,
        "scientific_registration_commit": R1,
        "registration_sha256": _sha(git.read_blob(R3, R3_PATH)),
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
            "authorization source must be an auth-only child of K_H3"
        )
    _require_normal_merge(
        git, implementation_merge, implementation_base, implementation
    )
    if (
        set(git.changes(implementation_base, implementation))
        != {("A", path) for path in IMPLEMENTATION_PATHS}
        or not git.ancestor(R3, implementation_base)
        or not git.ancestor(implementation_merge, base)
        or implementation == base
    ):
        raise AuthorizationError("complete registered I3 ancestry is required")
    closure = authorization["runtime_dependency_closure"]
    if _sha(_canonical(closure)) != authorization["runtime_dependency_closure_sha256"]:
        raise AuthorizationError("authorization runtime closure hash differs")
    implementation_files = authorization["implementation_files"]
    if (
        _sha(_canonical(implementation_files))
        != authorization["implementation_files_sha256"]
    ):
        raise AuthorizationError("implementation file manifest digest differs")
    for checkpoint in (implementation, base, source, head):
        _registered_authorities(git, checkpoint)
        if _implementation_manifest(git, checkpoint) != implementation_files:
            raise AuthorizationError(
                "registered implementation files changed at checkpoint"
            )
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
        git=git,
        phase="I3",
    )
    auth_reviews = _discover_authorization_reviews(
        api,
        source=source,
        base=base,
        merge=head,
        closure_sha256=authorization["runtime_dependency_closure_sha256"],
    )
    _verify_reviews(
        api,
        auth_reviews,
        implementation=source,
        merge=head,
        base=base,
        closure_sha256=authorization["runtime_dependency_closure_sha256"],
        git=git,
        phase="A_H_s3",
    )
    _verify_worktree_runtime(git, head, closure)
    return _issue_verified_facts(
        repository, head, source, authorization, _sha(raw), auth_reviews
    )


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


# This fragment requires the existing static imports plus `import stat`.
# It introduces no dynamic import, reflection-based access, or output fallback.

_STARTUP_SCHEMA = "lotto649-v12.0.2-historical-startup-v1"
_STARTUP_PHASES = (
    "authorized_startup_started",
    "capability_issued",
    "lease_absence_confirmed",
    "lease_commit_POST_intent",
    "lease_commit_POST_receipt",
    "lease_commit_GET_verified",
    "lease_ref_POST_intent",
    "lease_ref_POST_receipt",
    "lease_ref_reread_verified",
    "startup_checkpoint",
    "claim_created",
    "scientific_ledger_started",
    "history_load_intent",
)
_STARTUP_RESULTS = frozenset(
    {
        "success",
        "http_rejected",
        "transport_failed",
        "malformed_response",
        "identity_mismatch",
        "io_failed",
        "authority_failed",
    }
)
_STARTUP_OID_FIELDS = frozenset(
    {
        "execution_authority_M_A_H3",
        "registration_R3",
        "source_A_H_s3",
        "implementation_commit",
        "authorization_base",
    }
)
_STARTUP_DIGEST_FIELDS = frozenset(
    {
        "registration_sha256",
        "config_sha256",
        "authorization_sha256",
        "historical_runtime_dependency_closure_sha256",
        "runtime_identity_sha256",
        "requirements_sha256",
        "required_pure_core_sha256",
        "statistical_fingerprint_sha256",
        "verified_facts_sha256",
    }
)
_STARTUP_PUBLIC_APPEND = frozenset(
    {
        "capability_issued",
        "lease_absence_confirmed",
        "lease_commit_GET_verified",
        "lease_ref_reread_verified",
        "claim_created",
        "scientific_ledger_started",
        "history_load_intent",
    }
)
_STARTUP_JOURNALS: dict[object, dict[str, Any]] = {}


@dataclass(frozen=True)
class StartupCheckpoint:
    path: str
    sequence: int
    head_sha256: str
    prefix_byte_count: int
    prefix_sha256: str

    def as_dict(self) -> dict[str, Any]:
        if (
            self.path
            not in {"reports/" + _ARTIFACT_NAMES["startup"], "synthetic-startup.jsonl"}
            or type(self.sequence) is not int
            or self.sequence != 9
            or type(self.prefix_byte_count) is not int
            or self.prefix_byte_count <= 0
        ):
            raise AttemptError("startup_checkpoint_invalid")
        return {
            "path": self.path,
            "sequence": self.sequence,
            "head_sha256": _digest(self.head_sha256),
            "prefix_byte_count": self.prefix_byte_count,
            "prefix_sha256": _digest(self.prefix_sha256),
        }


def _startup_state(journal: object) -> dict[str, Any]:
    if type(journal) is not StartupJournal or journal not in _STARTUP_JOURNALS:
        raise AttemptError("startup_unissued")
    return _STARTUP_JOURNALS[journal]


def _startup_fail(state: dict[str, Any], code: str) -> None:
    state["poisoned"] = True
    raise AttemptError(code)


def _startup_directory_chain(
    directory: Path,
) -> tuple[int, tuple[tuple[Path, int, int], ...]]:
    """Open each absolute directory component without following any symlink."""
    if not directory.is_absolute() or ".." in directory.parts:
        raise AttemptError("startup_unsafe_directory")
    descriptor = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    records: list[tuple[Path, int, int]] = []
    current = Path("/")
    try:
        root_stat = os.fstat(descriptor)
        records.append((current, root_stat.st_dev, root_stat.st_ino))
        for component in directory.parts[1:]:
            next_descriptor = os.open(
                component,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                dir_fd=descriptor,
            )
            os.close(descriptor)
            descriptor = next_descriptor
            current = current / component
            observed = os.fstat(descriptor)
            if not stat.S_ISDIR(observed.st_mode) or (
                observed.st_mode & 0o022 and not observed.st_mode & stat.S_ISVTX
            ):
                raise AttemptError("startup_unsafe_directory")
            records.append((current, observed.st_dev, observed.st_ino))
        return descriptor, tuple(records)
    except BaseException:
        os.close(descriptor)
        raise


def _startup_verify_owned(state: dict[str, Any]) -> None:
    if state["closed"] or state["poisoned"]:
        _startup_fail(state, "startup_unavailable")
    try:
        for path, device, inode in state["ancestors"]:
            observed = path.lstat()
            if (
                not stat.S_ISDIR(observed.st_mode)
                or observed.st_dev != device
                or observed.st_ino != inode
                or (observed.st_mode & 0o022 and not observed.st_mode & stat.S_ISVTX)
            ):
                _startup_fail(state, "startup_directory_changed")
        parent = os.fstat(state["parent_fd"])
        if (parent.st_dev, parent.st_ino) != state["parent_identity"]:
            _startup_fail(state, "startup_parent_descriptor_changed")
        by_descriptor = os.fstat(state["fd"])
        by_name = os.stat(
            state["path"].name,
            dir_fd=state["parent_fd"],
            follow_symlinks=False,
        )
        for observed in (by_descriptor, by_name):
            if (
                not stat.S_ISREG(observed.st_mode)
                or observed.st_dev != state["device"]
                or observed.st_ino != state["inode"]
                or observed.st_nlink != 1
                or stat.S_IMODE(observed.st_mode) != 0o600
                or observed.st_size != len(state["raw"])
            ):
                _startup_fail(state, "startup_file_identity_changed")
        observed_raw = os.pread(state["fd"], len(state["raw"]) + 1, 0)
        if observed_raw != state["raw"] or _sha(observed_raw) != state["digest"]:
            _startup_fail(state, "startup_bytes_changed")
        if os.lseek(state["fd"], 0, os.SEEK_CUR) != len(state["raw"]):
            _startup_fail(state, "startup_descriptor_offset_changed")
    except BaseException:  # noqa: BLE001 -- preserve partial bytes on every interruption.
        state["poisoned"] = True
        raise AttemptError("startup_ownership_failed") from None


def _startup_payload(state: dict[str, Any], kind: str, payload: dict[str, Any]) -> None:
    if type(payload) is not dict or any(type(key) is not str for key in payload):
        _startup_fail(state, "startup_payload_invalid")
    if kind == "authorized_startup_started":
        if payload != state["first_payload"]:
            _startup_fail(state, "startup_identity_invalid")
    elif kind in {"capability_issued", "startup_checkpoint", "history_load_intent"}:
        if payload:
            _startup_fail(state, "startup_payload_invalid")
    elif kind == "lease_absence_confirmed":
        if (
            set(payload) != {"http_status"}
            or type(payload["http_status"]) is not int
            or payload["http_status"] != 404
        ):
            _startup_fail(state, "startup_absence_invalid")
    elif kind in {"lease_commit_GET_verified", "lease_ref_reread_verified"}:
        if (
            set(payload) != {"validated_oid"}
            or _oid(payload["validated_oid"]) != state["expected_oid"]
        ):
            _startup_fail(state, "startup_oid_invalid")
    elif kind in {"lease_commit_POST_intent", "lease_ref_POST_intent"}:
        if set(payload) != {
            "phase_enum",
            "nonce_hex",
            "expected_lease_oid",
            "raw_commit_sha256",
            "request_body_bytes",
            "request_body_sha256",
        }:
            _startup_fail(state, "startup_intent_invalid")
        phase = "lease_commit" if kind == "lease_commit_POST_intent" else "lease_ref"
        if (
            payload["phase_enum"] != phase
            or _digest(payload["nonce_hex"]) != state["nonce"]
            or _oid(payload["expected_lease_oid"]) != state["expected_oid"]
            or _digest(payload["raw_commit_sha256"]) != state["raw_commit_sha256"]
            or type(payload["request_body_bytes"]) is not int
            or payload["request_body_bytes"] <= 0
        ):
            _startup_fail(state, "startup_intent_invalid")
        _digest(payload["request_body_sha256"])
    elif kind in {"lease_commit_POST_receipt", "lease_ref_POST_receipt"}:
        if set(payload) != {
            "phase_enum",
            "result_enum",
            "http_status",
            "validated_oid",
        }:
            _startup_fail(state, "startup_receipt_invalid")
        phase = "lease_commit" if kind == "lease_commit_POST_receipt" else "lease_ref"
        status, result, oid = (
            payload["http_status"],
            payload["result_enum"],
            payload["validated_oid"],
        )
        if (
            payload["phase_enum"] != phase
            or type(result) is not str
            or result not in _STARTUP_RESULTS
            or (
                status is not None
                and (type(status) is not int or not 100 <= status <= 599)
            )
            or (oid is not None and _oid(oid) != state["expected_oid"])
            or (result == "success" and (status != 201 or oid != state["expected_oid"]))
        ):
            _startup_fail(state, "startup_receipt_invalid")
    elif kind == "claim_created":
        if set(payload) != {"claim_sha256"}:
            _startup_fail(state, "startup_claim_invalid")
        _digest(payload["claim_sha256"])
    elif kind == "scientific_ledger_started":
        if set(payload) != {"first_event_sha256"}:
            _startup_fail(state, "startup_scientific_ledger_invalid")
        _digest(payload["first_event_sha256"])
    else:
        _startup_fail(state, "startup_phase_invalid")


def _startup_append(journal: object, kind: str, payload: dict[str, Any]) -> str:
    state = _startup_state(journal)
    try:
        _startup_verify_owned(state)
        if (
            state["sealed"]
            or type(kind) is not str
            or state["sequence"] >= len(_STARTUP_PHASES)
            or kind != _STARTUP_PHASES[state["sequence"]]
        ):
            _startup_fail(state, "startup_phase_invalid")
        _startup_payload(state, kind, payload)
        timestamp = _utc_now()
        if (
            type(timestamp) is not str
            or re.fullmatch(
                r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?Z",
                timestamp,
            )
            is None
        ):
            _startup_fail(state, "startup_clock_invalid")
        datetime.fromisoformat(timestamp)
        event = {
            "schema_version": _STARTUP_SCHEMA,
            "sequence": state["sequence"],
            "generated_at": timestamp,
            "previous_event_sha256": state["head"],
            "kind": kind,
            "payload": payload,
        }
        raw = _canonical(event) + b"\n"
        if os.write(state["fd"], raw) != len(raw):
            _startup_fail(state, "startup_short_write")
        os.fsync(state["fd"])
        state["raw"] += raw
        state["digest"] = _sha(state["raw"])
        state["head"] = _sha(raw)
        state["sequence"] += 1
        _startup_verify_owned(state)
        return state["head"]
    except BaseException:  # noqa: BLE001 -- preserve partial bytes on every interruption.
        state["poisoned"] = True
        raise AttemptError("startup_append_failed") from None


class StartupJournal:
    """Exclusive current-process startup receipt writer; never a resume handle."""

    __slots__ = ()

    def __new__(cls, *args: Any, **kwargs: Any) -> Any:
        raise AttemptError("startup_requires_verified_or_synthetic_factory")

    @classmethod
    def _create(
        cls,
        directory: Path,
        head: str,
        identity: dict[str, Any],
        *,
        synthetic: bool,
        verified_facts: object = None,
    ) -> StartupJournal:
        if cls is not StartupJournal:
            raise AttemptError("startup_subclass_forbidden")
        if synthetic:
            if (
                identity != {"synthetic_fixture_only": True}
                or head != "0" * 40
                or any(
                    (parent / ".git").exists() or (parent / ".git").is_symlink()
                    for parent in (directory, *directory.parents)
                )
            ):
                raise AttemptError("startup_synthetic_identity_invalid")
        else:
            checked = _require_verified_facts(verified_facts)
            if checked != {
                "repository": directory,
                "head": head,
                "startup_identity": identity,
            }:
                raise AuthorizationError("startup_unverified_creation")
        parent_fd = -1
        descriptor = -1
        state: dict[str, Any] | None = None
        try:
            relative_path = (
                "synthetic-startup.jsonl"
                if synthetic
                else "reports/" + _ARTIFACT_NAMES["startup"]
            )
            path = directory / relative_path
            parent_fd, ancestors = _startup_directory_chain(path.parent)
            if not synthetic:
                for name in _ARTIFACT_NAMES.values():
                    candidate = directory / "reports" / name
                    if candidate.exists() or candidate.is_symlink():
                        raise AttemptError("startup_reserved_output_exists")
            descriptor = os.open(
                path.name,
                os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600,
                dir_fd=parent_fd,
            )
            observed = os.fstat(descriptor)
            parent = os.fstat(parent_fd)
            first_payload = {
                "repository": "synthetic_fixture_only"
                if synthetic
                else "Jasper-Shi/lottopred",
                "branch": "synthetic_fixture_only" if synthetic else "main",
                "startup_identity": identity,
            }
            state = {
                "repository": directory,
                "execution_head": head,
                "path": path,
                "relative_path": relative_path,
                "fd": descriptor,
                "parent_fd": parent_fd,
                "ancestors": ancestors,
                "parent_identity": (parent.st_dev, parent.st_ino),
                "device": observed.st_dev,
                "inode": observed.st_ino,
                "raw": b"",
                "digest": _sha(b""),
                "head": None,
                "sequence": 0,
                "first_payload": first_payload,
                "first_head": None,
                "checkpoint": None,
                "nonce": None,
                "expected_oid": None,
                "raw_commit_sha256": None,
                "sealed": False,
                "poisoned": False,
                "closed": False,
            }
            journal = object.__new__(cls)
            _STARTUP_JOURNALS[journal] = state
            state["first_head"] = _startup_append(
                journal, "authorized_startup_started", first_payload
            )
            os.fsync(parent_fd)
            _startup_verify_owned(state)
            return journal
        except BaseException:  # noqa: BLE001 -- never resume partially created startup.
            if state is not None:
                state["poisoned"] = True
                state["closed"] = True
            if descriptor >= 0:
                os.close(descriptor)
            if parent_fd >= 0:
                os.close(parent_fd)
            raise AttemptError("startup_creation_failed") from None

    @classmethod
    def _from_verified_facts(cls, facts: object) -> StartupJournal:
        # Root's inert-facts registry rejects fabricated/stale facts before I/O.
        verified = _require_verified_facts(facts)
        if type(verified) is not dict or set(verified) != {
            "repository",
            "head",
            "startup_identity",
        }:
            raise AuthorizationError("startup_verified_facts_invalid")
        root, head, identity = (
            verified["repository"],
            verified["head"],
            verified["startup_identity"],
        )
        if (
            not isinstance(root, Path)
            or not root.is_absolute()
            or type(identity) is not dict
            or set(identity) != _STARTUP_OID_FIELDS | _STARTUP_DIGEST_FIELDS
        ):
            raise AuthorizationError("startup_verified_facts_invalid")
        _oid(head)
        for field in _STARTUP_OID_FIELDS:
            _oid(identity[field])
        for field in _STARTUP_DIGEST_FIELDS:
            _digest(identity[field])
        if identity["execution_authority_M_A_H3"] != head:
            raise AuthorizationError("startup_verified_head_invalid")
        return cls._create(
            root, head, dict(identity), synthetic=False, verified_facts=facts
        )

    @classmethod
    def for_synthetic(cls, directory: Path, facts: dict[str, Any]) -> StartupJournal:
        if (
            type(facts) is not dict
            or set(facts) != {"synthetic_fixture_only"}
            or facts["synthetic_fixture_only"] is not True
        ):
            raise AttemptError("startup_synthetic_facts_invalid")
        root = directory.absolute()
        if root.name in {"reports", "predictions", "evaluations", "evidence"} or any(
            (parent / ".git").exists() or (parent / ".git").is_symlink()
            for parent in (root, *root.parents)
        ):
            raise AttemptError("startup_synthetic_repository_forbidden")
        descriptor, _ = _startup_directory_chain(root.parent)
        try:
            try:
                os.mkdir(root.name, 0o700, dir_fd=descriptor)
            except FileExistsError:
                pass
            if root.is_symlink() or not root.is_dir() or any(root.iterdir()):
                raise AttemptError("startup_synthetic_directory_not_empty")
        finally:
            os.close(descriptor)
        return cls._create(
            root, "0" * 40, {"synthetic_fixture_only": True}, synthetic=True
        )

    @property
    def path(self) -> Path:
        return _startup_state(self)["path"]

    @property
    def byte_count(self) -> int:
        return len(_startup_state(self)["raw"])

    @property
    def head_sha256(self) -> str:
        return _startup_state(self)["head"]

    @property
    def digest_sha256(self) -> str:
        return _startup_state(self)["digest"]

    @property
    def sealed(self) -> bool:
        return _startup_state(self)["sealed"]

    @property
    def verified_identity(self) -> dict[str, Any]:
        return dict(_startup_state(self)["first_payload"]["startup_identity"])

    @property
    def initial_identity(self) -> dict[str, Any]:
        state = _startup_state(self)
        return {
            "repository": str(state["repository"]),
            "head": state["execution_head"],
            "path": state["relative_path"],
            "device": state["device"],
            "inode": state["inode"],
            "fd": state["fd"],
            "parent_device": state["parent_identity"][0],
            "parent_inode": state["parent_identity"][1],
            "first_event_sha256": state["first_head"],
        }

    def append(self, kind: str, payload: dict[str, Any]) -> str:
        state = _startup_state(self)
        if type(kind) is not str or kind not in _STARTUP_PUBLIC_APPEND:
            _startup_fail(state, "startup_public_phase_invalid")
        return _startup_append(self, kind, payload)

    def intent(
        self, phase: str, nonce: str, oid: str, raw_sha256: str, request_bytes: bytes
    ) -> str:
        state = _startup_state(self)
        try:
            if (
                phase not in {"lease_commit", "lease_ref"}
                or type(phase) is not str
                or type(request_bytes) is not bytes
                or not request_bytes
            ):
                _startup_fail(state, "startup_intent_invalid")
            _digest(nonce)
            _oid(oid)
            _digest(raw_sha256)
            if _canonical(_json(request_bytes)) != request_bytes:
                _startup_fail(state, "startup_request_not_canonical")
            if phase == "lease_commit" and state["sequence"] == 3:
                state["nonce"], state["expected_oid"], state["raw_commit_sha256"] = (
                    nonce,
                    oid,
                    raw_sha256,
                )
            if (nonce, oid, raw_sha256) != (
                state["nonce"],
                state["expected_oid"],
                state["raw_commit_sha256"],
            ):
                _startup_fail(state, "startup_intent_identity_changed")
            return _startup_append(
                self,
                phase + "_POST_intent",
                {
                    "phase_enum": phase,
                    "nonce_hex": nonce,
                    "expected_lease_oid": oid,
                    "raw_commit_sha256": raw_sha256,
                    "request_body_bytes": len(request_bytes),
                    "request_body_sha256": _sha(request_bytes),
                },
            )
        except BaseException:  # noqa: BLE001 -- preserve partial bytes on every interruption.
            state["poisoned"] = True
            raise AttemptError("startup_intent_failed") from None

    def receipt(
        self, phase: str, result: str, http_status: int | None, oid: str | None = None
    ) -> str:
        state = _startup_state(self)
        try:
            if type(phase) is not str or phase not in {"lease_commit", "lease_ref"}:
                _startup_fail(state, "startup_receipt_invalid")
            head = _startup_append(
                self,
                phase + "_POST_receipt",
                {
                    "phase_enum": phase,
                    "result_enum": result,
                    "http_status": http_status,
                    "validated_oid": oid,
                },
            )
            if result != "success":
                _startup_fail(state, "startup_receipt_terminal_failure")
            return head
        except BaseException:  # noqa: BLE001 -- preserve partial bytes on every interruption.
            state["poisoned"] = True
            raise AttemptError("startup_receipt_failed") from None

    def checkpoint(self) -> StartupCheckpoint:
        state = _startup_state(self)
        if state["checkpoint"] is not None:
            _startup_fail(state, "startup_checkpoint_repeated")
        head = _startup_append(self, "startup_checkpoint", {})
        checkpoint = StartupCheckpoint(
            state["relative_path"],
            state["sequence"] - 1,
            head,
            len(state["raw"]),
            state["digest"],
        )
        checkpoint.as_dict()
        state["checkpoint"] = checkpoint
        return checkpoint

    def seal(self) -> None:
        state = _startup_state(self)
        _startup_verify_owned(state)
        if (
            state["sealed"]
            or state["sequence"] != len(_STARTUP_PHASES)
            or state["checkpoint"] is None
        ):
            _startup_fail(state, "startup_seal_invalid")
        state["sealed"] = True

    def verify_owned(self) -> None:
        _startup_verify_owned(_startup_state(self))

    def close(self) -> None:
        state = _startup_state(self)
        if state["closed"]:
            return
        state["closed"] = True
        for descriptor, device, inode in (
            (state["fd"], state["device"], state["inode"]),
            (state["parent_fd"], *state["parent_identity"]),
        ):
            try:
                observed = os.fstat(descriptor)
            except OSError:
                state["poisoned"] = True
                continue
            if (observed.st_dev, observed.st_ino) != (device, inode):
                # Never close a foreign descriptor reusing the same integer.
                state["poisoned"] = True
                continue
            try:
                os.close(descriptor)
            except OSError:
                state["poisoned"] = True


def _post_lease_request(
    api: FixedGitHubApi,
    startup: StartupJournal,
    *,
    phase: str,
    nonce: str,
    oid: str,
    raw_sha256: str,
    request_bytes: bytes,
    commit_payload: Mapping[str, Any] | None = None,
) -> None:
    # The exact bytes below are both journaled and sent, with no reserialization.
    startup.intent(phase, nonce, oid, raw_sha256, request_bytes)
    suffix = "/git/commits" if phase == "lease_commit" else "/git/refs"
    try:
        response = api.request_json(
            "POST", _API_PREFIX + suffix, body_bytes=request_bytes
        )
    except TransportError as failure:
        startup.receipt(phase, failure.result_enum, failure.http_status)
        raise AttemptError("lease transport failed; no retry") from None
    except Exception:  # noqa: BLE001 -- authenticated exception text is never recorded.
        startup.receipt(phase, "transport_failed", None)
        raise AttemptError("lease outcome is uncertain; no retry") from None
    try:
        if phase == "lease_commit":
            if commit_payload is None:
                raise AuthorizationError("lease payload is unavailable")
            _verify_lease_post_response(response, oid, commit_payload)
        else:
            _verify_lease_ref(response, oid)
    except Exception:  # noqa: BLE001 -- authenticated exception text is never recorded.
        startup.receipt(phase, "identity_mismatch", api.last_status)
        raise AttemptError("lease response differs; no retry") from None
    startup.receipt(phase, "success", api.last_status, oid)


def acquire_historical_lease(
    authority: VerifiedAuthorization, api: FixedGitHubApi
) -> Lease:
    """One durable intent before each single POST; no uncertain state resumes."""
    _require_authorization_capability(authority, consume=True)
    git = GitRepository(authority.repository)
    git.require_full_clean(authority=authority)
    _remote_protection(api)
    if (
        _remote_main(api) != authority.execution_commit
        or git.head() != authority.execution_commit
    ):
        raise AuthorizationError("authority moved before lease")
    absence = api.request_json(
        "GET",
        _API_PREFIX + "/git/ref/heads/v12-consumption-v12.0.2",
        allow_absent=True,
    )
    if (
        absence is not None
        or type(api.last_status) is not int
        or api.last_status != 404
    ):
        raise AttemptError("the immutable attempt lease exists or absence is ambiguous")
    startup = authority.startup
    startup.append("lease_absence_confirmed", {"http_status": 404})
    nonce = secrets.token_hex(32)
    oid, raw, payload = _lease_commit(git, authority, nonce)
    _post_lease_request(
        api,
        startup,
        phase="lease_commit",
        nonce=nonce,
        oid=oid,
        raw_sha256=_sha(raw),
        request_bytes=_canonical(payload),
        commit_payload=payload,
    )
    observed = _required_response(api, "/git/commits/" + oid)
    _verify_lease_object(observed, oid, raw, payload)
    startup.append("lease_commit_GET_verified", {"validated_oid": oid})
    _post_lease_request(
        api,
        startup,
        phase="lease_ref",
        nonce=nonce,
        oid=oid,
        raw_sha256=_sha(raw),
        request_bytes=_canonical({"ref": LEASE_REF, "sha": oid}),
    )
    reread = _required_response(api, "/git/ref/heads/v12-consumption-v12.0.2")
    _verify_lease_ref(reread, oid)
    _remote_protection(api)
    if _remote_main(api) != authority.execution_commit:
        raise AttemptError("main moved after lease; no retry")
    git.require_full_clean(authority=authority)
    startup.append("lease_ref_reread_verified", {"validated_oid": oid})
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


# Authored by /root/i3_transport, session i3-artifact-ownership-authoring-20260913.
# Uses the registered startup fragment's _startup_directory_chain and import stat.

_ARTIFACT_OWNERS: dict[object, dict[str, Any]] = {}
_ARTIFACT_PUBLICATIONS = frozenset(
    {
        ("json_staging", "json"),
        ("markdown_staging", "markdown"),
        ("commit_staging", "commit"),
    }
)


def _artifact_owner_state(owner: object) -> dict[str, Any]:
    if type(owner) is not OwnedArtifacts or owner not in _ARTIFACT_OWNERS:
        raise AttemptError("artifact_owner_unissued")
    state = _ARTIFACT_OWNERS[owner]
    if state["poisoned"] or state["closed"]:
        raise AttemptError("artifact_owner_unavailable")
    return state


def _artifact_owner_context(state: dict[str, Any]) -> None:
    if state["synthetic"]:
        if any(
            os.path.lexists(parent / ".git")
            for parent in (state["root"], *state["root"].parents)
        ):
            raise AttemptError("artifact_synthetic_repository_refused")
    else:
        _require_authorization_capability(state["authority"])
        if (
            state["authority"].repository != state["root"]
            or state["authority"].execution_commit != state["head"]
            or GitRepository(state["root"]).head() != state["head"]
        ):
            raise AuthorizationError("artifact_authority_moved")
    for path, device, inode in state["ancestors"]:
        observed = path.lstat()
        if (
            not stat.S_ISDIR(observed.st_mode)
            or (observed.st_dev, observed.st_ino) != (device, inode)
            or (observed.st_mode & 0o022 and not observed.st_mode & stat.S_ISVTX)
        ):
            raise AttemptError("artifact_directory_identity_changed")
    parent = os.fstat(state["parent_fd"])
    if (parent.st_dev, parent.st_ino) != state["parent_identity"]:
        raise AttemptError("artifact_parent_descriptor_changed")


def _artifact_entry_stat(
    state: dict[str, Any], entry: dict[str, Any], *, links: int = 1
) -> None:
    path_stat = os.stat(
        entry["path"].name, dir_fd=state["parent_fd"], follow_symlinks=False
    )
    descriptor_stat = os.fstat(entry["fd"])
    observations = [path_stat, descriptor_stat]
    stream = entry["stream"]
    if stream is not None and not stream.closed:
        observations.append(os.fstat(stream.fileno()))
    for observed in observations:
        if (
            not stat.S_ISREG(observed.st_mode)
            or (observed.st_dev, observed.st_ino) != (entry["device"], entry["inode"])
            or observed.st_nlink != links
            or stat.S_IMODE(observed.st_mode) != 0o600
        ):
            raise AttemptError("artifact_file_identity_changed")


def _artifact_entry_bytes(
    state: dict[str, Any], entry: dict[str, Any], count: int, digest: str
) -> None:
    _artifact_entry_stat(state, entry)
    if os.fstat(entry["fd"]).st_size != count:
        raise AttemptError("artifact_length_changed")
    observed_hash = hashlib.sha256()
    offset = 0
    while offset < count:
        chunk = os.pread(entry["fd"], min(1024 * 1024, count - offset), offset)
        if not chunk:
            raise AttemptError("artifact_read_incomplete")
        observed_hash.update(chunk)
        offset += len(chunk)
    if os.pread(entry["fd"], 1, count) or observed_hash.hexdigest() != digest:
        raise AttemptError("artifact_bytes_changed")
    _artifact_entry_stat(state, entry)
    if os.fstat(entry["fd"]).st_size != count:
        raise AttemptError("artifact_length_changed")


def _artifact_verify_entries(
    state: dict[str, Any], *, skip_role: str | None = None
) -> None:
    if state["synthetic"]:
        owned_names = {entry["path"].name for entry in state["entries"].values()}
        if any(path.name not in owned_names for path in state["root"].iterdir()):
            raise AttemptError("artifact_synthetic_foreign_output")
    for role, entry in state["entries"].items():
        if role != skip_role:
            _artifact_entry_bytes(
                state, entry, entry["byte_count"], entry["hash"].hexdigest()
            )
    for role in state["retired"]:
        try:
            os.stat(
                state["paths"][role].name,
                dir_fd=state["parent_fd"],
                follow_symlinks=False,
            )
        except FileNotFoundError:
            continue
        raise AttemptError("artifact_retired_staging_reappeared")
    for role, path in state["paths"].items():
        if role in state["entries"] or role in state["retired"]:
            continue
        try:
            os.stat(path.name, dir_fd=state["parent_fd"], follow_symlinks=False)
        except FileNotFoundError:
            continue
        raise AttemptError("artifact_foreign_reserved_output")


def _artifact_begin(owner: object) -> dict[str, Any]:
    with _CAPABILITY_LOCK:
        state = _artifact_owner_state(owner)
        if state["busy"]:
            state["poisoned"] = True
            raise AttemptError("artifact_concurrent_operation_refused")
        state["busy"] = True
    try:
        _artifact_owner_context(state)
    except BaseException:
        state["poisoned"] = True
        state["busy"] = False
        raise
    return state


def _artifact_create_entry(state: dict[str, Any], role: str) -> dict[str, Any]:
    if (
        type(role) is not str
        or role not in state["paths"]
        or role in state["used_roles"]
    ):
        raise AttemptError("artifact_role_unregistered_or_used")
    state["used_roles"].add(role)
    path = state["paths"][role]
    descriptor = os.open(
        path.name,
        os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
        dir_fd=state["parent_fd"],
    )
    try:
        observed = os.fstat(descriptor)
        entry = {
            "role": role,
            "path": path,
            "device": observed.st_dev,
            "inode": observed.st_ino,
            "fd": descriptor,
            "stream": None,
            "stream_finished": False,
            "byte_count": 0,
            "hash": hashlib.sha256(),
        }
        state["entries"][role] = entry
        _artifact_entry_stat(state, entry)
        return entry
    except BaseException:
        if role not in state["entries"]:
            os.close(descriptor)
        raise


def _artifact_write_bytes(
    state: dict[str, Any], role: str, raw: bytes
) -> dict[str, Any]:
    if type(raw) is not bytes:
        raise AttemptError("artifact_bytes_required")
    entry = _artifact_create_entry(state, role)
    written = os.write(entry["fd"], raw)
    if type(written) is not int or written != len(raw):
        raise AttemptError("artifact_write_incomplete")
    os.fsync(entry["fd"])
    os.fsync(state["parent_fd"])
    _artifact_entry_bytes(state, entry, len(raw), _sha(raw))
    entry["hash"].update(raw)
    entry["byte_count"] = len(raw)
    return entry


class OwnedArtifacts:
    """Creation-only provenance; neither names nor existing bytes grant ownership."""

    __slots__ = ()

    def __init__(self, authority: VerifiedAuthorization) -> None:
        if type(self) is not OwnedArtifacts:
            raise AttemptError("artifact_owner_subclass_refused")
        _require_authorization_capability(authority)
        root = authority.repository
        head = authority.execution_commit
        if GitRepository(root).head() != head:
            raise AuthorizationError("artifact_authority_moved")
        with _CAPABILITY_LOCK:
            if self in _ARTIFACT_OWNERS or any(
                state["authority"] is authority for state in _ARTIFACT_OWNERS.values()
            ):
                raise AttemptError("artifact_owner_already_issued")
            paths = _paths(root / "reports", synthetic=False)
            paths.pop("startup")
            parent_fd, ancestors = _startup_directory_chain(root / "reports")
            try:
                if any(os.path.lexists(path) for path in paths.values()):
                    raise AttemptError("artifact_preexisting_reserved_output")
                parent = os.fstat(parent_fd)
                _ARTIFACT_OWNERS[self] = {
                    "authority": authority,
                    "root": root,
                    "head": head,
                    "synthetic": False,
                    "paths": paths,
                    "parent_fd": parent_fd,
                    "ancestors": ancestors,
                    "parent_identity": (parent.st_dev, parent.st_ino),
                    "entries": {},
                    "retired": {},
                    "used_roles": set(),
                    "poisoned": False,
                    "closed": False,
                    "busy": False,
                }
            except BaseException:
                os.close(parent_fd)
                raise

    @classmethod
    def for_synthetic(cls, directory: Path) -> OwnedArtifacts:
        if cls is not OwnedArtifacts:
            raise AttemptError("artifact_owner_subclass_refused")
        root = directory.absolute()
        if (
            root.name in {"reports", "predictions", "evaluations", "evidence"}
            or ".." in root.parts
            or any(os.path.lexists(parent / ".git") for parent in (root, *root.parents))
        ):
            raise AttemptError("artifact_synthetic_repository_refused")
        if not os.path.lexists(root):
            parent_fd, _ancestors = _startup_directory_chain(root.parent)
            try:
                os.mkdir(root.name, mode=0o700, dir_fd=parent_fd)
                os.fsync(parent_fd)
            finally:
                os.close(parent_fd)
        parent_fd, ancestors = _startup_directory_chain(root)
        try:
            if any(root.iterdir()):
                raise AttemptError("artifact_synthetic_directory_not_empty")
            parent = os.fstat(parent_fd)
            paths = _paths(root, synthetic=True)
            paths.pop("startup")
            owner = object.__new__(cls)
            with _CAPABILITY_LOCK:
                if any(state["root"] == root for state in _ARTIFACT_OWNERS.values()):
                    raise AttemptError("artifact_synthetic_owner_already_issued")
                _ARTIFACT_OWNERS[owner] = {
                    "authority": None,
                    "root": root,
                    "head": "0" * 40,
                    "synthetic": True,
                    "paths": paths,
                    "parent_fd": parent_fd,
                    "ancestors": ancestors,
                    "parent_identity": (parent.st_dev, parent.st_ino),
                    "entries": {},
                    "retired": {},
                    "used_roles": set(),
                    "poisoned": False,
                    "closed": False,
                    "busy": False,
                }
            return owner
        except BaseException:
            os.close(parent_fd)
            raise

    @property
    def paths(self) -> dict[str, Path]:
        if type(self) is not OwnedArtifacts or self not in _ARTIFACT_OWNERS:
            raise AttemptError("artifact_owner_unissued")
        # Static path metadata remains inspectable after a terminal failure.
        # It never grants an allowance; allowed_paths must verify live ownership.
        return dict(_ARTIFACT_OWNERS[self]["paths"])

    def create_bytes(self, role: str, raw: bytes) -> None:
        state = _artifact_begin(self)
        try:
            _artifact_verify_entries(state)
            _artifact_write_bytes(state, role, raw)
        except BaseException:
            state["poisoned"] = True
            raise
        finally:
            state["busy"] = False

    def create_stream(self, role: str) -> Any:
        state = _artifact_begin(self)
        try:
            if role != "ledger":
                raise AttemptError("artifact_only_ledger_may_stream")
            _artifact_verify_entries(state)
            entry = _artifact_create_entry(state, role)
            # Unbuffered writes mean terminal close cannot finish a pending line.
            stream = os.fdopen(os.dup(entry["fd"]), "wb", buffering=0)
            entry["stream"] = stream
            os.fsync(entry["fd"])
            os.fsync(state["parent_fd"])
            _artifact_entry_bytes(state, entry, 0, _sha(b""))
            return stream
        except BaseException:
            state["poisoned"] = True
            raise
        finally:
            state["busy"] = False

    def record_append(self, role: str, raw: bytes) -> None:
        state = _artifact_begin(self)
        try:
            if (
                type(role) is not str
                or role not in state["entries"]
                or type(raw) is not bytes
                or not raw
            ):
                raise AttemptError("artifact_append_unregistered")
            entry = state["entries"][role]
            stream = entry["stream"]
            if (
                role != "ledger"
                or stream is None
                or stream.closed
                or entry["stream_finished"]
            ):
                raise AttemptError("artifact_append_stream_unavailable")
            _artifact_verify_entries(state, skip_role=role)
            prospective = entry["hash"].copy()
            prospective.update(raw)
            count = entry["byte_count"] + len(raw)
            stream.flush()
            _artifact_entry_bytes(state, entry, count, prospective.hexdigest())
            os.fsync(entry["fd"])
            _artifact_entry_bytes(state, entry, count, prospective.hexdigest())
            # Only caller-supplied known bytes extend the expected state.
            entry["hash"] = prospective
            entry["byte_count"] = count
        except BaseException:
            state["poisoned"] = True
            raise
        finally:
            state["busy"] = False

    def close_stream(self, role: str) -> None:
        state = _artifact_begin(self)
        try:
            if type(role) is not str or role not in state["entries"]:
                raise AttemptError("artifact_stream_unregistered")
            entry = state["entries"][role]
            stream = entry["stream"]
            if stream is None:
                raise AttemptError("artifact_stream_unregistered")
            if not stream.closed:
                stream.flush()
            os.fsync(entry["fd"])
            _artifact_verify_entries(state)
            stream.close()
            entry["stream_finished"] = True
        except BaseException:
            state["poisoned"] = True
            raise
        finally:
            state["busy"] = False

    def publish(self, staging_role: str, final_role: str, raw: bytes) -> None:
        state = _artifact_begin(self)
        try:
            if (
                type(staging_role) is not str
                or type(final_role) is not str
                or (staging_role, final_role) not in _ARTIFACT_PUBLICATIONS
                or final_role in state["used_roles"]
            ):
                raise AttemptError("artifact_publication_unregistered_or_used")
            _artifact_verify_entries(state)
            entry = _artifact_write_bytes(state, staging_role, raw)
            state["used_roles"].add(final_role)
            destination = state["paths"][final_role]
            os.link(
                entry["path"].name,
                destination.name,
                src_dir_fd=state["parent_fd"],
                dst_dir_fd=state["parent_fd"],
                follow_symlinks=False,
            )
            # Preserve the actual intermediate publication state on every failure.
            state["retired"][staging_role] = {
                "stage": "linked",
                "final_role": final_role,
                "device": entry["device"],
                "inode": entry["inode"],
                "byte_count": entry["byte_count"],
                "sha256": entry["hash"].hexdigest(),
            }
            _artifact_entry_stat(state, entry, links=2)
            destination_stat = os.stat(
                destination.name, dir_fd=state["parent_fd"], follow_symlinks=False
            )
            if (destination_stat.st_dev, destination_stat.st_ino) != (
                entry["device"],
                entry["inode"],
            ):
                raise AttemptError("artifact_publication_identity_changed")
            os.fsync(state["parent_fd"])
            os.unlink(entry["path"].name, dir_fd=state["parent_fd"])
            state["retired"][staging_role]["stage"] = "staging_unlinked"
            entry["path"] = destination
            entry["role"] = final_role
            state["entries"][final_role] = entry
            del state["entries"][staging_role]
            os.fsync(state["parent_fd"])
            state["retired"][staging_role]["stage"] = "published"
            _artifact_verify_entries(state)
        except BaseException:
            state["poisoned"] = True
            raise
        finally:
            state["busy"] = False

    def verify_owned(self) -> None:
        state = _artifact_begin(self)
        try:
            _artifact_verify_entries(state)
        except BaseException:
            state["poisoned"] = True
            raise
        finally:
            state["busy"] = False

    def allowed_paths(self) -> set[str]:
        self.verify_owned()
        state = _artifact_owner_state(self)
        return {
            _relative(str(entry["path"].relative_to(state["root"])))
            for entry in state["entries"].values()
        }

    def close(self) -> None:
        """Close retained descriptors at final exit; never write or recover bytes."""
        if type(self) is not OwnedArtifacts or self not in _ARTIFACT_OWNERS:
            raise AttemptError("artifact_owner_unissued")
        state = _ARTIFACT_OWNERS[self]
        if state["closed"]:
            return
        state["closed"] = True
        closed_descriptors: set[int] = set()
        for entry in state["entries"].values():
            stream = entry["stream"]
            if stream is not None and not stream.closed:
                stream.close()
            if entry["fd"] not in closed_descriptors:
                os.close(entry["fd"])
                closed_descriptors.add(entry["fd"])
        os.close(state["parent_fd"])


def _owned_artifacts(authority: VerifiedAuthorization) -> OwnedArtifacts:
    _require_authorization_capability(authority)
    with _CAPABILITY_LOCK:
        matches = [
            owner
            for owner, state in _ARTIFACT_OWNERS.items()
            if state["authority"] is authority
        ]
    if len(matches) != 1:
        raise AttemptError("artifact_owner_missing_or_ambiguous")
    _artifact_owner_state(matches[0])
    return matches[0]


class DurableLedger:
    """One open exclusive descriptor, contiguous hash chain, fsync per event."""

    def __init__(
        self,
        path: Path,
        bindings: Mapping[str, Any],
        *,
        owner: OwnedArtifacts | None = None,
    ) -> None:
        self.path = path
        self._owner = owner
        self._bindings = json.loads(_canonical(dict(bindings)))
        self._sequence = 0
        self._head = "0" * 64
        self._closed = False
        if owner is None:
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            self._stream = os.fdopen(descriptor, "wb")
            _fsync_directory(path.parent)
        else:
            if owner.paths["ledger"] != path:
                raise AttemptError("ledger ownership path differs")
            self._stream = owner.create_stream("ledger")

    @property
    def head(self) -> str:
        return self._head

    def append(self, kind: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        if self._closed:
            raise AttemptError("closed ledger cannot append or retry")
        event = {
            "schema_version": "lotto649-v12.0.2-attempt-ledger-v1",
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
            raw = _canonical(event) + b"\n"
            if self._stream.write(raw) != len(raw):
                raise AttemptError("scientific ledger short write; no retry")
            self._stream.flush()
            os.fsync(self._stream.fileno())
            if self._owner is not None:
                self._owner.record_append("ledger", raw)
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
            if self._owner is None:
                self._stream.close()
            else:
                self._owner.close_stream("ledger")


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
    from .v12_0_2_evidence import (
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
            "schema_version": "lotto649-v12.0.2-frozen-forecast-v1",
            "classification": "synthetic_fixture_only"
            if synthetic
            else "consumed_historical_diagnostic_only",
            "model_version": "v12.0.2",
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
            body = f"分类：历史诊断/审计候选、不可晋升\n模型版本：v12.0.2\n历史目标日期：{target.isoformat()}\n训练截止：{history_through}\n事件：{category}\n预测摘要：{digest}\n仅为 consumed historical diagnostic，不是下一期预测或购票建议。\n"
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
    owner: OwnedArtifacts | None = None,
) -> dict[str, Any]:
    from .v12_0_2_evidence import build_report, canonical_json_bytes, render_markdown

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
    exact_rows = [row for row in rows if row.get("exact_final6_opportunities")]
    report["independent_leakage_audit"] = (
        "pending" if exact_rows else "not_required_no_exact_final6"
    )
    if exact_rows:
        candidate = exact_rows[0]
        producer = candidate["exact_final6_opportunities"][0]["primary_producer"]
        target = candidate["target_draw_date"]
        prefix = (
            "synthetic_historical-6of6-candidate"
            if synthetic
            else "reports/historical-6of6-candidate"
        )
        report["candidate_audit_handoff"] = {
            "status": "independent_audit_pending",
            "target_draw_date": target,
            "primary_producer": producer,
            "forecast_payload_sha256": candidate["forecast_payload_sha256"],
            "report_path_after_audit": f"{prefix}__{target}__{producer}__v12.0.2.json",
            "write_policy": "write_once_only_after_independent_audit",
            "eligible_evidence": False,
        }
    report["audit_publication"] = "pending_git_integration"
    json_raw = canonical_json_bytes(report)
    markdown_raw = render_markdown(report).encode("utf-8")
    if synthetic:
        markdown_raw = b"# SYNTHETIC FIXTURE ONLY\n\n" + markdown_raw
    if owner is None:
        if not synthetic:
            raise AttemptError("canonical reports require current artifact ownership")
        _publish_exclusive(paths["json_staging"], paths["json"], json_raw)
        _publish_exclusive(paths["markdown_staging"], paths["markdown"], markdown_raw)
    else:
        owner.publish("json_staging", "json", json_raw)
        owner.publish("markdown_staging", "markdown", markdown_raw)
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
            R3,
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
    _exclusive_bytes(root / ".synthetic-v12-0-2", b"synthetic_fixture_only\n")
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
    if not authority.startup.sealed:
        raise AttemptError("governed history requires sealed durable startup")
    GitRepository(authority.repository).require_full_clean(authority=authority)
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
    git: GitRepository,
    authority: VerifiedAuthorization,
    paths: Mapping[str, Path],
    *,
    startup_checkpoint: Mapping[str, Any],
) -> str:
    """Create an unattached artifact commit with a self-reference-free manifest.

    No ref changes and no network publication occur here. The manifest names
    its parent and tree inputs; its own containing commit is discovered from
    the immutable commit object, avoiding impossible self-referential bytes.
    """
    git.require_full_clean(authority=authority)
    if not authority.startup.sealed:
        raise AttemptError("final manifest requires sealed startup")
    owner = _owned_artifacts(authority)
    file_keys = ("startup", "claim", "ledger", "json", "markdown")
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
        "schema_version": "lotto649-v12.0.2-report-commit-manifest-v1",
        "classification": "consumed_historical_diagnostic_only",
        "parent_commit": authority.execution_commit,
        "authorization_sha256": authority.authorization_sha256,
        "files": files,
        "startup_checkpoint": dict(startup_checkpoint),
        "sealed_startup": {
            "path": paths["startup"].relative_to(git.root).as_posix(),
            "bytes": authority.startup.byte_count,
            "sha256": authority.startup.digest_sha256,
        },
        "self_reference": "containing_commit_resolved_from_Git_object_not_embedded",
    }
    owner.publish("commit_staging", "commit", _canonical(manifest) + b"\n")
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
    index = paths["commit"].parent / (".v12.0.2-index-" + secrets.token_hex(16))
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
        message = b"Record immutable V12.0.2 consumed historical diagnostic artifacts\n"
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
    from .v12_0_2_evidence import four_forecasts

    git = GitRepository(authority.repository)
    paths = _paths(authority.repository / "reports", synthetic=False)
    _require_fresh_outputs(
        {key: path for key, path in paths.items() if key != "startup"}
    )
    git.require_full_clean(authority=authority)
    owner = _owned_artifacts(authority)
    checkpoint = authority.startup.checkpoint().as_dict()
    facts_preimage = _facts_preimage(authority.facts)
    bindings = {
        **authority.payload,
        "startup_checkpoint": checkpoint,
        "verified_facts_sha256": _sha(_canonical(facts_preimage)),
        "execution_authority_M_A_H3": authority.execution_commit,
        "authorization_source_A_H_s3": authority.source_commit,
        "authorization_sha256": authority.authorization_sha256,
        "lease_ref": lease.ref,
        "lease_commit_L_H3": lease.commit,
        "nonce_hex": lease.nonce_hex,
        "seed": 649,
        "classification": "consumed_historical_diagnostic_only",
    }
    owner.create_bytes(
        "claim",
        _canonical(
            {
                "verified_authorization_facts": facts_preimage,
                "schema_version": "lotto649-v12.0.2-permanent-claim-v1",
                "claimed_at": _utc_now(),
                "bindings": bindings,
            }
        )
        + b"\n",
    )
    claim_sha256 = _sha(paths["claim"].read_bytes())
    ledger = DurableLedger(paths["ledger"], bindings, owner=owner)
    first_event = ledger.append(
        "attempt_claimed",
        {"claim_sha256": claim_sha256, "startup_checkpoint": checkpoint},
    )
    authority.startup.append("claim_created", {"claim_sha256": claim_sha256})
    authority.startup.append(
        "scientific_ledger_started", {"first_event_sha256": first_event["event_sha256"]}
    )
    authority.startup.append("history_load_intent", {})
    authority.startup.seal()
    git.require_full_clean(authority=authority)
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
            git.require_full_clean(authority=authority)
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
        owner=owner,
    )
    commit = _publish_git_manifest(git, authority, paths, startup_checkpoint=checkpoint)
    git.require_full_clean(authority=authority)
    return {
        "artifact_commit": commit,
        "classification": "consumed_historical_diagnostic_only",
        "report_path": str(paths["json"]),
        "stop_reason": stop_reason,
        "report": report,
    }


def main() -> int:
    """The only canonical entry; every failure is terminal and safely identified."""
    phase = "isolated_source_preflight"
    authority: VerifiedAuthorization | None = None
    owner: OwnedArtifacts | None = None
    try:
        if sys.argv[1:] != [COMMAND[-1]] or not (
            sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
        ):
            raise AuthorizationError("the fixed isolated launcher is required")
        _require_default_notification_environment()
        repository = Path(__file__).resolve().parents[2]
        api = FixedGitHubApi(os.environ.get("GH_TOKEN", ""))
        phase = "read_only_authorization"
        facts = verify_authorization(repository, api=api)
        phase = "authorized_startup"
        authority = begin_authorized_startup(facts)
        owner = _owned_artifacts(authority)
        phase = "lease_acquisition"
        lease = acquire_historical_lease(authority, api)
        phase = "historical_worker"
        result = _run_canonical(authority, lease)
        phase = "final_ownership_check"
        GitRepository(repository).require_full_clean(authority=authority)
        owner.close()
        authority.startup.close()
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
    except BaseException:  # noqa: BLE001 -- interruption is terminal; no uncontrolled text.
        print(
            _canonical(
                {
                    "schema_version": "lotto649-v12.0.2-safe-terminal-v1",
                    "phase_enum": phase,
                    "result_enum": "authority_failed",
                    "retry_allowed": False,
                }
            ).decode("utf-8"),
            file=sys.stderr,
        )
        return 1
    finally:
        if authority is not None:
            try:
                if owner is not None:
                    owner.close()
                authority.startup.close()
            except BaseException:  # noqa: BLE001 -- descriptor cleanup cannot expose errors.
                print(
                    "V12.0.2 terminal descriptor cleanup; preserve evidence; no retry.",
                    file=sys.stderr,
                )
