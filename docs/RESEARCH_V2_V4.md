# V2–V4 Research Protocol

> **Historical registration note:** “blind” below records the intended frozen
> protocol at the time of execution. A later source-integrity incident showed
> that the run used 621 registered rows from a malformed and incomplete history
> rather than the corrected 627-draw 2020–2025 calendar. Its strict-blind
> evidence qualification
> is withdrawn, while the interval remains fully consumed. See
> `V2_V4_RESULTS.md` for the erratum; do not retune or rerun these versions and
> relabel the result as blind.

This document records the frozen hypotheses introduced after V1. The consumed
2020–2025 interval must not be used to tune coefficients after results are
observed; later uses of “blind” describe the original registration, not the
current evidence status.

## V2 — conservative statistical multi-factor model

V2 expands the per-number feature set with:

- short/medium/long rolling frequencies (10/25/50/100/250 draws)
- three exponential-decay frequencies (half-lives 12/35/90)
- current omission gap and gap-to-historical-gap ratio
- previous one/two draw indicators
- weekday-conditional frequency with strong shrinkage
- month-conditional frequency with strong shrinkage
- previous-draw transition frequency with strong shrinkage
- previous draw sum, rolling sum levels and short sum slope
- cyclical month representation

V2 uses a deliberately weak fixed linear score. Coefficients were chosen before reading the V2 blind result and are not optimized against 2020–2025.

## V3 — regularized nonlinear model

V3 uses the same leakage-safe feature engine but learns nonlinear interactions using `HistGradientBoostingClassifier`. It trains on a rolling historical window using strided snapshots to limit compute and model complexity. Output probabilities are shrunk toward the fair 6/49 prior.

## V4 — compact diversified ensemble

V4 combines three signal families rather than adding another large feature search:

- V1 EMA/gap state signal
- V2 conservative statistical score
- V3 regularized nonlinear boosting

The compact design avoids duplicating expensive training and reduces the risk that one large model dominates the ensemble. Weights are frozen before reading the V2–V4 2020–2025 blind result.

## Evaluation

All versions are evaluated with strict walk-forward chronology. For each target draw, only earlier draws are visible. Metrics include:

- mean Top-6, Top-12 and Top-18 hits
- final-combination hits
- Brier score and binary log loss
- mean rank of actual winning numbers
- frequency of 3+ and 4+ final hits
- lift against exact combinatorial random expectations
- approximate z/p diagnostics against the hypergeometric random baseline

The exact random expectations are:

- Top-6: `36/49 ≈ 0.734694` winning numbers per draw
- Top-12: `72/49 ≈ 1.469388`
- Top-18: `108/49 ≈ 2.204082`

An empirical random model is retained as a sanity check but is not the reference used to claim lift, because one finite random realization can itself run high or low.

## Promotion rule

A model is not promoted because of one 4/6 or 5/6 historical hit. Promotion requires broad improvement across probability-quality and ranking metrics, preferably across multiple time blocks, and no obvious dependence on a single lucky interval. If the blind benchmark does not support a version, the correct result is to reject or keep it as a shadow model rather than tune it on the blind answers.
