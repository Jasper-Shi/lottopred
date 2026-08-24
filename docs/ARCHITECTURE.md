# Architecture

## Goal

Ask one narrow question: **does any model repeatedly assign higher probability/rank to future winning numbers than a fair-lottery baseline when it is forbidden from seeing the future?**

## Data layer

V1 merges three sources:

1. WCLC since-inception PDF — primary historical source.
2. lotto.net annual archive pages — bridge for years where the WCLC PDF lags.
3. WCLC current LOTTO 6/49 results page — authoritative live/current source.

Overlapping dates are compared exactly, including bonus. Any disagreement raises an error. The merged chronology must contain more than 4,000 draws and may not contain suspicious post-2000 gaps greater than 14 days.

## Data-integrity incident execution boundary

The registered-history reconciliation opened on 2026-08-20 places the
operational source-refresh, default historical-backtest, and live-cycle paths
behind three explicit kill switches:

| Boundary | Required configuration | Incident value |
|---|---|---|
| Network/source refresh and processed-data write | `data.refresh_enabled is True` | `false` |
| Unattended live refresh/evaluation/prediction cycle | `live.enabled is True` **and** `data.refresh_enabled is True` | `false` / `false` |
| Historical backtest and report generation | `backtest.enabled is True` | `false` |

These checks deny by default. A missing key, a non-boolean value, or a value
other than literal boolean `true` does not enable execution. `bootstrap`
checks before resolving or loading the processed dataset or contacting a
source; `backtest` checks before loading data, building a model, or writing a
report. The gate is repeated at the direct `run_backtest` boundary and both
public `refresh_with_sources` implementations, so bypassing the CLI cannot
construct models or reach a source. Live refresh, evaluation, generation, and
cycle entry points require both literal-true live and data-refresh approval
before source access, filesystem reads, evaluation writes, or prediction
generation. Literal `true` satisfies only this runtime gate; it is never
sufficient to reopen a sealed workflow.

The three affected GitHub Actions workflows have a read-only boundary directly
after checkout. That boundary reads the committed configuration with the
runner's standard Python runtime and hashes the complete `config.yaml` byte
stream with SHA-256; it does not interpret YAML. The incident seal recognizes
only disabled-config SHA-256
`ad3237bc57c85013e85dad16d1b6f04f43b50991d666a4b1528bf5b8614a76b6`,
and even that exact match emits `false` for every execution stage. Every other
digest also emits only `false`. Runtime setup, dependency installation,
bootstrap, backtest, live execution, artifact upload, and Git writes therefore
skip successfully for both the sealed config and any unreviewed byte change.
The guard writes all-false outputs before hashing; a missing or unreadable
`config.yaml` produces a warning and a successful sealed exit rather than a
traceback that could obscure the operational state.

The ordinary paths below describe the system when a later reviewed release has
reopened them. Re-enablement requires a committed and independently reviewed
corrected-history epoch, exact identity/integrity verification at its consumer
boundary, and passing offline tests and source-policy review. The release must
change the exact config bytes **and**, in the same reviewed commit, replace the
affected workflow's incident seal with an explicit execution plan bound to the
new config SHA-256. The CLI/runtime literal-boolean checks remain a second,
independent approval gate; a config-only toggle or a workflow-only digest
change cannot enable execution. Live must never be reopened without data
refresh in that same reviewed release. Existing predictions, evaluations,
reports, and registered evidence remain immutable.

This emergency seal is deliberately scoped to the three execution commands on
main: `bootstrap`, `backtest`, and `live`. It grants no authority for any other
research execution. Any broader operation must be added to a reviewed incident
plan rather than inferred from this operational seal.

## Verified corrected-history boundary

`src/lotto649/history_registry.py` resolves the source-pinned registry genesis
and current seal/suffix identities only from immutable Git objects.
`src/lotto649/verified_history.py` validates those bytes and reconstructs the
corrected epoch, while `src/lotto649/operational_history.py` is the single
operational read seam. It resolves `HEAD` once, hides paths and hashes from
callers, loads the immutable 4,442-draw base from the sealed artifact commit,
and accepts only the suffix named by the canonical append-only registry. Each
suffix row must be the next scheduled draw and must be independently
reconstructed from immutable WCLC and Loto-Québec raw assets committed after
the base. Receipt timestamps must be UTC, conservatively post-date the draw,
and not post-date the evidence commit.

The currently registered suffix adds 2026-08-19 and 2026-08-22, yielding a
4,444-draw verified view through 2026-08-22. Registry genesis commit
`a6857d6b4e6e532062f484bcce4466f76ba4327b` binds that state without rewriting
it. Direct backtest execution loads through this seam only after its incident
gate and no longer accepts a caller-provided draw list. The offline
`history_publication` module can now validate already-retrieved WCLC and
Loto-Québec assets and create an unattached `B -> E -> S -> P` candidate. The
`official_source_collection` module is the network collector seam: it retrieves
the two exact, bounded raw HTML assets without writing repository or operational
state. The
`history_publication_cas` module can validate and advance one self-contained
local bare `refs/heads/main` authority with exact compare-and-swap and mandatory
reread. The disconnected `history_publication_github` module is the remote
exact-CAS publisher seam: it fixes the GitHub repository and `main` identities,
uploads exact Git objects, attempts one
GraphQL `updateRefs` compare-and-swap, rereads the remote ref, and requires a
fresh anonymous full fetch through the production reader before success. None
of these modules is connected to a CLI or workflow. The local CAS is not a
remote publisher, and the GitHub publisher is not an execution release.

The disconnected `history_execution_handoff` module consumes only a successful
publication receipt. It makes a second anonymous fetch of authority `main` into
a new temporary repository, requires exact `P`, a complete self-contained SHA-1
object store, a plain-file tree, detached `HEAD=P`, and a literal-HEAD production
reload equal to the receipt. The caller's original `B` checkout is never read or
modified. Its configuration loader reads authenticated `P:config.yaml` and
points later file I/O at the temporary `P` checkout. It can also freeze an exact
sorted list of newly created
`predictions/*.json` and `evaluations/*.json` files into an unattached commit
`A` whose sole parent is `P`; it does not stage directories, change an index or
ref, publish `A`, or connect to a workflow.

The disconnected `history_artifact_publication_github` candidate is the narrow
remote continuation of that handoff. It accepts only a capability-scoped
`FrozenExecutionArtifacts` value while the same temporary P context remains
open; fixes the authority to `Jasper-Shi/lottopred` `main`; uploads and verifies
the exact object identities needed by A; attempts one GraphQL `updateRefs`
`P -> A` with `force=false`; rereads `main` for every acknowledgement outcome;
and returns success only after a fresh anonymous full fetch of exact A passes
`load_published_history(A)`. It has no CLI, live, or workflow connection and is
still awaiting review and true-remote proof.

The handoff does not change the current interpreter's import path. Future
orchestration must execute reviewed P code inside this context, or independently
prove the loaded code bytes equal P, before it may call the live helpers. A
P-rooted configuration alone is not code provenance.

Bootstrap and every public live entry point therefore remain quarantined after
their gates until protected-main policy and a disposable-repository OID/CAS
canary prove the GitHub adapter, the collector/preparer/publisher/handoff are
orchestrated with P-code provenance, and the artifact publisher passes its
review plus a real `P -> A` publication/reload canary. Live refresh raises after
both gates because that end-to-end remote path is not wired. The workflow/config
release remains a separate reviewed change. See
`OPERATIONAL_HISTORY_REGISTRY_PROTOCOL.md` for the exact schema, transaction,
and trust boundary.

Offline preparation uses a single frozen source snapshot, exact
`RawSource`/string/byte identity types, a 2 MiB per-source limit, canonical
URLs, private indexes, and Git config overrides that prevent split-index or
cache files from leaking into the caller's repository state. A failed late
validation may leave only unreachable Git objects for ordinary garbage
collection; it never changes an authoritative ref.

Backtest detail and summary rows carry the canonical operational-history
provenance as serialized JSON. New live prediction metadata carries the verified training
history identity, while new evaluation artifacts separately carry the verified
actual-result history identity; an old prediction is never relabeled as having
been trained on corrected history.

Workflows that may consume verified history use full-history checkout because
the loader must resolve the registry genesis, publication topology, sealed
artifact, and evidence commits. A shallow checkout is not a supported
operational adapter.

Seal publication assumes its output directory is permission-isolated and that
all legitimate concurrent writers follow the repository's exclusive-create
protocol. Open file-descriptor leases, content hashes, no-replace Git settings,
and failure archives protect against ordinary races and ambiguous filesystem
errors; they are not an OS security boundary against a malicious same-UID
process that can rename arbitrary directory entries between syscalls.

## Path A — Live forward prediction

```text
collect WCLC + Loto-Québec assets
     |
     v
prepare B -> E -> S -> P; exact-CAS P; fresh authority reload
     |
     v
open isolated detached P execution workspace
     |
     v
evaluate due committed snapshots ----> SMTP alert if threshold met
     |
     v
run the complete P-configured live model cohort and create next-draw files
     |
     v
freeze exact files into A with sole parent P
     |
     v
exact-CAS P -> A; reread A; fresh authority reload
```

Only the remotely published and reloaded A commit creates the external audit
trail proving the prediction existed before the result was known. The same
temporary P context must remain open through A publication; returning only a
history object and resuming execution in the caller's old checkout is forbidden.
Evaluation also revalidates that its source prediction was added by the prior
artifact base from a pre-draw, provenance-bound parent; a structurally valid
post-draw prediction cannot be wrapped in a successful evaluation.

During the data-integrity incident this entire path is dormant; the kill-switch
boundary takes precedence over the normal unattended schedule.

## Path B — Historical walk-forward simulation

For target draw `t`:

```text
verified history[0:t] -> features -> model -> probability vector -> result[t] -> score
```

Then advance to `t+1`. Random train/test shuffling is forbidden.

## Feature engine

V1 number-level features include:

- long-run frequency
- 10/25/50/100/250-draw frequencies
- exponentially weighted recent frequency
- gap since last appearance
- appeared in previous draw
- appeared in last 1/2/3/5 draws
- number identity scaled to 0..1

Structural metrics such as sum, odd/even, high/low, range, adjacency and repeated numbers are implemented as analysis helpers but are not forced into the final combination in V1. They become predictive features only after out-of-sample evidence.

## Models

- `random`: fixed `6/49` probability for every number.
- `long_frequency`: Bayesian-shrunk long-run frequency.
- `recent_frequency`: recent-100 frequency shrunk toward fair probability.
- `ema_gap`: weak EMA signal plus deliberately weak gap term.
- `logistic`: regularized logistic regression trained only on historical prior draws.
- `ensemble`: frozen weighted combination of the non-random V1 models.

All models emit 49 inclusion probabilities normalized to expected count six.

## Combination selection

V1 ranks all 49 numbers and selects the highest independent log-score six-number combination within the Top-12 candidate pool. It intentionally does not force a chosen sum band, 3/3 odd-even split, or similar folklore.

## Snapshot format

`predictions/YYYY-MM-DD__MODEL__VERSION.json`

Contains:

- target draw date
- generation timestamp and timezone
- model name/version
- probabilities 1..49
- Top-6, Top-12, Top-18
- final six-number combination
- number of historical draws visible to the model
- latest visible draw date

Existing snapshots are never overwritten.

## Evaluation

Each result stores:

- final six hits
- Top-6 hits
- Top-12 hits
- Top-18 hits
- matched final numbers
- Brier score
- binary log loss
- mean rank of actual six numbers

A single historical 6/6 or 5/6 is not sufficient evidence of predictive skill. Aggregate out-of-sample metrics and statistical significance are required.

## Scheduling

Codex Cloud is for development/agent work. GitHub Actions is the unattended scheduler. The live workflow runs Thursday and Sunday after the prior Wednesday/Saturday draw.
