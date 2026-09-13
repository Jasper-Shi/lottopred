# Completed V13 historical audit archive

The sole `v13.0.0` worker completed all 627 consumed historical targets and
returned **Reject**, with no Final-6 6/6 from any of its four producers. This
archive records two actually executed, independent audits of the original
worker commit `8ab54e1827317239b33061a439305801e733872c`, whose sole parent is
authorized execution commit `182a4245bbaf0c444ef1e16c1b5beb120eec327f`.
Neither audit generates a new prediction, fits a model or grants execution,
notification, promotion or Goal-completion authority.

- [Integrity proof](independent-audit.json) and [report](independent-audit.md):
  `/root/v13_auth_helper_readiness_review` checked the pinned official history,
  strict prior prefixes, 13-phase startup, permanent lease, original Git/runtime
  bindings, 627 forecast-before-reveal records and 2,508 frozen producer outputs.
  The complete reconstructed JSON and Markdown matched the original bytes.
- [Spec proof](spec-statistical-proof.json) and [report](spec-audit.md):
  `/root/v13_exception_spec_review` independently recomputed scoring, calibration,
  exact integer tests and fixed bootstrap intervals without project imports.
  All registered statistics and ten gates matched. Both reviews had zero
  blocker and zero major findings; the Spec review also recorded zero minor.
- [Original process observation](original-terminal-six-files.json),
  [launch intent](launch-intent.json), [terminal receipt](launch-terminal.json)
  and [stdout/stderr](launch-output.log) preserve the parent process's actual
  exit-0 observation and six-file identity. Earlier `false` publication/audit
  fields in these creation-time receipts remain unchanged; subsequent proofs
  record what happened later.
- [Standards comment](pr55-standards-review.md) and
  [Spec comment](pr55-spec-review.md) preserve actual agent review text prepared
  while PR55 CI was pending. These files do not themselves attest that CI passed.
  The [actual published-review receipt](pr55-published-reviews.json) records
  the real GitHub comment IDs, publisher, remote text and hashes. The separate
  ordinary-merge provenance records the final checks/publication.

[manifest.json](manifest.json) pins the original external basenames, byte counts
and SHA-256 values of the twelve archived files. The two `.py.txt` files contain
exact executed audit-script bytes for source inspection, preserved as historical
artifacts rather than an installed command. Their original local paths and
receipts are deliberately retained. They are not portable launch instructions;
never rerun the historical worker or its launcher to reproduce these audits.

The integrity auditor did not independently refit coefficients. Hash chains and
current GitHub observations are not independent wall-clock witnesses of every
original fsync. Original process exit relies on the retained parent receipt;
the frozen implementation, runtime, durable intents and actual stored evidence
support the operational chronology. Read each proof's full scope and limits.
The worker's own `audit.complete` flag is separate from these independent checks.
Its `pending_git_integration` field remains immutable; Git ancestry, subsequent
publication provenance and later documentation resolve that creation-time state.

PR55 was ordinarily merged at `05986709848b08e069ba14eea832143f14a075f6`
on 2026-09-13T19:35:00Z after both exact-W checks passed 3,162 tests.
[Publication provenance](pr55-merge-provenance.json) records ordered parents,
unchanged tree, protected main and the permanent original lease.
[publication-manifest.json](publication-manifest.json) pins the four later
CI/review/merge observation records separately from the original audit files.

The permanent historical lease is
`refs/heads/v13-consumption-v13.0.0` at
`4cfd6d641d32b7168f74725626448d82f9dec46d`.
Never update, delete, adopt or recreate it, rerun V13, alter its model in response
to these results, or overwrite any original output. No capture notification was
required or sent because no 6/6 occurred. The existing hourly committed-state
email is separate. Live remains paused. The broader research Goal is incomplete.

The archived `pr55-spec-review.md` retains the original two Markdown hard-break
spaces on its reviewer line. Git reports that one line as trailing whitespace;
its exact original hash is intentionally preserved. Other changed files pass
the whitespace check. No repository-wide whitespace rule was changed.
