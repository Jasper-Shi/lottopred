# Codex Project Instructions

## Mission

Maintain an auditable research system that tests whether Canadian LOTTO 6/49
history contains stable out-of-sample signal. Treat a fair, unpredictable lottery
as the default explanation. A negative result is a successful research outcome.

Preserve two properties above headline hit counts:

1. **Chronology:** a prediction for draw `t` can use only information available
   strictly before `t`.
2. **Auditability:** live predictions are immutable, pre-draw snapshots committed
   to Git before their results are known.

## Read the right context first

- For current production/shadow status, live snapshots, Actions, email, or data
  source behavior, read `docs/CODEX_HANDOFF.md`.
- Before changing features, models, backtests, selection metrics, or ensemble
  weights, read `docs/MODEL_PROTOCOL.md`, `docs/V2_V4_RESULTS.md`, and
  `docs/RESEARCH_ROADMAP.md`.
- For historical opportunity, high-water, or 6/6 evidence claims, read
  `docs/HISTORICAL_OOS_EVIDENCE_PROTOCOL.md`.
- For system boundaries and operational recovery, read `docs/ARCHITECTURE.md`
  and `docs/OPERATIONS.md`.

When code and prose disagree, verify behavior from code and tests, then update the
affected documentation in the same change.

## Architecture

- `src/lotto649/data.py` parses and validates WCLC and lotto.net payloads.
- `src/lotto649/data_sources.py` preserves the legacy reconciliation and bridge
  fallback policy for audit; it is not an operational CLI write path.
- `src/lotto649/verified_history.py` validates the sealed corrected-history
  epoch and its Git-bound, dual-source suffix.
- `src/lotto649/operational_history.py` owns the deployed history paths and
  external hashes. Operational callers must use its single load interface and
  must not fall back to `data/processed/draws.csv`.
- `src/lotto649/features.py` and `research_features.py` build leakage-safe
  number-level features.
- `src/lotto649/models/` contains probability models. Each model must return one
  probability for every integer `1..49`, with values in `(0, 1)` normalized to an
  expected total of six.
- `src/lotto649/backtest.py` performs strict chronological walk-forward scoring.
- `src/lotto649/live.py` refreshes results, evaluates due committed snapshots, and
  creates snapshots for the next Wednesday/Saturday draw.
- `predictions/` and `evaluations/` are the forward-test audit trail. Existing
  JSON snapshots are immutable.
- `reports/` contains reproducible research/backtest outputs.
- `config.yaml` selects the frozen backtest suite, V1 live suite, V3 shadow role,
  thresholds, and model parameters.
- `.github/workflows/` is the unattended execution layer; Codex is the
  development and research layer.

## Model history and status

- **V1 — paused production baseline suite.** Before the data-integrity hold,
  random, long-frequency, recent-frequency, EMA/gap, logistic, and their frozen
  ensemble produced live snapshots. V1 is a baseline, not proof that lottery
  draws are predictable; restarting it requires the reviewed corrected-history
  release described in `docs/CODEX_HANDOFF.md`.
- **V2 — rejected.** Its frozen statistical multi-factor model underperformed
  the fair theoretical Top-6, Top-12, and Top-18 expectations in the legacy
  registered-data run. The exact metrics are withdrawn as corrected-history
  evidence; see the data-integrity erratum in `docs/V2_V4_RESULTS.md`.
- **V3 — paused shadow / unpromoted.** It was the sole V2–V4 candidate with
  small positive ranking lift at all three Top-K levels in that legacy run, but
  the lift was not significant, probability calibration was worse than the fair
  constant baseline, and 2025 deteriorated sharply. It remains unpromoted;
  corrected-history behavior requires a reviewed new version and prospective
  evidence.
- **V4 — rejected.** Its legacy registered-data result finished below fair
  theoretical expectations at all three Top-K levels. The conservative rejection
  remains, but the exact result is not corrected-history evidence.

The authoritative numbers and decisions are in `docs/V2_V4_RESULTS.md`.

## Leakage and research guardrails

The historical partitions are:

| Period | Current interpretation |
|---|---|
| 1982–2014 | historical development |
| 2015–2019 | legacy validation/model-selection data |
| 2020–2025 | consumed legacy registered-data diagnostic; strict-blind status withdrawn |
| 2026+ | model-specific prospective forward evidence |

**Post-hoc tuning on 2020–2025 is prohibited.** Do not change features,
coefficients, windows, hyperparameters, weights, constraints, or candidate
selection because doing so improves the already-observed 2020–2025 results and
then describe the result as blind, validation, confirmation, or new evidence.
Use that interval only as labeled historical diagnostic data.

Apply the same rule to live evidence: once a 2026+ result influences a candidate,
that result is consumed for the changed candidate. Freeze a new version and begin
a new prospective cohort from its first committed pre-draw snapshot.

Positive research behavior is:

- pre-register the hypothesis, feature definitions, primary metric, comparison
  set, and stopping/promotion rule before reading confirmatory outcomes;
- fit transformations, calibration, and model parameters only on the history
  visible at each walk-forward step;
- keep the fair `6/49` theoretical baseline and shuffled/permuted negative
  controls in serious benchmarks;
- record every attempted feature family, including negative results, and correct
  for multiple comparisons;
- assign a new model version whenever statistical behavior changes.

## Live and backtest workflows

Historical research:

```text
history before t -> features/train -> frozen prediction for t -> reveal t -> score
```

Never shuffle draws or train on a target/future draw. `lotto649 backtest` reads
only through the verified operational-history seam. `lotto649 bootstrap` remains
blocked until the reviewed dual-source suffix writer and external-pin publication
protocol exist; it must never fall back to the legacy processed CSV.

Live forward cycle:

```text
refresh verified sources
  -> evaluate previously committed due snapshots
  -> optionally send threshold email
  -> write verified history/evaluations
  -> generate next-draw V1 + V3-shadow snapshots
  -> GitHub Actions commit the audit trail
```

Do not overwrite or regenerate an existing prediction to change its numbers,
timestamp, model role, or visible-history metadata. Fixes apply to a new version
and future target draws.

## Coding and testing conventions

- Support Python 3.11+; GitHub Actions currently runs Python 3.12.
- Keep model behavior deterministic where applicable; the project seed/random
  state is `649`.
- Preserve categorical number treatment: predicting 27 when 28 is drawn is not a
  near-hit.
- Add unit tests for parsing, chronology, probability contracts, scoring, and
  failure behavior. Keep unit tests offline and deterministic; network-source
  checks belong in the integration workflow.
- Reject suspiciously small, discontinuous, duplicated, or conflicting datasets
  rather than silently choosing a convenient source.
- Keep credentials in GitHub Secrets. Never commit SMTP usernames, passwords, or
  App Passwords.
- Update model protocol/results/roadmap documentation whenever a change alters
  research interpretation or evidence status.

Run before completing a normal code/model change:

```bash
pip install -e '.[dev]'
pytest -q
ruff check .
```

For data-source or live-path changes, also run the relevant integration smoke test
when network access is available. For documentation-only changes, run the unit
suite and verify that every referenced repository path exists.

## Completion criteria

A change is complete only when its intended files are isolated on a feature
branch, relevant checks pass, the diff contains no credentials or generated
noise, research status is stated honestly, and any new model behavior has a new
version plus a prospective evaluation plan.
