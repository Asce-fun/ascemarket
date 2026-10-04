# Scalar-AMM payoff library: reuse for Asce clearing

Reviewed 1 October 2026. Source project: `/Users/saurabhyadav30/Desktop/Scalar-AMM`, HEAD `fdfdb22c9de87b9079e2161d55ddc330432c62f7`. That checkout has existing local changes; this review did not modify it. This is a payoff/architecture review, not a security audit or implemented clearing engine.

## Verdict

**Reuse the payoff mathematics as a starting point. Do not reuse the per-curve funded-market architecture as the portfolio clearing model.** `LibPayoffCurve` supplies bounded continuous scalar payoff evaluation; it does not calculate the maximum obligation of multiple covers sharing capital.

The user's clarified scope permits different payout types under a broad event. The earlier Asce categorical-condition recommendation remains a valid restricted control, but is not a universal event model. Fixed interpolation knots also must not be confused with mutually exclusive price buckets.

## Files inspected

- `README.md` — implemented two-claim CTF/LMSR architecture and trusted resolver assumptions.
- `HEDGING_PROTOCOL_FROM_SCRATCH.md` — Metric → resolved state → Hedge Series → claims → replaceable execution, especially its objects, issuance and library sections.
- `HEDGING_PRIMITIVE.md 04-54-36-240.md` — relevant payoff, state and CTF sections, including anchor-based interpolation and discontinuous losses.
- `src/libs/gnosis/LibPayoffCurve.sol` and `LibGnosisConstants.sol` — actual codec, validation, evaluation, complements and rounding.
- `src/gnosis/base/ScalarMarketCreation.sol` and `ScalarMarketSettlement.sol` — actual per-market condition preparation and reporting.
- `test/libs/gnosis/LibPayoffCurve.t.sol`, its harness and independent reference evaluator.

These are local source files, not assertions about current public deployments.

## What is already implemented

| Feature | Actual behavior |
|---|---|
| Payoff input | Packed points `(scalar value, normalized payout)` |
| Point storage | Signed `int128` value plus `uint64` payout; 24 bytes per point |
| Limits | 2–32 points, strictly increasing scalar coordinates |
| Payout range | Each point between 0 and `1e18`; interpolation stays bounded |
| Between points | Linear interpolation; rising and falling segments are supported |
| Outside points | Clamp to first/last payout |
| Shape | Ramps, deductibles, caps, tents and other continuous piecewise-linear curves |
| Commitment | Validate then hash encoded bytes |
| Complement | Capital numerator = `1e18 − Protection numerator` |
| Rounding | Protection interpolation rounds down; complementary Capital receives numerator dust |
| Redemption preview | Mirrors separate CTF claim flooring in collateral base units |

The library returns a fraction, not a dollar payment. A separately specified coverage quantity scales it into cash. A caller of the unchecked memory evaluator must authenticate previously validated bytes. Use the checked entry point or enforce that hash binding explicitly.

The document's proposed library API mentions exposing a maximum payout; the actual library has no portfolio-maximum function or dedicated maximum scanner. The code is the implementation authority.

## Limits relevant to mixed covers

1. **Binary thresholds and categorical jumps are not exact continuous curves.** Equal scalar coordinates are rejected, so duplicate points cannot encode a jump. A narrow ramp changes the contract. Add an explicit digital/interval or categorical evaluator with precise boundary rules.
2. **Constant curves are rejected.** Constant claims and constant portfolio residuals may be useful to clearing; they need explicit representation or a deliberate validation change. A portfolio engine must not pass a flat aggregate through this market-specific validator.
3. **One scalar input is not arbitrary future history.** The library can evaluate a payoff of final price, minimum price or another scalar metric, but the oracle must establish that metric. Covers on final price and historical minimum cannot receive the same input indiscriminately. Their joint valid-state relationships need a separate risk model.
4. **A curve-byte hash is not a full cover identity.** Bind event, measurement specification, units, payoff type/version, curve commitment, collateral and failure treatment. Define a canonical encoding; economically equivalent encodings need not currently have the same raw hash.
5. **A bounded curve is not a collateral proof.** Portfolio quantities, withdrawals, premiums, fees, rounding and exceptional outcomes still need clearing invariants.

## How the library helps portfolio risk

For continuous curves on exactly the same scalar observation `x`, form the ideal unrounded aggregate:

\[
L(x)=\sum_i N_i h_i(x).
\]

Collect the union of all curves' knots. Between adjacent knots every curve, and therefore the aggregate, is affine. An affine function achieves its maximum/minimum at an endpoint; outside the outermost knots all curves are constant under the implemented clamp rule.

Therefore the **ideal real-valued** aggregate's extrema are found at the union of knots. There is no need to sample every BTC price or discretize prices into buckets. Covers with digital jumps require additional boundary/one-sided candidates.

For the restricted underwriter with nonnegative buyer obligations, the maximum bounds required backing before accounting for trade cashflows. For signed-account netting use the full cash-plus-payoff floor, not just the sum of buyer caps. A rounding-aware implementation is required in both cases.

### Numerical control

Cover A decreases linearly from 100% at BTC 80k to 0% at 120k; coverage 10,000 USDC. Cover B increases over the same interval from 0% to 100%; coverage 10,000 USDC. Both clamp outside that interval.

| BTC | A ideal payout | B ideal payout | Total |
|---|---:|---:|---:|
| ≤80k | 10,000 | 0 | 10,000 |
| 90k | 7,500 | 2,500 | 10,000 |
| 100k | 5,000 | 5,000 | 10,000 |
| 110k | 2,500 | 7,500 | 10,000 |
| ≥120k | 0 | 10,000 | 10,000 |

Summed caps: 20,000. Required backing: 10,000. Saving: 50%. Independently rounded-down buyer payouts cannot exceed the ideal total, and the tails attain 10,000 exactly, so this example's maximum remains exact in base units. These calculations assume zero buyer payout on INVALID; a refund promise must enter the risk calculation separately.

Add a third tent-shaped cover with 5,000 maximum at 100k and zero at/beyond 80k and 120k. The aggregate peaks at 15,000; summed caps are 25,000. Saving: 10,000, or 40%. Exact rational checks of these examples were run locally; they are not an implemented onchain portfolio risk engine.

### Rounding cannot be omitted from the proof

The library floors each independently evaluated Protection fraction. Two ideal complementary curves can sum to one between knots, yet their separately floored values sum to `1e18 − 1` at some interior observations. With one USDC notional on each, separately floored payments can total 999,999 base units inside the interval and 1,000,000 at both endpoints.

For example use knots at scalar values 0 and 3, with fractions rising from 0 to `1e18` and falling from `1e18` to 0. At `x=1` their fractions are 333,333,333,333,333,333 and 666,666,666,666,666,666. This follows the actual evaluator's rounding rule. A knot-only calculation of guaranteed **long** portfolio proceeds would overstate the interior guarantee by one USDC base unit in this example.

This is not a demonstrated library bug; it shows why the real-valued extrema theorem cannot be copied unchanged into signed integer netting. For positive obligations, use upward-rounded bounds on the ideal aggregate until an exact algorithm is proven. For credited long offsets, prove a lower bound including every rounding loss. Quantity scaling, position fragmentation and claim redemption must share one specified policy.

## CTF distinction: independent curve conditions versus shared interpolation basis

The existing Scalar-AMM implementation prepares one two-slot condition per allocated market, evaluates that market's curve and reports complementary Capital/Protection numerators. Its README assigns one LMSR clone per market. The from-scratch document likewise proposes one condition per Hedge Series and explicitly describes this as fully collateralized independent issuance.

That supports continuous cover payouts but does not implement shared portfolio collateral across different curves. Independently locking 10,000 for each of A and B locks 20,000 despite the 10,000 joint maximum.

However, **CTF is not inherently limited to one-hot bucket resolution**. A common condition can use interpolation basis slots at fixed knots. At a scalar value between two knots, report nonzero payout weights for those two neighboring slots. A buyer's knot-value basket then gives its linear interpolation. The Scalar-AMM hedging document already describes a related anchor construction.

For the three-cover example with common knots `[80k,100k,120k]`, allocate these basis-claim quantities:

```text
A:              [10,000, 5,000,      0]
B:              [     0, 5,000, 10,000]
C:              [     0, 5,000,      0]
total:          [10,000,15,000, 10,000]
maker residual: [ 5,000,     0,  5,000]
```

Backing of 15,000 can fund this allocation. At BTC 90k, basis weights `[1/2,1/2,0]` give ideal payouts 7,500, 2,500 and 2,500, with maker residual 2,500. The weights sum to one and all allocated quantities are nonnegative. If INVALID has zero buyer payout, include a dedicated slot whose residual quantity is the full 15,000.

This is a mathematical construction, not a newly executed EVM test. Per-basis redemption rounding need not match this library's per-curve-then-quantity rounding exactly; require a consistent contractual rounding rule or an explicit bound before claiming token-level equivalence.

The trade-off is **fixed basis versus flexible covers**. A shared CTF interpolation basis can span continuous curves aligned to its committed knots. It does not automatically admit a new arbitrary breakpoint, categorical predicate or path-dependent rule after claims are issued. Silently changing the basis would change outstanding claims. An internal ledger can keep each cover's immutable curve and update the risk engine's union of knots as new compatible covers enter, without changing old claims.

Thus the library does not by itself prove CTF should be replaced. It provides an excellent control for comparing shared-basis CTF with internal claims under identical contracts. If freely chosen knots and mixed payoff types are core requirements, an internal clearing prototype is the more direct experiment. CTF export remains optional and needs a separately funded conversion proof; direct cash settlement needs no CTF minting detour.

## Recommended next implementation experiment

1. Reuse/adapt the validated scalar codec and evaluator, with explicit measurement and coverage-unit binding.
2. Add typed digital/interval and categorical payoffs; keep continuous and discontinuous boundary semantics distinct.
3. Prototype the common-observation portfolio extrema engine in Python, with rational reference calculations and rounded base-unit settlement. Test premiums, partial closes and withdrawals.
4. Compare internal claims against the shared interpolation-basis CTF control. Do not compare against an intentionally isolated condition-per-cover baseline alone.
5. Then specify Solidity authorization, bounded computation and custody. One event may contain several measurement specifications, but only grant offsets with a proof over their valid joint states. Unproved combinations receive conservative backing.

The next contract specification must describe this expanded scope; the earlier fixed-bucket executor proposal is a restricted baseline, not its final architecture.

## Verification performed

```sh
forge test --offline --match-contract LibPayoffCurveTest \
  --out /private/tmp/asce-scalar-payoff-review-out \
  --cache-path /private/tmp/asce-scalar-payoff-review-cache
```

Solidity 0.8.34; **13 tests passed, zero failures/skips**, including four fuzz tests at 256 runs each. The tests cover malformed encodings, point bounds, payout bounds, interpolation, signed-domain extremes, independent-reference agreement, complements and redemption dust. Outputs/caches were directed outside Scalar-AMM. The controller suite, production oracle authentication and multi-cover collateralization were not tested by this command.
