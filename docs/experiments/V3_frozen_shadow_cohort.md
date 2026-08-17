# V3 frozen prospective shadow cohort

Registration date: 2026-08-16

Experiment ID: `V3_frozen_shadow_cohort`

Frozen identity: `v3_boosting v3.0.0`
Status: **registered / prospective `not_activated`**

## Decision being registered

This registration gives the already-existing V3 algorithm a clean prospective
identity without changing its numerical behavior on valid strict-prefix
inputs. The freeze adds fail-closed chronology enforcement and corrects the
cache identity so distinct histories cannot alias; neither change alters a
valid uncached V3 probability. V3 remains a shadow model; V1 remains the
production baseline. This document does not authorize a live release, does not
promote V3, and does not claim that V3 predicts a fair lottery.

The 2020--2025 V2--V4 result is consumed historical evidence. Its small V3
ranking lift was not significant, its probability calibration was worse than
the fair constant baseline, and 2025 deteriorated sharply. Those observations
explain why an unchanged prospective replication is scientifically preferable
to another historical feature search, but they cannot count toward this cohort.
No historical V3 score may be rerun, recomputed, selected, or used as
confirmatory evidence under this registration.

All V3 snapshots currently stamped `v1.0.0` are excluded, even though valid
operational inputs use the same intended probability algorithm. That includes
the committed snapshot targeting 2026-08-19. The version change to `v3.0.0` is
an audit-identity correction for a new cohort plus fail-closed implementation
hardening, not a response to a newly observed V3 outcome and not a statistical
model change on valid strict-prefix inputs.

## Known-outcome boundary at registration

The fixed local registration prefix is the first 4,431 rows of
`data/processed/draws.csv`, through 2026-08-12:

- source commit:
  `39b99a9e0a6351b4143f81c9a95eb1639456a35d`;
- byte SHA-256:
  `95434535857a95f3ae9bd25e42345291274804702ed514b0bace6fafcf584bdf`.

The stronger outcome boundary records every result already known when this
registration was written: 4,432 draws through 2026-08-15 at commit
`90177c80cfb070038d79508fb2e73305a297f516`, with byte SHA-256
`edfb7f8a4a7711a630957d6f86b567e6b254caf7b1d1aaea0edf1d16a34155b3`.
The activation anchor must replace this with an equal or later verified
boundary. No target on or before the activation boundary can ever be eligible.

The historical lanes remain fixed but are not scored in this registration:

| Lane | Dates | V3 cohort use |
|---|---|---|
| Development | 1982-01-01 through 2014-12-31 | Consumed algorithm-development context only |
| Legacy validation | 2015-01-01 through 2019-12-31 | Consumed model-selection context only |
| Consumed diagnostic | 2020-01-01 through 2025-12-31 | Refer only to the committed V2--V4 result; no new score |
| Prospective | Eligible snapshots after the future release seal | Sole evidentiary lane for `v3.0.0` |

## Frozen implementation

The following repository paths, as they exist at the freeze commit `F`, jointly
define the model and prediction environment. They are normative, not merely
illustrative:

1. `docs/experiments/V3_frozen_shadow_cohort.md`
2. `src/lotto649/models/v3_boosting.py`
3. `src/lotto649/models/baselines.py`
4. `src/lotto649/models/logistic.py`
5. `src/lotto649/models/ensemble.py`
6. `src/lotto649/research_features.py`
7. `src/lotto649/features.py`
8. `src/lotto649/models/base.py`
9. `src/lotto649/models/factory.py`
10. `src/lotto649/predictor.py`
11. `src/lotto649/optimizer.py`
12. `src/lotto649/live.py`
13. `src/lotto649/config.py`
14. `src/lotto649/storage.py`
15. `src/lotto649/domain.py`
16. `src/lotto649/evaluation.py`
17. `src/lotto649/research_protocol.py`
18. `src/lotto649/prospective.py`
19. `src/lotto649/cli.py`
20. `src/lotto649/data.py`
21. `src/lotto649/data_sources.py`
22. `config.yaml`
23. `pyproject.toml`
24. `requirements-live.lock`
25. `.github/workflows/live.yml`
26. `.github/workflows/prospective.yml`

The workflow frozen at `F` must install the project using
`requirements-live.lock` as a constraints lock. Running with an unconstrained
scikit-learn, NumPy, SciPy, pandas, or joblib version is ineligible. A change to
any frozen path, dependency version, feature definition, training rule,
probability mapping, ranking tie-break, or output selection after `F`
closes `v3.0.0`; the changed model needs a new version and new cohort.
Live release verification also requires CPython `3.12` and every installed
distribution pinned by `requirements-live.lock` to match its exact registered
version before a `v3.0.0` snapshot may be written.

The separate read-only prospective monitor runs after the live workflow and on
manual dispatch. It does not create a claim, compute a formal metric early, or
write repository content. At 207 raw committed V3 evaluations it emits a
notice. At 208 or more it runs the full immutable-evidence audit; `ready`,
`overdue`, and integrity failures become high-visibility independent job
failures without undoing the already committed V1 live cycle. The live path's
performance-blind interlock then prevents a 209th V3 evaluation while leaving
V1 evaluation and generation operational. Catch-up cycles impose a per-model
quota: below 208 raw committed candidate evaluations they may add at most the
remaining count; from 208 onward a still-collecting cohort may add at most one
candidate evaluation before another committed-HEAD audit. Earlier-pending,
ready, sealed, overdue, closed, or audit-invalid states admit zero.

`data.py` and `data_sources.py` are included deliberately. A committed source
blob, its append-only prefix, and its Git SHA prove exactly which rows trained a
snapshot, but blob evidence alone cannot prove that a changed parser or
reconciliation policy still means "verified official result." Freezing both
the ingestion semantics and the blob evidence closes those separate risks.
The V1 ensemble and target-date-seeded random control are formal comparison
gates, so their baseline, logistic, and ensemble implementations are frozen as
well; an unchanged `v1.0.0` filename alone is not sufficient evidence.

`config.yaml` at `F` pre-registers both
`live.model_versions.v3_boosting: v3.0.0` and
`live.model_version_experiments.v3_boosting: V3_frozen_shadow_cohort`. The
frozen live path must ignore that version override unless the named registry
entry has experiment status `prospective_shadow` and prospective status
`active`. Therefore `F` and `A` continue writing legacy V3 `v1.0.0` snapshots;
only the registry transition at `R` opens the preconfigured gate. Neither `R`
nor any later snapshot commit may modify a frozen path.
`docs/experiments/registry.yaml` is deliberately not in the frozen path manifest
because `R` must change its administrative cohort fields.

Before writing the first `v3.0.0` snapshot, live generation must run the
performance-blind release verifier at its committed source `HEAD`. Each new
candidate snapshot records an exact `metadata.prospective_release` mapping with
`experiment_id`, `freeze_commit`, `activation_commit`, `release_commit`,
`generation_source_commit`, `immutable_registration_digest`,
`activation_anchor_sha256`, `frozen_manifest_sha256`, and
`requirements_live_lock_sha256`. The auditor derives those values again from
Git and rejects a missing, extra, or mismatched field; metadata is not accepted
as self-attestation. If this performance-blind gate fails, that draw's
`v3.0.0` output is suppressed with a structured warning and becomes missing
prospective evidence; the six V1 production-baseline snapshots still run. The
live path must never hide the failure by falling back to a legacy V3 `v1.0.0`
snapshot.

That exclusion does not make the research specification mutable. The auditor
must canonically compare this V3 registry row with its blob at `F`. The only
fields allowed to change at release are top-level `status` and `result`, plus
`prospective.status`, `freeze_commit`, `activation_commit`,
`outcomes_known_at_activation`, and `cohort_start`. Identity, family, version,
seed, primary metric, multiplicity, registration data, historical partitions,
all `parameters`, negative controls, role, 208 minimum, and commit deadline must
remain byte-semantically equal to `F` at `R` and every `S`. Any other registry
change is specification drift and makes the cohort ineligible.

### Training rows and target chronology

For a prediction target date `t`, the caller must supply a verified,
chronologically ordered history whose newest draw date is strictly before `t`.
Let `D` be its length. If `D < 300`, V3 returns the fair constant
`6/49` for all labels and such a prediction is not eligible for this cohort.

For eligible histories, freeze these current settings:

- `training_draws = 280`;
- `stride = 14`;
- `min_history = 300`;
- training target indices are
  `range(max(120, D - 280), D, 14)`;
- every training row for index `j` is built only from `history[:j]`, and its
  label is membership in the six main numbers of `history[j]`;
- the bonus number is excluded from features, fitting labels, and scoring;
- the target date may supply only its known calendar fields; its result and
  bonus are prohibited.

The exact ordered feature vector is:

```text
number_scaled, long_freq, freq_10, freq_25, freq_50, freq_100,
freq_250, ema_12, ema_35, ema_90, gap, gap_ratio, in_prev,
in_prev2, weekday_freq, month_freq, transition_freq,
sum_prev_centered, sum_ma5_centered, sum_ma20_centered,
sum_slope5, target_weekday, target_month_sin, target_month_cos
```

Their exact formulas, constants, edge behavior, and ordering are the frozen
implementation in `research_features.py` and `features.py` at `F`. No feature
may be removed, added, recalculated with a different window, normalized using a
future row, or selected after observing this cohort.

### Estimator and probability map

Fit exactly one scikit-learn `HistGradientBoostingClassifier` per uncached
prediction with:

```text
learning_rate       = 0.06
max_iter            = 45
max_leaf_nodes      = 15
min_samples_leaf    = 35
l2_regularization   = 2.0
random_state        = 649
```

For each label `i`, let `g_i` be the fitted positive-class probability and let
`b = 6/49`. The pre-normalization score is fixed as

```text
s_i = 0.72 * g_i + 0.28 * b.
```

Apply the frozen `normalize_expected_six` implementation to labels `1..49`.
Before caching or writing a snapshot, the model must enforce all of these
conditions: the key set is exactly the integer labels `1..49`; every value is
finite and strictly in `(0,1)`; and `math.fsum(values)` is equal to six under
`math.isclose(rel_tol=0, abs_tol=1e-12)`. Any failure raises `RuntimeError` with
message `V3 probability contract is violated`; it must not write, clip, impute,
or silently repair a probability or snapshot. This fail-closed validation does not
alter a valid probability. Rank valid output by descending probability and then
ascending number. Top-6, Top-12, and Top-18 are prefixes of that one ranking;
the final six uses the unchanged independent log-score selector over the Top-12
pool. There are no structural-number constraints, calibration fit, ensemble
weight, or outcome-dependent override.

The frozen prediction cache is an implementation optimization only. Its key is
the complete immutable `tuple(history)` plus `target_date`, and it must return
the same probabilities as an uncached fit. The pre-freeze short key `(history
length, newest history date, target date)` is prohibited because distinct
histories could alias. Prediction also calls the strict chronology assertion
before cache lookup. A cache or determinism defect makes the affected snapshot
ineligible and triggers an audit review; it may not be silently repaired after
the outcome.

## Fixed comparison set and negative control

Score the same eligible target draws for exactly these comparisons:

1. exact fair theory, with per-label probability `6/49` and Top-12 expected
   hits `72/49`;
2. the frozen V1 `ensemble v1.0.0` operational baseline;
3. the existing `random v1.0.0` negative control.

The random control is the current `RandomBaseline`: it uses
`numpy.default_rng(649000000 + target_date.toordinal())`, draws one
`Uniform(-1e-9, 1e-9)` jitter for each ascending label, adds it to `6/49`, and
normalizes to expected total six. Its outcome-independent target-date seed is
fixed before any target result. It never enters V3 training or probabilities.

All candidate/control comparisons use identical eligible target rows. The V1
ensemble and random model must also be generated before their target results;
retrospective reconstruction is prohibited. Report Top-6, Top-12, Top-18,
Brier, binary log loss, and mean actual rank for all three models. V1 is an
operational comparator, not a second discovery hypothesis. V3 cannot be
recommended to replace V1 if its aggregate Top-12 mean is not strictly higher
than V1 ensemble at the formal look.

The random control must behave as a null in the aggregate and both fixed
halves: for each scope, either its one-sided exact fair-null `p` is greater than
`0.05` or its registered Top-12 lift interval includes zero. A systematic
control lift, chronology failure, or scoring mismatch archives the cohort as
invalid rather than supporting V3.

## Primary metric and fixed uncertainty procedures

The sole primary metric is mean Top-12 main-number hits per eligible draw minus
the exact fair expectation `72/49`. Top-6, Top-18, final-six hits, proper
scores, and rank are secondary diagnostics except where a proper score is a
mandatory gate below. No secondary p-value supports a predictive claim.

For the aggregate 208-draw primary test, compute the one-sided upper-tail
probability under the exact per-draw distribution
`Hypergeometric(N=49, K=6, n=12)`. Convolve that discrete distribution across
all 208 complete draws and report `P(total hits >= observed total hits)`. The
registered family contains one V3 variant, so the raw and family-adjusted
primary p-values are identical. The fixed alpha is `0.05`.

Compute a second, jointly required uncertainty check as follows:

- unit: one complete target draw;
- statistic: mean Top-12 hits minus `72/49`;
- generator: `numpy.random.default_rng(649)`;
- replicates: exactly 10,000;
- resample 208 row indices with replacement within each replicate;
- interval: two-sided 95th-percentile interval using NumPy's `linear` percentile
  method.

Do not resample the 49 label cells separately. Do not change the seed,
replicate count, tail, interpolation, alpha, or statistic after any eligible
outcome is visible.

For proper scores, use the repository's per-label mean Brier score and clipped
binary log loss over the six main labels. In the aggregate and each fixed half,
both

```text
V3 Brier - fair-constant Brier   <= 1e-9
V3 log loss - fair-constant loss <= 1e-9
```

must hold. The tolerance only covers floating-point equality; it is not a
performance margin.

## Cohort boundary: `F < A < R < S`

The four Git events have distinct meanings and must be strict ancestors in this
order:

```text
F = freeze commit containing this registration and all frozen inputs
A = later activation-anchor commit recording F and the then-latest verified
    outcome boundary; A does not enable V3 live execution
R = still-later reviewed release-seal/registry-transition commit that cites A
    and sets the cohort active and cohort_start; this registry-only transition
    opens the v3.0.0 mapping and constrained workflow already frozen at F
S = first Git commit that adds an otherwise eligible v3.0.0 prediction snapshot

F < A < R < S
```

`A` must add exactly these three previously absent artifacts and no other path:

- `reports/prospective/V3_frozen_shadow_cohort__v3.0.0__activation.json`;
- `reports/prospective/V3_frozen_shadow_cohort__v3.0.0__activation.md`;
- `reports/prospective/V3_frozen_shadow_cohort__v3.0.0__activation.claim`.

The JSON has schema version `1` and exactly binds the experiment/model/version,
`F`, decision `continue_shadow`, role `shadow`, the processed-data path and its
SHA-256/count/tail date, and the planned `cohort_start`. The data boundary's
`source_commit` in `R` must equal `A`, whose tree contains that exact data blob.
The result row introduced at `R` must cite the three fixed artifacts as its JSON,
Markdown, and result/claim paths. This avoids a self-referential commit hash in
the anchor while still proving what `A` reviewed. Any delayed release that misses
the planned start requires a new anchor rather than editing or reusing `A`.
Both `A` and `R` must have timezone-aware Git commit timestamps whose
`America/Toronto` calendar date is strictly before the planned `cohort_start`.
An anchor or release committed on the start date is late, even if no draw has
yet occurred that day, and the version must remain inactive until a new anchor
and later start are reviewed.

`A` must remain a real, reachable commit with its exact SHA; the activation PR
must not squash it away. The release verifier must prove that `F` is a strict
ancestor of `A`, `A` is a strict ancestor of `R`, and `R` is a strict ancestor
of the snapshot's single first-add commit `S`. A snapshot first committed in
`F`, `A`, or `R` is ineligible. The current stacked research branch is not
merged and this registration PR performs only `F`; it must not write an
activation boundary, mark the cohort active, open the dormant live-version
gate, or create a snapshot.

`R` cannot be inferred merely from the registry's current contents. The auditor
must derive the real commit that first introduced the complete reviewed
`prospective_shadow` / `active` row, verify its frozen-registration digest and
activation reference, and use that commit in the `R < S` ancestry check. Merely
showing `A < S` is insufficient.

At registration, the structured fields therefore remain exactly:

```text
status                         = registered
prospective.status             = not_activated
prospective.freeze_commit      = null
prospective.activation_commit  = null
outcomes_known_at_activation   = null
cohort_start                   = null
```

## Eligibility and stopping rule

The cohort consists of the earliest exactly 208 evaluated snapshots that pass
every rule below:

1. identity is exactly `v3_boosting v3.0.0`, role `shadow`;
2. its target date is strictly after both the registration-known and
   activation-known outcome boundaries and is on or after the registered
   `cohort_start`;
3. `F < A < R < S` is proven from a complete, non-shallow Git history;
4. the snapshot file has one unambiguous first-add commit and has never been
   modified, regenerated, or recommitted;
5. `S` is before the target's local calendar date in `America/Toronto`;
6. the source-data fingerprint, history count, and history-through date bind an
   exact verified chronological prefix strictly before the target;
7. model/config/runtime fingerprints match the freeze and release records;
8. a later immutable evaluation is bound to the same snapshot and verified
   official result; and
9. the matching V1 ensemble and random comparison snapshots are also valid
   pre-draw artifacts.

Missing, late, overwritten, reconstructed, conflicting-source, wrong-version,
wrong-role, dependency-drift, or otherwise integrity-failed files are excluded
and never repaired. Exclusion does not reduce the required count: collection
continues only until the first 208 eligible evaluated rows exist.

The halves are positional, not calendar-selected: eligible rows 1--104 and
105--208. There is no formal or informal aggregate gate look before row 208,
no optional stopping, and no result-inspired extension. Per-draw operational
evaluations may be committed, but they cannot be used to change V3, its role,
this protocol, or the endpoint. If an observed outcome influences a change,
`v3.0.0` closes and the changed version starts a new post-change cohort.

At exactly 208 eligible evaluated rows, perform one formal look. Promotion
eligibility requires the conjunction of all of these frozen gates:

1. aggregate Top-12 lift is strictly positive;
2. the exact one-sided primary p-value is at most `0.05`;
3. the aggregate 95% bootstrap interval has a lower endpoint strictly above
   zero;
4. Top-12 lift is strictly positive in each fixed 104-row half;
5. both proper-score deltas meet the `1e-9` fair-baseline tolerance in the
   aggregate and both halves;
6. aggregate V3 Top-12 mean is strictly above the frozen V1 ensemble comparison;
7. the random control meets its null rule in the aggregate and both halves; and
8. chronology, source, runtime, snapshot, evaluation, and audit checks are all
   clear.

The formal-look claim step must atomically create the permanent claim
`reports/prospective/V3_frozen_shadow_cohort__v3.0.0__formal.claim` before any
checkpoint-level aggregate performance metric is computed. Per-draw immutable
evaluations may already contain operational scores and may be integrity-checked,
but they may not be aggregated. The claim must then be committed as a unique
first-add Git artifact. Only after that commit may the public formal runner
atomically and permanently create
`reports/prospective/V3_frozen_shadow_cohort__v3.0.0__formal.attempt`. That
attempt artifact is acquired before reading or computing any checkpoint-level
aggregate metric and distinguishes an unrun committed claim from a consumed
failed run. The runner then stages the schema version `1` JSON and Markdown
reports and publishes both without overwrite to the correspondingly named
`__formal.json` and `__formal.md` paths. The claim and attempt are retained after
success or failure. Publication commits only after both final hard links exist
and their parent directory has been fsynced. Any failure after attempt
acquisition but before that commit point archives `v3.0.0` and forbids a rerun.
Cleanup after the durable commit point is best effort: a cleanup failure emits a
warning but does not invalidate the already published pair. A 209th eligible
evaluation also makes an unrecorded look overdue and cannot be repaired
retrospectively.

The decision map is frozen before activation. If either
`random_control_null_aggregate_and_halves` or `audit_clear` fails, decide
**Archive**, because the pipeline cannot support a performance claim. If those
two validity gates pass but any scientific-performance or calibration gate
fails, decide **Reject** and close the valid negative experiment. Passing every
gate makes V3 only **eligible for a separate reviewed promotion PR**;
promotion is never automatic. That review must leave V1 production unchanged
unless it explicitly approves the role/config transition from the frozen
prospective evidence. There is no continuation or extension beyond the single
208-draw formal look. If a 209th eligible evaluation is committed before the
208-row formal-look record is fixed, the cohort is overdue and no retrospective
formal look may be manufactured; the release must fail closed to an audit
decision.

The terminal transition `T` is a separate, non-merge, registry-only commit
strictly after the committed formal attempt/JSON/Markdown result. Reject,
Archive, and Promote must match the formal gate outcome; Promote additionally
requires that separate reviewed promotion decision. The terminal result cites
the formal JSON and Markdown, uses the formal Markdown as `result_file`, and
binds `implementation_commit` to the formal-result commit. The auditor fixes a
closed cohort's data/target upper bound at `T`, rejects any prediction or
evaluation for the same model/version added after `T`, and still replays V3,
V1 ensemble, and random from the frozen implementation. If a later model
version legitimately changes a frozen path, audit the closed cohort from a
checkout of `T`; current-HEAD audit must fail closed rather than execute new
code against old evidence.

## Pre-snapshot checks required of the release PR

Before `R`, deterministic offline tests must establish:

- every training feature and label uses only a strict historical prefix;
- appending a future draw cannot change a prediction for an earlier target;
- the exact 280/14/300 training schedule and ordered feature list are locked;
- estimator parameters, seed, 0.72/0.28 blend, expected-six normalization, and
  number-ascending tie-break are locked;
- invalid label keys, non-finite or out-of-range probabilities, or an
  expected-six error above `1e-12` fail before cache/snapshot persistence;
- cached and uncached predictions are identical;
- the 49-label probability contract and main-only scoring hold;
- per-model `v3.0.0` filenames and metadata do not rename or overwrite any
  `v1.0.0` snapshot;
- a missing/invalid experiment mapping, registry, release proof, or V3 runtime
  prediction failure suppresses only V3 with a stable warning while V1 still
  persists; a non-default version can never bypass the experiment gate;
- the preconfigured version override remains dormant while the named registry
  experiment is `registered` / `not_activated` and opens only after the
  registry-only `R` transition to `prospective_shadow` / `active`;
- the F/A/R ancestry, outcome boundary, source fingerprint, one-commit snapshot,
  and pre-target deadline fail closed;
- the live workflow installs with `requirements-live.lock` as constraints; and
- V1 production behavior and all existing predictions/evaluations remain
  unchanged.

No historical performance run is part of those checks.
