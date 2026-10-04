# Netting review and a simple explanation

Review date: 29 September 2026. Scope: the executable Python v2 kernel plus the proposed order/contract integration. No deployed Solidity or ERC-6909 custody implementation exists in this repository to audit.

**Result:** no underfunding or conservation counterexample was found in the reviewed kernel paths and tests below. This is evidence for the finite-graph accounting, not a guarantee against protocol breaches. The proposed token reserve, real authorization, exchange gateway and oracle integration remain implementation requirements.

## 1. What netting across cover IDs means

Suppose one seller writes these two covers for the same match:

- Cover A pays 100 if Barcelona wins at full time.
- Cover B pays 100 if Real Madrid wins at full time.

Assume these are defined on the same final result, and draw/cancellation pay zero. One match cannot have both teams win under those rules.

| Event result | A pays | B pays | This seller must pay in total |
|---|---:|---:|---:|
| Barcelona wins | 100 | 0 | 100 |
| Real Madrid wins | 0 | 100 | 100 |
| Draw | 0 | 0 | 0 |
| Cancellation under these example terms | 0 | 0 | 0 |

The seller needs 100 of total backing, not 200. The two buyers still own separate claims. Neither claim disappears. The same 100 can back them because their combined payment never exceeds 100.

If buyers pay premiums of 30 and 40, those 70 become backing too. The seller needs to contribute another 30 **if both trades settle atomically**. If A settles alone first, it needs 100 backing then: premium 30 plus seller contribution 70. After B later fills for 40, cash becomes 140 and 40 is withdrawable. Future expected premiums cannot fund an earlier trade.

This is a maximum-obligation calculation. It is not a discount based on probabilities, not a match between two order sides, and not an instruction to pay just one buyer regardless of the event.

## 2. How the computer connects different IDs

An ID identifies a validated payout definition. The manager loads that definition from its own records. It does not infer meaning from the hash or title.

```text
Event E has a common set of permitted histories.
CoverID A → A's payout on those histories.
CoverID B → B's payout on those same histories.
Writer account → cash and signed quantities for A, B and all other held covers.

For each permitted history conceptually:
    amount owed = A quantity owed × A payout
                + B quantity owed × B payout
                + every other obligation
                - eligible internal rights held by this same account

Use the largest resulting obligation to check backing.
```

The actual verifier aggregates signed node/edge factors and uses an exact graph recurrence instead of enumerating every history. It neither merges token IDs nor scans every order in the exchange. Distinct IDs can have related payouts; identical display names do not establish a relationship.

For the two short covers, the internal account is `cash = 100, A = -1, B = -1`. Its minimum entitlement is `min(100 - A_payout - B_payout) = 0`, so it is funded. Withdrawal of 1 would make the minimum −1 and must fail.

## 3. When backing must be larger

**Both can win:** “a goal in ten minutes” and “a player is substituted” can both happen. If both pay 100, the combined obligation can be 200. Premiums of 70 then require another 130, not 30.

**Cancellation changes the promise:** if A and B normally exclude each other but cancellation pays 60 on each, maximum combined payment is 120. Premiums of 70 require another 50. The exceptional branch must be in the graph before the trade.

**More units:** one A plus one B under exclusive rules needs 100. Two A plus one B needs 200 because A may pay twice. Existing backing cannot be reused without recalculating the complete resulting account.

**More than two covers:** three mutually exclusive 100-payout covers need 100 together. Do not subtract three independently computed pairwise “savings” from 300; that incorrect method would leave zero backing. The kernel evaluates the whole account once.

**Different owners or events:** this kernel does not share margin across them. A seller of A and a different seller of B each need their own funded accounts. Tokens in an external wallet also do not automatically count as internal collateral; they can leave that wallet.

## 4. Why the accounting is sound under its assumptions

For each account and every remaining permitted history:

```text
entitlement = cash + sum(signed lots × payout)
entitlement >= 0
```

The internal model additionally maintains:

```text
sum(all account entitlements on that history) = remaining event escrow
```

The proposed external-token extension must maintain:

```text
sum(internal account entitlements)
    + sum(external token supply × that cover's payout)
    = remaining event escrow
```

The external-token term is the virtual reserve. It is not additional cash and cannot also appear as a buyer's internal holding.

Why the state transitions preserve these equations:

- Issuance creates a writer obligation and an equal buyer right. Premium transfers and fees conserve cash. Deposits add the same amount to cash entitlement and escrow.
- A withdrawal subtracts the same amount from entitlement and escrow, and cannot exceed the account's guaranteed minimum.
- Valid final facts only remove possible histories. The minimum over a smaller nonempty set cannot decrease. A provisional report cannot remove funded histories.
- Materializing a fixed payout replaces `quantity × fixed payout` with exactly that cash amount. It does not add a second entitlement.
- External-token mint/burn/import/redemption must preserve the extended equation. These are design obligations, not implemented token tests.

This reasoning depends on complete, correct payout definitions; exact arithmetic; complete account loading; valid finality; conservation; and authorization. A solvency check alone cannot prevent theft through an unauthorized but solvent trade.

## 5. Internal review coverage

| Reviewed boundary | Evidence / result | Limit |
|---|---|---|
| IDs and immutable definitions | `schema.py` binds covers to their market and validates sparse factors; ledger admission rejects foreign definitions | Python hashing is not the future Solidity encoding |
| Complete-account evaluation | `compile_factors` aggregates all current holdings, with checked signed arithmetic; no independent pairwise discount | Contract storage iteration must preserve the same completeness |
| Exact graph minimum | Generic recurrence, reachable terminal paths and optional proven suffix optimization compared with independent path evaluation | A correct minimum on an incomplete real-world graph is still the wrong product |
| Batches, fees, withdrawals | `_candidate` loads full accounts, checks per-cover/cash conservation, includes fees, checks every affected account and commits only afterward | Simulated wallets, no external token calls |
| Reusing margin / removing a hedge | Targeted tests reject a second underfunded issue, over-withdrawal, and hedge export without extra funding | Export test uses an internal reserve-account proxy, not ERC-6909 code |
| Facts and cancellation | Support is intersected; empty/conflicting support rejected; provisional reports do not narrow funding support | Authorized source truth and semantic mapping are not proven |
| Resolution and claims | Fixed positions materialize once; both claim orders reconcile to zero escrow | Python one-shot account claim is not external token redemption |
| Standing orders | Current backing is rechecked on fill; quantities, replay, epoch and expiry tested by existing suite | Harness approvals are not cryptographic signatures; new receiver/mode schema differs |
| Proposed exchange gateway | Narrow settlement shape and explicit pinned-exchange authorization dependency reviewed | No implementation to test; authorization defects can cause loss despite solvency |
| Token reserve and custody | Reviewed export/import/issuance/redemption conservation requirements | Actual reserve accounting, reentrancy and ERC-20/6909 behavior remain untested |

## 6. Test evidence

Commands:

```sh
python3 -B -m unittest model_v2.test_kernel model_v2.test_netting_review -q
python3 -B -m model_v2.research --seeds 200 --steps 100 --output /private/tmp/ascemarket-netting-review-results.json
```

Results from this run:

- 63 tests passed: 54 existing tests and 9 new netting review tests.
- New exhaustive check: 5,625 signed-portfolio/support/cash combinations agree with independent payout enumeration.
- Existing suite also includes 1,000 randomized general-graph differential cases.
- Synthetic lifecycle replay: 200 seeds × 100 attempted steps; 14,274 accepted operations, 2,792 rejected without state mutation, and 2,934 skips for resolved covers.
- 448,826 path audits across replay states; all final escrows zero.

These are synthetic accounting checks. Path audit counts include repeated histories at different ledger states; they are not counts of unique attacks or real-world events. The source hashes and replay summary are saved in [netting-review-results.json](netting-review-results.json). The new regressions are in [test_netting_review.py](../model_v2/test_netting_review.py).

## 7. Release-critical boundaries

No netting arithmetic bug was reproduced, so this review does not change the kernel math. It identifies the following boundaries that must hold in implementation:

1. **Every allowed payout must be funded, including exceptions.** Admission must reject unsupported joint-history definitions rather than asserting exclusivity from names or correlation.
2. **Never remove a hedge without rechecking the residual account.** A freely transferable external token cannot remain counted as the writer's internal hedge.
3. **Keep token reserve accounting complete.** Issuance must not duplicate internal/external buyer rights; redemption must burn; imports must remove the external reserve exactly once. Also cover redemption before/after writer withdrawals and later credits to previously emptied accounts.
4. **Authenticate owners independently of callers.** Pinned-exchange code is security-critical; receiver binding, debt authorization, fees and replay require real contract tests. ERC-20/6909 approvals alone are insufficient.
5. **Do not reverse finalized facts after collateral is released.** If the oracle falsely finalizes an outcome, a later real-world correction cannot safely be implemented by widening the graph. That is an oracle-policy risk even if accounting remains correct for the accepted fact.
6. **Bound execution and finalization work.** A correct but unexecutable settlement can lock payouts. Python limits do not establish EVM gas limits.

The shared manager also holds multiple events' collateral. Logical netting is event-local, but a custody implementation bug can affect more than one event. This design must not be described as physical per-event loss isolation.
