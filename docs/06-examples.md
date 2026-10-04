# Worked numerical examples

All amounts are illustrative USDC units, executed in the Python ledger with 1,000,000 base units per displayed unit. Premiums are stipulated inputs, not fair-value estimates. No correlation or probabilities enter the collateral calculation. Each example locks its state space before trading.

Reproduce with `python3 -B -m simulations.portfolio_examples`. [Machine-readable results](../simulations/results.json). The new [native CTF test](../research/ctf/run-state-clearing-baseline.cjs) executes A and C independently.

## A. Three curves, one maker, five normal states

Use BTC's specified December observation. The canonical ranges use explicit half-open boundaries. The ambiguous shorthand “>120k” in an interface is not a substitute for these contractual ranges.

| State | A: downside | B: upside | C: middle cover | Aggregate liability | Maker settlement equity with 11,000 cash |
|---|---:|---:|---:|---:|---:|
| `x < 80,000` | 10,000 | 0 | 1,000 | 11,000 | 0 |
| `80,000 ≤ x < 100,000` | 6,000 | 0 | 5,000 | 11,000 | 0 |
| `100,000 ≤ x < 120,000` | 2,000 | 2,000 | 6,000 | 10,000 | 1,000 |
| `120,000 ≤ x < 150,000` | 0 | 7,000 | 4,000 | 11,000 | 0 |
| `x ≥ 150,000` | 0 | 10,000 | 0 | 10,000 | 1,000 |
| `INVALID` under the illustrative zero-payout policy | 0 | 0 | 0 | 0 | 11,000 |

Vectors include INVALID:

```text
A = [10000, 6000, 2000,    0,     0, 0]
B = [    0,    0, 2000, 7000, 10000, 0]
C = [ 1000, 5000, 6000, 4000,     0, 0]
L = [11000,11000,10000,11000, 10000, 0]
```

Define gross notional here as **sum of individual maximum payouts**, since no underlying token notional is specified: `10,000+10,000+6,000=26,000`. Naive separately capped backing is also 26,000. State-aware backing is 11,000. Saving is **15,000, or 57.69%** against that separate-funding control.

Let premiums be A=2,300, B=2,600, C=2,100, totaling 7,000. With one atomic issuance, the maker contributes 4,000; buyers contribute 7,000; event escrow is 11,000. Maker cash is 11,000, exposure is `−L`, and its minimum entitlement is zero. Buyer cash after purchase is zero and buyer exposure is its full cover. Every state in the table exhaustively settles all accounts without a top-up.

At settlement maker economic PnL is `7,000−L[k]`: losses of 4,000 in states 1, 2 and 4; losses of 3,000 in states 3 and 5; profit of 7,000 on INVALID. Maker equity above is the remaining claim after its original 4,000 contribution, not PnL.

Zero INVALID payouts are a deliberately simple prototype contract. They do not refund buyer premiums. A commercial cancellation/refund policy must be explicitly encoded and fully funded; it cannot be decided after trading.

### Same curves under CTF

Mint 11,000 units of each of the six atomic claims from one 11,000 collateral split. Distribute A, B and C's state amounts. Retain maker residual:

```text
[0, 0, 1000, 0, 1000, 11000]
```

This is exactly the maker equity column. Native CTF does not need 26,000 for these buyers. The EVM runner confirms every buyer and maker payout in all six states, with zero remaining CTF escrow after redemption.

### Opening order and personal capital

| Executed checkpoint | Backing required | Cumulative premiums | Net maker contribution if free cash is withdrawn |
|---|---:|---:|---:|
| A alone | 10,000 | 2,300 | 7,700 |
| A then B | 10,000 | 4,900 | 5,100 |
| A then B then C | 11,000 | 7,000 | 4,000 |
| All three atomically | 11,000 | 7,000 | 4,000 |

Sequential peak is **7,700**, rather than 4,000. Both end at the same portfolio. A prefunded native CTF inventory also has a larger initial funding checkpoint, but an authorized buyer-funded atomic issuance can avoid it; this is not an unavoidable difference between CTF and internal clearing.

## B. Nested and overlapping scalar claims

Before trading this example, refine the domain to preserve the strict predicate `BTC > 120,000`. Unlike `≥`, it excludes the exact boundary. Keeping a singleton boundary state prevents silently changing the contract.

Claims: D pays 4,000 if `x<80,000`; E pays 6,000 if `x<100,000`; F pays 5,000 if `80,000≤x<120,000`; G pays 7,000 if `x>120,000`. All pay zero on INVALID. Premiums are zero solely to isolate backing arithmetic.

| Atomic state | D | E | F | G | Aggregate | Maker equity from 11,000 |
|---|---:|---:|---:|---:|---:|---:|
| `x<80,000` | 4,000 | 6,000 | 0 | 0 | 10,000 | 1,000 |
| `80,000≤x<100,000` | 0 | 6,000 | 5,000 | 0 | 11,000 | 0 |
| `100,000≤x<120,000` | 0 | 0 | 5,000 | 0 | 5,000 | 6,000 |
| `x=120,000` | 0 | 0 | 0 | 0 | 0 | 11,000 |
| `120,000<x<150,000` | 0 | 0 | 0 | 7,000 | 7,000 | 4,000 |
| `x≥150,000` | 0 | 0 | 0 | 7,000 | 7,000 | 4,000 |
| `INVALID` | 0 | 0 | 0 | 0 | 0 | 11,000 |

Summed caps are 22,000. Maximum joint liability is **11,000**. Saving is **11,000, or 50%**. D is nested in E, so both pay below 80k; their required joint payment is 10,000, not merely the larger individual cap. E and F overlap in the second state, creating the overall 11,000 maximum. No pairwise relationship is substituted for the whole-state sum.

The ledger settles all seven states. A common categorical CTF condition for this predeclared partition can reproduce the same atomic allocation. A and B are separate example setups; B does not mutate A's traded partition or assume their different condition IDs are freely nettable.

## C. Partial close and actually released cash

Start from Example A's minimal funded account: cash 11,000 and liabilities `L`. The C buyer sells half its cover back to the maker for a stipulated 400. Exact per-state amounts halve; no fractional quantity rounding is needed. The adapter cancels the old C lot and replaces it with an immutable half-sized cover, atomically.

```text
remaining C = [500,2500,3000,2000,0,0]
remaining L = [10500,8500,7000,9000,10000,0]
```

Required backing falls from 11,000 to **10,500**. Maker cash after buyback is `11,000−400=10,600`. Free cash is **100**. After that withdrawal, maker cash is 10,500, and the buyer can withdraw its 400 proceeds.

| State, ordered as A | Remaining A | Remaining B | Remaining C | Maker final equity | Sum of remaining entitlements |
|---|---:|---:|---:|---:|---:|
| 1 | 10,000 | 0 | 500 | 0 | 10,500 |
| 2 | 6,000 | 0 | 2,500 | 2,000 | 10,500 |
| 3 | 2,000 | 2,000 | 3,000 | 3,500 | 10,500 |
| 4 | 0 | 7,000 | 2,000 | 1,500 | 10,500 |
| 5 | 0 | 10,000 | 0 | 500 | 10,500 |
| INVALID | 0 | 0 | 0 | 10,500 | 10,500 |

Prior withdrawals of 400 to the C buyer and 100 to the maker are already removed from these remaining claims and escrow. They are not paid twice at settlement. Remaining summed caps are 23,000, so remaining state-aware backing saves **12,500** versus separate caps.

For C's closed half, allocated entry premium is 1,050 and exit proceeds 400: buyer realized loss 650 before fees. The maker realizes the corresponding 650 on that closed portion; its remaining exposure is still contingent.

The native CTF control buys back half of C's basket, increasing maker inventory to `[500,2500,4000,2000,1000,11000]`. The minimum atomic balance is 500; merging that complete set releases 500 collateral. The 400 buyback leaves the same **100 net cash release** and 10,500 CTF backing.

### Two important counterexamples

- At a buyback price of 1,000 instead, maker cash becomes 10,000 while liability is 10,500. The voluntary close must reject unless the maker authorizes a **500 deposit**. That is a transaction funding need, not price-triggered liquidation of the existing portfolio.
- Closing half of A instead leaves aggregate liability `[6000,8000,9000,11000,10000,0]`. Maximum liability remains **11,000**. Reduced gross position size does not guarantee any backing release.

## D. Received premiums: income versus withdrawable capital

The same 7,000 premiums have different withdrawal consequences depending on actual deposited capital:

| Funding history | Maker deposit | Received premiums | Maker cash after trade | Required backing | Immediately free |
|---|---:|---:|---:|---:|---:|
| Fully prefunded maker | 11,000 | 7,000 | 18,000 | 11,000 | 7,000 |
| Minimum atomic contribution | 4,000 | 7,000 | 11,000 | 11,000 | 0 |

In the first case, the maker can withdraw 7,000, leaving its own full backing in place. In the second, the premiums themselves help fund buyer payouts and cannot be withdrawn. A rule that “premiums are always immediately withdrawable profit” is insolvent.

With a 200 maker-paid fee, the minimum contribution becomes **4,200**. Cash before fee is 11,200; transfer 200 internally to treasury; maker retains 11,000. Event escrow is 11,200 while treasury's 200 remains inside it. Treasury can withdraw that 200, leaving 11,000 backing. The fee cannot silently reduce buyer payout funding.

## Failure-state sensitivity

Two exclusive 100-cap claims normally need 100 backing. If each pays 60 on cancellation, the cancellation liability is 120. Required backing is **120**, even if cancellation is thought unlikely. Both the existing CTF fixture and the new arithmetic tests check this relationship. A settlement guarantee is only as complete as the contractual state table.
