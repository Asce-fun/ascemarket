"""Exact synthetic experiments for a reusable event-cover marketplace.

Run from any directory with python3 -B research/cover_marketplace_quant.py.
No observed demand, live quotes, or maker-profitability claims are made.
"""
from fractions import Fraction
from itertools import product
from pathlib import Path
import hashlib
import json
import math
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from model_v2.examples import checkpoint_market, checkpoint_cover, change, execute
from model_v2.ledger import Ledger
from model_v2.schema import Account
from model_v2.verifier import extrema
from model_v2.oracle import extrema as exhaustive_extrema, cover_value, paths


def basis_experiment():
    market, values = checkpoint_market("reusable-cover-research", (tuple(range(8)),), lambda a, b: True)
    basis = [checkpoint_cover(market, values, f"threshold-{k}", 1,
                              lambda x, k=k: 100 if x >= k else 0) for k in range(8)]
    covers = {c.identifier: c for c in basis}
    complete_paths = list(paths(market))
    intervals = 0
    for a in range(8):
        for b in range(a + 1, 9):
            direct = checkpoint_cover(market, values, f"interval-{a}-{b}", 1,
                                      lambda x, a=a, b=b: 100 if a <= x < b else 0)
            for path in complete_paths:
                replicated = cover_value(basis[a], path)
                if b < 8:
                    replicated -= cover_value(basis[b], path)
                assert replicated == cover_value(direct, path)
            intervals += 1

    profile_count = 0
    for amounts in product((0, 100, 200), repeat=8):
        coefficients = [amounts[0] // 100] + [(amounts[k] - amounts[k-1]) // 100 for k in range(1, 8)]
        account = Account(holdings=tuple((basis[k].identifier, q) for k, q in enumerate(coefficients) if q))
        fast = extrema(market, account, covers)
        slow = exhaustive_extrema(market, account, covers)
        for path in complete_paths:
            value = sum(q * cover_value(basis[k], path) for k, q in enumerate(coefficients))
            expected = amounts[path[1]] if path[1] < 8 else 0
            assert value == expected
        assert (fast.minimum, fast.maximum) == (slow[0], slow[1]) == (0, max(amounts))
        profile_count += 1
    return {"normal_states": 8, "exception_states": 1, "basis_covers": 8,
            "exact_interval_replications": intervals, "exact_profile_replications": profile_count,
            "all_exceptions_checked": True,
            "boundary": "Exact finite settlement domain; all covers cancel at zero. Replication uses signed internal holdings. This is not an implemented external-token conversion router."}


def maker_experiment():
    market, values = checkpoint_market("maker-inventory-research", (tuple(range(8)),), lambda a, b: True)
    a = checkpoint_cover(market, values, "left-tail", 1, lambda x: 1000 if x < 3 else 0)
    b = checkpoint_cover(market, values, "right-tail", 1, lambda x: 1000 if x >= 5 else 0)
    def setup():
        ledger = Ledger(market)
        ca, cb = ledger.admit(a), ledger.admit(b)
        for owner in ("maker", "buyer-a", "buyer-b"):
            ledger.register(owner, 10000)
        return ledger, ca, cb

    atomic, ca, cb = setup()
    initial = atomic.funding("maker", ((ca, -1), (cb, -1)), cash=770)["deposit"]
    execute(atomic, (change(atomic, "maker", ((ca, -1), (cb, -1)), 770, initial),
                     change(atomic, "buyer-a", ((ca, 1),), -385, 385),
                     change(atomic, "buyer-b", ((cb, 1),), -385, 385)), "atomic")
    atomic.audit()

    sequential, ca, cb = setup()
    first = sequential.funding("maker", ((ca, -1),), cash=385)["deposit"]
    execute(sequential, (change(sequential, "maker", ((ca, -1),), 385, first),
                         change(sequential, "buyer-a", ((ca, 1),), -385, 385)), "first")
    sequential.audit()
    execute(sequential, (change(sequential, "maker", ((cb, -1),), 385),
                         change(sequential, "buyer-b", ((cb, 1),), -385, 385)), "second")
    released = sequential.bounds("maker").minimum
    execute(sequential, (change(sequential, "maker", external=-released),), "release")
    sequential.audit()
    assert initial == 230 and first == 615 and released == 385
    assert sequential.net_deposits["maker"] == initial

    cancelled_a = checkpoint_cover(market, values, "left-tail-refund", 1,
                                  lambda x: 1000 if x < 3 else 0, exception=600)
    cancelled_b = checkpoint_cover(market, values, "right-tail-refund", 1,
                                  lambda x: 1000 if x >= 5 else 0, exception=600)
    exception_covers = {c.identifier: c for c in (cancelled_a, cancelled_b)}
    exception_minimum = extrema(market, Account(770, tuple((cid, -1) for cid in exception_covers)), exception_covers).minimum
    assert -exception_minimum == 430

    expected_profit = Fraction(6, 8) * -230 + Fraction(2, 8) * 770
    assert expected_profit == 20
    return {"unit": "one tenth of illustrative currency unit", "per_cover_cap": 1000,
            "per_cover_premium": 385, "atomic_writer_contribution": initial,
            "separate_writers_total_contribution": 1230,
            "sequential_peak_writer_contribution": first,
            "sequential_release_after_second_fill": released,
            "remaining_writer_contribution": sequential.net_deposits["maker"],
            "contribution_with_600_exception_payout_per_cover": -exception_minimum,
            "synthetic_expected_gross_profit": str(expected_profit),
            "loss_probability_under_uniform_normal_model": "3/4",
            "loss_when_a_tail_wins": 230, "profit_when_neither_wins": 770,
            "boundary": "Uniform probabilities on eight normal outcomes, exception probability zero only for this illustrative expected-value calculation. Funding includes the exception. Premiums are assumptions, not observed quotes; costs and estimation error are excluded. CTF can match this mutually exclusive funding construction."}


def joint_price_experiment():
    # Identical fair checkpoint digitals can support very different path prices.
    models = {"perfectly_opposed": (Fraction(0), Fraction(1,2), Fraction(1,2), Fraction(0)),
              "independent": (Fraction(1,4),) * 4,
              "perfectly_aligned": (Fraction(1,2), Fraction(0), Fraction(0), Fraction(1,2))}
    states = ((0,0), (0,1), (1,0), (1,1))
    rows = []
    for label, probabilities in models.items():
        first = sum(p * x for p, (x, y) in zip(probabilities, states))
        second = sum(p * y for p, (x, y) in zip(probabilities, states))
        joint = sum(p * x * y for p, (x, y) in zip(probabilities, states))
        assert first == second == Fraction(1,2)
        rows.append({"model": label, "first_checkpoint_digital_price": str(100*first),
                     "second_checkpoint_digital_price": str(100*second),
                     "both_checkpoints_digital_price": str(100*joint)})
    return {"rows": rows, "boundary": "Hypothetical undiscounted fair values. Equal marginal prices do not identify joint/path-dependent prices. These probability models do not alter permitted funding histories."}


def coherent_pricing_experiment():
    # A and B are exclusive; C has their summed payoff, including zero exceptions.
    states = ("A", "B", "neither", "exception")
    a, b, c = (100,0,0,0), (0,100,0,0), (100,100,0,0)
    assert all(x+y == z for x,y,z in zip(a,b,c))
    synthetic_asks = {"A": 35, "B": 35, "C": 80}
    synthetic_c_bid = 75
    return {"states": states, "equal_payouts": True, "synthetic_asks": synthetic_asks,
            "replication_ask": synthetic_asks["A"] + synthetic_asks["B"],
            "direct_ask": synthetic_asks["C"], "synthetic_C_bid": synthetic_c_bid,
            "gross_arbitrage_if_atomic_conversion_and_all_quotes_executable": synthetic_c_bid - synthetic_asks["A"] - synthetic_asks["B"],
            "boundary": "An exact funding/equivalence demonstration, not an implemented conversion facility or observed arbitrage. Fees, execution, permissions and quote capacity can remove the opportunity."}


def shared_quote_experiment():
    # Finite-state entropic cost illustration. Floating-point here is offchain
    # research pricing only, never the integer ledger's solvency calculation.
    probabilities = [0.99 / 8] * 8 + [0.01]
    a = [100 if k < 3 else 0 for k in range(8)] + [0]
    b = [100 if k >= 5 else 0 for k in range(8)] + [0]
    risk_parameter = 100
    def cost(liability):
        exponents = [x / risk_parameter for x in liability]
        shift = max(exponents)
        return risk_parameter * (shift + math.log(sum(p * math.exp(x-shift)
                                             for p, x in zip(probabilities, exponents))))
    zero = [0] * 9
    total = [x+y for x, y in zip(a,b)]
    first = cost(a) - cost(zero)
    second = cost(total) - cost(a)
    basket = cost(total) - cost(zero)
    assert abs(first + second - basket) < 1e-10
    return {"first_cover_quote_from_empty_inventory": round(first, 6),
            "opposite_tail_quote_from_empty_inventory": round(cost(b)-cost(zero), 6),
            "second_cover_quote_after_first_sale": round(second, 6),
            "atomic_basket_quote": round(basket, 6),
            "sequential_quote_total": round(first+second, 6),
            "customer_holdings_used_in_pricing": False,
            "boundary": "Illustrative finite-state entropic cost with assumed probabilities and risk parameter, no fees. Shows common maker-inventory pricing and exact telescoping, not profitable liquidity, a production AMM, an onchain numeric implementation, or a guarantee every quote can be funded. Integer funding checks remain mandatory."}


def main():
    output = Path(__file__).with_name("cover-marketplace-quant-results.json")
    result = {"date": "2026-09-30", "scope": "Exact synthetic accounting and pricing-identity research; no empirical liquidity or demand findings.",
              "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "model_sha256": {name: hashlib.sha256((ROOT / "model_v2" / name).read_bytes()).hexdigest()
                               for name in ("schema.py", "verifier.py", "oracle.py", "ledger.py", "examples.py")},
              "basis": basis_experiment(), "maker": maker_experiment(),
              "joint_prices": joint_price_experiment(), "coherent_prices": coherent_pricing_experiment(),
              "shared_quotes": shared_quote_experiment()}
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
