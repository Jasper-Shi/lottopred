# V8 Fixed-Recurrence Harmonic Result and Decision Record

## Decision

**Reject `v8_spectral_phase` version `v8.0.0`. Do not activate it as a
shadow model.** V1 remains the production-baseline suite and V3 remains the
only research shadow model; their operational roles are unchanged.

The sole frozen historical diagnostic failed six of the eight jointly required
gates. Aggregate Top-12 lift was negative at
`-0.016891780866936212`, the Holm-adjusted exact p-value was
`0.6700938237435888`, and the aggregate bootstrap interval
`[-0.08935554898287834, 0.05883285681422251]` included zero. The first
fixed half also had negative Top-12 lift, aggregate and first-half proper scores
exceeded the registered fair-baseline tolerance, and the candidate did not
outperform the row-permutation control in any registered scope. Both control
families met their registered null definitions, and the audit-warning list was
empty.

This is a valid negative result. It does not establish predictive lottery
signal and it is not proof of the null. The fixed recurrence was deliberately a
low-prior falsification test: `49/6` is a fair geometric waiting-time mean, not
a mechanism-backed period. No frequency, phase, feature, activation boundary,
mapping, solver parameter, metric, control, split, seed, or gate may be changed
and then re-evaluated as `v8.0.0`.

## Audit identity and evidence boundary

- Experiment: `V8_fixed_recurrence_harmonic`; multiplicity family:
  `periodicity_frequency_domain`; variant and family size: `1`.
- Candidate: `v8_spectral_phase`; version: `v8.0.0`.
- Registration commit:
  `dff1aecdffb6607d95a7653be87adcd13fb26231`.
- Frozen implementation commit:
  `c48ab2277f005a48bc4dc57f5a532b476ab900fa` (`c48ab22`).
- Exact command:
  `lotto649 --config config/research-v8-fixed-spectral-phase.yaml research-v8 --code-commit c48ab2277f005a48bc4dc57f5a532b476ab900fa`.
- Permanent one-shot claim:
  [`reports/v8_spectral_phase_v8.0.0_historical.claim`](../../reports/v8_spectral_phase_v8.0.0_historical.claim),
  raw SHA-256
  `6598a2f38462fe6274b9dfa6b6b8c51e6af367b551fd861ef8a582000d60c76d`.
  It was created before the first score and is retained permanently on success
  or failure.
- Historical-diagnostic dataset:
  [`data/processed/draws.csv`](../../data/processed/draws.csv), 4,431 draws
  through 2026-08-12, raw SHA-256
  `95434535857a95f3ae9bd25e42345291274804702ed514b0bace6fafcf584bdf`,
  source commit `39b99a9e0a6351b4143f81c9a95eb1639456a35d`.
- Outcomes known at registration: 4,432 draws through 2026-08-15, raw
  SHA-256
  `edfb7f8a4a7711a630957d6f86b567e6b254caf7b1d1aaea0edf1d16a34155b3`,
  source commit `90177c80cfb070038d79508fb2e73305a297f516`.
- Git data-boundary verification passed, every fold used the exact
  target-truncated prefix, the registration prefix was preserved, and the
  known-outcomes fingerprint is
  `257aef242bb898649b0923ac03f2271c7536ff7f840edf552c0dc6b4b03ce1dd`.
- Research configuration:
  [`config/research-v8-fixed-spectral-phase.yaml`](../../config/research-v8-fixed-spectral-phase.yaml),
  raw SHA-256
  `37cd3f5444be05c0508029d8f341e5291514d7444cd4c961cdc0d57815ee1aed`,
  effective canonical SHA-256
  `db5dbbcb9ecb7654c92a407310671c42fc290e09a744014d485fd809f1c1f60a`.
- Frozen V7 reference report:
  [`reports/v7_main_bonus_role_bias_v7.0.0_historical.json`](../../reports/v7_main_bonus_role_bias_v7.0.0_historical.json),
  raw SHA-256
  `242018714a17a78a8b99309e4391e153c293a02121738addd2bb8f9f74d6c121`.
- Frozen V7 reference claim:
  [`reports/v7_main_bonus_role_bias_v7.0.0_historical.claim`](../../reports/v7_main_bonus_role_bias_v7.0.0_historical.claim),
  raw SHA-256
  `1443982f9b40ba5b460632211baa17b4aff7cb9cdcd48010c0a538f141344290`.
- Machine-readable result:
  [`reports/v8_spectral_phase_v8.0.0_historical.json`](../../reports/v8_spectral_phase_v8.0.0_historical.json),
  schema version `4`, raw SHA-256
  `e9b51a5316811cbde2b06c36bb61ffffd04b283a4c886cb9ac213bb8fb7deed5`.
- Compact generated result:
  [`reports/v8_spectral_phase_v8.0.0_historical.md`](../../reports/v8_spectral_phase_v8.0.0_historical.md),
  raw SHA-256
  `9f39a94e5b1735176eafc6c0a14f3d712de96d703370ab505a5eb96ca5017667`.
- Frozen specification:
  [`V8_fixed_recurrence_harmonic.md`](V8_fixed_recurrence_harmonic.md).

The only scored lane contains 621 targets from 2020-01-01 through
2025-12-31. The entire interval is **consumed historical diagnostic evidence**:
it is not blind, validation, confirmatory, or prospective evidence, and it can
never be relabeled as such. Development and legacy-validation are not
applicable to this post-RNG hypothesis and were not scored. Every 2026+ outcome
already observed before a changed candidate is frozen is likewise consumed for
that changed candidate; none may be backfilled into a prospective cohort.

## Candidate results

Fair per-draw expectations are `36/49 = 0.7346938775510204` for Top-6,
`72/49 = 1.4693877551020409` for Top-12, and
`108/49 = 2.204081632653061` for Top-18. Positive hit-count lift is favorable.
Lower Brier score, log loss, and actual rank are favorable. A positive
proper-score delta means worse performance than the fair constant baseline.

### Ranking and primary inference

| Scope | Draws | Top-6 mean | Top-6 lift | Top-12 mean | Top-12 lift | Top-18 mean | Top-18 lift | Total Top-12 | Exact one-sided p | Holm p | 95% bootstrap CI for Top-12 lift |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Aggregate, 2020-2025 | 621 | 0.7085346215780999 | -0.02615925597292057 | 1.4524959742351047 | -0.016891780866936212 | 2.154589371980676 | -0.04949226067238488 | 902 | 0.6700938237435888 | 0.6700938237435888 | [-0.08935554898287834, 0.05883285681422251] |
| Fixed half 1, 2020-2022 | 307 | 0.7003257328990228 | -0.03436814465199767 | 1.4299674267100977 | -0.039420328391943205 | 2.1433224755700326 | -0.06075915708302837 | 439 | 0.7641105277179469 | n/a | [-0.14365485607923967, 0.06807152828558127] |
| Fixed half 2, 2023-2025 | 314 | 0.7165605095541401 | -0.018133367996880367 | 1.4745222929936306 | 0.0051345378915896855 | 2.1656050955414012 | -0.03847653711165977 | 463 | 0.4733977866921009 | n/a | [-0.09996100350968429, 0.11023007929286366] |

All three aggregate Top-K point estimates were below fair theory. The second
half had a small positive Top-12 point estimate, but its interval included zero
and the first-half lift was negative. This sign instability cannot rescue the
negative aggregate primary result.

### Proper scores, actual rank, and activation

The exact fair-constant reference is Brier `0.10745522698875469` and log loss
`0.37177617994345286` in every scope. The frozen gate requires both deltas to be
at most `1e-9` in the aggregate and each fixed half.

| Scope | Brier | Brier delta vs fair | Log loss | Log-loss delta vs fair | Mean actual rank | Active / targets | Fair fallback |
|---|---:|---:|---:|---:|---:|---:|---:|
| Aggregate, 2020-2025 | 0.10747373619300349 | 0.000018509204248798317 | 0.3718619687380382 | 0.00008578879458531752 | 25.163177670424044 | 582 / 621 | 39 |
| Fixed half 1, 2020-2022 | 0.10749518125407802 | 0.000039954265323327576 | 0.3719616406214411 | 0.00018546067798824728 | 25.435939196525517 | 268 / 307 | 39 |
| Fixed half 2, 2023-2025 | 0.10745276920653883 | -0.0000024577822158589058 | 0.3717645188392972 | -0.000011661104155680224 | 24.89649681528663 | 314 / 314 | 0 |

The second-half proper scores were better than the fair constant, but the
aggregate and first-half deltas were positive and exceeded the registered
`1e-9` tolerance. The conjunction therefore fails. The frozen 104-prior-draw
activation rule produced 39 fair-fallback targets and 582 active targets; the
first active target was 2020-05-20. These counts are integrity facts, not an
alternate active-only subgroup, and no active-only score is permitted.

## Registered negative controls

The row control, `v8_spectral_phase_row_control v8.0.0`, permutes each strict
post-RNG history prefix as complete six-main-plus-bonus rows while leaving the
target unchanged. The phase control,
`v8_spectral_phase_rotation_control v8.0.0`, rotates each label's spectral
phase inside the same strict prefixes. Under the registered null rule, a
control behaves as null when its raw p-value is greater than `0.05` **or** its
bootstrap interval includes zero. Both controls met that definition in the
aggregate and both fixed halves.

### Control ranking and primary inference

| Scope | Control | Draws | Top-6 mean (lift) | Top-12 mean (lift) | Top-18 mean (lift) | Total Top-12 | Exact one-sided p | 95% bootstrap CI for Top-12 lift | Null |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
| Aggregate, 2020-2025 | Row permutation | 621 | 0.789049919484702 (0.0543560419336816) | 1.534621578099839 (0.06523382299779801) | 2.2801932367149758 (0.07611160406191475) | 953 | 0.054107340966030364 | [-0.008840251076275951, 0.1425285089881363] | yes |
| Fixed half 1, 2020-2022 | Row permutation | 307 | 0.752442996742671 (0.017749119191650564) | 1.498371335504886 (0.0289835804028451) | 2.263843648208469 (0.059762015555408166) | 460 | 0.31430196799960197 | [-0.07525094728445136, 0.1397327660705976] | yes |
| Fixed half 2, 2023-2025 | Row permutation | 314 | 0.8248407643312102 (0.09014688678018978) | 1.570063694267516 (0.10067593916547501) | 2.2961783439490446 (0.09209671129598362) | 493 | 0.0397586888766534 | [-0.007604315611595025, 0.205771480566749] | yes |
| Aggregate, 2020-2025 | Phase rotation | 621 | 0.7326892109500805 (-0.0020046666009398972) | 1.4508856682769726 (-0.018502086825068265) | 2.1497584541062804 (-0.05432317854678059) | 901 | 0.6845723398581931 | [-0.09579677281540633, 0.0587925991652698] | yes |
| Fixed half 1, 2020-2022 | Phase rotation | 307 | 0.7947882736156352 (0.06009439606461475) | 1.504885993485342 (0.03549823838330113) | 2.208469055374593 (0.0043874227215319195) | 462 | 0.27501423323511803 | [-0.07850827627467938, 0.14950475304128164] | yes |
| Fixed half 2, 2023-2025 | Phase rotation | 314 | 0.6719745222929936 (-0.06271935525802685) | 1.3980891719745223 (-0.07129858312751858) | 2.0923566878980893 (-0.11172494475497174) | 439 | 0.9028998532570208 | [-0.17957883790458862, 0.03698167164955146] | yes |

The row control's second-half raw p-value was below `0.05`, but its registered
two-sided interval included zero, so it still met the pre-registered disjunctive
null definition. This descriptive control result is not predictive evidence.

### Control proper scores

| Scope | Control | Brier | Brier delta vs fair | Log loss | Log-loss delta vs fair | Mean actual rank |
|---|---|---:|---:|---:|---:|---:|
| Aggregate, 2020-2025 | Row permutation | 0.10744746253436945 | -0.00000776445438524509 | 0.3717398826664744 | -0.00003629727697845864 | 24.61567364465915 |
| Fixed half 1, 2020-2022 | Row permutation | 0.1074596760571819 | 0.000004449068427211933 | 0.3717960764954704 | 0.00001989655201756202 | 24.8099891422367 |
| Fixed half 2, 2023-2025 | Row permutation | 0.10743552128754319 | -0.000019705701211500393 | 0.3716849415661502 | -0.00009123837730268258 | 24.425690021231425 |
| Aggregate, 2020-2025 | Phase rotation | 0.10745724909237127 | 0.0000020221036165779527 | 0.37178453398788597 | 0.000008354044433112051 | 24.924315619967793 |
| Fixed half 1, 2020-2022 | Phase rotation | 0.10744564899541875 | -0.000009577993335938007 | 0.3717300874450104 | -0.00004609249844245156 | 24.528773072747015 |
| Fixed half 2, 2023-2025 | Phase rotation | 0.10746859058843633 | 0.000013363599681640026 | 0.371837766754328 | 0.00006158681087514717 | 25.311040339702757 |

## Paired candidate-minus-row-control diagnostic

The direct row-control gate used exactly 10,000 paired candidate-row bootstrap
resamples from `numpy.default_rng(649)`. It required the lower endpoint to be
strictly above zero in the aggregate and both fixed halves.

| Scope | Draws | Mean candidate minus row-control Top-12 hits | Paired 95% CI |
|---|---:|---:|---|
| Aggregate, 2020-2025 | 621 | -0.0821256038647343 | [-0.18679549114331723, 0.020933977455716585] |
| Fixed half 1, 2020-2022 | 307 | -0.06840390879478828 | [-0.21172638436482086, 0.06840390879478828] |
| Fixed half 2, 2023-2025 | 314 | -0.09554140127388536 | [-0.2515923566878981, 0.06369426751592357] |

Every point estimate favored the row control and every interval had a negative
lower endpoint. The candidate therefore fails the direct row-control gate in
all three scopes.

## Frozen gate decision

| Registered JSON gate | Result | Evidence |
|---|---|---|
| `positive_aggregate_primary_lift` | **Fail** | `-0.016891780866936212` |
| `aggregate_holm_adjusted_p_at_most_0_05` | **Fail** | `0.6700938237435888` |
| `aggregate_bootstrap_lower_above_zero` | **Fail** | `-0.08935554898287834` |
| `positive_primary_lift_in_both_fixed_halves` | **Fail** | First half `-0.039420328391943205`; second half `0.0051345378915896855` |
| `proper_scores_within_fair_tolerance_aggregate_and_halves` | **Fail** | Aggregate and first-half Brier/log-loss deltas exceed `1e-9` |
| `row_control_null_and_candidate_outperforms_it` | **Fail** | Row control is null, but paired lower endpoints are `-0.18679549114331723`, `-0.21172638436482086`, and `-0.2515923566878981` |
| `phase_control_null_aggregate_and_halves` | Pass | All three phase-control intervals include zero |
| `audit_clear` | Pass | Empty warning list; Git, data-boundary, fold-prefix, and one-shot checks passed |

Only two of eight gates pass. Because the registered decision is a conjunction,
`all_gates_passed` is `false`, `historical_primary_signal_supported` is
`false`, and the valid decision is **Reject**. Prospective/shadow status is
exactly **`not_activated`**.

## Fixed comparison context

The descriptive comparison set retained exact fair theory, deterministic
random, all V1 production baselines and their ensemble, V3 shadow, rejected V5,
rejected V6, rejected V7, and V8. The complete Top-6, Top-12, Top-18, Brier,
log-loss, and actual-rank summaries remain in the machine-readable report. The
V1 through V7 summaries were reused from the frozen V7 report on the identical
621 targets and did not enter a V8 gate, select a variant, refit a model, or
alter an operational role.

For context, V8's aggregate Top-12 mean `1.4524959742351047` was below fair
theory, deterministic random, V3, V5, V6, and V7. Its aggregate Brier and log
loss were also worse than the exact fair constant. This consumed historical
ordering does not establish predictability and cannot be used to tune and
re-present a changed harmonic as confirmatory evidence.

## Consequences

`v8.0.0` is closed as **Reject**. It must not be added to `config.yaml`, must
not produce live or shadow snapshots, and has no eligible prospective
observation. No existing prediction snapshot is modified or regenerated by
this decision. V1 remains production and V3 remains shadow.

The permanent one-shot claim proves that this frozen historical diagnostic has
already been consumed. It must not be deleted, bypassed, renamed, or otherwise
used to run `v8.0.0` again. The result may not be rescued by changing features,
frequency, phase, activation counts, dates, halves, weights, constraints,
metrics, controls, seeds, or gates and presenting the new answer as a
same-version blind or confirmatory test.

Any hypothesis or implementation changed after these results were observed
must have a new model version, a new pre-registration and freeze, and a new
prospective cohort beginning only after a separate reviewed activation
decision. The complete 2020-2025 result and every observed 2026+ outcome that
influences that change are consumed for the changed candidate. Negative
attempts remain in the multiplicity ledger; a new variant cannot erase or
relabel this result.
