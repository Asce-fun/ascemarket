"""Check hypothetical quote cards against the existing accounting kernel.

This is not a quoting service. Prices are fixtures; no external trades occur.
Run: python3 -B -m model.workflow_examples --output research/workflow-checks.json
"""

import argparse
from fractions import Fraction as F
import json
from pathlib import Path

from .examples import LOW, HIGH, change, commit
from .ledger import Fee, Ledger
from .payoffs import Payoff, VOID


def protection(start, cap=200):
    # Constant over numeric outcomes, but explicitly zero on VOID.
    return Payoff(cap, (), 0) - Payoff.ramp(start - cap, start, cap, void=0)


def book():
    ledger = Ledger()
    ledger.register("user", 1000)
    ledger.register("provider", 1000)
    return ledger


def equal(actual, expected, label):
    if actual != expected:
        raise AssertionError(f"{label}: {actual!r} != {expected!r}")


def summary(ledger, before, label):
    balance = ledger.account("user").balance
    return {"case": label, "wallet_change": ledger.wallet("user") - before,
            "user_future_balance_min_max": balance.extrema(),
            "user_void_balance": balance.value(VOID),
            "user_net_cash_contributed_to_date": 1000 - ledger.wallet("user"),
            "escrow": ledger.escrow,
            "treasury_balance": ledger.account("treasury").balance.base}


def run():
    ledger = book()
    original, target = protection(3000), protection(2873)
    before = ledger.wallet("user")
    commit(ledger, change(ledger, "user", original, payment=64, cash=65),
           change(ledger, "provider", -original, payment=-64, cash=136),
           fees=(Fee("user", 1),))
    equal(ledger.account("user").balance, original, "A resulting payout")
    equal(ledger.wallet("user") - before, -65, "A wallet debit")
    a = summary(ledger, before, "A: buy capped downside protection")

    before = ledger.wallet("user")
    delta = target - original
    commit(ledger, change(ledger, "user", delta, payment=-15, cash=-14),
           change(ledger, "provider", -delta, payment=15, cash=15),
           fees=(Fee("user", 1),))
    equal(ledger.account("user").balance, target, "B resulting payout")
    equal(ledger.wallet("user") - before, 14, "B wallet credit")
    b = summary(ledger, before, "B: move protection start to 2873")
    b["incremental_value_vs_keeping_original_min_max"] = (target - original + Payoff.constant(14)).extrema()
    equal(b["incremental_value_vs_keeping_original_min_max"], (-113, 14), "B change versus retaining original")

    # An explicit, stronger approximation than rounding to the nearest spread.
    approximation = (protection(2850) + protection(2900)) * F(1, 2)
    difference = approximation - target
    error = max(abs(v) for v in difference.extrema())
    equal(error, F(27, 2), "four-listed-put approximation error")
    b["listed_option_approximation"] = {
        "legs": {"put_2850": "1/2", "put_2650": "-1/2",
                 "put_2900": "1/2", "put_2700": "-1/2"},
        "max_absolute_normal_payout_error": error,
        "optimality_claim": False,
        "prices_and_execution_eligibility_verified": False,
    }
    b["normal_payout_samples"] = [
        {"observation": x, "old": original.value(x), "target": target.value(x),
         "listed_approximation": approximation.value(x)}
        for x in (2600, 2673, 2700, 2800, 2850, 2873, 2900, 3000)]

    maker = book()
    tails = LOW + HIGH
    # The provider owns both tail claims; the user is their fully funded seller.
    commit(maker, change(maker, "user", -tails, payment=-54, cash=46),
           change(maker, "provider", tails, payment=54, cash=54))
    before = maker.wallet("user")
    commit(maker, change(maker, "user", tails * F(1, 2), payment=27, cash=-22),
           change(maker, "provider", -tails * F(1, 2), payment=-27, cash=-27),
           fees=(Fee("user", 1),))
    equal(maker.account("user").balance, Payoff.constant(50) - tails * F(1, 2), "C remaining payout")
    equal(maker.wallet("user") - before, 22, "C wallet credit")
    c = summary(maker, before, "C: halve two tail obligations")
    c["released_backing_before_payment_and_fee"] = 50
    c["trade_payment"] = 27
    c["fee"] = 1

    # A categorical complement reproduces Case C, including the exceptional state.
    # Slots: low, middle, high, VOID. Tail claim: [1,0,1,0]. Complement: [0,1,0,1].
    observations = (94, 100, 106, VOID)
    equal([maker.account("user").balance.value(x) for x in observations],
          [0, 50, 0, 50], "C categorical complement")
    c["four_outcome_reference"] = {
        "slots": ["low", "middle", "high", "VOID"],
        "user_remaining_claims": [0, 50, 0, 50],
        "provider_remaining_claims": [50, 0, 50, 0],
        "treasury": 1,
        "equal_backing": 51,
    }
    ledger.audit()
    maker.audit()
    return {"status": "all scenario checks passed", "prices": "illustrative, not live quotes",
            "cases": [a, b, c],
            "not_implemented": ["quote service", "capacity reservation", "real signatures",
                                "idempotent request store", "venue adapter", "user interface"]}


def serializable(value):
    if isinstance(value, F):
        return str(value)
    if isinstance(value, dict):
        return {k: serializable(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [serializable(v) for v in value]
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = json.dumps(serializable(run()), indent=2) + "\n"
    if args.output:
        args.output.write_text(result)
        print(f"All scenario checks passed; wrote {args.output}")
    else:
        print(result, end="")


if __name__ == "__main__":
    main()
