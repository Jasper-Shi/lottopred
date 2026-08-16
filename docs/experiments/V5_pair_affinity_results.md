# V5 Pair-Affinity Result and Decision Record

## Decision

**Reject `v5_pair_affinity` version `v5.0.0`. Do not activate it as a
shadow model.** V1 remains the production-baseline suite and V3 remains the
only research shadow model; their operational roles are unchanged.

The frozen candidate did not support its registered primary hypothesis in any
lane. Each one-sided exact Top-12 p-value (and, with one recorded family
variant, each Holm-adjusted p-value) is greater than `0.05`, every registered
95% bootstrap interval includes zero, and both proper scores are worse than the
fair constant baseline in every lane. The intact-draw date-permutation control
behaved as a null in all three lanes, so it raises no pipeline warning.

This is a valid negative research result, not evidence that a predictive model
has been found and not proof of the null. No candidate parameters, features,
windows, weights, constraints, or comparisons were changed after the results
were read.

## Audit identity and evidence boundary

- Experiment: `V5_pair_affinity`; family: `v5_pair_cooccurrence`; family size:
  `1`.
- Candidate: `v5_pair_affinity`; version: `v5.0.0`.
- Frozen candidate implementation: commit
  `f51a3b59e857f6c3a5d9c0502a0c30e71d15d3b4` (`f51a3b5`).
- Registered-prefix preservation infrastructure: commit
  `f3b0711864d11ce86a7f0683e15e0ceca2df468f` (`f3b0711`). This follow-up
  infrastructure change does not alter the frozen candidate specification.
- Dataset: [`data/processed/draws.csv`](../../data/processed/draws.csv), 4,431
  draws through 2026-08-12, SHA-256
  `95434535857a95f3ae9bd25e42345291274804702ed514b0bace6fafcf584bdf`,
  source commit `39b99a9e0a6351b4143f81c9a95eb1639456a35d`.
- Reproduction command:
  `lotto649 --config config/research-v5-pair-affinity.yaml research-v5 --code-commit f51a3b59e857f6c3a5d9c0502a0c30e71d15d3b4`.
- Research configuration:
  [`config/research-v5-pair-affinity.yaml`](../../config/research-v5-pair-affinity.yaml),
  raw SHA-256
  `b89a74aa353fda9891a011edfa44a4d0a6d99edb8477ed803a176ef8fa035550`,
  effective canonical SHA-256
  `83553c57c8dd76dce7a8272e59f5047ba2e129c5b438028b4c120c2b37899676`.
- Machine-readable report:
  [`reports/v5_pair_affinity_v5.0.0_historical.json`](../../reports/v5_pair_affinity_v5.0.0_historical.json).
- Compact generated report:
  [`reports/v5_pair_affinity_v5.0.0_historical.md`](../../reports/v5_pair_affinity_v5.0.0_historical.md).
- Frozen specification:
  [`docs/experiments/V5_pair_affinity.md`](V5_pair_affinity.md).

After scoring completed, the reports were augmented with the frozen registered
parameters, full effective research configuration, comparison list, and both
configuration hashes required by the reporting protocol. No score was
recomputed or changed; the report generator now emits the same manifest on
reproduction.

All reported lanes are historical diagnostics. None is blind, confirmatory, or
prospective. The 2020-2025 lane is consumed V2-V4 blind-period data and is
reported only as a consumed historical diagnostic. Every 2026 result available
before the candidate freeze is also consumed for `v5.0.0`; the generated report
does not score a 2026 prospective lane. The prospective cohort was never
activated.

## Candidate results

Fair per-draw expectations are `36/49 = 0.7346938776` for Top-6,
`72/49 = 1.4693877551` for Top-12, and `108/49 = 2.2040816327` for Top-18.
Positive hit-count lift is favorable. Lower Brier score, log loss, and actual
rank are favorable. A positive proper-score delta means worse performance than
the fair constant baseline.

### Ranking and primary inference

| Lane | Eligible draws | Excluded (<300 history) | Top-6 mean (lift) | Top-12 mean (lift) | Top-18 mean (lift) | Exact one-sided p | Holm p | 95% bootstrap CI for Top-12 lift |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Development, 1982-2014 | 2,926 | 300 | 0.746753247 (+0.012059369) | 1.477443609 (+0.008055854) | 2.192412850 (-0.011668782) | 0.334025225 | 0.334025225 | [-0.028171077, +0.044282785] |
| Legacy validation, 2015-2019 | 520 | 0 | 0.715384615 (-0.019309262) | 1.403846154 (-0.065541601) | 2.140384615 (-0.063697017) | 0.936384804 | 0.936384804 | [-0.155926217, +0.024843014] |
| Consumed diagnostic, 2020-2025 | 621 | 0 | 0.785829308 (+0.051135430) | 1.494363929 (+0.024976174) | 2.201288245 (-0.002793388) | 0.272298253 | 0.272298253 | [-0.052318512, +0.103881166] |

The corresponding total Top-12 hits are 4,323, 730, and 928. No lane has an
adjusted p-value at or below `0.05`, and no interval has a lower endpoint above
zero. The development and consumed lanes have small positive point estimates,
while the exposed legacy-validation lane has a negative point estimate; none is
eligible to be relabeled as confirmation.

### Proper scores and actual rank

The exact fair-constant reference is Brier `0.10745522698875469` and log loss
`0.37177617994345286` in every lane.

| Lane | Brier | Brier delta vs fair | Log loss | Log-loss delta vs fair | Mean actual rank |
|---|---:|---:|---:|---:|---:|
| Development, 1982-2014 | 0.107617599 | +0.000162372 | 0.372544163 | +0.000767983 | 25.097288676 |
| Legacy validation, 2015-2019 | 0.107647499 | +0.000192272 | 0.372669755 | +0.000893575 | 25.110576923 |
| Consumed diagnostic, 2020-2025 | 0.107594118 | +0.000138891 | 0.372442620 | +0.000666440 | 25.035695115 |

Both registered proper scores are worse than the fair constant in all three
lanes. The candidate therefore provides no calibration-based reason to override
the failed primary gate.

## Registered negative control

The sole registered control assigns intact whole-draw outcomes to fixed dates by
the deterministic seed-649 permutation and then runs the same strict-prefix
walk-forward pipeline. `Null = yes` means the control failed the candidate's
positive gate, as required; it does not mean the control supports a prediction
claim.

### Control ranking and primary inference

| Lane | Draws | Top-6 mean (lift) | Top-12 mean (lift) | Top-18 mean (lift) | Exact one-sided p | Holm p | 95% bootstrap CI for Top-12 lift | Null |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Development, 1982-2014 | 2,926 | 0.710184552 (-0.024509325) | 1.466165414 (-0.003222342) | 2.216336295 (+0.012254663) | 0.572563701 | 0.572563701 | [-0.039791036, +0.032671370] | yes |
| Legacy validation, 2015-2019 | 520 | 0.761538462 (+0.026844584) | 1.498076923 (+0.028689168) | 2.313461538 (+0.109379906) | 0.262399080 | 0.262399080 | [-0.054003140, +0.111381476] | yes |
| Consumed diagnostic, 2020-2025 | 621 | 0.755233494 (+0.020539617) | 1.508856683 (+0.039468928) | 2.238325282 (+0.034243649) | 0.166867432 | 0.166867432 | [-0.041046370, +0.118373920] | yes |

### Control proper scores and actual rank

| Lane | Brier | Brier delta vs fair | Log loss | Log-loss delta vs fair | Mean actual rank |
|---|---:|---:|---:|---:|---:|
| Development, 1982-2014 | 0.107624171 | +0.000168944 | 0.372545579 | +0.000769399 | 25.023125997 |
| Legacy validation, 2015-2019 | 0.107480392 | +0.000025165 | 0.371873667 | +0.000097487 | 24.433974359 |
| Consumed diagnostic, 2020-2025 | 0.107569334 | +0.000114107 | 0.372306588 | +0.000530408 | 24.829844337 |

All three control p-values exceed `0.05`, all three intervals include zero, and
the control's proper scores are worse than fair in all three lanes. The control
therefore behaves as the registered null and raises no leakage/pipeline warning.

## Complete frozen operational comparison set

These comparisons are descriptive and use identical target dates. They neither
replace the fair primary null nor select a candidate variant. The table retains
the complete fixed set: deterministic random, every V1 production baseline and
ensemble, V3 shadow, and V5 candidate.

| Lane | Model (version) | Top-6 | Top-12 | Top-18 | Brier | Log loss | Mean actual rank |
|---|---|---:|---:|---:|---:|---:|---:|
| Development | random (`v1.0.0`) | 0.762816131 | 1.470608339 | 2.203691046 | 0.107455227 | 0.371776180 | 25.032638414 |
| Development | long_frequency (`v1.0.0`) | 0.759740260 | 1.498291183 | 2.193779904 | 0.107509418 | 0.372030939 | 24.996069720 |
| Development | recent_frequency (`v1.0.0`) | 0.752221463 | 1.491797676 | 2.223171565 | 0.107835309 | 0.373579408 | 24.963830030 |
| Development | ema_gap (`v1.0.0`) | 0.750170882 | 1.493506494 | 2.232057416 | 0.108567345 | 0.376754458 | 24.848370927 |
| Development | logistic (`v1.0.0`) | 0.742993848 | 1.496924129 | 2.232399180 | 0.107655125 | 0.372716536 | 24.941216678 |
| Development | ensemble (`v1.0.0`) | 0.751196172 | 1.502050581 | 2.236842105 | 0.107598124 | 0.372437017 | 24.878389155 |
| Development | v3_boosting (`v1.0.0`) | 0.723855092 | 1.464114833 | 2.207108681 | 0.109543628 | 0.380484552 | 24.977386648 |
| Development | v5_pair_affinity (`v5.0.0`) | 0.746753247 | 1.477443609 | 2.192412850 | 0.107617599 | 0.372544163 | 25.097288676 |
| Legacy validation | random (`v1.0.0`) | 0.863461538 | 1.586538462 | 2.317307692 | 0.107455227 | 0.371776180 | 24.466346154 |
| Legacy validation | long_frequency (`v1.0.0`) | 0.732692308 | 1.500000000 | 2.259615385 | 0.107465090 | 0.371818780 | 24.780769231 |
| Legacy validation | recent_frequency (`v1.0.0`) | 0.688461538 | 1.407692308 | 2.175000000 | 0.107898720 | 0.373838091 | 25.203205128 |
| Legacy validation | ema_gap (`v1.0.0`) | 0.713461538 | 1.432692308 | 2.198076923 | 0.108704331 | 0.377399759 | 25.125320513 |
| Legacy validation | logistic (`v1.0.0`) | 0.719230769 | 1.496153846 | 2.234615385 | 0.107667628 | 0.372771350 | 24.916346154 |
| Legacy validation | ensemble (`v1.0.0`) | 0.717307692 | 1.430769231 | 2.153846154 | 0.107597088 | 0.372429172 | 25.150320513 |
| Legacy validation | v3_boosting (`v1.0.0`) | 0.767307692 | 1.459615385 | 2.215384615 | 0.109437401 | 0.380069572 | 24.880128205 |
| Legacy validation | v5_pair_affinity (`v5.0.0`) | 0.715384615 | 1.403846154 | 2.140384615 | 0.107647499 | 0.372669755 | 25.110576923 |
| Consumed diagnostic | random (`v1.0.0`) | 0.776167472 | 1.470209340 | 2.223832528 | 0.107455227 | 0.371776180 | 24.633655395 |
| Consumed diagnostic | long_frequency (`v1.0.0`) | 0.702093398 | 1.429951691 | 2.177133655 | 0.107500788 | 0.371986183 | 25.213902308 |
| Consumed diagnostic | recent_frequency (`v1.0.0`) | 0.703703704 | 1.384863124 | 2.096618357 | 0.107921851 | 0.373952417 | 25.394524960 |
| Consumed diagnostic | ema_gap (`v1.0.0`) | 0.719806763 | 1.412238325 | 2.101449275 | 0.108918337 | 0.378360733 | 25.418679549 |
| Consumed diagnostic | logistic (`v1.0.0`) | 0.681159420 | 1.446054750 | 2.243156200 | 0.107685320 | 0.372837339 | 25.136339238 |
| Consumed diagnostic | ensemble (`v1.0.0`) | 0.682769726 | 1.397745572 | 2.146537842 | 0.107682585 | 0.372814454 | 25.519323671 |
| Consumed diagnostic | v3_boosting (`v1.0.0`) | 0.758454106 | 1.521739130 | 2.231884058 | 0.109406240 | 0.380001354 | 24.924584004 |
| Consumed diagnostic | v5_pair_affinity (`v5.0.0`) | 0.785829308 | 1.494363929 | 2.201288245 | 0.107594118 | 0.372442620 | 25.035695115 |

The comparison set is mixed across metrics and eras. V5 trails every non-random
V1 reference on development Top-12, trails the entire fixed comparison set on
legacy-validation Top-12, and trails V3 on consumed-diagnostic Top-12. It exceeds
several V1 Top-12 point estimates in the consumed lane, but that already-consumed
result is non-significant and cannot establish the registered signal. Across all
lanes, every non-random model shown also has worse proper scores than the fair
constant baseline; headline ranking fluctuations therefore do not establish
stable predictive probabilities.

## Consequences

`v5.0.0` is closed as **Reject**. It must not be added to `config.yaml`, must not
produce live or shadow snapshots, and has no eligible prospective observation.
No existing prediction snapshot is modified or regenerated by this decision.

Any new hypothesis inspired by these observed results must be pre-registered as
a statistically distinct model version before implementation. All history used
here, all 2020-2025 outcomes, and any already-observed 2026+ outcomes are consumed
for that changed candidate. A changed candidate must freeze a new version and
begin a new prospective cohort from its first immutable pre-draw snapshot; it
cannot inherit or relabel evidence from `v5.0.0`.
