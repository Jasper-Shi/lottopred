# Operational History Registry Protocol

## Status

Protocol version: `lotto649-history-pin-registry-event-v1`.

The reader, one-event genesis migration, network source collector, offline
dual-source preparation seam, local bare-repository compare-and-swap adapter,
disconnected fixed-repository GitHub publisher, and isolated execution/artifact
handoff are implemented. They are not workflow-integrated and have not yet
passed the required disposable-repository object-OID/CAS canary. Exact remote
publication of the later artifact commit is not implemented. Therefore
`data.refresh_enabled`, `backtest.enabled`, and `live.enabled` remain `false`;
this protocol does not authorize execution or claim remote publication safety.

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
never read or modified. Callers must load configuration through the workspace, which reads
the authenticated `P:config.yaml` into an independent object and roots all later
file I/O in the P checkout. The context must span the complete
evaluate/notify/predict/freeze/publish-A operation; returning only history and
resuming in the caller's checkout is forbidden. The temporary repository is
removed on normal exit and on exceptions.

This seam does not itself replace the running Python import path or launch the
model process. The later orchestration must execute the reviewed code from P
(or independently prove the loaded code bytes equal P) while keeping this
context open. Merely changing `cfg["_root"]` is not code provenance and does not
authorize execution.

After evaluation and prediction code has created files in that isolated
workspace, `freeze_execution_outputs(...)` accepts only a bounded, sorted,
unique list of canonical `predictions/*.json` and `evaluations/*.json` paths.
Every listed path must be a new non-executable regular UTF-8 JSON file with a
real scheduled date, filename-bound model identity, the exact prediction or
evaluation schema, and the correct P-derived history provenance. Prediction
targets must be the next scheduled draw after P; evaluation values are
recomputed from a prediction added by the prior artifact base B and the
verified actual draw. That source prediction must itself be bound to B's sole
parent history, have a generation time between that parent and B, and remain
strictly pre-draw. The new prediction cohort must exactly match
`P:config.yaml`'s `live.models` at `project.model_version`; no model may be
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

This seam does not publish A. A later reviewed publisher must independently
freeze and upload A's exact objects, compare-and-swap remote main from P to A,
reread exact A, and perform a fresh public production reload. It must not use
the current workflow's broad directory staging or ordinary push. Evaluation,
prediction, email, or output files that cannot complete that remote publication
are not committed audit evidence. Because the temporary object store is removed
when the workspace context exits, that future publisher must complete inside
the same context.

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

Merging the reader, official-source collector, offline/local publication
components, disconnected GitHub publisher, and execution/artifact handoff does
not reopen execution. The next implementation phase is the authorized
disposable-remote canary, protected-main verification, orchestration, and exact
remote `P -> A` artifact publication/reload. Only a later, independently
reviewed release may change the exact disabled config bytes and the SHA-bound
workflow execution plan. Until then all three runtime switches and all workflow
stages remain false.
