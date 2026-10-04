# CTF evidence and version boundaries

The repository already contained `run-evidence.cjs`, `EvidenceHelpers.sol` and the pinned npm dependency lockfile. The old runner was reproduced: 160 assertions, seven expected reverts and 26 terminal redemption scenarios.

The new `run-state-clearing-baseline.cjs` adds an unequal-payoff-vector comparison without writing new Solidity. It uses the same published CTF 1.0.3 and existing test currency. Results: 63 assertions, 12 redemption scenarios, 26,000 summed caps backed by 11,000; a half-C buyback reduces backing by 500 and releases 100 after consideration.

```sh
node research/ctf/run-evidence.cjs
node research/ctf/run-state-clearing-baseline.cjs
```

Install instructions are in [the MVP research guide](../../docs/08-mvp.md#research-reproduction). Both runners support `ASCEMARKET_CTF_DEP_ROOT` and use an in-process local EVM. They make no live chain transactions.

The new runner is a **prefunded native-inventory mechanics control**. Separate test-actor transfers collect synthetic premiums and deliver baskets. It does not validate real atomic-trade authorization, buyer-funded general-vector issuance, wrapper custody, production oracles or current Polymarket bytecode. Gas receipts use Ganache 7.9.2 / Shanghai / Solidity 0.5.17 with optimizer runs 200 and include source hashes. [New results](state-clearing-baseline-results.json), [old results](ctf-evidence-results.json).

The [CTF analysis](../../docs/01-ctf-analysis.md) distinguishes underlying Gnosis capabilities, legacy Polymarket exchange mechanics, inspected V2 source and current product documentation. A published package test is not a deployment verification.
