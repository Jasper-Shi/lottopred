# Codex Handoff

Last verified on 2026-08-24 against operational `main` merge
`60f972b217f7bd23d1b4807e96034db0cfd1fe2e` and corrected-epoch artifact
commit `b04393944ef12f78417dfb6151343c72d4c2a2ac`.

## Current state

This repository is the execution and audit system. Codex develops and reviews the
code; outside an incident hold, GitHub Actions is the unattended runner that
commits live artifacts. Chat history is not required to continue because the
research decisions are recorded here and in `V2_V4_RESULTS.md`.

> **Data-integrity incident hold (2026-08-20):** the operational roles in the
> table below describe the pre-incident system, but execution is currently
> suspended. `data.refresh_enabled`, `backtest.enabled`, and `live.enabled` are
> all `false`; the live, integration, and backtest workflows are sealed to
> safe no-op behavior by disabled-config SHA-256
> `ad3237bc57c85013e85dad16d1b6f04f43b50991d666a4b1528bf5b8614a76b6`.
> No refresh, backtest, evaluation, or prediction is authorized. The legacy
> 4,434-row history through 2026-08-22 is not strict real-calendar evidence.
> A reviewed candidate now seals a corrected 4,442-draw base through
> 2026-08-15 and a two-event, dual-source suffix through 2026-08-22. The
> verified view contains 4,444 draws. Its external seal SHA-256 is
> `80397752105b567d6a8bdd3673b12ffa470a12efbd792719a4f6c89ef391f6fd`;
> the suffix file SHA-256 is
> `b91be6a4057648abd86dc0e6fc5d762fc4cd9b222519c147d635703cc550a803`;
> and its head event SHA-256 is
> `3022b98fefbe3dbbc80423574319c169edcc845bf2218152c6abe18d0be27475`.
> Append-only authority now begins at registry genesis commit
> `a6857d6b4e6e532062f484bcce4466f76ba4327b`, event
> `22bcfe219c091dbcdb751ef7a2d9d5251f3040770de6e2e825ac5c64fc69c63d`.
> The operational reader resolves that registry, seal, suffix, and evidence from
> immutable Git blobs; local worktree replacements are never history authority.
> The verified-history read interface is now the sole input to the direct
> backtest boundary. The kill switches remain false, so it is not authorized to
> execute. Bootstrap and every public live entry point fail explicitly after
> their gates. The dual-source collector, offline preparer, local bare-repository
> CAS, fixed-repository GitHub publisher, isolated execution/artifact handoff,
> and capability-scoped exact remote `P -> A` publisher remain disconnected
> from CLI. PR #31 merged the fixed code-level orchestration at
> `2fe56a40532f7be2586a5cfc004699561556e849`; it
> composes collect through remote P publication/reload, a fresh detached-P
> handoff, private exact-P worker execution, A freezing, and remote A
> publication/reread/fresh reload. It reads literal-B configuration and trusted
> clocks internally and exposes no caller-injectable configuration, clock, or
> adapter seam. The private worker has no standalone entry point, and the
> parent binds the worker plus its imported `lotto649` source modules to P.
> It remains unimported by every CLI. PR #32 fixed due-prediction provenance by
> proving each prediction's unique immutable origin across the complete commit
> DAG and merged as `60f972b217f7bd23d1b4807e96034db0cfd1fe2e`.
> The authorized
> disposable OID/CAS canary succeeded on 2026-08-24, and production `main` now
> enforces administrator, force-push, and deletion protection. A real production
> end-to-end `P -> A` canary has not run.
>
> The disconnected-until-reviewed Stage-1 branch is the manual production
> canary candidate. It sets data refresh and live to literal `true`, leaves
> backtest `false`, and binds only `live.yml` `workflow_dispatch` to exact config
> SHA-256
> `d53a9a9eed5ab434b021472135d6aed65c2c052339e0dfb88f8c00d46c0d8931`.
> Checkout and repository permissions are read-only. Only the protected canary
> step receives the dedicated publication credential, and it calls only
> `orchestrate_github_live_cycle(*, token=...)`; no CLI, ordinary Git push,
> automatic retry after worker start, or schedule is present. The branch is not
> dispatchable until independent review, credential installation, and the hard
> `2026-08-27T15:15:00Z` plus dual-official-source gate pass. Stage 2 is a
> separate PR after canary success and evidence review.
> The complete facts and blocker list are in `OPERATIONS.md`. No component or
> preparation authorizes execution. Re-enable only through the reviewed
> two-gate release described in
> [`OPERATIONS.md`](OPERATIONS.md#data-integrity-incident-kill-switch).
>
> The historical OOS opportunity ledger preserves its exact 18,259-event
> legacy prefix, then appends three governance events bound to this deployed
> seal. All 18,251 legacy opportunities are `registered_data_only` and
> ineligible; the governed eligible count is `0`, both high-waters are `null`,
> and `stop_global_search=false`. See
> [`HISTORICAL_OOS_EVIDENCE_PROTOCOL.md`](HISTORICAL_OOS_EVIDENCE_PROTOCOL.md).

| Component | Status | Meaning |
|---|---|---|
| V1 live suite | Paused baseline | Before the hold, six models created forward snapshots: `random`, `long_frequency`, `recent_frequency`, `ema_gap`, `logistic`, and `ensemble`. |
| V2 statistical | Rejected | Retained for reproducibility and historical research; absent from the live model list. |
| V3 boosting | Paused shadow | Before the hold, it created immutable snapshots and evaluations beside V1; it did not change V1 predictions or ensemble weights. |
| V4 ensemble | Rejected | Retained for reproducibility and historical research; absent from the live model list. |
| 2020–2025 legacy diagnostic | Consumed / strict-blind label withdrawn | The old run used 621 registered rows from a malformed and incomplete history rather than the corrected 627-draw calendar. Exact metrics are archival only; correction cannot make the known outcomes untouched. |
| 2026+ snapshots | Immutable source-relative artifacts | Their pre-draw chronology remains auditable. The 2026-08-19/22 outcomes are independently source-verified, but predictions trained on the malformed legacy history are not corrected-history promotion evidence. |

No version has established a reliable lottery-prediction edge. V3's historical
ranking lift is interesting but not statistically convincing.

## How the implemented system runs

The CLI entry points are:

```bash
lotto649 bootstrap
lotto649 backtest
lotto649 live
```

The authorized disposable canary and protected production `main` were verified
on 2026-08-24. The production publication path is the sole public
`orchestrate_github_live_cycle(*, token=...)` boundary, not a CLI command.
`backtest` walks forward chronologically over the Git-authenticated verified
history. The live cycle may refresh history, evaluate due snapshots, and create
predictions for the next Wednesday or Saturday only inside the isolated
workspace obtained after the remote publisher installs P and a fresh authority
reload succeeds. That context must remain open until the exact artifact commit
A (sole parent P) is remotely compare-and-swapped and freshly reloaded. The
legacy CLI `bootstrap` and `live` commands remain stopped by the writer
interlock even on the Stage-1 true-toggle branch. Backtest remains false and
unauthorized. The Stage-1 workflow can reach only the public orchestrator after
its exact digest, repository, ref, commit, event, review, credential, time, and
source gates all pass.

`config.yaml` deliberately separates two selections:

- `backtest.models`: the configured historical comparison suite, including V2,
  V3, and V4.
- `live.models`: the approved V1 suite plus V3.

`live.shadow_models: [v3_boosting]` adds `"role": "shadow"` to V3 snapshot
metadata; all other live snapshots receive `"role": "primary"`. The role is a
research label, not a separate execution path. In the pre-hold path V3 was
evaluated and could trigger the common hit-threshold email. It does not feed the
V1 ensemble.

All live models currently inherit `project.model_version: v1.0.0` for the
`model_version` field and filename. Therefore the model identity
`v3_boosting` plus `metadata.role == "shadow"` distinguishes the V3 shadow
snapshot; do not infer that it is a V1 algorithm from the shared version tag.
Change version semantics deliberately rather than renaming committed snapshots.

## Current committed forward checkpoint

The immutable pre-hold artifacts originated at `main` commit
`9f16e20c726c7b65eed1d387c4c725d51248f570`, remained present at ancestor
`e3c39dda3233cec5933430f22afd6aa8d78a998d`, and remain present at current
operational `main` `60f972b217f7bd23d1b4807e96034db0cfd1fe2e`:

- `data/processed/draws.csv` contains 4,434 registered rows through 2026-08-22;
- evaluations for all seven pre-hold live models are committed for both
  2026-08-19 and 2026-08-22, including
  `evaluations/2026-08-19__v3_boosting__v1.0.0.json` and
  `evaluations/2026-08-22__v3_boosting__v1.0.0.json`;
- seven immutable predictions for target 2026-08-26 are committed, including
  `predictions/2026-08-26__v3_boosting__v1.0.0.json`.

The newest V3 snapshot was generated on 2026-08-23 at 11:36 EDT from 4,434
registered draws through 2026-08-22 and is labeled `shadow`. Its target was not
yet knowable at this checkpoint, so no 2026-08-26 evaluation is committed. The
Stage-1 branch preregisters exactly seven descriptive-only evaluations of this
legacy cohort and seven new 2026-08-29 predictions, but none exists until the
reviewed canary publishes A.

The corrected epoch is separate and append-only. Its sealed base contains 4,442
draws through 2026-08-15. The suffix binds the 2026-08-19 and 2026-08-22 draws
to immutable WCLC and Loto-Québec source receipts at evidence commit
`60dbd42a502850091508491f9011f9a08acf894f`. The public verified-history loader
reconstructs a 4,444-draw view through 2026-08-22 only when the external seal,
suffix-file, and suffix-head identities all match. `history_registry.py` pins
the one-line genesis at commit `a6857d6b4e6e532062f484bcce4466f76ba4327b`
and proves the selected revision's immutable Git state; `operational_history.py`
combines that authority with the full validator behind one load interface.
Backtest consumes that interface. Public live evaluation/prediction entry points no longer accept an
arbitrary draw list and currently stop at the writer interlock; the private
post-writer helpers accept only the `VerifiedHistory` returned by the live
cycle. This consumer integration is not authorization to resume execution.

Prediction files are immutable. Within the post-writer stage,
`_generate_next_predictions` skips an already existing target/model/version
path, and the storage layer rejects overwrites by default. Never edit a snapshot
after its result is knowable.

## GitHub Actions and email

The configured workflows are:

- `test.yml`: unit tests on every push and pull request.
- `integration.yml`: source/model smoke checks, sealed to an all-false guard in
  Stage 1.
- `backtest.yml`: configured historical backtest, currently sealed to checkout
  and an all-false guard.
- `live.yml`: the Stage-1 branch exposes only a manual, digest-bound production
  canary. Repository permissions are read-only, checkout does not persist
  credentials, and only the protected canary step receives the dedicated
  publication secret.
- `email-test.yml`: explicit Gmail SMTP smoke test.
- `research-v2-fast.yml` and `research-v2-v4.yml`: historical branch-specific
  research workflows retained for auditability.

The last committed pre-hold live-cycle boundary is `main` commit
`9f16e20c726c7b65eed1d387c4c725d51248f570`: it appended the 2026-08-22 draw and
evaluations and froze the 2026-08-26 predictions. Its parent `0ef1883` appended
the 2026-08-19 evaluations and froze the 2026-08-22 predictions. Those artifacts
remain immutable during the hold.

The 2026-08-26 cohort is now sealed by
`evidence/data_integrity/DI-2026-08-20-registered-history/legacy-2026-08-26-prediction-cohort.json`.
It pins the exact seven prediction blobs and the 4,434-row registered history
visible at their origin. Once the corrected 2026-08-26 result is published,
their evaluations must include a recomputed `prediction_source` classified as
`sealed_legacy_incident_history`; `actual_history` separately identifies the
corrected result source. These evaluations are descriptive prospective hits,
not corrected-history training or promotion evidence.

The historical Gmail alert smoke test succeeded on 2026-08-15
([Actions run 31887288254](https://github.com/Jasper-Shi/lottopred/actions/runs/31887288254)).
Secret values are not readable from the repository; that run establishes only
that usable configuration existed at that time, not its current state.

Email requires only these repository secrets:

```text
SMTP_USERNAME=<Gmail address>
SMTP_PASSWORD=<Google App Password>
```

Defaults are `smtp.gmail.com:587`, with sender and recipient both equal to
`SMTP_USERNAME`. `SMTP_HOST`, `SMTP_PORT`, `EMAIL_FROM`, and `EMAIL_TO` are
optional overrides for manual and legacy paths. The exact-P orchestration
deliberately passes only `SMTP_USERNAME` and
`SMTP_PASSWORD` into its isolated worker, so that boundary always uses the
Gmail defaults. Missing credentials or an SMTP exception records
`email_sent=false` and does not block evaluation, prediction, freezing, or A
publication. The dedicated email smoke workflow treats a false send as a
failure so configuration can be tested explicitly. After the private P worker
starts, any orchestration failure receives no automatic retry because an email
may already have left the process.

Current alert thresholds in `config.yaml` are final-combination hits `>= 4` or
Top-12 hits `>= 5`.

## Data-source and fallback behavior

The legacy source adapters remain in `src/lotto649/data_sources.py` for audit and
future refactoring, but they are no longer a valid operational-history write
path. Legacy live refresh remains behind its writer interlock. The Stage-1
branch binds the merged orchestrator to exact reviewed workflow/config bytes,
but remains disconnected until its independent review and credential are
complete and the hard time/source gate passes. The disposable OID/CAS canary
and production-main protection were completed on 2026-08-24; the production
`P -> A` canary has not run.
The pre-incident reconciliation policy was:

1. Use the WCLC since-inception PDF for years before `bridge_start_year` (2024).
2. Use lotto.net annual HTML as the machine-readable bridge from 2024 onward.
3. Use the current WCLC results page as the authoritative current source and as
   an independent check wherever it overlaps the bridge.
4. Retain committed draws only when they agree with newly selected source data.
5. Require a strictly ordered, unique chronology of more than 4,000 draws, with
   no suspicious post-2000 gap greater than 14 days.

A lotto.net `requests` failure or timeout is recoverable: the cycle warns and
continues with committed data, the WCLC archive, and current WCLC results. This is
safe only if the resulting chronology still passes validation.

The following conditions remain fatal by design:

- WCLC archive/current request or parse failure;
- bridge parse/format failure that is not a request exception;
- bridge versus current-WCLC disagreement;
- committed data versus refreshed-source disagreement;
- undersized, duplicated, unordered, or discontinuous chronology.

Do not broaden the fallback to swallow those integrity failures.

## How Codex should continue

1. Read root `AGENTS.md`, `MODEL_PROTOCOL.md`, `V2_V4_RESULTS.md`,
   `RESEARCH_ROADMAP.md`, `ARCHITECTURE.md`, and `OPERATIONS.md` first.
2. Treat `9f16e20c726c7b65eed1d387c4c725d51248f570` and the artifact facts above as
   the last pre-hold `main` boundary.
3. On deployed `main`, preserve all three false switches until the reviewed
   Stage-1 release. On the Stage-1 branch, keep exactly data/live true and
   backtest false, bind `live.yml` to the exact config digest, and keep the
   branch disconnected until independent review. Call only the public
   orchestrator; preserve the CLI writer interlock.
4. Preserve and independently review the sealed corrected epoch and append-only
   suffix identities above. Do not replace them with worktree CSV bytes or
   caller-supplied metadata.
5. Never rewrite the existing processed history, prediction, evaluation, report,
   or registered evidence artifacts; corrections belong to a new sealed epoch.
6. Merge the sealed-epoch branch without squash/rebase so artifact commit
   `b04393944ef12f78417dfb6151343c72d4c2a2ac` and evidence commit
   `60dbd42a502850091508491f9011f9a08acf894f` remain reachable, then verify the
   deployed pins from a fresh full-history clone of `main`.
7. Keep the verified-history consumer as the only read path. Preserve registry
   genesis `a6857d6b4e6e532062f484bcce4466f76ba4327b` without squash/rebase. The
   bounded dual-source collector, offline `B -> E -> S -> P` preparer, local bare
   CAS, fixed-repository GitHub publisher, and execution/artifact handoff are
   disconnected review tools, not independent execution paths. Preserve the
   merged orchestration's fixed literal-B, exact-P worker, freeze-A, and P-to-A
   sequence; do not add a standalone worker or caller-injectable
   configuration/clock/adapter path. The prediction-origin fix is satisfied by
   PR #32. Complete the remaining Stage-1 independent review, credential, and
   hard time/source gates; run at most one production canary and verify exact
   reload evidence. Add scheduling only through the separate Stage-2 PR in
   `OPERATIONS.md` after Stage-1 succeeds.
8. Outcome-blind model design and preregistration may continue during the hold,
   but do not score models on the legacy history or treat the sealed epoch as an
   authorized runtime before that release. Use a new version whenever
   statistical behavior changes.
9. Run `pytest -q` and `ruff check .`; run a network smoke only after source
   access is explicitly authorized, and record positive and negative results.

Use `docs/RESEARCH_ROADMAP.md` as the decision process, not as evidence that any
listed feature family will work.
