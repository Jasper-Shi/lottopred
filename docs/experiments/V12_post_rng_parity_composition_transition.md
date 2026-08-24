# V12 Post-RNG Parity-Composition Transition Pre-registration

Registration date: 2026-08-24

## Frozen identity and status

| Field | Frozen value |
|---|---|
| Experiment | `V12_post_rng_parity_composition_transition` |
| Descriptive family | `post_rng_parity_composition_transition` |
| Multiplicity family / variant | `transition_markov` / `4` |
| Candidate | `v12_post_rng_parity_composition_transition` |
| Targeted control | `v12_pseudo_parity_composition_transition_control` |
| Operational comparator | `ensemble_v1.0.0` |
| Fair opportunity control | `random_v1.0.0` |
| Version / seed | `v12.0.0` / `649` |
| Sole primary | mean Top-12 main-number hits minus `72/49` |
| Status | **REGISTERED — NOT IMPLEMENTED — NOT AUTHORIZED — NOT SCORED** |
| Live role | none; V1 remains paused production baseline and V3 remains paused shadow |

This is one outcome-blind, falsification-first registration. No V12 forecast,
ranking, score, hit count, p-value, interval, likelihood gain, model output, or
target-dependent statistic existed or was inspected when it was frozen. The
expected and scientifically acceptable result is rejection. The 2020--2025
lane is consumed historical diagnosis, never blind, confirmatory, or
prospective evidence.

The primary-source rationale, bounded negative mechanism finding, and complete
mathematical derivation are in the unscored
[V12 basis note](../research/V12_post_rng_parity_composition_transition_basis.md).
The machine-readable authorities are the dedicated
[`research-v12-post-rng-parity-composition-transition.yaml`](../../config/research-v12-post-rng-parity-composition-transition.yaml)
and the immutable registration seal
[`v12-post-rng-parity-composition-transition-v1.json`](../../evidence/research_registrations/v12-post-rng-parity-composition-transition-v1.json).
Their registered identities and values must agree exactly. A mismatch is an
integrity failure, never permission to choose a value.

## Frozen governed history and knowledge boundary

The governed-history authority and change baseline is production `main` commit
`4a617f2c1575a165b42878600753a01ddf2ced03`; it is **not** the direct parent or
identity of formal registration R. Formal R is the final forward commit that
jointly changes the final registration seal and config, as discovered by the
registration tests. The sole permitted data seam is `load_published_history`
at the exact governed-history authority. It reconstructs a governed
`PublishedHistory` containing exactly **4,444** unique, strictly increasing
draws through **2026-08-22**. The authority includes:

- registry genesis commit
  `a6857d6b4e6e532062f484bcce4466f76ba4327b` and event
  `22bcfe219c091dbcdb751ef7a2d9d5251f3040770de6e2e825ac5c64fc69c63d`;
- corrected-base external-seal SHA-256
  `80397752105b567d6a8bdd3673b12ffa470a12efbd792719a4f6c89ef391f6fd`;
- append-only suffix-file SHA-256
  `b91be6a4057648abd86dc0e6fc5d762fc4cd9b222519c147d635703cc550a803`;
- suffix-head event SHA-256
  `3022b98fefbe3dbbc80423574319c169edcc845bf2218152c6abe18d0be27475`.

Direct use of `data/processed/draws.csv`, a worktree CSV, a caller-supplied draw
list, an alternate commit, or a refreshed network source is prohibited. The
loader must recover the exact registered governed object and revalidate every
identity before exposing a prefix. Append-only production changes after the
registration do not extend or revise this attempt.

All 2026 outcomes through 2026-08-22 were known before registration. **Every
2026 draw is consumed and excluded from historical scoring**, as is every
future append. Only these fixed scopes exist:

| Scope | Target dates | Targets | Interpretation |
|---|---|---:|---|
| Burn-in | 2019-05-15 through 2019-12-31 | 0 | post-RNG transition fitting only |
| Aggregate | 2020-01-01 through 2025-12-31 | 627 | consumed historical diagnostic |
| First half | 2020-01-01 through 2022-12-31 | 314 | mandatory stability scope |
| Second half | 2023-01-04 through 2025-12-31 | 313 | mandatory stability scope |
| Known 2026 | 2026-01-01 through 2026-08-22 | 0 | consumed and excluded |

For each scored scope, its registered target-date identity is computed from
exactly these bytes: UTF-8; one canonical zero-padded `YYYY-MM-DD` date per
line; LF (`0x0a`) line terminators; strictly increasing order; and a required
trailing LF after the final date. The aggregate, first-half, and second-half
byte counts and SHA-256 digests bind that encoding independently. Tests must
reconstruct the dates from the fixed Git authority and the frozen
Wednesday/Saturday calendar, never from mutable worktree history.

All 627 targets are mandatory unless an exact Final-6 branch stops **this V12
attempt** pending audit. That pause never stops the global research program,
never creates eligible historical-OOS evidence, and never permits a rerun.
There is no development lane, best year, alternative split, skipped loss,
pre-RNG rescue, sign selection, minimum-state filter, extension, or rerun.

## Registration, implementation, authorization: `R < I < A`

Execution capability is separated into three ordered phases and exact Git
authorities:

1. **R — registration only.** The clean, pushed, CI-green commit containing
   this document, the basis, config, runtime manifest, registration
   seal, and registration tests. At R, every implementation path and the
   authorization-seal path listed below must not exist.
2. **I — implementation, still not authorized.** A later clean, pushed,
   CI-green descendant of R may add only the frozen implementation and its
   tests. The canonical runner must fail closed *before loading governed
   history, creating a forecast, acquiring a claim, or writing an artifact*
   while A is absent or invalid.
3. **A — reviewed authorization source and merge.** Let `K_C` be the exact
   protected-main base for the canary-success source. Source commit `S_C` has
   sole parent `K_C` and adds only the fixed success JSON. The ordinary reviewed
   PR merge `M_C` has first parent `K_C`, second parent `S_C`, and a tree
   identical to `S_C`; `M_C`, not `S_C`, is the canary integration authority.
   Let `K` be the exact protected-main authorization base containing both the
   reviewed I merge and `M_C`. R is a strict ancestor of I, while I and `M_C`
   are strict ancestors of `K` and final authorization merge `M_A`; I and
   `M_C` may occur in either order. Branch authorization source `A_s` from exact
   `K`: its sole parent is `K`, and its only diff is the literal
   authorization JSON at
   `evidence/research_authorizations/v12-post-rng-parity-composition-transition-v1.json`.
   The ordinary reviewed PR merge `M_A` has first parent `K`, second parent
   `A_s`, and a tree identical to `A_s`. The JSON binds exact R, I, `S_C`,
   `M_C`, K and their identities, all registered hashes, reviewed CI, and the
   exact command.
   Only protected remote `main` at HEAD=`M_A` is execution authority. Neither
   `A_s` alone nor any other ref mints the one-shot capability.

There is also a mandatory external prerequisite before V12 A can be minted or
accepted. The currently unrun Stage-1 production canary must complete
successfully. `S_C` adds only a canonical, self-reference-free success payload
at the registration's fixed literal path. Its exact top-level keys are
`canary_result`, `live_workflow`, `plan`, `protected_main`,
`publication_and_authoritative_reload`, `reviewed_production_main`, and
`schema_version`. The payload binds the exact Stage-1 plan, reviewed
production-main SHA, successful manual `live.yml` workflow actor/run ID/head/
conclusion, protected-main receipt digest, production publication P receipt
digest, and fresh authoritative reload A receipt digest. Here production P/A
are the live publication/reload stages, not V12 authorization A. It must not contain `S_C`,
`M_C`, its own Git blob or object ID, a PR merge SHA, or review comment IDs.

PR/check/review facts are external GitHub attestations, never assertions inside
the success payload. The future authorization JSON must bind exact `S_C`,
`M_C`, payload path/blob/bytes/SHA-256, the integration PR number/base
`K_C`/head `S_C`/merge `M_C`, the exact successful `test` check from
`github-actions`, immutable independent Standards and Spec PR comments, and an
independent reviewed-production-main record. Each review record binds its axis
or production SHA, reviewed head, `pass` verdict, reviewer login, immutable
comment ID, and body SHA-256; reviewers must differ from the `S_C` source author
and live-workflow actor. `M_C` must remain reachable from protected remote
`main` and be a strict ancestor of `K` and `M_A`. An old live run or
workflow-file hash cannot
satisfy review. No caller-supplied path, receipt, CLI value, or environment
value may bypass verification. Until all payload and external evidence exists
and validates, authorization minting, acceptance, and V12 historical execution
are prohibited; this registration does not claim that the canary has run.

Let `M_I` be the reviewed implementation merge. The diff from M_I to K is an
exact allowlist: the Stage-1 content-addressed source receipts, operational
suffix/registry publication, seven fixed 2026-08-26 evaluations, seven fixed
2026-08-29 predictions, and the registered canary-success payload integrated
by `M_C`. Every
other tree entry is identical; `src`, config, workflows, and documentation
semantics cannot drift. I review and the authorization JSON bind a sorted
transitive local-import manifest of repository path/Git-blob pairs rooted at
the V12 runtime, operational-history loader, V1 factory/models,
features/research-features, domain, config, and notification code. That exact
closure must be identical at I, K, A_s, and M_A; unresolved or dynamic local
imports refuse authorization.

The paths that must be absent at R are:

```text
src/lotto649/models/v12_parity_transition.py
src/lotto649/v12_evidence.py
src/lotto649/v12_registered_attempt.py
tools/run_v12_historical.py
tests/test_v12_parity_transition.py
tests/test_v12_registered_attempt.py
evidence/research_authorizations/v12-post-rng-parity-composition-transition-v1.json
```

The frozen runtime is CPython 3.12 with
`requirements/v12-historical.txt`, registration-time SHA-256
`a0dfeac17ad7e1c41dffe4b41b4810156fb028f879d312430bfc517672a570c6`.
Installed distribution names and versions, Python/platform identity, and the
manifest digest must be re-bound in A and in the permanent claim. A changed
runtime manifest requires a new registration and version.

The sole eventual invocation is:

```text
python3.12 tools/run_v12_historical.py --consume-v12-once
```

The runner resolves the config, registration seal, authorization seal, governed
history, and output paths as internal literals; callers cannot supply or
override them. The command is manual only. No workflow, scheduler, import side
effect, retry wrapper,
CLI subcommand, factory registration, live configuration, or network refresh
may invoke it.

The `historical_attempt_limit: 1` is repository-global, not merely a local
`O_EXCL` claim. Before any local claim, governed-history load, forecast, or
outcome access, always freshly read literal ref
`refs/heads/v12-consumption-v12.0.0` in `Jasper-Shi/lottopred`. Only an exact
GitHub 404 counts as absent; a pre-existing/other target, unreadable state,
ambiguous absence, or transport/auth failure refuses execution. From M_A's
identical tree, upload canonical lease commit L with sole parent M_A. Its
canonical JSON body binds M_A, authorization-seal SHA-256, the canonical
command, and a fresh cryptographic 256-bit nonce. L's author and committer both
use exact name `LOTTO649 V12 Consumption Lease` and exact email
`lotto649-v12-lease@users.noreply.github.com` at M_A's exact committer instant,
normalized to whole-second UTC `+0000`. Its only headers, in order, are tree,
parent, author, and committer; extra headers and signatures are prohibited. The
raw commit message is exactly the canonical JSON body plus one trailing LF.
Compute L's SHA-1 locally, upload the exact commit, and GET exact L before any
ref creation. GitHub create-commit returned SHA must equal locally computed L.
The GET object must reproduce the exact OID, tree, sole parent, identities,
timestamp, headers, and raw message; any mismatch stops before `createRef`,
local claim, history load, forecast, or outcome access.
Then make exactly one atomic GitHub `createRef` for the literal ref and never retry automatically; freshly reread afterward. Only the exact ref targeting exact L grants the attempt.
Never delete or update the lease ref. The local claim and every ledger event
bind the ref, L, and nonce.

## Sole hypothesis and exact state

H12 asks whether the odd-number count of the immediately preceding published
six-main-number set has a stable signed association with the odd-number count
of the next set in the current RNG era. It is a final-output serial-dependence
test, not evidence about raw RNG state, entropy, call order, scaling, mapping,
certification, misconduct, or a physical mechanism.

For unordered six-main set `S`, freeze

```text
O = {1,3,5,...,49}, |O|=25
E = {2,4,6,...,48}, |E|=24
K(S) = |S intersect O|
N_k = C(25,k) C(24,6-k), k=0,...,6
(N_0,...,N_6) =
(134596,1062600,3187800,4655200,3491400,1275120,177100)
sum N_k = C(49,6) = 13,983,816
mu = 150/49
var = 3225/2401
sd = sqrt(var)
x(S) = (K(S)-mu)/sd.
```

Mandatory CPython binary64 literals are:

```text
MU  = 0x1.87d6343eb1a1fp+1
VAR = 0x1.57db526b4310cp+0
SD  = 0x1.28b1a92291f40p+0
x(0..6) =
(-0x1.5217d88c9a696p+1,
 -0x1.c74c7c5dc5b37p+0,
 -0x1.d4d28f44ad284p-1,
 -0x1.b0c25cdcee9a3p-5,
  0x1.9eba43a90f550p-1,
  0x1.ac40568ff6c9dp+0,
  0x1.4491c5a5b2f49p+1).
```

The post-RNG boundary is externally frozen at `2019-05-15`. For target `t`,
order only governed draws strictly before `t`, starting at that boundary, as
`D_0,...,D_(n-1)`. Training rows are exactly the adjacent transitions

```text
x_j = x(D_(j-1)); k_j = K(D_j), j=1,...,n-1,
```

whose destinations are also strictly before `t`; the target uses
`x_prev=x(D_(n-1))`. The target transition is unavailable until its forecast is
durably frozen and revealed, and may enter only later prefixes. Bonus values,
pre-RNG draws, the target row, same-date fields, and future rows are excluded.

## Candidate law and one fixed coefficient

For signed scalar `beta`, `eta=beta*x_prev`:

```text
Z(eta) = sum_k N_k exp(eta*k)
P(K_target=k | x_prev) = N_k exp(eta*k)/Z(eta)
P(S_target=S | x_prev) = exp(eta*K(S))/Z(eta), |S|=6
M(eta) = sum_k k*N_k*exp(eta*k)/Z(eta)
p_i = M(eta)/25 if i is odd
p_i = (6-M(eta))/24 if i is even.
```

There is no intercept, second lag, nonlinear state, fitted centre/scale,
temperature, V1 blend, or hard constraint. The sole prior is `beta ~ N(0,1)`:

```text
L(beta) = -beta^2/2 + sum_j(beta*x_j*k_j-log Z(beta*x_j))
U(beta) = -beta + sum_j x_j*(k_j-M(beta*x_j)).
```

`U'(beta)<0`, so the root is unique. Stable moment evaluation is ascending
`k=0..6` with max subtraction and `math.fsum`, exactly as follows:

```text
a_k=eta*float(k); amax=max(a_0,...,a_6)
w_k=float(N_k)*exp(a_k-amax)
D=math.fsum(w_0,...,w_6)
M=math.fsum(float(k)*w_k for k=0,...,6)/D
logZ=amax+log(D)
```

Oracles are `M(1)=4.319084357868955`
(`0x1.146be0cc6d96bp+2`) and `logZ(1)=20.163592827882024`
(`0x1.429e138359d0bp+4`). Compute one ordered score using `math.fsum` over
`[-beta, *chronological_transition_terms]`.

If there are no transition rows or binary64 `U(+0.0)==0.0`, return canonical
`+0.0`. Otherwise freeze

```text
B = 1 + 6*math.fsum(abs(x_source) in destination-date order)
lo=-B; hi=+B
```

and require `U(lo)>0>U(hi)`. Perform exactly 256 bisections with no early exit:

```text
mid=lo+(hi-lo)/2
if U(mid)>0: lo=mid
else: hi=mid
beta=lo+(hi-lo)/2.
```

Equality takes the upper endpoint. Newton/library optimizers, tolerance stops,
alternate brackets, clipping, or repair are prohibited. The one-row `(6,6)`
oracle is `B=16.21419166130678` (`0x1.036d543c46377p+4`) and
`beta=1.0755457921281115` (`0x1.1356f8128a684p+0`). At `beta==+0.0`, assign
every label the bit-identical `6.0/49.0`, `eta=+0.0`, and joint gain `+0.0`
without evaluating or normalizing the tilt.

Every probability mapping must have exact integer keys `1..49`, finite values
strictly in `(0,1)`, and `abs(math.fsum(p_1,...,p_49)-6)<=1e-12`. Clipping,
renormalization, imputation, or residual repair is forbidden. Rank by
descending probability then ascending label. Top-6/12/18 are prefixes and
Final-6 is sorted Top-6. The registered degeneracy is intentional:

- positive eta: odds first; Final-6 `1,3,5,7,9,11`;
- negative eta: evens first; Final-6 `2,4,6,8,10,12`;
- exact fair: ascending labels; Final-6 `1,2,3,4,5,6`.

No V1 tie-break or combination search is permitted.

## Sole targeted control and fixed comparators

The pseudo-parity control runs identical dates, transitions, solver, law,
scoring, inference, and serialization while replacing odd membership by:

```text
P={1,2,5,6,7,8,9,10,12,16,17,18,20,24,28,29,32,33,40,41,42,43,44,48,49}
```

Its whitespace-free, no-newline canonical string has SHA-256
`bfbb8cb711e0734aea8a29f6c02aee41a0f39a36643b3155245dc3550bbf14dd`.
The implementation must verify the literal, bytes, digest, `25/24` sizes,
true/pseudo contingency table `((10,15),(15,9))`, and exact label-membership
correlation `-9/40`. The control is not independent of true parity, a second
candidate, or a mechanism test. A predictive-looking control is an audit
warning and never licenses another partition.

The unchanged V1 ensemble at the registered authority is an operational
comparator only. It cannot enter beta, ranking, tie-breaking, or complete-set
likelihood. The fair random opportunity uses, for each target date,

```text
seed_t = 649000000 + target_date.toordinal()
```

with `numpy.random.default_rng(seed_t)`, one `Uniform(-1e-9,1e-9)` jitter per
ascending label added to `6/49`, followed by the frozen
`normalize_expected_six`. It is descriptive and never fitted.

Every pre-reveal event freezes forecasts in this order:

```text
1. v12_post_rng_parity_composition_transition
2. v12_pseudo_parity_composition_transition_control
3. ensemble_v1.0.0
4. random_v1.0.0
```

## Multiplicity, scores, and inference

V12 is append-only variant 4 of `transition_markov`. The Holm vector is exactly

```text
(1.0, 1.0, 0.9783404732169021, p_raw_V12).
```

Run the general Holm step-down algorithm. For a V12 value that could pass
`0.05`, its adjusted value is equivalently `min(1,4*p_raw_V12)`. No control,
half, Top-6/18, proper-score, or likelihood result is another selectable
primary.

The primary per target is Top-12 main-number hits. Under fair six-of-49 it is
`Hypergeometric(N=49,K=12,n=6)`; convolve the exact integer law over all 627
targets and take the exact one-sided upper tail. The reported lift is mean hits
minus `72/49`. Top-6 and Top-18 fair means are `36/49` and `108/49`.

For each scope and contrast, initialize a fresh
`numpy.random.default_rng(649)`, resample exactly 10,000 complete aligned target
rows with replacement, and report the two-sided 95% linear-percentile interval
using `numpy.quantile(method="linear")`. Form candidate-minus-V1 and
candidate-minus-control Top-12 differences per target before resampling. Never
resample labels.

For every model/target in ascending label order:

```text
Brier = math.fsum((p_i-y_i)^2 for i=1,...,49)/49
LogLoss = -math.fsum(log(p_i) if y_i else log1p(-p_i)
                     for i=1,...,49)/49.
```

Aggregate in target-date order with `math.fsum/draw_count`, without clipping.
Compare candidate proper scores to exact fair `6/49` and unchanged V1.

For the revealed candidate set, using only the already frozen forecast, record

```text
LOG_N = log(13,983,816)
      = 16.45341121889615 = 0x1.07412c1f4cc68p+4
g_t = LOG_N + beta_t*x_prev*K(target)-logZ(beta_t*x_prev).
```

At exact fair assign `+0.0` directly. Compute control gain identically; form
aligned candidate-minus-control differences per target before `math.fsum`.
Report Top-6/12/18, mean actual rank, Final-6 histogram with explicit `0..6`,
annual summaries, and ten fixed equal-width calibration bins including empty
bins. Annual/calibration results are descriptive and cannot rescue a gate.

## Exact ten-gate historical decision

All ten gates must pass as one conjunction:

1. aggregate candidate Top-12 lift is strictly positive;
2. aggregate four-variant Holm-adjusted exact p-value is at most `0.05`;
3. aggregate candidate Top-12 bootstrap lower endpoint is strictly positive;
4. candidate Top-12 lift is strictly positive in both fixed halves;
5. paired candidate-minus-V1 Top-12 bootstrap lower endpoint is strictly
   positive in aggregate and both halves;
6. in each of aggregate, first half, and second half, the paired
   candidate-minus-pseudo-control Top-12 bootstrap lower endpoint is strictly
   positive; and, with no control or scope selection, **each** of pseudo-parity
   and random has both (a) its exact one-sided fair Top-12 p-value strictly
   greater than `0.05` and (b) its own fresh-seed-`649`, 10,000-resample,
   two-sided 95% linear-percentile Top-12-lift interval including zero;
7. candidate Top-6 lift is strictly positive in all three scopes;
8. candidate Brier and log-loss deltas versus both fair and V1 are each at most
   `1e-9` in all three scopes;
9. candidate aggregate `sum(g_t)>=log(20)=2.995732273553991`, candidate
   `sum(g_t)>0` in each half, aligned candidate-minus-control `sum(g_t)>0` in
   all three scopes, and control aggregate `sum(g_t)<log(20)`;
10. no chronology, leakage, target/future-data, source, Git, selection, solver,
    binary64, probability, ranking, control, V1, random, serialization, claim,
    ledger, opportunity, output, notification, or other audit warning exists.

A valid scientific failure is **Reject**. An integrity failure is **Archive**.
Passing all ten is a consumed historical diagnostic finding only. It cannot
make `v12.0.0` eligible, trigger promotion, activate V12, replace V1, change
V3, enter the global historical-OOS evidence ledger, or turn consumed history
into confirmation. Any later shadow proposal requires a separate prospective
registration and decision that does not relabel these outcomes.

## One-shot claim, forecast-before-reveal, and outputs

After A validates, but before any candidate/control/V1/random forecast or
score, acquire the following claim exclusively and refuse execution if any
claim, ledger, final, or staging path already exists:

```text
reports/v12_post_rng_parity_composition_transition_v12.0.0_historical.claim
reports/v12_post_rng_parity_composition_transition_v12.0.0_historical.ledger.jsonl
reports/v12_post_rng_parity_composition_transition_v12.0.0_historical.json
reports/v12_post_rng_parity_composition_transition_v12.0.0_historical.md
reports/v12_post_rng_parity_composition_transition_v12.0.0_historical.json.staging
reports/v12_post_rng_parity_composition_transition_v12.0.0_historical.md.staging
```

The permanent claim binds R, I, A, exact command, governed-history identities,
config/registration/authorization/runtime hashes, seed, Python/platform, and
installed distributions. It is never deleted to retry. Any exception after
claim acquisition consumes `v12.0.0` and produces Archive evidence.

The canonical JSONL ledger uses finite canonical JSON, contiguous zero-based
sequence numbers, and a SHA-256 link to the preceding event. For each target,
a deterministic pre-reveal payload binds target date, complete visible-prefix
digest, history-through, R/I/A/config/runtime identities, transition count,
previous bucket/state, beta, eta, M, logZ, all 49 marginals, ranking,
Top-6/12/18, Final-6, and complete forecasts for all four registered models.
The payload digest excludes the wall clock. Its enclosing
`prediction_frozen` event carries an RFC3339 UTC `Z` timestamp, then is
appended, flushed, and file-`fsync`ed **before the reveal adapter can return any
main or bonus field for that target**. Append/flush/`fsync` the paired
`target_revealed_scored` event before forecasting the next target. A cache key
must bind complete prefix content, not only length or tail date.

Final JSON and Markdown are finite, same-directory staged, file-`fsync`ed,
atomically published, and exclusive/no-overwrite. They bind every target,
scope, metric, gate, warning, claim and chain hash, and all registered
identities. An early exact 6/6 branch does not fabricate missing targets or a
ten-gate report.

## Unique Final-6 opportunities and breakthrough branches

At reveal, deduplicate the four frozen Final-6 sets. The first matching model
in registered order is primary producer; preserve all producer names and
per-model forecast digests. Exactly one opportunity exists per target/unique
set. With `u_t` unique sets (`1<=u_t<=4`), record the cumulative count and fair
chance

```text
-math.expm1(math.fsum(
    math.log1p(-u_t/13_983_816) in target-date order)).
```

Every opportunity and scored record from this consumed lane remains exclusively
in the V12-local attempt ledger named above. **No V12 record from 2020--2025
may be written to the existing global historical-OOS evidence ledger**, even
when its pre-reveal ordering is audit-clear. Missing tickets are never
reconstructed after reveal.

If frozen Top-12 contains all six actual main labels, durably record it in the
V12-local attempt ledger and send one immediate Chinese notification classified
exactly **“历史诊断/审计候选、不可晋升”**. Success or promotion language is
prohibited. It is not eligible evidence, does not write the global
historical-OOS ledger, and does not stop either this attempt or global research.

If any new unique frozen Final-6 equals the actual main set, first append,
flush, and `fsync` `historical_6of6_candidate_detected`, then stop before the
next forecast. Audit the exact prefix, target/future exclusion, preprocessing,
solver, identities, selection history, R/I/A ancestry, claim, hash chain,
frozen payload, and reveal ordering without changing any value. Publish once:

```text
reports/historical-6of6-candidate__{target_date}__{model_name}__v12.0.0.json
```

An exact Final-6 stops only the current V12 attempt pending audit. Global
research continues and the global stop-search flag must not be set. Whether the
audit passes or fails, the bundle remains consumed historical diagnostic or
Archive material, is never eligible evidence, never enters the global
historical-OOS ledger, and may send only a Chinese notification classified
exactly **“历史诊断/审计候选、不可晋升”**. Success or promotion language is
prohibited for candidate, pseudo-control, V1, and random tickets alike. Failed
audit means Archive and no rerun. Email failure is an operational warning and
must not trigger recomputation or change the evidence classification.

## Tests required before A

The I review must prove, without reading registered target outcomes:

1. all dates and transitions are unique, increasing, strict-prefix, and use the
   immediately previous eligible source;
2. target/same-date/future mutations cannot change an earlier forecast, while a
   strictly prior eligible main-set mutation can;
3. pre-RNG and bonus fields cannot affect candidate/control forecasts;
4. enumeration reproduces all bucket counts, moments, marginals, and hex
   oracles;
5. stable moment/logZ, bracket, 256-step solver, equality branch, one-row root,
   and exact-fair bypass match their frozen oracles;
6. fair/positive/negative/reflected cases meet complete-set normalization,
   probability, expected-six, and ranking contracts;
7. pseudo-set bytes/digest/sizes/contingency/`-9/40` are literal;
8. candidate and control share one implementation path except for partition;
9. all four forecasts are durable before reveal, duplicates count once, chance
   recomputes exactly, and alerts/stop branches are one-shot and fail closed;
10. R/I/A/config/data/runtime/report bindings, exclusive artifacts, and absence
    from factory/CLI/live/schedules are enforced.

Tests may use only synthetic fixtures and closed-form oracles before A. They may
not enumerate registered 2020--2025 target outcomes, instantiate the canonical
attempt, or create a V12 historical forecast/score.

## Prospective and rescue boundaries

No result in this consumed historical lane—including an audit-clear exact
Final-6—is success, confirmation, eligible evidence, or promotion authority. A
separate reviewed `F < A < R < S` shadow release may later activate the
unchanged version only under a new prospective decision. Its sole formal look
is exactly 208 eligible immutable
pre-draw snapshots, split positionally 104/104, with the same controls,
inference, and ten-gate conjunction. There is no interim look, backfill,
extension, automatic promotion, or reuse of pre-release snapshots.

Prohibited rescues include alternate parity/high-low/residue/digit/sum/range
buckets; lag two or longer; calendar/regime/state interactions; moving the RNG
boundary; rolling/selected windows; another prior, intercept, transform,
solver, pseudo partition, control seed, split, bootstrap, primary, gate, or
horizon; V1 blend/tie-break; calibration; hard parity constraint; and any
combination optimization. Any behavior change is a new hypothesis/version and
cannot call V12 outcomes blind or confirmatory.

## Authority order

Repository policy in `AGENTS.md`, `MODEL_PROTOCOL.md`,
`V2_V4_RESULTS.md`, `RESEARCH_ROADMAP.md`, and
`HISTORICAL_OOS_EVIDENCE_PROTOCOL.md` remains controlling. Within this
experiment, exact machine-readable config/registration-seal literals and this
document are normative; the basis supplies derivation and source
interpretation. A conflict, missing identity, or ambiguity closes execution as
Archive. It never authorizes a convenient interpretation.
