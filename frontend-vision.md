# AsceMarket — landing page and frontend direction

Based on [AsceMarket.md](AsceMarket.md) and the clarification that anyone can buy or sell covers under the same funding rules.

This is a proposed product experience, written in simple words. It describes the bigger product, not a testnet interface or a claim that every screen already exists. All example prices below are illustrative.

## 1. What the whole website should communicate

**AsceMarket lets you choose financial protection against specific things that might happen, and change that protection as the future unfolds.**

That is the main idea. The user should not need to understand the kernel, collateral mathematics or the word “netting” to start.

A cover is a simple promise with clear terms:

> If this defined situation happens, this cover pays you this amount.

Some covers pay a fixed amount. Others increase their payout as a measured value moves, up to a stated limit. Each cover explains the event, time, payout and cancellation rules.

Someone buys that promise. Someone else sells it and supplies the required backing. The platform checks that accepted trades remain funded.

The landing page explains why this is useful. The application helps people actually choose, buy, sell and manage it.

## 2. My overall recommendation

Use a calm, clear financial-product design with a strong visual demonstration of cover.

The landing page should feel broad and forward-looking: prices, weather, events and other measurable uncertainty can all fit the vision. The application should be concrete: these are the markets and executable covers available now.

Give users familiar market discovery, then a more thoughtful position and protection experience inside each market.

Do not make everything look like a list of Yes/No tickets. Also do not open with a blank chart and expect a new user to draw a financial contract.

The experience should make three things obvious:

1. What am I covered for?
2. What does it cost or require from me?
3. What happens to my money in the different possible outcomes?

## 3. Landing page: the first screen

### Suggested headline

**Protection for what comes next.**

### Suggested supporting text

> Choose cover for prices, events and the changes that matter to you. Combine it into one position for each market, and adjust it as the future unfolds.

A short explanation beneath it:

> Buy a defined payout. Or sell cover with the required backing. See what changes before you trade.

### Main actions

- **Explore covers** — opens the available markets.
- **See how it works** — moves to a simple interactive explanation.

Do not require login just to understand the product or browse markets. Ask users to sign in when they want to trade or save their position setup.

If trading is not available yet, the primary action should clearly open a product preview or waitlist. Do not send people into a flow that pretends they can buy live cover.

### The main visual

Put a clear cover example beside the headline, rather than an abstract illustration that does not explain the product.

For example:

```text
Protect against a price drop

Protection starts below           3,000
Maximum payout                    200 USDC

Price at observation              Cover payout
3,100                             0
2,900                             100
2,800 or below                    200

[Move the example price]

Illustrative payout — not a live quote
```

The visitor moves the example price and sees the payout change. This demonstrates the meaning of cover before asking them to learn the rest of the product.

The example must show that protection has limits. A maximum payout of 200 is not unlimited protection against every loss.

## 4. Landing page: explain the vision through examples

Below the first screen, show three examples of why someone would want cover.

| Example | Simple explanation |
|---|---|
| A price moves against you | Choose a payout that grows when the measured price falls below your threshold |
| Weather affects your plans or business | Choose a payout tied to a defined weather measurement |
| A live event changes | Add protection against a particular result or window while the event unfolds |

These examples show the breadth of the idea. Mark concepts that are not available to trade as examples of the vision, and keep them separate from actual listed markets.

For external exposure, explain that the cover follows its stated measurement. A weather payout does not automatically reimburse every business loss; a price cover does not necessarily match the user's entire portfolio.

### Suggested section heading

**Different futures. Cover you can understand.**

The focus is the user's situation, not a catalogue of technical cover types.

## 5. Landing page: demonstrate how cover changes a position

Show a three-step story:

1. **Choose what you want protection against.** Select an event, threshold or time window.
2. **See what changes.** Compare what your position pays before and after adding the cover.
3. **Accept the complete trade.** Review the price and money required, then confirm.

The visual should start with an existing position, add one cover and show the resulting payout scenarios.

Suggested heading:

**Add cover. See your whole position.**

This is where we show the difference between buying another disconnected ticket and understanding all related exposure together.

For a live event, use a small scenario table. For a single price observation, use a payout curve. A single final-score chart cannot explain a payout that also depends on when a goal happened.

## 6. Landing page: explain the funding promise simply

Use a short section with the heading:

**Every accepted trade must be backed.**

Suggested copy:

> The system checks the combined position of every participant. Before a sale completes, enough funds must be held to meet its obligations in every permitted outcome.

Then explain the useful part:

> When related obligations cannot both pay, the system can recognize that overlap and reduce the backing required. When both can pay, both must be funded.

A two-option example could make this understandable:

| Two 100-USDC obligations | Maximum combined payment |
|---|---:|
| A goal and no goal, for the same defined window | 100 USDC |
| A goal and a player substitution, when both can happen | 200 USDC |

This illustration assumes the published cancellation rules do not create a larger combined payment. State that beneath it.

Do not turn this into a claim that every trade uses less money, or that the platform offers guaranteed profit. The benefit depends on the actual obligations and their rules.

## 7. Landing page: buying and selling are both part of the product

Suggested heading:

**Buy protection. Provide it. Or do both.**

Suggested copy:

> Anyone eligible to trade can buy or sell supported covers. Sellers review the premium they receive and the backing their resulting position needs. Everyone follows the same funding rules.

A maker is simply someone who regularly offers prices. Do not make the public product imply that only approved professional makers can sell, unless a specific access policy is introduced later.

The interface can offer advanced quoting tools without creating a different accounting system or privileged seller role.

End the landing page with **Explore covers**, plus links to how settlement works, market rules and the product explanation. Use measured claims and real examples rather than invented volume, customer logos or testimonials.

## 8. The application: main navigation

Keep the main navigation small:

| Page | Purpose |
|---|---|
| **Markets** | Find an observation or event and its available covers |
| **Portfolio** | Understand and manage positions across markets |
| **Orders** | Track active offers, pending requests, fills and cancellations |

Put wallet/account settings in the account menu. Keep product explanations accessible through Help or How it works.

Customizing protection belongs inside a selected market, where the system knows the observation and supported rules. A separate global “Build anything” screen would suggest more freedom than the engine or available liquidity may support.

## 9. Markets page

This page answers: **What can I get cover for?**

Include search, useful category filters and a clear distinction between open, paused and completed markets.

Each card should show:

- The observation or event.
- The relevant date, expiry or live stage.
- A few examples of available covers.
- Whether quotes are currently available.
- A clear action: **View covers**.

Example:

```text
Barcelona vs Real Madrid
Live · 60 minutes · 1–0

Available covers
• Real Madrid scores between 60 and 70 minutes
• Final score is exactly 1–0
• Barcelona wins

[View covers]
```

The same market can contain several cover types only if its declared observations support them. Do not show a player-substitution cover merely because we already receive match scores.

Price labels must distinguish a live offer for a stated quantity from an estimate. Avoid a misleading “from” price that cannot actually be accepted for the user's requested size.

## 10. Market detail page

On desktop, use three clear areas:

```text
Event / observation, timing, source and current status

Available covers       Your position and scenarios       Trade panel
                       What you hold now                 Buy or sell
Choose a cover         What the proposed change does     Set amount
                       What remains uncovered            Get quote
                                                         Review and accept
```

These are conceptual areas, not a requirement to force three narrow columns onto every screen. The position view should have enough space to explain the exposure.

### Event information

Show the current observation, important checkpoints and the source. If the displayed score is provisional, say so. If the oracle has finalized a window, show **Result final**.

Keep live event display separate from contract settlement status. A live score changing does not mean every cover has settled.

### Available covers

Each cover should be a plain sentence with fixed terms:

> Pays 100 USDC if Real Madrid scores between minutes 60 and 70.

Show its observation window, payout rule, cancellation terms and quote availability. A compact card can expand for the full rules.

### Your combined position

For users with existing exposure, show their whole current position before suggesting another purchase. Preview what adding the selected cover changes.

For new users, show the proposed cover's payout and an explanation of when it pays zero. Do not fill an empty account view with meaningless charts.

## 11. Buying a cover

The main flow is:

**Choose cover → choose payout size → get quote → review → buy.**

An illustrative ticket for a fixed-payout cover could read:

```text
Real Madrid scores between minutes 60 and 70
Payout if the condition is met     100 USDC

Cover price                        30 USDC
Platform fee                        1 USDC
Total trade cost                   31 USDC
Additional wallet funding needed  31 USDC

If this cover pays                 Receive 100 USDC
If it does not pay                 Receive 0 USDC
Cancellation                       See this cover's stated rule

[Review and buy]
```

This example assumes a new, empty account, immediate spending of the premium and fee, and no network charge. Existing account funds may reduce the additional wallet funding needed. Always show any actual network charge separately and include it in the final spending total.

A 100 payout is not 100 profit. For this example, profit would be 69 if it pays and a loss of 31 if it does not, excluding external holdings and assuming no later trades or costs. Cancellation outcomes must be included before claiming an overall worst loss.

After execution, show a receipt and the updated position. Before confirmation, show **Transaction pending**, not a completed purchase.

## 12. Selling a cover

Use the same market and a clear **Buy / Sell** selection. Selling needs its own explanation; it must not look like a button that simply collects free premium.

For a new account, an illustrative no-fee sale might show:

```text
Sell cover paying up to            100 USDC
Premium you receive                 30 USDC
Additional backing you provide      70 USDC

Funds held after the trade         100 USDC
Available to withdraw now            0 USDC

[Review and sell]
```

Explain:

> The premium contributes to the backing. It is not necessarily money you can withdraw immediately.

For an existing position, replace standalone assumptions with the actual combined funding calculation. Show the additional funding required after all offsets, payments and fees.

If the user sells two covers that can both pay, show the resulting combined obligation. The account's existing compatible claims may help fund it, but the fact that the user is a maker does not change the rule.

Defining a cover, posting an offer and executing a sale are different states. An unreserved offer may later fail a funding check; do not describe it as guaranteed liquidity.

## 13. Customizing protection

Inside a market, offer **Customize cover** alongside the listed choices.

Ask useful questions, depending on the market:

- Which situation should trigger a payout?
- Which observation or time window matters?
- How much should it pay?
- What is the maximum the user wants to spend?

Use structured controls first. A price market might use thresholds and a chart. An event market might use conditions and time windows.

The result should clearly say:

- **Exact match:** this proposed cover matches the request.
- **Closest available:** this is what differs, and where the requested protection is missing.
- **Unavailable:** explain whether the limitation is the market's supported rules or the absence of an acceptable seller.

A custom request is still a request. It does not create coverage until an accepted, funded trade executes.

## 14. Portfolio page

This page answers: **What protection do I hold, what can happen to it, and what can I do next?**

Show separate positions by market. Each position combines that market's covers and displays:

- A plain summary of the exposure.
- Appropriate payout scenarios or a curve.
- Funds available to withdraw.
- Finalized amounts and unresolved exposure.
- Cash deposited and withdrawn, with an understandable profit/loss basis.
- Actions to add cover, change the position, reduce it or request a full exit.

Do not add each market's possible maximum payout and call it a guaranteed portfolio value. Any estimated sale value must be labeled as an estimate unless backed by a current executable quote.

Wallet funds and funds held in separate markets stay visibly distinct. A portfolio overview does not create cross-market collateral sharing.

## 15. Reducing, exiting and claiming

Use separate actions with clear meanings:

| Action | What it does |
|---|---|
| **Change protection** | Requests a new combination of covers |
| **Reduce position** | Requests a quoted sale of a fraction of the complete funded position |
| **Sell whole position** | Requests a quote for all remaining exposure and account entitlement |
| **Withdraw available funds** | Moves the guaranteed withdrawable amount to the wallet without requiring a buyer |
| **Claim payout** | Redeems the remaining settled entitlement |

Before a reduction or exit, show money received or paid, any additional deposit, fees and the protection left afterward. A selected-cover close can require additional money even when reducing the whole funded position would not.

A finalized winning cover may still be backing other obligations in the same account. Show both **Finalized payout** and **Available to withdraw** when they differ, with a simple explanation. Do not present a claim button that offers more than the combined account can release.

Keep history after an exit. Closing a position is a new executed transaction, not deletion of its earlier trades.

## 16. Important states to design deliberately

| Situation | What the user should see |
|---|---|
| No counterparty offers the trade | “No quote available. Try another amount or request again.” |
| Market update invalidates prices | “Event update in progress. Quotes will refresh.” |
| Quote expires | “This quote expired. Get a new quote.” |
| Not enough funds | Exact additional amount required; acceptance disabled |
| Request cannot be represented | What the market supports and why this request does not fit |
| Transaction is submitted | Pending status with a way to inspect its progress |
| Connection is lost after submission | Status being checked; do not assume the trade failed |
| A result is final | The resolved cover, its payout and the account's withdrawable amount |
| Event cancellation | What happens to finalized and unresolved covers under the published rules |

These messages belong in the core flow. Users should not need technical knowledge to distinguish an unavailable quote from a failed transaction or an unresolved event.

## 17. Visual direction

Use generous spacing, clear typography and strong emphasis on the few numbers that matter. A light neutral background with dark text and one distinctive accent color would fit the protection theme well. Dark mode can follow the same hierarchy if that is the preferred brand direction.

Give current and proposed payouts consistent visual treatments. Keep “covered,” “uncovered,” “pending” and “final” distinguishable through text and symbols, not color alone.

Motion should explain a change: adding a cover, updating a scenario or releasing available funds. Avoid decorative motion around money amounts that makes them harder to read.

Build for desktop first, as already chosen. On smaller screens, stack the scenario preview above the trade review so users still see the consequences before accepting. Charts need readable table alternatives, and all editing controls need exact numeric inputs and keyboard access.

Do not use probability percentages simply because a cover has a price. Show the actual payout and executable cost unless there is a separately justified probability calculation.

## 18. What I would design first

Create these screens as one connected journey:

1. Landing page with a simple interactive cover example.
2. Markets page with a small, understandable selection.
3. Numeric market detail with a payout curve.
4. Live-event market detail with scenario payouts.
5. Buy and sell quote reviews, including an existing position.
6. Portfolio with change, reduction and full-exit requests.
7. Final-result and withdrawal/claim states.

This sequence makes the bigger vision tangible while proving the central user experience. The first design should demonstrate both sides of the market and at least one situation where a cover leaves an important risk uncovered.

**The landing page should make someone think, “I can choose cover for what matters to me.” The application should let them answer, “I know what I bought or sold, what it costs, and what can happen to my money.”**
