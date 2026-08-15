# V2–V4 Frozen Blind Results

## Test protocol

The confirmatory historical test covered 621 LOTTO 6/49 draws from 2020-01-01 through 2025-12-31. For every target draw, each model saw only earlier draws. The exact fair-draw expectations used as the primary baseline were:

- Top-6: 0.734694 winning numbers per draw
- Top-12: 1.469388
- Top-18: 2.204082

The finite empirical random model is a sanity check only. Model claims are compared with the exact combinatorial expectations.

## Frozen result

| Model | Top-6 | Top-12 | Top-18 | Brier | Log loss | Mean actual rank |
|---|---:|---:|---:|---:|---:|---:|
| Fair theoretical expectation | 0.7347 | 1.4694 | 2.2041 | — | — | — |
| V2 statistical | 0.6779 | 1.3494 | 2.1079 | 0.110425 | 0.384752 | 25.4053 |
| V3 boosting | 0.7407 | 1.5346 | 2.2496 | 0.109469 | 0.380153 | 24.8902 |
| V4 ensemble | 0.7198 | 1.3865 | 2.1401 | 0.108594 | 0.376849 | 25.3164 |
| V1 EMA/gap reference | 0.7198 | 1.4122 | 2.1014 | 0.108918 | 0.378361 | 25.4187 |

### V2

V2 failed the blind test. Relative to theory, its Top-12 result was lower by about 0.120 winning numbers per draw (`p≈0.0027` under the simple hypergeometric-normal diagnostic), and Top-18 was also lower (`p≈0.032`). The added handcrafted combination of sum trend, calendar, transition, omission and multi-scale frequency factors is therefore rejected in its frozen V2 form.

The V2 coefficients must not be retuned on the 2020–2025 answers and then presented as a new blind result.

### V3

V3 was the only research model with positive ranking lift across all three candidate-pool sizes:

- Top-6 lift: +0.0060; `p≈0.843`
- Top-12 lift: +0.0652; `p≈0.103`
- Top-18 lift: +0.0455; `p≈0.310`

None is statistically convincing. In addition, V3's Brier score and log loss are worse than the fair constant-probability baseline, so its slight ranking improvement is not evidence of well-calibrated predictive probabilities.

Year-by-year Top-K performance shows that the apparent lift is not confined to one lucky year, but it is not stable either:

| Year | Draws | Top-6 | Top-12 | Top-18 |
|---|---:|---:|---:|---:|
| 2020 | 104 | 0.7981 | 1.5577 | 2.2596 |
| 2021 | 100 | 0.7900 | 1.6200 | 2.1700 |
| 2022 | 103 | 0.7476 | 1.6311 | 2.1748 |
| 2023 | 105 | 0.8000 | 1.5048 | 2.2571 |
| 2024 | 104 | 0.7404 | 1.5192 | 2.3654 |
| 2025 | 105 | 0.5714 | 1.3810 | 2.2667 |

The 2025 deterioration is a clear warning against treating the aggregate 2020–2025 lift as a durable edge. V3 should therefore remain a **shadow model**, not a promoted primary predictor.

### V4

The frozen V4 ensemble failed to improve on V3 and was below the theoretical baseline at Top-6, Top-12 and Top-18. In particular its Top-12 result was 1.3865 versus the theoretical 1.4694 (`p≈0.038` in the simple diagnostic). Mixing the failed V2 signal into V4 diluted V3 rather than improving it. This V4 design is rejected.

## Decision

- **V2:** rejected; retain only for audit/research history.
- **V3:** retain as a shadow model for genuine future-forward testing; no claim of predictive edge.
- **V4:** rejected; do not promote or post-hoc tune against the same blind period.
- **Production/live:** keep the existing V1 models and add V3 as an explicitly experimental shadow predictor so every future draw produces an immutable pre-draw snapshot.

The next statistically meaningful evidence should come from future draws that were never available during model design. Historical diagnostics can continue, but the 2020–2025 interval is now considered consumed for V2–V4 model selection and must not be reused as an untouched test set.
