# Codex Handoff

## 2026-09-13 research checkpoint

The user-requested
[`V1_ensemble_verified_history_diagnostic_20260913`](experiments/V1_ensemble_verified_history_diagnostic.md)
has completed its single registered run: all 627 consumed 2020–2025 targets,
three frozen producers per target, 1,881 prediction files, and 627 evaluations.
PR #42 normally merged reviewed source `c886604cecb65ed9879d90568a1541430223b030`
at execution commit `5d348b72938ece45e41d42e7f9bb4850d220c740`.
The source passed 1,213 CI tests and independent Standards/Spec review with
0 blocker/major/minor. The independent V1 consumption ref points to that
execution commit and must never be updated, deleted or reused.

V1 mean Top-6/12/18 hits are 0.720893 / 1.395534 / 2.078150; all are below
fair expectations. Mean Final-6 hits are 0.720893 versus the random control's
0.779904. V1's best Final-6 is 4/6 on 2020-07-25; none of the three producers
has a 5/6 or 6/6. Probability scoring also trails the fair constant. This
experiment closes with a negative diagnostic result, no promotion and no
future-winning claim. The broader 6/6 Goal is not complete. No hit-triggered
email was sent. Do not tune or rerun this V1 experiment.

The immutable full report, every prediction/evaluation, ledger, read-only audit,
and Chinese interpretation are under
[`reports/v1_ensemble_verified_history_diagnostic_20260913/`](../reports/v1_ensemble_verified_history_diagnostic_20260913/summary.zh-CN.md).
The verified input contains 4,444 draws through 2026-08-22; each predictor saw
only the prefix strictly before its historical target. Actual forecast generation
was 2026-09-13 00:59:20–01:05:40 UTC, never backdated. These are corrected-history
sensitivity diagnostics, not restored blind or prospective predictions.
`config.yaml`, models, production switches and all pre-existing artifacts
remain unchanged.

V12 I2 merged in PR #40 at
`40f6e4098d4ed59f9421196efb8573c66c48928a`. New historical authorization
PR #44 normally merged source `f194d5cccf30868f1088680e338fcad9cb697949`
at `baa08ecb77555e17f383ef2998bea3c433e16f74`, after 1,213 passing CI tests
and independent Standards/Spec review with zero findings. The single canonical
invocation then exited 1 before creating any claim, ledger or prediction.
The remote V12.0.1 lease was exactly 404 both before and after invocation.
V12.0.1 is **startup-failed, frozen against retry, and not scored**; no scientific
Reject result exists. See the append-only
[startup incident](../evidence/research_execution_incidents/v12-0-1-20260913/startup-incident.json).

GET-only diagnosis confirmed a GitHub commit-message representation mismatch:
an existing raw commit has one trailing LF but its JSON response has none,
which the frozen lease verifier rejects. The original invocation retained no
phase/nonce/OID/POST receipt, so its exact failure stage and whether a dangling
commit was uploaded remain unknown. Do not infer either from the later 404,
retry the command, reuse either old authorization source, or alter the frozen
I2 closure. PR #45 normally merged the incident and live closure at
`3015078e251bdcbb92719e1b291b1807525fef16`. Obsolete PR #41 is closed and
unmerged; its source branch and audit history are preserved. V12.0.1 produced
no scientific result or 6/6.

V12.0.2 has now completed its **sole authorized historical run: 627/627
consumed 2020–2025 targets, frozen disposition Reject, no Final-6 6/6**.
The candidate's best Final-6 was 3/6 on 11 dates. This is a negative historical
diagnostic, with no promotion, future-winning claim or completed 6/6 Goal.
The full interpretation and audit status are in
[`V12_0_2_HISTORICAL_RESULTS.md`](research/V12_0_2_HISTORICAL_RESULTS.md).

The completed sequence preserves the H12 fingerprint, pure core, dates, seed,
controls and ten gates registered in
[`R3`](experiments/V12_0_2_historical_operational_rebinding.md):

- I3 source `978475ee472af9f6c6ad46c3d9de1f8a90b39dae` normally merged in
  [PR #48](https://github.com/Jasper-Shi/lottopred/pull/48) as
  `0c54d443325a2dbf59bc5fa70a0288593f8df9b9` (`K_H3`).
- Authorization source `caaeaca6d5ddfd3705171d86fddd3c53bdd75de6` normally
  merged in [PR #49](https://github.com/Jasper-Shi/lottopred/pull/49) as
  execution authority `b7fa81d6d5facc1730700cd527362df79f457cf8` (`M_A_H3`).
- Permanent lease `refs/heads/v12-consumption-v12.0.2` points to
  `a8b264a5d3db199e831b0c06cb0697794766d160`. Preserve it without update,
  deletion, adoption, retry or reuse.
- Worker artifact commit `c9b483f6e89bf73eade28829188fbebe745e28c0` has sole
  parent `b7fa81d6d5facc1730700cd527362df79f457cf8`. It is pushed on
  `codex/v12-0-2-historical-evidence`; protected-main publication remains
  pending at this evidence-source checkpoint. Preserve this commit as an
  ancestor through an ordinary merge; never squash, rebase or rewrite it.

The six immutable worker files are the
[startup journal](../reports/v12_post_rng_parity_composition_transition_v12.0.2_historical.startup.jsonl),
[claim](../reports/v12_post_rng_parity_composition_transition_v12.0.2_historical.claim),
[scientific ledger](../reports/v12_post_rng_parity_composition_transition_v12.0.2_historical.ledger.jsonl),
[JSON report](../reports/v12_post_rng_parity_composition_transition_v12.0.2_historical.json),
[Markdown report](../reports/v12_post_rng_parity_composition_transition_v12.0.2_historical.md)
and [commit manifest](../reports/v12_post_rng_parity_composition_transition_v12.0.2_historical.commit.json).
The independent negative-result audit by `/root/i3_independent_output_audit`
passed within its stated scope, with 0 blocker, 0 major and 0 minor findings.
It checked all 627 actual main/bonus results and complete visible prefixes,
1,255 ledger events, 13 startup events, all 18 bootstrap intervals and 12 exact
fair tests. It used frozen scores without regenerating forecasts or refitting.
The [audit JSON](../evidence/research_audits/v12-0-2-historical-20260913/independent-audit.json)
and [audit report and limitations](../evidence/research_audits/v12-0-2-historical-20260913/independent-audit.md)
record its scope. This completed negative-result audit does not establish a
6/6 leakage-audit milestone or Goal completion. The worker's internal
`audit.complete=true` remains a separate creation-time check.
Root's separate GET-only
[remote observation](../evidence/research_audits/v12-0-2-historical-20260913/remote-observation.json)
passed its lease, protection, Git and PR #48/#49 review/CI checks; that observation
was performed by root and is separate from the independent audit.

The report's `audit_publication=pending_git_integration` is its immutable
creation-time status. Later Git integration and separate audit receipts resolve
publication without changing a worker file. Keep the experiment closed against
retuning or another run; a next experiment still requires separate registration.
No manual email was sent during evidence preparation. The historical R3
registration checkpoint was **REGISTERED / NOT IMPLEMENTED / NOT AUTHORIZED /
NOT SCORED**; those historical words do not describe the completed run.

The V12.0.1 live seed and canary windows have expired. That lane is
`superseded_unexecuted`, recorded in the separate
[live-lane closure](../evidence/research_closures/v12-post-rng-parity-composition-transition-v2-live-superseded-unexecuted.json).
That live-only closure does not reject or consume the historical experiment.
Production remains paused, and PR #37's ticket-email direction remains outside
this research. The older operational checkpoints below describe their dated
state and do not supersede this section.

Last verified on 2026-08-24 against a production history containing Stage-1
activation merge ancestor `3b72d6f3f5cbaf7122d9f4941215c33edac4a6ee`
and corrected-epoch artifact commit
`b04393944ef12f78417dfb6151343c72d4c2a2ac`. This document does not pin the
mutable post-documentation `main` head.

The V12 registration uses exact production authority baseline
`4a617f2c1575a165b42878600753a01ddf2ced03`; this identity is a frozen research
input, not a claim that later mutable `main` still has that head.

## Current state

This repository is the execution and audit system. Codex develops and reviews the
code; outside an incident hold, GitHub Actions is the unattended runner that
commits live artifacts. Chat history is not required to continue because the
research decisions are recorded here and in `V2_V4_RESULTS.md`.

> **Data-integrity incident hold (2026-08-20):** the operational roles in the
> table below describe the pre-incident system, but execution is currently
> suspended. The original gated Stage-1 manual canary expired unexecuted and
> grants no dispatch authority. Pre-Stage-1 ancestor
> `60f972b217f7bd23d1b4807e96034db0cfd1fe2e` had
> `data.refresh_enabled=false`, `backtest.enabled=false`, and
> `live.enabled=false`. Production now contains activation merge ancestor
> `3b72d6f3f5cbaf7122d9f4941215c33edac4a6ee`; its exact deployed config has
> data refresh and live `true` while backtest remains `false`. Integration and
> backtest remain safe no-ops, and the disabled mode remains recognized by
> SHA-256
> `ad3237bc57c85013e85dad16d1b6f04f43b50991d666a4b1528bf5b8614a76b6`.
> No refresh, backtest, evaluation, or prediction has run under Stage 1; no
> manual dispatch is currently authorized. The legacy
> 4,434-row history through 2026-08-22 is not strict real-calendar evidence.
> A reviewed candidate now seals a corrected 4,442-draw base through
> 2026-08-15 and a two-event, dual-source suffix through 2026-08-22. The
> verified view contains 4,444 draws. Its external seal SHA-256 is
> `80397752105b567d6a8bdd3673b12ffa470a12efbd792719a4f6c89ef391f6fd`;
> the suffix file SHA-256 is
> `b91be6a4057648abd86dc0e6fc5d762fc4cd9b222519c147d635703cc550a803`;
> and its head event SHA-256 is
> `3022b98fefbe3dbbc80423574319c169edcc845bf2218152c6abe18d0be27475`.
> Append-only authority now begins at registry genesis commit
> `a6857d6b4e6e532062f484bcce4466f76ba4327b`, event
> `22bcfe219c091dbcdb751ef7a2d9d5251f3040770de6e2e825ac5c64fc69c63d`.
> The operational reader resolves that registry, seal, suffix, and evidence from
> immutable Git blobs; local worktree replacements are never history authority.
> The verified-history read interface is now the sole input to the direct
> backtest boundary. Backtest remains false, and the legacy bootstrap/live
> writer interlocks remain closed. The old Stage-1 data/live true bytes must not
> be consumed; D0 must reseal the operational outputs all-false. The dual-source
> collector, offline preparer, local bare-repository
> CAS, fixed-repository GitHub publisher, isolated execution/artifact handoff,
> and capability-scoped exact remote `P -> A` publisher remain disconnected
> from CLI. PR #31 merged the fixed code-level orchestration at
> `2fe56a40532f7be2586a5cfc004699561556e849`; it
> composes collect through remote P publication/reload, a fresh detached-P
> handoff, private exact-P worker execution, A freezing, and remote A
> publication/reread/fresh reload. It reads literal-B configuration and trusted
> clocks internally and exposes no caller-injectable configuration, clock, or
> adapter seam. The private worker has no standalone entry point, and the
> parent binds the worker plus its imported `lotto649` source modules to P.
> It remains unimported by every CLI. PR #32 fixed due-prediction provenance by
> proving each prediction's unique immutable origin across the complete commit
> DAG and merged as pre-Stage-1 ancestor
> `60f972b217f7bd23d1b4807e96034db0cfd1fe2e`.
> The authorized
> disposable OID/CAS canary succeeded on 2026-08-24, and production `main` now
> enforces administrator, force-push, and deletion protection. A real production
> end-to-end `P -> A` canary has not run.
>
> The original Stage-1 route is
> `merged_armed_expired_unexecuted_pending_D0_reseal`. Final candidate
> `5c5dc355ce1bfdae1f467eefa35062aff59d9614` passed independent Standards and
> Spec review with 0 blocker, 0 major, and 0 minor findings, and production
> contains activation merge ancestor
> `3b72d6f3f5cbaf7122d9f4941215c33edac4a6ee`. It binds only `live.yml`
> `workflow_dispatch` to exact config
> SHA-256
> `d53a9a9eed5ab434b021472135d6aed65c2c052339e0dfb88f8c00d46c0d8931`.
> Repository permissions are read-only and checkout does not persist
> credentials. Only the protected canary step receives the dedicated
> publication credential, and it calls only
> `orchestrate_github_live_cycle(*, token=...)`; no CLI, ordinary Git push,
> automatic retry after worker start, or unattended live schedule was present.
> At design time, `workflow_dispatch` required `expected_sha`, the canonical
> 40-hex production `main` target established by independent review. No dispatch
> SHA was approved before expiry; neither the candidate nor activation merge
> ancestor became that value. The plan stored only
> `approved_sha_source=post_merge_review`; any attempted value would have been
> recorded in dispatch evidence. On the exact Stage-1 config, invalid identity
> or early timing would have written all-false outputs and failed red. The
> publication credential was never installed, and the fixed
> `2026-08-27T15:15:00Z` canary window expired without execution. It must not be
> dispatched late, re-dated, or reused; a separate D0 all-false reseal is
> pending. No manual dispatch ran and no unattended live schedule existed. A
> successful P or A advance would have invalidated its approved SHA and blocked
> rerun. The expired plan has no Stage-2
> continuation. The later V12.0.1 live lane also expired unexecuted. Future
> live recovery requires its own new registration and reviewed canary; R3
> provides no live or scheduling authority.
> The complete facts and blocker list are in `OPERATIONS.md`. No component or
> preparation authorizes execution. Re-enable only through the reviewed
> two-gate release described in
> [`OPERATIONS.md`](OPERATIONS.md#data-integrity-incident-kill-switch).
>
> The historical OOS opportunity ledger preserves its exact 18,259-event
> legacy prefix, then appends three governance events bound to this deployed
> seal. All 18,251 legacy opportunities are `registered_data_only` and
> ineligible; the governed eligible count is `0`, both high-waters are `null`,
> and `stop_global_search=false`. See
> [`HISTORICAL_OOS_EVIDENCE_PROTOCOL.md`](HISTORICAL_OOS_EVIDENCE_PROTOCOL.md).

| Component | Status | Meaning |
|---|---|---|
| V1 live suite | Paused baseline | Before the hold, six models created forward snapshots: `random`, `long_frequency`, `recent_frequency`, `ema_gap`, `logistic`, and `ensemble`. |
| V2 statistical | Rejected | Retained for reproducibility and historical research; absent from the live model list. |
| V3 boosting | Paused shadow | Before the hold, it created immutable snapshots and evaluations beside V1; it did not change V1 predictions or ensemble weights. |
| V4 ensemble | Rejected | Retained for reproducibility and historical research; absent from the live model list. |
| V12.0.0 parity transition | Superseded unexecuted | Its fixed canary route expired without execution. This is not Archive, Reject, consumed evidence, or a model result. |
| V12.0.1 parity transition | Startup failed; frozen against retry; not scored | Its sole invocation after PR #44 failed before any claim or forecast. The exact failure stage and remote POST activity remain unknown. Its separate live lane expired unexecuted. |
| V12.0.2 parity transition | Completed once; frozen Reject | All 627 consumed targets were scored. Candidate best Final-6: 3/6 on 11 dates; no 6/6. Independent audit/publication status is separate; no retuning, rerun or live lane. |
| 2020–2025 legacy diagnostic | Consumed / strict-blind label withdrawn | The old run used 621 registered rows from a malformed and incomplete history rather than the corrected 627-draw calendar. Exact metrics are archival only; correction cannot make the known outcomes untouched. |
| 2026+ snapshots | Immutable source-relative artifacts | Their pre-draw chronology remains auditable. The 2026-08-19/22 outcomes are independently source-verified, but predictions trained on the malformed legacy history are not corrected-history promotion evidence. |

No version has established a reliable lottery-prediction edge. V3's historical
ranking lift is interesting but not statistically convincing.

### V12 scientific authority and completed sequence

The immutable V12.0.0 scientific authority is
[`V12_post_rng_parity_composition_transition.md`](experiments/V12_post_rng_parity_composition_transition.md).
It freezes one post-RNG odd-count transition hypothesis and one literal
pseudo-parity control against governed `PublishedHistory` authority
`4a617f2c1575a165b42878600753a01ddf2ced03`: 4,444 draws through
2026-08-22. The only historical diagnostic remains exactly 627 consumed targets
in 2020--2025, split 314/313; every 2026 outcome is excluded.

V12.0.0 remains `superseded_unexecuted`. V12.0.1's actual historical startup
failure and its separate expired live lane retain the distinct dispositions
recorded in the 2026-09-13 checkpoint above. Neither old authorization source
grants another attempt.

The [`R3 specification`](experiments/V12_0_2_historical_operational_rebinding.md)
and its registration-time file bindings remain frozen at R3. The sequence
`R3 < I3 < K_H3 < A_H_s3 < M_A_H3 < L_H3 < run_H3` completed at the identities
recorded above. The ordinary authorization merge supplied execution authority;
the source branch and registration alone never did. That sole attempt is now
consumed and closed. R3 has no live lane, shadow activation or production wiring,
and its historical execution did not require D0 or live-canary success.

## How the implemented system runs

The CLI entry points are:

```bash
lotto649 bootstrap
lotto649 backtest
lotto649 live
```

The disposable publication canary and protected production `main` were verified
on 2026-08-24. The production publication path is the sole public
`orchestrate_github_live_cycle(*, token=...)` boundary, not a CLI command.
`backtest` walks forward chronologically over the Git-authenticated verified
history. The live cycle may refresh history, evaluate due snapshots, and create
predictions for the next Wednesday or Saturday only inside the isolated
workspace obtained after the remote publisher installs P and a fresh authority
reload succeeds. That context must remain open until the exact artifact commit
A (sole parent P) is remotely compare-and-swapped and freshly reloaded. The
legacy CLI `bootstrap` and `live` commands remain stopped by the writer
interlock. Backtest remains false and unauthorized. The old Stage-1 workflow
bytes are expired and grant no dispatch authority; D0 must reseal them all-false.
V12.0.1's live lane also expired. A future production attempt requires a new
live registration and reviewed release with its own exact digest, repository,
ref, event, production SHA, checkout, credential, time, and source gates.
R3 historical authorization cannot reach this orchestrator.

`config.yaml` deliberately separates two selections:

- `backtest.models`: the configured historical comparison suite, including V2,
  V3, and V4.
- `live.models`: the approved V1 suite plus V3.

`live.shadow_models: [v3_boosting]` adds `"role": "shadow"` to V3 snapshot
metadata; all other live snapshots receive `"role": "primary"`. The role is a
research label, not a separate execution path. In the pre-hold path V3 was
evaluated and could trigger the common hit-threshold email. It does not feed the
V1 ensemble.

All live models currently inherit `project.model_version: v1.0.0` for the
`model_version` field and filename. Therefore the model identity
`v3_boosting` plus `metadata.role == "shadow"` distinguishes the V3 shadow
snapshot; do not infer that it is a V1 algorithm from the shared version tag.
Change version semantics deliberately rather than renaming committed snapshots.

## Current committed forward checkpoint

The immutable pre-hold artifacts originated at `main` commit
`9f16e20c726c7b65eed1d387c4c725d51248f570`, remained present at ancestor
`e3c39dda3233cec5933430f22afd6aa8d78a998d`, remained present at pre-Stage-1
ancestor `60f972b217f7bd23d1b4807e96034db0cfd1fe2e`, and remain present at
Stage-1 activation merge ancestor
`3b72d6f3f5cbaf7122d9f4941215c33edac4a6ee` and its descendants:

- `data/processed/draws.csv` contains 4,434 registered rows through 2026-08-22;
- evaluations for all seven pre-hold live models are committed for both
  2026-08-19 and 2026-08-22, including
  `evaluations/2026-08-19__v3_boosting__v1.0.0.json` and
  `evaluations/2026-08-22__v3_boosting__v1.0.0.json`;
- seven immutable predictions for target 2026-08-26 are committed, including
  `predictions/2026-08-26__v3_boosting__v1.0.0.json`.

The newest V3 snapshot was generated on 2026-08-23 at 11:36 EDT from 4,434
registered draws through 2026-08-22 and is labeled `shadow`. Its target was not
yet knowable at this checkpoint, so no 2026-08-26 evaluation is committed.
The expired Stage-1 plan preregistered exactly seven descriptive-only
evaluations of this legacy cohort and seven 2026-08-29 predictions. It never ran,
none of those artifacts was created by that plan, and they must not be created
late.

The corrected epoch is separate and append-only. Its sealed base contains 4,442
draws through 2026-08-15. The suffix binds the 2026-08-19 and 2026-08-22 draws
to immutable WCLC and Loto-Québec source receipts at evidence commit
`60dbd42a502850091508491f9011f9a08acf894f`. The public verified-history loader
reconstructs a 4,444-draw view through 2026-08-22 only when the external seal,
suffix-file, and suffix-head identities all match. `history_registry.py` pins
the one-line genesis at commit `a6857d6b4e6e532062f484bcce4466f76ba4327b`
and proves the selected revision's immutable Git state; `operational_history.py`
combines that authority with the full validator behind one load interface.
Backtest consumes that interface. Public live evaluation/prediction entry points no longer accept an
arbitrary draw list and currently stop at the writer interlock; the private
post-writer helpers accept only the `VerifiedHistory` returned by the live
cycle. This consumer integration is not authorization to resume execution.

Prediction files are immutable. Within the post-writer stage,
`_generate_next_predictions` skips an already existing target/model/version
path, and the storage layer rejects overwrites by default. Never edit a snapshot
after its result is knowable.

## GitHub Actions and email

The configured workflows are:

- `test.yml`: unit tests on every push and pull request.
- `integration.yml`: source/model smoke checks, sealed to an all-false guard in
  Stage 1.
- `backtest.yml`: configured historical backtest, currently sealed to checkout
  and an all-false guard.
- `live.yml`: the old Stage-1 branch is expired and pending D0 all-false reseal;
  it must not be dispatched. V12.0.1's later live lane also expired. Any
  replacement wiring requires a new live registration; R3 adds none.
- `email-test.yml`: explicit Gmail SMTP smoke test.
- `research-progress-email.yml`: configured hourly (`17 * * * *`) Chinese
  committed-state report. It is read-only, uses a full-history checkout with
  `persist-credentials=false`, loads history through the production
  `load_published_history(HEAD)` authority, and passes only the two SMTP
  secrets to its send step. It neither runs nor imports live refresh, model,
  backtest, or data-refresh entry points and does not query the GitHub API.
- `research-v2-fast.yml` and `research-v2-v4.yml`: historical branch-specific
  research workflows retained for auditability.

The last committed pre-hold live-cycle boundary is `main` commit
`9f16e20c726c7b65eed1d387c4c725d51248f570`: it appended the 2026-08-22 draw and
evaluations and froze the 2026-08-26 predictions. Its parent `0ef1883` appended
the 2026-08-19 evaluations and froze the 2026-08-22 predictions. Those artifacts
remain immutable during the hold.

The latest committed `ensemble v1.0.0` evaluation, for 2026-08-22, records
Top-6/12/18 as `2/3/3`. Its source prediction records 4,433 input draws through
2026-08-19, while the production published-history authority reconstructs 4,443
draws through that date. The hourly report therefore labels this
incident-affected, pre-incident/legacy malformed-history cohort
`descriptive-only` and `nonpromotion`; it must not silently present the hits as
corrected-history or promotion evidence.

The 2026-08-26 cohort is now sealed by
`evidence/data_integrity/DI-2026-08-20-registered-history/legacy-2026-08-26-prediction-cohort.json`.
It pins the exact seven prediction blobs and the 4,434-row registered history
visible at their origin. Once the corrected 2026-08-26 result is published,
their evaluations must include a recomputed `prediction_source` classified as
`sealed_legacy_incident_history`; `actual_history` separately identifies the
corrected result source. These evaluations are descriptive prospective hits,
not corrected-history training or promotion evidence.

The historical Gmail alert smoke test succeeded on 2026-08-15
([Actions run 31887288254](https://github.com/Jasper-Shi/lottopred/actions/runs/31887288254)).
Secret values are not readable from the repository; that run establishes only
that usable configuration existed at that time, not its current state.

Email requires only these repository secrets:

```text
SMTP_USERNAME=<Gmail address>
SMTP_PASSWORD=<Google App Password>
```

Defaults are `smtp.gmail.com:587`, with sender and recipient both equal to
`SMTP_USERNAME`. `SMTP_HOST`, `SMTP_PORT`, `EMAIL_FROM`, and `EMAIL_TO` are
optional overrides for manual and legacy paths. The exact-P orchestration
deliberately passes only `SMTP_USERNAME` and
`SMTP_PASSWORD` into its isolated worker, so that boundary always uses the
Gmail defaults. Missing credentials or an SMTP exception records
`email_sent=false` and does not block evaluation, prediction, freezing, or A
publication. The dedicated email smoke workflow treats a false send as a
failure so configuration can be tested explicitly. After the private P worker
starts, any orchestration failure receives no automatic retry because an email
may already have left the process.

The hourly progress workflow is independent of the Codex/chat thread and of a
Codex Goal or live worker. Its concurrency group serializes only this email job
and does not cancel an in-progress run. It accepts only the first scheduled `main`
attempt (`GITHUB_RUN_ATTEMPT=1`), exact checkout/workflow SHA, and fixed workflow
identity. It reads only committed facts, labels current PR/CI, remote protection,
and Codex in-flight work as not queried, and sends at most once with no retry.
An SMTP false result or exception makes this email job red; unlike a live hit
alert, it has no model/artifact work to preserve. The body is built before SMTP
and never claims successful delivery. Setup installs only the reviewed
hash-locked wheels in `requirements/research-progress-email.txt` with
`--require-hashes --only-binary=:all:`. They are the narrow transitive imports
needed by the production history loader; after setup, the only intended network
side effect is SMTP.
The cron is a scheduling request, not a punctual real-time guarantee. This
workflow is configured but not yet operationally proven; that wording may be
changed only after the merged workflow's first scheduled run is verified.
`GITHUB_RUN_NUMBER` is rendered as “第 N 次更新,” not as elapsed research hours.
The UTC report-generation instant is captured inside the process and is kept
separate from the committed evidence timestamp; it is not claimed to be the
GitHub service start time. Without a cross-run cursor, the report does not claim
whether an evaluation was added “this hour.” It instead reports the pending
latest prediction and the latest committed evaluation separately. Its displayed
hit counts are recomputed from the matching committed prediction and the
production published-history draw; inconsistent evaluation JSON fails closed.

Current alert thresholds in `config.yaml` are final-combination hits `>= 4` or
Top-12 hits `>= 5`.

## Data-source and fallback behavior

The legacy source adapters remain in `src/lotto649/data_sources.py` for audit and
future refactoring, but they are no longer a valid operational-history write
path. Legacy live refresh remains behind its writer interlock. The old Stage-1
release remains an immutable record, but its fixed window expired and its
workflow/config bytes grant no dispatch authority. D0 must reseal those bytes
before any newly registered live recovery wiring; the V12.0.1 live route also
expired and cannot be revived. The disposable OID/CAS canary and production-main
protection were completed on 2026-08-24; the production
`P -> A` canary has not run.
The pre-incident reconciliation policy was:

1. Use the WCLC since-inception PDF for years before `bridge_start_year` (2024).
2. Use lotto.net annual HTML as the machine-readable bridge from 2024 onward.
3. Use the current WCLC results page as the authoritative current source and as
   an independent check wherever it overlaps the bridge.
4. Retain committed draws only when they agree with newly selected source data.
5. Require a strictly ordered, unique chronology of more than 4,000 draws, with
   no suspicious post-2000 gap greater than 14 days.

A lotto.net `requests` failure or timeout is recoverable: the cycle warns and
continues with committed data, the WCLC archive, and current WCLC results. This is
safe only if the resulting chronology still passes validation.

The following conditions remain fatal by design:

- WCLC archive/current request or parse failure;
- bridge parse/format failure that is not a request exception;
- bridge versus current-WCLC disagreement;
- committed data versus refreshed-source disagreement;
- undersized, duplicated, unordered, or discontinuous chronology.

Do not broaden the fallback to swallow those integrity failures.

## How Codex should continue

1. Read root `AGENTS.md`, `MODEL_PROTOCOL.md`, `V2_V4_RESULTS.md`,
   `RESEARCH_ROADMAP.md`, `ARCHITECTURE.md`, and `OPERATIONS.md` first.
2. Treat `9f16e20c726c7b65eed1d387c4c725d51248f570` and the artifact facts above as
   the last pre-hold `main` boundary.
3. Do not dispatch the expired Stage-1 route. Preserve its history, but use the
   separate reviewed D0 release to restore data/live/backtest and `live.yml` to
   all-false behavior. Preserve the CLI writer interlock. Any later production
   attempt requires a new live registration and independently reviewed exact
   production SHA. V12.0.1's live lane also expired; preserve its fixed dates
   and closure. R3 supplies no replacement live identity.
4. Preserve and independently review the sealed corrected epoch and append-only
   suffix identities above. Do not replace them with worktree CSV bytes or
   caller-supplied metadata.
5. Never rewrite the existing processed history, prediction, evaluation, report,
   or registered evidence artifacts; corrections belong to a new sealed epoch.
6. Preserve artifact commit `b04393944ef12f78417dfb6151343c72d4c2a2ac`
   and evidence commit `60dbd42a502850091508491f9011f9a08acf894f`
   as reachable ancestors; verify the deployed pins from a fresh full-history
   clone of `main` before dispatch approval.
7. Keep the verified-history consumer as the only read path. Preserve registry
   genesis `a6857d6b4e6e532062f484bcce4466f76ba4327b` without squash/rebase. The
   bounded dual-source collector, offline `B -> E -> S -> P` preparer, local bare
   CAS, fixed-repository GitHub publisher, and execution/artifact handoff are
   disconnected review tools, not independent execution paths. Preserve the
   merged orchestration's fixed literal-B, exact-P worker, freeze-A, and P-to-A
   sequence; do not add a standalone worker or caller-injectable
   configuration/clock/adapter path. The prediction-origin fix is satisfied by
   PR #32, and the expired Stage-1 candidate review remains an immutable
   historical fact. Both Stage-1 and V12.0.1 live windows are closed. A new
   live registration must define its own reviewed digest/OID identities,
   canary and reload evidence after D0; historical I3 does not authorize them.
   Scheduling requires a later separate release after that canary succeeds.
8. Preserve V12.0.2's completed scoped independent audit and finish ordinary
   protected-main publication using the existing frozen outputs and receipts;
   consult `research/V12_0_2_HISTORICAL_RESULTS.md`. Preserve artifact commit
   `c9b483f6e89bf73eade28829188fbebe745e28c0` as a reachable ancestor and leave
   all six worker files unchanged. The permanent lease is consumed: never
   rerun, retune, update/delete the lease or regenerate a forecast. Preserve
   V12.0.1's distinct startup-failure closure. After documenting the negative
   result, preregister the next narrow, falsifiable experiment before computing
   its results; planning alone is not a registration or execution authority.
   The broader Goal remains incomplete without an independently audited 6/6.
9. Run `pytest -q` and `ruff check .`; run a network smoke only after source
   access is explicitly authorized, and record positive and negative results.

Use `docs/RESEARCH_ROADMAP.md` as the decision process, not as evidence that any
listed feature family will work.
