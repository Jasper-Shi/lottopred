# Architecture

## Goal

Ask one narrow question: **does any model repeatedly assign higher probability/rank to future winning numbers than a fair-lottery baseline when it is forbidden from seeing the future?**

## Data layer

V1 merges three sources:

1. WCLC since-inception PDF — primary historical source.
2. lotto.net annual archive pages — bridge for years where the WCLC PDF lags.
3. WCLC current LOTTO 6/49 results page — authoritative live/current source.

Overlapping dates are compared exactly, including bonus. Any disagreement raises an error. The merged chronology must contain more than 4,000 draws and may not contain suspicious post-2000 gaps greater than 14 days.

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
