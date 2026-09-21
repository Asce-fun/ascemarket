"""Matched lifecycle funding challenge; no live trading or pricing model.

Run: python3 -B -m model.capital_challenge --output research/capital-results.json
The independent reference uses outstanding quantities and cash accounting, not
the ledger's payout evaluation or minimum calculation.
"""

import argparse
from fractions import Fraction as F
import json
from pathlib import Path

from .examples import LOW, HIGH, automatic_change, change, commit
from .ledger import Fee, Ledger, Rejected
from .payoffs import Payoff, VOID


def matched_path(actions, *, fee=0, settle=106, basis=(LOW, HIGH), verify=True):
    book = Ledger()
    book.register("user", 10000)
    book.register("provider", 10000)
    quantities = [F(0), F(0)]
    receipts = F(0)
    fees = F(0)
    previous = {"asce": F(0), "exact_reference": F(0), "separate": F(0)}
    peak = dict(previous)
    gross_deposits = dict(previous)
    rows = []
    for label, changes, prices in actions:
        changes, prices = list(map(F, changes)), list(map(F, prices))
        incoming = sum((d * p for d, p in zip(changes, prices)), F(0))
        delta = -(basis[0] * changes[0] + basis[1] * changes[1])
        funding = book.funding("user", delta, -incoming, fee)
        cash = funding.deposit - funding.withdrawable
        commit(book, change(book, "user", delta, -incoming, cash),
               automatic_change(book, "provider", -delta, incoming),
               fees=(Fee("user", fee),) if fee else ())
        quantities = [a + b for a, b in zip(quantities, changes)]
        if any(q < 0 for q in quantities):
            raise AssertionError("reference supports nonnegative outstanding obligations")
        receipts += incoming
        fees += F(fee)
        # Both bases have disjoint nonnegative tails, each with maximum 100.
        exact_backing = 100 * max(quantities)
        separate_backing = 100 * sum(quantities)
        current = {"asce": 10000 - book.wallet("user"),
                   "exact_reference": exact_backing - receipts + fees,
                   "separate": separate_backing - receipts + fees}
        if verify and current["asce"] != current["exact_reference"]:
            raise AssertionError((label, current))
        row = {"action": label, "outstanding": quantities[:],
               "net_premiums_received_to_date": receipts, "fees_to_date": fees,
               "exact_backing": exact_backing, "separate_backing": separate_backing,
               "net_personal_cash_committed": current.copy(),
               "cash_deposit_positive_withdrawal_negative": {}}
        for method, amount in current.items():
            flow = amount - previous[method]
            row["cash_deposit_positive_withdrawal_negative"][method] = flow
            peak[method] = max(peak[method], amount)
            gross_deposits[method] += max(F(0), flow)
        previous = current
        rows.append(row)
    # Complete every lifecycle, including already-flat positions, by redemption.
    book.advance(book.close_at)
    book.finalize(settle)
    user_redemption = book.redeem("user")
    for name in ("provider", "treasury"):
        book.redeem(name)
    book.audit()
    final_loss = 10000 - book.wallet("user")
    due = sum((quantity * payout.value(settle) for quantity, payout in zip(quantities, basis)), F(0))
    if final_loss != due - receipts + fees or book.escrow != 0:
        raise AssertionError("final cash reconciliation failed")
    return {"rows": rows, "peak_personal_cash_required": peak,
            "gross_deposits_including_recycled_money": gross_deposits,
            "initial_cash_required": rows[0]["net_personal_cash_committed"],
            "user_final_redemption": user_redemption,
            "final_realized_loss_negative_means_profit": final_loss,
            "fees": fees, "settlement": str(settle),
            "verdict_vs_exact_reference": "tie"}


OPEN = ("Open both obligations together", (1, 1), (22, 32))


def scenarios(fee=0):
    return {
        "hold_tail_settlement": matched_path([OPEN], fee=fee),
        "hold_middle_settlement": matched_path([OPEN], fee=fee, settle=100),
        "hold_void_settlement": matched_path([OPEN], fee=fee, settle=VOID),
        "halve_then_close_package": matched_path([
            OPEN, ("Buy back half of both", (F(-1, 2), F(-1, 2)), (22, 32)),
            ("Close the remainder together", (F(-1, 2), F(-1, 2)), (22, 32))], fee=fee),
        "individual_exits_after_reversal": matched_path([
            OPEN, ("Close low at 90", (-1, 0), (90, 0)),
            ("Later close high at 90", (0, -1), (0, 90))], fee=fee),
        "open_low_then_high": matched_path([
            ("Open low", (1, 0), (22, 0)), ("Open high", (0, 1), (0, 32))], fee=fee),
        "open_high_then_low": matched_path([
            ("Open high", (0, 1), (0, 32)), ("Open low", (1, 0), (22, 0))], fee=fee),
    }


def rejection_check():
    book = Ledger()
    book.register("user", 46)
    book.register("provider", 1000)
    commit(book, change(book, "user", -(LOW + HIGH), -54, 46),
           change(book, "provider", LOW + HIGH, 54, 54))
    before = book.snapshot()
    try:
        commit(book, change(book, "user", LOW, 90),
               automatic_change(book, "provider", -LOW, -90))
    except Rejected:
        if book.snapshot() != before:
            raise AssertionError("rejection changed state")
    else:
        raise AssertionError("unsafe exit accepted")
    return {"only_original_46_available": "individual exit rejected without state change",
            "extra_deposit_required_for_low_exit_at_90": book.funding("user", LOW, 90).deposit}


def market_replay():
    path = Path(__file__).resolve().parent.parent / "research/capital-market-snapshot.json"
    snapshot = json.loads(path.read_text())
    quotes = {r["data"]["instrument_name"]: r["data"] for r in snapshot["legs"]}
    def side(strike, kind, side):
        data = quotes[f"ETH_USDC-25SEP26-{strike}-{kind}"]
        if data["state"] != "open" or F(str(data[f"best_{side}_amount"])) < 1:
            raise AssertionError("snapshot lacks one-unit displayed size")
        return F(str(data[f"best_{side}_price"]))
    open_low = side(2800, "P", "bid") - side(2700, "P", "ask")
    open_high = side(3000, "C", "bid") - side(3100, "C", "ask")
    close_low = side(2800, "P", "ask") - side(2700, "P", "bid")
    close_high = side(3000, "C", "ask") - side(3100, "C", "bid")
    ramps = (Payoff(100, (), 0) - Payoff.ramp(2700, 2800, 100, void=0),
             Payoff.ramp(3000, 3100, 100, void=0))
    opening = ("Open at displayed leg prices, assumed package", (1, 1), (open_low, open_high))
    together = matched_path([opening, ("Close at displayed leg prices, assumed package", (-1, -1),
                                       (close_low, close_high))], basis=ramps)
    separate = matched_path([opening, ("Close low spread", (-1, 0), (close_low, 0)),
                             ("Close high spread", (0, -1), (0, close_high))], basis=ramps)
    if (open_low + open_high, close_low + close_high) != (F(81), F("110.2")):
        raise AssertionError("captured price calculation changed; re-review report")
    if together["peak_personal_cash_required"]["asce"] != F("29.2"):
        raise AssertionError("package price replay mismatch")
    if separate["peak_personal_cash_required"]["asce"] != 128:
        raise AssertionError("sequential price replay mismatch")
    return {"opening_credit": open_low + open_high, "closing_cost": close_low + close_high,
            "fee_status": "excluded; no venue account or Asce provider quote",
            "execution_status": "counterfactual replay of displayed leg prices, not a firm package or completed fill",
            "assumed_package_close": together, "sequential_spread_close": separate}


def run():
    zero, fee = scenarios(), scenarios(1)
    expected = {"hold_tail_settlement": (46, 146, 46),
                "hold_middle_settlement": (46, 146, -54),
                "hold_void_settlement": (46, 146, -54),
                "halve_then_close_package": (46, 146, 0),
                "individual_exits_after_reversal": (136, 146, 126),
                "open_low_then_high": (78, 146, 46),
                "open_high_then_low": (68, 146, 46)}
    for key, values in expected.items():
        actual = zero[key]
        if (actual["peak_personal_cash_required"]["asce"],
                actual["peak_personal_cash_required"]["separate"],
                actual["final_realized_loss_negative_means_profit"]) != values:
            raise AssertionError((key, actual))
    count = 0
    for low in range(0, 121, 5):
        for high in range(0, 121, 5):
            r = matched_path([OPEN, ("Close low", (-1, 0), (low, 0)),
                              ("Close high", (0, -1), (0, high))])
            if r["peak_personal_cash_required"]["asce"] != max(46, 46 + low, low + high - 54):
                raise AssertionError("grid peak formula mismatch")
            if r["peak_personal_cash_required"]["separate"] != max(146, 46 + low, low + high - 54):
                raise AssertionError("separate grid peak mismatch")
            count += 1
    # Same analysis on bounded ramps, not just binary claims.
    ramps = (Payoff(100, (), 0) - Payoff.ramp(2700, 2800, 100, void=0),
             Payoff.ramp(3000, 3100, 100, void=0))
    for observation in (2600, 2700, 2750, 2800, 2900, 3000, 3050, 3100, 3200, VOID):
        matched_path([OPEN], basis=ramps, settle=observation)
    return {"status": "all checks passed", "zero_fee": zero, "flat_one_per_batch_fee_sensitivity": fee,
            "reversal_grid": {"paths": count, "price_range": "0 to 120 in steps of 5, including adverse offers above the payout cap",
                              "peak_asce_formula": "max(46, 46 + first buyback, first buyback + second buyback - 54)",
                              "peak_separate_formula": "max(146, 46 + first buyback, first buyback + second buyback - 54)",
                              "exact_reference_ties": count,
                              "asce_saving_vs_separate_range": [0, 100]},
            "bounded_ramp_settlement_checks": 10, "exit_limit": rejection_check(),
            "public_price_replay": market_replay(),
            "reference_status": "independent exact-funding arithmetic, not a deployed competing venue",
            "prices": "stipulated and identical across methods; no live fills"}


def encode(value):
    if isinstance(value, F):
        return str(value)
    if isinstance(value, dict):
        return {k: encode(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [encode(v) for v in value]
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = json.dumps(encode(run()), indent=2) + "\n"
    if args.output:
        args.output.write_text(result)
        print(f"All lifecycle, fee, 625 reversal and 10 ramp checks passed; wrote {args.output}")
    else:
        print(result, end="")


if __name__ == "__main__":
    main()
