# Mathematical model and solvency proof

## 1. Exact cash-only funding floor

On a finite immutable nonempty domain, let `p_k` be an account's signed remaining payoff, and `c` its cash component. Settlement entitlement is `W_k=c+p_k`.

\[
W_k\geq0\ \forall k\quad\Longleftrightarrow\quad c\geq-\min_k p_k.
\]

If separately imposing `c≥0`, minimum cash is:

\[
R(p)=\max(0,-\min_k p_k)=\max_k(-p_k)_+.
\]

For pure shorts `p=−L`, with `L≥0`, this becomes `R=max L`. Necessity follows by taking the maximizing state; sufficiency follows because every state's liability is at most `R`. The claim is relative to the complete specified contractual domain, not a promise that a flawed oracle/state definition matches reality.

For the unrestricted signed ledger, the minimum allowed cash component is `−min p`, potentially negative. It is an accounting component, not a negative physical vault asset. Actual vault assets remain nonnegative because all account entitlements reconcile to those assets.

## 2. Deterministic saving

For nonnegative short covers `L_i`:

\[
R_{joint}=\max_k\sum_i L_{i,k}\leq\sum_i\max_k L_{i,k}=R_{separate}.
\]

Equality holds when a state simultaneously attains all individual maxima (including ties); otherwise it is strict. Zero-probability assumptions provide no additional discount. A cancellation state with joint refunds can be the maximum even when normal cover states exclude one another.

For `m` disjoint equal-cap `K` covers, separate backing is `mK` and joint backing `K`. Saving is `1−1/m`. That comparison is against separate funding, not against a shared CTF complete set, which already attains `K`.

For any proposed nonnegative new liability `f`, the incremental reserve is:

\[
\Delta R=\max_k(L_k+f_k)-\max_k L_k\in[0,\max_k f_k].
\]

It can be zero without the new contract being economically free: state capacity was already funded. Its premium and expected loss remain separate quantities. Pairwise margin discounts cannot be summed; the maximum must be taken on the whole portfolio.

## 3. Cashflow-sensitive admissibility

Let `c_0,p_0` be current accounting state. After internal net consideration `t`, fee `F`, and exposure change `Δp`, but before external funding:

\[
g_{candidate}=c_0+t-F+\min_k(p_{0,k}+\Delta p_k).
\]

Additional deposit `d` and withdrawal `x` are admissible iff:

\[
d-x\geq-g_{candidate}.
\]

Premiums appear only in `t`. They are not subtracted from `p` and again from required cash. The price of a cover can be far below its cap.

For lifecycle checkpoints `t=0…T`, signed payoff `p_t`, and cumulative net received cashflow `π_t` including fees, the minimum starting personal capital with immediately reusable released funds is:

\[
D_{peak}=\max\left(0,\max_t\{-\min p_t-\pi_t\}\right).
\]

Include every standalone execution checkpoint. A complete atomic package has one final checkpoint; it does not have independently executable intermediate legs. This explains the difference between final backing, peak external capital and sum of deposits. The latter may count recycled funds repeatedly.

## 4. Inductive safety proof

Base state: empty accounts, zero escrow, zero entitlements.

Assume `W_a[k]≥0` for every account/state and `sum W_a[k]=B`. Then:

1. Depositing `d` adds `d` to one entitlement and custody. Nonnegativity and conservation persist.
2. A conserving trade has zero aggregate `Δq` per cover and zero aggregate cash change, with fees credited to recipients. It leaves total entitlement unchanged. Checking each changed account suffices; unchanged accounts keep their old nonnegative entitlements.
3. A withdrawal `x≤min W_a` subtracts `x` from one entitlement and custody. Neither invariant fails.
4. Final resolution selects an allowed `k*`. Every `W_a[k*]` was already nonnegative and their sum equals custody. A mere provisional report changes no funded state support.
5. Materializing or paying an entitlement removes exactly that entitlement once. Paying `s=W_a[k*]` reduces custody by `s`; remaining entitlements still sum to it. Any order of valid account claims therefore succeeds.

By induction, no sequence of such valid actions creates underfunding. This proof assumes authorization, exact arithmetic, actual transfer receipts, complete domains, callback isolation and correct transition implementation. It does not prove those implementation conditions from a Python test.

## 5. Eligibility of long claims

Subtract a long's future receipt from liability only when its right is enforceable in the same clearing system and settlement domain and cannot disappear without an atomic account recheck. It must not also be credited as marked cash. An external CTF long needs custody and a precisely validated asset-payout vector. An external wallet balance, statistical hedge or expected future purchase is insufficient.

Immediate settlement must use **net entitlement**, not force gross shorts to pay first and only later credit longs. The latter would invent a liquidity requirement absent from this proof.

## 6. CTF reaches the same lower bound

For buyer vectors `f_i≥0`, split `M=max_k sum_i f_i[k]` complete atomic sets, allocate `f_i[k]` to buyers and retain `M−sum_i f_i[k]`. This constructive allocation is feasible and settles exactly. Any lower cash backing fails in a state achieving `M`. Therefore an appropriately structured common CTF condition is optimal for this comparison.

A stronger observation applies to any cash-only funded internal ledger: its entitlements `W_a[k]` are nonnegative and sum to a constant `B`. Splitting `B` complete sets and allocating `W_a[k]` to each account tokenizes those **net entitlements** exactly. This does not mean each nominal position can be exported after its guaranteed floor was withdrawn; gross positions and net entitlement differ.

## 7. CTF custody inside Architecture B

If the internal vault holds base cash `B_v` and owned CTF claims with exact state payout `V_k`, the extended asset vector is `A_k=B_v+V_k`. Then require:

\[
W_a[k]\geq0,\qquad\sum_a W_a[k]=A_k\quad\forall k.
\]

Minting `m` complete sets changes `B_v` by `−m` and `V_k` by `+m` for every state: assets are unchanged. Exporting claim `F` changes vault assets by `−F_k` and the exporting account entitlement by `−F_k`. Both sides change exactly once. Recheck that account's residual entitlement. Retained complements are owned assets, not free base cash.

Example: maker/buyers total entitlements sum to `[100,100]`, with pure cash assets 100. Buyer holds `[100,0]`. Mint 100 complete sets, export its low-state claim, and retain `[0,100]`. Base cash becomes zero; remaining maker entitlement and vault asset both become `[0,100]`. Requiring another 100 from the maker here would double-fund the already backed liability. Treating the retained claim as 100 freely withdrawable cash would instead steal its backing.

## 8. Why export can require cash

A buyer owns `f=[100,150]`, withdraws its guaranteed floor 100, and has `c=−100`. Net entitlement is `[0,50]`. Exporting the full nominal `f` leaves `W=[−100,−100]` and must fail unless 100 is restored. Exporting the net entitlement `[0,50]` is a different claim and must be explicitly authorized. Removing a long hedge from a short writer has the analogous restriction.

There is no universal export penalty: an unencumbered prepaid long can be exported with no account deficit. There is no universal free export either.

## 9. Continuous scalar extension

For exact piecewise-linear portfolios on scalar `x`, use the union of their knots. On each open interval the aggregate is affine, so its extrema occur at endpoints or limits; separately check discontinuity values, one-sided limits, exceptional states and bounded tail behavior. This can compute an exact supremum without probability scenarios.

For finite buckets, a sufficient state map satisfies `map(x)=map(y) ⇒ f_j(x)=f_j(y)` for every admitted claim. Otherwise midpoint evaluation is unsafe. A conservative alternative is `max_k sup_{x in bucket k} L(x)`; summing each claim's separate within-bucket supremum is safe but loses netting and is not generally the exact portfolio supremum.

Individual per-position integer rounding can turn a linear portfolio into staircase functions. Checking only real-valued aggregate knots is then not necessarily exact for a signed portfolio. An extension must enumerate relevant integer/rounding transitions or prove a conservative error bound. The MVP avoids this problem with explicitly integer per-state payouts and exact lots.
