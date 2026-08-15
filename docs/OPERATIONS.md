# Operations Guide

## Cloud execution

No local computer needs to stay running.

- **Codex Cloud**: development, code changes, debugging and research.
- **GitHub Actions**: recurring production-like execution.

## GitHub Actions workflows

- `test.yml` — runs unit tests on pushes and pull requests.
- `backtest.yml` — manually builds the dataset and runs the configured historical blind walk-forward benchmark.
- `live.yml` — runs Thursday/Sunday, evaluates due predictions, generates the next draw predictions and commits the audit trail.

The live workflow has `contents: write` permission because snapshots/results are committed back to the repository.

## First deployment checklist

1. Merge the V1 implementation to `main` after tests pass.
2. Confirm repository Actions are enabled.
3. Manually run `lotto649-backtest` once and inspect the report artifact.
4. Manually run `lotto649-live-cycle` once.
5. Confirm `data/processed/draws.csv` is created and a next-draw JSON exists under `predictions/`.
6. Add email secrets.
7. Trigger the live workflow manually once more to verify SMTP configuration.

## Gmail email setup

The application uses Gmail SMTP with STARTTLS. Do **not** put credentials in source code or `.env` committed to Git.

Required repository secrets:

```text
SMTP_HOST        smtp.gmail.com
SMTP_PORT        587
SMTP_USERNAME    your Gmail address
SMTP_PASSWORD    your Google App Password
EMAIL_FROM       your Gmail address
EMAIL_TO         notification destination
```

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
