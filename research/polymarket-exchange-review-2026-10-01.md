# Polymarket exchange review and implications for Asce

Research date: 1 October 2026. This is a source review and contract-design input. It does not implement contracts or verify deployed bytecode. Read it alongside the [selected CTF architecture](../contracts/ctf-cover-architecture.md) and [clearing proof](../docs/03-math.md).

## 1. What “one shared definition per observation/domain” means

Use the simpler phrase **one shared settlement condition**. Define the measurement and its possible results once; many covers refer to it.

For example, fix these terms before issuing claims:

- Subject: BTC/USD.
- Observation: one specified UTC timestamp on 31 December 2026.
- Source: one specified feed and historical-sample selection rule.
- Domain: five price buckets plus INVALID, with the boundaries below.
- Policy: units, precision, trading cutoff, finality, timeout and failure treatment.

This example uses:

| Slot | Terminal result | Atomic mask |
|---|---|---|
| 0 | BTC < 80,000 | 1 |
| 1 | 80,000 ≤ BTC < 100,000 | 2 |
| 2 | 100,000 ≤ BTC < 120,000 | 4 |
| 3 | 120,000 ≤ BTC < 150,000 | 8 |
| 4 | BTC ≥ 150,000 | 16 |
| 5 | INVALID | 32 |

The source and timestamp above are illustrative placeholders, not a complete deployable oracle specification. The implementation must commit to their exact values and rules.

Different covers can then be built offchain:

| Cover | Selected slots | Native subset mask | Payout for 100 units when BTC is 107,000 |
|---|---|---|---|
| BTC < 100,000 | 0, 1 | 3 | 0 |
| 80,000 ≤ BTC < 120,000 | 1, 2 | 6 | 100 |
| BTC ≥ 120,000 | 3, 4 | 24 | 0 |

The oracle reports the common result once: `[0,0,1,0,0,0]`. CTF then assigns payouts to every subset or basket under that condition. There is no loop over covers and no `resolveCover(coverId)` call. A cover with unequal state payouts is a basket of atomic claims, rather than one native subset token.

The cover's selected states differ; the source, observation and state meanings are shared. A different observation time, source rule, grid or definition of INVALID/finality is a different settlement definition. Different payout amounts on the same recognized states can still share that condition; they change the cover's basket. A broad label such as “BTC price” does not establish common settlement semantics.

CTF initializes a condition before splitting claims. Its identity includes the reporting oracle, question ID and slot count. The native token additionally binds the collateral and collection. Asce must commit the economic terms into the question ID and validate descriptors against that commitment. A hash alone cannot tell the oracle which measurement to obtain. [CTF implementation](https://github.com/gnosis/conditional-tokens-contracts/blob/master/contracts/ConditionalTokens.sol)

```text
questionId  = hash(versioned, canonical settlement terms)
conditionId = CTF.getConditionId(AsceOracleAdapter, questionId, 6)
tokenId     = CTF.getPositionId(USDC,
                CTF.getCollectionId(0, conditionId, selectedMask))
```

Use CTF's collection helper; it is not a substitute application hash. Premium, creator, quantity and order salt do not change the native cover identity. For arbitrary baskets, a canonical basket hash can identify the descriptor, but it is not itself a mintable native CTF token ID. [CTF identifier helpers](https://github.com/gnosis/conditional-tokens-contracts/blob/master/contracts/CTHelpers.sol)

## 2. Research scope and pinned versions

The old exchange repository is archived and points to V2. The official contracts page separately lists the current exchange, collateral, oracle and Combos contracts. A historical V1 source review is not a complete review of today's Polymarket platform. [Archived repository](https://github.com/Polymarket/ctf-exchange), [official contract catalogue](https://docs.polymarket.com/resources/contracts)

| Component | Inspected revision | Work performed |
|---|---|---|
| CTF Exchange V2 | `ccc0596074f4dfd62c944fbca4de252893b82b4b` | Read exchange, orders, signatures, assets, fees, pause, collateral adapter, relevant tests and both bundled audit reports; ran the full local suite |
| Legacy CTF Exchange | `ed5c7708b7be3aa98bf5f0c6602b57cc498e2ef4` | Read execution, order, cancellation, registry and funding paths; did not run its suite |
| UMA CTF Adapter | `8b76cc9e0d46c6f7450a0adb0ddc0f5b0568c9cc` | Read initialization, resolution, dispute/reset and exceptional payouts; did not run its suite |

Source hashes, dependency revisions, test counts and gas observations are saved in [the evidence record](polymarket-exchange-review-results.json). All checkouts and test execution were local and disposable. No live transactions were sent.

## 3. The actual boundary between exchange, oracle and CTF

| Layer | Polymarket responsibility | Asce equivalent |
|---|---|---|
| Offchain order service | Collect, quote, match and submit signed orders | RFQ/quote service and a route builder |
| Exchange | Verify authorizations and execute asset transfers and funded conversions | `AsceExecutor`, or `AsceExchange` if that name communicates its role better |
| Oracle adapter | Initialize settlement questions and translate oracle answers into CTF payouts | `AsceOracleAdapter`, with Asce's scalar rules |
| CTF | Funded claims, balances, split/merge, final redemption | Retain native CTF |
| Collateral integration | Current V2 supports a wrapped collateral system | Direct mock USDC for the accepted local MVP |

V2's `matchOrders` is operator-only and trading-pause gated. It accepts a condition, signed taker/maker orders, fill quantities and fee amounts. It does not create real-world questions or report oracle payouts. [V2 exchange entry points](https://github.com/Polymarket/ctf-exchange-v2/blob/ccc0596074f4dfd62c944fbca4de252893b82b4b/src/exchange/CTFExchange.sol)

The inspected UMA adapter stores the question's oracle terms, prepares its two-slot CTF condition and requests UMA resolution. Finalization obtains an answer and reports payouts. It includes reset/dispute handling and an administrator manual-resolution path after a safety delay. Asce should preserve this separation while defining its own scalar/finality policy. Copying the UMA adapter's binary answer mapping would not implement our bucket domain. [Pinned UMA adapter](https://github.com/Polymarket/uma-ctf-adapter/blob/8b76cc9e0d46c6f7450a0adb0ddc0f5b0568c9cc/src/UmaCtfAdapter.sol)

One identity detail should not be copied: this UMA adapter appends the initializer address to the supplied ancillary data before hashing it. Identical supplied text from different initializers therefore produces different question IDs. Asce's canonical condition identity should exclude creator and arbitrary order salt so identical settlement terms can converge on the same condition. [Ancillary-data helper](https://github.com/Polymarket/uma-ctf-adapter/blob/8b76cc9e0d46c6f7450a0adb0ddc0f5b0568c9cc/src/libraries/AncillaryDataLib.sol)

“Trade settlement” means exchanging cash and claims during a fill. “Event settlement” means final oracle resolution and redemption later. The exchange has no reason to iterate over every holder at expiry.

## 4. Orders, traders and operators

V2 signs an EIP-712 order containing salt, funding wallet (`maker`), signer, one token ID, offered/requested amounts, side, signature type, creation timestamp, metadata and builder attribution. The signature is outside the signed struct hash. BUY offers collateral for a claim; SELL offers the claim for collateral. The amount ratio establishes the price limit. [Order schema](https://github.com/Polymarket/ctf-exchange-v2/blob/ccc0596074f4dfd62c944fbca4de252893b82b4b/src/exchange/libraries/Structs.sol), [EIP-712 hashing](https://github.com/Polymarket/ctf-exchange-v2/blob/ccc0596074f4dfd62c944fbca4de252893b82b4b/src/exchange/mixins/Hashing.sol)

`maker` in the struct means the wallet supplying that order's assets. Even the taker order has an `Order.maker`. It is not a special market-maker contract or a protocol-created account. The separately authorized **operator** submits matches; it need not be the economic counterparty. [Role management](https://github.com/Polymarket/ctf-exchange-v2/blob/ccc0596074f4dfd62c944fbca4de252893b82b4b/src/exchange/mixins/Auth.sol)

V2 supports EOAs, Polymarket-specific proxy/Safe ownership checks and ERC-1271 contract wallets. An operator can cache a preapproval only after verifying a valid signature. An empty signature then requires preapproval; a supplied nonempty signature is checked normally. Cached authorization can outlive a contract wallet's changed signing policy. The invalidation path removes that cache; it is not permanent cancellation of an otherwise valid signed order. [Signature implementation](https://github.com/Polymarket/ctf-exchange-v2/blob/ccc0596074f4dfd62c944fbca4de252893b82b4b/src/exchange/mixins/Signatures.sol), [preapproval tests](https://github.com/Polymarket/ctf-exchange-v2/blob/ccc0596074f4dfd62c944fbca4de252893b82b4b/src/test/Preapproved.t.sol)

**Asce recommendation:** start with ordinary EOA signed quotes and caller-funded fills. This does not require a privileged matching operator. Add generic ERC-1271 if the first maker uses a smart wallet. Do not import Polymarket wallet factories, builder attribution or preapproval caching into the first prototype. Relayed execution later requires a signed customer intent or an equivalent narrowly scoped authorization; an allowance alone is not customer consent to a particular trade.

## 5. Three exchange paths, with numbers

Both versions distinguish existing-token trades, funded minting and complete-set merging. V2 can batch several matches and aggregate CTF operations. A BUY taker can combine existing-token sellers with opposite-token buyers; a SELL taker can combine buyers with opposite-token sellers. Because all makers face one taker side, the standard binary batch is not a general collection of unrelated mint and merge operations. [Trading implementation](https://github.com/Polymarket/ctf-exchange-v2/blob/ccc0596074f4dfd62c944fbca4de252893b82b4b/src/exchange/mixins/Trading.sol), [balance tests](https://github.com/Polymarket/ctf-exchange-v2/blob/ccc0596074f4dfd62c944fbca4de252893b82b4b/src/test/BalanceDeltas.t.sol)

These examples use zero fees and collateral units, not a claim that current Polymarket trades raw USDC directly:

| Path | Example | What happens |
|---|---|---|
| Existing claim trade (`COMPLEMENTARY`) | Alice buys 100 YES for 40; Bob already holds 100 YES and sells for 40 | Cash and YES change hands; backing is unchanged |
| Joint issuance (`MINT`) | Alice buys 100 YES for 40; Bob buys 100 NO for 60 | Their combined 100 funds CTF; each receives 100 units of the requested token |
| Joint redemption before expiry (`MERGE`) | Alice sells 100 YES for 40; Bob sells 100 NO for 60 | The complete set burns; CTF returns 100, distributed 40/60 |

In this source, `COMPLEMENTARY` names opposite **order sides on the same asset**, not two different complementary assets. For binary minting, buy prices must sum to at least one; for merging, sell prices must sum to at most one. Exactly crossing prices make the examples unambiguous. Better prices leave surplus whose allocation is part of execution policy, not collateral calculation. [Legacy matching calculations](https://github.com/Polymarket/ctf-exchange/blob/ed5c7708b7be3aa98bf5f0c6602b57cc498e2ef4/src/exchange/libraries/CalculatorHelper.sol)

The useful precedent is strong: **a seller need not independently prefund a fresh full-cap position if counterparties and retained complementary exposure fund issuance atomically**. This is established CTF/exchange functionality. Asce extends execution to a common categorical inventory and supported subset/basket routes; it should not claim joint-funded issuance as an invention.

## 6. What prevents a direct drop-in fork

V2 derives only position IDs for masks `1` and `2` for the supplied condition. Its mint/merge helper fixes partition `[1,2]`. This is a binary matcher. On a six-slot condition, those masks do not exhaust the domain: splitting `[1,2]` would subdivide the existing union `3`, not mint a six-state complete set from collateral. Simply accepting extra token IDs would leave the funding/conversion logic wrong. [Asset operations](https://github.com/Polymarket/ctf-exchange-v2/blob/ccc0596074f4dfd62c944fbca4de252893b82b4b/src/exchange/mixins/AssetOperations.sol), [token validation](https://github.com/Polymarket/ctf-exchange-v2/blob/ccc0596074f4dfd62c944fbca4de252893b82b4b/src/exchange/mixins/Trading.sol)

V1 uses an administrator-maintained token/complement registry rather than V2's derivation. Its native issuance still uses the fixed binary partition. Registration also is not a general proof that an arbitrary pair is the promised complete partition. Asce should derive and check accepted condition/mask identities rather than reuse a trusted arbitrary-token mapping. [Legacy registry](https://github.com/Polymarket/ctf-exchange/blob/ed5c7708b7be3aa98bf5f0c6602b57cc498e2ef4/src/exchange/mixins/Registry.sol), [legacy asset operations](https://github.com/Polymarket/ctf-exchange/blob/ed5c7708b7be3aa98bf5f0c6602b57cc498e2ef4/src/exchange/mixins/AssetOperations.sol)

Asce's full six-slot mask is `63`. The complementary claim to subset `S` is `63 XOR S`. A funded split of `[S,63 XOR S]` creates the cover and its true complement. A route can also split into atomic masks `[1,2,4,8,16,32]`, allocate several covers, and retain the residual inventory. Overlapping masks are not a disjoint partition; normalize them into atoms before calculating demand.

For unequal payout vectors, one order with one token ID cannot describe the complete desired basket. Initially support aligned threshold/interval subset tokens; add canonical atomic basket commitments and bounded batch transfers when variable curves enter trading scope. Do not present the basket hash as an ERC-1155 wrapper unless a wrapper is actually implemented.

## 7. Cancellation, expiry, fees and rounding: V1 is not V2

| Feature | Inspected legacy V1 | Inspected V2 | Asce proposal |
|---|---|---|---|
| Execution access | Operator-only fills/matches | Operator-only `matchOrders` | Caller-funded RFQ fills; no privileged matcher required initially |
| User cancellation | Per-order cancel and wallet nonce invalidation | No equivalent per-order cancellation or nonce manager | Owner cancellation plus a wallet quote epoch |
| Signed expiry | `expiration` checked onchain | Creation `timestamp`; no onchain expiry check | Explicit signed deadline, checked onchain |
| Counterparty restriction | Signed `taker`, checked against transaction submitter | No signed taker field | Optional actual customer restriction, with precisely defined semantics |
| Fees | Signed fee rate; implementation calculates fee | Operator supplies fees; global cap | Zero protocol fees in local MVP |
| Token acceptance | Admin registry | Derived binary IDs | Derived masks under an adapter-recognized fixed condition |
| Reentrancy guard | Present | Absent in the core exchange | Retain a guard for public Asce execution |

[V1 order schema](https://github.com/Polymarket/ctf-exchange/blob/ed5c7708b7be3aa98bf5f0c6602b57cc498e2ef4/src/exchange/libraries/OrderStructs.sol), [V1 checks/cancellation](https://github.com/Polymarket/ctf-exchange/blob/ed5c7708b7be3aa98bf5f0c6602b57cc498e2ef4/src/exchange/mixins/Trading.sol), [V2 order schema](https://github.com/Polymarket/ctf-exchange-v2/blob/ccc0596074f4dfd62c944fbca4de252893b82b4b/src/exchange/libraries/Structs.sol).

V1's restricted `taker` is checked against `msg.sender`, which is an operator on its execution entry points. Do not silently reinterpret it as the maker of the other matched order. A direct-fill Asce quote can bind the actual filling customer; a relayer requires separate authenticated customer identity.

V2 has user self-pause with a default delay of 100 blocks. Pausing/unpausing is not an immediate permanent cancellation of one order. The audit explicitly identifies cancellation and stale-order rejection as relying on operator/offchain behavior. Asce should enforce its observation cutoff and signed deadline regardless of a backend's decision. [User pause](https://github.com/Polymarket/ctf-exchange-v2/blob/ccc0596074f4dfd62c944fbca4de252893b82b4b/src/exchange/mixins/UserPausable.sol), [Quantstamp report, operational considerations](https://github.com/Polymarket/ctf-exchange-v2/blob/ccc0596074f4dfd62c944fbca4de252893b82b4b/audits/CTF%20Exchange%20V2%20-%20Quantstamp%20-%20March%202026.pdf)

V2 fees are collateral-denominated. BUY fees are extra cash; SELL fees are deducted from cash proceeds. Its default global cap is 500 bps. A configured cap of zero disables rate validation; it does **not** turn fees off. Asce's zero-fee MVP must reject nonzero fees rather than copy that configuration convention. Later fees should be bounded by each signed quote as well as protocol policy. [Fee implementation](https://github.com/Polymarket/ctf-exchange-v2/blob/ccc0596074f4dfd62c944fbca4de252893b82b4b/src/exchange/mixins/Fees.sol)

Both price and fill accounting use base-unit integers. V2 computes proportional taking amounts with floor division. Asce should begin with full fills; later partial fills should use defined integral lots with exact payout/cash amounts, or a separately derived cumulative rounding policy. Repeatedly flooring each fragment can give a different total from filling once. A simple arithmetic example is `floor(1×2/3)` repeated three times = 0, whereas `floor(3×2/3)` = 2. This is a design warning, not a demonstrated production exploit. [V2 calculator](https://github.com/Polymarket/ctf-exchange-v2/blob/ccc0596074f4dfd62c944fbca4de252893b82b4b/src/exchange/libraries/CalculatorHelper.sol)

## 8. Collateral and terminal redemption

Current documentation describes pUSD. In the pinned V2 source, the traded collateral and collateral used to derive CTF IDs are distinct constructor parameters. `CtfCollateralAdapter` converts pUSD to USDC.e for legacy CTF split operations and converts released USDC.e back to pUSD for merge/redemption. Consequently, derive position IDs from `ctfCollateral`, not automatically from the displayed trading currency. [Assets configuration](https://github.com/Polymarket/ctf-exchange-v2/blob/ccc0596074f4dfd62c944fbca4de252893b82b4b/src/exchange/mixins/Assets.sol), [collateral adapter](https://github.com/Polymarket/ctf-exchange-v2/blob/ccc0596074f4dfd62c944fbca4de252893b82b4b/src/adapters/CtfCollateralAdapter.sol)

The public position guide describes direct pUSD token-ID derivation; that description should not override a particular deployment's configured collateral identity. The contracts page and the pinned README also list different collateral-adapter addresses. This review does not resolve those differences by claiming the checkout equals every live deployment. Direct integration requires reading the actual deployment's configuration and verifying its bytecode. Asce's local MVP avoids this ambiguity by using one mock USDC token for both trading and CTF backing. [Position guide](https://docs.polymarket.com/trading/positions/how-positions-work), [contract catalogue](https://docs.polymarket.com/resources/contracts), [pinned README](https://github.com/Polymarket/ctf-exchange-v2/blob/ccc0596074f4dfd62c944fbca4de252893b82b4b/README.md)

The inspected UMA adapter maps ordinary binary answers to `[1,0]` or `[0,1]`, and its UNKNOWN answer to `[1,1]` (half payout each). Asce's accepted policy instead uses a dedicated INVALID slot, excluded from buyer cover masks, with zero buyer payout. CTF must still receive a positive-sum vector: resolve INVALID as `[0,0,0,0,0,1]`, not an all-zero vector. The holder of INVALID residual claims receives their backing. With an oracle delay/dispute, retain the prepared condition and funded claims until the committed finalization/timeout policy produces a valid result.

## 9. What the capital saving actually is

For buyer obligations `f_i[k]` on this common domain:

```text
L[k] = sum_i f_i[k]
M    = max_k L[k]
```

Split `M` into atomic claims, deliver buyer `i` its `f_i[k]` units, and retain `M-L[k]` in each slot. No state has a negative residual; total claim payout in every state is exactly the funded `M`. Our [existing local CTF control](ctf/state-clearing-baseline-results.json) realizes 26,000 in summed cover caps with 11,000 backing.

Native shared CTF inventory therefore already reaches the deterministic collateral minimum for nonnegative finite buyer payoffs. The exchange does not need a second margin ledger merely to establish this backing. Maker capital accounting and inventory planning can be offchain views; the onchain executor must deliver only assets actually held or funded through supported CTF conversions. Promised but unminted future claims would introduce a different ledger and new solvency obligations.

Premiums are trade cashflows. A 1,000 premium does not fully fund a 10,000 claim by itself: existing inventory or another authorized capital contribution must supply the difference. Closing releases cash only when actual complete-set inventory can be merged, or when the buyer sells claims for an agreed price. “Reduced maximum liability” is not permission to transfer backing out of CTF while externally held claims remain outstanding.

Polymarket negative risk already uses deterministic one-winner relationships. Its current Combos documentation also describes decomposition, complementary merging and collateral return. Those are relevant precedents; “Polymarket is only isolated YES/NO pools” is an incorrect platform-wide comparison. The binary V2 limitation above concerns this particular matcher, not every current Polymarket product. A complete comparison with Combos modules remains separate work. [Negative risk](https://docs.polymarket.com/concepts/negative-risk), [Combo collateral return](https://docs.polymarket.com/trading/combos/collateral-return)

## 10. Audit lessons to carry into Asce tests

The bundled Cantina report records five medium and six low findings, all reported fixed, plus twenty informational findings. Quantstamp records one medium, three low and one informational finding, all reported fixed at fix review. Their reviewed revisions differ from our checkout; audits do not automatically certify Asce changes. [Cantina report](https://github.com/Polymarket/ctf-exchange-v2/blob/ccc0596074f4dfd62c944fbca4de252893b82b4b/audits/CTF%20Exchange%20V2%20-%20Cantina%20-%20March%202026.pdf), [Quantstamp report](https://github.com/Polymarket/ctf-exchange-v2/blob/ccc0596074f4dfd62c944fbca4de252893b82b4b/audits/CTF%20Exchange%20V2%20-%20Quantstamp%20-%20March%202026.pdf)

The useful regression targets are:

1. **Actual execution determines consumption:** maker fragments cannot debit a customer more than authorized, credit too little, or consume a different order amount in storage. Price improvement must update consumed quantities consistently.
2. **Every token belongs to the declared condition:** another event's token, wrong mask, malformed subset, token ID zero or incorrect collateral cannot satisfy a route.
3. **Only this execution's assets fund its outputs:** donated/stranded exchange balances cannot be mistaken for customer proceeds or refunded to an unrelated filler. Account for balance changes and explicit residual ownership per supported asset.
4. **Fees correspond to executed cash:** empty/zero-fill plans cannot charge fees; any later fee cap applies to actual execution and signed customer limits.
5. **Callbacks cannot reuse authorization:** block nested execution; test receiver callbacks, ERC-1271 policy changes, cancellations and rollback. V2's operator restriction is not a reentrancy defense that transfers automatically to a public executor.
6. **Integer limits are enforced onchain:** cap amounts before multiplication and before packed storage writes. Do not import unchecked or packed assembly on the assumption that offchain validation will bound inputs.

Also test cutoff/resolution races, full rollback on a failing route leg, direct caller identity versus relayer identity, and redemption in every normal/INVALID state. A failed fill due to absent assets is order rejection; it is not liquidation of a previously funded cover.

## 11. Local test and gas evidence

Ran the unchanged upstream V2 code with its pinned submodules:

```sh
FOUNDRY_PROFILE=ci forge test --offline
```

Foundry 1.8.1, Solidity 0.8.34, Osaka EVM target, optimizer enabled with 1,000,000 runs, isolated tests and FFI disabled; **265 tests passed across 22 suites, zero failures or skips**. Includes the three matching paths, multi-maker balance accounting, token checks, signature/preapproval behavior, fee checks and collateral adapters. Compiler warnings were from dependency modifier deprecation and one test mutability suggestion. These are upstream tests, not an independent audit or evidence that a new Asce executor is safe.

The run generated these marked-call gas observations for direct CTF, excluding test setup and transaction intrinsic gas:

| Makers in one call | Existing-token match | Mint | Merge |
|---|---:|---:|---:|
| 1 | 198,601 | 289,257 | 265,122 |
| 5 | 391,989 | 479,166 | 464,663 |
| 10 | 633,965 | 728,158 | 721,308 |
| 20 | 1,119,005 | 1,228,004 | 1,236,390 |

These differ from committed historical snapshots and README comparison numbers. The [evidence record](polymarket-exchange-review-results.json) retains both generated and committed values. Treat them as a local benchmark of Polymarket's binary code, not Asce categorical-route estimates. Batching funded conversions is worth measuring; cloning extensive assembly optimization before correctness is established is not justified.

## 12. Licensing and practical reuse

V1 is MIT licensed. V2 uses Business Source License 1.1, with no additional use grant and a stated change date of 27 March 2030. Its current terms permit non-production use; copying V2 into a production Asce fork needs an applicable licensing basis. Researching the architecture and implementing Asce's own requirements does not justify presenting a copied V2 derivative as unrestricted MIT code. Keep provenance clear. [V1 license](https://github.com/Polymarket/ctf-exchange/blob/ed5c7708b7be3aa98bf5f0c6602b57cc498e2ef4/LICENSE.md), [V2 license](https://github.com/Polymarket/ctf-exchange-v2/blob/ccc0596074f4dfd62c944fbca4de252893b82b4b/LICENSE.md)

## 13. Recommended input to the forthcoming contract specification

Keep two Asce contracts plus native CTF and local mocks:

| Component | MVP responsibility |
|---|---|
| `AsceOracleAdapter` | Commit and recognize the approved observation/domain; prepare one common condition; enforce fixed cutoffs/finality/timeout; translate a mock observation into one normal or INVALID slot |
| `AsceExecutor` | Verify signed quotes, direct customer authority, deadlines/cancellation and asset identities; execute a bounded allowlist of transfers and CTF split/merge routes atomically; allocate residuals exactly |
| Native CTF | Own claim balances and backing; support deterministic conversion and terminal redemption |
| Mock USDC / mock source | Local funding and controlled final observations for tests |

An event/template approval record can live in the adapter; there is no need for a separate event contract. There is no per-cover registry, per-maker contract, custom collateral wrapper, general margin vault, AMM or onchain order book in this first profile. One maker means one quoting wallet in the demo; addresses are not hardcoded into the protocol.

The proposed quote binds the funding wallet, optional customer restriction, receiver policy, recognized condition, exact subset or basket commitment, offered/requested base-unit amounts, deadline, cancellation epoch and unique order salt. Its EIP-712 domain binds Asce's version, chain ID and executor address. Exact final fields belong in the contract specification. Cover identity and order identity remain separate. Every extra asset or cash contribution in a conversion route must be caller supplied or explicitly authorized; the executor is not allowed to infer consent from broad token approvals. Cutoffs apply to Asce execution; native CTF tokens remain externally transferable, so the adapter is not a universal transfer gate.

Implement in stages: oracle/condition and every-state redemption; signed full-fill existing-claim trades; funded categorical issuance and supported split/merge routes; then partial fills and atomic cover changes. Keep zero protocol fees and no price-triggered liquidation. Use the numerical CTF controls as the minimum expected behavior, and the audit lessons above as required adversarial tests.

**Assessment:** the common CTF settlement and exchange layout are proven precedents. Asce's work is canonical scalar domains, cover construction and execution across compatible liquidity, plus useful maker inventory tooling. The first finite-state prototype should demonstrate that workflow; it should not claim to invent complete-set backing or offer a smaller collateral floor than the equivalent shared CTF construction.
