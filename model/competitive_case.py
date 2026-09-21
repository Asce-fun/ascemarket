"""Research comparison, not a venue integration or price simulation.

Run: python3 -B -m model.competitive_case
Checks a two-butterfly liability and an optimal allocation of its fixed put
inventory under the inspected Gamma type-0 vault formula. All math is rational;
the Gamma allocation is a continuous relaxation, not a Solidity execution.
"""
from copy import deepcopy
from fractions import Fraction as F
import json
from pathlib import Path

from .examples import automatic_change, commit
from .ledger import Ledger
from .payoffs import Payoff, VOID
from .workflow_examples import serializable

GAMMA_COMMIT = "841f81d9d05da9d27277b5775edfbb48c4012d2a"


def butterfly(center):
    return (Payoff.ramp(center - 200, center, 200, void=0)
            - Payoff.ramp(center, center + 200, 200, void=0))


def put(k, x):
    return max(F(k) - x, F(0))


def vault_cash(q, k, l, h):
    return max(q * k - min(q, l) * h, F(0))


def allocation_check():
    # short quantity, short strike, deposited long quantity, long strike
    rows = [(F(1), 2800, F(14, 15), 3000),
            (F(15, 16), 3200, F(15, 16), 3000),
            (F(1, 16), 3200, F(1, 18), 3600),
            (F(1), 3400, F(17, 18), 3600),
            (F(1), 3800, F(1), 3600)]
    shorts = {k: sum(q for q, s, l, h in rows if s == k)
              for k in (2800, 3200, 3400, 3800)}
    longs = {h: sum(l for q, k, l, s in rows if s == h)
             for h in (3000, 3600)}
    assert all(v == 1 for v in shorts.values())
    assert all(v <= 2 for v in longs.values())
    cash = sum(vault_cash(*r) for r in rows)
    assert cash == F(775, 2)

    # Exact lower-bound certificate, allowing arbitrary fractional splitting.
    # For every vault, c + beta[h]*l >= alpha[k]*q. For q>0 it suffices
    # to check l/q at 0, 1, k/h when in [0,1]: piecewise linear there;
    # beyond 1 margin no longer falls and beta is nonnegative.
    alpha = {2800: F(0), 3200: F(200), 3400: F(425, 2), 3800: F(425)}
    beta = {3000: F(0), 3600: F(225)}
    certificate_checks = 0
    for k in shorts:
        for h in longs:
            ratios = {F(0), F(1)}
            if k <= h:
                ratios.add(F(k, h))
            for r in ratios:
                assert vault_cash(F(1), k, r, h) + beta[h] * r >= alpha[k]
                certificate_checks += 1
    lower_bound = sum(alpha.values()) - 2 * sum(beta.values())
    assert lower_bound == cash
    return {"continuous_optimum_cash": cash,
            "allocation": [{"short_strike": k, "short_amount": q,
                            "long_strike": h, "long_amount": l,
                            "cash": vault_cash(q, k, l, h)} for q, k, l, h in rows],
            "unused_long_3000": 2 - longs[3000],
            "lower_bound_alpha": alpha, "lower_bound_beta": beta,
            "certificate_endpoint_checks": certificate_checks,
            "scope": "fixed put inventory; arbitrary fractional vault allocation; no extra instruments"}


def path(actions):
    first, second = butterfly(3000), butterfly(3600)
    b = Ledger()
    b.register("seller", 2000)
    b.register("buyer", 2000)
    qs = [F(0), F(0)]
    received = F(0)
    rows = []
    peak_asce = peak_gamma = F(0)
    for name, delta_q, seller_payment in actions:
        payout = first * delta_q[0] + second * delta_q[1]
        commit(b, automatic_change(b, "seller", -payout, seller_payment),
               automatic_change(b, "buyer", payout, -seller_payment))
        qs = [q + d for q, d in zip(qs, delta_q)]
        received -= seller_payment
        # Only states proved here: equal scaled inventories or a single butterfly.
        if qs[0] == qs[1]:
            gamma = F(775, 2) * qs[0]
        else:
            assert min(qs) == 0
            gamma = 200 * max(qs)
        exact = 200 * max(qs)
        net_asce = 2000 - b.wallet("seller")
        assert net_asce == exact - received
        net_gamma = gamma - received
        peak_asce, peak_gamma = max(peak_asce, net_asce), max(peak_gamma, net_gamma)
        rows.append({"action": name, "quantities": qs[:],
                     "asce_backing": exact, "gamma_relaxed_cash": gamma,
                     "asce_net_cash": net_asce, "gamma_net_cash": net_gamma})
    # Actual ledger settlement at every corner, both tails, and VOID.
    for result in (0, 2800, 3000, 3200, 3400, 3600, 3800, 10000, VOID):
        settled = deepcopy(b)
        settled.advance(settled.close_at)
        settled.finalize(result)
        for name in settled.names:
            settled.redeem(name)
            settled.audit()
        assert settled.escrow == 0
    return {"rows": rows, "peak_asce": peak_asce,
            "peak_gamma_relaxation": peak_gamma,
            "final_asce_net_cash_before_redemption": 2000 - b.wallet("seller")}


def run():
    first, second = butterfly(3000), butterfly(3600)
    liability = first + second
    assert liability.extrema() == (0, 200)
    # Independent vanilla-option evaluation at all knots and tails proves
    # equality on each affine interval, not just at arbitrary sampled prices.
    checks = []
    for x in (0, 2800, 3000, 3200, 3400, 3600, 3800, 10000):
        reference = (put(2800, x) - 2 * put(3000, x) + put(3200, x)
                     + put(3400, x) - 2 * put(3600, x) + put(3800, x))
        assert liability.value(x) == reference
        checks.append({"observation": x, "liability": reference})
    opening = ("Open both, illustrative net premium 80", (F(1), F(1)), F(-80))
    return {"status": "all exact arithmetic, allocation certificate and ledger checks passed",
            "source_commit": GAMMA_COMMIT, "normal_outcome_checks": checks,
            "asce_maximum_liability": liability.extrema()[1],
            "gamma_allocation": allocation_check(),
            "paths": {
                "hold": path([opening]),
                "halve_then_close": path([opening,
                    ("Halve both for 40", (F(-1, 2), F(-1, 2)), F(40)),
                    ("Close remainder for 40", (F(-1, 2), F(-1, 2)), F(40))]),
                "close_individually_180": path([opening,
                    ("Close first for 180", (F(-1), F(0)), F(180)),
                    ("Close second for 180", (F(0), F(-1)), F(180))]),
                "close_individually_200": path([opening,
                    ("Close first for 200", (F(-1), F(0)), F(200)),
                    ("Close second for 200", (F(0), F(-1)), F(200))])},
            "limits": ["No live quotes, trades or deployed Gamma calls",
                       "Gamma formula is ported; Solidity and token rounding not executed",
                       "Matched normal settlement assumed; exceptional-state equivalence unverified",
                       "Gamma allocation optimizes fixed put inventory, not all synthetic strategies",
                       "All opening and closing premiums are illustrative; fees zero",
                       "Gamma path assumes free atomic reallocation and immediately reusable cash",
                       "No claim of superiority to Deribit portfolio margin or Polymarket"]}


if __name__ == "__main__":
    output = Path("research/competitive-case-results.json")
    result = run()
    for name, expected in {
        "hold": (120, F(615, 2)),
        "halve_then_close": (120, F(615, 2)),
        "close_individually_180": (300, F(615, 2)),
        "close_individually_200": (320, 320),
    }.items():
        row = result["paths"][name]
        assert (row["peak_asce"], row["peak_gamma_relaxation"]) == expected
    output.write_text(json.dumps(serializable(result), indent=2) + "\n")
    print(result["status"])
    print(f"Wrote {output}")
