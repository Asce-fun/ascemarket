# State-aware clearing: research verdict

Research date: 30 September 2026. Scope: one collateral asset, one terminal observation, one expiry, one immutable settlement domain per clearing account. This report is research, not a change to deployed contracts or an implementation mandate.

## Verdict

**The collateral thesis is correct. The basic capital-saving primitive is already available in a properly constructed shared CTF condition.** Internal portfolio accounts may be useful infrastructure, but the proposed finite-state MVP does not establish a new collateral capability.

For nonnegative covers `f_i[k]` written by one maker, the cash backing floor is:

\[
M=\max_k\sum_i q_i f_i[k],\qquad q_i\geq0.
\]

This is an exhaustive contractual maximum, not a loss quantile. It is smaller than separately funding each cap whenever the individual maxima cannot all occur together. It cannot be smaller than `M` with only cash assets and the same unconditional promises: the state attaining `M` requires that much cash.

**Recommend Architecture A for the stated 5–10-state MVP: a canonical event/payoff and execution layer above native CTF.** Use one categorical condition for the common terminal state space, including failure treatment. Represent variable covers as baskets of its atomic outcome claims; subset covers can use a single native collection. Do not create an independent binary condition for each cover.

Research Architecture B as an alternative if persistent accounts and frequent custom payoff modifications materially reduce measured transaction/storage cost or provide necessary behavior. It is a real new custody and accounting surface, not a way to mint unbacked CTF claims. CTF conversion is optional; cash settlement should be direct. There is no demonstrated reason to choose Architecture C here.

## The requested first deliverable

| Deliverable | Result | Detail |
|---|---|---|
| A: existing systems | CTF already supplies funded contingent claims, partitions and conversions. Exchange matching adds execution. Current Polymarket also documents collateral-return workflows. None should be described as isolated-cap funding only. | [CTF analysis](01-ctf-analysis.md) |
| B: exact clearing model | Every account's terminal entitlement must remain nonnegative; all entitlements must reconcile to actual event assets. Premiums enter cash once. | [Accounting](02-clearing-model.md), [proof](03-math.md), [contract checks](05-solvency-invariants.md) |
| C: three numerical examples | 26,000 → 11,000 USDC; 22,000 → 11,000; partial close reduces backing by 500 but releases 100 after its 400 consideration. | [Examples](06-examples.md) |
| D: architecture | A first; B requires a demonstrated account/representation advantage; C is unsupported. | [Architecture](04-architecture.md) |
| E: critical assessment | Useful formulation and possible infrastructure; no established novelty in same-event deterministic netting or complete-set backing. Commercial differentiation remains unproven. | This document and [open questions](09-open-questions.md) |

## What the existing repository actually establishes

This review used the current working tree, including its uncommitted research. It preserved that work. The repository already contains two alternatives:

- [The current CTF design](../contracts/ctf-cover-architecture.md) selects native claims and an oracle adapter, while leaving exchange design open.
- [The signed-account specification](../v2-kernel-spec.md) and [model_v2](../model_v2/README.md) implement exact finite graph funding in Python. They already distinguish signed cash from withdrawable funds and check conservation.

The [netting review](../research/netting-safety-review.md) correctly identifies exception payouts, hedge removal and account-local backing. The [capital challenge](../research/capital-challenge.md) correctly warns that execution order and expensive buybacks can erase lifecycle savings. Its old `model/` reproduction targets are absent; those earlier experiments were not rerun in this review.

The [30 September CTF findings](../research/cover-marketplace-test-findings.md) already show parity for mutually exclusive covers and a native interval buy/change/close lifecycle. We reproduced their 160 assertions, seven expected transaction reverts and 26 redemption scenarios. The existing 63 Python tests pass.

New evidence extends the comparison from exclusive binaries to unequal payoff vectors. The existing ledger and an independent direct-state arithmetic module agree on the worked cases. A new runner using published CTF 1.0.3, with the repository's existing test currency, reproduces Example A's 11,000 backing and Example C's 500 backing release: 63 assertions and 12 redemption scenarios. No new Solidity was written.

These tests demonstrate mechanics under explicit assumptions. They do not establish market demand, profitable maker quotes, oracle accuracy, deployment safety or a production gas comparison between A and B.

## Where value could remain

Professional makers are the strongest first candidate because they hold many related shapes and can actively seek trades that fill less-used state capacity. A passive pool can achieve the same offsets **if it is one legally/economically shared portfolio**; professionalism does not improve the mathematics. Makers may improve inventory management, quoting, hedging and execution quality.

Buyers benefit from bounded prepaid exposure and potentially better quoted size or spreads. Lower maker capital does not automatically lower prices. Illiquid exits remain illiquid. A buyer's actual external loss may also fail to match a coarse bucket cover.

Applications could share a canonical event definition and immutable payoff catalogue, or route to maker accounts through a common clearing API. That is a plausible infrastructure product. Merely sharing an underlying label does not authorize shared collateral: source, timestamp, units, failure policy, finality and settlement asset must match.

The strongest competing design is a common CTF state basis with good routing and account tooling. For this MVP it reaches the same backing floor. Kalshi's published collateral-return rules also recognize contractual offsets in eligible event groups; the arithmetic is not unique to Asce. See the [event-market comparison](../research/event-markets/README.md).

## A commercial decision rule

Proceed with a small comparative prototype, not a broad clearing deployment. Use real or firm shadow maker portfolios to measure:

1. `sum(individual caps) / max(aggregate payout)` and the same ratio over actual lifecycle checkpoints.
2. The incremental reserve `max(L+f)-max(L)`, premium, fees, temporary funding and oracle lock duration separately.
3. Matched CTF basket execution cost versus internal account execution cost, including export and settlement.
4. Executable spread, size, rejection rate, maker PnL after costs and demand for repeat payoff changes.

If traffic is mainly same-direction downside protection, most maxima coincide and there may be little saving. If the best CTF route already supports the required operations at acceptable cost, build that route. A custom custody layer then adds risk without demonstrated benefit.

## Scope exclusions

No BTC/ETH, Fed/BTC or weather/energy offsets; no statistical correlations, VaR collateral discounts, mark-based assets, lending of backing, unbounded contracts, maintenance margin or forced liquidation. The same BTC observation at a different expiry is a different clearing domain. The earlier multi-checkpoint graph work is retained as research, not brought into this MVP.
