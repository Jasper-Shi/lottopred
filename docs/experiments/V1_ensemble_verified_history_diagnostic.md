# V1 ensemble: verified-history diagnostic

Registered on 2026-09-13 UTC, before this experiment's historical forecasts.
Experiment: `V1_ensemble_verified_history_diagnostic_20260913`, revision 1.
Algorithm: the unchanged repository `ensemble`, `v1.0.0`.

## Question and scope

The user explicitly requested a historical test of the same existing V1
ensemble that produced their separate, ad hoc 2026-09-12 selection. This
experiment measures that algorithm on the corrected, authenticated history.
It is a data-correction sensitivity diagnostic, not untouched confirmation,
prospective evidence, a new feature family, or a claim of future winning ability.

The fixed source baseline is protected-main commit
`40f6e4098d4ed59f9421196efb8573c66c48928a`. The registration JSON seals every
existing Python source file, `config.yaml`, and the frozen dependency manifest.
The model, source weights, features, windows, fitting algorithm and combination
optimizer remain unchanged. The four ensemble weights are 0.15 long frequency,
0.20 recent frequency, 0.20 EMA/gap and 0.45 logistic. We will not change any of
them after observing this experiment's results.

Machine-readable authority:
[`v1-ensemble-verified-history-diagnostic-20260913.json`](../../evidence/research_registrations/v1-ensemble-verified-history-diagnostic-20260913.json).

## Data and chronology

Read only the Git-registry-authenticated `PublishedHistory` from the reviewed
source revision through `lotto649.operational_history.load_published_history`.
It contains 4,444 draws through 2026-08-22. Reject a changed data authority,
count, cutoff or target-date fingerprint; never use the malformed legacy CSV.
The scored cohort is all 627 dates in 2020–2025, with the fixed 314/313 halves
(2020–2022 and 2023–2025). No 2026 target is scored here.

For each target, the model receives only earlier draws and the target date:

```text
strict prefix -> calculate all three forecasts -> exclusive forecast files
-> flush/fsync -> hash-chain prediction_frozen event -> flush/fsync
-> reveal target -> calculate scores -> exclusive evaluation -> durable event
```

Each frozen forecast includes all 49 probabilities and their complete ordering,
Top-6/12/18, Final-6, algorithm and experiment identity, source commit, feature
identity, verified data provenance, prefix cutoff/count, target date, actual
generation timestamp and runtime. The timestamp is the real generation time;
it is never backdated to the historical target date. The report therefore proves
the ordering of this historical replay, not that a prediction existed years ago.

The full dataset may be held by the orchestration layer, but the forecast
function's interface excludes the target's numbers, bonus and all future rows.
The reveal function is called only after successful durable prediction writes.
Tests use synthetic prefixes and closed-form scoring oracles to enforce this
boundary before any real historical forecast in this experiment.

## Fixed comparisons and inference

There are exactly three forecast producers: unchanged V1 `ensemble`, unchanged
repository `random`, and one label-permuted ensemble-probability negative control.
The last control keeps the candidate's 49 probability values but maps them to a
target-date-seeded permutation of number labels, fixed by the registration.
It does not refit the candidate or select a favorable permutation. The fair
constant 6/49 probability is also a mathematical calibration and hit benchmark;
it does not add another searched ticket.

The primary metric is ensemble mean Top-12 hits minus 72/49. Report all
producers' mean Top-6/12/18 and Final-6 hits, Final-6 distribution from 0 to 6,
every date tied for best performance, numberwise Brier score, binary log loss,
and ten fixed equal-width probability calibration bins. Report both fixed
halves, including deterioration or failures.

Fair expected Top-K hits are 6K/49. For a completed 627-target run, compute
inclusive upper-tail probabilities by convolving the fixed Hypergeometric
(49, K, 6) law, and Holm-adjust the three Top-K comparisons for each producer.
Only the registered ensemble Top-12 comparison is primary; control and other
comparisons remain diagnostic. Confidence intervals use a fixed circular
moving-block bootstrap (block length 12, 2,000 replicates, seed 649), including
paired ensemble-minus-random and ensemble-minus-permuted differences.
No p-value or interval from this consumed period authorizes promotion.

Deduplicate the three Final-6 sets for each target and report both cumulative
opportunities and the fair probability of at least one exact match across those
opportunities. A random/control hit must be identified as such.

## Single run and stopping

Registration, implementation and synthetic tests must be committed, reviewed on
both Standards and Spec axes, pass CI, and be normally merged into protected
main before the single manual run from a fresh complete clone. The command is:

```bash
python3.12 tools/run_v1_verified_history_diagnostic.py --run-once
```

The only output directory is
`reports/v1_ensemble_verified_history_diagnostic_20260913/`. Its prior existence
refuses a new run. Before creating outputs or loading history, the runner also
requires an exact GitHub 404 for the independent V1 consumption marker
`refs/heads/v1-ensemble-history-consumed-20260913`, creates it exactly once at
the reviewed execution commit, and verifies that exact ref. A pre-existing
marker, uncertain create result or mismatched response refuses execution.
It must never update/delete that marker or try another ref. This is an
independent V1 marker and does not use either V12 lease namespace.
Files are exclusive, durable and never overwritten. An
uncertain or failed started run is retained and is not restarted under another
directory or identity. Verification reads existing outputs and never predicts.
The resulting artifacts are committed in a separate ordinary evidence PR.

At the first Final-6 6/6 from any producer, stop before the next forecast, freeze
the candidate and all evidence, and require an independent chronology/leakage
audit. A partial run reports its actual target count and cannot claim completed
627-target inference. The root task then commits the detected candidate and
uses the repository's reviewed default SMTP route for a single Chinese notice.
The notice must identify historical diagnostic evidence and pending audit; it
must not imply future prediction or promotion. SMTP credentials are not needed
to start this standalone diagnostic and are never embedded in evidence.

Absent an exact match, complete every target and report the negative or mixed
result honestly. Do not search variants, change seeds, tune the candidate, or
rerun a revealed target. A future experiment must be separately registered.

## Relationship to paused operations

This is the user's separately requested V1 diagnostic. It does not run or alter
V12, grant its authorization, consume its lease, change its statistical
fingerprint, enable the generic backtest/live kill switches, dispatch live
workflows, repair history, or create a late production snapshot. The V1 output
for 2026-09-12 remains a separate ad hoc calculation and is not scored here.

V12 I2 is implemented and merged by PR #40. Its historical authorization PR #41
is still unmerged. Advancing main with this separate V1 experiment means the
old authorization source/base in PR #41 cannot be treated as a current M_A;
future V12 execution must first bind a new auth-only source to the then-current
protected main, with the unchanged historical closure and all original gates.
Do not rewrite or force-update the old source to conceal that chronology.

The V12.0.1 live lane's fixed seed/canary windows have expired and cannot be
rescheduled. That does not reject its unexecuted historical candidate.
