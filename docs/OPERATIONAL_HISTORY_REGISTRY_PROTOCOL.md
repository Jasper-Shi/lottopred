# Operational History Registry Protocol

## Status

Protocol version: `lotto649-history-pin-registry-event-v1`.

The reader, one-event genesis migration, network source collector, offline
dual-source preparation seam, local bare-repository compare-and-swap adapter,
disconnected fixed-repository GitHub publisher, and isolated execution/artifact
handoff are implemented. A disconnected, capability-scoped exact remote
`P -> A` artifact publisher is independently reviewed and merged. It fixes
production repository/main identity, exact object-OID upload, GraphQL
`updateRefs` with `force=false`, mandatory ref reread, and a fresh anonymous
full-fetch production reload. PR #31 merged the fixed orchestration at
`2fe56a40532f7be2586a5cfc004699561556e849`; it composes collect,
`B -> E -> S -> P` publication/reload, exact-P execution, A freezing, and
`P -> A` publication/reload in the required order. No CLI imports it. PR #32
fixed source-prediction origin proof across the complete commit DAG at head
`69d59709dd5f8d9c6d8e761dc84d784af844144d`, merged as
pre-Stage-1 ancestor `60f972b217f7bd23d1b4807e96034db0cfd1fe2e`.
The shared exact-object/updateRefs boundary passed its authorized
disposable-remote canary on 2026-08-24, and production `main` now has
the required administrator, force-push, and deletion protection. No real
production `P -> A` execution/reload canary has run. Production `main` contains
Stage-1 activation merge ancestor
`3b72d6f3f5cbaf7122d9f4941215c33edac4a6ee`; its configuration has
`data.refresh_enabled=true`, `live.enabled=true`, and
`backtest.enabled=false`. This protocol still does not authorize execution or
claim remote publication safety.

Stage 1 binds only the public `orchestrate_github_live_cycle(*, token=...)`
boundary to a manual workflow. Its exact config digest is
`d53a9a9eed5ab434b021472135d6aed65c2c052339e0dfb88f8c00d46c0d8931`;
data/live are true and backtest is false. Repository permissions are read-only,
checkout does not persist credentials, and the dedicated publication secret is
scoped only to the protected canary step. Stage 1 is
`merged_armed_not_executed`. Final candidate
`5c5dc355ce1bfdae1f467eefa35062aff59d9614` passed independent Standards and
Spec review with 0 blocker, 0 major, and 0 minor findings, but the production
canary remains unrun. Manual dispatch requires `expected_sha`, a canonical
lowercase 40-hex production `main` target established by independent review.
No dispatch SHA is approved yet; neither the candidate nor the activation merge
ancestor is that authority. The plan stores
`approved_sha_source=post_merge_review` and dispatch evidence must record the
eventual value. The guard requires
`expected_sha == GITHUB_SHA == checkout HEAD`. With the exact Stage-1 config,
an invalid/mismatched SHA, context mismatch, checkout mismatch, or early time
writes all-false outputs and fails red. The credential is not installed, and
the hard `2026-08-27T15:15:00Z` plus dual-source gate remains pending. No
schedule exists. Stage 2 is a separate PR after successful canary evidence
review.

## Purpose

The corrected 4,442-draw base is immutable. Later official draws belong in an
append-only suffix. The registry is the Git-bound authority that identifies the
approved seal and the latest suffix without treating mutable worktree bytes or
caller-supplied hashes as trusted input.

Operational callers have one read seam:

```python
load_operational_history(cfg) -> PublishedHistory
```

It resolves the repository's literal `HEAD` once to a full commit OID, loads the
registry, seal, suffix, and evidence from Git blobs, validates the complete
history, and returns frozen publication provenance. Callers cannot override the
registry path, genesis identity, revision, seal, suffix, or hashes through
configuration.

## Fixed genesis

The registry path is:

```text
evidence/operational_history/DI-2026-08-20-registered-history/pin-registry.jsonl
```

Its source-pinned genesis is:

```text
commit: a6857d6b4e6e532062f484bcce4466f76ba4327b
parent: cf401a8873821b0f5647945752aee320f9452d57
event SHA-256: 22bcfe219c091dbcdb751ef7a2d9d5251f3040770de6e2e825ac5c64fc69c63d
Git blob: e95aeaaa28d5c1b7e5fb636d0fc4a3c26ff31017
bytes: 1170
file SHA-256: 42a9df8ef861a5fad6e1d7e7639d3d9317e519c0e83e96d7b1148527215afb72
```

That event migrates, without rewriting, the already reviewed state:

```text
seal commit: b3056cd1772f8e992e27a9eb87e5037eb15e2b79
seal blob: 23c05e7d2c1344f77085b228bfc919e88e3c4af3
seal SHA-256: 80397752105b567d6a8bdd3673b12ffa470a12efbd792719a4f6c89ef391f6fd
suffix commit: 0b476b6de1f6bed1382c29187fd5cdaa4f70c153
suffix blob: 3fa0319cc9d98fc17c49d4917e222d2da10aef07
suffix SHA-256: b91be6a4057648abd86dc0e6fc5d762fc4cd9b222519c147d635703cc550a803
suffix head: 3022b98fefbe3dbbc80423574319c169edcc845bf2218152c6abe18d0be27475
verified draws: 4,444 through 2026-08-22
```

Genesis and the reader that pins it are intentionally separate commits. Their
original OIDs must remain reachable. Merge this migration normally; do not
squash or rebase it. A normal merge may carry genesis on its second-parent
ancestry, so the validator requires ordinary ancestry rather than incorrectly
assuming it is on the final merge's first-parent chain.

## Canonical event format

The registry is nonempty canonical JSONL. Every line is UTF-8 canonical JSON
followed by exactly one LF. Canonical JSON uses sorted keys, compact separators,
`ensure_ascii=False`, and forbids NaN. Integers must be actual nonnegative
integers; booleans are not integers.

Every event has exactly these keys:

```text
event_kind
event_sha256
incident_id
previous_event_sha256
schema_version
seal
sequence
suffix
transaction
```

Nested exact keys are:

```text
seal: bytes, commit, git_blob, path, sha256
suffix: bytes, event_count, git_blob, head_event_sha256,
        history_through, path, sha256
transaction: base_commit, evidence_commit, suffix_commit
```

`event_sha256` is SHA-256 of the canonical event object with only
`event_sha256` removed, without a trailing LF. Sequence starts at zero. Genesis
uses `event_kind=genesis_migration` and sets `previous_event_sha256` to the
frozen seal SHA-256. All later events use `event_kind=append` and chain
`previous_event_sha256` to the preceding registry event.

The seal object is frozen across all events. Each append increments suffix event
count by one, advances the history date, and identifies a new suffix blob whose
bytes are the previous suffix bytes followed by exactly one canonical JSONL
event. Replacing or reserializing any prior registry or suffix byte is forbidden.

## Publication transaction

The implemented offline preparer creates one candidate transaction per
scheduled draw:

```text
B -> E -> S -> P
```

- `B` is the exact advertised remote `main` OID used as the compare-and-swap
  expectation. It may be a transparent reviewed code/merge descendant of the
  previous publication, but reserved history paths must be unchanged.
- `E` has sole parent `B` and adds exactly two raw HTML files: one WCLC and one
  Loto-Québec asset. Their paths are
  `evidence/live_sources/{authority}/{draw_date}-{raw_sha256}.html`; the filename
  hash must equal the committed bytes.
- `S` has sole parent `E` and modifies only the suffix path by appending one
  canonical event bound to `E`.
- `P` has sole parent `S` and modifies only the registry path by appending one
  canonical registry event.

`P` is not written inside its own event because a Git commit cannot contain its
own content-addressed OID. The validator derives `P` as the unique ancestor that
has sole parent `S` and installs the exact registry prefix.

Preparation must create unattached Git objects with private temporary indexes;
it must not change the caller's worktree, index, branch, or remote ref. The
candidate `P` must pass the production reader before publication. Publication is
one non-force fast-forward compare-and-swap from `B` to `P`, followed by a remote
fetch and successful reload. Evaluation, prediction, email, and artifact writes
remain forbidden before that post-publication reload.

The implemented preparation seam is
`prepare_history_publication(...) -> PreparedPublication`. It is offline and
accepts exactly two already-retrieved, immutable `RawSource` values: one WCLC
asset and one Loto-Québec asset. It freezes the input sequence once; requires
the exact `RawSource` class and exact built-in `str`/`bytes` identity fields;
limits each raw asset to 2 MiB; requires distinct bytes; normalizes valid aware
timestamps to whole-second UTC audit times; and accepts only the exact canonical
source URLs. WCLC has no query string.
Loto-Québec has exactly `date=YYYY-MM-DD` for the target draw. The two strict
parsers must reconstruct the same next scheduled draw before any Git object is
written.

All preparation Git commands scrub caller-controlled authority variables, use
a private index, and explicitly disable split-index, untracked-cache,
filesystem-monitor, and sparse-index behavior. A late candidate-validation
failure may leave only unreachable content-addressed objects for normal Git
garbage collection; it never advances a ref or changes the caller's worktree or
index. Those unreachable objects are not published history and must not be
treated as a successful preparation.

The implemented local CAS seam is
`publish_prepared_history(prepared, ref_store) -> PublicationReceipt`, with
`LocalBareHistoryRefStore` as its only adapter. It is deliberately restricted to
a self-contained bare repository whose literal `HEAD` is
`refs/heads/main`. Its Git directory and common directory must be the same
canonical path; only the `files` ref backend is accepted; and symbolic `main`,
external config includes, repository-provided `fsck.*` policy overrides,
unbounded ref-lock timeout overrides, control-file/ref/reflog/object-store
symlinks or special nodes, reftable, alternates, promisor/partial-clone markers,
and corrupt or missing reachable objects are rejected. Before CAS it reloads
`P` through the production reader and verifies the exact
`B -> E -> S -> P` identities. It then compares `main` with `B` and uses
`git update-ref --no-deref ... P B`. Once the CAS call starts, every normal
exception or ambiguous acknowledgement is followed by an authority reread.
Only observing exact `P`, followed by a fresh successful production reload,
returns success. Observing `B`, a third head, malformed authority, or an
unreadable ref returns a typed non-success; there is no retry, merge, or force.

This local adapter proves the state machine against one local bare authority.
It does not prove GitHub branch-protection, receive-pack, API, credential, or
remote acknowledgement semantics.

The disconnected GitHub seam is
`publish_prepared_history_to_github(prepared, token=...) -> PublicationReceipt`.
Its public entry point fixes `Jasper-Shi/lottopred` and `refs/heads/main`; callers
cannot inject a repository or substitute the post-publication loader. Before
any upload it freezes and rehashes the exact local blob, tree, and commit objects
for `E`, `S`, and `P`; verifies repository identity, SHA-1 object format, and
protected-main force/deletion policy; then requires every Git Database REST
response OID to equal the prepared OID. It attempts GraphQL `updateRefs` exactly
once with `beforeOid=B`, `afterOid=P`, and `force=false`. Any acknowledgement,
error, or timeout is followed by an authoritative ref reread. A successful
return additionally requires a new anonymous full bare fetch of public `main`
at exact `P` and a production-reader reload. It never uses an ordinary push,
force, merge, rebase, temporary ref, or the prepared repository as remote proof.

This code seam alone does not prove GitHub token permissions, branch-rule
compatibility, REST commit serialization, unattached-object visibility, or
remote read-after-write behavior. Before workflow integration, an authorized
disposable repository must prove exact returned OIDs for all `B -> E -> S -> P`
objects, one successful and one stale `updateRefs` CAS, protected-main behavior,
and a fresh public reload. Production `main` protection must also be configured
and independently verified.

The REST protection preflight requires repository Administration read, while
Git object installation requires Contents write. The built-in Actions token is
not assumed to satisfy that combination. The canary/release review must select
and prove the narrow credential and permissions without placing it in Git,
logs, subprocess arguments, receipts, or exception text.

## Execution handoff and artifact commit

The implemented `history_execution_handoff` seam begins only from a successful
`PublicationReceipt`. Its public context manager fixes the anonymous authority
to `https://github.com/Jasper-Shi/lottopred.git`; callers cannot provide a
repository, ref, destination, token, or loader. It fetches
`refs/heads/main` itself into a newly initialized temporary repository and
requires that fetched ref to equal exact `P`. Fetching an old P by object ID is
not sufficient.

Before exposing the workspace it requires a complete self-contained SHA-1
object store, no shallow/promisor/alternate state, a plain-file tree without
gitlinks, `.gitmodules`, or symlinks, detached literal `HEAD=P`, a clean index
and worktree, and a fresh `load_operational_history` result exactly equal to the
remote publication receipt. It issues one opaque context capability bound to
the canonical checkout root, its `.git` and object-store directory identities,
and exact `P`; copied workspaces, replaced directories, external Git controls,
and use after context exit fail closed. The caller's original B checkout is
never read or modified. Callers must load configuration through the workspace,
which reads the authenticated `P:config.yaml` into an independent object and roots all later
file I/O in the P checkout. The context must span the complete
evaluate/notify/predict/freeze/publish-A operation; returning only history and
resuming in the caller's checkout is forbidden. The temporary repository is
removed on normal exit and on exceptions.

The handoff seam itself does not replace the running Python import path or
launch the model process. The merged `live_orchestration` module does so through
private `src/lotto649/_live_worker.py` in the detached P workspace.
The parent verifies that worker before and after execution, launches isolated
Python with P/src first, and accepts a bounded canonical manifest only after
every loaded `lotto649` source module is bound to its exact P Git blob and
SHA-256. The worker has no standalone module or CLI entry point. Merely changing
`cfg["_root"]` remains insufficient code provenance.

After evaluation and prediction code has created files in that isolated
workspace, `freeze_execution_outputs(...)` accepts only a bounded, sorted,
unique list of canonical `predictions/*.json` and `evaluations/*.json` paths.
Every listed path must be a new non-executable regular UTF-8 JSON file with a
real scheduled date, filename-bound model identity, the exact prediction or
evaluation schema, and the correct P-derived history provenance. Prediction
targets must be the next scheduled draw after P; evaluation values are
recomputed from an immutable source prediction and the verified actual draw.
For each source path, the reader traverses the complete commit DAG reachable
from P, not a path-simplified or first-parent-only history. It requires P and
the registry transaction base B to contain the same `100644` blob, one unique
single-parent origin O on B's first-parent history, the exact same blob at every
reachable descendant of O, and absence at every reachable commit outside that
origin cone. Side-branch copies, merge-introduced origins, modifications,
deletions, re-additions, mode changes, replace refs, grafts, shallow history,
and missing objects fail closed.

For an ordinary source prediction, O's parent must load through the production
published-history reader and the prediction metadata and chronology must match
that history exactly. The only exception is the exact seven-file 2026-08-26
cohort sealed by
`evidence/data_integrity/DI-2026-08-20-registered-history/legacy-2026-08-26-prediction-cohort.json`.
Its SHA-256 is
`04f115049f81fa462810a18b756e7d893633b0195705bf27d8e4e5c91d52fc02`.
That manifest pins O/O^, the raw commit, the 4,434-row incident-affected legacy
history input, and every prediction path, mode, blob, byte count, SHA-256,
timestamp, model, version, and role. Any mismatch rejects the whole cohort.
Its evaluation `prediction_source.kind` is `sealed_legacy_incident_history` and
must state that corrected-history claims and promotion-evidence eligibility are
false; `actual_history` remains the separate corrected source of the revealed
draw. The new prediction cohort must exactly match `P:config.yaml`'s
`live.models` at `project.model_version`; no model may be
missing or added, and each `primary`/`shadow` role must agree with
`live.shadow_models`.
Duplicate keys, non-finite numbers, overwrites, ignored files, or any unlisted
worktree or index change fail closed. The function revalidates the workspace
capability, repository controls, complete object store, P history, and exact
output bytes before and after construction. It uses a private index rooted at P,
creates an unattached commit `A` with sole parent P, then verifies full object
integrity, the exact add-only path delta, each A blob against its frozen bytes,
and unchanged worktree bytes. It leaves literal HEAD, the normal index,
worktree bytes, and all refs unchanged. Its timestamp must be whole-second UTC,
conservatively post-date the history, not predate P, and remain pre-draw for new
predictions.

The handoff itself does not publish A. The disconnected
`publish_frozen_execution_artifacts_to_github(artifacts, token=...)` accepts
only the exact freeze-issued `FrozenExecutionArtifacts` while its opaque
capability and original P workspace remain active. It independently freezes A's
commit/tree/file identities, fixes `Jasper-Shi/lottopred` `main`, uploads and
checks every required Git Database object OID, and attempts GraphQL `updateRefs`
exactly once with `beforeOid=P`, `afterOid=A`, and `force=false`. Every
acknowledgement, error, or timeout is followed by an authoritative ref reread.
Success additionally requires public `main=A`, a new anonymous complete bare
fetch, exact A topology/tree/files, and `load_published_history(A)`. It does not
push, merge, rebase, force, retry, stage a directory, or touch a workflow or
runtime gate. Evaluation, prediction, email, or output files that cannot
complete that remote publication are not committed audit evidence.

The sole orchestration public boundary is
`orchestrate_github_live_cycle(*, token=...)`. It loads configuration from
literal B, obtains trusted whole-second UTC values internally, and fixes all
adapters, repository, and ref; there is no caller-injectable
configuration/clock/ports state-machine seam. It keeps the same opaque P
workspace active across worker execution, exact freeze, artifact publication,
reread, and fresh A reload. The isolated worker receives a scrubbed environment
plus only `SMTP_USERNAME` and `SMTP_PASSWORD`, so it uses fixed Gmail defaults;
manual/legacy SMTP host, port, sender, and recipient overrides do not cross this
boundary. An SMTP exception records `email_sent=false` and processing
continues. Once worker execution starts, no failure is retried automatically
because notification may already have caused an external side effect.

Only after a new A is remotely installed and freshly verified, the parent reads
the exact A blob for the configured primary `ensemble` snapshot and makes one
fixed-Gmail Chinese pre-draw email attempt with its target date and final six.
The worktree is not an authority for this message. `ALREADY_PUBLISHED`, a
shadow/arbitrary model, or the Toronto target date and later cannot send. A
missing secret, false SMTP result, or exception is recorded in the returned
cycle receipt, does not invalidate A, and is not automatically retried.

The publishers and orchestration remain disconnected from CLI entry points.
Stage 1 exposes only the composed public orchestrator through its digest-bound
manual workflow. Local tests cannot prove GitHub serialization,
token permission, branch protection, unattached object visibility, or
read-after-write behavior; those claims require the unrun production canary and
protected-main evidence listed in `OPERATIONS.md`.

## Reader guarantees

For a selected full revision OID, the reader:

- disables Git replacement objects and grafts and scrubs caller-controlled
  `GIT_*` authority variables;
- requires the fixed genesis commit and parent to exist and be reachable;
- reads only `100644` Git blobs with `ls-tree` and `cat-file`, never worktree
  seal/suffix/registry bytes;
- validates canonical schemas, self-hashes, chains, strict byte prefixes, blob
  OIDs, lengths, and SHA-256 values;
- verifies every `B -> E -> S -> P` single-parent closure and its exact changed
  path set;
- rejects reserved-path mutation followed by restoration, as well as an
  unregistered final seal, suffix, registry, or evidence state;
- passes the immutable seal and suffix bytes into the full verified-history
  validator, which reconstructs every suffix draw from both raw authorities;
- returns the observed revision, derived publication commit, registry blob/head,
  seal/suffix blobs, and evidence commits in provenance.

Missing historical objects, shallow history, wrong modes, symlinks, malformed or
noncanonical JSON, truncation, coordinated prefix rewrites, unexpected paths,
source disagreement, and chronology gaps all fail closed. The reader never
fetches missing objects from the network.

## Trust and capability boundary

Version 1 trusts the repository host, protected `main`, repository
administrators, reviewed workflow credential, local Git executable, and host OS.
It protects against accidental corruption, mutable worktree input, partial or
out-of-protocol commits, stale concurrent writers, and actors without repository
write authority. It is not an external transparency log or nonrepudiation
system.

A fixed genesis proves integrity along the selected revision's history. Without
an independently retained monotonic checkpoint or witness, it cannot prove that
the selected revision is the globally newest legal head, distinguish two legal
post-genesis forks, or defeat a trusted administrator who rewrites both code and
authority. If that stronger threat model becomes required, freeze a registry v2
with an external signed checkpoint/witness; do not silently broaden v1 claims.

## Release rule

Merging the reader, collectors, publishers, execution handoff, orchestration,
and prediction-origin fix did not reopen execution. The disposable remote
OID/CAS canary and protected-main setup were verified on 2026-08-24; the real
production canary has not run. Stage 1 is a SHA-bound, manual-only release in
state `merged_armed_not_executed`; backtest remains false and no schedule
exists. Candidate review is satisfied at
`5c5dc355ce1bfdae1f467eefa35062aff59d9614` with Standards/Spec findings
0/0/0. The remaining Stage-1 work is the narrow publication credential,
independent approval of the exact production `main` dispatch SHA, the hard
time/source gate, and one real end-to-end production
`B -> E -> S -> P -> A` canary/reload. Any failure after worker start has no
automatic retry. The first successful P or A advance makes the approved SHA
stale, so it cannot authorize a replay. A separate Stage-2 PR may add scheduling
only after the exact canary evidence passes review.
