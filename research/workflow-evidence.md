# Quote workflow: evidence and alternatives

Research date: **17 September 2026**. Companion specification: [quote-workflow.md](../quote-workflow.md).

## What was actually investigated

Reviewed primary product/API documentation, inspected DIVA's Solidity implementation, and downloaded Deribit's public instrument catalogue. No authenticated accounts were used, no orders were placed, and no makers or users were contacted. Consequently, workflow steps below are documented or inferred; completion times, live execution prices, acceptance rates and user preference remain unmeasured.

The comparison covers listed option packages, configurable derivative pools, and conditional outcome claims. These are close mechanical substitutes for the three proposed tasks. It is not an exhaustive survey of financial infrastructure.

## Existing mechanisms

### Deribit: package execution is already a product

Combo books execute supported strategies at one package price, with simultaneous legs. Existing legs remain independently tradable. The available strategies include put spreads. This directly challenges a claim that opening a capped payout in one action requires AsceMarket. [Combo Books](https://support.deribit.com/hc/en-us/articles/31424954956061-Combo-Books).

Block RFQ accepts structures of up to 20 legs with configurable ratios. It supports package quotes and taker limit execution; block-size eligibility matters. This supplies a credible route for eligible multi-leg edits, rather than forcing the comparison to separate market orders. It does not mean a one-ETH six-leg example is automatically eligible. [Block RFQ](https://support.deribit.com/hc/en-us/articles/25951371614621-Deribit-Block-RFQ).

Linear options use USDC and a specified expiry index observation. The current settlement process passes through an immediately settling future. Thus a put spread is a valid normal-outcome payoff comparison; inverse coin options should not be substituted without adjusting the payout units. Account margin, delivery fees and exceptional treatment also need separate comparison. [Linear USDC Options](https://support.deribit.com/hc/en-us/articles/31424932728093-Linear-USDC-Options).

**Catalogue observation:** the public response contained 580 ETH_USDC option instruments. For 25 September 2026, it included puts at 2,650, 2,700, 2,800, 2,850, 2,900 and 3,000, but not 2,673 or 2,873. Stored the full 74-put expiry subset, retrieval time and raw-response hash in [the catalogue snapshot](deribit-catalog-2026-09-17.json). Source: [public instruments endpoint](https://www.deribit.com/api/v2/public/get_instruments?currency=USDC&kind=option&expired=false).

This establishes listing presence at retrieval, not an executable price, current order depth, available combo route or account eligibility. New listings can change the comparison.

### DIVA: a custom payout and signed offer are also existing mechanisms

DIVA represents a contingent pool through complementary long and short tokens. Pool creation can specify its payoff parameters. This is a serious alternative to building a new contract for a custom bounded ramp. [Position creation](https://docs.divaprotocol.io/diva-app/create-position-tokens).

Inspected repository commit `1263828cd5c5b2192e876edef90444448e66176d`, obtained from the repository HEAD on the research date:

| Implementation | What it actually does |
|---|---|
| [EIP712CreateFacet](https://github.com/divaprotocol/diva-protocol-v1/blob/1263828cd5c5b2192e876edef90444448e66176d/contracts/facets/EIP712CreateFacet.sol) | Validates a maker's offer, derives the two contributions, creates the pool on first fill, and allocates opposite positions. Subsequent fills add to the same pool. Creation therefore need not precede agreement with a counterparty. |
| [LibDIVA](https://github.com/divaprotocol/diva-protocol-v1/blob/1263828cd5c5b2192e876edef90444448e66176d/contracts/libraries/LibDIVA.sol) | `_calcPayoffs` computes the bounded curve from floor, inflection, cap and gradient. `_removeLiquidityLib` checks and burns matching amounts of that pool's complementary tokens. The inspected path releases pool backing; it does not compute a wallet-wide minimum over unrelated pools. |
| [EIP712RemoveFacet](https://github.com/divaprotocol/diva-protocol-v1/blob/1263828cd5c5b2192e876edef90444448e66176d/contracts/facets/EIP712RemoveFacet.sol) and [LibEIP712](https://github.com/divaprotocol/diva-protocol-v1/blob/1263828cd5c5b2192e876edef90444448e66176d/contracts/libraries/LibEIP712.sol) | Signed removal offers allow the complementary positions to come from different participants and divide released collateral according to the offer. Batch removal exists. |

**Architectural inference:** a smart-account batch or carefully designed adapter could close an old pool position with a signed removal offer and open a new one with a signed creation offer in one transaction. This needs validation of caller identity, allowances, fees and intermediate funding. It was not implemented or executed here. An adapter cannot claim general cross-pool netting merely because its calls are atomic.

This is why “custom terms + one acceptance” is not yet a defensible reason for a new settlement engine.

### Polymarket: compare with its current combo flow

The current documentation describes requesting a combo price, receiving a signed quote and accepting it. It also describes optional maker last look. These are already package quote mechanics, so an analysis based only on separate binary orders would be incomplete. [Combo overview](https://docs.polymarket.com/trading/combos/overview).

The requester API chooses compatible legs from the enabled catalogue, returns exact required amounts, accepts a signed order and exposes execution status. The documented requester side is currently YES, and its buy/sell requests are separate operations. The overview and requester guide disagree about the acceptance-window duration; an integration should follow returned expiry data rather than hardcode either description. No claim about an atomic sell-old/buy-new combo roll was verified. [Requester API](https://docs.polymarket.com/trading/combos/requesters).

These combos are conjunctions of existing outcomes, not a weighted sum of arbitrary numeric payout functions. That distinction matters: a parlay is not an option spread. [Combinatorial positions](https://docs.polymarket.com/trading/positions/combinatorial).

Collateral return also has a documented plan-and-execute flow. It decomposes compatible positions, merges complementary exposure into collateral, and retains residual positions. Therefore “release cash while preserving remaining exposure” alone is not new. [Collateral return](https://docs.polymarket.com/trading/combos/collateral-return).

### Conditional Tokens: a stronger accounting baseline for the tail example

The framework prepares a condition with a fixed outcome-slot count, supports collections of outcomes, and splits/merges claims against collateral. Its guide also includes scalar outcomes, so it should not be described as limited to categorical bets. [Developer guide](https://gnosis-conditional-tokens.readthedocs.io/en/latest/developer-guide.html).

**Our construction:** prepare low, middle, high and VOID slots. The tail basket is low plus high; its complement is middle plus VOID. Starting with 100 units of complete-set backing, a seller can retain the complement and sell the tail basket for 54. Acquiring half the basket later makes 50 complete sets redeemable. Pay 27 plus a fee of 1 and release 22 to the seller. This reproduces Case C's funding, including its exceptional outcome. A router, counterparty authorization and fees still need implementation; the token accounting is not a capital disadvantage.

## Comparison of the complete work involved

These are semantic tasks, not measured click counts. All flows need an identified account, funds, a clear contract and a confirmed result. One trade authorization may still trigger a wallet confirmation; setup and withdrawals must be counted separately in a user study.

| Route | User's trading task after setup | Setup, ongoing work and trust | What this investigation establishes |
|---|---|---|---|
| Keep current position | Review existing exposure; take no action | Existing provider and settlement terms remain | Zero switching effort; fails a task only when changing exposure actually matters |
| Existing option strategy interface | Select an eligible spread/package, inspect price and margin, submit, reconcile | Exchange account, venue custody/margin rules; listed instruments and package eligibility | Strong baseline for standard curves; no AsceMarket execution novelty established |
| Payout editor over existing option APIs | Edit a curve; software maps it to eligible instruments and submits a supported package | Maintain instrument mapping, account authorization and venue adapters; disclose approximation | Could deliver much of AsceMarket's interface benefit without a new ledger |
| Custom-pool interface or adapter | Configure/translate the curve, review the signed offer, accept; close/reopen when editing | Token approvals, pool inventory, caller-sensitive batching and existing contract rules | Custom creation exists; a complete edit adapter remains an engineering hypothesis |
| Conditional-claim router | Convert a portfolio change into transfers, splits/merges and an exact settlement plan | Condition compatibility, token inventory, routing/authorization and contract trust | Matches the tail example's accounting; does not establish a ready-made consumer workflow |
| Proposed AsceMarket account | Edit the desired payout; inspect the whole account change; accept one exact offer | New custody/accounting and authorization implementation, provider quoting, execution recovery and future maintenance | Research ledger handles the accounting; quote service and usability advantage are unbuilt |

## What advantage remains plausible?

The remaining hypothesis is **repeated edits of custom numeric exposure in one account**, with one understandable quote and exact funding across its existing compatible positions. It is stronger than a claim about one option spread or one RFQ.

Evidence currently supports three different conclusions:

- A standard capped payout is familiar functionality. Treat Case A as a control, not the main reason to build.
- A threshold absent from a listed catalogue is a real representational mismatch, but custom-contract infrastructure can address it. Whether the exact threshold is valuable is untested.
- Combined accounting is useful, but our tail case has an equally funded conditional-token construction. It does not demonstrate a new capital capability.

**Recommendation: narrow the product test and keep the choice of settlement engine open.** Compare the same payout editor over existing infrastructure with the proposed account engine. If both solve the chosen tasks at acceptable cost, prefer the simpler implementation. Retain the custom engine only where a necessary, recurring operation cannot be delivered as well by that adapter, or measured lifecycle costs justify the extra infrastructure.

No conclusion here relies on launch jurisdiction, team size, deadline, acquiring liquidity or solving external reporting. Those were excluded from this stage. No simulated trades are counted as demand.
