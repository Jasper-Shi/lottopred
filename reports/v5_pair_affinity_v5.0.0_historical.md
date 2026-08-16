# V5 Pair-Affinity Historical Diagnostic

Status: historical diagnostic only. No result in this report is blind,
confirmatory, prospective, or sufficient for production promotion.

- Experiment: `V5_pair_affinity` / `v5.0.0`
- Frozen implementation commit: `f51a3b59e857f6c3a5d9c0502a0c30e71d15d3b4`
- Dataset SHA-256: `95434535857a95f3ae9bd25e42345291274804702ed514b0bace6fafcf584bdf`
- Research config: `config/research-v5-pair-affinity.yaml`
- Research config SHA-256: `b89a74aa353fda9891a011edfa44a4d0a6d99edb8477ed803a176ef8fa035550`
- Effective config SHA-256: `83553c57c8dd76dce7a8272e59f5047ba2e129c5b438028b4c120c2b37899676`
- Negative-control seed: `649`
- Primary metric: mean Top-12 hits lift versus exact `72/49`

## Registered lane results

| Lane | Draws | Top-12 | Lift | Exact one-sided p | Holm p | 95% bootstrap CI | Control lift | Control null? |
|---|---:|---:|---:|---:|---:|---|---:|---|
| development | 2926 | 1.477444 | +0.008056 | 0.334025 | 0.334025 | [-0.028171, +0.044283] | -0.003222 | yes |
| legacy_validation | 520 | 1.403846 | -0.065542 | 0.936385 | 0.936385 | [-0.155926, +0.024843] | +0.028689 | yes |
| consumed_diagnostic | 621 | 1.494364 | +0.024976 | 0.272298 | 0.272298 | [-0.052319, +0.103881] | +0.039469 | yes |

## Interpretation boundary

All signs, proper scores, operational comparisons, and negative-control
results are retained in the JSON companion report. Historical outcomes
cannot activate or promote the model. Any behavior change made after
reading this report requires a new version and new prospective cohort.
