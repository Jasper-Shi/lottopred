# V6 Fixed-Boundary Entropy-Regime Historical Diagnostic

Status: historical diagnostic only. No result here is blind, confirmatory,
prospective, or an automatic shadow/production promotion.

- Experiment: `V6_fixed_boundary_js_regime` / `v6.0.0`
- Frozen implementation commit: `591b6173aa3a2e711d2c5e5e7f9cc3f8c7801bf6`
- Exact command: `lotto649 --config config/research-v6-entropy-regime.yaml research-v6 --code-commit 591b6173aa3a2e711d2c5e5e7f9cc3f8c7801bf6`
- Diagnostic prefix: 4431 draws through `2026-08-12` (`95434535857a95f3ae9bd25e42345291274804702ed514b0bace6fafcf584bdf`)
- Outcomes known at registration: 4432 draws through `2026-08-15` (`edfb7f8a4a7711a630957d6f86b567e6b254caf7b1d1aaea0edf1d16a34155b3`)
- Data-boundary Git verification: passed; registered prefix preserved
- Reused V5 reference: `reports/v5_pair_affinity_v5.0.0_historical.json` (`b86391ada265d96f94e789f4962812d32771385702e2efa2285cb9ef96d5d6bb`)
- Research config: `config/research-v6-entropy-regime.yaml`
- Effective config SHA-256: `608081dd74240f71519c5e85e8f326c25910a6baaaac56c6e906cc1f7d76ff8d`
- Primary metric: mean Top-12 hits lift versus exact `72/49`
- Sole historical Holm gate: consumed diagnostic lane

## Registered lane results

| Lane | Draws | Active | Top-12 | Lift | Raw p | Holm p | 95% CI | Brier delta | Log-loss delta | Control active | Control lift | Control null? |
|---|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---|
| development | 2926 | 44 | 1.467874 | -0.001514 | 0.53592 | n/a | [-0.037740, +0.034372] | +3.75744e-06 | +1.83737e-05 | 65 | -0.017576 | yes |
| legacy_validation | 520 | 0 | 1.586538 | +0.117151 | 0.00413902 | n/a | [+0.032535, +0.203737] | -5.84255e-13 | -2.7186e-12 | 20 | -0.032849 | yes |
| consumed_diagnostic | 621 | 0 | 1.470209 | +0.000822 | 0.498761 | 0.498761 | [-0.078083, +0.078116] | -4.03705e-13 | -1.87844e-12 | 10 | -0.010451 | yes |

## Frozen historical decision

Decision: **reject**. Prospective status remains **not_activated**.

- `positive_primary_lift_all_lanes`: fail
- `consumed_holm_adjusted_p_at_most_0_05`: fail
- `consumed_bootstrap_lower_above_zero`: fail
- `proper_scores_within_fair_tolerance_all_lanes`: fail
- `negative_controls_null_all_lanes`: pass
- `audit_clear`: pass

The JSON companion retains every secondary metric, the complete reused
comparison summaries, activation counts, control results, hashes, and
provenance. Any behavior change after reading these outcomes requires a
new model version and a new prospective cohort.
