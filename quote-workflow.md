# AsceMarket: quote and accept a portfolio change

**Product promise: see the complete trade, fund the resulting portfolio, and explicitly approve the money required.**

Status: proposed workflow, checked numerical examples, and researched alternatives. The accounting model exists. The interface, quote service, reservations, real signatures and integrations described here do not. See [evidence and alternatives](research/workflow-evidence.md), [core accounting](core-design.md), and [executable scenario results](research/workflow-checks.json).

## The decision this specification addresses

The core thesis is efficient funding of compatible bounded exposure throughout its lifecycle. Editing is the way users express a trade; it is not a substitute for demonstrating a funding or execution advantage.

What the user edits is their account's payout across every permitted state of the observation, as described in [ps.md](ps.md) and section 1 of [core-design.md](core-design.md). The interface therefore quotes a change to one vector, not a basket of separate instruments, and the funding figure it displays is a property of the resulting whole rather than of any component. This is why an exit is quoted against the remaining account and why a “close one leg” action can require money rather than release it. Start with people who hold or change such portfolios. The first scope is one numeric observation, one settlement asset and one exact package offer from one provider. The provider supplies the entire opposite payout change. Comparing several complete offers is allowed; assembling partial offers from several providers comes later.

The engine remains an independent design. References to other venues, protocols and possible adapters are competitive comparisons, not a decision to use them.

The three cases deliberately include a standard trade, a custom boundary edit and an account funding operation. They test different claims. None assumes AsceMarket has cheaper prices or guarantees a fill.

All quoted prices below are illustrative. Settlement amounts are in USDC-equivalent units; network costs are excluded from the arithmetic and must be displayed separately before any real authorization. These are derivative-only results, not protection guarantees for assets held elsewhere.

### The funding promise the interface must explain

**The current portfolio is funded through settlement. Every later trade, including an exit, gets a new funding check.** A price move alone does not require a deposit for an unchanged portfolio. Closing a component can remove an offset and require more money. Two mutually exclusive settlement promises can both lose money if closed at different times.

The initial deposit is not a lifetime trading-loss limit. A user may refuse to add funds, in which case some individual exits cannot execute. The interface must never imply that an open market guarantees an affordable exit or that an atomic package guarantees a favorable price.

Show three distinct amounts: **money moving now, net personal cash committed after the change, and the remaining payout at settlement**. Label profit/loss with its basis and the assumption of no further trades. Track peak personal funding separately in account history; do not label the current deposit requirement as the lifecycle peak.

## One flow for all three cases

1. **Choose or edit the payout.** Select the observation and the position to change. Set a threshold, capped amount or reduction. Display the existing and proposed *whole account* payout; preserve all exposure not selected for editing.
2. **Request a price.** Send the explicit payout change and size to providers. The initial preview is an estimate until an offer arrives. Changing any input invalidates the displayed offer.
3. **Review an offer.** Show the resulting payout, exact trade payment, all protocol/provider fees, wallet debit or credit, net personal cash committed after the change and expiry. For an exit, explain any additional funding needed for the remaining positions. Compare complete offers for identical terms. A required deposit is not the trade price, and released collateral is not profit.
4. **Accept the exact change.** The user approves one package. Every participant's approved change executes together, or account state remains unchanged. A wallet may require its own confirmation. Initial account funding and token approvals are separate setup operations, not hidden behind a “one click” claim.
5. **Confirm the result.** Until execution is confirmed, display “Pending.” The receipt shows the actual cash movement, resulting payout and execution identifier. A lost connection does not establish failure.

The interface should always answer: **What changes? What moves now? What can I receive later?**

## Case A — Buy capped downside protection

**User intention:** “For one ETH of exposure, pay me as the expiry price falls below 3,000, up to 200. The trade price and its fee must not exceed 65.”

For comparison, use the ETH_USDC expiry observation on 25 September 2026 at 08:00 UTC. Align the observation definition before comparing venues. Normal-outcome payout:

```
G(x) = min(max(3000 - x, 0), 200)
```

It pays 200 at or below 2,800, 100 at 2,900 and zero at or above 3,000. The example contract explicitly pays zero on VOID; this is not a claim that another venue uses the same exceptional terms.

The user selects the protection preset, enters 3,000 and 200, then requests the price. No option-leg selection is required in the proposed interface.

```text
Protect below 3,000 · payout capped at 200
Observation: ETH expiry, 25 Sep 2026, 08:00 UTC

Trade price                              64
Fee                                       1
Wallet debit                             65
Settlement payout                     0–200
Worst loss if held to settlement         65
Best profit if held to settlement       135
VOID payout                               0

[Accept — pay 65]       Offer expires at the shown time
```

Those profit figures include the quoted fee and use a zero-position starting point. They exclude external holdings and network cost. Before real acceptance, any additional network cost needs its own visible spending limit; a user who sets an all-in budget must have that cost included. The provider contributes 136; together with the user's 65, escrow is 201, including the treasury's fee entitlement of 1.

**Strongest existing route:** buy the 3,000 put and sell the 2,800 put at the same expiry as an eligible package. Both puts appear in the captured catalogue. The payoff identity is exact for normal outcomes. Deribit documents a single-price put-spread combo mechanism; actual route availability, price and account funding were not tested. [Combo mechanics](https://support.deribit.com/hc/en-us/articles/31424954956061-Combo-Books), [catalogue snapshot](research/deribit-catalog-2026-09-17.json).

**Result:** this is a control case. A payout editor could translate the intention to the existing spread. AsceMarket must demonstrate clearer understanding or less work; it has not demonstrated a new payoff, fewer necessary trade authorizations or lower collateral here.

## Case B — Move protection to a personal threshold

**User intention:** “My relevant price is now 2,873. Move the start of my protection there, keep the same 200 cap and expiry, and return any money released.”

Begin with Case A's position. The new payout is:

```
H(x) = min(max(2873 - x, 0), 200)
Requested change = H(x) - G(x)
```

The user opens the position, changes the start to 2,873, and sees the full-payout point move to 2,673. The old and new curves remain visible together. The engine must not quietly round the request to a listed strike.

```text
Move protection start: 3,000 → 2,873
Keep the 200 payout cap and the same expiry

Net trade credit                         15
Fee                                       1
Wallet credit                            14
Additional deposit                        0
Remaining settlement payout           0–200
Net spend since opening                  51
VOID payout                               0

[Accept — change protection and receive 14]
```

The quote is for the entire change. Its 15-unit credit is not obtained by adding two uncommitted indicative leg prices. The user originally paid 65 and now receives 14, so the cumulative derivative-only profit range is -51 to 149. Receiving 14 is not itself a realized-profit calculation.

That range assumes the new portfolio is held to settlement without further trades or costs. The history's peak funding remains 65 even though net spend has fallen to 51. A later exit gets its own price and funding check.

Relative to keeping the old payout, the combined change in cash plus final entitlement ranges from **-113 to +14**. The reduced protection can matter substantially even though cash is returned. This comparison belongs in the preview alongside the payout chart.

The model checks a provider deposit of 15, a user withdrawal of 14, and a second fee credit of 1. Escrow becomes 202, of which 2 belongs to treasury. The final user profile is exactly `H`, including its exceptional value.

**Listed-instrument alternative:** the captured expiry has neither 2,673 nor 2,873. A finite portfolio of ordinary same-expiry vanilla options is affine between its listed strikes, so it cannot create an exact new kink inside one of those intervals. This is a mathematical limitation of that particular basis, not a claim that all existing infrastructure lacks custom contracts.

A stronger approximation than simply rounding the threshold is:

```
0.5 × (put(2850) - put(2650))
+ 0.5 × (put(2900) - put(2700))
```

All four strikes appear in the snapshot. The checked maximum absolute normal-outcome payout error is **13.5** per unit of this example. This is one candidate approximation, not the optimal one. Quotes, total fees and package eligibility have not been verified. Rolling from the original two-leg spread to this four-leg portfolio entails up to six signed leg quantities; eligible RFQ packages are a credible execution alternative. [Block RFQ](https://support.deribit.com/hc/en-us/articles/25951371614621-Deribit-Block-RFQ).

**Custom-contract alternative:** DIVA can parameterize the desired ramp without that strike grid. An adapter that closes the old complementary pool positions and creates the new pair could plausibly reproduce the atomic edit. That route still needs implementation validation. [Inspected mechanisms and limits](research/workflow-evidence.md#diva-a-custom-payout-and-signed-offer-are-also-existing-mechanisms).

**Result:** exact custom boundaries are a measurable capability relative to this listed catalogue. They are not yet a unique AsceMarket capability. The product question is whether an exact boundary matters enough to this user, and whether repeated changes are simpler or cheaper than the custom-contract adapter.

## Case C — Reduce two obligations and release funds

**User intention:** “Halve both of my tail obligations and tell me what I can withdraw, without leaving the other obligation underfunded.”

Use the existing model's illustrative numeric index, with low below 95 and high at or above 105. This is a separate example market, not a claim about a listed ETH contract. Let `L` and `H` each pay 100 in their respective tail and zero on VOID. The user's starting final balance is `100 - L - H`, funded by a net contribution of 46 after receiving premiums of 54.

Here the two obligations were opened together, making opening peak funding 46. Opening the full low obligation first would have needed 78; opening high first would have needed 68, even though either sequence finishes with 46 committed. These are different execution paths, not interchangeable funding claims.

For this example, one provider holds both tail claims. A 50% reduction transfers half of both back to the user. It needs only one provider to supply the whole change; the demonstration does not assume an unimplemented multi-provider matcher.

```text
Reduce both tail obligations by 50%

Funding released before trade costs      50
Buyback payment                          27
Fee                                       1
Wallet credit                            22
Additional deposit                        0
Remaining obligation in either tail      50
Net personal cash committed to date       24
Worst total loss if now held to settlement 24

[Accept — reduce both and receive 22]
```

The final user balance is `50 - L/2 - H/2`. It pays zero in either tail, 50 in the middle, and 50 on VOID. The provider retains half of each claim and withdraws 27; treasury receives 1. Remaining escrow is 51. The original 46 contribution falls to 24; the 22 returned includes released backing and must not be labelled trading profit.

The 24 maximum total loss is measured from opening this example account and assumes no later trades or costs. Peak personal funding to this point remains 46. The user has not reduced that historical peak by withdrawing cash.

**Strongest accounting alternative:** a four-outcome conditional claim construction can merge 50 complete sets and reproduce this funding exactly. A suitable router can be considered for one authorized package; its execution implementation is not supplied here. [Construction and source](research/workflow-evidence.md#conditional-tokens-a-stronger-accounting-baseline-for-the-tail-example).

Polymarket's current collateral-return workflow is also relevant precedent for preserving residual exposure while releasing compatible backing; it is not evidence that this exact synthetic market is available there. [Collateral return](https://docs.polymarket.com/trading/combos/collateral-return).

**Result:** the engine releases backing that the remaining obligations cannot need, but no unique capital saving is established against the stronger accounting alternative. The next question is whether an existing route can execute the same funded change with comparable cost and restrictions. Separately executed full legs are a weaker comparison; sliced execution must also be considered, as in [the existing funding measurements](model/results.md).

### Case C stress branch — Close just one obligation after a price move

Reset to the original two obligations and the 46 contribution, **before** the 50% reduction above. Use zero fees in this separate branch to isolate funding. The user asks to close only the low obligation, now quoted at 90, while retaining the high obligation.

```text
Close the low obligation only
Keep the high obligation unchanged

Buyback payment                              90
Fee                                           0
Additional deposit required                   90
Net personal cash committed after this trade  136
Remaining high-outcome obligation            100
Remaining settlement payout                0–100
Worst total loss if then held to settlement  136

Closing low removes an offset. The remaining high obligation
still needs full backing after paying the buyback price.

[Accept — deposit 90 and close low]
```

The button is available only within the user's authorized spending limit and when the required wallet funds are available. If the original 46 was all the user had, the wallet has no additional funds: show “90 more required” and disable execution. Do not silently draw other funds or close the high obligation instead.

The user can choose to supply funds, request a separately quoted complete change, or keep the current position. A package that also closes high is a different instruction; it is not an equivalent fallback for a user who wants to retain high exposure.

If the user funds this exit, then later closes high for another 90, the second close releases 10. Total realized loss is 126 and peak personal funding is 136. The original two promises could not both pay at settlement, but they could both be costly to close at different times. The [capital challenge](research/capital-challenge.md) executed this branch and verified rejection without the additional funding.

This branch is required reading alongside the favorable 50% reduction example. Both use the same accounting rule; the selected trade and its price determine whether funds are released or required.

## What a quote must bind

The user edits a selected exposure; the compiler produces an explicit signed payout delta `D`. The whole-account candidate is:

```
W_after = W_before + D - trade_payment - fee + external_cash_flow
```

Payout deltas between user and provider cancel, including VOID. Existing positions outside the edit remain in `W_before`; the engine checks their combined worst result too. A drawing or natural-language instruction is not an executable contract until converted to explicit terms.

| Object | Required content and behavior |
|---|---|
| Request | Stable request ID; requester and account revision; complete market/asset/precision identity; exact payout delta and size; separate trade-price and maximum-additional-deposit limits; desired treatment of guaranteed cash; all-or-nothing size |
| Offer | Request ID and unique quote ID; complete proposed batch and both expected revisions; exact net payment, fees and cash flows; resulting account profile; additional funding for any retained obligations; provider approval; expiry; conditional execution status |
| Acceptance | User approval of the exact batch and quote identity; an idempotency key; no authority to reprice, round a boundary, replace the provider or choose a partial size |
| Receipt | Stable execution ID; final status; accepted payload hash; actual cash/fee movements; resulting account revision and profile; settlement reference where applicable |

The current model binds batches, revisions, fees and expiry. It does **not** implement durable request/quote IDs, an acceptance store, authentic signatures, cancellation ordering or a network confirmation service. Those are requirements for a future quoting implementation.

The quote layer must also compute cash-history and loss-basis labels consistently. Those labels are not additional collateral or a separate claim on funds. The exact approved cash flow controls how much the ledger may take; a broad “close position” instruction is not permission for an unbounded deposit.

The provider needs the requested change to price it and its own account state to assess funding. Broadcasting the user's full portfolio is not required by this design. The user's complete account is checked by the clearing engine.

### Offer validity is distinct from a guaranteed fill

Initially, the quote is a **fixed-price conditional execution offer**. It must pass revision, expiry, authorization and funding checks when executed. Do not describe it as reserved or guaranteed. No discretionary maker last look is proposed after acceptance; a state-validation failure is still possible.

The existing revision rule means that one maker fill can invalidate its other outstanding offers in the same account. The first experiment can serialize offers, but that does not establish production suitability. Measure this conflict before selecting reservations or another concurrency design. A reservation must account for all outstanding commitments; independently checking each offer against the same free funds would double-count capacity.

### Failure and recovery behavior

| Situation | Required user-visible behavior |
|---|---|
| No quote | Keep the draft and existing position. Offer a changed size or limit only as a new user decision. |
| Quote expires or account changes | Disable acceptance; show that the offer needs refreshing. Requote and request new approval. |
| Provider changes price | Invalidate the old offer only under the defined cancellation order. Never edit an already approved payload. |
| Funding check fails | Execute no portfolio change; explain which required funds or state changed. |
| Requested exit needs more than the authorized deposit | Show the required amount and retained exposure; do not execute. Any higher deposit needs a new exact approval. |
| Exit quote costs more than holding through settlement could pay | Show both the quoted cost and settlement payout bounds. Do not call the quote loss-bounded by the original deposit. The user can decline it. |
| A component cannot execute | Reject the complete package. No silent separate-leg fallback. |
| Double click or retry | Return status for the same acceptance; do not create another trade. |
| Connection lost after acceptance | Mark status unknown/pending and recover by request/execution ID. Do not automatically submit a replacement trade. |
| User cancels while execution races | Acknowledge cancellation only once the authoritative ordering establishes it preceded commitment. Otherwise show the committed result. |
| Transaction submitted but reverts | Preserve portfolio state; disclose any incurred network cost. “No trade” is not necessarily “no cost.” |

## What each participant gains and pays

The user pays the quoted net consideration and disclosed fees, or receives a net credit. The provider takes the opposite payout change, supplies any required backing and prices its inventory change. Provider profit is not guaranteed by the accounting. Treasury receives the explicit fee. No subsidy, token reward or self-trade is needed in the example arithmetic.

Users bear setup, authorization and any movement of funds into a new environment. Providers bear quoting, hedging and committed-capital costs. The operator bears quote delivery, invalidation, recovery and accounting maintenance. The independent ledger also creates a trust and maintenance obligation. Include these duties when comparing its complete cost with existing routes and when specifying the production system.

## Capital findings and the next comparison

The three quote cases and the adverse-exit branch have been checked against the model. The [full lifecycle challenge](research/capital-challenge.md) additionally measures peak funding, fee sensitivity and 625 adverse price paths. Its zero-fee comparison starts with an atomic opening:

| Path | AsceMarket peak | Exact-netting reference peak | Separate-funding peak |
|---|---:|---:|---:|
| Hold through settlement | 46 | 46 | 146 |
| Halve and close through packages | 46 | 46 | 146 |
| Close individually at 90 after a reversal | 136 | 136 | 146 |

Exact netting saves money against separate funding; an exit can shrink or erase that saving. The exact reference is arithmetic, not a deployed competitor account. The research found an existing collateral-return rule that can match the opening calculation, but did not establish the exact funded-exit behavior of that venue. Public option books were captured; they are not firm package quotes or completed trades.

The next discriminator is a **named competitor's funding and permitted exits for the same useful operation**. Match final payouts, intermediate exposure, price assumptions, fees and withdrawal availability. Do not credit AsceMarket for closing both obligations when the compared user wants to retain one. Where account access or executable quotes are missing, keep the conclusion unknown.

The subsequent [two-butterfly comparison](research/competitive-case.md) identifies a source-level funding advantage over the inspected Gamma vault architecture for a fixed put inventory, even after optimizing fractional allocation. It also demonstrates an exit path that erases the saving. This is a candidate for the next quote comparison, not a live price, general options-market advantage or confirmed user need.

The [stronger follow-up](research/competitive-followup.md) rules out removing that gap simply by adding more cash-collateralized puts under the same rules. Any future comparison card should describe the difference as **cash left available**, state the matched exposure and price assumptions, and keep fees and trading profit separate. The prepared Deribit margin requests have no authenticated results yet.

After a useful funding or execution distinction is established, test whether people understand and can operate the quote flow. A clearer editor can improve usability, but cannot by itself establish the core capital-efficiency claim. Possible adapters remain comparison controls only; this specification does not propose adopting DIVA or another settlement protocol.

### What to record

| Measure | Evidence required |
|---|---|
| Contract fidelity | Maximum payout difference over all intervals and permitted exceptional outcomes; no hidden rounding or omitted exposure |
| Complete cash cost | Premium, spread, protocol/provider fees, network costs, setup and exit costs; mark unquoted items unknown |
| Funding | Opening cash; maximum cumulative net personal cash committed across the whole path; additional deposits at each change; remaining backing; whether returned funds are immediately reusable |
| User work | Time and corrections from intention to an accepted correct offer; count setup, semantic choices, confirmations and recovery separately |
| Understanding | User correctly explains money moving now, remaining exposure and loss basis before accepting |
| Reliability | Stale/expired quotes, cancellation races, duplicate submissions and status recovery; include concurrent offers from the same maker account |
| Switching value | User supplies their own next portfolio change and states why this route is worth its known costs |

### Proposed go/change/stop criteria

First resolve the funding/execution comparison below. A later formative study can use six experienced bounded-exposure traders, including sellers. Rotate route order and use neutral labels. Ask what improvement would matter in their actual workflow before showing the new flow. This small study would screen the design, not estimate demand.

- **Correctness gate:** every supported task preserves the requested exposure and authorized cash limits. Any unauthorized exposure, duplicate execution or unsafe withdrawal blocks implementation until fixed. Approximate alternatives must display the error and obtain separate agreement.
- **Workflow gate:** at least four of six complete their relevant tasks without coaching and correctly explain the cash movement and remaining risk. They must meet their own stated improvement threshold and choose the flow for a second task drawn from their actual portfolio. This is a proposed product decision rule, not a statistical claim.
- **Capital/execution gate:** demonstrate a recurring operation for which a named competing route needs more peak personal capital or blocks a funded change that AsceMarket supports, under matched terms and acceptable total costs. Parity with exact netting or a favorable opening deposit alone does not pass this gate. If no such advantage is found, reconsider the standalone thesis rather than treating an editor as proof of capital superiority.
- **Change direction:** if exact custom boundaries do not matter to participants, narrow to ordinary strategy editing. If users misunderstand credits as profit or fail to understand reduced protection, revise the preview before broadening the product.
- **Stop the standalone thesis:** if the strongest existing workflow or a small adapter matches all relevant tasks and users identify no worthwhile remaining improvement, do not proceed with a new exchange on this evidence.

No interviews, preference results or live executions have been inferred from the scripted examples. The saved public-price replay is explicitly separated from an executable quote comparison.

## What not to build yet

Do not add a new chain, token, AMM, multi-provider solver, continuous auto-rebalancing, cross-market margin, multi-variable payouts or a general-purpose financial app suite. Keep the accounting core while investigating the specific capital or funded-exit advantage. Do not build a larger interface or rewrite the engine as a substitute for that evidence.

The working vision remains broad: **make financial exposure something people can directly shape and fund efficiently.** The immediate test is specific: can the system support a useful portfolio lifecycle with a worthwhile funding or execution advantage, and can the user correctly understand its limits?
