# V11 previous-bonus carryover historical diagnostic

This is a consumed historical diagnostic, not blind confirmation. The model remains `not_activated`.

## Identity and scope

- Experiment: `V11_previous_bonus_carryover` / `v11.0.0`
- Registration commit: `eb12933ab74f3a9c34a3ece3de90d280197c410c`
- Implementation commit: `539d7c12531aa21daf16887536c2ace1455c25a2`
- Claim SHA-256: `6a6465d5b5ec2913aae4047c42a7e94b50a9e63aac67019e966145d9c698751b`
- Ledger head before publication: `adc77fe37ca9aa1b077cd97511ba8b432d564a01970b9b59590f3f853ca44521`
- Registered data/source: `{"draw_count": 4432, "fixed_half_counts": [307, 314], "history_through": "2026-08-15", "path": "data/processed/draws.csv", "sha256": "edfb7f8a4a7711a630957d6f86b567e6b254caf7b1d1aaea0edf1d16a34155b3", "source_commit": "90177c80cfb070038d79508fb2e73305a297f516", "source_commit_ancestor_of_implementation": true, "source_commit_ancestor_of_registration": true, "source_git_blob": {"byte_count": 136236, "git_blob_byte_identical": true, "sha256": "edfb7f8a4a7711a630957d6f86b567e6b254caf7b1d1aaea0edf1d16a34155b3"}, "target_count": 621}`
- Frozen research configuration: `{"path": "config/research-v11-previous-bonus-carryover.yaml", "registry_parameters_equal": true, "registry_status": "registered", "sha256": "514b0d9e234b8e5eb1d64587224289791ce95fad8f8381b28fda2d0954da7dd7", "v1_base_config_path": "config.yaml", "v1_base_config_sha256": "b67b6cd4e1ace10275da6142fbb8739c1de0e91c37a7f636e42d2c0f4d862ff5", "v1_base_file_sha256": [{"path": "src/lotto649/models/baselines.py", "sha256": "76f9050a13bde44d51584397ecd6acb358f320e1617ef329b70bd6a22d23e28a"}, {"path": "src/lotto649/models/logistic.py", "sha256": "886367c16ed0f0d1109aacb943a3393e63807a31e7710bd0e664e06f6f3c4da2"}, {"path": "src/lotto649/models/ensemble.py", "sha256": "9b2a3fb3156efb3ff248fa6debecfd7a92b718e9517d8da0e3a5fc43da7c0047"}, {"path": "src/lotto649/models/factory.py", "sha256": "d0d3043656144a469b1677491c11cde3143a65b026c2a815485cc89ae5d48fcc"}, {"path": "src/lotto649/features.py", "sha256": "b7bc67b9038b2e3d78230c3087c3ac4e3f17751aeab678574f3601af00671979"}, {"path": "src/lotto649/models/base.py", "sha256": "e2f0c90c376ea6063b906bcca042e8903b351a1ed4b76e9d83e17be3bcf166ec"}, {"path": "src/lotto649/domain.py", "sha256": "fbcb22747ae361767df070c6e50af49fda1aa190b72fd39894afa1c879a50b7a"}, {"path": "src/lotto649/config.py", "sha256": "7563042563ec197de01120bf2d4267d9f089875defdfa95da8323d9f5702e862"}], "v1_base_source_commit": "86549d2650fe98cd48375fa77b5b8521ca271df2"}`
- Frozen runtime/lock: `{"distributions": [{"name": "beautifulsoup4", "version": "4.13.5"}, {"name": "certifi", "version": "2025.11.12"}, {"name": "charset-normalizer", "version": "3.4.4"}, {"name": "idna", "version": "3.11"}, {"name": "iniconfig", "version": "2.3.0"}, {"name": "joblib", "version": "1.5.2"}, {"name": "lotto649-model", "version": "0.1.0"}, {"name": "narwhals", "version": "2.24.0"}, {"name": "numpy", "version": "2.3.5"}, {"name": "packaging", "version": "26.3"}, {"name": "pandas", "version": "2.3.3"}, {"name": "pip", "version": "25.1.1"}, {"name": "pluggy", "version": "1.6.0"}, {"name": "Pygments", "version": "2.21.0"}, {"name": "pypdf", "version": "6.16.1"}, {"name": "pytest", "version": "8.4.2"}, {"name": "python-dateutil", "version": "2.9.0.post0"}, {"name": "pytz", "version": "2025.2"}, {"name": "PyYAML", "version": "6.0.3"}, {"name": "requests", "version": "2.32.5"}, {"name": "ruff", "version": "0.16.3"}, {"name": "scikit-learn", "version": "1.7.2"}, {"name": "scipy", "version": "1.16.3"}, {"name": "six", "version": "1.17.0"}, {"name": "soupsieve", "version": "2.5"}, {"name": "threadpoolctl", "version": "3.5.0"}, {"name": "typing_extensions", "version": "4.15.0"}, {"name": "tzdata", "version": "2025.2"}, {"name": "urllib3", "version": "2.5.0"}], "executable": "/private/tmp/lottopred-v11-py312.4CrBhf/bin/python", "implementation": "CPython", "lock_sha256": "2fea4cf73cc2578b73c21e6600e31ad843bd903e8a2656b7a2543164ab8d801c", "locked_distributions_verified": {"beautifulsoup4": "4.13.5", "certifi": "2025.11.12", "charset-normalizer": "3.4.4", "idna": "3.11", "joblib": "1.5.2", "numpy": "2.3.5", "pandas": "2.3.3", "pypdf": "6.16.1", "python-dateutil": "2.9.0.post0", "pytz": "2025.2", "pyyaml": "6.0.3", "requests": "2.32.5", "scikit-learn": "1.7.2", "scipy": "1.16.3", "six": "1.17.0", "soupsieve": "2.5", "threadpoolctl": "3.5.0", "typing-extensions": "4.15.0", "tzdata": "2025.2", "urllib3": "2.5.0"}, "platform": "macOS-26.5.2-arm64-arm-64bit", "python_version": "3.12.11", "requirements_lock_path": "requirements-live.lock", "requirements_lock_sha256": "2fea4cf73cc2578b73c21e6600e31ad843bd903e8a2656b7a2543164ab8d801c"}`
- Targets: `2020-01-01` through `2025-12-31` (621)
- Decision: `reject`

## Frozen feature sets

- `v11_previous_bonus_carryover`: `frozen_v1_marginals_plus_previous_published_bonus_logit_tilt`
- `v11_previous_bonus_carryover_pseudo_bonus_control`: `frozen_v1_marginals_plus_deterministic_pseudo_bonus_logit_tilt`
- `ensemble`: `frozen_v1_ensemble_marginals`
- `random`: `date_seeded_fair_random_baseline`

## Scope summaries

| Model | Scope | Draws | Top-6 | Top-12 | Top-18 | Brier | Log loss | Final-6 histogram |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| v11_previous_bonus_carryover | aggregate_621 | 621 | 0.684380032206 | 1.38969404187 | 2.1384863124 | 0.107692718321 | 0.372857758885 | `{"0": 292, "1": 247, "2": 70, "3": 10, "4": 2, "5": 0, "6": 0}` |
| v11_previous_bonus_carryover | first_307 | 307 | 0.71009771987 | 1.48859934853 | 2.20195439739 | 0.107663626223 | 0.372727745026 | `{"0": 140, "1": 125, "2": 35, "3": 5, "4": 2, "5": 0, "6": 0}` |
| v11_previous_bonus_carryover | second_314 | 314 | 0.65923566879 | 1.29299363057 | 2.07643312102 | 0.107721161869 | 0.372984874346 | `{"0": 152, "1": 122, "2": 35, "3": 5, "4": 0, "5": 0, "6": 0}` |
| v11_previous_bonus_carryover_pseudo_bonus_control | aggregate_621 | 621 | 0.692431561997 | 1.40257648953 | 2.14492753623 | 0.107692470757 | 0.372888072597 | `{"0": 294, "1": 240, "2": 73, "3": 12, "4": 2, "5": 0, "6": 0}` |
| v11_previous_bonus_carryover_pseudo_bonus_control | first_307 | 307 | 0.726384364821 | 1.48859934853 | 2.20846905537 | 0.107669339481 | 0.372805142154 | `{"0": 141, "1": 119, "2": 39, "3": 6, "4": 2, "5": 0, "6": 0}` |
| v11_previous_bonus_carryover_pseudo_bonus_control | second_314 | 314 | 0.65923566879 | 1.31847133758 | 2.08280254777 | 0.107715086367 | 0.372969154273 | `{"0": 153, "1": 121, "2": 34, "3": 6, "4": 0, "5": 0, "6": 0}` |
| ensemble | aggregate_621 | 621 | 0.682769726248 | 1.39774557166 | 2.14653784219 | 0.107682584889 | 0.372814454252 | `{"0": 296, "1": 241, "2": 71, "3": 11, "4": 2, "5": 0, "6": 0}` |
| ensemble | first_307 | 307 | 0.71009771987 | 1.49511400651 | 2.21824104235 | 0.107647306455 | 0.372659647128 | `{"0": 143, "1": 120, "2": 36, "3": 6, "4": 2, "5": 0, "6": 0}` |
| ensemble | second_314 | 314 | 0.656050955414 | 1.3025477707 | 2.07643312102 | 0.10771707686 | 0.372965810261 | `{"0": 153, "1": 121, "2": 35, "3": 5, "4": 0, "5": 0, "6": 0}` |
| random | aggregate_621 | 621 | 0.77616747182 | 1.47020933977 | 2.22383252818 | 0.107455226985 | 0.371776179928 | `{"0": 256, "1": 260, "2": 93, "3": 12, "4": 0, "5": 0, "6": 0}` |
| random | first_307 | 307 | 0.732899022801 | 1.38110749186 | 2.15309446254 | 0.107455226988 | 0.371776179942 | `{"0": 130, "1": 134, "2": 38, "3": 5, "4": 0, "5": 0, "6": 0}` |
| random | second_314 | 314 | 0.81847133758 | 1.55732484076 | 2.29299363057 | 0.107455226983 | 0.371776179914 | `{"0": 126, "1": 126, "2": 55, "3": 7, "4": 0, "5": 0, "6": 0}` |

## Primary, paired, mechanism, calibration, and yearly evidence

- Candidate raw exact p: `0.9783404732169021`; Holm adjusted p: `1.0`; bootstrap CI: `[-0.1569883992244241, -0.00078872128561569]`
- Paired candidate minus V1: `{"aggregate_621": {"bootstrap_95_ci": [-0.027375201288244767, 0.011272141706924315], "draws": 621, "mean_difference": -0.008051529790660225, "scope": "aggregate_621"}, "first_307": {"bootstrap_95_ci": [-0.04234527687296417, 0.029315960912052116], "draws": 307, "mean_difference": -0.006514657980456026, "scope": "first_307"}, "second_314": {"bootstrap_95_ci": [-0.022292993630573247, 0.0], "draws": 314, "mean_difference": -0.009554140127388535, "scope": "second_314"}}`
- Paired candidate minus control: `{"aggregate_621": {"bootstrap_95_ci": [-0.040257648953301126, 0.014492753623188406], "draws": 621, "mean_difference": -0.01288244766505636, "scope": "aggregate_621"}, "first_307": {"bootstrap_95_ci": [-0.04560260586319218, 0.04560260586319218], "draws": 307, "mean_difference": 0.0, "scope": "first_307"}, "second_314": {"bootstrap_95_ci": [-0.05732484076433121, 0.0031847133757961785], "draws": 314, "mean_difference": -0.025477707006369428, "scope": "second_314"}}`
- Anchor mechanism: `{"candidate_aggregate_d": -1.3040865570121065, "candidate_aggregate_log_g": -2.4054676365522885, "candidate_half_d": [-1.0083918174139248, -0.2956947395981817], "candidate_half_log_g": [-1.7642013957969063, -0.6412662407553822], "candidate_minus_control_aggregate_d": 1.1048554924551925, "candidate_minus_control_aggregate_log_g": 2.3312221152258, "candidate_minus_control_half_d": [1.2588546017719229, -0.15399910931673028], "candidate_minus_control_half_log_g": [1.3208105561694397, 1.0104115590563603], "control_aggregate_log_g": -4.736689751778089}`
- Candidate calibration: `{"bins": [{"bin": 0, "cell_count": 409, "lower": 0.0, "mean_forecast": 0.09674790005276394, "observed_inclusion_rate": 0.12224938875305623, "right_closed": false, "upper": 0.1}, {"bin": 1, "cell_count": 30017, "lower": 0.1, "mean_forecast": 0.1227909210363432, "observed_inclusion_rate": 0.1224639371023087, "right_closed": false, "upper": 0.2}, {"bin": 2, "cell_count": 3, "lower": 0.2, "mean_forecast": 0.2050107101686891, "observed_inclusion_rate": 0.0, "right_closed": false, "upper": 0.3}, {"bin": 3, "cell_count": 0, "lower": 0.3, "mean_forecast": null, "observed_inclusion_rate": null, "right_closed": false, "upper": 0.4}, {"bin": 4, "cell_count": 0, "lower": 0.4, "mean_forecast": null, "observed_inclusion_rate": null, "right_closed": false, "upper": 0.5}, {"bin": 5, "cell_count": 0, "lower": 0.5, "mean_forecast": null, "observed_inclusion_rate": null, "right_closed": false, "upper": 0.6}, {"bin": 6, "cell_count": 0, "lower": 0.6, "mean_forecast": null, "observed_inclusion_rate": null, "right_closed": false, "upper": 0.7}, {"bin": 7, "cell_count": 0, "lower": 0.7, "mean_forecast": null, "observed_inclusion_rate": null, "right_closed": false, "upper": 0.8}, {"bin": 8, "cell_count": 0, "lower": 0.8, "mean_forecast": null, "observed_inclusion_rate": null, "right_closed": false, "upper": 0.9}, {"bin": 9, "cell_count": 0, "lower": 0.9, "mean_forecast": null, "observed_inclusion_rate": null, "right_closed": true, "upper": 1.0}], "expected_calibration_error": 0.0006855374069749042}`
- Candidate performance by year: `{"2020": {"avg_top12_hits": 1.4423076923076923, "avg_top18_hits": 2.0865384615384617, "avg_top6_hits": 0.7211538461538461, "draws": 104}, "2021": {"avg_top12_hits": 1.53, "avg_top18_hits": 2.28, "avg_top6_hits": 0.67, "draws": 100}, "2022": {"avg_top12_hits": 1.4951456310679612, "avg_top18_hits": 2.2427184466019416, "avg_top6_hits": 0.7378640776699029, "draws": 103}, "2023": {"avg_top12_hits": 1.2666666666666666, "avg_top18_hits": 2.038095238095238, "avg_top6_hits": 0.6571428571428571, "draws": 105}, "2024": {"avg_top12_hits": 1.2403846153846154, "avg_top18_hits": 1.9615384615384615, "avg_top6_hits": 0.6346153846153846, "draws": 104}, "2025": {"avg_top12_hits": 1.3714285714285714, "avg_top18_hits": 2.2285714285714286, "avg_top6_hits": 0.6857142857142857, "draws": 105}}`

## Frozen ten-gate decision

1. `aggregate_candidate_top12_lift_strictly_positive`: `false`
2. `aggregate_candidate_holm_adjusted_exact_p_at_most_0.05`: `false`
3. `aggregate_candidate_top12_bootstrap_lower_strictly_positive`: `false`
4. `candidate_top12_lift_strictly_positive_in_both_halves`: `false`
5. `paired_candidate_minus_v1_top12_bootstrap_lower_strictly_positive_aggregate_and_halves`: `false`
6. `paired_candidate_minus_control_top12_bootstrap_lower_strictly_positive_and_pseudo_bonus_and_random_controls_null_aggregate_and_halves`: `false`
7. `candidate_top6_lift_strictly_positive_aggregate_and_halves`: `false`
8. `candidate_brier_and_log_loss_no_worse_than_fair_or_v1_by_more_than_1e-9_aggregate_and_halves`: `false`
9. `all_anchor_mechanism_log_g_d_candidate_control_conditions_pass`: `false`
10. `no_audit_warning`: `true`

All ten gates passed: `false`.

## Warnings and audit trail

- Scientific/audit warnings: `[]`
- Operational warnings: `[]`
- Opportunity total (deduplicated Final-6 sets): `1484`
- Full per-target probabilities, rankings, Top-K sets, Final-6 sets, scores, calibration inputs, and chronology evidence are retained in the JSON report and hash-chain ledger.
