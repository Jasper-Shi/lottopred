# V5 Pair-Affinity Implementation Audit

## Status and scope

**This is a pre-score implementation audit.** It maps the frozen
`V5_pair_affinity` / `v5_pair_affinity` / `v5.0.0` registration to code and
synthetic-test surfaces before the candidate is scored; it does not assert that
an implementation is complete. No candidate score on committed historical draws
was run or inspected for this audit, and nothing here is evidence that the
hypothesis works.

The normative sources are the
[pre-registration](V5_pair_affinity.md#exact-candidate-specification), the
[machine-readable registry](registry.yaml), the
[model protocol](../MODEL_PROTOCOL.md#non-negotiable-no-future-leakage), and the
[V5+ research loop](../RESEARCH_ROADMAP.md#research-loop). If an implementation
choice conflicts with one of those sources, the registration wins; a behavioral
change requires a new version and a new prospective cohort.

Implementation must remain separate from activation. Registering the class in
the model factory is not permission to add it to `config.yaml`, the live suite,
or an existing prediction snapshot. Those are later, reviewed freeze/live
actions under the
[prospective-cohort rule](V5_pair_affinity.md#prospective-cohort-and-stopping-rule).

## Intended code and test surfaces

| Surface | Intended responsibility |
|---|---|
| `src/lotto649/models/v5_pair_affinity.py` (new) | A statistically pure `V5PairAffinityModel` implementing only the frozen count, residual, score, and probability equations. Constants are named and fixed; the constructor exposes no tuning choices. Any internal cache must be exact-prefix-safe and behaviorally invisible. |
| [`src/lotto649/models/factory.py`](../../src/lotto649/models/factory.py#L11-L46) | Import and make `v5_pair_affinity` explicitly requestable. Do not add it to any default configured suite. |
| [`src/lotto649/research_protocol.py`](../../src/lotto649/research_protocol.py#L223-L314) | Own registration loading, strict-prefix folds, the one whole-draw negative control, fingerprints, and cohort accounting. |
| `src/lotto649/research_diagnostics.py` (new) | Own the exact registered inference, three fixed evidence lanes, comparison set, control scoring, data-fingerprint gate, and reproducible JSON/Markdown report. |
| [`src/lotto649/backtest.py`](../../src/lotto649/backtest.py#L15-L53) | Reuse prediction construction/ranking through validated `walk_forward_folds`, with per-model versions supplied by the registered research config. The generic summary is still not the V5 inference report. |
| [`src/lotto649/evaluation.py`](../../src/lotto649/evaluation.py#L9-L46) | Reuse the existing per-draw Top-K, Brier, binary-log-loss, and actual-rank definitions unchanged. |
| `tests/test_v5_pair_affinity.py` (new) | Synthetic-only formula oracle, boundary, probability-contract, determinism, bonus-exclusion, and prefix-invariance tests. |
| [`tests/test_research_protocol.py`](../../tests/test_research_protocol.py#L37-L200) | Generic registry, negative-control construction, chronology, fingerprint, and prospective-accounting tests. |
| `tests/test_research_diagnostics.py` (new) | Registered exact-inference, bootstrap, fair-score, multiplicity, and secondary-metric tests. No committed-draw candidate score belongs in the unit suite. |

## Frozen specification-to-surface map

### Identity, information set, and eligibility

| Frozen item | Exact implementation mapping | Required pre-score test |
|---|---|---|
| Experiment `V5_pair_affinity`; model `v5_pair_affinity`; version `v5.0.0`; seed `649` | Keep the identity in [`registry.yaml`](registry.yaml) authoritative. The class `name` is exactly `v5_pair_affinity`; registered reports obtain the version and seed from the registration, not the global `project.model_version`. | Load the registry and assert identity, seed, family `pair_cooccurrence`, multiplicity family `v5_pair_cooccurrence`, and variant index `1`. |
| For target date `t`, use the complete date-ordered prefix `H_t` with every draw date strictly `< t` | The model begins with [`assert_history_precedes_target`](../../src/lotto649/research_protocol.py#L256-L263). Registered evaluation uses [`walk_forward_folds`](../../src/lotto649/research_protocol.py#L275-L287), whose history is exactly `draws[:index]`. | Reject empty, duplicate, out-of-order, target-in-history, and future-in-history inputs. For every synthetic fold, assert `history == tuple(draws[:index])`. |
| `D = len(H_t)`, expanding history, no rolling window, minimum `D = 300` | Count every visible draw on every call. The model itself raises before prediction when `D < 300`; the backtest minimum is not an adequate substitute. | `299` visible draws raises; `300` succeeds; changing a configuration minimum cannot weaken the model guard. |
| Lag-one anchors are exactly the six main numbers in `H_t[-1]` | Read `history[-1].numbers`; never use the target, target date fields other than the boundary check, or a bonus. Candidate `n` excludes itself from the anchor tuple. | Histories differing only in valid bonus labels produce bitwise-equal probabilities. An anchor-membership oracle verifies six anchors for absent `n`, five for `n` in the last draw, and no self-pair. |

The backtest now enters through validated strict-prefix folds, but its minimum
history and per-model versions remain configuration inputs
([`run_backtest`](../../src/lotto649/backtest.py#L36-L49)). The registered V5
runner therefore verifies the frozen dataset, full comparison list, 300-draw
minimum, and registry-matched `v5.0.0` before scoring; silently routing the model
through generic defaults remains invalid.

### Counts, shrinkage, and residuals

For candidates and anchors, iteration order is fixed as candidates `1..49` and
ascending prior-draw anchors. All counts use main-number membership in the same
strict prefix; bonus labels are never counted.

| Frozen equation/value | Exact implementation mapping | Required pre-score test |
|---|---|---|
| `C_n = sum(1[n in draw.numbers] for draw in H_t)` | A marginal count for every label `1..49` representing all `D` visible draws. | Independent synthetic count oracle for selected present/absent labels. |
| `C_a` uses the identical history and marginal definition | Reuse the same marginal-count table for an anchor; do not count only recent draws or anchor occurrences after a cutoff. | Assert `C_a` equals the independently counted anchor frequency. |
| `C_na = sum(1[n and a in draw.numbers] for draw in H_t)` | Same-draw, intact main-number co-occurrence; diagonal pairs are never requested because `a != n`. | Hand-count selected symmetric pairs and assert `C_na == C_an`; changing bonuses has no effect. |
| Prior strength `250`; marginal prior `6/49` | Compute `q_n = (C_n + 250 * (6/49)) / (D + 250)` using floating-point division only after integer counts are complete. | Independent formula oracle checks several labels, including zero/additional counts. |
| Conditional prior `5/48` and the same strength `250` | Compute `q_n_given_a = (C_na + 250 * (5/48)) / (C_a + 250)`. The denominator is `C_a + 250`, never `D`, `C_n`, or `C_a + 250 * 5/48`. | Oracle checks a pair whose `C_a`, `C_n`, and `D` differ so denominator substitutions fail. |
| `logit(x) = log(x / (1-x))` | Compute `residual(n,a) = logit(q_n_given_a) - logit(q_n)` with the fixed priors providing interior probabilities. Do not clip, calibrate, or add another epsilon. | Compare selected residuals to an independent `math.log(x/(1-x))` oracle at tight tolerance and assert finiteness. |

The implementation uses an integer-count prefix cache only as a performance
optimization. It verifies exact tuple-prefix extension and clears/rebuilds for a
shorter or branched history. Synthetic tests compare it with a stateless full
recount, exercise repeat/long-then-short calls, and require bitwise-identical
predictions, so the cache cannot change the registered statistic.

### Candidate score and probability mapping

| Frozen equation/value | Exact implementation mapping | Required pre-score test |
|---|---|---|
| `A_t(n) = H_t[-1].numbers \ {n}` | Preserve the sorted tuple order while excluding only exact equality. It has length five when `n` was in the prior draw and six otherwise. | Explicit five-versus-six anchor test; ensure no set iteration determines floating summation order. |
| `score_n = mean(residual(n,a) for a in A_t(n))` | Arithmetic mean over exactly that five- or six-residual tuple; no sum, maximum, recency weight, or learned coefficient. | Independent score oracle for one prior-draw member and one non-member. |
| Cross-sectional `mu = mean(score_1..score_49)` | Use all 49 current-fold scores in ascending label order. No historical/future score enters the transform. | Oracle asserts the exact 49-value population mean and detects omitted labels. |
| Population `sigma = sqrt(mean((score_n-mu)^2))` | Use population variance (`ddof=0`), not pandas' default sample standard deviation. | A non-degenerate synthetic history must match a population-standard-deviation oracle and differ from a `ddof=1` oracle. |
| Epsilon exactly `1e-9` | `z_n = (score_n - mu) / (sigma + 1e-9)`. The epsilon is added after the square root; it is not inside the variance and is not configurable. | Include a degenerate-score helper/oracle case and assert finite `z`; lock the literal against the registry value `1.0e-9`. |
| Temperature exactly `0.10` | `raw_n = exp(0.10 * z_n)` using no offset, clipping, or fitted temperature. | Oracle checks raw scores and locks `0.10` against the registry. |
| `p_n = 6 * raw_n / sum(raw_j for j=1..49)` | Return exactly 49 finite, strictly positive values, each `< 1`, summing to six. Compute the denominator in fixed label order. Do **not** pass the result through a second normalization. | Independent end-to-end probability oracle; keys exactly `1..49`; repeat-call dictionary equality; finite/interior values; `sum(p)` within the repository tolerance. |
| Descending probability, exact ties by ascending number | Use [`rank_numbers`](../../src/lotto649/optimizer.py#L7-L8) for Top-6/12/18. | Equal-probability fixture ranks `1..49`; a non-tied fixture follows descending probability. |

[`normalize_expected_six`](../../src/lotto649/models/base.py#L17-L20) is not the
registered V5 equation: it floors missing/nonpositive scores and caps individual
outputs. Applying it after the registered softmax would add an unregistered
transformation and could also disturb the exact total if a cap were reached.
`v5.0.0` should compute and return the registered normalization directly, then
fail loudly if the probability contract is violated.

The registration explicitly fixes `combination_constraints = none`,
`calibration = none`, and `ensemble_members = none`. The model must not call
`select_combination`, fit a transform, accept alternate windows/priors/scales, or
blend another model. Generic prediction construction may populate a descriptive
`final_combination`, but final-combination performance is not a registered V5
outcome and cannot alter its ranking or decision.

## Evaluation and inference map

These surfaces are required before any historical report can be called valid;
they are not needed to unit-test the candidate equations.

| Frozen outcome/inference | Exact reporting surface and test oracle |
|---|---|
| Primary lift | From each eligible target's `top_12_hits`, compute `mean(h12_t) - 72/49`. Reuse exact-hit construction in [`evaluate_prediction`](../../src/lotto649/evaluation.py#L31-L45). Synthetic tests check zero, fair-expectation, positive, and negative fixtures. |
| Primary p-value | Deterministically convolve the draw-level `Hypergeometric(N=49,K=12,n=6)` PMF and report the **one-sided upper tail** `P(sum X >= observed total)`. This belongs in registered research inference, not the generic summary, and must be tested against one-draw combinatorial probabilities and small brute-force convolutions. |
| Primary confidence interval | Resample draw-level `h12_t` values 10,000 times with a **fresh** `numpy.random.default_rng(649)` for each registered calculation; take the two-sided 95% percentile interval for mean lift. Test repeat-call equality and fixed synthetic quantiles. Never reuse a stream whose state depends on which comparison ran first. |
| Bounded secondary set | Report only Top-6 lift vs `36/49`, Top-18 lift vs `108/49`, mean Brier, mean binary log loss, and mean actual rank as secondary outcomes. The proper-score/rank definitions are frozen in [`evaluation.py`](../../src/lotto649/evaluation.py#L9-L28). Report every item regardless of sign. |
| Fair proper-score comparator | Build the constant probability map `{n: 6/49 for n in 1..49}` on the identical target outcomes. Do not substitute the jittered random ranking baseline for the constant proper-score baseline. |
| Operational comparison set | On identical eligible target dates, include deterministic `random`; V1 `long_frequency`, `recent_frequency`, `ema_gap`, `logistic`, and `ensemble`; and shadow reference `v3_boosting`. Request this complete fixed set explicitly from the factory; the present `backtest.models` default is not the registered comparison set. |
| Historical lanes | Report 1982–2014 as development diagnostic, 2015–2019 as exposed legacy validation, and 2020–2025 as consumed historical diagnostic. Never relabel a lane based on its score. The fixed boundaries are enforced in [`research_protocol.py`](../../src/lotto649/research_protocol.py#L17-L22). |
| Multiplicity | Apply Holm step-down adjustment to every recorded variant in `v5_pair_cooccurrence`; missing/invalid raw p-values enter as `1`, family alpha is `0.05`, and the append-only variant denominator may grow. Synthetic p-value vectors test sorting, monotonic adjusted values, missing entries, and family expansion. |

The existing [`summarize`](../../src/lotto649/backtest.py#L68-L100) computes
two-sided normal-approximation p-values. That is useful legacy output but is not
the registered one-sided exact convolution, and must not be quoted as the V5
primary test.

## Negative-control and integrity map

The registered control is already constructed by
[`permute_draw_outcomes`](../../src/lotto649/research_protocol.py#L290-L314):
sort source indices by
`SHA256("lotto649-control-v1:649:{i}")`, rotate an identity order left once, and
zip intact `(six main numbers, bonus)` outcomes onto the unchanged ordered date
slots.

Before score inspection, synthetic tests must additionally prove that:

1. the permutation is created once on the fixed input sequence **before** folds,
   not independently for each expanding prefix;
2. seed `649` is used, dates and the multiset of intact outcomes are preserved,
   and the mapping is deterministic and non-identity when length is greater than
   one;
3. candidate and control enter the same `walk_forward_folds -> predict ->
   rank_numbers -> evaluate_prediction` function with the same 300-draw minimum
   and target-date set; and
4. the control is always labeled synthetic. It blocks promotion if its
   unadjusted one-sided `p <= 0.05` **and** its registered interval is wholly
   above zero; it can never support a prediction claim.

Each report must record experiment ID, model/version, exact command, seed,
effective frozen constants/configuration, data path and file SHA-256, history
boundary, code commit, eligible/excluded fold counts, and the full comparison
set, as required by the
[registration integrity checks](V5_pair_affinity.md#leakage-and-integrity-checks)
and [roadmap validation protocol](../RESEARCH_ROADMAP.md#validation-protocol).
The current registry parser preserves `parameters` as a generic mapping
([`ExperimentRegistration`](../../src/lotto649/research_protocol.py#L98-L147));
therefore a pre-score test must lock every V5 registry parameter to the model's
named constants rather than assume the loader enforces their values.

## Prospective boundary (not part of implementation activation)

The cohort remains `not_activated`, with no freeze commit or start date. Existing
cohort assessment already checks model identity, shadow role, strict
`history_through`, Toronto-local pre-target commit/generation deadlines, commit
identity, snapshot digest, regeneration, source integrity, and evaluation
identity
([`assess_prospective_snapshot`](../../src/lotto649/research_protocol.py#L355-L444)).
No 2026 result available at registration is prospective for `v5.0.0`.

Only a later reviewed activation may set the freeze commit and cohort start and
produce immutable shadow snapshots. The fixed decision is at 104 eligible,
evaluated, exact-version draws, split into the first and last 52. Promotion then
requires all six registered conditions: positive primary lift; Holm-adjusted
one-sided `p <= 0.05` and CI lower bound `> 0`; Brier and log loss no worse than
the constant fair baseline; positive lift in both halves; null-behaving control
and clean audit trail; and a separate reviewed promotion PR. No implementation
or historical diagnostic satisfies that gate.

## Pre-score stop conditions

Do not inspect a committed-data candidate score until all of the following are
true:

- the formula oracle, chronology, minimum-history, bonus-exclusion,
  probability-contract, determinism, and prefix-invariance tests pass on
  synthetic draws;
- registry constants and identity match the code exactly;
- candidate and negative control demonstrably use the same validated synthetic
  pipeline;
- registered inference tests pass without using the generic normal p-value;
- `pytest -q` and `ruff check .` pass; and
- the diff contains no `config.yaml`, live-role, prediction-snapshot,
  evaluation-snapshot, or existing-snapshot changes.

A failed leakage, determinism, probability, source, or snapshot-integrity check
means `Archive` with no performance claim, consistent with the
[registered failure rule](V5_pair_affinity.md#leakage-and-integrity-checks).
