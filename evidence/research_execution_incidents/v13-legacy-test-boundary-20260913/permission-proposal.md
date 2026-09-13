# Limited legacy-test exception — ready for user decision

**Unapproved proposal.** The interrupted full suite remains stopped. This document
supersedes the earlier proposal only by clarifying coverage of the first CI run
for the replacement operational registration; it does not change V13 source.

The root agent started full repository tests without first checking legacy
fixtures' data reads. Source audit identified real historical CSV and old ledger
readers. The test was immediately interrupted: exit 2, 230 passed in 668.11 seconds.
Its terse log lacks node IDs; specific executed readers are inferred from the
unmodified default ordering. This is not a passing full suite, a V13 model run,
a V13 result, or proof of model tuning. The incident record is preserved.

R13's activation contract prohibits governed-history and target-answer loads
before historical authorization. The mandatory full legacy suite conflicts with
that restriction. Independent protocol review found no existing exception.

## Requested permission, for future tests only

Permit the existing legacy regression tests from protected-main commit
900054719a4ac089d4c059830b5c7162f2543616 to read the historical files and completed-
experiment evidence they already use, solely for their existing parsing,
integrity and evidence-consistency checks. This permission would cover both local
regression and automatic CI, **including the first CI run of the new operational
registration PR before that registration is merged**, and subsequent implementation
checks governed by the new registration.

Before any such rerun, freeze the compatible replacement operational rules and
obtain independent Standards and Spec review. Follow the explicit user permission
for those limited tests while completing normal CI and the protected-main
registration merge. This removes a circular dependency: CI can verify the new
registration without pretending it was already merged or already authorized a
historical worker.

Keep the legacy code and data references fixed and run tests offline in an
isolated workspace. Any synthetic test products stay in owned temporary fixtures;
no real canonical research outputs or remote operational mutations are allowed.
Keep V13 tests synthetic-only, and keep the already reviewed statistical rule
unchanged. Real V13 training, prediction, reveal and scoring must still wait for
the separately completed historical authorization chain and unique run lease.
No live run, ticket recommendation, email, repeat worker or lease change follows
from this permission. Test payloads must not be exposed in logs or used to select
or change the candidate.

Preserve the current immutable R13 seal and this incident. Register a distinct
operational version if required by the frozen contract; do not silently edit the
old seal, backdate permission, label the interrupted run compliant, or describe
consumed historical data as untouched evidence. This request authorizes no
retroactive correction of what occurred.

If permission is declined or absent, full legacy tests, CI, implementation merge
and historical execution remain paused while source-only work can continue.

Independent protocol review: `/private/tmp/v13-legacy-test-exception-protocol-review-20260913.md`,
SHA-256 629e47c3b4ddd1727cdde8f19cafb82c7fc7f09ef66579a6411e60b154b6773f.
