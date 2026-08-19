# V5+ Research Roadmap

## Objective

Develop one falsifiable hypothesis at a time while protecting the true forward
experiment. The goal is evidence about predictability, not a sequence of models
that look better on already-observed draws.

V5+ begins with a hard fact: every historical result through 2025 has already
been available to the research process. The 2020–2025 interval was the frozen
V2–V4 blind test and is now consumed. It remains useful for diagnostics, but it
cannot become untouched confirmation for a revised model.

## Evidence lanes

Keep these lanes separate in code, reports, and claims:

| Lane | Data | Allowed use | Claim allowed |
|---|---|---|---|
| Historical development | 1982–2014 | Feature construction, fitting choices, nested chronological tuning | Development result only |
| Historical legacy validation | 2015–2019 | Stability and sensitivity diagnostics | Historical validation, already exposed to model selection |
| Consumed blind diagnostic | 2020–2025 | Frozen-candidate stress test and failure analysis | Historical diagnostic only; never untouched/blind for V5+ |
| Prospective forward | 2026+ after a candidate's freeze commit | Immutable pre-draw prediction and later scoring | Confirmatory evidence for that exact frozen version |

Forward evidence is model-specific. A 2026 result observed before V5 is frozen is
historical input for V5, not V5 forward evidence. If a V5 outcome causes any
behavioral change, V5 is closed; freeze V5.1/V6 and start a new cohort.

## Research loop

### 1. Register one hypothesis

Before implementation, add an experiment note such as
`docs/experiments/V5_<feature-family>.md` containing:

- causal/statistical rationale;
- exact feature definitions and information availability time;
- model class, training window, regularization, and seed;
- one primary metric and bounded secondary metrics;
- fair/V1 comparisons and negative controls;
- historical partitions and all tuning degrees of freedom;
- multiple-testing family and correction method;
- minimum prospective sample, stopping rule, and promotion/rejection gate.

The registration is complete only when another person could implement the same
test without choosing values after seeing its score.

### 2. Build leakage checks before feature evaluation

For target draw `t`, assert that every input, fitted transform, calibration step,
training label, and ensemble member depends only on draws before `t`. Add a
shuffled-label or date-permuted control through the same pipeline. A control that
appears predictive is a pipeline warning, not a discovery.

### 3. Develop chronologically

Use expanding or rolling walk-forward evaluation within 1982–2014. Hyperparameter
selection must be nested inside earlier chronological blocks; random train/test
splits are invalid. Prefer a small, interpretable parameter grid fixed in the
experiment note.

### 4. Run labeled historical diagnostics

After the candidate is frozen on development data, inspect 2015–2019 for legacy
stability and 2020–2025 as a consumed stress test. Report all defined metrics,
years/eras, attempted variants, and negative controls. A strong 2020–2025 result
may justify a prospective shadow test, but it is not confirmation.

### 5. Freeze a version

Commit the exact code, config, experiment note, tests, and historical report.
Assign a new version whenever feature definitions, windows, weights, constraints,
training rules, or calibration change. Do not reuse a filename/version for changed
statistical behavior.

### 6. Start a prospective shadow cohort

Add the candidate to the live suite only through a reviewed PR that labels it
`shadow`. The first eligible observation is a snapshot committed before its target
draw. Missing, late, regenerated, or integrity-failed snapshots are excluded by
the pre-registered rule, not repaired after results are known.

### 7. Decide without tuning the cohort

At the registered checkpoint, promote, continue unchanged, or reject. Publish the
decision and full comparison set. A change inspired by the cohort begins a new
model version and a new prospective counter.

## Candidate feature families

Each row is a separate hypothesis family for multiple-testing purposes. Start
with simple, shrunk statistics; do not combine families until each has an
independent record.

| Family | Candidate measurements | Principal risk/control |
|---|---|---|
| Sum dynamics | Lagged draw sum, rolling level/slope/variance, residual or mean-reversion state mapped to number inclusion | V2 already used sum features; V5 must state what is genuinely new and compare against frozen V2 |
| Pair/co-occurrence | Shrunk pair counts, recency-weighted graph degree, conditional partner scores | 1,176 pairs create a severe multiple-testing burden; require shrinkage and permuted-draw controls |
| Transition/Markov | Prior-draw-to-next-number transitions, multi-lag transition decay, state-conditional inclusion | V2 already used a shrunk previous-draw transition feature; avoid relabeling the same hypothesis |
| Entropy/regime | Rolling inclusion entropy, dispersion, drift/change-point indicators, calibration sharpness | Regime boundaries must be learned from prior data only; change-point hindsight leaks |
| Draw-role exchangeability | Post-RNG, strictly lagged main-versus-bonus conditional role odds | Mechanism boundary must be externally justified; preserve seven-number sets and randomize only within-draw roles |
| Periodicity/frequency domain | Pre-specified spectral power or phase from each number's binary history | Many frequencies invite p-hacking; choose bands before validation and compare to phase-randomized controls |
| Structural set features | Odd/even, high/low, range, adjacency, repeats, sorted gaps, sum-bin probabilities | These describe combinations, not near-hits; score exact probabilistic consequences and avoid folklore constraints |
| Calendar effects | Weekday/month interactions with strong hierarchical shrinkage | V2 already tested weak calendar signals; control for schedule/format changes and multiple categories |
| Calibration/regularization | Stronger shrinkage toward `6/49`, isotonic/logistic calibration fitted within prior history, rank-to-probability mapping | Must improve proper scores prospectively; calibration cannot use the target or full test block |

Recommended order:

1. build the experiment registry, negative-control harness, and cohort accounting;
2. test one narrow pair/co-occurrence or entropy hypothesis independently;
3. test a pre-specified periodicity hypothesis only after spectral null controls
   exist;
4. consider a compact ensemble only after multiple distinct families show stable
   standalone evidence.

## Active experiment registry

The structured registry is [`docs/experiments/registry.yaml`](experiments/registry.yaml).
It is the attempt ledger for V5+ and is validated by
`src/lotto649/research_protocol.py`. A registration records an attempt before
any candidate score is inspected; later negative, invalid, and positive outcomes
must remain in the ledger rather than being deleted.

| ID | Family | Version | Status | Historical result | Prospective cohort |
|---|---|---|---|---|---|
| [`V3_frozen_shadow_cohort`](experiments/V3_frozen_shadow_cohort.md) | Frozen boosting prospective replication | `v3.0.0` | Registered; not activated | Existing V2--V4 evidence is consumed; no new historical scoring permitted | Fixed 208 eligible draws (104 + 104); awaits separate F/A/R release sequence |
| [`V5_pair_affinity`](experiments/V5_pair_affinity.md) | Pair/co-occurrence | `v5.0.0` | Closed — reject | No significant Top-12 lift; proper scores worse than fair | Never activated |
| [`V6_fixed_boundary_js_regime`](experiments/V6_entropy_regime.md) | Entropy/regime | `v6.0.0` | Closed — reject | Frozen historical gate failed; no stable Top-12 or proper-score support | Never activated |
| [`V7_post_rng_main_bonus_role_bias`](experiments/V7_main_bonus_role_bias.md) | Draw-role exchangeability | `v7.0.0` | Closed — reject | Frozen 2020–2025 gate failed on significance, stability, proper scores, and global role audit | Never activated |
| [`V8_fixed_recurrence_harmonic`](experiments/V8_fixed_recurrence_harmonic.md) | Periodicity/frequency domain | `v8.0.0` | Closed — reject | Negative aggregate Top-12 lift; six of eight frozen gates failed | Never activated |
| [`V10_adjacent_pair_structure`](experiments/V10_adjacent_pair_structure.md) | Structural set feature; `v5_pair_cooccurrence` variant 2 for multiplicity | `v10.0.0` | Closed — reject | Small positive Top-12 point lift, but Holm/CI, proper-score, control, and joint-mechanism gates failed; maximum final-six hit was 3/6 | Never activated |
| [`V11_previous_bonus_carryover`](experiments/V11_previous_bonus_carryover.md) | Previous-bonus cross-draw residual; `transition_markov` variant 3 | `v11.0.0` | Registered; not implemented or scored | One 621-target consumed diagnostic is pre-registered but not authorized until a separate audited implementation commit | Not activated; fixed 208 eligible draws (104 + 104) only after a separate reviewed release sequence |

### V3 prospective freeze

After V5--V8 produced valid negative results, the next evidence-generating step
is not another historical pattern search. The project registered V3 with
unchanged numerical behavior on valid strict-prefix inputs as
`v3_boosting v3.0.0` for one clean prospective shadow cohort. Fail-closed
chronology and a full-history cache key harden evidence handling without
changing a valid uncached probability. Its
[registration](experiments/V3_frozen_shadow_cohort.md) freezes the
current 280-draw training span, stride 14, minimum 300-draw history, exact
feature list, gradient-boosting parameters, seed 649, 0.72 learned/0.28 fair
blend, runtime constraints, comparison set, and formal gates.

This is a registration only. Prospective status is `not_activated`; the current
stacked research branch freezes a dormant registry-gated version mapping but
does not activate it or create a `v3.0.0` snapshot. Every existing V3 snapshot
stamped `v1.0.0`, including the target
2026-08-19 file, is permanently excluded from the new cohort. The required Git
order is `F < A < R < S`: freeze, a later non-live activation anchor, a later
reviewed release seal, then the first snapshot's one-time first-add commit.
At `F`, config and live code contain a dormant registry-gated `v3.0.0` mapping;
`R` changes only the registry to `active` and may not change any frozen path.
The performance-blind activation producer defaults to dry-run and can create
only the three registered `A` artifacts; the frozen verifier independently
requires both `A` and `R` to precede the planned start's Toronto calendar date.

The sole formal look is the earliest exactly 208 eligible evaluated snapshots,
split positionally into 104 + 104. There is no early look and no extension.
Primary evidence is Top-12 hit lift over exact fair theory, with an exact
draw-level hypergeometric-convolution upper-tail test and a 10,000-replicate
seed-649 complete-row linear-percentile bootstrap. Brier and log loss must not
degrade versus fair in the aggregate or either half. V1 ensemble and the fixed
target-date-seeded random control remain comparisons. Even if every gate passes,
V1 remains production until a separate reviewed promotion PR.

The V9 post-RNG seven-number-selection idea is
[documented](research/V9_post_rng_seven_number_selection_basis.md). An
[outcome-blind independent review](research/V9_selection_stage_independence_review.md)
found it identifiable from V7 but too highly overlapping with V1 main-frequency
and unsupported by a distinct official production mechanism. It was rejected
before registration, implementation, or scoring and remains deferred. It may
only be reopened by new outcome-independent external evidence; no historical
V9 performance search is permitted.

V10 was the next registered bounded falsification attempt. Its
[source basis](research/V10_adjacent_pair_structure_basis.md) derives the exact
fair distribution of the count of adjacent integer pairs in an unordered
six-main-number set. The
[pre-registration](experiments/V10_adjacent_pair_structure.md) freezes one
fair-centred one-parameter exponential tilt, a fixed seed-649 global-label
bijection control, marginal Top-6/12/18 outputs, the sole Top-12 primary, and a
mandatory non-primary complete-set prequential likelihood gate. Because the
statistic sums 48 same-draw label pairs, V10 is conservatively variant 2 of
V5's append-only `v5_pair_cooccurrence` multiplicity family rather than a fresh
family. It is research-only and absent from live config. Its unique registered
621-target 2020–2025 consumed diagnostic is complete and the model is closed as
Reject. Aggregate Top-12 lift was `0.020145256170100767`, but Holm
`p=0.5445965052903498` and the interval crossing zero gave no reliable primary
evidence; proper-score, targeted-control, and joint-mechanism gates also
failed. Final-six output reached only 3/6 and never 6/6. See the
[decision record](experiments/V10_adjacent_pair_structure_results.md). The run
cannot be repeated or relabeled as blind or confirmatory evidence, and any
formula change requires a new version and prospective cohort.

V11 is the next registered falsification attempt. It applies one standard-
normal-penalized scalar logit offset to the immediately previous published
bonus label's frozen V1 ensemble marginal, then conserves expected count six
with one deterministic direct-marginal capacity transfer. The current RNG
boundary is fixed externally at 2019-05-15. The only targeted control selects a
deterministic pseudo bonus from each prior seven-label draw union using the
registered full SHA-256 rule; candidate and control retain the same original V1
history and marginals. The project-wide target-date-seeded `random v1.0.0`
benchmark remains a descriptive null control and a separately counted Final-6
opportunity. V11 is conservatively variant 3 of the append-only
`transition_markov` family because V2 and V3 were prior transition-bearing
attempts; their incompatible historical primary p-values enter Holm as `1.0`.

No V11 forecast or score existed at registration. Its one possible historical
run includes exactly the 621 already-consumed 2020--2025 targets, fixed 307/314
halves, paired V1/control gates, proper-score and anchor-evidence gates, and a
hash-chained forecast-before-reveal plus 6/6 opportunity ledger. It cannot be
called blind or confirmatory and cannot be rerun after claim acquisition. V11
is absent from production/live workflows; V1 remains production and V3 remains
shadow. Historical passage could only justify a separate reviewed activation
decision for an unchanged 208-draw prospective cohort.

The permanent historical opportunity catalog now preserves every still-
available V1--V4 Actions artifact and the complete V10 snapshot stream. It
records 16,146 legacy reported opportunities, 621 independently recomputed V10
opportunities, two exact duplicate streams that add zero opportunities, and
four explicit V5--V8 coverage gaps. Consequently the evidence statements stay
separate: legacy reports at least 4/6 without the complete frozen ticket, V10
verifies a maximum of 3/6, and the global maximum remains unknown. Legacy rows
whose Top-12 contains all six actual labels are coverage records, not Final-6
6/6 successes. The global claim also remains blocked by incomplete legacy
ticket-level deduplication. See
[`HISTORICAL_OOS_EVIDENCE_PROTOCOL.md`](HISTORICAL_OOS_EVIDENCE_PROTOCOL.md).

The V5 registration dataset contains 4,431 committed draws through 2026-08-12
with SHA-256
`95434535857a95f3ae9bd25e42345291274804702ed514b0bace6fafcf584bdf`.
Those observed 2026 draws were already consumed for `v5.0.0`; none can count as
prospective evidence. The frozen implementation and labeled historical
diagnostic are complete. Across the three registered lanes, every primary 95%
bootstrap interval included zero, every exact one-sided primary p-value exceeded
`0.05`, and both proper scores were worse than the fair constant baseline. The
seed-649 negative control behaved as null. The full outcome is in
[`V5_pair_affinity_results.md`](experiments/V5_pair_affinity_results.md).

The version is rejected, remains absent from `config.yaml`, produced no V5 live
prediction, and never began a prospective cohort. Any follow-up must register a
genuinely separate hypothesis/version before implementation; it may not tune
this candidate against the now-consumed answers.

V6 froze one adjacent-block entropy/regime hypothesis before implementation:
two fixed 104-draw blocks, one asymptotic gate, one directional probability
mapping, and one Top-12 primary metric. Its single labeled historical diagnostic
used the append-only 4,431-draw prefix through 2026-08-12; the registry
separately records that outcomes were already known through 2026-08-15 at
registration. Every reported lane is consumed and non-confirmatory.

The frozen `v6.0.0` gate failed. Development Top-12 lift was negative; the sole
formal 2020-2025 historical gate had Holm-adjusted `p = 0.498761088` with a 95%
bootstrap interval spanning zero; and development Brier and log-loss deltas
exceeded the frozen fair-baseline tolerance. The whole-draw date-permutation
control behaved as a null and the audit was clear, so this is a valid negative
result rather than a pipeline failure. The full decision is in
[`V6_entropy_regime_results.md`](experiments/V6_entropy_regime_results.md).

V6 is rejected, was not activated, and has no prospective cohort or live role.
V1 remains production and V3 remains shadow. Any change inspired by these
results requires a new version, pre-registration, freeze, and prospective cohort;
it cannot relabel any observed V6 result as blind or confirmatory.

V7 registered one externally bounded post-RNG mechanism probe before any V7
score existed. Starting at the documented 2019-05-15 RNG transition, it compares
each label's strictly prior six-main-role count with its bonus-role count using
one frozen seven-role Dirichlet-half smoothing rule and a deterministic
sum-to-six probability mapping. Its negative control preserves each observed
seven-number set and date while reassigning only the historical bonus role. The
unscored primary-source rationale is in
[`V7_mechanical_bias_basis.md`](research/V7_mechanical_bias_basis.md), and the
complete frozen formula is in
[`V7_main_bonus_role_bias.md`](experiments/V7_main_bonus_role_bias.md).

V7 has no development or legacy-validation score: pre-RNG history is not the
registered mechanism, and 2019 supplies only strictly lagged feature burn-in.
Its one applicable historical diagnostic is all 621 targets from 2020-01-01
through 2025-12-31, with fixed 2020–2022 and 2023–2025 stability halves. That
interval is already consumed and can only reject the candidate or support a
separate reviewed shadow-activation decision; it can never confirm prediction.
No V7 historical run had occurred at registration. The implementation was then
frozen at `180cd045e7797b95db4226f7d79d66d6ee9a5965`, pushed, tested in CI, and
run exactly once from a clean matching tree. The aggregate Top-12 lift was
`+0.013704`, but Holm-adjusted `p=0.372657` and the 95% bootstrap interval
`[-0.065201, +0.094219]` did not support it. The 2020–2022 half was negative,
proper scores were worse than fair in the aggregate and both halves, and the
global role audit was null (`p=0.570743`). The registered control behaved as a
null and the audit was clear, so this is a valid negative result, not a pipeline
failure. See the [V7 decision record](experiments/V7_main_bonus_role_bias_results.md).

V7 is rejected, was never activated, and has no prospective cohort or live
role. Its previously registered 208-draw plan remains an unstarted record, not
permission to reopen `v7.0.0`. Any follow-up inspired by these results requires
a genuinely new hypothesis/version and pre-registration; the observed V7
history is consumed for it. V1 remains production and V3 remains shadow.

V8 registered one fixed-frequency, post-RNG falsification test before any V8
score existed. It projects each label's strictly prior
six-main membership indicator onto the sole frequency `12*pi/49`, chosen from
the reciprocal fair inclusion probability rather than from a periodogram. The
[primary-source basis](research/V8_fixed_spectral_basis.md) makes the limitation
explicit: `49/6` is a geometric waiting-time mean, not an official or physical
lottery cycle, and a fair IID process gives this frequency no privileged
expected power.

The [V8 registration](experiments/V8_fixed_recurrence_harmonic.md) freezes the
raw expanding projection, one deterministic sum-to-six sigmoid map, all 621
consumed 2020–2025 targets, two fixed stability halves, and two distinct
controls. The strict-prefix whole-draw control preserves the six-of-49 row
constraint while destroying temporal order; the per-label phase rotation is
only a component stress test and is not presented as a row-preserving fair
null. V8 is now **implemented / historical diagnostic complete / rejected /
never activated**.
The frozen implementation commit is
`c48ab2277f005a48bc4dc57f5a532b476ab900fa`. Its sole one-shot historical
diagnostic then scored exactly the 621 already-consumed targets from 2020-01-01
through 2025-12-31. Aggregate Top-12 lift was
`-0.016891780866936212`, exact/Holm p was `0.6700938237435888`, and the 95%
bootstrap interval was
`[-0.08935554898287834, 0.05883285681422251]`. The first fixed half had
negative primary lift, and aggregate plus first-half Brier/log-loss deltas
exceeded the frozen fair tolerance.

Both controls met their registered null definitions, but that did not support
the candidate. Candidate-minus-row-control Top-12 point estimates were negative
in the aggregate and both halves, and every paired interval had a negative lower
endpoint. Of the eight jointly required gates, only the phase-control-null and
audit-clear gates passed. The frozen conjunction therefore made the exact
**Reject / `not_activated`** decision. The complete outcome is in the
[V8 decision record](experiments/V8_fixed_recurrence_harmonic_results.md) and
[generated report](../reports/v8_spectral_phase_v8.0.0_historical.md).

The permanent claim at
`reports/v8_spectral_phase_v8.0.0_historical.claim` has SHA-256
`6598a2f38462fe6274b9dfa6b6b8c51e6af367b551fd861ef8a582000d60c76d`.
It must remain permanently and prohibits another `v8.0.0` historical run. The
2020–2025 lane is consumed, non-blind, and non-confirmatory. Any hypothesis,
frequency, feature, parameter, control, metric, split, or gate changed in
response needs a new version and pre-registration; every 2026+ outcome observed
before that new freeze is also consumed for the changed candidate. V8 has no
prospective cohort or live role. V1 remains production and V3 remains shadow.

## Validation protocol

Every serious candidate must satisfy all of the following:

- **Chronological walk-forward:** the prediction for `t` sees `history[:t]` only.
- **Frozen selection:** metrics, feature family, parameters, and decision gates are
  fixed before confirmatory scoring.
- **Fair baseline:** compare Top-6, Top-12, and Top-18 hits to exact hypergeometric
  expectations, not only one finite random run.
- **Operational baselines:** retain the random baseline and frozen V1/V3 reference
  outputs where relevant; do not change references to flatter a candidate.
- **Proper scoring:** report Brier score and binary log loss against the fair
  constant probability, plus mean actual rank and Top-K hits.
- **Uncertainty:** report confidence intervals and a pre-specified permutation,
  bootstrap, or exact-test diagnostic appropriate to the primary metric.
- **Multiplicity:** keep a ledger of all attempted families/variants and apply the
  registered family-wise or false-discovery-rate correction.
- **Stability:** report non-overlapping eras and prospective halves; do not hide a
  failing year or source regime behind an aggregate.
- **Negative controls:** shuffled labels, time permutations, and/or phase-random
  series must fail to show systematic lift.
- **Reproducibility:** fixed seed, committed data fingerprint, config, version,
  command, detailed report, and tests accompany the result.

Theoretical fair expectations per draw remain:

- Top-6: `36/49 = 0.734694...`
- Top-12: `72/49 = 1.469388...`
- Top-18: `108/49 = 2.204082...`

## Default promotion gate

The experiment note may set a stricter gate, but not a weaker one after outcomes
are visible. Promotion from shadow to production requires:

1. at least 104 eligible prospective draws for the exact frozen version; this is
   a minimum observation window, not a claim that one year always provides enough
   power;
2. positive lift on the single pre-registered primary ranking metric with a
   multiplicity-adjusted `p <= 0.05` and a confidence interval excluding zero;
3. no material degradation versus the fair constant baseline on both Brier score
   and log loss;
4. positive primary-metric lift in both non-overlapping halves of the prospective
   cohort, with no dependence on one short lucky interval;
5. negative controls behaving as nulls and no unresolved leakage, source, missed
   snapshot, or audit-trail issue;
6. a reviewed promotion PR that updates model role/config and documents the
   evidence. Promotion is never automatic.

If the registered prospective power analysis requires more than 104 draws, use
the larger number. If the gate fails, reject the version or continue it unchanged
only under a pre-registered extension. Do not rescue it by tuning on its answers.

## Reporting decisions

Use one of these explicit outcomes:

- **Reject:** evidence contradicts the hypothesis or fails the frozen gate.
- **Archive:** implementation was invalid, leaked, or could not produce an
  auditable cohort; make no performance claim.
- **Continue shadow:** checkpoint is valid but underpowered and the registered
  stopping rule permits more observations without modification.
- **Promote:** every frozen gate is met and a review approves the operational
  change.

“Promising” may justify a shadow cohort; it is not a synonym for proven,
predictive, or production-ready.
