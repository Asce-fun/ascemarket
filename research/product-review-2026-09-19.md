# Repository review — 19 September 2026

## Decision

Keep the accounting kernel and narrow the next work to a faithful executable quote workflow. Do not rewrite the ledger, lower backing below the full-outcome requirement, or build the proposed AMM on its current derivation. The newer editor and explanatory documents contain concrete errors that should be corrected before they inform product decisions.

The strongest thesis is funding and trading multiple bounded shapes together on one precisely specified observation. There is a source-level advantage against some fragmented collateral architectures. There is still no demonstrated general advantage over the strongest portfolio-margin venues, no verified total-cost advantage, and no user evidence establishing the best first use case.

Reviewed the product/core/quote specs, AMM proposal, explainers, ledger/payoff model, HTTP editor adapter and frontend, tests, and competitive research. Ran `python3 -B -m unittest model.test_model -q`: all 28 tests passed. Additional direct reproductions below do not change product code. Passing tests are not a production audit; notably, these tests do not cover the newer editor adapter or AMM.

## High priority: editor cash amounts disagree with the ledger

In [server.py](../model/server.py), `combined()` already includes premium payments in the final profit profile. `evaluate()` derives a funding difference from that profile, then adds the premium again to calculate `cash_now`.

With an empty account, a claim paying 100 below 2,800 and premium 22:

| Action | Editor cash needed | Actual ledger funding helper |
|---|---:|---:|
| Buy | 44 | 22 |
| Sell | 56 | 78 |

The sell preview understates required cash. This is a real mathematical integration bug in the demo, not a failure of the ledger invariant.

There is a second source-of-truth problem: the browser's close button deletes a historical trade from `held`. It does not quote a buyback or preserve the historical premium and realized cash. The result is a scenario editor behaving like a trading account. Labelling deletion as a close teaches exactly the wrong exit semantics.

Fix direction: use a funded `W`, explicit wallet/cash history, and the ledger's candidate-balance calculation for previews. Model closing as another authorized trade. Do not merely patch the displayed sum: the current state model also assumes away actual deposits/withdrawals and history. Add meaningful regression checks for buying, selling, withdrawing and an expensive partial exit.

## High priority: the protection preset pays in the wrong direction

`QUOTES[4]` in [server.py](../model/server.py) is labelled “Protection below 3,000” but uses the increasing `ramp` constructor. It pays 0 at 2,700, 100 at 2,900, and 200 at 3,100. The intended downside protection pays the opposite way. The earlier workflow example already implements the correct descending profile.

Fix direction: share a single payout compiler/preset definition between the editor, quote examples and ledger. Test the meaning of each preset at representative low, middle and high outcomes, including VOID.

## High priority: AMM solvency guarantee is not supported as written

amm-design.md (removed v1 document) begins with finitely many outcome ticks, each with positive prior mass at least epsilon. Its bounded-loss proof requires that discrete mass. The implementation derivation then uses a continuous piecewise density and an ordinary integral. A continuous distribution has zero mass at individual points, so that proof does not apply to those prices.

Counterexample to combining the two sections: depth 1, claimed budget `log(100)`, uniform continuous density on `[0,1]`, and a sold claim paying 100 on an interval of width `10^-6`. The continuous premium is approximately 86.184489. The maker's balance inside the interval becomes `log(100) - 100 + 86.184489 = -9.210340`. The ledger would reject the trade, contradicting the stated “funding check never fails” guarantee. This does not disprove a correctly specified discrete LMSR.

There are two additional defects:

- The cost function's outcome set excludes the ledger's separately priced VOID state. If arbitrary VOID exposure is permitted, the maker can be asked to sell a claim it has not priced. Every settlement state must be included, or supported trades must be explicitly restricted with a separate solvency argument.
- Rounding prices against the maker breaks the telescoping premium identity used by the loss proof. For example, repeatedly flooring a positive sub-cent buy quote to zero gives away claims. The ledger may remain solvent by eventually rejecting them, but the guaranteed-quote claim then fails. Round the signed charge conservatively in the maker's favor using certified error bounds, or explicitly budget and bound rounding leakage.

Fix direction: if this component is retained, use one finite outcome definition consistently with the ledger, include exceptional states, and derive the discrete sum. Uniform/geometric weights on tick segments may permit geometric-series aggregation without scanning every tick. That is a possible implementation direction, not a validated replacement. Freeze depth/prior during the proof or account explicitly for parameter changes. A tiny backstop also cannot promise economically useful exits merely because an executable price exists.

Primary background: [Hanson's market scoring rule paper](https://hanson.gmu.edu/mktscore.pdf). The counterexample above is an independent calculation against this repository's proposed formulas.

## Medium priority: the explanations overstate what follows from the math

1. **A seller need not have one unique worst outcome.** The original tail example already has multiple worst regions. Further, a new sale away from the old minimum may create a new minimum. A profile paying 0 below 0, 10 on `0,1)`, and 100 above 1 becomes underfunded by 10 after selling a 20 payout on `[0,1)` at zero premium. The old worst region was untouched. Replace the “free trade away from your worst day” explanation with a full funding-slack calculation. Zero incremental backing also does not imply zero expected loss or free economic risk. [Explainer (removed v1 document).

2. **Finite trade prices are not automatically probabilities.** A normalized, coherent marginal pricing measure can have a probability interpretation. Size-dependent quotes, fees, spreads and discounting require qualifications. Even a symmetric two-state LMSR with depth 1 has marginal probability 0.5 but charges about 0.620115 for a one-unit claim. The representation alone does not produce a uniquely identified real-world distribution. Product spec (removed v1 document), core design (removed v1 document), AMM proposal (removed v1 document).

3. **Export is not strictly more expensive in every case.** Separating offsets can increase required backing; exporting an already independently funded claim need not do so. Whole-profile transfer is already acknowledged as preserving offsets. State a conditional/nondecreasing cost claim for a specified export construction, not a universal strict inequality.

4. **Reduced capital does not automatically triple returns or lower buyer prices.** Capital denominators, holding periods, loss paths, financing and provider competition matter. Some benefits may remain with sellers; passes to customers must be measured. Fee rebates redistribute revenue and are not newly generated yield.

## Medium priority: narrow the Polymarket claim to what was tested

The new [NegRisk comparison](negrisk-case.md) is useful for the selected adapter operations and market layout. A numeric observation can express offsets that two independently declared partitions do not automatically certify. That is a plausible architectural distinction.

However, searching legal conversion masks from the current holdings is not an exhaustive search over trading, token purchases, refinements and all current venue mechanisms. The public [collateral-return documentation](https://docs.polymarket.com/trading/combos/collateral-return) describes a broader decomposition and residual-position workflow. This does not prove that it solves the example; it means the old adapter alone cannot establish a platform-wide impossibility claim.

Also, `scaling()` in [negrisk_case.py](../model/negrisk_case.py) starts the adapter at collateral 1 without inserting its carried middle YES token into its holdings, and it does not check terminal payoff equivalence after each refinement. The collateral tally can still match the intended restricted example, but that branch is not the fully reconciled comparative lifecycle its presentation suggests. Zero-premium repeated sales are accounting fixtures, not evidence of arbitrarily large economic gains. Finite integer boundary precision also limits that particular halving loop.

Fix direction: carry the actual initial holdings; check net cash plus terminal payout equality at every step; test current relevant mechanisms; retain the conclusion as restricted until then.

## Improvements worth pursuing

### 1. Make proportional whole-profile exits a first-class quote

An account owns nonnegative final payout `W(x)`. Selling fraction `a` of that complete payout for price `p`, with fee `f`, leaves `(1-a)W(x) + p - f` before withdrawal. When `0 <= a <= 1` and `p >= f`, the seller needs no new deposit; withdrawing `p-f` leaves a funded residual.

This is a useful structural guarantee: reducing the whole funded profile preserves its offsets. It does not guarantee a buyer, a good price, or zero funding for the counterparty. Closing one obligation while retaining another is a different request and may still need cash. The current batch kernel can express this operation; no new collateral primitive is needed.

### 2. Quote using the maker's full inventory and funding slack

For each proposed change, compute the complete resulting minimum after consideration and fees. Show where funding is tight and where obligations can be added without another deposit. Match useful incoming trades to existing inventory and compare complete packages. The target is lower actual funding cost and executable prices, not artificially cheap risk.

For fixed desired exposures and all-outcome cash guarantees, the engine already reaches the funding floor. Improvements come from finding real offsets, maintaining them through execution and reusing genuinely released cash. They do not come from a more optimistic minimum calculation.

### 3. Transfer guaranteed floors across markets atomically

If `g = inf W >= 0`, withdrawing `g` from one account and depositing it into another market is safe when both updates and escrow movements commit together. Subtract it from the source: never promise the same funds twice. This improves cash movement and can help rollovers, but creates no additional capital beyond the existing withdrawable floor. Most risky hedges may have a zero floor, so it will not eliminate all rollover funding.

### 4. Preserve netting while making quotes usable

One maker fill currently invalidates its other same-account revision-bound quotes. Splitting inventory into separate accounts to avoid this can lose the very netting the product sells. Measure this conflict on the intended workflow before choosing reservations or batch matching. Any reservation policy must cover jointly executable commitments; quoting each against the same free cash is unsafe.

### 5. Concentrate the first product on one observation family

Supporting arbitrary scalar measurement rules is a valid abstraction. Launching many unrelated observations immediately does not improve capital efficiency: their funds cannot share the exact offsets of one observation. Prefer a setting where users repeatedly hold several compatible shapes and where entire-position exits matter. Expanding to rates, weather or compute should follow a concrete use case rather than substitute for one.

## Recommended order

First correct the demo's cash/history semantics and protection preset, and quarantine the unsupported AMM guarantee. Next demonstrate inventory-aware package quotes and proportional funded-profile exits with actual ledger transitions. Then compare those complete tasks and costs against a strong alternative using a real portfolio. Keep pricing, fees, collateral and guarantees separately measured.

The kernel remains promising research infrastructure. The product has not yet shown that users receive a sufficiently valuable improvement to choose a new venue. No accounting rewrite, broad expansion or additional collateral risk is warranted by the current evidence.
