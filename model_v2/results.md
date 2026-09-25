# V2 kernel research results

Recorded on 25 September 2026. Inputs and machine-readable results: [results.json](results.json). Reproduction commands and implementation boundaries: [README.md](README.md).

## Outcome

The current validation run passed **54 v2 tests and 28 earlier-model tests (82 total)**. The v2 suite includes 1,000 randomized general-graph comparisons and 250 randomized suffix-optimization comparisons against independent exhaustive evaluation, as well as complete ledger lifecycle regressions.

The larger synthetic replay ran **200 seeded lifecycles × 100 generated steps**:

| Measure | Result |
|---|---:|
| Accepted replay actions | 14,274 |
| Rejected actions with unchanged complete ledger snapshots | 2,792 |
| Skipped requests for already resolved covers | 2,934 |
| Path-level funding/conservation audits | 448,826 |
| Markets ending with zero escrow after all claims | 200 / 200 |

Generated actions include trades, fees, withdrawals, deliberately missing approvals or insufficient funding, provisional report corrections, final facts during the trading sequence, lazy materialization and complete-position sales. End-of-run observation finalization and claims add lifecycle operations beyond the generated-step count. Every audited history reconciles all account payouts to escrow and wallets plus escrow to the initial token endowment.

These are synthetic accounting stress tests. There is no historical data feed, calibrated maker pricing, executable spread or trading-strategy return claim. Passing sampled cases is not a mathematical proof or security audit.

## Economic examples reproduced

- **Rainfall:** mutually exclusive 100-unit obligations sold for 30 and 50 need a 20-unit maker contribution, compared with 120 if funded separately. A provisional winning report releases nothing. Contractual finalization makes the standalone buyer's 100 withdrawable, and later cancellation does not reclaim it under this example's policy.
- **Football:** the specified window-goal and exact-final-score covers need a 40-unit maker contribution, compared with 140 separately. This depends on the exact state and exception rules, not a correlation assumption.
- **Free-moving prices:** the same range at two checkpoints can pay twice, requiring 200 gross backing. The engine does not invent a cross-time offset.
- **Exits:** halving cover holdings alone can make an account with negative cash insolvent. A representable sale of half the entire funded profile, including its cash component, preserves the seller's funding when proceeds cover the fee.

All prices are fixed example inputs. These examples demonstrate accounting effects, not lower customer prices or a superior live-market execution route.

## Performance improvement implemented

The general evaluator checks graph edges. The optimized evaluator detects suffix successor sets and reuses suffix minima/maxima only when the account has no pair-dependent edge cost on that layer. Otherwise it falls back to the general evaluator.

Warm single-account, single-terminal-cover evaluations on the recorded machine:

| Graph | Values/checkpoint | Checkpoints | Edges | General ms | Optimized ms | Speedup |
|---|---:|---:|---:|---:|---:|---:|
| free | 10 | 4 | 344 | 0.354 | 0.046 | 7.7× |
| free | 40 | 6 | 8,246 | 7.319 | 0.179 | 40.9× |
| free | 100 | 8 | 70,808 | 66.595 | 0.652 | 102.1× |
| monotone | 10 | 4 | 209 | 0.202 | 0.039 | 5.2× |
| monotone | 40 | 6 | 4,346 | 3.933 | 0.176 | 22.4× |
| monotone | 100 | 8 | 36,158 | 32.589 | 0.612 | 53.3× |

The largest free graph represents up to 10^16 normal paths without enumerating them. The benchmark records construction and structural-classification costs separately. These numbers do not measure complete trade throughput, many-cover portfolios, oracle updates, storage costs or EVM gas. General edge-dependent accounts may receive much smaller gains or none.

## Improvements identified while implementing

### 1. Finality is part of the payout definition

A progressive checkpoint can create an irrevocable payment. An end-finality observation cannot use that same payout graph if later cancellation is meant to erase provisional winnings. The model now provides separate builders and tests both. The end-finality builder retains sufficient history, exposes its state-space cost and rejects oversized inputs.

**Product implication:** users must see whether a payment is merely indicated or contractually final. A generic “confirmed” label without contractual meaning is insufficient.

### 2. Resolution needs its own resource budget

Bounding one trade's work does not guarantee that resolving all admitted covers is affordable. Cover admission now reserves a conservative catalogue-finalization work budget.

**Next improvement:** evaluate incremental dependency indexes so a fact only revisits covers whose payout range could change. Verify against the full-catalogue reference before using this to enforce limits.

### 3. Net arithmetic is not enough

Large factors can cancel in a portfolio, while individual resolved-cover credits still exceed the configured integer bound. The model adds an explicit conservative arithmetic envelope so materialization cannot introduce this trap.

**Tradeoff:** equivalent but unnecessarily verbose representations can hit complexity/arithmetic limits earlier. A future canonical simplifier could improve representability without changing the funding floor. It must preserve exceptional payouts too.

### 4. State design determines both precision and cost

Checkpoint-only values support many useful covers. Event-order or nonadjacent conditions require sufficient remembered state. The reference demonstrates that extension through history augmentation, and also demonstrates why unrestricted generality can grow exponentially.

**Next improvement:** replace full history with minimal sufficient counters or finite-state machines for selected cover families. Check the compressed and uncompressed payouts and minima on every small test history.

### 5. Solvency does not make standing liquidity firm

Orders can share a maker's account and retain netting, but another fill can consume capacity. The ledger safely rejects the later fill; it does not guarantee liquidity or prevent economic losses from stale quotes.

**Next research step:** a separate execution simulation with competing fills, quote cancellation latency and capacity policies. Pricing/spread and latency assumptions must be stated before measuring maker returns or fill quality.

## What to do before a contract implementation

1. Choose a concrete real-world observation adapter and prove that its state encoding preserves the supported payouts, including corrections, overflow and cancellation.
2. Define portable transaction/authorization fixtures in addition to the current funding fixtures; specify actual signatures, replay domains and source finalization authority.
3. Benchmark the intended state graph, cover menu and worst-case account/batch on the target execution environment. Python timings do not establish gas affordability.
4. Implement one contract operation at a time against the same fixtures and differential tests, then exercise token-transfer and adversarial-call behavior.
5. Separately test demand, executable quote quality and maker economics. The accounting model cannot answer those commercial questions.
