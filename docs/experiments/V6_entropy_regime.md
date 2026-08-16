# V6 Fixed-Boundary Entropy-Regime Pre-registration

## Frozen identity

| Field | Value |
|---|---|
| Experiment ID | `V6_fixed_boundary_js_regime` |
| Model | `v6_entropy_regime` |
| Version | `v6.0.0` |
| Family / variant | `entropy_regime` / `1` |
| Status | **CLOSED — REJECTED; NEVER ACTIVATED** |
| Registration date | 2026-08-16 |
| Protocol seed | `649` |
| Live role | none; V1 stays production and V3 stays shadow |

This note freezes one bounded hypothesis before implementation and before any V6
historical score. A null or negative result is a successful outcome. Historical
results cannot establish a predictive lottery model; only an exact-version,
immutable prospective cohort can provide confirmatory evidence
([project mission](../../AGENTS.md#mission),
[research objective](../RESEARCH_ROADMAP.md#objective)).

Administrative status and commit fields may later be updated without changing
any formula, constant, metric, control, comparison, or decision rule below.

The one frozen historical diagnostic has now been completed without changing
this specification. It failed the registered gates, so `v6.0.0` is rejected and
remains unactivated. See the
[decision record](V6_entropy_regime_results.md) and generated
[historical report](../../reports/v6_entropy_regime_v6.0.0_historical.md).

## Hypothesis and independence boundary

The alternative hypothesis is that a large, pre-draw redistribution of the 49
main-number inclusion counts between two adjacent fixed 104-draw blocks tends to
continue for one next draw. A global entropy/log-ratio statistic must cross a
fixed nominal 1% asymptotic gate before the signed per-number redistribution is used. The
directional prediction is positive mean Top-12 hit lift versus exact fair
`72/49`. The null is no stable forward lift.

V6 uses no bonus, calendar, number magnitude, draw sum, odd/even, adjacency,
individual long-frequency or EMA level, fitted classifier, pair count,
previous-draw anchor, V1/V2/V3/V5 prediction, ensemble weight, or combination
constraint. It is therefore a separate fixed-boundary regime hypothesis, not a
retune or relabeling of V2/V3/V5.

There is nevertheless a disclosed raw-data overlap: V2/V3 include rolling
frequency features, while V6 also counts inclusions. V6 is behaviorally distinct
because it uses only two non-overlapping 104-draw blocks, their signed contrast,
and one global fixed gate; it does not use their models or parameters. A positive
V6 result would apply only to exact `v6.0.0` and must not be called a fully
orthogonal replication of V2/V3
([actual V2/V3 features](../../src/lotto649/research_features.py),
[V2–V4 results](../V2_V4_RESULTS.md),
[V5 result](V5_pair_affinity_results.md)).

The entropy convention is the natural-log discrete form introduced in
[Shannon (1948)](https://onlinelibrary.wiley.com/doi/10.1002/j.1538-7305.1948.tb00917.x).
No external empirical lottery claim is used.

## Evidence and data boundaries

| Lane | Dates | Allowed claim |
|---|---|---|
| Development | 1982-01-01 to 2014-12-31 | Historical development diagnostic only |
| Legacy validation | 2015-01-01 to 2019-12-31 | Exposed historical stability diagnostic |
| Consumed diagnostic | 2020-01-01 to 2025-12-31 | Consumed diagnostic only; never blind, confirmatory, or prospective |
| Prospective | Only after a future reviewed freeze/activation commit | Confirmatory evidence for exact `v6.0.0` only |

The immutable historical-diagnostic prefix is 4,431 draws through 2026-08-12:

- path: [`data/processed/draws.csv`](../../data/processed/draws.csv);
- raw SHA-256:
  `95434535857a95f3ae9bd25e42345291274804702ed514b0bace6fafcf584bdf`;
- source commit: `39b99a9e0a6351b4143f81c9a95eb1639456a35d`.

One newer outcome was already known at registration. The committed known-outcome
prefix is 4,432 draws through 2026-08-15, raw SHA-256
`edfb7f8a4a7711a630957d6f86b567e6b254caf7b1d1aaea0edf1d16a34155b3`,
source commit `90177c80cfb070038d79508fb2e73305a297f516`. That draw, and every
other result observed before a future activation, is consumed for `v6.0.0` and
can never enter its prospective cohort. The historical diagnostic still ends at
2025-12-31; it does not create a pseudo-forward 2026 lane
([evidence lanes](../RESEARCH_ROADMAP.md#evidence-lanes)).

## Exact model specification

### Information set and fixed blocks

For target date `t`, let `H_t` be all verified draws strictly before `t`, ordered
by unique date, and let `D = |H_t|`. The model is eligible only when `D >= 300`.
Only the final 208 visible draws are used:

```text
B0 = H_t[D-208 : D-104]   # older block, exactly 104 draws
B1 = H_t[D-104 : D]       # newer block, exactly 104 draws
```

For each main-number label `n in {1,...,49}`, let `c0_n` and `c1_n` be its
inclusion counts in `B0` and `B1`, and let `e_n = (c0_n + c1_n) / 2`.
Define `0 * log(0/e) = 0`; if `c0_n = c1_n = 0`, set `g_n = a_n = s_n = 0`.

### Frozen regime statistic

```text
g_n = 2 * [c0_n * log(c0_n / e_n) + c1_n * log(c1_n / e_n)]
a_n = (48 / 43) * g_n
T   = sum_(n=1)^49 a_n
```

The factor `48/43`, all block lengths, and all following constants are frozen.
The regime is active if and only if

```text
T > 73.68263852010577.
```

Equality is inactive. The constant is the frozen 99th percentile of a
chi-square distribution with 48 degrees of freedom; its definition is available
in the official
[SciPy chi-square documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.chi2.html).
The chi-square label explains the pre-registration choice only: primary
inference remains the exact fair Top-12 test below, not an asymptotic p-value for
`T`. There is no alternate boundary, window, degree of freedom, or gate.

### Signed scores and probabilities

For every label,

```text
s_n     = sign(c1_n - c0_n) * a_n
mu      = mean(s_1, ..., s_49)
sigma   = sqrt(mean((s_n - mu)^2 for n in 1..49))
z_n     = (s_n - mu) / (sigma + 1e-12)
```

`sigma` is the population standard deviation and the epsilon is exactly
`1e-12`. Generate 49 deterministic tie-break values, in label order `1..49`, by

```text
rng       = numpy.random.default_rng(649000000 + target_date.toordinal())
jitter_n  = rng.uniform(-1e-9, 1e-9, size=49)[n-1]
```

where `toordinal()` is Python's `date.toordinal()`. Then

```text
eta_n = 0.10 * z_n + jitter_n    if T > 73.68263852010577
eta_n = jitter_n                 otherwise
raw_n = exp(eta_n)
p_n   = 6 * raw_n / sum_j raw_j.
```

Inactive predictions are therefore fair up to the registered outcome-independent
tie-break jitter. No clipping, calibration, constraint, ensemble, refit, or
post-normalization is permitted. Outputs must contain exactly labels `1..49`, be
finite and strictly in `(0,1)`, and sum to six within absolute tolerance
`1e-12`. Rank by descending probability, then ascending label for any exact tie,
matching [`rank_numbers`](../../src/lotto649/optimizer.py). Bonus numbers and the
final combination do not enter the primary or secondary metrics: only the six
main numbers are prediction/scoring targets, bonus is excluded from features and
scoring, and final-combination hits are not a registered evaluation metric.

Any change to the 300-draw eligibility rule, 208/104 blocks, count definition,
`48/43`, gate, sign, z-score, epsilon, scale `0.10`, jitter seed/range, softmax,
or tie rule creates a new model version and a new cohort.

## Primary, secondary, and comparisons

For eligible target `t`, let `h12_t` be the number of its six winning main
numbers in the frozen pre-draw Top-12. The sole primary metric is

```text
mean(h12_t) - 72/49.
```

The raw one-sided p-value is the exact upper-tail probability of the total
Top-12 hits under independent draw-level
`Hypergeometric(N=49, K=12, n=6)` variables, evaluated by deterministic
convolution. The 95% interval is a two-sided draw-level percentile bootstrap for
the mean lift with exactly 10,000 resamples and a fresh
`numpy.random.default_rng(649)` stream. A finite random run never replaces exact
fair theory
([fair baselines](../MODEL_PROTOCOL.md#fair-lottery-baselines)).

The bounded secondary set is exactly:

- mean Top-6 lift versus `36/49`;
- mean Top-18 lift versus `108/49`;
- mean Brier score and delta versus constant `6/49`;
- mean binary log loss and delta versus constant `6/49`;
- mean actual rank of the six winners.

Use the repository definitions in
[`evaluation.py`](../../src/lotto649/evaluation.py). Report every secondary
regardless of sign. No subgroup, year, alternate `K`, final-combination result,
or unregistered metric can replace the primary or rescue failure.

The fixed descriptive comparison set on identical target dates is: exact fair
theory; deterministic `random v1.0.0`; all V1 production models
(`long_frequency v1.0.0`, `recent_frequency v1.0.0`, `ema_gap v1.0.0`,
`logistic v1.0.0`, `ensemble v1.0.0`); `v3_boosting v1.0.0` shadow;
rejected `v5_pair_affinity v5.0.0`; and `v6_entropy_regime v6.0.0`. Their
already-frozen same-fold summaries may be reused from
[`v5_pair_affinity_v5.0.0_historical.json`](../../reports/v5_pair_affinity_v5.0.0_historical.json)
rather than refitted. Its frozen raw SHA-256 is
`b86391ada265d96f94e789f4962812d32771385702e2efa2285cb9ef96d5d6bb`;
identity, dataset, lane, model-version, and eligible-count mismatches must stop
the V6 run before any candidate scoring. V2 and V4 are contextual references only through
[`V2_V4_RESULTS.md`](../V2_V4_RESULTS.md); they are not refitted or represented
as identical-target comparisons. Comparisons do not select weights or variants
and do not change operational roles.

## Dedicated negative time/phase control

The sole registered control is the existing seed-649 whole-draw date
permutation in
[`permute_draw_outcomes`](../../src/lotto649/research_protocol.py). It keeps the
ordered date slots fixed and each valid six-main-number-plus-bonus outcome
intact, but deterministically reassigns outcomes to dates before forming folds.
V6 then runs through the exact same 300-draw eligibility, adjacent-block,
regime-gate, jitter, ranking, and scoring pipeline.

This is V6's dedicated time/phase control: it destroys the original placement of
outcomes across the two fixed 104-draw phases without inventing invalid draws or
shuffling labels within a draw. No other seed, permutation, block alignment, or
favorable realization may be substituted.

The control is consistent with null when its raw primary `p > 0.05` or its 95%
bootstrap interval includes zero. Raw `p <= 0.05` **and** an interval wholly
above zero is a pipeline warning that blocks shadow activation/promotion and
requires audit. A control never supports a prediction claim and does not enter
the discovery Holm family.

## Leakage and implementation checks before scoring

Offline deterministic tests must prove all of the following before the first V6
historical score is generated:

1. dates are strictly increasing/unique, every fold is the exact prefix before
   its target, and `history[-1].draw_date < target_date`;
2. a hand-computed synthetic oracle verifies `B0`, `B1`, counts, zero-count
   convention, `g`, `a`, `T`, strict gate, signs, population z-score, jitter,
   softmax, and ranks;
3. the target, bonus, and any future suffix cannot change its prediction;
4. histories of 299 draws are ineligible and 300 are eligible; modifying
   `H_t[-209]` cannot change output, while a synthetic modification at
   `H_t[-208]` can change output;
5. inactive, active, equal-count, and a label with zero count in both blocks
   satisfy the 49-probability contract and deterministic serialization;
6. repeated target dates reproduce the exact seed-649-derived jitter vector and
   different dates use the exact registered ordinal seed;
7. a global 49-label permutation is equivariant for active directional scores;
   inactive jitter is checked separately against its exact date-derived seed;
8. the seed-649 intact-outcome permutation changes phase assignment and passes
   through the same strict-prefix pipeline;
9. reports record experiment/model/version, exact command, seed, config and code
   commit, both data identities, hashes, all comparisons, eligible/excluded
   counts, and control results;
10. the runner verifies both registered data boundaries from their committed Git
    blobs, requires a completely clean worktree plus the canonical committed
    research config, and refuses to overwrite an existing historical report;
11. the research config disables the live path, and no existing file in
    `predictions/` or `evaluations/` is changed or regenerated.

Any chronology, leakage, probability, source-prefix, control, or audit failure
archives the run with no performance claim; it is not repaired under the same
version after answers are inspected
([roadmap leakage checks](../RESEARCH_ROADMAP.md#2-build-leakage-checks-before-feature-evaluation)).

## Multiplicity and historical decision

The append-only multiplicity family is `entropy_regime`; V6 is variant 1. Every
later alternate window, boundary, statistic, correction, gate, sign, scale,
jitter, mapping, or entropy/change-regime candidate remains in this family.
A genuinely different family must be registered before any score for its first
candidate exists; entropy variants cannot be reclassified after their outcomes
are known. Failed, abandoned, invalid, and negative attempts remain in the
denominator.

At each formal decision, adjust all recorded family primary p-values with Holm's
step-down procedure at family-wise `alpha = 0.05`; a missing/invalid p-value
enters as `1`. With this sole variant, current family size is one. Secondary
metrics and controls cannot become alternative discovery tests. The original
procedure is [Holm (1979)](https://doi.org/10.2307/4615733).

After the implementation/config/registry/tests are committed, run one frozen
historical diagnostic and publish all three lanes, every metric/comparison, the
control, uncertainty, Holm state, failures, exclusions, hashes, and command.
No parameter may change in response.

Historical evidence can justify only a separate reviewed **shadow** activation.
Eligibility requires: positive primary lift in all three lanes; the 2020–2025
consumed-diagnostic lane's Holm-adjusted exact `p <= 0.05` and bootstrap lower
endpoint `> 0`; Brier and log-loss deltas versus fair each `<= 1e-9` in every
lane; null control in every lane; and no audit warning. Only the consumed lane's
primary p-value enters this historical Holm decision. Development and legacy
p-values and intervals are reported but cannot become alternate discovery
tests. Failure means **Reject**, or **Archive** if implementation is invalid.
Passing can support a reviewed shadow PR only; consumed data are not
confirmatory evidence and activation is never automatic.

## Prospective cohort and fixed decision

At registration, `cohort_start`, `freeze_commit`, `activation_commit`, and
`outcomes_known_at_activation` are null and status is `not_activated`. Only a
future reviewed PR may add exact `v6.0.0` as shadow, verify every outcome known
at activation, and set a strictly later start. No known or late target may be
backfilled. Eligibility must
use immutable, original snapshots committed before `00:00 America/Toronto` on
their target date, with exact model/version/role, strictly prior
`history_through`, verified digest/first commit/generated time/source/evaluation,
and no regeneration
([cohort assessment](../../src/lotto649/research_protocol.py)).

The sole formal look is exactly **208 eligible, evaluated, exact-version draws**.
Exclusions delay but never reduce that count. There is no early efficacy look,
optional extension, or automatic promotion. Split the ordered cohort into the
first 104 and last 104 eligible draws. Promotion requires all of:

1. full-cohort primary Top-12 lift is positive;
2. Holm-adjusted exact one-sided `p <= 0.05` and bootstrap lower endpoint `> 0`;
3. Brier and binary-log-loss deltas versus constant fair `6/49` are each
   `<= 1e-9`, using the same frozen tolerance as the historical gate;
4. primary lift is strictly positive in both fixed 104-draw halves;
5. the registered control behaves as null and no leakage/source/snapshot/audit
   issue remains; and
6. a separate reviewed promotion PR publishes all evidence and changes role.

If any gate fails, reject `v6.0.0`. Any behavior change starts a new version and
new cohort; every outcome that influenced the change is consumed for that new
candidate. V1 remains production and V3 remains shadow throughout unless their
own separately reviewed evidence changes those roles
([default promotion gate](../RESEARCH_ROADMAP.md#default-promotion-gate),
[decide without tuning](../RESEARCH_ROADMAP.md#7-decide-without-tuning-the-cohort)).

## Source ledger

Repository authorities: [`AGENTS.md`](../../AGENTS.md),
[`MODEL_PROTOCOL.md`](../MODEL_PROTOCOL.md),
[`V2_V4_RESULTS.md`](../V2_V4_RESULTS.md),
[`RESEARCH_ROADMAP.md`](../RESEARCH_ROADMAP.md),
[`V5_pair_affinity.md`](V5_pair_affinity.md),
[`V5_pair_affinity_results.md`](V5_pair_affinity_results.md),
[`research_features.py`](../../src/lotto649/research_features.py),
[`v5_pair_affinity.py`](../../src/lotto649/models/v5_pair_affinity.py),
[`backtest.py`](../../src/lotto649/backtest.py), and
[`research_protocol.py`](../../src/lotto649/research_protocol.py).

External primary/official definitions only: Shannon (1948), linked above;
Sture Holm, “A Simple Sequentially Rejective Multiple Test Procedure,”
*Scandinavian Journal of Statistics* 6 (1979),
[DOI 10.2307/4615733](https://doi.org/10.2307/4615733); and official SciPy
chi-square documentation, linked above.
