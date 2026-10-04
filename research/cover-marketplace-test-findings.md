# Cover marketplace and CTF test findings

The reusable cover marketplace is mechanically feasible: a customer can create an interval cover, obtain it from related liquidity, change it, and close it. Native Gnosis CTF reproduced this lifecycle and the tested capital efficiency. These results support building shared routing, but do not establish customer demand or sustainable maker pricing.

All prices, balances and probability models below are synthetic. The CTF tests ran on a local Ganache EVM using the published `@gnosis.pm/conditional-tokens-contracts@1.0.3` contract, compiled with Solidity 0.5.17. They did not use a live exchange or move real funds. The test exchange and fixed routers are research fixtures.

## What passed

The [Python adapter](cover_marketplace_flow.py) uses the existing kernel without changing it. Four atomic routes allowed two customers to buy the same cover, one customer to widen it, and that customer to close it. Nine terminal scenarios, including cancellation, paid every account and exhausted escrow. An independent raw path evaluator checked 315 account and outcome combinations during the lifecycle.

Quote search executed 36 intervals independently from eight threshold covers. Twenty eight intervals had no direct orders. Search compared exact direct and related routes, checked maker funding and capacity, selected the cheaper feasible route, and used a direct quote when a source quote was cancelled. These are independent fresh-inventory tests; they do not prove simultaneous depth for all 36 covers.

Ten invalid requests left both the ledger and quote counters unchanged: insufficient customer budget, fractional quantities, incompatible cancellation payouts, cancelled quotes, stale epochs, expired quotes, insufficient maker funding, a missing atomic offset, insufficient capacity, and closing a cover the customer did not own.

The [native CTF runner](ctf/run-evidence.cjs) passed 160 assertions, seven expected transaction reverts, and 26 terminal redemption scenarios. It tested order placement, partial fills, cancellation, repeated orders backed by the same inventory, buyer-funded issuance, partial split/merge, unequal cancellation payouts, and the complete interval lifecycle. The existing 63 kernel tests also passed.

## How related liquidity supplied a new cover

Let `T2` pay 100 when the event value is at least 2, and `T5` pay 100 when it is at least 5. Both pay zero on cancellation. The cover paying 100 for values in `[2,5)` equals `T2 - T5` on every permitted outcome.

| Customer action | Existing source quotes | Price before fees |
| --- | --- | --- |
| Buy the new cover for `[2,5)` | Buy T2 at 40 and sell T5 at 15 | Pay 25 |
| Widen the held cover to `[1,5)` | Buy T1 at 50 and sell T2 at 38 | Pay 12 more |
| Close the widened cover | Sell T1 at 48 and buy T5 at 16 | Receive 32 |

In CTF, the router received T2 and split it into the interval and T5. The customer received the interval token; the maker bidding for T5 received T5. No extra ERC20 collateral entered CTF for this partial split. Changing and closing used further splits and merges. Recovered complete positions allowed makers to withdraw their original backing; final CTF escrow was zero.

In the kernel, a router account held the signed replication residual. Its payout was exactly zero on every path. Each maker and customer remained independently funded. The Python version charged one assumed currency unit per action. That customer's roundtrip loss was 8 including fees; the fee-free CTF version lost 5 through the source spreads.

This establishes a way to share existing liquidity. It still requires executable bids and asks in the appropriate directions. A payout identity cannot manufacture a missing bid, maker inventory, or available capital.

## CTF collateral and maker usefulness

CTF supplies position issuance, transfers and redemption; it does not itself supply an order book. Existing positions can be transferred without minting them again. Its full split locks ERC20 backing, while a partial split burns an existing union position and issues its components. These mechanics are documented in the [Gnosis developer guide](https://conditional-tokens.readthedocs.io/en/latest/developer-guide.html).

The public [Polymarket exchange source](https://github.com/Polymarket/ctf-exchange/blob/main/src/exchange/mixins/Trading.sol) also distinguishes transfers from minting and merging matches. This source inspection is not a test of the current deployed Polymarket exchange. Our illustrative local book verifies only the existing-inventory lifecycle.

Consider two mutually exclusive covers A and B, each paying at most 100, sold for premiums of 30 and 40. A common condition has outcomes A, B, neither, and cancellation; both covers pay zero on cancellation.

| Funding construction | Maker peak cash contribution | Maker contribution after both sales | Total backing after both sales |
| --- | ---: | ---: | ---: |
| CTF common condition, inventory minted before buyers arrive | 100 | 30 | 100 |
| CTF common condition, sequential buyer-funded issuance | 70 | 30 | 100 |
| CTF common condition, simultaneous buyer-funded issuance | 30 | 30 | 100 |
| Kernel, sequential atomic fills and withdrawal | 70 | 30 | 100 |
| Kernel, simultaneous atomic fill | 30 | 30 | 100 |
| Separate CTF binary conditions, inventory minted before buyers arrive | 200 | 130 | 200 |

Posting additional sell orders over the common-condition inventory added **zero** collateral. The same inventory could back multiple outstanding orders, but after it was consumed a competing fill reverted, including its payment and fill counter. Such orders are not independently reserved liquidity.

For sequential common-condition issuance, A's buyer contributed 30 and the maker contributed 70. The maker later split its remaining NO A position to deliver B without another collateral deposit, received B's premium of 40, and retained the neither/cancellation claim. The maker's final contribution was 30, with a peak of 70.

Separate binary conditions did not natively encode the shared exclusivity. That is why common event representation matters. A CTF implementation that creates an unrelated binary condition for each cover can lose this advantage.

Buying back only one missing outcome did not permit a full collateral merge. Buying back all required components did. Overlapping outcomes also failed the native partition check; overlapping liabilities cannot be treated as exclusive.

When both covers instead refunded 60 on cancellation, backing increased to 120 and the maker's net contribution increased to 50. CTF reproduced this using a basket of normal and cancellation positions for each buyer. Presenting that basket as one transferable cover would require an additional custody wrapper. This test does not implement that wrapper.

## Maker profitability remains conditional

After the Python lifecycle, makers collectively received 30 net and owed the remaining customer's 100-cap `[2,5)` cover. Their combined terminal profit was therefore `30 - cover payout`, before costs. Worst combined profit was minus 70.

An explicitly assumed distribution consistent with all source bid/ask quotes valued T1 at 49, T2 at 39, T5 at 15.5, and the remaining interval at 23.5. It included a one percent cancellation probability. Makers' expected gross profit was 6.5 under that model. If total maker costs were 7, expected profit became minus 0.5.

Under uniform normal outcomes and zero cancellation probability, the interval probability was 37.5 percent, so the same trading sequence produced expected maker profit of minus 7.5 before costs. Break even was an interval probability of 30 percent before costs. This exposes model and adverse selection risk; correct collateral accounting does not make incorrect prices profitable.

No observed quotes, buyer exposure data, gas benchmark, maker capital charge, oracle delay estimate, or live hedge costs were used. The test cannot establish better protection terms than existing products.

## Implementation recommendation

Preserve reusable event covers. Prioritize a canonical event definition, restricted payout templates, and atomic routing between direct and related quotes. Canonical identity must bind the source, collateral, settlement rules, precision, finality and exceptional payouts. Cosmetic creator labels should not fragment economically identical contracts.

For an initial product with a manageable finite terminal outcome domain, CTF plus a routing layer is a credible implementation option. The tested liquidity and capital benefits do not require the custom kernel. A production router still needs authenticated maker terms, fill limits, cancellation, deadlines, customer price bounds, safe allowances and atomic execution.

Retain the custom kernel as a candidate for requirements where it gives a measured advantage: compact path-dependent portfolios, progressive finality, or payout families whose equivalent CTF representation becomes expensive. CTF can represent joint outcome histories too, but enumerating them can become large; CTF's per-condition limit is 256 slots. The current graph model also has finite state and work limits. Neither approach automatically supports every arbitrary new continuous threshold or history function.

Current kernel admission remains admin-only. The prototype's customer template creation uses a trusted harness adapter, and its approvals are Python assertions rather than signatures. Those production requirements remain unfinished.

The next commercial validation should use one event family and real source quotes or maker shadow quotes. Compare direct and routed all-in premiums, executable size, probability calibration, maker profit after costs, and the customer's actual reduction in loss. The present result justifies that focused experiment; it does not justify promising liquidity for every user-created payout.

## Reproduce the evidence

From the repository root:

```sh
python3 -B research/cover_marketplace_flow.py
python3 -B -m unittest model_v2.test_kernel model_v2.test_netting_review -q
npm ci --prefix research/ctf --ignore-scripts --no-audit --no-fund
node research/ctf/run-evidence.cjs
```

The runner uses an in-process EVM. Its test currency uses 1,000,000 base units per displayed currency unit; it is not real USDC. Exact dependency versions and transitive integrity hashes are saved in `ctf/package.json` and `ctf/package-lock.json`. Results include source hashes. An existing dependency installation can be selected with `ASCEMARKET_CTF_DEP_ROOT`.

Machine-readable results are in [the kernel and routing results](cover-marketplace-flow-results.json) and [the CTF results](ctf/ctf-evidence-results.json). No rendered Page preview was available; this record was saved and checked as repository Markdown.
