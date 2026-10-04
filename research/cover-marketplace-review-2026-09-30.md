# Reusable event covers: product and quantitative review

Research date: 30 September 2026. Scope: user-created, reusable covers over a common event, traded to shape an account's exposure. This review does not substitute a customer-specific protection RFQ product for that marketplace.

**Finding: the intended marketplace is mathematically coherent and worth validating. Its key unsolved mechanism is trading liquidity across related covers. The current kernel supplies shared funding, not shared price discovery or execution.** A custom custody engine is justified only if it materially improves the necessary operations over a CTF or existing derivative construction.

Evidence consists of primary-source protocol documentation/code, research papers, and new reproducible synthetic calculations against the existing Python model. No customer interviews, executable AsceMarket quotes, live comparative order-book study, or historical maker-profitability backtest was completed. Consequently this report supports mechanism and architecture decisions, not a claim that demand or a commercial advantage has been established.

## The product being evaluated

An event fixes its observations, sufficient state, permitted histories, collateral asset, finality, exceptions, and verification capabilities. Users may define a cover within those capabilities. A cover has an immutable payout per lot; many users can trade the same definition. Different users build different positions by choosing quantities and combining covers. An ordinary user can write units at their own offered price if the resulting account is funded; a professional market maker may automate the same activity.

Customer diversity does not require customer-specific instruments or valuation models. A maker prices a cover's payout, trade size, and the change to its own inventory. The customer's existing account affects funding and presentation, not the definition of the traded cover. Package quotes may serve execution, but are not the product's sole entry point.

Creating a definition, issuing units, and supplying two-sided liquidity are three different actions. Permissionless creation does not promise a counterparty, a favorable price, or an exit. “Any payout” must mean any bounded payout admitted by the declared verification class and observation schema, not unrestricted executable code or a dependency on unrecorded facts.

## What related systems establish

| Mechanism | Primary evidence | Implication for AsceMarket |
|---|---|---|
| CTF | Fixed conditions, scalar/categorical payout vectors, nested positions, collateralized split/merge/redemption in the [Gnosis guide](https://conditional-tokens.readthedocs.io/en/latest/developer-guide.html) and [contract](https://raw.githubusercontent.com/gnosis/conditional-tokens-contracts/master/contracts/ConditionalTokens.sol) | Benchmark the actual cover constructions. Mutually exclusive complete sets are not a new capital capability. |
| DIVA | Users specify an event, payoff parameters, collateral, and oracle to create paired claims. Its [creation guide](https://docs.divaprotocol.io/diva-app/create-position-tokens) and [whitepaper](https://www.divaprotocol.io/pdf/DIVA_Whitepaper_v1.0.0.pdf) describe custom contingent derivatives. | User-defined tokenized payout creation is established prior work. Its pool construction is a useful comparison for combined account funding. |
| Opyn Gamma | Historical [protocol documentation](https://github.com/opynfinance/v2-documentation) describes creating options for whitelisted products and using long options to collateralize spreads. | Permissionless parameter choice within admitted families is a precedent. This is not evidence about current trading activity. |
| Deribit | [Combo books](https://support.deribit.com/hc/en-us/articles/31424954956061-Combo-Books) execute related legs together and retain independent leg trading. Inactive books are constrained by volume and book-count policies. | Atomic baskets and reusable components already exist. Unbounded book creation is a practical concern even for an established venue. |
| Betfair | [Cross-matching](https://www.betfair.com.au/hub/help/cross-matching-on-exchange-markets/) matches orders using other selections. [Developer documentation](https://support.developer.betfair.com/hc/en-us/articles/115003878512-Why-are-the-prices-displayed-on-the-website-different-from-what-I-see-in-my-API-application) describes displayed virtual liquidity. | Equivalent exposure can provide executable liquidity beyond the direct book. This is a stronger comparison than matching only identical IDs. |
| Polymarket | [Combo collateral return](https://docs.polymarket.com/trading/combos/collateral-return) decomposes compatible claims, returns collateral, and preserves residual positions. | Combined positions and capital release alone are insufficient differentiation. |

These are mechanism comparisons, not deployed-bytecode audits, guarantees of venue safety, or evidence that every mechanism reproduces every proposed AsceMarket cover.

The best literature match is [Dudik et al., Log-time Prediction Markets for Interval Securities (2021)](https://xintongemilywang.github.io/assets/paper/aamas21.pdf). It studies reusable interval claims over one numeric outcome and efficient common market making, including a multi-resolution construction with a bounded-loss result. It supports the feasibility of shared pricing across many covers. It does not establish a ready EVM implementation or profitable operation on AsceMarket's proposed event families.

[Abernethy, Chen and Vaughan (2013)](https://www.microsoft.com/en-us/research/publication/efficient-market-making-via-convex-optimization-and-a-connection-to-online-learning/) give a broader convex-optimization framework for bounded contingent securities. A restricted payout family and its tractable structure matter; merely accepting an expression does not make general market making inexpensive.

## New quantitative evidence

Reproduce with:

```sh
python3 -B research/cover_marketplace_quant.py
```

The script writes [the result file](cover-marketplace-quant-results.json), records its hash and model hashes, and uses independent raw-path evaluation to check exact identities. There are five experiments.

### 1. Many reusable covers can draw on a small basis

For an event with eight exact normal values and a zero-paying exception, define eight threshold covers T_k, each paying 100 when the observation is at least k. A payout table g is represented by its initial level and successive changes:

```text
g = (g(0)/100) T_0 + sum_k ((g(k)-g(k-1))/100) T_k
```

Negative coefficients are internal short holdings. An interval is the difference of its two boundary thresholds, with the top boundary omitted when the interval extends to the highest admitted value.

The experiment checks all 36 nonempty contiguous intervals and all 6,561 profiles whose eight payments independently belong to {0, 100, 200}. Each representation matches on every complete history, including cancellation, and the graph minimum/maximum agree with independent exhaustive evaluation.

**Interpretation:** many public cover definitions need not represent equally many independent risk dimensions. Users can hold reusable covers while makers and execution services manage a smaller underlying basis. The result applies to this exact finite domain. Discontinuous/continuous and path-dependent families require their own representation.

**Important boundary:** this is a signed-account replication result. It is not an implemented facility converting a basket into a transferable single-cover token. Custody, issuance, permissions, backing, and fees for any conversion route still need design.

### 2. Shared funding can matter without establishing profitability

Use two exclusive tail covers paying at most 100 each, assumed premiums of 38.50 each, and zero cancellation payouts. Under an assumed uniform distribution on the eight normal outcomes, each tail wins in three outcomes.

| Execution / ownership | Maker's personal contribution |
|---|---:|
| Two separately funded writers | 123.00 in total |
| One maker, both sales atomic | 23.00 |
| One maker, first sale executes alone | 61.50 initially |
| Same maker after the second sale and surplus withdrawal | 23.00 remaining |

The ledger executes and reconciles both the atomic and sequential cases. The difference illustrates account-local offsets and the temporary capital cost of legging. A CTF complete-set construction can match the exclusive example's backing; these figures are not a competitive superiority claim.

Under the stated probability/premium assumptions, expected gross maker profit is 2.00. Yet it loses 23.00 with probability 75% and gains 77.00 with probability 25%. Costs and probability-estimation error can erase that 2.00. Exception probability is zero only in this illustrative expected-value model; exceptions remain in funding support. If cancellation instead pays 60 on both covers, required personal contribution becomes 43.00 at unchanged premiums.

**Interpretation:** favorable collateral arithmetic is real, but it neither proves sustainable maker returns nor determines who receives the savings.

### 3. Shared event marginals do not determine all cover prices

Two checkpoints can each have a 50% probability of being above a threshold. A cover paying 100 only when both are above can have these undiscounted fair values:

| Joint model | First checkpoint cover | Second checkpoint cover | Both-checkpoints cover |
|---|---:|---:|---:|
| Perfectly opposed | 50 | 50 | 0 |
| Independent | 50 | 50 | 25 |
| Perfectly aligned | 50 | 50 | 50 |

The experiment checks those exact joint distributions. They have identical marginal prices and different path-cover prices.

**Interpretation:** a maker can share a model across covers, but richer dependencies require a richer model. Existing terminal-price quotes do not uniquely value every window, touch, or sequence cover. A complete safety graph does not specify probabilities. For a nontradable event there need not be a unique hedge-based valuation measure at all.

### 4. Different cover IDs can compete through payout equivalence

Suppose exclusive A and B each pay 100 and C pays exactly A+B, including exceptions. In a hypothetical book, asks of 35 for A and B replicate C at 70, compared with a direct C ask of 80. A C bid of 75 would create a gross opportunity of 5 if acquisition, conversion/delivery, and sale were executable together.

**Interpretation:** the cheapest route to a payoff can span other cover books. Showing only C's direct book misses relevant liquidity. The opportunity is conditional on actual depth, signatures, custody, exact equivalence, and all costs. No observed arbitrage or implemented conversion is claimed.

### 5. A common maker can price reusable covers without knowing customers' exposure

An illustrative finite-state cost is:

```text
C(L) = b log(sum_h p(h) exp(L(h)/b))
quote(f) = C(L + f) - C(L)
```

Here L is the maker's current liability payout, f is the new liability, p is an assumed event distribution, and b is a risk/liquidity parameter. This example uses eight normal states, a 1% exception probability, and b=100. An empty maker quotes either tail at approximately 49.342234. After writing one tail, the other is quoted at approximately 32.891996. Their total is 82.234230, equal to the atomic basket quote.

The maker's event model and inventory change the quote; the customer's holdings do not enter it. Dependence on the total payout rather than arbitrary token labels also gives equivalent portfolios the same cost change. The calculation demonstrates coherent shared quoting and telescoping, not a production AMM or economically competitive spreads. Floating-point pricing is used only in this offchain illustration; executable settlement remains exact integer arithmetic. Funding checks cannot be replaced by these cost calculations.

## The decisive architectural gap

The repository already handles account-level funding over a common event. It does not yet provide these distinct kinds of reuse:

1. Definition reuse: identical contractual cover terms map to the same ID and lot denomination.
2. Pricing reuse: makers value multiple covers from one event model and inventory.
3. Execution reuse: an exact basket of related orders can deliver a requested payout at a competitive all-in cost.

The existing kernel addresses funding and accepts supplied candidate operations. It does not discover an optimal basket, ensure coherent market prices, or make a thin book liquid. Efficient account verification does not imply efficient unrestricted order combination search.

Do not deploy a pool or permanently active matching structure per new cover. A direct cover book may exist while executable synthetic routes use a limited known basis or explicitly supported identities. Use bounded route candidates and atomic settlement rather than assuming a general optimal portfolio solver is cheap. An unsolicited basket containing short legs must never be substituted for a bought transferable claim without explicit semantics and authorization.

## Recommended implementation direction preserving the intended product

**Event-level accounting:** retain the complete-account invariant and immutable observation/finality schema. Multiple cover IDs share backing only within an account and a correctly modeled event. Unrelated prices or correlated events do not gain offsets merely by appearing together.

**User cover creation:** let users instantiate admitted, bounded declarative templates within a platform-approved event. Validate payout totality, nonnegativity for external claims, bounds, state sufficiency, exceptions, canonical identity, and whole-account/resource limits. A new definition does not mint units. Issuance requires funding and authorization. Listing spam and eventual catalogue resolution must have bounded cost. The current manager document's platform-approved cover policy differs from this intended user-creation policy; select that policy explicitly rather than claim it is implemented.

**Canonical identities:** keep display labels separate from economic identity. Normalize supported expressions and lot conventions; bind event, source/finality, deadlines, exceptional payouts, and versions. Proving arbitrary program equivalence is not required or assumed. Two expressions equal under normal outcomes but different on cancellation must remain different instruments.

**Reusable instrument trading:** users post cover prices and quantities; buyers/sellers acquire the same terms. Maker automation is optional infrastructure for that marketplace. An RFQ for a cover or basket is one execution option and does not require a customer to disclose an external exposure or create a bespoke policy.

**Shared maker quoting:** build an offchain reference quoter over the same payout semantics. Separate the event valuation model from the exact funding model. For numerical terminal covers, known threshold/ramp families are easier to quote and hedge than arbitrary path conditions. Expose direct and equivalent-route prices when available, with full quantity and fee limits. A supplied quote is not a guarantee of executable capacity after competing fills.

**Atomic bounded routing:** settle authorized related legs together. Start with a small set of exact payout identities and explicit maker baskets. Final facts, cancellation policy, precision, and historical contributions must match before recognizing equivalence. A conversion adapter that backs a new claim with acquired internal rights is itself a security-relevant implementation, not free algebra.

**Settlement choice:** compare the necessary operations using CTF outcome inventory versus the custom manager. For compact categorical/finite numeric events, CTF is a strong baseline. Custom graph accounting becomes more attractive if managing large joint-outcome inventories is demonstrably more expensive than graph evaluation. Exact scalar cover creation on a fixed coarse graph remains restricted; use an explicitly finite precision/domain or separately validated analytic family. None of these choices should silently alter old cover promises.

## What might differentiate the product

The defensible hypothesis is a combination: user-created reusable payouts on one approved event; instrument trading that reaches related liquidity; common account funding; and understandable combined exposure. The mechanism is not novel in all its parts. Its implementation, supported cover families, costs, and market quality must outperform a concrete alternative for a recurring task.

Choose the first event from demand and source availability rather than inventing a broad customer market. A single terminal numeric event makes valuation and representation easier, but competes with options and interval markets. Live sports can provide meaningful logical relations and window conditions, but adds source corrections, event-order state, and severe stale-quote risk. Both fit the product thesis; neither has demonstrated demand here.

Track active executable cover count rather than admitted definitions. Track spread at specified trade sizes, fill rate, quote age, rejection rate, direct versus synthetic-route availability, maker net P&L including costs, temporary capital needs, repeated use of the same definitions, and cost to change/exit a position. Payout diversity or number of minted IDs is not a success metric.

The next validation should compare the same supported cover set under direct-only trading, bounded exact routing, and a shared inventory-aware maker. Use replayed real event data and stated latency assumptions; obtain actual maker quotes before concluding customers get better terms. Retain the custom settlement layer only if its necessary behavior or measured lifecycle cost wins that comparison.
