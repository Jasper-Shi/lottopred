# Historical OOS Evidence Protocol

## Status after the registered-history incident

This protocol governs the append-only historical out-of-sample ledger after
data-integrity incident `DI-2026-08-20-registered-history`. The ledger is an
audit artifact, not a source of currently eligible scientific evidence. It
must not be used to reactivate a model, claim a hit-rate high-water, tune a
candidate, or stop the global search.

The strict governed status is
`no_eligible_evidence_after_data_integrity_tombstone`.

## Immutable raw prefix

The old ledger remains byte-for-byte intact as the prefix of
`reports/historical_oos/global_opportunities.jsonl`:

- event count: 18,259;
- opportunity event count: 18,251;
- ledger SHA-256:
  `546d21c96a3f3c5f077ea3b07b7a654a4d4b556a32274a5e17214443de0bf797`;
- final sequence: 18,258;
- final event SHA-256:
  `a8d1d9168eabda5914e8e0b5da4983524ada7f9b1bbe204e22bb1a645e511f19`.

These bytes retain what the earlier process registered. Retention is not
endorsement. Exact scores, rankings, high-waters, and other numeric claims
inside that raw prefix are archival and withdrawn from the governed evidence
view because they were evaluated against the invalidated registered history.
No replacement metric is inferred from the raw events.

## Three append-only governance events

Exactly three canonical hash-chain events follow the old prefix:

1. `data_integrity_incident_registered` binds the incident and seal artifact
   identities supplied by the caller.
2. `opportunity_set_tombstoned` selects every `opportunity` event in the fixed
   18,259-event prefix and applies `evidence_use=registered_data_only` and
   `eligibility=ineligible` / `eligible=false` without changing the raw event.
3. `high_water_erratum` records the strict-view result derived from that
   selection.

The resulting 18,262-event ledger has SHA-256
`1ab120c1db07fd2cc0b0dd34408c7182fab8ee2f2e00c265e258827d6623e476`.
Its final event is sequence 18,261 with event SHA-256
`9b0339b9c67a02d610463f023a8517b2779008dd971289766cff37fe0885b032`.

The validator scans the prefix to derive which events the selector covers. It
does not trust a reported opportunity count or reported high-water. The strict
view therefore has these semantics:

- the eligible count is `0`;
- the Final-6 high-water is `null`;
- the Top-12 high-water is `null`;
- the status is `no_eligible_evidence_after_data_integrity_tombstone`;
- `stop_global_search=false`.

`null` means there is no eligible evidence from which to compute a high-water.
It must never be rendered as `0/6`, because zero hits would be a numeric result
from an eligible opportunity and no such opportunity exists.

## Model dispositions

All exact numeric metrics attached to all 18,251 opportunities in the legacy
prefix are withdrawn, including V1 baseline producers and fixed controls. The
scope is the governed opportunity set, not a hand-maintained version list.

The operational closed/nonpromotion posture remains in force for V2, V4,
V5–V8, V10, and V11. This is a conservative safety decision, not proof of
rejection on corrected history. V1 is a paused baseline with no edge claim. V3
remains a paused, never-promoted shadow; the incident supplies no promotion
authority. V9 has no numeric evidence, so there is no V9 metric to withdraw or
replace.

This disposition does not alter raw bytes and does not assign new scores. Any
future candidate must start a new version and a new prospective cohort against
a separately reviewed, pinned data epoch.

## Incident and seal authority

The governance event binds the incident path, incident SHA-256, incident
artifact commit, seal path, seal SHA-256, and the commit sealed by that seal.
These identities are explicit API and CLI parameters; the implementation never
guesses them from the worktree and never opens the incident or seal artifact.

The seal was deployed to `main` by merge commit
`8debb2e13d117124dbf4b7cdf7e8744ee23e0e89`. The recorded deployment status is
`pinned_to_main_branch`, and the governance event binds that exact commit. The
external identities currently registered are:

- incident path:
  `evidence/data_integrity/DI-2026-08-20-registered-history/incident.json`;
- incident SHA-256:
  `b74e21722e1d95667504415c445169969d8a2810eaf3df90be3d83b359234ce5`;
- incident artifact commit:
  `b04393944ef12f78417dfb6151343c72d4c2a2ac`;
- seal path:
  `evidence/data_integrity/DI-2026-08-20-registered-history/seal.json`;
- seal SHA-256:
  `80397752105b567d6a8bdd3673b12ffa470a12efbd792719a4f6c89ef391f6fd`;
- sealed artifact commit:
  `b04393944ef12f78417dfb6151343c72d4c2a2ac`;
- deployed main commit:
  `8debb2e13d117124dbf4b7cdf7e8744ee23e0e89`.

The tombstone validator compares these values with the explicit external
authority supplied by its caller. It does not infer them from mutable worktree
paths.

## Validation and failure behavior

`src/lotto649/historical_oos_tombstone.py` validates every old and new line as
UTF-8 canonical JSON with a trailing newline, contiguous sequence, exact
previous-event link, and recomputed SHA-256 event hash. It additionally checks
the fixed prefix count, whole-prefix SHA-256, prefix head, exact three-event
order, explicit authority binding, all-opportunity selector, governed
high-water projection, and model disposition.

Any different prefix, broken chain, partial suffix, additional event, authority
mismatch, or self-reported erratum that differs from the derived projection
fails closed. A repeated append with the same explicit identities is
idempotent. The strict opportunity view returns each immutable raw opportunity
alongside its separate governance overlay.

The offline tool is `tools/append_historical_oos_tombstone.py`. All authority
arguments are required. Use `--validate-only` after an append to verify the
same bytes and projection. The module and tool do not access the network,
processed draw data, model code, prediction code, backtests, or the project
scorer.

This is a one-time, single-writer builder for an isolated feature worktree, not
an unattended or concurrent transaction writer. If a write, flush, or fsync is
interrupted, the resulting partial suffix fails validation; rebuild the file
from the fixed 18,259-event Git prefix before retrying. Do not repair or append
past a partially written suffix in place.
