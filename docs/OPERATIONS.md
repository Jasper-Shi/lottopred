# Operations Guide

## Cloud execution

No local computer needs to stay running.

- **Codex Cloud**: development, code changes, debugging and research.
- **GitHub Actions**: recurring production-like execution.

## Data-integrity incident kill switch

The 2026-08-20 registered-history reconciliation suspends source refresh, live
execution, and historical backtesting. The registered 4,434-row history through
2026-08-22 is not strict real-calendar evidence. A reviewed candidate now seals
the correction, but sealing evidence does not authorize execution. The
committed incident state remains:

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
not work around a disabled command by calling a lower-level function. The direct
`run_backtest` boundary and both public `refresh_with_sources` implementations
repeat their respective checks before model construction, report writes, or
source access. Public live refresh, evaluation, generation, and cycle boundaries
require both live and data-refresh approval before their data loads, filesystem
access, evaluations, or prediction snapshots. Changing only `live.enabled`
cannot resume production.

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
side effect. The guard writes its all-false outputs before attempting the hash;
a missing or unreadable `config.yaml` emits a warning and exits successfully in
the same sealed state.

Re-enable a boundary only in a separate reviewed release after all applicable
items below are true:

The corrected-history evidence available to that release is pinned as follows:

```text
base: 4,442 draws through 2026-08-15
verified suffix: 2 draws through 2026-08-22
verified view: 4,444 draws
seal SHA-256: 80397752105b567d6a8bdd3673b12ffa470a12efbd792719a4f6c89ef391f6fd
suffix SHA-256: b91be6a4057648abd86dc0e6fc5d762fc4cd9b222519c147d635703cc550a803
suffix head SHA-256: 3022b98fefbe3dbbc80423574319c169edcc845bf2218152c6abe18d0be27475
registry genesis commit: a6857d6b4e6e532062f484bcce4466f76ba4327b
registry genesis blob: e95aeaaa28d5c1b7e5fb636d0fc4a3c26ff31017
registry genesis event: 22bcfe219c091dbcdb751ef7a2d9d5251f3040770de6e2e825ac5c64fc69c63d
```

The base is bound to artifact commit
`b04393944ef12f78417dfb6151343c72d4c2a2ac`; the two raw-source receipts are
bound to evidence commit `60dbd42a502850091508491f9011f9a08acf894f`.
The operational-history read seam fixes the registry genesis in source, resolves
the selected revision once, and reads the registry, seal, suffix, and evidence
only from immutable Git blobs. Worktree replacements and caller-provided pin
overrides are not authority. The direct backtest boundary consumes this single
read seam after its runtime gate.

Official-source collection, offline preparation, local CAS, the fixed-repository
remote exact-CAS publisher, and the isolated execution/artifact handoff are
implemented as disconnected review/test seams. The network collector retrieves
exact bounded WCLC and Loto-Québec HTML without writing Git or operational
state. The preparation seam takes those two assets, creates an
unattached `B -> E -> S -> P` candidate without changing worktree/index/refs,
and validates `P` through the production reader. The local adapter can advance
only a self-contained bare repository whose literal `HEAD` is `main`; it always
rereads authority after a CAS attempt and returns success only after exact `P`
is observed and reloaded. The local adapter is not a GitHub/remote adapter. The
GitHub adapter uploads only exact-OID objects, attempts one GraphQL
`updateRefs` CAS, rereads `main` after every acknowledgement outcome, and
requires a fresh anonymous full fetch through the production reader. It refuses
an unprotected or non-SHA-1 authority. The handoff independently fetches exact
authority `P`, reloads it from detached literal `HEAD`, and can freeze only the
exact new prediction/evaluation files into an unattached single-parent artifact
commit `A`. A capability-scoped exact remote `P -> A` publisher candidate is
under review on its isolated branch. It accepts only the freeze-issued artifact
while the same P context remains open, fixes `Jasper-Shi/lottopred` `main`,
uploads and verifies A's required object OIDs, attempts one GraphQL
`updateRefs` CAS with `force=false`, rereads every acknowledgement outcome, and
requires a fresh anonymous full fetch plus `load_published_history(A)`. None of
these seams is connected to a CLI, live entry point, or workflow.

### Remote publication release state

Read-only inspection on 2026-08-24 established these production facts:

- `Jasper-Shi/lottopred` `main` is not protected and the repository has no
  rulesets (`[]`).
- GitHub Actions default workflow permissions are read-only.
- GitHub's GraphQL schema exposes `updateRefs` and the exact `beforeOid` input
  needed for compare-and-swap.

The schema fact proves interface availability only; no production mutation or
remote-safety canary has succeeded. The remaining release blockers are:

1. independently reviewed artifact-publisher code and tests;
2. an authorized disposable-remote exact object-OID/updateRefs canary;
3. configured and independently verified production protected `main`;
4. collector/preparer/publisher/handoff orchestration with reviewed P-code
   provenance;
5. a real exact `P -> A` canary followed by reread and fresh anonymous reload;
6. a separate review of the new config bytes and SHA-bound workflow execution
   plan.

The future live order is fixed: collect both sources, prepare and remotely
publish P, freshly reload P, keep the isolated detached-P context open while
evaluating/notifying/predicting, freeze exact outputs in A with sole parent P,
then remotely compare-and-swap and freshly reload A. Do not evaluate before P,
resume in the caller's old checkout, broadly stage directories, or use an
ordinary push.

Public bootstrap, live refresh, evaluation, and prediction entry points
therefore still refuse execution after their gates. Before reconsidering those
gates, complete every blocker in the remote publication release state above.
The disconnected publisher candidate does not complete the remote operational
path or reviewed release; all switches remain false. The
frozen schema and trust boundary are in
[`OPERATIONAL_HISTORY_REGISTRY_PROTOCOL.md`](OPERATIONAL_HISTORY_REGISTRY_PROTOCOL.md).

Create or validate the seal only in a permission-isolated repository directory.
Legitimate concurrent processes must use the exclusive-create protocol. Treat
any untrusted same-UID process with rename/write access as a compromised host;
the portable seal transaction is not a substitute for OS directory isolation.

The integration that carries this evidence must preserve artifact commit
`b04393944ef12f78417dfb6151343c72d4c2a2ac` and evidence commit
`60dbd42a502850091508491f9011f9a08acf894f`, plus registry genesis
`a6857d6b4e6e532062f484bcce4466f76ba4327b`, as reachable ancestors. Do not use
a squash or rebase merge for those migrations. After merge, test the deployed
registry from a fresh full-history clone of `main`; a passing source worktree is
not enough.

1. The corrected historical epoch and its reconciliation evidence are
   committed, independently reviewed, and bound to exact expected identities.
2. The consuming read path verifies the approved epoch before exposing rows.
   The historical base remains immutable. Offline preparation and local bare
   CAS do not satisfy the remote requirement. Before live can reopen, a reviewed
   network path must retrieve two independent raw-source receipts, append only
   the next canonical suffix and registry events through the exact
   `B -> E -> S -> P` transaction, remotely compare-and-swap `main`, and reload
   that remote revision successfully before evaluation or prediction.
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
- `backtest.yml` — outside the hold, runs the configured historical walk-forward
  benchmark. Reopening it now requires the reviewed corrected-history consumer;
  no corrected rerun makes the consumed 2020–2025 outcomes blind again.
- `live.yml` — runs after model deployment and every Thursday/Sunday, evaluates due predictions, generates the next-draw predictions and commits the audit trail.

During the data-integrity incident the last three workflows remain sealed as
described above. The live workflow retains `contents: write` permission for its
ordinary role, but every Git-writing step is conditioned on the sealed cycle
output and cannot run while the incident guard emits `false`.

The backtest, integration, and live workflows use full Git history so the
verified-history loader can resolve its pinned artifact/evidence ancestry if a
future reviewed execution plan enables a consumer. Full checkout does not
weaken the all-false incident guard.

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

The reviewed exact-CAS paths stop on a stale base, third head, unreadable reread,
or indeterminate acknowledgement. They do not retry, merge, force, or fall back
to an ordinary push. Existing prediction snapshots remain immutable and are
never regenerated or overwritten.

## Scheduled time

The live workflow runs at `15:15 UTC` Thursday and Sunday, well after the preceding Wednesday/Saturday draw. This reduces the chance of querying before official results have propagated.
