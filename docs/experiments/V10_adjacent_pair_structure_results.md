# V10 Adjacent-Pair Structure Result and Decision Record

## Decision

**Reject `v10_adjacent_pair_structure` version `v10.0.0`. Do not activate it.**
V1 remains the production-baseline suite and V3 remains the only research
shadow model. Their operational roles are unchanged.

The unique registered 621-target historical diagnostic completed normally and
passed its audit, but only five of ten jointly required scientific gates
passed. Aggregate Top-12 lift was positive at `0.020145256170100767`, but the
one-sided p-value was `0.31366891969110644`, the Holm-adjusted p-value was
`0.5445965052903498`, and the bootstrap interval
`[-0.05875973577836935, 0.09743994216043905]` included zero. Proper scores were
worse than the exact fair constant beyond the registered tolerance, the
complete-set joint mechanism result was negative, and the candidate did not
reliably outperform its targeted label-bijection control.

This is a valid negative result, not a pipeline Archive. `audit_warnings` is
empty and the permanent hash-chain ledger verifies all 621 forecast-freeze
events before their corresponding target-reveal events. The 2020–2025 lane is
consumed historical diagnostic evidence; it is not blind, confirmatory, or
prospective evidence and may not be run again for `v10.0.0`.

## Audit identity and immutable artifacts

- Experiment: `V10_adjacent_pair_structure`; descriptive family:
  `structural_set_features`; multiplicity family: `v5_pair_cooccurrence`,
  variant `2`.
- Candidate: `v10_adjacent_pair_structure`; version: `v10.0.0`.
- Registration commit:
  `e7ac6b81d45b647ca1d144bdd8e21ce66a106185`.
- Frozen implementation commit:
  `38be95eb27aa69a9e16bc972d14df13b0b24d6dd`.
- Historical dataset: 4,432 draws through 2026-08-15, source commit
  `90177c80cfb070038d79508fb2e73305a297f516`, raw SHA-256
  `edfb7f8a4a7711a630957d6f86b567e6b254caf7b1d1aaea0edf1d16a34155b3`.
- Permanent one-shot
  [claim](../../reports/v10_adjacent_pair_structure_v10.0.0_historical.claim):
  SHA-256
  `0f68d60ec923de2fc3370e95f939069d3ffd4f22f4ed6b30da3773dcd49877c6`.
- Permanent hash-chain
  [ledger](../../reports/v10_adjacent_pair_structure_v10.0.0_historical.ledger.jsonl):
  1,250 events, SHA-256
  `774434e8cd34664f4546a7874f043dbf752e9aaf579ef9d020639cf2d8c4d3c9`.
- Machine-readable
  [report](../../reports/v10_adjacent_pair_structure_v10.0.0_historical.json):
  schema `1`, SHA-256
  `26fe097bad44c6563a1c4d659a42b0bbdbdc7e3414bc62e37a3ec5108edd49c6`.
- Generated compact
  [report](../../reports/v10_adjacent_pair_structure_v10.0.0_historical.md):
  SHA-256
  `25ac333713db4fab79bcc72f83662456f54ed6adc0eb6ec6775a7794060281c8`.
- Frozen specification:
  [`V10_adjacent_pair_structure.md`](V10_adjacent_pair_structure.md).

The ledger contains exactly 621 `prediction_frozen` and 621
`target_revealed_scored` events. Its first event is `claimed`, its terminal
event is `published`, and no 2026 target was scored. The registered 307/314
fixed halves, CPython 3.12 runtime lock, implementation ancestry, pushed commit,
CI checks, data boundary, control map, and V5/V8 reference identities all
passed before the claim was acquired.

## Candidate ranking results

Fair per-draw expectations are `36/49 = 0.7346938775510204` for Top-6,
`72/49 = 1.4693877551020409` for Top-12, and
`108/49 = 2.204081632653061` for Top-18.

| Scope | Draws | Top-6 mean / lift | Top-12 mean / lift | Top-18 mean / lift | Total Top-12 | Exact p | Holm p | Top-12 bootstrap 95% CI |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Aggregate | 621 | 0.711755233494364 / -0.022938644056656465 | 1.4895330112721417 / 0.020145256170100767 | 2.2270531400966185 / 0.02297150744355747 | 925 | 0.31366891969110644 | 0.5445965052903498 | [-0.05875973577836935, 0.09743994216043905] |
| 2020–2022 | 307 | 0.7296416938110749 / -0.005052183739945537 | 1.488599348534202 / 0.019211593432161056 | 2.231270358306189 / 0.02718872565312802 | 457 | 0.377340655036301 | n/a | [-0.08828026324536342, 0.12996077909991355] |
| 2023–2025 | 314 | 0.6942675159235668 / -0.04042636162745361 | 1.4904458598726114 / 0.021058104770570463 | 2.2229299363057327 / 0.01884830365267165 | 468 | 0.36342829738160165 | n/a | [-0.09040686338229564, 0.1325230729234368] |

The Top-12 point estimate was positive in both halves and exceeded the frozen
V1 ensemble mean (`1.4895330112721417` versus `1.3977455716586151`). It was
below the existing V3 descriptive mean (`1.5217391304347827`). More
importantly, the aggregate interval included zero and the multiplicity-adjusted
p-value was far above `0.05`; the point increase is therefore not reliable
predictive evidence. Top-6, the actual six-number output, was below fair theory
in every scope.

## Proper scores and complete-set mechanism

The exact fair-constant references are Brier `0.10745522698875469` and log
loss `0.37177617994345286`. Positive deltas are worse; the registered maximum
was `1e-9` in every scope.

| Scope | Brier / delta vs fair | Log loss / delta vs fair | Mean actual rank |
|---|---:|---:|---:|
| Aggregate | 0.10745529826088167 / 0.00000007127212697799479 | 0.37177651145660673 / 0.0000003315131538728089 | 24.988727858293075 |
| 2020–2022 | 0.10745527753453828 / 0.000000050545783586430915 | 0.371776415014657 / 0.0000002350712041687686 | 24.85342019543974 |
| 2023–2025 | 0.10745531852517282 / 0.00000009153641812587043 | 0.3717766057485766 / 0.0000004258051237715499 | 25.121019108280255 |

All six proper-score deltas exceeded the tolerance, so the non-degradation gate
failed.

The complete-set prequential log-gain gate failed more directly:

- candidate aggregate: `-0.19939433677351204`;
- candidate halves: `-0.11995566773341082`, `-0.07943866904010122`;
- label-bijection control aggregate: `0.18824492908563784`;
- candidate minus control aggregate: `-0.3876392658591499`;
- candidate minus control halves: `-0.2693046082031252`,
  `-0.11833465765602469`.

The registered candidate threshold was `log(20) = 2.995732273553991` in the
aggregate, with positive candidate and candidate-minus-control values required
in both halves. The observed values do not support the proposed adjacency
mechanism.

## Targeted control and comparisons

The fixed global-label bijection control behaved as null in the aggregate and
both halves. However, the candidate did not show a reliable advantage over it:

| Scope | Mean candidate minus control Top-12 hits | Paired 95% CI |
|---|---:|---|
| Aggregate | 0.004830917874396135 | [-0.0821256038647343, 0.09017713365539452] |
| 2020–2022 | 0.026058631921824105 | [-0.09446254071661238, 0.1465798045602606] |
| 2023–2025 | -0.01592356687898089 | [-0.14331210191082802, 0.10828025477707007] |

Every interval included zero and the second-half point estimate favored the
control. Within the append-only V5/V10 multiplicity family, V5's raw p-value
was `0.2722982526451749`, V10's was `0.31366891969110644`, and both Holm
adjusted values were `0.5445965052903498`.

## Final-six hit record

The complete final-six hit distribution is:

| Hits | 0 | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Count | 274 | 262 | 75 | 10 | 0 | 0 | 0 |

The maximum was **3/6**, occurring on 2020-02-19, 2020-04-15, 2020-05-16,
2021-07-24, 2023-04-01, 2023-08-16, 2024-01-20, 2024-02-21, 2025-04-19,
and 2025-12-03. Under exact fair six-of-49 selection, 621 targets have an
expected `10.960900801326334` occurrences of 3/6, so ten such outcomes are not
an unusual success signal.

There were no 4/6, 5/6, or 6/6 outcomes. The registered historical-6/6 branch
was never entered, no breakthrough bundle was produced, and
`stop_global_search` remained false. Top-12 reached at most 4/6.

## Frozen gate decision

| Gate | Result | Evidence |
|---|---|---|
| Positive aggregate primary lift | Pass | `0.020145256170100767` |
| Holm-adjusted p at most 0.05 | **Fail** | `0.5445965052903498` |
| Aggregate bootstrap lower endpoint above zero | **Fail** | `-0.05875973577836935` |
| Positive primary lift in both halves | Pass | `0.019211593432161056`, `0.021058104770570463` |
| Proper scores within fair tolerance | **Fail** | all aggregate/half deltas exceed `1e-9` |
| Candidate above frozen V1 ensemble Top-12 | Pass | `1.4895330112721417 > 1.3977455716586151` |
| Controls null in aggregate and halves | Pass | registered disjunctive null rule met |
| Candidate outperforms targeted control | **Fail** | all paired intervals include zero |
| Joint mechanism gate | **Fail** | candidate and candidate-control gains are negative |
| Audit clear | Pass | `audit_warnings=[]` |

Five of ten gates passed. Because the registered decision is a conjunction,
`all_scientific_gates_passed` is false, the decision is **Reject**, and
prospective status remains exactly `not_activated`.

## Consequences

`v10.0.0` is closed as a valid negative result. It must not be added to
`config.yaml`, must not create live or shadow snapshots, and must never be
rerun. The permanent claim, ledger, reports, registry result, and terminal seal
must remain append-only evidence of the attempt.

No existing prediction or evaluation was modified. V1 remains production and
V3 remains shadow. Any changed adjacency hypothesis must use a new identity,
pre-registration, multiplicity entry, and future prospective cohort; the
observed 2020–2025 outcomes and all results known before that new freeze are
consumed for the changed candidate.

The V10 terminal-seal change advances a file in V3's frozen manifest before V3
activation. V3 still has no freeze commit, activation anchor, release seal, or
`v3.0.0` evidence. Any future V3 activation must therefore use the commit that
contains this V10 terminal result and seal as its new final freeze `F`; the
earlier `f791c91` candidate must not be used.
