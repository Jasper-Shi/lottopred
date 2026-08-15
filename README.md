# Lotto 6/49 Prediction Research System

A reproducible, auditable research system for testing whether historical LOTTO 6/49 draw data contains any stable out-of-sample predictive signal.

This repository deliberately separates **research**, **historical walk-forward backtesting**, and **live forward testing**. It does not assume that lottery draws are predictable; every model is compared with an equal-probability random baseline.

## V1

- Official-history ingestion and validation
- Strict walk-forward backtesting with no future leakage
- Probability estimates for all 49 numbers
- Top-6 / Top-12 / Top-18 evaluation
- Random, frequency, EMA/gap, logistic and ensemble models
- Immutable pre-draw prediction snapshots
- Post-draw evaluation
- Optional email alerts
- GitHub Actions for tests, backtests and live twice-weekly operation

Codex Cloud can be used to develop the repository; GitHub Actions handles scheduled execution, so a local computer does not need to stay on.

See `docs/ARCHITECTURE.md`, `docs/MODEL_PROTOCOL.md`, and `docs/OPERATIONS.md`.

> This is a statistical research project, not evidence that LOTTO 6/49 can be predicted. A fair draw gives every exact six-number combination the same jackpot probability.
