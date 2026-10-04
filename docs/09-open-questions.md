# Open questions and critical decision gates

## Findings that should be treated as settled for this scope

1. Full terminal-state funding is coherent and can avoid liquidation for bounded prepaid contracts and underwriters.
2. Premiums and fees are actual cashflows, not changes to contractual caps.
3. A shared categorical CTF condition can match the exact backing floor for arbitrary nonnegative finite curves as baskets.
4. Complete-set conversion, negative risk, collateral return and account risk aggregation are prior work. No novelty claim follows from taking a finite maximum.
5. The current repository already contains a relevant exact account model and local CTF parity evidence. A second ledger is not needed merely to demonstrate the thesis.

## Decisions that still need evidence

| Priority | Question | Evidence that resolves it |
|---|---|---|
| P0 | Who repeatedly wants multiple cover shapes on this same observation? | Real portfolios and buyer/maker interviews, conducted separately with authorization |
| P0 | Do state maxima diverge in actual flow? | Liability vectors and lifecycle savings from realistic trade/exit sequences |
| P0 | Does a native basket satisfy the desired buyer experience? | Wallet/SDK demonstration; requirements for single-token transferability |
| P0 | Is internal account execution materially better than CTF transformations? | Matched gas, latency, complexity and export/exit benchmarks |
| P0 | What exactly is the BTC historical observation and failure policy? | Provider capability, source selection and finality contract with boundary tests |
| P1 | Are bucket payoffs useful protection? | External loss mismatch analysis; repeated demand for unaligned thresholds or ramps |
| P1 | Can makers quote competitively after source and capital costs? | Firm/shadow quotes, adversarial latency replay and realized cost accounting |
| P1 | Which current competitor already supports the required task? | Current API/source review plus matched executable workflows; no hypothetical weak baseline |
| P1 | How much lock duration does dispute/timeout add? | Provider delay distribution and funded failure semantics |
| P1 | Do maker quotes need reservations? | Competing-fill rejection rates versus jointly reserved capital |
| P2 | Is exact continuous piecewise-linear support needed? | Concrete payoff demand plus proved rounding/extrema implementation |
| P2 | Is CTF export needed for B? | Named external applications and asset compatibility requirements |

## Limits of earlier repository comparisons

The earlier Gamma comparison concerns a pinned collateral formula and specified instrument set. It does not prove superiority over all options clearing or mixed collateral. The earlier Deribit simulator requests were prepared, not authenticated and executed; this review does not invent numerical venue margin results.

The NegRisk comparison is about a particular adapter and partition layout. It is not a proof covering current Combo decomposition or all Polymarket behavior. Its refinement scenario is outside the locked-grid MVP, and its old reproduction module is absent. Archived result files remain evidence records, not automatically reproducible current code.

The existing pricing/marketplace experiments use stipulated probabilities and quotes. They show coherent mechanics and possible routing, not sustainable profitability or simultaneous liquidity for every admitted interval.

## What might be new or useful

The candidate product is an account and execution abstraction over a canonical event domain: reusable custom curves, exact vector risk, affordable portfolio modifications, shared maker inventory and interoperable claims. Each component has precedents. The useful integration may still be valuable if it reduces actual friction or cost.

A more distinctive future capability might be compact exact verification of path-dependent same-event portfolios where explicit joint CTF inventory becomes expensive. That is not the first terminal-price MVP, and both the graph engine and combinatorial CTF representation face resource limits. Do not use this possible later advantage as evidence for a present claim.

## Fundamental flaws to avoid

- Netting creates no capital below the worst payout using cash-only backing. A plan to withdraw that last backing dollar while leaving claims outstanding is impossible under the stated guarantee.
- Minting one independent funded binary condition per curve sacrifices relationships already available in one common condition. Comparing against that design is not enough to justify new custody.
- “Same asset” does not prove same state space. Different expiries, feeds, invalid policies or observations cannot share this netting.
- Guaranteed terminal solvency is not guaranteed early exit liquidity, oracle truth or favorable pricing.
- A continuously changing state grid and arbitrary unrestricted payout code defeat the small exact-verifier scope.
- Passive LP capital is not free maker profit. If the market lacks complementary demand, concentrated liability can erase the thesis's practical savings.

## Decision

The next credible step is a comparative common-domain execution prototype and commercial evidence. Retain CTF for the finite MVP. Keep internal clearing as a research option, with its precise invariants available here. Do not claim Asce has discovered a new capital primitive or already established a standalone business.
