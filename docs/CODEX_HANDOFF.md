# Codex Handoff

Last verified on 2026-08-23 against `main` commit
`9f16e20c726c7b65eed1d387c4c725d51248f570`.

## Current state

This repository is the execution and audit system. Codex develops and reviews the
code; outside an incident hold, GitHub Actions is the unattended runner that
commits live artifacts. Chat history is not required to continue because the
research decisions are recorded here and in `V2_V4_RESULTS.md`.

> **Data-integrity incident hold (2026-08-20):** the operational roles in the
> table below describe the pre-incident system, but execution is currently
> suspended. `data.refresh_enabled`, `backtest.enabled`, and `live.enabled` are
> all `false`; the live, integration, and backtest workflows are sealed to
> safe no-op behavior by disabled-config SHA-256
> `ad3237bc57c85013e85dad16d1b6f04f43b50991d666a4b1528bf5b8614a76b6`.
> No refresh, backtest, evaluation, or prediction is authorized. The registered
> 4,434-row history through 2026-08-22 is not strict real-calendar evidence; a
> corrected epoch and its reconciliation are not yet sealed into `main`.
> Re-enable only through the reviewed two-gate release described in
> [`OPERATIONS.md`](OPERATIONS.md#data-integrity-incident-kill-switch).

| Component | Status | Meaning |
|---|---|---|
| V1 live suite | Paused baseline | Before the hold, six models created forward snapshots: `random`, `long_frequency`, `recent_frequency`, `ema_gap`, `logistic`, and `ensemble`. |
| V2 statistical | Rejected | Retained for reproducibility and historical research; absent from the live model list. |
| V3 boosting | Paused shadow | Before the hold, it created immutable snapshots and evaluations beside V1; it did not change V1 predictions or ensemble weights. |
| V4 ensemble | Rejected | Retained for reproducibility and historical research; absent from the live model list. |
| 2020–2025 blind period | Consumed | It cannot confirm a model selected or tuned after those outcomes were known. |
| 2026+ snapshots | Immutable source-relative artifacts | They remain auditable, but the incident means they are not strict real-calendar evidence until a corrected epoch is reviewed. |

No version has established a reliable lottery-prediction edge. V3's historical
ranking lift is interesting but not statistically convincing.

## How the implemented system runs

The CLI entry points are:

```bash
lotto649 bootstrap
lotto649 backtest
lotto649 live
```

When a reviewed configuration explicitly enables them, `bootstrap` refreshes and
validates source data, `backtest` walks forward chronologically over the committed
processed CSV, and `live` refreshes history, evaluates due snapshots, and creates
predictions for the next Wednesday or Saturday. During the incident all three
commands fail closed before those operations.

`config.yaml` deliberately separates two selections:

- `backtest.models`: the configured historical comparison suite, including V2,
  V3, and V4.
- `live.models`: the approved V1 suite plus V3.

`live.shadow_models: [v3_boosting]` adds `"role": "shadow"` to V3 snapshot
metadata; all other live snapshots receive `"role": "primary"`. The role is a
research label, not a separate execution path. In the pre-hold path V3 was
evaluated and could trigger the common hit-threshold email. It does not feed the
V1 ensemble.

All live models currently inherit `project.model_version: v1.0.0` for the
`model_version` field and filename. Therefore the model identity
`v3_boosting` plus `metadata.role == "shadow"` distinguishes the V3 shadow
snapshot; do not infer that it is a V1 algorithm from the shared version tag.
Change version semantics deliberately rather than renaming committed snapshots.

## Current committed forward checkpoint

At `main` commit `9f16e20c726c7b65eed1d387c4c725d51248f570`:

- `data/processed/draws.csv` contains 4,434 registered rows through 2026-08-22;
- evaluations for all seven pre-hold live models are committed for both
  2026-08-19 and 2026-08-22, including
  `evaluations/2026-08-19__v3_boosting__v1.0.0.json` and
  `evaluations/2026-08-22__v3_boosting__v1.0.0.json`;
- seven immutable predictions for target 2026-08-26 are committed, including
  `predictions/2026-08-26__v3_boosting__v1.0.0.json`.

The newest V3 snapshot was generated on 2026-08-23 at 11:36 EDT from 4,434
registered draws through 2026-08-22 and is labeled `shadow`. Its target was not
yet knowable at this checkpoint, so no 2026-08-26 evaluation is committed. The
incident hold prevents any later cycle from evaluating or generating until a
reviewed release reopens both runtime and workflow gates.

Prediction files are immutable. `generate_next_predictions` skips an already
existing target/model/version path, and the storage layer rejects overwrites by
default. Never edit a snapshot after its result is knowable.

## GitHub Actions and email

The configured workflows are:

- `test.yml`: unit tests on every push and pull request.
- `integration.yml`: source/model smoke checks, currently sealed to checkout and
  the incident guard only.
- `backtest.yml`: configured historical backtest, currently sealed to checkout
  and the incident guard only.
- `live.yml`: scheduled/manual live cycle, currently sealed to checkout and the
  incident guard only. Its write permission does not bypass guarded steps.
- `email-test.yml`: explicit Gmail SMTP smoke test.
- `research-v2-fast.yml` and `research-v2-v4.yml`: historical branch-specific
  research workflows retained for auditability.

The last committed pre-hold live-cycle boundary is `main` commit
`9f16e20c726c7b65eed1d387c4c725d51248f570`: it appended the 2026-08-22 draw and
evaluations and froze the 2026-08-26 predictions. Its parent `0ef1883` appended
the 2026-08-19 evaluations and froze the 2026-08-22 predictions. Those artifacts
remain immutable during the hold.

The historical Gmail alert smoke test succeeded on 2026-08-15
([Actions run 31887288254](https://github.com/Jasper-Shi/lottopred/actions/runs/31887288254)).
Secret values are not readable from the repository; that run establishes only
that usable configuration existed at that time, not its current state.

Email requires only these repository secrets:

```text
SMTP_USERNAME=<Gmail address>
SMTP_PASSWORD=<Google App Password>
```

Defaults are `smtp.gmail.com:587`, with sender and recipient both equal to
`SMTP_USERNAME`. `SMTP_HOST`, `SMTP_PORT`, `EMAIL_FROM`, and `EMAIL_TO` are
optional overrides. In the ordinary enabled path, missing credentials do not
block prediction or evaluation; `send_email` returns false. The dedicated email
smoke workflow treats that as a failure so configuration can be tested
explicitly.

Current alert thresholds in `config.yaml` are final-combination hits `>= 4` or
Top-12 hits `>= 5`.

## Data-source and fallback behavior

The live CLI imports `refresh_with_sources` from `src/lotto649/data_sources.py`.
When source refresh is explicitly reopened, its reconciliation policy is:

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

1. Read root `AGENTS.md`, `MODEL_PROTOCOL.md`, `V2_V4_RESULTS.md`,
   `RESEARCH_ROADMAP.md`, `ARCHITECTURE.md`, and `OPERATIONS.md` first.
2. Treat `9f16e20c726c7b65eed1d387c4c725d51248f570` and the artifact facts above as
   the last pre-hold `main` boundary.
3. Keep all three runtime switches false and preserve the SHA-bound workflow
   seal. Do not bypass a command guard through a lower-level public function.
4. Complete and independently review the corrected historical epoch,
   reconciliation evidence, immutable base identity, and any append-only suffix.
5. Never rewrite the existing processed history, prediction, evaluation, report,
   or registered evidence artifacts; corrections belong to a new sealed epoch.
6. Re-enable only through the reviewed two-gate release in `OPERATIONS.md`, with
   new exact config bytes and matching workflow plans in the same commit.
7. Resume model research or prospective collection only after that release, with
   a new version whenever statistical behavior changes.
8. Run `pytest -q` and `ruff check .`; run a network smoke only after source
   access is explicitly authorized, and record positive and negative results.

Use `docs/RESEARCH_ROADMAP.md` as the decision process, not as evidence that any
listed feature family will work.
