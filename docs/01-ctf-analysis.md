# Existing-system analysis: CTF and Polymarket

Research date: 30 September 2026. Version boundaries matter: the local EVM evidence uses published Gnosis CTF 1.0.3. Polymarket's older exchange repository is archived; V2 was inspected separately. No current deployment bytecode was verified.

Follow-up, 1 October 2026: [the pinned Polymarket exchange review](../research/polymarket-exchange-review-2026-10-01.md) examines order authorization, cancellation, fees, binary matching limits, collateral adapters and published audit findings. Its local upstream V2 run passed 265 tests. It also explains precisely what one shared settlement condition means and which exchange features Asce should adopt.

Scope clarification later on 1 October: the user requires a broad event supporting different payoff types, rather than treating a fixed categorical domain as the event itself. The [Scalar-AMM payoff review](../research/scalar-payoff-library-review-2026-10-01.md) examines the existing continuous-curve library, portfolio-extrema work still needed, and a shared fractional CTF interpolation basis. Fixed buckets remain a valid restricted control; the broader contract architecture is not yet settled.

## Conditions, collections and claims

A condition binds an oracle address, question identifier and slot count. Its ID is `keccak256(abi.encodePacked(oracle, questionId, outcomeSlotCount))`. Preparation initializes 2–256 slots; the identifier does not itself define the real-world question. The application must commit to those terms. The reporting oracle supplies nonnegative numerators with positive sum; normalizing by that sum gives the resolution weights. Reporting final payouts is one-way in the inspected contract. CTF accepts the oracle's answer; it does not verify external truth or implement its dispute policy. [CTF implementation](https://raw.githubusercontent.com/gnosis/conditional-tokens-contracts/master/contracts/ConditionalTokens.sol)

A collection selects a nonempty proper slot subset, encoded by an index mask. A position binds that collection to an ERC-20 collateral asset and uses the resulting ID as an ERC-1155 token ID. Collection IDs use CTF's curve-based helper, including parent collection composition; they are not simple application hashes. [Identifier helpers](https://raw.githubusercontent.com/gnosis/conditional-tokens-contracts/master/contracts/CTHelpers.sol)

On one categorical condition, let `e_k` pay one collateral unit in state `k`. A mask `S` represents `sum(k in S) e_k`. The full state set is collateral, rather than another subset token. This is the natural basis for Asce's fixed domain.

## Split, merge, redemption and complete sets

`splitPosition` consumes collateral for a full partition, or burns an existing parent/union position when subdividing it. Partition members must be disjoint. `mergePositions` reverses this construction. `redeemPositions` burns resolved balances for collateral or a parent position. A complete partition has a constant combined unit payout. Partial splits need no new collateral. Native transfers move existing claims without reminting them. [Developer guide](https://conditional-tokens.readthedocs.io/en/latest/developer-guide.html)

For example, on states `[low, middle, high, INVALID]`, split 100 collateral into `[low, middle, high|INVALID]`. Low and middle buyers can receive separate 100-cap claims from that one issuance. Selling them is not two independent 100-collateral mint operations.

For a fractional resolution, a subset balance `b` redeems as `floor(b * sum(selected numerators) / denominator)`. Integer rounding may leave dust. Our MVP's one-hot resolution makes redemption exact in collateral base units. A specified INVALID slot is preferable to silently assuming a 50/50 binary refund: these create different buyer promises.

## Scalar and combinatorial positions

CTF's documentation also describes a two-slot scalar condition whose final weights interpolate between endpoints. This already supplies normalized complementary scalar exposure. It does not mean two tokens span every capped ramp or arbitrary nonlinear curve over that scalar. [Scalar example](https://conditional-tokens.readthedocs.io/en/latest/developer-guide.html#a-scalar-example)

Composing collections across conditions produces conjunctive/product claims, with nested split/merge paths. It can represent combinatorial exposure. It does not automatically discover that two separately prepared predicates share one physical observation, or exclude inconsistent combinations. Those relationships require a correct common condition or additional adapter semantics. Our first version uses one condition, zero parent collection and no cross-event combinatorics.

## The decisive capital comparison: arbitrary finite payoff vectors

The following is an independent construction, not a claim that CTF exposes an automatic portfolio-margin method.

For any nonnegative buyer vectors `f_i[k]` with integer amounts on the same categorical condition, define:

\[
L_k=\sum_i f_i[k],\quad M=\max_k L_k.
\]

Split `M` collateral into `M` units of every atomic claim `e_k`. Give buyer `i` exactly `f_i[k]` units of `e_k`, retaining `M-L_k` units per state. Each recipient has a nonnegative balance, and:

\[
\sum_i f_i[k]+(M-L_k)=M\quad\text{in every state.}
\]

Each buyer's basket delivers its full promised curve. The maker's basket delivers its residual equity. All buyers may hold their claims externally immediately. Settlement needs exactly `M` collateral, matching the lower bound in [the proof](03-math.md).

Thus **immediately creating external CTF claims does not necessarily consume the saving**. Independent conditions, individually prefunded minting and unmerged complete sets can consume it. Shared atomic inventory does not. Unequal payouts and overlapping covers also fit this construction; overlaps simply increase the amount needed in the overlapping state.

The new [EVM baseline](../research/ctf/state-clearing-baseline-results.json) executes this construction for three unequal covers: summed caps 26,000 USDC, CTF backing 11,000. It also buys back half of C, merges a 500 complete set and settles all six outcomes before and after the close. This is a prefunded mechanics test using separate harness transfers, not a secure atomic trading integration. The older runner already tests a limited atomic buyer-funded issuance route.

## What CTF does and does not solve

| Requirement | Already supplied by native CTF | Application work |
|---|---|---|
| Shared finite claims and subsets | Outcome tokens and subset collections | Canonical domain and observation terms |
| Deterministic complete-set backing | Split/merge and residual inventory | Construct and allocate the correct basket |
| Unequal custom payoff vectors | Replicable as atomic baskets | Builder, basket handling, optional wrapper |
| Oracle resolution | Authorized final reporting interface | Data selection, verification, challenges, timeout |
| Settlement | Redemption | Correct source-to-slot mapping and UX |
| Account `min(c+p)` checks | No signed account ledger | Internal ledger if that representation is chosen |
| Automatic extraction of offsets | Structural conversions, not general discovery | Inventory normalization, routing/plan generation |
| Maker quotes and premium formation | None | Pricing, signatures, execution and fees |

An automatic account service can be useful even where the optimum is attainable natively. Its advantage must be convenience, supported operations, computation or transaction cost; it is not a lower cash solvency floor for these finite vectors.

## Polymarket CTF Exchange: precise order meaning

The inspected legacy `Trading.sol` distinguishes three matching routes. A buy versus sell on the same token transfers claims for cash (`COMPLEMENTARY` in that source's naming). Buys on opposite binary tokens can jointly fund issuance (`MINT`). Opposite sells can consume both tokens and release backing (`MERGE`). Do not confuse the enum name with a requirement that every opposite-side order uses opposite tokens. Matching and fill accounting are exchange work; final claim redemption remains CTF work. [Legacy trading source](https://raw.githubusercontent.com/Polymarket/ctf-exchange/main/src/exchange/mixins/Trading.sol)

The legacy repository was archived on 11 May 2026 and points integrators to V2. [Repository notice](https://github.com/Polymarket/ctf-exchange)

V2 retains those match classes, batches mint/merge work, and validates orders against the two native IDs for the supplied condition. Its inspected `Trading.sol` is a binary-token matcher, not a general `n`-state payoff-vector account engine. That is an application-level restriction, not a restriction that makes Gnosis CTF incapable of categorical baskets. [V2 trading source](https://raw.githubusercontent.com/Polymarket/ctf-exchange-v2/main/src/exchange/mixins/Trading.sol)

Current Polymarket documentation describes positions backed by pUSD; this research's USDC choice is Asce's proposed asset, not a statement that current Polymarket uses raw USDC identically. [Position documentation](https://docs.polymarket.com/trading/positions/how-positions-work)

## Negative risk and current collateral return

Polymarket negative risk links outcomes where one winner is allowed: a NO claim can convert into YES claims on the other outcomes. This is established contractual capital efficiency. It relies on the declared event's rules, rather than historical correlation. [Negative-risk documentation](https://docs.polymarket.com/concepts/negative-risk)

Polymarket also currently documents decomposing compatible Combo positions, merging complementary parts into collateral and retaining residual exposure. Plans execute in bounded chunks. This is broader than inspecting the old NegRiskAdapter alone. The documentation does not establish support for every arbitrary Asce curve or exact account-wide minimum, but it invalidates a blanket assertion that Polymarket has no portfolio-related collateral extraction. [Collateral return](https://docs.polymarket.com/trading/combos/collateral-return)

The repository's [earlier NegRisk comparison](../research/negrisk-case.md) is a restricted source-level comparison for a pinned adapter and market layout. Its claims of universal separation or an unbounded refinement advantage must not be reused as platform-wide claims. That document's absent v1 runner was not reproduced, and the present MVP forbids post-trade state refinements anyway.

## Architecture implications

Choose a common domain first. CTF cannot infer semantic equivalence from titles, and independently initialized questions are not one condition merely because one adapter resolves them.

Keep Architecture A as the control and simplest first implementation. If Architecture B is evaluated, compare identical payoffs, finality, failure states, prices, fees, execution grouping and withdrawal rights. Do not compare B to the deliberately weaker design of an unrelated binary pool per cover.
