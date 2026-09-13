# Model Research Protocol

## Non-negotiable: no future leakage

A target draw may use only information available strictly before that draw. This includes features, normalization, training labels, hyperparameter selection and ensemble weights.

## Research partitions

| Period | Purpose |
|---|---|
| 1982–2014 | historical development; legacy runs carry the registered-history incident caveat |
| 2015–2019 | exposed legacy validation/model selection |
| 2020–2025 | consumed historical diagnostic; the old 621-row strict-blind qualification is withdrawn |
| 2026+ | model-version-specific prospective forward evidence |

Once a blind-test result influences a model change, that period must no longer be described as untouched validation data for the changed model.

The official-calendar reconciliation contains 627 draws in 2020–2025, not the
621 rows used by the archived V2–V4 run. All exact V2–V4 metrics are therefore
legacy registered-data diagnostics; see `docs/V2_V4_RESULTS.md`. New historical
execution must consume the Git-registry-authenticated corrected-history boundary
through the single reviewed operational adapter. Recomputing an old candidate on corrected history is a
data-correction sensitivity diagnostic under a new experiment/version, never a
restored blind test. Pre-incident 2026 snapshots may still prove that their
predictions existed before reveal, but models trained on the malformed history
do not thereby acquire corrected-history promotion evidence.

## Fair-lottery baselines

The separately requested
[`V1_ensemble_verified_history_diagnostic_20260913`](experiments/V1_ensemble_verified_history_diagnostic.md)
registers one corrected-history replay of the unchanged V1 ensemble, with the
original random baseline and a fixed label-permuted probability control. Its
reviewed registration/implementation merge authorizes only its named manual
one-shot diagnostic command. It does not enable the generic backtest/live
switches or authorize V12. At registration it has no historical predictions or
scores; a later evidence commit must report the complete result or an explicit
early stop. Its target-day ad hoc V1 selection for 2026-09-12 is separate and
cannot become registered prospective evidence.

The single replay is now complete: 627 targets, no Final-6 6/6, and V1 mean
Top-6/12/18 hits 0.720893 / 1.395534 / 2.078150, each below its fair
expectation. Brier and binary log loss also trail the fair constant. The
experiment is closed as a negative diagnostic and grants no promotion or
permission to tune/replay its revealed outcomes. Complete frozen results and
read-only audit are in the
[dated evidence report](../reports/v1_ensemble_verified_history_diagnostic_20260913/summary.zh-CN.md).

- Single-number inclusion probability: `6/49 ~= 0.122449`
- Expected hits from a fixed six-number selection: `36/49 ~= 0.734694`
- Expected Top-12 hits: `72/49 ~= 1.469388`
- Expected Top-18 hits: `108/49 ~= 2.204082`

The random model remains in every benchmark.

## Why numerical distance is meaningless

Predicting 27 when 28 is drawn is not a near-hit. Number labels are categorical. The system predicts a probability for each of 49 labels and uses proper probability/ranking metrics.

## Allowed automatic update after every draw

- add verified draw result
- recompute rolling features
- refit a previously frozen training algorithm
- evaluate previously committed prediction
- generate next prediction

## Requires a new model version

- changing feature definitions
- changing window lengths because a recent result looked bad
- changing ensemble weights because of blind/live results
- adding a newly discovered date/sum/periodicity rule
- changing combination constraints to improve past hits

## Versioning

- `v1.x`: implementation/bug fixes preserving intended statistical behavior.
- `v2.0+`: changed research/model behavior.

Whenever practical, new models run as shadow models beside old versions rather than replacing them immediately.

## Candidate V2 hypotheses

- sum level, trend and mean reversion
- odd/even and high/low distributions
- repeated numbers between adjacent draws
- adjacent/consecutive numbers
- sorted-number gaps
- pair/co-occurrence statistics
- weekday/month/calendar effects
- Fourier/periodicity features
- Markov/transition features

Each hypothesis must prove value out-of-sample and survive multiple-testing correction before receiving material ensemble weight.

## V12 registered research checkpoint

The original
[`V12_post_rng_parity_composition_transition`](experiments/V12_post_rng_parity_composition_transition.md)
registration froze one signed lag-one association between consecutive post-RNG
odd-number counts and one fixed pseudo-parity control. Its governed input remains
production `main` authority `4a617f2c1575a165b42878600753a01ddf2ced03`,
whose `PublishedHistory` has 4,444 draws through 2026-08-22. The only historical
score scope remains the 627 consumed targets in 2020--2025, split 314/313; all
2026 outcomes are excluded.

V12.0.0 is now **`superseded_unexecuted`** because its fixed forward-canary
window expired. This is not `Archive`, `Reject`, or `consumed`, and it conveys no
scientific result. The outcome-blind
[`V12.0.1 operational rebinding`](experiments/V12_0_1_operational_rebinding.md)
retains the identical H12 statistical fingerprint while assigning new execution
identities. I2 merged by PR #40 at
`40f6e4098d4ed59f9421196efb8573c66c48928a`. Historical authorization PR #44
normally merged at `baa08ecb77555e17f383ef2998bea3c433e16f74`; its sole
canonical invocation failed before any claim or forecast. V12.0.1 is
**startup-failed, frozen against retry, and not scored**. Its exact pre-claim
failure stage is unknown; the subsequently observed lease 404 does not prove
that no commit upload was attempted. The
[startup incident](../evidence/research_execution_incidents/v12-0-1-20260913/startup-incident.json)
records the confirmed API representation defect and the remaining uncertainty.
There is no scientific Reject result. Its live lane missed its fixed windows
and has a separate
[`superseded_unexecuted` closure](../evidence/research_closures/v12-post-rng-parity-composition-transition-v2-live-superseded-unexecuted.json).

R2 defined separate historical and live authorization lanes. Complete reviewed
I2 and the ordinary historical-auth merge `M_A_H2` at protected remote
`main`/HEAD were required before the one-shot historical lease
`refs/heads/v12-consumption-v12.0.1`. Its fixed-history authority was independent
of future draws and live-canary success. Those former prerequisites do not
restore the failed attempt. The independent live lane's fixed dates expired
without its D0/W2/S2/C2/M_C2/K_L2 and `M_A_L2` prerequisites.
The V12.0.1 command must not be retried or repaired in place. PR #45 preserves
the incident and live closure at ordinary merge
`3015078e251bdcbb92719e1b291b1807525fef16`.

The current registered operation is
[`V12.0.2 historical operational rebinding`](experiments/V12_0_2_historical_operational_rebinding.md).

**R3 checkpoint: REGISTERED / NOT IMPLEMENTED / NOT AUTHORIZED / NOT SCORED.**

It preserves the exact H12 statistical fingerprint, pure-core SHA-256, formula,
seed, controls, 627 targets, 314/313 split, inference and ten gates. R3 changes only
the historical execution identities, strict GitHub representation verification
and durable sanitized startup receipts; it introduces no live lane. New I3
implementation and independent reviews, exact-head CI, an ordinary
protected-main implementation merge, new auth-JSON-only source and ordinary
authorization merge, and a fresh V12.0.2 one-shot lease are required before
execution. Authorization must be fully verified before any startup artifact.
Fixed history and runtime closure remain independent of future draws, D0 and
live-canary success. Neither V1's observed results nor the startup failure may
change H12's scientific behavior. No V12 forecast, score, report, canary success
or live authorization exists. V1 and V3 roles are unchanged.

## Planned anti-overfitting checks

- permutation tests
- bootstrap confidence intervals
- false-discovery-rate correction
- shuffled-label controls
- stability across eras
- calibration curves
- probability sharpness vs accuracy

## Interpretation

The system is explicitly allowed to conclude that no exploitable predictive signal exists. Convergence toward equal `6/49` probabilities is a valid scientific result.
