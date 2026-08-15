# Operations Guide

## Cloud execution

No local computer needs to stay running.

- **Codex Cloud**: development, code changes, debugging and research.
- **GitHub Actions**: recurring production-like execution.

## GitHub Actions workflows

- `test.yml` — runs unit tests on pushes and pull requests.
- `integration.yml` — verifies real result sources, a short walk-forward run and live snapshot generation.
- `backtest.yml` — runs the configured historical blind walk-forward benchmark when model code reaches `main`, and can also be run manually.
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
