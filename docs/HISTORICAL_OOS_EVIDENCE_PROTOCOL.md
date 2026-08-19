# Historical OOS Evidence Protocol

## Purpose and evidence boundary

This protocol preserves already-produced historical out-of-sample evidence. It
does not run a predictor or reconstruct a missing ticket. Legacy counts without
snapshots are copied unchanged. Where a complete frozen snapshot exists, the
importer independently counts set intersections and requires every stored hit
count and `matched_final` value to agree. Missing facts remain `null` or
`unknown`.

The permanent baseline is:

- manifest: `evidence/historical/actions/31888527837/manifest.json`
- raw Actions archives and unique CSV streams:
  `evidence/historical/actions/31888527837/`
- canonical ledger: `reports/historical_oos/global_opportunities.jsonl`
- line schema: `reports/historical_oos/global_opportunities.schema.json`
- importer and validator: `src/lotto649/historical_oos_evidence.py`

The 2020–2025 interval is consumed historical diagnostic evidence. Nothing in
this record restores blind or confirmatory status to it.

## Immutable GitHub Actions catalog

All seven unexpired Actions archives were copied byte-for-byte. The manifest
binds each ZIP to its artifact, run, job, implementation commit, and its exact
detail and summary CSV digests.

| Artifact | Run / job | Head SHA | ZIP SHA-256 | Detail SHA-256 | Treatment |
|---|---:|---|---|---|---|
| 9238718557 | 31853568483 / 94933923596 | `323b71607f6155b6b1b10b497f6b464aa9fc3bde` | `698fe9acdb499f1dadb7188649a2fed43359ea63b71f071cae80d0a8344147e9` | `78abb855c62249b84540d7b49ee75532a720f68269afb9c5f59562d168ab5ee8` | unique, 3,726 opportunities |
| 9238792690 | 31853798359 / 94934594417 | `1e0652c0fb642ab754d90b2f874d151564dce319` | `381a322f89335284c1f0be6e0b1b6aba57d31b4650b629aacfed0046f730f5d5` | `78abb855c62249b84540d7b49ee75532a720f68269afb9c5f59562d168ab5ee8` | exact duplicate of 9238718557; zero added |
| 9248543222 | 31888413139 / 95020953209 | `07f32ddc01ead33f2ea09a98af2fa9f597fc80e8` | `0d22ea952ae0a2b7f5e54e725e27a6a9d013b8c939b75d84fd5e8632e9d00084` | `21a113a89afe8ec7ec2c49ec991fbd13ac445de7b617aef5b72844bf56043db9` | unique, 4,347 opportunities |
| 9247962892 | 31888527837 / 95021219682 | `2310713e3f6fc6ae61a165874c049ac3cb69dffb` | `2e9a7d6ecd163fd64bd87354f5cf8e5776723ffaad572e1740d9cb6bea62cd50` | `e7e20bc089a8a4883468424ed6e499acaf0043a40f0d0ba821e3d75f0a598edd` | unique, 3,105 opportunities |
| 9247988617 | 31888831449 / 95021922612 | `276c8ad290f071962112b1b9a75300a7269ffed8` | `edcc1ad82f46b0705b15bb10e58159d0248d4cd219a55f9df5d3d690b3a99786` | `2c988e5590a6ed1706c4121bcc7ca490483ca2cb534824f4d5a55d67e4acfb78` | unique, 1,863 opportunities |
| 9248111786 | 31889097167 / 95022582496 | `2c0d4ca90d5c4dab49d32c531cc80aa920cecfd4` | `0e0fb08f25a45d0c092b8bf3a2afde8762af72c57195a70b653df9a96e8c335d` | `d0d24b8494a9bbc888b7481be528e63bd4b2c1f6880bc46b1cbf270bb7982912` | unique, 3,105 opportunities |
| 9248159303 | 31889275115 / 95023019432 | `7a8f7e6b480cdd2bef643cf595da166856307fe8` | `e0fb61fb0efbe57b12acfc6b7de2e182a5fb0a0fbeea1cc8637101b3fbbae652` | `d0d24b8494a9bbc888b7481be528e63bd4b2c1f6880bc46b1cbf270bb7982912` | exact duplicate of 9248111786; zero added |

The byte-identical raw summary CSVs are also retained. The five unique
detail/summary digest pairs are:

| Detail SHA-256 | Summary SHA-256 |
|---|---|
| `78abb855c62249b84540d7b49ee75532a720f68269afb9c5f59562d168ab5ee8` | `045b0549707b22aba33e5b8200e567675813d68046c0f6dc563f643a50a788e1` |
| `21a113a89afe8ec7ec2c49ec991fbd13ac445de7b617aef5b72844bf56043db9` | `187a27d32749af7d92c4da3c43fe1b06a8f1f673598ff127a9e9742e19d7cf76` |
| `e7e20bc089a8a4883468424ed6e499acaf0043a40f0d0ba821e3d75f0a598edd` | `6d4b122cdf7b9333f03dcf1bb4843ac702961886cfa78e792aa956fb406013fb` |
| `2c988e5590a6ed1706c4121bcc7ca490483ca2cb534824f4d5a55d67e4acfb78` | `dbb3581cc946d926a799b305eee306039f77e87c9753eba4597146d14336d1e6` |
| `d0d24b8494a9bbc888b7481be528e63bd4b2c1f6880bc46b1cbf270bb7982912` | `0cf0e6ca9eb770e4e0710f2c014070b0267187e71ed05f60cf99b1030472a315` |

The five unique detail streams contribute 16,146 rows. An exact repeated
detail SHA-256 is recorded as a `duplicate_stream` event and contributes zero
opportunities. Different detail digests remain different consumed
implementation streams. Because the legacy CSVs omit complete forecast
snapshots, cross-stream ticket-level deduplication is explicitly unknown.
Legacy rows still fail closed on structural facts that do not require a
forecast: the actual set must be six unique labels in 1..49, the bonus must be a
different legal label, `matched_final` must contain exactly `final6_hits`
distinct members of the actual set, and Top-K hit counts must be monotone. These
checks do not turn a missing legacy forecast into a verified ticket.

Inspection of each registered implementation commit showed the backtest passed
`draws[:idx]` into `model.predict(...)`. That supports
`chronology=implementation_strict_prefix`. The artifacts do not prove that each
forecast was durably persisted before its result was revealed, so
`pre_reveal_persistence=not_proven`.

## Evidence lanes and opportunity count

The ledger contains 16,767 opportunity events:

- 16,146 copied legacy rows from the five unique V1–V4 streams;
- 621 V10 rows joined from its already-stored `prediction_frozen` and
  `target_revealed_scored` hash-chain events and independently score-checked.

It also contains one `source_registered` event, two `duplicate_stream` events,
and four `coverage_gap` events, for 16,774 events in total.

V5, V6, V7, and V8 have committed aggregate reports but no preserved
per-target ticket snapshots in the catalog. Each is therefore a
`coverage_gap`: target-level Final-6 and Top-12 values and the maximum Final-6
hit count are `unknown`. No result is inferred from an aggregate summary.

V10 is the only imported lane with a complete stored forecast snapshot for all
621 targets. Its source report and source JSONL ledger are SHA-bound, the
source ledger's canonical hash chain is revalidated, and Final-6/Top-6/Top-12/
Top-18 hit counts plus `matched_final` are independently derived from the frozen
sets and revealed actual set. Import fails unless every derived value equals the
stored score. Each target must have exactly one freeze followed later in the
ledger by exactly one reveal; freeze and reveal target dates must each be
strictly increasing, and the prior target must be revealed before the next
target is frozen. Prefix `history_through` must equal the immediately previous
target date (and remain strictly before the new target), while `history_draws`
must advance by exactly one; both fields must equal the corresponding forecast
metadata, and all target identities must agree. The report's 621 `per_target`
records must also exactly equal the joined ledger evidence. Forecast and actual
sets must have exact sizes, unique integer labels in 1..49, Top-K values must
equal ranking prefixes, Final-6 must equal the sorted ranking Top-6, and the
ranking must agree with the frozen probabilities. The importer does not import
or call V10 model code or the project scorer. It also binds the report preflight
to the ledger's preflight event and records whether runner chronology checks and
warnings are explicitly clear.

## Three distinct high-water statements

These statements must never be collapsed into one headline:

| Claim | Current value | What it proves |
|---|---:|---|
| Maximum reported Final-6 hit count | at least 4/6 | A registered legacy CSV reports 4; the full forecast ticket is absent. |
| Maximum with a verified full stored snapshot | 3/6 | V10's frozen ticket and actual set are hash-validated; all hit fields independently recompute to the stored values. |
| Global maximum across every consumed attempt | unknown | V5–V8 lack per-target opportunity records, and legacy ticket-level deduplication cannot be completed. |

`Top12=6` means all six drawn main numbers appeared somewhere within a set of
twelve ranked candidates. It does **not** mean that the selected Final-6 ticket
matched six. Such a row is classified `top12_coverage_only`, never as a
Final-6 success.

A legacy row reporting `final6_hits=6` without its complete immutable Final-6
snapshot is classified `reported_unverified_final6`. It does not set
`stop_global_search` and must not be announced as success. An exact match
between a complete frozen Final-6 snapshot and the stored six-number result is
`verified_true`, but that fact alone still cannot stop the global search. The
original one-shot runner must also have a clear preflight/chronology record and
a target-bound, normalized leakage audit whose required checks all pass,
followed by its clear terminal event. Missing or failed audit evidence is
`verified_historical_final6_audit_not_clear` with
`stop_global_search=false`; only the audit-clear case is
`verified_historical_final6` with `stop_global_search=true`. Historical
verification still does not make a post-hoc 2020–2025 attempt prospective
evidence.

## Canonical ledger and failure behavior

Every line is UTF-8 canonical JSON using sorted keys, no insignificant
whitespace, finite JSON values, and a trailing newline. Sequences start at zero
and are contiguous. For event `i`:

```text
event_sha256 = SHA256(
  canonical_json(event_without_event_sha256)
  || ASCII(previous_event_sha256)
)
```

The first `previous_event_sha256` is 64 zeroes. Validation fails closed for a
non-canonical line, missing newline, broken sequence, broken previous hash,
incorrect event hash, source digest mismatch, undeclared duplicate stream,
source/ledger content mismatch, coverage mismatch, or registered high-water
mismatch. It also rejects a reveal placed before its freeze, duplicated or
non-monotone target events, a next-target freeze placed before the prior reveal,
non-contiguous prefix history, or disagreement between the V10 report and
source ledger—even if the altered source is rehashed into a cryptographically
valid new chain.

Import is deterministic and idempotent: the same sources and manifest yield the
same ledger bytes and SHA-256. The migration never rewrites a different
existing ledger. Future prospective versions must write their native complete
pre-draw snapshots through a separately reviewed append path; they must not
edit this historical baseline or use this importer to reconstruct predictions.

## Offline commands

From the repository root:

```bash
python tools/import_historical_oos_evidence.py
python tools/import_historical_oos_evidence.py --validate-only
```

Both commands read only committed local sources. They perform no network access,
model execution, prediction generation, or invocation of project scoring code.
Their only score operation is deterministic set-intersection verification of
already-frozen complete snapshots.

## Requirements for V11 and later

Every new research opportunity should preserve, before reveal, the target date,
model/version and implementation identity, strict-prefix digest, complete
ranking and Top-6/12/18 sets, selected Final-6 ticket, and a digest of the
canonical forecast payload. After reveal, append the immutable actual main
numbers and independently matched evaluation linked to that forecast digest. Promotion and
success language must use the prospective cohort for that frozen version, not
the consumed 2020–2025 history.
