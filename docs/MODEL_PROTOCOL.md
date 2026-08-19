# Model Research Protocol

## Non-negotiable: no future leakage

A target draw may use only information available strictly before that draw. This includes features, normalization, training labels, hyperparameter selection and ensemble weights.

## Research partitions

| Period | Purpose |
|---|---|
| 1982–2014 | development |
| 2015–2019 | validation/model selection |
| 2020–2025 | consumed historical diagnostic period (formerly the V2–V4 blind test) |
| 2026+ | model-specific prospective evidence only after that exact version is frozen |

The observed 2020–2025 outcomes are consumed for every V5+ attempt and must not
be described as blind, confirmatory, or untouched validation evidence. Once any
2026+ result influences a model change, that result is also consumed for the
changed model; the changed version must start a new prospective cohort.

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

## Planned anti-overfitting checks

- permutation tests
- bootstrap confidence intervals
- append-only family-wise Holm correction for registered discovery attempts
- shuffled-label controls
- stability across eras
- calibration curves
- probability sharpness vs accuracy

## Registered V10 structural-set diagnostic

`V10_adjacent_pair_structure v10.0.0` is registered and implemented in an
isolated model/one-shot runner for review, but it has not been historically
scored. It tests exactly one statistic: the count of adjacent integer pairs in
an unordered six-main-number set. Its complete-set law is a one-parameter
exponential tilt of the exact fair six-set distribution, estimated from every
strictly prior verified main draw with one fair-equivalent pseudo-observation.
Bonus numbers, alternate gaps, windows, eras, hard combination constraints,
joint-MAP tie choices, fitted scales, and calibration are excluded.

The sole formal primary remains Top-12 lift versus exact fair theory. The
complete-set prequential likelihood advantage is a mandatory conjunctive
mechanism check, not another selectable primary. Because the statistic is a sum
over same-draw label pairs, this attempt is variant 2 of the existing
`v5_pair_cooccurrence` Holm family. The only authorized historical run is the
fixed 621-target 2020–2025 consumed diagnostic; it cannot become confirmatory
evidence or activate the model. See
[`V10_adjacent_pair_structure.md`](experiments/V10_adjacent_pair_structure.md).

## Interpretation

The system is explicitly allowed to conclude that no exploitable predictive signal exists. Convergence toward equal `6/49` probabilities is a valid scientific result.
