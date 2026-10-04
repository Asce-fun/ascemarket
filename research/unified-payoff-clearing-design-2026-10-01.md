# Unified payoff representation and clearing state

Proposal, 1 October 2026. This incorporates the user's latest requirements: one immutable protocol collateral token, protocol-level failure handling, a broad event supporting different future observation times, and mixed payoff shapes. It is a design input, not implemented Solidity or a claim that the rounded portfolio minimum has already been proven.

## Recommendation

Use **one bounded piecewise-affine payoff representation with explicit jumps**, rather than one onchain evaluator per commercial cover label. Binary, range and scalar are builder/UI descriptions that compile to this common representation.

Retain separately defined observations: the measurement determines the input; the curve determines payment. This representation is a useful language for one scalar input and finite category codes. It is not a universal formula for arbitrary functions of several inputs or an entire price history.

## Mathematical form

A piecewise-affine function with finitely many jumps and specified boundary values can be written as:

\[
h(x)=a+bx+\sum_j c_j\max(x-k_j,0)
       +\sum_j d_j\mathbf 1_{x\geq k_j}
       +\sum_j e_j\mathbf 1_{x>k_j}.
\]

The hinge terms change slopes. The indicator terms change values at thresholds. Both strict and inclusive indicators allow the value exactly at a knot to differ from either side. Constants, binaries, intervals and bounded linear ramps all fit. Boundedness on the permitted input domain must be validated; arbitrary coefficients are not automatically bounded.

For example, with `H_K(x)=1` when `x≥K`, a range `[L,U)` is `H_L−H_U`. A capped increasing ramp is `(max(x−L,0)−max(x−U,0))/(U−L)`. Multiplying by coverage produces its cash payoff. A strict threshold uses the strict indicator instead.

## Recommended canonical storage

For the first implementation store values at ordered knots, rather than accepting arbitrary formula text or signed cancellation-heavy coefficients:

```text
CurveSpec:
    encodingVersion
    constantFraction                 // used if there are no knots
    Knot[] knots

Knot:
    x
    fractionImmediatelyBelow
    fractionAtX
    fractionImmediatelyAbove
```

All fractions are between zero and `1e18`. Coordinates have the measurement's declared integer scale. Coordinates strictly increase. The zero-knot form has a constant fraction; its encoding requires all unused fields to take canonical values.

Evaluation is one algorithm:

1. At a knot return its exact-at value.
2. Between consecutive knots interpolate from the previous knot's above-value to the next knot's below-value.
3. Below the first knot return its below-value; above the last return its above-value.

This makes the tails constant and bounded. Bounding all stored fractions also bounds every interpolated value. A normal scalar knot has identical below/at/above values. A digital has a jump. A range has two jumps. Isolated exact-point payouts can also be represented.

The arrays are the curve's formula parameters. There is no `BINARY/RANGE/SCALAR` discriminator. A formula/encoding version remains necessary. Observation schema validation remains necessary too: encoding categories as numbers does not turn them into a meaningful continuous metric. A categorical observation accepts only its declared category codes; use flat/jump sections to express payments at those codes.

Reuse the current Scalar-AMM validation and full-precision interpolation principles. Its current 24-byte codec does not encode jumps or exact-point overrides, so extend/version the codec instead of silently changing existing curve bytes. Its rejection of flat curves should not carry into this generalized representation.

## Cover identity

```text
observationId = commitment(eventId, measurement rule, future time/window, units)
curveHash     = commitment(canonical CurveSpec)
coverId       = commitment(protocol domain/version, eventId, observationId, curveHash)
```

The collateral token is an immutable protocol dependency. Failure handling follows fixed protocol rules. Neither is a user-configurable cover parameter. A quantity in an authorized order/position scales the normalized payoff; premiums, owners and order salt do not change cover identity.

Store the validated immutable descriptor on first admitted use, or in an immutable data blob with an authenticated pointer. Do not require a separate user `createCover` transaction. A hash alone is insufficient for later risk checks/redemption unless its authenticated preimage is reliably available. The first prototype can store the bounded encoding directly and measure cost.

## Clearing state belongs to AsceExecutor

Logical state, not a final Solidity storage layout:

| State | Purpose |
|---|---|
| Immutable collateral token and oracle adapter | Protocol dependencies |
| Events/approved measurement rules | Define eligible underlying context and measurements |
| Observation records | Committed future measurement, finality status and finalized fact; logically owned by the adapter |
| Cover descriptors | Immutable validated curves bound to observations |
| Account per event | Cash accounting and sum of required reserves; events remain financially segregated |
| Account/observation portfolio | Bounded active cover list and derived reserve |
| Account/cover positions | Signed quantities: long positive, underwritten obligation negative |
| Order state | Filled quantities, cancellation state/epochs and replay prevention |
| Settlement state | Which exposures have been materialized/paid; prevents double payment |

The payoff library is pure math. The risk library derives safe bounds. The executor owns custody/account transitions and enforces checks. Observation verification belongs to the oracle adapter. No separate onchain market-making account contract is required.

`requiredCollateral` is derived/cached data, not another physical token balance. Free collateral is calculated from cash minus the reserve; avoid separately writable free/locked balances that can diverge. Derived caches must be checked against authoritative positions in invariant tests.

## Risk within one settlement group

Group only covers referring to the same measurement and compatible cash settlement/finality rules. Let the account's ideal signed payout be:

\[
P_{a,g}(x)=\sum_j q_{a,j}h_j(x).
\]

Here quantities carry cash units and the normalized fraction is divided by its precision denominator. For an initially restricted account with nonnegative cash, define:

\[
R_{a,g}=\max\left(0,\sup_{x\in\Omega_g}[-P_{a,g}(x)]\right).
\]

The real-valued extremum candidates are the union of all knots: evaluate below, exactly at and above each knot, plus permitted tails. Between knots the aggregate is affine, so there is no missing real-valued interior extremum. Respect domain limits and check protocol exceptional outcomes separately. For discrete-valued observations use neighboring valid ticks/categories; one-sided limits supply conservative bounds when not attainable.

The first engine should derive those candidates from validated curves and recompute a bounded small portfolio. Decode inputs once and use indexed/binary-search evaluation. Do not trust a trader-supplied candidate list or cache an aggregate by naively interpolating individually floored samples. Incremental slope/jump caching is a later optimization requiring exact equivalence to the authoritative payout semantics.

Set limits on active covers and aggregate knot count per account/group, not only on knots per individual cover. Benchmark before committing gas ceilings. Initial experiment targets can be eight active covers and sixteen knots per curve; these are proposed resource limits, not economic price buckets.

## Different observation times

Covers at arbitrary eligible future times can coexist under one event. Initially keep separate reserves for distinct settlement groups:

\[
R_a=\sum_g R_{a,g},\qquad c_a\geq R_a\geq0.
\]

This is conservative across groups. It deliberately does not claim the minimum for arbitrary cross-time portfolios. It allows same-observation netting while preventing a later expected receipt from funding an earlier payment. When a group settles, materialize that account's actual net payout into its cash and remove its exposure/reserve exactly once. A mere resolution announcement cannot erase unpaid liabilities.

An exact cross-time extension requires valid joint histories and checks at every cashflow prefix, conditional on finalized facts. Two price observations being under BTC is insufficient evidence of mutually exclusive payouts. More complex guarantees and observations must not silently receive the same scalar risk calculation.

## Accounting and transitions

Cash includes actual deposits minus withdrawals, premiums paid/received, protocol fees if enabled, and net payouts already materialized. A cashflow moves once; once materialized, remove the corresponding exposure term. Fees are zero in the accepted local MVP.

Each trade applies opposing signed position changes and conserving cash changes, computes both participants' new reserves, and accepts only when both cash/reserve checks pass. No future quote or uncollected premium is an asset. Position transfers and partial closes recheck every affected account.

Withdraw only free cash. Settlement must honor existing entitlements independent of claim ordering. Cash transfers, position updates, reserves and order consumption form one atomic operation with callback isolation. Global custody reconciliation must account for outstanding claims, materialized balances and amounts already paid; do not double-count resolved claims as both future exposure and cash.

## Integer rounding is part of the contract

The extrema rule above is exact for the ideal real-valued piecewise-affine portfolio. Actual per-cover flooring can introduce interior steps, particularly for signed long offsets. The existing Scalar-AMM rounding counterexample is recorded in [the library review](scalar-payoff-library-review-2026-10-01.md).

First derive a cash-conserving settlement convention, then use conservative upper liability/lower asset bounds including interpolation and quantity rounding. A position-size-dependent error allowance must come from that derivation, not a guessed constant. Do not advertise a rounded base-unit minimum until it is proven. Solidity signed integer division truncates toward zero, so it is not automatically a conservative floor for negative exposures. [Solidity integer arithmetic](https://docs.soliditylang.org/en/v0.8.34/types.html#division)

## Mixed-cover numerical check

At the same BTC observation:

- A: binary, 10,000 when BTC ≥100k.
- B: range, 10,000 when 80k ≤ BTC <100k.
- C: scalar, 5,000 at/below 80k, decreasing linearly to zero at 100k and remaining zero above.

| BTC | A | B | C | Total |
|---|---:|---:|---:|---:|
| 70k | 0 | 0 | 5,000 | 5,000 |
| 80k | 0 | 10,000 | 5,000 | 15,000 |
| 90k | 0 | 10,000 | 2,500 | 12,500 |
| 100k | 10,000 | 0 | 0 | 10,000 |
| 120k | 10,000 | 0 | 0 | 10,000 |

Summed caps 25,000; joint maximum 15,000; saving 10,000 (40%). This assumes the accepted zero buyer payout on protocol INVALID; protocol refunds would need separate inclusion. The maximum is attained at 80k, and rounded-down short payouts cannot exceed it.

An independent local `fractions.Fraction` calculation checked the unified evaluator, range endpoints, binary inclusivity, scalar interpolation and the union-of-knots maximum. It also checked that strict-below and strict-above claims both pay zero at their shared threshold—an exact-point state that cannot be omitted. This was an arithmetic experiment, not an EVM clearing implementation or complete test campaign.
