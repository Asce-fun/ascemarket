"""Exact certificate against extra put constructions; no external dependencies.

Run python3 -B -m model.competitive_extensions.
The accompanying report proves the continuous-strike inequality. Finite checks
below verify its coefficients, candidate boundaries, and saved catalogue.
"""
from fractions import Fraction as F
import json
from pathlib import Path

from .competitive_case import allocation_check, vault_cash
from .workflow_examples import serializable


def phi(k):
    k = F(k)
    if k <= 3000:
        return F(0)
    if k <= 3200:
        return k - 3000
    if k <= 3600:
        return k / 16
    if k <= 3800:
        return k - 3375
    return k * F(17, 152)


def run():
    # phi = a*K+b. On each interval: slope in [0,1] and b<=0.
    # Thus phi is nonnegative, nondecreasing, 1-Lipschitz and phi(K)/K
    # nondecreasing. Continuity checks join these properties globally.
    pieces = [(0, 3000, F(0), F(0)),
              (3000, 3200, F(1), F(-3000)),
              (3200, 3600, F(1, 16), F(0)),
              (3600, 3800, F(1), F(-3375)),
              (3800, None, F(17, 152), F(0))]
    for lo, hi, a, b in pieces:
        assert 0 <= a <= 1 and b <= 0
        assert a * lo + b == phi(lo)
        if hi is not None:
            assert a * hi + b == phi(hi)
    inventory = {2800: 1, 3000: -2, 3200: 1, 3400: 1, 3600: -2, 3800: 1}
    bound = sum(q * phi(k) for k, q in inventory.items())
    assert bound == allocation_check()["continuous_optimum_cash"] == F(775, 2)
    catalogue = json.loads(Path("research/deribit-catalog-2026-09-17.json").read_text())
    strikes = sorted({F(str(r["strike"])) for r in catalogue["puts_at_expiry"]}
                     | {F(k) for k in range(0, 5001, 100)} | {F(1000000)})
    count = 0
    for k in strikes:
        for h in strikes:
            ratios = {F(0), F(1), F(2)}
            if h > 0 and k <= h:
                ratios.add(k / h)
            for r in ratios:
                assert phi(k) - r * phi(h) <= vault_cash(F(1), k, r, h)
                count += 1
    return {"status": "exact certificate coefficients and vault inequalities passed",
            "bound": bound, "attained_by": "competitive-case-results.json allocation",
            "scope": "arbitrary finite additional put strikes and offsetting positions; same expiry, underlying and strike/collateral asset; Gamma type-0 formula in exact arithmetic",
            "phi_pieces": pieces, "finite_inequality_checks": count,
            "continuous_proof": "research/competitive-followup.md",
            "hypothetical_weekly_capital_value": {
                "released_cash": F(375, 2), "annual_rate_assumption": F(1, 10),
                "days": 7, "simple_interest_value": F(375, 2) * F(1, 10) * F(7, 365)},
            "unresolved": ["live deployed margin and precision", "mixed call/spot/borrowing constructions",
                           "Deribit margin preview", "actual prices and complete costs", "recurring user value"]}


if __name__ == "__main__":
    result = run()
    path = Path("research/competitive-extension-results.json")
    path.write_text(json.dumps(serializable(result), indent=2) + "\n")
    print(result["status"])
    print(f"Verified {result['finite_inequality_checks']} inequalities; wrote {path}")
