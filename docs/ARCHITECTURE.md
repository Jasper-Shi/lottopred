# Architecture

## Goal

Ask one narrow question: **does any model repeatedly assign higher probability/rank to future winning numbers than a fair-lottery baseline when it is forbidden from seeing the future?**

## Data layer

V1 merges three sources:

1. WCLC since-inception PDF — primary historical source.
2. lotto.net annual archive pages — bridge for years where the WCLC PDF lags.
3. WCLC current LOTTO 6/49 results page — authoritative live/current source.

Overlapping dates are compared exactly, including bonus. Any disagreement raises an error. The merged chronology must contain more than 4,000 draws and may not contain suspicious post-2000 gaps greater than 14 days.

## Data-integrity incident execution boundary

The registered-history reconciliation opened on 2026-08-20 places the
operational source-refresh, default historical-backtest, and live-cycle paths
behind three explicit kill switches:

| Boundary | Required configuration | Incident value |
|---|---|---|
| Network/source refresh and processed-data write | `data.refresh_enabled is True` | `false` |
| Unattended live refresh/evaluation/prediction cycle | `live.enabled is True` **and** `data.refresh_enabled is True` | `false` / `false` |
| Historical backtest and report generation | `backtest.enabled is True` | `false` |

These checks deny by default. A missing key, a non-boolean value, or a value
other than literal boolean `true` does not enable execution. `bootstrap`
checks before resolving or loading the processed dataset or contacting a
source; `backtest` checks before loading data, building a model, or writing a
report; public live entry points check before source access, filesystem reads,
evaluation writes, or prediction generation. Literal `true`
satisfies only this runtime gate; it is never sufficient to reopen a sealed
workflow.

The three affected GitHub Actions workflows have a read-only boundary directly
after checkout. That boundary reads the committed configuration with the
runner's standard Python runtime and hashes the complete `config.yaml` byte
stream with SHA-256; it does not interpret YAML. The incident seal recognizes
only disabled-config SHA-256
`ad3237bc57c85013e85dad16d1b6f04f43b50991d666a4b1528bf5b8614a76b6`,
and even that exact match emits `false` for every execution stage. Every other
digest also emits only `false`. Runtime setup, dependency installation,
bootstrap, backtest, live execution, artifact upload, and Git writes therefore
skip successfully for both the sealed config and any unreviewed byte change.

The ordinary paths below describe the system when a later reviewed release has
reopened them. Re-enablement requires a committed and independently reviewed
corrected-history epoch, exact identity/integrity verification at its consumer
boundary, and passing offline tests and source-policy review. The release must
change the exact config bytes **and**, in the same reviewed commit, replace the
affected workflow's incident seal with an explicit execution plan bound to the
new config SHA-256. The CLI/runtime literal-boolean checks remain a second,
independent approval gate; a config-only toggle or a workflow-only digest
change cannot enable execution. Live must never be reopened without data
refresh in that same reviewed release. Existing predictions, evaluations,
reports, and registered evidence remain immutable.

This emergency seal is deliberately scoped to the three execution commands on
main: `bootstrap`, `backtest`, and `live`. It grants no authority for any other
research execution. Any broader operation must be added to a reviewed incident
plan rather than inferred from this operational seal.

## Path A — Live forward prediction

```text
refresh sources
     |
     v
evaluate due committed snapshots ----> SMTP alert if threshold met
     |
     v
update historical state
     |
     v
run all frozen V1 models
     |
     v
create immutable next-draw snapshots
     |
     v
GitHub Actions commit
```

The Git commit timestamp creates an external audit trail proving the prediction existed before the result was known.

During the data-integrity incident this entire path is dormant; the kill-switch
boundary takes precedence over the normal unattended schedule.

## Path B — Historical walk-forward simulation

For target draw `t`:

```text
history[0:t] -> features -> model -> probability vector -> result[t] -> score
```

Then advance to `t+1`. Random train/test shuffling is forbidden.

## Feature engine

V1 number-level features include:

- long-run frequency
- 10/25/50/100/250-draw frequencies
- exponentially weighted recent frequency
- gap since last appearance
- appeared in previous draw
- appeared in last 1/2/3/5 draws
- number identity scaled to 0..1

Structural metrics such as sum, odd/even, high/low, range, adjacency and repeated numbers are implemented as analysis helpers but are not forced into the final combination in V1. They become predictive features only after out-of-sample evidence.

## Models

- `random`: fixed `6/49` probability for every number.
- `long_frequency`: Bayesian-shrunk long-run frequency.
- `recent_frequency`: recent-100 frequency shrunk toward fair probability.
- `ema_gap`: weak EMA signal plus deliberately weak gap term.
- `logistic`: regularized logistic regression trained only on historical prior draws.
- `ensemble`: frozen weighted combination of the non-random V1 models.

All models emit 49 inclusion probabilities normalized to expected count six.

## Combination selection

V1 ranks all 49 numbers and selects the highest independent log-score six-number combination within the Top-12 candidate pool. It intentionally does not force a chosen sum band, 3/3 odd-even split, or similar folklore.

## Snapshot format

`predictions/YYYY-MM-DD__MODEL__VERSION.json`

Contains:

- target draw date
- generation timestamp and timezone
- model name/version
- probabilities 1..49
- Top-6, Top-12, Top-18
- final six-number combination
- number of historical draws visible to the model
- latest visible draw date

Existing snapshots are never overwritten.

## Evaluation

Each result stores:

- final six hits
- Top-6 hits
- Top-12 hits
- Top-18 hits
- matched final numbers
- Brier score
- binary log loss
- mean rank of actual six numbers

A single historical 6/6 or 5/6 is not sufficient evidence of predictive skill. Aggregate out-of-sample metrics and statistical significance are required.

## Scheduling

Codex Cloud is for development/agent work. GitHub Actions is the unattended scheduler. The live workflow runs Thursday and Sunday after the prior Wednesday/Saturday draw.
