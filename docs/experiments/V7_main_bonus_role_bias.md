# V7 Post-RNG Main/Bonus Role-Bias Pre-registration

## Frozen identity

| Field | Value |
|---|---|
| Experiment ID | `V7_post_rng_main_bonus_role_bias` |
| Family / variant | `draw_role_exchangeability` / `1` |
| Model | `v7_main_bonus_role_bias` |
| Version | `v7.0.0` |
| Status | **IMPLEMENTED AND FROZEN — NOT SCORED** |
| Registration date | 2026-08-16 |
| Protocol seed | `649` |
| Live role | none; V1 stays production and V3 stays shadow |

This note froze one bounded hypothesis before V7 implementation and before any
V7 historical prediction score or role-audit statistic was produced. The
fair, exchangeable draw remains the default explanation, and a null or negative
result is a successful research outcome. The primary-source rationale was fixed
separately in the unscored
[mechanical-bias basis](../research/V7_mechanical_bias_basis.md).

The deterministic candidate, dedicated control, diagnostic runner, and offline
tests are now implemented on the V7 feature branch. No V7 historical score or
role-audit statistic has been run or inspected. The implementation commit is the
freeze boundary recorded by the diagnostic command and its future report; the
runner refuses to score any different or dirty working tree.

Immediately after every preflight passes and before the first scoring call, the
runner exclusively creates
`reports/v7_main_bonus_role_bias_v7.0.0_historical.claim`. That claim is a
permanent one-shot audit artifact on both success and failure; it must never be
deleted to permit a rerun. Complete JSON and Markdown are first written to
same-directory `.tmp` files and then published sequentially. A caught partial
publication is rolled back; a crash or other failure after claiming retains the
permanent claim plus any staging or partial-publication evidence, consumes the
attempt, and requires **Archive** review rather than cleanup-and-rerun. A
successful report records the permanent claim path and SHA-256 and removes only
the staging files.

Historical results through 2025 are consumed diagnostics. They cannot establish
a predictive lottery model or be called blind, confirmatory, validation, or
prospective evidence. Administrative status and commit fields may later be
updated without changing any formula, constant, metric, control, comparison, or
decision rule below.

## Hypothesis and independence boundary

The registered alternative is that, after LOTTO 6/49 moved to an RNG draw
mechanism, number identity has a stable effect on whether an already-selected
label is assigned to one of the six main roles rather than the bonus role. If
that conditional role effect is stable, strictly lagged main/bonus role counts
may improve the next draw's six-main-number ranking and probabilities. The null
is conditional main/bonus exchangeability and no stable forward lift.

V7 is a draw-role hypothesis. It does not use a rolling hot/cold window, pair or
transition counts, entropy/change-point gates, calendar values, number magnitude,
sum or gap features, V1/V2/V3/V5/V6 predictions, fitted coefficients,
calibration, constraints, or ensemble weights. Its only non-fair input is each
label's strictly prior post-RNG count in the six main positions versus its count
in the bonus position. This makes it a distinct family from the rejected V5
pair-affinity and V6 entropy-regime candidates, although all models ultimately
consume the same public draw record.

The role-bias interpretation is deliberately narrow. Outcome data alone cannot
identify whether any detected departure arose in RNG role mapping, publication
labelling, or chance, and cannot establish misconduct. The official transition
date and primary sources supporting the mechanism boundary are recorded in the
[basis note](../research/V7_mechanical_bias_basis.md).

## Evidence and data boundaries

V7 has exactly one applicable historical prediction lane:

| Lane | Dates | V7 status and allowed claim |
|---|---|---|
| Historical development | 1982-01-01 to 2014-12-31 | **N/A**; pre-RNG and prohibited from V7 scoring or gates |
| Legacy validation | 2015-01-01 to 2019-12-31 | **N/A**; mechanism transition/burn-in only and prohibited from V7 scoring or gates |
| Post-RNG consumed diagnostic | 2020-01-01 to 2025-12-31 | Exactly 621 target draws; consumed historical diagnostic only |
| Prospective | Only after a future reviewed freeze/activation commit | Confirmatory evidence for exact `v7.0.0` only |

The fixed post-RNG information boundary is `2019-05-15`. Draws from that date
through 2019-12-31 may accumulate strictly lagged counts for 2020 targets, but
they are not a separate scoring lane and cannot rescue a failed 2020–2025 result.
Every one of the 621 targets from 2020-01-01 through 2025-12-31 is included,
including targets before the model becomes active; those targets receive the
registered fair fallback. The two fixed stability splits are calendar periods
`2020-01-01..2022-12-31` and `2023-01-01..2025-12-31`. No alternate split,
year, start date, or subgroup may replace them.

The committed dates mechanically imply 65 post-RNG burn-in draws through
2019-12-31, 39 fair-fallback targets, 582 active targets, and first activation
on 2020-05-20. The two fixed halves contain exactly 307 and 314 targets. These
are fail-closed integrity counts, not selected performance subgroups; the
runner must reject any mismatch before scoring.

The immutable registration-data prefix is 4,431 draws through 2026-08-12:

- path: [`data/processed/draws.csv`](../../data/processed/draws.csv);
- raw SHA-256:
  `95434535857a95f3ae9bd25e42345291274804702ed514b0bace6fafcf584bdf`;
- source commit: `39b99a9e0a6351b4143f81c9a95eb1639456a35d`.

One newer outcome was already known at registration. The known-outcome prefix is
4,432 draws through 2026-08-15, raw SHA-256
`edfb7f8a4a7711a630957d6f86b567e6b254caf7b1d1aaea0edf1d16a34155b3`,
source commit `90177c80cfb070038d79508fb2e73305a297f516`. That outcome and every
other result observed before any future activation are consumed for `v7.0.0` and
can never be added to its prospective cohort.

The frozen descriptive-reference report is
[`reports/v6_entropy_regime_v6.0.0_historical.json`](../../reports/v6_entropy_regime_v6.0.0_historical.json),
raw SHA-256
`12400a4b5164b030225827d47a8024a1ec7aeaeb32fa64cd2fab0b46ff8d4c2a`.
Its identity, digest, data boundary, target dates, eligible count, lane, model
names, and versions must be verified before reuse. A mismatch stops the V7 run
before candidate scoring.

## Exact model specification

### Strictly lagged post-RNG counts

For target date `t`, let `H_t` contain all verified draws satisfying

```text
2019-05-15 <= draw_date < t
```

ordered by strictly increasing unique date. The target, every same-date value,
and every future draw are excluded. Let `R_t = |H_t|`. For each categorical
label `i in {1,...,49}`, define

```text
m_i(t) = number of draws in H_t where i is one of the six main numbers
b_i(t) = number of draws in H_t where i is the bonus number.
```

The historical bonus is an explicitly permitted predictor only because it is
strictly before `t`. The target bonus is unavailable and prohibited from the
feature, ranking, hits, and every per-target predictive score. After the result
is revealed, its bonus role may enter only the pre-registered aggregate `G`
role audit; that audit is not a prediction score and cannot alter the frozen
prediction.

The signal is active if and only if `R_t >= 104`. When `R_t < 104`, set every
`u_i(t) = 0`, yielding the exact fair fallback. When active, set

```text
u_i(t) = log((m_i(t) + 3) / (b_i(t) + 0.5)) - log(6).
```

The boundary, comparison operator, full expanding post-RNG history, and fixed
pseudo-counts `3` and `0.5` are immutable. The pseudo-counts come from one
seven-role `Dirichlet(1/2,...,1/2)` prior: aggregating the six main roles gives
`6 * 1/2 = 3`, while the single bonus role gives `1/2`. There is no rolling
window, alternate minimum, decay, number selection, or count weighting.

### Probability mapping and deterministic root

When `R_t < 104`, or when all 49 computed `u_i(t)` are exactly zero, bypass the
numerical solver and directly return the exact constant vector `p_i(t) = 6/49`.
Otherwise, for all labels define

```text
p_i(t) = sigmoid(alpha_t + u_i(t)),
```

where `alpha_t` is the unique root of

```text
sum_(i=1)^49 sigmoid(alpha_t + u_i(t)) = 6.
```

Use the stable sigmoid exactly:

```text
sigmoid(x) = 1 / (1 + exp(-x))       if x >= 0
sigmoid(x) = exp(x) / (1 + exp(x))   if x < 0.
```

The root implementation is frozen deterministic bisection. Let
`A = max_i(abs(u_i(t)))`, initialize

```text
lower = -64 - A
upper =  64 + A,
```

and perform exactly 256 iterations. On each iteration set
`mid = (lower + upper) / 2`. If
`sum_i sigmoid(mid + u_i) > 6`, replace `upper = mid`; otherwise replace
`lower = mid`. After iteration 256, set `alpha_t = (lower + upper) / 2` and
compute the final probabilities with the stable sigmoid above. Equality follows
the `lower = mid` branch. No library root solver or tolerance-based early exit
may replace this algorithm.

Before the first iteration, verify strictly that

```text
sum_i sigmoid(lower + u_i) < 6 < sum_i sigmoid(upper + u_i).
```

Failure to bracket the root is a model/audit error; the implementation must not
clip `alpha`, accept an endpoint, expand the registered bracket, or continue.
After the iterations, `alpha_t` must be strictly inside the original bracket.

The final output must contain exactly labels/keys `1..49` (canonical JSON keys
`"1"` through `"49"`), every probability must be finite and strictly in
`(0,1)`, and their sum must equal six within absolute tolerance `1e-12`. Rank by
descending probability, then ascending numeric label for any exact tie, matching
[`rank_numbers`](../../src/lotto649/optimizer.py). The inactive vector is exactly
constant `6/49`; there is no jitter.

There is no signal scale, fitted parameter, training step, normalization beyond
the intercept, probability clipping, calibration, combination constraint,
ensemble, or final-combination evaluation. Any change to the boundary, active
minimum, counts, pseudo-counts, baseline odds, sigmoid, root bracket/iterations,
tie rule, or probability contract creates a new model version and a new
prospective cohort.

## Primary, secondary, and descriptive comparisons

For every one of the 621 registered target dates, let `h12_t` be the number of
the target's six winning **main** numbers in the frozen pre-draw Top-12. The sole
primary predictive metric is

```text
mean(h12_t) - 72/49.
```

The one-sided raw p-value is the exact upper-tail probability of the observed
total Top-12 hits under independent draw-level
`Hypergeometric(N=49, K=12, n=6)` variables, computed by deterministic
convolution. The 95% interval is a two-sided draw-level percentile bootstrap of
the mean lift: initialize a fresh `numpy.random.default_rng(649)`, draw exactly
10,000 samples of 621 draw indices with replacement, compute each mean lift,
and take the `0.025` and `0.975` quantiles using NumPy's linear quantile method.
Compute and report the same exact raw upper-tail p-value and bootstrap interval
separately for each fixed stability half, using all targets in that half and a
fresh seed-649 generator. Half p-values are descriptive and do not enter the
Holm family or replace the aggregate test. A finite random run never replaces
exact fair theory.

The bounded secondary set is exactly:

- mean Top-6 lift versus `36/49`;
- mean Top-18 lift versus `108/49`;
- mean Brier score and delta versus the constant fair probability `6/49`;
- mean binary log loss and delta versus the constant fair probability `6/49`;
- mean actual rank of the six target main numbers; and
- the one pre-registered global conditional role audit defined below.

Use the repository definitions in
[`evaluation.py`](../../src/lotto649/evaluation.py) and report every secondary for
the aggregate and both fixed halves regardless of sign. No target bonus,
individual label, year, alternate `K`, combination hit, or unregistered metric
can replace the primary or rescue failure.

On the identical 621 target dates, the fixed descriptive comparison set is exact
fair theory; deterministic `random v1.0.0`; every V1 production baseline
(`long_frequency`, `recent_frequency`, `ema_gap`, `logistic`, and `ensemble`, all
`v1.0.0`); `v3_boosting v1.0.0` shadow; rejected
`v5_pair_affinity v5.0.0`; and rejected `v6_entropy_regime v6.0.0`. Reuse the
already-frozen consumed-lane summaries from the registered V6 reference report;
do not refit, retrain, select, reweight, or substitute comparisons. Descriptive
comparisons never enter the V7 decision gate and never change operational roles.

## Frozen global conditional role audit

This audit is a post-outcome mechanism diagnostic, not a feature, hit, rank,
proper score, or primary predictive metric. It is the only registered operation
that may inspect realized bonus roles in the audit interval after their outcomes
are known. Use every draw with
`2019-05-15 <= draw_date <= 2025-12-31`. For each label, let
`m_i`, `b_i`, and `n_i = m_i + b_i` be its aggregate main, bonus, and selected
counts in that fixed interval. Define the conditional 6:1 likelihood-ratio
statistic

```text
G = 2 * sum_(i=1)^49 [
      m_i * log(m_i / (6*n_i/7))
    + b_i * log(b_i / (  n_i/7))
].
```

Use the complete conventions
`m_i * log(m_i / (6*n_i/7)) = 0` when `m_i = 0` and
`b_i * log(b_i / (n_i/7)) = 0` when `b_i = 0`; equivalently `0*log(0)=0`.
If `n_i = 0`, both terms for label `i` are zero. Do not inspect or select any of
the 49 label-level effects as a replacement statistic.

Calibrate `G` only by within-draw role randomization. Initialize one fresh
`numpy.random.default_rng(649)`. For replicate `r = 1..10,000`, process the
fixed audit draws in chronological order; sort each draw's observed seven labels
ascending, use `rng.integers(0, 7)` to choose its pseudo-bonus, and assign the
other six labels to pseudo-main. Compute `G_r` from that replicate. The
plus-one, right-tail Monte Carlo p-value is exactly

```text
p_global = (1 + count(G_r >= G_observed)) / 10001.
```

No asymptotic chi-square p-value, alternate seed, extra replicate, single-label
test, or favorable randomization realization may replace it. The historical
gate requires `p_global <= 0.05`; that condition is necessary but cannot by
itself establish predictive skill.

## Dedicated within-draw role negative control

The sole registered prediction control is `within_draw_bonus_reassignment` with
seed `649`. It preserves exactly the aspect unrelated to the hypothesis and
destroys only the observed main/bonus role association:

1. The control receives the same strict history prefix as the candidate.
2. Pre-RNG draws remain byte-for-byte/field-for-field unchanged.
3. For each historical draw on or after 2019-05-15, in chronological order,
   sort its observed seven labels ascending, initialize one
   `numpy.random.default_rng(649)` per prediction call, use exactly one
   `rng.integers(0, 7)` value to select its pseudo-bonus, and assign the other
   six labels to pseudo-main.
4. Run the identical 104-draw activation rule, counts, probability mapping,
   `run_backtest` target dates, ranking, and scoring pipeline on this transformed
   history.
5. Never transform the target outcome: the actual target six main numbers remain
   the candidate's originals, and its actual bonus remains excluded from all
   scoring.

Reinitializing from seed 649 and replaying the chronological prefix makes a
given historical draw's pseudo-role stable at every later target. The control
preserves dates, seven-number sets, marginal seven-number frequencies,
chronology, and without-replacement dependence. It changes only the historical
role label used by `predict`.

Report the control's complete aggregate and fixed-half metrics. It behaves as a
null when its aggregate raw primary `p > 0.05` or its aggregate 95% interval
includes zero. Raw `p <= 0.05` **and** an interval wholly above zero is a
pipeline warning; the same conjunction in either fixed half is also an audit
warning. Any such warning blocks activation or promotion and requires audit.
The control never supports a discovery claim and does not enter the Holm family.

## Leakage and implementation checks before scoring

Offline deterministic tests and fail-closed runner checks must prove all of the
following before the first V7 historical score exists:

1. source dates are strictly increasing and unique; every prediction receives
   the exact verified prefix before its target, with no same-date/future value;
2. counts ignore every pre-2019-05-15 draw and include the 2019-05-15 boundary;
   a hand-computed oracle verifies `m`, `b`, the seven-role Dirichlet-half
   aggregation, `u`, stable sigmoid, strict root bracket, all 256 bisection
   steps, interior final `alpha`, probabilities, and ranks;
3. 103 visible post-RNG draws produce a direct exact fair return and 104 activate
   the formula; an active all-zero-`u` input also directly returns exact `6/49`
   without invoking bisection; all 621 registered historical targets are
   retained, including fair fallback targets;
4. modifying the target main/bonus, any future suffix, or any pre-RNG draw cannot
   change the prediction, while modifying a strictly prior post-RNG role can;
5. historical bonus is consumed only when strictly prior, while target bonus
   cannot affect features, hits, ranks, Brier, log loss, or any primary total;
6. inactive, active, zero-count, extreme-count, equal-ratio, and label-tie cases
   satisfy the exact 49-label, finite, open-interval, sum-six, deterministic
   serialization, and numeric-label tie contracts;
7. a global permutation of the 49 labels is equivariant for counts,
   probabilities, and ranks subject to the registered numeric-label tie rule;
8. a synthetic oracle verifies the within-draw control's exact seed stream,
   sorted-seven choice, unchanged pre-RNG records, preserved seven-label sets,
   stable prefix replay, and unchanged target outcomes;
9. candidate and control use the same `run_backtest` folds, 621 target dates,
   metric functions, and scoring targets, and differ only in the transformed
   history supplied to prediction;
10. a hand-computed audit oracle verifies `G`, the zero-term convention, exactly
    10,000 chronological within-draw randomizations, seed 649, comparison
    operator, and plus-one denominator;
11. the runner scores no V7 development/legacy lane, enforces the two registered
    fixed halves, reports fair fallbacks, and refuses alternate dates, subsets,
    labels, or rescue metrics;
12. the runner verifies both registered data boundaries and the V6 reference
    report from committed Git blobs, requires a completely clean worktree plus
    canonical committed config, atomically acquires and permanently retains the
    canonical one-shot claim before scoring, records exact
    command/config/code/data/report/claim identities, and refuses to overwrite
    an existing claim, staging file, or historical report;
13. the research config disables live execution, contains no production or
    shadow model, and no existing file in `predictions/` or `evaluations/` is
    changed or regenerated.

Any chronology, leakage, probability, role-boundary, source-prefix, target,
control, reference, or audit failure means **Archive** with no performance
claim. It is not repaired under `v7.0.0` after any V7 answer has been inspected.

## Multiplicity and frozen historical decision

The append-only multiplicity family is `draw_role_exchangeability`; V7 is
variant 1 and the family size at registration is one. Any later alternate
transition date, minimum history, pseudo-count, role statistic, mapping, scale,
window, seed, target definition, subgroup, or main/bonus exchangeability variant
remains in this family. Failed, abandoned, invalid, and negative attempts remain
in the ledger and variants cannot be renamed into a new family after outcomes
are known.

At each formal decision, adjust all recorded family primary p-values using
Holm's step-down procedure with family-wise `alpha = 0.05`; a missing or invalid
p-value enters as `1`. With this sole registered variant, the historical
Holm-adjusted p-value equals its raw exact primary p-value. Secondary metrics,
the global audit, comparisons, and controls cannot become alternate discovery
tests.

After the implementation, config, registry, tests, and leakage checks are frozen
in a committed and pushed code state, run exactly one historical diagnostic and
publish every registered metric, half, control, audit statistic, fallback count,
comparison, exclusion, hash, warning, and command. No feature, parameter, date,
window, weight, constraint, or rule may change in response.

Historical passage requires **all** of the following:

1. aggregate 2020–2025 primary Top-12 lift is strictly positive;
2. its family Holm-adjusted exact p-value is `<= 0.05`;
3. its 95% bootstrap lower endpoint is strictly greater than zero;
4. primary lift is strictly positive in both fixed `2020–2022` and `2023–2025`
   halves;
5. aggregate and each fixed half have Brier and log-loss deltas versus fair each
   `<= 1e-9`;
6. the fixed historical global role audit has `p_global <= 0.05`;
7. the aggregate registered negative control behaves as a null and produces no
   fixed-half control warning; and
8. no leakage, source, role, reference, reproducibility, or other audit warning
   remains.

Failure of any valid performance gate means **Reject**. An invalid pipeline
means **Archive** with no performance conclusion. Even complete passage can
justify only a separate reviewed **shadow activation PR**; it is consumed
historical evidence, not confirmation, and activation is never automatic.

## Prospective cohort and fixed decision

At registration, status is `not_activated`; `freeze_commit`,
`activation_commit`, `outcomes_known_at_activation`, and `cohort_start` are all
null. V7 is absent from the live suite. Only a separate reviewed PR after a
valid historical passage may freeze and add exact `v7.0.0` as shadow, record
every outcome known at activation, and choose a strictly later cohort start.
No known, missed, late, or regenerated target may be backfilled.

Eligibility requires an immutable original `v7.0.0` shadow snapshot committed
before `00:00 America/Toronto` on its target date, exact model/version/role,
strictly prior history metadata, verified digest/first commit/generated
time/source/evaluation ancestry, and a valid evaluation of the original target's
six main numbers. The target bonus is never an eligible prediction or scoring
field.

There is one formal look at exactly **208 eligible, evaluated snapshots**.
Exclusions delay that point but cannot reduce the count. There is no early look,
optional extension, continuation, or automatic promotion. Split the ordered
cohort into exactly the first 104 and last 104 eligible evaluations.

At that single look, repeat the same frozen primary test and bootstrap on the
208 outcomes; require positive primary lift in the aggregate and both 104-draw
halves, Holm-adjusted exact primary `p <= 0.05`, aggregate bootstrap lower
endpoint `> 0`, and aggregate/half Brier and log-loss deltas each `<= 1e-9`.
Run the same registered prediction control on the same target/history evidence
and require it to behave as null without half warnings. Each control prediction
must be reproduced from the exact immutable source commit, data blob, and
strict-history digest bound to its corresponding candidate snapshot; rebuilding
controls from a later or revised final-state history is prohibited. Also compute the same
conditional 6:1 `G` statistic on exactly the 208 prospective outcomes, use a
fresh 10,000-replicate seed-649 within-draw role-randomization stream, and require
its plus-one `p_global <= 0.05`. This post-reveal audit may use the 208 realized
bonus roles solely to compute `G`; no realized target bonus may enter a
prediction, hit, rank, Brier score, log loss, or primary total. Every snapshot,
source, leakage, role, control, and audit check must be clear.

If any gate fails, reject `v7.0.0`; the cohort cannot be extended or tuned. If
all gates pass, a separate reviewed promotion PR must publish the complete
evidence and approve any role change. Any behavior change after observing a V7
historical or prospective result creates a new version and a new cohort, and
every outcome that influenced the change is consumed for that changed version.
V1 remains production and V3 remains shadow unless their own separately reviewed
evidence changes those roles.

## Source ledger

Repository authorities: [`AGENTS.md`](../../AGENTS.md),
[`MODEL_PROTOCOL.md`](../MODEL_PROTOCOL.md),
[`V2_V4_RESULTS.md`](../V2_V4_RESULTS.md),
[`RESEARCH_ROADMAP.md`](../RESEARCH_ROADMAP.md),
[`V7_mechanical_bias_basis.md`](../research/V7_mechanical_bias_basis.md),
[`V6_entropy_regime_results.md`](V6_entropy_regime_results.md),
[`backtest.py`](../../src/lotto649/backtest.py),
[`evaluation.py`](../../src/lotto649/evaluation.py),
[`optimizer.py`](../../src/lotto649/optimizer.py), and
[`research_protocol.py`](../../src/lotto649/research_protocol.py).

The external primary-source ledger and statistical rationale are frozen in the
[V7 basis note](../research/V7_mechanical_bias_basis.md). Holm's family-wise
procedure is Sture Holm, “A Simple Sequentially Rejective Multiple Test
Procedure,” *Scandinavian Journal of Statistics* 6 (1979),
[DOI 10.2307/4615733](https://doi.org/10.2307/4615733).
