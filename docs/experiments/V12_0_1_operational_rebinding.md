# V12.0.1 Outcome-Blind Operational Rebinding Registration (R2)

Registration date: 2026-08-30

## Frozen status and identity

| Field | R2 value |
|---|---|
| Experiment | `V12_0_1_post_rng_parity_composition_transition_operational_rebinding` |
| Scientific family | `V12_post_rng_parity_composition_transition` |
| Model version | `v12.0.1` |
| Classification | `operational_rebinding_only` |
| Statistical behavior changed | `false` |
| Statistical fingerprint | `af2e16a55ff0e817cf71208471e19e4f481bed63990f7e41268997c4c4b35c76` |
| Seed | `649` |
| Status | **REGISTERED — NOT IMPLEMENTED — NOT AUTHORIZED — NOT SCORED** |

R2 creates no prediction, score, model output, claim, lease, notification,
authorization, production configuration, workflow wiring, or source request.
It does not read a registered target outcome. The expected scientific result
remains rejection; a historical run, if later authorized, remains consumed
diagnostic evidence only.

## V12.0.0 closure

The V12.0.0 route is `superseded_unexecuted` because its exact forward-canary
window expired. It is not `Archive`, `Reject`, or `consumed`, and this offline
registration makes no assertion about a remote lease ref. The immutable closure
is
[`v12-post-rng-parity-composition-transition-v1-superseded-unexecuted.json`](../../evidence/research_closures/v12-post-rng-parity-composition-transition-v1-superseded-unexecuted.json).

The old registration, configuration, plan, authorization path, lease namespace,
and report paths remain immutable. Creating the old authorization JSON, using a
new canary as its prerequisite, backdating a timestamp, weakening chronology,
or generating the 2026-08-29 cohort after its target date is prohibited.

## Exact statistical inheritance

V12.0.1 inherits the scientific contract from formal V12.0.0 registration R at
`0af20fc41fc5aaa0879dada0a258797a8bc14e20`. The complete V1 registration
bytes have SHA-256
`4406bd25ee82195bff7a97b258885cb3bb3c1a8fb829f383c5e3c1616e169170`.

The canonical R2 statistical fingerprint binds:

- unchanged `H12` signed lag-one post-RNG parity-composition association;
- seed `649`;
- the exact V1 `model`, `mathematical_contract`, `controls`, `multiplicity`,
  `gates`, `historical_scope`, `control_null_contract`,
  `historical_governance`, `notifications`, and `target_date_identities`
  objects by their canonical hashes;
- exactly 627 historical diagnostic targets split 314/313;
- unchanged mean Top-12 main-number hits minus `72/49` primary and all ten
  conjunctive gates;
- expected pure scientific core
  `src/lotto649/models/v12_parity_transition.py` at SHA-256
  `fae93e0a6f76c6604eabe24f6b93676e22e87d7e567365b382484433fba2eb77`.

The pseudo partition, RNG boundary, one-coefficient law, prior, binary64
literals, 256-step solver, comparators, Holm vector, bootstrap, ranking,
notification classification, report governance, and prospective 208-snapshot
rule therefore remain exactly as registered in V12.0.0. This document does not
restate them in a way that permits reinterpretation. A mismatch closes R2.

## New execution namespaces

Historical research execution and live activation have distinct authorization
and lease identities. Neither can borrow any V12.0.0 identity.

| Identity | V12.0.1 value |
|---|---|
| Registration | `evidence/research_registrations/v12-post-rng-parity-composition-transition-v2.json` |
| Research config | `config/research-v12-0-1-post-rng-parity-composition-transition.yaml` |
| Historical authorization | `evidence/research_authorizations/v12-post-rng-parity-composition-transition-v2-historical.json` |
| Live authorization | `evidence/research_authorizations/v12-post-rng-parity-composition-transition-v2-live.json` |
| Historical one-shot lease | `refs/heads/v12-consumption-v12.0.1` |
| Live canary one-shot lease | `refs/heads/v12-live-canary-v12.0.1` |
| Canary plan | `evidence/release_canaries/2026-09-10-v12.0.1-production-live-canary-plan.json` |
| Canary success | `evidence/release_canaries/stage1-r2-v12.0.1-production-live-canary-success.json` |
| Historical command | `python3.12 tools/run_v12_0_1_historical.py --consume-v12-0-1-once` |

All eight claim/ledger/report/staging/commit-manifest paths contain literal
`v12.0.1`. A later
implementation must reject every V12.0.0 lease, claim, report, authorization,
or success payload as authority for this attempt.

## Two authorization lanes

R2 precedes every implementation: `R2 < I2`. After a complete independently
reviewed I2, the historical and live lanes have different prerequisites.

The historical lane is:

```text
R2 < I2 < K_H2 < A_H_s2 < M_A_H2 < L_H2 < run_H2
```

- `K_H2` is protected remote `main` containing the registered R2 authority and
  complete reviewed I2, with the fixed governed-history authority and the
  historical runtime closure frozen at I2.
- `A_H_s2` is an auth-JSON-only child of `K_H2`; it is not authoritative while
  merely on a source branch.
- only its ordinary protected-main merge `M_A_H2`, at remote `main`/HEAD, can
  authorize acquisition of the new one-shot historical lease `L_H2` and then
  `run_H2`.
- `A_H2` explicitly does **not** depend on D0, W2, S2, C2, M_C2, K_L2, A_L2,
  any future draw outcome, or live-canary success. Historical authorization
  must not be delayed until, or inferred from, future prospective evidence.

The independent live lane is the following partial order:

```text
R2 < D0
R2 < I2
{D0, I2} < W2 < S2 < C2 < M_C2 < K_L2 < A_L_s2 < M_A_L2
```

- `D0` is a separate reviewed release that reseals the expired V12.0.0
  Stage-1 workflow to all-false outputs.
- `W2` is a bounded production-wiring release based on complete reviewed I2.
- `S2` is the immutable pre-draw seed cohort, `C2` the single fixed canary,
  and `M_C2` the ordinary merge of self-reference-free success evidence.
- `A_L_s2` is a live-auth-JSON-only child of `K_L2`; only normal merge
  `M_A_L2` at protected remote `main`/HEAD is live authority `A_L2`.

R2 contains neither lane's implementation or authorization. The production
path is absent at R2 but is not registered to remain permanently fail closed.

## R2 Git authority and stable later CI

R2 cannot put its own commit SHA inside its own bytes. Its Git authority is
therefore the first ordinary ancestor commit that **adds the exact registration
path**. Once that commit exists, the registration blob at that authority must
remain byte-identical.

Registration-time assertions are evaluated against that fixed authority tree,
not against a later checkout:

- every I2 implementation path, both authorization paths, and the canary
  success path must be absent in the R2 authority tree;
- the repository `config.yaml` in that tree must have SHA-256
  `d53a9a9eed5ab434b021472135d6aed65c2c052339e0dfb88f8c00d46c0d8931`.

I2 may later add its registered implementation files, and D0/W2 may later
change `config.yaml`, without making the R2 test reinterpret the current work
tree as registration-time evidence. A non-ordinary history rewrite, multiple
candidate adding commits, or registration-blob mismatch fails closed.

The six repository-wide status documents `AGENTS.md`,
`docs/ARCHITECTURE.md`, `docs/CODEX_HANDOFF.md`, `docs/MODEL_PROTOCOL.md`,
`docs/OPERATIONS.md`, and `docs/RESEARCH_ROADMAP.md` are owned outside this
seven-file change. The root owner completed their V12.0.1 synchronization. R2
binds their exact SHA-256 values respectively as
`332bb70be33d3d02c1b3d534d0c494024dd845b1ce0f4f0cf05e3a43f7e6bfe7`,
`ae92bf302bc76814b09c8e91b5ff9e7e8e2bb0909feda31eaaa451c54233c691`,
`1e0ed362b2c555fe1e5c9f58b203809dde6cfe5928fc9a1b0b3cc85e73d861ca`,
`5c6f48af7291b37cb742451a0ed69a2638a9aa0d4b86dbcd6e5f4bb74d9e9b0f`,
`b9ab3b8b2cc98fab82e62c27e6a7e72f5bdec417a5c4f43c7795aeb718da7661`,
and `f6578ad3a05b92a1d1a1e2b47cd91292a4a61836a26e479866dddd0c214e531a`.
They must remain unchanged through the first R2 authority commit; that tree and
the registered-file table jointly bind their final bytes.

## D0: separate old-canary reseal

D0 must make the legacy Stage-1 workflow produce only these runtime outputs:

```text
backtest=false
integration=false
live=false
```

D0 must occur before W2 and before any live recovery dispatch. It is not a
historical-lane prerequisite and need not precede I2. D0 needs its own config
bytes, digest-bound workflow plan, review, and deployment evidence. R2 contains
none of those bytes and cannot be used to dispatch D0.

## W2: bounded production wiring

W2 requires complete independently reviewed I2 and may arm only the fixed seed
and canary entrypoints. At R2 the live dispatch identity is already immutable:

| Field | Frozen value |
|---|---|
| Repository | `Jasper-Shi/lottopred` |
| Branch | `main` |
| Workflow | `.github/workflows/live.yml` |
| Event | `workflow_dispatch` |
| Invocation | manual only |
| Schedule | prohibited |
| Automatic retry | prohibited |

W2 may add only digest bindings: reviewed protected-main commit SHA, config Git
blob OID and SHA-256, workflow Git blob OID and SHA-256, and live runtime
dependency-closure SHA-256. It may not change any semantic dispatch field,
date, model byte, metric, gate, or authorization identity.

The historical runtime dependency closure freezes at I2 and must be identical
at I2, K_H2, A_H_s2, and M_A_H2. The independent live runtime dependency
closure freezes at W2 and must be identical at W2, K_L2, A_L_s2, and M_A_L2.

## Outcome-blind recovery and S2

Missed operational history may be recovered only under a separately reviewed,
data-only, append-only, dual-source exact-CAS plan. Recovery must never create a
late prediction, run V12, score V12, modify the statistical fingerprint, or
rewrite an acknowledged commit.

S2 may be created only after history recovery is authoritative and W2 is
complete. Its seven configured V1/V3 predictions target 2026-09-09. The trusted
freeze time must satisfy the exclusive comparison

```text
freeze_time_utc < 2026-09-09T04:00:00Z
```

because `2026-09-09T04:00:00Z` is exactly the start of 2026-09-09 in
`America/Toronto`. Equality is late. Thus every valid freeze is on a Toronto
calendar date strictly before the target day.

If `freeze_time_utc >= 2026-09-09T04:00:00Z`, the V12.0.1 **live lane only** is
`superseded_unexecuted`; the target does not move. This has no effect on an
otherwise valid historical lane and does not reclassify historical evidence.

## Fixed C2 canary

The exact plan is
[`2026-09-10-v12.0.1-production-live-canary-plan.json`](../../evidence/release_canaries/2026-09-10-v12.0.1-production-live-canary-plan.json).

- canary draw: `2026-09-09`;
- official-source gate: WCLC and Loto-Québec independently publish and agree;
- dispatch not before: `2026-09-10T15:15:00Z`;
- dispatch not after: `2026-09-11T15:15:00Z`;
- next prediction target: `2026-09-12`;
- exact order: `B -> E -> S -> P -> A`;
- expected freshly reloaded history: 4,449 draws through 2026-09-09;
- expected due cohort: seven immutable 2026-09-09 evaluations;
- expected next cohort: seven immutable 2026-09-12 predictions.

The dispatch uses one independently reviewed exact protected-main SHA and one
narrow publication credential. There is no schedule or automatic retry. The
plan expires without execution if S2 or the dispatch window is missed. It
cannot roll to a later draw; a new operational registration and version are
mandatory for another live attempt.

## Authorization checklists

Historical `A_H2` requires only:

1. the exact formal R2 Git authority, synchronized status-doc hashes, and
   registered-file seals;
2. complete independently reviewed I2 on protected remote main;
3. the unchanged fixed governed-history authority;
4. the historical runtime dependency closure frozen at I2 and equal at all
   four historical checkpoints;
5. auth-JSON-only source A_H_s2, normal protected-main merge M_A_H2, and a
   fresh exact V12.0.1 historical lease before the one-shot run.

Live `A_L2` separately requires:

1. D0 all-false reseal evidence and complete reviewed I2;
2. W2 digest bindings and complete live runtime dependency closure;
3. exact, timely S2 pre-draw cohort;
4. C2 workflow run, actor, reviewed main SHA, source receipts, protected-main
   receipt, publication receipt, acknowledgement receipt, and fresh reload;
5. self-reference-free C2 success source and normal merge M_C2;
6. K_L2 allowlist and closure equality at W2/K_L2/A_L_s2/M_A_L2;
7. live-auth-only source A_L_s2 and ordinary protected-main merge M_A_L2.

Caller-provided paths, receipts, clocks, configuration, refs, alternate canary
dates, or historical results cannot bypass either checklist.

## Tests and outcome blindness

R2 tests operate only on registration artifacts, immutable Git metadata,
canonical hashes, calendar dates, and registered absences. They do not open
operational history data, import a V12 model, instantiate the canonical attempt,
collect a source, run live code, create a forecast, or compute a score.

I2 tests remain subject to the original V12 synthetic-only requirements. Review
findings may correct implementation conformance to the already frozen
fingerprint. They may not change a scientific rule because of any known
historical or live result.

V12.0.0 remains the scientific-contract authority; R2 is the V12.0.1
operational-identity authority. Any ambiguity, seal mismatch, missing required
phase, late live seed or dispatch, or statistical drift fails closed. A missed
live deadline supersedes only this registered live lane; it neither authorizes
nor revokes the separately governed historical lane.
