# State-clearing source register

Reviewed 30 September 2026. Sources are primary protocol code, official documentation and standards. Links to mutable branches identify what was inspected on this date; they do not pin a deployed version. No onchain deployment addresses or current bytecode equivalence were established.

| Source | Claim supported | Evidence boundary |
|---|---|---|
| [CTF 1.0.3 developer guide](https://conditional-tokens.readthedocs.io/en/latest/developer-guide.html) | Native conditions, collections, partitions, scalar/combinatorial operations | Published framework semantics, not Asce event truth |
| [ConditionalTokens.sol](https://raw.githubusercontent.com/gnosis/conditional-tokens-contracts/master/contracts/ConditionalTokens.sol) | Preparation/reporting and split/merge/redemption implementation | Mutable upstream source; local tested package is separately versioned and hashed |
| [CTHelpers.sol](https://raw.githubusercontent.com/gnosis/conditional-tokens-contracts/master/contracts/CTHelpers.sol) | Identifier and parent collection construction | Use native helpers, not invented hashes |
| [Legacy CTF Exchange](https://github.com/Polymarket/ctf-exchange) | Archived status and V2 migration notice | Legacy is not current deployment evidence |
| [Legacy Trading.sol](https://raw.githubusercontent.com/Polymarket/ctf-exchange/main/src/exchange/mixins/Trading.sol) | Transfer, mint and merge matching routes | Source semantics only |
| [V2 Trading.sol](https://raw.githubusercontent.com/Polymarket/ctf-exchange-v2/main/src/exchange/mixins/Trading.sol) | Batched native operations and binary ID checks | Source inspection; not runtime/deployment audit |
| [Polymarket positions](https://docs.polymarket.com/trading/positions/how-positions-work) | Current documented position lifecycle and collateral denomination | Product documentation, not independently verified deployment |
| [Polymarket negative risk](https://docs.polymarket.com/concepts/negative-risk) | Linked contractual conversion | Declared compatible event rules |
| [Polymarket collateral return](https://docs.polymarket.com/trading/combos/collateral-return) | Compatible Combo decomposition and residual collateral extraction | Does not establish unrestricted scalar clearing support |
| [Kalshi collateral return](https://help.kalshi.com/en/articles/13823816-collateral-return) | Guaranteed-payout release, eligibility and sale restrictions | No authenticated portfolio/exit test |
| [DIVA position creation](https://docs.divaprotocol.io/diva-app/create-position-tokens) | Configurable paired contingent claims | No account-wide clearing comparison executed |
| [CME SPAN](https://www.cmegroup.com/clearing/files/span-methodology.pdf) | Risk arrays and portfolio/spread methodology | Scenario margin, not exhaustive terminal funding |
| [CME SPAN 2](https://www.cmegroup.com/clearing/risk-management/span-overview/span-2-methodology.html) | Historical/stress, liquidity and concentration framework | Different risk horizon/service |
| [OCC customer PM](https://www.theocc.com/risk-management/customer-portfolio-margin) | TIMS-based portfolio calculation | Customer framework, distinct from STANS |
| [OCC STANS](https://www.theocc.com/risk-management/margin-methodology) | Monte Carlo, expected shortfall, two-day horizon and intraday calls | Statistical risk coverage |
| [Deribit PM](https://support.deribit.com/hc/en-us/articles/25944756247837-Portfolio-Margin) | Shock portfolio methodology and liquidation conditions | No authenticated margin measurements |
| [EIP-2200](https://eips.ethereum.org/EIPS/eip-2200), [EIP-2929](https://eips.ethereum.org/EIPS/eip-2929), [EIP-3529](https://eips.ethereum.org/EIPS/eip-3529) | Storage/reset/cold access and refund rules | Operation estimates exclude full transaction costs and target-chain differences |
| [ERC-6909](https://eips.ethereum.org/EIPS/eip-6909) | Multi-token interface | Does not define solvency or collateral |

## Independent work versus source claims

The exact account invariant, inductive proof, CTF atomic allocation theorem, cashflow-sensitive lifecycle floor and export-account derivations are independently worked through in `docs/02`–`05`. They should be assessed against their explicit assumptions rather than treated as claims copied from a protocol's marketing.

Numeric premiums and payoff curves are synthetic. USDC base-unit scaling is a simulation convention. The CTF parity example is executed locally, and its package/source hashes are in the result JSON. Existing historical comparisons referencing removed v1 `model/` modules were reviewed as documents, not rerun or promoted to new findings.

## Reproduction results in this review

- `model_v2.test_kernel` and `model_v2.test_netting_review`: 63 tests pass.
- `tests/test_state_clearing.py`: 20 tests pass, including seeded action and state/claim-order checks.
- Existing `research/ctf/run-evidence.cjs`: 160 assertions, seven expected reverts, 26 redemption scenarios.
- New `research/ctf/run-state-clearing-baseline.cjs`: 63 assertions, 12 redemption scenarios.

These records are not a formal implementation audit or evidence of market profitability.
