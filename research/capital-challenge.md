# Capital efficiency across the full lifecycle

Research date: 17 September 2026. Reproduction: `python3 -B -m model.capital_challenge --output research/capital-results.json`.

## Verdict

**The capital saving from recognizing offsets is real. It can shrink or disappear when the user closes positions individually. Our engine matches an equally capable exact-netting reference; this investigation does not establish a unique funding advantage over a deployed competitor.**

An extra deposit during an exit does not, by itself, mean netting was inefficient. The independently funded alternative may already have required that money at opening. Compare the largest total amount needed throughout the path, not the number of deposit requests.

The strongest demonstrated result remains efficient funding of compatible exposure. The unresolved product claim is whether AsceMarket recognizes useful offsets or supports funded changes that particular competing systems cannot handle as well.

## Method and limits

Executed the existing account ledger and compared every trade checkpoint with a separately calculated reference. The reference uses outstanding quantities and cumulative trade cash flows; it does not use the ledger's payout evaluator or minimum calculation. A second reference funds each obligation separately. All methods receive identical quantities, prices, execution groupings and fees.

The original contracts pay 100 below 95 or at/above 105, respectively, on one final observation. Both pay zero in the middle and on VOID. Opening premiums are 22 and 32. These are stipulated prices. The methods hold identical obligations after every matched action.

For outstanding quantities `q_low` and `q_high`:

```
Exact backing = 100 × max(q_low, q_high)
Separate backing = 100 × (q_low + q_high)
Net personal cash committed = backing − cumulative net premiums received + fees
Peak personal capital required = max(0, net cash committed at every checkpoint)
```

These formulas apply to the disjoint, nonnegative obligations in this challenge, not arbitrary portfolios. The same independent calculation was checked on disjoint capped ramps at ten settlement results.

Peak capital is the minimum starting cash needed to complete that path without borrowing, assuming released cash is immediately reusable. It includes money lost on earlier trades as well as money still committed. It is not the sum of all deposits: withdrawn money can be recycled. The results also record gross deposits and every cash movement separately.

Withdraw all guaranteed cash after each action. Assume enough external cash can be supplied when a path requires it; separately test failure when only the initial deposit is available. No withdrawal delays, financing charges, price changes within an assumed atomic package, or margin liquidation are modeled. The fragments reference is allowed the same package execution as AsceMarket, so this comparison does not give AsceMarket an artificial execution advantage.

Every path reaches settlement or closes all obligations, then redeems all accounts. Fees are transferred to treasury, not discarded. [Machine-readable results](capital-results.json), [implementation](../model/capital_challenge.py).

## Three matched lifecycle results

Zero fees for the accounting comparison. Initial opening is a single package unless specified otherwise.

| Lifecycle | AsceMarket peak capital | Exact-netting reference | Separately funded obligations | Final trading loss, same for all | Result |
|---|---:|---:|---:|---:|---|
| Hold both through a tail settlement | 46 | 46 | 146 | 46 | Win versus separate funding; tie versus exact netting |
| Halve both together, then close the remainder together at original prices | 46 | 46 | 146 | 0 | Win versus separate funding; tie versus exact netting |
| Close low for 90, then later close high for 90 | 136 | 136 | 146 | 126 | Smaller win versus separate funding; tie versus exact netting |

Holding through a middle or VOID settlement gives a profit of 54 instead of a loss, but does not change opening peak capital. Results are in illustrative currency units. They are not recorded competitor account balances.

### The reversal case, cash movement by cash movement

| Action | Asce: additional deposit / withdrawal | Asce: cumulative net cash committed | Separate funding: additional deposit / withdrawal | Separate funding: cumulative net cash committed |
|---|---:|---:|---:|---:|
| Open both | Deposit 46 | 46 | Deposit 146 | 146 |
| Buy back low for 90 | Deposit 90 | 136 | Withdraw 10 | 136 |
| Later buy back high for 90 | Withdraw 10 | 126 | Withdraw 10 | 126 |

Both methods lose 126 on that trading sequence. AsceMarket needed 136 at its peak; the separate method needed 146. The deposit request is real friction, but the comparison shows where the money was needed in each method.

With only 46 available, the model rejects the first individual exit and preserves all state. It does not promise that every exit is affordable from the original deposit. A user can supply the additional funding, request a different complete portfolio change, or retain the position. Closing both earlier is not an equivalent solution if the user specifically wants to keep the high obligation until later.

### Opening execution matters too

| Opening method, same final portfolio | Asce/exact reference peak capital before settlement | Capital committed after both trades |
|---|---:|---:|
| Open both atomically | 46 | 46 |
| Open low, then high | 78 | 46 |
| Open high, then low | 68 | 46 |

Earlier documentation's 46 describes the completed portfolio. It must not be reported as the lifecycle peak for a sequential opening. An equally capable package mechanism can match the atomic row. These are full-leg orderings; smaller interleaved fills are another comparison and can change temporary funding at the cost of more executions.

## Adverse paths and fees

Checked **625 reversal price pairs**, independently varying each buyback from 0 to 120 in steps of 5. Prices above 100 are included because an offered exit price can exceed a claim's maximum payout. A trader can decline it; the model should still account correctly if the trader authorizes and funds it.

If the low and high buybacks are `a` and `b`, respectively:

```
Asce/exact peak = max(46, 46 + a, a + b − 54)
Separate peak   = max(146, 46 + a, a + b − 54)
```

All 625 paths tied the exact reference. Savings against separate funding ranged from 0 to 100. For example, a first buyback of 100 brings both methods to 146; the initial saving is completely gone at that checkpoint.

There is a limited mathematical conclusion here: with identical cash flows, fees and execution checkpoints, exact backing never exceeds separate backing. Taking the maximum over time preserves that inequality. This does **not** prove lower total cost against a real venue: different fees, available prices, collateral rules, execution groupings or withdrawal delays can change the result.

A sensitivity run charges the same hypothetical fee of 1 per executed batch to each method:

| Path | Asce/exact peak | Separate peak | Total fees | Final loss |
|---|---:|---:|---:|---:|
| Hold through tail settlement | 47 | 147 | 1 | 47 |
| Halve and close through packages | 47 | 147 | 3 | 3 |
| Reversal exits | 138 | 147 | 3 | 129 |

This is a sensitivity test, not a venue fee schedule or proposed Asce pricing. A smaller apparent collateral requirement does not compensate automatically for higher spreads or fees.

## What actual competing rules establish

**Kalshi:** eligible mutually exclusive positions can receive early collateral return based on their guaranteed combined payout. Mapping our two shorts into purchases of their complementary NO claims gives 78 + 68 = 146 upfront claim cost, with 100 guaranteed across outcomes; the net requirement is 46 before fees under that rule. This is an application of the published rule, not a live account test. Kalshi also warns that returned collateral can restrict later sales, and eligibility is fixed for an event when its first order is placed. The precise funding/unlock behavior for our exit sequence was not verified. [Collateral Return](https://help.kalshi.com/en/articles/13823816-collateral-return).

**Deribit:** standard margin computes position requirements separately, while portfolio margin tests the portfolio together using price/volatility scenarios and risk charges. Neither should be equated to our separate-full-funding reference. A scenario-margin requirement is also not the same guarantee as full funding through every possible settlement result. We did not obtain account-specific requirements for the tested portfolio, so a numeric claim of superiority against Deribit would be unsupported. [Standard Margin](https://support.deribit.com/hc/en-us/articles/25944811528477-Standard-Margin), [Portfolio Margin](https://support.deribit.com/hc/en-us/articles/25944756247837-Portfolio-Margin).

The exact reference is therefore a meaningful accounting control, not a claim that every competitor implements its exit semantics. Kalshi's documented holding rule can match the opening saving. The real comparative question is which funded changes remain available afterward.

## Public option-price check

Captured four Deribit books for 25 September 2026 ETH_USDC options. Exchange timestamp: **17 September 2026, 14:56:34.556 UTC**, roughly 1.4 seconds before retrieval. Displayed best-level quantities exceeded one unit on each side. Retained source URLs, timestamps, depth and raw-response hashes in [the snapshot](capital-market-snapshot.json).

| Instrument | Bid | Ask |
|---|---:|---:|
| Put 2,700 | 238 | 252 |
| Put 2,800 | 333 | 347 |
| Call 3,000 | 1.4 | 2.0 |
| Call 3,100 | 0.8 | 1.4 |

Sell the 2,800 put / buy the 2,700 put, and sell the 3,000 call / buy the 3,100 call. Each bounded spread has maximum payout 100; their positive payout regions do not overlap. These are ramps, not the binary contracts in the earlier table.

Using the appropriate displayed sides, opening credit is `333 − 252 + 1.4 − 1.4 = 81`. Immediate closing cost is `347 − 238 + 2.0 − 0.8 = 110.2`. Fees are additional. These are candidate leg-crossing prices, **not a guaranteed package quote**. A package market or patient execution may offer a better price. Deribit documents package execution; a simple sum of leg quotes is not its best attainable package price. [Combo Books](https://support.deribit.com/hc/en-us/articles/31424954956061-Combo-Books).

Replaying those prices through the accounting model gives:

| Assumed execution path | Asce/exact peak | Separate-funding peak | Final loss before fees |
|---|---:|---:|---:|
| Open and close as complete packages at the derived prices | 29.2 | 119 | 29.2 |
| Open as a package; close the low spread, then the high spread | 128 | 128 | 29.2 |

The opening exact requirement is 19. Buying back the low spread at the displayed leg prices costs 109, pushing its subsequent net funding requirement to 128 while the high spread remains. Both methods reach the same peak on that path. This is a replay of one snapshot, not observed trading, a simulated reversal in actual history, or proof that a provider would quote these prices on AsceMarket.

The useful observation is that **a fully funded position's maximum settlement loss does not cap the cost of choosing an early exit at an unfavorable quote**. A cheaper exit cannot be promised merely by improving collateral accounting.

## What is complete and what remains unknown

Completed the matched three-scenario challenge, opening-order controls, fee sensitivity, 625 reversal paths, ten ramp settlement checks, insufficient-funds rejection, and a saved public-price replay. Every executed model path reconciled backing and final cash. These are checks, not a formal proof or production audit.

Unmeasured: authenticated competitor margin previews; whether additional funds unlock a specific netted exit on Kalshi; firm package quotes; Asce provider prices; actual fills; real fees, withdrawal timing and financing cost. The public books cannot supply those answers. No trades or account changes were made.

## Decision

**Do not claim that AsceMarket has already beaten the best available capital treatment.** It wins the separate-funding control and ties exact netting. Some stressful exit paths erase the separate-funding saving entirely.

The narrower thesis worth investigating is: **exact funding across custom compatible payouts, with clearly defined ways to exit or reshape them when the resulting portfolio is funded.** The next empirical discriminator is a competing venue's actual funded-exit behavior, not another variation of the 146-versus-46 opening example.

Before a larger build, demonstrate at least one recurring portfolio operation where a named competitor requires more peak capital or blocks a funded change that our design can execute, under matched contract terms and acceptable total cost. If that evidence is absent, capital efficiency alone has not justified a standalone product. Keep the current kernel; adding an editor or more infrastructure does not answer this question.
