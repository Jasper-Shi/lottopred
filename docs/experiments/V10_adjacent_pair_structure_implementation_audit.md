# V10 Adjacent-Pair Structure — Implementation Audit

Status: **IMPLEMENTED FOR REVIEW — HISTORICAL DIAGNOSTIC NOT RUN**

This note audits the implementation seam for the frozen
`V10_adjacent_pair_structure` pre-registration. It contains no V10 historical
performance result. No 2020–2025 V10 forecast or score was generated while
developing or testing this implementation. All runner tests use visibly
synthetic dates, prefixes, forecasts, and outcomes.

## Isolation and deterministic model

- The model lives in
  `src/lotto649/models/v10_adjacent_pair_structure.py` and is not added to the
  normal model factory, live configuration, or GitHub Actions.
- Candidate and targeted control use the same `forecast_v10` engine; the only
  control difference is the frozen global label bijection.
- The exact fair category law, binary64 moment conversion, fair bypass, fixed
  256-iteration bisection, DP table digest, reflection identity, probability
  contract, ranking tie break, and control-map digest are checked by literal
  offline tests.
- Forecast canonical payloads contain no timestamp, target result, or bonus.
  Repeated calls on an identical strict prefix must be byte-for-byte equal.

## One-shot state machine

`src/lotto649/v10_diagnostics.py` implements an injected state machine with the
following durable order:

1. all artifact, environment, Git, source, reference, configuration, and
   chronology preflight checks finish before claim acquisition;
2. the claim, including the exact bootstrap/reference/scope analysis plan, and
   hash-chain ledger are created exclusively and fsynced;
3. the ledger records `claimed`, `preflight_passed`, and `scoring_started`;
4. for each target, the complete three-model forecast payload is built twice
   and required to serialize identically;
5. `prediction_frozen` binds its SHA-256 and one RFC3339 UTC timestamp, then is
   flushed and file-fsynced;
6. only after that receipt returns may the isolated `reveal_actual` callback
   convert the target row into six numbers;
7. `target_revealed_scored`, including progressive-record evidence, is flushed
   and file-fsynced before any next target; when that score deterministically
   requires an in-run record or Top-12 notification, an exact
   `progress_notification_outbox` request, idempotency key, and visible pending
   warning are also flushed and file-fsynced before best-effort dispatch and
   before the next target;
8. a normal complete run records `scoring_completed`,
   `publication_started`, publishes the JSON/Markdown pair via fsynced staging
   files and exclusive hard links, fully revalidates the claim/ledger/rebuilt
   JSON/exact Markdown before any all-gates-pass notification, and finally
   fsyncs one terminal `published` event containing an exact durable outbox
   request, idempotency key, `pending_external_receipt` status, and visible
   pending warning; only after that terminal exists may dispatch be attempted;
   and
9. any post-claim exception attempts a durable terminal `failed` event while
   retaining the claim and ledger as consumed Archive evidence.

The hash-chain verifier rejects noncanonical JSON, missing newline terminators,
noncontiguous sequence numbers, wrong predecessor hashes, and changed event
content. Its semantic pass also recomputes each canonical forecast SHA, validates
the RFC3339Z receipt timestamp and complete three-model forecast contract,
recomputes every public score and progressive record from the frozen payload
plus revealed main set, and rejects invalid state transitions. For a normal
publication it then uses the same pure report builder as the runner to rebuild
`per_target`, all scope summaries, paired bootstrap, joint metrics,
multiplicity, the exact ten gates, and the decision from ledger score events;
coordinated edits to a report and a legally rehashed `published` event therefore
fail semantic verification. The fixed claim file and its complete payload are
also bound to the report. The validator rebuilds the complete fixed top-level
template, including unchanged live roles and the non-activated prospective
cohort, and requires the Markdown bytes to equal a fresh rendering of that
rebuilt JSON. A sole final
`failed` event is valid after any otherwise valid post-claim prefix, including a
frozen-but-not-revealed target, but even an early failure must retain a
canonical fixed claim whose digest and frozen identity match its `claimed`
event (and whose preflight fields match whenever preflight was recorded). JSON
serialization rejects NaN, Infinity, and
non-JSON evidence.

## Opaque outcome adapter and exact preflight

`tools/run_v10_historical.py` is a manual-only entry point. It is not called by
the package CLI or any workflow and requires the explicit
`--execute-consumed-historical-diagnostic` acknowledgement.

Before claim acquisition it requires:

- CPython 3.12, the frozen `requirements-live.lock` SHA-256, and the exact
  installed version of every locked distribution;
- a clean exact implementation `HEAD`, descended from the registration commit,
  pushed to its upstream branch, with the required `test` and
  `source-and-model-smoke` jobs successful and every latest non-neutral CI check
  passing; the exact GitHub branch head is rechecked before claim and before
  each workflow-based notification dispatch, with every external command
  bounded by an explicit timeout;
- no post-registration changes to `config.yaml`, workflows, live audit trails,
  existing reports, or the frozen V10 registration/config/basis files;
- the canonical committed research config with live and notifications disabled;
- the exact registered registry identity, multiplicity family, random control,
  and targeted-control declaration;
- the registered Git data blob, raw digest, 4,432-row boundary through
  2026-08-15, and an append-only working dataset;
- exactly 621 opaque target rows and the frozen 307/314 halves;
- exact V5 multiplicity and V8 comparison report/claim hashes; and
- a registration-to-implementation diff containing every required V10 code/test
  file and only the explicit V10 implementation/status documentation allowlist.

The production fold store initially parses only prior training rows. Historical
target rows remain opaque CSV bytes. For target `t`, the store supplies the
complete already-revealed prefix to the models, but it does not parse the
target's six numbers until the core runner calls `reveal_actual` after the
fsynced `prediction_frozen` receipt. Revealed targets then become part of the
next strict prefix. Known 2026 rows are never targets. The production 6/6 audit
independently replays the same strict prefix against legal, byte-distinct target
and future suffix rows whose dates are unchanged. It also checks bonus-only and
prior-main counterfactuals. The prior-main check tries a fixed deterministic
set of legal alternatives and requires the selected alternative to change both
the candidate and targeted-control forecast payloads, recording every attempted
collision as evidence. The audit also checks registered source identity, exact
implementation/config/runtime/CI evidence, and byte-identical forecast replay.

## Metrics and frozen decision

The diagnostic module records all 49 probabilities, full ranking, Top-6/12/18,
sorted final six, actual ranks, categorical hits, Brier score, binary log loss,
ten calibration bins (including zero-count bins), year diagnostics, exact
`0..6` final-hit histograms, and the progressive record ledger.

It implements the exact draw-level Hypergeometric Top-12 convolution using
integer polynomial coefficients across all draws followed by one final division
by `C(49,6)^D`; fresh seed-649 10,000-row linear bootstrap for each scope;
aligned paired bootstrap,
two-variant Holm adjustment with the frozen V5 result, candidate/control joint
gains with per-target differences before `math.fsum`, proper-score deltas,
control-null warnings, the frozen V1 ensemble comparison, and all ten
conjunctive historical gates. A normal pass means only
`eligible_for_separate_reviewed_shadow_decision`; V10 remains not activated and
V1/V3 roles remain unchanged.

## Historical 6/6 branch

After a durable score, final-six 6/6 immediately records
`historical_6of6_candidate_detected` and stops before another target. The runner
performs the injected leakage audit without retraining, publishes the complete
candidate bundle exclusively, and takes exactly one terminal branch:

- `historical_6of6_candidate_published` for an audit-clear candidate, with the
  required Chinese success notification and `stop_global_search=true`; or
- `historical_6of6_candidate_archived_leakage_failed` when any audit check
  fails, with the required Chinese invalid-evidence warning and continued
  eligibility for a later newly registered experiment.

Neither early branch fabricates a 621-target aggregate report or resumes the
attempt. Notification uncertainty is pre-recorded as a durable operational
warning and cannot delete or weaken durable evidence. Clearance is derived by the runner from ten
required, uniquely named, boolean-true checks with nonempty canonical evidence.
Missing, duplicate, extra-failed, malformed, NaN, or nonserializable audit data
is normalized to the dedicated Archive branch rather than a generic crash.
Both 6/6 terminal branches carry the warnings that existed before their
mandatory notification and the exact outbox request/idempotency key plus a new
`notification_pending_external_receipt:*` warning.
For the normal path, the immutable scientific JSON states
`notification_status_at_report_publication=pending_post_publication` and names
the post-terminal external workflow receipt as the operational result authority.
The report is published and the unique final ledger outbox is fsynced before any
significant-result email. Dispatch is then best effort and can never rewrite the
ledger or turn a scientific terminal into `failed`.
Warnings accumulated before publication are rebuilt from semantically required
per-score `progress_notification_outbox` events, then bound in the durable
`publication_started` event and replayed into the immutable JSON. A coordinated
rehash cannot delete one of those warnings because the verifier independently
recomputes each notification trigger from the frozen forecast and revealed
score. The terminal outbox
preserves that exact prefix and adds one deterministic pending-receipt warning;
the terminal validator rejects hidden, dropped, or forged request/warning data.

## Synthetic test evidence

The dedicated runner tests cover:

- canonical chained ledger creation and verification;
- semantic rejection of hash-valid rechains with changed forecast payloads,
  timestamps, scores, target/digest pairing, missing/reordered/duplicate events,
  forged report rows/summaries/gates/decision/alerts, activation status, and
  Markdown, plus accepted terminal failure after valid intermediate states;
- exact scoring, proper-score baselines, calibration, explicit zero bins,
  exact Top-12 tail probability, and deterministic bootstrap;
- a complete two-target synthetic vertical slice proving each reveal callback
  observes a durable `prediction_frozen` event and each next target follows a
  durable scored event;
- exclusive staged report/bundle publication, staging cleanup, and
  fault-injected races that retain staging evidence whenever any final path
  survives;
- audit-clear and leakage-failed synthetic 6/6 branches, early stop, required
  terminal events, bundle preservation, and absence of a normal report;
- production-adapter receipt-before-reveal, target/future main-number and bonus
  invariance, same-date alternate sealed-row replay, exact 621/307/314 counts,
  runtime/CI/changed-path fail-closed helpers, bounded remote-ref and dispatch
  timeouts, and explicit CLI acknowledgement;
- refusal before preflight when any one-shot artifact exists; and
- durable post-claim failure plus refusal to rerun the consumed attempt; and
- fault-injected proof that a final artifact-validation failure sends no success
  alert, terminal-append failure calls no notifier for normal or either 6/6
  branch, progress-outbox append failure calls no notifier, and a post-terminal
  dispatch failure leaves terminal bytes unchanged; and
- coordinated hash-valid attacks that try to delete a progress-warning prefix
  from normal, audit-clear 6/6, or archived 6/6 terminals.

The focused V10 verification currently passes 99 offline tests. This is a
positive implementation result only. The deliberately negative scientific
result remains: no V10 2020–2025 historical diagnostic has been executed, no
V10 hit-rate or promotion claim exists, and V10 has no prospective activation.

The required final verification before freezing the implementation is
`pytest -q`, `ruff check .`, and Git diff/whitespace review from a clean feature
branch. Only after that exact commit is pushed and its CI is green may the
manual one-shot command be considered. This document records implementation
evidence only; it is not authorization or evidence that the historical run has
already occurred.
