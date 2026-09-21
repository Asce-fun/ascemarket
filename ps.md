# AsceMarket

## A market for every risk.

**Choose how the future affects your money.**

Trade a view. Protect an exposure. Reshape your position in one move.

---

## The vision

The future affects everyone differently. A rise in gold is an opportunity for one person and a cost for another. More expensive computing can help a cloud provider and hurt the startup that depends on it. Rain can save one business and interrupt another.

People should be able to choose which risks they hold, which they share, and how much they can lose.

AsceMarket is a market where people shape that exposure directly. Choose an event or measurement, decide how your money should respond to its result, and see the price. As your view or needs change, reshape the position in a single transaction.

Underneath, every account holds one combined payout for each market. Related positions offset, every remaining payment is funded, and changing a portfolio requires only the money needed to complete the change safely.

We want to make shaping financial exposure as straightforward as choosing an amount to send. Over time, the same foundation can support everyday trading, protection for businesses, and financial products for risks that are difficult to express today.

**The ambition is a common foundation for moving risk: flexible enough to express what people need, simple enough for them to use.**

*Product specification — intended behavior and design targets. The demonstration criteria below define how the proposed capabilities will be verified.*

---

## The problem

People think in outcomes:

- “I expect a moderate rise, and I am happy to cap my profit.”
- “Protect me if this cost goes above my budget.”
- “I think the result will land in this range.”
- “My situation changed. Adjust my exposure without making me rebuild everything.”

Financial products ask them to translate those intentions into instruments, quantities, strikes and separate trades. Existing tools can express many of these exposures, but constructing and maintaining them can require several decisions and operations.

The friction appears in four places.

**Expressing the position.** The available contract may not match the desired boundary, payout or observation period. A combination may work, but the user must construct it.

**Funding the position.** Where contractual offsets are not recognized, positions tie up more money than their combined worst outcome requires.

**Changing the position.** Replacing one exposure with another can require temporary funding or leave the user exposed between separate executions.

**Understanding the position.** A list of trades does not immediately show what the person will receive, what they can lose, or how the next trade changes the whole account.

AsceMarket brings these tasks into one workflow: **choose the exposure, see its effect on the account, and execute the complete change.**

---

## The core idea: one account, one combined payout

### The unit is a state, not an instrument

Most venues sell instruments: a share, a contract, a listed strike. This design sells something more primitive — **money in particular states of the world.**

A market fixes what will be observed. Each permitted result is a state. An account records what its owner receives in every state. A trade moves money between states and between accounts. That is the whole object.

This is the Arrow–Debreu description of a market, and choosing it as the unit has consequences that are not stylistic:

- **Offsets are structural.** Two claims on the same observation are two functions over the same states, so combining them is addition. “A wins” and “A or B wins” are not separate products that happen to be related; they are vectors in one space, and the engine sees their sum without needing a rule for that particular pair.
- **The vocabulary is complete within the observation.** Any bounded payout the language can describe is expressible directly, rather than assembled from whichever instruments happen to be listed.
- **Prices are probabilities.** The price of a claim paying one unit across a range is the market's implied probability that the result lands in that range.

An instrument-based venue can add each of these as a feature. A state-based one gets them as consequences. This is a claim about the representation, not about liquidity: a state that nobody wants to price is still unpriced.

The limit is equally important. One market covers one observation, so the completeness above applies to a slice of the future, not to the future. Combinations across separate observations remain outside this design.

### A market describes one future observation

A market identifies what is observed, when it is observed, and the settlement rules that apply. Examples include an election result, a price at a specified time, or rainfall accumulated over a defined period.

The observed value need not be an instantaneous reading. It may be any single number produced by an agreed measurement rule: an average price or rate over a period, a cumulative total, a measure of variability, or an extreme reached within a window. The requirement is that the rule is fixed before trading and yields one value at expiry. The accounting treats that value identically however it was produced, so widening the range of supported measurements does not change the funding rules.

This is what allows one engine to serve price exposure, rate exposure and metered or physical quantities without a separate mechanism for each. Payouts remain bounded, so an exposure that is naturally unlimited is expressed with an explicit cap.

The result may be a category or a number. Numeric results are treated as numbers; the design does not require a separate market for every range or strike.

Positions share collateral when they belong to the same market and settlement asset. Their observation and settlement rules must be identical. A similar underlying, a different expiry or a statistical correlation does not by itself create a guaranteed offset.

### An account describes what its owner receives

For each possible result, the account records its owner's final balance. This combines deposited funds, trade payments and all remaining payout obligations and claims.

A person may make many trades, but the engine evaluates one combined balance profile. The interface retains the trade history while showing the resulting exposure as a whole.

### A trade changes that combined payout

Buying, selling, adding protection and replacing a position are all changes to future balances.

The engine accepts a change when the participants authorize its terms and every affected account remains fully funded. The core operation is:

> **Move from the exposure I have to the exposure I want, at an acceptable price, in one transaction.**

Thresholds, ranges and custom curves are ways to describe that change. They use the same accounting rule.

---

## What the user does

### Start with an intention

The product offers four entry points:

| Intention | What the user chooses |
|---|---|
| Profit from a move | Direction, sensitivity, maximum loss and profit cap |
| Profit within a range | Lower and upper boundaries, payout and maximum spend |
| Protect an exposure | The level at which protection starts and how the payout grows |
| Reshape my position | The desired change to an existing combined payout |

Presets provide a starting point. A chart makes the result visible. Advanced users can edit supported payout shapes directly.

### See the whole change before accepting

The preview shows:

- The existing and proposed combined payout on the same chart.
- The net trade payment and fees.
- Any additional deposit required and any funds available to withdraw afterward.
- The maximum loss and gain under the quoted terms, with the comparison basis identified.
- The observation time and settlement terms.

Payout, profit and available cash are distinct values. The product must not label a gross payout as profit or confuse a premium payment with additional collateral.

### Execute together

The accepted change executes as one atomic transaction: its agreed components complete together or none complete. Any permitted partial execution must be explicitly authorized and must preserve the specified exposure and funding limits.

After execution, the user sees one updated position and a record of the change.

### Manage exposure as it evolves

The user can move a boundary, reduce size, add a cap, add protection or request a full exit. Each action starts from the existing portfolio and quotes the complete change.

An exit follows the same execution and funding rules as any other trade. Estimated valuations are identified separately from executable quotes.

---

## How the money stays funded

The rule is simple: **every account must be able to receive its promised final balance using money already held by the market.**

For every permitted settlement result:

1. Every account's final balance is nonnegative.
2. The sum of all final balances equals the funds backing those accounts.

A deposit adds funds and increases the depositing account's balance across outcomes. A trade redistributes future balances between consenting participants. A withdrawal removes funds and reduces the withdrawing account's balance across outcomes. Each operation preserves both rules, including its fees.

If an account has at least $20 in every possible settlement result, that $20 is guaranteed and can be withdrawn. Its remaining profile is reduced by $20 in every result, so the same funds cannot be claimed twice.

This design does not require a participant to deposit more because market prices move. Positions are funded against their contractual worst outcome. New trades and withdrawals must pass the funding check again.

That funding bound applies to the current portfolio through settlement. Closing one component can remove an offset and require an additional deposit. Losses accumulated through subsequent trades can exceed the original deposit when the user authorizes and supplies more funds. An open trading window is not a guarantee that every individual exit is affordable from the original deposit.

The guarantee concerns the specified payouts in the settlement asset. It depends on correct execution of the accounting and settlement rules.

### An example of exact netting

Consider one price observation with three outcomes: low, middle and high. A seller supplies two contracts:

- A $100 payout in the low outcome, for a $22 premium.
- A $100 payout in the high outcome, for a $32 premium.

The seller collects $54. Only one contract can pay, so the maximum combined obligation is $100. After both trades complete, the seller needs to contribute $46.

| Treatment | Seller's net capital contribution |
|---|---:|
| Each obligation funded separately | $146 |
| Combined worst-case funding | $46 |

The buyers' $54 and the seller's $46 together fund $100. The seller loses $46 in either tail outcome and earns $54 in the middle outcome. These are illustrative prices, with fees omitted.

Existing systems that recognize the same complete offsets can achieve the same final funding requirement. AsceMarket's design goal is to make this treatment native across its supported custom payouts and portfolio changes.

The [full lifecycle capital challenge](research/capital-challenge.md) checks this claim across holding, package changes and individual exits after a reversal. The 46 figure is the completed portfolio's contribution; sequential opening can require more temporary funding. The challenge demonstrates savings over separate funding and parity with an exact-netting reference, not a verified capital advantage over the best competing venue.

A subsequent [named architecture test](research/competitive-case.md) finds a funding advantage for a fixed two-butterfly option portfolio against the inspected Gamma vault rules, even after optimizing their allocation. This is a narrow source-level result; deployed execution, alternative constructions and superiority to mainstream portfolio margin remain unverified. It supports investigating whole-account funding across multiple bounded structures without claiming universal capital superiority.

A [second test](research/negrisk-case.md) applies the same method to the Polymarket NegRiskAdapter. That contract already nets mutually exclusive claims declared within one market, and the comparison records parity there rather than an advantage. What it cannot net is an offset spanning two markets, which is forced whenever a boundary falls inside an existing question. The distinction is between funding one declared partition and funding one observation.

---

## Efficiency throughout the life of a position

Capital efficiency includes more than the amount locked after a trade.

| Dimension | What AsceMarket aims to improve |
|---|---|
| Final capital | Recognize exact offsets across the account's combined payout |
| Execution capital | Avoid funding unnecessary intermediate portfolios |
| Capital availability | Release guaranteed amounts as soon as the rules permit |
| Computation | Represent and verify exposure without expanding every possible outcome |
| User effort | Reduce the decisions and operations needed to create and maintain exposure |

### Changing exposure with one net payment

Suppose a current position can be sold for $40 and its replacement costs $60.

Buying first requires $60 before recovering the $40. Selling first reduces the additional cash needed to $20, but temporarily removes the original exposure. An atomic replacement completes both actions with a $20 net payment, assuming no additional collateral requirement and excluding fees.

The final exposure is the same. The path to it requires less temporary funding than buying first and avoids the intermediate exposure of selling first.

**The target is to fund the agreed result directly, without requiring users to finance avoidable steps along the way.** This is an execution objective, not a promise to fund unchanged obligations below their worst-case requirement.

---

## Flexible payouts without a separate instrument for every shape

### Supported expressions

The engine's payout vocabulary consists of:

- **Thresholds:** pay when a result is above or below a chosen level.
- **Ranges:** pay when a result falls inside or outside chosen boundaries.
- **Ramps:** increase or decrease payment between two levels, with capped tails.
- **Custom combinations:** bounded profiles formed from steps and straight-line segments.
- **Categories:** assign a payout to each permitted categorical outcome.

These expressions cover binary positions, capped directional exposure and combinations of protection. “Custom” means expressible within this defined vocabulary; it does not imply arbitrary executable code.

### Store the shape that matters

For numeric markets, the proposed representation stores the boundaries, jumps and slopes needed to describe each account's combined payout. Values use defined precision and boundary conventions.

A new trade can introduce a new boundary without rewriting other accounts or changing the meaning of their positions. Equivalent payout expressions should reduce to the same exposure and receive the same funding treatment.

Worst-case verification must include boundaries, one-sided limits, tails and any exceptional settlement cases. The complexity target is that checking an account depends on its relevant exposure, rather than the total number of shapes created by unrelated users. The exact data structure and performance remain to be demonstrated.

Relative instructions, such as “protection starting 2% above the current price,” are converted to explicit levels using an agreed reference at execution. The resulting contract has fixed terms.

---

## What the market produces

A venue that prices states rather than instruments produces a different output.

Where a binary market reports a single number — the probability of one event — a complete state market reports the **whole implied distribution over the observed value.** The price of a claim paying one unit between two levels is the implied probability mass between those levels, read directly from the quote.

Options markets contain the same information, but only implicitly: the distribution has to be recovered from prices at sparse listed strikes, by differentiating an interpolated curve. Here the quantity is quoted natively, because the traded object already is a claim on a set of states.

This is a property of the representation. Its usefulness depends entirely on whether the quotes are real. A thin market yields a confident-looking distribution assembled from noise, which is worse than reporting nothing. Any published distribution must therefore carry the liquidity that produced it, and no accuracy claim is made here.

## Holding a position outside the account

Positions in this design are account entries rather than transferable instruments. Netting is a property of an account, so an offset cannot travel with a position that leaves it. Two routes are compatible with the funding rules:

- **Transfer the whole account.** A complete payout profile moves as one object, preserving every offset inside it. This is also the cleanest form of the whole-position exit described in the sections above.
- **Export standardized pieces.** The payout language decomposes into complementary claims that each pay between zero and one unit and sum to one unit, so a deposit mints a pair and returning the pair releases the deposit. These pieces are fungible and portable.

Exporting is strictly more expensive than holding the same exposure in one account, because each exported piece must be backed on its own. That cost is the netting being left behind, and it should be quoted plainly rather than hidden. Neither route is implemented.

---

## Price the complete change

The first [quote-and-accept workflow](quote-workflow.md) defines three concrete tasks: buy a capped payout, move its protection boundary, and reduce offsetting obligations while releasing funds. It includes checked quote examples, failure handling and a [comparison with current alternatives](research/workflow-evidence.md). The first quote mechanism is one exact package offer from one provider; the core remains independent of how that provider prices the change.

A request describes the desired payout change, size, price limit and execution conditions. Providers evaluate the complete request against their own exposure and available funds.

A quote states what can execute, at what net price, for what size and under what conditions. It may come from a firm package offer, an automated pricing function or a combination of compatible orders.

The clearing engine is independent of the pricing mechanism. Its job is to verify authorization, funding, conservation of funds and atomic execution.

Price discovery can compare complete offers and valid combinations. Any assembled execution must respect package conditions, shared capacity and account funding. Taking the cheapest apparent price for each piece is not assumed to produce the best executable package.

This separation allows the same account primitive to support different market mechanisms without changing what ownership or full funding means.

---

## Time and settlement

The first product uses a fixed observation and expiry. Its payouts depend on that defined result, rather than on temporary price movements beforehand.

Each market specifies its observation, permitted results, precision, boundary conventions, finalization rule and exceptional settlement treatment before trading. Every permitted treatment must preserve the same funding guarantees. Cancellation rules must define their payments explicitly; they cannot assume that historical trades and withdrawals can simply be reversed.

Once the result is final, each account's payout is determined from its combined profile. Accounts can be settled or redeemed individually without requiring one transaction to update every participant.

Repeating exposure extends the same model:

- **A fixed schedule** purchases specified contracts for several observations. Each component has explicit terms and funding.
- **Renewal instructions** request the next contract within the user's price, spending and exposure limits. Future periods become funded positions only when their trades execute.

A sequence of capped daily payouts is a different contract from a payout on a monthly result. The product shows that distinction. Renewal accounting also keeps unsettled earlier periods separate from funds available for the next trade.

---

## One engine, many applications

**Trade** is the first experience: express a view, understand the possible results, and reshape the position as the view changes.

**Cover** is a future experience for people and businesses managing a cost or revenue exposure. It starts with what they need protection against and translates that need into an explicit payout. Comparing the payout with the actual exposure is part of that product.

**Build** is the longer-term opportunity for developers: create focused applications on a shared foundation for payout accounting and execution. Different interfaces can serve different needs while using the same funding rules.

The core grows through reusable operations. More applications can use the same language for exposure. Exact collateral benefits remain tied to compatible settlement states; unrelated markets do not acquire guaranteed offsets merely by sharing the platform.

---

## What makes the product worth building

The product thesis is one choice and the four capabilities that follow from it. The choice is to make a **state of the world** the traded unit rather than an instrument.

1. **Express the payout directly.** Choose boundaries and supported shapes without manually constructing a collection of instruments. Expressiveness follows from assigning amounts to states rather than selecting from listed contracts.
2. **Manage the whole exposure.** Understand and edit the account's combined payout, which is one vector over states rather than a list of positions.
3. **Execute the complete change.** Apply compatible purchases, sales and funding movements together.
4. **Keep funding exact.** Recognize contractual offsets and release guaranteed balances throughout the position's life. Offsets need no per-pair rule, because claims over the same states combine by addition.

Netting, bounded payouts and package execution have existing precedents. The proposed advantage is that a state-based account obtains them together as consequences of one representation, rather than as features added one at a time to an instrument-based one. The corresponding costs are equally structural: positions are not separable without giving up their offsets, and completeness stops at the boundary of a single observation.

The system should match the final funding of an equivalent, correctly netted alternative. Its additional opportunity is to improve how easily that exposure can be expressed, reached and changed, and how efficiently those operations can be verified.

The same payout-editing experience should also be tested over existing infrastructure. Custom payouts and package quotes already exist. A new account engine earns its place when a recurring user requirement or measured lifecycle improvement justifies it; a simpler adapter remains a valid route toward the vision.

The strongest product demonstration is a person reshaping a complex position as easily as placing a simple trade.

---

## The first complete product

Start with one numeric market, one observation time and one settlement asset. The initial experience supports creating and editing thresholds, ranges, ramps and their bounded combinations in one account.

The first users we design for are traders shaping bounded exposure and makers managing several related payouts. Both need to understand and change the effect of a portfolio on one observation.

The central demonstration follows a complete lifecycle:

1. Create a payout from a simple intention.
2. Introduce a boundary that was not previously used.
3. Add an offsetting position and show the combined funding requirement.
4. Replace several components through one atomic change.
5. Withdraw an amount guaranteed across every permitted settlement result.
6. Partially exit while keeping the remaining position funded.
7. Settle the final account balance.

This lifecycle exercises the proposed primitive more directly than launching several unrelated product categories at once.

Categorical markets, scheduled exposure, renewals and specialized protection experiences follow once they can use the same verified operations. The core funding promise remains unchanged.

## What the design must demonstrate

| Property | Demonstration required |
|---|---|
| Full funding | Every accepted operation preserves nonnegative final balances and conservation of backing funds for every permitted result |
| Equivalent treatment | Different descriptions of the same exposure produce the same collateral requirement |
| Stable positions | Adding a boundary or refining another account's representation leaves existing payouts unchanged |
| Exact accounting | Fees, rounding, deposits and withdrawals reconcile without creating unbacked claims |
| Atomic changes | A portfolio transition meets all authorized limits or leaves the account unchanged |
| Efficient funding | Measure peak funding throughout execution as well as final locked capital against equivalent alternatives |
| Safe partial exits | Removing an offset cannot leave the remaining obligations underfunded |
| Scalable verification | Measure cost as an account's complexity grows and as unrelated market activity grows |
| Consistent pricing rules | Equivalent packages and trade sequences cannot exploit accounting or representation differences to extract funds |

These are architecture and product criteria. Synthetic demonstrations establish mechanism behavior; they do not establish adoption or revenue.

## Design decisions to resolve

The first accounting design and its executable checks are documented in [core-design.md](core-design.md), with measured findings in [model/results.md](model/results.md). These results test mechanism behavior; they do not yet establish production readiness or a reason for users to switch.

- The canonical representation of payout functions and exact numeric precision.
- How accepted quotes bind to the current account state and handle concurrent changes.
- Which package quoting and matching method best supports atomic portfolio transitions.
- How to bound and communicate supported payout complexity while retaining expressive power.
- How fees interact with package pricing, offsets and guaranteed withdrawals.
- How to present profit, payout, trade consideration and withdrawable funds without ambiguity.

## Reference mechanisms and research

These references establish useful comparisons for the design. They do not prescribe implementation dependencies.

- [Gnosis Conditional Tokens](https://gnosis-conditional-tokens.readthedocs.io/en/latest/developer-guide.html): outcome claims, collateral splitting and merging.
- [Polymarket negative-risk adapter](https://github.com/Polymarket/neg-risk-ctf-adapter/): collateral conversion across compatible categorical positions.
- [An Optimization-Based Framework for Automated Market-Making](https://arxiv.org/abs/1011.1941): pricing bounded securities through convex optimization.
- [Log-time Prediction Markets for Interval Securities](https://arxiv.org/abs/2102.07308): efficient operations for numeric interval markets.
- [Integrating Market Makers, Limit Orders, and Continuous Trade](https://www.microsoft.com/en-us/research/publication/integrating-market-makers-limit-orders-and-continuous-trade-in-prediction-markets/): bundle execution and market-design tradeoffs.
