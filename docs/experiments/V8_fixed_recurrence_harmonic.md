# V8 Fixed-Recurrence Harmonic Pre-registration

## Frozen identity

| Field | Value |
|---|---|
| Experiment ID | `V8_fixed_recurrence_harmonic` |
| Family / variant | `periodicity_frequency_domain` / `1` |
| Model | `v8_spectral_phase` |
| Version | `v8.0.0` |
| Status | **REGISTERED — NOT IMPLEMENTED — NOT SCORED** |
| Registration date | 2026-08-16 |
| Protocol seed | `649` |
| Live role | none; V1 stays production and V3 stays shadow |

This note freezes one narrow, low-prior periodicity hypothesis before any V8
implementation or V8 score exists. It is deliberately a falsification attempt,
not a claim that a fair lottery should be periodic. The primary-source and
mathematical basis is frozen separately in
[`V8_fixed_spectral_basis.md`](../research/V8_fixed_spectral_basis.md).

The reciprocal fair inclusion probability, `49/6` draws, is only the mean of a
broad geometric waiting-time distribution under the fair IID null. It is not a
mechanism-backed cycle. No reviewed official source identifies an 8.17-draw
oscillation. V8 tests the single frequency only because it can be chosen from
the published game combinatorics without inspecting a periodogram or historical
V8 result.

## Hypothesis and independence boundary

For each number label, the registered alternative is that its strictly prior
post-RNG main-number indicator contains a stable phase-coherent component at
the sole angular frequency

```text
p0    = 6/49
P     = 1/p0 = 49/6 draws
omega = 2*pi/P = 12*pi/49 radians per draw.
```

If that phase is stable, a one-draw extrapolation may improve the next draw's
main-number ranking and probabilities. The null is conditional exchangeability
with no stable predictive phase. Under a fair IID process, no fixed frequency,
including `12*pi/49`, is privileged in expectation.

V8 is a new `periodicity_frequency_domain` family. It shares the raw categorical
main-number indicator with earlier frequency and boosting models, but it does
not use their rolling frequencies, EMA, gaps, calendar harmonics, transition or
pair counts, entropy gates, main/bonus role counts, fitted coefficients,
constraints, ensembles, or predictions. V2/V3 contain rolling and calendar
features but no Fourier projection of each label's historical indicator. This
conceptual overlap is recorded rather than described as complete orthogonality.

## Evidence and data boundaries

The diagnostic data prefix is immutable:

- path: `data/processed/draws.csv`;
- source commit: `39b99a9e0a6351b4143f81c9a95eb1639456a35d`;
- raw SHA-256:
  `95434535857a95f3ae9bd25e42345291274804702ed514b0bace6fafcf584bdf`;
- 4,431 data rows through 2026-08-12.

At registration, outcomes were already known through 2026-08-15:

- source commit: `90177c80cfb070038d79508fb2e73305a297f516`;
- raw SHA-256:
  `edfb7f8a4a7711a630957d6f86b567e6b254caf7b1d1aaea0edf1d16a34155b3`;
- 4,432 data rows through 2026-08-15.

The registered prefix must be verified from its Git blob. The known-outcomes
blob must preserve that prefix exactly. Every scored historical history must be
the exact target-truncated prefix of that verified canonical draw sequence; an
interior missing draw, disputed row, conflict, or non-append revision is an
invalid pipeline and requires Archive. Compressing the draw index across a gap,
interpolating a row, or continuing from a convenient subset is prohibited. A
later append cannot change the V8 historical input, and no already-known 2026
outcome can be backfilled into a prospective cohort. Prospective reconstruction
must likewise use the exact prefix of the immutable source data blob bound to
each eligible snapshot.

V8 uses the externally documented RNG boundary `2019-05-15`. Earlier draws are
excluded from the V8 feature series, not merely downweighted. The sole scored
historical lane is every target from 2020-01-01 through 2025-12-31:

| Scope | Dates | Targets | Status |
|---|---|---:|---|
| Development | 1982–2014 | 0 | N/A; pre-RNG and prohibited from V8 scoring |
| Legacy/model-selection | 2015–2019 | 0 | N/A; transition/burn-in only and prohibited from V8 scoring |
| Consumed diagnostic | 2020–2025 | 621 | historical diagnostic only; never blind or confirmatory |
| Fixed half 1 | 2020–2022 | 307 | consumed stability diagnostic |
| Fixed half 2 | 2023–2025 | 314 | consumed stability diagnostic |

There are 65 post-RNG burn-in draws through 2019. With the frozen 104-prior-draw
activation rule, exactly 39 historical targets use the fair fallback and 582
are active; the first active target is 2020-05-20. All 621 targets remain in the
aggregate and fixed-half metrics. Active-only, alternate-year, alternate-start,
or best-subperiod scores are prohibited.

The frozen comparison reference is the unique V7 consumed-lane report:

- `reports/v7_main_bonus_role_bias_v7.0.0_historical.json`;
- SHA-256:
  `242018714a17a78a8b99309e4391e153c293a02121738addd2bb8f9f74d6c121`;
- permanent V7 claim:
  `reports/v7_main_bonus_role_bias_v7.0.0_historical.claim`;
- claim SHA-256:
  `1443982f9b40ba5b460632211baa17b4aff7cb9cdcd48010c0a538f141344290`.

The V7 report supplies the identical 621-target fair/random/V1/V3/V5/V6/V7
descriptive summaries. They are reused without refitting and cannot select or
rescue V8.

## Exact candidate

For target date `t`, first validate that the supplied history is strictly
ordered, has unique dates, and ends strictly before `t`. Filter it to verified
draws with `draw_date >= 2019-05-15`. Let their count be `D`, ordered by date,
and assign zero-based indices `i = 0, ..., D-1`; `i=0` is the draw on
2019-05-15. Time means consecutive draw index, never elapsed days or calendar
position.

For label `n in {1,...,49}` define

```text
x[i,n] = 1  if n is among the six main numbers of post-RNG draw i
         0  otherwise
y[i,n] = x[i,n] - 6/49.
```

Bonus numbers are excluded from every candidate feature, ranking, hit target,
Brier score, and log loss. The target main numbers and target bonus are absent
from prediction.

If `D < 104`, return the exact fair mapping `p[n] = 6/49` for all labels. If
`D >= 104`, compute with IEEE-754 binary64 `math.sin`, `math.cos`, and
`math.fsum` in ascending index order:

```text
a[n] = (2/D) * fsum(y[i,n] * cos(omega*i), i=0..D-1)
b[n] = (2/D) * fsum(y[i,n] * sin(omega*i), i=0..D-1)
theta = omega*D
s[n] = a[n]*cos(theta) + b[n]*sin(theta).
```

This is the only coefficient estimator and the only one-step phase forecast.
Because an arbitrary finite `D` need not span an integer number of cycles, the
two basis columns are not exactly orthogonal and `2/D` is a fixed Fourier
projection rather than an exact two-column least-squares inverse. That finite-
prefix boundary mixing is part of the registered statistic; orthogonalization,
demeaning beyond `6/49`, tapering, or a later estimator correction is a new
variant.

There is no frequency scan, periodogram selection, alternate sign, phase lag,
calendar time, window, taper, detrending rule, z-score, amplitude threshold,
temperature, shrinkage coefficient, clipping, fitted parameter, calibration,
constraint, or ensemble member. The window is the complete expanding post-RNG
prefix.

## Probability mapping

For `D >= 104`, map the 49 scores through one deterministic intercept. Define
the stable sigmoid

```text
sigmoid(v) = 1/(1+exp(-v))       when v >= 0
             exp(v)/(1+exp(v))  when v < 0.
```

Let `M = max_n(abs(s[n]))`, `lower = -64-M`, and `upper = 64+M`. Before
iteration, require strictly

```text
sum_n sigmoid(lower+s[n]) < 6 < sum_n sigmoid(upper+s[n]).
```

Failure is an invalid pipeline; widening, clipping, or silently using an
endpoint is prohibited. Perform exactly 256 bisection iterations. At each step,
`mid=(lower+upper)/2`; if the probability sum at `mid` is `<= 6`, replace
`lower=mid`, otherwise replace `upper=mid`. After iteration set
`alpha=(lower+upper)/2` and

```text
p[n] = sigmoid(alpha+s[n]).
```

If all 49 `s[n]` are exactly zero, return exact `6/49` without entering the
solver. Otherwise require keys exactly `1..49`, every probability finite and
strictly between zero and one, and `abs(sum(p)-6) <= 1e-12`; any failure is
invalid. There is no post-solver renormalization or cap. Rank by decreasing
probability with ascending number as the exact tie-break. Existing combination
selection may consume the ranked Top-12 for descriptive output, but final-six
hits and combination constraints are not registered V8 metrics.

## Registered negative controls

Both controls use the same target dates, eligibility, candidate formula,
probability mapping, ranking, and scoring as V8. Neither may support discovery
or enter the Holm family. Each must behave as null in the aggregate and both
fixed halves. In addition, the candidate must directly outperform the formal
row control under the paired comparison frozen below.

### 1. Strict-prefix whole-draw permutation

For every `predict(history, target_date)` call, validate and filter the same
strict post-RNG history prefix. If `D < 104`, return exact fair without drawing
randomness. Otherwise compute, for each source index `i=0,...,D-1`,

```text
key[i] = SHA256(UTF8("lotto649-v8-prefix-control-v1:649:{D}:{index}"))
```

Substitute the decimal integers `D` and `index=i` before UTF-8 encoding. Sort
source indices by the full 32-byte digest in ascending byte order and then by
integer index to break a hypothetical digest tie. This ordered index vector
is the permutation assigned to destination positions `0,...,D-1`. If and only
if it is the exact identity vector, rotate it left by one position. Destination
dates remain fixed; each selected source contributes its complete six-main-plus-
bonus outcome row. Recompute the identical V8 candidate from that permuted
prefix; the actual target draw and its date never change. No NumPy RNG or
version-dependent shuffle algorithm is used for this control.

This preserves the exact six-of-49 row constraint, within-draw dependence,
prefix label counts, and empirical complete-row distribution while destroying
their temporal phase order. It must operate inside each strict prefix; a single
permutation of the full registered dataset that can move future outcomes into
an earlier control history is prohibited.

### 2. Per-number spectral phase rotation

For each label `n`, define a fixed angle without an RNG stream:

```text
payload = UTF8("lotto649-v8-phase-control-v1:649:{number}")
u[n] = uint64_big_endian(SHA256(payload)[0:8]) / 2^64
phi[n] = 2*pi*u[n]
s_control[n] = a[n]*cos(theta+phi[n]) + b[n]*sin(theta+phi[n]).
```

Substitute the decimal integer `number=n` before UTF-8 encoding.

Use the same intercept solver and scoring. This preserves each label's fitted
amplitude while destroying the candidate's registered target phase. It acts on
coefficients rather than complete rows and therefore does **not** preserve the
cross-label six-of-49 constraint. It is a component stress control, never the
fair-lottery null or a substitute for the row permutation.

For either control and scope, `behaves_as_null` is true when its raw exact
primary `p > 0.05` **or** its 95% bootstrap interval includes zero. A control is
non-null only when raw `p <= 0.05` and the interval's lower endpoint is strictly
positive. Any non-null control creates an audit warning and fails its registered
gate; secondary metrics cannot rescue it.

For the formal row control only, align candidate and control by target date and
define one paired draw value as `candidate_top12_hits - row_control_top12_hits`.
For the aggregate and each fixed half separately, initialize a fresh
`numpy.random.default_rng(649)`, resample the aligned draw indices with
replacement exactly 10,000 times, and calculate the two-sided 95% percentile
interval for the mean paired difference using
`numpy.quantile(..., method="linear")`. The lower endpoint must be strictly
greater than zero in all three scopes. A zero-touching interval means the row
control matched the apparent advantage and fails gate 6 even if the row
control's standalone p-value is slightly above `0.05`. No unpaired resampling,
alternate confidence level, or phase-control substitution is allowed.

## Leakage and integrity tests required before scoring

Before any V8 score exists, deterministic synthetic tests must prove:

1. 103 post-RNG prior draws return exact fair; 104 enter the registered formula.
2. Unordered or duplicate dates, `target_date <= history[-1].draw_date`, a
   missing 2019-05-15 origin, any interior deletion or conflict relative to the
   target-truncated verified source blob, non-finite math, or an invalid
   probability contract fail closed.
3. Bonus changes never change candidate or control probabilities.
4. A worked literal oracle independently verifies `a`, `b`, target phase,
   stable sigmoid, strict bracket, all 256 bisections, equality-to-lower, and
   probability/rank output.
5. The dedicated config may restate only the frozen literals. Preflight and the
   factory reject any different frequency, window, phase sign, amplitude
   normalization, temperature, or selectable alternative.
6. Repeated calls are byte-for-byte deterministic; appending a future draw and
   reconstructing an old fold leaves its prediction unchanged.
7. The row control preserves every complete six-main-plus-bonus row, prefix
   marginal counts, dates, and target identity; its SHA-256 keys bind seed 649
   and `D` inside every prefix, and it never sees a target or later row.
8. Literal SHA-256 phase-control angles, fitted amplitudes, target sets, and
   candidate/control fold dates are locked independently.
9. Candidate and both controls pass through the same `run_backtest`, rank,
   `evaluate_prediction`, frame validation, exact test, bootstrap, and report
   publisher.
10. The paired candidate-minus-row-control bootstrap uses identical target
    dates and aligned draw resampling; literal synthetic values lock all three
    lower-endpoint gates and reject unpaired or reordered inputs.
11. Historical counts are exactly 621 aggregate, 307/314 halves, 39 fair
    fallback, 582 active, and first active 2020-05-20; exclusions are zero.
12. Git verifies the registered and known-outcomes data blobs, preserved prefix,
    frozen V7 reference/claim, canonical committed config, clean exact HEAD, and
    code commit before the first score.
13. `config.yaml`, `predictions/`, `evaluations/`, and workflows remain
    unchanged; the V8 research config has `live.enabled: false` and empty live
    model lists.

## Metrics and fixed comparisons

The sole primary metric is mean Top-12 main-number hits minus exact fair theory
`72/49`. For each scope, sum the draw-level Top-12 hits and compute the exact
one-sided upper-tail distribution by convolving
`Hypergeometric(N=49, K=12, n=6)` across all included draws. Normal
approximations and empirical random rankings are not the primary p-value.

For each candidate/control scope, initialize a fresh
`numpy.random.default_rng(649)`, resample complete target draws with replacement
exactly 10,000 times, and report the two-sided 95% percentile interval for mean
Top-12 lift using NumPy `quantile(..., method="linear")`. Do not resample the
six winning labels independently.

Bounded secondary metrics are Top-6 and Top-18 lift versus `36/49` and `108/49`,
Brier score, binary log loss, their deltas versus exact constant `6/49`, and
mean actual rank. Lower proper scores and rank are favorable. Proper-score gates
require every aggregate/half Brier and log-loss delta to be `<= 1e-9`.

The fixed descriptive comparison set is exact fair theory, deterministic
random, every V1 production baseline and ensemble, V3 shadow, and rejected V5,
V6, and V7. V7's frozen report is reused on identical targets; no reference is
refit. Comparisons and secondaries cannot choose another V8 variant or override
the primary gate.

## Multiplicity and historical decision

The append-only Holm family is `periodicity_frequency_domain`; V8 is variant 1,
so the family size at registration is one. Any later change to frequency,
period, regime origin, history length/window, coefficient estimator, phase,
sign, normalization, probability map, solver, control, split, metric, or gate is
another variant in this same family. Missing, invalid, archived, or selectively
unreported family p-values count as `1.0`. Family-wise alpha is `0.05`.

Only the aggregate 2020–2025 candidate exact primary p-value enters the current
historical Holm calculation. Halves, secondary metrics, and both controls do not
enter the discovery family. All are nevertheless mandatory gates.

A valid historical result is eligible for a separate reviewed shadow-activation
decision only if all eight gates pass:

1. aggregate candidate Top-12 lift is strictly positive;
2. aggregate candidate Holm-adjusted exact `p <= 0.05`;
3. aggregate candidate bootstrap lower endpoint is strictly positive;
4. candidate Top-12 lift is strictly positive in both fixed halves;
5. aggregate and both-half Brier/log-loss deltas are each `<= 1e-9`;
6. strict-prefix row-permutation control behaves as null in aggregate and
   halves, and the paired candidate-minus-row-control Top-12 interval has a
   strictly positive lower endpoint in aggregate and both halves;
7. per-number phase-rotation control behaves as null in aggregate and halves;
8. no chronology, source, reference, probability, serialization, claim, or
   audit warning exists.

If a valid run fails any gate, decide **Reject** and keep prospective status
`not_activated`. If the pipeline is invalid, leaked, cannot prove its source
boundary, produces a non-finite/contract-invalid output, or fails after claiming
the one-shot attempt, decide **Archive** with no performance claim. There is no
alternate frequency, active-only rescue, secondary rescue, or same-version
rerun.

## One-shot historical execution

No V8 historical result may be produced from the registration commit. First
implement the exact candidate, both controls, runner, CLI, synthetic tests, and
reports on a later commit without scoring. Push that implementation, require all
local checks and PR CI to pass, and require the supplied full implementation SHA
to equal a completely clean local HEAD.

After every preflight and immediately before the first candidate score, the
runner must exclusively create the permanent claim
`reports/v8_spectral_phase_v8.0.0_historical.claim`. It must refuse any existing
claim, final report, or staging path. JSON and Markdown must be fully staged in
the reports directory before sequential no-overwrite publication. A caught
partial publication is rolled back. The claim is permanent on success or
failure; a crash or any other post-claim failure consumes the attempt and
requires Archive rather than deletion and rerun.

Successful canonical outputs are exactly:

- `reports/v8_spectral_phase_v8.0.0_historical.json`;
- `reports/v8_spectral_phase_v8.0.0_historical.md`;
- the permanent claim above.

The report must record the exact command, code/config/data/reference/claim
identities, registered parameters, model versions, target dates, fallback and
active counts, complete candidate and both-control aggregate/half metrics, all
three paired candidate-minus-row-control intervals, all eight gate values,
warnings, and prospective `not_activated` state. JSON must reject NaN/Infinity.
No automatic workflow may run this diagnostic.

## Prospective cohort and stopping rule

Historical passage does not activate V8. A separate reviewed PR must freeze the
implementation commit again, verify a new append-only known-outcomes boundary,
set a cohort start strictly after every outcome known at activation, and add
exact `v8.0.0` only as shadow. V1 remains production and V3 remains shadow.

The sole formal prospective look is exactly the earliest 208 eligible,
evaluated, immutable pre-draw candidate snapshots, ordered by target date and
split into the first 104 and last 104. Missing, late, regenerated, changed,
duplicate, source-invalid, or post-draw snapshots are excluded and delay the
checkpoint. There is no early look, optional extension, continuation, or
automatic promotion.

At the 208-draw look, repeat the same exact primary test, bootstrap, family Holm
policy, bounded secondaries, fixed halves, proper-score gates, and both control
gates. Each deterministic control must be reconstructed only from the exact
immutable source commit, data blob, and strict-history digest bound to the
corresponding candidate snapshot; later or revised final-state history is
prohibited. Require the same eight gates, with aggregate and both 104-draw
halves replacing historical scopes.

Any failed gate rejects `v8.0.0`; the cohort cannot be extended or tuned. If all
gates pass, a separate reviewed promotion PR must publish the complete evidence
and approve any role change. Promotion is never automatic. Any change after
observing a historical or prospective V8 answer creates a new version and a new
prospective cohort; every outcome that influenced it is consumed for that
changed version.

## Source ledger

Repository authorities: [`AGENTS.md`](../../AGENTS.md),
[`MODEL_PROTOCOL.md`](../MODEL_PROTOCOL.md),
[`V2_V4_RESULTS.md`](../V2_V4_RESULTS.md),
[`RESEARCH_ROADMAP.md`](../RESEARCH_ROADMAP.md),
[`V8_fixed_spectral_basis.md`](../research/V8_fixed_spectral_basis.md),
[`V7_main_bonus_role_bias_results.md`](V7_main_bonus_role_bias_results.md),
[`backtest.py`](../../src/lotto649/backtest.py),
[`evaluation.py`](../../src/lotto649/evaluation.py), and
[`research_protocol.py`](../../src/lotto649/research_protocol.py).

External primary sources and their exact claim boundaries are indexed in the
[V8 basis note](../research/V8_fixed_spectral_basis.md). Those sources establish
the game rules, current RNG integrity context, and limits of spectral randomness
testing; none asserts a predictive LOTTO 6/49 harmonic.
