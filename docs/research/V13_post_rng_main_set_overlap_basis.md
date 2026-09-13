# Basis for V13: one exact main-set overlap law

This document supports the
[V13 preregistration](../experiments/V13_post_rng_main_set_overlap.md).
At R13 the version is registered, not implemented, authorized or scored.
Its complete fixed mathematics and literal oracles live in the
[registration seal](../../evidence/research_registrations/v13-post-rng-main-set-overlap-v1.json).
No empirical V13 advantage is asserted.

## Why this restriction is testable

Choosing k labels from an anchor of size six and 6-k from the remaining 43
gives N_k=C(6,k)C(43,6-k). Vandermonde's identity gives
sum N_k=C(49,6)=13,983,816. Exponential tilting by beta*k defines a normalized
law over six-element sets with one parameter. Under beta=0 it is exactly the
fair combinatorial law, with E[k]=36/49 and Var(k)=5547/9604.

Differentiating log Z gives the mean and variance. The fixed Normal(0,1)
log prior makes the objective strictly concave:
`Q''(beta)=-1-D*Var_beta(k)<0`. Thus there is a unique MAP optimum and no
choice among fitted local maxima. Since 0<=k<=6, the registered bracket
`[-(6D+64), +(6D+64)]` contains the root. Integer residual
`49*sum(k)-36*D` determines which side contains it; exact fairness bypasses
the small floating-point score residual at zero.

The prior, full expanding pair history and 256-iteration bisection are fixed
engineering/scientific choices made before any V13 result. They are not
estimated by comparing validation scores. The program prescribes binary64
operation order because algebraically equal forms can round differently.
The separately summed complementary overlap moment avoids subtracting nearly
equal quantities at an extreme positive tilt. Final probabilities must remain
strictly inside (0,1); failure terminates rather than repairing the law.

## What the ranking can and cannot express

Within the preceding main set all six labels have equal inclusion probability;
all 43 outside labels form the other equal-probability group. Exact-law
positive beta favors the prior set, negative beta favors its complement,
and zero is fair. The literal numerical and tie oracles define the actual
binary64 ranking. Ascending label ties are a deterministic convention, not a
theory that small numbered balls are favored.

The probability law is equivariant under relabeling. The ascending-label
ranking is not. In particular, outside-group selection cannot distinguish
which of those 43 labels is more likely. This limited representational power
is disclosed before scoring and cannot motivate a post-result refinement.

## Why the cyclic control is correlated

For uniform S and fixed size-six anchors A and B with intersection size r,
the covariance of the two overlap counts follows from sampling without
replacement. Dividing by their common variance gives
`Corr(|S intersect A|,|S intersect B|)=(49*r-36)/258`.
For B=pi(A), pi(i)=1+(i mod49), a uniform anchor has E[r]=5/8 and the
unconditional fair correlation is -1/48.

Under the candidate alternative the transformed anchor's conditional shift
is `(r-36/49)*(p_inside-p_outside)`. Under a uniform stationary anchor law
the mean shift is `-43*(p_inside-p_outside)/392`. A true alternative may
therefore make the control weakly predictive with the opposite sign.
The registered null-control conjunction is conservative and can reject
shared real dependence. A failed control gate is a scientific failure,
not automatically evidence of leakage. No alternate map is available.

## Scope of the statistical statements

Under independent uniform draws, any Top-12 set determined by the past has
the same conditional Hypergeometric(49,12,6) hit distribution. Iterating that
conditional law validates the registered fixed-horizon integer convolution
despite expanding-prefix refits. This argument does not claim independent
hits under arbitrary alternatives. Ordinary row bootstrap intervals are
reported as fixed descriptive diagnostics, with their dependence limitation.

The mathematical product of exact-law likelihood ratios against fair draws
is a prequential fair-null martingale. Its binary64 log evaluation is a
numerical diagnostic, not a proof of exactly normalized floating products.
The fixed log(20) gate is neither an early-stop rule nor Goal-global evidence.
Stopping at a first 6/6 forbids completed-horizon inference on that prefix.

The five-entry Holm adjustment is limited to the disclosed transition family.
V2/V3 unavailable compatible p-values stay at the previously registered
conservative value 1; the inherited V11 value remains legacy accounting,
not newly corrected-history evidence. The immutable V12 raw value is solely
an accounting input. Missing or incompatible provenance blocks authorization;
no replacement rule may be chosen after a V13 outcome.

Existing V1/random tickets can repeat between experiments. Counting them
again as independent opportunities would inflate the apparent search.
The local ledger deduplicates each target/set and preserves cross-version
identity; it never retroactively populates an untouched-evidence ledger.
An adaptive observed-count chance product is nominal accounting, not an
unconditional or anytime probability of the observed research search.

## Scientific preparation and independence

The science draft was authored by `/root/i3_evidence` using source,
registrations, synthetic fixtures and closed mathematics. The separate
`/root/v13_novelty_review` task supplied substantive novelty and mathematical
input, so it is credited as a contributor rather than an independent reviewer
of the completed registration. Root supplied the already frozen V12 p-value
for accounting and integrated wording about normal ensemble constituent
execution and the user-authorized Final-6-only notification route.

An independent draft science review by `/root/i3_independent_output_audit`
verified the mathematical/statistical fixtures and the three integration
string changes. That agent subsequently authored the operational contract;
it consequently cannot act as an independent reviewer of the final R13
source. Fresh Standards and Spec source reviews must use actual distinct
non-author agents and sessions. The seal lists all source contributors,
including tests and integration, independently of the GitHub publisher.

Some project participants, including root and the later operational author,
already audited prior V12 results. This preparation is not globally
outcome-blind. No V13 result exists, and no target answer or governed-history
payload was accessed to choose or change this new scientific contract.
The fixed 2020–2025 period remains consumed historical diagnostic data.
No model promotion or live activity follows from registration.
