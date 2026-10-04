# Clearing-account accounting

All quantities are integers in collateral base units. One account belongs to one immutable event-expiry definition. A long bought cover has a nonnegative bounded payoff; the signed account quantity may be positive or negative. Prices are supplied inputs.

## Definitions

Let `Ω = {0,…,n−1}` contain every permitted terminal state, including exceptions. Cover `j` has per-lot vector `f_j ∈ Z_{≥0}^n`. Account `a` has signed lots `q_aj`, signed cash component `c_a`, and signed future payout:

\[
p_{a,k}=\sum_j q_{a,j}f_{j,k},\qquad W_{a,k}=c_a+p_{a,k}.
\]

`W` is the account's eventual net entitlement. `c` includes cash already contributed and transferred; it is not the account's current mark value. Define net contractual liability `ell_{a,k} = -p_{a,k}`. Negative liability is an eligible internal right, not a cash asset at its market price.

Before finality, use the complete funded support. A spot move does not eliminate terminal states for this event.

## Cash history without double counting

With no external claims or contingent assets, after all executed actions:

\[
c_a=D_a-X_a+P_a^{in}-P_a^{out}-F_a^{paid}+F_a^{received}+R_a.
\]

`D` is cumulative deposits; `X` withdrawals; `P` actual trade consideration; `F` fees; `R` payouts already materialized into cash. Once a payout enters `R`, remove its exposure term from `p`. Maker buybacks are `P_out`; the original premium remains in history. Settled payouts and close proceeds must not both erase the original trade.

For a cash-backed short portfolio with no materialization, premiums `π` and fees `F` give:

\[
D-X+\pi-F\geq\max_k L_k.
\]

At entry from zero, `D_min = max(0, max L − π + F)`. Premiums reduce the maker's personal contribution, **not the buyers' promised payouts or the total backing**. Future expected premiums and unpaid orders contribute zero.

## Free and locked collateral

The exact account check is:

\[
g_a=\min_k W_{a,k}=c_a+\min_k p_{a,k}\geq0.
\]

For a deliberately restricted cash-nonnegative account, define `R_a=max(0,−min p_a)`. Then `c_a ≥ R_a`. A pure underwriter with `p=−L` has locked cash `R=max L` and free cash `c−R`.

The general signed ledger permits negative `c` after withdrawing a guaranteed long-position floor. In that ledger **withdrawable funds are `g_a`**, not `c−max(0,−min p)`. The inequality `c ≥ −min p` is the correct general form. Calling negative `c` a token balance would be incorrect.

For the user's million-dollar example `p=[−4,−8,−2,+1,−5]m`, `c=10m`: required nonnegative cash is 8m, free collateral is 2m, and terminal entitlements are `[6,2,8,11,5]m`. This assumes the +1m is a funded internal claim within this settlement system. A wallet promise or an unsecured counterparty IOU does not qualify.

For the MVP, buyers prepay premium/fees and acquire only nonnegative exposure; no guaranteed-floor financing is needed. That preserves a straightforward no-liquidation UX. The broader signed ledger remains useful research and is already supported by `model_v2`.

## Trade admissibility

Given candidate changes `Δq`, actual internal cash transfer `t`, authorized deposit `d`, withdrawal `x`, and net paid fee `F`:

\[
c'_a=c_a+t_a+d_a-x_a-F_a,\quad p'_a=p_a+\sum_j\Delta q_{a,j}f_j.
\]

Accept only if `min(c'_a+p'_a)≥0`, authorization and domain checks pass, and cash/claim changes conserve value. A plain sale of `q f` gives seller `(+π,−q f)` and buyer `(−π,+q f)`; deposits fund any deficit. Fees credit an explicit recipient.

Before external funding, candidate entitlement `V` gives `required additional deposit=max(0,−min V)`. The maximum authorized withdrawal after funding is `min W`. Never silently take an additional deposit from a wallet to make a failed quote pass.

Check the entire final atomic batch. Check every independently executed partial fill as a separate batch. Beneficial later legs cannot back an earlier standalone fill. An atomic all-or-nothing basket may use its final combined offsets if no callback can observe or act on interim inconsistent state.

## Entry, exit, modifications and ownership

| Action | Accounting transition | Consequence |
|---|---|---|
| Deposit | `c += d`, event escrow `+=d` | Adds real capital |
| Withdraw | `c -= x`, escrow `-=x`; require `x≤g` | Cannot consume backing |
| Open | Paired signed claim changes and consideration | Recompute both participants |
| Secondary sale | Move long claim plus cash | Check residual seller account and buyer |
| Buyback / close | Reverse exposure at a new executed price | Cap release may be smaller than cash paid |
| Partial close | Reduce exact lots, or replace old vector with a declared smaller vector | Preserve previous premiums and realized cash |
| Payoff modification | Close old immutable terms and open new immutable terms atomically | Never mutate a held cover definition |
| Account transfer | Authorized novation of complete entitlements or paired claims/cash | Check both affected portfolios; offsets cannot be copied |
| Resolution | Select final state once | No new premium or cash creation |
| Claim | Pay `W[k*]`, remove entitlement exactly once | Order-independent settlement |

A closed long's realized PnL is close proceeds minus allocated entry premium and fees. A short's realized PnL is entry premium minus buyback and fees. Reporting needs a consistent lot-cost policy; it is not another margin credit. At final settlement with unchanged ownership, total PnL equals total withdrawals plus final claim minus deposits. Before expiry, unpaid residual payoff is contingent, not realized profit.

Closing a pure short can reduce `R` but still need a deposit if its buyback is expensive. Selling a long hedge can **increase** `R`. A guaranteed liquid exit at arbitrary market prices is not implied by terminal funding.

## Conservation and why long offsets are safe

For the cash-only internal ledger, outstanding claim quantities are zero-sum and internal cash transfers are zero-sum. Initially empty accounts and exact deposits imply:

\[
\forall k:\quad \sum_a W_{a,k}=B,
\]

where `B` is actual remaining event escrow. Check every account is nonnegative as well as this equation. Global zero-sum exposure alone is insufficient: `[−100,+100]` entitlements sum to zero but one account is insolvent.

All obligations resolve together. No account's net payout depends on first collecting an uncollateralized payment from another account at settlement. Backing is already in custody. In an implementation, enforce conserving transitions locally; use independent global reconciliation in tests and monitoring, rather than looping over all holders on each trade.

Accounts in different events have separate escrows. Moving genuinely free cash between them is a withdrawal and deposit, not a cross-event margin credit.

## No liquidation result and its limits

If domains and promises are immutable, collateral remains spendable, obligations are bounded, and every operation preserves the two invariants above, terminal liabilities are funded irrespective of interim prices. Both buyers and underwriters can hold to settlement without maintenance-margin liquidation. If a proposed voluntary trade cannot be funded, reject it.

Liquidation or recapitalization becomes necessary only after changing those assumptions: borrowing below worst liability, collateral whose usable value can fall relative to promised settlement units, lending reserve assets, intermediate compulsory payments, or unbounded exposure. Miscomputed states and custody exploits can also cause losses; liquidation is not a mathematical remedy for incorrect accounting. USDC-denominated settlement guarantees token units, not an independent guarantee of dollar purchasing power or freedom from issuer transfer restrictions.
