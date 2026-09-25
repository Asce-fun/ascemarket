# AsceMarket v2 — generic cover kernel

Status: normative design specification with a [finite-state reference implementation](model_v2/README.md), not a deployed or audited engine. It replaces the earlier v2 draft. The earlier Python model in `model/` has been removed. `model_v2/` implements the baseline graph verifier and simulated ledger; its README identifies unimplemented integration and extension capabilities.

Product definition: [AsceMarket](AsceMarket.md).

## 1. Purpose and scope

The kernel supports markets in reusable bounded covers. An account combines cash and signed cover holdings into one remaining payout over all contractually permitted settlement histories. It accepts an operation only when authorization, exact accounting and full funding hold.

The architecture is generic across event domains. Market schemas describe what can happen; cover definitions describe payouts; a verifier computes the worst case of the combined account. A new cover using existing capabilities requires data, not a new accounting contract.

Generic does not mean arbitrary executable code. A cover and every account containing it must belong to an admitted verification class with finite resource bounds. Additional classes can extend the architecture without altering existing market semantics.

The kernel does not set prices, guarantee counterparties, infer probabilities or net unrelated markets. It does not assume quoted market value is collateral.

## 2. Core objects

| Object | Definition |
|---|---|
| Market | Immutable observation process, settlement asset, state/transition schema, finality rules, exception policy and verifier version |
| State | Sufficient recorded information to evaluate supported payouts and determine permitted continuations |
| History `h` | A complete permitted settlement history, including normal completion or an exceptional terminal branch |
| Funding support `Ω_e` | Nonempty set of histories still contractually possible at market epoch `e` |
| Display support | Optional provisional view; never authoritative for funding |
| Cover `j` | Immutable bounded integer payout function `φ_j(h)` per cover lot |
| Account `i` | Signed cash component `c_i`, signed integer lot holdings `q_ij`, revision and audit history |
| Escrow `C` | Settlement-token funds backing outstanding account entitlements |
| Fact | Authorized, contractually final constraint on permitted histories |
| Report | Source information that may still be provisional or corrected |
| Epoch | Market version for finality, suspension and quote invalidation events |

A history includes the ordering of contractual finalization and cancellation where that ordering affects payout. An eventual physical result alone need not determine the settlement amount.

## 3. Immutable market definition

Before opening, a market binds:

1. Settlement asset, token precision and supported transfer behavior.
2. Observations, units, source identifiers, authoritative clock and measurement rules.
3. State domains, permitted transitions and initial states.
4. Checkpoint/event structure, horizon and permitted cover parameter domains.
5. Finality mode, authorized reporters/finalizers, challenges, deadlines and missing-data handling.
6. Cancellation, source failure, overflow, conflicting-report and noncompletion outcomes.
7. Cover-language, verifier and canonical-encoding versions.
8. Arithmetic, lot-size, resource and transaction limits.
9. Suspension, reopening and order-invalidation policy.
10. Cover admission authority and rules, account authorization and any declared administrative powers.

The market ID commits to these definitions. Economic meaning cannot change after opening. A software upgrade preserving the same semantics requires equivalence validation; a changed observation, payout or finality promise belongs to a new market.

A market may contain a structured state such as `(home_goals, away_goals)`, or a bounded augmented state carrying event order. It is one explicitly modeled joint process, not an invitation to combine unrelated exposures without modeling their joint possibilities.

### 3.1 State sufficiency and out-of-domain data

If two physical histories map to the same modeled state/history, every admitted payout and continuation rule must treat them identically. Otherwise the encoding is insufficient.

A score bucket meaning “7 or more” cannot support exact home-win settlement when it merges 8–7, 7–8 and 8–8. A checkpoint score pair cannot reveal who scored first inside the interval.

Use sufficient state, restrict the admitted covers, or define an explicit overflow terminal outcome with its own funded payout rules. Never silently clamp a value while continuing to claim exact settlement on the unclamped event.

Observed data outside the domain follows the published exception policy. It must not cause an undefined evaluator or an empty funding support.

## 4. Cover language and admission

A canonical cover definition contains:

- Market ID, language version and required verifier capabilities.
- Explicit observation dependencies and fixed time/checkpoint identifiers.
- A bounded payout expression per lot.
- Resolution/finalization condition.
- Payouts for every reachable exceptional branch.
- Canonical encoding, identity hash, lot denomination and complexity metadata.

Supported expression families can include constants, checkpoint tables, threshold/range predicates, capped ramps, adjacent-state change tables, event occurrence, bounded accumulators and finite-state conditions. Names such as “next scorer” are interface labels; they must compile to observable, verified rules.

The mandatory baseline verifier supports a finite layered state graph with node and adjacent-edge payouts. More complex conditions are supported only if they compile into that graph within limits, or through a separately admitted verifier class.

Combinations use a common market state space. Arbitrary products, Boolean nesting or distant-time dependencies are not implicitly admitted merely because their individual pieces are supported. State augmentation can make a dependency local, but its full resource cost is counted.

### 4.1 Admission requirements

The engine checks that a new cover:

1. Uses available observations and immutable market rules.
2. Has a total deterministic payout on every permitted normal and exceptional history.
3. Is bounded and integer-valued per executable lot.
4. Compiles into the market's supported verification class.
5. Meets resource and coefficient limits.
6. Does not alter existing covers, states or transition meanings.

Admitting an account update additionally checks the complexity of the whole resulting account. Per-cover validity is insufficient.

Covers can be listed after opening if the market's admission policy permits it and their definitions fit the precommitted schema. No listing can introduce missing historical information or new exception branches. Resolved covers cannot be newly issued through ordinary trading.

Relative user requests become fixed identifiers and time bounds before signing. “Next ten minutes” must not move between quote and execution. Reject and requote if the requested window no longer applies.

## 5. Exact arithmetic

Settlement amounts are integers in the token's smallest unit. Cover quantities are signed integer lots; a lot may represent a declared fractional economic exposure. Prices are exact total consideration for the executable lot quantity.

For every admitted cover and supported state, `φ_j(h)` is an integer. Ramps with fractional intermediate values must either use admissible payout/lot parameters or compile to an explicitly defined integer payout table. Any discretization error belongs in the preview and immutable definition.

There is no floating-point or unspecified rounding in kernel evaluation. Display formatting never changes execution amounts. Independent rounding of account balances is forbidden because it can break conservation.

A percentage reduction is executable only if the required cover lots and cash-component transfer are exactly representable. Otherwise return an executable alternative for explicit approval or reject; never silently round the legs independently.

All products, sums and intermediate recurrence values use checked bounds. Limits cover negative cash, signed holdings, batch accumulation and intermediate cancellation terms—not just final nonnegative payouts. An overflow or exceeded budget rejects the operation without mutation. Admission must also ensure that later cover resolution and lazy cash materialization fit the arithmetic bounds. The reference implementation uses a conservative absolute factor budget; a small net payout alone does not establish safe intermediate arithmetic.

## 6. Accounts and invariants

For account `i` and history `h`:

```
W_i(h) = c_i + Σ_j q_ij × φ_j(h)
```

`c_i` is a signed accounting component, not a separately withdrawable wallet balance. It may be negative after withdrawing a guaranteed floor. The account is funded when its combined `W_i` is nonnegative.

For every `h ∈ Ω_e`:

```
W_i(h) ≥ 0                 for every outstanding account
Σ_i W_i(h) = C             conservation of remaining escrow
```

Accounts start empty. Cover quantities are created/transferred in zero-sum batches; premiums and fees are zero-sum cash-component transfers. Deposits and withdrawals change account entitlement and escrow equally. These local checks establish conservation inductively; global reconciliation remains required for audits and reference tests.

Fees are credited to explicit recipient accounts. Passive receipt of a configured fee does not authorize spending that recipient's existing position.

For a valid account:

```
available_to_withdraw = min_{h ∈ Ω_e} W_i(h)
```

Withdrawal of `d` subtracts `d` from `c_i` and `C`. Negative cash does not itself indicate insolvency, and positive cash is not itself permission to withdraw.

After a proposed exposure/consideration/fee change, but before external funding, let the candidate entitlement be `V_i`:

```
minimum_deposit = max(0, −min V_i)
maximum_withdrawal_without_deposit = max(0, min V_i)
```

Every actual external transfer is explicitly authorized. The kernel never silently takes extra wallet money.

Trade history is separate from holdings. For account cash-history reporting, deposits minus withdrawals provide a profit basis only when ownership and transfers are accounted for consistently. Full account ownership changes must carry or explicitly reset the reporting basis; they do not manufacture profit.

## 7. Worst-case verification

### 7.1 Baseline factorization

A market uses a finite layered directed acyclic graph. At layer `t`, state `v` contains sufficient information for future transitions and payouts. All valid settlement paths are represented, including cancellation, failure and overflow branches. Termination can be padded with absorbing states if the evaluator requires equal path lengths.

For an account, compile its combined payout into:

```
W_i(path) = c_i + Σ_t U_it(v_t) + Σ_t E_it(v_t, v_{t+1})
```

Each payout is attributed exactly once. `U` and `E` aggregate signed holdings, so the verifier finds the minimum of the complete account, not the sum of individual cover minima.

The compiler must establish that this factorization equals the canonical cover evaluation on every permitted path. A dependency needing extra memory must be represented in the state. A plugin cannot hide path dependencies outside this model.

### 7.2 Backward recurrence

For states that can reach an allowed terminal:

```
D_T(v) = U_iT(v)
D_t(v) = U_it(v) + min_{w: allowed(v,w)} [E_it(v,w) + D_{t+1}(w)]
minimum_i = c_i + min_{v: allowed initial state} D_0(v)
```

States with no valid terminal continuation are unreachable, not zero-cost paths. Implement reachability separately or with a safe sentinel outside monetary arithmetic. If no terminal path remains, reject the fact/state transition and enter the declared conflict procedure; never return unlimited withdrawable funds.

Final facts prune the graph. The evaluator retains all already determined payout contributions. It may start from a confirmed prefix only after including prefix payouts and the boundary-crossing edge contribution exactly once. Out-of-order facts must constrain the whole relevant graph; do not assume that confirming the latest checkpoint also confirms earlier ones.

Exceptional paths participate in the same minimum. A separate exceptional evaluator is allowed only when taking the minimum over its complete branch set is proven equivalent.

### 7.3 Complexity and limits

General graph evaluation costs `O(V + E)` after payout-factor assembly. Account compilation cost depends on holdings, expressions and the factors they touch. Naive edge enumeration can be quadratic in states per adjacent layer.

An unrestricted transition with no pair-dependent edge cost permits a shared minimum. Monotone transitions with suitable separable costs may permit suffix minima. Arbitrary change-cover costs do not automatically have those optimizations.

Each deployment declares measured limits for states, edges, layers, cover expressions, nonzero holdings, accumulated coefficient magnitude, accounts per batch, order fills and total verification work. Account-local compilation must not scan unrelated accounts or the entire live cover catalogue. Admission must reserve sufficient work capacity for later fact processing and catalogue resolution as well as ordinary trades; otherwise an admitted market can become unable to finalize within its own limits.

Reject unsupported complexity before quoting and recheck at execution. No approximate search may claim an exact minimum. If an extension uses conservative bounds, it must expose that distinct guarantee and must not claim exact netting; the baseline exact engine rejects unsupported cases.

## 8. Extension contract

Extensions are verifier implementations, not arbitrary user-provided execution hooks. A registered capability must define:

- Observation and payout grammar, canonical serialization and dependency rules.
- Exact evaluation and minimum computation over its admitted support.
- Exceptional-outcome and finality behavior.
- Bounds, arithmetic and composability rules.
- Deterministic test fixtures and an independent correctness argument.

A market pins a verifier version. Several capabilities may coexist only when one verifier handles their joint account exposure correctly. Summing their separate minima is generally conservative rather than exact and cannot substitute silently for joint verification.

Adding a capability to new markets does not change old markets. Introducing a richer state representation must preserve all existing meanings or require a new market. There is no promise that every bounded program can be verified cheaply.

## 9. Reports, final facts and support

Maintain separate report state and funding state.

1. **Reported:** authenticated source data arrives; event-sensitive orders may be paused or invalidated immediately.
2. **Provisional:** display and scenario estimates may use it, but funding includes all contractually restorable histories.
3. **Final:** the declared finalization procedure makes its consequences irreversible for the contract; support narrows.

A final transition requires:

```
∅ ≠ Ω_{e+1} ⊆ Ω_e
```

For unchanged economic positions, narrowing support cannot lower the minimum. Every trade and withdrawal uses the funding support, not the provisional display support.

A report arriving late, out of order or contradicting previous final facts must follow a predeclared procedure. Conflicting reports pause affected operations; they cannot erase the whole support or silently restore excluded histories. Source authenticity and contract finality are distinct properties.

### 9.1 Finality modes

**Progressive finality:** checkpoints become irrevocable under the contract while the process continues. External corrections after that point do not amend past contractual facts. The source/contract divergence is explicit in the market rules.

**End finality:** reports remain revisable until the closing procedure. Both trading and withdrawal checks retain every history corrections can restore. A narrower display is not usable collateral. Its payout graph must retain the appropriate unresolved cancellation branches: a builder that automatically preserves checkpoint payouts implements progressive finality, not end finality. End-finality path payouts may require additional remembered state until terminal settlement.

Neither mode permits changing payout obligations after funds have been released without already funded backing for that change. A future correction-insurance mechanism would require a separately specified, funded liability; it is not implicit in this kernel.

Confirmation delays, challenge responses, source outages and finalization authority must be specified. No universal waiting period guarantees that external data will never change.

### 9.2 Epochs and execution ordering

Final facts, cancellation, material provisional updates, suspensions and reopening advance the applicable market/quote epoch. Transactions have a deterministic serialization order. A fill either executes under its authorized epoch or fails; it cannot partly precede and partly follow an update.

The epoch invalidates derived quotes and cached minima. Facts need not rewrite every account immediately. Reads and writes must evaluate or materialize against the current authoritative epoch. Account revisions track actual account changes separately.

## 10. Cancellation and cover finalization

“VOID” is an exceptional settlement policy, not a rollback command. The graph includes every permitted cancellation/failure timing and payout consequence from market creation.

The standard progressive policy is:

- If a cover has been contractually finalized before cancellation, its finalized payout survives.
- Otherwise it pays its immutable unresolved-cancellation amount for that branch.
- Cancellation never reverses historical premiums, fees, authorized withdrawals or finalized cover payments.

Finalization order is authoritative. An observation being known in ordinary outcomes does not itself finalize a cover. Any exceptional branch before finalization remains part of its funding requirement.

Other policies require explicit branch definitions and exact joint verification. Per-cover exceptional payouts can destroy an apparent normal-outcome offset; all examples and quotes must include them.

### 10.1 Resolved-cover accounting

A cover is resolved only when its payout equals the same integer `k` on every remaining contractual history, including exceptions. An explicit finalization operation can establish this under the immutable policy.

Economically, for each holder:

```
c_i' = c_i + q_ij × k
q_ij' = 0
```

This preserves `W_i` pointwise. It does not move tokens out of escrow. It replaces the cover entitlement with a cash-component amount once, preventing a duplicate payout later.

Global eager rewriting is not required. The registry records the immutable resolution and epoch; accounts may materialize lazily. Logical evaluation counts either the unresolved holding at its now-fixed value or the materialized cash, never both. Materialization is idempotent and tracked per account/cover or by an equivalent proven checkpoint mechanism. Trading in the resolved cover is disabled.

A holder's ability to withdraw the resolved amount depends on the entire account. Other obligations may still need that cash. A standalone winning buyer and a heavily offset account need not have the same withdrawable amount.

## 11. Atomic batches

A batch commits to deployment/network domain, market and verifier identities, epoch, deadline, replay protection, participants and exact changes:

- Cover lots transferred.
- Signed consideration cash flows.
- Fees and recipients.
- Deposits, withdrawals and destinations.
- Required account revisions or explicitly supported order authorizations.
- Any approved execution limits or partial-fill conditions.

Before mutation:

1. Validate market status, time windows, epoch, canonical data and limits.
2. Verify every required authorization; no participant can debit an unrelated account.
3. Materialize/evaluate resolved claims at the current epoch consistently.
4. Verify zero-sum changes per cover and zero-sum internal cash flows including fees.
5. Derive complete candidate accounts and escrow, including external transfers.
6. Verify token funding availability, exact transfer amounts and nonnegative escrow.
7. Compute each affected account's minimum over the complete funding support.
8. Require every candidate minimum to be nonnegative.
9. Commit all effects, revisions, order counters and receipt atomically.

Failure changes nothing. External token interactions must preserve this atomicity; unsupported fee-on-transfer or rebasing behavior is rejected or separately modeled. Internal accounting cannot treat an unreceived deposit as backing.

Trade execution never mutates the meaning of a cover or shrinks support. Fact/finalization transitions use their separate authority and rules.

## 12. Quote and order authorization

### Package quotes

All participants authorize exact package terms, account revisions, epoch and expiry. An account change or incompatible epoch invalidates the quote. Refreshing a quote requires fresh authorization unless an existing bounded authorization explicitly covers it.

### Standing orders

A standing order signs a bounded offer rather than an arbitrary future batch. It binds maker account, cover ID, side, lot size, total/minimum fill quantities, exact price rule, fee/debit bounds, expiry, epoch policy, nonce and cancellation authority. The taker authorizes its side of each fill.

The maker revision need not be fixed. Execution verifies that the generated fill is within the signed offer, tracks cumulative fills atomically and rechecks the maker's complete funded position at the current epoch. Whole-lot pricing prevents cumulative rounding exploits.

This is the explicit exception to requiring every participant to sign the exact assembled batch: the signed order authorizes only fills satisfying its precise constraints. A solver cannot append unrelated maker obligations, withdrawals or fees.

Default orders are bound to an exact quote epoch. Persistence across epochs is a separately supported, explicit bounded authorization—not the default. Market suspension and order cancellation take effect according to serialized state, with replay-safe nonces.

Unreserved orders can fail when capacity is consumed elsewhere. Any firm reservation mechanism must account for jointly executable commitments, not reserve the same free funds independently for several orders.

## 13. Exits and complete-position transfers

### Selected-cover close

Transfer selected holdings for a quoted consideration. It can remove offsets and require additional funding. Apply ordinary batch checks.

### Proportional complete-position sale

For seller payout `W = c + Σ q_j φ_j`, sell exactly representable fraction `a`, `0 ≤ a ≤ 1`, for proceeds `p`, with seller fee `f`.

Transfer `a q_j` lots and `a c` of the signed cash component to the buyer. Transfer `p` cash component from buyer to seller, and `f` from seller to treasury. The buyer explicitly authorizes the complete acquisition, including any negative cash component.

The seller then has:

```
W_after = (1 − a)W + p − f
```

If `p ≥ f`, the seller remains funded without a deposit and may withdraw `p − f`, leaving `(1 − a)W`. The buyer and fee recipient are also checked. The guarantee is conditional on exact representability, the current support and the stated fee/proceeds condition, not market liquidity.

Scaling holdings alone leaves `c` unchanged and has no equivalent guarantee. Example: `c = −100`, cover payout `(100, 200)`, so `W = (0, 100)`. Selling half the holdings for 25 gives `(-25, 25)` and is rejected without additional funding. A complete-profile sale also transfers half the cash component and avoids this error.

A full economic position sale is `a = 1`. It need not transfer wallet ownership, historical permissions or identity. Historical receipts remain intact. Any separate account-ownership transfer must define revocation of outstanding orders and reporting-basis changes.

## 14. Settlement and claims

Normal final settlement requires all payoff-relevant observations and exception choices to be final, or proof that every admitted outstanding cover has the same value on all remaining histories. Confirmation of the last timestamp alone is insufficient.

Market finalization disables trading and freezes the resolved payout rules. Each account can materialize resolved holdings and claim its remaining entitlement independently. Claiming subtracts exactly that amount from its entitlement and escrow, and records replay-safe claimed state atomically with transfer.

Previously withdrawn funds and resolved-cover credits are not paid again. Fees remain assigned to their recipient. Once every outstanding entitlement, including treasury entitlements, has been claimed, accounted escrow is zero. Accidental unsolicited token transfers are separately reconciled and do not silently alter promised payouts.

Noncompletion, missing observations and disputes must have a deterministic eventual resolution/failure procedure in the market rules. A safety-preserving indefinite pause is not a completed settlement policy.

## 15. Worked examples and mandatory expected behavior

Amounts below are economic units for readability; implementations encode exact token base units. Fees are zero unless stated. Cover buyers deposit their stated premiums and pay them to the maker, leaving zero buyer cash component and positive holdings.

### A. Rainfall: offsets plus progressive finalization

Cumulative rainfall is nondecreasing. Cover A pays 100 if noon rainfall is at least 10; cover B pays 100 if evening rainfall is below 10. Prices are 30 and 50.

Normal paths cannot pay both. For this example, unresolved covers pay zero on cancellation, and finalized payouts survive cancellation. Those exception rules also never make both covers pay 100.

Buyers contribute 80; maker contributes 20. Escrow is 100. Maker cash is 100 and holdings are `−A −B`, so maker payout is `100 − A − B` and is nonnegative on every history.

Before A is finalized, a cancellation branch may still give its buyer zero. The buyer cannot withdraw 100 just because a provisional report says noon rainfall was 12.

After A is contractually finalized at 100, every remaining history preserves that amount. The standalone A buyer can withdraw 100. B cannot win under the finalized monotonic facts and has zero cancellation payout. After the withdrawal, remaining escrow and all remaining account entitlements are zero; final bookkeeping may continue.

This is early payment of a resolved claim. It does not return an extra 100 to the maker.

### B. Football: partial protection and compatible obligations

From a contractually finalized 1–0 score, H pays 100 if away goals increase between the declared checkpoints. K pays 100 if the final score is exactly 1–0. The state encoding must distinguish all results needed by these covers; an ambiguous overflow bucket is not allowed to impersonate an exact score.

With nondecreasing finalized goal counts, H and K cannot both pay normally. If unresolved cancellation payouts are zero and finalized payments survive, the example's exceptional branches also preserve that bound. Prices of 35 and 25 imply maker contribution 40 to escrow 100.

A standalone H buyer can withdraw 100 only once H is finalized with that amount across every remaining exceptional branch. A home-win buyer adding H still has no protection against an equalizer outside the chosen window; the product's scenario table must expose that.

### C. Free-moving prices

Two covers paying 100 for the same price range at two different checkpoints can both pay. Their combined gross obligation is 200. Two disjoint ranges at the same checkpoint cannot both pay and have gross obligation 100, provided their exception rules do not create a larger joint payout.

For the baseline of independent checkpoint-only price claims with free transitions, there is no additional cross-time offset. A separately admitted path-dependent price cover may change the structure; the baseline conclusion is not a theorem about every possible price derivative.

### D. Provisional correction without withdrawal

Start with two permitted histories A and B. A provisional report favors A. A proposed seller position pays 100 in A and −100 in B. It must be rejected even if withdrawals are disabled. Restoring B after a report correction must never reveal an already accepted underfunded position.

### E. Fixed total does not determine a window

At the final checkpoint, cumulative count equals 2. At the earlier checkpoint it could have been 0, 1 or 2. A cover paying 100 if the earlier count was at least 1 remains unresolved until that observation or an equivalent sufficient fact is finalized.

### F. No false release from state deletion

An account pays `(0, 100, 0)` on low, middle and high. Removing low leaves `(100, 0)`, whose minimum is still zero. Support shrinking can raise the guaranteed floor, but need not do so.

## 16. Integration contracts

A deployment supplies deterministic interfaces for:

- Market configuration, capabilities and canonical cover admission.
- Authoritative epochs, facts, provisional reports and suspension state.
- Account revisions, canonical holdings, resolved credits and escrow reconciliation.
- Exact previews, minimum deposits, allowed withdrawals and payout witnesses/scenarios.
- Package/order signing, fill/cancel state and idempotent execution receipts.
- Fact finalization, cancellation, cover resolution and account claims.

Every preview identifies its market epoch, account revisions and canonical proposed changes. A fresh funding check still occurs at execution. APIs distinguish unsupported expression, excessive complexity, no quote, stale state, insufficient funds and unresolved observation.

The deployment must specify who can enforce these rules on escrow. Direct on-chain verification and a properly specified proof-verification design are possible implementations. An off-chain service holding data next to an escrow contract does not by itself enforce the invariant; trusting a sequencer or attestation must be an explicit deployment trust assumption. Placement and benchmark limits are implementation choices, not substitutes for the rules.

## 17. Verification and acceptance criteria

Build an independent exhaustive evaluator for small state spaces and compare the optimized verifier against it. Mathematical specifications and shared fixtures guide implementations; they do not prove that contracts, backend and screens cannot contain bugs.

Required checks include:

| Property | Required cases |
|---|---|
| Full funding | Random valid/invalid batches, signed cash, long/short holdings and all exception branches |
| Conservation | Recompute total entitlements and reconcile actual token movements after every operation |
| Exact minimum | Node/edge factors, augmented state, cancellations, unreachable states and signed quantities against exhaustive paths |
| Equivalent exposure | Different baskets with identical complete payouts have identical funding |
| Support finality | Only irreversible facts affect funding; minima do not decrease for unchanged positions when support narrows |
| Corrections | Revised provisional facts, out-of-order reports, conflicting final facts and empty-support rejection |
| State sufficiency | Overflow, event-order ambiguity, missing checkpoints and insufficient observation resolution |
| Cover lifecycle | Cancellation before/after finalization, lazy/eager materialization equivalence and no double credits |
| Atomicity | Failures leave balances, escrow, order counters, revisions and receipts uncommitted |
| Order authorization | Concurrent fills, cancellation races, epoch changes, cumulative size and unauthorized appended operations |
| Exits | Selected-leg funding needs, holdings-only counterexample, full-profile transfer including negative cash and representability |
| Arithmetic | Fractional ramp requests, lot constraints, split fills, percentage reductions and intermediate overflow |
| Settlement | Last timestamp without earlier facts, repeated claims, prior withdrawals, treasury balances and missing-data termination |
| Performance | Worst-case combined account and batch complexity at declared deployment limits |
| Product parity | Executable payouts, cash movements and exceptional terms match previews and scenario displays |

Record input/output fixtures for every worked example and failure case. No market is admitted with unspecified observation, finality, overflow, cancellation or arithmetic behavior. No verifier capability is activated merely because its cover expression can be parsed.

**The invariant is universal within a declared market: every accepted entitlement is funded across all remaining contractual histories. The language grows through verified definitions and capabilities, not exceptions to that invariant.**
