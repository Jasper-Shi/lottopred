# V5+ Research Roadmap

## Objective

Develop one falsifiable hypothesis at a time while protecting the true forward
experiment. The goal is evidence about predictability, not a sequence of models
that look better on already-observed draws.

V5+ begins with two hard facts. Every historical result through 2025 has already
been available to the research process, and the legacy registered history was
later found incomplete and conflicting. The old V2–V4 run used 621 recorded rows
in 2020–2025; the sealed official-calendar reconciliation contains 627 draws.
Its strict-blind qualification and exact headline metrics are withdrawn as
described in `docs/V2_V4_RESULTS.md`. The interval remains consumed and useful
only for labeled diagnostics; correction does not make its answers unseen again.

## Evidence lanes

Keep these lanes separate in code, reports, and claims:

| Lane | Data | Allowed use | Claim allowed |
|---|---|---|---|
| Historical development | 1982–2014 | Feature construction, fitting choices, nested chronological tuning | Development result only |
| Historical legacy validation | 2015–2019 | Stability and sensitivity diagnostics | Historical validation, already exposed to model selection |
| Consumed corrected-history diagnostic | 2020–2025 | Data-correction sensitivity, frozen-candidate stress test, and failure analysis | Historical diagnostic only; never untouched/blind for V5+ |
| Prospective forward | 2026+ after a corrected-history candidate's freeze commit | Immutable pre-draw prediction and later scoring | Confirmatory evidence for that exact frozen version and data identity |

Forward evidence is model-specific. A 2026 result observed before V5 is frozen is
historical input for V5, not V5 forward evidence. If a V5 outcome causes any
behavioral change, V5 is closed; freeze V5.1/V6 and start a new cohort.

## Data-integrity gate

Before any new historical model execution, the runner must load history through
the reviewed `src/lotto649/operational_history.py` seam, which owns the deployed
Git-registry genesis and delegates immutable seal/suffix validation to
`history_registry.py` and `verified_history.py`. Direct use of the legacy
processed CSV is prohibited for new evidence. The read consumer is integrated,
but the operational kill switch remains closed. The bounded dual-source
collector, offline preparer, and local bare-repository exact-CAS adapter now
cover source acquisition plus the `B -> E -> S -> P` transaction and local state
machine as disconnected seams. A fixed-repository GitHub exact-CAS publisher,
fresh public reload, and isolated exact-P execution/artifact handoff now also
exist, still disconnected. A capability-scoped exact remote `P -> A` publisher
is independently reviewed, merged, and likewise remains disconnected. Live
still requires the prescribed remote canaries, protected `main`,
P-code-provenance orchestration, a real `P -> A` reload, and the separate
SHA-bound workflow release review in `docs/OPERATIONS.md` before any execution
switch can be reconsidered.

Do not silently rerun or overwrite V2–V11 artifacts under their old versions.
Any corrected-history sensitivity analysis gets a new experiment identity,
states that 2020–2025 is consumed, and preserves the old artifacts plus their
data-integrity erratum. A historical high-water or opportunity claim is eligible
only after the corrected source identity and chronology validator both pass.
The append-only legacy opportunity ledger currently has zero eligible
opportunities and null Final-6/Top-12 high-waters; its raw metrics are archival
only. See `docs/HISTORICAL_OOS_EVIDENCE_PROTOCOL.md` before registering or
reporting any new opportunity.

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
