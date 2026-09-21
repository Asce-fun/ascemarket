# A concrete competitive test: two separate payout peaks

Research date: 17 September 2026. This is a source-level architecture comparison and an executable accounting experiment, not a live trading comparison.

## Verdict

**We found a specific funding advantage over the inspected Opyn Gamma vault rules for a fixed option portfolio. We have not established an advantage over the best available options venue, Polymarket, or every possible Gamma strategy.**

The useful distinction is whole-account funding across several compatible payout shapes. It is not a new option payoff, a custom strike, or an easier editor. The strongest remaining challenge is whether another route can provide the same exposure and guarantees at comparable capital and total cost.

The result justifies investigating this narrower capability. It does not yet justify launching a general exchange or claiming that users will switch.

**Follow-up:** the [stronger construction test](competitive-followup.md) extends the 387.5 lower bound to additional same-expiry, cash-collateralized puts at arbitrary nonnegative strikes under the same formula. It also explains the value of freed cash and prepares the still-unexecuted Deribit margin comparison. Mixed-instrument alternatives and deployed execution remain outside the proof.

## 1. The task and the matched exposure

Candidate user: a seller or market maker writing bounded payouts across several price regions of one observation. Their assumed need is to fund the complete inventory rather than commit separate cash to each structure. No interview or trading record establishes that this specific task is frequent or commercially important.

Sell two triangular payouts on the same final ETH observation:

- First pays zero at/below 2,800, rises to 200 at 3,000, then falls to zero at 3,200.
- Second pays zero at/below 3,400, rises to 200 at 3,600, then falls to zero at 3,800.
- Both remain zero outside their respective ranges. They cannot both pay at the same final observation.

The maximum combined obligation is **200**, not 400. These are final-observation contracts, not promises triggered whenever a price is touched.

Let `P(K)` be the ordinary terminal put payout `max(K - x, 0)`. The buyer's combined payout is:

```text
B(x) = P(2800) - 2P(3000) + P(3200)
     + P(3400) - 2P(3600) + P(3800)
```

The seller therefore has shorts of one put each at 2,800 / 3,200 / 3,400 / 3,800, and longs of two puts each at 3,000 / 3,600. All six strikes exist in the saved Deribit expiry catalogue. This is deliberately a listed-strike example: missing custom strikes cannot manufacture the result. [Catalogue](deribit-catalog-2026-09-17.json).

Match the underlying observation, expiry, settlement asset, quantities and premiums. The calculations assume the collateral and strike asset are the same stable unit. Normal terminal payouts match mathematically. Matching actual venue observation rules and exceptional settlement treatment remains unverified; the Asce harness additionally checks its own zero-claim `VOID` rule.

## 2. What the named alternative actually implements

Inspected Opyn Gamma commit `841f81d9d05da9d27277b5775edfbb48c4012d2a`, not merely its product description:

- A vault accepts at most one short option type and one long option type. Compatible longs must share underlying, expiry, strike/collateral assets and put/call type.
- For a fully collateralized put vault, required cash is `max(q_short × K_short − min(q_short, q_long) × K_long, 0)`.
- The liquidation function requires vault type 1. The maximum-loss/spread comparison here uses type 0, so it does not credit Asce with eliminating liquidation that this comparator already avoids.

Sources: [vault constraints](https://github.com/opynfinance/GammaProtocol/blob/841f81d9d05da9d27277b5775edfbb48c4012d2a/contracts/core/MarginCalculator.sol#L1134), [put margin formula](https://github.com/opynfinance/GammaProtocol/blob/841f81d9d05da9d27277b5775edfbb48c4012d2a/contracts/core/MarginCalculator.sol#L845), [liquidation restriction](https://github.com/opynfinance/GammaProtocol/blob/841f81d9d05da9d27277b5775edfbb48c4012d2a/contracts/core/MarginCalculator.sol#L416).

This establishes the inspected code's rules, not the current configuration or availability of a deployed market. No Gamma transaction or Solidity test was executed.

## 3. Give the alternative its best allocation

Putting each butterfly in its obvious spread vaults needs 400 cash. That is not the strongest baseline. Allow fractional quantities, arbitrary splitting across vaults and free rearrangement of the entire fixed inventory.

The best continuous allocation needs **387.5** cash:

| Short strike | Short quantity | Long strike | Long quantity | Cash required |
|---|---:|---|---:|---:|
| 2,800 | 1 | 3,000 | 14/15 | 0 |
| 3,200 | 15/16 | 3,000 | 15/16 | 187.5 |
| 3,200 | 1/16 | 3,600 | 1/18 | 0 |
| 3,400 | 1 | 3,600 | 17/18 | 0 |
| 3,800 | 1 | 3,600 | 1 | 200 |

This consumes both 3,600 puts and leaves `31/240` of a 3,000 put outside the vaults. That unused claim stays in the portfolio; it has not been discarded to obtain the result.

The research script verifies both this feasible allocation and an exact lower-bound certificate. The latter rules out a cheaper fractional rearrangement of this fixed inventory under the formula. It does not search all economic substitutes, additional instruments, borrowing arrangements or changes to the protocol.

Because some fractions are not representable with finite token precision, 387.5 is the optimum of a competitor-favorable continuous relaxation. It is not an exact executable token quote. The Solidity arithmetic and deployed rounding must be checked before making a transaction-level numerical claim.

### Why the lower bound is trustworthy

Assign long-token resource weights `beta(3000)=0`, `beta(3600)=225`, and short-position weights `alpha(2800)=0`, `alpha(3200)=200`, `alpha(3400)=212.5`, `alpha(3800)=425`.

For every allowed vault, its required cash plus `beta × long quantity` is at least `alpha × short quantity`. This inequality is piecewise linear in the long/short ratio: checking zero, one and the strike ratio where it lies between them proves it on every interval. Beyond a ratio of one, more longs cannot reduce margin under the formula. The script checks all these boundaries with exact fractions.

Summing across vaults gives a cash lower bound of `0 + 200 + 212.5 + 425 − 2×225 = 387.5`. The allocation above attains it. This includes unhedged shorts and unused longs, so the proof does not assume equal-sized spread legs.

## 4. The actual advantage and its limit

Asce funds `200 − B(x)`, which is nonnegative everywhere, with 200 gross backing. The optimized Gamma allocation above requires 387.5 cash, in addition to its deposited long option claims. Those option purchases and short sale receipts are included in the net premium when comparing personal cash.

For an identical positive net premium `p` below 200 and no fees, personal opening cash is:

```text
Asce:                  200 − p
Gamma fixed inventory: 387.5 − p   (continuous lower bound)
Difference:            187.5
```

The mechanism is a real accounting distinction: the full portfolio recognizes that the two payout peaks cannot happen together. Per-vault checks cannot use the complete offset in this allocation model. No production code change to Asce was needed; the existing kernel already supports the combined curve.

An ordinary interface or router that only rearranges these same Gamma puts cannot beat the proved bound. A different economic construction, another margin mode or a changed clearing rule is a stronger alternative and remains open. Do not equate this restricted result with beating every possible Gamma strategy.

## 5. Does the advantage survive exits?

Use an explicitly hypothetical opening premium of 80, zero fees, and matched package checkpoints. Give Gamma free atomic reallocations and immediate cash reuse, even though their real execution is unverified. These assumptions avoid awarding Asce an artificial execution advantage.

| Trading path | Asce peak personal cash | Optimized Gamma relaxation peak | Final loss if fully closed |
|---|---:|---:|---:|
| Open and hold | 120 | 307.5 | Depends on settlement; maximum 120 |
| Halve both for 40, then close both remaining for 40 | 120 | 307.5 | 0 |
| Close first payout for 180, later second for 180 | 300 | 307.5 | 280 |
| Close first payout for 200, later second for 200 | 320 | 320 | 320 |

Closing one entire butterfly is the matched action here, not closing one vanilla option leg. Removing individual option legs is a different task with different temporary exposures.

The last row disproves a universal lifecycle advantage even for this more promising example. Both payouts can be expensive to close at different times. At a first buyback of 200, the remaining 200 obligation plus already spent cash brings both methods to a 320 peak. A smaller opening deposit never capped later voluntary trading losses.

Prices are fixtures, not quotes. Fees, spreads, financing, setup and withdrawal delays are unmeasured. Extra trading costs can outweigh the economic benefit of releasing capital. The value of releasing 187.5 is its financing or alternative-use value over time, not an automatic 187.5 profit.

## 6. Does it beat PM, perps or mainstream options?

| Alternative | Strongest credible response | Conclusion |
|---|---|---|
| Deribit options with portfolio margin | The listed puts reproduce the normal payout. Portfolio margin evaluates the portfolio together; combo execution also exists. | No capital win established. Account-specific requirements, funded exits and all-in package prices are missing. |
| Polymarket | Compatible combo positions already support collateral return. Its documented combos combine event outcomes into YES/NO positions. | No capital win established. A finite set of fixed binary payouts cannot exactly reproduce these continuous ramps; approximating them is a different contract. This is an expressiveness distinction, not a proved reason to switch. |
| Hyperliquid perps | Cross margin shares collateral and leverage lowers initial funding. | Static linear exposure does not reproduce two bounded payoff peaks. Dynamic trading changes path risk and costs; it is not an exact terminal guarantee. No leverage superiority claim is made. |
| An exact full-portfolio funding engine | It can compute the same 200 maximum obligation. | Tie by construction. Asce cannot beat the all-outcome cash lower bound without changing a guarantee or adding another source of support. |

Sources: [Deribit portfolio margin](https://support.deribit.com/hc/en-us/articles/25944756247837-Portfolio-Margin), [combo books](https://support.deribit.com/hc/en-us/articles/31424954956061-Combo-Books), [Polymarket combos](https://docs.polymarket.com/trading/combos/overview), [collateral return](https://docs.polymarket.com/trading/combos/collateral-return), [Hyperliquid margin](https://hyperliquid.gitbook.io/hyperliquid-docs/trading/margining). Static replication limitations are mathematical deductions from the stated payoff mechanisms, not claims of having tested every product on those platforms.

Deribit's documented `private/simulate_portfolio` returns margin and risk information for simulated positions with `account:read` access. No authenticated comparison was performed, and public price books cannot substitute for it. [Simulation endpoint](https://docs.deribit.com/api-reference/account-management/private-simulate_portfolio).

## 7. Decision and next falsification

**Narrow the investigation to whole-account funding of multiple bounded structures.** Confidence is high in the exact arithmetic and limited source-level comparison; confidence in a commercially worthwhile advantage remains low because the best live alternative and recurring user need are unmeasured.

The next comparison is now concrete, rather than another generic research request:

1. Use the six listed puts above, identical expiry and asset, with seller quantities `−1,+2,−1,−1,+2,−1` at ascending strikes. Obtain read-only margin previews for the full portfolio, half size and each single remaining butterfly. Compare those with the source-level Gamma allocation and Asce backing.
2. Record the corresponding net package premiums, fees, permitted withdrawals and actual conditions for retaining the portfolio. Lower scenario margin does not automatically provide Asce's unchanged-portfolio funding guarantee; document the difference instead of silently ignoring it.
3. Look for a cheaper equivalent construction, including additional instruments or another fully funded product. If it matches the economics and guarantees, this candidate advantage weakens or disappears.
4. Ask relevant sellers to supply an actual recurring portfolio of this kind and their acceptable capital/cost tradeoff. The example is not evidence that such demand exists.

Success means a recurring user operation retains a worthwhile advantage after the strongest executable alternative, lifecycle funding and complete costs are included. Change direction if the advantage appears only against the restricted legacy vault architecture, users do not need the operation, or another route matches it cheaply. No arbitrary adoption forecast follows from the math.

Do not build a new venue, margin-token system, borrowing layer, provider matcher or larger editor on this result. Preserve the existing independent kernel and close the named comparison gaps first. No protocol adoption or integration is proposed.

## Reproduction

Run `python3 -B -m model.competitive_case` from the project root. [Script](../model/competitive_case.py) and [results](competitive-case-results.json).

The script checks the vanilla-option identity at every affine boundary and both tails, the allocation's resource constraints, the lower-bound certificate, and all four paths in the actual Asce ledger. Each path is settled and fully redeemed at eight numeric outcomes and `VOID`. The Gamma side is formula arithmetic, not a live or forked protocol execution. The output preserves these limits alongside the numbers.
