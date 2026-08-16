# Lotto 6/49 Prediction Research System

A reproducible, auditable research pipeline for testing whether historical Canadian LOTTO 6/49 Classic Draw data contains any stable out-of-sample predictive signal.

The project does **not** assume that lottery draws are predictable. Every serious model is measured against the fair-lottery baseline and evaluated using strict chronological walk-forward testing.

## V1 capabilities

- Builds a historical draw dataset from the WCLC since-inception PDF, a yearly archive bridge for periods where the WCLC PDF lags, and WCLC's current official results page.
- Cross-checks overlapping sources and fails on disagreement rather than silently training on conflicting data.
- Runs strict walk-forward backtests without future leakage.
- Produces inclusion probabilities for all 49 numbers.
- Includes random, long-frequency, recent-frequency, EMA/gap, logistic-regression and ensemble models.
- Scores Top-6, Top-12, Top-18, Brier score, log loss, mean actual rank and hit distributions.
- Writes immutable pre-draw JSON prediction snapshots.
- Evaluates snapshots after the result becomes available.
- Sends optional SMTP email alerts for configured hit thresholds.
- Uses GitHub Actions for unattended Thursday/Sunday live cycles, so a local computer does not need to remain on.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest -q
lotto649 bootstrap
lotto649 backtest
lotto649 live
```

`lotto649 bootstrap` requires internet access because it refreshes historical/current result sources.

## Execution paths

### Historical research path

```text
past data -> walk-forward prediction -> reveal historical result -> score -> move one draw forward
```

A model predicting draw `t` can see only draws before `t`.

### Live path

```text
refresh results
  -> evaluate already-committed prediction snapshots
  -> optional email alert
  -> update history
  -> generate next Wed/Sat snapshots
  -> GitHub Actions commits the audit trail
```

## Email configuration

No email credentials are required for testing, backtesting, or predictions. When email alerts are wanted, configure these GitHub repository secrets:

```text
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=<gmail address>
SMTP_PASSWORD=<Google App Password>
EMAIL_FROM=<gmail address>
EMAIL_TO=<destination address>
```

Use a **Google App Password**, not the normal Google account password. See `docs/OPERATIONS.md`.

## Data-source policy

The WCLC since-inception PDF is the primary historical source, but it can lag recent years. V1 uses annual pages from lotto.net only as a bridge, then cross-checks every overlapping draw with WCLC wherever overlap exists. The current WCLC results page is authoritative for new live draws. Any source disagreement stops the pipeline.

## Research warning

For a fair LOTTO 6/49 Classic Draw, every exact six-number combination has the same jackpot probability. Apparent hot/cold/date/sum patterns can arise from randomness and overfitting. This project exists to test those claims rigorously; it is allowed to conclude that no exploitable signal exists.

See:

- `docs/ARCHITECTURE.md`
- `docs/MODEL_PROTOCOL.md`
- `docs/OPERATIONS.md`
- `docs/RESEARCH_ROADMAP.md`
- `docs/V2_V4_RESULTS.md`
- `docs/experiments/V5_pair_affinity_results.md`
- `docs/experiments/V6_entropy_regime_results.md`
- `docs/experiments/V7_main_bonus_role_bias.md`
- `docs/experiments/V7_main_bonus_role_bias_results.md`
- `docs/research/V7_mechanical_bias_basis.md`
- `docs/experiments/V8_fixed_recurrence_harmonic.md`
- `docs/research/V8_fixed_spectral_basis.md`
