# Implementable solvency invariants

This specifies Architecture B's minimal checks and the reference model's proof obligations. It is not Solidity implementation. Architecture A instead enforces delivery of funded CTF inventory through native transformations; it should not independently lock the same collateral again.

## State and monetary invariants

For each open event `E`, each account `a`, and each allowed state `k`:

\[
\begin{aligned}
p_{a,k}&=\sum_j q_{a,j}f_{j,k} &&\text{aggregate-cache correctness}\\
W_{a,k}&=c_a+p_{a,k}\geq0 &&\text{account funding}\\
\sum_aW_{a,k}&=B_E &&\text{cash-only conservation}\\
\sum_E B_E&\leq\operatorname{balanceOf}(vault) &&\text{custody reconciliation}.
\end{aligned}
\]

The inequality allows unsolicited token donations. Donations do not credit an account, subsidize a trade, or authorize a withdrawal. Credited escrow must be matched by measured supported-token receipts, and separate event balances must never be spent twice.

With owned external contingent assets, replace `B_E` in the conservation equation with exact `A_E[k]=baseCash_E+ownedClaimPayout_E[k]`. Never also count another contract's gross escrow balance. For the MVP, omit such assets and all claim import/export entirely.

The domain is immutable, complete and nonempty. Finalization chooses one valid state once; a final state cannot be replaced. In this terminal-only MVP, oracle reports do not progressively prune funding support.

## Atomic batch checks

```text
execute(batch):
    require event is trading and before cutoff
    validate event/version/domain, nonce, expiry, fills, exact authorizations
    reject duplicate account entries, unsupported assets and excessive work
    load every affected account and authorized cover definition
    verify cash deltas sum to zero (fees credit explicit recipients)
    verify signed lot deltas sum to zero per cover
    compute candidate cash and aggregate payout for every affected account
    require arithmetic bounds on products, sums and future materialization
    measure authorized deposits; add only actually received units
    require min_k(candidateCash + candidatePayout[k]) >= 0 for each account
    require authorized withdrawal amounts do not violate that check
    commit all account/custody changes, fill counters and nonces together
    transfer authorized outputs under a reentrancy lock
    emit exact accounting receipt
    revert everything if any check or transfer fails
```

Computing candidates and verification must not call untrusted payoff code. Deposit external calls can have token callbacks even before commit; guard the whole operation. Enforce checks-effects-interactions for outputs, and never expose a state where a reentrant call can spend an uncommitted deposit or stale free-collateral value. Transient in-memory deficits inside an atomic computation are not independently spendable protocol state.

SafeERC20-style return handling alone does not establish exact received amounts. Reject fee-on-transfer, rebasing and unsupported callback assets; use actual balance deltas for approved deposits. In a production design, exact onchain signatures and ownership checks replace Python actor strings.

## Withdrawal and settlement

```text
withdraw(account, x):
    authorize account owner; reject negative x
    synchronize any final payout exactly once
    require x <= min_k(cash + payout[k])
    cash -= x; creditedEventEscrow -= x
    transfer x to authorized recipient

claim(account):
    require final event state k*
    authorize recipient policy; reject already claimed account
    s = cash + payout[k*]
    require s >= 0
    mark claimed and remove its economic entitlement
    creditedEventEscrow -= s
    transfer s
```

Resolution stores a state; it does not loop through every holder. Lazy per-account settlement prevents holder count from blocking finalization. Mixed materialized and unmaterialized accounts must reconcile: clear a paid account's terms once, and evaluate remaining accounts with the same final payout. Replaying a claim or first withdrawing its final entitlement then claiming it again must fail to create money.

## Cached risk and data bounds

A stored maximum is not an authorization to skip a full update. Verify the cached vector equals holdings in differential tests; onchain updates should be derived from exact signed lots and immutable definitions. Bound `n`, batch accounts, fills, vector magnitude, per-lot multiplication and accumulated absolute factor exposure. A small net vector does not prove intermediate arithmetic is safe.

If packing signed values, widen before multiplication/addition and validate both positive and negative limits before narrowing. Give accounts enough headroom for future materialization. Prohibit a vector that can trade cheaply but can never settle within resource limits.

## Transfer and order invariants

- Moving a long away from an account rechecks that account, even if no token leaves the vault.
- No internal claim and external native token simultaneously represent the same credited right.
- A fill checks the current portfolio and cumulative consumed quantity. Two quotes can each fit alone and fail together.
- Unreserved quotes can revert after a competing fill. Firm reservations require funding the jointly enforceable commitments; per-order best-case checks are insufficient.
- Portfolio novation needs explicit recipient consent and checks on both accounts, including consideration and fees.
- Revisions/nonces, event epochs and cutoff times cannot be bypassed by partial fills or callback races.

## What is established now

The proof is in [03-math.md](03-math.md); examples execute in [portfolio_examples.py](../simulations/portfolio_examples.py). The existing graph ledger provides atomic simulated accounting. The new tests compare it with direct-state calculations over 4,000 seeded candidate actions and exhaustive settlement ordering. CTF backing parity is separately executed on a local EVM.

No test here validates production signatures, real custody callbacks, chain reorg handling or the proposed contracts. Those are requirements for the next implementation phase, not reasons to claim this repository already has a production clearing house.
