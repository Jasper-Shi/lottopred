# V12.0.2 completed-run audit archive

This archive accompanies the immutable six-file worker commit
`c9b483f6e89bf73eade28829188fbebe745e28c0`, whose sole parent is execution
authority `b7fa81d6d5facc1730700cd527362df79f457cf8`. It adds audit observations
and reproducibility material after the sole formal run; it changes no forecast,
score, model, scientific rule, authorization or lease. The scientific disposition
is Reject; there was no Final-6 6/6 and the broader Goal is incomplete.

## Records and authorship

- `independent-audit.json` and `independent-audit.md` are byte-for-byte copies of
  the completed independent historical/output/statistical audit by
  `/root/i3_independent_output_audit`, session
  `v12-0-2-post-run-history-chronology-result-20260913-01`. The original full
  historical/statistical audit ran as temporary inline Python. It did not have
  a saved standalone script; these records do not pretend otherwise.
- `output-consistency-auditor.py.txt` is the original standalone read-only
  consistency checker by that same independent agent, preserved without
  formatting changes. Its 68 synthetic checks passed before the worker results
  were available. Root subsequently ran it on the completed worker outputs,
  then on the identical archived bytes. The latter output and exact invocation
  are `archived-output-consistency.json` and
  `archived-output-consistency-invocation.json`. Those later invocation facts
  are root-owned, not another independent reviewer identity.
- `remote-observation.json` is root's GET-only remote/Git observation after
  artifact branch publication. `remote-observer.py.txt` is its exact source.
  It verifies the fixed lease object and its request intent hashes, ordinary
  authority merges, unchanged review comments, successful exact-source CI
  before those merges, current protected main and artifact branch, and all six
  artifact Git/file identities. It makes no remote mutation. Its recorded main
  and branch heads are historical observations; the script deliberately fails
  after those refs advance. Do not change its pins to reinterpret the old receipt.

The `.py.txt` suffixes identify source archives, with no CLI, workflow or model
integration. They are evidence of the executed audit procedures, not additions
to the frozen historical runtime closure. The original worker, authorization
verifier and lease routes must never be reinvoked to reproduce this audit.

| Archived original | SHA-256 |
|---|---|
| independent-audit.json | `f8d12147e065d869ea10e3ebc7ebcd7a3f8249996d9692f0394ab83a53545a31` |
| independent-audit.md | `6cac99e44c22e0c33d256725630c44a0a58755af987b1accd6ec8b4b4fe500b7` |
| output-consistency-auditor.py.txt | `2be159451ee2025b1e96209e942dd0da7b15799c493ce9a15997ff8d9b097407` |
| remote-observation.json | `c94f4cb041ad942fc7e19704ac538ee004ef72e561307907d7f3715f838590cb` |
| remote-observer.py.txt | `d5e6817f4f7ffc25dfa42339bbfceb5f0527cc0178660ff1fc2d79d65fe4f599` |

## Post-audit statistics reproducibility helper

`statistics-replay.py.txt` was authored by `/root/i3_independent_output_audit`
**after** the original inline audit. Its SHA-256 is
`cd73fcd584dbc1d4191cde31e7d0a44ae605d44ba15788e01b4a79b38d307606`.
It adds a standalone read-only route for authenticating the fixed Git history,
all target outcomes and prefixes, frozen forecast score arithmetic, 18 bootstrap
intervals and 12 exact integer ratios. It does not refit or forecast and does
not reproduce the separate complete startup/ledger or source chronology audits.

The final helper passed 24 synthetic/math checks and Ruff check/format. Its
first development replay failed before history access because the helper
incorrectly included a trailing LF in the closure digest. This audit-helper
encoding error was corrected against the frozen digest format, then the final
source passed. No worker or scientific output was changed or rerun.
The original author replay passed as session `48762`, exit 0. The later archived
replay result and root invocation are `statistics-replay-result.json` and
`statistics-replay-invocation.json`; they are additional audit observations,
not replacements for the original independent receipt.

Using the existing frozen CPython 3.12.11 / NumPy 2.3.5 environment and complete
local Git history, from the repository root:

```sh
/Users/jaspershi/CodexResearch/venvs/lottopred-v12-frozen/bin/python3.12 -I -S -B \
  evidence/research_audits/v12-0-2-historical-20260913/statistics-replay.py.txt \
  --verify-frozen-negative-result --repository .
```

Use `--self-test` alone for synthetic/math checks. The original source pins its
frozen dependency location; it intentionally refuses incompatible environments.
Preserve the archive unchanged. A future portability wrapper would be a new
reviewed audit helper, not a revision to this source or its existing receipts.

## Read-only output consistency replay

Use CPython 3.12 with the archived source from this checkout. From the repository
root, this command reads existing files only; it cannot generate predictions,
load model features or consume a lease:

```sh
python3.12 -I -S -B evidence/research_audits/v12-0-2-historical-20260913/output-consistency-auditor.py.txt \
  --output-dir "$PWD/reports" \
  --expected-execution-commit b7fa81d6d5facc1730700cd527362df79f457cf8 \
  --expected-source-commit caaeaca6d5ddfd3705171d86fddd3c53bdd75de6 \
  --expected-authorization-sha256 2bc702251488876bfc488e3bb5531b9157c0ab3913091e4f795fe0b74b4d29cd \
  --expected-lease-commit a8b264a5d3db199e831b0c06cb0697794766d160 \
  --expected-execution-tree 4992f479c2c6e33b8fc130eb58de95ccc770ae05 \
  --expected-execution-epoch 1789276427
```

`--self-test` instead of these arguments runs synthetic consistency checks
without reading the historical output directory. The consistency checker alone
does not replay bootstrap intervals, authenticate actual draws or establish
remote authority; the independent audit and separate remote receipt document
those additional checks.

## Interpretation and limits

The independent audit authenticated all 627 actual main/bonus outcomes and all
visible prefixes to the fixed committed governed authority. It checked all
49 probabilities and rankings per producer, score arithmetic, calibration,
annual summaries, both journals, source/core/runtime pins, exact p-value ratios,
18 bootstrap intervals from frozen score arrays, and all ten gates. It never
refit a model or regenerated a forecast. The later replay of consistency is
an audit of the same evidence, not a new statistical attempt or opportunity.

The independent audit's own complete limitations remain in its JSON and
Markdown records. In particular:

- The loader held the complete governed dataset in memory. Strict-prefix model
  inputs and the forecast/reveal boundary isolate predictions. There is no
  claim that future rows were physically absent from the entire process.
- Source review plus output chronology supports the recorded order. No direct
  historical instruction/memory trace, external OS durability attestation or
  trusted wall-clock attestation was recorded.
- Actual outcomes were checked against the fixed governed Git authority,
  not freshly authenticated from a second external lottery publisher.
- Recorded runtime matches the fixed source pins and audit environment; this
  is not independent physical attestation of the historical process.
- Root's current remote GETs prove the state at observation, not uninterrupted
  past lease existence or historical branch-protection settings. Startup
  journals record pre-run absence/creation/reread and are worker receipts.
- Draw-level bootstrap intervals are the frozen diagnostic resampling rule,
  not generally serial-dependence-robust intervals. Family Holm adjustment is
  limited to the declared four-variant transition family, not the entire Goal.
- The report's cumulative fair-opportunity product uses the realized, adaptively
  determined unique ticket counts. It is nominal bookkeeping, not a Goal-wide
  unconditional or anytime-valid p-value; reused comparator tickets are not new
  globally independent opportunities.
- This is a scoped completed negative-result audit, not the special independent
  leakage audit required after a captured Final-6 6/6.

The remote receipt observed artifact publication on its own branch, before
ordinary protected-main evidence integration. A later merge must preserve
`c9b483f6...` as a reachable ancestor and leave all six worker files identical.
Use that Git relationship to establish integration; never change the report's
creation-time `audit_publication=pending_git_integration` field or these dated
observations to claim they knew a future merge.

For interpretation of every result and links to the original complete records,
see [the result document](../../../docs/research/V12_0_2_HISTORICAL_RESULTS.md).
