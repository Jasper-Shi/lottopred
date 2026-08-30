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

The registered-history reconciliation opened on 2026-08-20 placed the
operational source-refresh, default historical-backtest, and live-cycle paths
behind three explicit kill switches. Pre-Stage-1 ancestor
`60f972b217f7bd23d1b4807e96034db0cfd1fe2e` retained this incident baseline:

| Boundary | Required configuration | Pre-Stage-1 value |
|---|---|---|
| Network/source refresh and processed-data write | `data.refresh_enabled is True` | `false` |
| Unattended live refresh/evaluation/prediction cycle | `live.enabled is True` **and** `data.refresh_enabled is True` | `false` / `false` |
| Historical backtest and report generation | `backtest.enabled is True` | `false` |

Production `main` now contains Stage-1 activation merge ancestor
`3b72d6f3f5cbaf7122d9f4941215c33edac4a6ee`. Its deployed configuration has
`data.refresh_enabled=true`, `live.enabled=true`, and
`backtest.enabled=false`. The fixed manual canary window expired without
execution, so those residual true values grant no dispatch authority. D0 must
reseal all three workflow outputs to false before any replacement live wiring;
the old route must not be run late or reused.

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
stream with SHA-256; it does not interpret YAML. The retained incident-disabled
mode recognizes disabled-config SHA-256
`ad3237bc57c85013e85dad16d1b6f04f43b50991d666a4b1528bf5b8614a76b6`,
and even that exact match emits `false` for every execution stage. An
unrecognized digest also emits only `false`. Integration and backtest likewise
recognize the Stage-1 digest only to remain all-false no-ops; `live.yml` retains
the expired Stage-1 path solely as historical deployed state, not as dispatch
authority. The guard writes all-false
outputs before hashing; a missing or unreadable `config.yaml` produces a
warning and a successful sealed exit rather than a traceback that could obscure
the operational state.

The following records the expired Stage-1 design for audit only. The merged
release changed only the live production-canary boundary. Its plan must not be
dispatched, re-dated, or reused. The exact `config.yaml` SHA-256 was
`d53a9a9eed5ab434b021472135d6aed65c2c052339e0dfb88f8c00d46c0d8931`.
The old route accepted only a manual `workflow_dispatch` after a read-only
full-history checkout and fixed repository/ref/commit/time checks, and called
`orchestrate_github_live_cycle(*, token=...)`. Its publication secret was scoped
only to that protected step. Integration and backtest remained all-false
workflow no-ops, the legacy CLI writer interlock remained closed, and the route
had no ordinary Git push or unattended schedule.

The expired dispatch contract required an `expected_sha` established by
independent review, supplied as a canonical lowercase 40-hex value, with
`expected_sha == GITHUB_SHA == checkout HEAD`. Neither reviewed candidate
`5c5dc355ce1bfdae1f467eefa35062aff59d9614` nor activation merge ancestor
`3b72d6f3f5cbaf7122d9f4941215c33edac4a6ee` was an approved dispatch SHA. No
value was approved before expiry. The plan stored only
`approved_sha_source=post_merge_review`; invalid identity or timing wrote
all-false outputs first and failed the workflow red.

The original Stage 1 is
`merged_armed_expired_unexecuted_pending_D0_reseal`. Its final candidate
`5c5dc355ce1bfdae1f467eefa35062aff59d9614` passed independent Standards and
Spec review with 0 blocker, 0 major, and 0 minor findings. No manual dispatch
has run, no dispatch SHA is approved, the repository-scoped publication
credential is not installed, and its fixed 2026-08-27 window expired without a
dispatch. The old plan must not be run late or reused, and D0 must reseal its
remaining true runtime bytes before new live wiring. Its registered success
shape was exact
`B -> E -> S -> P -> A`, a fresh reload of 4,445 draws through 2026-08-26,
seven descriptive-only legacy evaluations, and seven immutable 2026-08-29
predictions. The existing seven 2026-08-26 snapshots remain byte-identical. A
post-worker failure has no automatic retry. The first successful P or A
authority advance would have moved `main`, so the old independently approved
`expected_sha` would have failed a second dispatch and blocked replay. V12.0.1
keeps its historical one-shot `A_H2` authorization independent of D0, W2,
future outcomes, and the replacement live-canary lane. The separate future
`A_L2` route is manual-only, has no automatic retry, and authorizes no
unattended schedule.

The expired emergency seal was deliberately scoped to the three execution
commands on main: `bootstrap`, `backtest`, and `live`. It now grants no
execution authority. Any replacement operation must be added through its own
reviewed incident plan rather than inferred from the old seal.

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
of these component modules is directly connected to a CLI or workflow. The
local CAS is not a remote publisher, and the GitHub publisher is not an
execution release.

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

The merged `history_artifact_publication_github` module is the narrow
remote continuation of that handoff. It accepts only a capability-scoped
`FrozenExecutionArtifacts` value while the same temporary P context remains
open; fixes the authority to `Jasper-Shi/lottopred` `main`; uploads and verifies
the exact object identities needed by A; attempts one GraphQL `updateRefs`
`P -> A` with `force=false`; rereads `main` for every acknowledgement outcome;
and returns success only after a fresh anonymous full fetch of exact A passes
`load_published_history(A)`. It has no CLI or standalone workflow connection.

The merged `live_orchestration` module composes those seams into one fixed
state machine: load configuration from literal B, load B
history, collect both sources, prepare and remotely publish `B -> E -> S -> P`,
freshly reload P, open the isolated detached-P workspace, execute the private
P worker, freeze its exact outputs in A, publish exact `P -> A`, and require the
final reread plus fresh A reload before returning success. Its public boundary
accepts only the GitHub token. Configuration, UTC clocks, adapters, repository,
and ref are fixed internally rather than supplied by a caller.

The parent launches `src/lotto649/_live_worker.py` with isolated Python flags
from the detached P workspace, verifies that worker before and after execution,
and binds every imported `lotto649` source module to its exact P blob and
SHA-256. The private worker has no standalone module or CLI entry point. Its
subprocess environment is scrubbed and admits only `SMTP_USERNAME` and
`SMTP_PASSWORD`; notification therefore uses fixed Gmail defaults rather than
optional host, port, sender, or recipient overrides. It remains absent from
every CLI import path. The expired Stage-1 release connected only this public
function to the digest-bound manual workflow; that old wiring has no dispatch
authority.

Bootstrap and every legacy public live entry point remain quarantined by the
writer interlock. The disposable remote OID/CAS canary and production `main`
protection were verified on 2026-08-24. PR #31 merged orchestration as
`2fe56a40532f7be2586a5cfc004699561556e849`; PR #32 merged the complete-DAG
prediction-origin proof as
`60f972b217f7bd23d1b4807e96034db0cfd1fe2e`, now a pre-Stage-1 ancestor.
Production `main` contains activation merge ancestor
`3b72d6f3f5cbaf7122d9f4941215c33edac4a6ee`. Stage 1 expired unexecuted and has
no dispatch authority; D0 must reseal its residual runtime bytes before any new
live wiring. See
`OPERATIONAL_HISTORY_REGISTRY_PROTOCOL.md` for the exact schema, transaction,
and trust boundary.

Offline preparation uses a single frozen source snapshot, exact
`RawSource`/string/byte identity types, a 2 MiB per-source limit, canonical
URLs, private indexes, and Git config overrides that prevent split-index or
cache files from leaking into the caller's repository state. A failed late
validation may leave only unreachable Git objects for ordinary garbage
collection; it never changes an authoritative ref.

Backtest detail and summary rows carry the canonical operational-history
provenance as serialized JSON. New live prediction metadata carries the verified
training-history identity. Every new evaluation carries two distinct fields:
`actual_history` identifies the corrected history that supplied the revealed
draw, while `prediction_source` identifies the immutable forecast bytes, their
unique Git origin, and the history visible when that forecast was created. An
old prediction is never relabeled as having been trained on corrected history.

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
Evaluation resolves the source prediction's unique single-parent origin across
the complete `P` ancestry, proves that the exact `100644` blob is present at
every reachable descendant and absent everywhere outside that origin cone, and
requires the origin to lie on the publication base's first-parent history. A
structurally valid post-draw, rewritten, re-added, side-branch, or
merge-introduced prediction cannot be wrapped in a successful evaluation.

The seven immutable 2026-08-26 snapshots are a closed exception because their
origin predates the corrected operational registry. Their exact cohort,
origin, raw Git objects, and 4,434-row legacy history input are pinned by
`evidence/data_integrity/DI-2026-08-20-registered-history/legacy-2026-08-26-prediction-cohort.json`.
Evaluations may report their descriptive hits, but `prediction_source` marks
them as incident-affected legacy evidence that is ineligible for corrected-
history promotion.

An SMTP exception records `email_sent=false` and does not interrupt evaluation,
prediction, freezing, or A publication. Any other failure after the private P
worker starts is fail closed and receives no automatic retry: notification may
already have produced an external side effect even when the worker cannot
return a complete manifest.

The old Stage-1 path is permanently non-authoritative after expiry. It must not
be dispatched after its window, even if a SHA or credential later becomes
available. D0 must first restore all-false outputs; any replacement production
path requires the separate future `A_L2` manual-only chain and has no automatic
retry or unattended schedule.

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

Codex Cloud is for development and review. The old Stage-1 manual canary expired
without execution and cannot be dispatched. V12.0.1's future live lane is
manual-only through `A_L2`, with no automatic retry or schedule. Any unattended
Thursday/Sunday schedule requires a separate later release after the new canary
evidence passes independent review.
