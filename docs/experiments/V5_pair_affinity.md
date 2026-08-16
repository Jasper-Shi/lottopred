# V5 Pair-Affinity Pre-registration

## Registration status

| Field | Frozen value |
|---|---|
| Experiment ID | `V5_pair_affinity` |
| Candidate | `v5_pair_affinity` |
| Model version | `v5.0.0` |
| Feature family | pair/co-occurrence |
| Registration | **REGISTERED** |
| Candidate implementation | **NOT IMPLEMENTED** |
| Candidate evaluation | **NOT EVALUATED** |
| Prospective cohort | **NOT ACTIVATED** |
| Registration date | 2026-08-16 |
| Protocol seed | `649` |

This document freezes one outcome-blind candidate before any candidate score is
generated or inspected. The candidate's null or negative result is a successful
research outcome; this experiment exists to test a falsifiable claim, not to
manufacture a winning-number narrative. That interpretation follows the
repository's fair-lottery default and chronology/auditability priorities
([project instructions](../../AGENTS.md#mission),
[research roadmap](../RESEARCH_ROADMAP.md#objective)).

The machine-readable row is `V5_pair_affinity` in the
[experiment registry](registry.yaml). Registry validation, deterministic
negative-control construction, leakage assertions, and prospective-cohort
eligibility live in [research_protocol.py](../../src/lotto649/research_protocol.py)
and are covered by
[test_research_protocol.py](../../tests/test_research_protocol.py). Those are
supporting protocol components, not an implementation or evaluation of the
candidate model.

## Hypothesis

The alternative hypothesis is that, after strong fixed shrinkage, the historical
same-draw affinity between a candidate number and the six numbers in the
immediately preceding draw contains stable positive information about that
candidate's inclusion in the next draw. The directional prediction is a positive
prospective mean Top-12 hit lift relative to the exact fair value `72/49`.

The null hypothesis is that the ranking has no stable forward lift over the fair
`6/49` process. No causal mechanism is asserted. Under the repository protocol,
number labels are categorical and a pair-affinity hypothesis must be judged by
exact hits, ranks, and proper probability scores rather than numerical closeness
([model protocol](../MODEL_PROTOCOL.md#why-numerical-distance-is-meaningless),
[roadmap candidate families](../RESEARCH_ROADMAP.md#candidate-feature-families)).

## Evidence boundaries and frozen data state

The historical evidence lanes are fixed as follows; their meanings may not be
upgraded after results are viewed
([research roadmap](../RESEARCH_ROADMAP.md#evidence-lanes),
[project guardrails](../../AGENTS.md#leakage-and-research-guardrails)).

| Lane | Dates | Permitted interpretation for `v5.0.0` |
|---|---|---|
| Historical development | 1982-01-01 through 2014-12-31 | Development diagnostic only |
| Exposed legacy validation | 2015-01-01 through 2019-12-31 | Historical validation diagnostic; already exposed to model selection |
| Consumed historical diagnostic | 2020-01-01 through 2025-12-31 | Consumed diagnostic only; never blind or confirmatory |

All feature definitions, constants, inference rules, and decision gates in this
document are frozen **before any historical evaluation of this candidate**.
Although 1982-2014 retains the repository's `development` lane name, this
candidate has no grid or tuning step in that lane. The 2015-2019 and 2020-2025
answers cannot change this specification. This is deliberately stricter than the
roadmap's allowance for chronological development fitting
([research loop](../RESEARCH_ROADMAP.md#research-loop)).

At registration, the committed
[processed draw file](../../data/processed/draws.csv) contains 4,431 draws
through 2026-08-12 and has file SHA-256
`95434535857a95f3ae9bd25e42345291274804702ed514b0bace6fafcf584bdf`; this
fingerprint and its source commit
`39b99a9e0a6351b4143f81c9a95eb1639456a35d` are recorded in the
[experiment registry](registry.yaml). Every 2026 outcome available at
registration is consumed for `v5.0.0`: it is not prospective evidence, even if a
later diagnostic includes it. Prospective evidence can begin only after the
future reviewed activation commit described below, consistent with the
model-specific forward-evidence rule
([research roadmap](../RESEARCH_ROADMAP.md#evidence-lanes)).

## Exact candidate specification

### Information set

For target draw date `t`, let `H_t` be the complete expanding sequence of verified
draws whose dates are strictly earlier than `t`, ordered by date. Let `D = |H_t|`.
The model is eligible to predict only when `D >= 300`; it uses all `D` draws and
has no rolling window. The only anchors are the six main numbers in the last draw
of `H_t`. The target outcome, target bonus number, and every draw on or after `t`
are unavailable to feature construction. This is the repository's required
walk-forward information boundary
([backtest implementation](../../src/lotto649/backtest.py),
[model protocol](../MODEL_PROTOCOL.md#non-negotiable-no-future-leakage)).

### Counts and shrinkage

For every candidate `n` in `{1, ..., 49}` and every preceding-draw anchor `a`
where `a != n`, compute over the same complete `H_t`:

- `C_n`: number of visible prior draws containing `n`;
- `C_a`: number of visible prior draws containing `a`;
- `C_na`: number of visible prior draws containing both `n` and `a` in the same
  six-number outcome.

Define the fixed-shrinkage probabilities

```text
q_n         = (C_n  + 250 * (6/49)) / (D   + 250)
q_n_given_a = (C_na + 250 * (5/48)) / (C_a + 250)
```

and define `logit(x) = log(x / (1 - x))`. The anchor residual is

```text
residual(n, a) = logit(q_n_given_a) - logit(q_n)
```

The prior strength `250`, marginal prior `6/49`, conditional prior `5/48`, use of
same-draw counts, and complete expanding history are fixed. The strong shrinkage
and intact-pair treatment address the pair family's high multiplicity without
selecting individual pairs after seeing outcomes, as required by the roadmap
([pair/co-occurrence risk](../RESEARCH_ROADMAP.md#candidate-feature-families)).

### Score and probabilities

For candidate `n`, let `A_t(n)` be the preceding draw's anchors excluding `n`
itself. Thus `|A_t(n)|` is five if `n` appeared in the preceding draw and six
otherwise. Define

```text
score_n = mean(residual(n, a) for a in A_t(n))
```

Across the 49 candidate scores, use the population mean and population standard
deviation:

```text
mu    = mean(score_1, ..., score_49)
sigma = sqrt(mean((score_n - mu)^2 for n in 1..49))
z_n   = (score_n - mu) / (sigma + 1e-9)
raw_n = exp(0.10 * z_n)
p_n   = 6 * raw_n / sum(raw_j for j in 1..49)
```

The epsilon is exactly `1e-9`; the exponential coefficient is exactly `0.10`;
the z-score uses population, not sample, standard deviation. The final mapping is
the repository probability normalization contract: one strictly positive
probability for each label `1..49`, normalized to expected total six
([model base contract](../../src/lotto649/models/base.py)). Rankings sort by
descending `p_n`, breaking exact ties by ascending number, matching
[rank_numbers](../../src/lotto649/optimizer.py).

This candidate has no fitted coefficients, selectable pair subset, alternate
prior strength, alternate exponential scale, rolling or recency window,
constraint, post-hoc calibration, ensemble weight, or model-selection grid. It
does not use sum, odd/even, high/low, adjacency, calendar, periodicity, or final
combination constraints. Any change to the defined feature, count scope,
constant, normalization, tie-breaking, or minimum history changes statistical
behavior and therefore requires a new version and a new prospective cohort
([versioning rules](../MODEL_PROTOCOL.md#requires-a-new-model-version)).

## Outcomes, comparisons, and inference

### Primary outcome

For each eligible target `t`, let `h12_t` be the count of its six winning main
numbers contained in the model's pre-draw Top-12. The sole primary metric is

```text
mean(h12_t) - 72/49
```

The exact fair expectation is `72/49 = 1.469387...` hits per draw
([fair-lottery baselines](../MODEL_PROTOCOL.md#fair-lottery-baselines)). The
primary null p-value is the exact upper-tail probability for the observed total
Top-12 hits under independent `Hypergeometric(N=49, K=12, n=6)` draw-level hit
counts, evaluated by deterministic convolution rather than by a finite random
baseline. The directional alternative is positive lift.

The primary 95% confidence interval is the two-sided draw-level percentile
bootstrap interval for the mean lift, using 10,000 resamples and a fresh
deterministic `numpy.random.default_rng(649)` stream. The registered promotion
condition is that the interval's lower endpoint is strictly greater than zero.
The bootstrap count, method, confidence level, and seed are not selectable after
scores are observed. This supplies the roadmap's pre-specified uncertainty check
([validation protocol](../RESEARCH_ROADMAP.md#validation-protocol)).

### Bounded secondary outcomes

The complete secondary set is limited to:

- mean Top-6 hit lift versus exact `36/49`;
- mean Top-18 hit lift versus exact `108/49`;
- mean Brier score;
- mean binary log loss;
- mean actual rank of the six winning numbers.

Top-K hits, Brier score, binary log loss, and mean actual rank use the repository's
existing exact definitions in [evaluation.py](../../src/lotto649/evaluation.py).
No unregistered metric, subgroup, final-combination hit rate, selected year, or
alternative `K` can replace the primary outcome or rescue a failed gate. All
secondary outcomes are reported regardless of sign.

### Comparison set

Primary inference is against the exact fair Top-12 expectation. Proper scores are
compared with the constant `p_n = 6/49` fair baseline. On identical target dates,
reports also show the deterministic random baseline, each frozen V1 production
baseline (`long_frequency`, `recent_frequency`, `ema_gap`, `logistic`, and
`ensemble`), and the frozen V3 `v3_boosting` shadow reference. Their current
operational roles are defined in [config.yaml](../../config.yaml) and the
production/shadow decision is documented in
[V2-V4 results](../V2_V4_RESULTS.md#decision). These operational references are
descriptive comparisons only: they do not add candidate weights, select a
variant, or replace the fair primary null. V1 remains the production baseline and
V3 remains shadow unless a separate reviewed promotion decision satisfies the
prospective gate.

## Negative control

The sole registered primary negative control is a deterministic permutation of
**whole draw outcomes** across the fixed chronological draw dates, with seed
`649`. The six main numbers and bonus remain intact as one outcome; number labels
within a draw are never shuffled. Before walk-forward folds are formed, source
index `i` receives the SHA-256 sort key
`SHA256("lotto649-control-v1:649:{i}")`; source indices are sorted by that byte
digest and zipped to the original ordered date slots. An identity permutation is
rotated left by one position. The permuted series then passes through the exact
same minimum-history, feature, prediction, ranking, and scoring pipeline as the
candidate. This construction is frozen in
[research_protocol.py](../../src/lotto649/research_protocol.py).

The control is synthetic and can never support a prediction claim. It is run for
every registered historical report and again on the full fixed draw sequence at
the prospective checkpoint, with results restricted to the candidate's eligible
target dates. It is considered consistent with the null only if it fails the
candidate's positive primary gate: its upper-tail primary p-value must be greater
than `0.05` or its 95% bootstrap confidence interval must include zero. A control
with unadjusted upper-tail `p <= 0.05` **and** an interval wholly above zero is a pipeline
warning that blocks promotion and requires an audit, consistent with the
roadmap's negative-control rule
([leakage checks](../RESEARCH_ROADMAP.md#2-build-leakage-checks-before-feature-evaluation)).
No alternate seed or favorable control realization may be substituted for
`649` in this version.

## Leakage and integrity checks

Before any candidate scoring, automated tests must establish all of the
following through [research_protocol.py](../../src/lotto649/research_protocol.py)
and [test_research_protocol.py](../../tests/test_research_protocol.py):

1. Draw dates are strictly increasing and unique; every walk-forward fold uses
   exactly the prefix before its target.
2. `history[-1].draw_date < target_date`, `history_through < target_date`, and no
   target outcome participates in a count, anchor, cross-sectional z-score, or
   normalization.
3. The anchor set is exactly the prior visible draw's six main numbers, and every
   `C_n`, `C_a`, and `C_na` is recomputed only from that fold's visible prefix.
4. No prediction is emitted below 300 visible draws; at eligibility, all 49
   outputs are finite, lie strictly in `(0, 1)`, and sum to six within numerical
   tolerance.
5. Re-running from the same ordered inputs is bitwise deterministic where
   serialized, and appending future draws cannot change a previously generated
   fold prediction.
6. The negative control preserves fixed dates and intact valid outcomes, changes
   their assignment deterministically, and enters the same strict-prefix
   walk-forward builder.
7. Every report records experiment ID, exact model/version, command, seed,
   configuration, data path and SHA-256, history boundary, code commit, and full
   comparison set, as required for reproducibility
   ([validation protocol](../RESEARCH_ROADMAP.md#validation-protocol)).

Any failed chronology, prefix-invariance, probability-contract, source-integrity,
or snapshot-integrity check invalidates the affected run. It is reported as
`Archive`, with no performance claim, rather than repaired after outcomes are
known ([reporting decisions](../RESEARCH_ROADMAP.md#reporting-decisions)).

## Multiplicity ledger

The multiplicity family is every pair/co-occurrence candidate variant ever
recorded in the append-only [experiment registry](registry.yaml), including
future pair/co-occurrence attempts. `V5_pair_affinity` is variant 1 and the family
currently contains one variant. No failed, abandoned, or negative variant may be
removed from the denominator.

Family-wise alpha is `0.05`. At every formal decision, raw primary p-values for
all recorded variants are adjusted together by Holm's step-down family-wise
procedure; a recorded variant without a valid primary p-value is conservatively
entered as `p = 1`. With one recorded variant, the current Holm family size is
one; a future variant expands the same family, and any later claim must recompute
the adjustment over the expanded ledger. Secondary metrics and subgroups do not
create alternate discovery claims. This implements the repository requirement to
record every attempt and correct for multiple comparisons
([project guardrails](../../AGENTS.md#leakage-and-research-guardrails),
[validation protocol](../RESEARCH_ROADMAP.md#validation-protocol)).

## Prospective cohort and stopping rule

No cohort start date or freeze commit is registered today. The registry status is
`registered` and the cohort status is `not_activated`. A start date and immutable
freeze commit may be set only by a future reviewed freeze/live-activation commit
that implements this exact `v5.0.0` specification as a `shadow` model. No target
before that activation can be included retrospectively
([start a prospective cohort](../RESEARCH_ROADMAP.md#6-start-a-prospective-shadow-cohort)).

After activation, a target is eligible only when all of these conditions hold:

- the first Git commit containing the exact snapshot blob predates `00:00`
  `America/Toronto` on the target date;
- the snapshot has `model_name = v5_pair_affinity`,
  `model_version = v5.0.0`, and `metadata.role = shadow` exactly;
- its target is on or after the registered cohort start and its
  `metadata.history_through` date is strictly before the target;
- its recorded digest matches the committed snapshot, the first commit identity
  is available, the verified source result passes integrity checks, and the
  evaluation identity matches the snapshot;
- the snapshot is original, immutable, and not missing, late, regenerated, or
  integrity-failed.

These rules are enforced by the prospective assessment in
[research_protocol.py](../../src/lotto649/research_protocol.py). Prediction files
are already write-once by default in [storage.py](../../src/lotto649/storage.py),
and the live workflow labels configured research models as shadow in
[live.py](../../src/lotto649/live.py). An excluded observation remains excluded;
it is never regenerated or repaired to improve cohort results.

The sole formal prospective decision point is the first time **104 eligible,
evaluated, exact-version draws** exist. Exclusions delay the calendar date but do
not lower the count. There is no early efficacy look, automatic promotion, or
registered extension. At 104, split the chronologically ordered cohort into the
first 52 and last 52 eligible draws. Promotion requires every condition below:

1. primary mean Top-12 lift is positive;
2. its Holm-adjusted one-sided p-value is `<= 0.05` and its registered 95%
   bootstrap confidence interval has lower endpoint `> 0`;
3. mean Brier score and mean binary log loss are each no worse than the
   constant-`6/49` fair baseline;
4. primary lift is strictly positive in both the first and second 52-draw halves;
5. the registered negative control behaves as null and there is no unresolved
   leakage, source, missed-snapshot, or audit-trail issue; and
6. a separate reviewed promotion PR documents the complete evidence and changes
   the operational role.

This gate is no weaker than the roadmap default
([default promotion gate](../RESEARCH_ROADMAP.md#default-promotion-gate)). If any
condition fails at the fixed checkpoint, `v5.0.0` is rejected; a null or negative
result is complete and successful research. Continuing, changing, or combining
the idea would require a separately pre-registered new version and prospective
cohort. V1 remains production and V3 remains shadow throughout this experiment;
promotion is never automatic.

## Reporting commitment

Every valid historical diagnostic will disclose every registered lane, all five
secondary metrics, fair and operational comparisons, the seed-649 negative
control, uncertainty, multiplicity status, excluded folds, and failures as well
as successes. The 2020-2025 lane will be labeled `consumed historical
diagnostic`, never blind, validation, confirmation, or prospective evidence.

Every valid prospective report will include all eligible and excluded targets,
both fixed halves, the exact registry and data fingerprints, and the unchanged
decision gate. If any observed 2026+ result influences feature definitions,
parameters, windows, weights, constraints, model selection, or interpretation of
a changed candidate, that observation is consumed for the changed candidate;
`v5.0.0` closes and the changed version begins a new prospective cohort. These
commitments implement the repository's evidence-lane and decision rules
([research roadmap](../RESEARCH_ROADMAP.md#7-decide-without-tuning-the-cohort),
[project completion criteria](../../AGENTS.md#completion-criteria)).
