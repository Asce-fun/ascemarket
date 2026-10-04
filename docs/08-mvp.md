# Smallest credible prototype and settlement lifecycle

## Objective

Prove that many gross bounded covers on one event can be funded at their exact worst aggregate payout, and determine whether the required operations are better served by native CTF or internal accounts. Do not claim a custom netting advantage merely because both beat separate per-cover backing.

## Locked scope

- One supported USDC token, one chain selected later, no reserve lending.
- One scalar terminal observation and one expiry; exact historical source selection defined before deployment.
- Five to ten normal atomic states, plus an explicit failure state; no mutable grid.
- Integer per-state bounded payouts and exact lot sizing.
- One maker, many prepaid buyers, fees explicit if enabled.
- No cross-event or cross-expiry offsets, marks, statistical risk reduction or maintenance liquidation.
- Maker quote inputs; no automatic pool or unproven AMM.
- Simple declared oracle trust model; a test resolver is acceptable only when labeled as such.

## What exists after this research

The requested first deliverable is complete as documents, simulations, scenario/invariant tests and local native CTF comparisons. No production Solidity or new prototype Solidity is added. `contracts/` retains its existing design documents.

| Artifact | Purpose |
|---|---|
| `docs/00`–`09` | Conclusions, model, architecture, examples, security and decisions |
| `simulations/collateral_engine.py` | Independent direct-state math and CTF backing certificates |
| `simulations/portfolio_examples.py` | Execute the examples through the existing ledger |
| `tests/test_state_clearing.py` | Differential/action/settlement regression coverage |
| `research/ctf/run-state-clearing-baseline.cjs` | Execute unequal curve baskets on existing CTF |
| `research/*/README.md` | Evidence boundaries and primary-source comparisons |

## Settlement lifecycle

| Step | Required behavior |
|---:|---|
| 1. Create event | Bind collateral, measurement source, timestamp/sampling, units, precision, finality, deadlines and failure payouts |
| 2. Lock state space | Store ordered boundaries/endpoint conventions and INVALID; hash economic terms; prepare common CTF condition for A |
| 3. Start trading | Activate only validated cover templates/definitions on this domain; require cutoff before observation becomes exploitable |
| 4. Quote and trade | Maker prices requested reusable cover or basket; parties authorize actual payouts, consideration, fees and maximum debit |
| 5. Check funding | A delivers native funded inventory; B checks every candidate account vector against all funded states |
| 6. Modify/close | Quote another atomic trade; preserve history and check residual portfolios; reject unaffordable exits |
| 7. Observe and resolve | Stop new trading at cutoff; authenticate historical observation; provisional/disputed data is not final |
| 8. Determine winning state | Map the final value exactly, including equality/tails; finalize allowed state once |
| 9. Net settlement | A: CTF redeems owned positions. B: evaluate `c+p[k*]`; no gross collection waterfall |
| 10. Release surplus | Maker receives its remaining final entitlement; no earlier assumption that premiums were profit |
| 11. Withdraw | Each owner pulls its payable funds exactly once; no global holder loop |

**Oracle delay:** funded states and backing remain unchanged. Stop new trading; free collateral may still be withdrawn if the same invariant permits it. Do not charge newly invented running fees against locked backing. Funds needed for contingent payouts remain unavailable until finality or the precommitted timeout.

**Dispute:** retain every contractually possible result and the failure branch. Do not prune to a proposed answer. Once final, neither an adapter correction nor an administrative intervention may restore discarded possibilities after money has been released.

**Timeout:** select the pre-funded INVALID state under a deterministic deadline rule. Resolve the exact boundary race between a timely final result and timeout; use one irreversible transition. The example's zero-payout rule is only a research choice; refund policies change backing and must be specified before trading.

## Prototype comparison, after the research phase

First build the smallest authenticated CTF executor on the common domain, reusing the existing oracle-adapter design. Demonstrate arbitrary vectors as baskets, direct cover purchase, partial close, every terminal payout and all-or-nothing failure.

If the necessary account workflows motivate B, implement one event-scoped clearing house plus the same final observation adapter. Keep export disabled initially. Compare identical action sequences and cashflows against A. Required measurements include quote execution, storage initiation, partial close, claim, oracle delay and any later export path. Use conservative deployment gas limits; the present operation estimates are not that benchmark.

This staged comparison avoids building a second custody system to rediscover a complete set. It also makes the decision concrete: B must win a necessary operation, measured cost or supported representation under matched guarantees.

## Research reproduction

From the repository root:

```sh
python3 -B -m simulations.portfolio_examples
python3 -B -m unittest model_v2.test_kernel model_v2.test_netting_review -q
python3 -B -m unittest discover -s tests -p 'test_state_clearing.py' -q
```

For local EVM evidence, use already installed dependencies or the pinned lockfile:

```sh
npm ci --prefix research/ctf --ignore-scripts --no-audit --no-fund
node research/ctf/run-evidence.cjs
node research/ctf/run-state-clearing-baseline.cjs
```

`ASCEMARKET_CTF_DEP_ROOT` may select an existing dependency directory. This review used `/private/tmp/ascemarket-ctf-evidence`; no dependency installation was needed. Ganache's unavailable native bindings fell back to JavaScript; the assertions completed. No live network transactions or funds were used.

## Acceptance and stop conditions

The accounting prototype passes only if all allowed states settle exactly, unsuccessful operations are atomic, premiums/fees reconcile, cache and raw evaluation agree, and removed hedges cannot create deficits. Showing `11,000 < 26,000` alone is insufficient.

The product experiment passes only if the maker can support recurring desired covers at acceptable all-in quotes and funded lifecycle cost. Stop expanding custom clearing if A already supports those operations cheaply or actual portfolio maxima coincide. Neither more curve IDs nor a more elaborate oracle answers the demand question.
