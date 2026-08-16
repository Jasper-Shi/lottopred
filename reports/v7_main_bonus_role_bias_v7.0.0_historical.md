# V7 Post-RNG Main/Bonus Role-Bias Historical Diagnostic

Status: consumed historical diagnostic only. It is not blind,
confirmatory, prospective, or an automatic shadow/production promotion.

- Experiment: `V7_post_rng_main_bonus_role_bias` / `v7.0.0`
- Frozen implementation commit: `180cd045e7797b95db4226f7d79d66d6ee9a5965`
- Exact command: `lotto649 --config config/research-v7-main-bonus-role-bias.yaml research-v7 --code-commit 180cd045e7797b95db4226f7d79d66d6ee9a5965`
- Permanent one-shot claim: `reports/v7_main_bonus_role_bias_v7.0.0_historical.claim`
- Claim SHA-256: `1443982f9b40ba5b460632211baa17b4aff7cb9cdcd48010c0a538f141344290`
- Research config SHA-256: `ca6f0b8b07a5d35c966cd9e3d015b5f87978e465338a260ba3a581b565468558`
- V6 reference SHA-256: `12400a4b5164b030225827d47a8024a1ec7aeaeb32fa64cd2fab0b46ff8d4c2a`
- Applicable prediction lane: 2020-01-01 through 2025-12-31 only
- Development and legacy-validation lanes: not applicable and not scored

## Registered prediction results

| Scope | Model | Draws | Top-12 | Lift | Raw p | Holm p | 95% CI | Brier delta | Log-loss delta |
|---|---|---:|---:|---:|---:|---:|---|---:|---:|
| aggregate | v7_main_bonus_role_bias | 621 | 1.483092 | +0.013704 | 0.372657 | 0.372657 | [-0.065201, +0.094219] | +0.00227568 | +0.00893285 |
| aggregate control | v7_main_bonus_role_control | 621 | 1.471820 | +0.002432 | 0.482711 | n/a | [-0.078083, +0.081337] | +0.00255236 | +0.0107396 |
| 2020_2022 | v7_main_bonus_role_bias | 307 | 1.456026 | -0.013362 | 0.60252 | n/a | [-0.124111, +0.097387] | +0.00350126 | +0.012869 |
| 2020_2022 control | v7_main_bonus_role_control | 307 | 1.508143 | +0.038756 | 0.256333 | n/a | [-0.068736, +0.146247] | +0.00374118 | +0.0152656 |
| 2023_2025 | v7_main_bonus_role_bias | 314 | 1.509554 | +0.040166 | 0.245846 | n/a | [-0.071299, +0.158001] | +0.00107742 | +0.00508447 |
| 2023_2025 control | v7_main_bonus_role_control | 314 | 1.436306 | -0.033082 | 0.730374 | n/a | [-0.150916, +0.084752] | +0.00139004 | +0.00631445 |

## Registered integrity and role audit

- Targets: `621`; fair fallback: `39`; active: `582`; first active: `2020-05-20`
- Global role statistic G: `47.22561384929766`
- Global role audit plus-one p: `0.5707429257074292` from `10000` randomizations

## Frozen historical decision

Decision: **reject**. Prospective status remains **not_activated**.

- `positive_aggregate_primary_lift`: pass
- `aggregate_holm_adjusted_p_at_most_0_05`: fail
- `aggregate_bootstrap_lower_above_zero`: fail
- `positive_primary_lift_in_both_fixed_halves`: fail
- `proper_scores_within_fair_tolerance_aggregate_and_halves`: fail
- `global_role_audit_p_at_most_0_05`: fail
- `negative_control_null_aggregate_and_halves`: pass
- `audit_clear`: pass

The JSON companion retains the frozen comparison summaries, complete
aggregate/half candidate and control metrics, data/config/code hashes,
registered parameters, audit warnings, and prospective boundary.
