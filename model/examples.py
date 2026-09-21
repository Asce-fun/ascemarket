"""Executable numerical cases. Prices are stipulated, not discovered or forecast."""

from copy import deepcopy
from fractions import Fraction

from .ledger import Batch, Change, Fee, Ledger, approve
from .payoffs import Payoff, VOID


LOW = Payoff.below(95, 100, void=0)
HIGH = Payoff.step(105, 100, void=0)
RANGE = Payoff.interval(97, 103, 20, void=0)


def change(book, account, payout=Payoff(), payment=0, cash=0):
    return Change(account, book.account(account).revision, payout, payment, cash)


def commit(book, *changes, fees=()):
    batch = Batch(book.market_id, book.now + 100, changes, fees)
    book.execute(batch, [approve(batch, c.account) for c in changes])
    book.audit()
    return batch


def new_book():
    book = Ledger()
    for account in ("maker", "low_buyer", "high_buyer", "range_buyer"):
        book.register(account, 500)
    return book


def record(book, label):
    return {"step": label, "escrow": book.escrow,
            "maker_net_cash_in": 500 - book.wallet("maker"),
            "maker_guaranteed_balance": book.account("maker").balance.minimum,
            "maker_boundaries": len(book.account("maker").balance.knots)}


def open_tails(book=None):
    book = new_book() if book is None else book
    commit(book, change(book, "maker", -LOW, -22, 78),
           change(book, "low_buyer", LOW, 22, 22))
    rows = [record(book, "Sell low tail")]
    commit(book, change(book, "maker", -HIGH, -32, -32),
           change(book, "high_buyer", HIGH, 32, 32))
    rows.append(record(book, "Sell high tail"))
    return book, rows


def lifecycle():
    book, rows = open_tails()
    existing = {n: book.account(n) for n in ("low_buyer", "high_buyer")}
    commit(book, change(book, "maker", -RANGE, -5),
           change(book, "range_buyer", RANGE, 5, 5))
    stable = all(book.account(n) == a for n, a in existing.items())
    rows.append(record(book, "Introduce range boundaries"))
    commit(book, change(book, "maker", cash=-5))
    rows.append(record(book, "Withdraw guaranteed 5"))
    commit(book, change(book, "maker", (LOW + HIGH) * Fraction(1, 2), 27, -22),
           change(book, "low_buyer", -LOW * Fraction(1, 2), -11, -11),
           change(book, "high_buyer", -HIGH * Fraction(1, 2), -16, -16),
           fees=(Fee("maker", 1),))
    rows.append(record(book, "Buy back half of both tails, fee 1"))
    branches = {}
    for result in (100, VOID):
        settled = deepcopy(book)
        settled.advance(settled.close_at)
        settled.finalize(result)
        payouts = {}
        for name in settled.names:
            payouts[name] = settled.redeem(name)
            settled.audit()
        branches[str(result)] = {"payouts": payouts, "escrow": settled.escrow}
    return book, {"rows": rows, "unrelated_accounts_unchanged": stable,
                  "settlement": branches}


def automatic_change(book, name, payout, payment):
    funding = book.funding(name, payout, payment)
    return change(book, name, payout, payment, funding.deposit - funding.withdrawable)


def closing_case(*, slices=1, high_first=False, atomic=False):
    """Close fixed-price tails; withdraw every guaranteed balance after each trade.

    Slices add executions and assume every partial quote is available at the same
    unit price. No fixed transaction cost or adverse price movement is modeled.
    """
    book, _ = open_tails()
    starting_wallet = book.wallet("maker")
    peak_extra = Fraction(0)
    executions = 0
    if atomic:
        commit(book, automatic_change(book, "maker", LOW + HIGH, 54),
               automatic_change(book, "low_buyer", -LOW, -22),
               automatic_change(book, "high_buyer", -HIGH, -32))
        executions = 1
    else:
        legs = [(LOW, "low_buyer", 22), (HIGH, "high_buyer", 32)]
        if high_first:
            legs.reverse()
        fraction = Fraction(1, slices)
        for _ in range(slices):
            for payout, buyer, price in legs:
                payout, price = payout * fraction, price * fraction
                commit(book, automatic_change(book, "maker", payout, price),
                       automatic_change(book, buyer, -payout, -price))
                peak_extra = max(peak_extra, starting_wallet - book.wallet("maker"))
                executions += 1
    if book.escrow != 0 or any(not book.account(n).balance.is_zero for n in book.names):
        raise AssertionError("close left outstanding funds or obligations")
    return {"executions": executions, "peak_additional_maker_cash": peak_extra,
            "final_locked": book.escrow, "maker_final_wallet": book.wallet("maker")}


def funding_comparison():
    return {
        "Sequential full legs, low first": closing_case(),
        "Sequential full legs, high first": closing_case(high_first=True),
        "Sequential, 10 slices per leg": closing_case(slices=10),
        "Sequential, 100 slices per leg": closing_case(slices=100),
        "Atomic package": closing_case(atomic=True),
    }
