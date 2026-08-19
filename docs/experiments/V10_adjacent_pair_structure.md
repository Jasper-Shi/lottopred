# V10 Adjacent-Pair Structure Pre-registration

## Frozen identity

| Field | Value |
|---|---|
| Experiment ID | `V10_adjacent_pair_structure` |
| Descriptive family | `structural_set_features` |
| Multiplicity family / registered variant | `v5_pair_cooccurrence` / `2` |
| Candidate model | `v10_adjacent_pair_structure` |
| Targeted control model | `v10_adjacency_label_bijection_control` |
| Version | `v10.0.0` |
| Status | **REGISTERED — NOT IMPLEMENTED — NOT SCORED** |
| Registration date | 2026-08-19 |
| Protocol seed | `649` |
| Live role | none; V1 stays production and V3 stays shadow |

This document freezes one bounded, falsification-first hypothesis before any
V10 historical prediction or V10 performance score is generated. The fair,
unpredictable lottery is the default explanation. A negative result is a
complete and successful research outcome. The primary-source and mathematical
basis is recorded in the unscored
[V10 basis note](../research/V10_adjacent_pair_structure_basis.md).

V10 is not a search over consecutive-number rules. It has one statistic, one
signed parameter, one estimator, one label-bijection control, one primary
metric, and one historical diagnostic. Distances other than exactly one,
cyclic adjacency between 49 and 1, selected adjacency categories, rolling or
post-RNG windows, fitted prior strengths, temperatures, constraints,
calibration, ensembles, and alternative seeds are outside `v10.0.0`.

No result already known at registration—from 1982 through 2026-08-15—may be
described as untouched, blind, confirmatory, or prospective for V10. The model
was designed while those outcomes were available. The single frozen 2020–2025
run permitted below is a **consumed historical diagnostic** only. A result
cannot change the formula or this interpretation. A later pre-draw snapshot
could count only after the separate prospective activation specified below.

## Hypothesis and target

For a sorted six-main-number set `S = {s_1 < ... < s_6}`, define

```text
A(S) = sum[j=1..5] 1[s_(j+1) = s_j + 1].
```

The sole registered alternative is that the complete strict historical prefix
contains a stable signed exponential tilt in `A`, and that carrying the same
tilt forward improves both the probability of the next complete six-set and
its induced marginal Top-12 ranking. The null is the uniform distribution over
all `C(49,6)` unordered six-main-number sets.

The target is always the unordered set of six main numbers. Bonus numbers are
excluded from `A`, fitting, probabilities, ranks, Top-K hits, final-six hits,
proper scores, the joint score, and every decision gate. A target bonus may be
retained only as inert source provenance proving that an intact draw row was
loaded.

This hypothesis is statistically distinct from V5's previous-draw-anchored,
label-specific pair affinity, but it aggregates 48 within-draw label pairs.
Therefore V10 is conservatively entered as variant 2 of V5's append-only
`v5_pair_cooccurrence` multiplicity family. The conceptual overlap may not be
erased by renaming V10 after results are known.

## Exact fair law

If `A=a`, the six selected positions form `6-a` nonempty runs. The number of
possible six-sets is exactly

```text
N_a = C(5,a) C(44,6-a),    a = 0,...,5.
```

The complete frozen table is:

| `a` | `N_a` |
|---:|---:|
| 0 | 7,059,052 |
| 1 | 5,430,040 |
| 2 | 1,357,510 |
| 3 | 132,440 |
| 4 | 4,730 |
| 5 | 44 |

The implementation must assert that these counts sum to `13,983,816`, exactly
`C(49,6)`, and that the exact fair mean is

```text
mu_0 = E_0[A] = 30/49.
```

No observed historical adjacency frequency may replace any entry in this
table or select a favored `a`.

## Strict expanding information set

For target date `t`, use every verified draw with `draw_date < t`, ordered
strictly by date. There is no window, decay, minimum active history, mechanism
switch, weekday filter, or selected era. Let this complete prefix have `D_t`
draws and let

```text
sum_A(t) = sum[d<t] A(S_d).
```

The target, every same-date field, and every future row are prohibited. An empty
prefix is mathematically valid and returns the fair model. The registered
historical lane starts in 2020 and therefore has a nonempty prefix, but no
alternate burn-in rule may be introduced.

The estimate uses exactly one fair-equivalent pseudo-observation:

```text
m_t = (30/49 + sum_A(t)) / (D_t + 1)
    = (49*sum_A(t) + 30) / (49*(D_t+1)).
```

No other regularization, prior strength, clipping, temperature, or fitted
coefficient exists.

## Candidate joint distribution

Let `Omega` be the `C(49,6)` possible main-number sets. The candidate is the
single-parameter exponential tilt

```text
Z(theta)   = sum[a=0..5] N_a exp(theta*a)
P_theta(S) = exp(theta*A(S)) / Z(theta).
```

For each target, `theta_t` is the unique solution of

```text
M(theta_t) = m_t,

M(theta) =
  sum[a=0..5] a*N_a*exp(theta*a)
  --------------------------------.
      sum[a=0..5] N_a*exp(theta*a)
```

This is a fair-centred MAP plug-in forecast, not an integrated posterior
predictive. There is no parameter grid and no choice of sign after outcomes are
known.

### Frozen binary64 solver

All candidate and control computations use CPython IEEE-754 binary64 and the
same algorithm:

1. Store the target moment identity as integer `numerator=49*sum_A+30` and
   integer `denominator=49*(D+1)`. Then set
   `m_binary64=numerator/denominator` using CPython integer true division.
   Record all three values. The integer ratio is used only for audit and the
   exact-fair identity below; `Fraction`, cross-multiplied root comparisons,
   decimal arithmetic, or any other representation of `m` is prohibited.
2. If and only if `49*sum_A == 30*D`, bypass the root solver and return exact
   `theta=0.0` plus the constant mapping `p_i=6/49`.
3. Otherwise use the strict, fixed bracket `lower=-64.0`, `upper=64.0`.
4. Evaluate `M(lower)` and `M(upper)` and require strictly
   `M(lower) < m_binary64 < M(upper)`. A failed comparison or non-finite value is an
   invalid pipeline; expansion or clipping is prohibited.
5. Perform exactly 256 bisection iterations with no tolerance-based early exit.
   At each iteration set `mid=lower+(upper-lower)/2`. If
   `M(mid) < m_binary64`, replace `lower=mid`; otherwise replace `upper=mid`.
   **Equality therefore takes the upper branch.**
6. Return `theta=lower+(upper-lower)/2` after the 256th iteration.

Every evaluation is a stable log-sum-exp calculation. In ascending `a` order,
set

```text
ell_a   = log(N_a) + theta*a
ell_max = max[a=0..5] ell_a
w_a     = exp(ell_a - ell_max)
W       = math.fsum(w_a for a=0..5)
logZ    = ell_max + log(W)
M       = math.fsum(a*w_a for a=0..5) / W.
```

The synthetic identity `D=2`, `sum_A=2` must serialize
`numerator=128`, `denominator=147`,
`m_binary64.hex()="0x1.bdd2b899406f7p-1"`, and final
`theta.hex()="0x1.d4c61abbdd33cp-2"`. This literal distinguishes the registered
binary64 comparison from an exact-rational or cross-multiplied comparison.
At the exact-fair bypass, assign directly `theta=0.0`,
`logZ=math.log(13_983_816)` whose binary64 hex is
`0x1.07412c1f4cc68p+4`, every `p_i=6/49`, and per-target joint gain `g=0.0`
whose hex is `0x0.0p+0`; do not obtain `g` by subtractive cancellation.

The implementation may not use an unstable raw exponential sum, a different
summation order, Newton iteration, a library optimizer, early stopping,
post-hoc normalization, or a solver-dependent fallback. A behavior-changing
numeric revision requires a new version and new cohort.

## Exact marginal dynamic program

For each original label `i`, define the outcome-independent integer

```text
N_(a,i) = count{S in Omega : A(S)=a and i in S}.
```

Generate this table with a binary-string dynamic program. For each forced label
`i`, let `F_i(j,u,a,b)` count length-`j` prefixes containing `u` ones, `a`
adjacent `11` edges, and final bit `b`. Initialize only
`F_i(0,0,0,0)=1`. At position `j+1`, allow `b' in {0,1}`, except that position
`i` must have `b'=1`, and update exactly

```text
F_i(j+1, u+b', a+b*b', b') += F_i(j,u,a,b).
```

Discard states outside `u<=6` and `a<=5`. Then

```text
N_(a,i) = F_i(49,6,a,0) + F_i(49,6,a,1).
```

No lottery outcome enters this table. It may be generated once and cached only
after exact identity tests. The marginal forecast is

```text
p_i(t) =
  sum[a=0..5] N_(a,i)*exp(theta_t*a)
  -----------------------------------.
       Z(theta_t)
```

Canonicalize the complete integer table as compact UTF-8 JSON with rows in
label order `1..49`, columns in adjacency-category order `0..5`, no whitespace,
and no trailing newline. Its frozen SHA-256 is
`7d14a90bc388cb0e02dda77ff315a1662492c2cb44f6d5497e297354804d781b`.
Independent literal rows must include

```text
label 1:  [962598,617050,123410,9030,215,1]
label 25: [860586,666310,168146,16646,610,6]
label 49: [962598,617050,123410,9030,215,1].
```

These values and the digest are mathematical oracles, not fitted data. A cache
with any other bytes or integers is invalid.

Evaluate each marginal against the same `ell_max` and `W` used above, exactly
as

```text
q_(a,i)   = exp(log(N_(a,i)) + theta*a - ell_max)
numerator = math.fsum(q_(a,i) for a=0..5 in ascending a)
p_i       = numerator / W.
```

The shortcut `math.fsum((N_(a,i)/N_a)*w_a)/W` is prohibited because it rounds
differently. At synthetic `theta=-1.3`, label 1 must have
`p_1.hex()="0x1.0e2c39c67edaep-3"`. Require all of the following before a
probability can be ranked or serialized:

```text
keys(p) = {1,...,49}
0 < p_i < 1 for every i
abs(math.fsum(p_i)-6) <= 1e-12
sum[i=1..49] N_(a,i) = 6*N_a for every a
p_i = p_(50-i) under the candidate with exact binary64 equality (zero tolerance).
```

At exact fair bypass, every marginal is exactly the same binary64 `6/49`
literal. Probability repair, clipping, imputation, or renormalization is
prohibited.

Rank all 49 labels by decreasing probability and then ascending numeric label.
Top-6, Top-12, and Top-18 are prefixes of this one complete ranking. The final
six are exactly the sorted ascending labels from ranked Top-6. There is no
candidate-pool optimization, joint-MAP set, adjacency constraint, sum band, or
other combination rule.

## Frozen global label-bijection control

The sole targeted V10 control destroys numeric-path neighbourhood while
preserving dates, intact six-sets, label histories, co-occurrences, and
cross-draw ordering. For source label `i`, compute the full SHA-256 digest of

```text
UTF8("lotto649-v10-adjacency-control-v1:649:{i}")
```

after decimal substitution. Sort source labels by ascending 32-byte digest,
then by ascending source label for a hypothetical digest tie. Map the source at
sorted position `j` to destination `j+1`. This seed-649 map is frozen literally
as the following 49 source-to-destination pairs:

```text
1:3,2:11,3:2,4:14,5:41,6:45,7:22,8:39,9:1,10:40,11:31,12:37,13:29,14:12,15:30,16:6,17:7,18:19,19:46,20:15,21:27,22:26,23:42,24:28,25:13,26:21,27:20,28:36,29:18,30:4,31:5,32:32,33:17,34:8,35:9,36:10,37:35,38:43,39:47,40:16,41:48,42:34,43:23,44:24,45:44,46:25,47:33,48:38,49:49
```

The SHA-256 of exactly that UTF-8 canonical string, with no whitespace or
trailing newline, is
`c533509f258e0bb8bdd9fabac8a017ee689e07af0f1d6daf4d36ee63873c0562`.
The implementation must verify the generated map, literal map, canonical
string, and digest; verify that the values are exactly `1..49`; and verify that
the map is neither the identity nor the reversal `i -> 50-i`. Fixed points do
not invalidate the control; selecting another seed or map is prohibited.

For each target:

1. transform every strictly prior main set with this same global `pi`;
2. fit the identical full-prefix pseudo-observation and root solver in the
   permuted label space;
3. generate the identical DP marginals in that space; and
4. map back by `p_control_i = p_permuted_(pi(i))` before ranking and scoring the
   unchanged original target.

Equivalently, `P_control(S)=P_permuted(pi(S))`. Its revealed-target joint
advantage uses `A(pi(S_t))`. Candidate and control use identical target dates,
prefix lengths, target rows, arithmetic, output contracts, and scoring code and
differ only by the frozen bijection. The control can never support discovery or
select a rescue variant.

This targeted control is frozen under the registry `parameters` mapping. The
generic `negative_controls` list contains only the already-supported
target-date fair-random control because adding a new enum to
`research_protocol.py` would alter the separately frozen V3 prospective
implementation. The V10 runner must require both locations exactly; this
administrative split does not make the label-bijection control optional.

## Target-date fair-random control

Also record the existing `random v1.0.0` model on exactly the same target dates.
For target date `t`, it initializes
`numpy.random.default_rng(649000000 + t.toordinal())`, draws one
`Uniform(-1e-9,1e-9)` jitter for each ascending label, adds it to `6/49`, and
uses the existing expected-sum-six normalization. The target-date seed is
outcome independent. This control never enters V10 fitting, never enters the
Holm family, and can never support a claim.

## Evidence boundary and the only historical lane

The immutable known-outcomes boundary at registration is:

- path: `data/processed/draws.csv`;
- source commit: `90177c80cfb070038d79508fb2e73305a297f516`;
- raw SHA-256:
  `edfb7f8a4a7711a630957d6f86b567e6b254caf7b1d1aaea0edf1d16a34155b3`;
- 4,432 data rows through 2026-08-15.

The runner must recover and verify this exact Git blob, verify that the working
dataset preserves the registered historical target sequence exactly, and fail
closed on any missing, duplicate, reordered, conflicting, or interior-revised
row. Appends after the boundary cannot change the historical one-shot input.

The sole scored historical lane is:

| Scope | Dates | Targets | Interpretation |
|---|---|---:|---|
| Training prefix only | inception through 2019-12-31 | 0 scored | strictly prior expanding history |
| Aggregate diagnostic | 2020-01-01 through 2025-12-31 | 621 | consumed historical diagnostic |
| Fixed half 1 | 2020-01-01 through 2022-12-31 | 307 | mandatory stability diagnostic |
| Fixed half 2 | 2023-01-01 through 2025-12-31 | 314 | mandatory stability diagnostic |
| Known 2026 outcomes | through 2026-08-15 | 0 scored | consumed and excluded |

Every one of the 621 targets is included. Later targets use only earlier draws,
including earlier targets once their dates are strictly prior. There is no
development score, legacy score, pre/post-RNG score, active-only score,
alternate-year score, subgroup search, or best-period rescue. Years and
predeclared descriptive regime labels may be tabulated only as diagnostics and
may not enter any decision gate or replace the fixed scopes.

## Prequential outputs and permanent record

For each model and each target, prediction construction must complete before
the target outcome is passed to evaluation. The canonical JSON must preserve,
for candidate, targeted control, and fair-random control:

- target date, history count, history-through date, and strict-prefix digest;
- `prediction_frozen_at_utc` as an RFC3339 UTC `Z` timestamp in the one-shot
  ledger-event envelope only as audit metadata and never as a model input;
- model/version, seed, feature identity, `sum_A`, `m`, `theta`, and `logZ` where
  applicable;
- all 49 probabilities keyed by integer label and the complete 49-label rank;
- ranked Top-6, Top-12, Top-18, and sorted final six;
- after reveal only: the six actual main numbers, hits at each Top-K and final
  six, all six actual ranks, Brier score, binary log loss, and joint log
  advantages where applicable; and
- a draw-by-draw progressive record entry containing the previous maximum
  final-six hits, current hits, new maximum, whether a new record occurred, and
  the exact prediction/actual pair.

Aggregate and both fixed-half output must include exact final-six hit counts for
every bin `0,1,2,3,4,5,6`, the ordered record-event ledger, Top-6/12/18 means and
lifts, mean actual rank, Brier/log loss, per-year diagnostics, excluded rows,
warnings, and every registered gate. Zero-count hit bins must be emitted as
explicit zeroes. An observed 6/6 must be preserved with its full fold evidence
and trigger the repository's historical-candidate leakage audit, but it cannot
override the consumed-diagnostic label, multiplicity, or failed formal gates.

Calibration is a required descriptive output. Pool the draw-label cells only
for this display into ten fixed equal-width probability bins
`[j/10,(j+1)/10)` for `j=0..8` and `[0.9,1.0]` for the last bin. Emit every bin,
including empty bins, with cell count, mean forecast, observed main-inclusion
rate, and the cell-count-weighted expected calibration error. Report it for the
aggregate and fixed halves. It creates no extra p-value or decision gate because
the 49 labels within a draw are dependent. Performance by year is descriptive;
the two registered halves are the only allowed regime summary.

## Sole primary and Top-12 inference

The sole formal primary is

```text
mean Top-12 main-number hits - 72/49.
```

For every registered scope, sum the draw-level Top-12 hits and calculate the
exact one-sided upper-tail probability by integer convolution of
`Hypergeometric(N=49,K=12,n=6)` over all complete target draws. Under the fair
null, the target is independent of a strict-prefix adaptive Top-12 set, so this
conditional law remains exact. A normal approximation or one finite random
ranking is not the primary test.

For each model and scope, initialize a fresh
`numpy.random.default_rng(649)`, resample complete aligned target-draw indices
with replacement exactly 10,000 times, and compute the two-sided 95th-percentile
interval for mean Top-12 lift with
`numpy.quantile(..., method="linear")`. Labels within a draw may not be
resampled. For candidate-minus-targeted-control Top-12 comparisons, form the
aligned per-draw hit differences first and apply the identical fresh-seed row
bootstrap. Reordering, unpaired resampling, alternate seeds, extra replicates,
or alternate intervals are prohibited.

Only the aggregate candidate exact p-value enters Holm. The append-only
`v5_pair_cooccurrence` family contains V5 variant 1 and V10 variant 2. Use the
already published V5 aggregate 2020–2025 primary p-value from
`reports/v5_pair_affinity_v5.0.0_historical.json`, whose SHA-256 is
`b86391ada265d96f94e789f4962812d32771385702e2efa2285cb9ef96d5d6bb`,
and the V10 aggregate p-value. Apply Holm step-down family-wise control at
`alpha=0.05`. A missing, invalid, archived, or selectively unreported variant
enters as `p=1.0`. Halves, controls, proper scores, joint scores, ranks, hit
records, and descriptive comparisons never become alternate primaries.

## Mandatory non-primary joint mechanism gate

For revealed target main set `S_t`, calculate only after its forecast is frozen:

```text
g_candidate(t)
  = log P_(theta_t)(S_t) - log(1/C(49,6))
  = theta_t*A(S_t) - logZ(theta_t) + log C(49,6).
```

Calculate each non-bypass value in this exact binary64 operation order: first
`theta_t*A(S_t)`, then subtract `logZ(theta_t)`, then add
`math.log(13_983_816)`. Define `g_control(t)` identically from the control
parameter and `A(pi(S_t))`, and
`delta_g(t)=g_candidate(t)-g_control(t)`. These are complete-set prequential
log-likelihood advantages, not 49 independent label scores.

Within each registered scope, traverse targets in ascending target-date order
and aggregate candidate and control values separately with `math.fsum`. Form
each aligned `delta_g(t)` first and then apply `math.fsum` to those per-target
differences. Python `sum`, aggregate subtraction, or a different order is
prohibited.

The joint mechanism gate is a mandatory conjunction, never a second primary
and never a rescue for failed Top-12 evidence:

1. aggregate `sum(g_candidate) >= log(20)`, with the frozen binary64 threshold
   `2.995732273553991`;
2. `sum(g_candidate) > 0` separately in both fixed halves;
3. `sum(delta_g) > 0` in the aggregate and separately in both fixed halves; and
4. aggregate `sum(g_control) < log(20)`.

Both fixed-half control sums are still reported, but have no separate threshold
and cannot replace the aggregate gate. No IID bootstrap interval or p-value is
calculated for a joint gate. The thresholds apply to the deterministic
prequential sums exactly as stated. A positive joint result establishes, at
most, support for this normalized adjacency law; it is not marginal
number-prediction skill.

## Proper scores, comparisons, and controls

Bounded secondary metrics are Top-6 and Top-18 lift versus exact expectations
`36/49` and `108/49`, mean actual rank, final-six hits, 49-label Brier score,
and 49-label binary log loss. For the candidate, Brier and log-loss deltas
versus the exact constant `6/49` baseline must each be `<=1e-9` in the aggregate
and both fixed halves.

The frozen descriptive comparison set is exact fair theory; deterministic
random; every V1 production model (`long_frequency`, `recent_frequency`,
`ema_gap`, `logistic`, and `ensemble`, all `v1.0.0`); V3 shadow; and rejected
V5–V8. Reuse the identical-target summaries from
`reports/v8_spectral_phase_v8.0.0_historical.json`, SHA-256
`e9b51a5316811cbde2b06c36bb61ffffd04b283a4c886cb9ac213bb8fb7deed5`,
with permanent claim SHA-256
`6598a2f38462fe6274b9dfa6b6b8c51e6af367b551fd861ef8a582000d60c76d`.
Do not refit, reweight, or select a comparator. The formal operational comparison
requires the candidate's aggregate Top-12 mean to be strictly greater than the
frozen V1 ensemble mean; other comparisons remain descriptive.

The targeted label-bijection control and target-date random control must each
behave as null in the aggregate and both fixed halves. For each scope, a control
behaves as null when its raw exact Top-12 `p > 0.05` **or** its 95% bootstrap
interval includes zero. It is non-null only when `p <= 0.05` and the interval
lower endpoint is strictly positive. Any non-null scope is an audit warning.

In addition, the paired candidate-minus-targeted-control Top-12 bootstrap lower
endpoint must be strictly greater than zero in the aggregate and both fixed
halves. A zero-touching interval fails. Neither control enters Holm or supports
discovery.

## Leakage and implementation checks required before scoring

Deterministic offline tests and fail-closed runner checks must establish all of
the following before the one-shot claim is acquired:

1. dates are strictly increasing and unique, and each fold receives exactly the
   verified target-truncated prefix with every date strictly before target;
2. target main/bonus fields, same-date data, and future suffixes cannot affect
   candidate or control predictions, while a changed prior main set can;
3. bonus changes at any date cannot affect either model or any score;
4. hand oracles verify `A`, all six `N_a`, `mu_0`, exact ratio construction,
   fair bypass, stable `logZ`, the strict bracket, all 256 bisections,
   equality-to-upper behavior, and final midpoint;
5. brute-force small-`(n,k)` oracles verify the DP recurrence, forced-label
   counts, marginal identities, reflection, fair marginals, all 49 keys,
   open-interval bounds, sum six, ties, rank, and sorted final six;
6. literal tests lock all 49 bijection pairs, the payload, digest byte order,
   tie rule, canonical string SHA, non-automorphism checks, forward/back maps,
   intact rows, stable prefix replay, and unchanged targets;
7. candidate and targeted control traverse identical folds and code paths and
   differ only by the map; target-date random uses the frozen ordinal seed;
8. a future append or target mutation leaves every earlier deterministic
   `forecast_payload` byte-for-byte unchanged; repeated forecast calls are
   deterministic, while the timestamped ledger envelope is created once only;
9. exact Top-12 convolution, 10,000-row bootstrap, linear quantiles, Holm with
   V5, proper-score deltas, joint sums, every comparison operator, and all
   aggregate/half gates have independent literal oracles;
10. exactly 621 target dates and fixed 307/314 halves are present, 2026 has zero
    targets, every `0..6` hit bin is emitted, and full probabilities/ranks plus
    the progressive record ledger are complete;
11. Git verifies the registered dataset blob, V5 multiplicity report, V8
    comparison report and claim, canonical committed config, clean exact HEAD,
    and a frozen implementation commit before any target result is scored; and
12. `config.yaml`, workflows, `predictions/`, `evaluations/`, and existing
    reports remain unchanged; the dedicated config disables live and
    notifications and lists only candidate, targeted control, and random.

Any chronology, source, solver, probability, mapping, comparison, metric,
serialization, or audit failure is **Archive** with no performance claim. It is
not repaired and rerun as `v10.0.0` after the permanent claim exists.

## Frozen historical decision

After the registration, exact implementation, registry entry, tests, and runner
are committed and pushed, and local plus CI checks pass from a clean exact HEAD,
the runner may execute exactly one 2020–2025 historical diagnostic. A valid run
passes only if every condition below is true:

1. aggregate candidate Top-12 lift is strictly positive;
2. aggregate candidate Holm-adjusted exact p-value is `<=0.05`;
3. aggregate candidate Top-12 bootstrap lower endpoint is strictly positive;
4. candidate Top-12 lift is strictly positive in both fixed halves;
5. candidate-minus-targeted-control paired Top-12 bootstrap lower endpoint is
   strictly positive in the aggregate and both halves;
6. candidate Brier and log-loss deltas versus fair are each `<=1e-9` in the
   aggregate and both halves;
7. candidate aggregate Top-12 mean is strictly above frozen V1 ensemble;
8. both targeted and random controls behave as null in the aggregate and both
   halves;
9. all four joint-mechanism conditions above pass; and
10. no chronology, leakage, source, reference, probability, claim, publication,
    serialization, or other audit warning exists.

A valid failure of any scientific gate is **Reject** and leaves V10
`not_activated`. An integrity or audit failure is **Archive**. Even passage of
all ten conditions means only `eligible_for_separate_reviewed_shadow_decision`;
it does not activate V10, replace V1, or change V3's shadow role. There is no
secondary rescue, best-half rescue, near-miss extension, or same-version rerun.

## One-shot claim, attempt ledger, and publication

No automatic workflow may run the historical diagnostic. Immediately before
the first operation that can score or aggregate a V10 target, the runner must
exclusively create the permanent claim. It must refuse any existing claim,
attempt ledger, final report, staging file, or partial publication. The fixed
artifact paths are:

```text
reports/v10_adjacent_pair_structure_v10.0.0_historical.claim
reports/v10_adjacent_pair_structure_v10.0.0_historical.ledger.jsonl
reports/v10_adjacent_pair_structure_v10.0.0_historical.json
reports/v10_adjacent_pair_structure_v10.0.0_historical.md
```

The claim records experiment/version, start time, exact command, code/config
commit and hashes, data/reference identities, and seed. The JSON-lines ledger is
append-only and begins with ordered `claimed`, `preflight_passed`, and
`scoring_started` events. For each target it then records exactly
`prediction_frozen` followed by `target_revealed_scored`. The former contains
the target and prefix identity plus complete candidate, targeted-control, and
random forecasts: `D`, `sum_A`, `m`, `theta`, `logZ`, all 49 probabilities,
full ranking, and Top-K/final-six outputs. Those deterministic fields form a
canonical `forecast_payload` and `forecast_sha256`; the wall-clock timestamp is
excluded from that payload and appears only in the surrounding one-shot event.
The event binds payload, digest, and timestamp under its own hash. It is
appended, flushed, and file-`fsync`ed before the runner may retrieve or pass
that target's actual main numbers to any scoring function.
Only afterward may `target_revealed_scored` append the actual set, ranks, hits,
proper scores, and joint gains; that event is likewise flushed and `fsync`ed
before the next target begins.

The claim also binds CPython `3.12`, `requirements-live.lock` SHA-256
`2fea4cf73cc2578b73c21e6600e31ad843bd903e8a2656b7a2543164ab8d801c`,
the platform, and every installed distribution/version. The report repeats the
complete runtime manifest. A runtime mismatch fails before claim acquisition;
the timestamp and environment fields may never enter probabilities or ranking.

After all 621 target pairs, the ledger records `scoring_completed`,
`publication_started`, and `published`, or a terminal `failed` event. Every
line has a contiguous zero-based sequence number and a SHA-256 hash of its
canonical JSON plus the preceding event hash. Missing, reordered, duplicate,
noncanonical, or hash-broken events invalidate the run. Repeated forecast calls
with the same strict prefix must produce byte-identical `forecast_payload`
bytes, while a `prediction_frozen` envelope is created only once and is never
regenerated with a new timestamp. The ledger is retained on success and
failure. Merely reconstructing predictions in the final report after actuals
were available does not satisfy this protocol.

## Breakthrough handling

After each durable `target_revealed_scored` event and before any next target,
the runner durably records whether final-six hits set a new V10 within-run
maximum and whether Top-12 or final-six contains all six main numbers. A new
within-run maximum of at least 2/6 triggers an immediate Chinese progress alert,
explicitly labeled as within-run rather than a global record until the
cross-version ledger has been audited. A Top-12 6/6 triggers the registered
immediate alert even when final-six is below 6/6. If the completed durable
report passes every scientific gate, dispatch the separate statistically
significant-improvement alert; that message may not precede report publication.

If final-six is exactly 6/6, append and `fsync` a
`historical_6of6_candidate_detected` event and stop the scoring state machine
before forecasting another target. This is a provisional candidate stop and
may occur after any positive number of scored targets; it is not a successful
result until the mandatory audit is clear. Preserve the model under status
`historical-6of6-candidate`. Immediately run the registered chronology,
target, future, preprocessing, feature-selection, and model-selection leakage
audit without retraining or changing a parameter, and durably record both its
result and any audit failure. Then create the fixed bundle template
`reports/historical-6of6-candidate__{target_date}__v10.0.0.json` containing the
source and implementation commit, model/features/parameters, target and cutoff,
complete probabilities/ranking/snapshot, actual set, seed, runtime manifest,
claim/ledger hashes, and the completed leakage-audit record. Stage and `fsync`
that bundle and publish it exclusively without overwrite. Only a clear audit
may append the terminal success event
`historical_6of6_candidate_published` and dispatch the existing repository
email workflow with the required Chinese 6/6 success alert. Its title is
exactly `🚨 [LOTTO649] 历史严格回测成功预测 6/6`; its body includes the
prediction, actual set, target, model/version, cutoff, leakage-audit result, Git
commit, complete benchmark, and why chronology qualifies as simulated OOS.
Email failure is a visible warning but cannot delete, weaken, rerun, or continue
past the durable evidence. No aggregate gate may be used to erase a valid 6/6
record, although the consumed historical label still applies. Only this
audit-clear branch stops the repository's broader autonomous model search.

If that audit is not clear, the bundle is still published as preserved Archive
evidence, but the terminal event is instead
`historical_6of6_candidate_archived_leakage_failed`. The required Chinese alert
title is `⚠️ [LOTTO649] 历史 6/6 候选泄漏审计失败`; it must state that the hit is
invalid evidence. The success event and success email are prohibited, and the
V10 run cannot continue or be rerun. The invalid candidate does not satisfy the
research goal and therefore does not stop later, newly registered model
research.

The only normal success state is `published` after exactly 621 scored targets.
The only early success state is `historical_6of6_candidate_published`; it skips
the normal aggregate report because scoring was deliberately stopped. The
failure terminals are `failed` and
`historical_6of6_candidate_archived_leakage_failed`. An early 6/6 path may not
fabricate 621-row gates, resume later targets, or overwrite an existing
candidate bundle.

JSON and Markdown are fully written to unique same-directory staging paths,
fsynced, and then published without overwrite. A caught partial publication is
rolled back only when both finals can be proven absent; otherwise all evidence
is retained for Archive review. The claim and ledger are permanent under every
post-claim outcome. A crash, exception, invalid metric, or publication failure
after claim acquisition consumes the only attempt and cannot be erased to
rerun. Final JSON rejects NaN and Infinity and records every required output,
gate, warning, exclusion, digest, and artifact hash.

## Prospective cohort (registered but not activated)

V10 has no prospective start, freeze commit, activation commit, live model, or
eligible snapshot. Historical passage cannot fill those fields. Only a later,
separately reviewed PR may freeze the unchanged implementation again, verify a
new known-outcomes boundary, set a cohort start strictly after every result then
known, and add exact `v10.0.0` as shadow. V1 remains production and V3 remains
shadow.

If activated, the sole formal look is exactly the earliest 208 eligible,
evaluated, immutable pre-draw V10 snapshots, ordered by target date and split
positionally into the first 104 and second 104. A snapshot must be original,
committed before the target's Toronto calendar date, bind an exact verified
strict-history source blob, use the exact model/version/role, and have a matching
evaluation. Missing, late, regenerated, duplicate, changed, or integrity-failed
snapshots are excluded and delay the look. There is no interim look, optional
extension, backfill, or automatic promotion.

At 208, apply the same Top-12 exact test, Holm family, row bootstrap, proper
scores, targeted and random controls, joint sums, V1 ensemble operational
comparison, and ten-part conjunction, with aggregate 208 and positional 104/104
scopes. Controls must be reconstructed solely from each snapshot's bound strict
history. A failed gate rejects `v10.0.0`; all gates passing permits only a
separate reviewed promotion decision. Any behavior change after any historical
or prospective result starts a new version and a new cohort, and every outcome
that influenced the change is consumed for it.

## Source ledger

Repository authorities: [`AGENTS.md`](../../AGENTS.md),
[`MODEL_PROTOCOL.md`](../MODEL_PROTOCOL.md),
[`V2_V4_RESULTS.md`](../V2_V4_RESULTS.md),
[`RESEARCH_ROADMAP.md`](../RESEARCH_ROADMAP.md),
[`V10_adjacent_pair_structure_basis.md`](../research/V10_adjacent_pair_structure_basis.md),
[`V5_pair_affinity.md`](V5_pair_affinity.md),
[`V8_fixed_recurrence_harmonic.md`](V8_fixed_recurrence_harmonic.md),
[`backtest.py`](../../src/lotto649/backtest.py),
[`evaluation.py`](../../src/lotto649/evaluation.py), and
[`research_protocol.py`](../../src/lotto649/research_protocol.py).

External primary sources and their bounded uses are indexed in the V10 basis
note. They establish official game rules, RNG-integrity context, exact
sampling-without-replacement framing, and prequential scoring principles. None
claims that adjacency predicts LOTTO 6/49.
