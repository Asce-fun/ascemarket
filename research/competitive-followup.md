# Does the funding advantage survive a stronger alternative?

Research date: 17 September 2026. Builds on the [two-butterfly comparison](competitive-case.md).

## What “accounting edge” means to the user

It means less personal money tied up for the same contractual exposure, because the system recognizes promises that offset. The account still has enough backing for every permitted settlement result. This does not increase the trade's premium, make losses smaller, or promise that an early exit will be affordable.

In the example, gross required backing is 200 in Asce versus a 387.5 minimum under the compared Gamma put-vault rules in exact arithmetic. If both routes receive the same illustrative net premium of 80, the user's cash contribution is 120 versus 307.5. The difference of 187.5 remains available for other uses. It is **available cash, not a profit**.

Its economic value depends on what the user can do with that cash and for how long. At an entirely hypothetical annual financing rate of 10%, freeing 187.5 for seven days is worth about **0.36**, before any costs. At 1,000 times the position size it would be about 359.59, assuming the same terms scale. These are arithmetic illustrations, not offered rates, executable sizes or earnings forecasts. A slightly worse quote or higher fee can erase the financing benefit.

## Finding: extra put constructions do not remove this particular gap

The earlier experiment optimized allocation of a fixed inventory. This follow-up allows additional put strikes and additional offsetting long/short positions, while requiring the same final payout and the same underlying, expiry and strike/collateral asset.

A numerical linear-program search found the same 387.5 minimum using both the six original strikes and a larger 19-strike set. More importantly, an exact mathematical certificate below establishes the bound for **any finite collection of nonnegative put strikes**, under the inspected Gamma type-0 formula. The conclusion therefore does not depend on which strike grid the search happened to choose.

The existing allocation attains the bound in continuous quantities. This strengthens the architecture result: an adapter cannot remove the cash gap merely by adding same-expiry, cash-collateralized put positions or rearranging their vaults. Actual token precision, deployment configuration and execution costs are still unverified. This is not a universal theorem about all financial instruments or all versions of Gamma.

### The certificate

For a strike `K >= 0`, define an artificial weight `phi(K)`:

```text
K <= 3000:         0
3000..3200:        K - 3000
3200..3600:        K / 16
3600..3800:        K - 3375
K >= 3800:         17K / 152
```

These weights are a proof device, not option prices or a market valuation. The function is continuous, nonnegative, nondecreasing, has slopes between zero and one, and `phi(K)/K` is nondecreasing for positive strikes. On each affine segment the last property follows because its constant term is nonpositive.

For every put vault with short quantity `q`, short strike `K`, long quantity `l` and long strike `H`:

```text
q*phi(K) - l*phi(H)
    <= max(q*K - min(q,l)*H, 0)
    = required cash under the inspected formula
```

For `q>0`, divide by `q` and set `r=l/q`. At `r=0`, the inequality follows from `phi(K)<=K`. At `r=1`, it follows from monotonicity and the slope bound. If `K<H`, the intermediate corner `r=K/H` follows from the nondecreasing ratio. Both sides are affine between these corners. For `r>1`, required cash no longer falls and the left side cannot increase. The `q=0` case follows from nonnegativity.

Sum this inequality across all vaults. Additional offsetting puts cancel their weights, and freely held long puts contribute nonpositive weights. The required net liability has weight:

```text
phi(2800) - 2phi(3000) + phi(3200)
  + phi(3400) - 2phi(3600) + phi(3800)
= 0 - 0 + 200 + 212.5 - 450 + 425
= 387.5
```

This gives the lower bound even with extra puts. It matches the [feasible allocation already checked](competitive-case.md#3-give-the-alternative-its-best-allocation). The script verifies the exact piece coefficients and continuity, and 29,487 vault inequalities covering the saved catalogue, additional strikes and boundary ratios. The continuous proof, rather than that finite check count, supports the all-strike conclusion.

## Stronger alternatives that remain open

**Calls and underlying collateral.** The inspected whitelist accepts puts collateralized in the strike asset and calls collateralized in the underlying. A put-to-call rewrite therefore changes the collateral asset; it cannot be compared by counting ETH units as if they were USDC. A matching strategy would have to include the underlying collateral's value, its residual price exposure, premiums, and any financing or hedge. I have not proved that every such construction is inferior. [Pinned whitelist rule](https://github.com/opynfinance/GammaProtocol/blob/841f81d9d05da9d27277b5775edfbb48c4012d2a/contracts/core/Whitelist.sol#L139), [call margin calculation](https://github.com/opynfinance/GammaProtocol/blob/841f81d9d05da9d27277b5775edfbb48c4012d2a/contracts/core/MarginCalculator.sol#L861).

**Deribit portfolio margin.** It evaluates the portfolio together, making it a stronger competitor than separate Gamma vaults. Its live numbers remain unknown here. The documented simulator requires authenticated `account:read` access; no authenticated results were supplied or obtained. I prepared five read-only requests for an empty control, the full portfolio, half size, and either remaining butterfly. No request was submitted and no account was modified. [Request payloads](deribit-margin-requests.json), [official endpoint](https://docs.deribit.com/api-reference/account-management/private-simulate_portfolio).

**Another fully funded payoff engine.** A system that already recognizes the full combined obligation can match 200. The all-put Gamma result does not overturn this fact. There is no arithmetic room below the 200 worst payout for this claim with only cash backing and the same unconditional settlement guarantee.

## How to compare Deribit without a misleading number

The saved requests use the listed ETH_USDC puts for 25 September 2026 and `add_positions=false`. Before running them later, revalidate expiry and instruments. This parameter replaces simulated positions; do not assume it also zeroes the account's collateral or removes all account-specific context. Record the margin mode and use a clean comparison context.

Most importantly, **initial margin is not automatically the user's cash contribution**. The API distinguishes cash balance, signed option value, equity, margin and withdrawal availability. Under a simplified segregated cash-only portfolio-margin account:

```text
cash after trade = personal deposit + net premium received - fees
equity          = cash after trade + signed option mark value

entry deposit floor
    = max(0, initial margin - signed option mark value
             - net premium received + fees)
```

This is a reconciliation formula under the stated assumptions, not a substitute for the venue's checks. Additional reserves, collateral conversion, existing positions and withdrawal rules must be included when applicable. Do not compare a displayed margin number directly with Asce's `200 - premium`. Use actual package prices, not the assumption that both venues quote identically. [API balance and margin definitions](https://docs.deribit.com/api-reference/account-management/private-simulate_portfolio).

Capture initial/maintenance margin, signed option value, cash/equity, available funds, available withdrawal funds, timestamp, market marks and margin model for every state. Also capture the proposed trade cash flows and fees. A current margin preview does not establish a no-top-up guarantee through every future price path.

## Decision

**Continue the narrow investigation; do not broaden the product yet.** We now have a stronger source-level result against cash-collateralized put-vault constructions, not just a favorable allocation example. The plausible user benefit is less idle cash supporting multiple bounded structures.

Two questions decide whether that benefit deserves a standalone product: whether the strongest executable alternative already matches it, and whether users' actual portfolios release enough valuable capital to outweigh extra costs and switching effort. Neither is answered by the mathematical certificate.

The adverse exit findings are unchanged: the earlier path closing both payouts at 200 at different times erases the peak-capital advantage. Retaining the portfolio, changing both together and closing one component remain different tasks. No revision to the core accounting rule is needed.

Do not add borrowing, mixed collateral, a new token or a larger trading interface to manufacture a better number. They change the guarantees and comparison. The specific remaining live comparison needs read-only margin results and matched quotes; this report does not invent them.

## Reproduction and provenance

Run `python3 -B -m model.competitive_extensions`. [Exact checker](../model/competitive_extensions.py), [recorded output](competitive-extension-results.json). It uses only the standard library and does not connect to a venue. The earlier [lifecycle checker](../model/competitive_case.py) covers the opening, partial changes and adverse exits.

SciPy 1.18.1 / HiGHS was used only for exploratory linear-program searches in a temporary directory. The saved certificate and feasible allocation can be checked without SciPy and do not rely on floating-point solver tolerances. The inspected Gamma commit remains `841f81d9d05da9d27277b5775edfbb48c4012d2a`; no deployed Solidity execution or full mixed-instrument optimization is claimed.
