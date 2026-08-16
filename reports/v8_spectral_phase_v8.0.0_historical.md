# V8 Fixed-Recurrence Harmonic Historical Diagnostic

Status: consumed historical diagnostic only. It is not blind,
confirmatory, prospective, or an automatic shadow/production promotion.

- Experiment: `V8_fixed_recurrence_harmonic` / `v8.0.0`
- Frozen implementation commit: `c48ab2277f005a48bc4dc57f5a532b476ab900fa`
- Exact command: `lotto649 --config config/research-v8-fixed-spectral-phase.yaml research-v8 --code-commit c48ab2277f005a48bc4dc57f5a532b476ab900fa`
- Permanent one-shot claim: `reports/v8_spectral_phase_v8.0.0_historical.claim`
- Claim SHA-256: `6598a2f38462fe6274b9dfa6b6b8c51e6af367b551fd861ef8a582000d60c76d`
- Research config SHA-256: `37cd3f5444be05c0508029d8f341e5291514d7444cd4c961cdc0d57815ee1aed`
- V7 reference SHA-256: `242018714a17a78a8b99309e4391e153c293a02121738addd2bb8f9f74d6c121`
- V7 claim SHA-256: `1443982f9b40ba5b460632211baa17b4aff7cb9cdcd48010c0a538f141344290`
- Applicable prediction lane: 2020-01-01 through 2025-12-31 only
- Development and legacy-validation lanes: not applicable and not scored

## Registered prediction and control results

| Scope | Model | Draws | Top-12 | Lift | Raw p | Holm p | 95% CI | Brier delta | Log-loss delta |
|---|---|---:|---:|---:|---:|---:|---|---:|---:|
| aggregate | v8_spectral_phase | 621 | 1.452496 | -0.016892 | 0.670094 | 0.670094 | [-0.089356, +0.058833] | +1.85092e-05 | +8.57888e-05 |
| aggregate row control | v8_spectral_phase_row_control | 621 | 1.534622 | +0.065234 | 0.0541073 | n/a | [-0.008840, +0.142529] | -7.76445e-06 | -3.62973e-05 |
| aggregate phase control | v8_spectral_phase_rotation_control | 621 | 1.450886 | -0.018502 | 0.684572 | n/a | [-0.095797, +0.058793] | +2.0221e-06 | +8.35404e-06 |
| 2020_2022 | v8_spectral_phase | 307 | 1.429967 | -0.039420 | 0.764111 | n/a | [-0.143655, +0.068072] | +3.99543e-05 | +0.000185461 |
| 2020_2022 row control | v8_spectral_phase_row_control | 307 | 1.498371 | +0.028984 | 0.314302 | n/a | [-0.075251, +0.139733] | +4.44907e-06 | +1.98966e-05 |
| 2020_2022 phase control | v8_spectral_phase_rotation_control | 307 | 1.504886 | +0.035498 | 0.275014 | n/a | [-0.078508, +0.149505] | -9.57799e-06 | -4.60925e-05 |
| 2023_2025 | v8_spectral_phase | 314 | 1.474522 | +0.005135 | 0.473398 | n/a | [-0.099961, +0.110230] | -2.45778e-06 | -1.16611e-05 |
| 2023_2025 row control | v8_spectral_phase_row_control | 314 | 1.570064 | +0.100676 | 0.0397587 | n/a | [-0.007604, +0.205771] | -1.97057e-05 | -9.12384e-05 |
| 2023_2025 phase control | v8_spectral_phase_rotation_control | 314 | 1.398089 | -0.071299 | 0.9029 | n/a | [-0.179579, +0.036982] | +1.33636e-05 | +6.15868e-05 |

## Paired candidate-minus-row-control intervals

| Scope | Draws | Mean difference | Paired 95% CI |
|---|---:|---:|---|
| aggregate | 621 | -0.082126 | [-0.186795, +0.020934] |
| 2020_2022 | 307 | -0.068404 | [-0.211726, +0.068404] |
| 2023_2025 | 314 | -0.095541 | [-0.251592, +0.063694] |

## Registered integrity and historical decision

- Targets: `621`; fair fallback: `39`; active: `582`; first active: `2020-05-20`; exclusions: `0`
- Decision: **reject**
- Prospective status: **not_activated**

- `positive_aggregate_primary_lift`: fail
- `aggregate_holm_adjusted_p_at_most_0_05`: fail
- `aggregate_bootstrap_lower_above_zero`: fail
- `positive_primary_lift_in_both_fixed_halves`: fail
- `proper_scores_within_fair_tolerance_aggregate_and_halves`: fail
- `row_control_null_and_candidate_outperforms_it`: fail
- `phase_control_null_aggregate_and_halves`: pass
- `audit_clear`: pass

The JSON companion retains all aggregate/half candidate and control
metrics, the three paired intervals, frozen comparison summaries,
data/config/code/reference/claim identities, warnings, and the
prospective boundary. V1 remains production and V3 remains shadow.
