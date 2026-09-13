# V13: post-RNG main-set overlap

At the R13 registration checkpoint: **REGISTERED / NOT IMPLEMENTED /
NOT AUTHORIZED / NOT SCORED**. This historical-only version is `v13.0.0`,
experiment `V13_post_rng_main_set_overlap`, seed `649`. Registration freezes
rules; it creates no prediction or permission to execute.

The normative machine contract is the
[R13 seal](../../evidence/research_registrations/v13-post-rng-main-set-overlap-v1.json).
Its `scientific_contract` contains every arithmetic operation, literal oracle,
comparator source pin, statistic, gate and stopping rule. Its
`operational_contract` fixes authority, paths, runtime and failure behavior.
The [research configuration](../../config/research-v13-post-rng-main-set-overlap.yaml)
is canonical JSON with one LF, also valid YAML, and is disconnected from
production. The [mathematical basis](../research/V13_post_rng_main_set_overlap_basis.md)
explains the restriction and its limitations.

Scientific contract SHA-256 (canonical compact sorted JSON plus LF):
`7d86364d43907a64d3eb45f23ebb2fdfc2edf807633748e329cd64e0c8341a37`.
This digest is not a source-code hash. The new pure core first freezes at I13
and must remain identically bound at K_H13, authorization source and merge.
No V12 pure-core hash can represent this new law.

## Hypothesis and fixed evidence scope

Test one signed dependence on how many main labels repeat from the immediately
preceding post-RNG draw. Fair independent draws remain the default. This is a
new restricted law within an already explored transition family, not an
untouched family, independent replication, or demonstrated stronger model.
V2/V3 transitions, V5 previous-main pair affinities, V11 bonus transitions and
V12 parity-composition transitions are disclosed prior exposure.

The governed input is frozen at commit
`4a617f2c1575a165b42878600753a01ddf2ced03`: 4,444 draws through 2026-08-22.
Score the fixed 627 dates from 2020-01-01 through 2025-12-31, with fixed halves
314 through 2022-12-31 and 313 from 2023-01-04. These are **consumed historical
diagnostics**, with no new untouched confirmation. The calendar digests and
all immutable input identities are in `scientific_contract.scope`.
Every 2026 observation is excluded from target scoring and visible prefixes.
There is no V13 live lane or calendar extension.

## Exactly one fitted coefficient

For previous main set A, potential six-number set S and k=|S intersect A|:

```text
N_k = C(6,k) C(43,6-k)
N = [6096454,5775588,1851150,246820,13545,258,1]
Z(beta) = sum_k N_k exp(beta*k)
P_beta(S | A) = exp(beta*|S intersect A|) / Z(beta)
Q(beta) = -beta²/2 + sum_j (beta*k_j - log Z(beta))
U(beta) = -beta + sum_j (k_j - E_beta[k])
```

At each target refit one global beta with a fixed Normal(0,1) prior, using
every chronological adjacent pair whose two dates are at or after 2019-05-15
and whose destination is strictly before that target. No bonus, pre-RNG
candidate inputs, selected lag, window, decay, label coefficient, calibration,
model search or ensemble blend may be introduced.

An empty pair sequence with a valid prior anchor, or exact integer equality
`49*sum(k) == 36*D`, forces canonical positive zero. Otherwise the registered
signed bracket uses `float(6*D+64)` and exactly 256 bisections. The fixed
binary64 program, operation ordering, sign checks, strict finite bounds and
all 13 literal moment/root oracle cases are normative. Assertions printed in
the mathematical specification mean terminal validations in production;
optimization-dependent Python assertions cannot enforce them. Do not execute
documentation as runtime code. There is no numerical rescue, clipping,
renormalization, tolerance exit or solver substitution.

For mean overlap mu and separately summed complementary moment c, every label
inside A has probability mu/6 and every label outside A has probability c/43.
Store all 49 strict (0,1) probabilities and matching hex values, with sum six
within 1e-12. Rank descending probability then ascending categorical label.
Candidate and cyclic-control Final-6 are sorted Top-6. Ties create no
within-group skill; numeric closeness is never a hit.

## Four frozen producers

1. The candidate exact overlap law.
2. One cyclic-anchor control: pi(i)=1+(i mod49) transforms source anchors in
   every training pair and current anchor; destinations stay unchanged. It
   fits its own beta under the same law and is a correlated fair-null sanity
   control, not guaranteed signal destruction or independent replication.
3. The frozen V1 ensemble using its full visible prefix. Its four constituent
   predictors and prescribed logistic/scaler fits execute normally. No inactive
   V2/V3/V4 predict or fit may execute. Build a fresh graph per target.
4. The frozen random comparator with registered date-derived seed.

Comparator source bytes, configuration, default dependencies and original
12-candidate combination selection are pinned in the seal. The fair 6/49
proper-score reference produces no fifth ticket. Existing live flags in
`config.yaml` remain content of the comparator source, never dispatch authority.

## Frozen inference and decision

The sole primary is aggregate mean Top-12 hits minus 72/49. Compute the exact
inclusive upper tail from the integer Hypergeometric(49,12,6) convolution on
each complete fixed scope. Restart NumPy default_rng(649) for each scope and
contrast, with exactly 10,000 whole aligned-row resamples and linear 2.5/97.5
percentiles. These intervals are descriptive; they do not guarantee general
serial-dependence-robust coverage under alternatives.

The fixed family-only Holm vector is
`[1, 1, 0.9783404732169021, 0.5909687963172663, p13]`, ordered V2/V3/V11/V12/V13.
This is not a Goal-global correction. Prior constants have frozen provenance
and cannot be replaced, removed, recomputed or adapted after V13 results.
The supplied V12 value is used only for multiplicity accounting.

All ten gates are mandatory, using unrounded values:

| Gate | Exact rule |
|---|---|
| 1 — aggregate_positive_primary | aggregate candidate Top-12 mean minus 72/49 > 0.0 |
| 2 — aggregate_family_holm | aggregate candidate five-entry Holm-adjusted exact inclusive upper-tail Top-12 p <= 0.05 |
| 3 — aggregate_primary_interval | aggregate candidate Top-12-lift 95% bootstrap lower endpoint > 0.0 |
| 4 — both_half_primary | candidate Top-12 lift > 0.0 in first_half AND second_half |
| 5 — paired_v1_superiority | candidate-minus-V1 per-draw Top-12 difference 95% bootstrap lower endpoint > 0.0 in aggregate AND first_half AND second_half |
| 6 — correlated_controls_conservative_conjunction | In EACH of aggregate, first_half, second_half: candidate-minus-cyclic-control paired Top-12 95% bootstrap lower > 0.0 AND EACH of cyclic-control and random has exact fair Top-12 upper-tail p > 0.05 AND its own Top-12-lift 95% bootstrap lower <= 0.0 <= upper. All clauses mandatory; predictive-looking cyclic control alone is a scientific gate failure, not proof of leakage. |
| 7 — all_scope_top6 | candidate Top-6 mean minus 36/49 > 0.0 in aggregate AND first_half AND second_half |
| 8 — proper_scores | For EACH scope and EACH reference fair,V1: mean aligned per-draw candidate-minus-reference Brier <= 1e-9 AND mean aligned per-draw candidate-minus-reference binary LogLoss <= 1e-9. No rounding or clipping before comparison. |
| 9 — joint_law | candidate aggregate sum(g) >= float.fromhex("0x1.7f7427b73e391p+1") AND candidate sum(g) > 0.0 in EACH half AND sum of aligned candidate-minus-cyclic-control g differences > 0.0 in ALL three scopes AND cyclic-control aggregate sum(g) < that same log(20) literal |
| 10 — zero_audit_warnings | Integer audit_warning_count == 0. Includes chronology, source, target/future, selection history, exact runtime, solver/binary64, probability, ranking, comparator, serialization, authorization, external reviews, startup, lease, ownership, claim, ledger, output, opportunity and required notification failures. Distinct scientific gate failures do not manufacture integrity warnings. |

Complete clean execution failing any scientific gate is Reject. Passing all
gates is `historical_diagnostic_pass_unpromoted`; it establishes neither
confirmation nor future ability. Integrity failure is Archive, and startup
failure without a forecast is unscored, not a scientific Reject. On early
6/6 or failure retain descriptive partial evidence only: no completed-horizon
p-values, Holm result, scope intervals or ten-gate verdict.

Report every target and all four producers, all best-date ties, complete 0..6
Final-6 distributions, Top-6/12/18, actual ranks, Brier, binary Log Loss,
10-bin calibration, joint log gain, fixed halves and all six calendar years.
No year-specific inference or selection is added. The exact statistic and
formatting operations are in `scientific_contract.statistics`.

## Chronology, first 6/6 and notification

For every target, expose only its prior prefix to all four predictors; serialize,
validate and durably freeze their complete 49-number outputs before revealing
the target once. Score those bytes without fitting or predicting again. Preserve
training cutoff, target date, real generation time, input projection/count
digests, beta/moments/logZ state, model/features, runtime and every Git authority.

Deduplicate opportunities by target date and sorted Final-6, retaining every
matching producer and forecast hash. Cross-version repeated V1/random tickets
are not new independent opportunities. Adaptive plug-in fair chance accounting
is nominal bookkeeping, not an anytime p-value or global significance claim.

The first new unique Final-6 6/6 from any frozen producer stops before the next
forecast after retaining the entire current target cohort. Freeze evidence,
perform an independent leakage/chronology/Git/runtime/lease audit, publish the
complete partial report and one candidate bundle. Only after a passing audit
attempt one grouped Chinese notification through the unchanged repository
default SMTP route. Persist the attempt before sending; failed or uncertain
sends are never retried. Top-12 6/6 alone is recorded and execution continues;
it triggers no mail or additional stop. There is no next-draw recommendation.

Only an independently audited historical Final-6 6/6, complete freeze/final
report and successful Chinese notification may complete the broad Goal. No
6/6 leaves that Goal open and requires another separately preregistered narrow
hypothesis before any new outcomes. V13 cannot be retuned or rerun.

## Operational contract

### Registration and noncircular publication

R13 adds exactly five registration/spec/config/test/seal files and modifies exactly
three status documents at base `f247649be2928bfc7cbf5a00c0a400eedadb89f2`. The unique ordinary one-parent status-A
registration source is resolved from immutable Git after it exists. The final
13-key seal embeds science and operation objects with independent C+LF digests,
seven final registered-file entries excluding itself, and a complete ls-tree preservation
manifest with exact mode/type/oid/path metadata for all tracked base entries except
the eight registered R13 paths. It includes all existing modes and reads no history
or report blobs. No future
source/merge/seal digest is inserted into its own inputs. The separate config has
exactly nine metadata/digest fields, with activation=registration_only_no_runtime_wiring;
it does not embed the contracts. R13 itself uses the truthful phase-R13 source-author
trailer, matching seal contributor pairs. Once its ordinary ADD origin exists,
no intervening seal change/deletion/re-add/merge-restore is allowed anywhere in
the reachable lineage, even if later bytes match again.

I13 later adds exactly eight registered paths, including a NEW V13 core and its
tests/fixture. None is created by R13. The new core SHA first freezes at reviewed
I13 and remains equal at K_H13/A_H_s13/M_A_H13, startup, forecast boundaries and
publication. The old V12 core SHA is not a substitute. Closure and implementation
manifest digests use canonical JSON WITHOUT LF; science, operations, preservation
and JSON output documents use canonical JSON WITH exactly one LF. Markdown is a
deterministic UTF8 human rendering with LF line endings, hashed as actual bytes;
it is not serialized as JSON. Scientific
ledger event hashes retain R3 canonical-without-LF hashing excluding event_sha256,
with complete lines written with LF; startup instead hashes the complete LF line.

### Sole historical authority

`R13 < I13 < K_H13 < A_H_s13 < M_A_H13 < L_H13 < run_H13`.
I13 and authorization need fresh exact-source CI and two actual nonauthor agent/session
reviews. One real GitHub publisher may publish both actual reviews; it must not
impersonate them. Source-author trailers bind complete contributors to exact Git
messages before CI/reviews. The inherited counts were 23 authorization and 12 review
comment keys: V13 explicitly adds `operational_contract_sha256` to each, yielding
closed 24/8/13 auth/record/comment schemas. No claim that R3 already had those counts
is made.

Only ordinary protected-main authorization merge M_A_H13 with exact first/second
parents and source-equal tree authorizes the clean fullclone at the same current
remote main. Source authorization alone is inert. Runtime is exact CPython3.12.11,
27 frozen distributions, source/static closure, libm oracles and unchanged pinned
requirements. No live/CLI/workflow/scheduler activation is created.

### One attempt and auditable startup

After complete read-only authorization yields inert integrity-bound facts, exclusively
create the 0600 startup file, bind complete verified identities, fsync file and parent,
and only then issue a capability. Strict13phase full-line-LF hash-chain receipts
record intent before each of the at-most-one commit POST and one createRef POST.
Only an exact fresh literal remote404 grants absence. Raw commit message and POST
message are C+LF; the mandatory GET projection is C without LF. Every SHA, tree,
parent, identity, time, unsigned-verification and nested key set is fixed. POST
message text supplies no identity proof. No response-dependent schema relaxation,
retry, resume, lease update/delete/adoption or later404 revival is allowed.

Checkpoint sequence9 precedes immutable claim and first scientific ledger event.
The claim binds the fsynced prefix, then startup records claim/firstledger/history
intent and seals at sequence12 before history loading. Final manifest separately
binds both earlier checkpoint and complete sealed startup, avoiding circular hashes.
Owned current-attempt files remain recognizable through retained identity; a path
allowlist alone never permits foreign artifacts. All partial evidence survives.

All four forecasts are durably frozen before target reveal; only frozen bytes are
scored. The final worker artifact commit adds exactly six files with sole parent
M_A_H13, keeping ordinary ancestry. It performs no remote artifact publication.

### Capture, independent audit and notification

A first Final6 exact6 freezes the whole current cohort and stops before another
forecast. The worker closes with only its six normal artifact files. Additional
candidate bundle, independent audit JSON/Markdown and separate notification
intent/journal/result paths are fully named in the contract; no such action is required
before the independent audit concludes. The capture bundle binds the immutable
worker artifact and completed audit, with no future self-commit dependency.

Only a passing independent audit plus ordinary immutable publication permits the
separate notification claim procedure. Local O_EXCL alone is insufficient across
clones. The fixed remote ref `refs/heads/v13-notification-v13.0.0` is distinct from
the historical consumption lease. Concurrent clones may both see404 and upload
commits; only one atomic createRef can win. Only that invocation, with exact own201,
mandatory fixed commit GET, fresh exact ref reread, unchanged main and retained
nontransferable local capability, may call the default sender once. A present ref
or another process's identical-looking marker never grants authority.

The claim binds a closed notification identity digest. The complete local intent
then binds expected raw commit/OID and both exact request digests; a separate nine-
phase journal binds that complete intent and records each durable pre-POST and
pre-SMTP intent. This order is acyclic. Failure or ambiguity permanently poisons
the invocation; a winner crash or failed/unknown send never releases the global
claim or permits takeover. The guarantee is global at-most-one authorized SMTP
call, not global at-most-one commit POST. It assumes the trusted fixed service's
atomic createRef and the permanent prohibition on deleting/updating the ref.
A result is a separate immutable file bound to the sealed journal. No new
historical command, worker retry, lease reuse or automatic activation is added.
Top12 alone records and continues, with no email or mail-failure stop. Existing
committed-state hourly reporting remains separate and never duplicates an attempted
hour. Registration and review must not read or display Secrets.

### Required verification and prior accounting

Required future synthetic cases explicitly cover two fresh clones/one winner,
exact404, present/mismatched/uncertain claims, losing/ref-adopting callers, winner
failure before SMTP, all SMTP outcomes and no historical worker/lease reuse.

Prior family accounting uses only fixed Git tree/object metadata during V13
preauthorization: exact existing commit/path/mode/type/blob/size pins. It relies
transparently on the already completed independently audited V12 identity/value/
metric evidence archived at the pinned baseline. It does not reopen old report,
audit-result or target payloads, run prior replay code, recompute SHA256 from those
payloads or extract p12 again. Missing or incompatible metadata blocks, with no
replacement, rerun or fixed-family-vector alteration. The p12 and p11 literals
remain exactly the frozen scientific contract's accounting constants.

### Sources and source review

The machine contract pins each inherited operational source by immutable commit,
path, byte count, hash and exact section. Only these explicit operational clauses
are inherited; no H12 mathematics or old execution authority applies. The V13
object records its author and the registration seal records all contributors.
An author cannot independently review this completed source.

This registration specifies required behavior. It does not prove that a future
implementation, historical run, captured result, independent audit or notification
exists. I13 and its authorization need their own complete tests and independent
source reviews before the sole historical run.


Operational contract SHA-256 (canonical compact sorted JSON plus LF):
`69f5eb033a678bf42fe6aeb49ece451934c413a0e4fcd5bc8e1d5e27cb06f382`.
