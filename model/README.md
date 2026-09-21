# AsceMarket accounting research model

This is an executable companion to [core-design.md](../core-design.md). It tests one question: can accounts holding bounded custom payouts be changed atomically while preserving exact funding across every allowed result?

It is a local, standard-library Python model. There are no external dependencies, services, keys or real funds. Use Python 3.10 or newer; the recorded run uses Python 3.14. Approvals are harness assertions, not cryptographic signatures.

From the project root:

```sh
python3 -B -m unittest model.test_model -v
python3 -B -m model.report --output model/results.md
python3 -B -m model.workflow_examples --output research/workflow-checks.json
python3 -B -m model.capital_challenge --output research/capital-results.json
python3 -B -m model.competitive_case
python3 -B -m model.competitive_extensions
python3 -B -m model.negrisk_case
```

The report command also runs the tests and refuses to write a new report if they fail. It then executes the lifecycle, funding comparisons and local CPU benchmarks. Omit `--output` to print the report. The `-B` flag avoids creating Python bytecode files.

Read [results.md](results.md) for measured outcomes and limitations. Timings vary by machine and load; correctness checks use exact values and never depend on timing thresholds.

| File | Purpose |
|---|---|
| [payoffs.py](payoffs.py) | Canonical steps, ranges and ramps; exact extrema including jump limits and VOID |
| [table.py](table.py) | Independent explicit interval evaluator built from elementary formulas |
| [ledger.py](ledger.py) | Approved batches, revisions, premiums, fees, deposits, withdrawals and individual redemption |
| [examples.py](examples.py) | Worked lifecycle and atomic versus sequential funding comparisons |
| [test_model.py](test_model.py) | Differential, state transition, rollback and conservation checks |
| [benchmark.py](benchmark.py) | Shared/local table comparisons, account growth and unrelated funded activity |
| [report.py](report.py) | Reproducible Markdown report generation |
| [workflow_examples.py](workflow_examples.py) | Check the three hypothetical quote cards and their payoff comparisons |
| [capital_challenge.py](capital_challenge.py) | Matched lifecycle funding, independent reference, adverse paths and saved public-price replay |
| [competitive_case.py](competitive_case.py) | Two-butterfly portfolio, optimized Gamma vault allocation with a lower-bound certificate, and matched exit paths |
| [competitive_extensions.py](competitive_extensions.py) | Exact certificate checks extending the Gamma cash bound to additional put constructions |

Read [the capital challenge](../research/capital-challenge.md) for the distinction between opening contribution and lifecycle peak funding. Its public-price replay uses the committed snapshot; running it does not contact an exchange.

Read [the named architecture comparison](../research/competitive-case.md) for the narrower funding advantage against an inspected Gamma vault formula. The script uses exact rational arithmetic and the existing Asce ledger; it does not execute Gamma Solidity, connect to a venue or obtain live margin quotes.

Read [the neg-risk comparison](../research/negrisk-case.md) for the matching test against the inspected Polymarket NegRiskAdapter. It reimplements that contract's split, merge and convert operations from source, searches every legal conversion the adapter permits, and reports parity where the adapter nets and a gap where it cannot. No Solidity is executed and no deployed market is measured.

The [follow-up](../research/competitive-followup.md) extends the mathematical bound beyond fixed inventory, explains user economics and supplies pending read-only Deribit request payloads. The exact checker needs no numerical-solver dependency.

The workflow examples correspond to [quote-workflow.md](../quote-workflow.md). They verify wallet debits/credits, resulting profiles, one listed-option approximation and the categorical funding alternative. They do not submit quotes or orders to any venue.

Amounts are integers, rational strings or `fractions.Fraction`; floats are rejected. A positive `payment` pays another participant. A positive `cash_flow` deposits wallet funds; a negative value withdraws them. A payout delta changes the complete final cash entitlement, including its explicitly specified VOID value.

The ledger has no matching, price discovery, concurrent database transactions, production identity checks or real custody. It uses exact rational settlement without token-unit rounding. Python process access is trusted. The account minima and zero-sum changes are a mathematical prototype, not a deployable financial contract.

The comparison deliberately includes competent alternatives: exact netting matches the final funding requirement, atomic netting matches package funding, sliced sequential trades reduce temporary cash, and account-local tables avoid global table growth. None of the simulation's activity is evidence of demand.
