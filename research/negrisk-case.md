# A concrete competitive test: a boundary the partition cannot express

Research date: 18 September 2026. This is a source-level architecture comparison and an
executable accounting experiment, not a live trading comparison.

## Verdict

**The inspected NegRiskAdapter matches this ledger exactly whenever the traded claims are
declared questions of one neg-risk market. It provides no relief at all once an offset
spans two markets, and a boundary inside an existing question always requires a second
market.**

The useful distinction is not categorical versus numeric. It is **whole-observation
funding versus per-market funding**. The adapter nets across one declared partition; this
ledger nets across everything settling on the same observation, including boundaries
introduced after the first trade.

This is a narrow, verified result about the inspected source. It establishes no advantage
in price, liquidity or cost, and it does not claim Polymarket users want the capability.

Reproduce with `python3 -B -m model.negrisk_case`; recorded output in
[negrisk-case-results.json](negrisk-case-results.json).

## 1. The matched exposure

One numeric terminal observation of ETH, one settlement asset, shared by both systems.

A neg-risk market **M** is declared with the partition:

| Question | Pays 1 when |
|---|---|
| Q0 | x < 3000 |
| Q1 | 3000 ≤ x < 3200 |
| Q2 | x ≥ 3200 |

A maker then does two things, in order:

1. Sells one unit of Q0 and one unit of Q2. These are mutually exclusive.
2. Sells one unit of a claim paying on **[3000, 3100)** — a boundary at 3100, strictly
   inside Q1.

Premiums are zero on both sides so the comparison isolates backing. Both systems are
measured on the cash the maker must supply, and the resulting terminal payoffs are
checked for equality.

## 2. What the named alternative actually implements

Inspected `Polymarket/neg-risk-ctf-adapter` at commit `f78b35b0863b4308a431ca307d06f49b2ea65e78`, not its product description.

- [`splitPosition(conditionId, amount)`](https://github.com/Polymarket/neg-risk-ctf-adapter/blob/f78b35b0863b4308a431ca307d06f49b2ea65e78/src/NegRiskAdapter.sol#L124): the caller
  supplies `amount` collateral and receives `amount` YES and `amount` NO.
- [`mergePositions(conditionId, amount)`](https://github.com/Polymarket/neg-risk-ctf-adapter/blob/f78b35b0863b4308a431ca307d06f49b2ea65e78/src/NegRiskAdapter.sol#L158): the inverse.
  It requires both sides **of the same condition**.
- [`convertPositions(marketId, indexSet, amount)`](https://github.com/Polymarket/neg-risk-ctf-adapter/blob/f78b35b0863b4308a431ca307d06f49b2ea65e78/src/NegRiskAdapter.sol#L244):
  burns the caller's NO tokens named by `indexSet`, returns one YES for each complement
  question, and releases
  [`(popcount(indexSet) - 1) * amountOut`](https://github.com/Polymarket/neg-risk-ctf-adapter/blob/f78b35b0863b4308a431ca307d06f49b2ea65e78/src/NegRiskAdapter.sol#L335) collateral.
  It reverts on [`questionCount <= 1`](https://github.com/Polymarket/neg-risk-ctf-adapter/blob/f78b35b0863b4308a431ca307d06f49b2ea65e78/src/NegRiskAdapter.sol#L249) and on an
  [`indexSet` wider than that market's `questionCount`](https://github.com/Polymarket/neg-risk-ctf-adapter/blob/f78b35b0863b4308a431ca307d06f49b2ea65e78/src/NegRiskAdapter.sol#L251).
- [`_prepareQuestion`](https://github.com/Polymarket/neg-risk-ctf-adapter/blob/f78b35b0863b4308a431ca307d06f49b2ea65e78/src/modules/MarketDataManager.sol#L74) adds a question to an
  existing market, but only the market's own oracle may call it
  ([`OnlyOracle`](https://github.com/Polymarket/neg-risk-ctf-adapter/blob/f78b35b0863b4308a431ca307d06f49b2ea65e78/src/modules/MarketDataManager.sol#L79)), and the index is a
  `uint8`, capping a market at 256 questions.

**Every collateral-moving operation takes a single `conditionId` or a single
`marketId`.** There is no operation that reads balances across two markets.

This establishes the inspected code's rules. No Solidity was executed and no deployed
market was measured.

## 3. Give the alternative its best moves

The model does not assume a naive allocation. At each step it searches every legal
`indexSet` in the relevant market and takes the largest release available.

**Step 1 — parity.** Q0 and Q2 are both declared questions of M, so conversion applies:

| | This ledger | Adapter |
|---|---:|---:|
| Backing after step 1 | **1** | **1** |

The adapter splits twice (2 collateral in), sells both YES, then converts `indexSet =
{Q0, Q2}`, which releases 1 and returns YES`Q1`. Net backing 1, holding `1(3000 ≤ x <
3200)`. This ledger funds `max(0, -inf(-Q0 - Q2)) = 1` and holds the same profile. The
model checks the two terminal payoffs are equal, and they are.

**There is no advantage here, and the write-up should not claim one.**

**Step 2 — the gap.** The claim on [3000, 3100) is not a question of M and cannot become
one: adding it would break the partition, because it and Q1 would both pay when
3000 ≤ x < 3100. It therefore requires a second market N.

| | This ledger | Adapter |
|---|---:|---:|
| Additional backing at step 2 | **0** | **1** |
| Best convert release available in N | — | **0** |
| **Total backing** | **1** | **2** |

In N the maker holds a single NO position, so every legal `indexSet` gives
`popcount - 1 = 0` and releases nothing. The YES`Q1` held in M cannot help, because no
operation spans both markets.

## 4. Where the extra collateral goes

The model checks what the adapter is left holding. The difference between the two
terminal profiles is **the constant 1** — verified constant, with an empty knot list, and
equal to the measured gap.

The adapter's extra unit is therefore not lost. It sits as a flat payoff the maker cannot
release, because merging requires both sides of one condition and the maker holds YES in
M and NO in N. That trapped constant *is* the offset this ledger recognises.

## 5. The gap is unbounded in the number of refinements

Each further boundary inside the currently held interval needs another market, and each
new market contains a single NO position, which converts to nothing:

| Refinement | Boundary added | This ledger | Adapter |
|---:|---:|---:|---:|
| 1 | 3100 | 1 | 2 |
| 2 | 3150 | 1 | 3 |
| 3 | 3175 | 1 | 4 |
| 4 | 3187 | 1 | 5 |

Each new obligation is dominated by the profile the maker already holds, so this ledger
requires nothing further. The adapter's total grows by one per refinement.

## 6. Why no rearrangement closes it

`splitPosition` and `mergePositions` act on one `conditionId`. `convertPositions` acts on
one `marketId` with an `indexSet` bounded by that market's `questionCount`. No operation
moves collateral between markets.

The caller's requirement is therefore **additively separable across market identifiers**,
and its minimum is the sum of the per-market minima. This ledger instead funds a single
infimum over the combined profile. Whenever an offset spans a market boundary, the
separable sum strictly exceeds the joint infimum.

Reorganising positions cannot help, because the separation is in the operation set rather
than in the allocation.

## 7. What this does not establish

- No Solidity was executed and no deployed Polymarket market was measured.
- Nothing about prices, spreads, liquidity or total cost on either venue. Polymarket's
  liquidity and token composability are real advantages this comparison does not weigh.
- Premiums are zero on both sides. Real premiums change the cash comparison.
- It assumes an oracle would list the refined market at all. If none does, the exposure
  is unavailable on that venue rather than merely more expensive.
- Token precision and Solidity rounding are not modelled.
- VOID and invalid-resolution semantics are excluded; only numeric terminal payoffs are
  matched.
- It does not establish that anyone wants to trade a boundary introduced after a market
  was declared. That remains the unmeasured demand question.
