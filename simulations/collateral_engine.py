"""Independent finite-state arithmetic in integer collateral base units.

This module deliberately does not use model_v2.verifier. The existing ledger
executes the examples; these calculations supply an independent comparison.
Prices are inputs. No probabilities, marks, correlations, or liquidation rules.
"""
from dataclasses import dataclass
from typing import Iterable, Sequence

MAX_ABS = 2**127 - 1


def integer(value: int) -> int:
    if type(value) is not int or abs(value) > MAX_ABS:
        raise ValueError("expected bounded integer")
    return value


def vector(values: Sequence[int], states: int | None = None) -> tuple[int, ...]:
    result = tuple(integer(x) for x in values)
    if not result or (states is not None and len(result) != states):
        raise ValueError("wrong or empty state domain")
    return result


def payoff(values: Sequence[int], states: int | None = None) -> tuple[int, ...]:
    result = vector(values, states)
    if min(result) < 0:
        raise ValueError("purchased cover must have nonnegative payouts")
    return result


def aggregate(positions: Iterable[tuple[int, Sequence[int]]], states: int) -> tuple[int, ...]:
    if type(states) is not int or states < 1:
        raise ValueError("invalid state count")
    result = [0] * states
    for quantity, raw in positions:
        integer(quantity)
        f = payoff(raw, states)
        for k, value in enumerate(f):
            result[k] = integer(result[k] + integer(quantity * value))
    return tuple(result)


def requirement(payout: Sequence[int]) -> int:
    """Cash-only nonnegative reserve: max(0, -min signed terminal payout)."""
    p = vector(payout)
    return max(0, -min(p))


def guaranteed_floor(cash: int, payout: Sequence[int]) -> int:
    """May be negative for an inadmissible candidate; do not clamp it."""
    return integer(integer(cash) + min(vector(payout)))


@dataclass(frozen=True)
class Candidate:
    cash: int
    payout: tuple[int, ...]
    floor: int
    deposit_needed: int


def candidate(cash: int, payout: Sequence[int], delta_cash: int,
              delta_payout: Sequence[int], *, fee: int = 0) -> Candidate:
    """Fee is already a separate recipient credit in the executing ledger.

    Caller supplies premiums/buybacks once in delta_cash; external funding has
    not yet occurred. It is not also subtracted from collateral a second time.
    """
    p = vector(payout)
    d = vector(delta_payout, len(p))
    if integer(fee) < 0:
        raise ValueError("negative fee")
    next_cash = integer(integer(integer(cash) + integer(delta_cash)) - fee)
    next_p = tuple(integer(a + b) for a, b in zip(p, d))
    floor = guaranteed_floor(next_cash, next_p)
    return Candidate(next_cash, next_p, floor, max(0, -floor))


def gross_short_cap(positions: Iterable[tuple[int, Sequence[int]]]) -> int:
    """Separate full funding for short legs, without granting long offsets."""
    result = 0
    for q, f in positions:
        integer(q)
        f = payoff(f)
        if q < 0:
            result = integer(result + integer(-q * max(f)))
    return result


def ctf_allocation(covers: Sequence[Sequence[int]]) -> dict:
    """Construct a shared-condition atomic-claim backing certificate.

    M complete sets mint M units of each atomic claim. Give each buyer its
    state-specific amount and retain M-L[k]. This is algebra, not an EVM test.
    """
    if not covers:
        raise ValueError("no covers")
    n = len(covers[0])
    claims = tuple(payoff(f, n) for f in covers)
    liability = aggregate(((1, f) for f in claims), n)
    backing = max(liability)
    residual = tuple(backing - value for value in liability)
    return {"backing": backing, "buyer_claims": claims,
            "aggregate_liability": liability, "maker_residual": residual}


def export_account(cash: int, payout: Sequence[int], exported: Sequence[int]) -> int:
    """Floor remaining after removing an internal right. Assets need checking too."""
    p = vector(payout)
    f = payoff(exported, len(p))
    return guaranteed_floor(cash, tuple(integer(a - b) for a, b in zip(p, f)))


def minimum_new_cash(initial_payout: Sequence[int], cashflows: Sequence[int],
                     payouts_after_actions: Sequence[Sequence[int]]) -> int:
    """Peak net personal funding, with released cash immediately reusable.

    Includes the starting portfolio before any premium or action. Requires the
    same executed path and cashflows when comparing collateral architectures.
    """
    p = vector(initial_payout)
    if len(cashflows) != len(payouts_after_actions):
        raise ValueError("mismatched lifecycle")
    cumulative = 0
    peak = max(0, -min(p))
    for flow, raw in zip(cashflows, payouts_after_actions):
        cumulative = integer(cumulative + integer(flow))
        next_p = vector(raw, len(p))
        peak = max(peak, -min(next_p) - cumulative)
    return max(0, peak)
