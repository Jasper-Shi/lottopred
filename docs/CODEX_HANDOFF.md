# Codex Handoff

Last verified against `main` commit `39b99a9` on 2026-08-16.

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
| V5 pair affinity | Registered only | `v5.0.0` is pre-registered but not implemented, evaluated, or activated. It is absent from backtest and live config. |
| 2020–2025 blind period | Consumed | It cannot confirm a tuned V5+ model. |
| 2026+ snapshots | Prospective evidence | Evidence belongs to the exact frozen version that created each pre-draw snapshot. |

No version has established a reliable lottery-prediction edge. V3's historical
ranking lift is interesting but not statistically convincing.

## V5 research checkpoint

The first V5+ attempt is registered as
[`V5_pair_affinity`](experiments/V5_pair_affinity.md), with its structured row in
[`docs/experiments/registry.yaml`](experiments/registry.yaml). The registration
freezes one strongly shrunk, previous-draw-anchored pair-affinity formula, a
single primary Top-12 metric, bounded secondary metrics, a deterministic
whole-draw date-permutation control, Holm family-wise correction, and the default
minimum 104-draw prospective gate.

The current status is **registered / not implemented / not evaluated / not
activated**. No candidate score was inspected while defining it. Its recorded
dataset is the 4,431-draw file through 2026-08-12 at source commit `39b99a9`, so
all 2026 outcomes knowable before a future activation are consumed rather than
prospective for this version. `config.yaml`, the model factory, V1 production,
V3 shadow behavior, and all committed snapshots remain unchanged.

`src/lotto649/research_protocol.py` provides the supporting registry validation,
strict-prefix walk-forward folds, deterministic negative-control transform,
fingerprints, and conservative cohort eligibility checks. The next research
step is to implement the registered formula and its feature-specific invariance
tests without changing the registration or reading candidate scores during
implementation. Historical diagnostics must then be reported with their lane
labels and both negative and positive results before any separate shadow
activation review.

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

The first committed V3 shadow snapshot is
`predictions/2026-08-15__v3_boosting__v1.0.0.json`:

- generated 2026-08-15 10:13:18 EDT (`America/Toronto`);
- target draw 2026-08-15;
- trained from 4,431 committed draws through 2026-08-12;
- Top-6/final combination: `07 21 36 38 41 49` (ranking order is
  `07 36 41 49 21 38`);
- Top-12: `07 36 41 49 21 38 13 08 20 43 04 16`;
- metadata role: `shadow`.

At this handoff checkpoint, the processed dataset still ends on 2026-08-12 and no
evaluation for the 2026-08-15 target is committed. The scheduled live job will
evaluate it only after a verified result appears in the reconciled dataset. To
find the moving current checkpoint, inspect the newest V3 file under
`predictions/` and its same-named file under `evaluations/`.

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

The latest checked live run after the bridge fallback fix succeeded on 2026-08-15
([Actions run 31889275021](https://github.com/Jasper-Shi/lottopred/actions/runs/31889275021)).
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

The following conditions remain fatal by design:

- WCLC archive/current request or parse failure;
- bridge parse/format failure that is not a request exception;
- bridge versus current-WCLC disagreement;
- committed data versus refreshed-source disagreement;
- undersized, duplicated, unordered, or discontinuous chronology.

Do not broaden the fallback to swallow those integrity failures.

## How Codex should continue

1. Read root `AGENTS.md`, `MODEL_PROTOCOL.md`, `V2_V4_RESULTS.md`, and
   `RESEARCH_ROADMAP.md` before proposing V5.
2. Pull current `main` and inspect the newest committed prediction/evaluation
   files before reporting live status.
3. Keep V1 unchanged as the baseline and V3 labeled shadow while new hypotheses
   are developed.
4. Keep the registered V5 pair-affinity specification immutable while implementing
   it and its feature-specific invariance tests.
5. Run leakage checks and the registered negative control before candidate
   scoring, then report every historical lane as a labeled diagnostic; do not
   call any 1982–2025 result untouched evidence for V5.
6. Freeze code/config/version in Git, then use a separate reviewed PR to start V5
   as a shadow model. Count forward evidence only from its own first eligible
   pre-draw snapshot.
7. Let normal live jobs continue during research. Never rewrite forward artifacts
   or mix research-only models into `live.models` without a reviewed promotion PR.
8. Run `pytest -q` and `ruff check .`; run integration smoke checks for live/data
   changes; record both positive and negative research results.

Use `docs/RESEARCH_ROADMAP.md` as the decision process, not as evidence that any
listed feature family will work.
