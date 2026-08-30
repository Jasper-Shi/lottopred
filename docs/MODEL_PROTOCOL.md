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
identities. V12.0.1 is **registered only: not implemented, not authorized, not
scored, and not activated**.

V12.0.1 has separate historical and live authorization lanes. After complete
independently reviewed I2, only the ordinary historical-auth merge `M_A_H2` at
protected remote `main`/HEAD may authorize the new one-shot historical lease
`refs/heads/v12-consumption-v12.0.1` and historical run. That lane uses the fixed
governed-history authority and does not depend on a future draw or live-canary
success. The independent live lane remains manual-only and fail closed through
D0/W2/S2/C2/M_C2/K_L2 and `M_A_L2`; it permits neither a schedule nor automatic
retry. No V12 forecast, score, report, canary success, historical authorization,
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
