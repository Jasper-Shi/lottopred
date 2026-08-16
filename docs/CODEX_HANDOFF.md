# Codex Handoff

Last verified against `main` commit `90177c8` on 2026-08-16.

## Current state

This repository is the execution and audit system. Codex develops and reviews the
code; GitHub Actions runs unattended jobs and commits live artifacts. Chat history
is not required to continue because the research decisions are recorded here and
in `V2_V4_RESULTS.md`.

| Component | Status | Meaning |
|---|---|---|
| V1 live suite | Production baseline | Six models continue to create forward snapshots: `random`, `long_frequency`, `recent_frequency`, `ema_gap`, `logistic`, and `ensemble`. |
| V2 statistical | Rejected | Retained for reproducibility and historical research; absent from the live model list. |
| V3 boosting | Shadow | Creates immutable live snapshots and evaluations beside V1; it does not change V1 predictions or ensemble weights. |
| V4 ensemble | Rejected | Retained for reproducibility and historical research; absent from the live model list. |
| V5 pair affinity | Rejected | `v5.0.0` was implemented exactly, did not establish historical signal, and was closed without shadow activation. It remains absent from live config. |
| V6 entropy regime | Rejected | `v6.0.0` failed its frozen historical gates and was closed without shadow activation. Its research config explicitly disables live execution. |
| V7 main/bonus role bias | Implemented; unscored | `v7.0.0` is frozen on a feature branch with a dedicated within-draw role control. It has no live role and no historical result yet. |
| 2020–2025 blind period | Consumed | It cannot confirm a tuned V5+ model. |
| 2026+ snapshots | Prospective evidence | Evidence belongs to the exact frozen version that created each pre-draw snapshot. |

No version has established a reliable lottery-prediction edge. V3's historical
ranking lift is interesting but not statistically convincing.

## V5 research checkpoint

The first V5+ attempt was registered as
[`V5_pair_affinity`](experiments/V5_pair_affinity.md), with its structured row in
[`docs/experiments/registry.yaml`](experiments/registry.yaml). The registration
freezes one strongly shrunk, previous-draw-anchored pair-affinity formula, a
single primary Top-12 metric, bounded secondary metrics, a deterministic
whole-draw date-permutation control, Holm family-wise correction, and the default
minimum 104-draw prospective gate.

The current status is **implemented / historical diagnostic complete / rejected
/ never activated**. The exact model implementation was committed as `f51a3b5`
before any candidate score was inspected. Its recorded dataset is the fixed
4,431-draw prefix through 2026-08-12 at source commit `39b99a9`; later live
appends cannot change that prefix or the registered negative control.

The result did not establish stable signal. Primary Top-12 lifts for development,
legacy validation, and consumed 2020-2025 were `+0.008056`, `-0.065542`, and
`+0.024976`; exact one-sided p-values were `0.334025`, `0.936385`, and
`0.272298`, and every 95% bootstrap interval included zero. Brier score and log
loss were worse than the fair constant baseline in every lane. The seed-649
negative control behaved as null. See the
[decision record](experiments/V5_pair_affinity_results.md) and generated
[historical report](../reports/v5_pair_affinity_v5.0.0_historical.md).

`v5_pair_affinity` is requestable only from the dedicated research config. It is
not in `config.yaml` or `live.models`; no V5 live snapshot exists. V1 production,
V3 shadow behavior, and every committed prediction snapshot remain unchanged.

## V6 research checkpoint

The second V5+ attempt, [`V6_fixed_boundary_js_regime`](experiments/V6_entropy_regime.md),
froze two adjacent 104-draw blocks, one global entropy gate, deterministic
date-derived jitter, the same whole-draw negative control, and an exact 208-draw
prospective decision before implementation or score inspection. The frozen
implementation commit is `591b6173`.

The one historical diagnostic is complete and **rejected / never activated**.
Development, legacy-validation, and consumed 2020–2025 Top-12 lifts were
`-0.001514`, `+0.117151`, and `+0.000822`. The sole historical gate lane had
exact/Holm `p=0.498761` and a 95% bootstrap interval of
`[-0.078083, +0.078116]`. V6 activated on 44 development targets but zero
legacy or consumed targets; the isolated legacy lift therefore came from the
registered outcome-independent fair jitter and cannot rescue the failed
all-lane/consumed gates. All negative controls behaved as null and the audit was
clear. See the [decision record](experiments/V6_entropy_regime_results.md).

`src/lotto649/research_protocol.py` now provides fail-closed Git/data evidence,
evaluation rebinding and recomputation, fixed prospective checkpoints, and a
single immutable formal-look record. V1 remains production and V3 remains
shadow. The next research attempt must be a new bounded pre-registration and
new model version; do not retune or reopen rejected `v5.0.0` or `v6.0.0`.

## V7 research checkpoint

The next bounded attempt is
[`V7_post_rng_main_bonus_role_bias`](experiments/V7_main_bonus_role_bias.md),
version `v7.0.0`. It tests whether, after the documented 2019-05-15 RNG
transition, a label's strictly prior six-main versus bonus-role counts contain a
stable role-assignment signal. The frozen seed-649 negative control keeps every
draw's date and seven-number set but reassigns only its historical bonus role.

The candidate, control, diagnostic runner, and deterministic offline tests are
implemented on `codex/v7-research-foundations`. No V7 historical prediction
score or global role-audit statistic has been generated or inspected. Before the
sole run, the implementation must be committed and pushed, CI must pass, and the
runner requires the supplied full commit SHA to equal a completely clean local
HEAD. It then permits only the consumed 621 targets in 2020–2025 and refuses to
overwrite either report artifact.

The runner creates the canonical `.claim` file exclusively after all preflights
and before the first score. It is permanent on success or failure and must never
be deleted to retry V7. JSON and Markdown use same-directory `.tmp` staging and
are both staged before sequential publication; a caught partial publication is
rolled back. A crash or other post-claim failure leaves the permanent claim and
any staging or partial-publication evidence for an **Archive** decision. On
success only the `.tmp` files are removed, and the report records the permanent
claim's path and SHA-256.

V7 remains absent from `config.yaml`; its research config has
`live.enabled: false` with empty primary and shadow lists. Even complete
historical passage
would require a separate reviewed shadow-activation PR. V1 remains production,
V3 remains shadow, and existing prediction/evaluation snapshots are unchanged.

## How the implemented system runs

The CLI entry points are:

```bash
lotto649 bootstrap
lotto649 backtest
lotto649 live
```

`bootstrap` refreshes and validates source data. `backtest` uses the committed
processed CSV and walks forward chronologically over the configured dates. `live`
loads existing committed history, refreshes sources, evaluates every due snapshot
that lacks an evaluation, and creates predictions for the next Wednesday or
Saturday after the latest known draw.

`config.yaml` deliberately separates two selections:

- `backtest.models`: the configured historical comparison suite, including V2,
  V3, and V4.
- `live.models`: the approved V1 suite plus V3.

`live.shadow_models: [v3_boosting]` adds `"role": "shadow"` to V3 snapshot
metadata; all other live snapshots receive `"role": "primary"`. The role is a
research label, not a separate execution path. V3 is still evaluated and can
trigger the common hit-threshold email. It does not feed the V1 ensemble.

All live models currently inherit `project.model_version: v1.0.0` for the
`model_version` field and filename. Therefore the model identity
`v3_boosting` plus `metadata.role == "shadow"` distinguishes the V3 shadow
snapshot; do not infer that it is a V1 algorithm from the shared version tag.
Change version semantics deliberately rather than renaming committed snapshots.

## Current V3 forward checkpoint

The newest committed V3 shadow snapshot is
`predictions/2026-08-19__v3_boosting__v1.0.0.json`:

- generated 2026-08-16 11:36:09 EDT (`America/Toronto`);
- target draw 2026-08-19;
- trained from 4,432 committed draws through 2026-08-15;
- Top-6 ranking: `17 08 10 27 33 20`;
- final combination: `08 10 17 20 27 33`;
- Top-12: `17 08 10 27 33 20 03 22 49 15 30 39`;
- metadata role: `shadow`.

That newest target is not yet evaluated. The preceding 2026-08-15 V3 snapshot
has now been evaluated against verified main numbers `01 09 17 34 36 43`
(bonus `24`): Top-6 `1`, Top-12 `2`, Top-18 `3`, final-combination hits `1`,
mean actual rank `19.166667`, Brier `0.105576857`, and log loss `0.361421605`.
The processed dataset now contains 4,432 draws through 2026-08-15. To find the
moving current checkpoint, inspect the newest V3 file under `predictions/` and
its same-named file under `evaluations/`.

Prediction files are immutable. `generate_next_predictions` skips an already
existing target/model/version path, and the storage layer rejects overwrites by
default. Never edit a snapshot after its result is knowable.

## GitHub Actions and email

The active workflows are:

- `test.yml`: unit tests on every push and pull request.
- `integration.yml`: source/model smoke checks on relevant pull-request paths or
  manual dispatch.
- `backtest.yml`: frozen configured backtest on relevant `main` changes or manual
  dispatch.
- `live.yml`: `15:15 UTC` every Thursday and Sunday, manual dispatch, and relevant
  `main` changes. It commits `data/processed`, `predictions`, `evaluations`, and
  `reports` with `contents: write` permission.
- `email-test.yml`: explicit Gmail SMTP smoke test.
- `research-v2-fast.yml` and `research-v2-v4.yml`: historical branch-specific
  research workflows retained for auditability.

The latest scheduled live cycle succeeded on 2026-08-16
([Actions run 31956059222](https://github.com/Jasper-Shi/lottopred/actions/runs/31956059222)).
It committed `90177c8`, advanced verified history to 2026-08-15, created seven
evaluations, and created seven next-draw snapshots for 2026-08-19.
The Gmail alert smoke test also succeeded on 2026-08-15
([Actions run 31887288254](https://github.com/Jasper-Shi/lottopred/actions/runs/31887288254)).
Secret values are not readable from the repository; the successful smoke run
shows that usable configuration existed at that time.

Email requires only these repository secrets:

```text
SMTP_USERNAME=<Gmail address>
SMTP_PASSWORD=<Google App Password>
```

Defaults are `smtp.gmail.com:587`, with sender and recipient both equal to
`SMTP_USERNAME`. `SMTP_HOST`, `SMTP_PORT`, `EMAIL_FROM`, and `EMAIL_TO` are
optional overrides. Missing credentials do not block prediction or evaluation;
`send_email` returns false. The dedicated email smoke workflow treats that as a
failure so configuration can be tested explicitly.

Current alert thresholds in `config.yaml` are final-combination hits `>= 4` or
Top-12 hits `>= 5`.

## Data-source and fallback behavior

The live CLI imports `refresh_with_sources` from `src/lotto649/data_sources.py`.
Its current reconciliation policy is:

1. Use the WCLC since-inception PDF for years before `bridge_start_year` (2024).
2. Use lotto.net annual HTML as the machine-readable bridge from 2024 onward.
3. Use the current WCLC results page as the authoritative current source and as
   an independent check wherever it overlaps the bridge.
4. Retain committed draws only when they agree with newly selected source data.
5. Require a strictly ordered, unique chronology of more than 4,000 draws, with
   no suspicious post-2000 gap greater than 14 days.

A lotto.net `requests` failure or timeout is recoverable: the cycle warns and
continues with committed data, the WCLC archive, and current WCLC results. This is
safe only if the resulting chronology still passes validation.

The 2026-08-16 scheduled run exercised that fallback: the lotto.net 2024 bridge
timed out after 60 seconds, while committed/WCLC reconciliation still produced a
valid 4,432-draw chronology and the run succeeded. This remains an operational
warning, not a silent source substitution. GitHub also emitted its platform-level
Node.js 20 deprecation warning for `actions/checkout@v4` and
`actions/setup-python@v5`; it did not fail the job.

The following conditions remain fatal by design:

- WCLC archive/current request or parse failure;
- bridge parse/format failure that is not a request exception;
- bridge versus current-WCLC disagreement;
- committed data versus refreshed-source disagreement;
- undersized, duplicated, unordered, or discontinuous chronology.

Do not broaden the fallback to swallow those integrity failures.

## How Codex should continue

1. Read root `AGENTS.md`, `MODEL_PROTOCOL.md`, `V2_V4_RESULTS.md`, and
   `RESEARCH_ROADMAP.md` before proposing any V5+ candidate.
2. Pull current `main` and inspect the newest committed prediction/evaluation
   files before reporting live status.
3. Keep V1 unchanged as the baseline and V3 labeled shadow while new hypotheses
   are developed.
4. Keep rejected `v5.0.0` immutable and retain its reports and registry row as a
   negative result.
5. Pre-register one genuinely separate hypothesis before implementing or
   inspecting its scores; all currently observed outcomes are consumed for any
   model changed in response to them.
6. Start a future candidate as shadow only through a separate reviewed PR and
   count evidence only from that exact version's first eligible pre-draw snapshot.
7. Let normal live jobs continue during research. Never rewrite forward artifacts
   or mix research-only models into `live.models` without a reviewed promotion PR.
8. Run `pytest -q` and `ruff check .`; run integration smoke checks for live/data
   changes; record both positive and negative research results.

Use `docs/RESEARCH_ROADMAP.md` as the decision process, not as evidence that any
listed feature family will work.
