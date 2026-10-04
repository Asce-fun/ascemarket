# AsceMarket v2 reference model

Executable research implementation of the finite-state baseline in [the v2 kernel specification](../v2-kernel-spec.md). It uses Python's standard library and exact integer token base units. It is a reference for accounting and verification, not a deployed exchange, wallet integration or audited contract.

## Run

From the repository root:

```sh
python3 -B -m unittest model_v2.test_kernel model_v2.test_netting_review -q
python3 -B -m model_v2.research --seeds 200 --steps 100
```

The earlier `model/` implementation has been removed. Historical combined test results remain recorded in the research report; the command above runs the current v2 suite.

Research output is written to [results.json](results.json). Read [results.md](results.md) for measured findings and their limits. The random seed, scenario inputs and source hashes are recorded; timings depend on the machine. No dependencies need installation.

## What exists

| File | Responsibility |
|---|---|
| [schema.py](schema.py) | Immutable markets, exact node/edge covers, signed accounts, canonical identities and resource limits |
| [oracle.py](oracle.py) | Independent exhaustive path enumeration and direct raw-cover evaluation; not an external data oracle |
| [verifier.py](verifier.py) | Combined-account min/max computation, worst-case witness and proven-structure suffix optimization |
| [ledger.py](ledger.py) | Atomic batches, fees, wallets, facts, epochs, lazy resolution, withdrawals, package/order authorization assertions and claims |
| [examples.py](examples.py) | Reusable graph/payout builders, rainfall/football/price scenarios and end-finality history augmentation |
| [test_kernel.py](test_kernel.py) | Deterministic regressions, independent differential tests and stateful replay checks |
| [test_netting_review.py](test_netting_review.py) | Targeted cross-cover funding, hedge-removal and exhaustive signed-portfolio regressions |
| [research.py](research.py) | Synthetic lifecycle backtesting and warm/general-verifier benchmarks |
| [fixtures.json](fixtures.json) | Language-neutral market/account inputs with explicitly stated expected extrema |
| [fixtures.py](fixtures.py) | Deliberate fixture regeneration, independent of the optimized answer |

There is no event-specific accounting in the ledger. Builders translate domain rules into the same immutable graph and payout-factor language. Predicates used by the example constructors run during table construction; they are not executable trading hooks.

## Example

```python
from model_v2.examples import rainfall

ledger, values, noon_cover, evening_cover = rainfall()
assert ledger.net_deposits["maker"] == 20
assert ledger.escrow == 100
ledger.audit()  # exhaustive funding, entitlement and token reconciliation

ledger.post_report(1, {2}, "resolver")  # reported noon value 12
assert ledger.bounds("buyer_a").minimum == 0
ledger.confirm({1: {2}}, "resolver")    # contractually final, not merely reported
assert ledger.bounds("buyer_a").minimum == 100
ledger.audit()
```

The integers in these examples use a simple unit denomination. Production USDC values would be encoded in its configured base units; no token decimals are assumed by the kernel.

## Exact semantics

- Account payout is signed cash plus signed cover lots. Cash alone is neither a wallet balance nor the withdrawable amount.
- Funding uses every remaining graph path, including explicitly modeled cancellation, failure and overflow branches.
- Provisional reports pause trading and advance the epoch, but do not prune funding support.
- Final facts intersect support; contradictory or empty constraints reject without changing ledger state. Existing final constraints never widen.
- Resolved cover payouts can be materialized lazily into account cash exactly once. Other obligations can still prevent withdrawal.
- All external transfers go between an account and its own simulated wallet. Deposits consume available wallet funds. Premiums and fees remain explicit internal transfers.
- Packages authorize exact payloads and revisions. Standing orders authorize bounded fills with current funding checks, cumulative quantities, expiry and cancellation. The model supports zero-fee standing orders; package fees are implemented.
- Complete-position sales transfer a fraction of both cash and holdings. A fraction must be exactly representable. No independently rounded partial exit is executed.
- Claims account for previous withdrawals and credits. Every simulated token is reconciled through wallets plus escrow.

## Progressive versus end finality

`checkpoint_market` constructs a progressive market in which selecting a normal checkpoint state means that checkpoint is **contractually finalized**. Entering its absorbing exceptional state cancels unresolved covers and preserves earlier finalized payments. Observation reports alone do not select such states.

A multi-checkpoint end-finality market cannot reuse those cancellation rules. Earlier observed winnings remain provisional and may disappear on terminal cancellation. `deferred_history_market` retains the necessary history in its state; `deferred_cover` evaluates the payout only at the terminal layer. This also demonstrates more complex bounded path conditions on the same generic verifier.

History augmentation can grow exponentially. The builder enforces state/edge limits and refuses oversized inputs. A domain-specific sufficient statistic or finite-state automaton can compress that history later, but must pass the same exhaustive equivalence tests. The reference does not pretend that every path function is cheap.

An example's finite value domain is explicit. The progressive builder's exceptional branch also supplies a defined out-of-domain/failure route; it never rounds an actual score into an ambiguous “7+” bucket. Real source-to-state adapters must validate this mapping before deployment.

## Optimizations and resource safety

The verifier always has a general edge-by-edge recurrence. An optional fast path applies only where:

1. The immutable graph proves that each state's successors form a suffix of the next layer.
2. The combined account has no nonzero pair-dependent edge cost on that transition layer.
3. Scanning the suffix is no more work than scanning the existing edges.

It reuses suffix minima/maxima, including holes caused by final facts and unreachable states. Otherwise the verifier uses general adjacency. Both paths are checked against exhaustive evaluation. Benchmarks report one-time graph/classification costs separately from repeated evaluation.

Arithmetic uses an explicit absolute factor budget: absolute cash plus the sum of absolute lot-weighted factor entries must fit the configured bound. This is conservative but ensures future lazy materialization cannot overflow merely because previously offsetting factors are credited separately. A representation can exceed this budget even if its economic net payout is small; that is an explicit admission/representation limit, not additional required collateral.

Cover admission also reserves a worst-case work budget for catalogue-wide fact finalization. An affordable trade must not create a market whose later resolution cannot be processed within its declared model limits. These limits are research guardrails, not calibrated on-chain gas limits.

## What the tests establish

Small-space exhaustive evaluation and randomized comparisons check the algorithm. Stateful replays check atomicity, funding, conservation, correction handling and eventual claims over generated transaction sequences. Named regressions cover the counterexamples identified during design review.

This is **synthetic kernel backtesting**. It does not use historical event feeds, real maker quotes, a calibrated pricing model or realistic network latency. It cannot establish demand, achievable spreads, maker profitability, an economic advantage over a live competitor, or production safety.

The benchmark's large-state path counts are upper bounds for normal paths; its timed runs are verifier evaluations, not complete trades. No exhaustive enumeration is attempted for those large cases. Their arithmetic result is compared between the optimized and general algorithms.

## Remaining implementation boundaries

- `Approval`, `approve()` and actor strings are harness assertions. Anyone controlling the Python process can construct them. There are no real signatures or access-control boundaries.
- Funds are simulated. There are no contracts, token callbacks, custody, persistence, concurrent database writes or chain reorganization handling.
- Operations are serialized in one process. Order-race tests model interleavings, not a production concurrent matcher.
- Graphs and cover definitions must explicitly encode valid observations and all exceptional semantics. The kernel cannot establish whether a real-world source report is true or whether an observation adapter omitted a physically possible history.
- The finalizer directly supplies validated graph constraints. Real challenge periods, automated deadlines, proof verification, source adapters and conflict adjudication remain to be implemented.
- Market schemas currently use node masks for final constraints. More involved final facts require sufficient augmented state or a future validated edge-constraint interface.
- The cover language is the finite node/edge baseline. It has no dynamic verifier plugin loader, natural-language compiler, order reservation system, cross-market margin or live price-discovery service.
- The portable fixtures currently cover funding evaluation. Complete contract execution/authorization wire formats still need definition; the Python digest is not an EIP-712 specification.

The next implementation decision should follow measured source-to-state requirements and contract benchmarks, not the assumption that a passing Python model is ready for deployment.
