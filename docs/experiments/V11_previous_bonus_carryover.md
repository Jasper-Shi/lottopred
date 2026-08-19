# V11 Previous-Bonus Carryover Pre-registration

## Frozen identity and status

| Field | Frozen value |
|---|---|
| Experiment | `V11_previous_bonus_carryover` |
| Descriptive family | `cross_draw_role_transition` |
| Multiplicity family / variant | `transition_markov` / `3` |
| Candidate | `v11_previous_bonus_carryover` |
| Targeted control | `v11_previous_bonus_carryover_pseudo_bonus_control` |
| Fair sanity control | target-date-seeded `random v1.0.0` |
| Version / seed | `v11.0.0` / `649` |
| Primary | Top-12 hits lift versus exact fair theory |
| Registration date | 2026-08-19 |
| Status | **REGISTERED — NOT IMPLEMENTED — NOT SCORED** |
| Live role | none; V1 remains production and V3 remains shadow |

This document freezes one outcome-blind, one-parameter experiment. No V11
historical forecast, score, p-value, confidence interval, hit count, or model
output existed or was inspected when this registration was written. Existing
V1--V10 results were consulted only to avoid duplicating a prior hypothesis and
to preserve the append-only multiplicity record. The expected result is null.
A sound negative result is a successful research outcome.

The sole historical run authorized here covers 2020--2025 and is permanently
labelled a **consumed historical diagnostic**. It is simulated chronological
out-of-sample evaluation, not blind, confirmatory, or prospective evidence.
There is no result-driven alternative, sign choice, window, prior scale,
control seed, threshold, or rerun.

The primary-source and mathematical review is in the unscored
[V11 basis note](../research/V11_previous_bonus_carryover_basis.md). The
machine-readable authorities are the V11 row of
[`registry.yaml`](registry.yaml) and the dedicated
[`research-v11-previous-bonus-carryover.yaml`](../../config/research-v11-previous-bonus-carryover.yaml).
Their complete `parameters` / `research` mappings must be literally equal.

## Hypothesis and information boundary

The one registered hypothesis is that, in the current RNG era, the published
bonus label of the immediately preceding draw has a stable signed residual
tendency to appear among the next draw's six main labels after conditioning on
the frozen V1 ensemble marginal for that label.

This is a test of published final-output serial dependence. It is not a claim
about RNG call order, software state, misconduct, or a physical mechanism. The
reviewed public sources do not expose those internals. The target is always the
unordered six-main set. The target draw's bonus is excluded from prediction,
training responses, ranking, scoring, and all gates.

The RNG boundary is the externally documented `2019-05-15` transition. For a
target date `t`, order all verified draws strictly before `t` by date. An
eligible training row is one adjacent source/destination pair for which both
draws are on or after the boundary and the destination date is strictly before
`t`. If the source draw is `s-1` and destination is `s`, define

```text
b_s = published bonus label of source draw s-1
y_s = 1[b_s belongs to the six main labels of destination draw s].
```

For destination `s`, independently reconstruct the frozen V1 ensemble using
every verified draw before `s`, including pre-RNG history, and no draw on or
after `s`. Let its 49 marginals be `q_(s,i)` and set `q_s=q_(s,b_s)`. Thus every
training probability is itself a nested strict-prefix forecast. Reusing a
full-block V1 fit or a cache keyed only by length/tail date is leakage.

For the current target, the anchor `b_t` is the bonus of the latest verified
draw before `t`, and `q_b=q_(t,b_t)` comes from the original V1 forecast for
`t`. The target main set is unavailable until the complete forecast has been
durably frozen. Earlier revealed transitions may enter the estimate; the
transition ending at `t` may not.

Candidate and control use the same original draw history and the same original
49-value V1 forecast at every destination. Bonus-role manipulation never
rewrites V1 history. A fresh V1 model graph is constructed per destination;
any persisted forecast cache must bind the complete prefix SHA-256 and
destination date.

## Frozen V1 base

The base is `ensemble v1.0.0` at repository commit
`86549d2650fe98cd48375fa77b5b8521ca271df2` and `config.yaml` SHA-256
`b67b6cd4e1ace10275da6142fbb8739c1de0e91c37a7f636e42d2c0f4d862ff5`.
Its members are long frequency `0.15`, recent-frequency-100 `0.20`, EMA/gap
`0.20`, and logistic `0.45`; logistic uses training `480`, minimum `300`,
stride `4`, `C=0.25`, and `max_iter=500`.

The following source hashes are frozen:

| Path | SHA-256 |
|---|---|
| `src/lotto649/models/baselines.py` | `76f9050a13bde44d51584397ecd6acb358f320e1617ef329b70bd6a22d23e28a` |
| `src/lotto649/models/logistic.py` | `886367c16ed0f0d1109aacb943a3393e63807a31e7710bd0e664e06f6f3c4da2` |
| `src/lotto649/models/ensemble.py` | `9b2a3fb3156efb3ff248fa6debecfd7a92b718e9517d8da0e3a5fc43da7c0047` |
| `src/lotto649/models/factory.py` | `d0d3043656144a469b1677491c11cde3143a65b026c2a815485cc89ae5d48fcc` |
| `src/lotto649/features.py` | `b7bc67b9038b2e3d78230c3087c3ac4e3f17751aeab678574f3601af00671979` |
| `src/lotto649/models/base.py` | `e2f0c90c376ea6063b906bcca042e8903b351a1ed4b76e9d83e17be3bcf166ec` |
| `src/lotto649/domain.py` | `fbcb22747ae361767df070c6e50af49fda1aa190b72fd39894afa1c879a50b7a` |
| `src/lotto649/config.py` | `7563042563ec197de01120bf2d4267d9f089875defdfa95da8323d9f5702e862` |

V11 may neither refit nor reweight V1 because of a V11 result. Each V1 vector
must contain exactly integer labels `1..49`, finite values strictly in `(0,1)`,
and satisfy `abs(math.fsum(q_i in ascending label order)-6)<=1e-12`.

## One scalar N(0,1) MAP estimate

For a prefix containing `D` eligible transition rows, define

```text
logit(q) = log(q) - log1p(-q)
r_s(beta) = sigmoid(logit(q_s) + beta)
residuals_in_target_date_order =
    [y_s-r_s(beta) for s in destination-date order]
U(beta) = math.fsum([-beta, *residuals_in_target_date_order]).
```

The prior is exactly `beta ~ N(0,1)` with variance and scale exactly one. The
MAP is the unique root `U(beta)=0`, because

```text
U'(beta) = -1 - sum_s r_s(beta)(1-r_s(beta)) < 0.
```

There is no coefficient grid or estimated prior scale. Evaluate the logit as
shown. Evaluate sigmoid with `1/(1+exp(-z))` when `z>=0` and
`exp(z)/(1+exp(z))` when `z<0`. All arithmetic is CPython 3.12 IEEE-754
binary64. Build one list whose first element is `-beta` and whose remaining
elements are chronological residuals, then call `math.fsum` once. Summing the
residuals first and adding `-beta` afterward is a different, prohibited
binary64 program.

The solver is uniquely specified:

1. If `D==0` or binary64 `U(0.0)==0.0`, return positive `0.0` exactly.
2. Otherwise set `B=float(D+64)`. If `U(0)>0`, use `[0.0,B]`; otherwise use
   `[-B,0.0]`.
3. Require strictly `U(lower)>0>U(upper)`. Bracket expansion is prohibited.
4. Perform exactly 256 iterations. Set
   `mid=lower+(upper-lower)/2`. If `U(mid)>0`, set `lower=mid`; otherwise set
   `upper=mid`. Equality therefore takes the upper branch.
5. Do not exit on tolerance. Return
   `lower+(upper-lower)/2` after iteration 256.

The dynamic bracket is guaranteed in exact reasoning: its linear prior term
dominates at least 64 beyond the maximum absolute sum of `D` Bernoulli
residuals. Failure of a required binary64 bracket, finite-value, or oracle
check is an audit failure, not permission to repair the solver.

Literal solver oracles are:

- four rows with every `q=6/49` and `y=[1,0,0,1]` yield
  `beta=0.9440698092952482`, hex `0x1.e35d1e3820caep-1`, and common
  `r=0.26398254767618795`, hex `0x1.0e5170e3ef9a9p-2`;
- `q=[0.5,0.5]`, `y=[1,0]` takes the exact `U(0)==0` branch and returns
  beta hex `0x0.0p+0`.

## Direct marginal tilt and conservation

For the current anchor, calculate

```text
r_b = sigmoid(logit(q_b)+beta).
```

If beta is positive zero, or the nonzero calculation nevertheless makes
binary64 `r_b==q_b`, return the original V1 mapping bit for bit. Do not perform
a logit round-trip, copy through another numeric type, normalize, or retie the
ranking. This is the exact feature-off ablation.

Otherwise set `p_b=r_b` and, for every `i != b`, use exactly one branch:

```text
if r_b > q_b:
    p_i = q_i * (6-r_b)/(6-q_b)

if r_b < q_b:
    p_i = q_i + (q_b-r_b)*(1-q_i)/(42+q_b).
```

The negative denominator is **`42+q_b`**, because

```text
sum_(i != b) (1-q_i) = 48-(6-q_b) = 42+q_b.
```

The rising branch preserves all non-anchor probability ratios; the falling
branch preserves all non-anchor remaining-capacity ratios. Both preserve their
ordering. Consequently every Top-K prefix changes from V1 by at most one label,
and sorted marginal Top-6 changes by at most one replacement.

Iterate labels in ascending numeric order. Require exact keys `1..49`, finite
probabilities strictly in `(0,1)`, and
`abs(math.fsum(p_i)-6)<=1e-12`. Clipping, residual repair, rescaling, or
post-normalization is prohibited. Rank by descending probability with exact
ties resolved by ascending number. Emit the full ranking, Top-6/12/18 prefixes,
and the final combination as the numerically sorted marginal Top-6.

For the synthetic V1 vector `q_1=0.2`, `q_2..q_49=29/240`:

| beta | anchor result | each non-anchor result | binary64 sum |
|---|---|---|---|
| `log(2)` | `0x1.5555555555555p-2` | `0x1.e38e38e38e38fp-4` | `6.000000000000001` |
| `-log(2)` | `0x1.c71c71c71c71ep-4` | `0x1.f684bda12f685p-4` | `6.0` |
| positive `0.0` | original values bit for bit | original values bit for bit | original V1 sum |

A 48-dimensional maximum-entropy inverse, odds conditioning, fixed-six V1
joint completion, joint MAP combination, or other redistribution is outside
`v11.0.0`. V1 supplies marginals, not an identified six-set joint law.

## Deterministic pseudo-bonus control

The control changes only the anchor role. For each source draw, form its sorted
seven-label union of main plus bonus. For every member `label`, hash the exact
UTF-8 payload

```text
lotto649-v11-bonus-anchor-control-v1:649:{ISO-date}:{label}
```

Select the label with the smallest full 32-byte SHA-256 digest, with ascending
label as the digest-tie fallback. Identity is allowed and there are no retries.
Use the selected pseudo bonus as the control anchor, leaving the original main
history, seven-set, dates, next-main response, target, and all 49 V1 marginals
unchanged. The control fits its own beta through the identical strict-prefix
solver and uses the identical marginal transfer and scoring code.

For source date `2020-01-01` and union `{1,2,3,4,5,6,7}`, the unique selected
label is `4`; its digest must be
`1052da1f3ebf9c1bfe2f06998f13ebc812c01dd08fd9b0b21cc20fd35d0840c8`.
The registry enum is `within_draw_bonus_reassignment`, seed `649`. A changed
seed, payload, digest truncation, rejection of identity, or repeated draw is a
new experiment.

This is the one registered targeted negative control. It can expose a generic
prior-seven-label or prior-main effect because V1 already accounts for the
main-only history. It never supports the V11 bonus-specific claim.

A global randomized/conditional role audit is explicitly deferred and excluded
from `v11.0.0`. It has no frozen exact conditional null in this registration,
must not be implemented or run by the V11 runner, is not a gate, and cannot be
described as an inspected V11 hypothesis. Only the deterministic SHA control
above belongs to this version.

## Target-date fair-random benchmark

The project-wide random benchmark also runs on exactly the same 621 target
dates. For target date `t`, use the frozen `random v1.0.0` implementation:

```text
seed = 649000000 + t.toordinal()
```

Initialize `numpy.random.default_rng(seed)`, draw one
`Uniform(-1e-9,1e-9)` jitter for each ascending label, add it to `6/49`, and
apply the frozen `normalize_expected_six` implementation. This outcome-
independent model never enters beta fitting, Holm, or a candidate-versus-random
discovery claim. It is a descriptive fair sanity control and an independently
frozen Final-6 opportunity. It must behave as null in the aggregate and both
fixed halves; otherwise the audit is not clear. This control is distinct from,
and does not revive, the deferred global role-randomization audit.

## Multiplicity and overlap ledger

V11 is conservatively variant 3 in the append-only `transition_markov` Holm
family:

1. V2 used a previous-main transition feature;
2. V3 was a separate transition-bearing nonlinear candidate;
3. V11 tests previous-bonus-to-next-main residual recurrence.

The published V2/V3 summaries do not supply primary p-values compatible with
this exact registered Top-12 convolution. Each prior entry therefore enters
the family as `p=1.0`; it is never silently dropped. The registered family size
is three. For V11's aggregate raw primary p-value the resulting adjustment is
`min(1,3*p_raw)`, expressed through the general Holm step-down algorithm.

V1's `in_prev` feature is an operational baseline, not a newly registered
discovery attempt. V4 is a frozen mixture, not a new transition hypothesis.
V5 is a prior-main pair family, V7 is same-draw main/bonus role bias, V9 was an
unimplemented within-draw union proposal, and V10 is within-draw adjacency.
These overlaps remain disclosed but do not reset or enlarge this conservative
three-entry family. A later transition/Markov attempt must append a new variant.

## Evidence boundary and fixed historical lane

The registered data object is:

- `data/processed/draws.csv`;
- source commit `90177c80cfb070038d79508fb2e73305a297f516`;
- SHA-256 `edfb7f8a4a7711a630957d6f86b567e6b254caf7b1d1aaea0edf1d16a34155b3`;
- 4,432 rows through 2026-08-15.

The implementation must recover and verify that exact Git blob and fail on a
missing, changed, duplicated, reordered, conflicting, or interior-revised row.
Appended future rows cannot alter the registered historical target sequence.

| Scope | Dates | Targets | Interpretation |
|---|---|---:|---|
| Prefix only | inception through 2019-12-31 | 0 scored | V1 history and post-RNG transition training |
| Aggregate | 2020-01-01 through 2025-12-31 | 621 | consumed historical diagnostic |
| First half | 2020-01-01 through 2022-12-31 | 307 | mandatory gate scope |
| Second half | 2023-01-01 through 2025-12-31 | 314 | mandatory gate scope |
| Known 2026 | through 2026-08-15 | 0 scored | consumed and excluded |

All 621 targets are mandatory unless the audited early 6/6 branch below fires.
There is no best year, chosen side of beta, pre/post split, rolling window,
minimum-event rescue, skipped loss, subgroup, or extension.

## Scores and required output

The sole formal primary is

```text
mean Top-12 main hits - 72/49.
```

Conditional on any strict-prefix adaptive Top-12, one draw's fair hit count is
`Hypergeometric(N=49,K=12,n=6)`. Convolve that integer law over complete target
draws and use the exact one-sided upper tail. Only the aggregate candidate p
enters Holm. Top-6 and Top-18 fair means are `36/49` and `108/49`.

For every scope and contrast, initialize a fresh
`numpy.random.default_rng(649)`, draw exactly 10,000 complete aligned target
rows with replacement, and use a two-sided 95% percentile interval with
`numpy.quantile(method="linear")`. Paired candidate-minus-V1 and
candidate-minus-control Top-12 differences are formed per target before
resampling. Labels within a draw are never resampled.

Per-target Brier and binary log loss are calculated in ascending label order:

```text
Brier = math.fsum((p_i-y_i)^2)/49
LogLoss = -math.fsum(log(p_i) if y_i else log1p(-p_i))/49.
```

Aggregate in target-date order with `math.fsum/draw_count`. There is no clipping
because the probability contract is open interval. Compare candidate scores to
both exact fair `6/49` and the original V1 ensemble.

For the anchor event after reveal, record the log e-factor

```text
log_g_t = y*log(r_b/(6/49)) + (1-y)*log((1-r_b)/(43/49))
d_t = y*log(r_b/q_b) + (1-y)*log((1-r_b)/(1-q_b)).
```

Evaluate only the observed `y` branch; do not multiply a divergent expression
by zero. The exponential of cumulative `log_g` is the fair-null anchor
e-process.
The same `r_b` used in the forecast is used here. Equivalently, `log_g` is the log
ratio obtained by uniformly distributing mass within the anchor-present and
anchor-absent six-set strata; that identity does not turn V1 or V11 into an
integrated joint prediction law. Sum per-target values in date order with
`math.fsum`.

Each frozen bundle must include target/prefix identities, prefix digest,
history-through, anchor, `D`, beta, `q_b`, `r_b`, and candidate/pseudo-control/
V1/random full 49 probabilities, full rankings, Top-6/12/18, and sorted final
six. Only after reveal add the actual six-main set, anchor response, all hits
and actual ranks, Brier/log loss, `log_g`, `d`, and the opportunity record.

Aggregate, halves, and candidate/control/V1/random summaries must include
Top-K means and lifts, exact p-values where applicable, intervals, paired
contrasts, proper scores, anchor gains where defined, mean actual rank, every
exclusion/warning, and the final-six histogram with explicit keys `0..6`.
Emit fixed-year diagnostics and ten fixed equal-width calibration bins,
including empty bins, with cell count, mean forecast, observed inclusion rate,
and ECE. Years, random-control results, and calibration are descriptive and
cannot rescue a gate.

## Exact ten-gate decision

The historical scientific decision is one conjunction. Every item must pass:

1. aggregate candidate Top-12 lift is strictly positive;
2. aggregate candidate Holm-adjusted exact p-value is at most `0.05`;
3. aggregate candidate Top-12 bootstrap lower endpoint is strictly positive;
4. candidate Top-12 lift is strictly positive in both fixed halves;
5. paired candidate-minus-V1 Top-12 bootstrap lower endpoint is strictly
   positive in the aggregate and both halves;
6. paired candidate-minus-control Top-12 bootstrap lower endpoint is strictly
   positive in all three scopes, and both the pseudo-bonus control and target-
   date random control behave as null in every scope (`p>0.05` or the relevant
   interval includes zero);
7. candidate Top-6 lift is strictly positive in all three scopes;
8. candidate Brier and log-loss deltas versus both fair and V1 are each at most
   `1e-9` in all three scopes;
9. the anchor-mechanism conjunction passes: candidate aggregate `sum(log_g)`
   is at least `log(20)=2.995732273553991`; candidate `sum(log_g)` and `sum(d)`
   are positive in each half and aggregate `sum(d)>0`; control aggregate
   `sum(log_g)` is strictly below `log(20)`; and aligned candidate-minus-
   control `log_g` and `d` sums are positive in the aggregate and both halves;
10. no chronology, leakage, data, Git, source, V1-base, control, numeric,
    probability, serialization, claim, ledger, opportunity, output, or other
    audit warning exists.

A valid scientific failure is **Reject**. An audit failure is **Archive**.
Passing all ten only makes unchanged `v11.0.0` eligible for a separately
reviewed shadow decision. It does not activate V11, promote it, change V1, or
change V3. There is no secondary, Top-18, half, proper-score, mechanism, or
near-miss rescue.

## One-shot claim and hash-chained ledger

No workflow may run this diagnostic automatically. After all implementation
tests and preflight checks pass from a clean, pushed, CI-green exact HEAD, but
before any operation that creates a candidate, pseudo-control, V1, or random
forecast or score, acquire
these paths exclusively:

```text
reports/v11_previous_bonus_carryover_v11.0.0_historical.claim
reports/v11_previous_bonus_carryover_v11.0.0_historical.ledger.jsonl
reports/v11_previous_bonus_carryover_v11.0.0_historical.json
reports/v11_previous_bonus_carryover_v11.0.0_historical.md
```

Any existing claim, ledger, final, or staging artifact refuses execution. The
claim is permanent on success, failure, crash, or audit stop. It binds the
registration and implementation commits, exact command, config/data/source
hashes, seed, CPython 3.12, `requirements-live.lock` SHA-256
`2fea4cf73cc2578b73c21e6600e31ad843bd903e8a2656b7a2543164ab8d801c`,
platform, and installed distributions.

The JSON-lines ledger has contiguous zero-based sequence numbers. Each event is
canonical finite JSON and binds the preceding event hash. For each target, a
`prediction_frozen` event contains the deterministic full candidate, pseudo-
bonus control, V1, and random payload and its SHA-256. Its wall-clock RFC3339
UTC `Z` timestamp is
outside that deterministic payload and never enters a forecast. Append, flush,
and file-`fsync` this event before the current target's main or bonus field can
be retrieved or passed to scoring. Then append and `fsync`
`target_revealed_scored` before forecasting the next target. Repeated calls on
the same prefix must produce byte-identical forecast payloads.

Any post-claim exception consumes the only attempt. It is preserved as Archive
evidence and cannot be erased and rerun under `v11.0.0`. Final JSON/Markdown
publication uses same-directory staging, `fsync`, and exclusive no-overwrite
publication, rejects NaN/Infinity, and retains every gate, warning, hash, and
failure.

## 6/6 opportunity ledger and breakthrough branch

At each reveal, collect the candidate, pseudo-bonus control, V1 ensemble, and
target-date random sorted final-six sets. Deduplicate identical sets on the
same target; in particular, a feature-off candidate identical to V1 is one
opportunity, not two. For each unique set, the primary producer is the first
matching entry in the frozen `opportunity_models` order. Its model name is used
in the breakthrough path, while the bundle records every matching
`producer_model_names` entry in that same order. Exactly one bundle, opportunity,
and alert is permitted for a target/unique-set pair. Let `u_t` be the number of
unique sets (`1..4`). The durable scored event records each set, all producing
model names, `producer_forecast_sha256_by_model` in the same registered order,
actual set, hits, chronology status, `u_t`, cumulative unique opportunities,
and cumulative fair probability

```text
-expm1(fsum_t(log1p(-u_t / C(49,6))))
```

with `C(49,6)=13,983,816` and targets in date order. These full-snapshot records
are eligible for the append-only global historical-OOS evidence ledger. Missing
legacy snapshots stay explicitly unknown; they are never reconstructed after
reveal or silently treated as new opportunities.

Top-12 containing all six is recorded and alerted immediately but is explicitly
**not** an exact final-six success. If any newly frozen unique final six equals
the target main set, first append and `fsync` a
`historical_6of6_candidate_detected` event, then stop before another target.
Run the complete chronology, preprocessing, feature-selection, target,
future-data, claim, and model-selection leakage audit without retraining or
changing any value.

Publish, without overwrite, the full bundle
`reports/historical-6of6-candidate__{target_date}__{model_name}__v11.0.0.json`
with forecast, actual, prefix, source/implementation commits, runtime, claim and
ledger hashes, opportunity count/chance, and completed audit. A control hit is
validly recorded but never supports the V11 bonus mechanism or activation.
Only an audit-clear exact frozen final-six record may trigger the Chinese alert
`🚨 [LOTTO649] 历史严格回测成功预测 6/6` and stop broader model search. Email
failure preserves the evidence and emits a warning.

If leakage audit fails, preserve the bundle as Archive evidence, emit
`⚠️ [LOTTO649] 历史 6/6 候选泄漏审计失败`, prohibit the success event, and do
not resume or rerun V11. An early branch does not fabricate a 621-target report
or scientific gates. Normal completion requires exactly 621 scored targets.

## Implementation and prospective boundaries

The commit containing this registration must be an ancestor of the later V11
implementation commit. Before claim acquisition, that exact clean/pushed
implementation commit must differ from the registration commit in exactly five
required source/test paths and three required non-behavioral status documents:

```text
src/lotto649/models/v11_previous_bonus_carryover.py
src/lotto649/v11_diagnostics.py
tools/run_v11_historical.py
tests/test_v11_previous_bonus_carryover.py
tests/test_v11_diagnostics.py
docs/CODEX_HANDOFF.md
docs/MODEL_PROTOCOL.md
docs/RESEARCH_ROADMAP.md
```

The three documentation diffs may state only **implemented / not scored / not
activated** and may not change a formula, gate, evidence interpretation, or
execution rule. Every other changed path is prohibited. This registration does
not create the five implementation files, authorize a diagnostic run, or modify
factory, CLI, live, production `config.yaml`, V1, or any V3 frozen path. The
dedicated config has live and notifications disabled and lists only the
candidate, pseudo-bonus control, V1 ensemble, and target-date random benchmark
for the diagnostic.

V11 prospective status is `not_activated`: freeze commit, activation commit,
activation-known outcomes, and cohort start are all null. A separate reviewed
freeze/activation/release sequence may later activate the unchanged model as
shadow. Its sole formal look is exactly 208 eligible, evaluated, immutable
pre-draw snapshots, positionally split 104/104, using the same inference and
ten-gate conjunction. There is no early look, backfill, extension, or automatic
promotion. Any behavior changed after an observed result requires a new version
and consumes every outcome that influenced it.

## Authority ledger

Repository authorities are [`AGENTS.md`](../../AGENTS.md),
[`MODEL_PROTOCOL.md`](../MODEL_PROTOCOL.md),
[`V2_V4_RESULTS.md`](../V2_V4_RESULTS.md),
[`RESEARCH_ROADMAP.md`](../RESEARCH_ROADMAP.md), the
[V11 basis note](../research/V11_previous_bonus_carryover_basis.md), and the
frozen registry/config literals linked above. External sources and their
strictly bounded interpretation are indexed in the basis note. None provides
evidence that a certified fair lottery is predictably exploitable.
