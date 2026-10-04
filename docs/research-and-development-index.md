# AsceMarket

A marketplace for reusable protection: buy a cover, reshape it using compatible liquidity, and redeem its funded payout.

## State-aware clearing research

Start with [the research verdict and deliverable index](00-thesis.md). The new report reviews the existing work, derives exact same-event solvency, works three numerical examples plus premium accounting, and compares native CTF with internal clearing accounts.

**Finding for the restricted finite-state model:** three covers with 26,000 USDC in summed payout caps need 11,000 backing. A shared CTF condition reproduces that same optimum. That remains a comparison baseline. Following clarification of flexible payoff shapes and broad events, the current prototype specification investigates internal clearing accounts; it does not claim new complete-set mathematics.

- [Existing-system analysis](01-ctf-analysis.md)
- [Pinned Polymarket exchange review and Asce reuse decisions](../research/polymarket-exchange-review-2026-10-01.md) — includes 265 passing upstream V2 tests and shared-condition examples.
- [Accounting model](02-clearing-model.md) and [proof](03-math.md)
- [Architecture, representations and gas](04-architecture.md)
- [Solvency checks](05-solvency-invariants.md) and [worked examples](06-examples.md)
- [Security](07-security.md), [MVP/reproduction](08-mvp.md), [open decisions](09-open-questions.md)
- [Primary-source register](../research/state-clearing-sources.md)
- [Python results](../simulations/results.json) and [new local CTF control](../research/ctf/state-clearing-baseline-results.json)

```sh
python3 -B -m simulations.portfolio_examples
python3 -B -m unittest discover -s tests -p 'test_state_clearing.py' -q
```

No new Solidity was written for this research. The existing CTF and graph-kernel artifacts remain below with their evidence and implementation boundaries.

## Main implementation reference

**Start with [the AsceExecutor local prototype specification](../contracts/asce-executor-prototype-spec.md).** It is the current review document for contract responsibilities, signed orders, stored state, payoff encoding, rounding-aware clearing and settlement. Implementation requires the user's green light; no new Solidity has been written.

The proposed local prototype has one event and observation, bounded piecewise-linear curves with explicit jumps, immutable USDC-compatible collateral, an internal signed-position ledger and a mock oracle. Earlier native CTF and graph-manager architectures remain comparison research rather than additional implementation dependencies.

- [Product vision](../AsceMarket.md) — broader ambition; the contract reference controls MVP implementation scope.
- [Restricted CTF architecture and historical handoff](../contracts/ctf-cover-architecture.md)
- [Marketplace and CTF test findings](../research/cover-marketplace-test-findings.md)
- [Product and quantitative review](../research/cover-marketplace-review-2026-09-30.md)
- [Local CTF evidence runner](../research/ctf/run-evidence.cjs)

The current artifacts are designs and research fixtures, not deployed or audited production contracts. The main reference explicitly separates tested constructions from required implementation work and deployment choices.

## Custom kernel research

These earlier documents describe broader signed-account and graph-margin research. The current local prototype specification defines the proposed implementation's scope and custody semantics.

- [Generic v2 kernel specification](../v2-kernel-spec.md)
- [AsceManager design](../contracts/ascemanager-design.md)
- [Graph verifier design](../contracts/graph-verifier-design.md)
- [Earlier order matching and netting design](../v2-order-matching-and-netting.md)
- [Netting safety review](../research/netting-safety-review.md)
- [Python model and reproduction instructions](../model_v2/README.md)
- [Kernel tests and synthetic findings](../model_v2/results.md)
- [Portable kernel fixtures](../model_v2/fixtures.json)

Run the reference-model tests:

```sh
python3 -B -m unittest model_v2.test_kernel model_v2.test_netting_review -q
```

For native CTF research reproduction, follow [the test findings](../research/cover-marketplace-test-findings.md#reproduce-the-evidence). These checks do not establish customer demand, maker profitability, production security or deployment gas limits.
