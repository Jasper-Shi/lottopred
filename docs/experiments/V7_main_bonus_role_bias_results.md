# V7 Post-RNG Main/Bonus Role-Bias Result and Decision Record

## Decision

**Reject `v7_main_bonus_role_bias` version `v7.0.0`. Do not activate it as a
shadow model.** V1 remains the production-baseline suite and V3 remains the
only research shadow model; their operational roles are unchanged.

The single frozen historical diagnostic produced a small positive aggregate
Top-12 lift, but failed five of the eight jointly required gates. The
Holm-adjusted exact p-value was `0.372656874`, the aggregate bootstrap interval
included zero, the first fixed half had negative Top-12 lift, every candidate
Brier and log-loss delta was worse than the fair constant by more than the
registered `1e-9` tolerance, and the global role audit had p-value
`0.570742926`. The registered negative control behaved as a null in the
aggregate and both halves, and the audit-warning list was empty.

This is a valid negative research result. It is not evidence that a predictive
lottery model has been found, and it is not proof of the null. No feature,
pseudo-count, activation boundary, solver parameter, metric, control, split,
comparison, or decision rule may be changed and then re-evaluated as
`v7.0.0`.

## Audit identity and evidence boundary

- Experiment: `V7_post_rng_main_bonus_role_bias`; multiplicity family:
  `draw_role_exchangeability`; variant and family size: `1`.
- Candidate: `v7_main_bonus_role_bias`; version: `v7.0.0`.
- Frozen implementation commit:
  `180cd045e7797b95db4226f7d79d66d6ee9a5965` (`180cd04`).
- Exact command:
  `lotto649 --config config/research-v7-main-bonus-role-bias.yaml research-v7 --code-commit 180cd045e7797b95db4226f7d79d66d6ee9a5965`.
- Permanent one-shot claim:
  [`reports/v7_main_bonus_role_bias_v7.0.0_historical.claim`](../../reports/v7_main_bonus_role_bias_v7.0.0_historical.claim),
  raw SHA-256
  `1443982f9b40ba5b460632211baa17b4aff7cb9cdcd48010c0a538f141344290`.
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
- Git data-boundary verification passed, the registration prefix was
  preserved, and the known-outcomes fingerprint is
  `257aef242bb898649b0923ac03f2271c7536ff7f840edf552c0dc6b4b03ce1dd`.
- Research configuration:
  [`config/research-v7-main-bonus-role-bias.yaml`](../../config/research-v7-main-bonus-role-bias.yaml),
  raw SHA-256
  `ca6f0b8b07a5d35c966cd9e3d015b5f87978e465338a260ba3a581b565468558`,
  effective canonical SHA-256
  `4ab892f6d9f4a23a49e345951234f0d21eb36ed30de9689df9792a2bc7ea0184`.
- Frozen V6 reference:
  [`reports/v6_entropy_regime_v6.0.0_historical.json`](../../reports/v6_entropy_regime_v6.0.0_historical.json),
  raw SHA-256
  `12400a4b5164b030225827d47a8024a1ec7aeaeb32fa64cd2fab0b46ff8d4c2a`.
  Its consumed-lane summaries were reused without refitting.
- Machine-readable result:
  [`reports/v7_main_bonus_role_bias_v7.0.0_historical.json`](../../reports/v7_main_bonus_role_bias_v7.0.0_historical.json),
  schema version `3`, raw SHA-256
  `242018714a17a78a8b99309e4391e153c293a02121738addd2bb8f9f74d6c121`.
- Compact generated result:
  [`reports/v7_main_bonus_role_bias_v7.0.0_historical.md`](../../reports/v7_main_bonus_role_bias_v7.0.0_historical.md),
  raw SHA-256
  `e944c33494712c932c826b84d288a7239911e5d34eecb113cc6dffe639dec3f4`.
- Frozen specification:
  [`V7_main_bonus_role_bias.md`](V7_main_bonus_role_bias.md).

The only scored prediction lane is 621 targets from 2020-01-01 through
2025-12-31. That entire interval is **consumed historical diagnostic evidence**:
it is not blind, validation, confirmatory, or prospective evidence, and it can
never be relabeled as such. The historical-development and legacy-validation
lanes are not applicable to this post-RNG hypothesis and were not scored. Every
2026+ outcome already observed before any possible activation is also consumed
for `v7.0.0`; none can be backfilled into a prospective cohort.

## Candidate results

Fair per-draw expectations are `36/49 = 0.7346938776` for Top-6,
`72/49 = 1.4693877551` for Top-12, and `108/49 = 2.2040816327` for Top-18.
Positive hit-count lift is favorable. Lower Brier score, log loss, and actual
rank are favorable. A positive proper-score delta means worse performance than
the fair constant baseline.

### Ranking and primary inference

| Scope | Draws | Top-6 mean (lift) | Top-12 mean (lift) | Top-18 mean (lift) | Total Top-12 | Exact one-sided p | Holm p | 95% bootstrap CI for Top-12 lift |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Aggregate, 2020-2025 | 621 | 0.766505636 (+0.031811759) | 1.483091787 (+0.013704032) | 2.196457327 (-0.007624306) | 921 | 0.372656874 | 0.372656874 | [-0.065200960, +0.094219330] |
| Fixed half 1, 2020-2022 | 307 | 0.771986971 (+0.037293093) | 1.456026059 (-0.013361696) | 2.133550489 (-0.070531144) | 447 | 0.602520019 | n/a | [-0.124110882, +0.097387489] |
| Fixed half 2, 2023-2025 | 314 | 0.761146497 (+0.026452619) | 1.509554140 (+0.040166385) | 2.257961783 (+0.053880151) | 474 | 0.245845715 | n/a | [-0.071298583, +0.158000780] |

The aggregate Top-6 and Top-12 point estimates were positive, and all three
Top-K point estimates were positive in the second fixed half. Those are the
positive descriptive observations. They do not establish stable signal: the
sole primary family-adjusted test is not significant, every registered
bootstrap interval includes zero, and the primary lift changes sign between
the fixed halves. The aggregate Top-18 lift and the first-half Top-12 and
Top-18 lifts were negative.

### Proper scores, actual rank, and activation

The exact fair-constant reference is Brier `0.10745522698875469` and log loss
`0.37177617994345286` in every scope. The frozen gate requires both deltas to be
at most `1e-9` in the aggregate and each fixed half.

| Scope | Brier | Brier delta vs fair | Log loss | Log-loss delta vs fair | Mean actual rank | Active / targets | Fair fallback |
|---|---:|---:|---:|---:|---:|---:|---:|
| Aggregate, 2020-2025 | 0.109730908444 | +0.002275681455 | 0.380709033255 | +0.008932853311 | 25.132045089 | 582 / 621 | 39 |
| Fixed half 1, 2020-2022 | 0.110956489847 | +0.003501262858 | 0.384645162854 | +0.012868982910 | 25.198154180 | 268 / 307 | 39 |
| Fixed half 2, 2023-2025 | 0.108532648919 | +0.001077421930 | 0.376860651768 | +0.005084471824 | 25.067409766 | 314 / 314 | 0 |

All six proper-score deltas are positive and materially exceed the registered
tolerance, so the probability forecasts were worse than the exact fair
constant in every scope. The frozen 104-prior-draw activation rule produced 39
fair-fallback targets and 582 active targets; the first active target was
2020-05-20. These activation counts are integrity facts, not an alternate
active-only subgroup, and no active-only score is permitted.

## Registered negative control

The sole control, `v7_main_bonus_role_control v7.0.0`, reassigns the bonus role
within each strictly prior post-RNG seven-number draw using the frozen seed-649
stream. It preserves chronology, dates, seven-label sets, and target outcomes
while destroying the historical main/bonus role association. A null control is
pipeline evidence only; it cannot support a prediction claim.

### Control ranking and primary inference

| Scope | Draws | Top-6 mean (lift) | Top-12 mean (lift) | Top-18 mean (lift) | Total Top-12 | Exact one-sided p | 95% bootstrap CI for Top-12 lift | Null |
|---|---:|---:|---:|---:|---:|---:|---|---|
| Aggregate, 2020-2025 | 621 | 0.753623188 (+0.018929311) | 1.471819646 (+0.002431891) | 2.202898551 (-0.001183082) | 914 | 0.482710953 | [-0.078083407, +0.081336883] | yes |
| Fixed half 1, 2020-2022 | 307 | 0.762214984 (+0.027521106) | 1.508143322 (+0.038755567) | 2.169381107 (-0.034700525) | 463 | 0.256332559 | [-0.068736289, +0.146247424] | yes |
| Fixed half 2, 2023-2025 | 314 | 0.745222930 (+0.010529052) | 1.436305732 (-0.033082023) | 2.235668790 (+0.031587157) | 451 | 0.730373958 | [-0.150916418, +0.084752372] | yes |

No control exact p-value is at or below `0.05`, and every interval includes
zero. The aggregate and both halves therefore meet the registered null
condition and raise no control warning.

### Control proper scores and actual rank

| Scope | Brier | Brier delta vs fair | Log loss | Log-loss delta vs fair | Mean actual rank | Active / targets | Fair fallback |
|---|---:|---:|---:|---:|---:|---:|---:|
| Aggregate, 2020-2025 | 0.110007585438 | +0.002552358449 | 0.382515758111 | +0.010739578167 | 24.888888889 | 582 / 621 | 39 |
| Fixed half 1, 2020-2022 | 0.111196407762 | +0.003741180773 | 0.387041784384 | +0.015265604440 | 24.958740499 | 268 / 307 | 39 |
| Fixed half 2, 2023-2025 | 0.108845265522 | +0.001390038533 | 0.378090630512 | +0.006314450569 | 24.820594480 | 314 / 314 | 0 |

## Frozen global conditional role audit

The post-outcome audit used all 686 draws from 2019-05-15 through 2025-12-31.
The observed conditional 6:1 likelihood-ratio statistic was
`G = 47.22561384929766`. With exactly 10,000 chronological within-draw role
randomizations from a fresh seed-649 generator, 5,707 randomized statistics
were greater than or equal to the observed value. The registered plus-one
right-tail result was therefore

```text
p_global = (1 + 5707) / 10001 = 0.5707429257074292.
```

This fails the required `p_global <= 0.05` gate. It provides no evidence of a
stable aggregate departure from conditional main/bonus role exchangeability in
the fixed interval. It is a mechanism diagnostic, not a prediction score, and
cannot rescue or replace the primary Top-12 result.

## Frozen gate decision

| Registered gate | Result | Evidence |
|---|---|---|
| Positive aggregate primary Top-12 lift | Pass | `+0.013704032` |
| Aggregate Holm-adjusted exact p <= 0.05 | **Fail** | `0.372656874` |
| Aggregate bootstrap lower endpoint > 0 | **Fail** | `-0.065200960` |
| Positive primary lift in both fixed halves | **Fail** | First half `-0.013361696` |
| Aggregate and half Brier/log-loss deltas <= 1e-9 | **Fail** | Every delta is positive; smallest is Brier `+0.001077422` |
| Global role-audit p <= 0.05 | **Fail** | `0.570742926` |
| Negative control null in aggregate and both halves | Pass | All exact p-values > `0.05`; all intervals include zero |
| Audit clear | Pass | Empty warning list; Git boundary and one-shot checks passed |

Only three of eight gates pass. Because the registered decision is a
conjunction, the valid decision is **Reject**. Historical primary signal support
is `false`; prospective/shadow status is **`not_activated`**.

## Fixed comparison context

The frozen descriptive comparison set was exact fair theory, deterministic
random, all V1 production baselines and their ensemble, V3 shadow, rejected V5,
rejected V6, and V7. The complete Top-6, Top-12, Top-18, Brier, log-loss, and
actual-rank summaries remain in the machine-readable report. They were reused
from the registered V6 report on the identical 621 targets and did not enter a
V7 gate, select a variant, refit a model, or alter an operational role.

For context, V7's aggregate Top-12 mean `1.483091787` was above exact fair
theory and the frozen random/V6 summaries but below V3's `1.521739130` and V5's
`1.494363929`. Its Brier and log loss were worse than the fair constant and all
V1 comparison models. This mixed, already-consumed ordering does not establish
stable predictability and does not change the frozen rejection.

## Consequences

`v7.0.0` is closed as **Reject**. It must not be added to `config.yaml`, must not
produce live or shadow snapshots, and has no eligible prospective observation.
No existing prediction snapshot is modified or regenerated by this decision.
V1 remains production and V3 remains shadow.

The permanent one-shot claim proves that the frozen historical diagnostic has
already been consumed. It must not be deleted, bypassed, renamed, or otherwise
used to run `v7.0.0` again. The result may not be rescued by changing features,
pseudo-counts, activation counts, dates, halves, weights, constraints, metrics,
controls, seeds, or gates and presenting the new answer as a same-version blind
or confirmatory test.

Any hypothesis or implementation changed after these results were observed
must have a new model version, a new pre-registration and freeze, and a new
prospective cohort starting only after a separate reviewed activation decision.
The complete 2020-2025 result and every observed 2026+ outcome that influences
that change are consumed for the changed candidate. Negative attempts remain in
the multiplicity ledger; a new variant cannot erase or relabel this result.
