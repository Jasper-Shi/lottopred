# V12.0.1 Operational Rebinding Basis

Date: 2026-08-30

Status: formal outcome-blind registration basis; no implementation,
authorization, forecast, score, live execution, source refresh, or registered
target outcome access was performed.

## Question

Can the unchanged V12 statistical candidate receive a new auditable execution
route after the fixed V12.0.0 production-canary window expired?

## Primary repository evidence

1. Repository policy makes chronology and immutable pre-draw snapshots more
   important than headline hits. A target may use only information available
   strictly before it, and an existing prediction may not be regenerated or
   overwritten. See [`AGENTS.md`](../../AGENTS.md), especially “Mission,”
   “Leakage and research guardrails,” and “Live and backtest workflows.”
2. The V12.0.0 registration binds authorization to one exact Stage-1 plan, one
   exact success payload, and an exact `M_I -> K` artifact allowlist containing
   the 2026-08-29 prediction cohort. It does not authorize substitution of a
   later canary. See
   [`V12_post_rng_parity_composition_transition.md`](../experiments/V12_post_rng_parity_composition_transition.md)
   under `R < I < A`, and the matching
   [`research-v12-post-rng-parity-composition-transition.yaml`](../../config/research-v12-post-rng-parity-composition-transition.yaml).
3. The production artifact handoff rejects a prediction when either its
   generation date or its artifact-creation date in `America/Toronto` is on or
   after the target date. The production orchestrator obtains those instants
   from its internal trusted clock. See
   [`history_execution_handoff.py`](../../src/lotto649/history_execution_handoff.py)
   `_validate_prediction_against_history` and
   [`live_orchestration.py`](../../src/lotto649/live_orchestration.py)
   `orchestrate_github_live_cycle`.
4. The operations guide fixes the old canary to the 2026-08-26 history append
   and 2026-08-29 next prediction, forbids automatic retry after worker start,
   and requires forward resealing after a partial acknowledged failure. See
   [`OPERATIONS.md`](../OPERATIONS.md) under “Stage-1 manual production
   canary.”
5. The model protocol distinguishes statistical behavior changes from
   implementation/bug-fix versions. An operational patch may retain the same
   statistical behavior, while any change to features, windows, weights,
   constraints, or result-driven selection requires a new scientific version.
   See [`MODEL_PROTOCOL.md`](../MODEL_PROTOCOL.md) under “Requires a new model
   version” and “Versioning.”

These sources establish a deterministic calendar/identity incompatibility. No
draw value, model output, hit count, p-value, interval, or score is needed to
reach it.

## Decision

V12.0.0 is no longer authorizable or executable under its registered A route.
Its fixed 2026-08-26-to-2026-08-29 live plan has expired, and the target-day
artifact rule forbids a late substitute. Its operational route is therefore
closed as `superseded_unexecuted`. This is not `Archive`, `Reject`, or
`consumed`: no scientific disposition is being made, and the offline closure
makes no remote lease-absence assertion.

The minimum safe replacement is V12.0.1, classified
`operational_rebinding_only`. It receives new registration, historical and live
authorization paths, historical and live lease refs, command identity,
claim/report namespace, canary plan, success payload, and R2/I2/W2/C2 Git
identities. It must never use a future canary as evidence for the V12.0.0 route.

## Statistical fingerprint

R2 treats the scientific candidate as a deep module. Its interface is one
canonical fingerprint; operational dates, Git topology, credentials, and
publication adapters remain outside that interface. V12.0.1 must reproduce
this interface exactly.

| Bound item | Frozen value |
|---|---|
| Hypothesis | `H12`, unchanged |
| Seed | `649` |
| Historical diagnostic targets | `627`, fixed halves `314 + 313` |
| Primary | mean Top-12 main-number hits minus `72/49` |
| Gate count | `10`, unchanged conjunction |
| Pure core path | `src/lotto649/models/v12_parity_transition.py` |
| Expected pure-core SHA-256 | `fae93e0a6f76c6604eabe24f6b93676e22e87d7e567365b382484433fba2eb77` |
| Canonical statistical fingerprint SHA-256 | `af2e16a55ff0e817cf71208471e19e4f481bed63990f7e41268997c4c4b35c76` |

The fingerprint also binds the canonical SHA-256 of the V12.0.0 registration's
`model`, `mathematical_contract`, `controls`, `multiplicity`, `gates`,
`historical_scope`, `control_null_contract`, `historical_governance`,
`notifications`, and `target_date_identities` objects. R2 tests recompute those
hashes from the immutable V1 registration bytes without opening a history
artifact.

The pure-core hash is an expected I2 identity, not a claim that the file exists
at R2. Statistical assumptions, H12, 627 targets, metrics, gates, seed, and core
bytes may be inherited exactly. Every mutable execution identity must be new.
Any outcome-informed change to the scientific interface requires a different
scientific registration, not V12.0.1.

## Why historical and live authorization are separate

The fixed governed historical diagnostic does not need future prospective
evidence. Coupling it to C2 would make a future outcome or an operational live
success a needless condition for a distinct historical computation. R2
therefore defines two narrow lanes.

Historical lane:

```text
R2 < I2 < K_H2 < A_H_s2 < M_A_H2 < L_H2 < run_H2
```

`A_H2` requires the formal R2 authority, complete independently reviewed I2,
protected remote main at K_H2, the fixed governed-history authority, the
historical runtime dependency closure frozen at I2, normal auth-only merge
M_A_H2, and a fresh exact V12.0.1 one-shot lease. It excludes D0, W2, S2, C2,
M_C2, K_L2, A_L2, all future draw outcomes, and live-canary success.

Live lane:

```text
R2 < D0
R2 < I2
{D0, I2} < W2 < S2 < C2 < M_C2 < K_L2 < A_L_s2 < M_A_L2
```

`A_L2` requires the separate D0/W2/S2/C2/M_C2/K_L2 chain and an auth-only
source merged normally to protected remote main. Neither source branch alone
is authority. The historical closure freezes at I2; the live closure freezes
at W2. Each closure is compared only across its own registered checkpoints.

## Stable R2 Git authority

R2 cannot embed the hash of the commit containing its own bytes without a
self-reference. The authority is instead resolved as the first ordinary
ancestor commit that adds the exact V12.0.1 registration path. After that
binding, the authority registration blob must equal the registered bytes.

The R2 tree—not the current checkout—proves that all six I2 paths, both new
authorization paths, and the live success artifact were absent, and that its
repository `config.yaml` had the registered SHA-256. Consequently later I2
files or D0/W2 config changes do not break or reinterpret the R2 test. History
rewrites, ambiguous adding commits, or blob drift fail closed.

Six repository-wide status documents remain outside the seven-file ownership
of this change: `AGENTS.md`, `docs/ARCHITECTURE.md`,
`docs/CODEX_HANDOFF.md`, `docs/MODEL_PROTOCOL.md`, `docs/OPERATIONS.md`, and
`docs/RESEARCH_ROADMAP.md`. The root owner completed their V12.0.1 status sync.
Their final SHA-256 values are registered respectively as
`332bb70be33d3d02c1b3d534d0c494024dd845b1ce0f4f0cf05e3a43f7e6bfe7`,
`ae92bf302bc76814b09c8e91b5ff9e7e8e2bb0909feda31eaaa451c54233c691`,
`1e0ed362b2c555fe1e5c9f58b203809dde6cfe5928fc9a1b0b3cc85e73d861ca`,
`5c6f48af7291b37cb742451a0ed69a2638a9aa0d4b86dbcd6e5f4bb74d9e9b0f`,
`b9ab3b8b2cc98fab82e62c27e6a7e72f5bdec417a5c4f43c7795aeb718da7661`,
and `f6578ad3a05b92a1d1a1e2b47cd91292a4a61836a26e479866dddd0c214e531a`.
They must not drift before the first R2 authority commit; the authority tree
and registered-file table bind those exact bytes.

## Fixed prospective dates and dispatch identity

The live recovery is fixed to a 2026-09-09 canary draw and a 2026-09-12 next
prediction target. The seed freeze deadline is exclusive:

```text
freeze_time_utc < 2026-09-09T04:00:00Z
```

That UTC instant is local midnight at the start of 2026-09-09 in
`America/Toronto`. Equality is invalid, so a valid freeze is necessarily on a
Toronto date strictly before the target date. A seed at or after the deadline,
or a canary dispatch outside its fixed window, marks only the V12.0.1 live lane
`superseded_unexecuted`. The date cannot slide, and this does not revoke or
reclassify the separately authorized historical lane.

R2 freezes the live identity as repository `Jasper-Shi/lottopred`, branch
`main`, workflow `.github/workflows/live.yml`, event `workflow_dispatch`,
manual-only invocation, no schedule, and no automatic retry. W2 may supply only
digest bindings: the reviewed protected-main commit SHA, config Git blob OID
and SHA-256, workflow Git blob OID and SHA-256, and live runtime-closure
SHA-256. W2 cannot revise any semantic identity or registered date.

## Outcome-blind operating rule

- Registration and implementation review may use only source text, synthetic
  fixtures, fixed literals, and closed-form oracles.
- The canonical V12 attempt, operational history reader, live worker, and
  source collectors remain uninvoked before their separately merged authority.
- The operational recovery team may later publish missed official draws only
  after R2 and the statistical bytes are frozen. Those values cannot alter the
  fingerprint or any scientific rule.
- Current implementation review may correct conformance defects against the
  preregistered contract, but the findings themselves are not model-selection
  or tuning inputs.
- Known 2020–2025 or 2026 outcomes may not be opened or summarized to justify a
  feature, coefficient, window, comparison, threshold, gate, or date.
- A post-freeze change to the hypothesis, partition, feature state, solver,
  seed, historical scope, comparators, metrics, gates, ranking, or inference
  closes V12.0.1 and requires a new scientific registration.

## Minimum staged recovery

1. Complete this formal R2 registration, verify the completed root-owned
   six-document sync has not drifted, reseal, and create the first normal Git
   authority commit before I2.
2. Implement and independently review complete I2 using only synthetic fixtures
   and closed-form oracles. Freeze its historical runtime closure.
3. If desired, authorize the fixed historical diagnostic independently through
   K_H2/A_H_s2/M_A_H2 and acquire its fresh one-shot lease.
4. Separately release D0 with all legacy canary outputs false.
5. Build W2 from complete reviewed I2. Add only its registered digest bindings
   and freeze the live runtime closure.
6. Recover authoritative history by the separately reviewed data-only plan,
   then freeze S2 strictly before the exclusive Toronto deadline.
7. Execute the one-shot manual C2 only in its window and only after dual-source
   agreement. Do not retry automatically.
8. Integrate self-reference-free success evidence through M_C2, form K_L2, and
   authorize live activation only through A_L_s2/M_A_L2.

At every stage, missing authority, a changed statistical fingerprint, a stale
digest, or a missed live deadline fails closed. No result already known during
implementation review may be treated as new tuning information.
