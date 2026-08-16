# V8 primary-source basis: fixed Fourier phase extrapolation

Date: 2026-08-16

Research status: source review and mathematical derivation only; no V8
historical outcome was scored or inspected

Registered experiment: `V8_fixed_recurrence_harmonic`; model:
`v8_spectral_phase` version `v8.0.0`

## Scope and bottom line

This note evaluates one deliberately bounded candidate family:

> **H8:** For each number label, the strictly prior binary main-draw indicator
> contains a stable phase-coherent component at the single, outcome-independent
> angular frequency `omega = 12*pi/49`; extrapolating that component by one draw
> improves future main-number probabilities or ranks over the fair `6/49`
> baseline.

The official game and draw-security material makes a fair random draw the
default explanation, not a periodic mechanism. The
[current ILC game conditions](https://corporate.bclc.com/content/dam/bclccorporate/documents/terms-and-conditions/rules-and-regulations/lotto/lotto-649-game-conditions.pdf)
specify six main numbers and one different bonus number drawn at random from
`1..49`; [WCLC's draw-security description](https://www.wclc.com/game-draw-security.htm)
says national and regional draws use stand-alone RNG draw machines whose
software is independently tested and certified for random output and whose
draws are externally witnessed. These are strong reasons to assign H8 a low
prior probability. They are not a mathematical proof that the published draw
sequence is IID, which is why a frozen diagnostic remains falsifiable.

The crucial limitation is mathematical: `49/6` is the reciprocal marginal
inclusion probability, hence the *mean waiting length* of a geometric waiting
time under an IID Bernoulli model. It is not a cycle length. A fair IID process
does not acquire a spectral line at `omega = 12*pi/49` merely because its event
probability is `6/49`.

**Recommendation:** H8 is admissible only as a one-shot, negative-expected
falsification experiment with a custom fair-LOTTO null and a fully frozen
one-step forecast. It should be rejected *before preregistration* if the claimed
rationale is that `1/p0` is a mechanism-backed physical period, if an ordinary
NIST DFT p-value is proposed, or if amplitude, phase, window, frequency,
normalization, probability mapping, or model-selection rules remain tunable.

## Official LOTTO 6/49 facts and the fair null

The [ILC LOTTO 6/49 Game Conditions, effective 2024-01-22](https://corporate.bclc.com/content/dam/bclccorporate/documents/terms-and-conditions/rules-and-regulations/lotto/lotto-649-game-conditions.pdf)
state that a Classic selection contains six numbers from `1..49` and that a
Classic Draw produces six main numbers plus one bonus number, all seven
different, at random from `1..49`. The same conditions score `6/6` using the six
main numbers, so the predictive indicator for H8 must exclude the bonus number.

For a fixed label `i` and draw `d`, define

```text
Y_i,d = 1  if i is one of the six main numbers in draw d
          0  otherwise
```

Under the fair exchangeable draw null,

```text
p0 = P(Y_i,d = 1) = 6/49
E[Y_i,d] = p0
Var(Y_i,d) = p0 * (1 - p0)
```

The `6/49` marginal follows directly by symmetry: six of the 49 labels occupy
main-number roles. Indicators for different labels in the *same* draw are not
independent: exact selection of six labels without replacement induces negative
dependence.
Therefore a negative control must preserve the six-of-49 row constraint rather
than treating all `49 * number_of_draws` cells as independent Bernoulli trials.

The current mechanism is an RNG regime. Atlantic Lottery's
[official transition notice](https://www.alc.ca/content/dam/alc/docs-en/Corp/AboutAL/Retailers/LMx2_Sellsheet_EN.PDF)
states that the 2019-05-15 LOTTO 6/49 winning numbers would be generated with
RNG software. Its [official integrity
page](https://www.alc.ca/content/alc/en/corporate/about-atlantic-lottery/integrity-and-compliance.html)
records the May 2019 replacement of mechanical ball-drop machines and says
third-party experts tested and certified the software for randomness.
[WCLC](https://www.wclc.com/game-draw-security.htm)
describes pre-draw integrity checks, independent testing and certification, and
external auditors for current draws. Consequently, pooling ball-machine and
RNG observations as one stationary spectral process would need a separate,
pre-specified justification; a current-mechanism hypothesis should use an
officially documented regime boundary fixed without reference to outcomes.

## Why `P = 49/6` is not evidence of periodicity

The proposed frequency is fixed without looking at outcomes:

```text
p0    = 6/49
P     = 1/p0 = 49/6 draws
omega = 2*pi/P = 2*pi*p0 = 12*pi/49 radians per draw
```

This protects the experiment from choosing a visually attractive periodogram
peak after the fact. It does not provide a generating mechanism.

Under an IID Bernoulli null, the waiting length `W` from one occurrence to the
next has

```text
P(W = k) = (1-p0)^(k-1) * p0,  k = 1, 2, ...
E[W]     = 1/p0 = 49/6
Var(W)   = (1-p0)/p0^2 = 2107/36
```

Thus the standard deviation is about `7.65` draws while the mean is about
`8.17` draws. The reciprocal probability describes a broad random waiting-time
distribution, not regularly spaced events.

The same point follows in the frequency domain. Let `X_i,d = Y_i,d - p0` and,
for any fixed angular frequency `w`, define the prefix coefficient

```text
Z_i,n(w) = sum[d=0..n-1] X_i,d * exp(-j*w*d)
```

If draws are IID under the fair null, then for `d != e`,
`E[X_i,d * X_i,e] = 0`. Expanding the squared modulus gives

```text
E[Z_i,n(w)]       = 0
E[|Z_i,n(w)|^2]   = n * p0 * (1-p0)
```

for every fixed `w`, including `12*pi/49`. No frequency is privileged in
expectation. Individual finite samples will still show random peaks; selecting
one after inspection would be data snooping.

NIST gives the relevant conceptual interpretation. Its
[SP 800-22 Rev. 1a](https://doi.org/10.6028/NIST.SP.800-22r1a)
describes the DFT spectral test as a detector of periodic features that would
depart from a randomness assumption. The same publication explains that an
ideal random sequence has independent future outputs and warns that apparent
departures can arise as ordinary anomalies, that no finite test suite is
complete, and that test results require careful interpretation. A spectral
detector therefore does not, by itself, establish stable phase or predictive
skill.

## Why the NIST DFT calibration cannot be copied here

NIST SP 800-22 is useful context, not an off-the-shelf null distribution for
this lottery feature:

1. Its reference bit model is the unbiased fair-coin sequence, whereas a
   fixed LOTTO label has `P(Y=1)=6/49`, not `1/2`. The publication's DFT
   procedure maps bits to `-1/+1`; applying that procedure directly to the
   sparse label indicator would leave a large non-zero mean unrelated to a
   predictive cycle. See the [SP 800-22 DFT test description](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-22.pdf),
   section 2.6.
2. NIST's DFT statistic counts peaks over many Fourier frequencies. H8 tests
   one exogenously fixed frequency and then extrapolates its phase.
   Those are different statistics and different claims.
3. [SP 800-22 section 2.6.7](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-22.pdf)
   recommends at least 1,000 bits for its spectral test. A shorter prefix must
   not inherit the NIST asymptotic reference merely by using a Fourier
   transform.
4. NIST itself says statistical testing cannot certify a generator; its
   [official publication page](https://csrc.nist.gov/pubs/sp/800/22/r1/upd1/final)
   labels tests a first step rather than a substitute for generator analysis.
   NIST's [2022 revision decision](https://csrc.nist.gov/news/2022/decision-to-revise-nist-sp-800-22-rev-1a)
   specifically calls for clarifying the suite's purpose and rejecting misuse
   for RNG assessment.

The correct null for H8 is the frozen fair six-of-49 draw process or a
pre-registered row-preserving randomization, not the published NIST DFT
threshold.

## Bounded candidate family

The research family should contain exactly one frequency and one phase
extrapolation rule. For target draw index `t`, only verified main outcomes with
indices `d < t` may enter. A suitable pre-registration should define the
centered series

```text
X_i,d = Y_i,d - 6/49
```

and estimate the two coefficients of the fixed basis

```text
cos((12*pi/49) * d)
sin((12*pi/49) * d)
```

from that strict prefix. The target score is the fitted component evaluated at
index `t`. This is equivalent to estimating amplitude and phase at one fixed
frequency and moving that fitted phase forward by exactly one draw.

This source note intentionally does not choose among raw Fourier projection,
least squares, or another algebraically specified estimator. Before any V8
score is produced, the experiment registry must freeze all of the following:

- the regime start and the zero point for draw index `d`;
- whether time means consecutive draw index or elapsed calendar time;
- the exact coefficient estimator and minimum prefix length;
- whether the fit is expanding or uses one fixed, source-justified window;
- the treatment of missing, duplicated, or disputed draws;
- the mapping from 49 raw scores to probabilities strictly in `(0,1)` whose
  expected total is six;
- any amplitude regularization, shrinkage, clipping, or fallback;
- deterministic tie-breaking and the project seed `649` where randomness is
  required;
- one primary metric, comparison set, multiplicity correction, and stopping
  and promotion gates.

None of those choices may be selected because it improves the observed
2020-2025 diagnostic interval. If they cannot be fixed on non-outcome grounds,
H8 has too many researcher degrees of freedom and should be rejected before a
backtest.

## Targeted negative control and null simulation

A targeted historical negative control should destroy alignment between
observed draw order and the fixed phase while preserving what H8 is not meant
to test:

1. Keep each observed six-number main set intact.
2. Permute complete draw rows within the strict training prefix using one
   frozen deterministic algorithm and seed policy.
3. Recompute the identical fixed-frequency estimator and one-step forecast.

This preserves the exact six-of-49 row constraint, each label's prefix count,
and all within-draw dependence, while removing label-specific temporal phase
alignment. The protocol must specify whether a fresh prefix permutation or a
single global pre-registered permutation stream is used; changing that choice
after observing results is prohibited.

A second implementation check may simulate complete rows by uniformly choosing
six labels without replacement at each draw. That is the direct fair null, but
it does not preserve empirical marginal counts. It should be labelled a null
simulation, not silently substituted for the row-permutation control.

A complementary **coefficient-phase stress control** may rotate each label's
fitted complex coefficient by a different, outcome-independent deterministic
angle before evaluating the target phase. This preserves that label's fitted
amplitude while destroying the candidate's exact phase alignment. It does not
preserve the cross-label six-of-49 row constraint because it operates on 49
coefficients rather than complete draw rows. It therefore must not replace the
strict-prefix row permutation or supply the fair-lottery null distribution. If
pre-registered, it is only an additional requirement: arbitrary rotated phases
must not appear predictive through the same scoring pipeline.

Independently circular-shifting or phase-rotating each label's binary series is
not row preserving: after separate shifts, a pseudo-draw need not contain
exactly six ones. Such a transform may be registered as a candidate-component
stress test, but it must not be described as a complete fair-LOTTO null or used
to inherit a row-permutation randomization p-value. If retained, its comparator
role and its broken row constraint must be explicit, while inferential null
calibration remains based on complete-row permutation or fair six-without-
replacement simulation.

[NIST SP 800-90B](https://doi.org/10.6028/NIST.SP.800-90B)
defines IID samples as mutually independent observations sharing one
distribution and describes permutation testing as comparing an observed
statistic with statistics from shuffled data. Its procedure is useful support
for the control principle, but H8 still needs a lottery-specific statistic and
row-level permutation because labels within a draw are not independent.

The candidate should fail if its apparent advantage is matched by the
row-permuted control, if the sign is unstable across pre-registered subperiods,
or if probability scores are worse than the constant fair baseline. The frozen
registration operationalizes the first condition as a paired, draw-resampled
candidate-minus-row-control Top-12 interval whose lower endpoint must exceed
zero in the aggregate and both fixed halves. A spectral-amplitude finding alone
must not rescue failed forward prediction.

## Leakage checks required before scoring

The implementation should prove, with deterministic tests, that:

- changing any outcome at or after target `t` leaves the prediction for `t`
  bit-for-bit unchanged;
- the coefficient fit, normalization, calibration, and control use only rows
  with draw index strictly less than `t`;
- the target draw never enters a centered series, minimum-history decision, or
  fallback decision;
- the target bonus is excluded from both the predictor and all main-number hit
  and proper-score targets;
- all 49 labels receive a valid probability and their probabilities sum to an
  expected six;
- draw ordering and the index origin are deterministic and reject duplicates,
  gaps that violate the registered policy, and conflicting rows;
- candidate and control use identical target dates, visible prefixes, scoring,
  and eligibility rules;
- the implementation records the code commit and frozen registration before
  any diagnostic output can be published.

These are necessary chronology checks. They do not turn an already observed
historical interval into new evidence.

## Evidence interpretation and prospective boundary

Under the [project's model protocol](../MODEL_PROTOCOL.md), the 2020-2025
interval is consumed diagnostic data. It may falsify the frozen V8 candidate.
A favourable result there would only justify starting a new immutable
prospective cohort; it cannot be called blind confirmation.
Any 2026+ outcome consulted while changing the estimator, frequency, window,
weights, gates, or probability map is consumed for that changed version, which
must receive a new identifier and start a new cohort.

Three claims must remain separate:

1. **Spectral detection:** a fixed-frequency coefficient is unusual under the
   registered fair null.
2. **Phase stability:** its sign and phase persist into later, untouched draws.
3. **Prediction:** probabilities committed before draws outperform `6/49` on
   the pre-registered primary metric and pass the proper-score and negative-
   control gates.

Only the third claim supports predictive use, and only prospective immutable
snapshots can provide new evidence after the historical diagnostic. Under the
[current project handoff](../CODEX_HANDOFF.md), V1 must remain the production
baseline and V3 must remain shadow unless a separate reviewed promotion
decision satisfies the documented prospective criteria.

## Pre-registration rejection audit

Reject H8 without running it if any of these statements is intended to justify
the experiment:

- “A number occurs every `49/6` draws, so it has that period.” The premise
  confuses a geometric mean waiting length with a deterministic cycle.
- “NIST's spectral test validates the forecast.” NIST's test addresses
  detection in an unbiased bit stream, not sparse six-of-49 phase prediction.
- “We will inspect the periodogram and then keep `12*pi/49` if it looks good.”
  That makes the allegedly fixed frequency outcome-selected.
- “We can try several windows, phase conventions, shrinkage strengths, or
  mappings and report the winner.” That consumes the historical interval and
  creates an unregistered multiple-comparison search.
- “Independent per-label phase rotation is a row-preserving fair-LOTTO null.”
  Separate rotations can change a pseudo-draw's number of selected labels; the
  transform is only a stress-test comparator unless paired with a valid
  complete-row inferential null.
- “A significant Fourier coefficient proves future predictability.” Detection
  does not establish phase stability or forward probability skill.

No official source reviewed here identifies an `8.17`-draw oscillatory
mechanism in the LOTTO 6/49 RNG. The sole defensible reason to retain H8 is that
the frequency is fixed from the game combinatorics before outcomes are read,
making a narrow folklore-like periodicity claim cheaply falsifiable. Its
expected scientific result remains negative.

## Primary-source index

| Primary source | What it supports |
|---|---|
| [ILC LOTTO 6/49 Game Conditions (BCLC-hosted, effective 2024-01-22)](https://corporate.bclc.com/content/dam/bclccorporate/documents/terms-and-conditions/rules-and-regulations/lotto/lotto-649-game-conditions.pdf) | Six main numbers and a distinct bonus are drawn at random from `1..49`; Classic prizes distinguish main from bonus |
| [WCLC Game & Draw Security](https://www.wclc.com/game-draw-security.htm) | Current stand-alone RNG draw machines, independent testing/certification, integrity checks, and external witnesses |
| [Atlantic Lottery 2019 transition notice](https://www.alc.ca/content/dam/alc/docs-en/Corp/AboutAL/Retailers/LMx2_Sellsheet_EN.PDF) | First LOTTO 6/49 winning numbers generated by RNG on 2019-05-15 |
| [Atlantic Lottery Integrity and Compliance](https://www.alc.ca/content/alc/en/corporate/about-atlantic-lottery/integrity-and-compliance.html) | May 2019 transition from mechanical ball machines to RNG software; third-party randomness testing |
| [NIST SP 800-22 Rev. 1a](https://doi.org/10.6028/NIST.SP.800-22r1a) | Spectral-test purpose, independent-random benchmark, statistical-test limitations, and minimum sequence recommendation |
| [NIST decision to revise SP 800-22](https://csrc.nist.gov/news/2022/decision-to-revise-nist-sp-800-22-rev-1a) | Official warning that the suite's purpose and misuse for RNG assessment need clarification |
| [NIST SP 800-90B](https://doi.org/10.6028/NIST.SP.800-90B) | IID definition and permutation-testing principle |
