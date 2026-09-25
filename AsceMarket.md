# AsceMarket

## A market for cover

**Choose how your money responds as the future unfolds.**

Describe the protection you want. Buy it from makers. Combine it with what you already hold. Change it as your situation changes, while seeing what is covered, what is still exposed, and what money can move now.

AsceMarket is a marketplace and a common accounting foundation for bounded financial protection. Its unit of ownership is one funded position in a market. That position can combine many covers over the same observed process.

This document describes the product and its intended guarantees. [The v2 kernel specification](v2-kernel-spec.md) defines the accounting and verification requirements. These are design specifications, not a claim that the system has been implemented or verified.

## 1. The bigger vision

People experience uncertainty as changing exposure, not as a catalogue of instruments.

A business wants protection if cumulative rainfall stays low. A trader wants a payout if a price finishes below a personal threshold. Someone holding a live event position wants cover against what could happen next. A developer wants to build that experience without inventing a new collateral system for every protection.

The vision is one reusable foundation for these products:

- Markets define observations, possible developments and settlement rules.
- Covers define bounded payouts on those observations.
- Makers quote repeatable covers and complete changes in exposure.
- Accounts combine compatible claims and obligations.
- The engine verifies that every accepted position is funded in every permitted outcome.
- Interfaces help people choose and understand protection without manually assembling and tracking every component.

The engine should not need a football-specific or rainfall-specific accounting function. New thresholds, windows and combinations should usually be new definitions in a shared cover language. More advanced dependencies can extend that language through verified capabilities rather than bypassing the funding rules.

Generic does not mean unrestricted code or an assurance that every imaginable request has a price. A requested protection must be observable, representable, computationally verifiable and offered by a counterparty.

## 2. The product promise

**Choose the cover you want, understand how it changes your whole position, and execute the funded change together.**

The product must answer three questions before a trade:

1. What situations does this protect me against, and what remains uncovered?
2. What do I pay or receive now?
3. What can my resulting position pay later, including cancellation outcomes?

One account is not a guarantee against every loss. A window cover protects that window; a capped cover stops paying more at its cap. External exposure may differ from the observed index. The product makes these boundaries visible.

An unchanged funded position does not need more money merely because market prices change. A later trade, including an exit, is a new decision with a new price and funding check. A user can spend more over time than their initial deposit if they authorize additional spending.

## 3. The user experience

### Discover a market

A market page explains what is observed, the observation source, important times, available protections and resolution rules. The user can browse before deciding what exposure to take.

A market is one declared observation process. It may contain several related measurements, such as both teams' scores, when their joint state and transitions are explicitly defined. Sharing a platform or having correlated prices does not make separate markets eligible for netting.

### Start with an intention

The main entry points are:

| Intention | User input | Result |
|---|---|---|
| Protect an exposure | What could hurt, when, coverage size and spending limit | A proposed cover or basket |
| Take a view | Direction or result, payout size and maximum spend | A funded position proposal |
| Cover a range or window | Boundaries, time interval and amount | One or more compatible covers |
| Change existing protection | Desired remaining exposure or reduction | A complete change to the current position |

Presets and precise fields make common requests easy. Supported drawing tools and direct cover selection serve advanced users. Natural-language input, if offered, produces a proposal to review; it does not itself authorize a trade.

### See an executable proposal

The compiler translates the request into supported cover definitions and available offers. It distinguishes:

- **Exact match:** the proposed payout equals the requested payout on every relevant permitted outcome, including exceptional terms.
- **Approximation:** the difference is measured and shown, and the user explicitly accepts it.
- **Unavailable:** the engine cannot support the request, the required cover is not listed, or no maker offers acceptable terms.

Those are different reasons for refusal. The application must not replace an unavailable request with a different protection silently.

### Review and accept

Show the old and new position together, with:

- Covered situations and important uncovered situations.
- Trade payment or credit, fees and any network charge.
- Required wallet deposit and any authorized withdrawal.
- Remaining payout range and available-to-withdraw amount.
- Profit/loss with a stated cash-history basis and assumptions about external holdings.
- Exact cover definitions, fixed time boundaries, quote expiry and observation status.
- Cancellation treatment and what is already contractually final.

The user accepts one package. All agreed changes and funding movements execute together or nothing changes. Partial fills are allowed only under explicit instructions describing acceptable residual exposure and spending.

### Continue through the event

As observations arrive, the account view distinguishes reported information from contractually final information. Final facts may resolve covers or increase guaranteed funds. Neither a model prediction nor an unconfirmed report can release collateral.

The user can request additional cover, replace several covers in one package, reduce their complete position, or exit. A maker and an acceptable price are required for a trade. Withdrawing already guaranteed funds does not require a buyer.

## 4. One position, the right view

The account combines all compatible cover into one funded position. History remains available, but a list of past trades is not the primary explanation of current exposure.

Use the visualization that actually represents the payout:

- A payout curve when a single numeric result determines it.
- An outcome table for categorical results.
- Scenario tables, checkpoint views or conditional payout bands when the path matters.

Two histories with the same final result may pay different amounts. A single line over final price or score cannot represent that difference honestly. Conditional charts identify their assumptions; payout bands show the remaining range rather than an invented average.

Always separate current wallet cash, guaranteed withdrawable funds, uncertain future payout and estimated sale value.

### Example: protection on a live position

A user holds a cover paying 100 if the home team wins. They buy another paying 100 if the away team scores between minutes 60 and 70.

| Scenario | Home-win cover | Window cover | Combined payout |
|---|---:|---:|---:|
| Home wins; no away goal in the window | 100 | 0 | 100 |
| Home wins; away scores in the window | 100 | 100 | 200 |
| Home does not win; away scores in the window | 0 | 100 | 100 |
| Home does not win; away scores only later | 0 | 0 | 0 |

These are normal-outcome payouts before subtracting trade costs. The last row is essential: the added protection is partial. The market must also publish the exceptional-outcome payouts.

## 5. Generic covers, personalized positions

A cover is a bounded payout rule over a market's declared observations. It has an immutable definition shared by everyone trading it. Size, price and the owner's other holdings do not change that definition.

The language can describe families such as:

- Thresholds and ranges at a checkpoint.
- Capped ramps and piecewise payouts.
- Payout tables on categories.
- Changes between observations.
- Event occurrence within a defined interval.
- Accumulated or order-sensitive conditions when the market records sufficient state and the verifier supports them.
- Combinations of supported covers.

A new threshold or window using existing capabilities is configuration, not a new accounting framework. A new event source needs an observation adapter. A genuinely new dependency may need an additional state model or verifier capability; that is a deliberate extension with shared tests and resource limits.

“Who scores next?” needs event-order information. “A goal occurred between checkpoints” may need only a correctly defined goal counter. The system must distinguish them rather than infer information that was never recorded.

A small menu is a distribution and liquidity choice. It is not a hardcoded limit on the architecture.

## 6. Makers and execution

Makers quote standardized covers that can be reused across customers. They can also quote complete baskets of these covers against their current inventory. A package RFQ and a public market of standard covers are complementary mechanisms.

The market can support:

- Standing orders for individual covers.
- Atomic execution across compatible orders.
- One maker's quote for a complete change or exit.

An offer is a price for a defined size and set of conditions, not a universal price for every user and trade size. Quotes may differ by spread, capacity and execution terms.

The engine checks every maker's funded account. A standing order can become unavailable if another fill consumes its capacity. Firm reserved liquidity requires explicit reservation accounting; an unreserved quote is not a promise of guaranteed execution.

Material event updates can invalidate prices across the market. Suspension, cancellation and quote-refresh rules apply before stale offers can be treated as current. Accounting solvency does not protect a maker from selling at an outdated price.

Makers manage economic risk and prices. The kernel verifies funding and execution; it does not manufacture liquidity or profitable market making.

## 7. How funding works

Every account represents its remaining entitlement to the market's escrow across all contractually permitted settlement histories, including cancellation and failure outcomes.

Two rules hold:

1. Every account's entitlement is nonnegative in every permitted history.
2. The total entitlement equals escrow in every permitted history.

Related covers offset only where the market's rules prove they cannot demand payment together. Historical correlation is not enough.

If an account has at least 20 in every permitted history, it can withdraw 20. Withdrawal reduces its entitlement by 20 everywhere and reduces escrow by 20. The same funds cannot remain counted as backing.

### Three different benefits

| Benefit | What actually happens |
|---|---|
| Combined funding | Compatible obligations need less backing than if each were funded separately |
| Early payment | A cover's entitlement becomes irrevocably known before the whole market ends |
| Released surplus | New final information raises an account's guaranteed floor, allowing withdrawal |

They are measured separately. A winning cover paid early is not automatically a reduction in the seller's total liability. Deleting one losing scenario does not free cash if another remaining scenario is equally demanding.

An alternative that recognizes exactly the same offsets can achieve the same mathematical funding floor. AsceMarket's product opportunity is to make compatible protection easier to express, price, change and settle—not to claim savings over every correctly netted system.

## 8. Finality, cancellation and early release

Markets publish how reported observations become final for their contracts. A delay alone is not proof that the external source can never correct a report.

Reported or provisional facts may update the interface and suspend quotes. They cannot shrink the set used to fund trades or withdrawals until their contractual consequences are irreversible.

Markets choose their finality policy before trading:

- **Progressive finality:** defined checkpoints become final for the contract during the event. Later external corrections do not reverse those commitments.
- **End finality:** observations remain provisional until the declared closing procedure. Funding continues to include histories that corrections could restore.

The standard progressive cancellation policy is: **a cover finalized before cancellation keeps its finalized payout; an unresolved cover pays its previously specified cancellation amount.** The exact order and authority of finalization and cancellation are part of the rules. Being economically certain under normal outcomes is not enough if a remaining cancellation outcome pays less.

Other cancellation policies are possible only when their payouts are fully modeled and funded. “VOID” is a published outcome policy, not permission to reverse history or recover money already withdrawn.

The product displays which amounts are final, which remain conditional and why money can or cannot be withdrawn.

## 9. Changing and exiting protection

Users can request:

- A change to selected covers.
- A replacement basket.
- A proportional sale of the complete funded position.
- A full sale of the complete funded position.
- Withdrawal of guaranteed funds without selling exposure.

These actions are distinct. Closing a selected component can remove an offset and require additional money.

A proportional complete-position sale includes the account's cash component and all its payout entitlements, including exceptional outcomes. When exactly representable, the retained fraction remains funded; net nonnegative sale proceeds need not require an additional seller deposit. Simply reducing every cover holding while leaving cash unchanged has no such guarantee.

The interface states precisely which operation a reduction button requests. Unsupported fractional quantities are rejected or replaced by an explicitly reviewed executable fraction. The buyer must also be funded, and no acceptable sale price is guaranteed.

## 10. The compiler and the generic engine

The architecture separates responsibilities:

| Component | Responsibility |
|---|---|
| Observation adapter | Map source reports to the market's declared, auditable facts |
| Market schema | Define sufficient state, allowed transitions, finality and exceptional outcomes |
| Cover language | Define immutable bounded payouts using supported expressions |
| Verifier | Compute exact funding over the complete permitted account exposure |
| Quote and execution service | Obtain executable offers and coordinate authorized packages |
| Intention compiler | Translate a user's request into supported covers and expose any mismatch |
| Account interface | Explain the whole position and its cash movements |

A verifier must handle all covers in an account together. Individually supported covers cannot be combined if their joint dependencies exceed the verifier's supported class or limits.

New capabilities are versioned. Existing markets and covers keep their meaning. Adding a cover does not permit silently changing the observation history, introducing new settlement states, or weakening collateral checks.

Exact settlement uses token base units and a declared lot system. Where a requested expression must be discretized, the executable payout is shown before acceptance. The engine never relies on display rounding to remain solvent.

## 11. The broader product

The same foundation can serve several experiences:

- **Trade:** take views and manage related event positions.
- **Protect:** map an external exposure to available bounded payouts, making basis risk explicit.
- **Build:** let developers define supported markets, list cover and create focused interfaces on common accounting.

Scheduled purchases and renewal instructions can request future quotes within user limits. Future coverage exists only when a funded trade executes. A renewal instruction is not itself an unconditional promise of future protection.

The vision spans numeric, categorical and evolving processes. It does not require every experience to launch together, or every requested cover to fit the same verification method.

## 12. What the product must demonstrate

Before claiming these capabilities, demonstrate:

- One cover definition can be traded by many users without bespoke accounting.
- Requests become exact baskets or clearly explained approximations/refusals.
- Combined payouts include history-dependent and exceptional outcomes correctly.
- Every accepted trade, withdrawal, fact and settlement preserves funding and conservation.
- Atomic changes avoid unintended intermediate exposure.
- Corrections cannot reintroduce unfunded obligations.
- Resolved payouts and residual positions reconcile without double counting.
- Partial and whole-position exits behave as described.
- Maker quotes remain usable under competing fills and event updates.
- Verification cost stays within declared limits.
- Users understand their remaining exposure, including what their cover does not protect.

Mechanism demonstrations do not establish customer demand, favorable prices or maker profitability. Those must be measured with actual users and executable offers.

**The intended result: makers trade reusable covers; people hold understandable protection; developers share one accounting foundation; every accepted promise remains funded.**
