# Core model: measured results

Generated 2026-09-17T10:35:14+00:00 with Python 3.14.0 (Darwin, arm64).

Command: `python3 -B -m model.report --output model/results.md`. Standard library only. All prices and trades below are stipulated test inputs.

## Decision

Keep investigating a simple account ledger for bounded custom payouts and atomic portfolio changes. The accounting model passes its checks. It demonstrates a coherent mechanism; it does not establish a commercially distinct product or a new financial payoff.

Exact netting reduces the example maker's contribution from 146 (independent obligations) to 46. A correctly netted alternative matches 46. Atomic exit avoids a temporary deposit in one execution, but splitting sequential trades makes that deposit arbitrarily small in this divisible, zero-cost model. The credible hypothesis is easier execution of custom portfolio changes, not a universal collateral advantage.

## Checks

**28 tests passed**, with no failures or errors. This includes 250 seeded portfolios compared with an independent interval evaluator; 100 seeded atomic transfers with global backing audits; 960 settlement scenarios covering all 120 redemption orders at eight results; and rejection/rollback checks for unsafe exits, altered approvals, stale revisions, fees, deadlines and exceptional outcomes.

The compact and table implementations have separate evaluation formulas. Shared language assumptions, finite test coverage and the Python runtime remain common limitations. Passing these checks is not a formal proof or a security audit.

## Executed lifecycle

| Step | Escrow | Maker net cash contributed | Maker guaranteed balance | Maker boundaries |
| --- | --- | --- | --- | --- |
| Sell low tail | 100 | 78 | 0 | 1 |
| Sell high tail | 100 | 46 | 0 | 2 |
| Introduce range boundaries | 105 | 46 | 5 | 4 |
| Withdraw guaranteed 5 | 100 | 41 | 0 | 4 |
| Buy back half of both tails, fee 1 | 51 | 19 | 0 | 4 |

Introducing new range boundaries preserved the existing low and high buyers' balances and revisions: **True**.

| Settlement result | Maker | Low buyer | High buyer | Range buyer | Treasury | Escrow after all redemptions |
| --- | --- | --- | --- | --- | --- | --- |
| 100 | 30 | 0 | 0 | 20 | 1 | 0 |
| VOID | 50 | 0 | 0 | 0 | 1 | 0 |

VOID is an explicitly priced contractual outcome in this example: claim payouts are zero, not premium refunds. The model also tests nonzero exceptional payouts.

## Peak funding to close the same two obligations

| Method | Executions | Peak additional maker cash | Final locked capital |
| --- | --- | --- | --- |
| Sequential full legs, low first | 2 | 22 | 0 |
| Sequential full legs, high first | 2 | 32 | 0 |
| Sequential, 10 slices per leg | 20 | 11/5 | 0 |
| Sequential, 100 slices per leg | 200 | 11/50 | 0 |
| Atomic package | 1 | 0 | 0 |

Fractions are exact currency units: 11/5 = 2.2 and 11/50 = 0.22. Baseline is the maker's wallet after opening both obligations. Released existing capital can fund later trades. In the sliced case, each pair closes 1/n of both obligations at unchanged unit prices, and guaranteed cash is withdrawn after each execution. Peak new cash is 22/n for this schedule, with 2n executions. Allowing arbitrarily small fills therefore removes any strictly positive universal lower bound on sequential funding. With minimum trade sizes, fees or changing quotes the tradeoff changes; those effects are not measured here.

A competent existing atomic netting mechanism can reproduce the atomic row. These results distinguish execution methods, not brands or novel capabilities.

## Representation measurements

Timings are median microseconds per operation over five repeats of 20 iterations. These are local Python measurements, not transaction throughput, gas estimates or service-level promises. Counts below are rational scalar slots, including boundaries; they are not serialized bytes or Python heap sizes.

The fixed profile is one ramp with two account boundaries. We compare a materialized shared-axis interval table, a table using only this account's own boundaries, and the compact coefficient form.

| Shared boundaries | Compact slots | Shared-table slots | Account-table slots | Compact extrema µs | Shared-table extrema µs | Account-table extrema µs |
| --- | --- | --- | --- | --- | --- | --- |
| 10 | 8 | 33 | 9 | 5.66 | 12.23 | 3.56 |
| 100 | 8 | 303 | 9 | 5.66 | 116.05 | 3.56 |
| 1000 | 8 | 3003 | 9 | 5.66 | 1108.30 | 3.56 |
| 5000 | 8 | 15003 | 9 | 5.66 | 5576.70 | 3.56 |

The storage advantage is against a materialized global table. An account-local interval table also avoids unrelated boundaries and can inspect precomputed endpoints faster. The compact representation is retained for canonical cancellation and additive composition in this prototype; locality is not unique to it. Caching minima, sharing axes, compressing tables or maintaining augmented trees changes this comparison.

For genuine account growth, the profile alternates between zero and one at every boundary:

| Account boundaries | Compact extrema µs | Account-table extrema µs | Compact normalization µs |
| --- | --- | --- | --- |
| 2 | 5.70 | 3.53 | 11.18 |
| 10 | 28.91 | 12.36 | 47.91 |
| 100 | 289.75 | 113.00 | 510.58 |
| 1000 | 2972.08 | 1142.51 | 5028.76 |

Both extrema scans grow with account complexity. Table construction, table updates, fixed-point arithmetic, serialization and adversarial numerator/denominator growth are not benchmarked. Exact rational arithmetic is useful evidence of conservation, not a production precision design.

## Unrelated funded activity

| Unrelated funded accounts | Two-account execute µs |
| --- | --- |
| 0 | 124.80 |
| 10 | 122.31 |
| 100 | 124.71 |
| 1000 | 125.19 |

Each unrelated account actually holds a distinct funded step claim against a separate backer. The timed batch alternates opening and closing a one-unit interval between the same two accounts. Timing includes payload hashing, conservation, affected-account funding checks and commit; it excludes creating harness approvals and a full audit. Global audits run outside timing. This tests account locality in memory, not database/storage contention, concurrent execution or network cost.

## What is not established

No executable quotes, price discovery, willingness to use the product, multi-variable netting, cryptographic authorization, real custody, fixed-point redemption, settlement reporting, transaction fees or production scalability were tested. Harness approvals do not authenticate anyone. Simulated fills are not demand.

## Next smallest decision

Specify a small set of concrete portfolio edits and executable quote terms. Compare identical accepted final payouts, total cash flows and user actions using this account model and the strongest practical existing workflow. Select a numeric precision and complexity budget before a production implementation. Keep the kernel independent of the quote mechanism until that comparison identifies a necessary advantage.

Do not build a chain, protocol token, AMM, generalized multi-variable market, frontend suite or production custody from this model yet.
