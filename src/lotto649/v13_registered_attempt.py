"""One-shot V13.0.0 authority, durable ordering, and fixed GitHub boundary.

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

_DRAFT_INCOMPLETE = False
# Operational fixes: /root/v13_attempt_draft, v13-attempt-operational-fixes-20260913.
# Notification closure integration: /root/v13_attempt_draft,
# v13-attempt-notification-closure-integration-20260913.
# Startup publication binding: /root/v13_attempt_draft,
# v13-attempt-startup-binding-fix-20260913.
_ARTIFACT_INDEX_OS_TEMP = "/tmp"
_FROZEN_CORE_CONSTRUCTOR_SHA256 = (
    "7944102759212ef88da895e1336e8489f077c75e7aa9682fb1c805cd96707675"
)
REPOSITORY = "Jasper-Shi/lottopred"
REPOSITORY_NODE_ID = "R_kgDOT41pdQ"
HISTORY_AUTHORITY = "4a617f2c1575a165b42878600753a01ddf2ced03"
CORE_PATH = "src/lotto649/models/v13_main_set_overlap.py"
R13 = "6ae855a9e23876f4bb1ca77285fbff17fd1a367d"
REGISTRATION_PATH = (
    "evidence/research_registrations/v13-post-rng-main-set-overlap-v1.json"
)
REGISTRATION_SHA256 = "36543acd288418c0cfbf561024b2ca60fa483b8aae6a6988026b76dde861e759"
OPERATIONAL_SHA256 = "69f5eb033a678bf42fe6aeb49ece451934c413a0e4fcd5bc8e1d5e27cb06f382"
FINGERPRINT = "7d86364d43907a64d3eb45f23ebb2fdfc2edf807633748e329cd64e0c8341a37"
REQUIREMENTS_PATH = "requirements/v12-historical.txt"
REQUIREMENTS_SHA256 = "a0dfeac17ad7e1c41dffe4b41b4810156fb028f879d312430bfc517672a570c6"
CONFIG_PATH = "config/research-v13-post-rng-main-set-overlap.yaml"
AUTHORIZATION_PATH = (
    "evidence/research_authorizations/v13-post-rng-main-set-overlap-v1-historical.json"
)
LEASE_REF = "refs/heads/v13-consumption-v13.0.0"
COMMAND = ["python3.12", "tools/run_v13_historical.py", "--consume-v13-once"]
EVIDENCE_PATH = "src/lotto649/v13_evidence.py"
ATTEMPT_PATH = "src/lotto649/v13_registered_attempt.py"
LAUNCHER_PATH = "tools/run_v13_historical.py"
IMPLEMENTATION_PATHS = (
    "src/lotto649/models/v13_main_set_overlap.py",
    "src/lotto649/v13_evidence.py",
    "src/lotto649/v13_registered_attempt.py",
    "tests/fixtures/v13_git_commit_projection.json",
    "tests/test_v13_evidence.py",
    "tests/test_v13_main_set_overlap.py",
    "tests/test_v13_registered_attempt.py",
    "tools/run_v13_historical.py",
)
_STEM = "v13_post_rng_main_set_overlap_v13.0.0_historical"
_ARTIFACT_NAMES = {
    "claim": "v13_post_rng_main_set_overlap_v13.0.0_historical.claim",
    "json": "v13_post_rng_main_set_overlap_v13.0.0_historical.json",
    "json_staging": "v13_post_rng_main_set_overlap_v13.0.0_historical.json.staging",
    "ledger": "v13_post_rng_main_set_overlap_v13.0.0_historical.ledger.jsonl",
    "manifest": "v13_post_rng_main_set_overlap_v13.0.0_historical.commit-manifest.json",
    "manifest_staging": "v13_post_rng_main_set_overlap_v13.0.0_historical.commit-manifest.json.staging",
    "markdown": "v13_post_rng_main_set_overlap_v13.0.0_historical.md",
    "markdown_staging": "v13_post_rng_main_set_overlap_v13.0.0_historical.md.staging",
    "startup": "v13_post_rng_main_set_overlap_v13.0.0_historical.startup.jsonl",
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
    "lotto649.models.v13_main_set_overlap": frozenset(
        {
            "CANDIDATE_MODEL_NAME",
            "CONTROL_MODEL_NAME",
            "FAIR_MEAN",
            "FAIR_SET_COUNT",
            "OverlapForecast",
            "forecast_candidate",
            "forecast_control",
            "moments",
            "map_score",
            "map_objective",
            "solve_map_beta",
            "MainDraw",
            "validate_forecast",
            "CANDIDATE_NAME",
            "CONTROL_NAME",
            "CANDIDATE_FEATURE_SET",
            "CONTROL_FEATURE_SET",
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
    "lotto649.v13_evidence": frozenset(
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
    "lotto649.v13_registered_attempt": frozenset({"main"}),
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
        "beta_hex",
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
        "complement_mean",
        "complement_mean_hex",
        "concat",
        "copy",
        "cos",
        "count",
        "counts_sha256",
        "create_bytes",
        "create_ref",
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
        "digest",
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
        "feature_set",
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
        "get_commit",
        "get_path",
        "get_ref",
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
        "log_z_hex",
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
        "mean_hex",
        "members",
        "metadata",
        "microsecond",
        "min_history",
        "min_samples",
        "minor",
        "mkdir",
        "model_name",
        "model_version",
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
        "post_commit",
        "pread",
        "predict",
        "predict_proba",
        "prefix_byte_count",
        "prefix_sha256",
        "previous_bucket",
        "probabilities",
        "probability_hex",
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
        "scientific_projection_sha256",
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
        "source_anchor",
        "source_commit",
        "source_draw_date",
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
        "training_overlap_sum",
        "training_pair_count",
        "transaction",
        "transformed_anchor",
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
    "tools/run_v13_historical.py",
    "src/lotto649/v13_registered_attempt.py",
    "src/lotto649/v13_evidence.py",
    "src/lotto649/models/v13_main_set_overlap.py",
    "src/lotto649/operational_history.py",
    "src/lotto649/models/factory.py",
    "src/lotto649/notification.py",
    "evidence/research_registrations/v13-post-rng-main-set-overlap-v1.json",
    "config/research-v13-post-rng-main-set-overlap.yaml",
    "config.yaml",
    "requirements/v12-historical.txt",
)


_EXACT_RUNTIME = {
    "byteorder": "little",
    "dependency_manifest_sha256": "a0dfeac17ad7e1c41dffe4b41b4810156fb028f879d312430bfc517672a570c6",
    "implementation": "cpython",
    "installed_distributions": {
        "beautifulsoup4": "4.13.5",
        "certifi": "2025.11.12",
        "charset-normalizer": "3.4.4",
        "idna": "3.11",
        "iniconfig": "2.3.0",
        "joblib": "1.5.2",
        "numpy": "2.3.5",
        "packaging": "26.3",
        "pandas": "2.3.3",
        "pip": "25.1.1",
        "pluggy": "1.6.0",
        "pygments": "2.21.0",
        "pypdf": "6.16.1",
        "pytest": "9.1.1",
        "python-dateutil": "2.9.0.post0",
        "pytz": "2025.2",
        "pyyaml": "6.0.3",
        "requests": "2.32.5",
        "ruff": "0.16.6",
        "scikit-learn": "1.7.2",
        "scipy": "1.16.3",
        "six": "1.17.0",
        "soupsieve": "2.5",
        "threadpoolctl": "3.5.0",
        "typing-extensions": "4.15.0",
        "tzdata": "2025.2",
        "urllib3": "2.5.0",
    },
    "machine": "arm64",
    "platform": "macOS-26.5.2-arm64-arm-64bit",
    "python_version": "3.12.11",
}
_LEDGER_PAYLOAD_KEYS = {
    "attempt_archived": ["reason", "retry_allowed"],
    "attempt_claimed": ["claim_sha256", "startup_checkpoint"],
    "historical_6of6_candidate_detected": [
        "target_draw_date",
        "forecast_payload_sha256",
        "opportunities",
        "audit_status",
        "eligible_evidence",
        "global_stop_search",
    ],
    "historical_top12_all_six_detected": [
        "target_draw_date",
        "forecast_payload_sha256",
        "producers",
        "eligible_evidence",
    ],
    "prediction_frozen": ["forecast_payload", "forecast_payload_sha256"],
    "target_revealed_scored": [
        "target_draw_date",
        "actual",
        "bonus",
        "forecast_payload",
        "forecast_payload_sha256",
        "prediction_generated_at",
        "prediction_frozen_event_sequence",
        "prediction_frozen_event_sha256",
        "scores",
        "fair_scores",
        "unique_final6",
        "unique_opportunity_count",
        "exact_final6_opportunities",
        "top12_all_six_producers",
        "cumulative_opportunities",
    ],
}
_PRIOR_ACCOUNTING_PINS = [
    {
        "bytes": 14597956,
        "commit": "c9b483f6e89bf73eade28829188fbebe745e28c0",
        "git_blob": "338dea7e401ee385807cd954151664825d0e8a68",
        "mode": "100644",
        "path": "reports/v12_post_rng_parity_composition_transition_v12.0.2_historical.json",
        "type": "blob",
    },
    {
        "bytes": 33106,
        "commit": "f247649be2928bfc7cbf5a00c0a400eedadb89f2",
        "git_blob": "dbe9b4b0cb14be7549a62d9c56cefb61dffa5ada",
        "mode": "100644",
        "path": "evidence/research_audits/v12-0-2-historical-20260913/independent-audit.json",
        "type": "blob",
    },
    {
        "bytes": 35474,
        "commit": "f247649be2928bfc7cbf5a00c0a400eedadb89f2",
        "git_blob": "d92e68bec72a15dbe9813ff652d55c74fb22f1ae",
        "mode": "100644",
        "path": "evidence/research_audits/v12-0-2-historical-20260913/statistics-replay.py.txt",
        "type": "blob",
    },
    {
        "bytes": 14044,
        "commit": "f247649be2928bfc7cbf5a00c0a400eedadb89f2",
        "git_blob": "e994a49015c2f9c8ceb6f30f8c19f7c6bb19eb35",
        "mode": "100644",
        "path": "evidence/research_audits/v12-0-2-historical-20260913/statistics-replay-result.json",
        "type": "blob",
    },
    {
        "bytes": 796,
        "commit": "f247649be2928bfc7cbf5a00c0a400eedadb89f2",
        "git_blob": "45e10551e8a6449ee959dfa61ece974707ca40a0",
        "mode": "100644",
        "path": "evidence/research_audits/v12-0-2-historical-20260913/statistics-replay-invocation.json",
        "type": "blob",
    },
    {
        "bytes": 21416,
        "commit": "0af20fc41fc5aaa0879dada0a258797a8bc14e20",
        "git_blob": "43411a12a4ad9154dcce08a4951a3cef299ca804",
        "mode": "100644",
        "path": "evidence/research_registrations/v12-post-rng-parity-composition-transition-v1.json",
        "type": "blob",
    },
]
_REGISTRATION_STATUSES = {
    "A": [
        "config/research-v13-post-rng-main-set-overlap.yaml",
        "docs/experiments/V13_post_rng_main_set_overlap.md",
        "docs/research/V13_post_rng_main_set_overlap_basis.md",
        "evidence/research_registrations/v13-post-rng-main-set-overlap-v1.json",
        "tests/test_v13_registration.py",
    ],
    "M": [
        "docs/CODEX_HANDOFF.md",
        "docs/MODEL_PROTOCOL.md",
        "docs/RESEARCH_ROADMAP.md",
    ],
}
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
        "src/lotto649/v13_registered_attempt.py",
        "FixedGitHubApi.__init__",
    ): "a02a654059bdb216ff2f9445e93d35c9d23f2449acf6b902a8c5966d050a8ec2",
    (
        "src/lotto649/v13_registered_attempt.py",
        "FixedGitHubApi._request_json_checked",
    ): "91dc8d1299098af523f069c32daf453200a3c03342bd29c8b34b297d1db5d657",
    (
        "src/lotto649/v13_registered_attempt.py",
        "FixedGitHubApi.request_json",
    ): "c528920339ceaa90faea6fe71337dea709e7dc9953bf4a0663f797cb56271fdb",
    (
        "src/lotto649/v13_registered_attempt.py",
        "OwnedArtifacts.for_synthetic",
    ): "bd35d81e278b90d25b24fe1d51311b01ec18348dc2c761c15bcdd49338b90e4f",
    (
        "src/lotto649/v13_registered_attempt.py",
        "StartupJournal._create",
    ): "9ea2b76308eef401c6e4e750d93574b84fa9f79ee0396e69b965f4a9a4a753cc",
    (
        "src/lotto649/v13_registered_attempt.py",
        "StartupJournal.for_synthetic",
    ): "15baf689ea809aae0feac0f432164674053f90842ba497d06aee5d539af6363c",
    (
        "src/lotto649/v13_registered_attempt.py",
        "TransportError.__init__",
    ): "2d75234e45076dcc7d640d3ef40dc7a84574d99dee3505661765d1129e42235a",
    (
        "src/lotto649/v13_registered_attempt.py",
        "_NotificationHTTP.__init__",
    ): "d89e5c7ced67db8a4a1d0d092b1bc812b08ca705f19a6c69f2a0d3d60e840759",
    (
        "src/lotto649/v13_registered_attempt.py",
        "_NotificationHTTP.request_json",
    ): "b7a9d06e03a399dc582bb9a00f42e7513cbe607a84eadfd47cd8a55dc251b1e8",
    (
        "src/lotto649/v13_registered_attempt.py",
        "_artifact_entry_bytes",
    ): "ac2b37a2455a0bc6e9fc4b75ce44fee2869fe5197a0daed6f9bad8e66ea84ac6",
    (
        "src/lotto649/v13_registered_attempt.py",
        "_bind_historical_transport",
    ): "ee5f155585948fe1cc3165eb1a35dce17cbe5a8af0d678bf506da51d08e1c243",
    (
        "src/lotto649/v13_registered_attempt.py",
        "_complete_historical_transport",
    ): "261dcd130a8865d84835dc9f7a19a879040da046647d9f36de262841eeb64a10",
    (
        "src/lotto649/v13_registered_attempt.py",
        "_historical_after_request",
    ): "ca94063302131400581947889b57d690de28ade63d4f00afefff8f95a4b1b809",
    (
        "src/lotto649/v13_registered_attempt.py",
        "_historical_authority_context",
    ): "0d14cf39a2d9af4f446feca90582225930ed2baa418f92f1357195d0120c0768",
    (
        "src/lotto649/v13_registered_attempt.py",
        "_historical_before_request",
    ): "d145b4ee457e68165d05ef20500bb41b3ef6a3cb5f5740d2bf83924f2cb96214",
    (
        "src/lotto649/v13_registered_attempt.py",
        "_historical_bound_state",
    ): "3691e06b4763048a0cb5d7dbbbfb26cdad3f5b8b2f9fe669b89ee1a8e9a561d1",
    (
        "src/lotto649/v13_registered_attempt.py",
        "_historical_intent",
    ): "7885bd7ce95f60f47ad9a120f295aea03963d7da9cdf9c66de0fc4abaa5cf574",
    (
        "src/lotto649/v13_registered_attempt.py",
        "_historical_journal_suffix",
    ): "a6a47b37e0ba2e428bfb68619f1b6170c59dd816af0e8cfe5371f8504e3db6e0",
    (
        "src/lotto649/v13_registered_attempt.py",
        "_historical_plan",
    ): "2f04483ad9b4286c19a15a6451647f943cf75a2accd4a44905692777f183a32e",
    (
        "src/lotto649/v13_registered_attempt.py",
        "_historical_success_receipt",
    ): "7a337fb1bc259078bcf1419cd22289054a88f7d5472a68930f698ff78929cfc4",
    (
        "src/lotto649/v13_registered_attempt.py",
        "_historical_transport_poison",
    ): "2a19b05f52ce5f2e9a8660bc8cd95d0a45cf9c472484a1522d55f52889534f83",
    (
        "src/lotto649/v13_registered_attempt.py",
        "_historical_transport_register",
    ): "7572e4580752080fa91997d1e399c067228ee7dc30f7a76f04224d10f54a9c7c",
    (
        "src/lotto649/v13_registered_attempt.py",
        "_historical_transport_state",
    ): "4f64f33b43a114376580761074906d1db750a610b6150f469cd10e9e118963f9",
    (
        "src/lotto649/v13_registered_attempt.py",
        "_issue_authorization",
    ): "ff9e4784432eb3135d363cd53398278bd63d6a153f02592853e0ab34cac9d91d",
    (
        "src/lotto649/v13_registered_attempt.py",
        "_issue_lease",
    ): "b0987c4f2c0a72b7c0c90686a4ae6dbb2d096e4b690354893f34b1fdcf386bbf",
    (
        "src/lotto649/v13_registered_attempt.py",
        "_issue_notification_files",
    ): "af4fb78bd75c02cb1bcb620edcd51c25c2780c43bb9e9e3520482f75ef471d63",
    (
        "src/lotto649/v13_registered_attempt.py",
        "_issue_verified_facts",
    ): "5fa1da583be2ba05352457b1dfa48913b9bc14e5a179130a4303c46cbaf105fa",
    (
        "src/lotto649/v13_registered_attempt.py",
        "_notification_capture_artifacts",
    ): "e49ef6ef2a8fc90de8b3f23b0c3fbb048917ffa21fb2331096323afcd121b4b2",
    (
        "src/lotto649/v13_registered_attempt.py",
        "_notification_check_immutable",
    ): "0d09c151cf1e963f6259d5dc749a953fab45c1d4db7385f2e041d8b74d04e50f",
    (
        "src/lotto649/v13_registered_attempt.py",
        "_notification_checkpoint_metadata",
    ): "58908a98bec911fa805fef40aa1a36c0ff646b1652d49b718d18d533c5a948a6",
    (
        "src/lotto649/v13_registered_attempt.py",
        "_notification_ledger_metadata",
    ): "6eb574b6fc07ac46f4d16e96177bbe81259733d8b5e4701efd501e601c4b28c3",
    (
        "src/lotto649/v13_registered_attempt.py",
        "_notification_publication_time",
    ): "8541ca014ad7d16393563f4918b41e3233ec0bbaeba5c2a2637940c755baeb2b",
    (
        "src/lotto649/v13_registered_attempt.py",
        "_notification_read_immutable",
    ): "ef8314020195965a846d39db59beb7afa3647bf053d956a30ef06c99f9b5a965",
    (
        "src/lotto649/v13_registered_attempt.py",
        "_notification_safe_directory",
    ): "90adf8f86c2099c8603a7c3ca04a23d8f6867132a4871a8d7ae524431847366f",
    (
        "src/lotto649/v13_registered_attempt.py",
        "_notification_startup_metadata",
    ): "64520e5313fbccefbbfa51a3d1ae756834ae478f894b82e7930e6954fc59b5c4",
    (
        "src/lotto649/v13_registered_attempt.py",
        "_plan_historical_transport",
    ): "b75939a0b245e4ba89df8b3a8d18ab4981ac0456d634d246fe5624f4a9b0dca7",
    (
        "src/lotto649/v13_registered_attempt.py",
        "_precredential_local_runtime",
    ): "ae3b0df760641d01a5fdeb77f9f77b813416b3fe78a26af6e0c70be68b267e55",
    (
        "src/lotto649/v13_registered_attempt.py",
        "_prepare_production_notification",
    ): "f42e136c8a7b74a66d400748ec70f10be9fa891c697da9bbdb6d08d587f98962",
    (
        "src/lotto649/v13_registered_attempt.py",
        "_publish_git_manifest.current_index_identity",
    ): "6d333e210924e4219501a59478e70b526d634349aca2620ebad186309344ab9c",
    (
        "src/lotto649/v13_registered_attempt.py",
        "_require_production_notification_issuance",
    ): "b463cacb7754b03e69e18779f7ec7f2c90463404384ffeda959c164e3b3185fc",
    (
        "src/lotto649/v13_registered_attempt.py",
        "_startup_verify_owned",
    ): "48241231ea4b5e7b79518643d9d17eebdd207a1209f57f5930c8cc186355de76",
    (
        "src/lotto649/v13_registered_attempt.py",
        "_verify_loaded_modules",
    ): "5e28b8ed294c2c6a8961eccc8ef7e76e51a3879db4f09af11d007055ff9ace5f",
    (
        "src/lotto649/v13_registered_attempt.py",
        "acquire_historical_lease",
    ): "4ba69b96020391fe769288b4d9c8452a84531be9cda8ae5fbedabf30a445b543",
    (
        "src/lotto649/v13_registered_attempt.py",
        "verify_notification_publication",
    ): "81be0b7faf6486bfb4e887afbb2715b00d3de6d9cc34d899503940ea02ad8d1f",
    (
        "tools/run_v13_historical.py",
        "main",
    ): "2141698a2c24b8c938f505b4cadbfe25adb0280f5bd51c9b204bcad946dee096",
}

_SCOPED_ATTRIBUTE_OWNERS = {
    (
        "src/lotto649/v13_registered_attempt.py",
        "FixedGitHubApi.request_json",
    ): frozenset(["_request_json_checked"]),
    (
        "src/lotto649/v13_registered_attempt.py",
        "_NotificationHTTP.request_json",
    ): frozenset(["_request_json_checked"]),
    (
        "src/lotto649/v13_registered_attempt.py",
        "verify_notification_publication",
    ): frozenset(["format"]),
}

_SCOPED_CALL_OWNERS = {
    ("src/lotto649/v13_registered_attempt.py", "os.mkdir"): frozenset(
        [
            "OwnedArtifacts.for_synthetic",
            "StartupJournal.for_synthetic",
            "_notification_safe_directory",
        ]
    ),
    ("src/lotto649/v13_registered_attempt.py", "os.pread"): frozenset(
        [
            "_artifact_entry_bytes",
            "_notification_check_immutable",
            "_notification_read_immutable",
            "_publish_git_manifest.current_index_identity",
            "_startup_verify_owned",
        ]
    ),
    ("src/lotto649/v13_registered_attempt.py", "requests.Session"): frozenset(
        ["FixedGitHubApi.__init__", "_NotificationHTTP.__init__"]
    ),
    (
        "src/lotto649/v13_registered_attempt.py",
        "requests.adapters.HTTPAdapter",
    ): frozenset(["FixedGitHubApi.__init__", "_NotificationHTTP.__init__"]),
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
            "c42ba1ff88224a2100022895ded0bab3ccdb0a3fcf6bf70001fff6ba3d70c1d1",
            "f5f6801159316fb8716b4d1807221bf315d8a8443ce9ec398307862964f5d0bc",
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


def _source_function_owner(
    node: ast.AST, parents: Mapping[ast.AST, ast.AST]
) -> tuple[str, ast.FunctionDef] | None:
    current: ast.AST | None = node
    while current is not None and not isinstance(current, ast.FunctionDef):
        current = parents.get(current)
    if current is None:
        return None
    function = current
    names = []
    while current is not None:
        if isinstance(current, (ast.ClassDef, ast.FunctionDef)):
            names.append(current.name)
        current = parents.get(current)
    return ".".join(reversed(names)), function


def _scoped_attribute_allowed(
    path: str, node: ast.Attribute, parents: Mapping[ast.AST, ast.AST]
) -> bool:
    owner = _source_function_owner(node, parents)
    if owner is None:
        return False
    name, function = owner
    key = (path, name)
    return node.attr in _SCOPED_ATTRIBUTE_OWNERS.get(key, frozenset()) and _sha(
        ast.dump(function, include_attributes=False).encode()
    ) == _SENSITIVE_FUNCTION_AST.get(key)


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
            and not _scoped_attribute_allowed(path, node, parents)
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
            owners = (
                _SCOPED_CALL_OWNERS.get((path, origin + "." + member_path))
                if origin is not None
                else None
            )
            if owners is not None:
                call = parents.get(node)
                owner = _source_function_owner(node, parents)
                if (
                    not isinstance(call, ast.Call)
                    or call.func is not node
                    or owner is None
                    or owner[0] not in owners
                    or _sha(ast.dump(owner[1], include_attributes=False).encode())
                    != _SENSITIVE_FUNCTION_AST.get((path, owner[0]))
                ):
                    raise AuthorizationError(
                        "scoped runtime API escaped its exact source owner"
                    )


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
    expected_functions = {
        name for source_path, name in _SENSITIVE_FUNCTION_AST if source_path == path
    }
    found_functions: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            owner = _source_function_owner(node, parents)
            if owner is None:
                raise AuthorizationError("source function ownership is unavailable")
            name, _function = owner
            expected = _SENSITIVE_FUNCTION_AST.get((path, name))
            if expected is not None:
                if (
                    name in found_functions
                    or _sha(ast.dump(node, include_attributes=False).encode())
                    != expected
                ):
                    raise AuthorizationError(
                        "sealed source function changed or duplicated"
                    )
                found_functions.add(name)
                trusted_nodes.update(ast.walk(node))
    if found_functions != expected_functions:
        raise AuthorizationError("sealed source function is missing or moved")
    dynamic_names = {
        "__import__",
        "breakpoint",
        "help",
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
                and not (
                    path == CORE_PATH and blob_sha256 == _FROZEN_CORE_CONSTRUCTOR_SHA256
                )
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
        or sys.version_info[:3] != (3, 12, 11)
        or sys.float_info.radix != 2
        or sys.float_info.mant_dig != 53
        or sys.float_info.max_exp != 1024
    ):
        raise AuthorizationError(
            "registered CPython 3.12.11 binary64 runtime is required"
        )
    root = Path(__file__).resolve().parents[2]
    if _sha((root / REQUIREMENTS_PATH).read_bytes()) != REQUIREMENTS_SHA256:
        raise AuthorizationError("frozen dependency manifest differs")
    installed: dict[str, str] = {}
    for distribution in distributions():
        name = re.sub(r"[-_.]+", "-", distribution.metadata["Name"]).lower()
        if name in installed:
            raise AuthorizationError("duplicate installed distribution")
        installed[name] = distribution.version
    result = {
        "implementation": sys.implementation.name,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "byteorder": sys.byteorder,
        "dependency_manifest_sha256": REQUIREMENTS_SHA256,
        "installed_distributions": dict(sorted(installed.items())),
    }
    if result != _EXACT_RUNTIME or len(installed) != 27:
        raise AuthorizationError(
            "exact registered runtime or distribution inventory differs"
        )
    return result


# Historical source origin: /root/i3_transport, i3-transport-authoring-20260913,
# in the reviewed V12.0.2 mechanics. This is not new I13 author provenance.
# V13 adaptation: /root/v13_attempt_draft, v13-attempt-draft-authoring-20260913.


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
    expected_name = "LOTTO649 V13 Consumption Lease"
    expected_email = "lotto649-v13-lease@users.noreply.github.com"
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
    _exact_string(body["schema_version"], "lotto649-v13-consumption-lease-v1")
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


# Precredential local verification: /root,
# root-v13-implementation-integration-20260913.
def _precredential_local_runtime(repository: Path) -> None:
    """Verify local registered source/runtime before any token-bearing package.

    This is read-only and uses only the already loaded standard-library boundary.
    It issues no facts, authority, transport, startup, lease or notification state.
    Remote authorization and its final freshness checks must still follow.
    """
    git = GitRepository(repository)
    git.require_full_clean()
    head = git.head()
    _science, operation = _registered_authorities(git, head)
    runtime = runtime_identity()
    if runtime != operation["runtime_closure"]["exact_runtime"]:
        raise AuthorizationError("local registered runtime identity differs")
    raw = git.read_blob(head, AUTHORIZATION_PATH)
    authorization = _closed_object(
        _json(raw),
        set(operation["authorization"]["authorization_schema"]["required_keys"]),
    )
    if raw != _canonical(authorization) + b"\n":
        raise AuthorizationError("local authorization bytes are not canonical")
    if authorization["runtime"] != runtime:
        raise AuthorizationError("local authorization runtime differs")
    manifest = _implementation_manifest(git, head)
    if manifest != authorization["implementation_files"] or _sha(
        _canonical(manifest)
    ) != _digest(authorization["implementation_files_sha256"]):
        raise AuthorizationError("local implementation file binding differs")
    closure = _core_and_closure(
        git,
        head,
        required_core_sha256=_digest(authorization["pure_core_sha256"]),
    )
    if closure != authorization["runtime_dependency_closure"] or _sha(
        _canonical(closure)
    ) != _digest(authorization["runtime_dependency_closure_sha256"]):
        raise AuthorizationError("local historical runtime closure differs")
    _verify_worktree_runtime(git, head, closure)
    git.require_full_clean()
    if git.head() != head:
        raise AuthorizationError("local source moved before credential boundary")


# Author: /root/v13_notification_production_draft
# Session: v13-historical-transport-purpose-fix-authoring-20260913
# Internal historical transport purpose; no new imports, routes or schema.

_HISTORICAL_TRANSPORTS: dict[object, dict[str, Any]] = {}
_HISTORICAL_TRANSPORT_OWNERS: list[tuple[object, object, object]] = []


def _historical_transport_poison(api: object) -> None:
    if type(api) is FixedGitHubApi:
        api._terminal = True
    state = _HISTORICAL_TRANSPORTS.get(api)
    if state is not None:
        state["poisoned"] = True


def _historical_transport_register(api: object) -> None:
    if type(api) is not FixedGitHubApi or api in _HISTORICAL_TRANSPORTS:
        _historical_transport_poison(api)
        raise AuthorizationError("historical transport construction cannot repeat")
    _HISTORICAL_TRANSPORTS[api] = {
        "session": api._session,
        "authority": None,
        "startup": None,
        "binding": None,
        "phase": "read_only",
        "commit_attempted": False,
        "ref_attempted": False,
        "poisoned": False,
        "status": None,
        "request": None,
        "prefix": None,
        "plan": None,
    }


def _historical_transport_state(api: object) -> dict[str, Any]:
    if type(api) is not FixedGitHubApi or api not in _HISTORICAL_TRANSPORTS:
        raise AuthorizationError("historical transport is unissued")
    state = _HISTORICAL_TRANSPORTS[api]
    if (
        state["poisoned"]
        or api._terminal
        or api._session is not state["session"]
        or api._commit_post_attempted is not state["commit_attempted"]
        or api._create_ref_attempted is not state["ref_attempted"]
        or api._last_status != state["status"]
        or api._session.trust_env is not False
    ):
        _historical_transport_poison(api)
        raise AuthorizationError("historical transport binding changed or ended")
    return state


def _historical_authority_context(authority: VerifiedAuthorization) -> dict[str, Any]:
    """Read existing issuance and original owned startup; never issue authority."""
    if type(authority) is not VerifiedAuthorization:
        raise AuthorizationError("historical transport requires an issued authority")
    _require_authorization_capability(authority)
    if not any(used is authority for used in _USED_AUTHORITIES):
        raise AuthorizationError("historical lease acquisition has not begun")
    checked = _require_verified_facts(authority.facts)
    journal = _startup_state(authority.startup)
    authority.startup.verify_owned()
    if (
        checked["repository"] != authority.repository
        or checked["head"] != authority.execution_commit
        or authority.startup.verified_identity != checked["startup_identity"]
        or journal["repository"] != authority.repository
        or journal["execution_head"] != authority.execution_commit
        or journal["first_payload"]["repository"] != REPOSITORY
        or journal["first_payload"]["branch"] != "main"
        or journal["relative_path"] != "reports/" + _ARTIFACT_NAMES["startup"]
    ):
        raise AuthorizationError("historical authority and owned startup differ")
    return {
        "stamp": _authorization_stamp(authority),
        "facts": authority.facts,
        "startup": authority.startup,
    }


def _historical_bound_state(api: object) -> dict[str, Any]:
    state = _historical_transport_state(api)
    if state["authority"] is None or state["phase"] in {"read_only", "complete"}:
        raise AuthorizationError("historical transport has no active purpose")
    context = _historical_authority_context(state["authority"])
    if (
        context["stamp"] != state["binding"]
        or context["startup"] is not state["startup"]
        or context["facts"] is not state["facts"]
    ):
        raise AuthorizationError("historical transport authority drifted")
    return state


def _bind_historical_transport(
    api: FixedGitHubApi, authority: VerifiedAuthorization
) -> None:
    """One immutable same-instance purpose, reserved before its fresh ref GET."""
    try:
        state = _historical_transport_state(api)
        context = _historical_authority_context(authority)
        startup = context["startup"]
        journal = _startup_state(startup)
        with _CAPABILITY_LOCK:
            if (
                state["phase"] != "read_only"
                or api._request_active
                or journal["sequence"] != 2
                or journal["sealed"]
                or journal["nonce"] is not None
                or any(
                    owner is authority or facts is context["facts"] or writer is startup
                    for owner, facts, writer in _HISTORICAL_TRANSPORT_OWNERS
                )
            ):
                raise AuthorizationError(
                    "historical transport purpose cannot be rebound"
                )
            _HISTORICAL_TRANSPORT_OWNERS.append((authority, context["facts"], startup))
            state["authority"] = authority
            state["facts"] = context["facts"]
            state["startup"] = startup
            state["binding"] = context["stamp"]
            state["prefix"] = journal["raw"]
            state["phase"] = "await_absence"
    except BaseException:
        _historical_transport_poison(api)
        raise


def _historical_journal_suffix(
    state: dict[str, Any], expected: Sequence[tuple[str, dict[str, Any]]]
) -> None:
    startup = state["startup"]
    startup.verify_owned()
    journal = _startup_state(startup)
    prefix = state["prefix"]
    raw = journal["raw"]
    if type(prefix) is not bytes or not raw.startswith(prefix):
        raise AuthorizationError("historical startup prefix changed")
    before = prefix.splitlines(keepends=True)
    added = raw[len(prefix) :].splitlines(keepends=True)
    if len(added) != len(expected) or journal["sequence"] != len(before) + len(added):
        raise AuthorizationError("historical startup phase differs")
    previous = _sha(before[-1])
    for index, (line, (kind, payload)) in enumerate(zip(added, expected, strict=True)):
        event = _closed_object(
            _json(line),
            {
                "schema_version",
                "sequence",
                "generated_at",
                "previous_event_sha256",
                "kind",
                "payload",
            },
        )
        if (
            line != _canonical(event) + b"\n"
            or event["schema_version"] != _STARTUP_SCHEMA
            or type(event["sequence"]) is not int
            or event["sequence"] != len(before) + index
            or event["previous_event_sha256"] != previous
            or event["kind"] != kind
            or event["payload"] != payload
        ):
            raise AuthorizationError("historical durable receipt or intent differs")
        previous = _sha(line)
    if journal["head"] != previous or journal["digest"] != _sha(raw):
        raise AuthorizationError("historical startup digest differs")
    state["prefix"] = raw


def _plan_historical_transport(
    api: FixedGitHubApi, authority: VerifiedAuthorization, nonce: str
) -> tuple[str, bytes, dict[str, Any]]:
    try:
        state = _historical_bound_state(api)
        if state["authority"] is not authority or state["phase"] != "absence_verified":
            raise AuthorizationError("historical plan requires its fresh exact absence")
        _historical_journal_suffix(
            state, [("lease_absence_confirmed", {"http_status": 404})]
        )
        oid, raw, payload = _lease_commit(
            GitRepository(authority.repository), authority, nonce
        )
        if _lease_request_parts(payload)[:2] != (oid, raw):
            raise AuthorizationError("historical plan projection differs")
        state["plan"] = {
            "oid": oid,
            "raw": raw,
            "payload": payload,
            "nonce": nonce,
            "commit_bytes": _canonical(payload),
            "ref_bytes": _canonical({"ref": LEASE_REF, "sha": oid}),
        }
        state["plan_stamp"] = _canonical(
            state["plan"]
            | {
                "raw": raw.hex(),
                "commit_bytes": _canonical(payload).hex(),
                "ref_bytes": _canonical({"ref": LEASE_REF, "sha": oid}).hex(),
            }
        )
        state["phase"] = "planned"
        return oid, raw, payload
    except BaseException:
        _historical_transport_poison(api)
        raise


def _historical_plan(state: dict[str, Any]) -> dict[str, Any]:
    plan = state["plan"]
    if (
        type(plan) is not dict
        or _canonical(
            plan
            | {
                "raw": plan["raw"].hex(),
                "commit_bytes": plan["commit_bytes"].hex(),
                "ref_bytes": plan["ref_bytes"].hex(),
            }
        )
        != state["plan_stamp"]
    ):
        raise AuthorizationError("historical immutable request plan changed")
    return plan


def _historical_intent(plan: dict[str, Any], phase: str) -> dict[str, Any]:
    body = plan["commit_bytes"] if phase == "lease_commit" else plan["ref_bytes"]
    return {
        "phase_enum": phase,
        "nonce_hex": plan["nonce"],
        "expected_lease_oid": plan["oid"],
        "raw_commit_sha256": _sha(plan["raw"]),
        "request_body_bytes": len(body),
        "request_body_sha256": _sha(body),
    }


def _historical_success_receipt(plan: dict[str, Any], phase: str) -> dict[str, Any]:
    return {
        "phase_enum": phase,
        "result_enum": "success",
        "http_status": 201,
        "validated_oid": plan["oid"],
    }


def _historical_before_request(
    api: FixedGitHubApi,
    method: str,
    suffix: str,
    body: bytes | None,
    allow_absent: bool,
) -> None:
    state = _historical_transport_state(api)
    if state["request"] is not None or api._request_active:
        raise AuthorizationError("historical request is already active")
    action = "metadata"
    if state["authority"] is None:
        if method != "GET":
            raise AuthorizationError(
                "historical transport is read-only without issued authority"
            )
    else:
        state = _historical_bound_state(api)
        if suffix == "/git/ref/heads/v13-consumption-v13.0.0":
            if method == "GET" and allow_absent and state["phase"] == "await_absence":
                _historical_journal_suffix(state, [])
                action = "absence"
            elif (
                method == "GET"
                and not allow_absent
                and state["phase"] == "ref_post_verified"
            ):
                plan = _historical_plan(state)
                _historical_journal_suffix(
                    state,
                    [
                        (
                            "lease_ref_POST_receipt",
                            _historical_success_receipt(plan, "lease_ref"),
                        )
                    ],
                )
                action = "ref_get"
            else:
                raise AuthorizationError("historical ref request is out of order")
        elif method == "POST":
            plan = _historical_plan(state)
            if (
                suffix == "/git/commits"
                and state["phase"] == "planned"
                and not state["commit_attempted"]
            ):
                phase, expected_body, action = (
                    "lease_commit",
                    plan["commit_bytes"],
                    "commit_post",
                )
                events = [("lease_commit_POST_intent", _historical_intent(plan, phase))]
            elif (
                suffix == "/git/refs"
                and state["phase"] == "commit_get_verified"
                and not state["ref_attempted"]
            ):
                phase, expected_body, action = (
                    "lease_ref",
                    plan["ref_bytes"],
                    "ref_post",
                )
                events = [
                    ("lease_commit_GET_verified", {"validated_oid": plan["oid"]}),
                    ("lease_ref_POST_intent", _historical_intent(plan, phase)),
                ]
            else:
                raise AuthorizationError("historical POST slot or phase is unavailable")
            if body != expected_body:
                raise AuthorizationError(
                    "historical POST differs from internally bound bytes"
                )
            _historical_journal_suffix(state, events)
        elif suffix.startswith("/git/commits/"):
            plan = _historical_plan(state)
            if (
                suffix != "/git/commits/" + plan["oid"]
                or state["phase"] != "commit_post_verified"
            ):
                raise AuthorizationError("historical commit GET is out of order")
            _historical_journal_suffix(
                state,
                [
                    (
                        "lease_commit_POST_receipt",
                        _historical_success_receipt(plan, "lease_commit"),
                    )
                ],
            )
            action = "commit_get"
    state["request"] = action
    if action == "absence":
        state["phase"] = "absence_started"
    if action == "commit_post":
        state["commit_attempted"] = True
    if action == "ref_post":
        state["ref_attempted"] = True


def _historical_after_request(api: FixedGitHubApi, result: object) -> None:
    state = _HISTORICAL_TRANSPORTS[api]
    state["status"] = api._last_status
    action = state["request"]
    if action == "absence":
        if api._last_status != 404 or result is not None:
            raise AuthorizationError("historical absence is not an exact fresh 404")
        state["phase"] = "absence_verified"
    elif action in {"commit_post", "commit_get", "ref_post", "ref_get"}:
        plan = _historical_plan(state)
        if action == "commit_post":
            _verify_lease_post_response(result, plan["oid"], plan["payload"])
        elif action == "commit_get":
            _verify_lease_object(result, plan["oid"], plan["raw"], plan["payload"])
        else:
            _verify_lease_ref(result, plan["oid"])
        state["phase"] = action + "_verified"
    state["request"] = None


def _complete_historical_transport(
    api: FixedGitHubApi, authority: VerifiedAuthorization
) -> None:
    try:
        state = _historical_bound_state(api)
        if state["authority"] is not authority or state["phase"] != "ref_get_verified":
            raise AuthorizationError(
                "historical transport has not completed its own protocol"
            )
        plan = _historical_plan(state)
        _historical_journal_suffix(
            state, [("lease_ref_reread_verified", {"validated_oid": plan["oid"]})]
        )
        state["phase"] = "complete"
    except BaseException:
        _historical_transport_poison(api)
        raise


class FixedGitHubApi:
    """Closed fixed-origin transport, with one poisoned slot per mutation."""

    def __init__(self, token: str) -> None:
        if type(self) is not FixedGitHubApi or self in _HISTORICAL_TRANSPORTS:
            _historical_transport_poison(self)
            raise AuthorizationError("historical transport construction cannot repeat")
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
                "User-Agent": "lotto649-v13.0.0",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )
        self._commit_post_attempted = False
        self._create_ref_attempted = False
        self._last_status: int | None = None
        self._request_active = False
        self._terminal = False
        _historical_transport_register(self)

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
        try:
            result = self._request_json_checked(
                method, path, body_bytes=body_bytes, allow_absent=allow_absent
            )
            _historical_after_request(self, result)
            return result
        except BaseException:
            _historical_transport_poison(self)
            raise

    def _request_json_checked(
        self,
        method: str,
        path: str,
        *,
        body_bytes: bytes | None = None,
        allow_absent: bool = False,
    ) -> dict[str, Any] | list[dict[str, Any]] | None:
        try:
            if (
                type(method) is not str
                or type(path) is not str
                or type(allow_absent) is not bool
            ):
                raise AuthorizationError("GitHub request types differ")
            if not path.startswith(_API_PREFIX):
                raise AuthorizationError("GitHub repository route differs")
            suffix = path[len(_API_PREFIX) :]
            lease_path = "/git/ref/heads/v13-consumption-v13.0.0"
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
                raise AuthorizationError(
                    "GitHub capability does not permit this request"
                )
            _historical_before_request(self, method, suffix, body_bytes, allow_absent)
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
                    raise AuthorizationError(
                        "GitHub POST bytes are malformed"
                    ) from None
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
                    "verify": True,
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
        except BaseException:
            _historical_transport_poison(self)
            raise


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


def _tree_metadata(git: GitRepository, commit: str) -> list[dict[str, str]]:
    rows = []
    for raw in git.run("ls-tree", "-r", "-z", "--full-tree", _oid(commit)).split(b"\0"):
        if not raw:
            continue
        metadata, path = raw.split(b"\t", 1)
        mode, kind, oid = metadata.decode("ascii").split(" ")
        relative = _relative(path.decode("utf-8"))
        rows.append({"mode": mode, "type": kind, "oid": _oid(oid), "path": relative})
    return sorted(rows, key=lambda row: row["path"].encode("utf-8"))


def _registration_origin(git: GitRepository, head: str) -> str:
    additions = []
    addition = b"A\t" + REGISTRATION_PATH.encode("utf-8") + b"\n"
    for row in git.text("rev-list", "--parents", _oid(head)).splitlines():
        commit, *parents = row.split()
        for value in (commit, *parents):
            _oid(value)
        if not parents:
            if git.run("ls-tree", "-z", commit, "--", REGISTRATION_PATH):
                raise AuthorizationError("registration root introduction is prohibited")
            continue
        changes = [
            git.run(
                "diff-tree",
                "--no-commit-id",
                "--name-status",
                "--no-renames",
                "-r",
                parent,
                commit,
                "--",
                REGISTRATION_PATH,
            )
            for parent in parents
        ]
        if any(change not in {b"", addition} for change in changes):
            raise AuthorizationError("registration changed on a reachable DAG edge")
        if all(change == addition for change in changes):
            if len(parents) != 1:
                raise AuthorizationError(
                    "registration merge introduction is prohibited"
                )
            additions.append(commit)
    if additions != [R13]:
        raise AuthorizationError("unique ordinary R13 ADD authority differs")
    return R13


def _prior_accounting_metadata(git: GitRepository, head: str) -> None:
    """Authenticate prior accounting objects; never open their outcome payloads."""
    for pin in _PRIOR_ACCOUNTING_PINS:
        if not git.ancestor(pin["commit"], head):
            raise AuthorizationError("prior accounting ancestry differs")
        record = git.run("ls-tree", "-z", pin["commit"], "--", pin["path"])
        expected = (
            f"{pin['mode']} {pin['type']} {pin['git_blob']}\t{pin['path']}\0".encode()
        )
        if (
            record != expected
            or git.text("cat-file", "-t", pin["git_blob"]) != pin["type"]
            or git.text("cat-file", "-s", pin["git_blob"]) != str(pin["bytes"])
        ):
            raise AuthorizationError("prior accounting fixed object metadata differs")
        if git.oid(head, pin["path"]) != pin["git_blob"]:
            raise AuthorizationError("prior accounting object preservation differs")


def _registered_authorities(
    git: GitRepository, head: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    origin = _registration_origin(git, head)
    raw = git.read_blob(origin, REGISTRATION_PATH)
    if (
        _sha(raw) != REGISTRATION_SHA256
        or git.read_blob(head, REGISTRATION_PATH) != raw
    ):
        raise AuthorizationError("R13 sealed source bytes differ")
    seal = _json(raw)
    if raw != _canonical(seal) + b"\n" or set(seal) != {
        "schema_version",
        "experiment_id",
        "model_version",
        "status",
        "registration_base",
        "scientific_contract",
        "statistical_fingerprint_sha256",
        "operational_contract",
        "operational_contract_sha256",
        "registered_files",
        "preserved_tree_manifest",
        "preserved_tree_manifest_sha256",
        "preparation_provenance",
    }:
        raise AuthorizationError("R13 closed seal schema differs")
    science, operation = seal["scientific_contract"], seal["operational_contract"]
    if (
        _sha(_canonical(science) + b"\n") != FINGERPRINT
        or seal["statistical_fingerprint_sha256"] != FINGERPRINT
        or _sha(_canonical(operation) + b"\n") != OPERATIONAL_SHA256
        or seal["operational_contract_sha256"] != OPERATIONAL_SHA256
    ):
        raise AuthorizationError("R13 scientific or operational identity differs")
    if git.parents(origin) != (seal["registration_base"],):
        raise AuthorizationError("R13 source parent differs")
    expected_changes = {
        (status, path)
        for status, paths in _REGISTRATION_STATUSES.items()
        for path in paths
    }
    if set(git.changes(seal["registration_base"], origin)) != expected_changes:
        raise AuthorizationError(
            "R13 source must contain exactly eight registered changes"
        )
    source_authors = _source_author_provenance(
        git.run("cat-file", "commit", origin), "R13"
    )
    if source_authors != [
        {"agent_id": item["agent_id"], "session_id": item["session_id"]}
        for item in seal["preparation_provenance"]["contributors"]
    ]:
        raise AuthorizationError("R13 contributor provenance differs")
    paths = {path for _status, path in expected_changes}
    files = seal["registered_files"]
    if type(files) is not list or [item["path"] for item in files] != sorted(
        paths - {REGISTRATION_PATH}
    ):
        raise AuthorizationError("R13 seven-file seal inventory differs")
    for item in files:
        _closed_object(item, {"path", "git_blob", "bytes", "sha256"})
        content = git.read_blob(origin, item["path"])
        if (
            type(item["bytes"]) is not int
            or len(content) != item["bytes"]
            or _sha(content) != item["sha256"]
            or git.oid(origin, item["path"]) != item["git_blob"]
        ):
            raise AuthorizationError("R13 registered source file differs")
    preserved = seal["preserved_tree_manifest"]
    if _sha(_canonical(preserved) + b"\n") != seal["preserved_tree_manifest_sha256"]:
        raise AuthorizationError("R13 preservation metadata digest differs")
    baseline = [
        item
        for item in _tree_metadata(git, seal["registration_base"])
        if item["path"] not in paths
    ]
    if baseline != preserved:
        raise AuthorizationError("R13 preservation inventory differs")
    for checkpoint in (origin, head):
        observed = {item["path"]: item for item in _tree_metadata(git, checkpoint)}
        if any(observed.get(item["path"]) != item for item in preserved):
            raise AuthorizationError("preserved Git object metadata changed")
    original_paths = {item["path"] for item in _tree_metadata(git, origin)}
    forbidden = (
        set(IMPLEMENTATION_PATHS)
        | {AUTHORIZATION_PATH}
        | {"reports/" + name for name in _ARTIFACT_NAMES.values()}
    )
    if original_paths & forbidden or any(
        path.startswith(
            (
                "evidence/research_audits/v13.0.0/",
                "evidence/research_notifications/v13.0.0/",
            )
        )
        or (
            path.startswith("reports/historical-6of6-candidate__")
            and path.endswith("__v13.0.0.json")
        )
        for path in original_paths
    ):
        raise AuthorizationError("R13 contains future execution or capture artifacts")
    _prior_accounting_metadata(git, head)
    if git.text("cat-file", "-t", HISTORY_AUTHORITY) != "commit":
        raise AuthorizationError("fixed history authority is absent")
    return science, operation


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
        or phase not in {"R13", "I13", "A_H_s13"}
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
        or body["schema_version"] != "lotto649-v13-source-author-provenance-v1"
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


def _core_and_closure(
    git: GitRepository, commit: str, *, required_core_sha256: str | None = None
) -> list[dict[str, str]]:
    core = _sha(git.read_blob(commit, CORE_PATH))
    if required_core_sha256 is not None and core != _digest(required_core_sha256):
        raise AuthorizationError("I13-frozen pure-core SHA-256 differs")
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
                "lotto649-v13-i13-independent-review-v1"
                if phase == "I13"
                else "lotto649-v13-ah13-independent-review-v1"
            ),
            "axis": record["axis"],
            "base_sha": base,
            "head_sha": implementation,
            "closure_sha256": closure_sha256,
            "operational_contract_sha256": OPERATIONAL_SHA256,
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
        if (
            body.encode("utf-8") != _canonical(attestation) + b"\n"
            or attestation != expected
            or not all(
                type(expected[key]) is str and expected[key]
                for key in ("reviewer_agent_id", "review_session_id", "publisher_login")
            )
        ):
            raise AuthorizationError(
                "review body does not bind the complete reviewed source"
            )


def _verify_registered_numerics(science: Mapping[str, Any]) -> None:
    """Run frozen scalar/hex closed-math oracles, never a history forecast."""
    import math

    from .models.v13_main_set_overlap import (
        map_objective,
        map_score,
        moments,
        solve_map_beta,
    )

    oracles = science["literal_oracles"]["closed_math"]
    if len(oracles["moment_oracles"]) != 4 or len(oracles["root_oracles"]) != 9:
        raise AuthorizationError("registered scalar oracle inventory differs")
    for oracle in (*oracles["moment_oracles"], *oracles["root_oracles"]):
        expected = oracle["outputs"]
        counts = None
        if "counts_run_length" in oracle:
            counts = tuple(
                value["value"]
                for value in oracle["counts_run_length"]
                for _ in range(value["count"])
            )
            if len(counts) != oracle["D"] or sum(counts) != oracle["Ksum"]:
                raise AuthorizationError("registered oracle integer projection differs")
            beta = solve_map_beta(counts)
        else:
            beta = float.fromhex(expected["beta"]["hex"])
        mean, complement, log_z = moments(beta)
        p_in = 6.0 / 49.0 if beta == 0.0 else mean / 6.0
        p_out = 6.0 / 49.0 if beta == 0.0 else complement / 43.0
        observed = {
            "beta": beta,
            "mean": mean,
            "complement_mean": complement,
            "log_z": log_z,
            "p_in": p_in,
            "p_out": p_out,
            "expected_six": math.fsum([p_in] * 6 + [p_out] * 43),
        }
        if counts is not None:
            observed["score_at_root"] = map_score(beta, counts)
            observed["objective_at_root"] = map_objective(beta, counts)
        if set(observed) != set(expected) or any(
            type(value) is not float
            or value.hex() != expected[key]["hex"]
            or value != expected[key]["decimal"]
            for key, value in observed.items()
        ):
            raise AuthorizationError("registered binary64 scalar/hex oracle differs")


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
    if git.parents(implementation) != (implementation_base,):
        raise AuthorizationError("I13 must be one ordinary child of its exact base")
    if (
        not git.ancestor(R13, implementation_base)
        or merge != base
        or implementation == base
        or not git.ancestor(implementation, base)
    ):
        raise AuthorizationError("R13/I13/K_H13 order differs")
    if set(git.changes(implementation_base, implementation)) != {
        ("A", path) for path in IMPLEMENTATION_PATHS
    }:
        raise AuthorizationError("I13 must add exactly the eight registered paths")
    closure = _core_and_closure(git, implementation)
    implementation_files = _implementation_manifest(git, implementation)
    if _implementation_manifest(git, base) != implementation_files:
        raise AuthorizationError("registered implementation files drifted")
    if _core_and_closure(git, base) != closure:
        raise AuthorizationError("historical closure drift after I13")
    _verify_worktree_runtime(git, base, closure)
    _verify_registered_numerics(r1)
    _remote_protection(api)
    if _remote_main(api) != base:
        raise AuthorizationError("K_H13 is not current protected remote main")
    _verify_reviews(
        api,
        review_records,
        implementation=implementation,
        merge=merge,
        base=implementation_base,
        closure_sha256=_sha(_canonical(closure)),
        git=git,
        phase="I13",
    )
    return {
        "schema_version": "lotto649-v13.0.0-historical-authorization-v1",
        "experiment_id": r3["identity"]["experiment_id"],
        "model_version": "v13.0.0",
        "repository": REPOSITORY,
        "branch": "main",
        "registration_commit": R13,
        "registration_sha256": _sha(git.read_blob(R13, REGISTRATION_PATH)),
        "scientific_registration_commit": R13,
        "statistical_fingerprint_sha256": FINGERPRINT,
        "operational_contract_sha256": OPERATIONAL_SHA256,
        "pure_core_sha256": _sha(git.read_blob(implementation, CORE_PATH)),
        "implementation_commit": implementation,
        "implementation_base": implementation_base,
        "implementation_merge": merge,
        "authorization_base": base,
        "canonical_command": COMMAND,
        "governed_history_authority": HISTORY_AUTHORITY,
        "governed_history_identity": r3["identity"]["governed_history_identity"],
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
            body.get("schema_version") != "lotto649-v13-ah13-independent-review-v1"
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
        "execution_authority_M_A_H13": facts.execution_commit,
        "registration_R13": R13,
        "source_A_H_s13": facts.source_commit,
        "implementation_commit": facts.payload["implementation_commit"],
        "authorization_base": facts.payload["authorization_base"],
        "registration_sha256": facts.payload["registration_sha256"],
        "config_sha256": _sha(
            GitRepository(facts.repository).read_blob(R13, CONFIG_PATH)
        ),
        "authorization_sha256": facts.authorization_sha256,
        "historical_runtime_dependency_closure_sha256": facts.payload[
            "runtime_dependency_closure_sha256"
        ],
        "runtime_identity_sha256": _sha(_canonical(facts.payload["runtime"])),
        "requirements_sha256": REQUIREMENTS_SHA256,
        "required_pure_core_sha256": facts.payload["pure_core_sha256"],
        "statistical_fingerprint_sha256": FINGERPRINT,
        "operational_contract_sha256": OPERATIONAL_SHA256,
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
    if raw != _canonical(authorization) + b"\n":
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
        "operational_contract_sha256",
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
        "schema_version": "lotto649-v13.0.0-historical-authorization-v1",
        "experiment_id": r3["identity"]["experiment_id"],
        "model_version": "v13.0.0",
        "repository": REPOSITORY,
        "branch": "main",
        "registration_commit": R13,
        "scientific_registration_commit": R13,
        "registration_sha256": _sha(git.read_blob(R13, REGISTRATION_PATH)),
        "statistical_fingerprint_sha256": FINGERPRINT,
        "operational_contract_sha256": OPERATIONAL_SHA256,
        "canonical_command": COMMAND,
        "governed_history_authority": HISTORY_AUTHORITY,
        "governed_history_identity": r3["identity"]["governed_history_identity"],
        "runtime": runtime_identity(),
    }
    if any(authorization[key] != value for key, value in required.items()):
        raise AuthorizationError("authorization fixed identity differs")
    implementation = _oid(authorization["implementation_commit"])
    if _sha(git.read_blob(implementation, CORE_PATH)) != _digest(
        authorization["pure_core_sha256"]
    ):
        raise AuthorizationError("I13 core binding differs")
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
            "authorization source must be an auth-only child of K_H13"
        )
    _require_normal_merge(
        git, implementation_merge, implementation_base, implementation
    )
    if git.parents(implementation) != (implementation_base,):
        raise AuthorizationError("I13 must be one ordinary child of its exact base")
    if (
        set(git.changes(implementation_base, implementation))
        != {("A", path) for path in IMPLEMENTATION_PATHS}
        or not git.ancestor(R13, implementation_base)
        or implementation_merge != base
        or implementation == base
    ):
        raise AuthorizationError("complete registered I13 ancestry is required")
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
        if (
            _core_and_closure(
                git, checkpoint, required_core_sha256=authorization["pure_core_sha256"]
            )
            != closure
        ):
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
        phase="I13",
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
        phase="A_H_s13",
    )
    _verify_worktree_runtime(git, head, closure)
    _verify_registered_numerics(r1)
    return _issue_verified_facts(
        repository, head, source, authorization, _sha(raw), auth_reviews
    )


def _verify_worktree_runtime(
    git: GitRepository, head: str, closure: Sequence[Mapping[str, str]]
) -> None:
    runtime_identity()
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
                "schema_version": "lotto649-v13-consumption-lease-v1",
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
        "LOTTO649 V13 Consumption Lease <lotto649-v13-lease@users.noreply.github.com>"
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
        "name": "LOTTO649 V13 Consumption Lease",
        "email": "lotto649-v13-lease@users.noreply.github.com",
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

_STARTUP_SCHEMA = "lotto649-v13.0.0-historical-startup-v1"
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
        "execution_authority_M_A_H13",
        "registration_R13",
        "source_A_H_s13",
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
        "operational_contract_sha256",
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
        instant = datetime.fromisoformat(timestamp)
        if state["last_instant"] is not None and instant < state["last_instant"]:
            _startup_fail(state, "startup_clock_moved_backward")
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
        state["last_instant"] = instant
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
                "last_instant": None,
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
        if identity["execution_authority_M_A_H13"] != head:
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
    try:
        _require_authorization_capability(authority, consume=True)
        _bind_historical_transport(api, authority)
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
            _API_PREFIX + "/git/ref/heads/v13-consumption-v13.0.0",
            allow_absent=True,
        )
        if (
            absence is not None
            or type(api.last_status) is not int
            or api.last_status != 404
        ):
            raise AttemptError(
                "the immutable attempt lease exists or absence is ambiguous"
            )
        startup = authority.startup
        startup.append("lease_absence_confirmed", {"http_status": 404})
        nonce = secrets.token_hex(32)
        oid, raw, payload = _plan_historical_transport(api, authority, nonce)
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
        reread = _required_response(api, "/git/ref/heads/v13-consumption-v13.0.0")
        _verify_lease_ref(reread, oid)
        _remote_protection(api)
        if _remote_main(api) != authority.execution_commit:
            raise AttemptError("main moved after lease; no retry")
        git.require_full_clean(authority=authority)
        startup.append("lease_ref_reread_verified", {"validated_oid": oid})
        _complete_historical_transport(api, authority)
        return _issue_lease(authority, oid, nonce)
    except BaseException:
        _historical_transport_poison(api)
        raise


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


# Historical source origin: /root/i3_transport,
# i3-artifact-ownership-authoring-20260913, in reviewed V12.0.2 mechanics.
# V13 adaptation: /root/v13_attempt_draft, v13-attempt-draft-authoring-20260913.
# Uses the registered startup fragment's _startup_directory_chain and import stat.

_ARTIFACT_OWNERS: dict[object, dict[str, Any]] = {}
_ARTIFACT_PUBLICATIONS = frozenset(
    {
        ("json_staging", "json"),
        ("markdown_staging", "markdown"),
        ("manifest_staging", "manifest"),
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


def _ledger_payload(kind: str, payload: Mapping[str, Any], *, synthetic: bool) -> None:
    if type(kind) is not str or type(payload) is not dict:
        raise AttemptError("ledger closed event type differs")
    if synthetic and kind in {"synthetic_attempt_claimed", "synthetic_fixture_event"}:
        expected = (
            {"claim_sha256"} if kind == "synthetic_attempt_claimed" else {"value"}
        )
    else:
        if kind not in _LEDGER_PAYLOAD_KEYS:
            raise AttemptError("unregistered scientific ledger event")
        expected = set(_LEDGER_PAYLOAD_KEYS[kind])
    if set(payload) != expected:
        raise AttemptError("scientific ledger payload schema differs")
    _canonical(payload)
    if kind == "attempt_archived" and (
        payload["reason"]
        not in {
            "source_integrity_failure",
            "runtime_failure",
            "chronology_failure",
            "numerical_failure",
            "io_failure",
            "worker_failure",
        }
        or payload["retry_allowed"] is not False
    ):
        raise AttemptError("scientific ledger archive values differ")
    if kind in {
        "historical_6of6_candidate_detected",
        "historical_top12_all_six_detected",
    }:
        if payload["eligible_evidence"] is not False:
            raise AttemptError("capture cannot precede independent audit")
        if kind == "historical_6of6_candidate_detected" and (
            payload["audit_status"] != "independent_leakage_audit_pending"
            or payload["global_stop_search"] is not True
        ):
            raise AttemptError("capture must freeze Goal search pending audit")
    for key in (
        "claim_sha256",
        "forecast_payload_sha256",
        "prediction_frozen_event_sha256",
    ):
        if key in payload:
            _digest(payload[key])
    if "target_draw_date" in payload:
        value = payload["target_draw_date"]
        if type(value) is not str or date.fromisoformat(value).isoformat() != value:
            raise AttemptError("scientific ledger target date differs")
    if kind == "prediction_frozen":
        from .v13_evidence import validate_frozen_payload

        raw = _canonical(payload["forecast_payload"]) + b"\n"
        validate_frozen_payload(raw)
        if _sha(raw) != payload["forecast_payload_sha256"]:
            raise AttemptError("scientific ledger frozen digest differs")


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
        _ledger_payload(
            kind,
            dict(payload),
            synthetic=self._bindings.get("classification") == "synthetic_fixture_only"
            or self._bindings.get("fixture") is True,
        )
        event = {
            "schema_version": "lotto649-v13.0.0-attempt-ledger-v1",
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


def _ledger_expected_detection(
    payload: Mapping[str, Any],
) -> tuple[str, dict[str, Any]] | None:
    """Check discrete capture facts from the stored cohort, without any model call.

    Proper scores and independent leakage review remain separate evidence checks.
    This verifies only the main-label membership and producer identities needed to
    establish the ledger's mandatory next event and stopping state.
    """
    actual = payload["actual"]
    if (
        type(actual) is not list
        or len(actual) != 6
        or any(type(label) is not int or not 1 <= label <= 49 for label in actual)
        or actual != sorted(set(actual))
    ):
        raise AttemptError("scored main labels are invalid")
    bonus = payload["bonus"]
    if bonus is not None and (
        type(bonus) is not int or not 1 <= bonus <= 49 or bonus in actual
    ):
        raise AttemptError("scored bonus is invalid")
    actual_set = set(actual)
    forecasts = payload["forecast_payload"]["forecasts"]
    scores = payload["scores"]
    if type(scores) is not list or len(scores) != len(forecasts):
        raise AttemptError("scored producer inventory differs")
    unique: dict[tuple[int, ...], dict[str, Any]] = {}
    top12 = []
    for forecast, score in zip(forecasts, scores, strict=True):
        if type(score) is not dict:
            raise AttemptError("scored producer record differs")
        name = forecast["model_name"]
        digest = _sha(_canonical(forecast) + b"\n")
        matches = sorted(actual_set & set(forecast["final6"]))
        expected = {
            "model_name": name,
            "model_version": forecast["model_version"],
            "forecast_sha256": digest,
            "top6_hits": len(actual_set & set(forecast["top6"])),
            "top12_hits": len(actual_set & set(forecast["top12"])),
            "top18_hits": len(actual_set & set(forecast["top18"])),
            "final6_hits": len(matches),
            "matched_final6": matches,
        }
        if not set(expected).issubset(score) or _canonical(
            {key: score[key] for key in expected}
        ) != _canonical(expected):
            raise AttemptError("scored capture membership differs from frozen cohort")
        if expected["top12_hits"] == 6:
            top12.append(name)
        ticket = tuple(forecast["final6"])
        if ticket not in unique:
            unique[ticket] = {
                "final6": list(ticket),
                "primary_producer": name,
                "producer_model_names": [],
                "forecast_sha256_by_producer": {},
                "hits": len(matches),
            }
        unique[ticket]["producer_model_names"].append(name)
        unique[ticket]["forecast_sha256_by_producer"][name] = digest
    opportunities = list(unique.values())
    exact = [entry for entry in opportunities if entry["hits"] == 6]
    for key, expected_value in (
        ("unique_final6", opportunities),
        ("unique_opportunity_count", len(opportunities)),
        ("exact_final6_opportunities", exact),
        ("top12_all_six_producers", top12),
    ):
        if _canonical(payload[key]) != _canonical(expected_value):
            raise AttemptError("scored opportunity or producer grouping differs")
    identity = {
        "target_draw_date": payload["target_draw_date"],
        "forecast_payload_sha256": payload["forecast_payload_sha256"],
    }
    if exact:
        return "historical_6of6_candidate_detected", {
            **identity,
            "opportunities": exact,
            "audit_status": "independent_leakage_audit_pending",
            "eligible_evidence": False,
            "global_stop_search": True,
        }
    if top12:
        return "historical_top12_all_six_detected", {
            **identity,
            "producers": top12,
            "eligible_evidence": False,
        }
    return None


def audit_ledger(path: Path) -> dict[str, Any]:
    """Bind stored receipts and mandatory capture phases; never refit or repair."""
    raw = path.read_bytes()
    if not raw or not raw.endswith(b"\n"):
        raise AttemptError("incomplete durable ledger")
    previous = "0" * 64
    pending: dict[str, Any] | None = None
    expected_detection: tuple[str, dict[str, Any]] | None = None
    count = 0
    stopped = False
    capture_detected = False
    bindings: object = None
    targets: set[str] = set()
    previous_target: date | None = None
    for number, line in enumerate(raw.splitlines()):
        event = _json(line)
        if (
            set(event)
            != {
                "schema_version",
                "sequence",
                "recorded_at",
                "previous_event_sha256",
                "event_kind",
                "bindings",
                "payload",
                "event_sha256",
            }
            or event["schema_version"] != "lotto649-v13.0.0-attempt-ledger-v1"
            or type(event["sequence"]) is not int
            or type(event["bindings"]) is not dict
        ):
            raise AttemptError("scientific ledger envelope schema differs")
        _valid_utc(event["recorded_at"])
        try:
            _ledger_payload(
                event["event_kind"],
                event["payload"],
                synthetic=event["bindings"].get("classification")
                == "synthetic_fixture_only"
                or event["bindings"].get("fixture") is True,
            )
        except (KeyError, TypeError, ValueError):
            raise AttemptError("scientific ledger payload values differ") from None
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
        kind, payload = event["event_kind"], event["payload"]
        if stopped:
            raise AttemptError(
                "scientific ledger continued after terminal capture/archive"
            )
        if number == 0 and kind not in {
            "attempt_claimed",
            "synthetic_attempt_claimed",
            "synthetic_fixture_event",
        }:
            raise AttemptError("scientific ledger must begin with the permanent claim")
        if number > 0 and kind in {"attempt_claimed", "synthetic_attempt_claimed"}:
            raise AttemptError("scientific ledger cannot repeat its claim")
        if expected_detection is not None:
            if kind != expected_detection[0] or _canonical(payload) != _canonical(
                expected_detection[1]
            ):
                raise AttemptError(
                    "mandatory capture record differs from just-scored cohort"
                )
            capture_detected = kind == "historical_6of6_candidate_detected"
            stopped = capture_detected
            expected_detection = None
            continue
        if kind in {
            "historical_6of6_candidate_detected",
            "historical_top12_all_six_detected",
        }:
            raise AttemptError("capture lacks its exact immediately scored cohort")
        if kind == "prediction_frozen":
            if pending is not None:
                raise AttemptError("forecast ordering violated")
            frozen = payload["forecast_payload"]
            if type(frozen) is not dict or _canonical(frozen["bindings"]) != _canonical(
                bindings
            ):
                raise AttemptError("forecast payload or bindings differ")
            digest = _sha(_canonical(frozen) + b"\n")
            target = frozen["target_draw_date"]
            if target in targets or payload["forecast_payload_sha256"] != digest:
                raise AttemptError("duplicate forecast or incorrect payload digest")
            target_date = date.fromisoformat(target)
            if previous_target is not None and target_date <= previous_target:
                raise AttemptError("ledger targets are not strictly chronological")
            previous_target = target_date
            if date.fromisoformat(frozen["history_through"]) >= target_date:
                raise AttemptError("forecast chronology violated")
            targets.add(target)
            pending = {
                "target_draw_date": target,
                "forecast_payload_sha256": digest,
                "forecast_payload": frozen,
                "prediction_generated_at": event["recorded_at"],
                "prediction_frozen_event_sequence": number,
                "prediction_frozen_event_sha256": recorded_digest,
            }
        elif kind == "target_revealed_scored":
            if (
                pending is None
                or number != pending["prediction_frozen_event_sequence"] + 1
                or _canonical({key: payload[key] for key in pending})
                != _canonical(pending)
            ):
                raise AttemptError(
                    "reveal lacks preceding exact frozen forecast receipt"
                )
            expected_detection = _ledger_expected_detection(payload)
            pending = None
            count += 1
        elif kind == "attempt_archived":
            stopped = True
    if expected_detection is not None:
        raise AttemptError("incomplete durable capture record after scored cohort")
    return {
        "event_count": len(raw.splitlines()),
        "scored_target_count": count,
        "head_sha256": previous,
        "pending_forecast": pending is not None,
        "stopped_for_audit": capture_detected,
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
    synthetic: bool,
) -> tuple[list[dict[str, Any]], list[str], str | None]:
    from .domain import Draw
    from .v13_evidence import (
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
            "schema_version": "lotto649-v13.0.0-frozen-forecast-v1",
            "classification": "synthetic_fixture_only"
            if synthetic
            else "consumed_historical_diagnostic_only",
            "model_version": "v13.0.0",
            "target_draw_date": target.isoformat(),
            "history_through": history_through,
            "training_cutoff_date": history_through,
            "visible_prefix_sha256": prefix_digest,
            "visible_prefix_draw_count": len(prefix),
            "bindings": dict(bindings),
            "forecasts": [dict(item) for item in predictions],
            "forecast_sha256_by_model": {
                item["model_name"]: _sha(canonical_json_bytes(dict(item)))
                for item in predictions
            },
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
                    "global_stop_search": True,
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
    from .v13_evidence import build_report, canonical_json_bytes, render_markdown

    audit = audit_ledger(paths["ledger"])
    complete = (
        stop_reason is None
        and not warnings
        and audit["scored_target_count"] == len(rows)
        and not audit["pending_forecast"]
    )
    report_bindings = dict(bindings)
    report = build_report(
        rows,
        report_bindings,
        audit_complete=complete,
        audit_warnings=tuple(warnings),
        stop_reason=stop_reason,
    )
    report["claim_sha256"] = _sha(paths["claim"].read_bytes())
    report["ledger"] = audit
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
            "report_path_after_audit": f"{prefix}__{target}__{producer}__v13.0.0.json",
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
            R13,
            R13,
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
    _exclusive_bytes(root / ".synthetic-v13", b"synthetic_fixture_only\n")
    return root


def run_synthetic_attempt(
    output_root: Path,
    targets: Sequence[date],
    prefix_for: Callable[[date], Sequence[Any]],
    reveal: Callable[[date], Any],
    forecast: Callable[[Sequence[Any], date], Sequence[Mapping[str, Any]]],
    *,
    bindings: Mapping[str, Any],
) -> dict[str, Any]:
    """Synthetic-only ordering seam; cannot acquire authority or write Git."""
    directory = _synthetic_root(output_root, bindings)
    paths = _paths(directory, synthetic=True)
    identity = {
        "classification": "synthetic_fixture_only",
        "synthetic_only": True,
        **dict(bindings),
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
            "schema_version": "lotto649-v13-synthetic-artifacts-v1",
            "classification": "synthetic_fixture_only",
            "files": {
                paths[key].name: _sha(paths[key].read_bytes())
                for key in ("claim", "ledger", "json", "markdown")
            },
            "git_commit": None,
        }
        _publish_exclusive(
            paths["manifest_staging"], paths["manifest"], _canonical(manifest) + b"\n"
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
        identity = next(
            item for item in registration["scope"]["scopes"] if item["id"] == name
        )
        if (
            len(dates) != identity["count"]
            or _sha(raw) != identity["target_dates_sha256"]
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
    files = sorted(files, key=lambda entry: entry["path"])
    manifest = {
        "schema_version": "lotto649-v13.0.0-report-commit-manifest-v1",
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
    owner.publish("manifest_staging", "manifest", _canonical(manifest) + b"\n")
    raw = paths["manifest"].read_bytes()
    files.append(
        {
            "path": paths["manifest"].relative_to(git.root).as_posix(),
            "git_blob": _oid(
                git.run("hash-object", "-w", "--stdin", input_bytes=raw)
                .decode()
                .strip()
            ),
        }
    )
    # The frozen macOS runtime has the fixed OS /tmp namespace. No environment,
    # caller index, or alternate temp-root fallback selects this private workspace.
    temporary = Path(_ARTIFACT_INDEX_OS_TEMP).resolve()
    execution_root = git.root.resolve()
    if temporary == execution_root or execution_root in temporary.parents:
        raise AttemptError("artifact index must be outside the execution clone")
    index = temporary / ("lotto649-v13-artifact-index-" + secrets.token_hex(16))
    parent_fd, ancestors = _startup_directory_chain(temporary)
    descriptor = -1
    index_identity: tuple[int, int, int, str] | None = None
    environment = _git_environment()
    environment["GIT_INDEX_FILE"] = str(index)

    def current_index_identity() -> tuple[int, int, int, str]:
        for directory, device, inode in ancestors:
            observed = directory.lstat()
            if (
                not stat.S_ISDIR(observed.st_mode)
                or (observed.st_dev, observed.st_ino) != (device, inode)
                or (observed.st_mode & 0o022 and not observed.st_mode & stat.S_ISVTX)
            ):
                raise AttemptError("artifact index directory ownership differs")
        opened = os.open(index.name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent_fd)
        try:
            observed = os.fstat(opened)
            named = os.stat(index.name, dir_fd=parent_fd, follow_symlinks=False)
            if (
                not stat.S_ISREG(observed.st_mode)
                or stat.S_IMODE(observed.st_mode) != 0o600
                or observed.st_nlink != 1
                or (named.st_dev, named.st_ino) != (observed.st_dev, observed.st_ino)
            ):
                raise AttemptError("artifact index file ownership differs")
            raw_index = os.pread(opened, observed.st_size + 1, 0)
            if len(raw_index) != observed.st_size:
                raise AttemptError("artifact index changed while reading")
            return observed.st_dev, observed.st_ino, observed.st_size, _sha(raw_index)
        finally:
            os.close(opened)

    def index_git(*arguments: str, input_bytes: bytes | None = None) -> bytes:
        nonlocal index_identity
        if current_index_identity() != index_identity:
            raise AttemptError("artifact index changed outside its Git operation")
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
                umask=0o077,
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
        # Git exclusively creates index.lock then replaces its own index inode.
        # Only this successful registered operation can advance the local receipt;
        # an exception/nonzero result never authorizes adoption or cleanup.
        index_identity = current_index_identity()
        return result.stdout

    try:
        descriptor = os.open(
            index.name,
            os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=parent_fd,
        )
        observed = os.fstat(descriptor)
        if (
            not stat.S_ISREG(observed.st_mode)
            or stat.S_IMODE(observed.st_mode) != 0o600
            or observed.st_nlink != 1
        ):
            raise AttemptError("artifact index creation mode differs")
        # A valid empty Git index permits exclusive creation without deleting an
        # empty placeholder before Git's first read-tree operation.
        header = b"DIRC\x00\x00\x00\x02\x00\x00\x00\x00"
        empty_index = header + hashlib.sha1(header).digest()
        if os.write(descriptor, empty_index) != len(empty_index):
            raise AttemptError("artifact index short write; no retry")
        os.fsync(descriptor)
        os.fsync(parent_fd)
        index_identity = current_index_identity()
        if index_identity[:2] != (observed.st_dev, observed.st_ino):
            raise AttemptError("artifact index creation ownership differs")
        os.close(descriptor)
        descriptor = -1
        index_git("read-tree", authority.execution_commit)
        entries = b"".join(
            f"100644 {entry['git_blob']}\t{entry['path']}\0".encode() for entry in files
        )
        index_git("update-index", "-z", "--index-info", input_bytes=entries)
        tree = _oid(index_git("write-tree").decode().strip())
        now = int(datetime.now(UTC).timestamp())
        identity = "LOTTO649 V13 Historical Evidence <lotto649-v13-evidence@users.noreply.github.com>"
        message = b"Record immutable V13.0.0 consumed historical diagnostic artifacts\n"
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
        if current_index_identity() != index_identity:
            raise AttemptError("successful artifact index ownership differs")
        os.unlink(index.name, dir_fd=parent_fd)
        return commit
    finally:
        # Failed/uncertain construction preserves this index and any Git lock;
        # no cleanup, retry, or adoption can occur in the failure path.
        if descriptor >= 0:
            os.close(descriptor)
        os.close(parent_fd)


def _run_canonical(authority: VerifiedAuthorization, lease: Lease) -> dict[str, Any]:
    _consume_lease(authority, lease)
    from .v13_evidence import four_forecasts

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
        "execution_authority_M_A_H13": authority.execution_commit,
        "authorization_source_A_H_s13": authority.source_commit,
        "authorization_sha256": authority.authorization_sha256,
        "lease_ref": lease.ref,
        "lease_commit_L_H13": lease.commit,
        "nonce_hex": lease.nonce_hex,
        "seed": 649,
        "classification": "consumed_historical_diagnostic_only",
    }
    owner.create_bytes(
        "claim",
        _canonical(
            {
                "verified_authorization_facts": facts_preimage,
                "schema_version": "lotto649-v13.0.0-permanent-claim-v1",
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
        r13 = _json(git.read_blob(R13, REGISTRATION_PATH))
        targets = _target_dates(history, r13["scientific_contract"])
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
            "attempt_archived", {"reason": "worker_failure", "retry_allowed": False}
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


# V13 notification protocol author: /root/v13_attempt_draft,
# session v13-attempt-draft-authoring-20260913. No production notification has run.
_NOTIFICATION_REF = "refs/heads/v13-notification-v13.0.0"
_NOTIFICATION_KIND = "audited_historical_final6_exact6"
_NOTIFICATION_PHASES = (
    "notification_intent_frozen",
    "notification_commit_POST_intent",
    "notification_commit_POST_receipt",
    "notification_commit_GET_verified",
    "notification_ref_POST_intent",
    "notification_ref_POST_receipt",
    "notification_ref_reread_verified",
    "notification_send_intent",
    "notification_send_result",
)
_NOTIFICATION_KEYS = {
    "notification_intent_frozen": {
        "intent_sha256",
        "intent_identity_sha256",
        "expected_claim_oid",
        "audited_publication_commit",
        "absence_http_status",
    },
    "notification_commit_POST_intent": {
        "phase_enum",
        "nonce_hex",
        "expected_claim_oid",
        "raw_commit_sha256",
        "request_body_bytes",
        "request_body_sha256",
    },
    "notification_commit_POST_receipt": {
        "phase_enum",
        "result_enum",
        "http_status",
        "validated_oid",
    },
    "notification_commit_GET_verified": {"validated_oid"},
    "notification_ref_POST_intent": {
        "phase_enum",
        "nonce_hex",
        "expected_claim_oid",
        "raw_commit_sha256",
        "request_body_bytes",
        "request_body_sha256",
    },
    "notification_ref_POST_receipt": {
        "phase_enum",
        "result_enum",
        "http_status",
        "validated_oid",
    },
    "notification_ref_reread_verified": {"validated_oid", "remote_main_oid"},
    "notification_send_intent": {
        "validated_oid",
        "intent_sha256",
        "audited_publication_commit",
        "notification_kind",
    },
    "notification_send_result": {"result_enum"},
}
_NOTIFICATION_IDENTITY_KEYS = {
    "experiment_id",
    "model_version",
    "target_draw_date",
    "notification_kind",
    "candidate_bundle_path",
    "candidate_bundle_sha256",
    "audit_json_path",
    "audit_json_sha256",
    "audited_publication_commit",
    "publication_tree_oid",
    "scientific_contract_sha256",
    "operational_contract_sha256",
    "nonce_hex",
}
_NOTIFICATION_CLAIM_KEYS = {
    "schema_version",
    "experiment_id",
    "model_version",
    "target_draw_date",
    "notification_kind",
    "audited_publication_commit",
    "audit_json_sha256",
    "candidate_bundle_sha256",
    "intent_identity_sha256",
    "operational_contract_sha256",
    "nonce_hex",
}
_NOTIFICATION_STATES: dict[object, dict[str, Any]] = {}
_SYNTHETIC_NOTIFICATION_REF = "refs/heads/synthetic-v13-notification-fixture"


def _valid_utc(value: object) -> datetime:
    if (
        type(value) is not str
        or re.fullmatch(
            r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?Z",
            value,
        )
        is None
    ):
        raise AttemptError("invalid trusted UTC time")
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        raise AttemptError("invalid trusted UTC time") from None


def _notification_request_parts(
    payload: object, *, synthetic: bool = False
) -> tuple[str, bytes, str]:
    """Closed purpose-specific object projection; no historical lease capability."""
    request = _closed_object(
        payload, {"tree", "parents", "author", "committer", "message"}
    )
    tree = _oid(request["tree"])
    parents = request["parents"]
    if type(parents) is not list or len(parents) != 1:
        raise AuthorizationError("notification claim must have one parent")
    parent = _oid(parents[0])
    author = _closed_object(request["author"], {"name", "email", "date"})
    committer = _closed_object(request["committer"], {"name", "email", "date"})
    name = "LOTTO649 V13 Notification Claim"
    email = "lotto649-v13-notification@users.noreply.github.com"
    if author != committer or author["name"] != name or author["email"] != email:
        raise AuthorizationError("notification author identity differs")
    instant = _valid_utc(author["date"])
    if instant.microsecond or len(author["date"]) != 20:
        raise AuthorizationError("notification claim requires whole-second metadata")
    message = request["message"]
    if type(message) is not str or not message.endswith("\n"):
        raise AuthorizationError("notification claim POST message differs")
    body = _json(message.encode("utf-8"))
    _closed_object(body, _NOTIFICATION_CLAIM_KEYS)
    if message.encode("utf-8") != _canonical(body) + b"\n":
        raise AuthorizationError("notification body must be C plus one LF")
    fixed_experiment = (
        "synthetic_v13_capture" if synthetic else "V13_post_rng_main_set_overlap"
    )
    fixed_version = "synthetic_fixture_only" if synthetic else "v13.0.0"
    if (
        body["schema_version"] != "lotto649-v13.0.0-notification-claim-v1"
        or body["experiment_id"] != fixed_experiment
        or body["model_version"] != fixed_version
        or body["notification_kind"] != _NOTIFICATION_KIND
        or body["audited_publication_commit"] != parent
    ):
        raise AuthorizationError("notification claim purpose differs")
    if (
        type(body["target_draw_date"]) is not str
        or date.fromisoformat(body["target_draw_date"]).isoformat()
        != body["target_draw_date"]
    ):
        raise AuthorizationError("notification capture date differs")
    for key in (
        "audit_json_sha256",
        "candidate_bundle_sha256",
        "intent_identity_sha256",
        "operational_contract_sha256",
        "nonce_hex",
    ):
        _digest(body[key])
    if not synthetic and body["operational_contract_sha256"] != OPERATIONAL_SHA256:
        raise AuthorizationError("notification operational binding differs")
    who = f"{name} <{email}> {int(instant.timestamp())} +0000"
    raw = (
        f"tree {tree}\nparent {parent}\nauthor {who}\ncommitter {who}\n\n" + message
    ).encode("utf-8")
    oid = hashlib.sha1(
        b"commit " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()
    return oid, raw, message[:-1]


def _verify_notification_post(
    expected: str,
    request: Mapping[str, Any],
    observed: object,
    *,
    synthetic: bool = False,
) -> None:
    oid, _raw, _message = _notification_request_parts(request, synthetic=synthetic)
    if oid != expected:
        raise AuthorizationError("notification local raw identity differs")
    value = _closed_object(
        observed,
        {"sha"},
        {
            "node_id",
            "url",
            "html_url",
            "author",
            "committer",
            "tree",
            "parents",
            "message",
            "verification",
        },
    )
    _exact_string(value["sha"], expected)
    for key in value:
        if key == "sha":
            continue
        if key == "message":
            if type(value[key]) is not str:
                raise AuthorizationError("notification POST metadata type differs")
        else:
            _verify_lease_metadata(key, value[key], expected, request)


def _verify_notification_get(
    expected: str,
    request: Mapping[str, Any],
    response: object,
    *,
    synthetic: bool = False,
) -> None:
    oid, _raw, projected = _notification_request_parts(request, synthetic=synthetic)
    if oid != _oid(expected):
        raise AuthorizationError("notification local content address differs")
    value = _closed_object(
        response,
        {
            "sha",
            "node_id",
            "url",
            "html_url",
            "author",
            "committer",
            "tree",
            "parents",
            "message",
            "verification",
        },
    )
    _exact_string(value["sha"], expected)
    _exact_string(value["message"], projected)
    for key in (
        "node_id",
        "url",
        "html_url",
        "author",
        "committer",
        "tree",
        "parents",
        "verification",
    ):
        _verify_lease_metadata(key, value[key], expected, request)


def _notification_claim_request(
    identity: Mapping[str, Any], committer_time: str, *, synthetic: bool = False
) -> tuple[dict[str, Any], str, bytes]:
    _closed_object(identity, _NOTIFICATION_IDENTITY_KEYS)
    identity_digest = _sha(_canonical(identity) + b"\n")
    body = {
        "schema_version": "lotto649-v13.0.0-notification-claim-v1",
        "experiment_id": identity["experiment_id"],
        "model_version": identity["model_version"],
        "target_draw_date": identity["target_draw_date"],
        "notification_kind": identity["notification_kind"],
        "audited_publication_commit": identity["audited_publication_commit"],
        "audit_json_sha256": identity["audit_json_sha256"],
        "candidate_bundle_sha256": identity["candidate_bundle_sha256"],
        "intent_identity_sha256": identity_digest,
        "operational_contract_sha256": identity["operational_contract_sha256"],
        "nonce_hex": identity["nonce_hex"],
    }
    person = {
        "name": "LOTTO649 V13 Notification Claim",
        "email": "lotto649-v13-notification@users.noreply.github.com",
        "date": committer_time,
    }
    request = {
        "tree": identity["publication_tree_oid"],
        "parents": [identity["audited_publication_commit"]],
        "author": person,
        "committer": dict(person),
        "message": (_canonical(body) + b"\n").decode("utf-8"),
    }
    expected, raw, _message = _notification_request_parts(request, synthetic=synthetic)
    return request, expected, raw


class _NotificationInvocation:
    """Only an issuing verifier may create a same-process notification context."""

    def __new__(cls, *args: Any, **kwargs: Any) -> Any:
        raise AuthorizationError("notification capability is not constructible")


def _notification_state(
    invocation: object, *, allow_sealed: bool = False
) -> dict[str, Any]:
    if (
        type(invocation) is not _NotificationInvocation
        or invocation not in _NOTIFICATION_STATES
    ):
        raise AttemptError("notification capability unissued")
    state = _NOTIFICATION_STATES[invocation]
    if state["closed"] or state["poisoned"] or (state["sealed"] and not allow_sealed):
        raise AttemptError("notification capability unavailable; no retry")
    return state


def _notification_open(path: Path, raw: bytes) -> dict[str, Any]:
    parent_fd, ancestors = _startup_directory_chain(path.parent)
    try:
        fd = os.open(
            path.name,
            os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=parent_fd,
        )
    except BaseException:
        os.close(parent_fd)
        raise
    observed = os.fstat(fd)
    record = {
        "path": path,
        "fd": fd,
        "parent_fd": parent_fd,
        "ancestors": ancestors,
        "parent_identity": (os.fstat(parent_fd).st_dev, os.fstat(parent_fd).st_ino),
        "device": observed.st_dev,
        "inode": observed.st_ino,
        "raw": b"",
        "digest": _sha(b""),
        "closed": False,
        "poisoned": False,
    }
    try:
        if raw and os.write(fd, raw) != len(raw):
            raise AttemptError("notification short write")
        os.fsync(fd)
        os.fsync(parent_fd)
        record["raw"] = raw
        record["digest"] = _sha(raw)
        _startup_verify_owned(record)
    except BaseException:
        record["poisoned"] = True
        os.close(fd)
        os.close(parent_fd)
        record["closed"] = True
        raise
    return record


def _notification_validate_payload(
    state: dict[str, Any], kind: str, payload: dict[str, Any]
) -> None:
    _closed_object(payload, _NOTIFICATION_KEYS[kind])
    identity, intent = state["identity"], state["intent"]
    expected = state["expected"]
    if kind == "notification_intent_frozen":
        if (
            payload
            != {
                "intent_sha256": state["intent_sha256"],
                "intent_identity_sha256": intent["identity_sha256"],
                "expected_claim_oid": expected,
                "audited_publication_commit": identity["audited_publication_commit"],
                "absence_http_status": 404,
            }
            or type(payload["absence_http_status"]) is not int
        ):
            raise AttemptError("notification first journal identity differs")
    elif kind.endswith("POST_intent"):
        phase = (
            "notification_commit"
            if kind == "notification_commit_POST_intent"
            else "notification_ref"
        )
        raw = (
            state["commit_bytes"]
            if phase == "notification_commit"
            else state["ref_bytes"]
        )
        if (
            payload
            != {
                "phase_enum": phase,
                "nonce_hex": identity["nonce_hex"],
                "expected_claim_oid": expected,
                "raw_commit_sha256": intent["raw_commit_sha256"],
                "request_body_bytes": len(raw),
                "request_body_sha256": _sha(raw),
            }
            or type(payload["request_body_bytes"]) is not int
        ):
            raise AttemptError("notification durable request identity differs")
    elif kind.endswith("POST_receipt"):
        phase = (
            "notification_commit"
            if kind == "notification_commit_POST_receipt"
            else "notification_ref"
        )
        status = payload["http_status"]
        if (
            payload["phase_enum"] != phase
            or payload["result_enum"] not in _STARTUP_RESULTS
            or (
                status is not None
                and (type(status) is not int or not 100 <= status <= 599)
            )
            or payload["validated_oid"] not in {None, expected}
        ):
            raise AttemptError("notification receipt schema differs")
        if payload["result_enum"] == "success" and (
            status != 201 or payload["validated_oid"] != expected
        ):
            raise AttemptError("notification receipt cannot mint a winner")
    elif kind == "notification_commit_GET_verified":
        if payload != {"validated_oid": expected}:
            raise AttemptError("notification commit reread differs")
    elif kind == "notification_ref_reread_verified":
        if (
            payload
            != {
                "validated_oid": expected,
                "remote_main_oid": identity["audited_publication_commit"],
            }
            or not state["own_ref_201"]
        ):
            raise AttemptError("notification winner cannot be adopted")
    elif kind == "notification_send_intent":
        if (
            not state["own_ref_201"]
            or not state["reread_verified"]
            or payload
            != {
                "validated_oid": expected,
                "intent_sha256": state["intent_sha256"],
                "audited_publication_commit": identity["audited_publication_commit"],
                "notification_kind": _NOTIFICATION_KIND,
            }
        ):
            raise AttemptError("notification send lacks owned winner authority")
    elif kind == "notification_send_result" and (
        not state["send_consumed"]
        or payload["result_enum"] not in {"sent", "failed", "unknown"}
    ):
        raise AttemptError("notification send result differs")


def _notification_append(
    invocation: object, kind: str, payload: dict[str, Any]
) -> None:
    state = _notification_state(invocation)
    if (
        state["sequence"] >= len(_NOTIFICATION_PHASES)
        or kind != _NOTIFICATION_PHASES[state["sequence"]]
    ):
        state["poisoned"] = True
        raise AttemptError("notification phase order differs; no retry")
    try:
        _notification_validate_payload(state, kind, payload)
        _startup_verify_owned(state["intent_file"])
        _startup_verify_owned(state["journal_file"])
        stamp = _utc_now()
        instant = _valid_utc(stamp)
        if state["previous_time"] is not None and instant < state["previous_time"]:
            raise AttemptError("notification trusted clock moved backwards")
        event = {
            "schema_version": "lotto649-v13.0.0-notification-journal-v1",
            "sequence": state["sequence"],
            "generated_at": stamp,
            "previous_event_sha256": state["head"],
            "kind": kind,
            "payload": payload,
        }
        raw = _canonical(event) + b"\n"
        journal = state["journal_file"]
        if os.write(journal["fd"], raw) != len(raw):
            raise AttemptError("notification journal short write")
        os.fsync(journal["fd"])
        journal["raw"] += raw
        journal["digest"] = _sha(journal["raw"])
        _startup_verify_owned(journal)
        state["head"] = _sha(raw)
        state["sequence"] += 1
        state["previous_time"] = instant
    except BaseException:
        state["poisoned"] = True
        raise


def _issue_notification_files(
    directory: Path, identity: dict[str, Any], committer_time: str, *, synthetic: bool
) -> _NotificationInvocation:
    """Private issuance after preflight. This function itself grants no SMTP slot."""
    if synthetic is not True:
        _require_production_notification_issuance(directory, identity, committer_time)
    request, expected, raw = _notification_claim_request(
        identity, committer_time, synthetic=synthetic
    )
    reference = _SYNTHETIC_NOTIFICATION_REF if synthetic else _NOTIFICATION_REF
    commit_bytes = _canonical(request)
    ref_bytes = _canonical({"ref": reference, "sha": expected})
    prefix = (
        "synthetic-notification"
        if synthetic
        else "historical-6of6__" + identity["target_draw_date"]
    )
    paths = {
        "intent": directory / (prefix + ".intent.json"),
        "journal": directory / (prefix + ".journal.jsonl"),
        "result": directory / (prefix + ".result.json"),
    }
    if any(os.path.lexists(path) for path in paths.values()):
        raise AttemptError("notification evidence already exists; no adoption")
    started_at = _utc_now()
    _valid_utc(started_at)
    intent = {
        "schema_version": "lotto649-v13.0.0-capture-notification-intent-v1",
        "identity": identity,
        "identity_sha256": _sha(_canonical(identity) + b"\n"),
        "expected_claim_oid": expected,
        "raw_commit_sha256": _sha(raw),
        "commit_request_bytes": len(commit_bytes),
        "commit_request_sha256": _sha(commit_bytes),
        "ref_request_bytes": len(ref_bytes),
        "ref_request_sha256": _sha(ref_bytes),
        "started_at": started_at,
        "state": "started",
        "retry_allowed": False,
    }
    intent_raw = _canonical(intent) + b"\n"
    intent_file = _notification_open(paths["intent"], intent_raw)
    try:
        journal_file = _notification_open(paths["journal"], b"")
    except BaseException:
        os.close(intent_file["fd"])
        os.close(intent_file["parent_fd"])
        raise
    invocation = object.__new__(_NotificationInvocation)
    state = {
        "identity": json.loads(_canonical(identity)),
        "intent": intent,
        "intent_sha256": _sha(intent_raw),
        "request": request,
        "commit_bytes": commit_bytes,
        "ref_bytes": ref_bytes,
        "expected": expected,
        "reference": reference,
        "paths": paths,
        "intent_file": intent_file,
        "journal_file": journal_file,
        "sequence": 0,
        "head": None,
        "previous_time": None,
        "closed": False,
        "poisoned": False,
        "sealed": False,
        "commit_consumed": False,
        "ref_consumed": False,
        "send_consumed": False,
        "own_ref_201": False,
        "reread_verified": False,
        "synthetic": synthetic,
    }
    with _CAPABILITY_LOCK:
        _NOTIFICATION_STATES[invocation] = state
    _notification_append(
        invocation,
        "notification_intent_frozen",
        {
            "intent_sha256": state["intent_sha256"],
            "intent_identity_sha256": intent["identity_sha256"],
            "expected_claim_oid": expected,
            "audited_publication_commit": identity["audited_publication_commit"],
            "absence_http_status": 404,
        },
    )
    return invocation


def _notification_post(invocation: object, service: Any, phase: str) -> None:
    state = _notification_state(invocation)
    if phase not in {"notification_commit", "notification_ref"}:
        raise AttemptError("notification POST phase differs")
    slot = "commit_consumed" if phase == "notification_commit" else "ref_consumed"
    raw = (
        state["commit_bytes"] if phase == "notification_commit" else state["ref_bytes"]
    )
    _notification_append(
        invocation,
        phase + "_POST_intent",
        {
            "phase_enum": phase,
            "nonce_hex": state["identity"]["nonce_hex"],
            "expected_claim_oid": state["expected"],
            "raw_commit_sha256": state["intent"]["raw_commit_sha256"],
            "request_body_bytes": len(raw),
            "request_body_sha256": _sha(raw),
        },
    )
    with _CAPABILITY_LOCK:
        if state[slot]:
            state["poisoned"] = True
            raise AttemptError("notification POST already consumed")
        state[slot] = True
    result, status, validated = "transport_failed", None, None
    try:
        status, response = (
            service.post_commit(raw)
            if phase == "notification_commit"
            else service.create_ref(raw)
        )
        if type(status) is not int or not 100 <= status <= 599:
            raise AttemptError("notification transport status invalid")
        if status != 201:
            result = "http_rejected"
        else:
            if phase == "notification_commit":
                _verify_notification_post(
                    state["expected"],
                    state["request"],
                    response,
                    synthetic=state["synthetic"],
                )
            else:
                _verify_notification_ref(
                    state["reference"], state["expected"], response
                )
            validated, result = state["expected"], "success"
    except BaseException:  # noqa: BLE001 -- preserve uncertainty without credential-bearing exception text.
        # No diagnostic text escapes; durable intent records the uncertain edge.
        if type(status) is not int or not 100 <= status <= 599:
            status = None
        result = "transport_failed" if status is None else "identity_mismatch"
    _notification_append(
        invocation,
        phase + "_POST_receipt",
        {
            "phase_enum": phase,
            "result_enum": result,
            "http_status": status,
            "validated_oid": validated,
        },
    )
    if result != "success":
        state["poisoned"] = True
        raise AttemptError("notification POST failed or uncertain; no retry")
    if phase == "notification_ref":
        state["own_ref_201"] = True


def _verify_notification_ref(reference: str, expected: str, response: object) -> None:
    value = _closed_object(response, {"ref", "node_id", "url", "object"})
    _exact_string(value["ref"], reference)
    _nonempty_node(value["node_id"])
    _exact_string(value["url"], _API_ORIGIN + _API_PREFIX + "/git/" + reference)
    item = _closed_object(value["object"], {"sha", "type", "url"})
    _exact_string(item["sha"], expected)
    _exact_string(item["type"], "commit")
    _exact_string(item["url"], _API_ORIGIN + _API_PREFIX + "/git/commits/" + expected)


def _notification_close(invocation: object) -> None:
    if (
        type(invocation) is not _NotificationInvocation
        or invocation not in _NOTIFICATION_STATES
    ):
        return
    state = _NOTIFICATION_STATES[invocation]
    state["sealed"] = True
    if state["closed"]:
        return
    state["closed"] = True
    for key in ("intent_file", "journal_file"):
        record = state[key]
        if not record["closed"]:
            record["closed"] = True
            os.close(record["fd"])
            os.close(record["parent_fd"])


def _notification_result(invocation: object, result: str) -> dict[str, Any]:
    state = _notification_state(invocation)
    if result not in {"sent", "failed", "unknown", "not_sent"} or (
        result != "not_sent" and not state["send_consumed"]
    ):
        raise AttemptError("notification result cannot invent a send")
    if result in {"sent", "failed", "unknown"} and state["sequence"] != 9:
        raise AttemptError("notification result requires already sealed send journal")
    _startup_verify_owned(state["intent_file"])
    _startup_verify_owned(state["journal_file"])
    state["sealed"] = True
    journal = state["journal_file"]
    value = {
        "schema_version": "lotto649-v13.0.0-capture-notification-result-v1",
        "experiment_id": state["identity"]["experiment_id"],
        "model_version": state["identity"]["model_version"],
        "target_draw_date": state["identity"]["target_draw_date"],
        "notification_kind": _NOTIFICATION_KIND,
        "intent_sha256": state["intent_sha256"],
        "claim_commit": state["expected"]
        if state["own_ref_201"] and state["reread_verified"]
        else None,
        "sealed_journal": {
            "path": state["paths"]["journal"].name
            if state["synthetic"]
            else "evidence/research_notifications/v13.0.0/"
            + state["paths"]["journal"].name,
            "bytes": len(journal["raw"]),
            "sha256": _sha(journal["raw"]),
        },
        "completed_at": _utc_now(),
        "result": result,
        "retry_allowed": False,
    }
    _valid_utc(value["completed_at"])
    record = _notification_open(state["paths"]["result"], _canonical(value) + b"\n")
    os.close(record["fd"])
    os.close(record["parent_fd"])
    return value


def _drive_notification(
    invocation: object,
    service: Any,
    sender: Callable[[str, str], bool],
    pre_send: Callable[[], None],
) -> dict[str, Any]:
    state = _notification_state(invocation)
    try:
        _notification_post(invocation, service, "notification_commit")
        observed = service.get_commit(state["expected"])
        _verify_notification_get(
            state["expected"], state["request"], observed, synthetic=state["synthetic"]
        )
        _notification_append(
            invocation,
            "notification_commit_GET_verified",
            {"validated_oid": state["expected"]},
        )
        _notification_post(invocation, service, "notification_ref")
        status, observed = service.get_ref(state["reference"])
        if type(status) is not int or status != 200:
            raise AttemptError("notification winner ref reread uncertain")
        _verify_notification_ref(state["reference"], state["expected"], observed)
        pre_send()
        state["reread_verified"] = True
        _notification_append(
            invocation,
            "notification_ref_reread_verified",
            {
                "validated_oid": state["expected"],
                "remote_main_oid": state["identity"]["audited_publication_commit"],
            },
        )
        _startup_verify_owned(state["intent_file"])
        _startup_verify_owned(state["journal_file"])
        pre_send()
        _notification_append(
            invocation,
            "notification_send_intent",
            {
                "validated_oid": state["expected"],
                "intent_sha256": state["intent_sha256"],
                "audited_publication_commit": state["identity"][
                    "audited_publication_commit"
                ],
                "notification_kind": _NOTIFICATION_KIND,
            },
        )
        with _CAPABILITY_LOCK:
            if state["send_consumed"] or not state["own_ref_201"]:
                raise AttemptError("notification send slot already consumed")
            state["send_consumed"] = True
        try:
            sent = sender(
                "历史严格回测：已审计的 Final-6 6/6",
                "历史严格回测；consumed historical diagnostic，仅已审计冻结证据，不是下一期预测。",
            )
            result = (
                "sent" if sent is True else "failed" if sent is False else "unknown"
            )
        except BaseException:  # noqa: BLE001 -- interrupted send consumes its slot with unknown outcome.
            result = "unknown"
        _notification_append(
            invocation, "notification_send_result", {"result_enum": result}
        )
        return _notification_result(invocation, result)
    except BaseException:  # noqa: BLE001 -- terminal failure preserves evidence and never retries.
        state["poisoned"] = True
        raise AttemptError(
            "notification terminal failure; preserve evidence; no retry"
        ) from None
    finally:
        _notification_close(invocation)


def prepare_synthetic_notification(
    directory: Path, service: Any, *, fixture_id: str = "synthetic"
) -> object:
    """Fabricated namespace only. A real ref/authority is never an accepted input."""
    if (
        type(fixture_id) is not str
        or re.fullmatch(r"synthetic[a-z0-9_-]*", fixture_id) is None
    ):
        raise AttemptError("synthetic notification identity required")
    directory = directory.absolute()
    if any(
        os.path.lexists(parent / ".git") for parent in (directory, *directory.parents)
    ) or directory.name in {"reports", "evidence", "predictions", "evaluations"}:
        raise AttemptError("synthetic notification cannot enter a repository")
    if directory.exists() and (directory.is_symlink() or any(directory.iterdir())):
        raise AttemptError("synthetic notification directory must be new or empty")
    status, response = service.get_ref(_SYNTHETIC_NOTIFICATION_REF)
    if type(status) is not int or status != 404 or response != {"message": "Not Found"}:
        raise AttemptError("synthetic notification requires exact direct absence")
    directory.mkdir(parents=True, exist_ok=True)
    identity = {
        "experiment_id": "synthetic_v13_capture",
        "model_version": "synthetic_fixture_only",
        "target_draw_date": "2030-01-02",
        "notification_kind": _NOTIFICATION_KIND,
        "candidate_bundle_path": "synthetic-candidate.json",
        "candidate_bundle_sha256": "a" * 64,
        "audit_json_path": "synthetic-audit.json",
        "audit_json_sha256": "b" * 64,
        "audited_publication_commit": "c" * 40,
        "publication_tree_oid": "d" * 40,
        "scientific_contract_sha256": "e" * 64,
        "operational_contract_sha256": "f" * 64,
        "nonce_hex": secrets.token_hex(32),
    }
    return _issue_notification_files(
        directory, identity, "2023-11-14T22:13:20Z", synthetic=True
    )


def run_synthetic_notification(
    invocation: object,
    service: Any,
    sender: Callable[[str, str], bool],
    *,
    pre_send: Callable[[], None],
) -> dict[str, Any]:
    state = _notification_state(invocation)
    if (
        state["synthetic"] is not True
        or state["identity"]["experiment_id"] != "synthetic_v13_capture"
        or state["reference"] != _SYNTHETIC_NOTIFICATION_REF
    ):
        raise AttemptError(
            "synthetic driver refuses production notification capability"
        )
    return _drive_notification(invocation, service, sender, pre_send)


# BEGIN V13 POST-AUDIT NOTIFICATION IMPLEMENTATION
# Source-only integration fragment for src/lotto649/v13_registered_attempt.py.
# Author: /root/v13_notification_production_draft
# Session: v13-notification-production-draft-authoring-20260913
# No production capability or effect was created during authoring.
# Insert after the notification protocol block; module-level helpers are reused.


class _NotificationHTTP:
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
                "User-Agent": "lotto649-v13.0.0",
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
        try:
            return self._request_json_checked(
                method, path, body_bytes=body_bytes, allow_absent=allow_absent
            )
        except BaseException:
            self._terminal = True
            raise

    def _request_json_checked(
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
        lease_path = "/git/ref/heads/v13-notification-v13.0.0"
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
            _require_notification_transport_post(self, suffix, body_bytes)
            try:
                request = _transport_json(body_bytes)
                if _canonical(request) != body_bytes:
                    raise AuthorizationError("GitHub POST bytes are not canonical")
                if suffix == "/git/commits":
                    _notification_request_parts(request)
                else:
                    request = _closed_object(request, {"ref", "sha"})
                    _exact_string(request["ref"], _NOTIFICATION_REF)
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
                "verify": True,
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
                    or response.headers.get("Link", "") != ""
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

    def get_ref(self, reference: str) -> tuple[int, dict[str, Any]]:
        if type(reference) is not str or reference != _NOTIFICATION_REF:
            self._terminal = True
            raise AuthorizationError(
                "notification adapter refuses cross-purpose reference"
            )
        result = self.request_json(
            "GET",
            _API_PREFIX + "/git/ref/heads/v13-notification-v13.0.0",
            allow_absent=True,
        )
        if result is None:
            return 404, {"message": "Not Found"}
        if type(result) is not dict or self.last_status != 200:
            self._terminal = True
            raise AuthorizationError("notification ref metadata unavailable")
        return 200, result

    def get_commit(self, oid: str) -> dict[str, Any]:
        transport = _NOTIFICATION_TRANSPORTS.get(self)
        if (
            transport is None
            or transport["invocation"] is None
            or _notification_state(transport["invocation"])["expected"] != _oid(oid)
        ):
            self._terminal = True
            raise AuthorizationError(
                "notification commit GET lacks own expected identity"
            )
        result = self.request_json("GET", _API_PREFIX + "/git/commits/" + oid)
        if type(result) is not dict:
            self._terminal = True
            raise AuthorizationError("notification commit metadata unavailable")
        return result

    def post_commit(self, raw: bytes) -> tuple[int, dict[str, Any]]:
        result = self.request_json("POST", _API_PREFIX + "/git/commits", body_bytes=raw)
        if type(result) is not dict or self.last_status != 201:
            self._terminal = True
            raise AuthorizationError("notification commit receipt unavailable")
        return 201, result

    def create_ref(self, raw: bytes) -> tuple[int, dict[str, Any]]:
        result = self.request_json("POST", _API_PREFIX + "/git/refs", body_bytes=raw)
        if type(result) is not dict or self.last_status != 201:
            self._terminal = True
            raise AuthorizationError("notification ref receipt unavailable")
        return 201, result


# Inert metadata and transport registries are separate from historical authority.
_NOTIFICATION_FACTS = {}
_NOTIFICATION_TRANSPORTS = {}


class _VerifiedNotificationFacts:
    __slots__ = ()

    def __new__(cls, *args: Any, **kwargs: Any) -> Any:
        raise AuthorizationError("notification facts require independent verification")


def _notification_facts(facts: object) -> dict[str, Any]:
    with _CAPABILITY_LOCK:
        if (
            type(facts) is not _VerifiedNotificationFacts
            or facts not in _NOTIFICATION_FACTS
        ):
            raise AuthorizationError("unissued notification facts")
        state = _NOTIFICATION_FACTS[facts]
        if (
            state["closed"]
            or state["poisoned"]
            or _canonical(state["proof"]) != state["stamp"]
        ):
            raise AuthorizationError("notification facts changed or terminated")
        return state


def _notification_blob_origin(git: GitRepository, head: str, path: str) -> str:
    """Require one ordinary ADD and immutability on every reachable parent edge."""
    expected = git.run("ls-tree", "-z", _oid(head), "--", _relative(path))
    if not re.fullmatch(
        rb"100644 blob [0-9a-f]{40}\t" + re.escape(path.encode()) + rb"\x00", expected
    ):
        raise AuthorizationError("capture evidence is not an ordinary immutable blob")
    origins = []
    for line in git.text("rev-list", "--parents", _oid(head)).splitlines():
        commit, *parents = line.split()
        current = git.run("ls-tree", "-z", _oid(commit), "--", path)
        previous = [
            git.run("ls-tree", "-z", _oid(parent), "--", path) for parent in parents
        ]
        if current not in {b"", expected} or any(
            value not in {b"", expected} for value in previous
        ):
            raise AuthorizationError("capture evidence changed on a reachable DAG edge")
        if not parents:
            if current:
                raise AuthorizationError(
                    "capture evidence root introduction is prohibited"
                )
        elif current:
            if all(not value for value in previous):
                if len(parents) != 1:
                    raise AuthorizationError(
                        "capture evidence merge introduction is prohibited"
                    )
                origins.append(commit)
        elif any(previous):
            raise AuthorizationError(
                "capture evidence deletion or restoration is prohibited"
            )
    if len(origins) != 1:
        raise AuthorizationError(
            "capture evidence must have one immutable ordinary ADD"
        )
    return _oid(origins[0])


def _notification_json(
    git: GitRepository, commit: str, path: str, keys: Sequence[str]
) -> tuple[dict[str, Any], bytes]:
    raw = git.read_blob(_oid(commit), _relative(path))
    value = _json(raw)
    _closed_object(value, set(keys))
    if raw != _canonical(value) + b"\n":
        raise AuthorizationError("capture JSON is not exact canonical C plus LF")
    return value, raw


def _notification_six(value: object) -> list[int]:
    if (
        type(value) is not list
        or len(value) != 6
        or any(type(n) is not int or not 1 <= n <= 49 for n in value)
        or value != sorted(set(value))
    ):
        raise AuthorizationError("capture Final-6 domain differs")
    return value


def _notification_read_immutable(
    git: GitRepository, head: str, path: str
) -> dict[str, Any]:
    file = git.root / _relative(path)
    if any(parent.is_symlink() for parent in (file, *file.parents)):
        raise AuthorizationError("capture path symlink is prohibited")
    fd = os.open(file, os.O_RDONLY | os.O_NOFOLLOW)
    parent_fd = None
    try:
        parent_fd = os.open(file.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        info, parent = os.fstat(fd), os.fstat(parent_fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise AuthorizationError("capture path must be a unique regular file")
        expected = git.read_blob(head, path)
        raw = os.pread(fd, len(expected) + 1, 0)
        if raw != expected:
            raise AuthorizationError("capture working bytes differ from publication")
        return {
            "path": file,
            "fd": fd,
            "parent_fd": parent_fd,
            "dev": info.st_dev,
            "ino": info.st_ino,
            "parent_dev": parent.st_dev,
            "parent_ino": parent.st_ino,
            "raw": raw,
        }
    except BaseException:
        os.close(fd)
        if parent_fd is not None:
            os.close(parent_fd)
        raise


def _notification_check_immutable(record: Mapping[str, Any]) -> None:
    file = record["path"]
    if any(parent.is_symlink() for parent in (file, *file.parents)):
        raise AuthorizationError("retained capture path changed")
    info, observed = os.fstat(record["fd"]), file.stat(follow_symlinks=False)
    parent, path_parent = (
        os.fstat(record["parent_fd"]),
        file.parent.stat(follow_symlinks=False),
    )
    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_nlink != 1
        or (info.st_dev, info.st_ino) != (record["dev"], record["ino"])
        or (observed.st_dev, observed.st_ino) != (info.st_dev, info.st_ino)
        or (parent.st_dev, parent.st_ino)
        != (record["parent_dev"], record["parent_ino"])
        or (path_parent.st_dev, path_parent.st_ino) != (parent.st_dev, parent.st_ino)
        or os.pread(record["fd"], len(record["raw"]) + 1, 0) != record["raw"]
    ):
        raise AuthorizationError("retained capture file identity or bytes changed")


def _notification_authorization_metadata(
    git: GitRepository, api: Any, execution: str, head: str
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """Revalidate archived authorization without constructing execution facts."""
    _science, operation = _registered_authorities(git, head)
    specification = operation["authorization"]["authorization_schema"]
    auth, raw = _notification_json(
        git, execution, AUTHORIZATION_PATH, specification["required_keys"]
    )
    _closed_object(auth, set(specification["required_keys"]))
    required = {
        "schema_version": specification["schema_version"],
        "experiment_id": operation["identity"]["experiment_id"],
        "model_version": "v13.0.0",
        "repository": REPOSITORY,
        "branch": "main",
        "registration_commit": R13,
        "scientific_registration_commit": R13,
        "registration_sha256": REGISTRATION_SHA256,
        "statistical_fingerprint_sha256": FINGERPRINT,
        "operational_contract_sha256": OPERATIONAL_SHA256,
        "canonical_command": COMMAND,
        "governed_history_authority": HISTORY_AUTHORITY,
        "governed_history_identity": operation["identity"]["governed_history_identity"],
        "runtime": runtime_identity(),
    }
    if any(auth[key] != value for key, value in required.items()):
        raise AuthorizationError("archived authorization identity differs")
    implementation, base, merge = map(
        _oid,
        (
            auth["implementation_commit"],
            auth["implementation_base"],
            auth["implementation_merge"],
        ),
    )
    if (
        auth["authorization_base"] != merge
        or git.parents(implementation) != (base,)
        or not git.ancestor(R13, base)
        or set(git.changes(base, implementation))
        != {("A", path) for path in IMPLEMENTATION_PATHS}
    ):
        raise AuthorizationError("archived I13 source topology differs")
    _require_normal_merge(git, merge, base, implementation)
    parents = git.parents(execution)
    if len(parents) != 2 or parents[0] != merge:
        raise AuthorizationError("archived authorization merge differs")
    source = parents[1]
    _require_normal_merge(git, execution, merge, source)
    if (
        git.parents(source) != (merge,)
        or git.changes(merge, source) != [("A", AUTHORIZATION_PATH)]
        or git.read_blob(source, AUTHORIZATION_PATH) != raw
        or _notification_blob_origin(git, head, AUTHORIZATION_PATH) != source
    ):
        raise AuthorizationError("archived authorization ADD provenance differs")
    closure = auth["runtime_dependency_closure"]
    manifest = auth["implementation_files"]
    if _sha(_canonical(closure)) != _digest(
        auth["runtime_dependency_closure_sha256"]
    ) or _sha(_canonical(manifest)) != _digest(auth["implementation_files_sha256"]):
        raise AuthorizationError("archived closure manifests differ")
    for checkpoint in (implementation, merge, source, execution, head):
        _registered_authorities(git, checkpoint)
        if (
            _implementation_manifest(git, checkpoint) != manifest
            or _core_and_closure(
                git, checkpoint, required_core_sha256=_digest(auth["pure_core_sha256"])
            )
            != closure
        ):
            raise AuthorizationError("archived implementation or runtime closure drift")
    _verify_worktree_runtime(git, head, closure)
    _verify_reviews(
        api,
        auth["review_records"],
        implementation=implementation,
        merge=merge,
        base=base,
        closure_sha256=auth["runtime_dependency_closure_sha256"],
        git=git,
        phase="I13",
    )
    reviews = _discover_authorization_reviews(
        api,
        source=source,
        base=merge,
        merge=execution,
        closure_sha256=auth["runtime_dependency_closure_sha256"],
    )
    _verify_reviews(
        api,
        reviews,
        implementation=source,
        merge=execution,
        base=merge,
        closure_sha256=auth["runtime_dependency_closure_sha256"],
        git=git,
        phase="A_H_s13",
    )
    contributors = set()
    for commit, phase in ((R13, "R13"), (implementation, "I13"), (source, "A_H_s13")):
        for person in _source_author_provenance(
            git.run("cat-file", "commit", commit), phase
        ):
            contributors.add((person["agent_id"], person["session_id"]))
    return auth, [
        {"agent_id": agent, "session_id": session}
        for agent, session in sorted(
            contributors, key=lambda pair: (pair[0].encode(), pair[1].encode())
        )
    ]


def _notification_reference_digest(
    git: GitRepository,
    reference: dict[str, Any],
    *,
    head: str,
    execution: str,
    worker: str,
    auth: Mapping[str, Any],
    operation: Mapping[str, Any],
) -> str:
    """Authenticate evidence references without opening governed history blobs."""
    _closed_object(reference, {"path", "sha256", "git_commit"})
    path, commit = _relative(reference["path"]), _oid(reference["git_commit"])
    _digest(reference["sha256"])
    if not git.ancestor(commit, head):
        raise AuthorizationError("capture audit cites nonancestral evidence")

    def checked(expected: str) -> str:
        if reference["sha256"] != expected:
            raise AuthorizationError("capture evidence reference digest differs")
        return expected

    worker_paths = {
        "reports/" + _ARTIFACT_NAMES[role]
        for role in ("startup", "claim", "ledger", "json", "markdown", "manifest")
    }
    if path in worker_paths:
        if commit != worker:
            raise AuthorizationError("worker evidence authority differs")
        return checked(_sha(git.read_blob(worker, path)))
    seal_raw = git.read_blob(R13, REGISTRATION_PATH)
    if _sha(seal_raw) != REGISTRATION_SHA256:
        raise AuthorizationError("registration evidence seal differs")
    seal = _json(seal_raw)
    registered = {entry["path"]: entry for entry in seal["registered_files"]}
    # R13 is a source authority even when the same sealed path is also a later
    # runtime input. Resolve that exact source identity before runtime checkpoints.
    if commit == R13:
        if path == REGISTRATION_PATH:
            return checked(REGISTRATION_SHA256)
        if path in registered:
            if git.oid(commit, path) != registered[path]["git_blob"]:
                raise AuthorizationError("registration evidence authority differs")
            return checked(registered[path]["sha256"])
    entries = {entry["path"]: entry for entry in auth["runtime_dependency_closure"]}
    entries.update({entry["path"]: entry for entry in auth["implementation_files"]})
    if path in entries:
        if (
            commit
            not in {
                auth["implementation_commit"],
                auth["implementation_merge"],
                git.parents(execution)[1],
                execution,
            }
            or git.oid(commit, path) != entries[path]["git_blob"]
        ):
            raise AuthorizationError("runtime evidence authority differs")
        return checked(entries[path]["sha256"])
    preserved = {entry["path"]: entry for entry in seal["preserved_tree_manifest"]}
    if path not in preserved or git.oid(commit, path) != preserved[path]["oid"]:
        raise AuthorizationError("audit reference is outside registered evidence")
    identity = operation["identity"]["governed_history_identity"]
    for pin in identity["immutable_objects"].values():
        if preserved[path]["oid"] == pin["git_blob"]:
            if commit not in {
                HISTORY_AUTHORITY,
                R13,
                pin.get("commit"),
                pin.get("genesis_commit"),
            }:
                raise AuthorizationError(
                    "governed metadata reference authority differs"
                )
            return checked(pin["sha256"])
    # Source-only preserved paths can be hashed. Outcome/report data cannot.
    if commit == R13 and (
        path.startswith(("src/", "tools/", "requirements/", "docs/", "config/"))
        or path in {"AGENTS.md", "config.yaml", "pyproject.toml"}
    ):
        return checked(_sha(git.read_blob(R13, path)))
    raise AuthorizationError("audit reference lacks a registered metadata-only digest")


def _capture_publication_authors(raw_commit: bytes) -> list[dict[str, str]]:
    """I13's stricter proof, separate from the immutable R13 phase schemas."""
    marker = b"Capture-Publication-Authors: "
    if type(raw_commit) is not bytes or b"\n\n" not in raw_commit:
        raise AuthorizationError("capture publication authors unavailable")
    message = raw_commit.split(b"\n\n", 1)[1]
    lines = message.split(b"\n")
    matches = [
        line for line in lines if line.lstrip(b" \t\r\v\f").startswith(marker[:-1])
    ]
    if (
        len(lines) < 2
        or lines[-1]
        or not lines[-2].startswith(marker)
        or matches != [lines[-2]]
    ):
        raise AuthorizationError("capture publication author trailer framing differs")
    raw = lines[-2][len(marker) :]
    value = _json(raw)
    _closed_object(value, {"schema_version", "contributors"})
    if (
        raw != _canonical(value)
        or value["schema_version"] != "lotto649-v13-capture-publication-authors-v1"
    ):
        raise AuthorizationError("capture publication author trailer differs")
    persons = value["contributors"]
    if type(persons) is not list or not 1 <= len(persons) <= 64:
        raise AuthorizationError("capture publication authors missing or unbounded")
    pairs = []
    for person in persons:
        _closed_object(person, {"agent_id", "session_id"})
        pairs.append(
            (
                _provenance_identifier(person["agent_id"]),
                _provenance_identifier(person["session_id"]),
            )
        )
    if pairs != sorted(
        set(pairs), key=lambda pair: (pair[0].encode(), pair[1].encode())
    ):
        raise AuthorizationError("capture publication authors duplicated or unsorted")
    return persons


def _notification_publication_reviews(
    git: GitRepository,
    api: Any,
    *,
    head: str,
    source: str,
    base: str,
    closure_sha256: str,
    excluded: Sequence[Mapping[str, str]],
) -> list[dict[str, Any]]:
    """Dedicated I13-fixed 13-key review proof; no new R13 phase is asserted."""
    associated = api.request_json(
        "GET", _API_PREFIX + f"/commits/{source}/pulls?per_page=100"
    )
    if (
        type(associated) is not list
        or len(associated) > 100
        or any(type(pr) is not dict for pr in associated)
    ):
        raise AuthorizationError("capture publication PR collection incomplete")
    matches = [
        pr
        for pr in associated
        if pr.get("merge_commit_sha") == head
        and pr.get("head", {}).get("sha") == source
        and pr.get("base", {}).get("sha") == base
    ]
    if (
        len(matches) != 1
        or type(matches[0].get("number")) is not int
        or matches[0]["number"] < 1
    ):
        raise AuthorizationError("capture publication PR is ambiguous")
    number = matches[0]["number"]
    pr = _required_response(api, f"/pulls/{number}")
    if (
        pr.get("number") != number
        or pr.get("state") != "closed"
        or pr.get("merged") is not True
        or pr.get("merge_commit_sha") != head
        or pr.get("head", {}).get("sha") != source
        or pr.get("base", {}).get("sha") != base
        or pr.get("base", {}).get("ref") != "main"
        or pr.get("head", {}).get("repo", {}).get("full_name") != REPOSITORY
        or pr.get("base", {}).get("repo", {}).get("full_name") != REPOSITORY
    ):
        raise AuthorizationError("capture publication PR identity differs")
    checks = _required_response(api, f"/commits/{source}/check-runs?per_page=100")
    if (
        type(checks.get("total_count")) is not int
        or not 0 <= checks["total_count"] <= 100
        or type(checks.get("check_runs")) is not list
        or len(checks["check_runs"]) != checks["total_count"]
        or any(type(item) is not dict for item in checks["check_runs"])
    ):
        raise AuthorizationError("capture publication CI collection incomplete")
    matches = [check for check in checks["check_runs"] if check.get("name") == "test"]
    if (
        len(matches) != 1
        or type(matches[0].get("id")) is not int
        or matches[0]["id"] < 1
    ):
        raise AuthorizationError("capture publication requires one exact test check")
    check_id = matches[0]["id"]
    check = _required_response(api, f"/check-runs/{check_id}")
    if (
        check.get("id") != check_id
        or check.get("name") != "test"
        or check.get("head_sha") != source
        or check.get("status") != "completed"
        or check.get("conclusion") != "success"
        or check.get("app", {}).get("slug") != "github-actions"
    ):
        raise AuthorizationError("capture publication exact-source CI did not pass")
    comments = api.request_json(
        "GET", _API_PREFIX + f"/issues/{number}/comments?per_page=100"
    )
    if (
        type(comments) is not list
        or len(comments) > 100
        or any(type(comment) is not dict for comment in comments)
    ):
        raise AuthorizationError("capture review comment collection incomplete")
    reviewers = []
    for listed in comments:
        text = listed.get("body")
        if type(text) is not str:
            raise AuthorizationError("capture review body type differs")
        try:
            body = _json(text.encode())
        except AuthorizationError:
            continue
        if (
            body.get("schema_version")
            != "lotto649-v13-capture-publication-independent-review-v1"
        ):
            continue
        _closed_object(
            body,
            {
                "schema_version",
                "axis",
                "base_sha",
                "head_sha",
                "closure_sha256",
                "operational_contract_sha256",
                "verdict",
                "blocker_count",
                "major_count",
                "reviewer_kind",
                "reviewer_agent_id",
                "review_session_id",
                "publisher_login",
            },
        )
        comment_id = listed.get("id")
        if type(comment_id) is not int or comment_id < 1:
            raise AuthorizationError("capture review comment ID differs")
        comment = _required_response(api, f"/issues/comments/{comment_id}")
        if (
            comment != listed
            or comment.get("body", "").encode() != _canonical(body) + b"\n"
            or comment.get("updated_at") != comment.get("created_at")
            or comment.get("issue_url")
            != _API_ORIGIN + _API_PREFIX + f"/issues/{number}"
            or comment.get("user", {}).get("login") != body["publisher_login"]
        ):
            raise AuthorizationError("capture publication review is not immutable")
        _valid_utc(comment["created_at"])
        for key in ("reviewer_agent_id", "review_session_id", "publisher_login"):
            _provenance_identifier(body[key])
        required = {
            "base_sha": base,
            "head_sha": source,
            "closure_sha256": closure_sha256,
            "operational_contract_sha256": OPERATIONAL_SHA256,
            "verdict": "pass",
            "reviewer_kind": "independent_agent",
        }
        if (
            any(body[key] != value for key, value in required.items())
            or body["axis"] not in {"standards", "spec"}
            or any(
                type(body[key]) is not int or body[key] != 0
                for key in ("blocker_count", "major_count")
            )
        ):
            raise AuthorizationError(
                "capture publication review identity or verdict differs"
            )
        if body["reviewer_agent_id"] in {
            person["agent_id"] for person in excluded
        } or body["review_session_id"] in {person["session_id"] for person in excluded}:
            raise AuthorizationError("capture publication review is not independent")
        reviewers.append(
            {
                "axis": body["axis"],
                "check_id": check_id,
                "comment_body_sha256": _sha(comment["body"].encode()),
                "comment_id": comment_id,
                "pr_number": number,
                "publisher_login": body["publisher_login"],
                "review_session_id": body["review_session_id"],
                "reviewer_agent_id": body["reviewer_agent_id"],
            }
        )
    if (
        len(reviewers) != 2
        or {review["axis"] for review in reviewers} != {"standards", "spec"}
        or len({review["reviewer_agent_id"] for review in reviewers}) != 2
        or len({review["review_session_id"] for review in reviewers}) != 2
    ):
        raise AuthorizationError(
            "capture publication lacks two independent review axes"
        )
    return sorted(reviewers, key=lambda review: review["axis"])


def render_capture_audit_markdown(audit: Mapping[str, Any]) -> bytes:
    """I13-fixed UTF-8/LF rendering preserves every paired audit JSON fact."""
    return (
        "# V13.0.0 历史严格回测独立审计\n\n"
        + "目标开奖日期："
        + audit["target_draw_date"]
        + "\n\n"
        + "审计结论："
        + audit["verdict"]
        + "；阻断项："
        + str(audit["blocker_count"])
        + "；重大问题："
        + str(audit["major_count"])
        + "。\n\n"
        + "本记录仅属于已消耗的历史诊断；不表示下一期预测或稳定中奖能力。\n\n"
        + "## 完整审计记录\n\n```json\n"
        + json.dumps(
            dict(audit), sort_keys=True, ensure_ascii=False, allow_nan=False, indent=2
        )
        + "\n```\n"
    ).encode("utf-8")


def _notification_checkpoint_metadata(
    value: object, operation: Mapping[str, Any]
) -> dict[str, Any]:
    checkpoint = _closed_object(
        value, set(operation["claim_ledger_publication"]["checkpoint_exact_keys"])
    )
    if (
        checkpoint["path"] != operation["startup"]["path"]
        or type(checkpoint["sequence"]) is not int
        or checkpoint["sequence"]
        != operation["startup"]["sequence_contract"]["checkpoint_sequence"]
        or type(checkpoint["prefix_byte_count"]) is not int
        or checkpoint["prefix_byte_count"] <= 0
    ):
        raise AuthorizationError("notification startup checkpoint metadata differs")
    _digest(checkpoint["head_sha256"])
    _digest(checkpoint["prefix_sha256"])
    return checkpoint


def _notification_startup_metadata(
    git: GitRepository,
    raw: bytes,
    manifest: Mapping[str, Any],
    claim: Mapping[str, Any],
    claim_raw: bytes,
    events: Sequence[Mapping[str, Any]],
    execution: str,
    operation: Mapping[str, Any],
) -> None:
    """Validate closed startup bytes and their acyclic receipts, never rerun them."""
    startup = operation["startup"]
    publication = operation["claim_ledger_publication"]
    checkpoint = _notification_checkpoint_metadata(
        manifest["startup_checkpoint"], operation
    )
    sealed = _closed_object(
        manifest["sealed_startup"],
        set(publication["manifest_schema"]["sealed_startup_exact_keys"]),
    )
    if (
        type(raw) is not bytes
        or not raw
        or not raw.endswith(b"\n")
        or type(sealed["bytes"]) is not int
        or sealed["bytes"] <= 0
        or sealed["path"] != startup["path"]
        or sealed["bytes"] != len(raw)
        or _digest(sealed["sha256"]) != _sha(raw)
    ):
        raise AuthorizationError("notification sealed startup byte binding differs")
    auth_keys = set(operation["authorization"]["authorization_schema"]["required_keys"])
    extras = {
        "startup_checkpoint",
        "verified_facts_sha256",
        "execution_authority_M_A_H13",
        "authorization_source_A_H_s13",
        "authorization_sha256",
        "lease_ref",
        "lease_commit_L_H13",
        "nonce_hex",
        "seed",
        "classification",
    }
    bindings = _closed_object(claim["bindings"], auth_keys | extras)
    original_facts = _closed_object(
        claim["verified_authorization_facts"],
        set(operation["authorization"]["facts_preimage_exact_keys"]),
    )
    _closed_object(original_facts["payload"], auth_keys)
    if (
        _canonical({key: bindings[key] for key in auth_keys})
        != _canonical(original_facts["payload"])
        or _sha(_canonical(original_facts)) != bindings["verified_facts_sha256"]
        or original_facts["execution_commit"] != execution
        or bindings["execution_authority_M_A_H13"] != execution
        or original_facts["source_commit"] != bindings["authorization_source_A_H_s13"]
        or original_facts["authorization_sha256"] != bindings["authorization_sha256"]
        or bindings["lease_ref"] != LEASE_REF
        or type(bindings["seed"]) is not int
        or bindings["seed"] != 649
        or bindings["classification"] != "consumed_historical_diagnostic_only"
    ):
        raise AuthorizationError("notification startup original facts binding differs")
    if len(events) < 2 or (
        _canonical(
            _notification_checkpoint_metadata(bindings["startup_checkpoint"], operation)
        )
        != _canonical(checkpoint)
        or _canonical(
            _notification_checkpoint_metadata(
                events[0]["payload"]["startup_checkpoint"], operation
            )
        )
        != _canonical(checkpoint)
        or _canonical(events[0]["bindings"]) != _canonical(bindings)
        or events[0]["payload"]["claim_sha256"] != _sha(claim_raw)
    ):
        raise AuthorizationError(
            "notification checkpoint claim and first ledger differ"
        )
    closure = bindings["runtime_dependency_closure"]
    if type(closure) is not list:
        raise AuthorizationError("notification startup closure metadata differs")
    for entry in closure:
        _closed_object(entry, {"path", "git_blob", "sha256"})
    config_entries = [entry for entry in closure if entry["path"] == CONFIG_PATH]
    if len(config_entries) != 1:
        raise AuthorizationError("notification startup config identity unavailable")
    identity = {
        "execution_authority_M_A_H13": execution,
        "registration_R13": bindings["registration_commit"],
        "source_A_H_s13": bindings["authorization_source_A_H_s13"],
        "implementation_commit": bindings["implementation_commit"],
        "authorization_base": bindings["authorization_base"],
        "registration_sha256": bindings["registration_sha256"],
        "config_sha256": config_entries[0]["sha256"],
        "authorization_sha256": bindings["authorization_sha256"],
        "historical_runtime_dependency_closure_sha256": bindings[
            "runtime_dependency_closure_sha256"
        ],
        "runtime_identity_sha256": _sha(_canonical(bindings["runtime"])),
        "requirements_sha256": REQUIREMENTS_SHA256,
        "required_pure_core_sha256": bindings["pure_core_sha256"],
        "statistical_fingerprint_sha256": bindings["statistical_fingerprint_sha256"],
        "operational_contract_sha256": bindings["operational_contract_sha256"],
        "verified_facts_sha256": bindings["verified_facts_sha256"],
    }
    for key in startup["first_identity_exact_oid_keys"]:
        _oid(identity[key])
    for key in startup["first_identity_exact_digest_keys"]:
        _digest(identity[key])
    lease = _oid(bindings["lease_commit_L_H13"])
    nonce = _digest(bindings["nonce_hex"])
    lease_raw = git.run("cat-file", "commit", lease)
    if type(lease_raw) is not bytes or b"\n\n" not in lease_raw:
        raise AuthorizationError("notification startup lease framing differs")
    headers, message = lease_raw.split(b"\n\n", 1)
    lines = headers.split(b"\n")
    author_prefix = b"author LOTTO649 V13 Consumption Lease <lotto649-v13-lease@users.noreply.github.com> "
    if (
        len(lines) != 4
        or not lines[2].startswith(author_prefix)
        or lines[3] != b"committer " + lines[2][len(b"author ") :]
        or re.fullmatch(rb"[0-9]+ \+0000", lines[2][len(author_prefix) :]) is None
    ):
        raise AuthorizationError("notification startup lease header differs")
    try:
        timestamp = datetime.fromtimestamp(
            int(lines[2][len(author_prefix) :].split(b" ")[0]), UTC
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
        person = {
            "name": "LOTTO649 V13 Consumption Lease",
            "email": "lotto649-v13-lease@users.noreply.github.com",
            "date": timestamp,
        }
        request = {
            "tree": git.tree(execution),
            "parents": [execution],
            "author": person,
            "committer": dict(person),
            "message": message.decode("utf-8"),
        }
        observed_oid, expected_raw, _projected = _lease_request_parts(request)
    except (ValueError, OverflowError, OSError, UnicodeError, AttemptError):
        raise AuthorizationError(
            "notification startup lease projection differs"
        ) from None
    if (
        observed_oid != lease
        or expected_raw != lease_raw
        or _json(_projected.encode("utf-8"))
        != {
            "schema_version": "lotto649-v13-consumption-lease-v1",
            "authorization_seal_sha256": bindings["authorization_sha256"],
            "canonical_command": COMMAND,
            "execution_authority_M_A": execution,
            "nonce_hex": nonce,
        }
    ):
        raise AuthorizationError("notification startup lease raw identity differs")
    expected_payloads = {
        "authorized_startup_started": {
            "repository": REPOSITORY,
            "branch": "main",
            "startup_identity": identity,
        },
        "capability_issued": {},
        "lease_absence_confirmed": {"http_status": 404},
        "lease_commit_POST_receipt": {
            "phase_enum": "lease_commit",
            "result_enum": "success",
            "http_status": 201,
            "validated_oid": lease,
        },
        "lease_commit_GET_verified": {"validated_oid": lease},
        "lease_ref_POST_receipt": {
            "phase_enum": "lease_ref",
            "result_enum": "success",
            "http_status": 201,
            "validated_oid": lease,
        },
        "lease_ref_reread_verified": {"validated_oid": lease},
        "startup_checkpoint": {},
        "claim_created": {"claim_sha256": _sha(claim_raw)},
        "scientific_ledger_started": {"first_event_sha256": events[0]["event_sha256"]},
        "history_load_intent": {},
    }
    for phase, body in (
        ("lease_commit", request),
        ("lease_ref", {"ref": LEASE_REF, "sha": lease}),
    ):
        wire = _canonical(body)
        expected_payloads[phase + "_POST_intent"] = {
            "phase_enum": phase,
            "nonce_hex": nonce,
            "expected_lease_oid": lease,
            "raw_commit_sha256": _sha(lease_raw),
            "request_body_bytes": len(wire),
            "request_body_sha256": _sha(wire),
        }
    raw_lines = raw.splitlines(keepends=True)
    phases = startup["required_phase_events"]
    if len(raw_lines) != startup["sequence_contract"]["phase_count"] or len(
        phases
    ) != len(raw_lines):
        raise AuthorizationError("notification startup requires all thirteen phases")
    previous, last_instant = None, None
    instants = []
    for sequence, (line, phase) in enumerate(zip(raw_lines, phases, strict=True)):
        event = _closed_object(
            _json(line), set(startup["event_envelope"]["exact_keys"])
        )
        if (
            line != _canonical(event) + b"\n"
            or event["schema_version"] != startup["schema_version"]
            or type(event["sequence"]) is not int
            or event["sequence"] != sequence
            or event["kind"] != phase
            or event["previous_event_sha256"] != previous
        ):
            raise AuthorizationError("notification startup event chain differs")
        _closed_object(
            event["payload"], set(startup["phase_payload_exact_keys"][phase])
        )
        if phase == "authorized_startup_started":
            _closed_object(
                event["payload"]["startup_identity"],
                set(startup["first_identity_exact_oid_keys"])
                | set(startup["first_identity_exact_digest_keys"]),
            )
        if _canonical(event["payload"]) != _canonical(expected_payloads[phase]):
            raise AuthorizationError(
                "notification startup phase receipt binding differs"
            )
        try:
            instant = _valid_utc(event["generated_at"])
        except AttemptError:
            raise AuthorizationError(
                "notification startup clock metadata differs"
            ) from None
        if last_instant is not None and instant < last_instant:
            raise AuthorizationError("notification startup clock regressed")
        instants.append(instant)
        last_instant, previous = instant, _sha(line)
    prefix = b"".join(raw_lines[: checkpoint["sequence"] + 1])
    if (
        checkpoint["prefix_byte_count"] != len(prefix)
        or checkpoint["prefix_sha256"] != _sha(prefix)
        or checkpoint["head_sha256"] != _sha(raw_lines[checkpoint["sequence"]])
        or len(prefix) >= len(raw)
    ):
        raise AuthorizationError("notification startup early prefix bytes differ")
    try:
        claim_instant = _valid_utc(claim["claimed_at"])
        first_ledger_instant = _valid_utc(events[0]["recorded_at"])
        first_forecast_instant = _valid_utc(events[1]["recorded_at"])
    except AttemptError:
        raise AuthorizationError(
            "notification startup cross-stream clock differs"
        ) from None
    if not (
        instants[9] <= claim_instant <= first_ledger_instant <= instants[10]
        and instants[10] <= instants[11]
        and instants[12] <= first_forecast_instant
    ):
        raise AuthorizationError("notification startup acyclic clock ordering differs")


def _notification_capture_artifacts(
    git: GitRepository,
    head: str,
    worker: str,
    execution: str,
    operation: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    paths = operation["claim_ledger_publication"]["worker_outputs"]
    finals = sorted(
        paths[role]
        for role in ("startup", "claim", "ledger", "json", "markdown", "manifest")
    )
    if git.parents(worker) != (execution,) or set(git.changes(execution, worker)) != {
        ("A", path) for path in finals
    }:
        raise AuthorizationError(
            "worker artifact commit is not the exact six-file child"
        )
    for path in finals:
        if _notification_blob_origin(git, head, path) != worker:
            raise AuthorizationError("worker artifact provenance changed")
    specification = operation["claim_ledger_publication"]["manifest_schema"]
    manifest, _raw = _notification_json(
        git, worker, paths["manifest"], specification["required_keys"]
    )
    if (
        manifest["schema_version"] != specification["schema_version"]
        or manifest["classification"] != "consumed_historical_diagnostic_only"
        or manifest["parent_commit"] != execution
        or manifest["authorization_sha256"]
        != _sha(git.read_blob(execution, AUTHORIZATION_PATH))
        or manifest["self_reference"]
        != "containing_commit_resolved_from_Git_object_not_embedded"
    ):
        raise AuthorizationError("worker manifest identity differs")
    _notification_checkpoint_metadata(manifest["startup_checkpoint"], operation)
    _closed_object(
        manifest["sealed_startup"], set(specification["sealed_startup_exact_keys"])
    )
    entries = manifest["files"]
    if (
        type(entries) is not list
        or any(type(entry) is not dict for entry in entries)
        or [entry.get("path") for entry in entries]
        != sorted(path for path in finals if path != paths["manifest"])
    ):
        raise AuthorizationError("worker manifest five-file inventory differs")
    for entry in entries:
        _closed_object(entry, {"path", "git_blob", "sha256", "bytes"})
        raw = git.read_blob(worker, entry["path"])
        if (
            type(entry["bytes"]) is not int
            or entry["bytes"] != len(raw)
            or entry["git_blob"] != git.oid(worker, entry["path"])
            or entry["sha256"] != _sha(raw)
        ):
            raise AuthorizationError("worker manifest file binding differs")
    claim_spec = operation["claim_ledger_publication"]["claim_schema"]
    claim, raw = _notification_json(
        git, worker, paths["claim"], claim_spec["required_keys"]
    )
    if (
        claim["schema_version"] != claim_spec["schema_version"]
        or type(claim["bindings"]) is not dict
        or claim["bindings"].get("execution_authority_M_A_H13") != execution
        or claim["bindings"].get("lease_ref") != LEASE_REF
        or claim["bindings"].get("classification")
        != "consumed_historical_diagnostic_only"
    ):
        raise AuthorizationError("worker claim binding differs")
    _valid_utc(claim["claimed_at"])
    ledger = _notification_ledger_metadata(
        git.read_blob(worker, paths["ledger"]), operation
    )
    if (
        ledger["pending_forecast"]
        or not ledger["stopped_for_audit"]
        or ledger["scored_target_count"] < 1
    ):
        raise AuthorizationError("worker ledger has no completed exact capture")
    events = [
        _json(line) for line in git.read_blob(worker, paths["ledger"]).splitlines()
    ]
    _notification_startup_metadata(
        git,
        git.read_blob(worker, paths["startup"]),
        manifest,
        claim,
        raw,
        events,
        execution,
        operation,
    )
    captures = [
        event
        for event in events
        if event["event_kind"] == "historical_6of6_candidate_detected"
    ]
    rows = [
        event["payload"]
        for event in events
        if event["event_kind"] == "target_revealed_scored"
    ]
    if (
        len(captures) != 1
        or captures[0] != events[-1]
        or events[-2]["event_kind"] != "target_revealed_scored"
        or any(event["bindings"] != claim["bindings"] for event in events)
        or events[0]["payload"]["claim_sha256"] != _sha(raw)
        or any(row["exact_final6_opportunities"] for row in rows[:-1])
    ):
        raise AuthorizationError(
            "worker capture is not the first terminal frozen cohort"
        )
    row, capture = rows[-1], captures[0]["payload"]
    opportunities = row["exact_final6_opportunities"]
    if (
        type(opportunities) is not list
        or len(opportunities) != 1
        or opportunities[0]["hits"] != 6
        or type(opportunities[0]["hits"]) is not int
        or capture["opportunities"] != opportunities
        or capture["target_draw_date"] != row["target_draw_date"]
        or capture["forecast_payload_sha256"] != row["forecast_payload_sha256"]
        or capture["audit_status"] != "independent_leakage_audit_pending"
        or capture["eligible_evidence"] is not False
        or capture["global_stop_search"] is not True
    ):
        raise AuthorizationError("worker exact-capture metadata differs")
    opportunity = opportunities[0]
    final6 = _notification_six(opportunity["final6"])
    if final6 != _notification_six(row["actual"]) or row[
        "forecast_payload_sha256"
    ] != _sha(_canonical(row["forecast_payload"]) + b"\n"):
        raise AuthorizationError("capture does not bind its frozen Final-6")
    frozen = row["forecast_payload"]
    expected_producers = [
        forecast["model_name"]
        for forecast in frozen["forecasts"]
        if forecast["final6"] == final6
    ]
    if (
        opportunity["producer_model_names"] != expected_producers
        or opportunity["primary_producer"] != expected_producers[0]
        or opportunity["forecast_sha256_by_producer"]
        != {
            name: frozen["forecast_sha256_by_model"][name]
            for name in expected_producers
        }
    ):
        raise AuthorizationError("capture producer grouping differs")
    report_raw = git.read_blob(worker, paths["json"])
    report = _json(report_raw)
    _closed_object(
        report,
        {
            "ledger",
            "opportunities",
            "schema_version",
            "processed_target_count",
            "targets",
            "audit",
            "audit_publication",
            "disposition",
            "promotion_authority",
            "stop_reason",
            "cyclic_control",
            "primary_metric",
            "bindings",
            "scopes",
            "classification",
            "complete_registered_scope",
            "statistical_fingerprint_sha256",
            "gates",
            "classification_zh",
            "best_final6_by_model",
            "fair_baselines",
            "partial_descriptive",
            "model_order",
            "opportunity_interpretation",
            "claim_sha256",
            "seed",
            "eligible_evidence",
            "multiplicity",
            "experiment_id",
            "annual_descriptive_only",
            "model_version",
            "required_pure_core_sha256",
            "candidate_audit_handoff",
            "expected_target_count",
            "operational_contract_sha256",
            "scope_order",
            "exclusions",
            "independent_leakage_audit",
        },
    )
    if (
        report_raw != _canonical(report) + b"\n"
        or report.get("classification") != "consumed_historical_diagnostic_only"
        or report.get("model_version") != "v13.0.0"
        or report.get("ledger") != ledger
        or report.get("claim_sha256") != _sha(raw)
        or report.get("bindings") != claim["bindings"]
        or report.get("processed_target_count") != len(rows)
        or report.get("independent_leakage_audit") != "pending"
        or report.get("audit_publication") != "pending_git_integration"
    ):
        raise AuthorizationError("worker final report does not bind its capture")
    report_rows = report.get("targets")
    expected_rows = []
    for event in events:
        if event["event_kind"] == "target_revealed_scored":
            expected_rows.append(
                {
                    **event["payload"],
                    "scored_event_sequence": event["sequence"],
                    "scored_event_sha256": event["event_sha256"],
                }
            )
    if report_rows != expected_rows:
        raise AuthorizationError("worker report omitted or changed a frozen score row")
    return row, claim


def _notification_publication_time(git: GitRepository, publication: str) -> str:
    """Bind claim time to the exact already-audited publication Git object."""
    publication = _oid(publication)
    raw = git.run("cat-file", "commit", publication)
    if (
        type(raw) is not bytes
        or b"\n\n" not in raw
        or hashlib.sha1(
            b"commit " + str(len(raw)).encode("ascii") + b"\x00" + raw
        ).hexdigest()
        != publication
    ):
        raise AuthorizationError("notification publication raw Git identity differs")
    headers = raw.split(b"\n\n", 1)[0].split(b"\n")
    committers = [line for line in headers if line.startswith(b"committer ")]
    if len(committers) != 1:
        raise AuthorizationError("notification publication committer is ambiguous")
    parsed = re.fullmatch(
        rb"committer [^<>\x00\r\n]+ <[^<>\x00\r\n]+> ([0-9]+) [+-]([0-9]{2})([0-9]{2})",
        committers[0],
    )
    if parsed is None or int(parsed[2]) > 23 or int(parsed[3]) > 59:
        raise AuthorizationError("notification publication committer instant differs")
    try:
        timestamp = datetime.fromtimestamp(int(parsed[1]), UTC).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        _valid_utc(timestamp)
    except (ValueError, OverflowError, OSError, AttemptError):
        raise AuthorizationError(
            "notification publication committer instant differs"
        ) from None
    return timestamp


def verify_notification_publication(
    repository: Path, *, api: _NotificationHTTP
) -> object:
    """Read-only post-audit proof. Never creates historical execution authority."""
    if type(api) is not _NotificationHTTP or api._terminal:
        raise AuthorizationError("notification metadata adapter identity differs")
    git = GitRepository(repository)
    git.require_full_clean()
    if repository != Path(__file__).resolve().parents[2]:
        raise AuthorizationError("notification source must be its exact runtime clone")
    head = git.head()
    _remote_protection(api)
    if _remote_main(api) != head:
        raise AuthorizationError("notification requires exact protected current main")
    science, operation = _registered_authorities(git, head)
    capture_spec = operation["capture_audit_notification"]
    paths = [item["path"] for item in _tree_metadata(git, head)]
    candidates = [
        path
        for path in paths
        if path.startswith("reports/historical-6of6-candidate__")
        and path.endswith("__v13.0.0.json")
    ]
    if len(candidates) != 1:
        raise AuthorizationError("exactly one completed V13 capture bundle is required")
    bundle_path = candidates[0]
    bundle, bundle_raw = _notification_json(
        git, head, bundle_path, capture_spec["bundle_schema"]["required_keys"]
    )
    target = bundle["target_draw_date"]
    if (
        type(target) is not str
        or date.fromisoformat(target).isoformat() != target
        or not "2020-01-01" <= target <= "2025-12-31"
        or date.fromisoformat(target).weekday() not in {2, 5}
    ):
        raise AuthorizationError(
            "notification target is not a registered historical date"
        )
    producers = bundle["producer_model_names"]
    fixed_order = science["identity"]["producer_order"]
    if (
        type(producers) is not list
        or not producers
        or producers != [name for name in fixed_order if name in producers]
        or bundle["primary_model_name"] != producers[0]
    ):
        raise AuthorizationError("capture producers are not unique fixed-order names")
    final6 = _notification_six(bundle["final6"])
    expected_paths = {
        role: template.format(target_date=target, primary_model_name=producers[0])
        for role, template in capture_spec["paths"].items()
    }
    if (
        bundle_path != expected_paths["candidate_bundle"]
        or bundle["audit_json_path"] != expected_paths["independent_audit_json"]
        or bundle["audit_markdown_path"] != expected_paths["independent_audit_markdown"]
    ):
        raise AuthorizationError("capture bundle paths differ from reserved literals")
    if any(
        path.startswith("evidence/research_notifications/v13.0.0/") for path in paths
    ):
        raise AuthorizationError("prior notification evidence cannot be adopted")
    audit_path, markdown_path = bundle["audit_json_path"], bundle["audit_markdown_path"]
    audit, audit_raw = _notification_json(
        git, head, audit_path, capture_spec["audit_json_schema"]["required_keys"]
    )
    markdown_raw = git.read_blob(head, markdown_path)
    expected_common = {
        "experiment_id": science["identity"]["experiment"],
        "model_version": "v13.0.0",
        "target_draw_date": target,
        "final6": final6,
        "primary_model_name": producers[0],
        "producer_model_names": producers,
        "worker_artifact_commit": _oid(bundle["worker_artifact_commit"]),
        "execution_commit": _oid(bundle["execution_commit"]),
        "claim_sha256": _digest(bundle["claim_sha256"]),
        "ledger_sha256": _digest(bundle["ledger_sha256"]),
        "forecast_payload_sha256": _digest(bundle["forecast_payload_sha256"]),
    }
    if (
        any(audit[key] != value for key, value in expected_common.items())
        or bundle["schema_version"] != capture_spec["bundle_schema"]["schema_version"]
        or bundle["classification"] != "consumed_historical_diagnostic_only"
        or bundle["experiment_id"] != science["identity"]["experiment"]
        or bundle["model_version"] != "v13.0.0"
        or bundle["audit_verdict"] != "pass"
        or audit["schema_version"]
        != capture_spec["audit_json_schema"]["schema_version"]
        or audit["verdict"] != "pass"
        or audit["registration_commit"] != R13
        or audit["scientific_contract_sha256"] != FINGERPRINT
        or audit["operational_contract_sha256"] != OPERATIONAL_SHA256
        or any(
            type(audit[key]) is not int or audit[key] != 0
            for key in ("blocker_count", "major_count")
        )
    ):
        raise AuthorizationError("capture audit identity or pass verdict differs")
    if (
        bundle["audit_json_sha256"] != _sha(audit_raw)
        or bundle["audit_markdown_sha256"] != _sha(markdown_raw)
        or markdown_raw != render_capture_audit_markdown(audit)
    ):
        raise AuthorizationError("capture audit hashes or exact human rendering differ")
    _valid_utc(audit["audited_at"])
    if type(audit["limitations"]) is not list or not audit["limitations"]:
        raise AuthorizationError("capture audit must disclose trust limitations")
    for limitation in audit["limitations"]:
        _provenance_identifier(limitation)
    parents = git.parents(head)
    if len(parents) != 2:
        raise AuthorizationError("capture publication main must be an ordinary merge")
    base, source = parents
    _require_normal_merge(git, head, base, source)
    publication_paths = {audit_path, markdown_path, bundle_path}
    if (
        git.parents(source) != (base,)
        or set(git.changes(base, source)) != {("A", path) for path in publication_paths}
        or any(
            _notification_blob_origin(git, head, path) != source
            for path in publication_paths
        )
    ):
        raise AuthorizationError(
            "capture publication must be exactly three immutable ADD files"
        )
    worker, execution = bundle["worker_artifact_commit"], bundle["execution_commit"]
    if not git.ancestor(worker, base) or not git.ancestor(execution, worker):
        raise AuthorizationError(
            "capture publication lacks unchanged executed artifact ancestry"
        )
    auth, contributors = _notification_authorization_metadata(git, api, execution, head)
    if audit["source_contributors"] != contributors:
        raise AuthorizationError(
            "capture audit omitted actual scientific/source contributors"
        )
    reviewer = _provenance_identifier(audit["reviewer_agent_id"])
    session = _provenance_identifier(audit["review_session_id"])
    if reviewer in {person["agent_id"] for person in contributors} or session in {
        person["session_id"] for person in contributors
    }:
        raise AuthorizationError("capture auditor is a scientific/source author")
    capture_authors = _capture_publication_authors(
        git.run("cat-file", "commit", source)
    )
    if {"agent_id": reviewer, "session_id": session} not in capture_authors:
        raise AuthorizationError("capture publication omitted its audit content author")
    reviews = _notification_publication_reviews(
        git,
        api,
        head=head,
        source=source,
        base=base,
        closure_sha256=auth["runtime_dependency_closure_sha256"],
        excluded=contributors + capture_authors,
    )
    dimensions = audit["dimensions"]
    _closed_object(
        dimensions, set(science["stopping_and_notifications"]["audit_dimensions"])
    )
    for dimension in dimensions.values():
        _closed_object(dimension, {"verdict", "evidence"})
        if (
            dimension["verdict"] != "pass"
            or type(dimension["evidence"]) is not list
            or not dimension["evidence"]
        ):
            raise AuthorizationError("independent capture audit dimension did not pass")
        for reference in dimension["evidence"]:
            if (
                _notification_reference_digest(
                    git,
                    reference,
                    head=head,
                    execution=execution,
                    worker=worker,
                    auth=auth,
                    operation=operation,
                )
                != reference["sha256"]
            ):
                raise AuthorizationError("capture audit evidence digest differs")
    row, claim = _notification_capture_artifacts(
        git, head, worker, execution, operation
    )
    opportunity = row["exact_final6_opportunities"][0]
    if (
        row["target_draw_date"] != target
        or row["forecast_payload_sha256"] != bundle["forecast_payload_sha256"]
        or opportunity["final6"] != final6
        or opportunity["producer_model_names"] != producers
    ):
        raise AuthorizationError(
            "published capture does not match frozen scored cohort"
        )
    worker_paths = operation["claim_ledger_publication"]["worker_outputs"]
    if (
        _sha(git.read_blob(worker, worker_paths["claim"])) != bundle["claim_sha256"]
        or _sha(git.read_blob(worker, worker_paths["ledger"]))
        != bundle["ledger_sha256"]
    ):
        raise AuthorizationError("published capture claim or ledger hash differs")
    bindings = claim["bindings"]
    extras = {
        "startup_checkpoint",
        "verified_facts_sha256",
        "execution_authority_M_A_H13",
        "authorization_source_A_H_s13",
        "authorization_sha256",
        "lease_ref",
        "lease_commit_L_H13",
        "nonce_hex",
        "seed",
        "classification",
    }
    _closed_object(bindings, set(auth) | extras)
    if (
        any(bindings[key] != value for key, value in auth.items())
        or bindings["authorization_source_A_H_s13"] != git.parents(execution)[1]
        or bindings["authorization_sha256"]
        != _sha(git.read_blob(execution, AUTHORIZATION_PATH))
        or type(bindings["seed"]) is not int
        or bindings["seed"] != 649
    ):
        raise AuthorizationError("capture claim altered original authorization")
    facts_preimage = claim["verified_authorization_facts"]
    _closed_object(
        facts_preimage,
        {
            "repository",
            "execution_commit",
            "source_commit",
            "payload",
            "authorization_sha256",
            "authorization_review_records",
        },
    )
    if (
        _sha(_canonical(facts_preimage)) != bindings["verified_facts_sha256"]
        or facts_preimage["payload"] != auth
        or facts_preimage["execution_commit"] != execution
        or facts_preimage["source_commit"] != git.parents(execution)[1]
        or facts_preimage["authorization_sha256"] != bindings["authorization_sha256"]
    ):
        raise AuthorizationError("capture claim facts preimage differs")
    if (
        type(facts_preimage["repository"]) is not str
        or not Path(facts_preimage["repository"]).is_absolute()
        or ".." in Path(facts_preimage["repository"]).parts
    ):
        raise AuthorizationError("archived execution clone path is invalid")
    _verify_reviews(
        api,
        facts_preimage["authorization_review_records"],
        implementation=git.parents(execution)[1],
        merge=execution,
        base=auth["implementation_merge"],
        closure_sha256=auth["runtime_dependency_closure_sha256"],
        git=git,
        phase="A_H_s13",
    )
    lease = _oid(bindings["lease_commit_L_H13"])
    _digest(bindings["nonce_hex"])
    if git.parents(lease) != (execution,) or git.tree(lease) != git.tree(execution):
        raise AuthorizationError("archived lease commit topology differs")
    raw_lease = git.run("cat-file", "commit", lease)
    message = raw_lease.split(b"\n\n", 1)[1]
    lease_body = _json(message)
    if message != _canonical(lease_body) + b"\n" or lease_body != {
        "schema_version": "lotto649-v13-consumption-lease-v1",
        "authorization_seal_sha256": bindings["authorization_sha256"],
        "canonical_command": COMMAND,
        "execution_authority_M_A": execution,
        "nonce_hex": bindings["nonce_hex"],
    }:
        raise AuthorizationError("archived lease content differs")
    headers = raw_lease.split(b"\n\n", 1)[0].split(b"\n")
    author_prefix = b"author LOTTO649 V13 Consumption Lease <lotto649-v13-lease@users.noreply.github.com> "
    if (
        len(headers) != 4
        or not headers[2].startswith(author_prefix)
        or headers[3] != b"committer " + headers[2][len(b"author ") :]
        or re.fullmatch(rb"[0-9]+ \+0000", headers[2][len(author_prefix) :]) is None
    ):
        raise AuthorizationError("archived lease raw header identity differs")
    epoch = int(headers[2][len(author_prefix) :].split(b" ")[0])
    lease_time = datetime.fromtimestamp(epoch, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    person = {
        "name": "LOTTO649 V13 Consumption Lease",
        "email": "lotto649-v13-lease@users.noreply.github.com",
        "date": lease_time,
    }
    expected_oid, expected_raw, _projection = _lease_request_parts(
        {
            "tree": git.tree(execution),
            "parents": [execution],
            "author": person,
            "committer": dict(person),
            "message": message.decode("utf-8"),
        }
    )
    if expected_oid != lease or expected_raw != raw_lease:
        raise AuthorizationError("archived lease local raw OID binding differs")
    records = []
    try:
        for path in sorted(
            publication_paths
            | {
                worker_paths[role]
                for role in (
                    "startup",
                    "claim",
                    "ledger",
                    "json",
                    "markdown",
                    "manifest",
                )
            }
        ):
            records.append(_notification_read_immutable(git, head, path))
        proof = {
            "repository": str(repository),
            "publication": head,
            "publication_committer_time": _notification_publication_time(git, head),
            "source": source,
            "base": base,
            "tree": git.tree(head),
            "audit": audit,
            "audit_path": audit_path,
            "audit_sha256": _sha(audit_raw),
            "bundle_path": bundle_path,
            "bundle_sha256": _sha(bundle_raw),
            "runtime_closure": auth["runtime_dependency_closure"],
            "runtime_closure_sha256": auth["runtime_dependency_closure_sha256"],
            "reviews": reviews,
            "history_through": row["forecast_payload"]["history_through"],
            "training_cutoff_date": row["forecast_payload"]["training_cutoff_date"],
            "immutable_files": [
                {
                    "path": record["path"].relative_to(repository).as_posix(),
                    "sha256": _sha(record["raw"]),
                }
                for record in records
            ],
        }
        facts = object.__new__(_VerifiedNotificationFacts)
        with _CAPABILITY_LOCK:
            _NOTIFICATION_FACTS[facts] = {
                "proof": proof,
                "stamp": _canonical(proof),
                "files": records,
                "closed": False,
                "poisoned": False,
                "started": False,
                "api": api,
                "invocation": None,
            }
        return facts
    except BaseException:
        for record in records:
            os.close(record["fd"])
            os.close(record["parent_fd"])
        raise


_PRODUCTION_NOTIFICATION_ISSUANCE = []


def _require_production_notification_issuance(
    directory: Path, identity: dict[str, Any], committer_time: str
) -> None:
    """Called inside _issue_notification_files before every production file effect."""
    with _CAPABILITY_LOCK:
        matches = [
            state
            for state in _PRODUCTION_NOTIFICATION_ISSUANCE
            if state["identity"] is identity
        ]
        if len(matches) != 1:
            raise AuthorizationError("production notification identity was not issued")
        permit = matches[0]
        if (
            permit["used"]
            or permit["directory"] != directory
            or permit["committer_time"] != committer_time
            or permit["stamp"] != _canonical(identity)
        ):
            raise AuthorizationError(
                "production notification issuance changed or consumed"
            )
        permit["used"] = True
    facts_state = _notification_facts(permit["facts"])
    if (
        facts_state["started"] is not True
        or facts_state["invocation"] is not None
        or committer_time != facts_state["proof"]["publication_committer_time"]
    ):
        raise AuthorizationError("production notification issuance state differs")


def _require_notification_transport_post(api: object, suffix: str, raw: bytes) -> None:
    """A direct transport call cannot bypass the issued durable protocol phase."""
    with _CAPABILITY_LOCK:
        if type(api) is not _NotificationHTTP or api not in _NOTIFICATION_TRANSPORTS:
            raise AuthorizationError("notification transport purpose is unissued")
        transport = _NOTIFICATION_TRANSPORTS[api]
        if transport["facts"] is None or transport["invocation"] is None:
            raise AuthorizationError("read-only notification transport cannot POST")
    facts = _notification_facts(transport["facts"])
    invocation = _notification_state(transport["invocation"])
    if (
        facts["api"] is not api
        or facts["invocation"] is not transport["invocation"]
        or invocation["synthetic"] is not False
        or invocation["reference"] != _NOTIFICATION_REF
        or invocation["identity"]["audited_publication_commit"]
        != facts["proof"]["publication"]
        or _canonical(invocation["identity"]) != transport["identity_stamp"]
    ):
        raise AuthorizationError("notification transport integrity or purpose differs")
    if suffix == "/git/commits":
        expected, sequence, consumed = (
            invocation["commit_bytes"],
            2,
            invocation["commit_consumed"],
        )
    elif suffix == "/git/refs":
        expected, sequence, consumed = (
            invocation["ref_bytes"],
            5,
            invocation["ref_consumed"],
        )
    else:
        raise AuthorizationError("notification transport route is not permitted")
    if (
        type(raw) is not bytes
        or raw != expected
        or invocation["sequence"] != sequence
        or consumed is not True
    ):
        raise AuthorizationError("notification POST lacks its exact durable intent")
    _startup_verify_owned(invocation["intent_file"])
    _startup_verify_owned(invocation["journal_file"])
    for record in facts["files"]:
        _notification_check_immutable(record)


def _notification_safe_directory(root: Path) -> Path:
    directory = root / "evidence/research_notifications/v13.0.0"
    descriptor, _records = _startup_directory_chain(root)
    try:
        for component in ("evidence", "research_notifications", "v13.0.0"):
            try:
                os.mkdir(component, mode=0o700, dir_fd=descriptor)
                os.fsync(descriptor)
            except FileExistsError:
                pass
            following = os.open(
                component,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                dir_fd=descriptor,
            )
            info = os.fstat(following)
            if not stat.S_ISDIR(info.st_mode) or info.st_mode & 0o022:
                os.close(following)
                raise AuthorizationError("notification output directory is unsafe")
            os.close(descriptor)
            descriptor = following
        os.fsync(descriptor)
        return directory
    finally:
        os.close(descriptor)


def _prepare_production_notification(facts: object, api: _NotificationHTTP) -> object:
    state = _notification_facts(facts)
    proof = state["proof"]
    with _CAPABILITY_LOCK:
        if (
            state["started"]
            or state["api"] is not api
            or type(api) is not _NotificationHTTP
        ):
            raise AuthorizationError(
                "notification invocation already started or changed"
            )
        state["started"] = True
    try:
        git = GitRepository(Path(proof["repository"]))
        git.require_full_clean()
        _verify_worktree_runtime(git, proof["publication"], proof["runtime_closure"])
        for record in state["files"]:
            _notification_check_immutable(record)
        _require_default_notification_environment()
        _remote_protection(api)
        if (
            git.head() != proof["publication"]
            or _remote_main(api) != proof["publication"]
        ):
            raise AuthorizationError(
                "audited publication is no longer exact protected main"
            )
        status, absent = api.get_ref(_NOTIFICATION_REF)
        if (
            type(status) is not int
            or status != 404
            or absent != {"message": "Not Found"}
        ):
            raise AuthorizationError("notification requires fresh exact direct ref404")
        identity = {
            "experiment_id": "V13_post_rng_main_set_overlap",
            "model_version": "v13.0.0",
            "target_draw_date": proof["audit"]["target_draw_date"],
            "notification_kind": _NOTIFICATION_KIND,
            "candidate_bundle_path": proof["bundle_path"],
            "candidate_bundle_sha256": proof["bundle_sha256"],
            "audit_json_path": proof["audit_path"],
            "audit_json_sha256": proof["audit_sha256"],
            "audited_publication_commit": proof["publication"],
            "publication_tree_oid": proof["tree"],
            "scientific_contract_sha256": FINGERPRINT,
            "operational_contract_sha256": OPERATIONAL_SHA256,
            "nonce_hex": secrets.token_hex(32),
        }
        committer_time = proof["publication_committer_time"]
        if _notification_publication_time(git, proof["publication"]) != committer_time:
            raise AuthorizationError("issued publication committer instant changed")
        directory = _notification_safe_directory(git.root)
        with _CAPABILITY_LOCK:
            _PRODUCTION_NOTIFICATION_ISSUANCE.append(
                {
                    "identity": identity,
                    "stamp": _canonical(identity),
                    "directory": directory,
                    "committer_time": committer_time,
                    "facts": facts,
                    "used": False,
                }
            )
        invocation = _issue_notification_files(
            directory, identity, committer_time, synthetic=False
        )
        with _CAPABILITY_LOCK:
            state["invocation"] = invocation
            _NOTIFICATION_TRANSPORTS[api] = {
                "facts": facts,
                "invocation": invocation,
                "identity_stamp": _canonical(identity),
            }
        return invocation
    except BaseException:  # noqa: BLE001 -- terminal poison, never disclose exception text.
        state["poisoned"] = True
        raise AuthorizationError("notification preparation failed; no retry") from None


def _notification_git_owned(git: GitRepository, invocation: object) -> None:
    """Same safe Git checks, with only currently owned intent/journal permitted."""
    state = _notification_state(invocation)
    for role in ("intent_file", "journal_file"):
        _startup_verify_owned(state[role])
    git_directory = git.root / ".git"
    if (
        not git_directory.is_dir()
        or any(
            parent.is_symlink() for parent in (git_directory, *git_directory.parents)
        )
        or any(
            os.path.lexists(git_directory / path)
            for path in (
                "info/grafts",
                "objects/info/alternates",
                "objects/info/http-alternates",
                "shallow",
            )
        )
    ):
        raise AuthorizationError("notification Git repository trust changed")
    allowed = {
        "core.repositoryformatversion",
        "core.filemode",
        "core.bare",
        "core.logallrefupdates",
        "core.ignorecase",
        "core.precomposeunicode",
        "remote.origin.url",
        "remote.origin.fetch",
    }
    keys = (
        git.run("config", "--local", "--name-only", "--list")
        .decode("utf-8")
        .splitlines()
    )
    if (
        any(
            key not in allowed
            and re.fullmatch(r"branch\.[A-Za-z0-9/_-]+\.(?:remote|merge)", key) is None
            for key in keys
        )
        or git.text("rev-parse", "--is-shallow-repository") != "false"
        or git.text("rev-parse", "--show-object-format") != "sha1"
        or git.run("for-each-ref", "--format=%(refname)", "refs/replace")
    ):
        raise AuthorizationError("notification Git configuration changed")
    if git.run("status", "--porcelain=v1", "-z", "--untracked-files=no"):
        raise AuthorizationError("notification tracked source changed")
    others = {
        _relative(path.decode("utf-8"))
        for path in git.run("ls-files", "--others", "-z").split(b"\0")
        if path
    }
    owned = {
        state["paths"][role].relative_to(git.root).as_posix()
        for role in ("intent", "journal")
    }
    if others != owned or any(
        os.path.lexists(state["paths"][role]) for role in ("result",)
    ):
        raise AuthorizationError(
            "notification output lacks current descriptor ownership"
        )


def _verify_notification_pre_send(
    facts: object, invocation: object, api: _NotificationHTTP
) -> None:
    state = _notification_facts(facts)
    proof = state["proof"]
    current = _notification_state(invocation)
    if (
        state["api"] is not api
        or state["invocation"] is not invocation
        or current["own_ref_201"] is not True
        or current["identity"]["audited_publication_commit"] != proof["publication"]
    ):
        raise AuthorizationError("notification winner provenance differs")
    git = GitRepository(Path(proof["repository"]))
    _notification_git_owned(git, invocation)
    if (
        git.head() != proof["publication"]
        or git.tree(proof["publication"]) != proof["tree"]
    ):
        raise AuthorizationError("notification audited publication changed")
    _verify_worktree_runtime(git, proof["publication"], proof["runtime_closure"])
    for record in state["files"]:
        _notification_check_immutable(record)
    _require_default_notification_environment()
    _remote_protection(api)
    if _remote_main(api) != proof["publication"]:
        raise AuthorizationError("notification remote main changed after own claim")
    status, response = api.get_ref(_NOTIFICATION_REF)
    if type(status) is not int or status != 200:
        raise AuthorizationError("notification owned winner ref became uncertain")
    _verify_notification_ref(_NOTIFICATION_REF, current["expected"], response)


def _notification_chinese_message(facts: object) -> tuple[str, str]:
    proof = _notification_facts(facts)["proof"]
    audit = proof["audit"]
    subject = "历史严格回测：V13.0.0 Final-6 6/6 已通过独立审计"
    body = (
        "本结果为历史严格回测，属于已消耗的历史诊断，不是下一期预测或稳定中奖能力。\n"
        + "目标开奖日期："
        + audit["target_draw_date"]
        + "\n"
        + "模型版本：v13.0.0\n匹配模型："
        + "、".join(audit["producer_model_names"])
        + "\n"
        + "训练截止日期："
        + proof["training_cutoff_date"]
        + "\n"
        + "可见历史截止日期："
        + proof["history_through"]
        + "\n"
        + "已冻结 Final-6："
        + "、".join(str(n) for n in audit["final6"])
        + "；主号码命中 6/6。\n"
        + "独立审计：11 项维度通过，0 阻断项、0 重大问题。\n"
        + "审计人员："
        + audit["reviewer_agent_id"]
        + "；会话："
        + audit["review_session_id"]
        + "\n"
        + "冻结工作产物提交："
        + audit["worker_artifact_commit"]
        + "\n"
        + "已审查发布提交："
        + proof["publication"]
        + "\n"
        + "完整证据：https://github.com/"
        + REPOSITORY
        + "/blob/"
        + proof["publication"]
        + "/"
        + proof["bundle_path"]
        + "\n"
        + "公平且不可预测的彩票仍是默认解释；该历史结果不能证明未来有优势。\n"
    )
    return subject, body


def _close_notification_facts(facts: object) -> None:
    if (
        type(facts) is not _VerifiedNotificationFacts
        or facts not in _NOTIFICATION_FACTS
    ):
        return
    state = _NOTIFICATION_FACTS[facts]
    if state["closed"]:
        return
    state["closed"] = True
    for record in state["files"]:
        os.close(record["fd"])
        os.close(record["parent_fd"])


def notify_audited_capture() -> int:
    """Separate fixed no-argument post-audit action; never invokes historical code."""
    facts = None
    try:
        if _DRAFT_INCOMPLETE or not (
            sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
        ):
            raise AuthorizationError("notification requires reviewed isolated runtime")
        _require_default_notification_environment()
        repository = Path(__file__).resolve().parents[2]
        _precredential_local_runtime(repository)
        api = _NotificationHTTP(os.environ.get("GH_TOKEN", ""))
        facts = verify_notification_publication(repository, api=api)
        invocation = _prepare_production_notification(facts, api)

        def send_bound_capture(_subject: str, _body: str) -> bool:
            # The driver has consumed its durable send slot. No caller text/route.
            state = _notification_state(invocation)
            if state["send_consumed"] is not True or state["sequence"] != 8:
                raise AuthorizationError(
                    "default sender lacks consumed durable send intent"
                )
            _verify_notification_pre_send(facts, invocation, api)
            subject, body = _notification_chinese_message(facts)
            return _default_notification(subject, body)

        result = _drive_notification(
            invocation,
            api,
            send_bound_capture,
            lambda: _verify_notification_pre_send(facts, invocation, api),
        )
        return 0 if result["result"] == "sent" else 1
    except BaseException:  # noqa: BLE001 -- preserve terminal uncertainty without secrets.
        # Never stringify transport/SMTP exceptions or the process environment.
        print(
            "V13 notification failed or uncertain; evidence retained; no retry.",
            file=sys.stderr,
        )
        return 1
    finally:
        if facts is not None:
            _close_notification_facts(facts)


def _notification_frozen_bytes(
    frozen: object, operation: Mapping[str, Any], *, bindings: dict[str, Any]
) -> None:
    """Authenticate closed frozen structures; never select, solve, fit or score."""
    specification = operation["claim_ledger_publication"]
    _closed_object(frozen, set(specification["frozen_payload_exact_keys"]))
    if (
        frozen["schema_version"] != "lotto649-v13.0.0-frozen-forecast-v1"
        or frozen["classification"] != "consumed_historical_diagnostic_only"
        or frozen["model_version"] != "v13.0.0"
        or frozen["bindings"] != bindings
    ):
        raise AuthorizationError("notification frozen forecast identity differs")
    target, cutoff = frozen["target_draw_date"], frozen["history_through"]
    if (
        type(target) is not str
        or type(cutoff) is not str
        or date.fromisoformat(target).isoformat() != target
        or date.fromisoformat(cutoff).isoformat() != cutoff
        or cutoff >= target
        or frozen["training_cutoff_date"] != cutoff
        or not "2020-01-01" <= target <= "2025-12-31"
        or date.fromisoformat(target).weekday() not in {2, 5}
    ):
        raise AuthorizationError("notification frozen chronology metadata differs")
    _digest(frozen["visible_prefix_sha256"])
    if (
        type(frozen["visible_prefix_draw_count"]) is not int
        or not 1 <= frozen["visible_prefix_draw_count"] <= 4444
    ):
        raise AuthorizationError("notification frozen prefix count differs")
    forecasts = frozen["forecasts"]
    order = [
        "v13_post_rng_main_set_overlap",
        "v13_cyclic_anchor_overlap_control",
        "ensemble_v1.0.0",
        "random_v1.0.0",
    ]
    if type(forecasts) is not list or len(forecasts) != 4:
        raise AuthorizationError("notification needs four frozen producers")
    _closed_object(frozen["forecast_sha256_by_model"], set(order))
    for index, forecast in enumerate(forecasts):
        _closed_object(forecast, set(specification["forecast_exact_keys"]))
        if (
            forecast["model_name"] != order[index]
            or forecast["model_version"] != ("v13.0.0" if index < 2 else "v1.0.0")
            or type(forecast["feature_set"]) is not str
            or not forecast["feature_set"]
            or _sha(_canonical(forecast) + b"\n")
            != frozen["forecast_sha256_by_model"][order[index]]
        ):
            raise AuthorizationError(
                "notification frozen producer or byte digest differs"
            )
        labels = {str(n) for n in range(1, 50)}
        _closed_object(forecast["probabilities"], labels)
        _closed_object(forecast["probability_hex"], labels)
        for label in labels:
            value = forecast["probabilities"][label]
            if (
                type(value) is not float
                or not 0 < value < 1
                or value.hex() != forecast["probability_hex"][label]
            ):
                raise AuthorizationError(
                    "notification frozen probability encoding differs"
                )
        ranking = forecast["ranking"]
        if (
            type(ranking) is not list
            or any(type(n) is not int for n in ranking)
            or sorted(ranking) != list(range(1, 50))
        ):
            raise AuthorizationError("notification full ranking labels differ")
        for k in (6, 12, 18):
            if forecast["top" + str(k)] != ranking[:k]:
                raise AuthorizationError("notification Top-K snapshot differs")
        _notification_six(forecast["final6"])
        state = forecast["scientific_state"]
        if index >= 2:
            if state is not None:
                raise AuthorizationError("notification comparator state differs")
        else:
            _closed_object(state, set(specification["scientific_state_exact_keys"]))
            _notification_six(state["source_anchor"])
            if index == 0 and state["transformed_anchor"] is not None:
                raise AuthorizationError("notification candidate anchor type differs")
            if index == 1:
                _notification_six(state["transformed_anchor"])
            if state["source_draw_date"] != cutoff:
                raise AuthorizationError("notification frozen source date differs")
            for key in ("training_pair_count", "training_overlap_sum"):
                if type(state[key]) is not int or state[key] < 0:
                    raise AuthorizationError("notification frozen count type differs")
            for key in ("scientific_projection_sha256", "counts_sha256"):
                _digest(state[key])
            for key in ("beta", "mean", "complement_mean", "log_z"):
                if (
                    type(state[key]) is not float
                    or state[key].hex() != state[key + "_hex"]
                ):
                    raise AuthorizationError(
                        "notification frozen scalar encoding differs"
                    )


def _notification_ledger_metadata(
    raw: bytes, operation: Mapping[str, Any]
) -> dict[str, Any]:
    """Byte/hash/phase validation only. Semantic scoring remains independent audit."""
    if type(raw) is not bytes or not raw or not raw.endswith(b"\n"):
        raise AuthorizationError("notification scientific ledger bytes incomplete")
    specification = operation["claim_ledger_publication"]
    allowed = specification["ledger_event_payload_keys"]
    previous, previous_time, bindings, pending, last_row = (
        "0" * 64,
        None,
        None,
        None,
        None,
    )
    count, stopped, last_target, top12_seen = 0, False, None, False
    lines = raw.splitlines()
    for sequence, line in enumerate(lines):
        event = _json(line)
        _closed_object(
            event,
            {
                "schema_version",
                "sequence",
                "recorded_at",
                "previous_event_sha256",
                "event_kind",
                "bindings",
                "payload",
                "event_sha256",
            },
        )
        if (
            event["schema_version"] != "lotto649-v13.0.0-attempt-ledger-v1"
            or type(event["sequence"]) is not int
            or event["sequence"] != sequence
            or event["previous_event_sha256"] != previous
            or line != _canonical(event)
            or _sha(
                _canonical(
                    {
                        key: value
                        for key, value in event.items()
                        if key != "event_sha256"
                    }
                )
            )
            != event["event_sha256"]
        ):
            raise AuthorizationError("notification scientific chain identity differs")
        instant = _valid_utc(event["recorded_at"])
        if previous_time is not None and instant < previous_time:
            raise AuthorizationError("notification scientific chronology regressed")
        previous_time, previous = instant, _digest(event["event_sha256"])
        kind, payload = event["event_kind"], event["payload"]
        if type(kind) is not str or kind not in allowed or stopped:
            raise AuthorizationError(
                "notification scientific phase is unregistered or after stop"
            )
        _closed_object(payload, set(allowed[kind]))
        if sequence == 0:
            if kind != "attempt_claimed" or type(event["bindings"]) is not dict:
                raise AuthorizationError(
                    "notification chain lacks its first permanent claim"
                )
            bindings = event["bindings"]
            _digest(payload["claim_sha256"])
            _notification_checkpoint_metadata(payload["startup_checkpoint"], operation)
        elif event["bindings"] != bindings or kind == "attempt_claimed":
            raise AuthorizationError(
                "notification chain binding changed or claim repeated"
            )
        elif kind == "prediction_frozen":
            if pending is not None or (
                last_row is not None and last_row["exact_final6_opportunities"]
            ):
                raise AuthorizationError(
                    "notification chain forecast occurred after pending/capture"
                )
            frozen = payload["forecast_payload"]
            _notification_frozen_bytes(frozen, operation, bindings=bindings)
            if _sha(_canonical(frozen) + b"\n") != payload[
                "forecast_payload_sha256"
            ] or (
                last_target is not None and frozen["target_draw_date"] <= last_target
            ):
                raise AuthorizationError(
                    "notification frozen target/hash repeated or changed"
                )
            pending = event
            last_target, top12_seen = frozen["target_draw_date"], False
        elif kind == "target_revealed_scored":
            if (
                pending is None
                or payload["target_draw_date"] != last_target
                or payload["forecast_payload"] != pending["payload"]["forecast_payload"]
                or payload["forecast_payload_sha256"]
                != pending["payload"]["forecast_payload_sha256"]
                or payload["prediction_frozen_event_sequence"] != pending["sequence"]
                or payload["prediction_frozen_event_sha256"] != pending["event_sha256"]
                or payload["prediction_generated_at"] != pending["recorded_at"]
            ):
                raise AuthorizationError(
                    "notification scored record lacks exact preceding freeze"
                )
            _notification_six(payload["actual"])
            if (
                type(payload["bonus"]) is not int
                or not 1 <= payload["bonus"] <= 49
                or payload["bonus"] in payload["actual"]
            ):
                raise AuthorizationError("notification frozen bonus domain differs")
            _closed_object(payload["fair_scores"], {"brier_score", "log_loss"})
            _closed_object(
                payload["cumulative_opportunities"],
                {"unique_opportunity_count", "nominal_fair_exact6_chance"},
            )
            if type(payload["scores"]) is not list or len(payload["scores"]) != 4:
                raise AuthorizationError("notification frozen score cohort incomplete")
            for index, score in enumerate(payload["scores"]):
                _closed_object(score, set(specification["score_exact_keys"]))
                forecast = payload["forecast_payload"]["forecasts"][index]
                if (
                    score["model_name"] != forecast["model_name"]
                    or score["model_version"] != forecast["model_version"]
                    or score["forecast_sha256"]
                    != payload["forecast_payload"]["forecast_sha256_by_model"][
                        forecast["model_name"]
                    ]
                ):
                    raise AuthorizationError(
                        "notification stored score identity differs"
                    )
                for metric in ("top6_hits", "top12_hits", "top18_hits", "final6_hits"):
                    if type(score[metric]) is not int or not 0 <= score[metric] <= 6:
                        raise AuthorizationError(
                            "notification stored hit domain differs"
                        )
            for collection in (
                payload["unique_final6"],
                payload["exact_final6_opportunities"],
            ):
                if type(collection) is not list:
                    raise AuthorizationError(
                        "notification opportunity collection differs"
                    )
                for opportunity in collection:
                    _closed_object(
                        opportunity,
                        {
                            "final6",
                            "primary_producer",
                            "producer_model_names",
                            "forecast_sha256_by_producer",
                            "hits",
                        },
                    )
                    _notification_six(opportunity["final6"])
            score_names = [score["model_name"] for score in payload["scores"]]
            exact_names = [
                name
                for opportunity in payload["exact_final6_opportunities"]
                for name in opportunity["producer_model_names"]
            ]
            declared_exact = [
                score["model_name"]
                for score in payload["scores"]
                if score["final6_hits"] == 6
            ]
            declared_top12 = [
                score["model_name"]
                for score in payload["scores"]
                if score["top12_hits"] == 6
            ]
            if (
                exact_names != [name for name in score_names if name in exact_names]
                or exact_names != declared_exact
                or payload["top12_all_six_producers"] != declared_top12
                or type(payload["unique_opportunity_count"]) is not int
                or not 1 <= payload["unique_opportunity_count"] <= 4
                or payload["unique_opportunity_count"] != len(payload["unique_final6"])
            ):
                raise AuthorizationError(
                    "notification stored opportunity metadata disagrees with stored scores"
                )
            last_row, pending, count = payload, None, count + 1
        elif kind == "historical_top12_all_six_detected":
            if (
                pending is not None
                or last_row is None
                or top12_seen
                or last_row["exact_final6_opportunities"]
                or payload["target_draw_date"] != last_target
                or payload["forecast_payload_sha256"]
                != last_row["forecast_payload_sha256"]
                or payload["producers"] != last_row["top12_all_six_producers"]
                or not payload["producers"]
                or payload["eligible_evidence"] is not False
            ):
                raise AuthorizationError("notification Top12 metadata grammar differs")
            top12_seen = True
        elif kind == "historical_6of6_candidate_detected":
            if (
                pending is not None
                or last_row is None
                or not last_row["exact_final6_opportunities"]
                or payload["opportunities"] != last_row["exact_final6_opportunities"]
                or payload["target_draw_date"] != last_target
                or payload["forecast_payload_sha256"]
                != last_row["forecast_payload_sha256"]
                or payload["audit_status"] != "independent_leakage_audit_pending"
                or payload["eligible_evidence"] is not False
                or payload["global_stop_search"] is not True
            ):
                raise AuthorizationError(
                    "notification terminal exact-capture grammar differs"
                )
            exact = last_row["exact_final6_opportunities"]
            if len(exact) != 1:
                raise AuthorizationError(
                    "notification capture must identify one actual main set"
                )
            opportunity = exact[0]
            frozen = last_row["forecast_payload"]
            producers = [
                forecast["model_name"]
                for forecast in frozen["forecasts"]
                if forecast["final6"] == opportunity["final6"]
            ]
            scores_by_name = {
                score["model_name"]: score for score in last_row["scores"]
            }
            if (
                type(opportunity["hits"]) is not int
                or opportunity["hits"] != 6
                or opportunity not in last_row["unique_final6"]
                or opportunity["final6"] != last_row["actual"]
                or not producers
                or opportunity["producer_model_names"] != producers
                or opportunity["primary_producer"] != producers[0]
                or opportunity["forecast_sha256_by_producer"]
                != {
                    name: frozen["forecast_sha256_by_model"][name] for name in producers
                }
                or any(
                    scores_by_name[name]["final6_hits"] != 6
                    or scores_by_name[name]["matched_final6"] != opportunity["final6"]
                    for name in producers
                )
            ):
                raise AuthorizationError(
                    "notification terminal capture identity differs"
                )
            stopped = True
        else:
            raise AuthorizationError("archived or noncapture worker cannot notify")
    if not stopped or pending is not None or count < 1:
        raise AuthorizationError("notification ledger has no terminal exact capture")
    return {
        "event_count": len(lines),
        "scored_target_count": count,
        "head_sha256": previous,
        "pending_forecast": False,
        "stopped_for_audit": True,
        "file_sha256": _sha(raw),
    }


# END V13 POST-AUDIT NOTIFICATION IMPLEMENTATION


def main() -> int:
    """The only canonical entry; every failure is terminal and safely identified."""
    if _DRAFT_INCOMPLETE:
        print("V13 draft incomplete; no execution authority.", file=sys.stderr)
        return 1
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
        _precredential_local_runtime(repository)
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
                    "schema_version": "lotto649-v13.0.0-safe-terminal-v1",
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
                    "V13.0.0 terminal descriptor cleanup; preserve evidence; no retry.",
                    file=sys.stderr,
                )
