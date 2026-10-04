# AsceExecutor local prototype specification

**For implementation approval — 1 October 2026. No implementation is authorized by this document alone.** This is the current specification for the flexible-payoff clearing experiment. Earlier CTF documents remain comparison research. This document defines behavior, rather than a development schedule.

## 1. What we will build

An executor where wallets buy and sell bounded covers, while collateral backs the worst possible **combined** obligation instead of each cover separately.

| Prototype choice | Behavior |
|---|---|
| Environment | Local Foundry tests; no deployment to a public network |
| Collateral | One immutable, ordinary USDC-compatible token; 6-decimal MockUSDC in tests |
| Event / observation | One BTC/USD event and one specified future observation |
| Payoffs | Bounded straight-line segments with explicit jumps and exact boundary values |
| Claims | Internal signed positions; direct collateral settlement |
| Execution | Offchain EOA-signed quotes, executed by the named counterparty |
| Fills | Entire signed order or revert; partial position closes use smaller new orders |
| Fees | Zero |
| Risk | Deterministic same-observation netting; no price-based liquidation |
| Oracle failure | Protocol-wide zero payout on INVALID or timeout; premiums are not refunded |

The test fixture uses one professional maker and many customers. **A maker is a wallet signing a quote, not a separate contract or privileged protocol role.** Any wallet can be a buyer or seller if its resulting account is solvent. Quotes do not reserve collateral before execution and can become unfillable.

The broad event is not a fixed list of price buckets. This first experiment supports only one observation under it. Later observations require separately reserved settlement groups; merely sharing the BTC event will not authorize offsets between different times or measurements.

## 2. Event, observation, cover and position

| Object | Simple meaning | Example |
|---|---|---|
| Event | The underlying subject and eligible horizon | BTC/USD through 31 December |
| Observation | The particular fact the oracle must finalize | BTC/USD at an exact UTC timestamp, using specified source and sample-selection rules |
| Cover | A payment rule applied to that observation | Pay 100% when BTC ≥100k |
| Position | A wallet's signed amount of that cover | +10,000 USDC coverage bought; −10,000 underwritten |

The immutable observation specification commits to `eventId`, measurement/source/rule hash, `observationTime`, integer units and permitted scalar bounds. Its time must be in the future at setup and within the event horizon. The mock does not fetch or verify a real feed; its trusted resolver supplies a value in the committed domain.

The mock is configured once at deployment. It exposes the event and observation IDs/specifications; the executor binds to those IDs at deployment. No mutable event registry or separate user-facing event-creation transaction is needed for this prototype.

```text
curveHash = keccak256(validatedCurveBytes)
coverId   = keccak256(abi.encode(
    coverDomain, eventId, observationId, curveHash
))
```

`coverDomain` binds the protocol/version, chain and executor. The collateral token and failure policy are protocol settings, not configurable cover fields. Owner, quantity, premium and order salt are not part of cover identity.

Cover construction happens offchain. On first successful fill, the executor verifies the supplied curve against `coverId` and stores its immutable bytes. Subsequent fills can reference that stored descriptor. A hash alone cannot calculate payout or collateral. Encoding is syntactically canonical; equivalent curves with redundant knots can still have different hashes.

## 3. Contracts and libraries

| Component | Responsibility | Stored state / trust |
|---|---|---|
| `AsceExecutor` | Deposits, signed-order execution, positions, collateral checks, cancellations, settlement and withdrawals | Account cash, positions, cover descriptors, order status, epochs and settlement flags. Holds collateral; trusts the immutable token and oracle |
| `MockOracle` | Expose the fixed definitions and finalize one scalar value or INVALID | Fixed resolver, definitions, status and result. Resolver is deliberately trusted in local tests |
| `PayoffLib` | Decode/validate curves and evaluate rational payouts | Pure functions; no storage or external calls |
| `RiskLib` | Derive a safe portfolio reserve from authenticated curves and signed positions | Pure math over bounded memory inputs; no trusted offchain risk answer |
| `OrderLib` | Define/hash the order and interpret its side | No storage; use established EIP-712/ECDSA helpers for signing and verification |

These are **two deployed protocol contracts**, plus the test collateral fixture. Libraries are internal Solidity code, not separate custody services. There is no separate margin vault, maker contract, position token or CTF adapter in this experiment. No upgradeability or administrator ability to rewrite claims or take collateral.

`AsceExecutor` uses guarded token transfers for deposit/withdrawal. Fills move internal cash and positions without calling a pricing service. Oracle reads are read-only. All balance-changing entry points share reentrancy protection.

## 4. Payoff encoding

Use the locked unified representation; there is no binary/range/scalar payoff-type enum.

```text
Header: uint8 version = 2 | uint8 knotCount | uint64 constantFraction
Knot:   int128 x | uint64 below | uint64 at | uint64 above
```

The header is 10 bytes; each knot is 40 bytes in big-endian packed encoding. Fractions are integers from zero to `D = 1e18`. Coordinates use the observation's declared integer units. For nonconstant curves the header's constant field is zero; zero knots encode a constant curve. All byte lengths must match exactly.

Rules:

- At a knot, use `at`.
- Between knots, interpolate from the earlier knot's `above` to the later knot's `below`.
- Outside the first/last knot, use the corresponding constant tail.
- Require strictly increasing coordinates and bounded fractions.
- Allow 0–16 knots per curve and at most 8 nonzero covers per account: at most 128 portfolio knots before deduplication.

A normal point has `below = at = above`. A binary at 100k can have `below = 0, at = above = D`. Two jumps create an exact range. Binary, range, ramps, capped call/put, tents, trapezoids, staircases and multiple peaks use this one evaluator.

Reuse Scalar-AMM's validation and full-precision arithmetic principles, not its unmodified 24-byte decoder. This prototype accepts version 2 only; existing version-1 bytes are not reinterpreted. **Settlement rounds once in cash units**, rather than flooring a normalized interpolated fraction and then flooring cash again. That intentional difference is part of this new version's contract.

## 5. Order specification

The following is an interface sketch, not implemented Solidity:

```solidity
enum Side { BUY, SELL } // direction of the maker's position change

struct Order {
    address maker;       // wallet signing and funding this quote
    address taker;       // only this wallet may execute it
    bytes32 coverId;
    Side side;
    uint96 quantity;     // coverage amount in USDC base units
    uint128 premium;     // total cash consideration for the whole order
    uint64 validUntil;
    uint64 epoch;        // maker's current cancellation epoch
    uint256 salt;        // distinguishes individual orders
}
```

One USDC is `1_000_000` base units. `quantity` determines contractual coverage; `premium` is its negotiated price. They are separate numbers.

| Side | Position change | Cash change |
|---|---|---|
| Maker SELL | Maker −quantity; taker +quantity | Taker pays premium to maker |
| Maker BUY | Maker +quantity; taker −quantity | Maker pays premium to taker |

SELL can create an underwritten obligation or sell existing exposure. BUY can purchase exposure or buy back an existing short. Signed quantities net within the identical cover. Different covers are combined by the risk engine.

Use EIP-712 domain `AsceExecutor`, version `1`, current chain ID and executor address. Encode `side` as `uint8` in the signed type. Require an EOA signature recovering `maker`, `msg.sender == taker`, distinct nonzero counterparties, positive quantity, current epoch and `block.timestamp < validUntil <= observationTime`. Always block trading at/after observation time. Store the order digest as FILLED only after a successful atomic execution. [EIP-712 specification](https://eips.ethereum.org/EIPS/eip-712)

`cancelOrder(order)` permanently cancels an unused digest and requires its maker. `cancelAllOrders()` increments the caller's epoch. Filled/cancelled orders cannot execute. Signed expiry and cancellation are enforced onchain; EIP-712 by itself is not replay protection.

No partial order fills, relayer authority, smart-wallet signatures, signer delegation or signature-preapproval cache in version 0. A user can close half a position by accepting a new order for half its quantity; that order still fills completely.

## 6. What state is stored?

Here “state” has two meanings: **a possible oracle result**, and **contract storage**. The risk engine considers possible scalar results; the contract stores the records below. We do not create a token or storage slot for every possible BTC price.

| Executor record | Meaning |
|---|---|
| Immutable collateral/oracle and event/observation IDs | Fixed protocol dependencies and account scope |
| `covers[coverId]` | Validated, immutable curve bytes |
| `cash[wallet]` | Deposits − withdrawals + net premiums + materialized settlement cashflows |
| `position[wallet][coverId]` | Signed coverage; positive is a receipt, negative an obligation |
| `activeCovers[wallet]` | Bounded index used for risk calculations; no unbounded holder scan |
| `requiredCollateral[wallet]` | Derived reserve cache, never another token balance |
| `orderStatus[digest]` | UNUSED, FILLED or CANCELLED |
| `orderEpoch[wallet]` | Cancels all older quotes |
| `settled[wallet]` | Whether this observation's portfolio has already become cash |

The fixture has one event, so each wallet has one cash account. A maker account is just these mappings keyed by its wallet.

```text
freeCollateral = cash − requiredCollateral
```

Store cash and the reserve; calculate free collateral. Do not maintain independently editable free/locked balances. Use checked arithmetic, `int128` positions with absolute quantity capped at `2^96−1` per wallet/cover, `uint128` cash/reserves, and wider checked intermediates. Reverts enforce bounds before narrowing casts. Realized PnL can be derived from logged cashflows; it is not a second spendable cash balance.

## 7. Clearing rule, including rounding

Let `r_i(x)` be the curve's exact rational fraction numerator between 0 and `D`. For an account with signed quantity `q_i`, its cashflow for cover `i` is:

```text
t_i(x) = mathematicalFloor(q_i × r_i(x) / D)
P(x)   = sum t_i(x)
```

Positive quantities round receipts down; negative quantities round debits up in magnitude. Solidity's ordinary signed division truncates toward zero and must not be used as a substitute for mathematical floor. Evaluate the rational interpolation and quantity together using full-precision multiplication/division. [Solidity integer division](https://docs.soliditylang.org/en/v0.8.34/types.html#division), [Solady full-precision arithmetic](https://github.com/Vectorized/solady/blob/main/src/utils/FixedPointMathLib.sol)

For example, two receipts rounding to 3 and 6 base units can be backed by a 10-unit debit. The remaining unit stays in the vault as rounding surplus; it is not credited twice. No surplus-sweep function is provided in this prototype.

The solvency requirement is:

```text
cash >= max(0, maximum over valid x of −P(x))
```

The exact real-valued portfolio is affine between the union of all knots. Its extrema therefore occur at endpoints, exact knot values or one-sided knot limits. The engine derives that union itself, includes bounded-domain endpoints and checks protocol INVALID separately. It does not trust a caller's proposed state list.

Per-cover cash rounding can create interior steps. The first implementation deliberately uses this safe reserve rather than claiming the rounded minimum:

```text
N = number of nonzero cover positions
S(c) = sum mathematicalFloor(q_i × r_i(c) / D) at each candidate c
R = max(0, −min S(c) + N − 1)      // if N > 0
R = 0                             // if N = 0, or all positions are nonnegative
```

The buffer is at most **7 USDC base units (0.000007 USDC)** for eight active covers. Candidate rounding can add further conservative slack; it is not an exact minimum claim. Curves are evaluated as rational limits at discontinuities, and unattainable one-sided limits can also make this bound conservative.

Why the buffer works: for ideal aggregate `I(x)`, `sum floor(z_i) > sum z_i − N`. The minimum sampled integer sum is no greater than the ideal minimum. Since actual cashflows and the sampled minimum are integers, `P(x) >= min S(c) − (N−1)` everywhere. Nonnegative-only portfolios have no terminal debit and need no reserve. INVALID has `P=0` under the fixed protocol rule.

The interpolation numerator is at most `D × span`; int128 knot spans are below `2^128`, so that numerator and `D × span` fit uint256. Multiplying by the bounded quantity can require a 512-bit product; use a reviewed full-multiply/divide helper. Do not implement overflow-prone chained multiplication or double-rounded cash evaluation.

## 8. Public actions and atomic behavior

| Action | What happens |
|---|---|
| `deposit(amount)` | Transfer exact collateral in; credit the caller by the verified received amount |
| `fillOrder(order, signature, curveBytes)` | Verify quote/cover, apply paired position changes and cash transfer, check both accounts, consume order atomically |
| `cancelOrder(order)` / `cancelAllOrders()` | Revoke the caller's quotes |
| `withdraw(amount)` | Settle the caller first if the oracle is final; require amount ≤ free collateral; debit then transfer to caller |
| `settle(account)` | Anyone can materialize that account's finalized portfolio; funds remain credited to its owner |
| Views / previews | Read descriptors, positions, cash/reserve/free balances, order validity and proposed post-trade risk |

For a fill: the premium payer must have cash, the paired quantities must conserve exposure, both candidate cash balances must satisfy their recomputed reserves, and portfolio-size limits must pass. Otherwise everything reverts, including first-use cover registration and order consumption. Collateral can include the premium actually received in that same atomic fill; an unexecuted quote or future premium is not an asset.

All successful fills emit order, position, premium and reserve changes. Closing, reshaping and withdrawals follow the same risk check. A reshape is an ordinary close plus a new purchase, each independently admissible; atomic multi-order packages are deferred.

## 9. Lifecycle and settlement

```text
Oracle:     PENDING ── resolver supplies value ──> RESOLVED
               └──── resolver invalidates / timeout ──> INVALID
Order:      UNUSED ── successful fill ──> FILLED
               └──── maker cancels ──> CANCELLED
Account:    UNSETTLED ── settle after finality ──> SETTLED
```

Trading is allowed only before observation time while the oracle is PENDING. PENDING after that time means trading is closed and reserves remain. The mock's immutable, protocol-wide grace period is 24 hours. Its resolver can finalize only from observation time through the deadline; after the deadline anyone can finalize INVALID. Final outcomes cannot be changed. Dispute/challenge mechanics belong to a later real oracle adapter, not this mock.

After finality, `settle(account)` evaluates at most eight covers, adds the account's **signed net cashflow** to cash, marks it settled, clears its active-cover index and sets its reserve to zero. Historical quantities remain readable but no longer represent unpaid positions. INVALID materializes zero cashflow. No holder-wide settlement loop or ERC-20 payout is required during this step.

Oracle finalization alone does not delete liabilities or unlock their backing. A short account must have its debit reflected in cash before its reserve is released. Long accounts can settle first because every remaining account's finalized equity is nonnegative. Anyone can trigger settlement; only the account owner can withdraw its cash. Repeated settlement cannot credit or debit twice.

## 10. Worked example

At the same observation, the maker sells:

| Cover | Coverage | Payout rule |
|---|---:|---|
| A | 10,000 USDC | Binary: BTC ≥100k |
| B | 10,000 USDC | Range: 80k ≤ BTC <100k |
| C | 5,000 USDC | Full at/below 80k; falls linearly to zero at 100k |

The summed caps are 25,000 USDC. The combined maximum is 15,000, attained at 80k. This prototype reserves **15,000.000002 USDC**, including its two-base-unit buffer.

Suppose the maker deposits 15,000.000002 and receives 3,000 total premiums. Cash is 18,000.000002; reserve is 15,000.000002; free collateral is 3,000. It can withdraw that 3,000.

At BTC 90k: A pays 0, B pays 10,000, C pays 2,500. The maker materializes a 12,500 debit and keeps 2,500.000002 cash. Buyers independently materialize their receipts and withdraw. Settlement ordering changes neither entitlement nor solvency.

If the maker initially deposits only 12,000.000002 and relies on those 3,000 premiums, every individual fill must still pass its own collateral check. The final portfolio being safe does not authorize an unsafe intermediate fill.

## 11. Checks required before calling this prototype correct

- After every admissible trade/close/withdrawal, each account satisfies the authoritative recomputed reserve; caches match positions.
- Trade cash transfers sum to zero; pre-settlement cover quantities sum to zero across accounts, including positions later archived on settlement.
- For every valid remaining outcome, every account's equity `cash + unpaid signed payouts` is nonnegative, and total equity is no greater than actual vault assets. Deposits/withdrawals update custody and cash equally.
- During partial settlement, raw stored cash totals can exceed custody because some debits are still unpaid. Reconciliation must include those finalized pending cashflows; it must not count buyer cash and the same unresolved claim twice. After all accounts settle, cash totals cannot exceed custody; the difference is unswept rounding surplus.
- Boundary, tail, constant, jump, zero-quantity removal, precision and maximal-coordinate cases match an independent rational reference.
- Fuzz trades, closes, cancels, withdrawals and every settlement order. Test stale epochs, replay, wrong taker/signature, wrong curve preimage, oracle timing, malformed bytes, failed token transfers, callbacks and limit overflows.
- Benchmark maximum permitted active-cover/knot portfolios before keeping the proposed 8/16 limits. No gas ceiling is claimed yet.

A local rational experiment checked 5,000 random portfolios, 105,000 scalar outcomes and 5,000 conserving signed-rounding cases against the proposed bound; all passed. This supplements the argument above. It is not Solidity validation, a complete proof of implementation or a security audit.

## 12. What approval covers

Approval authorizes implementing this local specification and its tests. It does not authorize deployment or production use.

Deferred: multiple observations, cross-time offsets, cross-event offsets, path/multivariate observations, native categorical oracle schemas, partial order fills, transferable claim tokens, CTF export, AMM pricing, fees, passive pooled LP shares and production oracle/dispute handling. Scalar-coded categorical tables are representable by the curve language, but a categorical measurement adapter is outside this BTC scalar prototype.

CTF remains the comparison baseline: shared complete sets and interpolation bases can already reproduce important capital savings. The experiment tests whether flexible per-cover knots plus an account ledger are a useful implementation choice; it does not claim to invent complete-set collateral netting. See [the Scalar library review](../research/scalar-payoff-library-review-2026-10-01.md), [unified representation research](../research/unified-payoff-clearing-design-2026-10-01.md) and [Polymarket exchange review](../research/polymarket-exchange-review-2026-10-01.md).
