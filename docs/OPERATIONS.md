# Operations Guide

## Cloud execution

No local computer needs to stay running.

- **Codex Cloud**: development, code changes, debugging and research.
- **GitHub Actions**: recurring production-like execution.

## Data-integrity incident kill switch

The 2026-08-20 registered-history reconciliation suspends source refresh, live
execution, and historical backtesting. The registered 4,432-row history is not
strict real-calendar evidence; a separate reviewed change must seal the 4,442-row
corrected epoch and its reconciliation before any execution can resume. The
committed incident state is:

```yaml
data:
  refresh_enabled: false
backtest:
  enabled: false
live:
  enabled: false
```

All three switches are fail closed. Missing keys, YAML nulls, numbers, and
strings such as `"true"` remain disabled. Literal boolean `true` satisfies only
an individual runtime guard; it is not sufficient to re-enable a workflow. Do
not work around a disabled command by calling a lower-level function. The
`bootstrap`, `backtest`, and public live boundaries repeat the checks before
their data loads, source access, model construction, report writes,
evaluations, or prediction snapshots. A live cycle additionally requires data
refresh to be enabled, so changing only `live.enabled` cannot resume
production.

`live.yml`, `integration.yml`, and `backtest.yml` checkout the repository and
then use only the runner's standard Python library to SHA-256 the complete
`config.yaml` bytes before Python setup or dependency installation. The
incident workflows recognize only this disabled-config digest:

```text
ad3237bc57c85013e85dad16d1b6f04f43b50991d666a4b1528bf5b8614a76b6
```

An exact match still emits `false` for every stage. Any byte change—including
a comment, whitespace, YAML-equivalent key spelling, duplicate key, or a true
toggle—also emits only `false`. The guard never relies on a partial YAML parser.
The guarded runtime, bootstrap, backtest, live, commit, and artifact-upload
steps are skipped and the workflow exits successfully. A sealed state is not
treated as a failed model job and cannot fall through to a Git write or other
side effect.

Re-enable a boundary only in a separate reviewed release after all applicable
items below are true:

1. The corrected historical epoch and its reconciliation evidence are
   committed, independently reviewed, and bound to exact expected identities.
2. The consuming data path verifies the approved epoch before exposing rows;
   the historical base is immutable and any permitted live suffix is
   append-only.
3. Offline unit, chronology, integrity, workflow-guard, and lint checks pass.
   Run a network smoke only after source access itself is approved.
4. The review names exactly which stages are reopening and why, prepares the
   exact new config bytes, and records their SHA-256. In the same commit, update
   both `config.yaml` and each affected workflow with an explicit execution plan
   bound to that digest. Never approve a config-only switch change.
5. The runtime switches remain a second gate. Use YAML boolean `true`, never a
   quoted value. Reopening live requires both `data.refresh_enabled: true` and
   `live.enabled: true` in the same reviewed commit; the SHA-bound workflow plan
   must independently authorize the live stage.
6. Backtesting is reopened only against the corrected epoch. Do not overwrite
   or relabel any pre-incident prediction, evaluation, report, or registered
   evidence artifact.

Until that release is committed, manual and scheduled dispatches are expected
to perform only checkout plus the safe guard and then skip.

## GitHub Actions workflows

- `test.yml` — runs unit tests on pushes and pull requests.
- `integration.yml` — verifies real result sources, a short walk-forward run and live snapshot generation.
- `backtest.yml` — runs the configured historical blind walk-forward benchmark when model code reaches `main`, and can also be run manually.
- `live.yml` — runs after model deployment and every Thursday/Sunday, evaluates due predictions, generates the next-draw predictions and commits the audit trail.

During the data-integrity incident the last three workflows remain sealed as
described above. The live workflow retains `contents: write` permission for its
ordinary role, but every Git-writing step is conditioned on the sealed cycle
output and cannot run while the incident guard emits `false`.

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
