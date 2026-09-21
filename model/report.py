"""Run checks, execute examples, and write a reproducible research report."""

import argparse
from datetime import datetime, timezone
import platform
from pathlib import Path
import sys
import unittest

from .benchmark import representation_benchmarks, unrelated_account_benchmarks
from .examples import funding_comparison, lifecycle


def table(headers, rows):
    return "\n".join(["| " + " | ".join(headers) + " |",
                      "| " + " | ".join("---" for _ in headers) + " |"] +
                     ["| " + " | ".join(str(v) for v in row) + " |" for row in rows])


def generate(test_result):
    _, life = lifecycle()
    funding = funding_comparison()
    shared, growth = representation_benchmarks()
    unrelated = unrelated_account_benchmarks()
    sections = ["# Core model: measured results",
                f"Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')} with Python {platform.python_version()} ({platform.system()}, {platform.machine()}).",
                "Command: `python3 -B -m model.report --output model/results.md`. Standard library only. All prices and trades below are stipulated test inputs.",
                "## Decision",
                "Keep investigating a simple account ledger for bounded custom payouts and atomic portfolio changes. The accounting model passes its checks. It demonstrates a coherent mechanism; it does not establish a commercially distinct product or a new financial payoff.",
                "Exact netting reduces the example maker's contribution from 146 (independent obligations) to 46. A correctly netted alternative matches 46. Atomic exit avoids a temporary deposit in one execution, but splitting sequential trades makes that deposit arbitrarily small in this divisible, zero-cost model. The credible hypothesis is easier execution of custom portfolio changes, not a universal collateral advantage.",
                "## Checks",
                f"**{test_result.testsRun} tests passed**, with no failures or errors. This includes 250 seeded portfolios compared with an independent interval evaluator; 100 seeded atomic transfers with global backing audits; 960 settlement scenarios covering all 120 redemption orders at eight results; and rejection/rollback checks for unsafe exits, altered approvals, stale revisions, fees, deadlines and exceptional outcomes.",
                "The compact and table implementations have separate evaluation formulas. Shared language assumptions, finite test coverage and the Python runtime remain common limitations. Passing these checks is not a formal proof or a security audit.",
                "## Executed lifecycle",
                table(["Step", "Escrow", "Maker net cash contributed", "Maker guaranteed balance", "Maker boundaries"],
                      [[r["step"], r["escrow"], r["maker_net_cash_in"], r["maker_guaranteed_balance"], r["maker_boundaries"]] for r in life["rows"]]),
                f"Introducing new range boundaries preserved the existing low and high buyers' balances and revisions: **{life['unrelated_accounts_unchanged']}**.",
                table(["Settlement result", "Maker", "Low buyer", "High buyer", "Range buyer", "Treasury", "Escrow after all redemptions"],
                      [[result] + [branch["payouts"][name] for name in ("maker", "low_buyer", "high_buyer", "range_buyer", "treasury")] + [branch["escrow"]]
                       for result, branch in life["settlement"].items()]),
                "VOID is an explicitly priced contractual outcome in this example: claim payouts are zero, not premium refunds. The model also tests nonzero exceptional payouts.",
                "## Peak funding to close the same two obligations",
                table(["Method", "Executions", "Peak additional maker cash", "Final locked capital"],
                      [[name, r["executions"], r["peak_additional_maker_cash"], r["final_locked"]] for name, r in funding.items()]),
                "Fractions are exact currency units: 11/5 = 2.2 and 11/50 = 0.22. Baseline is the maker's wallet after opening both obligations. Released existing capital can fund later trades. In the sliced case, each pair closes 1/n of both obligations at unchanged unit prices, and guaranteed cash is withdrawn after each execution. Peak new cash is 22/n for this schedule, with 2n executions. Allowing arbitrarily small fills therefore removes any strictly positive universal lower bound on sequential funding. With minimum trade sizes, fees or changing quotes the tradeoff changes; those effects are not measured here.",
                "A competent existing atomic netting mechanism can reproduce the atomic row. These results distinguish execution methods, not brands or novel capabilities.",
                "## Representation measurements",
                "Timings are median microseconds per operation over five repeats of 20 iterations. These are local Python measurements, not transaction throughput, gas estimates or service-level promises. Counts below are rational scalar slots, including boundaries; they are not serialized bytes or Python heap sizes.",
                "The fixed profile is one ramp with two account boundaries. We compare a materialized shared-axis interval table, a table using only this account's own boundaries, and the compact coefficient form.",
                table(["Shared boundaries", "Compact slots", "Shared-table slots", "Account-table slots", "Compact extrema µs", "Shared-table extrema µs", "Account-table extrema µs"],
                      [[r["shared_boundaries"], r["compact_scalar_slots"], r["shared_scalar_slots"], r["local_table_scalar_slots"],
                        f"{r['compact_min_us']:.2f}", f"{r['shared_table_min_us']:.2f}", f"{r['local_table_min_us']:.2f}"] for r in shared]),
                "The storage advantage is against a materialized global table. An account-local interval table also avoids unrelated boundaries and can inspect precomputed endpoints faster. The compact representation is retained for canonical cancellation and additive composition in this prototype; locality is not unique to it. Caching minima, sharing axes, compressing tables or maintaining augmented trees changes this comparison.",
                "For genuine account growth, the profile alternates between zero and one at every boundary:",
                table(["Account boundaries", "Compact extrema µs", "Account-table extrema µs", "Compact normalization µs"],
                      [[r["account_boundaries"], f"{r['compact_min_us']:.2f}", f"{r['local_table_min_us']:.2f}", f"{r['compact_normalize_us']:.2f}"] for r in growth]),
                "Both extrema scans grow with account complexity. Table construction, table updates, fixed-point arithmetic, serialization and adversarial numerator/denominator growth are not benchmarked. Exact rational arithmetic is useful evidence of conservation, not a production precision design.",
                "## Unrelated funded activity",
                table(["Unrelated funded accounts", "Two-account execute µs"],
                      [[r["unrelated_funded_accounts"], f"{r['execute_us']:.2f}"] for r in unrelated]),
                "Each unrelated account actually holds a distinct funded step claim against a separate backer. The timed batch alternates opening and closing a one-unit interval between the same two accounts. Timing includes payload hashing, conservation, affected-account funding checks and commit; it excludes creating harness approvals and a full audit. Global audits run outside timing. This tests account locality in memory, not database/storage contention, concurrent execution or network cost.",
                "## What is not established",
                "No executable quotes, price discovery, willingness to use the product, multi-variable netting, cryptographic authorization, real custody, fixed-point redemption, settlement reporting, transaction fees or production scalability were tested. Harness approvals do not authenticate anyone. Simulated fills are not demand.",
                "## Next smallest decision",
                "Specify a small set of concrete portfolio edits and executable quote terms. Compare identical accepted final payouts, total cash flows and user actions using this account model and the strongest practical existing workflow. Select a numeric precision and complexity budget before a production implementation. Keep the kernel independent of the quote mechanism until that comparison identifies a necessary advantage.",
                "Do not build a chain, protocol token, AMM, generalized multi-variable market, frontend suite or production custody from this model yet."]
    return "\n\n".join(sections) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Write Markdown; omit to print it")
    args = parser.parse_args()
    suite = unittest.defaultTestLoader.loadTestsFromName("model.test_model")
    result = unittest.TextTestRunner(stream=sys.stderr, verbosity=1).run(suite)
    if not result.wasSuccessful():
        raise SystemExit("Checks failed; report was not written.")
    report = generate(result)
    if args.output:
        args.output.write_text(report, encoding="utf-8")
        print(f"Wrote {args.output}")
    else:
        print(report, end="")


if __name__ == "__main__":
    main()
