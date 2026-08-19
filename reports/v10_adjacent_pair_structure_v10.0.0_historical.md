# V10 Adjacent-Pair Structure Historical Diagnostic

Status: consumed historical diagnostic only; not blind, confirmatory,
prospective, or an automatic live/shadow promotion.

- Experiment: `V10_adjacent_pair_structure` / `v10.0.0`
- Frozen implementation commit: `38be95eb27aa69a9e16bc972d14df13b0b24d6dd`
- Targets: `621`
- Candidate Top-12 mean: `1.489533011`
- Candidate Top-12 lift: `+0.020145256`
- Candidate raw p: `0.31366892`
- Candidate Holm p: `0.544596505`
- Historical decision: **reject**
- Prospective status: **not_activated**
- V1 production and V3 shadow roles: unchanged

## Frozen gate outcomes

- `positive_aggregate_primary_lift`: pass
- `aggregate_holm_adjusted_p_at_most_0_05`: fail
- `aggregate_bootstrap_lower_above_zero`: fail
- `positive_primary_lift_in_both_fixed_halves`: pass
- `candidate_outperforms_targeted_control_aggregate_and_halves`: fail
- `proper_scores_within_fair_tolerance_aggregate_and_halves`: fail
- `candidate_above_frozen_v1_ensemble_top12`: pass
- `controls_null_aggregate_and_halves`: pass
- `joint_mechanism_gate`: fail
- `audit_clear`: pass

The JSON companion and permanent hash-chain ledger retain complete
forecast, score, calibration, control, joint-gain, record, warning,
and provenance evidence. A negative result is a valid outcome.
