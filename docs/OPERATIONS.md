# Operations Guide

## Cloud execution

No local computer needs to stay running.

- **Codex Cloud**: development, code changes, debugging and research.
- **GitHub Actions**: recurring production-like execution.

## V3 prospective release protocol

The frozen V3 cohort identity is `v3_boosting v3.0.0`. Its registration starts
as `registered` / prospective `not_activated`; V1 remains production and the
legacy V3 `v1.0.0` live snapshots remain ordinary shadow audit artifacts, not
members of the new cohort.

Release requires four distinct, strictly ordered Git events:

```text
F = freeze commit containing the V3 registration and frozen implementation
A = activation-anchor commit recording F and the latest verified result boundary
R = reviewed release-seal commit that activates the registry, records cohort_start,
    and thereby opens the per-model v3.0.0 gate already frozen at F
S = first eligible v3.0.0 snapshot's one-time first-add commit

F < A < R < S
```

`A` is an evidence anchor, not a live release. It must leave V3 `v3.0.0` out of
live generation, preserve the exact full SHA of `F`, and bind the complete
verified `data/processed/draws.csv` outcome boundary then known. The activation
PR must preserve `A` as a reachable commit; do not squash it away.

At `F`, `config.yaml` already contains the dormant mapping
`live.model_versions.v3_boosting: v3.0.0` and its guard
`live.model_version_experiments.v3_boosting: V3_frozen_shadow_cohort`. The
frozen live code applies an experimental version only when the named registry
experiment is `prospective_shadow` and its cohort is `active`; `registered` /
`not_activated` continues to use project default `v1.0.0`.
The workflow at `F` must already install with the frozen runtime constraints:

```bash
python -m pip install --constraint requirements-live.lock -e .
```

`R` must be a later reviewed **registry-only** transition. It cites `A`, records
a cohort start strictly after the activation-known outcome boundary, and sets
the experiment/cohort states to `prospective_shadow` / `active`. That state opens the mapping without
renaming any old file. `R` must not modify `config.yaml`, model/live/scoring
code, `requirements-live.lock`, or `.github/workflows/live.yml`; all are part of
the frozen manifest. The registry itself is intentionally outside that manifest
because its administrative state must change at `R`.

The cohort auditor must nevertheless compare the V3 registry specification to
its canonical entry at `F`. Only status/result and the named prospective
activation fields may change; identity, parameters, controls, metrics, gates,
208/104+104 stopping rule, role, and deadline remain frozen. It must also derive
the real commit `R` that first introduced the complete active row and prove
`A < R < S`; checking only `A < S` is not sufficient.

The freeze/release reviews must verify that the constraint file covers every
production dependency and that all packages resolve. The pre-snapshot verifier
requires CPython `3.12` and exact installed versions for every pinned
distribution. An unconstrained live environment, changed frozen path, missing
ancestor, or snapshot added in the same commit as `R` is ineligible for the
cohort.

`S` must be strictly later than `R`, add exactly one new immutable prediction
file for a target not yet knowable, and precede that target's Toronto local
calendar date. All existing `v3_boosting v1.0.0` files are excluded regardless
of target date. Missing, late, regenerated, dependency-drifted, or integrity-
failed snapshots are excluded rather than repaired.

Every `v3.0.0` snapshot must carry the nested
`metadata.prospective_release` evidence written by the verified live path. The
auditor re-derives its release, activation-anchor, frozen-manifest, generation
commit, and dependency-lock identities from Git and replays V3, V1 ensemble,
and the target-date-seeded random control from the snapshot-bound history.
Snapshot metadata alone is never treated as proof.

An invalid or missing V3 experiment mapping, registry, release proof, runtime
lock, target boundary, or V3 prediction suppresses only that prospective shadow
snapshot and emits a stable `prospective_*` warning in both the Actions log and
live-cycle JSON. V1 production snapshots continue. Shared storage failures and
V1 model failures still fail the cycle. Do not generate a legacy V3 fallback;
the missing planned target remains explicit cohort evidence and is excluded by
the auditor.

After activation, the performance-blind progress command is:

```bash
lotto649 prospective-audit --experiment V3_frozen_shadow_cohort
```

The read-only `lotto649-prospective-cohort-monitor` workflow performs the same
integrity/count check after each completed live workflow. It emits a notice at
207 raw candidate evaluations and a failing, high-visibility warning at an
exact verified `ready` checkpoint; it never creates the claim or computes a
formal result. Once 208 raw evaluations exist, the next live cycle runs the
same performance-blind audit before evaluating due files. A ready, overdue,
formally sealed, or integrity-failed cohort holds only V3 evaluation/generation
so that a 209th result cannot be admitted; V1 continues normally.
Catch-up evaluation is quota-limited: it cannot cross 208 raw candidate files
in one cycle, and after that threshold a still-collecting audit admits at most
one V3 evaluation before the next committed-tree audit. Earlier-pending and all
terminal/invalid states admit zero V3 evaluations. V1 has no such quota.

It reports counts and integrity state only, never interim aggregate performance.
When and only when it reports the exact ready 208-row checkpoint, create the
claim:

```bash
lotto649 prospective-claim --experiment V3_frozen_shadow_cohort
git add reports/prospective/V3_frozen_shadow_cohort__v3.0.0__formal.claim
git commit -m "Claim V3 prospective formal look"
```

The claim must be a real first-add commit strictly after all 208 evaluation
commits. Only then may an operator run:

```bash
lotto649 prospective-formal-look --experiment V3_frozen_shadow_cohort
```

That command acquires the permanent registered `__formal.attempt` before it
reads or computes any checkpoint-level aggregate metric, then stages and
publishes the registered JSON and Markdown pair without overwrite. Commit the
attempt and both reports together. Claim and attempt are permanent after
success or failure. Failure before the publication commit point (both final
hard links plus parent-directory fsync) means Archive and forbids rerunning
`v3.0.0`. Cleanup after that durable point is best effort and may warn without
invalidating the result. An unrecorded 209th eligible evaluation is likewise
overdue.

After committing the attempt and report pair, record the reviewed terminal
decision in one later non-merge, registry-only commit `T`. Its result paths and
implementation commit must bind the formal artifacts and their commit; the
decision must match Reject/Archive/eligible-for-reviewed-Promote semantics.
Run the closed audit before merging `T`. Later data appends do not extend the
closed target range, and any post-`T` artifact for the same model/version is an
error. If a future version changes a frozen implementation path, check out `T`
to re-audit this closed cohort; do not replay old evidence using the new code.

The current research branch is stacked and unmerged. Its only permitted stage
is `F`; it may commit the dormant gated mapping but must not perform `A`, `R`,
or `S`, open the gate, or generate a prediction. See
[`V3_frozen_shadow_cohort.md`](experiments/V3_frozen_shadow_cohort.md) for the
fixed 208-draw/104+104 stopping and promotion rules.

## GitHub Actions workflows

- `test.yml` — runs unit tests on pushes and pull requests.
- `integration.yml` — verifies real result sources, a short consumed-data
  regression that explicitly excludes V3, and live snapshot generation.
- `backtest.yml` — runs an explicitly labeled consumed historical regression
  (`random`, `ema_gap`, and rejected V2 only) when model code reaches `main`;
  it is neither blind nor confirmatory. Manual research runs must be labeled by
  their registered evidence status.
- `live.yml` — runs after model deployment and every Thursday/Sunday, evaluates due predictions, generates the next-draw predictions and commits the audit trail.

The live workflow has `contents: write` permission because snapshots/results are committed back to the repository.

## Gmail email setup

The application uses Gmail SMTP with STARTTLS. Do **not** put credentials in source code or commit them to Git.

Only two GitHub repository secrets are required:

```text
SMTP_USERNAME    your Gmail address
SMTP_PASSWORD    your Google App Password
```

With only those two values configured, the system automatically uses:

```text
SMTP_HOST = smtp.gmail.com
SMTP_PORT = 587
EMAIL_FROM = SMTP_USERNAME
EMAIL_TO = SMTP_USERNAME
```

So alerts are sent from your Gmail account back to the same inbox. `SMTP_HOST`, `SMTP_PORT`, `EMAIL_FROM`, and `EMAIL_TO` remain optional GitHub Secrets if you ever want to override those defaults or send alerts to another address.

For `SMTP_PASSWORD`, use a Google **App Password**, not the account's normal sign-in password. Google App Password availability normally requires 2-Step Verification on the Google account.

Missing email secrets do not stop backtesting, evaluation, or prediction; email is a side effect only.

## Notification defaults

V1 emails when either condition is met:

- final six-number prediction hits at least 4/6, or
- Top-12 candidate pool contains at least 5/6 actual winning numbers.

Thresholds are in `config.yaml`. Changing them does not change model probabilities but should still be documented.

## Data failure behavior

### Source disagreement

Pipeline stops immediately. Never choose one source silently.

### WCLC/bridge format changes

Parser raises rather than proceeding with a suspiciously small or discontinuous dataset.

### Email failure

The evaluation/prediction state remains valid. SMTP is not part of model state.

### Git push conflict

Re-run from current `main`. Existing prediction snapshots are immutable and are not regenerated/overwritten.

## Scheduled time

The live workflow runs at `15:15 UTC` Thursday and Sunday, well after the preceding Wednesday/Saturday draw. This reduces the chance of querying before official results have propagated.
