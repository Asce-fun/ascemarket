# AsceMarket

## A market for covers on future states

**Whitepaper**

[Download the whitepaper (PDF)](ascemarket-whitepaper.pdf)

[Read or download the hosted whitepaper](https://asce-fun.github.io/ascemarket/)

author: Saurabh yadav

### Abstract

AsceMarket is a marketplace for standardized financial covers on future states of an event. Customers select listed covers and trade quantities to build or adjust their protection. Each cover has a fixed, bounded payment rule; combined positions determine the portfolio's payout. Creating and listing covers is a separate activity.

Binary, range, categorical and variable-payment covers share a common payout language. Each rule is tied to a defined observation and scaled by coverage quantity. Compatible positions combine within an account, whose collateral covers its greatest net obligation across permitted outcomes, accounting for eligible payment rights.

A selected cover can be bought directly or replaced by an explicitly accepted combination with equivalent payments. Offers identify positions, price, available quantities and funding requirements. Payment equivalence alone does not establish an executable trade.

This paper defines the payout language, account funding and trading lifecycle. Worked examples connect customer exposure to cover payments and show how premiums, combined obligations and execution order affect capital. The product's value is assessed through useful protection at executable terms and sustainable supply.

---

## 1. A market for financial protection

A participant may need protection below a price, within a range, or in an amount that increases as conditions worsen. AsceMarket makes standardized covers the unit of trade: customers select listed instruments and quantities, then combine their payments to build protection.

### 1.1 A customer purchase: protecting an ETH holding

Consider a participant holding 10 ETH, worth $30,000 at a reference price of $3,000 per ETH. They want protection against a lower price at a specified future observation.

They select a listed capped downside cover. Its payment fraction is zero at or above $3,000, rises linearly to one as ETH falls to $2,000, and stays one below $2,000. These thresholds are fixed in the listing.

Buying $10,000 of coverage gives this payment:

$$
C(x)=10\min\left(1{,}000,\max(3{,}000-x,0)\right).
$$

The illustrative premium is $1,500, with zero fees. The holding's downside shortfall is independently determined by its quantity and reference price:

$$
L(x)=10\max(3{,}000-x,0).
$$

The remaining downside cost is the shortfall minus the cover payment, plus the premium.

| ETH price at the observation | Holding's downside shortfall | Cover payment | Uncovered shortfall | Remaining downside cost, including premium |
|---|---:|---:|---:|---:|
| $3,000 | 0 | 0 | 0 | 1,500 |
| $2,750 | 2,500 | 2,500 | 0 | 1,500 |
| $2,500 | 5,000 | 5,000 | 0 | 1,500 |
| $2,000 | 10,000 | 10,000 | 0 | 1,500 |
| $1,500 | 15,000 | 10,000 | 5,000 | 6,500 |
| $1,000 | 20,000 | 10,000 | 10,000 | 11,500 |

~~~mermaid
flowchart LR
    E["10 ETH at an observed price of 1,500"] --> L["Downside shortfall: 15,000"]
    C["Cover payment: 10,000"] --> R["Uncovered shortfall: 5,000"]
    L --> R
    R --> T["Including premium: 6,500"]
    P["Premium paid: 1,500"] --> T
~~~

*Figure 1. A listed cover offsets a defined holding's shortfall. Its payment cap and purchase cost remain visible.*

Between $2,000 and $3,000, this position offsets the modeled shortfall. Below $2,000, its cap leaves some loss uncovered. At or above $3,000, it pays zero and the premium remains a cost. More or less coverage changes payment size without changing the listed thresholds.

The example assumes the participant still holds 10 ETH and values it at the cover's observation. It measures downside cost, rather than total investment profit or loss. The specified noncompletion outcome pays zero with no premium refund.

The ETH holding is external to the cover account. Underwriting this cover alone requires $10,000 of backing: the received $1,500 premium can contribute, leaving $8,500 of maker funding.

### 1.2 From selection to a funded trade

The product has three connected functions:

1. **Build protection from listed covers.** Select covers with defined observations and payment rules, then choose quantities.
2. **Find executable offers.** Identify counterparties able to trade those positions at agreed prices and sizes.
3. **Fund the resulting account.** Combine compatible rights and obligations, then retain the required backing as the trade executes.

Makers supply buy and sell quotes under the same funding rules as other participants. Premiums and resale prices are market quantities, distinct from the cover's contractual payment.

## 2. Events, observations, covers and positions

### 2.1 The event provides context

An event is the underlying subject of a market. It may be an ongoing process, such as ETH's price, or a finite occurrence, such as a particular football match.

An ongoing event does not need one final settlement time. Covers under that event have their own observation times or finite windows. An ETH price event can therefore contain covers referring to different future dates.

### 2.2 The observation fixes the relevant fact

An observation specifies the measurement on which a cover depends, including its time or window, units, permitted results and settlement rules.

“ETH below $2,000” is incomplete. “ETH/USD below $2,000 at the specified December 31 observation” identifies a particular future measurement to which a payment can be attached.

Two covers can reference the same observation while having different payout shapes. Two covers with the same shape can reference different observations and therefore represent different instruments.

### 2.3 The cover defines payment

A cover binds an observation to an immutable payment rule, described by its payout shape. Its event, measurement, thresholds or categories, boundary values, settlement currency and exceptional payment rules determine its identity.

Creating and listing establishes these terms before trading. Everyone trading the same cover uses the same terms; owner, quantity and premium do not redefine it. Changing a payment rule or observation creates a different cover.

Payment depends on the defined observation, not on the holder proving an individual loss. Customers select covers that suit their exposure; any difference between the cover payment and their actual loss remains their residual exposure.

### 2.4 The position determines size and direction

A position is a participant's amount of a cover:

- A positive position is a right to receive its payment.
- A negative position is an obligation to make its payment.
- A zero position has no remaining exposure to that cover.

Buying increases the signed quantity; selling decreases it. Reselling a positive holding reduces an existing right. Selling beyond that holding creates an underwriting obligation. Buying back a negative position reduces that obligation.

| Object | What it specifies | Example |
|---|---|---|
| Event | Underlying context | ETH/USD |
| Observation | The particular future measurement | ETH/USD at a specified December 31 time |
| Cover | Payment rule for that observation | Full payment below $2,000 |
| Position | Coverage amount and direction | +$10,000 held or −$10,000 underwritten |
| Premium | Agreed consideration for a trade | $1,500 paid for the position |

~~~mermaid
flowchart TD
    E["Event: ETH/USD"] --> O1["December 31 observation"]
    E --> O2["January 31 observation"]
    O1 --> C1["Binary cover"]
    O1 --> C2["Range cover"]
    O1 --> C3["Variable-payment cover"]
    O2 --> C4["A separate dated cover"]
    C1 --> P["Compatible positions in an account"]
    C2 --> P
    C3 --> P
    P --> R["Combined obligation and required backing"]
~~~

*Figure 2. An event can contain several observations. Compatible positions within an account can contribute to the same collateral calculation.*

## 3. One payout language for standardized covers

The payout language describes listed covers and allows their payments to be evaluated together.

### 3.1 Payment as a fraction of coverage

For a numerical observation with result $x$, a cover defines a normalized payout fraction $h(x)$:

$$
0 \leq h(x) \leq 1.
$$

For coverage amount $Q$, its payment is:

$$
\operatorname{payment}(x)=Qh(x).
$$

A fraction of zero pays nothing. A fraction of one pays the full coverage. Intermediate fractions produce proportional payments.

Coverage quantity scales the shape. It does not move its thresholds or change its boundary rules.

### 3.2 Segments, jumps and exact boundary values

The common representation describes a shape using ordered points. Each point specifies:

- Its observation value.
- The payout fraction immediately below it.
- The payout fraction exactly at it.
- The payout fraction immediately above it.

Between consecutive points, the fraction follows a straight line. Outside the outer points, it remains constant. A constant cover can be described without turning points.

This representation expresses flat regions, gradual changes and abrupt jumps in one language. It also preserves distinctions such as “below,” “at or below” and “exactly equal.”

| Shape | Payment behavior | Representation |
|---|---|---|
| Binary or digital | Full payment when a specified condition holds | A threshold jump or payments assigned to declared results |
| Range | Full payment within a specified interval | Two jumps with a flat region between them |
| Scalar or ramp | Payment changes proportionally with the result | A straight segment with bounded tails |
| Capped call or put | Payment grows as the observed price rises or falls, up to a cap | Flat, sloping and capped regions |
| Tent or trapezoid | Payment is concentrated around a region | Rising and falling segments |
| Staircase | Payment changes in stages | Several flat regions separated by jumps |
| Categorical | Payment is specified for each declared result | Fractions attached to valid category codes |

For categorical observations, only the declared categories are meaningful. A numerical label for a category does not introduce intermediate settlement outcomes.

### 3.3 Three shapes on the same observation

Consider a BTC/USD observation with thresholds at $80,000 and $100,000:

- **Binary:** full payment when BTC is at least $100,000.
- **Range:** full payment when BTC is at least $80,000 and below $100,000.
- **Scalar:** full payment at or below $80,000, declining linearly to zero at $100,000.

~~~text
Normalized payout fraction

Binary: full payment at and above 100k
1 |                  ●────────
  |                  │
0 |──────────────────○
  +------------------|--------> BTC
                   100k

Range: full payment from 80k up to, excluding, 100k
1 |         ●────────○
  |         │        │
0 |─────────○        ●─────────
  +---------|--------|--------> BTC
           80k      100k

Scalar: full payment through 80k, falling to zero at 100k
1 |─────────●
  |          \
  |           \
0 |            ●──────────────
  +---------|--|--------------> BTC
           80k 100k

● included point     ○ excluded point
~~~

*Figure 3. Schematic payout shapes. The definitions below specify their exact values; drawings do not replace boundary rules.*

The corresponding fractions are:

$$
h_A(x)=
\begin{cases}
0 & x<100{,}000,\\
1 & x\geq100{,}000,
\end{cases}
$$

$$
h_B(x)=
\begin{cases}
1 & 80{,}000\leq x<100{,}000,\\
0 & \text{otherwise},
\end{cases}
$$

$$
h_C(x)=
\begin{cases}
1 & x\leq80{,}000,\\
\dfrac{100{,}000-x}{20{,}000} & 80{,}000<x<100{,}000,\\
0 & x\geq100{,}000.
\end{cases}
$$

At $80,000, both the range and scalar covers pay their full amounts. At $100,000, the binary pays in full and the other two pay zero. Those exact boundary values matter to both settlement and collateral.

### 3.4 The shape stays tied to its observation

A payout curve answers how much a cover pays for a result. Its observation definition supplies the meaning of that result.

Where a cover depends on a sequence of observations, its payment must be defined over that sequence. A closing value cannot establish a past threshold touch by itself. The information needed to distinguish paying and nonpaying scenarios is part of the cover's observation dependencies.

The same account funding principle applies to the resulting permitted scenarios.

### 3.5 Combine listed covers and compare executable offers

Listed covers can be traded together as a package. A combination can reproduce the payment of another listed cover, allowing a customer to compare a direct offer with offers for the component positions.

For example, let $H_K(x)$ pay one when $x\geq K$ and zero otherwise. A position paying $100 within the range $[80{,}000,100{,}000)$ can be constructed as:

$$
100H_{80{,}000}(x)-100H_{100{,}000}(x).
$$

Starting from no positions, the participant buys $100 of the listed lower-threshold cover and underwrites $100 of the listed upper-threshold cover. The combined payment is zero below $80,000, $100 within the range, and zero at or above $100,000. The two legs must reference the same observation, units, boundary conventions and exceptional payment rules.

The customer holds two positions matching $100 of range coverage, rather than a new separately owned claim. Both enter the account's funding calculation. The actual positions are disclosed and authorized:

| Offer | What the participant receives |
|---|---|
| Direct cover | A position in the selected listed cover |
| Exact combination | Positions in other listed covers whose combined payment equals that of the selected cover and quantity in every permitted scenario |
| Unavailable | No executable offer meets the selected quantities and accepted terms |

A combination with a different payment requires a separate selection. Its shortfall or excess relative to the original selection is shown by scenario.

Consider these illustrative offers for $100 of range coverage:

| Route | Trade consideration | Fees | Total purchase cost | Available coverage |
|---|---|---:|---:|---:|
| Direct range cover | Pay 27 | 1 | 28 | 100 |
| Exact threshold combination | Pay 62 for the lower threshold; receive 38 for selling the upper threshold | 2 | 26 | 100 |

The exact combination costs $2 less in this example. Its available coverage is limited by the smaller eligible leg: if the lower-threshold seller offers 120 units and the upper-threshold buyer offers 100, the package can supply 100.

Every affected account must remain funded. An unavailable leg, mismatched observation or failed funding check makes the package unavailable. These prices illustrate offer comparison; they are not estimates of fair value.

## 4. The account combines rights, obligations and cash

### 4.1 Combined exposure

For account $a$, let $q_{a,j}$ be its signed coverage in cover $j$. Let $\omega$ be a permitted settlement scenario, and let $h_j(\omega)$ be that cover's payout fraction.

The account's net future payment is:

$$
P_a(\omega)=\sum_j q_{a,j}h_j(\omega).
$$

Positive terms are receipts; negative terms are payments owed. Combining positions means summing their contractual cashflows under the same scenario.

Let $c_a$ be the account's cash accounting component. Its settlement entitlement is:

$$
W_a(\omega)=c_a+P_a(\omega).
$$

An account is funded when:

$$
W_a(\omega)\geq0
\qquad\text{for every permitted }\omega.
$$

A held cover can offset another obligation only where its payment is enforceable in the same compatible settlement account. A quoted sale value or an expected future trade does not establish that right.

### 4.2 Cash history

The account's cash component records actual monetary movements:

$$
\begin{aligned}
c_a={}&
\text{deposits}
-\text{withdrawals}\\
&+\text{premiums received}
-\text{premiums paid}\\
&-\text{fees paid}
+\text{fees received}\\
&+\text{net settlement payments already credited}.
\end{aligned}
$$

When a settlement payment becomes cash, its future exposure is removed. The same amount cannot appear as both a remaining cover payment and an already credited balance.

Profit reporting uses the history of deposits, premiums, sale proceeds, fees and settlement. It does not create an additional spendable balance.

## 5. Collateral follows the maximum obligation

### 5.1 The reserve

For an account holding nonnegative cash reserves, define:

$$
R_a=
\max\left(0,\sup_{\omega}\left[-P_a(\omega)\right]\right).
$$

It must retain at least $R_a$ in cash. The reserve is the largest net payment the account could owe, including the settlement scenarios specified by the product.

For an account holding only underwriting obligations, with combined nonnegative liability $L_a(\omega)$:

$$
P_a(\omega)=-L_a(\omega),
\qquad
R_a=\sup_{\omega}L_a(\omega).
$$

The calculation uses the whole portfolio.

### 5.2 How collateral is shared

For nonnegative liabilities $L_j$:

$$
\sup_{\omega}\sum_jL_j(\omega)
\leq
\sum_j\sup_{\omega}L_j(\omega).
$$

The right side funds each maximum separately; the left side funds the greatest combined payment. A smaller combined maximum allows collateral reuse while covering all payments that can occur together.

Coinciding maxima still add: downside obligations paying $10,000 and $5,000 in the same low-price state require $15,000. Probabilities and forecasts do not reduce backing for a payment that remains possible.

### 5.3 Compatibility determines the collateral group

Positions share a reserve within the same account when they use the same settlement measurement, settlement currency and compatible payment rules. Different participants' portfolios do not automatically share collateral.

| Relationship | Treatment |
|---|---|
| Different shapes on the same observation | Evaluate their combined payment |
| Different quantities of the same cover | Net signed quantities |
| Different observation dates under the same event | Maintain separate timing-group reserves |
| Different measurements or unrelated events | Maintain separate backing |
| A guarantee removed or a hedge sold | Recalculate the remaining account |

Sharing the label “ETH” does not establish an offset between December and January payments.

With separately reserved groups $g$:

$$
R_a^{\mathrm{total}}=\sum_gR_{a,g}.
$$

A later expected receipt cannot fund an earlier compulsory payment. Any recognized timing relationship must preserve funding at each payment date.

### 5.4 Funds available to withdraw

For a funded settlement account, the guaranteed entitlement is:

$$
G_a=\inf_{\omega}W_a(\omega).
$$

A withdrawal of $d$ is permitted only when:

$$
0\leq d\leq G_a.
$$

For an account holding only underwriting obligations, this reduces to:

$$
G_a=c_a-R_a.
$$

Premiums enter the cash history in Section 4.2; the withdrawal rule applies to that resulting account.

Ordinary market-price changes do not release backing for still-permitted outcomes. Contractually final information can change the remaining scenarios and therefore the amount guaranteed to the account.

## 6. Worked example: three listed covers, one funded portfolio

All amounts in this example are illustrative USDC amounts. Premiums are agreed example prices, with zero fees. The numerical examples use a predefined zero-payment outcome for noncompletion; under that rule, premiums are not refunded.

At one BTC observation, a maker underwrites these three listed covers:

| Cover | Shape | Coverage | Example premium |
|---|---|---:|---:|
| A | Binary: BTC at least $100,000 | 10,000 | 3,000 |
| B | Range: $80,000 to below $100,000 | 10,000 | 2,000 |
| C | Scalar: full at $80,000, declining to zero at $100,000 | 5,000 | 1,000 |

The payments are:

| BTC result | A | B | C | Combined obligation |
|---|---:|---:|---:|---:|
| $70,000 | 0 | 0 | 5,000 | 5,000 |
| $80,000 | 0 | 10,000 | 5,000 | **15,000** |
| $90,000 | 0 | 10,000 | 2,500 | 12,500 |
| $100,000 | 10,000 | 0 | 0 | 10,000 |
| $120,000 | 10,000 | 0 | 0 | 10,000 |
| Noncompletion | 0 | 0 | 0 | 0 |

The individual maxima sum to:

$$
10{,}000+10{,}000+5{,}000=25{,}000.
$$

The portfolio's maximum obligation is:

$$
R=15{,}000.
$$

Its backing is therefore $10,000 lower, a **40% reduction compared with funding those three caps separately**.

~~~mermaid
xychart-beta
    title "Backing for the same promised payments"
    x-axis ["Separate caps", "Combined obligation"]
    y-axis "USDC" 0 --> 25000
    bar [25000, 15000]
~~~

*Figure 4. Both bars refer to the same three payment promises. The comparison is with separate cap funding.*

The table lists representative prices. The maximum is established over the full domain: the obligation is $5,000 below $80,000, declines from $15,000 to $10,000 across the range, and is $10,000 at and above $100,000.

### 6.1 Total backing and maker contribution

Buyers pay $6,000 in total premiums. In a funded package starting from empty accounts, the maker contributes $9,000:

$$
9{,}000+6{,}000=15{,}000.
$$

~~~mermaid
flowchart LR
    M["Maker contribution: 9,000 USDC"] --> B["Total backing: 15,000 USDC"]
    C["Buyer premiums: 6,000 USDC"] --> B
    B --> P["Maximum combined payment: 15,000 USDC"]
~~~

*Figure 5. Premiums help fund the obligation. They do not reduce any buyer's contractual payment.*

The maker's cash after receiving premiums is $15,000. Its reserve is also $15,000, so it has no free withdrawal at that point.

At settlement, the maker receives the backing remaining after the cover payments. Its economic profit or loss equals premiums received minus cover payments:

| BTC result | Buyer payments | Maker's remaining entitlement | Maker profit or loss |
|---|---:|---:|---:|
| $70,000 | 5,000 | 10,000 | +1,000 |
| $80,000 | 15,000 | 0 | −9,000 |
| $90,000 | 12,500 | 2,500 | −6,500 |
| $100,000 | 10,000 | 5,000 | −4,000 |
| $120,000 | 10,000 | 5,000 | −4,000 |
| Noncompletion | 0 | 15,000 | +6,000 |

A smaller reserve is a funding benefit. It does not determine whether the premiums compensate the maker for the exposure.

## 7. Trading and changing protection

### 7.1 Executable liquidity

Executable liquidity is the coverage counterparties can actually trade at a stated price. It requires an active offer, sufficient available size and funded resulting accounts.

An offer specifies its cover or component positions, side, premium, fees, available quantity, expiry and conditions of execution. Composite offers require all their legs to be available together.

Available capacity cannot be promised independently to several customers as though each promise had separate backing. A firm commitment requires explicitly reserved capacity and funding. An unreserved quote can become unavailable after another fill, cancellation, expiry or account change; it is checked again at execution.

Three checks distinguish a usable trade:

| Check | Question |
|---|---|
| Position matching | Does the offer specify the selected covers and quantities, or an explicitly accepted alternative combination? |
| Execution | Are all counterparties and required quantities available at the quoted total cost? |
| Funding | Do all resulting accounts satisfy their combined obligations? |

Passing one check does not establish the others. A defined cover can have no quote, and a price-compatible package can fail its funding check.

### 7.2 Review the complete trade

A trade specifies the cover, signed position change, premium, fees and any authorized funding movement.

Before accepting it, a participant can review:

- The covers, their payment rules and quantities bought or sold.
- Any alternative component positions and differences in payment.
- Available size, quote expiry and execution conditions.
- Premiums, fees, deposits and total cash movement.
- Resulting portfolio payments and withdrawable funds.

The preview compares existing and resulting portfolio payments. Participants can optionally supply an external exposure to see its remaining shortfall; doing so is not required to trade.

### 7.3 Execute the funded change together

Execution applies equal and opposite position changes for each traded cover, transfers the agreed consideration, and checks every affected account. A single trade may involve two accounts; a package may involve several counterparties.

~~~mermaid
flowchart TD
    A["Select listed covers and quantities"] --> B["Find direct or combined offers"]
    B --> Q["Check available size and total price"]
    Q --> V["Review the resulting protection"]
    V --> C["Authorize coverage, cash and fees"]
    C --> D["Evaluate every affected account"]
    D --> E{"All affected accounts remain funded?"}
    E -->|Yes| F["Commit payments and positions together"]
    E -->|No| G["Leave the accounts unchanged"]
    F --> H["Hold, adjust positions or settle"]
~~~

*Figure 6. Execution requires an available offer and funded resulting accounts.*

A package of changes can use its final combined offsets when the entire package executes together. Separately executed trades must each pass their own funding check.

### 7.4 Sell, close or adjust positions

A holder can resell some or all of a positive position at an agreed price. An underwriter can buy back some or all of a negative position. A full close leaves zero quantity in that cover.

Customers can also combine sales and purchases to change protection, such as selling a held binary cover and buying a listed capped downside cover. Cover terms remain fixed; the holdings change.

Sale proceeds and released collateral are different amounts. The account is recalculated after both the payment and position change.

Returning to the three-cover example, suppose the maker buys back half of C for $1,000:

| Item | Before | After the buyback |
|---|---:|---:|
| Maximum C payment | 5,000 | 2,500 |
| Maximum combined obligation | 15,000 | 12,500 |
| Maker cash | 15,000 | 14,000 |
| Maker's withdrawable funds | 0 | 1,500 |

At $80,000, B still pays $10,000 and the remaining C pays $2,500. That is the new maximum.

The reserve falls by $2,500, but the maker pays $1,000 for the close. It can therefore withdraw $1,500 while preserving the remaining backing.

A close requires an executable counterparty price. Reducing gross coverage does not necessarily lower the portfolio maximum; another scenario can remain the binding obligation.

### 7.5 Assess useful protection and sustainable supply

Product value is assessed at the coverage amount and timing a participant needs:

| Measure | What it establishes |
|---|---|
| Coverage fit | The loss offset by the payment and the residual exposure |
| Total customer cost | Premium, fees and the cost of opening or changing protection |
| Executable size and fills | How much of the selected cover quantities can actually be traded |
| Exit and adjustment capacity | Whether a participant can change positions at acceptable terms |
| Maker economics | Premiums less payments, hedging, operating and capital costs |
| Funding efficiency | Total backing and peak personal contribution through the actual trade sequence |

The comparison is with the best usable alternative for that participant. A cover or combination has value when the protection it provides justifies its total cost. Makers must earn enough to continue supplying quotes.

## 8. Timing, available capital and final payments

### 8.1 Peak funding depends on execution order

Funding comparisons must hold cover payments, premiums, exceptional outcomes and execution order constant. The 40% reduction in Section 6 compares combined backing with separate caps; it is not a measured advantage over every alternative construction.

Consider two mutually exclusive $100 covers on one observation. Buyers pay premiums of $30 and $40. Neither cover pays on the declared neither or noncompletion outcomes, and fees are zero. Their combined maximum payment is $100.

| Funding construction | Total backing after both sales | Peak maker contribution | Final net maker contribution |
|---|---:|---:|---:|
| Separate CTF conditions, prefunded inventory | 200 | 200 | 130 |
| Common-condition CTF, prefunded inventory | 100 | 100 | 30 |
| Common-condition CTF, sequential buyer-funded issuance | 100 | 70 | 30 |
| Account-based clearing, sequential funded trades | 100 | 70 | 30 |
| Common-condition CTF, simultaneous buyer-funded issuance | 100 | 30 | 30 |
| Account-based clearing, one funded package | 100 | 30 | 30 |

These figures were reproduced in a controlled comparison using synthetic premiums and fixed outcomes. The account-based routes and common-condition CTF routes require the same backing and maker contributions under matched execution. They establish funding behavior, rather than live quote quality or maker profitability. [Comparison record](research/cover-marketplace-test-findings.md#ctf-collateral-and-maker-usefulness)

In the sequential route, the first buyer contributes $30 and the maker contributes $70. After the second sale, cash is $140 against a $100 obligation; withdrawing $40 leaves a $30 net maker contribution. Executing both sales together collects $70 in premiums at entry, so the maker contributes only $30.

The reduction follows compatible claims and funding timing. CTF also supports collateral-backed splits and merges of compatible positions; this result does not establish a unique AsceMarket collateral advantage. [Conditional Tokens developer guide](https://conditional-tokens.readthedocs.io/en/latest/developer-guide.html#splitting-and-merging-positions)

Commercial comparison additionally requires actual premiums, fees, available size, exit terms and maker costs. Future premiums do not fund an independently executed checkpoint.

### 8.2 Final payment

When the relevant outcome becomes final, each account's entitlement is evaluated under that outcome.

For a compatible group with final result $\omega^*$:

$$
\operatorname{entitlement}_a=W_a(\omega^*).
$$

Its net cover payment is credited into cash once and the settled positions are removed. Finalized covers are closed to further trading.

Other timing groups retain their own positions and reserves. Participants can withdraw eligible funds without reducing the backing of those remaining obligations.

## 9. Product accounting guarantees

### 9.1 Every account remains funded

Every operation preserves the account funding rule in Section 4.1. Each affected account is checked individually; one account's surplus does not excuse another's deficit. A quoted-price change alone does not require additional collateral for unchanged bounded positions.

Cash, guaranteed withdrawable funds, contingent payments and quoted exit value are distinct account quantities. Appendix D gives the accounting argument for retaining backing through authorized operations.

### 9.2 Backing and entitlements reconcile

With exact cashflows and cash-only backing:

$$
\sum_aW_a(\omega)=B,
$$

where $B$ is the settlement currency held for those accounts.

Trades apply equal and opposite quantity changes for the same cover and transfer consideration between accounts. A resale can transfer an existing payment right; underwriting can create an offsetting right and obligation. Deposits increase backing and entitlement equally; withdrawals decrease both equally.

Where defined currency rounding leaves a surplus $S(\omega)$, reconciliation becomes:

$$
\sum_aW_a(\omega)+S(\omega)=B,
\qquad S(\omega)\geq0.
$$

The surplus is not credited twice or treated as another participant's free cash.

### 9.3 Rights and payment records remain consistent

Held covers retain the terms defined in Section 2.3. A right supporting an obligation cannot be removed without checking the resulting account.

Settlement credits cash and removes the corresponding future exposure exactly once. Paid entitlements cannot be claimed again.

These conditions connect the customer's payment right to the maker's retained backing throughout the position's lifecycle.

## Appendix A. Mathematical definition of the payout language

A piecewise-affine shape with explicit boundary values can be expressed as:

$$
h(x)=a+bx
+\sum_jc_j\max(x-k_j,0)
+\sum_jd_j\mathbf{1}_{x\geq k_j}
+\sum_je_j\mathbf{1}_{x>k_j}.
$$

The hinge terms change slopes. The indicators specify jumps and distinguish the exact threshold from either side. The cover's payout fraction is bounded between zero and one on its declared input domain.

The ordered-point representation provides the same payment semantics through the values immediately below, exactly at and immediately above each point.

For threshold $K$, define:

$$
H_K(x)=\mathbf{1}_{x\geq K}.
$$

Then the range $[L,U)$ is:

$$
h_{\mathrm{range}}(x)=H_L(x)-H_U(x).
$$

A capped increasing ramp is:

$$
h_{\mathrm{ramp}}(x)
=
\frac{\max(x-L,0)-\max(x-U,0)}{U-L},
\qquad U>L.
$$

Multiplying a fraction by coverage gives the corresponding payment.

## Appendix B. Calculating the portfolio obligation

For covers on the same compatible numerical observation, combine their signed positions:

$$
P_a(x)=\sum_jq_{a,j}h_j(x).
$$

Between the union of their turning points, the ideal combined payment is affine. Its extrema occur at the domain endpoints, exact turning-point values or their one-sided limits.

The calculation therefore examines the full union of points and the relevant tails. Exact values at jumps are included separately. For categorical observations, only valid categories are settlement candidates.

Currency amounts are integers in the settlement currency's smallest unit. Each position's exact rational payment $r_j=q_{a,j}h_j(x)$ is rounded once using $\lfloor r_j\rfloor$: receipts round down, and negative obligations round away from zero in magnitude.

For $m\geq1$ nonzero positions, the rounded portfolio payment $\widehat P_a$ satisfies:

$$
\left\lfloor P_a(x)\right\rfloor-(m-1)
\leq \widehat P_a(x)
=\sum_j\left\lfloor r_j(x)\right\rfloor
\leq\left\lfloor P_a(x)\right\rfloor.
$$

The bound follows because each position contributes less than one unit of fractional rounding loss. Let $p_{\min}=\inf_xP_a(x)$, including exceptional outcomes. Then:

$$
c_a+\widehat P_a(x)
\geq c_a+\left\lfloor p_{\min}\right\rfloor-(m-1).
$$

For nonnegative cash reserves, retaining $\max(0,-\lfloor p_{\min}\rfloor+m-1)$ is therefore sufficient. The allowance is at most $m-1$ currency base units; an empty portfolio needs none. This is a conservative bound, rather than a claim to the exact rounded minimum. Arithmetic must preserve the stated rational payment before its final rounding.

## Appendix C. Funding an authorized change

For one compatible account, let:

- $c_a$ be the existing cash component.
- $t_a$ be the net cash transfer from the trade, including applicable fees.
- $\Delta P_a(\omega)$ be the signed change in future payment.
- $d_a$ be an authorized deposit.
- $x_a$ be an authorized withdrawal.

The resulting entitlement is:

$$
W'_a(\omega)
=
c_a+t_a+d_a-x_a+P_a(\omega)+\Delta P_a(\omega).
$$

The change is acceptable when:

$$
\inf_{\omega}W'_a(\omega)\geq0.
$$

Before deposits or withdrawals, the minimum additional funding is:

$$
d_a^{\min}
=
\max\left(
0,
-\inf_{\omega}
\left[c_a+t_a+P_a(\omega)+\Delta P_a(\omega)\right]
\right).
$$

For integer payments, use the conservative entitlement bound in Appendix B.

For an underwriter starting from an empty account, with received premiums $\pi$ and paid fees $F$:

$$
D_{\min}=\max(0,R-\pi+F).
$$

This quantity is the underwriter's own contribution. The obligation remains backed by the full reserve.

The general account rule concerns entitlement, rather than the sign of its cash component in isolation. If a position has a guaranteed future receipt, withdrawing that guaranteed floor can leave a negative cash component while every final entitlement remains nonnegative. That component records accounting history; it is not a negative physical balance of settlement currency.

## Appendix D. Why authorized operations preserve backing

Consider one compatible settlement group with fixed payment rules and cash-only backing. Start from empty accounts and zero backing. Include premium and fee recipients in the accounting. Assume every operation uses the declared payment and rounding conventions and checks each affected account's resulting entitlement.

**Trades.** For each traded cover, quantity changes sum to zero across accounts. Premium and fee transfers also sum to zero. With exact cashflows:

$$
\sum_a\Delta W_a(\omega)
=\sum_a\Delta c_a
+\sum_jh_j(\omega)\sum_a\Delta q_{a,j}
=0.
$$

Trading therefore preserves total entitlement and backing. The funding check admits the change only when every resulting account is nonnegative in every permitted scenario.

**Deposits and withdrawals.** A deposit increases one account's cash and held backing equally. A withdrawal decreases both equally. Since $d\leq\inf_\omega W_a(\omega)$, the remaining entitlement $W_a(\omega)-d$ stays nonnegative in every scenario. The same check applies when a held right is sold or transferred.

**Settlement.** Once a payment $p$ is final, it is constant over the remaining permitted scenarios. Crediting $p$ to cash and removing it from future exposure gives:

$$
(c_a+p)+(P_a-p)=c_a+P_a.
$$

Materializing a payment therefore preserves entitlement without moving custody. Removing the exposure at that same step prevents a second credit. A later withdrawal follows the withdrawal rule.

By induction, these operations preserve nonnegative accounts and $\sum_aW_a=B$ under exact cashflows.

Before settlement, rounding each signed payment down makes total integer entitlement no greater than the exact total. The excess backing remains as nonnegative surplus $S$. Converting a final integer payment into cash preserves that account's integer entitlement, so the surplus is retained. Together with the funding bound in Appendix B, this preserves nonnegative integer accounts and $\sum_aW_a+S=B$.

For different payment dates, the separate group reserves in Section 5.3 remain in force. This argument grants no additional offset against a payment due later.
