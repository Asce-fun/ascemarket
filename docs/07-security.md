# Security research and test obligations

The primary property is preservation of nonnegative account entitlement in every allowed state, together with custody conservation. A mathematically solvent unauthorized transaction can still steal funds, so solvency is necessary but not sufficient for security.

## Attack surfaces

| Surface | Failure mode | Required control and test |
|---|---|---|
| Incorrect netting | Pairwise discounts overcount relief; longs credited twice | Whole-vector minimum; independent raw-state reference |
| Malformed payoff | Negative bought exposure, missing states, unbounded amounts | Fixed length, total nonnegative bounded definition, exception entries |
| State mutation | Old liabilities reinterpreted or valid adverse state removed | Immutable domain/terms; new IDs for changed semantics |
| Boundary mapping | `<`/`≤`, scaling, timestamp or source selection differs | Test exact boundary, adjacent precision ticks, tails and failure mapping |
| Oracle manipulation | False outcome, stale round, disputed report treated final | Pinned policy/source, historical selection verification, finality delay, immutable timeout |
| Reentrancy | Deposit/output or receiver callback observes stale funding | Whole-operation guard, bounded calls, effects before outputs, callback adversaries |
| Rounding | Partial quantities or fees mint net entitlement | Exact lots/total amounts, one rounding policy; one-base-unit adversarial fills |
| Overflow | Large opposite factors mask unsafe intermediate products | Checked wider arithmetic and absolute exposure limits |
| Partial fills | Full-order hedge assumed despite incomplete execution | Check actual executed quantity and residual account each fill |
| Withdrawal races | Concurrent quote assumes collateral already withdrawn | Onchain serialization and current-account checks; nonce/revision tests |
| Temporary underfunding | Callback spends cash between legs | Candidate computation then atomic commit; reject untrusted callbacks |
| Settlement ordering | Shorts pay before longs; double materialization or replay | Pre-funded net claims, exactly-once pull settlement |
| Account transfers | Hedge leaves or negative liabilities move without consent | Both parties authorize and pass funding checks |
| Fee accounting | Fee silently taken from backing or discarded in conservation | Explicit fee recipient and payer; dust and last-unit tests |
| Token custody | False ERC-20 success, fee-on-transfer, rebasing or donations credited | Pinned supported asset, receipts and credited balances reconciled |
| External claim export | Internal right remains while token leaves | Exact debit, asset-vector update, residual-account check |
| State explosion | New curves force huge domains or irredeemable catalogue | Fixed domain, bounded definitions/batch work, lazy account settlement |
| Pathological maker vectors | Excessive magnitudes, duplicate indices or crafted packing | Full decoding validation, limits, signed arithmetic checks |
| Orders/quoting | Same capacity promised to many firm quotes | Unreserved current checks, or explicit jointly funded reservations |
| Administrative powers | Pause becomes confiscation or economic upgrade | Document roles; preserve immutable payout/redemption rules |

Oracle truth is external to the algebra. Selecting a wrong state may keep the vault solvent while paying the wrong person. A small low-security oracle can be economically attacked when payout incentives exceed its cost; capacity and source-security assumptions must be evaluated together.

## Stateful invariant strategy

Generate deposits, withdrawals, conserving trades, partial fills, close/modify packages, fees, transfers, cancellations, reports and final claims. At each accepted action:

1. Reconstruct each payout directly from lots and definitions, independently of the cached risk algorithm.
2. Evaluate every allowed state and require every account entitlement nonnegative.
3. Require the sum of entitlements equals credited event assets in every state.
4. Reconcile wallets, vault custody, donations and paid claims; ensure no token was created.
5. Check old final facts and immutable definitions did not change.

For rejected actions, require a byte-identical economic snapshot, including wallets, fills, nonces and escrow. Test both orderings of a competing withdrawal/fill; execution can reject a stale quote but cannot underfund the account.

For each generated portfolio, branch on every state and permute claim order. Final aggregate payouts must equal the same original backing, independent of order; replayed claims pay zero or reject. Include maximal monetary bounds and events with all-zero buyer payouts on INVALID.

## Important targeted counterexamples

- Three mutually exclusive 100 claims: backing is 100, not zero after three pairwise discounts.
- Two “exclusive normal” claims with 60 refunds each: backing is 120.
- Identical long/short curves under different admitted IDs: zero exposure before removing the long; removing it requires full funding.
- Two high-cap claims on the same adverse state: no capital saving.
- Guaranteed long floor withdrawn into negative signed cash: gross claim export or sale needs restored funding.
- Cache has two tied maxima; update/delete one, then the other. Cached maximum must remain correct.
- An arbitrary new strike splits a bucket after trading: reject it rather than infer a false relationship.
- Premium credited once versus premium subtracted again from liability: only the correct accounting preserves escrow.
- A one-base-unit fee or withdrawal from a zero-floor writer: reject.
- Buyback reduces maximum liability less than its cash cost: require a funded candidate or reject.

## Completed evidence

- Existing Python suite: 63 tests passed.
- New suite: 20 tests passed, including 4,000 seeded candidate actions compared to independent direct-state arithmetic, 1,000 randomized CTF backing certificates, and 120 claim orders for each of six states (720 branches).
- Existing native CTF runner: 160 assertions, seven expected transaction reverts, 26 terminal scenarios.
- New native CTF curve baseline: 63 assertions, 12 terminal redemption scenarios, and gas receipts.

These are research tests. Python authorization uses actor/digest assertions; it is not cryptographic permission. Ganache uses the existing research token and harness transfers. No production callback/signature tests, deployment audit, real source oracle or historical trading-profit backtest is claimed.

## Future Solidity verification

Once the model and architecture choice are accepted, implement a small contract and a deliberately simple state-by-state test oracle. Foundry handlers should generate admissible and inadmissible operations with multiple actors, fuzz USDC-scale values and signed bounds, include malicious token/receiver fixtures, and test expiry/report/timeout races. Measure coverage of accepted versus rejected operations so a suite that rejects everything cannot appear to prove usefulness.

The acceptance property is not merely that `maxLiability` returns expected numbers: every reachable funded state must remain backed after any successful protocol action. Verify also that conservation transitions are complete; a missing fee or duplicated right can otherwise leave individually nonnegative accounts with more entitlements than custody.
