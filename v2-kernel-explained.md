# AsceMarket v2 kernel, in simple words

This guide explains [v2-kernel-spec.md](v2-kernel-spec.md). The specification remains the source of truth. This is a guide to the engine's rules, not a final contract architecture.

## 1. What are we building?

AsceMarket lets people buy and sell covers with clearly defined payouts tied to future events.

A buyer pays a price for protection. A seller accepts the obligation to fund that protection. The kernel is the accounting and settlement engine that makes sure accepted obligations can be paid.

Its main question is:

> After this action, can every account meet its obligations in every outcome that is still allowed by the market's rules?

If the answer is no, the action fails unless the authorized transaction supplies enough additional funds.

The kernel does not decide what a cover should cost. Sellers quote prices, and buyers decide whether to accept them. It also does not guarantee that someone will sell a cover or buy an existing position.

## 2. A market and a cover are different things

A **market** defines the event, the information we observe, and the settlement rules.

For a football match, that might include:

- Which match and which observation source we use.
- Which scores and event information the system can represent.
- Which checkpoints we observe.
- When observations become final.
- What happens if the match is cancelled or data never arrives.

A **cover** defines a particular payout within that market.

For example:

| Cover | Payout condition |
|---|---|
| A | Pay 100 if Real Madrid scores between minutes 60 and 70. |
| B | Pay 100 if the final score is exactly 1–0. |
| C | Pay 100 if Barcelona wins. |

These covers share an event, but they have different obligations. Each also needs explicit cancellation and failure rules.

The cover definition is reusable. Different sellers can offer the same cover at different prices and quantities. The definition, the seller's offer, and the buyer's resulting holding are separate things.

## 3. How can one engine support different kinds of protection?

The engine works with possible event histories and payout rules, rather than hardcoding a separate accounting system for football, rainfall, or prices.

Think of an event as a map of possible routes:

`Starting state → later observation → next observation → final outcome`

Some routes end normally. Others end in cancellation or another declared failure outcome. A cover assigns a payout to each permitted route.

The current baseline represents this as a finite map of states and connections. Payouts can depend on a state or a transition between states. More complicated conditions may need extra information remembered in those states.

A new cover can use the existing engine if its rules fit this language and its limits. That normally means adding a definition, rather than writing a new settlement contract for that cover.

**Generic does not mean every imaginable cover is automatically supported.** A new capability needs its own validated evaluator if the existing representation cannot express it safely or cheaply.

For example, a score at minute 70 does not necessarily tell us who scored first during the previous ten minutes. A “first scorer” cover needs that information represented and observed. The kernel cannot reconstruct information the market never recorded.

## 4. What must be decided before trading starts?

The market must commit to its economic rules before anyone trades: observations, possible histories, settlement asset, finality, exceptions, and the allowed cover language.

Those promises cannot change after people buy protection. Changing the meaning requires a new market.

New cover definitions may be added later if the market permits it, but they must fit the existing rules and available information.

Even a phrase like “the next ten minutes” must become an exact time window before signing. Buying later must not silently move that window.

Unexpected data also needs a rule. If a market cannot represent a reported score, it must follow its published overflow or failure policy. It cannot silently replace the score with a different one.

## 5. What does an account contain?

Within a market, an account combines:

- An internal cash component.
- Covers it owns: rights to receive payouts.
- Covers it has sold: obligations to pay payouts.

For any permitted outcome:

`Account entitlement = cash component + cover payouts owned − cover payouts owed`

The cash component is an accounting number inside the engine. It is not the user's wallet balance, and it is not automatically available to withdraw.

The engine checks the whole account. A positive cash component may still be needed to back sold covers. A negative cash component can be valid when the remaining cover rights guarantee enough value to offset it in every permitted outcome.

The actual settlement tokens sit in escrow. Across all accounts, total remaining entitlements must equal the accounted funds in escrow, whichever permitted outcome occurs. Premiums and fees move value between accounts; they do not create money.

## 6. How much backing does a seller need?

Suppose a seller sells a cover that pays either 0 or 100. The buyer pays 30. Ignore fees for this example.

The seller contributes another 70. Together, those funds provide the 100 needed if the cover wins.

| Outcome | Buyer receives | Seller's remaining entitlement |
|---|---:|---:|
| Cover wins | 100 | 0 |
| Cover loses | 0 | 100 |

The seller received a premium of 30, but it is part of the backing while the obligation remains. It is not simultaneously free money to withdraw.

This rule applies equally to a professional maker and an ordinary user selling protection. Neither receives a special right to leave obligations underfunded.

## 7. What does netting mean?

Netting means checking the combined obligations against the same possible histories. The engine does not decide from cover names or statistical correlation.

### When both covers can win

Suppose A and B each pay 100, and all four combinations are possible:

| Outcome | Total seller obligation |
|---|---:|
| Neither wins | 0 |
| Only A wins | 100 |
| Only B wins | 100 |
| Both win | 200 |

The gross backing requirement is 200. If the seller receives premiums of 30 and 40, another 130 is needed for this otherwise empty account, ignoring fees.

A goal in a window and a player being substituted can both happen. They do not earn a collateral reduction merely because they belong to the same match. Both facts would also need to be supported by the market's state model.

### When both covers cannot win

Suppose cumulative rainfall cannot decrease:

- A pays 100 if rainfall by noon is at least 10 mm.
- B pays 100 if rainfall by evening is below 10 mm.

Both cannot win normally. If the cancellation rules also never make both pay, their combined maximum obligation is 100.

If their premiums are 30 and 50, the seller adds 20, making 100 total backing.

**Netting is a consequence of the complete payout rules. There is no manual “net these two covers” switch.**

The current design does not net unrelated markets. Covers must share an explicitly modeled joint event process for the engine to evaluate their combined possibilities.

## 8. How does the engine find the worst case?

It combines all the account's cover payouts on the event map, then calculates the smallest entitlement the account could have along any permitted route.

It works backwards through the map, reusing results for shared continuations. It does not need to list every complete route separately.

- If the smallest entitlement is negative, the proposed account needs more backing.
- If it is zero, the account is funded but has no guaranteed surplus.
- If it is positive, that amount is available to withdraw.

The calculation includes cancellations and failures. Checking only normal outcomes could incorrectly release money needed on an exceptional outcome.

The map and account still need size limits. A complicated cover can make verification too expensive. The engine must reject unsupported complexity, including cases that would make later settlement unaffordable.

## 9. What is the oracle's job, and what is the kernel's job?

The oracle supplies observed information through the market's agreed reporting process. It does not supply all possible futures: those possibilities are already part of the market definition.

The kernel enforces what accepted observations mean for payouts and funding.

There is an important distinction:

| Status | Meaning for the engine |
|---|---|
| Reported or provisional | Information has arrived, but it can still be revised under the rules. It may pause trading or invalidate quotes. |
| Contractually final | The agreed process has made its consequences irreversible for this market. The engine can exclude incompatible histories. |

A reliable source and a final contractual observation are related, but different concepts. A source can issue a correctable report.

If a provisional report says a cover won, the engine cannot release its backing while a permitted correction could make it lose. When the required fact becomes final, the engine can resolve the claim if its payout is now fixed.

Conflicting data cannot simply erase every possible outcome or restore outcomes already excluded by contractual finality. It must follow the market's declared conflict procedure.

## 10. Why do progressive and end-finality markets differ?

**Progressive finality:** parts of the event can settle permanently while the rest continues.

For example, the 60–70 minute window is contractually finalized and a cover pays 100. Under the standard progressive policy, a later match cancellation does not undo that payment.

**End finality:** earlier reports remain provisional until the market's closing procedure.

The same cover might appear to have won at minute 70, but its payout is not yet permanent. A later cancellation follows the agreed unresolved-cover rules, which might pay zero.

These policies need different accounting histories. We cannot release money as permanently won and later pretend that the same obligation can be reversed without separately funded backing.

Cancellation is a defined settlement outcome. It is not an automatic refund or a rollback of premiums, fees, and earlier payments. Every market must state its policy clearly.

## 11. When can a user redeem a claim?

A cover is resolved when it pays the same amount on every remaining permitted history, including exceptions.

The engine can then replace that cover holding with its fixed cash credit. A winning 100-unit claim becomes a 100-unit credit; a seller's matching obligation becomes a debit. This conversion does not itself transfer tokens out of escrow.

The engine records the conversion so the same cover cannot be credited twice. It can do this when an account is accessed, rather than updating every holder in one transaction.

A standalone buyer with a finalized 100 payout and no other obligations can withdraw that 100. If the same account has other sold covers, some money may still be needed to back those obligations.

At complete settlement, every account can claim its remaining entitlement. Earlier withdrawals and credits are counted, not paid again. The last timestamp alone is insufficient if a payout still depends on a missing earlier observation.

## 12. What happens when someone buys a cover?

Conceptually, the operation proceeds as follows:

1. Check the market status, exact cover, time window, offer expiry, and current market version.
2. Check that the participants authorized these terms.
3. Calculate the cover transfers, premium, fees, and any authorized deposits or withdrawals.
4. Calculate each affected account's complete resulting position.
5. Verify that the actual funds are available and every resulting account remains funded.
6. Commit everything together.

If any check fails, none of the trade is committed. The engine cannot charge the buyer while failing to establish the seller's obligation.

It also cannot silently take additional money from someone's wallet. Any required external funding must be authorized.

## 13. How do quotes and standing offers differ?

A **package quote** authorizes one exact proposed transaction using specified account and market versions. If those conditions change, the quote may need to be refreshed and signed again.

A **standing offer** authorizes a bounded set of fills: a particular cover, price rule, quantity, fees, expiry, and cancellation rules. A buyer can accept part of it if the signed terms permit partial fills.

Every fill still checks current funding. An unreserved offer may stop being executable because another trade used the seller's capacity. Being listed does not itself guarantee a fill.

The engine tracks filled quantities and cancellations so a signed offer cannot be reused beyond its authorization. Market updates advance a version called an **epoch**, which normally invalidates older offers. Account changes have separate revision numbers.

Any future reservation feature would need to back all commitments that could execute together. It cannot promise the same free funds independently to multiple buyers.

## 14. What happens if someone wants to exit?

There are two different operations:

**Sell selected covers.** This changes the account's mix of rights and obligations. Removing a cover can remove protection that was backing something else, so the remaining account must be checked again. An exit can require extra funding.

**Sell a fraction of the complete position.** This transfers the same fraction of both holdings and the signed cash component. The buyer explicitly accepts the whole package, including any negative cash component.

For a funded seller, an exactly representable complete-position sale preserves funding when the sale proceeds cover the seller's fee. The buyer must also pass the funding check.

Neither operation guarantees a willing buyer or a good price. Selling a position does not transfer wallet ownership or account permissions.

## 15. Why are exact amounts important?

The engine uses whole numbers in the settlement token's smallest unit and executable cover lots.

It cannot independently round the buyer's and seller's balances, because that could create or lose money. A percentage exit must be exactly representable, or the user must approve a different executable quantity.

All calculations have bounds. A transaction that exceeds arithmetic or resource limits fails rather than producing an approximate funding answer.

## 16. What exists today?

The [Python reference model](model_v2/README.md) implements the baseline event representation, combined-account verification, and a simulated ledger. The [recorded results](model_v2/results.md) include funding, cancellation, correction, settlement, and lifecycle checks.

This demonstrates accounting behavior on specified examples and generated cases. It does not establish real-world data accuracy, onchain affordability, live seller profitability, or production security.

Real contracts, signatures, token custody, oracle adapters, and concurrent backend services still need implementation and testing. The reference model provides expected behavior against which those implementations can be checked.

The rule every implementation must preserve is:

> Every accepted account remains fully funded across every settlement history still permitted by its market's rules.
