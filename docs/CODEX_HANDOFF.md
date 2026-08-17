# Codex Handoff

Last verified against `main` commit `90177c8` on 2026-08-16.

## Current state

This repository is the execution and audit system. Codex develops and reviews the
code; GitHub Actions runs unattended jobs and commits live artifacts. Chat history
is not required to continue because the research decisions are recorded here and
in `V2_V4_RESULTS.md`.

| Component | Status | Meaning |
|---|---|---|
| V1 live suite | Production baseline | Six models continue to create forward snapshots: `random`, `long_frequency`, `recent_frequency`, `ema_gap`, `logistic`, and `ensemble`. |
| V2 statistical | Rejected | Retained for reproducibility and historical research; absent from the live model list. |
| V3 boosting | Shadow | Creates immutable live snapshots and evaluations beside V1; it does not change V1 predictions or ensemble weights. |
| V3 formal cohort | Registered, not activated | V3 is frozen as prospective identity `v3.0.0` with unchanged valid-input probabilities plus fail-closed chronology/cache hardening; every existing `v1.0.0` snapshot is excluded and a separate F/A/R release sequence is required before evidence starts. |
| V4 ensemble | Rejected | Retained for reproducibility and historical research; absent from the live model list. |
| V5 pair affinity | Rejected | `v5.0.0` was implemented exactly, did not establish historical signal, and was closed without shadow activation. It remains absent from live config. |
| V6 entropy regime | Rejected | `v6.0.0` failed its frozen historical gates and was closed without shadow activation. Its research config explicitly disables live execution. |
| V7 main/bonus role bias | Rejected | `v7.0.0` failed its frozen one-shot historical gates and was closed without shadow activation. Its permanent claim and reports preserve the attempt. |
| V8 fixed-recurrence harmonic | Rejected | `v8.0.0` failed six of eight frozen one-shot historical gates and was closed without shadow activation. Its permanent claim and reports preserve the attempt. |
| 2020–2025 blind period | Consumed | It cannot confirm a tuned V5+ model. |
| 2026+ snapshots | Prospective evidence | Evidence belongs to the exact frozen version that created each pre-draw snapshot. |

No version has established a reliable lottery-prediction edge. V3's historical
ranking lift is interesting but not statistically convincing.

## V3 prospective registration checkpoint

V3, numerically unchanged for valid strict-prefix inputs, is now registered as
[`V3_frozen_shadow_cohort`](experiments/V3_frozen_shadow_cohort.md), prospective
identity `v3_boosting v3.0.0`. This is a freeze record only: registry status is
`registered`, prospective status is `not_activated`, and all freeze/activation
boundary fields remain null. The current stacked research branch must not
enable live execution or create any `v3.0.0` prediction.

The registration freezes the current 280-draw training span, stride 14,
300-draw minimum, exact V3 feature vector and gradient-boosting parameters,
seed 649, 0.72 learned/0.28 fair blend, expected-six normalization, and the
dependency versions in `requirements-live.lock`. The workflow frozen at `F`
must install using that file as a constraints lock.

The freeze also makes chronology fail closed before prediction and keys the V3
cache by the complete history plus target date. This removes stale-cache alias
risk without changing valid uncached probabilities. V3 also rejects any output
whose integer keys are not exactly 1--49, whose values are non-finite or outside
`(0,1)`, or whose `math.fsum` differs from six by more than `1e-12`; failure
occurs before snapshot persistence.

The freeze preconfigures `v3_boosting -> v3.0.0` in `config.yaml`, guarded by
the registry experiment ID. The frozen live code applies that mapping only when
the named experiment/cohort is `prospective_shadow` / `active`; while it is
`registered` / `not_activated`, V3 continues to emit legacy `v1.0.0`. Thus `R`
changes only the registry's administrative cohort state. It must not change the
frozen config, code, dependency lock, or workflow.

The auditor must compare the immutable portion of the V3 registry row to `F`,
derive the actual release-transition commit `R`, and prove `A < R < S`; the
mutable allowlist is limited to status/result and the prospective activation
fields named in the registration.

Activation is deliberately four-stage Git evidence:

```text
F = this freeze
A = later anchor recording F plus the latest verified outcome boundary; no live enable
R = later registry-only release seal that opens the preconfigured v3.0.0 gate
S = first eligible snapshot's one-time first-add commit

F < A < R < S
```

`A` must retain its real SHA and must not be removed by a squash merge. Every
V3 snapshot stamped `v1.0.0` is excluded, including the current 2026-08-19
snapshot. The cohort has one exact 208-draw look, split 104 + 104, with no early
look or extension. Primary Top-12 lift must pass the exact fair-null test and
10,000-replicate seed-649 bootstrap; Brier and log loss must not degrade versus
fair in either half or the aggregate. V1 ensemble and fixed random remain
comparisons. Passing the conjunction permits only a separate promotion review;
V1 remains production meanwhile.

Routine monitoring uses `lotto649 prospective-audit --experiment
V3_frozen_shadow_cohort`, which exposes integrity/count state but no interim
performance. At the exact ready checkpoint, `prospective-claim` creates a
permanent claim that must be committed alone before `prospective-formal-look`.
The latter acquires the permanent registered attempt before aggregate
calculation and publishes the single JSON/Markdown result pair. A failed
post-attempt run before the durable pair-publication commit point is consumed
and must be archived, never retried; cleanup warnings after that point do not
invalidate the durable result.
The read-only `lotto649-prospective-cohort-monitor` workflow also runs after
each live workflow: it notices raw count 207 and performs the full audit from
208 onward. A ready/overdue/integrity condition is highly visible but cannot
roll back the already committed V1 live cycle. The frozen live interlock holds
only V3 before any 209th evaluation; the workflow never auto-claims or reads a
formal metric. Catch-up cycles quota V3 to the remaining raw slots below 208;
at or above that threshold a still-collecting state admits at most one candidate
evaluation before the next committed-tree audit, while earlier-pending admits
zero. V1 remains unrestricted.
After the one formal result, a separate registry-only terminal commit `T` binds
the reviewed decision to the immutable formal report. Closed audits cap their
data and target range at `T`, reject later same-version artifacts, and still
replay all three frozen models. Once a future version changes any frozen path,
re-audit this cohort from a checkout of `T`; current code is not allowed to
stand in for the frozen implementation.
If the prospective experiment mapping, registry, release verifier, runtime
lock, target boundary, or V3 prediction fails during a future live cycle, the
cycle suppresses only V3 `v3.0.0`, emits a structured warning, and keeps the six
V1 production-baseline snapshots running. It never lets a non-default version
bypass the experiment gate or disguises the gap with a V3 `v1.0.0` fallback;
shared storage and V1 failures still fail loudly.

The source-bounded V9 union-propensity note is retained at
[`V9_post_rng_seven_number_selection_basis.md`](research/V9_post_rng_seven_number_selection_basis.md),
but V9 is deferred, prospective-only if ever revived, and has never been
implemented or historically scored.

## V5 research checkpoint

The first V5+ attempt was registered as
[`V5_pair_affinity`](experiments/V5_pair_affinity.md), with its structured row in
[`docs/experiments/registry.yaml`](experiments/registry.yaml). The registration
freezes one strongly shrunk, previous-draw-anchored pair-affinity formula, a
single primary Top-12 metric, bounded secondary metrics, a deterministic
whole-draw date-permutation control, Holm family-wise correction, and the default
minimum 104-draw prospective gate.

The current status is **implemented / historical diagnostic complete / rejected
/ never activated**. The exact model implementation was committed as `f51a3b5`
before any candidate score was inspected. Its recorded dataset is the fixed
4,431-draw prefix through 2026-08-12 at source commit `39b99a9`; later live
appends cannot change that prefix or the registered negative control.

The result did not establish stable signal. Primary Top-12 lifts for development,
legacy validation, and consumed 2020-2025 were `+0.008056`, `-0.065542`, and
`+0.024976`; exact one-sided p-values were `0.334025`, `0.936385`, and
`0.272298`, and every 95% bootstrap interval included zero. Brier score and log
loss were worse than the fair constant baseline in every lane. The seed-649
negative control behaved as null. See the
[decision record](experiments/V5_pair_affinity_results.md) and generated
[historical report](../reports/v5_pair_affinity_v5.0.0_historical.md).

`v5_pair_affinity` is requestable only from the dedicated research config. It is
not in `config.yaml` or `live.models`; no V5 live snapshot exists. V1 production,
V3 shadow behavior, and every committed prediction snapshot remain unchanged.

## V6 research checkpoint

The second V5+ attempt, [`V6_fixed_boundary_js_regime`](experiments/V6_entropy_regime.md),
froze two adjacent 104-draw blocks, one global entropy gate, deterministic
date-derived jitter, the same whole-draw negative control, and an exact 208-draw
prospective decision before implementation or score inspection. The frozen
implementation commit is `591b6173`.

The one historical diagnostic is complete and **rejected / never activated**.
Development, legacy-validation, and consumed 2020–2025 Top-12 lifts were
`-0.001514`, `+0.117151`, and `+0.000822`. The sole historical gate lane had
exact/Holm `p=0.498761` and a 95% bootstrap interval of
`[-0.078083, +0.078116]`. V6 activated on 44 development targets but zero
legacy or consumed targets; the isolated legacy lift therefore came from the
registered outcome-independent fair jitter and cannot rescue the failed
all-lane/consumed gates. All negative controls behaved as null and the audit was
clear. See the [decision record](experiments/V6_entropy_regime_results.md).

`src/lotto649/research_protocol.py` now provides fail-closed Git/data evidence,
evaluation rebinding and recomputation, fixed prospective checkpoints, and a
single immutable formal-look record. V1 remains production and V3 remains
shadow. The next research attempt must be a new bounded pre-registration and
new model version; do not retune or reopen rejected `v5.0.0` or `v6.0.0`.

## V7 research checkpoint

The next bounded attempt is
[`V7_post_rng_main_bonus_role_bias`](experiments/V7_main_bonus_role_bias.md),
version `v7.0.0`. It tests whether, after the documented 2019-05-15 RNG
transition, a label's strictly prior six-main versus bonus-role counts contain a
stable role-assignment signal. The frozen seed-649 negative control keeps every
draw's date and seven-number set but reassigns only its historical bonus role.

The candidate, control, diagnostic runner, and deterministic offline tests were
frozen at implementation commit
`180cd045e7797b95db4226f7d79d66d6ee9a5965`. After push, full local checks, and
green PR CI, the sole diagnostic ran from a clean matching tree over exactly the
consumed 621 targets in 2020–2025. It completed without audit warning and made
the registered **Reject / not activated** decision.

Aggregate Top-12 lift was `+0.013704`, but its exact/Holm p-value was
`0.372657` and its 95% bootstrap interval was `[-0.065201, +0.094219]`.
The fixed 2020–2022 half had negative lift; aggregate and both-half Brier and
log-loss deltas were worse than fair; and the global role audit was null at
`p=0.570743`. The candidate control behaved as null in the aggregate and both
halves, and the audit was clear. The complete outcome is in the
[V7 decision record](experiments/V7_main_bonus_role_bias_results.md) and
[generated report](../reports/v7_main_bonus_role_bias_v7.0.0_historical.md).

The permanent one-shot claim remains at
`reports/v7_main_bonus_role_bias_v7.0.0_historical.claim` with SHA-256
`1443982f9b40ba5b460632211baa17b4aff7cb9cdcd48010c0a538f141344290`;
it must never be deleted to retry the experiment. V7 remains absent from
`config.yaml`, and its research config keeps `live.enabled: false` with empty
primary and shadow lists. V1 remains production, V3 remains shadow, and existing
prediction/evaluation snapshots are unchanged.

## V8 research checkpoint

The next attempt is
[`V8_fixed_recurrence_harmonic`](experiments/V8_fixed_recurrence_harmonic.md),
version `v8.0.0`. It is **implemented / historical diagnostic complete /
rejected / never activated**. Its
[source note](research/V8_fixed_spectral_basis.md) records the weak prior
honestly: `49/6` draws is the fair geometric waiting-time mean, not a
mechanism-backed period, and the fixed `12*pi/49` harmonic is expected to be a
negative falsification test under a fair IID process.

The registration fixes a strict post-2019-05-15 expanding main-number history,
the raw Fourier projection and target phase, a deterministic sum-to-six sigmoid
mapping, and exactly 621 consumed 2020–2025 targets. Development and legacy
scores are N/A rather than substitute discovery lanes. It also freezes two
controls: a strict-prefix complete-row permutation that preserves each six-main
plus bonus row, and a per-label phase rotation used only as a spectral-component
stress test. Both must behave as null in the aggregate and both fixed halves.

The dedicated config is
`config/research-v8-fixed-spectral-phase.yaml`; it explicitly sets
`live.enabled: false` with empty primary and shadow lists. The candidate and both
controls are implemented in `src/lotto649/models/v8_spectral_phase.py`; the
factory accepts them only with the exact frozen research config and never adds
them to the default-all or live paths. `lotto649 research-v8 --code-commit SHA`
completed its sole historical run against frozen implementation commit
`c48ab2277f005a48bc4dc57f5a532b476ab900fa`.

Across the 621 consumed 2020–2025 targets, aggregate Top-12 lift was
`-0.016891780866936212`, exact/Holm p was `0.6700938237435888`, and the 95%
bootstrap interval was
`[-0.08935554898287834, 0.05883285681422251]`. The first fixed half was
negative, aggregate and first-half proper scores missed the fair tolerance, and
candidate-minus-row-control point estimates were negative in the aggregate and
both halves. The row and phase controls met their registered null rules, the
audit was clear, and only `phase_control_null_aggregate_and_halves` and
`audit_clear` passed. The registered conjunction therefore made the exact
**Reject / `not_activated`** decision. See the
[V8 decision record](experiments/V8_fixed_recurrence_harmonic_results.md) and
[generated report](../reports/v8_spectral_phase_v8.0.0_historical.md).

The permanent one-shot claim is
`reports/v8_spectral_phase_v8.0.0_historical.claim` with SHA-256
`6598a2f38462fe6274b9dfa6b6b8c51e6af367b551fd861ef8a582000d60c76d`.
It must never be deleted or bypassed to rerun `v8.0.0`. The 2020–2025 result is
consumed, non-blind, and non-confirmatory; any tuning or other response to it
requires a new version, pre-registration, freeze, and genuinely new prospective
cohort. V8 remains absent from `config.yaml`; V1 production, V3 shadow,
workflows, and all existing prediction/evaluation snapshots remain unchanged.

## How the implemented system runs

The CLI entry points are:

```bash
lotto649 bootstrap
lotto649 backtest --models random ema_gap v2_statistical
lotto649 live
```

`bootstrap` refreshes and validates source data. `backtest` uses the committed
processed CSV and walks forward chronologically over the configured dates. `live`
loads existing committed history, refreshes sources, evaluates every due snapshot
that lacks an evaluation, and creates predictions for the next Wednesday or
Saturday after the latest known draw.

`config.yaml` deliberately separates two selections. Its default backtest suite
and the automatic `main` and integration workflows use the same consumed-safe
model subset that excludes V3 and V4 (which embeds V3):

- `backtest.models`: `random`, `ema_gap`, and rejected `v2_statistical`, used
  only as labeled consumed regression context.
- `live.models`: the approved V1 suite plus V3.

Do not invoke V3 or V4 through the generic historical backtest command under
the new cohort registration. Their authoritative historical numbers already
exist in `docs/V2_V4_RESULTS.md`; recomputing them cannot create new evidence.

`live.shadow_models: [v3_boosting]` adds `"role": "shadow"` to V3 snapshot
metadata; all other live snapshots receive `"role": "primary"`. The role is a
research label, not a separate execution path. V3 is still evaluated and can
trigger the common hit-threshold email. It does not feed the V1 ensemble.

While `V3_frozen_shadow_cohort` remains inactive, all live models still inherit
`project.model_version: v1.0.0`; the dormant `v3.0.0` mapping is ignored. Only a
verified future `prospective_shadow / active` registry release may cause new V3
files to use `v3.0.0`. Existing files retain their original version forever.

## Current V3 forward checkpoint

The newest committed V3 shadow snapshot is
`predictions/2026-08-19__v3_boosting__v1.0.0.json`:

- generated 2026-08-16 11:36:09 EDT (`America/Toronto`);
- target draw 2026-08-19;
- trained from 4,432 committed draws through 2026-08-15;
- Top-6 ranking: `17 08 10 27 33 20`;
- final combination: `08 10 17 20 27 33`;
- Top-12: `17 08 10 27 33 20 03 22 49 15 30 39`;
- metadata role: `shadow`.

That newest target is not yet evaluated. The preceding 2026-08-15 V3 snapshot
has now been evaluated against verified main numbers `01 09 17 34 36 43`
(bonus `24`): Top-6 `1`, Top-12 `2`, Top-18 `3`, final-combination hits `1`,
mean actual rank `19.166667`, Brier `0.105576857`, and log loss `0.361421605`.
The processed dataset now contains 4,432 draws through 2026-08-15. To find the
moving current checkpoint, inspect the newest V3 file under `predictions/` and
its same-named file under `evaluations/`.

Prediction files are immutable. `generate_next_predictions` skips an already
existing target/model/version path, and the storage layer rejects overwrites by
default. Never edit a snapshot after its result is knowable.

## GitHub Actions and email

The active workflows are:

- `test.yml`: unit tests on every push and pull request.
- `integration.yml`: source/model smoke checks on relevant pull-request paths or
  manual dispatch.
- `backtest.yml`: explicitly consumed, non-blind historical regression on
  relevant `main` changes or manual dispatch; its automatic model list excludes
  the new V3 prospective identity.
- `live.yml`: `15:15 UTC` every Thursday and Sunday, manual dispatch, and relevant
  `main` changes. It commits `data/processed`, `predictions`, `evaluations`, and
  `reports` with `contents: write` permission.
- `email-test.yml`: explicit Gmail SMTP smoke test.
- `research-v2-fast.yml` and `research-v2-v4.yml`: historical branch-specific
  research workflows retained for auditability.

The latest scheduled live cycle succeeded on 2026-08-16
([Actions run 31956059222](https://github.com/Jasper-Shi/lottopred/actions/runs/31956059222)).
It committed `90177c8`, advanced verified history to 2026-08-15, created seven
evaluations, and created seven next-draw snapshots for 2026-08-19.
The Gmail alert smoke test also succeeded on 2026-08-15
([Actions run 31887288254](https://github.com/Jasper-Shi/lottopred/actions/runs/31887288254)).
Secret values are not readable from the repository; the successful smoke run
shows that usable configuration existed at that time.

Email requires only these repository secrets:

```text
SMTP_USERNAME=<Gmail address>
SMTP_PASSWORD=<Google App Password>
```

Defaults are `smtp.gmail.com:587`, with sender and recipient both equal to
`SMTP_USERNAME`. `SMTP_HOST`, `SMTP_PORT`, `EMAIL_FROM`, and `EMAIL_TO` are
optional overrides. Missing credentials do not block prediction or evaluation;
`send_email` returns false. The dedicated email smoke workflow treats that as a
failure so configuration can be tested explicitly.

Current alert thresholds in `config.yaml` are final-combination hits `>= 4` or
Top-12 hits `>= 5`.

## Data-source and fallback behavior

The live CLI imports `refresh_with_sources` from `src/lotto649/data_sources.py`.
Its current reconciliation policy is:

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

The 2026-08-16 scheduled run exercised that fallback: the lotto.net 2024 bridge
timed out after 60 seconds, while committed/WCLC reconciliation still produced a
valid 4,432-draw chronology and the run succeeded. This remains an operational
warning, not a silent source substitution. GitHub also emitted its platform-level
Node.js 20 deprecation warning for `actions/checkout@v4` and
`actions/setup-python@v5`; it did not fail the job.

The following conditions remain fatal by design:

- WCLC archive/current request or parse failure;
- bridge parse/format failure that is not a request exception;
- bridge versus current-WCLC disagreement;
- committed data versus refreshed-source disagreement;
- undersized, duplicated, unordered, or discontinuous chronology.

Do not broaden the fallback to swallow those integrity failures.

## How Codex should continue

1. Read root `AGENTS.md`, `MODEL_PROTOCOL.md`, `V2_V4_RESULTS.md`, and
   `RESEARCH_ROADMAP.md` before proposing any V5+ candidate.
2. Pull current `main` and inspect the newest committed prediction/evaluation
   files before reporting live status.
3. Keep V1 unchanged as the baseline and V3 labeled shadow while new hypotheses
   are developed.
4. Keep rejected `v5.0.0` through `v8.0.0` immutable and retain every claim,
   report, decision record, and registry row as a negative result. Never rerun
   the same version or tune it against its consumed answers.
5. Pre-register one genuinely separate hypothesis before implementing or
   inspecting its scores; all currently observed outcomes are consumed for any
   model changed in response to them.
6. Start a future candidate as shadow only through a separate reviewed PR and
   count evidence only from that exact version's first eligible pre-draw snapshot.
7. For V3 `v3.0.0`, preserve `F < A < R < S`, install live dependencies with
   `requirements-live.lock` as constraints, and exclude every legacy `v1.0.0`
   V3 snapshot from the cohort.
8. Let normal live jobs continue during research. Never rewrite forward artifacts
   or mix research-only models into `live.models` without a reviewed promotion PR.
9. Run `pytest -q` and `ruff check .`; run integration smoke checks for live/data
   changes; record both positive and negative research results.

Use `docs/RESEARCH_ROADMAP.md` as the decision process, not as evidence that any
listed feature family will work.
