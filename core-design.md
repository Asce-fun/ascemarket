# AsceMarket core engine

## Decision and scope

The first engine is an account ledger for **bounded payouts on one numeric observation**. Its central operation is an authorized, atomic change from each participant's current payout to a new payout.

Use a compact payout function for the reference ledger. Keep an explicit interval table as an independent mathematical comparison. Neither representation requires an existing token protocol. Pricing stays outside the accounting kernel.

This document specifies an executable research model, not a production exchange. It tests accounting, representation and execution funding. It does not implement wallets, cryptographic signatures, price discovery, external settlement reporting, a blockchain or real money transfers. The model uses Python's standard library and exact rational arithmetic.

The product direction is described in [ps.md](ps.md). The reference implementation and reproducible checks are in [model/README.md](model/README.md).

### Read this first: what the system promises

**Fund the maximum possible settlement loss of the current compatible portfolio. Recheck funding whenever that portfolio changes.**

People trade promises about one final observation. Some promises offset: a low and a high result cannot happen at the same final observation. The engine recognizes those contractual offsets and keeps enough money to pay every permitted outcome. An amount guaranteed to remain in an account under every outcome can be withdrawn.

Prices offered for trading those promises can change before the final observation. A low-outcome promise can become expensive today and a high-outcome promise can become expensive tomorrow. Closing them at those different times can lose money on both. An exit is a new trade, so the engine checks the remaining portfolio and the exit payment together. It may require an additional, explicitly authorized deposit.

An unchanged, fully funded portfolio does not need more money merely because market prices move. The original deposit is **not a lifetime loss limit across later trading decisions**. Nor does an open trading window promise that every individual exit is available or affordable. A provider must quote the change, and every resulting account must remain funded.

This is an independent account-engine design. Other protocols and venues are comparison baselines, not required dependencies. Capital efficiency is a core thesis; easier editing is a supporting workflow. The [lifecycle capital challenge](research/capital-challenge.md) establishes savings over separately funded obligations and parity with an exact-netting reference. A capital advantage over a named deployed competitor remains unverified.

### Keep these amounts separate

| Amount | Meaning |
|---|---|
| Final account payout | What the account receives at settlement for a particular result; includes its retained cash and net claims |
| Gross obligation | What the seller's outstanding promises could require before considering premiums already received |
| Net personal cash committed | Cumulative deposits minus withdrawals for the account; can include losses already incurred, so it is not simply remaining collateral |
| Withdrawable cash | The amount the account can release while its remaining final payout stays nonnegative in every permitted result |
| Peak capital required | The largest net personal cash commitment reached during the entire trading path, floored at zero, assuming withdrawn money is immediately reusable |
| Worst settlement loss | The loss if the current portfolio is held to settlement, measured from an explicitly stated cash-history basis |

For an account that started with no position, let `N` be cumulative deposits minus withdrawals, and `W(x)` the remaining final payout. If there are no further trades or costs, total profit from that history through settlement is `W(x) - N`. Maximum total loss on that basis is `max(0, N - inf(W))`. A new trade changes this calculation. Neither `W` nor a quoted sale value should be labelled profit by itself.

## 1. The account invariant

Let `x` be the final numeric observation. Let `W_i(x)` be the amount that account `i` receives at settlement, including its cash and all outstanding claims and obligations. Let `C` be the market's escrow balance.

For every permitted result:

```
W_i(x) >= 0                for each account i
sum_i W_i(x) = C
```

There is also an explicit exceptional result, `VOID`. Each profile has a separately specified `W_i(VOID)`. The same two invariants apply to it. `VOID` does not reverse transaction history or refund historical premiums.

The maximum amount an account can withdraw is the infimum of its final balance across numeric results and `VOID`. An infimum is used because a step can jump before a limiting value is reached; any negative limiting value would still imply negative balances at nearby permitted results.

An account is a nonnegative entitlement to future cash. It is not an additional claim on top of separately counted collateral. Summing both would double-count backing.

### Reading the invariant as a state space

`W_i` is a function from permitted results to amounts. Each permitted result is a state, and each account holds one vector over those states. This is the Arrow–Debreu formulation, and three properties of the engine follow from it directly rather than being added as rules.

**Combination is addition.** Two claims on the same observation are two vectors over the same states, so the engine evaluates their sum. It requires no rule naming which pairs offset. A short claim on one event and a long claim on a superset of that event net exactly, for the same reason that a low tail and a high tail net exactly: the resulting vector is what it is. An instrument-based ledger has to recognize each such relationship explicitly; this one cannot fail to see it.

**Funding is a single scalar of the vector.** The collateral requirement is `max(0, -inf W_i)`, a property of the account's whole vector rather than of any position within it. Positions therefore have no individual collateral requirement, which is what makes the netting exact and also what makes positions non-separable (section 9).

**Prices induce a measure.** If the traded claims span the state space and quotes admit no arbitrage, the prices define an implied distribution over results. The price of `range(a, b, 1)` is the implied probability mass on `[a, b]`. This model prices nothing and establishes no such quotes; the observation is about what the representation permits a pricing layer to express.

Completeness holds within one observation only. Vectors over different observations live in different spaces, which is the same fact recorded in section 2 as the absence of cross-market offsets.

### Deposits, payments, fees and withdrawals

- A deposit of `d` adds `d` to every value of the depositing account and adds `d` to escrow.
- A trade transfers a payout profile between accounts. A premium is a separate transfer of a constant balance between them.
- A fee subtracts a constant from its payer and credits the same constant to a treasury account. It cannot disappear from the conservation calculation.
- A withdrawal of `r` subtracts `r` from every value of the account and from escrow, provided the remaining profile is nonnegative.

External wallets are exact cash balances in this model. They cannot be overdrawn. Model setup may endow a new participant's wallet; ordinary ledger operations cannot create funds.

## 2. Market identity and payout semantics

The model has one immutable market identifier, a settlement asset identifier, an integer trading-close timestamp, numeric outcomes and `VOID`. A production market identifier must bind the complete observation and settlement specification, including exceptional-state policy and numeric precision.

### What the observation may be

The engine requires exactly one scalar result per market, determined at expiry. It does not require that result to be a spot price read at an instant.

The settlement value `x` may be any scalar functional of an observable path, fixed in the market specification before trading opens:

- a terminal price at a stated time,
- a time-weighted or volume-weighted average over a stated window,
- an average borrow or lend rate accrued over a stated period,
- a realized variance or range over a stated window,
- a cumulative quantity, such as rainfall or metered consumption,
- an extremum over a stated window, such as the maximum price reached.

The accounting kernel is unchanged in every case. It evaluates `W_i(x)` at a single final `x` and never inspects the path that produced it. Nothing in sections 1, 3, 4, 5 or 8 depends on how `x` is computed.

Three requirements attach to the choice:

1. The functional is fully specified before trading opens, including source, sampling times, interpolation, missing-data treatment and rounding to the settlement lattice.
2. It resolves to a single value at expiry. A functional whose value is knowable before trading closes creates a settled-information race, so the trading-close timestamp must precede the end of the observation window.
3. The payout remains bounded. A linear rate or variance exposure requires an explicit cap and floor to be expressible here; uncapped notional exposure is not.

This widens the product surface without widening the kernel. A collared exposure to an average rate is an ordinary `ramp` on an average-rate observation, not a new instrument class. The choice of functional also affects how expensive the reported value is to influence, but that property belongs to the observation source and is not established by this document.

“Compatible” means the promises share this market's observation, settlement asset and outcome rules. The engine checks their combined payout under every permitted result; it does not assume that historically correlated prices will continue moving together. Different expiries or observations do not receive cross-market offsets in this design.

The observation determines the final payout. Path dependence, where it is wanted, belongs in the observation functional rather than in the payout language: a contract sensitive to whether a level was ever reached is expressed by settling on the window's maximum, not by giving `step` new semantics. The payout stays a plain function of one final scalar, and the funding checks are unaffected. Given a terminal-price observation, passing below 95 today and above 105 tomorrow does not trigger both final-outcome promises. Trading prices can nevertheless make both promises expensive to close at different times, whatever the observation.

The mathematical numeric domain is the real line. Profiles have constant tails and finitely many breakpoints. Implementation inputs and evaluation points are exact rational values. Binary floating-point inputs are rejected.

The initial language is right-continuous:

- `step(k, a)` pays `a` for `x >= k`, otherwise zero.
- `range(lo, hi, a)` pays `a` for `lo <= x < hi`, otherwise zero.
- `ramp(lo, hi, a)` is zero below `lo`, rises linearly to `a` at `hi`, then remains `a`.
- Addition, subtraction and rational scaling combine these profiles.
- Each nonconstant constructor requires an explicit `VOID` payout. Constants have the same value in numeric and exceptional outcomes.

Exact-point-only payouts and other boundary conventions are outside this model. A bounded function cannot have a nonzero slope extending to infinity. Cancellation terms must be supplied when constructing the payout; the engine does not invent them later.

The examples use zero `VOID` payouts for the traded claims. Consequently a void can return the remaining escrow to a seller without refunding buyers' premiums. This is an explicit illustrative contract term, not a recommendation for a live market's cancellation policy. Tests also use different exceptional payouts to check that the engine cannot ignore them.

## 3. Compare the representations

### Candidate A: an explicit interval table

Fix the sorted union of all relevant boundaries. For each interval, store its value at the left boundary and its limiting value at the right boundary. Store constant tails and a separate `VOID` value. The two sides of a boundary can differ.

This is a complete table of affine intervals, not sampled prices on a grid. It represents the specified functions exactly, including jumps. A coarse table that lacks a required boundary cannot express the new payout exactly.

Adding a boundary to a shared table requires refining the representation of accounts that use that table, even when their economic payout is unchanged. Table addition is straightforward when axes match. The minimum is the smallest stored endpoint or exceptional value.

A stronger table alternative gives each account its own interval axis. It avoids global refinement too, at the cost of aligning two local axes when combining profiles. The model benchmarks this alternative as well. Locality is a property of account-local storage, not a unique advantage of the coefficient representation.

### Candidate B: a compact function per account

Represent the numeric payout as:

```
W(x) = base + sum_k [jump_k * 1(x >= k) + slope_change_k * max(x - k, 0)]
```

Store sorted, unique boundaries with nonzero coefficients. Combine coefficients at equal boundaries and remove zero terms. The sum of slope changes must be zero, giving constant tails. `VOID` is stored separately.

This normal form means equivalent expressions normalize to the same coefficients. A trade can introduce a boundary in the affected accounts without changing other accounts or expanding a global outcome array.

To compute extrema, sweep from left to right. Between boundaries the function is affine, so extrema occur at interval endpoints or their limits. At every boundary inspect both the value before its jump and the value after it. Include both tails and `VOID`.

| Property | Shared interval table | Compact account function |
|---|---|---|
| Exact steps and ramps | Yes, if all needed boundaries are present | Yes |
| New boundary | Refine the shared axis and materialized tables | Add terms to affected accounts |
| Per-account stored numeric values | Grows with the shared boundary count | Grows with that account's boundaries |
| Minimum check | Linear in table size | Linear in account boundaries |
| Straightforward arithmetic | Elementwise on a common axis | Normalize and combine coefficients |
| Main tradeoff | Simple but can expand unrelated accounts | Compact but rational coefficient arithmetic has a cost |

**Choose Candidate B for the reference ledger.** The current normalization uses sorting and is `O(k log k)` in the number of input terms; evaluation and extrema sweeps are `O(k)`. Rational numerator and denominator growth adds cost not captured by the term count. There is no claim of logarithmic account updates or onchain affordability.

This choice favors canonical cancellation and additive composition. A local interval table can scan precomputed endpoint values with less arithmetic. Keep the representation decision reversible; these measurements do not establish that coefficients are the fastest production structure.

The independent table evaluator is constructed directly from elementary expressions for differential tests. It does not obtain its expected values from the compact evaluator. Benchmarks separately materialize a fixed profile on increasingly large shared axes to measure the representation tradeoff.

## 4. What a participant authorizes

An immutable batch contains:

- Market identifier and expiration timestamp.
- One change per explicitly participating account.
- For each change: account identifier, expected revision, signed payout change, signed premium payment and signed external cash flow.
- Explicit fee payers and amounts. The market's configured treasury receives them.

Positive premium means the account pays another participant. Positive external cash flow means a deposit; negative means a withdrawal. The two are separate so trade consideration is not confused with new capital.

For account `i`, define:

```
V_i = W_i + payout_change_i - premium_i - fees_i
new W_i = V_i + external_cash_flow_i

minimum_required_deposit = max(0, -inf(V_i))
maximum_available_withdrawal = max(0, inf(V_i))
```

For treasury, add any incoming fee credits to `V_i` before computing these bounds. The standalone funding helper estimates a participant's outgoing fee; it does not infer batch-wide treasury receipts.

An exact external cash flow is authorized as part of the batch. The engine does not silently take more from a wallet. The model's funding helper computes the requirement before a batch is submitted.

Payout changes must sum to zero as complete functions, including `VOID`. Premium payments must sum to zero. Fees are explicit transfers to treasury. Batch fields are serialized canonically and included in a SHA-256 digest.

Every explicit participant supplies an approval naming their account and the exact batch digest. The expected account revision prevents replay and stale portfolio changes. The digest binds all counterparties, amounts, fees, boundaries, exceptional values and deadlines.

**Approvals in the model are assertions by the test harness, not signatures.** Anyone running the Python process can create them. A production verifier would need authentication, market/deployment domain separation and a defined signature scheme; SHA-256 hashing alone supplies none of those properties.

The treasury can receive configured positive fee credits without an approval. Any explicit disposition of its funds requires its own approved change, like another account. Passive fee credits still advance its revision.

## 5. Atomic execution algorithm

1. Require an open market and a batch that has not expired.
2. Validate the market, fields, unique participants, existing accounts, revisions and exact approvals.
3. Verify that payout changes and premium payments each conserve value.
4. Derive all candidate profiles, wallet balances and the candidate escrow balance in temporary state. Apply fee transfers explicitly.
5. Check every affected account's numeric and exceptional minimum. Check that each depositing wallet has the authorized funds.
6. Commit all candidate values and advance affected revisions together. If any check fails, commit nothing.

Intermediate instructions inside a batch do not become observable positions. The completed batch must be funded. There is no temporary unbacked state committed to the ledger.

The engine verifies conservation of the changes and checks affected profiles; it need not re-scan every unrelated account. The inductive argument is that valid unchanged accounts stay valid, the zero-sum trade and fee transfers preserve conservation, and deposits/withdrawals change profiles and escrow by equal constants. A separate full audit recomputes global invariants for testing.

The first model uses exact, all-or-nothing batches. To partially exit, the user authorizes another exact batch for the desired fraction. Solver-selected partial fills and open-ended price limits are not implemented.

Reducing the number of open positions does not necessarily reduce the required deposit. A partial exit can remove an offset and also spend money to buy back a promise. Both effects enter the same candidate-balance calculation. The engine must reject an underfunded exit even if the interface calls it “close” or “reduce risk.”

The engine does not determine whether an exit price is attractive. An authorized offer can cost more than the maximum settlement payout being bought back; accepting it may require additional funds. Atomic execution removes intermediate committed positions, but it does not guarantee a low package price or supply missing capital.

## 6. Worked lifecycle

All numbers below are illustrative currency units. Define `L = 100 * 1(x < 95)`, `H = 100 * 1(x >= 105)` and `R = 20 * 1(97 <= x < 103)`. All three pay zero on `VOID`.

1. **Create a position.** A maker sells `L` for 22. The buyer deposits 22 and the maker deposits 78. Their combined escrow is 100.
2. **Add another shape.** The maker sells `H` for 32. Its worst gross obligation remains 100. The high buyer deposits 32, while the maker can withdraw 32. Maker net contribution becomes 46, against 146 if both obligations were funded independently.
3. **Introduce new boundaries.** The maker sells `R` for 5, introducing 97 and 103. Existing low and high buyers' profiles are unchanged. Escrow becomes 105; the maker now has 5 guaranteed in every outcome.
4. **Release guaranteed cash.** The maker withdraws 5, leaving escrow at 100.
5. **Reshape both tails atomically.** The maker buys back half of `L` and half of `H` for 11 and 16, paying a fee of 1. Together these changes permit a maker withdrawal of 22. The two buyers withdraw their proceeds of 11 and 16. Treasury receives 1, and escrow becomes 51.
6. **Settle individually.** At `x = 100`, the maker receives 30, the range buyer receives 20 and treasury receives 1. The low and high buyers receive zero. Escrow reaches zero after all redemptions. On a separately executed `VOID` branch, the maker instead receives 50 and treasury 1.

Each step checks global backing. A failed partial exit, stale approval, altered fee, wrong market or underfunded batch must leave the complete ledger unchanged.

This lifecycle opens the low obligation first, so its maker has already needed **78** before reaching the 46 contribution at step 2. Reporting 46 as this path's peak would be incorrect. The opening-order comparison below distinguishes that path from opening both together.

## 7. Where atomic execution can save funding

### Opening contribution versus peak funding

With premiums of 22 and 32 and fees omitted:

| Opening method | Peak personal capital needed during opening | Contribution after both positions are open |
|---|---:|---:|
| Both in one funded package | 46 | 46 |
| Low first, then high | 78 | 46 |
| High first, then low | 68 | 46 |
| Fund both obligations separately | 146 | 146 |

These are full-leg opening sequences. Smaller interleaved fills can change the peak. The 46 package row assumes a provider supplies and authorizes the whole package; it is not a claim about live quote availability.

### Closing a complete package

Return to the account after step 2. The maker's final balance is `100 - L - H`, and its net contribution is 46. It wants to close both obligations at their original premiums.

Buying back only `L` for 22 creates `78 - H`, whose worst balance is -22. Executing that leg alone requires another deposit of 22. Buying back only `H` first similarly requires 32. Closing both together creates the constant balance 46 and requires no new deposit.

| Closing method | Additional maker funding needed to execute | Final maker capital locked |
|---|---:|---:|
| Separate trades, low first | 22 | 0 |
| Separate trades, high first | 32 | 0 |
| Separate trades, 10 equal slices per leg | 2.2 | 0 |
| Separate trades, 100 equal slices per leg | 0.22 | 0 |
| Atomic, correctly netted package | 0 | 0 |

After a separate low-first close, the maker can recover its temporary 22 along with its original 46 when the other leg closes. The benefit is a reduction in peak additional funding, not a reduction in the completed portfolio's minimum collateral.

There is a stronger sequential alternative than choosing the order of two full legs. Close `1/n` of each obligation at a time, low first, at unchanged unit prices. The first slice requires `22/n` new cash; released original capital can fund subsequent steps. This schedule reaches the same final state in `2n` executions. With arbitrary divisibility and no transaction cost, the additional cash approaches zero. An atomic package achieves zero in one execution. A minimum fill size, fixed execution cost, unavailable partial fills or changing quotes would alter that comparison, but none is assumed in the measured funding example.

An existing system that supports an equivalent atomic, correctly netted package can also achieve zero additional funding. This comparison establishes a mechanism benefit over sequential execution, not a unique AsceMarket advantage.

### Closing individual positions after a reversal

Start again with the original `100 - L - H` balance and a net contribution of 46. This is a separate branch from the range-trade lifecycle above. All fees are zero in this branch.

The maker buys back `L` for 90 after a fall, then later buys back `H` for 90 after a rise. The first exit produces `10 - H` before any deposit. Its minimum is -90, so a deposit of 90 is required. The resulting funded balance is `100 - H`. The second exit produces a constant 10, which can be withdrawn.

| Action | Deposit / withdrawal | Net personal cash committed after action |
|---|---:|---:|
| Open both as a package | Deposit 46 | 46 |
| Close low for 90 | Deposit 90 | 136 |
| Later close high for 90 | Withdraw 10 | 126 |

The final trading loss is **126**, and peak personal funding is **136**. The initial 46 remains the worst settlement loss of the original unchanged portfolio; it never guaranteed the outcome of this later trading sequence. If only the original 46 is available, the first individual exit is rejected without changing the account.

The separately funded method needs 146 at opening, then releases 10 on each exit. Its final loss is also 126 and its peak is 146. Thus the exit deposit shrinks the capital saving from 100 to 10 on this path. Other tested paths erase the saving completely. An equally netted reference matches our funding throughout.

### What the lifecycle measurements establish

| Zero-fee path, atomic opening | AsceMarket peak | Exact-netting reference peak | Separate-funding peak |
|---|---:|---:|---:|
| Hold through settlement | 46 | 46 | 146 |
| Halve both, then close both at original prices | 46 | 46 | 146 |
| Individual exits at 90 after a reversal | 136 | 136 | 146 |

The [capital challenge](research/capital-challenge.md) also checks fees, 625 adverse price paths, bounded ramps and a public option-price snapshot. For identical cash flows and execution checkpoints, recognizing exact offsets cannot require more backing than funding the obligations separately. This does not prove lower total cost against an actual venue with different prices, fees, margin rules or withdrawal timing.

The reference is independent accounting arithmetic, not a live competitor account. Documented competing collateral-return rules can match some opening offsets. Firm package prices and the exact restrictions on a competitor's funded exits remain unverified. The design must earn any competitive claim against those stronger baselines.

## 8. Finalization and cash precision

The harness can finalize a numeric result or `VOID` only after trading closes. Finalization is one-way. No further trades, deposits or pre-settlement withdrawals are accepted. Accounts redeem individually, and each account can redeem at most once. Redemption credits its external wallet and reduces escrow by exactly its final balance.

After finalization, the relevant conservation check is the sum of unredeemed balances at the actual result, not every counterfactual result. This permits individual redemptions without a global loop.

The model uses exact rational balances through redemption. It deliberately does not round to an ERC-20 or banking unit. A production precision design must specify either integral payouts at all permitted observations or conservative redemption rounding with explicitly owned residual dust. Rounding individual legs before netting can change the contract; independent rounding cannot be treated as harmless. Tests involving thirds establish rational conservation, not the correctness of an unimplemented fixed-point port.

## 9. Portability of positions

Positions here are account entries, not transferable objects. That follows from section 1: the collateral requirement is a scalar of the account's whole vector, so no position carries a requirement of its own and no offset can travel with a position that leaves. Any export mechanism must therefore state what happens to the netting, and the answer is that it stays behind.

Two routes preserve the invariants. Neither is implemented or specified in detail.

**Transfer the whole profile.** One account's complete `W_i`, including its `VOID` value, moves to another owner as a single object. Every internal offset is preserved because nothing is separated. This is the natural form of the whole-position exit in section 7, and it requires no new accounting: it is an ordinary batch in which one participant's profile goes to zero and another's absorbs it.

**Export standardized pieces.** The payout language of section 2 decomposes into complementary pairs that each pay within `[0, 1]` and sum to the constant 1:

- `step(k, 1)` and its complement `1 - step(k, 1)`,
- a ramp capped at both ends and its complement.

A deposit of one unit mints a pair; returning the pair releases the unit. The pieces are fungible across holders with the same boundary, which is what makes them portable.

Export is strictly more expensive than holding the same exposure in one account. For example, `range(95, 105, 100)` decomposes as `100·step(95,1) + 100·(1 - step(105,1)) - 100`, so holding it as separated pieces requires backing 200 of claims against a 100 constant obligation, where one account requires 100. The difference is exactly the netting left behind. It is not a defect of the decomposition; it is the price of separability, and an interface must quote it rather than obscure it.

A boundary chosen freely produces a piece that only its creator holds. Concentration of liquidity at conventional levels, if it happens, will come from trading convention rather than from a restriction imposed here; forcing a coarse export lattice would make export inexact and is rejected for that reason.

## 10. Evidence and next decision

The next product-facing layer is specified in [quote-workflow.md](quote-workflow.md). Its three quote cards are checked by [model/workflow_examples.py](model/workflow_examples.py); [research/workflow-checks.json](research/workflow-checks.json) records the results. This adds no live quoting, authentication or reservation system to the ledger.

Run the commands in [model/README.md](model/README.md) to regenerate the lifecycle, funding comparison, representation measurements and test results. Generated observations belong in [model/results.md](model/results.md).

For the full-path capital assessment, read [research/capital-challenge.md](research/capital-challenge.md) and its [recorded results](research/capital-results.json). For how the interface explains an exit that needs more funds, read the adverse-exit branch in [quote-workflow.md](quote-workflow.md).

A subsequent [named architecture comparison](research/competitive-case.md) finds a narrower result: two separate butterfly payout peaks need 200 backing here versus a 387.5 continuous minimum when allocating their fixed put inventory under the inspected Gamma type-0 vault rules. The comparison optimizes fractional vault allocation and checks adverse exits. It is source-level evidence, not a deployed-venue measurement or proof against every synthetic alternative; it does not establish superiority to Deribit portfolio margin.

A second [named architecture comparison](research/negrisk-case.md) tests the Polymarket NegRiskAdapter at commit `f78b35b`. Its conversion operation matches this ledger exactly when the traded claims are declared questions of one neg-risk market: both require 1 unit of backing for two mutually exclusive claims, and the resulting profiles are equal. The gap appears only when an offset spans two markets, which a boundary inside an existing question always forces, since adding that boundary to the same market would break its partition. Measured backing is then 1 here against 2 there, growing by one per further refinement, and the adapter's surplus is verified to sit as a constant it cannot merge away. Every collateral-moving operation in that contract takes a single `conditionId` or `marketId`, so its requirement is additively separable across markets while this one is a single infimum over the combined profile. This is source-level evidence about an operation set, not a statement about prices, liquidity, token composability or demand.

The [follow-up proof](research/competitive-followup.md) shows that extra same-expiry puts cannot remove this gap under those cash-collateralized vault rules. For the user, the benefit is cash left available for other uses, not additional profit or a smaller loss on the same trade. Its financing value must exceed any extra trading and operating costs. Mixed-instrument alternatives and live portfolio margin remain unmeasured.

The model can establish exact arithmetic identities and reject invalid transitions for the cases it covers. Its tests are not a formal proof of the implementation. It cannot establish executable market prices, commercial adoption, production security, gas costs or the best data structure at scale.

Keep the simple sorted representation unless account-local growth makes verification too expensive. The next product decision is whether a named alternative requires more peak capital or blocks a useful funded change under matched terms and acceptable cost. Improving the data structure or the editor alone does not establish that advantage. Any future representation change must preserve the funding, exit and authorization semantics described here.
