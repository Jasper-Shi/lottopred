# V6 Fixed-Boundary Entropy-Regime Result and Decision Record

## Decision

**Reject `v6_entropy_regime` version `v6.0.0`. Do not activate it as a
shadow model.** V1 remains the production-baseline suite and V3 remains the
only research shadow model; their operational roles are unchanged.

The frozen candidate failed four of its six registered historical gates. Its
development Top-12 lift was negative, so lift was not positive in all three
lanes. In the sole registered historical gate lane, the consumed 2020-2025 period,
the Holm-adjusted exact p-value was `0.498761088`, and the 95% bootstrap interval
included zero. Development Brier and log-loss deltas also exceeded the frozen
`1e-9` tolerance. The registered negative control behaved as a null in all three
lanes, data-boundary verification passed, and the report contains no audit
warning.

This is a valid negative research result. It is not evidence that a predictive
lottery model has been found, and it is not proof of the null. No feature,
window, gate, coefficient, mapping, control, comparison, or decision rule was
changed after the single frozen historical diagnostic was read.

## Audit identity and evidence boundary

- Experiment: `V6_fixed_boundary_js_regime`; family: `entropy_regime`; family
  size: `1`.
- Candidate: `v6_entropy_regime`; version: `v6.0.0`.
- Frozen implementation commit:
  `591b6173aa3a2e711d2c5e5e7f9cc3f8c7801bf6` (`591b617`).
- Exact command:
  `lotto649 --config config/research-v6-entropy-regime.yaml research-v6 --code-commit 591b6173aa3a2e711d2c5e5e7f9cc3f8c7801bf6`.
- Historical-diagnostic dataset: [`data/processed/draws.csv`](../../data/processed/draws.csv),
  4,431 draws through 2026-08-12, raw SHA-256
  `95434535857a95f3ae9bd25e42345291274804702ed514b0bace6fafcf584bdf`,
  source commit `39b99a9e0a6351b4143f81c9a95eb1639456a35d`.
- Outcomes known at registration: 4,432 draws through 2026-08-15, raw
  SHA-256
  `edfb7f8a4a7711a630957d6f86b567e6b254caf7b1d1aaea0edf1d16a34155b3`,
  source commit `90177c80cfb070038d79508fb2e73305a297f516`.
- Git data-boundary verification passed, the registered prefix was preserved,
  and the known-outcomes fingerprint is
  `257aef242bb898649b0923ac03f2271c7536ff7f840edf552c0dc6b4b03ce1dd`.
- Research configuration:
  [`config/research-v6-entropy-regime.yaml`](../../config/research-v6-entropy-regime.yaml),
  raw SHA-256
  `072fb97d1280939bd88d6d00829a2c3bf407c1f02979f3eb00a330b033473177`,
  effective canonical SHA-256
  `608081dd74240f71519c5e85e8f326c25910a6baaaac56c6e906cc1f7d76ff8d`.
- Reused frozen V5 reference:
  [`reports/v5_pair_affinity_v5.0.0_historical.json`](../../reports/v5_pair_affinity_v5.0.0_historical.json),
  raw SHA-256
  `b86391ada265d96f94e789f4962812d32771385702e2efa2285cb9ef96d5d6bb`.
  Its summaries were reused on identical target dates; reference models were
  not refitted.
- Machine-readable result:
  [`reports/v6_entropy_regime_v6.0.0_historical.json`](../../reports/v6_entropy_regime_v6.0.0_historical.json),
  raw SHA-256
  `12400a4b5164b030225827d47a8024a1ec7aeaeb32fa64cd2fab0b46ff8d4c2a`.
- Compact generated result:
  [`reports/v6_entropy_regime_v6.0.0_historical.md`](../../reports/v6_entropy_regime_v6.0.0_historical.md),
  raw SHA-256
  `cd842403041a166a3996ab982a987a3871a7039aaf4d600f73b9c6e4dc4aec80`.
- Frozen specification: [`V6_entropy_regime.md`](V6_entropy_regime.md).

All three evaluated lanes are consumed historical diagnostics. Development and
legacy-validation results were already exposed to research, and 2020-2025 is
the consumed V2-V4 blind period. None is blind, confirmatory, prospective, or
eligible for relabeling. Outcomes known before any future activation are also
consumed for `v6.0.0`. No prospective cohort was activated and the report does
not score a prospective lane.

## Candidate results

Fair per-draw expectations are `36/49 = 0.7346938776` for Top-6,
`72/49 = 1.4693877551` for Top-12, and `108/49 = 2.2040816327` for Top-18.
Positive hit-count lift is favorable. Lower Brier score, log loss, and actual
rank are favorable. A positive proper-score delta means worse performance than
the fair constant baseline.

### Ranking and primary inference

| Lane | Eligible draws | Excluded (<300 history) | Top-6 mean (lift) | Top-12 mean (lift) | Top-18 mean (lift) | Total Top-12 | Exact one-sided p | Holm p | 95% bootstrap CI for Top-12 lift |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Development, 1982-2014 | 2,926 | 300 | 0.761107314 (+0.026413436) | 1.467874231 (-0.001513524) | 2.200956938 (-0.003124695) | 4,295 | 0.535919519 | n/a | [-0.037740455, +0.034371643] |
| Legacy validation, 2015-2019 | 520 | 0 | 0.863461538 (+0.128767661) | 1.586538462 (+0.117150706) | 2.317307692 (+0.113226060) | 825 | 0.004139020 | n/a | [+0.032535322, +0.203737245] |
| Consumed diagnostic, 2020-2025 | 621 | 0 | 0.776167472 (+0.041473594) | 1.470209340 (+0.000821585) | 2.223832528 (+0.019750896) | 913 | 0.498761088 | 0.498761088 | [-0.078083407, +0.078116271] |

Only the consumed-diagnostic p-value was the pre-registered historical Holm
gate. The legacy-validation point estimate and raw p-value are exposed
historical diagnostics, not an alternate discovery test. They are especially
uninformative about the proposed gated regime mechanism because that mechanism
was inactive on all 520 legacy-validation targets. The development primary
point estimate is negative, and the consumed registered-gate interval includes
zero, so the hypothesis does not have stable support across the registered
lanes.

### Proper scores and actual rank

The exact fair-constant reference is Brier `0.10745522698875469` and log loss
`0.37177617994345286` in every lane. The registered tolerance requires each
candidate delta to be at most `1e-9` in every lane.

| Lane | Brier | Brier delta vs fair | Log loss | Log-loss delta vs fair | Mean actual rank |
|---|---:|---:|---:|---:|---:|
| Development, 1982-2014 | 0.107458984425 | +0.000003757436 | 0.371794553623 | +0.000018373680 | 25.065105947 |
| Legacy validation, 2015-2019 | 0.107455226988 | -5.84255e-13 | 0.371776179941 | -2.71860e-12 | 24.466346154 |
| Consumed diagnostic, 2020-2025 | 0.107455226988 | -4.03705e-13 | 0.371776179942 | -1.87844e-12 | 24.633655395 |

Legacy and consumed deltas are only floating-point-scale differences around the
fair constant and satisfy the tolerance. Development fails both proper-score
limits. Proper scoring therefore does not rescue the failed primary gate.

### Frozen-regime activation

| Lane | Eligible targets | Active | Inactive | Activation rate |
|---|---:|---:|---:|---:|
| Development, 1982-2014 | 2,926 | 44 | 2,882 | 0.015037594 |
| Legacy validation, 2015-2019 | 520 | 0 | 520 | 0.000000000 |
| Consumed diagnostic, 2020-2025 | 621 | 0 | 621 | 0.000000000 |

Activation counts are descriptive only; the pre-registration forbids
active-only scoring. The candidate's change-regime mapping was active on just
44 development targets and none in either later lane. In inactive folds it is
fair apart from the frozen, outcome-independent tie-break jitter. Thus the
positive legacy-validation ranking fluctuation cannot establish continuation
of a detected regime.

## Registered negative control

The sole registered control applies a deterministic seed-649 intact whole-draw
date permutation and runs the same complete V6 walk-forward pipeline. It is
consistent with the registered null when its raw primary `p > 0.05` or its 95%
bootstrap interval includes zero. A null control is required pipeline evidence;
it never supports a prediction claim.

### Control ranking and primary inference

| Lane | Draws | Top-6 mean (lift) | Top-12 mean (lift) | Top-18 mean (lift) | Total Top-12 | Exact one-sided p | 95% bootstrap CI for Top-12 lift | Null |
|---|---:|---:|---:|---:|---:|---:|---|
| Development, 1982-2014 | 2,926 | 0.721804511 (-0.012889366) | 1.451811347 (-0.017576409) | 2.165755297 (-0.038326335) | 4,248 | 0.832181464 | [-0.053119813, +0.017966995] | yes |
| Legacy validation, 2015-2019 | 520 | 0.725000000 (-0.009693878) | 1.436538462 (-0.032849294) | 2.196153846 (-0.007927786) | 747 | 0.779992663 | [-0.117464678, +0.055612245] | yes |
| Consumed diagnostic, 2020-2025 | 621 | 0.758454106 (+0.023760229) | 1.458937198 (-0.010450557) | 2.188405797 (-0.015675836) | 906 | 0.609822649 | [-0.089355549, +0.068454435] | yes |

No control p-value is at or below `0.05`, and every interval includes zero. All
three controls therefore behave as the registered null and raise no
leakage/pipeline warning.

### Control proper scores, actual rank, and activation

| Lane | Brier (delta vs fair) | Log loss (delta vs fair) | Mean actual rank | Active / eligible (rate) |
|---|---:|---:|---:|---:|
| Development, 1982-2014 | 0.107460800982 (+0.000005573993) | 0.371798239619 (+0.000022059676) | 25.191273639 | 65 / 2,926 (0.022214627) |
| Legacy validation, 2015-2019 | 0.107469481225 (+0.000014254236) | 0.371848851449 (+0.000072671506) | 24.975641026 | 20 / 520 (0.038461538) |
| Consumed diagnostic, 2020-2025 | 0.107466804637 (+0.000011577648) | 0.371831997989 (+0.000055818046) | 25.120772947 | 10 / 621 (0.016103059) |

## Frozen gate decision

| Registered gate | Result | Evidence |
|---|---|---|
| Positive primary lift in all three lanes | **Fail** | Development lift `-0.001513524` |
| Consumed Holm-adjusted exact p <= 0.05 | **Fail** | `0.498761088` |
| Consumed bootstrap lower endpoint > 0 | **Fail** | Lower endpoint `-0.078083407` |
| Brier and log-loss deltas <= 1e-9 in every lane | **Fail** | Development deltas `+3.75744e-6` and `+1.83737e-5` |
| Negative control null in every lane | Pass | All raw p-values > `0.05`; all intervals include zero |
| Audit clear | Pass | Empty warning list; Git boundary checks passed |

The conjunction fails, so the only registered valid decision is **Reject**.
Historical primary signal support is `false`; shadow activation is
`not_activated`.

## Fixed comparison context

The fixed comparison set was exact fair theory, deterministic random, all V1
production baselines and their ensemble, V3 shadow, rejected V5, and V6. The
complete Top-6/Top-12/Top-18, Brier, log-loss, and actual-rank summaries for
every model and lane remain in the machine-readable report linked above. They
are descriptive and cannot replace the fair primary null or select a variant.

V6's mean Top-12 result was `1.467874231`, `1.586538462`, and `1.470209340`
across development, legacy validation, and consumed diagnostic. The legacy and
consumed values also exactly match the deterministic-random ranking summaries
on those target dates. V6 never crossed its regime gate in either lane, so
those V6 values reflect its frozen outcome-independent inactive ranking rather
than evidence for the proposed active regime mechanism.
V6 trailed V3 and V5 on consumed-diagnostic Top-12, while several V1 point
estimates were lower. This mixed, already-consumed comparison pattern does not
change the frozen rejection decision or establish stable predictability.

## Consequences

`v6.0.0` is closed as **Reject**. It must not be added to `config.yaml`, must not
produce live or shadow snapshots, and has no eligible prospective observation.
No existing prediction snapshot is modified or regenerated by this decision.
V1 remains the production baseline and V3 remains shadow.

Any hypothesis or implementation changed after these results were observed
must use a new model version and begin a new prospective cohort after a separate
pre-registration, freeze, and reviewed shadow-activation decision. It cannot
inherit `v6.0.0` evidence. All history reported here, the consumed 2020-2025
period, and every already-observed 2026+ result that influences the change are
consumed for that changed candidate.
