# V10 primary-source basis: adjacent-pair set structure

Date: 2026-08-19

Research status: source and mathematics review only; **no V10 historical
adjacency count, prediction, or performance score was inspected or run**

Proposed slug: `v10_adjacent_pair_structure`

## Scope and freeze decision

This note considers one outcome-blind hypothesis about the six **main** numbers
in a LOTTO 6/49 Classic Draw.  For a sorted six-set
`S = {s_1 < ... < s_6}`, define

```text
A(S) = sum[j=1..5] 1[s_(j+1) = s_j + 1].
```

The fair-lottery explanation remains the default.  The current game conditions
say that six main numbers and one distinct bonus number are drawn at random from
`1..49`; the published 6/6 odds are `1 in 13,983,816`, exactly
`1 / C(49, 6)`.  OLG also says that the current ILC RNG was independently
tested and certified and that the draw process has external checks and a
parallel audit draw.  Those facts give a stable adjacency anomaly a low prior
probability; they do not make an empirical audit logically unnecessary.  See
the [current ILC game conditions published by BCLC](https://corporate.bclc.com/content/dam/bclccorporate/documents/terms-and-conditions/rules-and-regulations/lotto/lotto-649-game-conditions.pdf),
sections 4 and 10, and the
[OLG RNG description](https://www.olg.ca/en/frequently-asked-questions/lottery-games/lotto-max.html).

**Decision: FREEZE-ELIGIBLE as exactly one research-only, falsification-first
registration, but DO NOT activate it in live prediction or present it as an
improvement.**  The registration is defensible only with the single
fair-centred model and control below, frozen before any V10 score is generated.
Its first historical run, if authorized after that freeze, is consumed
diagnostic evidence.  Only immutable post-freeze snapshots could create
prospective evidence.  A joint-structure result alone cannot promote the model:
marginal proper scores and ranking must also improve prospectively.

The decision is narrower than a recommendation that consecutive numbers are
"due."  It licenses one exact probability model to test and very likely reject;
it does not license a search over gap sizes, adjacency thresholds, windows,
weights, regimes, or hard combination constraints.

## Official and statistical facts that bound the hypothesis

1. The effective ILC game conditions define a Classic Draw as six main numbers
   and one bonus number, all different and drawn at random from `1..49`.  They
   separately define a 6/6 win as matching the six main numbers and publish odds
   of `1 in 13,983,816`.  The V10 outcome is therefore the unordered six-main
   set only; the bonus must not enter `A`, fitting, hits, or scores.  See
   [BCLC/ILC LOTTO 6/49 Game Conditions](https://corporate.bclc.com/content/dam/bclccorporate/documents/terms-and-conditions/rules-and-regulations/lotto/lotto-649-game-conditions.pdf),
   sections 4, 5, and 10.

2. WCLC's current public instructions likewise say to select six numbers from
   `1..49` and publish the same 6/6 odds.  See the
   [WCLC LOTTO 6/49 game page](https://www.wclc.com/games/lotto-649.htm?channel=print).

3. OLG says the national LOTTO 6/49 draw process moved to RNG technology in May
   2019, that the ILC algorithm is proprietary, that GLI reviewed and tested
   the software, and that MNP and a geographically separate parallel draw at
   Loto-Quebec provide additional checks.  The public material does not expose
   RNG bits, scaling code, seeds, or ordered intermediate outputs, so published
   sorted sets cannot identify a physical or software cause for an anomaly.
   See the [OLG RNG FAQ](https://www.olg.ca/en/frequently-asked-questions/lottery-games/lotto-max.html).

4. A `k/N` lotto draw is sampling without replacement, not 49 independent
   Bernoulli outcomes.  NIST describes the hypergeometric distribution as the
   count law for sampling without replacement.  More specifically for lottery
   sets, Joe derives uniformity tests for `k`-tuple margins and warns that the
   ordinary independent-cell chi-square expression is not appropriate.  See
   [NIST's sampling statement](https://www.nist.gov/system/files/documents/2021/06/01/ASTM%20E2548-16%20Supplemental%20Statement.pdf),
   p. 4, and
   [Joe (1993), *Tests of uniformity for sets of lotto numbers*](https://doi.org/10.1016/0167-7152(93)90141-5).

5. Johnson and Klotz model lottery numbers as sequential sampling without
   replacement when estimating unequal label probabilities.  Coronel-Brizio et
   al. derive theoretical moments for lotto `k/N` outcomes and explicitly frame
   comparison with the hypergeometric model as statistical auditing, including
   possible RNG auditing.  These sources support a set-level null and
   complete-draw inference; they do not turn a detected departure into a
   forecast.  See
   [Johnson and Klotz (1993)](https://doi.org/10.1080/01621459.1993.10476320)
   and
   [Coronel-Brizio et al. (2008)](https://doi.org/10.1016/j.physa.2008.07.017)
   ([author preprint](https://arxiv.org/abs/0806.4595)).

## Exact fair distribution of `A`

Represent a six-set by a length-49 binary string with six ones.  If `A=a`, the
ones form `r=6-a` nonempty runs.  There are `C(5,r-1)=C(5,a)` compositions of
six ones into `r` positive run lengths.  The 43 zeroes create 44 slots in which
to place the `r` separated one-runs, giving `C(44,r)`.  Consequently the exact
number of six-sets with `A=a` is

```text
N_a = C(5, a) C(44, 6-a),               a = 0,...,5,
P_0(A=a) = N_a / C(49,6).
```

This is a direct counting identity, not an estimate from lottery history.  Its
values are:

| `a` | `N_a` | exact-fair probability (decimal) |
|---:|---:|---:|
| 0 | 7,059,052 | 0.504801550592 |
| 1 | 5,430,040 | 0.388308885071 |
| 2 | 1,357,510 | 0.097077221268 |
| 3 | 132,440 | 0.009470948416 |
| 4 | 4,730 | 0.000338248158 |
| 5 | 44 | 0.000003146494 |

The counts sum to `13,983,816`.  Two useful exact checks are

```text
E_0[A]   = 30/49 = 0.612244897959...
Var_0[A] = 2365/4802 = 0.492503123698...
P_0(A >= 1) = 0.495198449408...
```

Thus the mere appearance of a consecutive pair is not unusual: it occurs in
almost half of fair six-sets.  V10 may not use folklore such as "exclude
consecutive numbers" or choose an observed adjacency category after seeing its
frequency.

## One pre-registered hypothesis

The sole alternative is:

> Relative to the exact uniform six-set law, the complete strictly prior draw
> history contains a stable, signed exponential tilt in `A(S)`; carrying that
> unchanged tilt forward improves the probability assigned to future complete
> six-sets, and any marginal ranking consequence is stable rather than a
> historical accident.

Formally, with `Omega` the `C(49,6)` possible main-number sets, define

```text
Z(theta)       = sum[S in Omega] exp(theta A(S))
               = sum[a=0..5] N_a exp(theta a),

P_theta(S)     = exp(theta A(S)) / Z(theta).
```

`theta=0` is exactly the fair uniform distribution.  Positive `theta` favours
more adjacent pairs; negative `theta` favours fewer.  This is the unique
one-statistic exponential tilt of the fair law and avoids choosing a favoured
category after results are known.  It is an explicitly imposed model, not a
consequence of the official draw mechanism.

The alternative is stronger than "the historical histogram of `A` is odd."
It asserts that one stable tilt learned strictly before a target is useful on
that target.  A one-time goodness-of-fit rejection would establish neither
stability nor prediction.

## Unique, no-grid candidate skeleton

### Strict-prefix information set

For target date `t`, use every verified six-main draw `S_d` satisfying
`draw_date(d) < t`, in chronological order.  Let their count be `D_t`.  This is
the complete expanding prefix: no rolling window, decay, 2019 cut, weekday,
selected era, or minimum-history threshold may be chosen from outcomes.  The
target set and bonus, every same-date value, and every future draw are
prohibited.

The all-history rule deliberately assumes that any adjacency tilt survives the
documented May-2019 mechanism change.  That is a severe, falsifiable stability
assumption.  A later post-RNG-only version would be a different model and may
not be substituted after seeing V10 results.

### Fair-centred expanding estimate

Let `mu_0=30/49`.  Use exactly one fair-equivalent pseudo-observation and no
other regularization:

```text
m_t = (mu_0 + sum[d<t] A(S_d)) / (D_t + 1).
```

Define `theta_t` as the unique solution of

```text
sum[a=0..5] a N_a exp(theta_t a)
-------------------------------- = m_t.
sum[a=0..5]   N_a exp(theta_t a)
```

At an empty prefix, `m_t=mu_0` and `theta_t=0`.  For every finite prefix the
fair pseudo-observation keeps `m_t` strictly inside `(0,5)`, and the derivative
of the left side is `Var_theta(A)>0`, so the solution is finite and unique.
Equivalently, this is the posterior mode under the proper conjugate density

```text
pi_0(theta) proportional to exp(mu_0 theta - log Z(theta)),
```

whose mode is the fair point `theta=0`.  The unit prior strength, complete
prefix, exact moment equation, and numerical root algorithm must be frozen in
the experiment registration.  No alternative prior strength, temperature,
calibration coefficient, clipping threshold, or fitted ensemble weight is in
this candidate.

This is a conjugate-prior **MAP plug-in** forecast, not a Bayesian posterior
predictive distribution that integrates over `theta`.  The pre-draw joint
forecast is exactly `P_(theta_t)` at that posterior mode.

Freeze IEEE-754 binary64 arithmetic and the following solver. Store the moment
identity as integers

```text
numerator   = 49*sum_A + 30
denominator = 49*(D+1).
```

Then set `m_binary64=numerator/denominator` using CPython integer true division.
Record the two integers and this float. The ratio is exact only as an audit
identity: `Fraction`, cross-multiplied comparisons, decimal arithmetic, and
other representations are prohibited. If `49*sum_A == 30*D`, assign exact
`theta=0.0`, `logZ=math.log(13_983_816)`, every `p_i=6/49`, and joint gain
`g=0.0`. Otherwise use the strict bracket `[-64.0,+64.0]`, require
`M(lower) < m_binary64 < M(upper)`, and perform exactly 256 bisection iterations
with no early exit. Set `mid=lower+(upper-lower)/2`; if
`M(mid) < m_binary64`, replace `lower`, otherwise
replace `upper` (equality therefore takes the upper branch).  Return the final
midpoint `lower+(upper-lower)/2`.  Evaluate `M`, `Z`, and the marginals with
ascending-`a` `math.fsum` after the stable shift
`ell_a=log(N_a)+a*theta`, `ell_max=max(ell_a)`.  A failed strict bracket or
non-finite value is invalid; bracket expansion, clipping, alternate roots, and
post-hoc normalization are prohibited.  Changing this solver in a way that
changes serialized probabilities requires a new version.

The frozen synthetic oracle `D=2`, `sum_A=2` has `numerator=128`,
`denominator=147`, `m_binary64.hex()="0x1.bdd2b899406f7p-1"`, and
`theta.hex()="0x1.d4c61abbdd33cp-2"`. The fair-bypass `logZ` hex is
`0x1.07412c1f4cc68p+4` and its joint gain hex is `0x0.0p+0`.

### Marginal probabilities

For label `i`, let

```text
N_(a,i) = number of S in Omega with A(S)=a and i in S.
```

Then the required 49-label probability output is evaluated against the same
`ell_max` and `W` as the partition function, exactly as

```text
q_(a,i) = exp(log(N_(a,i)) + theta_t*a - ell_max)
p_i(t)  = math.fsum(q_(a,i) for ascending a=0..5) / W.
```

The algebraically equivalent ratio shortcut
`math.fsum((N_(a,i)/N_a)*w_a)/W` is prohibited because its binary64 rounding
differs. At synthetic `theta=-1.3`, label 1 has
`p_1.hex()="0x1.0e2c39c67edaep-3"`.

The integer table `N_(a,i)` is outcome-independent and can be generated once by
a binary-string dynamic program.  A transparent recurrence tracks prefix
length, number of ones, number of adjacent `11` edges, and the last bit; to
obtain `N_(a,i)`, force bit `i` to one.  Tests should compare the recurrence to
brute-force enumeration for small `(n,k)` oracles and assert the exact identities

```text
sum[i=1..49] N_(a,i) = 6 N_a,
sum[i=1..49] p_i(t) = 6,
0 < p_i(t) < 1,
p_i(t) = p_(50-i)(t) with exact binary64 equality.
```

The pre-registration canonicalizes the `49 x 6` table as compact UTF-8 JSON,
with labels `1..49` as rows and `a=0..5` as columns.  Its frozen SHA-256 is
`7d14a90bc388cb0e02dda77ff315a1662492c2cb44f6d5497e297354804d781b`;
rows `1`, `25`, and `49` are respectively
`[962598,617050,123410,9030,215,1]`,
`[860586,666310,168146,16646,610,6]`, and the reflection of row `1`.
These are outcome-independent integer oracles, not values estimated from draw
history.

At `theta_t=0`, every marginal is exactly `6/49`.  Reflection equality follows
from the path geometry and makes the model's limitation visible: it learns no
individual "hot number" and has at most 25 distinct marginal values.

### Ranking and final six

Rank the 49 marginals by descending `p_i`, breaking exact ties by ascending
numeric label, and use the existing top-six marginal rule for the reported final
combination.  This maximizes expected marginal hits under the candidate and
introduces no second structural search.

Do **not** add a hard adjacency count, sum band, odd/even rule, candidate-pool
search, or post-hoc joint-MAP constraint.  In particular, for the exponential
tilt any `theta>0` makes every six-consecutive set a joint mode and any
`theta<0` makes every zero-adjacency set a joint mode; choosing among those huge
tie classes would be an arbitrary label rule, not learned 6/6 skill.  Final-six
hits must be reported, including any 6/6, but the extremely rare 6/6 event is
not a statistically powered primary gate.

## What the model can and cannot identify

A stable shift in `A` can improve the joint set probability under the frozen
tilt.  It does **not** necessarily improve marginal number probabilities:

- many different joint six-set laws have the same distribution of `A`;
- a departure concentrated in particular labels or pairs violates the
  one-statistic tilt even if the aggregate `A` histogram changes;
- correlation can change while every one-number marginal remains `6/49`; and
- even under the tilt, marginal information comes only from the boundary
  geometry of the path `1-2-...-49`, not from learned label identities.

Therefore a positive joint score is an adjacency audit finding.  Predictive
number skill additionally requires prospective improvement in the 49 marginal
probabilities and ranks.  A retrospective 6/6, if one occurs, cannot override
that distinction or be called confirmatory.

## Overlap audit

### V1 production baselines

V1 long/recent frequency, EMA/gap, logistic, and their ensemble estimate
number-level marginal behavior from each label's own prior inclusion history.
V10 uses none of those label counts, gaps, windows, or coefficients.  Its only
learned quantity is the global mean of `A`, and its label differences arise
from fixed path boundaries.  It is therefore statistically distinct from V1,
although any claim of practical value must compare its marginals and ranks with
the frozen V1 suite.

### V5 pair affinity

V5 estimates all same-draw label-pair counts with fixed shrinkage and scores a
candidate against the six labels in the immediately preceding draw.  V10 does
count `48` particular same-draw edges implicitly through `A`, so the raw data
object overlaps the broad pair/co-occurrence domain.  The tested claims differ:

- V5 is a cross-draw, previous-draw-anchored conditional label-affinity model;
- V10 collapses all adjacent-label edges into one within-draw structural
  statistic and has no previous-draw anchor or pair identity; and
- V10 supplies a normalized joint six-set distribution, whereas V5 supplies
  shrunk per-label scores.

V10 must not reuse or retune V5's prior `250`, scale `0.10`, or result.  The
attempt ledger must disclose the pair-domain overlap rather than advertise V10
as wholly unrelated.  V5 pre-registered every later pair/co-occurrence attempt
in its append-only multiplicity family.  V10 therefore remains descriptive
family `structural_set_features`, but its formal `multiplicity_family` is
`v5_pair_cooccurrence` and its `variant_index` is `2`; V5 remains variant `1`.
The V10 historical decision must apply Holm correction over both attempts, and
neither a negative V5 result nor a different structural interpretation permits
resetting the family count.

### V2/V3 sum and transition features

The implemented V2/V3 feature frame contains previous-draw and rolling sums,
per-label frequency/gap features, and a transition frequency conditioned on
overlap with the preceding set.  The implemented V2 score does not use its sum
columns; V3 can use them through boosting.  Neither implemented model consumes
`structure_features()["adjacent_pairs"]`, and neither constructs a joint set
law from `A`.  V10 is therefore not a renamed sum or transition model.

There is still conceptual exposure: adjacency/consecutive numbers were listed
among the project's V2 hypotheses and `features.py` already defines the
descriptive statistic.  V10 is novel only in its exact fair-null distribution,
one-parameter joint tilt, and strict expanding prequential use.  The old
documentation exposure must remain in the multiplicity narrative.

## Targeted negative control

Use one fixed global bijection `pi` of labels `1..49`, frozen literally in the
registration before scoring.  Construct it by sorting source labels by the full
SHA-256 digest of

```text
UTF8("lotto649-v10-adjacency-control-v1:649:{source-label}")
```

with ascending source label as the impossible-digest-tie fallback, then map the
label at sorted position `j` to destination `j+1`.  The registration must print
all 49 source-to-destination pairs and assert that `pi` is neither the identity
nor the reversal `i -> 50-i`, the two automorphisms of the path.

For the control at target `t`:

1. apply the same `pi` to every six-main set in the strict prior prefix;
2. run the identical expanding estimate, joint model, marginal dynamic program,
   ranking, and final-six rule in the permuted label space; and
3. map the complete distribution back by defining
   `P_control(S)=P_permuted(pi(S))` and map marginals by
   `p_control_i=p_permuted_(pi(i))` before scoring the unchanged target set.

This preserves dates, complete draw rows, set size, every label's full temporal
history up to one global relabelling, all co-occurrence relations, and all
cross-draw dependence.  It changes only which original label pairs are treated
as neighbours on the numeric path.  It is therefore more targeted than
permuting dates or independently scrambling every row.

The control can never support discovery.  Candidate and control must use
identical eligible targets and complete target rows for paired inference.  A
predictive-looking control is an audit/multiplicity warning that blocks any
activation; it is not a reason to try another seed or bijection.

## Prequential scoring and evidence gates

The sole formal primary is the project's number-ranking estimand:

```text
mean Top-12 main-number hits - 72/49.
```

It uses the exact one-sided draw-level hypergeometric convolution, the frozen
complete-draw bootstrap interval, and the append-only Holm ledger.  This choice
was made before any V10 outcome existed.  It aligns the formal endpoint with the
actual prediction question and with the existing machine-validated experiment
registry.  Under the fair IID null, a target draw is independent of the
strictly prior, adaptively generated Top-12 set, so its conditional hit count is
still exactly `Hypergeometric(49,12,6)`.

The complete-set log-score advantage is a separate **mandatory
mechanism-support gate**, not a second selectable primary and not a rescue for
a failed Top-12 result.  For revealed target set `S_t`, computed only after its
pre-draw forecast is immutable,

```text
g_t = log P_(theta_t)(S_t) - log(1/C(49,6))
    = theta_t A(S_t) - log Z(theta_t) + log C(49,6).
```

For a non-bypass row, binary64 evaluates that expression in the written order:
multiply `theta_t*A(S_t)`, subtract `logZ(theta_t)`, and then add
`math.log(13_983_816)`. The exact-fair bypass assigns `g_t=0.0` directly.
Within each scope, targets are in ascending date order and all candidate and
control sums use `math.fsum`. Candidate-minus-control is formed per aligned
target first and those differences are then passed to `math.fsum`; aggregate
subtraction and ordinary `sum` are prohibited.

Because each `theta_t` is fixed by the earlier prefix, under the fair null

```text
E_T = exp(sum[t<=T] g_t)
```

is an exact prequential likelihood-ratio martingale/e-process.  The formal
mechanism gate therefore requires candidate `sum(g_t) >= log(20)` in the
aggregate, `sum(g_t) > 0` in each fixed half, and candidate-minus-control
`sum(g_t)` strictly positive in the aggregate and both halves.  The control's
own aggregate `sum(g_t)` must be `< log(20)`.  Ordinary IID row-bootstrap
intervals for this sequentially updated score are descriptive only and cannot
replace the e-value gate.

A successful joint gate cannot rescue the Top-12 primary; conversely a
successful Top-12 result with a failed joint gate is rejected.  Draws, not 49
label cells, are the resampling unit for the Top-12 bootstrap and all descriptive
uncertainty.  This matches Dawid's requirement that a probability forecast
precede the observation; see
[Dawid (1984), *Statistical theory: the prequential approach*](https://doi.org/10.2307/2981683).

Bounded secondary outputs should be exactly:

- 49-label Brier and binary log loss versus constant `6/49`;
- Top-6, Top-12, and Top-18 hit lift versus exact fair expectations;
- mean actual rank; and
- final-six hits, including an exact audit record for any 6/6; a historical
  6/6 is only a provisional candidate until the registered leakage audit is
  clear, while an audit failure archives that V10 attempt and cannot stop later
  newly registered research; and
- a descriptive ten-bin equal-width calibration table and ECE, with every bin
  emitted and no cell-level independence claim or rescue gate.

Before a prospective cohort starts, the registration must freeze one confidence
procedure, the multiplicity rule, exactly 208 eligible immutable snapshots split
positionally into `104 + 104`, and no interim look or extension.  Reusing the
already documented 208-draw convention avoids inventing a V10-specific horizon.
At the final look, the Top-12 primary must pass its registered corrected
significance and confidence gates.  Candidate, control, and paired joint scores
must pass the exact mechanism-support rule above; and marginal Brier/log loss
may not degrade versus fair in aggregate or either half.  Even all gates
passing permits only a separate reviewed promotion decision; it does not
displace V1 automatically.

Every historical draw through 2025 is consumed, and every 2026+ draw already
observed before the V10 freeze is consumed for V10.  A frozen one-shot historical
diagnostic may reject the candidate or describe stress behaviour, but cannot be
called blind, untouched, confirmatory, or prospective.  Any change inspired by
that diagnostic closes `v10.0.0` and begins a new version and cohort.

To prevent selecting among historical eras, the one-shot diagnostic has exactly
one scored lane: all 621 targets from `2020-01-01` through `2025-12-31`, split
only into the fixed descriptive/stability halves `2020-01-01..2022-12-31`
(307 targets) and `2023-01-01..2025-12-31` (314 targets).  Every verified draw
before a target, beginning at the dataset origin in 1982, enters its strict
expanding estimate.  The 1982--2019 targets are not scored as alternate lanes,
and known 2026 targets are excluded from this historical run.  None of these
choices may be changed after a V10 score exists.

For each pre-draw forecast, a deterministic canonical `forecast_payload` must
bind `D_t`, `sum_A` before the target, the integer moment numerator and
denominator, `m_binary64`, `theta_t`, `log Z(theta_t)`, all 49 marginals and the
control equivalents. Its SHA-256 excludes wall-clock time, so repeated calls on
the same strict prefix are byte-identical. The registered runner then appends
and file-`fsync`s a one-shot hash-chained `prediction_frozen` envelope that
binds the payload, its digest, and an RFC3339 UTC freeze timestamp before its
reveal seam may return the target main set. The timestamp is audit metadata,
never a model input, and the envelope may not be regenerated. A separate
`target_revealed_scored` event follows and is made durable before the next
target. Reconstructing those joint parameters only after the target outcome is
revealed is prohibited.

## Required leakage and integrity checks before any score

The registration and tests must prove at least the following:

1. dates are strictly increasing and unique, and every prediction receives
   exactly the verified prefix ending before its target;
2. target main numbers, target bonus, same-date fields, and every future suffix
   are absent from `m_t`, `theta_t`, `Z`, marginals, ranking, and final six;
3. changing a target or future suffix cannot change an earlier deterministic
   `forecast_payload`, while changing a strictly prior main set can;
4. bonus values never affect candidate or control predictions or scores;
5. hand oracles verify `A`, all six `N_a`, `mu_0`, `Z`, the moment root, and a
   small-`(n,k)` marginal dynamic program;
6. exact-fair and reflected inputs verify all 49 labels, open-interval
   probabilities, sum-six, reflection symmetry, and numeric tie-breaking;
7. candidate and control share target dates, history lengths, solver, scoring,
   and report code and differ only by the frozen label bijection;
8. the control bijection is literal, one-to-one, deterministic, non-path-
   preserving, and stable under prefix replay;
9. every report records experiment/version, data hash and boundary, code/config
   commit, command, seed, all attempted metrics, both fixed halves, control
   output, and excluded snapshots; and
10. no existing prediction, evaluation, or historical report is overwritten or
    regenerated, and research configuration cannot enter the live suite before
    a separate reviewed activation.

## Frozen degrees of freedom

If registered, `v10.0.0` must contain exactly:

| Item | Frozen value |
|---|---|
| Outcome | Unordered six main numbers; bonus excluded |
| Statistic | `A(S)` counts gaps exactly equal to one |
| Null counts | `N_a=C(5,a)C(44,6-a)` for `a=0..5` |
| Model | One exponential tilt `exp(theta A)` of uniform six-sets |
| History | Complete expanding verified prefix strictly before target |
| Centre/shrinkage | One fair pseudo-observation `mu_0=30/49` |
| Parameter | Unique moment root; no grid or fitted scale |
| Marginals | Exact `N_(a,i)` dynamic-program sum |
| Ranking/final | Descending marginal probability; ascending-label ties; top six |
| Sole formal primary | Mean Top-12 hit lift versus exact `72/49` |
| Mandatory mechanism gate | Candidate aggregate e-value at least 20; positive candidate half log-gains and candidate-minus-control log-gains; control aggregate e-value below 20 |
| Control | One printed seed-649 global SHA-256 label bijection |
| Prospective look | Exactly 208 eligible snapshots, fixed `104+104`, no interim look |
| Live role | None unless a later separately reviewed shadow activation occurs |

The following are prohibited rescue variants: adjacency distance `2` or larger,
cyclic adjacency `49-1`, maximum run length, selected `A` categories, observed
sum/odd-even interactions, rolling windows, post-2019 switching, learned prior
strength, temperature, calibration, ensemble weight, hard final-set constraint,
alternative control seeds, subgroup selection, or extending the cohort after a
near miss.  Each is a separate hypothesis and version if ever justified before
its own outcomes are known.

## Final interpretation

The candidate is mathematically coherent and unusually auditable: the fair null
is exact, the alternative is one-dimensional, the joint law is normalized, the
49 marginals follow without an independence fiction, and a targeted control can
preserve every label history while destroying numeric neighbourhood.  That is
enough to freeze one bounded research attempt.

It is not evidence that LOTTO 6/49 is predictable.  Official RNG testing and the
lack of a public mechanism for numeric-neighbour attraction make the expected
result negative.  More importantly, joint adjacency calibration and marginal
number prediction are different claims.  V10 should be rejected or retained as
an audit-only curiosity unless an unchanged prospective version clears both the
joint and marginal gates.  V1 remains production and V3 remains shadow throughout
this work.

## Primary-source index

| Source | Use in this note |
|---|---|
| [BCLC/ILC LOTTO 6/49 Game Conditions, effective 2024-01-22](https://corporate.bclc.com/content/dam/bclccorporate/documents/terms-and-conditions/rules-and-regulations/lotto/lotto-649-game-conditions.pdf) | Six main plus one distinct bonus drawn at random from `1..49`; 6/6 definition and odds |
| [WCLC LOTTO 6/49 game page](https://www.wclc.com/games/lotto-649.htm?channel=print) | Current six-number selection and published 6/6 odds |
| [OLG lottery RNG FAQ](https://www.olg.ca/en/frequently-asked-questions/lottery-games/lotto-max.html) | May-2019 RNG transition, proprietary ILC algorithm, GLI testing, MNP and parallel-draw checks |
| [NIST ASTM E2548 supplemental statement](https://www.nist.gov/system/files/documents/2021/06/01/ASTM%20E2548-16%20Supplemental%20Statement.pdf) | Hypergeometric sampling-without-replacement statement |
| [Johnson and Klotz (1993)](https://doi.org/10.1080/01621459.1993.10476320) | Lottery probability estimation under sequential sampling without replacement |
| [Joe (1993)](https://doi.org/10.1016/0167-7152(93)90141-5) | Set-valued lotto uniformity and invalidity of an independent-cell chi-square shortcut |
| [Coronel-Brizio et al. (2008)](https://doi.org/10.1016/j.physa.2008.07.017) | `k/N` theoretical moments and statistical-audit framing |
| [Dawid (1984)](https://doi.org/10.2307/2981683) | Sequential forecasts must precede the observations used to judge them |
